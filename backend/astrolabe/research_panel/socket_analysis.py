"""Actual read/computation of socket receipt diagnostics, never a source-admission shortcut."""

import shutil
import time
from dataclasses import asdict

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _digest, _sync_directory, verify_capture
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist
from astrolabe.feature_store.types import canonical_json

from .build_identity import verified_panel_build
from .input_read import _canonical
from .socket_window_journal import LIMITS as SOCKET_LIMITS
from .socket_window_journal import read_socket_window
from .window_computation import LIMITS, _check, _save
from .window_coverage import WindowCoveragePolicy, _Projection
from .window_reconciliation import WindowReconciliationPolicy, _book, _endpoints

VERSION = "fs2-socket-analysis-v1"


def dependencies(socket_root, post_root):
    socket = _canonical(socket_root)
    policy, _ = _pair(socket, "socket_window_policy")
    pre = _canonical(policy["pre_computation_root"])
    roots = [socket, pre]
    if post_root is not None:
        roots.append(_canonical(post_root))
    for root in tuple(roots[1:]):
        declaration, _ = _pair(root, "book_policy")
        roots.append(_canonical(declaration["source_root"]))
    return roots


def _paths(socket_root, post_root, output_root):
    roots, root = dependencies(socket_root, post_root), _canonical(output_root)
    if not root.name.startswith("fs2_socket_analysis_") or any(
        root == p or p in root.parents or root in p.parents for p in roots
    ):
        raise ValueError("separate socket analysis outside all transitive dependencies required")
    return roots, root


def _post(root):
    if root is None:
        return None, {"snapshots": [], "source_inventory": []}, []
    summary, projection, rows = _book(root)
    declaration, _ = _pair(root, "book_policy")
    source = _canonical(declaration["source_root"])
    receipts = []
    for row in rows:
        path = _canonical(row["request_metadata"]["capture_uri"])
        if path.parent != source:
            raise ValueError("post receipt outside source")
        capture = verify_capture(path)
        receipt = capture["receipt"]
        if (
            capture["raw_ack"]["receipt_hash"] != row["request_metadata"]["receipt_hash"]
            or receipt["raw_hash"] != row["payload_hash"]
            or receipt["source_id"] != row["source_id"]
            or receipt["capture_id"] != row["request_id"]
            or receipt["request"] != row["request_metadata"]["request"]
        ):
            raise ValueError("post receipt differs from verified input")
        receipts.append(
            {
                "observation_id": row["id"],
                "source_id": row["source_id"],
                "receipt_hash": capture["raw_ack"]["receipt_hash"],
                "request": receipt["request"],
                "request_started": receipt["request_started"],
                "first_received": receipt["first_received"],
                "raw_available_at": capture["raw_ack"]["durable_ack"],
                "missing_reason": row["missing_reason"],
            }
        )
    return summary, projection, receipts


def _load(socket_root, post_root):
    socket = read_socket_window(socket_root)
    declaration, _ = _pair(socket_root, "socket_window_policy")
    binding, _ = _pair(socket_root, "socket_window_binding")
    pre_summary, pre, _ = _book(_canonical(declaration["pre_computation_root"]))
    if pre_summary != binding["binding"]["pre_computation"]:
        raise ValueError("socket prior computation changed during read")
    post_summary, post, receipts = _post(post_root)
    if post_summary and post_summary["source_provenance_class"] != socket["provenance_class"]:
        raise ValueError("socket/post provenance mismatch")
    events, manifest, previous = [], [], None
    for ordinal in range(1, socket["event_count"] + 1):
        name = f"event_{ordinal:06d}"
        event, ack = _pair(socket_root, name)
        raw = None
        if event["raw_state"] == "observed":
            path = socket_root / (name + ".bin")
            if path.is_symlink() or path.stat().st_size > SOCKET_LIMITS["max_frame_bytes"]:
                raise ValueError("bounded nonsymlink socket raw required")
            raw = path.read_bytes()
            if _digest(raw) != event["raw_hash"] or len(raw) != event["raw_bytes"]:
                raise ValueError("socket raw changed during read")
        if event["previous_hash"] != previous or event["ordinal"] != ordinal:
            raise ValueError("socket event chain changed during read")
        previous = ack["payload_hash"]
        events.append({"event": event, "ack": ack, "raw": raw})
        manifest.append(
            {
                "event_hash": previous,
                "durable_ack": ack["durable_ack"],
                "raw_hash": event["raw_hash"],
            }
        )
    if previous != socket["last_event_hash"] or read_socket_window(socket_root) != socket:
        raise ValueError("socket changed during consumption")
    inputs = {
        "socket": socket,
        "socket_policy": declaration,
        "pre_computation": pre_summary,
        "post_computation": post_summary,
        "post_receipts": receipts,
        "input_manifest_hash": content_hash(manifest),
    }
    return inputs, (pre, post, events)


def _project(inputs, material, policy, at):
    pre, post, events = material
    socket = inputs["socket"]
    coverage = reconciliation = None
    if socket["subscription_sent_at"] is not None:
        source_policy = {
            **{k: socket["identity"][k] for k in ("token_id", "condition_id")},
            "duration_ms": inputs["socket_policy"]["duration_ms"],
        }
        summary = {**socket, "window_report_hash": socket["socket_window_report_hash"]}
        engine = _Projection(
            source_policy, summary, WindowCoveragePolicy(policy.max_receipt_hold_ms)
        )
        started = time.monotonic()
        for entry in events:
            if time.monotonic() - started > LIMITS["max_seconds"]:
                raise ValueError("socket coverage processing deadline exceeded")
            engine.frame(entry)
        result = engine.result()
        result.update(
            schema_version="fs2-socket-receipt-coverage-v1",
            identity_state="verified_prior_source_local_binding",
            source_admitted=False,
            socket_terminal=socket["terminal"],
            socket_close_state=socket["close_state"],
        )
        coverage = {**result, "projection_hash": content_hash(result)}
        # This is a new authenticated envelope, not a rewritten or promoted legacy journal.
        # The shared pure endpoint algebra keeps the actual socket report boundary intact.
        bound = {
            "identity": socket["identity"],
            "window": {"ended_at": socket["ended_at"]},
            "provenance_class": socket["provenance_class"],
            "bound_window_available_at": socket["socket_window_available_at"],
            "state": "fresh_at_subscription"
            if socket["source_provenance_compatible"]
            and socket["identity_fresh_at_subscription_completion"]
            else "expired",
        }
        envelope = {
            "bound_window": bound,
            "post_receipts": inputs["post_receipts"],
            "original_identity_available_at": socket["identity_available_at"],
        }
        reconciliation = _endpoints(envelope, pre, post, coverage, policy, at)
        reconciliation["schema_version"] = "fs2-socket-endpoint-reconciliation-v1"
    result = {
        "schema_version": VERSION,
        "coverage": coverage,
        "reconciliation": reconciliation,
        "state": "diagnostics_available" if coverage else "no_subscribed_window",
        "socket_terminal": socket["terminal"],
        "socket_close_state": socket["close_state"],
        "provenance_class": socket["provenance_class"],
        "source_admitted": False,
        "origin_admitted": False,
        "feature_store_admitted": False,
        "continuous_sequence_proven": False,
        "native_clock_admitted": False,
    }
    return {**result, "projection_hash": content_hash(result)}


def record_socket_analysis(socket_root, *, output_root, policy, post_root=None):
    roots, root = _paths(socket_root, post_root, output_root)
    socket_root = roots[0]
    post_root = _canonical(post_root) if post_root is not None else None
    if type(policy) is not WindowReconciliationPolicy:
        raise ValueError("explicit socket analysis policy required")
    if root.exists():
        raise FileExistsError("socket analysis terminal; no overwrite/resume")
    if shutil.disk_usage(root.parent).free < (
        LIMITS["free_reserve_bytes"] + LIMITS["max_output_bytes"]
    ):
        raise ValueError("full socket analysis storage reserve unavailable")
    started, build = time.monotonic(), verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        _save(
            root,
            "socket_analysis_policy",
            {
                "schema_version": VERSION,
                "build": build,
                "limits": dict(LIMITS),
                "socket_root": str(socket_root),
                "post_root": str(post_root) if post_root else None,
                "policy": asdict(policy),
                "declared_at": _clock(),
            },
            started,
        )
        _, pa = _pair(root, "socket_analysis_policy")
        read_started = _clock()
        inputs, material = _load(socket_root, post_root)
        completed = _clock()
        _save(
            root,
            "socket_analysis_input",
            {
                "inputs": inputs,
                "policy_hash": pa["payload_hash"],
                "read_started_at": read_started,
                "read_completed_at": completed,
            },
            started,
        )
        _, ia = _pair(root, "socket_analysis_input")
        compute_started = _clock()
        projection = _project(inputs, material, policy, compute_started)
        completed = _clock()
        _save(
            root,
            "socket_analysis_facts",
            {
                "schema_version": VERSION,
                "policy_hash": pa["payload_hash"],
                "input_hash": ia["payload_hash"],
                "computation_started_at": compute_started,
                "computed_at": completed,
                "projection": projection,
            },
            started,
        )
        return read_socket_analysis(root)
    except BaseException as exc:
        try:
            _persist(
                root,
                "socket_analysis_failure",
                {"exception_type": type(exc).__name__, "at": _clock()},
            )
        except (OSError, ValueError):
            pass
        raise


def read_socket_analysis(root):
    root, started = _canonical(root), time.monotonic()
    expected = {
        name + suffix
        for name in ("socket_analysis_policy", "socket_analysis_input", "socket_analysis_facts")
        for suffix in (".json", "_ack.json")
    }
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError("complete successful socket analysis closure required")
    _check(root, started)
    declaration, pa = _pair(root, "socket_analysis_policy")
    roots, root = _paths(declaration["socket_root"], declaration["post_root"], root)
    policy = WindowReconciliationPolicy(**declaration["policy"])
    if (
        declaration["schema_version"] != VERSION
        or declaration["limits"] != LIMITS
        or declaration["build"] != verified_panel_build()
    ):
        raise ValueError("socket analysis build/policy differs")
    post_root = _canonical(declaration["post_root"]) if declaration["post_root"] else None
    inputs, material = _load(roots[0], post_root)
    saved, ia = _pair(root, "socket_analysis_input")
    facts, fa = _pair(root, "socket_analysis_facts")
    availability = [inputs["socket"]["socket_window_available_at"]]
    if inputs["post_computation"]:
        availability.append(inputs["post_computation"]["computation_available_at"])
    if (
        canonical_json(inputs) != canonical_json(saved["inputs"])
        or saved["policy_hash"] != pa["payload_hash"]
        or facts["schema_version"] != VERSION
        or facts["policy_hash"] != pa["payload_hash"]
        or facts["input_hash"] != ia["payload_hash"]
        or not _ordered_clocks(
            declaration["declared_at"],
            pa["durable_ack"],
            saved["read_started_at"],
            saved["read_completed_at"],
            ia["durable_ack"],
            facts["computation_started_at"],
            facts["computed_at"],
            fa["durable_ack"],
        )
        or any(not _ordered_clocks(v, saved["read_started_at"]) for v in availability)
    ):
        raise ValueError("socket analysis input/chronology differs")
    projection = _project(inputs, material, policy, facts["computation_started_at"])
    if canonical_json(projection) != canonical_json(facts["projection"]):
        raise ValueError("socket analysis exact replay differs")
    if declaration["build"] != verified_panel_build():
        raise ValueError("socket analysis build changed during replay")
    _check(root, started)
    return {
        "schema_version": VERSION,
        "computation_hash": fa["payload_hash"],
        "policy_hash": pa["payload_hash"],
        "projection_hash": projection["projection_hash"],
        "computation_started_at": facts["computation_started_at"],
        "computed_at": facts["computed_at"],
        "computation_available_at": fa["durable_ack"],
        "source_provenance_class": projection["provenance_class"],
        "state": projection["state"],
        "origin_admitted": False,
        "feature_store_admitted": False,
        "source_admitted": False,
    }
