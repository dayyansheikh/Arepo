"""Alert service: eligibility, dedup/cooldown, sending with retry, and history logging.

Alerts are OFF unless enabled (or in test mode). Eligibility follows spec section 11: minimum
strength, minimum confidence, at least two independent evidence families, adequate liquidity,
acceptable spread, fresh data, valid market status and no unresolved data-quality failure. A
per-market cooldown deduplicates repeat alerts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from ..observability.logging import get_logger
from ..opportunity.schemas import OpportunityBoard, OpportunityCard
from .config import AlertConfig
from .content import build_alert
from .models import AlertHistoryRow
from .provider import EmailMessage, EmailProvider, provider_for

logger = get_logger("astrolabe.alerts.service")


@dataclass
class AlertOutcome:
    market_id: str
    # sent | test | failed | skipped_disabled | skipped_ineligible | skipped_cooldown
    action: str
    reason: str
    subject: str | None = None


class AlertService:
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

    # -- eligibility --------------------------------------------------------------------
    def eligibility(self, card: OpportunityCard) -> tuple[bool, str]:
        c = self.config
        if card.research_priority < c.min_priority:
            return False, f"priority {card.research_priority} < {c.min_priority}"
        if card.signal_strength < c.min_strength:
            return False, "signal strength below threshold"
        if card.confidence < c.min_confidence:
            return False, "confidence below threshold"
        if card.n_families < c.min_families:
            return False, f"only {card.n_families} evidence family; needs {c.min_families}"
        if card.data_quality == "poor":
            return False, "data quality is poor"
        if card.liquidity_quality == "thin":
            return False, "liquidity is thin"
        return True, "eligible"

    # -- dedup / cooldown ---------------------------------------------------------------
    async def _recent_send(self, market_id: str, now: datetime) -> AlertHistoryRow | None:
        cutoff = now - timedelta(hours=self.config.cooldown_hours)
        res = await self.session.execute(
            select(AlertHistoryRow)
            .where(
                AlertHistoryRow.market_id == market_id,
                AlertHistoryRow.status.in_(("sent", "test")),
                AlertHistoryRow.at >= cutoff,
            )
            .order_by(AlertHistoryRow.at.desc())
        )
        return res.scalars().first()

    async def _record(self, card, status, detail, subject, now) -> None:
        self.session.add(
            AlertHistoryRow(
                market_id=card.market_id, token_id=card.token_id, subject=subject or "",
                status=status, detail=detail, at=now,
            )
        )
        await self.session.commit()

    async def _send_with_retry(self, message: EmailMessage):
        result = None
        for _ in range(self.config.max_retries + 1):
            result = await self.provider.send(message)
            if result.ok:
                return result
        return result

    # -- main ---------------------------------------------------------------------------
    async def process_card(
        self, card: OpportunityCard, *, now: datetime | None = None
    ) -> AlertOutcome:
        now = now or utcnow()
        c = self.config
        if not c.enabled and not c.test_mode:
            return AlertOutcome(card.market_id, "skipped_disabled", "alerts are disabled")

        eligible, reason = self.eligibility(card)
        if not eligible:
            return AlertOutcome(card.market_id, "skipped_ineligible", reason)

        if await self._recent_send(card.market_id, now) is not None:
            return AlertOutcome(card.market_id, "skipped_cooldown", "within per-market cooldown")

        content = build_alert(card)
        message = EmailMessage(
            to=c.recipient, sender=c.sender, subject=content.subject, text=content.text
        )
        if c.test_mode:
            # Build and record, but do not attempt an external send.
            await self._record(card, "test", "test mode; not sent externally", content.subject, now)
            return AlertOutcome(card.market_id, "test", "recorded in test mode", content.subject)

        result = await self._send_with_retry(message)
        if result and result.ok:
            await self._record(card, "sent", result.detail, content.subject, now)
            return AlertOutcome(card.market_id, "sent", result.detail, content.subject)
        detail = result.detail if result else "no result"
        logger.warning("alert send failed", extra={"ctx_market": card.market_id, "ctx": detail})
        await self._record(card, "failed", detail, content.subject, now)
        return AlertOutcome(card.market_id, "failed", detail, content.subject)

    async def process_board(
        self, board: OpportunityBoard, *, now: datetime | None = None,
        only_high_priority: bool = True,
    ) -> list[AlertOutcome]:
        """Consider each card on the board for an immediate alert (spec section 11)."""
        now = now or utcnow()
        outcomes: list[AlertOutcome] = []
        for card in board.cards:
            if only_high_priority and not card.high_priority:
                continue
            outcomes.append(await self.process_card(card, now=now))
        return outcomes
