"""Pinned read-only probe contracts. No application settings or implicit network work."""

import re
from dataclasses import asdict, dataclass

from .admission import content_hash
from .types import uint_text


@dataclass(frozen=True)
class SourceContract:
    source_id: str
    endpoint: str
    documentation: str
    protocol: str
    parser_version: str
    clock_semantics: str
    units: str
    rights_scope: str = "bounded local diagnostic; bulk/commercial redistribution unverified"

    @property
    def version(self):
        return content_hash(asdict(self))

    def params(self, values):
        """Reject arbitrary URLs, auth, pagination fan-out and unbounded limits."""
        if self.source_id == "gamma.market":
            allowed = {"market_id"}
            value = values.get("market_id")
            if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]{0,77}", value):
                raise ValueError("one bounded canonical decimal market ID required")
        elif self.source_id == "gamma.markets":
            allowed = {"limit", "active", "closed"}
            if values.get("active") != "true" or values.get("closed") != "false":
                raise ValueError("diagnostic Gamma query requires explicit active/open filter")
        elif self.source_id == "gamma.markets.keyset":
            allowed = {"limit", "closed", "after_cursor"}
            if values.get("closed") != "false":
                raise ValueError("keyset frame requires explicit open-market scope")
            if "after_cursor" in values and (
                not isinstance(values["after_cursor"], str)
                or not 1 <= len(values["after_cursor"]) <= 8192
            ):
                raise ValueError("invalid keyset cursor")
        elif self.source_id == "data.v2.trades":
            allowed = {"limit", "condition", "taker_only", "cursor"}
            if values.get("taker_only") != "true":
                raise ValueError("diagnostic trades require explicit taker-only semantics")
            if "condition" in values:
                if not re.fullmatch(r"0x[0-9a-fA-F]{64}", values["condition"]):
                    raise ValueError("one exact condition is required")
            if "cursor" in values and (
                not isinstance(values["cursor"], str) or len(values["cursor"]) > 8192
            ):
                raise ValueError("invalid cursor")
        elif self.source_id == "clob.book":
            allowed = {"token_id"}
            uint_text(values.get("token_id"), bits=256)
        elif self.source_id == "coinbase.btc_usd.ticker":
            allowed = set()
        else:
            raise ValueError("source not allowlisted")
        if set(values) - allowed:
            raise ValueError("unsupported query parameters")
        if "limit" in allowed:
            limit = values.get("limit")
            maximum = 100 if self.source_id == "gamma.markets.keyset" else 10
            if type(limit) is not int or not 1 <= limit <= maximum:
                raise ValueError(f"probe limit must be an integer in 1..{maximum}")
        return dict(values)

    def request(self, values):
        """Build an exact public request; path identifiers are never query parameters."""
        params = self.params(values)
        if self.source_id == "gamma.market":
            return {"method": "GET", "url": self.endpoint.format(id=params["market_id"]),
                    "params": {}, "path_params": {"id": params["market_id"]}}
        return {"method": "GET", "url": self.endpoint, "params": params}

    def market_request_id(self, request):
        """Replay the exact fixed-host path contract, including absent query/auth fields."""
        if not isinstance(request, dict) or not isinstance(request.get("path_params"), dict):
            raise ValueError("targeted market path parameters required")
        value = request.get("path_params", {}).get("id")
        if self.source_id != "gamma.market" or request != self.request({"market_id": value}):
            raise ValueError("targeted market request differs from pinned contract")
        return value


SOURCES = {
    source.source_id: source
    for source in (
        SourceContract(
            "gamma.market", "https://gamma-api.polymarket.com/markets/{id}",
            "https://docs.polymarket.com/api-reference/markets/get-market-by-id", "gamma-by-id",
            "gamma-market-identity-v1", "metadata clocks are not first receipt or lifecycle time",
            "one exact decimal market ID; ordered outcomes/tokens; nullable lifecycle flags",
        ),
        SourceContract(
            "gamma.markets", "https://gamma-api.polymarket.com/markets",
            "https://docs.polymarket.com/api-reference/markets/list-markets", "gamma",
            "gamma-identity-v1", "createdAt/updatedAt are metadata clocks, not first receipt",
            "market/condition IDs; ordered string outcome/token arrays; source-native decimals",
        ),
        SourceContract(
            "gamma.markets.keyset", "https://gamma-api.polymarket.com/markets/keyset",
            "https://docs.polymarket.com/api-reference/markets/list-markets-keyset-pagination",
            "gamma-keyset", "gamma-keyset-frame-v1",
            "metadata clocks are not first receipt; enumeration spans an interval",
            "markets array with exact native values; opaque next_cursor omitted on last page",
        ),
        SourceContract(
            "clob.book", "https://clob.polymarket.com/book",
            "https://docs.polymarket.com/api-reference/market-data/get-order-book", "clob",
            "clob-book-v1", "snapshot timestamp retained raw; unit admission requires evidence",
            "decimal price and share size strings; asset token and condition IDs",
        ),
        SourceContract(
            "data.v2.trades", "https://data-api.polymarket.com/v2/trades",
            "https://docs.polymarket.com/api-reference/feeds/list-trades", "data-v2",
            "data-v2-trades-v1", "per-trade timestamp retained; retrieval is later knowledge",
            "taker_only=true; native BUY/SELL; exact price/size; tx hash not unique fill ID",
        ),
        SourceContract(
            "coinbase.btc_usd.ticker", "https://api.exchange.coinbase.com/products/BTC-USD/ticker",
            "https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker",
            "exchange-rest", "coinbase-ticker-v1", "time is last trade, not entire snapshot time",
            "BTC-USD; quote USD/base BTC; decimal strings; trade ID",
        ),
        SourceContract(
            "clob.market_stream", "wss://ws-subscriptions-clob.polymarket.com/ws/market",
            "https://docs.polymarket.com/api-reference/wss/market", "clob-market-channel",
            "clob-stream-diagnostic-v1", "raw message clocks retained; no native sequence proof",
            "BUY=bid and SELL=ask price-level changes; decimal strings; zero removes level",
        ),
    )
}
