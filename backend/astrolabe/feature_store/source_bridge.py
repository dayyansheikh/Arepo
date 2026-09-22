"""Verified diagnostic artefacts -> local immutable records, never a prospective bypass.

Source-specific parsing has its own durable acknowledgement. Previously captured
diagnostics are reconstructed; injected transports remain synthetic. No caller can
choose provenance, receipt clocks, payloads or arbitrary source definitions here.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

from .admission import CONTRACT, content_hash
from .capture import (
    _clock,
    _digest,
    _json_bytes,
    _strict_json,
    _sync_directory,
    _write_once,
    verify_capture,
)
from .repository import append_batch
from .schema import FIELD_SPECS
from .source_parsers import (
    _condition,
    clob_book,
    data_v2_trades,
    gamma_identity,
    gamma_market,
    native_clock,
)
from .sources import SOURCES
from .types import exact_decimal, uint_text, utc_datetime

BRIDGE_VERSION = "fs2-diagnostic-bridge-v1"


def _time(clock):
    return utc_datetime(datetime.fromisoformat(clock["utc"]))


def parse_source(capture):
    """Typed transformations only. Native REST numeric clock units remain unadmitted."""
    if capture["parsed"]["parse_error"] is not None:
        return {"value": None, "error": capture["parsed"]["parse_error"]}
    value = _strict_json(capture["raw"])
    source = capture["receipt"]["source_id"]
    params = capture["receipt"]["request"]["params"]
    try:
        if source == "gamma.market":
            value = gamma_market(value, expected_market=SOURCES[source].market_request_id(
                capture["receipt"]["request"]))
        elif source == "gamma.markets":
            if not isinstance(value, list):
                raise ValueError("market list required")
            value = [gamma_identity(row) for row in value]
        elif source == "clob.book":
            value = clob_book(value, expected_token=params["token_id"])
        elif source == "data.v2.trades":
            value = data_v2_trades(value, expected_condition=params.get("condition"))
        elif source == "coinbase.btc_usd.ticker":
            if not isinstance(value, dict):
                raise ValueError("ticker object required")
            value = {
                "product": "BTC-USD",
                "numbers": {k: exact_decimal(value[k]) for k in ("price", "size", "bid", "ask")},
                "last_trade_clock": native_clock(
                    value.get("time"), unit="iso8601",
                    received_at=_time(capture["receipt"]["first_received"]),
                ),
            }
            if any(v < 0 for v in value["numbers"].values()):
                raise ValueError("negative ticker quantity")
        elif source == "clob.market_stream":
            messages = value if isinstance(value, list) else [value]
            if not messages:
                raise ValueError("empty stream frame is not a book snapshot")
            for message in messages:
                if not isinstance(message, dict):
                    raise ValueError("stream message object required")
                if message.get("event_type") == "book":
                    clob_book(message, expected_token=params["assets_ids"][0])
                elif message.get("event_type") == "price_change":
                    _condition(message.get("market"))
                    changes = message.get("price_changes")
                    if not isinstance(changes, list) or not changes:
                        raise ValueError("stream changes required")
                    for change in changes:
                        if (not isinstance(change, dict)
                                or change.get("side") not in {"BUY", "SELL"}
                                or not 0 <= exact_decimal(change.get("price")) <= 1
                                or exact_decimal(change.get("size")) < 0):
                            raise ValueError("invalid stream delta")
                        uint_text(change.get("asset_id"), bits=256)
                    if not any(c["asset_id"] in params["assets_ids"] for c in changes):
                        raise ValueError("stream delta does not concern subscribed token")
                else:
                    return {"value": None, "error": "unsupported_message_type"}
        else:
            raise ValueError("source parser unavailable")
        return {"value": value, "error": None}
    except (ValueError, TypeError, KeyError):
        return {"value": None, "error": "source_schema_invalid"}


def source_parse_artifact(folder, *, create=True):
    """Parse now or read the original complete parse; never overwrite a torn attempt."""
    capture = verify_capture(Path(folder))
    receipt = capture["receipt"]
    source = SOURCES[receipt["source_id"]]
    if receipt["source_version"] != source.version:
        raise ValueError("pinned source parser version unavailable; no current-parser substitution")
    code_manifest = {
        name: _digest(Path(__file__).with_name(name).read_bytes())
        for name in ("source_bridge.py", "source_parsers.py", "types.py")
    }
    implementation_hash = content_hash(code_manifest)
    path = Path(folder) / ("source_parse_" + source.version + "_" + implementation_hash)
    if not path.exists():
        if not create:
            raise ValueError("complete pinned source parse required; read cannot reconstruct it")
        path.mkdir(mode=0o700)
        _sync_directory(path.parent)
        parsed = parse_source(capture)
        payload = {
            "schema_version": BRIDGE_VERSION, "source_version": source.version,
            "implementation_hash": implementation_hash, "code_manifest": code_manifest,
            "capture_id": receipt["capture_id"], "raw_hash": receipt["raw_hash"],
            "generic_ack_hash": _digest((Path(folder) / "parsed_ack.json").read_bytes()),
            "parser_version": source.parser_version + ":" + implementation_hash,
            "result": parsed, "parsed_at": _clock(),
        }
        data = _json_bytes(payload)
        _write_once(path / "source.json", data)
        _write_once(path / "ack.json", _json_bytes({"payload_hash": _digest(data),
                                                   "durable_ack": _clock()}))
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("noncanonical source parse path")
    for name in ("source.json", "ack.json"):
        target = path / name
        if target.is_symlink() or target.stat().st_size > 16 * 1048576:
            raise ValueError("invalid source parse artefact")
    data = (path / "source.json").read_bytes()
    payload, ack = json.loads(data), json.loads((path / "ack.json").read_bytes())
    if (
        ack["payload_hash"] != _digest(data)
        or payload["source_version"] != source.version
        or payload["implementation_hash"] != implementation_hash
        or payload["code_manifest"] != code_manifest
        or payload["capture_id"] != receipt["capture_id"]
        or payload["raw_hash"] != receipt["raw_hash"]
        or payload["schema_version"] != BRIDGE_VERSION
        or payload["generic_ack_hash"] != _digest((Path(folder) / "parsed_ack.json").read_bytes())
        or not (_time(capture["parsed_ack"]["durable_ack"])
                <= _time(payload["parsed_at"]) <= _time(ack["durable_ack"]))
    ):
        raise ValueError("source parse integrity/clock mismatch")
    return capture, payload, ack, path


def _record(entity, provenance, values):
    result = {k: None for k, spec in FIELD_SPECS[entity].items() if spec["nullable"] == "true"}
    result.update(schema_version=CONTRACT, provenance_class=provenance, **values)
    result["missing_fields"] = {
        key: "not_supported" for key, value in result.items() if value is None
    }
    for key in ("supersedes_id", "revision_of", "legacy_reference", "verified_observation_id"):
        if key in result["missing_fields"]:
            result["missing_fields"][key] = "not_applicable"
    return result


async def import_diagnostic_capture(url, folder):
    """Local explicit DB target only. Retry with the same untouched folder is idempotent.

    Register the immutable source contract, then its observation, then a separately
    versioned runtime verification. A crash between steps leaves valid append-only
    evidence, and a retry completes the remaining links. No cyclic registry/observation FK.
    """
    # Reject a nonlocal DB before even creating a source-parse artefact.
    from .migrations import check, validate_local_url

    validate_local_url(url)
    if not (await check(url))["current"]:
        raise ValueError("current guarded local schema required before source import")
    capture, parsed, ack, path = source_parse_artifact(folder)
    receipt = capture["receipt"]
    kind = receipt["capture_kind"]
    if kind not in {"synthetic", "live_diagnostic"}:
        raise ValueError("unsupported diagnostic capture provenance")
    provenance = "synthetic" if kind == "synthetic" else "reconstructed"
    source = SOURCES[receipt["source_id"]]
    registry_version = content_hash({"contract": source.version,
                                     "implementation": parsed["implementation_hash"]})
    registry = _record("source_registry", provenance, {
        "source_id": source.source_id, "registry_version": registry_version,
        "endpoint": source.endpoint, "parser_version": parsed["parser_version"],
        "protocol_version": source.protocol, "access_state": "documented_only",
        "clock_semantics": {"description": source.clock_semantics},
        "unit_conventions": {"description": source.units},
        "schema_hash": content_hash({"parser": parsed["parser_version"], "source": source.version}),
        "rights_state": "restricted",
        "rights_evidence": {"documentation": source.documentation, "scope": source.rights_scope,
                            "allowed_uses": ["source_verification"],
                            "model_feature_admission": False},
    })
    registry = (await append_batch(url, [("source_registry", registry)]))[0]
    available = max(_time(ack["durable_ack"]), registry["recorded_at"])
    # The immutable source-specific result is already durable, and the registry append
    # has returned. This is reconstructed diagnostic availability, not a live bypass.
    observation = _record("source_observation", provenance, {
        "source_registry_id": registry["id"], "source_id": source.source_id,
        "parser_version": parsed["parser_version"], "protocol_version": source.protocol,
        "request_id": receipt["capture_id"], "receipt_ordinal": receipt["receipt_ordinal"],
        "first_received_at": _time(receipt["first_received"]),
        "receipt_monotonic_ns": receipt["first_received"]["monotonic_ns"],
        "clock_session_id": receipt["first_received"]["clock_session_id"],
        "ingested_at": _time(capture["raw_ack"]["durable_ack"]),
        "parsed_at": _time(parsed["parsed_at"]), "available_to_model_at": available,
        "availability_evidence_ids": [], "missing_reason": (
            "observed" if parsed["result"]["error"] is None else
            "permission_denied" if receipt["status"] in {401, 403} else
            "rate_limited" if receipt["status"] == 429 else
            "transport_gap" if receipt["transport_error"] is not None else
            "source_error" if receipt["status"] is None or receipt["status"] >= 500 else "invalid"
        ),
        "quality_assessment_state": "checked",
        "quality_flags": ["diagnostic_not_research_admitted", "clock_uncertainty_unknown"],
        "native_clock_details": {"status": "raw_preserved; source-specific result linked",
                                 "source_parse_hash": ack["payload_hash"]},
        "payload_encoding": "base64", "payload_hash": receipt["raw_hash"],
        "raw_payload_inline": base64.b64encode(capture["raw"]).decode("ascii"),
        "coverage_definition": "single bounded diagnostic response; total history unknown",
        "request_cursor": receipt["request"]["params"].get("cursor"),
        "request_metadata": {"request": receipt["request"], "source_parse_uri": str(path),
                             "source_parse_hash": ack["payload_hash"],
                             "receipt_hash": capture["raw_ack"]["receipt_hash"],
                             "capture_uri": str(folder), "bridge_version": BRIDGE_VERSION,
                             "status": receipt["status"], "parse_error": parsed["result"]["error"]},
    })
    for field in ("source_event_at", "source_published_at", "raw_timestamp", "timestamp_unit"):
        observation["missing_fields"][field] = "not_requested"
    observation["missing_fields"]["raw_payload_uri"] = "not_applicable"
    observation = (await append_batch(url, [("source_observation", observation)]))[0]
    verification = None
    if parsed["result"]["error"] is None:
        revision = dict(registry)
        for field in ("id", "recorded_at"):
            revision.pop(field)
        revision.update(
            registry_version=content_hash({
                "registry": registry_version, "observed": observation["id"],
            }),
            access_state="runtime_verified", verified_observation_id=observation["id"],
            supersedes_id=registry["id"],
        )
        revision["missing_fields"] = {
            key: value for key, value in revision["missing_fields"].items()
            if key not in {"supersedes_id", "verified_observation_id"}
        }
        verification = (await append_batch(url, [("source_registry", revision)]))[0]
    return {"registry": registry, "observation": observation, "verification": verification}
