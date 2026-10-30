# ruff: noqa: E501
"""The parent event's other children (aux family ``parentsib``, DESIGN_V1 section 45; CH237).

Inputs, all from capture k or earlier: k's complete binary listing (``rows.csv.gz``, the ``event`` family's filter:
binary, open, active, with an event id), k's own Gamma sidecar ``rows_ext.csv.gz`` (v3 ``event_ids`` with the aligned
``parent_event_ids``), and the previous slot's engine quotes (the ``event`` family's ``prev_mid``). A market's child
event is its listing ``event_id``; its parent is that event's ``parentEventId`` in its own sidecar row. Its siblings are
the listing markets whose child event has the same parent and is not its own event.

Clock (per pair): a sibling counts only if its row was received no later than ``EVENT_MAX_SPREAD_S`` (5 s) after the
market's own row, the ``event`` family's tolerance. Later pages never feed an earlier market. A sibling mean needs a
value for at least ``SIB_MIN_SHARE`` of the siblings (own event excluded). A sibling that fails the clock counts as
having no value. A missing value is never read as zero.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

PS_VERSION = "se-aux-parentsib-v1"
PS_COLUMNS = ["ps_has_parent", "ps_log_n_child", "ps_sib_d2h", "ps_sib_abs", "ps_sib_moving"]
MOVE_C = 0.01  # |2 h change| >= 1c counts as moving (CH237)
MAX_LAG_S = 5.0  # = aux.EVENT_MAX_SPREAD_S
MIN_SHARE = 0.5  # = aux.SIB_MIN_SHARE


def _parent_of(event_id, event_ids: str, parents: str):
    """The parent id of ``event_id`` in one sidecar row; "" = known no parent; None = unknown (no lists)."""
    if not isinstance(event_ids, str) or not event_ids.strip().startswith("["):
        return None
    if not isinstance(parents, str) or not parents.strip().startswith("["):
        return None
    try:
        e, p = json.loads(event_ids), json.loads(parents)
    except ValueError:
        return None
    if not isinstance(e, list) or not isinstance(p, list) or len(e) != len(p):
        return None
    m = {str(a): b for a, b in zip(e, p, strict=True)}
    v = m.get(str(event_id))
    return str(v) if v not in (None, "") else ""


def read_parent_ext(cap_dir) -> pd.DataFrame | None:
    """Per market id: ``event_id`` and the sidecar lists. None when the sidecar or its v3 column is absent."""
    p = Path(cap_dir) / "rows_ext.csv.gz" if cap_dir is not None else None
    if p is None or not p.exists():
        return None
    import pyarrow as pa
    import pyarrow.csv as pacsv

    cols = ["market_id", "event_id", "event_ids", "parent_event_ids"]
    types = {"market_id": pa.int64(), "event_id": pa.string(), "event_ids": pa.string(), "parent_event_ids": pa.string()}
    try:
        t = pacsv.read_csv(p, convert_options=pacsv.ConvertOptions(include_columns=cols, column_types=types))
    except (pa.ArrowInvalid, KeyError):
        return None  # an older sidecar without parent_event_ids: the family is missing for this capture
    return t.to_pandas().drop_duplicates("market_id").set_index("market_id")


def parentsib_features(rows: pd.DataFrame, f: pd.DataFrame, prev_mid: pd.Series | None, ext: pd.DataFrame | None) -> pd.DataFrame:
    """Per eligible market (``f`` row order); NaN where the sidecar, its v3 column or the market's listing row is absent."""
    n = len(f)
    out = pd.DataFrame({c: np.full(n, np.nan, np.float32) for c in PS_COLUMNS})
    if n == 0 or ext is None or rows is None or rows.empty:
        return out
    from .features import _epoch_col, _truthy

    b = rows[rows["binary"] == 1]
    b = b[(~_truthy(b["closed"])) & _truthy(b["active"])]
    b = b[b["event_id"].notna()].drop_duplicates("market_id")
    bid, ask = b["best_bid"].to_numpy(float), b["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask)
    mid = np.where(two, (bid + ask) / 2.0, np.nan)
    mids = b["market_id"].to_numpy(np.int64)
    pm = prev_mid.reindex(mids).to_numpy(float) if prev_mid is not None else np.full(len(b), np.nan)
    ev = b["event_id"].astype(str).to_numpy()
    xe = ext.reindex(mids)
    par = np.array([_parent_of(e, a, p) for e, a, p in zip(ev, xe["event_ids"].to_numpy(object), xe["parent_event_ids"].to_numpy(object), strict=True)], object)
    g = pd.DataFrame({"market_id": mids, "ev": ev, "par": par, "d2h": mid - pm, "t": _epoch_col(b["received_utc"])})
    # eligible rows: the parent read from their own listing row (the same row the features came from)
    own = g.set_index("market_id").reindex(f["market_id"].to_numpy(np.int64))
    opar = own["par"].to_numpy(object)
    known = np.array([x is not None and not (isinstance(x, float) and math.isnan(x)) for x in opar])
    has = np.array([bool(x) if k else False for x, k in zip(opar, known, strict=True)])
    out["ps_has_parent"] = np.where(known, has.astype(np.float32), np.nan)
    if not has.any():
        return out.astype(np.float32)
    gp = g[g["par"].map(lambda x: isinstance(x, str) and x != "")]
    groups = {k: (v["ev"].to_numpy(), v["d2h"].to_numpy(float), v["t"].to_numpy(float)) for k, v in gp.groupby("par", sort=False)}
    oev, ot = own["ev"].to_numpy(object), own["t"].to_numpy(float)
    cols = {c: out[c].to_numpy(np.float32).copy() for c in PS_COLUMNS[1:]}
    for i in np.flatnonzero(has):
        gev, gd, gt = groups[opar[i]]
        if not math.isfinite(ot[i]):
            continue
        seen = np.isfinite(gt) & (gt <= ot[i] + MAX_LAG_S)  # rows received by the market's own row (+ 5 s)
        cols["ps_log_n_child"][i] = math.log(len(set(gev[seen]) | {oev[i]}))
        sib = gev != oev[i]
        n_sib = int(sib.sum())
        if n_sib == 0:
            continue
        val = sib & seen & np.isfinite(gd)
        n_val = int(val.sum())
        if n_val >= 1 and n_val >= MIN_SHARE * n_sib:
            d = gd[val]
            cols["ps_sib_d2h"][i] = d.mean()
            cols["ps_sib_abs"][i] = np.abs(d).mean()
            cols["ps_sib_moving"][i] = (np.abs(d) >= MOVE_C - 1e-12).mean()
    for c, v in cols.items():
        out[c] = v
    return out.astype(np.float32)


def code_sha256() -> str:
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
