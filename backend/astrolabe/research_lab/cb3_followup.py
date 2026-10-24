# ruff: noqa: E501
"""CB3 post-window trade follow-up step (docs/research_lab/CREATIVE_BATCH_3.md §4.3.2). Data-only; NOT wired into the pass.

Per pass (current capture c = pass i+1) writes ``data-dumps/research_lab/cb3_followup/<c>/``:
  plan.json            seed, sampled markets and request order, sealed (atomic) BEFORE the first request
  pre/                 rows of the previous pass's trade sample for the seeded 50% subsample, copied UNCHANGED (no request):
                       trades.csv.gz and wallets.csv.gz (hashed wallets), taken before the 3-day retention removes them
  post/trades.csv.gz   the window (previous capture start, request time] fetched again with windowed
                       /trades?market&start&end&takerOnly=true paging (limit 1,000, offset pages, <= 5 pages), hashed wallets
  vacuum_plan.json     seeded uniform draw (<= 300) of the A-rule onsets at c, inclusion probability recorded
  vacuum/trades.csv.gz windows (second-sweep receipt of the previous pass's onset, request time] for last pass's vacuum plan
  meta.json            per-market request records (request time, pages, page-cap flag, oldest ts), 429 counters
The step stores raw windows; the analysis applies ``ts < t`` to pre/ and ``ts > t`` to post/ (item 5). No raw wallet address is
written anywhere. The trade-sample directory is only read. Markets are requested in a seeded random order, so those not
reached within the budget are a random subset (missing, counted, never backfilled).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import cb3_declaration as D
from . import cb3_quote_vacuum as V
from . import forecast, trade_sample
from .wallet_sidecar import hash_wallet, load_or_create_key

VERSION = "cb3-followup-v1"
FOLLOWUP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "cb3_followup"
SAMPLE_ROOT = trade_sample.SAMPLE_ROOT
QS_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "cb3_extract"
DATA_DUMPS = forecast.ROOT / "data-dumps"
LIMIT = int(D.FOLLOWUP_CONSTANTS["limit"])
MAX_PAGES = int(D.FOLLOWUP_CONSTANTS["max_pages"])
DEFAULT_FRAC = float(D.FOLLOWUP_CONSTANTS["frac"])
DEFAULT_VACUUM_MAX = int(D.FOLLOWUP_CONSTANTS["vacuum_max"])
DEFAULT_RPS = float(D.FOLLOWUP_CONSTANTS["rps"])
DEFAULT_BUDGET_S = float(D.FOLLOWUP_CONSTANTS["budget_s"])
BACKOFF_BASE, BACKOFF_CAP = D.FOLLOWUP_CONSTANTS["backoff"]
MAX_429 = int(D.FOLLOWUP_CONSTANTS["max_429"])
R429_WINDOW_S, R429_HALVE_FRAC = D.FOLLOWUP_CONSTANTS["r429_window_s"], D.FOLLOWUP_CONSTANTS["r429_halve_frac"]
TRADE_COLS = ["market_id", "condition_id", "ts", "side", "price", "size", "outcome_index", "asset", "tx_hash", "wallet_hash"]

Transport = Callable[[dict], tuple[int, bytes, dict]]


def _fmt(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path, dtype=str, keep_default_na=False) if Path(path).exists() else None


def seeded_subsample(market_ids: list[str], seed: str, frac: float) -> list[str]:
    """Reproducible Bernoulli(frac) draw: a market is in iff sha256(seed | market_id) / 2^256 < frac."""
    out = []
    for m in sorted(market_ids):
        h = int(hashlib.sha256(f"{seed}|{m}".encode()).hexdigest(), 16) / float(1 << 256)
        if h < frac:
            out.append(m)
    return out


def seeded_order(items: list, seed: str) -> list:
    rng = np.random.default_rng(int(hashlib.sha256(f"{seed}|order".encode()).hexdigest()[:16], 16))
    idx = rng.permutation(len(items))
    return [items[i] for i in idx]


def find_previous_sample(prev_capture_id: str, sample_root: Path = SAMPLE_ROOT) -> Path | None:
    """Newest trade sample whose manifest snapshot_id is the previous capture (any state with a trades file)."""
    best = None
    for m in sorted(Path(sample_root).glob("*/manifest.json")):
        try:
            man = json.loads(m.read_text())
        except (OSError, ValueError):
            continue
        if man.get("snapshot_id") == prev_capture_id and (m.parent / "trades.csv.gz").exists():
            best = m.parent
    return best


def window_trades(transport: Transport, condition_id: str, start: float, end: float, *, sleep: Callable[[float], None], budget: Budget,
                  key: bytes | None) -> dict:
    """Windowed paging: market, start (inclusive), end (inclusive), takerOnly, limit 1,000, offset pages, <= 5 pages. Returns
    rows (hashed wallets), pages, ``page_cap`` (5 full pages: older prints in the window may be missing), ``oldest_ts``."""
    rows: list[dict] = []
    pages, cap, status = 0, False, "ok"
    for off in range(0, LIMIT * MAX_PAGES, LIMIT):
        code, body = budget.get(transport, {"market": condition_id, "start": int(math.floor(start)) + 1, "end": int(math.floor(end)), "takerOnly": "true",
                                            "limit": LIMIT, "offset": off}, sleep)
        if code is None:
            return {"rows": rows, "pages": pages, "page_cap": False, "oldest_ts": min((r["ts"] for r in rows), default=None), "status": budget.stop_reason or "failed"}
        if code == -1:
            return {"rows": rows, "pages": pages, "page_cap": False, "oldest_ts": min((r["ts"] for r in rows), default=None), "status": "retries_exhausted"}
        if code != 200:
            return {"rows": rows, "pages": pages, "page_cap": False, "oldest_ts": min((r["ts"] for r in rows), default=None), "status": f"http_{code}"}
        try:
            data = json.loads(body)
            if not isinstance(data, list):
                raise ValueError
        except ValueError:
            return {"rows": rows, "pages": pages, "page_cap": False, "oldest_ts": None, "status": "schema_error"}
        pages += 1
        for it in data:
            try:
                rows.append({"market_id": "", "condition_id": condition_id, "ts": int(it["timestamp"]), "side": str(it["side"]).upper(), "price": float(it["price"]),
                             "size": float(it["size"]), "outcome_index": None if it.get("outcomeIndex") is None else int(it["outcomeIndex"]),
                             "asset": None if it.get("asset") is None else str(it["asset"]), "tx_hash": it.get("transactionHash"),
                             "wallet_hash": hash_wallet(key, it.get("proxyWallet")) if key else None})
            except (KeyError, TypeError, ValueError):
                continue
        if len(data) < LIMIT:
            break
        if pages == MAX_PAGES:
            cap = True
    oldest = min((r["ts"] for r in rows), default=None)
    return {"rows": rows, "pages": pages, "page_cap": cap, "oldest_ts": oldest, "status": status}


class Budget:
    """Request budget: <= rps, Retry-After honoured, exponential back-off 1 s..30 s, rps halved when > 1% of the last 10 minutes of
    requests were 429, the step ends after 50 429s or when the wall-clock budget is spent."""

    def __init__(self, rps: float, budget_s: float, clock: Callable[[], float], max_retries: int = 5) -> None:
        self.rps, self.budget_s, self.clock, self.max_retries = rps, budget_s, clock, max_retries
        self.t0 = clock()
        self.n_req = self.n_429 = 0
        self.recent: list[tuple[float, bool]] = []
        self.stop_reason: str | None = None
        self.last_sent = -1e18
        self.halved = False

    def expired(self) -> bool:
        if self.stop_reason:
            return True
        if self.clock() - self.t0 >= self.budget_s:
            self.stop_reason = "budget"
        elif self.n_429 >= MAX_429:
            self.stop_reason = "429_stop"
        return self.stop_reason is not None

    def _note(self, was_429: bool) -> None:
        now = self.clock()
        self.recent = [(t, f) for t, f in self.recent if now - t <= R429_WINDOW_S] + [(now, was_429)]
        if not self.halved and len(self.recent) >= 20 and sum(f for _t, f in self.recent) / len(self.recent) > R429_HALVE_FRAC:
            self.rps /= 2.0
            self.halved = True

    def get(self, transport: Transport, params: dict, sleep: Callable[[float], None]) -> tuple[int | None, bytes]:
        for attempt in range(self.max_retries + 1):
            if self.expired():
                return None, b""
            wait = max(0.0, self.last_sent + 1.0 / self.rps - self.clock())
            if wait:
                sleep(wait)
            self.last_sent = self.clock()
            self.n_req += 1
            try:
                code, body, hdr = transport(params)
            except Exception:  # network failure: retried
                code, body, hdr = 0, b"", {}
            self._note(code == 429)
            if code == 429 or code >= 500 or code == 0:
                if code == 429:
                    self.n_429 += 1
                ra = (hdr or {}).get("Retry-After") or (hdr or {}).get("retry-after")
                try:
                    delay = float(ra) if ra is not None else min(BACKOFF_CAP, BACKOFF_BASE * 2 ** attempt)
                except ValueError:
                    delay = min(BACKOFF_CAP, BACKOFF_BASE * 2 ** attempt)
                sleep(min(delay, BACKOFF_CAP))
                continue
            return code, body
        return -1, b""  # retries exhausted (recorded as such, not as an http status)


def _atomic_csv_gz(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    trade_sample._atomic_csv_gz(path, df)


def _atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    trade_sample._atomic_json(path, obj)


def plan_vacuum(qs_root: Path, current_capture_id: str, seed: str, vacuum_max: int) -> dict:
    """A-rule onsets at the current capture (tight at i-1 and i from ``quote_state/``, vacuum at the current capture), seeded
    uniform draw of <= ``vacuum_max``. Data copying only: reads quote_state/ with the J4-R guard disabled (the live extractor and
    this step write rows for T_J4R too; analysis refuses them)."""
    man = json.loads((Path(qs_root) / "manifest.json").read_text())
    ents = sorted((e for e in man["captures"].values() if e.get("status") == "extracted"), key=lambda e: D.epoch(e["capture_start_utc"]))
    ids = [e["capture_id"] for e in ents]
    if current_capture_id not in ids or ids.index(current_capture_id) < 2:
        return {"status": "no_quote_state_triple", "onsets": [], "n_onsets": 0}
    k = ids.index(current_capture_id)
    sel = ents[k - 2:k + 1]
    P = V.load_quote_panel(qs_root, since=D.epoch(sel[0]["capture_start_utc"]), before=D.epoch(sel[-1]["capture_start_utc"]) + 1.0, purpose="followup_copy", j4r=(0.0, 0.0))
    u, _ex = V.detect_onsets(P)
    u = u[u["cap_i"] == P.n_caps - 2] if len(u) else u
    n = len(u)
    if not n:
        return {"status": "ok", "onsets": [], "n_onsets": 0, "inclusion_prob": None, "seed": seed}
    order = seeded_order(list(range(n)), seed + "|vacuum")[:vacuum_max]
    pick = u.iloc[sorted(order)]
    m = pick["m_idx"].to_numpy(int)
    s2 = P.mat["s2_recv"][m, P.n_caps - 1]
    onsets = [{"market_id": str(P.markets[j]), "condition_id": str(P.meta["condition_id"].to_numpy()[j]), "side": int(s), "q": float(q), "s2_epoch": (None if not np.isfinite(t) else float(t)),
               "capture_id": current_capture_id}
              for j, s, q, t in zip(m, pick["s"], pick["q"], s2, strict=True)]
    return {"status": "ok", "seed": seed, "n_onsets": int(n), "n_drawn": len(onsets), "inclusion_prob": min(1.0, vacuum_max / n), "onsets": onsets}


def run(*, snapshot_root: Path | None = None, current_dir: Path | None = None, sample_root: Path = SAMPLE_ROOT, qs_root: Path = QS_ROOT,
        out_root: Path = FOLLOWUP_ROOT, transport: Transport, frac: float = DEFAULT_FRAC, vacuum_max: int = DEFAULT_VACUUM_MAX,
        rps: float = DEFAULT_RPS, budget_s: float = DEFAULT_BUDGET_S, seed: str | None = None, key: bytes | None = None,
        sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
        now: Callable[[], float] = time.time, data_dumps: Path | None = None, data_dumps_max_gb: float | None = None,
        dir_gb: Callable[[Path], float] | None = None) -> dict:
    """One follow-up pass for the latest complete capture. Idempotent per capture id; never raises on network trouble."""
    from .creative_batch1 import _dir_gb  # noqa: PLC0415

    dir_gb = dir_gb or _dir_gb
    caps = forecast.list_complete_captures(Path(snapshot_root) if snapshot_root else forecast.SNAPSHOT_ROOT)
    if len(caps) < 1:
        return {"cb3_followup": VERSION, "stopped": "no_complete_capture"}
    cur = caps[-1] if current_dir is None else next(c for c in caps if Path(c["dir"]) == Path(current_dir))
    prev = caps[caps.index(cur) - 1] if caps.index(cur) > 0 else None
    cid = cur["capture_id"]
    out = Path(out_root) / cid
    res: dict = {"cb3_followup": VERSION, "capture_id": cid, "stopped": None}
    if data_dumps_max_gb is not None and data_dumps is not None and dir_gb(Path(data_dumps)) > data_dumps_max_gb:
        return {**res, "stopped": "refused_data_dumps_over_cap"}
    if (out / "manifest.json").exists():
        return {**res, "stopped": "already_done"}
    seed = seed or secrets.token_hex(16)
    if key is None:
        try:
            key = load_or_create_key()
        except Exception:  # without a wallet key no wallet field can be written: the pass is recorded as missing, nothing else is written
            key = None
    if key is None:
        _atomic_json(out / "manifest.json", {"version": VERSION, "capture_id": cid, "state": "missing_no_wallet_key"})
        return {**res, "stopped": "missing_no_wallet_key"}
    sample_dir = find_previous_sample(prev["capture_id"], sample_root) if prev else None
    b_markets: list[dict] = []
    pre_tr = pre_w = pre_f = None
    if sample_dir is not None:
        plan_s = json.loads((sample_dir / "plan.json").read_text())
        smap = {str(m["market_id"]): m for m in plan_s["sample"]}
        chosen = seeded_subsample(list(smap), seed, frac)
        b_markets = [smap[m] for m in chosen]
        tr, wl = _read_csv(sample_dir / "trades.csv.gz"), _read_csv(sample_dir / "wallets.csv.gz")
        pre_tr = tr[tr["market_id"].isin(chosen)] if tr is not None else None
        pre_w = wl[wl["market_id"].isin(chosen)] if wl is not None else None
        ft = _read_csv(sample_dir / "features.csv.gz")
        pre_f = ft[ft["market_id"].isin(chosen)] if ft is not None else None
    prev_vac = None
    if prev is not None:
        pv = Path(out_root) / prev["capture_id"] / "vacuum_plan.json"
        if pv.exists():
            prev_vac = json.loads(pv.read_text())
    tasks: list[dict] = [{"kind": "post", "market_id": str(m["market_id"]), "condition_id": m["condition_id"], "start": prev["_start"].timestamp() if prev else None} for m in b_markets]
    for o in (prev_vac or {}).get("onsets", []):
        if o.get("s2_epoch") is not None and o.get("condition_id"):
            tasks.append({"kind": "vacuum", "market_id": o["market_id"], "condition_id": o["condition_id"], "start": float(o["s2_epoch"])})
    tasks = seeded_order(tasks, seed)
    # Seal: plan (seed, sampled markets, request order) is durable before the first request.
    _atomic_json(out / "plan.json", {"version": VERSION, "capture_id": cid, "seed": seed, "frac": frac, "previous_capture_id": prev["capture_id"] if prev else None,
                                     "sample_dir": sample_dir.name if sample_dir else None, "n_sample_markets": len(b_markets),
                                     "inclusion_float": {str(m["market_id"]): m.get("inclusion_float") for m in b_markets},
                                     "request_order": [(t["kind"], t["market_id"]) for t in tasks], "vacuum_max": vacuum_max, "planned_utc": _fmt(now())})
    if pre_tr is not None:
        _atomic_csv_gz(out / "pre" / "trades.csv.gz", pre_tr)
    if pre_w is not None:
        _atomic_csv_gz(out / "pre" / "wallets.csv.gz", pre_w)
    if pre_f is not None:  # per-market fetch status and n_returned of the trade sample (its 500-print cap), unchanged
        _atomic_csv_gz(out / "pre" / "features.csv.gz", pre_f)
    bud = Budget(rps, budget_s, clock)
    got: dict[str, list[dict]] = {"post": [], "vacuum": []}
    meta: dict = {}
    for t in tasks:
        if bud.expired():
            meta[f"{t['kind']}:{t['market_id']}"] = {"status": "not_reached"}
            continue
        req_t = now()
        w = window_trades(transport, t["condition_id"], t["start"], req_t, sleep=sleep, budget=bud, key=key)
        for r in w["rows"]:
            r["market_id"] = t["market_id"]
        got[t["kind"]] += w["rows"]
        meta[f"{t['kind']}:{t['market_id']}"] = {"status": w["status"], "request_epoch": req_t, "window_start": t["start"], "pages": w["pages"], "page_cap": w["page_cap"],
                                                 "oldest_ts": w["oldest_ts"], "n_rows": len(w["rows"])}
    for kind in ("post", "vacuum"):
        if got[kind] or kind == "post" and tasks:
            _atomic_csv_gz(out / kind / "trades.csv.gz", pd.DataFrame(got[kind], columns=TRADE_COLS))
    vac_plan = plan_vacuum(qs_root, cid, seed, vacuum_max) if (Path(qs_root) / "manifest.json").exists() else {"status": "no_quote_state", "onsets": [], "n_onsets": 0}
    _atomic_json(out / "vacuum_plan.json", vac_plan)
    n_not = sum(1 for v in meta.values() if v["status"] == "not_reached")
    res.update(stopped=bud.stop_reason, requests=bud.n_req, n_429=bud.n_429, rps_final=bud.rps, tasks=len(tasks), not_reached=n_not,
               page_cap_hits=sum(1 for v in meta.values() if v.get("page_cap")), post_rows=len(got["post"]), vacuum_rows=len(got["vacuum"]),
               n_sample_markets=len(b_markets), vacuum_plan_onsets=vac_plan.get("n_drawn", 0))
    _atomic_json(out / "meta.json", {"version": VERSION, "request_utc_final": _fmt(now()), "markets": meta, **{k: res[k] for k in ("requests", "n_429", "rps_final")}})
    _atomic_json(out / "manifest.json", {"version": VERSION, "capture_id": cid, "state": "incomplete" if bud.stop_reason else "complete", **res})
    return res


def has_raw_address(path: Path) -> bool:
    """Test helper: True if any 0x-address-like token appears in a followup file."""
    import re

    pat = re.compile(rb"0x[0-9a-fA-F]{40}")
    for p in Path(path).rglob("*"):
        if p.is_file():
            data = p.read_bytes()
            if p.suffix == ".gz":
                data = gzip.decompress(data)
            if pat.search(data):
                return True
    return False


__all__ = ["Budget", "FOLLOWUP_ROOT", "VERSION", "find_previous_sample", "plan_vacuum", "run", "seeded_order", "seeded_subsample", "window_trades"]
