"""Predeclared exact snapshot rule with authenticated reads; no validated signal claim."""

import shutil
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from fractions import Fraction

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import _clock, _sync_directory
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist, _time
from astrolabe.feature_store.types import canonical_json, uint_text

from .book_primitives import _ratio
from .build_identity import verified_panel_build
from .input_read import _canonical
from .socket_analysis import _post
from .window_computation import LIMITS, _check, _save

VERSION = "fs2-snapshot-trigger-computation-v1"
CHILD = "fs2_trigger_computation_result"


@dataclass(frozen=True)
class SnapshotTriggerPolicy:
    numerator: int
    denominator: int
    max_age_ms: int
    version: str = "fs2-absolute-snapshot-imbalance-rule-v1"

    def __post_init__(self):
        if (
            type(self.numerator) is not int
            or type(self.denominator) is not int
            or not 0 < self.numerator <= self.denominator <= 1000000
            or Fraction(self.numerator, self.denominator).denominator != self.denominator
            or type(self.max_age_ms) is not int
            or not 0 <= self.max_age_ms <= 300000
            or self.version != "fs2-absolute-snapshot-imbalance-rule-v1"
        ):
            raise ValueError("explicit reduced exact threshold and bounded age required")


def _outside(a, b):
    return a != b and a not in b.parents and b not in a.parents


def declare_snapshot_trigger(root, *, book_root, market_id, token_id, policy):
    root, book = _canonical(root), _canonical(book_root)
    if not root.name.startswith("fs2_trigger_declaration_") or not _outside(root, book):
        raise ValueError("separate canonical declaration and future book root required")
    if root.exists() or book.exists():
        raise FileExistsError("declare before fresh computation; no overwrite")
    if type(policy) is not SnapshotTriggerPolicy:
        raise ValueError("explicit snapshot rule required")
    if (
        not isinstance(market_id, str)
        or not market_id.isdecimal()
        or len(market_id) > 80
        or uint_text(token_id, bits=256) != token_id
    ):
        raise ValueError("source-local market/token identity required")
    if (
        shutil.disk_usage(root.parent).free
        < LIMITS["free_reserve_bytes"] + LIMITS["max_output_bytes"]
    ):
        raise ValueError("full trigger output reserve unavailable")
    build, started = verified_panel_build(), time.monotonic()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    _save(
        root,
        "trigger_declaration",
        {
            "schema_version": VERSION,
            "build": build,
            "limits": dict(LIMITS),
            "book_root": str(book),
            "market_id": market_id,
            "token_id": token_id,
            "rule": asdict(policy),
            "rule_hash": content_hash(asdict(policy)),
            "declared_at": _clock(),
        },
        started,
    )
    return _pair(root, "trigger_declaration")[1]


def _declaration(root):
    declaration, ack = _pair(root, "trigger_declaration")
    rule = SnapshotTriggerPolicy(**declaration["rule"])
    book = _canonical(declaration["book_root"])
    if (
        declaration["schema_version"] != VERSION
        or declaration["limits"] != LIMITS
        or declaration["build"] != verified_panel_build()
        or declaration["rule_hash"] != content_hash(asdict(rule))
        or not _outside(root, book)
        or not _ordered_clocks(declaration["declared_at"], ack["durable_ack"])
    ):
        raise ValueError("trigger declaration differs")
    return declaration, ack, book, rule


def _load(declaration_root):
    declaration, ack, book, rule = _declaration(declaration_root)
    summary, projection, receipts = _post(book)
    book_policy, _ = _pair(book, "book_policy")
    source = _canonical(book_policy["source_root"])
    if not _outside(declaration_root, source):
        raise ValueError("source evidence outside declaration required")
    return {
        "declaration": declaration,
        "declaration_ack": ack,
        "book_summary": summary,
        "book_projection": projection,
        "receipts": receipts,
        "source_root": str(source),
    }, rule


def _project(inputs, rule, at):
    declaration = inputs["declaration"]
    receipts, book = inputs["receipts"], inputs["book_projection"]
    reasons = []
    if sorted(v["source_id"] for v in receipts) != ["clob.book", "gamma.market"]:
        reasons.append("source_pair_unavailable")
    for receipt in receipts:
        if not _ordered_clocks(
            inputs["declaration_ack"]["durable_ack"], receipt["request_started"]
        ):
            raise ValueError("source request preceded trigger declaration")
        if receipt["missing_reason"] != "observed":
            reasons.append(receipt["source_id"] + "_" + receipt["missing_reason"])
        if (
            not timedelta(0)
            <= _time(at) - _time(receipt["first_received"])
            <= timedelta(milliseconds=rule.max_age_ms)
        ):
            reasons.append("source_stale_at_assessment")
        request = receipt["request"]
        actual = (
            request["params"].get("token_id")
            if receipt["source_id"] == "clob.book"
            else request["path_params"].get("id")
        )
        expected = declaration["token_id" if receipt["source_id"] == "clob.book" else "market_id"]
        if actual != expected:
            reasons.append("requested_identity_differs")
    snapshot = book["snapshots"][0] if len(book["snapshots"]) == 1 else None
    quote = snapshot["quote"] if snapshot else None
    if snapshot is None or snapshot["state"] != "observed":
        reasons.append("snapshot_" + (snapshot["state"] if snapshot else "unavailable"))
    mapping = quote.get("mapping") if quote else None
    if (
        mapping is None
        or mapping["market_id"] != declaration["market_id"]
        or quote["token_id"] != declaration["token_id"]
    ):
        reasons.append("snapshot_identity_unavailable_or_changed")
    if mapping is None or mapping.get("lifecycle") != {
        "active": True,
        "closed": False,
        "archived": False,
        "acceptingOrders": True,
    }:
        reasons.append("known_active_lifecycle_unavailable")
    value = absolute = difference = None
    threshold = Fraction(rule.numerator, rule.denominator)
    state = "unavailable"
    if not reasons:
        component = snapshot["components"]["F08_snapshot"]
        value = Fraction(int(component["numerator"]), int(component["denominator"]))
        absolute = abs(value)
        difference = absolute - threshold
        state = "triggered" if difference >= 0 else "untriggered"
    clocks = [v["first_received"] for v in receipts]
    result = {
        "schema_version": VERSION,
        "state": state,
        "reasons": sorted(set(reasons)),
        "signed_imbalance": _ratio(value) if value is not None else None,
        "absolute_imbalance": _ratio(absolute) if absolute is not None else None,
        "threshold": _ratio(threshold),
        "absolute_minus_threshold": _ratio(difference) if difference is not None else None,
        "market_id": declaration["market_id"],
        "token_id": declaration["token_id"],
        "rule_hash": declaration["rule_hash"],
        "input_window_start": min(clocks, key=lambda v: v["utc"]) if clocks else None,
        "input_window_end": max(clocks, key=lambda v: v["utc"]) if clocks else None,
        "mapping": mapping,
        "provenance_class": inputs["book_summary"]["source_provenance_class"],
        "scope": "development_snapshot_rule_only",
        "origin_admitted": False,
        "feature_store_admitted": False,
        "runtime_sampling_verification_required": True,
    }
    return {**result, "projection_hash": content_hash(result)}


def record_snapshot_trigger(declaration_root):
    parent = _canonical(declaration_root)
    declaration, ack, _, _ = _declaration(parent)
    root = parent / CHILD
    if root.exists():
        raise FileExistsError("trigger computation terminal; no overwrite or resume")
    if shutil.disk_usage(parent).free < LIMITS["free_reserve_bytes"] + LIMITS["max_output_bytes"]:
        raise ValueError("full trigger computation reserve unavailable")
    started = time.monotonic()
    root.mkdir(mode=0o700)
    _sync_directory(parent)
    try:
        _save(
            root,
            "trigger_computation_policy",
            {
                "schema_version": VERSION,
                "build": verified_panel_build(),
                "limits": dict(LIMITS),
                "declaration_root": str(parent),
                "declaration_hash": ack["payload_hash"],
                "book_root": declaration["book_root"],
                "declared_at": _clock(),
            },
            started,
        )
        _, pa = _pair(root, "trigger_computation_policy")
        read_started = _clock()
        inputs, rule = _load(parent)
        _save(
            root,
            "trigger_input",
            {"inputs": inputs, "read_started_at": read_started, "read_completed_at": _clock()},
            started,
        )
        _, ia = _pair(root, "trigger_input")
        computed_start = _clock()
        projection = _project(inputs, rule, computed_start)
        _save(
            root,
            "trigger_computation_facts",
            {
                "schema_version": VERSION,
                "policy_hash": pa["payload_hash"],
                "input_hash": ia["payload_hash"],
                "computation_started_at": computed_start,
                "computed_at": _clock(),
                "projection": projection,
            },
            started,
        )
        return read_snapshot_trigger(root)
    except BaseException as exc:
        try:
            _persist(
                root, "trigger_failure", {"exception_type": type(exc).__name__, "at": _clock()}
            )
        except (OSError, ValueError):
            pass
        raise


def read_snapshot_trigger(root):
    root, started = _canonical(root), time.monotonic()
    expected = {
        n + s
        for n in ("trigger_computation_policy", "trigger_input", "trigger_computation_facts")
        for s in (".json", "_ack.json")
    }
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError("successful complete trigger closure required")
    _check(root, started)
    policy, pa = _pair(root, "trigger_computation_policy")
    parent = _canonical(policy["declaration_root"])
    if (
        root != parent / CHILD
        or {p.name for p in parent.iterdir()}
        != {CHILD, "trigger_declaration.json", "trigger_declaration_ack.json"}
        or policy["build"] != verified_panel_build()
        or policy["limits"] != LIMITS
        or policy["schema_version"] != VERSION
    ):
        raise ValueError("trigger ownership/build differs")
    inputs, rule = _load(parent)
    saved, ia = _pair(root, "trigger_input")
    facts, fa = _pair(root, "trigger_computation_facts")
    if (
        policy["declaration_hash"] != inputs["declaration_ack"]["payload_hash"]
        or policy["book_root"] != inputs["declaration"]["book_root"]
        or canonical_json(saved["inputs"]) != canonical_json(inputs)
        or facts["schema_version"] != VERSION
        or facts["policy_hash"] != pa["payload_hash"]
        or facts["input_hash"] != ia["payload_hash"]
        or not _ordered_clocks(
            inputs["declaration_ack"]["durable_ack"],
            policy["declared_at"],
            pa["durable_ack"],
            saved["read_started_at"],
            saved["read_completed_at"],
            ia["durable_ack"],
            facts["computation_started_at"],
            facts["computed_at"],
            fa["durable_ack"],
        )
        or not _ordered_clocks(
            inputs["book_summary"]["computation_available_at"], saved["read_started_at"]
        )
    ):
        raise ValueError("trigger input/chronology differs")
    projection = _project(inputs, rule, facts["computation_started_at"])
    if canonical_json(projection) != canonical_json(facts["projection"]):
        raise ValueError("trigger exact replay differs")
    if verified_panel_build() != policy["build"]:
        raise ValueError("trigger build changed during replay")
    _check(root, started)
    return {
        "schema_version": VERSION,
        "computation_hash": fa["payload_hash"],
        "computation_started_at": facts["computation_started_at"],
        "computed_at": facts["computed_at"],
        "computation_available_at": fa["durable_ack"],
        "projection_hash": projection["projection_hash"],
        "state": projection["state"],
        "source_provenance_class": projection["provenance_class"],
        "origin_admitted": False,
        "feature_store_admitted": False,
    }
