"""Bounded Gamma enumeration with original receipts, lossless pages and causal manifests.

No v1 startup, settings, SQL, scheduler or caller-supplied prospective payloads.
A fresh journal is mandatory; crashed attempts remain readable evidence, never resumed
under a new clock/build or silently promoted into a complete population frame.
"""

import asyncio
import json
import time
from dataclasses import asdict
from pathlib import Path

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import (
    Budget,
    CaptureJournal,
    _digest,
    _json_bytes,
    _strict_json,
    verify_capture,
)
from astrolabe.feature_store.source_parsers import gamma_identity
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist, _read
from astrolabe.feature_store.sources import SOURCES

from .build_identity import verified_panel_build

SOURCE = 'gamma.markets.keyset'
VERSION = 'fs2-gamma-frame-v1'
POLICY = {
    'population': 'all Gamma /markets/keyset rows returned under closed=false',
    'scope': 'no date, liquidity, category, active, display or top-N filter',
    'eligibility': 'active=true, closed=false and resolvable source-local outcome mapping',
    'outcome_rule': 'first source-ordered token; not the most favourable outcome',
    'terminal_rule': 'next_cursor omitted and row count strictly below requested limit',
    'duplicate_rule': 'retain every row; changed versions are inconsistent, never first/last wins',
    'rights': 'bounded internal public-interface measurement only; redistribution unadmitted',
    'clocks': 'local receipt/availability; native venue clocks and global atomicity unadmitted',
    'scientific_stage': 'measurement_development_only',
}


def parse_page(raw, limit):
    """Source envelope and row facts. Exact primitives remain in full raw/parsed journals."""
    payload = _strict_json(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get('markets'), list):
        raise ValueError('markets envelope required')
    markets = payload['markets']
    cursor = payload.get('next_cursor')
    if len(markets) > limit:
        raise ValueError('page exceeds requested limit')
    if 'next_cursor' in payload:
        if not isinstance(cursor, str) or not 1 <= len(cursor) <= 8192:
            raise ValueError('explicit null/empty cursor is not documented exhaustion')
        if len(markets) != limit:
            raise ValueError('continuing page count contradicts source protocol')
    elif len(markets) == limit:
        raise ValueError('full page missing cursor is not proven exhaustion')
    rows = []
    for index, row in enumerate(markets):
        identity, reasons = None, []
        market_id = row.get('id') if isinstance(row, dict) else None
        if not isinstance(market_id, str) or not market_id:
            market_id = None
            reasons.append('market_id_unavailable')
        try:
            identity = gamma_identity(row)
        except (ValueError, TypeError, KeyError):
            reasons.append('identity_unresolved')
        if not isinstance(row, dict) or type(row.get('closed')) is not bool:
            reasons.append('closed_state_unavailable')
        elif row['closed']:
            reasons.append('closed')
        if not isinstance(row, dict) or type(row.get('active')) is not bool:
            reasons.append('active_state_unavailable')
        elif not row['active']:
            reasons.append('inactive')
        rows.append({
            'source_index': index, 'market_id': market_id, 'row_hash': content_hash(row),
            'identity': identity, 'eligible': not reasons, 'exclusion_reasons': reasons,
            'selected_token_id': identity['outcomes'][0]['token_id'] if identity else None,
        })
    return {'rows': rows, 'next_cursor': cursor, 'terminal': 'next_cursor' not in payload}


def _page_facts(capture, limit):
    error = capture['parsed']['parse_error']
    result = None
    if error is None:
        try:
            result = parse_page(capture['raw'], limit)
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            error = 'source_schema_invalid'
    return {'result': result, 'error': error}


def _verify_policy(root):
    root = Path(root)
    if root.resolve() != root or not root.name.startswith('fs2_capture_'):
        raise ValueError('canonical fresh frame directory required')
    policy, ack = _pair(root, 'frame_policy')
    session_bytes = _read(root / 'session.json')
    session = json.loads(session_bytes)
    expected_kind = 'synthetic' if session['capture_kind'] == 'synthetic' else 'prospective'
    params = SOURCES[SOURCE].params(policy['params'])
    if (policy['schema_version'] != VERSION or policy['policy'] != POLICY
            or policy['build'] != verified_panel_build()
            or policy['source'] != asdict(SOURCES[SOURCE])
            or policy['session_hash'] != _digest(session_bytes)
            or policy['budget'] != asdict(Budget(**session['budget']))
            or session['capture_kind'] not in {'synthetic', 'live_diagnostic'}
            or policy['provenance_class'] != expected_kind
            or set(params) != {'limit', 'closed'}
            or not _ordered_clocks(session['started'], ack['durable_ack'])):
        raise ValueError('frame policy/build/source/clock differs')
    return root, policy, ack


def _inventory(root, policy, policy_ack):
    """Read all attempts, never omit torn/unindexed folders from the ordered manifest."""
    entries, captures = [], []
    folders = sorted(p for p in root.iterdir() if p.is_dir())
    if len(folders) > policy['budget']['requests']:
        raise ValueError('frame exceeds request budget')
    for folder in folders:
        try:
            capture = verify_capture(folder)
            page, ack = _pair(folder, 'frame_page')
        except (OSError, ValueError, KeyError, TypeError):
            # Raw evidence is retained; unavailable chronology cannot be inferred.
            entries.append({'capture_id': folder.name, 'state': 'unverified_attempt'})
            continue
        receipt = capture['receipt']
        expected = _page_facts(capture, policy['params']['limit'])
        if (receipt['source_id'] != SOURCE
                or receipt['source_version'] != SOURCES[SOURCE].version
                or receipt['source_contract'] != policy['source']
                or page['policy_hash'] != policy_ack['payload_hash']
                or page['receipt_hash'] != capture['raw_ack']['receipt_hash']
                or page['generic_parse_hash'] != capture['parsed_ack']['parsed_hash']
                or page['facts'] != json.loads(_json_bytes(expected))
                or not _ordered_clocks(policy_ack['durable_ack'], receipt['request_started'],
                                       capture['parsed_ack']['durable_ack'], ack['durable_ack'])):
            raise ValueError('frame page integrity/chronology mismatch')
        captures.append((capture, page, ack))
    captures.sort(key=lambda v: v[0]['receipt']['receipt_ordinal'])
    previous_id, previous_cursor, prior_clock = None, None, policy_ack['durable_ack']
    seen_cursors, total_bytes = set(), 0
    for ordinal, (capture, page, ack) in enumerate(captures, 1):
        receipt = capture['receipt']
        params = {**policy['params']}
        if previous_cursor is not None:
            params['after_cursor'] = previous_cursor
        total_bytes += receipt['raw_bytes']
        if (receipt['receipt_ordinal'] != ordinal
                or receipt['request'] != {'method': 'GET', 'url': SOURCES[SOURCE].endpoint,
                                          'params': params}
                or receipt['previous_capture_id'] != previous_id
                or (ordinal > 1 and previous_cursor is None)
                or not _ordered_clocks(prior_clock, receipt['request_started'])
                or receipt['raw_bytes'] > policy['budget']['bytes_per_response']
                or total_bytes > policy['budget']['total_bytes']):
            raise ValueError('frame cursor/scope/ordinal/budget mismatch')
        facts = page['facts']
        result = facts['result']
        cursor = result['next_cursor'] if result else None
        repeated = cursor is not None and cursor in seen_cursors
        if cursor is not None:
            seen_cursors.add(cursor)
        entry = {
            'capture_id': receipt['capture_id'], 'state': 'verified_attempt',
            'ordinal': ordinal, 'raw_hash': receipt['raw_hash'],
            'receipt_hash': capture['raw_ack']['receipt_hash'], 'page_hash': ack['payload_hash'],
            'raw_bytes': receipt['raw_bytes'], 'http_status': receipt['status'],
            'request_started': receipt['request_started'],
            'first_received': receipt['first_received'], 'available_at': ack['durable_ack'],
            'error': 'cursor_cycle' if repeated else facts['error'],
            'result': result,
        }
        entries.append(entry)
        previous_id, previous_cursor = receipt['capture_id'], cursor
        prior_clock = ack['durable_ack']
        stopped = repeated or facts['error'] or (result and result['terminal'])
        if stopped and ordinal < len(captures):
            raise ValueError('frame continued beyond stop/termination')
    return entries


def _summarize(policy, policy_ack, entries):
    good = [e for e in entries if e['state'] == 'verified_attempt']
    unknown = [e for e in entries if e['state'] == 'unverified_attempt']
    terminal = bool(good and good[-1]['result'] and good[-1]['result']['terminal'])
    errors = sorted({e['error'] for e in good if e['error']})
    rows = [r for e in good if e['result'] for r in e['result']['rows']]
    by_market, by_condition, by_token = {}, {}, {}
    exclusions = {}
    for row in rows:
        if row['market_id'] is not None:
            by_market.setdefault(row['market_id'], set()).add(row['row_hash'])
        for reason in row['exclusion_reasons']:
            exclusions[reason] = exclusions.get(reason, 0) + 1
        identity = row['identity']
        if identity:
            mapping = content_hash(identity['outcomes'])
            by_condition.setdefault(identity['condition_id'], set()).add(mapping)
            for outcome in identity['outcomes']:
                by_token.setdefault(outcome['token_id'], set()).add(
                    (identity['condition_id'], outcome['outcome_index'], outcome['outcome_label']))
    conflicts = sorted(k for k, values in by_market.items() if len(values) > 1)
    condition_conflicts = sorted(k for k, values in by_condition.items() if len(values) > 1)
    token_conflicts = sorted(k for k, values in by_token.items() if len(values) > 1)
    inconsistent = bool(conflicts or condition_conflicts or token_conflicts
                        or exclusions.get('market_id_unavailable') or exclusions.get('closed'))
    state = ('incomplete' if unknown or errors or not terminal else
             'exhausted_inconsistent' if inconsistent else 'exhausted_consistent')
    return {
        'schema_version': VERSION, 'policy_hash': policy_ack['payload_hash'],
        'provenance_class': policy['provenance_class'], 'state': state,
        'population_inference_eligible': False,
        'source_semantics': 'interval enumeration, not atomic snapshot or independent events',
        'enumeration_terminal_observed': terminal and not errors and not unknown,
        'page_manifest_hash': content_hash(entries), 'pages': entries,
        'verified_attempts': len(good), 'unverified_attempts': len(unknown),
        'raw_bytes': sum(e['raw_bytes'] for e in good), 'source_rows': len(rows),
        'unique_market_ids': len(by_market),
        'duplicate_market_rows': sum(r['market_id'] is not None for r in rows) - len(by_market),
        'conflicting_market_ids': conflicts, 'conflicting_condition_ids': condition_conflicts,
        'conflicting_token_ids': token_conflicts, 'exclusion_counts': exclusions,
        'eligible_row_count': sum(r['eligible'] for r in rows), 'errors': errors,
        'interval_start': good[0]['request_started'] if good else None,
        'interval_end': good[-1]['first_received'] if good else None,
        'availability_basis': 'page acknowledgements; full frame needs report acknowledgement',
        'scientific_stage': 'measurement_development_only',
    }


class GammaFrameRun:
    """Predeclare scope and budgets durably, then make a single bounded collection pass."""

    def __init__(self, root, *, limit=100, budget=Budget(requests=1), transport=None):
        params = SOURCES[SOURCE].params({'closed': 'false', 'limit': limit})
        build = verified_panel_build()
        self.journal = CaptureJournal(root, budget=budget, transport=transport)
        self._lock = asyncio.Lock()
        _persist(self.journal.root, 'frame_policy', {
            'schema_version': VERSION, 'policy': POLICY, 'params': params,
            'source': asdict(SOURCES[SOURCE]), 'build': build, 'budget': asdict(budget),
            'session_hash': _digest(_read(self.journal.root / 'session.json')),
            'provenance_class': 'synthetic' if transport is not None else 'prospective',
        })

    async def collect(self):
        async with self._lock:
            root, policy, ack = _verify_policy(self.journal.root)
            if (root / 'frame_report_ack.json').exists():
                return read_frame(root)
            if any(p.is_dir() for p in root.iterdir()) or (root / 'frame_report.json').exists():
                raise ValueError('interrupted run retained; never silently resume or overwrite')
            previous, cursor, seen_cursors = None, None, set()
            stop = 'request_budget'
            for _ in range(self.journal.budget.requests):
                if self.journal.bytes >= self.journal.budget.total_bytes:
                    stop = 'byte_budget'
                    break
                if time.monotonic() - self.journal.started >= self.journal.budget.total_seconds:
                    stop = 'time_budget'
                    break
                params = dict(policy['params'])
                if cursor is not None:
                    params['after_cursor'] = cursor
                capture = await self.journal.fetch(SOURCE, params, previous_capture_id=previous)
                verified_panel_build()
                facts = _page_facts(capture, params['limit'])
                _persist(Path(capture['folder']), 'frame_page', {
                    'policy_hash': ack['payload_hash'],
                    'receipt_hash': capture['raw_ack']['receipt_hash'],
                    'generic_parse_hash': capture['parsed_ack']['parsed_hash'], 'facts': facts,
                })
                result = facts['result']
                if facts['error']:
                    stop = 'page_error'
                    break
                if result['terminal']:
                    stop = 'terminal'
                    break
                cursor = result['next_cursor']
                if cursor in seen_cursors:
                    stop = 'cursor_cycle'
                    break
                seen_cursors.add(cursor)
                previous = capture['receipt']['capture_id']
            verified_panel_build()
            summary = _summarize(policy, ack, _inventory(root, policy, ack))
            _persist(root, 'frame_report', {**summary, 'stop_reason': stop})
            return read_frame(root)


def read_frame(root):
    """Read-only recovery. A torn run stays incomplete; this never reparses into new evidence."""
    root, policy, ack = _verify_policy(root)
    entries = _inventory(root, policy, ack)
    summary = _summarize(policy, ack, entries)
    if not (root / 'frame_report_ack.json').exists():
        return {**summary, 'state': 'incomplete', 'stop_reason': 'interrupted',
                'frame_available_at': None, 'frame_report_hash': None}
    report, report_ack = _pair(root, 'frame_report')
    if {k: v for k, v in report.items() if k != 'stop_reason'} != summary:
        raise ValueError('frame manifest differs from retained evidence')
    clocks = [ack['durable_ack']]
    clocks.extend(e['available_at'] for e in entries if e['state'] == 'verified_attempt')
    if not _ordered_clocks(*clocks, report_ack['durable_ack']):
        raise ValueError('frame report chronology differs')
    return {**report, 'frame_available_at': report_ack['durable_ack'],
            'frame_report_hash': report_ack['payload_hash']}
