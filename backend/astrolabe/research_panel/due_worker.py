"""Synthetic due observations over durable origins; no live or SQL admission."""

import asyncio
import hashlib
import math
import re
import shutil
import time
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal, localcontext
from pathlib import Path

import httpx

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import (
    Budget,
    _clock,
    _json_bytes,
    _sync_directory,
    verify_capture,
)
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_quota import quota_policy
from astrolabe.feature_store.source_run import (
    TARGETED_POLICY,
    SourceRun,
    _ordered_clocks,
    _pair,
    _persist,
)
from astrolabe.feature_store.sources import SOURCES

from .activation import allocation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .origin_worker import read_origin_run
from .origin_worker import run_root as origin_run_root
from .panel_declaration import PanelProtocol, read_panel_declaration
from .quote_computation import (
    CHILD,
    computation_limits,
    read_quote_computation,
    record_quote_computation,
)
from .quote_inputs import QuoteInputPolicy, _at
from .target_adapter import adapt_target_quote
from .targets import Quote, select_target

VERSION = "fs2-synthetic-due-worker-v1"
SOURCE = "fs2_capture_target"
COMPUTATION = "fs2_quote_computation_target"
POLICY = {
    "live_collection_enabled": False,
    "origin_admitted": False,
    "accepted_panel": False,
    "top_bytes": 32 * 1048576,
    "artifact_bytes": 16 * 1048576,
    "attempt_metadata_bytes": 131072,
    "failure_reserve_bytes": 65536,
    "free_reserve_bytes": 2 * 1024**3,
    "max_snapshot_seconds": 60,
    "max_files_per_attempt": 160,
    "max_attempts": 16384,
    "attempt_offsets": "floor(index*tolerance/attempt_count)",
    "incomplete_evidence_blocks_selection": True,
}


def run_root(panel):
    return origin_run_root(panel).with_name(
        "fs2_target_run_" + _canonical(panel).name.removeprefix("fs2_panel_")
    )


def _size(root, attempt=False):
    files = []
    for p in root.iterdir():
        if p.is_symlink():
            raise ValueError("target symlink refused")
        if p.is_dir():
            valid = (
                p.name in {SOURCE, COMPUTATION}
                if attempt
                else re.fullmatch("[0-9a-f]{64}", p.name) is not None
            )
            if not valid:
                raise ValueError("unexpected target child")
        elif p.is_file():
            files.append(p)
        else:
            raise ValueError("unexpected target file type")
    if len(files) > 10 or any(p.stat().st_size > POLICY["artifact_bytes"] for p in files):
        raise ValueError("target metadata file bound exceeded")
    return sum(p.stat().st_size for p in files)


def _save(root, name, payload, *, attempt=False, final=False):
    size = len(_json_bytes(payload)) + 4096
    ceiling = POLICY["attempt_metadata_bytes" if attempt else "top_bytes"]
    if not final:
        ceiling -= POLICY["failure_reserve_bytes"]
    if size > POLICY["artifact_bytes"] or _size(root, attempt) + size > ceiling:
        raise ValueError("target metadata byte budget exceeded")
    if shutil.disk_usage(root).free < POLICY["free_reserve_bytes"] + size:
        raise ValueError("target free-space reserve reached")
    _persist(root, name, payload)


def _inventory(root, ceiling):
    started, total, records, pending = time.monotonic(), 0, [], [root]
    while pending:
        folder = pending.pop()
        for p in sorted(folder.iterdir()):
            relative = p.relative_to(root)
            if folder == root and p.name in {"target_receipt.json", "target_receipt_ack.json"}:
                continue
            if p.is_symlink() or len(relative.parts) > 4:
                raise ValueError("target evidence path/depth differs")
            if p.is_dir():
                pending.append(p)
                if len(pending) > 32:
                    raise ValueError("target evidence directory bound exceeded")
                continue
            if not p.is_file() or len(records) >= POLICY["max_files_per_attempt"]:
                raise ValueError("target evidence file bound exceeded")
            size = p.stat().st_size
            total += size
            if total > ceiling:
                raise ValueError("target evidence byte budget exceeded")
            digest = hashlib.sha256()
            with p.open("rb") as handle:
                while chunk := handle.read(65536):
                    if time.monotonic() - started > POLICY["max_snapshot_seconds"]:
                        raise ValueError("target evidence deadline exceeded")
                    digest.update(chunk)
            if p.stat().st_size != size:
                raise ValueError("target evidence changed during snapshot")
            records.append({"path": str(relative), "bytes": size, "sha256": digest.hexdigest()})
    return sorted(records, key=lambda r: r["path"])


def _origins(panel, summary):
    records = []
    for result in summary["results"]:
        root = origin_run_root(panel) / result["intent_id"]
        intent, _ = _pair(root, "origin_intent")
        receipt, receipt_ack = _pair(root, "origin_receipt")
        intent_file = next(r for r in receipt["inventory"] if r["path"] == "origin_intent.json")
        if (
            receipt_ack["payload_hash"] != result["receipt_hash"]
            or hashlib.sha256(_json_bytes(intent)).hexdigest() != intent_file["sha256"]
        ):
            raise ValueError("origin intent/receipt changed during actual consumption")
        facts = None
        if result["origin_hash"] is not None:
            facts, facts_ack = _pair(root, "origin_facts")
            if facts_ack["payload_hash"] != result["origin_hash"]:
                raise ValueError("origin facts changed during actual consumption")
        records.append(
            {
                "result": result,
                "member": intent["member"],
                "facts": facts,
                "origin_persisted_at": receipt_ack["durable_ack"],
            }
        )
    return records


def _schedule(origins, protocol):
    jobs = []
    for origin in origins:
        oid = origin["result"]["intent_id"]
        # Ineligible origins still own all declared attempt slots, without invented origin times.
        due = (
            _time(origin["facts"]["origin_at"]) + timedelta(seconds=protocol.horizon_seconds)
            if origin["facts"] is not None
            else None
        )
        for i in range(protocol.target_attempts):
            scheduled = (
                due + timedelta(seconds=i * protocol.tolerance_seconds // protocol.target_attempts)
                if due
                else None
            )
            value = {
                "origin_id": oid,
                "attempt_index": i,
                "scheduled_at": scheduled.isoformat() if scheduled else None,
                "deadline_at": (due + timedelta(seconds=protocol.tolerance_seconds)).isoformat()
                if due
                else None,
            }
            jobs.append({**value, "attempt_id": content_hash(value)})
    if len(jobs) > POLICY["max_attempts"]:
        raise ValueError("target attempt count exceeds declared bound")
    return sorted(jobs, key=lambda j: (j["scheduled_at"] or "", j["origin_id"], j["attempt_index"]))


def _budget(protocol, job, at):
    remaining = (_at(job["deadline_at"]) - _time(at)).total_seconds()
    if remaining < 0:
        return None
    seconds = max(1, math.ceil(remaining))
    return Budget(
        requests=2,
        bytes_per_response=protocol.source_response_bytes,
        total_bytes=2 * protocol.source_response_bytes,
        seconds_per_request=min(15, seconds),
        total_seconds=min(180, seconds),
    )


def _ceiling(panel_policy):
    return (
        panel_policy["protocol"]["source_run_retained_bytes"]
        + computation_limits(panel_policy.get("computation_storage_profile"))["max_output_bytes"]
        + POLICY["attempt_metadata_bytes"]
    )


def _adapt(root, origin, panel_policy, intent_ack):
    protocol = PanelProtocol(**panel_policy["protocol"])
    summary = read_quote_computation(root / COMPUTATION)
    facts, _ = _pair(root / COMPUTATION, "quote_facts")
    policy, _ = _pair(root / COMPUTATION, "quote_policy")
    source, source_ack = _pair(root / SOURCE, "run")
    intent, _ = _pair(root, "target_intent")
    inputs, _ = _pair(root / COMPUTATION / CHILD, "read_facts")
    rows = sorted(
        (r for k, r in inputs["source_projection"]["rows"] if k == "source_observation"),
        key=lambda r: r["receipt_ordinal"],
    )
    member = origin["member"]
    requests = [
        ("gamma.market", {"market_id": member["market_id"]}),
        ("clob.book", {"token_id": member["token_id"]}),
    ]
    if (
        len(rows) != 2
        or source["policy"] != TARGETED_POLICY
        or source["budget"] != intent["source_budget"]
        or source["retention_quota"] != quota_policy(protocol.source_run_retained_bytes)
        or source["provenance_class"] != "synthetic"
        or policy["source_root"] != str(root / SOURCE)
        or policy["limits"].get("storage_profile")
        != panel_policy.get("computation_storage_profile")
        or policy["quote_policy"]
        != asdict(
            QuoteInputPolicy(protocol.max_quote_age_seconds, protocol.max_identity_age_seconds)
        )
        or not _ordered_clocks(intent_ack["durable_ack"], source_ack["durable_ack"])
    ):
        raise ValueError("target source/computation binding differs")
    for row, (source_id, params) in zip(rows, requests, strict=True):
        capture = verify_capture(Path(row["request_metadata"]["capture_uri"]))
        capture_started = capture["receipt"]["request_started"]
        if (
            row["source_id"] != source_id
            or row["request_metadata"]["request"] != SOURCES[source_id].request(params)
            or _time(capture_started) > _at(intent["job"]["deadline_at"])
            or not _ordered_clocks(intent_ack["durable_ack"], capture_started)
        ):
            raise ValueError("target fixed request or deadline differs")
    adapted = adapt_target_quote(
        origin["facts"]["projection"]["quote"],
        origin_at=origin["facts"]["origin_at"]["utc"],
        source_rows=rows,
        projection=facts["projection"],
        computation_available_at=summary["computation_available_at"]["utc"],
    )
    return {"computation": summary, "adaptation": adapted}


async def _collect_one(root, job, origin, panel_policy, transport):
    protocol = PanelProtocol(**panel_policy["protocol"])
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        at = _clock()
        eligible = origin["result"]["state"] == "observed"
        budget = _budget(protocol, job, at) if eligible else None
        _save(
            root,
            "target_intent",
            {
                "schema_version": VERSION,
                "job": job,
                "origin_result": origin["result"],
                "created_at": at,
                "source_budget": asdict(budget) if budget else None,
            },
            attempt=True,
        )
        _, intent_ack = _pair(root, "target_intent")
        if not eligible or budget is None:
            _save(
                root,
                "target_skip",
                {"state": "origin_ineligible" if not eligible else "expired", "at": _clock()},
                attempt=True,
            )
        else:
            source = SourceRun(
                root / SOURCE,
                budget=budget,
                transport=transport,
                policy_version=TARGETED_POLICY["version"],
                retained_bytes=protocol.source_run_retained_bytes,
            )
            for sid, params in [
                ("gamma.market", {"market_id": origin["member"]["market_id"]}),
                ("clob.book", {"token_id": origin["member"]["token_id"]}),
            ]:
                if _budget(protocol, job, _clock()) is None:
                    raise TimeoutError("target deadline before next source request")
                await source.fetch(sid, params)
            record_quote_computation(
                root / SOURCE,
                output_root=root / COMPUTATION,
                policy=QuoteInputPolicy(
                    protocol.max_quote_age_seconds, protocol.max_identity_age_seconds
                ),
                storage_profile=panel_policy.get("computation_storage_profile"),
            )
            read_started = _clock()
            projection = _adapt(root, origin, panel_policy, intent_ack)
            _save(
                root,
                "target_facts",
                {
                    "schema_version": VERSION,
                    "intent_hash": intent_ack["payload_hash"],
                    "read_started_at": read_started,
                    "computed_at": _clock(),
                    "projection": projection,
                    "feature_store_admitted": False,
                },
                attempt=True,
            )
    except (ValueError, OSError, TimeoutError) as exc:
        _save(
            root,
            "target_failure",
            {"exception_type": type(exc).__name__, "at": _clock()},
            attempt=True,
            final=True,
        )
    _save(
        root,
        "target_receipt",
        {"inventory": _inventory(root, _ceiling(panel_policy)), "completed_at": _clock()},
        attempt=True,
        final=True,
    )
    return _read_one(root, job, origin, panel_policy)


def _read_one(root, job, origin, panel_policy):
    protocol = PanelProtocol(**panel_policy["protocol"])
    receipt, receipt_ack = _pair(root, "target_receipt")
    intent, intent_ack = _pair(root, "target_intent")
    eligible = origin["result"]["state"] == "observed"
    budget = _budget(protocol, job, intent["created_at"]) if eligible else None
    if (
        receipt["inventory"] != _inventory(root, _ceiling(panel_policy))
        or _size(root, True) > POLICY["attempt_metadata_bytes"]
        or intent["schema_version"] != VERSION
        or intent["job"] != job
        or intent["origin_result"] != origin["result"]
        or intent["source_budget"] != (asdict(budget) if budget else None)
        or not _ordered_clocks(
            origin["origin_persisted_at"],
            intent["created_at"],
            intent_ack["durable_ack"],
            receipt["completed_at"],
            receipt_ack["durable_ack"],
        )
        or eligible
        and _time(intent["created_at"]) < _at(job["scheduled_at"])
    ):
        raise ValueError("target intent/inventory/chronology differs")
    projection = None
    if (root / "target_failure.json").exists():
        failure, ack = _pair(root, "target_failure")
        if not _ordered_clocks(
            intent_ack["durable_ack"], failure["at"], ack["durable_ack"], receipt["completed_at"]
        ):
            raise ValueError("target failure chronology differs")
        state = "incomplete_evidence"
    elif (root / "target_skip.json").exists():
        skip, ack = _pair(root, "target_skip")
        expected = "origin_ineligible" if not eligible else "expired"
        if (
            skip["state"] != expected
            or eligible
            and budget is not None
            or (root / SOURCE).exists()
            or (root / COMPUTATION).exists()
            or not _ordered_clocks(
                intent_ack["durable_ack"], skip["at"], ack["durable_ack"], receipt["completed_at"]
            )
        ):
            raise ValueError("target skip state/chronology differs")
        state = skip["state"]
    else:
        if not eligible or budget is None:
            raise ValueError("target observations require eligible nonexpired intent")
        facts, ack = _pair(root, "target_facts")
        projection = _adapt(root, origin, panel_policy, intent_ack)
        if (
            facts["schema_version"] != VERSION
            or facts["intent_hash"] != intent_ack["payload_hash"]
            or facts["feature_store_admitted"] is not False
            or _json_bytes(facts["projection"]) != _json_bytes(projection)
            or not _ordered_clocks(
                intent_ack["durable_ack"],
                projection["computation"]["computation_available_at"],
                facts["read_started_at"],
                facts["computed_at"],
                ack["durable_ack"],
                receipt["completed_at"],
            )
        ):
            raise ValueError("target exact facts or consumption chronology differs")
        state = "recorded"
    return {
        "attempt_id": job["attempt_id"],
        "origin_id": job["origin_id"],
        "state": state,
        "receipt_hash": receipt_ack["payload_hash"],
        "available_at": receipt_ack["durable_ack"],
        "projection": projection,
    }


def _outcomes(origins, attempts, protocol, as_of):
    results = []
    for origin in origins:
        oid = origin["result"]["intent_id"]
        rows = [a for a in attempts if a["origin_id"] == oid]
        blocked = [a["attempt_id"] for a in rows if a["state"] == "incomplete_evidence"]
        target, change = None, None
        if origin["result"]["state"] != "observed":
            state = "origin_ineligible"
        elif blocked:
            state = "incomplete_evidence"
        else:
            quotes = []
            for row in rows:
                if row["projection"] is None:
                    continue
                data = row["projection"]["adaptation"]["quote"]
                data = {
                    **data,
                    **{
                        k: _at(data[k])
                        for k in ("received_at", "available_at", "mapping_available_at")
                    },
                }
                # Adaptation and its retained evidence are not usable before their own
                # durable receipt. Keep the earlier computation time in the projection.
                data["available_at"] = max(data["available_at"], _time(row["available_at"]))
                quotes.append(Quote(**data))
            target = select_target(
                quotes,
                token_id=origin["member"]["token_id"],
                origin_at=_time(origin["facts"]["origin_at"]),
                origin_persisted_at=_time(origin["origin_persisted_at"]),
                horizon_seconds=protocol.horizon_seconds,
                tolerance_seconds=protocol.tolerance_seconds,
                as_of=_time(as_of),
            )
            state = target["status"]
            if target["selected"] is not None:
                before = Decimal(origin["facts"]["projection"]["quote"]["midpoint"])
                after = Decimal(target["selected"]["midpoint"])
                digits = max(
                    len(v.as_tuple().digits) + v.as_tuple().exponent for v in (before, after)
                )
                digits -= min(v.as_tuple().exponent for v in (before, after))
                with localcontext() as ctx:
                    ctx.prec = max(32, digits + 4)
                    change = str(after - before)
        results.append(
            {
                "origin_id": oid,
                "state": state,
                "target": target,
                "blocking_attempt_ids": blocked,
                "midpoint_change": change,
                "economic_value_claim": False,
                "feature_store_admitted": False,
            }
        )
    return results


async def exercise_targets(panel_root, *, transport):
    if type(transport) is not httpx.MockTransport:
        raise ValueError("synthetic MockTransport required; live due collection remains closed")
    panel, root = _canonical(panel_root), run_root(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, "panel_policy")
    protocol = PanelProtocol(**panel_policy["protocol"])
    if root.exists():
        raise FileExistsError("target run retained; no resume or reschedule")
    reserved = allocation(declaration)["required_free_bytes"] + POLICY["top_bytes"]
    if shutil.disk_usage(root.parent).free < reserved:
        raise ValueError("insufficient full target reservation")
    build = verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(
            root,
            "target_policy",
            {
                "schema_version": VERSION,
                "policy": POLICY,
                "build": build,
                "panel_root": str(panel),
                "declaration_hash": declaration["declaration_hash"],
                "required_free_bytes": reserved,
                "declared_at": _clock(),
            },
        )
        read_started = _clock()
        summary = read_origin_run(panel)
        origins = _origins(panel, summary)
        jobs = _schedule(origins, protocol)
        _save(
            root,
            "target_plan",
            {
                "origin_report_hash": summary["worker_report_hash"],
                "origins": origins,
                "jobs": jobs,
                "read_started_at": read_started,
                "read_at": _clock(),
            },
        )
        by_id = {o["result"]["intent_id"]: o for o in origins}
        attempts = []
        for job in jobs:
            origin = by_id[job["origin_id"]]
            if origin["result"]["state"] == "observed":
                remaining = (_at(job["scheduled_at"]) - _time(_clock())).total_seconds()
                if remaining > 0:
                    await asyncio.sleep(remaining)
            attempts.append(
                await _collect_one(root / job["attempt_id"], job, origin, panel_policy, transport)
            )
        # Do not label an unobserved open tolerance window unavailable.
        deadlines = [
            _at(j["deadline_at"])
            for j in jobs
            if by_id[j["origin_id"]]["result"]["state"] == "observed"
        ]
        remaining = (max(deadlines) - _time(_clock())).total_seconds() if deadlines else 0
        if remaining > 0:
            await asyncio.sleep(remaining)
        cutoff = _clock()
        outcomes = _outcomes(origins, attempts, protocol, cutoff)
        if verified_panel_build() != build:
            raise ValueError("target worker build changed")
        _save(
            root,
            "target_report",
            {
                "schema_version": VERSION,
                "as_of": cutoff,
                "attempts": [{k: v for k, v in a.items() if k != "projection"} for a in attempts],
                "outcomes": outcomes,
                "finished_at": _clock(),
                "provenance_class": "synthetic",
                "accepted_panel": False,
                "feature_store_admitted": False,
            },
        )
        return read_target_run(panel)
    except BaseException as exc:
        try:
            _save(
                root,
                "target_worker_failure",
                {"exception_type": type(exc).__name__, "at": _clock()},
                final=True,
            )
        except (ValueError, OSError):
            pass
        raise


def read_target_run(panel_root):
    panel, root = _canonical(panel_root), run_root(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, "panel_policy")
    protocol = PanelProtocol(**panel_policy["protocol"])
    policy, policy_ack = _pair(root, "target_policy")
    plan, plan_ack = _pair(root, "target_plan")
    report, report_ack = _pair(root, "target_report")
    summary = read_origin_run(panel)
    origins = _origins(panel, summary)
    jobs = _schedule(origins, protocol)
    expected = {
        name + suffix
        for name in ("target_policy", "target_plan", "target_report")
        for suffix in (".json", "_ack.json")
    } | {j["attempt_id"] for j in jobs}
    if (
        set(p.name for p in root.iterdir()) != expected
        or _size(root) > POLICY["top_bytes"]
        or policy["schema_version"] != VERSION
        or policy["policy"] != POLICY
        or policy["build"] != verified_panel_build()
        or policy["panel_root"] != str(panel)
        or policy["declaration_hash"] != declaration["declaration_hash"]
        or policy["required_free_bytes"]
        != allocation(declaration)["required_free_bytes"] + POLICY["top_bytes"]
        or plan["origin_report_hash"] != summary["worker_report_hash"]
        or not _ordered_clocks(summary["worker_available_at"], plan["read_at"])
        or _json_bytes(plan["origins"]) != _json_bytes(origins)
        or plan["jobs"] != jobs
        or not _ordered_clocks(
            policy["declared_at"],
            policy_ack["durable_ack"],
            plan["read_started_at"],
            plan["read_at"],
            plan_ack["durable_ack"],
            report["as_of"],
            report["finished_at"],
            report_ack["durable_ack"],
        )
    ):
        raise ValueError("target policy/origin/schedule/chronology differs")
    by_id = {o["result"]["intent_id"]: o for o in origins}
    attempts = []
    for job in jobs:
        child = root / job["attempt_id"]
        intent, _ = _pair(child, "target_intent")
        if not _ordered_clocks(plan_ack["durable_ack"], intent["created_at"]):
            raise ValueError("target intent precedes durable origin read")
        attempt = _read_one(child, job, by_id[job["origin_id"]], panel_policy)
        if not _ordered_clocks(attempt["available_at"], report["as_of"]):
            raise ValueError("target final cutoff precedes consumed attempts")
        attempts.append(attempt)
    if (
        report["schema_version"] != VERSION
        or report["provenance_class"] != "synthetic"
        or report["accepted_panel"] is not False
        or report["feature_store_admitted"] is not False
        or report["attempts"]
        != [{k: v for k, v in a.items() if k != "projection"} for a in attempts]
        or _json_bytes(report["outcomes"])
        != _json_bytes(_outcomes(origins, attempts, protocol, report["as_of"]))
    ):
        raise ValueError("target outcome replay differs")
    return {
        **report,
        "report_hash": report_ack["payload_hash"],
        "report_available_at": report_ack["durable_ack"],
    }
