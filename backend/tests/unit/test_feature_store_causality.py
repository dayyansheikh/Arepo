"""A complete small synthetic decision graph, including late outcomes and revisions."""

import hashlib
from datetime import timedelta

import pytest

from astrolabe.feature_store.admission import AdmissionError, content_hash, prepare
from astrolabe.feature_store.migrations import upgrade
from astrolabe.feature_store.repository import append_batch
from tests.unit.test_feature_store_repository import (  # noqa: F401
    AT,
    manifest,
    record,
    registry,
)


@pytest.fixture
async def url(tmp_path):
    value = f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_causality.sqlite'}"
    await upgrade(value)
    return value


def source(registry_id, *, ordinal=0, at=AT):
    raw = '{"timestamp":"1789898400.123456789","price":"0.50000000000000001"}'
    return record(
        "source_observation",
        recorded_at=at,
        available_to_model_at=at,
        ingested_at=at,
        parsed_at=at,
        first_received_at=at,
        source_id="fixture:book",
        source_registry_id=registry_id,
        request_id="fixture-request",
        receipt_ordinal=ordinal,
        parser_version="fixture-v1",
        missing_reason="observed",
        payload_encoding="utf8",
        raw_payload_inline=raw,
        payload_hash=hashlib.sha256(raw.encode()).hexdigest(),
        native_clock_details={"precision": "ns"},
        quality_assessment_state="checked",
        quality_flags=[],
        availability_evidence_ids=[],
        request_metadata={"coverage": "single synthetic response"},
        raw_timestamp="1789898400.123456789",
        timestamp_unit="seconds",
    )


def graph():
    rows = []

    def add(entity, payload):
        row = prepare(entity, payload)
        rows.append((entity, payload))
        return row["id"]

    source_id = add("source_registry", registry())
    observation = add("source_observation", source(source_id))
    market = add(
        "market_identity_version",
        record(
            "market_identity_version",
            venue="fixture",
            market_id="m1",
            mapping_version="c" * 64,
            mapping_evidence_ids=[observation],
            observed_from_at=AT,
            lifecycle_state="open",
            question="Synthetic event",
            rules_text="Synthetic rule",
            rules_hash="d" * 64,
        ),
    )
    token = add(
        "token_outcome_version",
        record(
            "token_outcome_version",
            market_identity_id=market,
            mapping_version="e" * 64,
            token_id=str(2**256 - 1),
            outcome_index=0,
            outcome_label="yes",
            mapping_evidence_ids=[observation],
            observed_from_at=AT,
        ),
    )
    sampling = add("artifact_manifest", manifest())
    grouping = add("artifact_manifest", manifest(manifest_kind="group"))
    origin_at = AT + timedelta(seconds=10)
    origin = add(
        "research_origin",
        record(
            "research_origin",
            recorded_at=origin_at,
            prediction_origin_at=origin_at,
            feature_cutoff_at=origin_at,
            origin_recorded_at=origin_at,
            origin_kind="synthetic",
            market_identity_id=market,
            token_outcome_id=token,
            sampling_manifest_id=sampling,
            group_manifest_id=grouping,
            event_group_version="fixture-group-v1",
            sampling_arm="control",
            eligibility_version="fixture-v1",
            eligibility_reason="admitted synthetic control",
            eligibility_snapshot={"admitted": True},
            selection_probability="1",
        ),
    )
    definition = add(
        "feature_definition",
        record(
            "feature_definition",
            feature_id="fixture.price",
            feature_version="f" * 64,
            formula="Identity of exact parsed synthetic price",
            units="collateral/share",
            status="locked",
            raw_dependencies={"price": "source_observation"},
            missingness_policy={"zero": "observed"},
            transformation_specification={"kind": "none"},
            window_specification={"seconds": "1", "closure": "right"},
        ),
    )
    feature = record(
        "feature_value",
        recorded_at=origin_at,
        origin_id=origin,
        feature_definition_id=definition,
        feature_id="fixture.price",
        feature_version="f" * 64,
        units="collateral/share",
        available_to_model_at=AT + timedelta(seconds=9),
        computed_at=AT + timedelta(seconds=9),
        input_observation_ids=[observation],
        missingness_reason="observed",
        quality_flags=[],
        raw_value_decimal="0.50000000000000001",
        raw_value_text="0.50000000000000001",
        transform_version="none",
        window_start_at=AT,
        window_end_at=AT + timedelta(seconds=8),
    )
    return rows, feature, source_id


async def test_causal_graph_keeps_raw_precision_and_fine_timestamp(url):  # noqa: F811
    rows, feature, _ = graph()
    got = await append_batch(url, [*rows, ("feature_value", feature)], fixture_clock=AT)
    assert str(got[-1]["raw_value_decimal"]) == "0.50000000000000001"
    assert got[1]["raw_timestamp"] == "1789898400.123456789"


@pytest.mark.parametrize(
    "mutation,match",
    [
        (
            {
                "computed_at": AT + timedelta(seconds=11),
                "available_to_model_at": AT + timedelta(seconds=11),
            },
            "late feature",
        ),
        ({"window_end_at": AT + timedelta(seconds=12)}, "window_end_at"),
        ({"feature_version": "wrong"}, "subject"),
        ({"units": "USD"}, "subject"),
        ({"missingness_reason": "stale"}, "missingness"),
        ({"denominator": "0"}, "zero-denominator"),
    ],
)
async def test_feature_causal_and_numerical_contract(url, mutation, match):  # noqa: F811
    rows, feature, _ = graph()
    feature.update(mutation)
    feature["missing_fields"] = {k: "not_applicable" for k, v in feature.items() if v is None}
    with pytest.raises(AdmissionError, match=match):
        await append_batch(url, [*rows, ("feature_value", feature)], fixture_clock=AT)


async def test_later_metadata_cannot_enter_origin(url):  # noqa: F811
    rows, _, _ = graph()
    rows[2][1]["observed_from_at"] = AT + timedelta(seconds=11)
    # The mapping key changes with knowledge time; update FK so this tests causality.
    market_id = prepare(*rows[2])["id"]
    rows[3][1]["market_identity_id"] = market_id
    token_id = prepare(*rows[3])["id"]
    rows[6][1]["market_identity_id"] = market_id
    rows[6][1]["token_outcome_id"] = token_id
    with pytest.raises(AdmissionError, match="availability|cutoff"):
        await append_batch(url, rows, fixture_clock=AT)


async def test_outcome_and_revised_label_keep_separate_availability(url):  # noqa: F811
    rows, _, source_id = graph()
    origin_id = prepare(*rows[6])["id"]
    target = record(
        "target_definition",
        target_version="1" * 64,
        horizon_seconds=60,
        target_family="T1",
        quote_rule={"clock": "receipt"},
        label_rule={"flat": "0"},
        metric_contract={"primary": "fixture"},
        units="collateral/share",
    )
    target_id = prepare("target_definition", target)["id"]
    observed = AT + timedelta(seconds=71)
    raw = source(source_id, ordinal=1, at=observed)
    raw_id = prepare("source_observation", raw)["id"]
    outcome = record(
        "outcome_observation",
        recorded_at=observed,
        source_observation_id=raw_id,
        origin_id=origin_id,
        target_definition_id=target_id,
        target_at=AT + timedelta(seconds=70),
        label_observed_at=observed,
        first_received_at=observed,
        available_to_model_at=observed,
        close_state="open",
        resolution_state="unresolved",
        observation_status="observed",
        missingness_reason="observed",
        midpoint="0.55",
        units={"price": "collateral/share"},
    )
    outcome_id = prepare("outcome_observation", outcome)["id"]
    label = record(
        "label_version",
        recorded_at=observed,
        origin_id=origin_id,
        target_definition_id=target_id,
        target_at=outcome["target_at"],
        outcome_observation_ids=[outcome_id],
        label_computation_version="2" * 64,
        status="evaluated",
        label_observed_at=observed,
        label_available_at=observed,
        label_value={"schema_version": "fixture", "direction": "up"},
        actual_delay_seconds="1",
    )
    base = [
        *rows,
        ("target_definition", target),
        ("source_observation", raw),
        ("outcome_observation", outcome),
    ]
    for field in ("first_received_at", "available_to_model_at", "label_observed_at"):
        changed = {**outcome, field: observed - timedelta(seconds=1)}
        with pytest.raises(AdmissionError, match="receipt|availability|clock evidence"):
            await append_batch(
                url, [*base[:-1], ("outcome_observation", changed)], fixture_clock=AT
            )
    late = {**label, "label_available_at": observed - timedelta(seconds=1)}
    with pytest.raises(AdmissionError, match="label_observed_at|precedes"):
        await append_batch(url, [*base, ("label_version", late)], fixture_clock=AT)
    first = (await append_batch(url, [*base, ("label_version", label)], fixture_clock=AT))[-1]
    training_payload = {
        "schema_version": "fs2-manifest-v1",
        "roots": [{"entity": "label_version", "id": first["id"]}],
        "closure": [
            {"entity": entity, "id": prepare(entity, value)["id"]}
            for entity, value in base
            if entity != "feature_definition"
        ]
        + [{"entity": "label_version", "id": first["id"]}],
        "as_of_cutoff_at": (observed - timedelta(seconds=1)).isoformat(),
    }
    training = manifest(
        manifest_kind="training",
        payload=training_payload,
        content_hash=content_hash(training_payload),
        available_at=observed,
        recorded_at=observed,
    )
    with pytest.raises(AdmissionError, match="training cutoff"):
        await append_batch(url, [("artifact_manifest", training)], fixture_clock=AT)
    training_payload["as_of_cutoff_at"] = observed.isoformat()
    training = manifest(
        manifest_kind="training",
        payload=training_payload,
        content_hash=content_hash(training_payload),
        available_at=observed,
        recorded_at=observed,
    )
    await append_batch(url, [("artifact_manifest", training)], fixture_clock=AT)
    revision = {
        **label,
        "label_computation_version": "3" * 64,
        "supersedes_label_id": first["id"],
        "revision_reason": "synthetic correction",
        "recorded_at": observed + timedelta(seconds=1),
        "label_available_at": observed + timedelta(seconds=1),
    }
    revision["missing_fields"] = {k: "not_applicable" for k, v in revision.items() if v is None}
    second = (await append_batch(url, [("label_version", revision)], fixture_clock=AT))[-1]
    assert second["id"] != first["id"]
    assert second["label_available_at"] > first["label_available_at"]


def prediction_graph():
    rows, feature, _ = graph()
    origin_id = prepare(*rows[6])["id"]
    rows.append(("feature_value", feature))
    feature_id = prepare("feature_value", feature)["id"]
    inventory = [{"entity": entity, "id": prepare(entity, row)["id"]} for entity, row in rows]
    feature_payload = {
        "schema_version": "fs2-manifest-v1",
        "roots": [{"entity": "feature_value", "id": feature_id}],
        "closure": inventory,
    }
    features = manifest(
        manifest_kind="feature",
        payload=feature_payload,
        content_hash=content_hash(feature_payload),
        available_at=AT + timedelta(seconds=10),
        recorded_at=AT + timedelta(seconds=10),
    )
    training = manifest(manifest_kind="training")
    candidate = manifest(manifest_kind="model")
    protocol = manifest(manifest_kind="protocol")
    split = manifest(manifest_kind="split")
    for item in (features, training, candidate, protocol, split):
        rows.append(("artifact_manifest", item))
    run = record(
        "experiment_run",
        experiment_id="fixture-baseline",
        protocol_version="9" * 64,
        candidate_manifest_id=prepare("artifact_manifest", candidate)["id"],
        protocol_manifest_id=prepare("artifact_manifest", protocol)["id"],
        split_manifest_id=prepare("artifact_manifest", split)["id"],
        registered_at=AT,
        stage="development",
        verdict="not_run",
    )
    rows.append(("experiment_run", run))
    target = record(
        "target_definition",
        target_version="8" * 64,
        horizon_seconds=60,
        target_family="T1",
        quote_rule={"clock": "receipt"},
        label_rule={"flat": "0"},
        metric_contract={"primary": "fixture"},
        units="collateral/share",
    )
    rows.append(("target_definition", target))
    prediction = record(
        "prediction",
        recorded_at=AT + timedelta(seconds=12),
        origin_id=origin_id,
        experiment_run_id=prepare("experiment_run", run)["id"],
        target_definition_id=prepare("target_definition", target)["id"],
        target_version=target["target_version"],
        model_version="fixture-baseline",
        calibration_version="none",
        horizon_seconds=60,
        latency_ms="1000",
        generated_at=AT + timedelta(seconds=11),
        prediction_persisted_at=AT + timedelta(seconds=12),
        feature_manifest_id=prepare("artifact_manifest", features)["id"],
        training_manifest_id=prepare("artifact_manifest", training)["id"],
        output_kind="direction",
        direction="up",
    )
    return rows, prediction


async def test_prediction_is_saved_before_its_target(url):  # noqa: F811
    rows, prediction = prediction_graph()
    got = await append_batch(url, [*rows, ("prediction", prediction)], fixture_clock=AT)
    assert got[-1]["direction"] == "up"
    assert got[-1]["class_probabilities"] is None


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"prediction_persisted_at": AT + timedelta(seconds=71)}, "before target"),
        ({"latency_ms": "0"}, "latency"),
        ({"horizon_seconds": 300}, "horizon"),
        ({"class_probabilities": ["0.6", "0.4"]}, "output kind"),
    ],
)
async def test_prediction_rejects_lateness_wrong_horizon_and_invented_probabilities(
    url, mutation, match
):  # noqa: F811
    rows, prediction = prediction_graph()
    prediction.update(mutation)
    prediction["missing_fields"] = {k: "not_applicable" for k, v in prediction.items() if v is None}
    with pytest.raises(AdmissionError, match=match):
        await append_batch(url, [*rows, ("prediction", prediction)], fixture_clock=AT)


async def test_book_requires_all_declared_levels_and_preserves_raw_zero(url):  # noqa: F811
    rows, _, _ = graph()
    observation = prepare(*rows[1])["id"]
    token = prepare(*rows[3])["id"]
    book = record(
        "book_snapshot",
        source_observation_id=observation,
        token_outcome_id=token,
        reconstruction_version="fixture-v1",
        available_to_model_at=AT,
        snapshot_kind="snapshot",
        reconstruction_status="complete",
        delta_observation_ids=[],
        bid_state="observed",
        ask_state="empty",
        bid_level_count=1,
        ask_level_count=0,
        quote_age_semantics="unknown",
    )
    book_id = prepare("book_snapshot", book)["id"]
    level = record(
        "book_level",
        snapshot_id=book_id,
        source_observation_id=observation,
        side="bid",
        level=0,
        price_raw="0.5000",
        price_decimal="0.5000",
        size_raw="0.000",
        size_decimal="0.000",
        unit="shares",
    )
    with pytest.raises(AdmissionError, match="inventory"):
        await append_batch(url, [*rows, ("book_snapshot", book)], fixture_clock=AT)
    got = await append_batch(
        url, [*rows, ("book_snapshot", book), ("book_level", level)], fixture_clock=AT
    )
    assert str(got[-1]["size_decimal"]) == "0.000"
    # A manifest rooted at a book must include its numerical levels, not only its parent source.
    root = {"entity": "book_snapshot", "id": book_id}
    dependencies = [
        *[{"entity": entity, "id": prepare(entity, row)["id"]} for entity, row in rows[:4]],
        root,
    ]
    payload = {"schema_version": "fs2-manifest-v1", "roots": [root], "closure": dependencies}
    incomplete = manifest(
        manifest_kind="feature", payload=payload, content_hash=content_hash(payload)
    )
    with pytest.raises(AdmissionError, match="closure"):
        await append_batch(url, [("artifact_manifest", incomplete)], fixture_clock=AT)
    payload["closure"].append({"entity": "book_level", "id": got[-1]["id"]})
    complete = manifest(
        manifest_kind="feature", payload=payload, content_hash=content_hash(payload)
    )
    await append_batch(url, [("artifact_manifest", complete)], fixture_clock=AT)
