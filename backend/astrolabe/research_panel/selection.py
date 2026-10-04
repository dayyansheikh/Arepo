"""Durable scheduled-arm development selection from an original verified frame.

No SQL, settings, network, injected seed/clock/payload or prospective-origin admission.
Historical source facts stay historical; every new read and computation has its own clock.
"""

import json
import re
import secrets
import shutil
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import (
    _clock,
    _digest,
    _json_bytes,
    _strict_json,
    _sync_directory,
    verify_capture,
)
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist, _read

from .build_identity import verified_panel_build
from .metadata import project_metadata
from .original_reader import read_original_frame
from .sampling import FrameMember, SamplingProtocol, plan_sample

VERSION = 'fs2-development-selection-v1'
POLICY = {
    'use': 'development_selection_only', 'arms': 'scheduled_only; triggers/controls unavailable',
    'close_bins_seconds': [0, 86400, 604800, 2592000],
    'strata_reference': 'policy declaration UTC time; unknown metadata stays unknown',
    'deduplication': 'identical market versions only; retain every source row',
    'lineage': 'row-qualified evidence hash; not an inserted SQL source_observation',
    'origin_admitted': False, 'population_inference_eligible': False,
}
READ_FOLDER = 'fs2_frame_read_original'


@dataclass(frozen=True)
class SelectionBudget:
    pages: int = 4000
    rows: int = 400000
    raw_bytes: int = 3221225472
    output_bytes: int = 1073741824
    seconds: int = 600
    free_reserve_bytes: int = 2147483648

    def __post_init__(self):
        for value, maximum in zip(asdict(self).values(),
                                  (4000, 400000, 3221225472, 1073741824, 600, 2147483648),
                                  strict=True):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError('selection budget outside finite limits')


class _Budget:
    def __init__(self, root, budget):
        self.root, self.budget = root, budget
        self.started, self.written = time.monotonic(), 0

    def check(self, extra=0):
        if time.monotonic() - self.started > self.budget.seconds:
            raise ValueError('selection time budget exhausted')
        # Reserve enough space to retain a failure acknowledgement after a budget stop.
        if self.written + extra + 65536 > self.budget.output_bytes:
            raise ValueError('selection output budget exhausted')
        if shutil.disk_usage(self.root).free < self.budget.free_reserve_bytes + extra + 65536:
            raise ValueError('selection free-space reserve reached')

    def persist(self, folder, name, payload):
        size = len(_json_bytes(payload))
        if size > 16 * 1048576:
            raise ValueError('selection artefact exceeds readable limit')
        self.check(size + 4096)
        _persist(folder, name, payload)
        self.written += sum((folder / (name + suffix)).stat().st_size
                            for suffix in ('.json', '_ack.json'))


def _canonical(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('canonical absolute selection paths required')
    return path


def _protocol(policy):
    args = dict(policy['sampling_protocol'])
    args['probability_edges'] = tuple(args['probability_edges'])
    args['liquidity_edges'] = tuple(args['liquidity_edges'])
    return SamplingProtocol(**args)


def _complete(report, budget):
    if (report['state'] != 'exhausted_consistent' or not report['enumeration_terminal_observed']
            or report['unverified_attempts'] or report.get('unrecovered_errors')
            or report['conflicting_market_ids'] or report['conflicting_condition_ids']
            or report['conflicting_token_ids'] or not report['eligible_row_count']
            or report['provenance_class'] not in {'prospective', 'synthetic'}):
        raise ValueError('complete consistent nonempty original frame required')
    if (len(report['pages']) > budget.pages or report['source_rows'] > budget.rows
            or report['raw_bytes'] > budget.raw_bytes):
        raise ValueError('original frame exceeds selection budget')


def _projection(frame_root, entry, seen, report_hash):
    capture_id = entry['capture_id']
    if str(uuid.UUID(capture_id)) != capture_id:
        raise ValueError('canonical capture identity required')
    folder = frame_root / capture_id
    capture = verify_capture(folder)
    page, ack = _pair(folder, 'frame_page')
    if (entry['raw_hash'] != capture['receipt']['raw_hash']
            or entry['receipt_hash'] != capture['raw_ack']['receipt_hash']
            or entry['page_hash'] != ack['payload_hash']
            or entry['available_at'] != ack['durable_ack']
            or entry['raw_bytes'] != capture['receipt']['raw_bytes']):
        raise ValueError('original page changed during selection read')
    result = page['facts']['result']
    if result is None:
        if entry['result'] is not None or not entry['error']:
            raise ValueError('original failed-page lineage differs')
        return []
    if {**{k: v for k, v in result.items() if k != 'rows'},
        'row_count': len(result['rows'])} != entry['result']:
        raise ValueError('original page count/terminal differs')
    raw_rows = _strict_json(capture['raw'])['markets']
    if len(raw_rows) != len(result['rows']):
        raise ValueError('original source-row count differs')
    rows = []
    for index, (raw, fact) in enumerate(zip(raw_rows, result['rows'], strict=True)):
        if fact['source_index'] != index or fact['row_hash'] != content_hash(raw):
            raise ValueError('original source-row hash/index differs')
        evidence = content_hash({'frame_report_hash': report_hash,
                                 'page_hash': entry['page_hash'], 'source_index': index,
                                 'row_hash': fact['row_hash']})
        market = fact['market_id']
        duplicate = seen.get(market)
        if duplicate and duplicate[0] != fact['row_hash']:
            raise ValueError('conflicting market version cannot enter selection')
        seen.setdefault(market, (fact['row_hash'], evidence))
        identity = fact['identity']
        metadata = (project_metadata(raw, outcome_count=len(identity['outcomes']))
                    if identity else None)
        rows.append({**fact, 'evidence_id': evidence, 'metadata': metadata,
                     'duplicate_of': duplicate[1] if duplicate else None})
    return rows


def _member(row, available, reference):
    if not row['eligible'] or row['duplicate_of']:
        return None
    metadata = row['metadata']
    if metadata is None or row['selected_token_id'] is None:
        raise ValueError('eligible selection member has unresolved identity')
    close = metadata['close_time_utc']['value']
    close_bin = 'unknown'
    if close is not None:
        seconds = (_time({'utc': close}) - _time(reference)).total_seconds()
        close_bin = ('past' if seconds <= 0 else 'le_1d' if seconds <= 86400
                     else 'le_7d' if seconds <= 604800 else 'le_30d' if seconds <= 2592000
                     else 'gt_30d')
    # Prefix actual categories so a literal source category "unknown" cannot collapse
    # into the missing-category stratum.
    category = metadata['category']['value']
    return FrameMember(
        market_id=row['market_id'], token_id=row['selected_token_id'],
        source_observation_id=row['evidence_id'], available_at=_time(available),
        time_stratum=_time(reference).date().isoformat(),
        category='unknown' if category is None else 'source:' + category,
        close_stratum=close_bin, probability=metadata['metadata_probability']['value'],
        liquidity=metadata['liquidity']['value'], event_group=None, group_available_at=None,
        eligible=True, exclusion_reason=None, triggered=False, trigger_id=None,
        trigger_available_at=None,
    )


def _add_counts(counts, rows):
    for row in rows:
        counts['source_rows'] += 1
        counts['eligible_row_count'] += row['eligible']
        counts['duplicate_market_rows'] += row['duplicate_of'] is not None
        counts['sampling_members'] += bool(row['eligible'] and not row['duplicate_of'])
        for reason in row['exclusion_reasons']:
            counts['excluded:' + reason] += 1
        if row['metadata']:
            for key in ('category', 'close_time_utc', 'metadata_probability', 'liquidity'):
                counts['metadata:' + key + ':' + row['metadata'][key]['state']] += 1


def _check_counts(counts, report):
    for key in ('source_rows', 'eligible_row_count', 'duplicate_market_rows'):
        if counts[key] != report[key]:
            raise ValueError('selection inventory does not cover the original frame')
    if {k.removeprefix('excluded:'): v for k, v in counts.items() if k.startswith('excluded:')} != (
        report['exclusion_counts']
    ):
        raise ValueError('selection inventory exclusions differ')


def _plan(policy, members, cutoff, original_hash, inventory_hash):
    if policy['schema_version'] != VERSION:
        from .panel_selection import bound_plan

        return bound_plan(policy, members, cutoff, original_hash, inventory_hash)
    return plan_sample(
        _protocol(policy), members, cutoff=_time(cutoff),
        frame_scope='eligible mapped Gamma rows in the preserved complete source interval',
        frame_status='enumerated_complete', frame_evidence_ids=[original_hash, inventory_hash],
        max_frame_members=policy['budget']['rows'],
    )


def create_selection(frame_root, *, implementation_commit, output_root, repository=None,
                     budget=SelectionBudget(), scheduled_per_stratum=1, max_unique_markets=256):
    """Seal a new bounded development selection; never resume/reseed an existing directory."""
    return _create_selection(
        frame_root, implementation_commit=implementation_commit, output_root=output_root,
        repository=repository, budget=budget, scheduled_per_stratum=scheduled_per_stratum,
        max_unique_markets=max_unique_markets)


def _create_selection(frame_root, *, implementation_commit, output_root, repository=None,
                      budget=SelectionBudget(), scheduled_per_stratum=1, max_unique_markets=256,
                      panel_root=None):
    frame_root, root = _canonical(frame_root), _canonical(output_root)
    if (not root.name.startswith('fs2_selection_') or root == frame_root
            or frame_root in root.parents or root in frame_root.parents):
        raise ValueError('separate fresh fs2_selection_ directory required')
    if not re.fullmatch(r'[a-f0-9]{40}', implementation_commit):
        raise ValueError('original full immutable commit required')
    if type(budget) is not SelectionBudget:
        raise ValueError('explicit selection budget required')
    if root.exists():
        raise FileExistsError('existing selection retained; never resume or reseed')
    if shutil.disk_usage(root.parent).free < budget.output_bytes + budget.free_reserve_bytes:
        raise ValueError('insufficient selection storage reserve')
    build = verified_panel_build()
    if panel_root is None:
        protocol = SamplingProtocol(secrets.token_hex(32), scheduled_per_stratum, 1, 1,
                                    max_unique_markets)
        declaration = {
            'schema_version': VERSION, 'policy': POLICY, 'build': build,
            'frame_root': str(frame_root), 'implementation_commit': implementation_commit,
            'budget': asdict(budget), 'sampling_protocol': asdict(protocol),
            'declared_at': _clock(),
        }
    else:
        from .panel_selection import selection_policy

        declaration = selection_policy(panel_root, frame_root, root, implementation_commit,
                                       budget, build)
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    resource = _Budget(root, budget)
    try:
        resource.persist(root, 'selection_policy', declaration)
        policy, policy_ack = _pair(root, 'selection_policy')
        # Reserve maximum child report plus declaration/receipt before invoking its decoder.
        resource.check(34 * 1048576)
        original = read_original_frame(frame_root, implementation_commit=implementation_commit,
                                       output_root=root / READ_FOLDER, repository=repository)
        resource.written += sum(p.stat().st_size for p in (root / READ_FOLDER).rglob('*')
                                if p.is_file())
        resource.check()
        report = original['report']
        _complete(report, budget)
        if not _ordered_clocks(policy_ack['durable_ack'],
                               original['read_receipt']['metadata_read_started_at']):
            raise ValueError('original read preceded the frozen seed/policy')
        pages_root = root / 'pages'
        pages_root.mkdir(mode=0o700)
        _sync_directory(root)
        seen, counts, members, manifest = {}, Counter(), [], []
        for entry in report['pages']:
            resource.check()
            started = _clock()
            rows = _projection(frame_root, entry, seen, report['frame_report_hash'])
            completed = _clock()
            if not _ordered_clocks(entry['available_at'], original['read_available_at'],
                                   started, completed):
                raise ValueError('projection chronology differs')
            folder = pages_root / entry['capture_id']
            folder.mkdir(mode=0o700)
            _sync_directory(pages_root)
            resource.persist(folder, 'projection', {
                'policy_hash': policy_ack['payload_hash'], 'source_page': entry,
                'read_started_at': started, 'projected_at': completed, 'rows': rows,
            })
            _, ack = _pair(folder, 'projection')
            manifest.append({'capture_id': entry['capture_id'],
                             'projection_hash': ack['payload_hash']})
            _add_counts(counts, rows)
            members.extend(m for r in rows if (m := _member(r, ack['durable_ack'],
                                                             policy['declared_at'])) is not None)
        _check_counts(counts, report)
        resource.persist(root, 'inventory', {'policy_hash': policy_ack['payload_hash'],
                                             'pages': manifest, 'counts': dict(counts)})
        _, inventory_ack = _pair(root, 'inventory')
        cutoff, started = _clock(), _clock()
        if panel_root is not None:
            from .panel_selection import freshness

            freshness(policy, report, cutoff)
        plan = _plan(policy, members, cutoff, report['frame_report_hash'],
                     inventory_ack['payload_hash'])
        completed = _clock()
        verified_panel_build()
        resource.persist(root, 'selection_plan', plan)
        _, plan_ack = _pair(root, 'selection_plan')
        resource.persist(root, 'selection_report', {
            'schema_version': policy['schema_version'], 'policy_hash': policy_ack['payload_hash'],
            'original_read_hash': original['read_receipt_hash'],
            'frame_report_hash': report['frame_report_hash'],
            'inventory_hash': inventory_ack['payload_hash'], 'plan_hash': plan_ack['payload_hash'],
            'sampling_cutoff': cutoff, 'computation_started_at': started, 'computed_at': completed,
            'source_interval_start': report['interval_start'],
            'source_interval_end': report['interval_end'],
            'original_frame_available_at': report['frame_available_at'],
            **_status(policy, report),
            'counts': dict(counts), 'unique_selected_markets': plan['unique_selected_markets'],
            'origin_admitted': False, 'population_inference_eligible': False,
        })
        if panel_root is not None:
            _, report_ack = _pair(root, 'selection_report')
            freshness(policy, report, report_ack['durable_ack'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        try:
            _persist(root, 'selection_failure', {
                'schema_version': VERSION, 'failed_at': _clock(), 'error_class': type(exc).__name__,
            })
        except OSError:
            pass  # A storage failure must leave its original torn files intact.
        raise
    # Verification streams the inventory again. Release construction state so the
    # independent replay does not retain two copies of the entire eligible population.
    del members, seen
    return read_selection(root)


def _status(policy, original):
    if policy['schema_version'] != VERSION:
        from .panel_selection import status

        return status(original)
    return {'provenance_class': 'synthetic' if original['provenance_class'] == 'synthetic'
            else 'reconstructed', 'state': 'development_selection_sealed'}


def _read_original(root, policy):
    folder = root / READ_FOLDER
    if (folder / 'read_failure.json').exists():
        raise ValueError('failed original read cannot be admitted')
    declaration, declaration_ack = _pair(folder, 'read_policy')
    receipt, receipt_ack = _pair(folder, 'read_receipt')
    data = _read(folder / 'original_report.json')
    report = json.loads(data)
    frame_root = _canonical(policy['frame_root'])
    old, old_ack = _pair(frame_root, 'frame_report')
    old_policy, old_policy_ack = _pair(frame_root, 'frame_policy')
    facts = {k: v for k, v in report.items()
             if k not in {'frame_report_hash', 'frame_available_at'}}
    if (receipt['read_policy_hash'] != declaration_ack['payload_hash']
            or declaration['reader_build'] != policy['build']
            or declaration['frame_root'] != policy['frame_root']
            or declaration['implementation_commit'] != policy['implementation_commit']
            or declaration['frame_report_hash'] != old_ack['payload_hash']
            or declaration['frame_policy_hash'] != old_policy_ack['payload_hash']
            or old['policy_hash'] != old_policy_ack['payload_hash']
            or declaration['original_build'] != old_policy['build']
            or receipt['output_hash'] != _digest(data) or receipt['output_bytes'] != len(data)
            or report['frame_report_hash'] != old_ack['payload_hash'] or facts != old
            or report['frame_available_at'] != old_ack['durable_ack']
            or receipt['original_report_hash'] != old_ack['payload_hash']
            or receipt['original_state'] != report['state']
            or receipt['original_provenance_class'] != report['provenance_class']
            or receipt['origin_admitted'] is not False
            or receipt['observation_clocks_changed'] is not False):
        raise ValueError('original read evidence differs')
    if {p.name for p in frame_root.iterdir() if p.is_dir()} != {
        p['capture_id'] for p in report['pages']
    }:
        raise ValueError('original frame page closure differs')
    if not _ordered_clocks(old_ack['durable_ack'], declaration['metadata_read_started_at'],
                           declaration_ack['durable_ack'], receipt['verification_started_at'],
                           receipt['completed_at'], receipt_ack['durable_ack']):
        raise ValueError('original read chronology differs')
    return report, declaration, receipt_ack


def read_selection(root):
    """Read-only full closure and deterministic replay; torn runs are refused, not repaired."""
    root = _canonical(root)
    policy, policy_ack = _pair(root, 'selection_policy')
    if policy['schema_version'] != VERSION:
        from .panel_selection import verify_policy

        verify_policy(root, policy, policy_ack)
    elif policy['policy'] != POLICY:
        raise ValueError('selection policy/build differs')
    if (policy['build'] != verified_panel_build()
            or not _ordered_clocks(policy['declared_at'], policy_ack['durable_ack'])):
        raise ValueError('selection policy/build differs')
    budget = SelectionBudget(**policy['budget'])
    resource = _Budget(root, budget)
    report, report_ack = _pair(root, 'selection_report')
    if (root / 'selection_failure.json').exists():
        raise ValueError('failed selection cannot be admitted')
    original, declaration, original_ack = _read_original(root, policy)
    _complete(original, budget)
    inventory, inventory_ack = _pair(root, 'inventory')
    plan, plan_ack = _pair(root, 'selection_plan')
    if (inventory['policy_hash'] != policy_ack['payload_hash']
            or report['policy_hash'] != policy_ack['payload_hash']
            or report['original_read_hash'] != original_ack['payload_hash']
            or report['frame_report_hash'] != original['frame_report_hash']
            or report['inventory_hash'] != inventory_ack['payload_hash']
            or report['plan_hash'] != plan_ack['payload_hash']):
        raise ValueError('selection manifest lineage differs')
    expected_ids = [p['capture_id'] for p in original['pages']]
    if ([p['capture_id'] for p in inventory['pages']] != expected_ids
            or {p.name for p in (root / 'pages').iterdir()} != set(expected_ids)):
        raise ValueError('selection inventory page closure differs')
    seen, counts, members = {}, Counter(), []
    prior = original_ack['durable_ack']
    if not _ordered_clocks(policy_ack['durable_ack'],
                           declaration['metadata_read_started_at'], prior):
        raise ValueError('original frame read preceded selection policy')
    for entry, manifest in zip(original['pages'], inventory['pages'], strict=True):
        # Read-only replay checks deadline, not current free space: low disk cannot change
        # the historical validity of an intact sealed journal.
        if time.monotonic() - resource.started > budget.seconds:
            raise ValueError('selection verification time budget exhausted')
        page, ack = _pair(root / 'pages' / entry['capture_id'], 'projection')
        rows = _projection(Path(policy['frame_root']), entry, seen, original['frame_report_hash'])
        if (page['policy_hash'] != policy_ack['payload_hash'] or page['source_page'] != entry
                or page['rows'] != rows or ack['payload_hash'] != manifest['projection_hash']
                or not _ordered_clocks(entry['available_at'], prior, page['read_started_at'],
                                       page['projected_at'], ack['durable_ack'])):
            raise ValueError('selection projection/source/clock differs')
        prior = ack['durable_ack']
        _add_counts(counts, rows)
        members.extend(m for r in rows if (m := _member(r, ack['durable_ack'],
                                                         policy['declared_at'])) is not None)
    _check_counts(counts, original)
    if (inventory['counts'] != dict(counts) or report['counts'] != dict(counts)
            or not _ordered_clocks(prior, inventory_ack['durable_ack'], report['sampling_cutoff'],
                                   report['computation_started_at'], report['computed_at'],
                                   plan_ack['durable_ack'], report_ack['durable_ack'])):
        raise ValueError('selection counts/cutoff/chronology differs')
    expected = _plan(policy, members, report['sampling_cutoff'], original['frame_report_hash'],
                     inventory_ack['payload_hash'])
    if time.monotonic() - resource.started > budget.seconds:
        raise ValueError('selection verification time budget exhausted')
    if sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) > budget.output_bytes:
        raise ValueError('selection retained output exceeds frozen budget')
    if policy['schema_version'] != VERSION:
        from .panel_selection import freshness

        freshness(policy, original, report['sampling_cutoff'])
        freshness(policy, original, report_ack['durable_ack'])
    if (plan != json.loads(_json_bytes(expected))
            or report['schema_version'] != policy['schema_version']
            or _json_bytes({k: report.get(k) for k in _status(policy, original)})
                != _json_bytes(_status(policy, original))
            or report['origin_admitted'] is not False
            or report['population_inference_eligible'] is not False
            or report['unique_selected_markets'] != expected['unique_selected_markets']
            or report['source_interval_start'] != original['interval_start']
            or report['source_interval_end'] != original['interval_end']
            or report['original_frame_available_at'] != original['frame_available_at']):
        raise ValueError('selection plan/status differs')
    verified_panel_build()
    return {**report, 'selection_report_hash': report_ack['payload_hash'],
            'selection_available_at': report_ack['durable_ack'], 'plan': plan}
