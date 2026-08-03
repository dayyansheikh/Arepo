"""Per-user alert tests (spec §16 Alerts): opt-in/verified gating, thresholds, filters, dedup."""
from datetime import UTC, datetime

import pytest

from astrolabe.accounts.models import AlertPreference, User
from astrolabe.alerts.config import AlertConfig
from astrolabe.alerts.content import DISCLAIMER, build_alert
from astrolabe.alerts.provider import OutboxProvider
from astrolabe.alerts.user_alerts import UserAlertService, user_matches
from astrolabe.opportunity.schemas import OpportunityBoard, OpportunityCard
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    await engine.dispose()


def _card(**over) -> OpportunityCard:
    base = dict(
        market_id="m1", token_id="t1", question="Will X happen?", category="Politics",
        outcome="Yes", direction="up", directional=True, hypothesis="Arepo sees moderate...",
        probability=0.42, research_priority=80, signal_strength=0.7, confidence=0.8,
        families=["price", "trade_flow"], n_families=2, high_priority=True, tags=[],
        explanation="two families agree", liquidity=50000.0, liquidity_quality="good",
        relative_spread=0.02, time_remaining_hours=48.0, end_date=None,
        data_quality="good", data_mode="live",
    )
    base.update(over)
    return OpportunityCard(**base)


def _board(cards) -> OpportunityBoard:
    return OpportunityBoard(
        generated_at=NOW, data_mode="live", count=len(cards), universe_considered=len(cards),
        cards=cards, note="test",
    )


async def _add_user(session, email, *, verified=True, **pref):
    u = User(
        email=email, hashed_password="x", is_active=True, is_verified=verified,
        is_superuser=False,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    defaults = dict(email_enabled=True, min_research_priority=60, min_confidence=0.45)
    defaults.update(pref)
    session.add(AlertPreference(user_id=u.id, **defaults))
    await session.commit()
    return u


def _svc(session, box, *, enabled=True, test_mode=False):
    cfg = AlertConfig(enabled=enabled, provider="outbox", test_mode=test_mode,
                      recipient="", sender="arepo@test", min_families=2)
    return UserAlertService(session, config=cfg, provider=box)


async def test_only_verified_optedin_users_receive(session):
    await _add_user(session, "verified@x.com", verified=True, email_enabled=True)
    await _add_user(session, "unverified@x.com", verified=False, email_enabled=True)
    await _add_user(session, "disabled@x.com", verified=True, email_enabled=False)
    box = OutboxProvider()
    outcomes = await _svc(session, box).process_board(_board([_card()]), now=NOW)
    sent = [o for o in outcomes if o.action == "sent"]
    assert len(sent) == 1
    assert len(box.sent) == 1
    assert box.sent[0].to == "verified@x.com"


async def test_global_disable_blocks_all(session):
    await _add_user(session, "a@x.com")
    box = OutboxProvider()
    outcomes = await _svc(session, box, enabled=False).process_board(_board([_card()]), now=NOW)
    assert outcomes == []
    assert box.sent == []


async def test_per_user_priority_threshold(session):
    await _add_user(session, "picky@x.com", min_research_priority=90)
    box = OutboxProvider()
    board = _board([_card(research_priority=80)])
    outcomes = await _svc(session, box).process_board(board, now=NOW)
    assert all(o.action != "sent" for o in outcomes)
    assert box.sent == []


async def test_category_filter(session):
    await _add_user(session, "sports@x.com", categories="Sports")
    box = OutboxProvider()
    out = await _svc(session, box).process_board(_board([_card(category="Politics")]), now=NOW)
    assert all(o.action != "sent" for o in out)


async def test_short_term_only_filter(session):
    await _add_user(session, "st@x.com", short_term_only=True, max_hours_to_close=24)
    box = OutboxProvider()
    board = _board([_card(time_remaining_hours=48.0)])
    out = await _svc(session, box).process_board(board, now=NOW)
    assert all(o.action != "sent" for o in out)


async def test_cooldown_dedup(session):
    await _add_user(session, "a@x.com")
    box = OutboxProvider()
    svc = _svc(session, box)
    board = _board([_card()])
    first = await svc.process_board(board, now=NOW)
    assert any(o.action == "sent" for o in first)
    second = await svc.process_board(board, now=NOW)
    assert all(o.action == "skipped_cooldown" for o in second)
    assert len(box.sent) == 1


async def test_paused_and_unsubscribed_excluded(session):
    await _add_user(session, "paused@x.com", paused=True)
    await _add_user(session, "unsub@x.com", unsubscribed=True)
    box = OutboxProvider()
    out = await _svc(session, box).process_board(_board([_card()]), now=NOW)
    assert box.sent == []
    assert all(o.action != "sent" for o in out)


async def test_quality_floor_blocks_low_family_cards(session):
    await _add_user(session, "a@x.com", min_research_priority=0)
    box = OutboxProvider()
    # Single-family card fails the user-independent floor even for a permissive user.
    out = await _svc(session, box).process_board(_board([_card(n_families=1)]), now=NOW)
    assert box.sent == []
    assert out == []  # card never reaches per-user consideration


async def test_alert_copy_has_disclaimer_and_no_personalised_advice():
    content = build_alert(_card())
    assert DISCLAIMER in content.text
    low = content.text.lower()
    for banned in ("you should buy", "you should sell", "how much to", "guaranteed profit"):
        assert banned not in low


async def test_user_matches_unit():
    ok, _ = user_matches(_card(), AlertPreference(user_id="u", email_enabled=True,
                         min_research_priority=60, min_confidence=0.45))
    assert ok is True
