"""Complete-pagination tests for the Gamma client (prompt sections 2, 21).

Uses an httpx MockTransport so no network is touched. Proves the scanner follows every page until
the upstream signals completion, deduplicates deterministically, and - critically - marks the scan
INCOMPLETE (never silently complete) on an offset cap, a non-progressing page, an emergency guard
trip or a transient failure after retries. The acceptance test proves it does not stop merely
because page one is full.
"""
import httpx

from astrolabe.clients.gamma import GammaClient


def _market(i: int) -> dict:
    return {"id": str(i), "conditionId": f"c{i}", "question": f"Q{i}"}


def _dataset_handler(total: int, page_size: int = 100, cap: int | None = None):
    """Serve ``total`` markets via offset pages, optionally 422-capping at offset ``cap``."""

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        offset = int(params.get("offset", "0"))
        limit = int(params.get("limit", str(page_size)))
        if cap is not None and offset >= cap:
            return httpx.Response(
                422, json={"type": "validation error",
                           "error": "offset too large, use /markets/keyset"}
            )
        page = [_market(i) for i in range(offset, min(offset + limit, total))]
        return httpx.Response(200, json=page)

    return handler


def _client(handler) -> GammaClient:
    transport = httpx.MockTransport(handler)
    ac = httpx.AsyncClient(transport=transport, base_url="https://gamma.test")
    return GammaClient(ac)


async def test_single_page_complete():
    async with _client(_dataset_handler(40)) as g:
        markets, rep = await g.paginate_markets(page_size=100)
    assert len(markets) == 40 and rep.complete is True
    assert rep.pages == 1 and rep.raw_items == 40 and rep.unique_markets == 40


async def test_multiple_pages_complete():
    async with _client(_dataset_handler(250)) as g:
        markets, rep = await g.paginate_markets(page_size=100)
    assert rep.complete is True and len(markets) == 250
    assert rep.pages == 3  # 100 + 100 + 50 (short final page = genuine end)
    assert rep.offset_progression == [0, 100, 200]


async def test_full_page_one_does_not_stop_pagination():
    """The acceptance test: exactly page_size on page one with more pages remaining must NOT stop.

    This is the exact bug that produced the 60-market cohort - a full first page treated as the
    whole universe.
    """
    async with _client(_dataset_handler(60, page_size=60)) as g:
        # 60 on page one, but there are 500 total: must keep going, not stop at 60.
        pass
    async with _client(_dataset_handler(500, page_size=60)) as g:
        markets, rep = await g.paginate_markets(page_size=60)
    assert len(markets) == 500 and rep.complete is True
    assert rep.pages == 9  # 8 full pages of 60 (480) + a short page of 20


async def test_five_hundred_plus_records():
    async with _client(_dataset_handler(1234)) as g:
        markets, rep = await g.paginate_markets(page_size=100)
    assert len(markets) == 1234 and rep.complete is True
    assert rep.pages == 13 and rep.unique_markets == 1234


async def test_duplicates_across_pages_are_deduplicated_deterministically():
    # Every page repeats market c0..c9 plus fresh ones, then ends.
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        if offset >= 300:
            return httpx.Response(200, json=[])
        shared = [_market(i) for i in range(10)]           # duplicated on every page
        fresh = [_market(1000 + offset + i) for i in range(90)]
        return httpx.Response(200, json=shared + fresh)

    async with _client(handler) as g:
        m1, r1 = await g.paginate_markets(page_size=100)
        m2, r2 = await g.paginate_markets(page_size=100)
    # 10 shared (counted once) + 90*3 fresh = 280 unique; duplicates removed recorded.
    assert r1.unique_markets == 10 + 90 * 3
    assert r1.duplicates_removed == 20  # 10 dup on page 2 and page 3 each
    assert r1.complete is True
    # Deterministic: identical result on a repeat scan (idempotent).
    assert [x["conditionId"] for x in m1] == [x["conditionId"] for x in m2]
    assert r1.as_dict() == r2.as_dict()


async def test_repeated_page_is_flagged_incomplete():
    # The upstream keeps returning the SAME page (non-progressing cursor/offset).
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_market(i) for i in range(100)])

    async with _client(handler) as g:
        _markets, rep = await g.paginate_markets(page_size=100)
    assert rep.complete is False
    assert rep.repeated_page_detected is True
    assert "non-progressing" in rep.incomplete_reason


async def test_offset_cap_marks_incomplete_and_fails_loud():
    # 5000 markets exist but the upstream 422-caps offset at 2100 (the real Gamma behaviour).
    async with _client(_dataset_handler(5000, cap=2100)) as g:
        markets, rep = await g.paginate_markets(page_size=100)
    assert rep.offset_cap_reached is True
    assert rep.complete is False               # NEVER silently complete
    assert "offset pagination cap" in rep.incomplete_reason
    assert len(markets) == 2100                # everything reachable was still returned


async def test_emergency_guard_trips_and_marks_incomplete():
    # An endless upstream (never empties, always progresses) must be stopped by the guard, loudly.
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        return httpx.Response(200, json=[_market(offset + i) for i in range(100)])

    async with _client(handler) as g:
        _markets, rep = await g.paginate_markets(page_size=100, max_pages=5)
    assert rep.complete is False and rep.pages == 5
    assert "emergency loop guard" in rep.incomplete_reason


async def test_retry_success_after_transient_failure():
    state = {"fails": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        if offset == 100 and state["fails"] < 2:
            state["fails"] += 1
            return httpx.Response(503, json={"error": "transient"})
        if offset >= 200:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[_market(i) for i in range(offset, offset + 100)])

    async with _client(handler) as g:
        markets, rep = await g.paginate_markets(page_size=100)
    assert rep.complete is True and len(markets) == 200  # recovered on page 2


async def test_retry_exhaustion_marks_incomplete():
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        if offset == 100:
            return httpx.Response(503, json={"error": "down"})  # always fails
        return httpx.Response(200, json=[_market(i) for i in range(offset, offset + 100)])

    async with _client(handler) as g:
        markets, rep = await g.paginate_markets(page_size=100)
    assert rep.complete is False
    assert "failed at offset 100" in rep.incomplete_reason
    assert len(markets) == 100  # page one was kept, but the scan is not complete


async def test_list_markets_still_single_page():
    """The non-paginating list_markets is unchanged (used elsewhere); it returns one page only."""
    async with _client(_dataset_handler(500)) as g:
        page = await g.list_markets(limit=100, offset=0)
    assert len(page) == 100
