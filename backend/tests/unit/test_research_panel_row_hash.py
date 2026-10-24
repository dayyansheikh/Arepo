"""Raw-boundary hashing equivalence; synthetic cases are not prospective evidence."""

import json

import pytest

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _strict_json
from astrolabe.feature_store.types import canonical_json
from astrolabe.research_panel.frame import parse_page
from tests.unit.test_research_panel_frame import market


@pytest.mark.parametrize('raw_row', [
    'null', 'false', '17', '1.00', '-0.0', '1e-400', '1e400',
    '"λ\\n\\\""', '[1.00,{"$decimal":"1.0"},true,null]',
    '{"z":1.00,"a":-0.000,"nested":{"é":[1e-25,123456789012345678901234567890]}}',
    '{"$utc":"2026-10-09T00:00:00Z","$decimal":"1.000"}',
    json.dumps(market(description='Rule é', events=[{'id': '12'}])),
    json.dumps(market()).replace(
        '"active": true', '"amount": 1.00000000000000000001, "active": true'),
])
def test_exact_hash_matches_generic_contract_for_every_strict_input(raw_row):
    raw = ('{"markets":[' + raw_row + ']}').encode()
    decoded = _strict_json(raw)['markets'][0]
    result = parse_page(raw, 2)['rows'][0]
    assert result['row_hash'] == content_hash(decoded)
    assert result['source_index'] == 0
    if not isinstance(decoded, dict) or 'id' not in decoded:
        assert not result['eligible']
        assert 'market_id_unavailable' in result['exclusion_reasons']


@pytest.mark.parametrize('row', [
    '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
    '{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', '{1:"bad"}',
])
def test_strict_parser_still_rejects_ambiguous_or_nonfinite_raw_input(row):
    with pytest.raises(ValueError):
        parse_page(('{"markets":[' + row + ']}').encode(), 2)


def test_generic_hash_still_rejects_arbitrary_python_float_and_nonstring_key():
    for value in [{'x': 0.25}, {1: 'bad'}, [float('inf')]]:
        with pytest.raises(ValueError):
            canonical_json(value)


def test_decimal_spelling_and_literal_tag_semantics_are_unchanged():
    def digest(row):
        return parse_page(('{"markets":[' + row + ']}').encode(), 2)['rows'][0]['row_hash']
    assert digest('1.00') != digest('1.0')
    assert digest('-0.0') != digest('0.0')
    # Canonical JSON has historically represented native decimals with this literal tag.
    assert digest('1.00') == digest('{"$decimal":"1.00"}')


def test_oversized_decimal_still_rejected_by_canonical_contract():
    raw = ('{"markets":[0.' + '1' * 4097 + ']}').encode()
    with pytest.raises(ValueError, match='oversized'):
        parse_page(raw, 2)
