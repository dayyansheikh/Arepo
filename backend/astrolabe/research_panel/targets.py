"""Pure receipt-time target rules; no execution-profit or sparse-path inference."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from itertools import islice

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.types import HASH_PATTERN, exact_decimal, uint_text, utc_datetime


@dataclass(frozen=True)
class Quote:
    observation_id: str
    token_id: str
    received_at: datetime
    available_at: datetime
    mapping_available_at: datetime | None
    bid: str | None
    ask: str | None
    bid_size: str | None
    ask_size: str | None
    source_status: str = "observed"


def quote_state(quote):
    """No fallback from missing/one-sided/crossed books to a carried trade price."""
    if (not isinstance(quote.observation_id, str)
            or not HASH_PATTERN.fullmatch(quote.observation_id)):
        raise ValueError("quote observation lineage required")
    uint_text(quote.token_id, bits=256)
    received, available = utc_datetime(quote.received_at), utc_datetime(quote.available_at)
    if available < received:
        raise ValueError("quote availability cannot precede receipt")
    if quote.mapping_available_at is None:
        return "identity_unresolved", None
    if utc_datetime(quote.mapping_available_at) > received:
        return "identity_not_known_at_receipt", None
    if quote.source_status != "observed":
        if quote.source_status not in {"source_error", "rate_limited", "transport_gap", "closed"}:
            raise ValueError("unknown quote source state")
        return quote.source_status, None
    if any(v is None for v in (quote.bid, quote.ask, quote.bid_size, quote.ask_size)):
        return "one_sided_or_missing", None
    try:
        bid, ask, bid_size, ask_size = [exact_decimal(v) for v in
                                       (quote.bid, quote.ask, quote.bid_size, quote.ask_size)]
    except ValueError:
        return "invalid_numerical", None
    if not 0 <= bid <= ask <= 1 or bid_size <= 0 or ask_size <= 0:
        return "invalid_or_crossed", None
    # Context scales to retain tiny components/exponents instead of ambient precision.
    values = (bid, ask)
    digits = max(len(v.as_tuple().digits) + v.as_tuple().exponent for v in values)
    digits -= min(v.as_tuple().exponent for v in values)
    if digits > 10000:
        return "numerical_budget_exceeded", None
    with localcontext() as context:
        context.prec = max(32, digits + 4)
        midpoint = (bid + ask) / 2
    return "observed", midpoint


def select_target(quotes, *, token_id, origin_at, origin_persisted_at, horizon_seconds,
                  tolerance_seconds, as_of):
    """First valid receipt >= target, including frozen upper tolerance boundary.

    Availability is checked at report time. Earlier but delayed valid receipts block final
    selection until usable; never choose the later observation that gives a nicer return.
    A closed response is an explicit status, not a guessed closure from a metadata end date.
    """
    uint_text(token_id, bits=256)
    origin_at, persisted, as_of = map(utc_datetime, (origin_at, origin_persisted_at, as_of))
    if (type(horizon_seconds) is not int or not 1 <= horizon_seconds <= 604800
            or type(tolerance_seconds) is not int or not 0 <= tolerance_seconds < horizon_seconds):
        raise ValueError("bounded fixed horizon and shorter nonnegative tolerance required")
    target = origin_at + timedelta(seconds=horizon_seconds)
    deadline = target + timedelta(seconds=tolerance_seconds)
    if not origin_at <= persisted < target or as_of < persisted:
        raise ValueError("actual durable origin must precede target and reporting cutoff")
    quotes = list(islice(quotes, 10001))
    if len(quotes) > 10000:
        raise ValueError("bounded quote inventory required")
    records = []
    seen = set()
    for quote in quotes:
        received = utc_datetime(quote.received_at)
        if received > as_of:
            continue
        if quote.observation_id in seen:
            raise ValueError("duplicate quote receipt must be deduplicated before target selection")
        seen.add(quote.observation_id)
        if (not isinstance(quote.observation_id, str)
                or not HASH_PATTERN.fullmatch(quote.observation_id)):
            raise ValueError("quote observation lineage required")
        if quote.token_id != token_id:
            raise ValueError("target inventory contains a different token")
        available = utc_datetime(quote.available_at)
        if available < received:
            raise ValueError("quote availability cannot precede receipt")
        # Do not inspect values, identity revisions or quality not available at this cutoff.
        state, midpoint = (quote_state(quote) if available <= as_of
                           else ("not_yet_available", None))
        if state == "observed" and utc_datetime(quote.mapping_available_at) > origin_at:
            state, midpoint = "identity_not_frozen_at_origin", None
        records.append((quote, state, midpoint))
    records.sort(key=lambda item: (item[0].received_at, item[0].observation_id))
    exclusions = []
    censoring_observation_id = None
    blocking_observation_id = None
    selected, status = None, "pending" if as_of < deadline else "unavailable"
    for quote, state, midpoint in records:
        if quote.received_at < target:
            continue
        if quote.received_at > deadline:
            exclusions.append({"observation_id": quote.observation_id, "reason": "late"})
            continue
        if quote.available_at > as_of:
            status = "pending"
            blocking_observation_id = quote.observation_id
            break  # earlier receipt may still become the first usable valid quote
        if state == "closed":
            status = "closed"
            censoring_observation_id = quote.observation_id
            break
        if state != "observed":
            exclusions.append({"observation_id": quote.observation_id, "reason": state})
            continue
        delay = quote.received_at - target
        microseconds = (delay.days * 86400 + delay.seconds) * 1000000 + delay.microseconds
        with localcontext() as context:
            context.prec = 32
            delay_seconds = str(Decimal(microseconds) / 1000000)
        selected = {"observation_id": quote.observation_id, "midpoint": str(midpoint),
                    "observed_at": utc_datetime(quote.received_at).isoformat(),
                    "available_at": utc_datetime(quote.available_at).isoformat(),
                    "delay_seconds": delay_seconds}
        status = "observed"
        break
    result = {"schema_version": "fs2-receipt-target-v1", "token_id": token_id,
              "origin_at": origin_at.isoformat(), "origin_persisted_at": persisted.isoformat(),
              "horizon_seconds": horizon_seconds, "tolerance_seconds": tolerance_seconds,
              "target_at": target.isoformat(), "deadline_at": deadline.isoformat(),
              "as_of": as_of.isoformat(), "clock_basis": "receipt", "status": status,
              "equal_receipt_time_tie_rule": "observation_id_lexicographic",
              "selected": selected, "exclusions": exclusions,
              "censoring_observation_id": censoring_observation_id,
              "blocking_observation_id": blocking_observation_id,
              "inventory_hash": content_hash([
                  {"observation_id": q.observation_id, "state": state,
                   "received_at": utc_datetime(q.received_at).isoformat(),
                   "available_at": utc_datetime(q.available_at).isoformat()
                   if state != "not_yet_available" else None,
                   "known_payload_hash": content_hash(asdict(q))
                   if state != "not_yet_available" else None}
                  for q, state, _ in records]),
              "economic_value_claim": False}
    return {**result, "result_hash": content_hash(result)}
