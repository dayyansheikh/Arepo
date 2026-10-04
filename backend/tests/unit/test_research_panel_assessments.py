"""Pure assessment-aware sampling invariants; fixtures are not prospective evidence."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from itertools import repeat

import pytest

from astrolabe.research_panel.assessments import TriggerAssessment, TriggerAssessmentPolicy
from astrolabe.research_panel.sampling import (
    FrameMember,
    SamplingProtocol,
    exact_probability,
    plan_sample,
)

AT = datetime(2026, 9, 22, 8, tzinfo=UTC)
POLICY = TriggerAssessmentPolicy('b' * 64, AT - timedelta(minutes=5), 60, 10)


def member(i):
    return FrameMember(str(i), str(i), f'{i:064x}', AT - timedelta(minutes=6),
                       'scheduled', 'unknown', 'unknown', None, None, None, None,
                       True, None, False, None, None)


def assessment(i, state='untriggered', **changes):
    return replace(TriggerAssessment(
        str(i), str(i), POLICY.trigger_policy_hash, f'{i + 100:064x}', state,
        AT - timedelta(seconds=90), AT - timedelta(seconds=60), AT - timedelta(seconds=10),
        'source_gap' if state == 'unavailable' else None,
    ), **changes)


def plan(rows, assessments, policy=POLICY, **changes):
    kwargs = dict(cutoff=AT, frame_scope='synthetic development', frame_status='explicit_list',
                  frame_evidence_ids=['a' * 64], assessment_policy=policy,
                  trigger_assessments=assessments)
    kwargs.update(changes)
    return plan_sample(SamplingProtocol('c' * 64, 10, 2, 2, 100), rows, **kwargs)


def arm(result, name):
    return [r for r in result['assignments'] if r['arm'] == name]


def test_unavailable_and_unassessed_remain_scheduled_but_never_controls():
    rows = [member(i) for i in range(1, 6)]
    facts = [assessment(1, 'triggered'), assessment(2), assessment(3, 'unavailable')]
    result = plan(rows, facts)
    assert result == plan(reversed(rows), reversed(facts))
    assert len(arm(result, 'scheduled')) == 5
    assert [r['market_id'] for r in arm(result, 'control')] == ['2']
    assert result['strata'][0]['unfilled_control_slots'] == 1
    assert result['strata'][0]['assessment_counts'] == {
        'triggered': 1, 'untriggered': 1, 'unavailable': 1, 'not_assessed': 2,
    }
    assert len(result['assessment_inventory']) == 5
    assert result['assessment_inventory'][3]['assessment'] is None
    assert result['origin_admitted'] is False
    assert result['runtime_assessment_verification_required'] is True
    assert result['population_inference_eligible'] is False


def test_freshness_edges_are_inclusive_and_stale_states_are_retained():
    facts = [assessment(1, 'triggered'), assessment(2),
             assessment(3, input_window_end=AT - timedelta(seconds=60, microseconds=1)),
             assessment(4, available_at=AT - timedelta(seconds=10, microseconds=1)),
             assessment(5, 'triggered', available_at=AT - timedelta(seconds=11))]
    result = plan([member(i) for i in range(1, 6)], facts)
    assert [r['market_id'] for r in arm(result, 'control')] == ['2']
    assert [r['market_id'] for r in arm(result, 'triggered')] == ['1']
    records = result['assessment_inventory']
    assert records[2]['reasons'] == ['input_window_stale']
    assert records[3]['reasons'] == ['assessment_stale']
    assert records[4]['assessment']['state'] == 'triggered'
    assert records[4]['effective_state'] == 'unavailable'


def test_exact_probabilities_use_only_the_assessed_control_pool():
    facts = [assessment(1, 'triggered'), assessment(2, 'triggered'),
             *[assessment(i) for i in range(3, 8)]]
    result = plan([member(i) for i in range(1, 10)], facts)
    assert len(arm(result, 'scheduled')) == 9
    for row in arm(result, 'control'):
        assert row['inclusion_probability'] == exact_probability(4, 5)
        assert row['conditional_matching_probability'] == exact_probability(2, 5)
        assert row['assessment_state'] == 'untriggered'
        assert row['matched_trigger_ids'][0] in {f'{101:064x}', f'{102:064x}'}


@pytest.mark.parametrize('changes', [
    {'market_id': 'absent'}, {'token_id': '999'}, {'policy_hash': 'd' * 64},
    {'evidence_id': 'bad'}, {'state': False}, {'state': 'not_assessed'},
    {'available_at': AT + timedelta(microseconds=1)},
    {'input_window_end': AT},
    {'input_window_start': AT - timedelta(minutes=6)},
    {'input_window_start': AT}, {'available_at': AT.replace(tzinfo=None)},
    {'unavailable_reason': 'not-valid-for-observed'},
])
def test_conflicting_future_or_invalid_assessments_refuse_plan(changes):
    with pytest.raises(ValueError):
        plan([member(1)], [assessment(1, **changes)])


@pytest.mark.parametrize('reason', [None, '', ' ', 'x' * 257, True])
def test_unavailable_requires_explicit_bounded_reason(reason):
    with pytest.raises(ValueError, match='bounded reason'):
        plan([member(1)], [assessment(1, 'unavailable', unavailable_reason=reason)])


def test_duplicate_assessments_evidence_and_unknown_markets_refused():
    rows = [member(1), member(2)]
    with pytest.raises(ValueError, match='duplicate market'):
        plan(rows, [assessment(1), assessment(1)])
    with pytest.raises(ValueError, match='multiple market decisions'):
        plan(rows, [assessment(1), assessment(2, evidence_id=f'{101:064x}')])
    with pytest.raises(ValueError, match='bounded one-assessment'):
        plan(rows, repeat(assessment(1)))


def test_no_assessments_means_scheduled_only_and_no_hidden_control_claim():
    result = plan([member(1), member(2)], [])
    assert len(arm(result, 'scheduled')) == 2
    assert arm(result, 'control') == arm(result, 'triggered') == []
    assert result['strata'][0]['control_pool'] == 0
    assert result['strata'][0]['assessment_counts']['not_assessed'] == 2
    assert result['schema_version'] == 'fs2-sampling-plan-v3'


def test_excluded_members_keep_assessments_but_do_not_enter_any_arm():
    rows = [member(1), replace(member(2), eligible=False, exclusion_reason='invalid_identity')]
    result = plan(rows, [assessment(1, 'triggered'), assessment(2)])
    assert len(result['assessment_inventory']) == 2
    assert arm(result, 'control') == []
    assert result['strata'][0]['unfilled_control_slots'] == 2
    assert result['exclusions'] == [{'market_id': '2', 'reason': 'invalid_identity'}]


def test_assessment_mode_has_one_authority_and_requires_explicit_policy_and_inventory():
    with pytest.raises(ValueError, match='neutral legacy'):
        plan([replace(member(1), triggered=True, trigger_id='t', trigger_available_at=AT)], [])
    with pytest.raises(ValueError, match='both assessment'):
        plan([member(1)], None)
    with pytest.raises(ValueError, match='both assessment'):
        plan([member(1)], [], policy=None)
    with pytest.raises(ValueError, match='after cutoff'):
        plan([member(1)], [], policy=replace(POLICY, declared_at=AT + timedelta(seconds=1)))


@pytest.mark.parametrize('changes', [
    {'max_window_age_seconds': True}, {'max_assessment_age_seconds': -1},
    {'max_window_age_seconds': 604801}, {'trigger_policy_hash': 'invalid'},
    {'version': 'unknown'}, {'declared_at': AT.replace(tzinfo=None)},
])
def test_policy_bounds_are_explicit(changes):
    with pytest.raises(ValueError):
        replace(POLICY, **changes)


def test_plan_hash_binds_actual_assessment_evidence_and_freshness_policy():
    rows, facts = [member(1)], [assessment(1)]
    original = plan(rows, facts)
    changed = plan(rows, [replace(facts[0], evidence_id='e' * 64)])
    assert original['plan_hash'] != changed['plan_hash']
    changed = plan(rows, facts, policy=replace(POLICY, max_window_age_seconds=61))
    assert original['plan_hash'] != changed['plan_hash']


def test_assessment_times_have_canonical_utc_hashes():
    zone = timezone(timedelta(hours=1))
    fact = assessment(1)
    shifted = replace(fact, input_window_start=fact.input_window_start.astimezone(zone),
                      input_window_end=fact.input_window_end.astimezone(zone),
                      available_at=fact.available_at.astimezone(zone))
    assert plan([member(1)], [fact])['plan_hash'] == plan([member(1)], [shifted])['plan_hash']


def test_assessed_mode_never_truncates_a_selected_sample():
    with pytest.raises(ValueError, match='never truncate'):
        plan_sample(SamplingProtocol('c' * 64, 2, 1, 1, 1), [member(1), member(2)],
                    cutoff=AT, frame_scope='fixture', frame_status='explicit_list',
                    frame_evidence_ids=['a' * 64], assessment_policy=POLICY,
                    trigger_assessments=[])
