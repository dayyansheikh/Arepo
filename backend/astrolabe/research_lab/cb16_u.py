# ruff: noqa: E501
"""CB16-U: wake-up prints, relative large-print silence in active markets (docs/research_lab/CREATIVE_BATCH_16.md CB16-U, section 9 items 9-13, section 10). Rules part ``A`` (with ``cb16_q``).

Q and U share units and mark-outs (``cb16_q.make_fills`` / ``build_dataset``). U adds the SILENCE state of each large transaction, measured on the monitor's large-print stream (cash >= $1k) only:

* ``tau_prev`` = the venue time of the market's previous large transaction (any outcome token of the condition), ``s = tau - tau_prev``;
* the market's PRIOR GAPS are the consecutive large-transaction gaps with both ends in ``[max(tau - 7 d, 2026-10-26T00Z), tau)``; a gap that overlaps a GLOBAL MONITOR GAP (any 15-minute
  interval in which the stream holds no print in any market) is dropped; at least 5 uncensored prior gaps are needed (standardisable), else "few_gaps";
* ``x = ln(s) - ln(median of the prior gaps)``; a WAKE-UP is ``s >= max(1 h, the 90th percentile of the prior gaps)`` (frozen; no data-derived threshold);
* a genesis print (sidecar ``created_at`` less than 24 h before ``tau``) and an unverifiable creation time are excluded and counted; a silence overlapping a global monitor gap is censored;
* ``SD(x)`` is computed on SCREEN_A units and written to the SCREEN_A result file; U1-rep refuses to run without that frozen value and refuses a value computed on REP_A.

U1 is ``beta_U = -(the coefficient on x / SD(x))`` in a market fixed-effect OLS of ``M_2-4h`` (one-sided > 0, floor +0.5c per SD). U2 (Stage 2) is the within-market difference of the
CB13-T3 round-trip net on AVOIDED fills (REP_A fills ``(tau_w + 60 s, tau_w + 2 h]`` after a wake-up print) minus the market's other fills, plus the avoided-fill level; its p is the max of
the two component p's. No U path reads ``side``, a wallet field, ``alerts`` / ``scores`` / ``outcomes`` / ``wallets`` / ``stats`` or ``surprise_live`` (E011): there is no detector score, no
surprise label and no join to alert, candidate or control status.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb13_label as lab
from . import cb13_t as t13
from . import cb16_common as c16
from . import cb16_q as q

Refused = cm.Refused
NotNow = cm.NotNow

LABEL_U_A = "L2 live window (SCREEN_A, post-freeze), Stage-1 screen: large-print silence in active markets"
LABEL_U_UPPER = "maker mark-out at a mid exit: an upper bound for any maker"
LABEL_U_PROTECT = "a pass says that stepping aside avoids losses, not that a maker route exists"
LABEL_ARRIVAL = "arrival information"
LABEL_U_COMPOSITION = "composition, not silence"
LABEL_U_LARGE_ONLY = "large-print silence only; market was trading below $1k"
NOT_TESTABLE_CADENCE = q.NOT_TESTABLE_CADENCE
MIN_PRIOR_GAPS = 5
MONITOR_GAP_S = 900.0  # a global monitor gap: >= 15 minutes with no print in any market
MIN_GAP_S = 1.0  # gaps and silences are floored at one second before the log
GENESIS_MIN_AGE_S = 86400.0
WAKE_MIN_S = 3600.0
WAKE_PCT = 90.0
NIGHT_START_S = 0.0  # UTC 00:00-06:00
NIGHT_END_S = 6 * 3600.0
LONG_SILENCE_S = 12 * 3600.0  # the silences the >= 5 prior-gap rule drops (census; item 9)
MIN_UNITS_PER_MARKET = 5
U1_FLOOR = 0.5  # cents per SD of standardised log-silence
U2_PRIMARY_FLOOR = 0.5  # the within-market difference, avoided minus the market's other fills, <= -0.5c
U2_LEVEL_FLOOR = 1.0  # the avoided-fill net <= -1.0c
U2_DELAY_S = 60.0
U2_DELAY_ROBUST_S = 300.0
U2_WINDOW_S = 7200.0
GU_MIN = {"units": 1000, "markets": 100, "events": 60}
U_POWER_MDE_MAX = 1.0  # per SD
TAKER_HURDLE_C = 4.5
VALIDITY_N = 300
VALIDITY_PAGES = 6
VALIDITY_PAGE_SIZE = 500
VALIDITY_WAKE_MIN = 0.50  # below: every U line carries LABEL_U_LARGE_ONLY
VALIDITY_SILENCE_S = 3600.0
DATA_TRADES = "https://data-api.polymarket.com/trades"
S_OK = "ok"
S_NO_PREV = "no_prev"
S_FEW = "few_gaps"
S_GENESIS = "genesis"
S_GENESIS_UNKNOWN = "genesis_unknown"
S_CENSORED = "censored (monitor gap)"
SILENCE_STATUSES = (S_OK, S_NO_PREV, S_FEW, S_GENESIS, S_GENESIS_UNKNOWN, S_CENSORED)


# =====================================================================================================================================================
# The silence state
# =====================================================================================================================================================


def monitor_gaps(all_ts: np.ndarray) -> np.ndarray:
    """Global monitor gaps: ``(a, b)`` of consecutive prints in ANY market at least ``MONITOR_GAP_S`` apart (an empty 15-minute interval; 14 min 59 s is not one). The stream carries
    7,000-13,600 prints a day, so such an interval is almost surely an outage."""
    t = np.asarray(all_ts, float)
    if len(t) < 2:
        return np.zeros((0, 2))
    d = np.diff(t)
    k = np.where(d >= MONITOR_GAP_S - 1e-9)[0]
    return np.column_stack([t[k], t[k + 1]]) if len(k) else np.zeros((0, 2))


def overlaps_gap(gaps: np.ndarray, lo: float, hi: float) -> bool:
    """True iff the interval ``(lo, hi)`` intersects a global monitor gap in a set of positive length."""
    if not len(gaps):
        return False
    return bool(np.any((gaps[:, 0] < hi) & (gaps[:, 1] > lo)))


def spans_night(lo: float, hi: float) -> bool:
    """True iff ``(lo, hi)`` overlaps UTC 00:00-06:00 of any day in a set of positive length."""
    if not hi > lo:
        return False
    d0 = math.floor(lo / 86400.0)
    d1 = math.floor(hi / 86400.0)
    for d in range(int(d0), int(d1) + 1):
        a, b = d * 86400.0 + NIGHT_START_S, d * 86400.0 + NIGHT_END_S
        if lo < b and hi > a:
            return True
    return False


def _prior_gaps(times: np.ndarray, lo: float, tau: float, mgaps: np.ndarray) -> np.ndarray:
    j0 = int(np.searchsorted(times, lo, side="left"))
    j1 = int(np.searchsorted(times, tau, side="left"))
    seg = times[j0:j1]
    if len(seg) < 2:
        return np.array([])
    out = []
    for a, b in zip(seg[:-1], seg[1:], strict=True):
        if overlaps_gap(mgaps, float(a), float(b)):
            continue
        out.append(max(float(b - a), MIN_GAP_S))
    return np.array(out)


def silence_state(times: np.ndarray, mgaps: np.ndarray, tau: float, created: float, *, lookback_s: float = c16.LOOKBACK_S, floor: float | None = None) -> dict:
    """The silence state of one transaction at ``tau`` from its market's sorted transaction times (``times``, earliest print of each transaction). Pure and outcome-free."""
    floor = c16.ep(c16.LOOKBACK_FLOOR) if floor is None else floor
    out = {"s": math.nan, "tau_prev": math.nan, "n_prior": 0, "x_raw": math.nan, "wake": 0, "spans_night": 0, "silence_status": S_NO_PREV}
    i = int(np.searchsorted(times, tau, side="left"))
    if i == 0:
        return out
    tp = float(times[i - 1])
    s = max(tau - tp, MIN_GAP_S)
    out.update(s=tau - tp, tau_prev=tp, spans_night=int(spans_night(tp, tau)))
    lo = max(tau - lookback_s, floor)
    gaps = _prior_gaps(times, lo, tau, mgaps)
    out["n_prior"] = int(len(gaps))
    if len(gaps) < MIN_PRIOR_GAPS:
        out["silence_status"] = S_FEW
        return out
    out["x_raw"] = float(math.log(s) - math.log(float(np.median(gaps))))
    if not math.isfinite(created):
        out["silence_status"] = S_GENESIS_UNKNOWN
    elif created > tau - GENESIS_MIN_AGE_S + 1e-9:
        out["silence_status"] = S_GENESIS
    elif overlaps_gap(mgaps, tp, tau):
        out["silence_status"] = S_CENSORED
    else:
        out["silence_status"] = S_OK
        out["wake"] = int(s >= max(WAKE_MIN_S, float(np.percentile(gaps, WAKE_PCT))))
    return out


def add_silence(rows: list[dict], by_cid: dict[str, np.ndarray], all_ts: np.ndarray, *, created: dict[str, float] | None = None, floor: float | None = None) -> dict:
    """Attach the silence columns to EVERY transaction row (the wake-up print of a U2 avoided-fill window need not itself be a touch-consistent fill). ``x`` and ``x3`` are the units'
    values (NaN unless the silence status is ``ok``); ``x_raw`` is the standardised value whenever >= 5 prior gaps exist (the exclusion-by-x tercile table). Returns counts by status."""
    mg = monitor_gaps(all_ts)
    created = created or {}
    empty = np.array([])
    counts: Counter = Counter()
    for r in rows:
        times = by_cid.get(r["condition_id"], empty)
        cr = created.get(r["condition_id"], r.get("created_epoch", math.nan))
        st = silence_state(times, mg, r["tau"], cr if cr is not None else math.nan, floor=floor)
        st3 = silence_state(times, mg, r["tau"], cr if cr is not None else math.nan, lookback_s=c16.LOOKBACK_ROBUST_S, floor=floor)
        ok = st["silence_status"] == S_OK
        r.update(s=st["s"], tau_prev=st["tau_prev"], n_prior=st["n_prior"], x_raw=st["x_raw"], x=st["x_raw"] if ok else math.nan, wake=st["wake"], spans_night=st["spans_night"],
                 silence_status=st["silence_status"], n_prior3=st3["n_prior"], x3=st3["x_raw"] if (ok and st3["silence_status"] == S_OK) else math.nan,
                 s12_dropped=int(st["silence_status"] == S_FEW and math.isfinite(st["s"]) and st["s"] >= LONG_SILENCE_S))
        counts[st["silence_status"]] += 1
    return {"by_status": dict(counts), "global_monitor_gaps": int(len(mg))}


def attach_wake_lags(rows: list[dict], prints_tx: dict[tuple[str, float], str], lags: dict[tuple[str, str], float]) -> int:
    """U2's receipt-lag robustness (rep frame only): the wake-up transactions' ``recv_ts - ts`` (``prints_tx`` maps ``(condition_id, ts)`` to the in-memory hash, ``lags`` maps
    ``(condition_id, tx16)`` to the lag). The hash is never stored."""
    n = 0
    for r in rows:
        if r.get("wake") == 1:
            tx = prints_tx.get((r["condition_id"], r["tau"]))
            lag = lags.get((r["condition_id"], tx)) if tx else None
            r["wake_lag_s"] = float(lag) if lag is not None else math.nan
            n += int(lag is not None)
    return n


# =====================================================================================================================================================
# U units
# =====================================================================================================================================================


def u_mask_rows(rows: list[dict]) -> list[dict]:
    """Features-only U units: touch-consistent non-sports fills with ``P`` in [0.03, 0.97], a standardisable, uncensored, non-genesis silence, in markets with >= 5 such units."""
    cand = [r for r in rows if q.is_primary(r) and int(r["u_ok"]) == 1 and r["silence_status"] == S_OK and math.isfinite(r["x"])]
    cnt = Counter(r["condition_id"] for r in cand)
    return [r for r in cand if cnt[r["condition_id"]] >= MIN_UNITS_PER_MARKET]


def u_units(D: dict) -> np.ndarray:
    """Boolean mask of the U units in an analysis dataset (same rule as ``u_mask_rows``)."""
    n = len(D.get("tx_id", []))
    if not n:
        return np.zeros(0, bool)
    cand = (D["u_ok"] == 1) & (D["silence_ok"] == 1) & np.isfinite(D["x"]) & q.arm_mask(D)
    cnt = Counter(D["cid"][cand].tolist())
    return cand & np.array([cnt.get(c, 0) >= MIN_UNITS_PER_MARKET for c in D["cid"]], dtype=bool)


def sd_of(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.std(x, ddof=1)) if len(x) > 2 else math.nan


def u_gate_gu(rows: list[dict]) -> dict:
    """GU (section 2.3): >= 1,000 standardisable units in markets with >= 5 units, in >= 100 markets and >= 60 events (features only)."""
    us = u_mask_rows(rows)
    out = {"units": len(us), "markets": len({r["condition_id"] for r in us}), "events": len({r["event_id"] for r in us})}
    out["pass"] = all(out[k] >= GU_MIN[k] for k in GU_MIN)
    return out


def u_power(rows: list[dict]) -> dict:
    """GUP (feature-only): U1's estimator and ways on the pre-fill proxy; ONLY the clustered SE and the MDE per SD are returned (never a proxy point estimate)."""
    us = u_mask_rows(rows)
    if len(us) < 4:
        return {"se": math.nan, "mde": math.nan, "pass": False, "n": len(us)}
    x = np.array([r["x"] for r in us])
    sd = sd_of(x)
    out = q.power_se(us, x / sd if sd and math.isfinite(sd) else x, sign=-1.0)
    out["pass"] = bool(math.isfinite(out["mde"]) and out["mde"] <= U_POWER_MDE_MAX)
    return out


def silence_dropped_counts(rows: list[dict]) -> dict:
    """The silences of at least 12 h the >= 5 prior-gap rule drops (item 9), among non-sports touch-consistent fills and among all non-sports transactions, by silence status."""
    allr = [r for r in rows if r["label"] != lab.SPORTS and math.isfinite(r["s"]) and r["s"] >= LONG_SILENCE_S]
    fills = [r for r in allr if r["status"] == q.S_FILL]
    return {"ge_12h_all_transactions": len(allr), "ge_12h_fills": len(fills), "dropped_by_prior_gap_rule_all": sum(int(r["s12_dropped"]) for r in allr),
            "dropped_by_prior_gap_rule_fills": sum(int(r["s12_dropped"]) for r in fills), "by_status_fills": dict(Counter(r["silence_status"] for r in fills))}


def exclusion_by_x(rows: list[dict], D: dict | None = None) -> dict:
    """Round 1 item 13: among standardisable non-sports transactions (>= 5 prior gaps), the inside, inconsistent, one-sided, no-mark and censored rates by tercile of ``x_raw``."""
    base = [r for r in rows if r["label"] != lab.SPORTS and math.isfinite(r["x_raw"]) and r["silence_status"] in (S_OK, S_CENSORED, S_GENESIS, S_GENESIS_UNKNOWN)]
    if len(base) < 3:
        return {"n": len(base), "terciles": {}}
    cuts = np.percentile([r["x_raw"] for r in base], [100 / 3, 200 / 3])
    nomark: Counter = Counter()
    if D is not None and len(D.get("tx_id", [])):
        tx_to_t = {int(t): int(np.digitize(x, cuts)) for t, x in zip(D["tx_id"], D["x"], strict=True) if np.isfinite(x)}
        for t, mm in zip(D["tx_id"], D["m_2-4h"], strict=True):
            if int(t) in tx_to_t and not np.isfinite(mm):
                nomark[tx_to_t[int(t)]] += 1
    out = {}
    for k in range(3):
        sel = [r for r in base if int(np.digitize(r["x_raw"], cuts)) == k]
        c = Counter(r["status"] for r in sel)
        n = len(sel)
        row = {"n": n, "inside": c.get(t13.S_INSIDE, 0), "inconsistent": c.get(t13.S_INCONSISTENT, 0), "one_sided": c.get(t13.S_ONESIDED, 0),
               "censored": sum(1 for r in sel if r["silence_status"] == S_CENSORED), "no_mark": int(nomark.get(k, 0))}
        row["rates"] = {key: (row[key] / n if n else None) for key in ("inside", "inconsistent", "one_sided", "censored", "no_mark")}
        out[str(k)] = row
    return {"n": len(base), "cuts": [float(c) for c in cuts], "terciles": out}


# =====================================================================================================================================================
# U1
# =====================================================================================================================================================


def _g_extra(D: dict) -> dict[str, np.ndarray]:
    gm = np.where((D["grain_ok"] == 1) & (D["g"] >= 0), D["g"], 0.0)
    return {"g": gm, "g_missing": ((D["grain_ok"] != 1) | (D["g"] < 0)).astype(float)}


def u1_test(D: dict, *, n_draws: int = c16.PLACEBO_DRAWS, rep: bool = False, sd: float | None = None) -> dict:
    """U1 (within-market slope): ``beta_U = -(the coefficient on x / SD(x))`` in a market fixed-effect OLS of ``M_2-4h`` (unweighted), one-sided > 0, floor +0.5c per SD. ``SD(x)`` is the
    SCREEN_A units' value; the REP_A run (``rep=True``) REQUIRES the frozen SCREEN_A value (``sd``) and Stage 1 forbids passing one. Binding: composition placebo (primary), within-market
    calibration placebo, pre-fill placebo, attribution ("arrival information"), robustness (6-8 h, touch age <= 20 min, adverse-touch mark, SCHEDULED-EVENT class out, 3-day lookback,
    silence spanning 00:00-06:00Z out, each side, tx < $10k), top-5 of every way, leave-one-day-out p < 0.05, availability."""
    if rep and (sd is None or not math.isfinite(sd) or sd <= 0):
        raise Refused("U1-rep needs SCREEN_A's frozen SD(x) (never REP_A's own): the value is read from the SCREEN_A result file")
    if not rep and sd is not None:
        raise Refused("Stage 1 computes SD(x) on SCREEN_A; a frozen value is only for U1-rep")
    units = u_units(D)
    m = D["m_2-4h"]
    idx = np.where(units & np.isfinite(m))[0]
    av = c16.availability(len(idx), int(units.sum()))
    sd_used = sd if rep else sd_of(D["x"][units])
    base_info = {"availability": av, "sd_x": sd_used, "sd_source": "SCREEN_A frozen" if rep else "SCREEN_A units", "rep": rep}
    if not av["ok"] or not (sd_used and math.isfinite(sd_used) and sd_used > 0):
        return {**q.not_testable(c16.AVAILABILITY_LABEL), **base_info}
    xs = np.where(np.isfinite(D["x"]), D["x"] / sd_used, 0.0)
    mk = q.make_fe(m, xs, D, sign=-1.0)
    res = {**q.analyse(mk, idx, D, U1_FLOOR), **base_info}
    res["units"] = {"n": int(len(idx)), "markets": len(set(D["cid"][idx].tolist())), "events": len(set(D["event"][idx].tolist()))}
    if not res["testable"]:
        res.update(advance=False, checks_ok=False, verdict="not testable (population / clusters)")
        return res
    est = res["est"]
    res["attribution"] = q.attribution(D, idx, m, xs, est, sign=-1.0, extra=_g_extra(D), credit=LABEL_ARRIVAL, debit=LABEL_U_COMPOSITION)
    sb = np.array([q.spread_band(s) for s in D["spread"]])
    sz = np.array([q.size_band(c) for c in D["cash"]])
    strata = q.stratum_keys(D["cid"], (D["block"].astype(int) % 4), sb, sz)
    comp = q.strata_permutation_test(D, idx, m, xs, strata, est, sign=-1.0, n_draws=n_draws, seed=c16.PLACEBO_SEEDS["U1_composition"],
                                     note="U1 composition placebo (x permuted within market x UTC 6 h band of day x touch-spread band x size band; coefficient permutation test)")
    comp["informative_share_reported"] = _informative_x(xs, strata, idx)  # reported, not binding for U (the design binds it for Q only)
    res["composition_placebo"] = comp
    res["calibration_placebo"] = q.permutation_placebo(D, idx, m, xs, np.asarray(D["cid"]).astype(str), sign=-1.0, n_draws=n_draws, seed=c16.PLACEBO_SEEDS["U1_calibration"],
                                                      note="U1 within-market calibration placebo (x shuffled within market)")
    res["prefill_placebo"] = q.prefill_placebo(D, np.where(units)[0], xs, sign=-1.0)
    rob: dict[str, bool | None] = {}
    i68 = np.where(units & np.isfinite(D["m_6-8h"]))[0]
    rob["mark_6_8h"] = q.est_only(q.make_fe(D["m_6-8h"], xs, D, sign=-1.0), i68) > 0
    rob["age_le_20m"] = q.est_only(mk, idx[D["age"][idx] <= q.TIGHT_AGE_S]) > 0
    ia = np.where(units & np.isfinite(D["adv_2-4h"]))[0]
    rob["adverse_touch_mark"] = q.est_only(q.make_fe(D["adv_2-4h"], xs, D, sign=-1.0), ia) > 0
    rob["excl_scheduled_event"] = q.est_only(mk, idx[D["label"][idx] != lab.SCHEDULED]) > 0
    x3 = np.where(np.isfinite(D["x3"]), D["x3"] / (sd_of(D["x3"][units]) or 1.0), 0.0)
    i3 = idx[np.isfinite(D["x3"][idx])]
    rob["lookback_3d"] = q.est_only(q.make_fe(m, x3, D, sign=-1.0), i3) > 0
    rob["excl_silence_spans_night"] = q.est_only(mk, idx[D["spans_night"][idx] == 0]) > 0
    rob["side_maker_sells"] = q.est_only(mk, idx[D["d"][idx] == -1]) > 0
    rob["side_maker_buys"] = q.est_only(mk, idx[D["d"][idx] == 1]) > 0
    rob["tx_lt_10k"] = q.est_only(mk, idx[D["cash"][idx] < q.BIG_TX_USD]) > 0
    res["robustness"] = rob
    res["robust_ok"] = bool(all(v for v in rob.values() if v is not None) and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["small_g_rules_hold"] and comp["holds"] and res["calibration_placebo"]["holds"] and res["prefill_placebo"]["holds"] and res["robust_ok"])
    res["advance"] = c16.stage1_advance(res["p"], res["checks_ok"])
    res["labels"] = [LABEL_U_UPPER]
    res["arrival_label"] = res["attribution"]["label"]
    res["verdict"] = ("advance" if res["advance"] else "no advance") + (f"; {res['arrival_label']}" if res["advance"] else "")
    return res


def _informative_x(xs: np.ndarray, strata: np.ndarray, idx: np.ndarray) -> float:
    """Reported only: the share of U1's units in strata holding at least two distinct ``x`` values (a permutation inside a one-unit stratum moves nothing)."""
    if not len(idx):
        return math.nan
    s, v = strata[idx], xs[idx]
    multi = {k for k in set(s.tolist()) if len(set(np.round(v[s == k], 9).tolist())) > 1}
    return float(np.mean([k in multi for k in s]))


def u_reported(D: dict, rows: list[dict], sd: float | None = None) -> dict:
    """Uncounted readings (point estimates, no p-value): the wake-up indicator's within-market contrast, ``beta_U`` by LABELLER class and in the sports arm, exclusion rates by ``x``
    tercile (with the no-mark rate), the count of >= 12 h silences the prior-gap rule drops, and the taker follow at recorded prints (expected to fail the 4.5c round trip, as E007)."""
    out: dict = {}
    units = u_units(D)
    m = D["m_2-4h"]
    idx = np.where(units & np.isfinite(m))[0]
    sd_used = sd or sd_of(D["x"][units])
    xs = np.where(np.isfinite(D["x"]), D["x"] / (sd_used or 1.0), 0.0)
    wk = D["wake"].astype(float)
    out["wake_contrast"] = {"n": int(len(idx)), "est_cents": q.est_only(q.make_fe(m, wk, D, sign=-1.0), idx) if len(idx) > 3 else None,
                            "note": "market fixed-effect coefficient of the wake-up indicator, signed so that positive = worse for the maker; point estimate only"}
    out["by_class"] = {c: q.est_only(q.make_fe(m, xs, D, sign=-1.0), idx[D["label"][idx] == c]) for c in lab.CLASSES if (D["label"][idx] == c).sum() >= 8}
    cs = (D["u_ok"] == 1) & (D["silence_ok"] == 1) & np.isfinite(D["x"]) & q.arm_mask(D, sports=True)
    isp = np.where(cs & np.isfinite(m))[0]
    out["sports_arm"] = {"n": int(len(isp)), "est": q.est_only(q.make_fe(m, xs, D, sign=-1.0), isp) if len(isp) > 3 else None, "note": "uncounted"}
    out["exclusion_by_x_tercile"] = exclusion_by_x(rows, D)
    out["dropped_long_silences"] = silence_dropped_counts(rows)
    wi = idx[D["wake"][idx] == 1]
    out["taker_follow"] = {"n": int(len(wi)), "mean_follow_cents": float(np.mean(-m[wi])) if len(wi) else None, "hurdle_cents": TAKER_HURDLE_C,
                           "exceeds_hurdle": bool(len(wi) and float(np.mean(-m[wi])) > TAKER_HURDLE_C), "note": "mid-exit follow of the print's direction; expected to fail the 4.5c round trip (E007)"}
    return out


# =====================================================================================================================================================
# U2 (avoided fills)
# =====================================================================================================================================================


def wake_index(rows: list[dict]) -> dict[str, list[tuple[float, float]]]:
    """Per market the wake-up prints ``(tau_w, receipt lag)`` of any transaction row with a ``wake`` label (``ok`` silence; the print need not be a touch-consistent fill)."""
    out: dict[str, list[tuple[float, float]]] = {}
    for r in rows:
        if r.get("wake") == 1 and r["silence_status"] == S_OK and r["label"] != lab.SPORTS:
            out.setdefault(r["condition_id"], []).append((float(r["tau"]), float(r.get("wake_lag_s", math.nan))))
    for v in out.values():
        v.sort()
    return out


def avoided_mask(D: dict, wakes: dict[str, list[tuple[float, float]]], delay: Callable[[float], float] | float = U2_DELAY_S) -> np.ndarray:
    """A fill is AVOIDED iff some wake-up print ``tau_w`` of its market has ``tau_w + delay < tau <= tau_w + 2 h`` (``delay`` is 60 s; the 5 min and the receipt-lag variants are the
    robustness checks)."""
    out = np.zeros(len(D.get("tx_id", [])), bool)
    for j in range(len(out)):
        for tw, lag in wakes.get(D["cid"][j], []):
            dl = delay(lag) if callable(delay) else float(delay)
            if tw + dl < D["tau"][j] <= tw + U2_WINDOW_S:
                out[j] = True
                break
    return out


def _net(D: dict, mask: np.ndarray) -> np.ndarray:
    idx = np.where(mask)[0]
    net = np.full(len(D["tx_id"]), math.nan)
    if len(idx):
        net[idx] = t13.t3_values(D, idx)
    return net


def u2_test(D: dict, wakes: dict[str, list[tuple[float, float]]]) -> dict:
    """U2 (economic protection value; Stage 2; triggered by U1; the pooled GAI PASS is checked by the caller): PRIMARY = the within-market difference of the CB13-T3 round-trip net
    (avoided fills minus the market's other REP_A fills), one-sided < 0, floor <= -0.5c per filled share; SECOND = the avoided-fill net itself, one-sided < 0, floor <= -1.0c. U2's p is the
    MAX of the two one-sided p's. Robustness: wake-up delays of 5 min and of AREPO's receipt lag keep the sign of the primary (the draft's +0.5c exit check is dropped as vacuous). Reported:
    the protected maker's net on the remaining fills."""
    prim = q.arm_mask(D)
    net = _net(D, prim)
    ok = np.where(np.isfinite(net))[0]
    av = c16.availability(len(ok), int(prim.sum()))
    if not av["ok"]:
        return {**q.not_testable(c16.AVAILABILITY_LABEL), "availability": av, "label": LABEL_U_PROTECT}
    a = avoided_mask(D, wakes).astype(float)
    ia = ok[a[ok] == 1]
    out: dict = {"availability": av, "label": LABEL_U_PROTECT, "n_avoided": int(len(ia)), "n_other": int(len(ok) - len(ia)), "labels": [q.LABEL_RT, LABEL_U_PROTECT]}
    if len(ia) < 2 or len(ok) - len(ia) < 2:
        return {**q.not_testable("not testable (population)"), **out}
    prim_fn = q.make_fe(net, a, D, sign=-1.0)  # positive = the avoided fills are worse than the market's other fills
    r1 = q.analyse(prim_fn, ok, D, U2_PRIMARY_FLOOR)
    lvl_fn = q.make_mean(net, sign=-1.0)
    r2 = q.analyse(lvl_fn, ia, D, U2_LEVEL_FLOOR, loo=False, top5=False)
    out["primary"] = r1
    out["level"] = r2
    out["p"] = float(max(r1["p"], r2["p"]))
    out["est"] = r1["est"]
    out["n"] = int(len(ok))
    out["testable"] = bool(r1["testable"] and r2["testable"])
    if not out["testable"]:
        return {**out, "advance": False, "checks_ok": False, "verdict": "not testable (population / clusters)"}
    rob = {}
    for name, dly in (("delay_5min", U2_DELAY_ROBUST_S), ("delay_receipt_lag", lambda lag: max(float(lag), 0.0) if math.isfinite(lag) else math.inf)):
        a2 = avoided_mask(D, wakes, dly).astype(float)
        ia2 = ok[a2[ok] == 1]
        e = q.est_only(q.make_fe(net, a2, D, sign=-1.0), ok) if len(ia2) >= 2 else math.nan
        rob[name] = bool(math.isfinite(e) and e > 0)
    out["robustness"] = rob
    out["reported"] = {"protected_maker_net_on_remaining_fills": float(np.mean(net[ok][a[ok] == 0])) if (a[ok] == 0).any() else None,
                       "avoided_net": float(np.mean(net[ia])) if len(ia) else None}
    out["checks_ok"] = bool(r1["floor_ok"] and r2["floor_ok"] and r1["small_g_rules_hold"] and r2["small_g_rules_hold"] and all(rob.values()) and r1["loo_day"]["holds"] and all(r1["top5"].values()))
    out["verdict"] = "checks ok" if out["checks_ok"] else "checks fail"
    return out


# =====================================================================================================================================================
# q0389: the all-size silence validity sample (reported only; Data API)
# =====================================================================================================================================================


def validity_sample(rows: list[dict], *, seed: int = c16.SEED_U_VALIDITY, n: int = VALIDITY_N) -> dict:
    """A seeded sample of SCREEN_A U units: ``n`` with a wake-up label and ``n`` without (all if fewer). Only ids and ``tau`` are used."""
    us = sorted(u_mask_rows(rows), key=lambda r: (r["condition_id"], r["tau"]))
    rng = np.random.default_rng(seed)
    out = {}
    for name, sel in (("wake", [r for r in us if r["wake"] == 1]), ("non_wake", [r for r in us if r["wake"] == 0])):
        k = min(n, len(sel))
        pick = rng.choice(len(sel), size=k, replace=False) if k else []
        out[name] = [{"condition_id": sel[i]["condition_id"], "tau": float(sel[i]["tau"])} for i in sorted(pick)]
    return out


def parse_data_api_page(body) -> list[dict]:
    """Whitelisted fields only (``timestamp``, ``price``, ``size``, ``conditionId``); ``side``, ``proxyWallet``, names and hashes are discarded at parse."""
    out = []
    if not isinstance(body, list):
        return out
    for rec in body:
        if not isinstance(rec, dict):
            continue
        ts = c16.num(rec.get("timestamp"))
        if math.isfinite(ts):
            out.append({"timestamp": ts, "price": c16.num(rec.get("price")), "size": c16.num(rec.get("size")), "conditionId": str(rec.get("conditionId") or "")})
    return out


def all_size_silence(get_page: Callable[[int], list[dict] | None], tau: float, *, max_pages: int = VALIDITY_PAGES) -> dict:
    """Newest-first paging until a print strictly before ``tau`` is found or ``max_pages`` pages are read; prints at or after ``tau`` are never stored. ``get_page(offset)`` returns the
    parsed page, or ``None`` for a failed read (a non-200 response): that is ``failed``, never ``exhausted`` (freeze-check amendment 4)."""
    for p in range(max_pages):
        page = get_page(p * VALIDITY_PAGE_SIZE)
        if page is None:
            return {"found": False, "silence_s": math.nan, "pages": p + 1, "exhausted": False, "failed": True}
        if not page:
            return {"found": False, "silence_s": math.nan, "pages": p + 1, "exhausted": True}
        before = [r["timestamp"] for r in page if r["timestamp"] < tau]
        if before:
            return {"found": True, "silence_s": float(tau - max(before)), "pages": p + 1, "exhausted": False}
        if len(page) < VALIDITY_PAGE_SIZE:
            return {"found": False, "silence_s": math.nan, "pages": p + 1, "exhausted": True}
    return {"found": False, "silence_s": math.nan, "pages": max_pages, "exhausted": False}


def run_validity(sample: dict, lim, *, max_requests: int = 3600) -> dict:
    """The validity line: among sampled wake-ups, the share whose all-size silence is >= 1 h; among sampled non-wake-ups, the share under 1 h. ``lim`` is a ``Limiter``-like object with
    ``get(url, params) -> (status, parsed json)``. Reported only; below 50% on the first share every U line carries ``LABEL_U_LARGE_ONLY``."""
    res = {"wake": {"n": 0, "silent_ge_1h": 0, "unresolved": 0, "failed": 0, "no_earlier_print": 0}, "non_wake": {"n": 0, "silent_lt_1h": 0, "unresolved": 0, "failed": 0, "no_earlier_print": 0}}
    for name in ("wake", "non_wake"):
        for u in sample.get(name, []):
            if getattr(lim, "requests", 0) >= max_requests:
                res[name]["unresolved"] += 1
                continue

            def page(off, cid=u["condition_id"]):
                status, body = lim.get(DATA_TRADES, {"market": cid, "limit": VALIDITY_PAGE_SIZE, "offset": off})
                return parse_data_api_page(body) if status == 200 else None  # a non-200 read is a FAILED read, never "no more prints"

            r = all_size_silence(page, u["tau"])
            res[name]["n"] += 1
            if not r["found"]:
                if r.get("failed"):
                    res[name]["failed"] += 1
                elif r["exhausted"]:  # every U unit has >= 5 prior gaps in the monitor stream: no earlier print at all is inconsistent, so unresolved (never counted as silent)
                    res[name]["no_earlier_print"] += 1
                else:
                    res[name]["unresolved"] += 1
                continue
            if name == "wake":
                res[name]["silent_ge_1h"] += int(r["silence_s"] >= VALIDITY_SILENCE_S)
            else:
                res[name]["silent_lt_1h"] += int(r["silence_s"] < VALIDITY_SILENCE_S)
    w, nw = res["wake"], res["non_wake"]
    wd = w["n"] - w["unresolved"] - w["failed"] - w["no_earlier_print"]  # the share's denominator: resolved units only
    nd = nw["n"] - nw["unresolved"] - nw["failed"] - nw["no_earlier_print"]
    res["wake_share_silent_ge_1h"] = (w["silent_ge_1h"] / wd) if wd > 0 else None
    res["non_wake_share_silent_lt_1h"] = (nw["silent_lt_1h"] / nd) if nd > 0 else None
    res["label"] = LABEL_U_LARGE_ONLY if (res["wake_share_silent_ge_1h"] is not None and res["wake_share_silent_ge_1h"] < VALIDITY_WAKE_MIN) else None
    res["reported_only"] = True
    return res


# =====================================================================================================================================================
# Smoke (part A, no network) and declaration
# =====================================================================================================================================================


def smoke_silence_checks() -> dict:
    """The global monitor-gap detector and the silence standardiser on fixtures (section CB16-SM): a 15-minute empty interval censors a spanning silence, 14 min 59 s does not; 4 prior gaps
    are not standardisable, 5 are; the lookback floor bounds the prior gaps."""
    t0 = c16.ep(c16.LOOKBACK_FLOOR) + 86400.0
    base = [t0 + 60.0 * i for i in range(12)]  # one print a minute
    g15 = np.array(base + [base[-1] + 900.0, base[-1] + 960.0])
    g1459 = np.array(base + [base[-1] + 899.0, base[-1] + 960.0])
    mg15, mg1459 = monitor_gaps(g15), monitor_gaps(g1459)
    gap_ok = bool(len(mg15) == 1 and len(mg1459) == 0 and overlaps_gap(mg15, base[-1] + 100.0, base[-1] + 1000.0) and not overlaps_gap(mg1459, base[-1] + 100.0, base[-1] + 1000.0)
                  and not overlaps_gap(mg15, base[-1] - 500.0, base[-1]))
    far = t0 - 40 * 86400.0
    no_gap = np.zeros((0, 2))

    def times(n_gaps: int) -> np.ndarray:  # n_gaps prior gaps of 10 min ending 1 h before tau
        tt = [t0 + 600.0 * i for i in range(n_gaps + 1)]
        return np.array(tt)

    for_tau = lambda tt: float(tt[-1]) + 7200.0  # noqa: E731
    t4, t5 = times(4), times(5)
    s4 = silence_state(t4, no_gap, for_tau(t4), far)
    s5 = silence_state(t5, no_gap, for_tau(t5), far)
    # the lookback floor: gaps before the floor are not prior gaps
    tf = np.array([c16.ep(c16.LOOKBACK_FLOOR) - 1000.0 + 100.0 * i for i in range(30)])
    sf = silence_state(tf, no_gap, float(tf[-1]) + 600.0, far, lookback_s=7 * 86400.0)
    gen = silence_state(t5, no_gap, for_tau(t5), for_tau(t5) - GENESIS_MIN_AGE_S)  # exactly 24 h old: not a genesis print
    gen2 = silence_state(t5, no_gap, for_tau(t5), for_tau(t5) - GENESIS_MIN_AGE_S + 1.0)
    wake_hi = silence_state(t5, no_gap, float(t5[-1]) + 2 * 3600.0, far)
    wake_lo = silence_state(t5, no_gap, float(t5[-1]) + 3599.0, far)
    sc = [s4["silence_status"] == S_FEW and s4["n_prior"] == 4, s5["silence_status"] == S_OK and s5["n_prior"] == 5, math.isfinite(s5["x_raw"]), sf["n_prior"] == 19,
          gen["silence_status"] == S_OK, gen2["silence_status"] == S_GENESIS, wake_hi["wake"] == 1, wake_lo["wake"] == 0,
          spans_night(c16.ep("2026-11-02T22:00:00Z"), c16.ep("2026-11-03T01:00:00Z")), not spans_night(c16.ep("2026-11-02T07:00:00Z"), c16.ep("2026-11-02T20:00:00Z"))]
    return {"a_monitor_gap": {"pass": gap_ok, "gaps_15min": int(len(mg15)), "gaps_14m59s": int(len(mg1459))},
            "a_silence_standardiser": {"pass": bool(all(sc)), "checks": [bool(x) for x in sc]}}


def declared() -> dict:
    return {"family": "U (CH132): relative large-print silence in active markets", "stream": "the monitor's large-print stream (cash >= $1k), per condition id (any outcome token)",
            "silence": {"tau_prev": "previous large transaction at or after the lookback floor", "prior_gaps": "consecutive gaps with both ends in [max(tau - 7 d, 2026-10-26T00Z), tau)",
                        "min_prior_gaps": MIN_PRIOR_GAPS, "min_gap_s": MIN_GAP_S, "monitor_gap_s": MONITOR_GAP_S, "genesis_min_age_s": GENESIS_MIN_AGE_S,
                        "x": "ln(s) - ln(median of the prior gaps)", "sd_x": "computed on SCREEN_A units, frozen for U1-rep (a REP_A value is refused)",
                        "wake": {"rule": "s >= max(1 h, 90th percentile of the prior gaps)", "min_s": WAKE_MIN_S, "pct": WAKE_PCT}},
            "units": {"min_units_per_market": MIN_UNITS_PER_MARKET, "p_band": list(q.U_P_BAND), "sports": "out of the primary (reported arm)"},
            "u1": {"statistic": "-(coefficient on x / SD(x)) in a market fixed-effect OLS of M_2-4h", "floor_cents_per_sd": U1_FLOOR,
                   "placebos": {"composition": {"strata": "market x UTC 6 h band x spread band x size band", "rule": "within-strata permutation test: holds iff <= 3 of 200 permuted coefficients reach the observed one", "seed": c16.PLACEBO_SEEDS["U1_composition"]}, "calibration": {"seed": c16.PLACEBO_SEEDS["U1_calibration"]},
                                "prefill": "x on the pre-fill proxy must not pass p < 0.01", "draws": c16.PLACEBO_DRAWS, "max_advance": c16.PLACEBO_MAX_ADVANCE},
                   "robustness": ["6-8 h", "age <= 20 min", "adverse-touch mark", "SCHEDULED-EVENT class out", "3-day lookback", "silence spanning 00:00-06:00Z out", "each side", "tx < $10k",
                                  "top-5 of every way", "leave-one-day-out"], "attribution": {"label": LABEL_ARRIVAL, "else": LABEL_U_COMPOSITION, "covariates": "Q's plus g (missing indicator)"}},
            "gates": {"GU": GU_MIN, "GUP_mde_max_per_sd": U_POWER_MDE_MAX, "GAI": "as Q"},
            "u2": {"avoided": {"delay_s": U2_DELAY_S, "window_s": U2_WINDOW_S, "robust_delays": [U2_DELAY_ROBUST_S, "receipt lag"]},
                   "primary": {"stat": "within-market difference of the CB13-T3 net, avoided minus other fills", "floor_cents": -U2_PRIMARY_FLOOR},
                   "level": {"stat": "avoided-fill net", "floor_cents": -U2_LEVEL_FLOOR}, "p": "max of the two one-sided p's", "exit_cost_check": "none (vacuous, round 1 item 11)"},
            "validity": {"seed": c16.SEED_U_VALIDITY, "n_each": VALIDITY_N, "pages": VALIDITY_PAGES, "wake_min_share": VALIDITY_WAKE_MIN, "silence_s": VALIDITY_SILENCE_S, "reported_only": True,
                         "unresolved_rule": "a non-200 read = failed; no earlier print at all = no_earlier_print; each counted separately and never in the share or its denominator",
                         "fields": list(c16.DATA_API_FIELDS)},
            "labels": {"upper": LABEL_U_UPPER, "protect": LABEL_U_PROTECT, "arrival": LABEL_ARRIVAL, "composition": LABEL_U_COMPOSITION, "large_only": LABEL_U_LARGE_ONLY}}


def _dump(obj) -> str:
    return json.dumps(obj, default=str, sort_keys=True)


def sample_path(root: Path) -> Path:
    return Path(root) / "u_validity" / "sample.json"
