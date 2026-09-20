"""Exact stratified sampling plans, never a collector or evidence of actual origins."""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.types import HASH_PATTERN, exact_decimal, utc_datetime


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
            or not 0 <= numerator <= denominator or not 1 <= denominator <= 100000):
        raise ValueError("valid nonnegative inclusion count/frequency required")
    value = Fraction(numerator, denominator)
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


def plan_sample(protocol, members, *, cutoff, frame_scope, frame_status, frame_evidence_ids):
    """Each arm has its own conditional inclusion probability, not a union weight.

    The caller must durably freeze this output before capture; this pure planner cannot
    attest that happened. Unknown event groups are a stratum, never independent events.
    """
    cutoff = utc_datetime(cutoff)
    members = list(islice(members, 100001))
    if not 1 <= len(members) <= 100000:
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

    def select(rows, count, stratum, arm):
        return sorted(rows, key=lambda r: (
            content_hash({"seed": protocol.seed, "stratum": stratum,
                          "arm": arm, "market": r.market_id}), r.market_id,
        ))[:count]

    def add(row, arm, stratum, count, population, matched=(), matching_probability=None):
        assignments.append({"market_id": row.market_id, "token_id": row.token_id,
                            "source_observation_id": row.source_observation_id,
                            "arm": arm, "stratum": stratum,
                            "inclusion_probability": exact_probability(count, population),
                            "probability_scope": "market within arm/stratum, frozen trigger states",
                            "trigger_id": row.trigger_id if arm == "triggered" else None,
                            "matched_trigger_ids": list(matched),
                            "conditional_matching_probability": matching_probability})

    for key, stratum in sorted(strata.items()):
        rows = stratum["members"]
        scheduled_n = min(protocol.scheduled_per_stratum, len(rows))
        for row in select(rows, scheduled_n, key, "scheduled"):
            add(row, "scheduled", key, scheduled_n, len(rows))
        triggered_pool = [r for r in rows if r.triggered]
        control_pool = [r for r in rows if not r.triggered]
        triggered = select(triggered_pool, protocol.triggered_per_stratum, key, "triggered")
        wanted = len(triggered) * protocol.controls_per_trigger
        controls = select(control_pool, wanted, key, "control")
        for row in triggered:
            add(row, "triggered", key, len(triggered), len(triggered_pool))
        for index, row in enumerate(controls):
            trigger_index = index % len(triggered)
            slots = (len(controls) + len(triggered) - 1 - trigger_index) // len(triggered)
            add(row, "control", key, len(controls), len(control_pool),
                (triggered[trigger_index].trigger_id,), exact_probability(slots, len(control_pool)))
        reports.append({"stratum": key, **stratum["fields"], "eligible_count": len(rows),
                        "scheduled_count": scheduled_n, "triggered_pool": len(triggered_pool),
                        "triggered_count": len(triggered), "control_pool": len(control_pool),
                        "controls_wanted": wanted, "controls_selected": len(controls),
                        "unfilled_control_slots": wanted - len(controls),
                        "economic_independence": "unresolved" if stratum["fields"]["event_group"]
                        is None else "grouped_not_independent_rows"})
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
        "frame_hash": content_hash([asdict(r) for r in sorted(members, key=lambda r: r.market_id)]),
        "frame_size": len(members), "unique_selected_markets": unique,
        "assignments": sorted(assignments, key=lambda a: (a["market_id"], a["arm"])),
        "strata": reports, "exclusions": excluded,
        "runtime_frame_verification_required": True,
        "population_inference_eligible": False,
        "role_count_is_not_independent_sample_size": True,
        "scientific_stage": "measurement_development_only",
    }
    return {**result, "plan_hash": content_hash(result)}
