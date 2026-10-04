"""Bounded screening acquisition; prospective panel admission remains a separate gate."""

import asyncio
import shutil
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import httpx

from astrolabe.feature_store.capture import Budget, _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import SourceRun, _pair, _persist

from .book_computation import LIMITS as BOOK_LIMITS
from .book_computation import record_book_computation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .original_reader import (
    _extract,
    read_original_runtime,
    read_original_screening,
)
from .panel_declaration import FIXED, PanelProtocol, read_panel_declaration, role_capacity
from .panel_selection import selection_root
from .quote_inputs import QuoteInputPolicy
from .runtime import _reserved
from .screening import (
    IDENTITY_POLICY,
    PER_DECISION_BYTES,
    ScreeningPolicy,
    _prepare_owned_screening,
    declare_screening,
    finish_screening,
)
from .screening import LIMITS as SCREEN_LIMITS
from .trigger_computation import SnapshotTriggerPolicy, record_snapshot_trigger

VERSION = "fs2-synthetic-screening-worker-v1"
PUBLIC_VERSION = "fs2-public-screening-worker-v2"
IDENTITY_VERSION = "fs2-identity-screening-worker-v3"
OWNED_VERSION = "fs2-owned-screening-worker-v4"
PILOT_VERSION = "fs2-owned-pilot-worker-v5"
MIB = 1048576
LIMITS = {
    "worker_metadata_bytes": 32 * MIB,
    "artifact_bytes": 16 * MIB,
    "failure_reserve_bytes": 65536,
    "free_reserve_bytes": 2 * 1024**3,
    "original_read_bytes": 32 * MIB,
    "max_files_per_screen": 256,
    "acquisition_seconds": 1800,
    "max_seconds": 7200,
    "live_collection_enabled": False,
}


def worker_root(panel_root):
    panel = _canonical(panel_root)
    if not panel.name.startswith("fs2_panel_"):
        raise ValueError("canonical panel root required")
    return panel.with_name("fs2_screening_worker_" + panel.name.removeprefix("fs2_panel_"))


def allocation(declaration, *, windows=False):
    p = declaration["reservation"]
    # Reserve all slots before the actual draw/role overlap is known. Original readers reserve
    # twice their 16 MiB output ceiling, allowing policy/receipt/failure metadata as well.
    slots = p["scheduled_origin_slots"] // (p["origin_slots"] // p["market_slots"])
    source = p["source_retained_bytes"] // p["source_run_slots"]
    screen = (
        slots * (source + BOOK_LIMITS["max_output_bytes"] + PER_DECISION_BYTES)
        + SCREEN_LIMITS["max_output_bytes"]
        + LIMITS["worker_metadata_bytes"]
        + LIMITS["original_read_bytes"]
    )
    future = _reserved(declaration) - LIMITS["free_reserve_bytes"]
    future += LIMITS["original_read_bytes"]  # complete eventual runtime recovery
    if windows:
        from .owned_windows import reservation

        screen += reservation(slots)
    total = screen + future
    if total > FIXED["max_panel_bytes"]:
        raise ValueError("complete screening/runtime reservation exceeds bounded ceiling")
    return {
        "screen_slots": slots,
        "source_bytes_per_screen": source,
        "screening_retained_bytes": screen,
        "future_runtime_retained_bytes": future,
        "total_retained_bytes": total,
        "required_free_bytes": total + LIMITS["free_reserve_bytes"],
        "overlap_discount_applied": False,
        **({"window_bytes": reservation(slots)} if windows else {}),
    }


def _size(root, reserved):
    total = files = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("screening worker symlink refused")
        if path.is_file():
            total += path.stat().st_size
            files += 1
        elif not path.is_dir():
            raise ValueError("screening worker nonregular path refused")
    if (
        total > reserved["screening_retained_bytes"]
        or files > 128 + reserved["screen_slots"] * (LIMITS["max_files_per_screen"]
            + (3200 if reserved.get("window_bytes", 0) else 0))
    ):
        raise ValueError("screening worker retained budget exceeded")
    return total


def _check(root, reserved, started, *, acquisition=False):
    limit = LIMITS["acquisition_seconds"] if acquisition else LIMITS["max_seconds"]
    if time.monotonic() - started > limit:
        raise ValueError("screening worker deadline exceeded")
    retained = _size(root, reserved)
    if shutil.disk_usage(root).free < reserved["required_free_bytes"] - retained:
        raise ValueError("complete remaining screening/runtime reservation unavailable")
    return retained


def _save(root, name, value, *, failure=False):
    # Only worker top-level manifests here; child writers independently enforce their caps.
    size = len(_json_bytes(value)) + 4096
    used = sum(p.stat().st_size for p in root.iterdir() if p.is_file())
    reserve = 0 if failure else LIMITS["failure_reserve_bytes"]
    if size > LIMITS["artifact_bytes"] or used + size > LIMITS["worker_metadata_bytes"] - reserve:
        raise ValueError("screening worker metadata quota exceeded")
    _persist(root, name, value)


async def _durable_call(function, *args, **kwargs):
    # Cancellation cannot leave an untracked thread writing evidence after the worker returns.
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


async def run_synthetic_screening(
    panel_root, *, implementation_commit, rule, freshness, transport, concurrency=4,
    repository=None, identity_policy=None
):
    """Acquire only owned assignments. No live transport, replacement draw, retry or activation."""
    if type(transport) is not httpx.MockTransport:
        raise ValueError("screening worker requires explicit synthetic MockTransport")
    return await _run_screening(
        panel_root, implementation_commit=implementation_commit, rule=rule, freshness=freshness,
        transport=transport, concurrency=concurrency, repository=repository,
        identity_policy=identity_policy)


async def run_public_screening(
    panel_root, *, implementation_commit, rule, freshness, concurrency=4, repository=None,
    identity_policy=None
):
    """Public read-only requests for prospective assignments; no injected transport or payload."""
    return await _run_screening(
        panel_root, implementation_commit=implementation_commit, rule=rule, freshness=freshness,
        transport=None, concurrency=concurrency, repository=repository,
        identity_policy=identity_policy)


async def run_synthetic_pilot(panel_root, *, implementation_commit, rule, freshness, transport,
                              concurrency=4, runtime_concurrency=4, repository=None):
    """Exercise the complete owned path with synthetic sources; never empirical evidence."""
    if runtime_concurrency is None:
        raise ValueError('explicit runtime concurrency required')
    if type(transport) is not httpx.MockTransport:
        raise ValueError('synthetic pilot requires MockTransport')
    return await _run_screening(
        panel_root, implementation_commit=implementation_commit, rule=rule, freshness=freshness,
        transport=transport, concurrency=concurrency, repository=repository,
        identity_policy=IDENTITY_POLICY, runtime_concurrency=runtime_concurrency)


async def run_public_pilot(panel_root, *, implementation_commit, rule, freshness,
                           concurrency=4, runtime_concurrency=4, repository=None):
    """One finite public read-only pilot. No injected payload, clock, provenance or transport."""
    if runtime_concurrency is None:
        raise ValueError('explicit runtime concurrency required')
    return await _run_screening(
        panel_root, implementation_commit=implementation_commit, rule=rule, freshness=freshness,
        transport=None, concurrency=concurrency, repository=repository,
        identity_policy=IDENTITY_POLICY, runtime_concurrency=runtime_concurrency)


async def run_public_window_pilot(panel_root, *, implementation_commit, rule, freshness,
        window_policy, concurrency=4, runtime_concurrency=4, repository=None):
    from .owned_windows import OwnedWindowPolicy

    if type(window_policy) is not OwnedWindowPolicy or runtime_concurrency is None:
        raise ValueError('explicit owned window policy and runtime concurrency required')
    return await _run_screening(panel_root, implementation_commit=implementation_commit,
        rule=rule, freshness=freshness, transport=None, concurrency=concurrency,
        runtime_concurrency=runtime_concurrency, repository=repository,
        identity_policy=IDENTITY_POLICY, window_policy=window_policy)


async def run_synthetic_window_pilot(panel_root, *, implementation_commit, rule, freshness,
        window_policy, port, transport, concurrency=4, runtime_concurrency=4, repository=None):
    from .owned_windows import OwnedWindowPolicy
    from .socket_window_journal import scope

    if (type(window_policy) is not OwnedWindowPolicy or runtime_concurrency is None
            or type(transport) is not httpx.MockTransport or port is None):
        raise ValueError('explicit synthetic window policy/transport/port/concurrency required')
    scope(port)
    return await _run_screening(panel_root, implementation_commit=implementation_commit,
        rule=rule, freshness=freshness, transport=transport, concurrency=concurrency,
        runtime_concurrency=runtime_concurrency, repository=repository,
        identity_policy=IDENTITY_POLICY, window_policy=window_policy, window_port=port)


async def _run_screening(
    panel_root, *, implementation_commit, rule, freshness, transport, concurrency, repository,
    identity_policy=None, runtime_concurrency=None, window_policy=None, window_port=None
):
    from . import owned_windows

    windows = window_policy is not None
    pilot = runtime_concurrency is not None
    if windows and (not pilot or type(window_policy) is not owned_windows.OwnedWindowPolicy):
        raise ValueError("owned pilot required for window collection")
    if pilot and (type(runtime_concurrency) is not int or not 2 <= runtime_concurrency <= 8
                  or identity_policy != IDENTITY_POLICY):
        raise ValueError('bounded owned runtime concurrency and identity policy required')
    if identity_policy not in (None, IDENTITY_POLICY):
        raise ValueError("unsupported screening identity policy")
    if transport is not None and type(transport) is not httpx.MockTransport:
        raise ValueError("unsupported screening transport")
    public = transport is None
    version = (owned_windows.VERSION if windows else PILOT_VERSION if pilot
               else OWNED_VERSION if identity_policy
               else PUBLIC_VERSION if public else VERSION)
    provenance = "prospective" if public else "synthetic"
    limits = {**LIMITS, "live_collection_enabled": public}
    if (
        type(concurrency) is not int
        or not 1 <= concurrency <= 8
        or type(rule) is not SnapshotTriggerPolicy
        or type(freshness) is not ScreeningPolicy
    ):
        raise ValueError("bounded concurrency and explicit screening policies required")
    panel, root = _canonical(panel_root), worker_root(panel_root)
    if root.exists():
        raise FileExistsError("screening worker already owned; never resume or overwrite")
    declaration = read_panel_declaration(panel)
    policy, da = _pair(panel, "panel_policy")
    protocol = PanelProtocol(**policy["protocol"])
    reserved = allocation(declaration, windows=windows)
    if pilot and declaration['reservation']['duration_seconds'] > (
        LIMITS['max_seconds'] - LIMITS['acquisition_seconds'] - 600
    ):
        raise ValueError('owned pilot duration exceeds worker budget')
    if shutil.disk_usage(root.parent).free < reserved["required_free_bytes"]:
        raise ValueError("full screening/source/recovery/runtime capacity unavailable")
    build = verified_panel_build()
    repository = _canonical(repository or Path(__file__).parents[3])
    with tempfile.TemporaryDirectory(prefix="arepo_screening_code_") as tmp:
        _extract(repository, implementation_commit, build, Path(tmp))
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    started = time.monotonic()
    budget = Budget(
        requests=2,
        bytes_per_response=protocol.source_response_bytes,
        total_bytes=2 * protocol.source_response_bytes,
        seconds_per_request=15,
        total_seconds=60,
    )
    quotes = QuoteInputPolicy(protocol.max_quote_age_seconds, protocol.max_identity_age_seconds)
    screening = root / "fs2_screening_batch"
    stage = "declaration"
    try:
        _save(
            root,
            "worker_policy",
            {
                "schema_version": version,
                **({"identity_policy": identity_policy} if identity_policy else {}),
                "build": build,
                "panel_root": str(panel),
                "panel_declaration_hash": da["payload_hash"],
                "implementation_commit": implementation_commit,
                "limits": limits,
                "reservation": reserved,
                "concurrency": concurrency,
                **({'runtime_concurrency': runtime_concurrency} if pilot else {}),
                **({"window_policy": asdict(window_policy), "window_port": window_port}
                   if windows else {}),
                "source_budget": asdict(budget),
                "source_policy": "receipt-time-selected-market-v1",
                "quote_policy": asdict(quotes),
                "rule": asdict(rule),
                "freshness": asdict(freshness),
                "declared_at": _clock(),
                "provenance_class": provenance,
                "source_paths": [
                    str(root / f"fs2_capture_screen_{i:03d}")
                    for i in range(reserved["screen_slots"])
                ],
                "live_collection_enabled": public,
                "origin_admitted": False,
                "accepted_panel": False,
            },
        )
        if identity_policy:
            frozen, finish_owned = _prepare_owned_screening(
                selection_root(panel), output_root=screening, rule=rule, policy=freshness)
        else:
            frozen = declare_screening(
                selection_root(panel), output_root=screening, rule=rule, policy=freshness)
            finish_owned = None
        if (
            frozen["source_provenance_class"] != provenance
            or len(frozen["selected"]) > reserved["screen_slots"]
        ):
            raise ValueError("screening assignment provenance or declared scope differs")
        _, wa = _pair(root, "worker_policy")
        if windows:
            acquire_window, finish_windows = owned_windows._prepare(
                root, frozen["selected"], provenance)
        semaphore = asyncio.Semaphore(concurrency)

        async def collect(index, item):
            async with semaphore:
                _check(root, reserved, started, acquisition=True)
                if verified_panel_build() != build:
                    raise ValueError("screening worker build changed")
                source = root / f"fs2_capture_screen_{index:03d}"
                _save(
                    root,
                    f"intent_{index:03d}",
                    {
                        "policy_hash": wa["payload_hash"],
                        "item": item,
                        "source_root": str(source),
                        "at": _clock(),
                    },
                )
                run = SourceRun(
                    source,
                    transport=transport,
                    budget=budget,
                    policy_version="receipt-time-selected-market-v1",
                    retained_bytes=protocol.source_run_retained_bytes,
                )
                await run.fetch("gamma.market", {"market_id": item["member"]["market_id"]})
                _check(root, reserved, started, acquisition=True)
                await run.fetch("clob.book", {"token_id": item["member"]["token_id"]})
                _check(root, reserved, started, acquisition=True)
                await _durable_call(
                    record_book_computation,
                    source,
                    output_root=Path(item["book_root"]),
                    policy=quotes,
                )
                await _durable_call(record_snapshot_trigger, Path(item["declaration_root"]))
                if windows:
                    await _durable_call(acquire_window, index)

        stage = "acquisition"
        async with asyncio.timeout(LIMITS["acquisition_seconds"]):
            async with asyncio.TaskGroup() as group:
                for index, item in enumerate(frozen["selected"]):
                    group.create_task(collect(index, item))
        stage = "screening"
        _check(root, reserved, started)
        runtime = None
        if pilot:
            from .concurrent_runtime import _exercise_owned_panel
            from .runtime import run_root

            stage = "runtime"
            screened, runtime = await _exercise_owned_panel(
                panel, screening, finish_owned=finish_owned, transport=transport,
                concurrency=runtime_concurrency,
                window_inputs=finish_windows() if windows else None)
        else:
            screened = finish_owned() if finish_owned is not None else finish_screening(screening)
        roles = role_capacity(screened["plan"], protocol)
        stage = "recovery"
        # One complete original audit after the last source/origin/target. No duplicate
        # per-child audit or full-population replay on an origin/target deadline.
        _check(root, reserved, started)
        if pilot:
            read = read_original_runtime(
                run_root(panel), implementation_commit=implementation_commit,
                repository=repository, output_root=root / "fs2_runtime_read_batch")
            if read['report'] != runtime:
                raise ValueError('original owned runtime replay differs')
        else:
            read = read_original_screening(
                screening, implementation_commit=implementation_commit,
                repository=repository, output_root=root / "fs2_screening_read_batch")
            if read["report"] != screened:
                raise ValueError("original screening replay differs")
        retained = _check(root, reserved, started)
        result = {
            "schema_version": version,
            "policy_hash": wa["payload_hash"],
            "screening": screened,
            **({'runtime': runtime} if pilot else {}),
            "role_capacity": roles,
            "recovery": [read["read_receipt"]],
            "reported_at": _clock(),
            "retained_bytes_before_report": retained,
            "state": ("pilot_collected_unaccepted" if pilot else "screening_complete")
            if roles["fits"] else "blocked_role_capacity",
            "origin_admitted": False,
            "accepted_panel": False,
        }
        _save(root, "worker_report", result)
        _check(root, reserved, started)
        return result
    except BaseException as exc:
        try:
            _save(
                root,
                "worker_failure",
                {"stage": stage, "at": _clock(), "exception_type": type(exc).__name__},
                failure=True,
            )
        except (OSError, ValueError):
            pass
        raise
