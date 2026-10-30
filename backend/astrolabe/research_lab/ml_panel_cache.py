"""Disk-backed, period-cached build of the multi-signal panel (MC1).

Produces the same panel as ``ml_panel.build_panel`` followed by ``DataFrame.to_parquet`` (the
form every cached run reads back), without ever holding more than one period frame in memory:

1. each period frame is built by ``ml_panel.build_period`` exactly as in ``build_panel`` (same
   snapshots, same nearest-first history of up to six earlier snapshots, same declared sweeps)
   and written to ``<period_dir>/<key>.parquet`` with its counts in ``<key>.json``;
2. the cross-period dependence pooling (``ml_panel.pool_dependence_groups``) and the category
   policy (``ml_panel.apply_category_policy``) run on a slim frame of id columns only;
3. the panel parquet is written period by period with the pooled ids substituted.

The period key hashes everything a period frame depends on: the origin, target and history
capture ids, the origin and target sweep entries and a caller ``salt`` (module hashes, feature
versions, delta, link digest). A period frame is therefore reusable by any later panel whose
capture list gives that period the same inputs, so raw snapshots that age out of retention are
not needed again once their periods are cached. Period frames always carry the leakage-alarm
``leak_*`` columns; a panel built without ``with_leak`` drops them, which is exactly the frame
``build_period(with_leak=False)`` returns (the leak columns are appended and touch nothing else).
Only the integer ``period`` column depends on the position in the capture list; it is rewritten.
Snapshots and sweeps are only read.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import ml_panel

PERIOD_CACHE_VERSION = "ml-period-cache-v1"
POOLED_COLS = ("dep_group", "dep_group_season", "dep_group_fixture_day",
               *ml_panel.SENSITIVITY_GROUP_COLS)
PERIOD_COPIES = (("dep_group_period", "dep_group"), ("dep_group_season_period", "dep_group_season"))
LEAK_PREFIX = "leak_"


def _cap_key(c: dict) -> list:
    return [c["capture_id"], c.get("started_utc"), c.get("sidecar")]


def _sweep_key(e: dict | None) -> dict | None:
    if e is None:
        return None
    return {"sweep_id": e.get("sweep_id"), "dir": Path(e["dir"]).name if e.get("dir") else None,
            "receipt_epoch": e.get("receipt_epoch"), "started_epoch": e.get("started_epoch"),
            "returned": e.get("returned"), "eligible": e.get("eligible")}


def period_key(captures: list[dict], k: int, sweep_receipts: dict, salt: str) -> str:
    """Content key of period ``k`` (origin ``captures[k]``, target ``captures[k + 1]``)."""
    lo = max(k - ml_panel.HISTORY_DEPTH, 0)
    body = {
        "version": PERIOD_CACHE_VERSION, "salt": salt,
        "i": _cap_key(captures[k]), "j": _cap_key(captures[k + 1]),
        "history": [_cap_key(captures[m]) for m in range(k - 1, lo - 1, -1)],
        "sweep_i": _sweep_key(sweep_receipts.get(captures[k]["capture_id"])),
        "sweep_j": _sweep_key(sweep_receipts.get(captures[k + 1]["capture_id"])),
    }
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _json_default(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not serialisable: {type(o)}")


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _load_cached(period_dir: Path, key: str) -> tuple[dict, Path | None] | None:
    jp, pp = period_dir / f"{key}.json", period_dir / f"{key}.parquet"
    if not jp.exists():
        return None
    rec = json.loads(jp.read_text())
    if rec.get("has_frame"):
        return (rec["counts"], pp) if pp.exists() else None
    return rec["counts"], None


def build_periods(
    captures: list[dict],
    period_dir: Path,
    salt: str,
    load: Callable[[dict], pd.DataFrame] | None = None,
    sweep_receipts: dict | None = None,
    delta: float = ml_panel.DELTA_PRIMARY,
    sweep_loader: Callable[[dict], pd.DataFrame] | None = None,
    dep_underlying_date: bool = ml_panel.DEP_GROUP_UNDERLYING,
    link_fields: dict | None = None,
    rebuild: bool = False,
    log: Callable[[str], None] | None = None,
) -> list[tuple[int, dict, Path | None]]:
    """Build (or reuse) every period frame. Returns ``[(k, counts, parquet path or None)]``.

    At most two full snapshots are in memory, plus slim history records; a snapshot is loaded
    only when a period that needs it (as origin, target or history) is not cached.
    """
    load = load or (lambda cap: ml_panel.load_snapshot_rows(
        Path(cap["dir"]), exclude=ml_panel.PANEL_UNUSED_COLS))
    sl = sweep_loader or ml_panel.load_sweep_rows
    sweep_receipts = sweep_receipts or {}
    period_dir = Path(period_dir)
    period_dir.mkdir(parents=True, exist_ok=True)
    snaps: dict[int, pd.DataFrame] = {}
    slims: dict[int, pd.DataFrame] = {}

    def snap(m: int) -> pd.DataFrame:
        if m not in snaps:
            snaps[m] = load(captures[m])
        return snaps[m]

    def slim(m: int) -> pd.DataFrame:
        if m not in slims:
            loaded = m in snaps
            slims[m] = ml_panel.slim_history(snap(m))
            if not loaded:
                snaps.pop(m, None)  # loaded only for its history record
        return slims[m]

    out: list[tuple[int, dict, Path | None]] = []
    for k in range(len(captures) - 1):
        key = period_key(captures, k, sweep_receipts, salt)
        hit = None if rebuild else _load_cached(period_dir, key)
        if hit is not None:
            counts, path = hit
            out.append((k, {**counts, "period": k}, path))
            continue
        lo = max(k - ml_panel.HISTORY_DEPTH, 0)
        hist = [slim(m) for m in range(k - 1, lo - 1, -1)]
        for m in [m for m in snaps if m < k]:
            del snaps[m]
        cur, nxt = snap(k), snap(k + 1)
        sw = sweep_receipts.get(captures[k]["capture_id"])
        srows = sl(sw) if sw is not None and sw.get("dir") else None
        nx = sweep_receipts.get(captures[k + 1]["capture_id"])
        lsw = sl(nx) if nx is not None and nx.get("dir") else None
        frame, counts = ml_panel.build_period(
            cur, nxt, captures[k], captures[k + 1], k, hist,
            None if sw is None else sw["receipt_epoch"], delta,
            sweep_returned=None if sw is None else sw["returned"],
            sweep_eligible=None if sw is None else sw["eligible"],
            sweep_rows=srows, sweep_started_epoch=None if sw is None else sw.get("started_epoch"),
            dep_underlying_date=dep_underlying_date, with_leak=True, leak_sweep_rows=lsw,
            link_fields=link_fields,
        )
        del srows, lsw
        pp = period_dir / f"{key}.parquet"
        if frame is not None:
            tmp = pp.with_name(pp.name + ".tmp")
            frame.to_parquet(tmp, index=False)
            os.replace(tmp, pp)
        _atomic_write_text(period_dir / f"{key}.json", json.dumps(
            {"version": PERIOD_CACHE_VERSION, "has_frame": frame is not None,
             "n_rows": 0 if frame is None else int(len(frame)), "counts": counts},
            default=_json_default))
        has = frame is not None
        del frame
        out.append((k, counts, pp if has else None))
        for m in [m for m in slims if m < k + 1 - ml_panel.HISTORY_DEPTH]:
            del slims[m]
        if log:
            log(f"period {k}: built ({counts.get('skipped') or 'ok'})")
    snaps.clear()
    return out


def _unify(schemas: list[pa.Schema], nulls: dict[str, set[int]]) -> pa.Schema:
    """One schema for all period files, mirroring ``pd.concat`` + ``to_parquet``: a column that is
    all-null in some periods takes the type of the others; int64 with double gives double."""
    names: list[str] = []
    for s in schemas:
        names += [n for n in s.names if n not in names]
    fields = []
    for n in names:
        types = {}
        for i, s in enumerate(schemas):
            if n in s.names and i not in nulls.get(n, set()):
                types[str(s.field(n).type)] = s.field(n).type
        if not types:  # all-null everywhere: keep the first file's type (null or double)
            fields.append(next(s.field(n) for s in schemas if n in s.names))
            continue
        if len(types) == 1:
            t = next(iter(types.values()))
        elif set(types) <= {"int64", "double"}:
            t = pa.float64()
        else:
            raise TypeError(f"column {n!r} has incompatible period types {sorted(types)}")
        fields.append(pa.field(n, t))
    return pa.schema(fields)


def _conform(t: pa.Table, schema: pa.Schema) -> pa.Table:
    cols = []
    for f in schema:
        if f.name in t.column_names:
            c = t.column(f.name)
            if c.type != f.type:
                if c.null_count != len(c) and not (
                        pa.types.is_integer(c.type) and pa.types.is_floating(f.type)):
                    raise TypeError(f"cannot cast non-null {f.name!r} {c.type} -> {f.type}")
                c = c.cast(f.type) if c.null_count != len(c) else pa.nulls(len(c), f.type)
            cols.append(c)
        else:
            cols.append(pa.nulls(t.num_rows, f.type))
    return pa.Table.from_arrays(cols, schema=schema)


def assemble_panel(
    periods: list[tuple[int, dict, Path | None]],
    out_path: Path,
    policy: dict | None = None,
    with_leak: bool = False,
) -> tuple[dict, int]:
    """Write the pooled, policy-filtered panel parquet from cached period frames.

    Returns ``(category_info, n_rows)``. Identical (after a parquet round trip) to
    ``build_panel`` + ``to_parquet(index=False)`` on the same captures.
    """
    out_path = Path(out_path)
    files = [(k, p) for k, _c, p in periods if p is not None]
    tmp = out_path.with_name(out_path.name + ".tmp")
    if not files:
        empty, info = ml_panel.apply_category_policy(pd.DataFrame(), policy)
        empty.to_parquet(tmp, index=False)
        os.replace(tmp, out_path)
        return info, 0

    def keep_col(n: str) -> bool:
        return with_leak or not n.startswith(LEAK_PREFIX)

    schemas = []
    for _k, p in files:
        s = pq.read_schema(p).remove_metadata()
        schemas.append(pa.schema([f for f in s if keep_col(f.name)]))
    nulls: dict[str, set[int]] = {}
    names = {n for s in schemas for n in s.names}
    for n in sorted(names):  # only columns whose type differs between periods are inspected
        if len({str(s.field(n).type) for s in schemas if n in s.names}) > 1:
            for i, (_k, p) in enumerate(files):
                if n in schemas[i].names:
                    c = pq.read_table(p, columns=[n]).column(0)
                    if c.null_count == len(c):
                        nulls.setdefault(n, set()).add(i)
    schema = _unify(schemas, nulls)

    # pass 1: slim id frame -> pooled dependence groups and the category-policy mask
    slim_cols = ["market_id", *POOLED_COLS, "fee_category"]
    parts = []
    for i, (k, p) in enumerate(files):
        sch = pa.schema([schema.field(c) for c in slim_cols if c in schema.names])
        t = _conform(pq.read_table(p, columns=[c for c in sch.names if c in schemas[i].names]),
                     sch)
        parts.append(t.append_column("period", pa.array(np.full(t.num_rows, k, np.int64))))
    ids = pa.concat_tables(parts).to_pandas()
    del parts
    pooled = {c: ml_panel.pool_dependence_groups(ids, c).to_numpy(object) for c in POOLED_COLS
              if c in ids.columns}
    probe = pd.DataFrame({"_row": np.arange(len(ids))})
    if "fee_category" in ids.columns:
        probe.insert(0, "fee_category", ids["fee_category"].to_numpy(object))
    kept, info = ml_panel.apply_category_policy(probe, policy)
    keep = np.zeros(len(ids), bool)
    keep[kept["_row"].to_numpy()] = True
    del ids, probe, kept

    # pass 2: stream every period into the panel parquet
    out_schema = schema
    for name, src in PERIOD_COPIES:
        if src in schema.names:
            out_schema = out_schema.append(pa.field(name, schema.field(src).type))
    writer = pq.ParquetWriter(tmp, out_schema)
    n_rows, off = 0, 0
    try:
        for i, (k, p) in enumerate(files):
            t = _conform(pq.read_table(p, columns=[c for c in schemas[i].names]), schema)
            n = t.num_rows
            t = t.set_column(t.schema.get_field_index("period"), "period",
                             pa.array(np.full(n, k, np.int64)))
            orig = {src: t.column(src) for _n, src in PERIOD_COPIES if src in t.column_names}
            for c, v in pooled.items():
                t = t.set_column(t.schema.get_field_index(c), c,
                                 pa.array(v[off:off + n], type=schema.field(c).type))
            for name, src in PERIOD_COPIES:
                if src in orig:
                    t = t.append_column(pa.field(name, orig[src].type), orig[src])
            m = keep[off:off + n]
            if not m.all():
                t = t.filter(pa.array(m))
            writer.write_table(t)
            n_rows += t.num_rows
            off += n
    finally:
        writer.close()
    os.replace(tmp, out_path)
    return info, n_rows


def build_panel_to_parquet(
    captures: list[dict],
    out_path: Path,
    period_dir: Path,
    salt: str,
    load: Callable[[dict], pd.DataFrame] | None = None,
    sweep_receipts: dict | None = None,
    delta: float = ml_panel.DELTA_PRIMARY,
    policy: dict | None = None,
    sweep_loader: Callable[[dict], pd.DataFrame] | None = None,
    dep_underlying_date: bool = ml_panel.DEP_GROUP_UNDERLYING,
    with_leak: bool = False,
    link_fields: dict | None = None,
    rebuild: bool = False,
    log: Callable[[str], None] | None = None,
) -> tuple[list[dict], dict, int]:
    """``build_panel`` written straight to ``out_path``. Returns (counts, category_info, n_rows)."""
    periods = build_periods(captures, period_dir, salt, load, sweep_receipts, delta,
                            sweep_loader, dep_underlying_date, link_fields, rebuild, log)
    info, n = assemble_panel(periods, out_path, policy, with_leak)
    return [c for _k, c, _p in periods], info, n
