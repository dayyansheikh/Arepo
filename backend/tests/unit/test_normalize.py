"""Unit tests for the pure normalization layer (no network)."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from astrolabe.domain.enums import MarketStatus
from astrolabe.ingest.normalize import (
    normalize_book,
    normalize_discovered_market,
    normalize_events_to_markets,
    normalize_market,
    normalize_price_history,
    parse_json_array_string,
    safe_float,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


# --------------------------------------------------------------------------------------
# safe_float
# --------------------------------------------------------------------------------------


def test_safe_float_numeric_passthrough():
    assert safe_float(5) == 5.0
    assert safe_float(5.5) == 5.5


def test_safe_float_string_number():
    assert safe_float("3.14") == 3.14
    assert safe_float("  42  ") == 42.0


def test_safe_float_none_and_empty():
    assert safe_float(None) is None
    assert safe_float("") is None
    assert safe_float("   ") is None


def test_safe_float_unparsable_string():
    assert safe_float("not-a-number") is None


def test_safe_float_bool_rejected():
    # bool is an int subclass in Python; must not silently become 0.0/1.0.
    assert safe_float(True) is None
    assert safe_float(False) is None


# --------------------------------------------------------------------------------------
# parse_json_array_string
# --------------------------------------------------------------------------------------


def test_parse_json_array_string_normal():
    assert parse_json_array_string('["Yes", "No"]') == ["Yes", "No"]


def test_parse_json_array_string_already_a_list():
    assert parse_json_array_string(["Yes", "No"]) == ["Yes", "No"]


def test_parse_json_array_string_empty_or_none():
    assert parse_json_array_string("") == []
    assert parse_json_array_string(None) == []


def test_parse_json_array_string_invalid_json():
    assert parse_json_array_string("not json") == []


def test_parse_json_array_string_json_object_not_array():
    assert parse_json_array_string('{"a": 1}') == []


# --------------------------------------------------------------------------------------
# normalize_market
# --------------------------------------------------------------------------------------


def test_normalize_market_binary_well_formed():
    raw = _load("gamma_markets.json")[0]
    market = normalize_market(raw)
    assert market is not None
    assert market.id == "559651"
    assert market.question == "Will the Fed cut rates in September?"
    assert market.slug == "fed-cut-rates-september"
    assert market.condition_id == "0xabc123"
    assert market.status == MarketStatus.ACTIVE
    assert market.enable_order_book is True
    assert market.is_binary is True

    assert [o.name for o in market.outcomes] == ["Yes", "No"]
    assert [o.token_id for o in market.outcomes] == ["1001", "1002"]
    assert market.outcomes[0].price == 0.62
    assert market.outcomes[1].price == 0.38

    # numeric coercion: "volume" is a string, liquidity has both string and Num variant
    assert market.volume == 125000.50
    assert market.volume_24hr == 4300.25
    assert market.liquidity == 50210.10
    assert market.tick_size == 0.001
    assert market.min_order_size == 5

    assert market.start_date == datetime(2026, 6, 1, tzinfo=UTC)
    assert market.end_date == datetime(2026, 9, 17, tzinfo=UTC)


def test_normalize_market_multi_outcome_closed_uses_num_field():
    raw = _load("gamma_markets.json")[1]
    market = normalize_market(raw)
    assert market is not None
    assert market.status == MarketStatus.CLOSED
    assert market.is_binary is False
    assert len(market.outcomes) == 3
    assert [o.name for o in market.outcomes] == ["Alice", "Bob", "Carol"]
    # no "volume" key present, only "volumeNum" -> must still be coerced
    assert market.volume == 98765.4
    # no liquidityNum -> falls back to string "liquidity"
    assert market.liquidity == 1200.0


def test_normalize_market_applies_category_and_tags():
    raw = _load("gamma_markets.json")[0]
    market = normalize_market(raw, category="Politics", tags=["Politics", "US"])
    assert market is not None
    assert market.category == "Politics"
    assert market.tags == ["Politics", "US"]


def test_normalize_discovered_market_uses_only_carried_event_tags():
    raw = dict(_load("gamma_markets.json")[0])
    raw["_arepo_event_tags"] = [{"label": "Gold"}, {"label": "Commodities"}]
    market = normalize_discovered_market(raw)
    assert market is not None
    assert market.category == "Gold"
    assert market.tags == ["Gold", "Commodities"]


def test_normalize_market_returns_none_when_missing_id():
    raw = dict(_load("gamma_markets.json")[0])
    del raw["id"]
    assert normalize_market(raw) is None


def test_normalize_market_returns_none_when_missing_question():
    raw = dict(_load("gamma_markets.json")[0])
    raw["question"] = ""
    assert normalize_market(raw) is None


def test_normalize_market_returns_none_when_clob_token_ids_missing():
    raw = dict(_load("gamma_markets.json")[0])
    raw["clobTokenIds"] = ""
    assert normalize_market(raw) is None


def test_normalize_market_never_raises_on_malformed_outcome_prices():
    raw = dict(_load("gamma_markets.json")[0])
    raw["outcomePrices"] = "not valid json"
    market = normalize_market(raw)
    assert market is not None
    # prices could not be parsed -> None rather than a crash
    assert all(o.price is None for o in market.outcomes)


def test_normalize_market_never_raises_on_garbage_numeric_fields():
    raw = dict(_load("gamma_markets.json")[0])
    raw["volume"] = "garbage"
    raw["liquidity"] = "garbage"
    raw["liquidityNum"] = "also garbage"
    raw["orderPriceMinTickSize"] = "garbage"
    market = normalize_market(raw)
    assert market is not None
    assert market.volume is None
    assert market.liquidity is None
    assert market.tick_size is None


def test_normalize_market_handles_not_a_dict():
    assert normalize_market(None) is None  # type: ignore[arg-type]
    assert normalize_market([]) is None  # type: ignore[arg-type]


def test_normalize_market_missing_slug_and_condition_id_defaults_to_empty_string():
    raw = dict(_load("gamma_markets.json")[0])
    del raw["slug"]
    del raw["conditionId"]
    market = normalize_market(raw)
    assert market is not None
    assert market.slug == ""
    assert market.condition_id == ""


# --------------------------------------------------------------------------------------
# normalize_events_to_markets
# --------------------------------------------------------------------------------------


def test_normalize_events_to_markets_flattens_and_tags():
    events = _load("gamma_events.json")
    markets = normalize_events_to_markets(events)
    # the second nested market has an empty clobTokenIds and must be dropped
    assert len(markets) == 1
    market = markets[0]
    assert market.id == "700001"
    assert market.category == "Politics"
    assert market.tags == ["Politics", "US"]


def test_normalize_events_to_markets_empty_input():
    assert normalize_events_to_markets([]) == []
    assert normalize_events_to_markets(None) == []  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------
# normalize_book
# --------------------------------------------------------------------------------------


def test_normalize_book_sorts_best_first():
    raw = _load("clob_book.json")
    book = normalize_book("1001", raw)
    assert book.token_id == "1001"

    # bids descending by price (best bid = highest)
    assert [b.price for b in book.bids] == [0.45, 0.02, 0.01]
    # asks ascending by price (best ask = lowest)
    assert [a.price for a in book.asks] == [0.52, 0.98, 0.99]

    assert book.best_bid == 0.45
    assert book.best_ask == 0.52
    assert book.tick_size == 0.001

    # timestamp: "1785600000000" is unix ms as a string
    assert book.timestamp == datetime.fromtimestamp(1785600000000 / 1000.0, tz=UTC)
    assert book.timestamp.tzinfo is not None


def test_normalize_book_empty_sides_never_crash():
    book = normalize_book("2001", {"bids": [], "asks": []})
    assert book.bids == []
    assert book.asks == []
    assert book.best_bid is None
    assert book.best_ask is None
    assert book.is_two_sided is False


def test_normalize_book_missing_sides_and_timestamp():
    book = normalize_book("2002", {})
    assert book.bids == []
    assert book.asks == []
    assert book.tick_size is None
    assert book.timestamp.tzinfo is not None
    # falls back to "now" — should be very recent
    assert (datetime.now(UTC) - book.timestamp).total_seconds() < 5


def test_normalize_book_drops_malformed_levels():
    raw = {
        "bids": [{"price": "0.3", "size": "10"}, {"price": "not-a-number", "size": "5"}],
        "asks": [{"price": "0.6"}],  # missing size -> dropped
    }
    book = normalize_book("2003", raw)
    assert [b.price for b in book.bids] == [0.3]
    assert book.asks == []


# --------------------------------------------------------------------------------------
# normalize_price_history
# --------------------------------------------------------------------------------------


def test_normalize_price_history_parses_and_skips_malformed():
    raw = _load("clob_prices_history.json")
    points = normalize_price_history(raw["history"])
    # 5 raw points, 2 malformed (p=null, t=null) -> 3 valid points
    assert len(points) == 3
    assert points[0].t == datetime.fromtimestamp(1785595806, tz=UTC)
    assert points[0].p == 0.245
    # string t/p coerced correctly
    assert points[2].t == datetime.fromtimestamp(1785597006, tz=UTC)
    assert points[2].p == 0.255


def test_normalize_price_history_empty_and_none():
    assert normalize_price_history([]) == []
    assert normalize_price_history(None) == []  # type: ignore[arg-type]


def test_normalize_price_history_non_dict_items_skipped():
    assert normalize_price_history([{"t": 1, "p": 0.5}, "garbage", None, 42]) == [
        normalize_price_history([{"t": 1, "p": 0.5}])[0]
    ]
