"""Build honest, non-personalised research alert content from an Opportunity card.

Wording rules (spec section 10): a practical directional interpretation is allowed, but never
a promise of profit, never certainty, never personalised advice, and never "buy", "sell" or a
specific stake. Every alert ends with a research disclaimer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..opportunity.schemas import OpportunityCard

DISCLAIMER = (
    "This is a research signal, not financial advice. Review the market and risks yourself "
    "before making any decision."
)


@dataclass
class AlertContent:
    subject: str
    text: str


def _app_base() -> str:
    return os.environ.get("AREPO_APP_BASE", "http://localhost:3000").rstrip("/")


def _lede(direction: str | None) -> str:
    if direction == "up":
        return (
            "Strong signals suggest this market may be repricing upwards. Have a look yourself "
            "and review the evidence before acting."
        )
    if direction == "down":
        return (
            "Several independent indicators suggest downward pressure may be building. Have a "
            "look yourself and check whether the move is continuing."
        )
    return (
        "Several independent indicators are firing on this market. Have a look yourself and "
        "review the evidence before drawing any conclusion."
    )


def build_alert(card: OpportunityCard) -> AlertContent:
    """Compose the subject and plain-text body for a research alert about ``card``."""
    outcome = card.outcome or "the leading outcome"
    prob = f"{card.probability * 100:.0f}%" if card.probability is not None else "n/a"
    tags = ", ".join(t.label for t in card.tags) or "composite anomaly"
    link = f"{_app_base()}/markets/{card.market_id}"

    subject = f"Arepo research signal: {card.question[:70]}"
    lines = [
        _lede(card.direction),
        "",
        f"Market: {card.question}",
        f"Relevant outcome: {outcome} (currently {prob})",
        f"Research Priority: {card.research_priority}/100 "
        f"(a research ranking, not expected profit)",
        f"Signal strength: {card.signal_strength * 100:.0f}%  Confidence: "
        f"{card.confidence * 100:.0f}%",
        f"Independent evidence families: {card.n_families} "
        f"({', '.join(card.families) or 'price'})",
        f"Triggered indicators: {tags}",
        "",
        "What caused the signal:",
        f"  {card.explanation}",
        "",
        "Liquidity and spread to check first:",
        f"  Liquidity looks {card.liquidity_quality}"
        + (
            f"; relative spread about {card.relative_spread * 100:.1f}%."
            if card.relative_spread is not None
            else "."
        ),
        "",
        "What this may suggest:",
        "  - price pressure may continue if the flow persists",
        "  - the market may be slow to reflect new information",
        "  - related markets may offer confirmation or contradiction",
        "  - liquidity should be checked before drawing conclusions",
        "",
        "What could invalidate it:",
        "  - the flow reverses or was a one-off large trade",
        "  - the move does not continue at the next observation",
        "  - the spread widens or liquidity thins out",
        f"  - data quality here is {card.data_quality}, so treat a weak reading cautiously",
        "",
        "What you may want to examine next:",
        "  - open the Arepo analysis and read each piece of evidence",
        "  - compare this market with related markets",
        "  - watch whether the imbalance or flow persists",
        "",
        f"Open the analysis: {link}",
        f"Data mode: {card.data_mode}",
        "",
        DISCLAIMER,
    ]
    return AlertContent(subject=subject, text="\n".join(lines))
