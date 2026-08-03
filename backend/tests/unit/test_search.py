"""Tests for the company/ticker alias layer used by full-universe market search."""
from astrolabe.ingest.aliases import expand_query


def test_ticker_expands_to_company():
    terms = expand_query("MSFT")
    assert terms[0] == "MSFT"           # original first
    assert "microsoft" in [t.lower() for t in terms]


def test_company_expands_to_ticker():
    terms = expand_query("Microsoft")
    assert "msft" in [t.lower() for t in terms]


def test_case_insensitive():
    assert "microsoft" in [t.lower() for t in expand_query("msft")]
    assert "microsoft" in [t.lower() for t in expand_query("MsFt")]


def test_unknown_term_is_searched_as_is():
    assert expand_query("Will it rain in London") == ["Will it rain in London"]


def test_empty_query():
    assert expand_query("") == []
    assert expand_query("   ") == []


def test_multi_alias_group():
    terms = [t.lower() for t in expand_query("google")]
    assert "alphabet" in terms and ("goog" in terms or "googl" in terms)
