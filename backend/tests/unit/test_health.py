"""Smoke test: the app boots and /health responds."""
from fastapi.testclient import TestClient

from astrolabe.api.app import create_app


def test_health_ok():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "Arepo"
    # timestamp is present and ISO-ish
    assert "T" in body["time"]


def test_domain_models_import_and_orderbook_math():
    """Domain contract sanity: order-book derived properties are correct."""
    from astrolabe.domain.models import BookLevel, OrderBook

    book = OrderBook(
        token_id="t1",
        bids=[BookLevel(price=0.49, size=100), BookLevel(price=0.48, size=50)],
        asks=[BookLevel(price=0.52, size=80), BookLevel(price=0.53, size=40)],
    )
    assert book.best_bid == 0.49
    assert book.best_ask == 0.52
    assert book.midpoint == 0.505
    assert abs(book.spread - 0.03) < 1e-9
    assert book.is_two_sided is True

    empty = OrderBook(token_id="t2")
    assert empty.best_bid is None and empty.midpoint is None and empty.spread is None
    assert empty.is_two_sided is False
