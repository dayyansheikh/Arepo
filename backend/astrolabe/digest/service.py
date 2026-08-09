"""Bounded, idempotent personalised digest delivery and immutable history reads."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..accounts.email import CANONICAL_AREPO_BASE_URL, AccountEmailService, SignalDigestPreparation
from ..accounts.models import AlertPreference, DigestDelivery, DigestEntry, User
from ..alerts.config import AlertConfig
from ..alerts.provider import EmailProvider, provider_for
from ..categories import USER_SELECTABLE_CATEGORIES, primary_category
from ..config import get_settings
from ..discovery.signal_service import FRESH_MAX_INTERVALS, REFRESH_INTERVAL_SECONDS
from ..discovery.snapshot_models import ScanRunRow, SignalSnapshotRow
from ..domain.models import utcnow
from ..evaluation.models import MarketResolutionRow
from ..evaluation.research_models import ResearchCohortRow, ResearchEntryRow, ResearchForwardRow
from ..evaluation.research_replay import replay_result_state
from ..scheduler import state as scheduler_state
from ..storage.models import MarketRow
from .email import render_signal_cards
from .scheduling import due_window_key, evaluation_horizon, horizon_due_at

DIGEST_LEASE = "digest_delivery"
_SENT = "sent"
_TERMINAL = {"skipped_empty", "uncertain"}


class DigestDeferred(RuntimeError):
    """No sufficiently current complete scan is available yet; consume no due window."""


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _config() -> AlertConfig:
    settings = get_settings()
    base = AlertConfig.from_env()
    base.enabled = settings.digest_email_enabled
    base.sender = "Arepo Alerts <alerts@arepolabs.com>"
    base.max_retries = settings.digest_max_retries
    return base


def _clean_categories(values: list[str] | None) -> list[str]:
    wanted = set(values or [])
    return [category for category in USER_SELECTABLE_CATEGORIES if category in wanted]


def _categories(pref: AlertPreference) -> list[str]:
    return _clean_categories(
        [part for part in (pref.digest_categories or "").split(",") if part]
    )


def _token_secret(selector: str) -> str:
    digest = hmac.new(
        get_settings().auth_secret.encode("utf-8"),
        f"digest-unsubscribe:{selector}".encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _unsubscribe_token(delivery: DigestDelivery) -> str:
    if not delivery.unsubscribe_selector:
        raise ValueError("digest has no unsubscribe selector")
    return f"{delivery.unsubscribe_selector}.{_token_secret(delivery.unsubscribe_selector)}"


async def unsubscribe_digest(session: AsyncSession, token: str) -> bool:
    """Disable only digest delivery using an opaque selector + HMAC token."""
    try:
        selector, supplied = token.split(".", 1)
    except ValueError:
        return False
    delivery = await session.scalar(
        select(DigestDelivery).where(DigestDelivery.unsubscribe_selector == selector)
    )
    if delivery is None or not delivery.unsubscribe_secret_hash:
        return False
    expected = _token_secret(selector)
    expected_hash = hashlib.sha256(expected.encode("ascii")).hexdigest()
    if not (
        hmac.compare_digest(supplied, expected)
        and hmac.compare_digest(delivery.unsubscribe_secret_hash, expected_hash)
    ):
        return False
    pref = await session.get(AlertPreference, delivery.user_id)
    if pref is None:
        return False
    pref.digest_frequency = "off"
    pref.digest_unsubscribed = True
    pref.updated_at = utcnow()
    await session.commit()
    return True


class DigestService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: EmailProvider | None = None,
        enabled: bool | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.session = session
        self.config = _config()
        if enabled is not None:
            self.config.enabled = enabled
        if max_retries is not None:
            self.config.max_retries = max_retries
        self.provider = provider or provider_for(self.config)
        self.email = AccountEmailService(provider=self.provider)

    async def _latest_complete_scan(self, now: datetime) -> ScanRunRow | None:
        freshest_allowed = now - timedelta(
            seconds=REFRESH_INTERVAL_SECONDS * FRESH_MAX_INTERVALS
        )
        return await self.session.scalar(
            select(ScanRunRow)
            .where(
                ScanRunRow.status == "ok",
                ScanRunRow.pagination_complete.is_(True),
                ScanRunRow.started_at >= freshest_allowed,
            )
            .order_by(ScanRunRow.started_at.desc())
            .limit(1)
        )

    async def _opportunity_rows(
        self, scan: ScanRunRow
    ) -> list[tuple[SignalSnapshotRow, MarketRow | None]]:
        """Full eligible directional universe in the public Opportunities ranking order."""
        result = await self.session.execute(
            select(SignalSnapshotRow, MarketRow)
            .outerjoin(MarketRow, MarketRow.id == SignalSnapshotRow.market_id)
            .where(
                SignalSnapshotRow.scan_id == scan.scan_id,
                SignalSnapshotRow.eligible.is_(True),
                SignalSnapshotRow.direction.in_(("up", "down")),
            )
            .order_by(
                SignalSnapshotRow.research_priority.desc(),
                SignalSnapshotRow.strength.desc(),
                SignalSnapshotRow.market_id,
            )
        )
        return list(result.all())

    async def _research_entries(
        self, scan_id: str, rows: list[tuple[SignalSnapshotRow, MarketRow | None]]
    ) -> dict[tuple[str, str], ResearchEntryRow]:
        keys = {(snap.market_id, snap.token_id) for snap, _market in rows}
        if not keys:
            return {}
        result = await self.session.execute(
            select(ResearchEntryRow)
            .join(ResearchCohortRow, ResearchCohortRow.id == ResearchEntryRow.cohort_id)
            .where(
                ResearchCohortRow.scan_id == scan_id,
                ResearchCohortRow.frozen.is_(True),
                or_(
                    *(
                        (ResearchEntryRow.market_id == market_id)
                        & (ResearchEntryRow.token_id == token_id)
                        for market_id, token_id in keys
                    )
                ),
            )
            .order_by(ResearchCohortRow.frozen_at.desc())
        )
        mapped: dict[tuple[str, str], ResearchEntryRow] = {}
        for entry in result.scalars().all():
            mapped.setdefault((entry.market_id, entry.token_id), entry)
        return mapped

    async def _entries(self, digest_id: int) -> list[DigestEntry]:
        result = await self.session.scalars(
            select(DigestEntry)
            .where(DigestEntry.digest_id == digest_id)
            .order_by(DigestEntry.rank)
        )
        return list(result)

    async def _existing(self, user_id: str, window_key: str) -> DigestDelivery | None:
        return await self.session.scalar(
            select(DigestDelivery).where(
                DigestDelivery.user_id == user_id,
                DigestDelivery.due_window_key == window_key,
            )
        )

    async def create_snapshot(
        self,
        user: User,
        pref: AlertPreference,
        *,
        now: datetime,
        window_key: str | None = None,
    ) -> DigestDelivery:
        """Create one content snapshot once. A retry returns the original rows unchanged."""
        key = window_key or due_window_key(pref.digest_frequency, now)
        if key is None:
            raise ValueError("digest delivery is off")
        existing = await self._existing(str(user.id), key)
        if existing is not None:
            return existing

        scan = await self._latest_complete_scan(now)
        if scan is None:
            raise DigestDeferred("no fresh complete Opportunity scan is available")
        categories = _categories(pref)
        selector = secrets.token_urlsafe(12)
        secret_hash = hashlib.sha256(_token_secret(selector).encode("ascii")).hexdigest()
        delivery = DigestDelivery(
            user_id=str(user.id),
            due_window_key=key,
            frequency=pref.digest_frequency,
            top_n=pref.digest_top_n,
            categories=categories,
            scan_id=scan.scan_id,
            source_captured_at=scan.started_at,
            evaluation_horizon=evaluation_horizon(pref.digest_frequency),
            status="created",
            unsubscribe_selector=selector,
            unsubscribe_secret_hash=secret_hash,
            created_at=now,
        )
        self.session.add(delivery)
        try:
            await self.session.flush()
            ranked = await self._opportunity_rows(scan)
            selected: list[tuple[SignalSnapshotRow, MarketRow | None, str]] = []
            for snap, market in ranked:
                label = snap.primary_category or primary_category(
                    market.category if market else None,
                    list(market.tags or []) if market else [],
                )
                if categories and label not in categories:
                    continue
                selected.append((snap, market, label))
                if len(selected) >= pref.digest_top_n:
                    break
            research = await self._research_entries(
                scan.scan_id, [(snap, market) for snap, market, _label in selected]
            )
            if not selected:
                delivery.status = "skipped_empty"
            for rank, (snap, _market, label) in enumerate(selected, start=1):
                exact = research.get((snap.market_id, snap.token_id))
                self.session.add(
                    DigestEntry(
                        digest_id=delivery.id,
                        rank=rank,
                        market_id=snap.market_id,
                        token_id=snap.token_id,
                        market_question=snap.market_question,
                        outcome_name=snap.outcome_name,
                        category=label,
                        direction=snap.direction or "",
                        strength=snap.strength,
                        research_priority=snap.research_priority,
                        entry_price=snap.midpoint,
                        signal_captured_at=snap.captured_at,
                        research_entry_id=exact.id if exact else None,
                    )
                )
            await self.session.commit()
            await self.session.refresh(delivery)
            return delivery
        except IntegrityError:
            await self.session.rollback()
            concurrent = await self._existing(str(user.id), key)
            if concurrent is None:
                raise
            return concurrent

    async def send(self, delivery: DigestDelivery, user: User, *, now: datetime) -> str:
        if delivery.status == _SENT or delivery.status in _TERMINAL:
            return delivery.status
        entries = await self._entries(delivery.id)
        if not entries:
            delivery.status = "skipped_empty"
            await self.session.commit()
            return delivery.status
        if getattr(self.provider, "name", "") == "console":
            delivery.status = "failed"
            delivery.provider_detail = "digest provider is not configured for external delivery"
            await self.session.commit()
            return delivery.status
        # A process may have died after Resend accepted the request but before the success commit.
        # Retry inside Resend's 24-hour idempotency window; after it expires, stop automatically
        # rather than risk sending a duplicate successful email.
        last_attempt = _utc(delivery.last_attempt_at)
        if last_attempt and now - last_attempt >= timedelta(hours=24):
            delivery.status = "uncertain"
            delivery.provider_detail = "automatic retry stopped after provider idempotency window"
            await self.session.commit()
            return delivery.status

        html_cards, text_cards = render_signal_cards(entries)
        summary = (
            f"{len(entries)} current opportunit{'y' if len(entries) == 1 else 'ies'} matched "
            "your preferences."
        )
        preferences_url = f"{CANONICAL_AREPO_BASE_URL}/account?tab=preferences"
        unsubscribe_url = (
            f"{CANONICAL_AREPO_BASE_URL}/unsubscribe?"
            f"{urlencode({'token': _unsubscribe_token(delivery)})}"
        )
        idempotency_key = f"arepo-digest-{delivery.id}-{delivery.due_window_key}"
        result = None
        for _attempt in range(self.config.max_retries + 1):
            delivery.status = "sending"
            delivery.attempt_count += 1
            delivery.last_attempt_at = now
            await self.session.commit()
            result = await self.email.send_signal_digest(
                user.email,
                user_name=user.first_name,
                summary=summary,
                signals_html=html_cards,
                signals_text=text_cards,
                preferences_url=preferences_url,
                unsubscribe_url=unsubscribe_url,
                idempotency_key=idempotency_key,
            )
            if result.ok:
                delivery.status = _SENT
                delivery.sent_at = now
                delivery.provider_detail = result.detail[:500]
                await self.session.commit()
                return delivery.status
            delivery.status = "failed"
            delivery.provider_detail = result.detail[:500]
            await self.session.commit()
        return "failed"

    async def process_user(
        self,
        user: User,
        pref: AlertPreference,
        *,
        now: datetime,
        window_key: str | None = None,
    ) -> str:
        try:
            delivery = await self.create_snapshot(user, pref, now=now, window_key=window_key)
        except DigestDeferred:
            return "deferred_no_fresh_scan"
        return await self.send(delivery, user, now=now)

    async def run_due(
        self,
        *,
        now: datetime | None = None,
        holder: str = "digest-runner",
        user_email: str | None = None,
    ) -> dict:
        now = _utc(now) or utcnow()
        if not self.config.enabled:
            return {"ran": False, "reason": "digest email is disabled", "processed": 0}
        if getattr(self.provider, "name", "") == "console":
            return {"ran": False, "reason": "digest provider is not configured", "processed": 0}
        settings = get_settings()
        if not await scheduler_state.acquire_lease(
            self.session,
            name=DIGEST_LEASE,
            holder=holder,
            ttl_seconds=settings.digest_lease_seconds,
            now=now,
        ):
            return {"ran": False, "reason": "digest lease held", "processed": 0}
        counts: dict[str, int] = {}
        try:
            considered = 0
            for frequency in ("every_6h", "twice_daily", "daily", "weekly"):
                remaining = settings.digest_max_users_per_run - considered
                if remaining <= 0:
                    break
                key = due_window_key(frequency, now)
                terminal_exists = (
                    select(DigestDelivery.id)
                    .where(
                        DigestDelivery.user_id == User.id,
                        DigestDelivery.due_window_key == key,
                        DigestDelivery.status.in_((_SENT, *_TERMINAL)),
                    )
                    .exists()
                )
                query = (
                    select(User, AlertPreference)
                    .join(AlertPreference, AlertPreference.user_id == User.id)
                    .where(
                        User.is_active.is_(True),
                        User.is_verified.is_(True),
                        AlertPreference.digest_frequency == frequency,
                        AlertPreference.digest_unsubscribed.is_(False),
                        ~terminal_exists,
                    )
                    .order_by(User.id)
                    .limit(remaining)
                )
                if user_email:
                    query = query.where(
                        func.lower(User.email) == user_email.strip().lower()
                    ).limit(1)
                result = await self.session.execute(query)
                for user, pref in result.all():
                    considered += 1
                    try:
                        status = await self.process_user(
                            user, pref, now=now, window_key=key
                        )
                    except Exception:  # noqa: BLE001 - isolate one user's DB/provider failure
                        await self.session.rollback()
                        status = "error"
                    counts[status] = counts.get(status, 0) + 1
            return {"ran": True, "processed": considered, "outcomes": counts}
        finally:
            await scheduler_state.release_lease(
                self.session, name=DIGEST_LEASE, holder=holder
            )


async def list_digest_history(
    session: AsyncSession, user_id: str, *, limit: int = 20, offset: int = 0
) -> tuple[list[dict], bool]:
    counts = (
        select(DigestEntry.digest_id, func.count(DigestEntry.id).label("signal_count"))
        .group_by(DigestEntry.digest_id)
        .subquery()
    )
    result = await session.execute(
        select(DigestDelivery, counts.c.signal_count)
        .join(counts, counts.c.digest_id == DigestDelivery.id)
        .where(DigestDelivery.user_id == user_id, DigestDelivery.status == _SENT)
        .order_by(DigestDelivery.sent_at.desc(), DigestDelivery.id.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = list(result.all())
    items = [
        {
            "id": delivery.id,
            "sent_at": delivery.sent_at,
            "frequency": delivery.frequency,
            "signal_count": signal_count,
            "categories": list(delivery.categories or []),
        }
        for delivery, signal_count in rows[:limit]
    ]
    return items, len(rows) > limit


async def _exact_research_map(
    session: AsyncSession, delivery: DigestDelivery, entries: list[DigestEntry]
) -> dict[tuple[str, str], ResearchEntryRow]:
    ids = [entry.research_entry_id for entry in entries if entry.research_entry_id is not None]
    mapped: dict[tuple[str, str], ResearchEntryRow] = {}
    if ids:
        rows = await session.scalars(select(ResearchEntryRow).where(ResearchEntryRow.id.in_(ids)))
        mapped.update({(row.market_id, row.token_id): row for row in rows})
    missing = [entry for entry in entries if (entry.market_id, entry.token_id) not in mapped]
    if missing and delivery.scan_id:
        result = await session.execute(
            select(ResearchEntryRow)
            .join(ResearchCohortRow, ResearchCohortRow.id == ResearchEntryRow.cohort_id)
            .where(
                ResearchCohortRow.scan_id == delivery.scan_id,
                ResearchCohortRow.frozen.is_(True),
                or_(
                    *(
                        (ResearchEntryRow.market_id == entry.market_id)
                        & (ResearchEntryRow.token_id == entry.token_id)
                        for entry in missing
                    )
                ),
            )
        )
        for row in result.scalars().all():
            mapped.setdefault((row.market_id, row.token_id), row)
    return mapped


async def digest_detail(session: AsyncSession, user_id: str, digest_id: int) -> dict | None:
    delivery = await session.scalar(
        select(DigestDelivery).where(
            DigestDelivery.id == digest_id,
            DigestDelivery.user_id == user_id,
            DigestDelivery.status == _SENT,
        )
    )
    if delivery is None:
        return None
    entries = list(
        await session.scalars(
            select(DigestEntry)
            .where(DigestEntry.digest_id == digest_id)
            .order_by(DigestEntry.rank)
        )
    )
    research = await _exact_research_map(session, delivery, entries)
    research_ids = [row.id for row in research.values()]
    forwards: dict[int, ResearchForwardRow] = {}
    if research_ids:
        result = await session.scalars(
            select(ResearchForwardRow).where(
                ResearchForwardRow.entry_id.in_(research_ids),
                ResearchForwardRow.horizon == delivery.evaluation_horizon,
            )
        )
        forwards = {row.entry_id: row for row in result}
    market_ids = {entry.market_id for entry in entries}
    resolutions: dict[str, MarketResolutionRow] = {}
    if market_ids:
        result = await session.scalars(
            select(MarketResolutionRow).where(MarketResolutionRow.market_id.in_(market_ids))
        )
        resolutions = {row.market_id: row for row in result}
    now = utcnow()
    output_entries: list[dict] = []
    for entry in entries:
        research_entry = research.get((entry.market_id, entry.token_id))
        fwd = forwards.get(research_entry.id) if research_entry else None
        unavailable_reason = fwd.unavailable_reason if fwd else None
        if research_entry is None:
            state = (
                "pending"
                if now < horizon_due_at(entry.signal_captured_at, delivery.evaluation_horizon)
                else "unavailable"
            )
            if state == "unavailable":
                unavailable_reason = (
                    "No exact prospective cohort observation exists for this signal."
                )
        elif (
            fwd
            and fwd.midpoint is None
            and "closed before" in (fwd.unavailable_reason or "").lower()
        ):
            state = "closed_before_horizon"
        else:
            state = replay_result_state(entry.direction, entry.entry_price, fwd)
        resolution = resolutions.get(entry.market_id)
        resolved = bool(resolution and resolution.resolved)
        resolution_correct = None
        if resolved and resolution.resolved_token_id is not None:
            resolution_correct = resolution.resolved_token_id == entry.token_id
        output_entries.append(
            {
                "rank": entry.rank,
                "market_id": entry.market_id,
                "token_id": entry.token_id,
                "market_question": entry.market_question,
                "outcome_name": entry.outcome_name,
                "canonical_url": SignalDigestPreparation.market_url(entry.market_id),
                "category": entry.category,
                "direction": entry.direction,
                "strength": entry.strength,
                "research_priority": entry.research_priority,
                "signal_captured_at": entry.signal_captured_at,
                "evaluation": {
                    "horizon": delivery.evaluation_horizon,
                    "state": state,
                    "unavailable_reason": unavailable_reason,
                    "resolved": resolved,
                    "resolved_outcome": resolution.resolved_outcome if resolved else None,
                    "resolution_correct": resolution_correct,
                },
            }
        )
    return {
        "id": delivery.id,
        "sent_at": delivery.sent_at,
        "frequency": delivery.frequency,
        "categories": list(delivery.categories or []),
        "evaluation_horizon": delivery.evaluation_horizon,
        "entries": output_entries,
    }
