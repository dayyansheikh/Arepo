# ruff: noqa: E501
"""CB7-X fetch side and counting definitions (docs/research_lab/CREATIVE_BATCH_7.md CB7-X, CB7-F "C1 prints", sections 2.7 and 5.1).

Fetch (q0146, ``xv_prints_fetch``): taker prints of the Polymarket legs of the 316 audited C1 cross-venue pairs, one request series per
UTC day of each pair's study window: ``/trades?market=<cid>&start&end&takerOnly=true&limit=1000&offset`` with at most ``DAY_PAGES``
(10) pages. A day whose last allowed page is still full is **capped**: it is recorded ``capped`` (unavailable), none of its prints is
stored and it is never filled or sampled. A failed request is a failed item (``failed``), never an empty day. Stored per print: pair
key, ``ts``, side mapped to YES terms (+1 ask-side, -1 bid-side), YES price, size. **No wallet field is read or stored.** Resumable by
pair-day. Not ``T_seal``-bound (all rows predate 2026-09) but rows are still capped at ``min(now, cap_at)``; never opens
``cross_venue_live/``; no target is computed.

Definitions (pure functions, used by the census): Kalshi mid, move events, skip windows, print classification into S / S' / N.
Counting only: no mark-out, no price relative to a later price, no outcome.
"""

from __future__ import annotations

import bisect
import json
import math
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as cm
from . import h5_seal
from . import history_backfill as hb

Refused, NotNow, DAY = cm.Refused, cm.NotNow, cm.DAY

XV_RUN_ID = "xv_prints"
XV_COMPLETE = "xv_prints_complete"
XV_TERMINAL_FILE = "XV_TERMINAL.json"
XV_TERMINAL_STATES = ("refused", "disk_budget")
XV_VERSION = "cb7-xv-prints-v1"
DAY_PAGES = 10
PAGE_LIMIT = 1000
PROBE_MIN_ROWS = 100
XV_OUTPUT_CAP_GB = 0.25
LEG_COLUMNS = ["pair_key", "p_market_id", "p_event_id", "k_cat", "condition_id", "win_start", "win_end", "token0"]
PRINT_FILE_COLUMNS = ["pair_key", "ts", "side", "yes_price", "size"]
DAY_COLUMNS = ["pair_key", "day", "status", "n_pages", "n_rows", "n_stored", "capped", "failed", "dropped_cap", "dropped_window", "malformed"]
PARTIAL = "prints_partial.jsonl.gz"
C1_EXPECTED = (316, 183)

# ---- definitions (CB7-X "Definitions (fixed now)") --------------------------------------------------------------------------
K_MAX_AGE_S = 300.0
K_MAX_SPREAD = 0.10
MID_RANGE = (0.03, 0.97)
MOVE_LOOKBACK_S = 600
MOVE_THRESHOLD = 0.01
SKIP_LAG_S = 120
SKIP_LEN_S = 1200
POLY_MARK_MIN_AGE_S = 600
POLY_MARK_MAX_AGE_S = 3600


# ---- the print row ----------------------------------------------------------------------------------------------------------------


def map_trade_row(x: dict) -> list | None:
    """``[ts, yes_price, size, yes_side]`` of one Data API row (outcome index 1 -> ``1 - price``; ``yes_side`` +1 = buy of YES or sell
    of NO = ask-side), or ``None`` when malformed. Reads ``timestamp``, ``outcomeIndex``, ``size``, ``price`` and ``side`` only: no
    wallet, hash or asset field is touched."""
    try:
        ts, idx = int(x["timestamp"]), int(x["outcomeIndex"])
        size, price = float(x["size"]), float(x["price"])
        side = str(x["side"]).upper()
        if idx not in (0, 1) or side not in ("BUY", "SELL") or not (math.isfinite(size) and math.isfinite(price)):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return [ts, price if idx == 0 else 1.0 - price, size, 1 if (side == "BUY") == (idx == 0) else -1]


def day_segments(win_start: float, win_end: float, cap_epoch: float) -> list[tuple[str, int, int]]:
    """UTC days of ``[win_start, min(win_end, cap_epoch))`` as ``(day, start, end_exclusive)``; the first and last day are clipped to the window."""
    lo, hi = int(win_start), int(min(win_end, cap_epoch))
    out = []
    d = lo - lo % 86400
    while d < hi:
        a, b = max(d, lo), min(d + 86400, hi)
        if b > a:
            out.append((datetime.fromtimestamp(d, UTC).strftime("%Y-%m-%d"), a, b))
        d += 86400
    return out


# ---- the C1 legs ------------------------------------------------------------------------------------------------------------------


def load_c1_legs(cv_root: Path | None = None) -> list[dict]:
    """The Polymarket legs of the audited C1 set (316 pairs, 183 events, 517,616 usable steps; ``cb12_x.load_c1`` reproduces it from the
    pinned study files and asserts the counts). Window = the stored series window of the pair. ``condition_id`` comes from a streamed,
    field-restricted read of ``poly_markets.json`` when the row carries one, else it is blank and the fetch resolves it by Gamma id.
    Reads ``cross_venue/`` only; never ``cross_venue_live/``."""
    from . import (
        cb12_x,  # noqa: PLC0415
        provenance,  # noqa: PLC0415
    )

    root = Path(cv_root) if cv_root is not None else provenance.REPO_ROOT / "data-dumps" / "research_lab" / "cross_venue"
    res = cb12_x.load_c1(root, expected=cb12_x.C1_EXPECTED)
    keep = {p.pair_id for p in res["pairs"]}
    rows = {r["k_ticker"]: r for r in json.loads((root / "matches.json").read_text()) if r["k_ticker"] in keep}
    ids = {str(r["p_market_id"]) for r in rows.values()}
    cids: dict[str, str] = {}
    for m in cb12_x.iter_json_array(root / "poly_markets.json"):
        if isinstance(m, dict) and str(m.get("market_id")) in ids:
            c = m.get("condition_id") or m.get("conditionId")
            if c:
                cids[str(m["market_id"])] = str(c)
    legs = []
    for k in sorted(keep):
        r = rows[k]
        z = np.load(root / "series" / f"{k}.npz")
        legs.append({"pair_key": k, "p_market_id": str(r["p_market_id"]), "p_event_id": str(r["p_event_id"]), "k_cat": str(r.get("k_cat", "")),
                     "condition_id": cids.get(str(r["p_market_id"]), ""), "win_start": int(z["win"][0]), "win_end": int(z["win"][1]),
                     "token0": str(r.get("p_token0", ""))})
    return legs


def resolve_condition_ids(lim: hb.Limiter, legs: list[dict]) -> int:
    """Fill blank condition ids by Gamma id lookup (parse guard keeps the condition id only). Returns the number resolved; a network
    failure raises :class:`NotNow` (nothing is written)."""
    need = sorted({leg["p_market_id"] for leg in legs if not leg.get("condition_id")})
    if not need:
        return 0
    found = cm._gamma_lookup(lim, need)
    n = 0
    for leg in legs:
        if not leg.get("condition_id") and found.get(leg["p_market_id"], {}).get("cid"):
            leg["condition_id"] = str(found[leg["p_market_id"]]["cid"])
            n += 1
    return n


# ---- the fetch --------------------------------------------------------------------------------------------------------------------


def fetch_pair_day(fr: cm.Cb7Run, it: dict, day_pages: int) -> dict:
    """One pair-day: pages at offsets 0, 1000, ... (at most ``day_pages``). A short page ends the day. A day whose last allowed page is
    still full is ``capped``: unavailable, nothing stored. A non-200 reply raises (failed item, retried by a later chunk)."""
    rows: list[list] = []
    n_pages = n_raw = dropped_cap = dropped_window = malformed = 0
    capped = False
    for page in range(day_pages):
        status, data = fr.lim.get(hb.DATA_TRADES, {"market": it["condition_id"], "start": it["start"], "end": it["end"] - 1,
                                                    "takerOnly": "true", "limit": PAGE_LIMIT, "offset": page * PAGE_LIMIT})
        if status != 200 or not isinstance(data, list):
            raise c4.ApiError(f"trades status {status}")
        n_pages += 1
        n_raw += len(data)
        for x in data:
            r = map_trade_row(x)
            if r is None:
                malformed += 1
            elif r[0] > fr.cap_epoch:
                dropped_cap += 1
            elif not (it["start"] <= r[0] < it["end"]):
                dropped_window += 1
            else:
                rows.append(r)
        if len(data) < PAGE_LIMIT:
            if len(data) >= PROBE_MIN_ROWS:  # a server that silently caps the page size would look like a short last page
                st2, probe = fr.lim.get(hb.DATA_TRADES, {"market": it["condition_id"], "start": it["start"], "end": it["end"] - 1,
                                                          "takerOnly": "true", "limit": PAGE_LIMIT, "offset": page * PAGE_LIMIT + len(data)})
                if st2 != 200 or not isinstance(probe, list):
                    raise c4.ApiError(f"trades probe status {st2}")
                if probe:
                    fr.page_size_refusal = (f"the Data API returned a short page of {len(data)} rows (< limit {PAGE_LIMIT}) but offset {page * PAGE_LIMIT + len(data)} "
                                            f"still returns rows: the page size is capped server-side; refusing (no silent truncation)")
                    raise c4.ApiError("page size capped")
            break
        if page == day_pages - 1:
            capped = True
    rec = {"item_id": it["item_id"], "pair_key": it["pair_key"], "day": it["day"], "n_pages": n_pages, "n_rows": n_raw,
           "capped": int(capped), "dropped_cap": dropped_cap, "dropped_window": dropped_window, "malformed": malformed,
           "status": "done", "n_stored": 0 if capped else len(rows)}
    if not capped:
        rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
        cm.append_member(fr, fr.rdir / PARTIAL, {"item_id": it["item_id"], "prints": rows})
    return rec


def tally_days(counts: dict[str, int]) -> Callable[[dict], None]:
    def tally(rec: dict) -> None:
        counts["days_done"] = counts.get("days_done", 0) + int(not rec.get("capped"))
        counts["days_capped"] = counts.get("days_capped", 0) + int(bool(rec.get("capped")))
        counts["print_rows_stored"] = counts.get("print_rows_stored", 0) + int(rec.get("n_stored", 0))
        counts["print_rows_dropped_post_cap"] = counts.get("print_rows_dropped_post_cap", 0) + int(rec.get("dropped_cap", 0))
        counts["print_rows_dropped_out_of_window"] = counts.get("print_rows_dropped_out_of_window", 0) + int(rec.get("dropped_window", 0))
        counts["print_rows_malformed"] = counts.get("print_rows_malformed", 0) + int(rec.get("malformed", 0))

    return tally


def finalize_tables(fr: cm.Cb7Run, legs: list[dict], items: list[dict]) -> dict:
    """At completion: ``prints/<pair_key>.csv.gz`` (first member per day wins) and ``days.csv.gz`` (every pair-day with its status);
    the partial file is removed. Days that failed finally are recorded ``failed`` (unavailable)."""
    rdir = fr.rdir
    done = fr.read_progress("item_id")
    by_pair: dict[str, list[list]] = {}
    seen: set[str] = set()
    for rec in c6.iter_partial(rdir / PARTIAL):
        iid = rec["item_id"]
        if iid in seen or done.get(iid, {}).get("status") != "done":
            continue
        seen.add(iid)
        by_pair.setdefault(iid.split("|")[0], []).extend(rec["prints"])
    n_pairs_with_prints = 0
    for k in sorted(by_pair):
        rows = sorted(by_pair[k], key=lambda r: (r[0], r[1], r[2], r[3]))
        fr.budget.write_gz_csv(rdir / "prints" / f"{k}.csv.gz", PRINT_FILE_COLUMNS, ([k, r[0], r[3], r[1], r[2]] for r in rows))
        n_pairs_with_prints += 1
    day_rows = []
    n_failed = 0
    for it in items:
        rec = done.get(it["item_id"])
        st = "failed" if not rec or rec["status"] != "done" else "capped" if rec.get("capped") else "done"
        n_failed += int(st == "failed")
        g = rec or {}
        day_rows.append([it["pair_key"], it["day"], st, g.get("n_pages", 0), g.get("n_rows", 0), g.get("n_stored", 0), int(st == "capped"),
                         int(st == "failed"), g.get("dropped_cap", 0), g.get("dropped_window", 0), g.get("malformed", 0)])
    fr.budget.write_gz_csv(rdir / "days.csv.gz", DAY_COLUMNS, day_rows)
    (rdir / PARTIAL).unlink(missing_ok=True)
    return {"n_pair_day_items": len(items), "pairs_with_prints": n_pairs_with_prints, "days_failed_final": n_failed,
            "days_capped": sum(1 for r in day_rows if r[2] == "capped")}


def write_terminal_marker(rdir: Path, status: str, reason: str, *, wall_clock: Callable[[], float] = time.time) -> Path | None:
    """Durable, write-once record that the q0146 fetch ended in a terminal state (``refused`` or ``disk_budget``). Never called for a
    transient or pending state. Carries the sha256 of ``manifest.json`` if one exists. Returns the path if written, ``None`` if a marker
    already exists (the first record stands)."""
    if status not in XV_TERMINAL_STATES:
        raise Refused(f"terminal marker status must be one of {XV_TERMINAL_STATES}, not {status!r}")
    rdir = Path(rdir)
    rdir.mkdir(parents=True, exist_ok=True)
    mp = rdir / "manifest.json"
    rec = {"run_id": rdir.name, "status": status, "reason": str(reason)[:300], "utc": cm._iso(wall_clock()),
           "manifest_sha256": h5_seal.sha256_file(mp) if mp.exists() else None,
           "rule": "CREATIVE_BATCH_7.md 1.4: a failed or unknown GX makes X1 'not testable'; recorded from how the fetch ended, never from an outcome"}
    path = rdir / XV_TERMINAL_FILE
    try:
        with path.open("x") as fh:
            fh.write(json.dumps(rec, indent=1, sort_keys=True))
    except FileExistsError:
        return None
    return path


def _disk_budget_end(fr, reason, extra: dict | None = None, wall_clock: Callable[[], float] = time.time) -> dict:
    m = cm.disk_budget_end(fr, reason, extra)
    write_terminal_marker(fr.rdir, "disk_budget", str(m.get("stopped") or reason), wall_clock=wall_clock)
    return m


def xv_prints_fetch(
    root: Path, transport: hb.Transport, *, legs: list[dict], day_pages: int = DAY_PAGES, cap_at: str = cm.T_SEAL, rps: float = 4.0,
    disk_cap: int = int(XV_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, now: float | None = None,
    sleep: Callable[[float], None] = time.sleep, live_check: Callable[[], bool] | None = hb.live_pass_or_lock,
    should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time, snapshot_root: Path | None = None,
    health_every_s: float = 600.0, health_check: Callable[[float], tuple[bool, str]] | None = None, data_dumps: Path | None = None,
    data_dumps_cap_gb: float = 40.0, run_id: str = XV_RUN_ID, rules_sha256: str = "",
) -> dict:
    """One resumable chunk of the C1 print fetch. ``root`` is ``<data-dumps>/research_lab/creative_batch7``. Terminal states are
    sticky (``xv_prints_complete``, ``disk_budget``); the chunk ends at the budget (``--budget-min``), a 429 limit or a collector-health
    pause (the queue repeats). Headroom refusal raises :class:`NotNow` (exit 75). No ``T_seal`` deadline: all rows predate 2026-09."""
    root = Path(root)
    cm.refuse_path(root)
    if run_id != XV_RUN_ID:
        raise Refused(f"this command writes only {XV_RUN_ID!r}, not {run_id!r}")
    if day_pages != DAY_PAGES:
        raise Refused(f"day_pages={day_pages} differs from the declaration ({DAY_PAGES})")
    inf = float("inf")
    early = cm.guard_start(root, run_id, wall_clock, inf, XV_COMPLETE)
    if early is not None:
        if early.get("status") == cm.DISK_BUDGET_TOKEN:  # sticky from an earlier chunk: make sure the durable marker exists
            write_terminal_marker(root / run_id, "disk_budget", str(early.get("stopped") or "disk_budget"), wall_clock=wall_clock)
        return early
    if data_dumps is not None:
        c6.require_data_dumps_room(Path(data_dumps), data_dumps_cap_gb, disk_cap / 1024**3)
    legs = [{**x, "win_start": int(float(x["win_start"])), "win_end": int(float(x["win_end"]))} for x in legs]
    fr = cm.Cb7Run(root, run_id, transport, kind="xv_prints", params={"set": "C1", "day_pages": day_pages, "page_limit": PAGE_LIMIT, "n_legs": len(legs),
                                                                         "version": XV_VERSION}, rps=rps, disk_cap=disk_cap, budget_min=budget_min,
                   now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, t_seal_epoch=inf, snapshot_root=snapshot_root,
                   health_every_s=health_every_s, health_check=health_check, cap_at=cap_at, key=b"cb7-no-wallets")
    fr.label = "CB7-X xv_prints"
    fr.rules_sha256 = rules_sha256
    fr.page_size_refusal = ""
    rdir = fr.rdir
    why = fr.unhealthy()
    if why:
        return fr.manifest(why, {"transient": True})
    lp = rdir / "legs.csv.gz"
    try:
        if lp.exists():
            legs = [{**r, "win_start": int(float(r["win_start"])), "win_end": int(float(r["win_end"]))} for r in cm.read_csv_gz(lp)]
        else:
            n_resolved = resolve_condition_ids(fr.lim, legs)
            fr.budget.write_gz_csv(lp, LEG_COLUMNS, ([leg.get(c, "") for c in LEG_COLUMNS] for leg in sorted(legs, key=lambda x: x["pair_key"])))
            fr.counts["condition_ids_resolved_by_gamma"] = n_resolved
    except OSError as exc:
        return _disk_budget_end(fr, exc, wall_clock=wall_clock)
    except (NotNow, c4.ApiError, RuntimeError) as exc:
        return fr.manifest(f"stage_failed: {exc}"[:200], {"transient": True, "status": "in_progress"})
    n_no_cid = sum(1 for x in legs if not x.get("condition_id"))
    items = []
    for leg in sorted(legs, key=lambda x: x["pair_key"]):
        if not leg.get("condition_id"):
            continue  # unresolved leg: no request, recorded in the manifest (its days are unavailable)
        for day, a, b in day_segments(float(leg["win_start"]), float(leg["win_end"]), fr.cap_epoch):
            items.append({"item_id": f"{leg['pair_key']}|{day}", "pair_key": leg["pair_key"], "day": day, "start": a, "end": b,
                          "condition_id": leg["condition_id"]})
    extra = {"n_legs": len(legs), "legs_without_condition_id": n_no_cid, "n_items": len(items), "legs_sha256": cm._sha(sorted(x["pair_key"] for x in legs))}
    def stop_now() -> bool:
        return bool(fr.page_size_refusal) or bool(should_stop and should_stop())

    stopped, pending = c4._fetch_items(fr, items, "item_id", lambda it: fetch_pair_day(fr, it, day_pages), tally_days(fr.counts), stop_now, extra)
    if fr.page_size_refusal:
        write_terminal_marker(rdir, "refused", fr.page_size_refusal, wall_clock=wall_clock)
        raise Refused(fr.page_size_refusal)
    if stopped is None and pending == 0:
        try:
            extra.update(finalize_tables(fr, legs, items))
        except OSError as exc:
            return _disk_budget_end(fr, exc, extra, wall_clock)
        extra.update(complete=True, status=XV_COMPLETE, file_sha256=cm.file_hashes(rdir))
        m = fr.manifest(None, extra)
        m["status"] = XV_COMPLETE
        return m
    if stopped and stopped.startswith("disk_budget"):
        return _disk_budget_end(fr, stopped[len("disk_budget: "):], extra, wall_clock)
    m = fr.manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})
    m["status"] = "in_progress"
    return m


# ---- definitions used by the census ---------------------------------------------------------------------------------------------


def valid_mid(bid: float, ask: float) -> float | None:
    """Kalshi mid of one candle if ``0 < bid < ask < 1``, spread <= 10c and mid in [0.03, 0.97], else ``None``."""
    if not (math.isfinite(bid) and math.isfinite(ask)) or not (0.0 < bid < ask < 1.0) or ask - bid > K_MAX_SPREAD + 1e-12:
        return None
    mid = (bid + ask) / 2.0
    return mid if MID_RANGE[0] - 1e-12 <= mid <= MID_RANGE[1] + 1e-12 else None


class KalshiMid:
    """Mid at any time from 1-minute candles ``[end_ts, bid, ask, last, volume]`` (sorted by ``end_ts`` here): the latest candle with
    ``end_ts <= tau`` and age <= 5 min, which must itself be valid (a stale or invalid latest candle gives no mid; no fall-back to an
    older one)."""

    def __init__(self, kc: np.ndarray) -> None:
        kc = np.asarray(kc, float).reshape(-1, 5) if len(kc) else np.empty((0, 5))
        if len(kc):
            kc = kc[np.argsort(kc[:, 0], kind="stable")]
        self.ts = kc[:, 0].copy() if len(kc) else np.empty(0)
        self.mid: list[float | None] = [valid_mid(float(b), float(a)) for b, a in zip(kc[:, 1], kc[:, 2], strict=True)] if len(kc) else []
        self._mid_arr = np.array([np.nan if m is None else m for m in self.mid], float)

    def at(self, tau: float) -> float | None:
        i = int(np.searchsorted(self.ts, tau, side="right")) - 1
        if i < 0 or tau - self.ts[i] > K_MAX_AGE_S:
            return None
        return self.mid[i]

    def at_many(self, taus: np.ndarray) -> np.ndarray:
        """Vectorised :meth:`at` (NaN where there is no mid)."""
        taus = np.asarray(taus, float)
        if not len(self.ts):
            return np.full(len(taus), np.nan)
        i = np.searchsorted(self.ts, taus, side="right") - 1
        ok = (i >= 0) & (taus - self.ts[np.clip(i, 0, None)] <= K_MAX_AGE_S)
        return np.where(ok, self._mid_arr[np.clip(i, 0, None)], np.nan)

    def grid(self) -> np.ndarray:
        """Every minute end between the first and the last candle."""
        if not len(self.ts):
            return np.empty(0)
        return np.arange(math.ceil(self.ts[0] / 60.0) * 60.0, self.ts[-1] + 1e-9, 60.0)

    def minutes_without_candle(self) -> tuple[int, int]:
        """(minute ends on the grid, of which no candle is stamped exactly there): the density the move-event grid relies on."""
        g = self.grid()
        have = np.isin(g, self.ts)
        return len(g), int((~have).sum())


def move_events(km: KalshiMid) -> tuple[list[float], list[float]]:
    """``(up_taus, down_taus)``: EVERY minute end ``tau`` between the first and last candle with both mids valid and
    ``mid(tau) - mid(tau - 600) >= +0.01`` (up) or ``<= -0.01`` (down). A minute without a candle still has a mid while the latest valid
    candle is at most 5 minutes old."""
    g = km.grid()
    if not len(g):
        return [], []
    d = km.at_many(g) - km.at_many(g - MOVE_LOOKBACK_S)
    up = g[np.isfinite(d) & (d >= MOVE_THRESHOLD - 1e-9)]
    down = g[np.isfinite(d) & (d <= -MOVE_THRESHOLD + 1e-9)]
    return [float(x) for x in up], [float(x) for x in down]


def in_skip(taus: list[float], s: float) -> bool:
    """True iff some event ``tau`` has ``tau + 120 <= s < tau + 120 + 1,200``."""
    i = bisect.bisect_right(taus, s - SKIP_LAG_S) - 1
    return i >= 0 and s < taus[i] + SKIP_LAG_S + SKIP_LEN_S


def skip_windows(taus: list[float]) -> list[tuple[float, float]]:
    """Event windows ``[tau + 120, tau + 1,320)`` merged (overlapping or touching windows join)."""
    out: list[list[float]] = []
    for t in sorted(taus):
        a, b = t + SKIP_LAG_S, t + SKIP_LAG_S + SKIP_LEN_S
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def poly_point_ok(ps_ts: np.ndarray, ps_px: np.ndarray, s: float) -> bool:
    """The latest Polymarket history point stamped in ``[s - 3,600, s - 600]`` has its price in [0.03, 0.97]."""
    i = int(np.searchsorted(ps_ts, s - POLY_MARK_MIN_AGE_S, side="right")) - 1
    if i < 0 or ps_ts[i] < s - POLY_MARK_MAX_AGE_S:
        return False
    return MID_RANGE[0] - 1e-12 <= float(ps_px[i]) <= MID_RANGE[1] + 1e-12


def mark_available(ps_ts: np.ndarray, u: float) -> bool:
    """Existence only (no value is read): a Polymarket history point stamped in ``[u - 3,600, u - 600]`` exists for ``u = s + 3,600``."""
    i = int(np.searchsorted(ps_ts, u - POLY_MARK_MIN_AGE_S, side="right")) - 1
    return bool(i >= 0 and ps_ts[i] >= u - POLY_MARK_MAX_AGE_S)


def classify_prints(prints: Iterator[tuple[float, int]] | list[tuple[float, int]], up: list[float], down: list[float], km: KalshiMid,
                    ps_ts: np.ndarray, ps_px: np.ndarray) -> dict:
    """Count a pair's prints ``(ts, side)`` (side +1 ask-side, -1 bid-side) into S / S' / N. Returns counts plus the per-print records of
    S (``s_ts``, ``s_window``) needed for the cluster counts. Both-states prints and prints without a valid mid on either venue are excluded
    and counted; no price, mark or outcome is used beyond the usability rule."""
    c = {"n_prints": 0, "excluded_both_states": 0, "excluded_unusable": 0, "S": 0, "Sp": 0, "N": 0, "S_mark_available": 0}
    s_ts: list[float] = []
    s_window: list[tuple[str, float]] = []
    wins = {"up": skip_windows(up), "down": skip_windows(down)}
    for ts, side in prints:
        c["n_prints"] += 1
        kmid = km.at(ts)
        if kmid is None or not poly_point_ok(ps_ts, ps_px, ts):
            c["excluded_unusable"] += 1
            continue
        u, d = in_skip(up, ts), in_skip(down, ts)
        if u and d:
            c["excluded_both_states"] += 1
            continue
        if not (u or d):
            c["N"] += 1
            continue
        direction = "up" if u else "down"
        if (side > 0) == u:  # ask-side in up-skip or bid-side in down-skip: the fills the skew rule forgoes
            c["S"] += 1
            c["S_mark_available"] += int(mark_available(ps_ts, ts + 3600.0))
            s_ts.append(ts)
            w = next((w for w in wins[direction] if w[0] <= ts < w[1]), None)
            s_window.append((direction, w[0] if w else float("nan")))
        else:
            c["Sp"] += 1
    return {**c, "s_ts": s_ts, "s_window": s_window}
