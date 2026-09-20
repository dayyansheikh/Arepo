"""Predeclared bounded source measurement, with the durable journal as authority.

No payload/provenance/clock injection API. Earlier diagnostic directories cannot be
adopted. Synthetic transports keep synthetic provenance through the exact same path.
"""

import asyncio
import base64
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .admission import content_hash, prepare
from .build_identity import verified_build
from .capture import (
    Budget,
    CaptureJournal,
    _clock,
    _digest,
    _json_bytes,
    _write_once,
)
from .source_bridge import _record, _time, source_parse_artifact
from .sources import SOURCES
from .types import utc_datetime

VERSION = "fs2-source-run-v1"
POLICY = {
    "version": "receipt-time-internal-measurement-v1",
    "sources": ["gamma.markets", "clob.book", "data.v2.trades"],
    "allowed_uses": ["bounded_internal_receipt_time_measurement"],
    "native_event_clock_admitted": False,
    "redistribution_admitted": False,
    "historical_event_availability_admitted": False,
    "claim": "documented public read interface; not a redistribution licence or predictive result",
}


def _read(path):
    if path.is_symlink() or path.stat().st_size > 16 * 1048576:
        raise ValueError("invalid measurement artefact")
    return path.read_bytes()


def _pair(folder, name):
    if folder.resolve() != folder:
        raise ValueError("noncanonical measurement artefact directory")
    data = _read(folder / (name + ".json"))
    payload = json.loads(data)
    ack = json.loads(_read(folder / (name + "_ack.json")))
    if ack["payload_hash"] != _digest(data):
        raise ValueError("measurement acknowledgement hash differs")
    if _time(ack["durable_ack"]) > datetime.now(UTC):
        raise ValueError("measurement acknowledgement is in the future")
    return payload, ack


def _ordered_clocks(*clocks):
    return all(
        _time(a) <= _time(b)
        and (a["clock_session_id"] != b["clock_session_id"]
             or int(a["monotonic_ns"]) <= int(b["monotonic_ns"]))
        for a, b in zip(clocks, clocks[1:], strict=False)
    )


def _persist(folder, name, payload):
    data = _json_bytes(payload)
    _write_once(folder / (name + ".json"), data)
    _write_once(folder / (name + "_ack.json"), _json_bytes({
        "payload_hash": _digest(data), "durable_ack": _clock(),
    }))


def _registry(run, ack, source_id):
    source = SOURCES[source_id]
    build_hash = content_hash(run["build"])
    version = content_hash({"run": ack["payload_hash"], "source": source.version})
    facts = _record("source_registry", run["provenance_class"], {
        "source_id": source_id, "registry_version": version,
        "endpoint": source.endpoint, "protocol_version": source.protocol,
        "parser_version": source.parser_version + ":" + build_hash,
        "access_state": "documented_only", "rights_state": "restricted",
        "rights_evidence": {"documentation": source.documentation, "policy": run["policy"],
                            "declared_at": ack["durable_ack"]["utc"],
                            "source_contract_rights_scope": source.rights_scope},
        "clock_semantics": {"description": source.clock_semantics,
                            "analysis_basis": "receipt_time_only; native clock unadmitted"},
        "unit_conventions": {"description": source.units},
        "schema_hash": content_hash({"source": source.version, "build": build_hash}),
    })
    return prepare("source_registry", {**facts, "recorded_at": _time(ack["durable_ack"])})


def _verify_run(root):
    root = Path(root)
    if root.resolve() != root or not root.name.startswith("fs2_capture_"):
        raise ValueError("canonical measurement run directory required")
    run, ack = _pair(root, "run")
    session = json.loads(_read(root / "session.json"))
    if (run["schema_version"] != VERSION or run["policy"] != POLICY
            or run["build"] != verified_build()
            or run["session_hash"] != _digest(_read(root / "session.json"))
            or run["budget"] != asdict(Budget(**session["budget"]))
            or run["sources"] != {k: asdict(SOURCES[k]) for k in POLICY["sources"]}
            or run["provenance_class"] != (
                "synthetic" if session["capture_kind"] == "synthetic" else "prospective")
            or session["capture_kind"] not in {"synthetic", "live_diagnostic"}
            or not _ordered_clocks(session["started"], ack["durable_ack"])):
        raise ValueError("measurement run/build/policy integrity differs")
    return root, run, ack


class SourceRun:
    """Fresh finite measurement; registration is durable before any request can start."""

    def __init__(self, root, *, budget=Budget(), transport=None):
        build = verified_build()
        self.journal = CaptureJournal(root, budget=budget, transport=transport)
        self._lock = asyncio.Lock()
        _persist(self.journal.root, "run", {
            "schema_version": VERSION, "policy": POLICY, "build": build,
            "origin_uri": str(self.journal.root),
            "budget": asdict(budget),
            "provenance_class": "synthetic" if transport is not None else "prospective",
            "session_hash": _digest(_read(self.journal.root / "session.json")),
            "sources": {k: asdict(SOURCES[k]) for k in POLICY["sources"]},
        })

    async def fetch(self, source_id, params, *, previous_capture_id=None):
        async with self._lock:
            root, run, ack = _verify_run(self.journal.root)
            if source_id not in POLICY["sources"]:
                raise ValueError("source outside predeclared measurement policy")
            captured = await self.journal.fetch(source_id, params,
                                                previous_capture_id=previous_capture_id)
            verified_build()
            folder = Path(captured["folder"])
            capture, parsed, parsed_ack, path = source_parse_artifact(folder)
            if not _ordered_clocks(ack["durable_ack"], capture["receipt"]["request_started"]):
                raise ValueError("source request preceded durable run declaration")
            verified_build()
            # Only this run's freshly returned capture is sealed. No old-folder admission API.
            _persist(folder, "admission", {
                "schema_version": VERSION, "run_hash": ack["payload_hash"],
                "capture_id": capture["receipt"]["capture_id"],
                "source_parse_hash": parsed_ack["payload_hash"],
                "source_parse_folder": path.name,
                "ready_at": _clock(),
            })
            return read_source_run(root, capture_id=capture["receipt"]["capture_id"])


def read_source_run(root, *, capture_id=None, cutoff=None):
    """Verify complete primary facts and return their immutable relational projection.

    A cutoff filters journal fact availability, not proof of SQL visibility/model execution.
    Torn attempts refuse the run; there is no silent skip, repair or old diagnostic promotion.
    """
    root, run, run_ack = _verify_run(root)
    cutoff = utc_datetime(cutoff) if cutoff is not None else None
    registries = {k: _registry(run, run_ack, k) for k in POLICY["sources"]}
    rows = [("source_registry", value) for value in registries.values()
            if cutoff is None or value["recorded_at"] <= cutoff]
    seen_ordinals = set()
    folders = sorted(p for p in root.iterdir() if p.is_dir())
    if len(folders) > run["budget"]["requests"]:
        raise ValueError("measurement run exceeds its predeclared request budget")
    if capture_id is not None and capture_id not in {p.name for p in folders}:
        raise ValueError("requested capture is absent from this measurement run")
    total_bytes = 0
    for folder in folders:
        if capture_id is not None and folder.name != capture_id:
            continue
        admission, ack = _pair(folder, "admission")
        capture, parsed, parse_ack, path = source_parse_artifact(folder, create=False)
        receipt = capture["receipt"]
        total_bytes += receipt["raw_bytes"]
        at = _time(ack["durable_ack"])
        if (admission["schema_version"] != VERSION
                or admission["run_hash"] != run_ack["payload_hash"]
                or admission["capture_id"] != receipt["capture_id"]
                or admission["source_parse_hash"] != parse_ack["payload_hash"]
                or admission["source_parse_folder"] != path.name
                or receipt["source_id"] not in registries
                or receipt["receipt_ordinal"] in seen_ordinals
                or not 1 <= receipt["receipt_ordinal"] <= run["budget"]["requests"]
                or receipt["raw_bytes"] > run["budget"]["bytes_per_response"]
                or total_bytes > run["budget"]["total_bytes"]
                or not _ordered_clocks(run_ack["durable_ack"], receipt["request_started"],
                                       parse_ack["durable_ack"], admission["ready_at"],
                                       ack["durable_ack"])):
            raise ValueError("measurement admission chronology/lineage mismatch")
        seen_ordinals.add(receipt["receipt_ordinal"])
        if cutoff is not None and at > cutoff:
            continue
        source = registries[receipt["source_id"]]
        original_folder = str(Path(run["origin_uri"]) / folder.name)
        reason = (
            "observed" if parsed["result"]["error"] is None else
            "permission_denied" if receipt["status"] in {401, 403} else
            "rate_limited" if receipt["status"] == 429 else
            "transport_gap" if receipt["transport_error"] is not None else
            "source_error" if receipt["status"] is None or receipt["status"] >= 500 else "invalid"
        )
        facts = _record("source_observation", run["provenance_class"], {
            "source_registry_id": source["id"], "source_id": source["source_id"],
            "parser_version": source["parser_version"],
            "protocol_version": source["protocol_version"],
            "request_id": receipt["capture_id"], "receipt_ordinal": receipt["receipt_ordinal"],
            "first_received_at": _time(receipt["first_received"]),
            "receipt_monotonic_ns": receipt["first_received"]["monotonic_ns"],
            "clock_session_id": receipt["first_received"]["clock_session_id"],
            "ingested_at": _time(capture["raw_ack"]["durable_ack"]),
            "parsed_at": _time(parsed["parsed_at"]), "available_to_model_at": at,
            "availability_evidence_ids": [], "missing_reason": reason,
            "quality_assessment_state": "checked",
            "quality_flags": ["native_clock_unadmitted", "clock_uncertainty_unknown",
                              "bounded_response_coverage"],
            "native_clock_details": {"status": "raw retained; receipt-time analysis only"},
            "payload_encoding": "base64", "payload_hash": receipt["raw_hash"],
            "raw_payload_inline": base64.b64encode(capture["raw"]).decode("ascii"),
            "coverage_definition": "single bounded response; total source history unknown",
            "request_cursor": receipt["request"]["params"].get("cursor"),
            "request_metadata": {
                "schema_version": VERSION, "run_hash": run_ack["payload_hash"],
                "capture_uri": original_folder,
                "receipt_hash": capture["raw_ack"]["receipt_hash"],
                "source_parse_uri": str(Path(original_folder) / path.name),
                "source_parse_hash": parse_ack["payload_hash"],
                "admission_hash": ack["payload_hash"], "primary_authority": "source_journal",
                "request": receipt["request"], "status": receipt["status"],
                "parse_error": parsed["result"]["error"],
            },
        })
        observation = prepare("source_observation", {**facts, "recorded_at": at})
        rows.append(("source_observation", observation))
        if reason == "observed":
            revision = dict(source)
            revision.pop("id")
            revision.update(
                registry_version=content_hash({"registry": source["id"],
                                               "observation": observation["id"]}),
                recorded_at=at, access_state="runtime_verified",
                verified_observation_id=observation["id"], supersedes_id=source["id"],
            )
            revision["missing_fields"] = {
                k: v for k, v in revision["missing_fields"].items()
                if k not in {"verified_observation_id", "supersedes_id"}
            }
            rows.append(("source_registry", prepare("source_registry", revision)))
    verified_build()
    return rows
