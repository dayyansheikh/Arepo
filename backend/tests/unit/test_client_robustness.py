"""Regression tests: upstream clients never leak raw httpx errors; live discovery filters."""
import httpx
import pytest
import respx

from astrolabe.clients.clob_rest import ClobRestClient
from astrolabe.clients.errors import AstrolabeClientError, NotFound
from astrolabe.clients.gamma import GammaClient
from astrolabe.config import Settings
from astrolabe.domain.enums import MarketStatus
from astrolabe.domain.models import Market, Outcome
from astrolabe.service.sources import _is_tradeable


@pytest.fixture
def settings():
    return Settings(http_max_retries=0)


@respx.mock
async def test_clob_book_404_raises_typed_notfound_not_httpx(settings):
    respx.get("https://clob.polymarket.com/book").mock(return_value=httpx.Response(404))
    client = ClobRestClient(settings=settings)
    with pytest.raises(NotFound) as ei:
        await client.get_book("resolved-token")
    assert ei.value.status_code == 404
    # NotFound is catchable as the shared base type (what LiveSource relies on).
    assert isinstance(ei.value, AstrolabeClientError)
    await client.aclose()


@respx.mock
async def test_clob_other_4xx_maps_to_client_error(settings):
    respx.get("https://clob.polymarket.com/midpoint").mock(return_value=httpx.Response(403))
    client = ClobRestClient(settings=settings)
    with pytest.raises(AstrolabeClientError):
        await client.get_midpoint("t")
    await client.aclose()


@respx.mock
async def test_gamma_get_market_404_returns_none(settings):
    respx.get("https://gamma-api.polymarket.com/markets/nope").mock(
        return_value=httpx.Response(404)
    )
    client = GammaClient(settings=settings)
    assert await client.get_market("nope") is None
    await client.aclose()


@respx.mock
async def test_gamma_list_404_raises_typed_not_httpx(settings):
    respx.get("https://gamma-api.polymarket.com/events").mock(return_value=httpx.Response(404))
    client = GammaClient(settings=settings)
    with pytest.raises(AstrolabeClientError):
        await client.list_events(limit=5)
    await client.aclose()


def _mk(prices):
    return Market(
        id="m", question="q?", slug="q", condition_id="0x",
        outcomes=[Outcome(name=n, token_id=f"t{i}", price=p)
                 for i, (n, p) in enumerate(zip(["Yes", "No"], prices, strict=False))],
        status=MarketStatus.ACTIVE, enable_order_book=True,
    )


def test_is_tradeable_filters_resolved_and_bookless():
    assert _is_tradeable(_mk([0.42, 0.58])) is True       # normal two-sided
    assert _is_tradeable(_mk([1.0, 0.0])) is False         # resolved (price ~1)
    assert _is_tradeable(_mk([0.0005, 0.9995])) is False   # effectively resolved
    no_book = _mk([0.4, 0.6])
    no_book.enable_order_book = False
    assert _is_tradeable(no_book) is False
    single = Market(id="m", question="q?", slug="q", condition_id="0x",
                    outcomes=[Outcome(name="Yes", token_id="t0", price=0.5)],
                    status=MarketStatus.ACTIVE, enable_order_book=True)
    assert _is_tradeable(single) is False                  # < 2 outcomes
