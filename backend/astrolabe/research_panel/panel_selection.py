"""Fresh declaration-bound selection; no source collection, origin or measured controls."""

import shutil
from collections import Counter
from dataclasses import asdict
from datetime import timedelta

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair

from .assessments import TriggerAssessmentPolicy
from .panel_declaration import PanelProtocol, read_panel_declaration
from .sampling import plan_sample
from .selection import POLICY as LEGACY_POLICY
from .selection import SelectionBudget, _canonical, _create_selection, _protocol

VERSION = 'fs2-panel-selection-v1'
ASSESSMENTS = {'version': 'fs2-no-measured-assessments-v1',
               'state': 'not_assessed', 'reason': 'not_assessed',
               'supplied_assessments': 0, 'matched_controls_eligible': False}
POLICY = {**LEGACY_POLICY, 'use': 'fresh_declaration_bound_selection_only',
          'arms': 'scheduled; all trigger assessments absent; no negative controls',
          'freshness_basis': 'original interval request start, not new read availability',
          'collection_enabled': False, 'accepted_panel': False}


def selection_root(panel_root):
    panel = _canonical(panel_root)
    if not panel.name.startswith('fs2_panel_'):
        raise ValueError('canonical panel declaration required')
    return panel.with_name('fs2_selection_panel_' + panel.name.removeprefix('fs2_panel_'))


def create_panel_selection(panel_root, *, repository=None):
    """One fresh attempt per declaration, with no caller seed/clock/assessment override."""
    panel = _canonical(panel_root)
    read_panel_declaration(panel)
    payload, _ = _pair(panel, 'panel_policy')
    return _create_selection(
        payload['frame_root'], implementation_commit=payload['frame_implementation_commit'],
        output_root=selection_root(panel), repository=repository, panel_root=panel)


def selection_policy(panel, frame, root, commit, budget, build):
    declaration = read_panel_declaration(panel)
    payload, ack = _pair(panel, 'panel_policy')
    if (root != selection_root(panel) or str(frame) != payload['frame_root']
            or commit != payload['frame_implementation_commit']
            or budget != SelectionBudget() or build != payload['build']
            or ack['payload_hash'] != declaration['declaration_hash']):
        raise ValueError('selection differs from frozen declaration')
    if shutil.disk_usage(root.parent).free < declaration['reservation']['required_free_bytes']:
        raise ValueError('insufficient full panel/control/target capacity before selection')
    return {
        'schema_version': VERSION, 'policy': POLICY, 'build': build,
        'frame_root': str(frame), 'implementation_commit': commit, 'budget': asdict(budget),
        'sampling_protocol': payload['sampling_recipe'], 'declared_at': _clock(),
        'panel_root': str(panel), 'panel_declaration_hash': ack['payload_hash'],
        'panel_available_at': ack['durable_ack'], 'panel_protocol': payload['protocol'],
        'assessment_policy': ASSESSMENTS,
    }


def verify_policy(root, policy, ack):
    if policy['schema_version'] != VERSION:
        raise ValueError('unknown selection schema')
    panel = _canonical(policy['panel_root'])
    declaration = read_panel_declaration(panel)
    payload, panel_ack = _pair(panel, 'panel_policy')
    if (root != selection_root(panel) or policy['policy'] != POLICY
            or policy['assessment_policy'] != ASSESSMENTS
            or policy['budget'] != asdict(SelectionBudget())
            or policy['build'] != payload['build']
            or policy['panel_declaration_hash'] != declaration['declaration_hash']
            or policy['panel_available_at'] != panel_ack['durable_ack']
            or policy['frame_root'] != payload['frame_root']
            or policy['implementation_commit'] != payload['frame_implementation_commit']
            or _json_bytes(policy['sampling_protocol']) != _json_bytes(payload['sampling_recipe'])
            or policy['panel_protocol'] != payload['protocol']
            or not _ordered_clocks(panel_ack['durable_ack'], policy['declared_at'],
                                   ack['durable_ack'])):
        raise ValueError('selection declaration/recipe/assessment/chronology differs')
    # Deterministic directory ownership and complete sealed artefacts; never repair a prefix.
    if {p.name for p in root.iterdir()} != {
        'selection_policy.json', 'selection_policy_ack.json',
        'selection_report.json', 'selection_report_ack.json',
        'selection_plan.json', 'selection_plan_ack.json', 'inventory.json',
        'inventory_ack.json', 'pages', 'fs2_frame_read_original',
    }:
        raise ValueError('complete isolated panel selection required')
    directories = {'pages', 'fs2_frame_read_original'}
    for path in root.iterdir():
        if path.is_symlink() or not (path.is_dir() if path.name in directories
                                     else path.is_file()):
            raise ValueError('unexpected panel selection file type')
    child = root / 'fs2_frame_read_original'
    if {p.name for p in child.iterdir()} != {
        'read_policy.json', 'read_policy_ack.json', 'read_receipt.json',
        'read_receipt_ack.json', 'original_report.json',
    } or any(p.is_symlink() or not p.is_file() for p in child.iterdir()):
        raise ValueError('original frame read file closure differs')
    pages = list((root / 'pages').iterdir())
    if len(pages) > SelectionBudget().pages:
        raise ValueError('panel selection page limit exceeded')
    for folder in pages:
        if (folder.is_symlink() or not folder.is_dir()
                or {p.name for p in folder.iterdir()} != {'projection.json', 'projection_ack.json'}
                or any(p.is_symlink() or not p.is_file() for p in folder.iterdir())):
            raise ValueError('panel selection projection file closure differs')


def freshness(policy, original, point):
    protocol = PanelProtocol(**policy['panel_protocol'])
    start, end, available = (original[k] for k in
                            ('interval_start', 'interval_end', 'frame_available_at'))
    if not _ordered_clocks(start, end, available, point):
        raise ValueError('frame interval/availability is future or unordered')
    if _time(end) - _time(start) > timedelta(seconds=protocol.max_frame_interval_seconds):
        raise ValueError('frame interval exceeds frozen selection limit')
    if _time(point) - _time(start) > timedelta(seconds=protocol.max_frame_age_seconds):
        raise ValueError('frame stale under frozen selection limit')


def bound_plan(policy, members, cutoff, original_hash, inventory_hash):
    if policy['schema_version'] != VERSION or policy['assessment_policy'] != ASSESSMENTS:
        raise ValueError('explicit no-measured-assessments policy required')
    assessment = TriggerAssessmentPolicy(
        trigger_policy_hash=content_hash(ASSESSMENTS), declared_at=_time(policy['declared_at']),
        max_window_age_seconds=0, max_assessment_age_seconds=0)
    plan = plan_sample(
        _protocol(policy), members, cutoff=_time(cutoff),
        frame_scope='eligible mapped Gamma rows in the preserved complete source interval',
        frame_status='enumerated_complete', frame_evidence_ids=[original_hash, inventory_hash],
        max_frame_members=policy['budget']['rows'], assessment_policy=assessment,
        trigger_assessments=(),
    )
    counts = Counter(a['arm'] for a in plan['assignments'])
    if counts['scheduled'] > policy['panel_protocol']['scheduled_slots']:
        raise ValueError('sample exceeds scheduled slot ceiling; never truncate')
    if counts['triggered'] or counts['control']:
        raise ValueError('absent assessments cannot admit triggers or controls')
    inventory = plan.pop('assessment_inventory')
    plan.pop('plan_hash')
    plan.update(
        schema_version='fs2-panel-selection-plan-v1',
        assessment_inventory_encoding={
            'version': 'fs2-uniform-not-assessed-inventory-v1',
            'member_domain': 'all members in the complete retained selection inventory',
            'member_count': len(members), 'inventory_hash': content_hash(inventory),
            'assessment': None, 'effective_state': 'not_assessed', 'reasons': ['not_assessed'],
        },
        collection_enabled=False, accepted_panel=False,
    )
    return {**plan, 'plan_hash': content_hash(plan)}


def status(original):
    return {'provenance_class': original['provenance_class'],
            'state': 'fresh_selection_sealed', 'collection_enabled': False,
            'accepted_panel': False, 'feature_store_admitted': False}
