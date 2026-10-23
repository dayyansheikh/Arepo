# ruff: noqa: E501
"""AREPO signal engine v1 runner (docs/research_lab/signal_engine/DESIGN_V1.md).

Subcommands (each prints ONE JSON line starting with its marker; exit 75 = nothing to do / not due / disk guard,
so the queue waits 30 min without counting an attempt):

    features    [--max-items 4]        new complete captures -> quotes/, features/, meta/ (write-once; no network)
    predict     [--max-items 4]        every active model predicts every eligible market of new captures (write-once)
    tick        [--max-items 4]        features, predict, then the champion's signal feed (the per-capture job)
    refit       [--min-interval-h 20]  daily walk-forward refit of every active model (fit_time = now)
    resolve     [--max-requests 300]   Gamma resolution labels for markets past their scheduled end (network)
    score       [--min-interval-h 20]  resolve, prospective scoring, daily leaderboard, promotion rule, dashboard.json
    walkforward [--max-test-days 7]    development/historical walk-forward (separate from prospective scores)
    status                             counts only

Research tooling: no trades, no edge claims. Never reads E-test outcome files.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.signal_engine import config as C  # noqa: E402
from astrolabe.signal_engine import store as S  # noqa: E402


def out(marker: str, payload: dict, code: int) -> int:
    payload = {"marker": marker, "exit": code, "peak_rss_mb": S.peak_rss_mb(), **payload}
    print(f"{marker} " + json.dumps(S.clean_json(payload), sort_keys=True, default=str))
    return code


def last_time(paths: S.Paths, kind: str, field: str, now: float) -> float:
    rows = S.read_logs(paths, kind, now - 4 * 86400)
    ts = [S.epoch(r.get(field)) for r in rows]
    ts = [t for t in ts if math.isfinite(t)]
    return max(ts) if ts else -math.inf


def cmd_features(paths, args) -> tuple[dict, int]:
    from astrolabe.signal_engine import aux as A
    from astrolabe.signal_engine import features as F

    r = F.run_features(paths, max_items=args.max_items)
    # auxiliary families (aux.py) for the captures just written and any backlog whose rows still exist. The budget
    # covers every family of each new capture in the same run (newest first): with 2 x max_items (4 at a pass's tick)
    # the 5th and later families waited for the next pass, after the capture's 2 h target had started (2026-10-22)
    r["aux"] = A.run_aux(paths, max_items=max(len(A.AUX_FAMILIES) * args.max_items, 4))
    return r, 0 if (r["written"] or r["aux"]["written"]) else C.TEMPFAIL


def cmd_predict(paths, args) -> tuple[dict, int]:
    from astrolabe.signal_engine import predict as P
    from astrolabe.signal_engine import specs as SP

    reg = SP.load_registry(paths.spec_dir)
    r = P.run_predict(paths, reg, max_items=args.max_items)
    return r, 0 if r["written"] else C.TEMPFAIL


def cmd_tick(paths, args) -> tuple[dict, int]:
    f, _ = cmd_features(paths, args)
    p, _ = cmd_predict(paths, args)
    res = {"features": f, "predict": p}
    try:  # per-market signal feed from the champion's newest prediction (DESIGN_V1 §27); never fails the tick
        from astrolabe.signal_engine import signal_feed as SF
        from astrolabe.signal_engine import specs as SP

        res["feed"] = SF.write_feed(paths, SP.load_registry(paths.spec_dir), S.now_ts(),
                                    fetch=None if args.no_feed_titles else SF.fetch_titles)
    except Exception as exc:  # noqa: BLE001
        res["feed_error"] = f"{type(exc).__name__}: {exc}"[:300]
    return res, 0 if (f["written"] or f["aux"]["written"] or p["written"]) else C.TEMPFAIL


def cmd_refit(paths, args) -> tuple[dict, int]:
    now = S.now_ts()
    last = last_time(paths, "fits", "fit_time", now)
    if not args.force and now - last < args.min_interval_h * 3600:
        return {"due": False, "last_fit": S.iso_s(last)}, C.TEMPFAIL
    from astrolabe.signal_engine import specs as SP
    from astrolabe.signal_engine import training as T

    reg = SP.load_registry(paths.spec_dir)
    fit_time = math.floor(now / 60) * 60.0
    if args.fit_time:  # dry runs / backfill only: an earlier fit time sees less data, never more
        fit_time = min(fit_time, S.epoch(args.fit_time))
    r = T.refit_all(paths, reg, fit_time, now)
    S.append_log(paths, "runs", [{"cmd": "refit", **r["summary"]}])
    return r["summary"], 0


def cmd_resolve(paths, args) -> tuple[dict, int]:
    from astrolabe.research_lab import calibration
    from astrolabe.signal_engine import labels as L

    now = S.now_ts()
    state = S.load_state(paths, "labels")
    index = S.load_index(paths)
    cand = L.resolution_candidates(paths, index, now, state)
    S.save_state(paths, state, "labels")
    res = L.load_resolutions(paths)
    due = L.due_for_fetch(cand, res, now)
    if not due or args.max_requests <= 0:
        return {"candidates": len(cand), "due": len(due), "fetched": {}}, 0
    fetcher = calibration.PoliteFetcher(delay=0.3, max_requests=args.max_requests * 4)
    c = L.fetch_resolutions(paths, due, lambda params: fetcher.get_json(calibration.GAMMA + "/markets", params), args.max_requests)
    return {"candidates": len(cand), "due": len(due), "fetched": dict(c), "http_requests": fetcher.requests}, 0


def cmd_score(paths, args) -> tuple[dict, int]:
    now = S.now_ts()
    lb_dir = paths.sub("leaderboard")
    last = max((S.epoch(json.loads(p.read_text()).get("generated_utc")) for p in sorted(lb_dir.glob("2*.json"))[-1:]),
               default=-math.inf) if lb_dir.exists() else -math.inf
    if not args.force and now - last < args.min_interval_h * 3600:
        return {"due": False, "last_leaderboard": S.iso_s(last)}, C.TEMPFAIL
    from astrolabe.signal_engine import dashboard as D
    from astrolabe.signal_engine import promotion as PR
    from astrolabe.signal_engine import scoring as SC
    from astrolabe.signal_engine import specs as SP

    result = {}
    if not args.no_resolve:
        try:
            result["resolve"], _ = cmd_resolve(paths, args)
        except Exception as exc:  # noqa: BLE001 - labels are retried next day; scoring still runs
            result["resolve_error"] = f"{type(exc).__name__}: {exc}"[:300]
    reg = SP.load_registry(paths.spec_dir)
    champion = SP.current_champion(paths, reg)
    agg, info = SC.score_prospective(paths, reg, champion, now)
    lb = SC.leaderboard(agg, reg, champion, now, role="prospective_engine")
    lb["info"] = info
    first = {}
    for r in S.read_logs(paths, "predictions"):
        first.setdefault(r.get("model_id"), S.epoch(r["written_utc"]))
    decision = PR.evaluate(agg, reg, champion, now, SP.champion_history(paths), first)
    lb["promotion"] = decision
    stamp = S.iso_s(now).replace("-", "").replace(":", "")
    S.write_once_json(lb_dir / f"{stamp}.json", lb)
    S.replace_json(lb_dir / "latest.json", lb)
    S.append_log(paths, "promotions", [decision], at=now)
    promo = PR.apply(paths, decision, reg)
    champion = SP.current_champion(paths, reg)
    S.replace_json(paths.sub("dashboard.json"), D.build(paths, reg, champion, now, lb))
    result.update({"leaderboard": f"{stamp}.json", "days_scored": lb["days_scored"], "rows": len(lb["rows"]),
                   "captures": info["captures"], "embargoed": sorted(info["embargoed"]), "promotion": promo,
                   "champion": champion})
    return result, 0


def cmd_walkforward(paths, args) -> tuple[dict, int]:
    from astrolabe.signal_engine import dashboard as D
    from astrolabe.signal_engine import specs as SP
    from astrolabe.signal_engine import walkforward as W

    now = S.now_ts()
    reg = SP.load_registry(paths.spec_dir)
    champion = SP.current_champion(paths, reg)
    lb = W.run_walkforward(paths, reg, champion, now, max_test_days=args.max_test_days, max_rows=args.max_rows)
    latest = paths.sub("leaderboard", "latest.json")
    plb = json.loads(latest.read_text()) if latest.exists() else None
    S.replace_json(paths.sub("dashboard.json"), D.build(paths, reg, champion, now, plb))
    return {"test_days": lb["test_days"], "rows": len(lb["rows"]), "seconds": lb["seconds"], "fits": lb["fits"]}, 0


def cmd_status(paths, args) -> tuple[dict, int]:
    def n(sub, pat="*"):
        d = paths.sub(sub)
        return len(list(d.glob(pat))) if d.exists() else 0

    return {"captures": n("meta", "*.json"), "prediction_dirs": n("predictions"), "fits": len(list(paths.sub("models").glob("*/*/fit.json"))) if paths.sub("models").exists() else 0,
            "leaderboards": n("leaderboard", "2*.json"), "engine_bytes": S.du_bytes(paths.engine)}, 0


CMDS = {"features": cmd_features, "predict": cmd_predict, "tick": cmd_tick, "refit": cmd_refit, "resolve": cmd_resolve,
        "score": cmd_score, "walkforward": cmd_walkforward, "status": cmd_status}
WRITERS = {"features", "predict", "tick", "refit", "resolve", "score", "walkforward"}
# Separate locks: a long refit never delays the per-capture tick (fits become visible only when fit.json exists).
LOCKS = {"features": "tick", "predict": "tick", "tick": "tick", "refit": "refit", "resolve": "score", "score": "score",
         "walkforward": "walkforward", "status": "status"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=sorted(CMDS))
    ap.add_argument("--max-items", type=int, default=4)
    ap.add_argument("--min-interval-h", type=float, default=20.0)
    ap.add_argument("--max-requests", type=int, default=300)
    ap.add_argument("--max-test-days", type=int, default=7)
    ap.add_argument("--max-rows", type=int, default=None, help="walkforward only: cap training rows per target")
    ap.add_argument("--force", action="store_true", help="refit/score even if not due")
    ap.add_argument("--fit-time", default=None, help="refit only: an earlier ISO fit time (labels before it only)")
    ap.add_argument("--no-resolve", action="store_true")
    ap.add_argument("--no-feed-titles", action="store_true", help="tick only: build the signal feed without the Gamma title lookup")
    ap.add_argument("--data-dumps-cap-gb", type=float, default=40.0)
    ap.add_argument("--engine-root", default=None, help="override (dry runs / tests)")
    ap.add_argument("--dumps-root", default=None, help="override the research_lab input root (dry runs)")
    ap.add_argument("--spec-dir", default=None, help="override the spec directory (tests)")
    args = ap.parse_args(argv)
    kw = {}
    if args.dumps_root:
        d = Path(args.dumps_root)
        kw = {"snapshots": d / "snapshots", "sweeps": d / "book_sweeps", "samples": d / "trade_samples",
              "xv_quotes": d / "cross_venue_live" / "quotes"}
    if args.spec_dir:
        kw["spec_dir"] = Path(args.spec_dir)
    paths = S.Paths(engine=Path(args.engine_root) if args.engine_root else C.ENGINE_ROOT, **kw)
    marker = f"SE_{args.cmd.upper()}"
    t0 = time.time()
    if args.cmd in WRITERS:
        ok, why = S.disk_ok(paths, None if args.engine_root else args.data_dumps_cap_gb)
        if not ok:
            return out(marker, {"refused": why}, C.TEMPFAIL)
    try:
        with S.lock(paths, LOCKS[args.cmd]):
            res, code = CMDS[args.cmd](paths, args)
    except BlockingIOError:
        return out(marker, {"refused": "another signal-engine run holds the lock"}, C.TEMPFAIL)
    except Exception as exc:  # noqa: BLE001
        return out(marker, {"error": f"{type(exc).__name__}: {exc}"[:400], "trace": traceback.format_exc()[-1500:]}, 1)
    res["seconds"] = round(time.time() - t0, 1)
    return out(marker, res, code)


if __name__ == "__main__":
    sys.exit(main())
