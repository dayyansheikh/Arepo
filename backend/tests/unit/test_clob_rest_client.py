"""Unit tests for ClobRestClient: HTTP mocked via respx, no real network calls."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from astrolabe.clients.clob_rest import ClobRestClient
from astrolabe.clients.errors import RateLimited, UpstreamUnavailable
from astrolabe.config import Settings

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BASE_URL = "https://clob.polymarket.com"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def _fast_settings(**overrides) -> Settings:
    overrides.setdefault("http_max_retries", 1)
    return Settings(clob_base_url=BASE_URL, **overrides)


@respx.mock
async def test_get_book_returns_raw_dict():
    fixture = _load("clob_book.json")
    respx.get(f"{BASE_URL}/book", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(200, json=fixture)
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_book("1001")
    assert result == fixture
    # still raw string prices — no normalization here
    assert result["bids"][0]["price"] == "0.01"


@respx.mock
async def test_get_midpoint_accepts_mid_key():
    respx.get(f"{BASE_URL}/midpoint", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(200, json={"mid": "0.195"})
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_midpoint("1001")
    assert result == 0.195


@respx.mock
async def test_get_midpoint_accepts_mid_price_key():
    respx.get(f"{BASE_URL}/midpoint", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(200, json={"mid_price": "0.42"})
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_midpoint("1001")
    assert result == 0.42


@respx.mock
async def test_get_midpoint_missing_key_returns_none():
    respx.get(f"{BASE_URL}/midpoint", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(200, json={"unexpected": "field"})
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_midpoint("1001")
    assert result is None


@respx.mock
async def test_get_price_buy_and_sell():
    respx.get(f"{BASE_URL}/price", params={"token_id": "1001", "side": "buy"}).mock(
        return_value=httpx.Response(200, json={"price": "0.19"})
    )
    respx.get(f"{BASE_URL}/price", params={"token_id": "1001", "side": "sell"}).mock(
        return_value=httpx.Response(200, json={"price": "0.21"})
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        buy = await client.get_price("1001", "buy")
        sell = await client.get_price("1001", "sell")
    assert buy == 0.19
    assert sell == 0.21


@respx.mock
async def test_get_spread():
    respx.get(f"{BASE_URL}/spread", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(200, json={"spread": "0.01"})
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_spread("1001")
    assert result == 0.01


@respx.mock
async def test_get_spread_missing_field_returns_none():
    respx.get(f"{BASE_URL}/spread", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(200, json={})
    )
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_spread("1001")
    assert result is None


@respx.mock
async def test_get_prices_history_returns_history_array():
    fixture = _load("clob_prices_history.json")
    respx.get(
        f"{BASE_URL}/prices-history",
        params={"market": "1001", "interval": "1d", "fidelity": "10"},
    ).mock(return_value=httpx.Response(200, json=fixture))
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_prices_history("1001")
    assert result == fixture["history"]


@respx.mock
async def test_get_prices_history_custom_interval_and_fidelity():
    respx.get(
        f"{BASE_URL}/prices-history",
        params={"market": "1001", "interval": "1w", "fidelity": "60"},
    ).mock(return_value=httpx.Response(200, json={"history": []}))
    async with ClobRestClient(settings=_fast_settings()) as client:
        result = await client.get_prices_history("1001", interval="1w", fidelity=60)
    assert result == []


@respx.mock
async def test_rate_limited_raises_after_retries_exhausted():
    route = respx.get(f"{BASE_URL}/book", params={"token_id": "1001"}).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0.01"})
    )
    async with ClobRestClient(settings=_fast_settings(http_max_retries=2)) as client:
        with pytest.raises(RateLimited) as excinfo:
            await client.get_book("1001")
    assert excinfo.value.status_code == 429
    assert route.call_count == 3


@respx.mock
async def test_timeout_retries_then_raises_upstream_unavailable():
    route = respx.get(f"{BASE_URL}/book", params={"token_id": "1001"}).mock(
        side_effect=httpx.ReadTimeout("boom")
    )
    async with ClobRestClient(settings=_fast_settings(http_max_retries=2)) as client:
        with pytest.raises(UpstreamUnavailable):
            await client.get_book("1001")
    assert route.call_count == 3


@respx.mock
async def test_5xx_retries_then_recovers():
    fixture = _load("clob_book.json")
    route = respx.get(f"{BASE_URL}/book", params={"token_id": "1001"}).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json=fixture)]
    )
    async with ClobRestClient(settings=_fast_settings(http_max_retries=2)) as client:
        result = await client.get_book("1001")
    assert result == fixture
    assert route.call_count == 2


async def test_client_injection_is_not_owned_and_not_closed():
    injected = httpx.AsyncClient(base_url=BASE_URL)
    client = ClobRestClient(client=injected, settings=_fast_settings())
    await client.aclose()
    assert injected.is_closed is False
    await injected.aclose()
