# ruff: noqa: E501
"""LT6 analysis module (docs/research_lab/LIVE_TESTS_6.md, as amended by sections 14 and 15). DRAFT: this is the SKELETON. It holds

* the estimator and the one-sided p rule (1.7): expanding-past demeaning, CR1 on event, two-way event x UTC day and UTC day,
  ``p = max(p_event on t with G_event - 1 df, p_two-way normal, p_day on t with G_day - 1 df)``; for D and B the event t uses
  ``G_treated - 1`` df (and ``G_series - 1`` if smaller where no family is excluded); the plain CR1 p is reported beside it;
* the gates (1.8): Freedman-Lane within census-fixed strata (K, D, B) and the block (circular-shift) Freedman-Lane gate (V);
* Holm over k, verdicts and labels (1.9), the counting record (1.11, kind ``live_tests6``);
* the simulated-null size check (1.8, 1.8.1): the eleven binding scenarios in table order from one generator seeded 20261167, the
  plain-CR1 and ``G_treated`` rates reported in scenarios 6, 7 and 11, and the non-binding scenario 12 and planted-effect power
  runs on their own seeds.

The loaders that read the reader's write-once ``live_tests6/`` files and the final ``analyze`` entry point come with the reader.
``analyze_frames`` runs the whole analysis on prepared per-test frames (synthetic frames in the tests). Research tooling only.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import bounce_decomp as bd
from . import live_tests3_analysis as la3
from . import live_tests5_analysis as la5
from . import live_tests5_base as b
from . import live_tests6 as lt

TESTS = ("V", "K", "D", "B")
DIRECTION = {t: +1 for t in TESTS}  # every LT6 primary is one-sided > 0 (YES terms for D; absolute moves for B)
TRIAL_KIND = "live_tests6"
GATE_LABEL = "SE check failed"
SIZE_LABEL = "SE check failed (size scenario)"
fl_perm_gate = b.fl_perm_gate
block_fl_gate = la5.block_fl_gate
strip, attach, underpowered, verdict = la3.strip, la3.attach, la3.underpowered, la3.verdict

PRIMARY = {
    "V": {"term": "zv", "y": "c_vskip", "controls": lt.CONTROLS_V, "gate": "block", "treated": None},
    "K": {"term": "CL", "y": "c_skip", "controls": lt.CONTROLS_K, "gate": "fl", "treated": None},
    "D": {"term": "LT", "y": "y22", "controls": lt.CONTROLS_D, "gate": "fl", "treated": "LT"},
    "B": {"term": "BR", "y": "a22", "controls": lt.CONTROLS_B, "gate": "fl", "treated": "BR"},
}


# --- estimator and p rule ---------------------------------------------------------------------------------------------------


def event_df(g_event: int, g_treated: int | None, g_series: int | None) -> int:
    """The df of the event t: ``G_event - 1``; for D and B ``G_treated - 1``; ``G_series - 1`` too if smaller (series family not
    excluded). Never below 0 (a df below 1 gives p = 1)."""
    c = [g_event - 1]
    if g_treated is not None:
        c.append(g_treated - 1)
    if g_series is not None:
        c.append(g_series - 1)
    return int(max(min(c), 0))


def fit6(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, sign: int = +1, treated_col: str | None = None,
         series_col: str | None = None, seed: int = 0, n_boot: int = 2000) -> dict:
    """Expanding-past demeaned OLS slope of ``term`` on ``controls`` with the LT6 inference. LT3's ``fit`` (imported) supplies the
    estimator, the CR1 clusterings and the event bootstrap; this wrapper replaces the event reference by t on ``event_df`` df
    (``G_treated - 1`` for D / B), recomputes ``p`` and widens the conservative CI with the same quantile and beta +- 1.96 SE_two-way.
    ``p_plain_cr1`` is the rule with t on ``G_event - 1`` df, reported beside it (1.7)."""
    r = la3.fit(df, y, term, controls, sign=sign, ev_t_ref=True, seed=seed, n_boot=n_boot)
    if not r.get("testable"):
        return r
    ok = r["_mask"]
    ev = df["event_id"].astype(str).to_numpy()[ok]
    g_event = int(r["n_event"])
    g_treated = int(pd.Series(ev[df[treated_col].to_numpy(float)[ok] > 0]).nunique()) if treated_col else None
    g_series = int(pd.Series(df[series_col].astype(str).to_numpy()[ok]).nunique()) if series_col else None
    dfe = event_df(g_event, g_treated, g_series)
    p_plain = max(float(r["p_event"]), float(r["p_twoway"]), float(r["p_time_t"]))
    p_event = float(t_dist.sf(sign * r["z_event"], df=dfe)) if dfe >= 1 else 1.0
    r["p_event"] = p_event
    r["p_event_ref"] = f"t on {dfe} df"
    r["p"] = max(p_event, float(r["p_twoway"]), float(r["p_time_t"]))
    r["p_plain_cr1"] = p_plain
    te = float(t_dist.ppf(0.975, dfe)) if dfe >= 1 else float("inf")
    tq = float(t_dist.ppf(0.975, int(r["t_df"]))) if r["t_df"] >= 1 else float("inf")
    boot = r.get("ci_event_boot") or [None, None]
    lo = [v for v in (boot[0], r["beta"] - te * r["se_event"], r["beta"] - tq * r["se_day"], r["beta"] - 1.96 * r["se_twoway"]) if v is not None]
    hi = [v for v in (boot[1], r["beta"] + te * r["se_event"], r["beta"] + tq * r["se_day"], r["beta"] + 1.96 * r["se_twoway"]) if v is not None]
    r["ci95_cons"] = [min(lo), max(hi)]
    r.update(event_df=dfe, g_event=g_event, g_treated=g_treated, g_series=g_series,
             p_rule="max(p_event t on event_df, p_two-way event x day, p_day t on G_day-1)")
    return r


def both_demeaned_y(df: pd.DataFrame, y: np.ndarray) -> np.ndarray:
    """The target expanding-past demeaned by market (the both-demeaned sensitivity of 1.7; reported, never changes a verdict)."""
    tmp = pd.DataFrame({"_y": np.asarray(y, float), "market_id": df["market_id"].to_numpy(), "t_row": df["t_row"].to_numpy(float)})
    return b.demean(tmp, ["_y"], "market_id", "t_row", "expanding")["_y"].to_numpy(float)


# --- gates ------------------------------------------------------------------------------------------------------------------


def strata_of(df: pd.DataFrame, stratum: str | None, t0: float | None = None) -> np.ndarray:
    """Permutation strata: ``day`` = market x UTC day; ``block2`` = market x two-day block anchored at ``t0`` (a UTC midnight: the
    registered start). ``market`` = one stratum per market (a sanity option for tests). Anything else is refused."""
    mk = df["market_id"].astype(str).to_numpy()
    if stratum == "market":
        return mk
    if stratum not in ("day", "block2"):
        raise ValueError(f"unfilled or unknown perm_stratum {stratum!r}")
    if stratum == "day" and t0 is None and "day" in df:
        return mk + "|" + df["day"].astype(str).to_numpy()
    if t0 is None:
        raise ValueError("block anchor t0 required (REGISTERED_UTC, a UTC midnight)")
    day = np.floor((df["t_row"].to_numpy(float) - t0) / lt.DAY_S).astype(int)
    key = day if stratum == "day" else day // 2
    return mk + "|" + key.astype(str)


def gate_for(test: str, df: pd.DataFrame, y: np.ndarray, spec: dict, t0: float | None = None) -> dict:
    """The census-fixed gate of the test: V the block (circular-shift) Freedman-Lane gate with at least 16 shiftable rows per market;
    K, D, B Freedman-Lane within the census-fixed strata, minimum 4. 200 draws, the test's gate seed. One-sided (sign +1)."""
    cfg, g = PRIMARY[test], spec["gates"]
    seed = spec["seeds"][f"{test}_gate"]
    if cfg["gate"] == "block":
        return block_fl_gate(df, y, cfg["term"], cfg["controls"], sign=+1, draws=g["draws"], seed=seed, min_n=g["block_min_n"])
    return fl_perm_gate(df, y, cfg["term"], cfg["controls"], sign=+1, strata=strata_of(df, spec[test.lower()]["perm_stratum"], t0), draws=g["draws"],
                        seed=seed, min_stratum=g["perm_min_stratum"])


# --- one primary ------------------------------------------------------------------------------------------------------------


def floors_status(test: str, df: pd.DataFrame, spec: dict) -> dict:
    """Floors (Unavailable below any of them, 1.9): the counts that matter per test and their floors."""
    f = spec[test.lower()]["floors"]
    days = int(df["day"].nunique()) if len(df) else 0
    ev = df["event_id"].astype(str)
    if test == "V":
        n = {"units": len(df), "events": int(ev.nunique()), "days": days}
    elif test == "K":
        n = {"clip_units": int((df["CL"] == 1).sum()), "clip_free_units": int((df["CL"] == 0).sum()), "events": int(ev.nunique()), "days": days}
    elif test == "D":
        n = {"later_units": int((df["LT"] == 1).sum()), "events": int(ev[df["LT"] == 1].nunique()), "days": days}
    else:
        n = {"birth_units": int((df["BR"] == 1).sum()), "events": int(ev[df["BR"] == 1].nunique()), "days": days}
    below = {k_: v for k_, v in n.items() if v < f[k_]}
    return {"counts": n, "floors": f, "below": below, "available": not below}


def run_primary(test: str, df: pd.DataFrame, spec: dict, *, t0: float | None = None, n_boot: int | None = None) -> dict:
    """One primary on its prepared frame (columns of ``lt.prepare_*`` plus the target and ``day``): the census-fixed family exclusion,
    floors, the fit, the gate and the both-demeaned sensitivity. The frame holds the test's analysis sample: for D / B the washout and
    the clean no-birth rule were applied when the units were built."""
    cfg = PRIMARY[test]
    fam = spec[test.lower()].get("exclude_family") or ""
    pop = df[df["skey"].astype(str) != fam].reset_index(drop=True) if fam and "skey" in df else df.reset_index(drop=True)
    fl = floors_status(test, pop, spec)
    out = {"test": test, "n_units": len(pop), "exclude_family": fam, "floors": fl, "available": fl["available"]}
    if not pop.empty and "skey" in pop:
        out["top_family_share"] = float(pop["skey"].astype(str).value_counts(normalize=True).iloc[0])
    if not fl["available"]:
        return out
    y = pop[cfg["y"]].to_numpy(float)
    kw = {"n_boot": n_boot} if n_boot is not None else {}
    series_col = "skey" if (not fam and "skey" in pop) else None
    out["primary"] = strip(fit6(pop, y, cfg["term"], cfg["controls"], treated_col=cfg["treated"], series_col=series_col, seed=spec["seeds"][test], **kw))
    out["gate"] = gate_for(test, pop, y, spec, t0)
    out["sensitivity_both_demeaned"] = strip(fit6(pop, both_demeaned_y(pop, y), cfg["term"], cfg["controls"], treated_col=cfg["treated"], series_col=series_col,
                                                  seed=spec["seeds"][test], **kw))
    return out


# --- Holm, verdicts, labels, counting ---------------------------------------------------------------------------------------


def trial_record(k: int, spec_sha: str | None, extra: dict | None = None) -> dict:
    """The one counted line of the analysis: kind ``live_tests6``, ``n_tests`` = k (the Holm primaries that survived their census
    gates). Gate draws, secondaries, mechanism readings, placebos, economics, censuses and the size check count 0 (1.11)."""
    return {"kind": TRIAL_KIND, "n_tests": int(k), "spec_sha256": spec_sha, **(extra or {})}


def is_material(test: str, res: dict, spec: dict) -> bool:
    """Label only: K and D point estimate >= 0.5c, B >= 1.0c on the absolute move, V the top-minus-bottom tercile contrast of ``zv`` >= 0.5c."""
    prim = res.get("primary") or {}
    if not prim.get("testable"):
        return False
    lab = spec["labels"]
    if test == "V":
        gap = (spec["v"].get("tercile_gap") or float("nan"))
        return bool(np.isfinite(gap) and prim["beta"] * gap * 100.0 >= lab["material_v_tercile_contrast_c"])
    ref = lab["material_b_c"] if test == "B" else lab["material_k_d_c"]
    return bool(prim["beta"] * 100.0 >= ref)


def analyze_frames(frames: dict[str, pd.DataFrame], spec: dict, *, size_check: dict | None = None, now: float | None = None, force: bool = False,
                   require_pinned: bool = True, t0: float | None = None, n_boot: int | None = None) -> dict:
    """The whole analysis on prepared per-test frames. Refuses before the analysis date (``force`` is for tests only), an unpinned
    spec when ``require_pinned``, null ``k_tests``, a test named in ``k_tests`` that LT6 does not have, and a frame missing for a
    surviving test. One Holm family over k, one-sided, alpha 0.05; a primary that is unavailable, fails its gate or is named by a
    failing size scenario enters Holm with p = 1 (k unchanged). Labels never change a verdict."""
    if not force:
        nb = spec.get("analysis_not_before")
        if nb is None:
            raise RuntimeError("live_tests6 analysis refused: analysis_not_before is null (the spec is a DRAFT)")
        if (b.now_ts() if now is None else now) < lt.epoch(nb):
            raise RuntimeError(f"live_tests6 analysis refused before {nb}")
    if require_pinned and not spec.get("_pinned"):
        raise RuntimeError("live_tests6 analysis refused: the spec is not pinned")
    ktests = spec.get("k_tests")
    if ktests is None:
        raise RuntimeError("live_tests6 analysis refused: k_tests is null")
    if any(t not in TESTS for t in ktests) or len(set(ktests)) != len(ktests):
        raise RuntimeError(f"live_tests6 k_tests may hold each of {TESTS} at most once: {ktests}")
    missing = [t for t in ktests if t not in frames]
    if missing:
        raise RuntimeError(f"live_tests6 analysis refused: no frame for {missing}")
    k = len(ktests)
    size_failed = set((size_check or {}).get("se_check_failed_size_scenario", []))
    res: dict = {t: run_primary(t, frames[t], spec, t0=t0, n_boot=n_boot) for t in ktests}
    pv = {}
    for t in ktests:
        r = res[t]
        if t in size_failed:
            pv[t] = 1.0
            continue
        pv[t] = verdict(r.get("primary") or {}, r.get("gate"), r.get("available", False), None, DIRECTION[t], GATE_LABEL)["p_for_holm"]
    hp = bd.holm(pv) if pv else {}
    lab = spec["labels"]
    for t in ktests:
        r = res[t]
        if t in size_failed:
            r["verdict"] = {"verdict": f"Inconclusive ({SIZE_LABEL})", "p_for_holm": 1.0, "labels": [SIZE_LABEL]}
            r["holm_p"] = hp[t]
            continue
        v = verdict(r.get("primary") or {}, r.get("gate"), r.get("available", False), hp[t], DIRECTION[t], GATE_LABEL)
        r["holm_p"] = hp[t]
        labels: list = []
        if is_material(t, r, spec):
            labels.append("material")
        prim = r.get("primary") or {}
        if str(v.get("verdict", "")) == "Inconclusive" and underpowered(prim, k, spec[t.lower()].get("mde_ref", 0.005)):
            labels.append("underpowered")
        if (r.get("top_family_share") or 0.0) > lab["series_concentrated_share"]:
            labels.append(f"series-concentrated ({r['top_family_share']:.0%})")
        if t == "D" and (lab.get("partially_seen_d") is not False):
            labels.append("partially seen (CB18 end_date class)")
        sc = ((size_check or {}).get("scenarios") or {})
        if any(t in s.get("binding_for", []) and (s.get("analytic_rates") or {}).get("oversized") for s in sc.values()):
            labels.append("analytic p oversized in simulation")
        r["verdict"] = attach(v, labels)
    return bd._clean({"tests": res, "holm": {"tests": ktests, "m": k, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True},
                      "trial": trial_record(k, spec.get("_sha256")), "spec_sha": spec.get("_sha256")})


# =====================================================================================================================
# Simulated-null size check (LIVE_TESTS_6.md 1.8 / 1.8.1). No effect of the tested term in any binding world.
# =====================================================================================================================


def _ar(rng: np.random.Generator, n: int, rho: float) -> np.ndarray:
    return la5._ar(rng, n, rho)


def sim_markov_ma2_world6(rng: np.random.Generator, *, n_mkt: int = 60, persistence: float = 0.6) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenarios 4-5 (K): LT5 scenario 4's world (60 markets, ``n_m`` uniform on 6..60, events of three) with label rate
    ``p_m ~ U(0.05, 0.3)`` (clips rarer than jumps): the label keeps its previous value with probability ``persistence`` else is
    redrawn Bernoulli(``p_m``); pass shocks ``u ~ N(0, 0.03)``; ``y_i = level + u_{i+1} + u_{i+2} + 0.5 u_{i+3}``; ``c1 ~ N(0, 1)``, no effect."""
    rows = []
    for m in range(n_mkt):
        n = int(rng.integers(6, 61))
        pr, lvl = rng.uniform(0.05, 0.3), rng.normal(0, 0.01)
        u = rng.normal(0, 0.03, n + 3)
        lab = int(rng.random() < pr)
        for i in range(n):
            lab = lab if rng.random() < persistence else int(rng.random() < pr)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "P": lab, "c1": rng.normal(),
                         "y": lvl + u[i + 1] + u[i + 2] + 0.5 * u[i + 3]})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def sim_event_label_world(rng: np.random.Generator, *, label_p: float = 0.004, absolute: bool = False, effect: float = 0.0, level_edits: bool = False,
                          n_mkt: int = 240, ev_size: int = 4) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenarios 6 (D) and 7 (B), 12 and the power runs. ``n_mkt`` markets in events of ``ev_size``; ``n_m`` uniform on 24..120 units at
    2 h spacing (``t_row = 7200 i``, ``day = i // 12``). Per event and unit an edit (listing) occurs with probability ``label_p`` and
    labels EVERY market of the event at that unit. Pass shocks: market ``u ~ N(0, 0.0173)``, event ``w ~ N(0, 0.01)`` (shared by the
    event's markets); ``y_i = level + sum_{j=2..12} (u_{i+j} + w_{e,i+j})`` (the 22 h skip target; MA(10) in unit steps), or its
    absolute value (``absolute``, scenario 7). Control ``c1 = 0.5 zL + sqrt(0.75) xi`` (``zL`` the standardised label) with a real
    effect 0.02 on the target. ``effect`` plants a label effect (power runs only). ``level_edits`` (scenario 12): the label is a
    per-market Bernoulli with probability ``min(label_p exp(25 level_m), 0.5)`` instead of the event-level edit."""
    n_ev = n_mkt // ev_size
    n_m = rng.integers(24, 121, n_mkt)
    level = rng.normal(0, 0.01, n_mkt)
    T = int(n_m.max()) + 13
    u = rng.normal(0, 0.0173, (n_mkt, T))
    w = rng.normal(0, 0.01, (n_ev, T))
    edits = rng.random((n_ev, int(n_m.max()))) < label_p
    recs = []
    for m in range(n_mkt):
        e = m // ev_size
        inc = u[m] + w[e]
        P = np.concatenate([[0.0], np.cumsum(inc)])
        S = P[np.arange(int(n_m[m])) + 13] - P[np.arange(int(n_m[m])) + 2]  # sum_{j=2..12} inc_{i+j}
        n = int(n_m[m])
        if level_edits:
            p_m = min(label_p * math.exp(25.0 * level[m]), 0.5)
            lab = (rng.random(n) < p_m).astype(float)
        else:
            lab = edits[e, :n].astype(float)
        recs.append(pd.DataFrame({"market_id": f"m{m}", "event_id": f"e{e}", "t_row": np.arange(n) * 7200.0, "day": (np.arange(n) // 12).astype(str), "L": lab,
                                  "S": np.abs(S) if absolute else S, "level": level[m]}))
    df = pd.concat(recs, ignore_index=True)
    sd = float(df["L"].std())
    zl = (df["L"] - df["L"].mean()) / sd if sd > 0 else df["L"] * 0.0
    df["c1"] = 0.5 * zl + math.sqrt(0.75) * rng.normal(size=len(df))
    df["y"] = df["level"] + df["S"] + 0.02 * df["c1"] + effect * df["L"]
    return df.drop(columns=["S", "level"]), df["y"].to_numpy(float)


def sim_stochvol_world(rng: np.random.Generator, *, n_mkt: int = 240, ev_size: int = 4) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenario 11 (B; R1 item 2): stochastic volatility, a listing hazard rising with current volatility, the primary's prior-|move|
    controls, an absolute target and NO listing effect. Per market log-volatility ``s_t`` AR(1) rho 0.95, stationary SD 0.5, half its
    variance shared with the event (``s = 0.5 (sqrt(1/2) own + sqrt(1/2) ev)``); market pass shocks ``u_t = 0.0173 exp(s_t - 0.25) e_t``
    and event shocks ``w_t = 0.01 exp(S_e,t - 0.25) e'_t`` (``S_e = 0.5 ev``): with ``Var = 0.25`` the ``- 0.25`` keeps the MEAN
    VARIANCE at its base (the R1 re-check). Listing hazard per event and unit ``min(0.006 exp(sbar_{e,t}), 0.05)`` (``sbar`` the event's
    mean ``s_t``) labels every market of the event. The mid path is the cumulative sum of ``u + w``; the controls are the unit's own
    ``|2 h|``, ``|6 h|``, ``|24 h|`` moves and the event's leave-one-out mean ``|2 h|`` move; the target is
    ``|sum_{j=2..12} (u_{i+j} + w_{e,i+j})|``. Each market has 12 pre-history passes so every control is defined."""
    n_ev = n_mkt // ev_size
    n_m = rng.integers(24, 121, n_mkt)
    nmax = int(n_m.max())
    T = nmax + 12 + 13
    ev_ar = np.stack([_ar(rng, T, 0.95) for _ in range(n_ev)])
    own = np.stack([_ar(rng, T, 0.95) for _ in range(n_mkt)])
    ev_of = np.arange(n_mkt) // ev_size
    s = 0.5 * (math.sqrt(0.5) * own + math.sqrt(0.5) * ev_ar[ev_of])
    S_e = 0.5 * ev_ar
    level = rng.normal(0, 0.01, n_mkt)
    u = 0.0173 * np.exp(s - 0.25) * rng.normal(size=(n_mkt, T))
    w = 0.01 * np.exp(S_e - 0.25) * rng.normal(size=(n_ev, T))
    inc = u + w[ev_of]
    sbar = np.stack([s[ev_of == e].mean(axis=0) for e in range(n_ev)])
    haz = np.minimum(0.006 * np.exp(sbar), 0.05)
    lab_ev = rng.random((n_ev, nmax)) < haz[:, 12:12 + nmax]
    cum = np.concatenate([np.zeros((n_mkt, 1)), np.cumsum(inc, axis=1)], axis=1)
    recs = []
    for m in range(n_mkt):
        n, e = int(n_m[m]), int(ev_of[m])
        i = np.arange(n)
        tau = i + 12
        mid_tau = cum[m, tau + 1]  # the mid path after pass tau
        a1, a6, a24 = np.abs(mid_tau - cum[m, tau]), np.abs(mid_tau - cum[m, tau - 2]), np.abs(mid_tau - cum[m, tau - 11])
        S = cum[m, tau + 13] - cum[m, tau + 2]
        recs.append(pd.DataFrame({"market_id": f"m{m}", "event_id": f"e{e}", "t_row": i * 7200.0, "day": (i // 12).astype(str), "L": lab_ev[e, :n].astype(float),
                                  "a1": a1, "a6": a6, "a24": a24, "i": i, "y": level[m] + np.abs(S)}))
    df = pd.concat(recs, ignore_index=True)
    g = df.groupby(["event_id", "i"])["a1"]
    cnt, tot = g.transform("size"), g.transform("sum")
    df["loo_a1"] = np.where(cnt > 1, (tot - df["a1"]) / (cnt - 1).clip(lower=1), np.nan)
    return df.drop(columns=["i"]), df["y"].to_numpy(float)


def sim_v_world(rng: np.random.Generator, *, rho: float, n_mkt: int = 80) -> tuple[pd.DataFrame, np.ndarray]:
    """Scenarios 8-10 (V): ``n_m`` uniform on 6..60 (18% below 16), events of three; state ``z`` = market level ``N(0, 0.5)`` + AR(1)
    ``rho`` (stationary SD 1); control ``c1 = 0.5 z + sqrt(0.75) xi``, ``xi`` AR(1) with the same ``rho``, real effect 0.02; target
    ``y_i = level + 0.02 c1_i + u_{i+1} + u_{i+2} + 0.5 u_{i+3}``, ``u ~ N(0, 0.03)`` (MA(2)); no effect of ``z``."""
    rows = []
    for m in range(n_mkt):
        n = int(rng.integers(6, 61))
        lvl, zl = rng.normal(0, 0.01), rng.normal(0, 0.5)
        z = zl + _ar(rng, n, rho)
        xi = _ar(rng, n, rho)
        u = rng.normal(0, 0.03, n + 3)
        for i in range(n):
            c1 = 0.5 * z[i] + math.sqrt(0.75) * xi[i]
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "z": z[i], "c1": c1,
                         "y": lvl + 0.02 * c1 + u[i + 1] + u[i + 2] + 0.5 * u[i + 3]})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def _strata_day(df: pd.DataFrame) -> np.ndarray:
    return (df["market_id"].astype(str) + "|" + df["day"].astype(str)).to_numpy()


def analytic_rates(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], rates: dict) -> None:
    """Add this world's analytic-rule rejections to ``rates``: the p rule of 1.7 with t on ``G_treated - 1`` df and the plain CR1 rule
    (t on ``G_event - 1``), at nominal 0.0125 and 0.05, one-sided. Draws nothing from any generator (a fixed bootstrap seed, two
    draws: the CI is not used), so it cannot perturb the binding worlds."""
    r = fit6(df, y, term, controls, treated_col=term, seed=0, n_boot=2)
    for key, p in (("treated", r.get("p", 1.0)), ("plain", r.get("p_plain_cr1", 1.0))):
        for nom in (0.0125, 0.05):
            rates[f"{key}_{nom}"] = rates.get(f"{key}_{nom}", 0) + int(bool(r.get("testable")) and p < nom)


NOMINALS = (0.0125, 0.05)


def scenario_table(rng: np.random.Generator, draws: int, rates: dict) -> dict:
    """The eleven binding scenarios of LIVE_TESTS_6.md 1.8 in table order: name -> callable returning whether the gate passes in one
    world (the world and the gate seed come from ``rng`` in that order). Scenarios 6, 7 and 11 also add the analytic rule's rejections
    to ``rates[name]`` (reported, never binding)."""

    def fl(df, y, term, ctrl, strata) -> bool:
        return bool(fl_perm_gate(df, y, term, ctrl, sign=+1, strata=strata, draws=draws, seed=int(rng.integers(1 << 31)), min_stratum=4).get("passes"))

    def blk(df, y) -> bool:
        return bool(block_fl_gate(df, y, "z", ["c1"], sign=+1, draws=draws, seed=int(rng.integers(1 << 31)), min_n=16).get("passes"))

    def move(**kw):
        df, y = b.sim_move_world(rng, **kw)
        return fl(df, y, "P", ["c1"], _strata_day(df))

    def corr():
        df, y = b.sim_corr_label_world(rng, corr=0.7, binary=True)
        return fl(df, y, "L", ["c1"], _strata_day(df))

    def mk(p):
        df, y = sim_markov_ma2_world6(rng, persistence=p)
        return fl(df, y, "P", ["c1"], _strata_day(df))

    def ev(name, label_p, absolute):
        df, y = sim_event_label_world(rng, label_p=label_p, absolute=absolute)
        analytic_rates(df, y, "L", ["c1"], rates.setdefault(name, {}))
        return fl(df, y, "L", ["c1"], _strata_day(df))

    def sv(name):
        df, y = sim_stochvol_world(rng)
        analytic_rates(df, y, "L", ["a1", "a6", "a24", "loo_a1"], rates.setdefault(name, {}))
        return fl(df, y, "L", ["a1", "a6", "a24", "loo_a1"], _strata_day(df))

    def v(rho):
        df, y = sim_v_world(rng, rho=rho)
        return blk(df, y)

    return {"s01_fl_binary_iid": lambda: move(), "s02_fl_binary_persistent": lambda: move(persistent=True), "s03_fl_binary_control_corr0.7": corr,
            "s04_fl_markov0.6_ma2": lambda: mk(0.6), "s05_fl_markov0.9_ma2": lambda: mk(0.9),
            "s06_fl_d_event_label_ma10": lambda: ev("s06_fl_d_event_label_ma10", 0.004, False), "s07_fl_b_abs_target": lambda: ev("s07_fl_b_abs_target", 0.006, True),
            "s08_block_v_rho0": lambda: v(0.0), "s09_block_v_rho0.6": lambda: v(0.6), "s10_block_v_rho0.9": lambda: v(0.9),
            "s11_fl_b_stochvol": lambda: sv("s11_fl_b_stochvol")}


def nonbinding_runs(spec: dict, draws: int, worlds: int | None = None, only: list[str] | None = None) -> dict:
    """The non-binding runs of 1.8, each on its OWN generator derived from 20261167 (scenario 12 seed 2026116712; the power runs
    2026116721-24), so they cannot perturb the binding worlds. Scenario 12 reports the gate's rate for the raw-target and the
    both-demeaned estimators; the power runs plant a later / birth effect of 0.5c and 1.0c and report the gate's and the analytic rule's
    power. Information only; they drop nothing."""
    nb = spec["size_check"]["nonbinding"]
    out: dict = {}

    def gate_both(df, y, rng):
        seed = int(rng.integers(1 << 31))
        a = fl_perm_gate(df, y, "L", ["c1"], sign=+1, strata=_strata_day(df), draws=draws, seed=seed, min_stratum=4)
        yd = both_demeaned_y(df, y)
        c = fl_perm_gate(df, yd, "L", ["c1"], sign=+1, strata=_strata_day(df), draws=draws, seed=seed, min_stratum=4)
        return bool(a.get("passes")), bool(c.get("passes"))

    s12 = nb["s12_label_correlated_with_level"]
    if only is None or "s12" in only:
        rng = np.random.default_rng(s12["seed"])
        n_w = worlds or spec["size_check"]["worlds"]
        raw = dem = 0
        for _ in range(n_w):
            df, y = sim_event_label_world(rng, level_edits=True)
            a, c = gate_both(df, y, rng)
            raw, dem = raw + int(a), dem + int(c)
        out["s12_label_correlated_with_level"] = {"worlds": n_w, "rate_raw_target": raw / n_w, "rate_both_demeaned": dem / n_w, "seed": s12["seed"], "binding": False}
    for key, absolute, label_p in (("power_d_0.5c", False, 0.004), ("power_d_1.0c", False, 0.004), ("power_b_0.5c", True, 0.006), ("power_b_1.0c", True, 0.006)):
        if only is not None and key not in only:
            continue
        cfg = nb[key]
        rng = np.random.default_rng(cfg["seed"])
        n_w = worlds or cfg["worlds"]
        gp, ap = 0, {}
        for _ in range(n_w):
            df, y = sim_event_label_world(rng, label_p=label_p, absolute=absolute, effect=cfg["effect"])
            gp += int(bool(fl_perm_gate(df, y, "L", ["c1"], sign=+1, strata=_strata_day(df), draws=draws, seed=int(rng.integers(1 << 31)), min_stratum=4).get("passes")))
            analytic_rates(df, y, "L", ["c1"], ap)
        out[key] = {"worlds": n_w, "effect": cfg["effect"], "gate_power": gp / n_w, "analytic_power_treated_0.05": ap.get("treated_0.05", 0) / n_w,
                    "analytic_power_plain_0.05": ap.get("plain_0.05", 0) / n_w, "seed": cfg["seed"], "binding": False}
    return out


def size_check(*, worlds: int, draws: int, seed: int, nominal: float = 0.05, binding: dict | None = None, only: list[str] | None = None,
               spec_sha256: str | None = None, dev: bool = False, include_nonbinding: bool = False, spec: dict | None = None) -> dict:
    """Pass rate of each gate under its simulated nulls; limit ``nominal + 1.645 sqrt(nominal (1 - nominal) / worlds)``. The eleven
    scenarios run in table order on ONE generator seeded ``seed`` (20261167). ``binding`` maps scenario -> tests (spec
    ``size_check.scenarios``): a failing scenario sets only its tests to "SE check failed (size scenario)" (p = 1, k unchanged;
    1.8). In scenarios 6, 7 and 11 the plain-CR1 and ``G_treated - 1`` analytic rates at 0.0125 and 0.05 are reported against their
    limits (0.0166, 0.058) and label the test *analytic p oversized in simulation* (never a verdict change). Fails closed if the
    binding map and the table disagree. ``only`` runs a subset and is never the registered statement."""
    spec = spec or lt.load_spec(sha=None)
    binding = binding or spec["size_check"]["scenarios"]
    rng = np.random.default_rng(seed)
    rates: dict = {}
    table = scenario_table(rng, draws, rates)
    missing = [n for n in table if n not in binding or not binding[n]]
    extra = [n for n in binding if n not in table]
    if missing or extra:
        raise ValueError(f"size-check binding map mismatch: missing {missing}, unknown {extra}")
    lim = nominal + 1.645 * float(np.sqrt(nominal * (1 - nominal) / worlds))
    lim_a = {0.0125: 0.0125 + 1.645 * math.sqrt(0.0125 * 0.9875 / worlds), 0.05: lim}
    out: dict = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": {}, "spec_sha256": spec_sha256, "dev": bool(dev or only is not None)}
    for name, fn in table.items():
        if only is not None and name not in only:
            continue
        rej = sum(int(fn()) for _ in range(worlds))
        row = {"rate": rej / worlds, "ok": rej / worlds <= lim, "binding_for": binding[name]}
        if name in rates:
            rr = rates[name]
            ana = {f"{kind}_{nom}": rr.get(f"{kind}_{nom}", 0) / worlds for kind in ("treated", "plain") for nom in NOMINALS}
            ana["limits"] = {str(n_): v for n_, v in lim_a.items()}
            ana["oversized"] = any(ana[f"treated_{n_}"] > lim_a[n_] for n_ in NOMINALS)
            ana["plain_oversized"] = any(ana[f"plain_{n_}"] > lim_a[n_] for n_ in NOMINALS)
            row["analytic_rates"] = ana
        out["scenarios"][name] = row
    failed = sorted({t for v in out["scenarios"].values() if not v["ok"] for t in v["binding_for"]})
    out["se_check_failed_size_scenario"] = failed
    out["all_ok"] = not failed
    out["code_sha256"] = lt.code_hashes()
    if include_nonbinding:
        out["nonbinding"] = nonbinding_runs(spec, draws)
    return out
