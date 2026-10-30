# ruff: noqa: E501
"""Unified paper execution-cost model for AREPO cost checks (development tool; AREPO never trades).

Every future "cost check" should price a candidate through this module so that the taker, maker and
hold-to-resolution alternatives use one fee table, one book walk and one documented set of maker
assumptions. Reference: ``docs/research_lab/COST_MODEL.md`` (assumptions, sources, calibration).

Units (everywhere in this module)
---------------------------------
* ``price``, ``mid``, ``spread`` and every ``*_ps`` value: probability units per share, i.e. USDC per
  share of a binary outcome token (1 cent = 0.01). Multiply by 100 for cents.
* ``shares``: outcome-token shares. ``notional``: USDC (= shares * price).
* ``rate``: the taker fee rate ``r`` of ``fee = C * r * p * (1 - p)`` (``C`` shares, ``p`` price).
* times: seconds (``*_s``) or hours (``*_h``) as named.

Status
------
Paper model, "optimistic, not tradable". Fee and rebate tables are facts from the official
docs (see ``FEE_SOURCES``); the latency haircut and every maker parameter are ASSUMPTIONS or
development estimates (``MAKER_DEFAULTS`` carries its provenance). Nothing here relabels a past
verdict: past outcomes stand, and a re-check of a closed candidate needs its own registered design.

All functions are pure (no I/O, no globals mutated). Constants are module-level and documented.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

# =============================================================================================
# 0. Fee and rebate facts (official docs; see COST_MODEL.md section 2 for quotes and dates)
# =============================================================================================

FEE_SOURCES = {
    "fees": "https://docs.polymarket.com/trading/fees",
    "maker_rebates": "https://docs.polymarket.com/programs/maker-rebates",
    "taker_rebates": "https://docs.polymarket.com/programs/taker-rebates",
    "liquidity_rewards": "https://docs.polymarket.com/programs/liquidity-rewards",
    "market_fields": "https://docs.polymarket.com/market-data/market-details",
    "changelog": "https://docs.polymarket.com/changelog",
    "retrieved": "2026-10-19 (fees page last updated 2026-07-10; table first retrieved 2026-10-11 in economics.py)",
}

# Taker fee rate by fee category. Identical to ``economics.DOCS_CATEGORY_RATE`` (a unit test pins
# the equality so the two tables cannot drift). Makers pay no fee.
CATEGORY_TAKER_RATE: dict[str, float] = {
    "crypto": 0.07,
    "sports": 0.05, "economics": 0.05, "culture": 0.05, "weather": 0.05, "other": 0.05,
    "finance": 0.04, "politics": 0.04, "mentions": 0.04, "tech": 0.04,
    "geopolitics": 0.0,
}
MAX_TAKER_RATE = max(CATEGORY_TAKER_RATE.values())

# Share of the taker fees paid in a market that is redistributed to that market's makers
# (identical to ``economics.REBATE_SHARE``; pinned by a test).
CATEGORY_REBATE_SHARE: dict[str, float] = {
    "crypto": 0.20, "sports": 0.15, "finance": 0.25, "politics": 0.25, "economics": 0.25,
    "culture": 0.25, "weather": 0.25, "other": 0.25, "mentions": 0.25, "tech": 0.25,
    "geopolitics": 0.0,
}

# The rebate is a pool shared pro rata among the makers whose liquidity was taken; one maker's
# expected rebate per filled share is not the full share. ASSUMPTION: half of the formula value
# (the CB3 convention, cb3_declaration.MAKER rebate halving). 0 is the most conservative value.
REBATE_POOL_HAIRCUT = 0.5

FEE_POLICIES = ("schedule", "conservative", "docs")


def category_key(category: object) -> str:
    """``'politics:us'`` -> ``'politics'``; None/NaN/empty -> ``''``."""
    if category is None or (isinstance(category, float) and math.isnan(category)):
        return ""
    return str(category).split(":")[0].strip().lower()


def taker_rate(category: object = None, schedule_rate: float | None = None,
               fees_enabled: bool | None = None, policy: str = "conservative") -> float:
    """Taker fee rate ``r`` for one market.

    * ``fees_enabled is False`` -> 0 (fees switched off for the market).
    * ``policy='schedule'``: the per-market Gamma ``feeSchedule.rate`` when known, else the docs rate.
    * ``policy='docs'``: the docs category rate.
    * ``policy='conservative'`` (default for cost checks): ``max(schedule, docs)``.
    * Unknown category and no schedule -> ``MAX_TAKER_RATE`` (0.07), never 0.
    """
    if policy not in FEE_POLICIES:
        raise ValueError(f"policy must be one of {FEE_POLICIES}")
    if fees_enabled is False:
        return 0.0
    docs = CATEGORY_TAKER_RATE.get(category_key(category), math.nan)
    sched = math.nan if schedule_rate is None else float(schedule_rate)
    if not math.isfinite(sched) or sched < 0:
        sched = math.nan
    if policy == "docs":
        cands = [docs]
    elif policy == "schedule":
        cands = [sched] if not math.isnan(sched) else [docs]
    else:
        cands = [docs, sched]
    cands = [c for c in cands if not math.isnan(c)]
    return max(cands) if cands else MAX_TAKER_RATE


def taker_fee_ps(price: float, rate: float, exponent: float = 1.0) -> float:
    """Taker fee per share, ``rate * (p (1 - p)) ** exponent`` (USDC/share, unrounded).

    The venue rounds the per-order fee to 5 decimals of USDC; per share that is immaterial at the
    sizes modelled here and is not applied."""
    p = min(max(float(price), 0.0), 1.0)
    return float(rate) * (p * (1.0 - p)) ** float(exponent)


def maker_rebate_ps(price: float, category: object, rate: float | None = None,
                    pool_haircut: float = REBATE_POOL_HAIRCUT, rebate_share: float | None = None) -> float:
    """Expected maker rebate per FILLED share: ``share * taker_fee_ps(p, r) * haircut``.

    ``rate`` defaults to the docs rate of the category; ``rebate_share`` defaults to the docs share
    (pass the per-market ``feeSchedule.rebateRate`` when known). Unknown category -> 0 (no rebate
    claimed). The docs rebate is ``(own fee-equivalent / total fee-equivalent) * pool``; the pool is
    the share times the taker fees actually collected in the market, so a filled maker share earns
    about ``share * fee`` only if every maker fill in that market paid an equivalent taker fee."""
    key = category_key(category)
    share = CATEGORY_REBATE_SHARE.get(key, 0.0) if rebate_share is None else float(rebate_share)
    r = CATEGORY_TAKER_RATE.get(key, 0.0) if rate is None else float(rate)
    return share * taker_fee_ps(price, r) * float(pool_haircut)


# =============================================================================================
# 1. Book representation and walk
# =============================================================================================

Level = tuple[float, float]  # (price, shares), best first, on the side a taker consumes


def _tick_round(price: float, tick: float | None, up: bool) -> float:
    if not tick or tick <= 0:
        return price
    n = price / tick
    n = math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)
    return round(n * tick, 10)


def levels_from_summary(best: float, size1: float, depth_1c: float | None = None,
                        depth_5c: float | None = None, *, lift_asks: bool,
                        tick: float | None = 0.01) -> list[Level]:
    """Conservative levels from a ``book_sweep`` row (touch size, cumulative depth within 1c and 5c,
    both inclusive of the touch). Each band beyond the touch is priced at its OUTER edge (best +/- 1c,
    best +/- 5c), so a walk on it is an upper bound on cost. Same expansion as
    ``economics.side_levels``. Empty list if the side is missing."""
    if best is None or size1 is None or not (math.isfinite(best) and math.isfinite(size1)) or size1 <= 0:
        return []
    d1 = size1 if depth_1c is None or not math.isfinite(depth_1c) else max(float(depth_1c), size1)
    d5 = d1 if depth_5c is None or not math.isfinite(depth_5c) else max(float(depth_5c), d1)
    sgn = 1.0 if lift_asks else -1.0
    lv: list[Level] = [(float(best), float(size1))]
    for extra, width in ((d1 - size1, 0.01), (d5 - d1, 0.05)):
        if extra > 1e-12:
            lv.append((_tick_round(float(best) + sgn * width, tick, up=lift_asks), extra))
    return lv


@dataclass(frozen=True)
class Walk:
    """Result of consuming ``levels`` for a target size."""

    target_shares: float
    filled_shares: float
    cash: float  # USDC paid (buy) or received (sell) for the filled shares, before fees
    vwap: float  # NaN if nothing filled
    best: float  # touch price (NaN if empty)
    worst: float  # last level touched (NaN if empty)
    exhausted: bool  # True if the recorded depth could not fill the target

    @property
    def impact_ps(self) -> float:
        """|vwap - touch| per filled share (probability units)."""
        return abs(self.vwap - self.best) if self.filled_shares > 0 else math.nan


def walk(levels: Sequence[Level], shares: float | None = None, notional: float | None = None) -> Walk:
    """Consume ``levels`` (best first) for ``shares`` OR a USDC ``notional`` (exactly one)."""
    if (shares is None) == (notional is None):
        raise ValueError("give exactly one of shares / notional")
    if not levels:
        tgt = float(shares) if shares is not None else math.nan
        return Walk(tgt, 0.0, 0.0, math.nan, math.nan, math.nan, True)
    got = cash = 0.0
    worst = levels[0][0]
    if shares is not None:
        need = float(shares)
        for p, s in levels:
            take = min(need - got, s)
            if take <= 0:
                break
            got += take
            cash += take * p
            worst = p
        tgt = float(shares)
        exhausted = got < tgt - 1e-9
    else:
        budget = float(notional)
        for p, s in levels:
            room = budget - cash
            if room <= 1e-12:
                break
            take = min(s, room / p) if p > 0 else s
            got += take
            cash += take * p
            worst = p
        tgt = got if cash >= budget - 1e-9 else math.nan
        exhausted = cash < budget - 1e-9
    vwap = cash / got if got > 0 else math.nan
    return Walk(tgt, got, cash, vwap, levels[0][0], worst, exhausted)


def depth_notional_within(levels: Sequence[Level], width: float) -> float:
    """USDC available within ``width`` of the touch (inclusive)."""
    if not levels:
        return 0.0
    best = levels[0][0]
    return sum(p * s for p, s in levels if abs(p - best) <= width + 1e-12)


# =============================================================================================
# 2. Taker legs, staleness haircut and round trips
# =============================================================================================


def staleness_haircut_ps(latency_s: float, sigma_1h: float, kappa: float = 0.4) -> float:
    """Expected extra cost per share of acting on a quote ``latency_s`` old.

    ``sigma_1h``: SD of the mid change over one hour (probability units). The mid moves by about
    ``sigma_1h * sqrt(latency_s / 3600)`` during the delay; ``kappa`` is the fraction of that SD the
    taker loses on average. ASSUMPTION: kappa = 0.4 (about E|Z|/2 = 0.399 for a normal move, i.e.
    the move is as likely against as for the signal, and the trader still trades when it moved
    against). Signals that are themselves stale-quote artefacts need a larger haircut."""
    if latency_s <= 0 or sigma_1h <= 0:
        return 0.0
    return float(kappa) * float(sigma_1h) * math.sqrt(float(latency_s) / 3600.0)


@dataclass(frozen=True)
class LegCost:
    """Cost of one taker leg per filled share, relative to the mid (all probability units)."""

    half_spread_ps: float
    impact_ps: float
    fee_ps: float
    staleness_ps: float
    filled_shares: float
    exhausted: bool
    flags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def total_ps(self) -> float:
        return self.half_spread_ps + self.impact_ps + self.fee_ps + self.staleness_ps


def taker_leg(levels: Sequence[Level], mid: float, *, shares: float | None = None,
              notional: float | None = None, rate: float = MAX_TAKER_RATE,
              latency_s: float = 0.0, sigma_1h: float = 0.0, kappa: float = 0.4) -> LegCost:
    """One taker leg (buy lifts asks or sell hits bids; ``levels`` is the consumed side, best first)."""
    w = walk(levels, shares=shares, notional=notional)
    flags: list[str] = []
    if w.filled_shares <= 0:
        return LegCost(math.nan, math.nan, math.nan, math.nan, 0.0, True, ("empty_side",))
    if w.exhausted:
        flags.append("depth_exhausted")
    hs = abs(w.best - mid) if math.isfinite(mid) else math.nan
    if not math.isfinite(mid):
        flags.append("no_mid")
    return LegCost(hs, w.impact_ps, taker_fee_ps(w.vwap, rate), staleness_haircut_ps(latency_s, sigma_1h, kappa),
                   w.filled_shares, w.exhausted, tuple(flags))


def round_trip_from_quote(mid: float, spread: float, rate: float, *, impact_ps: float = 0.0,
                          staleness_ps: float = 0.0, exit_mode: str = "taker",
                          exit_price: float | None = None) -> dict[str, float]:
    """Round-trip cost per share from a quote summary (no book walk).

    ``exit_mode``: ``'taker'`` (enter and exit by crossing: full spread, two fees, impact and
    staleness on both legs), ``'resolution'`` (enter by crossing, hold to resolution: one
    half-spread, one fee, no exit cost; redemption of a resolved share has no trading fee).
    ``exit_price`` is the price the exit fee is charged at (default ``mid``)."""
    if exit_mode not in ("taker", "resolution"):
        raise ValueError(exit_mode)
    h = spread / 2.0
    entry_fee = taker_fee_ps(min(mid + h, 1.0), rate)
    if exit_mode == "resolution":
        out = {"half_spread_ps": h, "impact_ps": impact_ps, "fee_ps": entry_fee, "staleness_ps": staleness_ps}
    else:
        xp = mid if exit_price is None else exit_price
        exit_fee = taker_fee_ps(max(xp - h, 0.0), rate)
        out = {"half_spread_ps": 2 * h, "impact_ps": 2 * impact_ps, "fee_ps": entry_fee + exit_fee,
               "staleness_ps": 2 * staleness_ps}
    out["total_ps"] = sum(out.values())
    return out


# =============================================================================================
# 3. Maker model (conservative; parameters are development estimates with uncertainty)
# =============================================================================================


def fill_probability(queue_ahead_shares: float, own_shares: float, p_active: float,
                     scale_shares: float, alpha: float) -> float:
    """P(a resting order at the touch fills completely within the horizon), queue-back rule.

    Model: with probability ``p_active`` at least one taker trade hits the order's price level (or
    trades through it) within the horizon. Given that, the effective hitting volume has a Lomax
    (Pareto II) survival ``(1 + x / scale) ** -alpha``; the order fills when it exceeds the queue
    ahead plus the order's own size:

        P = p_active * (1 + (Q + q) / scale_shares) ** -alpha

    Trades through the price fill the order whatever the queue, which is why the tail is heavy
    (calibrated alpha about 0.2-0.3). Cancellations ahead of the order, which would help it, are
    ignored, so the rule is conservative given the inputs. An exponential survival was rejected in
    calibration (it mis-ranked short and long queues). Parameters per liquidity tier and horizon:
    ``MAKER_DEFAULTS['tiers']``."""
    if p_active <= 0 or scale_shares <= 0 or alpha < 0:
        return 0.0
    q = max(float(queue_ahead_shares), 0.0) + max(float(own_shares), 0.0)
    return min(float(p_active), 1.0) * (1.0 + q / float(scale_shares)) ** (-float(alpha))


@dataclass(frozen=True)
class MakerLeg:
    """Passive entry at the own-side touch, then the named exit, per share.

    ``fill_conditioning_ps``: how far the mark-referenced move on FILLED orders falls short of the
    signal's unconditional gross. Under 'fill independent of the signal' it equals the unconditional
    adverse selection of a filled touch order (half-spread minus realised spread); for a directional
    signal it is larger, because the orders that fill are those the price moved against.

    ``net_per_fill_ps = gross + half_spread - fill_conditioning + rebate - exit_cost``;
    ``net_per_attempt_ps = p_fill * net_per_fill_ps`` (an unfilled order costs nothing and forgoes
    the signal)."""

    p_fill: float
    gross_ps: float
    half_spread_ps: float
    fill_conditioning_ps: float
    rebate_ps: float
    exit_cost_ps: float

    @property
    def net_per_fill_ps(self) -> float:
        return (self.gross_ps + self.half_spread_ps - self.fill_conditioning_ps
                + self.rebate_ps - self.exit_cost_ps)

    @property
    def net_per_attempt_ps(self) -> float:
        return self.p_fill * self.net_per_fill_ps

    @property
    def breakeven_gross_ps(self) -> float:
        """Gross per filled share needed for ``net_per_fill_ps = 0``."""
        return self.fill_conditioning_ps + self.exit_cost_ps - self.half_spread_ps - self.rebate_ps


def maker_entry(*, p_fill: float, gross_ps: float, half_spread_ps: float, fill_conditioning_ps: float,
                rebate_ps: float = 0.0, exit_cost_ps: float = 0.0) -> MakerLeg:
    """Assemble a maker leg (all inputs per share, probability units)."""
    return MakerLeg(float(p_fill), float(gross_ps), float(half_spread_ps), float(fill_conditioning_ps),
                    float(rebate_ps), float(exit_cost_ps))


def fill_conditioning(adverse_selection_ps: float, scenario: str = "conservative") -> float:
    """Fill-conditioning term for a maker leg.

    ``'independent'`` (optimistic, must be labelled): the tier's unconditional adverse selection.
    ``'conservative'`` (default): ``max(tier adverse selection, MAKER_DEFAULTS
    ['flow_fill_conditioning_ps'])``, the only historical signal-conditional estimate (flow
    signals). Neither is a measurement for a NEW signal; a registered design must measure its own."""
    if scenario == "independent":
        return float(adverse_selection_ps)
    if scenario == "conservative":
        return max(float(adverse_selection_ps), float(MAKER_DEFAULTS["flow_fill_conditioning_ps"]))  # type: ignore[arg-type]
    raise ValueError(scenario)


# Development estimates, per share in probability units, horizon 1 h, order of 5 shares joining the
# back of the touch queue. Source: scripts/cost_model_calibration.py on development book sweeps +
# trade samples 2026-10-16T04Z..2026-10-19T00Z (34 origins, 128,742 hypothetical orders, 22,293
# markets); 95% CIs are event-cluster bootstrap. Full output:
# model_specs/cost_model_calibration_v1.json; discussion: docs/research_lab/COST_MODEL.md section 4.
# ``flow_fill_conditioning_ps``: ECONOMIC_CONDITIONS_STUDY.md part B (pmxt history 2026-04..08, flow
# signal, queue rule, 2h): filled mean move -2.30c vs unfilled +0.51c -> 2.81c.
MAKER_DEFAULTS: dict[str, object] = {
    "version": "cost-model-v1",
    "horizon_h": 1.0,
    "own_shares": 5.0,
    "flow_fill_conditioning_ps": 0.0281,
    "tiers": {
        "<1k": {"p_active": 0.0408, "scale_shares": 2.721, "alpha": 0.2622,
                "p_fill": 0.0187, "p_fill_ci95": (0.0170, 0.0205),
                "adverse_selection_ps": 0.0387, "adverse_selection_ci95": (0.0320, 0.0466),
                "half_spread_median_ps": 0.020, "realised_spread_filled_ps": -0.0192},
        "1k-10k": {"p_active": 0.0899, "scale_shares": 1.823, "alpha": 0.2021,
                   "p_fill": 0.0433, "p_fill_ci95": (0.0391, 0.0474),
                   "adverse_selection_ps": 0.0245, "adverse_selection_ci95": (0.0219, 0.0270),
                   "half_spread_median_ps": 0.010, "realised_spread_filled_ps": -0.0117},
        "10k-100k": {"p_active": 0.0804, "scale_shares": 3.325, "alpha": 0.2404,
                     "p_fill": 0.0286, "p_fill_ci95": (0.0263, 0.0313),
                     "adverse_selection_ps": 0.0204, "adverse_selection_ci95": (0.0176, 0.0231),
                     "half_spread_median_ps": 0.0075, "realised_spread_filled_ps": -0.0123},
        ">=100k": {"p_active": 0.2631, "scale_shares": 6.062, "alpha": 0.3401,
                   "p_fill": 0.0341, "p_fill_ci95": (0.0268, 0.0423),
                   "adverse_selection_ps": 0.0039, "adverse_selection_ci95": (-0.0001, 0.0065),
                   "half_spread_median_ps": 0.005, "realised_spread_filled_ps": -0.0005},
    },
}

LIQ_EDGES = (1e3, 1e4, 1e5)
LIQ_LABELS = ("<1k", "1k-10k", "10k-100k", ">=100k")


def liquidity_tier(liquidity: float | None) -> str:
    """Gamma ``liquidity`` (USDC) -> tier label, same edges as ``economics.LIQ_EDGES``. Missing -> '<1k'."""
    try:
        x = float(liquidity) if liquidity is not None else 0.0
    except (TypeError, ValueError):
        x = 0.0
    if not math.isfinite(x):
        x = 0.0
    for edge, lab in zip(LIQ_EDGES, LIQ_LABELS, strict=False):
        if x < edge:
            return lab
    return LIQ_LABELS[-1]


def maker_tier(liquidity: float | None, tiers: dict | None = None) -> dict:
    """Calibrated 1 h maker parameters for a market's Gamma ``liquidity`` (USDC)."""
    t = tiers if tiers is not None else MAKER_DEFAULTS["tiers"]
    return dict(t[liquidity_tier(liquidity)])  # type: ignore[index]


# =============================================================================================
# 4. The standard cost check
# =============================================================================================


@dataclass(frozen=True)
class CostCheck:
    """Standard output of :func:`cost_check` (probability units per share unless named)."""

    gross_ps: float
    taker_round_trip_ps: float
    taker_net_ps: float
    taker_resolution_cost_ps: float
    maker_net_per_fill_ps: float
    maker_net_per_attempt_ps: float
    maker_p_fill: float
    maker_breakeven_gross_ps: float
    label: str = "development cost check (paper; optimistic, not tradable)"
    assumptions: dict = field(default_factory=dict)

    @property
    def taker_breakeven_gross_ps(self) -> float:
        return self.taker_round_trip_ps

    def cents(self) -> dict[str, float]:
        """The numeric fields in cents (for reports)."""
        keys = ("gross_ps", "taker_round_trip_ps", "taker_net_ps", "taker_resolution_cost_ps",
                "maker_net_per_fill_ps", "maker_net_per_attempt_ps", "maker_breakeven_gross_ps")
        return {k.replace("_ps", "_c"): round(100 * getattr(self, k), 4) for k in keys}


def cost_check(gross_ps: float, *, mid: float, spread: float, category: object = None,
               schedule_rate: float | None = None, fees_enabled: bool | None = None,
               liquidity: float | None = None, impact_ps: float = 0.0, latency_s: float = 0.0,
               sigma_1h: float = 0.0, maker_scenario: str = "conservative", maker_exit: str = "taker",
               maker: dict | None = None) -> CostCheck:
    """Price a candidate's gross per-share edge under taker and maker execution.

    ``gross_ps``: mean mid-to-mid move per share in the signal's direction over the signal's horizon
    (the quantity battery/screen economics report as 'gross'). ``impact_ps``: walk impact per leg
    beyond the touch (use :func:`walk` on the book for the intended size; 0 = touch fill).
    ``taker_resolution_cost_ps`` is the cost of entering by crossing and holding to resolution (one
    half-spread, one fee); it is reported as a cost only, because a gross measured at a fixed horizon
    is not a hold-to-resolution gross. Maker: entry at the own-side touch with the tier's 1 h fill
    probability, ``maker_scenario`` 'conservative' (default) or 'independent' (optimistic, label it),
    exit by crossing (``maker_exit='taker'``) or ``'resolution'`` (no exit cost; same caveat)."""
    if maker_exit not in ("taker", "resolution"):
        raise ValueError(maker_exit)
    rate = taker_rate(category, schedule_rate, fees_enabled, "conservative")
    st = staleness_haircut_ps(latency_s, sigma_1h)
    rt = round_trip_from_quote(mid, spread, rate, impact_ps=impact_ps, staleness_ps=st)
    rr = round_trip_from_quote(mid, spread, rate, impact_ps=impact_ps, staleness_ps=st, exit_mode="resolution")
    mk = maker if maker is not None else maker_tier(liquidity)
    h = spread / 2.0
    exit_cost = (h + taker_fee_ps(max(mid - h, 0.0), rate) + impact_ps + st) if maker_exit == "taker" else 0.0
    fc = fill_conditioning(float(mk["adverse_selection_ps"]), maker_scenario)
    ml = maker_entry(p_fill=float(mk["p_fill"]), gross_ps=gross_ps, half_spread_ps=h, fill_conditioning_ps=fc,
                     rebate_ps=maker_rebate_ps(mid, category, rate), exit_cost_ps=exit_cost)
    return CostCheck(gross_ps, rt["total_ps"], gross_ps - rt["total_ps"], rr["total_ps"],
                     ml.net_per_fill_ps, ml.net_per_attempt_ps, ml.p_fill, ml.breakeven_gross_ps,
                     assumptions={"rate": rate, "fee_policy": "conservative", "staleness_ps": st,
                                  "impact_ps_per_leg": impact_ps, "maker_scenario": maker_scenario,
                                  "fill_conditioning_ps": fc, "maker_exit": maker_exit,
                                  "maker_tier": liquidity_tier(liquidity) if maker is None else "given",
                                  "rebate_pool_haircut": REBATE_POOL_HAIRCUT,
                                  "version": MAKER_DEFAULTS["version"]})
