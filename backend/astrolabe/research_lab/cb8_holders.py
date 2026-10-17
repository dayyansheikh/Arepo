# ruff: noqa: E501
"""CB8-H collection (docs/research_lab/CREATIVE_BATCH_8.md CB8-H "Collection", CB8-F, 5.1): q0160 smoke, q0162 daily /holders
snapshot, q0163 windowed prints and capture marks. PROSPECTIVE collection from 2026-10-21; data only, no statistic, no outcome.

Wallets: the Data API ``proxyWallet`` is hashed on parse (``cb8_common.hash_wallet``, strict key, pinned fingerprint); raw
addresses are never stored, logged or returned. Clocks: the snapshot time ``h`` is the request-sent time of the /holders call;
prints are stored for ``ts`` in ``[h, h + 26 h]`` and the analysis uses exits only after ``h + 60 s`` (a later stage).
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import cb6_tail as c6
from . import cb8_common as cm
from . import h5_seal
from . import history_backfill as hb

SMOKE_VERSION = "cb8-holders-smoke-v3"  # v3 (H-v4): oi_absent = OI 0, 2 % rule on failed + nonnumeric. v2: market OI from /oi at t_f (CREATIVE_BATCH_8.md "H v2")
SMOKE_V2_VERSION = "cb8-holders-smoke-v2"
SMOKE_V2_RECORD = {"version": SMOKE_V2_VERSION, "job": "q0160b_cb8_holders_smoke_v2", "result": "FAIL", "criteria_failed": ["h"], "rules_sha256": "b6ac7f7fd773c1656ad96a2b00abb260cfe693a8ee06a0a48798d8d6f3211f57",
                   "n_base": 278705, "oi_states": {"ok": 50387, "oi_absent": 228318, "oi_lookup_failed": 0, "oi_nonnumeric": 0}, "frame_size": 8564,
                   "cause": "82 % of base-frame markets are absent from /oi (no OI listed); the v3 rule counted absence as unavailable"}
SMOKE_V1_VERSION = "cb8-holders-smoke-v1"
SMOKE_V1_RECORD = {"version": SMOKE_V1_VERSION, "job": "q0160_cb8_holders_smoke", "result": "FAIL", "frame_size": 0, "n_requested": 0,
                   "criteria_failed": ["a", "b", "g"], "cause": "empty frame: the sidecar open_interest (Gamma market openInterest) is blank in all rows"}
HOLDERS_URL = "https://data-api.polymarket.com/holders"
OI_URL = "https://data-api.polymarket.com/oi"
SEED_SMOKE = "arepo-cb8-hsmoke-v3"
SEED_DAY_PREFIX = "arepo-cb8-holders-"
N_SMOKE = 20
SMOKE_MIN_OK = 19
N_MAIN = 1500
N_SPORTS = 300
HOLDERS_LIMIT = 20
MIN_OI = 1000.0
OI_BATCH = 60  # condition ids per /oi request (comma-separated; a repeated market= parameter returns only one)
OI_RPS = 4.0
# 2 % rule (fixed 2026-10-17 before any v2 run; reason in SMOKE_DIAGNOSIS_2026-10-17_CB7_CB8H.md section 4): the CB6/CB7 exclusion-key tolerance
# (--max-unverified-key-share 0.02); unavailable OI can reshape a 1,800-market daily sample by at most about 36 markets.
OI_MAX_MISSING_SHARE = 0.02
OI_AGREE_BAND = 0.25  # /oi and a single-market event's OI "agree" if 1/(1+band) <= ratio <= 1+band (units check; drift over hours is far smaller)
OI_MAX_CONSECUTIVE_FAILS = 5
OI_OK, OI_FAILED, OI_ABSENT, OI_NONNUMERIC = "ok", "oi_lookup_failed", "oi_absent", "oi_nonnumeric"
OI_MISSING = (OI_FAILED, OI_ABSENT, OI_NONNUMERIC)
# H-v4 (2026-10-17, CREATIVE_BATCH_8.md "CB8-H amendment H-v4"): oi_absent is "no OI listed" (the venue lists only markets with positive OI), i.e. OI 0,
# which the OI >= MIN_OI rule already excludes. The 2 % rule counts the states in which the OI could not be read.
OI_UNAVAILABLE = (OI_FAILED, OI_NONNUMERIC)
MAX_CAPTURE_AGE_S = 2.5 * 3600
H1_EARLIEST = "2026-10-21T06:00:00Z"
DEPLOY_DELAY_S = 2 * 3600
H1_DAYS = 21
COLLECT_MAX_DAYS = 63
PRINT_WINDOW_H = 26
MARK_WINDOW_H = 30
LAG_H = 30  # a market-day is processed once its captures through h + 30 h exist (design said 28 h; see implementation notes)
PRINT_PAGES = 5
PRINT_LIMIT = 1000
CONC_MIN = 0.5
TOP_STORED = 5
OI_UNITS_RATIO = 1.05
TERCILES = 3
SNAP_RUN, PRINTS_RUN = "snap", "prints"
SNAP_COMPLETE = "holders_collection_complete"
PRINTS_COMPLETE = "holders_prints_complete"
SMOKE_V1_PATH = cm.CB8_DIR / "holders_smoke.json"  # q0160 FAIL (empty frame), write-once, never overwritten
SMOKE_V2_PATH = cm.CB8_DIR / "holders_smoke_v2.json"  # q0160b FAIL (h), write-once, never overwritten
SMOKE_DEFAULT = cm.CB8_DIR / "holders_smoke_v3.json"
HOLDERS_DIR = cm.CB8_DIR / "holders"
SNAP_OUTPUT_CAP_GB = 0.15  # about 1.9 MB a day over 63 days + plans (reviewed cost amendment, CREATIVE_BATCH_8.md section 10)
PRINTS_OUTPUT_CAP_GB = 0.12  # about 0.9 MB a day over 63 days, doubled for the estimate error (section 10)
PAGING_OFFSET = 4000
PIN_DELAY_S = 2 * 3600
ROW_COLS = ["market_id", "condition_id", "event_id", "binary", "closed", "best_bid", "best_ask", "received_utc"]
EXT_COLS = ["accepting_orders", "event_open_interest", "fee_category", "series_slugs"]
HOLDER_COLUMNS = ["market_id", "token_idx", "rank", "wallet_hash", "amount"]
MARKET_COLUMNS = ["market_id", "condition_id", "event_id", "group", "stratum", "oi_tf", "oi_t_f_epoch", "best_bid", "best_ask", "capture_id", "h_epoch",
                  "status", "n_rows", "max_rows_token", "n_tokens", "oi_below_sum"]
PRINT_COLUMNS = ["market_id", "ts", "token_idx", "side", "price", "size", "wallet_hash", "rank", "stored_reason"]
PRINT_MARKET_COLUMNS = ["market_id", "h_epoch", "status", "pages", "n_raw", "n_stored", "malformed", "duplicates", "out_of_window",
                        "missing_wallet", "order_ok", "c0", "c1", "c_max", "stored_all"]
MARK_COLUMNS = ["market_id", "capture_id", "capture_start_utc", "received_utc", "best_bid", "best_ask"]
TRUTHY = ("1", "1.0", "true", "True", "TRUE", "t", "T", "yes")


def declared() -> dict:
    """Everything the collection could otherwise choose after seeing data (CB8 section 1.4)."""
    return {
        "holders": {"url": HOLDERS_URL, "limit": HOLDERS_LIMIT, "rank": "descending amount within token", "snapshot_time": "request-sent time h"},
        "frame": {"source": "latest complete capture (rows.csv.gz + rows_ext.csv.gz), finished <= 2.5 h before the frame build starts",
                  "base_filters": ["binary", "closed false (capture time)", "accepting_orders true (capture time)", "condition id present",
                                   "not weather (fee_category)", "not crypto Up/Down (hb.CB1_UPDOWN_RE on series_slugs)"],
                  "oi_source": {"url": OI_URL, "mode": "EVERY base-frame market, condition ids comma-separated, batches of 60 (repeated market= parameters return one)",
                                "frame_time_t_f": "reply-received time of each batch, stored per batch (plan.oi.t_f_batches) and per market (oi_t_f_epoch); "
                                                  "max t_f must be strictly before every /holders request (asserted at each request)",
                                "filter": f"market OI at t_f >= {MIN_OI:g} (threshold unchanged from v1; its units are unverified unless /oi and "
                                          "single-market event OI agree, smoke criterion e)",
                                "mixed_clocks": "accepting_orders / closed / event OI are capture-time values; the OI is the /oi value at t_f (hours later); "
                                                "c uses OI at t_f, not OI at the snapshot time h",
                                "missing_states": {OI_FAILED: "request failed after retries (3 attempts per batch across chunks) or non-200 reply or reply "
                                                              "that fails the per-batch count/identity assertion",
                                                   OI_ABSENT: "H-v4: requested id missing from an otherwise valid reply = no OI listed (the venue lists only "
                                                              "markets with positive OI; smoke v2 check: 0 of 40 sampled absent markets had any holder, "
                                                              f"all 10 listed small-OI controls did): treated as OI 0, excluded by the OI >= {MIN_OI:g} rule, "
                                                              "counted, never imputed as a value for an eligible market and not part of the 2 % rule",
                                                   OI_NONNUMERIC: "value present but not a finite number >= 0 (strings, null, bool, negative)"},
                                "never": "imputed, zero-filled or carried over from another time",
                                "per_batch_assert": "reply is a list; every returned market was sent (identity, case-insensitive); no duplicate; "
                                                    "count <= ids sent",
                                "network": "a network failure after retries writes nothing (smoke) / leaves the resumable partial (snapshot) and exits 75",
                                "stop_rule": f"more than {OI_MAX_MISSING_SHARE:.0%} of base-frame markets in the oi_lookup_failed or oi_nonnumeric states (oi_absent excluded, H-v4): the smoke FAILs and the day's "
                                             "snapshot stops, recorded 'missed (oi_source)' apart from 'missed (stale capture)'",
                                "stop_rule_reason": "the same tolerance as the CB6/CB7 exclusion-key rule (--max-unverified-key-share 0.02): unavailable OI "
                                                    "cannot reshape a 1,800-market daily sample by more than about 36 markets, and a handful of transient "
                                                    "misses does not stop a day",
                                "sub_reasons": {"day_rolled": "the UTC day changed between chunk start and the plan write (or a /holders request): refused, "
                                                              "the day is 'missed (oi_source)' (before the plan) or closes INCOMPLETE (after it)",
                                                "oi_capture_gone": "the capture pinned for a pending /oi frame vanished and the day ended",
                                                "unfinished_at_day_end": "the /oi frame build ran out of day"},
                                "drop_granularity": "a failed or integrity-violating /oi reply drops its WHOLE batch of up to 60 sorted condition ids at once "
                                                    "(oi_lookup_failed), so missing markets come in batches, not singly",
                                "oi_rps": OI_RPS, "batch": OI_BATCH},
                  "sports": "fee_category == 'sports'", "max_capture_age_s": MAX_CAPTURE_AGE_S},
        "sample": {"n_main": N_MAIN, "n_sports": N_SPORTS, "seed_prefix": SEED_DAY_PREFIX, "seed_smoke": SEED_SMOKE,
                   "strata": "group x market-OI tercile (cut points from that day's /oi frame, OI at t_f)", "allocation": "proportional (hb.allocate_weighted)",
                   "order_within_stratum": "sha256(seed|market_id)", "plan_written_before_first_request": True},
        "dates": {"h1_earliest": H1_EARLIEST, "deploy_delay_s": DEPLOY_DELAY_S, "h1_days": H1_DAYS, "collect_max_days": COLLECT_MAX_DAYS,
                  "h1_start": "first complete capture >= max(h1_earliest, first run + 2 h), pinned in snap/t8_h1_start.json",
                  "collect_max": "t8_h1_start + 63 d; nothing is collected after it", "h2": "pinned by holders-pin-h2 (write-once)"},
        "prints": {"window_h": PRINT_WINDOW_H, "pages": PRINT_PAGES, "limit": PRINT_LIMIT, "taker_only": True, "lag_h": LAG_H,
                   "capped": "market-day unavailable (counted), prints not stored",
                   "stored": f"all prints of market-days with c >= {CONC_MIN:.1f} on either token; else prints by top-{TOP_STORED} holders of either token"},
        "marks": {"window_h": MARK_WINDOW_H, "fields": MARK_COLUMNS, "rule": "YES best bid / ask of each stored market at every complete capture in [h, h + 30 h]"},
        "concentration": "c_j = amount_rank1(j) / max(OI_tf, sum top-20 amounts of j), bounded by 1; OI_tf = the market's /oi value at t_f (the day's frame time), "
                         "not the OI at the snapshot time h",
        "wallet_hash_hex": cm.WALLET_HASH_HEX,
        "smoke": {"version": SMOKE_VERSION, "n": N_SMOKE, "min_ok": SMOKE_MIN_OK, "oi_units_ratio": OI_UNITS_RATIO,
                  "criteria": "a: HTTP 200 >= 19/20; b: grouped by token, outcomeIndex in {0,1}, numeric amount >= 0, proxyWallet present, >= 1 non-empty; "
                              "c: <= 20 rows per token; d: response time; e: OI units label (records the /oi value at t_f, the event OI of single-market events "
                              "and the sum-top-20 ratios; 'units unverified' unless /oi and single-market event OI agree within the band, or if sum top-20 > "
                              f"{OI_UNITS_RATIO} x OI for more than half of the markets); f: strict key fingerprint == pin; g: paging probe; "
                              f"h: /oi source (lookup_failed + nonnumeric share <= {OI_MAX_MISSING_SHARE:.0%} of base-frame markets; oi_absent is OI 0, H-v4). pass = a and b and f and h",
                  "agree_band": OI_AGREE_BAND, "t_f_before_first_holders_request": True, "v1": SMOKE_V1_RECORD, "v2": SMOKE_V2_RECORD,
                  "discloses": "realised frame and stratum sizes against the 1,500 + 300 sample", "output": "counts and ratios only, write-once, holders_smoke_v3.json"},
        "disk": {"snap_cap_gb": SNAP_OUTPUT_CAP_GB, "prints_cap_gb": PRINTS_OUTPUT_CAP_GB},
        "paging": {"offset": PAGING_OFFSET, "rule": "a 400 at offset > 0 is a capped window (unavailable), any other non-200 is a failed request; the smoke probes offsets 0 and 4000"},
        "window2_pin": {"min_delay_s": PIN_DELAY_S, "rule": "T8_H2_start >= max(T8_H1_end, pin time + 2 h); the pin time is recorded"},
        "incomplete_day": "a plan still in progress after UTC midnight is consolidated with what was done and marked <day>.INCOMPLETE.json (n_planned, n_done)",
        "idle": {"heartbeat_s": cm.HEARTBEAT_S, "idle_exit": cm.TEMPFAIL_EXIT},
    }


# ---- capture frame -------------------------------------------------------------------------------------------------------------


def _truthy(v: Any) -> bool:
    return str(v).strip() in TRUTHY


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def is_updown(series_slugs: str) -> bool:
    """Capture rows carry no question text, so the crypto Up/Down exclusion reads the sidecar's series slugs."""
    return bool(hb.CB1_UPDOWN_RE.search(str(series_slugs or "").replace("_", " ")))


def read_capture(cdir: Path) -> Iterator[dict]:
    """Rows of one capture merged with the sidecar by ``market_id`` (streamed; the sidecar columns are held in memory)."""
    cdir = Path(cdir)
    ext: dict[str, dict] = {}
    with gzip.open(cdir / "rows_ext.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ext[r["market_id"]] = {c: r.get(c, "") for c in EXT_COLS}
    with gzip.open(cdir / "rows.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            e = ext.get(r["market_id"])
            yield {**{c: r.get(c, "") for c in ROW_COLS}, **(e if e is not None else {c: None for c in EXT_COLS})}


def holders_frame(rows: Iterator[dict] | list[dict]) -> tuple[list[dict], dict]:
    """The H BASE frame of one capture: binary, open, accepting orders (capture-time fields), condition id present, not weather, not crypto
    Up/Down. There is NO open-interest filter here: market OI comes from the Data API /oi at frame time t_f (``apply_oi``). Reads no outcome.
    ``group`` is ``sports`` iff ``fee_category == 'sports'``. Each entry carries the capture's event OI and the number of markets of its event
    in the capture (``event_n``, for the single-market-event unit check). Returns (base frame, counts of rows dropped per reason)."""
    seen: set[str] = set()
    out: list[dict] = []
    drop: dict[str, int] = {}
    event_n: dict[str, int] = {}

    def no(reason: str) -> None:
        drop[reason] = drop.get(reason, 0) + 1

    for r in rows:
        mid = str(r.get("market_id") or "")
        if not mid or mid in seen:
            no("duplicate_or_blank_id")
            continue
        seen.add(mid)
        eid = str(r.get("event_id") or "")
        if eid:
            event_n[eid] = event_n.get(eid, 0) + 1
        if r.get("accepting_orders") is None:
            no("no_sidecar_row")
        elif not _truthy(r.get("binary")):
            no("not_binary")
        elif _truthy(r.get("closed")):
            no("closed")
        elif not _truthy(r.get("accepting_orders")):
            no("not_accepting_orders")
        elif not str(r.get("condition_id") or ""):
            no("no_condition_id")
        elif str(r.get("fee_category") or "") == "weather":
            no("weather")
        elif is_updown(r.get("series_slugs")):
            no("crypto_updown")
        else:
            out.append({"market_id": mid, "condition_id": str(r["condition_id"]), "event_id": eid,
                        "group": "sports" if str(r.get("fee_category") or "") == "sports" else "main",
                        "event_oi": _num(r.get("event_open_interest")), "best_bid": r.get("best_bid", ""), "best_ask": r.get("best_ask", "")})
    for e in out:
        e["event_n"] = event_n.get(e["event_id"], 0)
    return out, {"n_base": len(out), "dropped": dict(sorted(drop.items()))}


# ---- market OI from the Data API /oi (v2) -------------------------------------------------------------------------------------------------------


def _oi_number(v: Any) -> float | None:
    """A finite number >= 0 (int or float, never bool or string), else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) and f >= 0 else None


def parse_oi_reply(sent: list[str], status: int, data: Any) -> tuple[dict[str, tuple[str, float | None]], dict]:
    """Per-id (state, value) of ONE /oi reply for the ids ``sent``. A non-200 reply, a non-list body, or a reply that fails the per-batch
    assertion (every returned market was sent; no duplicate; no more rows than ids sent) marks the WHOLE batch ``oi_lookup_failed``
    (``integrity_violation`` for the assertion). Otherwise: an id missing from the reply is ``oi_absent``, a value that is not a finite
    number >= 0 is ``oi_nonnumeric``. Nothing is imputed."""
    info = {"http_status": status, "integrity_violation": False, "n_sent": len(sent), "n_returned": 0}
    if status != 200 or not isinstance(data, list):
        info["integrity_violation"] = bool(status == 200)
        return dict.fromkeys(sent, (OI_FAILED, None)), info
    info["n_returned"] = len(data)
    want = {c.lower(): c for c in sent}
    got: dict[str, Any] = {}
    for row in data:
        m = str(row.get("market") or "").lower() if isinstance(row, dict) else ""
        if m not in want or m in got or len(data) > len(sent):
            info["integrity_violation"] = True
            return dict.fromkeys(sent, (OI_FAILED, None)), info
        got[m] = row.get("value")
    out: dict[str, tuple[str, float | None]] = {}
    for c in sent:
        if c.lower() not in got:
            out[c] = (OI_ABSENT, None)
        else:
            v = _oi_number(got[c.lower()])
            out[c] = (OI_OK, v) if v is not None else (OI_NONNUMERIC, None)
    return out, info


def fetch_oi_batch(lim: hb.Limiter, cids: list[str]) -> tuple[dict[str, tuple[str, float | None]], dict]:
    """ONE request ``/oi?market=<cid1>,<cid2>,...`` (<= 60 ids). :class:`RuntimeError` (given up after retries) propagates to the caller."""
    status, data = lim.get(OI_URL, {"market": ",".join(cids)})
    return parse_oi_reply(cids, status, data)


def oi_batches(base: list[dict]) -> list[list[str]]:
    """Distinct condition ids of the base frame in sorted order, in batches of ``OI_BATCH`` (deterministic, so a resumed build re-forms them)."""
    cids = sorted({r["condition_id"] for r in base})
    return [cids[i:i + OI_BATCH] for i in range(0, len(cids), OI_BATCH)]


class _paced:
    """Temporarily set the limiter's pacing to ``rps`` (the /oi frame build runs at up to 4 rps; /holders stays at <= 2 rps)."""

    def __init__(self, lim: hb.Limiter, rps: float) -> None:
        self.lim, self.gap, self.old = lim, 1.0 / min(max(rps, 0.1), OI_RPS), lim.min_gap

    def __enter__(self) -> None:
        self.lim.min_gap = self.gap

    def __exit__(self, *exc: object) -> None:
        self.lim.min_gap = self.old


def run_oi_batches(lim: hb.Limiter, batches: list[list[str]], clock: Callable[[], float], done: dict[int, dict], record: Callable[[int, dict], None] | None = None,
                   *, stop_reason: Callable[[], str | None] | None = None, fails: dict[int, int] | None = None,
                   record_fail: Callable[[int], None] | None = None) -> str | None:
    """Fetch the batches not yet in ``done`` (index -> record ``{i, t_f, http, integrity, v}``; ``v`` is a number or a missing-state string per id
    of the batch). ``t_f`` is the reply-received time. A :class:`RuntimeError` (request failed after retries) is a transient network error:
    without ``fails`` (smoke) it raises :class:`cm.NotNow` (nothing is written); with ``fails`` (snapshot) the batch attempt is counted, and
    the attempt is counted only if a later batch answers (a streak of ``OI_MAX_CONSECUTIVE_FAILS`` failures, or a chunk in which nothing answered, is an
    outage: :class:`cm.NotNow`, nothing counted); after ``MAX_ITEM_ATTEMPTS`` counted attempts the batch's ids are recorded ``oi_lookup_failed``. Returns a stop reason (``stop_reason()``) or None when every batch is done."""
    streak: list[int] = []  # failed batches not yet followed by a success in this chunk

    def commit() -> None:
        for j in streak:
            fails[j] = fails.get(j, 0) + 1  # type: ignore[index]
            if record_fail is not None:
                record_fail(j)
            if fails[j] >= cm.MAX_ITEM_ATTEMPTS:  # type: ignore[index]
                rec = {"i": j, "t_f": clock(), "http": None, "integrity": False, "v": [OI_FAILED] * len(batches[j])}
                if record is not None:
                    record(j, rec)
                done[j] = rec
        streak.clear()

    for i, ids in enumerate(batches):
        if i in done:
            continue
        why = stop_reason() if stop_reason is not None else None
        if why:
            return why
        try:
            states, info = fetch_oi_batch(lim, ids)
        except RuntimeError:
            if fails is None:
                raise cm.NotNow("holders /oi: request failed after retries (network); nothing written, retry later") from None
            streak.append(i)
            if len(streak) >= OI_MAX_CONSECUTIVE_FAILS:  # looks like an outage: the streak is not counted against the batches
                raise cm.NotNow("holders /oi: repeated request failures (network); resumable partial kept, retry later") from None
            continue
        if streak:  # batches that failed while a later batch answered are batch-specific failures: the attempt counts
            commit()
        rec = {"i": i, "t_f": clock(), "http": info["http_status"], "integrity": info["integrity_violation"],
               "v": [states[c][1] if states[c][0] == OI_OK else states[c][0] for c in ids]}
        if record is not None:
            record(i, rec)
        done[i] = rec
    if streak:
        if not done:  # nothing answered in this chunk or before: a network outage, not a source property
            raise cm.NotNow("holders /oi: no request answered (network); nothing written, retry later")
        commit()
    return None


def oi_states(batches: list[list[str]], done: dict[int, dict]) -> dict[str, tuple[str, float | None, float]]:
    """cid -> (state, value, t_f of its batch) from the stored batch records."""
    out: dict[str, tuple[str, float | None, float]] = {}
    for i, ids in enumerate(batches):
        rec = done[i]
        for c, v in zip(ids, rec["v"], strict=True):
            out[c] = (OI_OK, float(v), rec["t_f"]) if not isinstance(v, str) else (v, None, rec["t_f"])
    return out


def oi_summary(base: list[dict], states: dict[str, tuple[str, float | None, float]], batches: list[list[str]], done: dict[int, dict]) -> dict:
    """Counts per base-frame market of each OI state, the missing share, batch counts and t_f (per batch, min, max). Counts only."""
    counts = dict.fromkeys((OI_OK, *OI_MISSING), 0)
    for r in base:
        counts[states[r["condition_id"]][0]] += 1
    n = len(base)
    miss = sum(counts[k] for k in OI_MISSING)
    tfs = [done[i]["t_f"] for i in range(len(batches))]
    return {"n_base": n, "n_batches": len(batches), "states": counts, "n_missing": miss, "missing_share": (miss / n if n else None),
            "n_unavailable": sum(counts[k] for k in OI_UNAVAILABLE), "unavailable_share": (sum(counts[k] for k in OI_UNAVAILABLE) / n if n else None),
            "n_batches_integrity_violation": sum(1 for i in range(len(batches)) if done[i]["integrity"]),
            "t_f_min_epoch": min(tfs) if tfs else None, "t_f_max_epoch": max(tfs) if tfs else None, "t_f_batches": tfs}


def oi_source_ok(summary: dict) -> tuple[bool, str]:
    """The 2 % rule (H-v4): more than ``OI_MAX_MISSING_SHARE`` of base-frame markets in ``OI_UNAVAILABLE`` (lookup failed, integrity violation or
    nonnumeric) or an empty base frame is a failed source. ``oi_absent`` (no OI listed = OI 0) is counted but not part of the rule."""
    if not summary["n_base"]:
        return False, "empty base frame"
    share = sum(summary["states"][k] for k in OI_UNAVAILABLE) / summary["n_base"]
    if share > OI_MAX_MISSING_SHARE:
        return False, f"unavailable share {share:.4f} > {OI_MAX_MISSING_SHARE}"
    return True, "ok"


def apply_oi(base: list[dict], states: dict[str, tuple[str, float | None, float]]) -> tuple[list[dict], dict]:
    """The H frame: base-frame markets whose /oi value (at t_f) is >= 1,000. Markets in a missing state are dropped and counted, never imputed."""
    out: list[dict] = []
    below = 0
    for r in base:
        state, v, tf = states[r["condition_id"]]
        if state != OI_OK:
            continue
        if not (v is not None and v >= MIN_OI):
            below += 1
            continue
        out.append({**r, "oi": v, "oi_t_f": tf})
    return out, {"n_frame": len(out), "n_oi_below_min": below}


def assert_tf_before(t_f_max: float, t_request: float) -> None:
    """Frame time t_f is strictly before the request time of every /holders call (the OI the sample is stratified on pre-dates the snapshot)."""
    if not (t_f_max < t_request):
        raise cm.Refused(f"t_f ordering violated: frame time {t_f_max} is not strictly before the /holders request at {t_request}")


def holders_sample(frame: list[dict], day: str, n_main: int = N_MAIN, n_sports: int = N_SPORTS, seed: str | None = None
                   ) -> tuple[list[dict], dict]:
    """Seeded sample for one UTC day: ``n_main`` non-sports and ``n_sports`` sports markets, stratified by market-OI tercile (OI at t_f; cut
    points from this day's /oi frame), proportional allocation, order within a stratum by sha256(seed|market_id). Reads open interest (a
    frame field fixed at t_f) and ids only."""
    seed = seed or f"{SEED_DAY_PREFIX}{day}"
    chosen: list[dict] = []
    rep: dict = {"seed": seed, "day": day, "groups": {}}
    for group, n in (("main", n_main), ("sports", n_sports)):
        pool = sorted((r for r in frame if r["group"] == group), key=lambda r: (r["oi"], r["market_id"]))
        k = len(pool)
        c1, c2 = (pool[k // TERCILES]["oi"], pool[2 * k // TERCILES]["oi"]) if k else (0.0, 0.0)
        strata: dict[str, list[dict]] = {}
        for r in pool:
            t = 0 if r["oi"] < c1 else (1 if r["oi"] < c2 else 2)
            strata.setdefault(f"{group}|t{t}", []).append(r)
        sizes = {s: len(v) for s, v in strata.items()}
        alloc = hb.allocate_weighted(sizes, dict.fromkeys(sizes, 1.0), n) if sizes else {}
        for s in sorted(strata):
            for r in sorted(strata[s], key=lambda x: hb._rank(seed, x["market_id"]))[: alloc[s]]:
                chosen.append({**{k_: v for k_, v in r.items() if k_ not in ("event_oi", "event_n")}, "stratum": s})
        rep["groups"][group] = {"pool": k, "n": sum(alloc.values()), "target": n, "cuts": [c1, c2], "strata": sizes, "alloc": alloc}
    return chosen, rep


# ---- /holders ------------------------------------------------------------------------------------------------------------------------


def parse_holders(data: Any, key: bytes) -> tuple[list[list], dict]:
    """Rows ``[token_idx, rank, wallet_hash, amount]`` of one /holders reply (rank by descending amount within the token, ties in
    reply order, at most 20 per token) and a shape report. The raw address is hashed here and not kept."""
    info = {"shape_ok": isinstance(data, list), "n_groups": 0, "max_rows_token": 0, "malformed": 0, "blank_wallet": 0, "n_tokens": 0}
    by_idx: dict[int, list[tuple[float, str]]] = {}
    for g in data if isinstance(data, list) else []:
        hs = g.get("holders") if isinstance(g, dict) else None
        if not isinstance(hs, list):
            info["shape_ok"] = False
            continue
        info["n_groups"] += 1
        info["max_rows_token"] = max(info["max_rows_token"], len(hs))
        for h in hs:
            try:
                idx, amt = int(h["outcomeIndex"]), float(h["amount"])
                if idx not in (0, 1) or not (amt >= 0 and math.isfinite(amt)):
                    raise ValueError("bad row")
            except (KeyError, TypeError, ValueError):
                info["malformed"] += 1
                continue
            w = cm.hash_wallet(key, h.get("proxyWallet")) if isinstance(h, dict) else None
            if w is None:
                info["blank_wallet"] += 1
                continue
            by_idx.setdefault(idx, []).append((amt, w))
    rows: list[list] = []
    for idx in sorted(by_idx):
        ordered = sorted(enumerate(by_idx[idx]), key=lambda t: (-t[1][0], t[0]))[:HOLDERS_LIMIT]
        rows.extend([idx, rk + 1, w, amt] for rk, (_, (amt, w)) in enumerate(ordered))
    info["n_tokens"] = len(by_idx)
    info["shape_ok"] = bool(info["shape_ok"] and not info["malformed"] and not info["blank_wallet"])
    return rows, info


def fetch_holders(lim: hb.Limiter, cid: str, key: bytes) -> tuple[list[list], dict]:
    """ONE request ``/holders?market=<cid>&limit=20``. A non-200 reply raises :class:`cm.ApiError` (never "no data")."""
    status, data = lim.get(HOLDERS_URL, {"market": cid, "limit": HOLDERS_LIMIT})
    if status != 200:
        raise cm.ApiError(f"holders status {status}")
    rows, info = parse_holders(data, key)
    info["http_status"] = status
    return rows, info


def concentration(rows: list[list], oi: float) -> dict:
    """``c_j = amount_rank1(j) / max(OI_tf, sum of the top-20 amounts of j)`` per token, bounded by 1 (conservative); ``oi`` is the market's /oi
    value at the day's frame time t_f (not the OI at the snapshot time h). ``oi_below_sum`` is 1 if that OI is below the top-20 sum of any token."""
    out: dict = {"c0": float("nan"), "c1": float("nan"), "oi_below_sum": 0}
    oi_v = oi if isinstance(oi, float) and math.isfinite(oi) else 0.0
    for j in (0, 1):
        amts = [r[3] for r in rows if r[0] == j]
        if not amts:
            continue
        s = sum(amts)
        denom = max(oi_v, s)
        out[f"c{j}"] = min(1.0, max(amts) / denom) if denom > 0 else float("nan")
        if oi_v < s:
            out["oi_below_sum"] = 1
    return out


# ---- smoke (q0160) ------------------------------------------------------------------------------------------------------------


def smoke_verdict(n_ok: int, n_requested: int, shape_ok: bool, n_nonempty: int, max_rows: int, f_ok: bool, n_oi_over: int, n_oi_known: int,
                  oi_ok: bool = True, n_cmp: int = 0, n_agree: int = 0) -> dict:
    a = bool(n_requested >= N_SMOKE and n_ok >= SMOKE_MIN_OK)
    b = bool(shape_ok and n_nonempty >= 1 and n_requested >= N_SMOKE)
    c = bool(max_rows <= HOLDERS_LIMIT)
    agree = bool(n_cmp >= 1 and n_agree * 2 > n_cmp)
    over = bool(n_oi_known and n_oi_over * 2 > n_oi_known)
    label = "units consistent" if (agree and not over) else "units unverified"
    return {"a": a, "b": b, "c": c, "e_label": label, "f": bool(f_ok), "h": bool(oi_ok), "pass": bool(a and b and f_ok and oi_ok)}


def smoke_pick(frame: list[dict], n: int = N_SMOKE, seed: str = SEED_SMOKE) -> list[dict]:
    return sorted(frame, key=lambda r: hb._rank(seed, r["market_id"]))[:n]


def paging_probe(lim: hb.Limiter, cid: str, clock: Callable[[], float] = time.time) -> dict:
    """Deep-offset probe of the Data API trades paging that q0163 relies on (offset up to 4,000 at limit 1,000): offset 0 must be 200; offset 4,000 is
    200 (ok) or 400 (the venue's offset cap: a capped window, not a failed request). Anything else is unexpected. Counts only."""
    now = int(clock())
    out = {}
    for off in (0, PAGING_OFFSET):
        try:
            st, data = lim.get(hb.DATA_TRADES, {"market": cid, "start": now - 30 * 86400, "end": now, "takerOnly": "true", "limit": PRINT_LIMIT, "offset": off})
        except RuntimeError:
            raise cm.NotNow("holders smoke: paging probe failed after retries (network); nothing written, retry later") from None
        out[off] = st
    deep = "ok" if out[PAGING_OFFSET] == 200 else ("offset_capped" if out[PAGING_OFFSET] == 400 else "unexpected")
    return {"offset0_status": out[0], "offset4000_status": out[PAGING_OFFSET], "deep_offset": deep, "pass": bool(out[0] == 200 and deep != "unexpected")}


def holders_smoke(lim: hb.Limiter, key: bytes, base: list[dict], rules_sha: str, fp: str, capture_id: str, *, clock: Callable[[], float] = time.time,
                  oi_rps: float = OI_RPS) -> dict:
    """q0160b (smoke v2). The /oi frame of EVERY base-frame market is built first (batches of 60, ``t_f`` per batch), then 20 markets from the OI >= 1,000
    frame (seed ``arepo-cb8-hsmoke-v3``) get one /holders request each; ``t_f`` is asserted strictly before the first /holders request. Counts and
    ratios only: no market id, no wallet (hashed in memory, dropped), no amount list. A network failure raises :class:`cm.NotNow` (nothing is written)."""
    batches = oi_batches(base)
    done: dict[int, dict] = {}
    with _paced(lim, oi_rps):
        run_oi_batches(lim, batches, clock, done)
    states = oi_states(batches, done)
    summ = oi_summary(base, states, batches, done)
    oi_ok, oi_why = oi_source_ok(summ)
    frame, fcounts = apply_oi(base, states)
    cmp_ratios = [r["oi"] / r["event_oi"] for r in frame if r["event_n"] == 1 and r["event_oi"] == r["event_oi"] and r["event_oi"] > 0]
    n_agree = sum(1 for x in cmp_ratios if 1.0 / (1.0 + OI_AGREE_BAND) <= x <= 1.0 + OI_AGREE_BAND)
    pick = smoke_pick(frame)
    n_ok = n_nonempty = max_rows = 0
    shape_ok = True
    times: list[float] = []
    ratios: list[dict] = []
    n_over = n_known = n_status_bad = 0
    t_first = None
    for r in pick:
        t0 = clock()
        if t_first is None:
            t_first = t0
            assert_tf_before(summ["t_f_max_epoch"], t0)
        try:
            status, data = lim.get(HOLDERS_URL, {"market": r["condition_id"], "limit": HOLDERS_LIMIT})
        except RuntimeError:
            raise cm.NotNow("holders smoke: request failed after retries (network); nothing written, retry later") from None
        times.append(round(clock() - t0, 3))
        if status != 200:
            n_status_bad += 1
            continue
        n_ok += 1
        rows, info = parse_holders(data, key)
        shape_ok = shape_ok and info["shape_ok"]
        n_nonempty += int(bool(rows))
        max_rows = max(max_rows, info["max_rows_token"])
        top = max(sum(x[3] for x in rows if x[0] == j) for j in (0, 1))
        oi_tf, ev = r["oi"], r["event_oi"]
        ev_ok = r["event_n"] == 1 and ev == ev and ev > 0
        n_known += 1
        n_over += int(bool(top > OI_UNITS_RATIO * oi_tf)) if oi_tf > 0 else 0
        ratios.append({"oi_tf": oi_tf, "event_oi_single_market": (ev if ev_ok else None), "sum_top20": top,
                       "sum_top20_over_oi_tf": (top / oi_tf if oi_tf > 0 else None),
                       "sum_top20_over_event_oi": (top / ev if ev_ok else None),
                       "oi_tf_over_event_oi": (oi_tf / ev if ev_ok else None)})
    v = smoke_verdict(n_ok, len(pick), shape_ok, n_nonempty, max_rows, True, n_over, n_known, oi_ok, len(cmp_ratios), n_agree)
    paging = paging_probe(lim, pick[0]["condition_id"], clock) if pick else {"pass": False, "deep_offset": "no_market"}
    _, srep = holders_sample(frame, cm.iso(clock())[:10])
    disclosure = {g: {"pool": d["pool"], "target": d["target"], "realised_n": d["n"], "shortfall": max(0, d["target"] - d["n"]), "strata": d["strata"],
                      "alloc": d["alloc"], "cuts": d["cuts"]} for g, d in srep["groups"].items()}
    oi_report = {k: val for k, val in summ.items() if k != "t_f_batches"}
    return {"smoke_version": SMOKE_VERSION, "rules_sha256": rules_sha, "wallet_key_fingerprint": fp, "capture_id": capture_id,
            "git_commit": hb._git_commit(), "run_utc": cm.iso(clock()), "counts_only": True,
            "criterion_a_http_ok": v["a"], "criterion_b_shape": v["b"], "criterion_c_rows_per_token_le_20": v["c"],
            "criterion_e_oi_units_label": v["e_label"], "criterion_f_key_fingerprint": v["f"], "criterion_g_paging": paging["pass"], "paging": paging,
            "criterion_h_oi_source": v["h"], "oi_source_verdict": oi_why, "pass": v["pass"],
            "n_requested": len(pick), "n_http_ok": n_ok, "n_http_not_ok": n_status_bad, "n_nonempty": n_nonempty,
            "max_rows_per_token": max_rows, "n_oi_over_1_05": n_over, "n_oi_known": n_known,
            "response_time_s": {"median": sorted(times)[len(times) // 2] if times else None, "max": max(times) if times else None},
            "oi_ratios": ratios, "frame_size": len(frame), "frame_counts": fcounts, "oi": oi_report,
            "t_f_asserted_before_first_holders_request": bool(t_first is not None), "first_holders_request_epoch": t_first,
            "event_oi_comparison": {"n_single_market_events_in_frame": len(cmp_ratios), "n_agree": n_agree, "agree_band": OI_AGREE_BAND,
                                    "median_oi_tf_over_event_oi": (sorted(cmp_ratios)[len(cmp_ratios) // 2] if cmp_ratios else None)},
            "sample_disclosure": disclosure, "clocks": "accepting_orders/closed/event OI: capture time; /oi: t_f (after the capture, before any /holders request)",
            "threshold_units": v["e_label"], "v1_record": SMOKE_V1_RECORD, "v2_record": SMOKE_V2_RECORD}


def smoke_ok(path: Path, rules_sha: str, fp: str, *, require_paging: bool = False) -> dict:
    p = Path(path)
    if not p.exists():
        raise cm.Refused(f"holders smoke result {p} not found; run holders-smoke first (v3: q0160c)")
    try:
        d = json.loads(p.read_text())
    except ValueError as exc:
        raise cm.Refused(f"holders smoke result {p} unreadable") from exc
    if d.get("smoke_version") != SMOKE_VERSION or d.get("rules_sha256") != rules_sha or d.get("wallet_key_fingerprint") != fp:
        raise cm.Refused(f"holders smoke result {p} was made under another version, rules hash or key fingerprint (the v3 PASS under the v4 rules hash is required)")
    if d.get("pass") is not True or d.get("criterion_h_oi_source") is not True:
        raise cm.Refused(f"holders smoke result {p} is a FAIL; H is 'not run (source)'")
    if require_paging and d.get("criterion_g_paging") is not True:
        raise cm.Refused(f"holders smoke result {p}: the paging criterion (g) is not met; q0163 is not run")
    return d


# ---- small stores ---------------------------------------------------------------------------------------------------------------------


def _member(rec: dict) -> bytes:
    return c6._gz_jsonl_member(rec)


def _append(fr: cm.Cb8Run, path: Path, rec: dict) -> None:
    data = _member(rec)
    fr.budget.charge(len(data))
    with Path(path).open("ab") as fh:
        fh.write(data)


def _fails(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                k = json.loads(line)["market_id"]
                out[k] = out.get(k, 0) + 1
    return out


def _read_gz_csv(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def _write_plan(fr: cm.Cb8Run, path: Path, plan: dict) -> None:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(json.dumps(plan, sort_keys=True, default=float).encode())
    fr.budget.write(path, buf.getvalue())


def _read_plan(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.loads(fh.read())


def _day_of(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%d")


def list_captures(snapshot_root: Path) -> list[dict]:
    from . import forecast  # noqa: PLC0415

    out = []
    for c in forecast.list_complete_captures(Path(snapshot_root)):
        st = cm.c4._parse_ts(c.get("started_utc"))
        fin = cm.c4._parse_ts(c.get("finished_utc")) if c.get("finished_utc") else None
        out.append({"capture_id": c.get("capture_id") or Path(c["dir"]).name, "dir": c["dir"], "start": st, "finish": fin if fin is not None else st})
    return sorted((c for c in out if c["start"] is not None), key=lambda c: c["start"])


# ---- windows and pins -------------------------------------------------------------------------------------------------------------------


def start_gate(root: Path, now: float) -> tuple[float, float]:
    """(not-before epoch, first-run epoch). The first run is recorded write-once in ``<root>/deployment.json``."""
    dp = Path(root) / "deployment.json"
    if not dp.exists():
        try:
            cm.write_once_json(dp, {"first_run_epoch": now, "first_run_utc": cm.iso(now), "rule": "T8_H1_start >= first run + 2 h"})
        except cm.Refused:
            pass
    first = json.loads(dp.read_text())["first_run_epoch"]
    return max(cm.ep(H1_EARLIEST), first + DEPLOY_DELAY_S), first


def read_pins(root: Path) -> dict:
    p = Path(root) / SNAP_RUN / "t8_h1_start.json"
    return json.loads(p.read_text()) if p.exists() else {}


def pin_h2(root: Path, h2_start_epoch: float, now: float | None = None) -> dict:
    """Write-once pin of window 2 (``<root>/h2_pin.json``): ``T8_H2_start`` >= ``T8_H1_end``; ``T8_H2_end`` = start + 21 d. A window 2
    that would end after ``T8_H_collect_max`` is recorded as ``freeze_slip`` (H1-rep 'not run (freeze slip)', counted); collection is
    never extended. The start may not lie earlier than the pin time + 2 h (no pinning onto days already collected); the pin time is recorded."""
    now = time.time() if now is None else now
    pins = read_pins(root)
    if not pins:
        raise cm.Refused("window 1 is not pinned yet (no snapshot has run)")
    if h2_start_epoch < pins["h1_end_epoch"]:
        raise cm.Refused("T8_H2_start is before T8_H1_end")
    if h2_start_epoch < now + PIN_DELAY_S:
        raise cm.Refused("T8_H2_start is earlier than the pin time + 2 h; window 2 is never pinned onto days already collected")
    end = h2_start_epoch + H1_DAYS * cm.DAY
    doc = {"pinned_utc": cm.iso(now), "pinned_epoch": now, "t8_h2_start_utc": cm.iso(h2_start_epoch), "t8_h2_end_utc": cm.iso(end), "h2_start_epoch": h2_start_epoch, "h2_end_epoch": end,
           "freeze_slip": bool(end > pins["collect_max_epoch"]), "collect_max_utc": pins["collect_max_utc"]}
    cm.write_once_json(Path(root) / "h2_pin.json", doc)
    return doc


def collection_end(root: Path) -> float | None:
    """The epoch after which nothing is collected: ``min(T8_H_collect_max, T8_H2_end + 30 h)`` once the pins exist."""
    pins = read_pins(root)
    if not pins:
        return None
    end = pins["collect_max_epoch"]
    p = Path(root) / "h2_pin.json"
    if p.exists():
        end = min(end, json.loads(p.read_text())["h2_end_epoch"] + MARK_WINDOW_H * cm.HOUR)
    return end


def close_incomplete_days(fr: cm.Cb8Run, rdir: Path, today: str) -> list[str]:
    """A day whose plan is still unfinished after its UTC day ended is consolidated with the markets done so far and marked
    ``<day>.INCOMPLETE.json`` (planned / done counts), so no plan or partial file silently keeps consuming the cap."""
    closed = []
    for plan_p in sorted(rdir.glob("*.plan.json.gz")):
        day = plan_p.name[:10]
        if day >= today or (rdir / f"{day}.markets.csv.gz").exists() or (rdir / f"{day}.MISSED.json").exists():
            continue
        plan = _read_plan(plan_p)
        part = rdir / f"{day}.partial.jsonl.gz"
        recs = list(c6.iter_partial(part))
        out = _consolidate_snap(fr, rdir, day, plan, part)
        marker = {"day": day, "reason": "incomplete at day end", "n_planned": len(plan["markets"]), "n_done": len(recs),
                  "n_failed": sum(1 for r in recs if r["status"] == "failed"), "n_empty": sum(1 for r in recs if r["status"] == "empty")}
        fr.budget.write(rdir / f"{day}.INCOMPLETE.json", json.dumps(marker, sort_keys=True).encode())
        fr.counts["days_incomplete"] = fr.counts.get("days_incomplete", 0) + 1
        closed.append(day)
        del out
    return closed


def missed_days(rdir: Path, start_day: str, today: str) -> list[str]:
    out = []
    d = datetime.strptime(start_day, "%Y-%m-%d").date()
    end = datetime.strptime(today, "%Y-%m-%d").date()
    while d < end:
        ds = d.isoformat()
        if not (rdir / f"{ds}.markets.csv.gz").exists() and not (rdir / f"{ds}.MISSED.json").exists():
            out.append(ds)
        d += timedelta(days=1)
    return out


def _oi_fails(path: Path) -> dict[int, int]:
    out: dict[int, int] = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                k = int(json.loads(line)["i"])
                out[k] = out.get(k, 0) + 1
    return out


def close_oi_days(fr: cm.Cb8Run, rdir: Path, today: str) -> list[str]:
    """A day whose /oi frame build was still unfinished when its UTC day ended (no plan yet) is marked 'missed (oi_source)' with the batches done;
    the transient /oi files are removed so they do not hold the disk cap. Nothing is imputed."""
    closed = []
    for hdr_p in sorted(rdir.glob("*.oi.hdr.json")):
        day = hdr_p.name[:10]
        if day >= today:
            continue
        gone_p = rdir / f"{day}.oi.capture_gone.json"
        leftovers = (hdr_p, rdir / f"{day}.oi.partial.jsonl.gz", rdir / f"{day}.oi.fail.jsonl", gone_p)
        if not (rdir / f"{day}.plan.json.gz").exists() and not (rdir / f"{day}.MISSED.json").exists():
            n_done = sum(1 for _ in c6.iter_partial(rdir / f"{day}.oi.partial.jsonl.gz"))
            sub = "oi_capture_gone" if gone_p.exists() else "unfinished_at_day_end"  # the pinned capture vanished vs. the build simply ran out of day
            marker = {"day": day, "kind": "oi_source", "sub_reason": sub, "n_batches_done": n_done,
                      "reason": ("oi_source: the pinned capture of the /oi frame was no longer available and the day ended" if sub == "oi_capture_gone"
                                 else "oi_source: the /oi frame build was unfinished at day end")}
            fr.budget.write(rdir / f"{day}.MISSED.json", json.dumps(marker, sort_keys=True).encode())
            fr.counts["days_missed_oi_source"] = fr.counts.get("days_missed_oi_source", 0) + 1
            closed.append(day)
        for q in leftovers:
            q.unlink(missing_ok=True)
    return closed


# ---- q0162: the daily snapshot ---------------------------------------------------------------------------------------------------------------


def _open(root: Path, run_id: str, transport, kind: str, label: str, params: dict, rules_sha: str, fp: str, disk_cap: int, rps: float,
          budget_min: float | None, sleep, live_check, wall_clock, snapshot_root, health_check, now) -> cm.Cb8Run:
    return cm.open_run(root, run_id, transport, allowed_run_id=run_id, kind=kind, label=label, params={**params, "evidence_role": "prospective"},
                       rules_sha=rules_sha, key_fp=fp, disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep,
                       live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)


def holders_snap(root: Path, transport, *, key: bytes, fp: str, rules_sha: str, smoke_path: Path = SMOKE_DEFAULT, snapshot_root: Path | None = None,
                 captures_fn: Callable[[], list[dict]] | None = None, n_main: int = N_MAIN, n_sports: int = N_SPORTS, rps: float = 2.0,
                 disk_cap: int = int(SNAP_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
                 data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB, wall_clock: Callable[[], float] = time.time, sleep=time.sleep,
                 live_check=None, health_check=None, health_snapshot_root: Path | None = None, read_capture_fn=read_capture,
                 oi_rps: float = OI_RPS) -> dict:
    """One resumable chunk of the daily snapshot. Order of refusals: smoke gate (v2 PASS under the v2 rules hash + fingerprint) -> headroom (exit 75)
    -> sticky end states -> start gate (before the declared start: idle) -> collection end -> missed days -> the day's /oi frame (resumable per
    batch; t_f per batch; a missing share above 2 % ends the day as 'missed (oi_source)') -> the day's plan (written before the first /holders
    request) -> requests (t_f asserted before each) -> consolidation. Idempotent per UTC day."""
    root = Path(root)
    smoke_ok(smoke_path, rules_sha, fp)
    rdir = root / SNAP_RUN
    wait = cm.room_or_idle(rdir, data_dumps, data_dumps_cap_gb, disk_cap, wall_clock())
    if wait is not None:
        return wait
    term = cm.prior_terminal(rdir)
    if term:
        return term
    now = wall_clock()
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("status") == SNAP_COMPLETE:
        return {"stopped": None, "status": SNAP_COMPLETE, "complete": True, "counts": prior.get("counts")}
    not_before, _ = start_gate(root, now)
    if now < not_before:
        return cm.idle(rdir, f"before the declared start {cm.iso(not_before)}", now)
    pins = read_pins(root)
    end = collection_end(root)
    fr = _open(root, SNAP_RUN, transport, "holders_snap", "CB8-H snapshot", {"n_main": n_main, "n_sports": n_sports}, rules_sha, fp, disk_cap,
               rps, budget_min, sleep, live_check, wall_clock, health_snapshot_root, health_check, now)
    if end is not None and now >= end:
        fr.extra_state["ended_utc"] = cm.iso(now)
        m = fr.manifest(None, {"complete": True, "status": SNAP_COMPLETE, "missed_days": sorted(p.stem.split(".")[0] for p in rdir.glob("*.MISSED.json"))})
        m["status"] = SNAP_COMPLETE
        return m
    day = _day_of(now)
    try:
        close_incomplete_days(fr, rdir, day)
        close_oi_days(fr, rdir, day)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    if pins:
        for d in missed_days(rdir, pins["t8_h1_start_utc"][:10], day):
            fr.budget.write(rdir / f"{d}.MISSED.json", json.dumps({"day": d, "kind": "no_snapshot", "reason": "no snapshot was taken that UTC day"}).encode())
            fr.counts["days_missed"] = fr.counts.get("days_missed", 0) + 1
    if (rdir / f"{day}.markets.csv.gz").exists() or (rdir / f"{day}.MISSED.json").exists():
        return cm.idle(rdir, f"{day} already snapshotted", now)
    plan_p = rdir / f"{day}.plan.json.gz"
    hdr_p = rdir / f"{day}.oi.hdr.json"
    oi_part, oi_failp = rdir / f"{day}.oi.partial.jsonl.gz", rdir / f"{day}.oi.fail.jsonl"
    try:
        if plan_p.exists():
            plan = _read_plan(plan_p)
        else:
            caps = (captures_fn or (lambda: list_captures(snapshot_root or cm.c4.SNAPSHOT_ROOT)))()
            if hdr_p.exists():  # resuming this day's /oi frame build on the capture pinned when it started
                hdr = json.loads(hdr_p.read_text())
                cap = next((c for c in caps if c["capture_id"] == hdr["capture_id"]), None)
                if cap is None:
                    gone_p = rdir / f"{day}.oi.capture_gone.json"  # sub-reason evidence for close_oi_days if the day ends this way
                    if not gone_p.exists():
                        fr.budget.write(gone_p, json.dumps({"day": day, "capture_id": hdr["capture_id"], "first_seen_utc": cm.iso(now)}, sort_keys=True).encode())
                    return cm.idle(rdir, "the capture of the pending /oi frame is no longer available; retry later", now, kind="oi_capture_gone")
            else:
                cap = caps[-1] if caps else None
                if cap is None or now - cap["finish"] > MAX_CAPTURE_AGE_S:
                    if (now + 1800) // cm.DAY != now // cm.DAY and pins:  # last half hour of the UTC day: this day is missed
                        fr.budget.write(rdir / f"{day}.MISSED.json", json.dumps({"day": day, "kind": "stale_capture", "reason": "no complete capture <= 2.5 h old"}).encode())
                        fr.counts["days_missed_stale_capture"] = fr.counts.get("days_missed_stale_capture", 0) + 1
                        return fr.manifest("day_missed", {"status": "day_missed", "missed_kind": "stale_capture"})
                    return cm.idle(rdir, "no complete capture <= 2.5 h old; retry later", now, kind="no_fresh_capture")
                if not pins and cap["start"] < not_before:
                    return cm.idle(rdir, "waiting for the first complete capture after the declared start", now)
                fr.budget.write(hdr_p, json.dumps({"day": day, "capture_id": cap["capture_id"], "capture_start_utc": cm.iso(cap["start"]),
                                                   "frame_build_started_utc": cm.iso(now)}, sort_keys=True).encode())
            base, base_counts = holders_frame(read_capture_fn(cap["dir"]))
            batches = oi_batches(base)
            oi_done: dict[int, dict] = {r["i"]: r for r in c6.iter_partial(oi_part)}
            oi_fails = _oi_fails(oi_failp)

            def _record(i: int, rec: dict) -> None:
                _append(fr, oi_part, rec)

            def _record_fail(i: int) -> None:
                with oi_failp.open("a") as fh:
                    fh.write(json.dumps({"i": i}) + "\n")

            with _paced(fr.lim, oi_rps):
                why = run_oi_batches(fr.lim, batches, wall_clock, oi_done, _record, stop_reason=fr.stop_reason, fails=oi_fails, record_fail=_record_fail)
            if why or len(oi_done) < len(batches):
                m = fr.manifest(why or "oi_pending", {"transient": True, "status": "in_progress", "day": day, "oi_batches_done": len(oi_done),
                                                       "oi_batches": len(batches)})
                m["status"] = "in_progress"
                return m
            states = oi_states(batches, oi_done)
            summ = oi_summary(base, states, batches, oi_done)
            if _day_of(wall_clock()) != day:  # the day label is fixed at chunk start: never write day D's plan after UTC midnight
                marker = {"day": day, "kind": "oi_source", "sub_reason": "day_rolled", "reason": "oi_source: the UTC day rolled over before the plan was written",
                          "capture_id": cap["capture_id"], "n_batches": summ["n_batches"]}
                fr.budget.write(rdir / f"{day}.MISSED.json", json.dumps(marker, sort_keys=True).encode())
                fr.counts["days_missed_oi_source"] = fr.counts.get("days_missed_oi_source", 0) + 1
                for q in (hdr_p, oi_part, oi_failp, rdir / f"{day}.oi.capture_gone.json"):
                    q.unlink(missing_ok=True)
                return fr.manifest("day_missed", {"status": "day_missed", "missed_kind": "oi_source", "sub_reason": "day_rolled"})
            oi_ok, oi_why = oi_source_ok(summ)
            if not oi_ok:  # the day stops: recorded apart from a stale capture, nothing imputed
                marker = {"day": day, "kind": "oi_source", "reason": f"oi_source: {oi_why}", "capture_id": cap["capture_id"], "n_base": summ["n_base"],
                          "states": summ["states"], "missing_share": summ["missing_share"], "unavailable_share": summ["unavailable_share"], "n_batches": summ["n_batches"],
                          "n_batches_integrity_violation": summ["n_batches_integrity_violation"], "max_missing_share": OI_MAX_MISSING_SHARE}
                fr.budget.write(rdir / f"{day}.MISSED.json", json.dumps(marker, sort_keys=True).encode())
                fr.counts["days_missed_oi_source"] = fr.counts.get("days_missed_oi_source", 0) + 1
                for q in (hdr_p, oi_part, oi_failp):
                    q.unlink(missing_ok=True)
                return fr.manifest("day_missed", {"status": "day_missed", "missed_kind": "oi_source"})
            frame, frame_oi = apply_oi(base, states)
            sample, srep = holders_sample(frame, day, n_main, n_sports)
            plan = {"day": day, "capture_id": cap["capture_id"], "capture_start_utc": cm.iso(cap["start"]), "frame": {**base_counts, **frame_oi},
                    "oi": summ, "sample_report": srep, "seed": srep["seed"], "markets": sample}
            if not pins:  # pin window 1 with the first plan, before the first /holders request
                h1 = cap["start"]
                pin = {"t8_h1_start_utc": cm.iso(h1), "h1_end_utc": cm.iso(h1 + H1_DAYS * cm.DAY), "collect_max_utc": cm.iso(h1 + COLLECT_MAX_DAYS * cm.DAY),
                       "h1_end_epoch": h1 + H1_DAYS * cm.DAY, "collect_max_epoch": h1 + COLLECT_MAX_DAYS * cm.DAY, "capture_id": cap["capture_id"],
                       "rule": "first complete capture >= max(2026-10-21T06:00Z, first run + 2 h)"}
                fr.budget.write(rdir / "t8_h1_start.json", json.dumps(pin, indent=1, sort_keys=True).encode())
            _write_plan(fr, plan_p, plan)
            for q in (hdr_p, oi_part, oi_failp, rdir / f"{day}.oi.capture_gone.json"):
                q.unlink(missing_ok=True)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    part, failp = rdir / f"{day}.partial.jsonl.gz", rdir / f"{day}.fail.jsonl"
    done: dict[str, dict] = {r["market_id"]: r for r in c6.iter_partial(part)}
    fails = _fails(failp)
    stopped = None
    for mk in plan["markets"]:
        if mk["market_id"] in done:
            continue
        why = fr.stop_reason()
        if why:
            stopped = why
            break
        t_req = wall_clock()
        if _day_of(t_req) != day:  # no /holders row is labelled day D after UTC midnight; the next chunk closes the day as INCOMPLETE
            stopped = "day_rolled"
            break
        assert_tf_before(plan["oi"]["t_f_max_epoch"], t_req)
        h = int(t_req)
        try:
            rows, info = fetch_holders(fr.lim, mk["condition_id"], key)
            rec = {"market_id": mk["market_id"], "h": h, "status": "ok" if rows else "empty", "rows": rows, "info": info}
        except (cm.ApiError, RuntimeError) as exc:
            fails[mk["market_id"]] = fails.get(mk["market_id"], 0) + 1
            with failp.open("a") as fh:
                fh.write(json.dumps({"market_id": mk["market_id"], "error": str(exc)[:120], "h": h}) + "\n")
            if fails[mk["market_id"]] < cm.MAX_ITEM_ATTEMPTS:
                fr.counts["request_failures"] = fr.counts.get("request_failures", 0) + 1
                continue
            rec = {"market_id": mk["market_id"], "h": h, "status": "failed", "rows": [], "info": {"error": str(exc)[:120]}}
        try:
            _append(fr, part, rec)
        except OSError as exc:
            return cm.disk_budget_end(fr, exc)
        done[mk["market_id"]] = rec
        fr.counts[f"n_{rec['status']}"] = fr.counts.get(f"n_{rec['status']}", 0) + 1
    pending = [mk for mk in plan["markets"] if mk["market_id"] not in done and fails.get(mk["market_id"], 0) < cm.MAX_ITEM_ATTEMPTS]
    if stopped or pending:
        m = fr.manifest(stopped or "pending", {"transient": True, "status": "in_progress", "day": day})
        m["status"] = "in_progress"
        return m
    try:
        out = _consolidate_snap(fr, rdir, day, plan, part)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    fr.counts["days_done"] = fr.counts.get("days_done", 0) + 1
    m = fr.manifest(None, {"status": "day_done", "day": day, "day_report": out})
    m["status"] = "day_done"
    return m


def _consolidate_snap(fr: cm.Cb8Run, rdir: Path, day: str, plan: dict, part: Path) -> dict:
    by_id = {mk["market_id"]: mk for mk in plan["markets"]}

    def holder_rows() -> Iterator[list]:
        for rec in c6.iter_partial(part):
            for idx, rank, w, amt in rec["rows"]:
                yield [rec["market_id"], idx, rank, w, amt]

    def market_rows() -> Iterator[list]:
        for rec in sorted(c6.iter_partial(part), key=lambda r: r["market_id"]):
            mk = by_id[rec["market_id"]]
            info = rec.get("info") or {}
            c = concentration(rec["rows"], mk["oi"])
            yield [mk["market_id"], mk["condition_id"], mk["event_id"], mk["group"], mk["stratum"], mk["oi"], mk["oi_t_f"], mk["best_bid"], mk["best_ask"],
                   plan["capture_id"], rec["h"], rec["status"], len(rec["rows"]), info.get("max_rows_token", ""), info.get("n_tokens", ""), c["oi_below_sum"]]

    hp, mp_ = rdir / f"{day}.holders.csv.gz", rdir / f"{day}.markets.csv.gz"
    fr.budget.write_gz_csv(hp, HOLDER_COLUMNS, holder_rows())
    fr.budget.write_gz_csv(mp_, MARKET_COLUMNS, market_rows())  # last: marks the day done
    fr.record_file(hp)
    fr.record_file(mp_)
    fr.file_sha256[f"{day}.plan.json.gz"] = h5_seal.sha256_file(rdir / f"{day}.plan.json.gz")
    part.unlink(missing_ok=True)
    (rdir / f"{day}.fail.jsonl").unlink(missing_ok=True)
    return {"markets": len(by_id), "file_sha256": {hp.name: fr.file_sha256[hp.name], mp_.name: fr.file_sha256[mp_.name]}}


# ---- q0163: windowed prints and capture marks ----------------------------------------------------------------------------------------------------


def capture_marks(captures: list[dict], market_h: dict[str, int], window_s: float = MARK_WINDOW_H * cm.HOUR, read_rows_fn=None
                  ) -> tuple[list[list], dict]:
    """YES best bid / ask of each market at every complete capture whose start lies in ``[h, h + window]`` of that market. Streams each
    capture once. An unreadable capture is counted, never fabricated."""
    out: list[list] = []
    stats = {"captures_used": 0, "captures_unreadable": 0, "captures_available": len(captures),
             "earliest_capture_available_utc": cm.iso(min(c["start"] for c in captures)) if captures else None}
    if not market_h:
        return out, stats
    lo, hi = min(market_h.values()), max(market_h.values()) + window_s
    in_window = [c for c in captures if lo <= c["start"] <= hi]
    stats.update(expected_window_utc=[cm.iso(lo), cm.iso(hi)], captures_in_window=len(in_window),
                 window_start_covered=bool(captures and min(c["start"] for c in captures) <= lo),
                 captures_before_earliest_available=bool(captures and min(c["start"] for c in captures) > lo))
    read = read_rows_fn or (lambda d: _read_gz_csv(Path(d) / "rows.csv.gz"))
    for cap in captures:
        if not (lo <= cap["start"] <= hi):
            continue
        try:
            for r in read(cap["dir"]):
                h = market_h.get(str(r.get("market_id")))
                if h is not None and h <= cap["start"] <= h + window_s:
                    out.append([r["market_id"], cap["capture_id"], cm.iso(cap["start"]), r.get("received_utc", ""), r.get("best_bid", ""), r.get("best_ask", "")])
            stats["captures_used"] += 1
        except (OSError, EOFError, KeyError, csv.Error):
            stats["captures_unreadable"] += 1
    return out, stats


def holders_prints(root: Path, transport, *, key: bytes, fp: str, rules_sha: str, smoke_path: Path = SMOKE_DEFAULT, snapshot_root: Path | None = None,
                   captures_fn: Callable[[], list[dict]] | None = None, lag_h: float = LAG_H, day_pages: int = PRINT_PAGES, rps: float = 2.0,
                   disk_cap: int = int(PRINTS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
                   data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB, wall_clock: Callable[[], float] = time.time, sleep=time.sleep,
                   live_check=None, health_check=None, health_snapshot_root: Path | None = None) -> dict:
    """One resumable chunk of q0163: for the oldest snapshot day whose markets are all at least ``lag_h`` hours old, fetch the windowed
    prints ``[h, h + 26 h]`` per market (capped -> unavailable, counted), store them by the storage rule, then the capture marks."""
    root = Path(root)
    smoke_ok(smoke_path, rules_sha, fp, require_paging=True)
    snap = root / SNAP_RUN
    rdir = root / PRINTS_RUN
    wait = cm.room_or_idle(rdir, data_dumps, data_dumps_cap_gb, disk_cap, wall_clock())
    if wait is not None:
        return wait
    term = cm.prior_terminal(rdir)
    if term:
        return term
    now = wall_clock()
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("status") == PRINTS_COMPLETE:
        return {"stopped": None, "status": PRINTS_COMPLETE, "complete": True, "counts": prior.get("counts")}
    snap_man = json.loads((snap / "manifest.json").read_text()) if (snap / "manifest.json").exists() else {}
    days = sorted(p.name[:10] for p in snap.glob("*.markets.csv.gz")) if snap.exists() else []
    todo = [d for d in days if not (rdir / f"{d}.markets.csv.gz").exists()]
    snap_complete = snap_man.get("status") == SNAP_COMPLETE and snap_man.get("complete") is True
    ready = []
    for d in todo:
        mk = list(_read_gz_csv(snap / f"{d}.markets.csv.gz"))
        if mk and now >= max(int(r["h_epoch"]) for r in mk) + lag_h * cm.HOUR:
            ready.append((d, mk))
    if not ready:
        if snap_complete and not todo:
            fr = _open(root, PRINTS_RUN, transport, "holders_prints", "CB8-H prints", {"lag_h": lag_h}, rules_sha, fp, disk_cap, rps, budget_min, sleep,
                       live_check, wall_clock, health_snapshot_root, health_check, now)
            m = fr.manifest(None, {"complete": True, "status": PRINTS_COMPLETE})
            m["status"] = PRINTS_COMPLETE
            return m
        return cm.idle(rdir, "no snapshot day is old enough for its window to be complete", now)
    day, mkts = ready[0]
    fr = _open(root, PRINTS_RUN, transport, "holders_prints", "CB8-H prints", {"lag_h": lag_h, "day_pages": day_pages}, rules_sha, fp, disk_cap, rps,
               budget_min, sleep, live_check, wall_clock, health_snapshot_root, health_check, now)
    holders: dict[str, list[list]] = {}
    for r in _read_gz_csv(snap / f"{day}.holders.csv.gz"):
        holders.setdefault(r["market_id"], []).append([int(r["token_idx"]), int(r["rank"]), r["wallet_hash"], float(r["amount"])])
    part, failp = rdir / f"{day}.partial.jsonl.gz", rdir / f"{day}.fail.jsonl"
    done = {r["market_id"]: r for r in c6.iter_partial(part)}
    fails = _fails(failp)
    stopped = None
    for r in mkts:
        mid = r["market_id"]
        if mid in done or r["status"] != "ok":
            continue
        why = fr.stop_reason()
        if why:
            stopped = why
            break
        h = int(r["h_epoch"])
        try:
            prints, info = cm.windowed_prints(fr.lim, r["condition_id"], h, h + int(PRINT_WINDOW_H * cm.HOUR), day_pages, key, limit=PRINT_LIMIT)
        except (cm.ApiError, RuntimeError) as exc:
            fails[mid] = fails.get(mid, 0) + 1
            with failp.open("a") as fh:
                fh.write(json.dumps({"market_id": mid, "error": str(exc)[:120]}) + "\n")
            if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                fr.counts["request_failures"] = fr.counts.get("request_failures", 0) + 1
                continue
            rec = {"market_id": mid, "status": "failed", "info": {"error": str(exc)[:120]}, "stored": [], "c": {"c0": None, "c1": None}}
        else:
            hrows = holders.get(mid, [])
            c = concentration(hrows, _num(r["oi_tf"]))
            stored_all = bool(max([x for x in (c["c0"], c["c1"]) if x == x] or [0.0]) >= CONC_MIN)
            rank_of = {(x[0], x[2]): x[1] for x in hrows}
            top5 = {x[2] for x in hrows if x[1] <= TOP_STORED}
            stored = []
            if info["capped"]:
                status = "capped"
            else:
                status = "ok"
                for p in prints:
                    if stored_all or p["wallet"] in top5:
                        stored.append([mid, p["ts"], p["idx"], p["side"], p["price"], p["size"], p["wallet"] or "", rank_of.get((p["idx"], p["wallet"]), 0),
                                       "all" if stored_all else "top5"])
            rec = {"market_id": mid, "status": status, "info": info, "stored": stored, "c": c, "stored_all": stored_all, "h": h}
        try:
            _append(fr, part, rec)
        except OSError as exc:
            return cm.disk_budget_end(fr, exc)
        done[mid] = rec
        fr.counts[f"n_{rec['status']}"] = fr.counts.get(f"n_{rec['status']}", 0) + 1
    need = [r for r in mkts if r["status"] == "ok" and r["market_id"] not in done and fails.get(r["market_id"], 0) < cm.MAX_ITEM_ATTEMPTS]
    if stopped or need:
        m = fr.manifest(stopped or "pending", {"transient": True, "status": "in_progress", "day": day})
        m["status"] = "in_progress"
        return m
    try:
        out = _consolidate_prints(fr, rdir, day, mkts, part, captures_fn or (lambda: list_captures(snapshot_root or cm.c4.SNAPSHOT_ROOT)))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    fr.counts["days_done"] = fr.counts.get("days_done", 0) + 1
    m = fr.manifest(None, {"status": "day_done", "day": day, "day_report": out})
    m["status"] = "day_done"
    return m


def _consolidate_prints(fr: cm.Cb8Run, rdir: Path, day: str, mkts: list[dict], part: Path, captures_fn) -> dict:
    market_h: dict[str, int] = {}
    summary: list[list] = []
    for rec in sorted(c6.iter_partial(part), key=lambda r: r["market_id"]):
        info, c = rec["info"], rec["c"] or {}
        n_stored = len(rec["stored"])
        if rec["status"] == "ok" and (n_stored or rec.get("stored_all")):
            market_h[rec["market_id"]] = rec["h"]
        summary.append([rec["market_id"], rec.get("h", ""), rec["status"], info.get("pages", ""), info.get("n_raw", ""), n_stored, info.get("malformed", ""),
                        info.get("duplicates", ""), info.get("out_of_window", ""), info.get("missing_wallet", ""), info.get("order_ok", ""),
                        c.get("c0"), c.get("c1"), max([x for x in (c.get("c0"), c.get("c1")) if isinstance(x, float) and x == x] or [""]),
                        int(bool(rec.get("stored_all")))])
    for r in mkts:  # snapshot markets without a usable /holders reply have no prints request; they are listed, never dropped silently
        if r["status"] != "ok":
            summary.append([r["market_id"], r["h_epoch"], f"snapshot_{r['status']}", "", "", 0, "", "", "", "", "", None, None, "", 0])
    summary.sort(key=lambda x: x[0])

    def print_rows() -> Iterator[list]:
        for rec in sorted(c6.iter_partial(part), key=lambda r: r["market_id"]):
            yield from rec["stored"]

    pp, kp, sp = rdir / "prints" / f"{day}.csv.gz", rdir / "marks" / f"{day}.csv.gz", rdir / f"{day}.markets.csv.gz"
    fr.budget.write_gz_csv(pp, PRINT_COLUMNS, print_rows())
    marks, mstats = capture_marks(captures_fn(), market_h)
    marks.sort()
    fr.budget.write_gz_csv(kp, MARK_COLUMNS, marks)
    wp = rdir / "marks" / f"{day}.window.json"  # expected capture window and the earliest capture still available (retention gaps are counted)
    fr.budget.write(wp, json.dumps({"day": day, **mstats}, indent=1, sort_keys=True).encode())
    fr.record_file(wp)
    fr.budget.write_gz_csv(sp, PRINT_MARKET_COLUMNS, summary)  # last: marks the day done
    for p in (pp, kp, sp):
        fr.record_file(p)
    part.unlink(missing_ok=True)
    (rdir / f"{day}.fail.jsonl").unlink(missing_ok=True)
    return {"markets": len(summary), "stored_markets": len(market_h), "marks": len(marks), **mstats}


def rule_funcs() -> tuple:
    return (declared, is_updown, read_capture, holders_frame, holders_sample, parse_holders, fetch_holders, concentration, smoke_verdict, smoke_pick,
            holders_smoke, smoke_ok, parse_oi_reply, fetch_oi_batch, oi_batches, run_oi_batches, oi_states, oi_summary, oi_source_ok, apply_oi,
            assert_tf_before, _oi_number, _paced, _oi_fails, close_oi_days, start_gate, pin_h2, collection_end, missed_days, capture_marks, holders_snap, holders_prints, _consolidate_snap,
            _consolidate_prints, list_captures, hb._rank, hb.allocate_weighted)
