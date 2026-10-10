"""Bounded diagnostic receipt journal; disconnected from the research writer.

Raw payload/receipt persist before parsing. Acknowledgement times are sampled after
fsync and refer to those artefacts, not the acknowledgement's own persistence time.
No deletion, overwrite, backdated clocks, application DB or scheduler integration.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
import zlib
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx

from .sources import SOURCES
from .types import canonical_json, canonical_value, utc_text

_CLOCK_SESSION = str(uuid.uuid4())
REUSED_HTTP_POLICY = {
    "version": "single-client-http1-v1", "max_connections": 1,
    "max_keepalive_connections": 1, "keepalive_expiry_seconds": 30,
    "transport_retries": 0, "cookies": "cleared_before_each_request",
}

GZIP_HTTP_POLICY = {
    "version": "bounded-gzip-wire-v1", "accept_encoding": "gzip",
    "source_id": "gamma.markets.keyset", "raw_artifact": "encoded-wire-entity-body",
    "decoded_limits": "independent-per-response-and-session-budget",
    "invalid_decode_charge": "full-reserved-decoded-limit",
    "gzip_members": "one-crc-valid-member-no-trailing-bytes",
}


class DecodedByteBudgetError(ValueError):
    pass


def payload_policy(session):
    if session.get("schema_version") != "fs2-capture-v3":
        if "http_payload_policy" in session:
            raise ValueError("legacy capture cannot enable payload decoding")
        return None
    if session.get("http_payload_policy") != GZIP_HTTP_POLICY:
        raise ValueError("capture HTTP payload policy differs")
    for key, maximum in (("bytes_per_response", 4194304), ("total_bytes", 3221225472)):
        value = session["budget"][key]
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("invalid decoded byte budget")
    return dict(GZIP_HTTP_POLICY)


def json_payload(capture):
    """Derive bounded JSON bytes from a verified capture; raw always remains wire bytes."""
    receipt, raw = capture["receipt"], capture["raw"]
    encoding = receipt["headers"].get("content-encoding", "identity")
    if receipt["schema_version"] != "fs2-receipt-v3":
        if encoding != "identity":
            raise ValueError("unsupported content encoding")
        return raw
    limit = receipt["decoded_byte_limit"]
    if (type(limit) is not int or not 1 <= limit <= 4194304
            or receipt["source_id"] != GZIP_HTTP_POLICY["source_id"]
            or receipt["request"].get("headers") != {"Accept-Encoding": "gzip"}):
        raise ValueError("invalid encoded capture contract")
    if encoding == "identity":
        if len(raw) > limit:
            raise DecodedByteBudgetError("decoded byte budget exceeded")
        return raw
    if encoding != "gzip":
        raise ValueError("unsupported content encoding")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decoded = decoder.decompress(raw, limit + 1)
    if len(decoded) > limit or decoder.unconsumed_tail:
        raise DecodedByteBudgetError("decoded byte budget exceeded")
    if not decoder.eof or decoder.unused_data:
        raise ValueError("incomplete or trailing gzip member")
    return decoded


def _response_error(receipt):
    error = receipt["transport_error"]
    if (error is None and receipt["request"]["method"] != "WS_RECEIVE"
            and not (receipt["status"] is not None and 200 <= receipt["status"] < 300)):
        error = "http_non_success"
    return error


def _decoded_evidence(capture):
    receipt = capture["receipt"]
    decoded, error = None, _response_error(receipt)
    if error is None:
        if receipt["headers"].get("content-encoding", "identity") not in {"gzip", "identity"}:
            error = "unsupported_content_encoding"
        else:
            try:
                decoded = json_payload(capture)
            except DecodedByteBudgetError:
                error = "decoded_byte_budget_exceeded"
            except (ValueError, zlib.error):
                error = "invalid_content_encoding"
    facts = {
        "decoded_bytes": len(decoded) if decoded is not None else None,
        "decoded_hash": _digest(decoded) if decoded is not None else None,
        "decoded_budget_charge": (len(decoded) if decoded is not None
                                  else receipt["decoded_byte_limit"]),
    }
    return decoded, facts, error


def connection_policy(session):
    """Read the frozen transport policy; older one-client-per-request sessions stay valid."""
    payload = payload_policy(session)
    if (session.get("schema_version") == "fs2-capture-v1"
            and "http_connection_policy" not in session):
        return None
    if (session.get("schema_version") in {"fs2-capture-v2", "fs2-capture-v3"}
            and (session["schema_version"] != "fs2-capture-v3" or payload is not None)
            and session.get("http_connection_policy") == REUSED_HTTP_POLICY):
        return dict(REUSED_HTTP_POLICY)
    raise ValueError("capture HTTP connection policy differs")


def _clock():
    return {"utc": utc_text(datetime.now(UTC)), "monotonic_ns": str(time.monotonic_ns()),
            "clock_session_id": _CLOCK_SESSION}


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_once(path, content):
    # A torn exclusive file is retained on failure, never silently overwritten/repaired.
    from .source_quota import guard_write

    guard_write(path, content)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    _sync_directory(path.parent)


def _json_bytes(value):
    return canonical_json(value).encode("utf-8")


def _digest(content):
    return hashlib.sha256(content).hexdigest()


def _strict_json(raw):
    def pairs(values):
        result = dict(values)
        if len(result) != len(values):
            raise ValueError("duplicate JSON key")
        return result

    def reject(value):
        raise ValueError("nonfinite JSON number")

    return json.loads(
        raw, parse_float=Decimal, parse_int=int, parse_constant=reject, object_pairs_hook=pairs,
    )


@dataclass(frozen=True)
class Budget:
    requests: int = 6
    bytes_per_response: int = 262144
    total_bytes: int = 1048576
    seconds_per_request: int = 15
    total_seconds: int = 90

    def __post_init__(self):
        for value, maximum in zip(
            asdict(self).values(), (10, 1048576, 4194304, 30, 180), strict=True,
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("capture budget outside bounded diagnostic limits")


class CaptureJournal:
    """A fresh, explicit directory for one bounded live or synthetic session.

    Supplying a mock transport always tags the session synthetic. This journal is
    diagnostic capture only; none of its rows are automatically research-admitted.
    """

    def __init__(self, root: Path, *, budget: Budget = Budget(), transport=None,
                 reuse_connections=False, accept_gzip=False):
        if type(reuse_connections) is not bool:
            raise ValueError("explicit boolean connection reuse policy required")
        if type(accept_gzip) is not bool or (accept_gzip and not reuse_connections):
            raise ValueError("gzip requires explicit boolean opt-in and reused connection")
        root = Path(root)
        if not root.is_absolute() or not root.name.startswith("fs2_capture_"):
            raise ValueError("explicit absolute fs2_capture_ directory required")
        if root.parent.resolve() != root.parent:
            raise ValueError("symlink/relative parent not permitted")
        root.mkdir(mode=0o700, exist_ok=False)
        _sync_directory(root.parent)
        self.root = root
        self.budget = budget
        self.transport = transport
        self.reuse_connections = reuse_connections
        self.accept_gzip = accept_gzip
        self.decoded_bytes = 0
        self._client = None
        self._scope_active = False
        self.session_id = str(uuid.uuid4())
        self.kind = "synthetic" if transport is not None else "live_diagnostic"
        self.started = time.monotonic()
        self.count = 0
        self.bytes = 0
        self._lock = asyncio.Lock()
        session = {
            "schema_version": "fs2-capture-v1", "session_id": self.session_id,
            "capture_kind": self.kind, "started": _clock(), "budget": asdict(budget),
        }
        if reuse_connections:
            session.update(schema_version="fs2-capture-v2",
                           http_connection_policy=dict(REUSED_HTTP_POLICY))
        if accept_gzip:
            session.update(schema_version="fs2-capture-v3",
                           http_payload_policy=dict(GZIP_HTTP_POLICY))
            payload_policy(session)
        _write_once(root / "session.json", _json_bytes(session))

    def _new_client(self):
        limits = ({"limits": httpx.Limits(max_connections=1, max_keepalive_connections=1,
                                          keepalive_expiry=30)} if self.reuse_connections else {})
        return httpx.AsyncClient(
            timeout=self.budget.seconds_per_request, follow_redirects=False,
            transport=self.transport, trust_env=False, http2=False, **limits,
            headers={"User-Agent": "Arepo-Research-Verification/2.0",
                     "Accept": "application/json",
                     "Accept-Encoding": "gzip" if self.accept_gzip else "identity"},
        )

    def connection_scope(self):
        # Keep loaded functions directly verifiable against compiled source. Decorating
        # the method itself would replace its code object with a contextlib wrapper.
        return asynccontextmanager(self._connection_scope)()

    async def _connection_scope(self):
        """Own and close one optional client, including cancellation and failed collection.

        The pool may reconnect after a server close; it does not retry failed requests.
        Injected transports remain synthetic. No caller-supplied live client is admitted.
        """
        if not self.reuse_connections:
            yield
            return
        if self._scope_active:
            raise ValueError("connection scope already active")
        self._scope_active = True
        try:
            async with self._new_client() as client:
                self._client = client
                try:
                    yield
                finally:
                    self._client = None
        finally:
            self._scope_active = False

    def _request_client(self):
        return asynccontextmanager(self._request_client_scope)()

    async def _request_client_scope(self):
        if self.reuse_connections:
            if self._client is None:
                raise ValueError("connection reuse requires an active scope")
            # Pooling must not add cookie-based state to these public stateless requests.
            self._client.cookies.clear()
            yield self._client
        else:
            async with self._new_client() as client:
                yield client

    async def fetch(self, source_id, params, *, previous_capture_id=None):
        # Serialize this small diagnostic session so total budgets and ordinals are exact.
        async with self._lock:
            if self.reuse_connections and self._client is None:
                raise ValueError("connection reuse requires an active scope")
            if self.accept_gzip and source_id != GZIP_HTTP_POLICY["source_id"]:
                raise ValueError("gzip is restricted to Gamma keyset")
            source = SOURCES[source_id]
            params = source.params(params)
            request = source.request(params)
            if self.accept_gzip:
                request = {**request, "headers": {"Accept-Encoding": "gzip"}}
                if self.decoded_bytes >= self.budget.total_bytes:
                    raise ValueError("decoded session byte budget exhausted")
            if self.count >= self.budget.requests or self.bytes >= self.budget.total_bytes:
                raise ValueError("session request/byte budget exhausted")
            remaining = self.budget.total_seconds - (time.monotonic() - self.started)
            if remaining <= 0:
                raise ValueError("session time budget exhausted")
            if previous_capture_id is not None:
                if str(uuid.UUID(previous_capture_id)) != previous_capture_id:
                    raise ValueError("parent must be a canonical capture UUID")
                previous = verify_capture(self.root / previous_capture_id)
                if previous["receipt"]["source_id"] != source_id:
                    raise ValueError("page/retry parent must have same source")
            if "cursor" in params:
                if previous_capture_id is None:
                    raise ValueError("cursor requires captured prior page")
                parent = previous["receipt"]["request"]["params"]
                if ({k: v for k, v in parent.items() if k != "cursor"}
                        != {k: v for k, v in params.items() if k != "cursor"}):
                    raise ValueError("cursor cannot change query scope")
                page = _strict_json(json_payload(previous))
                if (previous["parsed"]["parse_error"] is not None
                        or page.get("pagination", {}).get("next_cursor") != params["cursor"]
                        or params["cursor"] == parent.get("cursor")):
                    raise ValueError("cursor does not progress from captured page")
            if "after_cursor" in params:
                if previous_capture_id is None:
                    raise ValueError("keyset cursor requires captured prior page")
                parent = previous["receipt"]["request"]["params"]
                if ({k: v for k, v in parent.items() if k != "after_cursor"}
                        != {k: v for k, v in params.items() if k != "after_cursor"}):
                    raise ValueError("keyset cursor cannot change query scope")
                page = _strict_json(json_payload(previous))
                if (previous["parsed"]["parse_error"] is not None
                        or not isinstance(page, dict)
                        or page.get("next_cursor") != params["after_cursor"]
                        or params["after_cursor"] == parent.get("after_cursor")):
                    raise ValueError("keyset cursor does not progress from captured page")
            self.count += 1
            capture_id = str(uuid.uuid4())
            folder = self.root / capture_id
            folder.mkdir(mode=0o700)
            _sync_directory(self.root)
            started = _clock()
            raw = bytearray()
            status = None
            headers = {}
            error = None
            first_byte = None
            cancelled = None
            limit = min(self.budget.bytes_per_response, self.budget.total_bytes - self.bytes)
            decoded_before = self.decoded_bytes
            decoded_limit = min(self.budget.bytes_per_response,
                                self.budget.total_bytes - decoded_before)
            if self.accept_gzip:
                # Reserve before I/O: even an interrupted parse cannot evade the budget.
                self.decoded_bytes += decoded_limit
            try:
                async with asyncio.timeout(min(remaining, self.budget.seconds_per_request)):
                    async with self._request_client() as client:
                        async with client.stream("GET", request["url"],
                                                 params=request["params"],
                                                 headers=request.get("headers")) as response:
                            status = response.status_code
                            header_names = ("content-type", "content-encoding",
                                            "date", "retry-after")
                            if self.accept_gzip:
                                header_names += ("content-length", "etag", "age",
                                                 "cf-cache-status", "vary")
                            headers = {k: response.headers[k] for k in header_names
                                       if k in response.headers}
                            async for chunk in response.aiter_raw():
                                if first_byte is None:
                                    first_byte = _clock()
                                room = limit - len(raw)
                                raw.extend(chunk[:room])
                                if len(chunk) > room:
                                    error = "byte_budget_exceeded"
                                    break
            except (httpx.HTTPError, TimeoutError) as exc:
                error = type(exc).__name__  # Do not leak response bodies/credentials in errors.
            except asyncio.CancelledError as exc:
                # Preserve a cancelled partial attempt synchronously before propagating
                # cancellation. It must never resemble a complete empty response.
                error, cancelled = "cancelled", exc
            received = _clock()  # Complete response/partial-attempt receipt, before parsing.
            self.bytes += len(raw)
            receipt = {
                "schema_version": "fs2-receipt-v2", "capture_id": capture_id,
                "session_hash": _digest((self.root / "session.json").read_bytes()),
                "session_id": self.session_id, "receipt_ordinal": self.count,
                "capture_kind": self.kind, "source_id": source_id,
                "source_version": source.version, "source_contract": asdict(source),
                "request": request,
                "previous_capture_id": previous_capture_id, "request_started": started,
                "first_byte": first_byte, "first_received": received,
                "status": status, "headers": headers, "transport_error": error,
                "raw_bytes": len(raw), "raw_hash": _digest(raw),
                "clock_error_bound_ms": None,
                "scope": "diagnostic_only; no population or historical coverage claim",
            }
            if self.accept_gzip:
                receipt.update(schema_version="fs2-receipt-v3",
                               decoded_budget_before=decoded_before,
                               decoded_byte_limit=decoded_limit)
            _write_once(folder / "raw.bin", raw)
            receipt_bytes = _json_bytes(receipt)
            _write_once(folder / "receipt.json", receipt_bytes)
            _write_once(folder / "raw_ack.json", _json_bytes({
                "receipt_hash": _digest(receipt_bytes), "raw_hash": _digest(raw),
                "durable_ack": _clock(),
            }))
            result = finish_parse(folder)
            if self.accept_gzip:
                self.decoded_bytes -= decoded_limit - result["parsed"]["decoded_budget_charge"]
            if cancelled is not None:
                raise cancelled
            return result


def finish_parse(folder: Path):
    """Recover only an intact raw receipt; never reuse an unproven old parse clock.

    Complete retries read their original artefacts. A partial parse attempt is retained
    and refused; callers must investigate it, not overwrite it or label it prospective.
    """
    folder = Path(folder)
    base = verify_capture(folder, raw_only=True)
    if (folder / "parsed_ack.json").exists():
        return verify_capture(folder)
    if (folder / "parsed.json").exists():
        raise ValueError("partial parse retained; availability is unproven")
    receipt, raw = base["receipt"], base["raw"]
    encoding = receipt["headers"].get("content-encoding", "identity")
    parsed = None
    decoded_facts = None
    error = _response_error(receipt)
    if receipt["schema_version"] == "fs2-receipt-v3":
        raw, decoded_facts, error = _decoded_evidence(base)
    elif error is None and encoding != "identity":
        error = "unsupported_content_encoding"
    if error is None:
        try:
            parsed = _strict_json(raw)
        except (ValueError, UnicodeError, RecursionError):
            error = "invalid_json"
    result = {
        "schema_version": "fs2-parsed-v1", "capture_id": receipt["capture_id"],
        "parser_version": "lossless-json-v1", "raw_hash": receipt["raw_hash"],
        "parsed_at": _clock(), "parse_error": error, "value": parsed,
    }
    if decoded_facts is not None:
        result.update(schema_version="fs2-parsed-v2", **decoded_facts)
    # Metadata keeps the generic strict canonical conversion. Only the freshly decoded
    # JSON value (string keys, int/Decimal numbers) can skip the recursive primitive copy.
    # Decimal tags still use canonical_value; this is not a generic encoder for callers.
    envelope = canonical_value({key: value for key, value in result.items() if key != "value"})
    envelope["value"] = parsed
    output = json.dumps(
        envelope, default=canonical_value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    _write_once(folder / "parsed.json", output)
    _write_once(folder / "parsed_ack.json", _json_bytes({
        "parsed_hash": _digest(output),
        "raw_ack_hash": _digest((folder / "raw_ack.json").read_bytes()),
        "durable_ack": _clock(),
    }))
    return verify_capture(folder)


def verify_capture(folder: Path, *, raw_only=False):
    """Read-only integrity/chronology verification, with no repair or inferred clocks."""
    folder = Path(folder)
    if folder.is_symlink() or folder.resolve() != folder:
        raise ValueError("capture path must be canonical and nonsymlink")
    uuid.UUID(folder.name)

    def read(name):
        path = folder / name
        if path.is_symlink() or path.stat().st_size > 16 * 1048576:
            raise ValueError("invalid capture artefact")
        return path.read_bytes()

    receipt_bytes, raw, ack_bytes = read("receipt.json"), read("raw.bin"), read("raw_ack.json")
    receipt, ack = _strict_json(receipt_bytes), _strict_json(ack_bytes)
    if (
        receipt["capture_id"] != folder.name
        or receipt["schema_version"] not in {"fs2-receipt-v1", "fs2-receipt-v2", "fs2-receipt-v3"}
        or _digest(raw) != receipt["raw_hash"] or len(raw) != receipt["raw_bytes"]
        or ack["raw_hash"] != _digest(raw) or ack["receipt_hash"] != _digest(receipt_bytes)
    ):
        raise ValueError("raw capture integrity mismatch")
    if receipt["source_id"] == "gamma.market":
        SOURCES["gamma.market"].market_request_id(receipt["request"])
    if receipt["source_id"] == "nws.station.observation":
        SOURCES["nws.station.observation"].station_request_id(receipt["request"])
    if receipt["schema_version"] in {"fs2-receipt-v2", "fs2-receipt-v3"}:
        session_path = folder.parent / "session.json"
        if session_path.is_symlink() or session_path.stat().st_size > 1048576:
            raise ValueError("invalid capture session")
        session_bytes = session_path.read_bytes()
        session = _strict_json(session_bytes)
        if (receipt["session_hash"] != _digest(session_bytes)
                or session["session_id"] != receipt["session_id"]
                or session["capture_kind"] != receipt["capture_kind"]):
            raise ValueError("capture session integrity mismatch")
        connection_policy(session)
        encoded = session["schema_version"] == "fs2-capture-v3"
        if encoded != (receipt["schema_version"] == "fs2-receipt-v3"):
            raise ValueError("capture payload version differs")
        if encoded:
            before, limit = receipt["decoded_budget_before"], receipt["decoded_byte_limit"]
            if (receipt["source_id"] != GZIP_HTTP_POLICY["source_id"]
                    or receipt["request"].get("headers") != {"Accept-Encoding": "gzip"}
                    or type(before) is not int or not 0 <= before < session["budget"]["total_bytes"]
                    or type(limit) is not int
                    or limit != min(session["budget"]["bytes_per_response"],
                                    session["budget"]["total_bytes"] - before)):
                raise ValueError("encoded capture scope/reservation differs")
    clocks = [receipt["request_started"]]
    if receipt["first_byte"] is not None:
        clocks.append(receipt["first_byte"])
    clocks.extend([receipt["first_received"], ack["durable_ack"]])
    result = {"folder": str(folder), "receipt": receipt, "raw": raw, "raw_ack": ack}
    if not raw_only:
        parsed_bytes = read("parsed.json")
        parsed, parsed_ack = _strict_json(parsed_bytes), _strict_json(read("parsed_ack.json"))
        if (
            parsed_ack["parsed_hash"] != _digest(parsed_bytes)
            or parsed_ack["raw_ack_hash"] != _digest(ack_bytes)
            or parsed["raw_hash"] != receipt["raw_hash"]
            or parsed["capture_id"] != receipt["capture_id"]
        ):
            raise ValueError("parsed capture integrity mismatch")
        if receipt["schema_version"] == "fs2-receipt-v3":
            _, facts, decode_error = _decoded_evidence(result)
            if (parsed.get("schema_version") != "fs2-parsed-v2"
                    or _json_bytes({k: parsed.get(k) for k in facts}) != _json_bytes(facts)
                    or (decode_error is not None and parsed["parse_error"] != decode_error)
                    or (decode_error is None
                        and parsed["parse_error"] not in {None, "invalid_json"})):
                raise ValueError("decoded capture evidence differs")
        clocks.extend([parsed["parsed_at"], parsed_ack["durable_ack"]])
        result.update(parsed=parsed, parsed_ack=parsed_ack)
    for previous, current in zip(clocks, clocks[1:], strict=False):
        from .types import utc_datetime

        if (
            utc_datetime(datetime.fromisoformat(current["utc"]))
            < utc_datetime(datetime.fromisoformat(previous["utc"]))
            or (current["clock_session_id"] == previous["clock_session_id"]
                and int(current["monotonic_ns"]) < int(previous["monotonic_ns"]))
        ):
            raise ValueError("clock regression; retain capture but do not admit")
    return result


def diagnostic_summary(capture):
    """Safe report: no raw text, wallet identifiers or claim of research admission."""
    return {
        "capture_id": capture["receipt"]["capture_id"],
        "source_id": capture["receipt"]["source_id"],
        "status": capture["receipt"]["status"],
        "raw_bytes": capture["receipt"]["raw_bytes"],
        "raw_hash": capture["receipt"]["raw_hash"],
        "received_at": capture["receipt"]["first_received"]["utc"],
        "parse_error": capture["parsed"]["parse_error"],
        "parsed_artifact_available_at": capture["parsed_ack"]["durable_ack"]["utc"],
        "capture_kind": capture["receipt"]["capture_kind"],
        "research_admitted": False,
    }
