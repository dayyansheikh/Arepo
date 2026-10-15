"""CB1-F data jobs: the ``h5_cb1_ladders`` fetch, the h5 seal and the seal verifier
(docs/research_lab/CREATIVE_BATCH_1.md, CB1-F). The ``h5_cb1`` market backfill itself is
``scripts/backfill_history.py run --strata-profile cb1 ...``.

    python scripts/cb1_h5.py ladders-fetch --run-id h5_cb1_ladders --start 2024-01-01 \\
        --end 2025-05-31 --exclude-runs h1_first,h2_main,h3_power --rps 4 --disk-cap-gb 0.15 \\
        --budget-min 150
    python scripts/cb1_h5.py seal --run-id h5_cb1,h5_cb1_ladders
    python scripts/cb1_h5.py verify-seal --run-id h5_cb1,h5_cb1_ladders
    python scripts/cb1_h5.py selfcheck                      # synthetic, no network, exit 0 = ok
    python scripts/cb1_h5.py count-h2-coverage              # read-only disclosure count for h2_main

``seal`` also writes the single committed copy ``docs/research_lab/seals/<run_id>_SEAL.json``
(see ``astrolabe.research_lab.h5_seal``); a Claude session commits it.

``ladders-fetch`` prints one JSON line containing ``ladders_fetch_complete`` or ``probe_failed``
when finished (the queue's repeat regex); a budget stop exits 0 and a re-run resumes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from astrolabe.research_lab import h5_ladders, h5_seal
from astrolabe.research_lab import history_backfill as hb

DEFAULT_IFH2 = hb.DEFAULT_ROOT.parent / "if_h2" / "ladders.jsonl.gz"


def _union_gap(wins: list[tuple[float, float]], a: float, b: float) -> bool:
    """True when ``[a, b]`` is not fully covered by the union of ``wins`` (1 s tolerance)."""
    cur = a
    for x, y in sorted(wins):
        if x > cur + 1:
            break
        cur = max(cur, y)
        if cur >= b - 1:
            return False
    return cur < b - 1


def count_h2_coverage(root: Path, run_id: str = "h2_main", max_days: int = 120) -> dict:
    """Disclosure only. For each done unit of ``<root>/<run_id>`` (local files only), whether its
    fetched price windows (``progress.jsonl`` ``window`` and ``head_window``) cover (i) the
    end-anchored span ``[max(created, end+1d-max_days), end+1d]`` and (ii) the whole ``[created,
    end+1d]``, with ``end+1d`` clipped to the request clock. Units without a known end are counted
    separately. Counts are by status (closed / active). Nothing is written or refetched."""
    import pandas as pd

    rdir = Path(root) / run_id
    sample = pd.read_csv(rdir / "sample.csv.gz", dtype={"market_id": str}, keep_default_na=False)
    man = json.loads((rdir / "manifest.json").read_text())
    now = datetime.strptime(man["request_clock_now"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC).timestamp()
    done: dict[str, dict] = {}
    with open(rdir / "progress.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                done[rec["market_id"]] = rec
    out: dict = {"run_id": run_id, "request_clock_now": man["request_clock_now"], "by_status": {}}
    for row in sample.to_dict("records"):
        rec = done.get(row["market_id"])
        if not rec or rec.get("status") != "done":
            continue
        st = "closed" if str(row["closed"]) in ("1", "True", "true", "1.0") else "active"
        c = out["by_status"].setdefault(st, {"units": 0, "no_end": 0, "miss_end_anchor": 0,
                                             "miss_full_interval": 0})
        c["units"] += 1
        try:
            start, end = float(row["start_epoch"]), float(row["end_epoch"])
        except (TypeError, ValueError):
            start = end = float("nan")
        if math.isnan(start) or math.isnan(end):
            c["no_end"] += 1
            continue
        e = min(end + 86400, now)
        wins = [tuple(w) for w in (rec.get("window"), rec.get("head_window")) if w]
        if _union_gap(wins, max(start, e - max_days * 86400), e):
            c["miss_end_anchor"] += 1
        if _union_gap(wins, start, e):
            c["miss_full_interval"] += 1
    return out


def check_window_logic() -> None:
    """Synthetic assertions of the fixed h5 window and trade-cap logic (no network, no files)."""
    day = 86400
    now = 1_790_000_000.0
    hb_ = hb

    def row(closed, close_d, end_d=-150, start_d=-200):
        return {"closed": int(closed), "start_epoch": now + start_d * day,
                "close_epoch": now + close_d * day if closed else float("nan"),
                "end_epoch": now + end_d * day}

    # coverage of [created, end+1d] must not depend on the close time (or on being active)
    for r in (row(1, -20), row(1, -100), row(1, -149), row(1, -200), row(0, 0)):
        w = hb_.price_windows(r, now, 120, "close_or_end_max", 8)
        a, b = r["start_epoch"], r["end_epoch"] + day
        assert not _union_gap([(x, y) for x, y in w], a, b), (r, w)
    # an active market whose end passed 130 days ago still has its end window
    act = row(0, 0, end_d=-130, start_d=-400)
    w = hb_.price_windows(act, now, 120, "close_or_end_max", 8)
    assert not _union_gap(w, act["end_epoch"] + day - 120 * day, act["end_epoch"] + day)
    # the default (h2) plan is untouched
    r = row(1, -20)
    assert hb_.price_windows(r, now, 120) == [hb_.price_window(r, now, 120)]
    # trade cap at T_fetch and T_seal refusal
    class _L:
        def get(self, url, params):
            if params["offset"]:
                return 200, []
            return 200, [{"timestamp": ts, "side": "BUY", "size": 1, "price": 0.5,
                          "outcomeIndex": 0, "proxyWallet": "0x1", "transactionHash": str(ts),
                          "asset": "a"} for ts in (100, 200, 300)]
    rows, st = hb_.fetch_trades(_L(), "c", b"k" * 32, 100, ts_cap=250)
    assert [x[0] for x in rows] == [100, 200] and st["dropped_post_cap"] == 1
    with tempfile.TemporaryDirectory() as td:
        m = hb_.run(Path(td), "h5_cb1", lambda *a: (200, b"[]", {}), strata_profile="cb1",
                    wall_clock=lambda: hb_.T_SEAL_EPOCH + 1)
        assert str(m["stopped"]).startswith("t_seal_passed")


def _day(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["ladders-fetch", "seal", "verify-seal", "selfcheck",
                                       "count-h2-coverage"])
    ap.add_argument("--run-id", default="", help="comma-separated for seal / verify-seal")
    ap.add_argument("--seals-dir", default=None, help="override docs/research_lab/seals")
    ap.add_argument("--root", default=str(hb.DEFAULT_ROOT))
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-05-31")
    ap.add_argument("--exclude-runs", default="h1_first,h2_main,h3_power")
    ap.add_argument("--exclude-ifh2", default=str(DEFAULT_IFH2),
                    help="IF-H2 ladders.jsonl.gz (event and rung ids; exclusion only)")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--disk-cap-gb", type=float, default=0.15)
    ap.add_argument("--budget-min", type=float, default=None)
    ap.add_argument("--max-trades", type=int, default=10000)
    a = ap.parse_args(argv)
    root = Path(a.root)
    runs = [r for r in a.run_id.split(",") if r]
    if a.cmd == "selfcheck":
        check_window_logic()
        print(json.dumps({"selfcheck": "ok"}))
        return 0
    if a.cmd == "count-h2-coverage":
        print(json.dumps(count_h2_coverage(root, a.run_id or "h2_main"), sort_keys=True))
        return 0
    if not runs:
        print("--run-id is required")
        return 2
    if a.cmd == "ladders-fetch":
        if len(runs) != 1:
            print("ladders-fetch takes exactly one run id")
            return 2
        m = h5_ladders.ladders_fetch(
            root, runs[0], hb.httpx_transport(), start=_day(a.start), end=_day(a.end),
            exclude_runs=[r for r in a.exclude_runs.split(",") if r],
            ifh2_ladder_file=Path(a.exclude_ifh2), rps=a.rps,
            disk_cap=int(a.disk_cap_gb * 1024**3), budget_min=a.budget_min,
            max_trades=a.max_trades, live_check=hb.live_pass_or_lock)
        out = {k: m.get(k) for k in ("counts", "requests", "disk_bytes", "stopped", "probe",
                                     "n_ladders", "n_rungs", "token", "elapsed_s_this_session")}
        if m.get("token"):
            out["status"] = m["token"]
        print(json.dumps(out, default=float))
        return 0
    rc = 0
    for rid in runs:
        try:
            if a.cmd == "seal":
                seal = h5_seal.seal_run(root / rid)
                copy = h5_seal.write_committed_copy(
                    root / rid, Path(a.seals_dir) if a.seals_dir else None)
                print(json.dumps({"run_id": rid, "sealed": True, "committed_copy": str(copy),
                                  "listing_sha256": seal["listing_sha256"],
                                  "n_files": seal["n_files"], "total_bytes": seal["total_bytes"]}))
            else:
                seal = h5_seal.verify_seal(root / rid)
                print(json.dumps({"run_id": rid, "verified": True,
                                  "listing_sha256": seal["listing_sha256"]}))
        except h5_seal.SealError as exc:
            print(json.dumps({"run_id": rid, "error": str(exc)}))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
