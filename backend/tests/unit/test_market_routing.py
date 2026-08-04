"""Canonical market resolution across data modes (spec §3, IDs like 2694364 / 2822017)."""
import httpx
import pytest
import respx

from astrolabe.service import MarketService

# A minimal but complete Gamma single-market payload (fields normalize_market needs).
_MARKET_JSON = {
    "id": "2694364",
    "question": "Will James Graf win the 2026 Montgomery County race?",
    "slug": "will-james-graf-win",
    "active": True,
    "closed": False,
    "enableOrderBook": True,
    "clobTokenIds": '["111", "222"]',
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.4", "0.6"]',
    "volume": "10000",
    "liquidity": "5000",
}


@respx.mock
async def test_search_result_opens_regardless_of_selected_mode():
    # The market is NOT in the replay dataset, but a valid live Gamma id. With Replay selected,
    # opening it must still resolve (canonical live fallback), labelled data_source=live.
    respx.get("https://gamma-api.polymarket.com/markets/2694364").mock(
        return_value=httpx.Response(200, json=_MARKET_JSON)
    )
    # Order book + price history for its tokens (best-effort; empty is fine).
    respx.get(url__regex=r"https://clob\.polymarket\.com/book.*").mock(
        return_value=httpx.Response(200, json={"bids": [], "asks": []})
    )
    respx.get(url__regex=r"https://clob\.polymarket\.com/prices-history.*").mock(
        return_value=httpx.Response(200, json={"history": []})
    )

    svc = MarketService()
    try:
        detail = await svc.market_detail("2694364", requested_mode="replay")
        assert detail is not None, "a valid live market must open even when Replay is selected"
        assert detail.market.id == "2694364"
        assert detail.market.data_source == "live"  # resolved canonically from the live universe
        assert len(detail.market.outcomes) == 2
    finally:
        await svc.aclose()


@respx.mock
async def test_genuinely_missing_market_is_404_not_silent():
    respx.get("https://gamma-api.polymarket.com/markets/does-not-exist").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    svc = MarketService()
    try:
        detail = await svc.market_detail("does-not-exist", requested_mode="replay")
        assert detail is None  # only None when it exists in no supported source
    finally:
        await svc.aclose()


@pytest.mark.parametrize("mode", ["live", "cached", "replay"])
@respx.mock
async def test_canonical_id_resolves_in_all_modes(mode):
    respx.get("https://gamma-api.polymarket.com/markets/2694364").mock(
        return_value=httpx.Response(200, json=_MARKET_JSON)
    )
    respx.get(url__regex=r"https://clob\.polymarket\.com/.*").mock(
        return_value=httpx.Response(200, json={"bids": [], "asks": [], "history": []})
    )
    svc = MarketService()
    try:
        detail = await svc.market_detail("2694364", requested_mode=mode)
        assert detail is not None and detail.market.id == "2694364"
    finally:
        await svc.aclose()
