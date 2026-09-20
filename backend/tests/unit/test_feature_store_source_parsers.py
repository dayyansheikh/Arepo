from datetime import UTC, datetime
from decimal import Decimal

import pytest

from astrolabe.feature_store.source_parsers import (
    clob_book,
    data_v2_trades,
    gamma_identity,
    native_clock,
)

NOW = datetime(2026, 9, 20, tzinfo=UTC)
CONDITION = "0x" + "a" * 64


@pytest.mark.parametrize("raw,unit,reason", [
    (None, "epoch_ms", "not_supported"), ("123", None, "invalid"),
    ("bad", "epoch_s", "invalid"), (True, "epoch_s", "invalid"),
    (1.2, "epoch_s", "invalid"), ("2026-09-20", "iso8601", "invalid"),
    ("-1", "epoch_s", "invalid"), ("1e900", "epoch_s", "invalid"),
])
def test_missing_and_invalid_clocks_do_not_become_receipt(raw, unit, reason):
    result = native_clock(raw, unit=unit, received_at=NOW)
    assert result["value"] is None
    assert result["raw"] == raw
    assert result["missing_reason"] == reason


def test_precision_and_future_clocks_are_flagged():
    result = native_clock("1234567890.123456789", unit="epoch_s", received_at=NOW)
    assert result["value"].microsecond == 123456
    assert result["quality_flags"] == ["timestamp_precision"]
    future = native_clock("2030-01-01T00:00:00Z", unit="iso8601", received_at=NOW)
    assert "future_source_clock" in future["quality_flags"]
    assert native_clock("1234567890123", unit="epoch_ms", received_at=NOW)["value"] == (
        native_clock("1234567890.123", unit="epoch_s", received_at=NOW)["value"])


def gamma():
    return {"id": "12", "conditionId": CONDITION, "questionID": "0x" + "b" * 64,
            "clobTokenIds": '["123456789012345678901234567890", "2"]',
            "outcomes": '["Yes", "No"]', "description": "original rules",
            "events": [{"id": "3"}]}


def test_ordered_identity_and_rule_revisions_are_not_current_defaults():
    first = gamma_identity(gamma())
    changed = gamma()
    changed["outcomes"] = '["No", "Yes"]'
    second = gamma_identity(changed)
    assert first["outcomes"][0]["token_id"] == "123456789012345678901234567890"
    assert first["mapping_version"] != second["mapping_version"]
    assert first["chain_id"] is None and first["collateral_address"] is None
    assert first["economic_group_status"] == "unresolved"
    changed["description"] = "corrected rules"
    assert gamma_identity(changed)["rules_hash"] != first["rules_hash"]


@pytest.mark.parametrize("field,value", [("clobTokenIds", '["1", "1"]'),
                                         ("outcomes", '["Yes"]'),
                                         ("conditionId", "missing")])
def test_unresolvable_identity_refused(field, value):
    row = gamma()
    row[field] = value
    with pytest.raises(ValueError):
        gamma_identity(row)


def book():
    return {"asset_id": "1", "market": CONDITION, "timestamp": None,
            "bids": [{"price": "0.600", "size": "0.000"}],
            "asks": [{"price": "0.40", "size": "12.12345678901234567890123"}]}


def test_book_zero_and_spelling_preserved_no_timestamp_substitution():
    result = clob_book(book(), expected_token="1", expected_condition=CONDITION)
    assert result["bids"][0]["size"].as_tuple() == Decimal("0.000").as_tuple()
    assert result["timestamp_raw"] is None
    assert "one_sided_book" in result["quality_flags"]
    row = book()
    row["bids"][0]["size"] = "1"
    assert "crossed_book" in clob_book(row)["quality_flags"]
    row.pop("asks")
    with pytest.raises(ValueError, match="missing book side"):
        clob_book(row)
    with pytest.raises(ValueError, match="token mismatch"):
        clob_book(book(), expected_token="2")


def test_trade_paging_duplicates_and_transaction_hash_are_not_fill_identity():
    row = {"condition_id": CONDITION, "token_id": "1", "price": Decimal("0.450"),
           "size": Decimal("1.001"), "side": "BUY", "transaction_hash": "tx"}
    payload = {"data": [row, row], "pagination": {"has_more": True, "next_cursor": "opaque"}}
    result = data_v2_trades(payload)
    assert len(result["rows"]) == 2 and result["identical_rows"] == 1
    assert result["rows"][0]["price_raw"] == "0.450"
    assert result["rows"][0]["economic_fill_id"] is None
    assert result["coverage_fraction"] is None
    payload["pagination"]["next_cursor"] = None
    with pytest.raises(ValueError, match="cursor"):
        data_v2_trades(payload)
    with pytest.raises(ValueError, match="v2 envelope"):
        data_v2_trades([row])
