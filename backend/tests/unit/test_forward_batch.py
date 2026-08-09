"""Batched + deduplicated forward-quote collection: proves functional EQUIVALENCE to the per-token
path and that the batch endpoint dedups + chunks (the scaling fix for the collect job).
"""
import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import event

from astrolabe.clients.clob_rest import ClobRestClient
from astrolabe.config import Settings
from astrolabe.evaluation.research_constants import CADENCE_6H
from astrolabe.evaluation.research_engine import build_entry_inputs, freeze_from_inputs
from astrolabe.evaluation.research_tracking import (
    Quote,
    clob_batch_quotes,
    collect_due_forward,
    quote_from_book,
)
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

from .test_research_pipeline import _screen  # reuse the screen builder

CUTOFF = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


async def _fresh_frozen_db():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    s = await sm().__aenter__()
    screens = [_screen("m1", 0.6, "up", 2, rp=90), _screen("m2", 0.6, "down", 2, rp=89)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    await freeze_from_inputs(s, cadence=CADENCE_6H, cutoff_at=CUTOFF, inputs=inputs,
                             model_version="m", calculation_version="c", frozen_at=CUTOFF)
    return engine, s


def _forward_rows(session):
    from sqlalchemy import select

    from astrolabe.evaluation.research_models import ResearchForwardRow

    async def _q():
        res = await session.execute(select(ResearchForwardRow))
        return sorted(
            (r.entry_id, r.horizon, r.midpoint, r.best_bid, r.best_ask, r.spread,
             r.near_mid_depth, r.unavailable_reason)
            for r in res.scalars().all()
        )
    return _q()


async def test_batch_and_per_token_forward_are_equivalent():
    """Same stored observations whether quotes come per-token (price_of) or batched (quotes_of)."""
    now = CUTOFF + timedelta(minutes=90)  # 1h horizon elapsed, 6h/24h/7d not
    quotes = {
        "m1-yes": Quote(0.55, 0.54, 0.56, 0.02, 1000.0),
        "m2-yes": Quote(0.40, 0.39, 0.41, 0.02, 900.0),
    }

    async def price_of(_mid, tok):
        return quotes.get(tok)

    async def quotes_of(tokens):
        return {t: quotes.get(t) for t in tokens}

    eng_a, sa = await _fresh_frozen_db()
    ra = await collect_due_forward(sa, now=now, price_of=price_of)
    rows_a = await _forward_rows(sa)
    await eng_a.dispose()

    eng_b, sb = await _fresh_frozen_db()
    rb = await collect_due_forward(sb, now=now, quotes_of=quotes_of)
    rows_b = await _forward_rows(sb)
    await eng_b.dispose()

    assert ra["written"] == rb["written"] > 0
    assert rows_a == rows_b  # byte-identical stored observations


async def test_dedup_one_fetch_per_token_across_horizons():
    """A token with several due horizons is fetched ONCE (dedup), not once per horizon."""
    now = CUTOFF + timedelta(hours=25)  # 1h + 6h + 24h all elapsed for m1/m2
    asked: list[list[str]] = []

    async def quotes_of(tokens):
        asked.append(list(tokens))
        return {t: Quote(0.5, 0.49, 0.51, 0.02, 100.0) for t in tokens}

    eng, s = await _fresh_frozen_db()
    r = await collect_due_forward(s, now=now, quotes_of=quotes_of)
    await eng.dispose()
    # 2 tokens, each with 3 due horizons -> 6 observations but only 2 unique token fetches.
    assert r["written"] == 6
    assert sorted(asked[0]) == ["m1-yes", "m2-yes"]  # deduped to 2 unique tokens, one batch call
    assert len(asked) == 1


async def test_forward_batch_flushes_once_at_commit():
    """A horizon spike is persisted in one flush, not one remote round-trip per row."""
    now = CUTOFF + timedelta(hours=25)  # 2 entries x 3 elapsed horizons = 6 inserts

    async def quotes_of(tokens):
        return {t: Quote(0.5, 0.49, 0.51, 0.02, 100.0) for t in tokens}

    eng, s = await _fresh_frozen_db()
    flushes = 0

    @event.listens_for(s.sync_session, "before_flush")
    def _count_flushes(*_args):
        nonlocal flushes
        flushes += 1

    result = await collect_due_forward(s, now=now, quotes_of=quotes_of)
    rows = await _forward_rows(s)
    await eng.dispose()

    assert result["written"] == 6
    assert len(rows) == 6
    assert flushes == 1


def _clob_with_mock(handler):
    client = httpx.AsyncClient(base_url="https://clob.local",
                               transport=httpx.MockTransport(handler))
    return ClobRestClient(client=client, settings=Settings())


async def test_get_books_dedups_and_chunks():
    calls = {"n": 0, "bodies": []}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(request.content)
        calls["bodies"].append([b["token_id"] for b in body])
        return httpx.Response(200, json=[
            {"asset_id": b["token_id"], "bids": [{"price": "0.50", "size": "100"}],
             "asks": [{"price": "0.52", "size": "80"}]} for b in body])

    clob = _clob_with_mock(handler)
    books = await clob.get_books(["a", "a", "b", "c"], batch_size=2)  # dup 'a'
    await clob.aclose()
    assert set(books) == {"a", "b", "c"}                 # deduped
    assert calls["n"] == 2                                # 3 unique / batch 2 -> 2 requests
    assert all(len(b) <= 2 for b in calls["bodies"])      # each request within batch size


def test_quote_from_book_matches_book_normalisation():
    raw = {"bids": [{"price": "0.49", "size": "100"}, {"price": "0.48", "size": "50"}],
           "asks": [{"price": "0.51", "size": "80"}], "timestamp": "0"}
    q = quote_from_book("tok", raw)
    assert q is not None
    assert q.best_bid == 0.49 and q.best_ask == 0.51
    assert abs(q.midpoint - 0.50) < 1e-9 and abs(q.spread - 0.02) < 1e-9
    assert quote_from_book("tok", None) is None          # no book -> unavailable
    assert quote_from_book("tok", {"bids": [], "asks": []}) is None


async def test_clob_batch_quotes_provider_maps_all_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        # return a book only for 'a' -> 'b' must map to None (unavailable), never missing
        return httpx.Response(200, json=[
            {"asset_id": b["token_id"], "bids": [{"price": "0.5", "size": "10"}],
             "asks": [{"price": "0.52", "size": "10"}]}
            for b in body if b["token_id"] == "a"])

    clob = _clob_with_mock(handler)
    quotes_of = clob_batch_quotes(clob)
    out = await quotes_of(["a", "b"])
    await clob.aclose()
    assert out["a"] is not None and out["b"] is None


async def test_dependence_aware_headline_dedups_markets_across_cohorts():
    """A market frozen in several 6h cohorts is counted ONCE in the headline (dependence-aware)."""
    from datetime import timedelta

    from astrolabe.evaluation.research_constants import CADENCE_6H
    from astrolabe.evaluation.research_replay import ResearchReplayService
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        # Same market m1 frozen in two 6h cohorts (two boundaries).
        for k in range(2):
            cutoff = CUTOFF + timedelta(hours=6 * k)
            inputs = build_entry_inputs([_screen("m1", 0.6, "up", 2, rp=90)], now=cutoff)
            await freeze_from_inputs(s, cadence=CADENCE_6H, cutoff_at=cutoff, inputs=inputs,
                                     model_version="m", calculation_version="c", frozen_at=cutoff)
        head = await ResearchReplayService(s).dependence_aware_headline()
    await engine.dispose()
    assert head["cohorts_pooled"] == 2
    assert head["unique_markets"] == 1        # m1 counted once, not twice
    assert head["wider_unique"] == 1
