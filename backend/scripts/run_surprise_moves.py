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


def _meta(args) -> None:
    import pandas as pd

    OUT.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(RUN / "sample.csv.gz", dtype=str, keep_default_na=False)
    path = OUT / "gamma_meta.json"
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("log-labels")
    s.add_argument("--note", default="")
    s = sub.add_parser("meta")
    s.add_argument("--rps", type=float, default=4.0)
    s = sub.add_parser("build")
    s.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    {"meta": _meta, "log-labels": _log_labels, "build": _build}[args.cmd](args)


if __name__ == "__main__":
    main()
