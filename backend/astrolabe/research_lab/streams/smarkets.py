# ruff: noqa: E501
"""Smarkets exchange quotes for politics and current affairs (a real-money UK exchange crowd on the same
questions as Polymarket / Kalshi / PredictIt; CH114's cross-venue family, the 2026-11-03 US midterms).

Keyless public API ``https://api.smarkets.com/v3``. Every poll (5-minute slot):

* ``GET /markets/<ids>/quotes/`` (batches of ``BATCH`` market ids): the order book per contract; we keep the top
  ``DEPTH`` levels per side as ``[price, quantity]``. Smarkets units, kept RAW: ``price`` in basis points of
  probability (``1754`` = 17.54 %), ``quantity`` in the API's integer stake units;
* ``GET /markets/<ids>/last_executed_prices/``: last trade per contract with Smarkets' own ``timestamp`` (source
  clock, part of the value because it only changes on a trade).

Keys ``q:<contract id>`` = ``{market_id, bids, offers, last, last_ts}``. The catalogue (events, markets, contracts,
volumes) is refreshed every ``CATALOGUE_S`` seconds and on the first poll, and is written as ``ev:``, ``mk:``
and ``ct:`` keys on those polls only (their ``gone`` scopes apply only on catalogue polls).
"""

from __future__ import annotations

from typing import Any

from .common import FetchError, Http, PollResult, StreamSpec

BASE = "https://api.smarkets.com/v3"
DOMAINS = ("politics", "current_affairs")
BATCH = 25
EVENT_BATCH = 20
DEPTH = 3
CATALOGUE_S = 3600
MAX_MARKETS = 800
CLOSED_MARKET_STATES = {"settled", "voided", "cancelled", "closed"}


def _chunks(xs: list, n: int) -> list[list]:
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def fetch_events(http: Http) -> list[dict]:
    out: dict[str, dict] = {}
    for dom in DOMAINS:
        q = f"?state=upcoming&state=live&type_domain={dom}&limit=100&sort=id"
        for _ in range(50):  # pagination guard
            d = http.get_json(f"{BASE}/events/{q}", tag=f"events:{dom}")
            for e in d.get("events") or []:
                if isinstance(e, dict) and e.get("id") is not None:
                    out[str(e["id"])] = e
            nxt = (d.get("pagination") or {}).get("next_page")
            if not nxt:
                break
            q = nxt
        else:
            raise FetchError(f"smarkets: events pagination did not end ({dom})")
    return [out[k] for k in sorted(out)]


def build_catalogue(http: Http) -> dict:
    events = fetch_events(http)
    markets: list[dict] = []
    for ch in _chunks([e["id"] for e in events], EVENT_BATCH):
        d = http.get_json(f"{BASE}/events/{','.join(map(str, ch))}/markets/", tag="markets")
        markets += [m for m in d.get("markets") or [] if isinstance(m, dict) and m.get("id") is not None]
    markets = [m for m in markets if str(m.get("state", "")).lower() not in CLOSED_MARKET_STATES]
    markets.sort(key=lambda m: int(m["id"]))
    truncated = len(markets) > MAX_MARKETS
    markets = markets[:MAX_MARKETS]
    contracts: list[dict] = []
    volumes: dict[str, Any] = {}
    for ch in _chunks([m["id"] for m in markets], BATCH):
        ids = ",".join(map(str, ch))
        d = http.get_json(f"{BASE}/markets/{ids}/contracts/", tag="contracts")
        contracts += [c for c in d.get("contracts") or [] if isinstance(c, dict) and c.get("id") is not None]
        v = http.get_json(f"{BASE}/markets/{ids}/volumes/", tag="volumes")
        for row in v.get("volumes") or []:
            if isinstance(row, dict) and row.get("market_id") is not None:
                volumes[str(row["market_id"])] = row.get("volume")
    return {"events": events, "markets": markets, "contracts": contracts, "volumes": volumes,
            "truncated": truncated}


def catalogue_items(cat: dict) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for e in cat["events"]:
        items[f"ev:{e['id']}"] = {k: e.get(k) for k in (
            "name", "type", "state", "start_datetime", "end_date", "parent_id", "full_slug", "modified")}
    for m in cat["markets"]:
        items[f"mk:{m['id']}"] = {**{k: m.get(k) for k in (
            "event_id", "name", "state", "winner_count", "created", "modified", "description")},
            "volume": cat["volumes"].get(str(m["id"]))}
    for c in cat["contracts"]:
        items[f"ct:{c['id']}"] = {k: c.get(k) for k in (
            "market_id", "name", "slug", "state_or_outcome", "outcome_timestamp", "modified")}
    return items


def _levels(xs: Any) -> list[list]:
    out = []
    for lv in (xs or [])[:DEPTH]:
        if isinstance(lv, dict):
            out.append([lv.get("price"), lv.get("quantity")])
    return out


def quote_items(quotes: dict, last_prices: dict, contract_market: dict[str, str]) -> dict[str, Any]:
    lep: dict[str, tuple] = {}
    for rows in (last_prices or {}).values():
        for r in rows or []:
            if isinstance(r, dict) and r.get("contract_id") is not None:
                lep[str(r["contract_id"])] = (r.get("last_executed_price"), r.get("timestamp"))
    items: dict[str, Any] = {}
    for cid, book in (quotes or {}).items():
        if not isinstance(book, dict):
            continue
        last, last_ts = lep.get(str(cid), (None, None))
        items[f"q:{cid}"] = {"market_id": contract_market.get(str(cid)), "bids": _levels(book.get("bids")),
                             "offers": _levels(book.get("offers")), "last": last, "last_ts": last_ts}
    return items


def poll(http: Http, extra: dict, *, t0: float, **_: Any) -> PollResult:
    cat = extra.get("catalogue")
    items: dict[str, Any] = {}
    scopes: list[str] = []
    refreshed = False
    if not cat or t0 - float(extra.get("catalogue_t", 0)) >= CATALOGUE_S:
        full = build_catalogue(http)
        items.update(catalogue_items(full))
        scopes += ["ev:", "mk:", "ct:"]
        cat = {"market_ids": [str(m["id"]) for m in full["markets"]],
               "contract_market": {str(c["id"]): str(c.get("market_id")) for c in full["contracts"]},
               "truncated": full["truncated"]}
        refreshed = True
    quotes: dict = {}
    lep: dict = {}
    for ch in _chunks(cat["market_ids"], BATCH):
        ids = ",".join(ch)
        quotes.update(http.get_json(f"{BASE}/markets/{ids}/quotes/", tag="quotes") or {})
        lep.update((http.get_json(f"{BASE}/markets/{ids}/last_executed_prices/", tag="lep") or {})
                   .get("last_executed_prices") or {})
    items.update(quote_items(quotes, lep, cat["contract_market"]))
    scopes.append("q:")
    new_extra = {"catalogue": cat, "catalogue_t": t0 if refreshed else extra.get("catalogue_t")}
    meta = {"catalogue_refreshed": refreshed, "n_markets": len(cat["market_ids"]),
            "n_quoted_contracts": sum(k.startswith("q:") for k in items),
            "catalogue_truncated": cat.get("truncated", False)}
    return PollResult(items=items, scopes=tuple(scopes), meta=meta, extra_state=new_extra)


SPEC = StreamSpec(name="smarkets", dirname="stream_smarkets", slot_s=300, checkpoint_s=3600,
                  allowance_bytes=5_000_000, stream_cap_gb=3.0, rps=1.0, budget_s=240, poll=poll)
