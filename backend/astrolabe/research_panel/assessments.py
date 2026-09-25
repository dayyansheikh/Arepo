"""Pure declared trigger evidence checks; runtime journal verification remains required."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.types import HASH_PATTERN, utc_datetime


def _hash(value):
    if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
        raise ValueError('content-addressed assessment/policy evidence required')


@dataclass(frozen=True)
class TriggerAssessmentPolicy:
    trigger_policy_hash: str
    declared_at: datetime
    max_window_age_seconds: int
    max_assessment_age_seconds: int
    version: str = 'fs2-trigger-assessment-policy-v1'

    def __post_init__(self):
        _hash(self.trigger_policy_hash)
        utc_datetime(self.declared_at)
        for value in (self.max_window_age_seconds, self.max_assessment_age_seconds):
            if type(value) is not int or not 0 <= value <= 604800:
                raise ValueError('explicit bounded assessment freshness required')
        if self.version != 'fs2-trigger-assessment-policy-v1':
            raise ValueError('unknown assessment policy')

    @property
    def hash(self):
        return content_hash(asdict(self))


@dataclass(frozen=True)
class TriggerAssessment:
    market_id: str
    token_id: str
    policy_hash: str
    evidence_id: str
    state: str
    input_window_start: datetime
    input_window_end: datetime
    available_at: datetime
    unavailable_reason: str | None = None


def assessment_inventory(policy, assessments, members, cutoff):
    """Validate declarations and retain unknowns; never verify caller hashes as actual facts.

    A later durable consumer must bind each evidence ID to its source/read/computation
    closure. The current result is only a deterministic sampling design.
    """
    if type(policy) is not TriggerAssessmentPolicy:
        raise ValueError('explicit trigger assessment policy required')
    cutoff, declared = utc_datetime(cutoff), utc_datetime(policy.declared_at)
    if declared > cutoff:
        raise ValueError('assessment policy declared after cutoff')
    by_market = {m.market_id: m for m in members}
    # Members are bounded/unique by the caller; never exhaust an unbounded iterator.
    records = list(islice(assessments, len(members) + 1))
    if len(records) > len(members):
        raise ValueError('bounded one-assessment-per-market inventory required')
    supplied, evidence = {}, set()
    for row in records:
        if type(row) is not TriggerAssessment:
            raise ValueError('explicit trigger assessment record required')
        if not isinstance(row.market_id, str) or row.market_id not in by_market:
            raise ValueError('assessment market absent from frame')
        if row.market_id in supplied:
            raise ValueError('duplicate market assessment')
        if row.token_id != by_market[row.market_id].token_id:
            raise ValueError('assessment token differs from frame')
        _hash(row.evidence_id)
        _hash(row.policy_hash)
        if row.evidence_id in evidence:
            raise ValueError('assessment evidence cannot identify multiple market decisions')
        if row.policy_hash != policy.trigger_policy_hash:
            raise ValueError('assessment trigger policy differs')
        if (not isinstance(row.state, str)
                or row.state not in {'triggered', 'untriggered', 'unavailable'}):
            raise ValueError('explicit three-state assessment required')
        if row.state == 'unavailable':
            if (not isinstance(row.unavailable_reason, str)
                    or not row.unavailable_reason.strip() or len(row.unavailable_reason) > 256):
                raise ValueError('unavailable assessment requires bounded reason')
        elif row.unavailable_reason is not None:
            raise ValueError('observed assessment cannot carry unavailable reason')
        start, end, available = map(utc_datetime, (
            row.input_window_start, row.input_window_end, row.available_at,
        ))
        if not declared <= start <= end <= available <= cutoff:
            raise ValueError('assessment policy/window/availability chronology differs')
        reasons = []
        if cutoff - end > timedelta(seconds=policy.max_window_age_seconds):
            reasons.append('input_window_stale')
        if cutoff - available > timedelta(seconds=policy.max_assessment_age_seconds):
            reasons.append('assessment_stale')
        if row.state == 'unavailable':
            reasons.append(row.unavailable_reason)
        state = 'unavailable' if reasons else row.state
        supplied[row.market_id] = {
            'market_id': row.market_id, 'token_id': row.token_id,
            'assessment': asdict(row), 'effective_state': state, 'reasons': reasons,
        }
        evidence.add(row.evidence_id)
    return [supplied.get(m.market_id, {
        'market_id': m.market_id, 'token_id': m.token_id, 'assessment': None,
        'effective_state': 'not_assessed', 'reasons': ['not_assessed'],
    }) for m in sorted(members, key=lambda m: m.market_id)]
