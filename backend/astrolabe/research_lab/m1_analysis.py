# ruff: noqa: E501
"""M1-A analysis (``MEASUREMENT_M1_CH263.md`` sections 4-8, 10, 11, 9.5). Descriptive measurement; no test, no p-value.

Refuses before ``READOUT_UTC`` + 12 h, without ``out``, over an existing ``out``, and on any pin mismatch. Keeps only unit lines whose
``spec_sha`` and ``code_sha`` equal the pins and whose role is ``prospective_measurement``. Cost lines come from ``costs.py`` (read-only),
recorded at J1 time. Money units are dollars per share ("c" in the text's coarse thresholds means cents).
"""

from __future__ import annotations

import gzip
import json
import math
import re
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.stats import beta

from . import m1_extract as ex
from . import m1_j0 as j0
from . import m1_spec as sp

BANNED = re.compile(r"\b(supported|confirmed|significant|edge|profitable|route exists)\b|p-value", re.I)
NONFINAL = ("pending", "not_found", "unavailable_fetch", "unavailable_other")


# --- loading ---------------------------------------------------------------------------------------------------------------------------

def parse_closed(v) -> float:
    if v in (None, ""):
        return math.nan
    s = str(v).strip().replace(" ", "T", 1)
    if re.search(r"[+-]\d\d$", s):
        s += ":00"
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return math.nan
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).timestamp()


def load_units(store: Path, pins: dict) -> tuple[list[dict], dict]:
    units: list = []
    cnt: Counter = Counter()
    for p in sorted((Path(store) / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                if not line.strip():
                    continue
                u = json.loads(line)
                cnt["lines"] += 1
                if u.get("spec_sha") != pins["spec_sha"] or u.get("code_sha") != pins["code_sha"] or u.get("role") != sp.ROLE:
                    cnt["dropped_pin_or_role_mismatch"] += 1
                    continue
                units.append(u)
    return units, dict(cnt)


def load_readout(store: Path) -> dict:
    p = Path(store) / "readout" / "readout.jsonl.gz"
    out: dict = {}
    if p.exists():
        with gzip.open(p, "rt") as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    out[int(d["market_id"])] = d
    return out


def classify_units(units: list[dict], readout: dict, spec: dict) -> Counter:
    """Adds ``cls`` (8.1), ``final``, ``L``, ``w_h``, ``cap``, ``n1``, ``n2``, ``n1_L1loss`` to each unit; returns wait-rule counts."""
    notes: Counter = Counter()
    rate, hpy = spec["capital_rate"], spec["hours_per_year"]
    for u in units:
        r = readout.get(u["market_id"])
        st = r["state"] if r else "unavailable_fetch"
        if r is None:
            notes["no_readout_record"] += 1
        if st == "resolved":
            fav = (r["y"] == 1) if u["side"] == "YES" else (r["y"] == 0)
            u["cls"], u["L"] = ("resolved_favoured", 0.0) if fav else ("resolved_other", 1.0)
        elif st == "split_50_50":
            u["cls"], u["L"] = "split_50_50", 0.5
        elif st == "pending":
            u["cls"], u["L"] = "pending", None
        elif st == "not_found":
            u["cls"], u["L"] = "not_found", None
        elif st == "unavailable_fetch":
            u["cls"], u["L"] = "unavailable_fetch", None
        else:
            u["cls"], u["L"] = "unavailable_other", None
            u["unavailable_sub"] = st
        u["final"] = u["L"] is not None
        u["uma"] = r.get("uma") if r else None
        fetched = sp_ts(r.get("fetched_utc")) if r else math.nan
        ct = parse_closed(r.get("closed_time")) if r else math.nan
        t_d = u["t_d"]
        if math.isfinite(ct):
            w = 0.0 if ct < t_d else (ct - t_d) / 3600.0
            if ct < t_d:
                notes["wait_clock_anomaly"] += 1
        elif math.isfinite(fetched):
            w = max(0.0, (fetched - t_d) / 3600.0)
            notes["wait_upper_bound"] += 1
        else:
            w = 0.0
            notes["wait_unknown_zero"] += 1
        u["w_h"] = w
        u["cap"] = u["ask_f"] * rate * w / hpy
        u["n1"] = None if not u["final"] else u["c"] - u["L"] - u["fee_L1"] - u["cap"]
        u["n2"] = None if not u["final"] else u["c"] - u["L"] - u["fee_L2"] - u["cap"]
        u["n_loss"] = u["c"] - 1.0 - u["fee_L1"] - u["cap"]  # L = 1: the stake is lost (8.2)
    return notes


def sp_ts(v) -> float:
    return sp.ts({"x": v}, "x") if v else math.nan


# --- bootstrap ---------------------------------------------------------------------------------------------------------------------------

def _draws(n_events: int, spec: dict):
    b = spec["bootstrap"]
    rng = np.random.default_rng(b["seed"])
    done = 0
    while done < b["B"]:
        m = min(b["chunk"], b["B"] - done)
        yield rng.integers(0, n_events, size=(m, n_events))
        done += m


def ci_of(draws: np.ndarray, spec: dict) -> tuple[float, float]:
    a = (1 - spec["bootstrap"]["ci"]) / 2 * 100
    lo, hi = np.percentile(draws, [a, 100 - a])
    return float(lo), float(hi)


def event_boot(units: list[dict], stats: dict, spec: dict, event_mean: dict | None = None) -> dict:
    """Event bootstrap of unit-weighted means ``mean(stats[k](u))``; ``event_mean`` stats are event-weighted (mean over events of the event's mean).
    All of an event's units are resampled together; B, seed from the spec; percentile interval."""
    if not units:
        return {}
    groups: dict = defaultdict(list)
    for u in units:
        groups[u["cluster"]].append(u)
    keys = sorted(groups)
    e = len(keys)
    den = np.array([len(groups[k]) for k in keys], dtype=float)
    num = {n: np.array([sum(f(u) for u in groups[k]) for k in keys], dtype=float) for n, f in stats.items()}
    emean = {n: np.array([sum(f(u) for u in groups[k]) / len(groups[k]) for k in keys], dtype=float) for n, f in (event_mean or {}).items()}
    est = {n: float(a.sum() / den.sum()) for n, a in num.items()} | {n: float(a.mean()) for n, a in emean.items()}
    acc: dict = {n: [] for n in est}
    for idx in _draws(e, spec):
        d = den[idx].sum(axis=1)
        for n, a in num.items():
            acc[n].append(a[idx].sum(axis=1) / d)
        for n, a in emean.items():
            acc[n].append(a[idx].mean(axis=1))
    out = {}
    for n in est:
        lo, hi = ci_of(np.concatenate(acc[n]), spec)
        out[n] = {"est": est[n], "lo": lo, "hi": hi, "degenerate": bool(lo == hi)}
    return out


def day_block_boot(units: list[dict], key, spec: dict) -> dict:
    """Block bootstrap over the window's UTC days (same B and seed): resample days with replacement, ``mean(key)`` over the drawn days' units."""
    by: dict = defaultdict(lambda: [0.0, 0])
    for u in units:
        by[u["window_day"]][0] += key(u)
        by[u["window_day"]][1] += 1
    days = sorted(by)
    if not days:
        return {}
    s = np.array([by[d][0] for d in days])
    n = np.array([by[d][1] for d in days], dtype=float)
    acc = []
    for idx in _draws(len(days), spec):
        acc.append(s[idx].sum(axis=1) / n[idx].sum(axis=1))
    lo, hi = ci_of(np.concatenate(acc), spec)
    return {"est": float(s.sum() / n.sum()), "lo": lo, "hi": hi, "days": len(days)}


# --- tail bound ---------------------------------------------------------------------------------------------------------------------------

def stratum_of(n: int) -> str:
    return j0.units_bucket(n)


def tail_bound(final: list[dict], spec: dict) -> dict:
    """7.2: strata = final-state units per event; one-sided Clopper-Pearson upper bound at 1 - alpha/S per stratum; T_U = sum N_s/N_F p_U,s."""
    strata = spec["tu"]["strata"]
    level = 1 - spec["tu"]["alpha"] / len(strata)
    by_ev: dict = defaultdict(list)
    for u in final:
        by_ev[u["cluster"]].append(u)
    per: dict = {s: {"events": 0, "units": 0, "reversed_events": 0, "loss_events": 0, "split_events": 0, "p_upper": 0.0} for s in strata}
    for evu in by_ev.values():
        s = stratum_of(len(evu))
        per[s]["events"] += 1
        per[s]["units"] += len(evu)
        per[s]["reversed_events"] += int(any(u["L"] > 0 for u in evu))
        per[s]["loss_events"] += int(any(u["L"] == 1.0 for u in evu))
        per[s]["split_events"] += int(any(u["L"] == 0.5 for u in evu))
    nf = len(final)
    tu = 0.0
    for d in per.values():
        if d["events"]:
            r, e = d["reversed_events"], d["events"]
            d["p_upper"] = 1.0 if r >= e else float(beta.ppf(level, r + 1, e - r))
            tu += d["units"] / nf * d["p_upper"]
    top = sorted(((k, len(v), int(any(u["L"] > 0 for u in v))) for k, v in by_ev.items()), key=lambda t: (-t[1], str(t[0])))[:10]
    return {"T_U": tu, "level": level, "strata": per, "events_final": len(by_ev),
            "event_reversal_losses": sum(d["loss_events"] for d in per.values()), "event_reversal_splits": sum(d["split_events"] for d in per.values()),
            "ten_largest_events": [{"event": k, "final_units": n, "I_e": i} for k, n, i in top],
            "assumption": "homogeneity within a stratum: an event's reversal probability does not depend on its unit count"}


# --- blocks -----------------------------------------------------------------------------------------------------------------------------

def mean(xs) -> float | None:
    xs = list(xs)
    return float(sum(xs) / len(xs)) if xs else None


def quantiles(xs) -> dict:
    v = np.array(sorted(xs), dtype=float)
    if not len(v):
        return {"n": 0}
    p = np.percentile(v, [10, 25, 50, 75, 90])
    return {"n": int(len(v)), "p10": float(p[0]), "p25": float(p[1]), "median": float(p[2]), "p75": float(p[3]), "p90": float(p[4]), "max": float(v[-1])}


def headline(final: list[dict], spec: dict) -> dict:
    stats = {"theta": lambda u: u["n1"], "theta_L2": lambda u: u["n2"], "c": lambda u: u["c"], "r_eff": lambda u: u["L"], "P_loss": lambda u: float(u["L"] == 1.0),
             "P_split": lambda u: float(u["L"] == 0.5), "fee_L1": lambda u: u["fee_L1"], "fee_L2": lambda u: u["fee_L2"], "capital": lambda u: u["cap"],
             "one_minus_mid_f": lambda u: 1.0 - u["mid_f"], "h": lambda u: u["h"]}
    return event_boot(final, stats, spec) | _theta_e(final, spec)


def _theta_e(final: list[dict], spec: dict) -> dict:
    groups: dict = defaultdict(list)
    for u in final:
        groups[u["cluster"]].append(u["n1"])
    keys = sorted(groups)
    if not keys:
        return {}
    em = np.array([sum(groups[k]) / len(groups[k]) for k in keys])
    acc = [em[idx].mean(axis=1) for idx in _draws(len(keys), spec)]
    lo, hi = ci_of(np.concatenate(acc), spec)
    return {"theta_E": {"est": float(em.mean()), "lo": lo, "hi": hi, "degenerate": bool(lo == hi)}}


def cell_row(units: list[dict], spec: dict) -> dict:
    fin = [u for u in units if u["final"]]
    th = event_boot(fin, {"theta": lambda u: u["n1"]}, spec).get("theta") if fin else None
    fin_events = len({u["cluster"] for u in fin})
    return {"N": len(units), "events": len({u["cluster"] for u in units}), "final": len(fin), "final_events": fin_events,
            "mean_c": mean(u["c"] for u in fin), "r_eff": mean(u["L"] for u in fin), "mean_fee_L1": mean(u["fee_L1"] for u in fin), "mean_capital": mean(u["cap"] for u in fin),
            "theta": th, "nonfinal": dict(Counter(u["cls"] for u in units if not u["final"])),
            "thin": bool(len(fin) < spec["thin"]["final_units"] or fin_events < spec["thin"]["events"])}


SPLIT_KEY = {"S1": "tier", "S2": "s2", "S3": "ladder", "S4": "fee_class", "S5": "side", "S7": "end_rel", "S8": "members", "S10": "s10"}


def split_cell(u: dict, name: str) -> str:
    if name == "S6":
        return j0.zone_of(u["c"])
    if name == "S9":
        t = u["tick"]
        return "0.001" if t == 0.001 else "0.01" if t == 0.01 else "other_or_missing"
    return str(u[SPLIT_KEY[name]])


def splits(units: list[dict], spec: dict) -> dict:
    out: dict = {}
    for name, cells in spec["cells"].items():
        by: dict = defaultdict(list)
        for u in units:
            by[split_cell(u, name)].append(u)
        out[name] = {c: cell_row(by.get(c, []), spec) for c in cells} | {f"_unlisted:{c}": cell_row(v, spec) for c, v in sorted(by.items()) if c not in cells}
    return out


def capacity_block(units: list[dict]) -> dict:
    cov = [u for u in units if u["sweep_covered"]]
    usd = [u["sweep_ask_size_1"] * u["sweep_best_ask"] for u in cov if u.get("sweep_best_ask") is not None]
    per_day: dict = defaultdict(float)
    for u in cov:
        if u.get("sweep_best_ask") is not None:
            per_day[sp.iso(u["k_start_ts"])[:10]] += u["sweep_ask_size_1"] * u["sweep_best_ask"]
    agree: Counter = Counter()
    for u in cov:
        if u.get("sweep_best_ask") is not None and u["tick"] and math.isfinite(u["tick"]) and u["tick"] > 0:
            agree[str(int(round((u["sweep_best_ask"] - u["ask_f"]) / u["tick"])))] += 1
        elif u.get("sweep_best_ask") is not None:
            agree["tick_unknown"] += 1
    return {"label": f"covered subset only (coverage {100 * len(cov) / len(units):.2f}%), not the population's capacity" if units else "no units",
            "coverage": len(cov) / len(units) if units else None, "covered": len(cov), "units": len(units),
            "cap_usd": quantiles(usd), "cap_usd_sum_per_utc_day": dict(sorted(per_day.items())),
            "depth_ask_1c": quantiles([u["sweep_depth_ask_1c"] for u in cov if u.get("sweep_depth_ask_1c") is not None and math.isfinite(u["sweep_depth_ask_1c"])]),
            "composition_covered": {"S6": dict(Counter(j0.zone_of(u["c"]) for u in cov)), "S7": dict(Counter(u["end_rel"] for u in cov))},
            "composition_population": {"S6": dict(Counter(j0.zone_of(u["c"]) for u in units)), "S7": dict(Counter(u["end_rel"] for u in units))},
            "ask_agreement_ticks_sweep_minus_rows": dict(sorted(agree.items()))}


def engine_log(engine_root: Path | None) -> dict:
    out: dict = {}
    if engine_root is None:
        return out
    for p in sorted((Path(engine_root) / "logs").glob("resolutions-*.jsonl")):
        for line in p.read_text().splitlines():
            try:
                d = json.loads(line)
                out[int(d["market_id"])] = d
            except (ValueError, KeyError, TypeError):
                continue
    return out


def cross_check(units: list[dict], log: dict) -> dict:
    """8.3, read-out only: agreement of state and y with the engine's resolution log for units also present there (counts; disagreements listed)."""
    agree = dis = 0
    lst = []
    for u in units:
        d = log.get(u["market_id"])
        if d is None:
            continue
        mine_y = None if u["cls"] not in ("resolved_favoured", "resolved_other") else (1 if (u["side"] == "YES") == (u["cls"] == "resolved_favoured") else 0)
        if d.get("state") == "resolved":
            ok = mine_y is not None and d.get("y") == mine_y
        else:
            ok = u["cls"] == d.get("state") or (u["cls"] == "split_50_50" and d.get("state") == "split_50_50")
        agree += int(ok)
        if not ok:
            dis += 1
            lst.append({"market_id": u["market_id"], "m1": u["cls"], "engine_state": d.get("state"), "engine_y": d.get("y")})
    return {"units_in_log": agree + dis, "agree": agree, "disagree": dis, "disagreements": lst[:100], "note": "the pinned source governs"}


def survivorship(units: list[dict], log: dict) -> dict:
    """13: per UTC day, M1's first-seen proposals (units) against the engine log's markets by closed day; counts only, lagged and partial.
    The log carries no category, so the log counts are all categories (not the non-sports ex-crypto restriction of the text)."""
    first: Counter = Counter(sp.iso(u["k_start_ts"])[:10] for u in units)
    closed: Counter = Counter()
    for d in log.values():
        t = parse_closed(d.get("closed_time"))
        if math.isfinite(t):
            closed[sp.iso(t)[:10]] += 1
    in_log = Counter(sp.iso(u["k_start_ts"])[:10] for u in units if u["market_id"] in log)
    days = sorted(set(first) | set(closed))
    return {"label": "lagged partial read: the engine log holds only its candidates and carries no category", "per_day": {d: {"m1_first_seen_units": first.get(d, 0), "log_markets_closed_that_day_all_categories": closed.get(d, 0), "m1_units_in_log": in_log.get(d, 0)} for d in days}}


# --- pins and manifest -------------------------------------------------------------------------------------------------------------------

def verify_manifest(store: Path, pins: dict) -> dict:
    mp = Path(store) / "manifest.json"
    if not mp.exists():
        raise ex.M1Refusal("analysis refuses: no J2 manifest")
    if sp.sha256_file(mp) != pins.get("manifest_sha256"):
        raise ex.M1Refusal("analysis refuses: J2 manifest hash differs from the pin")
    man = json.loads(mp.read_text())
    bad = [f for f, h in man["files"].items() if not (Path(store) / f).exists() or sp.sha256_file(Path(store) / f) != h]
    if bad:
        raise ex.M1Refusal(f"analysis refuses: files differ from the J2 manifest: {bad[:5]}")
    return man


def check_run_pins(spec: dict, pins: dict, paths=None, design=None) -> dict:
    rec = sp.check_pins(spec, paths, design)
    if pins.get("spec_sha") != sp.spec_sha(spec) or pins.get("code_sha") != sp.code_sha():
        raise sp.PinMismatch({"spec_sha": {"pin": pins.get("spec_sha"), "actual": sp.spec_sha(spec)}, "code_sha": {"pin": pins.get("code_sha"), "actual": sp.code_sha()}})
    return rec


# --- the analysis -------------------------------------------------------------------------------------------------------------------------

def run_analysis(store: Path, pins: dict, out: Path | None, spec: dict = sp.SPEC, now: float | None = None, engine_root: Path | None = None,
                 paths: dict | None = None, design: Path | None = None) -> dict:
    now = time.time() if now is None else now
    if now < sp.ts(spec, "readout_utc") + spec["analysis_after_readout_s"]:
        raise ex.M1Refusal("analysis refuses before READOUT_UTC + 12 h")
    if out is None:
        raise ex.M1Refusal("analysis requires --out")
    out = Path(out)
    if out.exists():
        raise ex.M1Refusal("analysis refuses to overwrite --out")
    pin_rec = check_run_pins(spec, pins, paths, design)
    store = Path(store)
    man = verify_manifest(store, pins)
    audit = ex.audit_chain(store, spec)
    units, lc = load_units(store, pins)
    readout = load_readout(store)
    wait_notes = classify_units(units, readout, spec)
    _init, chain, _late = ex.load_statuses(store)
    funnel: Counter = Counter()
    contested_n = 0
    contested_c = 0.0
    for d in chain:
        if d["kind"] == "processed":
            funnel.update(d["funnel"])
            contested_n += d.get("contested_n", 0)
            contested_c += d.get("contested_c_sum", 0.0)
    final = [u for u in units if u["final"]]
    nf = len(final)
    classes = Counter(u["cls"] for u in units)
    nonfinal = sum(classes[c] for c in NONFINAL)
    events_all = {u["cluster"] for u in units}
    covered_u = [u for u in units if u["cls"] not in ("not_found", "unavailable_fetch")]
    cov_units = len(covered_u) / len(units) if units else None
    by_ev: dict = defaultdict(list)
    for u in units:
        by_ev[u["cluster"]].append(u["cls"] not in ("not_found", "unavailable_fetch"))
    cov_events = sum(sum(v) / len(v) for v in by_ev.values()) / len(by_ev) if by_ev else None
    void: list = []
    if not audit["ok"]:
        void.append(f"11.2(a) chain broken: {audit['breaks'][:5]}")
    if units and (cov_units < spec["coverage_floor"] or cov_events < spec["coverage_floor"]):
        void.append(f"11.4 coverage below the floor: units {cov_units:.4f}, events {cov_events:.4f}")
    if lc.get("lines") and lc.get("dropped_pin_or_role_mismatch", 0) / lc["lines"] > spec["void_sha_mismatch_share"]:
        void.append("11.5 unit lines with a different spec_sha / code_sha / role exceed 1%")
    reg_commit = pins.get("registration_commit_utc")
    if reg_commit is not None and sp.ts(spec, "registered_utc") < sp_ts(reg_commit) + 86400:
        void.append("11.6 the window started before the registration commit plus 24 h")
    res: dict = {"kind": "M1-A analysis (descriptive measurement; no test)", "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "role": sp.ROLE, "pin_check": pin_rec,
                 "manifest_sha256": pins["manifest_sha256"], "chain_audit": audit, "unit_lines": lc, "wait_notes": dict(wait_notes), "void_reasons": void,
                 "funnel_k_time": dict(funnel), "contested": {"n": contested_n, "mean_c_nearer_1": contested_c / contested_n if contested_n else None},
                 "classes": dict(sorted(classes.items())), "eligible_units": len(units), "final_units": nf, "events": len(events_all),
                 "coverage": {"units": cov_units, "events_event_weighted": cov_events, "floor": spec["coverage_floor"], "final_share_of_eligible": nf / len(units) if units else None},
                 "ask_f_at_1": {"units": sum(1 for u in units if u["ask_f_at_1"]), "share": sum(1 for u in units if u["ask_f_at_1"]) / len(units) if units else None,
                                "note": "entry price of a venue placeholder (c = 0); kept as declared; bias is toward lower theta (3.2, E6 note)"},
                 "uma_status_by_class": {c: dict(Counter(str(u["uma"]) for u in units if u["cls"] == c)) for c in sorted(classes)},
                 "m2_overlap": "not computed here (M2's store is not read)"}
    nums: dict = {}
    if nf:
        h = headline(final, spec)
        tb = tail_bound(final, spec)
        mc, mf2, mcap = mean(u["c"] for u in final), mean(u["fee_L2"] for u in final), mean(u["cap"] for u in final)
        theta_low = mc - tb["T_U"] - mf2 - mcap
        nf_loss_set = [u for u in units if u["final"] or u["cls"] == "not_found"]
        theta_nfl = mean((u["n1"] if u["final"] else u["n_loss"]) for u in nf_loss_set)
        theta_w = mean((u["n1"] if u["final"] else u["n_loss"]) for u in units)
        day = day_block_boot(final, lambda u: u["n1"], spec)
        hw = (h["theta"]["hi"] - h["theta"]["lo"]) / 2
        widest = max(((h["theta"]["hi"] - h["theta"]["lo"]), "event_bootstrap"), ((day["hi"] - day["lo"]), "day_block_bootstrap")) if day else (h["theta"]["hi"] - h["theta"]["lo"], "event_bootstrap")
        waits = [u["w_h"] for u in final]
        co = spec["coarse"]
        coarse_rules = {"1_final_units_below": nf < co["min_final_units"], "2_ci_half_width_above": hw > co["max_ci_half_width_ps"], "3_tu_above": tb["T_U"] > co["max_tu_ps"],
                        "4_nonfinal_share_above": (nonfinal / len(units)) > co["max_nonfinal_share"], "5_slot_coverage_below": man["slot_coverage"] < co["min_slot_coverage"]}
        nums = {"headline_components": h, "theta_low": theta_low, "theta_W": theta_w, "theta_not_found_as_loss": theta_nfl, "tail_bound": tb,
                "theta_day_block_sensitivity": day, "wider_interval": {"width": widest[0], "which": widest[1]},
                "c_quantiles": quantiles([u["c"] for u in final]), "wait_hours": quantiles(waits), "bid_side_quoted_carry_gross": quantiles([1.0 - u["bid_f"] for u in final]),
                "capacity": capacity_block(units), "gaps_s": {"sidecar_minus_row": j0.qdist([u["gap_ext_row_s"] for u in units]), "sweep_minus_row": j0.qdist([u["gap_sweep_row_s"] for u in units if u["gap_sweep_row_s"] is not None])},
                "coarse": {"rules_fired": coarse_rules, "coarse": any(coarse_rules.values()), "thresholds": co, "ci_half_width": hw, "nonfinal_share": nonfinal / len(units), "slot_coverage": man["slot_coverage"]},
                "splits": splits(units, spec), "bootstrap": spec["bootstrap"]}
        cap = nums["capacity"]
        capy = f"{cap['cap_usd']['median']:.2f} USD median" if cap["cap_usd"].get("n") else "unavailable"
        th = h["theta"]
        nums["ledger_line"] = (f"measured (prospective, k = 0; units seen at a 2 h capture and two-sided at k): unit-weighted mean net per share theta = {th['est']:.6f} "
                               f"[{th['lo']:.6f}, {th['hi']:.6f}], theta_low = {theta_low:.6f} (bound), theta_W = {theta_w:.6f} (worst case), cost-model-v1, conservative fee, touch, "
                               f"size-unlimited, capacity {capy} (covered subset {100 * (cap['coverage'] or 0):.2f}%){' [reported coarse]' if nums['coarse']['coarse'] else ''}.")
        assert not BANNED.search(json.dumps(nums, default=str)), "banned wording in output"
    elif not void:
        void_note = "no final-state units"
        res["note"] = void_note
    log = engine_log(engine_root)
    if log:
        res["cross_check_engine_log"] = cross_check(units, log)
        res["survivorship"] = survivorship(units, log)
    if void:
        res["void"] = True
        res["not_a_measurement"] = nums
    else:
        res["void"] = False
        res.update(nums)
    ex._write_once(out, ex.dumps(res).encode(), lambda a, b: False)
    return res
