"""The production scheduler tick (master prompt §11).

    python -m astrolabe.scheduler.tick run       # run one tick: do only what is DUE
    python -m astrolabe.scheduler.tick status    # print the health/observability snapshot (no work)
    python -m astrolabe.scheduler.tick run --only refresh   # force one job (manual/debug)

A hosted runner (GitHub Actions) calls ``run`` roughly every five minutes. The application decides
what is due from stored state and causal timing, then runs only that work by reusing the existing
collector functions — no research logic is duplicated here. Everything is idempotent and delay-
tolerant:

* **Late tick** — work is gated on elapsed time / causal boundaries, not an exact clock, so a late
  wake simply runs whatever is now due.
* **Duplicate tick** — a DB lease admits one heavy tick at a time; the loser exits 0.
* **Missed tick** — the next wake catches up (a refresh runs if the latest complete scan is stale; a
  cohort freezes as soon as a complete scan exists at/after its boundary). A period whose window
  fully elapsed with no in-window complete scan is honestly left unfrozen (no look-ahead).

Exit code is non-zero if any due job failed, so the runner surfaces the failure.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

from ..clients.data_api import DataApiClient
from ..config import get_settings
from ..discovery.cohort_from_scan import freeze_cohort_from_scan, latest_complete_scan
from ..discovery.refresh_cli import run_refresh
from ..evaluation.research_engine import cadence_cutoff
from ..evaluation.research_repository import ResearchRepository
from ..evaluation.research_tracking import collect_due_forward
from ..observability.logging import get_logger
from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from ..storage.migrate import preflight
from . import state as sched_state
from .retention import run_retention, storage_health

_LEASE_NAME = "scheduler-tick"
logger = get_logger("astrolabe.scheduler.tick")


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _holder() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def _due_by_interval(last_success: datetime | None, interval_minutes: int, now: datetime) -> bool:
    if last_success is None:
        return True
    return (now - _utc(last_success)) >= timedelta(minutes=interval_minutes)


async def _price_provider(service: MarketService):
    from ..domain.models import utcnow
    from ..evaluation.research_tracking import Quote

    async def price_of(market_id: str, token_id: str):
        try:
            detail = await service.market_detail(market_id, requested_mode="live")
        except Exception:  # noqa: BLE001
            return None
        if detail is None:
            return None
        for o in detail.market.outcomes:
            if o.token_id == token_id:
                return Quote(
                    midpoint=o.midpoint, best_bid=o.best_bid, best_ask=o.best_ask,
                    spread=o.spread, near_mid_depth=o.near_mid_depth, source_timestamp=utcnow(),
                )
        return None
    return price_of


async def _refresh_due(session, now: datetime) -> bool:
    settings = get_settings()
    latest = await latest_complete_scan(session)
    if latest is None:
        return True
    age = now - _utc(latest.started_at)
    return age >= timedelta(minutes=settings.scan_refresh_interval_minutes)


async def _freeze_due_cadences(session, now: datetime) -> list[str]:
    """Cadences whose current period can be causally frozen now (in-period complete scan exists)."""
    settings = get_settings()
    cadences = [c.strip() for c in settings.research_freeze_cadences.split(",") if c.strip()]
    latest = await latest_complete_scan(session)
    if latest is None:
        return []
    started = _utc(latest.started_at)
    repo = ResearchRepository(session)
    due: list[str] = []
    for cadence in cadences:
        boundary = cadence_cutoff(cadence, now)
        if started < boundary:
            continue  # no complete scan yet in this period -> cannot freeze without look-ahead
        existing = await repo.get_cohort(cadence, boundary)
        if existing is None:
            due.append(cadence)
    return due


async def run_tick(*, only: str | None = None, force: bool = False) -> dict:
    """Run one tick. Returns a JSON-able summary; ``ok`` is False if any due job failed."""
    settings = get_settings()
    engine = make_engine()
    # Schema must be current before any cohort work (fail-fast unless AUTO_MIGRATE).
    await preflight(engine, auto_migrate=settings.auto_migrate)
    sm = make_sessionmaker(engine)
    holder = _holder()
    now = datetime.now(UTC)
    jobs: dict[str, dict] = {}
    ok = True

    async with sm() as lease_session:
        got = await sched_state.acquire_lease(
            lease_session, name=_LEASE_NAME, holder=holder,
            ttl_seconds=settings.tick_lease_seconds, now=now,
        )
    if not got:
        await engine.dispose()  # release the pool on the early-exit path (duplicate-tick backoff)
        return {"ran": False, "reason": "another tick holds the lease", "ok": True, "jobs": {}}

    service = MarketService()
    data_api = DataApiClient()

    async def _job(name: str, coro_factory):
        nonlocal ok
        if only is not None and only != name:
            return
        t0 = time.time()
        logger.info("phase start", extra={"ctx_phase": name})
        try:
            async with sm() as s:
                detail = await coro_factory(s)
            await _record(name, True, time.time() - t0, detail)
            jobs[name] = {"ok": True, "detail": detail}
            logger.info("phase done", extra={"ctx_phase": name, "ctx_ok": True,
                                             "ctx_elapsed_s": round(time.time() - t0, 1)})
        except Exception as exc:  # noqa: BLE001 - one job's failure must not abort the others
            ok = False
            await _record(name, False, time.time() - t0, {"error": str(exc)})
            jobs[name] = {"ok": False, "error": str(exc)}
            logger.info("phase failed", extra={"ctx_phase": name, "ctx_ok": False,
                                               "ctx_elapsed_s": round(time.time() - t0, 1),
                                               "ctx_error": str(exc)[:200]})

    async def _record(name, success, dur, detail):
        async with sm() as s:
            await sched_state.record_attempt(
                s, job=name, ok=success, duration_seconds=dur, detail=detail)

    try:
        # 1. Complete signal refresh (heavy) — only when the latest complete scan is stale.
        async def _do_refresh(s):
            if not force and not await _refresh_due(s, now):
                return {"skipped": "recent complete scan"}
            return await run_refresh(s, service, data_api, holder=f"tick-{holder}")
        await _job("refresh", _do_refresh)

        # 2. Causally-due cohort freezes (idempotent on (cadence, cutoff)).
        async def _do_freeze(s):
            cadences = [only_c for only_c in await _freeze_due_cadences(s, now)] if not force \
                else [c.strip() for c in settings.research_freeze_cadences.split(",") if c.strip()]
            results = {}
            for cadence in cadences:
                results[cadence] = await freeze_cohort_from_scan(s, cadence=cadence)
            return {"cadences": results} if results else {"skipped": "no cadence due"}
        await _job("freeze", _do_freeze)

        # 3. Forward observations (collect only due; idempotent).
        async def _do_forward(s):
            st = await sched_state.get_state(s, "forward")
            if not force and not _due_by_interval(
                st.last_success_at if st else None, settings.forward_interval_minutes, now):
                return {"skipped": "not due"}
            provider = await _price_provider(service)
            return await collect_due_forward(s, price_of=provider)
        await _job("forward", _do_forward)

        # 4. Freeze-to-close (preclose) quotes.
        async def _do_preclose(s):
            st = await sched_state.get_state(s, "preclose")
            if not force and not _due_by_interval(
                st.last_success_at if st else None, settings.preclose_interval_minutes, now):
                return {"skipped": "not due"}
            from ..evaluation.research_preclose import collect_preclose
            provider = await _price_provider(service)
            return await collect_preclose(
                s, price_of=provider, public_only=True, within_hours=168.0)
        await _job("preclose", _do_preclose)

        # 5. Resolutions (record newly-available; idempotent).
        async def _do_resolve(s):
            st = await sched_state.get_state(s, "resolve")
            if not force and not _due_by_interval(
                st.last_success_at if st else None, settings.resolve_interval_minutes, now):
                return {"skipped": "not due"}
            from ..evaluation.service import CohortRunner
            updated = await CohortRunner(service, mode="live").check_resolutions(s)
            return {"resolutions_recorded": updated}
        await _job("resolve", _do_resolve)

        # 6. Retention / storage maintenance (roughly once a day).
        async def _do_retention(s):
            st = await sched_state.get_state(s, "retention")
            if not force and not _due_by_interval(
                st.last_success_at if st else None, settings.retention_interval_hours * 60, now):
                return {"skipped": "not due"}
            return await run_retention(s, now=now)
        await _job("retention", _do_retention)
    finally:
        t_cleanup = time.time()
        logger.info("phase start", extra={"ctx_phase": "cleanup"})
        # Bound cleanup too: a lingering httpx/asyncpg resource must not hang shutdown. Each close
        # is best-effort with its own short timeout so run_tick always returns promptly.
        for closer in (service.aclose, data_api.aclose):
            try:
                await asyncio.wait_for(closer(), timeout=30)
            except Exception:  # noqa: BLE001 - cleanup must never block termination
                pass
        try:
            async with sm() as s:
                await sched_state.release_lease(s, name=_LEASE_NAME, holder=holder)
        except Exception:  # noqa: BLE001
            pass
        try:
            await asyncio.wait_for(engine.dispose(), timeout=30)
        except Exception:  # noqa: BLE001
            pass
        logger.info("phase done", extra={"ctx_phase": "cleanup",
                                         "ctx_elapsed_s": round(time.time() - t_cleanup, 1)})

    return {"ran": True, "ok": ok, "at": now.isoformat(), "jobs": jobs}


async def health_from_session(session) -> dict:
    """Build the production health/observability snapshot from an open session (master prompt §16).

    Read-only. Raises only if the DB itself is unreachable; callers wrap it.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    latest = await latest_complete_scan(session)
    latest_scan_at = _utc(latest.started_at) if latest is not None else None
    latest_scan_age = round((now - latest_scan_at).total_seconds(), 0) if latest_scan_at else None
    jobs = {}
    for job in ("refresh", "freeze", "forward", "preclose", "resolve", "retention"):
        st = await sched_state.get_state(session, job)
        jobs[job] = None if st is None else {
            "last_attempt_at": _utc(st.last_attempt_at).isoformat() if st.last_attempt_at else None,
            "last_success_at": _utc(st.last_success_at).isoformat() if st.last_success_at else None,
            "last_ok": st.last_ok, "run_count": st.run_count, "fail_count": st.fail_count,
        }
    cohorts = await ResearchRepository(session).list_cohorts(frozen=True)
    latest_cohort = None
    if cohorts:
        c = cohorts[0]
        latest_cohort = {
            "id": c.id, "cadence": c.cadence,
            "scheduled_for": _utc(c.cutoff_at).isoformat() if c.cutoff_at else None,
            "frozen_at": _utc(c.frozen_at).isoformat() if c.frozen_at else None,
            "lateness_seconds": c.lateness_seconds, "late": c.late,
            "universe_size": c.universe_size, "directional_count": c.directional_count,
            "scan_id": c.scan_id, "scan_complete": c.scan_complete,
        }
    storage = await storage_health(session)
    # A concise refresh-health verdict the API can surface to users without engineering detail.
    stale = (latest_scan_age is not None
             and latest_scan_age > settings.scan_refresh_interval_minutes * 60 * 3)
    return {
        "db_healthy": True,
        "time": now.isoformat(),
        "environment": settings.environment,
        "latest_complete_scan_at": latest_scan_at.isoformat() if latest_scan_at else None,
        "latest_complete_scan_age_seconds": latest_scan_age,
        "scan_refresh_interval_minutes": settings.scan_refresh_interval_minutes,
        "data_delayed": stale,
        "scheduler_jobs": jobs,
        "latest_cohort": latest_cohort,
        "storage": storage,
    }


async def health_snapshot() -> dict:
    """Standalone health snapshot (CLI ``status``): opens its own engine. Never raises."""
    engine = make_engine()
    sm = make_sessionmaker(engine)
    try:
        async with sm() as s:
            return await health_from_session(s)
    except Exception as exc:  # noqa: BLE001
        return {"db_healthy": False, "error": str(exc), "time": datetime.now(UTC).isoformat()}
    finally:
        await engine.dispose()


async def _run(args: argparse.Namespace) -> int:
    if args.command == "status":
        print(json.dumps(await health_snapshot(), indent=2, default=str))
        return 0
    deadline = get_settings().tick_hard_deadline_seconds
    try:
        summary = await asyncio.wait_for(
            run_tick(only=getattr(args, "only", None), force=getattr(args, "force", False)),
            timeout=deadline,
        )
    except TimeoutError:
        # Graceful in-loop abort at the hard deadline. run_tick's finally already released the lease
        # during cancellation; report and exit non-zero.
        logger.error("tick exceeded hard deadline; aborted", extra={"ctx_deadline_s": deadline})
        summary = {"ran": True, "ok": False, "reason": f"tick exceeded {deadline}s hard deadline"}
    print(json.dumps(summary, default=str))
    return 0 if summary.get("ok", False) else 1


def _install_watchdog(deadline_seconds: int) -> None:
    """Daemon wall-clock backstop: force-exit even if the event loop / a pool refuses to close, so
    the runner is never the component that kills a normal tick. Fires slightly AFTER the graceful
    in-loop deadline, giving the clean path first chance."""
    def _kill() -> None:
        time.sleep(deadline_seconds)
        print(f"[tick] hard wall-clock deadline {deadline_seconds}s reached; forcing exit",
              flush=True)
        os._exit(2)
    threading.Thread(target=_kill, name="tick-watchdog", daemon=True).start()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.scheduler.tick", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run one tick: do only what is due")
    r.add_argument("--only", default=None,
                   choices=["refresh", "freeze", "forward", "preclose", "resolve", "retention"])
    r.add_argument("--force", action="store_true", help="ignore due-gates for the selected job(s)")
    sub.add_parser("status", help="print the health/observability snapshot (no work)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "command", None) == "run":
        # Watchdog fires just after the graceful in-loop deadline (enforced by _run via wait_for),
        # and comfortably before the workflow's timeout-minutes.
        _install_watchdog(get_settings().tick_hard_deadline_seconds + 60)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    _code = main()
    # Deterministic, immediate termination: os._exit bypasses any lingering non-daemon thread,
    # undisposed connection pool or atexit hook that could otherwise keep the process alive.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_code if isinstance(_code, int) else 0)
