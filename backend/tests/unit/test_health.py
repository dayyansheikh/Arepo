"""Smoke test: the app boots and /health responds."""
from fastapi.testclient import TestClient

from astrolabe.api.app import create_app
from astrolabe.api.routes import health as health_route
from astrolabe.config import Settings
from astrolabe.storage.db import Base, get_session, make_engine, make_sessionmaker
from astrolabe.storage.migrate import _load_all_models


def test_health_ok():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "Arepo"
    # timestamp is present and ISO-ish
    assert "T" in body["time"]


def test_admin_health_disabled_without_token(monkeypatch):
    """With ADMIN_TOKEN unset the diagnostic route does not exist (404) — no surface exposed."""
    monkeypatch.setattr(health_route, "get_settings", lambda: Settings(admin_token=""))
    client = TestClient(create_app())
    assert client.get("/admin/health").status_code == 404


def test_admin_health_requires_matching_token(monkeypatch):
    _load_all_models()
    monkeypatch.setattr(health_route, "get_settings", lambda: Settings(admin_token="secret"))

    engine = make_engine("sqlite+aiosqlite:///:memory:")

    async def _override():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sm = make_sessionmaker(engine)
        async with sm() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = _override
    client = TestClient(app)
    assert client.get("/admin/health").status_code == 401                       # missing token
    assert client.get("/admin/health",
                      headers={"X-Admin-Token": "wrong"}).status_code == 401     # wrong token
    ok = client.get("/admin/health", headers={"X-Admin-Token": "secret"})
    assert ok.status_code == 200
    assert ok.json()["db_healthy"] is True
    assert "storage" in ok.json()


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
