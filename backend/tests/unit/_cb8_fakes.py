# ruff: noqa: E501
"""Shared fakes for the CB8 tests: a mocked Gamma / Data API transport, capture directories and a wallet key. No network."""

from __future__ import annotations

import csv
import gzip
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from astrolabe.research_lab import cb8_common as cm

T0 = datetime(2026, 10, 21, 12, tzinfo=UTC).timestamp()
HOUR = 3600.0
RAW_PREFIX = "0xRAWWALLET"


def make_key(tmp_path: Path, content: bytes = b"k" * 64, mode: int = 0o600) -> Path:
    p = tmp_path / "keydir" / "wallet_hash_key"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    os.chmod(p, mode)
    return p


class Clock:
    def __init__(self, t: float) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def nosleep(_s: float) -> None:
    return None


class Api:
    """Transport ``(url, params) -> (status, body, headers)`` for /holders, /trades and Gamma /markets."""

    def __init__(self) -> None:
        self.holders: dict[str, list] = {}
        self.trades: dict[str, list[dict]] = {}
        self.gamma: dict[str, dict] = {}
        self.fail_holders: set[str] = set()
        self.fail_trades: set[str] = set()
        self.fail_all = False
        self.max_offset: int | None = None  # the venue's offset cap: a larger offset answers 400
        self.deep_status: int | None = None  # forced status for offset >= 4000
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, params: dict):
        self.calls.append((url, dict(params)))
        if self.fail_all:
            return 500, b"", {}
        if url.endswith("/holders"):
            cid = params["market"]
            if cid in self.fail_holders:
                return 500, b"", {}
            return 200, json.dumps(self.holders.get(cid, [])).encode(), {}
        if url.endswith("/trades"):
            cid = params["market"]
            if cid in self.fail_trades:
                return 500, b"", {}
            off = int(params.get("offset", 0))
            if self.max_offset is not None and off > self.max_offset:
                return 400, b"", {}
            if self.deep_status is not None and off >= 4000:
                return self.deep_status, b"", {}
            rows = sorted((r for r in self.trades.get(cid, []) if params["start"] <= r["timestamp"] <= params["end"]), key=lambda r: -r["timestamp"])
            o, n = int(params.get("offset", 0)), int(params["limit"])
            return 200, json.dumps(rows[o:o + n]).encode(), {}
        if url.endswith("/markets"):
            if "id" in params:
                ids = params["id"] if isinstance(params["id"], list) else [params["id"]]
                return 200, json.dumps([self.gamma[i] for i in ids if i in self.gamma]).encode(), {}
            lo = datetime.strptime(params["end_date_min"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()
            hi = datetime.strptime(params["end_date_max"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()
            rows = [m for m in self.gamma.values() if lo <= datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp() < hi and m.get("closed")]
            o, n = int(params.get("offset", 0)), int(params.get("limit", 100))
            return 200, json.dumps(rows[o:o + n]).encode(), {}
        return 404, b"", {}


def holder_groups(cid: str, n: int = 4, top: float = 100.0) -> list[dict]:
    out = []
    for idx in (0, 1):
        hs = [{"proxyWallet": f"{RAW_PREFIX}_{cid}_{idx}_{k}", "amount": top / (k + 1) / (idx + 1), "outcomeIndex": idx} for k in range(n)]
        out.append({"token": f"tok{cid}{idx}", "holders": hs})
    return out


def print_row(cid: str, ts: int, *, idx: int = 0, side: str = "SELL", price: float = 0.4, size: float = 10.0, wallet: str | None = None, tx: str = "") -> dict:
    return {"timestamp": int(ts), "side": side, "size": size, "price": price, "outcomeIndex": idx, "proxyWallet": wallet or f"{RAW_PREFIX}_x_{ts}",
            "transactionHash": tx or f"tx{cid}{ts}{idx}{side}"}


def cap_row(i: int, *, sports: bool = False, oi: float = 5000.0, bid: str = "0.40", ask: str = "0.44", updown: bool = False, accepting: str = "1") -> dict:
    return {"market_id": f"m{i}", "condition_id": f"c{i}", "event_id": f"e{i // 2}", "binary": "1", "closed": "0", "best_bid": bid, "best_ask": ask,
            "received_utc": "2026-10-21T14:00:00Z", "accepting_orders": accepting, "open_interest": str(oi + i), "fee_category": "sports" if sports else "politics",
            "series_slugs": "btc-up-or-down-daily" if updown else "series"}


def write_capture(d: Path, rows: list[dict]) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    rc = ["market_id", "condition_id", "event_id", "binary", "closed", "best_bid", "best_ask", "received_utc"]
    ec = ["market_id", "accepting_orders", "open_interest", "fee_category", "series_slugs"]
    for name, cols in (("rows.csv.gz", rc), ("rows_ext.csv.gz", ec)):
        with gzip.open(d / name, "wt", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return d


def capture(d: Path, start: float, finish: float, rows: list[dict], cid: str | None = None) -> dict:
    write_capture(d, rows)
    return {"capture_id": cid or d.name, "dir": str(d), "start": start, "finish": finish}


def write_smoke(path: Path, rules_sha: str, fp: str, ok: bool = True, paging: bool = True) -> None:
    from astrolabe.research_lab import cb8_holders as h

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"smoke_version": h.SMOKE_VERSION, "rules_sha256": rules_sha, "wallet_key_fingerprint": fp, "pass": ok, "criterion_g_paging": paging}))


def fingerprint_and_sha(kind: str, key: bytes) -> tuple[str, str]:
    fp = cm.key_fingerprint(key)
    return cm.rules_file_doc(kind, fp)["rules_sha256"], fp


def all_bytes(root: Path) -> bytes:
    """Concatenated, gunzipped content of every file under ``root`` (for 'no raw wallet anywhere' checks)."""
    out = b""
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            try:
                b = gzip.decompress(b)
            except (OSError, EOFError):
                pass
            out += b
    return out
