"""Exact, conservative source parsing. Pure functions; no receipt-time fallback."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from decimal import localcontext

from .admission import content_hash
from .capture import _strict_json
from .types import exact_decimal, uint_text, utc_datetime

HEX32 = re.compile(r"0x[0-9a-fA-F]{64}\Z")


def native_clock(raw, *, unit, received_at):
    """Unit is pinned by the source contract, never inferred from digit count.

    Submicrosecond native precision stays in raw; the datetime is rounded down and
    flagged. Unknown units and naive/invalid times stay null. Receipt is only a check.
    """
    result = {"raw": raw, "unit": unit, "value": None,
              "missing_reason": "observed", "quality_flags": []}
    if raw is None:
        result["missing_reason"] = "not_supported"
        return result
    if unit is None:
        result.update(missing_reason="invalid", quality_flags=["source_clock_unknown"])
        return result
    try:
        if unit == "iso8601":
            if not isinstance(raw, str):
                raise ValueError("ISO timestamp must be text")
            value = utc_datetime(datetime.fromisoformat(raw.replace("Z", "+00:00")))
            if re.search(r"\.\d{7,}", raw):
                result["quality_flags"].append("timestamp_precision")
        elif unit in {"epoch_s", "epoch_ms", "epoch_us", "epoch_ns"}:
            number = exact_decimal(raw)
            with localcontext() as context:
                context.prec = 4200
                micros = number * {"epoch_s": 1000000, "epoch_ms": 1000,
                                   "epoch_us": 1, "epoch_ns": exact_decimal("0.001")}[unit]
                if micros < 0 or micros > 253402300799999999:
                    raise ValueError("clock outside supported range")
                integral = int(micros)
                if micros != integral:
                    result["quality_flags"].append("timestamp_precision")
                value = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=integral)
        else:
            raise ValueError("unsupported clock unit")
        result["value"] = value
        if value > utc_datetime(received_at):
            result["quality_flags"].append("future_source_clock")
    except (TypeError, ValueError, OverflowError):
        result.update(value=None, missing_reason="invalid")
    return result


def _condition(value):
    if not isinstance(value, str) or not HEX32.fullmatch(value):
        raise ValueError("invalid source condition ID")
    return value.lower()


def _array(value):
    result = _strict_json(value) if isinstance(value, str) else value
    if not isinstance(result, list):
        raise ValueError("ordered array required")
    return result


def gamma_market(row, *, expected_market):
    """Single-target identity plus nullable source lifecycle, without invented defaults."""
    if not isinstance(row, dict) or row.get("id") != expected_market:
        raise ValueError("Gamma response differs from requested market")
    lifecycle = {key: row.get(key) for key in ("active", "closed", "archived", "acceptingOrders")}
    if any(value is not None and type(value) is not bool for value in lifecycle.values()):
        raise ValueError("Gamma lifecycle must be boolean or unknown")
    return {**gamma_identity(row), "lifecycle": lifecycle}


def gamma_identity(row):
    """Preserve source-local mappings; no asserted chain/collateral from defaults."""
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
        raise ValueError("Gamma market ID required")
    tokens, labels = _array(row.get("clobTokenIds")), _array(row.get("outcomes"))
    if not tokens or len(tokens) != len(labels) or not all(isinstance(v, str) for v in labels):
        raise ValueError("token/outcome order cannot be resolved")
    tokens = [uint_text(value, bits=256) for value in tokens]
    if len(set(tokens)) != len(tokens):
        raise ValueError("duplicate outcome token identity")
    events = row.get("events")
    if not isinstance(events, list):
        events = []
    event_ids = [event["id"] for event in events
                 if isinstance(event, dict) and isinstance(event.get("id"), str)]
    rules = row.get("description")
    if rules is not None and not isinstance(rules, str):
        raise ValueError("rules must preserve source text")
    result = {
        "venue": "polymarket", "market_id": row["id"],
        "condition_id": _condition(row.get("conditionId")),
        "question_id": _condition(row["questionID"]) if row.get("questionID") else None,
        "question": row.get("question"), "rules_text": rules,
        "rules_hash": content_hash({"description": rules,
                                    "resolution_source": row.get("resolutionSource")}),
        "resolution_source": row.get("resolutionSource"),
        "source_event_ids": event_ids,
        "outcomes": [{"token_id": token, "outcome_index": index, "outcome_label": labels[index]}
                     for index, token in enumerate(tokens)],
        "chain_id": None, "token_contract": None, "collateral_address": None,
        "identity_status": "source_local_only", "economic_group_status": "unresolved",
    }
    result["mapping_version"] = content_hash(result)
    return result


def clob_book(row, *, expected_token=None, expected_condition=None):
    if not isinstance(row, dict):
        raise ValueError("book object required")
    token, condition = uint_text(row.get("asset_id"), bits=256), _condition(row.get("market"))
    if expected_token is not None and token != expected_token:
        raise ValueError("book token mismatch")
    if expected_condition is not None and condition != expected_condition:
        raise ValueError("book condition mismatch")
    result = {"token_id": token, "condition_id": condition, "timestamp_raw": row.get("timestamp"),
              "native_hash": row.get("hash"), "quality_flags": []}
    for side in ("bids", "asks"):
        if not isinstance(row.get(side), list):
            raise ValueError("missing book side is not empty depth")
        levels = []
        for index, level in enumerate(row[side]):
            if not isinstance(level, dict):
                raise ValueError("book level object required")
            price, size = exact_decimal(level.get("price")), exact_decimal(level.get("size"))
            if not 0 <= price <= 1 or size < 0:
                raise ValueError("invalid book level range")
            levels.append({"source_index": index, "price_raw": level["price"],
                           "size_raw": level["size"], "price": price, "size": size})
        result[side] = levels
        if len({v["price"] for v in levels}) != len(levels):
            result["quality_flags"].append("duplicate_price_level")
    bids = [v["price"] for v in result["bids"] if v["size"] > 0]
    asks = [v["price"] for v in result["asks"] if v["size"] > 0]
    if not bids or not asks:
        result["quality_flags"].append("one_sided_book")
    if bids and asks and max(bids) > min(asks):
        result["quality_flags"].append("crossed_book")
    return result


def data_v2_trades(payload, *, expected_condition=None):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Data API v2 envelope required; no v1 fallback")
    pagination = payload.get("pagination")
    if not isinstance(pagination, dict) or type(pagination.get("has_more")) is not bool:
        raise ValueError("explicit pagination state required")
    cursor = pagination.get("next_cursor")
    if pagination["has_more"] and (not isinstance(cursor, str) or not cursor):
        raise ValueError("missing continuation cursor")
    if not pagination["has_more"] and cursor is not None:
        raise ValueError("contradictory pagination state")
    rows = []
    fingerprints = set()
    duplicate_count = 0
    for raw in payload["data"]:
        if not isinstance(raw, dict):
            raise ValueError("trade row object required")
        condition = _condition(raw.get("condition_id"))
        if expected_condition is not None and condition != expected_condition:
            raise ValueError("trade condition mismatch")
        token = uint_text(raw.get("token_id"), bits=256)
        price, size = exact_decimal(raw.get("price")), exact_decimal(raw.get("size"))
        if not 0 <= price <= 1 or size < 0 or raw.get("side") not in {"BUY", "SELL"}:
            raise ValueError("invalid trade primitive")
        fingerprint = content_hash(raw)
        duplicate_count += int(fingerprint in fingerprints)
        fingerprints.add(fingerprint)
        rows.append({"row_fingerprint": fingerprint, "condition_id": condition, "token_id": token,
                     "price": price, "size": size, "price_raw": str(raw["price"]),
                     "size_raw": str(raw["size"]), "side": raw["side"],
                     "timestamp_raw": raw.get("timestamp"), "economic_fill_id": None,
                     "transaction_hash": raw.get("transaction_hash")})
    return {"rows": rows, "pagination": pagination, "identical_rows": duplicate_count,
            "coverage_fraction": None, "coverage_state": "bounded_page",
            "economic_deduplication": "unresolved"}


NWS_QUANTITIES = (
    "elevation", "temperature", "dewpoint", "windDirection", "windSpeed", "windGust",
    "barometricPressure", "seaLevelPressure", "visibility", "maxTemperatureLast24Hours",
    "minTemperatureLast24Hours", "precipitationLastHour", "precipitationLast3Hours",
    "precipitationLast6Hours", "relativeHumidity", "windChill", "heatIndex",
)


def nws_observation(row, *, expected_station, received_at):
    """Receipt-time knowledge of exact native quantities, not first release or QC admission."""
    if not isinstance(row, dict) or row.get("type") != "Feature":
        raise ValueError("NWS observation GeoJSON feature required")
    props = row.get("properties")
    if not isinstance(props, dict):
        raise ValueError("NWS observation properties required")
    station = "https://api.weather.gov/stations/" + expected_station
    identity = props.get("@id")
    if (props.get("station") != station
            or props.get("stationId", expected_station) != expected_station
            or not isinstance(identity, str) or len(identity) > 512
            or not identity.startswith(station + "/observations/")
            or not identity.removeprefix(station + "/observations/")
            or any(c in identity for c in ("?", "#", "\\"))):
        raise ValueError("NWS station/observation identity mismatch")
    observation_clock = native_clock(props.get("timestamp"), unit="iso8601",
                                     received_at=received_at)
    quantities = {}
    for name in NWS_QUANTITIES:
        if name not in props:
            quantities[name] = {"state": "not_reported"}
            continue
        q = props[name]
        if not isinstance(q, dict) or "value" not in q:
            raise ValueError("NWS quantitative value required")
        unit, qc = q.get("unitCode"), q.get("qualityControl")
        if (not isinstance(unit, str) or not 1 <= len(unit) <= 128
                or qc is not None and (not isinstance(qc, str) or len(qc) > 32)):
            raise ValueError("NWS quantity units/QC required")
        quantities[name] = {
            "state": "source_null" if q["value"] is None else "reported",
            "value": None if q["value"] is None else exact_decimal(q["value"]),
            "unit_code": unit, "quality_control": qc,
            "bounds": {k: exact_decimal(q[k]) for k in ("minValue", "maxValue") if k in q},
        }
    return {"station_id": expected_station, "observation_id": identity,
            "observation_clock": observation_clock, "quantities": quantities,
            "publication_clock": None, "first_release_known": False,
            "market_relevance_admitted": False, "quality_control_interpreted": False}
