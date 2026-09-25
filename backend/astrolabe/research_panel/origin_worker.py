"""Synthetic origin-worker integration with actual clocks; live collection stays closed."""

import asyncio
import hashlib
import re
import shutil
import time
from dataclasses import asdict
from datetime import timedelta

import httpx

from astrolabe.feature_store.capture import Budget, _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_quota import quota_policy
from astrolabe.feature_store.source_run import (
    TARGETED_POLICY,
    SourceRun,
    _ordered_clocks,
    _pair,
    _persist,
)
from astrolabe.feature_store.sources import SOURCES

from .activation import activate_panel, activation_root, allocation, read_activation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .panel_declaration import PanelProtocol, read_panel_declaration
from .quote_computation import (
    CHILD,
    computation_limits,
    read_quote_computation,
    record_quote_computation,
)
from .quote_inputs import QuoteInputPolicy, _at

VERSION = 'fs2-synthetic-origin-worker-v1'
SOURCE = 'fs2_capture_origin'
COMPUTATION = 'fs2_quote_computation_origin'
POLICY = {'live_collection_enabled': False, 'targets_collected': False,
          'top_manifest_bytes': 1048576, 'origin_metadata_bytes': 131072,
          'failure_reserve_bytes': 65536, 'free_reserve_bytes': 2 * 1024**3,
          'max_files_per_origin': 160, 'max_snapshot_seconds': 60,
          'trade_page_limit': 10, 'origin_admitted': False, 'accepted_panel': False}


def run_root(panel):
    return activation_root(panel).with_name(
        'fs2_origin_run_' + _canonical(panel).name.removeprefix('fs2_panel_'))


def _metadata_size(root, *, origin):
    files = []
    for path in root.iterdir():
        if path.is_symlink():
            raise ValueError('origin-worker symlink refused')
        if path.is_dir():
            if (path.name not in {SOURCE, COMPUTATION} if origin
                    else re.fullmatch('[0-9a-f]{64}', path.name) is None):
                raise ValueError('unexpected origin-worker child')
        elif not path.is_file():
            raise ValueError('unexpected origin-worker file type')
        else:
            files.append(path)
    if len(files) > 8:
        raise ValueError('origin-worker metadata file limit')
    return sum(p.stat().st_size for p in files)


def _save(root, name, payload, *, origin=False, failure=False):
    size = len(_json_bytes(payload)) + 4096
    limit = POLICY['origin_metadata_bytes' if origin else 'top_manifest_bytes']
    allowance = limit if failure else limit - POLICY['failure_reserve_bytes']
    if _metadata_size(root, origin=origin) + size > allowance:
        raise ValueError('origin-worker metadata quota exceeded')
    if shutil.disk_usage(root).free < POLICY['free_reserve_bytes'] + size:
        raise ValueError('origin-worker free-space reserve reached')
    _persist(root, name, payload)


def _snapshot(root, ceiling):
    """Bind partial raw bytes as preserved evidence, never as successful parsed observations."""
    started, total, records = time.monotonic(), 0, []
    pending = [root]
    while pending:
        folder = pending.pop()
        for path in sorted(folder.iterdir()):
            relative = path.relative_to(root)
            if path.name in {'origin_receipt.json', 'origin_receipt_ack.json'} and folder == root:
                continue
            # SourceRun permits three components below its own root; the source
            # directory adds one component beneath this origin's root.
            if path.is_symlink() or len(relative.parts) > 4:
                raise ValueError('origin evidence path/depth differs')
            if path.is_dir():
                pending.append(path)
                if len(pending) > 32:
                    raise ValueError('origin evidence directory limit')
                continue
            if not path.is_file() or len(records) >= POLICY['max_files_per_origin']:
                raise ValueError('origin evidence file limit')
            size = path.stat().st_size
            total += size
            if total > ceiling:
                raise ValueError('origin evidence exceeds full reserved cost')
            digest = hashlib.sha256()
            with path.open('rb') as handle:
                while chunk := handle.read(65536):
                    if time.monotonic() - started > POLICY['max_snapshot_seconds']:
                        raise ValueError('origin evidence snapshot deadline')
                    digest.update(chunk)
            if path.stat().st_size != size:
                raise ValueError('origin evidence changed during snapshot')
            records.append({'path': str(relative), 'bytes': size, 'sha256': digest.hexdigest()})
    return sorted(records, key=lambda r: r['path'])


def _requests(member):
    return [('gamma.market', {'market_id': member['market_id']}),
            ('clob.book', {'token_id': member['token_id']}),
            ('data.v2.trades', {'condition': member['condition_id'],
                              'limit': POLICY['trade_page_limit'], 'taker_only': 'true'})]


def _budget(protocol, slot, at):
    remaining = int((_at(slot['latest_origin_at']) - _time(at)).total_seconds())
    if remaining < 1:
        return None
    return Budget(requests=3, bytes_per_response=protocol.source_response_bytes,
                  total_bytes=3 * protocol.source_response_bytes,
                  seconds_per_request=min(15, remaining), total_seconds=min(180, remaining))


def _projection(root, intent, panel_policy, freeze):
    """Consume verified journal facts directly; replay uses the original actual freeze."""
    protocol = PanelProtocol(**panel_policy['protocol'])
    member = intent['member']
    summary = read_quote_computation(root / COMPUTATION)
    policy, _ = _pair(root / COMPUTATION, 'quote_policy')
    facts, _ = _pair(root / COMPUTATION, 'quote_facts')
    inputs, _ = _pair(root / COMPUTATION / CHILD, 'read_facts')
    source, source_ack = _pair(root / SOURCE, 'run')
    _, intent_ack = _pair(root, 'origin_intent')
    rows = sorted((row for kind, row in inputs['source_projection']['rows']
                   if kind == 'source_observation'), key=lambda row: row['receipt_ordinal'])
    expected_requests = _requests(member)
    if (len(rows) != 3 or source['policy'] != TARGETED_POLICY
            or source['budget'] != intent['source_budget']
            or source['retention_quota'] != quota_policy(protocol.source_run_retained_bytes)
            or source['provenance_class'] != 'synthetic'
            or policy['source_root'] != str(root / SOURCE)
            or policy['limits'].get('storage_profile')
                != panel_policy.get('computation_storage_profile')
            or policy['quote_policy'] != asdict(QuoteInputPolicy(
                protocol.max_quote_age_seconds, protocol.max_identity_age_seconds))
            or not _ordered_clocks(intent_ack['durable_ack'], source_ack['durable_ack'],
                                   summary['computation_available_at'], freeze)):
        raise ValueError('origin source/computation policy or chronology differs')
    for row, (source_id, params) in zip(rows, expected_requests, strict=True):
        if (row['source_id'] != source_id
                or row['request_metadata']['request'] != SOURCES[source_id].request(params)):
            raise ValueError('origin request differs from frozen assignment')
    quotes = facts['projection']['quotes']
    if len(quotes) != 1:
        raise ValueError('one fixed origin book observation required')
    quote = quotes[0]
    return {'computation': summary, 'quote': quote,
            'state_at_freeze': _choice(quote, member, protocol, intent['slot'], freeze),
            'source_statuses': [{'source_id': r['source_id'], 'state': r['missing_reason'],
                                 'observation_id': r['id']} for r in rows],
            'provenance_class': 'synthetic', 'clock_basis': 'receipt',
            'flow_window_complete': False, 'economic_value_claim': False}


def _choice(quote, member, protocol, slot, freeze):
    state = quote['state']
    mapping = quote['mapping']
    if state == 'observed':
        if (quote['token_id'] != member['token_id']
                or quote['condition_id'] != member['condition_id']
                or mapping['market_id'] != member['market_id']
                or mapping['mapping_version'] != member['mapping_version']
                or mapping['outcome_index'] != member['outcome_index']
                or mapping['outcome_label'] != member['outcome_label']):
            state = 'identity_changed_since_selection'
        elif _time(freeze) - _at(quote['received_at']) > timedelta(
            seconds=protocol.max_quote_age_seconds
        ):
            state = 'receipt_stale_at_origin'
        elif _time(freeze) - _at(mapping['received_at']) > timedelta(
            seconds=protocol.max_identity_age_seconds
        ):
            state = 'identity_stale_at_origin'
    if _time(freeze) > _at(slot['latest_origin_at']):
        state = 'late_origin'
    return state


def _state(facts, ack, protocol):
    freeze, saved = _time(facts['origin_at']), _time(ack['durable_ack'])
    if not _ordered_clocks(facts['origin_at'], ack['durable_ack']):
        raise ValueError('origin save clock regressed')
    if (saved - freeze > timedelta(seconds=protocol.max_origin_save_seconds)
            or saved >= freeze + timedelta(seconds=protocol.horizon_seconds)):
        return 'late_persistence'
    return facts['projection']['state_at_freeze']


async def _collect_one(root, slot, member, panel_policy, activation, transport):
    protocol = PanelProtocol(**panel_policy['protocol'])
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        at = _clock()
        budget = _budget(protocol, slot, at)
        _save(root, 'origin_intent', {
            'schema_version': VERSION, 'slot': slot, 'member': member,
            'activation_hash': activation['activation_hash'], 'budget_basis_at': at,
            'source_budget': asdict(budget) if budget else None,
            'created_at': at,
        }, origin=True)
        intent, intent_ack = _pair(root, 'origin_intent')
        if budget is None:
            _save(root, 'origin_failure', {'state': 'expired_before_request', 'at': _clock()},
                  origin=True, failure=True)
        else:
            source = SourceRun(root / SOURCE, budget=budget, transport=transport,
                               policy_version=TARGETED_POLICY['version'],
                               retained_bytes=protocol.source_run_retained_bytes)
            for source_id, params in _requests(member):
                if _budget(protocol, slot, _clock()) is None:
                    raise TimeoutError('origin slot expired before next request')
                await source.fetch(source_id, params)
            record_quote_computation(root / SOURCE, output_root=root / COMPUTATION,
                policy=QuoteInputPolicy(protocol.max_quote_age_seconds,
                                        protocol.max_identity_age_seconds),
                storage_profile=panel_policy.get('computation_storage_profile'))
            # Actual source/computation consumption finishes before the actual freeze.
            # Recheck ages at freeze without fetching any new values afterward.
            read_started = _clock()
            projection = _projection(root, intent, panel_policy, read_started)
            freeze = _clock()
            projection['state_at_freeze'] = _choice(
                projection['quote'], member, protocol, slot, freeze)
            _save(root, 'origin_facts', {
                'schema_version': VERSION, 'intent_hash': intent_ack['payload_hash'],
                'read_started_at': read_started, 'origin_at': freeze,
                'projection': projection, 'origin_admitted': False,
                'feature_store_admitted': False, 'accepted_panel': False,
            }, origin=True)
    except (ValueError, OSError, TimeoutError) as exc:
        _save(root, 'origin_failure', {'state': 'expired_during_requests'
                                      if isinstance(exc, TimeoutError) else 'failed',
                                      'exception_type': type(exc).__name__,
                                      'at': _clock()}, origin=True, failure=True)
    ceiling = (protocol.source_run_retained_bytes + POLICY['origin_metadata_bytes']
               + computation_limits(panel_policy.get('computation_storage_profile'))[
                   'max_output_bytes'])
    _save(root, 'origin_receipt', {'inventory': _snapshot(root, ceiling),
                                  'completed_at': _clock()}, origin=True, failure=True)
    return _read_one(root, slot, member, panel_policy, activation)


def _read_one(root, slot, member, panel_policy, activation):
    protocol = PanelProtocol(**panel_policy['protocol'])
    receipt, receipt_ack = _pair(root, 'origin_receipt')
    ceiling = (protocol.source_run_retained_bytes + POLICY['origin_metadata_bytes']
               + computation_limits(panel_policy.get('computation_storage_profile'))[
                   'max_output_bytes'])
    if receipt['inventory'] != _snapshot(root, ceiling):
        raise ValueError('origin raw/partial evidence inventory differs')
    if _metadata_size(root, origin=True) > POLICY['origin_metadata_bytes']:
        raise ValueError('origin metadata quota differs')
    if not _ordered_clocks(receipt['completed_at'], receipt_ack['durable_ack']):
        raise ValueError('origin receipt chronology differs')
    intent, intent_ack = _pair(root, 'origin_intent')
    budget = _budget(protocol, slot, intent['budget_basis_at'])
    if (intent['schema_version'] != VERSION or intent['slot'] != slot or intent['member'] != member
            or intent['activation_hash'] != activation['activation_hash']
            or intent['source_budget'] != (asdict(budget) if budget else None)
            or not _ordered_clocks(activation['activation_available_at'], intent['created_at'],
                                   intent_ack['durable_ack'], receipt['completed_at'])
            or _time(intent['created_at']) < _at(slot['scheduled_at'])):
        raise ValueError('origin intent identity/budget/chronology differs')
    if (root / 'origin_failure.json').exists():
        failure, ack = _pair(root, 'origin_failure')
        if (failure['state'] not in {'failed', 'expired_before_request', 'expired_during_requests'}
                or not _ordered_clocks(intent_ack['durable_ack'], failure['at'],
                                       ack['durable_ack'], receipt['completed_at'])
                or failure['state'] == 'expired_before_request' and budget is not None):
            raise ValueError('origin failure chronology/state differs')
        state, origin_hash = failure['state'], None
    else:
        facts, ack = _pair(root, 'origin_facts')
        projection = _projection(root, intent, panel_policy, facts['origin_at'])
        if (facts['schema_version'] != VERSION or facts['intent_hash'] != intent_ack['payload_hash']
                or _json_bytes(facts['projection']) != _json_bytes(projection)
                or any(facts[k] is not False for k in
                       ('origin_admitted', 'feature_store_admitted', 'accepted_panel'))
                or not _ordered_clocks(intent_ack['durable_ack'], facts['read_started_at'],
                                       facts['origin_at'], ack['durable_ack'],
                                       receipt['completed_at'])
                or not _ordered_clocks(projection['computation']['computation_available_at'],
                                       facts['read_started_at'])):
            raise ValueError('origin facts/causality differs')
        state, origin_hash = _state(facts, ack, protocol), ack['payload_hash']
        if _time(receipt_ack['durable_ack']) >= (
            _time(facts['origin_at']) + timedelta(seconds=protocol.horizon_seconds)
        ):
            state = 'late_persistence'
    return {'intent_id': slot['intent_id'], 'state': state, 'origin_hash': origin_hash,
            'receipt_hash': receipt_ack['payload_hash'], 'provenance_class': 'synthetic',
            'origin_admitted': False, 'targets_collected': False}


async def exercise_origins(panel_root, *, transport):
    """No live transport, payload/clock overrides, new seeds, rescheduling or resume."""
    if type(transport) is not httpx.MockTransport:
        raise ValueError('synthetic MockTransport required until target integration is complete')
    panel = _canonical(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, 'panel_policy')
    root = run_root(panel)
    if root.exists():
        raise FileExistsError('origin run retained; never resume or reschedule')
    reserved = allocation(declaration)['required_free_bytes'] + POLICY['top_manifest_bytes']
    if shutil.disk_usage(root.parent).free < reserved:
        raise ValueError('insufficient complete origin-worker reservation')
    build = verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'worker_policy', {
            'schema_version': VERSION, 'policy': POLICY, 'build': build, 'panel_root': str(panel),
            'panel_declaration_hash': declaration['declaration_hash'],
            'required_free_bytes': reserved, 'declared_at': _clock(),
        })
        activated = activate_panel(panel)
        members = {m['market_id']: m for m in activated['selected']}
        results = []
        for slot in activated['slots']:
            remaining = (_at(slot['scheduled_at']) - _time(_clock())).total_seconds()
            if remaining > 0:
                await asyncio.sleep(remaining)
            results.append(await _collect_one(root / slot['intent_id'], slot,
                members[slot['market_id']], panel_policy, activated, transport))
        if verified_panel_build() != build:
            raise ValueError('origin worker build changed')
        _save(root, 'worker_report', {'schema_version': VERSION,
            'activation_hash': activated['activation_hash'], 'results': results,
            'finished_at': _clock(), 'provenance_class': 'synthetic',
            'origin_admitted': False, 'accepted_panel': False, 'targets_collected': False})
        return read_origin_run(panel)
    except BaseException as exc:
        try:
            _save(root, 'worker_failure', {'exception_type': type(exc).__name__, 'at': _clock()},
                  failure=True)
        except (OSError, ValueError):
            pass
        raise


def read_origin_run(panel_root):
    panel, root = _canonical(panel_root), run_root(panel_root)
    activated = read_activation(panel)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, 'panel_policy')
    policy, policy_ack = _pair(root, 'worker_policy')
    report, report_ack = _pair(root, 'worker_report')
    expected = {'worker_policy.json', 'worker_policy_ack.json',
                'worker_report.json', 'worker_report_ack.json',
                *[s['intent_id'] for s in activated['slots']]}
    if set(p.name for p in root.iterdir()) != expected:
        raise ValueError('complete origin-worker slot closure required')
    if (_metadata_size(root, origin=False) > POLICY['top_manifest_bytes']
            or policy['schema_version'] != VERSION or policy['policy'] != POLICY
            or policy['build'] != verified_panel_build() or policy['panel_root'] != str(panel)
            or policy['panel_declaration_hash'] != declaration['declaration_hash']
            or policy['required_free_bytes'] != allocation(declaration)['required_free_bytes']
                + POLICY['top_manifest_bytes']
            or report['schema_version'] != VERSION
            or report['activation_hash'] != activated['activation_hash']
            or report['provenance_class'] != 'synthetic'
            or any(report[k] is not False for k in
                   ('origin_admitted', 'accepted_panel', 'targets_collected'))
            or not _ordered_clocks(policy['declared_at'], policy_ack['durable_ack'],
                                   activated['activation_available_at'], report['finished_at'],
                                   report_ack['durable_ack'])):
        raise ValueError('origin-worker policy/activation/chronology differs')
    members = {m['market_id']: m for m in activated['selected']}
    results = [_read_one(root / slot['intent_id'], slot, members[slot['market_id']],
                         panel_policy, activated) for slot in activated['slots']]
    if results != report['results']:
        raise ValueError('origin-worker result replay differs')
    return {**report, 'worker_report_hash': report_ack['payload_hash'],
            'worker_available_at': report_ack['durable_ack']}
