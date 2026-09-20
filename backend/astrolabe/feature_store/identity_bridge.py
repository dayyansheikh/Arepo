"""Evidence-linked diagnostic identity versions; unresolved namespaces stay unresolved."""

from decimal import Decimal
from pathlib import Path

from .admission import content_hash, prepare
from .capture import _clock, _digest, _json_bytes, _strict_json, _sync_directory, _write_once
from .repository import append_batch
from .source_bridge import _record, _time, import_diagnostic_capture, source_parse_artifact
from .source_parsers import native_clock
from .types import canonical_json

IDENTITY_VERSION = "gamma-diagnostic-identities-v1"


def _numbers_as_text(value):
    if isinstance(value, Decimal):
        return str(value)
    if type(value) is int and abs(value) > 2**53 - 1:
        return str(value)
    if isinstance(value, list):
        return [_numbers_as_text(v) for v in value]
    if isinstance(value, dict):
        return {k: _numbers_as_text(v) for k, v in value.items()}
    return value


async def import_gamma_identities(url, folder):
    imported = await import_diagnostic_capture(url, folder)
    observation = imported["observation"]
    if observation["source_id"] != "gamma.markets" or observation["missing_reason"] != "observed":
        raise ValueError("valid captured Gamma identity response required")
    capture, parsed, source_ack, _ = source_parse_artifact(folder)
    implementation_hash = _digest(Path(__file__).read_bytes())
    path = Path(folder) / (IDENTITY_VERSION + "_" + content_hash({
        "implementation": implementation_hash, "source_parse": source_ack["payload_hash"],
    }))
    if not path.exists():
        path.mkdir(mode=0o700)
        _sync_directory(path.parent)
        raw_rows = _strict_json(capture["raw"])
        if len({r["id"] for r in raw_rows}) != len(raw_rows):
            raise ValueError("duplicate market IDs in identity page")
        facts = []
        for raw, identity in zip(raw_rows, parsed["result"]["value"], strict=True):
            if not isinstance(identity["question"], str) or not identity["question"]:
                raise ValueError("market question absent; retain unresolved raw evidence")
            facts.append({
                "identity": identity, "close_raw": raw.get("endDate"),
                "tick_raw": str(raw["orderPriceMinTickSize"])
                if raw.get("orderPriceMinTickSize") is not None else None,
                "lifecycle": {k: raw.get(k) for k in ("active", "closed", "archived",
                                                       "enableOrderBook", "acceptingOrders")},
                "fee_configuration": _numbers_as_text(raw.get("feeSchedule")),
            })
        payload = {"schema_version": IDENTITY_VERSION, "observation_id": observation["id"],
                   "implementation_hash": implementation_hash,
                   "source_parse_hash": source_ack["payload_hash"], "facts": facts,
                   "computed_at": _clock()}
        content = _json_bytes(payload)
        _write_once(path / "identities.json", content)
        _write_once(path / "ack.json", _json_bytes({"payload_hash": _digest(content),
                                                   "durable_ack": _clock()}))
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("noncanonical identity artefact path")
    for name in ("identities.json", "ack.json"):
        file = path / name
        if file.is_symlink() or file.stat().st_size > 16 * 1048576:
            raise ValueError("invalid identity artefact")
    content = (path / "identities.json").read_bytes()
    payload, ack = _strict_json(content), _strict_json((path / "ack.json").read_bytes())
    if (ack["payload_hash"] != _digest(content)
            or payload["observation_id"] != observation["id"]
            or payload["source_parse_hash"] != source_ack["payload_hash"]
            or payload["schema_version"] != IDENTITY_VERSION
            or payload["implementation_hash"] != implementation_hash
            or not (observation["available_to_model_at"] <= _time(payload["computed_at"])
                    <= _time(ack["durable_ack"]))):
        raise ValueError("identity artefact integrity/clock mismatch")
    known_at = _time(ack["durable_ack"])
    provenance = observation["provenance_class"]
    evidence = [observation["id"]]
    rows = []

    def add(entity, values, unresolved=()):
        row = _record(entity, provenance, values)
        for field in unresolved:
            row["missing_fields"][field] = "identity_unresolved"
        # Derive IDs for relationships; actual record time is still writer-owned.
        prepared = prepare(entity, {**row, "recorded_at": known_at})
        rows.append((entity, row))
        return prepared["id"]

    graph_version = content_hash({"definition": IDENTITY_VERSION, "artifact": ack["payload_hash"]})
    for fact in payload["facts"]:
        identity = fact["identity"]
        mapping = content_hash({"artifact": ack["payload_hash"], "identity": identity})
        common = {"mapping_version": mapping, "observed_from_at": known_at,
                  "mapping_evidence_ids": evidence}
        add("condition_identity", {**common, "venue": "polymarket",
                                   "condition_id": identity["condition_id"],
                                   "question_id": identity["question_id"],
                                   "identity_status": "unresolved"},
            ("chain_id", "collateral_address", "collateral_decimals"))
        clock = native_clock(fact["close_raw"], unit="iso8601", received_at=known_at)
        # Source close may legitimately be in the future; it is not a receipt/event clock.
        close_at = clock["value"]
        market_id = add("market_identity_version", {
            **common, "venue": "polymarket", "market_id": identity["market_id"],
            "question": identity["question"], "rules_text": identity["rules_text"],
            "rules_hash": identity["rules_hash"],
            "resolution_source": identity["resolution_source"],
            "event_id": identity["source_event_ids"][0]
            if len(identity["source_event_ids"]) == 1 else None,
            "close_at": close_at, "tick_size": fact["tick_raw"],
            "fee_configuration": fact["fee_configuration"],
            "lifecycle_state": canonical_json(fact["lifecycle"]),
        }, ("condition_identity_id",))
        if fact["close_raw"] is not None and close_at is None:
            rows[-1][1]["missing_fields"]["close_at"] = "invalid"
        for outcome in identity["outcomes"]:
            add("token_outcome_version", {**common, "market_identity_id": market_id, **outcome},
                ("chain_id", "token_contract", "condition_identity_id"))
        group_common = {"member_identity_id": market_id, "group_version": graph_version,
                        "observed_from_at": known_at, "mapping_evidence_ids": evidence,
                        "relationship_type": "related_contract"}
        add("event_group_membership", {**group_common, "mapping_view": "as_known",
                                       "mapping_method": "economic_group_unresolved"},
            ("event_group_id",))
        for event_id in identity["source_event_ids"]:
            add("event_group_membership", {**group_common,
                                           "mapping_view": "conservative_evaluation",
                                           "mapping_method": "source_event_only_v1",
                                           "event_group_id": "gamma:event:" + event_id})
    stored = await append_batch(url, rows)
    return {"records": list(zip([entity for entity, _ in rows], stored, strict=True)),
            "identity_artifact": str(path), "observation_id": observation["id"],
            "graph_version": graph_version, "verified_chain_identity": False}
