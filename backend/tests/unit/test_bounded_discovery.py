"""Bounded keyset discovery tests (prompt A2-A5, F1).

Deterministic httpx MockTransport, no network. Proves the official ``after_cursor`` contract
advances and terminates, that markets and events keyset paths reconcile, that bounded date params
are sent, that an incomplete keyset path triggers recursive window bisection, and that completeness
is only declared when every path terminated normally.
"""

import httpx

from astrolabe.clients.gamma import GammaClient
from astrolabe.discovery.bounded_discovery import BoundedDiscovery


def _mk(i: int) -> dict:
    return {"id": str(i), "conditionId": f"c{i}", "question": f"Q{i}",
            "endDate": "2026-08-10T00:00:00Z"}


class Dataset:
    """Serves keyset pages keyed by an integer ``after_cursor`` = offset. Optionally never
    terminates for a WIDE date window (to exercise bisection) but terminates for narrow ones."""

    def __init__(self, n_markets: int, *, page: int = 100,
                 bisect_threshold_hours: float | None = None, events_extra: int = 0):
        self.n = n_markets
        self.page = page
        self.bisect_threshold = bisect_threshold_hours
        self.events_extra = events_extra
        self.requests: list[dict] = []

    def _width_hours(self, params) -> float:
        if "end_date_min" in params and "end_date_max" in params:
            from datetime import datetime
            try:
                a = datetime.fromisoformat(params["end_date_min"].replace("Z", "+00:00"))
                b = datetime.fromisoformat(params["end_date_max"].replace("Z", "+00:00"))
                return (b - a).total_seconds() / 3600
            except Exception:
                return 9999.0
        return 9999.0

    def handler(self, request: httpx.Request) -> httpx.Response:
        params = request.url.params
        self.requests.append(dict(params))
        after = params.get("after_cursor")
        try:
            offset = int(after) if after is not None else 0
        except ValueError:
            offset = 0
        path = request.url.path
        width = self._width_hours(params)
        if path == "/markets/keyset":
            # If configured to cap wide windows, return a REPEATED cursor so pagination is detected
            # as non-progressing at once (incomplete) -> forces the windowed bisection fallback.
            if self.bisect_threshold is not None and width > self.bisect_threshold:
                return httpx.Response(200, json={"markets": [_mk(offset)],
                                                 "next_cursor": "STUCK"})
            page = [_mk(i) for i in range(offset, min(offset + self.page, self.n))]
            nxt = offset + self.page
            body = {"markets": page}
            if nxt < self.n and page:
                body["next_cursor"] = str(nxt)
            return httpx.Response(200, json=body)
        if path == "/events/keyset":
            # Verification path: wrap markets in events (2 markets per event), plus a few extras
            # only-verification markets to exercise reconciliation.
            total = self.n + self.events_extra
            page_ids = list(range(offset, min(offset + self.page, total)))
            events = []
            for j in range(0, len(page_ids), 2):
                ms = [_mk(k) if k < self.n else {**_mk(10_000 + k), "conditionId": f"vc{k}"}
                      for k in page_ids[j:j + 2]]
                events.append({"id": f"e{page_ids[j]}", "markets": ms})
            nxt = offset + self.page
            body = {"events": events}
            if nxt < total and page_ids:
                body["next_cursor"] = str(nxt)
            return httpx.Response(200, json=body)
        return httpx.Response(404, json={})


def _client(ds: Dataset) -> GammaClient:
    transport = httpx.MockTransport(ds.handler)
    return GammaClient(httpx.AsyncClient(transport=transport, base_url="https://gamma.test"))


async def test_after_cursor_advances_and_terminates():
    ds = Dataset(250)
    async with _client(ds) as g:
        items, rep = await g.paginate_keyset("/markets/keyset", "markets")
    assert rep["complete"] is True
    assert len(items) == 250 and rep["pages"] == 3  # 100+100+50, terminates when cursor absent
    # The FIRST request must omit after_cursor; later ones must send it.
    assert "after_cursor" not in ds.requests[0]
    assert ds.requests[1]["after_cursor"] == "100"


async def test_repeated_cursor_marks_incomplete():
    def handler(request):
        return httpx.Response(200, json={"markets": [_mk(1)], "next_cursor": "SAME"})
    g = GammaClient(httpx.AsyncClient(transport=httpx.MockTransport(handler),
                                      base_url="https://gamma.test"))
    async with g:
        _items, rep = await g.paginate_keyset("/markets/keyset", "markets")
    assert rep["complete"] is False and "non-progressing" in rep["incomplete_reason"]


async def test_bounded_date_params_are_sent():
    ds = Dataset(50)
    async with _client(ds) as g:
        await g.paginate_keyset("/markets/keyset", "markets",
                                end_date_min="A", end_date_max="B")
    assert ds.requests[0]["end_date_min"] == "A" and ds.requests[0]["end_date_max"] == "B"
    assert ds.requests[0]["active"] == "true" and ds.requests[0]["closed"] == "false"


async def test_reconciliation_union_keeps_only_verification_markets():
    # 200 shared markets + 20 only-verification markets from events.
    ds = Dataset(200, events_extra=20)
    async with _client(ds) as g:
        markets, report = await BoundedDiscovery(g).discover()
    assert report.complete is True
    assert report.primary_unique == 200
    # union includes the only-verification markets (never silently dropped).
    assert report.only_verification == 20
    assert report.union_unique == 220
    assert report.identity_conflicts == 0
    assert len(markets) == 220


async def test_more_than_2100_records_via_keyset():
    ds = Dataset(5000)
    async with _client(ds) as g:
        items, rep = await g.paginate_keyset("/markets/keyset", "markets")
    assert rep["complete"] is True and len(items) == 5000  # no 2100 offset cap on keyset


async def test_incomplete_primary_triggers_window_bisection():
    # Windows wider than 6h return a repeated (stuck) cursor -> incomplete; windows <=6h terminate.
    # Discovery must bisect the wide windows down until each exhausts.
    ds = Dataset(40, bisect_threshold_hours=6.0)
    async with _client(ds) as g:
        _markets, report = await BoundedDiscovery(g).discover()
    # The windowed fallback was used and windows were scanned (wide ones bisected to <=6h).
    assert any("windowed_fallback" in m for m in report.methods)
    assert len(report.windows) > 0
    assert all(w["hours"][1] - w["hours"][0] <= 6.0 or not w["complete"] for w in report.windows)
