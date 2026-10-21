# ruff: noqa: E501
"""A SYNTHETIC CB18 census world (captures, sidecars, sweeps, samples and a matching census seal) for the CB18 census tests. No real data-dumps file is opened.

Layout mirrors the archive: <root>/data-dumps/research_lab/cb18_census/restore/data-dumps/research_lab/{snapshots,book_sweeps,trade_samples}/<id>/... and the seal pins every file with
its sha256 (tests only; the real seal copies release hashes). Markets:

m0 quiet dormant (non-sports) | m1 silent every third slot | m2 mover | m3 chg_1h-only changes | m4 uma non-empty | m5 sports quiet | m6 exits after 10-13T18:31Z (tail mid)
m7 last present 10-13T22:31Z (gap-adjacent exit) | m8 absent 10-12T10:31Z and 12:31Z then back (exit + re-appearance) | m9 / m10 parallel re-centerings on 10-16/17 (fade / follow
trades in the next sample) | m11 volume oscillates across rank 10 (F) | e12..e21 filler events for the F ranks
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from astrolabe.research_lab import book_sweep, ext_sidecar, extract, trade_sample
from astrolabe.research_lab import cb18_rules_pre as r

GRID0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
UNAVAIL = {datetime.fromisoformat(s.replace("Z", "+00:00")) for s in r.UNAVAILABLE_CAPTURE_SLOTS}
FIRST = datetime(2026, 10, 11, 22, 31, tzinfo=UTC)
LAST = datetime(2026, 10, 17, 22, 31, tzinfo=UTC)
OLD_STAMP_MS = int(datetime(2026, 10, 1, tzinfo=UTC).timestamp() * 1000)
N_FILLER = 10


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def slots() -> list[datetime]:
    out, t = [], FIRST
    while t <= LAST:
        if t not in UNAVAIL:
            out.append(t)
        t += timedelta(hours=2)
    return out


def _gz_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in cols})


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def market_state(i: int, s: datetime, n: int) -> dict | None:
    """Row content of market i at slot s (n = slot ordinal); None = absent from the listing."""
    mid = f"m{i}"
    if i == 6 and s > datetime(2026, 10, 13, 18, 31, tzinfo=UTC):
        return None
    if i == 7 and s > datetime(2026, 10, 13, 22, 31, tzinfo=UTC):
        return None
    if i == 8 and s in (datetime(2026, 10, 12, 10, 31, tzinfo=UTC), datetime(2026, 10, 12, 12, 31, tzinfo=UTC)):
        return None
    bid, ask, upd = 0.40, 0.42, "2026-10-01T00:00:00Z"
    chg1h, vol, uma, fee_type, cat = "0.001", 1000.0, "[]", "politics_fees", "politics"
    if i == 1:
        upd = iso(s - timedelta(hours=2 * (n % 3)) + timedelta(seconds=30))  # bumps when the ordinal reaches a multiple of 3 (silent), equal otherwise (quiet)
    if i == 2:
        bid, ask = (0.40, 0.42) if n % 2 else (0.41, 0.43)
        upd = iso(s + timedelta(seconds=20))
    if i == 3:
        chg1h = f"{0.001 * (n % 5):.3f}"
    if i == 4:
        uma = '["proposed"]'
    if i == 5:
        fee_type, cat = "sports_fees_v2", "sports"
    if i == 6:
        bid, ask = 0.99, 1.0
    if i in (9, 10) and s.day in (16, 17) and n % 4 == 0:
        bid, ask = 0.41, 0.43  # parallel +1c re-centering at this slot (quote-only: ltp and volume unchanged)
    if i == 11:
        vol = 50.0 if n % 2 else 5000.0
    if i >= 12:
        vol = 2000.0 - 10.0 * i
    return {"market_id": mid, "condition_id": f"c{i}", "event_id": f"e{i}", "best_bid": bid, "best_ask": ask, "spread": round(ask - bid, 10), "last_trade_price": 0.41,
            "chg_1h": chg1h, "chg_1d": "0.002", "chg_1w": "0.003", "liquidity": 500.0, "volume24hr": vol, "end_date": "2026-12-31T00:00:00Z", "updated_at": upd,
            "clob_token_id_0": f"t{i}a", "clob_token_id_1": f"t{i}b", "neg_risk": 0, "closed": False, "active": True, "binary": 1, "uma": uma, "fee_type": fee_type, "fee_category": cat}


def build_world(tmp: Path) -> dict:
    base = tmp / "data-dumps" / "research_lab" / "cb18_census" / "restore" / "data-dumps" / "research_lab"
    snaps, sweeps, samples = base / "snapshots", base / "book_sweeps", base / "trade_samples"
    files: dict[str, dict] = {}
    caps: dict[datetime, str] = {}
    sl = slots()
    n_markets = 12 + N_FILLER
    for n, s in enumerate(sl):
        cid = f"{stamp(s + timedelta(seconds=2))}_{n:08x}"
        caps[s] = cid
        d = snaps / cid
        recv = iso(s + timedelta(seconds=90))
        rows, ext = [], []
        for i in range(n_markets):
            st = market_state(i, s, n)
            if st is None:
                continue
            rows.append({**{k: st.get(k) for k in extract.COLUMNS}, "capture_id": cid, "capture_start_utc": iso(s), "received_utc": recv, "dup_count": 0})
            ext.append({"capture_id": cid, "received_utc": recv, "page_index": 0, "market_id": st["market_id"], "condition_id": st["condition_id"], "clob_token_id_0": st["clob_token_id_0"],
                        "clob_token_id_1": st["clob_token_id_1"], "event_id": st["event_id"], "fee_type": st["fee_type"], "fee_category": st["fee_category"], "fees_enabled": 1,
                        "taker_base_fee": 0.0, "order_price_min_tick_size": 0.01, "order_min_size": 5.0, "uma_resolution_statuses": st["uma"], "event_comment_count": 3,
                        "series_slugs": None, "clob_rewards": None, "fee_schedule": None})
        _gz_csv(d / "rows.csv.gz", extract.COLUMNS, rows)
        _gz_csv(d / "rows_ext.csv.gz", ext_sidecar.COLUMNS, ext)
        (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "started_utc": iso(s), "state": "complete", "row_count": len(rows)}))
        (d / "ext_manifest.json").write_text(json.dumps({"capture_id": cid, "sidecar_status": "complete", "row_count": len(ext)}))
        for fn in ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json", "ext_manifest.json"):
            files[f"data-dumps/research_lab/snapshots/{cid}/{fn}"] = {"sha256": _sha(d / fn), "release": "synthetic", "job": "q0500"}
        if s.day in (15, 16) and s.month == 10:
            for si in (0, 1):
                sid = f"{stamp(s + timedelta(minutes=6 + si))}_{n:04x}{si:04x}"
                sd = sweeps / sid
                srows = []
                for i in range(n_markets):
                    st = market_state(i, s, n)
                    if st is None:
                        continue
                    book_ms = OLD_STAMP_MS if i not in (2, 9, 10) else int((s + timedelta(minutes=1)).timestamp() * 1000)
                    srows.append({"sweep_id": sid, "token_id": st["clob_token_id_0"], "market_id": st["market_id"], "batch_index": 0,
                                  "batch_receipt_utc": iso(s + timedelta(minutes=6 + si)), "book_timestamp": book_ms, "state": "ok"})
                _gz_csv(sd / "rows.csv.gz", book_sweep.ROW_COLUMNS, srows)
                (sd / "manifest.json").write_text(json.dumps({"sweep_id": sid, "series_index": si, "snapshot_id": cid, "state": "complete"}))
                for fn in ("rows.csv.gz", "manifest.json"):
                    files[f"data-dumps/research_lab/book_sweeps/{sid}/{fn}"] = {"sha256": _sha(sd / fn), "release": "synthetic", "job": "q0500"}
    # samples: every slot of 10-16/17 except 10-17T04:31Z (the unsealed one)
    sample_slots = [s for s in sl if s.day in (16, 17) and not (s.day == 17 and s.hour == 4)]
    for n, s in enumerate(sample_slots):
        k_ord = sl.index(s)
        sid = f"{stamp(s + timedelta(minutes=9))}_{n:08x}"
        sd = samples / sid
        sd.mkdir(parents=True, exist_ok=True)
        members = [i for i in range(n_markets) if market_state(i, s, k_ord) is not None and i not in (5,)]
        origin = iso(s + timedelta(seconds=90))
        plan = {"sample_id": sid, "frame": "active", "sample": [{"market_id": f"m{i}", "condition_id": f"c{i}", "stratum": i % 4, "origin_utc": origin, "token0": f"t{i}a"} for i in members]}
        (sd / "plan.json").write_text(json.dumps(plan))
        (sd / "manifest.json").write_text(json.dumps({"sample_id": sid, "snapshot_id": caps[s], "frame": "active", "state": "complete"}))
        feats, trades = [], []
        t_prev = (s - timedelta(hours=2) + timedelta(seconds=90)).timestamp()
        t_now = (s + timedelta(seconds=90)).timestamp()
        for i in members:
            feats.append({"market_id": f"m{i}", "condition_id": f"c{i}", "stratum": i % 4, "origin_utc": origin, "status": "ok", "n_returned": 20, "trades_truncated": False})
            for j in range(4):  # rows inside (t_{k-1}, t_k] and [t - 6 h, t)
                ts = int(t_prev + 600 + 900 * j)
                side = "BUY"
                if i == 9:
                    side = "SELL"  # against the +1c re-centering of the previous slot: fade
                trades.append({"market_id": f"m{i}", "condition_id": f"c{i}", "ts": ts, "side": side, "price": 0.42, "size": 10.0, "outcome_index": 0, "asset": f"t{i}a", "tx_hash": f"0x{i}{n}{j}"})
            if i == 0:  # a race: two rows, same second, different tx; and a same-tx pair (not a race)
                ts = int(t_now - 3000)
                trades += [{"market_id": "m0", "condition_id": "c0", "ts": ts, "side": "BUY", "price": 0.42, "size": 5.0, "outcome_index": 0, "asset": "t0a", "tx_hash": "0xaa"},
                           {"market_id": "m0", "condition_id": "c0", "ts": ts, "side": "BUY", "price": 0.42, "size": 5.0, "outcome_index": 0, "asset": "t0a", "tx_hash": "0xbb"},
                           {"market_id": "m0", "condition_id": "c0", "ts": ts + 7, "side": "SELL", "price": 0.41, "size": 1.0, "outcome_index": 0, "asset": "t0a", "tx_hash": "0xcc"},
                           {"market_id": "m0", "condition_id": "c0", "ts": ts + 7, "side": "SELL", "price": 0.41, "size": 2.0, "outcome_index": 0, "asset": "t0a", "tx_hash": "0xcc"}]
        _gz_csv(sd / "features.csv.gz", trade_sample.FEATURE_COLS, feats)
        _gz_csv(sd / "trades.csv.gz", trade_sample.TRADE_COLS, trades)
        for fn in ("manifest.json", "plan.json", "features.csv.gz", "trades.csv.gz"):
            files[f"data-dumps/research_lab/trade_samples/{sid}/{fn}"] = {"sha256": _sha(sd / fn), "release": "synthetic", "job": "q0501"}
    seal = {"purpose": "SYNTHETIC test seal", "rules_version": r.RULES_VERSION, "releases": {}, "jobs": {}, "files": files}
    seal_path = tmp / "seals" / r.CENSUS_INPUTS_SEAL
    seal_path.parent.mkdir(parents=True, exist_ok=True)
    seal_path.write_text(json.dumps(seal, indent=1, sort_keys=True))
    return {"base": base, "snapshots": snaps, "sweeps": sweeps, "samples": samples, "seal": seal, "seal_path": seal_path, "caps": caps, "out_dir": tmp / "data-dumps" / "research_lab" / "cb18_census"}
