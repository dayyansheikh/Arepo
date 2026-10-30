"""Exact stratified sampling plans, never a collector or evidence of actual origins."""

import hashlib
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from heapq import nsmallest
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.types import HASH_PATTERN, canonical_json, exact_decimal, utc_datetime

from .assessments import assessment_inventory


@dataclass(frozen=True)
class SamplingProtocol:
    seed: str
    scheduled_per_stratum: int
    triggered_per_stratum: int
    controls_per_trigger: int
    max_unique_markets: int
    probability_edges: tuple[str, ...] = ("0.1", "0.5", "0.9")
    liquidity_edges: tuple[str, ...] = ("1000", "10000", "100000")
    version: str = "fs2-panel-sampling-v1"

    def __post_init__(self):
        if not isinstance(self.seed, str) or not HASH_PATTERN.fullmatch(self.seed):
            raise ValueError("sampling seed must be a predeclared SHA256-sized random seed")
        for value in (self.scheduled_per_stratum, self.triggered_per_stratum,
                      self.controls_per_trigger, self.max_unique_markets):
            if type(value) is not int or not 1 <= value <= 10000:
                raise ValueError("positive bounded sampling counts required")
        for edges, bounded in ((self.probability_edges, True), (self.liquidity_edges, False)):
            if not isinstance(edges, tuple) or len(edges) > 20:
                raise ValueError("immutable bounded stratum edges required")
            values = [exact_decimal(v) for v in edges]
            if values != sorted(set(values)) or any(v <= 0 for v in values):
                raise ValueError("strictly increasing positive edges required")
            if bounded and any(v >= 1 for v in values):
                raise ValueError("probability edges must lie inside (0,1)")
        if self.version != "fs2-panel-sampling-v1":
            raise ValueError("unknown sampling protocol")

    @property
    def hash(self):
        return content_hash(asdict(self))


@dataclass(frozen=True)
class FrameMember:
    market_id: str
    token_id: str
    source_observation_id: str
    available_at: datetime
    time_stratum: str
    category: str
    close_stratum: str
    probability: str | None
    liquidity: str | None
    event_group: str | None
    group_available_at: datetime | None
    eligible: bool
    exclusion_reason: str | None
    triggered: bool
    trigger_id: str | None
    trigger_available_at: datetime | None


def exact_probability(numerator, denominator):
    """Finite decimal only when exact; manifest rational always remains authoritative."""
    if (type(numerator) is not int or type(denominator) is not int
            or not 0 <= numerator <= denominator or not 1 <= denominator <= 400000):
        raise ValueError("valid nonnegative inclusion count/frequency required")
    return _probability_fraction(Fraction(numerator, denominator))


def _probability_fraction(value):
    # Stage products can exceed the single-frame denominator ceiling without rounding.
    remainder = value.denominator
    for factor in (2, 5):
        while remainder % factor == 0:
            remainder //= factor
    text = None
    if remainder == 1:
        with localcontext() as context:
            context.prec = len(str(value.numerator)) + len(str(value.denominator)) * 4 + 4
            text = str(Decimal(value.numerator) / Decimal(value.denominator))
    return {"numerator": str(value.numerator), "denominator": str(value.denominator),
            "decimal": text, "decimal_state": "exact" if text is not None else "nonterminating"}


def _validate_member(row, cutoff):
    from astrolabe.feature_store.types import uint_text

    for value in (row.market_id, row.time_stratum, row.category, row.close_stratum):
        if not isinstance(value, str) or not value:
            raise ValueError("explicit frame identity and strata required")
    uint_text(row.token_id, bits=256)
    if (not isinstance(row.source_observation_id, str)
            or not HASH_PATTERN.fullmatch(row.source_observation_id)):
        raise ValueError("source observation lineage required")
    if utc_datetime(row.available_at) > cutoff:
        raise ValueError("frame member uses future source information")
    if row.event_group is None:
        if row.group_available_at is not None:
            raise ValueError("unknown group cannot carry inferred availability")
    elif (not isinstance(row.event_group, str) or not row.event_group
          or row.group_available_at is None
          or utc_datetime(row.group_available_at) > cutoff):
        raise ValueError("group must be known by sampling cutoff")
    if type(row.eligible) is not bool or type(row.triggered) is not bool:
        raise ValueError("eligibility/trigger state must be explicit booleans")
    if ((row.eligible and row.exclusion_reason is not None)
            or (not row.eligible and (not isinstance(row.exclusion_reason, str)
                                     or not row.exclusion_reason))):
        raise ValueError("excluded member requires reason; eligible member cannot have one")
    if row.triggered:
        if (not row.trigger_id or row.trigger_available_at is None
                or utc_datetime(row.trigger_available_at) > cutoff):
            raise ValueError("trigger evidence must predate sampling cutoff")
    elif row.trigger_id is not None or row.trigger_available_at is not None:
        raise ValueError("untriggered member cannot carry a trigger")
    for value, probability in ((row.probability, True), (row.liquidity, False)):
        if value is not None:
            number = exact_decimal(value)
            if number < 0 or (probability and number > 1):
                raise ValueError("invalid stratum numerical value")


def _band(value, edges):
    if value is None:
        return "unknown"
    number = exact_decimal(value)
    return str(sum(number >= exact_decimal(edge) for edge in edges))


def _frame_hash(members):
    # Exactly the canonical list encoding, without duplicating every dataclass/dict/string.
    digest = hashlib.sha256(b"[")
    for index, row in enumerate(sorted(members, key=lambda r: r.market_id)):
        if index:
            digest.update(b",")
        digest.update(canonical_json(asdict(row)).encode())
    digest.update(b"]")
    return digest.hexdigest()


def plan_sample(protocol, members, *, cutoff, frame_scope, frame_status, frame_evidence_ids,
                max_frame_members=100000, assessment_policy=None, trigger_assessments=None,
                strata_limit=None, pairing=None, dependence_groups=None,
                screened_assignments=None):
    """Each arm has its own conditional inclusion probability, not a union weight.

    The caller must durably freeze this output before capture; this pure planner cannot
    attest that happened. Unknown event groups are a stratum, never independent events.

    ``pairing`` (a ``pairing.PairingDesign``) selects the separate D120 screen-then-activate
    planner (plans v5/v6, ``_plan_pairing``); without it this function is unchanged.
    """
    if pairing is not None or dependence_groups is not None or screened_assignments is not None:
        if strata_limit is not None:
            raise ValueError('pairing design has its own stratum draw')
        return _plan_pairing(protocol, members, cutoff=cutoff, frame_scope=frame_scope,
                             frame_status=frame_status, frame_evidence_ids=frame_evidence_ids,
                             max_frame_members=max_frame_members,
                             assessment_policy=assessment_policy,
                             trigger_assessments=trigger_assessments, design=pairing,
                             groups=dependence_groups, screened=screened_assignments)
    cutoff = utc_datetime(cutoff)
    if type(max_frame_members) is not int or not 1 <= max_frame_members <= 400000:
        raise ValueError("finite frame capacity up to 400000 required")
    members = list(islice(members, max_frame_members + 1))
    if not 1 <= len(members) <= max_frame_members:
        raise ValueError("nonempty bounded frame required")
    if frame_status not in {"enumerated_complete", "source_partial", "explicit_list"}:
        raise ValueError("explicit frame completeness required")
    if not isinstance(frame_scope, str) or not frame_scope:
        raise ValueError("population scope required")
    if (not frame_evidence_ids or len(set(frame_evidence_ids)) != len(frame_evidence_ids)
            or any(not HASH_PATTERN.fullmatch(v) for v in frame_evidence_ids)):
        raise ValueError("frame completion/coverage evidence required")
    if len({r.market_id for r in members}) != len(members):
        raise ValueError("one predeclared outcome per market; duplicate market inflates sampling")
    assessed_mode = assessment_policy is not None or trigger_assessments is not None
    assessed = {}
    if assessed_mode:
        if assessment_policy is None or trigger_assessments is None:
            raise ValueError('both assessment policy and explicit inventory required')
        if any(r.triggered is not False or r.trigger_id is not None
               or r.trigger_available_at is not None for r in members):
            raise ValueError('assessment mode requires neutral legacy trigger fields')
        inventory = assessment_inventory(assessment_policy, trigger_assessments, members, cutoff)
        assessed = {r['market_id']: r for r in inventory}
    if strata_limit is not None:
        if type(strata_limit) is not int or not 1 <= strata_limit <= 256:
            raise ValueError('bounded stratum limit from 1 to 256 required')
        if (frame_status != 'enumerated_complete' or not assessed_mode
                or any(r['assessment'] is not None for r in inventory)):
            raise ValueError('bounded stratum draw requires complete unassessed frame')
    triggers = [r.trigger_id for r in members if r.triggered]
    if len(set(triggers)) != len(triggers):
        raise ValueError("trigger IDs must identify one market decision, not duplicate events")
    strata, excluded = {}, []
    for row in sorted(members, key=lambda r: r.market_id):
        _validate_member(row, cutoff)
        if not row.eligible:
            excluded.append({"market_id": row.market_id, "reason": row.exclusion_reason})
            continue
        fields = {"time": row.time_stratum, "category": row.category,
                  "time_to_close": row.close_stratum,
                  "probability_band": _band(row.probability, protocol.probability_edges),
                  "liquidity_band": _band(row.liquidity, protocol.liquidity_edges),
                  "event_group": row.event_group}
        key = content_hash(fields)
        strata.setdefault(key, {"fields": fields, "members": []})["members"].append(row)
    assignments, reports = [], []
    drawn_strata = set(strata)
    stage_probability = None
    if strata_limit is not None:
        drawn_strata = set(nsmallest(strata_limit, strata, key=lambda key: (
            content_hash({'seed': protocol.seed, 'stratum': key,
                          'arm': 'screening_stratum_v1'}), key)))
        if strata:
            stage_probability = exact_probability(len(drawn_strata), len(strata))

    def trigger_id(row):
        return (assessed[row.market_id]['assessment']['evidence_id']
                if assessed_mode else row.trigger_id)

    def state(row):
        return (assessed[row.market_id]['effective_state'] if assessed_mode
                else 'triggered' if row.triggered else 'untriggered')

    def select(rows, count, stratum, arm):
        return nsmallest(count, rows, key=lambda r: (
            content_hash({"seed": protocol.seed, "stratum": stratum,
                          "arm": arm, "market": r.market_id}), r.market_id,
        ))

    def add(row, arm, stratum, count, population, matched=(), matching_probability=None):
        assignments.append({"market_id": row.market_id, "token_id": row.token_id,
                            "source_observation_id": row.source_observation_id,
                            "arm": arm, "stratum": stratum,
                            "inclusion_probability": exact_probability(count, population),
                            "probability_scope": "market within arm/stratum, frozen trigger states",
                            "trigger_id": trigger_id(row) if arm == "triggered" else None,
                            "matched_trigger_ids": list(matched),
                            "conditional_matching_probability": matching_probability})
        if assessed_mode:
            record = assessed[row.market_id]
            assignments[-1].update(
                assessment_state=record['effective_state'],
                assessment_evidence_id=(record['assessment']['evidence_id']
                                        if record['assessment'] is not None else None),
            )
        if strata_limit is not None:
            assignments[-1].update(
                stratum_inclusion_probability=stage_probability,
                conditional_market_inclusion_probability=exact_probability(count, population),
                inclusion_probability=_probability_fraction(
                    Fraction(len(drawn_strata), len(strata)) * Fraction(count, population)),
                probability_scope='market in complete eligible frame; stratum then market draw',
            )

    for key, stratum in sorted(strata.items()):
        rows = stratum["members"]
        scheduled_n = min(protocol.scheduled_per_stratum, len(rows)) if key in drawn_strata else 0
        for row in select(rows, scheduled_n, key, "scheduled"):
            add(row, "scheduled", key, scheduled_n, len(rows))
        triggered_pool = [r for r in rows if state(r) == 'triggered']
        control_pool = [r for r in rows if state(r) == 'untriggered']
        triggered = select(triggered_pool, protocol.triggered_per_stratum, key, "triggered")
        wanted = len(triggered) * protocol.controls_per_trigger
        controls = select(control_pool, wanted, key, "control")
        for row in triggered:
            add(row, "triggered", key, len(triggered), len(triggered_pool))
        for index, row in enumerate(controls):
            trigger_index = index % len(triggered)
            slots = (len(controls) + len(triggered) - 1 - trigger_index) // len(triggered)
            add(row, "control", key, len(controls), len(control_pool),
                (trigger_id(triggered[trigger_index]),),
                exact_probability(slots, len(control_pool)))
        reports.append({"stratum": key, **stratum["fields"], "eligible_count": len(rows),
                        "scheduled_count": scheduled_n, "triggered_pool": len(triggered_pool),
                        "triggered_count": len(triggered), "control_pool": len(control_pool),
                        "controls_wanted": wanted, "controls_selected": len(controls),
                        "unfilled_control_slots": wanted - len(controls),
                        "economic_independence": "unresolved" if stratum["fields"]["event_group"]
                        is None else "grouped_not_independent_rows"})
        if assessed_mode:
            reports[-1]['assessment_counts'] = {
                name: sum(state(r) == name for r in rows)
                for name in ('triggered', 'untriggered', 'unavailable', 'not_assessed')
            }
        if strata_limit is not None:
            reports[-1].update(
                sampling_state='sampled' if key in drawn_strata else 'stratum_not_sampled',
                stratum_inclusion_probability=stage_probability,
                conditional_market_inclusion_probability=exact_probability(
                    min(protocol.scheduled_per_stratum, len(rows)), len(rows)),
                market_inclusion_probability=_probability_fraction(
                    Fraction(len(drawn_strata), len(strata))
                    * Fraction(min(protocol.scheduled_per_stratum, len(rows)), len(rows))),
            )
    unique = len({a["market_id"] for a in assignments})
    if unique > protocol.max_unique_markets:
        raise ValueError(
            "sample exceeds predeclared budget; change future protocol, never truncate"
        )
    result = {
        "schema_version": "fs2-sampling-plan-v1", "protocol_hash": protocol.hash,
        "protocol": asdict(protocol), "cutoff": cutoff.isoformat(),
        "frame_scope": frame_scope, "frame_status": frame_status,
        "frame_evidence_ids": sorted(frame_evidence_ids),
        "frame_hash": _frame_hash(members),
        "frame_size": len(members), "unique_selected_markets": unique,
        "assignments": sorted(assignments, key=lambda a: (a["market_id"], a["arm"])),
        "strata": reports, "exclusions": excluded,
        "runtime_frame_verification_required": True,
        "population_inference_eligible": False,
        "role_count_is_not_independent_sample_size": True,
        "scientific_stage": "measurement_development_only",
    }
    if max_frame_members != 100000:
        # Changed capacity is explicit in the output contract; the v1 default stays identical.
        result.update(schema_version="fs2-sampling-plan-v2", max_frame_members=max_frame_members)
    if assessed_mode:
        result.update(
            schema_version='fs2-sampling-plan-v3', max_frame_members=max_frame_members,
            assessment_policy=asdict(assessment_policy),
            assessment_policy_hash=assessment_policy.hash,
            assessment_inventory=inventory,
            runtime_assessment_verification_required=True, origin_admitted=False,
        )
    if strata_limit is not None:
        result.update(
            schema_version='fs2-sampling-plan-v4',
            stratum_draw={'version': 'fs2-bounded-stratum-draw-v1',
                          'strata_limit': strata_limit, 'eligible_strata': len(strata),
                          'selected_strata': len(drawn_strata),
                          'stratum_inclusion_probability': stage_probability,
                          'ranking_domain': 'screening_stratum_v1',
                          'design': 'uniform_without_replacement_then_within_stratum'},
        )
    return {**result, "plan_hash": content_hash(result)}


PAIRING_SCREEN_SCHEMA = 'fs2-sampling-plan-v5'
PAIRING_ROLE_SCHEMA = 'fs2-sampling-plan-v6'


def _stratum_fields(row, protocol):
    return {"time": row.time_stratum, "category": row.category,
            "time_to_close": row.close_stratum,
            "probability_band": _band(row.probability, protocol.probability_edges),
            "liquidity_band": _band(row.liquidity, protocol.liquidity_edges)}


def _plan_pairing(protocol, members, *, cutoff, frame_scope, frame_status, frame_evidence_ids,
                  max_frame_members, assessment_policy, trigger_assessments, design, groups,
                  screened):
    """D120 screen-then-activate planner; the dependence group is an attribute, not a stratum.

    First stage (no assessments; complete frame): ``pairing.screen_draw`` over strata keyed by
    time/category/time-to-close/probability/liquidity only. Second stage (assessments of the
    screened list): ``pairing.role_draw`` within the first-stage strata; scheduled arm 0.
    """
    from . import pairing as pairing_rules

    cutoff = utc_datetime(cutoff)
    if type(design) is not pairing_rules.PairingDesign:
        raise ValueError('explicit pairing design required')
    if type(max_frame_members) is not int or not 1 <= max_frame_members <= 400000:
        raise ValueError("finite frame capacity up to 400000 required")
    members = list(islice(members, max_frame_members + 1))
    if not 1 <= len(members) <= max_frame_members:
        raise ValueError("nonempty bounded frame required")
    if not isinstance(frame_scope, str) or not frame_scope:
        raise ValueError("population scope required")
    if (not frame_evidence_ids or len(set(frame_evidence_ids)) != len(frame_evidence_ids)
            or any(not HASH_PATTERN.fullmatch(v) for v in frame_evidence_ids)):
        raise ValueError("frame completion/coverage evidence required")
    if len({r.market_id for r in members}) != len(members):
        raise ValueError("one predeclared outcome per market; duplicate market inflates sampling")
    if any(r.event_group is not None or r.group_available_at is not None or r.triggered
           or r.trigger_id is not None or r.trigger_available_at is not None for r in members):
        raise ValueError('pairing keeps groups as attributes and legacy trigger fields neutral')
    for row in members:
        _validate_member(row, cutoff)
    role_stage = assessment_policy is not None or trigger_assessments is not None
    if role_stage:
        return _plan_pairing_roles(protocol, members, cutoff, frame_scope, frame_status,
                                   frame_evidence_ids, max_frame_members, assessment_policy,
                                   trigger_assessments, design, screened, pairing_rules)
    if frame_status != 'enumerated_complete' or screened is not None:
        raise ValueError('pairing screen draw requires the complete enumerated frame')
    if not isinstance(groups, dict):
        raise ValueError('explicit dependence groups required')
    strata, excluded, fields = {}, [], {}
    for row in sorted(members, key=lambda r: r.market_id):
        if not row.eligible:
            excluded.append({"market_id": row.market_id, "reason": row.exclusion_reason})
            continue
        group = groups.get(row.market_id)
        if not isinstance(group, str) or not group:
            raise ValueError('every eligible member requires a dependence group')
        value = _stratum_fields(row, protocol)
        key = content_hash(value)
        fields[key] = value
        strata.setdefault(key, {"fields": value, "groups": {}})["groups"].setdefault(
            group, []).append(row.market_id)
    draw = pairing_rules.screen_draw(protocol.seed, strata, design)
    by_market = {r.market_id: r for r in members}
    assignments = []
    for pick in draw['screened']:
        row = by_market[pick['market_id']]
        assignments.append({
            "market_id": row.market_id, "token_id": row.token_id,
            "source_observation_id": row.source_observation_id, "arm": "screened",
            **{k: pick[k] for k in pick if k != 'market_id'},
            "fee_category": fields[pick['stratum']]['category'],
            "probability_scope": ("market in complete eligible frame; uniform stratum draw then "
                                  "seeded group order with a shared claim set; conditional on "
                                  "earlier strata claims"),
            "unconditional_inclusion_probability": None,
            "unconditional_probability_reason": ("depends on the claims of strata processed "
                                                 "earlier; conditional factors are exact"),
            "trigger_id": None, "matched_trigger_ids": [], "activated": False})
    drawable, drawn = set(draw['drawable_strata']), {k: i for i, k in
                                                     enumerate(draw['drawn_strata'])}
    picked = Counter(p['stratum'] for p in draw['screened'])
    reports = []
    for key, stratum in sorted(strata.items()):
        reports.append({
            "stratum": key, **stratum["fields"],
            "eligible_count": sum(len(v) for v in stratum["groups"].values()),
            "dependence_groups": len(stratum["groups"]),
            "drawable": key in drawable,
            "sampling_state": ('sampled' if key in drawn else 'stratum_not_sampled'
                               if key in drawable else 'stratum_not_drawable_lt_min_groups'),
            "stratum_order": drawn.get(key),
            "stratum_inclusion_probability": (draw['stratum_inclusion_probability']
                                              if key in drawable else
                                              exact_probability(0, 1)),
            "screened_count": picked.get(key, 0), "scheduled_count": 0,
            "economic_independence": "group_disjoint_screening_not_independent"})
    unique = len(assignments)
    if unique > protocol.max_unique_markets or unique > design.screened_slots:
        raise ValueError("sample exceeds predeclared budget; change future protocol, never "
                         "truncate")
    result = {
        "schema_version": PAIRING_SCREEN_SCHEMA, "protocol_hash": protocol.hash,
        "protocol": asdict(protocol), "pairing_design": design.as_dict(),
        "cutoff": cutoff.isoformat(), "frame_scope": frame_scope, "frame_status": frame_status,
        "frame_evidence_ids": sorted(frame_evidence_ids), "frame_hash": _frame_hash(members),
        "frame_size": len(members), "max_frame_members": max_frame_members,
        "dependence_groups_hash": content_hash(dict(sorted(groups.items()))),
        "eligible_dependence_groups": len({g for s in strata.values() for g in s["groups"]}),
        "unique_selected_markets": unique,
        "assignments": sorted(assignments, key=lambda a: a["market_id"]),
        "strata": reports, "exclusions": excluded,
        "stratum_draw": {'version': 'fs2-pairing-stratum-draw-v1',
                         'strata': design.strata, 'eligible_strata': len(strata),
                         'drawable_strata': len(drawable),
                         'min_groups_per_stratum': design.min_groups_per_stratum,
                         'selected_strata': len(drawn),
                         'stratum_inclusion_probability': draw['stratum_inclusion_probability'],
                         'drawn_order': draw['drawn_strata'],
                         'ranking_domains': ['pairing_stratum_v1', 'pairing_group_v1',
                                             'pairing_member_v1'],
                         'design': 'uniform drawable strata, then seeded group order with a '
                                   'shared claim set, one member per group'},
        "runtime_frame_verification_required": True, "population_inference_eligible": False,
        "role_count_is_not_independent_sample_size": True,
        "scientific_stage": "measurement_development_only", "origin_admitted": False,
    }
    return {**result, "plan_hash": content_hash(result)}


def _plan_pairing_roles(protocol, members, cutoff, frame_scope, frame_status, frame_evidence_ids,
                        max_frame_members, assessment_policy, trigger_assessments, design,
                        screened, pairing_rules):
    if frame_status != 'explicit_list' or not isinstance(screened, dict):
        raise ValueError('pairing role draw requires the explicit screened list')
    if assessment_policy is None or trigger_assessments is None:
        raise ValueError('both assessment policy and explicit inventory required')
    if set(screened) != {r.market_id for r in members}:
        raise ValueError('screened first-stage assignments must cover the screened list')
    inventory = assessment_inventory(assessment_policy, trigger_assessments, members, cutoff)
    states = {}
    for record in inventory:
        evidence = (record['assessment']['evidence_id'] if record['assessment'] is not None
                    else None)
        states[record['market_id']] = {'state': record['effective_state'],
                                       'evidence_id': evidence}
    rows = [{'market_id': m, 'stratum': a['stratum'], 'stratum_order': a['stratum_order'],
             'dependence_group': a['dependence_group']} for m, a in sorted(screened.items())]
    if len({r['dependence_group'] for r in rows}) != len(rows):
        raise ValueError('screened members must be dependence-group disjoint')
    draw = pairing_rules.role_draw(protocol.seed, rows, states, design)
    by_market = {r.market_id: r for r in members}
    assignments = []
    for role in draw['assignments']:
        row, first = by_market[role['market_id']], screened[role['market_id']]
        record = states[role['market_id']]
        assignments.append({
            "market_id": row.market_id, "token_id": row.token_id,
            "source_observation_id": row.source_observation_id, "arm": role['arm'],
            "stratum": role['stratum'], "dependence_group": first['dependence_group'],
            "fee_category": first['fee_category'],
            "inclusion_probability": role['conditional_role_probability'],
            "probability_scope": "role within screened stratum, conditional on screened states",
            "trigger_id": role['trigger_id'], "matched_trigger_ids": role['matched_trigger_ids'],
            "conditional_matching_probability": role['conditional_matching_probability'],
            "assessment_state": record['state'], "assessment_evidence_id": record['evidence_id'],
            "screening_inclusion_probability": first['inclusion_probability'],
            "screening_conditional_inclusion_probability":
                first['conditional_market_inclusion_probability'],
            "activated": True})
    unique = len({a['market_id'] for a in assignments})
    if unique > design.origin_slots or unique > protocol.max_unique_markets:
        raise ValueError("activation exceeds predeclared origin slots; never truncate")
    strata = []
    for report in draw['strata']:
        strata.append({**report, 'control_pool': report['untriggered_pool'],
                       'triggered_count': report['pairs_drawn'],
                       'controls_selected': report['pairs_drawn'],
                       'controls_wanted': report['pairs_drawn'],
                       'unfilled_control_slots': 0})
    result = {
        "schema_version": PAIRING_ROLE_SCHEMA, "protocol_hash": protocol.hash,
        "protocol": asdict(protocol), "pairing_design": design.as_dict(),
        "cutoff": cutoff.isoformat(), "frame_scope": frame_scope, "frame_status": frame_status,
        "frame_evidence_ids": sorted(frame_evidence_ids), "frame_hash": _frame_hash(members),
        "frame_size": len(members), "max_frame_members": max_frame_members,
        "unique_selected_markets": unique,
        "assignments": sorted(assignments, key=lambda a: (a["market_id"], a["arm"])),
        "strata": strata, "exclusions": [],
        "triggers_in_scope": draw['triggers_in_scope'], "pairs_drawn": draw['pairs_drawn'],
        "fill": draw['fill'], "strata_with_trigger": draw['strata_with_trigger'],
        "control_scarcity_strata": draw['control_scarcity_strata'],
        "assessment_policy": asdict(assessment_policy),
        "assessment_policy_hash": assessment_policy.hash, "assessment_inventory": inventory,
        "screened_assignments": [dict(screened[m], market_id=m) for m in sorted(screened)],
        "roles_fixed_at_screening": True, "activate_screened": False,
        "runtime_assessment_verification_required": True, "origin_admitted": False,
        "population_inference_eligible": False,
        "role_count_is_not_independent_sample_size": True,
        "scientific_stage": "measurement_development_only",
    }
    return {**result, "plan_hash": content_hash(result)}
