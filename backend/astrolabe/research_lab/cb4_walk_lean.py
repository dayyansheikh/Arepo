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
import shutil
from collections.abc import Callable
from pathlib import Path

from . import cb4_data as d
from . import history_backfill as hb

CHUNK_BYTES = 4 * 1024 * 1024  # raw JSON bytes (about 10x as Python objects) materialised at once while writing the sorted outputs
_LEN_BITS = 32  # location = (byte offset of the record text in the partial file) << _LEN_BITS | (byte length of the record text)
_REP_FIELDS = ("requests", "splits", "windows_dropped_capped", "rows_in_dropped_windows", "events_seen",
               "events_no_series", "events_no_end_or_markets")
_DEC = json.JSONDecoder()


def _pack(start: int, length: int) -> int:
    return (start << _LEN_BITS) | length


class _MetaView:
    """Read-only ``events``-like view for ``series_frame_counts`` (it only calls ``.values()``): one small dict per event, built
    from the compact tuples; the series / markets lists are shared between events with the same series ids / fee categories."""

    def __init__(self, meta: dict[str, tuple]) -> None:
        self._m = meta

    def values(self):
        for eid, (end_epoch, series, markets) in self._m.items():
            yield {"event_id": eid, "end_epoch": end_epoch, "markets": markets, "series": series}


class WalkStore:
    """Index over the partial files: ``event_id -> packed (byte offset, byte length)`` of the record text for events and
    guarded records (first occurrence wins, exactly as ``dict.setdefault`` in the pinned walk) plus the compact fields
    ``series_frame_counts`` reads (end epoch, series list, fee-category list)."""

    def __init__(self, pp: Path, pg: Path) -> None:
        self.pp, self.pg = pp, pg
        self.ev_loc: dict[str, int] = {}
        self.g_loc: dict[str, int] = {}
        self.meta: dict[str, tuple] = {}
        self._cat: dict[str, dict] = {}
        self._series_lists: dict[tuple, list] = {}
        self._market_lists: dict[tuple, list] = {}

    # -- indexing
    def add_event(self, start: int, length: int, ev: dict) -> None:
        self.add_fields(start, length, ev["event_id"], ev["end_epoch"], tuple(s["id"] for s in ev["series"]),
                        tuple(m["fee_category"] for m in ev["markets"]))

    def add_fields(self, start: int, length: int, eid: str, end_epoch, sids: tuple, cats: tuple) -> None:
        if eid in self.ev_loc:
            return
        self.ev_loc[eid] = _pack(start, length)
        mk = self._market_lists.get(cats)
        if mk is None:
            mk = self._market_lists[cats] = [self._cat.setdefault(c, {"fee_category": c}) for c in cats]
        sr = self._series_lists.get(sids)
        if sr is None:
            sr = self._series_lists[sids] = [{"id": i} for i in sids]
        self.meta[eid] = (end_epoch, sr, mk)

    def add_guarded(self, start: int, length: int, eid: str) -> None:
        self.g_loc.setdefault(eid, _pack(start, length))

    # -- outputs
    def frame_counts(self) -> dict:
        return d.series_frame_counts(_MetaView(self.meta))  # type: ignore[arg-type]

    def _write_sorted(self, budget: hb.DiskBudget, path: Path, path_src: Path, loc: dict, chunk_bytes: int) -> None:
        ids = sorted(loc)
        tmp = path.with_name(path.name + ".tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        mask = (1 << _LEN_BITS) - 1
        try:
            with tmp.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz, path_src.open("rb") as src:
                i = 0
                while i < len(ids):
                    j, acc = i, 0
                    while j < len(ids) and (j == i or acc + (loc[ids[j]] & mask) <= chunk_bytes):
                        acc += loc[ids[j]] & mask
                        j += 1
                    chunk = ids[i:j]
                    got: dict[str, dict] = {}
                    for e in sorted(chunk, key=loc.__getitem__):  # file order: sequential reads
                        src.seek(loc[e] >> _LEN_BITS)
                        got[e] = json.loads(src.read(loc[e] & mask))
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
        self._write_sorted(budget, path, self.pp, self.ev_loc, chunk_bytes)

    def write_guarded(self, budget: hb.DiskBudget, path: Path, chunk_bytes: int = CHUNK_BYTES) -> None:
        self._write_sorted(budget, path, self.pg, self.g_loc, chunk_bytes)


def _lines(path: Path):
    """(byte offset, raw line) of the non-blank lines of ``path``, one at a time."""
    off = 0
    with path.open("rb") as fh:
        for line in fh:
            if line.strip():
                yield off, line
            off += len(line)


def _repair_tail(path: Path) -> None:
    """A progress line always ends with a newline; a trailing fragment is an interrupted write (its window was never recorded), so it is cut."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb+") as fh:
        size = fh.seek(0, 2)
        fh.seek(size - 1)
        if fh.read(1) == b"\n":
            return
        pos = size
        while pos > 0:
            step = min(1 << 20, pos)
            fh.seek(pos - step)
            k = fh.read(step).rfind(b"\n")
            if k >= 0:
                fh.truncate(pos - step + k + 1)
                return
            pos -= step
        fh.truncate(0)


def _head(line: bytes, key: str) -> tuple[dict, int | None]:
    """(header fields, byte index just after ``"<key>": [``) of a progress line without parsing the list; lines without
    the list (failed-window markers) are parsed whole and return ``None`` as index."""
    marker = f', "{key}": ['.encode()
    i = line.find(marker, 0, 400)
    if i < 0:
        return json.loads(line), None
    return json.loads(line[:i] + b"}"), i + len(marker)


def _items(line: bytes, start: int, rep_out: dict | None = None):
    """Yield ``(byte offset in line, byte length, record)`` for each element of the JSON list starting at byte ``start`` of a line written
    by ``json.dumps`` (separators ``", "``). One record is materialised at a time. ``rep_out`` receives the trailing ``rep`` object, if any."""
    text = line.decode()
    ascii_only = text.isascii()
    idx, last_c, last_b = start, start, start  # character index -> byte offset (identity for ASCII)

    def byte_of(ci: int) -> int:
        nonlocal last_c, last_b
        if ascii_only:
            return ci
        last_b += len(text[last_c:ci].encode())
        last_c = ci
        return last_b

    del line
    while text[idx] != "]":
        obj, end = _DEC.raw_decode(text, idx)
        yield byte_of(idx), byte_of(end) - byte_of(idx), obj
        idx = end
        if text.startswith(", ", idx):
            idx += 2
    if rep_out is not None and text.startswith(', "rep": ', idx + 1):
        rep_out.update(json.loads("{" + text[idx + 3:])["rep"])


class _Spool:
    """Newline-free ``", "``-joined JSON of the records of one base window, spilled to disk; remembers each record's offset and length."""

    def __init__(self, path: Path) -> None:
        self.path, self.n, self.pos = path, 0, 0
        self.spans: list[tuple[int, int]] = []
        self.ids: list[str] = []
        self.fh = path.open("wb")

    def add(self, obj: dict, eid: str) -> None:
        b = json.dumps(obj, default=float).encode()
        if self.n:
            self.fh.write(b", ")
            self.pos += 2
        self.spans.append((self.pos, len(b)))
        self.ids.append(eid)
        self.fh.write(b)
        self.pos += len(b)
        self.n += 1

    def close(self) -> None:
        self.fh.close()

    def discard(self) -> None:
        self.fh.close()
        self.path.unlink(missing_ok=True)


def _append_streamed(path: Path, prefix: bytes, spool: _Spool, suffix: bytes) -> int:
    """Append ``prefix + spool + suffix`` to ``path`` without building the line in memory; returns the line's start offset. On any
    error the partial line is cut off again, so the file never keeps a fragment."""
    start = path.stat().st_size if path.exists() else 0
    try:
        with path.open("ab") as fh, spool.path.open("rb") as src:
            fh.write(prefix)
            shutil.copyfileobj(src, fh, 1 << 20)
            fh.write(suffix)
    except BaseException:
        if path.exists():
            os.truncate(path, start)
        raise
    return start


def walk_series_events_lean(lim: hb.Limiter, start: float, end: float, modes: tuple[bool, ...], *, rdir: Path,
                            should_stop: Callable[[], bool] | None = None, base_days: int = d.SERIES_WALK_BASE_DAYS,
                            min_width_s: int = d.SERIES_WINDOW_MIN_S) -> tuple[WalkStore, dict, str | None]:
    """Same rules and return semantics as ``cb4_data.walk_series_events`` but returns ``(store, rep, stopped)``. Progress lines of up to
    tens of MB are never parsed or built whole: they are read record by record and written through a disk spool."""
    pp, pg = rdir / "walk_partial.jsonl", rdir / "walk_partial_guarded.jsonl"
    spool_e, spool_g = rdir / "walk_partial.events.spool", rdir / "walk_partial.guarded.spool"
    for sp in (spool_e, spool_g):  # leftovers of a killed attempt
        sp.unlink(missing_ok=True)
    _repair_tail(pp)
    _repair_tail(pg)
    store = WalkStore(pp, pg)
    rep: dict = {"modes": [bool(m) for m in modes], "base_windows": 0, "requests": 0, "splits": 0, "windows_dropped_capped": 0,
                 "rows_in_dropped_windows": 0, "events_seen": 0, "events_no_series": 0, "events_no_end_or_markets": 0,
                 "events_kept": 0, "base_windows_failed": 0, "failed_windows": []}
    done: set[tuple[bool, str]] = set()
    fails: dict[tuple[bool, str], int] = {}
    gby_off: dict[tuple[bool, str], tuple[int, int]] = {}  # last guarded line per window (later lines win, as dict overwrite)
    if pg.exists():
        for off, line in _lines(pg):
            g, _i = _head(line, "guarded")
            gby_off[(g["mode"], g["a"])] = (off, len(line))
    if pp.exists():
        with pg.open("rb") if pg.exists() else open(os.devnull, "rb") as gfh:
            for off, line in _lines(pp):
                head, istart = _head(line, "events")
                k = (head["mode"], head["a"])
                if head.get("fail"):
                    fails[k] = fails.get(k, 0) + 1
                    continue
                if k not in gby_off:
                    continue
                done.add(k)
                wrep: dict = {}
                for st, ln, ev in _items(line, istart, wrep):
                    store.add_event(off + st, ln, ev)
                del line
                goff, glen = gby_off[k]
                gfh.seek(goff)
                gline = gfh.readline()
                _gh, gstart = _head(gline, "guarded")
                for st, ln, g in _items(gline, gstart):
                    store.add_guarded(goff + st, ln, g["event_id"])
                del gline
                for f in _REP_FIELDS:
                    rep[f] += wrep.get(f, 0)
                rep["base_windows"] += 1
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
            sp_e, sp_g = _Spool(spool_e), _Spool(spool_g)
            seen_e: set[str] = set()
            metas: list[tuple] = []  # per kept event (parallel to sp_e.spans): end epoch, series ids, fee categories
            try:
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
                        sp_g.add(sg[1], sg[0]["event_id"])  # every guarded record is kept, duplicates included (as the pinned walk)
                        if sg[0]["event_id"] in seen_e:
                            continue
                        seen_e.add(sg[0]["event_id"])
                        sp_e.add(sg[0], sg[0]["event_id"])
                        metas.append((sg[0]["end_epoch"], tuple(s["id"] for s in sg[0]["series"]),
                                      tuple(m["fee_category"] for m in sg[0]["markets"])))
                    rows = []  # release the raw Gamma rows of this sub-window before the next request
                sp_e.close()
                sp_g.close()
                if failed:
                    with pp.open("a") as fh:
                        fh.write(json.dumps({"mode": bool(mode), "a": d._iso(a), "fail": True}) + "\n")
                    rep["requests"] += wrep["requests"]
                    return store, rep, f"walk_failed_window: closed={mode} {d._iso(a)}"
                head = json.dumps({"mode": bool(mode), "a": d._iso(a)})[:-1]
                gpre, ppre = (head + ', "guarded": [').encode(), (head + ', "events": [').encode()
                gstart = _append_streamed(pg, gpre, sp_g, b"]}\n")
                pstart = _append_streamed(pp, ppre, sp_e, ("], \"rep\": " + json.dumps(wrep, default=float) + "}\n").encode())
                for eid, (st, ln), (end_epoch, sids, cats) in zip(sp_e.ids, sp_e.spans, metas, strict=True):
                    store.add_fields(pstart + len(ppre) + st, ln, eid, end_epoch, sids, cats)
                for eid, (st, ln) in zip(sp_g.ids, sp_g.spans, strict=True):
                    store.add_guarded(gstart + len(gpre) + st, ln, eid)
            finally:
                sp_e.discard()
                sp_g.discard()
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
