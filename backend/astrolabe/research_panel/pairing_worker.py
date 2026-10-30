"""D120 screen-then-activate worker: screen the group-disjoint list, then activate pairs only.

Order (one owned process, no caller payload, clock or provenance):

1. own every screened member (intent, ``gamma.market`` + ``clob.book``, book computation and
   the frozen snapshot trigger) with no window: screened members are receipts and screening
   computations only;
2. seal the screening; the role draw (first available triggered member, first available
   untriggered member, per drawn stratum) is part of the sealed screening plan;
3. for activated members only: a fresh binding read (``gamma.market`` + ``clob.book``), its book
   computation and a recomputed snapshot trigger (declared before the read), then the owned
   10 s socket window bound to that fresh book;
4. activation, origins and targets in the owned concurrent runtime; one original-code audit.

Roles are fixed at screening. The binding trigger is the recomputed trigger state recorded
before each origin; a disagreement with the screening role is counted descriptively by the
evaluator and is never relabelled.
"""

import asyncio
import shutil
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import httpx

from astrolabe.feature_store.capture import Budget, _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import SourceRun, _pair

from . import owned_windows
from .book_computation import LIMITS as BOOK_LIMITS
from .book_computation import record_book_computation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .original_reader import _extract, read_original_runtime
from .pairing_declaration import (
    VERSION as DECLARATION_VERSION,
)
from .pairing_declaration import (
    PairingPanelProtocol,
    read_pairing_declaration,
    role_capacity,
)
from .panel_declaration import FIXED
from .panel_selection import selection_root
from .quote_inputs import QuoteInputPolicy
from .runtime import _reserved
from .screening import (
    IDENTITY_POLICY,
    PER_DECISION_BYTES,
    ScreeningPolicy,
    _prepare_owned_screening,
)
from .screening import LIMITS as SCREEN_LIMITS
from .screening_worker import LIMITS, _durable_call, _save, worker_root
from .trigger_computation import (
    SnapshotTriggerPolicy,
    declare_snapshot_trigger,
    record_snapshot_trigger,
)

VERSION = 'fs2-pairing-worker-v8'
BINDINGS = 'bindings'
SCREEN_SOURCE = 'fs2_capture_screen_'
BIND_SOURCE = 'fs2_capture_bind_'
BIND_BOOK = 'fs2_book_computation_bind_'
BIND_DECLARATION = 'fs2_trigger_declaration_bind_'


def allocation(declaration):
    """Screened receipts + bounded screening metadata; bindings/windows for origin slots only."""
    p = declaration['reservation']
    origins = p['origin_slots']
    source = p['source_retained_bytes'] // p['source_run_slots']
    screen = (p['screened_retained_bytes'] + SCREEN_LIMITS['max_output_bytes']
              + LIMITS['worker_metadata_bytes'] + LIMITS['original_read_bytes'])
    binding = origins * (source + BOOK_LIMITS['max_output_bytes'] + PER_DECISION_BYTES)
    windows = owned_windows.reservation(origins)
    future = _reserved(declaration) - LIMITS['free_reserve_bytes'] + LIMITS['original_read_bytes']
    total = screen + binding + windows + future
    if total > FIXED['max_panel_bytes']:
        raise ValueError('complete pairing screening/runtime reservation exceeds bounded ceiling')
    return {'screen_slots': p['screened_slots'], 'window_slots': origins,
            'source_bytes_per_screen': source,
            'screened_retained_bytes': p['screened_retained_bytes'],
            'binding_retained_bytes': binding, 'window_bytes': windows,
            'screening_retained_bytes': screen + binding + windows,
            'future_runtime_retained_bytes': future, 'total_retained_bytes': total,
            'required_free_bytes': total + LIMITS['free_reserve_bytes'],
            'overlap_discount_applied': False}


def _size(root, reserved):
    total = files = 0
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('pairing worker symlink refused')
        if path.is_file():
            total += path.stat().st_size
            files += 1
        elif not path.is_dir():
            raise ValueError('pairing worker nonregular path refused')
    if (total > reserved['screening_retained_bytes']
            or files > 128 + reserved['screen_slots'] * LIMITS['max_files_per_screen']
            + reserved['window_slots'] * (LIMITS['max_files_per_screen'] + 3200)):
        raise ValueError('pairing worker retained budget exceeded')
    return total


def _check(root, reserved, started, *, acquisition=False):
    limit = LIMITS['acquisition_seconds'] if acquisition else LIMITS['max_seconds']
    if time.monotonic() - started > limit:
        raise ValueError('pairing worker deadline exceeded')
    retained = _size(root, reserved)
    if shutil.disk_usage(root).free < reserved['required_free_bytes'] - retained:
        raise ValueError('complete remaining pairing/runtime reservation unavailable')
    return retained


def binding_items(root, frozen, screened):
    """Activated members in screening order, with their fresh binding paths (pure)."""
    roles = {}
    for role in screened['plan']['assignments']:
        roles.setdefault(role['market_id'], []).append(role['arm'])
    items = []
    for index, item in enumerate(frozen['selected']):
        arms = roles.get(item['member']['market_id'])
        if not arms:
            continue
        k = len(items)
        items.append({
            'member': item['member'], 'identity': item['identity'],
            'screening_assignment': item['screening_assignment'],
            'screening_index': index, 'arms': sorted(arms),
            'source_root': str(root / f'{BIND_SOURCE}{k:03d}'),
            'book_root': str(root / f'{BIND_BOOK}{k:03d}'),
            'declaration_root': str(root / f'{BIND_DECLARATION}{k:03d}'),
        })
    return items


def read_bindings(root):
    """The persisted binding list of a pairing worker (``bindings.json`` pair)."""
    value, ack = _pair(_canonical(root), BINDINGS)
    return {**value, 'bindings_hash': ack['payload_hash'], 'bindings_available_at':
            ack['durable_ack']}


async def run_pairing_window_pilot(panel_root, *, implementation_commit, rule, freshness,
                                   window_policy, concurrency=8, runtime_concurrency=8,
                                   repository=None):
    """One finite public read-only D120 run. No injected payload, clock, provenance or transport."""
    return await _run(panel_root, implementation_commit=implementation_commit, rule=rule,
                      freshness=freshness, window_policy=window_policy, transport=None,
                      port=None, concurrency=concurrency,
                      runtime_concurrency=runtime_concurrency, repository=repository)


async def run_synthetic_pairing_pilot(panel_root, *, implementation_commit, rule, freshness,
                                      window_policy, port, transport, concurrency=8,
                                      runtime_concurrency=8, repository=None):
    """Exercise the complete D120 path on synthetic sources; never empirical evidence."""
    from .socket_window_journal import scope

    if type(transport) is not httpx.MockTransport or port is None:
        raise ValueError('explicit synthetic transport and loopback port required')
    scope(port)
    return await _run(panel_root, implementation_commit=implementation_commit, rule=rule,
                      freshness=freshness, window_policy=window_policy, transport=transport,
                      port=port, concurrency=concurrency,
                      runtime_concurrency=runtime_concurrency, repository=repository)


async def _run(panel_root, *, implementation_commit, rule, freshness, window_policy, transport,
               port, concurrency, runtime_concurrency, repository):
    from . import activation as activation_module
    from .concurrent_runtime import _exercise_owned_panel
    from .runtime import run_root

    if (type(window_policy) is not owned_windows.OwnedWindowPolicy
            or type(rule) is not SnapshotTriggerPolicy or type(freshness) is not ScreeningPolicy
            or type(concurrency) is not int or not 1 <= concurrency <= 8
            or type(runtime_concurrency) is not int or not 2 <= runtime_concurrency <= 8):
        raise ValueError('explicit window/screening policies and bounded concurrency required')
    if transport is not None and type(transport) is not httpx.MockTransport:
        raise ValueError('unsupported pairing transport')
    public = transport is None
    provenance = 'prospective' if public else 'synthetic'
    panel, root = _canonical(panel_root), worker_root(panel_root)
    if root.exists():
        raise FileExistsError('pairing worker already owned; never resume or overwrite')
    declaration = read_pairing_declaration(panel)
    policy, da = _pair(panel, 'panel_policy')
    if policy['schema_version'] != DECLARATION_VERSION:
        raise ValueError('pairing declaration required')
    protocol = PairingPanelProtocol(**policy['protocol'])
    reserved = allocation(declaration)
    if declaration['reservation']['duration_seconds'] > (
            LIMITS['max_seconds'] - LIMITS['acquisition_seconds'] - 600):
        raise ValueError('owned pilot duration exceeds worker budget')
    if shutil.disk_usage(root.parent).free < reserved['required_free_bytes']:
        raise ValueError('full screening/binding/window/runtime capacity unavailable')
    build = verified_panel_build()
    repository = _canonical(repository or Path(__file__).parents[3])
    with tempfile.TemporaryDirectory(prefix='arepo_pairing_code_') as tmp:
        _extract(repository, implementation_commit, build, Path(tmp))
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    started = time.monotonic()
    budget = Budget(requests=2, bytes_per_response=protocol.source_response_bytes,
                    total_bytes=2 * protocol.source_response_bytes, seconds_per_request=15,
                    total_seconds=60)
    quotes = QuoteInputPolicy(protocol.max_quote_age_seconds, protocol.max_identity_age_seconds)
    screening = root / 'fs2_screening_batch'
    stage = 'declaration'
    limits = {**LIMITS, 'live_collection_enabled': public}
    try:
        _save(root, 'worker_policy', {
            'schema_version': VERSION, 'identity_policy': IDENTITY_POLICY, 'build': build,
            'panel_root': str(panel), 'panel_declaration_hash': da['payload_hash'],
            'implementation_commit': implementation_commit, 'limits': limits,
            'reservation': reserved, 'concurrency': concurrency,
            'runtime_concurrency': runtime_concurrency,
            'window_policy': owned_windows.policy_dict(window_policy), 'window_port': port,
            'source_budget': asdict(budget), 'source_policy': 'receipt-time-selected-market-v1',
            'quote_policy': asdict(quotes), 'rule': asdict(rule), 'freshness': asdict(freshness),
            'declared_at': _clock(), 'provenance_class': provenance,
            'pairing_design': policy['pairing_design'], 'activate_screened': False,
            'binding_policy': 'fresh gamma.market + clob.book and recomputed snapshot trigger '
                              'per activated member, declared before its read',
            'live_collection_enabled': public, 'origin_admitted': False,
            'accepted_panel': False,
        })
        _, wa = _pair(root, 'worker_policy')
        frozen, finish_owned = _prepare_owned_screening(
            selection_root(panel), output_root=screening, rule=rule, policy=freshness)
        if (frozen['source_provenance_class'] != provenance
                or frozen['schema_version'] != 'fs2-screening-pairing-v5'
                or len(frozen['selected']) > reserved['screen_slots']):
            raise ValueError('screening assignment provenance, version or scope differs')
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch(source, member):
            run = SourceRun(source, transport=transport, budget=budget,
                            policy_version='receipt-time-selected-market-v1',
                            retained_bytes=protocol.source_run_retained_bytes)
            await run.fetch('gamma.market', {'market_id': member['market_id']})
            _check(root, reserved, started, acquisition=True)
            await run.fetch('clob.book', {'token_id': member['token_id']})
            _check(root, reserved, started, acquisition=True)

        async def screen(index, item):
            async with semaphore:
                _check(root, reserved, started, acquisition=True)
                if verified_panel_build() != build:
                    raise ValueError('pairing worker build changed')
                source = root / f'{SCREEN_SOURCE}{index:03d}'
                _save(root, f'intent_{index:03d}', {'policy_hash': wa['payload_hash'],
                      'item': item, 'source_root': str(source), 'at': _clock()})
                await fetch(source, item['member'])
                await _durable_call(record_book_computation, source,
                                    output_root=Path(item['book_root']), policy=quotes)
                await _durable_call(record_snapshot_trigger, Path(item['declaration_root']))

        stage = 'screening_acquisition'
        async with asyncio.timeout(LIMITS['acquisition_seconds']):
            async with asyncio.TaskGroup() as group:
                for index, item in enumerate(frozen['selected']):
                    group.create_task(screen(index, item))
        stage = 'screening'
        _check(root, reserved, started)
        screened = finish_owned(activate=False)
        roles = role_capacity(screened['plan'], protocol)
        if not roles['fits']:
            raise ValueError('drawn roles exceed the declared origin slots')
        stage = 'binding'
        items = binding_items(root, frozen, screened)
        _save(root, BINDINGS, {'policy_hash': wa['payload_hash'],
                               'screening_report_hash': screened['screening_report_hash'],
                               'items': items, 'declared_at': _clock()})
        for item in items:
            declare_snapshot_trigger(_canonical(item['declaration_root']),
                                     book_root=_canonical(item['book_root']),
                                     market_id=item['member']['market_id'],
                                     token_id=item['member']['token_id'], policy=rule)
        window_inputs = None
        if items:
            acquire_window, finish_windows = owned_windows._prepare(root, items, provenance)

            async def bind(k, item):
                async with semaphore:
                    _check(root, reserved, started, acquisition=True)
                    if verified_panel_build() != build:
                        raise ValueError('pairing worker build changed')
                    source = Path(item['source_root'])
                    await fetch(source, item['member'])
                    await _durable_call(record_book_computation, source,
                                        output_root=Path(item['book_root']), policy=quotes)
                    await _durable_call(record_snapshot_trigger, Path(item['declaration_root']))
                    await _durable_call(acquire_window, k)

            async with asyncio.timeout(LIMITS['acquisition_seconds']):
                async with asyncio.TaskGroup() as group:
                    for k, item in enumerate(items):
                        group.create_task(bind(k, item))
            window_inputs = finish_windows()
        _check(root, reserved, started)
        stage = 'runtime'
        minted = []

        def finisher(*, activate=False):
            # Minted here from the sealed screening; activates exactly once.
            if activate is not True or minted:
                raise ValueError('pairing activation is minted once by its worker')
            minted.append(True)
            return screened, activation_module._activate_owned_panel(panel, screening, screened)

        _, runtime = await _exercise_owned_panel(
            panel, screening, finish_owned=finisher, transport=transport,
            concurrency=runtime_concurrency, window_inputs=window_inputs, pairing=True)
        stage = 'recovery'
        _check(root, reserved, started)
        read = read_original_runtime(run_root(panel), implementation_commit=implementation_commit,
                                     repository=repository,
                                     output_root=root / 'fs2_runtime_read_batch')
        if read['report'] != runtime:
            raise ValueError('original owned runtime replay differs')
        retained = _check(root, reserved, started)
        result = {
            'schema_version': VERSION, 'policy_hash': wa['payload_hash'],
            'screening': screened, 'runtime': runtime, 'role_capacity': roles,
            'bindings': [{'market_id': i['member']['market_id'], 'arms': i['arms'],
                          'screening_index': i['screening_index']} for i in items],
            'recovery': [read['read_receipt']], 'reported_at': _clock(),
            'retained_bytes_before_report': retained,
            'state': 'pilot_collected_unaccepted',
            'origin_admitted': False, 'accepted_panel': False,
        }
        if len(_json_bytes(result)) > LIMITS['artifact_bytes']:
            raise ValueError('pairing worker report exceeds bounded artefact')
        _save(root, 'worker_report', result)
        _check(root, reserved, started)
        return result
    except BaseException as exc:
        try:
            _save(root, 'worker_failure', {'stage': stage, 'at': _clock(),
                                           'exception_type': type(exc).__name__}, failure=True)
        except (OSError, ValueError):
            pass
        raise
