# ruff: noqa: E501
"""CB1 history tests: CB1-A (CH01), CB1-C (CH17), CB1-E (CH22). EXPLORATORY_HISTORICAL.

Implements, exactly as declared in ``docs/research_lab/CREATIVE_BATCH_1.md`` (sections 0-2, CB1-A, CB1-C, CB1-E,
challenger round 1 and the response), the history screens on ``h2_main`` and the frozen-definition replication on
``h5_cb1``. Nothing here is prospective, an edge claim or a profitability claim: every P&L is a paper rule at modelled
or recorded prices and AREPO never trades.

Design notes
------------
* Origin selection (``select_*``) never reads an outcome column. Outcomes are attached afterwards
  (``attach_outcome``). A census guard (:func:`drop_outcome_columns`) removes ``outcome_prices`` / ``uma_status``
  before any population code runs in census mode.
* Trade truncation (section 2.2): a trade condition over a window that starts before ``trades_oldest_ts`` of a truncated
  market is True if the stored trades already satisfy it, else *unavailable* (never 0). An unavailable earlier candidate
  excludes the market ("first qualifying origin" rules).
* Rare-event inference (section 2.3): break-even placebo ``Y ~ Bern(a + f)``, one-sided cluster-aware tail gate
  (Wilson on ``n / deff`` or exact Clopper-Pearson on event-level losses), >= 10 losing event clusters for the z-test.
* Reuses ``battery.mean_test`` / ``battery.beta_test`` (event and two-way CR1 clustering, event bootstrap),
  ``economics.taker_fee`` and the docs fee table, ``history_backfill`` readers and the as-of price rule.
* Interpretation choices where the document is silent are listed in ``INTERPRETATIONS`` and written into every
  results file.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta as beta_dist
from scipy.stats import norm

from . import battery as B
from . import economics, h5_seal, provenance
from . import history_backfill as hb

VERSION = "cb1-history-v1"
REVISION = "cb1_history"
REVISION_R = "cb1_history_replication"
EVIDENCE_ROLE = "exploratory_historical"
TRIAL_KIND = "cb1_history"
TRIAL_KIND_R = "cb1_history_replication"
TRIAL_KIND_D = "cb1_history_descriptive"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb1_history_v1.json"
SEAL_COPY = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "h5_cb1_SEAL.json"
FORBIDDEN_RUNS = ("h3_power", "h4_seal", "h1_first")
OUTCOME_COLUMNS = ("outcome_prices", "uma_status")

DAY = 86400.0
H = 3600.0
GRID_2H = 7200.0
GRID_6H = 21600.0
SEED = B.SEED  # 116
N_BOOT = 2000
MAX_AGE = float(hb.MAX_QUOTE_AGE_S)  # 2h

# --- declared dates / windows (section 1.2) -------------------------------------------------------------------------
HOLD_BUFFER_D = 60.0  # origins t <= T_censor - 60d
LIFE_MAX_D = 100.0  # A2 / E scheduled life
END_FORWARD_D = 400.0  # end_at <= T_fetch + 400d
LOOKBACK_D = 450.0  # CB1-F completeness rule: created_at >= T_fetch - 450d (h5; other runs use their manifest lookback_days)
A1_WINDOW_S = DAY
A2_PRE_END_S = DAY
A2_TRADE_LOOKBACK_S = 7 * DAY
E_ORIGIN_S = 24 * H
E_SECONDARY_S = (6 * H, 12 * H)
E_MIN_TRADES = 3
E_DRIFT_S = 7 * DAY
BAND_A = (0.95, 0.99)
BAND_E = (0.05, 0.80)
BAND_C = (0.02, 0.10)
C_ORDER_SHARES = 5.0
C_LIFE_S = 6 * H
C_LOOKBACK_S = 7 * DAY
C_DRIFT_S = DAY

# --- cost conventions (section 2.1) ---------------------------------------------------------------------------------
# half-spread by the price band of the side bought (2026-10-11 sweep)
HALF_SPREAD = ((0.05, 0.0205), (0.20, 0.0150), (0.80, 0.0110), (0.95, 0.0150), (1.0000001, 0.0125))
GENESIS_H_MIN = 0.025
ASK_CAP = 0.999
COST_SENS = 0.0075  # binding: +0.75c
COST_SENS_1C = 0.01  # reported only
CENSOR_ZERO_ONE = (0.0, 1.0)

# --- statistical rules (sections 2.3 - 2.8) --------------------------------------------------------------------------
MIN_UNITS = 100
MIN_CLUSTERS = 30
MIN_LOSING_CLUSTERS = 10
ALPHA_STAGE1 = 0.01
ALPHA_STAGE2 = 0.05
RANN_FLOOR = 0.10
PLACEBO_DRAWS = 200
PLACEBO_MAX_RATE = 0.015
TOP_EVENTS_DROPPED = 5
KILL_MIN_MARKETS = 100
PX1_Z = {1: 2.33, 2: 1.645}

# --- E3 sensational rule (frozen; challenger item 12) ----------------------------------------------------------------
NAME_RE = r"(?<=[a-z0-9,;:'\"\)]\s)[A-Z][a-zA-Z'\.\-]+(?:\s(?:[A-Z][a-zA-Z'\.\-]+))+"  # flags: none
VERB_RE = r"\b(arrest\w*|indict\w*|resign\w*|impeach\w*|invade[sd]?|invasion|attack\w*|strike[sd]?|assassinat\w*|convict\w*|jail\w*|prison\w*|fired|removed|ousted|coup|martial law|nuclear|war|collapse[sd]?|default\w*|crash\w*|hack\w*|sanction\w*|ban|bans|banned|die|dies|died|death|killed|out as)\b"  # flags: re.IGNORECASE
VERB_FLAGS = "re.IGNORECASE"
NAME_FLAGS = "none"


def sensational(q: str) -> bool:
    """Frozen E3 text rule, applied to the question text only (both patterns required)."""
    q = q if isinstance(q, str) else ""
    return bool(re.search(NAME_RE, q)) and bool(re.search(VERB_RE, q, re.IGNORECASE))


def e3_text_rule_sha256() -> str:
    blob = json.dumps(
        {"name_re": NAME_RE, "name_flags": NAME_FLAGS, "verb_re": VERB_RE, "verb_flags": VERB_FLAGS}, sort_keys=True
    ).encode()
    return hashlib.sha256(blob).hexdigest()


# --- declared hypotheses (sections 2.5, CB1-A, CB1-C, CB1-E) ----------------------------------------------------------
# floor_net: floor on the point estimate in price units (cents / 100); direction: sign tested one-sided.
HYPOTHESES_CB1: dict[str, dict] = {
    "A1": dict(
        family="A", kind="economic", direction=1, floor_net=0.0030, rann_floor=RANN_FLOOR, tail="A", tail_floor=0.003,
        placebo=True,
        population="fee_category != sports; first qualifying 2h UTC origin per market with end_at <= t < end_at + 24h; "
        "open at t; 0.95 <= p_s <= 0.99; >= 1 trade before end_at; >= 1 trade in [end_at, t); "
        "t <= T_censor - 60d; truncation: unavailable condition at the selected or any earlier candidate excludes the market",
        hold="to resolution (censored at T_censor)", statistic="mean net = Y_s - a - f(a) per share, unweighted",
    ),
    "A2": dict(
        family="A", kind="economic", direction=1, floor_net=0.0030, rann_floor=RANN_FLOOR, tail="A", tail_floor=0.003,
        placebo=True,
        population="scheduled life end_at - created_at <= 100d; end_at <= T_fetch + 400d; first qualifying 2h UTC origin "
        "per market with t < end_at - 24h; open at t; 0.95 <= p_s <= 0.99; >= 1 trade in [t - 7d, t); "
        "t <= T_censor - 60d; same truncation rule",
        hold="to resolution (censored at T_censor)", statistic="mean net = Y_s - a - f(a) per share, unweighted",
    ),
    "C1": dict(
        family="C", kind="economic", direction=1, floor_net=0.0050, rann_floor=RANN_FLOOR, tail="C", tail_floor=0.005,
        placebo=True,
        population="filled queue-rule orders, fee_category != sports: 6h pmxt two-sided books; longshot mid in [0.02, 0.10]; "
        ">= 1 trade in [t - 7d, t); t <= T_censor - 60d; 5-share ask at the best ask, life [t, t + 6h); fill when cumulative "
        "taker volume buying the longshot at >= a_c reaches Q0 + 5 (all-or-nothing); untruncated trades over the life required",
        hold="from fill to resolution (censored)", statistic="mean net = a_c - Y_c per filled share, maker fee 0, unweighted",
    ),
    "C2": dict(
        family="C", kind="economic", direction=1, floor_net=0.0050, rann_floor=RANN_FLOOR, tail="C", tail_floor=0.005,
        placebo=True,
        population="as C1 with fee_category == sports",
        hold="from fill to resolution (censored)", statistic="mean net = a_c - Y_c per filled share, maker fee 0, unweighted",
    ),
    "E1": dict(
        family="E", kind="economic", direction=1, floor_net=0.0100, rann_floor=RANN_FLOOR, tail=None, tail_floor=None,
        placebo=True,
        population="outcomes == [Yes, No]; fee_category != sports; end_at - created_at <= 100d; end_at <= T_fetch + 400d; "
        ">= 3 trades in [created_at, t); origin t = created_at + 24h; YES price in [0.05, 0.80]; open at t; "
        "t <= T_censor - 60d; one unit per market; NO bought at min((1-p_Y)+max(h,2.5c), 0.999)",
        hold="to resolution (censored)", statistic="mean net per NO share, unweighted",
    ),
    "E2": dict(
        family="E", kind="mechanism", direction=-1, floor_net=-0.0050, rann_floor=None, tail=None, tail_floor=None,
        placebo=False,
        population="as E1", hold="7 days", statistic="mean 7-day YES drift p_Y(t+7d) - p_Y(t) (payout if closed earlier), unweighted",
    ),
    "E3": dict(
        family="E", kind="economic", direction=1, floor_net=0.0100, rann_floor=RANN_FLOOR, tail=None, tail_floor=None,
        placebo=True,
        population="E1 population intersected with sensational(question) (frozen NAME_RE and VERB_RE)",
        hold="to resolution (censored)", statistic="mean net per NO share, unweighted",
    ),
}
FAMILY_TESTS = {"A": ("A1", "A2"), "C": ("C1", "C2"), "E": ("E1", "E2", "E3")}

INTERPRETATIONS = [
    "Rare-loss carries with < 10 losing event clusters: the z-test is not used; the exact event-level tail bound decides "
    "the p-condition, and the floors (point estimate, R_ann) and binding robustness still apply.",
    "Break-even placebo reruns the Stage-1 gate (p, floors, R_ann, tail gate) per draw; robustness checks are not rerun.",
    "Top-5-event robustness removes the 5 events with the largest absolute summed contribution and re-applies the p-condition and floor.",
    "Candidate origins for first-origin rules are those satisfying all non-trade conditions; an unavailable trade condition "
    "at such a candidate (before any available-True one) excludes the market.",
    "C post-fill drift: filled orders use m_c(t_fill + 24h) - m_c(t); unfilled orders use the end of the order life (t + 6h) as pseudo fill time.",
    "Local Holm in replicate runs covers the tests of that run only and is reported as replicated_provisional_per_run; the binding "
    "verdict is the CB1 batch Holm over all Stage-2 tests (`run_cb1_history.py batch-holm`).",
    "Completeness rule (CB1-F): A1, A2 and E use only markets with created_at >= T_fetch - lookback (450d for h5; the manifest "
    "lookback_days for other runs); markets outside (or with no created_at) are not units and are counted in lookback_excluded.",
    "Censored units are excluded from the denominator of the tail share pi; a censored-as-loser bound is reported, not binding.",
    "Units with no as-of price at any candidate origin are dropped and counted by outcome status in no_asof_price_by_status.",
    "End-at sensitivity drops markets whose closed_time is more than 30 days after end_at.",
]


H2_COMPLETENESS_RULE = (
    "Non-h5 runs (h2_main) apply the completeness rule with the run manifest's lookback_days; make_ctx refuses when the "
    "manifest has no lookback_days (no fallback to 450). h5 runs use the declared 450 days.")


def declaration_table() -> list[dict]:
    out = []
    for hid, h in HYPOTHESES_CB1.items():
        out.append({"id": hid, **{k: h[k] for k in sorted(h)}})
    return out


def declaration_blob() -> dict:
    return {
        "version": VERSION,
        "hyps": declaration_table(),
        "dates": {"hold_buffer_d": HOLD_BUFFER_D, "life_max_d": LIFE_MAX_D, "end_forward_d": END_FORWARD_D, "lookback_d": LOOKBACK_D},
        "windows": {
            "a1_window_s": A1_WINDOW_S, "a2_pre_end_s": A2_PRE_END_S, "a2_lookback_s": A2_TRADE_LOOKBACK_S,
            "e_origin_s": E_ORIGIN_S, "e_secondary_s": list(E_SECONDARY_S), "e_min_trades": E_MIN_TRADES,
            "e_drift_s": E_DRIFT_S, "c_life_s": C_LIFE_S, "c_lookback_s": C_LOOKBACK_S, "c_drift_s": C_DRIFT_S,
            "c_order_shares": C_ORDER_SHARES, "grid_2h": GRID_2H, "grid_6h": GRID_6H,
        },
        "bands": {"a": list(BAND_A), "e": list(BAND_E), "c": list(BAND_C)},
        "costs": {
            "half_spread": [list(x) for x in HALF_SPREAD], "genesis_h_min": GENESIS_H_MIN, "ask_cap": ASK_CAP,
            "cost_sens": COST_SENS, "docs_rate": economics.DOCS_CATEGORY_RATE, "unknown_rate": economics.MAX_DOCS_RATE,
            "fee_table_version": economics.FEE_TABLE_VERSION,
        },
        "rules": {
            "min_units": MIN_UNITS, "min_clusters": MIN_CLUSTERS, "min_losing_clusters": MIN_LOSING_CLUSTERS,
            "alpha_stage1": ALPHA_STAGE1, "alpha_stage2": ALPHA_STAGE2, "rann_floor": RANN_FLOOR,
            "placebo_draws": PLACEBO_DRAWS, "placebo_max_rate": PLACEBO_MAX_RATE, "top_events_dropped": TOP_EVENTS_DROPPED,
            "kill_min_markets": KILL_MIN_MARKETS, "px1_z": {str(k): v for k, v in PX1_Z.items()}, "seed": SEED,
            "max_age_s": MAX_AGE, "point_lag_s": float(hb.POINT_LAG_S),
        },
        "h2_completeness": H2_COMPLETENESS_RULE,
        "batch_holm_family": BATCH_HOLM_FAMILY_RULE,
        "e3_text_rule": {"name_re": NAME_RE, "name_flags": NAME_FLAGS, "verb_re": VERB_RE, "verb_flags": VERB_FLAGS},
        "interpretations": INTERPRETATIONS,
    }


def declaration_sha256() -> str:
    blob = json.dumps(declaration_blob(), sort_keys=True, default=float).encode()
    return hashlib.sha256(blob).hexdigest()


# =============================================================================================
# 1. Cost model (section 2.1)
# =============================================================================================


def half_spread(p: float) -> float:
    for edge, h in HALF_SPREAD:
        if p < edge:
            return h
    return HALF_SPREAD[-1][1]


def fee_rate(category) -> float:
    """Docs rate by ``fee_category`` prefix; unknown / null -> 0.07 (conservative)."""
    c = str(category or "unknown").split(":")[0]
    return float(economics.DOCS_CATEGORY_RATE.get(c, economics.MAX_DOCS_RATE))


def taker_fee_ps(a: float, rate: float) -> float:
    """Taker fee per share at price a (``economics.taker_fee`` with one share)."""
    return float(economics.taker_fee(1.0, float(a), float(rate)))


def is_sports(category) -> bool:
    return str(category or "").split(":")[0] == "sports"


@dataclass(frozen=True)
class Cost:
    ask: float
    fee: float
    capital: float


def cost_model(p_side: float, category, *, genesis: bool = False, extra: float = 0.0) -> Cost:
    """Modelled ask for the side bought and its taker fee. ``extra`` is the cost sensitivity (added to the half-spread)."""
    h = half_spread(p_side)
    if genesis:
        h = max(h, GENESIS_H_MIN)
    a = min(p_side + h + extra, ASK_CAP)
    f = taker_fee_ps(a, fee_rate(category))
    return Cost(ask=a, fee=f, capital=a + f)


# =============================================================================================
# 2. Outcomes, clocks, truncation
# =============================================================================================

DECISIVE = (0.0, 0.5, 1.0)


def parse_outcome0(raw) -> float | None:
    """Payout of token 0 (Yes / outcome 0) from Gamma ``outcomePrices``: 1, 0 or 0.5; None if missing / unparseable."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    try:
        v = json.loads(raw) if isinstance(raw, str) else list(raw)
        a, b = float(v[0]), float(v[1])
    except (TypeError, ValueError, IndexError, KeyError, json.JSONDecodeError):
        return None
    if abs(a + b - 1.0) > 1e-6 or a not in DECISIVE:
        return None
    return a


def iso_week(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%G-W%V")


def frame_psu(rec: dict) -> str:
    """Frame window (PSU): day x 15-minute slot of the Gamma walk key (end_date for closed, start_date for active)."""
    x = rec["end_epoch"] if rec["closed"] and not math.isnan(rec["end_epoch"]) else rec["start_epoch"]
    if math.isnan(x):
        return "nan"
    return f"{int(x // DAY)}|{int((x % DAY) // 900)}"


def oldest_or_inf(oldest_ts) -> float:
    """``trades_oldest_ts`` as a float; missing / NaN means nothing is known (+inf)."""
    try:
        v = float(oldest_ts)
    except (TypeError, ValueError):
        return math.inf
    return math.inf if math.isnan(v) else v


def trade_condition_state(
    tr_ts: np.ndarray, truncated: bool, oldest_ts: float | None, a, b, k: int = 1
) -> np.ndarray:
    """Per-candidate state of "at least k trades with a <= ts < b" (venue ``ts < t`` convention).

    1 = True, 0 = False, -1 = unavailable. A condition is known true if the stored trades already satisfy it; in a
    truncated market a window starting before ``trades_oldest_ts`` that the stored trades do not satisfy is unavailable
    (never 0). ``a`` may be -inf; ``a`` and ``b`` broadcast.
    """
    a = np.atleast_1d(np.asarray(a, float))
    b = np.atleast_1d(np.asarray(b, float))
    a, b = np.broadcast_arrays(a, b)
    cnt = np.searchsorted(tr_ts, b, side="left") - np.searchsorted(tr_ts, a, side="left")
    ok = cnt >= k
    out = np.where(ok, 1, 0)
    if truncated:
        # nothing is known before the oldest stored trade (no stored trades: nothing is known anywhere)
        old = oldest_or_inf(oldest_ts)
        out = np.where(~ok & (a < old), -1, out)
    return out.astype(int)


def combine_states(*states: np.ndarray) -> np.ndarray:
    """AND with unavailable propagation: any False -> False; else any unavailable -> unavailable; else True."""
    st = np.vstack([np.broadcast_to(s, np.broadcast(*states).shape) for s in states])
    anyf = (st == 0).any(axis=0)
    anyu = (st == -1).any(axis=0)
    return np.where(anyf, 0, np.where(anyu, -1, 1)).astype(int)


def open_at(created: float, close: float, t: np.ndarray) -> np.ndarray:
    """``created_at <= t < closed_time`` (closed_time NaN: still open)."""
    ok = t >= created if not math.isnan(created) else np.ones(len(t), bool)
    if not math.isnan(close):
        ok = ok & (t < close)
    return ok


def asof_quote(ts: np.ndarray, vals: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Last price point usable at t (stamp + 600 s < t, at most 2h old) else NaN."""
    if len(ts) == 0:
        return np.full(len(t), np.nan)
    return hb._asof(ts, vals, np.asarray(t, float), MAX_AGE)[0]


def first_qualifying(nontrade_ok: np.ndarray, trade_state: np.ndarray) -> tuple[int, str]:
    """(index, status): status 'selected' | 'unavailable' | 'none'. Scans candidates whose non-trade conditions hold."""
    cand = np.flatnonzero(nontrade_ok & (trade_state != 0))
    if len(cand) == 0:
        return -1, "none"
    i = int(cand[0])
    return i, ("selected" if trade_state[i] == 1 else "unavailable")


# =============================================================================================
# 3. Population / origin selection (no outcome is read here)
# =============================================================================================


@dataclass
class Ctx:
    run_id: str
    t_fetch: float
    t_censor: float
    is_h5: bool = False
    lookback_d: float = LOOKBACK_D

    @property
    def last_origin(self) -> float:
        return self.t_censor - HOLD_BUFFER_D * DAY


def in_lookback(rec: dict, ctx: Ctx) -> bool:
    """CB1-F completeness rule: ``created_at >= T_fetch - lookback``. A market with no creation time cannot be shown
    to satisfy it and is excluded (and counted); missing data stays missing."""
    cre = rec["created_epoch"]
    return bool(not math.isnan(cre) and cre >= ctx.t_fetch - ctx.lookback_d * DAY)


def status_tag(closed: bool, y0: float | None, close_epoch: float) -> str:
    """Outcome status of a market for counting units that never formed: unresolved | missing | 5050 | resolved."""
    if not closed:
        return "unresolved"
    if y0 is None or math.isnan(close_epoch):
        return "missing"
    return "5050" if y0 == 0.5 else "resolved"


def drop_outcome_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Census guard: the outcome columns never reach the population code."""
    return df.drop(columns=[c for c in OUTCOME_COLUMNS if c in df.columns])


def assert_no_outcome_columns(df: pd.DataFrame) -> None:
    bad = [c for c in OUTCOME_COLUMNS if c in df.columns]
    if bad:
        raise ValueError(f"census mode must not see outcome columns: {bad}")


def norm_rec(r: dict) -> dict:
    """Normalise a frame row: numeric epochs, categorical fields as str."""
    out = dict(r)
    for k in ("start_epoch", "end_epoch", "close_epoch", "liquidity", "volume"):
        v = out.get(k, "")
        out[k] = float("nan") if v in ("", None) else float(v)
    out["created_epoch"] = hb._epoch(out.get("created_at")) if out.get("created_at") not in ("", None) else float("nan")
    out["closed"] = int(float(out.get("closed", 0) or 0))
    out["market_id"] = str(out["market_id"])
    out["event_id"] = str(out.get("event_id", "") or "")
    out["fee_category"] = str(out.get("fee_category", "") or "unknown")
    return out


def parse_outcomes_list(raw) -> list[str] | None:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str) and raw.strip():
        try:
            v = json.loads(raw)
        except ValueError:
            return None
        return [str(x) for x in v] if isinstance(v, list) else None
    return None


def _side_and_price(p0: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Favourite side (0 if p0 >= 0.5 else 1) and its price."""
    side = np.where(p0 >= 0.5, 0, 1)
    return side, np.where(side == 0, p0, 1.0 - p0)


def _grid(lo: float, hi: float, step: float) -> np.ndarray:
    """Fixed UTC grid points t with lo <= t < hi."""
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        return np.empty(0)
    k0 = math.ceil(lo / step)
    k1 = math.ceil(hi / step)
    return np.arange(k0, k1) * step


def rec_weight(rec: dict) -> float:
    """Design weight (secondary estimates only): stored ``sample_weight`` (h5) or the h2 manifest-derived weight."""
    try:
        w = float(rec.get("sample_weight", 1.0))
    except (TypeError, ValueError):
        return 1.0
    return w if math.isfinite(w) and w > 0 else 1.0


def _unit_base(rec: dict, ctx: Ctx, tid: str, t: float, side: int, p_side: float, cost: Cost, extra: dict | None = None) -> dict:
    u = {
        "test": tid, "market_id": rec["market_id"], "event": rec["event_id"] or f"m:{rec['market_id']}",
        "category": rec["fee_category"], "t": float(t), "side": int(side), "p_side": float(p_side), "a": cost.ask,
        "f": cost.fee, "close_epoch": rec["close_epoch"], "end_epoch": rec["end_epoch"], "closed": rec["closed"],
        "psu": frame_psu(rec), "w": rec_weight(rec), "kind": "long",
    }
    if extra:
        u.update(extra)
    return u


def select_a1(rec: dict, ts, vals, tr_ts, truncated, oldest_ts, ctx: Ctx, diag: dict | None = None) -> tuple[dict | None, dict | None]:
    """A1: first qualifying 2h origin in [end_at, end_at + 24h). Returns (unit, excluded)."""
    if is_sports(rec["fee_category"]) or math.isnan(rec["end_epoch"]):
        return None, None
    end = rec["end_epoch"]
    t = _grid(end, end + A1_WINDOW_S, GRID_2H)
    t = t[t <= ctx.last_origin]
    if len(t) == 0:
        return None, None
    p0 = asof_quote(ts, vals, t)
    side, ps = _side_and_price(p0)
    nontrade = np.isfinite(p0) & open_at(rec["created_epoch"], rec["close_epoch"], t) & (ps >= BAND_A[0]) & (ps <= BAND_A[1])
    c1 = trade_condition_state(tr_ts, truncated, oldest_ts, -np.inf, end, 1)
    c2 = trade_condition_state(tr_ts, truncated, oldest_ts, end, t, 1)
    state = combine_states(c1, c2)
    i, st = first_qualifying(nontrade, state)
    if st == "none":
        if diag is not None and not np.isfinite(p0).any():
            diag["no_asof_price"] = True  # every candidate origin lacks an as-of price: dropped, counted by the caller
        return None, None
    cost = cost_model(float(ps[i]), rec["fee_category"])
    base = _unit_base(rec, ctx, "A1", t[i], int(side[i]), float(ps[i]), cost)
    if st == "unavailable":
        return None, {**base, "reason": "trade_truncation_unavailable"}
    return base, None


def select_a2(rec: dict, ts, vals, tr_ts, truncated, oldest_ts, ctx: Ctx, diag: dict | None = None) -> tuple[dict | None, dict | None]:
    """A2: scheduled life <= 100d, first qualifying 2h origin with t < end_at - 24h."""
    end, cre = rec["end_epoch"], rec["created_epoch"]
    if math.isnan(end) or math.isnan(cre) or end - cre > LIFE_MAX_D * DAY or end > ctx.t_fetch + END_FORWARD_D * DAY:
        return None, None
    t = _grid(cre, end - A2_PRE_END_S, GRID_2H)
    t = t[t <= ctx.last_origin]
    if len(t) == 0:
        return None, None
    p0 = asof_quote(ts, vals, t)
    side, ps = _side_and_price(p0)
    nontrade = np.isfinite(p0) & open_at(cre, rec["close_epoch"], t) & (ps >= BAND_A[0]) & (ps <= BAND_A[1])
    state = trade_condition_state(tr_ts, truncated, oldest_ts, t - A2_TRADE_LOOKBACK_S, t, 1)
    i, st = first_qualifying(nontrade, state)
    if st == "none":
        if diag is not None and not np.isfinite(p0).any():
            diag["no_asof_price"] = True
        return None, None
    cost = cost_model(float(ps[i]), rec["fee_category"])
    base = _unit_base(rec, ctx, "A2", t[i], int(side[i]), float(ps[i]), cost)
    if st == "unavailable":
        return None, {**base, "reason": "trade_truncation_unavailable"}
    return base, None


def e_eligible_static(rec: dict, ctx: Ctx) -> bool:
    """Population facts known at listing (scheduled facts only; no closed_time)."""
    if parse_outcomes_list(rec.get("outcomes")) != ["Yes", "No"] or is_sports(rec["fee_category"]):
        return False
    end, cre = rec["end_epoch"], rec["created_epoch"]
    if math.isnan(end) or math.isnan(cre):
        return False
    return (end - cre <= LIFE_MAX_D * DAY) and (end <= ctx.t_fetch + END_FORWARD_D * DAY)


def select_e(rec: dict, ts, vals, tr_ts, truncated, oldest_ts, ctx: Ctx, offset: float = E_ORIGIN_S,
             diag: dict | None = None) -> tuple[dict | None, dict | None]:
    """E1 population unit at origin created_at + offset (YES = outcome 0 = ``Yes``)."""
    if not e_eligible_static(rec, ctx):
        return None, None
    cre = rec["created_epoch"]
    t = np.array([cre + offset])
    if t[0] > ctx.last_origin:
        return None, None
    pY = asof_quote(ts, vals, t)
    if not np.isfinite(pY[0]):
        if diag is not None:
            diag["no_asof_price"] = True  # no as-of price at the origin: dropped, counted by the caller
        return None, None
    if not (BAND_E[0] <= pY[0] <= BAND_E[1]):
        return None, None
    if not open_at(cre, rec["close_epoch"], t)[0]:
        return None, None
    p_no = 1.0 - float(pY[0])
    cost = cost_model(p_no, rec["fee_category"], genesis=True)
    base = _unit_base(rec, ctx, "E1", t[0], 1, p_no, cost, {"p_yes": float(pY[0]), "question": rec.get("question", "")})
    st = trade_condition_state(tr_ts, truncated, oldest_ts, cre, t, E_MIN_TRADES)[0]
    if st == 0:
        return None, None
    if st == -1:
        return None, {**base, "reason": "trade_truncation_unavailable"}
    return base, None


# --- outcomes attached after selection ---------------------------------------------------------------------------------


def last_point(ts: np.ndarray, vals: np.ndarray) -> float:
    return float(vals[-1]) if len(vals) else float("nan")


def attach_outcome(u: dict, y0: float | None, ts: np.ndarray, vals: np.ndarray, ctx: Ctx) -> dict:
    """Add Y (payout of the position's outcome), status and hold / cluster fields. Long positions hold side ``u['side']``.

    status: resolved | 5050 | censored | missing. Censored long: marked at the last as-of price of the side minus the
    half-spread and the exit fee (flagged); censored short (C): bought back at the last price plus the half-spread.
    """
    u = dict(u)
    closed = bool(u["closed"])
    side = u["side"]
    u["censored"] = False
    u["Y0"] = np.nan if y0 is None else y0
    if closed and (y0 is None or math.isnan(u["close_epoch"])):
        u.update(status="missing", Y=np.nan, d=np.nan, week="missing")
        return u
    if closed:
        y = y0 if side == 0 else 1.0 - y0
        u["Y"] = float(y)
        u["status"] = "5050" if y0 == 0.5 else "resolved"
        u["d"] = max((u["close_epoch"] - u["t_hold"]) / DAY, 1.0) if "t_hold" in u else max((u["close_epoch"] - u["t"]) / DAY, 1.0)
        u["week"] = iso_week(u["close_epoch"])
        return u
    # unresolved at T_censor
    p_last0 = last_point(ts, vals)
    p_last = p_last0 if side == 0 else 1.0 - p_last0
    if not math.isfinite(p_last):
        u.update(status="missing", Y=np.nan, d=np.nan, week="missing")
        return u
    if u["kind"] == "long":
        proceeds = p_last - half_spread(p_last) - taker_fee_ps(p_last, fee_rate(u["category"]))
        u["Y"] = float(proceeds)
    else:
        u["Y"] = float(min(p_last + half_spread(p_last), 1.0))
    u["status"] = "censored"
    u["censored"] = True
    t0 = u.get("t_hold", u["t"])
    u["d"] = max((ctx.t_censor - t0) / DAY, 1.0)
    u["week"] = iso_week(ctx.t_censor)
    return u


def finalize_net(df: pd.DataFrame) -> pd.DataFrame:
    """net and capital from Y, a, f (long: Y - a - f; short cheap side: a - Y with capital 1 - a)."""
    df = df.copy()
    long = df["kind"].to_numpy() == "long"
    df["net"] = np.where(long, df["Y"] - df["a"] - df["f"], df["a"] - df["Y"])
    df["K"] = np.where(long, df["a"] + df["f"], 1.0 - df["a"])
    return df


# =============================================================================================
# 4. Statistics: clustering test, tail bound, placebo, robustness
# =============================================================================================


def r_ann(df: pd.DataFrame) -> float:
    """Capital-time ratio ``365 * sum(net) / sum(K * max(d, 1))``."""
    den = float((df["K"] * np.maximum(df["d"], 1.0)).sum())
    return float(365.0 * df["net"].sum() / den) if den > 0 else float("nan")


def cluster_arrays(df: pd.DataFrame, psu: bool = False) -> tuple[np.ndarray, np.ndarray]:
    ev = df["event"].astype(str).to_numpy()
    day = (df["psu"] if psu else df["week"]).astype(str).to_numpy()
    return ev, day


def cluster_test(
    v: np.ndarray, ev: np.ndarray, wk: np.ndarray, sign: int, n_boot: int = N_BOOT, w: np.ndarray | None = None, seed: int = SEED
) -> dict:
    """Mean with p = max(event-clustered CR1, two-way event x week CR1), one-sided in ``sign`` (HB1 rule) and a
    2,000-draw event-cluster percentile bootstrap CI."""
    if len(v) < 2 or len(pd.unique(ev)) < 2:
        return {"testable": False, "p": 1.0, "mean": float(np.mean(v)) if len(v) else float("nan"), "n": int(len(v)),
                "n_event": int(len(pd.unique(ev)))}
    return B.mean_test(np.asarray(v, float), ev, wk, sign=sign, n_boot=n_boot, seed=seed, w=w)


def clopper_pearson(k: int, n: int, conf: float, side: str) -> float:
    """One-sided Clopper-Pearson bound of a binomial proportion (``side`` 'upper' | 'lower')."""
    if n <= 0:
        return 1.0 if side == "upper" else 0.0
    if side == "upper":
        return 1.0 if k >= n else float(beta_dist.ppf(conf, k + 1, n - k))
    return 0.0 if k <= 0 else float(beta_dist.ppf(1.0 - conf, k, n - k + 1))


def wilson_bound(p: float, n_eff: float, conf: float, side: str) -> float:
    z = float(norm.ppf(conf))
    n = max(n_eff, 1.0)
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0))
    den = 1 + z * z / n
    return float(min(1.0, (centre + half) / den)) if side == "upper" else float(max(0.0, (centre - half) / den))


def tail_bound(
    losses: np.ndarray, clusters: np.ndarray, alpha: float, side: str = "upper", n_boot: int = 500, seed: int = SEED
) -> dict:
    """One-sided, cluster-aware bound on the losing share ``pi`` (section 2.3).

    With >= 10 losing event clusters: Wilson on ``n / deff`` (deff from the event-cluster bootstrap of the losing share,
    floored at 1). With fewer: exact Clopper-Pearson on event-level losses (an event loses if any of its units does).
    """
    losses = np.asarray(losses, bool)
    n = len(losses)
    if n == 0:
        return {"pi_hat": float("nan"), "bound": 1.0 if side == "upper" else 0.0, "method": "empty", "n": 0}
    conf = 1.0 - alpha
    codes, uniq = pd.factorize(np.asarray(clusters).astype(str))
    g = len(uniq)
    loss_c = np.bincount(codes, weights=losses.astype(float), minlength=g)
    cnt_c = np.bincount(codes, minlength=g).astype(float)
    n_lose_ev = int((loss_c > 0).sum())
    pi_hat = float(losses.mean())
    out = {"pi_hat": pi_hat, "n": int(n), "n_event": int(g), "losing_clusters": n_lose_ev, "alpha": alpha, "side": side}
    if n_lose_ev < MIN_LOSING_CLUSTERS:
        out.update(method="clopper_pearson_event_level", bound=clopper_pearson(n_lose_ev, g, conf, side), z_usable=False)
        return out
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ loss_c) / max(m @ cnt_c, 1e-12)
    var_b = float(bs.var(ddof=1))
    var_bin = pi_hat * (1 - pi_hat) / n
    deff = max(1.0, var_b / var_bin) if var_bin > 0 else 1.0
    out.update(method="wilson_n_over_deff", deff=deff, n_eff=n / deff, bound=wilson_bound(pi_hat, n / deff, conf, side), z_usable=True)
    return out


def tail_params(df: pd.DataFrame, which: str) -> tuple[np.ndarray, float]:
    """(loss indicator, break-even pi*) for the declared tail: A (favourite loses) or C (longshot wins).
    Computed over the NON-censored units only: a censored unit has no observed binary outcome, so it is not a
    non-loser in the denominator of pi (see :func:`tail_inputs` for the censored-as-loser bound)."""
    d = df[df["status"].to_numpy() != "censored"]
    if which == "A":
        return (d["Y"].to_numpy() == 0.0), float(1.0 - (d["a"] + d["f"]).mean()) if len(d) else float("nan")
    return (d["Y"].to_numpy() == 1.0), float(d["a"].mean()) if len(d) else float("nan")


def tail_inputs(df: pd.DataFrame, which: str) -> dict:
    """Tail-gate inputs: non-censored (losses, clusters, pi*) and the censored-as-loser variant (reported)."""
    cens = (df["status"].to_numpy() == "censored")
    d = df[~cens]
    losses, pi_star = tail_params(df, which)
    ev_all, _ = cluster_arrays(df)
    ev_all = np.asarray(ev_all)
    base = (d["Y"].to_numpy() == (0.0 if which == "A" else 1.0))
    full = np.zeros(len(df), bool)
    full[~cens] = base
    full[cens] = True  # worst case: every censored unit counted as a loser
    return {"losses": losses, "clusters": ev_all[~cens], "pi_star": pi_star, "losses_cens_loser": full,
            "clusters_all": ev_all, "n_censored": int(cens.sum())}


def value_col(spec: dict) -> str:
    return "drift" if spec["kind"] == "mechanism" else "net"


def gate_core(
    df: pd.DataFrame, spec: dict, alpha: float, *, n_boot: int, n_boot_deff: int = 500, w: np.ndarray | None = None, seed: int = SEED
) -> dict:
    """Stage gate conditions (a)-(d): p / exact bound, floor, R_ann, tail gate. Robustness and placebo are layered on top."""
    col = value_col(spec)
    n = len(df)
    if n == 0 or col not in df.columns:
        return {"n": 0, "n_event": 0, "testable": False, "p": 1.0, "advance_core": False, "fail": ["not_testable"],
                "mean": float("nan")}
    ev, wk = cluster_arrays(df)
    n_ev = int(len(pd.unique(ev)))
    out: dict = {"n": int(n), "n_event": n_ev}
    if n < MIN_UNITS or n_ev < MIN_CLUSTERS:
        out.update(testable=False, p=1.0, advance_core=False, fail=["not_testable"], mean=float(df[col].mean()) if n else float("nan"))
        return out
    v = df[col].to_numpy(float)
    ct = cluster_test(v, ev, wk, spec["direction"], n_boot=n_boot, seed=seed)
    out.update({k: ct.get(k) for k in ("mean", "p", "p_event", "p_twoway", "se_event", "se_twoway", "ci_event_boot", "z_event", "z_twoway")})
    out["testable"] = True
    fail = []
    z_usable = True
    tail = None
    if spec["tail"]:
        ti = tail_inputs(df, spec["tail"])
        pi_star = ti["pi_star"]
        tb = tail_bound(ti["losses"], ti["clusters"], alpha, "upper", n_boot=n_boot_deff, seed=seed)
        tail_ok = bool(tb["bound"] < pi_star - spec["tail_floor"])  # censored units are NOT in the pi denominator
        tail = {**tb, "pi_star": pi_star, "floor": spec["tail_floor"], "ok": tail_ok, "pi_star_minus_floor": pi_star - spec["tail_floor"],
                "n_censored_excluded": ti["n_censored"]}
        if ti["n_censored"]:  # reported bound: every censored unit counted as a loser (not binding)
            tbc = tail_bound(ti["losses_cens_loser"], ti["clusters_all"], alpha, "upper", n_boot=n_boot_deff, seed=seed)
            tail["censored_as_loser"] = {"pi_hat": tbc["pi_hat"], "bound": tbc["bound"], "method": tbc["method"],
                                         "ok": bool(tbc["bound"] < pi_star - spec["tail_floor"])}
        z_usable = bool(tb.get("z_usable", True))
        if not tail_ok:
            fail.append("tail_gate")
    out["tail"] = tail
    out["z_usable"] = z_usable
    p_ok = (ct["p"] < alpha) if z_usable else bool(tail and tail["ok"])
    out["p_ok"] = bool(p_ok)
    if not p_ok:
        fail.append("p")
    mean = float(ct["mean"])
    floor_ok = (mean >= spec["floor_net"]) if spec["direction"] > 0 else (mean <= spec["floor_net"])
    out["floor_ok"] = bool(floor_ok)
    if not floor_ok:
        fail.append("floor")
    if spec["rann_floor"] is not None:
        ra = r_ann(df)
        out["r_ann"] = ra
        out["rann_ok"] = bool(ra >= spec["rann_floor"])
        if not out["rann_ok"]:
            fail.append("r_ann")
    out["fail"] = fail
    out["advance_core"] = not fail
    return out


def breakeven_prob(df: pd.DataFrame) -> np.ndarray:
    """Break-even outcome probability: long ``min(a + f, 1)``; short cheap side ``a_c``."""
    long = df["kind"].to_numpy() == "long"
    return np.where(long, np.minimum(df["a"].to_numpy() + df["f"].to_numpy(), 1.0), df["a"].to_numpy())


def apply_y(df: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    d = df.copy()
    d["Y"] = y
    d["status"] = np.where(y == 0.5, "5050", "resolved")
    d["censored"] = False
    return finalize_net(d)


def breakeven_placebo(
    df: pd.DataFrame, spec: dict, alpha: float, n_draws: int = PLACEBO_DRAWS, seed: int = SEED, n_boot_deff: int = 200
) -> dict:
    """Replace Y by Bernoulli draws at break-even (expected net exactly 0) and rerun the Stage gate over ``n_draws``."""
    if not spec["placebo"] or len(df) == 0:
        return {"n_draws": 0, "advance_rate": None, "ok": True, "note": "not applicable"}
    rng = np.random.default_rng(seed + 7919)
    pb = breakeven_prob(df)
    adv = 0
    for _ in range(n_draws):
        y = (rng.random(len(df)) < pb).astype(float)
        d = apply_y(df, y)
        r = gate_core(d, spec, alpha, n_boot=2, n_boot_deff=n_boot_deff, seed=int(rng.integers(1, 10**6)))
        adv += int(r["advance_core"])
    rate = adv / n_draws
    return {"n_draws": n_draws, "n_advanced": adv, "advance_rate": rate, "max_rate": PLACEBO_MAX_RATE, "ok": bool(rate <= PLACEBO_MAX_RATE)}


def top_events_excluded(df: pd.DataFrame, k: int = TOP_EVENTS_DROPPED, col: str = "net") -> pd.DataFrame:
    contrib = df.groupby("event")[col].sum().abs().sort_values(ascending=False)
    drop = set(contrib.index[:k])
    return df[~df["event"].isin(drop)]


def sign_of(x: float) -> int:
    return 0 if (x is None or not math.isfinite(x)) else (1 if x > 0 else (-1 if x < 0 else 0))


def robustness(df: pd.DataFrame, spec: dict, alpha: float, rebuild_cost, n_boot: int) -> dict:
    """Binding checks (section 2.8): (i) +0.75c keeps net > 0; (ii) without the top 5 events p and floor hold; (iii) weighted
    and unweighted agree in sign. ``rebuild_cost(df, extra)`` returns the frame re-priced with the cost sensitivity."""
    col = value_col(spec)
    out: dict = {}
    if spec["kind"] == "economic":
        d2 = rebuild_cost(df, COST_SENS)
        out["cost_plus_075c_mean"] = float(d2["net"].mean())
        out["cost_plus_075c_ok"] = bool(d2["net"].mean() > 0)
    else:
        out["cost_plus_075c_ok"] = True
    red = top_events_excluded(df, col=col)
    g = gate_core(red, spec, alpha, n_boot=max(n_boot // 4, 50), n_boot_deff=200)
    out["without_top5_events"] = {k: g.get(k) for k in ("n", "n_event", "mean", "p", "p_ok", "floor_ok", "testable")}
    out["without_top5_ok"] = bool(g.get("testable") and g.get("p_ok") and g.get("floor_ok"))
    w = df["w"].to_numpy(float)
    mu_u = float(df[col].mean())
    mu_w = float((w * df[col].to_numpy(float)).sum() / w.sum()) if w.sum() > 0 else float("nan")
    out["weighted_mean"] = mu_w
    out["weighted_sign_agrees"] = bool(sign_of(mu_u) == sign_of(mu_w) and sign_of(mu_u) != 0)
    out["ok"] = bool(out["cost_plus_075c_ok"] and out["without_top5_ok"] and out["weighted_sign_agrees"])
    return out


def killed_categories(df: pd.DataFrame, spec: dict, alpha: float) -> dict:
    """Fee categories with >= 100 markets whose one-sided lower tail bound exceeds ``pi*`` (A, C only)."""
    if not spec["tail"]:
        return {}
    out = {}
    for cat, g in df.groupby(df["category"].str.split(":").str[0]):
        if g["market_id"].nunique() < KILL_MIN_MARKETS:
            continue
        ti = tail_inputs(g, spec["tail"])
        pi_star = ti["pi_star"]
        tb = tail_bound(ti["losses"], ti["clusters"], alpha, "lower", n_boot=200)
        out[str(cat)] = {"n_markets": int(g["market_id"].nunique()), "lower_bound": tb["bound"], "pi_star": pi_star, "killed": bool(tb["bound"] > pi_star)}
    return out


def capacity(df: pd.DataFrame, depth: np.ndarray | None = None, mean_net: float | None = None) -> dict:
    """Units per calendar week and median executable depth (shares at the ask, 'unknown' if not recorded)."""
    if len(df) == 0:
        return {"units_per_week": 0.0, "median_depth_shares": "unknown", "implied_usd_per_week": None}
    span_w = max((float(df["t"].max()) - float(df["t"].min())) / (7 * DAY), 1.0)
    per_week = len(df) / span_w
    dep = None if depth is None else np.asarray(depth, float)
    dep = dep[np.isfinite(dep)] if dep is not None else None
    if dep is None or len(dep) == 0:
        return {"units_per_week": per_week, "median_depth_shares": "unknown", "implied_usd_per_week": None}
    md = float(np.median(dep))
    return {"units_per_week": per_week, "median_depth_shares": md,
            "implied_usd_per_week": None if mean_net is None else float(per_week * md * mean_net)}


def km_wait(d: np.ndarray, resolved: np.ndarray) -> dict:
    """Median / p90 of the hold in days, censored share and a Kaplan-Meier survival curve (event = resolution)."""
    d = np.asarray(d, float)
    ev = np.asarray(resolved, bool)
    if len(d) == 0:
        return {}
    order = np.argsort(d)
    ds, es = d[order], ev[order]
    n_at = len(ds)
    s = 1.0
    curve = []
    i = 0
    while i < len(ds):
        j = i
        while j < len(ds) and ds[j] == ds[i]:
            j += 1
        at_risk = n_at - i
        deaths = int(es[i:j].sum())
        if deaths:
            s *= 1 - deaths / at_risk
            curve.append((float(ds[i]), s))
        i = j
    pts = {}
    for q in (7, 30, 60, 90, 180):
        pts[str(q)] = next((c[1] for c in reversed(curve) if c[0] <= q), 1.0)
    return {"median_d": float(np.median(d)), "p90_d": float(np.percentile(d, 90)), "censored_share": float(1 - ev.mean()), "km_survival_at_days": pts}


# =============================================================================================
# 5. Test evaluation (one declared test on one unit frame)
# =============================================================================================


def reprice_long(df: pd.DataFrame, extra: float) -> pd.DataFrame:
    """Cost sensitivity: re-price a long frame with ``extra`` added to the half-spread (outcomes unchanged)."""
    d = df.copy()
    genesis = d["test"].isin(["E1", "E3"]).to_numpy()
    asks, fees = [], []
    for ps, cat, g in zip(d["p_side"], d["category"], genesis, strict=True):
        c = cost_model(float(ps), cat, genesis=bool(g), extra=extra)
        asks.append(c.ask)
        fees.append(c.fee)
    d["a"], d["f"] = asks, fees
    # censored longs re-mark at the same proceeds; resolved Y is unchanged
    return finalize_net(d)


def reprice_short(df: pd.DataFrame, extra: float) -> pd.DataFrame:
    """C cost sensitivity: 0.75c less received on the sold longshot."""
    d = df.copy()
    d["a"] = np.maximum(d["a"] - extra, 0.0)
    return finalize_net(d)


def evaluate_test(
    df: pd.DataFrame, tid: str, *, stage: int = 1, n_boot: int = N_BOOT, n_placebo: int = PLACEBO_DRAWS, seed: int = SEED,
    depth: np.ndarray | None = None, placebo: bool = True, placebo_always: bool = False,
) -> dict:
    """Full declared evaluation of one test on its unit frame ``df`` (non-missing outcomes only)."""
    spec = HYPOTHESES_CB1[tid]
    alpha = ALPHA_STAGE1 if stage == 1 else ALPHA_STAGE2
    col = value_col(spec)
    res: dict = {"id": tid, "family": spec["family"], "kind": spec["kind"], "sign_tested": spec["direction"],
                 "floor": spec["floor_net"], "stage": stage, "alpha": alpha}
    df = df.reset_index(drop=True)
    g = gate_core(df, spec, alpha, n_boot=n_boot, seed=seed)
    res.update(g)
    res["effect"] = g.get("mean")
    if not g.get("testable"):
        res.update(advance=False, robustness=None, placebo=None, p=1.0)
        return res
    rebuild = reprice_short if spec["tail"] == "C" else reprice_long
    res["robustness"] = robustness(df, spec, alpha, rebuild, n_boot)
    if not spec["placebo"]:
        res["placebo"] = {"n_draws": 0, "ok": True, "note": "not applicable"}
    elif placebo and (g["advance_core"] or placebo_always):
        res["placebo"] = breakeven_placebo(df, spec, alpha, n_placebo, seed)
    else:
        res["placebo"] = {"n_draws": 0, "ok": True, "note": "skipped: gate not met (cannot advance)"}
    # PSU two-way sensitivity (reported)
    ev, psu = cluster_arrays(df, psu=True)
    res["psu_sensitivity"] = {k: v for k, v in cluster_test(df[col].to_numpy(float), ev, psu, spec["direction"], n_boot=50).items() if k in ("p", "p_event", "p_twoway", "mean")}
    res["killed_in_category"] = killed_categories(df, spec, alpha)
    res["capacity"] = capacity(df, depth, res.get("mean"))
    if spec["kind"] == "economic":
        res["sensitivity"] = economic_sensitivities(df, spec, rebuild)
        res["sub_band"] = sub_band(df, spec)
    res["by_month"] = by_group(df, col, pd.to_datetime(df["t"], unit="s", utc=True).dt.strftime("%Y-%m"))
    res["by_category"] = by_group(df, col, df["category"].str.split(":").str[0])
    killed = any(v["killed"] for v in res["killed_in_category"].values())
    res["advance"] = bool(g["advance_core"] and res["robustness"]["ok"] and res["placebo"].get("ok", True))
    res["fail"] = list(g["fail"]) + (["robustness"] if not res["robustness"]["ok"] else []) + (["placebo_miscalibrated"] if not res["placebo"].get("ok", True) else [])
    res["killed_flag"] = killed
    return res


def by_group(df: pd.DataFrame, col: str, key) -> dict:
    out = {}
    for k, g in df.groupby(key):
        out[str(k)] = {"n": int(len(g)), "mean": float(g[col].mean())}
    return out


def sub_band(df: pd.DataFrame, spec: dict) -> dict:
    if spec["family"] != "A":
        return {}
    hi = df[df["p_side"] >= 0.97]
    lo = df[df["p_side"] < 0.97]
    return {"ge_0.97": {"n": int(len(hi)), "mean": float(hi["net"].mean()) if len(hi) else None},
            "lt_0.97": {"n": int(len(lo)), "mean": float(lo["net"].mean()) if len(lo) else None}}


def economic_sensitivities(df: pd.DataFrame, spec: dict, rebuild) -> dict:
    """Reported, not binding: +1c cost, 50-50 / missing as losing, censoring at 0 and at 1, end_at sensitivity."""
    out = {"cost_plus_1c_mean": float(rebuild(df, COST_SENS_1C)["net"].mean())}
    long = df["kind"].to_numpy() == "long"
    d5 = df.copy()
    m = d5["status"] == "5050"
    d5.loc[m, "Y"] = np.where(long[m.to_numpy()], 0.0, 1.0)
    out["fifty_fifty_as_losing_mean"] = float(finalize_net(d5)["net"].mean())
    cens = df["censored"].to_numpy(bool)
    out["censored_share"] = float(cens.mean())
    for lab, val in zip(("censored_at_0", "censored_at_1"), CENSOR_ZERO_ONE, strict=True):
        dd = df.copy()
        dd.loc[cens, "Y"] = val
        out[lab + "_mean"] = float(finalize_net(dd)["net"].mean())
    lag = (df["close_epoch"] - df["end_epoch"]) > 30 * DAY
    keep = df[~(lag.fillna(False) & (df["closed"] == 1))]
    out["end_at_sensitivity"] = {"dropped": int(len(df) - len(keep)), "mean": float(keep["net"].mean()) if len(keep) else None}
    return out


# --- truncation / missing worst-case bounds (section 2.2) -----------------------------------------------------------------


def missing_as_losing(d: pd.DataFrame, raw: pd.DataFrame) -> dict:
    """Declared worst case (reported, not binding): units whose outcome is missing counted as losing at their own
    price (long: Y = 0; short cheap side: Y = 1), added to the usable units ``d``."""
    miss = raw[raw["status"] == "missing"] if len(raw) else raw
    base = float(d["net"].mean()) if len(d) else float("nan")
    if not len(miss):
        return {"n_missing": 0, "mean": base}
    m = miss.copy()
    m["Y"] = np.where(m["kind"].to_numpy() == "long", 0.0, 1.0)
    m = finalize_net(m)
    allnet = np.r_[d["net"].to_numpy(float) if len(d) else np.empty(0), m["net"].to_numpy(float)]
    return {"n_missing": int(len(m)), "mean": float(allnet.mean()), "mean_usable_only": base}


def y_tag(u: dict, y0: float | None) -> str:
    if u["closed"] and (y0 is None or math.isnan(u["close_epoch"])):
        return "missing"
    if not u["closed"]:
        return "unresolved"
    if y0 == 0.5:
        return "5050"
    y = y0 if u["side"] == 0 else 1.0 - y0
    return "win" if y == 1.0 else "lose"


def truncation_bound(df: pd.DataFrame, excluded: list[dict], tid: str) -> dict:
    """Mean net with every excluded unit added as a loser at its own ask (median ask when no origin was formed)."""
    spec = HYPOTHESES_CB1[tid]
    by_y: dict[str, int] = {}
    for u in excluded:
        by_y[u.get("y_tag", "unknown")] = by_y.get(u.get("y_tag", "unknown"), 0) + 1
    base = float(df["net"].mean()) if len(df) else float("nan")
    if not excluded:
        return {"n_excluded": 0, "by_outcome": by_y, "mean_with_excluded_as_losers": base, "sign_flips": False}
    med_cap = float((df["a"] + df["f"]).median()) if len(df) else 1.0
    short = spec["tail"] == "C"
    losers = []
    for u in excluded:
        if short:
            losers.append(u["a"] - 1.0 if "a" in u else -(1 - float(df["a"].median())))
        else:
            losers.append(-(u["a"] + u["f"]) if "a" in u else -med_cap)
    n = len(df)
    tot = (base * n if n else 0.0) + float(np.sum(losers))
    wc = tot / (n + len(excluded))
    return {"n_excluded": len(excluded), "by_outcome": by_y, "mean_with_excluded_as_losers": wc,
            "sign_flips": bool(sign_of(base) != sign_of(wc) and sign_of(base) > 0), "truncation_sensitive": bool(base > 0 >= wc)}


# =============================================================================================
# 6. CB1-C: longshot orders, queue fill rule, PX1 adverse-selection bound
# =============================================================================================


def buys_longshot(tr: pd.DataFrame, c: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(ts, price of side c, taker-buys-c flag, size) for trades sorted by ts. A BUY of c, or a SELL of the other token,
    is a taker buy of c; a SELL of the other token at p' is a buy of c at 1 - p'."""
    t = tr[tr["outcome_index"].isin([0, 1]) & tr["side"].isin(["BUY", "SELL"])].sort_values("ts", kind="stable")
    oi = t["outcome_index"].to_numpy()
    buy = (t["side"].to_numpy() == "BUY") == (oi == c)
    cp = np.where(oi == c, t["price"].to_numpy(float), 1.0 - t["price"].to_numpy(float))
    return t["ts"].to_numpy(float), cp, buy, t["size"].to_numpy(float)


def queue_fill(
    tr_c: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], t: float, a_c: float, q0: float, own: float = C_ORDER_SHARES,
    life: float = C_LIFE_S,
) -> dict:
    """Queue rule: cumulative taker volume buying side c at a price >= a_c within (t, t + life) reaches Q0 + own
    (all-or-nothing). Fill time = ts of the completing trade. Touch / through are reported alongside."""
    ts, cp, buy, size = tr_c
    lo = np.searchsorted(ts, t, side="right")
    hi = np.searchsorted(ts, t + life, side="left")
    ok = buy[lo:hi] & (cp[lo:hi] >= a_c - 1e-9)
    sz = size[lo:hi][ok]
    tt = ts[lo:hi][ok]
    need = (0.0 if (q0 is None or not math.isfinite(q0)) else float(q0)) + own
    cum = np.cumsum(sz)
    done = np.flatnonzero(cum >= need - 1e-12)
    through = bool((cp[lo:hi][ok] > a_c + 1e-9).any())
    return {"filled": bool(len(done)), "t_fill": float(tt[done[0]]) if len(done) else float("nan"),
            "touch": bool(ok.any()), "through": through}


def longshot_orders(books: pd.DataFrame, rec: dict, trades: pd.DataFrame | None, truncated: bool, oldest_ts, ts_p, vals_p, ctx: Ctx
                    ) -> tuple[list[dict], list[dict]]:
    """Orders for one market from its pmxt book rows (two-sided, both clocks <= origin by construction of the table).

    Returns (orders, excluded). Excluded: trade condition unavailable or an order life that starts before
    ``trades_oldest_ts`` of a truncated market (they enter the worst-case bound as filled losers).
    """
    orders: list[dict] = []
    excluded: list[dict] = []
    if trades is None:
        return orders, excluded
    tr_ts_all = np.sort(trades["ts"].to_numpy(float)) if len(trades) else np.empty(0)
    tr_c = {c: buys_longshot(trades, c) for c in (0, 1)}
    for r in books.itertuples():
        if r.state != "two_sided":
            continue
        b, a, bs, asz = r.sw_best_bid, r.sw_best_ask, r.sw_bid_size_1, r.sw_ask_size_1
        if not (np.isfinite(b) and np.isfinite(a)) or not a > b:
            continue
        t = float(r.origin_ts)
        if t > ctx.last_origin:
            continue
        if not open_at(rec["created_epoch"], rec["close_epoch"], np.array([t]))[0]:
            continue
        mid0 = (b + a) / 2
        c = 0 if mid0 <= 0.5 else 1
        m_c = mid0 if c == 0 else 1 - mid0
        if not (BAND_C[0] <= m_c <= BAND_C[1]):
            continue
        a_c = float(a if c == 0 else 1 - b)
        q0 = float(asz if c == 0 else bs)
        o = {"market_id": rec["market_id"], "event": rec["event_id"] or f"m:{rec['market_id']}", "category": rec["fee_category"],
             "t": t, "side": c, "m_c": float(m_c), "a_c": a_c, "a": a_c, "f": 0.0, "Q0": q0, "kind": "short",
             "close_epoch": rec["close_epoch"], "end_epoch": rec["end_epoch"], "closed": rec["closed"], "psu": frame_psu(rec),
             "w": rec_weight(rec)}
        st = trade_condition_state(tr_ts_all, truncated, oldest_ts, t - C_LOOKBACK_S, t, 1)[0]
        life_unc = bool(truncated) and oldest_or_inf(oldest_ts) > t
        if st == 0:
            continue
        if st == -1 or life_unc:
            excluded.append({**o, "reason": "trade_truncation_unavailable" if st == -1 else "life_before_oldest_trade"})
            continue
        fl = queue_fill(tr_c[c], t, a_c, q0)
        o.update(fl)
        t_ref = fl["t_fill"] if fl["filled"] else t + C_LIFE_S
        o["t_hold"] = fl["t_fill"] if fl["filled"] else t
        p_future = asof_quote(ts_p, vals_p, np.array([t_ref + C_DRIFT_S]))[0]
        m_future = (p_future if c == 0 else 1 - p_future) if np.isfinite(p_future) else float("nan")
        o["drift24"] = float(m_future - m_c) if np.isfinite(m_future) else float("nan")
        p_prev = asof_quote(ts_p, vals_p, np.array([t - C_DRIFT_S]))[0]
        o["prior24"] = float(m_c - (p_prev if c == 0 else 1 - p_prev)) if np.isfinite(p_prev) else float("nan")
        orders.append(o)
    return orders, excluded


def px1_bound(drift_filled: np.ndarray, drift_unfilled: np.ndarray, ev_f: np.ndarray, ev_u: np.ndarray,
              wk_f: np.ndarray, wk_u: np.ndarray, half_spread_captured: float, stage: int, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """PX1 adverse-selection bound: ``Delta = mean drift (filled) - mean drift (unfilled)``. Upper bound = hull (max) of the
    event-cluster bootstrap 95% upper limit and ``Delta + z * max(SE_event, SE_twoway)``; clean iff it is below the mean
    captured half-spread of filled orders."""
    z = PX1_Z[stage]
    y = np.concatenate([drift_filled, drift_unfilled]).astype(float)
    x = np.concatenate([np.ones(len(drift_filled)), np.zeros(len(drift_unfilled))])
    ev = np.concatenate([ev_f, ev_u]).astype(str)
    wk = np.concatenate([wk_f, wk_u]).astype(str)
    ok = np.isfinite(y)
    y, x, ev, wk = y[ok], x[ok], ev[ok], wk[ok]
    if x.sum() < 2 or (1 - x).sum() < 2:
        return {"testable": False, "clean": False, "reason": "too few filled or unfilled orders with a 24h post-fill point"}
    bt = B.beta_test(y, x, np.empty((len(y), 0)), ev, wk, sign=None, n_boot=2, seed=seed)
    if not bt.get("testable"):
        return {"testable": False, "clean": False, "reason": bt.get("reason", "no variation")}
    delta = float(bt["beta"])
    se = max(float(bt["se_event"]), float(bt["se_twoway"]))
    codes, uniq = pd.factorize(ev)
    g = len(uniq)
    sf = np.bincount(codes, weights=y * x, minlength=g)
    cf = np.bincount(codes, weights=x, minlength=g)
    su = np.bincount(codes, weights=y * (1 - x), minlength=g)
    cu = np.bincount(codes, weights=1 - x, minlength=g)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        nf, nu = m @ cf, m @ cu
        bs[i] = (m @ sf) / nf - (m @ su) / nu if nf > 0 and nu > 0 else np.nan
    boot_up = float(np.nanpercentile(bs, 95))
    hull = max(boot_up, delta + z * se)
    return {"testable": True, "delta_drift": delta, "se_max": se, "bootstrap_upper95": boot_up, "z": z, "upper_bound": hull,
            "mean_captured_half_spread": half_spread_captured, "clean": bool(hull < half_spread_captured),
            "n_filled": int(x.sum()), "n_unfilled": int((1 - x).sum())}


# =============================================================================================
# 7. Run drivers: loading a history run, building unit frames, screen / replicate / census
# =============================================================================================


class Refused(RuntimeError):
    """A guard refused to start the run."""


def forbid_run(run_id: str) -> None:
    if run_id in FORBIDDEN_RUNS or run_id.startswith("h4_seal"):
        raise Refused(f"CB1 refuses run id {run_id!r} (retired / sealed / pilot data)")


def utc_epoch(s: str) -> float:
    return hb._epoch(s)


def load_manifest(run_dir: Path) -> dict:
    p = Path(run_dir) / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


def request_clock(run_dir: Path) -> float:
    m = load_manifest(run_dir)
    v = m.get("request_clock_now")
    if not v:
        raise Refused(f"{run_dir}: manifest lacks request_clock_now (T_fetch / T_censor undefined)")
    return utc_epoch(v)


def h2_design_weights(manifest: dict, sample: pd.DataFrame) -> pd.Series:
    """h2 weights from its manifest: ``N_s / n_s`` per stratum (``sample_report.strata`` over ``allocation``)."""
    rep = manifest.get("sample_report", {})
    strata, alloc = rep.get("strata", {}), rep.get("allocation", {})
    w = sample["stratum"].map(lambda s: strata.get(s, np.nan) / alloc[s] if alloc.get(s) else np.nan)
    return w.astype(float)


def load_sample(run_dir: Path, census: bool = False) -> pd.DataFrame:
    run_dir = Path(run_dir)
    df = pd.read_csv(run_dir / "sample.csv.gz", dtype={"market_id": str, "token0": str, "token1": str, "event_id": str}, keep_default_na=False)
    if census:
        df = drop_outcome_columns(df)
        assert_no_outcome_columns(df)
    if "sample_weight" not in df.columns or (df["sample_weight"] == "").all():
        w = h2_design_weights(load_manifest(run_dir), df) if "stratum" in df.columns else pd.Series(1.0, index=df.index)
        df["sample_weight"] = w.fillna(1.0)
    text = run_dir / "cb1" / "text.csv.gz"
    if text.exists():
        tx = pd.read_csv(text, dtype=str, keep_default_na=False)
        cols = [c for c in ("market_id", "question", "outcomes") if c in tx.columns]
        tx = tx[cols].drop_duplicates("market_id")
        df = df.drop(columns=[c for c in ("question", "outcomes") if c in df.columns and c in tx.columns]).merge(tx, on="market_id", how="left")
        for c in ("question", "outcomes"):
            if c in df.columns:
                df[c] = df[c].fillna("")
    return df


def iter_markets(run_dir: Path, frame: pd.DataFrame, ids: set[str] | None = None):
    """Yield (rec, ts, vals, trades_df, truncated, oldest_ts) for every done market (streaming)."""
    run_dir = Path(run_dir)
    prog = hb._read_progress(run_dir / "progress.jsonl")
    for r in frame.to_dict("records"):
        mid = str(r["market_id"])
        if ids is not None and mid not in ids:
            continue
        p = prog.get(mid)
        if not p or p.get("status") != "done":
            continue
        rec = norm_rec(r)
        pp, tp = run_dir / "prices" / f"{mid}.csv.gz", run_dir / "trades" / f"{mid}.csv.gz"
        if not pp.exists() or not tp.exists():
            continue
        ts, vals = hb.load_prices(pp)
        tr = hb.load_trades(tp)
        yield rec, ts, vals, tr, bool(p.get("trades_truncated")), p.get("trades_oldest_ts")


def build_family_units(run_dir: Path, family: str, ctx: Ctx, *, text_ok: bool = True, max_markets: int | None = None,
                       books: pd.DataFrame | None = None, census: bool = False, synthetic: bool = False) -> dict:
    """Select origins and attach outcomes for one family. Returns {'units': {tid: DataFrame}, 'excluded': {...}, 'counts': {...}}."""
    frame = load_sample(run_dir, census=census or synthetic)  # dry run: outcome columns never loaded
    if family == "E" and ("outcomes" not in frame.columns or "question" not in frame.columns):
        raise Refused(f"{run_dir}: CB1-E needs question text and outcome labels (h2: run `fetch-text`; h5 stores them)")
    if max_markets:
        frame = frame.head(max_markets)
    units: dict[str, list[dict]] = {t: [] for t in FAMILY_TESTS[family]}
    excl: dict[str, list[dict]] = {t: [] for t in FAMILY_TESTS[family]}
    c_orders: list[dict] = []
    c_excl: list[dict] = []
    missing_text = 0
    if family == "C" and books is not None:
        books = books.copy()
        books["market_id"] = books["market_id"].astype(str)
        bk_groups = {k: g for k, g in books.groupby("market_id")}
    else:
        bk_groups = {}
    e_secondary: dict[float, list[dict]] = {o: [] for o in E_SECONDARY_S}
    n_markets = 0
    lb: dict = {"lookback_days": ctx.lookback_d, "markets_outside": 0, "created_missing": 0, "would_qualify": {t: 0 for t in FAMILY_TESTS[family]}}
    noprice: dict[str, dict[str, int]] = {t: {} for t in FAMILY_TESTS[family]}
    for rec, ts, vals, tr, trunc, oldest in iter_markets(run_dir, frame):
        n_markets += 1
        tr_ts = np.sort(tr["ts"].to_numpy(float)) if len(tr) else np.empty(0)
        if synthetic:  # code check only: token 0 "wins" in every closed market; real outcomes were dropped at load
            y0 = 1.0 if rec["closed"] else None
        else:
            y0 = None if census else parse_outcome0(rec.get("outcome_prices"))
        outside = family in ("A", "E") and not in_lookback(rec, ctx)
        if outside:
            lb["markets_outside"] += 1
            lb["created_missing"] += int(math.isnan(rec["created_epoch"]))
        if family == "A":
            for tid, fn in (("A1", select_a1), ("A2", select_a2)):
                dg: dict = {}
                u, ex = fn(rec, ts, vals, tr_ts, trunc, oldest, ctx, dg)
                if outside:  # completeness rule: not a unit; counted if it would otherwise have qualified
                    lb["would_qualify"][tid] += int(u is not None or ex is not None)
                    continue
                if dg.get("no_asof_price"):
                    tag = "census" if census else status_tag(bool(rec["closed"]), y0, rec["close_epoch"])
                    noprice[tid][tag] = noprice[tid].get(tag, 0) + 1
                if u is not None:
                    units[tid].append(u if census else attach_outcome(u, y0, ts, vals, ctx))
                if ex is not None:
                    ex["y_tag"] = "census" if census else y_tag(ex, y0)
                    excl[tid].append(ex)
        elif family == "E":
            if "outcomes" not in rec or rec.get("outcomes") in ("", None):
                if text_ok:
                    missing_text += 1
                continue
            dg = {}
            u, ex = select_e(rec, ts, vals, tr_ts, trunc, oldest, ctx, diag=dg)
            if outside:
                lb["would_qualify"]["E1"] += int(u is not None or ex is not None)
                continue
            if dg.get("no_asof_price"):
                tag = "census" if census else status_tag(bool(rec["closed"]), y0, rec["close_epoch"])
                noprice["E1"][tag] = noprice["E1"].get(tag, 0) + 1
            for off in E_SECONDARY_S:
                us, _ = select_e(rec, ts, vals, tr_ts, trunc, oldest, ctx, offset=off)
                if us is not None and not census:
                    e_secondary[off].append(attach_outcome(us, y0, ts, vals, ctx))
            sens = sensational(rec.get("question", ""))
            if u is not None:
                u["sensational"] = sens
                u["t_hold"] = u["t"]
                if not census:
                    u = attach_outcome(u, y0, ts, vals, ctx)
                    u["drift"] = e_drift(u, rec, ts, vals, y0)
                units["E1"].append(u)
                units["E2"].append(u)
                if sens:
                    units["E3"].append(u)
            if ex is not None:
                ex["y_tag"] = "census" if census else y_tag({**ex, "side": 1}, y0)
                ex["sensational"] = sens
                excl["E1"].append(ex)
                if sens:
                    excl["E3"].append(ex)
        elif family == "C":
            bk = bk_groups.get(rec["market_id"])
            if bk is None:
                continue
            od, ex = longshot_orders(bk, rec, tr, trunc, oldest, ts, vals, ctx)
            for o in od:
                c_orders.append(o if census else attach_outcome(o, y0, ts, vals, ctx))
            for e in ex:
                e["y_tag"] = "census" if census else y_tag(e, y0)
                c_excl.append(e)
    out: dict = {"n_markets_read": n_markets, "missing_text": missing_text}
    if family in ("A", "E"):
        out["lookback_excluded"] = lb
        out["no_asof_price_by_status"] = noprice
    if family == "C":
        out["orders"] = pd.DataFrame(c_orders)
        out["excluded"] = {"C": c_excl}
    else:
        out["units"] = {t: pd.DataFrame(v) for t, v in units.items()}
        out["excluded"] = excl
        if family == "E":
            out["e_secondary"] = {str(k): pd.DataFrame(v) for k, v in e_secondary.items()}
    return out


def e_drift(u: dict, rec: dict, ts, vals, y0) -> float:
    """7-day YES drift ``p_Y(t + 7d) - p_Y(t)``; payout if the market closed earlier; NaN when neither is available."""
    t7 = u["t"] + E_DRIFT_S
    if u["closed"] and not math.isnan(u["close_epoch"]) and u["close_epoch"] <= t7:
        return float(y0 - u["p_yes"]) if y0 is not None else float("nan")
    p = asof_quote(ts, vals, np.array([t7]))[0]
    return float(p - u["p_yes"]) if np.isfinite(p) else float("nan")


def usable(df: pd.DataFrame) -> pd.DataFrame:
    """Primary frame: non-missing outcomes, with net / capital computed."""
    if len(df) == 0:
        return df
    d = df[df["status"] != "missing"].copy()
    return finalize_net(d) if len(d) else d


def c_tests(orders: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if len(orders) == 0:
        return {"C1": orders, "C2": orders}
    f = orders[orders["filled"].astype(bool)]
    sp = f["category"].map(is_sports)
    return {"C1": f[~sp], "C2": f[sp]}


def census_counts(run_dir: Path, ctx: Ctx, books: pd.DataFrame | None = None, text_ok: bool = True) -> dict:
    """Counts only (population, clusters, price-band histograms, truncation exclusions not by outcome)."""
    out: dict = {"run_id": ctx.run_id, "note": "counts only; outcome columns dropped by guard; floors are not revised from the census"}
    for fam in ("A", "E"):
        r = build_family_units(run_dir, fam, ctx, text_ok=text_ok, census=True)
        out[fam] = {"markets_read": r["n_markets_read"], "missing_text": r["missing_text"]}
        for tid, df in r["units"].items():
            ex = r["excluded"][tid]
            hist = {}
            if len(df):
                bins = np.histogram(df["p_side"], bins=[0.0, 0.05, 0.2, 0.5, 0.8, 0.95, 0.97, 0.99, 1.0])
                hist = {f"{bins[1][i]:.2f}-{bins[1][i + 1]:.2f}": int(bins[0][i]) for i in range(len(bins[0]))}
            out[fam][tid] = {"units": int(len(df)), "event_clusters": int(df["event"].nunique()) if len(df) else 0,
                             "excluded_truncation": len(ex), "price_band_histogram": hist}
    if books is not None:
        r = build_family_units(run_dir, "C", ctx, books=books, census=True)
        o = r["orders"]
        out["C"] = {"orders": int(len(o)), "filled": int(o["filled"].sum()) if len(o) else 0,
                    "event_clusters_filled": int(o.loc[o["filled"].astype(bool), "event"].nunique()) if len(o) else 0,
                    "excluded_truncation": len(r["excluded"]["C"])}
    return out


# --- results / trials ---------------------------------------------------------------------------------------------------


def write_new(path: Path, obj) -> None:
    """Results files are never overwritten (exclusive create)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, default=_jsonable)


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(type(o))


def holm(pvals: dict[str, float], alpha: float = ALPHA_STAGE2) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict] = {}
    running = 0.0
    rejecting = True
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        rejecting = rejecting and (p <= alpha / (m - i))
        out[k] = {"p": p, "p_holm": running, "reject": bool(rejecting)}
    return out


STAGE2_TEST_IDS = ("A1", "A2", "C1", "C2", "E1", "E2", "E3", "D1", "D2", "B1", "B2")


def stage2_tests_from_results(doc: dict, name: str = "?") -> dict[str, dict]:
    """The Stage-2 tests of one results file, from either module. History rep files carry ``stage == 2``; the
    structural files are D rep (``window == 'rep'``) and B R1 (``stage == 'stage2_pre_holm'``). Anything else (a Stage-1
    screen, the D dev window, B3 prospective) is refused: it is not in the Stage-2 family."""
    tests = doc.get("tests")
    if not isinstance(tests, dict):
        raise Refused(f"{name}: no tests table")
    is_hist = doc.get("stage") == 2 and doc.get("revision") == REVISION_R
    is_d_rep = doc.get("window") == "rep" and set(tests) <= {"D1", "D2"}
    is_b_r1 = doc.get("stage") == "stage2_pre_holm" and set(tests) <= {"B1", "B2"}
    if not (is_hist or is_d_rep or is_b_r1):
        raise Refused(f"{name}: not a CB1 Stage-2 results file (history rep, D rep window, or B R1)")
    out = {}
    for tid, r in tests.items():
        if tid not in STAGE2_TEST_IDS:
            raise Refused(f"{name}: unknown test id {tid!r}")
        out[tid] = {"p": float(r.get("p", 1.0)), "advance": bool(r.get("advance")), "source": name}
    return out


ALWAYS_IN_FAMILY = ("B1", "B2")  # no Stage 1 (the effect was already seen in IF-H2): always in the Stage-2 family
BATCH_HOLM_FAMILY_RULE = (
    "The batch Holm family is every test that advanced at Stage 1 in any CB1 module (history A/C/E Stage-1 screens, D "
    "dev) plus B1 and B2, which have no Stage 1 and are always in the family. A Stage-2 test missing from the supplied "
    "Stage-2 files counts as p = 1 and is listed. The batch-holm command takes the Stage-1 (dev) results files and the "
    "Stage-2 files, derives the expected test list from the dev files plus the always-included tests, and refuses if "
    "any Stage-2 file contains a test outside that expected list.")


def stage1_advanced_from_results(doc: dict, name: str = "?") -> set[str]:
    """Tests that advanced at Stage 1 in one dev results file: a history screen (``stage == 1``, revision cb1_history)
    or the D dev window (``window == 'dev'``). Anything else is refused."""
    tests = doc.get("tests")
    if not isinstance(tests, dict):
        raise Refused(f"{name}: no tests table")
    is_hist = doc.get("stage") == 1 and doc.get("revision") == REVISION
    is_d_dev = doc.get("window") == "dev" and set(tests) <= {"D1", "D2"}
    if not (is_hist or is_d_dev):
        raise Refused(f"{name}: not a CB1 Stage-1 results file (history screen or D dev window)")
    out = set()
    for tid, r in tests.items():
        if tid not in STAGE2_TEST_IDS:
            raise Refused(f"{name}: unknown test id {tid!r}")
        if r.get("advance"):
            out.add(tid)
    return out


def batch_holm(results_docs: list[tuple[str, dict]], alpha: float = ALPHA_STAGE2, *,
               stage1_docs: list[tuple[str, dict]]) -> dict:
    """Batch-wide Holm (alpha, one-sided p-values) over the declared family (``BATCH_HOLM_FAMILY_RULE``): every test that
    advanced at Stage 1 in any CB1 module (``stage1_docs``) plus B1/B2. Stage-2 files (history rep, D rep, B R1) may
    contain only expected tests (else refused); an expected test with no Stage-2 result counts as p = 1 and is listed. A
    test is ``replicated`` only if its own Stage-2 gate passed (``advance``) AND the batch Holm rejects. A test id may
    appear once."""
    adv1: dict[str, str] = {}
    for name, doc in stage1_docs:
        for tid in stage1_advanced_from_results(doc, name):
            if tid in adv1:
                raise Refused(f"Stage-1 test {tid} appears in both {adv1[tid]} and {name}")
            adv1[tid] = name
    expected = set(adv1) | set(ALWAYS_IN_FAMILY)
    pv: dict[str, dict] = {}
    for name, doc in results_docs:
        for tid, rec in stage2_tests_from_results(doc, name).items():
            if tid not in expected:
                raise Refused(f"{name}: test {tid} is not in the expected family (advanced at Stage 1: {sorted(adv1)}; "
                              f"always: {list(ALWAYS_IN_FAMILY)})")
            if tid in pv:
                raise Refused(f"test {tid} appears in both {pv[tid]['source']} and {name}")
            pv[tid] = rec
    missing = sorted(expected - set(pv))
    for tid in missing:
        pv[tid] = {"p": 1.0, "advance": False, "source": "missing_stage2_p=1"}
    hm = holm({t: r["p"] for t, r in pv.items()}, alpha)
    tests = {t: {**pv[t], **hm[t], "replicated": bool(pv[t]["advance"] and hm[t]["reject"])} for t in sorted(pv)}
    return {"m": len(pv), "alpha": alpha, "tests": tests, "replicated": sorted(t for t, r in tests.items() if r["replicated"]),
            "expected_family": sorted(expected), "missing_stage2_counted_p1": missing,
            "stage1_inputs": [n for n, _ in stage1_docs], "family_rule": BATCH_HOLM_FAMILY_RULE}


def log_trials(out: dict, path: Path, *, replication: bool = False, family: str, dataset: str,
               trials_path: Path = provenance.TRIALS_PATH) -> int:
    """One ``cb1_history`` / ``cb1_history_replication`` line per test (EXCLUDE in ``battery2.KIND_RULES``), one placebo line per carry
    test (counts 0) and one ``ml_explain`` count line (``creative_batch_1:<family>``) carrying ``n_tests``, which is what
    both counters see."""
    sha = provenance.sha256_file(path)
    dsha = declaration_sha256()
    kind = TRIAL_KIND_R if replication else TRIAL_KIND
    rev = REVISION_R if replication else REVISION
    tests = out["tests"]
    prov = provenance.run_provenance()
    for tid, r in tests.items():
        provenance.append_trial({
            "kind": kind, "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE, "revision": rev, "dataset": dataset,
            "hypothesis": tid, "family": r["family"], "test_kind": r["kind"], "sign_tested": r["sign_tested"],
            "effect": B._clean(r.get("effect")), "p": B._clean(r.get("p")), "advance": bool(r.get("advance")),
            "testable": r.get("testable", True), "n": r.get("n"), "n_event": r.get("n_event"),
            "stage": r.get("stage"), "cumulative_count_at_run": out.get("cumulative_count"), "declaration_sha256": dsha,
            "results_sha256": sha, "provenance": prov, "data_provenance": hb.PROVENANCE,
        }, trials_path)
        pl = r.get("placebo") or {}
        if pl.get("n_draws"):
            provenance.append_trial({
                "kind": kind, "label": "EXPLORATORY", "evidence_role": "placebo", "revision": rev, "dataset": dataset,
                "hypothesis": tid, "note": "break-even placebo Y ~ Bern(a + f)", "advance_rate": pl.get("advance_rate"),
                "n_draws": pl["n_draws"], "declaration_sha256": dsha, "results_sha256": sha,
            }, trials_path)
    provenance.append_trial({
        "kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE, "source": f"creative_batch_1:{family}",
        "revision": rev, "dataset": dataset, "n_tests": len(tests), "n_tests_by_family": {f"cb1_{family}": len(tests)},
        "advanced": [t for t, r in tests.items() if r.get("advance")], "declaration_sha256": dsha, "results_sha256": sha,
        "data_provenance": hb.PROVENANCE, "note": "CB1 history summary: counts its tests into the cumulative ml_explain denominator",
    }, trials_path)
    return len(tests)


# =============================================================================================
# 8. Guards: declaration hash, seal, access log
# =============================================================================================


def spec_payload() -> dict:
    return {"version": VERSION, "declaration_sha256": declaration_sha256(), "e3_text_rule_sha256": e3_text_rule_sha256()}


def write_spec(path: Path = SPEC_PATH) -> dict:
    """Write the declaration spec (the CB1 freeze file). Refuses to overwrite."""
    p = spec_payload()
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; a frozen declaration is never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    return p


def spec_committed(path: Path) -> bool:
    """True if the spec file is tracked by git and identical to HEAD."""
    path = Path(path)
    cwd = provenance.REPO_ROOT
    try:
        rel = str(path.resolve().relative_to(cwd.resolve()))
    except ValueError:
        return False
    if provenance._git(["ls-files", "--error-unmatch", rel], cwd) is None:
        return False
    return provenance._git(["diff", "--quiet", "HEAD", "--", rel], cwd) is not None


def require_declaration(spec_path: Path = SPEC_PATH, *, require_committed: bool = True) -> str:
    """Refuse unless the committed spec's hash equals this code's declaration hash."""
    spec_path = Path(spec_path)
    if not spec_path.exists():
        raise Refused(f"declaration spec {spec_path} not found (CB1 freeze not committed)")
    if require_committed and not spec_committed(spec_path):
        raise Refused(f"declaration spec {spec_path} is not committed (or differs from HEAD)")
    spec = json.loads(spec_path.read_text())
    want = declaration_sha256()
    if spec.get("declaration_sha256") != want:
        raise Refused(f"declaration hash mismatch: committed {spec.get('declaration_sha256')} != code {want}")
    if spec.get("e3_text_rule_sha256") != e3_text_rule_sha256():
        raise Refused("E3 text-rule hash mismatch")
    return want


def require_e3_hash_committed(spec_path: Path = SPEC_PATH, *, require_committed: bool = True) -> None:
    """E3 text rule hash must be committed before any h2 question text is read."""
    spec_path = Path(spec_path)
    if not spec_path.exists() or (require_committed and not spec_committed(spec_path)):
        raise Refused("the E3 text-rule hash is not committed; refusing to read question text")
    if json.loads(spec_path.read_text()).get("e3_text_rule_sha256") != e3_text_rule_sha256():
        raise Refused("E3 text-rule hash mismatch")


def require_sealed(run_dir: Path, seal_copy: Path = SEAL_COPY) -> dict:
    """Every h5 reader calls this first: the run must carry a verifying ``SEAL.json`` and the committed repo copy must exist
    with the same listing hash. Any problem refuses (fail closed)."""
    try:
        return h5_seal.require_sealed(Path(run_dir), Path(seal_copy))
    except h5_seal.SealError as exc:
        raise Refused(f"h5 seal verification failed for {run_dir}: {exc}") from exc


def h5_access_log(run_dir: Path, job: str, files: list[str], decl_sha: str) -> dict:
    """Append one line to ``<run>/ACCESS_LOG.jsonl`` (UTC time, job id, git commit, files / globs, declaration hash)."""
    return h5_seal.log_access(Path(run_dir), job, list(files), declaration_sha=decl_sha)


def require_seal_copy(seal_copy: Path = SEAL_COPY) -> None:
    if not Path(seal_copy).exists():
        raise Refused(f"committed seal copy {seal_copy} not found; screens refuse to start before it exists")


# =============================================================================================
# 9. Family evaluation entry points
# =============================================================================================


@dataclass
class FamilyResult:
    family: str
    tests: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)


def evaluate_family(run_dir: Path, family: str, ctx: Ctx, *, stage: int = 1, only: list[str] | None = None, n_boot: int = N_BOOT,
                    n_placebo: int = PLACEBO_DRAWS, books: pd.DataFrame | None = None, text_ok: bool = True,
                    max_markets: int | None = None, placebo_y: bool = False, seed: int = SEED,
                    descriptive: bool = True) -> FamilyResult:
    """Run the declared tests of one family. ``placebo_y`` (dryrun) replaces every outcome by a break-even draw first."""
    built = build_family_units(run_dir, family, ctx, books=books, text_ok=text_ok, max_markets=max_markets, synthetic=placebo_y)
    fr = FamilyResult(family)
    fr.extras["n_markets_read"] = built["n_markets_read"]
    if "lookback_excluded" in built:
        fr.extras["lookback_excluded"] = built["lookback_excluded"]
        fr.extras["no_asof_price_by_status"] = built["no_asof_price_by_status"]
    rng = np.random.default_rng(seed + 31)

    def prep(df: pd.DataFrame) -> pd.DataFrame:
        d = usable(df) if len(df) else df
        if placebo_y and len(d):
            d = apply_y(d, (rng.random(len(d)) < breakeven_prob(d)).astype(float))
        return d

    if family == "C":
        orders = built["orders"]
        fr.extras["n_orders"] = int(len(orders))
        fr.extras["excluded_by_outcome"] = _tag_counts(built["excluded"]["C"])
        tests = c_tests(orders)
        for tid in FAMILY_TESTS["C"]:
            if only and tid not in only:
                continue
            f = prep(tests[tid])
            fr.tests[tid] = evaluate_c(f, orders, tid, stage, n_boot, n_placebo, built["excluded"]["C"], seed, ctx)
        return fr
    for tid in FAMILY_TESTS[family]:
        if only and tid not in only:
            continue
        df = built["units"][tid]
        d = prep(df)
        if tid == "E2":
            d = d[np.isfinite(d["drift"])] if len(d) else d
        r = evaluate_test(d, tid, stage=stage, n_boot=n_boot, n_placebo=n_placebo, seed=seed, placebo=True)
        r["n_missing_outcome"] = int((df["status"] == "missing").sum()) if len(df) else 0
        if len(d) and "sensitivity" in r:
            r["sensitivity"]["missing_as_losing"] = missing_as_losing(d, df)
        if tid != "E2":
            r["truncation"] = truncation_bound(d, built["excluded"][tid], tid) if len(d) else {"n_excluded": len(built["excluded"][tid])}
        else:
            r["truncation"] = {"n_excluded": len(built["excluded"]["E1"]), "note": "as E1"}
        if tid == "A1":
            r["wait"] = km_wait(d["d"].to_numpy(), (d["status"] != "censored").to_numpy()) if len(d) else {}
        if tid == "A2":
            r["wait"] = km_wait(d["d"].to_numpy(), (d["status"] != "censored").to_numpy()) if len(d) else {}
        fr.tests[tid] = r
    if family == "E":
        fr.extras["e_secondary_offsets"] = {k: _mean_net(usable(v)) for k, v in built["e_secondary"].items()}
        fr.extras["excluded_by_outcome"] = _tag_counts(built["excluded"]["E1"])
    if family == "A":
        fr.extras["excluded_by_outcome"] = {t: _tag_counts(v) for t, v in built["excluded"].items()}
        if descriptive and not placebo_y:
            fr.extras["a1_sports_descriptive"] = _a1_sports_descriptive(run_dir, ctx, max_markets)
    return fr


def _mean_net(d: pd.DataFrame) -> dict:
    return {"n": int(len(d)), "mean_net": float(d["net"].mean()) if len(d) else None}


def _tag_counts(lst: list[dict]) -> dict:
    out: dict[str, int] = {}
    for u in lst:
        out[u.get("y_tag", "unknown")] = out.get(u.get("y_tag", "unknown"), 0) + 1
    return out


def _a1_sports_descriptive(run_dir: Path, ctx: Ctx, max_markets: int | None) -> dict:
    frame = load_sample(run_dir)
    if max_markets:
        frame = frame.head(max_markets)
    sports = frame[frame["fee_category"].map(is_sports)]
    rows = []
    for rec, ts, vals, tr, trunc, oldest in iter_markets(run_dir, sports):
        tr_ts = np.sort(tr["ts"].to_numpy(float)) if len(tr) else np.empty(0)
        rec2 = {**rec, "fee_category": "other:sports_descriptive"}
        u, _ = select_a1(rec2, ts, vals, tr_ts, trunc, oldest, ctx)
        if u is not None:
            rows.append(attach_outcome(u, parse_outcome0(rec.get("outcome_prices")), ts, vals, ctx))
    d = usable(pd.DataFrame(rows)) if rows else pd.DataFrame()
    return {"note": "descriptive only (cb1_history_descriptive); sports end_at is game time", **(_mean_net(d) if len(d) else {"n": 0, "mean_net": None})}


def evaluate_c(f: pd.DataFrame, orders_all: pd.DataFrame, tid: str, stage: int, n_boot: int, n_placebo: int,
               excluded: list[dict], seed: int, ctx: Ctx) -> dict:
    """C1 / C2: queue-fill economic test plus the PX1 adverse-selection bound and secondaries."""
    f = f.reset_index(drop=True)
    r = evaluate_test(f, tid, stage=stage, n_boot=n_boot, n_placebo=n_placebo, seed=seed,
                      depth=f["Q0"].to_numpy(float) if len(f) else None)
    if not len(f):
        return r
    if "sensitivity" in r:
        r["sensitivity"]["missing_as_losing"] = missing_as_losing(f, c_tests(orders_all)[tid])
    sp = orders_all["category"].map(is_sports)
    pop = orders_all[sp if tid == "C2" else ~sp]
    filled = pop[pop["filled"].astype(bool)]
    unfilled = pop[~pop["filled"].astype(bool)]
    alpha_stage = 1 if stage == 1 else 2
    cap_hs = float((f["a"] - f["m_c"]).mean()) if "m_c" in f.columns else float("nan")
    ev_f, wk_f = filled["event"].astype(str).to_numpy(), filled["t"].map(lambda x: iso_week(x)).to_numpy()
    ev_u, wk_u = unfilled["event"].astype(str).to_numpy(), unfilled["t"].map(lambda x: iso_week(x)).to_numpy()
    r["px1"] = px1_bound(filled["drift24"].to_numpy(float), unfilled["drift24"].to_numpy(float), ev_f, ev_u, wk_f, wk_u, cap_hs, alpha_stage, n_boot=min(n_boot, N_BOOT), seed=seed)
    r["px1_clean"] = bool(r["px1"].get("clean"))
    r["decomposition"] = {"captured_half_spread": cap_hs, "resolution_excess": float((f["m_c"] - f["Y"]).mean()) if "m_c" in f.columns else None}
    pr = f["prior24"].to_numpy(float) if "prior24" in f.columns else np.full(len(f), np.nan)
    r["by_prior_24h_change"] = {
        "ge_0": _mean_net(f[pr >= 0]) if (pr >= 0).any() else {"n": 0}, "lt_0": _mean_net(f[pr < 0]) if (pr < 0).any() else {"n": 0}}
    r["market_equal_weight_mean"] = float(f.assign(_w=1.0 / f.groupby("market_id")["net"].transform("size")).pipe(lambda d: (d["net"] * d["_w"]).sum() / d["_w"].sum()))
    r["fill_rate_attempted"] = float(len(filled) / max(len(pop), 1))
    r["net_per_attempted_order"] = r["fill_rate_attempted"] * float(f["net"].mean())
    # touch / through fill rules (secondary): same orders, a looser fill
    for rule in ("touch", "through"):
        g = pop[pop[rule].astype(bool)]
        g = usable(g) if len(g) else g
        r[f"{rule}_rule"] = {"n": int(len(g)), "mean_net": float(g["net"].mean()) if len(g) else None}
    # rebate-optimistic (secondary): category share of the counterparty taker fee, pro rata
    reb = {"crypto": 0.20, "sports": 0.15}
    rb = np.array([reb.get(str(c).split(":")[0], 0.25) * taker_fee_ps(a, fee_rate(c)) for c, a in zip(f["category"], f["a"], strict=True)])
    r["rebate_optimistic_mean"] = float(f["net"].mean() + rb.mean())
    # worst case: excluded orders as filled losers
    ex = [e for e in excluded if (is_sports(e["category"]) == (tid == "C2"))]
    r["truncation"] = truncation_bound(f, ex, tid)
    r["advance_before_px1"] = r["advance"]
    r["advance"] = bool(r["advance"] and r["px1_clean"])
    r["verdict_cap"] = None if r["px1_clean"] else "inconclusive: adverse selection not excluded"
    return r

# =============================================================================================
# 10. Orchestration: h2 text fetch, books, screen / replicate / census / dry run
# =============================================================================================

GAMMA_BATCH = 20
BOOK_COLUMNS = ("market_id", "origin_ts", "state", "sw_best_bid", "sw_best_ask", "sw_bid_size_1", "sw_ask_size_1")


def results_name(families: list[str], replication: bool) -> str:
    return "results_cb1_" + "".join(sorted(families)) + ("_rep.json" if replication else ".json")


def parse_families(spec: str) -> list[str]:
    fams = [x.strip().upper() for x in spec.split(",") if x.strip()]
    bad = [f for f in fams if f not in FAMILY_TESTS]
    if bad or not fams:
        raise Refused(f"unknown CB1 history family {bad or spec!r} (declared: {sorted(FAMILY_TESTS)})")
    return sorted(set(fams))


def make_ctx(run_dir: Path) -> Ctx:
    forbid_run(Path(run_dir).name)
    t = request_clock(Path(run_dir))
    is_h5 = Path(run_dir).name.startswith("h5")
    lb = LOOKBACK_D
    if not is_h5:  # the run's own frame lookback (a longer rule would be vacuous, a shorter one is the frame's limit)
        man = load_manifest(run_dir)
        raw = man.get("lookback_days")
        if raw is None and isinstance(man.get("params"), dict):
            raw = man["params"].get("lookback_days")  # history manifests store it under params
        try:
            lb = float(raw)
        except (TypeError, ValueError):
            raise Refused(f"{run_dir}: manifest has no usable lookback_days ({raw!r}); h2 completeness needs it "
                          "(no fallback to 450)") from None
        if not math.isfinite(lb) or lb <= 0:
            raise Refused(f"{run_dir}: manifest lookback_days {raw!r} is not a positive number")
    return Ctx(run_id=Path(run_dir).name, t_fetch=t, t_censor=t, is_h5=is_h5, lookback_d=lb)


def load_books(path: Path) -> pd.DataFrame:
    """pmxt book table (6h grid); fails closed on a missing file or column."""
    path = Path(path)
    if not path.exists():
        raise Refused(f"book table {path} not found (CB1-C needs the pmxt book build)")
    b = pd.read_csv(path, dtype={"market_id": str})
    miss = [c for c in BOOK_COLUMNS if c not in b.columns]
    if miss:
        raise Refused(f"book table {path} lacks columns {miss}")
    b["origin_ts"] = b["origin_ts"].astype(float)
    return b


def fetch_text(run_dir: Path, transport, *, rps: float = 4.0, live_check=None, spec_path: Path = SPEC_PATH,
               require_committed: bool = True, sleep=None) -> dict:
    """q0019 step 1: question text and outcome labels for the sampled markets (Gamma ``/markets?id=``, metadata only).
    Refuses unless the E3 text-rule hash is committed first and never overwrites ``cb1/text.csv.gz``."""
    run_dir = Path(run_dir)
    forbid_run(run_dir.name)
    require_e3_hash_committed(spec_path, require_committed=require_committed)
    out = run_dir / "cb1" / "text.csv.gz"
    if out.exists():
        raise Refused(f"{out} exists (never overwritten)")
    ids = list(pd.read_csv(run_dir / "sample.csv.gz", usecols=["market_id"], dtype=str)["market_id"])
    kw = {} if sleep is None else {"sleep": sleep}
    lim = hb.Limiter(transport, rps=rps, live_check=live_check, **kw)
    got: dict[str, tuple[str, str]] = {}
    for i in range(0, len(ids), GAMMA_BATCH):
        chunk = ids[i : i + GAMMA_BATCH]
        status, data = lim.get(hb.GAMMA_MARKETS, {"id": chunk, "limit": len(chunk)})
        if status != 200 or not isinstance(data, list):
            continue
        for m in data:
            if isinstance(m, dict) and m.get("id") is not None:
                got[str(m["id"])] = (str(m.get("question") or "")[:300], str(m.get("outcomes") or "")[:200])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["market_id", "question", "outcomes"])
    for mid in ids:
        q, o = got.get(mid, ("", ""))
        w.writerow([mid, q, o])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))
    tmp.replace(out)
    return {"n_markets": len(ids), "n_text": len(got), "n_missing_text": len(ids) - len(got), "requests": lim.requests,
            "path": str(out)}


def header(ctx: Ctx, families: list[str], stage: int, extra: dict | None = None) -> dict:
    try:
        from . import battery2

        cum = battery2.cumulative_count()["total"]
    except Exception as exc:  # unknown kinds in trials.jsonl must not block a run; recorded instead
        cum = f"unavailable: {type(exc).__name__}: {str(exc)[:120]}"
    return {
        "version": VERSION, "revision": REVISION_R if stage == 2 else REVISION, "evidence_role": EVIDENCE_ROLE,
        "label": "EXPLORATORY", "run_id": ctx.run_id, "families": families, "stage": stage,
        "declaration_sha256": declaration_sha256(), "e3_text_rule_sha256": e3_text_rule_sha256(),
        "lookback_days": ctx.lookback_d, "t_fetch_utc": hb.utc_iso(ctx.t_fetch), "t_censor_utc": hb.utc_iso(ctx.t_censor), "cumulative_count": cum,
        "interpretations": INTERPRETATIONS, "provenance": provenance.run_provenance(), "data_provenance": hb.PROVENANCE,
        "beyond_budget_note": "h2_main is worn far beyond its revision budget: every result on it is L1 at most, not naive"
        if ctx.run_id == "h2_main" else None,
        **(extra or {}),
    }


def pack(fr: FamilyResult) -> dict:
    return {"tests": fr.tests, "extras": fr.extras}


def census(run_dir: Path, books: pd.DataFrame | None = None, text_ok: bool = True, spec_path: Path = SPEC_PATH,
           require_committed: bool = True) -> dict:
    """Counts only. Refuses an h5 run (the census reads nothing from h5) and, because it reads h2 question text,
    refuses unless the E3 text-rule hash is committed."""
    run_dir = Path(run_dir)
    forbid_run(run_dir.name)
    if run_dir.name.startswith("h5"):
        raise Refused("the pre-freeze census reads nothing from h5")
    require_e3_hash_committed(spec_path, require_committed=require_committed)
    ctx = make_ctx(run_dir)
    return {**header(ctx, ["A", "C", "E"], 0), "census": census_counts(run_dir, ctx, books=books, text_ok=text_ok)}


def screen(run_dir: Path, families: list[str], *, books: pd.DataFrame | None = None, n_boot: int = N_BOOT,
           n_placebo: int = PLACEBO_DRAWS, h5_run_dir: Path | None = None, spec_path: Path = SPEC_PATH,
           seal_copy: Path = SEAL_COPY, require_committed: bool = True, max_markets: int | None = None) -> dict:
    """Stage-1 screen on h2_main. Fails closed: the committed declaration, the committed h5 seal copy and a verifying
    ``h5_cb1`` seal must all exist BEFORE any outcome is read."""
    run_dir = Path(run_dir)
    forbid_run(run_dir.name)
    if run_dir.name.startswith("h5"):
        raise Refused("screen runs on h2_main only; h5 is read by `replicate`")
    require_declaration(spec_path, require_committed=require_committed)
    require_seal_copy(seal_copy)
    h5 = Path(h5_run_dir) if h5_run_dir else run_dir.parent / "h5_cb1"
    require_sealed(h5, seal_copy)
    ctx = make_ctx(run_dir)
    out = {**header(ctx, families, 1), "tests": {}, "extras": {}}
    for fam in families:
        if fam == "C" and books is None:
            raise Refused("CB1-C needs the pmxt book table (q0003)")
        fr = evaluate_family(run_dir, fam, ctx, stage=1, books=books, n_boot=n_boot, n_placebo=n_placebo, max_markets=max_markets)
        out["tests"].update(fr.tests)
        out["extras"][fam] = fr.extras
    out["advanced"] = sorted(t for t, r in out["tests"].items() if r.get("advance"))
    return out


def replicate(run_dir: Path, from_results: dict, families: list[str], *, books: pd.DataFrame | None = None,
              n_boot: int = N_BOOT, n_placebo: int = PLACEBO_DRAWS, job: str = "run_cb1_history:replicate",
              spec_path: Path = SPEC_PATH, seal_copy: Path = SEAL_COPY, require_committed: bool = True,
              max_markets: int | None = None) -> dict | None:
    """Stage-2 frozen replication of the advanced tests on h5_cb1. Returns None (no h5 read) when nothing advanced.
    The seal is verified and the read is logged to ``ACCESS_LOG.jsonl`` before any h5 file is opened."""
    run_dir = Path(run_dir)
    forbid_run(run_dir.name)
    if not run_dir.name.startswith("h5_cb1") or run_dir.name.startswith("h5_cb1_ladders"):
        raise Refused(f"replicate reads h5_cb1 only, not {run_dir.name!r}")
    decl = require_declaration(spec_path, require_committed=require_committed)
    if from_results.get("declaration_sha256") != decl:
        raise Refused("the screen results were produced under a different declaration hash")
    adv = [t for t in from_results.get("advanced", []) if HYPOTHESES_CB1[t]["family"] in families]
    if not adv:
        return None
    require_sealed(run_dir, seal_copy)
    h5_access_log(run_dir, job, ["sample.csv.gz", "progress.jsonl", "prices/*.csv.gz", "trades/*.csv.gz", "cb1/*"], decl)
    ctx = make_ctx(run_dir)
    out = {**header(ctx, families, 2, {"advanced_from_screen": adv}), "tests": {}, "extras": {}}
    for fam in sorted({HYPOTHESES_CB1[t]["family"] for t in adv}):
        if fam == "C" and books is None:
            raise Refused("CB1-C replication needs the h5 pmxt book table (q0025)")
        fr = evaluate_family(run_dir, fam, ctx, stage=2, only=[t for t in adv if HYPOTHESES_CB1[t]["family"] == fam],
                             books=books, n_boot=n_boot, n_placebo=n_placebo, max_markets=max_markets, descriptive=False)
        out["tests"].update(fr.tests)
        out["extras"][fam] = fr.extras
    hm = holm({t: float(r.get("p", 1.0)) for t, r in out["tests"].items()}, ALPHA_STAGE2)
    out["holm_local"] = hm
    for t, r in out["tests"].items():
        r["replicated_provisional_per_run"] = bool(r.get("advance") and hm[t]["reject"])
    out["replicated_provisional_per_run"] = sorted(t for t, r in out["tests"].items() if r["replicated_provisional_per_run"])
    out["holm_note"] = "per-run Holm only; the binding CB1 verdict is the batch Holm over all Stage-2 tests (batch-holm)"
    return out


def write_results_and_log(out: dict, path: Path, *, replication: bool, trials_path: Path = provenance.TRIALS_PATH) -> None:
    """Write the results file (never overwritten) then one count line per family and one trial line per test."""
    write_new(path, out)
    for fam in out["families"] if not replication else sorted({HYPOTHESES_CB1[t]["family"] for t in out["tests"]}):
        sub = {"tests": {t: r for t, r in out["tests"].items() if HYPOTHESES_CB1[t]["family"] == fam},
               "cumulative_count": out.get("cumulative_count")}
        if sub["tests"]:
            log_trials(sub, path, replication=replication, family=fam, dataset=out["run_id"], trials_path=trials_path)


def log_descriptive(path: Path, label: str, dataset: str, trials_path: Path = provenance.TRIALS_PATH) -> None:
    provenance.append_trial({
        "kind": TRIAL_KIND_D, "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE, "revision": REVISION, "dataset": dataset,
        "note": label, "results_sha256": provenance.sha256_file(path), "declaration_sha256": declaration_sha256(),
    }, trials_path)
