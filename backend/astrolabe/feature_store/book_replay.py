"""Exact bounded market-channel replay with explicit continuity limits.

No network connection or v1 state. Raw snapshots/deltas remain in the receipt journal;
this object is a reproducible derived view, never the research authority itself.
"""

from __future__ import annotations

from .admission import content_hash
from .source_parsers import clob_book
from .types import exact_decimal, uint_text, utc_datetime


class BookReplay:
    def __init__(self, token_id, condition_id, *, message_budget=1000):
        self.token_id = uint_text(token_id, bits=256)
        self.condition_id = condition_id
        if type(message_budget) is not int or not 1 <= message_budget <= 10000:
            raise ValueError("explicit bounded replay budget required")
        self.message_budget = message_budget
        self._seen = {}
        self._rejected = set()
        self._bids, self._asks = {}, {}
        self._session = None
        self._last_clock = None
        self._needs_snapshot = True
        self.gaps = []
        self.lineage = []
        self.native_timestamps = []
        self._has_deltas = False

    def disconnect(self, *, evidence_id, received_at):
        self._needs_snapshot = True
        self.gaps.append({"reason": "disconnect", "evidence_id": evidence_id,
                          "received_at": utc_datetime(received_at)})

    def apply(self, message, *, evidence_id, session_id, received_at, monotonic_ns):
        try:
            return self._apply(message, evidence_id=evidence_id, session_id=session_id,
                               received_at=received_at, monotonic_ns=monotonic_ns)
        except ValueError:
            # A rejected relevant message breaks reconstruction even when numerical
            # updates were atomic. Never continue from the pre-error book silently.
            self._needs_snapshot = True
            if (isinstance(evidence_id, str) and evidence_id in self._seen
                    and not any(g["evidence_id"] == evidence_id for g in self.gaps)):
                self.gaps.append({"reason": "rejected_message", "evidence_id": evidence_id})
            raise

    def _apply(self, message, *, evidence_id, session_id, received_at, monotonic_ns):
        received_at = utc_datetime(received_at)
        monotonic_ns = int(uint_text(monotonic_ns))
        if not isinstance(evidence_id, str) or not evidence_id or not session_id:
            raise ValueError("receipt evidence and clock session required")
        signature = content_hash({"message": message, "session": session_id,
                                  "received": received_at, "monotonic": str(monotonic_ns)})
        if evidence_id in self._seen:
            if self._seen[evidence_id] != signature:
                raise ValueError("receipt identity conflict")
            if evidence_id in self._rejected:
                raise ValueError("previously rejected receipt; snapshot recovery required")
            return self.view()
        if len(self._seen) >= self.message_budget:
            raise ValueError("replay budget exhausted; preserve input without dropping history")
        self._seen[evidence_id] = signature
        self._rejected.add(evidence_id)
        if not isinstance(message, dict):
            raise ValueError("market-channel object required")
        if self._session is not None and self._session != session_id:
            self._needs_snapshot = True
            self.gaps.append({"reason": "session_changed", "evidence_id": evidence_id,
                              "received_at": received_at})
        if self._last_clock is not None:
            previous_time, previous_monotonic = self._last_clock
            if (received_at < previous_time
                    or (self._session == session_id and monotonic_ns < previous_monotonic)):
                self._needs_snapshot = True
                self.gaps.append({"reason": "clock_regression", "evidence_id": evidence_id,
                                  "received_at": received_at})
                raise ValueError("receipt clock regression")
        kind = message.get("event_type")
        if kind == "book":
            parsed = clob_book(message, expected_token=self.token_id,
                               expected_condition=self.condition_id)
            if "duplicate_price_level" in parsed["quality_flags"]:
                self._needs_snapshot = True
                raise ValueError("duplicate snapshot levels cannot be silently collapsed")
            bids = {v["price"]: v["size"] for v in parsed["bids"] if v["size"] > 0}
            asks = {v["price"]: v["size"] for v in parsed["asks"] if v["size"] > 0}
            lineage = [evidence_id]
            has_deltas = False
        elif kind == "price_change":
            if self._needs_snapshot:
                raise ValueError("full snapshot required after gap/before deltas")
            if message.get("market") != self.condition_id:
                raise ValueError("delta condition mismatch")
            changes = message.get("price_changes")
            if not isinstance(changes, list) or not changes:
                raise ValueError("price_changes array required")
            bids, asks = dict(self._bids), dict(self._asks)
            matched = False
            for change in changes:
                if not isinstance(change, dict):
                    raise ValueError("delta object required")
                if uint_text(change.get("asset_id"), bits=256) != self.token_id:
                    continue
                matched = True
                side = change.get("side")
                price, size = exact_decimal(change.get("price")), exact_decimal(change.get("size"))
                if side not in {"BUY", "SELL"} or not 0 <= price <= 1 or size < 0:
                    raise ValueError("invalid delta")
                levels = bids if side == "BUY" else asks
                if size == 0:
                    levels.pop(price, None)
                else:
                    levels[price] = size
            if not matched:
                raise ValueError("message does not concern this token")
            lineage = [*self.lineage, evidence_id]
            has_deltas = True
        else:
            raise ValueError("unsupported event; never interpreted as a book delta")
        self._bids, self._asks = bids, asks
        self._session, self._last_clock = session_id, (received_at, monotonic_ns)
        self._rejected.remove(evidence_id)
        self.lineage = lineage
        self.native_timestamps.append({"evidence_id": evidence_id, "raw": message.get("timestamp")})
        self._needs_snapshot, self._has_deltas = False, has_deltas
        return self.view()

    def view(self):
        flags = ["continuous_sequence_unproven", "source_clock_not_admitted"]
        if not self._bids or not self._asks:
            flags.append("one_sided_book")
        if self._bids and self._asks and max(self._bids) > min(self._asks):
            flags.append("crossed_book")
        return {
            "token_id": self.token_id, "condition_id": self.condition_id,
            "bids": sorted(self._bids.items(), reverse=True), "asks": sorted(self._asks.items()),
            "requires_snapshot": self._needs_snapshot,
            "reconstruction": "received_deltas" if self._has_deltas else "returned_snapshot",
            "complete_continuous_history": False,
            "lineage": list(self.lineage), "gap_events": [dict(g) for g in self.gaps],
            "quality_flags": flags,
        }
