# ruff: noqa: E501
"""Memory- and disk-bounded variant of ``cb4_data.walk_series_events`` (the h7_cb4_series frame stage, q0082f).

The pinned ``cb4_data.walk_series_events`` (its source is covered by ``seals/cb4_series_rules.json``) reads both
partial files whole and keeps every slim event and guarded record in dicts; at ~110 base windows of ~4 MB that is
several GB of Python objects. This module keeps the SAME walk rules, partial-file format (so existing partial files
are read as they are, no conversion) and result, but holds only an index (event id -> line offset) and the compact
fields ``series_frame_counts`` reads. The sorted, de-duplicated ``walk_events.jsonl.gz`` / ``walk_guarded.jsonl.gz``
are streamed out in id-sorted chunks, byte-identical to ``_gz_jsonl_bytes([d[k] for k in sorted(d)])``.
Equivalence is tested in ``tests/unit/test_cb4_walk_lean.py`` (old logic vs this logic on a synthetic fixture).
"""

from __future__ import annotations

import gzip
import json
import math
import os
from collections.abc import Callable
from pathlib import Path

from . import cb4_data as d
from . import history_backfill as hb

CHUNK_BYTES = 24 * 1024 * 1024  # raw JSON bytes materialised at once while writing the sorted outputs
_REP_FIELDS = ("requests", "splits", "windows_dropped_capped", "rows_in_dropped_windows", "events_seen",
               "events_no_series", "events_no_end_or_markets")


class WalkStore:
    """Index over the partial files: ``event_id -> (line offset, index in line, approx bytes)`` for events and guarded
    records (first occurrence wins, exactly as ``dict.setdefault`` in the pinned walk) plus counts metadata."""

    def __init__(self, pp: Path, pg: Path) -> None:
        self.pp, self.pg = pp, pg
        self.ev_loc: dict[str, tuple[int, int, int]] = {}
        self.g_loc: dict[str, tuple[int, int, int]] = {}
        self.meta: dict[str, dict] = {}
        self._cat: dict[str, dict] = {}

    # -- indexing
    def add_events(self, off: int, nbytes: int, events: list[dict]) -> None:
        w = nbytes // max(len(events), 1)
        for i, ev in enumerate(events):
            eid = ev["event_id"]
            if eid in self.ev_loc:
                continue
            self.ev_loc[eid] = (off, i, w)
            cats = [self._cat.setdefault(m["fee_category"], {"fee_category": m["fee_category"]}) for m in ev["markets"]]
            self.meta[eid] = {"event_id": eid, "end_epoch": ev["end_epoch"], "markets": cats,
                              "series": [{"id": s["id"]} for s in ev["series"]]}

    def add_guarded(self, off: int, nbytes: int, guarded: list[dict]) -> None:
        w = nbytes // max(len(guarded), 1)
        for i, g in enumerate(guarded):
            self.g_loc.setdefault(g["event_id"], (off, i, w))

    # -- outputs
    def frame_counts(self) -> dict:
        return d.series_frame_counts(self.meta)

    def _write_sorted(self, budget: hb.DiskBudget, path: Path, path_src: Path, loc: dict, list_key: str,
                      chunk_bytes: int) -> None:
        ids = sorted(loc)
        tmp = path.with_name(path.name + ".tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tmp.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz, path_src.open("rb") as src:
                i = 0
                while i < len(ids):
                    j, acc = i, 0
                    while j < len(ids) and (j == i or acc + loc[ids[j]][2] <= chunk_bytes):
                        acc += loc[ids[j]][2]
                        j += 1
                    chunk = ids[i:j]
                    got: dict[str, dict] = {}
                    for off in sorted({loc[e][0] for e in chunk}):
                        src.seek(off)
                        items = json.loads(src.readline())[list_key]
                        for e in chunk:
                            if loc[e][0] == off:
                                got[e] = items[loc[e][1]]
                        del items
                    for e in chunk:
                        gz.write((json.dumps(got[e], sort_keys=True, default=float) + "\n").encode())
                    del got
                    i = j
            budget.charge(tmp.stat().st_size)
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def write_events(self, budget: hb.DiskBudget, path: Path, chunk_bytes: int = CHUNK_BYTES) -> None:
        self._write_sorted(budget, path, self.pp, self.ev_loc, "events", chunk_bytes)

    def write_guarded(self, budget: hb.DiskBudget, path: Path, chunk_bytes: int = CHUNK_BYTES) -> None:
        self._write_sorted(budget, path, self.pg, self.g_loc, "guarded", chunk_bytes)


def _lines(path: Path):
    """(byte offset, raw line) of the non-blank lines of ``path``, one at a time."""
    off = 0
    with path.open("rb") as fh:
        for line in fh:
            if line.strip():
                yield off, line
            off += len(line)


def walk_series_events_lean(lim: hb.Limiter, start: float, end: float, modes: tuple[bool, ...], *, rdir: Path,
                            should_stop: Callable[[], bool] | None = None, base_days: int = d.SERIES_WALK_BASE_DAYS,
                            min_width_s: int = d.SERIES_WINDOW_MIN_S) -> tuple[WalkStore, dict, str | None]:
    """Same rules and return semantics as ``cb4_data.walk_series_events`` but returns ``(store, rep, stopped)``."""
    pp, pg = rdir / "walk_partial.jsonl", rdir / "walk_partial_guarded.jsonl"
    store = WalkStore(pp, pg)
    rep: dict = {"modes": [bool(m) for m in modes], "base_windows": 0, "requests": 0, "splits": 0, "windows_dropped_capped": 0,
                 "rows_in_dropped_windows": 0, "events_seen": 0, "events_no_series": 0, "events_no_end_or_markets": 0,
                 "events_kept": 0, "base_windows_failed": 0, "failed_windows": []}
    done: set[tuple[bool, str]] = set()
    fails: dict[tuple[bool, str], int] = {}
    gby_off: dict[tuple[bool, str], tuple[int, int]] = {}  # last guarded line per window (later lines win, as dict overwrite)
    if pg.exists():
        for off, line in _lines(pg):
            g = json.loads(line)
            gby_off[(g["mode"], g["a"])] = (off, len(line))
    if pp.exists():
        with pg.open("rb") if pg.exists() else open(os.devnull, "rb") as gfh:
            for off, line in _lines(pp):
                rec = json.loads(line)
                k = (rec["mode"], rec["a"])
                if rec.get("fail"):
                    fails[k] = fails.get(k, 0) + 1
                    continue
                if k not in gby_off:
                    continue
                done.add(k)
                store.add_events(off, len(line), rec["events"])
                goff, glen = gby_off[k]
                gfh.seek(goff)
                store.add_guarded(goff, glen, json.loads(gfh.readline())["guarded"])
                for f in _REP_FIELDS:
                    rep[f] += rec["rep"].get(f, 0)
                rep["base_windows"] += 1
                del rec
    for mode in sorted(set(modes), key=bool):  # closed=false BEFORE closed=true
        t = start
        while t < end:
            a, b = t, min(t + base_days * d.DAY, end)
            t += base_days * d.DAY
            k = (bool(mode), d._iso(a))
            if k in done:
                continue
            if fails.get(k, 0) >= 3:
                rep["base_windows_failed"] += 1
                rep["failed_windows"].append([bool(mode), d._iso(a), d._iso(b)])
                done.add(k)
                continue
            if should_stop is not None and should_stop():
                return store, rep, "walk_paused"
            wrep = dict.fromkeys(_REP_FIELDS, 0)
            new_slim: list[dict] = []
            new_g: list[dict] = []
            stack = [(a, b)]
            failed = False
            while stack:
                x, y = stack.pop(0)
                rows: list[dict] = []
                capped, off = False, 0
                while True:
                    try:
                        status, data = lim.get(d.GAMMA_EVENTS, {"closed": "true" if mode else "false", "end_date_min": d._iso(x),
                                                                 "end_date_max": d._iso(y), "limit": 100, "offset": off})
                    except RuntimeError:
                        status, data = 599, None
                    wrep["requests"] += 1
                    if status != 200 or not isinstance(data, list):
                        failed = True
                        break
                    rows.extend(data)
                    if len(data) < 100:
                        break
                    off += 100
                    if off >= hb.GAMMA_OFFSET_CAP:
                        capped = True
                        break
                if failed:
                    break
                if capped and (y - x) > min_width_s:
                    mid = x + math.floor((y - x) / 2)
                    stack[:0] = [(x, mid), (mid, y)]
                    wrep["splits"] += 1
                    continue
                if capped:
                    wrep["windows_dropped_capped"] += 1
                    wrep["rows_in_dropped_windows"] += len(rows)
                    continue
                for e in rows:
                    wrep["events_seen"] += 1
                    if not e.get("series"):
                        wrep["events_no_series"] += 1
                        continue
                    sg = d.slim_event(e, mode)
                    if sg is None:
                        wrep["events_no_end_or_markets"] += 1
                        continue
                    new_slim.append(sg[0])
                    new_g.append(sg[1])
                rows = []  # release the raw Gamma rows of this sub-window before the next request
            if failed:
                with pp.open("a") as fh:
                    fh.write(json.dumps({"mode": bool(mode), "a": d._iso(a), "fail": True}) + "\n")
                rep["requests"] += wrep["requests"]
                return store, rep, f"walk_failed_window: closed={mode} {d._iso(a)}"
            seen_e: set[str] = set()
            uslim = [s for s in new_slim if not (s["event_id"] in seen_e or seen_e.add(s["event_id"]))]
            ug = [g for g in new_g if g["event_id"] in seen_e]
            gline = (json.dumps({"mode": bool(mode), "a": d._iso(a), "guarded": ug}, default=float) + "\n").encode()
            pline = (json.dumps({"mode": bool(mode), "a": d._iso(a), "events": uslim, "rep": wrep}, default=float) + "\n").encode()
            goff = pg.stat().st_size if pg.exists() else 0
            with pg.open("ab") as fh:
                fh.write(gline)
            poff = pp.stat().st_size if pp.exists() else 0
            with pp.open("ab") as fh:
                fh.write(pline)
            store.add_events(poff, len(pline), uslim)
            store.add_guarded(goff, len(gline), ug)
            del new_slim, new_g, uslim, ug
            for f in wrep:
                rep[f] += wrep[f]
            rep["base_windows"] += 1
            done.add(k)
    rep["events_kept"] = len(store.ev_loc)
    return store, rep, None


# ---- unit assembly without holding every event (q0082 "stage all", after the frame) ------------------------------------------------------


class _RecordingGuarded(dict):
    """Empty guarded mapping that records which event ids ``assemble_units`` asks ``get`` for (candidate predecessors)."""

    def __init__(self) -> None:
        super().__init__()
        self.asked: set[str] = set()

    def get(self, key, default=None):  # noqa: ANN001
        self.asked.add(key)
        return default


def _iter_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def assemble_units_lean(wpath: Path, wgpath: Path, **kwargs) -> dict:
    """Same result as ``cb4_data.assemble_units(events, guarded, **kwargs)`` with ``events`` / ``guarded`` read whole from
    ``wpath`` / ``wgpath``, but the pinned function runs on a mapping that holds a stub of every event and the FULL record
    only for the events of the series that can produce units.

    Pass A runs the pinned function on stubs (event id, end, series, weather flag, a market list carrying only fee categories)
    with an empty recording guarded mapping: the series table, the seeded sample and the blocks depend only on those fields,
    so the candidate predecessors it asks guarded records for (a superset of the real ones: no stub market ever matches an
    exclusion id) identify the sampled series. Pass B re-runs it on stubs plus the full events of those series and the guarded
    records of those predecessors, in the original insertion order, so every unit field comes from the pinned code on real data."""
    stubs: dict[str, dict] = {}
    series_pool: dict[tuple, dict] = {}
    mk_pool: dict[tuple, list] = {}
    cat_pool: dict[str, dict] = {}
    for ev in _iter_jsonl_gz(wpath):
        sr = [series_pool.setdefault((s["id"], s.get("slug")), s) for s in ev["series"]]
        cats = tuple(m["fee_category"] for m in ev["markets"])
        mk = mk_pool.setdefault(cats, [cat_pool.setdefault(c, {"fee_category": c, "market_id": ""}) for c in cats])
        stubs[ev["event_id"]] = {"event_id": ev["event_id"], "end_epoch": ev["end_epoch"], "series": sr,
                                 "weather_title": ev["weather_title"], "markets": mk}
    rec = _RecordingGuarded()
    d.assemble_units(stubs, rec, **kwargs)
    pred_ids = rec.asked
    chosen = {s["id"] for eid in pred_ids if eid in stubs for s in stubs[eid]["series"]}
    del mk_pool, cat_pool, series_pool
    events = stubs
    for ev in _iter_jsonl_gz(wpath):
        if any(s["id"] in chosen for s in ev["series"]):
            events[ev["event_id"]] = ev  # same key: insertion order unchanged
    guarded = {g["event_id"]: g for g in _iter_jsonl_gz(wgpath) if g["event_id"] in pred_ids}
    return d.assemble_units(events, guarded, **kwargs)
