# ruff: noqa: E501
"""PredictIt all-markets quotes (CH114: fee-adjusted third-crowd anchor on political questions).

One keyless request per poll: ``GET https://www.predictit.org/api/marketdata/all/`` (the whole open universe,
about 200 markets / 600+ contracts, about 460 kB). PredictIt updates the feed about once a minute; we poll once a
minute and never faster. Keys:

* ``m:<market id>``: ``{name, short_name, status, url}`` (metadata; changes rarely);
* ``c:<contract id>``: ``{market_id, name, short_name, status, date_end, last, buy_yes, buy_no, sell_yes,
  sell_no, last_close, display_order}``. PredictIt price fields: ``bestBuyYesCost`` = best ask for YES,
  ``bestSellYesCost`` = best bid for YES (likewise NO); null = no order on that side. Values are dollars.

Source clock: the market's ``timeStamp`` (PredictIt's own, a naive local-time string, kept RAW, never converted)
is stored as ``src_ts`` on market rows and as min/max in the poll meta; it never enters the change hash.
"""

from __future__ import annotations

from typing import Any

from .common import FetchError, Http, PollResult, StreamSpec

URL = "https://www.predictit.org/api/marketdata/all/"


def parse(payload: Any) -> PollResult:
    if not isinstance(payload, dict) or not isinstance(payload.get("markets"), list):
        raise FetchError("predictit: payload has no markets list")
    items: dict[str, Any] = {}
    src: dict[str, Any] = {}
    stamps = []
    for m in payload["markets"]:
        if not isinstance(m, dict) or m.get("id") is None:
            continue
        mid = str(m["id"])
        items[f"m:{mid}"] = {"name": m.get("name"), "short_name": m.get("shortName"),
                             "status": m.get("status"), "url": m.get("url")}
        if m.get("timeStamp") is not None:
            src[f"m:{mid}"] = m["timeStamp"]
            stamps.append(str(m["timeStamp"]))
        for c in m.get("contracts") or []:
            if not isinstance(c, dict) or c.get("id") is None:
                continue
            items[f"c:{c['id']}"] = {
                "market_id": mid, "name": c.get("name"), "short_name": c.get("shortName"),
                "status": c.get("status"), "date_end": c.get("dateEnd"),
                "last": c.get("lastTradePrice"), "buy_yes": c.get("bestBuyYesCost"),
                "buy_no": c.get("bestBuyNoCost"), "sell_yes": c.get("bestSellYesCost"),
                "sell_no": c.get("bestSellNoCost"), "last_close": c.get("lastClosePrice"),
                "display_order": c.get("displayOrder"),
            }
    if not items:
        raise FetchError("predictit: zero markets parsed")
    meta = {"n_markets": sum(k.startswith("m:") for k in items),
            "n_contracts": sum(k.startswith("c:") for k in items),
            "src_ts_min": min(stamps) if stamps else None, "src_ts_max": max(stamps) if stamps else None}
    # the feed is the whole universe: absent markets/contracts are "gone" (delisted or closed)
    return PollResult(items=items, scopes=("m:", "c:"), src_ts=src, meta=meta)


def poll(http: Http, extra: dict, **_: Any) -> PollResult:
    return parse(http.get_json(URL, tag="all"))


SPEC = StreamSpec(name="predictit", dirname="stream_predictit", slot_s=60, checkpoint_s=3600,
                  allowance_bytes=2_000_000, stream_cap_gb=2.0, rps=0.5, budget_s=45, poll=poll)
