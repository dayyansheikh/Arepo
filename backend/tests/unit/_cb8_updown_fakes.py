# ruff: noqa: E501
"""Shared fakes for the CB8-B tests: Up/Down Gamma markets, Binance monthly archives (zip + CHECKSUM), pmxt hourly parquet files. No network."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq

from astrolabe.research_lab import cb8_updown as u

SETTLE_MARK = 777.0  # the settlement candle's close in the fake archives (a recognisable marker for the guard tests)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mon(day: str) -> str:
    return datetime.strptime(day, "%Y-%m-%d").strftime("%b %d '%y").replace(" 0", " ")


def description(day: str, sym: str = "BTC", *, strike_day: str | None = None, up_word: str = "lower", down_word: str = "higher", drop_clause: bool = False) -> str:
    sd = strike_day or (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    a, b = _mon(sd), _mon(day)
    head = "This market resolves using Binance. The 1 minute candle at 12:00 ET (noon) is used. "
    if drop_clause:
        return head + "In the case of a 50-50 the market resolves 50-50."
    return (head + f'This market will resolve to "Up" if the "Close" price for the Binance 1 minute candle for {sym}/USDT {a} 12:00 in the ET timezone (noon) is {up_word} than the final "Close" price for the {b} 12:00 ET candle. '
            f'This market will resolve to "Down" if the "Close" price for the Binance 1 minute candle for {sym}/USDT {a} 12:00 in the ET timezone (noon) is {down_word} than the final "Close" price for the {b} 12:00 ET candle. '
            "In the case of a 50-50 the market resolves 50-50.")


def updown_market(mid: int, asset: str, day: str, *, end_off_s: int = 0, event: str | None = None, neg: str = "", series: tuple = (), outcome_prices: str = '["1","0"]', **over) -> dict:
    sym, venue = u.ASSETS[asset]
    month = datetime.strptime(day, "%Y-%m-%d").strftime("%B")
    end = u.t_end(day) + end_off_s
    src = f"https://www.binance.com/en/trade/{sym}_USDT" if venue == "spot" else f"https://www.binance.com/en/futures/{sym}USDT"
    m = {"id": str(mid), "conditionId": f"0xcond{mid}", "clobTokenIds": json.dumps([f"tokUp{mid}", f"tokDown{mid}"]), "createdAt": iso(end - 86400 * 2), "startDate": iso(end - 86400 * 2),
         "endDate": iso(end), "closed": True, "closedTime": iso(end + 300), "question": f"{asset} Up or Down on {month} {int(day[-2:])}?", "slug": f"{asset.lower()}-up-or-down-{day}",
         "feeType": "crypto_fees", "outcomes": '["Up","Down"]', "outcomePrices": outcome_prices, "umaResolutionStatus": "resolved", "volumeNum": 1000.0, "liquidityNum": 10.0,
         "negRisk": bool(neg), "negRiskMarketID": neg or None, "resolutionSource": src, "description": description(day, sym),
         "events": [{"id": str(event if event is not None else f"EV{mid}"), "title": f"{asset} {day}", "series": [{"id": str(s)} for s in series], "tags": []}]}
    m.update(over)
    return m


# ---- Binance archives ------------------------------------------------------------------------------------------------------------------------------------


def fake_close(sym: str, open_ms: int, day: str | None = None) -> float:
    """A smooth deterministic price path; the candle opening at t_end carries the SETTLE_MARK."""
    base = {"BTC": 60000.0, "ETH": 3000.0, "SOL": 150.0, "XRP": 0.5, "DOGE": 0.15, "BNB": 600.0, "HYPE": 30.0}[sym]
    return base * (1.0 + 0.0001 * ((open_ms // 60000) % 17))


def archive_zip(sym: str, venue: str, yyyymm: str, days: list[str]) -> bytes:
    """A monthly 1m archive that holds, per day, the minutes [t_end - 80 min, t_end + 2 min) (enough for the B features, the strike and the settlement candle)."""
    rows = []
    if venue == "um":
        rows.append("open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore")
    for d in days:
        if not d.startswith(yyyymm):
            continue
        te = int(u.t_end(d) * 1000)
        for o in range(te - 80 * 60000, te + 2 * 60000, 60000):
            c = SETTLE_MARK if o == te else fake_close(sym, o)
            rows.append(f"{o * 1000 if venue == 'spot' else o},{c},{c},{c},{c},1.0,{o + 59999},1.0,1,1.0,1.0,0")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(zipfile.ZipInfo(f"{sym}USDT-1m-{yyyymm}.csv", date_time=(2026, 1, 1, 0, 0, 0)), "\n".join(rows) + "\n")  # fixed header time: the bytes are reproducible
    return buf.getvalue()


class BinanceFake:
    """``blob_get(url) -> (status, bytes)`` for ``data.binance.vision`` archives and their ``.CHECKSUM`` files."""

    def __init__(self, days: list[str]) -> None:
        self.days = days
        self.calls: list[str] = []
        self.corrupt: set[str] = set()  # archive names whose checksum is wrong
        self.missing: set[str] = set()
        self.fail: set[str] = set()  # archive names answering 503

    def __call__(self, url: str):
        self.calls.append(url)
        checksum = url.endswith(".CHECKSUM")
        name = url.rsplit("/", 1)[1].removesuffix(".CHECKSUM")
        if name in self.missing:
            return 404, b""
        if name in self.fail:
            return 503, b""
        m = re.match(r"([A-Z]+)USDT-1m-(\d{4}-\d{2})\.zip", name)
        sym, ym = m.group(1), m.group(2)
        venue = "um" if "/futures/um/" in url else "spot"
        z = archive_zip(sym, venue, ym, self.days)
        if checksum:
            sha = hashlib.sha256(z).hexdigest()
            if name in self.corrupt:
                sha = "0" * 64
            return 200, f"{sha}  {name}\n".encode()
        return 200, z


# ---- pmxt parquet ------------------------------------------------------------------------------------------------------------------------------------------


def ev(market: str, asset: str, et: str, v_ms: int, r_ms: int | None = None, *, bids=None, asks=None, price=None, size=None, side=None, tick=None, fee=None) -> dict:
    return {"timestamp_received": r_ms if r_ms is not None else v_ms + 5, "timestamp": v_ms, "market": market, "event_type": et, "asset_id": asset,
            "bids": json.dumps(bids) if bids is not None else None, "asks": json.dumps(asks) if asks is not None else None, "price": price, "size": size, "side": side,
            "new_tick_size": tick, "fee_rate_bps": fee}


COLS = ["timestamp_received", "timestamp", "market", "event_type", "asset_id", "bids", "asks", "price", "size", "side", "new_tick_size", "fee_rate_bps"]


def parquet_bytes(events: list[dict], row_group_size: int = 4) -> bytes:
    events = sorted(events, key=lambda e: e["market"])
    ts = pa.timestamp("ms", "UTC")
    cols = {
        "timestamp_received": pa.array([e["timestamp_received"] for e in events], type=ts), "timestamp": pa.array([e["timestamp"] for e in events], type=ts),
        "market": pa.array([e["market"] for e in events], type=pa.string()), "event_type": pa.array([e["event_type"] for e in events], type=pa.string()),
        "asset_id": pa.array([e["asset_id"] for e in events], type=pa.string()), "bids": pa.array([e["bids"] for e in events], type=pa.string()),
        "asks": pa.array([e["asks"] for e in events], type=pa.string()), "price": pa.array([e["price"] for e in events], type=pa.float64()),
        "size": pa.array([e["size"] for e in events], type=pa.float64()), "side": pa.array([e["side"] for e in events], type=pa.string()),
        "new_tick_size": pa.array([e["new_tick_size"] for e in events], type=pa.string()), "fee_rate_bps": pa.array([e["fee_rate_bps"] for e in events], type=pa.float64()),
    }
    buf = io.BytesIO()
    pq.write_table(pa.table(cols), buf, row_group_size=row_group_size)
    return buf.getvalue()


class PmxtFake:
    """``fetch(url, a, b)`` and ``size_fn(url)`` over in-memory hourly files keyed by ``YYYY-MM-DDTHH``. Counts the bytes served."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.corrupt: set[str] = set()
        self.served = 0
        self.sizes: list[str] = []

    @staticmethod
    def key(url: str) -> str:
        return re.search(r"orderbook_(\d{4}-\d{2}-\d{2}T\d{2})\.parquet", url).group(1)

    def size_fn(self, url: str) -> int:
        k = self.key(url)
        self.sizes.append(k)
        if k not in self.files:
            raise FileNotFoundError(url)
        return len(self.files[k])

    def fetch(self, url: str, a: int, b: int) -> bytes:
        k = self.key(url)
        data = b"not a parquet file" * 100 if k in self.corrupt else self.files[k]
        out = data[a:b + 1]
        self.served += len(out)
        return out

    def add_day(self, day: str, markets: list[dict], *, up_ask: float = 0.95, down_ask: float = 0.06, hour: int = 15, skip: set[str] | None = None) -> None:
        """One hour file for ``hour``Z of ``day`` with a book event at the hour's start and a price_change near the checkpoints for every market."""
        evs: list[dict] = []
        h0 = int(datetime(*datetime.strptime(day, "%Y-%m-%d").timetuple()[:3], hour, tzinfo=UTC).timestamp() * 1000)
        for m in markets:
            if skip and m["market_id"] in skip:
                continue
            for tok, ask, bid in ((m["token_up"], up_ask, up_ask - 0.02), (m["token_down"], down_ask, down_ask - 0.02)):
                evs.append(ev(m["condition_id"], tok, "book", h0 + 1000, bids=[[str(round(bid, 2)), "100"]], asks=[[str(ask), "50"], [str(round(ask + 0.01, 2)), "80"]], fee=700))
                evs.append(ev(m["condition_id"], tok, "price_change", h0 + 40 * 60000, price=ask, size=60.0, side="SELL", fee=700))
        if evs:
            self.files[f"{day}T{hour:02d}"] = parquet_bytes(evs)
