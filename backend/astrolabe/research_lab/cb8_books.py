# ruff: noqa: E501
"""CB8-B data side, part 2 (docs/research_lab/CREATIVE_BATCH_8.md CB8-B "Book at t", "pmxt coverage audit", CB8-F, 5.1): the pmxt coverage audit, the
pmxt book states of the day's Up/Down tokens at the checkpoints, the terminal taker prints and the HOLDOUT seal (q0166).

Exploratory historical data (rows before 2026-08-10); NOT bound to T_seal. Counts and derived states only: no outcome is read or stored here. pmxt files
are read by HTTP range requests (row groups pruned on the ``market`` statistics), streamed and never stored; the ingress is metered against the declared
cap and persisted per hour read. A pmxt event is used at ``t`` iff both ``timestamp`` and ``timestamp_received`` are <= ``t``. Prints after ``t_end``
go to ``*_guarded`` files (they reveal the outcome). No wallet is stored.
"""

from __future__ import annotations

import json
import time
from bisect import bisect_right
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import cb4_data as c4
from . import cb6_tail as c6
from . import cb7_common as c7
from . import cb8_common as cm
from . import cb8_updown as U
from . import h5_seal
from . import history_backfill as hb
from . import history_sources as hs

RUN_ID = "updown_b"  # v3 (CB8-B amendment 2026-10-23): new run directory; the v2 run dir "updown" is never opened
COMPLETE = "updown_books_complete"
SOURCE_UNAVAILABLE = "updown_books_source_unavailable"
OFFSETS_S = (600, 300, 120, 60)  # t = t_end - s; 600 is reported only
AUDIT_SEED = "arepo-cb8-pmxt-audit"
AUDIT_HOUR = 13
AUDIT_DAYS = 20
AUDIT_PASS = 0.90
AVAILABLE_MIN = 0.80
INGRESS_CAP_GB = 90.0
ORDER_SEED = "arepo-cb8-updown-order"
TOP_LEVELS = 10
PRINT_PRE_S = 900
PRINT_POST_S = 120
PRINT_PAGES = 3
OUTPUT_CAP_GB = 0.02
SEAL_NAME = "HOLDOUT_SEAL.json"
SEAL_COPY_NAME = "cb8_updown_holdout_SEAL.json"
EVENT_COLS = ["timestamp_received", "timestamp", "market", "event_type", "asset_id", "bids", "asks", "price", "size", "side", "new_tick_size", "fee_rate_bps"]
STATE_COLUMNS = ["market_id", "condition_id", "day", "side", "token_id", "off_s", "plus_s", "t_ms", "has_book", "best_bid", "best_ask", "ask_size", "ask_size_1c",
                 "tick", "fee_bps", "last_event_ms", "fresh", "crossed", "halted", "n_events", "asks_top", "book_status"]
PRINT_COLUMNS = ["market_id", "ts", "idx", "side", "price", "size"]
MARKET_COLUMNS = ["market_id", "day", "split", "asset", "states_status", "lookback", "n_events_up", "n_events_down", "book_unavailable_sides", "prints_status", "n_prints_pre", "n_prints_post"]
DAY_COLUMNS = ["day", "split", "n_markets", "states_status", "prints_status", "n_source_unavailable", "n_book_unavailable", "bytes_read"]
BOOK_OK, BOOK_UNAVAILABLE, NO_EVENTS = "book", "book_unavailable", "no_events"  # per-state label: a snapshot exists / events but no `book` snapshot / no events
CLOCK_SLACK_MS = 3600 * 1000  # a pmxt event clock more than 1 h outside the file's hour means a wrong unit or a wrong file


class HourMissing(Exception):
    """The pmxt hour file is not published (HEAD / GET 404)."""


class HourCorrupt(Exception):
    """The pmxt hour file could not be decoded."""


class CapReached(Exception):
    """The declared pmxt ingress cap is used up."""


def hour_dt(day: str, hh: int) -> datetime:
    return datetime(*U.d_of(day).timetuple()[:3], hh, tzinfo=UTC)


# ---- ingress ---------------------------------------------------------------------------------------------------------------------------


def ingress_used(rdir: Path) -> int:
    p = Path(rdir) / "ingress.jsonl"
    if not p.exists():
        return 0
    return sum(int(json.loads(x)["bytes"]) for x in p.read_text().splitlines() if x.strip())


def ingress_add(rdir: Path, nbytes: int, tag: str) -> None:
    with (Path(rdir) / "ingress.jsonl").open("a") as fh:
        fh.write(json.dumps({"tag": tag, "bytes": int(nbytes)}) + "\n")


# ---- pmxt reading -------------------------------------------------------------------------------------------------------------------------


def _ms(col):
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.compute as pc  # noqa: PLC0415

    return pc.cast(pc.cast(col, pa.timestamp("ms", "UTC")), pa.int64())


def _check_clock(url: str, hour: datetime, *cols) -> None:
    """Raise :class:`HourCorrupt` unless every value of the ms-cast clock columns lies within one hour of the file's hour ``[hour - 1 h, hour + 2 h)``: the blind cast of
    ``_ms`` would otherwise turn a seconds / microseconds / nanoseconds column into plausible-looking but wrong event times."""
    import pyarrow.compute as pc  # noqa: PLC0415

    lo = int(hour.timestamp() * 1000) - CLOCK_SLACK_MS
    hi = int(hour.timestamp() * 1000) + 2 * CLOCK_SLACK_MS
    for col in cols:
        if len(col) == 0:
            continue
        mm = pc.min_max(col).as_py()
        if mm["min"] is None or mm["min"] < lo or mm["max"] >= hi:
            raise HourCorrupt(f"{url}: event clock outside the file's hour (unit or file mismatch)")


def read_hour_events(hour: datetime, tokens: dict[str, str], *, fetch, size_fn, cut_ms: int, gate: Callable[[], None] | None = None,
                     meter: Callable[[int], None] | None = None) -> tuple[dict[str, list[dict]], dict]:
    """Events of ``tokens`` (token -> condition id) in one pmxt hour file with both clocks <= ``cut_ms``, sorted by (venue, receipt) time. Row groups are pruned
    on the ``market`` statistics and the heavy columns (``bids`` / ``asks``) are read only for row groups that have a matching light row. Raises
    :class:`HourMissing` (404) or :class:`HourCorrupt` (also when an event clock of a requested token lies more than 1 h outside the file's hour); a network failure
    (``history_sources.SourceError``) propagates. ``info['bytes']`` is the ingress; ``meter`` (if given) receives the bytes fetched even when the read fails."""
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.compute as pc  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415

    from . import history_sources as hs  # noqa: PLC0415

    url = hs.pmxt_url(hour)
    try:
        size = size_fn(url)
    except FileNotFoundError:
        raise HourMissing(url) from None
    rf = hs.RangeFile(url, size, fetch)
    ev: dict[str, list[dict]] = {t: [] for t in tokens}
    info = {"bytes": 0, "row_groups_total": 0, "row_groups_read": 0, "rows": 0}
    try:
        pf = pq.ParquetFile(rf)
        names = set(pf.schema_arrow.names)
        cols = [c for c in EVENT_COLS if c in names]
        midx = pf.schema_arrow.get_field_index("market")
        want = {c.lower() for c in tokens.values()}
        info["row_groups_total"] = pf.num_row_groups
        value_set = pa.array(sorted(tokens), type=pa.string())
        for rg in range(pf.num_row_groups):
            ms = pf.metadata.row_group(rg).column(midx).statistics
            if ms is not None and ms.has_min_max and not any(hs._b(ms.min) <= c <= hs._b(ms.max) for c in want):
                continue
            if gate is not None:
                gate()
            light = pf.read_row_group(rg, columns=["timestamp_received", "timestamp", "asset_id"])
            mine = pc.is_in(light["asset_id"], value_set=value_set)
            r_ms, v_ms = _ms(light["timestamp_received"]), _ms(light["timestamp"])
            _check_clock(url, hour, r_ms.filter(mine), v_ms.filter(mine))
            keep = pc.and_(mine, pc.and_(pc.less_equal(r_ms, cut_ms), pc.less_equal(v_ms, cut_ms)))
            if not pc.any(keep).as_py():
                continue
            info["row_groups_read"] += 1
            tbl = pf.read_row_group(rg, columns=cols).filter(keep)
            data = {c: tbl[c].to_pylist() for c in cols if c not in ("timestamp_received", "timestamp")}
            rr, vv = _ms(tbl["timestamp_received"]).to_pylist(), _ms(tbl["timestamp"]).to_pylist()
            fee = data.get("fee_rate_bps")
            for i in range(tbl.num_rows):
                ev[data["asset_id"][i]].append({"et": data["event_type"][i], "v": vv[i], "r": rr[i], "bids": data["bids"][i] if "bids" in data else None,
                                                "asks": data["asks"][i] if "asks" in data else None, "price": data["price"][i] if "price" in data else None,
                                                "size": data["size"][i] if "size" in data else None, "side": data["side"][i] if "side" in data else None,
                                                "tick": data["new_tick_size"][i] if "new_tick_size" in data else None, "fee": fee[i] if fee else None})
            info["rows"] += tbl.num_rows
    except (pa.ArrowException, KeyError, ValueError, TypeError, IndexError) as exc:
        raise HourCorrupt(f"{url}: {type(exc).__name__}") from None
    finally:
        info["bytes"] = rf.bytes_fetched
        if meter is not None:
            meter(rf.bytes_fetched)
    for lst in ev.values():
        lst.sort(key=lambda e: (e["v"], e["r"]))
    return ev, info


def read_presence(hour: datetime, cids: list[str], *, fetch, size_fn, gate: Callable[[], None] | None = None,
                  meter: Callable[[int], None] | None = None) -> tuple[set[str], dict]:
    """Condition ids (of ``cids``) that have any event in one pmxt hour file; only the ``market`` column is read (counts only). Raises
    :class:`HourMissing` / :class:`HourCorrupt`."""
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.compute as pc  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415

    from . import history_sources as hs  # noqa: PLC0415

    url = hs.pmxt_url(hour)
    try:
        size = size_fn(url)
    except FileNotFoundError:
        raise HourMissing(url) from None
    rf = hs.RangeFile(url, size, fetch)
    want = {c.lower() for c in cids}
    present: set[str] = set()
    info = {"bytes": 0, "row_groups_read": 0}
    try:
        pf = pq.ParquetFile(rf)
        midx = pf.schema_arrow.get_field_index("market")
        for rg in range(pf.num_row_groups):
            ms = pf.metadata.row_group(rg).column(midx).statistics
            if ms is not None and ms.has_min_max and not any(hs._b(ms.min) <= c <= hs._b(ms.max) for c in want):
                continue
            if gate is not None:
                gate()
            col = pf.read_row_group(rg, columns=["market"])["market"]
            info["row_groups_read"] += 1
            for x in pc.unique(col.cast(pa.string()) if not pa.types.is_binary(col.type) else col.cast(pa.binary())).to_pylist():
                s = (x.decode() if isinstance(x, bytes) else str(x)).lower()
                if s in want:
                    present.add(s)
    except (pa.ArrowException, KeyError, ValueError, TypeError, IndexError) as exc:
        raise HourCorrupt(f"{url}: {type(exc).__name__}") from None
    finally:
        info["bytes"] = rf.bytes_fetched
        if meter is not None:
            meter(rf.bytes_fetched)
    return {c for c in cids if c.lower() in present}, info


# ---- book state ---------------------------------------------------------------------------------------------------------------------------


def _levels(raw) -> dict[float, float]:
    out: dict[float, float] = {}
    if isinstance(raw, str) and raw:
        raw = json.loads(raw)
    for lv in raw or []:
        p, s = (lv["price"], lv["size"]) if isinstance(lv, dict) else (lv[0], lv[1])
        out[float(p)] = float(s)
    return out


def state_at(events: list[dict], t_ms: int, t_end_ms: int) -> dict:
    """The reconstructed state of one token at ``t_ms`` from events (sorted by venue, receipt time) with BOTH clocks <= ``t_ms``: the last ``book`` event, then
    later ``price_change`` events (size = new absolute level total, 0 removes). Reports best bid / ask, size at the ask and within 1c, the best 10 ask levels,
    the tick, the fee rate of the latest event with one, the venue time of the latest event of any type, ``fresh`` (that time >= t - 120 s), ``crossed`` and
    ``halted`` (no event after t_end - 600 s and no ask) and ``book_status``: ``book`` (a snapshot exists), ``book_unavailable`` (events but no ``book`` snapshot by
    ``t``: not "no trade", not halted) or ``no_events``. Crossed books are reported, never repaired."""
    vs = [e["v"] for e in events]
    elig = [e for e in events[: bisect_right(vs, t_ms)] if e["r"] <= t_ms]
    last_v = max((e["v"] for e in elig), default=None)
    book_i = max((i for i, e in enumerate(elig) if e["et"] == "book"), default=None)
    fee = next((float(e["fee"]) for e in reversed(elig) if e["fee"] is not None and str(e["fee"]) != "nan"), None)
    tick = next((str(e["tick"]) for e in reversed(elig) if e["et"] == "tick_size_change" and e["tick"] is not None), None)
    fresh = last_v is not None and last_v >= t_ms - U.FRESH_S * 1000
    base = {"t_ms": t_ms, "has_book": False, "best_bid": None, "best_ask": None, "ask_size": None, "ask_size_1c": None, "tick": tick, "fee_bps": fee,
            "last_event_ms": last_v, "fresh": bool(fresh), "crossed": False, "halted": last_v is None or last_v <= t_end_ms - OFFSETS_S[0] * 1000, "n_events": len(elig),
            "asks_top": [], "book_status": BOOK_OK if book_i is not None else (BOOK_UNAVAILABLE if elig else NO_EVENTS)}
    if book_i is None:
        if elig:  # events without a snapshot: the state is unknown, which is neither a halt nor an empty ask side
            base["halted"] = False
        return base
    bids, asks = _levels(elig[book_i]["bids"]), _levels(elig[book_i]["asks"])
    for e in elig[book_i + 1:]:
        if e["et"] == "price_change" and e["price"] is not None:
            side = bids if str(e["side"]).upper() == "BUY" else asks
            p, s = float(e["price"]), float(e["size"])
            if s <= 0:
                side.pop(p, None)
            else:
                side[p] = s
    al = sorted((p, s) for p, s in asks.items() if s > 0)
    bb = max((p for p, s in bids.items() if s > 0), default=None)
    ba = al[0][0] if al else None
    base.update(has_book=True, best_bid=bb, best_ask=ba, ask_size=al[0][1] if al else None,
                ask_size_1c=sum(s for p, s in al if p <= al[0][0] + 0.01 + 1e-9) if al else None, crossed=bool(bb is not None and ba is not None and bb >= ba),
                asks_top=[[p, s] for p, s in al[:TOP_LEVELS]])
    base["halted"] = bool(base["halted"] and ba is None)
    return base


def token_rows(market: dict, side: str, token: str, events: list[dict], t_end_ms: int) -> list[list]:
    """State rows of one token at every checkpoint (600, 300, 120, 60 s before ``t_end``) and 10 s later (the latency check)."""
    out = []
    for off in OFFSETS_S:
        for plus in (0, U.LATENCY_S):
            t = t_end_ms - off * 1000 + plus * 1000
            s = state_at(events, t, t_end_ms)
            out.append([market["market_id"], market["condition_id"], market["day"], side, token, off, plus, t, int(s["has_book"]), s["best_bid"], s["best_ask"], s["ask_size"],
                        s["ask_size_1c"], s["tick"], s["fee_bps"], s["last_event_ms"], int(s["fresh"]), int(s["crossed"]), int(s["halted"]), s["n_events"],
                        json.dumps(s["asks_top"], separators=(",", ":")), s["book_status"]])
    return out


def day_states(day: str, markets: list[dict], *, fetch, size_fn, gate: Callable[[], None] | None = None,
               meter: Callable[[int], None] | None = None) -> tuple[list[list], list[dict], dict]:
    """Book-state rows of every market of ``day`` from the pmxt hour 15Z (the 14Z lookback only for tokens without a ``book`` event by the cut). A market
    whose tokens have no event in 14Z-15Z is ``source_unavailable`` (its own label, never "no trade"); a market with events on a token that never has a ``book``
    snapshot is ``book_unavailable`` (its own label; the rows keep a per-state ``book_status``). A missing or corrupt 15Z hour raises
    :class:`HourMissing` / :class:`HourCorrupt` (the day is unavailable for all its markets). Returns (rows, per-market info, hour info)."""
    t_end_ms = int(U.t_end(day) * 1000)
    cut = t_end_ms - (U.CHECKPOINTS_S[-1] - U.LATENCY_S) * 1000  # the last state needed is t_end - 60 s + 10 s
    tokens: dict[str, str] = {}
    for m in markets:
        tokens[m["token_up"]] = m["condition_id"]
        tokens[m["token_down"]] = m["condition_id"]
    ev15, i15 = read_hour_events(hour_dt(day, 15), tokens, fetch=fetch, size_fn=size_fn, cut_ms=cut, gate=gate, meter=meter)
    info = {"bytes": i15["bytes"], "row_groups_read": i15["row_groups_read"], "lookback_tokens": 0, "lookback_status": "not_needed"}
    first_t = t_end_ms - OFFSETS_S[0] * 1000  # the earliest state used (600 s, reported only): a token without a book event by then needs the 14Z lookback
    need = {t: c for t, c in tokens.items() if not any(e["et"] == "book" and e["v"] <= first_t and e["r"] <= first_t for e in ev15[t])}
    ev14: dict[str, list[dict]] = {}
    if need:
        info["lookback_tokens"] = len(need)
        try:
            ev14, i14 = read_hour_events(hour_dt(day, 14), need, fetch=fetch, size_fn=size_fn, cut_ms=cut, gate=gate, meter=meter)
            info["bytes"] += i14["bytes"]
            info["lookback_status"] = "read"
        except (HourMissing, HourCorrupt):
            info["lookback_status"] = "hour_unavailable"
    rows, minfo = [], []
    for m in markets:
        evs = {s: sorted(ev14.get(m[f"token_{s}"], []) + ev15[m[f"token_{s}"]], key=lambda e: (e["v"], e["r"])) for s in ("up", "down")}
        n_up, n_down = len(evs["up"]), len(evs["down"])
        if n_up + n_down == 0:
            minfo.append({"market_id": m["market_id"], "status": "source_unavailable", "n_events_up": 0, "n_events_down": 0,
                          "lookback": "read" if m["token_up"] in need else "not_needed"})
            continue
        for s in ("up", "down"):
            rows += token_rows(m, s, m[f"token_{s}"], evs[s], t_end_ms)
        no_book = [s for s in ("up", "down") if evs[s] and not any(e["et"] == "book" for e in evs[s])]
        minfo.append({"market_id": m["market_id"], "status": BOOK_UNAVAILABLE if no_book else "ok", "n_events_up": n_up, "n_events_down": n_down,
                      "book_unavailable_sides": "+".join(no_book), "lookback": "read" if m["token_up"] in need else "not_needed"})
    return rows, minfo, info


def terminal_prints(lim: hb.Limiter, cid: str, t_end_epoch: float, key: bytes = b"cb8-no-wallets", max_pages: int = PRINT_PAGES) -> tuple[list[list], list[list], dict]:
    """Taker prints of one condition id in ``[t_end - 15 min, t_end + 2 min]`` (venue time). Returns (pre rows ``ts < t_end``, post rows ``ts >= t_end`` for the
    guarded file, info). A capped window yields no rows and ``info['capped']``. No wallet is kept (the hash is dropped on the floor)."""
    a, b = int(t_end_epoch) - PRINT_PRE_S, int(t_end_epoch) + PRINT_POST_S
    rows, info = cm.windowed_prints(lim, cid, a, b, max_pages, key, limit=U.PRINT_LIMIT)
    if info["capped"]:
        return [], [], info
    flat = [[p["ts"], p["idx"], p["side"], p["price"], p["size"]] for p in rows]
    flat.sort()
    return [r for r in flat if r[0] < t_end_epoch], [r for r in flat if r[0] >= t_end_epoch], info


# ---- audit, order -------------------------------------------------------------------------------------------------------------------------


def audit_day_list(days_by_split: dict[str, list[str]], n: int = AUDIT_DAYS, seed: str = AUDIT_SEED) -> list[str]:
    """``n`` seeded B days, half SCREEN and half HOLDOUT (days that have at least one frame market)."""
    half = n // 2
    out: list[str] = []
    for s in ("screen", "holdout"):
        out += sorted(days_by_split.get(s, []), key=lambda d: hb._rank(seed, d))[:half]
    return sorted(out)


def day_order(days_by_split: dict[str, list[str]], seed: str = ORDER_SEED) -> list[str]:
    """All days in a seeded order that alternates SCREEN and HOLDOUT, so an ingress cap truncates both evenly."""
    a = sorted(days_by_split.get("screen", []), key=lambda d: hb._rank(seed, d))
    b = sorted(days_by_split.get("holdout", []), key=lambda d: hb._rank(seed, d))
    out = []
    for i in range(max(len(a), len(b))):
        if i < len(a):
            out.append(a[i])
        if i < len(b):
            out.append(b[i])
    return out


def coverage_audit(days: list[str], markets_by_day: dict[str, list[dict]], split_of: dict[str, str], *, fetch, size_fn, rdir: Path,
                   should_stop: Callable[[], bool] | None = None, hour: int = AUDIT_HOUR) -> dict:
    """Count, per (market, day) of the audited days, whether the market's condition id has any event in the hour ``hour`` (13Z, a non-checkpoint hour).
    PASS iff at least 90% of ALL pairs are present (an unreadable hour counts its pairs as absent; reported separately). Counts only."""
    n_pairs = n_present = n_pairs_readable = n_present_readable = 0
    per_day = []
    for d in days:
        cids = [m["condition_id"] for m in markets_by_day[d]]
        try:
            present, _ = read_presence(hour_dt(d, hour), cids, fetch=fetch, size_fn=size_fn, meter=lambda n, d=d: ingress_add(rdir, n, f"audit:{d}"))
            status = "ok"
        except HourMissing:
            present, status = set(), "hour_missing"
        except HourCorrupt:
            present, status = set(), "hour_corrupt"
        n_pairs += len(cids)
        n_present += len(present)
        if status == "ok":
            n_pairs_readable += len(cids)
            n_present_readable += len(present)
        per_day.append({"day": d, "split": split_of[d], "n_markets": len(cids), "n_present": len(present), "status": status})
    share = n_present / n_pairs if n_pairs else 0.0
    return {"hour": hour, "n_days": len(days), "n_pairs": n_pairs, "n_present": n_present, "share": share, "pass_threshold": AUDIT_PASS, "pass": bool(n_pairs and share >= AUDIT_PASS),
            "n_days_hour_unreadable": sum(1 for p in per_day if p["status"] != "ok"), "share_readable_only": (n_present_readable / n_pairs_readable) if n_pairs_readable else None,
            "per_day": per_day}


# ---- the job ---------------------------------------------------------------------------------------------------------------------------


def _read_frame(frame_dir: Path) -> list[dict]:
    return list(c7.read_csv_gz(Path(frame_dir) / "frame.csv.gz"))


def _split_dir(rdir: Path, split: str) -> Path:
    return rdir / split


def _fail_counts(pf: Path) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                j = json.loads(line)
                out[(j["day"], j["stage"])] = out.get((j["day"], j["stage"]), 0) + 1
    return out


def books_fetch(root: Path, transport, *, rules_sha: str, fetch, size_fn, frame_run: str = U.RUN_FRAME, smoke_path: Path = U.SMOKE_DEFAULT, require_smoke: bool = True,
                ingress_cap_gb: float = INGRESS_CAP_GB, audit_hour: int = AUDIT_HOUR, audit_days: int = AUDIT_DAYS, rps: float = 2.0,
                disk_cap: int = int(OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
                data_dumps_cap_gb: float = cm.DATA_DUMPS_FETCH_CAP_GB, wall_clock: Callable[[], float] = time.time, sleep=time.sleep, live_check=None, health_check=None,
                snapshot_root: Path | None = None, should_stop: Callable[[], bool] | None = None, now: float | None = None, seals_dir: Path | None = None,
                run_id: str = RUN_ID, is_committed: Callable[[Path], bool] | None = None) -> dict:
    """One resumable chunk of q0166. Refusals first (run id, root, smoke b and c, the finished frame run and its file hashes), headroom (exit 75), sticky
    end states, then: the count-only coverage audit (first stage; FAIL ends the run ``updown_books_source_unavailable`` and no checkpoint is extracted), per day
    (seeded order alternating SCREEN and HOLDOUT) the book states and the terminal prints (HOLDOUT days into ``holdout/``), the ingress cap (remaining days are
    unavailable, counted), and the HOLDOUT seal."""
    root = Path(root)
    cm.refuse_run_id(run_id, RUN_ID)
    cm.refuse_path(root)
    if require_smoke:
        U.smoke_ok(smoke_path, rules_sha, ("b", "c"))
    fdir = root / frame_run
    fman_p = fdir / "manifest.json"
    if not fman_p.exists():
        raise cm.Refused(f"frame run {fdir} has no manifest; run updown-frame first")
    fman = json.loads(fman_p.read_text())
    if not (fman.get("complete") is True and fman.get("status") == U.FRAME_COMPLETE and not fman.get("stopped")):
        raise cm.Refused(f"frame run {fdir.name} is not {U.FRAME_COMPLETE}")
    cm.verify_manifest_files(fdir, fman)
    rdir = root / run_id
    term = cm.prior_terminal(rdir)
    if term:
        return term
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None:
        return {"stopped": None, "status": prior.get("status") or COMPLETE, "complete": True, "counts": prior.get("counts")}
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    fr = cm.open_run(root, run_id, transport, allowed_run_id=RUN_ID, kind="cb8_updown_books", label="CB8-B books",
                     params={"ingress_cap_gb": ingress_cap_gb, "audit_hour": audit_hour, "audit_days": audit_days, "frame_manifest_sha256": h5_seal.sha256_file(fman_p),
                             "evidence_role": "exploratory_historical"},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
                     wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    why = fr.unhealthy()
    if why:
        m = fr.manifest(why, {"transient": True})
        m["status"] = "in_progress"
        return m
    cap_bytes = ingress_cap_gb * 1e9
    frame = _read_frame(fdir)
    markets_by_day: dict[str, list[dict]] = {}
    for r in frame:
        markets_by_day.setdefault(r["day"], []).append(r)
    split_of = {d: U.day_split(d) for d in markets_by_day}
    days_by_split = {s: sorted(d for d, sp in split_of.items() if sp == s) for s in ("screen", "holdout")}
    try:
        # stage 1: the count-only coverage audit
        audit_p = rdir / "audit.json"
        if not audit_p.exists():
            if ingress_used(rdir) >= cap_bytes:
                m = fr.manifest("ingress_cap", {"status": "in_progress"})
                return m
            audit = coverage_audit(audit_day_list(days_by_split, audit_days), markets_by_day, split_of, fetch=fetch, size_fn=size_fn, rdir=rdir, should_stop=should_stop, hour=audit_hour)
            fr.budget.write(audit_p, json.dumps(audit, indent=1, sort_keys=True).encode())
            fr.record_file(audit_p)
        audit = json.loads(audit_p.read_text())
        fr.extra_state["audit"] = {k: audit[k] for k in ("n_days", "n_pairs", "n_present", "share", "pass", "n_days_hour_unreadable", "share_readable_only")}
        if not audit["pass"]:
            (rdir / "AUDIT_FAIL.json").write_text(json.dumps({"run_id": run_id, "audit": fr.extra_state["audit"], "rule": "design CB8-B audit: PASS iff >= 90% of (market, day) pairs present; "
                                                              "FAIL -> B not testable (source unavailable); no checkpoint extracted"}, indent=1, sort_keys=True))
            m = fr.manifest(None, {"complete": True, "status": SOURCE_UNAVAILABLE})
            m["status"] = SOURCE_UNAVAILABLE
            return m
        # stage 2: per day, states then prints
        part, pf = rdir / "days_partial.jsonl.gz", rdir / "days_fail.jsonl"
        done = {(r["day"], r["stage"]): r for r in c6.iter_partial(part)}
        fails = _fail_counts(pf)
        retry = False
        order = day_order(days_by_split)
        for d in order:
            sp = split_of[d]
            sdir = _split_dir(rdir, sp)
            for stage in ("states", "prints"):
                if (d, stage) in done:
                    continue
                why = fr.stop_reason(should_stop)
                if why:
                    m = fr.manifest(why, {"transient": True})
                    m["status"] = "in_progress"
                    return m
                if stage == "states" and ingress_used(rdir) >= cap_bytes:
                    rec = {"day": d, "stage": stage, "status": "ingress_cap", "markets": []}
                    c7.append_member(fr, part, rec)
                    done[(d, stage)] = rec
                    fr.counts["days_ingress_cap"] = fr.counts.get("days_ingress_cap", 0) + 1
                    continue
                if stage == "prints" and done[(d, "states")]["status"] == "ingress_cap":
                    rec = {"day": d, "stage": stage, "status": "ingress_cap", "markets": []}
                    c7.append_member(fr, part, rec)
                    done[(d, stage)] = rec
                    continue
                try:
                    if stage == "states":
                        rows, minfo, hinfo = day_states(d, markets_by_day[d], fetch=fetch, size_fn=size_fn, meter=lambda n, d=d: ingress_add(rdir, n, f"states:{d}"))
                        p = sdir / f"{d}.states.csv.gz"
                        fr.budget.write_gz_csv(p, STATE_COLUMNS, rows)
                        rec = {"day": d, "stage": stage, "status": "ok", "markets": minfo, "bytes": hinfo["bytes"], "lookback_status": hinfo["lookback_status"]}
                    else:
                        pre, post, minfo = [], [], []
                        te = U.t_end(d)
                        for m in markets_by_day[d]:
                            a, b, info = terminal_prints(fr.lim, m["condition_id"], te)
                            pre += [[m["market_id"], *r] for r in a]
                            post += [[m["market_id"], *r] for r in b]
                            minfo.append({"market_id": m["market_id"], "status": "capped" if info["capped"] else "ok", "n_pre": len(a), "n_post": len(b)})
                        fr.budget.write_gz_csv(sdir / f"{d}.prints.csv.gz", PRINT_COLUMNS, pre)
                        fr.budget.write_gz_csv(sdir / f"{d}.prints_post_guarded.csv.gz", PRINT_COLUMNS, post)
                        rec = {"day": d, "stage": stage, "status": "ok", "markets": minfo}
                except (HourMissing, HourCorrupt) as exc:
                    rec = {"day": d, "stage": stage, "status": "hour_missing" if isinstance(exc, HourMissing) else "hour_corrupt", "markets": []}
                except (cm.ApiError, RuntimeError, Exception) as exc:
                    if isinstance(exc, OSError):
                        raise
                    fails[(d, stage)] = fails.get((d, stage), 0) + 1
                    with pf.open("a") as fh:
                        fh.write(json.dumps({"day": d, "stage": stage, "error": f"{type(exc).__name__}: {exc}"[:120]}) + "\n")
                    if fails[(d, stage)] < cm.MAX_ITEM_ATTEMPTS:
                        fr.counts["request_failures"] = fr.counts.get("request_failures", 0) + 1
                        retry = True
                        continue
                    rec = {"day": d, "stage": stage, "status": "failed", "markets": []}
                c7.append_member(fr, part, rec)
                done[(d, stage)] = rec
                fr.counts[f"{stage}_{rec['status']}"] = fr.counts.get(f"{stage}_{rec['status']}", 0) + 1
        if retry:
            m = fr.manifest("pending_retry", {"transient": True})
            m["status"] = "in_progress"
            return m
        finalize_books(fr, rdir, done, markets_by_day, split_of)
        seal = seal_holdout(fr, rdir, frame, rules_sha, seals_dir=Path(seals_dir or cm.SEALS_DIR), frame_dir=fdir, is_committed=is_committed)
        fr.record_file(rdir / SEAL_NAME)
        fr.extra_state["seal"] = seal
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    except hs.SourceError:  # a network failure in the audit stage (per-day failures are counted attempts instead): resume later, nothing is decided
        m = fr.manifest("audit_source_error", {"transient": True})
        m["status"] = "in_progress"
        return m
    m = fr.manifest(None, {"complete": True, "status": COMPLETE})
    m["status"] = COMPLETE
    return m


def finalize_books(fr: cm.Cb8Run, rdir: Path, done: dict, markets_by_day: dict[str, list[dict]], split_of: dict[str, str]) -> None:
    """``days.csv.gz`` and ``markets.csv.gz`` from the day records, then the hash of every file; the partials are dropped last."""
    drows, mrows = [], []
    for d in sorted(markets_by_day):
        st, pr = done[(d, "states")], done[(d, "prints")]
        ms = {m["market_id"]: m for m in st["markets"]}
        pm = {m["market_id"]: m for m in pr["markets"]}
        n_unav = n_book_unav = 0
        for mk in sorted(markets_by_day[d], key=lambda x: x["market_id"]):
            s = ms.get(mk["market_id"])
            status = s["status"] if s else ("day_" + st["status"])
            n_book_unav += int(status == BOOK_UNAVAILABLE)
            n_unav += int(status not in ("ok", BOOK_UNAVAILABLE))
            p = pm.get(mk["market_id"])
            mrows.append([mk["market_id"], d, split_of[d], mk["asset"], status, (s or {}).get("lookback", ""), (s or {}).get("n_events_up", ""), (s or {}).get("n_events_down", ""),
                          (s or {}).get("book_unavailable_sides", ""), (p or {}).get("status", "day_" + pr["status"]), (p or {}).get("n_pre", ""), (p or {}).get("n_post", "")])
        drows.append([d, split_of[d], len(markets_by_day[d]), st["status"], pr["status"], n_unav, n_book_unav, st.get("bytes", "")])
    fr.budget.write_gz_csv(rdir / "days.csv.gz", DAY_COLUMNS, drows)
    fr.budget.write_gz_csv(rdir / "markets.csv.gz", MARKET_COLUMNS, mrows)
    for p in sorted(rdir.rglob("*.csv.gz")):
        fr.record_file(p)
    for name in ("ingress.jsonl", "audit.json"):  # the metered ingress and the audit result are final here (no further chunk appends to them)
        if (rdir / name).exists():
            fr.record_file(rdir / name)
    (rdir / "days_partial.jsonl.gz").unlink(missing_ok=True)
    (rdir / "days_fail.jsonl").unlink(missing_ok=True)


def seal_copy_ids_audited(seals_dir: Path, own: tuple[str, ...] = ("h9_flow_SEAL.json", "cb8_updown_holdout_SEAL.json"), *,
                          is_committed: Callable[[Path], bool] | None = None) -> tuple[set[str], list[str], list[dict], dict[str, str]]:
    """Market ids named in every seal copy under ``seals_dir`` except CB8's own, like ``flow.seal_copy_ids`` but nothing is skipped silently. Returns (ids, used
    names, skipped ``[{"name", "reason"}]``, sha256 per used copy). With ``is_committed`` a copy that is not committed (identical to HEAD) is skipped with the
    reason ``not_committed`` (the drops cover copies committed by then); an unparseable copy is ``unparseable:<ExceptionType>`` and one without market ids
    ``no_market_ids``."""
    w = c4._cb2w()
    ids: set[str] = set()
    used: list[str] = []
    skipped: list[dict] = []
    shas: dict[str, str] = {}
    for p in sorted(Path(seals_dir).glob("*_SEAL.json")):
        if p.name in own:
            continue
        if is_committed is not None and not is_committed(p):
            skipped.append({"name": p.name, "reason": "not_committed"})
            continue
        try:
            found = w.seal_ids_from_copy(p)
        except Exception as exc:
            skipped.append({"name": p.name, "reason": f"unparseable:{type(exc).__name__}"})
            continue
        if not found:
            skipped.append({"name": p.name, "reason": "no_market_ids"})
            continue
        ids |= found
        used.append(p.name)
        shas[p.name] = h5_seal.sha256_file(p)
    return ids, used, skipped, shas


def seal_holdout(fr: cm.Cb8Run, rdir: Path, frame: list[dict], rules_sha: str, *, seals_dir: Path, frame_dir: Path | None = None,
                 is_committed: Callable[[Path], bool] | None = None) -> dict:
    """Final stage. Re-hash every file of the manifest (any change is a refusal), record seal-time drops by id and key against every seal copy committed by now
    (``DROPPED_*`` blocks in ``drops.csv.gz``; sealed files are never edited), hash the ``holdout/`` listing and write ``HOLDOUT_SEAL.json`` plus the committed
    copy ``cb8_updown_holdout_SEAL.json`` (never overwritten with different content). More than 2% of drop ids without metadata -> disjointness unverified."""
    seal_p = rdir / SEAL_NAME
    if seal_p.exists():
        return json.loads(seal_p.read_text())
    man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
    man_files = {**(man.get("file_sha256") or {}), **fr.file_sha256}
    n_checked = cm.verify_manifest_files(rdir, {"file_sha256": man_files})
    ids, used, skipped, used_shas = seal_copy_ids_audited(seals_dir, is_committed=is_committed)
    keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    missing_meta = 0
    if ids:
        found, _ = c6.lookup_keys(fr.lim, sorted(ids))
        missing_meta = len(ids) - len(found)
        for k in found.values():
            keys["event"].update(e for e in str(k.get("event_ids") or "").split(";") if e)
            if k.get("neg_risk_market_id"):
                keys["neg_risk_market"].add(k["neg_risk_market_id"])
            keys["series"].update(s for s in str(k.get("series_ids") or "").split(";") if s)
    unverified = bool(ids) and missing_meta / len(ids) > U.MAX_UNVERIFIED_KEY_SHARE
    rows, n = [], {"KEPT": 0, "DROPPED_SEAL_COPIES": 0}
    for r in frame:
        why = (["id"] if r["market_id"] in ids else []) + [t for t in c7.key_types_matched(r, keys) if t in U.B_KEY_TYPES]  # v3: same key set as the frame (series waived)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            rows.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        else:
            n["KEPT"] += 1
    rows.sort()
    (rdir / "drops.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], rows))
    files = h5_seal.list_files(rdir)
    holdout = {k: v for k, v in files.items() if k.startswith("holdout/")}
    if frame_dir is not None:  # the frame run's HOLDOUT kline features and strikes are part of the sealed set (design 1.3), re-hashed against its manifest
        fman = json.loads((Path(frame_dir) / "manifest.json").read_text())
        cm.verify_manifest_files(Path(frame_dir), fman)
        holdout.update({f"frame_{k}": v for k, v in h5_seal.list_files(Path(frame_dir)).items() if k.startswith(U.HOLDOUT_SUBDIR + "/")})
    doc = {"seal_version": "cb8-updown-holdout-seal-v1", "run_id": RUN_ID, "sealed_utc": cm.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": rules_sha,
           "listing_sha256": h5_seal.listing_sha256(holdout), "n_holdout_files": len(holdout), "files": dict(sorted(holdout.items())),
           "fetched_files_rehashed": n_checked, "drops": {"counts": n, "seal_copies_read": used, "seal_copies_sha256": used_shas, "seal_copies_skipped": skipped, "drop_ids": len(ids), "drop_ids_without_metadata": missing_meta,
                                                          "disjointness": U.UNVERIFIED if unverified else "verified"},
           "audit": fr.extra_state.get("audit"), "frame_manifest_sha256": fr.params.get("frame_manifest_sha256"),
           "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; holdout/ and the frame run's holdout/ (listed here as frame_holdout/) are not opened "
                         "before B1 advanced and its Stage-1 result is committed; "
                         "DROPPED_* blocks of drops.csv.gz are never read; holdout outcomes live in updown_frame_b/outcomes_guarded.csv.gz (same rule)",
           "information_end": "every state is at t <= t_end(d) - 50 s; post-t_end prints are in *_guarded files"}
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    seal_p.write_bytes(data)
    (rdir / "ACCESS_LOG.jsonl").touch()
    dest = Path(seals_dir) / SEAL_COPY_NAME
    if dest.exists() and dest.read_bytes() != data:
        raise cm.Refused(f"{dest} exists with different content; a seal is never rewritten")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"listing_sha256": doc["listing_sha256"], "committed_copy": str(dest), "drop_counts": n, "disjointness": doc["drops"]["disjointness"]}


def rule_funcs() -> tuple:
    return (hour_dt, _ms, read_hour_events, read_presence, _levels, state_at, token_rows, day_states, terminal_prints, audit_day_list, day_order, coverage_audit,
            _read_frame, _split_dir, _fail_counts, books_fetch, finalize_books, seal_holdout, ingress_used, ingress_add, h5_seal.listing_sha256, h5_seal.list_files,
            _check_clock, seal_copy_ids_audited)
