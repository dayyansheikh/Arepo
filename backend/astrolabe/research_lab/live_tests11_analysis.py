# ruff: noqa: E501
"""LT11 single registered analysis (LIVE_TESTS_11.md 1.7-1.11, sections 2-4). Research only; never trades; reads only LT11's own write-once files.

Runs ONCE, on or after ``live_tests11.ANALYSIS_NOT_BEFORE``, on the pinned spec and code. One Holm family over the ``k`` primaries that survived their census
gates (spec ``k_tests``), one-sided, familywise alpha 0.05. A primary that is unavailable, whose gate fails (on data or in the size check) or whose spec is
incomplete enters Holm with p = 1. F, the point conditions, secondaries, readings, arms, placebos, economics and the census count 0.

Estimator (1.7): expanding-past market demeaning of every regressor (the vendored ``fit``: target raw), CR1 on the Gamma event, the two-way event x UTC day and the
UTC day; one-sided ``p = max(p_event on t with min(G_event, G_minor) - 1 df, p_two-way normal, p_day on t with G_day - 1 df)``; the conservative 95% CI is the hull of a
2,000-draw event bootstrap and the three Wald intervals. Falsification (1.9): the arm model with the far-future twin; ``Delta = beta(lead) - beta(twin)`` is the
coefficient on the lead when the SUM lead + twin is added as a control. The point conditions (quote-only twin, ask-sum twin, control panel) are estimates only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import bounce_decomp as bd
from . import live_tests11 as lt
from . import live_tests11_analysis_base as ab
from . import live_tests11_base as b

TESTS = lt.TESTS
DIRECTION = {t: +1 for t in TESTS}
ROLE_CONF = lt.ROLE_CONF
EPS = 1e-9
HOLIDAY = ("2026-11-26T00:00:00Z", "2026-11-28T00:00:00Z")  # 1.1: US Thanksgiving and the following day
MONTH_START = ("2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z")  # 1.1: reward programmes may be re-rated on 2026-12-01
GATE_LABEL = "SE check failed (gate on data)"
SIZE_LABEL = "SE check failed (size scenario)"
MECH_LABEL = "SE check failed (mechanical world)"
POINT_LABEL = {"CH234": "not traded-specific", "CH233": "not bid-specific", "CH232": "not reward-specific"}
DIFF_LABEL = {"CH234": "traded-difference significant", "CH233": "bid-difference significant", "CH232": "panel-difference significant"}
HURDLES = {"taker_100_usd_c": {"ge_100k": 2.9, "10k_100k": 3.9, "1k_10k": 7.2}, "touch_5_share_round_trip_c": 4.5, "passive_fill_1h": [0.017, 0.031], "passive_adverse_selection_c": 2.38,
           "makers_fill_weighted_non_sports_c": -0.37, "source": "cost-model-v1 (COST_MODEL.md) as LT11 1.10 quotes it"}


class Refused(RuntimeError):
    """The analysis refuses (a date, pin, spec or input check failed): nothing is written."""


# --- pins, refusals (1.1, 8.1) ----------------------------------------------------------------------------------------------------------------


def code_check(spec: dict) -> dict:
    """Compare the modules on disk with the spec's ``code_sha256`` map. A pinned spec refuses on any mismatch, an unfilled map, a null, empty or unknown ``k_tests``, a
    ``k_tests`` naming a dropped test, a null size-check result for a surviving test, or unfilled census values; a DRAFT spec only labels."""
    pins = spec.get("code_sha256") or {}
    cur = lt.code_hashes()
    status = {n: ("not pinned" if pins.get(n) is None else ("match" if pins.get(n) == h else "MISMATCH")) for n, h in cur.items()}
    if spec.get("_pinned"):
        bad = {n: s for n, s in status.items() if s != "match"}
        if bad:
            raise Refused(f"live_tests11 code sha256 does not match the registered pins: {bad}")
        if (err := lt.registration_error(spec)) is not None:
            raise Refused(err["error"])
        k = spec["k_tests"]
        drop = set(spec.get("dropped_tests") or [])
        if drop & set(k):
            raise Refused(f"live_tests11 k_tests names a dropped test: {sorted(drop & set(k))}")
        sc = spec.get("size_check_result")
        if not isinstance(sc, dict) or any(t not in sc for t in k):
            raise Refused("live_tests11 spec pinned without the recorded size-check result of every surviving test")
        for t in k:
            if lt.f_role(spec, t) != lt.F_ROLES[t]:
                raise Refused("F role mismatch")
    return {"current": cur, "pinned": {n: pins.get(n) for n in cur}, "status": status, "label": None if all(s == "match" for s in status.values()) else "DRAFT: code hashes not verified"}


def preconditions(spec: dict, now: float, *, force: bool = False) -> None:
    """The refusals of ``analyze`` that do not depend on any file: the analysis date, the frozen design text, a pinned spec."""
    if not force and now < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise Refused(f"the analysis runs only on or after {lt.ANALYSIS_NOT_BEFORE}")
    if (e := lt.design_text_error()) is not None:
        raise Refused(e["error"])
    if not force and not spec.get("_pinned"):
        raise Refused("the analysis refuses an unpinned spec (SPEC_SHA256 is None)")


# --- loading ---------------------------------------------------------------------------------------------------------------------------------


def load_kind(out_root: Path, test: str, start: float, end: float, spec: dict, roles: tuple[str, ...] = (ROLE_CONF,)) -> tuple[pd.DataFrame, dict]:
    """Frozen (not ``.late``) unit lines of origins in ``[start, end)`` with an allowed role (and, with a pinned spec, the pinned spec and code hashes), merged
    with their target files (columns suffixed ``_h1`` / ``_h2``; a missing file is ``pending``), CH232's sweep readings (``_s0`` / ``_s1``) and the twin file.
    Counts dropped lines and late files."""
    kind = lt.KINDS[test]
    out_root = Path(out_root)
    pinned = bool(spec.get("_pinned"))
    want_spec = spec["_sha256"][:16] if pinned else None
    pins = spec.get("code_sha256") or {}
    want_code = lt.joint_sha(pins.get("live_tests11.py"), pins.get("live_tests11_base.py")) if pinned else None
    acc = {"files": 0, "late_files": 0, "empty_files": 0, "noprev_files": 0, "dropped_role": 0, "dropped_spec_sha": 0, "dropped_code_sha": 0}
    parts = []
    fdir = out_root / kind / "frozen"
    for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
        if p.name.endswith(".late.csv.gz"):
            acc["late_files"] += 1
            continue
        if p.name.endswith(".empty.csv.gz"):
            acc["empty_files"] += 1
            continue
        if p.name.endswith(lt.MARKERS):
            acc["noprev_files"] += 1
            continue
        fr = pd.read_csv(p, dtype={"market_id": str, "event_id": str, "nrkey": str, "spec_sha": str, "code_sha": str, "role": str, "vclass": str, "arm": str, "skey": str, "kind": str,
                                   "size_class": str, "cheap_side": str, "fee_cat": str, "day": str, "condition_id": str}, float_precision="round_trip")
        acc["files"] += 1
        t0 = lt.b.slot_time(int(fr["slot"].iloc[0]), spec) if len(fr) else math.nan
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
        for h in (1, 2):
            op = out_root / kind / "outcomes" / f"{fid}.h{h}.csv.gz"
            if op.exists():
                o = pd.read_csv(op, dtype={"market_id": str, "status": str}, float_precision="round_trip", usecols=["market_id", "status", "bid", "ask"]).drop_duplicates("market_id")
                o = o.rename(columns={c: f"{c}_h{h}" for c in o.columns if c != "market_id"})
                fr = fr.merge(o, on="market_id", how="left")
                fr[f"status_h{h}"] = fr[f"status_h{h}"].fillna("absent")
            else:
                fr[f"status_h{h}"] = "pending"
        if test == "CH232":
            for s_ in (0, 1):
                op = out_root / kind / "outcomes" / f"{fid}.s{s_}.csv.gz"
                if op.exists():
                    o = pd.read_csv(op, dtype={"market_id": str, "status": str}, float_precision="round_trip", usecols=["market_id", "status", "dbid1", "dask1", "dbid5", "dask5"]).drop_duplicates("market_id")
                    o = o.rename(columns={c: f"{c}_s{s_}" for c in o.columns if c != "market_id"})
                    fr = fr.merge(o, on="market_id", how="left")
        tp = out_root / kind / "twins" / f"{fid}.csv.gz"
        if tp.exists():
            w = pd.read_csv(tp, dtype={"market_id": str}, float_precision="round_trip").drop_duplicates("market_id")
            fr = fr.merge(w, on="market_id", how="left")
        else:
            fr["tw_ok"] = np.nan
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    tot = acc["files"] + acc["late_files"]
    acc["late_loss_share"] = acc["late_files"] / tot if tot else 0.0
    return df, acc


def _day(t) -> np.ndarray:
    return pd.to_datetime(np.asarray(t, float), unit="s", utc=True).strftime("%Y-%m-%d").to_numpy()


def _tg(df: pd.DataFrame, h: int) -> np.ndarray:
    c = f"status_h{h}"
    return (df[c].astype(str).to_numpy() == "two_sided") if c in df else np.zeros(len(df), bool)


def _mid(df: pd.DataFrame, h: int) -> np.ndarray:
    ok = _tg(df, h)
    return np.where(ok, (df[f"bid_h{h}"].to_numpy(float) + df[f"ask_h{h}"].to_numpy(float)) / 2.0, np.nan) if f"bid_h{h}" in df else np.full(len(df), np.nan)


def frame(df: pd.DataFrame, test: str, spec: dict) -> pd.DataFrame:
    """Analysis columns of one test: market / event / time aliases for the vendored estimators, the census-fixed terms, the twin and the targets in cents
    (2.2, 3.3, 4.3). Rows without a two-sided target keep NaN targets (counted by the callers)."""
    X = df.copy()
    X["market_id"], X["t_row"] = X["market_id"].astype(str), X["t_row"].astype(float)
    X["event_id"] = X["event_id"].astype(str)
    X["day"] = _day(X["t_row"])
    reg = lt.epoch(spec["registered_utc"])
    X["block2"] = ((X["t_row"].to_numpy(float) - reg) // (2 * lt.DAY_S)).astype(int)
    X["slot_of_day"] = (X["slot"].to_numpy(int) % 12)
    cf = (spec.get("census_fixed") or {}).get(test) or {}
    m1, m2 = _mid(X, 1), _mid(X, 2)
    if test == "CH234":
        sg = X["sgn"].to_numpy(float)
        pk = X["p_k"].to_numpy(float)
        X["xw"] = lt.xw_term(X["w"].to_numpy(float), X["absd"].to_numpy(float), cf)
        if "w_tw" in X:
            X["xw_tw"] = lt.xw_term(X["w_tw"].to_numpy(float), X["absd_tw"].to_numpy(float), cf)
        X["y"] = sg * (m1 - pk) * 100.0
        X["y_m1"] = sg * (m2 - m1) * 100.0
        wa = X["w"].to_numpy(float) * X["absd"].to_numpy(float)
        v = wa[np.isfinite(wa)]
        X["xw_raw"] = (wa - float(v.mean())) / float(v.std(ddof=1)) if len(v) > 1 and v.std(ddof=1) > 0 else np.nan
        X["traded"] = (X["vclass"].astype(str) == "traded").astype(float)
    elif test == "CH233":
        X["zcl"] = lt.zcl_term(X["cl_sib"].to_numpy(float), X["size_class"].to_numpy(object), cf)
        X["zca"] = lt.zcl_term(X["ca_sib"].to_numpy(float), X["size_class"].to_numpy(object), cf)
        if "cl_sib_tw" in X:
            X["zcl_tw"] = lt.zcl_term(X["cl_sib_tw"].to_numpy(float), X["size_class_tw"].to_numpy(object) if "size_class_tw" in X else X["size_class"].to_numpy(object), cf)
        sp1 = (X["ask_h1"].to_numpy(float) - X["bid_h1"].to_numpy(float)) * 100.0 if "ask_h1" in X else np.full(len(X), np.nan)
        X["y"] = np.where(_tg(X, 1), sp1 - X["spread_k_c"].to_numpy(float), np.nan)
        X["y_m1"] = np.where(_tg(X, 1), (X["bid_h1"].to_numpy(float) - X["bid_k"].to_numpy(float)) * 100.0, np.nan) if "bid_h1" in X else np.nan
        X["y_m2"] = np.where(_tg(X, 1), (m1 - (X["bid_k"].to_numpy(float) + X["ask_k"].to_numpy(float)) / 2.0) * 100.0, np.nan)
        X["hb_cross"] = ((X["hb_km1"].to_numpy(float) > 0) & (X["hb_k"].to_numpy(float) <= 0)).astype(float)
        X["wr"] = X["near_zero_km1"].to_numpy(float)
        X["zcl_wr"] = X["zcl"].to_numpy(float) * X["wr"].to_numpy(float)
    else:
        sp1 = (X["ask_h1"].to_numpy(float) - X["bid_h1"].to_numpy(float)) * 100.0 if "ask_h1" in X else np.full(len(X), np.nan)
        X["y"] = np.where(_tg(X, 1), sp1 - X["spread_k_c"].to_numpy(float), np.nan)
        side = X["cheap_side"].astype(str).to_numpy()
        reading = lt.M1_SIDE_READING if spec.get("m1_side_reading") is None else spec["m1_side_reading"]
        sides = lt.m1_side(reading)
        bid_ret = -(X["bid_h1"].to_numpy(float) - X["bid_k"].to_numpy(float)) * 100.0 if "bid_h1" in X else np.full(len(X), np.nan)
        ask_ret = (X["ask_h1"].to_numpy(float) - X["ask_k"].to_numpy(float)) * 100.0 if "ask_h1" in X else np.full(len(X), np.nan)
        cheap = np.where(side == "bid", bid_ret, ask_ret)
        dear = np.where(side == "bid", ask_ret, bid_ret)
        X["y_m1"] = np.where(_tg(X, 1), cheap if sides[0] == "cheap" else dear, np.nan)
        lower = X["upper"].to_numpy(float) == 0
        X["y_m2"] = np.where(_tg(X, 1), np.where(lower, 1.0, -1.0) * (m1 - X["m_k"].to_numpy(float)) * 100.0, np.nan)
    X, _ = lt.fee_dummies(X)
    return X


# --- estimator and inference (1.7) ----------------------------------------------------------------------------------------------------------------------


def g_minor(X: pd.DataFrame, ok: np.ndarray, test: str) -> int | None:
    """G_minor = the number of events holding at least one counted crossing (CH232's sparse class, 1.7); None for CH234 and CH233."""
    if test != "CH232":
        return None
    v = X["xo"].to_numpy(float)[ok]
    return int(pd.unique(X["event_id"].to_numpy()[ok][v == 1]).size)


def fit11(X: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, seed: int, minor: int | None = None, n_boot: int = ab.N_BOOT, sign: int = +1) -> dict:
    """The vendored LT3 ``fit`` (event p on t with G_event - 1 df), then 1.7's rule: ``p = max(p_event on t with min(G_event, G_minor) - 1 df, p_two-way normal,
    p_day on t with G_day - 1 df)`` and the conservative CI widened to the two-way Wald interval. ``sign`` = the predicted direction (+1 for every primary;
    -1 only for CH233's M1 reading, predicted < 0)."""
    ctrl = [c for c in controls if c in X and np.nanstd(X[c].to_numpy(float)) > 0 and c != term]
    r = ab.fit(X, y, term, ctrl, sign=sign, group="market_id", order="t_row", ev="event_id", time="day", ev_t_ref=True, seed=seed, n_boot=n_boot)
    r["dropped_controls"] = [c for c in controls if c not in ctrl]
    if not r.get("testable"):
        return r
    g_e = int(r["n_event"])
    df_e = g_e - 1
    if minor is not None and minor < g_e:
        df_e = max(int(minor) - 1, 0)
        r["p_event"] = float(t_dist.sf(sign * r["z_event"], df=df_e)) if df_e >= 1 else 1.0
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


def primary_population(X: pd.DataFrame, test: str, spec: dict) -> tuple[pd.DataFrame, dict]:
    """The primary population of each test from the frozen lines: CH234 traded, ``ladder`` 0, in scope; CH233 the ``primary`` arm; CH232 the ``out`` arm, in scope,
    ``ladder`` 0, reward status finite, the panel fixed at the market's first unit (``panel_switched`` counted) and the reward panel (the control panel is the
    point condition's); the census-fixed series family is excluded."""
    cnt: dict = {"lines": len(X)}
    cf = (spec.get("census_fixed") or {}).get(test) or {}
    if test == "CH234":
        m = (X["in_scope"] == 1) & (X["ladder"] == 0) & (X["vclass"].astype(str) == "traded")
    elif test == "CH233":
        m = (X["arm"].astype(str) == "primary")
    else:
        m = (X["arm"].astype(str) == "out") & (X["in_scope"] == 1) & (X["ladder"] == 0) & np.isfinite(X["rew"].to_numpy(float))
        cnt["reward_status_nan_excluded"] = int(((X["arm"].astype(str) == "out") & ~np.isfinite(X["rew"].to_numpy(float))).sum())
    P = X[m].reset_index(drop=True)
    if test == "CH232":
        P, pc = lt.fix_panels11(P)
        cnt.update(pc)
    fam = cf.get("exclude_family")
    if fam:
        cnt["family_excluded"] = int((P["skey"].astype(str) == fam).sum())
        P = P[P["skey"].astype(str) != fam].reset_index(drop=True)
    cnt["population"] = len(P)
    return P, cnt


def counts(X: pd.DataFrame, ok: np.ndarray, test: str) -> dict:
    ev = X["event_id"].to_numpy()[ok]
    out = {"units": int(ok.sum()), "events": int(pd.unique(ev).size), "days": int(pd.unique(X["day"].to_numpy()[ok]).size), "g_eff": lt.g_eff(ev) if len(ev) else float("nan")}
    if test == "CH232":
        out["crossings"] = int((X["xo"].to_numpy(float)[ok] == 1).sum())
    if test == "CH233":
        vc = pd.Series(ev).value_counts()
        out["events_ge48"] = int((vc >= 48).sum())
    return out


def unavailable(c: dict, test: str, spec: dict, extra: dict) -> str | None:
    """1.9's Unavailable: fewer than 20,000 units, fewer than 300 events, Kish G_eff below 15, fewer than 10 UTC days with units; CH234 also fewer than 20,000
    quote-only units; CH233 fewer than 100 events with >= 48 units; CH232 fewer than 2,000 counted crossings or 1,000 control-panel crossings."""
    f = (spec.get("verdict") or {}).get("floors") or {}
    if c["units"] < f.get("units", 20000):
        return f"fewer than {f.get('units', 20000)} units"
    if c["events"] < f.get("events", 300):
        return f"fewer than {f.get('events', 300)} events"
    if not (c["g_eff"] >= f.get("g_eff", 15)):
        return f"G_eff below {f.get('g_eff', 15)}"
    if c["days"] < f.get("days", 10):
        return f"fewer than {f.get('days', 10)} UTC days with units"
    if test == "CH234" and extra.get("quote_only_units", 0) < f.get("CH234_quote_only_units", 20000):
        return "fewer than 20,000 quote-only units"
    if test == "CH233" and c.get("events_ge48", 0) < f.get("CH233_events_ge48", 100):
        return "fewer than 100 events with >= 48 units"
    if test == "CH232" and (c.get("crossings", 0) < f.get("CH232_crossings", 2000) or extra.get("control_crossings", 0) < f.get("CH232_control_crossings", 1000)):
        return "fewer than 2,000 counted crossings or 1,000 control-panel crossings"
    return None


# --- the gates (1.8) ----------------------------------------------------------------------------------------------------------------------------------


def event_index_fl_gate(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, draws: int, seed: int, sign: int = 1, min_rows: int = 16, group: str = "market_id",
                        order: str = "t_row", event: str = "event_id", slot: str = "slot") -> dict:
    """CH233's event-phase block (circular-shift) Freedman-Lane gate (1.8, R1 should-fix 7). Expanding-past demeaning of every regressor within market; the
    reduced model's residuals are circularly shifted on the EVENT's capture index ``I_e`` (the ordered captures at which the event has at least one unit):
    ``n_e = |I_e|``, ``s_e = max(4, ceil(n_e / 4))``, ONE offset ``o`` per event and draw on ``[s_e, n_e - s_e]``; member i's unit at position t takes the residual of
    member i at ``(t + o) mod n_e``; if member i has no unit there the unit at t is OMITTED from that draw's refit (never filled, never borrowed). Events with fewer
    than ``min_rows`` captures on their index (``n_e``, as the census's block-gate share counts them) are excluded from the gate (counted). ``p_perm = (1 + #{sign beta* >= sign beta}) / (1 + draws)``; passes if < 0.05. The omitted share
    per draw is returned (median and maximum)."""
    X = b.demean(df, [term, *controls], group, order, "expanding")
    yv = np.asarray(y, float)
    ok = np.isfinite(yv) & np.all(np.isfinite(X.to_numpy()), axis=1)
    if ok.sum() < 10:
        return {"testable": False, "passes": False, "reason": "fewer than 10 rows"}
    Z = X[controls].to_numpy()[ok] if controls else np.zeros((int(ok.sum()), 0))
    xt = b._partial(Z, X[term].to_numpy()[ok])
    e = b._partial(Z, yv[ok])
    sxx = float(xt @ xt)
    if sxx <= 1e-18:
        return {"testable": False, "passes": False, "reason": "no residual variation in the term"}
    real = float(xt @ e / sxx)
    ev = df[event].astype(str).to_numpy()[ok]
    mk = df[group].astype(str).to_numpy()[ok]
    sl = df[slot].to_numpy(float)[ok]
    plan, fixed_num, fixed_den, n_planned, n_excl_rows = [], 0.0, 0.0, 0, 0
    ev_codes = pd.factorize(ev)[0]
    order_idx = np.argsort(ev_codes, kind="mergesort")
    bounds = np.flatnonzero(np.diff(ev_codes[order_idx])) + 1
    for idx in np.split(order_idx, bounds):
        positions = np.unique(sl[idx])
        n_e = len(positions)
        s_e = max(4, math.ceil(n_e / 4))
        if n_e < min_rows or n_e - s_e < s_e:  # 1.8 / 7: an event needs >= 16 shiftable CAPTURES on its index (the census counts captures too)
            fixed_num += float(xt[idx] @ e[idx])
            fixed_den += float(xt[idx] @ xt[idx])
            n_excl_rows += len(idx)
            continue
        members = pd.factorize(mk[idx])[0]
        pos = np.searchsorted(positions, sl[idx])
        M = int(members.max()) + 1
        XT, E = np.full((M, n_e), np.nan), np.full((M, n_e), np.nan)
        XT[members, pos], E[members, pos] = xt[idx], e[idx]
        plan.append((XT, E, n_e, s_e))
        n_planned += len(idx)
    if not plan:
        return {"testable": False, "passes": False, "reason": f"no event with >= {min_rows} captures on a shiftable capture index", "excluded_rows": n_excl_rows}
    rng = np.random.default_rng(seed)
    ge, om_share = 0, []
    tot_units = sum(int(np.isfinite(XT).sum()) for XT, _, _, _ in plan)
    for _ in range(draws):
        num, den, omitted = fixed_num, fixed_den, 0
        for XT, E, n_e, s_e in plan:
            o = int(rng.integers(s_e, n_e - s_e + 1))
            Es = np.roll(E, -o, axis=1)
            v = np.isfinite(XT) & np.isfinite(Es)
            omitted += int((np.isfinite(XT) & ~np.isfinite(Es)).sum())
            num += float(np.sum(XT[v] * Es[v]))
            den += float(np.sum(XT[v] ** 2))
        bb = num / den if den > 0 else 0.0
        ge += int(sign * bb >= sign * real)
        om_share.append(omitted / tot_units if tot_units else 0.0)
    p = (1 + ge) / (1 + draws)
    return {"testable": True, "real": real, "p_perm": p, "passes": bool(p < 0.05), "draws": draws, "method": "event-phase block circular-shift Freedman-Lane (one offset per event, event capture index)",
            "events_shifted": len(plan), "excluded_rows": n_excl_rows, "share_rows_shifted": n_planned / int(ok.sum()), "omitted_share_median": float(np.median(om_share)), "omitted_share_max": float(np.max(om_share))}


def gate(X: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], spec: dict) -> dict:
    """The block Freedman-Lane gate (1.8) on the primary model: market strata for CH234 and CH232 (the vendored LT5 ``block_fl_gate``), the event-phase form for
    CH233. A failed gate gives p = 1 and the label 'SE check failed (gate on data)'."""
    ctrl = [c for c in controls if c in X and np.nanstd(X[c].to_numpy(float)) > 0]
    g = spec["gates"]
    term = lt.TERM[test]
    if test == "CH233":
        return event_index_fl_gate(X, y, term, ctrl, draws=int(g["draws"]), seed=int(spec["seeds"]["gates"][test]), sign=+1, min_rows=int(g["min_shift_rows"]))
    return b.block_fl_gate(X, y, term, ctrl, sign=+1, draws=int(g["draws"]), seed=int(spec["seeds"]["gates"][test]), min_n=int(g["block_min_n"]), group="market_id", order="t_row")


# --- falsification and the point conditions (1.9) ----------------------------------------------------------------------------------------------------------


def f_rule(X: pd.DataFrame, y: np.ndarray, test: str, controls: list[str], prim: dict, spec: dict) -> dict:
    """The arm model: the primary model with the far-future twin added on the units that have it (a finite twin and ``f_end_ok``; a unit failing the 7 h end rule
    stays in the primary and is out of the F arm). ``Delta = beta(lead) - beta(twin)`` is the coefficient on the lead with ``lead + twin`` added as a control. F
    holds iff the one-sided p of Delta < 0.05 (the 1.7 rule, not Holm-adjusted, counted 0) and Delta-hat >= 0.5 x beta-hat(primary). An arm with fewer than 50% of
    the primary's units: falsification unavailable."""
    term, tw = lt.TERM[test], lt.TWIN[test]
    out: dict = {"role": lt.f_role(spec, test)}
    if tw not in X:
        return {**out, "available": False, "reason": "no twin column"}
    ok_p = prim["_mask"]
    arm = ok_p & np.isfinite(X[tw].to_numpy(float)) & (X["f_end_ok"].to_numpy(float) == 1)
    share = float(arm.sum() / max(1, ok_p.sum()))
    out.update(arm_units=int(arm.sum()), arm_share=share)
    if share < spec["verdict"]["f_rule"]["arm_min_share"] or arm.sum() < 10:
        return {**out, "available": False, "reason": "arm has fewer than 50% of the primary's units (falsification unavailable)"}
    A = X.loc[arm].reset_index(drop=True)
    ya = np.asarray(y, float)[arm]
    A["_sum"] = A[term].to_numpy(float) + A[tw].to_numpy(float)
    seed = int(spec["seeds"]["estimators"][test])
    d = fit11(A, ya, term, ["_sum", *controls], seed=seed, minor=g_minor(A, np.ones(len(A), bool), test), n_boot=200)
    if not d.get("testable"):
        return {**out, "available": False, "reason": d.get("reason")}
    beta_lead = fit11(A, ya, term, [tw, *controls], seed=seed, n_boot=200)
    beta_twin = fit11(A, ya, tw, [term, *controls], seed=seed, n_boot=200)
    delta, bprim = float(d["beta"]), float(prim["beta"])
    holds = bool(float(d["p"]) < spec["verdict"]["f_rule"]["delta_p_max"] and delta >= spec["verdict"]["f_rule"]["delta_over_primary_min"] * bprim)
    out.update(available=True, delta=delta, p_delta=float(d["p"]), delta_ge_half_primary=bool(delta >= 0.5 * bprim), holds=holds, beta_lead_arm=beta_lead.get("beta"), beta_twin_arm=beta_twin.get("beta"))
    return out


def point_condition(Xall: pd.DataFrame, test: str, controls: list[str], prim: dict, spec: dict, y_all: np.ndarray, seed: int) -> dict:
    """The binding point condition of 1.9 (estimates only, no test, counted 0): CH234 the quote-only twin model's slope on ``xw`` (same controls and demeaning)
    below half the traded slope; CH233 the ask-sum twin model (``z ca_sib`` in place of ``z cl_sib``) below half the bid slope; CH232 the control panel's crossing
    coefficient below half the reward panel's. The difference's one-sided p is reported (a label), none is a significance condition."""
    ratio = spec["verdict"]["point_condition_ratio"]
    bprim = float(prim["beta"])
    out: dict = {"ratio": ratio, "beta_primary": bprim}
    if test == "CH234":
        Q = Xall[(Xall["in_scope"] == 1) & (Xall["ladder"] == 0) & (Xall["vclass"].astype(str) == "quote_only")].reset_index(drop=True)
        fam = ((spec.get("census_fixed") or {}).get(test) or {}).get("exclude_family")
        Q = Q[Q["skey"].astype(str) != fam] if fam else Q
        Q = Q.reset_index(drop=True)
        r = fit11(Q, Q["y"].to_numpy(float), "xw", controls, seed=seed, n_boot=200) if len(Q) >= 30 else {"testable": False}
        out["beta_alt"], out["alt_name"], out["alt_units"] = r.get("beta"), "quote-only slope on xw", int(len(Q))
        P = pd.concat([Xall[(Xall["in_scope"] == 1) & (Xall["ladder"] == 0) & (Xall["vclass"].astype(str).isin(["traded", "quote_only"]))]], ignore_index=True)
        P = P.assign(xw_x_traded=P["xw"] * P["traded"])
        d = fit11(P, P["y"].to_numpy(float), "xw_x_traded", ["xw", "traded", *controls], seed=seed, n_boot=200) if len(P) >= 60 else {"testable": False}
        out["p_difference"], out["beta_difference"] = d.get("p"), d.get("beta")
    elif test == "CH233":
        P = Xall[Xall["arm"].astype(str) == "primary"].reset_index(drop=True)
        r = fit11(P, P["y"].to_numpy(float), "zca", [c for c in controls], seed=seed, n_boot=200) if len(P) >= 30 else {"testable": False}
        out["beta_alt"], out["alt_name"] = r.get("beta"), "ask-sum twin slope on z ca_sib"
        both = P.assign(_sum=P["zcl"] + P["zca"])  # LT11 ambiguity A23 (revised): beta_bid - beta_ask is the coefficient on zcl with zcl + zca added, as F's Delta
        d = fit11(both, both["y"].to_numpy(float), "zcl", ["_sum", *controls], seed=seed, n_boot=200) if len(P) >= 60 else {"testable": False}
        out["p_difference"], out["beta_difference"] = d.get("p"), d.get("beta")
    else:
        C = Xall[(Xall["arm"].astype(str) == "out") & (Xall["in_scope"] == 1) & (Xall["ladder"] == 0) & np.isfinite(Xall["rew"].to_numpy(float))].reset_index(drop=True)
        C, _ = lt.fix_panels11(C)
        Cc = C[C["panel"] == 0].reset_index(drop=True)
        r = fit11(Cc, Cc["y"].to_numpy(float), "xo", controls, seed=seed, minor=g_minor(Cc, np.ones(len(Cc), bool), test), n_boot=200) if len(Cc) >= 30 else {"testable": False}
        out["beta_alt"], out["alt_name"], out["alt_units"] = r.get("beta"), "control-panel crossing coefficient", int(len(Cc))
        C = C.assign(xo_x_rew=C["xo"] * C["panel"])
        d = fit11(C, C["y"].to_numpy(float), "xo_x_rew", ["xo", *controls], seed=seed, n_boot=200) if len(C) >= 60 else {"testable": False}
        out["p_difference"], out["beta_difference"] = d.get("p"), d.get("beta")
    b_alt = out.get("beta_alt")
    out["available"] = b_alt is not None and math.isfinite(float(b_alt))
    out["holds"] = bool(out["available"] and float(b_alt) < ratio * bprim)
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
    if term not in P or P.empty:
        return {**res, "available": False, "reason": f"{term} unavailable (census-fixed scale missing or no primary units)", "primary": None, "gate": None}
    y = P["y"].to_numpy(float)
    seed = int(spec["seeds"]["estimators"][test])
    first = fit11(P, y, term, controls, seed=seed)
    if not first.get("testable"):
        return {**res, "available": False, "reason": first.get("reason"), "primary": strip(first), "gate": None}
    ok = first["_mask"]
    minor = g_minor(P, ok, test)
    prim = fit11(P, y, term, controls, seed=seed, minor=minor) if minor is not None else first
    c = counts(P, ok, test)
    c["target_status"] = {k: int(v) for k, v in P["status_h1"].astype(str).value_counts().items()}
    extra = {}
    if test == "CH234":
        extra["quote_only_units"] = int(((Xall["in_scope"] == 1) & (Xall["ladder"] == 0) & (Xall["vclass"].astype(str) == "quote_only") & np.isfinite(Xall["y"].to_numpy(float))).sum())
    if test == "CH232":
        Cn = Xall[(Xall["arm"].astype(str) == "out") & (Xall["in_scope"] == 1) & (Xall["ladder"] == 0) & np.isfinite(Xall["rew"].to_numpy(float))]
        Cn, _ = lt.fix_panels11(Cn.reset_index(drop=True))
        extra["control_crossings"] = int(((Cn["panel"] == 0) & (Cn["xo"] == 1) & np.isfinite(Cn["y"].to_numpy(float))).sum())
    res["counts"], res["extra_counts"] = c, extra
    res["unavailable_reason"] = unavailable(c, test, spec, extra)
    res["available"] = res["unavailable_reason"] is None
    res["primary"] = strip(prim)
    res["gate"] = gate(P, y, test, controls, spec) if res["available"] else None
    res["f"] = f_rule(P, y, test, controls, prim, spec)
    res["point_condition"] = point_condition(Xall, test, controls, prim, spec, Xall["y"].to_numpy(float), seed) if res["available"] else {"available": False}
    res.update(_frame=P, _all=Xall, _y=y, _prim=prim, _controls=controls, size_note=size_note)
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
    """1.9. Supported: Holm-adjusted one-sided p < 0.05, estimate > 0, gate passed, F holds and the point condition holds. Otherwise, if everything else holds:
    Inconclusive with 'mechanical null not excluded' (or 'falsification unavailable') / the test's 'not ...-specific' label. Contradicted: the conservative 95% CI
    lies entirely below 0. Unavailable: the floors."""
    if not r.get("available"):
        return {"verdict": "Unavailable", "reason": r.get("unavailable_reason") or r.get("reason")}
    prim = r["primary"]
    pf, gl = p_for_holm(r)
    labels: list[str] = [gl] if gl else []
    f = r.get("f") or {}
    pcond = r.get("point_condition") or {}
    f_ok = bool(f.get("available") and f.get("holds"))
    pc_ok = bool(pcond.get("holds"))
    base = (holm_p < 0.05) and (DIRECTION[test] * prim["beta"] > 0) and (gl is None)
    if base and f_ok and pc_ok:
        return {"verdict": "Supported", "labels": labels}
    lo, hi = prim["ci95_cons"]
    if hi < 0:
        return {"verdict": "Contradicted", "labels": labels}
    if base and not f_ok:
        labels.append("falsification unavailable" if not f.get("available") else "mechanical null not excluded")
    if base and not pc_ok:
        labels.append(POINT_LABEL[test])
    return {"verdict": "Inconclusive", "labels": labels}


# --- readings, attrition, economics (1.9, 1.10; estimates only, count 0) ----------------------------------------------------------------------------------


def _refit(r: dict, mask: np.ndarray, spec: dict, test: str, *, term: str | None = None, controls: list[str] | None = None) -> dict:
    P, y = r["_frame"], r["_y"]
    sub = P[mask].reset_index(drop=True)
    if len(sub) < 30:
        return {"testable": False, "reason": "fewer than 30 units"}
    ok = np.ones(len(sub), bool)
    return strip(fit11(sub, y[mask], term or lt.TERM[test], controls or r["_controls"], seed=int(spec["seeds"]["estimators"][test]), minor=g_minor(sub, ok, test), n_boot=200)) or {}


def readings(r: dict, test: str, spec: dict) -> dict:
    """Estimates only: the window excluding the US holiday and the 2026-12-01 reward re-rating day, and per-category refits (crypto, non-crypto). Never a verdict."""
    P = r["_frame"]
    t = P["t_row"].to_numpy(float)
    h0, h1 = lt.epoch(HOLIDAY[0]), lt.epoch(HOLIDAY[1])
    m0, m1 = lt.epoch(MONTH_START[0]), lt.epoch(MONTH_START[1])
    out = {"holiday_excluded": _refit(r, ~((t >= h0) & (t < h1)), spec, test), "month_start_excluded": _refit(r, ~((t >= m0) & (t < m1)), spec, test)}
    if "cat" in P:
        crypto = P["cat"].astype(str).to_numpy() == "crypto"
        out["crypto_only"] = _refit(r, crypto, spec, test)
        out["non_crypto"] = _refit(r, ~crypto, spec, test)
    return out


def attrition_block(test: str, r: dict, spec: dict) -> dict:
    """1.5-style: the non-two_sided target share by contrasted class (|a_1 - a_0| > 2 pp triggers Lee-type bounds). Never changes a verdict."""
    X = r["_frame"]
    status = X["status_h1"].astype(str).to_numpy()
    cls = np.where(X[lt.TERM[test]].to_numpy(float) > 0, "1", "0")
    att = ab.attrition(status, cls, ("1", "0"), spec["verdict"]["attrition_pp"] / 100.0)
    if att.get("triggered"):
        att["lee_bounds"] = ab.lee_bounds(X, r["_y"], cls, ("1", "0"), att, lambda d, yy: fit11(d, yy, lt.TERM[test], r["_controls"], seed=int(spec["seeds"]["estimators"][test]), n_boot=200))
    return att


def economics_block(r: dict, test: str, spec: dict) -> dict:
    """1.10: the hurdles quoted for reference and the gross, no-fill, no-queue class contrast of each test's target. No LT11 result is the programme's economic check."""
    X, y = r["_frame"], r["_y"]
    out: dict = {"hurdles": HURDLES, "note": "gross, no fills, no queue, no realised rewards; none of this is the programme's economic check"}
    term = X[lt.TERM[test]].to_numpy(float)
    hi, lo = term > 0, term <= 0
    ok = np.isfinite(y)
    out["gross_target_by_term_sign_c"] = {"positive": float(np.nanmean(y[hi & ok])) if (hi & ok).any() else None, "non_positive": float(np.nanmean(y[lo & ok])) if (lo & ok).any() else None}
    return out


def _arm_fit(sub: pd.DataFrame, y: np.ndarray, test: str, spec: dict, *, term: str | None = None, sign: int = +1) -> dict:
    """An uncounted reading's fit (estimates only): the primary estimator on ``sub`` with the test's controls, never a verdict."""
    sub = sub.reset_index(drop=True)
    if len(sub) < 30 or (term or lt.TERM[test]) not in sub:
        return {"testable": False, "reason": "fewer than 30 units", "n": int(len(sub))}
    ctrl = lt.controls_for(test, sub)
    ok = np.ones(len(sub), bool)
    return strip(fit11(sub, np.asarray(y, float), term or lt.TERM[test], ctrl, seed=int(spec["seeds"]["estimators"][test]), minor=g_minor(sub, ok, test), n_boot=200, sign=sign)) or {}


def label_readings(r: dict, test: str, spec: dict) -> dict:
    """The readings 1.9's labels need (estimates only, count 0): CH234 M3's four bin slopes, the unknown-class arm (2.3) and the ladder arm; CH233 M1 (the
    bid's change, predicted < 0, one-sided p for < 0) and the ladder arm (11+ members); CH232 the ladder arm. Each arm uses the primary's estimator and
    controls on its own units (the census-fixed family excluded as in the primary)."""
    P, Xall = r["_frame"], r["_all"]
    out: dict = {}
    fam = ((spec.get("census_fixed") or {}).get(test) or {}).get("exclude_family")

    def nofam(d: pd.DataFrame) -> pd.DataFrame:
        return d[d["skey"].astype(str) != fam] if fam and "skey" in d else d

    if test == "CH234":
        out["bins"] = {str(i): _arm_fit(P[P["bin"] == i], P.loc[P["bin"] == i, "y"].to_numpy(float), test, spec) for i in range(4)} if "bin" in P else {}
        base = Xall[(Xall["in_scope"] == 1)]
        U = nofam(base[(base["ladder"] == 0) & ~base["vclass"].astype(str).isin(["traded", "quote_only"])])
        out["unknown_arm"] = _arm_fit(U, U["y"].to_numpy(float), test, spec)
        L = nofam(base[(base["ladder"] == 1) & (base["vclass"].astype(str) == "traded")])
        out["ladder_arm"] = _arm_fit(L, L["y"].to_numpy(float), test, spec)
    elif test == "CH233":
        out["m1"] = _arm_fit(P, P["y_m1"].to_numpy(float), test, spec, sign=-1) if "y_m1" in P else {"testable": False}
        L = nofam(Xall[Xall["arm"].astype(str) == "ladder"])
        out["ladder_arm"] = _arm_fit(L, L["y"].to_numpy(float), test, spec)
    else:
        L = Xall[(Xall["arm"].astype(str) == "out") & (Xall["in_scope"] == 1) & (Xall["ladder"] == 1) & np.isfinite(Xall["rew"].to_numpy(float))].reset_index(drop=True)
        L, _ = lt.fix_panels11(L)
        L = nofam(L[L["panel"] == 1]) if len(L) else L
        out["ladder_arm"] = _arm_fit(L, L["y"].to_numpy(float), test, spec) if len(L) else {"testable": False, "n": 0}
    return out


def underpowered(test: str, r: dict, spec: dict, k: int) -> dict:
    """1.9 *underpowered*: Inconclusive and ``(t_{G-1, 1-0.05/k} + t_{G-1, 0.8}) x SE_day`` above the census MDE (``census_fixed.<test>.mde_c``), G = the UTC
    days of the primary. Not computed (``computed`` False) while the census MDE is unfilled."""
    prim = r.get("primary") or {}
    mde = ((spec.get("census_fixed") or {}).get(test) or {}).get("mde_c")
    g, se = prim.get("n_day"), prim.get("se_day")
    if mde is None or g is None or se is None or int(g) < 2 or not math.isfinite(float(mde)):
        return {"computed": False}
    df_ = int(g) - 1
    m = (float(t_dist.ppf(1 - 0.05 / max(1, k), df_)) + float(t_dist.ppf(0.8, df_))) * float(se)
    return {"computed": True, "window_mde_c": m, "census_mde_c": float(mde), "above": bool(m > float(mde))}


def labels_for(test: str, r: dict, v: dict, spec: dict, k: int, cc: dict) -> list[str]:
    """1.9's labels (never change a verdict). Implemented: material (estimate at the census tercile gap of the tested term >= the floor; CH232 the class
    contrast), the difference label (difference p < 0.05), within-bin, re-centring not widening, side reading ambiguous, informed (X), analytic p oversized,
    underpowered, attrition-differential, late-loss, series-concentrated (top series family > 50%), ladder-dominated, holiday / month-start sensitive,
    volume-missing sensitive. Not computed (disclosed, LT11_CODE_NOTES A20): CLOB-disagreement sensitive (LT11 has no feed reader)."""
    lab = list(v.get("labels") or [])
    lab += [f"informed ({x})" for x in ((spec.get("informed_labels") or {}).get(test) or [])]
    if v["verdict"] == "Unavailable":
        return list(dict.fromkeys(lab + ([cc["label"]] if cc["label"] else [])))
    prim = r.get("primary") or {}
    beta = prim.get("beta")
    cf = (spec.get("census_fixed") or {}).get(test) or {}
    floor = spec["verdict"]["material_c"][test]
    gap = {"CH234": cf.get("xw_gap"), "CH233": cf.get("zcl_gap"), "CH232": 1.0}[test]  # CH232: xo is a 0/1 class, the estimate IS the class contrast
    if beta is not None and gap is not None and math.isfinite(float(gap)) and float(beta) * float(gap) >= floor:
        lab.append("material")
    pd_ = (r.get("point_condition") or {}).get("p_difference")
    if pd_ is not None and math.isfinite(float(pd_)) and float(pd_) < 0.05:
        lab.append(DIFF_LABEL[test])
    li = r.get("label_readings") or {}
    if test == "CH234":
        bins = li.get("bins") or {}
        if len(bins) == 4 and all(x.get("testable") and float(x["beta"]) > 0 for x in bins.values()):
            lab.append("within-bin")
        ua = li.get("unknown_arm") or {}
        if ua.get("testable") and beta is not None and (float(ua["beta"]) > float(beta) or float(ua["beta"]) * float(beta) < 0):
            lab.append("volume-missing sensitive")
    if test == "CH233":
        m1 = li.get("m1") or {}
        if m1.get("testable") and float(m1["beta"]) < 0 and float(m1["p"]) < 0.05 and v["verdict"] != "Supported":
            lab.append("re-centring not widening")
    if test == "CH232" and spec.get("m1_side_reading") not in ("cheap", "dear"):
        lab.append("side reading ambiguous")
    la = li.get("ladder_arm") or {}
    if la.get("testable") and beta is not None and float(la["beta"]) * float(beta) < 0:
        lab.append("ladder-dominated")
    if v["verdict"] == "Inconclusive" and (r.get("underpowered") or {}).get("above"):
        lab.append("underpowered")
    rd = r.get("readings") or {}
    ho = rd.get("holiday_excluded") or {}
    if ho.get("testable") and beta is not None and (ho["beta"] * beta < 0 or ((ho["p"] < 0.05) != (prim.get("p", 1) < 0.05))):
        lab.append("holiday-sensitive")
    ms = rd.get("month_start_excluded") or {}
    if ms.get("testable") and beta is not None and ms["beta"] * beta < 0:
        lab.append("month-start-sensitive")
    X = r.get("_frame")
    pm = (r.get("_prim") or {}).get("_mask")
    if X is not None and pm is not None:
        X = X[np.asarray(pm, bool)]
        if len(X) and "skey" in X:
            top = X["skey"].astype(str).value_counts(normalize=True)
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
    """The single counted trials line (``battery2.KIND_RULES['live_tests11']``, rule n_tests): k counted tests; gate draws, F, secondaries, readings, arms,
    economics, censuses and the size check count 0."""
    return {"kind": "live_tests11", "n_tests": len(ktests), "tests": ktests, "counts": "k = the Holm primaries that survived their census gates; everything else 0",
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
    for t in ktests:
        r = res[t]
        if r.get("available") and r.get("primary"):
            r["attrition"] = attrition_block(t, r, spec)
            r["readings"] = readings(r, t, spec)
            r["economics"] = economics_block(r, t, spec)
            r["label_readings"] = label_readings(r, t, spec)
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
    try:
        spec = lt.load_spec(sha=lt.SPEC_SHA256)
        res = analyze(args.out_root, spec=spec, now=now)
    except (Refused, RuntimeError) as exc:
        print(f"refusing: {exc}")
        return 2
    return write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=str))
