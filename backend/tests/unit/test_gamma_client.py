"""Unit tests for GammaClient: HTTP mocked via respx, no real network calls."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from astrolabe.clients.errors import RateLimited, UpstreamUnavailable
from astrolabe.clients.gamma import GammaClient
from astrolabe.config import Settings

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BASE_URL = "https://gamma-api.polymarket.com"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def _fast_settings(**overrides) -> Settings:
    overrides.setdefault("http_max_retries", 1)
    return Settings(gamma_base_url=BASE_URL, **overrides)


@respx.mock
async def test_list_markets_returns_raw_list():
    fixture = _load("gamma_markets.json")
    route = respx.get(f"{BASE_URL}/markets").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    async with GammaClient(settings=_fast_settings()) as client:
        result = await client.list_markets(limit=2)

    assert route.called
    assert result == fixture
    # raw dicts, not domain objects
    assert isinstance(result[0]["outcomes"], str)


@respx.mock
async def test_list_markets_sends_expected_query_params():
    fixture = _load("gamma_markets.json")
    route = respx.get(f"{BASE_URL}/markets").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    async with GammaClient(settings=_fast_settings()) as client:
        await client.list_markets(
            limit=5, active=True, closed=False, order="volume24hr", ascending=False
        )

    request = route.calls.last.request
    params = dict(httpx.QueryParams(request.url.query))
    assert params["limit"] == "5"
    assert params["active"] == "true"
    assert params["closed"] == "false"
    assert params["order"] == "volume24hr"
    assert params["ascending"] == "false"


@respx.mock
async def test_list_events_returns_raw_list():
    fixture = _load("gamma_events.json")
    respx.get(f"{BASE_URL}/events").mock(return_value=httpx.Response(200, json=fixture))
    async with GammaClient(settings=_fast_settings()) as client:
        result = await client.list_events(limit=10)
    assert result == fixture


@respx.mock
async def test_get_market_found():
    market = _load("gamma_markets.json")[0]
    respx.get(f"{BASE_URL}/markets/559651").mock(
        return_value=httpx.Response(200, json=market)
    )
    async with GammaClient(settings=_fast_settings()) as client:
        result = await client.get_market("559651")
    assert result == market


@respx.mock
async def test_get_market_not_found_returns_none():
    respx.get(f"{BASE_URL}/markets/nope").mock(return_value=httpx.Response(404))
    async with GammaClient(settings=_fast_settings()) as client:
        result = await client.get_market("nope")
    assert result is None


@respx.mock
async def test_rate_limited_raises_after_retries_exhausted():
    route = respx.get(f"{BASE_URL}/markets").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0.01"})
    )
    async with GammaClient(settings=_fast_settings(http_max_retries=2)) as client:
        with pytest.raises(RateLimited) as excinfo:
            await client.list_markets(limit=1)

    assert excinfo.value.status_code == 429
    assert excinfo.value.retry_after == 0.01
    # http_max_retries=2 -> 3 total attempts
    assert route.call_count == 3


@respx.mock
async def test_timeout_retries_then_raises_upstream_unavailable():
    route = respx.get(f"{BASE_URL}/markets").mock(side_effect=httpx.ConnectTimeout("boom"))
    async with GammaClient(settings=_fast_settings(http_max_retries=2)) as client:
        with pytest.raises(UpstreamUnavailable):
            await client.list_markets(limit=1)
    assert route.call_count == 3


@respx.mock
async def test_5xx_retries_then_recovers():
    fixture = _load("gamma_markets.json")
    route = respx.get(f"{BASE_URL}/markets").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=fixture),
        ]
    )
    async with GammaClient(settings=_fast_settings(http_max_retries=2)) as client:
        result = await client.list_markets(limit=1)
    assert result == fixture
    assert route.call_count == 2


@respx.mock
async def test_5xx_exhausted_raises_upstream_unavailable():
    route = respx.get(f"{BASE_URL}/markets").mock(return_value=httpx.Response(502))
    async with GammaClient(settings=_fast_settings(http_max_retries=1)) as client:
        with pytest.raises(UpstreamUnavailable) as excinfo:
            await client.list_markets(limit=1)
    assert excinfo.value.status_code == 502
    assert route.call_count == 2


@respx.mock
async def test_list_markets_raises_schema_error_on_non_list():
    respx.get(f"{BASE_URL}/markets").mock(return_value=httpx.Response(200, json={"oops": True}))
    from astrolabe.clients.errors import UpstreamSchemaError

    async with GammaClient(settings=_fast_settings()) as client:
        with pytest.raises(UpstreamSchemaError):
            await client.list_markets(limit=1)


async def test_client_injection_is_not_owned_and_not_closed():
    injected = httpx.AsyncClient(base_url=BASE_URL)
    client = GammaClient(client=injected, settings=_fast_settings())
    await client.aclose()
    assert injected.is_closed is False
    await injected.aclose()
