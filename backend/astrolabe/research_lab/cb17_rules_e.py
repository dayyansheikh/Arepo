# ruff: noqa: E501
"""CB17 rules part ``E`` (docs/research_lab/CREATIVE_BATCH_17.md section CB17-E, 11.5): first-day prints (CH154). A CENSUS ONLY: k = 0, no counted test is declared.

The first-day rule, the census counts (q0408 on SCREEN_8 features; q0400 on worn data) and the declared re-entry rule that decides whether a LATER batch may register a counted CH154
test on a fresh window. Under branch T (section 11.1) q0407 builds E's features only: every non-sports monitor transaction (no sign needed) and the CB13-T touch-consistent fills (the
signable population, pins). O1 ruling (amended): the re-entry COUNTS bind on the signable (touch-consistent) population a CH154 test would use, as does the proxy MDE; the counts on all
non-sports transactions are reported only (a stricter, non-binding view).
"""

from __future__ import annotations

import math

from . import cb17_census as cen
from . import cb17_common as c17
from . import cb17_pre as pre

Refused = c17.Refused

E_VERSION = "cb17-E-v1"
FIRST_DAY_H = pre.FIRST_DAY_S / 3600.0  # first day = market age at tau under 24 h
LATER_H = (24.0, 168.0)  # later = 1-7 d; > 7 d, negative and unknown ages are in neither group
REENTRY_MIN_TX = 400
REENTRY_MIN_MARKETS = 150
REENTRY_MDE_MAX_C = 1.0
REENTRY_SPREAD_FREE = "the later design must make the spread-free mark binding"
POPULATION_COUNTS = "the CB13-T touch-consistent fills (the signable population under branch T): non-sports first-day transactions and markets with first-day and later transactions"
POPULATION_MDE = "the CB13-T touch-consistent fills (the signable population under branch T)"
POPULATION_REPORTED = "all non-sports monitor transactions with a single condition id (unsigned; branch T reads no side): the same counts, REPORTED ONLY (never decide the verdict)"
POPULATION_RULE = "O1 amended: re-entry counts and the proxy MDE bind on the signable (touch-consistent) population; the counts on all transactions are reported only"
CREATED_RULE = "sidecar created_at of the latest capture before tau or, for a market not yet captured, the first capture after tau (a static attribute)"
CENSUS_COUNTS = ("first-day transactions by fill source, class, sports and hour", "markets and events with both first-day and later (1-7 d) transactions", "the share unsignable for lack of a touch",
                 "a feature-proxy SE of the within-market contrast on the pre-fill proxy (SE only)")
VERDICT_ALLOWED = "re-entry allowed on a fresh window"
VERDICT_DENIED = "not testable at the floor with host data"


def market_age_h(tau: float, created_epoch: float) -> float:
    return (float(tau) - float(created_epoch)) / 3600.0 if math.isfinite(float(tau)) and math.isfinite(float(created_epoch)) else math.nan


def age_group(age_h: float) -> str | None:
    """'first' (0 <= age < 24 h), 'later' (24 h <= age < 168 h), else None (part pre's first-day bins: q0400 ``age_bin_first_day``)."""
    if not math.isfinite(age_h):
        return None
    b = cen.age_bin_first_day(age_h)
    return "first" if b in ("lt6h", "6-24h") else "later" if b == "1-7d" else None


def reentry_verdict(n_first_tx: int, n_markets_first_and_later: int, proxy_mde_c: float | None) -> dict:
    """The declared re-entry rule (section CB17-E): >= 400 non-sports first-day transactions in >= 150 markets that also print on days 2-7, and a proxy MDE <= 1.0c (and the later design
    makes the spread-free mark binding). Otherwise CH154 is 'not testable at the floor with host data'."""
    mde_ok = proxy_mde_c is not None and math.isfinite(float(proxy_mde_c)) and float(proxy_mde_c) <= REENTRY_MDE_MAX_C
    ok = n_first_tx >= REENTRY_MIN_TX and n_markets_first_and_later >= REENTRY_MIN_MARKETS and mde_ok
    return {"first_day_transactions": int(n_first_tx), "markets_first_and_later": int(n_markets_first_and_later), "proxy_mde_c": proxy_mde_c, "pass": bool(ok),
            "verdict": VERDICT_ALLOWED if ok else VERDICT_DENIED, "condition": REENTRY_SPREAD_FREE}


def declared() -> dict:
    return {"version": E_VERSION, "k": 0, "first_day": {"rule": f"market age at tau < {FIRST_DAY_H:g} h", "later": f"{LATER_H[0]:g}-{LATER_H[1]:g} h", "created_at": CREATED_RULE},
            "census": list(CENSUS_COUNTS), "populations": {"counts": POPULATION_COUNTS, "mde": POPULATION_MDE, "reported_only": POPULATION_REPORTED, "rule": POPULATION_RULE},
            "reentry": {"min_first_day_transactions": REENTRY_MIN_TX, "min_markets_first_and_later": REENTRY_MIN_MARKETS, "proxy_mde_max_c": REENTRY_MDE_MAX_C, "condition": REENTRY_SPREAD_FREE,
                        "pass": VERDICT_ALLOWED, "fail": VERDICT_DENIED},
            "worn_inputs_q0400": {"T_units_by_age": {"lt6h": 2, "6-24h": 26, "1-7d": 106, "gt7d": 811, "unknown": 12}, "T_markets_first_and_later": 7, "non_sports_transactions_first_day": 200,
                                  "E_T_proxy_mde_c": 0.392125, "result_sha256": "9deedcf5a1aeb0e370796457cab3f933d8e4c6b59e6a5de302c9a70e82ec38cf"}}
