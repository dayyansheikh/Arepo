"""Hypothesis battery 1 (HB1) runner: EXPLORATORY_HISTORICAL development screen on h2_main.

Subcommands (see ``docs/research_lab/HYPOTHESIS_BATTERY_1.md``):

    meta       fetch Gamma event metadata for the sampled events (text, members; no outcomes)
    siblings   fetch 10-minute price series for neg-risk / ladder siblings (bounded)
    features   build the battery feature table (no targets are read)
    dryrun     run the whole test pipeline on GLOBALLY SHUFFLED targets (code check, no outcome)
    run        the declared battery: discovery fits, judgement tests, BY, robustness, economics

Nothing here is prospective, confirmatory, or an edge / profitability claim.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd  # noqa: E402

from astrolabe.research_lab import battery_data as bd  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402

RUN_DIR = ROOT / "data-dumps" / "research_lab" / "history" / "h2_main"
OUT = RUN_DIR / "battery1"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def limiter(rps: float) -> hb.Limiter:
    return hb.Limiter(hb.httpx_transport(), rps=rps, live_check=hb.live_pass_running_anchored)


def cmd_meta(a) -> int:
    s = pd.read_csv(RUN_DIR / "sample.csv.gz", dtype=str, keep_default_na=False)
    ids = sorted({e for e in s["event_id"] if e})
    res = bd.fetch_event_meta(limiter(a.rps), ids, OUT / "events_meta.jsonl.gz")
    log(json.dumps({k: (v if k != "missing" else len(v)) for k, v in res.items()}))
    (OUT / "events_meta.manifest.json").write_text(
        json.dumps(
            {
                "version": bd.META_VERSION,
                "events": res["events"],
                "missing": res["missing"],
                "requests": res["requests"],
                "utc": hb.utc_iso(),
                "source": bd.GAMMA_EVENTS,
                "kept_fields": "creation-time text and structure; no outcomePrices",
                "evidence_role": "exploratory_historical",
            },
            indent=1,
        )
    )
    return 0


def traded_spans() -> dict[str, tuple[float, float]]:
    p = pd.read_csv(
        RUN_DIR / "panel_H2h.csv.gz",
        usecols=["market_id", "t_i", "traded_before_t"],
        dtype={"market_id": str},
    )
    p = p[p["traded_before_t"] != 0]
    g = p.groupby("market_id")["t_i"].agg(["min", "max"])
    return {m: (float(r["min"]), float(r["max"])) for m, r in g.iterrows()}


def load_events() -> dict[str, dict]:
    return {e["event_id"]: e for e in bd.load_jsonl_gz(OUT / "events_meta.jsonl.gz")}


def cmd_siblings(a) -> int:
    s = pd.read_csv(RUN_DIR / "sample.csv.gz", dtype=str, keep_default_na=False)
    events = load_events()
    meta = bd.market_meta_table(s, events)
    meta.to_csv(OUT / "market_meta.csv.gz", index=False, compression="gzip")
    spans = traded_spans()
    tg = bd.sibling_targets(meta, events, spans)
    est = sum(max(1, int((t["hi"] - t["lo"]) // (14 * 86400)) + 1) for t in tg)
    log(f"sibling targets {len(tg)}, estimated requests {est}")
    if a.plan_only:
        return 0
    res = bd.fetch_sibling_prices(limiter(a.rps), tg, OUT / "siblings", a.max_requests, log=log)
    log(json.dumps(res))
    (OUT / "siblings.manifest.json").write_text(
        json.dumps(
            {
                **res,
                "estimated_requests": est,
                "nr_max_members": bd.NR_MAX_MEMBERS,
                "ladder_max_rungs": bd.LADDER_MAX_RUNGS,
                "lookback_s": bd.LOOKBACK_S,
                "utc": hb.utc_iso(),
                "fidelity_min": hb.FIDELITY_MIN,
                "evidence_role": "exploratory_historical",
            },
            indent=1,
        )
    )
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("meta")
    m.add_argument("--rps", type=float, default=4.0)
    s = sub.add_parser("siblings")
    s.add_argument("--rps", type=float, default=4.0)
    s.add_argument("--max-requests", type=int, default=40000)
    s.add_argument("--plan-only", action="store_true")
    for name in ("features", "dryrun", "run"):
        p = sub.add_parser(name)
        p.add_argument("--n-boot", type=int, default=2000)
        p.add_argument("--threads", type=int, default=4)
        p.add_argument("--only", default="", help="comma list of hypothesis ids (debug only)")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "meta":
        return cmd_meta(a)
    if a.cmd == "siblings":
        return cmd_siblings(a)
    from astrolabe.research_lab import battery  # heavy imports only when needed

    return battery.cli(a.cmd, a, OUT, RUN_DIR, log)


if __name__ == "__main__":
    sys.exit(main())
