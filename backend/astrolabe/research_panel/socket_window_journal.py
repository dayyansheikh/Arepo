"""Versioned socket evidence; receive time is distinct from serialized persistence time."""

import shutil
import time
from dataclasses import asdict

from astrolabe.feature_store.capture import (
    _clock,
    _digest,
    _json_bytes,
    _sync_directory,
    _write_once,
)
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist
from astrolabe.feature_store.types import HASH_PATTERN

from .bound_window import WindowBindingPolicy, _fresh, _pre
from .build_identity import verified_panel_build
from .input_read import _canonical
from .socket_connector import connector_contract

VERSION = "fs2-socket-window-v1"
LIMITS = {
    "max_frames": 1000,
    "max_frame_bytes": 262144,
    "max_raw_bytes": 16 * 1048576,
    "max_retained_bytes": 40 * 1048576,
    "max_metadata_bytes": 2 * 1048576,
    "max_events": 1032,
    "failure_reserve_bytes": 65536,
    "free_reserve_bytes": 2 * 1024**3,
    "max_processing_seconds": 180,
    "heartbeat_interval_ms": 10000,
    "send_timeout_seconds": 1,
}
KINDS = {
    "connect_intent",
    "connected",
    "connect_error",
    "subscription_intent",
    "subscription_sent",
    "subscription_error",
    "received",
    "receive_error",
    "ping_intent",
    "ping_sent",
    "ping_error",
    "interval_ended",
    "budget_stop",
    "refused",
    "close_intent",
    "closed",
    "close_error",
}


def paths(pre_root, output_root):
    pre, root = _canonical(pre_root), _canonical(output_root)
    declaration, _ = _pair(pre, "book_policy")
    dependencies = (pre, _canonical(declaration["source_root"]))
    if not root.name.startswith("fs2_socket_window_") or any(
        root == p or p in root.parents or root in p.parents for p in dependencies
    ):
        raise ValueError("separate socket window outside all pre-evidence required")
    return pre, root


def scope(port):
    if port is None:
        return {
            "kind": "public",
            "endpoint": connector_contract()["endpoint"],
            "provenance_class": "prospective",
            "loopback_port": None,
        }
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("explicit synthetic loopback port required")
    return {
        "kind": "loopback",
        "endpoint": f"ws://127.0.0.1:{port}/ws/market",
        "provenance_class": "synthetic",
        "loopback_port": port,
    }


def check(root, started, addition=0):
    if time.monotonic() - started > LIMITS["max_processing_seconds"]:
        raise ValueError("socket window processing deadline exceeded")
    files = list(root.iterdir())
    if len(files) > 3 * LIMITS["max_events"] + 8:
        raise ValueError("socket window file count exceeded")
    total = 0
    for p in files:
        if p.is_symlink() or not p.is_file():
            raise ValueError("socket window nonfile/symlink refused")
        size = p.stat().st_size
        if size > (
            LIMITS["max_frame_bytes"] if p.suffix == ".bin" else LIMITS["max_metadata_bytes"]
        ):
            raise ValueError("socket window artefact budget exceeded")
        total += size
    if total + addition > LIMITS["max_retained_bytes"] - LIMITS["failure_reserve_bytes"]:
        raise ValueError("socket window retained budget exceeded")
    if addition and shutil.disk_usage(root).free < LIMITS["free_reserve_bytes"] + addition:
        raise ValueError("socket window free reserve reached")


class SocketJournal:
    def __init__(self, pre_root, output_root, policy, duration_ms, port):
        self.pre, self.root = paths(pre_root, output_root)
        if type(policy) is not WindowBindingPolicy:
            raise ValueError("explicit source freshness policy required")
        if type(duration_ms) is not int or not 1 <= duration_ms <= 60000:
            raise ValueError("bounded socket duration required")
        transport = scope(port)
        contract = connector_contract()
        if self.root.exists():
            raise FileExistsError("socket window terminal; no overwrite/resume")
        if shutil.disk_usage(self.root.parent).free < (
            LIMITS["free_reserve_bytes"] + LIMITS["max_retained_bytes"]
        ):
            raise ValueError("full socket storage reservation unavailable")
        self.build, self.started = verified_panel_build(), time.monotonic()
        self.count = self.frames = self.raw_bytes = 0
        self.last_hash = None
        self.root.mkdir(mode=0o700)
        _sync_directory(self.root.parent)
        self.save(
            "socket_window_policy",
            {
                "schema_version": VERSION,
                "limits": dict(LIMITS),
                "build": self.build,
                "connector": contract,
                "transport": transport,
                "pre_computation_root": str(self.pre),
                "binding_policy": asdict(policy),
                "duration_ms": duration_ms,
                "declared_at": _clock(),
            },
        )

    def save(self, name, value):
        size = len(_json_bytes(value))
        if size > LIMITS["max_metadata_bytes"]:
            raise ValueError("socket metadata budget exceeded")
        check(self.root, self.started, size + 4096)
        _persist(self.root, name, value)

    def event(
        self, kind, *, observed=None, raw=None, error=None, operation_started=None, reason=None
    ):
        if kind not in KINDS or self.count >= LIMITS["max_events"]:
            raise ValueError("bounded socket event kind/count required")
        recorded = _clock()
        observed = recorded if observed is None else observed
        name = f"event_{self.count + 1:06d}"
        value = {
            "schema_version": VERSION,
            "ordinal": self.count + 1,
            "kind": kind,
            "observed_at": observed,
            "recorded_at": recorded,
            "operation_started_at": operation_started,
            "previous_hash": self.last_hash,
            "error": error,
            "reason": reason,
            "raw_hash": None,
            "raw_bytes": None,
            "received_hash": None,
            "received_bytes": None,
            "wire_type": None,
            "truncated": False,
            "raw_state": "unavailable" if kind == "receive_error" else "not_applicable",
        }
        if raw is not None:
            if type(raw) not in {str, bytes}:
                raise ValueError("raw wire bytes/text required")
            wire = "text" if isinstance(raw, str) else "binary"
            encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
            kept = encoded[
                : min(LIMITS["max_frame_bytes"], LIMITS["max_raw_bytes"] - self.raw_bytes)
            ]
            check(self.root, self.started, len(kept) + 16384)
            _write_once(self.root / (name + ".bin"), kept)
            value.update(
                raw_hash=_digest(kept),
                raw_bytes=len(kept),
                received_hash=_digest(encoded),
                received_bytes=len(encoded),
                wire_type=wire,
                truncated=len(kept) != len(encoded),
                raw_state="observed",
            )
        self.save(name, value)
        _, ack = _pair(self.root, name)
        self.count += 1
        self.frames += kind == "received"
        self.raw_bytes += value["raw_bytes"] or 0
        self.last_hash = ack["payload_hash"]
        return observed, value["truncated"]

    def failure(self, exc, stage):
        _persist(
            self.root,
            "socket_window_failure",
            {
                "schema_version": VERSION,
                "exception_type": type(exc).__name__,
                "stage": stage,
                "at": _clock(),
            },
        )

    def finish(self):
        report, _ = replay(self.root, self.count)
        self.save("socket_window_report", report)
        return read_socket_window(self.root)


def replay(root, count):
    started = time.monotonic()
    check(root, started)
    declaration, pa = _pair(root, "socket_window_policy")
    pre, root = paths(declaration["pre_computation_root"], root)
    policy = WindowBindingPolicy(**declaration["binding_policy"])
    transport = scope(declaration["transport"]["loopback_port"])
    if (
        declaration["schema_version"] != VERSION
        or declaration["limits"] != LIMITS
        or declaration["build"] != verified_panel_build()
        or declaration["connector"] != connector_contract()
        or declaration["transport"] != transport
        or type(declaration["duration_ms"]) is not int
        or not 1 <= declaration["duration_ms"] <= 60000
        or type(count) is not int
        or not 1 <= count <= LIMITS["max_events"]
    ):
        raise ValueError("socket declaration/build/scope differs")
    binding, ba = _pair(root, "socket_window_binding")
    original = _pre(pre)
    if (
        binding["binding"] != original
        or binding["policy_hash"] != pa["payload_hash"]
        or not _ordered_clocks(
            declaration["declared_at"],
            pa["durable_ack"],
            binding["read_started_at"],
            binding["read_completed_at"],
            ba["durable_ack"],
        )
        or not _ordered_clocks(
            original["pre_computation"]["computation_available_at"], binding["read_started_at"]
        )
    ):
        raise ValueError("socket prebinding/read chronology differs")
    expected = {
        n + s
        for n in ("socket_window_policy", "socket_window_binding")
        for s in (".json", "_ack.json")
    }
    previous_ack, previous_hash = ba["durable_ack"], None
    events, raw_bytes, frames, pings, late = [], 0, 0, 0, 0
    connected = False
    pending = None
    anchor = terminal = terminal_at = None
    close = None
    last_receive = None
    subscription = _json_bytes({"assets_ids": [original["identity"]["token_id"]], "type": "market"})
    provenance_ok = (
        original["pre_computation"]["source_provenance_class"] == transport["provenance_class"]
    )
    pre_fresh = all(
        _fresh(original, at, policy) for at in (binding["read_completed_at"], ba["durable_ack"])
    )
    for ordinal in range(1, count + 1):
        check(root, started)
        name = f"event_{ordinal:06d}"
        event, ack = _pair(root, name)
        expected.update({name + ".json", name + "_ack.json"})
        kind, observed, recorded = event["kind"], event["observed_at"], event["recorded_at"]
        if (
            event["schema_version"] != VERSION
            or event["ordinal"] != ordinal
            or event["previous_hash"] != previous_hash
            or kind not in KINDS
            or observed["clock_session_id"] != ba["durable_ack"]["clock_session_id"]
            or recorded["clock_session_id"] != observed["clock_session_id"]
            or ack["durable_ack"]["clock_session_id"] != observed["clock_session_id"]
            or not _ordered_clocks(previous_ack, recorded, ack["durable_ack"])
            or not _ordered_clocks(ba["durable_ack"], observed, recorded)
        ):
            raise ValueError("socket event lineage/persistence chronology differs")
        raw = None
        if event["raw_state"] == "observed":
            raw = (root / (name + ".bin")).read_bytes()
            expected.add(name + ".bin")
            if (
                event["wire_type"] not in {"text", "binary"}
                or event["raw_hash"] != _digest(raw)
                or event["raw_bytes"] != len(raw)
                or type(event["received_bytes"]) is not int
                or event["received_bytes"] < len(raw)
                or type(event["truncated"]) is not bool
                or event["truncated"] != (event["received_bytes"] > len(raw))
                or not isinstance(event["received_hash"], str)
                or not HASH_PATTERN.fullmatch(event["received_hash"])
                or (not event["truncated"] and event["received_hash"] != _digest(raw))
                or (
                    event["truncated"]
                    and (
                        kind != "received"
                        or len(raw)
                        != min(LIMITS["max_frame_bytes"], LIMITS["max_raw_bytes"] - raw_bytes)
                    )
                )
            ):
                raise ValueError("socket raw/truncation lineage differs")
            raw_bytes += len(raw)
        elif (
            event["raw_state"] != ("unavailable" if kind == "receive_error" else "not_applicable")
            or any(
                event[k] is not None
                for k in ("raw_hash", "raw_bytes", "received_hash", "received_bytes", "wire_type")
            )
            or event["truncated"] is not False
        ):
            raise ValueError("socket missing raw must not be fabricated")
        if (raw is not None) != (kind in {"subscription_intent", "ping_intent", "received"}):
            raise ValueError("socket raw scope differs")
        if events and events[-1]["truncated"] and kind != "budget_stop":
            raise ValueError("truncated socket must stop")
        operation = event["operation_started_at"]
        if kind in {
            "connected",
            "connect_error",
            "subscription_sent",
            "subscription_error",
            "ping_sent",
            "ping_error",
            "closed",
            "close_error",
        }:
            if (
                not operation
                or operation["clock_session_id"] != observed["clock_session_id"]
                or not _ordered_clocks(previous_ack, operation, observed)
            ):
                raise ValueError("socket operation lacks causal intent/actual start")
        elif operation is not None:
            raise ValueError("unexpected socket operation start")
        if kind == "connect_intent":
            if (
                ordinal != 1
                or not provenance_ok
                or not pre_fresh
                or not _fresh(original, observed, policy)
            ):
                raise ValueError("socket connection without fresh matching prior evidence")
            pending = kind
        elif kind in {"connected", "connect_error"}:
            if pending != "connect_intent" or ordinal != 2:
                raise ValueError("socket connection order differs")
            pending = None
            connected = kind == "connected"
            if not connected:
                terminal, terminal_at = kind, observed
        elif kind == "subscription_intent":
            if not connected or anchor or terminal or pending or raw != subscription:
                raise ValueError("socket subscription scope/order differs")
            pending = kind
        elif kind in {"subscription_sent", "subscription_error"}:
            if pending != "subscription_intent" or not _fresh(original, operation, policy):
                raise ValueError("socket subscription freshness/order differs")
            pending = None
            if kind == "subscription_sent":
                anchor = observed
            else:
                terminal, terminal_at = kind, observed
        elif kind in {
            "received",
            "receive_error",
            "ping_intent",
            "ping_sent",
            "ping_error",
            "interval_ended",
            "budget_stop",
        }:
            if not anchor or terminal or close:
                raise ValueError("socket event outside subscribed interval")
            elapsed = int(observed["monotonic_ns"]) - int(anchor["monotonic_ns"])
            if elapsed < 0:
                raise ValueError("socket event precedes subscription")
            if kind == "received":
                if pending not in {None, "ping_intent"} or (
                    last_receive and not _ordered_clocks(last_receive, observed)
                ):
                    raise ValueError("socket receive order differs")
                last_receive = observed
                frames += 1
                late += elapsed >= declaration["duration_ms"] * 1000000
            elif kind == "ping_intent":
                pings += 1
                if pending or raw != b"PING" or elapsed < pings * 10000000000:
                    raise ValueError("socket heartbeat schedule differs")
                pending = kind
            elif kind in {"ping_sent", "ping_error"}:
                if pending != "ping_intent":
                    raise ValueError("socket heartbeat result without intent")
                pending = None
            if kind in {"receive_error", "ping_error", "interval_ended", "budget_stop"}:
                if pending or (
                    kind == "interval_ended" and elapsed < declaration["duration_ms"] * 1000000
                ):
                    raise ValueError("socket terminal before interval/with pending send")
                terminal, terminal_at = kind, observed
        elif kind == "refused":
            if terminal or close:
                raise ValueError("duplicate socket refusal")
            reason = (
                "provenance_mismatch"
                if not provenance_ok
                else "pre_binding_stale"
                if not pre_fresh
                else "identity_expired_before_subscription"
            )
            if (
                event["reason"] != reason
                or (provenance_ok and pre_fresh and _fresh(original, observed, policy))
                or anchor
            ):
                raise ValueError("socket refusal not supported by original facts")
            terminal, terminal_at, pending = kind, observed, None
        elif kind == "close_intent":
            if not connected or not terminal or close or pending:
                raise ValueError("socket close order differs")
            pending, close = kind, kind
        elif kind in {"closed", "close_error"}:
            if pending != "close_intent" or ordinal != count:
                raise ValueError("socket close result order differs")
            pending, close = None, kind
        if kind != "refused" and event["reason"] is not None:
            raise ValueError("unexpected socket refusal reason")
        if kind.endswith("_error"):
            if (
                not isinstance(event["error"], dict)
                or set(event["error"])
                != {"exception_type", "sent_close_code", "received_close_code"}
                or not isinstance(event["error"]["exception_type"], str)
                or not 1 <= len(event["error"]["exception_type"]) <= 128
                or any(
                    v is not None and (type(v) is not int or not 1000 <= v <= 4999)
                    for k, v in event["error"].items()
                    if k != "exception_type"
                )
            ):
                raise ValueError("socket error facts required")
        elif event["error"] is not None:
            raise ValueError("unexpected socket error")
        if raw_bytes > LIMITS["max_raw_bytes"] or frames > LIMITS["max_frames"]:
            raise ValueError("socket source budget exceeded")
        previous_ack, previous_hash = ack["durable_ack"], ack["payload_hash"]
        events.append(event)
    if not terminal or pending or (connected and close not in {"closed", "close_error"}):
        raise ValueError("terminal socket/cleanup facts required")
    if declaration["build"] != verified_panel_build():
        raise ValueError("socket build changed during replay")
    report = {
        "schema_version": VERSION,
        "policy_hash": pa["payload_hash"],
        "binding_hash": ba["payload_hash"],
        "binding_available_at": ba["durable_ack"],
        "identity": original["identity"],
        "identity_available_at": original["identity_available_at"],
        "event_count": count,
        "last_event_hash": previous_hash,
        "frame_count": frames,
        "retained_raw_bytes": raw_bytes,
        "late_frame_count": late,
        "ping_count": pings,
        "subscription_sent_at": anchor,
        "ended_at": terminal_at,
        "terminal": terminal,
        "identity_fresh_at_subscription_completion": _fresh(original, anchor, policy)
        if anchor
        else None,
        "close_state": close or "not_connected",
        "state": "duration_completed"
        if terminal == "interval_ended" and close == "closed"
        else "incomplete",
        "provenance_class": "synthetic"
        if "synthetic"
        in {original["pre_computation"]["source_provenance_class"], transport["provenance_class"]}
        else "prospective",
        "transport_scope": transport["kind"],
        "source_provenance_compatible": provenance_ok,
        "source_admitted": False,
        "continuous_sequence_proven": False,
        "origin_admitted": False,
        "feature_store_admitted": False,
        "native_clock_admitted": False,
    }
    return report, expected


def read_socket_window(root):
    root = _canonical(root)
    check(root, time.monotonic())
    report, ack = _pair(root, "socket_window_report")
    expected, files = replay(root, report["event_count"])
    files.update({"socket_window_report.json", "socket_window_report_ack.json"})
    _, last_ack = _pair(root, f"event_{report['event_count']:06d}")
    if (
        report != expected
        or {p.name for p in root.iterdir()} != files
        or not _ordered_clocks(last_ack["durable_ack"], ack["durable_ack"])
    ):
        raise ValueError("socket report/closure differs")
    return {
        **report,
        "socket_window_report_hash": ack["payload_hash"],
        "socket_window_available_at": ack["durable_ack"],
    }
