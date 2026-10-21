# ruff: noqa: E501
"""E026 copy-skilled-wallets live test runner (research only; never trades). Design: docs/research_lab/LIVE_TESTS_COPY.md.

  freeze    build the frozen skilled set once from the HB1 history panels (refuses at/after t_freeze or if it exists)
  run       one recorder pass: signals from new trade samples / print hours, entries and exits from new captures
            (no network; exit 75 when nothing is new; prints COPY_SKILLED_WINDOW_CLOSED when done)
  label     one resolution pass (Gamma GET, read-only public data; exit 75 when nothing was asked)
  analyze   the single registered analysis (refuses before the analysis date; --out refuses to overwrite)
  status    counts only (no price, no payout is read)
  census    PRE-WINDOW planning census on a read-only copy of the inputs: skilled-signal rates, receipt ages, entry
            availability, entry-price spread (for SD), clusters, MDE. Never reads a payout; writes only under --work,
            deleted at the end unless --keep. Refuses any census window ending after 2026-10-22T00:00Z.
"""

from __future__ import annotations

import argparse
import json
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import copy_skilled as cs  # noqa: E402
from astrolabe.research_lab import copy_skilled_analysis as ca  # noqa: E402

SEALED_START = cs.epoch("2026-10-22T00:00:00Z")  # LT2-LT4 windows; a census never reads a batch at or after it


def peak_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024


def cmd_freeze(a) -> int:
    spec = cs.load_spec()
    man = cs.freeze_skillset(Path(a.history), Path(a.root) / "skillset", spec)
    print(json.dumps({k: man[k] for k in ("eligible", "skilled", "sha256", "t_freeze_utc", "profile_trades", "resolved_markets")}, indent=1))
    print(f"peak_mb {peak_mb():.0f}")
    return 0


def cmd_run(a) -> int:
    st = cs.run_once(root=Path(a.root), max_items=a.max_items)
    return cs.TEMPFAIL if st.get("tempfail") else 0


def cmd_label(a) -> int:
    st = cs.label_resolutions(root=Path(a.root), max_requests=a.max_requests)
    if st.get("closed"):
        return 0
    return cs.TEMPFAIL if st.get("tempfail") or not st.get("requests") else 0


def cmd_analyze(a) -> int:
    out = Path(a.out)
    if out.exists():
        print(f"refusing: {out} exists", file=sys.stderr)
        return 2
    res = ca.analyze(Path(a.root))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=str))
    if a.trials:
        cs.append_jsonl(Path(a.trials), [ca.trial_record(res)])
    print(json.dumps({"holm": res.get("holm"), "verdicts": {k: (res.get(k) or {}).get("verdict") for k in ca.TESTS}}, indent=1))
    return 0


def cmd_status(a) -> int:
    root = Path(a.root)
    sig = cs.read_store(root, "signals")
    ent = cs.read_store(root, "entries")
    out = {"signals": int(len(sig)), "entries": int(len(ent)),
           "by_arm_role": sig.groupby(["arm", "role"]).size().to_dict() if len(sig) else {},
           "entry_status": ent.groupby(["kind", "status"]).size().to_dict() if len(ent) else {},
           "bytes": cs.dir_bytes(root)}
    print(json.dumps({str(k): v for k, v in out.items()}, indent=1, default=str))
    return 0


def census_spec(t_start: float, t_end: float) -> dict:
    spec = json.loads(cs.SPEC_PATH.read_text())
    spec.update(registered_utc=cs.iso(t_start), end_utc=cs.iso(t_end), _sha256="census" + "0" * 58, _pinned=False)
    spec["skill"] = {**spec["skill"], "t_freeze_utc": cs.iso(t_start)}
    return spec


def cmd_census(a) -> int:
    from astrolabe.research_lab import wallet_skill_dev as wd

    t_start, t_end = cs.epoch(a.start), cs.epoch(a.end)
    if not (t_end <= SEALED_START) or not (t_start < t_end):
        print("refusing: census window must end at or before 2026-10-22T00:00Z", file=sys.stderr)
        return 2
    work = Path(a.work)
    if work.exists() and any(work.iterdir()):
        print(f"refusing: {work} is not empty", file=sys.stderr)
        return 2
    work.mkdir(parents=True, exist_ok=True)
    rep: dict = {"label": "PRE-WINDOW planning census (counts and quote levels only; no payout, no price change read)",
                 "window": [a.start, a.end]}
    t0 = time.time()
    try:
        spec = census_spec(t_start, t_end)
        h = wd.load_history(Path(a.history), panels=tuple(spec["skill"]["history_panels"]))
        pt, res = wd.profile_trades(h)
        del h
        snap = cs.skillset_frame(pt, res, t_start, spec["skill"])
        del pt
        cs.write_once_csv(work / "skillset" / "skillset.csv.gz", snap)
        rep["skillset"] = {"eligible": int(len(snap)), "skilled": int(snap["skilled"].sum()), "s": round(time.time() - t0, 1),
                           "peak_mb": round(peak_mb(), 1)}
        t1 = time.time()
        # recorder over the census window, then entries from every capture available now
        st = cs.run_once(root=work, snapshot_root=Path(a.snapshots), sample_root=Path(a.samples), prints_root=Path(a.prints),
                         spec=spec, now=cs.now_ts(), max_items=100000, log=lambda s: None)
        rep["recorder"] = {k: st.get(k) for k in ("samples", "print_hours", "captures", "signals_skilled", "signals_control",
                                                  "entries", "skipped_samples", "pending")}
        rep["recorder"]["s"] = round(time.time() - t1, 1)
        rep["recorder"]["peak_mb"] = round(peak_mb(), 1)
        rep["store_bytes"] = cs.dir_bytes(work) - cs.dir_bytes(work / "skillset")
        sig = cs.read_store(work, "signals")
        ent = cs.read_store(work, "entries")
        days = (t_end - t_start) / 86400.0
        rep["counts"] = _census_counts(sig, ent, spec, days)
        rep["passes_counts"] = _pass_counts(work / "passes.jsonl")
    finally:
        if not a.keep:
            shutil.rmtree(work, ignore_errors=True)
    rep["total_s"] = round(time.time() - t0, 1)
    rep["peak_mb"] = round(peak_mb(), 1)
    print(json.dumps(_str_keys(rep), indent=1, default=str))
    return 0


def _str_keys(x):
    """JSON-safe copy (pandas value_counts can give Interval or numpy keys)."""
    if isinstance(x, dict):
        return {str(k): _str_keys(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_str_keys(v) for v in x]
    return x


def _pass_counts(p: Path) -> dict:
    agg = {"sample_rows": 0, "kept": 0, "seen_before": 0, "no_receipt": 0, "sidecar_not_complete": 0, "print_lines": 0}
    if not p.exists():
        return agg
    for line in p.read_text().splitlines():
        r = json.loads(line)
        if r.get("kind") == "sample":
            c = r["counts"]
            agg["sample_rows"] += c.get("rows", 0)
            agg["kept"] += c.get("kept", 0)
            agg["seen_before"] += c.get("seen_before", 0)
            agg["no_receipt"] += c.get("no_receipt", 0)
            agg["sidecar_not_complete"] += int(c.get("sidecar_status") != "complete")
        elif r.get("kind") == "prints":
            agg["print_lines"] += r.get("lines", 0)
    return agg


def _census_counts(sig: pd.DataFrame, ent: pd.DataFrame, spec: dict, days: float) -> dict:
    """Counts, ages, availability and the entry-ask distribution (for the outcome SD under calibration). No payout."""
    out: dict = {}
    if not len(sig):
        return {"signals": 0}
    impacts = ca.impact_table()
    for arm, g in sig.groupby("arm"):
        sk, ct = g[g["role"] == "skilled"], g[g["role"] == "control"]
        o = {"skilled_signals": int(len(sk)), "per_day": round(len(sk) / days, 1), "wallets": int(sk["wallet"].nunique()),
             "markets": int(sk["market_id"].nunique()), "controls": int(len(ct)),
             "controls_per_signal": {str(k): int(v) for k, v in sk["n_controls"].astype(float).value_counts().sort_index().items()},
             "age_h_quantiles": {str(q): round(float(sk["age_s"].quantile(q)) / 3600, 2) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
             "side_buy_share": round(float((sk["side"].astype(int) > 0).mean()), 3),
             "trade_price_bands": {str(k): int(v) for k, v in pd.cut(sk["trade_price"].astype(float), [0, 0.05, 0.35, 0.65, 0.95, 1]).value_counts().sort_index().items()}}
        if len(ent):
            c = ca.build_copies(g, ent, pd.DataFrame(), spec, impacts)
            for L in spec["latencies_s"]:
                cl = c[(c["latency_s"].astype(float) == float(L)) & (c["role"] == "skilled")]
                o[f"L{int(L)}"] = {"entries": int(len(cl)), "status": cl["status"].value_counts().to_dict(),
                                   "entry_ok": int(cl["entry_ok"].sum()), "entry_and_price_ok": int((cl["entry_ok"] & cl["price_ok"]).sum()),
                                   "universe": int(cl["universe"].sum()),
                                   "entry_delay_h_median": round(float((cl["capture_start_ts"] - cl["due_ts"]).median()) / 3600, 2) if len(cl) else None,
                                   "realised_latency_h_quantiles": {str(q): round(float(cl["latency_real_s"].quantile(q)) / 3600, 2) for q in (0.1, 0.5, 0.9)} if len(cl) else {}}
            u = c[(c["latency_s"].astype(float) == float(spec["primary_latency_s"])) & (c["role"] == "skilled") & c["universe"]]
            uc = c[(c["latency_s"].astype(float) == float(spec["primary_latency_s"])) & (c["role"] == "control") & c["universe"]]
            if len(u):
                p = u["ask_j"].astype(float).to_numpy()
                sd_cal = float(np.sqrt(np.mean(p * (1 - p))))  # SD of (pay - ask) per share under calibration at entry
                sizes = u.groupby("cluster").size().to_numpy()
                stake = float(u["stake_ps"].mean())
                deff = ca.deff_upper(sizes)
                cost = float(u["cost_ps"].mean())
                o["universe_L0"] = {"n": int(len(u)), "per_day": round(len(u) / days, 2), "events": int(u["cluster"].nunique()),
                                    "deff_upper": round(deff, 2), "mean_stake": round(stake, 4), "sd_per_share_calibrated": round(sd_cal, 4),
                                    "mean_cost_ps": round(cost, 4), "mean_cost_per_dollar": round(cost / stake, 4),
                                    "days_to_end_median": round(float(((u["end_ts"] - u["row_received_ts"]) / 86400).median()), 2),
                                    "category": u["fee_category"].astype(str).str.split(":").str[0].value_counts().head(8).to_dict(),
                                    "controls_in_universe": int(len(uc))}
                o["universe_L0"]["mde_per_window"] = {}
                for wd_days in (14, 21):
                    n = len(u) / days * wd_days
                    o["universe_L0"]["mde_per_window"][f"{wd_days}d"] = {
                        "n": round(n), "mde_N_deff_upper": round(ca.mde(n, sd_cal, stake, deff), 4),
                        "mde_N_deff_1": round(ca.mde(n, sd_cal, stake, 1.0), 4),
                        "mde_C_deff_upper_K3": round(ca.mde(n, sd_cal * np.sqrt(1 + 1 / 3), stake, deff), 4)}
        out[arm] = o
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(cs.OUT_ROOT))
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--history", default=str(cs.HISTORY_ROOT))
    r = sub.add_parser("run")
    r.add_argument("--max-items", type=int, default=40)
    lb = sub.add_parser("label")
    lb.add_argument("--max-requests", type=int, default=600)
    an = sub.add_parser("analyze")
    an.add_argument("--out", required=True)
    an.add_argument("--trials", default=None)
    sub.add_parser("status")
    c = sub.add_parser("census")
    c.add_argument("--history", default=str(cs.HISTORY_ROOT))
    c.add_argument("--samples", default=str(cs.SAMPLE_ROOT))
    c.add_argument("--snapshots", default=str(cs.SNAPSHOT_ROOT))
    c.add_argument("--prints", default=str(cs.LIVE_TRADES_ROOT))
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True)
    c.add_argument("--work", default="/tmp/copyskill/census")
    c.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    return {"freeze": cmd_freeze, "run": cmd_run, "label": cmd_label, "analyze": cmd_analyze, "status": cmd_status,
            "census": cmd_census}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
