"""Pure structural admission, separate from runtime source verification and modelling.

No coercion of missing values to zero; no unknown enum or binary float enters the store.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, localcontext

from .schema import FIELD_SPECS, KEY_FIELDS
from .types import HASH_PATTERN, canonical_json, exact_decimal, stable_id, uint_text, utc_datetime

CONTRACT = "arepo-fs-v2.0"
PROVENANCE = {"prospective", "reconstructed", "synthetic", "legacy_unverified"}
MISSING = {
    "observed",
    "not_supported",
    "not_requested",
    "permission_denied",
    "rate_limited",
    "source_error",
    "transport_gap",
    "not_yet_available",
    "history_truncated",
    "stale",
    "invalid",
    "identity_unresolved",
    "not_applicable",
    "censored_by_close",
    "censored_by_window_end",
    "deleted_by_source",
    "unknown_legacy",
}

ENUMS = {
    ("archive_manifest", "verification_state"): "unverified verified failed",
    ("artifact_manifest", "manifest_kind"): (
        "sampling group feature training split model protocol result archive restore legacy"
    ),
    ("book_level", "side"): "bid ask",
    ("book_snapshot", "ask_state"): "observed empty unknown invalid",
    ("book_snapshot", "bid_state"): "observed empty unknown invalid",
    ("book_snapshot", "quote_age_semantics"): "venue_update receipt unknown",
    ("book_snapshot", "reconstruction_status"): "complete gap stale invalid",
    ("book_snapshot", "snapshot_kind"): "snapshot reconstructed_delta",
    ("condition_identity", "identity_status"): "verified unresolved conflicting",
    ("event_group_membership", "mapping_view"): "as_known conservative_evaluation",
    ("event_group_membership", "relationship_type"): (
        "common_cause mutually_exclusive nested_threshold recurring_release related_contract"
    ),
    ("experiment_run", "stage"): "design development locked_confirmation result",
    ("experiment_run", "verdict"): "not_run positive negative inconclusive invalid",
    ("feature_definition", "status"): "candidate locked retired",
    ("information_event_version", "text_hash_scope"): "content metadata_only",
    ("information_event_version", "text_rights_state"): "unknown permitted restricted prohibited",
    ("label_version", "status"): "pending unavailable unchanged closed evaluated invalid",
    ("label_version", "censoring_reason"): "close window source quality",
    ("outcome_observation", "observation_status"): "observed pending unavailable closed invalid",
    ("prediction", "abstention_reason"): "quality applicability insufficient-evidence no-signal",
    ("prediction", "direction"): "up down flat",
    ("prediction", "output_kind"): "class_probabilities distribution direction abstention",
    ("research_origin", "origin_kind"): "prospective legacy_reference synthetic",
    ("research_origin", "sampling_arm"): "scheduled triggered control",
    ("source_observation", "payload_encoding"): "utf8 base64 withheld unavailable",
    ("source_observation", "quality_assessment_state"): "checked not_checked",
    ("source_registry", "access_state"): "documented_only runtime_verified blocked retired",
    ("source_registry", "rights_state"): "unknown permitted restricted prohibited",
    ("target_definition", "target_family"): "T1 T2 T3 T4 T5 T6 T7",
    ("trade_observation", "aggressor_side"): "buy sell unknown",
    ("trade_observation", "deduplication_status"): "verified source_local ambiguous",
    ("trade_observation", "match_status"): "matched unknown",
    ("trade_observation", "settlement_status"): "matched settled reverted unknown",
}


class AdmissionError(ValueError):
    """Invalid evidence is rejected, never silently repaired."""


def content_hash(payload) -> str:
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def _json(value):
    # Roundtrip also detaches caller-owned mutable containers. Reject float/Decimal/datetime
    # in JSON: exact values need explicit schemas and string encodings, not implicit tags.
    def inspect(item):
        if type(item) is int and abs(item) > 2**53 - 1:
            raise AdmissionError("large JSON integers require exact string encoding")
        if isinstance(item, dict):
            for child in item.values():
                inspect(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                inspect(child)

    inspect(value)
    encoded = canonical_json(value)
    decoded = json.loads(encoded)
    if canonical_json(decoded) != encoded or decoded != value:
        raise AdmissionError("JSON numerical values require explicit string encodings")
    return decoded


def typed_number(value):
    if not isinstance(value, dict) or set(value) != {"kind", "value"}:
        raise AdmissionError("typed number requires kind and value")
    raw = value["value"]
    if not isinstance(raw, str):
        raise AdmissionError("typed number value must be a string")
    if value["kind"] == "decimal":
        exact_decimal(raw)
    elif value["kind"] == "float64":
        try:
            number = float.fromhex(raw)
        except (ValueError, OverflowError) as exc:
            raise AdmissionError("invalid float64 hex") from exc
        if not math.isfinite(number) or number.hex() != raw:
            raise AdmissionError("float64 must be finite canonical hexadecimal")
    else:
        raise AdmissionError("unknown typed number kind")
    return _json(value)


def typed_vector(value):
    required = {"schema_version", "dtype", "shape", "axis", "values", "units", "model_version"}
    if not isinstance(value, dict) or set(value) != required:
        raise AdmissionError("typed vector requires complete schema, axes and units")
    if value["dtype"] not in {"decimal", "float64"}:
        raise AdmissionError("unknown vector dtype")
    shape = value["shape"]
    if not isinstance(shape, list) or not shape or any(type(n) is not int or n < 0 for n in shape):
        raise AdmissionError("vector shape must be nonnegative integer dimensions")
    if not isinstance(value["axis"], list) or len(value["axis"]) != len(shape):
        raise AdmissionError("vector axes must identify every dimension")
    if not isinstance(value["values"], list) or len(value["values"]) != math.prod(shape):
        raise AdmissionError("vector shape/value count differs")
    for name in ("schema_version", "units", "model_version"):
        if not isinstance(value[name], str) or not value[name]:
            raise AdmissionError(f"vector {name} required")
    for item in value["values"]:
        typed_number({"kind": value["dtype"], "value": item})
    return _json(value)


def normalise_value(entity, field, value, spec):
    kind = spec["type"]
    if value is None:
        if spec["nullable"] != "true":
            raise AdmissionError(f"{entity}.{field} is required")
        return None
    if kind == "UTC":
        return utc_datetime(value)
    if kind == "DECIMAL_TEXT":
        return exact_decimal(value)
    if kind == "UINT_TEXT":
        return uint_text(value, bits=256 if field == "token_id" else None)
    if kind == "INT64":
        if type(value) is not int or not 0 <= value < 2**63:
            raise AdmissionError(f"{field} requires a nonnegative int64")
        return value
    if kind in {"TEXT", "HASH", "HEX32", "ADDRESS", "ENUM"}:
        if not isinstance(value, str):
            raise AdmissionError(f"{field} requires text")
        if kind == "HASH" and not HASH_PATTERN.fullmatch(value):
            raise AdmissionError(f"{field} requires a lowercase SHA256")
        if kind in {"HEX32", "ADDRESS"}:
            length = 64 if kind == "HEX32" else 40
            if not re.fullmatch("0x[0-9a-f]{" + str(length) + "}", value):
                raise AdmissionError(f"{field} requires normalised lowercase hex")
        if kind == "ENUM":
            allowed = (
                PROVENANCE
                if field == "provenance_class"
                else MISSING
                if field in {"missing_reason", "missingness_reason"}
                else set(ENUMS[(entity, field)].split())
            )
            if value not in allowed:
                raise AdmissionError(f"invalid {entity}.{field}")
        return value
    if kind == "TYPED_NUMBER":
        return typed_number(value)
    if kind == "TYPED_VECTOR":
        return typed_vector(value)
    if kind == "TYPED_OBJECT":
        if not isinstance(value, dict) or not isinstance(value.get("schema_version"), str):
            raise AdmissionError(f"{field} requires a discriminated schema_version")
        if not value["schema_version"]:
            raise AdmissionError("typed object schema_version cannot be empty")
    if kind == "JSON" and not isinstance(value, (dict, list)):
        raise AdmissionError("JSON fields require an explicit object or array")
    if kind in {"ID_LIST", "DECIMAL_VECTOR"}:
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise AdmissionError(f"{field} requires an ordered string list")
        if kind == "DECIMAL_VECTOR":
            values = [exact_decimal(v) for v in value]
            if not values or any(v < 0 or v > 1 for v in values):
                raise AdmissionError("probability/payout components must lie in [0,1]")
            if field in {"class_probabilities", "stance_probabilities"}:
                with localcontext() as context:
                    digits = max(len(v.as_tuple().digits) + v.as_tuple().exponent for v in values)
                    digits -= min(v.as_tuple().exponent for v in values)
                    if digits > 10000:
                        raise AdmissionError(
                            "probability normalization exceeds exact validation budget"
                        )
                    context.prec = max(32, digits + len(str(len(values))) + 2)
                    if sum(values, Decimal(0)) != 1:
                        raise AdmissionError("probabilities must sum exactly to one")
    return _json(value)


ALIASES = {
    "source_observation": "observation_id",
    "research_origin": "origin_id",
    "prediction": "prediction_id",
    "label_version": "label_id",
}


def prepare(entity: str, payload: dict) -> dict:
    """Validate complete record; only deterministic key/alias generation is implicit.

    Actual persisted clocks are supplied by the writer, never this pure function.
    """
    if entity not in FIELD_SPECS:
        raise AdmissionError("unknown entity")
    specs = FIELD_SPECS[entity]
    unknown = set(payload) - set(specs)
    if unknown:
        raise AdmissionError(f"unknown {entity} fields: {sorted(unknown)}")
    auto = {"id", ALIASES.get(entity)}
    row = {
        name: normalise_value(entity, name, payload.get(name), spec)
        for name, spec in specs.items()
        if name not in auto
    }
    if any(row[name] == "" for name in KEY_FIELDS[entity]):
        raise AdmissionError("natural-key components cannot be empty strings")
    row["id"] = stable_id(entity, {name: row[name] for name in KEY_FIELDS[entity]})
    if payload.get("id", row["id"]) != row["id"]:
        raise AdmissionError("record id differs from natural key")
    if entity in ALIASES:
        alias = ALIASES[entity]
        row[alias] = row["id"]
        if payload.get(alias, row["id"]) != row["id"]:
            raise AdmissionError("compatibility alias differs from id")
    if row["schema_version"] != CONTRACT:
        raise AdmissionError("unsupported store contract version")
    if row.get("horizon_seconds") is not None and row["horizon_seconds"] <= 0:
        raise AdmissionError("fixed horizon must be positive")
    missing = row["missing_fields"]
    if not isinstance(missing, dict):
        raise AdmissionError("missing_fields must map fields to reasons")
    absent = {name for name, value in row.items() if value is None}
    if set(missing) != absent or any(
        reason not in MISSING - {"observed"} for reason in missing.values()
    ):
        raise AdmissionError("each null field requires exactly one valid missingness reason")
    for name, value in row.items():
        if (
            value is not None
            and (
                name.endswith("_fraction")
                or name.endswith("_confidence")
                or name in {"selection_probability", "minimum_coverage"}
            )
            and not 0 <= value <= 1
        ):
            raise AdmissionError(f"{name} must lie in [0,1]")
    for start, end in (("valid_from_at", "valid_to_at"), ("window_start_at", "window_end_at")):
        if row.get(start) is not None and row.get(end) is not None and row[start] > row[end]:
            raise AdmissionError("reversed time interval")
    if entity == "artifact_manifest" and content_hash(row["payload"]) != row["content_hash"]:
        raise AdmissionError("manifest content hash mismatch")
    if entity == "artifact_manifest" and bool(row["object_uri"]) != bool(row["object_hash"]):
        raise AdmissionError("object URI and integrity hash must be supplied together")
    return row
