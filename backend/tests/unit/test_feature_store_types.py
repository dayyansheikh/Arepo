"""Exact storage regressions: original values must survive, not just compare approximately."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, insert, select
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import create_async_engine

from astrolabe.feature_store.types import (
    UINT256_MAX,
    ExactDecimal,
    UnsignedIntegerText,
    UTCDateTime,
    canonical_json,
    exact_decimal,
    stable_id,
    uint_text,
    utc_text,
)


@pytest.mark.parametrize(
    "raw",
    [
        "0",
        "-0.000",
        "0.123456789012345678901234567890123456789",
        "1.2300",
        "1E-1000",
        "123456789012345678901234567890123456789012345678901234567890.0001",
    ],
)
async def test_decimal_sqlite_round_trip_retains_decimal_tuple(raw):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    meta = MetaData()
    table = Table(
        "exact_values",
        meta,
        Column("id", Integer, primary_key=True),
        Column("value", ExactDecimal()),
        Column("token", UnsignedIntegerText(256)),
        Column("at", UTCDateTime()),
    )
    at = datetime(2026, 9, 20, 7, 3, 2, 123456, tzinfo=timezone(timedelta(hours=1)))
    try:
        async with engine.begin() as conn:
            await conn.run_sync(meta.create_all)
            await conn.execute(insert(table).values(value=raw, token=str(UINT256_MAX), at=at))
            row = (await conn.execute(select(table))).one()
            assert row.value.as_tuple() == Decimal(raw).as_tuple()
            assert row.token == str(UINT256_MAX)
            assert row.at == at.astimezone(UTC)
            assert row.at.tzinfo == UTC
            await conn.execute(insert(table).values(value=None, token=None, at=None))
            missing = await conn.execute(select(table.c.value).where(table.c.id == 2))
            assert missing.scalar() is None
            with pytest.raises(StatementError, match="exact decimal requires"):
                await conn.execute(insert(table).values(value=0.1))
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    "value",
    [0.1, True, "NaN", "Infinity", "-Infinity", " 1", "1_000", "1,000", "", ".", "1" * 4097],
)
def test_invalid_decimal_is_not_silently_converted(value):
    with pytest.raises(ValueError):
        exact_decimal(value)


@pytest.mark.parametrize("value", [True, 1.5, "1.0", "-1", "01", " 1", str(UINT256_MAX + 1)])
def test_invalid_asset_identifier(value):
    with pytest.raises(ValueError):
        uint_text(value, bits=256)


def test_canonical_hash_is_deterministic_but_preserves_numerical_evidence():
    assert stable_id("test", {"b": 2, "a": 1}) == stable_id("test", {"a": 1, "b": 2})
    assert stable_id("test", Decimal("0")) != stable_id("test", None)
    assert stable_id("test", Decimal("1.00")) != stable_id("test", Decimal("1.0"))
    assert stable_id("test", ["a", "b"]) != stable_id("test", ["b", "a"])
    with pytest.raises(ValueError, match="unsupported canonical value"):
        canonical_json({"lossy": 0.1})
    with pytest.raises(ValueError, match="keys must be strings"):
        canonical_json({1: "ambiguous"})


def test_utc_rejects_naive_and_preserves_microseconds():
    with pytest.raises(ValueError, match="aware datetime"):
        utc_text(datetime(2026, 9, 20))
    assert utc_text(datetime(2026, 9, 20, microsecond=1, tzinfo=UTC)).endswith(".000001Z")
