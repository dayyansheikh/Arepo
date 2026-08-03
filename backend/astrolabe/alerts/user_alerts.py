"""Per-user alerting: connect the alert engine to each user's verified, opted-in preferences.

Layered on top of the user-independent quality floor in ``AlertService.base_quality_ok``:

- Only verified, active users with ``email_enabled`` and neither paused nor unsubscribed are
  considered (spec §12 verified + opt-in).
- Each user's own thresholds apply: minimum Research Priority, minimum confidence, preferred
  categories, and a short-term-only / maximum-time-to-close preference.
- A global emergency disable (``AlertConfig.enabled``) gates everything; ``test_mode`` records
  eligibility without sending.
- Per-user, per-market deduplication and cooldown via ``alert_deliveries``.
- The email body is the same honest, non-personalised research hypothesis for everyone (built by
  ``content.build_alert``): it never tells a user what to buy, sell or stake, and always carries
  the "statistical research signal, not financial advice" disclaimer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..accounts.models import AlertDelivery, AlertPreference, User
from ..domain.models import utcnow
from ..observability.logging import get_logger
from ..opportunity.schemas import OpportunityBoard, OpportunityCard
from .config import AlertConfig
from .content import build_alert
from .provider import EmailMessage, EmailProvider, provider_for
from .service import AlertService

logger = get_logger("astrolabe.alerts.user")


@dataclass
class UserAlertOutcome:
    user_id: str
    market_id: str
    action: str  # sent | test | failed | skipped_*
    reason: str
    subject: str | None = None


def _categories(pref: AlertPreference) -> set[str]:
    raw = pref.categories or ""
    return {c.strip().lower() for c in raw.split(",") if c.strip()}


def user_matches(card: OpportunityCard, pref: AlertPreference) -> tuple[bool, str]:
    """Does this card meet a single user's preferences? (Assumes the quality floor already held.)"""
    if not pref.email_enabled:
        return False, "email disabled"
    if pref.unsubscribed:
        return False, "unsubscribed"
    if pref.paused:
        return False, "alerts paused"
    if card.research_priority < pref.min_research_priority:
        return False, f"priority {card.research_priority} < {pref.min_research_priority}"
    if card.confidence < pref.min_confidence:
        return False, "confidence below user minimum"
    wanted = _categories(pref)
    if wanted:
        cat = (card.category or "").strip().lower()
        if cat not in wanted:
            return False, "category not in user preferences"
    if pref.short_term_only:
        max_hours = pref.max_hours_to_close or 168
        if card.time_remaining_hours is None or card.time_remaining_hours > max_hours:
            return False, "not a short-term opportunity"
    return True, "matches"


class UserAlertService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        config: AlertConfig | None = None,
        provider: EmailProvider | None = None,
    ):
        self.session = session
        self.config = config or AlertConfig.from_env()
        self.provider = provider or provider_for(self.config)
        # Reused for the user-independent quality floor and retry policy.
        self._base = AlertService(session, config=self.config, provider=self.provider)

    async def _eligible_users(self) -> list[tuple[User, AlertPreference]]:
        rows = await self.session.execute(
            select(User, AlertPreference)
            .join(AlertPreference, AlertPreference.user_id == User.id)
            .where(
                User.is_active.is_(True),
                User.is_verified.is_(True),
                AlertPreference.email_enabled.is_(True),
                AlertPreference.paused.is_(False),
                AlertPreference.unsubscribed.is_(False),
            )
        )
        return list(rows.all())

    async def _recent_delivery(self, user_id: str, market_id: str, now: datetime) -> bool:
        cutoff = now - timedelta(hours=self.config.cooldown_hours)
        found = await self.session.scalar(
            select(AlertDelivery.id).where(
                AlertDelivery.user_id == user_id,
                AlertDelivery.market_id == market_id,
                AlertDelivery.status.in_(("sent", "test")),
                AlertDelivery.at >= cutoff,
            )
        )
        return found is not None

    async def _record(self, user_id, card, status, detail, subject, now) -> None:
        self.session.add(
            AlertDelivery(
                user_id=user_id, market_id=card.market_id, token_id=card.token_id,
                subject=subject or "", status=status, detail=detail, at=now,
            )
        )
        await self.session.commit()

    async def process_card_for_user(
        self, card: OpportunityCard, user: User, pref: AlertPreference,
        *, now: datetime,
    ) -> UserAlertOutcome:
        uid = str(user.id)
        matched, reason = user_matches(card, pref)
        if not matched:
            return UserAlertOutcome(uid, card.market_id, "skipped_ineligible", reason)
        if await self._recent_delivery(uid, card.market_id, now):
            return UserAlertOutcome(uid, card.market_id, "skipped_cooldown", "within cooldown")

        content = build_alert(card)
        if self.config.test_mode:
            await self._record(uid, card, "test", "test mode; not sent", content.subject, now)
            return UserAlertOutcome(uid, card.market_id, "test", "recorded in test mode",
                                    content.subject)

        message = EmailMessage(
            to=user.email, sender=self.config.sender,
            subject=content.subject, text=content.text,
        )
        result = await self._base._send_with_retry(message)
        if result and result.ok:
            await self._record(uid, card, "sent", result.detail, content.subject, now)
            return UserAlertOutcome(uid, card.market_id, "sent", result.detail, content.subject)
        detail = result.detail if result else "no result"
        await self._record(uid, card, "failed", detail, content.subject, now)
        return UserAlertOutcome(uid, card.market_id, "failed", detail, content.subject)

    async def process_board(
        self, board: OpportunityBoard, *, now: datetime | None = None,
        only_high_priority: bool = True,
    ) -> list[UserAlertOutcome]:
        now = now or utcnow()
        outcomes: list[UserAlertOutcome] = []

        # Global emergency disable.
        if not self.config.enabled and not self.config.test_mode:
            return outcomes

        users = await self._eligible_users()
        if not users:
            return outcomes

        for card in board.cards:
            if only_high_priority and not card.high_priority:
                continue
            ok, _ = self._base.base_quality_ok(card)
            if not ok:
                continue
            for user, pref in users:
                outcomes.append(
                    await self.process_card_for_user(card, user, pref, now=now)
                )
        return outcomes
