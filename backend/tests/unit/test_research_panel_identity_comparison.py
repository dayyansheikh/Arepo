"""Asymmetric endpoint shapes must not erase changes to economic identity."""

from copy import deepcopy

import pytest

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.source_parsers import gamma_identity
from astrolabe.research_panel.identity_comparison import compare_mapping
from tests.unit.test_research_panel_frame import market


def pair():
    row = market(1, description='Frozen rules', events=[{'id': '42'}])
    targeted = {k: v for k, v in row.items() if k != 'events'}
    return gamma_identity(row), gamma_identity(targeted)


def test_endpoint_omission_proves_only_core_equality_without_mutating_identities():
    frame, current = pair()
    before = deepcopy((frame, current))
    result = compare_mapping(frame, current['mapping_version'])
    assert result['state'] == 'core_equal_event_membership_unavailable'
    assert result['core_identity_equal']
    assert result['current_event_membership'] == 'unavailable'
    assert result['economic_group_status'] == 'unresolved'
    assert result['admission_decision'] is False
    assert 'source_event_ids' not in result
    assert before == (frame, current)


def test_exact_hash_and_missing_mapping_distinguish_evidence():
    frame, current = pair()
    exact = compare_mapping(frame, frame['mapping_version'])
    assert exact['current_event_membership'] == 'reported_equal'
    empty = compare_mapping(current, current['mapping_version'])
    assert empty['current_event_membership'] == 'unavailable'
    assert compare_mapping(frame, None)['state'] == 'mapping_unavailable'


@pytest.mark.parametrize('field,value', [
    ('market_id', '2'), ('condition_id', '0x' + 'a' * 64), ('question_id', '0x' + 'b' * 64),
    ('question', 'Different question'), ('rules_text', 'Changed rules'), ('rules_hash', 'f' * 64),
    ('resolution_source', 'Changed source'), ('source_event_ids', ['99']),
    ('chain_id', '137'), ('token_contract', 'changed'), ('collateral_address', 'changed'),
    ('identity_status', 'changed'), ('economic_group_status', 'changed'), ('venue', 'other'),
    ('outcomes', [{'token_id': '7', 'outcome_index': 0, 'outcome_label': 'Changed'}]),
])
def test_no_other_field_change_is_accepted(field, value):
    frame, current = pair()
    current[field] = value
    digest = content_hash({k: v for k, v in current.items() if k != 'mapping_version'})
    result = compare_mapping(frame, digest)
    assert not result['core_identity_equal'] and result['state'] == 'mapping_differs'


@pytest.mark.parametrize('change', ['order', 'label', 'token'])
def test_ordered_outcome_identity_remains_exact(change):
    frame, current = pair()
    if change == 'order':
        current['outcomes'].reverse()
    else:
        current['outcomes'][0]['outcome_label' if change == 'label' else 'token_id'] = '3'
    digest = content_hash({k: v for k, v in current.items() if k != 'mapping_version'})
    assert not compare_mapping(frame, digest)['core_identity_equal']


@pytest.mark.parametrize('change', ['hash', 'missing', 'extra', 'events'])
def test_incomplete_or_corrupt_frame_refused(change):
    frame, current = pair()
    if change == 'hash':
        frame['rules_text'] = 'Changed'
    elif change == 'missing':
        del frame['question_id']
    elif change == 'extra':
        frame['future_field'] = 'unknown'
    else:
        frame['source_event_ids'] = None
    with pytest.raises(ValueError):
        compare_mapping(frame, current['mapping_version'])


@pytest.mark.parametrize('value', ['', 1, True, 'not-a-hash'])
def test_arbitrary_mapping_rejected(value):
    with pytest.raises(ValueError):
        compare_mapping(pair()[0], value)
