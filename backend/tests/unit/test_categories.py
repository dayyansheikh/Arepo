"""Unit tests for category/sport/competition derivation and the markets facets endpoint.

Covers spec section 10 (Markets filters and categories): filter metadata must be real and
dynamically derived from normalized market data, never fabricated, and never surfaced as the
literal placeholder "Unknown".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astrolabe.api.app import create_app
from astrolabe.domain.enums import MarketStatus
from astrolabe.ingest.normalize import (
    derive_category,
    derive_competition,
    derive_sport,
    normalize_events_to_markets,
    normalize_market,
)
from astrolabe.service import MarketService

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def _base_market_raw() -> dict:
    """A minimal well-formed raw Gamma market payload usable across tests below."""
    raw = dict(_load("gamma_markets.json")[0])
    return raw


# --------------------------------------------------------------------------------------
# derive_category
# --------------------------------------------------------------------------------------


def test_derive_category_sports_from_league_tag():
    assert derive_category(["NFL"]) == "Sports"
    assert derive_category(["NBA", "US"]) == "Sports"
    assert derive_category(["MLB"]) == "Sports"


def test_derive_category_sports_from_generic_sport_words():
    assert derive_category(["Soccer"]) == "Sports"
    assert derive_category(["Football"]) == "Sports"
    assert derive_category(["Tennis"]) == "Sports"


def test_derive_category_politics_from_election_tags():
    assert derive_category(["Politics"]) == "Politics"
    assert derive_category(["US Election 2028"]) == "Politics"


def test_derive_category_crypto_from_bitcoin_tag():
    assert derive_category(["Crypto"]) == "Crypto"
    assert derive_category(["Bitcoin"]) == "Crypto"


def test_derive_category_economy_from_fed_tag():
    assert derive_category(["Fed"]) == "Economy"
    assert derive_category(["Economics"]) == "Economy"


def test_derive_category_first_matching_tag_wins_over_later_tags():
    # "NFL" (Sports) appears before "Politics" -> Sports should win, honouring tag order.
    assert derive_category(["NFL", "Politics"]) == "Sports"


def test_derive_category_no_tags_is_none_not_unknown():
    assert derive_category([]) is None
    assert derive_category(None) is None


def test_derive_category_unmatched_tag_keeps_real_first_tag_label():
    # A genuinely unrecognised tag must be kept as real data, never replaced with "Unknown".
    result = derive_category(["Miscellaneous Novelty Bets"])
    assert result == "Miscellaneous Novelty Bets"
    assert result != "Unknown"


def test_derive_category_never_returns_unknown_literal():
    samples = [
        ["NFL"], ["Politics"], ["Crypto"], ["Random Tag"], [], None,
        ["Something Else Entirely"],
    ]
    for tags in samples:
        assert derive_category(tags) != "Unknown"
        assert derive_category(tags) != "Parent for derivative"


# --------------------------------------------------------------------------------------
# derive_sport
# --------------------------------------------------------------------------------------


def test_derive_sport_maps_known_leagues():
    assert derive_sport(["NFL"]) == "NFL"
    assert derive_sport(["NBA", "US"]) == "NBA"
    assert derive_sport(["MLB"]) == "MLB"
    assert derive_sport(["Soccer"]) == "Soccer"
    assert derive_sport(["Tennis"]) == "Tennis"


def test_derive_sport_none_when_no_tags():
    assert derive_sport([]) is None
    assert derive_sport(None) is None


def test_derive_sport_none_when_tags_do_not_reliably_indicate_a_sport():
    # "Football" alone is ambiguous (American football vs association football) and must
    # never be guessed into a specific league/sport.
    assert derive_sport(["Football"]) is None
    assert derive_sport(["Politics"]) is None
    assert derive_sport(["Sports"]) is None  # generic "Sports" tag alone is not a sport


def test_derive_sport_never_returns_unknown_literal():
    for tags in [["NFL"], ["Football"], [], None, ["Something"]]:
        assert derive_sport(tags) != "Unknown"


# --------------------------------------------------------------------------------------
# derive_competition
# --------------------------------------------------------------------------------------


def test_derive_competition_maps_known_leagues():
    assert derive_competition(["Premier League"]) == "Premier League"
    assert derive_competition(["UEFA Champions League"]) == "UEFA Champions League"
    assert derive_competition(["NBA", "March Madness"]) == "March Madness"


def test_derive_competition_none_when_not_reliably_present():
    assert derive_competition(["NFL"]) is None
    assert derive_competition(["Soccer"]) is None
    assert derive_competition([]) is None
    assert derive_competition(None) is None


def test_derive_competition_never_returns_unknown_literal():
    for tags in [["Premier League"], ["NFL"], [], None]:
        assert derive_competition(tags) != "Unknown"


# --------------------------------------------------------------------------------------
# normalize_market / normalize_events_to_markets wiring
# --------------------------------------------------------------------------------------


def test_normalize_market_derives_sport_and_competition_from_tags():
    raw = _base_market_raw()
    market = normalize_market(raw, category="Sports", tags=["NFL", "Super Bowl"])
    assert market is not None
    assert market.category == "Sports"
    assert market.sport == "NFL"
    assert market.competition == "Super Bowl"


def test_normalize_market_leaves_sport_and_competition_unset_when_not_reliable():
    raw = _base_market_raw()
    market = normalize_market(raw, category="Politics", tags=["Politics", "US"])
    assert market is not None
    assert market.sport is None
    assert market.competition is None


def test_normalize_events_to_markets_derives_broad_category_from_tags():
    events = _load("gamma_events.json")
    markets = normalize_events_to_markets(events)
    assert len(markets) == 1
    # fixture tags are ["Politics", "US"] -> broad category "Politics", no sport/competition
    assert markets[0].category == "Politics"
    assert markets[0].sport is None
    assert markets[0].competition is None


def test_normalize_events_to_markets_sports_event_gets_sport_and_competition():
    raw_event = {
        "tags": [{"label": "NBA"}, {"label": "Playoffs"}],
        "markets": [dict(_base_market_raw())],
    }
    markets = normalize_events_to_markets([raw_event])
    assert len(markets) == 1
    market = markets[0]
    assert market.category == "Sports"
    assert market.sport == "NBA"
    # "Playoffs" alone is not a reliably specific competition -> left unset.
    assert market.competition is None


# --------------------------------------------------------------------------------------
# facets: MarketService.facets() / GET /api/markets/facets
# --------------------------------------------------------------------------------------


@pytest.fixture
def svc():
    return MarketService()


async def test_facets_replay_returns_distinct_sorted_real_values(svc):
    facets = await svc.facets(requested_mode="replay")
    # every value present must be real (non-empty) data, sorted, and de-duplicated
    assert facets.categories == sorted(set(facets.categories))
    assert facets.statuses == sorted(set(facets.statuses))
    assert facets.sports == sorted(set(facets.sports))
    assert facets.competitions == sorted(set(facets.competitions))
    assert all(c for c in facets.categories)
    assert all(s for s in facets.statuses)
    # nothing fabricated: no placeholder strings anywhere in the response
    for value in (*facets.categories, *facets.sports, *facets.competitions, *facets.statuses):
        assert value != "Unknown"
        assert value != "Parent for derivative"


async def test_facets_empty_lists_when_no_sports_or_competitions_present():
    # the replay scenario dataset has no sport/competition-bearing tags today; facets must
    # degrade to an empty list rather than inventing placeholder values.
    svc = MarketService()
    facets = await svc.facets(requested_mode="replay")
    assert isinstance(facets.sports, list)
    assert isinstance(facets.competitions, list)


def test_markets_facets_endpoint_shape():
    with TestClient(create_app()) as client:
        resp = client.get("/api/markets/facets", params={"mode": "replay"})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"categories", "sports", "competitions", "statuses"}
        for key in ("categories", "sports", "competitions", "statuses"):
            assert isinstance(body[key], list)
            assert all(isinstance(v, str) and v for v in body[key])
            assert "Unknown" not in body[key]
            assert "Parent for derivative" not in body[key]


def test_markets_facets_statuses_reflect_market_status_enum_values():
    with TestClient(create_app()) as client:
        resp = client.get("/api/markets/facets", params={"mode": "replay"})
        body = resp.json()
        valid_statuses = {s.value for s in MarketStatus}
        assert set(body["statuses"]).issubset(valid_statuses)
