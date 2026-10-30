# ruff: noqa: E501
"""Synthetic engine trees for the LT14 tests (no real data, no network): ``engine/{meta,quotes,features,predictions/<cap>/<P>.parquet,logs/predictions-*.jsonl,champion/history.jsonl}`` with the
column names and types of LIVE_TESTS_14.md 1.2, and ``snapshots/<cap>/rows_ext.csv.gz`` sidecars. Everything is written under tmp paths."""

from __future__ import annotations

import copy
import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from astrolabe.research_lab import live_tests14_base as t

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
FEE_ON = '{"rate": 0.04, "rebateRate": 0.25}'
FEE_FREE = '{"rate": 0, "rebateRate": 0}'
Q = 65535


def slot_dt(k: int) -> datetime:
    return G0 + timedelta(hours=2 * k)


def isoz(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def cap_id(k: int) -> str:
    return slot_dt(k).strftime("%Y%m%dT%H%M%SZ") + "_syn"


def write_pq(path: Path, df: pd.DataFrame, meta: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tab = pa.Table.from_pandas(df, preserve_index=False)
    if meta:
        md = dict(tab.schema.metadata or {})
        md[b"signal_engine"] = json.dumps(meta, sort_keys=True, separators=(",", ":")).encode()
        tab = tab.replace_schema_metadata(md)
    pq.write_table(tab, path, compression="zstd")


def make_world(root: Path, slots, *, n_markets: int = 400, seed: int = 5, p_late: set | None = None, p_absent: set | None = None, no_sidecar: set | None = None, drop_next: dict | None = None,
               st_next: dict | None = None, spec_bad: set | None = None, model_id: str = t.PINNED_MODEL, late_s: float = 0.0) -> dict:
    """Write engine + snapshot trees for ``slots`` under ``root``; returns {"engine": Path, "snaps": Path, "markets": DataFrame}. ``p_late`` / ``p_absent`` / ``spec_bad`` are slot sets;
    ``no_sidecar`` slots get no sidecar file; ``drop_next`` = {slot: set of market ids absent from that slot's quotes}; ``st_next`` = {(slot, market_id): st}."""
    rng = np.random.default_rng(seed)
    eng, snaps = Path(root) / "engine", Path(root) / "snaps"
    ids = np.arange(1000, 1000 + n_markets)
    liq = np.exp(rng.uniform(np.log(300.0), np.log(5e5), n_markets))
    mk = pd.DataFrame({"market_id": ids, "liq": liq, "event_id": np.where(np.arange(n_markets) % 17 == 0, -1, 7000 + np.arange(n_markets) // 3),
                       "cat": np.where(np.arange(n_markets) % 11 == 0, "crypto", np.where(np.arange(n_markets) % 7 == 0, "sports", "politics_fees")),
                       "slug": [f'["fam{i % 9}"]' for i in range(n_markets)], "neg": (np.arange(n_markets) % 5 == 0).astype(float)})
    mid = np.clip(0.5 + rng.normal(0, 0.15, n_markets), 0.05, 0.95)
    log_lines: list[dict] = []
    for k in slots:
        mid = np.clip(mid + rng.normal(0, 0.01, n_markets), 0.05, 0.95)
        half = np.round(rng.uniform(0.005, 0.02, n_markets), 3)
        bid, ask = np.round(mid - half, 4), np.round(mid + half, 4)
        start = slot_dt(k)
        cid = cap_id(k)
        fin = start + timedelta(minutes=10)
        meta = {"capture_id": cid, "slot": int(k), "started_utc": isoz(start), "finished_utc": isoz(fin), "features_version": "se-features-v1"}
        (eng / "meta").mkdir(parents=True, exist_ok=True)
        (eng / "meta" / f"{cid}.json").write_text(json.dumps(meta))
        t_off = rng.uniform(40, 120, n_markets).astype(np.float32)
        st = np.zeros(n_markets, np.int8)
        for (sl, m), v in (st_next or {}).items():
            if sl == k:
                st[int(np.nonzero(ids == m)[0][0])] = v
        ok = st == 0
        q = pd.DataFrame({"market_id": ids.astype(np.int64), "t_off": t_off, "bid": np.where(ok, bid, np.nan).astype(np.float32), "ask": np.where(ok, ask, np.nan).astype(np.float32), "st": st})
        keep = ~np.isin(ids, list((drop_next or {}).get(k, ())))
        write_pq(eng / "quotes" / f"{cid}.parquet", q[keep].reset_index(drop=True), {"capture_id": cid, "slot": int(k)})
        t_row = (start.timestamp() + t_off).astype(np.float64)
        feat = pd.DataFrame({"market_id": ids.astype(np.int64), "event_id": mk["event_id"].to_numpy(np.int64), "category": mk["cat"].to_numpy(), "t_row": t_row, "end_ts": np.full(n_markets, np.nan),
                             "ms_mid": ((bid + ask) / 2.0).astype(np.float32), "ms_spread": (ask - bid).astype(np.float32), "ms_log_liq": np.log1p(liq).astype(np.float32),
                             "ms_hours_to_end": rng.uniform(5, 500, n_markets).astype(np.float32), "ms_rv24": rng.uniform(0.001, 0.03, n_markets).astype(np.float32),
                             "ms_tick": np.full(n_markets, 0.01, np.float32), "ms_neg_risk": mk["neg"].to_numpy(np.float32), "mo_d2h": rng.normal(0, 0.01, n_markets).astype(np.float32)})
        feat = feat[ok].reset_index(drop=True)
        write_pq(eng / "features" / f"{cid}.parquet", feat, {"capture_id": cid, "slot": int(k)})
        n = len(feat)
        pu = np.clip(0.33 + 0.4 * rng.normal(0, 0.4, n), 0, 0.6)
        pdn = np.clip(0.33 - 0.4 * rng.normal(0, 0.4, n), 0, 0.6)
        elig = np.where(rng.random(n) < 0.95, 1, 0).astype(np.uint8)
        pred = pd.DataFrame({"elig": elig, "dir_2h_dn": np.where(elig & 1, np.floor(pdn * Q), 0).astype(np.uint16), "dir_2h_up": np.where(elig & 1, np.floor(pu * Q), 0).astype(np.uint16)})
        if k not in (p_absent or set()):
            fsha = t.b.sha256_file(eng / "features" / f"{cid}.parquet")
            spec_sha = "0" * 64 if k in (spec_bad or set()) else t.PINNED_SPEC_SHA256
            pm = {"capture_id": cid, "slot": int(k), "model_id": model_id, "spec_sha256": spec_sha, "fit_id": f"fit{k // 12}", "features_sha256": fsha, "n_rows": int(n)}
            pp = eng / "predictions" / cid / f"{model_id}.parquet"
            write_pq(pp, pred, pm)
            w = fin + timedelta(minutes=5) if k not in (p_late or set()) else slot_dt(k + 1) + timedelta(seconds=late_s + 5)
            log_lines.append({"capture_id": cid, "slot": int(k), "model_id": model_id, "spec_sha256": spec_sha, "fit_id": f"fit{k // 12}", "sha256": t.b.sha256_file(pp), "written_utc": isoz(w), "n_rows": int(n)})
        if k not in (no_sidecar or set()):
            d = snaps / cid
            d.mkdir(parents=True, exist_ok=True)
            sc = pd.DataFrame({"market_id": ids, "fee_type": np.where(mk["cat"] == "sports", "sports_fees", np.where(mk["cat"] == "crypto", "crypto_fees", "politics_fees")),
                               "fee_category": np.where(mk["cat"] == "sports", "sports", np.where(mk["cat"] == "crypto", "crypto", "politics")), "series_slugs": mk["slug"],
                               "fee_schedule": np.where(np.arange(n_markets) % 3 == 0, FEE_FREE, FEE_ON), "fees_enabled": "true"})
            with gzip.open(d / "rows_ext.csv.gz", "wt") as fh:
                sc.to_csv(fh, index=False)
    (eng / "logs").mkdir(parents=True, exist_ok=True)
    by_day: dict[str, list[dict]] = {}
    for ln in log_lines:
        by_day.setdefault(ln["written_utc"][:10].replace("-", ""), []).append(ln)
    for day, lines in by_day.items():
        (eng / "logs" / f"predictions-{day}.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    (eng / "champion").mkdir(parents=True, exist_ok=True)
    (eng / "champion" / "history.jsonl").write_text(json.dumps({"champion": t.PINNED_MODEL, "utc": "2026-10-21T00:00:00Z"}) + "\n")
    return {"engine": eng, "snaps": snaps, "markets": mk}


def loose_spec(first: int, last: int) -> dict:
    """Every census minimum made trivial and every maximum huge, so a rich synthetic world passes the CH262 block; a test then makes ONE threshold impossible."""
    spec = t.load_spec()
    g = spec["census_gates"]
    for key in list(g):
        if key.endswith("_min") and not isinstance(g[key], dict):
            g[key] = 0
        elif key.endswith("_max") or key.endswith("_max_points") or key.endswith("_max_c"):
            g[key] = 1e9
    g["tier_finite_min"], g["mid_check_share_min"] = 0.0, 1.0
    g["venue_clock_max"], g["unavailable_gap_max_points"] = 1.0, 100.0
    ci = spec["census_inputs"]
    ci["span"] = {"start_utc": isoz(slot_dt(first)), "end_utc": isoz(slot_dt(last + 1)), "first_slot_utc": isoz(slot_dt(first)), "last_slot_utc": isoz(slot_dt(last))}
    ci["expected_origins"] = last - first + 1
    ci["min_covered_days"] = 0.5
    ci["p_ontime_min"] = 0.5
    ci["refuse_at_or_after_utc"] = isoz(slot_dt(last + 40))
    ci["seal_not_before_utc"] = isoz(slot_dt(first))
    spec["mde"]["de_floor"] = 5.0
    return copy.deepcopy(spec)


def write_ledger(path: Path) -> Path:
    """A tmp ledger carrying the freeze line and the pinned-P line the code expects (the real ledger entry is the coordinator's)."""
    path.write_text(f"- **{t.LEDGER_FREEZE_MARKER}:** `LIVE_TESTS_14.md` at **485c63dd**, sha256 **`{t.DESIGN_TEXT_SHA256}`**, 802 lines.\n"
                    f"- **{t.LEDGER_P_MARKER} = `{t.PINNED_MODEL}`, spec_sha256 `{t.PINNED_SPEC_SHA256}`** (the engine's champion).\n")
    return path
