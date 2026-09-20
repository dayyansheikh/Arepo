"""Pinned read-only probe contracts. No application settings or implicit network work."""

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
        if self.source_id == "gamma.markets":
            allowed = {"limit", "active", "closed"}
            if values.get("active") != "true" or values.get("closed") != "false":
                raise ValueError("diagnostic Gamma query requires explicit active/open filter")
        elif self.source_id == "data.v2.trades":
            allowed = {"limit", "condition", "taker_only", "cursor"}
            if values.get("taker_only") != "true":
                raise ValueError("diagnostic trades require explicit taker-only semantics")
            if "condition" in values:
                import re

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
            if type(limit) is not int or not 1 <= limit <= 10:
                raise ValueError("probe limit must be an integer in 1..10")
        return dict(values)


SOURCES = {
    source.source_id: source
    for source in (
        SourceContract(
            "gamma.markets", "https://gamma-api.polymarket.com/markets",
            "https://docs.polymarket.com/api-reference/markets/list-markets", "gamma",
            "gamma-identity-v1", "createdAt/updatedAt are metadata clocks, not first receipt",
            "market/condition IDs; ordered string outcome/token arrays; source-native decimals",
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
    )
}
