"""Alert system: eligibility, wording, dedup/cooldown, provider failure, disabled, secrets."""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.alerts import models  # noqa: F401 - register table
from astrolabe.alerts.config import AlertConfig
from astrolabe.alerts.content import DISCLAIMER, build_alert
from astrolabe.alerts.models import AlertHistoryRow
from astrolabe.alerts.provider import FailingProvider, OutboxProvider
from astrolabe.alerts.service import AlertService
from astrolabe.opportunity.schemas import OpportunityCard, TagOut
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def card(*, market_id="m1", rp=70, strength=0.7, confidence=0.7, families=2, dq="good",
         liq="good", direction="up"):
    fam = ["price", "trade_flow", "timing"][:families]
    return OpportunityCard(
        market_id=market_id, token_id="t1", question="Will X happen by Friday?", outcome="Yes",
        direction=direction, probability=0.42, research_priority=rp, signal_strength=strength,
        confidence=confidence, families=fam, n_families=len(fam), high_priority=rp >= 50,
        tags=[TagOut(label="Large relative trade", family="trade_flow", explanation="big trade",
                     methodology_anchor="trade-flow", data_quality=dq, timestamp=NOW)],
        explanation="Two families agree.", liquidity=60000.0, liquidity_quality=liq,
        relative_spread=0.01, time_remaining_hours=48.0, end_date=None, data_quality=dq,
        data_mode="live",
    )


@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    await engine.dispose()


def _enabled(**over):
    base = dict(enabled=True, provider="console", recipient="x@example.com", min_priority=50,
                min_strength=0.4, min_confidence=0.4, min_families=2, cooldown_hours=12.0)
    base.update(over)
    return AlertConfig(**base)


# -- eligibility -------------------------------------------------------------------------
def test_eligibility_thresholds(session):
    svc = AlertService(session, config=_enabled(), provider=OutboxProvider())
    assert svc.eligibility(card())[0] is True
    assert svc.eligibility(card(rp=40))[0] is False
    assert svc.eligibility(card(confidence=0.1))[0] is False
    assert svc.eligibility(card(strength=0.1))[0] is False
    assert svc.eligibility(card(families=1))[0] is False       # needs >= 2 families
    assert svc.eligibility(card(dq="poor"))[0] is False
    assert svc.eligibility(card(liq="thin"))[0] is False


# -- wording -----------------------------------------------------------------------------
def test_alert_wording_honest_and_non_advisory():
    content = build_alert(card(direction="up"))
    text = content.text.lower()
    assert "repricing upwards" in text
    assert DISCLAIMER in content.text
    # Never definitive advice or instructions.
    for banned in (" buy ", " sell ", "stake", "guaranteed", "certain profit", "financial advice."):
        # "financial advice" appears only inside the disclaimer's "not financial advice".
        if banned == "financial advice.":
            assert "not financial advice" in text
        else:
            assert banned not in text
    assert "not expected profit" in text  # priority is framed correctly
    down = build_alert(card(direction="down")).text.lower()
    assert "downward pressure" in down


def test_alert_has_required_sections():
    text = build_alert(card()).text
    for section in ("Market:", "Relevant outcome:", "Research Priority:", "Signal strength:",
                    "Triggered indicators:", "What caused the signal", "What could invalidate",
                    "What you may want to examine", "Open the analysis:", "Data mode:"):
        assert section in text


# -- disabled / test mode ----------------------------------------------------------------
async def test_disabled_does_not_send(session):
    out = OutboxProvider()
    svc = AlertService(session, config=AlertConfig(enabled=False), provider=out)
    outcome = await svc.process_card(card(), now=NOW)
    assert outcome.action == "skipped_disabled"
    assert out.sent == []


async def test_test_mode_records_but_does_not_send(session):
    out = OutboxProvider()
    svc = AlertService(session, config=_enabled(enabled=False, test_mode=True), provider=out)
    outcome = await svc.process_card(card(), now=NOW)
    assert outcome.action == "test"
    assert out.sent == []  # test mode never sends externally
    rows = (await session.execute(__import__("sqlalchemy").select(AlertHistoryRow))).scalars().all()
    assert len(rows) == 1 and rows[0].status == "test"


# -- send + dedup/cooldown ---------------------------------------------------------------
async def test_send_then_cooldown_dedup(session):
    out = OutboxProvider()
    svc = AlertService(session, config=_enabled(), provider=out)
    first = await svc.process_card(card(market_id="mA"), now=NOW)
    assert first.action == "sent" and len(out.sent) == 1
    # Same market again within cooldown: skipped (dedup).
    second = await svc.process_card(card(market_id="mA"), now=NOW + timedelta(hours=1))
    assert second.action == "skipped_cooldown" and len(out.sent) == 1
    # After the cooldown window, it may alert again.
    third = await svc.process_card(card(market_id="mA"), now=NOW + timedelta(hours=13))
    assert third.action == "sent" and len(out.sent) == 2


async def test_ineligible_not_sent(session):
    out = OutboxProvider()
    svc = AlertService(session, config=_enabled(), provider=out)
    outcome = await svc.process_card(card(rp=10), now=NOW)
    assert outcome.action == "skipped_ineligible" and out.sent == []


# -- provider failure + retry ------------------------------------------------------------
async def test_provider_failure_is_recorded_and_retried(session):
    prov = FailingProvider()
    svc = AlertService(session, config=_enabled(max_retries=2), provider=prov)
    outcome = await svc.process_card(card(market_id="mF"), now=NOW)
    assert outcome.action == "failed"
    assert prov.attempts == 3  # initial + 2 retries
    rows = (await session.execute(__import__("sqlalchemy").select(AlertHistoryRow))).scalars().all()
    assert rows[0].status == "failed"


# -- no secrets --------------------------------------------------------------------------
def test_no_hardcoded_secrets_in_default_config():
    cfg = AlertConfig()
    assert cfg.smtp_password == "" and cfg.smtp_user == ""
    assert cfg.enabled is False and cfg.can_send_externally is False
    # Content never contains a password/credential field.
    text = build_alert(card()).text.lower()
    assert "password" not in text and "smtp" not in text
