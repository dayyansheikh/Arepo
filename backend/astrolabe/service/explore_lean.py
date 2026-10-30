"""Memory-lean, read-only market records for the Explore/facets universe (infra fix 2026-10-11).

The Explore universe is the whole persisted ``markets`` cache (every market any complete scan made
eligible). Materialising it as full pydantic ``Market`` objects (+ nested ``Outcome`` models) and
holding it in the process cache was the dominant resident-memory cost of the Render Free API
(512 MiB): measured at roughly 30 KB of RSS per market. ``LeanMarket`` carries only what Explore,
facets and the cards actually read, as ``__slots__`` objects, with the case-folded search haystack
precomputed so search semantics are byte-for-byte those of ``_market_search_matches``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..domain.models import MarketStatus


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class LeanOutcome:
    name: str
    token_id: str
    price: float | None


@dataclass(frozen=True, slots=True)
class LeanMarket:
    id: str
    question: str
    slug: str
    status: MarketStatus
    category: str | None
    tags: tuple[str, ...]
    volume: float | None
    volume_24hr: float | None
    liquidity: float | None
    end_date: datetime | None
    updated_at: datetime | None
    outcomes: tuple[LeanOutcome, ...]
    # Exactly the haystack ``_market_search_matches`` builds (question, slug, description,
    # category, tags joined by spaces, lower-cased); the description itself is not retained.
    search_text: str
    sport: str | None = None          # not persisted in the markets cache (as before: None)
    competition: str | None = None


def search_haystack(question: str, slug: str, description: str | None, category: str | None,
                    tags) -> str:
    return " ".join([question, slug, description or "", category or "", *list(tags or [])]).lower()


def _clip(price):
    # Mirror Outcome._clip_price so a lean card shows the same lead price as the pydantic model.
    if price is None:
        return None
    return min(1.0, max(0.0, float(price)))


def lean_from_row(row) -> LeanMarket:
    """Build from a narrow column row: (id, question, slug, status, category, tags, volume,
    volume_24hr, liquidity, end_date, updated_at, outcomes, description)."""
    (mid, question, slug, status, category, tags, volume, volume_24hr, liquidity, end_date,
     updated_at, outcomes, description) = row
    tags_t = tuple(tags or [])
    return LeanMarket(
        id=mid, question=question, slug=slug, status=MarketStatus(status), category=category,
        tags=tags_t, volume=volume, volume_24hr=volume_24hr, liquidity=liquidity,
        end_date=_utc(end_date), updated_at=_utc(updated_at),
        outcomes=tuple(
            LeanOutcome(name=o.get("name"), token_id=o.get("token_id"), price=_clip(o.get("price")))
            for o in (outcomes or [])
        ),
        search_text=search_haystack(question, slug, description, category, tags_t),
    )
