# ruff: noqa: E501
"""LT6 (docs/research_lab/LIVE_TESTS_6.md): the readings around the four primaries. NOTHING here changes a verdict.

The binding label rules (mechanism readings M1/M3 of V, K and D, the placebos of V, K and B), the attrition rule with Lee-type bounds
(1.5), the *coverage-limited* and *sweep-missing* labels (1.9), the reported secondaries and arms, the Thanksgiving sensitivity (1.1)
and the economics (1.10) are computed here on the prepared frames of ``live_tests6_analysis``. Every reading is a pure function of
the frame (and the frozen counts), uses the primary's fit (``fit6``) with the same inference, and counts 0 trials (1.11).

Imported lazily by ``live_tests6_analysis.analyze_frames`` so the two modules do not import each other at load time.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import live_tests3_analysis as la3
from . import live_tests6 as lt

HALF = 0.5  # "at least half of D" in every placebo / mechanism rule


def _la():
    from . import live_tests6_analysis as la

    return la


# --- small helpers -----------------------------------------------------------------------------------------------------------


def _kw(n_boot: int | None) -> dict:
    return {"n_boot": n_boot} if n_boot is not None else {}


def fit_reading(frame: pd.DataFrame, y, term: str, controls: list[str], spec: dict, test: str, offset: int, *, sign: int = +1,
                treated: str | None = None, n_boot: int | None = None) -> dict:
    """One reading's fit: the primary's estimator and inference on ``frame`` with another target or term. ``offset`` shifts the seed so
    two readings never share a bootstrap stream. A frame too small to fit gives ``{"testable": False}``."""
    la = _la()
    y = np.asarray(y, float)
    if len(frame) < 10 or int(np.isfinite(y).sum()) < 10:
        return {"testable": False, "reason": "fewer than 10 rows", "n": int(np.isfinite(y).sum())}
    ctrl = [c for c in controls if c != term]
    try:
        return la.strip(la.fit6(frame.reset_index(drop=True), y, term, ctrl, sign=sign, treated_col=treated, seed=int(spec["seeds"][test]) + offset, **_kw(n_boot)))
    except Exception as e:  # a degenerate design (collinear controls, one class) is a not-testable reading, never a crash of the analysis
        return {"testable": False, "reason": f"{type(e).__name__}: {e}"}


def one_sided_sig(r: dict | None, sign: int = +1) -> bool:
    """One-sided p < 0.05 in the predicted direction."""
    r = r or {}
    return bool(r.get("testable") and r.get("p") is not None and float(r["p"]) < 0.05 and sign * float(r["beta"]) > 0)


def reaches_half(primary_beta, chk: dict | None, sign: int = +1) -> bool:
    """The check is one-sided significant and at least half of the primary (LT3's ``check_fraction``)."""
    return la3.check_fraction(primary_beta, chk, sign, True, HALF)


def _supported(verdict: str | None) -> bool:
    return str(verdict or "").startswith("Supported")


def _mid(frame: pd.DataFrame, tag: str) -> np.ndarray:
    return la3.mid_at(frame, tag)


def _sx(frame: pd.DataFrame) -> np.ndarray:
    return np.sign(frame["x"].to_numpy(float))


# --- binding label rules (pure functions of the readings) ------------------------------------------------------------------------


def label_rules(test: str, supported: bool, prim_beta: float | None, rd: dict) -> list[str]:
    """The binding mechanism / placebo labels of ``test`` from the readings ``rd`` (1.9 and the test's section). A label needs the
    primary Supported for the mechanism readings; the placebo labels follow the design's own conditions."""
    out: list[str] = []
    pb = prim_beta
    if test == "V":
        if supported and not reaches_half(pb, rd.get("M1")):
            out.append("sweep-stream specific")
        m3 = rd.get("M3") or {}
        if supported and one_sided_sig(m3.get("lt"), -1) and not one_sided_sig(m3.get("la"), +1):
            out.append("depletion mechanics (the move's own footprint, not a vote)")
        if reaches_half(pb, rd.get("P_vprev")):
            out.append("standing skew, not a reaction")
    elif test == "K":
        if supported and not reaches_half(pb, rd.get("M1")):
            out.append("Gamma-quote mechanics")
        m3 = rd.get("M3") or {}
        if supported and not one_sided_sig(m3.get("running")) and one_sided_sig(m3.get("finished")):
            out.append("not schedule pressure")
        if reaches_half(pb, rd.get("P1")):
            out.append("size identity not shown")
        if reaches_half(pb, rd.get("P2")):
            out.append("persistent trait")
    elif test == "D":
        m1, rem = rd.get("M1") or {}, rd.get("M1_remainder") or {}
        contradicted = bool(rem.get("testable") and rem.get("ci95_cons") and rem["ci95_cons"][1] < 0)
        if supported and one_sided_sig(m1) and contradicted:
            out.append("transient")
        if reaches_half(pb, rd.get("P1")):
            out.append("not template-specific")
    else:
        if reaches_half(pb, rd.get("P_fake_birth")):
            out.append("event-level volatility, not the listing")
    return out


# --- attrition and Lee-type bounds (1.5) --------------------------------------------------------------------------------------------


def attrition_reading(test: str, pre: pd.DataFrame | None, frame: pd.DataFrame, spec: dict, refit) -> dict:
    """The attrition rule: non-``two_sided`` share by contrasted class (capture_missing and pending excluded); if the absolute
    difference exceeds 2 pp the label *attrition-differential* applies and Lee-type bounds re-estimate the primary at both trims.
    ``refit(frame, y)`` is the primary's fit on a sub-frame."""
    if pre is None or not len(pre):
        return {"computed": False}
    pair = ("upper", "lower") if test == "V" else (1, 0)
    cls = pre["cls"].to_numpy(dtype=object)
    att = la3.attrition(pre["status"].to_numpy(dtype=object), cls, pair, float(spec["labels"]["attrition_pp"]))
    out = {"computed": True, **att}
    if att.get("triggered") and len(frame):
        la = _la()
        y = frame[la.PRIMARY[test]["y"]].to_numpy(float)
        if test == "V":
            cuts, c_v, s_v = spec["v"]["terciles"], spec["v"]["c_v"], spec["v"]["s_v"]
            zv = (frame["v"].to_numpy(float) - c_v) / s_v
            fc = np.where(zv >= cuts[1], "upper", np.where(zv <= cuts[0], "lower", None))
        else:
            fc = frame[la.PRIMARY[test]["term"]].to_numpy(float).astype(int).astype(object)
        out["lee"] = la3.lee_bounds(frame, y, fc, pair, att, refit)
    return out


# --- coverage-limited and sweep-missing (1.9) -----------------------------------------------------------------------------------------


def pass_counts(root: Path, kind: str, spec: dict | None = None) -> dict:
    """Numeric ``counts`` summed over the reader's ``<kind>_frozen`` log lines (``passes.jsonl``). With a PINNED ``spec`` only the lines of
    the pinned spec (``spec_sha``) and of captures inside ``[registered_utc, end_utc)`` are summed (re-check fix); the capture time of a
    line is its id / ``capture_id`` name time."""
    import json

    p = Path(root) / "passes.jsonl"
    tot: dict = {}
    if not p.exists():
        return tot
    pinned = bool(spec and spec.get("_pinned"))
    want = spec["_sha256"][:16] if pinned else None
    lo, hi = (lt.epoch(spec["registered_utc"]), lt.epoch(spec["end_utc"])) if spec and spec.get("registered_utc") and spec.get("end_utc") else (None, None)
    for line in p.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != f"{kind}_frozen":
            continue
        if pinned and r.get("spec_sha") != want:
            continue
        if lo is not None:
            t = lt.l5._name_time(str(r.get("capture_id") or r.get("id") or ""))
            if t == t and not (lo <= t < hi):
                continue
        for k_, v in (r.get("counts") or {}).items():
            if isinstance(v, (int, float)):
                tot[k_] = tot.get(k_, 0) + v
    return tot


def coverage_label(counts: dict, spec: dict) -> str | None:
    """K: *coverage-limited* when interval-truncated sampled traded movers with >= 4 rows exceed 2% of those movers."""
    n = counts.get("traded_ge4_rows", 0)
    if not n:
        return None
    sh = counts.get("traded_ge4_truncated", 0) / n
    return f"coverage-limited ({sh:.1%} of sampled traded movers with >= 4 rows interval-truncated)" if sh > spec["labels"]["coverage_limited_truncated_share"] else None


def sweep_missing_label(acc: dict, spec: dict) -> str | None:
    """V: *sweep-missing* when ``.nosweep`` / ``.noprevsweep`` passes exceed 2% of V's origin passes (LT4's rule, inherited by 1.5)."""
    # the ONE "origin passes" denominator of load_kind (LIVE_TESTS_6.md 17): in-window frozen files (empty ones too) plus every in-window marker
    tot = acc.get("origin_passes", acc.get("files", 0) + sum(acc.get(f"{m}_files", 0) for m in ("late", "nosweep", "noprevsweep", "noprev", "e022boundary")))
    miss = acc.get("nosweep_files", 0) + acc.get("noprevsweep_files", 0)
    if not tot:
        return None
    sh = miss / tot
    return f"sweep-missing ({sh:.1%} of origin passes)" if sh > spec["labels"]["sweep_missing_share"] else None


# --- the readings of each test -------------------------------------------------------------------------------------------------------


def _clip_pop(frame: pd.DataFrame, mask_clip: np.ndarray) -> pd.DataFrame:
    """Clip-free units plus the clip units in ``mask_clip`` (K's running / finished split)."""
    return frame[(frame["CL"] == 0) | ((frame["CL"] == 1) & mask_clip)].reset_index(drop=True)


def readings_v(frame: pd.DataFrame, extras: dict, spec: dict, n_boot: int | None) -> dict:
    ctrl = lt.CONTROLS_V
    sx = _sx(frame)
    out: dict = {}
    out["M1"] = fit_reading(frame, frame["c_skip_m1"].to_numpy(float), "zv", ctrl, spec, "V", 11, n_boot=n_boot)
    c_sw = sx * (_mid(frame, "s1") - (frame["sbid_k"].to_numpy(float) + frame["sask_k"].to_numpy(float)) / 2.0)
    out["M2_own_sweep"] = fit_reading(frame, c_sw, "zv", ctrl, spec, "V", 12, n_boot=n_boot)
    y = frame["c_vskip"].to_numpy(float)
    f2 = frame.assign(z_lt=frame["lt"], z_la=frame["la"])
    out["M3"] = {"lt": fit_reading(f2, y, "z_lt", [c for c in ctrl if c != "zv"] + ["z_la"], spec, "V", 13, sign=-1, n_boot=n_boot),
                 "la": fit_reading(f2, y, "z_la", [c for c in ctrl if c != "zv"] + ["z_lt"], spec, "V", 14, sign=+1, n_boot=n_boot)}
    out["P_vprev"] = fit_reading(frame, y, "z_vprev", [c for c in ctrl if c != "z_vprev"], spec, "V", 15, n_boot=n_boot)
    # secondaries (reported)
    sec: dict = {}
    if "dspread" in frame:
        f3 = frame.assign(dsp_le0=(frame["dspread"] <= 0).astype(float))
        f3["zv_x_dsp"] = f3["zv"] * f3["dsp_le0"]
        sec["S1_zv_x_dspread_le0"] = fit_reading(f3, y, "zv_x_dsp", [*ctrl, "dsp_le0"], spec, "V", 21, n_boot=n_boot)
    if {"dbid1_k", "dask1_k"} <= set(frame.columns):
        imb1 = sx * lt.imbalance(frame["dbid1_k"], frame["dask1_k"])
        sec["S2_imbalance_1c"] = fit_reading(frame.assign(zv1=(imb1 - np.nanmean(imb1)) / (np.nanstd(imb1) or 1.0)), y, "zv1", ctrl, spec, "V", 22, n_boot=n_boot)
    arms = (extras or {}).get("arms") or {}
    if "sports" in arms and len(arms["sports"]):
        a = arms["sports"]
        sec["S3_sports_arm"] = fit_reading(a, a["c_vskip"].to_numpy(float), "zv", ctrl, spec, "V", 23, n_boot=n_boot) if "c_vskip" in a else {"testable": False}
        sec["S3_sports_arm"]["units"] = int(len(a))
    for nm, m in (("S4_traded", frame["cls"] == "traded"), ("S4_quote_only", frame["cls"] == "quote_only")):
        sub = frame[m.to_numpy()].reset_index(drop=True)
        sec[nm] = fit_reading(sub, sub["c_vskip"].to_numpy(float), "zv", ctrl, spec, "V", 24 + len(nm) % 3, n_boot=n_boot)
    if "status_h4" in frame:
        y6 = sx * (_mid(frame, "h4") - _mid(frame, "h1"))
        sec["S5_6h_gamma_target"] = fit_reading(frame, y6, "zv", ctrl, spec, "V", 27, n_boot=n_boot)
    sec["S7_counts"] = {"by_class": {str(k_): int(v) for k_, v in frame["cls"].value_counts().items()}}
    out["secondaries"] = sec
    return out


def readings_k(frame: pd.DataFrame, extras: dict, spec: dict, n_boot: int | None) -> dict:
    ctrl = lt.CONTROLS_K
    sx = _sx(frame)
    out: dict = {}
    out["M1"] = fit_reading(frame, sx * (_mid(frame, "s3") - _mid(frame, "s1")), "CL", ctrl, spec, "K", 11, n_boot=n_boot)
    out["M2"] = fit_reading(frame, sx * (_mid(frame, "h1") - frame["mid"].to_numpy(float)), "CL", ctrl, spec, "K", 12, n_boot=n_boot)
    split = float(spec["k"]["running_split_s"])
    age = frame["last_clip_age"].to_numpy(float)
    run, fin = np.isfinite(age) & (age <= split), np.isfinite(age) & (age > split)
    pr, pf = _clip_pop(frame, run), _clip_pop(frame, fin)
    out["M3"] = {"running": fit_reading(pr, pr["c_skip"].to_numpy(float), "CL", ctrl, spec, "K", 13, n_boot=n_boot),
                 "finished": fit_reading(pf, pf["c_skip"].to_numpy(float), "CL", ctrl, spec, "K", 14, n_boot=n_boot),
                 "units": {"running": int(run[frame["CL"].to_numpy() == 1].sum()), "finished": int(fin[frame["CL"].to_numpy() == 1].sum())}}
    # P1: the near-identical placebo, a fake class against clip-free units (clip-free in the real sense)
    free = frame[frame["CL"] == 0].reset_index(drop=True)
    if "p1_clip_share" in free:
        f1 = free.assign(P1=(free["p1_clip_share"] >= spec["k"]["clip_share_min"] - 1e-12).astype(float))
        out["P1"] = fit_reading(f1, f1["c_skip"].to_numpy(float), "P1", [c for c in ctrl], spec, "K", 15, n_boot=n_boot)
        out["P1"]["fake_units"] = int(f1["P1"].sum())
    # P2: the previous pass's class (the same market's frozen line one slot earlier) with the current class held fixed
    prev = (extras or {}).get("k_prev_class")
    if prev is not None:
        key = list(zip(frame["market_id"].astype(str), frame["slot"].astype(int) - 1, strict=False))
        pc = np.array([prev.get(k_) for k_ in key], dtype=object)
        known = np.array([v is not None for v in pc], bool)
        # PC = 1 for a previous class of clip, 0 for clip_free, interior or nan (declared coding: the persistent-trait test contrasts clip against
        # everything else); units with NO known previous class (no frozen line one slot earlier) are dropped and counted separately
        f2 = frame[known].assign(PC=[1.0 if v == "clip" else 0.0 for v in pc[known]]).reset_index(drop=True)
        out["P2"] = fit_reading(f2, f2["c_skip"].to_numpy(float), "PC", [*ctrl, "CL"], spec, "K", 16, n_boot=n_boot)
        out["P2"]["units_no_known_previous_class"] = int((~known).sum())
        out["P2"]["units_prev_clip"] = int(f2["PC"].sum())
    sec: dict = {}
    raw = (extras or {}).get("raw")
    if raw is not None and len(raw):
        r0 = raw[raw["class_k"].isin(["clip", "clip_free", "interior"])]
        sec["S6_counts_by_class"] = {str(k_): int(v) for k_, v in r0["class_k"].value_counts().items()}
    f5 = frame.assign(CL5=(frame["clip_share"] >= 0.5).astype(float))
    sec["S2_cut_0.5"] = fit_reading(f5, f5["c_skip"].to_numpy(float), "CL5", ctrl, spec, "K", 22, n_boot=n_boot)
    if "s3_clip_share" in frame:
        f3 = frame.assign(S3=(frame["s3_clip_share"] >= spec["k"]["clip_share_min"] - 1e-12).astype(float))
        sec["S3_notional_clips"] = fit_reading(f3, f3["c_skip"].to_numpy(float), "S3", ctrl, spec, "K", 23, n_boot=n_boot)
    for nm, m, off in (("S4_sports", frame["sports"] == 1, 24), ("S4_non_sports", frame["sports"] == 0, 27)):  # distinct bootstrap offsets (re-check fix)
        sub = frame[m.to_numpy()].reset_index(drop=True)
        sec[nm] = fit_reading(sub, sub["c_skip"].to_numpy(float), "CL", ctrl, spec, "K", off, n_boot=n_boot)
    if "status_h4" in frame:
        sec["S5_6h_target"] = fit_reading(frame, sx * (_mid(frame, "h4") - _mid(frame, "h1")), "CL", ctrl, spec, "K", 26, n_boot=n_boot)
    out["secondaries"] = sec
    return out


def readings_d(frame: pd.DataFrame, extras: dict, spec: dict, n_boot: int | None) -> dict:
    ctrl = lt.CONTROLS_D
    out: dict = {}
    m1 = _mid(frame, "h3") - _mid(frame, "h1")
    out["M1"] = fit_reading(frame, m1, "LT", ctrl, spec, "D", 11, treated="LT", n_boot=n_boot)
    out["M1_remainder"] = fit_reading(frame, _mid(frame, "h12") - _mid(frame, "h3"), "LT", ctrl, spec, "D", 12, treated="LT", n_boot=n_boot)
    out["M2"] = fit_reading(frame, _mid(frame, "h12") - frame["mid"].to_numpy(float), "LT", ctrl, spec, "D", 13, treated="LT", n_boot=n_boot)
    arms = (extras or {}).get("arms") or {}
    # P1 (re-check fix 4): the same model (LT on y22, the primary's controls and inference) on the frozen ``nonbydate`` arm: non-by-date old ends,
    # later vs no-change units. Label "not template-specific" when one-sided significant and at least half of D_D (label_rules).
    nb = arms.get("nonbydate")
    if nb is not None and len(nb):
        out["P1"] = fit_reading(nb, nb["y22"].to_numpy(float), "LT", ctrl, spec, "D", 14, treated="LT", n_boot=n_boot)
        out["P1"]["units"], out["P1"]["later"] = int(len(nb)), int((nb["LT"] == 1).sum())
    else:
        out["P1"] = {"computed": False, "testable": False, "reason": "no frozen nonbydate-arm units with a known target"}
    y = frame["y22"].to_numpy(float)
    sec: dict = {}
    old7 = frame["old_end_days"].to_numpy(float) >= float(spec["d"]["old_end_subset_days"])
    sub = frame[(frame["LT"] == 0).to_numpy() | old7].reset_index(drop=True)
    sec["S0_old_end_ge_7d"] = fit_reading(sub, sub["y22"].to_numpy(float), "LT", ctrl, spec, "D", 21, treated="LT", n_boot=n_boot)
    later = frame[frame["LT"] == 1].reset_index(drop=True)
    if len(later) and "delta_s" in later:
        r_ = later["delta_s"].to_numpy(float) / np.maximum((later["T_new_h"].to_numpy(float) * 3600.0 - later["delta_s"].to_numpy(float)), 1.0)
        sec["S1_dose_among_later"] = fit_reading(later.assign(dose=r_), later["y22"].to_numpy(float), "dose", [c for c in ctrl if c != "LT"], spec, "D", 22, n_boot=n_boot)
    f4 = frame.assign(LT_x_upd=frame["LT"] * frame["updated_changed"])
    sec["S4_updated_at_split"] = fit_reading(f4, y, "LT_x_upd", [*ctrl, "LT"], spec, "D", 23, n_boot=n_boot) if "updated_changed" in frame else {"testable": False}
    sec["S3_maker_abs_y22"] = fit_reading(frame, np.abs(y), "LT", ctrl, spec, "D", 24, treated="LT", n_boot=n_boot)
    sec["S3_maker_abs_first_pass"] = fit_reading(frame, np.abs(_mid(frame, "h1") - frame["mid"].to_numpy(float)), "LT", ctrl, spec, "D", 25, treated="LT", n_boot=n_boot)
    for nm, a in arms.items():
        if len(a):
            sec[f"arm_{nm}"] = {"units": int(len(a)), "later": int((a["cls"] == "later").sum()), "mean_y22_later": _mean_y22(a)}
    sec["S6_counts"] = {"by_class": {str(k_): int(v) for k_, v in frame["cls"].value_counts().items()}}
    raw = (extras or {}).get("raw")
    if raw is not None and len(raw):
        rm = raw[raw["arm"].astype(str) == "main"] if "arm" in raw else raw  # the primary population only: reported arms never enter these counts
        sec["S2_earlier_arm_units"] = int((rm["cls"] == "earlier").sum())
        sec["S7_overdue_units"] = int((rm["cls"] == "overdue").sum())
    out["secondaries"] = sec
    return out


def _mean_y22(a: pd.DataFrame) -> float | None:
    if "status_h1" not in a or "status_h12" not in a:
        return None
    sub = a[a["cls"] == "later"]
    y = _mid(sub, "h12") - _mid(sub, "h1")
    return float(np.nanmean(y)) if np.isfinite(y).any() else None


def fake_birth_frame(frame: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, dict]:
    """The placebo's population (section 5): one fake birth per real birth of an event, drawn (seed 20261364, real births in sorted
    (event, slot) order) from the event's no-birth slots at least 12 slots from every real birth of that event and in the same tercile
    of the event's leave-one-out ``|2 h|`` move as the real birth (cuts = the census's ``fake_birth_terciles``). The fake birth's
    incumbents are relabelled birth, real-birth units leave the sample. Counts (births, fakes drawn, none available) are returned."""
    cuts = spec["b"].get("fake_birth_terciles")
    cnt = {"real_births": 0, "fake_drawn": 0, "none_available": 0}
    if cuts is None or "loo_a1" not in frame:
        return pd.DataFrame(), {**cnt, "reason": "census terciles unavailable"}
    rng = np.random.default_rng(int(spec["seeds"]["B_fake_birth"]))
    ev = frame["event_id"].astype(str).to_numpy()
    sl = frame["slot"].to_numpy(int)
    ter = np.where(frame["loo_a1"].to_numpy(float) <= cuts[0], 0, np.where(frame["loo_a1"].to_numpy(float) <= cuts[1], 1, 2))
    g = pd.DataFrame({"ev": ev, "slot": sl, "ter": ter, "birth": frame["BR"].to_numpy(float) > 0, "loo": frame["loo_a1"].to_numpy(float)})
    es = g.groupby(["ev", "slot"]).agg(birth=("birth", "max"), loo=("loo", "mean")).reset_index()
    es["ter"] = np.where(es["loo"] <= cuts[0], 0, np.where(es["loo"] <= cuts[1], 1, 2))
    window = sorted(int(s_) for s_ in es["slot"].unique())
    fake: set[tuple[str, int]] = set()
    for e, grp in es.groupby("ev"):
        real = sorted(int(s_) for s_ in grp.loc[grp["birth"], "slot"])
        cand_ter = {int(r_.slot): int(r_.ter) for r_ in grp.loc[~grp["birth"]].itertuples()}
        cand_slots = [s_ for s_ in window if s_ in cand_ter]
        for rs in real:
            cnt["real_births"] += 1
            rt = int(grp.loc[grp["slot"] == rs, "ter"].iloc[0])
            pick = lt.fake_birth_slot(real, cand_slots, cand_ter, rt, rng, int(spec["b"]["fake_birth_min_slots"]))
            if pick is None:
                cnt["none_available"] += 1
            else:
                cnt["fake_drawn"] += 1
                fake.add((e, pick))
    pop = frame[frame["BR"] == 0].reset_index(drop=True)
    pop["BR_fake"] = [1.0 if (e, int(s_)) in fake else 0.0 for e, s_ in zip(pop["event_id"].astype(str), pop["slot"], strict=False)]
    return pop, cnt


def readings_b(frame: pd.DataFrame, extras: dict, spec: dict, n_boot: int | None) -> dict:
    ctrl = lt.CONTROLS_B
    out: dict = {}
    out["M1"] = fit_reading(frame, np.abs(_mid(frame, "h3") - _mid(frame, "h1")), "BR", ctrl, spec, "B", 11, treated="BR", n_boot=n_boot)
    out["M2"] = fit_reading(frame, np.abs(_mid(frame, "h1") - frame["mid"].to_numpy(float)), "BR", ctrl, spec, "B", 12, treated="BR", n_boot=n_boot)
    pop, fcnt = fake_birth_frame(frame, spec)
    out["fake_birth_counts"] = fcnt
    if len(pop):
        out["P_fake_birth"] = fit_reading(pop, pop["a22"].to_numpy(float), "BR_fake", [c for c in ctrl if c != "BR"], spec, "B", 13, treated="BR_fake", n_boot=n_boot)
    arms = (extras or {}).get("arms") or {}
    sec: dict = {}
    if "tail" in arms and len(arms["tail"]):
        a = arms["tail"]
        sy = _mid(a, "h12") - _mid(a, "h1")  # YES change, predicted < 0
        sec["S1_signed_tail_arm"] = fit_reading(a, sy, "BR", ctrl, spec, "B", 21, sign=-1, treated="BR", n_boot=n_boot)
        sec["S1_signed_tail_arm"]["units"] = int(len(a))
    sec["S2_attention"] = {"computed": False, "reason": "not computed, disclosed: volume24hr at k + 12 sits in the reader's write-once series files (no leakage), but the analysis keeps "
                                                                   "no slot-to-capture map for the k + 12 capture; nothing is labelled or counted for it (LIVE_TESTS_6.md 17)"}
    sec["S3_maker_first_pass"] = out["M2"]
    for nm, m, off in (("S4_neg_risk", frame["neg_risk"] == 1, 23), ("S4_not_neg_risk", frame["neg_risk"] == 0, 26)):  # distinct bootstrap offsets (re-check fix)
        sub = frame[m.to_numpy()].reset_index(drop=True)
        sec[nm] = fit_reading(sub, sub["a22"].to_numpy(float), "BR", ctrl, spec, "B", off, treated="BR", n_boot=n_boot)
    if "sports" in arms and len(arms["sports"]):
        a = arms["sports"]
        sec["S5_sports_arm"] = {"units": int(len(a)), "births": int((a["cls"] == "birth").sum())}
    if "n_born" in frame:
        births = frame[frame["BR"] == 1].reset_index(drop=True)
        sec["S6_dose_n_born"] = fit_reading(births, births["a22"].to_numpy(float), "n_born", [c for c in ctrl if c != "BR"], spec, "B", 25, n_boot=n_boot)
    sec["S7_counts"] = {"by_class": {str(k_): int(v) for k_, v in frame["cls"].value_counts().items()}}
    out["secondaries"] = sec
    return out


READERS = {"V": readings_v, "K": readings_k, "D": readings_d, "B": readings_b}


# --- Thanksgiving sensitivity (1.1) ---------------------------------------------------------------------------------------------------


def thanksgiving_sensitivity(test: str, frame: pd.DataFrame, spec: dict, n_boot: int | None) -> dict:
    """The primary re-fitted without origins in ``[2026-11-26T00:00Z, 2026-11-28T00:00Z)``; reported, never changes a verdict."""
    la = _la()
    lo, hi = (lt.epoch(x) for x in spec["labels"]["thanksgiving_excluded_utc"])
    t = frame["capture_t"].to_numpy(float)
    keep = ~((t >= lo) & (t < hi))
    sub = frame[keep].reset_index(drop=True)
    cfg = la.PRIMARY[test]
    out = fit_reading(sub, sub[cfg["y"]].to_numpy(float), cfg["term"], cfg["controls"], spec, test, 91, treated=cfg["treated"], n_boot=n_boot)
    out["units_dropped"] = int((~keep).sum())
    return out


# --- economics (1.10; separate, never a verdict) ----------------------------------------------------------------------------------------


def economics_v(frame: pd.DataFrame, spec: dict) -> dict:
    """(a) Reported taker follow of ratified moves (``zv`` in the top tercile, ``|x| >= 0.03``): entry at the sweep-1 touch of pass k + 1,
    exit at the sweep-1 touch of pass k + 3, direction ``sign(x)``; (b) maker lean: gross ``c_vskip`` by ``zv`` tercile, 'gross, no fills'.
    Frozen fee fields (``fee_rate``, ``fee_exp``) feed the paper taker. Descriptive."""
    out: dict = {"hurdle_c": 2.9}
    cuts = spec["v"].get("terciles")
    if cuts is None or not len(frame):
        return {**out, "computed": False}
    sub = frame[(frame["zv"] >= cuts[1]) & (np.abs(frame["x"]) >= 0.03)]
    out["taker_units"] = int(len(sub))
    if len(sub) and {"sbid_s1", "sask_s1", "sbid_s3", "sask_s3", "fee_rate", "fee_exp"} <= set(sub.columns):
        pnl = la3.paper_taker(sub["sbid_s1"].to_numpy(float), sub["sask_s1"].to_numpy(float), sub["sbid_s3"].to_numpy(float), sub["sask_s3"].to_numpy(float),
                              sub["fee_rate"].to_numpy(float), sub["fee_exp"].to_numpy(float), np.sign(sub["x"].to_numpy(float)))
        out["taker"] = la3.econ(pnl, sub["event_id"].astype(str).to_numpy(), sub["day"].astype(str).to_numpy(), int(spec["seeds"]["V"]) + 81)
    t = np.where(frame["zv"] <= cuts[0], "bottom", np.where(frame["zv"] >= cuts[1], "top", "middle"))
    out["maker_gross_by_tercile_c"] = {k_: float(np.nanmean(frame.loc[t == k_, "c_vskip"]) * 100.0) for k_ in ("bottom", "middle", "top") if (t == k_).any()}
    out["maker_note"] = "gross, no fills"
    out["computed"] = True
    return out


def economics_generic(test: str, frame: pd.DataFrame, spec: dict) -> dict:
    """K (a) taker join of clip-carried moves and D / B maker gross lines, descriptive; the lines the design names, computed from frozen
    fields only (no fills are simulated)."""
    la = _la()
    out: dict = {"hurdle_c": 2.9, "computed": True, "maker_note": "gross, no fills"}
    cfg = la.PRIMARY[test]
    y = frame[cfg["y"]].to_numpy(float)
    treated = frame[cfg["term"]].to_numpy(float) > 0
    if test == "K":
        sub = frame[(frame["CL"] == 1) & (np.abs(frame["x"]) >= 0.03)]
        out["taker_units"] = int(len(sub))
        if len(sub) and {"sbid_s1", "sask_s1", "sbid_s3", "sask_s3", "fee_rate", "fee_exp"} <= set(sub.columns):
            pnl = la3.paper_taker(sub["sbid_s1"].to_numpy(float), sub["sask_s1"].to_numpy(float), sub["sbid_s3"].to_numpy(float), sub["sask_s3"].to_numpy(float),
                                  sub["fee_rate"].to_numpy(float), sub["fee_exp"].to_numpy(float), np.sign(sub["x"].to_numpy(float)))
            out["taker"] = la3.econ(pnl, sub["event_id"].astype(str).to_numpy(), sub["day"].astype(str).to_numpy(), int(spec["seeds"]["K"]) + 81)
        out["maker_gross_c"] = {"clip": float(np.nanmean(y[treated]) * 100.0) if treated.any() else None, "clip_free": float(np.nanmean(y[~treated]) * 100.0) if (~treated).any() else None}
    else:
        key = "gross_y_c" if test == "D" else "gross_a22_c"
        out[key] = {"treated": float(np.nanmean(np.abs(y[treated])) * 100.0) if treated.any() else None, "control": float(np.nanmean(np.abs(y[~treated])) * 100.0) if (~treated).any() else None}
    return out


# --- the whole reading of one test -------------------------------------------------------------------------------------------------------


def run_readings(test: str, frame: pd.DataFrame, verdict_str: str | None, prim_beta: float | None, extras: dict | None, spec: dict, *,
                 accounts: dict | None = None, n_boot: int | None = None) -> dict:
    """All readings of ``test`` on its prepared frame, and the labels they imply. ``extras``: ``pre`` (attrition input), ``arms`` (frames of the
    reported arms), ``raw`` (all frozen lines of the test), ``k_prev_class`` ((market, slot) -> class_k), ``counts`` (summed reader counts).
    Never raises on a degenerate sub-sample (the reading is then marked not testable)."""
    la = _la()
    extras = extras or {}
    if frame is None or not len(frame):
        return {"computed": False, "labels": []}
    rd = READERS[test](frame, extras, spec, n_boot)
    cfg = la.PRIMARY[test]

    def refit(sub, y):
        return la.strip(la.fit6(sub, y, cfg["term"], cfg["controls"], treated_col=cfg["treated"], seed=int(spec["seeds"][test]), **_kw(n_boot)))

    rd["attrition"] = attrition_reading(test, extras.get("pre"), frame, spec, refit)
    rd["thanksgiving_sensitivity"] = thanksgiving_sensitivity(test, frame, spec, n_boot)
    rd["economics"] = economics_v(frame, spec) if test == "V" else economics_generic(test, frame, spec)
    labels = label_rules(test, _supported(verdict_str), prim_beta, rd)
    if (rd["attrition"] or {}).get("triggered"):
        labels.append("attrition-differential")
    if test == "K":
        lab = coverage_label(extras.get("counts") or {}, spec)
        if lab:
            labels.append(lab)
    if test == "V":
        lab = sweep_missing_label(accounts or {}, spec)
        if lab:
            labels.append(lab)
    return {"computed": True, "readings": rd, "labels": labels}


def clean(x):
    """JSON-safe copy (NaN / inf to None) for the readings block."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return float(x) if math.isfinite(float(x)) else None
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x
