"""Probability sample of markets with recorded inclusion probabilities, plus recent trades.

Frame: forecast-eligible markets of one complete snapshot (``panel.eligibility_mask`` exactly as
``forecast.predict_frame`` / ``book_sweep.select_tokens`` use it), one row per condition id.
Strata: liquidity quartile x spread tercile, cut points computed on the frame. Proportional
allocation (min 1 per non-empty stratum), simple random sampling without replacement per stratum,
with a seed that is generated and written to ``plan.json`` before the first request (sealed).

Trades: Data API ``GET /trades?market=<conditionId>`` (``astrolabe/clients/data_api.py:3,104``;
admitted source "Data API v2 taker-only trade pages",
``docs/architecture/V2_PROSPECTIVE_SOURCE_ADMISSION.md:45``). Timestamps are Unix seconds,
newest first (``astrolabe/ingest/normalize.py:455-458``).

Sign convention (signed volume on outcome 0, in shares): the API ``side`` is the taker's side on
the traded ``asset``. BUY of outcome 0 = +size, SELL of outcome 0 = -size, BUY of outcome 1 =
-size (equivalent to selling outcome 0), SELL of outcome 1 = +size. Outcome is ``outcomeIndex``,
falling back to ``asset == clob_token_id_0``; trades with neither contribute 0 and are counted.

Origin features use only trades with timestamp strictly before the market's snapshot
``received_utc``. Trades stamped after the request-sent time are dropped and counted (clock
anomaly). Wallet fields are never stored.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import secrets
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forecast, panel

SAMPLE_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "trade_samples"
ENDPOINT = "https://data-api.polymarket.com/trades"
HEADERS = {"Accept-Encoding": "gzip", "User-Agent": "arepo-research-lab/1"}
TRADE_LIMIT = 500
WINDOW_S = 3600.0
MAX_RETRIES = 5
MAX_REQUESTS = 3000
MAX_SECONDS = 20 * 60
DELAY_SECONDS = 0.1
BACKOFF_BASE = 1.0
N_TOTAL = 2000
VERSION = "trade-sample-v1"

Transport = Callable[[dict], tuple[int, bytes, dict]]
TRADE_COLS = ["market_id", "condition_id", "ts", "side", "price", "size",
              "outcome_index", "asset", "tx_hash"]
FEATURE_COLS = ["market_id", "condition_id", "stratum", "origin_utc", "sent_utc", "status",
                "n_returned", "n_dropped_future", "n_unsigned", "n_trades_1h", "volume_1h",
                "notional_1h", "signed_volume_1h", "max_trade_size_1h",
                "time_since_last_trade_s", "trades_truncated"]


def _now() -> datetime:
    return datetime.now(UTC)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def httpx_transport(timeout: float = 60.0) -> Transport:
    import httpx

    client = httpx.Client(timeout=timeout, headers=HEADERS)

    def fetch(params: dict) -> tuple[int, bytes, dict]:
        resp = client.get(ENDPOINT, params=params)
        return resp.status_code, resp.content, dict(resp.headers)

    return fetch


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=forecast.ROOT,
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# --- atomic writes ----------------------------------------------------------------------------


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _atomic_json(path: Path, obj: Any) -> None:
    atomic_write(path, (json.dumps(obj, indent=1, sort_keys=False) + "\n").encode())


def _atomic_csv_gz(path: Path, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(df.to_csv(index=False).encode())
    atomic_write(path, buf.getvalue())


# --- frame, strata, allocation, sampling ------------------------------------------------------


def build_frame(rows: pd.DataFrame) -> pd.DataFrame:
    """Forecast-eligible binary markets, one per condition id, sorted by condition id."""
    binary = rows[rows["binary"] == 1].reset_index(drop=True)
    t_i = panel._epoch(binary["received_utc"])
    ok = panel.eligibility_mask(binary, t_i + forecast.FORECAST_END_MARGIN_H * 3600.0)
    o = binary[ok].copy()
    o = o[o["condition_id"].notna() & (o["condition_id"].astype(str) != "")]
    spread = o["spread"].to_numpy(float)
    o["spread_eff"] = np.where(np.isnan(spread), o["best_ask"] - o["best_bid"], spread)
    o["liquidity_eff"] = o["liquidity"].astype(float).fillna(0.0)
    o = o.sort_values(["condition_id", "market_id"]).drop_duplicates("condition_id")
    return o.reset_index(drop=True)


def assign_strata(frame: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Stratum label ``Lq-Sq`` (liquidity quartile 0-3, spread tercile 0-2); cuts on the frame."""
    liq_cuts = [float(x) for x in np.quantile(frame["liquidity_eff"], [0.25, 0.5, 0.75])]
    spr_cuts = [float(x) for x in np.quantile(frame["spread_eff"], [1 / 3, 2 / 3])]
    li = np.searchsorted(liq_cuts, frame["liquidity_eff"].to_numpy(), side="right")
    si = np.searchsorted(spr_cuts, frame["spread_eff"].to_numpy(), side="right")
    labels = pd.Series([f"L{a}-S{b}" for a, b in zip(li, si, strict=True)], index=frame.index)
    return labels, {"liquidity_quartile_cuts": liq_cuts, "spread_tercile_cuts": spr_cuts,
                    "rule": "index = searchsorted(cuts, x, side='right'); ties go to upper bin"}


def allocate(sizes: dict[str, int], n_total: int) -> dict[str, int]:
    """Proportional allocation, min 1 per non-empty stratum, <= stratum size, sums to n_total."""
    total = sum(sizes.values())
    if n_total >= total:
        return dict(sizes)
    keys = sorted(k for k, v in sizes.items() if v > 0)
    if n_total < len(keys):
        raise ValueError("n_total smaller than the number of non-empty strata")
    exact = {k: n_total * sizes[k] / total for k in keys}
    alloc = {k: min(sizes[k], max(1, int(exact[k]))) for k in keys}
    while sum(alloc.values()) < n_total:
        cand = [k for k in keys if alloc[k] < sizes[k]]
        k = max(cand, key=lambda x: (exact[x] - alloc[x], x))
        alloc[k] += 1
    while sum(alloc.values()) > n_total:
        cand = [k for k in keys if alloc[k] > 1]
        k = min(cand, key=lambda x: (exact[x] - alloc[x], x))
        alloc[k] -= 1
    return alloc


def draw_sample(frame: pd.DataFrame, strata: pd.Series, n_total: int, seed: str) -> pd.DataFrame:
    """Deterministic given ``seed``: SRS without replacement within each stratum."""
    sizes = {k: int(v) for k, v in strata.value_counts().items()}
    alloc = allocate(sizes, n_total)
    rng = np.random.default_rng(int(seed, 16))
    parts = []
    for k in sorted(alloc):
        members = frame[strata == k]  # already sorted by condition_id
        pick = np.sort(rng.choice(len(members), size=alloc[k], replace=False))
        sub = members.iloc[pick].copy()
        sub["stratum"] = k
        sub["n_h"], sub["N_h"] = alloc[k], sizes[k]
        parts.append(sub)
    return pd.concat(parts).reset_index(drop=True)


def build_plan(rows: pd.DataFrame, manifest: dict, manifest_sha: str, rows_sha: str,
               n_total: int, seed: str) -> tuple[dict, pd.DataFrame]:
    frame = build_frame(rows)
    if frame.empty:
        raise ValueError("empty frame")
    strata, cuts = assign_strata(frame)
    sample = draw_sample(frame, strata, n_total, seed)
    sizes = {k: int(v) for k, v in strata.value_counts().items()}
    alloc = allocate(sizes, n_total)
    srows = []
    for k in sorted(alloc):
        f = Fraction(alloc[k], sizes[k])
        srows.append({"stratum": k, "N_h": sizes[k], "n_h": alloc[k],
                      "inclusion_prob": f"{f.numerator}/{f.denominator}",
                      "inclusion_float": float(f)})
    members = []
    for r in sample.itertuples():
        f = Fraction(int(r.n_h), int(r.N_h))
        members.append({"market_id": str(r.market_id), "condition_id": str(r.condition_id),
                        "stratum": r.stratum, "origin_utc": str(r.received_utc),
                        "token0": None if pd.isna(r.clob_token_id_0) else str(r.clob_token_id_0),
                        "inclusion_prob": f"{f.numerator}/{f.denominator}",
                        "inclusion_float": float(f)})
    plan = {
        "version": VERSION, "seed": seed, "seed_note": "sealed before any request",
        "snapshot_id": manifest.get("capture_id"), "snapshot_manifest_sha256": manifest_sha,
        "snapshot_rows_sha256": rows_sha, "n_total_requested": n_total,
        "n_sampled": len(members), "frame_size": len(frame), "cuts": cuts, "strata": srows,
        "eligibility": "panel.eligibility_mask at origin + FORECAST_END_MARGIN_H, one per "
                       "condition_id (smallest market_id); NaN liquidity treated as 0",
        "sum_inclusion_over_frame": float(sum(r["N_h"] * r["inclusion_float"] for r in srows)),
        "sample": members,
    }
    return plan, sample


# --- trade parsing and features ---------------------------------------------------------------


def parse_trades(body: bytes) -> tuple[list[dict], int]:
    """Compact trades (no wallet fields) and a count of malformed items. Raises on non-list."""
    data = json.loads(body)
    if not isinstance(data, list):
        raise ValueError("Data API /trades did not return a list")
    out, bad = [], 0
    for it in data:
        try:
            ts = int(it["timestamp"])
            side = str(it["side"]).upper()
            price, size = float(it["price"]), float(it["size"])
        except (KeyError, TypeError, ValueError):
            bad += 1
            continue
        oi = it.get("outcomeIndex")
        out.append({"ts": ts, "side": side, "price": price, "size": size,
                    "outcome_index": None if oi is None else int(oi),
                    "asset": None if it.get("asset") is None else str(it["asset"]),
                    "tx_hash": it.get("transactionHash")})
    out.sort(key=lambda t: -t["ts"])
    return out, bad


def _sign(t: dict, token0: str | None) -> int:
    oi = t["outcome_index"]
    if oi not in (0, 1):
        if token0 is None or t["asset"] is None:
            return 0
        oi = 0 if t["asset"] == token0 else None
        if oi is None:
            return 0
    buy = t["side"] == "BUY"
    if t["side"] not in ("BUY", "SELL"):
        return 0
    return (1 if buy else -1) * (1 if oi == 0 else -1)


def origin_features(trades: list[dict], origin_epoch: float, n_returned: int,
                    token0: str | None = None, limit: int = TRADE_LIMIT) -> dict:
    """Features from trades with ts strictly before ``origin_epoch`` only."""
    before = [t for t in trades if t["ts"] < origin_epoch]
    win = [t for t in before if t["ts"] >= origin_epoch - WINDOW_S]
    signs = [_sign(t, token0) for t in win]
    oldest = min((t["ts"] for t in trades), default=None)
    return {
        "n_trades_1h": len(win),
        "volume_1h": float(sum(t["size"] for t in win)),
        "notional_1h": float(sum(t["size"] * t["price"] for t in win)),
        "signed_volume_1h": float(sum(s * t["size"] for s, t in zip(signs, win, strict=True))),
        "max_trade_size_1h": float(max((t["size"] for t in win), default=0.0)),
        "n_unsigned": sum(1 for s in signs if s == 0),
        "time_since_last_trade_s": (origin_epoch - max(t["ts"] for t in before)) if before
        else float("nan"),
        "trades_truncated": bool(n_returned >= limit and oldest is not None
                                 and oldest > origin_epoch - WINDOW_S),
    }


# --- fetching ---------------------------------------------------------------------------------


def run(snapshot_dir: Path, transport: Transport, *, n_total: int = N_TOTAL,
        out_root: Path = SAMPLE_ROOT, seed: str | None = None, keep_raw: bool = False,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic, now: Callable[[], datetime] = _now,
        max_requests: int = MAX_REQUESTS, max_seconds: float = MAX_SECONDS) -> dict:
    snapshot_dir = Path(snapshot_dir)
    rows, snap_man = forecast.load_snapshot(snapshot_dir)
    man_sha = forecast.sha256_file(snapshot_dir / "manifest.json")
    rows_sha = forecast.sha256_file(snapshot_dir / "rows.csv.gz")
    seed = seed or secrets.token_hex(16)
    plan, sample = build_plan(rows, snap_man, man_sha, rows_sha, n_total, seed)
    started = now()
    sample_id = f"{started.strftime('%Y%m%dT%H%M%SZ')}_{seed[:8]}"
    out = Path(out_root) / sample_id
    out.mkdir(parents=True, exist_ok=False)
    # Seal: plan (with seed) and a 'planned' manifest are durable before any request.
    plan["sample_id"] = sample_id
    _atomic_json(out / "plan.json", plan)
    manifest: dict = {
        "sample_id": sample_id, "version": VERSION, "state": "planned", "seed": seed,
        "plan_sha256": forecast.sha256_file(out / "plan.json"),
        "snapshot_id": snap_man.get("capture_id"), "code_commit": _git_commit(),
        "endpoint": ENDPOINT, "limit": TRADE_LIMIT, "takerOnly": "true",
        "caps": {"max_requests": max_requests, "max_seconds": max_seconds,
                 "max_retries": MAX_RETRIES},
        "hash_note": "sha256 of decoded response body", "started_utc": _fmt(started),
    }
    _atomic_json(out / "manifest.json", manifest)
    if keep_raw:
        (out / "raw").mkdir()

    t0 = clock()
    reqs: list[dict] = []
    trade_rows: list[dict] = []
    feat_rows: list[dict] = []
    n_req = n_retry = 0
    stopped: str | None = None
    for m in plan["sample"]:
        base = {"market_id": m["market_id"], "condition_id": m["condition_id"],
                "stratum": m["stratum"], "origin_utc": m["origin_utc"]}
        status, body, sent = "not_attempted", None, None
        for attempt in range(MAX_RETRIES + 1):
            if n_req >= max_requests or clock() - t0 > max_seconds:
                stopped = "request_cap" if n_req >= max_requests else "time_cap"
                break
            sleep(DELAY_SECONDS if attempt == 0 else BACKOFF_BASE * 2 ** (attempt - 1))
            sent = now()
            n_req += 1
            code, raw, err = 0, b"", None
            try:
                code, raw, _ = transport({"market": m["condition_id"], "limit": TRADE_LIMIT,
                                          "takerOnly": "true"})
            except Exception as exc:  # network failure is recorded, then retried
                err = type(exc).__name__
            recv = now()
            reqs.append({"market_id": m["market_id"], "attempt": attempt, "sent_utc": _fmt(sent),
                         "received_utc": _fmt(recv), "status": code or err,
                         "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
            if err or code == 429 or code >= 500:
                n_retry += 1
                status = "retries_exhausted"
                continue
            status = "ok" if code == 200 else f"http_{code}"
            body = raw if code == 200 else None
            if keep_raw and body is not None:
                atomic_write(out / "raw" / f"{m['market_id']}.json.gz", gzip.compress(raw, mtime=0))
            break
        if stopped:
            feat_rows.append({**base, "sent_utc": None, "status": "not_attempted"})
            continue
        feat = {**base, "sent_utc": _fmt(sent) if sent else None, "status": status}
        if body is not None:
            try:
                trades, bad = parse_trades(body)
            except ValueError:  # includes JSONDecodeError
                feat["status"] = "schema_error"
                feat_rows.append(feat)
                continue
            sent_epoch = sent.timestamp()
            kept = [t for t in trades if t["ts"] <= sent_epoch]
            origin_epoch = float(panel._epoch(pd.Series([m["origin_utc"]]))[0])
            f = origin_features(kept, origin_epoch, len(trades), m["token0"])
            feat.update({"n_returned": len(trades), "n_dropped_future": len(trades) - len(kept),
                         "n_malformed": bad, **f})
            trade_rows += [{"market_id": m["market_id"], "condition_id": m["condition_id"], **t}
                           for t in kept]
        feat_rows.append(feat)
    finished = now()
    state = "incomplete" if stopped else "complete"
    status_counts = pd.Series([f["status"] for f in feat_rows]).value_counts().to_dict()
    _atomic_csv_gz(out / "trades.csv.gz", pd.DataFrame(trade_rows, columns=TRADE_COLS))
    fdf = pd.DataFrame(feat_rows)
    for c in FEATURE_COLS:
        if c not in fdf.columns:
            fdf[c] = np.nan
    _atomic_csv_gz(out / "features.csv.gz", fdf[FEATURE_COLS])
    manifest.update({
        "state": state, "stop_reason": stopped, "finished_utc": _fmt(finished),
        "request_count": n_req, "retry_count": n_retry, "markets_sampled": len(plan["sample"]),
        "status_counts": {k: int(v) for k, v in status_counts.items()},
        "dropped_future_trades": int(fdf["n_dropped_future"].fillna(0).sum()),
        "trades_rows": len(trade_rows),
        "malformed_trades": int(fdf.get("n_malformed", pd.Series(dtype=float)).fillna(0).sum()),
        "trades_sha256": forecast.sha256_file(out / "trades.csv.gz"),
        "features_sha256": forecast.sha256_file(out / "features.csv.gz"),
        "requests": reqs,
    })
    _atomic_json(out / "manifest.json", manifest)
    return manifest
