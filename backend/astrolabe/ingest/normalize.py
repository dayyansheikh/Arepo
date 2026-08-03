"""Anti-corruption layer: raw Gamma/CLOB JSON -> typed domain models.

Pure functions only — **no network I/O** here (that lives in ``astrolabe.clients``). Upstream
JSON is messy in well-documented ways (see ``docs/research-notes.md`` §2-3): numeric fields
arrive as strings and/or ``...Num`` numbers inconsistently, and ``outcomes`` /
``outcomePrices`` / ``clobTokenIds`` arrive as JSON-encoded strings rather than arrays. Every
function here is defensive: a single malformed field is coerced or dropped, never raised.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..domain.enums import MarketStatus
from ..domain.models import BookLevel, Market, OrderBook, Outcome, PricePoint, Trade, utcnow

# --------------------------------------------------------------------------------------
# Small coercion helpers
# --------------------------------------------------------------------------------------


def safe_float(value: Any) -> float | None:
    """Best-effort coercion of a (possibly stringy, possibly absent) upstream field to float."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def parse_json_array_string(value: Any) -> list:
    """Parse a field that upstream sends as a JSON-encoded array *string* (e.g. `outcomes`).

    Also tolerates the field already being a real list (defensive against upstream fixing the
    encoding later), and returns ``[]`` for anything unparsable rather than raising.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _first_float(raw: dict, *keys: str) -> float | None:
    """Try each key in order (e.g. the `...Num` variant first), return the first coercible."""
    for key in keys:
        if key in raw:
            v = safe_float(raw[key])
            if v is not None:
                return v
    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO-8601 (optionally 'Z'-suffixed) string into an aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


def _padded_tag(tag: str) -> str:
    """Lower-case a tag and pad it with spaces so short keywords can match as whole words
    (e.g. keyword " ai " matches tag "AI" but not "Fairtrade")."""
    return f" {tag.lower().strip()} "


def _keyword_in_tag(tag: str, keywords: tuple[str, ...]) -> bool:
    padded = _padded_tag(tag)
    return any(kw in padded for kw in keywords)


# Ordered broad categories: each tag is tested against these, in order, and the first
# category whose keyword set matches wins. Deliberately conservative — real Polymarket/Gamma
# tag labels (e.g. "NFL", "Politics", "Bitcoin") are expected to match directly; anything
# that matches nothing here falls back to the market's own first tag label, never a
# fabricated placeholder such as "Unknown".
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Sports": (
        "sports", "nfl", "nba", "mlb", "nhl", "ncaa", "soccer", "football",
        "basketball", "baseball", "hockey", "tennis", "golf", "mma", "ufc",
        "boxing", "cricket", "rugby", "esports", "olympics", "nascar",
        "formula 1", "formula1", " f1", "premier league", "champions league",
    ),
    "Politics": (
        "politics", "election", "senate", "congress", "president", "geopolitics",
        "government", "policy",
    ),
    "Crypto": (
        "crypto", "bitcoin", "ethereum", "solana", "defi", " btc", " eth",
    ),
    "Economy": (
        "economy", "economics", "fed", "federal reserve", "inflation",
        "interest rate", "business", "finance",
    ),
    "Entertainment": (
        "entertainment", "movies", "film", "television", " tv ", "music",
        "awards", "oscars", "pop culture", "celebrity",
    ),
    "Science & Technology": (
        "science", "technology", " tech", "artificial intelligence", " ai ", "space",
    ),
    "Weather": (
        "weather", "climate", "hurricane",
    ),
}

# Reliable single-tag -> canonical sport labels. Only unambiguous league/sport names are
# mapped; ambiguous tags (e.g. plain "Football", which could mean NFL or association
# football depending on region) are deliberately excluded so we never guess.
_SPORT_TAG_KEYWORDS: dict[str, str] = {
    "nfl": "NFL",
    "nba": "NBA",
    "mlb": "MLB",
    "nhl": "NHL",
    "mls": "Soccer",
    "soccer": "Soccer",
    "tennis": "Tennis",
    "atp": "Tennis",
    "wta": "Tennis",
    "golf": "Golf",
    "pga": "Golf",
    "mma": "MMA",
    "ufc": "MMA",
    "boxing": "Boxing",
    "cricket": "Cricket",
    "rugby": "Rugby",
    "basketball": "Basketball",
    "baseball": "Baseball",
    "hockey": "Hockey",
    "nascar": "NASCAR",
    "formula 1": "Formula 1",
    "formula1": "Formula 1",
    "esports": "Esports",
}

# Reliable competition/league-grouping tags. Only exact, well-known competition names are
# mapped; anything not covered here is left unset rather than guessed.
_COMPETITION_TAG_KEYWORDS: dict[str, str] = {
    "premier league": "Premier League",
    "champions league": "UEFA Champions League",
    "la liga": "La Liga",
    "serie a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue 1": "Ligue 1",
    "world cup": "World Cup",
    "super bowl": "Super Bowl",
    "march madness": "March Madness",
    "the masters": "The Masters",
    "wimbledon": "Wimbledon",
    "us open": "US Open",
    "ryder cup": "Ryder Cup",
    "stanley cup": "Stanley Cup",
    "world series": "World Series",
}


def derive_category(tag_labels: list[str] | None) -> str | None:
    """Map event tag labels to a clean, broad category.

    Conservative by design: a tag is matched against a small set of known keyword groups
    (see ``_CATEGORY_KEYWORDS``). If none match, the market's own first tag label is kept
    as-is (it is real data, just not bucketed). If there are no tags at all, ``None`` is
    returned. This function never invents or returns a placeholder such as "Unknown".
    """
    if not tag_labels:
        return None
    for tag in tag_labels:
        if not tag:
            continue
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if _keyword_in_tag(tag, keywords):
                return category
    return tag_labels[0]


def derive_sport(tag_labels: list[str] | None) -> str | None:
    """Derive a specific sport/league label (e.g. "NFL") only where tags reliably say so.

    Returns ``None`` (never a guess) when no tag maps to a known, unambiguous sport.
    """
    if not tag_labels:
        return None
    for tag in tag_labels:
        if not tag:
            continue
        padded = _padded_tag(tag)
        for keyword, sport in _SPORT_TAG_KEYWORDS.items():
            if keyword in padded:
                return sport
    return None


def derive_competition(tag_labels: list[str] | None) -> str | None:
    """Derive a specific competition/league grouping only where tags reliably say so.

    Returns ``None`` (never a guess) when no tag maps to a known competition.
    """
    if not tag_labels:
        return None
    for tag in tag_labels:
        if not tag:
            continue
        padded = _padded_tag(tag)
        for keyword, competition in _COMPETITION_TAG_KEYWORDS.items():
            if keyword in padded:
                return competition
    return None


def _derive_status(raw: dict) -> MarketStatus:
    """Derive lifecycle status from Gamma's active/closed/archived boolean flags.

    Precedence: archived > closed > active > unknown. Gamma has no explicit "resolved" flag
    on the market object, so that status value is not produced here.
    """
    if bool(raw.get("archived", False)):
        return MarketStatus.ARCHIVED
    if bool(raw.get("closed", False)):
        return MarketStatus.CLOSED
    if bool(raw.get("active", False)):
        return MarketStatus.ACTIVE
    return MarketStatus.UNKNOWN


# --------------------------------------------------------------------------------------
# Market / event normalization
# --------------------------------------------------------------------------------------


def normalize_market(
    raw: dict, category: str | None = None, tags: list[str] | None = None
) -> Market | None:
    """Normalize one raw Gamma market object into a :class:`Market`.

    Returns ``None`` if the market lacks the essentials (id, question, clobTokenIds) — such a
    record is not usable downstream. Any other malformed field is coerced or dropped rather
    than raised.
    """
    if not isinstance(raw, dict):
        return None

    market_id = raw.get("id")
    question = raw.get("question")
    token_ids = parse_json_array_string(raw.get("clobTokenIds"))

    if not market_id or not question or not token_ids:
        return None

    outcome_names = parse_json_array_string(raw.get("outcomes"))
    outcome_prices = parse_json_array_string(raw.get("outcomePrices"))

    outcomes: list[Outcome] = []
    for i, token_id in enumerate(token_ids):
        if not token_id:
            continue
        name = outcome_names[i] if i < len(outcome_names) else f"Outcome {i + 1}"
        price = safe_float(outcome_prices[i]) if i < len(outcome_prices) else None
        try:
            outcomes.append(Outcome(name=str(name), token_id=str(token_id), price=price))
        except Exception:  # noqa: BLE001 - never let one bad outcome sink the market
            continue

    start_date = _parse_datetime(raw.get("startDate"))
    end_date = _parse_datetime(raw.get("endDate"))

    try:
        return Market(
            id=str(market_id),
            question=str(question),
            slug=str(raw.get("slug") or ""),
            condition_id=str(raw.get("conditionId") or ""),
            outcomes=outcomes,
            status=_derive_status(raw),
            enable_order_book=bool(raw.get("enableOrderBook", False)),
            category=category,
            tags=list(tags) if tags else [],
            sport=derive_sport(tags),
            competition=derive_competition(tags),
            volume=_first_float(raw, "volumeNum", "volume"),
            volume_24hr=_first_float(raw, "volume24hrNum", "volume24hr"),
            liquidity=_first_float(raw, "liquidityNum", "liquidity"),
            tick_size=safe_float(raw.get("orderPriceMinTickSize")),
            min_order_size=safe_float(raw.get("orderMinSize")),
            start_date=start_date,
            end_date=end_date,
            description=raw.get("description"),
            image=raw.get("image"),
        )
    except Exception:  # noqa: BLE001 - malformed upstream record, never crash ingestion
        return None


def _extract_tag_labels(raw_tags: Any) -> list[str]:
    """Event `tags[]` items are usually `{label, ...}` objects; tolerate plain strings too."""
    if not isinstance(raw_tags, list):
        return []
    labels: list[str] = []
    for tag in raw_tags:
        if isinstance(tag, dict):
            label = tag.get("label") or tag.get("name")
            if label:
                labels.append(str(label))
        elif isinstance(tag, str) and tag:
            labels.append(tag)
    return labels


def normalize_events_to_markets(raw_events: list[dict]) -> list[Market]:
    """Flatten nested `markets[]` out of each Gamma event, attaching tags/category."""
    markets: list[Market] = []
    for event in raw_events or []:
        if not isinstance(event, dict):
            continue
        tag_labels = _extract_tag_labels(event.get("tags"))
        category = derive_category(tag_labels)
        for raw_market in event.get("markets") or []:
            market = normalize_market(raw_market, category=category, tags=tag_labels)
            if market is not None:
                markets.append(market)
    return markets


# --------------------------------------------------------------------------------------
# Order book / price history normalization
# --------------------------------------------------------------------------------------


def _normalize_levels(raw_levels: Any, *, best_first_desc: bool) -> list[BookLevel]:
    if not isinstance(raw_levels, list):
        return []
    levels: list[BookLevel] = []
    for lvl in raw_levels:
        if not isinstance(lvl, dict):
            continue
        price = safe_float(lvl.get("price"))
        size = safe_float(lvl.get("size"))
        if price is None or size is None:
            continue
        try:
            levels.append(BookLevel(price=price, size=size))
        except Exception:  # noqa: BLE001
            continue
    levels.sort(key=lambda level: level.price, reverse=best_first_desc)
    return levels


def _parse_book_timestamp(value: Any) -> datetime:
    """CLOB book `timestamp` may be a unix-ms string/number, an ISO string, or absent."""
    if value is None:
        return utcnow()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000.0, tz=UTC)
        except (ValueError, OverflowError, OSError):
            return utcnow()
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return utcnow()
        if s.isdigit():
            try:
                return datetime.fromtimestamp(int(s) / 1000.0, tz=UTC)
            except (ValueError, OverflowError, OSError):
                return utcnow()
        parsed = _parse_datetime(s)
        return parsed if parsed is not None else utcnow()
    return utcnow()


def normalize_book(token_id: str, raw: dict) -> OrderBook:
    """Normalize a raw CLOB `/book` response into a best-first-sorted :class:`OrderBook`.

    Bids are sorted descending by price (best bid = highest), asks ascending (best ask =
    lowest) — upstream ordering is not guaranteed. Missing/empty sides become `[]`.
    """
    raw = raw if isinstance(raw, dict) else {}
    bids = _normalize_levels(raw.get("bids"), best_first_desc=True)
    asks = _normalize_levels(raw.get("asks"), best_first_desc=False)
    return OrderBook(
        token_id=token_id,
        bids=bids,
        asks=asks,
        tick_size=safe_float(raw.get("tick_size")),
        timestamp=_parse_book_timestamp(raw.get("timestamp")),
    )


def normalize_price_history(raw_history: list[dict]) -> list[PricePoint]:
    """Normalize the CLOB `/prices-history` `history[]` array ({t: unix seconds, p}) points."""
    points: list[PricePoint] = []
    for item in raw_history or []:
        if not isinstance(item, dict):
            continue
        p = safe_float(item.get("p"))
        t_raw = item.get("t")
        if p is None or t_raw is None:
            continue
        try:
            t_seconds = float(t_raw)
            t = datetime.fromtimestamp(t_seconds, tz=UTC)
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        try:
            points.append(PricePoint(t=t, p=p))
        except Exception:  # noqa: BLE001
            continue
    return points


def normalize_trades(raw: Any) -> list[Trade]:
    """Normalize raw Data API ``/trades`` items into typed :class:`Trade` models.

    Skips malformed rows rather than raising, so one bad item never loses a whole page.
    Timestamps are Unix seconds. Returns trades in the order given (the API returns them
    newest-first).
    """
    if not isinstance(raw, list):
        return []
    out: list[Trade] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        wallet = item.get("proxyWallet")
        asset = item.get("asset")
        ts = item.get("timestamp")
        if not wallet or not asset or ts is None:
            continue
        try:
            t = datetime.fromtimestamp(int(ts), tz=UTC)
        except (TypeError, ValueError, OSError):
            continue
        try:
            out.append(
                Trade(
                    wallet=str(wallet),
                    side=str(item.get("side", "")).upper(),
                    token_id=str(asset),
                    size=float(item.get("size") or 0.0),
                    price=float(item.get("price") or 0.0),
                    timestamp=t,
                    outcome_index=item.get("outcomeIndex"),
                    outcome=item.get("outcome"),
                    tx_hash=item.get("transactionHash"),
                )
            )
        except Exception:  # noqa: BLE001 - one malformed trade never breaks the page
            continue
    return out
