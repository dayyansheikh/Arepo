"""D120 declaration-bound selection: fee category strata and group-disjoint screening draw.

``panel_selection.py`` is frozen (D116/D118); this module mirrors it for the pairing declaration.
Population: the D118 rule (scheduled end after the selection declaration or unknown, and
original-frame Gamma liquidity >= 1000), then the declared category policy (default all; an
optional exclusion list gives explicit zero-inclusion records). Category is ``fee_category``
from the original-frame ``feeType`` (frozen prefix map); the dependence group is an attribute
computed over every sampling member of the complete frame and never enters the stratum key.
"""

from collections import Counter
from dataclasses import asdict, replace

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _json_bytes
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair

from . import pairing
from .pairing_declaration import (
    PairingPanelProtocol,
    read_pairing_declaration,
)
from .panel_declaration import LIQUIDITY_FLOOR, LIQUIDITY_POPULATION
from .panel_selection import (
    ASSESSMENTS,
    LIQUIDITY_SCOPE,
    LIQUIDITY_SOURCE,
    _liquidity_scope,
    selection_root,
)
from .panel_selection import POLICY as PANEL_POLICY
from .sampling import plan_sample

VERSION = 'fs2-pairing-selection-v1'
PLAN_VERSION = 'fs2-pairing-selection-plan-v1'
TEMPORAL_REASON = 'scheduled_end_at_or_before_selection_declaration'
POLICY = {**PANEL_POLICY, 'use': 'fresh_declaration_bound_pairing_selection_only',
          'arms': 'screened only; roles drawn after screening; no scheduled arm',
          'category': 'fee_category from original-frame feeType (frozen prefix map)',
          'dependence': 'group attribute over the complete frame; never a stratum field'}
SCOPE = (LIQUIDITY_SCOPE + '; category policy applied to fee_category; one screened member per '
         'dependence group across all drawn strata')


def is_pairing_policy(policy):
    return policy.get('schema_version') == VERSION


def selection_policy(panel, frame, root, commit, budget, build):
    from .selection import SelectionBudget

    declaration = read_pairing_declaration(panel)
    payload, ack = _pair(panel, 'panel_policy')
    if (root != selection_root(panel) or str(frame) != payload['frame_root']
            or commit != payload['frame_implementation_commit']
            or budget != SelectionBudget() or build != payload['build']
            or ack['payload_hash'] != declaration['declaration_hash']):
        raise ValueError('selection differs from frozen declaration')
    import shutil

    if shutil.disk_usage(root.parent).free < declaration['reservation']['required_free_bytes']:
        raise ValueError('insufficient full screened/origin/target capacity before selection')
    return {
        'population_policy': payload['population_policy'],
        'category_policy': payload['category_policy'],
        **({'computation_storage_profile': payload['computation_storage_profile']}
           if 'computation_storage_profile' in payload else {}),
        'schema_version': VERSION, 'policy': POLICY, 'build': build,
        'frame_root': str(frame), 'implementation_commit': commit, 'budget': asdict(budget),
        'sampling_protocol': payload['sampling_recipe'], 'declared_at': _clock(),
        'panel_root': str(panel), 'panel_declaration_hash': ack['payload_hash'],
        'panel_available_at': ack['durable_ack'], 'panel_protocol': payload['protocol'],
        'pairing_design': payload['pairing_design'],
        'grouping_policy': pairing.grouping_policy(
            pairing.design_from_dict(payload['pairing_design']).underlying_grouping),
        'fee_category_map': {'version': pairing.FEE_CATEGORY_MAP_VERSION,
                             'prefixes': [list(x) for x in pairing.FEE_CATEGORY_PREFIXES]},
        'assessment_policy': ASSESSMENTS,
    }


def verify_policy(root, policy, ack):
    from .selection import SelectionBudget, _canonical

    if policy['schema_version'] != VERSION:
        raise ValueError('unknown selection schema')
    panel = _canonical(policy['panel_root'])
    declaration = read_pairing_declaration(panel)
    payload, panel_ack = _pair(panel, 'panel_policy')
    design = pairing.design_from_dict(payload['pairing_design'])
    if (root != selection_root(panel) or policy['policy'] != POLICY
            or policy['population_policy'] != payload['population_policy']
            or policy['category_policy'] != payload['category_policy']
            or policy['pairing_design'] != payload['pairing_design']
            or policy['grouping_policy'] != pairing.grouping_policy(design.underlying_grouping)
            or policy['fee_category_map'] != {
                'version': pairing.FEE_CATEGORY_MAP_VERSION,
                'prefixes': [list(x) for x in pairing.FEE_CATEGORY_PREFIXES]}
            or policy['assessment_policy'] != ASSESSMENTS
            or policy['budget'] != asdict(SelectionBudget())
            or policy['build'] != payload['build']
            or policy['panel_declaration_hash'] != declaration['declaration_hash']
            or policy['panel_available_at'] != panel_ack['durable_ack']
            or policy['frame_root'] != payload['frame_root']
            or policy['implementation_commit'] != payload['frame_implementation_commit']
            or _json_bytes(policy['sampling_protocol']) != _json_bytes(payload['sampling_recipe'])
            or policy['panel_protocol'] != payload['protocol']
            or policy.get('computation_storage_profile')
                != payload.get('computation_storage_profile')
            or not _ordered_clocks(panel_ack['durable_ack'], policy['declared_at'],
                                   ack['durable_ack'])):
        raise ValueError('selection declaration/recipe/assessment/chronology differs')
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
    from datetime import timedelta

    protocol = PairingPanelProtocol(**policy['panel_protocol'])
    start, end, available = (original[k] for k in
                             ('interval_start', 'interval_end', 'frame_available_at'))
    if not _ordered_clocks(start, end, available, point):
        raise ValueError('frame interval/availability is future or unordered')
    if _time(end) - _time(start) > timedelta(seconds=protocol.max_frame_interval_seconds):
        raise ValueError('frame interval exceeds frozen selection limit')
    if _time(point) - _time(start) > timedelta(seconds=protocol.max_frame_age_seconds):
        raise ValueError('frame stale under frozen selection limit')


def frame_freshness(policy, original, point):
    """Dispatch: pairing protocols here, every legacy protocol to the frozen function."""
    from .pairing_declaration import is_pairing_protocol
    from .panel_selection import freshness as legacy

    if is_pairing_protocol(policy['panel_protocol']):
        return freshness(policy, original, point)
    return legacy(policy, original, point)


def bound_plan(policy, members, cutoff, original_hash, inventory_hash, facts):
    from .selection import _protocol

    if (policy['schema_version'] != VERSION or policy['assessment_policy'] != ASSESSMENTS
            or policy['population_policy'] != LIQUIDITY_POPULATION):
        raise ValueError('explicit pairing population and no-assessment policy required')
    design = pairing.design_from_dict(policy['pairing_design'])
    if not isinstance(facts, dict) or set(facts) != {m.market_id for m in members}:
        raise ValueError('pairing facts must cover every sampling member')
    # Temporal then liquidity rule exactly as D118 (zero-inclusion records, never imputed).
    members = [replace(m, eligible=False, exclusion_reason=TEMPORAL_REASON)
               if m.eligible and m.close_stratum == 'past' else m for m in members]
    members = _liquidity_scope(policy, members)
    excluded = set(design.exclude_categories)
    scoped = []
    for m in members:
        category = facts[m.market_id]['fee_category']
        m = replace(m, category=pairing.STRATUM_CATEGORY_PREFIX + category)
        if m.eligible and category in excluded:
            m = replace(m, eligible=False, exclusion_reason=pairing.CATEGORY_POLICY_EXCLUDED)
        scoped.append(m)
    groups = pairing.dependence_groups(facts, underlying=design.underlying_grouping)
    plan = plan_sample(
        _protocol(policy), scoped, cutoff=_time(cutoff), frame_scope=SCOPE,
        frame_status='enumerated_complete', frame_evidence_ids=[original_hash, inventory_hash],
        max_frame_members=policy['budget']['rows'], pairing=design, dependence_groups=groups)
    counts = Counter(a['arm'] for a in plan['assignments'])
    if set(counts) - {'screened'} or counts['screened'] > design.screened_slots:
        raise ValueError('sample exceeds screened slot ceiling; never truncate')
    plan.pop('plan_hash')
    plan.update(
        schema_version=PLAN_VERSION, collection_enabled=False, accepted_panel=False,
        population_policy=policy['population_policy'],
        category_policy=policy['category_policy'],
        population_reference_at=policy['declared_at'],
        selection_eligible_member_count=sum(m.eligible for m in scoped),
        liquidity_floor=LIQUIDITY_FLOOR, liquidity_source=LIQUIDITY_SOURCE,
        grouping_policy=policy['grouping_policy'], fee_category_map=policy['fee_category_map'],
        population_exclusion_counts=dict(sorted(
            Counter(m.exclusion_reason for m in scoped if not m.eligible).items())),
        eligible_category_counts=dict(sorted(
            Counter(m.category for m in scoped if m.eligible).items())),
    )
    return {**plan, 'plan_hash': content_hash(plan)}


def status(original):
    return {'provenance_class': original['provenance_class'],
            'state': 'fresh_selection_sealed', 'collection_enabled': False,
            'accepted_panel': False, 'feature_store_admitted': False}


def create_pairing_selection(panel_root, *, repository=None):
    """One fresh attempt per pairing declaration; no caller seed/clock/assessment override."""
    from .selection import _canonical, _create_selection

    panel = _canonical(panel_root)
    read_pairing_declaration(panel)
    payload, _ = _pair(panel, 'panel_policy')
    return _create_selection(
        payload['frame_root'], implementation_commit=payload['frame_implementation_commit'],
        output_root=selection_root(panel), repository=repository, panel_root=panel)
