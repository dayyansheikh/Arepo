"""Runner for the learned surprise-move detector (research lab; exploratory_historical).

Sub-commands (in order): ``log-labels`` (one trials.jsonl line fixing the label spec, before any
feature work), ``meta`` (Gamma question / gameStartTime per market, <= 5 req/s, yields to the live
collector), ``build`` (rows + events + manifest), ``learn`` (walk-forward arms, evaluation on the
untouched test months, case recall), ``freeze`` (hash-pin the chosen learned spec).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import if_h1  # noqa: E402
from astrolabe.research_lab import surprise_moves as sm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data-dumps" / "research_lab"
OUT = ROOT / "surprise_moves"
RUN = ROOT / "history" / "h2_main"
log = logging.getLogger("surprise")


def _paths(args) -> tuple[Path, Path]:
    """(run_dir, out_dir): the h2_main development set by default, or ``--run``/``--out``."""
    run = ROOT / "history" / args.run if getattr(args, "run", None) else RUN
    out = ROOT / args.out if getattr(args, "out", None) else OUT
    return run, out


def _meta(args) -> None:
    import pandas as pd

    run, out = _paths(args)
    out.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(run / "sample.csv.gz", dtype=str, keep_default_na=False)
    path = out / "gamma_meta.json"
    have = json.loads(path.read_text()) if path.exists() else {}
    cids = [c for c in sample["condition_id"] if c not in have]
    lim = hb.Limiter(hb.httpx_transport(), rps=min(args.rps, 5.0))
    rule = if_h1.load_spec()["class_rule"]
    t0 = time.time()
    for i, batch in enumerate(if_h1.chunks(cids, 40)):
        hb.yield_to_live()
        for extra in ({}, {"closed": "true"}):
            missing = [c for c in batch if c not in have]
            if not missing:
                break
            st, data = lim.get(hb.GAMMA_MARKETS, {"condition_ids": missing, "limit": 100, **extra})
            for m in data if st == 200 and isinstance(data, list) else []:
                q = m.get("question") or ""
                have[m["conditionId"]] = {
                    "question": q, "slug": m.get("slug") or "",
                    "game_start_ts": hb._epoch(m.get("gameStartTime")),
                    "end_ts": hb._epoch(m.get("endDate")),
                    "decision_class": if_h1.classify(q, m.get("feeType"), rule),
                    "question_stem": sm.question_stem(q)}
        if i % 10 == 0:
            path.write_text(json.dumps(have))
            log.info("meta %d/%d batches, %d markets, %.0fs", i, len(cids) // 40 + 1, len(have),
                     time.time() - t0)
    path.write_text(json.dumps(have))
    log.info("meta done: %d markets with metadata (requests %d)", len(have), lim.requests)


def _log_labels(args) -> None:
    rec = sm.log_label_spec(note=args.note)
    print(json.dumps({k: rec[k] for k in ("trial_id", "label_spec_sha256", "utc")}))


def _build(args) -> None:
    import pandas as pd

    meta_path = OUT / "gamma_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    excl: set[str] = set()
    for p in args.exclude:
        pth = Path(p)
        if pth.suffix == ".json":
            d = json.loads(pth.read_text())
            items = d if isinstance(d, list) else d.get("condition_ids") or [
                m["condition_id"] for c in d.get("cases", []) for m in c.get("markets", [])]
            excl.update(str(x) for x in items)
        else:
            excl.update(pd.read_csv(pth, dtype=str)["condition_id"].dropna())
    man = sm.build_dataset(RUN, OUT, meta=meta, exclude_condition_ids=excl, log=log.info)
    print(json.dumps(man["counts"]))


def _heavy_lock():
    """Shared heavy-compute lock (~/arepo_collector/heavy_lock.md): mkdir lock, >= 20% free."""
    import contextlib
    import os
    import subprocess

    @contextlib.contextmanager
    def held():
        lock = Path("/tmp/arepo_heavy.lock")
        while True:
            try:
                lock.mkdir()
                break
            except FileExistsError:
                log.info("heavy lock held by another agent; retrying in 60s")
                time.sleep(60)
        (lock / "pid").write_text(str(os.getpid()))
        try:
            while True:
                out = subprocess.run(["memory_pressure"], capture_output=True, text=True,
                                     timeout=20).stdout
                pct = [int(x.split("free percentage:")[1].split("%")[0]) for x in out.splitlines()
                       if "free percentage:" in x]
                if not pct or pct[0] >= 20:
                    break
                log.info("memory free %s%% < 20%%; waiting", pct[0])
                time.sleep(60)
            yield
        finally:
            import shutil

            shutil.rmtree(lock, ignore_errors=True)
    return held()


def _learn(args) -> None:
    from astrolabe.research_lab import surprise_learn as sl

    with _heavy_lock():
        res = sl.run(OUT, n_boot=args.n_boot, n_placebo=args.n_placebo, log=log.info)
    recs = sl.log_arms(res, note=args.note)
    for name, r in res["test"].items():
        b = r["budgets"][str(sl.PRIMARY_BUDGET)]
        mc = b["matched_controls"]
        plc = res["placebo"]["arms"].get(name, {})
        print(f"{name:32s} prec6h={b['precision_6h']:.4f} base={r['base_rate_6h']:.4f} "
              f"ctrl={mc['control_base_rate']} excess={mc['excess_mean']} "
              f"ci={mc['excess_ci95']} p={mc['p_one_sided']} "
              f"placebo_rank={plc.get('p_rank_matched_excess')} "
              f"recall={b['recall_events']} n={b['n_alerts']}")
    print(json.dumps({"trials_logged": len(recs)}))


MADURO = {"916440": "0x580adc1327de9bf7c179ef5aaffa3377bb5cb252b7d6390b027172d43fd6f993"}
MADURO_NEWS_TS = 1767421200  # 2026-01-03 06:20Z, the price-defined onset in CASE_STUDY_MADURO.md


def _cases(args) -> None:
    import pandas as pd

    from astrolabe.research_lab import surprise_learn as sl

    cs_root = ROOT / "case_studies"
    es_root = ROOT / "event_study" / "markets"
    items = []  # (case_id, market_id, condition_id, prices_path, trades_path, news_ts, in_sample)
    for mp in sorted(cs_root.glob("*/manifest.json")):
        m = json.loads(mp.read_text())
        for v in m["markets"].values():
            items.append((m["case_id"], v["market_id"], v["condition_id"],
                          mp.parent / f"prices_{v['market_id']}.csv.gz",
                          mp.parent / f"trades_{v['market_id']}.csv.gz", float(m["news_ts"]),
                          False))
    for mid, cid in MADURO.items():
        d = es_root / mid
        if (d / "prices.csv.gz").exists():
            items.append(("maduro_jan2026", mid, cid, d / "prices.csv.gz", d / "trades.csv.gz",
                          float(MADURO_NEWS_TS), True))
    meta_path = OUT / "case_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    need = sorted({it[2] for it in items} - set(meta))
    if need:
        lim = hb.Limiter(hb.httpx_transport(), rps=4.0)
        hb.yield_to_live()
        rule = if_h1.load_spec()["class_rule"]
        from astrolabe.research_panel.pairing import fee_category
        for extra in ({}, {"closed": "true"}):
            st, data = lim.get(hb.GAMMA_MARKETS, {"condition_ids": need, "limit": 100, **extra})
            for m in data if st == 200 and isinstance(data, list) else []:
                ev = (m.get("events") or [{}])[0] or {}
                q = m.get("question") or ""
                meta[m["conditionId"]] = {
                    "event_id": str(ev.get("id") or ""), "fee_category": fee_category(
                        m.get("feeType")), "created_at": m.get("createdAt"),
                    "start_epoch": hb._epoch(m.get("startDate")),
                    "end_epoch": hb._epoch(m.get("endDate")),
                    "close_epoch": hb._epoch(m.get("closedTime")), "closed": bool(m.get("closed")),
                    "decision_class": if_h1.classify(q, m.get("feeType"), rule),
                    "question_stem": sm.question_stem(q)}
        meta_path.write_text(json.dumps(meta, indent=1))
    fs = sl.first_seen_from_cache([ROOT / "event_study" / "first_trade.jsonl",
                                   cs_root / "first_trade_cache.jsonl"])
    frames = []
    for case_id, mid, cid, pp, tp, news, in_sample in items:
        if not pp.exists() or not tp.exists() or cid not in meta:
            log.warning("case %s market %s: data or metadata missing", case_id, mid)
            continue
        mm = meta[cid]
        rec = {"market_id": mid, "event_id": mm["event_id"], "condition_id": cid,
               "fee_category": mm["fee_category"], "status": "closed" if mm["closed"] else "active",
               "liquidity": float("nan"), "volume": float("nan"),
               "created_at": mm["created_at"], "start_epoch": mm["start_epoch"],
               "end_epoch": mm["end_epoch"], "close_epoch": mm["close_epoch"],
               "closed": mm["closed"], "stratum": "", "decision_class": mm["decision_class"],
               "question_stem": mm["question_stem"]}
        prices = pd.read_csv(pp)
        trades = hb.load_trades(tp)
        rows = sl.case_rows(rec, prices, trades, fs, window_truncated=not in_sample)
        if not len(rows):
            log.warning("case %s market %s: no grid rows", case_id, mid)
            continue
        rows["case_id"], rows["news_ts"], rows["in_sample"] = case_id, news, in_sample
        frames.append(rows)
    cases = pd.concat(frames, ignore_index=True)
    models = sl.load_models(OUT)
    results = json.loads((OUT / "results.json").read_text())
    ts_ = pd.read_csv(OUT / "test_scores.csv.gz")
    out = sl.score_cases(cases, models, results, ts_)
    (OUT / "case_recall.json").write_text(json.dumps(out, indent=1, default=sl._json))
    for k, v in out.items():
        print(k, "in_sample" if v["in_sample"] else "held_out", {
            a: (round(r["percentile_vs_test_months"], 3), r["clears_1pct_budget"],
                r["lead_h_first_clear"]) if r.get("max_score") is not None else None
            for a, r in v["arms"].items()})


def _placebo(args) -> None:
    from astrolabe.research_lab import provenance
    from astrolabe.research_lab import surprise_learn as sl

    with _heavy_lock():
        out = sl.placebo_extension(OUT, n_draws=args.n_draws, log=log.info)
    for a, v in out["arms"].items():
        print(a, {k: v[k] for k in ("real_matched_excess", "p_rank_matched_excess",
                                    "real_precision_6h", "p_rank_precision")},
              "placebo excess", v["placebo_matched_excess"])
    provenance.append_trial({
        "kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move placebo extension",
        "evidence_role": sm.EVIDENCE_ROLE, "arm": "placebo_extension", "learned": False,
        "n_draws": args.n_draws, "summary": {a: {k: v[k] for k in (
            "real_matched_excess", "p_rank_matched_excess", "p_rank_precision")}
            for a, v in out["arms"].items()},
        "provenance": provenance.run_provenance([Path(sl.__file__)])})


def _freeze(args) -> None:
    from astrolabe.research_lab import detector_eval as de
    from astrolabe.research_lab import provenance
    from astrolabe.research_lab import surprise_learn as sl

    models = sl.load_models(OUT)
    m = models[args.arm]
    res = json.loads((OUT / "results.json").read_text())
    spec = m.to_rule_spec(args.rule_id, "1", "sm_imb_1h", args.description)
    index = de.freeze_rules([spec], index_name=sl_index())
    entry = [e for e in index["frozen"] if e["rule_id"] == args.rule_id][0]
    rec = provenance.append_trial({
        "kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move detector FROZEN",
        "evidence_role": sm.EVIDENCE_ROLE, "arm": args.arm, "rule_id": args.rule_id,
        "spec_sha256": entry["sha256"], "status": "frozen", "n_terms": len(spec.terms),
        "rows_sha256": res["rows_sha256"], "label_spec_sha256": res["label_spec_sha256"],
        "test_primary": res["test"][args.arm]["budgets"][str(sl.PRIMARY_BUDGET)][
            "matched_controls"],
        "provenance": provenance.run_provenance([Path(sl.__file__)])}, provenance.TRIALS_PATH)
    print(json.dumps({"rule_id": args.rule_id, "sha256": entry["sha256"],
                      "frozen_utc": entry["frozen_utc"], "n_terms": len(spec.terms),
                      "trial_id": rec["trial_id"]}))


def sl_index() -> str:
    from astrolabe.research_lab import live_trade_monitor as ltm

    return ltm.LEARNED_INDEX


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("log-labels")
    s.add_argument("--note", default="")
    s = sub.add_parser("meta")
    s.add_argument("--rps", type=float, default=4.0)
    s.add_argument("--run")
    s.add_argument("--out")
    s = sub.add_parser("build")
    s.add_argument("--exclude", nargs="*", default=[])
    s = sub.add_parser("learn")
    s.add_argument("--n-boot", type=int, default=1000)
    s.add_argument("--n-placebo", type=int, default=20)
    s.add_argument("--note", default="")
    sub.add_parser("cases")
    s = sub.add_parser("placebo")
    s.add_argument("--n-draws", type=int, default=100)
    s = sub.add_parser("freeze")
    s.add_argument("--arm", default="en_logit_full")
    s.add_argument("--rule-id", default="sm_learned_v1")
    s.add_argument("--description", default="Learned surprise-move detector (elastic-net "
                   "logistic on surprise-features-v1; weights fit on the development months)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    {"meta": _meta, "log-labels": _log_labels, "build": _build, "learn": _learn,
     "cases": _cases, "placebo": _placebo, "freeze": _freeze}[args.cmd](args)


if __name__ == "__main__":
    main()
