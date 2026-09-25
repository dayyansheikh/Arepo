"""Interleaved synthetic origins and due targets with an immutable dispatch journal."""

import asyncio
import hashlib
import heapq
import shutil
from datetime import timedelta

import httpx

from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist

from . import due_worker, origin_worker
from .activation import activate_panel, allocation, read_activation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .panel_declaration import PanelProtocol, read_panel_declaration
from .quote_inputs import _at

VERSION = 'fs2-interleaved-synthetic-runtime-v1'
POLICY = {'live_collection_enabled': False, 'top_bytes': 32 * 1048576,
          'artifact_bytes': 16 * 1048576, 'plan_bytes_per_origin': 131072,
          'failure_reserve_bytes': 65536, 'free_reserve_bytes': 2 * 1024**3,
          'queue_order': 'scheduled UTC; target before origin; immutable id',
          'request_concurrency': 1, 'origin_admitted': False, 'accepted_panel': False}
CHILDREN = {'origins', 'targets', 'plans'}


def run_root(panel):
    return origin_worker.run_root(panel).with_name(
        'fs2_runtime_' + _canonical(panel).name.removeprefix('fs2_panel_'))


def _size(root):
    total = 0
    files = 0
    for p in root.iterdir():
        if p.is_symlink() or (p.is_dir() and p.name not in CHILDREN):
            raise ValueError('runtime path closure differs')
        if p.is_file():
            size = p.stat().st_size
            if size > POLICY['artifact_bytes']:
                raise ValueError('runtime artefact limit')
            total += size
            files += 1
        elif not p.is_dir():
            raise ValueError('runtime file type differs')
    if files > 6 or total > POLICY['top_bytes']:
        raise ValueError('runtime metadata quota')
    return total


def _save(root, name, payload, failure=False):
    size = len(_json_bytes(payload)) + 4096
    reserve = 0 if failure else POLICY['failure_reserve_bytes']
    if (size > POLICY['artifact_bytes']
            or _size(root) + size > POLICY['top_bytes'] - reserve):
        raise ValueError('runtime metadata reservation exceeded')
    if shutil.disk_usage(root).free < POLICY['free_reserve_bytes'] + size:
        raise ValueError('runtime free reserve reached')
    _persist(root, name, payload)


def _reserved(declaration):
    return (allocation(declaration)['required_free_bytes'] + POLICY['top_bytes']
            + declaration['reservation']['origin_slots'] * POLICY['plan_bytes_per_origin'])


def _queue(activation):
    return [(_at(s['scheduled_at']), 1, s['intent_id'], 'origin', s)
            for s in activation['slots']]


def _enqueue(queue, jobs, plan_ack, eligible):
    for job in jobs:
        at = (_at(job['scheduled_at']) if eligible
              else _time(plan_ack['durable_ack']))
        heapq.heappush(queue, (at, 0, job['attempt_id'], 'target', job))


def _origin(root, result):
    intent, _ = _pair(root, 'origin_intent')
    receipt, receipt_ack = _pair(root, 'origin_receipt')
    record = next(r for r in receipt['inventory'] if r['path'] == 'origin_intent.json')
    if (receipt_ack['payload_hash'] != result['receipt_hash']
            or hashlib.sha256(_json_bytes(intent)).hexdigest() != record['sha256']):
        raise ValueError('runtime origin intent changed during consumption')
    facts = None
    if result['origin_hash'] is not None:
        facts, ack = _pair(root, 'origin_facts')
        if ack['payload_hash'] != result['origin_hash']:
            raise ValueError('runtime origin facts changed during consumption')
    return {'result': result, 'member': intent['member'], 'facts': facts,
            'origin_persisted_at': receipt_ack['durable_ack']}


def _plan(root, result, protocol):
    started = _clock()
    origin = _origin(root / 'origins' / result['intent_id'], result)
    jobs = due_worker._schedule([origin], protocol)
    path = root / 'plans' / result['intent_id']
    path.mkdir(mode=0o700)
    _sync_directory(path.parent)
    due_worker._save(path, 'plan', {'origin': origin, 'jobs': jobs,
        'read_started_at': started, 'read_at': _clock()}, attempt=True)
    _, ack = _pair(path, 'plan')
    return origin, jobs, ack


def _read_plan(root, result, protocol):
    origin = _origin(root / 'origins' / result['intent_id'], result)
    path = root / 'plans' / result['intent_id']
    if (set(p.name for p in path.iterdir()) != {'plan.json', 'plan_ack.json'}
            or due_worker._size(path, True) > POLICY['plan_bytes_per_origin']):
        raise ValueError('runtime per-origin plan closure differs')
    plan, ack = _pair(path, 'plan')
    jobs = due_worker._schedule([origin], protocol)
    if (_json_bytes(plan['origin']) != _json_bytes(origin) or plan['jobs'] != jobs
            or not _ordered_clocks(origin['origin_persisted_at'], plan['read_started_at'],
                                   plan['read_at'], ack['durable_ack'])):
        raise ValueError('runtime target plan binding/chronology differs')
    return origin, jobs, ack


async def exercise_panel(panel_root, *, transport):
    if type(transport) is not httpx.MockTransport:
        raise ValueError('synthetic MockTransport required; live runtime remains closed')
    panel, root = _canonical(panel_root), run_root(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, 'panel_policy')
    protocol = PanelProtocol(**panel_policy['protocol'])
    if root.exists():
        raise FileExistsError('runtime retained; no resume or reschedule')
    if shutil.disk_usage(root.parent).free < _reserved(declaration):
        raise ValueError('insufficient complete runtime reservation')
    build = verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        for child in sorted(CHILDREN):
            (root / child).mkdir(mode=0o700)
        _sync_directory(root)
        _save(root, 'runtime_policy', {'schema_version': VERSION, 'policy': POLICY,
            'build': build, 'panel_root': str(panel),
            'declaration_hash': declaration['declaration_hash'],
            'required_free_bytes': _reserved(declaration), 'declared_at': _clock()})
        activation = activate_panel(panel)
        members = {m['market_id']: m for m in activation['selected']}
        queue = _queue(activation)
        heapq.heapify(queue)
        origins, attempts, events = {}, [], []
        while queue:
            due, _, identity, kind, job = heapq.heappop(queue)
            remaining = (due - _time(_clock())).total_seconds()
            if remaining > 0:
                await asyncio.sleep(remaining)
            dispatched = _clock()
            if kind == 'origin':
                result = await origin_worker._collect_one(root / 'origins' / identity,
                    job, members[job['market_id']], panel_policy, activation, transport)
                origin, jobs, ack = _plan(root, result, protocol)
                origins[identity] = origin
                _enqueue(queue, jobs, ack, origin['result']['state'] == 'observed')
            else:
                attempts.append(await due_worker._collect_one(root / 'targets' / identity,
                    job, origins[job['origin_id']], panel_policy, transport))
            events.append({'kind': kind, 'id': identity, 'dispatched_at': dispatched,
                           'completed_at': _clock()})
        deadlines = [_time(o['facts']['origin_at']) + timedelta(
            seconds=protocol.horizon_seconds + protocol.tolerance_seconds)
            for o in origins.values() if o['result']['state'] == 'observed']
        remaining = (max(deadlines) - _time(_clock())).total_seconds() if deadlines else 0
        if remaining > 0:
            await asyncio.sleep(remaining)
        cutoff = _clock()
        outcomes = due_worker._outcomes(list(origins.values()), attempts, protocol, cutoff)
        if verified_panel_build() != build:
            raise ValueError('runtime build changed')
        _save(root, 'runtime_report', {'schema_version': VERSION,
            'activation_hash': activation['activation_hash'], 'events': events,
            'origins': [o['result'] for o in origins.values()],
            'attempts': [{k: v for k, v in a.items() if k != 'projection'} for a in attempts],
            'outcomes': outcomes, 'as_of': cutoff, 'finished_at': _clock(),
            'provenance_class': 'synthetic', 'accepted_panel': False,
            'feature_store_admitted': False})
        return read_runtime(panel)
    except BaseException as exc:
        try:
            _save(root, 'runtime_failure', {'exception_type': type(exc).__name__, 'at': _clock()},
                  failure=True)
        except (ValueError, OSError):
            pass
        raise


def read_runtime(panel_root):
    panel, root = _canonical(panel_root), run_root(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, 'panel_policy')
    protocol = PanelProtocol(**panel_policy['protocol'])
    policy, policy_ack = _pair(root, 'runtime_policy')
    report, report_ack = _pair(root, 'runtime_report')
    activation = read_activation(panel)
    if (set(p.name for p in root.iterdir()) != CHILDREN | {
            'runtime_policy.json', 'runtime_policy_ack.json',
            'runtime_report.json', 'runtime_report_ack.json'}
            or _size(root) > POLICY['top_bytes'] or policy['schema_version'] != VERSION
            or policy['policy'] != POLICY or policy['build'] != verified_panel_build()
            or policy['panel_root'] != str(panel)
            or policy['declaration_hash'] != declaration['declaration_hash']
            or policy['required_free_bytes'] != _reserved(declaration)
            or report['schema_version'] != VERSION
            or report['activation_hash'] != activation['activation_hash']
            or not _ordered_clocks(policy['declared_at'], policy_ack['durable_ack'],
                activation['activation_available_at'], report['as_of'], report['finished_at'],
                report_ack['durable_ack'])):
        raise ValueError('runtime policy/activation/chronology differs')
    members = {m['market_id']: m for m in activation['selected']}
    queue = _queue(activation)
    heapq.heapify(queue)
    origins, attempts = {}, []
    previous = activation['activation_available_at']
    for event in report['events']:
        if not queue:
            raise ValueError('extra runtime dispatch')
        due, _, identity, kind, job = heapq.heappop(queue)
        if (event['kind'] != kind or event['id'] != identity
                or _time(event['dispatched_at']) < due
                or not _ordered_clocks(previous, event['dispatched_at'], event['completed_at'])):
            raise ValueError('runtime dispatch order/time differs')
        if kind == 'origin':
            child = root / 'origins' / identity
            result = origin_worker._read_one(child, job, members[job['market_id']],
                                             panel_policy, activation)
            intent, _ = _pair(child, 'origin_intent')
            origin, jobs, ack = _read_plan(root, result, protocol)
            origins[identity] = origin
            _enqueue(queue, jobs, ack, origin['result']['state'] == 'observed')
            last = ack['durable_ack']
        else:
            child = root / 'targets' / identity
            attempt = due_worker._read_one(child, job, origins[job['origin_id']], panel_policy)
            intent, _ = _pair(child, 'target_intent')
            _, ack = _pair(root / 'plans' / job['origin_id'], 'plan')
            if not _ordered_clocks(ack['durable_ack'], intent['created_at']):
                raise ValueError('runtime target request precedes durable plan')
            attempts.append(attempt)
            last = attempt['available_at']
        if not _ordered_clocks(event['dispatched_at'], intent['created_at'],
                               last, event['completed_at']):
            raise ValueError('runtime dispatch consumption chronology differs')
        previous = event['completed_at']
    if (queue or set(p.name for p in (root / 'origins').iterdir()) != set(origins)
            or set(p.name for p in (root / 'plans').iterdir()) != set(origins)
            or set(p.name for p in (root / 'targets').iterdir())
                != {a['attempt_id'] for a in attempts}
            or not _ordered_clocks(previous, report['as_of'])
            or report['origins'] != [o['result'] for o in origins.values()]
            or report['attempts'] != [{k: v for k, v in a.items() if k != 'projection'}
                                      for a in attempts]
            or _json_bytes(report['outcomes']) != _json_bytes(due_worker._outcomes(
                list(origins.values()), attempts, protocol, report['as_of']))
            or report['provenance_class'] != 'synthetic'
            or report['accepted_panel'] is not False
            or report['feature_store_admitted'] is not False):
        raise ValueError('runtime complete evidence/outcome replay differs')
    return {**report, 'runtime_report_hash': report_ack['payload_hash'],
            'runtime_available_at': report_ack['durable_ack']}
