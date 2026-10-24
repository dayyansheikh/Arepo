"""Codec equivalence/corruption fixtures; no claim of full archive equivalence."""

import pytest

from astrolabe.feature_store.admission import AdmissionError, prepare
from astrolabe.feature_store.migrations import upgrade
from astrolabe.feature_store.preservation import decode_records, encode_records
from astrolabe.feature_store.repository import append_batch
from astrolabe.feature_store.types import canonical_json
from tests.unit.test_feature_store_causality import graph
from tests.unit.test_feature_store_repository import AT


async def test_lossless_graph_export_and_restore_to_fresh_store(tmp_path):
    rows, feature, _ = graph()
    records = [
        (entity, prepare(entity, payload))
        for entity, payload in [*rows, ("feature_value", feature)]
    ]
    data, inventory = encode_records(records)
    assert inventory["verification_state"] == "local_codec_only"
    restored = decode_records(data, inventory)
    assert canonical_json(records) == canonical_json(restored)
    url = f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_restore.sqlite'}"
    await upgrade(url)
    stored = await append_batch(url, restored, fixture_clock=AT)
    assert canonical_json([row for _, row in records]) == canonical_json(stored)
    assert (
        stored[-1]["raw_value_decimal"].as_tuple()
        == restored[-1][1]["raw_value_decimal"].as_tuple()
    )


def test_corruption_and_inventory_changes_are_detected():
    rows, feature, _ = graph()
    data, inventory = encode_records([*rows, ("feature_value", feature)])
    with pytest.raises(AdmissionError, match="integrity"):
        decode_records(data.replace(b"0.50000000000000001", b"0.50000000000000002"), inventory)
    with pytest.raises(AdmissionError, match="inventory"):
        decode_records(data, {**inventory, "row_count": 999})
    with pytest.raises(AdmissionError, match="integrity"):
        decode_records(data, {**inventory, "field_contract_hash": "0" * 64})
    with pytest.raises(AdmissionError, match="duplicate"):
        encode_records([rows[0], rows[0]])
