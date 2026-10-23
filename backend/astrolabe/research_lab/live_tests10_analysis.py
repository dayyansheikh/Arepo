# ruff: noqa: E501
"""LT10 single registered analysis (LIVE_TESTS_10.md 1.7-1.11, sections 2-4). Research only; never trades; reads only LT10's own write-once files.

Runs ONCE, on or after ``live_tests10.ANALYSIS_NOT_BEFORE``, on the pinned spec and code. One Holm family over the ``k`` primaries that survived their
census gates (spec ``k_tests``), one-sided, familywise alpha 0.05. A primary that is unavailable, whose gate fails (on data or in the size check) or whose
spec is incomplete enters Holm with p = 1. Secondaries, mechanism readings, arms, labels, sensitivities and economics never change a verdict and count 0.

Estimator (1.7): expanding-past pair demeaning of every regressor (the vendored ``fit``: target raw), CR1 on the Polymarket event, the two-way event x UTC
day and the UTC day; one-sided ``p = max(p_event on t with min(G_event, G_minor) - 1 df, p_two-way normal, p_day on t with G_day - 1 df)``; the conservative
95% CI is the hull of a 2,000-draw event bootstrap and the three Wald intervals. Falsification (1.9): the arm model with the far-future twin; ``Delta =
beta(lead) - beta(twin)`` is the coefficient on the lead when the SUM lead + twin is added as a control.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import bounce_decomp as bd
from . import economics
from . import live_tests10 as lt
from . import live_tests10_analysis_base as ab
from . import live_tests10_base as b

TESTS = lt.TESTS
DIRECTION = {t: +1 for t in TESTS}
ROLE_CONF = "prospective_confirmation"
EPS = 1e-9
HOLIDAY = ("2026-11-26T00:00:00Z", "2026-11-28T00:00:00Z")  # 1.1: US Thanksgiving and the following day
GATE_LABEL = "SE check failed (gate on data)"
SIZE_LABEL = "SE check failed (size scenario)"
MECH_LABEL = "SE check failed (mechanical world)"
HURDLES = {"taker_100_usd_c": {"ge_100k": 2.9, "10k_100k": 3.9, "1k_10k": 7.2}, "touch_5_share_round_trip_c": 4.5, "passive_fill_1h": [0.017, 0.031],
           "source": "cost-model-v1 (COST_MODEL.md) as round 15 fact 4 and round 14 fact 9 quote it (1.10)"}


class Refused(RuntimeError):
    """The analysis refuses (a date, pin, spec or input check failed): nothing is written."""


# --- pins, refusals (1.1, 8.1) ----------------------------------------------------------------------------------------------------------------


def code_check(spec: dict) -> dict:
    """Compare the modules on disk with the spec's ``code_sha256`` map. A pinned spec refuses on any mismatch, an unfilled map, a null, empty or unknown
    ``k_tests``, a ``k_tests`` naming a dropped test, a null size-check result for a surviving test, or unfilled census values; a DRAFT spec only labels."""
    pins = spec.get("code_sha256") or {}
    cur = lt.code_hashes()
    status = {n: ("not pinned" if pins.get(n) is None else ("match" if pins.get(n) == h else "MISMATCH")) for n, h in cur.items()}
    if spec.get("_pinned"):
        bad = {n: s for n, s in status.items() if s != "match"}
        if bad:
            raise Refused(f"live_tests10 code sha256 does not match the registered pins: {bad}")
        k = spec.get("k_tests")
        if k is None:
            raise Refused("live_tests10 spec pinned with null k_tests")
        if not k:
            raise Refused("live_tests10 spec pinned with an empty k_tests")
        if [t for t in k if t not in TESTS]:
            raise Refused(f"live_tests10 spec pinned with unknown k_tests {[t for t in k if t not in TESTS]}")
        drop = set(spec.get("dropped_tests") or [])
        if drop & set(k):
            raise Refused(f"live_tests10 k_tests names a dropped test: {sorted(drop & set(k))}")
        cf = spec.get("census_fixed") or {}
        if "CH224" in k and cf.get("scale_K_cents") is None:
            raise Refused("live_tests10 spec pinned with unfilled scale_K")
        if "CH222" in k and any((cf.get("rv60") or {}).get(z, {}).get(w) is None for z in ("rv60_P", "rv60_K") for w in ("centre", "scale")):
            raise Refused("live_tests10 spec pinned with unfilled rv60 centres and scales")
        sc = spec.get("size_check_result")
        if not isinstance(sc, dict) or any(t not in sc for t in k):
            raise Refused("live_tests10 spec pinned without the recorded size-check result of every surviving test")
        for t in k:
            if lt.f_role(spec, t) != lt.F_ROLES[t]:
                raise Refused("F role mismatch")
    return {"current": cur, "pinned": {n: pins.get(n) for n in cur}, "status": status,
            "label": None if all(s == "match" for s in status.values()) else "DRAFT: code hashes not verified"}


def preconditions(spec: dict, now: float, *, force: bool = False) -> None:
    """The refusals of ``analyze`` that do not depend on any file: the analysis date, the frozen design text, a pinned spec."""
    if not force and now < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise Refused(f"the analysis runs only on or after {lt.ANALYSIS_NOT_BEFORE}")
    if (e := lt.design_text_error()) is not None:
        raise Refused(e["error"])
    if not force and not spec.get("_pinned"):
        raise Refused("the analysis refuses an unpinned spec (SPEC_SHA256 is None)")


# --- loading ---------------------------------------------------------------------------------------------------------------------------


def _origin_t(p: Path) -> int:
    return lt._origin_of(p)


def load_kind(out_root: Path, test: str, start: float, end: float, spec: dict, roles: tuple[str, ...] = (ROLE_CONF,)) -> tuple[pd.DataFrame, dict]:
    """Frozen (not ``.late``) unit lines of origins in ``[start, end)`` with an allowed role (and, with a pinned spec, the pinned spec and code hashes),
    merged with their target files (columns suffixed ``_h<min>``; a missing file is ``pending``) and twin files. Counts dropped lines and late files."""
    kind = lt.KINDS[test]
    out_root = Path(out_root)
    pinned = bool(spec.get("_pinned"))
    want_spec = spec["_sha256"][:16] if pinned else None
    want_code = ((spec.get("code_sha256") or {}).get("live_tests10.py") or "")[:16] if pinned else None
    acc = {"files": 0, "late_files": 0, "dropped_role": 0, "dropped_spec_sha": 0, "dropped_code_sha": 0}
    parts = []
    for p in sorted((out_root / kind / "frozen").glob("*/*.csv.gz")) if (out_root / kind / "frozen").exists() else []:
        if p.name.endswith(".late.csv.gz"):
            acc["late_files"] += 1
            continue
        t = _origin_t(p)
        if not (start <= t < end):
            continue
        fr = pd.read_csv(p, dtype={"pid": str, "ev": str, "spec_sha": str, "code_sha": str, "role": str, "crypto": str}, float_precision="round_trip")
        acc["files"] += 1
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
        d, hm = p.parent.name, p.name[:4]
        for h in lt.HORIZON_MIN[kind]:
            op = out_root / kind / "outcomes" / d / f"{hm}.h{h}.csv.gz"
            if op.exists():
                o = pd.read_csv(op, dtype={"pid": str, "tg_status": str}, float_precision="round_trip", usecols=["pid", "tg_status", "pmid_h", "sP_h", "p_bid_sz_h", "p_ask_sz_h"]).drop_duplicates("pid")
                o = o.rename(columns={c: f"{c}{h}" for c in o.columns if c != "pid"})
                fr = fr.merge(o, on="pid", how="left")
            else:
                fr[f"tg_status{h}"] = "pending"
        tp = out_root / kind / "twins" / d / f"{hm}.csv.gz"
        if tp.exists():
            w = pd.read_csv(tp, dtype={"pid": str}, float_precision="round_trip", usecols=["pid", "tw_ok", "dsK_tw", "pull_tw", "traded_tw"]).drop_duplicates("pid")
            fr = fr.merge(w, on="pid", how="left")
        else:
            for c in ("tw_ok", "dsK_tw", "pull_tw", "traded_tw"):
                fr[c] = np.nan
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    tot = acc["files"] + acc["late_files"]
    acc["late_loss_share"] = acc["late_files"] / tot if tot else 0.0
    return df, acc


def _day(t) -> np.ndarray:
    return pd.to_datetime(np.asarray(t, float), unit="s", utc=True).strftime("%Y-%m-%d").to_numpy()


def _tg(df: pd.DataFrame, h: int) -> np.ndarray:
    c = f"tg_status{h}"
    return (df[c].astype(str).to_numpy() == "two_sided") if c in df else np.zeros(len(df), bool)


def frame(df: pd.DataFrame, test: str, spec: dict) -> pd.DataFrame:
    """Analysis columns of one test: pair / event / time aliases for the vendored estimators, hour dummies, the census-scale twin and the targets in
    cents (sections 2-4). Rows without a two-sided target keep NaN targets (counted by the callers)."""
    X = df.copy()
    X["market_id"], X["t_row"], X["event_id"] = X["pid"].astype(str), X["t"].astype(float), X["ev"].astype(str)
    X["day"] = _day(X["t"])
    X["hour"] = (X["t"].to_numpy(float) // 3600) % 24
    X["moh"] = X["t"].to_numpy(float) % 3600
    X["sign"] = np.sign(X["dk1"].to_numpy(float))
    X["block2"] = ((X["t"].to_numpy(float) - lt.epoch(spec["registered_utc"])) // (2 * lt.DAY_S)).astype(int)
    cf = spec.get("census_fixed") or {}
    scale = (cf.get("scale_K_cents") / 100.0) if cf.get("scale_K_cents") else None
    rv = (cf.get("rv60") or {}) if test == "CH222" else None
    if rv is not None and any(rv.get(z, {}).get(w) is None for z in ("rv60_P", "rv60_K") for w in ("centre", "scale")):
        rv = None
    X = lt.add_test_columns(X, scale, rv)
    pm, sp = X["pmid"].to_numpy(float), X["sP_t"].to_numpy(float)
    for h in lt.HORIZON_MIN[lt.KINDS[test]]:
        ok = _tg(X, h)
        mh = np.where(ok, X.get(f"pmid_h{h}", np.nan), np.nan) if f"pmid_h{h}" in X else np.full(len(X), np.nan)
        sh = np.where(ok, X.get(f"sP_h{h}", np.nan), np.nan) if f"sP_h{h}" in X else np.full(len(X), np.nan)
        X[f"mP_h{h}"], X[f"sP_h{h}_ok"] = mh, sh
    if test == "CH224":
        X["y"] = (X["sP_h20_ok"].to_numpy(float) - sp) * 100.0
        X["y_s1"] = (X["sP_h10_ok"].to_numpy(float) - sp) * 100.0
        s_t = np.expm1(X["lpb_t"].to_numpy(float)) + np.expm1(X["lpa_t"].to_numpy(float))
        s_h = np.where(_tg(X, 20), np.nan_to_num(X.get("p_bid_sz_h20", 0.0), nan=np.nan) + np.nan_to_num(X.get("p_ask_sz_h20", 0.0), nan=np.nan), np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            X["y_m2"] = np.log(s_h) - np.log(s_t)
    elif test == "CH223":
        X["y"] = np.abs(X["mP_h20"].to_numpy(float) - pm) * 100.0
        X["y_s1"] = np.abs(X["mP_h10"].to_numpy(float) - pm) * 100.0
        X["y_m1"] = np.where(X["pull_side"].to_numpy(float) != 0, X["pull_side"].to_numpy(float) * (X["mP_h20"].to_numpy(float) - pm) * 100.0, np.nan)
        X["y_m2"] = (X["sP_h20_ok"].to_numpy(float) - sp) * 100.0
    else:
        s = X["sign"].to_numpy(float)
        X["y"] = s * (X["mP_h20"].to_numpy(float) - pm) * 100.0
        X["y_s1"] = s * (X["mP_h10"].to_numpy(float) - pm) * 100.0
        X["y_m1"] = s * (X["mP_h60"].to_numpy(float) - pm) * 100.0
    # nothing past the scope: the primary is the sealed scope only
    return X


# --- estimator and inference (1.7) -------------------------------------------------------------------------------------------------------


def g_minor(X: pd.DataFrame, ok: np.ndarray, test: str) -> int | None:
    """G_minor = the number of events holding at least one unit of the smaller contrasted class (CH223: pull vs no pull; CH222: traded vs quote-only)."""
    if test == "CH224":
        return None
    term = lt.TERM[test]
    v = X[term].to_numpy(float)[ok]
    ev = X["event_id"].to_numpy()[ok]
    n1, n0 = int((v == 1).sum()), int((v == 0).sum())
    if n1 == 0 or n0 == 0:
        return 0
    small = 1.0 if n1 <= n0 else 0.0
    return int(pd.unique(ev[v == small]).size)


def fit10(X: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, seed: int, minor: int | None = None, n_boot: int = ab.N_BOOT) -> dict:
    """The vendored LT3 ``fit`` (event p on t with G_event - 1 df), then LT4/LT10's rule: ``p = max(p_event on t with min(G_event, G_minor) - 1 df,
    p_two-way normal, p_day on t with G_day - 1 df)`` and the conservative CI widened to the two-way Wald interval."""
    ctrl = [c for c in controls if c in X and np.nanstd(X[c].to_numpy(float)) > 0]
    r = ab.fit(X, y, term, ctrl, sign=+1, group="market_id", order="t_row", ev="event_id", time="day", ev_t_ref=True, seed=seed, n_boot=n_boot)
    r["dropped_controls"] = [c for c in controls if c not in ctrl]
    if not r.get("testable"):
        return r
    g_e = int(r["n_event"])
    df_e = g_e - 1
    if minor is not None and minor < g_e:
        df_e = max(int(minor) - 1, 0)
        r["p_event"] = float(t_dist.sf(r["z_event"], df=df_e)) if df_e >= 1 else 1.0
        r["p_event_ref"] = f"t on {df_e} df (G_minor = {minor})"
    r["g_minor"] = minor
    r["p"] = max(float(r["p_event"]), float(r.get("p_twoway", 1.0)), float(r["p_time_t"]))
    lo, hi = r["ci95_cons"]
    te = float(t_dist.ppf(0.975, df_e)) if df_e >= 1 else float("inf")
    r["ci95_cons"] = [min(lo, r["beta"] - 1.96 * r["se_twoway"], r["beta"] - te * r["se_event"]), max(hi, r["beta"] + 1.96 * r["se_twoway"], r["beta"] + te * r["se_event"])]
    r["p_rule"] = "max(p_event t on min(G_event, G_minor)-1, p_two-way event x day, p_day t on G_day-1)"
    r["controls"] = ctrl
    return r


def strip(r: dict | None) -> dict | None:
    return None if r is None else {k: v for k, v in r.items() if not k.startswith("_")}


def counts(X: pd.DataFrame, ok: np.ndarray, test: str) -> dict:
    ev = X["event_id"].to_numpy()[ok]
    out = {"units": int(ok.sum()), "events": int(pd.unique(ev).size), "days": int(pd.unique(X["day"].to_numpy()[ok]).size), "g_eff": lt.g_eff(ev) if len(ev) else float("nan")}
    v = X[lt.TERM[test]].to_numpy(float)[ok]
    if test == "CH223":
        out.update(withdrawal_units=int((v == 1).sum()), no_withdrawal_units=int((v == 0).sum()))
    elif test == "CH222":
        out.update(traded_units=int((v == 1).sum()), quote_only_units=int((v == 0).sum()))
    return out


def unavailable(c: dict, test: str, spec: dict) -> str | None:
    """1.9's Unavailable: fewer than 30 events with units, G_eff below 15, fewer than 10 UTC days, and each test's unit floors."""
    fl = spec.get("floors") or {}
    allf = fl.get("all") or {}
    if c["events"] < allf.get("events", 30):
        return f"fewer than {allf.get('events', 30)} events with units"
    if not (c["g_eff"] >= allf.get("g_eff", 15)):
        return f"G_eff below {allf.get('g_eff', 15)}"
    if c["days"] < allf.get("days", 10):
        return f"fewer than {allf.get('days', 10)} UTC days with units"
    f = fl.get(test) or {}
    if test == "CH224" and c["units"] < f.get("units", 30000):
        return f"fewer than {f.get('units', 30000)} units"
    if test == "CH223" and (c["withdrawal_units"] < f.get("withdrawals", 1500) or c["no_withdrawal_units"] < f.get("no_withdrawals", 30000)):
        return "fewer than 1,500 withdrawal units or 30,000 no-withdrawal units"
    if test == "CH222" and (c["traded_units"] < f.get("traded", 2000) or c["quote_only_units"] < f.get("quote_only", 2000)):
        return "fewer than 2,000 traded or 2,000 quote-only units"
    return None


def _stratum(test: str) -> tuple[str, int]:
    return ("block2", 288) if test == "CH222" else ("day", 144)


def gate(X: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], spec: dict) -> dict:
    """The event-phase block Freedman-Lane gate (1.8) on the primary model; a failed gate gives p = 1 and the label 'SE check failed (gate on data)'."""
    ctrl = [c for c in controls if c in X and np.nanstd(X[c].to_numpy(float)) > 0]
    g = spec["gates"]
    stratum, n_g = _stratum(test)
    return lt.event_phase_fl_gate(X, y, lt.TERM[test], ctrl, stratum=stratum, n_g=n_g, draws=int(g["draws"]), seed=int(spec["seeds"]["gates"][test]), sign=+1,
                                  min_pair=int(g["min_unit_pair"]), min_rows=int(g["min_rows_stratum"]))


# --- falsification (1.9) ------------------------------------------------------------------------------------------------------------------


def f_rule(X: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], prim: dict, spec: dict, minor_fn) -> dict:
    """The arm model: the primary model with the far-future twin added on the units that have it. ``Delta = beta(lead) - beta(twin)`` is the coefficient
    on the lead with ``lead + twin`` added as a control (same demeaning, controls and clustering). F holds iff the one-sided p of Delta < 0.05 (the 1.7
    rule, not Holm-adjusted, counted 0) and Delta-hat >= 0.5 x beta-hat(primary). An arm with fewer than 50% of the primary's units: unavailable."""
    term, tw = lt.TERM[test], lt.TWIN[test]
    out: dict = {"role": lt.f_role(spec, test)}
    if tw not in X:
        return {**out, "available": False, "reason": "no twin column"}
    ok_p = prim["_mask"]
    arm = ok_p & np.isfinite(X[tw].to_numpy(float))
    share = float(arm.sum() / max(1, ok_p.sum()))
    out.update(arm_units=int(arm.sum()), arm_share=share)
    if share < 0.5 or arm.sum() < 10:
        return {**out, "available": False, "reason": "arm has fewer than 50% of the primary's units (falsification unavailable)"}
    A = X.loc[arm].reset_index(drop=True)
    ya = np.asarray(y, float)[arm]
    A["_sum"] = A[term].to_numpy(float) + A[tw].to_numpy(float)
    seed = int(spec["seeds"]["estimators"][test])
    d = fit10(A, ya, term, ["_sum", *controls], seed=seed, minor=minor_fn(A, np.ones(len(A), bool)), n_boot=200)
    if not d.get("testable"):
        return {**out, "available": False, "reason": d.get("reason")}
    beta_lead = fit10(A, ya, term, [tw, *controls], seed=seed, minor=None, n_boot=200)
    beta_twin = fit10(A, ya, tw, [term, *controls], seed=seed, minor=None, n_boot=200)
    delta, bprim = float(d["beta"]), float(prim["beta"])
    holds = bool(float(d["p"]) < 0.05 and delta >= 0.5 * bprim)
    out.update(available=True, delta=delta, p_delta=float(d["p"]), delta_ge_half_primary=bool(delta >= 0.5 * bprim), holds=holds,
               beta_lead_arm=beta_lead.get("beta"), beta_twin_arm=beta_twin.get("beta"),
               twin_below_lead=bool(beta_lead.get("testable") and beta_twin.get("testable") and float(beta_twin["beta"]) < float(beta_lead["beta"])))
    return out


# --- readings, arms and sensitivities (never a verdict) -----------------------------------------------------------------------------------------


def refit(X: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], mask: np.ndarray | None = None, *, term: str | None = None, seed: int = 0, minor: bool = True) -> dict:
    """A reported refit on a subset (``mask``) with fewer bootstrap draws; beta, p and n only."""
    m = np.ones(len(X), bool) if mask is None else np.asarray(mask, bool)
    A = X.loc[m].reset_index(drop=True)
    if len(A) < 30:
        return {"testable": False, "n": int(len(A))}
    ya = np.asarray(y, float)[m]
    r = fit10(A, ya, term or lt.TERM[test], controls, seed=seed, minor=g_minor(A, np.ones(len(A), bool), test) if minor else None, n_boot=200)
    return {"testable": bool(r.get("testable")), "beta": r.get("beta"), "p": r.get("p"), "n": int(r["_mask"].sum()) if r.get("testable") else int(len(A))}


def readings(X: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], prim: dict, spec: dict) -> dict:
    """Mechanism readings, secondaries, arms and dependence sensitivities of sections 2-4 / 1.7 that can be formed from the frozen and target files.
    Reported only; each is a refit with 200 bootstrap draws."""
    seed = int(spec["seeds"]["estimators"][test])
    term = lt.TERM[test]
    out: dict = {}
    sc = X["in_scope"].to_numpy(bool) if "in_scope" in X else np.ones(len(X), bool)
    out["S2_sports_arm"] = refit(X, y, test, controls, X["sports"].to_numpy(float) == 1, seed=seed)
    out["S2_crypto_arm"] = refit(X, y, test, controls, (X["crypto"].astype(str) == "crypto").to_numpy(), seed=seed)
    out["S3_excluded_event_arm"] = {"computed": False, "reason": "excluded-event origins carry status excluded_event and no unit line (1.4 item 8)"}
    out["mismatch_sensitive_refit_hv_only"] = refit(X, y, test, controls, X["hv"].to_numpy(bool), seed=seed)
    # dependence sensitivities (1.7)
    ys = np.asarray(y, float)
    out["sens_event_x_two_day_block"] = strip(fit10(X.assign(day=X["event_id"].astype(str) + "|" + X["block2"].astype(str)), ys, term, controls, seed=seed, n_boot=200))
    out["sens_pair_cluster"] = strip(fit10(X.assign(event_id=X["market_id"]), ys, term, controls, seed=seed, n_boot=200))
    first = (~X.assign(_h=X["hour"]).duplicated(["market_id", "_h"])).to_numpy()
    out["S5_pair_deduplicated"] = refit(X, y, test, controls, first, seed=seed, minor=False)
    out["S4_non_overlapping_grid"] = refit(X, y, test, controls, (X["t"].to_numpy(float) % 1200 == 0), seed=seed)
    h0, h1 = lt.epoch(HOLIDAY[0]), lt.epoch(HOLIDAY[1])
    out["holiday_excluded"] = refit(X, y, test, controls, ~((X["t"].to_numpy(float) >= h0) & (X["t"].to_numpy(float) < h1)), seed=seed)
    # both-demeaned (LT6): the target also expanding-past demeaned
    Y = pd.DataFrame({"y": ys, "market_id": X["market_id"], "t_row": X["t_row"]})
    yd = ab.demean(Y, ["y"], "market_id", "t_row", "expanding")["y"].to_numpy(float)
    out["both_demeaned"] = strip(fit10(X, yd, term, controls, seed=seed, n_boot=200))
    # the vendored per-pair block gate in pair x day (CH222: pair x two-day block) strata: a sensitivity only, never binding (1.8)
    # DESIGN-AMBIGUITY: the vendored block_fl_gate demeans within its group, so the group here is the pair x stratum key, not the pair.
    key = "block2" if test == "CH222" else "day"
    Xg = X.assign(_pk=X["market_id"].astype(str) + "|" + X[key].astype(str))
    ctrl = [c for c in controls if c in Xg and np.nanstd(Xg[c].to_numpy(float)) > 0]
    out["per_pair_block_gate_sensitivity"] = b.block_fl_gate(Xg, ys, term, ctrl, sign=+1, draws=int(spec["gates"]["draws"]), seed=int(spec["seeds"]["gates"][test]), min_n=int(spec["gates"]["min_rows_stratum"]),
                                                              group="_pk", order="t_row")
    if test == "CH224":
        m2 = X["y_m2"].to_numpy(float)
        out["S1_plus_10min"] = refit(X, X["y_s1"].to_numpy(float), test, controls, seed=seed, minor=False)
        out["M2_log_touch_size"] = refit(X, m2, test, controls, seed=seed, minor=False)
        zp = X["zdsK"].clip(lower=0)
        zm = X["zdsK"].clip(upper=0)
        out["M1_asymmetry"] = {k: refit(X.assign(_z=v), y, test, controls, term="_z", seed=seed, minor=False) for k, v in (("zdsK_plus", zp), ("zdsK_minus", zm))}
        two = (X["sP_t"].to_numpy(float) / np.maximum(X["p_tick"].to_numpy(float), 1e-9)) >= 2 - 1e-6
        out["floor_driven_refit_sP_ge_2_ticks"] = refit(X, y, test, controls, two, seed=seed, minor=False)
        out["reward_band_not_listed_refit"] = refit(X, y, test, controls, X["rewarded"].to_numpy(float) == 0, seed=seed, minor=False)
        out["S6_counts"] = {"by_tick": {str(k): int(v) for k, v in np.round(X["dsK"] / 0.01).value_counts().sort_index().head(21).items()}, "floorP": int((X["floorP"] == 1).sum()),
                            "floorK": int((X["floorK"] == 1).sum()), "rewarded": int((X["rewarded"] == 1).sum()), "rewarded_nan": int(X["rewarded"].isna().sum())}
    elif test == "CH223":
        out["S1_plus_10min"] = refit(X, X["y_s1"].to_numpy(float), test, controls, seed=seed)
        out["M1_signed_on_withdrawals"] = {"n": int(np.isfinite(X["y_m1"].to_numpy(float)).sum()), "mean_c": float(np.nanmean(X.loc[X["pull"] == 1, "y_m1"])) if (X["pull"] == 1).any() else None}
        out["M2_spread_change"] = refit(X, X["y_m2"].to_numpy(float), test, controls, seed=seed)
        out["refit_widening_only"] = refit(X, y, test, controls, ((X["pull"] == 0) | (X["widen"].astype(bool))).to_numpy(), seed=seed)
        out["refit_size_fall_only"] = refit(X, y, test, controls, ((X["pull"] == 0) | ((X["bid_fall"].astype(bool) | X["ask_fall"].astype(bool)) & ~X["widen"].astype(bool))).to_numpy(), seed=seed)
        pw = X[X["pull"] == 1]
        modal = pw.groupby("market_id")["moh"].agg(lambda s: s.value_counts().index[0]) if len(pw) else pd.Series(dtype=float)
        mm = X["market_id"].map(modal)
        out["bot_cadence_refit_without_modal_minute"] = refit(X, y, test, controls, ~((X["pull"] == 1) & (X["moh"] == mm)).to_numpy(), seed=seed)
        out["S6_counts"] = {"by_side": {str(k): int(v) for k, v in pw["pull_side"].value_counts().items()}, "size_zero": int(X["size_zero"].sum()),
                            "by_hour": {str(int(k)): int(v) for k, v in pw["hour"].value_counts().sort_index().items()}}
    else:
        out["S1_plus_10min"] = refit(X, X["y_s1"].to_numpy(float), test, controls, seed=seed)
        out["M1_plus_60min"] = refit(X, X["y_m1"].to_numpy(float), test, controls, seed=seed)
        tr = X[X["traded"] == 1]
        out["M2_trade_steps_dose"] = refit(tr.reset_index(drop=True), tr["y"].to_numpy(float), test, [c for c in controls], term="trade_steps", seed=seed, minor=False) if len(tr) >= 30 else {"testable": False}
        out["refit_vol_unknown_0_only"] = refit(X, y, test, controls, (X["vol_unknown"] == 0).to_numpy(), seed=seed)
        out["S4_abs_dk1_ge_1c"] = refit(X, y, test, controls, (X["abs_dk1"].to_numpy(float) >= 0.01 - EPS), seed=seed)
        out["raw_class_means_c"] = {"traded": float(np.nanmean(X.loc[X["traded"] == 1, "y"])) if (X["traded"] == 1).any() else None,
                                    "quote_only": float(np.nanmean(X.loc[X["traded"] == 0, "y"])) if (X["traded"] == 0).any() else None}
        out["S6_counts"] = {"trade_steps": {str(int(k)): int(v) for k, v in tr["trade_steps"].value_counts().sort_index().items()},
                            "by_hour": {str(int(k)): int(v) for k, v in X["hour"].value_counts().sort_index().items()}}
    out["in_scope_units"] = int(sc.sum())
    return out


# --- economics (1.10; separate; never changes a verdict; counts 0) -------------------------------------------------------------------------------


def e009_models(spec: dict) -> dict:
    path = Path(lt.__file__).resolve().parent / "model_specs" / (spec["economics"]["e009_spec"])
    if b.sha256_file(path) != spec["economics"]["e009_spec_sha256"]:
        raise Refused("E009's frozen spec differs from the recorded sha256 (1.10)")
    return json.loads(path.read_text())["models"]["20"]["m1"]


def taker_pnl10(side: np.ndarray, bid0, ask0, bid1, ask1, rate) -> np.ndarray:
    """E009's paper P&L per share (``cross_venue_live.taker_pnl``) with ``economics.taker_fee`` on both legs at the pair record's rate."""
    out = np.full(len(side), np.nan)
    for i, (s, b0, a0, b1, a1, r) in enumerate(zip(side, bid0, ask0, bid1, ask1, rate, strict=True)):
        if s > 0:
            gross, legs = b1 - a0, (a0, b1)
        elif s < 0:
            gross, legs = b0 - a1, (b0, a1)
        else:
            continue
        if not all(math.isfinite(x) for x in (gross, *legs, r)):
            continue
        out[i] = gross - economics.taker_fee(1.0, legs[0], r) - economics.taker_fee(1.0, legs[1], r)
    return out


def gross10(v, ev) -> dict:
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    return {"n": int(ok.sum()), "events": int(pd.unique(np.asarray(ev)[ok]).size) if ok.any() else 0, "mean": float(v[ok].mean()) if ok.any() else None, "note": "gross, no fills, no queue"}


def economics_block(X: pd.DataFrame, test: str, spec: dict) -> dict:
    """1.10: the taker rule (reported) on CH222's traded, quote-only and all moves; the gross maker readings of each test; the reward subset's gross rate
    per 20 minutes. No LT10 result is an economic check in the programme's sense (disclosed in the output)."""
    out: dict = {"hurdles": HURDLES, "note": "no resolution, hold-to-resolution or realised reward income is computed; 'not shown' is the expected taker outcome; none of this is the programme's economic check"}
    seed = int(spec["seeds"]["estimators"][test])
    if test == "CH222":
        m1 = e009_models(spec)
        feats = {f: X[f].to_numpy(float) for f in b.FEATURES}
        y1 = m1["intercept"] + sum(m1[f] * feats[f] for f in b.FEATURES)
        half0, half1 = X["sP_t"].to_numpy(float) / 2, X["sP_h20_ok"].to_numpy(float) / 2
        pm, pm1 = X["pmid"].to_numpy(float), X["mP_h20"].to_numpy(float)
        bid0, ask0, bid1, ask1 = pm - half0, pm + half0, pm1 - half1, pm1 + half1
        rate = X["fee_rate"].to_numpy(float)
        cost = np.array([b.round_trip_cost(bb, aa, rr) for bb, aa, rr in zip(bid0, ask0, rate, strict=True)])
        side = np.where(y1 > 0, 1, np.where(y1 < 0, -1, 0))
        trade = (side != 0) & np.isfinite(cost) & (np.abs(y1) > cost)
        pnl = np.where(trade, taker_pnl10(side, bid0, ask0, bid1, ask1, rate), np.nan)
        ev, day = X["event_id"].to_numpy(), X["day"].to_numpy()
        arms = {"traded": X["traded"].to_numpy() == 1, "quote_only": X["traded"].to_numpy() == 0, "all_moves": np.ones(len(X), bool)}
        out["taker_e009_rule"] = {k: {"signals_fired": int(trade[m].sum()), **ab.econ(pnl[m & trade], ev[m & trade], day[m & trade], seed)} for k, m in arms.items()}
        tr, qo = X["y"].to_numpy(float)[arms["traded"]], X["y"].to_numpy(float)[arms["quote_only"]]
        out["maker_gross_class_difference_c"] = {"traded_minus_quote_only": float(np.nanmean(tr) - np.nanmean(qo)) if len(tr) and len(qo) else None, "note": "what re-centring only on traded moves gains over re-centring on every move"}
    elif test == "CH224":
        sel = (X["tightK"] == 1) & (X["abs_dk1"].to_numpy(float) < 1e-5)
        tick = X["p_tick"].to_numpy(float)
        half = X["sP_t"].to_numpy(float) / 2
        pm, mh = X["pmid"].to_numpy(float), X["mP_h20"].to_numpy(float)
        bid_mark = mh - ((pm - half) + tick)
        ask_mark = ((pm + half) - tick) - mh
        ev = X["event_id"].to_numpy()
        out["maker_gross_improve_one_tick_after_kalshi_tightening"] = {"bid_side_mark_per_share": gross10(np.where(sel, bid_mark, np.nan), ev),
                                                                        "ask_side_mark_per_share": gross10(np.where(sel, ask_mark, np.nan), ev),
                                                                        "rule": "after tightK = 1 with |dk1| < 0.001c, one tick inside Polymarket's touch on each side for 20 minutes, marked against the mid at t + 20 min"}
    else:
        pull = X["pull"].to_numpy(float) == 1
        a = X["y"].to_numpy(float)
        d = float(np.nanmean(a[pull]) - np.nanmean(a[~pull])) if pull.any() and (~pull).any() else None
        size = float(np.nanmean(np.expm1(X["lpb_t"].to_numpy(float)) + np.expm1(X["lpa_t"].to_numpy(float))))
        out["maker_gross_class_difference"] = {"abs_move_diff_c": d, "mean_touch_size_both_sides": size, "note": "the adverse selection a maker who steps aside avoids, per quote; the taker route is M1 only"}
    rw = X["rewarded"].to_numpy(float) == 1
    out["reward_subset"] = {"rewarded_units": int(rw.sum()), "gross_reward_per_20min_mean": float(np.nanmean(X["reward_rate"].to_numpy(float)[rw]) * 20.0 / 1440.0) if rw.any() else None,
                            "note": "an upper bound; no reward is computed as earned (MAKER_REWARDS_STUDY.md scoring rule)"}
    return out


# --- one test --------------------------------------------------------------------------------------------------------------------------------


def run_test(out_root: Path, test: str, start: float, end: float, spec: dict, roles: tuple[str, ...], size_note: str | None) -> dict:
    df, acc = load_kind(out_root, test, start, end, spec, roles)
    res: dict = {"load": acc}
    if df.empty:
        return {**res, "available": False, "reason": "no lines", "primary": None, "gate": None}
    X = frame(df, test, spec)
    inscope = X["in_scope"].astype(bool).to_numpy()
    Xa = X[inscope].reset_index(drop=True)
    term = lt.TERM[test]
    controls = list(lt.CONTROLS[test])
    y = Xa["y"].to_numpy(float)
    # the primary needs a finite term (CH224 zdsK needs the pinned scale)
    if term not in Xa:
        return {**res, "available": False, "reason": f"{term} unavailable (scale_K missing)", "primary": None, "gate": None}
    seed = int(spec["seeds"]["estimators"][test])
    first = fit10(Xa, y, term, controls, seed=seed, minor=None)
    if not first.get("testable"):
        return {**res, "available": False, "reason": first.get("reason"), "primary": strip(first), "gate": None}
    ok = first["_mask"]
    minor = g_minor(Xa, ok, test)
    prim = fit10(Xa, y, term, controls, seed=seed, minor=minor) if minor is not None else first
    c = counts(Xa, ok, test)
    c["target_status"] = {k: int(v) for k, v in Xa["tg_status20"].astype(str).value_counts().items()} if "tg_status20" in Xa else {}
    res["counts"] = c
    res["unavailable_reason"] = unavailable(c, test, spec)
    res["available"] = res["unavailable_reason"] is None
    res["primary"] = strip(prim)
    res["gate"] = gate(Xa, y, test, controls, spec) if res["available"] else None
    res["f"] = f_rule(Xa, y, test, controls, prim, spec, lambda A, m: g_minor(A, m, test))
    res["_frame"] = Xa
    res["_y"] = y
    res["_prim"] = prim
    res["_controls"] = controls
    res["size_note"] = size_note
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
    """1.9. Supported: Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed, and F holds (CH224) / beta_twin < beta_lead
    (CH223). Otherwise, if everything else holds: Inconclusive with 'mechanical null not excluded' (or 'falsification unavailable'). Contradicted: the
    conservative 95% CI lies entirely on the other side of 0. Unavailable: the floors."""
    if not r.get("available"):
        return {"verdict": "Unavailable", "reason": r.get("unavailable_reason") or r.get("reason")}
    prim = r["primary"]
    pf, gl = p_for_holm(r)
    labels: list[str] = [gl] if gl else []
    f = r.get("f") or {}
    f_ok = bool(f.get("available") and f.get("holds"))
    cond = {"CH224": f_ok, "CH223": bool(f.get("available") and f.get("twin_below_lead")), "CH222": True}[test]
    base = (holm_p < 0.05) and (DIRECTION[test] * prim["beta"] > 0) and (gl is None)
    if base and cond:
        return {"verdict": "Supported", "labels": labels}
    lo, hi = prim["ci95_cons"]
    if (DIRECTION[test] > 0 and hi < 0) or (DIRECTION[test] < 0 and lo > 0):
        return {"verdict": "Contradicted", "labels": labels}
    if base and not cond:
        labels.append("falsification unavailable" if not f.get("available") else "mechanical null not excluded")
    return {"verdict": "Inconclusive", "labels": labels}


def labels_for(test: str, r: dict, v: dict, spec: dict, k: int, stream_gap: float | None, cc: dict) -> list[str]:
    lab = list(v.get("labels") or [])
    lab.append("informed (E009, E010)")
    if (spec.get("labels") or {}).get("informed_se4_se13"):
        lab.append("informed (se4/se13)")
    prim = r.get("primary") or {}
    f = r.get("f") or {}
    if v["verdict"] == "Unavailable":
        return lab + ([cc["label"]] if cc["label"] else [])
    beta = prim.get("beta")
    if beta is not None:
        # DESIGN-AMBIGUITY: 'material' (CH224) = the slope per census SD of zdsK (zdsK is in census-SD units) x 2.2 >= 1.0c; CH223 / CH222 = the class contrast beta >= 0.5c.
        if test == "CH224" and beta * 2.2 * 1.0 >= 1.0:  # sign-adjusted slope x 2.2 census SDs of zdsK (zdsK is in census-SD units)
            lab.append("material")
        if test in ("CH223", "CH222") and beta >= 0.5:
            lab.append("material")
    if test in ("CH223", "CH222") and not f.get("holds", False):
        lab.append("far-future not excluded")
    rd = r.get("readings") or {}
    if test == "CH224" and v["verdict"] == "Supported":
        fd = rd.get("floor_driven_refit_sP_ge_2_ticks") or {}
        if fd.get("testable") and (fd["beta"] <= 0 or fd["p"] >= 0.05):
            lab.append("floor-driven")
        rb = rd.get("reward_band_not_listed_refit") or {}
        if rb.get("testable") and rb["beta"] < 0:
            lab.append("reward-band-sensitive")
    mm = rd.get("mismatch_sensitive_refit_hv_only") or {}
    if mm.get("testable") and beta is not None and mm["beta"] * beta < 0:
        lab.append("mismatch-sensitive")
    X = r.get("_frame")
    if X is not None and len(X):
        top = X["event_id"].value_counts(normalize=True)
        if len(top) and float(top.iloc[0]) > 0.5:
            lab.append(f"event-concentrated ({float(top.iloc[0]):.0%})")
    if test == "CH222" and v["verdict"] == "Supported":
        cm = rd.get("raw_class_means_c") or {}
        if cm.get("traded") is not None and cm.get("quote_only") is not None and cm["traded"] < cm["quote_only"]:
            lab.append("quote-only dominated")
    if test == "CH223" and v["verdict"] == "Supported":
        bc = rd.get("bot_cadence_refit_without_modal_minute") or {}
        if bc.get("testable") and beta is not None and bc["beta"] * beta < 0:
            lab.append("bot-cadence")
    att = r.get("attrition") or {}
    if att.get("triggered"):
        lab.append(f"attrition-differential ({att['diff'] * 100:+.1f} pp)")
    if (r["load"].get("late_loss_share") or 0.0) > 0.02:
        lab.append(f"late-loss ({r['load']['late_loss_share']:.1%} of origin files written late)")
    # DESIGN-AMBIGUITY: 'the stream missed > 10% of the window's 120 s cycles' is read as the share of the window's scheduled cycles with no kind = cycle line in the successor's runs.jsonl.
    if stream_gap is not None and stream_gap > 0.10:
        lab.append(f"stream-gap ({stream_gap:.1%} of the window's cycles missing)")
    ho = rd.get("holiday_excluded") or {}
    if ho.get("testable") and beta is not None and (ho["beta"] * beta < 0 or ((ho["p"] < 0.05) != (prim.get("p", 1) < 0.05))):
        lab.append("holiday-sensitive")
    mde = ((spec.get("census_fixed") or {}).get("mde_c") or {}).get(test)
    if v["verdict"] == "Inconclusive" and mde and prim.get("se_day") is not None:
        g = int(prim.get("n_day", 0))
        if g >= 3:
            need = (float(t_dist.ppf(1 - 0.05 / max(k, 1), g - 1)) + float(t_dist.ppf(0.8, g - 1))) * float(prim["se_day"])
            if need > float(mde):
                lab.append("underpowered")
    if r.get("analytic_oversized"):
        lab.append("analytic p oversized in simulation")
    if cc["label"]:
        lab.append(cc["label"])
    return list(dict.fromkeys(lab))


def attrition_block(test: str, r: dict, spec: dict) -> dict:
    """1.5: the non-two_sided target share by contrasted class (|a_1 - a_0| > 2 pp triggers Lee-type bounds); CH224 contrasts the top and bottom
    terciles of its state. Never changes a verdict."""
    X = r["_frame"]
    status = X["tg_status20"].astype(str).to_numpy()
    if test == "CH224":
        z = X[lt.TERM[test]].to_numpy(float)
        lo, hi = np.nanquantile(z, [1 / 3, 2 / 3])
        cls = np.where(z <= lo, "bottom", np.where(z >= hi, "top", "mid"))
        pair = ("top", "bottom")
    else:
        cls = np.where(X[lt.TERM[test]].to_numpy(float) == 1, "1", "0")
        pair = ("1", "0")
    att = ab.attrition(status, cls, pair, 0.02)
    if att.get("triggered"):
        def rf(d, yy):
            return fit10(d, yy, lt.TERM[test], r["_controls"], seed=int(spec["seeds"]["estimators"][test]), n_boot=200)

        att["lee_bounds"] = ab.lee_bounds(X, r["_y"], cls, pair, att, rf)
    return att


# --- the single analysis ------------------------------------------------------------------------------------------------------------------------


def stream_gap_share(xv_root: Path, spec: dict) -> float | None:
    from .xv_quotes_poller import read_runs

    p = Path(xv_root) / "runs.jsonl"
    if not p.exists():
        return None
    s, e = lt.epoch(spec["registered_utc"]), lt.epoch(spec["end_utc"])
    n = sum(1 for x in read_runs(Path(xv_root)) if x.get("kind") == "cycle" and s <= x.get("t", -1) < e)
    exp = (e - s) / lt.POLL_S
    return float(1.0 - n / exp)


def analyze(out_root: Path = lt.OUT_ROOT, *, xv_root: Path = lt.XV_ROOT, spec: dict | None = None, now: float | None = None, force: bool = False,
            roles: tuple[str, ...] = (ROLE_CONF,)) -> dict:
    """The single registered analysis (see the module docstring). Refuses before ``ANALYSIS_NOT_BEFORE``, on an unpinned spec, a changed design text, a code
    hash that differs from the pins, a null / empty / unknown / dropped ``k_tests``, or an unfilled census value."""
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
            res[t] = {"verdict": {"verdict": "dropped at its census (uncounted; not in the Holm family)"}}
            continue
        note = sc.get(t)
        status = note.get("status") if isinstance(note, dict) else note
        size_note = None if status in (None, "pass") else (SIZE_LABEL if str(status).startswith("fail_size") else MECH_LABEL)
        r = run_test(out_root, t, s, e, spec, roles, size_note)
        r["analytic_oversized"] = bool(isinstance(note, dict) and note.get("analytic_oversized"))
        res[t] = r
    pv = {t: p_for_holm(res[t])[0] for t in ktests}
    hp = bd.holm(pv)
    gap = stream_gap_share(xv_root, spec)
    for t in ktests:
        r = res[t]
        if r.get("available") and r.get("primary"):
            r["attrition"] = attrition_block(t, r, spec)
            r["readings"] = readings(r["_frame"], r["_y"], t, r["_controls"], r["_prim"], spec)
            r["economics"] = economics_block(r["_frame"], t, spec)
        v = verdict(r, hp[t], t)
        r["holm_p"] = hp[t]
        v["labels"] = labels_for(t, r, v, spec, k, gap, cc)
        r["verdict"] = v
    for t in ktests:
        for key in ("_frame", "_y", "_prim", "_controls"):
            res[t].pop(key, None)
    res["holm"] = {"tests": ktests, "m": k, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True}
    res["counting"] = trials_line(spec, ktests)
    res.update(spec_sha=spec["_sha256"], code_sha256=cc["current"], code_check=cc, window=[spec["registered_utc"], spec["end_utc"]], roles=list(roles),
               stream_gap_share=gap, design_text_sha256=lt.design_text_sha())
    return bd._clean(res)


def trials_line(spec: dict, ktests: list[str]) -> dict:
    """The single counted trials line (``battery2.KIND_RULES['live_tests10']``, rule n_tests): k counted tests; gate draws, F, secondaries, readings,
    arms, economics, censuses and the size check count 0."""
    return {"kind": "live_tests10", "n_tests": len(ktests), "tests": ktests, "counts": "k = the Holm primaries that survived their census gates; everything else 0",
            "spec_sha256": spec["_sha256"], "evidence_role": ROLE_CONF}


# --- command-line entries -------------------------------------------------------------------------------------------------------------------------


def analyze_cli(args, write_out, now: float) -> int:
    try:
        spec = lt.load_spec(sha=lt.SPEC_SHA256)
        res = analyze(args.out_root, xv_root=args.xv_root, spec=spec, now=now)
    except (Refused, RuntimeError) as exc:
        print(f"refusing: {exc}")
        return 2
    return write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=str))



# --- the size check (1.8, 1.8.1) -----------------------------------------------------------------------------------------------------------------------


# scenario -> (statistics, binding tests). "gate" = the event-phase gate's rejection rate; "verdict" = the share of worlds where the analytic one-sided p
# is < 0.05 AND the test's verdict conditions beyond p hold (CH224: F; CH223: beta_twin < beta_lead; CH222: none), the gate omitted (1.8). World 10 binds
# twice for every test.
SCENARIO_ORDER = ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10")
SCENARIOS: dict[str, dict] = {
    "W1": {"stats": ("gate",), "tests": ("CH224", "CH223", "CH222")},
    "W2": {"stats": ("gate",), "tests": ("CH224", "CH223", "CH222")},
    "W3": {"stats": ("gate",), "tests": ("CH224", "CH223", "CH222")},
    "W4": {"stats": ("gate",), "tests": ("CH222",)},
    "W5": {"stats": ("gate",), "tests": ("CH222",)},
    "W6": {"stats": ("gate",), "tests": ("CH223",)},
    "W7": {"stats": ("gate",), "tests": ("CH223",)},
    "W8": {"stats": ("gate",), "tests": ("CH224",)},
    "W9": {"stats": ("verdict",), "tests": ("CH224",)},
    "W10": {"stats": ("gate", "verdict"), "tests": ("CH224", "CH223", "CH222")},
}
NULL_WORLDS_ANALYTIC = ("W1", "W2", "W3")  # the analytic p's own rate here decides the 'analytic p oversized in simulation' label (a convention)
POWER = {"CH224": ("1.0c per 2.2 SD of zdsK", 1.0 / 2.2, 41), "CH223": ("0.5c between classes", 0.5, 42), "CH222": ("0.5c between classes", 0.5, 43)}


def limit_for(worlds: int) -> float:
    return 0.05 + 1.645 * math.sqrt(0.0475 / worlds)


def evaluate_world(world: str, sub_seed: int, spec: dict, *, tests, stats, draws: int, plan=None, days=None, effect: bool = False, with_f: bool = False) -> dict:
    """One simulated world under each binding test. ``effect`` plants the power-run effect (non-binding). ``with_f`` adds the F rule (the reported F-arm rates)."""
    from . import live_tests10_worlds as W

    rng = np.random.default_rng(sub_seed)
    S = W.simulate(world, rng, plan=plan, days=days)
    u, tw = W.origin_frame(S, rng)
    out: dict = {}
    for t in tests:
        X, y = W.test_frame(u, tw, t, spec)
        term, controls = lt.TERM[t], list(lt.CONTROLS[t])
        if effect:
            y = y + POWER[t][1] * X[term].to_numpy(float)
        rec: dict = {"n": int(len(X))}
        ctrl = [c for c in controls if c in X and np.nanstd(X[c].to_numpy(float)) > 0]
        if "gate" in stats or effect:
            stratum, n_g = _stratum(t)
            g = lt.event_phase_fl_gate(X, y, term, ctrl, stratum=stratum, n_g=n_g, draws=draws, seed=int(sub_seed % (2**31 - 1)) + 17, sign=+1)
            rec.update(gate_testable=bool(g.get("testable")), gate_reject=bool(g.get("passes")))
        need_fit = ("verdict" in stats) or with_f or effect or (world in NULL_WORLDS_ANALYTIC)
        if need_fit:
            ok0 = np.isfinite(y)
            r = fit10(X, y, term, ctrl, seed=int(sub_seed % (2**31 - 1)), minor=None, n_boot=20)
            if r.get("testable"):
                ok = r["_mask"]
                minor = g_minor(X, ok, t)
                if minor is not None and minor < int(r["n_event"]):
                    r = fit10(X, y, term, ctrl, seed=int(sub_seed % (2**31 - 1)), minor=minor, n_boot=20)
                rec.update(p_analytic=float(r["p"]), analytic_reject=bool(r["p"] < 0.05), beta=float(r["beta"]), n_fit=int(ok.sum()))
                if "verdict" in stats or with_f:
                    f = f_rule(X, y, t, ctrl, r, spec, lambda A, m, _t=t: g_minor(A, m, _t))
                    cond = {"CH224": bool(f.get("available") and f.get("holds")), "CH223": bool(f.get("available") and f.get("twin_below_lead")), "CH222": True}[t]
                    rec.update(f_available=bool(f.get("available")), f_holds=bool(f.get("holds", False)), twin_below_lead=bool(f.get("twin_below_lead", False)),
                               verdict_reject=bool(r["p"] < 0.05 and cond))
            else:
                rec.update(p_analytic=1.0, analytic_reject=False, verdict_reject=False, fit_testable=False)
            rec["n_finite_target"] = int(ok0.sum())
        out[t] = rec
    return out


def size_check(*, worlds: int, draws: int, seed: int, spec: dict, tests=None, plan=None, days=None, power_worlds: int | None = None, reported_worlds: int | None = None,
               scenarios=SCENARIO_ORDER, progress=None) -> dict:
    """The size check: ``worlds`` worlds per scenario (the world's sub-seed is drawn from ONE generator seeded ``seed``, scenarios in table order), each
    evaluated under every binding test through the same event-phase gate path, strata and minima as the analysis. Criterion: the rate <= ``0.05 + 1.645 x
    sqrt(0.0475 / worlds)`` (0.058 at 2,000 worlds). Non-binding: power runs (planted effect; generators ``seed x 100 + n``), the F-arm rates in W1-W3
    (the first ``reported_worlds`` worlds) and the analytic p's own rates. A failing gate scenario sets only its tests to 'SE check failed (size scenario)',
    a failing verdict-size scenario to '(mechanical world)'; k is unchanged, no rerun, reseed or redesign."""
    lim = limit_for(worlds)
    alive = list(tests) if tests is not None else list(TESTS)
    master = np.random.default_rng(seed)
    res: dict = {t: {} for t in alive}
    analytic: dict = {t: {} for t in alive}
    freport: dict = {t: {} for t in alive}
    rep_n = worlds if reported_worlds is None else reported_worlds
    for sc in scenarios:
        spec_s = SCENARIOS[sc]
        bind = [t for t in spec_s["tests"] if t in alive]
        if not bind:
            continue
        tally = {t: {"gate": 0, "gate_n": 0, "verdict": 0, "verdict_n": 0, "an": 0, "an_n": 0, "f": 0, "f_n": 0, "tbl": 0, "tbl_n": 0} for t in bind}
        for i in range(worlds):
            sub = int(master.integers(1, 2**62))
            recs = evaluate_world(sc, sub, spec, tests=bind, stats=spec_s["stats"], draws=draws, plan=plan, days=days, with_f=(sc in NULL_WORLDS_ANALYTIC and i < rep_n))
            for t, r in recs.items():
                a = tally[t]
                if "gate" in spec_s["stats"]:
                    a["gate_n"] += 1
                    a["gate"] += int(r.get("gate_reject", False))
                if "verdict" in spec_s["stats"]:
                    a["verdict_n"] += 1
                    a["verdict"] += int(r.get("verdict_reject", False))
                if "analytic_reject" in r:
                    a["an_n"] += 1
                    a["an"] += int(r["analytic_reject"])
                if "f_holds" in r and sc in NULL_WORLDS_ANALYTIC:
                    a["f_n"] += 1
                    a["f"] += int(r["f_holds"])
                    a["tbl_n"] += 1
                    a["tbl"] += int(r.get("twin_below_lead", False))
            if progress:
                progress(sc, i + 1, worlds)
        for t in bind:
            a = tally[t]
            for stat in spec_s["stats"]:
                n, k = a[f"{stat}_n"], a[stat]
                rate = k / n if n else float("nan")
                res[t][f"{sc}:{stat}"] = {"scenario": sc, "stat": stat, "worlds": n, "rejections": k, "rate": rate, "limit": lim, "ok": bool(n == worlds and rate <= lim)}
            if a["an_n"]:
                analytic[t][sc] = {"worlds": a["an_n"], "rate": a["an"] / a["an_n"], "over_limit": bool(a["an"] / a["an_n"] > lim)}
            if a["f_n"]:
                freport[t][sc] = {"worlds": a["f_n"], "f_holds_rate": a["f"] / a["f_n"], "twin_below_lead_rate": a["tbl"] / a["tbl_n"]}
    out = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": res, "analytic_rates": analytic, "f_arm_rates_reported": freport}
    out["per_test"] = per_test_result(res, analytic, alive, worlds, scenarios)
    pw = power_worlds
    if pw:
        out["power_runs"] = {}
        for t in alive:
            label, _slope, n_ = POWER[t]
            g = np.random.default_rng(seed * 100 + n_)
            hit_g = hit_a = 0
            for _ in range(pw):
                r = evaluate_world("W1", int(g.integers(1, 2**62)), spec, tests=[t], stats=("gate",), draws=draws, plan=plan, days=days, effect=True)[t]
                hit_g += int(r.get("gate_reject", False))
                hit_a += int(r.get("analytic_reject", False))
            out["power_runs"][t] = {"effect": label, "worlds": pw, "gate_power": hit_g / pw, "analytic_power": hit_a / pw, "binding": False}
    return out


def per_test_result(res: dict, analytic: dict, alive: list[str], worlds: int, scenarios=SCENARIO_ORDER) -> dict:
    """Fail-closed scenario-to-test map: a test passes only if EVERY binding statistic of the scenarios it is bound to exists with ``worlds`` worlds and is
    within the limit. A missing or incomplete statistic fails the test (a failing scenario sets only its own tests; k unchanged)."""
    out = {}
    for t in alive:
        fails_size, fails_mech, missing = [], [], []
        for sc in scenarios:
            spec_s = SCENARIOS.get(sc)
            if spec_s is None:
                raise Refused(f"unknown size scenario {sc!r}")
            if t not in spec_s["tests"]:
                continue
            for stat in spec_s["stats"]:
                r = res.get(t, {}).get(f"{sc}:{stat}")
                if r is None or r["worlds"] != worlds:
                    missing.append(f"{sc}:{stat}")
                elif not r["ok"]:
                    (fails_size if stat == "gate" and not (sc == "W9") else fails_mech).append(f"{sc}:{stat}")
        status = "fail_size_scenario" if (fails_size or missing) else ("fail_mechanical_world" if fails_mech else "pass")
        # DESIGN-AMBIGUITY: 'analytic p oversized in simulation' = the analytic p's own rejection rate exceeds the limit in W1, W2 or W3 (the null worlds without a leak).
        over = [sc for sc, v in (analytic.get(t) or {}).items() if sc in NULL_WORLDS_ANALYTIC and v["over_limit"]]
        out[t] = {"status": status, "failed_size": fails_size, "failed_mechanical": fails_mech, "missing": missing, "analytic_oversized": bool(over), "analytic_over_in": over}
    return out


def size_check_cli(args, write_out) -> int:
    try:
        spec = lt.load_spec(sha=None)
    except RuntimeError as exc:
        print(f"refusing: {exc}")
        return 2
    if (e := lt.design_text_error()) is not None:
        print(f"refusing: {e['error']}")
        return 2
    sc = spec["size_check"]
    worlds = args.worlds if args.worlds is not None else int(sc["worlds"])
    draws = args.draws if args.draws is not None else int(sc["draws"])
    if worlds < 2 or draws < 1:
        print("refusing: worlds / draws too small")
        return 2
    tests = spec.get("k_tests")
    out = size_check(worlds=worlds, draws=draws, seed=int(spec["seeds"]["size_check"]), spec=spec, tests=list(tests) if tests else None,
                     power_worlds=int(sc["power_worlds"]) if not args.dev else int(getattr(args, "power_worlds", 0) or 0))
    out.update(code_sha256=lt.code_hashes(), spec_sha256=spec["_sha256"], design_text_sha256=lt.design_text_sha(), dev=bool(args.dev))
    return write_out(args.out, json.dumps(bd._clean(out), sort_keys=True, indent=1, default=str))
