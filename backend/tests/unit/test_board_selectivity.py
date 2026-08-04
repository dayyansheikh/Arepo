"""Selective Opportunity Board tests (spec §4): views + honest screened/directional counts."""
from datetime import UTC, datetime

import pytest

from astrolabe.opportunity.service import build_opportunity_board
from astrolabe.service import MarketService

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


class _NoTrades:
    async def get_market_trades(self, *a, **k):
        return []


@pytest.fixture
def svc():
    return MarketService()


async def _board(svc, view):
    return await build_opportunity_board(
        svc, _NoTrades(), requested_mode="replay", top=30, universe_limit=40, view=view, now=NOW
    )


async def test_default_view_is_directional_only(svc):
    board = await _board(svc, "directional")
    assert board.view == "directional"
    assert all(c.directional for c in board.cards)
    # Honest selectivity counts are populated; the directional view shows exactly the
    # directional cards (up to the top cap).
    assert board.screened_count >= 1
    assert board.directional_count >= len(board.cards)
    assert f"screened {board.screened_count}" in board.note
    assert "directional view" in board.note


async def test_inconclusive_view_has_no_directional(svc):
    board = await _board(svc, "inconclusive")
    assert board.view == "inconclusive"
    assert all(not c.directional for c in board.cards)


async def test_all_view_includes_everything_screened(svc):
    directional = await _board(svc, "directional")
    inconclusive = await _board(svc, "inconclusive")
    allv = await _board(svc, "all")
    assert len(allv.cards) >= len(directional.cards)
    # all == directional + inconclusive (up to the top cap)
    assert len(allv.cards) == min(30, len(directional.cards) + len(inconclusive.cards))


async def test_strongest_view_is_directional_sorted_by_strength(svc):
    board = await _board(svc, "strongest")
    assert board.view == "strongest"
    assert all(c.directional for c in board.cards)
    strengths = [c.signal_strength for c in board.cards]
    assert strengths == sorted(strengths, reverse=True)
