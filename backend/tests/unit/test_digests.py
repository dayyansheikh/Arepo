"""Personalised digest selection, history, retry, isolation and unsubscribe tests."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import func, select

from astrolabe.accounts.models import AlertPreference, DigestDelivery, DigestEntry, User
from astrolabe.alerts.provider import EmailMessage, FailingProvider, OutboxProvider, SendResult
from astrolabe.digest.categories import (
    DIGEST_CATEGORIES,
    DIGEST_PREFERENCE_CATEGORIES,
    digest_category,
)
from astrolabe.digest.scheduling import due_window_key, evaluation_horizon, window_start
from astrolabe.digest.service import (
    DigestService,
    digest_detail,
    list_digest_history,
    unsubscribe_digest,
)
from astrolabe.discovery.snapshot_models import ScanRunRow, SignalSnapshotRow
from astrolabe.storage.db import Base, make_engine, make_sessionmaker
from astrolabe.storage.models import MarketRow

NOW = datetime(2099, 8, 10, 6, 20, tzinfo=UTC)


@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = make_sessionmaker(engine)
    async with maker() as value:
        yield value
    await engine.dispose()


async def _user(session, email: str = "ada@example.com") -> tuple[User, AlertPreference]:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="not-used-in-this-unit-test",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        first_name="Ada",
        last_name="Lovelace",
        auth_provider="local",
        created_at=NOW,
    )
    pref = AlertPreference(
        user_id=str(user.id),
        email_enabled=True,
        unsubscribed=False,
        digest_frequency="every_6h",
        digest_top_n=10,
        digest_unsubscribed=False,
        digest_categories="Crypto",
        updated_at=NOW,
    )
    session.add_all([user, pref])
    await session.commit()
    return user, pref


async def _scan(session, count: int = 22) -> None:
    session.add(
        ScanRunRow(
            scan_id="complete-scan",
            started_at=NOW,
            finished_at=NOW,
            duration_seconds=60,
            pagination_complete=True,
            pages_fetched=10,
            raw_discovered=100,
            unique_markets=100,
            eligible_30d=count,
            analysed=count,
            directional=count,
            status="ok",
            public_selection_limit=20,
            selection_policy="short-horizon-public-20-v1",
            created_at=NOW,
        )
    )
    for index in range(count):
        market_id = f"market-{index:02d}"
        crypto = index in {0, 1, 20, 21}
        session.add(
            MarketRow(
                id=market_id,
                question=f"Market {index}",
                slug=market_id,
                category="Crypto" if crypto else "Sports",
                tags=["Crypto"] if crypto else ["Sports"],
                updated_at=NOW,
            )
        )
        session.add(
            SignalSnapshotRow(
                scan_id="complete-scan",
                captured_at=NOW,
                market_id=market_id,
                token_id=f"token-{index:02d}",
                market_question=(
                    "Will <script>alert(1)</script> win?" if index == 0 else f"Market {index}?"
                ),
                outcome_name="Yes",
                eligible=True,
                direction="up",
                strength=1 - index / 100,
                confidence=0.8,
                research_priority=100 - index,
                n_families=2,
                midpoint=0.5,
                selection_policy="short-horizon-public-20-v1",
                created_at=NOW,
            )
        )
    await session.commit()


def test_due_windows_are_fixed_utc_boundaries():
    assert window_start("every_6h", datetime(2026, 8, 9, 17, 2, tzinfo=UTC)).hour == 12
    assert window_start("twice_daily", datetime(2026, 8, 9, 17, 2, tzinfo=UTC)).hour == 12
    assert window_start("daily", datetime(2026, 8, 9, 5, 59, tzinfo=UTC)) == datetime(
        2026, 8, 8, 6, tzinfo=UTC
    )
    assert window_start("weekly", datetime(2026, 8, 9, 12, tzinfo=UTC)) == datetime(
        2026, 8, 3, 6, tzinfo=UTC
    )
    assert due_window_key("off", NOW) is None
    assert evaluation_horizon("weekly") == "7d"


def test_other_is_internal_but_not_a_selectable_preference():
    assert digest_category("unclassified", []) == "Other"
    assert "Other" in DIGEST_CATEGORIES
    assert "Other" not in DIGEST_PREFERENCE_CATEGORIES


async def test_all_categories_includes_internal_other_markets(session):
    user, pref = await _user(session)
    pref.digest_categories = ""
    pref.digest_top_n = 20
    await _scan(session, count=4)
    unclassified = await session.get(MarketRow, "market-02")
    assert unclassified is not None
    unclassified.category = "Unclassified"
    unclassified.tags = []
    await session.commit()

    assert await DigestService(
        session, provider=OutboxProvider(), enabled=True, max_retries=0
    ).process_user(user, pref, now=NOW) == "sent"
    delivery = await session.scalar(select(DigestDelivery))
    entries = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))

    assert delivery is not None and delivery.categories == []
    assert [entry.market_id for entry in entries] == [
        "market-00", "market-01", "market-02", "market-03"
    ]
    assert [entry.category for entry in entries] == ["Crypto", "Crypto", "Other", "Sports"]


async def test_category_filtering_precedes_top_n_and_history_matches_sent_snapshot(session):
    user, pref = await _user(session)
    await _scan(session)
    outbox = OutboxProvider()
    service = DigestService(session, provider=outbox, enabled=True, max_retries=0)

    assert await service.process_user(user, pref, now=NOW) == "sent"
    delivery = await session.scalar(select(DigestDelivery))
    entries = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))

    assert delivery is not None and delivery.top_n == 10
    # Category matching uses the full eligible ranked universe, not the public Top-20 display cap.
    expected_ids = ["market-00", "market-01", "market-20", "market-21"]
    assert [entry.market_id for entry in entries] == expected_ids
    assert len(outbox.sent) == 1
    message = outbox.sent[0]
    assert message.template_id == "arepo-signals-digest"
    assert message.template_variables["USER_NAME"] == "Ada"
    content = str(message.template_variables["SIGNALS_CONTENT"])
    assert "&lt;script&gt;" in content and "<script>" not in content
    assert "https://www.arepolabs.com/markets/market-00" in content
    assert message.server_render_template is True
    assert message.trusted_html_variables == {"SIGNALS_CONTENT"}
    history, has_more = await list_digest_history(session, str(user.id))
    assert has_more is False
    assert len(history) == 1 and history[0]["signal_count"] == len(expected_ids)
    detail = await digest_detail(session, str(user.id), delivery.id)
    assert detail is not None
    assert [entry["market_id"] for entry in detail["entries"]] == expected_ids


async def test_digest_never_relaxes_eligibility_or_direction_thresholds(session):
    user, pref = await _user(session)
    await _scan(session)
    ineligible = await session.scalar(
        select(SignalSnapshotRow).where(SignalSnapshotRow.market_id == "market-00")
    )
    abstention = await session.scalar(
        select(SignalSnapshotRow).where(SignalSnapshotRow.market_id == "market-01")
    )
    assert ineligible is not None and abstention is not None
    ineligible.eligible = False
    abstention.direction = None
    await session.commit()

    await DigestService(
        session, provider=OutboxProvider(), enabled=True, max_retries=0
    ).process_user(user, pref, now=NOW)
    entries = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))

    assert [entry.market_id for entry in entries] == ["market-20", "market-21"]


async def test_digest_respects_top_n_after_category_filtering(session):
    user, pref = await _user(session)
    pref.digest_top_n = 5
    await _scan(session, count=12)
    for index in range(12):
        market = await session.get(MarketRow, f"market-{index:02d}")
        assert market is not None
        market.category = "Crypto"
        market.tags = ["Crypto"]
    await session.commit()

    await DigestService(
        session, provider=OutboxProvider(), enabled=True, max_retries=0
    ).process_user(user, pref, now=NOW)
    entries = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))

    assert [entry.market_id for entry in entries] == [
        "market-00", "market-01", "market-02", "market-03", "market-04"
    ]


async def test_same_due_window_is_idempotent_and_history_is_immutable(session):
    user, pref = await _user(session)
    await _scan(session)
    outbox = OutboxProvider()
    service = DigestService(session, provider=outbox, enabled=True, max_retries=0)

    await service.process_user(user, pref, now=NOW)
    first = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))
    frozen_question = first[0].market_question
    source = await session.scalar(
        select(SignalSnapshotRow).where(SignalSnapshotRow.market_id == "market-00")
    )
    source.market_question = "Changed live question"
    source.strength = 0.01
    await session.commit()

    await service.process_user(user, pref, now=NOW)
    second = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))
    assert len(outbox.sent) == 1
    assert await session.scalar(select(func.count(DigestDelivery.id))) == 1
    assert second[0].market_question == frozen_question
    assert second[0].strength == first[0].strength


async def test_failed_delivery_retries_same_snapshot_without_duplicate_rows(session):
    user, pref = await _user(session)
    await _scan(session)
    failing = FailingProvider()
    first_service = DigestService(session, provider=failing, enabled=True, max_retries=0)
    assert await first_service.process_user(user, pref, now=NOW) == "failed"
    before = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))

    outbox = OutboxProvider()
    retry_service = DigestService(session, provider=outbox, enabled=True, max_retries=0)
    assert await retry_service.process_user(user, pref, now=NOW) == "sent"
    after = list(await session.scalars(select(DigestEntry).order_by(DigestEntry.rank)))
    delivery = await session.scalar(select(DigestDelivery))

    assert failing.attempts == 1 and len(outbox.sent) == 1
    assert delivery is not None and delivery.attempt_count == 2
    assert [entry.id for entry in after] == [entry.id for entry in before]


@dataclass
class FailOnceProvider:
    name: str = "fail-once"
    attempts: int = 0
    sent: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> SendResult:
        self.attempts += 1
        if self.attempts == 1:
            return SendResult(False, "temporary")
        self.sent.append(message)
        return SendResult(True, "sent")


async def test_transient_failure_retries_with_one_provider_idempotency_key(session):
    user, pref = await _user(session)
    await _scan(session)
    provider = FailOnceProvider()
    service = DigestService(session, provider=provider, enabled=True, max_retries=1)
    assert await service.process_user(user, pref, now=NOW) == "sent"
    assert provider.attempts == 2 and len(provider.sent) == 1
    assert provider.sent[0].idempotency_key.startswith("arepo-digest-")


async def test_failed_delivery_is_not_retried_after_provider_idempotency_window(session):
    user, pref = await _user(session)
    await _scan(session)
    assert await DigestService(
        session, provider=FailingProvider(), enabled=True, max_retries=0
    ).process_user(user, pref, now=NOW) == "failed"

    outbox = OutboxProvider()
    status = await DigestService(
        session, provider=outbox, enabled=True, max_retries=0
    ).process_user(
        user,
        pref,
        now=NOW + timedelta(hours=24, seconds=1),
        window_key=due_window_key(pref.digest_frequency, NOW),
    )

    assert status == "uncertain"
    assert outbox.sent == []


async def test_unsubscribe_disables_only_digest_and_token_exposes_no_user_identity(session):
    user, pref = await _user(session)
    await _scan(session)
    outbox = OutboxProvider()
    await DigestService(session, provider=outbox, enabled=True, max_retries=0).process_user(
        user, pref, now=NOW
    )
    url = str(outbox.sent[0].template_variables["AREPO_UNSUBSCRIBE_LINK"])
    assert str(user.id) not in url and user.email not in url
    token = parse_qs(urlparse(url).query)["token"][0]
    assert await unsubscribe_digest(session, token) is True

    await session.refresh(pref)
    assert pref.digest_frequency == "off" and pref.digest_unsubscribed is True
    assert pref.email_enabled is True and pref.unsubscribed is False
    assert await unsubscribe_digest(session, "invalid.selector") is False


async def test_history_is_user_scoped_and_reports_truthful_pending_state(session):
    user_a, pref_a = await _user(session, "a@example.com")
    user_b, _pref_b = await _user(session, "b@example.com")
    await _scan(session)
    await DigestService(
        session, provider=OutboxProvider(), enabled=True, max_retries=0
    ).process_user(user_a, pref_a, now=NOW)
    delivery = await session.scalar(select(DigestDelivery))
    assert delivery is not None

    a_items, a_more = await list_digest_history(session, str(user_a.id))
    b_items, _ = await list_digest_history(session, str(user_b.id))
    assert len(a_items) == 1 and a_more is False
    assert b_items == []
    assert await digest_detail(session, str(user_b.id), delivery.id) is None
    detail = await digest_detail(session, str(user_a.id), delivery.id)
    assert detail is not None
    assert all(entry["evaluation"]["state"] == "pending" for entry in detail["entries"])


async def test_no_fresh_complete_scan_defers_without_demo_or_history_rows(session):
    user, pref = await _user(session)
    outbox = OutboxProvider()
    status = await DigestService(
        session, provider=outbox, enabled=True, max_retries=0
    ).process_user(user, pref, now=NOW)
    assert status == "deferred_no_fresh_scan"
    assert outbox.sent == []
    assert await session.scalar(select(func.count(DigestDelivery.id))) == 0
