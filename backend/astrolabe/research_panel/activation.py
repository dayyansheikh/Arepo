"""Actual selection consumption and immutable schedules; no sources or origin admission."""

import shutil
import time
from datetime import timedelta

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist

from .build_identity import verified_panel_build
from .input_read import _canonical
from .panel_declaration import PanelProtocol, read_panel_declaration
from .panel_selection import VERSION as SELECTION_VERSION
from .panel_selection import freshness, selection_root
from .selection import read_selection

VERSION = 'fs2-panel-activation-v1'
POLICY = {'lead_seconds': 2, 'max_output_bytes': 32 * 1048576,
          'max_artifact_bytes': 16 * 1048576, 'max_seconds': 600,
          'per_origin_metadata_bytes': 131072, 'per_target_metadata_bytes': 131072,
          'failure_reserve_bytes': 65536, 'free_reserve_bytes': 2 * 1024**3,
          'schedule_basis': 'activation facts durable acknowledgement plus lead and cadence',
          'collection_enabled': False, 'origin_admitted': False, 'accepted_panel': False}


def activation_root(panel_root):
    panel = _canonical(panel_root)
    if not panel.name.startswith('fs2_panel_'):
        raise ValueError('canonical panel declaration required')
    return panel.with_name('fs2_activation_' + panel.name.removeprefix('fs2_panel_'))


def allocation(declaration):
    reserved = declaration['reservation']
    metadata = (reserved['origin_slots'] * POLICY['per_origin_metadata_bytes']
                + reserved['target_attempt_slots'] * POLICY['per_target_metadata_bytes'])
    total = reserved['total_retained_bytes'] + POLICY['max_output_bytes'] + metadata
    return {'panel_reservation': reserved, 'runtime_metadata_bytes': metadata,
            'activation_bytes': POLICY['max_output_bytes'], 'total_retained_bytes': total,
            'required_free_bytes': total + POLICY['free_reserve_bytes'],
            'future_writer_quota_enforcement_required': True,
            'duration_seconds': reserved['duration_seconds'] + POLICY['lead_seconds']}


def _check(root, started, addition=0, *, writing=False):
    if time.monotonic() - started > POLICY['max_seconds']:
        raise ValueError('activation processing deadline exceeded')
    paths = list(root.iterdir())
    if len(paths) > 6 or any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('unexpected activation file closure')
    if any(p.stat().st_size > POLICY['max_artifact_bytes'] for p in paths):
        raise ValueError('activation artefact exceeds readable limit')
    if sum(p.stat().st_size for p in paths) + addition > (
        POLICY['max_output_bytes'] - POLICY['failure_reserve_bytes']
    ):
        raise ValueError('activation retained-byte budget exceeded')
    if writing and shutil.disk_usage(root).free < POLICY['free_reserve_bytes'] + addition:
        raise ValueError('activation free-space reserve reached')


def _save(root, name, payload, started):
    size = len(_json_bytes(payload))
    if size > POLICY['max_artifact_bytes']:
        raise ValueError('activation artefact exceeds readable limit')
    _check(root, started, size + 4096, writing=True)
    _persist(root, name, payload)


def _consume(panel, started, root):
    declaration = read_panel_declaration(panel)
    selection = selection_root(panel)
    report = read_selection(selection)
    if report['schema_version'] != SELECTION_VERSION or report['state'] != 'fresh_selection_sealed':
        raise ValueError('fresh declaration-bound selection required')
    policy, policy_ack = _pair(selection, 'selection_policy')
    inventory, inventory_ack = _pair(selection, 'inventory')
    if (policy['panel_declaration_hash'] != declaration['declaration_hash']
            or inventory_ack['payload_hash'] != report['inventory_hash']):
        raise ValueError('activation selection lineage differs')
    wanted = {}
    for assignment in report['plan']['assignments']:
        wanted.setdefault(assignment['source_observation_id'], []).append(assignment)
    selected = []
    for entry in inventory['pages']:
        _check(root, started)
        page, ack = _pair(selection / 'pages' / entry['capture_id'], 'projection')
        if (ack['payload_hash'] != entry['projection_hash']
                or page['policy_hash'] != policy_ack['payload_hash']):
            raise ValueError('activation selected projection changed during read')
        for row in page['rows']:
            roles = wanted.get(row['evidence_id'])
            if roles is None:
                continue
            identity = row['identity']
            token = row['selected_token_id']
            outcomes = [v for v in identity['outcomes'] if v['token_id'] == token]
            if (len(outcomes) != 1 or not row['eligible'] or row['duplicate_of']
                    or any(a['market_id'] != row['market_id'] or a['token_id'] != token
                           for a in roles)):
                raise ValueError('activation assignment identity differs')
            selected.append({
                'market_id': row['market_id'], 'token_id': token,
                'condition_id': identity['condition_id'],
                'mapping_version': identity['mapping_version'],
                'outcome_index': outcomes[0]['outcome_index'],
                'outcome_label': outcomes[0]['outcome_label'],
                'source_observation_id': row['evidence_id'], 'row_hash': row['row_hash'],
                'projection_hash': ack['payload_hash'],
                'projection_available_at': ack['durable_ack'], 'roles': roles,
            })
    if (len(selected) != report['unique_selected_markets'] or len(selected) > 256
            or len({r['source_observation_id'] for r in selected}) != len(wanted)):
        raise ValueError('activation selected identity closure differs')
    # Pin the report again after consuming its projections; no substituted selection prefix.
    _, final_ack = _pair(selection, 'selection_report')
    if (final_ack['payload_hash'] != report['selection_report_hash']
            or final_ack['durable_ack'] != report['selection_available_at']):
        raise ValueError('activation selection changed during read')
    return declaration, policy, report, sorted(selected, key=lambda r: r['market_id'])


def _fresh(policy, report, at):
    freshness(policy, {'interval_start': report['source_interval_start'],
                       'interval_end': report['source_interval_end'],
                       'frame_available_at': report['original_frame_available_at']}, at)


def _summary(facts, ack, panel_policy):
    protocol = PanelProtocol(**panel_policy['protocol'])
    first = _time(ack['durable_ack']) + timedelta(seconds=POLICY['lead_seconds'])
    slots = []
    for cycle in range(protocol.cycles):
        scheduled = first + timedelta(seconds=cycle * protocol.cadence_seconds)
        for member in facts['selected']:
            identity = {'panel_declaration_hash': facts['panel_declaration_hash'],
                        'cycle': cycle, 'market_id': member['market_id'],
                        'token_id': member['token_id']}
            slots.append({**identity, 'intent_id': content_hash(identity),
                          'scheduled_at': scheduled.isoformat(),
                          'latest_origin_at': (scheduled + timedelta(
                              seconds=protocol.max_origin_delay_seconds)).isoformat()})
    return {'schema_version': VERSION, 'activation_hash': ack['payload_hash'],
            'activation_available_at': ack['durable_ack'],
            'selection_report_hash': facts['selection_report_hash'],
            'selected': facts['selected'], 'slots': slots,
            'provenance_class': facts['provenance_class'],
            'collection_enabled': False, 'origin_admitted': False, 'accepted_panel': False,
            'feature_store_admitted': False}


def activate_panel(panel_root):
    """Consume actual verified selection; schedule only, with no caller clock or payload."""
    panel = _canonical(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, 'panel_policy')
    root = activation_root(panel)
    if root.exists():
        raise FileExistsError('activation already retained; never resume or reschedule')
    reserved = allocation(declaration)
    if shutil.disk_usage(root.parent).free < reserved['required_free_bytes']:
        raise ValueError('insufficient complete activation/origin/target reservation')
    build, started = verified_panel_build(), time.monotonic()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(root, 'activation_policy', {
            'schema_version': VERSION, 'policy': POLICY, 'build': build,
            'panel_root': str(panel), 'panel_declaration_hash': declaration['declaration_hash'],
            'reservation': reserved, 'declared_at': _clock(),
        }, started)
        policy, policy_ack = _pair(root, 'activation_policy')
        read_started = _clock()
        current, selection_policy, report, selected = _consume(panel, started, root)
        completed = _clock()
        if (current != declaration or not _ordered_clocks(
            policy['declared_at'], policy_ack['durable_ack'], read_started, completed
        ) or not _ordered_clocks(report['selection_available_at'], read_started)):
            raise ValueError('activation source/declaration/read chronology differs')
        _fresh(selection_policy, report, completed)
        if verified_panel_build() != build:
            raise ValueError('activation build changed')
        _save(root, 'activation_facts', {
            'schema_version': VERSION, 'policy_hash': policy_ack['payload_hash'],
            'panel_declaration_hash': declaration['declaration_hash'],
            'selection_report_hash': report['selection_report_hash'],
            'selection_available_at': report['selection_available_at'],
            'read_started_at': read_started, 'read_completed_at': completed,
            'selected': selected, 'provenance_class': report['provenance_class'],
            'collection_enabled': False, 'origin_admitted': False, 'accepted_panel': False,
        }, started)
        facts, ack = _pair(root, 'activation_facts')
        if not _ordered_clocks(completed, ack['durable_ack']):
            raise ValueError('activation acknowledgement chronology differs')
        _fresh(selection_policy, report, ack['durable_ack'])
        _check(root, started)
        # Do not spend the new lead interval on a second full population replay. All facts
        # above were actually verified; independent read_activation performs recovery replay.
        return _summary(facts, ack, panel_policy)
    except BaseException as exc:
        try:
            _persist(root, 'activation_failure', {'exception_type': type(exc).__name__,
                                                 'at': _clock()})
        except (OSError, ValueError):
            pass
        raise


def read_activation(panel_root):
    """Replay at the original acknowledgement; expired schedules are never moved forward."""
    panel = _canonical(panel_root)
    root, started = activation_root(panel), time.monotonic()
    if {p.name for p in root.iterdir()} != {
        name + suffix for name in ('activation_policy', 'activation_facts')
        for suffix in ('.json', '_ack.json')
    }:
        raise ValueError('complete successful activation required')
    _check(root, started)
    policy, policy_ack = _pair(root, 'activation_policy')
    declaration, selection_policy, report, selected = _consume(panel, started, root)
    panel_policy, _ = _pair(panel, 'panel_policy')
    facts, ack = _pair(root, 'activation_facts')
    if (policy['schema_version'] != VERSION or policy['policy'] != POLICY
            or policy['build'] != verified_panel_build() or policy['panel_root'] != str(panel)
            or policy['panel_declaration_hash'] != declaration['declaration_hash']
            or policy['reservation'] != allocation(declaration)
            or facts['schema_version'] != VERSION
            or facts['policy_hash'] != policy_ack['payload_hash']
            or facts['panel_declaration_hash'] != declaration['declaration_hash']
            or facts['selection_report_hash'] != report['selection_report_hash']
            or facts['selection_available_at'] != report['selection_available_at']
            or facts['selected'] != selected
            or facts['provenance_class'] != report['provenance_class']
            or any(facts[k] is not False for k in
                   ('collection_enabled', 'origin_admitted', 'accepted_panel'))
            or not _ordered_clocks(policy['declared_at'], policy_ack['durable_ack'],
                                   facts['read_started_at'], facts['read_completed_at'],
                                   ack['durable_ack'])
            or not _ordered_clocks(report['selection_available_at'], facts['read_started_at'])):
        raise ValueError('activation policy/selection/identity/chronology differs')
    _fresh(selection_policy, report, facts['read_completed_at'])
    _fresh(selection_policy, report, ack['durable_ack'])
    _check(root, started)
    return _summary(facts, ack, panel_policy)
