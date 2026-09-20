"""Lossless storage primitives. No settings, engines, or network access on import."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import DateTime, Text
from sqlalchemy.types import TypeDecorator

DECIMAL_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
UINT_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\Z")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
MAX_NUMERIC_CHARACTERS = 4096
UINT256_MAX = (1 << 256) - 1


def exact_decimal(value: Decimal | str | int) -> Decimal:
    """Reject binary floats, booleans and nonfinite values rather than invent precision."""
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise ValueError("exact decimal requires Decimal, source string or integer")
    raw = str(value)
    if len(raw) > MAX_NUMERIC_CHARACTERS or not DECIMAL_PATTERN.fullmatch(raw):
        raise ValueError("invalid or oversized exact decimal; preserve the raw source separately")
    try:
        result = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("invalid exact decimal") from exc
    if not result.is_finite():
        raise ValueError("nonfinite exact decimal")
    return result


def uint_text(value: str | int, *, bits: int | None = None) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("unsigned integer requires exact string or integer")
    result = str(value)
    if len(result) > MAX_NUMERIC_CHARACTERS or not UINT_PATTERN.fullmatch(result):
        raise ValueError("unsigned integer must be canonical nonnegative decimal text")
    if bits is not None and (len(result) > len(str((1 << bits) - 1)) or int(result) >= (1 << bits)):
        raise ValueError(f"integer exceeds uint{bits}")
    return result


def utc_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("an aware datetime is required; naive time is not UTC evidence")
    return value.astimezone(UTC)


def utc_text(value: datetime) -> str:
    return utc_datetime(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_value(value: Any) -> Any:
    """Canonical hashing representation; finite derived floats need explicit hex tags."""
    if isinstance(value, Decimal):
        return {"$decimal": str(exact_decimal(value))}
    if isinstance(value, datetime):
        return {"$utc": utc_text(value)}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("canonical object keys must be strings")
        return {k: canonical_value(v) for k, v in value.items()}
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_id(entity: str, natural_key: Any) -> str:
    payload = canonical_json(["arepo-fs-v2.0", entity, natural_key])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ExactDecimal(TypeDecorator[Decimal]):
    """TEXT on both dialects: SQLite NUMERIC affinity may silently round through float."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(exact_decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else exact_decimal(value)


class UnsignedIntegerText(TypeDecorator[str]):
    impl = Text
    cache_ok = True

    def __init__(self, bits: int | None = None):
        super().__init__()
        self.bits = bits

    def process_bind_param(self, value, dialect):
        return None if value is None else uint_text(value, bits=self.bits)

    def process_result_value(self, value, dialect):
        return None if value is None else uint_text(value, bits=self.bits)


class UTCDateTime(TypeDecorator[datetime]):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(DateTime(timezone=True))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return utc_datetime(value) if dialect.name == "postgresql" else utc_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return utc_datetime(value)
