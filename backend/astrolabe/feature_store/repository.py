"""Transactional append-only local store. No production URL or application settings.

Rows and their dependency closure are validated together before any insert. The public
writer owns the transaction; generic prospective writes remain closed pending Phase 2
durable receipt evidence. Fixture clocks are allowed only for synthetic records.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from .admission import AdmissionError, prepare
from .migrations import local_engine
from .models import MODEL_BY_ENTITY
from .schema import FIELD_SPECS
from .types import HASH_PATTERN, canonical_json, utc_datetime

# Lists with entity-qualified references. Flags and external entity namespaces are not FKs.
LIST_REFERENCES = {
    "availability_evidence_ids": "source_observation",
    "delta_observation_ids": "source_observation",
    "mapping_evidence_ids": "source_observation",
    "input_observation_ids": "source_observation",
    "lineage_observation_ids": "source_observation",
    "market_match_ids": "market_identity_version",
    "outcome_observation_ids": "outcome_observation",
}
REVISION_FIELDS = {"supersedes_id", "supersedes_label_id", "revision_of"}
SUBJECT_FIELDS = {
    "source_registry": ("source_id",),
    "condition_identity": ("venue", "chain_id", "condition_id"),
    "market_identity_version": ("venue", "market_id"),
    "token_outcome_version": ("chain_id", "token_contract", "token_id"),
    "event_group_membership": ("event_group_id", "member_identity_id", "mapping_view"),
    "source_observation": ("source_id", "native_record_id"),
    "trade_observation": ("token_outcome_id", "trade_id"),
    "wallet_state_version": ("chain_id", "wallet_id", "token_outcome_id"),
    "information_event_version": ("document_id",),
    "outcome_observation": ("origin_id", "target_definition_id"),
    "label_version": ("origin_id", "target_definition_id"),
    "experiment_run": ("experiment_id", "protocol_version"),
    "archive_manifest": ("artifact_manifest_id",),
}


class PayloadConflict(AdmissionError):
    pass


def availability(entity, row):
    """Knowledge time, never a source publication/event timestamp."""
    fields = (
        "available_to_model_at",
        "available_at",
        "observed_from_at",
        "label_available_at",
        "prediction_persisted_at",
    )
    times = [row[name] for name in fields if row.get(name) is not None]
    return max(times) if times else row["recorded_at"]


def direct_references(entity, row):
    refs = []
    for field, spec in FIELD_SPECS[entity].items():
        value = row[field]
        if value is None:
            continue
        if spec["reference"]:
            refs.append((spec["reference"].split(".")[0], value))
        elif field in LIST_REFERENCES:
            refs.extend((LIST_REFERENCES[field], key) for key in value)
    if entity == "artifact_manifest":
        payload = row["payload"]
        if not isinstance(payload, dict) or payload.get("schema_version") != "fs2-manifest-v1":
            raise AdmissionError("manifest requires fs2-manifest-v1 payload")
        for field in ("roots", "closure"):
            values = payload.get(field)
            if not isinstance(values, list):
                raise AdmissionError("manifest roots and closure required")
            for value in values:
                if (
                    not isinstance(value, dict)
                    or set(value) != {"entity", "id"}
                    or not isinstance(value["entity"], str)
                    or value["entity"] not in MODEL_BY_ENTITY
                    or not isinstance(value["id"], str)
                    or not HASH_PATTERN.fullmatch(value["id"])
                ):
                    raise AdmissionError("manifest references require known entity and id")
            if len({(v["entity"], v["id"]) for v in values}) != len(values):
                raise AdmissionError("duplicate manifest references")
        roots = payload["roots"]
        if not roots and not payload.get("empty_reason"):
            raise AdmissionError("empty manifest must explain coverage/applicability")
        refs.extend((value["entity"], value["id"]) for value in roots)
    return refs


async def _load(conn, entity, key, cache):
    identity = (entity, key)
    if identity not in cache:
        table = MODEL_BY_ENTITY[entity].__table__
        found = (
            (await conn.execute(select(table).where(table.c.id == key))).mappings().one_or_none()
        )
        if found is None:
            raise AdmissionError(f"missing {entity} dependency {key}")
        cache[identity] = dict(found)
    return cache[identity]


async def _closure(conn, entity, row, cache):
    """Visit shared dependencies once per graph, without recursive path expansion.

    Book/level composition is a permitted bidirectional relationship. All other cycles,
    including long revision cycles, are rejected by an iterative depth-first check.
    """
    root = (entity, row["id"])
    cache.setdefault(root, row)
    graph = {}
    pending = [root]
    while pending:
        identity = pending.pop()
        if identity in graph:
            continue
        kind, key = identity
        value = await _load(conn, kind, key, cache)
        references = set(direct_references(kind, value))
        if kind == "book_snapshot":
            table = MODEL_BY_ENTITY["book_level"].__table__
            for level in (
                await conn.execute(select(table).where(table.c.snapshot_id == key))
            ).mappings():
                cache.setdefault(("book_level", level["id"]), dict(level))
            references.update(
                (k, i)
                for (k, i), v in list(cache.items())
                if k == "book_level" and v["snapshot_id"] == key
            )
        graph[identity] = references
        pending.extend(references - graph.keys())

    state = {}
    for start in graph:
        if state.get(start) == 2:
            continue
        stack = [(start, False)]
        while stack:
            node, finished = stack.pop()
            if finished:
                state[node] = 2
                continue
            if state.get(node) == 1:
                raise AdmissionError("cyclic dependency/revision graph")
            if state.get(node) == 2:
                continue
            state[node] = 1
            stack.append((node, True))
            stack.extend(
                (child, False)
                for child in graph[node]
                if not (node[0] == "book_level" and child[0] == "book_snapshot")
            )

    for identity, value in (
        (node, cache[node]) for node in graph if node[0] == "artifact_manifest"
    ):
        reachable = set()
        pending = list(graph[identity])
        while pending:
            node = pending.pop()
            if node in reachable:
                continue
            reachable.add(node)
            pending.extend(graph[node] - reachable)
        reachable.discard(identity)
        declared = {(r["entity"], r["id"]) for r in value["payload"]["closure"]}
        if declared != reachable:
            raise AdmissionError("manifest transitive closure differs from declared inventory")
    return set(graph) - {root}


def _ordered(row, earlier, later):
    if row.get(earlier) is not None and row.get(later) is not None and row[earlier] > row[later]:
        raise AdmissionError(f"{earlier} must not follow {later}")


def _same(row, dependency, fields):
    if any(row.get(field) != dependency.get(field) for field in fields):
        raise AdmissionError(f"revision/link changes logical subject: {fields}")


async def _validate(conn, entity, row, cache):
    closure = await _closure(conn, entity, row, cache)
    prospective = row["provenance_class"] == "prospective"
    causal_fixture = prospective or row["provenance_class"] == "synthetic"
    deps = [cache[ref] for ref in closure]
    if prospective and any(dep["provenance_class"] != "prospective" for dep in deps):
        raise AdmissionError("prospective record depends on non-prospective evidence")
    if row["provenance_class"] != "synthetic" and any(
        dep["provenance_class"] == "synthetic" for dep in deps
    ):
        raise AdmissionError("synthetic evidence cannot enter non-synthetic records")
    if row["provenance_class"] == "reconstructed" and any(
        dep["provenance_class"] == "legacy_unverified" for dep in deps
    ):
        raise AdmissionError("legacy dependency cannot silently improve provenance")
    for field in REVISION_FIELDS & row.keys():
        if row[field] is None:
            continue
        old = await _load(conn, entity, row[field], cache)
        _same(row, old, SUBJECT_FIELDS[entity])
        if availability(entity, old) >= availability(entity, row):
            raise AdmissionError("revision must advance knowledge time")
        if entity == "source_observation" and row["native_record_id"] is None:
            raise AdmissionError("unknown native subject cannot establish source revision")
    # Metadata and scientific outputs cannot predate the evidence they reference.
    if deps and entity not in {"label_version", "outcome_observation", "prediction"}:
        relevant = [
            ref
            for ref in closure
            if not (entity == "feature_value" and ref[0] == "research_origin")
        ]
        if relevant and max(availability(ref[0], cache[ref]) for ref in relevant) > availability(
            entity, row
        ):
            raise AdmissionError("record availability precedes a dependency")

    async def ref(field):
        target = FIELD_SPECS[entity][field]["reference"].split(".")[0]
        return await _load(conn, target, row[field], cache)

    if (
        entity == "artifact_manifest"
        and row["manifest_kind"] == "training"
        and row["payload"]["roots"]
    ):
        cutoff_text = row["payload"].get("as_of_cutoff_at")
        if not isinstance(cutoff_text, str):
            raise AdmissionError("training inventory requires its actual as-of cutoff")
        cutoff = utc_datetime(datetime.fromisoformat(cutoff_text.replace("Z", "+00:00")))
        if cutoff > row["available_at"]:
            raise AdmissionError("training cutoff follows model availability")
        for kind, key in closure:
            dependency = cache[(kind, key)]
            if availability(kind, dependency) > cutoff:
                raise AdmissionError("training dependency became available after training cutoff")
            if kind == "label_version" and dependency["status"] not in {"evaluated", "unchanged"}:
                raise AdmissionError("training inventory contains an unavailable label")
    elif entity == "source_registry":
        if row["access_state"] == "runtime_verified":
            if row["verified_observation_id"] is None:
                raise AdmissionError("runtime verification requires observation evidence")
            evidence = await ref("verified_observation_id")
            _same(row, evidence, ("source_id", "parser_version"))
    elif entity == "source_observation":
        source = await ref("source_registry_id")
        _same(row, source, ("source_id", "parser_version"))
        if prospective and row["first_received_at"] is None:
            raise AdmissionError("prospective receipt is required")
        if row["first_received_at"] is None and row["provenance_class"] != "synthetic":
            if (
                row["provenance_class"] != "legacy_unverified"
                or row["missing_fields"]["first_received_at"] != "unknown_legacy"
            ):
                raise AdmissionError("absent historical receipt must remain legacy_unverified")
        for earlier, later in (
            ("first_received_at", "parsed_at"),
            ("first_received_at", "ingested_at"),
            ("parsed_at", "available_to_model_at"),
            ("ingested_at", "available_to_model_at"),
        ):
            _ordered(row, earlier, later)
        if row["missing_reason"] == "observed" and row["parsed_at"] is None:
            raise AdmissionError("observed source requires parsing completion")
        if row["first_available_at"] is not None and not row["availability_evidence_ids"]:
            raise AdmissionError("public availability requires evidence")
        if row["raw_payload_inline"] is not None:
            import base64
            import hashlib

            encoding = row["payload_encoding"]
            if encoding not in {"utf8", "base64"}:
                raise AdmissionError("inline bytes require declared encoding")
            raw = (
                row["raw_payload_inline"].encode()
                if encoding == "utf8"
                else base64.b64decode(row["raw_payload_inline"], validate=True)
            )
            if hashlib.sha256(raw).hexdigest() != row["payload_hash"]:
                raise AdmissionError("raw payload checksum mismatch")
    elif entity == "condition_identity":
        if row["identity_status"] == "verified" and (
            any(
                row[field] is None
                for field in (
                    "chain_id",
                    "condition_id",
                    "collateral_address",
                    "collateral_decimals",
                )
            )
            or not row["mapping_evidence_ids"]
        ):
            raise AdmissionError("verified condition requires complete namespace and evidence")
    elif entity == "token_outcome_version":
        market = await ref("market_identity_id")
        if row["condition_identity_id"] != market["condition_identity_id"]:
            raise AdmissionError("token and market condition mappings differ")
        if row["condition_identity_id"] is not None:
            condition = await ref("condition_identity_id")
            if row["chain_id"] != condition["chain_id"]:
                raise AdmissionError("token and condition chain differ")
    elif entity == "book_level":
        book = await ref("snapshot_id")
        if row["source_observation_id"] not in {
            book["source_observation_id"],
            *book["delta_observation_ids"],
        }:
            raise AdmissionError("book level raw evidence absent from reconstruction")
        for name in ("price", "size"):
            from .types import exact_decimal

            if row[f"{name}_decimal"] is not None and (
                row[f"{name}_decimal"].as_tuple() != exact_decimal(row[f"{name}_raw"]).as_tuple()
                or row[f"{name}_decimal"] < 0
            ):
                raise AdmissionError("book numerical primitive differs from raw evidence")
        if row["level"] >= book[f"{row['side']}_level_count"]:
            raise AdmissionError("book level exceeds declared retained depth")
    elif entity == "book_snapshot":
        if row["previous_snapshot_id"] is not None:
            _same(row, await ref("previous_snapshot_id"), ("token_outcome_id",))
        if row["snapshot_kind"] == "reconstructed_delta" and not row["delta_observation_ids"]:
            raise AdmissionError("delta reconstruction requires raw delta lineage")
        levels = [
            value
            for (kind, _), value in cache.items()
            if kind == "book_level" and value["snapshot_id"] == row["id"]
        ]
        for side in ("bid", "ask"):
            retained = [level["level"] for level in levels if level["side"] == side]
            if sorted(retained) != list(range(row[f"{side}_level_count"])):
                raise AdmissionError("book snapshot and complete retained level inventory differ")
            if row[f"{side}_state"] == "empty" and retained:
                raise AdmissionError("empty book side has levels")
    elif entity == "trade_observation":
        from .types import exact_decimal

        for name in ("price", "size"):
            number = row[f"{name}_decimal"]
            if number is not None and (
                number < 0
                or number.as_tuple() != exact_decimal(row[f"trade_{name}_raw"]).as_tuple()
            ):
                raise AdmissionError("trade primitive differs from source value")
        if row["trade_notional"] is not None:
            if row["price_decimal"] is None or row["size_decimal"] is None:
                raise AdmissionError("trade notional requires numerical primitives")
            with localcontext() as context:
                context.prec = max(
                    32,
                    sum(len(row[f"{name}_decimal"].as_tuple().digits) for name in ("price", "size"))
                    + 2,
                )
                if row["trade_notional"] != row["price_decimal"] * row["size_decimal"]:
                    raise AdmissionError("trade notional differs from exact price times size")
        if row["deduplication_status"] == "verified" and not row["economic_fill_key"]:
            raise AdmissionError("verified fill requires economic identity")
    elif entity == "wallet_state_version":
        history = await ref("history_manifest_id")
        if any(
            availability(link["entity"], cache[(link["entity"], link["id"])])
            > row["as_of_cutoff_at"]
            for link in history["payload"]["closure"]
        ):
            raise AdmissionError("wallet history contains information after as-of cutoff")
    elif entity == "information_event_version":
        _ordered(row, "first_received_at", "available_to_model_at")
        if row["numeric_expectation_raw"] is not None and (
            row["expectation_available_at"] is None
            or row["first_available_at"] is None
            or row["expectation_available_at"] >= row["first_available_at"]
        ):
            raise AdmissionError("surprise expectation must be evidenced before release")
    elif entity == "archive_manifest":
        if row["verification_state"] == "verified" and (
            row["preservation_report_id"] is None or row["restore_report_id"] is None
        ):
            raise AdmissionError("archive verification requires preservation and restore reports")
    elif entity == "research_origin":
        token = await ref("token_outcome_id")
        if token["market_identity_id"] != row["market_identity_id"]:
            raise AdmissionError("origin token belongs to a different market version")
        _ordered(row, "feature_cutoff_at", "prediction_origin_at")
        _ordered(row, "prediction_origin_at", "origin_recorded_at")
        if any(availability(ref[0], cache[ref]) > row["feature_cutoff_at"] for ref in closure):
            raise AdmissionError("origin depends on evidence after feature cutoff")
        group = await ref("group_manifest_id")
        if group["manifest_kind"] != "group":
            raise AdmissionError("origin requires group manifest")
        if any(cache[ref].get("mapping_view") == "conservative_evaluation" for ref in closure):
            raise AdmissionError("later evaluation grouping cannot become an origin input")
    elif entity == "feature_value":
        origin = await ref("origin_id")
        definition = await ref("feature_definition_id")
        _same(row, definition, ("feature_id", "feature_version", "units"))
        _ordered(row, "window_end_at", "computed_at")
        _ordered(row, "computed_at", "available_to_model_at")
        if row["window_end_at"] > origin["feature_cutoff_at"]:
            raise AdmissionError("feature window extends beyond cutoff")
        if causal_fixture and availability(entity, row) > origin["feature_cutoff_at"]:
            raise AdmissionError("late feature cannot be prospective at origin")
        if any(
            availability(ref[0], cache[ref]) > origin["feature_cutoff_at"]
            for ref in closure
            if ref[0] not in {"research_origin"}
        ):
            if causal_fixture:
                raise AdmissionError("feature has a late dependency")
        present = row["raw_value_decimal"] is not None or row["raw_value_vector"] is not None
        if (row["missingness_reason"] == "observed") != present:
            raise AdmissionError("feature missingness disagrees with numerical value")
        if row["denominator"] == 0 and present:
            raise AdmissionError("zero-denominator ratio must remain missing/invalid")
    elif entity in {"prediction", "outcome_observation", "label_version"}:
        origin = await ref("origin_id")
        target = await ref("target_definition_id")
        target_at = (
            origin["prediction_origin_at"] + timedelta(seconds=target["horizon_seconds"])
            if target["horizon_seconds"] is not None
            else None
        )
        if entity != "prediction":
            if target_at is not None and row["target_at"] != target_at:
                raise AdmissionError("target time differs from origin plus horizon")
        if entity == "prediction":
            if row["horizon_seconds"] != target["horizon_seconds"]:
                raise AdmissionError("prediction horizon differs from target")
            _same(row, target, ("target_version",))
            if target["recorded_at"] > origin["prediction_origin_at"]:
                raise AdmissionError("target definition was not locked before origin")
            if any(availability(ref[0], cache[ref]) > row["generated_at"] for ref in closure):
                raise AdmissionError("prediction completion precedes a required dependency")
            _ordered(row, "generated_at", "prediction_persisted_at")
            if row["generated_at"] < origin["prediction_origin_at"]:
                raise AdmissionError("prediction completion precedes origin")
            if causal_fixture and (target_at is None or availability(entity, row) >= target_at):
                raise AdmissionError("prediction was not persisted before target")
            delta = row["generated_at"] - origin["prediction_origin_at"]
            latency = (
                Decimal(delta.days * 86400000 + delta.seconds * 1000)
                + Decimal(delta.microseconds) / 1000
            )
            if row["latency_ms"] != latency:
                raise AdmissionError("prediction latency differs from measured clocks")
            field = {
                "direction": "direction",
                "class_probabilities": "class_probabilities",
                "distribution": "distribution_parameters",
                "abstention": "abstention_reason",
            }[row["output_kind"]]
            outputs = {
                "direction",
                "class_probabilities",
                "distribution_parameters",
                "abstention_reason",
            }
            if row[field] is None or any(row[name] is not None for name in outputs - {field}):
                raise AdmissionError("prediction output fields disagree with output kind")
            for manifest_field, kind in (
                ("feature_manifest_id", "feature"),
                ("training_manifest_id", "training"),
            ):
                manifest = await ref(manifest_field)
                if manifest["manifest_kind"] != kind:
                    raise AdmissionError("prediction manifest kind differs")
                if (
                    kind == "training"
                    and availability("artifact_manifest", manifest) > origin["prediction_origin_at"]
                ):
                    raise AdmissionError("training manifest became available after origin")
                for link in manifest["payload"]["closure"]:
                    dep = cache[(link["entity"], link["id"])]
                    if (
                        kind == "feature"
                        and link["entity"] == "feature_value"
                        and dep["origin_id"] != row["origin_id"]
                    ):
                        raise AdmissionError("feature manifest crosses origins")
                    if (
                        link["entity"] != "research_origin"
                        and availability(link["entity"], dep) > origin["prediction_origin_at"]
                    ):
                        raise AdmissionError("prediction uses post-origin information")
            experiment = await ref("experiment_run_id")
            if experiment["registered_at"] > origin["prediction_origin_at"]:
                raise AdmissionError("candidate was registered after prediction origin")
            if row["uncalibrated_prediction_id"] is not None:
                _same(
                    row,
                    await ref("uncalibrated_prediction_id"),
                    ("origin_id", "target_definition_id"),
                )
        elif entity == "outcome_observation":
            source = await ref("source_observation_id")
            if row["first_received_at"] != source["first_received_at"]:
                raise AdmissionError("outcome receipt differs from source evidence")
            if row["available_to_model_at"] is not None and (
                row["available_to_model_at"] < availability("source_observation", source)
            ):
                raise AdmissionError("outcome availability precedes source evidence")
            _ordered(row, "first_received_at", "available_to_model_at")
            if row["observation_status"] == "observed":
                clock_field = {
                    "receipt": "first_received_at",
                    "source_event": "source_event_at",
                    "source_published": "source_published_at",
                }.get(target["quote_rule"].get("clock"))
                if clock_field is None or source[clock_field] is None:
                    raise AdmissionError("observed outcome requires its declared source clock")
                if row["label_observed_at"] != source[clock_field]:
                    raise AdmissionError("outcome observation differs from declared clock evidence")
        elif entity == "label_version":
            _ordered(row, "label_observed_at", "label_available_at")
            if row["status"] in {"evaluated", "unchanged"} and (
                row["label_value"] is None
                or row["label_available_at"] is None
                or not row["outcome_observation_ids"]
            ):
                raise AdmissionError("evaluated label requires value, availability and outcomes")
            if row["status"] not in {"evaluated", "unchanged"} and row["label_value"] is not None:
                raise AdmissionError("unavailable label cannot carry an evaluated target value")
            if row["actual_delay_seconds"] is not None:
                if row["label_observed_at"] is None:
                    raise AdmissionError("label delay requires observation clock")
                delta = row["label_observed_at"] - row["target_at"]
                delay = (
                    Decimal(delta.days * 86400 + delta.seconds)
                    + Decimal(delta.microseconds) / 1000000
                )
                if row["actual_delay_seconds"] != delay:
                    raise AdmissionError("label delay differs from observed and target clocks")
            for key in row["outcome_observation_ids"]:
                outcome = await _load(conn, "outcome_observation", key, cache)
                _same(row, outcome, ("origin_id", "target_definition_id", "target_at"))
                if (
                    row["label_available_at"] is not None
                    and availability("outcome_observation", outcome) > row["label_available_at"]
                ):
                    raise AdmissionError("label availability precedes its outcome")
            if row["prediction_id"] is not None:
                _same(row, await ref("prediction_id"), ("origin_id", "target_definition_id"))
            if row["supersedes_label_id"] is not None and not row["revision_reason"]:
                raise AdmissionError("label revision requires reason")


async def _append(conn, records, fixture_clock):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    now = utc_datetime(fixture_clock) if fixture_clock is not None else datetime.now(UTC)
    cache = {}
    staged = []
    for entity, payload in records:
        payload = dict(payload)
        managed_clocks = {"recorded_at"}
        if payload.get("provenance_class") == "prospective":
            managed_clocks.update(
                {
                    "source_observation": {"ingested_at", "available_to_model_at"},
                    "research_origin": {"origin_recorded_at"},
                    "prediction": {"prediction_persisted_at"},
                    "label_version": (
                        {"label_available_at"}
                        if payload.get("status") in {"evaluated", "unchanged"}
                        else set()
                    ),
                }.get(entity, set())
            )
        if fixture_clock is not None and payload.get("provenance_class") != "synthetic":
            raise AdmissionError("fixture clock is permitted only for synthetic records")
        if fixture_clock is None and managed_clocks & payload.keys():
            raise AdmissionError("durable record time is owned by the writer")
        payload.setdefault("recorded_at", now)
        if fixture_clock is None and payload.get("provenance_class") == "prospective":
            for field in (
                "first_received_at",
                "parsed_at",
                "computed_at",
                "generated_at",
                "prediction_persisted_at",
                "label_available_at",
                "available_to_model_at",
                "prediction_origin_at",
                "feature_cutoff_at",
                "origin_recorded_at",
            ):
                if payload.get(field) is not None and utc_datetime(payload[field]) > now:
                    raise AdmissionError(f"local {field} cannot be in the future")
            for field in managed_clocks:
                payload[field] = now
        row = prepare(entity, payload)
        table = MODEL_BY_ENTITY[entity].__table__
        old = (
            (await conn.execute(select(table).where(table.c.id == row["id"])))
            .mappings()
            .one_or_none()
        )
        if old is not None and fixture_clock is None:
            for field in managed_clocks:
                row[field] = old[field]
        identity = (entity, row["id"])
        previous = dict(old) if old is not None else cache.get(identity)
        if previous is not None and canonical_json(previous) != canonical_json(row):
            raise PayloadConflict("same natural key has different immutable payload")
        cache[identity] = row
        staged.append((entity, row, old is not None, managed_clocks))
    for entity, row, exists, _ in staged:
        if not exists:
            await _validate(conn, entity, row, cache)
    insert_fn = pg_insert if conn.dialect.name == "postgresql" else sqlite_insert
    for entity, row, exists, managed_clocks in staged:
        if exists:
            continue
        table = MODEL_BY_ENTITY[entity].__table__
        await conn.execute(
            insert_fn(table).values(**row).on_conflict_do_nothing(index_elements=["id"])
        )
        stored = (await conn.execute(select(table).where(table.c.id == row["id"]))).mappings().one()
        if fixture_clock is None:
            for field in managed_clocks:
                row[field] = stored[field]
        if canonical_json(dict(stored)) != canonical_json(row):
            raise PayloadConflict("concurrent natural-key conflict")
    return [row for _, row, _, _ in staged]


async def append_batch(url, records, *, fixture_clock=None):
    """All-or-nothing append. Callers retry original facts, never change receipt clocks.

    SQLite writer contention is retried with bounded backoff; no failed transaction leaks
    partial evidence. Production-compatible SQL does not authorise a production connection.
    """
    records = list(records)
    if fixture_clock is None and any(
        payload.get("provenance_class") == "prospective" for _, payload in records
    ):
        raise AdmissionError(
            "prospective writes require the Phase 2 durable receipt/clock boundary; "
            "a generic transaction timestamp is not evidence of model availability"
        )
    engine = local_engine(url)
    try:
        for attempt in range(4):
            try:
                async with engine.begin() as conn:
                    return await _append(conn, records, fixture_clock)
            except OperationalError as exc:
                if (
                    engine.dialect.name != "sqlite"
                    or "locked" not in str(exc).lower()
                    or attempt == 3
                ):
                    raise
                await asyncio.sleep(0.01 * 2**attempt)
    finally:
        await engine.dispose()
