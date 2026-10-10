"""D116 acceptance evaluator: read retained artifacts, apply a predeclared classification table.

Pure and deterministic: no network, no clock, no writes, no source requests. It reads only the
retained panel / selection / screening-worker / activation / runtime artifacts of one D116 run
and returns a JSON-serialisable report. It does not replace the original-code audit (E8); it
applies the D116 protocol's gates, the exhaustive state classification table and the outcome
decision to what those retained artifacts say. Pair files (``name.json`` + ``name_ack.json``)
are checked against their acknowledged sha256 before use.

Every state or reason that the code can emit is mapped to exactly one class:

* ``OK``             the expected, non-limiting state;
* ``DATA_SOURCE``    the provider's data legitimately says so (closed, one-sided book, ...);
* ``DATA_TRANSPORT`` the provider/network did not deliver (transport error, 4xx/5xx, ...);
* ``ENGINEERING``    anything produced by our timing, budgets or defects, and every state that is
                     not listed here. Any ENGINEERING finding makes the outcome FAIL.

A DATA classification is only honoured when the retained raw receipts support it (status,
transport_error, raw_hash, and for content claims the parsed response). Otherwise the finding is
reclassified ENGINEERING with rule ``citation_failed:<check>``.
"""

import gzip
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..feature_store.capture import _strict_json
from ..feature_store.source_parsers import clob_book, gamma_market
from .bound_window import WindowBindingPolicy
from .origin_window import OriginWindowPolicy
from .owned_windows import OwnedWindowPolicy, policy_dict
from .panel_declaration import TEMPORAL_POPULATION
from .screening import LIMITS as SCREENING_LIMITS
from .screening import ScreeningPolicy
from .trigger_computation import SnapshotTriggerPolicy
from .window_reconciliation import WindowReconciliationPolicy

EVALUATOR_VERSION = "d116-evaluator-v3"
OK = "OK"
DATA_SOURCE = "DATA_SOURCE"
DATA_TRANSPORT = "DATA_TRANSPORT"
ENGINEERING = "ENGINEERING"
DATA_CLASSES = frozenset({DATA_SOURCE, DATA_TRANSPORT})

D116_PROTOCOL = {
    "scheduled_slots": 8,
    "triggered_slots": 8,
    "controls_per_trigger": 1,
    "cycles": 1,
    "target_attempts": 1,
    "scheduled_per_stratum": 2,
    "triggered_per_stratum": 2,
    "cadence_seconds": 120,
    "max_origin_delay_seconds": 60,
    "max_origin_save_seconds": 5,
    "horizon_seconds": 60,
    "tolerance_seconds": 15,
    "max_frame_age_seconds": 3600,
    "max_frame_interval_seconds": 600,
    "max_quote_age_seconds": 60,
    "max_identity_age_seconds": 180,
    "source_response_bytes": 65536,
    "source_run_retained_bytes": 1048576,
}

# --------------------------------------------------------------------------------------------
# Frozen run identity and frozen policy values (protocol sections 3 and 4.2 E0/E1). Every value
# below is compared against the retained artifacts; nothing here is tunable at evaluation time.
# --------------------------------------------------------------------------------------------
FROZEN_PANEL_NAME = "fs2_panel_d116_integrated_1"
FROZEN_ROOT_NAMES = {
    "selection": "fs2_selection_panel_d116_integrated_1",
    "worker": "fs2_screening_worker_d116_integrated_1",
    "activation": "fs2_activation_d116_integrated_1",
    "runtime": "fs2_runtime_d116_integrated_1",
}
# Recorded only: ancestry of this commit in the launch commit is a protocol launch precondition
# checked by the launch wrapper (git is not consulted here: the evaluator stays pure).
REQUIRED_ANCESTOR_COMMIT = "8afbdff"
REQUIRED_SCREENING_SCHEMA = "fs2-screening-owned-selection-v4"
LIVE_PROVENANCE = "prospective"  # synthetic runs record "synthetic"; socket transport kind "public"
LIVE_SOCKET_KIND = "public"
_COMMIT = re.compile("[0-9a-f]{40}")
FROZEN_EXPECTATIONS = {
    "panel": {"strata_limit": 4, "population_policy": TEMPORAL_POPULATION},
    "worker": {
        "rule": asdict(SnapshotTriggerPolicy(1, 3, 60000)),
        "freshness": asdict(ScreeningPolicy(120, 120)),
        "window_policy": policy_dict(
            OwnedWindowPolicy(
                10000,
                WindowBindingPolicy(60000, 180000),
                WindowReconciliationPolicy(120000, 120000, 1000),
                OriginWindowPolicy(120000, 60000),
                binding_mode="observation",
            )
        ),
        "concurrency": 8,
        "runtime_concurrency": 4,
        "limits": {"max_seconds": 7200, "acquisition_seconds": 1800},
    },
    "screening_max_seconds": 600,
    "screening_limits": dict(SCREENING_LIMITS),
}
SOURCE_REASONS = ("permission_denied", "rate_limited", "transport_gap", "source_error", "invalid")
_LIFECYCLE_KEYS = ("active", "closed", "archived", "acceptingOrders")
_ACTIVE = {"active": True, "closed": False, "archived": False, "acceptingOrders": True}
_HEX64 = re.compile("[0-9a-f]{64}")


def _row(cls, check=None, basis="", **params):
    row = {"class": cls, "basis": basis}
    if check:
        row["check"] = check
    row.update(params)
    return row


def _quote_states():
    return {
        "observed": _row(OK, basis="quote_inputs.py:84,112 missing_reason observed"),
        "permission_denied": _row(
            DATA_TRANSPORT,
            "http_auth_denied",
            "feature_store/source_run.py:285",
            source="clob.book",
        ),
        "rate_limited": _row(
            DATA_TRANSPORT,
            "http_rate_limited",
            "feature_store/source_run.py:286",
            source="clob.book",
        ),
        "transport_gap": _row(
            DATA_TRANSPORT, "transport_error", "feature_store/source_run.py:287", source="clob.book"
        ),
        "source_error": _row(
            DATA_TRANSPORT,
            "http_5xx_or_none",
            "feature_store/source_run.py:288",
            source="clob.book",
        ),
        "invalid": _row(
            DATA_SOURCE, "http_invalid", "feature_store/source_run.py:288", source="clob.book"
        ),
        "identity_unresolved_at_receipt": _row(
            DATA_SOURCE, "identity_unresolved", "quote_inputs.py:130"
        ),
        "identity_ambiguous_or_conflicting": _row(
            DATA_SOURCE, "identity_conflict", "quote_inputs.py:133"
        ),
        "one_sided_or_missing": _row(DATA_SOURCE, "book_empty_side", "targets.py:54"),
        "invalid_numerical": _row(DATA_SOURCE, "book_non_decimal", "targets.py:59"),
        "invalid_or_crossed": _row(DATA_SOURCE, "book_crossed", "targets.py:61"),
        "duplicate_price_level": _row(
            DATA_SOURCE, "book_duplicate_price", "quote_inputs.py:150-151"
        ),
        "numerical_budget_exceeded": _row(ENGINEERING, basis="targets.py:67 our numerical budget"),
        "identity_stale": _row(ENGINEERING, basis="quote_inputs.py:155 our timing"),
        "receipt_stale": _row(ENGINEERING, basis="quote_inputs.py:157 our timing"),
        "market_closed": _row(DATA_SOURCE, "lifecycle_closed", "quote_inputs.py:162"),
        "closed": _row(DATA_SOURCE, "lifecycle_closed", "target_adapter.py:81"),
        "market_archived": _row(DATA_SOURCE, "lifecycle_archived", "quote_inputs.py:164"),
        "market_not_accepting_orders": _row(
            DATA_SOURCE, "lifecycle_not_accepting", "quote_inputs.py:166"
        ),
        "market_lifecycle_unknown": _row(DATA_SOURCE, "lifecycle_unknown", "quote_inputs.py:168"),
        "identity_changed_since_origin": _row(
            DATA_SOURCE, "target_mapping_differs", "target_adapter.py:71"
        ),
        "identity_unresolved": _row(
            ENGINEERING, basis="targets.py:46 mapping time absent (not producible here)"
        ),
        "identity_not_known_at_receipt": _row(ENGINEERING, basis="targets.py:48"),
        "identity_not_frozen_at_origin": _row(
            ENGINEERING, basis="targets.py:114-115 (exclusion reason)"
        ),
        "not_yet_available": _row(ENGINEERING, basis="targets.py:112-113 our timing"),
        "late": _row(ENGINEERING, basis="targets.py:125-127 our timing"),
    }


def _build_table():
    quote = _quote_states()
    table = {"quote_state": quote}
    table["source_status"] = {
        f"{src}_{reason}": {**quote[reason], "source": src}
        for src in ("gamma.market", "clob.book")
        for reason in SOURCE_REASONS
    }
    trigger = {
        "source_pair_unavailable": _row(ENGINEERING, basis="trigger_computation.py:128"),
        "source_stale_at_assessment": _row(ENGINEERING, basis="trigger_computation.py:141"),
        "requested_identity_differs": _row(ENGINEERING, basis="trigger_computation.py:150"),
        "snapshot_identity_unavailable_or_changed": _row(
            DATA_SOURCE, "identity_unresolved_or_conflict", "trigger_computation.py:161"
        ),
        "known_active_lifecycle_unavailable": _row(
            DATA_SOURCE, "lifecycle_not_active_or_gamma_failed", "trigger_computation.py:168"
        ),
        "frame_mapping_changed_or_unavailable": _row(
            DATA_SOURCE, "frame_mapping_citation", "screening.py:324-325"
        ),
        "snapshot_unavailable": _row(
            ENGINEERING, basis="trigger_computation.py:154 (snapshot absent)"
        ),
    }
    trigger.update(table["source_status"])
    trigger.update({f"snapshot_{k}": v for k, v in quote.items() if k != "observed"})
    table["trigger_reason"] = trigger
    table["assessment_reason"] = {
        "input_window_stale": _row(
            ENGINEERING, basis="assessments.py:98-99 (plan.assessment_inventory)"
        ),
        "assessment_stale": _row(
            ENGINEERING, basis="assessments.py:100-101 (plan.assessment_inventory)"
        ),
    }
    table["screening_state"] = {
        "triggered": _row(OK, basis="screening.py:315-336"),
        "untriggered": _row(OK, basis="screening.py:315-336"),
        "unavailable": _row(OK, basis="container: every reason is classified separately"),
        "not_assessed": _row(ENGINEERING, basis="screening.py:300-303 missing journal"),
    }
    table["window_missing"] = {
        "none": _row(OK, basis="owned_windows.py:113-114"),
        "pre_snapshot_unavailable": _row(
            DATA_SOURCE, "pre_snapshot_citation", "owned_windows.py:85,90"
        ),
        "pre_identity_differs": _row(DATA_SOURCE, "pre_identity_citation", "owned_windows.py:96"),
        "pre_lifecycle_unavailable": _row(
            DATA_SOURCE, "pre_lifecycle_citation", "owned_windows.py:100"
        ),
    }
    table["socket_terminal"] = {
        "interval_ended": _row(OK, basis="socket_window_journal.py:432-437"),
        "connect_error": _row(
            DATA_TRANSPORT, "socket_error_event", "socket_window_journal.py:382-388"
        ),
        "subscription_error": _row(
            DATA_TRANSPORT, "socket_error_event", "socket_window_journal.py:393-400"
        ),
        "receive_error": _row(
            DATA_TRANSPORT, "socket_error_event", "socket_window_journal.py:432-437"
        ),
        "ping_error": _row(
            DATA_TRANSPORT, "socket_error_event", "socket_window_journal.py:432-437"
        ),
        "budget_stop": _row(ENGINEERING, basis="socket_window_journal.py:408-437 our budget"),
        "refused": _row(
            ENGINEERING, basis="socket_window_journal.py:438-454 our freshness/provenance"
        ),
    }
    table["socket_close_state"] = {
        "closed": _row(OK, basis="socket_window_journal.py:459-462"),
        "not_connected": _row(OK, basis="only valid after connect_error; checked with terminal"),
        "close_error": _row(
            ENGINEERING,
            basis="socket_window_journal.py:459-462 close_error is network-only "
            "(close handshake); conservatively ENGINEERING, never a data outcome",
        ),
    }
    origin = {
        "observed": _row(OK, basis="origin_worker.py:231,395"),
        "failed": _row(ENGINEERING, basis="origin_worker.py:317-321"),
        "expired_before_request": _row(ENGINEERING, basis="origin_worker.py:285"),
        "expired_during_requests": _row(ENGINEERING, basis="origin_worker.py:317-321"),
        "late_origin": _row(ENGINEERING, basis="origin_worker.py:229-230"),
        "late_persistence": _row(ENGINEERING, basis="origin_worker.py:238-240,396-399"),
        "receipt_stale_at_origin": _row(ENGINEERING, basis="origin_worker.py:221-224"),
        "identity_stale_at_origin": _row(ENGINEERING, basis="origin_worker.py:225-228"),
        "identity_changed_since_selection": _row(
            DATA_SOURCE, "origin_mapping_differs", "origin_worker.py:220"
        ),
    }
    for key, value in quote.items():
        origin.setdefault(key, value)
    table["origin_state"] = origin
    history = {
        "snapshot_unavailable": _row(
            DATA_SOURCE, "history_snapshot_citation", "origin_window.py:85"
        ),
        "identity_changed_or_unavailable": _row(
            DATA_SOURCE, "history_identity_citation", "origin_window.py:87"
        ),
        "prior_quote_stale": _row(ENGINEERING, basis="origin_window.py:92"),
        "current_quote_not_after_window": _row(ENGINEERING, basis="origin_window.py:97"),
        "window_stale": _row(ENGINEERING, basis="origin_window.py:101"),
    }
    table["history_reason"] = history
    freeze = dict(history)
    freeze.update(
        {
            "prior_quote_stale_at_freeze": _row(ENGINEERING, basis="origin_features.py:99-104"),
            "window_stale_at_freeze": _row(ENGINEERING, basis="origin_features.py:105-108"),
        }
    )
    freeze.update({f"origin_{k}": v for k, v in origin.items() if k != "observed"})
    table["freeze_reason"] = freeze
    table["target_attempt_state"] = {
        "recorded": _row(OK, basis="due_worker.py recorded attempt state"),
        "origin_ineligible": _row(
            OK, basis="due_worker.py:319,413: class follows the origin state"
        ),
        "incomplete_evidence": _row(ENGINEERING, basis="due_worker.py:410"),
        "expired": _row(ENGINEERING, basis="due_worker.py:319,413"),
    }
    table["target_outcome"] = {
        "observed": _row(OK, basis="targets.py:148"),
        "closed": _row(DATA_SOURCE, "target_lifecycle_closed", "targets.py:132-135"),
        "unavailable": _row(OK, basis="container: requires nonempty classified exclusions"),
        "origin_ineligible": _row(
            OK, basis="due_worker.py:464-465: class follows the origin state"
        ),
        "pending": _row(ENGINEERING, basis="targets.py:121,128-131"),
        "incomplete_evidence": _row(ENGINEERING, basis="due_worker.py:466-467"),
    }
    table["target_exclusion"] = dict(quote)
    table["artifact"] = {
        "selection_failure": _row(ENGINEERING, basis="selection.py failure artifact"),
        "activation_failure": _row(ENGINEERING, basis="activation.py failure artifact"),
        "worker_failure": _row(ENGINEERING, basis="screening_worker.py failure artifact"),
        "runtime_failure": _row(ENGINEERING, basis="concurrent_runtime.py failure artifact"),
        "origin_failure": _row(ENGINEERING, basis="origin_worker.py:317-321"),
        "target_failure": _row(ENGINEERING, basis="due_worker.py:410"),
        "missing_or_unreadable_artifact": _row(ENGINEERING, basis="evaluator"),
        "artifact_hash_mismatch": _row(ENGINEERING, basis="evaluator"),
    }
    table["worker_state"] = {
        "pilot_collected_unaccepted": _row(OK, basis="screening_worker.py:417-418"),
        "blocked_role_capacity": _row(ENGINEERING, basis="screening_worker.py:417-418"),
        "screening_complete": _row(ENGINEERING, basis="not an owned pilot report"),
    }
    return table


CLASSIFICATION_TABLE = _build_table()
UNLISTED = _row(ENGINEERING, basis="unlisted state: any state not in this table is ENGINEERING")
TABLE_SHA256 = hashlib.sha256(
    json.dumps(CLASSIFICATION_TABLE, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


# --------------------------------------------------------------------------------------------
# Artifact reading
# --------------------------------------------------------------------------------------------


def _utc(value):
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("utc") or value.get("$utc")
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value):
    return value.isoformat() if value is not None else None


def _seconds(later, earlier):
    if later is None or earlier is None:
        return None
    return (later - earlier).total_seconds()


class _Reader:
    """Loads JSON artifacts; every failure becomes an ENGINEERING finding, never an exception."""

    def __init__(self):
        self.findings = []

    def note(self, stage, value, detail, member=None):
        self.findings.append(_finding("artifact", value, stage=stage, member=member, detail=detail))

    def plain(self, path, stage="artifact", member=None, required=True):
        try:
            return json.loads(Path(path).read_bytes())
        except FileNotFoundError:
            if required:
                self.note(stage, "missing_or_unreadable_artifact", f"missing {path}", member)
        except (OSError, ValueError) as exc:
            self.note(
                stage, "missing_or_unreadable_artifact", f"{path}: {type(exc).__name__}", member
            )
        return None

    def pair(self, folder, name, stage="artifact", member=None, required=True):
        folder = Path(folder)
        body = folder / f"{name}.json"
        ack = folder / f"{name}_ack.json"
        if not body.exists():
            if required:
                self.note(stage, "missing_or_unreadable_artifact", f"missing {body}", member)
            return None
        try:
            raw = body.read_bytes()
            payload = json.loads(raw)
            receipt = json.loads(ack.read_bytes())
        except (OSError, ValueError) as exc:
            self.note(
                stage, "missing_or_unreadable_artifact", f"{body}: {type(exc).__name__}", member
            )
            return None
        if receipt.get("payload_hash") != hashlib.sha256(raw).hexdigest():
            self.note(stage, "artifact_hash_mismatch", f"{body}", member)
            return None
        payload = payload if isinstance(payload, dict) else {"value": payload}
        payload["__ack__"] = receipt
        return payload


def _finding(namespace, value, *, stage, member=None, detail=None, ctx=None):
    entry = CLASSIFICATION_TABLE.get(namespace, {}).get(value)
    rule = f"{namespace}:{value}"
    citation = None
    cls = entry["class"] if entry else ENGINEERING
    basis = entry["basis"] if entry else UNLISTED["basis"]
    if entry is not None and cls in DATA_CLASSES:
        check = entry.get("check")
        verdict = (
            CHECKS[check](ctx or {}, entry) if check in CHECKS else (False, "no citation rule")
        )
        ok, citation = verdict
        if not ok:
            cls, rule = ENGINEERING, f"citation_failed:{check}:{rule}"
    return {
        "stage": stage,
        "member": member,
        "state": value,
        "class": cls,
        "rule": rule,
        "basis": basis,
        "citation": citation,
        "detail": detail,
    }


class _Receipt:
    def __init__(self, folder):
        self.folder = Path(folder)
        raw_receipt = (self.folder / "receipt.json").read_bytes()
        self.receipt = json.loads(raw_receipt)
        raw = (self.folder / "raw.bin").read_bytes()
        self.source_id = self.receipt["source_id"]
        self.status = self.receipt["status"]
        self.transport_error = self.receipt["transport_error"]
        self.raw_bytes = self.receipt["raw_bytes"]
        self.raw_hash = self.receipt["raw_hash"]
        self.raw_verified = (
            hashlib.sha256(raw).hexdigest() == self.raw_hash and len(raw) == self.raw_bytes
        )
        try:
            ack = json.loads((self.folder / "raw_ack.json").read_bytes())
            self.receipt_verified = (
                ack.get("receipt_hash") == hashlib.sha256(raw_receipt).hexdigest()
            )
        except (OSError, ValueError):
            self.receipt_verified = False
        request = self.receipt.get("request") or {}
        self.market_id = (request.get("path_params") or {}).get("id")
        self.token_id = (request.get("params") or {}).get("token_id")
        self.first_received = _utc(self.receipt.get("first_received"))
        try:
            self.raw_text = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        except (OSError, EOFError):
            self.raw_text = b""
        try:
            self._body = json.loads(self.raw_text)
        except ValueError:
            self._body = None

    @property
    def ok2xx(self):
        return (
            self.transport_error is None
            and isinstance(self.status, int)
            and 200 <= self.status < 300
            and self.raw_verified
        )

    def body(self):
        return self._body

    def cite(self):
        return {
            "source_id": self.source_id,
            "status": self.status,
            "transport_error": self.transport_error,
            "raw_hash": self.raw_hash,
            "raw_verified": self.raw_verified,
        }


def _captures(reader, root, stage, member):
    """Receipts below a SourceRun root (``<root>/<capture_id>/receipt.json``)."""
    result = {}
    root = Path(root)
    if not root.is_dir():
        return result
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p / "receipt.json").exists()):
        try:
            item = _Receipt(folder)
        except (OSError, ValueError, KeyError) as exc:
            reader.note(
                stage,
                "missing_or_unreadable_artifact",
                f"receipt {folder.name}: {type(exc).__name__}",
                member,
            )
            continue
        result.setdefault(item.source_id, []).append(item)
    return result


# --------------------------------------------------------------------------------------------
# Discriminating checks. Each returns (supported, citation) from retained raw receipts only.
# --------------------------------------------------------------------------------------------


def _rx(ctx, source):
    return (ctx.get("receipts") or {}).get(source, [])


def _cite(items):
    return [r.cite() for r in items]


def _any(ctx, source, predicate):
    hits = [r for r in _rx(ctx, source) if predicate(r)]
    return (bool(hits), _cite(hits) if hits else _cite(_rx(ctx, source)))


def _source(entry, default="clob.book"):
    return entry.get("source", default)


def _levels(body, side):
    out = []
    for level in (body.get(side) if isinstance(body, dict) else None) or []:
        try:
            price, size = Decimal(str(level["price"])), Decimal(str(level["size"]))
        except (InvalidOperation, KeyError, TypeError):
            out.append((None, None))
            continue
        # NaN/Infinity parse as Decimal but are not decimals (targets.py:57-59). A zero size is a
        # valid decimal; it is invalid_or_crossed (targets.py:61), never non-decimal.
        out.append((price, size) if price.is_finite() and size.is_finite() else (None, None))
    return out


def _book(ctx):
    for r in _rx(ctx, "clob.book"):
        if r.ok2xx and isinstance(r.body(), dict):
            return r, r.body()
    return None, None


def _gamma(ctx):
    for r in _rx(ctx, "gamma.market"):
        if r.ok2xx and isinstance(r.body(), dict):
            return r, r.body()
    return None, None


def _gamma_failing(ctx):
    items = _rx(ctx, "gamma.market")
    return bool(items) and not any(r.ok2xx for r in items)


def _book_failing(ctx):
    items = _rx(ctx, "clob.book")
    return bool(items) and not any(r.ok2xx for r in items)


def _lifecycle_evidence(body):
    if not isinstance(body, dict):
        return {}
    return {k: body.get(k) for k in _LIFECYCLE_KEYS}


def _chk_auth(ctx, entry):
    return _any(
        ctx,
        _source(entry),
        lambda r: r.raw_verified and r.transport_error is None and r.status in (401, 403),
    )


def _chk_rate(ctx, entry):
    return _any(
        ctx,
        _source(entry),
        lambda r: r.raw_verified and r.transport_error is None and r.status == 429,
    )


def _chk_transport(ctx, entry):
    return _any(ctx, _source(entry), lambda r: r.raw_verified and r.transport_error is not None)


def _chk_5xx(ctx, entry):
    return _any(
        ctx,
        _source(entry),
        lambda r: (
            r.raw_verified and r.transport_error is None and (r.status is None or r.status >= 500)
        ),
    )


def _invalid_verdict(receipt, source):
    """Return ``(supported, parser_exception)``.

    ``invalid`` (source_run.py:283-288) is DATA for a 4xx outside 401/403/429, or for a 2xx/3xx
    whose hash-verified raw bytes the frozen production parsers (source_bridge.parse_source:
    ``_strict_json`` then ``gamma_market`` / ``clob_book``) reject with ValueError, TypeError or
    KeyError. A 2xx/3xx the parser accepts is not invalid. 1xx/5xx/401/403/429 never support it."""
    if not (
        receipt.raw_verified and receipt.transport_error is None and isinstance(receipt.status, int)
    ):
        return False, None
    if 400 <= receipt.status < 500:
        return receipt.status not in (401, 403, 429), None
    if not 200 <= receipt.status < 400:
        return False, None
    try:
        value = _strict_json(receipt.raw_text)
        if source == "clob.book":
            clob_book(value, expected_token=receipt.token_id)
        elif source == "gamma.market":
            gamma_market(value, expected_market=receipt.market_id)
        else:
            return False, None
    except (ValueError, TypeError, KeyError) as exc:
        return True, f"{type(exc).__name__}: {exc}"[:200]
    return False, None


def _invalid_supported(receipt, source):
    return _invalid_verdict(receipt, source)[0]


def _chk_invalid(ctx, entry):
    source = _source(entry)
    hits = []
    for r in _rx(ctx, source):
        ok, exc = _invalid_verdict(r, source)
        if ok:
            hits.append((r, exc))
    if not hits:
        return False, _cite(_rx(ctx, source))
    citation = [{**r.cite(), "parser_exception": exc} for r, exc in hits]
    return True, citation


def _chk_empty_side(ctx, entry):
    r, body = _book(ctx)
    if r is None:
        return False, _cite(_rx(ctx, "clob.book"))
    empty = [
        side
        for side in ("bids", "asks")
        if not [lv for lv in _levels(body, side) if lv[1] is not None and lv[1] > 0]
    ]
    return bool(empty), {**r.cite(), "empty_sides": empty}


def _chk_non_decimal(ctx, entry):
    r, body = _book(ctx)
    if r is None:
        return False, _cite(_rx(ctx, "clob.book"))
    bad = any(lv == (None, None) for side in ("bids", "asks") for lv in _levels(body, side))
    return bad, {**r.cite(), "non_decimal_level": bad}


def _chk_crossed(ctx, entry):
    r, body = _book(ctx)
    if r is None:
        return False, _cite(_rx(ctx, "clob.book"))
    bids = [lv for lv in _levels(body, "bids") if lv[1] is not None and lv[1] > 0]
    asks = [lv for lv in _levels(body, "asks") if lv[1] is not None and lv[1] > 0]
    if not bids or not asks:
        return False, r.cite()
    bid, ask = max(p for p, _ in bids), min(p for p, _ in asks)
    bad = bid > ask or bid < 0 or ask > 1
    return bad, {**r.cite(), "best_bid": str(bid), "best_ask": str(ask)}


def _chk_duplicate(ctx, entry):
    r, body = _book(ctx)
    if r is None:
        return False, _cite(_rx(ctx, "clob.book"))
    dup = any(
        len({p for p, _ in _levels(body, side)}) != len(_levels(body, side))
        for side in ("bids", "asks")
    )
    return dup, {**r.cite(), "duplicate_price_level": dup}


def _lifecycle(predicate, label):
    def check(ctx, entry):
        r, body = _gamma(ctx)
        if r is None:
            return False, _cite(_rx(ctx, "gamma.market"))
        life = _lifecycle_evidence(body)
        return bool(predicate(life)), {**r.cite(), "lifecycle": life, "claim": label}

    return check


_chk_closed = _lifecycle(lambda v: v.get("closed") is True, "closed")
_chk_archived = _lifecycle(lambda v: v.get("archived") is True, "archived")
_chk_not_accepting = _lifecycle(
    lambda v: v.get("active") is False or v.get("acceptingOrders") is False, "not_accepting"
)
_chk_unknown = _lifecycle(lambda v: any(v.get(k) is None for k in _LIFECYCLE_KEYS), "unknown")


def _token_absent(ctx):
    r, body = _gamma(ctx)
    if r is None:
        return False
    tokens = body.get("clobTokenIds")
    if isinstance(tokens, str):
        try:
            tokens = json.loads(tokens)
        except ValueError:
            return True
    return not isinstance(tokens, list) or str(ctx.get("token_id")) not in [str(t) for t in tokens]


def _chk_unresolved(ctx, entry):
    if _gamma_failing(ctx):
        return True, _cite(_rx(ctx, "gamma.market"))
    if _token_absent(ctx):
        r, _ = _gamma(ctx)
        return True, {**r.cite(), "token_absent_from_gamma": ctx.get("token_id")}
    if _book_failing(ctx):
        return True, _cite(_rx(ctx, "clob.book"))  # mapping is None whenever the book failed
    return False, _cite(_rx(ctx, "gamma.market"))


def _chk_conflict(ctx, entry):
    g, gb = _gamma(ctx)
    b, bb = _book(ctx)
    if g is None or b is None:
        return False, _cite(_rx(ctx, "gamma.market") + _rx(ctx, "clob.book"))
    left, right = gb.get("conditionId"), bb.get("market")
    return (
        isinstance(left, str) and isinstance(right, str) and left != right,
        {"gamma": g.cite(), "book": b.cite(), "gamma_condition": left, "book_market": right},
    )


def _chk_unresolved_or_conflict(ctx, entry):
    ok, cite = _chk_unresolved(ctx, entry)
    if ok:
        return ok, cite
    return _chk_conflict(ctx, entry)


def _chk_lifecycle_not_active(ctx, entry):
    if _gamma_failing(ctx) or _book_failing(ctx):
        return True, _cite(_rx(ctx, "gamma.market") + _rx(ctx, "clob.book"))
    r, body = _gamma(ctx)
    if r is None:
        return False, []
    life = _lifecycle_evidence(body)
    bad = life != _ACTIVE
    return bad, {**r.cite(), "lifecycle": life}


def _chk_frame_mapping(ctx, entry):
    cmp_ = ctx.get("identity_comparison")
    if not isinstance(cmp_, dict):
        return False, None
    state = cmp_.get("state")
    cite = {
        "compare_mapping_state": state,
        "frame_mapping_version": cmp_.get("frame_mapping_version"),
        "current_mapping_version": cmp_.get("current_mapping_version"),
    }
    if state == "mapping_differs":
        g, _ = _gamma(ctx)
        ok = (
            cmp_.get("current_mapping_version") is not None
            and cmp_["current_mapping_version"] != cmp_.get("frame_mapping_version")
            and g is not None
        )
        return ok, {**cite, "gamma": g.cite() if g else None, "differing_field": "mapping_version"}
    if state == "mapping_unavailable":
        ok, support = _chk_unresolved(ctx, entry)
        return ok and cmp_.get("current_mapping_version") is None, {**cite, "support": support}
    return False, cite


def _chk_target_mapping(ctx, entry):
    frozen, fresh = ctx.get("frozen_mapping"), ctx.get("fresh_mapping")
    if isinstance(frozen, dict) and isinstance(fresh, dict):
        fields = [
            k
            for k in ("market_id", "mapping_version", "outcome_index", "outcome_label")
            if frozen.get(k) != fresh.get(k)
        ]
        if fields:
            return True, {"differing_fields": fields}
    return _chk_conflict(ctx, entry)


def _chk_origin_mapping(ctx, entry):
    cmp_ = ctx.get("identity_comparison") or {}
    member, quote = ctx.get("member") or {}, ctx.get("quote") or {}
    mapping = quote.get("mapping") or {}
    pairs = {
        "token_id": (quote.get("token_id"), member.get("token_id")),
        "condition_id": (quote.get("condition_id"), member.get("condition_id")),
        "market_id": (mapping.get("market_id"), member.get("market_id")),
        "outcome_index": (mapping.get("outcome_index"), member.get("outcome_index")),
        "outcome_label": (mapping.get("outcome_label"), member.get("outcome_label")),
    }
    fields = [k for k, (a, b) in pairs.items() if a != b]
    if cmp_.get("core_identity_equal") is False:
        fields.append("compare_mapping:" + str(cmp_.get("state")))
    # A different token or condition is a defect of ours (the sample is keyed by them), never a
    # provider mapping change: only mapping, market and outcome differences are DATA_SOURCE.
    engineering = [k for k in fields if k in ("token_id", "condition_id")]
    return bool(fields) and not engineering, {
        "differing_fields": fields,
        "engineering_fields": engineering,
        "compare_mapping_state": cmp_.get("state"),
    }


def _chk_socket_error(ctx, entry):
    event = ctx.get("socket_terminal_event") or {}
    return event.get("error") is not None, {
        "terminal_event": event.get("kind"),
        "error": event.get("error"),
    }


def _recurse_quote(ctx, state, label):
    sub = _finding("quote_state", state, stage=label, ctx=ctx)
    return sub["class"] in DATA_CLASSES, {
        "quote_state": state,
        "class": sub["class"],
        "rule": sub["rule"],
        "citation": sub["citation"],
    }


def _chk_pre_snapshot(ctx, entry):
    state = ctx.get("pre_quote_state")
    if state in (None, "observed"):
        return False, {"pre_quote_state": state}
    return _recurse_quote(ctx, state, "pre_snapshot")


def _chk_pre_identity(ctx, entry):
    quote, member, ident = ctx.get("pre_quote"), ctx.get("member") or {}, ctx.get("identity") or {}
    if not isinstance(quote, dict):
        return False, None
    mapping = quote.get("mapping")
    if mapping is None:
        ok, cite = _chk_unresolved(ctx, entry)
        return ok, {"mapping": None, "support": cite}
    fields = [
        k
        for k, (a, b) in {
            "token_id": (quote.get("token_id"), member.get("token_id")),
            "condition_id": (quote.get("condition_id"), ident.get("condition_id")),
            "market_id": (mapping.get("market_id"), member.get("market_id")),
        }.items()
        if a != b
    ]
    engineering = [k for k in fields if k in ("token_id", "condition_id")]
    return bool(fields) and not engineering, {
        "differing_fields": fields,
        "engineering_fields": engineering,
    }


def _chk_pre_lifecycle(ctx, entry):
    quote = ctx.get("pre_quote") or {}
    life = (quote.get("mapping") or {}).get("lifecycle")
    if life == _ACTIVE or life is None:
        return False, {"pre_lifecycle": life}
    ok, cite = _chk_lifecycle_not_active(ctx, entry)
    return ok, {"pre_lifecycle": life, "support": cite}


def _chk_history_snapshot(ctx, entry):
    for key in ("pre_quote_state", "origin_quote_state"):
        state = ctx.get(key)
        if state not in (None, "observed"):
            sub_ctx = (
                ctx
                if key == "origin_quote_state"
                else {**ctx, "receipts": ctx.get("screen_receipts")}
            )
            ok, cite = _recurse_quote(sub_ctx, state, "history_snapshot")
            if ok:
                return True, {key: state, **cite}
    return False, {
        "pre_quote_state": ctx.get("pre_quote_state"),
        "origin_quote_state": ctx.get("origin_quote_state"),
    }


def _chk_history_identity(ctx, entry):
    prior, current = ctx.get("prior_mapping_version"), ctx.get("current_mapping_version")
    if prior is not None and current is not None and prior != current:
        return True, {"differing_field": "mapping_version", "prior": prior, "current": current}
    return _chk_history_snapshot(ctx, entry)


def _chk_target_closed(ctx, entry):
    return _chk_closed(ctx, entry)


CHECKS = {
    "http_auth_denied": _chk_auth,
    "http_rate_limited": _chk_rate,
    "transport_error": _chk_transport,
    "http_5xx_or_none": _chk_5xx,
    "http_invalid": _chk_invalid,
    "book_empty_side": _chk_empty_side,
    "book_non_decimal": _chk_non_decimal,
    "book_crossed": _chk_crossed,
    "book_duplicate_price": _chk_duplicate,
    "lifecycle_closed": _chk_closed,
    "lifecycle_archived": _chk_archived,
    "lifecycle_not_accepting": _chk_not_accepting,
    "lifecycle_unknown": _chk_unknown,
    "identity_unresolved": _chk_unresolved,
    "identity_conflict": _chk_conflict,
    "identity_unresolved_or_conflict": _chk_unresolved_or_conflict,
    "lifecycle_not_active_or_gamma_failed": _chk_lifecycle_not_active,
    "frame_mapping_citation": _chk_frame_mapping,
    "target_mapping_differs": _chk_target_mapping,
    "origin_mapping_differs": _chk_origin_mapping,
    "socket_error_event": _chk_socket_error,
    "pre_snapshot_citation": _chk_pre_snapshot,
    "pre_identity_citation": _chk_pre_identity,
    "pre_lifecycle_citation": _chk_pre_lifecycle,
    "history_snapshot_citation": _chk_history_snapshot,
    "history_identity_citation": _chk_history_identity,
    "target_lifecycle_closed": _chk_target_closed,
}


# --------------------------------------------------------------------------------------------
# Pure common-mode guard and outcome decision
# --------------------------------------------------------------------------------------------


def common_mode_flags(rows):
    """Systematic-defect signatures over per-member rows.

    Each row is ``{"complete": bool, "limiting": {"stage", "state", "class"} | None,
    "listed_market_failure": bool}``; ``limiting`` is the first non-OK cause in stage order
    screening, window (pre-state), origin, history, target. Flags (FAIL pending diagnosis):

    (a) at least two members, none with a complete chain, and every member shares one identical
        ``(stage, state)`` limiting cause;
    (b) every member's limiting cause is DATA_TRANSPORT;
    (c) at least half of the members have a transport error or an HTTP 4xx receipt on a market
        that was selected from the frame (listed, open under the declared population).

    Two one-sided books among eight is a legitimate data outcome; the identical cause at every
    member, an all-transport failure, or transport/4xx failures at half the members on markets the
    frame had just listed are the signature of a systematic defect (ours or the provider's), which
    must be diagnosed rather than counted as unavailable data.
    """
    if not rows:
        return ["no selected members"]
    flags = []
    limits = [r.get("limiting") for r in rows]
    if len(rows) >= 2 and not any(r["complete"] for r in rows) and all(limits):
        causes = {(c["stage"], c["state"]) for c in limits}
        if len(causes) == 1:
            flags.append(f"every member ends in the same cause {sorted(causes)[0]}")
    if all(limits) and all(c.get("class") == DATA_TRANSPORT for c in limits):
        flags.append("every member's limiting cause is a transport failure")
    failing = sum(1 for r in rows if r.get("listed_market_failure"))
    if 2 * failing >= len(rows):
        flags.append(
            f"{failing} of {len(rows)} members have transport errors or HTTP 4xx on markets "
            "selected from the frame"
        )
    return flags


def decide_outcome(summary):
    """Map an already-computed summary to the exhaustive outcome classes.

    FAIL if any engineering finding, failed E gate or common-mode pattern. INCONCLUSIVE if the
    sufficiency floor is not met. PASS if an observed matched pair exists. Otherwise
    PASS_WITH_LIMITATION with exactly one sub-label.
    """
    reasons = []
    if summary["engineering_findings"]:
        reasons.append(f"{summary['engineering_findings']} engineering finding(s)")
    if summary["failed_gates"]:
        reasons.append("failed gates: " + ",".join(summary["failed_gates"]))
    if summary["common_mode"]:
        reasons.append("common-mode pattern: " + "; ".join(summary["common_mode"]))
    if reasons:
        return "FAIL", reasons
    floor = []
    if summary["complete_chains"] < 1:
        floor.append("no complete chain")
    if summary["authenticated_state_members"] < 1:
        floor.append("no member with authenticated triggered/untriggered state")
    if not summary["strata_report_computed"]:
        floor.append("strata control_pool/controls_wanted not computed")
    if floor:
        return "INCONCLUSIVE", floor
    if summary["pairs_both_complete"] >= 1:
        return "PASS", ["observed matched pair with both members' complete chains"]
    if summary["n_triggered_members"] == 0:
        return (
            "PASS_WITH_LIMITATION:zero_triggered_control_matching_not_exercised",
            ["no member has an authenticated triggered state"],
        )
    if summary["control_assignments"] == 0:
        if summary["n_triggered_members"] == summary["n_members"]:
            return (
                "PASS_WITH_LIMITATION:all_triggered_no_control",
                ["every selected member is triggered; no untriggered control exists"],
            )
        if not summary.get("control_pool_zero_in_triggered_strata"):
            return (
                "FAIL",
                ["no control drawn although a stratum with a trigger has a non-empty control pool"],
            )
        return (
            "PASS_WITH_LIMITATION:no_eligible_untriggered",
            ["triggered members exist but no eligible untriggered member in their strata"],
        )
    return (
        "PASS_WITH_LIMITATION:pair_member_unobserved_data_reason",
        [
            "a matched pair was drawn but a member's chain is incomplete for a classified "
            "DATA reason"
        ],
    )


# --------------------------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------------------------


def _default_roots(panel_root):
    from .activation import activation_root
    from .panel_selection import selection_root
    from .runtime import run_root
    from .screening_worker import worker_root

    return (
        selection_root(panel_root),
        worker_root(panel_root),
        run_root(panel_root),
        activation_root(panel_root),
    )


def _gate(passed, reasons, **evidence):
    return {"pass": bool(passed), "reasons": reasons, **evidence}


def evaluate_d116(
    panel_root,
    selection_root=None,
    worker_root=None,
    runtime_root=None,
    *,
    activation_root=None,
    launch_commit=None,
    protocol_check=True,
):
    """Evaluate one retained D116 run; the only authoritative entry point.

    ``launch_commit`` (the commit the run was launched from) is required: gate E0 fails closed
    without it. The root overrides and ``protocol_check=False`` are test aids: using any of them
    forces ``FAIL`` (reason ``test_override_used``) and ``authoritative`` false. Any exception
    yields a report with ``FAIL`` (reason ``evaluator_exception:<type>``). Absence of a report is
    itself a FAIL (protocol section 4.4).
    """
    overrides = [
        name
        for name, value in (
            ("selection_root", selection_root),
            ("worker_root", worker_root),
            ("runtime_root", runtime_root),
            ("activation_root", activation_root),
        )
        if value is not None
    ]
    if not protocol_check:
        overrides.append("no_protocol_check")
    return _guarded(
        panel_root,
        selection_root,
        worker_root,
        runtime_root,
        activation_root,
        launch_commit,
        overrides,
        enforce=True,
    )


def evaluate_d116_logic_only_test_aid(panel_root, **roots):
    """TEST AID ONLY. Applies every gate except E0 and the frozen-value comparisons to a
    (typically synthetic) tree. The report is always ``authoritative: false`` and carries
    ``non_authoritative_logic_only``; its outcome is never a D116 result, and no command-line
    entry reaches this function."""
    return _guarded(
        panel_root,
        roots.get("selection_root"),
        roots.get("worker_root"),
        roots.get("runtime_root"),
        roots.get("activation_root"),
        roots.get("launch_commit"),
        [],
        enforce=False,
    )


def _guarded(panel_root, selection, worker, runtime, activation, launch_commit, overrides, enforce):
    try:
        panel_root = Path(panel_root)
        defaults = _default_roots(panel_root)
        ev = _Evaluation(
            _Reader(),
            panel_root,
            Path(selection) if selection else defaults[0],
            Path(worker) if worker else defaults[1],
            Path(runtime) if runtime else defaults[2],
            Path(activation) if activation else defaults[3],
            launch_commit=launch_commit,
            overrides=overrides,
            enforce=enforce,
            derived=not (selection or worker or runtime or activation),
        )
        return ev.run()
    except Exception as exc:  # noqa: BLE001 - every failure must become a FAIL report
        return {
            "evaluator_version": EVALUATOR_VERSION,
            "classification_table_sha256": TABLE_SHA256,
            "roots": {"panel": str(panel_root)},
            "authoritative": False,
            "non_authoritative_logic_only": not enforce,
            "test_override_used": list(overrides),
            "outcome": "FAIL",
            "outcome_reasons": [f"evaluator_exception:{type(exc).__name__}"],
            "gates": {},
            "summary": {},
            "pairs": [],
            "common_mode": [],
            "finding_counts": {},
            "findings": [],
            "members": {},
            "timeline": {},
            "diagnostics": {},
        }


class _Evaluation:
    def __init__(
        self,
        reader,
        panel,
        selection,
        worker,
        runtime,
        activation,
        *,
        launch_commit,
        overrides,
        enforce,
        derived,
    ):
        self.r, self.panel, self.selection = reader, panel, selection
        self.worker, self.runtime, self.activation = worker, runtime, activation
        self.launch_commit, self.overrides = launch_commit, list(overrides)
        self.enforce, self.derived = enforce, derived
        self.expectation = D116_PROTOCOL if enforce else None
        self.members = {}  # market_id -> record
        self.order = []

    # ----- helpers ------------------------------------------------------------------------
    def screen_available(self):
        return (self.screen_report.get("__ack__") or {}).get("durable_ack")

    def add(self, member, stage, namespace, value, detail=None, ctx=None):
        item = _finding(namespace, value, stage=stage, member=member, detail=detail, ctx=ctx)
        self.r.findings.append(item)
        return item

    def failure_files(self):
        for root, namespace, stage in (
            (self.selection, "selection_failure", "selection"),
            (self.activation, "activation_failure", "activation"),
            (self.worker, "worker_failure", "screening"),
            (self.runtime, "runtime_failure", "runtime"),
        ):
            if (root / f"{namespace}.json").exists():
                self.add(None, stage, "artifact", namespace, str(root.name))

    # ----- main -----------------------------------------------------------------------------
    def run(self):
        r = self.r
        self.failure_files()
        self.load()
        for market in self.order:
            self.member_stages(self.members[market])
        gates = self.gates()
        pairs = self.pairs()
        common = self.common_mode()
        timeline = self.timeline()
        summary = self.summarise(gates, pairs, common)
        outcome, outcome_reasons = decide_outcome(summary)
        if self.overrides:
            outcome = "FAIL"
            outcome_reasons = ["test_override_used: " + ",".join(self.overrides), *outcome_reasons]
        if not self.enforce:
            outcome_reasons = ["non_authoritative_logic_only", *outcome_reasons]
        authoritative = bool(self.enforce and not self.overrides and gates["E0"]["pass"])
        counts = Counter(f["class"] for f in r.findings)
        return {
            "evaluator_version": EVALUATOR_VERSION,
            "classification_table_sha256": TABLE_SHA256,
            "authoritative": authoritative,
            "non_authoritative_logic_only": not self.enforce,
            "test_override_used": self.overrides,
            "launch_commit": self.launch_commit,
            "required_ancestor_commit": REQUIRED_ANCESTOR_COMMIT,
            "roots": {
                "panel": str(self.panel),
                "selection": str(self.selection),
                "worker": str(self.worker),
                "runtime": str(self.runtime),
                "activation": str(self.activation),
            },
            "outcome": outcome,
            "outcome_reasons": outcome_reasons,
            "gates": gates,
            "summary": summary,
            "pairs": pairs,
            "common_mode": common,
            "finding_counts": dict(sorted(counts.items())),
            "findings": [f for f in r.findings if f["class"] != OK],
            "members": {m: self.public(self.members[m]) for m in self.order},
            "timeline": timeline,
            "diagnostics": self.diagnostics(),
        }

    # ----- loading ---------------------------------------------------------------------------
    def load(self):
        r = self.r
        self.panel_policy = r.pair(self.panel, "panel_policy", "panel") or {}
        self.sel_policy = r.pair(self.selection, "selection_policy", "selection") or {}
        self.sel_plan = r.pair(self.selection, "selection_plan", "selection") or {}
        self.sel_report = r.pair(self.selection, "selection_report", "selection") or {}
        self.sel_original = (
            r.plain(
                self.selection / "fs2_frame_read_original" / "original_report.json", "selection"
            )
            or {}
        )
        self.frame_read_policy = (
            r.pair(self.selection / "fs2_frame_read_original", "read_policy", "selection") or {}
        )
        self.read_batch = self.worker / "fs2_runtime_read_batch"
        self.rt_read_policy = r.pair(self.read_batch, "read_policy", "screening") or {}
        self.read_receipt = r.pair(self.read_batch, "read_receipt", "screening") or {}
        self.worker_policy = r.pair(self.worker, "worker_policy", "screening") or {}
        self.worker_report = r.pair(self.worker, "worker_report", "screening") or {}
        batch = self.worker / "fs2_screening_batch"
        self.screen_policy = r.pair(batch, "screening_policy", "screening") or {}
        self.screen_report = r.pair(batch, "screening_report", "screening") or {}
        self.completion = r.pair(batch, "screening_completion_policy", "screening") or {}
        self.act_policy = r.pair(self.activation, "activation_policy", "activation") or {}
        self.act_facts = r.pair(self.activation, "activation_facts", "activation") or {}
        self.rt_policy = r.pair(self.runtime, "runtime_policy", "runtime") or {}
        self.rt_report = r.pair(self.runtime, "runtime_report", "runtime") or {}
        self.protocol = self.panel_policy.get("protocol") or {}
        self.plan = self.screen_report.get("plan") or {}
        # Selected members come from the frozen screening assignment, indexed as the worker did.
        for index in range(len(self.screen_policy.get("selected") or [])):
            intent = r.pair(self.worker, f"intent_{index:03d}", "screening")
            item = (intent or {}).get("item") or self.screen_policy["selected"][index]
            member = item.get("member") or {}
            market = member.get("market_id")
            if market is None:
                continue
            record = {
                "market_id": market,
                "token_id": member.get("token_id"),
                "index": index,
                "item": item,
                "member": member,
                "identity": item.get("identity") or {},
                "stages": {},
                "causes": [],
                "roles": [],
                "assessment_state": None,
            }
            self.members[market] = record
            self.order.append(market)
        self.by_intent = {}
        origins_dir = self.runtime / "origins"
        if origins_dir.is_dir():
            for folder in sorted(p for p in origins_dir.iterdir() if p.is_dir()):
                intent = r.pair(folder, "origin_intent", "origin", None)
                market = ((intent or {}).get("slot") or {}).get("market_id")
                if market in self.members:
                    self.members[market]["origin_dir"] = folder
                    self.members[market]["origin_intent"] = intent
                    self.by_intent[folder.name] = market
                elif intent is not None:
                    r.note(
                        "origin",
                        "missing_or_unreadable_artifact",
                        f"origin {folder.name} market {market} not in screened selection",
                    )
        self.target_dirs = {}
        targets_dir = self.runtime / "targets"
        if targets_dir.is_dir():
            for folder in sorted(p for p in targets_dir.iterdir() if p.is_dir()):
                intent = r.pair(folder, "target_intent", "target")
                origin_id = ((intent or {}).get("job") or {}).get("origin_id")
                market = self.by_intent.get(origin_id)
                if market:
                    self.members[market].setdefault("target_dirs", []).append(folder)
                elif intent is not None:
                    r.note(
                        "target",
                        "missing_or_unreadable_artifact",
                        f"target {folder.name} origin_id {origin_id} matches no origin",
                    )
        for roles in self.plan.get("assignments") or []:
            if roles.get("market_id") in self.members:
                self.members[roles["market_id"]]["roles"].append(roles)
        for entry in self.plan.get("assessment_inventory") or []:
            if entry.get("market_id") in self.members:
                self.members[entry["market_id"]]["inventory"] = entry
        for state in self.screen_report.get("states") or []:
            if state.get("market_id") in self.members:
                self.members[state["market_id"]]["screening"] = state

    # ----- stages ----------------------------------------------------------------------------
    def member_stages(self, m):
        market = m["market_id"]
        self.screening_stage(m)
        self.window_stage(m)
        self.origin_stage(m)
        self.target_stage(m)
        stages = m["stages"]
        origin_ok = stages.get("origin", {}).get("state") == "observed"
        history_ok = stages.get("history", {}).get("eligible") is True
        target_ok = stages.get("target", {}).get("state") == "observed"
        m["complete_chain"] = bool(origin_ok and history_ok and target_ok)
        if not m["complete_chain"]:
            # First non-OK cause in stage order; screening and window causes count (common mode).
            for stage in ("screening", "window", "origin", "history", "target"):
                info = stages.get(stage) or {}
                if stage in ("origin", "target") and info.get("state") == "observed":
                    continue
                if stage == "history" and info.get("eligible") is not False:
                    continue
                for cause in info.get("causes", []):
                    m["causes"].append({"stage": stage, **cause})
                if info.get("causes"):
                    break
            if not m["causes"]:
                m["causes"].append(
                    {
                        "stage": "chain",
                        "state": "unknown",
                        "class": ENGINEERING,
                        "rule": "chain_incomplete_without_classified_cause",
                    }
                )
                self.add(
                    market,
                    "chain",
                    "artifact",
                    "missing_or_unreadable_artifact",
                    "chain incomplete without a classified cause",
                )

    def screening_stage(self, m):
        market = m["market_id"]
        index = m["index"]
        rx = _captures(self.r, self.worker / f"fs2_capture_screen_{index:03d}", "screening", market)
        m["screen_receipts"] = rx
        for source, items in rx.items():
            for item in items:
                expect = market if source == "gamma.market" else m["token_id"]
                got = item.market_id if source == "gamma.market" else item.token_id
                if source in ("gamma.market", "clob.book") and got != expect:
                    self.add(
                        market,
                        "screening",
                        "trigger_reason",
                        "requested_identity_differs",
                        f"{source} receipt requested {got}",
                    )
        ctx = {"receipts": rx, "token_id": m["token_id"], "market_id": market}
        state = m.get("screening")
        info = {"state": None, "reasons": [], "causes": [], "effective_state": None}
        m["stages"]["screening"] = info
        if state is None:
            self.add(
                market,
                "screening",
                "screening_state",
                "not_assessed",
                "no screening state row for selected member",
            )
            info["state"] = "missing_state_row"
            return
        info["state"] = state.get("state")
        info["reasons"] = list(state.get("reasons") or [])
        self.add(market, "screening", "screening_state", state.get("state"))
        ctx["identity_comparison"] = state.get("identity_comparison")
        for reason in info["reasons"]:
            f = self.add(market, "screening", "trigger_reason", reason, ctx=ctx)
            info["causes"].append(
                {"state": reason, "class": f["class"], "rule": f["rule"], "citation": f["citation"]}
            )
        inventory = m.get("inventory") or {}
        info["effective_state"] = inventory.get("effective_state")
        for reason in inventory.get("reasons") or []:
            for part in str(reason).split(";"):
                if part in CLASSIFICATION_TABLE["assessment_reason"]:
                    self.add(market, "screening", "assessment_reason", part)
        if inventory and info["effective_state"] != state.get("state"):
            self.add(
                market,
                "screening",
                "assessment_reason",
                "assessment_state_differs",
                f"states={state.get('state')} inventory={info['effective_state']}",
            )
        m["assessment_state"] = info["effective_state"]
        if state.get("state") in ("triggered", "untriggered") and info[
            "effective_state"
        ] == state.get("state"):
            evidence = (inventory.get("assessment") or {}).get("evidence_id")
            m["authenticated_state"] = bool(evidence and _HEX64.fullmatch(str(evidence)))
        else:
            m["authenticated_state"] = False
        if state.get("state") in ("triggered", "untriggered") and not m["authenticated_state"]:
            self.add(
                market,
                "screening",
                "artifact",
                "missing_or_unreadable_artifact",
                "triggered/untriggered state without an authenticated assessment evidence_id",
            )

    def window_stage(self, m):
        market, index = m["market_id"], m["index"]
        info = {"missing_reason": None, "terminal": None, "close_state": None, "causes": []}
        m["stages"]["window"] = info
        entry = self.r.pair(self.worker, f"window_{index:03d}", "window", market)
        if entry is None:
            info["missing_reason"] = "entry_missing"
            return
        missing = entry.get("missing_reason")
        info["missing_reason"] = missing
        book_root = self.worker / Path(str((entry.get("item") or {}).get("book_root", ""))).name
        pre_facts = self.r.pair(book_root, "book_facts", "window", market)
        snapshots = (((pre_facts or {}).get("projection") or {}).get("snapshots")) or []
        pre_quote = snapshots[0]["quote"] if len(snapshots) == 1 else None
        m["pre_quote"] = pre_quote
        ctx = {
            "receipts": m.get("screen_receipts", {}),
            "token_id": m["token_id"],
            "member": m["member"],
            "identity": m["identity"],
            "pre_quote": pre_quote,
            "pre_quote_state": (pre_quote or {}).get("state"),
        }
        key = "none" if missing is None else missing
        f = self.add(market, "window", "window_missing", key, ctx=ctx)
        if missing is not None:
            info["causes"].append(
                {"state": key, "class": f["class"], "rule": f["rule"], "citation": f["citation"]}
            )
            return
        socket = entry.get("socket") or {}
        terminal, close = socket.get("terminal"), socket.get("close_state")
        info["terminal"], info["close_state"] = terminal, close
        events = {}
        folder = self.worker / f"fs2_socket_window_{index:03d}"
        for path in sorted(folder.glob("event_*.json")):
            if path.name.endswith("_ack.json"):
                continue
            event = self.socket_event(path, market)
            if event:
                events[event.get("ordinal")] = event
        sock_report = self.r.pair(folder, "socket_window_report", "window", market, required=False)
        count = (sock_report or {}).get("event_count")
        if events:
            first = min(events)
            last_expected = count if type(count) is int else max(events)
            if sorted(events) != list(range(first, last_expected + 1)):
                self.r.note(
                    "window",
                    "missing_or_unreadable_artifact",
                    f"socket event ordinals not contiguous from {first} through "
                    f"event_count {count}: have {sorted(events)}",
                    market,
                )
        elif type(count) is int and count > 0:
            self.r.note(
                "window",
                "missing_or_unreadable_artifact",
                f"report event_count {count} but no readable events",
                market,
            )
        last = events[max(events)] if events else {}
        terminal_event = next(
            (e for _, e in sorted(events.items()) if e.get("kind") == terminal), {}
        )
        ctx["socket_terminal_event"] = terminal_event
        f = self.add(market, "window", "socket_terminal", terminal, ctx=ctx)
        if f["class"] != OK:
            info["causes"].append(
                {
                    "state": terminal,
                    "class": f["class"],
                    "rule": f["rule"],
                    "citation": f["citation"],
                }
            )
        valid_close = close == "closed" or (
            close == "not_connected" and terminal == "connect_error"
        )
        if valid_close or close not in CLASSIFICATION_TABLE["socket_close_state"]:
            self.add(market, "window", "socket_close_state", str(close))
        else:
            self.add(
                market,
                "window",
                "socket_close_state",
                "close_error",
                f"close_state {close} inconsistent with terminal {terminal}",
            )
        info["last_event"] = last.get("kind")

    def socket_event(self, path, market):
        """Load one journal event, verifying its ack hash and the sibling raw frame hash."""
        try:
            raw = path.read_bytes()
            event = json.loads(raw)
            ack = json.loads(path.with_name(path.stem + "_ack.json").read_bytes())
        except (OSError, ValueError) as exc:
            self.r.note(
                "window", "missing_or_unreadable_artifact", f"{path}: {type(exc).__name__}", market
            )
            return None
        if ack.get("payload_hash") != hashlib.sha256(raw).hexdigest():
            self.r.note("window", "artifact_hash_mismatch", str(path), market)
            return None
        frame = path.with_suffix(".bin")
        if event.get("raw_hash") is not None and not frame.exists():
            self.r.note(
                "window",
                "missing_or_unreadable_artifact",
                f"raw frame {frame.name} missing for recorded raw_hash",
                market,
            )
            return None
        if frame.exists() and hashlib.sha256(frame.read_bytes()).hexdigest() != event.get(
            "raw_hash"
        ):
            self.r.note("window", "artifact_hash_mismatch", str(frame), market)
            return None
        return event

    def origin_stage(self, m):
        market = m["market_id"]
        info = {"state": None, "causes": [], "eligible": None}
        history = {"eligible": None, "reasons": [], "causes": [], "freeze_reasons": []}
        m["stages"]["origin"], m["stages"]["history"] = info, history
        folder = m.get("origin_dir")
        report_row = next(
            (
                o
                for o in (self.rt_report.get("origins") or [])
                if self.by_intent.get(o.get("intent_id")) == market
            ),
            None,
        )
        if folder is None or report_row is None:
            info["state"] = "missing_origin"
            self.add(
                market,
                "origin",
                "artifact",
                "missing_or_unreadable_artifact",
                "no origin directory or runtime origin result",
            )
            info["causes"].append(
                {
                    "state": "missing_origin",
                    "class": ENGINEERING,
                    "rule": "artifact:missing_or_unreadable_artifact",
                }
            )
            history["eligible"] = None
            return
        state = report_row.get("state")
        info["state"] = state
        rx = _captures(self.r, folder / "fs2_capture_origin", "origin", market)
        m["origin_receipts"] = rx
        facts = self.r.pair(folder, "origin_facts", "origin", market, required=False)
        failure = self.r.pair(folder, "origin_failure", "origin", market, required=False)
        receipt = self.r.pair(folder, "origin_receipt", "origin", market)
        m["origin_facts"], m["origin_receipt"] = facts, receipt
        if failure is not None:
            self.add(market, "origin", "artifact", "origin_failure", failure.get("state"))
        projection = (facts or {}).get("projection") or {}
        quote = projection.get("quote") or {}
        ctx = {
            "receipts": rx,
            "token_id": m["token_id"],
            "market_id": market,
            "member": (m.get("origin_intent") or {}).get("member") or m["member"],
            "quote": quote,
            "identity_comparison": projection.get("identity_comparison"),
        }
        f = self.add(market, "origin", "origin_state", state, ctx=ctx)
        if f["class"] != OK:
            info["causes"].append(
                {"state": state, "class": f["class"], "rule": f["rule"], "citation": f["citation"]}
            )
        # History: only members with a pre-origin window dependency carry a pre_origin_window.
        window = projection.get("pre_origin_window")
        if window is None:
            history["eligible"] = False
            wcauses = (m["stages"].get("window") or {}).get("causes") or []
            if wcauses:
                history["causes"] = list(wcauses)
            elif facts is not None:
                self.add(
                    market,
                    "history",
                    "artifact",
                    "missing_or_unreadable_artifact",
                    "origin facts without a pre_origin_window",
                )
                history["causes"].append(
                    {
                        "state": "no_window",
                        "class": ENGINEERING,
                        "rule": "artifact:missing_or_unreadable_artifact",
                    }
                )
            return
        history["eligible"] = bool(window.get("eligible_at_freeze"))
        history["reasons"] = list(window.get("history_reasons") or [])
        history["freeze_reasons"] = list(window.get("freeze_reasons") or [])
        hctx = {
            **ctx,
            "screen_receipts": m.get("screen_receipts", {}),
            "pre_quote_state": (m.get("pre_quote") or {}).get("state"),
            "origin_quote_state": quote.get("state"),
            "prior_mapping_version": window.get("prior_mapping_version"),
            "current_mapping_version": window.get("current_mapping_version"),
        }
        for reason in history["reasons"]:
            f = self.add(market, "history", "history_reason", reason, ctx=hctx)
            history["causes"].append(
                {"state": reason, "class": f["class"], "rule": f["rule"], "citation": f["citation"]}
            )
        for reason in history["freeze_reasons"]:
            if reason in history["reasons"]:
                continue
            f = self.add(market, "history", "freeze_reason", reason, ctx=hctx)
            history["causes"].append(
                {"state": reason, "class": f["class"], "rule": f["rule"], "citation": f["citation"]}
            )
        if not history["eligible"] and not history["causes"]:
            self.add(
                market,
                "history",
                "artifact",
                "missing_or_unreadable_artifact",
                "ineligible history without a recorded reason",
            )
            history["causes"].append(
                {
                    "state": "no_reason",
                    "class": ENGINEERING,
                    "rule": "artifact:missing_or_unreadable_artifact",
                }
            )
        history["socket_terminal"] = window.get("socket_terminal")
        history["socket_close_state"] = window.get("socket_close_state")

    def target_stage(self, m):
        market = m["market_id"]
        info = {"state": None, "attempt_states": [], "exclusions": [], "causes": []}
        m["stages"]["target"] = info
        origin_state = (m["stages"].get("origin") or {}).get("state")
        outcome = next(
            (
                o
                for o in (self.rt_report.get("outcomes") or [])
                if self.by_intent.get(o.get("origin_id")) == market
            ),
            None,
        )
        dirs = m.get("target_dirs") or []
        rx = {}
        facts = []
        for folder in dirs:
            for source, items in _captures(
                self.r, folder / "fs2_capture_target", "target", market
            ).items():
                rx.setdefault(source, []).extend(items)
            for name in ("target_failure",):
                if self.r.pair(folder, name, "target", market, required=False) is not None:
                    self.add(market, "target", "artifact", "target_failure")
            f = self.r.pair(folder, "target_facts", "target", market, required=False)
            if f is not None:
                facts.append(f)
        m["target_receipts"] = rx
        for attempt in self.rt_report.get("attempts") or []:
            if self.by_intent.get(attempt.get("origin_id")) == market:
                info["attempt_states"].append(attempt.get("state"))
        if outcome is None:
            info["state"] = "missing_outcome"
            self.add(
                market,
                "target",
                "artifact",
                "missing_or_unreadable_artifact",
                "no runtime outcome for origin",
            )
            info["causes"].append(
                {
                    "state": "missing_outcome",
                    "class": ENGINEERING,
                    "rule": "artifact:missing_or_unreadable_artifact",
                }
            )
            return
        state = outcome.get("state")
        info["state"] = state
        origin_class = None
        for attempt_state in info["attempt_states"]:
            f = self.add(market, "target", "target_attempt_state", attempt_state)
            if f["class"] != OK:
                info["causes"].append(
                    {
                        "state": attempt_state,
                        "class": f["class"],
                        "rule": f["rule"],
                        "citation": None,
                    }
                )
        if not info["attempt_states"]:
            self.add(
                market,
                "target",
                "artifact",
                "missing_or_unreadable_artifact",
                "no target attempt recorded",
            )
            info["causes"].append(
                {
                    "state": "no_attempt",
                    "class": ENGINEERING,
                    "rule": "artifact:missing_or_unreadable_artifact",
                }
            )
        ctx = {"receipts": rx, "token_id": m["token_id"], "market_id": market}
        if facts:
            adaptation = (facts[0].get("projection") or {}).get("adaptation") or {}
            ctx["frozen_mapping"] = adaptation.get("frozen_mapping")
            ctx["fresh_mapping"] = adaptation.get("fresh_mapping")
        if state == "origin_ineligible":
            origin_class = next(
                (c["class"] for c in (m["stages"]["origin"].get("causes") or [])), ENGINEERING
            )
            f = self.add(market, "target", "target_outcome", state)
            if origin_state in (None, "observed"):
                self.add(
                    market,
                    "target",
                    "target_outcome",
                    "pending",
                    "origin_ineligible outcome for an observed origin",
                )
                info["causes"].append(
                    {
                        "state": state,
                        "class": ENGINEERING,
                        "rule": "origin_ineligible_with_observed_origin",
                    }
                )
            else:
                info["causes"].append(
                    {"state": state, "class": origin_class, "rule": "follows_origin_state"}
                )
        elif state == "unavailable":
            target = outcome.get("target") or {}
            exclusions = [e.get("reason") for e in (target.get("exclusions") or [])]
            info["exclusions"] = exclusions
            if not exclusions:
                f = self.add(
                    market,
                    "target",
                    "target_exclusion",
                    "no_receipt_in_window",
                    "unavailable without any excluded receipt in the tolerance window",
                )
                info["causes"].append(
                    {
                        "state": "no_receipt_in_window",
                        "class": f["class"],
                        "rule": f["rule"],
                        "citation": None,
                    }
                )
            for reason in exclusions:
                f = self.add(market, "target", "target_exclusion", reason, ctx=ctx)
                info["causes"].append(
                    {
                        "state": reason,
                        "class": f["class"],
                        "rule": f["rule"],
                        "citation": f["citation"],
                    }
                )
        elif state == "closed":
            f = self.add(market, "target", "target_outcome", state, ctx=ctx)
            info["causes"].append(
                {"state": state, "class": f["class"], "rule": f["rule"], "citation": f["citation"]}
            )
        else:
            f = self.add(market, "target", "target_outcome", state)
            if f["class"] != OK:
                info["causes"].append(
                    {"state": state, "class": f["class"], "rule": f["rule"], "citation": None}
                )

    # ----- gates -------------------------------------------------------------------------------
    def stage_engineering(self, *stages):
        return [f for f in self.r.findings if f["class"] == ENGINEERING and f["stage"] in stages]

    def identity_gate(self):
        """E0: this is the one frozen D116 run, launched from the stated commit, on live data."""
        reasons, evidence = [], {}
        if self.panel.name != FROZEN_PANEL_NAME:
            reasons.append(f"panel root name {self.panel.name} != {FROZEN_PANEL_NAME}")
        if self.overrides or not self.derived:
            reasons.append("roots are not derived from the panel root alone")
        actual = {
            "selection": self.selection,
            "worker": self.worker,
            "activation": self.activation,
            "runtime": self.runtime,
        }
        for key, name in FROZEN_ROOT_NAMES.items():
            if actual[key].name != name or actual[key].parent != self.panel.parent:
                reasons.append(f"{key} root {actual[key].name} != {name} beside the panel root")
        # Implementation commit recorded by every artifact that carries one.
        launch = self.launch_commit
        if not (isinstance(launch, str) and _COMMIT.fullmatch(launch)):
            reasons.append("launch commit absent or not a 40-hex commit")
        commits = {
            "panel_policy.frame_implementation_commit": self.panel_policy.get(
                "frame_implementation_commit"
            ),
            "selection_policy.implementation_commit": self.sel_policy.get("implementation_commit"),
            "frame_read_policy.implementation_commit": self.frame_read_policy.get(
                "implementation_commit"
            ),
            "worker_policy.implementation_commit": self.worker_policy.get("implementation_commit"),
            "runtime_read_policy.implementation_commit": self.rt_read_policy.get(
                "implementation_commit"
            ),
        }
        for name, value in commits.items():
            if not (isinstance(value, str) and _COMMIT.fullmatch(value)):
                reasons.append(f"{name} absent or malformed")
            elif value != launch:
                reasons.append(f"{name} {value} != launch commit {launch}")
        evidence["commits"] = commits
        # Screening schema: the final owned-selection screening contract.
        schemas = {
            "screening_policy": self.screen_policy.get("schema_version"),
            "screening_report": self.screen_report.get("schema_version"),
            "worker_report.screening": (self.worker_report.get("screening") or {}).get(
                "schema_version"
            ),
        }
        for name, value in schemas.items():
            if value != REQUIRED_SCREENING_SCHEMA:
                reasons.append(f"{name} schema {value} != {REQUIRED_SCREENING_SCHEMA}")
        evidence["screening_schemas"] = schemas
        # Provenance: public/prospective throughout, never synthetic/loopback/mock.
        recovery = self.worker_report.get("recovery") or []
        provenance = {
            "frame_original_report": self.sel_original.get("provenance_class"),
            "selection_report": self.sel_report.get("provenance_class"),
            "screening_policy.source": self.screen_policy.get("source_provenance_class"),
            "screening_report": self.screen_report.get("provenance_class"),
            "worker_policy": self.worker_policy.get("provenance_class"),
            "worker_report.screening": (self.worker_report.get("screening") or {}).get(
                "provenance_class"
            ),
            "worker_report.runtime": (self.worker_report.get("runtime") or {}).get(
                "provenance_class"
            ),
            "activation_facts": self.act_facts.get("provenance_class"),
            "runtime_policy": self.rt_policy.get("provenance_class"),
            "runtime_report": self.rt_report.get("provenance_class"),
            "read_receipt.original_provenance_class": self.read_receipt.get(
                "original_provenance_class"
            ),
            "worker_report.recovery[0].original_provenance_class": (
                recovery[0].get("original_provenance_class") if len(recovery) == 1 else None
            ),
        }
        for m in self.members.values():
            index, market = m["index"], m["market_id"]
            for stage, folder in (
                ("screening", self.worker / f"fs2_capture_screen_{index:03d}"),
                ("origin", (m.get("origin_dir") or Path("/nonexistent")) / "fs2_capture_origin"),
            ):
                if folder.is_dir():
                    run = self.r.plain(folder / "run.json", stage, market) or {}
                    provenance[f"{market}.{stage}_capture"] = run.get("provenance_class")
            for n, target in enumerate(m.get("target_dirs") or []):
                if (target / "fs2_capture_target").is_dir():
                    run = self.r.plain(target / "fs2_capture_target" / "run.json", "target", market)
                    provenance[f"{market}.target_capture[{n}]"] = (run or {}).get(
                        "provenance_class"
                    )
            socket_dir = self.worker / f"fs2_socket_window_{index:03d}"
            if socket_dir.is_dir():
                policy = self.r.pair(socket_dir, "socket_window_policy", "window", market) or {}
                report = self.r.pair(socket_dir, "socket_window_report", "window", market) or {}
                transport = policy.get("transport") or {}
                provenance[f"{market}.socket_policy"] = transport.get("provenance_class")
                provenance[f"{market}.socket_report"] = report.get("provenance_class")
                if transport.get("kind") != LIVE_SOCKET_KIND:
                    reasons.append(f"{market}: socket transport kind {transport.get('kind')}")
            elif (m["stages"].get("window") or {}).get("missing_reason") is None:
                reasons.append(f"{market}: socket window artifacts absent")
        bad = {k: v for k, v in sorted(provenance.items()) if v != LIVE_PROVENANCE}
        if bad:
            reasons.append(f"provenance is not {LIVE_PROVENANCE}: {bad}")
        evidence["provenance"] = provenance
        evidence["required_ancestor_commit"] = REQUIRED_ANCESTOR_COMMIT
        evidence["ancestry_note"] = "ancestry of the required commit is a launch precondition"
        return _gate(not reasons, reasons, **evidence)

    def frozen_failures(self):
        """E1 comparison of retained policies with the frozen module constants."""
        reasons = []
        frozen = FROZEN_EXPECTATIONS
        for key, expected in frozen["panel"].items():
            if self.panel_policy.get(key) != expected:
                reasons.append(f"panel_policy.{key} {self.panel_policy.get(key)!r} != {expected!r}")
        worker = self.worker_policy
        for key, expected in frozen["worker"].items():
            actual = worker.get(key)
            if key == "limits":
                actual = {k: (worker.get("limits") or {}).get(k) for k in expected}
            if actual != expected:
                reasons.append(f"worker_policy.{key} {actual!r} != {expected!r}")
        screening = self.screen_policy
        if (screening.get("limits") or {}).get("max_seconds") != frozen["screening_max_seconds"]:
            reasons.append("screening_policy.limits.max_seconds != 600")
        if screening.get("limits") != frozen["screening_limits"]:
            reasons.append("screening_policy.limits differ from screening.LIMITS")
        for key in ("freshness", "rule"):
            if screening.get(key) != frozen["worker"][key]:
                reasons.append(f"screening_policy.{key} differs from the frozen value")
        return reasons

    def gates(self):
        g = {"E0": self.identity_gate()}
        proto = self.protocol
        # E1
        reasons = []
        original = self.sel_original
        if original.get("state") != "exhausted_consistent":
            reasons.append(f"frame state {original.get('state')}")
        start, end = _utc(original.get("interval_start")), _utc(original.get("interval_end"))
        limit = proto.get("max_frame_interval_seconds")
        if start is None or end is None or limit is None or _seconds(end, start) > limit:
            reasons.append(f"interval {_seconds(end, start)} s exceeds {limit}")
        if not _HEX64.fullmatch(str(self.sel_report.get("frame_report_hash"))):
            reasons.append("frame report hash absent")
        pages = self.selection / "pages"
        if not pages.is_dir() or not any(pages.iterdir()):
            reasons.append("raw frame pages not retained in selection root")
        if not _HEX64.fullmatch(str(original.get("page_manifest_hash"))):
            reasons.append("page manifest hash absent")
        reasons += self.age_failures()
        reasons += [f"{e['member']}: {e['rule']}" for e in self.stage_engineering("panel")]
        if self.expectation is not None:
            diff = {k: (proto.get(k), v) for k, v in self.expectation.items() if proto.get(k) != v}
            if diff:
                reasons.append(f"panel protocol differs from frozen D116 values: {diff}")
            reasons += self.frozen_failures()
        g["E1"] = _gate(not reasons, reasons)
        # E2
        reasons = []
        available = _utc(self.sel_report.get("original_frame_available_at"))
        declared = _utc(self.panel_policy.get("declared_at"))
        sel_declared = _utc(self.sel_policy.get("declared_at"))
        started = _utc(self.sel_report.get("computation_started_at"))
        if declared is None or available is None or declared < available:
            reasons.append("panel_policy.declared_at precedes frame_available_at (or unreadable)")
        if sel_declared is None or declared is None or sel_declared < declared:
            reasons.append("selection policy declared before the panel declaration")
        if started is None or sel_declared is None or started < sel_declared:
            reasons.append("selection numerical reads precede the selection declaration")
        if not (self.sel_plan.get("protocol") or {}).get("seed"):
            reasons.append("sealed seed absent from selection plan")
        plan_strata = self.sel_plan.get("strata") or []
        sampled = [s for s in plan_strata if s.get("sampling_state") == "sampled"]
        for s in sampled:
            for key in (
                "stratum_inclusion_probability",
                "conditional_market_inclusion_probability",
                "market_inclusion_probability",
            ):
                if not isinstance(s.get(key), dict) or "numerator" not in s[key]:
                    reasons.append(f"stratum {str(s.get('stratum'))[:8]} lacks exact {key}")
        counts = self.sel_report.get("counts") or {}
        size = self.sel_plan.get("frame_size")
        exclusions = self.sel_plan.get("exclusions") or []
        eligible = self.sel_plan.get("selection_eligible_member_count")
        if counts.get("sampling_members") != size:
            reasons.append("selection_report.counts.sampling_members != plan frame_size")
        if eligible is None:
            # The frozen D116 population policy always records it; the legacy (non-temporal)
            # synthetic fixtures do not, so only the logic-only test aid tolerates its absence.
            if self.enforce:
                reasons.append("selection_eligible_member_count absent: reconciliation impossible")
        elif size != len(exclusions) + eligible:
            reasons.append("frame_size != zero-inclusion exclusions + eligible members")
        if self.sel_report.get("unique_selected_markets") != self.sel_plan.get(
            "unique_selected_markets"
        ):
            reasons.append("selected counts differ between report and plan")
        reasons += [f"{e['member']}: {e['rule']}" for e in self.stage_engineering("selection")]
        n = self.sel_plan.get("unique_selected_markets")
        underfill = []
        slots = proto.get("scheduled_slots")
        if isinstance(n, int) and isinstance(slots, int) and n < slots:
            underfill = [
                {
                    "stratum": str(s.get("stratum"))[:12],
                    "eligible_count": s.get("eligible_count"),
                    "scheduled_count": s.get("scheduled_count"),
                    "sampling_state": s.get("sampling_state"),
                }
                for s in plan_strata
            ]
        if len(self.members) != n:
            reasons.append(f"screened members {len(self.members)} != selected {n}")
        g["E2"] = _gate(
            not reasons,
            reasons,
            unique_selected_markets=n,
            zero_inclusion_exclusions=len(exclusions),
            selection_counts=counts,
            underfill_strata=underfill,
        )
        # E3
        reasons = []
        worker_state = self.worker_report.get("state")
        f = _finding("worker_state", worker_state, stage="screening")
        if f["class"] != OK:
            reasons.append(f"worker state {worker_state}")
        states = self.screen_report.get("states") or []
        if len(states) != len(self.members):
            reasons.append("screening state rows != selected members")
        for e in self.stage_engineering("screening"):
            reasons.append(f"{e['member']}: {e['rule']}")
        started = _utc(self.completion.get("read_started_at"))
        done = _utc(self.screen_available())
        limit = FROZEN_EXPECTATIONS["screening_max_seconds"]
        if started is None or done is None:
            reasons.append("finish-call clocks missing: duration cannot be checked")
        elif _seconds(done, started) > limit:
            reasons.append(f"finish call {_seconds(done, started)} s exceeds {limit}")
        g["E3"] = _gate(
            not reasons,
            reasons,
            states=dict(
                sorted(
                    Counter(
                        str(m["stages"]["screening"]["state"]) for m in self.members.values()
                    ).items()
                )
            ),
        )
        # E4
        reasons = []
        for e in self.stage_engineering("window", "history"):
            reasons.append(f"{e['member']}: {e['rule']}")
        for m in self.members.values():
            w, h = m["stages"].get("window") or {}, m["stages"].get("history") or {}
            if w.get("missing_reason") == "entry_missing":
                reasons.append(f"{m['market_id']}: no observer attempt or refusal")
            if h.get("eligible") is False and not h.get("causes"):
                reasons.append(f"{m['market_id']}: ineligible history without reason")
        g["E4"] = _gate(not reasons, reasons)
        # E5
        reasons = []
        by_trigger = {
            a.get("trigger_id"): a
            for a in self.plan.get("assignments") or []
            if a.get("arm") == "triggered"
        }
        for a in self.plan.get("assignments") or []:
            if a.get("arm") != "control":
                continue
            ids = a.get("matched_trigger_ids") or []
            if not ids or any(t not in by_trigger for t in ids):
                reasons.append(f"control {a.get('market_id')} matches no triggered assignment")
                continue
            if any(by_trigger[t].get("stratum") != a.get("stratum") for t in ids):
                reasons.append(f"control {a.get('market_id')} is not in its trigger's stratum")
            if a.get("assessment_state") != "untriggered":
                reasons.append(
                    f"control {a.get('market_id')} is not an authenticated untriggered member"
                )
        for s in self.plan.get("strata") or []:
            keys = (
                "control_pool",
                "controls_wanted",
                "controls_selected",
                "unfilled_control_slots",
                "triggered_pool",
            )
            if any(not isinstance(s.get(k), int) for k in keys):
                reasons.append(f"stratum {str(s.get('stratum'))[:8]} lacks control accounting")
            else:
                label = str(s.get("stratum"))[:8]
                if s["controls_wanted"] - s["controls_selected"] != s["unfilled_control_slots"]:
                    reasons.append(f"stratum {label} unfilled slots inconsistent")
                expected_controls = min(s["controls_wanted"], s["control_pool"])
                if s["controls_selected"] != expected_controls:
                    reasons.append(
                        f"stratum {label} controls_selected {s['controls_selected']} != "
                        f"min(controls_wanted, control_pool) {expected_controls}"
                    )
        per_stratum = (self.plan.get("protocol") or {}).get("triggered_per_stratum")
        pools = {s.get("stratum"): s.get("triggered_pool") for s in self.plan.get("strata") or []}
        if not isinstance(per_stratum, int):
            reasons.append("plan protocol triggered_per_stratum unreadable")
        else:
            for s in self.plan.get("strata") or []:
                pool, count = s.get("triggered_pool"), s.get("triggered_count")
                if isinstance(pool, int) and count != min(per_stratum, pool):
                    reasons.append(
                        f"stratum {str(s.get('stratum'))[:8]} triggered_count {count} != "
                        f"min(triggered_per_stratum, triggered_pool)"
                    )
            for m in self.members.values():
                if not (m.get("authenticated_state") and m.get("assessment_state") == "triggered"):
                    continue
                strata = {a.get("stratum") for a in m["roles"]}
                has_role = any(a.get("arm") == "triggered" for a in m["roles"])
                oversubscribed = any((pools.get(x) or 0) > per_stratum for x in strata)
                if not has_role and not oversubscribed:
                    reasons.append(
                        f"{m['market_id']}: triggered member has no triggered assignment"
                    )
        if not (self.worker_report.get("role_capacity") or {}).get("fits"):
            reasons.append("role_capacity.fits is not true")
        for m in self.members.values():
            if m["stages"]["screening"].get("state") not in (
                "triggered",
                "untriggered",
                "unavailable",
            ):
                reasons.append(
                    f"{m['market_id']}: member not classified triggered/untriggered/unavailable"
                )
        g["E5"] = _gate(not reasons, reasons)
        # E6
        reasons = []
        for e in self.stage_engineering("origin", "activation", "runtime"):
            reasons.append(f"{e['member']}: {e['rule']}")
        if len(self.rt_report.get("origins") or []) != len(self.members):
            reasons.append("origin results != selected members")
        for m in self.members.values():
            if m.get("origin_receipt") is None:
                reasons.append(f"{m['market_id']}: no durable origin receipt")
            if (
                m["stages"]["origin"].get("state") == "observed"
                and (m.get("origin_facts") or {}).get("origin_at") is None
            ):
                reasons.append(f"{m['market_id']}: observed origin without recorded origin_at")
        reasons += self.ack_before_target()
        g["E6"] = _gate(not reasons, reasons)
        # E7
        reasons = []
        for e in self.stage_engineering("target"):
            reasons.append(f"{e['member']}: {e['rule']}")
        for m in self.members.values():
            t = m["stages"]["target"]
            if t.get("state") in ("pending", "incomplete_evidence", "missing_outcome", None):
                reasons.append(f"{m['market_id']}: target state {t.get('state')}")
            if m["stages"]["origin"].get("state") == "observed" and len(
                t.get("attempt_states") or []
            ) != self.protocol.get("target_attempts", 1):
                reasons.append(f"{m['market_id']}: attempts {len(t.get('attempt_states') or [])}")
        g["E7"] = _gate(not reasons, reasons)
        # E8
        reasons = []
        recovery = self.worker_report.get("recovery") or []
        run_hash = (self.rt_report.get("__ack__") or {}).get("payload_hash")
        if worker_state != "pilot_collected_unaccepted":
            reasons.append(f"worker state {worker_state}")
        if len(recovery) != 1:
            reasons.append(f"recovery receipts {len(recovery)} != 1")
        else:
            rec = recovery[0]
            if rec.get("original_report_hash") != run_hash:
                reasons.append("recovery original_report_hash != runtime report hash")
            if not str(rec.get("original_state", "")).startswith("verified_"):
                reasons.append(f"recovery state {rec.get('original_state')}")
        receipt = {k: v for k, v in self.read_receipt.items() if k != "__ack__"}
        if not receipt:
            reasons.append("original read receipt absent or failed its hash check")
        elif len(recovery) == 1 and receipt != recovery[0]:
            reasons.append("read_receipt.json differs from worker_report recovery[0]")
        g["E8"] = _gate(not reasons, reasons)
        # E9
        reasons = self.accounting()
        g["E9"] = _gate(not reasons, reasons)
        return g

    def age_failures(self):
        reasons = []
        limit = self.protocol.get("max_frame_age_seconds")
        start = _utc(self.sel_original.get("interval_start"))
        if start is None or limit is None:
            return ["frame age cannot be computed"]
        points = {
            "screening_declared": _utc(self.screen_policy.get("declared_at")),
            "screening_cutoff": _utc(self.screen_report.get("cutoff")),
            "activation_read_completed": _utc(self.act_facts.get("read_completed_at")),
            "activation_acknowledged": _utc(
                (self.act_facts.get("__ack__") or {}).get("durable_ack")
            ),
        }
        for name, point in points.items():
            if point is None:
                reasons.append(f"{name} clock unreadable")
            elif _seconds(point, start) > limit:
                reasons.append(
                    f"frame age at {name} {_seconds(point, start):.1f} s exceeds {limit}"
                )
        return reasons

    def ack_before_target(self):
        reasons = []
        for m in self.members.values():
            plan_ack = self.r.pair(
                self.runtime
                / "plans"
                / (m.get("origin_intent") or {}).get("slot", {}).get("intent_id", "none"),
                "plan",
                "origin",
                m["market_id"],
                required=False,
            )
            acked = _utc(((plan_ack or {}).get("__ack__") or {}).get("durable_ack"))
            for folder in m.get("target_dirs") or []:
                intent = self.r.pair(folder, "target_intent", "target", m["market_id"])
                created = _utc((intent or {}).get("created_at"))
                if acked is None or created is None or created < acked:
                    reasons.append(f"{m['market_id']}: target intent not after the origin plan ack")
        return reasons

    def accounting(self):
        reasons = []
        members = set(self.members)
        if not members:
            return ["no selected members"]
        stage_sets = {
            "screening_states": {
                s.get("market_id") for s in self.screen_report.get("states") or []
            },
            "inventory": {
                s.get("market_id") for s in (self.plan.get("assessment_inventory") or [])
            },
            "windows": {
                m
                for m, v in self.members.items()
                if (v["stages"].get("window") or {}).get("missing_reason") != "entry_missing"
            },
            "origins": {
                self.by_intent.get(o.get("intent_id")) for o in self.rt_report.get("origins") or []
            },
            "outcomes": {
                self.by_intent.get(o.get("origin_id")) for o in self.rt_report.get("outcomes") or []
            },
            "activation": {s.get("market_id") for s in self.act_facts.get("selected") or []},
        }
        for name, ids in stage_sets.items():
            if ids != members:
                reasons.append(f"{name} members differ from the selected set")
        for name, rows, key in (
            ("states", self.screen_report.get("states"), "market_id"),
            ("origins", self.rt_report.get("origins"), "intent_id"),
            ("outcomes", self.rt_report.get("outcomes"), "origin_id"),
        ):
            counts = Counter(r.get(key) for r in rows or [])
            if any(v != 1 for v in counts.values()):
                reasons.append(f"{name}: a member appears in more than one terminal row")
        attempts = Counter(a.get("origin_id") for a in self.rt_report.get("attempts") or [])
        expected = self.protocol.get("target_attempts", 1)
        if any(v != expected for v in attempts.values()) or len(attempts) != len(members):
            reasons.append("target attempts per origin differ from the declared number")
        for m in self.members.values():
            screen = sum(len(v) for v in (m.get("screen_receipts") or {}).values())
            if screen != 2:
                reasons.append(f"{m['market_id']}: {screen} screening receipts != 2")
            if (
                m["stages"]["origin"].get("state") in ("observed",)
                and sum(len(v) for v in (m.get("origin_receipts") or {}).values()) != 3
            ):
                reasons.append(f"{m['market_id']}: origin receipts != 3")
            if (
                m["stages"]["target"].get("state") in ("observed", "unavailable", "closed")
                and sum(len(v) for v in (m.get("target_receipts") or {}).values()) != 2 * expected
            ):
                reasons.append(f"{m['market_id']}: target receipts != {2 * expected}")
            for source, items in (
                list((m.get("screen_receipts") or {}).items())
                + list((m.get("origin_receipts") or {}).items())
                + list((m.get("target_receipts") or {}).items())
            ):
                for item in items:
                    if not (item.raw_verified and item.receipt_verified):
                        reasons.append(f"{m['market_id']}: {source} receipt/raw hash mismatch")
        reserved = (self.worker_policy.get("reservation") or {}).get("screening_retained_bytes")
        retained = self.worker_report.get("retained_bytes_before_report")
        if not isinstance(reserved, int) or not isinstance(retained, int) or retained > reserved:
            reasons.append("retained bytes exceed the screening reservation (or unreadable)")
        chain = [
            self.sel_original.get("frame_available_at"),
            self.panel_policy.get("declared_at"),
            self.sel_policy.get("declared_at"),
            self.sel_report.get("computed_at"),
            self.worker_policy.get("declared_at"),
            self.screen_available(),
            self.act_facts.get("read_completed_at"),
            self.rt_report.get("finished_at"),
            self.worker_report.get("reported_at"),
        ]
        times = [_utc(c) for c in chain]
        if any(t is None for t in times) or any(
            b < a for a, b in zip(times, times[1:], strict=False)
        ):
            reasons.append("ordered stage clocks do not hold across the retained artifacts")
        # Same member-slot identity as activation (activation.py:267-274).
        from astrolabe.feature_store.admission import content_hash

        for m in self.members.values():
            slot = (m.get("origin_intent") or {}).get("slot") or {}
            identity = {
                "panel_declaration_hash": slot.get("panel_declaration_hash"),
                "cycle": slot.get("cycle"),
                "market_id": slot.get("market_id"),
                "token_id": slot.get("token_id"),
            }
            if slot and (
                content_hash(identity) != slot.get("intent_id")
                or slot.get("panel_declaration_hash")
                != self.act_facts.get("panel_declaration_hash")
            ):
                reasons.append(f"{m['market_id']}: origin slot identity differs from activation")
        return reasons

    # ----- pairs and decision ---------------------------------------------------------------
    def pairs(self):
        assignments = self.plan.get("assignments") or []
        triggered = {a["trigger_id"]: a for a in assignments if a.get("arm") == "triggered"}
        result = []
        for a in assignments:
            if a.get("arm") != "control":
                continue
            for tid in a.get("matched_trigger_ids") or []:
                t = triggered.get(tid)
                members = [a["market_id"]] + ([t["market_id"]] if t else [])
                complete = [self.members.get(x, {}).get("complete_chain", False) for x in members]
                missing = [x for x, ok in zip(members, complete, strict=True) if not ok]
                result.append(
                    {
                        "trigger_id": tid,
                        "stratum": a.get("stratum"),
                        "triggered_market": t["market_id"] if t else None,
                        "control_market": a["market_id"],
                        "link": "control.matched_trigger_ids == triggered.trigger_id (evidence_id)",
                        "both_complete": bool(t) and all(complete),
                        "unobserved_members": missing,
                        "unobserved_causes": {
                            x: self.members[x]["causes"] for x in missing if x in self.members
                        },
                    }
                )
        return result

    def common_mode(self):
        rows = []
        for m in self.members.values():
            receipts = [
                r
                for d in (
                    m.get("screen_receipts"),
                    m.get("origin_receipts"),
                    m.get("target_receipts"),
                )
                for v in (d or {}).values()
                for r in v
            ]
            failing = any(
                r.transport_error is not None
                or (isinstance(r.status, int) and 400 <= r.status < 500)
                for r in receipts
            )
            limiting = None
            if not m["complete_chain"] and m["causes"]:
                limiting = {k: m["causes"][0].get(k) for k in ("stage", "state", "class")}
            rows.append(
                {
                    "complete": m["complete_chain"],
                    "limiting": limiting,
                    "listed_market_failure": failing,
                }
            )
        return common_mode_flags(rows)

    def summarise(self, gates, pairs, common):
        ms = list(self.members.values())
        # Only an authenticated effective state counts as triggered/untriggered (E5, sub-labels).
        states = Counter(
            "unauthenticated"
            if m["stages"]["screening"].get("effective_state") in ("triggered", "untriggered")
            and not m.get("authenticated_state")
            else m["stages"]["screening"].get("effective_state")
            for m in ms
        )
        controls = [a for a in self.plan.get("assignments") or [] if a.get("arm") == "control"]
        strata = self.plan.get("strata") or []
        triggered_strata = [s for s in strata if (s.get("triggered_pool") or 0) > 0]
        pool_zero = all(s.get("control_pool") == 0 for s in triggered_strata)
        strata_ok = bool(strata) and all(
            isinstance(s.get("control_pool"), int) and isinstance(s.get("controls_wanted"), int)
            for s in strata
        )
        return {
            "n_members": len(ms),
            "engineering_findings": sum(1 for f in self.r.findings if f["class"] == ENGINEERING),
            "failed_gates": sorted(
                k for k, v in gates.items() if not v["pass"] and (self.enforce or k != "E0")
            ),
            "common_mode": common,
            "complete_chains": sum(1 for m in ms if m["complete_chain"]),
            "authenticated_state_members": sum(1 for m in ms if m.get("authenticated_state")),
            "n_triggered_members": states.get("triggered", 0),
            "n_untriggered_members": states.get("untriggered", 0),
            "n_unavailable_members": states.get("unavailable", 0),
            "control_assignments": len(controls),
            "pairs_drawn": len(pairs),
            "pairs_both_complete": sum(1 for p in pairs if p["both_complete"]),
            "strata_report_computed": strata_ok,
            "control_pool_zero_in_triggered_strata": pool_zero,
            "pass_pair_requires": "both pair members' origins observed with eligible histories "
            "and valid (observed) targets",
        }

    def timeline(self):
        start = _utc(self.sel_original.get("interval_start"))
        points = {
            "interval_start": self.sel_original.get("interval_start"),
            "interval_end": self.sel_original.get("interval_end"),
            "frame_available_at": self.sel_original.get("frame_available_at"),
            "panel_declared_at": self.panel_policy.get("declared_at"),
            "selection_declared_at": self.sel_policy.get("declared_at"),
            "selection_cutoff": self.sel_report.get("sampling_cutoff"),
            "selection_computed_at": self.sel_report.get("computed_at"),
            "worker_declared_at": self.worker_policy.get("declared_at"),
            "screening_declared_at": self.screen_policy.get("declared_at"),
            "screening_cutoff": self.screen_report.get("cutoff"),
            "screening_available_at": self.screen_available(),
            "activation_read_completed_at": self.act_facts.get("read_completed_at"),
            "activation_acknowledged_at": (self.act_facts.get("__ack__") or {}).get("durable_ack"),
            "runtime_declared_at": self.rt_policy.get("declared_at"),
            "runtime_finished_at": self.rt_report.get("finished_at"),
            "worker_reported_at": self.worker_report.get("reported_at"),
        }
        seconds = {k: _seconds(_utc(v), start) for k, v in points.items()}
        margins = {}
        limit = self.protocol.get("max_frame_age_seconds")
        if limit is not None and seconds.get("activation_acknowledged_at") is not None:
            margins["frame_age_margin_at_activation_ack_s"] = (
                limit - seconds["activation_acknowledged_at"]
            )
        # Unbudgeted freshness: assessments must still be <= 120 s old at activation.
        fresh = self.plan.get("assessment_policy") or {}
        act = _utc(self.act_facts.get("read_completed_at"))
        ages = []
        for entry in self.plan.get("assessment_inventory") or []:
            a = entry.get("assessment") or {}
            if a and act:
                ages.append(
                    {
                        "market_id": entry.get("market_id"),
                        "window_age_s": _seconds(act, _utc(a.get("input_window_end"))),
                        "assessment_age_s": _seconds(act, _utc(a.get("available_at"))),
                    }
                )
        margins["assessment_ages_at_activation"] = ages
        margins["assessment_limits_s"] = {
            "window": fresh.get("max_window_age_seconds"),
            "assessment": fresh.get("max_assessment_age_seconds"),
        }
        freeze_ages = []
        for m in self.members.values():
            w = ((m.get("origin_facts") or {}).get("projection") or {}).get(
                "pre_origin_window"
            ) or {}
            if w.get("frozen_at") and w.get("window_ended_at"):
                freeze_ages.append(
                    {
                        "market_id": m["market_id"],
                        "window_age_at_freeze_s": _seconds(
                            _utc(w["frozen_at"]), _utc(w["window_ended_at"])
                        ),
                    }
                )
        margins["window_age_at_freeze"] = freeze_ages
        return {
            "seconds_after_interval_start": seconds,
            "margins": margins,
            "note": "estimates of measured clocks; frame age (fail-closed) is the real bound",
        }

    def diagnostics(self):
        ms = list(self.members.values())
        n = len(ms)
        observed = sum(1 for m in ms if m["stages"]["origin"].get("state") == "observed")
        histories = sum(1 for m in ms if m["stages"]["history"].get("eligible") is True)
        valid = sum(1 for m in ms if m["stages"]["target"].get("state") == "observed")
        return {
            "n": n,
            "observed_origins": observed,
            "observed_origins_of_8": f"{observed}/8",
            "eligible_completed_histories": histories,
            "eligible_histories_of_8": f"{histories}/8",
            "observed_matched_pairs": sum(1 for p in self.pairs() if p["both_complete"]),
            "valid_targets": valid,
            "target_ratio_5v_ge_4o": 5 * valid >= 4 * observed,
            "per_window": {
                m["market_id"]: {
                    k: v for k, v in (m["stages"].get("window") or {}).items() if k != "causes"
                }
                for m in ms
            },
            "descriptive_only": "not acceptance; for comparability with D089-era counts",
        }

    def public(self, m):
        stages = {}
        for name, info in m["stages"].items():
            stages[name] = {k: v for k, v in info.items()}
        return {
            "market_id": m["market_id"],
            "token_id": m["token_id"],
            "roles": [
                {
                    k: a.get(k)
                    for k in (
                        "arm",
                        "stratum",
                        "trigger_id",
                        "matched_trigger_ids",
                        "assessment_state",
                    )
                }
                for a in m["roles"]
            ],
            "effective_assessment_state": m.get("assessment_state"),
            "authenticated_state": bool(m.get("authenticated_state")),
            "stages": stages,
            "complete_chain": m["complete_chain"],
            "causes": m["causes"],
        }
