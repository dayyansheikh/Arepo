# ruff: noqa: E501
"""CB11-W: whitelisted-proposer clocks (docs/research_lab/CREATIVE_BATCH_11.md section CB11-W, round-1 revision).

W1 forecasts the wait ``close_epoch - end_epoch`` (log hours, capped at 21 d) from schedule features known at the scheduled end against a category-median
baseline B0 and a rolling recent-lag baseline B1; W2 is a decided carry (next transaction at or after tau + 60 s, hourly capital-time measure, capacity-capped
pool gate). Population = the h2_main and h3_power ``frame.csv.gz`` metadata columns (sha256 pinned), every closed row open at its scheduled end (NO status
filter; ``uma_status`` and ``outcome_prices`` only through the guarded accessors), W key rule (market id and event id).

Guards: the frame reader opens only the pinned frame files and yields only the whitelisted columns; the W_hold rows go to ``w/hold/`` (sealed listing) and are
loaded only by ``rep-W``; screen-window and gap targets live in a guarded file opened only by screen / rep; W_fit waits are stored in the unit file (they are
fit features, determined before W_screen); no census path receives a W_screen or W_hold wait, an outcome or a P&L. No ``side`` field and no wallet is read.
"""

from __future__ import annotations

import csv
import gzip
import heapq
import json
import math
import time
from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb11_common as c11
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow

HOUR = 3600.0
DAY = 86400.0
W_FIT = ("2025-10-01", "2026-02-08")
W_SCREEN = ("2026-03-01", "2026-07-01")
W_HOLD = ("2026-07-01", "2026-09-10")
W_EXCLUDED_DATES = ("2026-09-10", "2026-09-11")
REP_FIT_END = "2026-06-09"
CAP_S = 21 * DAY
FLOOR_S = 60.0
F7_DAYS = 14
F7_MIN = 20
RARE_MIN = 200
W_SPORTS_IN_PRIMARY = False
PRIMARY_EXCLUDED = ("sports", "crypto")
SEED_SAMPLE = "arepo-cb11-w-sample"
SEED_HOLD = "arepo-cb11-w-hold"
SEED_CENSOR = "arepo-cb11-w-censor"
N_SAMPLE_SCREEN = 4000
N_SAMPLE_HOLD = 3000
MAX_PER_EVENT = 3
N_CENSOR_WINDOWS = 300
CENSOR_PAGE = 100
CENSOR_PAGES = 5
CENSOR_MAX_SHARE = 0.02
CENSOR_CONF = 0.95
CENSOR_MATCH_MIN = 0.99  # share of a frame's closed rows (ends in [W_fit start, W_hold end)) that fall in the reconstructed 15-minute windows; below -> q0222 stalls (N8)
AVAIL_MIN = 0.60  # design 2.6(iv): available share of eligible units / windows below this is "not testable (availability)"
SKLEARN_PIN = "1.9.1"
NUMPY_PIN = "2.4.6"
MODEL_PARAMS = {"loss": "absolute_error", "learning_rate": 0.05, "max_iter": 400, "max_leaf_nodes": 31, "min_samples_leaf": 200, "l2_regularization": 1.0,
                "early_stopping": False, "random_state": 1111}
FEATURES = ("f1_hour_ny", "f2_weekday_ny", "f3_placeholder", "f4_category", "f5_neg_risk", "f6_ln_life_days", "f7_recent_lag")
SCHED = (0, 1, 2)  # feature columns removed in the schedule attribution refit
W1_FLOOR_B0 = 0.20
W1_FLOOR_B1 = 0.10
W1_SUBSET_R = 0.10
ATTR_SCHED_MIN = 0.10
H_W = 0.005
H_W_ROBUST = 0.010
UNFILLED_NO_TRADE = "unfilled_no_trade_before_close"
UNFILLED_OUTSIDE = "unfilled_outside_window"
UNFILLED = (UNFILLED_NO_TRADE, UNFILLED_OUTSIDE)
DECIDED_HI = 0.95
DECIDED_LO = 0.05
TRIG_FROM_S = 300.0
TRIG_TO_S = 3600.0
TRIG_TO_ROBUST_S = 1800.0
LATENCY_S = 60.0
NO_ROOM = 0.995
TX_BEFORE_S = 6 * HOUR
TX_AFTER_S = 6 * HOUR
COVER_AFTER_S = 3600.0
HOLD_FLOOR_H = 2.0
HOLD_FLOOR_ROBUST_H = 6.0
LIVENESS_H = 1.0
W2_NET_FLOOR = 0.003
W2_RANN_FLOOR = 0.10
RF_RATE = 0.045
POOL_USD = 10000.0
POOL_ALT = (1000.0, 100000.0)
POOL_EXCESS_FLOOR = 0.10
S_MAX_HOURS = 6.0
ATTR_RANN_MULT = 1.5
ATTR_NET_SLACK = 0.001
TAIL_FLOOR = 0.003
GW = {"units": 5000, "dates": 90, "categories": 6, "fit_min": 200}
GW2 = {"units": 300, "events": 100, "dates": 60}
COVER_MIN = 0.90
MDE_Z = 2.326 + 0.842
MDE_SD_W2 = 0.12
MDE_DEFF_W2 = 2.0
MDE_SD_W1 = 0.02
MDE_G_REF = 120  # end-dates at which the declared W1 bootstrap SD (0.02) holds; the census rescales the SD by sqrt(G_REF / end-dates in W_screen) (N6)
DATA_PAGE_LIMIT = 1000
DATA_PAGES = 4
TAKER_ONLY = "true"
WPRINTS_OUTPUT_CAP_GB = 0.03
WFRAME_OUTPUT_CAP_GB = 0.02
CENSOR_OUTPUT_CAP_GB = 0.001
# W chain v2 (q0222b-q0231b, 2026-10-19): the q0222 / q0224 run dirs ("w", "w_censoring") and census_W.json hold the terminal stall caused by the half-open window
# defect (section 11.3) and are never rewritten; the re-run writes new creative_batch11 dirs. history/h11_wprints is the canonical id source of the CB12-CB15 exclusion
# readers, so the prints run stays there and writes NEW files only, under its own manifest (c11.MANIFEST_NAMES: manifest_b.json); the q0223 stall manifest.json is
# never read as the run's state and never rewritten.
FRAME_RUN = "w_b"
CENSOR_RUN = "w_censoring_b"
PRINTS_RUN = H11 = c11.H11_WPRINTS
SUPERSEDED_RUNS = ("w", "w_censoring")  # q0222 / q0224 (stalled on the defect); read by nothing
MARKET_IDS_FILE = "markets.csv.gz"  # history/h11_wprints/markets.csv.gz: ids of every sampled W2 market (both splits), the file the CB12-CB15 id readers open
FRAME_STATUS = "w_frame_complete"
PRINTS_STATUS = "w_prints_complete"
CENSOR_STATUS = "w_censoring_complete"
FRAME_SEEDS = {"h2_main": ("arepo-h2", 270), "h3_power": ("arepo-h3-power", 365)}  # read-only host inspection 2026-10-17 (manifest params); verified at q0222 from the manifest
FEE_RATE = {"politics": 0.04, "finance": 0.04, "tech": 0.04, "mentions": 0.04, "economics": 0.05, "culture": 0.05, "weather": 0.05, "unknown": 0.05, "other": 0.05,
            "sports": 0.05, "crypto": 0.07, "geopolitics": 0.0, "other:zero_fees": 0.0}
W_COLUMNS = ("market_id", "event_id", "fee_category", "neg_risk", "start_epoch", "end_epoch", "close_epoch", "closed", "token0", "token1", "condition_id")
GUARDED_FRAME_COLUMNS = ("market_id", "outcome_prices", "uma_status")
UNIT_COLUMNS = ["market_id", "event_id", "fee_category", "src", "window", "end_epoch", "start_epoch", "f1", "f2", "f3", "f5", "f6", "f7", "L_fit"]
SAMPLE_COLUMNS = ["market_id", "event_id", "fee_category", "condition_id", "token0", "token1", "end_epoch", "split"]
TARGET_COLUMNS = ["market_id", "L", "close_epoch"]
OUTCOME_COLUMNS = ["market_id", "outcome_prices", "uma_status"]
TX_COLUMNS = ["market_id", "ts", "price", "size"]
MARKET_COLUMNS = ["market_id", "split", "t", "status", "oldest_ts", "truncated", "n_prints", "n_nohash", "n_tx", "covered"]
WINDOW_COLUMNS = ["frame", "day", "k", "a", "b", "set", "n_frame_closed"]
GUARDED_NAMES = ("targets_guarded.csv.gz", "targets_guarded_hold.csv.gz", "outcomes_guarded.csv.gz", "outcomes_guarded_hold.csv.gz")
HOLD_ONLY = ("targets_guarded_hold.csv.gz", "outcomes_guarded_hold.csv.gz")
CENSUS_FORBIDDEN = ("L", "wait", "close_epoch", "outcome_prices", "uma_status", "net", "pnl", "targets_guarded")
SEAL_COPY_NAME = "cb11_w_hold_SEAL.json"
HOLD_DIR = "hold"


def _ep(d: str) -> float:
    return cm.ep(d + "T00:00:00Z")


E_FIT = (_ep(W_FIT[0]), _ep(W_FIT[1]))
E_SCREEN = (_ep(W_SCREEN[0]), _ep(W_SCREEN[1]))
E_HOLD = (_ep(W_HOLD[0]), _ep(W_HOLD[1]))
E_GAP = (E_FIT[1], E_SCREEN[0])
E_START = E_FIT[0]
E_EXCL = (_ep(W_EXCLUDED_DATES[0]), _ep(W_EXCLUDED_DATES[1]) + DAY)


def window_of(end_epoch: float) -> str | None:
    """'fit' / 'gap' / 'screen' / 'hold' for a scheduled end inside W_fit ∪ gap ∪ W_screen ∪ W_hold, else None (the excluded dates are None too)."""
    if not math.isfinite(end_epoch):
        return None
    if E_EXCL[0] <= end_epoch < E_EXCL[1]:
        return None
    if E_FIT[0] <= end_epoch < E_FIT[1]:
        return "fit"
    if E_GAP[0] <= end_epoch < E_GAP[1]:
        return "gap"
    if E_SCREEN[0] <= end_epoch < E_SCREEN[1]:
        return "screen"
    if E_HOLD[0] <= end_epoch < E_HOLD[1]:
        return "hold"
    return None


def is_primary(cat: str) -> bool:
    return W_SPORTS_IN_PRIMARY or str(cat).split(":")[0] not in PRIMARY_EXCLUDED


def wait_L(end: float, close: float) -> float:
    """Target ``L = ln(min(max(close - end, 60 s), 21 d) / 1 h)`` (log hours)."""
    return math.log(min(max(close - end, FLOOR_S), CAP_S) / HOUR)


def month_of(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m")


def date_of(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%d")


# =====================================================================================================================================
# Frame reader (whitelisted columns; guarded accessor)
# =====================================================================================================================================


def _open_frame(path: Path, sha256: str | None):
    from . import h5_seal  # noqa: PLC0415

    p = Path(path)
    if p.name != "frame.csv.gz" or p.parent.name not in c11.FRAME_RUN_IDS:
        raise Refused(f"the W reader opens only <history>/(h2_main|h3_power)/frame.csv.gz, not {p}")
    if sha256 is not None and h5_seal.sha256_file(p) != sha256:
        raise Refused(f"{p} sha256 differs from the pin; refusing")
    csv.field_size_limit(10**9)
    return gzip.open(p, "rt", encoding="utf-8", newline="")


def read_frame_rows(path: Path, *, sha256: str | None = None) -> Iterator[dict]:
    """Stream ONLY the whitelisted columns (``W_COLUMNS``) of a pinned frame file. ``outcome_prices`` / ``uma_status`` and every other column are dropped
    on read (they never enter a row dict), so no census path can reach them."""
    with _open_frame(path, sha256) as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in W_COLUMNS if c not in (rd.fieldnames or [])]
        if missing:
            raise Refused(f"{path} lacks whitelisted columns {missing}")
        for r in rd:
            yield {c: r[c] for c in W_COLUMNS}


def iter_frame_guarded(path: Path, *, sha256: str | None = None) -> Iterator[dict]:
    """The GUARDED accessor: (market_id, outcome_prices, uma_status) rows. Called only by ``w_frame`` to route them to the guarded files."""
    with _open_frame(path, sha256) as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in GUARDED_FRAME_COLUMNS if c not in (rd.fieldnames or [])]
        if missing:
            raise Refused(f"{path} lacks guarded columns {missing}")
        for r in rd:
            yield {c: r[c] for c in GUARDED_FRAME_COLUMNS}


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def collect_frame(rows: Iterable[dict]) -> dict[str, tuple]:
    """market_id -> (event_id, fee_category, neg_risk, start, end, close, closed, has_tokens). Compact tuples (no token strings)."""
    out: dict[str, tuple] = {}
    for r in rows:
        mid = str(r["market_id"])
        out[mid] = (str(r["event_id"]), str(r["fee_category"]), int(_f(r["neg_risk"]) == 1.0), _f(r["start_epoch"]), _f(r["end_epoch"]), _f(r["close_epoch"]),
                    int(_f(r["closed"]) == 1.0), int(bool(r["token0"]) and bool(r["token1"]) and bool(r["condition_id"])))
    return out


def merge_sources(h2: dict[str, tuple], h3: dict[str, tuple]) -> tuple[dict[str, tuple], dict]:
    """Union by market id; the h3 row is kept when both exist (field disagreements counted)."""
    rep = {"n_h2": len(h2), "n_h3": len(h3), "both": 0, "disagree_end": 0, "disagree_close": 0, "disagree_category": 0}
    out: dict[str, tuple] = {}
    for mid, r in h2.items():
        out[mid] = (*r, "h2")
    for mid, r in h3.items():
        if mid in out:
            o = out[mid]
            rep["both"] += 1
            rep["disagree_end"] += int(not (abs(o[4] - r[4]) <= 1.0 or (math.isnan(o[4]) and math.isnan(r[4]))))
            rep["disagree_close"] += int(not (abs(o[5] - r[5]) <= 1.0 or (math.isnan(o[5]) and math.isnan(r[5]))))
            rep["disagree_category"] += int(o[1] != r[1])
            out[mid] = (*r, "both")
        else:
            out[mid] = (*r, "h3")
    return out, rep


# =====================================================================================================================================
# Population, features
# =====================================================================================================================================


def build_population(merged: dict[str, tuple], excl_ids: set[str], excl_event: set[str]) -> tuple[dict[str, np.ndarray], dict]:
    """The W units (all strata): every closed row with two tokens, scheduled end inside W_fit ∪ gap ∪ W_screen ∪ W_hold (not on the excluded dates), open at
    its scheduled end (``close_epoch > end_epoch``, visible at ``t``), minus the W key drops (market id, event id). NO status filter. Sorted by (end, id)."""
    reasons: Counter = Counter()
    drops_src: dict[str, Counter] = {"h2": Counter(), "h3": Counter(), "both": Counter()}
    keep = []
    for mid in sorted(merged):
        ev, cat, neg, start, end, close, closed, tok, src = merged[mid]
        if not closed:
            reasons["not_closed"] += 1
            continue
        if not tok:
            reasons["no_tokens"] += 1
            continue
        if not math.isfinite(end):
            reasons["no_end"] += 1
            continue
        if E_EXCL[0] <= end < E_EXCL[1]:
            reasons["excluded_date"] += 1
            continue
        w = window_of(end)
        if w is None:
            reasons["end_outside_windows"] += 1
            continue
        if not math.isfinite(close):
            reasons["no_close_time"] += 1
            continue
        if not close > end:
            reasons["closed_at_or_before_end"] += 1
            continue
        if mid in excl_ids:
            reasons["key_drop_id"] += 1
            drops_src[src]["id"] += 1
            continue
        if ev and ev in excl_event:
            reasons["key_drop_event"] += 1
            drops_src[src]["event"] += 1
            continue
        keep.append((end, mid, ev, cat, neg, start, close, src, w))
    keep.sort(key=lambda x: (x[0], x[1]))
    n = len(keep)
    pop = {"market_id": np.array([k[1] for k in keep], dtype=object), "event_id": np.array([k[2] for k in keep], dtype=object),
           "cat": np.array([k[3] for k in keep], dtype=object), "neg": np.array([k[4] for k in keep], dtype=np.int8), "start": np.array([k[5] for k in keep], float),
           "end": np.array([k[0] for k in keep], float), "close": np.array([k[6] for k in keep], float), "src": np.array([k[7] for k in keep], dtype=object),
           "window": np.array([k[8] for k in keep], dtype=object)}
    rep = {"n_union": len(merged), "n_units": n, "excluded": dict(reasons), "key_drops_by_source": {s: dict(c) for s, c in drops_src.items()},
           "series_rule_drops": "not computable (the frames carry no series id; W key rule = market id and event id)",
           "negrisk_rule_drops": "not computable (the frames carry no negRiskMarketID)"}
    return pop, rep


def rolling_f7(end: np.ndarray, close: np.ndarray, cat: np.ndarray, L: np.ndarray, *, days: int = F7_DAYS, min_n: int = F7_MIN) -> np.ndarray:
    """f7 = median of ``L`` over units of the same ``fee_category`` with ``end in [t - days, t)`` AND ``close < t`` (only closes visible at ``t``); NaN if
    fewer than ``min_n``. Uses every unit passed in (all strata, all windows)."""
    f7 = np.full(len(end), math.nan)
    cat = np.asarray(cat).astype(str)
    for c in sorted(set(cat.tolist())):
        idx = np.where(cat == c)[0]
        o = idx[np.argsort(end[idx], kind="stable")]
        e, cl, ll = end[o], close[o], L[o]
        lo = np.searchsorted(e, e - days * DAY, side="left")
        hi = np.searchsorted(e, e, side="left")
        for j in range(len(o)):
            a, b = lo[j], hi[j]
            if b - a < min_n:
                continue
            m = cl[a:b] < e[j]
            if int(m.sum()) >= min_n:
                f7[o[j]] = float(np.median(ll[a:b][m]))
    return f7


def add_features(pop: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Waits and the frozen features f1-f3, f5-f7 (f4 is the fee category, pooled from the fit counts at fit time)."""
    n = len(pop["end"])
    L = np.array([wait_L(e, c) for e, c in zip(pop["end"], pop["close"], strict=True)], float) if n else np.zeros(0)
    ny = [c11.ny_clock(e) for e in pop["end"]]
    f1 = np.array([h for h, _ in ny], float) if n else np.zeros(0)
    f2 = np.array([d for _, d in ny], float) if n else np.zeros(0)
    f3 = (np.mod(pop["end"], DAY) == 0.0).astype(float)
    life = pop["end"] - pop["start"]
    f6 = np.where(np.isfinite(life) & (life > 0), np.log(np.where(life > 0, life, 1.0) / DAY), math.nan)
    out = dict(pop)
    out.update(L=L, f1=f1, f2=f2, f3=f3, f5=pop["neg"].astype(float), f6=f6, f7=rolling_f7(pop["end"], pop["close"], pop["cat"], L))
    return out


def draw_sample(ids: np.ndarray, events: np.ndarray, seed: str, n: int, per_event: int = MAX_PER_EVENT) -> list[int]:
    """Indices of a seeded sample: rank by sha256(seed|id), keep the ``per_event`` lowest-ranked of every event, then the first ``n`` by rank."""
    order = sorted(range(len(ids)), key=lambda i: c11.rank(seed, str(ids[i])))
    seen: Counter = Counter()
    out: list[int] = []
    for i in order:
        e = str(events[i]) or f"__m{ids[i]}"
        if seen[e] >= per_event:
            continue
        seen[e] += 1
        out.append(i)
        if len(out) >= n:
            break
    return out


def _unit_row(F: dict, i: int) -> list:
    nan_to = lambda x: "" if (isinstance(x, float) and math.isnan(x)) else x  # noqa: E731
    return [F["market_id"][i], F["event_id"][i], F["cat"][i], F["src"][i], F["window"][i], F["end"][i], nan_to(F["start"][i]), F["f1"][i], F["f2"][i], F["f3"][i],
            F["f5"][i], nan_to(F["f6"][i]), nan_to(F["f7"][i]), F["L"][i] if F["window"][i] == "fit" else ""]


# =====================================================================================================================================
# w-frame job (q0222): no network
# =====================================================================================================================================


def frame_windows(source: str, manifest: dict) -> list[dict]:
    """The deterministic 15-minute 'closed' end windows of a history frame: ``random.Random(f"{seed}|{day}").sample(range(96), 6)`` per UTC day for the
    ``lookback_days`` days ending at the frame's request clock (``history_backfill.fetch_frame`` rule). Windows that end after the clock are skipped."""
    import random  # noqa: PLC0415

    seed, lookback = FRAME_SEEDS[source]
    prm = manifest.get("params") or {}
    if prm.get("seed") != seed or int(prm.get("lookback_days", -1)) != lookback:
        raise Refused(f"{source} manifest seed/lookback {prm.get('seed')}/{prm.get('lookback_days')} differ from the declared {seed}/{lookback}")
    now = cm.ep(str(manifest["request_clock_now"]).replace(" ", "T")) if "T" in str(manifest["request_clock_now"]) else cm.ep(str(manifest["request_clock_now"]))
    day0 = datetime.fromtimestamp(now, UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for d in range(lookback, -1, -1):
        day = day0 - timedelta(days=d)
        picks = sorted(random.Random(f"{seed}|{day:%Y-%m-%d}").sample(range(96), 6))
        for k in picks:
            a = day + timedelta(minutes=15 * k)
            b = a + timedelta(minutes=15)
            if b.timestamp() > now:
                continue
            out.append({"frame": source, "day": f"{day:%Y-%m-%d}", "k": k, "a": a.timestamp(), "b": b.timestamp()})
    return out


def censor_window_set(a: float) -> str | None:
    """'fit' / 'screen' / 'hold' for a window starting at ``a`` (W_fit ∪ W_screen ∪ W_hold only; gap and excluded dates are None)."""
    w = window_of(a)
    return w if w in ("fit", "screen", "hold") else None


def draw_censor_windows(windows: list[dict], n: int = N_CENSOR_WINDOWS) -> list[dict]:
    """Seeded sample of the frame windows whose ends fall in W_fit ∪ W_screen ∪ W_hold (rank by sha256 of frame|day|k)."""
    elig = []
    for w in windows:
        s = censor_window_set(w["a"])
        if s:
            elig.append({**w, "set": s})
    elig.sort(key=lambda w: c11.rank(SEED_CENSOR, f"{w['frame']}|{w['day']}|{w['k']}"))
    return sorted(elig[:n], key=lambda w: (w["frame"], w["a"]))


def closed_rows_per_window(rows_end_close: Iterable[tuple[float, int]], windows: list[dict]) -> list[int]:
    """Number of frame rows with ``closed == 1`` and ``end_epoch in [a, b]`` per window (counts only). The window is CLOSED at both ends, as the Gamma query that
    built the frame (``end_date_min`` / ``end_date_max`` are inclusive; ``hb.fetch_frame``) and the q0224 count (``count_in_window``) are (section 11.3)."""
    if not windows:
        return []
    ends = np.sort(np.array([e for e, c in rows_end_close if c], float))
    return [int(np.searchsorted(ends, w["b"], side="right") - np.searchsorted(ends, w["a"], side="left")) for w in windows]


def in_frame_windows(ends: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Boolean per end: does it fall in some reconstructed window ``[a, b]`` (closed at both ends, the Gamma walk's own convention; section 11.3)? The windows of
    one frame do not overlap (adjacent windows share only an endpoint)."""
    ends, a, b = np.asarray(ends, float), np.asarray(a, float), np.asarray(b, float)
    if not len(ends) or not len(a):
        return np.zeros(len(ends), bool)
    o = np.argsort(a)
    j = np.searchsorted(a[o], ends, side="right") - 1
    return (j >= 0) & (ends <= b[o][np.clip(j, 0, None)])


def _wcsv(path: Path, header: list[str], rows: Iterable[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(hb._gz_csv_bytes(header, rows))


def write_seal_copy(doc: dict, seals_dir: Path) -> Path:
    dest = Path(seals_dir) / SEAL_COPY_NAME
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    if dest.exists() and dest.read_bytes() != data:
        raise Refused(f"{dest} exists with different content; a seal is never rewritten")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def w_frame(root: Path, hist_root: Path, *, rules_sha: str, smoke_path: Path, exclusion_keys_path: Path, seals_dir: Path | None = None, now: float,
            data_dumps: Path | None = None, data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, disk_cap: int = int(WFRAME_OUTPUT_CAP_GB * 1024**3), free_fn=None,
            h2_sha: str | None = c11.H2_FRAME_SHA256, h3_sha: str | None = c11.H3_FRAME_SHA256, with_seal_copy: bool = True, censor_match_min: float = CENSOR_MATCH_MIN) -> dict:
    """q0222 (no network). Population, features, splits, W2 samples, guarded targets / outcomes, censoring windows and the W_hold listing + seal copy."""
    from . import cb11_smoke as sm  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    root = Path(root)
    rdir = c11.require_output_root(root / FRAME_RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    done = c11.manifest_complete(rdir, (FRAME_STATUS,))
    if done:
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": done.get("counts")}
    bad = sm.smoke_failures(smoke_path, sm.FAMILY_NEEDS["W"])
    if bad:
        return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c11.load_exclusion_keys(Path(exclusion_keys_path))
    # Design 1.3 (B10): unverified disjointness (> 2% of exclusion ids without metadata) makes P and A "not testable"; W's key rule is market id + event id and W
    # proceeds. The unverified state is recorded in the frame report and the census.
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    rdir.mkdir(parents=True, exist_ok=True)
    hist_root = Path(hist_root)
    paths = {"h2_main": hist_root / "h2_main" / "frame.csv.gz", "h3_power": hist_root / "h3_power" / "frame.csv.gz"}
    shas = {"h2_main": h2_sha, "h3_power": h3_sha}
    frames = {s: collect_frame(read_frame_rows(paths[s], sha256=shas[s])) for s in paths}
    manifests = {s: json.loads((hist_root / s / "manifest.json").read_text()) for s in paths}
    merged, mrep = merge_sources(frames["h2_main"], frames["h3_power"])
    pop, prep = build_population(merged, ids, keys["event"])
    F = add_features(pop)
    n = len(F["end"])
    primary = np.array([is_primary(c) for c in F["cat"]], bool) if n else np.zeros(0, bool)
    win = F["window"]
    # censoring windows (counts only): the frames' own closed rows per window, before any exclusion
    wins_all: list[dict] = []
    for s in paths:
        wins = frame_windows(s, manifests[s])
        wins_all += wins
    sample_w = draw_censor_windows(wins_all)
    counts_by_frame = {s: closed_rows_per_window([(r[4], r[6]) for r in frames[s].values()], [w for w in sample_w if w["frame"] == s]) for s in paths}
    cw_rows = []
    for s in paths:
        for w, cnt in zip([w for w in sample_w if w["frame"] == s], counts_by_frame[s], strict=True):
            cw_rows.append([s, w["day"], w["k"], int(w["a"]), int(w["b"]), w["set"], cnt])
    allw = {s: [w for w in wins_all if w["frame"] == s] for s in paths}
    match = {}
    for s in paths:
        ends = np.array([r[4] for r in frames[s].values() if r[6] and math.isfinite(r[4]) and E_START <= r[4] < E_HOLD[1]], float)
        a = np.array([w["a"] for w in allw[s]], float)
        b = np.array([w["b"] for w in allw[s]], float)
        if len(ends) and len(a):
            match[s] = float(in_frame_windows(ends, a, b).mean())
        else:
            match[s] = math.nan
    bad_match = {s: m for s, m in match.items() if not (m >= censor_match_min)}
    if bad_match:  # the reconstructed windows must reproduce the frames' closed rows (N8): else the censoring counts are not comparable
        return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"reconstructed censoring windows cover < {censor_match_min:.0%} of a frame's closed rows: {bad_match}", "not testable (censoring windows)")
    # units files
    idx_p = np.where(primary)[0]
    idx_np = np.where(~primary)[0]
    fit_cat = Counter(str(F["cat"][i]) for i in idx_p if win[i] == "fit")
    rows_main = [_unit_row(F, i) for i in idx_p if win[i] != "hold"]
    rows_hold = [_unit_row(F, i) for i in idx_p if win[i] == "hold"]
    _wcsv(rdir / "units.csv.gz", UNIT_COLUMNS, rows_main)
    _wcsv(rdir / HOLD_DIR / "units_hold.csv.gz", UNIT_COLUMNS, rows_hold)
    _wcsv(rdir / "units_nonprimary.csv.gz", UNIT_COLUMNS, [_unit_row(F, i) for i in idx_np if win[i] in ("fit", "gap", "screen")])  # reported strata (sports, crypto): screen-W only
    _wcsv(rdir / "targets_guarded.csv.gz", TARGET_COLUMNS, ([F["market_id"][i], F["L"][i], F["close"][i]] for i in range(n) if win[i] in ("screen", "gap")))
    _wcsv(rdir / HOLD_DIR / "targets_guarded_hold.csv.gz", TARGET_COLUMNS, ([F["market_id"][i], F["L"][i], F["close"][i]] for i in idx_p if win[i] == "hold"))
    # W2 samples (metadata only, before any print)
    scr = [i for i in idx_p if win[i] == "screen"]
    hld = [i for i in idx_p if win[i] == "hold"]
    s_scr = [scr[j] for j in draw_sample(F["market_id"][scr], F["event_id"][scr], SEED_SAMPLE, N_SAMPLE_SCREEN)] if scr else []
    s_hld = [hld[j] for j in draw_sample(F["market_id"][hld], F["event_id"][hld], SEED_HOLD, N_SAMPLE_HOLD)] if hld else []
    want = {str(F["market_id"][i]): ("screen" if i in set(s_scr) else "holdout") for i in [*s_scr, *s_hld]}
    tok: dict[str, tuple[str, str, str]] = {}
    for s in ("h3_power", "h2_main"):  # the h3 row is kept when both exist
        for r in read_frame_rows(paths[s], sha256=None):
            m = str(r["market_id"])
            if m in want and m not in tok:
                tok[m] = (r["condition_id"], r["token0"], r["token1"])
    pos = {str(F["market_id"][i]): i for i in [*s_scr, *s_hld]}

    def srow(m: str) -> list:
        i = pos[m]
        return [m, F["event_id"][i], F["cat"][i], *tok.get(m, ("", "", "")), F["end"][i], want[m]]

    _wcsv(rdir / "w2_sample.csv.gz", SAMPLE_COLUMNS, (srow(str(F["market_id"][i])) for i in s_scr))
    _wcsv(rdir / HOLD_DIR / "w2_sample_hold.csv.gz", SAMPLE_COLUMNS, (srow(str(F["market_id"][i])) for i in s_hld))
    # guarded outcomes of the sampled markets (the frame's outcome_prices and uma_status, routed here only)
    out_scr, out_hld = [], []
    seen_o: set[str] = set()
    for s in ("h3_power", "h2_main"):  # the h3 row is kept when both exist
        for g in iter_frame_guarded(paths[s]):
            m = str(g["market_id"])
            if m in want and m not in seen_o:
                seen_o.add(m)
                (out_scr if want[m] == "screen" else out_hld).append([m, g["outcome_prices"], g["uma_status"]])
    wp = Path(hist_root) / H11
    _wcsv(wp / "outcomes_guarded.csv.gz", OUTCOME_COLUMNS, out_scr)
    _wcsv(rdir / HOLD_DIR / "outcomes_guarded_hold.csv.gz", OUTCOME_COLUMNS, out_hld)
    _wcsv(rdir / "censor_windows.csv.gz", WINDOW_COLUMNS, cw_rows)
    # report (counts only: no wait, no outcome)
    cat_by_win = {w: Counter(str(F["cat"][i]) for i in idx_p if win[i] == w) for w in ("fit", "gap", "screen", "hold")}
    src_by_win = {w: Counter(str(F["src"][i]) for i in idx_p if win[i] == w) for w in ("fit", "gap", "screen", "hold")}
    dates_by_win = {w: len({date_of(F["end"][i]) for i in idx_p if win[i] == w}) for w in ("fit", "gap", "screen", "hold")}
    events_by_win = {w: len({str(F["event_id"][i]) for i in idx_p if win[i] == w}) for w in ("fit", "gap", "screen", "hold")}
    hour_by_win = {w: Counter(int(F["f1"][i]) for i in idx_p if win[i] == w) for w in ("fit", "screen", "hold")}
    nonprim = Counter((str(F["cat"][i]), str(win[i])) for i in range(n) if not primary[i])
    f7_nan = {w: int(sum(1 for i in idx_p if win[i] == w and not math.isfinite(F["f7"][i]))) for w in ("fit", "screen", "hold")}
    open_at_end_share = {"note": "every unit is open at its scheduled end by construction; closed-at-or-before-end rows counted in 'excluded'"}
    rep = {"version": "cb11-w-frame-v2", "frame_sha256": {s: shas[s] for s in paths}, "merge": mrep, "population": prep, "exclusion_keys_sha256": ksha,
           "exclusion": {"disjointness": krep.get("disjointness"), "missing_share": krep.get("missing_share"), "n_missing": krep.get("n_missing"),
                         "note": "unverified disjointness stalls P and A only (design 1.3); W's key rule is market id + event id"},
           "n_units_all_strata": n, "n_units_primary": int(primary.sum()), "primary_excluded_categories": list(PRIMARY_EXCLUDED),
           "non_primary_counts": {f"{c}|{w}": v for (c, w), v in sorted(nonprim.items())},
           "windows": {w: int(sum(1 for i in idx_p if win[i] == w)) for w in ("fit", "gap", "screen", "hold")}, "categories": {w: dict(c) for w, c in cat_by_win.items()},
           "frame_source": {w: dict(c) for w, c in src_by_win.items()}, "end_dates": dates_by_win, "events": events_by_win, "end_hour_ny": {w: dict(sorted(c.items())) for w, c in hour_by_win.items()},
           "fit_category_counts": dict(fit_cat), "f7_nan": f7_nan, "open_at_end": open_at_end_share,
           "sample": {"screen": len(s_scr), "hold": len(s_hld), "per_event_cap": MAX_PER_EVENT, "seeds": {"screen": SEED_SAMPLE, "hold": SEED_HOLD}},
           "censor_windows": {"n": len(cw_rows), "by_set": dict(Counter(r[5] for r in cw_rows)), "window_match_share": match, "seed": SEED_CENSOR,
                              "match_min": censor_match_min,
                              "note": "capped frame windows (300 rows) are not identifiable from the partial records; the frame's closed rows in a window are a lower bound"},
           "waits_note": "W_fit waits are stored in units.csv.gz (L_fit, a fit feature); screen / gap / hold waits only in the guarded target files"}
    (rdir / "frame_report.json").write_text(json.dumps(rep, indent=1, sort_keys=True, default=float))
    # hold listing + seal copy
    hold_files = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(HOLD_DIR + "/")}
    listing = {"seal_version": "cb11-w-hold-seal-v1", "listing_sha256": h5_seal.listing_sha256(hold_files), "n_hold_files": len(hold_files), "files": dict(sorted(hold_files.items())),
               "n_units_hold": len(rows_hold), "n_end_dates": dates_by_win["hold"], "n_events": events_by_win["hold"], "categories": dict(cat_by_win["hold"]),
               "n_sample_hold": len(s_hld), "rules_sha256": rules_sha, "exclusion_keys_sha256": ksha, "windows": {"hold": list(W_HOLD)},
               "read_rules": "units_hold / targets / outcomes are opened only by rep-W after the listing hash is verified; the census reads this listing's counts only"}
    (rdir / "w_hold_listing.json").write_text(json.dumps(listing, indent=1, sort_keys=True))
    seal_path = write_seal_copy(listing, Path(seals_dir or c11.SEALS_DIR)) if with_seal_copy else None
    files = {k: v for k, v in h5_seal.list_files(rdir).items() if k not in ("manifest.json",)}
    m = {"status": FRAME_STATUS, "complete": True, "stopped": None, "rules_sha256": rules_sha, "counts": {"units": len(rows_main) + len(rows_hold), "sample_screen": len(s_scr), "sample_hold": len(s_hld)},
         "file_sha256": files, "written_utc": cm.iso(time.time()), "request_clock": cm.iso(now), "seal_copy": str(seal_path) if seal_path else None}
    cm.write_json_atomic(rdir / "manifest.json", m)
    return m


# =====================================================================================================================================
# Loaders for the analysis jobs (census / screen / rep)
# =====================================================================================================================================


def _typed(r: dict) -> dict:
    return {**r, "end_epoch": _f(r["end_epoch"]), "start_epoch": _f(r.get("start_epoch")), "f1": _f(r["f1"]), "f2": _f(r["f2"]), "f3": _f(r["f3"]), "f5": _f(r["f5"]),
            "f6": _f(r["f6"]), "f7": _f(r["f7"]), "L_fit": _f(r.get("L_fit"))}


def load_units(wdir: Path, windows: tuple[str, ...], *, job: str) -> list[dict]:
    """Units of the given windows. ``hold`` is loaded only by ``rep-W`` (the sealed listing hash verified first); the census never receives a wait of a
    screen / gap / hold unit (``L_fit`` is filled for the fit window only, ``L`` is not in the file)."""
    wdir = Path(wdir)
    if "hold" in windows:
        if job != "rep-W":
            raise Refused("W_hold is sealed: only rep-W loads it (after verify_hold_seal)")
        rows = [_typed(r) for r in c11.read_csv_gz(wdir / HOLD_DIR / "units_hold.csv.gz")]
    else:
        rows = []
    if any(w != "hold" for w in windows):
        rows += [_typed(r) for r in c11.read_csv_gz(wdir / "units.csv.gz") if r["window"] in windows]
    return [r for r in rows if r["window"] in windows]


def open_w_guarded(path: Path, job: str) -> list[dict]:
    """Guarded W files: ``screen-W`` and ``rep-W`` open the non-hold files, only ``rep-W`` the ``*_hold`` ones."""
    p = Path(path)
    if p.name in HOLD_ONLY and job != "rep-W":
        raise Refused(f"{p.name} is sealed: only rep-W opens it")
    return c11.open_guarded(p, job if job in ("screen-W", "rep-W") else "refused", GUARDED_NAMES)


def verify_hold_seal(wdir: Path, seals_dir: Path | None = None, *, require_committed: bool = True) -> dict:
    """The run's listing equals ``seals/cb11_w_hold_SEAL.json`` AND (N5) that copy is tracked by git and identical to HEAD; the HOLD listing sha256 is re-verified."""

    from . import cb1_history as c1  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    wdir = Path(wdir)
    sp = wdir / "w_hold_listing.json"
    if not sp.exists():
        raise Refused("w_hold_listing.json missing; run w-frame first")
    copy = Path(seals_dir or c11.SEALS_DIR) / SEAL_COPY_NAME
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise Refused(f"seal copy {copy} missing or different from {sp}")
    if require_committed and not c1.spec_committed(copy):
        raise Refused(f"seal copy {copy} is not committed (or differs from HEAD)")
    doc = json.loads(sp.read_text())
    hold = {k: v for k, v in h5_seal.list_files(wdir).items() if k.startswith(HOLD_DIR + "/")}
    if h5_seal.listing_sha256(hold) != doc["listing_sha256"]:
        raise Refused("W_hold listing sha256 differs from the seal; refusing")
    return doc


# =====================================================================================================================================
# Model (W1)
# =====================================================================================================================================


def category_levels(units: list[dict]) -> list[str]:
    cnt = Counter(str(u["fee_category"]) for u in units)
    return sorted(c for c, n in cnt.items() if n >= RARE_MIN)


def design_matrix(units: list[dict], levels: list[str]) -> np.ndarray:
    code = {c: i for i, c in enumerate(levels)}
    rare = len(levels)
    return np.array([[u["f1"], u["f2"], u["f3"], code.get(str(u["fee_category"]), rare), u["f5"], u["f6"], u["f7"]] for u in units], float).reshape(-1, 7)


def baseline_b0(units: list[dict], L: np.ndarray) -> dict:
    """W_fit median of ``L`` per fee category, overall median as the fallback for an unseen category."""
    by: dict[str, list[float]] = {}
    for u, y in zip(units, L, strict=True):
        by.setdefault(str(u["fee_category"]), []).append(float(y))
    return {"by_category": {c: float(np.median(v)) for c, v in by.items()}, "overall": float(np.median(L)) if len(L) else math.nan}


def b0_of(units: list[dict], b0: dict) -> np.ndarray:
    return np.array([b0["by_category"].get(str(u["fee_category"]), b0["overall"]) for u in units], float)


def b1_of(units: list[dict], b0_vals: np.ndarray) -> tuple[np.ndarray, float]:
    """B1: the unit's own f7, falling back to B0 where f7 is NaN. Returns (values, fallback share)."""
    f7 = np.array([u["f7"] for u in units], float)
    nan = ~np.isfinite(f7)
    return np.where(nan, b0_vals, f7), float(nan.mean()) if len(f7) else math.nan


def fit_model(fit_units: list[dict], L: np.ndarray, *, drop_sched: bool = False) -> dict:
    """Frozen HGB (absolute error) fitted once; ``drop_sched`` removes f1-f3 for the schedule attribution refit. sklearn / numpy versions are pinned."""
    import numpy as _np  # noqa: PLC0415
    import sklearn  # noqa: PLC0415
    from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: PLC0415

    if sklearn.__version__ != SKLEARN_PIN or _np.__version__ != NUMPY_PIN:
        raise Refused(f"pinned sklearn {SKLEARN_PIN} / numpy {NUMPY_PIN} required, found {sklearn.__version__} / {_np.__version__}")
    levels = category_levels(fit_units)
    X = design_matrix(fit_units, levels)
    cols = [i for i in range(7) if not (drop_sched and i in SCHED)]
    cat_idx = [cols.index(i) for i in (0, 1, 3) if i in cols]
    mdl = HistGradientBoostingRegressor(categorical_features=cat_idx, **MODEL_PARAMS)
    mdl.fit(X[:, cols], np.asarray(L, float))
    return {"model": mdl, "levels": levels, "cols": cols, "b0": baseline_b0(fit_units, L), "drop_sched": drop_sched}


def predict(fm: dict, units: list[dict]) -> np.ndarray:
    X = design_matrix(units, fm["levels"])
    return np.asarray(fm["model"].predict(X[:, fm["cols"]]), float)


def w1_boot(err_m: np.ndarray, err_b0: np.ndarray, err_b1: np.ndarray, clusters, *, n_boot: int = c11.N_BOOT, seed: int = c11.SEED_BOOT) -> tuple[np.ndarray, np.ndarray]:
    """Cluster bootstrap draws of R_B0 = 1 - sum(err_m)/sum(err_b0) and R_B1 (one set of resamples for both)."""
    import pandas as pd  # noqa: PLC0415

    codes, uniq = pd.factorize(np.asarray(clusters).astype(str))
    g = len(uniq)
    s_m = np.bincount(codes, weights=err_m, minlength=g)
    s_0 = np.bincount(codes, weights=err_b0, minlength=g)
    s_1 = np.bincount(codes, weights=err_b1, minlength=g)
    rng = np.random.default_rng(seed)
    r0, r1 = np.empty(n_boot), np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        d0, d1, nm = float(m @ s_0), float(m @ s_1), float(m @ s_m)
        r0[i] = 1.0 - nm / d0 if d0 > 0 else math.nan
        r1[i] = 1.0 - nm / d1 if d1 > 0 else math.nan
    return r0, r1


def _boot_p(draws: np.ndarray) -> float:
    return c11.one_sided_boot_p(draws)


def w1_core(L: np.ndarray, pred: np.ndarray, b0: np.ndarray, b1: np.ndarray, date: np.ndarray, event: np.ndarray, *, n_boot: int = c11.N_BOOT, seed: int = c11.SEED_BOOT) -> dict:
    """R_B0, R_B1 over the units and the one-sided cluster-bootstrap p of each (max over the end-date and event ways); testable needs >= 100 units and >= 30
    clusters in every way."""
    L, pred, b0, b1 = (np.asarray(x, float) for x in (L, pred, b0, b1))
    em, e0, e1 = np.abs(L - pred), np.abs(L - b0), np.abs(L - b1)
    n = len(L)
    out: dict = {"n": int(n), "mae_model": float(em.mean()) if n else math.nan, "mae_b0": float(e0.mean()) if n else math.nan, "mae_b1": float(e1.mean()) if n else math.nan}
    out["R_B0"] = float(1.0 - em.sum() / e0.sum()) if n and e0.sum() > 0 else math.nan
    out["R_B1"] = float(1.0 - em.sum() / e1.sum()) if n and e1.sum() > 0 else math.nan
    ways = {"date": np.asarray(date).astype(str), "event": np.asarray(event).astype(str)}
    G = {k: len(set(v.tolist())) for k, v in ways.items()}
    testable = bool(n >= c11.MIN_UNITS and all(g >= c11.MIN_CLUSTERS for g in G.values()))
    p0 = p1 = 1.0
    if testable:
        ps0, ps1 = [], []
        for v in ways.values():
            r0, r1 = w1_boot(em, e0, e1, v, n_boot=n_boot, seed=seed)
            ps0.append(_boot_p(r0))
            ps1.append(_boot_p(r1))
        p0, p1 = max(ps0), max(ps1)
    out.update(testable=testable, G=G, p_B0=float(p0), p_B1=float(p1))
    return out


def w1_floor_ok(r: dict, alpha: float = c11.GATE_P, inclusive: bool = False) -> bool:
    """Both floors and both p thresholds. Stage 1: ``alpha`` = 0.01, p < alpha. Stage 2: ``alpha`` = 0.05 / k, ``inclusive`` (p <= alpha / k); no extra 0.01 gate (B8)."""
    return bool(r.get("testable") and r["R_B0"] >= W1_FLOOR_B0 and r["R_B1"] >= W1_FLOOR_B1 and _p_ok(r["p_B0"], alpha, inclusive) and _p_ok(r["p_B1"], alpha, inclusive))


def permute_within_cells(L: np.ndarray, cell: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A uniform random bijection of the units of every cell onto the cell's own ``L`` values (cell = fee_category x calendar month)."""
    out = np.asarray(L, float).copy()
    cell = np.asarray(cell).astype(str)
    for c in sorted(set(cell.tolist())):
        idx = np.where(cell == c)[0]
        out[idx] = np.asarray(L, float)[idx][rng.permutation(len(idx))]
    return out


def w1_placebo(L, pred, b0, b1, date, event, cell, *, n_draws: int = c11.PLACEBO_DRAWS, seed: int = c11.PLACEBO_SEEDS["W1_permute"], n_boot: int = c11.N_BOOT,
               alpha: float = c11.GATE_P) -> dict:
    """Binding calibration placebo: permute the targets within category x month (predictions and baselines fixed); a draw advances iff BOTH p thresholds
    hold at ``alpha`` (floors off). Advance rate <= 1.5%. Stage 1 ``alpha`` = 0.01; Stage 2 passes min(alpha / k, 0.01) (never looser than Stage 1's calibration level)."""
    rng = np.random.default_rng(seed)
    adv = []
    for _ in range(n_draws):
        lp = permute_within_cells(L, cell, rng)
        r = w1_core(lp, pred, b0, b1, date, event, n_boot=n_boot, seed=int(rng.integers(1, 10**6)))
        adv.append(max(r["p_B0"], r["p_B1"]))
    out = c11.placebo_advance_rate(adv, alpha)
    out["alpha"] = alpha
    out["note"] = "W1 target permutation within category x month; advance iff both p thresholds hold"
    return out


def hours_view(L: np.ndarray, pred: np.ndarray, b0: np.ndarray, b1: np.ndarray) -> tuple[np.ndarray, ...]:
    """MAE on ``min(wait, 21 d)`` in hours: back-transform of the log-hour target and forecasts."""
    return tuple(np.exp(np.asarray(x, float)) for x in (L, pred, b0, b1))


def w1_robustness(U: list[dict], L, pred, b0, b1, *, decided_mask=None, n_boot: int = c11.N_BOOT, alpha: float = c11.GATE_P, inclusive: bool = False) -> dict:
    """Binding robustness: R >= 0.10 (both baselines) in every calendar month; p and floors hold without the top-5 end-dates and the top-5 events; R >= 0.10 on
    hours; R >= 0.10 on h2-only and h3-only rows. ``decided_mask`` (W2 decided SCREEN units) feeds the attribution (b)."""
    L, pred, b0, b1 = (np.asarray(x, float) for x in (L, pred, b0, b1))
    date = np.array([date_of(u["end_epoch"]) for u in U])
    event = np.array([str(u["event_id"]) for u in U])
    month = np.array([month_of(u["end_epoch"]) for u in U])
    src = np.array([str(u["src"]) for u in U])
    out: dict = {}

    def _r(mask) -> tuple[float, float]:
        a = np.abs(L[mask] - pred[mask]).sum()
        d0, d1 = np.abs(L[mask] - b0[mask]).sum(), np.abs(L[mask] - b1[mask]).sum()
        return (float(1 - a / d0) if d0 > 0 else math.nan, float(1 - a / d1) if d1 > 0 else math.nan)

    months = {}
    for m in sorted(set(month.tolist())):
        r0, r1 = _r(month == m)
        months[m] = {"R_B0": r0, "R_B1": r1, "n": int((month == m).sum()), "ok": bool(r0 >= W1_SUBSET_R and r1 >= W1_SUBSET_R)}
    out["by_month"] = months
    out["by_month_ok"] = bool(months) and all(v["ok"] for v in months.values())
    contrib = (np.abs(L - b0) - np.abs(L - pred)) + (np.abs(L - b1) - np.abs(L - pred))
    drop = {}
    for way, cl in (("date", date), ("event", event)):
        keep = c11.c9.top_k_drop_mask(contrib, cl, c11.TOP_DROP)
        r = w1_core(L[keep], pred[keep], b0[keep], b1[keep], date[keep], event[keep], n_boot=n_boot)
        drop[way] = {"n": r["n"], "R_B0": r["R_B0"], "R_B1": r["R_B1"], "p_B0": r["p_B0"], "p_B1": r["p_B1"], "ok": w1_floor_ok(r, alpha, inclusive)}
    out["without_top5"] = drop
    out["without_top5_ok"] = all(v["ok"] for v in drop.values())
    h = hours_view(L, pred, b0, b1)
    hr = _r_hours(*h)
    out["hours"] = {"R_B0": hr[0], "R_B1": hr[1], "ok": bool(hr[0] >= W1_SUBSET_R and hr[1] >= W1_SUBSET_R)}
    by_src = {}
    for s in ("h2", "h3"):
        mask = src == s  # N4: rows present in both frames ('both') are in neither the h2-only nor the h3-only subset
        r0, r1 = _r(mask) if mask.any() else (math.nan, math.nan)
        by_src[s] = {"R_B0": r0, "R_B1": r1, "n": int(mask.sum()), "ok": bool(r0 >= W1_SUBSET_R and r1 >= W1_SUBSET_R)}
    out["by_source"] = by_src
    out["by_source_ok"] = all(v["ok"] for v in by_src.values())
    if decided_mask is not None and np.asarray(decided_mask).any():
        r0, r1 = _r(np.asarray(decided_mask, bool))
        out["decided_units"] = {"R_B0": r0, "n": int(np.asarray(decided_mask).sum()), "ok": bool(r0 >= W1_SUBSET_R)}
    out["ok"] = bool(out["by_month_ok"] and out["without_top5_ok"] and out["hours"]["ok"] and out["by_source_ok"])
    return out


def _r_hours(Lh, ph, b0h, b1h) -> tuple[float, float]:
    a = np.abs(Lh - ph).sum()
    d0, d1 = np.abs(Lh - b0h).sum(), np.abs(Lh - b1h).sum()
    return (float(1 - a / d0) if d0 > 0 else math.nan, float(1 - a / d1) if d1 > 0 else math.nan)


def w1_stat(eval_units: list[dict], L: np.ndarray, fm: dict, fm_nosched: dict | None, *, decided_mask=None, n_draws: int = c11.PLACEBO_DRAWS, n_boot: int = c11.N_BOOT, placebo: bool = True,
            alpha: float = c11.GATE_P, inclusive: bool = False) -> dict:
    """W1 on ``eval_units`` (targets ``L``) with the frozen model ``fm`` (fitted before; see ``fit_model``). ``alpha`` is the p threshold of BOTH baselines: 0.01
    (strict) in Stage 1; alpha / k (inclusive) in Stage 2, where the design's Holm rule is the only p gate (B8)."""
    pred = predict(fm, eval_units)
    b0 = b0_of(eval_units, fm["b0"])
    b1, fb = b1_of(eval_units, b0)
    date = np.array([date_of(u["end_epoch"]) for u in eval_units])
    event = np.array([str(u["event_id"]) for u in eval_units])
    core = w1_core(L, pred, b0, b1, date, event, n_boot=n_boot)
    out: dict = {**core, "b1_fallback_share": fb, "floors": {"R_B0": W1_FLOOR_B0, "R_B1": W1_FLOOR_B1}, "p_threshold": alpha, "p_threshold_inclusive": inclusive,
                 "label": "reused frame, fresh target (L1)"}
    if not core["testable"]:
        return {**out, "advance": False, "p": 1.0, "verdict": "not testable (units or clusters)"}
    cell = np.array([f"{u['fee_category']}|{month_of(u['end_epoch'])}" for u in eval_units])
    out["placebo"] = w1_placebo(L, pred, b0, b1, date, event, cell, n_draws=n_draws, n_boot=n_boot, alpha=min(alpha, c11.GATE_P)) if placebo else {"n_draws": 0, "holds": True, "advance_rate": None, "note": "skipped"}
    out["robustness"] = w1_robustness(eval_units, L, pred, b0, b1, decided_mask=decided_mask, n_boot=n_boot, alpha=alpha, inclusive=inclusive)
    if fm_nosched is not None:
        pn = predict(fm_nosched, eval_units)
        rn = w1_core(L, pn, b0, b1, date, event, n_boot=2)
        out["attribution_schedule"] = {"R_full_B0": core["R_B0"], "R_noSched_B0": rn["R_B0"], "delta": core["R_B0"] - rn["R_B0"], "credit_clock": bool(core["R_B0"] - rn["R_B0"] >= ATTR_SCHED_MIN),
                                       "label_if_not": "the wait is forecastable from category and recent lag, not from the clock"}
    dec = (out["robustness"].get("decided_units") or {})
    out["attribution_decided"] = {**dec, "label_if_not": "skill comes from undecided markets (event timing), not proposer timing"} if dec else {"note": "no decided units", "ok": False}
    core_ok = w1_floor_ok(core, alpha, inclusive)
    out["core_ok"] = core_ok
    out["advance"] = bool(core_ok and out["placebo"].get("holds") and out["robustness"]["ok"])
    out["p"] = float(max(core["p_B0"], core["p_B1"]))
    out["verdict"] = "advance" if out["advance"] else ("floor / p not met" if not core_ok else "placebo or robustness failed")
    return out


# =====================================================================================================================================
# W2: transactions, decided carry, pool, statistic
# =====================================================================================================================================


def fee_rate(cat: str) -> float:
    c = str(cat or "unknown")
    return float(FEE_RATE.get(c, FEE_RATE.get(c.split(":")[0], 0.05)))


def fetch_prints_until(lim: hb.Limiter, cid: str, t_stop: float, *, limit: int = DATA_PAGE_LIMIT, pages: int = DATA_PAGES) -> tuple[list[dict], dict]:
    """Newest-first ``/trades`` pages (limit 1,000) until a page's oldest print is before ``t_stop`` (= t - 6 h) or the cap. ``truncated`` iff the cap is
    reached on a full page without reaching ``t_stop`` (or the API refuses the deep offset). A non-200 first page raises."""
    rows: list[dict] = []
    info = {"pages": 0, "truncated": False}
    for page in range(pages):
        st, data = lim.get(hb.DATA_TRADES, {"market": cid, "limit": limit, "offset": page * limit, "takerOnly": TAKER_ONLY})
        if st == 400 and page > 0:
            info["truncated"] = True
            break
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"trades status {st}")
        info["pages"] += 1
        got = [x for x in data if isinstance(x, dict)]
        rows.extend(got)
        ts = [float(x["timestamp"]) for x in got if str(x.get("timestamp", "")).replace(".", "", 1).isdigit()]
        if len(data) < limit or (ts and min(ts) < t_stop):
            return rows, {**info, "n_nohash": sum(1 for x in rows if not x.get("transactionHash")), "n_prints": len(rows), "oldest_ts": _min_ts(rows)}
    else:
        info["truncated"] = True
    return rows, {**info, "n_nohash": sum(1 for x in rows if not x.get("transactionHash")), "n_prints": len(rows), "oldest_ts": _min_ts(rows)}


def _min_ts(rows: list[dict]) -> float:
    ts = [float(x["timestamp"]) for x in rows if str(x.get("timestamp", "")).replace(".", "", 1).isdigit()]
    return min(ts) if ts else math.nan


def load_tx(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """market_id -> (ts, outcome-0-terms price, size), time-ordered."""
    acc: dict[str, list[tuple[float, float, float]]] = {}
    p = Path(path)
    if p.exists():
        for r in c11.read_csv_gz(p):
            acc.setdefault(str(r["market_id"]), []).append((float(r["ts"]), float(r["price"]), float(r["size"])))
    out = {}
    for m, v in acc.items():
        v.sort()
        out[m] = (np.array([x[0] for x in v]), np.array([x[1] for x in v]), np.array([x[2] for x in v]))
    return out


def decide_and_enter(tx: tuple[np.ndarray, np.ndarray, np.ndarray] | None, t: float, close: float, *, trig_to: float = TRIG_TO_S, h_w: float = H_W) -> dict:
    """Trigger and execution (design W2). Trigger: the first transaction in ``[t + 5 min, t + trig_to)`` with outcome-0 VWAP ``v >= 0.95`` (token 0 decided) or
    ``v <= 0.05`` (token 1 decided) at time ``tau``. 'no carry room' if the trigger token price + h_W > 0.995 (decided, not entered). Execution: the next
    transaction at or after ``tau + 60 s`` and before the close; entry price = its token price + h_W, capped at 1.0, whatever its level. No such transaction ->
    'unfilled': split (N9) into ``unfilled_outside_window`` (the close lies beyond the stored transaction span ``t + 6 h``, so a later transaction cannot be
    excluded) and ``unfilled_no_trade_before_close`` (the span reaches the close and holds no such transaction); both are counted, excluded from per-share
    means and decided (B6/N9: a decided unit is a filled one). Returns a dict with ``status`` in {not_decided, no_room, unfilled_*, filled}."""
    if tx is None or len(tx[0]) == 0:
        return {"status": "not_decided", "reason": "no transactions"}
    ts, v, sz = tx
    i = np.where((ts >= t + TRIG_FROM_S) & (ts < t + trig_to) & ((v >= DECIDED_HI) | (v <= DECIDED_LO)))[0]
    if len(i) == 0:
        return {"status": "not_decided"}
    j = int(i[0])
    k = 0 if v[j] >= DECIDED_HI else 1
    tau = float(ts[j])
    p_tau = float(v[j]) if k == 0 else 1.0 - float(v[j])
    base = {"k": k, "tau": tau, "p_trigger": p_tau}
    if p_tau + h_w > NO_ROOM:
        return {**base, "status": "no_room"}
    e = np.where((ts >= tau + LATENCY_S) & (ts < close))[0]
    if len(e) == 0:
        return {**base, "status": UNFILLED_OUTSIDE if close > t + TX_AFTER_S else UNFILLED_NO_TRADE}
    q = int(e[0])
    p_entry = float(v[q]) if k == 0 else 1.0 - float(v[q])
    cap_mask = (ts >= tau + LATENCY_S) & (ts < tau + COVER_AFTER_S)
    return {**base, "status": "filled", "tau_e": float(ts[q]), "p_entry": p_entry, "c": min(p_entry + h_w, 1.0), "capacity": float(sz[cap_mask].sum())}


def outcome_y(prices_json: str, k: int) -> tuple[float, bool]:
    """(Y_k, clean) from the guarded outcome vector: [1,0] / [0,1] clean; [0.5,0.5] clean 0.5; anything else unclean -> Y_k = 0 (worst case)."""
    try:
        p = [float(x) for x in json.loads(prices_json)]
    except (ValueError, TypeError):
        return 0.0, False
    if len(p) != 2:
        return 0.0, False
    if sorted(p) == [0.0, 1.0] or p == [0.5, 0.5]:
        return float(p[k]), True
    return 0.0, False


def load_markets(path: Path) -> dict[str, dict]:
    """``markets.csv.gz`` of a prints split (covered span, truncation, status). A missing file is a refusal: W2 never runs on prints of unknown coverage."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"print coverage file {p} missing")
    return {str(r["market_id"]): r for r in c11.read_csv_gz(p)}


def market_available(rec: dict | None) -> bool:
    """A sampled market's prints are usable iff the fetch succeeded (``status`` ok), the span was covered (``covered`` = 1: the oldest print is before t - 6 h or
    the whole history was retrieved) and not truncated. Anything else is 'unavailable' (design 2.6(iv)): excluded and counted, never imputed (B5)."""
    if not rec:
        return False
    return bool(str(rec.get("status")) == "ok" and str(rec.get("covered")) in ("1", "1.0") and str(rec.get("truncated")) in ("0", "0.0"))


def w2_units(sample: list[dict], tx: dict[str, tuple], targets: dict[str, dict], outcomes: dict[str, dict], pred_hours: dict[str, float], *, trig_to: float = TRIG_TO_S,
             h_w: float = H_W, markets: dict[str, dict] | None = None) -> tuple[list[dict], dict]:
    """The decided units of the W2 sample (``sample`` rows from w2_sample.csv.gz, SCREEN or HOLDOUT) with entry, payoff, hold hours and arm S membership
    (``pred_hours`` = exp(L_hat) of the frozen model). ``markets`` = the coverage records of the prints fetch: a sampled market without a usable, covered print
    span (``market_available``) is excluded and counted ``unavailable`` (B5; ``None`` = no coverage data, unit tests only). Returns (filled units, counts incl.
    eligible / unavailable / not_decided / no_room / unfilled_* / filled / decided)."""
    cnt: Counter = Counter()
    out = []
    for s in sample:
        m = str(s["market_id"])
        cnt["eligible"] += 1
        if markets is not None and not market_available(markets.get(m)):
            cnt["unavailable"] += 1
            continue
        t = float(s["end_epoch"])
        tg = targets.get(m)
        d = decide_and_enter(tx.get(m), t, float(tg["close_epoch"]) if tg else math.nan, trig_to=trig_to, h_w=h_w)
        cnt[d["status"]] += 1
        if d["status"] != "filled":
            continue
        oc = outcomes.get(m, {})
        y, clean = outcome_y(oc.get("outcome_prices", ""), d["k"]) if oc else (0.0, False)
        c = d["c"]
        fee = fee_rate(str(s["fee_category"])) * c * (1.0 - c)
        close = float(tg["close_epoch"])
        out.append({"market_id": m, "event": str(s["event_id"]), "date": date_of(t), "cat": str(s["fee_category"]), "t": t, "k": d["k"], "tau": d["tau"], "tau_e": d["tau_e"],
                    "p_entry": d["p_entry"], "c": c, "fee": fee, "Y": y, "clean": clean, "uma_status": str(oc.get("uma_status", "")), "close": close,
                    "H": (close - d["tau_e"]) / HOUR + LIVENESS_H, "q": d["capacity"], "net": y - c - fee, "pred_h": float(pred_hours.get(m, math.nan)),
                    "S": bool(pred_hours.get(m, math.inf) <= S_MAX_HOURS)})
    cnt["decided"] = cnt["filled"]  # B6 / N9: a decided unit is one whose entry rule is satisfied; no_room / unfilled are triggered, counted, not decided
    return out, dict(cnt)


def r_ann_h(units: list[dict], *, hold_floor: float = HOLD_FLOOR_H, rate_key: str = "net") -> float:
    """``8760 * sum(net) / sum(c * max(H, floor))`` (hourly capital-time; the 2 h floor equals the liveness)."""
    den = sum(u["c"] * max(u["H"], hold_floor) for u in units)
    return float(8760.0 * sum(u[rate_key] for u in units) / den) if den > 0 else math.nan


def pool_simulation(units: list[dict], *, pool: float = POOL_USD, window_days: float | None = None) -> dict:
    """Chronological single-pool simulation (design W2): S units in order of ``tau_e``; each buys ``min(free cash / cost, q_i)`` shares (cost per share = c +
    fee, stricter than the design's ``c``; ``q_i`` = recorded traded size in [tau + 60 s, tau + 60 min), summed over both tokens, section 11 N2); cash returns at
    ``close + 1 h`` with ``Y`` per share. The return is annualised over ``window_days`` (the evaluated window: W_screen for Stage 1, W_hold for Stage 2, B9). Mean
    utilisation = time-weighted invested cost / pool between the first entry and the last return (N6)."""
    if window_days is None:
        window_days = (E_SCREEN[1] - E_SCREEN[0]) / DAY
    us = sorted(units, key=lambda u: (u["tau_e"], u["market_id"]))
    cash = pool
    heap: list[tuple[float, int, float]] = []
    pnl = 0.0
    n_in = n_skip_cash = n_skip_cap = 0
    by_month: dict[str, float] = {}
    entered: list[tuple[float, float, float]] = []  # (entry time, return time, cost)
    for idx, u in enumerate(us):
        te = u["tau_e"]
        while heap and heap[0][0] <= te:
            cash += heapq.heappop(heap)[2]
        cost = u["c"] + u["fee"]
        shares = min(cash / cost, u["q"]) if cost > 0 else 0.0
        if shares <= 0:
            if u["q"] <= 0:
                n_skip_cap += 1
            else:
                n_skip_cash += 1
            continue
        cash -= shares * cost
        t_ret = u["close"] + HOUR
        heapq.heappush(heap, (t_ret, idx, shares * u["Y"]))
        entered.append((te, t_ret, shares * cost))
        pnl += shares * (u["Y"] - cost)
        n_in += 1
        mo = month_of(te)
        by_month[mo] = by_month.get(mo, 0.0) + shares * (u["Y"] - cost)
    if entered:
        t0, t1 = min(e[0] for e in entered), max(e[1] for e in entered)
        span = max((t1 - t0) / DAY, 1e-9)
        util = float(min(sum(c * (r - e) for e, r, c in entered) / max(t1 - t0, 1.0) / pool, 1.0))
    else:
        span, util = 0.0, 0.0
    ann = float(pnl / pool * 365.0 / window_days)
    return {"pool_usd": pool, "pnl_usd": float(pnl), "annualised_return": ann, "excess_over_rf": float(ann - RF_RATE), "n_entered": n_in, "n_skipped_cash": n_skip_cash,
            "n_skipped_no_capacity": n_skip_cap, "skipped_cash_share": float(n_skip_cash / len(us)) if us else math.nan, "pnl_by_month": {k: float(v) for k, v in sorted(by_month.items())},
            "mean_utilisation": util, "window_days": window_days, "span_days": float(span)}


def _tail(U: list[dict], alpha: float, n_boot: int = 500) -> dict:
    from . import cb1_history as c1  # noqa: PLC0415

    if not U:
        return {"ok": False, "n": 0}
    losses = np.array([u["Y"] == 0.0 for u in U], bool)
    cl = np.array([u["event"] for u in U])
    pi_star = float(1.0 - np.mean([u["c"] + u["fee"] for u in U]))
    tb = c1.tail_bound(losses, cl, alpha, "upper", n_boot=n_boot, seed=c11.SEED_BOOT)
    return {**tb, "pi_star": pi_star, "floor": TAIL_FLOOR, "ok": bool(tb["bound"] < pi_star - TAIL_FLOOR)}


def _p_ok(p: float, alpha: float, inclusive: bool) -> bool:
    """Stage 1: p < alpha. Stage 2 (Holm at alpha / k): p <= alpha / k (``inclusive``)."""
    return bool(p <= alpha if inclusive else p < alpha)


def _stat_w2(S: list[dict], alpha: float, *, hold_floor: float = HOLD_FLOOR_H) -> dict:
    v = np.array([u["net"] for u in S], float)
    cp = c11.cluster_p(v, {"date": np.array([u["date"] for u in S]), "event": np.array([u["event"] for u in S])}) if len(S) >= 2 else {"testable": False, "p": 1.0, "n": len(S)}
    return {"n": len(S), "net_mean": float(v.mean()) if len(v) else math.nan, "p": cp["p"], "testable": cp["testable"], "ways": cp.get("ways"), "r_ann_h": r_ann_h(S, hold_floor=hold_floor),
            "tail": _tail(S, alpha)}


def window_months(window: tuple[float, float]) -> list[str]:
    """Calendar months (UTC, 'YYYY-MM') that a half-open epoch window ``[a, b)`` overlaps."""
    a, b = window
    d = datetime.fromtimestamp(a, UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    out = []
    while d.timestamp() < b:
        out.append(d.strftime("%Y-%m"))
        d = d.replace(year=d.year + (d.month == 12), month=1 if d.month == 12 else d.month + 1)
    return out


def w2_stat(units: list[dict], counts: dict, *, alpha: float = c11.GATE_P, n_boot: int = 500, window: tuple[float, float] = E_SCREEN, inclusive: bool = False) -> dict:
    """W2 on the filled units of a sample: arm S statistic, floors, attribution, capacity-capped pool gate, binding robustness. ``units`` carry ``Y`` and the
    status fields; ``counts`` is the trigger / fill tally (with ``eligible`` / ``unavailable`` from ``w2_units``: an available share below 60% is 'not testable
    (availability)', B5). The pool return is annualised over ``window`` (W_screen or W_hold, B9); ``inclusive`` = the Stage-2 rule p <= alpha / k. The CB1-A1
    prior is disclosed on every line."""
    S = [u for u in units if u["S"]]
    out: dict = {"counts": counts, "n_filled": len(units), "label": "modelled-cost economic check, reused frame (L1)",
                 "prior_disclosed": "CB1-A1 (post-end decided carry, h2, 57 units) was 'not testable' with a descriptive -4.00c per share on mid-like prices"}
    elig = int(counts.get("eligible", 0) or 0)
    if elig:
        avail = (elig - int(counts.get("unavailable", 0) or 0)) / elig
        out["availability"] = {"eligible": elig, "available": elig - int(counts.get("unavailable", 0) or 0), "share": avail, "min": AVAIL_MIN}
        if avail < AVAIL_MIN:
            return {**out, "testable": False, "advance": False, "p": 1.0, "verdict": "not testable (availability)"}
    st = _stat_w2(S, alpha)
    out["S"] = st
    out["all_decided"] = {"n": len(units), "net_mean": float(np.mean([u["net"] for u in units])) if units else math.nan, "r_ann_h": r_ann_h(units)}
    if not st["testable"]:
        return {**out, "testable": False, "advance": False, "p": 1.0, "verdict": "not testable (S units or clusters)"}
    wd = (window[1] - window[0]) / DAY
    pools = {str(int(p)): pool_simulation(S, pool=p, window_days=wd) for p in (POOL_USD, *POOL_ALT)}
    out["pool"] = pools
    floors = {"net": bool(st["net_mean"] >= W2_NET_FLOOR), "r_ann_h": bool(st["r_ann_h"] >= W2_RANN_FLOOR), "pool_excess": bool(pools[str(int(POOL_USD))]["excess_over_rf"] >= POOL_EXCESS_FLOOR),
              "tail": bool(st["tail"]["ok"]), "p": _p_ok(st["p"], alpha, inclusive)}
    out["floors"] = floors
    a_all = out["all_decided"]
    out["attribution"] = {"credit_clock": bool(st["r_ann_h"] >= ATTR_RANN_MULT * a_all["r_ann_h"] and st["net_mean"] >= a_all["net_mean"] - ATTR_NET_SLACK),
                          "label_if_not": "the carry, not the clock"}
    out["effect"] = st["net_mean"]
    return {**out, "testable": True, "p": float(st["p"])}


def w2_robustness(variants: dict[str, tuple[list[dict], dict]], base_S: list[dict], alpha: float, *, window: tuple[float, float] = E_SCREEN, inclusive: bool = False) -> dict:
    """Binding robustness. ``variants`` maps ``h_w_1c`` / ``trigger_30m`` to (units, counts) built by ``w2_units`` with the changed parameter. Also binding
    (design 2.6(iii), B7): the sign of the mean net per share in EVERY calendar month of the evaluated ``window`` (a month without an S unit does not count as
    met). Reported: the losing share by category ('killed in category'), capacity and net by category."""
    rob: dict = {}
    for name, (us, _c) in variants.items():
        S = [u for u in us if u["S"]]
        rob[name] = {"n": len(S), "net_mean": float(np.mean([u["net"] for u in S])) if S else math.nan, "ok": bool(S and np.mean([u["net"] for u in S]) > 0)}
    rob["hold_floor_6h"] = {"r_ann_h": r_ann_h(base_S, hold_floor=HOLD_FLOOR_ROBUST_H), "ok": bool(r_ann_h(base_S, hold_floor=HOLD_FLOOR_ROBUST_H) >= W2_RANN_FLOOR)}
    months = window_months(window)
    by_m: dict[str, dict] = {}
    for mo in months:
        xs = [u["net"] for u in base_S if month_of(u["t"]) == mo]
        by_m[mo] = {"n": len(xs), "net_mean": float(np.mean(xs)) if xs else math.nan, "ok": bool(xs and np.mean(xs) > 0)}
    rob["by_month_sign"] = {"months": by_m, "ok": bool(by_m) and all(v["ok"] for v in by_m.values())}
    if base_S:
        v = np.array([u["net"] for u in base_S], float)
        top = {}
        for way in ("date", "event"):
            cl = np.array([u[way] for u in base_S])
            keep = c11.c9.top_k_drop_mask(v, cl, c11.TOP_DROP)
            sub = [u for u, k in zip(base_S, keep, strict=True) if k]
            st = _stat_w2(sub, alpha)
            top[way] = {"n": len(sub), "net_mean": st["net_mean"], "p": st["p"], "ok": bool(st["testable"] and _p_ok(st["p"], alpha, inclusive) and st["net_mean"] >= W2_NET_FLOOR)}
        rob["without_top5"] = top
        rob["without_top5_ok"] = all(x["ok"] for x in top.values())
        worst = [{**u, "Y": 0.0, "net": 0.0 - u["c"] - u["fee"]} if u["uma_status"] != "resolved" else u for u in base_S]
        wst = _stat_w2(worst, alpha)
        rob["worst_case_status"] = {"n_rescored": int(sum(1 for u in base_S if u["uma_status"] != "resolved")), "net_mean": wst["net_mean"], "tail_ok": bool(wst["tail"]["ok"]),
                                    "ok": bool(wst["net_mean"] > 0 and wst["tail"]["ok"]),
                                    "note": "the frame carries one uma_status string (no status history): every unit whose status is not 'resolved' is scored Y = 0"}
        rob["capacity"] = {"median_q_shares": float(np.median([u["q"] for u in base_S]))}
        byc: dict[str, list[dict]] = {}
        for u in base_S:
            byc.setdefault(u["cat"], []).append(u)
        rob["by_category_net"] = {c: {"n": len(x), "net_mean": float(np.mean([u["net"] for u in x]))} for c, x in sorted(byc.items())}
        rob["killed_in_category"] = {c: {"n": len(x), "losing_share": float(np.mean([u["Y"] == 0.0 for u in x]))} for c, x in sorted(byc.items())}
    rob["ok"] = bool(all(rob[k]["ok"] for k in ("h_w_1c", "trigger_30m", "hold_floor_6h", "worst_case_status", "by_month_sign") if k in rob) and rob.get("without_top5_ok", False))
    return rob


def w2_decide(res: dict, rob: dict) -> dict:
    """Advance iff testable, every floor holds and the binding robustness holds."""
    adv = bool(res.get("testable") and all((res.get("floors") or {}).values()) and rob.get("ok"))
    return {**res, "robustness": rob, "advance": adv, "verdict": "advance" if adv else "floors or robustness not met"}


# =====================================================================================================================================
# Screen / rep orchestration
# =====================================================================================================================================


def _index_by(rows: list[dict], key: str = "market_id") -> dict[str, dict]:
    return {str(r[key]): r for r in rows}


def refit_range_units(wdir: Path, job: str) -> list[dict]:
    """Units with ends in [2025-10-01, 2026-06-09): fit + gap + the screen part before 06-09 (the W1-rep / W2-rep refit set)."""
    lim = _ep(REP_FIT_END)
    return [u for u in load_units(wdir, ("fit", "gap", "screen"), job=job) if u["end_epoch"] < lim]


def build_fit(units: list[dict], tgt: dict[str, dict], *, use_fit_L: bool = False) -> tuple[list[dict], np.ndarray]:
    L = np.array([u["L_fit"] if use_fit_L else float(tgt[str(u["market_id"])]["L"]) for u in units], float)
    return units, L


def load_nonprimary_units(wdir: Path, *, job: str) -> list[dict]:
    """The non-primary (sports, crypto) fit / gap / screen units, for the DESCRIPTIVE sports-stratum report of ``screen-W`` only (never the census)."""
    if job != "screen-W":
        raise Refused("the non-primary strata file is opened only by screen-W")
    p = Path(wdir) / "units_nonprimary.csv.gz"
    return [_typed(r) for r in c11.read_csv_gz(p)] if p.exists() else []


def non_primary_strata(wdir: Path, fm: dict, tg: dict[str, dict]) -> dict:
    """Descriptive (no p, no gate, never an advance condition): R_B0 / R_B1 of the frozen model on the reported non-primary strata of W_screen (design:
    'the sports stratum'). The strata are absent from the fit (category code 'rare', B0 = overall median)."""
    units = [u for u in load_nonprimary_units(wdir, job="screen-W") if u["window"] == "screen" and str(u["market_id"]) in tg]
    out: dict = {"note": "descriptive; sports and crypto are not in the primary population; W2 samples primary markets only, so there is no W2 sports stratum"}
    for cat in sorted({str(u["fee_category"]).split(":")[0] for u in units}):
        us = [u for u in units if str(u["fee_category"]).split(":")[0] == cat]
        L = np.array([float(tg[str(u["market_id"])]["L"]) for u in us], float)
        pred = predict(fm, us)
        b0 = b0_of(us, fm["b0"])
        b1, _ = b1_of(us, b0)
        em, e0, e1 = np.abs(L - pred), np.abs(L - b0), np.abs(L - b1)
        out[cat] = {"n": len(us), "R_B0": float(1 - em.sum() / e0.sum()) if e0.sum() > 0 else math.nan, "R_B1": float(1 - em.sum() / e1.sum()) if e1.sum() > 0 else math.nan}
    return out


def screen_w(wdir: Path, hist_root: Path, census: dict, *, n_boot: int = c11.N_BOOT, n_draws: int = c11.PLACEBO_DRAWS) -> dict:
    """W1 and W2 Stage 1 on W_screen (the caller checked the freeze, the census labels and the fetch manifests). Stage-1 p threshold 0.01 (strict)."""
    wdir, pdir = Path(wdir), Path(hist_root) / H11
    cw = census.get("W") or {}
    lab1, lab2 = cw.get("label_W1"), cw.get("label_W2")
    res: dict = {}
    if lab1:
        res["W1"] = {"testable": False, "p": 1.0, "advance": False, "verdict": lab1}
    if lab2:
        res["W2"] = {"testable": False, "p": 1.0, "advance": False, "verdict": lab2}
    if lab1 and lab2:
        return res
    fit = load_units(wdir, ("fit",), job="screen-W")
    scr = load_units(wdir, ("screen",), job="screen-W")
    tg = _index_by(open_w_guarded(wdir / "targets_guarded.csv.gz", "screen-W"))
    L_fit = np.array([u["L_fit"] for u in fit], float)
    fm = fit_model(fit, L_fit)
    fm_ns = fit_model(fit, L_fit, drop_sched=True)
    L = np.array([float(tg[str(u["market_id"])]["L"]) for u in scr], float)
    pred_h = {str(u["market_id"]): float(math.exp(p)) for u, p in zip(scr, predict(fm, scr), strict=True)}
    sample = [r for r in c11.read_csv_gz(wdir / "w2_sample.csv.gz")]
    tx = load_tx(pdir / "screen" / "tx.csv.gz")
    mk = load_markets(pdir / "screen" / "markets.csv.gz")
    oc = _index_by(open_w_guarded(pdir / "outcomes_guarded.csv.gz", "screen-W"))
    targets = {m: tg[m] for m in (str(s["market_id"]) for s in sample) if m in tg}
    units2, cnt2 = w2_units(sample, tx, targets, oc, pred_h, markets=mk)
    decided_ids = {u["market_id"] for u in units2}
    dmask = np.array([str(u["market_id"]) in decided_ids for u in scr], bool)
    if not lab1:
        res["W1"] = w1_stat(scr, L, fm, fm_ns, decided_mask=dmask, n_draws=n_draws, n_boot=n_boot, alpha=c11.GATE_P)
        res["W1"]["non_primary_strata"] = non_primary_strata(wdir, fm, tg)
    if not lab2:
        w2 = w2_stat(units2, cnt2, alpha=c11.GATE_P, window=E_SCREEN)
        if w2.get("testable"):
            variants = {"h_w_1c": w2_units(sample, tx, targets, oc, pred_h, h_w=H_W_ROBUST, markets=mk), "trigger_30m": w2_units(sample, tx, targets, oc, pred_h, trig_to=TRIG_TO_ROBUST_S, markets=mk)}
            rob = w2_robustness(variants, [u for u in units2 if u["S"]], c11.GATE_P, window=E_SCREEN)
            w2 = w2_decide(w2, rob)
        else:
            w2 = {**w2, "advance": False}
        res["W2"] = w2
    return res


def rep_w(wdir: Path, hist_root: Path, census: dict, advanced: tuple[str, ...], k: int, *, n_boot: int = c11.N_BOOT, n_draws: int = c11.PLACEBO_DRAWS,
          seals_dir: Path | None = None, committed_seals: bool = True) -> dict:
    """Stage 2 on the sealed W_hold with the model and baselines refit on ends [2025-10-01, 2026-06-09). Judged at alpha / k (inclusive) with alpha = 0.05 and
    no other p gate (B8); the pool return is annualised over W_hold (B9) and the month-sign check runs over W_hold's months (B7)."""
    wdir, pdir = Path(wdir), Path(hist_root) / H11
    verify_hold_seal(wdir, seals_dir, require_committed=committed_seals)
    thr = c11.STAGE2_ALPHA / k
    fitu = refit_range_units(wdir, "rep-W")
    tg = _index_by(open_w_guarded(wdir / "targets_guarded.csv.gz", "rep-W"))
    L_fit = np.array([float(tg[str(u["market_id"])]["L"]) if u["window"] != "fit" else u["L_fit"] for u in fitu], float)
    fm = fit_model(fitu, L_fit)
    fm_ns = fit_model(fitu, L_fit, drop_sched=True)
    dropped = c11.dropped_market_ids(pdir)  # b1: seal-time drops are never analysed (W1 hold units and the W2 sample alike)
    hold = [u for u in load_units(wdir, ("hold",), job="rep-W") if str(u["market_id"]) not in dropped]
    tgh = _index_by(open_w_guarded(wdir / HOLD_DIR / "targets_guarded_hold.csv.gz", "rep-W"))
    L = np.array([float(tgh[str(u["market_id"])]["L"]) for u in hold], float)
    out: dict = {"label": "out-of-time replication on a sealed later window (L2)", "stage2_alpha_over_k": thr, "k": k, "n_dropped_excluded": len(dropped)}
    cw = census.get("W") or {}
    pred_h = {str(u["market_id"]): float(math.exp(p)) for u, p in zip(hold, predict(fm, hold), strict=True)}
    sample = [r for r in c11.read_csv_gz(wdir / HOLD_DIR / "w2_sample_hold.csv.gz") if str(r["market_id"]) not in dropped]
    tx = load_tx(pdir / "holdout" / "tx.csv.gz")
    mk = load_markets(pdir / "holdout" / "markets.csv.gz")
    oc = _index_by(open_w_guarded(wdir / HOLD_DIR / "outcomes_guarded_hold.csv.gz", "rep-W"))
    targets = {m: tgh[m] for m in (str(s["market_id"]) for s in sample) if m in tgh}
    units2, cnt2 = w2_units(sample, tx, targets, oc, pred_h, markets=mk)
    if "W1" in advanced:
        if cw.get("label_W1_hold"):
            out["W1_rep"] = {"testable": False, "p": 1.0, "advance": False, "verdict": cw["label_W1_hold"]}
        else:
            ids = {u["market_id"] for u in units2}
            r = w1_stat(hold, L, fm, fm_ns, decided_mask=np.array([str(u["market_id"]) in ids for u in hold], bool), n_draws=n_draws, n_boot=n_boot, alpha=thr, inclusive=True)
            r["stage2_pass_alpha_over_k"] = bool(r.get("testable") and r.get("p", 1.0) <= thr and r.get("advance"))
            out["W1_rep"] = r
    if "W2" in advanced:
        if cw.get("label_W2_hold"):
            out["W2_rep"] = {"testable": False, "p": 1.0, "advance": False, "verdict": cw["label_W2_hold"]}
        else:
            w2 = w2_stat(units2, cnt2, alpha=thr, window=E_HOLD, inclusive=True)
            if w2.get("testable"):
                variants = {"h_w_1c": w2_units(sample, tx, targets, oc, pred_h, h_w=H_W_ROBUST, markets=mk), "trigger_30m": w2_units(sample, tx, targets, oc, pred_h, trig_to=TRIG_TO_ROBUST_S, markets=mk)}
                w2 = w2_decide(w2, w2_robustness(variants, [u for u in units2 if u["S"]], thr, window=E_HOLD, inclusive=True))
            w2["stage2_pass_alpha_over_k"] = bool(w2.get("testable") and w2.get("p", 1.0) <= thr and w2.get("advance"))
            out["W2_rep"] = w2
    return out


# =====================================================================================================================================
# Censoring (q0224) and census (q0231)
# =====================================================================================================================================


def gamma_window_params(a: float, b: float, offset: int, closed: str = "false") -> dict:
    f = "%Y-%m-%dT%H:%M:%SZ"
    return {"closed": closed, "order": "id", "ascending": "true", "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f),
            "limit": CENSOR_PAGE, "offset": offset}


def count_in_window(lim: hb.Limiter, a: float, b: float, closed: str) -> dict:
    """Binary markets (two outcomes, two token ids) with the given ``closed`` flag and ``endDate`` in ``[a, b]``; ids and ``endDate`` are the only fields read.
    ``capped`` iff the last allowed page is full (the count is then a lower bound). A non-200 reply raises."""
    from . import cb10_common as c10  # noqa: PLC0415

    n, pages, capped = 0, 0, False
    for page in range(CENSOR_PAGES):
        st, data = lim.get(hb.GAMMA_MARKETS, gamma_window_params(a, b, page * CENSOR_PAGE, closed))
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma window status {st}")
        pages += 1
        for m in data:
            if not isinstance(m, dict):
                continue
            if len(c10._listish(m.get("outcomes"))) == 2 and len(c10._listish(m.get("clobTokenIds"))) == 2:
                n += 1
        if len(data) < CENSOR_PAGE:
            break
    else:
        capped = True
    return {"n": n, "pages": pages, "capped": capped}


def count_open_in_window(lim: hb.Limiter, a: float, b: float) -> dict:
    """``closed=false`` count of one frame window (the censored markets). The ``closed=true`` count of the same window (N1, frame-to-query gap) is
    ``count_in_window(..., "true")``."""
    r = count_in_window(lim, a, b, "false")
    return {"open": r["n"], "pages": r["pages"], "capped": r["capped"]}


def censor_share(open_n: np.ndarray, closed_n: np.ndarray) -> float:
    d = float(np.sum(open_n) + np.sum(closed_n))
    return float(np.sum(open_n) / d) if d > 0 else math.nan


def censor_upper(open_n: np.ndarray, closed_n: np.ndarray, *, n_boot: int = c11.N_BOOT, seed: int = c11.SEED_GWC, conf: float = CENSOR_CONF) -> float:
    """One-sided upper ``conf`` bound of the censored share by a window bootstrap (resample windows with replacement)."""
    o, c = np.asarray(open_n, float), np.asarray(closed_n, float)
    n = len(o)
    if n == 0:
        return math.nan
    rng = np.random.default_rng(seed)
    sh = np.empty(n_boot)
    for i in range(n_boot):
        j = rng.integers(0, n, n)
        d = o[j].sum() + c[j].sum()
        sh[i] = o[j].sum() / d if d > 0 else 0.0
    return float(np.quantile(sh, conf))


def w_censoring(root: Path, w_dir: Path, transport, *, rules_sha: str, now: float, rps: float = 2.0, disk_cap: int = int(CENSOR_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
                sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0224 (resumable): one Gamma ``closed=false`` count per seeded frame window (<= 300 windows); ``censoring.json`` with the censored share and its
    window-bootstrap upper 95% bound per window set (gate GWC). A window failing ``MAX_ITEM_ATTEMPTS`` times is labelled unavailable (source) and left out."""
    root = Path(root)
    rdir = c11.require_output_root(root / CENSOR_RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    up = c11.upstream_stall(rdir, Path(w_dir))
    if up:
        return up
    if not c11.manifest_complete(Path(w_dir), (FRAME_STATUS,)):
        raise NotNow("q0224 waits for q0222 (w_frame) to finish")
    done = c11.manifest_complete(rdir, (CENSOR_STATUS,))
    if done:
        return {"stopped": None, "status": CENSOR_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(root, CENSOR_RUN, transport, allowed_run_id=CENSOR_RUN, kind="cb11_w_censoring", label="CB11-W censoring count",
                     params={"windows": N_CENSOR_WINDOWS, "evidence_role": c11.EVIDENCE_ROLE_HIST}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0),
                     budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    wins = list(c11.read_csv_gz(Path(w_dir) / "censor_windows.csv.gz"))
    part = rdir / "censor_partial.jsonl"
    have: dict[str, dict] = {}
    if part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                have[rec["key"]] = rec
    try:
        for w in wins:
            key = f"{w['frame']}|{w['day']}|{w['k']}"
            if key in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                m = fr.manifest(why, {"transient": True})
                m["status"] = "in_progress"
                return m
            try:
                r = count_open_in_window(fr.lim, float(w["a"]), float(w["b"]))
                rc = count_in_window(fr.lim, float(w["a"]), float(w["b"]), "true")
                rec = {"key": key, "set": w["set"], "n_frame_closed": int(w["n_frame_closed"]), **r, "gamma_closed": rc["n"], "gamma_closed_pages": rc["pages"],
                       "gamma_closed_capped": rc["capped"], "status": "ok"}
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[key] = fails.get(key, 0) + 1
                if fails[key] < cm.MAX_ITEM_ATTEMPTS:
                    m = fr.manifest(f"window_failed {key}: {exc}"[:200], {"transient": True})
                    m["status"] = "in_progress"
                    return m
                rec = {"key": key, "set": w["set"], "n_frame_closed": int(w["n_frame_closed"]), "open": 0, "pages": 0, "capped": False, "gamma_closed": 0, "gamma_closed_pages": 0,
                       "gamma_closed_capped": False, "status": "unavailable (source)"}
            with part.open("a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
            have[key] = rec
        doc = censoring_doc(list(have.values()))
        fr.budget.write(rdir / "censoring.json", json.dumps(doc, indent=1, sort_keys=True, default=float).encode())
        fr.record_file(rdir / "censoring.json")
        part.unlink(missing_ok=True)
        fr.counts.update(windows=len(have), unavailable=sum(1 for r in have.values() if r["status"] != "ok"))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": CENSOR_STATUS})
    m["status"] = CENSOR_STATUS
    return m


def censoring_doc(recs: list[dict]) -> dict:
    """Censored share (Σ open / (Σ open + Σ frame closed)) and its window-bootstrap upper 95% bound per window set; the gate GWC fails (``fail``) iff the upper
    bound exceeds 2% in that set, OR any window of the set is capped at the page limit (a lower-bound count cannot confirm the bound, N1), OR fewer than 60% of
    the set's windows are available (design 2.6(iv)). Unavailable windows are excluded and counted. The ``closed=true`` count per window closes the
    frame-to-query gap: ``frame_to_gamma_closed`` = Σ frame closed rows / Σ Gamma closed count over windows not capped on the closed query (diagnostic)."""
    out: dict = {"version": "cb11-censoring-v2", "max_share": CENSOR_MAX_SHARE, "conf": CENSOR_CONF, "avail_min": AVAIL_MIN, "sets": {}, "n_windows": len(recs),
                 "n_unavailable": sum(1 for r in recs if r["status"] != "ok"), "n_capped": sum(1 for r in recs if r.get("capped"))}
    for s in ("fit", "screen", "hold"):
        allr = [r for r in recs if r["set"] == s]
        rs = [r for r in allr if r["status"] == "ok"]
        o = np.array([r["open"] for r in rs], float)
        c = np.array([r["n_frame_closed"] for r in rs], float)
        sh = censor_share(o, c) if len(rs) else math.nan
        up = censor_upper(o, c) if len(rs) else math.nan
        capped = int(sum(1 for r in rs if r.get("capped")))
        avail = len(rs) / len(allr) if allr else 0.0
        unc = [r for r in rs if not r.get("gamma_closed_capped")]
        gc = float(sum(r.get("gamma_closed", 0) for r in unc))
        out["sets"][s] = {"n_windows": len(rs), "n_windows_all": len(allr), "available_share": avail, "open": int(o.sum()) if len(rs) else 0,
                          "frame_closed": int(c.sum()) if len(rs) else 0, "share": sh, "upper95": up, "capped_windows": capped,
                          "gamma_closed_windows_uncapped": len(unc), "gamma_closed": int(gc),
                          "frame_to_gamma_closed": (float(sum(r["n_frame_closed"] for r in unc)) / gc) if gc > 0 else math.nan,
                          "fail": bool((not math.isfinite(up)) or up > CENSOR_MAX_SHARE or capped > 0 or avail < AVAIL_MIN)}
    return out


def mde_w2(n: int) -> float:
    return float(MDE_Z * MDE_SD_W2 * math.sqrt(MDE_DEFF_W2 / n)) if n > 0 else math.nan


def mde_w1(n_dates: int) -> float:
    """W1 MDE (R points) recomputed from the census counts: the declared bootstrap SD (0.02 at 120 end-dates) rescaled by sqrt(120 / end-dates in W_screen); the
    end-date way has the fewest clusters. Never used to change a floor (N6)."""
    return float(MDE_Z * MDE_SD_W1 * math.sqrt(MDE_G_REF / n_dates)) if n_dates > 0 else math.nan


def census_w(wdir: Path, hist_root: Path, censoring: dict | None, coverage: dict | None, *, prints_stall: dict | None = None) -> dict:
    """Counts only (design 2.7 W). No screen / hold wait, outcome, status or net is read: the units loader gives the fit and screen windows (W_fit waits are
    fit features); the guarded files are never opened here. S membership uses the model fitted on W_fit."""
    wdir, pdir = Path(wdir), Path(hist_root) / H11
    fit = load_units(wdir, ("fit",), job="census")
    scr = load_units(wdir, ("screen",), job="census")
    rep = json.loads((wdir / "frame_report.json").read_text())
    listing = json.loads((wdir / "w_hold_listing.json").read_text())
    doc: dict = {"version": "cb11-w-census-v1", "counts_only": True, "frame": {k: rep[k] for k in ("windows", "categories", "frame_source", "end_dates", "events", "end_hour_ny", "fit_category_counts", "f7_nan",
                                                                                                    "non_primary_counts", "merge", "n_units_primary", "n_units_all_strata")},
                 "key_drops": rep["population"]["key_drops_by_source"], "series_rule_drops": rep["population"]["series_rule_drops"], "exclusion": rep.get("exclusion"),
                 "hold": {k: listing[k] for k in ("n_units_hold", "n_end_dates", "n_events", "n_sample_hold", "listing_sha256")}}
    # the listing counts are frame-time counts (the hold files are not opened by the census): UPPER BOUNDS, before the seal-time drops (re-check item 3)
    doc["hold"]["counts_basis"] = "UPPER BOUND: frame-time listing counts, seal-time drops not applied (hold files are not opened by the census)"
    doc["hold"]["n_dropped_markets_at_seal"] = len(c11.dropped_market_ids(pdir)) if (pdir / c11.SEAL_NAME).exists() else None
    label1 = label2 = None
    fit_cnt = Counter(str(u["fee_category"]) for u in fit)
    cats_ok = sorted(c for c in {str(u["fee_category"]) for u in scr} if fit_cnt.get(c, 0) >= GW["fit_min"])
    n_dates = len({date_of(u["end_epoch"]) for u in scr})
    gw = {"units": len(scr), "end_dates": n_dates, "categories_ge200_fit": len(cats_ok), "need": GW, "pass": bool(len(scr) >= GW["units"] and n_dates >= GW["dates"] and len(cats_ok) >= GW["categories"])}
    doc["GW"] = gw
    # GWC
    gwc: dict = {"present": censoring is not None}
    if censoring is None:
        gwc["pass"] = False
        label1 = label2 = "not testable (censoring: count missing)"
    else:
        sc = censoring["sets"]["screen"]
        gwc.update(screen=sc, hold=censoring["sets"]["hold"], pass_screen=not sc["fail"], pass_hold=not censoring["sets"]["hold"]["fail"], n_windows=censoring["n_windows"],
                   n_unavailable=censoring["n_unavailable"], n_capped=censoring["n_capped"])
        gwc["pass"] = bool(gwc["pass_screen"])
        if not gwc["pass"]:
            label1 = label2 = "not testable (censoring)"
    doc["GWC"] = gwc
    if not gw["pass"] and not label1:
        label1 = label2 = "not testable (GW: units, dates or categories)"
    # W2 side
    w2: dict = {}
    if prints_stall is not None:
        label2 = label2 or prints_stall.get("label") or "not testable (source)"
        w2["stall"] = prints_stall
    elif coverage is not None:
        sample = list(c11.read_csv_gz(wdir / "w2_sample.csv.gz"))
        tx = load_tx(pdir / "screen" / "tx.csv.gz")
        mk = {str(r["market_id"]): r for r in c11.read_csv_gz(pdir / "screen" / "markets.csv.gz")} if (pdir / "screen" / "markets.csv.gz").exists() else {}
        avail = [market_available(mk.get(str(s["market_id"]))) for s in sample]
        n_cov = int(sum(avail))
        cov = n_cov / len(sample) if sample else 0.0
        w2["coverage"] = {"n_sample": len(sample), "covered": n_cov, "share": cov, "min": COVER_MIN, "pass": bool(cov >= COVER_MIN)}
        w2["availability"] = {"eligible": len(sample), "available": n_cov, "unavailable": len(sample) - n_cov, "share": cov, "min": AVAIL_MIN, "pass": bool(cov >= AVAIL_MIN)}
        if not w2["availability"]["pass"]:
            label2 = label2 or "not testable (availability)"
        elif not w2["coverage"]["pass"]:
            label2 = label2 or "not testable (source limited)"
        # decided and S counts (feature-only: trigger and next-transaction existence inside the stored span; the close is not used)
        L_fit = np.array([u["L_fit"] for u in fit], float)
        if len(fit) >= 2:
            fm = fit_model(fit, L_fit)
            pred = predict(fm, scr)
            ph = {str(u["market_id"]): float(math.exp(p)) for u, p in zip(scr, pred, strict=True)}
        else:
            ph = {}
        dec = Counter()
        S_rows = []
        n_trig = 0
        for s, ok in zip(sample, avail, strict=True):
            if not ok:  # uncovered / unavailable: excluded and counted, never imputed (B5)
                dec["unavailable"] += 1
                continue
            m = str(s["market_id"])
            t = float(s["end_epoch"])
            d = decide_and_enter(tx.get(m), t, t + TX_AFTER_S)  # the close is a target-side quantity: the census uses the end of the stored transaction span
            dec[d["status"]] += 1
            if d["status"] in ("filled", *UNFILLED, "no_room"):
                n_trig += 1
            # GW2 counts decided S units whose ENTRY RULE IS SATISFIED (status filled): no_room and unfilled are not decided units (B6)
            if d["status"] == "filled" and ph.get(m, math.inf) <= S_MAX_HOURS:
                S_rows.append((str(s["event_id"]), date_of(t), d["status"]))
        n_s = len(S_rows)
        w2["counts"] = {"status": dict(dec), "triggered": n_trig, "decided": dec["filled"], "S_decided": n_s,
                        "note": "S_decided = filled S units (entry rule satisfied); no_room and unfilled are triggered but not decided units; whether the entry transaction precedes the close "
                                "is not used in the census (the stored span end t + 6 h stands in for the close)"}
        gw2 = {"S_decided": n_s, "events": len({e for e, _, _ in S_rows}), "dates": len({d for _, d, _ in S_rows}), "need": GW2,
               "pass": bool(n_s >= GW2["units"] and len({e for e, _, _ in S_rows}) >= GW2["events"] and len({d for _, d, _ in S_rows}) >= GW2["dates"])}
        w2["GW2"] = gw2
        w2["mde_net_per_share"] = mde_w2(n_s)
        if not gw2["pass"]:
            label2 = label2 or "not testable (GW2: decided S units)"
    else:
        label2 = label2 or "not testable (coverage audit missing)"
    doc["W2"] = w2
    doc["mde"] = {"W1_R": mde_w1(n_dates), "W1_end_dates": n_dates, "note": "W1 MDE = (z_0.99 + z_0.80) x 0.02 x sqrt(120 / end-dates in W_screen), from the census count; the 0.20 / 0.10 floors bind, not power. "
                  "W2 MDE uses SD 12c and deff 2 on the filled S units"}
    doc["label_W1"], doc["label_W2"] = label1, label2
    if censoring is not None:
        doc["label_W1_hold"] = doc["label_W2_hold"] = None if not censoring["sets"]["hold"]["fail"] else "not testable (censoring, W_hold)"
    else:
        doc["label_W1_hold"] = doc["label_W2_hold"] = "not testable (censoring: count missing)"
    doc["w1_runs"] = label1 is None
    doc["w2_runs"] = label2 is None
    return doc


def coverage_audit(pdir: Path, wdir: Path) -> dict:
    pdir = Path(pdir)
    sample = list(c11.read_csv_gz(Path(wdir) / "w2_sample.csv.gz"))
    mk = {str(r["market_id"]): r for r in c11.read_csv_gz(pdir / "screen" / "markets.csv.gz")} if (pdir / "screen" / "markets.csv.gz").exists() else {}
    n = sum(1 for s in sample if market_available(mk.get(str(s["market_id"]))))
    return {"n_sample": len(sample), "covered": n, "share": n / len(sample) if sample else 0.0}


# =====================================================================================================================================
# w-prints job (q0223)
# =====================================================================================================================================


def _rows_to_tx(prints: list[dict], t: float) -> list[tuple[float, float, float]]:
    from . import cb10_dlad as dl  # noqa: PLC0415

    return [x for x in dl.aggregate_transactions(prints, 0) if t - TX_BEFORE_S <= x[0] < t + TX_AFTER_S]


def w_prints(root: Path, w_dir: Path, transport, *, rules_sha: str, now: float, rps: float = 2.0, disk_cap: int = int(WPRINTS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
             sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
             data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, free_fn=None, smoke_path: Path | None = None, page_limit: int = DATA_PAGE_LIMIT, pages: int = DATA_PAGES) -> dict:
    """q0223, one resumable chunk: per sampled market (SCREEN then HOLDOUT, one in memory at a time) newest-first prints until the oldest print is before
    ``t - 6 h`` (cap ``pages`` pages of ``page_limit``), aggregated by transaction hash to (time, outcome-0 VWAP, size) inside ``[t - 6 h, t + 6 h)``. Writes
    ``screen/tx.csv.gz`` and ``holdout/tx.csv.gz`` (market id, ts, price, size) and ``markets.csv.gz`` (covered span, truncation). No side, wallet or hash stored."""
    from . import cb11_smoke as sm  # noqa: PLC0415

    root = Path(root)
    rdir = c11.require_output_root(root / PRINTS_RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    up = c11.upstream_stall(rdir, Path(w_dir))
    if up:
        return up
    if smoke_path is not None:
        bad = sm.smoke_failures(smoke_path, sm.FAMILY_NEEDS["W_prints"])
        if bad:
            return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    if not c11.manifest_complete(Path(w_dir), (FRAME_STATUS,)):
        raise NotNow("q0223 waits for q0222 (w_frame) to finish")
    done = c11.manifest_complete(rdir, (PRINTS_STATUS,))
    if done:
        return {"stopped": None, "status": PRINTS_STATUS, "complete": True, "counts": done.get("counts")}
    term = c11.prior_terminal(rdir)
    if term:
        return term
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(root, PRINTS_RUN, transport, allowed_run_id=PRINTS_RUN, kind="cb11_w_prints", label="CB11-W prints", params={"evidence_role": c11.EVIDENCE_ROLE_HIST, "pages": pages, "limit": page_limit},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    c11.bind_manifest(fr)  # manifest_b.json in the shared h11_wprints directory (the q0223 stall manifest.json is left as it is)
    samples = [(s, r) for s, f in (("screen", Path(w_dir) / "w2_sample.csv.gz"), ("holdout", Path(w_dir) / HOLD_DIR / "w2_sample_hold.csv.gz")) for r in c11.read_csv_gz(f)]
    part = rdir / "markets_partial.jsonl"
    have: dict[str, dict] = {}
    if part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                have[rec["market_id"]] = rec
    try:
        for split, r in samples:
            m = str(r["market_id"])
            if m in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                mm = fr.manifest(why, {"transient": True})
                mm["status"] = "in_progress"
                return mm
            t = float(r["end_epoch"])
            try:
                prints, info = fetch_prints_until(fr.lim, r["condition_id"], t - TX_BEFORE_S, limit=page_limit, pages=pages)
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[m] = fails.get(m, 0) + 1
                if fails[m] < cm.MAX_ITEM_ATTEMPTS:
                    mm = fr.manifest(f"prints_failed {m}: {exc}"[:200], {"transient": True})
                    mm["status"] = "in_progress"
                    return mm
                rec = {"market_id": m, "split": split, "t": t, "status": "unavailable (source)", "oldest_ts": math.nan, "truncated": 1, "n_prints": 0, "n_nohash": 0, "n_tx": 0, "covered": 0, "tx": []}
            else:
                tx = _rows_to_tx(prints, t)
                covered = int(not info["truncated"])
                rec = {"market_id": m, "split": split, "t": t, "status": "ok", "oldest_ts": info["oldest_ts"], "truncated": int(info["truncated"]), "n_prints": info["n_prints"],
                       "n_nohash": info["n_nohash"], "n_tx": len(tx), "covered": covered, "tx": [[x[0], x[1], x[2]] for x in tx]}
                del prints
            with part.open("a") as fh:
                fh.write(json.dumps(rec, default=float) + "\n")
            have[m] = rec
        for split in ("screen", "holdout"):
            recs = [have[str(r["market_id"])] for s, r in samples if s == split]
            fr.budget.write_gz_csv(rdir / split / "tx.csv.gz", TX_COLUMNS, ([x["market_id"], a, b, c] for x in recs for a, b, c in x["tx"]))
            fr.budget.write_gz_csv(rdir / split / "markets.csv.gz", MARKET_COLUMNS, ([x[c] for c in MARKET_COLUMNS] for x in sorted(recs, key=lambda y: y["market_id"])))
            fr.record_file(rdir / split / "tx.csv.gz")
            fr.record_file(rdir / split / "markets.csv.gz")
        fr.budget.write_gz_csv(rdir / MARKET_IDS_FILE, ["market_id"], ([m] for m in sorted({str(r["market_id"]) for _, r in samples})))  # ids only, for the other batches' id readers
        fr.record_file(rdir / MARKET_IDS_FILE)
        if (rdir / "outcomes_guarded.csv.gz").exists():
            fr.record_file(rdir / "outcomes_guarded.csv.gz")
        part.unlink(missing_ok=True)
        fr.counts.update(markets=len(have), truncated=sum(int(x["truncated"]) for x in have.values()), unavailable=sum(1 for x in have.values() if x["status"] != "ok"))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": PRINTS_STATUS})
    m["status"] = PRINTS_STATUS
    return m


# =====================================================================================================================================
# Rules
# =====================================================================================================================================


def declared() -> dict:
    import sklearn  # noqa: PLC0415, F401

    return {"windows": {"fit": list(W_FIT), "screen": list(W_SCREEN), "hold": list(W_HOLD), "excluded_dates": list(W_EXCLUDED_DATES), "rep_refit_end": REP_FIT_END},
            "target": {"cap_s": CAP_S, "floor_s": FLOOR_S, "form": "L = ln(min(max(close - end, 60 s), 21 d) / 1 h)"},
            "features": list(FEATURES), "f7": {"days": F7_DAYS, "min_n": F7_MIN, "causal": "close < t", "pool": "all W-population units, all strata and windows, after key drops"},
            "rare_min": RARE_MIN, "model": {**MODEL_PARAMS, "sklearn": SKLEARN_PIN, "numpy": NUMPY_PIN},
            "floors": {"W1_R_B0": W1_FLOOR_B0, "W1_R_B1": W1_FLOOR_B1, "W1_subset_R": W1_SUBSET_R, "attr_sched": ATTR_SCHED_MIN, "W2_net": W2_NET_FLOOR, "W2_rann_h": W2_RANN_FLOOR,
                       "pool_excess": POOL_EXCESS_FLOOR, "risk_free": RF_RATE, "tail_floor": TAIL_FLOOR, "attr_rann_mult": ATTR_RANN_MULT, "attr_net_slack": ATTR_NET_SLACK},
            "w2": {"h_w": H_W, "h_w_robust": H_W_ROBUST, "decided": [DECIDED_LO, DECIDED_HI], "trigger_s": [TRIG_FROM_S, TRIG_TO_S], "trigger_robust_to_s": TRIG_TO_ROBUST_S,
                   "latency_s": LATENCY_S, "no_room": NO_ROOM, "tx_span_s": [TX_BEFORE_S, TX_AFTER_S], "hold_floor_h": HOLD_FLOOR_H, "hold_floor_robust_h": HOLD_FLOOR_ROBUST_H,
                   "liveness_h": LIVENESS_H, "S_max_hours": S_MAX_HOURS, "fee_rate": FEE_RATE, "pool_usd": POOL_USD, "pool_alt": list(POOL_ALT),
                   "capacity": "summed transaction size in [tau + 60 s, tau + 60 min) (hash-aggregated; not split by token; section 11 N2)",
                   "unfilled": list(UNFILLED), "availability_min": AVAIL_MIN, "month_sign": "mean net > 0 in every calendar month of the evaluated window (a month without an S unit is not met)",
                   "pool_cost": "c + fee per share (stricter than the design's c)", "pool_annualised_over": "W_screen (Stage 1) / W_hold (Stage 2)"},
            "stage2": {"p_rule": "p <= alpha / k inclusive with alpha = 0.05 and no other p gate; placebo level min(alpha / k, 0.01)", "stage1_p_rule": "p < 0.01 strict"},
            "sample": {"screen": N_SAMPLE_SCREEN, "hold": N_SAMPLE_HOLD, "per_event": MAX_PER_EVENT, "seeds": [SEED_SAMPLE, SEED_HOLD]},
            "prints": {"limit": DATA_PAGE_LIMIT, "pages": DATA_PAGES, "taker_only": TAKER_ONLY, "stop": "oldest print before t - 6 h", "cover": "not truncated",
                       "max_requests": 7000 * DATA_PAGES},
            "censoring": {"windows": N_CENSOR_WINDOWS, "seed": SEED_CENSOR, "gwc_seed": c11.SEED_GWC, "max_share": CENSOR_MAX_SHARE, "conf": CENSOR_CONF, "page": CENSOR_PAGE, "pages": CENSOR_PAGES, "match_min": CENSOR_MATCH_MIN,
                          "queries_per_window": "closed=false (gate) + closed=true (diagnostic, N1); a capped window fails the set; available windows >= 60%",
                          "max_requests": 2 * N_CENSOR_WINDOWS * CENSOR_PAGES, "frame_seeds": {k: list(v) for k, v in FRAME_SEEDS.items()}},
            "gates": {"GW": GW, "GW2": GW2, "coverage_min": COVER_MIN, "availability_min": AVAIL_MIN, "mde_g_ref": MDE_G_REF}, "columns": {"frame": list(W_COLUMNS), "guarded": list(GUARDED_FRAME_COLUMNS), "units": UNIT_COLUMNS},
            "primary_excluded": list(PRIMARY_EXCLUDED), "sports_in_primary": W_SPORTS_IN_PRIMARY, "placebo": {"seed": c11.PLACEBO_SEEDS["W1_permute"], "draws": c11.PLACEBO_DRAWS},
            "census_forbidden": list(CENSUS_FORBIDDEN)}


def rule_funcs() -> tuple:
    return (window_of, is_primary, wait_L, read_frame_rows, iter_frame_guarded, collect_frame, merge_sources, build_population, rolling_f7, add_features, draw_sample, frame_windows,
            censor_window_set, draw_censor_windows, closed_rows_per_window, load_units, open_w_guarded, verify_hold_seal, category_levels, design_matrix, baseline_b0, b0_of, b1_of,
            fit_model, predict, w1_boot, w1_core, w1_floor_ok, permute_within_cells, w1_placebo, hours_view, w1_robustness, w1_stat, fee_rate, fetch_prints_until, decide_and_enter,
            outcome_y, load_markets, market_available, w2_units, r_ann_h, pool_simulation, _tail, _p_ok, _stat_w2, window_months, w2_stat, w2_robustness, w2_decide, load_nonprimary_units,
            non_primary_strata, screen_w, rep_w, gamma_window_params, count_in_window, count_open_in_window, censor_share, censor_upper, censoring_doc, mde_w1, mde_w2, census_w,
            coverage_audit, w_frame, w_censoring, w_prints, in_frame_windows, declared)
