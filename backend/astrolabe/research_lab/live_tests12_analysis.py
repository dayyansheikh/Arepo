# ruff: noqa: E501
"""LT12 single registered analysis (LIVE_TESTS_12.md 1.7-1.11, sections 2-3). Research only; never trades; reads only LT12's own write-once files.

Runs ONCE, on or after ``live_tests12.ANALYSIS_NOT_BEFORE``, on the pinned spec and code. One Holm family over the ``k`` primaries that survived their census
gates (spec ``k_tests``), one-sided, familywise alpha 0.05. A primary that is unavailable, whose gate fails (on data or in the size check) or whose spec is
incomplete enters Holm with p = 1. F, the point conditions, secondaries, readings, arms, placebos, economics and the census count 0.

Estimator (1.7): expanding-past event x UTC-day demeaning of every regressor (``live_tests12.demeaned_frame``; strictly earlier captures; target raw), then the
vendored LT3 ``fit`` (estimator ``given``): CR1 on the event, the two-way event x UTC day and the UTC day; one-sided ``p = max(p_event on t with G_event - 1 df,
p_two-way normal, p_day on t with G_day - 1 df)``; the conservative 95% CI is the hull of a 2,000-draw event bootstrap and the three Wald intervals. Gate: the
event-phase state-shift gate (``live_tests12.event_day_state_shift_gate``). Falsification (1.9): the arm model with the far-future twin; ``Delta = beta(lead) -
beta(twin)`` is the coefficient on the lead when the SUM lead + twin is added as a control. The point conditions are estimates only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import bounce_decomp as bd
from . import live_tests12 as lt
from . import live_tests12_analysis_base as ab
from . import live_tests12_base as b

TESTS = lt.TESTS
DIRECTION = {t: +1 for t in TESTS}
ROLE_CONF = lt.ROLE_CONF
Refused = lt.Refused
GATE_LABEL = "SE check failed (gate on data)"
SIZE_LABEL = "SE check failed (size scenario)"
MECH_LABEL = "SE check failed (mechanical world)"
HURDLES = {"taker_round_trip_c": {"ge_100k": 2.9, "10k_100k": 3.9, "1k_10k": 7.2}, "touch_5_share_c": 4.5, "touch_5_share_politics_c": 3.6, "passive_fill_1h": 0.031, "maker_before_rewards_c": -0.37,
           "source": "cost-model-v1 (COST_MODEL.md); no E026 frozen module is imported"}


def code_check(spec: dict) -> dict:
    """Compare the modules on disk with the spec's ``code_sha256`` map. A pinned spec refuses on any mismatch, an unfilled map, a null, empty or unknown
    ``k_tests``, a ``k_tests`` naming a dropped test, a null size-check result for a surviving test, or unfilled census values; a DRAFT spec only labels."""
    pins = spec.get("code_sha256") or {}
    cur = lt.code_hashes()
    status = {n: ("not pinned" if pins.get(n) is None else ("match" if pins.get(n) == h else "MISMATCH")) for n, h in cur.items()}
    if spec.get("_pinned"):
        bad = {n: s for n, s in status.items() if s != "match"}
        if bad:
            raise Refused(f"live_tests12 code sha256 does not match the registered pins: {bad}")
        if (err := lt.registration_error(spec)) is not None:
            raise Refused(err["error"])
        k = spec["k_tests"]
        drop = set(spec.get("dropped_tests") or [])
        if drop & set(k):
            raise Refused(f"live_tests12 k_tests names a dropped test: {sorted(drop & set(k))}")
        # code-freeze check fix 5: every test is in exactly one of k_tests, dropped_tests (census_dropped) and census_unavailable (coverage)
        lists = {"k_tests": set(k), "dropped_tests": drop, "census_unavailable": set(spec.get("census_unavailable") or [])}
        if (unk := sorted(set().union(*lists.values()) - set(TESTS))):
            raise Refused(f"live_tests12 census lists name unknown tests: {unk}")
        for t in TESTS:
            where = [n for n, v in lists.items() if t in v]
            if len(where) != 1:
                raise Refused(f"live_tests12 {t} must be in exactly one of k_tests, dropped_tests, census_unavailable (found in {where or 'none'})")
        sc = spec.get("size_check_result")
        if not isinstance(sc, dict) or any(t not in sc for t in k):
            raise Refused("live_tests12 spec pinned without the recorded size-check result of every surviving test")
        for t in k:
            lt.f_role(spec, t)
    return {"current": cur, "pinned": {n: pins.get(n) for n in cur}, "status": status, "label": None if all(s == "match" for s in status.values()) else "DRAFT: code hashes not verified"}


def census_state(spec: dict, t: str) -> str | None:
    """The census state of ``t`` read from the spec's own lists (code-freeze check fix 5): ``k`` (a Holm primary), ``census_dropped`` (``dropped_tests``) or
    ``census_unavailable (coverage)`` (``census_unavailable``); None when no list names it (a DRAFT spec; a pinned spec refuses in :func:`code_check`)."""
    if t in (spec.get("k_tests") or []):
        return "k"
    if t in (spec.get("census_unavailable") or []):
        return lt.CENSUS_UNAVAILABLE
    if t in (spec.get("dropped_tests") or []):
        return lt.CENSUS_DROPPED
    return None


NOT_IN_K = {lt.CENSUS_DROPPED: f"{lt.CENSUS_DROPPED}: dropped at its census (uncounted; not in the Holm family; never re-censused)",
            lt.CENSUS_UNAVAILABLE: f"{lt.CENSUS_UNAVAILABLE} (uncounted; not in the Holm family; may be re-censused only in the ordered lane as its own Holm family)",
            None: "not in k_tests; census state not recorded in the spec (uncounted; not in the Holm family)"}


def preconditions(spec: dict, now: float, *, force: bool = False) -> None:
    """The refusals of ``analyze`` that do not depend on any file: the analysis date, the frozen design text, a pinned spec."""
    if not force and now < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise Refused(f"the analysis runs only on or after {lt.ANALYSIS_NOT_BEFORE}")
    if (e := lt.design_text_error()) is not None:
        raise Refused(e["error"])
    if not force and not spec.get("_pinned"):
        raise Refused("the analysis refuses an unpinned spec (SPEC_SHA256 is None)")


# --- loading ---------------------------------------------------------------------------------------------------------------------------------


DTYPES = {"market_id": str, "o_market_id": str, "event_id": str, "nrkey": str, "spec_sha": str, "code_sha": str, "role": str, "arm": str, "line": str, "kind": str, "fam": str,
          "o_fam": str, "size_class": str, "fee_cat": str, "day": str, "condition_id": str, "cell": str, "pl_key": str, "pair_fams": str, "pair_eids": str, "rew_case_k": str, "rew_case_km1": str}


def load_kind(out_root: Path, test: str, start: float, end: float, spec: dict, roles: tuple[str, ...] = (ROLE_CONF,)) -> tuple[pd.DataFrame, dict]:
    """Frozen (not ``.late``) unit lines of origins in ``[start, end)`` with an allowed role (and, with a pinned spec, the pinned spec and code hashes),
    merged with their k + 1 outcome (``status_h1``, ``bid_h1``, ``ask_h1``, ``spread_c_h1``; a missing file is ``pending``) and their twin file (by market and
    line). Counts dropped lines and late files."""
    kind = lt.KINDS[test]
    out_root = Path(out_root)
    pinned = bool(spec.get("_pinned"))
    want_spec = spec["_sha256"][:16] if pinned else None
    pins = spec.get("code_sha256") or {}
    want_code = lt.joint_sha(pins.get("live_tests12.py"), pins.get("live_tests12_base.py")) if pinned else None
    acc = {"files": 0, "late_files": 0, "empty_files": 0, "noprev_files": 0, "boundary_files": 0, "dropped_role": 0, "dropped_spec_sha": 0, "dropped_code_sha": 0}
    parts = []
    fdir = out_root / kind / "frozen"
    for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
        if p.name.endswith(".late.csv.gz"):
            acc["late_files"] += 1
            continue
        if p.name.endswith(".empty.csv.gz"):
            acc["empty_files"] += 1
            continue
        if p.name.endswith(".boundary.csv.gz"):
            acc["boundary_files"] += 1
            continue
        if p.name.endswith(lt.MARKERS):
            acc["noprev_files"] += 1
            continue
        fr = pd.read_csv(p, dtype=DTYPES, float_precision="round_trip")
        acc["files"] += 1
        t0 = b.slot_time(int(fr["slot"].iloc[0]), spec) if len(fr) else math.nan
        if not (start <= t0 < end):
            continue
        keep = fr["role"].isin(roles)
        acc["dropped_role"] += int((~keep).sum())
        fr = fr[keep]
        if pinned:
            ok = fr["spec_sha"].astype(str) == want_spec
            acc["dropped_spec_sha"] += int((~ok).sum())
            fr = fr[ok]
            ok = fr["code_sha"].astype(str) == want_code
            acc["dropped_code_sha"] += int((~ok).sum())
            fr = fr[ok]
        fid = p.name[:-7]
        op = out_root / kind / "outcomes" / f"{fid}.h1.csv.gz"
        if op.exists():
            o = pd.read_csv(op, dtype={"market_id": str, "status": str}, float_precision="round_trip", usecols=["market_id", "status", "bid", "ask", "spread_c"]).drop_duplicates("market_id")
            o = o.rename(columns={c: f"{c}_h1" for c in o.columns if c != "market_id"})
            fr = fr.merge(o, on="market_id", how="left")
            fr["status_h1"] = fr["status_h1"].fillna("absent")
        else:
            fr["status_h1"] = "pending"
        tp = out_root / kind / "twins" / f"{fid}.csv.gz"
        if tp.exists():
            w = pd.read_csv(tp, dtype={"market_id": str, "line": str}, float_precision="round_trip").drop_duplicates(["market_id", "line"])
            fr = fr.merge(w, on=["market_id", "line"], how="left")
        else:
            fr["tw_ok"] = np.nan
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    tot = acc["files"] + acc["late_files"]
    acc["late_loss_share"] = acc["late_files"] / tot if tot else 0.0
    return df, acc


def frame(df: pd.DataFrame, test: str, spec: dict) -> pd.DataFrame:
    """The model frame: the target in cents (k + 1 minus k, ``two_sided`` at k + 1 only, else NaN), the census-scaled states, the twin terms and the fee
    dummies. CH245: ``y`` = the line's own spread change over (k, k + 1] (thin lines: ``ds_T``; dense lines: ``ds_D``); ``zs`` / ``zs_tw`` / ``zs_pl`` scaled
    by the census ``s_D`` (thin) or ``s_T`` (dense). CH244: ``y = ds_i``, ``shock_sz`` on the census scale, ``shock x unrew`` and its twin."""
    X = df.copy()
    cf = (spec.get("census_fixed") or {}).get(test) or {}
    two = X["status_h1"].astype(str).to_numpy() == "two_sided"
    if test == "CH245":
        sk = X["own_spread_k_c"].to_numpy(float)
        X["y"] = np.where(two, X.get("spread_c_h1", pd.Series(np.nan, index=X.index)).to_numpy(float) - sk, np.nan)
        X["zs"] = lt.zs_term(X["o_ds_c"].to_numpy(float), X["line"].to_numpy(object), cf)
        X["zs_tw"] = lt.zs_term(X["o_ds_tw_c"].to_numpy(float), X["line"].to_numpy(object), cf) if "o_ds_tw_c" in X else np.nan
        sD = cf.get("s_D")
        X["zs_pl"] = X["pl_ds_c"].to_numpy(float) / float(sD) if (sD and math.isfinite(float(sD)) and float(sD) > 0) else np.nan
    else:
        X["y"] = np.where(two, X.get("spread_c_h1", pd.Series(np.nan, index=X.index)).to_numpy(float) - X["spread_k_c"].to_numpy(float), np.nan)
        sc = cf.get("shock_size_scale")
        X["shock_sz"] = X["shock_size_raw"] / float(sc) if (sc and math.isfinite(float(sc)) and float(sc) > 0) else np.nan
        lt._recompute("CH244", X)
        X["shock_x_unrew_tw"] = X["shock_tw"].to_numpy(float) * X["unrew"].to_numpy(float) if "shock_tw" in X else np.nan
    if "fee_cat" in X:
        X, _ = lt.fee_dummies(X)
    return X


def fit12(X: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, seed: int, n_boot: int = ab.N_BOOT, sign: int = +1) -> dict:
    """The primary estimator (1.7): every regressor expanding-past event x UTC-day demeaned (strictly earlier captures), the target raw; the vendored LT3 ``fit``
    on the demeaned regressors (estimator ``given``; event p on t with G_event - 1 df), then ``p = max(p_event, p_two-way, p_day)`` and the conservative CI
    widened to the two-way Wald interval. Controls without variation are dropped (listed)."""
    ctrl = [c for c in controls if c in X and c != term and np.nanstd(X[c].to_numpy(float)) > 0]
    if term not in X or len(X) < 10:
        return {"testable": False, "reason": "fewer than 10 rows or no term", "p": 1.0}
    D = lt.demeaned_frame(X, [term, *ctrl])
    r = ab.fit(D, np.asarray(y, float), term, ctrl, sign=sign, group="event_id", order="slot", estimator="given", ev="event_id", time="day", ev_t_ref=True, seed=seed, n_boot=n_boot)
    r["dropped_controls"] = [c for c in controls if c not in ctrl]
    if not r.get("testable"):
        return r
    df_e = int(r["n_event"]) - 1
    r["p"] = max(float(r["p_event"]), float(r.get("p_twoway", 1.0)), float(r["p_time_t"]))
    lo, hi = r["ci95_cons"]
    te = float(t_dist.ppf(0.975, df_e)) if df_e >= 1 else float("inf")
    r["ci95_cons"] = [min(lo, r["beta"] - 1.96 * r["se_twoway"], r["beta"] - te * r["se_event"]), max(hi, r["beta"] + 1.96 * r["se_twoway"], r["beta"] + te * r["se_event"])]
    r["p_rule"] = "max(p_event t on G_event-1, p_two-way event x day, p_day t on G_day-1)"
    r["controls"] = ctrl
    return r


def strip(r: dict | None) -> dict | None:
    return None if r is None else {k: v for k, v in r.items() if not k.startswith("_")}


def primary_population(X: pd.DataFrame, test: str, spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH245: the ``thin`` lines of the ``primary`` arm; CH244: the ``primary`` arm (mixed 3-10 ladders); the census-fixed series family excluded (1.4)."""
    cnt: dict = {"lines": len(X)}
    cf = (spec.get("census_fixed") or {}).get(test) or {}
    m = (X["arm"].astype(str) == "primary") & ((X["line"].astype(str) == "thin") if test == "CH245" else True)
    P = X[m].reset_index(drop=True)
    fam = cf.get("exclude_family")
    if fam:
        cnt["family_excluded"] = int((P["fam"].astype(str) == fam).sum())
        P = P[P["fam"].astype(str) != fam].reset_index(drop=True)
    cnt["population"] = len(P)
    return P, cnt


def counts(P: pd.DataFrame, ok: np.ndarray, test: str) -> dict:
    ev = P["event_id"].astype(str).to_numpy()[ok]
    vc = pd.Series(ev).value_counts()
    out = {"units": int(ok.sum()), "events": int(pd.unique(ev).size), "days": int(pd.unique(P["day"].astype(str).to_numpy()[ok]).size), "g_eff": lt.g_eff(ev) if len(ev) else float("nan"),
           "events_ge48": int((vc >= 48).sum())}
    if test == "CH245":
        out["placebo_share"] = float(np.isfinite(P["zs_pl"].to_numpy(float)[ok]).mean()) if ok.any() else 0.0
    else:
        u, s = P["unrew"].to_numpy(float)[ok], P["shock"].to_numpy(float)[ok]
        out["tested_units"] = int(((u == 1) & (s == 1)).sum())
        out["rewarded_shock_units"] = int(((u == 0) & (s == 1)).sum())
    return out


def unavailable(c: dict, test: str, spec: dict) -> str | None:
    """1.9's Unavailable. CH245: < 20,000 thin units, < 300 events, < 100 events with >= 48 units, or the placebo defined on < 50% of thin units. CH244:
    < 20,000 tested units (unrewarded x shock) or < 20,000 rewarded shock units, < 300 events, < 100 events with >= 48 units. Both: Kish G_eff < 15 or < 10 UTC
    days with units."""
    f = spec["verdict"]["floors"]
    if test == "CH245":
        if c["units"] < f["CH245_thin_units"]:
            return f"fewer than {f['CH245_thin_units']} thin units"
        if c.get("placebo_share", 0.0) < f["CH245_placebo_share"]:
            return "the placebo is defined on fewer than 50% of thin units"
    else:
        if c.get("tested_units", 0) < f["CH244_tested_units"]:
            return f"fewer than {f['CH244_tested_units']} tested units"
        if c.get("rewarded_shock_units", 0) < f["CH244_rewarded_shock_units"]:
            return f"fewer than {f['CH244_rewarded_shock_units']} rewarded shock units"
    if c["events"] < f["events"]:
        return f"fewer than {f['events']} events"
    if c.get("events_ge48", 0) < f["events_ge48"]:
        return f"fewer than {f['events_ge48']} events with >= {f['events_min_units']} units"
    if not (c["g_eff"] >= f["g_eff"]):
        return f"G_eff below {f['g_eff']}"
    if c["days"] < f["days"]:
        return f"fewer than {f['days']} UTC days with units"
    return None


def gate(P: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], spec: dict, *, draws: int | None = None, seed: int | None = None) -> dict:
    """The event-phase state-shift gate (1.8) on the primary model; a failed gate gives p = 1 and the label 'SE check failed (gate on data)'."""
    g = spec["gates"]
    ctrl = [c for c in controls if c in P and np.nanstd(P[c].to_numpy(float)) > 0]
    return lt.event_day_state_shift_gate(P, y, lt.TERM[test], ctrl, test=test, draws=int(draws if draws is not None else g["draws"]),
                                         seed=int(seed if seed is not None else spec["seeds"]["gates"][test]), min_captures=int(g["min_captures"]), sign=+1)


# --- falsification and the point conditions (1.9) ----------------------------------------------------------------------------------------------------------


def f_rule(P: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], prim: dict, spec: dict, *, n_boot: int = 200) -> dict:
    """The arm model: the primary with the far-future twin added, on the units that have it (a finite twin and ``f_end_ok``). ``Delta = beta(lead) -
    beta(twin)`` is the coefficient on the lead with ``lead + twin`` added as a control. F holds iff Delta's one-sided p < 0.05 (the 1.7 rule, not
    Holm-adjusted, counted 0) and Delta-hat >= 0.5 x beta-hat(primary). An arm with fewer than 50% of the primary's units: falsification unavailable."""
    term, tw = lt.TERM[test], lt.TWIN[test]
    out: dict = {"role": lt.f_role(spec, test)}
    if tw not in P:
        return {**out, "available": False, "reason": "no twin column"}
    ok_p = prim["_mask"]
    arm = ok_p & np.isfinite(P[tw].to_numpy(float)) & (P["f_end_ok"].to_numpy(float) == 1)
    share = float(arm.sum() / max(1, ok_p.sum()))
    out.update(arm_units=int(arm.sum()), arm_share=share)
    if share < spec["verdict"]["f_rule"]["arm_min_share"] or arm.sum() < 10:
        return {**out, "available": False, "reason": "arm has fewer than 50% of the primary's units (falsification unavailable)"}
    A = P.loc[arm].reset_index(drop=True)
    ya = np.asarray(y, float)[arm]
    A["_sum"] = A[term].to_numpy(float) + A[tw].to_numpy(float)
    seed = int(spec["seeds"]["estimators"][test])
    d = fit12(A, ya, term, ["_sum", *controls], seed=seed, n_boot=n_boot)
    if not d.get("testable"):
        return {**out, "available": False, "reason": d.get("reason")}
    delta, bprim = float(d["beta"]), float(prim["beta"])
    fr = spec["verdict"]["f_rule"]
    holds = bool(float(d["p"]) < fr["delta_p_max"] and delta >= fr["delta_over_primary_min"] * bprim)
    out.update(available=True, delta=delta, p_delta=float(d["p"]), delta_ge_half_primary=bool(delta >= 0.5 * bprim), holds=holds)
    return out


def _pc(beta, ref, ratio: float, two_sided: bool = False) -> bool:
    if beta is None or ref is None or not (math.isfinite(float(beta)) and math.isfinite(float(ref))):
        return False
    return bool((abs(float(beta)) if two_sided else float(beta)) < ratio * float(ref))


def point_conditions(Xall: pd.DataFrame, P: pd.DataFrame, test: str, controls: list[str], prim: dict, spec: dict, *, n_boot: int = 200) -> dict:
    """1.9's binding point conditions (estimates only, no test, counted 0).

    CH245 (a) the dense twin on TWO sets (re-check fix 7): the model on the dense lines of the same pair-captures (target ``ds_D``, state ``zs_T``, mirrored
    controls) has ``beta_dense < 0.5 x beta_thin`` on the full set AND on the pair-captures whose dense spread at k is >= 2 ticks, each set's ``beta_thin``
    from the primary refitted on that set; that set under 5,000 thin units -> *dense-twin unavailable* (condition (a) cannot be shown); (b) the two-sided
    placebo: the primary with ``zs`` replaced by the unrelated pair's ``zs_pl`` has ``|beta_placebo| < 0.5 x beta_thin``. CH244: the twin model with ``lowliq``
    and ``shock x lowliq`` in place of ``unrew`` and ``shock x unrew`` has ``beta_lowliq < 0.5 x beta_unrew``. Each difference's one-sided p is reported (a
    label); CH244's joint model (both interactions) is reported (*liquidity-shared*)."""
    ratio = float(spec["verdict"]["point_condition_ratio"])
    seed = int(spec["seeds"]["estimators"][test])
    bprim = float(prim["beta"])
    out: dict = {"ratio": ratio, "beta_primary": bprim}
    if test == "CH245":
        keys = set(zip(P["nrkey"].astype(str), P["slot"].astype(int), strict=True))
        Dn = Xall[(Xall["line"].astype(str) == "dense") & (Xall["arm"].astype(str) == "primary")]
        Dn = Dn[[(a, int(s_)) in keys for a, s_ in zip(Dn["nrkey"].astype(str), Dn["slot"], strict=True)]].reset_index(drop=True)
        rd = fit12(Dn, Dn["y"].to_numpy(float), "zs", controls, seed=seed, n_boot=n_boot) if len(Dn) >= 30 else {"testable": False}
        full = {"beta_dense": rd.get("beta"), "beta_thin": bprim, "dense_units": int(len(Dn)), "holds": _pc(rd.get("beta"), bprim, ratio)}
        nt = float(spec["verdict"]["dense_twin_ge2_ticks"])
        Pm = P[P["o_spread_k_ticks"].to_numpy(float) >= nt - 1e-9].reset_index(drop=True)
        Dm = Dn[Dn["own_spread_k_ticks"].to_numpy(float) >= nt - 1e-9].reset_index(drop=True)
        n_set = int(np.isfinite(Pm["y"].to_numpy(float)).sum())
        if n_set < int(spec["verdict"]["dense_twin_ge2_min_units"]):
            ge2 = {"available": False, "thin_units": n_set, "reason": "dense spread_k >= 2 ticks set below 5,000 units (dense-twin unavailable)", "holds": False}
        else:
            rt2 = fit12(Pm, Pm["y"].to_numpy(float), "zs", controls, seed=seed, n_boot=n_boot)
            rd2 = fit12(Dm, Dm["y"].to_numpy(float), "zs", controls, seed=seed, n_boot=n_boot) if len(Dm) >= 30 else {"testable": False}
            ge2 = {"available": bool(rt2.get("testable") and rd2.get("testable")), "thin_units": n_set, "beta_thin": rt2.get("beta"), "beta_dense": rd2.get("beta"),
                   "holds": _pc(rd2.get("beta"), rt2.get("beta"), ratio)}
        out["dense_twin"] = {"full": full, "ge2_ticks": ge2, "available": bool(ge2.get("available") and rd.get("testable")), "holds": bool(full["holds"] and ge2.get("holds"))}
        pl = P[np.isfinite(P["zs_pl"].to_numpy(float))].reset_index(drop=True)
        rp = fit12(pl.assign(zs=pl["zs_pl"]), pl["y"].to_numpy(float), "zs", controls, seed=seed, n_boot=n_boot) if len(pl) >= 30 else {"testable": False}
        out["placebo"] = {"beta_placebo": rp.get("beta"), "units": int(len(pl)), "holds": _pc(rp.get("beta"), bprim, ratio, two_sided=True), "rule": "|beta_placebo| < 0.5 x beta_thin"}
        S = pd.concat([P.assign(is_thin=1.0), Dn.assign(is_thin=0.0)], ignore_index=True)
        S["zs_x_thin"] = S["zs"] * S["is_thin"]
        d = fit12(S, S["y"].to_numpy(float), "zs_x_thin", ["zs", "is_thin", *controls], seed=seed, n_boot=n_boot) if len(S) >= 60 else {"testable": False}
        out["p_difference"], out["beta_difference"] = d.get("p"), d.get("beta")
        out["available"] = out["dense_twin"]["available"]
        out["holds"] = bool(out["dense_twin"]["holds"] and out["placebo"]["holds"])
        return out
    ctrl_l = ["lowliq" if c == "unrew" else c for c in controls]
    rl = fit12(P, P["y"].to_numpy(float), "shock_x_lowliq", ctrl_l, seed=seed, n_boot=n_boot)
    out["beta_lowliq"] = rl.get("beta")
    out["holds"] = _pc(rl.get("beta"), bprim, ratio)
    out["available"] = bool(rl.get("testable"))
    J = P.assign(_sum=P["shock_x_unrew"] + P["shock_x_lowliq"])
    d = fit12(J, J["y"].to_numpy(float), "shock_x_unrew", ["_sum", "lowliq", *controls], seed=seed, n_boot=n_boot)
    out["p_difference"], out["beta_difference"] = d.get("p"), d.get("beta")
    jm = fit12(P, P["y"].to_numpy(float), "shock_x_unrew", ["shock_x_lowliq", "lowliq", *controls], seed=seed, n_boot=n_boot)
    jl = fit12(P, P["y"].to_numpy(float), "shock_x_lowliq", ["shock_x_unrew", "lowliq", *controls], seed=seed, n_boot=n_boot)
    cc = np.corrcoef(P["shock_x_unrew"].to_numpy(float), P["shock_x_lowliq"].to_numpy(float))[0, 1] if len(P) > 2 else math.nan
    out["joint_model"] = {"beta_unrew": jm.get("beta"), "p_unrew": jm.get("p"), "beta_lowliq": jl.get("beta"), "p_lowliq": jl.get("p"), "corr_interactions": float(cc)}
    return out


# --- run one test -----------------------------------------------------------------------------------------------------------------------------------------


def run_test(out_root: Path, test: str, start: float, end: float, spec: dict, roles: tuple[str, ...], size_note: str | None) -> dict:
    df, acc = load_kind(out_root, test, start, end, spec, roles)
    res: dict = {"load": acc}
    if df.empty:
        return {**res, "available": False, "reason": "no lines", "primary": None, "gate": None}
    Xall = frame(df, test, spec)
    P, pc = primary_population(Xall, test, spec)
    res["population"] = pc
    term = lt.TERM[test]
    controls = lt.controls_for(test, P)
    if P.empty or not np.isfinite(P[term].to_numpy(float)).any():
        return {**res, "available": False, "reason": f"{term} unavailable (census-fixed scale missing or no primary units)", "primary": None, "gate": None}
    y = P["y"].to_numpy(float)
    seed = int(spec["seeds"]["estimators"][test])
    prim = fit12(P, y, term, controls, seed=seed)
    if not prim.get("testable"):
        return {**res, "available": False, "reason": prim.get("reason"), "primary": strip(prim), "gate": None}
    ok = prim["_mask"]
    c = counts(P, ok, test)
    c["target_status"] = {k: int(v) for k, v in P["status_h1"].astype(str).value_counts().items()}
    reg0 = lt.epoch(spec["registered_utc"])
    c["pre_window_source"] = int((np.array([b.slot_time(int(s_) - 12, spec) for s_ in P["slot"].to_numpy(int)]) < reg0).sum())  # 1.1 (ruling A15): look-backs reading 2026-12-09
    c["effective_start_utc"] = lt.iso(float(min(b.slot_time(int(s_), spec) for s_ in P["slot"].to_numpy(int)))) if len(P) else None
    res["counts"] = c
    res["unavailable_reason"] = unavailable(c, test, spec)
    res["available"] = res["unavailable_reason"] is None
    res["primary"] = strip(prim)
    res["gate"] = gate(P, y, test, prim.get("controls", controls), spec) if res["available"] else None
    res["f"] = f_rule(P, y, test, prim.get("controls", controls), prim, spec)
    res["point_condition"] = point_conditions(Xall, P, test, prim.get("controls", controls), prim, spec) if res["available"] else {"available": False, "holds": False}
    res.update(_frame=P, _all=Xall, _y=y, _prim=prim, _controls=prim.get("controls", controls), size_note=size_note)
    return res


def p_for_holm(r: dict) -> tuple[float, str | None]:
    """1.8 / 1.9: p = 1 for an unavailable primary, a gate that fails on data, or a size scenario that failed; the label that goes with it."""
    prim = r.get("primary")
    if not r.get("available") or not prim or not prim.get("testable"):
        return 1.0, None
    if r.get("size_note"):
        return 1.0, r["size_note"]
    g = r.get("gate") or {}
    if not g.get("passes"):
        return 1.0, GATE_LABEL
    return float(prim["p"]), None


def verdict(r: dict, holm_p: float, test: str) -> dict:
    """1.9. Supported: Holm-adjusted one-sided p < 0.05, estimate > 0, gate passed, F holds and every point condition holds. Otherwise, with everything else
    holding: F fails or unavailable -> Inconclusive with 'mechanical null not excluded' (or 'falsification unavailable'); a point condition fails or cannot be
    shown -> Inconclusive with 'not thin-specific' (or 'dense-twin unavailable'), 'placebo not null' (CH245) or 'not status-specific' (CH244). Contradicted: the
    conservative 95% CI lies entirely below 0. Unavailable: the floors."""
    if not r.get("available"):
        return {"verdict": "Unavailable", "reason": r.get("unavailable_reason") or r.get("reason")}
    prim = r["primary"]
    pf, gl = p_for_holm(r)
    labels: list[str] = [gl] if gl else []
    f = r.get("f") or {}
    pc = r.get("point_condition") or {}
    f_ok = bool(f.get("available") and f.get("holds"))
    pc_ok = bool(pc.get("holds"))
    base = (holm_p < 0.05) and (DIRECTION[test] * prim["beta"] > 0) and (gl is None)
    if base and f_ok and pc_ok:
        return {"verdict": "Supported", "labels": labels}
    lo, hi = prim["ci95_cons"]
    if hi < 0:
        return {"verdict": "Contradicted", "labels": labels}
    if base and not f_ok:
        labels.append("falsification unavailable" if not f.get("available") else "mechanical null not excluded")
    if base and not pc_ok:
        if test == "CH245":
            dt = pc.get("dense_twin") or {}
            if not (dt.get("ge2_ticks") or {}).get("available", True):
                labels.append("dense-twin unavailable")
            elif not dt.get("holds"):
                labels.append("not thin-specific")
            if not (pc.get("placebo") or {}).get("holds"):
                labels.append("placebo not null")
        else:
            labels.append("not status-specific")
    return {"verdict": "Inconclusive", "labels": labels}


# --- readings, attrition, economics, labels (1.9, 1.10; estimates only, count 0) --------------------------------------------------------------------


def _refit(r: dict, mask: np.ndarray, spec: dict, test: str, *, term: str | None = None, controls: list[str] | None = None, frame_: pd.DataFrame | None = None) -> dict:
    P = r["_frame"] if frame_ is None else frame_
    sub = P[np.asarray(mask, bool)].reset_index(drop=True)
    if len(sub) < 30:
        return {"testable": False, "reason": "fewer than 30 units", "n": int(len(sub))}
    return strip(fit12(sub, sub["y"].to_numpy(float), term or lt.TERM[test], controls or r["_controls"], seed=int(spec["seeds"]["estimators"][test]), n_boot=200)) or {}


def readings(r: dict, test: str, spec: dict) -> dict:
    """Estimates only (never a verdict): the holiday-excluded refit (1.1: no origins in [2026-12-24, 2026-12-27)), CH245's M4 (``hb_k`` in place of
    ``hb_{k-1}``: *bid-sum mediated*), M5 (thin row received before the dense row at k: *receipt-order sensitive*) and the reward cells; CH244's 11+ arm
    (*ladder-dominated*), the CLOB-agreement refit (*CLOB-disagreement sensitive*), the M4 placebo arms and the event-capture aggregate (the deduplicated
    sensitivity of 1.7)."""
    P, Xall = r["_frame"], r["_all"]
    h0, h1 = (lt.epoch(x) for x in spec["verdict"]["holiday"])
    tt = np.array([b.slot_time(int(s_), spec) for s_ in P["slot"].to_numpy(int)])
    out: dict = {"holiday_excluded": _refit(r, ~((tt >= h0) & (tt < h1)), spec, test)}
    if test == "CH245":
        ctrl_m4 = ["hb_k" if c == "hb_km1" else c for c in r["_controls"]]
        out["m4_bid_sum"] = _refit(r, np.ones(len(P), bool), spec, test, controls=ctrl_m4)
        out["m5_thin_first"] = _refit(r, P["own_first"].to_numpy(float) == 1, spec, test)
        out["cells"] = {c_: _refit(r, P["cell"].astype(str).to_numpy() == c_, spec, test) for c_ in ("rr", "ru", "uu")}
        sym = Xall[(Xall["line"].astype(str) == "sym") & (Xall["arm"].astype(str) == "primary")].reset_index(drop=True)
        out["sym_arm"] = _refit(r, np.ones(len(sym), bool), spec, test, frame_=sym) if len(sym) else {"testable": False}
    else:
        L = Xall[Xall["arm"].astype(str) == "ladder11"].reset_index(drop=True)
        out["ladder11_arm"] = _refit(r, np.ones(len(L), bool), spec, test, frame_=L) if len(L) else {"testable": False, "n": 0}
        u, fl, fc = P["unrew"].to_numpy(float), P["feed_listed_pos"].to_numpy(float), P["feed_cov"].to_numpy(float)
        agree = (fc == 1) & (((u == 1) & (fl == 0)) | ((u == 0) & (fl == 1)))
        out["clob_agreement"] = _refit(r, agree, spec, test)
        for arm in ("allrew", "allunrew"):
            A = Xall[Xall["arm"].astype(str) == arm].reset_index(drop=True)
            ctrl = [c for c in r["_controls"] if c not in ("unrew", "shock")]
            out[f"m4_{arm}_shock"] = _refit(r, np.ones(len(A), bool), spec, test, term="shock", controls=ctrl, frame_=A) if len(A) else {"testable": False, "n": 0}
        ok = np.isfinite(P["y"].to_numpy(float))
        if ok.any():
            G = P[ok].groupby(["event_id", "slot", "unrew"])["y"].mean().unstack("unrew")
            sh = P[ok].groupby(["event_id", "slot"])["shock"].max()
            if 0.0 in G.columns and 1.0 in G.columns:
                agg = (G[1.0] - G[0.0]).dropna()
                s_ = sh.reindex(agg.index).to_numpy(float)
                out["event_capture_aggregate"] = {"n": int(len(agg)), "mean_diff_shock_c": float(agg[s_ == 1].mean()) if (s_ == 1).any() else None,
                                                  "mean_diff_noshock_c": float(agg[s_ == 0].mean()) if (s_ == 0).any() else None}
    return out


def attrition_block(test: str, r: dict, spec: dict) -> dict:
    """1.5: |a_1 - a_0| > 2 pp in target availability between the contrasted groups (CH245: top against bottom census tercile of ``zs_D``; CH244: unrewarded
    against rewarded members on shock captures) gives *attrition-differential* and Lee-type bounds, never a verdict change."""
    X = r["_frame"]
    status = X["status_h1"].astype(str).to_numpy()
    if test == "CH245":
        cuts = ((spec.get("census_fixed") or {}).get("CH245") or {}).get("zs_cuts") or [math.nan, math.nan]
        z = X["zs"].to_numpy(float)
        cls = np.where(z >= float(cuts[1]), "1", np.where(z <= float(cuts[0]), "0", "mid"))
    else:
        u, s = X["unrew"].to_numpy(float), X["shock"].to_numpy(float)
        cls = np.where(s == 1, np.where(u == 1, "1", "0"), "noshock")
    att = ab.attrition(status, cls, ("1", "0"), spec["verdict"]["attrition_pp"] / 100.0)
    if att.get("triggered"):
        att["lee_bounds"] = ab.lee_bounds(X, r["_y"], cls, ("1", "0"), att, lambda d, yy: fit12(d, yy, lt.TERM[test], r["_controls"], seed=int(spec["seeds"]["estimators"][test]), n_boot=200))
    return att


def economics_block(r: dict, test: str, spec: dict) -> dict:
    """1.10 (descriptive, never a verdict): the cost-model hurdles; the gross maker route (CH245: the thin book's next spread change after a dense widening;
    CH244: the unpaid member's bid change at k + 1 after a sibling shock) and LT3's ``paper_taker`` / ``econ`` at the recorded touches of capture k and k + 1
    with the origin sidecar's fee (CH245: take the thin book's stale side after the dense book widened, the ask where ``g_ask,k < 0``, the bid where
    ``g_bid,k < 0``; CH244: buy the unpaid member after a shock; LT12 ambiguity A19). No LT12 result is the programme's economic check."""
    X = r["_frame"]
    out: dict = {"hurdles": HURDLES, "note": "gross, no fills, no queue, no realised rewards; none of this is the programme's economic check"}
    two = X["status_h1"].astype(str).to_numpy() == "two_sided"
    ev, day = X["event_id"].astype(str).to_numpy(), X["day"].astype(str).to_numpy()
    rate = np.where(np.isfinite(X["fee_rate"].to_numpy(float)), X["fee_rate"].to_numpy(float), 0.0) if "fee_rate" in X else np.zeros(len(X))
    expo = np.where(np.isfinite(X["fee_exp"].to_numpy(float)), X["fee_exp"].to_numpy(float), 1.0) if "fee_exp" in X else np.ones(len(X))
    if test == "CH245":
        wid = X["zs"].to_numpy(float) > 0
        out["maker_route_mean_next_spread_change_c"] = float(np.nanmean(X["y"].to_numpy(float)[wid])) if wid.any() else None
        bk, ak = X["p_k"].to_numpy(float) - X["spread_c"].to_numpy(float) / 200.0, X["p_k"].to_numpy(float) + X["spread_c"].to_numpy(float) / 200.0
        ga, gb = X["g_ask_k"].to_numpy(float), X["g_bid_k"].to_numpy(float)
        d = np.where(ga < 0, 1.0, np.where(gb < 0, -1.0, np.nan))
        m = wid & two & np.isfinite(d)
        pnl = np.where(m, ab.paper_taker(bk, ak, X["bid_h1"].to_numpy(float), X["ask_h1"].to_numpy(float), rate, expo, np.nan_to_num(d, nan=1.0)), np.nan)
        out["paper_taker_stale_side"] = ab.econ(pnl * 100.0, ev, day, int(spec["seeds"]["estimators"][test]))
        cheaper = np.minimum(X["p_k"].to_numpy(float) + X["spread_c"].to_numpy(float) / 200.0, 1.0 - (X["p_k"].to_numpy(float) - X["spread_c"].to_numpy(float) / 200.0))
        out["cheaper_book_line_descriptive"] = {"note": "min(ask_A, 1 - bid_B) against ask_A at capture k only; a cost-route descriptive, not a forecast", "n": int(np.isfinite(cheaper).sum())}
    else:
        m = (X["shock"].to_numpy(float) == 1) & (X["unrew"].to_numpy(float) == 1) & two
        db = (X["bid_h1"].to_numpy(float) - X["bid_k"].to_numpy(float)) * 100.0
        out["maker_route_mean_bid_change_c"] = float(np.nanmean(db[m])) if m.any() else None
        pnl = np.where(m, ab.paper_taker(X["bid_k"].to_numpy(float), X["ask_k"].to_numpy(float), X["bid_h1"].to_numpy(float), X["ask_h1"].to_numpy(float), rate, expo, np.ones(len(X))), np.nan)
        out["paper_taker_buy_unpaid_after_shock"] = ab.econ(pnl * 100.0, ev, day, int(spec["seeds"]["estimators"][test]))
    return out


def underpowered(test: str, r: dict, spec: dict, k: int) -> dict:
    """1.9 *underpowered* (as LT11): Inconclusive and ``(t_{G-1, 1-0.05/k} + t_{G-1, 0.8}) x SE_day`` above the census MDE (``census_gate_values.<test>.mde_c``),
    G = the UTC days of the primary. Not computed while the census MDE is unfilled."""
    prim = r.get("primary") or {}
    mde = ((spec.get("census_gate_values") or {}).get(test) or {}).get("mde_c")
    g, se = prim.get("n_day"), prim.get("se_day")
    if mde is None or g is None or se is None or int(g) < 2 or not math.isfinite(float(mde)):
        return {"computed": False}
    df_ = int(g) - 1
    m = (float(t_dist.ppf(1 - 0.05 / max(1, k), df_)) + float(t_dist.ppf(0.8, df_))) * float(se)
    if test == "CH245":
        gap = ((spec.get("census_fixed") or {}).get("CH245") or {}).get("zs_gap")
        m = m * float(gap) if gap is not None else float("inf")
    return {"computed": True, "window_mde_c": m, "census_mde_c": float(mde), "above": bool(m > float(mde))}


def _sign_change(a: dict | None, beta) -> bool:
    return bool(a and a.get("testable") and beta is not None and float(a["beta"]) * float(beta) < 0)


def labels_for(test: str, r: dict, v: dict, spec: dict, k: int, cc: dict) -> list[str]:
    """1.9's labels (never change a verdict)."""
    lab = list(v.get("labels") or [])
    lab += [f"informed ({x})" for x in (*lt.CERTAIN_INFORMED.get(test, ()), *(((spec.get("informed_labels") or {}).get(test)) or []))]
    if v["verdict"] == "Unavailable":
        return list(dict.fromkeys(lab + ([cc["label"]] if cc["label"] else [])))
    prim = r.get("primary") or {}
    beta = prim.get("beta")
    cf = (spec.get("census_fixed") or {}).get(test) or {}
    floor = float(spec["verdict"]["material_c"][test])
    gap = cf.get("zs_gap") if test == "CH245" else 1.0
    if beta is not None and gap is not None and math.isfinite(float(gap)) and float(beta) * float(gap) >= floor:
        lab.append("material")
    pd_ = (r.get("point_condition") or {}).get("p_difference")
    if pd_ is not None and math.isfinite(float(pd_)) and float(pd_) < 0.05:
        lab.append("thin-difference significant" if test == "CH245" else "status-difference significant")
    rd = r.get("readings") or {}
    if test == "CH245":
        m4 = rd.get("m4_bid_sum") or {}
        if m4.get("testable") and beta is not None and float(m4["beta"]) < 0.5 * float(beta):
            lab.append("bid-sum mediated")
        if _sign_change(rd.get("m5_thin_first"), beta):
            lab.append("receipt-order sensitive")
    else:
        if _sign_change(rd.get("ladder11_arm"), beta):
            lab.append("ladder-dominated")
        if _sign_change(rd.get("clob_agreement"), beta):
            lab.append("CLOB-disagreement sensitive")
        jm = ((r.get("point_condition") or {}).get("joint_model") or {})
        if jm.get("beta_unrew") is not None and beta is not None and float(jm["beta_unrew"]) < 0.5 * float(beta):
            lab.append("liquidity-shared")
    if v["verdict"] == "Inconclusive" and (r.get("underpowered") or {}).get("above"):
        lab.append("underpowered")
    ho = rd.get("holiday_excluded") or {}
    if ho.get("testable") and beta is not None and (ho["beta"] * beta < 0 or ((ho["p"] < 0.05) != (prim.get("p", 1) < 0.05))):
        lab.append("holiday-sensitive")
    X = r.get("_frame")
    pm = (r.get("_prim") or {}).get("_mask")
    if X is not None and pm is not None:
        Xm = X[np.asarray(pm, bool)]
        if len(Xm):
            top = Xm["fam"].astype(str).value_counts(normalize=True)
            if float(top.iloc[0]) > spec["verdict"]["series_concentrated"]:
                lab.append(f"series-concentrated ({float(top.iloc[0]):.0%})")
    att = r.get("attrition") or {}
    if att.get("triggered"):
        lab.append(f"attrition-differential ({att['diff'] * 100:+.1f} pp)")
    if (r["load"].get("late_loss_share") or 0.0) > spec["verdict"]["late_loss_max"]:
        lab.append(f"late-loss ({r['load']['late_loss_share']:.1%} of origin files written late)")
    if r.get("analytic_oversized"):
        lab.append("analytic p oversized in simulation")
    if cc["label"]:
        lab.append(cc["label"])
    return list(dict.fromkeys(lab))


def trials_line(spec: dict, ktests: list[str]) -> dict:
    """The single counted trials line (``battery2.KIND_RULES['live_tests12']``, rule n_tests): k counted tests; gates, F, point conditions, placebos,
    secondaries, arms, economics, the census, the CH251 map and the size check count 0; CH243's drop counts 0."""
    return {"kind": "live_tests12", "n_tests": len(ktests), "tests": ktests, "counts": "k = the Holm primaries that survived their census gates; everything else 0",
            "spec_sha256": spec["_sha256"], "evidence_role": ROLE_CONF}


def analyze(out_root: Path = lt.OUT_ROOT, *, spec: dict | None = None, now: float | None = None, force: bool = False, roles: tuple[str, ...] = (ROLE_CONF,)) -> dict:
    """The single registered analysis. Refuses before ``ANALYSIS_NOT_BEFORE``, on an unpinned spec, a changed design text, a code-hash mismatch, a null / empty /
    unknown / dropped ``k_tests`` or an unfilled census value."""
    spec = spec or lt.load_spec(sha=lt.SPEC_SHA256)
    now = b.now_ts() if now is None else now
    preconditions(spec, now, force=force)
    cc = code_check(spec)
    s, e = lt.epoch(spec["registered_utc"]), lt.epoch(spec["end_utc"])
    ktests = list(spec.get("k_tests") or TESTS)
    k = len(ktests)
    sc = spec.get("size_check_result") or {}
    res: dict = {}
    for t in TESTS:
        if t not in ktests:
            st = census_state(spec, t)
            res[t] = {"census_state": st, "verdict": {"verdict": NOT_IN_K.get(st, NOT_IN_K[None])}}
            continue
        note = sc.get(t)
        status = note.get("status") if isinstance(note, dict) else note
        size_note = None if status in (None, "pass") else (SIZE_LABEL if str(status).startswith("fail_size") else MECH_LABEL)
        r = run_test(out_root, t, s, e, spec, roles, size_note)
        r["analytic_oversized"] = bool(isinstance(note, dict) and note.get("analytic_oversized"))
        r["census_state"] = "k"
        res[t] = r
    pv = {t: p_for_holm(res[t])[0] for t in ktests}
    hp = bd.holm(pv)
    for t in ktests:
        r = res[t]
        if r.get("available") and r.get("primary"):
            r["attrition"] = attrition_block(t, r, spec)
            r["readings"] = readings(r, t, spec)
            r["economics"] = economics_block(r, t, spec)
            r["underpowered"] = underpowered(t, r, spec, k)
        v = verdict(r, hp[t], t)
        r["holm_p"] = hp[t]
        v["labels"] = labels_for(t, r, v, spec, k, cc)
        r["verdict"] = v
    for t in ktests:
        for key in ("_frame", "_all", "_y", "_prim", "_controls"):
            res[t].pop(key, None)
    res["holm"] = {"tests": ktests, "m": k, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True}
    res["counting"] = trials_line(spec, ktests)
    res.update(spec_sha=spec["_sha256"], code_sha256=cc["current"], code_check=cc, window=[spec["registered_utc"], spec["end_utc"]], roles=list(roles), design_text_sha256=lt.design_text_sha())
    return bd._clean(res)


def analyze_cli(args, write_out, now: float) -> int:
    if getattr(args, "out", None) is None:  # code-freeze check fix 6: the single analysis is written once to --out, never only printed (repeatable)
        print("refusing: analyze needs --out (write-once)")
        return 2
    try:
        spec = lt.load_spec(sha=lt.SPEC_SHA256)
        res = analyze(args.out_root, spec=spec, now=now)
    except (Refused, RuntimeError) as exc:
        print(f"refusing: {exc}")
        return 2
    return write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=str))
