"""API endpoint tests via TestClient, driven in replay mode (hermetic, no network)."""
import pytest
from fastapi.testclient import TestClient

from astrolabe.api.app import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["app"] == "Arepo"
    assert "replay" in body["modes"]
    assert "insider" in body["disclaimer"].lower()


def test_status_replay(client):
    body = client.get("/api/status", params={"mode": "replay"}).json()
    assert body["mode"] == "replay"


def test_overview_replay(client):
    body = client.get("/api/overview", params={"mode": "replay"}).json()
    assert body["status"]["mode"] == "replay"
    assert len(body["highest_volume"]) == 3
    assert all(c["volume"] and c["volume"] > 0 for c in body["highest_volume"])
    assert isinstance(body["recent_signals"], list)


def test_markets_list_and_filters(client):
    body = client.get("/api/markets", params={"mode": "replay", "limit": 2}).json()
    assert body["total"] == 3 and len(body["markets"]) == 2
    econ = client.get("/api/markets", params={"mode": "replay", "category": "Economics"}).json()
    assert econ["total"] == 1


def test_market_detail_and_404(client):
    detail = client.get("/api/markets/90001", params={"mode": "replay"}).json()
    assert detail["market"]["id"] == "90001"
    assert len(detail["market"]["outcomes"]) == 2
    probs = [o["implied_probability_normalized"] for o in detail["market"]["outcomes"]]
    assert probs[0] + probs[1] == pytest.approx(1.0, abs=1e-6)
    assert client.get("/api/markets/nope", params={"mode": "replay"}).status_code == 404


def test_signals(client):
    body = client.get("/api/signals", params={"mode": "replay", "limit": 5}).json()
    assert body["status"]["mode"] == "replay"
    strengths = [s["strength"] for s in body["signals"]]
    assert strengths == sorted(strengths, reverse=True)


def test_backtest(client):
    body = client.get("/api/replay/backtest").json()
    assert body["sample_size"] >= 4
    assert 0.0 < body["hit_rate"] < 1.0
    assert any("profit" in x.lower() for x in body["limitations"])


def test_invalid_sort_rejected(client):
    resp = client.get("/api/markets", params={"mode": "replay", "sort": "bogus"})
    assert resp.status_code == 422       # pattern validation rejects unknown sort


def test_response_time_header_present(client):
    resp = client.get("/health")
    assert "X-Response-Time-ms" in resp.headers


def test_opportunity_diagnostics_replay(client):
    resp = client.get("/api/opportunity/diagnostics", params={"mode": "replay", "universe": 10})
    body = resp.json()
    assert "component_availability" in body and "confidence_distribution" in body
    assert set(body["component_availability"]) == {
        "spread_change", "depth_change", "volume_acceleration",
    }
    # coverage + confidence fields are present and sane
    assert 0 <= body["directional_coverage_pct"] <= 100
    for comp in body["component_availability"].values():
        assert comp["present"] + comp["missing"] == body["tokens_analysed"]
        assert comp["reason_when_missing"]  # honest reason, never a bare dash


def test_replay_cohorts_endpoint_idempotent(client):
    """The prospective-Replay cohort list serves 200 and is an idempotent read (prompt §11, §15)."""
    a = client.get("/api/research/replay/cohorts")
    b = client.get("/api/research/replay/cohorts")
    assert a.status_code == 200 and b.status_code == 200
    ja, jb = a.json(), b.json()
    assert "prospective" in ja["note"].lower()
    for k in ("cohorts", "cadences", "has_prospective", "default_cohort_id"):
        assert k in ja
    # Idempotent apart from the generated_at stamp.
    ja.pop("generated_at", None)
    jb.pop("generated_at", None)
    assert ja == jb


def test_replay_cohort_results_endpoint(client):
    """Result reads are 200, idempotent, and never mix non-directional rows into the table."""
    listing = client.get("/api/research/replay/cohorts").json()
    cid = listing["default_cohort_id"]
    if cid is None:
        # No frozen research cohort in this database; an unknown-cohort read is a clean not-found.
        assert client.get("/api/research/replay/cohort/1").json()["found"] is False
        return
    params = {"horizon": "6h", "scope": "directional", "closing": "all"}
    r1 = client.get(f"/api/research/replay/cohort/{cid}", params=params).json()
    r2 = client.get(f"/api/research/replay/cohort/{cid}", params=params).json()
    assert r1["found"] is True and r1 == r2
    assert all(row["role"] in ("public_selection", "shadow_directional") for row in r1["rows"])
    assert r1["shown"] <= 10
    # Unknown cohort is a clean not-found, not a 500.
    assert client.get("/api/research/replay/cohort/999999", params=params).json()["found"] is False
