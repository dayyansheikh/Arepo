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
import math
import resource
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
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


def batch_start(batch_id: str) -> float:
    """Start time of a batch from its id (sample dir name ``YYYYmmddTHHMMSSZ_...`` or ``lp_YYYYmmddTHH``)."""
    if batch_id.startswith("lp_"):
        return datetime.strptime(batch_id[3:14], "%Y%m%dT%H").replace(tzinfo=UTC).timestamp()
    return datetime.strptime(batch_id[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()


def read_batches(passes: Path) -> dict:
    """Start times of the batches the census actually read with a usable source, per arm (sidecar: sample with a
    complete wallet sidecar; large prints: every processed hour), plus the skipped-sample counts (``skipped``:
    ``sidecar_incomplete`` = read but no usable sidecar, ``missing`` = never read: not complete or files retired)."""
    out: dict = {"sidecar": [], "large_prints": [], "skipped": {"sidecar_incomplete": 0, "missing": 0}}
    if not passes.exists():
        return out
    for line in passes.read_text().splitlines():
        r = json.loads(line)
        if r.get("kind") == "sample":
            if r.get("counts", {}).get("sidecar_status") == "complete":
                out["sidecar"].append(batch_start(r["id"]))
            else:
                out["skipped"]["sidecar_incomplete"] += 1
        elif r.get("kind") == "sample_missing":
            out["skipped"]["missing"] += 1
        elif r.get("kind") == "prints":
            out["large_prints"].append(batch_start(r["id"]))
    out["sidecar"].sort()
    out["large_prints"].sort()
    return out


def batch_credit_s(arm: str, starts: np.ndarray, t_start: float) -> np.ndarray:
    """Time credited to each usable batch. Sidecar: the time back to the previous usable sample read (the census start
    for the first). A skipped sample does not advance a market's last-sent time, so its trades are first observed, and
    counted, in the next usable sample (the design's first-observation rule); crediting the gap to that sample keeps
    the rate per covered day. Large prints: one hour per processed hour (every hour is read)."""
    st = np.sort(np.asarray(starts, float))
    if arm != "sidecar":
        return np.full(len(st), BATCH_SPAN_S[arm])
    prev = np.concatenate([[t_start], st[:-1]]) if len(st) else st
    return np.maximum(st - prev, 0.0)


_CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from astrolabe.research_lab import copy_skilled as cs
a = json.loads(Path(sys.argv[2]).read_text())
st = cs.run_once(root=Path(a["root"]), snapshot_root=Path(a["snapshots"]), sample_root=Path(a["samples"]),
                 prints_root=Path(a["prints"]), spec=a["spec"], now=cs.now_ts(), max_items=100000, log=lambda s: None,
                 capture_hi=a["capture_hi"], exits=False)
print("CENSUS_RECORDER " + json.dumps(st, default=str))
try:  # VmHWM: this process's own peak; ru_maxrss carries the forking parent's peak across exec on Linux
    hwm = [x for x in Path("/proc/self/status").read_text().splitlines() if x.startswith("VmHWM:")][0]
    print("CENSUS_RECORDER_HWM_MB " + str(int(hwm.split()[1]) / 1024))
except (OSError, IndexError):
    import resource
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print("CENSUS_RECORDER_HWM_MB " + str(r / (1024 * 1024) if sys.platform == "darwin" else r / 1024))
"""


def recorder_in_child(work: Path, spec: dict, a, capture_hi: float) -> tuple[dict, float]:
    """The census recorder pass in a fresh interpreter, so its peak RSS is measured apart from the history load."""
    args = work / "census_args.json"
    args.write_text(json.dumps({"root": str(work), "snapshots": a.snapshots, "samples": a.samples, "prints": a.prints,
                                "spec": spec, "capture_hi": capture_hi}))
    r = subprocess.run([sys.executable, "-c", _CHILD, str(Path(__file__).resolve().parents[1]), str(args)],
                       capture_output=True, text=True, check=False)
    args.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"census recorder failed: {r.stderr[-2000:]}")
    line = [x for x in r.stdout.splitlines() if x.startswith("CENSUS_RECORDER ")][-1]
    hwm = [x for x in r.stdout.splitlines() if x.startswith("CENSUS_RECORDER_HWM_MB ")][-1]
    return json.loads(line[len("CENSUS_RECORDER "):]), float(hwm.split()[1])


WORK_MARKER = ".copy_skilled_census_work"


def prepare_work(work: Path) -> bool:
    """Create the census work dir with its marker file. A non-empty dir is removed only if it carries the marker (left
    by an earlier census attempt that was killed, e.g. SIGKILL / OOM, so it may hold wallet hashes); any other non-empty
    dir is refused and never touched."""
    if work.exists() and any(work.iterdir()):
        if not (work.is_dir() and (work / WORK_MARKER).is_file()):
            return False
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    (work / WORK_MARKER).write_text(json.dumps({"created_by": "run_copy_skilled.py census", "at": cs.iso(time.time())}))
    return True


def cmd_census(a) -> int:
    from astrolabe.research_lab import wallet_skill_dev as wd

    t_start, t_end = cs.epoch(a.start), cs.epoch(a.end)
    if not (t_end <= SEALED_START) or not (t_start < t_end):
        print("refusing: census window must end at or before 2026-10-22T00:00Z", file=sys.stderr)
        return 2
    out_path = Path(a.out) if a.out else None
    if out_path is not None and out_path.exists():
        print(f"refusing: {out_path} exists", file=sys.stderr)
        return 2
    work = Path(a.work)
    if not prepare_work(work):
        print(f"refusing: {work} is not empty and was not created by a census run", file=sys.stderr)
        return 2
    capture_hi = SEALED_START  # no quote at or after the LT2-LT4 / E026 windows is ever opened by a census
    rep: dict = {"label": "PRE-WINDOW planning census (counts and entry-quote levels only; no payout, no exit quote, "
                          "no price change read; no capture at or after 2026-10-22T00:00Z)",
                 "window": [a.start, a.end], "capture_hi": cs.iso(capture_hi), "git_commit": cs.git_commit(),
                 "code_sha256": cs.code_hashes(), "spec_file_sha256": cs.sha256_file(cs.SPEC_PATH)}
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
        del snap
        t1 = time.time()
        st, child_mb = recorder_in_child(work, spec, a, capture_hi)
        rep["recorder"] = {k: st.get(k) for k in ("samples", "print_hours", "captures", "signals_skilled", "signals_control",
                                                  "entries", "skipped_samples", "pending")}
        rep["recorder"]["s"] = round(time.time() - t1, 1)
        rep["recorder"]["peak_mb_child"] = round(child_mb, 1)  # the recorder alone (q0541 mem_mb must stay below 500)
        rep["store_bytes"] = cs.dir_bytes(work) - cs.dir_bytes(work / "skillset")
        caps = [c["start"] for c in cs.scan_captures(Path(a.snapshots), t_start) if c["start"] < capture_hi]
        cap_last = max(caps) if caps else t_start
        rep["last_capture_read"] = cs.iso(cap_last)
        sig = cs.read_store(work, "signals")
        ent = cs.read_store(work, "entries")
        rep["counts"] = census_counts(sig, ent, spec, read_batches(work / "passes.jsonl"), cap_last)
        rep["passes_counts"] = _pass_counts(work / "passes.jsonl")
    finally:
        if not a.keep:
            shutil.rmtree(work, ignore_errors=True)
    rep["total_s"] = round(time.time() - t0, 1)
    rep["peak_mb"] = round(peak_mb(), 1)
    text = json.dumps(_str_keys(rep), indent=1, default=str)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n")
    print(text)
    return 0


def _str_keys(x):
    """JSON-safe copy (pandas value_counts can give Interval or numpy keys)."""
    if isinstance(x, dict):
        return {str(k): _str_keys(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_str_keys(v) for v in x]
    return x


def _pass_counts(p: Path) -> dict:
    agg = {"sample_rows": 0, "kept": 0, "seen_before": 0, "no_receipt": 0, "sidecar_not_complete": 0, "samples_missing": 0,
           "print_lines": 0}
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
        elif r.get("kind") == "sample_missing":
            agg["samples_missing"] += 1
        elif r.get("kind") == "prints":
            agg["print_lines"] += r.get("lines", 0)
    return agg


BATCH_SPAN_S = {"sidecar": 7200.0, "large_prints": 3600.0}  # nominal span of one batch (2-hourly samples, print hours)
NO_PROJECTION = "do_not_register_redesign"
BATCH_RECEIPT_SLACK_S = 3600.0  # receipt of a sample row is within about 1 h of the sample start


def no_gates(reason: str, skipped: dict | None = None) -> dict:
    """Gate result when nothing can be projected: never a silent absence."""
    return {"G1_copies_events": False, "G2_pairs": False, "G3_mde_N_event": False, "decision": NO_PROJECTION,
            "reason": reason, "skipped_samples": skipped or {}}


def gate_eval(proj: dict, spec: dict) -> dict:
    """The pre-declared census gates (spec ``census_gates``, fixed before any census number) on the UNROUNDED 21-day
    projection (rounding is for display only)."""
    g = spec["census_gates"]
    out = {"G1_copies_events": bool(proj["n"] >= g["g1_min_copies"] and proj["events"] >= g["g1_min_events"]),
           "G2_pairs": bool(proj["pairs"] >= g["g2_min_pairs"] and proj["pair_events"] >= g["g2_min_pair_events"]),
           "G3_mde_N_event": bool(proj["mde_N_event_icc1"] <= g["g3_max_mde_N_event_ppd"])}
    out["decision"] = ("register_k2" if out["G1_copies_events"] and out["G2_pairs"] else
                       "drop_E026C_register_k1" if out["G1_copies_events"] else "do_not_register_redesign")
    if not out["G3_mde_N_event"]:
        out["label"] = "low-power (a null is uninformative)"
    return out


def census_counts(sig: pd.DataFrame, ent: pd.DataFrame, spec: dict, batches: dict[str, list[float]], cap_last: float) -> dict:
    """Counts, ages, entry availability and the entry-ask distribution (for the outcome SD under calibration). No payout.

    Rates use only batches whose every entry could be recorded from captures read (batch start + 1 h + L + max entry
    delay <= the last capture read), and divide by the time credited to those batches (``batch_credit_s``: a gap of
    skipped samples is credited to the next usable sample, which carries the gap's trades). The gate result (spec arm)
    is always written, with the skipped-sample counts next to it."""
    out: dict = {}
    skipped = batches.get("skipped", {})
    if not len(sig):
        return {"signals": 0, "gates": no_gates("no signals", skipped)}
    impacts = ca.impact_table()
    u_spec = spec["universe"]
    max_delay = float(u_spec["max_entry_delay_s"])
    window_days = (cs.epoch(spec["end_utc"]) - cs.epoch(spec["registered_utc"])) / 86400.0
    proj_days = 21.0
    t_start = cs.epoch(spec["registered_utc"])
    sig = sig.assign(_bstart=[batch_start(b) for b in sig["batch_id"].astype(str)])
    gates: dict | None = None
    for arm, g in sig.groupby("arm"):
        starts = np.sort(np.asarray(batches.get(arm, []), float))
        credit = batch_credit_s(arm, starts, t_start)
        sk, ct = g[g["role"] == "skilled"], g[g["role"] == "control"]
        days_read = float(credit.sum()) / 86400.0
        o = {"batches_read": int(len(starts)), "days_read": round(days_read, 3), "window_days": round(window_days, 3),
             "skilled_signals": int(len(sk)), "per_day": round(len(sk) / days_read, 2) if days_read else None,
             "wallets": int(sk["wallet"].nunique()), "markets": int(sk["market_id"].nunique()), "controls": int(len(ct)),
             "controls_per_signal": {str(k): int(v) for k, v in sk["n_controls"].astype(float).value_counts().sort_index().items()},
             "age_h_quantiles": {str(q): round(float(sk["age_s"].quantile(q)) / 3600, 2) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
             "side_buy_share": round(float((sk["side"].astype(int) > 0).mean()), 3) if len(sk) else None,
             "trade_price_bands": {str(k): int(v) for k, v in pd.cut(sk["trade_price"].astype(float), [0, 0.05, 0.35, 0.65, 0.95, 1]).value_counts().sort_index().items()}}
        if len(ent) and len(sk):
            c = ca.build_copies(g, ent, pd.DataFrame(), spec, impacts)
            c = c.merge(g[["signal_id", "_bstart"]], on="signal_id", how="left")
            for L in spec["latencies_s"]:
                lim = cap_last - BATCH_RECEIPT_SLACK_S - float(L) - max_delay
                ok_sig = sk[sk["_bstart"].to_numpy(float) <= lim]
                cl = c[(c["latency_s"].astype(float) == float(L)) & (c["role"] == "skilled") & (c["_bstart"].to_numpy(float) <= lim)]
                o[f"L{int(L)}"] = {"signals_complete": int(len(ok_sig)), "entries": int(len(cl)),
                                   "status": cl["status"].value_counts().to_dict(),
                                   "entry_ok": int(cl["entry_ok"].sum()), "entry_and_price_ok": int((cl["entry_ok"] & cl["price_ok"]).sum()),
                                   "universe": int(cl["universe"].sum()),
                                   "entry_delay_h_median": round(float((cl["capture_start_ts"] - cl["due_ts"]).median()) / 3600, 2) if len(cl) else None,
                                   "realised_latency_h_quantiles": {str(q): round(float(cl["latency_real_s"].quantile(q)) / 3600, 2) for q in (0.1, 0.5, 0.9)} if len(cl) else {}}
            L0 = float(spec["primary_latency_s"])
            lim0 = cap_last - BATCH_RECEIPT_SLACK_S - L0 - max_delay
            days0 = float(credit[starts <= lim0].sum()) / 86400.0
            c0 = c[(c["latency_s"].astype(float) == L0) & (c["_bstart"].to_numpy(float) <= lim0)]
            un = c0[(c0["role"] == "skilled") & c0["universe"]]
            u = c0[(c0["role"] == "skilled") & c0["primary_set"]]
            uc = c0[(c0["role"] == "control") & c0["primary_set"] & c0["parent_id"].isin(set(u["signal_id"]))]
            if len(u) and days0 > 0:
                p = u["ask_j"].astype(float).to_numpy()
                sd_cal = float(np.sqrt(np.mean(p * (1 - p))))  # SD of (pay - ask) per share under calibration at entry
                stake = float(u["stake_ps"].mean())
                deff_ev = ca.deff_upper(u.groupby("cluster").size().to_numpy())
                deff_w = ca.deff_upper(u.groupby("wallet").size().to_numpy())
                deff_evw = ca.deff_upper(u.groupby(["cluster", "wallet"]).size().to_numpy())
                deff_2w = deff_ev + deff_w - deff_evw  # two-way (event, wallet) with correlation 1 in each dimension
                wm = u.groupby("wallet").size().sort_values(ascending=False).to_numpy()
                cost = float(u["cost_ps"].mean())
                m_ctl = uc.groupby("parent_id").size()
                pairs = int(len(m_ctl))
                infl_c = float(np.sqrt(1.0 + np.mean(1.0 / m_ctl.to_numpy(float)))) if pairs else math.nan
                ev_pairs = int(u.loc[u["signal_id"].isin(set(m_ctl.index)), "cluster"].nunique())
                o["primary_set_L0"] = {
                    "days_used": round(days0, 3), "n": int(len(u)), "uncapped_universe_n": int(len(un)),
                    "per_day": round(len(u) / days0, 2), "events": int(u["cluster"].nunique()), "wallets": int(len(wm)),
                    "top1_wallet_share": round(float(wm[0] / wm.sum()), 3), "top10_wallet_share": round(float(wm[:10].sum() / wm.sum()), 3),
                    "deff_event_icc1": round(deff_ev, 2), "deff_wallet_icc1": round(deff_w, 2),
                    "deff_event_x_wallet_icc1": round(deff_evw, 2), "deff_twoway_icc1": round(deff_2w, 2),
                    "mean_stake": round(stake, 4), "sd_per_share_calibrated": round(sd_cal, 4),
                    "mean_cost_ps": round(cost, 4), "mean_cost_per_dollar": round(cost / stake, 4),
                    "days_to_end_median": round(float(((u["end_ts"] - u["row_received_ts"]) / 86400).median()), 2),
                    "ask_bands": {str(k): int(v) for k, v in pd.cut(p, [0.05, 0.35, 0.65, 0.951], right=False, labels=["long_shot", "middle", "favourite"]).value_counts().items()},
                    "buy_share": round(float((u["side"].astype(int) > 0).mean()), 3),
                    "category": u["fee_category"].astype(str).str.split(":").str[0].value_counts().head(8).to_dict(),
                    "controls_in_primary_set": int(len(uc)), "pairs": pairs, "pair_events": ev_pairs,
                    "control_sd_inflation": round(infl_c, 4) if pairs else None}
                scale = proj_days / days0
                n, npair = len(u) * scale, pairs * scale
                raw = {"days": proj_days, "n": n, "events": u["cluster"].nunique() * scale, "pairs": npair,
                       "pair_events": ev_pairs * scale,
                       "mde_N_deff1": ca.mde(n, sd_cal, stake, 1.0),
                       "mde_N_event_icc1": ca.mde(n, sd_cal, stake, deff_ev),
                       "mde_N_twoway_icc1": ca.mde(n, sd_cal, stake, deff_2w),
                       "mde_C_event_icc1": ca.mde(npair, sd_cal * infl_c, stake, deff_ev) if pairs else math.inf}
                o["primary_set_L0"]["projection_21d"] = {
                    k: (round(v, 1) if k in ("n", "events", "pairs", "pair_events") else round(v, 4) if math.isfinite(v) else None)
                    for k, v in raw.items()}
                if arm == spec["universe"]["arm"]:
                    gates = {**gate_eval(raw, spec), "skipped_samples": skipped}
            elif arm == spec["universe"]["arm"]:
                gates = no_gates("empty primary set or no usable days at L = 0", skipped)
        elif arm == spec["universe"]["arm"]:
            gates = no_gates("no skilled signal or no entry", skipped)
        out[arm] = o
    out["gates"] = gates if gates is not None else no_gates(f"no {spec['universe']['arm']} signals", skipped)
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
    c.add_argument("--out", default=None, help="also write the census JSON here (refuses to overwrite)")
    a = ap.parse_args(argv)
    return {"freeze": cmd_freeze, "run": cmd_run, "label": cmd_label, "analyze": cmd_analyze, "status": cmd_status,
            "census": cmd_census}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
