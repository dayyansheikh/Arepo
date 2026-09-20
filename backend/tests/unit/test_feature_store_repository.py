"""Adversarial synthetic evidence tests; none of these fixtures are research results."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from astrolabe.feature_store.admission import (
    CONTRACT,
    ENUMS,
    MISSING,
    AdmissionError,
    content_hash,
    prepare,
    typed_number,
    typed_vector,
)
from astrolabe.feature_store.migrations import local_engine, upgrade
from astrolabe.feature_store.models import MODEL_BY_ENTITY
from astrolabe.feature_store.repository import PayloadConflict, append_batch
from astrolabe.feature_store.schema import FIELD_SPECS

AT = datetime(2026, 9, 20, 10, tzinfo=UTC)


def record(entity, **values):
    row = {key: None for key, spec in FIELD_SPECS[entity].items() if spec["nullable"] == "true"}
    row.update(recorded_at=AT, schema_version=CONTRACT, provenance_class="synthetic")
    row.update(values)
    row["missing_fields"] = {key: "not_applicable" for key, value in row.items() if value is None}
    return row


def registry(**overrides):
    fields = dict(
        source_id="fixture:book",
        registry_version="a" * 64,
        access_state="documented_only",
        clock_semantics={"event": "not supplied"},
        endpoint="https://example.invalid/book",
        parser_version="fixture-v1",
        rights_evidence={"use": "synthetic fixture"},
        rights_state="permitted",
        schema_hash="b" * 64,
        unit_conventions={"size": "shares", "price": "collateral/share"},
    )
    fields.update(overrides)
    return record("source_registry", **fields)


def manifest(**overrides):
    payload = {
        "schema_version": "fs2-manifest-v1",
        "roots": [],
        "closure": [],
        "empty_reason": "synthetic no-input control",
    }
    fields = dict(
        available_at=AT,
        manifest_kind="sampling",
        payload=payload,
        content_hash=content_hash(payload),
    )
    fields.update(overrides)
    return record("artifact_manifest", **fields)


@pytest.fixture
async def url(tmp_path):
    value = f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_writer.sqlite'}"
    await upgrade(value)
    return value


def test_every_enum_has_an_explicit_closed_vocabulary():
    for entity, fields in FIELD_SPECS.items():
        for field, spec in fields.items():
            if spec["type"] == "ENUM" and field not in {
                "provenance_class",
                "missing_reason",
                "missingness_reason",
            }:
                assert (entity, field) in ENUMS


@pytest.mark.parametrize(
    "change",
    [
        {"registry_version": "not-a-hash"},
        {"access_state": "probably_verified"},
        {"recorded_at": datetime(2026, 9, 20)},
        {"unit_conventions": {"size": 0.1}},
        {"missing_fields": {}},
        {"schema_version": "invented"},
        {"id": "c" * 64},
    ],
)
def test_invalid_evidence_is_not_repaired(change):
    payload = registry()
    payload.update(change)
    with pytest.raises(ValueError):
        prepare("source_registry", payload)


@pytest.mark.parametrize("reason", sorted(MISSING - {"observed"}))
def test_all_missingness_reasons_survive_without_imputation(reason):
    payload = registry()
    payload["missing_fields"]["protocol_version"] = reason
    saved = prepare("source_registry", payload)
    assert saved["protocol_version"] is None
    assert saved["missing_fields"]["protocol_version"] == reason


def test_typed_numbers_and_vectors_preserve_schema_and_exact_bits():
    assert typed_number({"kind": "float64", "value": (0.1).hex()})["value"] == (0.1).hex()
    vector = {
        "schema_version": "fixture-v1",
        "dtype": "decimal",
        "shape": [2],
        "axis": ["outcome"],
        "values": ["0.000", "1.000"],
        "units": "probability",
        "model_version": "fixture",
    }
    assert typed_vector(vector) == vector
    for bad in (
        {**vector, "shape": [3]},
        {**vector, "values": ["NaN", "1"]},
        {**vector, "values": [0.1, 0.9]},
        {**vector, "axis": []},
    ):
        with pytest.raises(ValueError):
            typed_vector(bad)
    for raw in ("nan", "inf", "0.1", "0x1.0p+1024"):
        with pytest.raises((ValueError, OverflowError)):
            typed_number({"kind": "float64", "value": raw})


async def test_idempotent_retry_and_conflicting_content(url):
    first = await append_batch(url, [("source_registry", registry())], fixture_clock=AT)
    retry = await append_batch(url, [("source_registry", registry())], fixture_clock=AT)
    assert first == retry
    with pytest.raises(PayloadConflict):
        await append_batch(
            url,
            [("source_registry", registry(endpoint="https://example.invalid/changed"))],
            fixture_clock=AT,
        )


async def test_conflicting_batch_rolls_back_other_records(url):
    original = registry()
    altered = registry(endpoint="https://example.invalid/other")
    with pytest.raises(PayloadConflict):
        await append_batch(
            url,
            [
                ("artifact_manifest", manifest()),
                ("source_registry", original),
                ("source_registry", altered),
            ],
            fixture_clock=AT,
        )
    engine = local_engine(url)
    try:
        async with engine.connect() as conn:
            count = await conn.scalar(
                select(func.count()).select_from(MODEL_BY_ENTITY["artifact_manifest"])
            )
            assert count == 0
    finally:
        await engine.dispose()


async def test_manifest_requires_exact_transitive_inventory(url):
    source = prepare("source_registry", registry())
    root = {"entity": "source_registry", "id": source["id"]}
    payload = {"schema_version": "fs2-manifest-v1", "roots": [root], "closure": []}
    bad = manifest(payload=payload, content_hash=content_hash(payload))
    with pytest.raises(AdmissionError, match="closure"):
        await append_batch(
            url, [("source_registry", registry()), ("artifact_manifest", bad)], fixture_clock=AT
        )
    payload["closure"] = [root]
    good = manifest(payload=payload, content_hash=content_hash(payload))
    await append_batch(
        url, [("source_registry", registry()), ("artifact_manifest", good)], fixture_clock=AT
    )
    payload["roots"][0]["id"] = "d" * 64
    broken = manifest(payload=payload, content_hash=content_hash(payload))
    with pytest.raises(AdmissionError, match="missing"):
        await append_batch(url, [("artifact_manifest", broken)], fixture_clock=AT)


async def test_revision_must_preserve_subject_and_advance_knowledge(url):
    first = (await append_batch(url, [("source_registry", registry())], fixture_clock=AT))[0]
    revision = registry(registry_version="c" * 64, supersedes_id=first["id"])
    with pytest.raises(AdmissionError, match="advance"):
        await append_batch(url, [("source_registry", revision)], fixture_clock=AT)
    revision["recorded_at"] = AT + timedelta(seconds=1)
    await append_batch(url, [("source_registry", revision)], fixture_clock=AT)
    unrelated = registry(
        source_id="another",
        registry_version="d" * 64,
        supersedes_id=first["id"],
        recorded_at=AT + timedelta(seconds=2),
    )
    with pytest.raises(AdmissionError, match="subject"):
        await append_batch(url, [("source_registry", unrelated)], fixture_clock=AT)


async def test_cyclic_revision_batch_is_rejected(url):
    first = registry()
    second = registry(registry_version="c" * 64)
    first_id = prepare("source_registry", first)["id"]
    second_id = prepare("source_registry", second)["id"]
    first["supersedes_id"] = second_id
    first["missing_fields"].pop("supersedes_id")
    second["supersedes_id"] = first_id
    second["missing_fields"].pop("supersedes_id")
    with pytest.raises(AdmissionError, match="cyclic"):
        await append_batch(
            url, [("source_registry", first), ("source_registry", second)], fixture_clock=AT
        )


async def test_two_concurrent_identical_writers_keep_one_row(url):
    results = await asyncio.gather(
        *[append_batch(url, [("source_registry", registry())], fixture_clock=AT) for _ in range(2)]
    )
    assert results[0] == results[1]
    engine = local_engine(url)
    try:
        async with engine.connect() as conn:
            assert (
                await conn.scalar(
                    select(func.count()).select_from(MODEL_BY_ENTITY["source_registry"])
                )
                == 1
            )
    finally:
        await engine.dispose()


async def test_fixture_clock_cannot_backdate_prospective_records(url):
    with pytest.raises(AdmissionError, match="synthetic"):
        await append_batch(
            url, [("source_registry", registry(provenance_class="prospective"))], fixture_clock=AT
        )
    with pytest.raises(AdmissionError, match="owned by the writer"):
        await append_batch(url, [("source_registry", registry())])


async def test_real_writer_stamps_clock_and_retry_reuses_persisted_clock(url):
    payload = registry(provenance_class="reconstructed")
    payload.pop("recorded_at")
    before = datetime.now(UTC)
    row = (await append_batch(url, [("source_registry", payload)]))[0]
    assert before <= row["recorded_at"] <= datetime.now(UTC)
    again = (await append_batch(url, [("source_registry", payload)]))[0]
    assert again == row


async def test_concurrent_real_writer_clocks_do_not_create_false_payload_conflicts(url):
    payload = registry(provenance_class="reconstructed")
    payload.pop("recorded_at")
    results = await asyncio.gather(
        *[append_batch(url, [("source_registry", payload)]) for _ in range(2)]
    )
    assert results[0] == results[1]


async def test_generic_writer_cannot_assert_prospective_clock_evidence(url):
    payload = registry(provenance_class="prospective")
    payload.pop("recorded_at")
    with pytest.raises(AdmissionError, match="durable receipt"):
        await append_batch(url, [("source_registry", payload)])


def test_zero_is_distinct_from_missing():
    from astrolabe.feature_store.admission import normalise_value

    spec = {"type": "DECIMAL_TEXT", "nullable": "true"}
    assert (
        normalise_value("feature_value", "denominator", "0.000", spec).as_tuple()
        == Decimal("0.000").as_tuple()
    )
    assert normalise_value("feature_value", "denominator", None, spec) is None


def test_probability_sum_cannot_hide_a_small_positive_component():
    from astrolabe.feature_store.admission import normalise_value

    spec = {"type": "DECIMAL_VECTOR", "nullable": "true"}
    with pytest.raises(AdmissionError, match="sum exactly"):
        normalise_value("prediction", "class_probabilities", ["1", "1e-1000"], spec)


async def test_deep_dependency_chain_does_not_hit_python_recursion_limit(monkeypatch):
    from astrolabe.feature_store import repository

    cache = {}
    for number in range(1500):
        key = f"{number:064x}"
        cache[("source_registry", key)] = {
            "id": key,
            "links": ([("source_registry", f"{number + 1:064x}")] if number < 1499 else []),
        }
    monkeypatch.setattr(repository, "direct_references", lambda entity, row: row["links"])
    root = cache[("source_registry", "0" * 64)]
    assert len(await repository._closure(None, "source_registry", root, cache)) == 1499
    cache[("source_registry", f"{1499:064x}")]["links"] = [("source_registry", "0" * 64)]
    with pytest.raises(AdmissionError, match="cyclic"):
        await repository._closure(None, "source_registry", root, cache)


async def test_shared_dependency_diamonds_are_not_expanded_per_path(monkeypatch):
    from collections import Counter

    from astrolabe.feature_store import repository

    cache = {}
    for number in range(60):
        key = f"{number:064x}"
        cache[("source_registry", key)] = {
            "id": key,
            "links": [
                ("source_registry", f"{child:064x}")
                for child in (number + 1, number + 2)
                if child < 60
            ],
        }
    visits = Counter()

    def references(entity, row):
        visits[row["id"]] += 1
        return row["links"]

    monkeypatch.setattr(repository, "direct_references", references)
    await repository._closure(None, "source_registry", cache[("source_registry", "0" * 64)], cache)
    assert len(visits) == 60 and max(visits.values()) == 1
