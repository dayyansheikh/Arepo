"""Public signal projection: allow-list, embargo re-check, staleness, off-by-default route."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from astrolabe.accounts import db as accounts_db
from astrolabe.api.app import create_app
from astrolabe.config import get_settings
from astrolabe.lab import public_signals as ps
from astrolabe.lab.models import LabSnapshot
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

NOW = datetime(2026, 11, 7, 6, 0, tzinfo=UTC)
CHAMP = "se0_champion_lr_mm"


def _row(mid, target="dir_2h", auc=0.76, **extra):
    return {
        "model_id": mid,
        "target": target,
        "auc": auc,
        "brier": 0.23,
        "log_loss": 0.45,
        "days": 13,
        "n": 1000,
        "cal_slope": 1.0,
        "cal_intercept": -0.1,
        "coverage": 0.97,
        "secret": "x",
        **extra,
    }


def _market(mid, s):
    return {
        "market_id": mid,
        "title": "T",
        "url": "https://polymarket.com/event/x",
        "category": "sports",
        "mid": 0.4,
        "spread": 0.01,
        "hours_to_end": 10.0,
        "s_2h": s,
        "s_6h": 0.5,
        "s_24h": 0.6,
        "wallet": "0xabc",
    }


def payload(**over):
    se = {
        "schema": "se-dash-v1",
        "champion": {"model_id": CHAMP, "family": "baseline", "spec_sha256": "abc"},
        "models": [
            {"model_id": CHAMP, "family": "baseline", "status": "active", "embargoed_until": None},
            {
                "model_id": "se1_lgbm_mm",
                "family": "baseline (lgbm)",
                "status": "active",
                "embargoed_until": None,
            },
            {
                "model_id": "se2_lr_flow",
                "family": "flow",
                "status": "active",
                "embargoed_until": "2026-11-16",
            },
            {
                "model_id": "se3_lr_book",
                "family": "book",
                "status": "ineligible",
                "embargoed_until": None,
            },
            {
                "model_id": "se9_bad",
                "family": "x",
                "status": "active",
                "embargoed_until": "garbage",
            },
            {
                "model_id": "se5_lr_tte",
                "family": "tte",
                "status": "active",
                "embargoed_until": "2026-11-07",
            },
        ],
        "prospective": {
            "rows": [
                _row(CHAMP),
                _row(CHAMP, target="res_7d"),
                _row("se1_lgbm_mm", auc=0.80, log_loss=0.40),
                _row("se2_lr_flow"),
                _row("se3_lr_book"),
                _row("se9_bad"),
                _row("se5_lr_tte"),
                _row("se99_unlisted"),
            ]
        },
        "promotion": {"candidates": [{"model_id": "se1_lgbm_mm", "gain": 0.04}]},
        "family_gains": [{"family": "flow", "gain": 0.1}],
        "feed": {
            "schema": "se-feed-v1",
            "champion": {"model_id": CHAMP},
            "origin_utc": "2026-11-07T04:31:02Z",
            "prediction_written_utc": "2026-11-07T04:55:59Z",
            "prediction_sha256": "f" * 64,
            "stale": False,
            "top_up": [_market(1, 0.6), _market(2, -0.1), {"market_id": 3}],
            "top_down": [_market(4, -0.5)],
            "summary": {"dir_24h": {"mean": 0.1}},
            "track_record": {
                "days_scored": 17,
                "rows": [_row(CHAMP, target="dir_6h"), _row(CHAMP)],
            },
        },
    }
    se.update(over)
    return {"schema": "arepo-lab-v1", "source": "host", "queue": {"jobs": []}, "signal_engine": se}


def _keys(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(k)
            _keys(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, acc)
    return acc


def test_projection_is_allow_listed_and_dir_2h_only():
    out = ps.project(payload(), NOW, NOW)
    assert out["status"] == "ok" and out["champion"]["model_id"] == CHAMP
    keys = _keys(out)
    for forbidden in (
        "s_6h",
        "s_24h",
        "wallet",
        "secret",
        "coverage",
        "summary",
        "promotion",
        "family_gains",
        "queue",
        "spec_sha256",
        "res_7d",
    ):
        assert forbidden not in keys
    assert "res_7d" not in json.dumps(out) and "s_24h" not in json.dumps(out)
    feed = out["feed"]
    assert [m["market_id"] for m in feed["top_up"]] == [1]  # wrong-sign and malformed rows dropped
    assert [m["market_id"] for m in feed["top_down"]] == [4]
    assert feed["top_up"][0]["signal_strength"] == 0.6
    assert feed["track_record"]["auc"] == 0.76 and feed["days_scored"] == 17 and not feed["stale"]


def test_embargo_rechecked_and_fails_safe():
    board = {b["model_id"]: b for b in ps.project(payload(), NOW, NOW)["leaderboard"]}
    assert board["se2_lr_flow"] == {
        "model_id": "se2_lr_flow",
        "family": "flow",
        "role": "challenger",
        "hidden_until": "2026-11-16",
    }
    assert "auc" not in board["se9_bad"] and board["se9_bad"]["hidden_until"] == "garbage"
    assert "auc" not in board["se5_lr_tte"]  # date-only embargo holds through that UTC day
    assert "se3_lr_book" not in board and "se99_unlisted" not in board
    assert board[CHAMP]["role"] == "champion" and board["se1_lgbm_mm"]["auc"] == 0.80
    assert list(board)[0] == CHAMP
    assert board["se1_lgbm_mm"]["provisional"] is True  # 13 days < 14
    p = payload()
    p["signal_engine"]["promotion"]["min_days"] = 10
    rows = ps.project(p, NOW, NOW)["leaderboard"]
    assert rows[1]["model_id"] == "se1_lgbm_mm" and rows[1]["provisional"] is False
    later = {
        b["model_id"]: b for b in ps.project(payload(), NOW, NOW + timedelta(days=1))["leaderboard"]
    }
    assert later["se5_lr_tte"]["auc"] == 0.76


def test_embargoed_champion_drops_feed():
    p = payload()
    p["signal_engine"]["models"][0]["embargoed_until"] = "2026-12-01"
    out = ps.project(p, NOW, NOW)
    assert out["status"] == "champion_hidden" and out["feed"] is None and out["champion"] is None
    assert "auc" not in next(b for b in out["leaderboard"] if b["model_id"] == CHAMP)


def test_feed_of_other_model_is_dropped_and_stale_is_flagged():
    p = payload()
    p["signal_engine"]["feed"]["champion"] = {"model_id": "se1_lgbm_mm"}
    assert ps.project(p, NOW, NOW)["feed"] is None
    out = ps.project(payload(), NOW, NOW + timedelta(hours=7))
    assert out["status"] == "stale" and out["feed"]["stale"]


def test_bad_inputs_are_unavailable():
    assert ps.project({}, None, NOW)["status"] == "unavailable"
    assert ps.project_text("not json", None, NOW)["status"] == "unavailable"
    p = payload()
    p["signal_engine"]["feed"]["top_up"][0]["url"] = "javascript:alert(1)"
    assert ps.project(p, NOW, NOW)["feed"]["top_up"][0]["url"] is None


@pytest.fixture
async def client(monkeypatch):
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)

    async def override_session():
        async with sm() as session:
            yield session

    def make(enabled):
        monkeypatch.setenv("PUBLIC_SIGNALS_ENABLED", "true" if enabled else "false")
        get_settings.cache_clear()
        app = create_app()
        app.dependency_overrides[accounts_db.get_async_session] = override_session
        return TestClient(app)

    yield make, sm
    get_settings.cache_clear()
    await engine.dispose()


async def test_route_off_by_default_then_serves_projection(client):
    make, sm = client
    with make(False) as c:
        assert c.get("/api/public/signals").status_code == 404
    with make(True) as c:
        r = c.get("/api/public/signals")
        assert r.status_code == 200 and r.json()["status"] == "unavailable"
        async with sm() as s:
            s.add(
                LabSnapshot(
                    source="host",
                    received_at=NOW,
                    payload=json.dumps(payload()),
                    payload_sha256="x",
                    size_bytes=1,
                )
            )
            await s.commit()
        r = c.get("/api/public/signals")
        body = r.json()
        assert r.status_code == 200 and body["schema"] == ps.PUBLIC_SCHEMA
        assert body["champion"]["model_id"] == CHAMP and "queue" not in body
        assert r.headers["cache-control"] == "public, max-age=60"
