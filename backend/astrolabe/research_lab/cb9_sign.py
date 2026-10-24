# ruff: noqa: E501
"""CB9-S: trade-direction truth audit (docs/research_lab/CREATIVE_BATCH_9.md CB9-S, 1.4, 2.7 S0, CB9-F q0180/q0181/q0188/q0190/q0193/q0194).

Keyless Polygon JSON-RPC client (pinned endpoint order, <= 2 rps, every endpoint tried twice before a receipt is "unavailable"), a local
Keccak-256 (topic pins are checked against it, never trusted blindly), the receipt decoder for both exchange eras, the match rule, the
truth rules T1 (event-declared) and T2 (ERC-1155 asset flow), the fill types, the S0 strata samples (a: v2 era Oct 2026; c: v1 era
Feb-Apr 2026; b: K/D SCREEN prints), the census counts (field-restricted: no truth side, no agreement), the per-stratum verdict with the
era map, ``q_LB`` = min(market-cluster bootstrap 0.5th percentile, market-level Wilson 99%), the notional-weighted agreement, and the
conditional S1 (h10_sign fetch; ratio rule with the one-sided 99% lower bound > 1.5, ``beta_api <= 0`` draws count as failures).

Raw wallet addresses exist only in memory: the print's ``proxyWallet`` and the receipt's ``takerOrderMaker`` are compared through the
strict-loaded HMAC (identical hash = identical lower-cased address). No price, mark or outcome is stored with the S0 classes except the
declared ``notional`` weight (size x price) and a price-band label. EXPLORATORY / METHODS only; no edge claim.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import history_backfill as hb

Refused = c9.Refused
NotNow = c9.NotNow

# ---- pins (CREATIVE_BATCH_9.md CB9-S "On-chain truth"; re-verified against the code's keccak at every rules build) -------------------

ENDPOINTS = ("https://polygon.drpc.org", "https://1rpc.io/matic", "https://polygon-bor-rpc.publicnode.com")  # pinned order (2.8)
RPC_RPS = 2.0
RPC_ATTEMPTS_PER_ENDPOINT = 2
AMOUNT_DECIMALS = 6  # USDC.e and CTF position amounts both carry 6 decimals
SIZE_TOL = 1e-6

# Polymarket contracts (Polygon). v1 addresses from Polymarket's published contracts list (CTF Exchange, Neg-Risk CTF Exchange, Neg-Risk
# Adapter, Conditional Tokens); v2 exchange addresses from the probe observations (section 0.3, probes 2-3). OPEN ITEM for the freeze check:
# re-verify every address against the published list before the rules file is committed (no network in this session).
CTF = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
EXCHANGES_V1 = ("0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e", "0xc5d563a36ae78145c45a50134d48a1215220f80a")
EXCHANGES_V2 = ("0xe111180000d2663c0091e4f400237545b87b996b", "0xe2222d279d744050d28e00520010520000310f59")
NEG_RISK_ADAPTER = "0xd91e80cf2e7be2e162c6513ced06f1dd0da35296"
ZERO_ADDR = "0x" + "0" * 40

SIG = {
    "v1_order_filled": "OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)",
    "v1_orders_matched": "OrdersMatched(bytes32,address,uint256,uint256,uint256,uint256)",
    "v2_order_filled": "OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)",
    "v2_orders_matched": "OrdersMatched(bytes32,address,uint8,uint256,uint256,uint256)",
    "v2_fee_charged": "FeeCharged(address,uint256)",
    "transfer_single": "TransferSingle(address,address,address,uint256,uint256)",
    "transfer_batch": "TransferBatch(address,address,address,uint256[],uint256[])",
    "position_split": "PositionSplit(address,address,bytes32,bytes32,uint256[],uint256)",
    "positions_merge": "PositionsMerge(address,address,bytes32,bytes32,uint256[],uint256)",
}
# Full topic hashes stated in the design (v1 / v2 OrderFilled and OrdersMatched); the others are computed by the local keccak and
# recorded in the rules file. ``topic_pins_ok()`` must hold before any receipt is classified.
PINNED_TOPICS = {
    "v1_order_filled": "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6",
    "v1_orders_matched": "0x63bf4d16b7fa898ef4c4b2b6d90fd201e9c56313b65638af6088d149d2ce956c",
    "v2_order_filled": "0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee",
    "v2_orders_matched": "0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c",
}
PINNED_TOPIC_PREFIXES = {"v2_fee_charged": "0x55bb3cad"}  # the design states only the prefix
# Parameter layouts (names; leading parameters are the indexed ones, their number = len(topics) - 1, checked against the data length).
PARAMS = {
    "v1_order_filled": (("orderHash", "bytes32"), ("maker", "address"), ("taker", "address"), ("makerAssetId", "uint256"), ("takerAssetId", "uint256"),
                        ("makerAmountFilled", "uint256"), ("takerAmountFilled", "uint256"), ("fee", "uint256")),
    "v1_orders_matched": (("takerOrderHash", "bytes32"), ("takerOrderMaker", "address"), ("makerAssetId", "uint256"), ("takerAssetId", "uint256"),
                          ("makerAmountFilled", "uint256"), ("takerAmountFilled", "uint256")),
    "v2_order_filled": (("orderHash", "bytes32"), ("maker", "address"), ("taker", "address"), ("side", "uint8"), ("tokenId", "uint256"),
                        ("makerAmountFilled", "uint256"), ("takerAmountFilled", "uint256"), ("fee", "uint256"), ("b1", "bytes32"), ("b2", "bytes32")),
    "v2_orders_matched": (("takerOrderHash", "bytes32"), ("takerOrderMaker", "address"), ("side", "uint8"), ("tokenId", "uint256"),
                          ("makerAmountFilled", "uint256"), ("takerAmountFilled", "uint256")),
    "transfer_single": (("operator", "address"), ("from", "address"), ("to", "address"), ("id", "uint256"), ("value", "uint256")),
}
# v2 ``Side`` enum (the v1 ``Order.side`` enum carried into the v2 source: BUY = 0, SELL = 1). OPEN ITEM: confirm against the published v2
# source before the rules file is committed; the q0180 smoke (T1 = T2 on >= 18 of 20 v2 receipts) fails if the mapping is wrong.
SIDE_ENUM_V2 = {0: "BUY", 1: "SELL"}
# v2 share amount: a BUY taker order gives collateral (maker amount) and receives shares (taker amount); a SELL gives shares. Same as v1.

# ---- samples (fixed now) ---------------------------------------------------------------------------------------------------------------

SEEDS = {"a": "arepo-cb9-s0a", "b": "arepo-cb9-s0b", "c": "arepo-cb9-s0c"}
STRATA = ("a", "b", "c")
WINDOWS = {"a": ("2026-10-01", "2026-10-15"), "c": ("2026-02-01", "2026-04-27")}
N_MARKETS = 250
PRINTS_PER_MARKET = 4
MAX_PER_EVENT = 3
S0_MIN_VOLUME = 1000.0
S0_PAGES = 5
PRINT_LIMIT = 1000
N_PRINTS_TARGET = 1000
FRAME_END_FAR = "2100-01-01"
FRAME_SPLIT_DAYS = 7
FRAME_MIN_WINDOW_S = 3600.0
PRICE_BANDS = ((0.0, 0.10, "<0.10"), (0.10, 0.30, "0.10-0.30"), (0.30, 0.70, "0.30-0.70"), (0.70, 0.90, "0.70-0.90"), (0.90, 1.0000001, ">=0.90"))
ERA_MAP = {"a": {"era": "v2 exchange, [2026-10-01, 2026-10-15)", "informs": ["E007"]},
           "b": {"era": "v2 exchange, pmxt window May-Aug 2026", "informs": ["HB1", "HB2 (incl. HB2-R F4/F5)", "CB9-K"]},
           "c": {"era": "v1 exchange, [2026-02-01, 2026-04-27)", "informs": []}}

# ---- gates and decision bands (S0) -------------------------------------------------------------------------------------------------

GS_MATCH_RATE = 0.90
GS_MIN_MATCHED = 300
SOURCE_GATE_T1T2 = 0.99
NEAR_TRUTH_Q, NEAR_TRUTH_LB = 0.97, 0.95
MINOR_Q, MINOR_QWC = 0.90, 0.85
LB_PERCENTILE = 0.5
WILSON_CONF = 0.99

# ---- smoke (q0180, receipt part) ----------------------------------------------------------------------------------------------------

SMOKE_VERSION = "cb9-smoke-v2"  # v2 (2026-10-17): markets drawn in seeded order until 20 distinct receipts (cap 40 markets); pass rule unchanged. v1 FAILED on the 10-market cap (source worked) and is superseded by disclosure
SMOKE_RECEIPTS_PER_ERA = 20
SMOKE_MIN_DECODED = 18
SMOKE_ERA_DAYS = {"v1": "2026-01-20", "v2": "2026-09-15"}  # Gamma: closed markets ending that UTC day; prints from the 3 days before; outside every CB9 window
SMOKE_MAX_MARKETS_PER_ERA = 40  # v2: markets are drawn one at a time until SMOKE_RECEIPTS_PER_ERA distinct receipts; v1 used a fixed 10
SMOKE_PRINTS_PER_MARKET = 2
SMOKE_MIN_VOLUME = 10000.0
SMOKE_SEED = "arepo-cb9-smoke-v2"
SMOKE_MAX_UNAVAILABLE = 2  # M2: more unavailable receipts in an era -> NotNow (exit 75, nothing written), never a permanent FAIL

# ---- S1 (conditional) -----------------------------------------------------------------------------------------------------------------

H10_N_MARKETS = 1200
H10_WINDOW_H = 72
H10_MAX_RECEIPT_PRINTS = 20000
H10_SEED = "arepo-cb9-h10"
H10_ERA = {"v2": ("2026-05-01", "2026-10-01"), "v1": ("2026-02-01", "2026-04-27")}
H10_PAGES = 20
S1_ORIGIN_STEP_H = 2
S1_FEATURE_H = 6
S1_MIN_PRINTS = 3
S1_TARGET_H = 6
S1_ANCHOR_TOL_S = 1800
S1_RATIO = 1.5
S1_LB_PERCENTILE = 1.0

PRINT_COLUMNS = ["stratum", "market_id", "event_id", "tx", "asset", "api_side", "api_idx", "size", "notional", "price_band", "liq_tercile", "sports",
                 "era", "receipt_status", "endpoint", "match_status", "n_candidates", "t1_available", "t2_available", "t2_status", "t1_side", "t1_idx",
                 "t2_side", "t2_idx", "fill_type", "wallet_hash", "feed_side"]
# The census never receives a truth side, an API side or a weight: these columns are forbidden on every census path.
CENSUS_COLUMNS_S = ("stratum", "market_id", "era", "receipt_status", "endpoint", "match_status", "t1_available", "t2_available", "t2_status", "fill_type", "sports")
CENSUS_FORBIDDEN_S = ("api_side", "api_idx", "t1_side", "t1_idx", "t2_side", "t2_idx", "feed_side", "notional", "size", "price_band")


# =====================================================================================================================================
# Keccak-256 (local; Ethereum padding 0x01, not SHA3's 0x06)
# =====================================================================================================================================

_RC = (0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
       0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
       0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
       0x000000000000800A, 0x800000008000000A, 0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008)
_ROT = ((0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61), (28, 55, 25, 21, 56), (27, 20, 39, 8, 14))
_M64 = (1 << 64) - 1


def _keccak_f(a: list[list[int]]) -> None:
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ (((c[(x + 1) % 5] << 1) | (c[(x + 1) % 5] >> 63)) & _M64) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                r = _ROT[x][y]
                v = a[x][y]
                b[y][(2 * x + 3 * y) % 5] = ((v << r) | (v >> (64 - r))) & _M64 if r else v
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y] & _M64)
        a[0][0] ^= rc


def keccak256(data: bytes) -> bytes:
    rate = 136
    msg = bytearray(data)
    msg.append(0x01)
    while len(msg) % rate:
        msg.append(0)
    msg[-1] |= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        blk = msg[off:off + rate]
        for i in range(rate // 8):
            a[i % 5][i // 5] ^= int.from_bytes(blk[8 * i:8 * i + 8], "little")
        _keccak_f(a)
    return b"".join(a[i % 5][i // 5].to_bytes(8, "little") for i in range(4))


def topic(signature: str) -> str:
    return "0x" + keccak256(signature.encode()).hex()


def topics() -> dict[str, str]:
    """Every event topic computed by the local keccak."""
    return {k: topic(v) for k, v in SIG.items()}


def topic_pins_ok() -> dict:
    """The design's pinned topics must equal the local keccak of the pinned signatures (refusal otherwise)."""
    t = topics()
    full = {k: t[k] == v for k, v in PINNED_TOPICS.items()}
    pref = {k: t[k].startswith(v) for k, v in PINNED_TOPIC_PREFIXES.items()}
    return {"ok": all(full.values()) and all(pref.values()), "full": full, "prefix": pref}


def require_topic_pins() -> dict[str, str]:
    chk = topic_pins_ok()
    if not chk["ok"]:
        raise Refused(f"pinned topic hashes differ from the local keccak: {chk}")
    return topics()


# =====================================================================================================================================
# JSON-RPC client (keyless; pinned endpoints; <= 2 rps)
# =====================================================================================================================================

Post = Callable[[str, dict], tuple[int, bytes]]


def httpx_post(timeout: float = 30.0) -> Post:
    """``(status, body)`` of a keyless JSON-RPC POST. A transport error returns status 599 (the client retries / falls back)."""
    import httpx  # noqa: PLC0415

    client = httpx.Client(timeout=timeout, headers={"User-Agent": "arepo-research-lab/1", "Content-Type": "application/json"})

    def post(url: str, payload: dict) -> tuple[int, bytes]:
        try:
            r = client.post(url, json=payload)
        except httpx.HTTPError:
            return 599, b""
        return r.status_code, r.content

    return post


class RpcClient:
    """``eth_getTransactionReceipt`` over the pinned endpoint list in order; each endpoint is tried ``RPC_ATTEMPTS_PER_ENDPOINT`` times (HTTP
    status other than 200, an RPC error, an unparseable body or a null result are failures); after every endpoint failed that often the receipt
    is "unavailable" (counted, never repaired). One global pacing clock (<= ``rps``) across endpoints; yields to the live collector."""

    def __init__(self, post: Post, *, rps: float = RPC_RPS, endpoints: tuple[str, ...] = ENDPOINTS, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, live_check: Callable[[], bool] | None = None) -> None:
        if rps > RPC_RPS:
            raise Refused(f"Polygon RPC pacing {rps} rps exceeds the declared {RPC_RPS} rps")
        self.post, self.min_gap, self.endpoints = post, 1.0 / rps, tuple(endpoints)
        self.sleep, self.clock, self.live_check = sleep, clock, live_check
        self.last, self._last_live = -1e9, -1e9
        self.requests = 0
        self.yielded_s = 0.0
        self.failures: dict[str, int] = dict.fromkeys(self.endpoints, 0)
        self.served: dict[str, int] = dict.fromkeys(self.endpoints, 0)
        self.n_unavailable = 0

    def _pace(self) -> None:
        if self.live_check is not None and self.clock() - self._last_live >= 2.0:
            self.yielded_s += hb.yield_to_live(self.live_check, self.sleep)
            self._last_live = self.clock()
        wait = self.min_gap - (self.clock() - self.last)
        if wait > 0:
            self.sleep(wait)
        self.last = self.clock()

    def receipt(self, tx: str) -> tuple[dict | None, str]:
        """(receipt or None, endpoint that served it or "unavailable")."""
        payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionReceipt", "params": [tx]}
        for ep in self.endpoints:
            for _ in range(RPC_ATTEMPTS_PER_ENDPOINT):
                self._pace()
                self.requests += 1
                status, body = self.post(ep, payload)
                res = None
                if status == 200:
                    try:
                        doc = json.loads(body)
                        res = doc.get("result") if isinstance(doc, dict) and "error" not in doc else None
                    except ValueError:
                        res = None
                if isinstance(res, dict) and isinstance(res.get("logs"), list):
                    self.served[ep] += 1
                    return res, ep
                self.failures[ep] += 1
        self.n_unavailable += 1
        return None, "unavailable"

    def stats(self) -> dict:
        return {"requests": self.requests, "failures_by_endpoint": dict(self.failures), "served_by_endpoint": dict(self.served),
                "unavailable": self.n_unavailable, "yielded_to_live_s": self.yielded_s}


# =====================================================================================================================================
# Receipt decoder
# =====================================================================================================================================


def _words(data: str) -> list[str]:
    h = (data or "0x")[2:] if str(data or "").startswith("0x") else str(data or "")
    if len(h) % 64:
        raise ValueError("data length is not a multiple of 32 bytes")
    return [h[i:i + 64] for i in range(0, len(h), 64)]


def _val(word: str, typ: str):
    w = word[-64:].rjust(64, "0")
    if typ == "address":
        return "0x" + w[-40:].lower()
    if typ == "bytes32":
        return "0x" + w.lower()
    return int(w, 16)


def decode_static(kind: str, log: dict) -> dict | None:
    """Decode a log of a pinned static layout: the leading ``len(topics) - 1`` parameters are indexed (from topics), the rest come from the data
    words; ``None`` if the data length does not equal the number of non-indexed parameters (an undecodable log, counted)."""
    params = PARAMS[kind]
    tps = [str(t) for t in log.get("topics") or []]
    k = len(tps) - 1
    if k < 0 or k > len(params):
        return None
    try:
        ws = _words(log.get("data") or "0x")
    except ValueError:
        return None
    if len(ws) != len(params) - k:
        return None
    out = {}
    for i, (name, typ) in enumerate(params):
        out[name] = _val(tps[1 + i][2:], typ) if i < k else _val(ws[i - k], typ)
    return out


def decode_transfer_batch(log: dict) -> list[tuple[str, str, int, int]] | None:
    """``[(from, to, id, value)]`` of an ERC-1155 TransferBatch (operator, from, to indexed; dynamic ``ids`` / ``values`` arrays in data)."""
    tps = [str(t) for t in log.get("topics") or []]
    if len(tps) != 4:
        return None
    try:
        ws = _words(log.get("data") or "0x")
        o_ids, o_vals = int(ws[0], 16) // 32, int(ws[1], 16) // 32
        n_ids, n_vals = int(ws[o_ids], 16), int(ws[o_vals], 16)
        ids = [int(ws[o_ids + 1 + i], 16) for i in range(n_ids)]
        vals = [int(ws[o_vals + 1 + i], 16) for i in range(n_vals)]
    except (ValueError, IndexError):
        return None
    if len(ids) != len(vals):
        return None
    frm, to = _val(tps[2][2:], "address"), _val(tps[3][2:], "address")
    return [(frm, to, i, v) for i, v in zip(ids, vals, strict=True)]


def _side_token_v1(d: dict) -> tuple[str, int, float]:
    """v1 order perspective: maker asset 0 (collateral) -> BUY of the taker asset (shares = taker amount); else SELL of the maker asset."""
    if int(d["makerAssetId"]) == 0:
        return "BUY", int(d["takerAssetId"]), d["takerAmountFilled"] / 10**AMOUNT_DECIMALS
    return "SELL", int(d["makerAssetId"]), d["makerAmountFilled"] / 10**AMOUNT_DECIMALS


def _side_token_v2(d: dict) -> tuple[str, int, float] | None:
    side = SIDE_ENUM_V2.get(int(d["side"]))
    if side is None:
        return None
    shares = (d["takerAmountFilled"] if side == "BUY" else d["makerAmountFilled"]) / 10**AMOUNT_DECIMALS
    return side, int(d["tokenId"]), shares


def decode_receipt(receipt: dict, tps: dict[str, str] | None = None) -> dict:
    """Pinned-topic, pinned-address decode. Returns ``matches`` (OrdersMatched: log index, era, taker address, side, token, shares), ``fills``
    (OrderFilled: log index, era, maker, side, token, shares), ``transfers`` ((from, to, id, value) of the CTF contract), ``splits`` /
    ``merges`` (log indices of CTF PositionSplit / PositionsMerge) and ``undecodable`` (pinned topic on a pinned address that failed to decode)."""
    tps = tps or topics()
    inv = {v: k for k, v in tps.items()}
    out: dict[str, Any] = {"matches": [], "fills": [], "transfers": [], "splits": [], "merges": [], "undecodable": 0}
    for pos, lg in enumerate(receipt.get("logs") or []):
        t0 = str((lg.get("topics") or [""])[0]).lower()
        addr = str(lg.get("address") or "").lower()
        kind = inv.get(t0)
        if kind is None:
            continue
        li = int(lg["logIndex"], 16) if isinstance(lg.get("logIndex"), str) and str(lg["logIndex"]).startswith("0x") else int(lg.get("logIndex", pos))
        era = "v1" if kind.startswith("v1_") else ("v2" if kind.startswith("v2_") else None)
        if era is not None:
            if addr not in (EXCHANGES_V1 if era == "v1" else EXCHANGES_V2) or kind == "v2_fee_charged":
                continue
            d = decode_static(kind, lg)
            st = None if d is None else (_side_token_v1(d) if era == "v1" else _side_token_v2(d))
            if st is None:
                out["undecodable"] += 1
                continue
            side, token, shares = st
            if kind.endswith("orders_matched"):
                out["matches"].append({"li": li, "era": era, "exchange": addr, "taker": d["takerOrderMaker"], "side": side, "token": token, "shares": shares})
            else:
                out["fills"].append({"li": li, "era": era, "exchange": addr, "maker": d["maker"], "taker": d["taker"], "side": side, "token": token, "shares": shares})
            continue
        if addr != CTF:
            continue
        if kind == "transfer_single":
            d = decode_static("transfer_single", lg)
            if d is None:
                out["undecodable"] += 1
                continue
            out["transfers"].append((li, d["from"], d["to"], int(d["id"]), int(d["value"])))
        elif kind == "transfer_batch":
            rows = decode_transfer_batch(lg)
            if rows is None:
                out["undecodable"] += 1
                continue
            out["transfers"] += [(li, f, t, i, v) for f, t, i, v in rows]
        elif kind == "position_split":
            out["splits"].append(li)
        elif kind == "positions_merge":
            out["merges"].append(li)
    out["matches"].sort(key=lambda m: m["li"])
    out["fills"].sort(key=lambda m: m["li"])
    return out


# =====================================================================================================================================
# Match rule, T1, T2, fill type, YES-terms sign
# =====================================================================================================================================


def match_print(dec: dict, wallet_hash: str, tokens: tuple[int, int], size: float, hash_addr: Callable[[str], str | None]) -> tuple[str, dict | None, int]:
    """The print's OrdersMatched: taker (hashed) = the print's hashed ``proxyWallet`` and token in the market's pair (the print's asset or its
    complement); several -> those whose share amount equals ``size`` within 1e-6; zero or several remaining -> unmatched. Returns
    (status, match, number of first-stage candidates)."""
    cands = [m for m in dec["matches"] if m["token"] in tokens and wallet_hash and hash_addr(m["taker"]) == wallet_hash]
    if len(cands) == 1:
        return "matched", cands[0], 1
    if not cands:
        return "unmatched_none", None, 0
    sized = [m for m in cands if abs(m["shares"] - float(size)) <= SIZE_TOL]
    if len(sized) == 1:
        return "matched", sized[0], len(cands)
    return ("unmatched_ambiguous" if sized else "unmatched_size"), None, len(cands)


def t1_of(match: dict) -> tuple[str, int]:
    """T1 (event-declared): v2 the ``side`` enum and ``tokenId`` of the matched OrdersMatched; v1 BUY of ``takerAssetId`` if ``makerAssetId`` = 0,
    else SELL of ``makerAssetId`` (already resolved by the decoder)."""
    return match["side"], match["token"]


def t2_of(dec: dict, taker: str, tokens: tuple[int, int]) -> tuple[str, tuple[str, int] | None]:
    """T2 (asset flow, independent of the enum): net ERC-1155 flow of the pair's tokens to / from the taker address in the receipt. Exactly one
    token with a non-zero net -> (BUY if received else SELL, token); both -> ``ambiguous``; none -> ``absent``."""
    net = dict.fromkeys(tokens, 0)
    tk = str(taker).lower()
    for _li, frm, to, tid, val in dec["transfers"]:
        if tid not in net or frm == to:
            continue
        if to == tk:
            net[tid] += val
        if frm == tk:
            net[tid] -= val
    nz = [t for t in tokens if net[t] != 0]
    if len(nz) == 1:
        return "ok", ("BUY" if net[nz[0]] > 0 else "SELL", nz[0])
    return ("ambiguous" if nz else "absent"), None


def fill_type(dec: dict, match: dict, tokens: tuple[int, int]) -> str:
    """Fill type of the matched taker order from its own receipt segment (logs after the previous OrdersMatched up to this one): ``normal`` (maker
    fills on the taker's token, opposite side), ``mint`` (complementary BUYs with a PositionSplit), ``merge`` (complementary SELLs with a
    PositionsMerge), ``mixed`` (more than one class) or ``unknown``."""
    prev = max((m["li"] for m in dec["matches"] if m["li"] < match["li"]), default=-1)
    lo, hi = prev, match["li"]
    taker = match["taker"]
    side, tok = match["side"], match["token"]
    comp = tokens[1] if tok == tokens[0] else tokens[0]
    has_split = any(lo < li < hi for li in dec["splits"])
    has_merge = any(lo < li < hi for li in dec["merges"])
    classes = set()
    for f in dec["fills"]:
        if not (lo < f["li"] < hi) or f["maker"] == taker or f["token"] not in tokens:
            continue
        if f["token"] == tok and f["side"] != side:
            classes.add("normal")
        elif f["token"] == comp and f["side"] == side == "BUY" and has_split:
            classes.add("mint")
        elif f["token"] == comp and f["side"] == side == "SELL" and has_merge:
            classes.add("merge")
        else:
            classes.add("other")
    if not classes or classes == {"other"}:
        return "unknown"
    if len(classes - {"other"}) > 1 or "other" in classes:
        return "mixed"
    return next(iter(classes))


def yes_sign(side: str, idx: int) -> int:
    """``+1`` for BUY of outcome 0 or SELL of outcome 1, ``-1`` otherwise (``trade_sample._sign`` convention)."""
    return 1 if (side == "BUY") == (int(idx) == 0) else -1


def price_band(price: float) -> str:
    for lo, hi, lab in PRICE_BANDS:
        if lo <= price < hi:
            return lab
    return "out_of_range"


def classify_print(pr: dict, receipt: dict | None, endpoint: str, tokens: tuple[int, int], hash_addr: Callable[[str], str | None], tps: dict[str, str]) -> dict:
    """One stored S0 row from a print and its receipt (``None`` = unavailable). ``pr`` carries market_id, event_id, tx, asset (int), side, idx,
    size, price, wallet (hash), sports, liq_tercile, stratum and optionally feed_side."""
    row = {"stratum": pr["stratum"], "market_id": pr["market_id"], "event_id": pr.get("event_id", ""), "tx": pr["tx"], "asset": str(pr["asset"]),
           "api_side": pr["side"], "api_idx": int(pr["idx"]), "size": float(pr["size"]), "notional": round(float(pr["size"]) * float(pr["price"]), 6),
           "price_band": price_band(float(pr["price"])), "liq_tercile": pr.get("liq_tercile", ""), "sports": int(bool(pr.get("sports"))),
           "era": "", "receipt_status": "ok" if receipt is not None else "unavailable", "endpoint": endpoint, "match_status": "receipt_unavailable",
           "n_candidates": 0, "t1_available": 0, "t2_available": 0, "t2_status": "", "t1_side": "", "t1_idx": "", "t2_side": "", "t2_idx": "",
           "fill_type": "", "wallet_hash": pr.get("wallet") or "", "feed_side": pr.get("feed_side", "")}
    if receipt is None:
        return row
    dec = decode_receipt(receipt, tps)
    status, m, ncand = match_print(dec, pr.get("wallet") or "", tokens, float(pr["size"]), hash_addr)
    row.update(match_status=status, n_candidates=ncand)
    if m is None:
        return row
    s1, k1 = t1_of(m)
    st2, t2 = t2_of(dec, m["taker"], tokens)
    row.update(era=m["era"], t1_available=1, t1_side=s1, t1_idx=tokens.index(k1), t2_status=st2, fill_type=fill_type(dec, m, tokens), exchange=m["exchange"])
    if t2 is not None:
        row.update(t2_available=1, t2_side=t2[0], t2_idx=tokens.index(t2[1]))
    return row


# =====================================================================================================================================
# Print fetch (raw address hashed on parse, kept nowhere), frame walk, samples
# =====================================================================================================================================


def parse_print_s(x: Any, key: bytes) -> dict | None:
    """A Data API taker print with the fields S0 needs: ts, outcome index, side, price, size, asset (token id, int), tx (full hash) and the
    wallet HMAC. Malformed rows (bad side / index / price / tx / asset) -> None."""
    try:
        ts, idx = int(x["timestamp"]), int(x["outcomeIndex"])
        size, price = float(x["size"]), float(x["price"])
        side = str(x["side"]).upper()
        asset = int(str(x["asset"]))
        tx = str(x.get("transactionHash") or "").lower()
        if idx not in (0, 1) or side not in ("BUY", "SELL") or not (size > 0 and 0.0 <= price <= 1.0) or len(tx) != 66 or not tx.startswith("0x"):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return {"ts": ts, "idx": idx, "side": side, "price": price, "size": size, "asset": asset, "tx": tx, "wallet": cm.hash_wallet(key, x.get("proxyWallet"))}


def windowed_prints_s(lim: hb.Limiter, cid: str, start: int, end: int, max_pages: int, key: bytes, *, limit: int = PRINT_LIMIT) -> tuple[list[dict], dict]:
    """All taker prints of one condition id with ``start <= ts <= end``, offset-paged (as ``cb8_common.windowed_prints``, keeping asset and the full
    tx hash). A failed request raises :class:`cm.ApiError`; a window with a full last page after ``max_pages`` (or a venue 400 at a deep offset) is
    ``capped`` (the market is unavailable, counted)."""
    rows: list[dict] = []
    seen: set[tuple] = set()
    info = {"pages": 0, "n_raw": 0, "malformed": 0, "duplicates": 0, "out_of_window": 0, "capped": False}
    for page in range(max_pages):
        status, data = lim.get(hb.DATA_TRADES, {"market": cid, "start": int(start), "end": int(end), "takerOnly": "true", "limit": limit, "offset": page * limit})
        if status == 400 and page > 0:
            info["capped"] = True
            return rows, info
        if status != 200 or not isinstance(data, list):
            raise cm.ApiError(f"trades status {status}")
        info["pages"] += 1
        info["n_raw"] += len(data)
        for x in data:
            r = parse_print_s(x, key)
            if r is None:
                info["malformed"] += 1
                continue
            if not (start <= r["ts"] <= end):
                info["out_of_window"] += 1
                continue
            fp = (r["ts"], r["idx"], r["side"], r["price"], r["size"], r["wallet"], r["tx"], r["asset"])
            if fp in seen:
                info["duplicates"] += 1
                continue
            seen.add(fp)
            rows.append(r)
        if len(data) < limit:
            return rows, info
    info["capped"] = True
    return rows, info


def market_row(m: dict) -> dict | None:
    """Parse guard of a Gamma market for the S0 frame: ids, tokens, event / neg-risk / series keys, start / end, volume and the sports flag.
    Outcome prices, UMA status and every price field are dropped."""
    from . import cb1_history as c1  # noqa: PLC0415
    from . import cb6_tail as c6  # noqa: PLC0415

    r = hb.frame_row(m, with_text=True)
    if r is None:
        return None
    k = c6.key_fields(m)
    return {"market_id": r["market_id"], "condition_id": r["condition_id"], "token0": r["token0"], "token1": r["token1"], "event_id": r["event_id"],
            "event_ids": k["event_ids"], "neg_risk_market_id": k["neg_risk_market_id"], "series_ids": k["series_ids"], "start_epoch": r["start_epoch"],
            "end_epoch": r["end_epoch"], "volume": r["volume"], "sports": int(c1.is_sports(r["fee_category"]) or r.get("topic") == "sports"),
            "neg_risk": r["neg_risk"], "pyth": int("pythdata.app" in str(m.get("resolutionSource") or "").lower())}


def frame_windows(start: float, far: float, step_days: int = FRAME_SPLIT_DAYS) -> list[tuple[float, float]]:
    out, a = [], start
    while a < far:
        b = min(a + step_days * cm.DAY, far) if a < start + 400 * cm.DAY else far
        out.append((a, b))
        a = b
    return out


def walk_frame(lim: hb.Limiter, end_from: float, start_before: float, min_volume: float, *, far: float | None = None) -> tuple[list[dict], dict]:
    """Every binary Gamma market with ``endDate >= end_from``, ``startDate < start_before`` and ``volumeNum >= min_volume`` (closed and active,
    each its own query), walked by end-date windows that are bisected when Gamma's offset cap is reached (a window under 1 h that is still
    capped is truncated, counted). Deterministic; no outcome field kept."""
    far = far if far is not None else cm.ep(FRAME_END_FAR)
    rows: dict[str, dict] = {}
    info = {"requests_windows": 0, "truncated_windows": 0, "malformed": 0, "out_of_frame": 0}
    stack = list(reversed(frame_windows(end_from, far)))
    while stack:
        a, b = stack.pop()
        for closed in ("true", "false"):
            params = {"closed": closed, "end_date_min": cm.iso(a), "end_date_max": cm.iso(b), "start_date_max": cm.iso(start_before),
                      "volume_num_min": int(min_volume), "order": "id", "ascending": "true"}
            got, capped = hb._paged(lim, params, error_is_capped=True)
            info["requests_windows"] += 1
            if capped and b - a > FRAME_MIN_WINDOW_S:
                mid = a + (b - a) / 2
                stack += [(mid, b), (a, mid)]
                break
            if capped:
                info["truncated_windows"] += 1
            for m in got:
                r = market_row(m) if isinstance(m, dict) else None
                if r is None:
                    info["malformed"] += 1
                    continue
                if not (r["end_epoch"] >= end_from and r["start_epoch"] < start_before and r["volume"] >= min_volume):
                    info["out_of_frame"] += 1
                    continue
                rows[r["market_id"]] = r
    return sorted(rows.values(), key=lambda r: int(r["market_id"]) if r["market_id"].isdigit() else 0), info


def sample_markets(frame: list[dict], seed: str, n: int = N_MARKETS, max_per_event: int = MAX_PER_EVENT) -> list[dict]:
    """Seeded order (sha256 of seed|market id); at most ``max_per_event`` markets per Gamma event; first ``n``."""
    out, per = [], {}
    for r in sorted(frame, key=lambda r: c9.rank(seed, r["market_id"])):
        ev = r.get("event_id") or f"_m{r['market_id']}"
        if per.get(ev, 0) >= max_per_event:
            continue
        per[ev] = per.get(ev, 0) + 1
        out.append(r)
        if len(out) >= n:
            break
    return out


def draw_prints(prints: list[dict], seed: str, market_id: str, k: int = PRINTS_PER_MARKET) -> list[dict]:
    """``k`` prints of one market by seeded rank of (tx, asset, side, size, ts); distinct (tx, asset, side, size)."""
    out, seen = [], set()
    for p in sorted(prints, key=lambda p: c9.rank(seed, _print_rank_key(p, market_id))):
        fp = (p["tx"], p["asset"], p["side"], float(p["size"]))
        if fp in seen:
            continue
        seen.add(fp)
        out.append(p)
        if len(out) >= k:
            break
    return out


def terciles(values: list[float]) -> tuple[float, float]:
    v = np.asarray([x for x in values if math.isfinite(x)], float)
    if not len(v):
        return math.nan, math.nan
    return float(np.quantile(v, 1 / 3)), float(np.quantile(v, 2 / 3))


def tercile_of(x: float, cuts: tuple[float, float]) -> str:
    if not math.isfinite(x) or not all(math.isfinite(c) for c in cuts):
        return ""
    return "T1" if x <= cuts[0] else ("T2" if x <= cuts[1] else "T3")


# =====================================================================================================================================
# S0 audit job (q0181: strata a and c; q0188: stratum b)
# =====================================================================================================================================


def _hasher(key: bytes) -> Callable[[str], str | None]:
    cache: dict[str, str | None] = {}

    def h(addr: str) -> str | None:
        a = str(addr).lower()
        if a not in cache:
            cache[a] = cm.hash_wallet(key, a)
        return cache[a]

    return h


def seal_copy_ids(seals_dir: Path, is_committed: Callable[[Path], bool] | None) -> tuple[set[str], list[str]]:
    from . import cb8_books as bk  # noqa: PLC0415

    ids, used, _skipped, _shas = bk.seal_copy_ids_audited(Path(seals_dir), own=c9.OWN_SEAL_COPIES, is_committed=is_committed)
    return ids, used


def s0_frame_and_sample(fr: cm.Cb8Run, stratum: str, *, cb7_keys_path: Path | None, seals_dir: Path, is_committed) -> tuple[list[dict], dict]:
    """Frame + key drops (S0c only) + seeded sample, written once (``frame.csv.gz``, ``sample.json``); a resumed chunk reads them back."""
    sp = fr.rdir / "sample.json"
    if sp.exists():
        return json.loads(sp.read_text())["markets"], json.loads(sp.read_text())["info"]
    w0, w1 = (cm.ep(x) for x in WINDOWS[stratum])
    frame, finfo = walk_frame(fr.lim, w0, w1, S0_MIN_VOLUME)
    drops = {"id": 0, "key": 0}
    if stratum == "c":
        ids7, keys7, _rep, sha7 = c9.load_exclusion_keys(Path(cb7_keys_path or c9.CB7_KEYS_DEFAULT))
        sids, used = seal_copy_ids(seals_dir, is_committed)
        frame, drops = c9.drop_by_keys(frame, ids7 | sids, keys7)
        finfo.update(cb7_keys_sha256=sha7, seal_copies_used=used, n_seal_ids=len(sids))
    finfo["drops"] = drops
    fr.budget.write_gz_csv(fr.rdir / "frame.csv.gz", ["market_id", "event_id", "volume", "sports"], [[r["market_id"], r["event_id"], r["volume"], r["sports"]] for r in frame])
    fr.record_file(fr.rdir / "frame.csv.gz")
    smp = sample_markets(frame, SEEDS[stratum])
    cuts = terciles([r["volume"] for r in smp])
    for r in smp:
        r["liq_tercile"] = tercile_of(r["volume"], cuts)
    info = {**finfo, "n_frame": len(frame), "n_sample": len(smp), "liq_cuts": list(cuts), "seed": SEEDS[stratum]}
    fr.budget.write(sp, json.dumps({"markets": smp, "info": info}, sort_keys=True).encode())
    fr.record_file(sp)
    return smp, info


def sign_audit(root: Path, stratum: str, transport, post: Post, *, key: bytes, fp: str, rules_sha: str, smoke_path: Path, now: float,
               cb7_keys_path: Path | None = None, seals_dir: Path | None = None, is_committed=None, rps: float = 2.0,
               disk_cap: int = int(0.01 * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None,
               should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time, snapshot_root: Path | None = None,
               health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c9.DATA_DUMPS_CAP_GB,
               t_seal_epoch: float = c9.T_SEAL_EPOCH, s0b_input: Callable[[], list[dict]] | None = None,
               s0b_stall: Callable[[], dict | None] | None = None) -> dict:
    """q0181 (strata a, c) / q0188 (stratum b). Refuses before T_seal; needs the smoke's receipt criterion for the stratum's era; resumable by
    market (``progress.jsonl``). Writes ``prints_classes.csv.gz`` (no agreement computed) and the manifest. ``s0b_input`` (stratum b) returns the
    drawn K/D SCREEN prints (``kd_s0b_input``): ``market_id, event_id, tx, asset, side, idx, size, price, wallet, token0, token1, feed_side, liq_tercile``."""
    if stratum not in STRATA:
        raise Refused(f"unknown S0 stratum {stratum!r}")
    c9.require_after_t_seal(now, f"sign-audit {stratum}", t_seal_epoch)
    root = c9.refuse_path(Path(root))
    own = c9.stall_of(root / f"s0{stratum}")
    if own:  # sticky: a declared end state is never re-run or overwritten
        return own
    up = s0b_stall() if (stratum == "b" and s0b_stall is not None) else None
    if up:  # M5 (re-check fix 2): an upstream K/D stall is checked BEFORE any input is read; the label is copied, exit 0
        return c9.write_stall(root / f"s0{stratum}", c9.STALL_UPSTREAM, f"K/D input ended {up['status']}: {up.get('reason')}", label=up.get("label"))
    if not smoke_criterion(smoke_path, ERA_CRITERION[stratum]):  # M5: terminal, exit 0, labelled; never a refusal
        return c9.write_stall(root / f"s0{stratum}", c9.STALL_NOT_RUN_SOURCE, f"smoke criterion {ERA_CRITERION[stratum]} failed")
    tps = require_topic_pins()
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    run_id = f"s0{stratum}"
    fr = cm.open_run(root, run_id, transport, allowed_run_id=run_id, kind="cb9_sign_audit", label=f"CB9 S0{stratum}",
                     params={"stratum": stratum, "window": list(WINDOWS.get(stratum, ("kd_screen", "kd_screen"))), "seed": SEEDS[stratum], "n_markets": N_MARKETS,
                             "prints_per_market": PRINTS_PER_MARKET, "evidence_role": c9.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp=fp, disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    if (fr.rdir / "prints_classes.csv.gz").exists():
        m = fr.manifest(None, {"status": "sign_audit_complete", "complete": True})
        m["status"] = "sign_audit_complete"
        return m
    rpc = RpcClient(post, rps=min(rps, RPC_RPS), sleep=sleep, live_check=live_check)
    hasher = _hasher(key)
    if stratum == "b":
        if s0b_input is None:
            raise Refused("stratum b needs the K/D SCREEN prints (cb9_kd)")
        sp = fr.rdir / "s0b_drawn.json"
        if sp.exists():
            todo = json.loads(sp.read_text())
        else:
            try:
                todo = s0b_input()
            except UpstreamStall as exc:  # defensive: a stall that appeared after the first check
                return c9.write_stall(root / f"s0{stratum}", c9.STALL_UPSTREAM, f"K/D input ended {exc.stall['status']}: {exc.stall.get('reason')}",
                                      label=exc.stall.get("label"))
            fr.budget.write(sp, json.dumps(todo, sort_keys=True, default=float).encode())
            fr.record_file(sp)
        order: list[str] = []
        for p in todo:
            if p["market_id"] not in order:
                order.append(p["market_id"])
        plan = [(mid, [p for p in todo if p["market_id"] == mid]) for mid in order]
        sinfo: dict = {"n_prints_drawn": len(todo), "n_markets": len(plan)}
    else:
        smp, sinfo = s0_frame_and_sample(fr, stratum, cb7_keys_path=cb7_keys_path, seals_dir=Path(seals_dir or c9.SEALS_DIR), is_committed=is_committed)
        plan = [(r["market_id"], r) for r in smp]
    done = _progress(fr.rdir / "progress.jsonl")
    w0, w1 = (cm.ep(x) for x in WINDOWS.get(stratum, ("1970-01-01", "1970-01-02")))
    for mid, item in plan:
        if mid in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            m = fr.manifest(why, {"transient": True, "rpc": rpc.stats(), "sample": sinfo})
            m["status"] = "in_progress"
            return m
        rec: dict = {"market_id": mid, "rows": [], "status": "ok"}
        if stratum == "b":
            prs = item
            tokens = (int(prs[0]["token0"]), int(prs[0]["token1"]))
        else:
            r = item
            tokens = (int(r["token0"]), int(r["token1"]))
            try:
                got, pinfo = windowed_prints_s(fr.lim, r["condition_id"], int(w0), int(w1) - 1, S0_PAGES, key)
            except cm.ApiError as exc:
                rec["status"] = f"prints_failed:{str(exc)[:40]}"
                got, pinfo = [], {}
            except RuntimeError:
                m = fr.manifest("network", {"transient": True, "rpc": rpc.stats(), "sample": sinfo})
                m["status"] = "in_progress"
                return m
            if pinfo.get("capped"):
                rec["status"] = "capped"
                got = []
            prs = [{**p, "market_id": mid, "event_id": r["event_id"], "sports": r["sports"], "liq_tercile": r.get("liq_tercile", "")}
                   for p in draw_prints(got, SEEDS[stratum], mid)]
            rec["n_window_prints"] = len(got)
        for p in prs:
            rcpt, ep = rpc.receipt(p["tx"])
            rec["rows"].append(classify_print({**p, "stratum": stratum}, rcpt, ep, tokens, hasher, tps))
        _append(fr.rdir / "progress.jsonl", rec)
        done[mid] = rec
    rows = [[row[c] for c in PRINT_COLUMNS] for mid, _ in plan for row in done[mid]["rows"]]
    fr.budget.write_gz_csv(fr.rdir / "prints_classes.csv.gz", PRINT_COLUMNS, rows)
    fr.record_file(fr.rdir / "prints_classes.csv.gz")
    fr.counts.update({"markets": len(plan), "prints": len(rows), "markets_capped": sum(1 for x in done.values() if x["status"] == "capped"),
                      "markets_failed": sum(1 for x in done.values() if x["status"].startswith("prints_failed"))})
    m = fr.manifest(None, {"status": "sign_audit_complete", "complete": True, "rpc": rpc.stats(), "sample": sinfo})
    m["status"] = "sign_audit_complete"
    return m


def _progress(pf: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                out[rec["market_id"]] = rec
    return out


def _append(pf: Path, rec: dict) -> None:
    with Path(pf).open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")


def _print_rank_key(p: dict, market_id: str) -> str:
    return f"{market_id}|{p['tx']}|{p['asset']}|{p['side']}|{float(p['size'])!r}|{p['ts']}"


def s0b_sample(kd_prints: Iterable[dict], n: int = N_PRINTS_TARGET, per_market: int = PRINTS_PER_MARKET, seed: str = SEEDS["b"]) -> list[dict]:
    """S0b: markets in seeded order, within each market the ``per_market`` prints of lowest seeded rank (distinct tx, asset, side, size; the same
    rule as ``draw_prints``), until ``n`` prints. Streaming (memory = markets x per_market). SCREEN only: a HOLDOUT print is a refusal."""
    best: dict[str, dict[tuple, tuple[str, dict]]] = {}
    for p in kd_prints:
        if str(p.get("split", "SCREEN")).upper() != "SCREEN":
            raise Refused("S0b received a HOLDOUT print; the HOLDOUT is sealed")
        tx = str(p.get("tx") or "")
        if not tx.startswith("0x") or len(tx) != 66:
            continue
        mid = str(p["market_id"])
        rk = c9.rank(seed, _print_rank_key(p, mid))
        fp = (p["tx"], p["asset"], p["side"], float(p["size"]))
        cur = best.setdefault(mid, {})
        if fp in cur:
            if rk < cur[fp][0]:
                cur[fp] = (rk, p)
            continue
        if len(cur) < per_market:
            cur[fp] = (rk, p)
            continue
        worst = max(cur, key=lambda k: cur[k][0])
        if rk < cur[worst][0]:
            del cur[worst]
            cur[fp] = (rk, p)
    out: list[dict] = []
    for mid in sorted(best, key=lambda x: c9.rank(seed, x)):
        out += [v[1] for v in sorted(best[mid].values(), key=lambda v: v[0])]
        if len(out) >= n:
            return out[:n]
    return out


def _side_str(v) -> str:
    x = str(v).strip().upper()
    if x in ("BUY", "SELL"):
        return x
    try:
        return "BUY" if float(x) > 0 else "SELL"
    except ValueError:
        return ""


class UpstreamStall(Exception):
    """The K/D layout ended in a declared stall (kd-frame or kd-books): S0b has no input to draw; the caller records ``upstream_not_testable``."""

    def __init__(self, stall: dict):
        super().__init__(f"K/D upstream stall {stall.get('status')}")
        self.stall = stall


def kd_upstream_stall(cb9_root: Path) -> dict | None:
    """The K/D frame or books run's terminal stall manifest (kd-frame first, then kd-books), or None. Checked before any K/D file is opened."""
    from . import cb9_kd as kd  # noqa: PLC0415

    root = Path(cb9_root)
    return c9.stall_of(root / kd.FRAME_RUN) or c9.stall_of(root / kd.BOOKS_RUN)


def kd_s0b_input(cb9_root: Path) -> list[dict]:
    """S0b input from the K/D layout (``cb9_kd``): SCREEN pre-origin prints only (``<day>.prints_pre.csv.gz``; the guarded post-origin files are never
    opened here), markets of the SCREEN sample minus the seal-time drops; seeded draw; then the pmxt ``last_trade_price`` feed side by (tx, asset) from
    the SCREEN ``<day>.ltp.csv.gz`` files (a tx with conflicting feed sides -> blank); liquidity terciles of Gamma volume over the drawn markets.
    Ruling (c): feed sides exist for prints in [13Z, 14Z) (the stored 13Z-lookback events); the rest are ``not_measured``."""
    from . import cb1_history as c1  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb9_kd as kd  # noqa: PLC0415

    root = Path(cb9_root)
    up = kd_upstream_stall(root)
    if up:
        raise UpstreamStall(up)
    sample = {r["market_id"]: r for r in kd.read_sample(root / kd.FRAME_RUN) if str(r.get("split")).lower() == kd.SCREEN}
    drop = kd.dropped_ids(root / kd.BOOKS_RUN)
    sdir = root / kd.BOOKS_RUN / kd.SCREEN

    def stream():
        for f in sorted(sdir.glob("*" + kd.PRINTS_PRE_SUFFIX)):
            for r in c7.read_csv_gz(f):
                mid = r["market_id"]
                if mid not in sample or mid in drop:
                    continue
                m = sample[mid]
                yield {"market_id": mid, "event_id": m.get("event_id", ""), "tx": str(r["tx"]).lower(), "asset": int(r["asset"]), "side": _side_str(r["side"]),
                       "day": str(r.get("day") or ""), "idx": int(r["idx"]), "size": float(r["size"]), "price": float(r["price"]), "wallet": r.get("wallet_hash") or "", "ts": int(float(r["ts"])),
                       "token0": m["token0"], "token1": m["token1"], "split": "SCREEN", "volume": float(m.get("volume") or math.nan),
                       "sports": int(c1.is_sports(m.get("fee_category")) or m.get("topic") == "sports")}

    drawn = [p for p in s0b_sample(stream()) if p["side"] in ("BUY", "SELL")]
    need = {(p["tx"], str(p["asset"])) for p in drawn}
    read_lb: set[tuple[str, str, int]] = set()  # (market_id, day, idx) whose 13Z lookback hour was actually read (origin ``lookback`` == read)
    for f in sorted(sdir.glob("*" + kd.ORIGINS_SUFFIX)):
        for r in c7.read_csv_gz(f):
            if str(r.get("lookback")) == "read":
                read_lb.add((str(r["market_id"]), str(r["day"]), int(r["idx"])))
    feed: dict[tuple[str, str], str] = {}
    for f in sorted(sdir.glob(kd.SCREEN_LTP_GLOB)):
        for r in c7.read_csv_gz(f):
            k = (str(r.get("tx") or "").lower(), str(r.get("asset")))
            if k in need:
                sd = _side_str(r.get("side"))
                feed[k] = sd if feed.get(k, sd) == sd else ""
    cuts = terciles(list({p["market_id"]: p["volume"] for p in drawn}.values()))
    return [{**p, "feed_side": feed_label(p, feed, read_lb), "liq_tercile": tercile_of(p["volume"], cuts)} for p in drawn]


FEED_HOUR_Z = 13  # ruling (c): kd_books stores the 13Z-lookback last_trade_price events it already read; [13Z, 14Z) is the measured span


def feed_label(p: dict, feed: dict[tuple[str, str], str], read_lookback: set[tuple[str, str, int]] | None = None) -> str:
    """Feed side of an S0b print: BUY / SELL from the matched pmxt last_trade_price event; ``unmatched`` for a print in [13Z, 14Z) without an event
    (or with conflicting sides); ``not_measured`` outside that span (the guarded post-origin prints are never opened, ruling (c)) and, when
    ``read_lookback`` is given (re-check fix b), for a token whose 13Z hour was never read (origin ``lookback`` != read): no event could exist there."""
    hz = datetime.fromtimestamp(int(p["ts"]), UTC).hour
    if hz != FEED_HOUR_Z:
        return "not_measured"
    if read_lookback is not None and (str(p["market_id"]), str(p.get("day", "")), int(p["idx"])) not in read_lookback:
        return "not_measured"
    return feed.get((p["tx"], str(p["asset"])), "") or "unmatched"


# =====================================================================================================================================
# Smoke (q0180, receipt part) and its gate
# =====================================================================================================================================


def smoke_receipts(lim: hb.Limiter, rpc: RpcClient, key: bytes) -> dict:
    """For each era: closed Gamma markets ending on the pinned out-of-window day (volume >= $10k, id order), drawn in seeded order until
    ``SMOKE_RECEIPTS_PER_ERA`` distinct receipts (by tx hash) are collected, at most ``SMOKE_MAX_MARKETS_PER_ERA`` markets (``n_markets_tried``), ``SMOKE_PRINTS_PER_MARKET`` seeded prints each from the 3 days before the end; receipts decoded with the pinned topics; PASS per era
    iff >= 18 of 20 receipts give a matched print with T1 = T2. Counts only (no Data API side is compared). A network failure raises NotNow."""
    tps = require_topic_pins()
    hasher = _hasher(key)
    out = {}
    for era, day in SMOKE_ERA_DAYS.items():
        d0 = cm.ep(day)
        try:
            st, mk = lim.get(hb.GAMMA_MARKETS, {"closed": "true", "end_date_min": cm.iso(d0), "end_date_max": cm.iso(d0 + cm.DAY - 1),
                                                 "volume_num_min": int(SMOKE_MIN_VOLUME), "limit": 100, "order": "id", "ascending": "true"})
        except RuntimeError:
            raise NotNow("smoke: Gamma request failed (network); nothing written") from None
        if st != 200 or not isinstance(mk, list):
            raise NotNow(f"smoke: Gamma status {st}; nothing written")
        rows = [r for r in (market_row(m) for m in mk if isinstance(m, dict)) if r is not None]
        picks = sorted(rows, key=lambda r: c9.rank(SMOKE_SEED + era, r["market_id"]))[:SMOKE_MAX_MARKETS_PER_ERA]
        res = {"n_gamma_markets": len(rows), "n_markets": len(picks), "n_markets_tried": 0, "n_duplicate_tx": 0, "n_receipts": 0, "n_receipt_unavailable": 0, "n_matched": 0, "n_t1_eq_t2": 0,
               "n_era_seen": {"v1": 0, "v2": 0}, "fill_types": {},
               "by_exchange": {a: {"matched": 0, "t1_eq_t2": 0} for a in (EXCHANGES_V1 + EXCHANGES_V2)}}
        seen_tx: set = set()
        for r in picks:
            if res["n_receipts"] >= SMOKE_RECEIPTS_PER_ERA:
                break
            res["n_markets_tried"] += 1
            end = int(r["end_epoch"])
            try:
                got, _info = windowed_prints_s(lim, r["condition_id"], end - 3 * 86400, end, 1, key)
            except cm.ApiError:
                continue
            except RuntimeError:
                raise NotNow("smoke: trades request failed (network); nothing written") from None
            tokens = (int(r["token0"]), int(r["token1"]))
            for p in draw_prints(got, SMOKE_SEED + era, r["market_id"], SMOKE_PRINTS_PER_MARKET):
                if res["n_receipts"] >= SMOKE_RECEIPTS_PER_ERA:
                    break
                if p["tx"] in seen_tx:  # distinct receipts only
                    res["n_duplicate_tx"] += 1
                    continue
                seen_tx.add(p["tx"])
                rc, ep = rpc.receipt(p["tx"])
                res["n_receipts"] += 1
                row = classify_print({**p, "stratum": "smoke", "market_id": r["market_id"]}, rc, ep, tokens, hasher, tps)
                if row["receipt_status"] != "ok":
                    res["n_receipt_unavailable"] += 1
                    if res["n_receipt_unavailable"] > SMOKE_MAX_UNAVAILABLE:  # M2: unavailable is not failed; nothing written, retry later
                        raise NotNow(f"smoke: more than {SMOKE_MAX_UNAVAILABLE} receipts unavailable in era {era}; nothing written")
                    continue
                if row["t1_available"]:
                    res["n_matched"] += 1
                    res["n_era_seen"][row["era"]] = res["n_era_seen"].get(row["era"], 0) + 1
                    res["fill_types"][row["fill_type"]] = res["fill_types"].get(row["fill_type"], 0) + 1
                    bx = res["by_exchange"].setdefault(row["exchange"], {"matched": 0, "t1_eq_t2": 0})
                    bx["matched"] += 1
                    if row["t2_available"] and row["t2_side"] == row["t1_side"] and row["t2_idx"] == row["t1_idx"] and row["era"] == era:
                        res["n_t1_eq_t2"] += 1
                        bx["t1_eq_t2"] += 1
        res["exchanges_exercised"] = {a: res["by_exchange"][a]["matched"] > 0 for a in (EXCHANGES_V1 if era == "v1" else EXCHANGES_V2)}  # reported (M1)
        res["pass"] = bool(res["n_receipts"] >= SMOKE_RECEIPTS_PER_ERA and res["n_t1_eq_t2"] >= SMOKE_MIN_DECODED)
        out[era] = res
    return {"receipts": out, "rpc": rpc.stats(), "topic_pins": topic_pins_ok()}


def smoke_criterion(path: Path, name: str) -> bool:
    """One smoke criterion; a missing / unreadable / other-version result is a refusal (queue order), a False criterion is returned (the caller
    writes the M5 stall)."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found; run q0180 first")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"smoke result {p} unreadable") from exc
    if d.get("smoke_version") != SMOKE_VERSION:
        raise Refused(f"smoke result {p} is {d.get('smoke_version')}, not {SMOKE_VERSION}")
    return (d.get("criteria") or {}).get(name) is True


ERA_CRITERION = {"a": "receipts_v2", "b": "receipts_v2", "c": "receipts_v1"}


def smoke_ok(path: Path, need: tuple[str, ...]) -> dict:
    """The CB9 fetchers' smoke gate: the write-once result exists, is this smoke version, and the criteria in ``need`` passed."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found; run q0180 first")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"smoke result {p} unreadable") from exc
    if d.get("smoke_version") != SMOKE_VERSION:
        raise Refused(f"smoke result {p} is {d.get('smoke_version')}, not {SMOKE_VERSION}")
    crit = d.get("criteria") or {}
    bad = [k for k in need if crit.get(k) is not True]
    if bad:
        raise Refused(f"smoke result {p}: criteria {bad} not met; the dependent family is 'not run (source)', counted")
    return d


# =====================================================================================================================================
# Census (counts only, field-restricted) and the S0 screen
# =====================================================================================================================================


def census_s(rows_by_stratum: dict[str, list[dict]]) -> dict:
    """S0 census per stratum from rows that carry ONLY ``CENSUS_COLUMNS_S`` (refuses a row with a forbidden field). No agreement is computed."""
    out = {}
    for s, rows in rows_by_stratum.items():
        for r in rows:
            bad = [k for k in r if k in CENSUS_FORBIDDEN_S]
            if bad:
                raise Refused(f"census received forbidden fields {bad}")
        n = len(rows)
        matched = [r for r in rows if r["match_status"] == "matched"]
        def cnt(key: str, rows: list[dict] = rows) -> dict:
            return {v: sum(1 for r in rows if r[key] == v) for v in sorted({r[key] for r in rows})}

        gs = bool(n and len(matched) / n >= GS_MATCH_RATE and len(matched) >= GS_MIN_MATCHED)
        out[s] = {"n_prints": n, "n_receipt_ok": sum(1 for r in rows if r["receipt_status"] == "ok"), "by_endpoint": cnt("endpoint"),
                  "match_status": cnt("match_status"), "matched_share": len(matched) / n if n else 0.0, "n_matched": len(matched),
                  "matched_markets": len({r["market_id"] for r in matched}), "t1_available": sum(int(r["t1_available"]) for r in rows),
                  "t2_available": sum(int(r["t2_available"]) for r in rows), "t2_status": cnt("t2_status"), "fill_types": cnt("fill_type"), "eras": cnt("era"),
                  "sports_prints": sum(int(r["sports"]) for r in rows), "gate_GS": gs, "label": "ok" if gs else "not testable (source)"}
    return out


def read_census_rows(path: Path) -> list[dict]:
    return c9.read_csv_gz_restricted(path, CENSUS_COLUMNS_S, CENSUS_FORBIDDEN_S)


def _f(r: dict, k: str) -> str:
    return str(r.get(k, ""))


def s0_stratum(rows: list[dict], *, n_boot: int = c9.N_BOOT, seed: int = c9.SEED_BOOT) -> dict:
    """The S0 statistic and verdict of one stratum. Gate GS (match rate >= 90% of sampled prints and >= 300 matched); source gate (T1 = T2 on
    >= 99% of matched prints where both exist); ``q_hat`` = share of matched prints whose API YES-sign equals T1's; ``q_LB`` = min(0.5th percentile
    of a 2,000-draw market-cluster bootstrap, Wilson 99% lower bound on matched markets with successes = n q_hat); ``q_wc`` scores every sampled
    print without a match (unmatched or receipt unavailable) as a disagreement."""
    n = len(rows)
    matched = [r for r in rows if _f(r, "match_status") == "matched" and str(r.get("t1_available")) in ("1", "True", "true")]
    res: dict[str, Any] = {"n_prints": n, "n_matched": len(matched), "matched_markets": len({_f(r, "market_id") for r in matched})}
    gs = bool(n and len(matched) / n >= GS_MATCH_RATE and len(matched) >= GS_MIN_MATCHED)
    res["gate_GS"] = gs
    if not gs:
        return {**res, "testable": False, "verdict": "not testable (source)", "mapped_results": "unverified"}
    both = [r for r in matched if str(r.get("t2_available")) in ("1", "True", "true")]
    eq = sum(1 for r in both if _f(r, "t1_side") == _f(r, "t2_side") and _f(r, "t1_idx") == _f(r, "t2_idx"))
    res["source_gate"] = {"n_both": len(both), "n_t1_eq_t2": eq, "share": eq / len(both) if both else 0.0}
    if not both or eq / len(both) < SOURCE_GATE_T1T2:
        return {**res, "testable": False, "verdict": "not testable (on-chain truth ambiguous)", "mapped_results": "unverified"}
    api = np.array([yes_sign(_f(r, "api_side"), int(r["api_idx"])) for r in matched])
    t1 = np.array([yes_sign(_f(r, "t1_side"), int(r["t1_idx"])) for r in matched])
    agree = (api == t1).astype(float)
    mk = np.array([_f(r, "market_id") for r in matched])
    q_hat = float(agree.mean())
    boot = c9.cluster_bootstrap_means(agree, mk, n_boot=n_boot, seed=seed)
    q_boot = float(np.percentile(boot, LB_PERCENTILE))
    n_mk = len(set(mk))
    q_wil = c9.wilson_lower(n_mk * q_hat, n_mk, WILSON_CONF)
    q_lb = min(q_boot, q_wil)
    q_wc = float(agree.sum() / n)
    notional = np.array([float(r.get("notional") or 0.0) for r in matched])
    tok = np.array([_f(r, "api_side") == _f(r, "t1_side") and str(r["api_idx"]) == str(r["t1_idx"]) for r in matched], float)
    if q_hat < MINOR_Q or q_wc < MINOR_QWC:
        verdict = "material noise"
    elif q_hat >= NEAR_TRUTH_Q and q_lb >= NEAR_TRUTH_LB:
        verdict = "near-truth"
    elif q_hat >= NEAR_TRUTH_Q:
        verdict = "minor noise or better (bound limited by n)"
    else:
        verdict = "minor noise"
    dis = [r for r, a in zip(matched, agree, strict=True) if a == 0]

    def by(key: str) -> dict:
        out = {}
        for v in sorted({_f(r, key) for r in matched}):
            sel = np.array([_f(r, key) == v for r in matched])
            out[v] = {"n": int(sel.sum()), "q_hat": float(agree[sel].mean()) if sel.any() else None}
        return out

    feed = [r for r in matched if _f(r, "feed_side") in ("BUY", "SELL")]
    feed_agree = None
    if feed:
        # feed side is a token-terms side of the print's own asset; compared with T1 in YES terms on the print's outcome index
        feed_agree = float(np.mean([yes_sign(_f(r, "feed_side"), int(r["api_idx"])) == yes_sign(_f(r, "t1_side"), int(r["t1_idx"])) for r in feed]))
    return {**res, "testable": True, "q_hat": q_hat, "q_lb": q_lb, "q_lb_bootstrap": q_boot, "q_lb_wilson_markets": q_wil, "q_wc": q_wc,
            "q_print_wilson99_reported": c9.wilson_lower(agree.sum(), len(agree), WILSON_CONF), "verdict": verdict,
            "mapped_results": "attenuation route closed for this era" if verdict == "near-truth" else ("methods note M4; S1 runs" if verdict == "material noise" else "methods note only"),
            "s1_triggered": verdict == "material noise",
            "reported": {"a_tok": float(tok.mean()), "notional_weighted_q": float((agree * notional).sum() / notional.sum()) if notional.sum() > 0 else None,
                         "by_liq_tercile": by("liq_tercile"), "by_price_band": by("price_band"), "by_fill_type": by("fill_type"), "by_sports": by("sports"),
                         "feed_side_agreement": feed_agree, "n_feed": len(feed),
                         "disagreement_share_mint_merge": (sum(1 for r in dis if _f(r, "fill_type") in ("mint", "merge")) / len(dis)) if dis else None}}


def s0_screen(rows_by_stratum: dict[str, list[dict]]) -> dict:
    """Per-stratum verdicts with the era map; a stratum failing GS is 'not testable (source)' and its mapped results 'unverified' (never inherited).
    The pooled q_hat over strata passing GS is descriptive only."""
    per = {s: {**s0_stratum(rows_by_stratum.get(s, [])), "era_map": ERA_MAP[s]} for s in STRATA}
    pooled_rows = [r for s in STRATA if per[s].get("testable") for r in rows_by_stratum.get(s, []) if _f(r, "match_status") == "matched"]
    pooled = None
    if pooled_rows:
        pooled = float(np.mean([yes_sign(_f(r, "api_side"), int(r["api_idx"])) == yes_sign(_f(r, "t1_side"), int(r["t1_idx"])) for r in pooled_rows]))
    return {"strata": per, "pooled_q_hat_descriptive": pooled, "s1_triggered_eras": [s for s in STRATA if per[s].get("s1_triggered")],
            "testable": any(per[s].get("testable") for s in STRATA)}


# =====================================================================================================================================
# S1: features on identical prints, ratio rule
# =====================================================================================================================================


def s1_units(prints: list[dict], w0: float, w1: float) -> list[dict]:
    """2-h grid origins ``t = w0 + 6 h + 2 h k`` with ``t + 6 h <= w1`` and >= 3 prints in ``[t - 6 h, t)``. Each print carries ts, price (own token),
    size, idx, api_side and t1_side / t1_idx (prints without T1 are excluded from BOTH features: identical prints). ``x`` = 6-h notional
    imbalance in YES terms (raw, clipped [-1, 1]); ``d`` = last YES-price print before ``t + 6 h`` minus the last before ``t``, each within 30 min
    of its anchor, else unavailable."""
    pr = sorted([p for p in prints if p.get("t1_side") in ("BUY", "SELL")], key=lambda p: p["ts"])
    ts = np.array([p["ts"] for p in pr], float)
    yes_p = np.array([p["price"] if int(p["idx"]) == 0 else 1.0 - p["price"] for p in pr], float)
    notl = np.array([p["size"] * p["price"] for p in pr], float)
    s_api = np.array([yes_sign(p["api_side"], int(p["idx"])) for p in pr], float)
    s_chain = np.array([yes_sign(p["t1_side"], int(p["t1_idx"])) for p in pr], float)
    out = []
    t = w0 + S1_FEATURE_H * 3600.0
    while t + S1_TARGET_H * 3600.0 <= w1:
        lo, hi = np.searchsorted(ts, t - S1_FEATURE_H * 3600.0, "left"), np.searchsorted(ts, t, "left")
        if hi - lo >= S1_MIN_PRINTS and notl[lo:hi].sum() > 0:
            tot = notl[lo:hi].sum()
            x_api = float(np.clip((s_api[lo:hi] * notl[lo:hi]).sum() / tot, -1, 1))
            x_chain = float(np.clip((s_chain[lo:hi] * notl[lo:hi]).sum() / tot, -1, 1))
            i0 = hi - 1
            j = int(np.searchsorted(ts, t + S1_TARGET_H * 3600.0, "left")) - 1
            ok = i0 >= 0 and t - ts[i0] <= S1_ANCHOR_TOL_S and j >= hi and (t + S1_TARGET_H * 3600.0) - ts[j] <= S1_ANCHOR_TOL_S
            out.append({"t": t, "x_api": x_api, "x_chain": x_chain, "d": float(yes_p[j] - yes_p[i0]) if ok else math.nan})
        t += S1_ORIGIN_STEP_H * 3600.0
    return out


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    xc = x - x.mean()
    den = float((xc * xc).sum())
    return float((xc * (y - y.mean())).sum() / den) if den > 0 else math.nan


def s1_ratio(units: list[dict], events: list[str], *, n_boot: int = c9.N_BOOT, seed: int = c9.SEED_BOOT) -> dict:
    """R = beta_chain / beta_api from two OLS fits ``d = a + b x`` on identical units; 2,000-draw event-clustered bootstrap. A draw with
    ``beta_api <= 0`` (or undefined) counts as ``R <= 1.5``. Pass iff R_hat >= 1.5 AND the 1st percentile of the draws > 1.5 (p = share of draws
    with R <= 1.5 < 0.01). The share of R <= 1 is reported; beta_chain in cents per unit flow."""
    keep = [i for i, u in enumerate(units) if math.isfinite(u["d"])]
    x_a = np.array([units[i]["x_api"] for i in keep])
    x_c = np.array([units[i]["x_chain"] for i in keep])
    d = np.array([units[i]["d"] for i in keep])
    ev = np.array([events[i] for i in keep]).astype(str)
    n_ev = len(set(ev.tolist()))
    if len(keep) < c9.MIN_UNITS or n_ev < c9.MIN_CLUSTERS:
        return {"n": len(keep), "n_events": n_ev, "testable": False, "p": 1.0, "pass": False, "verdict": "not testable (too few units or events)"}
    b_api, b_chain = _slope(x_a, d), _slope(x_c, d)
    r_hat = b_chain / b_api if (math.isfinite(b_api) and b_api > 0) else -math.inf
    uniq = sorted(set(ev.tolist()))
    idx = {e: np.flatnonzero(ev == e) for e in uniq}
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot)
    for k in range(n_boot):
        pick = np.concatenate([idx[uniq[j]] for j in rng.integers(0, len(uniq), len(uniq))])
        ba, bc = _slope(x_a[pick], d[pick]), _slope(x_c[pick], d[pick])
        draws[k] = bc / ba if (math.isfinite(ba) and ba > 0 and math.isfinite(bc)) else -math.inf
    p = float(np.mean(draws <= S1_RATIO))
    lb = float(np.percentile(draws, S1_LB_PERCENTILE)) if np.isfinite(draws).any() else -math.inf
    ok = bool(r_hat >= S1_RATIO and lb > S1_RATIO)
    return {"n": len(keep), "n_events": n_ev, "testable": True, "beta_api": b_api, "beta_chain": b_chain, "beta_chain_cents": b_chain * 100.0,
            "r_hat": r_hat, "lb_1pct": lb, "p": p, "share_r_le_1": float(np.mean(draws <= 1.0)), "pass": ok, "advance": ok,
            "verdict": "pass (R >= 1.5, lower bound > 1.5)" if ok else "fail (lower bound <= 1.5 or R_hat < 1.5)"}


def h10_exclusions(excl_ids: set[str], excl_keys: dict[str, set[str]], cb9_ids: dict[str, set[str]]) -> tuple[set[str], dict]:
    """The h10_sign exclusion set (round 1 item 4): the q0182 ids and keys PLUS every CB9 market: the K/D frame (SCREEN and HOLDOUT), the P frame
    and the S0a/S0b/S0c samples. Every named CB9 source is required (a missing one is a refusal)."""
    need = ("kd_frame", "pyth_frame", "s0a", "s0b", "s0c")
    missing = [k for k in need if k not in cb9_ids]
    if missing:
        raise Refused(f"h10_sign exclusions: CB9 id sources {missing} missing")
    ids = set(excl_ids)
    for k in need:
        ids |= set(cb9_ids[k])
    return ids, {"n_q0182_ids": len(excl_ids), **{f"n_{k}": len(cb9_ids[k]) for k in need}, "keys": {k: len(v) for k, v in excl_keys.items()}}


def h10_window(market: dict, era: tuple[float, float], seed: str = H10_SEED) -> tuple[float, float] | None:
    """One seeded 72-h window per market: a seeded UTC day start inside the market's scheduled life within the era (the whole window must fit in
    ``[max(start, era0), min(end, era1))``); ``None`` if the overlap is shorter than 72 h."""
    lo = max(float(market["start_epoch"]), era[0])
    hi = min(float(market["end_epoch"]), era[1])
    first = math.ceil(lo / cm.DAY) * cm.DAY
    last = math.floor((hi - H10_WINDOW_H * 3600.0) / cm.DAY) * cm.DAY
    if last < first:
        return None
    n = int((last - first) // cm.DAY) + 1
    k = int(c9.rank(seed, f"window|{market['market_id']}"), 16) % n
    w0 = first + k * cm.DAY
    return w0, w0 + H10_WINDOW_H * 3600.0


def sign_fetch_h10(root: Path, transport, post: Post, *, key: bytes, fp: str, rules_sha: str, era: str, excl_ids: set[str], excl_keys: dict[str, set[str]],
                   cb9_ids: dict[str, set[str]], now: float, rps: float = 2.0, disk_cap: int = int(0.05 * 1024**3), budget_min: float | None = None,
                   sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None,
                   data_dumps: Path | None = None, data_dumps_cap_gb: float = c9.DATA_DUMPS_CAP_GB) -> dict:
    """q0193 (only after an S0 'material noise' verdict for ``era``): frame of the era (Gamma volume >= $1k), exclusions (``h10_exclusions``), 1,200
    markets in seeded order (<= 3 per event), one seeded 72-h window each, all taker prints (capped window -> unavailable), receipts for every print of
    whole windows in seeded order until 20,000 prints. Resumable by market. Writes ``sample.csv.gz``, ``prints/<market>.csv.gz`` (classes, no
    raw wallet) and ``manifest.json``."""
    if era not in H10_ERA:
        raise Refused(f"unknown S1 era {era!r}")
    c9.require_after_t_seal(now, "sign-fetch")
    ids, xinfo = h10_exclusions(excl_ids, excl_keys, cb9_ids)
    tps = require_topic_pins()
    root = c9.refuse_path(Path(root))
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    fr = cm.open_run(root, c9.H10_RUN, transport, allowed_run_id=c9.H10_RUN, kind="cb9_h10_sign", label="CB9 S1 h10_sign",
                     params={"era": era, "window": list(H10_ERA[era]), "n_markets": H10_N_MARKETS, "window_h": H10_WINDOW_H, "max_receipt_prints": H10_MAX_RECEIPT_PRINTS,
                             "seed": H10_SEED, "exclusions": xinfo, "evidence_role": c9.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp=fp, disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    e0, e1 = (cm.ep(x) for x in H10_ERA[era])
    sp = fr.rdir / "sample.json"
    if sp.exists():
        smp = json.loads(sp.read_text())
    else:
        frame, _finfo = walk_frame(fr.lim, e0, e1, S0_MIN_VOLUME)
        n_pyth = sum(1 for r in frame if r.get("pyth"))
        frame = [r for r in frame if not r.get("pyth")]  # every Pyth-settled market is excluded by rule (also when the P frame stalled)
        frame, drops = c9.drop_by_keys(frame, ids, excl_keys)
        drops["pyth_rule"] = n_pyth
        smp = []
        for r in sample_markets(frame, H10_SEED, n=len(frame)):
            w = h10_window(r, (e0, e1))
            if w is None:
                continue
            smp.append({**r, "w0": w[0], "w1": w[1]})
            if len(smp) >= H10_N_MARKETS:
                break
        fr.budget.write(sp, json.dumps(smp, sort_keys=True).encode())
        fr.record_file(sp)
        fr.budget.write_gz_csv(fr.rdir / "sample.csv.gz", ["market_id", "event_id", "w0", "w1"], [[r["market_id"], r["event_id"], r["w0"], r["w1"]] for r in smp])
        fr.record_file(fr.rdir / "sample.csv.gz")
        fr.extra_state["drops"] = drops
    rpc = RpcClient(post, rps=min(rps, RPC_RPS), sleep=sleep, live_check=live_check)
    hasher = _hasher(key)
    done = _progress(fr.rdir / "progress.jsonl")
    n_receipt_prints = sum(int(x.get("n_receipt_prints", 0)) for x in done.values())
    cols = ["ts", "idx", "api_side", "price", "size", "receipt_status", "match_status", "t1_side", "t1_idx", "t2_status", "fill_type"]
    for r in smp:
        mid = r["market_id"]
        if mid in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            m = fr.manifest(why, {"transient": True, "rpc": rpc.stats()})
            m["status"] = "in_progress"
            return m
        rec: dict = {"market_id": mid, "status": "ok", "n_receipt_prints": 0}
        try:
            got, pinfo = windowed_prints_s(fr.lim, r["condition_id"], int(r["w0"]), int(r["w1"]) - 1, H10_PAGES, key)
        except cm.ApiError as exc:
            got, pinfo, rec["status"] = [], {}, f"prints_failed:{str(exc)[:40]}"
        except RuntimeError:
            m = fr.manifest("network", {"transient": True, "rpc": rpc.stats()})
            m["status"] = "in_progress"
            return m
        if pinfo.get("capped"):
            rec["status"], got = "capped", []
        if got and n_receipt_prints + len(got) > H10_MAX_RECEIPT_PRINTS:
            rec["status"] = "receipt_cap_reached"  # whole windows only: this and every later window gets no receipts
        tokens = (int(r["token0"]), int(r["token1"]))
        rows = []
        if rec["status"] == "ok":
            for p in sorted(got, key=lambda p: (p["ts"], p["tx"])):
                rc, ep = rpc.receipt(p["tx"])
                row = classify_print({**p, "stratum": "h10", "market_id": mid}, rc, ep, tokens, hasher, tps)
                rows.append([p["ts"], p["idx"], p["side"], p["price"], p["size"], row["receipt_status"], row["match_status"], row["t1_side"], row["t1_idx"],
                             row["t2_status"], row["fill_type"]])
            rec["n_receipt_prints"] = len(rows)
            n_receipt_prints += len(rows)
            fp_ = fr.rdir / "prints" / f"{mid}.csv.gz"
            fr.budget.write_gz_csv(fp_, cols, rows)
            fr.record_file(fp_)
        _append(fr.rdir / "progress.jsonl", rec)
        done[mid] = rec
    fr.counts.update({"markets": len(smp), "receipt_prints": n_receipt_prints, "capped": sum(1 for x in done.values() if x["status"] == "capped")})
    m = fr.manifest(None, {"status": "sign_fetch_complete", "complete": True, "rpc": rpc.stats()})
    m["status"] = "sign_fetch_complete"
    return m


# =====================================================================================================================================
# Rules
# =====================================================================================================================================


def declared() -> dict:
    from . import cb9_pyth as py  # noqa: PLC0415

    return {
        "family": "CB9-S (CH79), CREATIVE_BATCH_9.md CB9-S; collection rules fixed before the first receipt (q0181)",
        "endpoints": {"order": list(ENDPOINTS), "rps": RPC_RPS, "attempts_per_endpoint": RPC_ATTEMPTS_PER_ENDPOINT,
                      "unavailable": "after every endpoint failed twice (HTTP != 200, RPC error, unparseable, null result); counted, never repaired",
                      "method": "eth_getTransactionReceipt (keyless JSON-RPC POST)", "used_by_other_jobs": False},
        "contracts": {"ctf": CTF, "exchanges_v1": list(EXCHANGES_V1), "exchanges_v2": list(EXCHANGES_V2), "neg_risk_adapter": NEG_RISK_ADAPTER,
                      "verification": "v1 and CTF from Polymarket's published contracts list; v2 from the section 0.3 probe; re-verify before commit (open item)"},
        "topics": {"signatures": SIG, "pinned_full": PINNED_TOPICS, "pinned_prefix": PINNED_TOPIC_PREFIXES, "computed": topics(), "pins_ok": topic_pins_ok()["ok"],
                   "keccak": "local Keccak-256 (Ethereum padding)"},
        "layouts": {k: [list(p) for p in v] for k, v in PARAMS.items()}, "indexed_rule": "leading len(topics) - 1 parameters; data length must equal the rest",
        "side_enum_v2": {str(k): v for k, v in SIDE_ENUM_V2.items()}, "amount_decimals": AMOUNT_DECIMALS,
        "shares": "BUY: taker amount; SELL: maker amount (both eras)",
        "match": "OrdersMatched on a pinned exchange whose takerOrderMaker equals the print's proxyWallet (compared as the strict-key HMAC, in memory) and whose "
                 f"token is the print's asset or its complement; several -> those with share amount = size within {SIZE_TOL}; zero or several remaining -> unmatched",
        "t1": "v2: side enum + tokenId of the matched OrdersMatched; v1: BUY of takerAssetId if makerAssetId = 0, else SELL of makerAssetId",
        "t2": "net ERC-1155 TransferSingle/TransferBatch flow (CTF contract) of the pair's tokens to (BUY) / from (SELL) the taker address; one token non-zero, else "
              "ambiguous / absent",
        "source_gate": {"t1_eq_t2_min": SOURCE_GATE_T1T2, "comparison": "side and token"},
        "yes_sign": "+1 for BUY of outcome 0 or SELL of outcome 1, -1 otherwise; primary A_yes = API sign == T1 sign; A_tok (side and token) reported",
        "fill_type": "receipt segment after the previous OrdersMatched up to the matched one: normal / mint (complementary BUYs + PositionSplit) / merge "
                     "(complementary SELLs + PositionsMerge) / mixed / unknown",
        "samples": {"seeds": SEEDS, "windows": WINDOWS, "n_markets": N_MARKETS, "prints_per_market": PRINTS_PER_MARKET, "max_per_event": MAX_PER_EVENT,
                    "min_volume": S0_MIN_VOLUME, "pages": S0_PAGES, "print_limit": PRINT_LIMIT,
                    "frame": f"Gamma closed and active, endDate >= window start, startDate < window end, volumeNum >= {S0_MIN_VOLUME:g}; end-date windows of "
                             f"{FRAME_SPLIT_DAYS} d (one window beyond 400 d), bisected on the offset cap down to {FRAME_MIN_WINDOW_S:g} s",
                    "feed_side": "S0b: pmxt last_trade_price side by (tx, asset) for prints in [13Z, 14Z); 'unmatched' there without an event; 'not_measured' elsewhere (ruling (c))",
                    "stall": "a failed smoke criterion for the stratum's era -> terminal not_run_source, label 'not testable (source)', exit 0 (M5)",
                    "s0c_drops": "CB7 q0141 key file (ids + event / neg-risk / series keys) + ids of every committed seal copy at q0181's start",
                    "s0a_drops": "none (section 1.3)", "s0b": f"{N_PRINTS_TARGET} K/D SCREEN prints, markets in seeded order, <= {PRINTS_PER_MARKET} per market; HOLDOUT refused",
                    "capped_market": "a market whose window is still full after 5 pages is unavailable (counted); no replacement market is drawn",
                    "no_replacement": "a sampled market with fewer than 4 prints contributes what it has; no replacement",
                    "liq_tercile": "terciles of Gamma volumeNum among the stratum's sampled markets", "price_bands": [list(b) for b in PRICE_BANDS],
                    "stored": PRINT_COLUMNS, "notional": "size x price, the declared weight of the notional-weighted agreement (round-1 addition)"},
        "census": {"columns": list(CENSUS_COLUMNS_S), "forbidden": list(CENSUS_FORBIDDEN_S), "gate_GS": {"match_rate": GS_MATCH_RATE, "min_matched": GS_MIN_MATCHED}},
        "decision": {"near_truth": {"q_hat": NEAR_TRUTH_Q, "q_lb": NEAR_TRUTH_LB}, "minor": {"q_hat": MINOR_Q, "q_wc": MINOR_QWC},
                     "material": f"q_hat < {MINOR_Q} or q_wc < {MINOR_QWC}", "q_lb": f"min(market-cluster bootstrap {LB_PERCENTILE}th percentile, Wilson {WILSON_CONF} on markets)",
                     "q_wc": "every sampled print without a match (unmatched or receipt unavailable) scored as a disagreement", "era_map": ERA_MAP,
                     "gs_fail": "not testable (source); mapped results unverified; never inherited", "pooled": "descriptive only"},
        "smoke": {"version": SMOKE_VERSION, "receipts_per_era": SMOKE_RECEIPTS_PER_ERA, "min_decoded_t1_eq_t2": SMOKE_MIN_DECODED, "era_days": SMOKE_ERA_DAYS,
                  "max_markets_per_era": SMOKE_MAX_MARKETS_PER_ERA, "draw": "markets in seeded order until 20 distinct receipts (tx hash), cap 40 markets", "prints_per_market": SMOKE_PRINTS_PER_MARKET, "min_volume": SMOKE_MIN_VOLUME, "seed": SMOKE_SEED,
                  "max_unavailable": SMOKE_MAX_UNAVAILABLE, "unavailable_rule": "more than 2 unavailable receipts in an era -> nothing written, exit 75 (M2)",
                  "per_exchange": "matched and T1 = T2 counts per pinned exchange address, reported (M1)",
                  "yahoo": py.smoke_declared(), "network_failure": "nothing written, exit 75"},
        "s1": {"n_markets": H10_N_MARKETS, "window_h": H10_WINDOW_H, "max_receipt_prints": H10_MAX_RECEIPT_PRINTS, "seed": H10_SEED, "eras": H10_ERA,
               "pages": H10_PAGES, "origin_step_h": S1_ORIGIN_STEP_H, "feature_h": S1_FEATURE_H, "min_prints": S1_MIN_PRINTS, "target_h": S1_TARGET_H,
               "anchor_tol_s": S1_ANCHOR_TOL_S, "ratio": S1_RATIO, "lb_percentile": S1_LB_PERCENTILE,
               "exclusions": "q0182 ids and keys + K/D frame (SCREEN and HOLDOUT) + P frame + S0a/S0b/S0c samples + every market with a pythdata.app resolution source (by rule; a stalled P frame contributes no ids)",
               "rule": "pass iff R_hat >= 1.5 and the 1st percentile of 2,000 event-clustered draws > 1.5; beta_api <= 0 draws count as R <= 1.5"},
    }


def rule_funcs() -> tuple:
    from . import cb9_pyth as py  # noqa: PLC0415

    return (declared, _keccak_f, keccak256, topic, topics, topic_pins_ok, require_topic_pins, httpx_post, RpcClient.__init__, RpcClient._pace, RpcClient.receipt,
            _words, _val, decode_static, decode_transfer_batch, _side_token_v1, _side_token_v2, decode_receipt, match_print, t1_of, t2_of, fill_type, yes_sign,
            price_band, classify_print, parse_print_s, windowed_prints_s, market_row, frame_windows, walk_frame, sample_markets, draw_prints, terciles, tercile_of,
            _hasher, seal_copy_ids, s0_frame_and_sample, sign_audit, _print_rank_key, s0b_sample, _side_str, kd_upstream_stall, kd_s0b_input, feed_label, smoke_receipts, smoke_criterion,
            smoke_ok, census_s, read_census_rows, s0_stratum, s0_screen,
            s1_units, _slope, s1_ratio, h10_exclusions, h10_window, sign_fetch_h10, hb._paged, hb.frame_row, c9.drop_by_keys,
            *py.smoke_rule_funcs())


def iter_dicts(rows: Iterable[list], cols: list[str]) -> Iterator[dict]:
    for r in rows:
        yield dict(zip(cols, r, strict=True))


def utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
