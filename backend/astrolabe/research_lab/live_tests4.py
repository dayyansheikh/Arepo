# ruff: noqa: E501
"""LIVE prospective tests E020-E024 (docs/research_lab/LIVE_TESTS_4.md). DRAFT until the ledger registration.

Research tooling only: a PURE READER of streams the Oracle collector already writes every 2 hours. It never trades and
makes no network request. It reuses the LT3 reader (``live_tests3``) by import, unmodified, and pins that module's hash
together with its own (LIVE_TESTS_4.md 1.0 L7); it never opens LT3's store.

Inputs: complete captures (``rows.csv.gz`` plus the ``rows_ext.csv.gz`` sidecar), sweep 1 of each pass (outcome-0 token
quote, sizes and 1c / 5c depths), the active-frame trade sample of each pass (trades and features; wallets never opened).

Outputs (``research_lab/live_tests4/``; every data file WRITE-ONCE, atomic, floats written with ``%.17g``):

* ``series/<capture>.csv.gz`` + ``status/<capture>.csv.gz``: LT3's slim series plus Gamma ``liquidity`` and the reward
  fields; ``sweeps/<capture>.csv.gz``: the sweep-1 outcome-0 quote, sizes and depths of the pass.
* ``move/frozen/<capture>.csv.gz``: every eligible |x| >= 1c mover with class, geometry and E020's fields.
* ``hollow/frozen/<capture>.csv.gz``: E022 traded movers with the sweep-1 state (``.nosweep`` marker if the sweep never
  arrives).
* ``clock/frozen/<sample>.csv.gz``: E021 sampled movers with the last-trade clock.
* ``flow/frozen/<sample>.csv.gz``: E023 / E024 lines (LT3's flow line plus the open share, the concentration and HHI).
* ``<kind>/outcomes/<id>.h<j>.csv.gz`` (status and quote at slot k + j) and ``.s<j>.csv.gz`` (sweep-1 quote of pass k + j).
* ``passes.jsonl`` (append-only log) and ``state.json`` (processed-id cache only).

Causality: origin features use the origin capture and earlier captures, sweep 1 of the origin pass (E022, whose target
starts at that sweep) and trades strictly before the origin row's receipt. A frozen file is refused (``.late`` marker)
once its earliest target slot may have started. ``ops_stats`` never reads a price column.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import forecast, panel, trade_sample
from . import live_tests3 as l3

VERSION = "live-tests4-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = l3.SAMPLE_ROOT
SWEEP_ROOT = l3.SWEEP_ROOT
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests4"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests4_v1.json"
SPEC_SHA256 = None  # pinned at registration (LIVE_TESTS_4.md 9.3); None = DRAFT, every line is prospective_unregistered

REGISTERED_UTC = "2026-10-26T00:00:00Z"
END_UTC = "2026-11-16T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-11-17T12:00:00Z"
TEMPFAIL = 75
DISK_CAP_BYTES = int(1.5e9)
GRID_S = l3.GRID_S
SERIES_LOOKBACK_S = 26 * 3600.0  # flow RV needs slots k - 12 .. k
MISSING_AFTER_S = l3.MISSING_AFTER_S
ROLE_CONF, ROLE_UNREG = l3.ROLE_CONF, l3.ROLE_UNREG
CODE_FILES = ("live_tests4.py", "live_tests4_analysis.py", "live_tests3.py", "live_tests3_analysis.py")
MARKERS = (".late.csv.gz", ".noprev.csv.gz", ".nosweep.csv.gz")

SNAP_COLS = [*l3.SNAP_COLS, "liquidity"]
EXT_COLS = [*l3.EXT_COLS, "rewards_min_size", "rewards_max_spread"]
SWEEP_COLS = [*l3.SWEEP_COLS, "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c", "min_order_size"]
# columns ops_stats may read (never a price, a move, a state value or a target; enforced by a unit test)
OPS_COLS = frozenset({"role", "cls", "geom", "sports", "arrival", "side_moved", "band", "clock", "tick_ok", "common", "n2h_truncated", "cov6", "status",
                      "late", "checked_utc", "noprev", "nosweep"})
KINDS = ("move", "hollow", "clock", "flow")
CONTROLS_E020 = ["spread_p", "log_abs_x", "logit_mid", "abs_dev", "log1p_vol", "log_hte", "hte_missing", "rew"]
CONTROLS_E021 = ["g_par", "g_os", "g_sc", "log_abs_x", "spread_k", "logit_mid", "abs_dev", "log1p_vol_p", "log_hte", "hte_missing", "log1p_n2h"]
CONTROLS_E022 = ["log1p_Dp", "Dp_missing", "dimb", "dimb_missing", "sw_spread0", "g_par", "g_os", "g_sc", "log_abs_x", "logit_mid",
                 "abs_dev", "log1p_vol"]

epoch, iso, now_ts, sha256_file, git_commit = l3.epoch, l3.iso, l3.now_ts, l3.sha256_file, l3.git_commit
append_jsonl, dir_bytes, du_bytes, _json = l3.append_jsonl, l3.dir_bytes, l3.du_bytes, l3._json


# --- pins -----------------------------------------------------------------------------------------------------------


def code_hashes() -> dict:
    """Normalised sha256 (``SPEC_SHA256`` line excluded) of the four modules LT4 runs: its own two and LT3's two."""
    here = Path(__file__).resolve().parent
    return {n: l3.code_sha256(here / n) for n in CODE_FILES}


def joint_sha(h4: str, h3: str) -> str:
    """16 hex digits identifying the reader code: LT4's reader module together with the LT3 module it imports."""
    return hashlib.sha256((str(h4) + str(h3)).encode("utf-8")).hexdigest()[:16]


def reader_sha() -> str:
    h = code_hashes()
    return joint_sha(h["live_tests4.py"], h["live_tests3.py"])


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"live_tests4 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"] = got
    spec["_pinned"] = sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests4 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    return spec


def write_once_csv(path: Path, df: pd.DataFrame) -> bool:
    """Write ``df`` (gzip CSV, floats ``%.17g``: exact round trip, L1) to ``path`` only if it does not exist; atomic
    (tmp + hard link). False if it existed (the existing file is never touched)."""
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_csv(tmp, index=False, compression="gzip", float_format="%.17g")
    with open(tmp, "rb") as fh:
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def _stamp(df: pd.DataFrame, spec: dict, commit: str) -> pd.DataFrame:
    df = df.drop(columns=[c for c in ("frozen_utc", "code_commit", "spec_sha", "code_sha") if c in df.columns])
    df["frozen_utc"] = iso(now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"] = commit, spec["_sha256"][:16], reader_sha()
    return df


def _marker(p: Path, suffix: str) -> Path:
    return p.with_name(p.name.replace(".csv.gz", suffix))


# --- readers ----------------------------------------------------------------------------------------------------------


def load_rows(cap_dir: Path) -> tuple[pd.DataFrame, dict]:
    """LT3's origin-side capture columns plus Gamma ``liquidity``; one row per market_id and condition_id."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category",
                              "end_date": "category", "closed": str, "active": str, "neg_risk": str})
    if "liquidity" not in rows:
        rows["liquidity"] = np.nan
    n0 = len(rows)
    rows = rows.drop_duplicates("market_id")
    n1 = len(rows)
    cond = rows["condition_id"].fillna("")
    dup_c = cond.ne("") & cond.duplicated()
    rows = rows[~dup_c.to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows, {"rows": n0, "dup_market_id": n0 - n1, "dup_condition_id": int(dup_c.sum())}


def load_ext(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS), dtype=str)
    for c in EXT_COLS:
        if c not in ext:
            ext[c] = None
    return ext.drop_duplicates("market_id").set_index("market_id")


def series_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """LT3's (series, status) plus ``liq`` (Gamma liquidity), ``rew`` (rewards_max_spread > 0) and ``rew_min``."""
    ser, status = l3.series_frame(rows, ext, spec)
    mids = pd.Index(ser["market_id"].astype(str))
    ser["liq"] = rows.set_index(rows["market_id"].astype(str))["liquidity"].reindex(mids).to_numpy(float)
    if ext is not None:
        e = ext.reindex(mids)
        rs = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
        ser["rew"] = (np.nan_to_num(rs, nan=0.0) > 0).astype(int)
        ser["rew_min"] = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
    else:
        ser["rew"], ser["rew_min"] = 0, np.nan
    return ser, status


def sweep_frame(sweep_dir: Path, cap_dir: Path) -> pd.DataFrame:
    """Sweep 1 per market: the outcome-0 token's quote, receipt, two-sided flag, top sizes, 1c / 5c depths and min order
    size, plus the outcome-1 token's quote and 5c depths (the other token of the same market in the sweep; R1 finding 6)."""
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=["market_id", "clob_token_id_0"],
                      dtype=str).drop_duplicates("market_id")
    sw = pd.read_csv(Path(sweep_dir) / "rows.csv.gz", usecols=lambda c: c in set(SWEEP_COLS), dtype={"token_id": str, "market_id": str})
    for c in SWEEP_COLS:
        if c not in sw:
            sw[c] = np.nan
    sw = sw.merge(tok, on="market_id", how="inner")
    t1 = sw[sw["token_id"] != sw["clob_token_id_0"]].drop_duplicates("market_id").set_index("market_id")
    sw = sw[sw["token_id"] == sw["clob_token_id_0"]].drop_duplicates("market_id")
    bid, ask = sw["best_bid"].to_numpy(float), sw["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask)
    f = {c: pd.to_numeric(sw[c], errors="coerce").to_numpy(float) for c in SWEEP_COLS[6:]}
    o = t1.reindex(sw["market_id"].astype(str))
    g = {c: pd.to_numeric(o[c], errors="coerce").to_numpy(float) for c in ("best_bid", "best_ask", "depth_bid_5c", "depth_ask_5c")}
    return pd.DataFrame({"market_id": sw["market_id"].to_numpy(), "sbid": bid, "sask": ask,
                         "s_t": panel._epoch(sw["batch_receipt_utc"]), "s_two": two.astype(int),
                         "bsz1": f["bid_size_1"], "asz1": f["ask_size_1"], "dbid1": f["depth_bid_1c"], "dask1": f["depth_ask_1c"],
                         "dbid5": f["depth_bid_5c"], "dask5": f["depth_ask_5c"], "minord": f["min_order_size"],
                         "sbid_t1": g["best_bid"], "sask_t1": g["best_ask"], "dbid5_t1": g["depth_bid_5c"], "dask5_t1": g["depth_ask_5c"]})


def write_series(root: Path, cap: dict, spec: dict) -> tuple[bool, dict]:
    rows, dup = load_rows(cap["dir"])
    ser, sta = series_frame(rows, load_ext(cap["dir"]), spec)
    w1 = write_once_csv(Path(root) / "series" / f"{cap['id']}.csv.gz", ser)
    w2 = write_once_csv(Path(root) / "status" / f"{cap['id']}.csv.gz", sta)
    return (w1 or w2), {"rows": len(ser), "status_rows": len(sta), **dup,
                        "sidecar": bool((ser["sports"] != -1).any()) if len(ser) else None}


# --- E020 / E022 / E021: move units ---------------------------------------------------------------------------------


def _log_hte(end_ts, t) -> tuple[np.ndarray, np.ndarray]:
    hte = (np.asarray(end_ts, float) - np.asarray(t, float)) / 3600.0
    with np.errstate(divide="ignore", invalid="ignore"):
        lh = np.log(np.clip(hte, 1.0, None))
    ok = np.isfinite(lh)
    return np.where(ok, lh, 0.0), (~ok).astype(int)


def freeze_move(ser_k: pd.DataFrame, ser_p: pd.DataFrame, cap: dict, k: int, spec: dict, role: str, commit: str
                ) -> tuple[pd.DataFrame, dict]:
    """Every eligible |x| >= 1c mover at capture k (section 1.4; all categories, sports flag kept) with LT3's class and
    geometry and E020's order-event fields: the moved side, arrival (1) / cancellation (0) / neither (-1) from the
    quoted spread change, the unmoved quote U_k, the tick at k - 1 and k. Captures k - 1 and k only."""
    m, e = spec["move"], spec["e020"]
    j, cnt = l3.move_join(ser_k, ser_p, cap, spec, m["mid_lo"], m["mid_hi"], m["end_margin_h"])
    bid, ask, bid_p, ask_p = (j[c].to_numpy(float) for c in ("bid", "ask", "bid_p", "ask_p"))
    mid, mid_p = (bid + ask) / 2.0, (bid_p + ask_p) / 2.0
    x = mid - mid_p
    cls, geom = l3.classify(bid_p, ask_p, bid, ask, j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    mover = np.abs(x) >= m["min_abs_x"] - 1e-12
    u = j[mover].reset_index(drop=True)
    b, a, bp, ap, xm = bid[mover], ask[mover], bid_p[mover], ask_p[mover], x[mover]
    cl, ge = cls[mover], geom[mover]
    db, da = b - bp, a - ap
    side = np.where(np.abs(db) > np.abs(da), "bid", "ask").astype(object)
    qs_k, qs_p = a - b, ap - bp
    one = ge == "one_sided"
    eps = float(e["spread_eps"])
    arrival = np.where(~one, -1, np.where(qs_k < qs_p - eps, 1, np.where(qs_k > qs_p + eps, 0, -1)))
    tk = u["tick"].to_numpy(float)
    smax = float(spec["eligibility"]["spread_max"]) + 1e-12
    with np.errstate(invalid="ignore"):
        lo = float(e["support_min_ticks"]) * tk - 1e-9
        common = np.isfinite(tk) & (qs_k >= lo) & (qs_p >= lo) & (qs_k <= smax) & (qs_p <= smax)  # R1 finding 1
    U_k = np.where(one, np.where(side == "bid", a, b), np.nan)
    tick_k = u["tick"].to_numpy(float)
    tick_p = ser_p["tick"].reindex(pd.Index(u["market_id"].astype(str))).to_numpy(float) if "tick" in ser_p else np.full(len(u), np.nan)
    with np.errstate(invalid="ignore"):
        tick_ok = np.isfinite(tick_k) & np.isfinite(tick_p) & (np.abs(tick_k - tick_p) <= float(e["tick_eq_tol"]))
        logit = np.log(((b + a) / 2.0) / (1.0 - (b + a) / 2.0))
        lax = np.log(np.abs(xm))
    lh, lh_miss = _log_hte(u["end_ts"], u["t_row"])
    vk, vp = u["vol24"].to_numpy(float), u["vol24_p"].to_numpy(float)
    units = pd.DataFrame({
        "capture_id": cap["id"], "capture_t": cap["start"], "slot": k, "role": role,
        "market_id": u["market_id"].to_numpy(), "event_id": u["event_id"].to_numpy(), "t_row": u["t_row"].to_numpy(float),
        "sports": u["sports"].to_numpy(int), "neg_risk": u["neg_risk"].to_numpy(int), "crypto": u["crypto"].to_numpy(int),
        "skey": u["skey"].to_numpy(), "bid_k": b, "ask_k": a, "mid_k": (b + a) / 2.0, "bid_p": bp, "ask_p": ap,
        "spread_k": u["spread"].to_numpy(float), "spread_p": u["spread_p"].to_numpy(float), "x": xm, "db": db, "da": da,
        "cls": cl, "geom": ge, "side_moved": side, "arrival": arrival.astype(int), "U_k": U_k,
        "tick_k": tick_k, "tick_p": tick_p, "tick_ok": tick_ok.astype(int), "common": common.astype(int), "qs_k": qs_k, "qs_p": qs_p,
        "g_par": (ge == "parallel").astype(int), "g_os": one.astype(int), "g_sc": (ge == "spread_change").astype(int),
        "log_abs_x": lax, "logit_mid": logit, "abs_dev": np.abs((b + a) / 2.0 - 0.5),
        "log1p_vol": np.log1p(np.nan_to_num(vk, nan=0.0).clip(min=0)), "log1p_vol_p": np.log1p(np.nan_to_num(vp, nan=0.0).clip(min=0)),
        "log_hte": lh, "hte_missing": lh_miss, "rew": u["rew"].to_numpy(int) if "rew" in u else 0,
        "liq": u["liq"].to_numpy(float) if "liq" in u else np.nan,
        "fee_rate": u["fee_rate"].to_numpy(float), "fee_exp": u["fee_exp"].to_numpy(float),
    })
    os_qo = (cl == "quote_only") & one
    cnt.update(movers=int(mover.sum()), by_class={str(a_): int(b_) for a_, b_ in pd.Series(cl).value_counts().items()},
               one_sided_quote_only=int(os_qo.sum()), arrivals=int((os_qo & (arrival == 1)).sum()),
               cancellations=int((os_qo & (arrival == 0)).sum()), tick_flip_or_unknown=int((os_qo & ~tick_ok).sum()),
               off_common_support=int((os_qo & ~common).sum()))
    return _stamp(units, spec, commit), cnt


def _depth_usd(sb, sa, db, da) -> np.ndarray:
    return np.asarray(db, float) * np.asarray(sb, float) + np.asarray(da, float) * np.asarray(sa, float)


def freeze_hollow(ser_k: pd.DataFrame, ser_p: pd.DataFrame, sw_k: pd.DataFrame, cap: dict, k: int, spec: dict, role: str,
                  commit: str, sw_p: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """E022 lines: traded movers at capture k with the sweep-1 state of pass k (decision time = the sweep receipt).
    D0 = depth_bid_5c * sbid + depth_ask_5c * sask on the outcome-0 token; D2 = D0 + the same on the outcome-1 token
    (R1 finding 6); L = Gamma liquidity at capture k; h = clip(1 - D / L, 0, 1) with D = D0 or D2 by the census rule
    (spec ``hollow.depth_def``; null in a DRAFT: token0). Controls: the signed depth imbalance at pass k and the depth of
    sweep 1 of pass k - 1 (R1 finding 5; both pre-decision)."""
    units, cnt = freeze_move(ser_k, ser_p, cap, k, spec, role, commit)
    t = units[units["cls"] == "traded"].reset_index(drop=True)
    mids = pd.Index(t["market_id"].astype(str))
    cols = ["sbid", "sask", "s_t", "s_two", "dbid5", "dask5", "dbid1", "dask1", "sbid_t1", "sask_t1", "dbid5_t1", "dask5_t1"]
    sw = sw_k.reindex(mids) if sw_k is not None else pd.DataFrame(index=mids, columns=cols)
    for c in cols:
        if c not in sw:
            sw[c] = np.nan
    sb, sa = sw["sbid"].to_numpy(float), sw["sask"].to_numpy(float)
    two = np.nan_to_num(sw["s_two"].to_numpy(float), nan=0.0) == 1
    db5, da5 = sw["dbid5"].to_numpy(float), sw["dask5"].to_numpy(float)
    D0 = _depth_usd(sb, sa, db5, da5)
    D2 = D0 + _depth_usd(sw["sbid_t1"], sw["sask_t1"], sw["dbid5_t1"], sw["dask5_t1"])
    D1c = _depth_usd(sb, sa, sw["dbid1"], sw["dask1"])
    L = t["liq"].to_numpy(float)
    dd = spec["hollow"].get("depth_def") or "token0"
    D = D2 if dd == "both" else D0
    sx = np.sign(t["x"].to_numpy(float))
    if sw_p is not None:
        swp = sw_p.reindex(mids)
        Dp_raw = _depth_usd(swp["sbid"], swp["sask"], swp["dbid5"], swp["dask5"]) if "dbid5" in swp else np.full(len(t), np.nan)
        Dp2 = Dp_raw + (_depth_usd(swp["sbid_t1"], swp["sask_t1"], swp["dbid5_t1"], swp["dask5_t1"]) if "dbid5_t1" in swp else np.nan)
        Dp = Dp2 if dd == "both" else Dp_raw
        Dp = np.where(np.nan_to_num(swp["s_two"].to_numpy(float), nan=0.0) == 1, Dp, np.nan) if "s_two" in swp else np.full(len(t), np.nan)
    else:
        Dp = np.full(len(t), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        okL = np.isfinite(L) & (L > 0)
        Lsafe = np.where(okL, L, 1.0)
        ok = two & np.isfinite(D) & okL
        h = np.where(ok, np.clip(1.0 - D / Lsafe, 0.0, 1.0), np.nan)
        h0 = np.where(two & np.isfinite(D0) & okL, np.clip(1.0 - D0 / Lsafe, 0.0, 1.0), np.nan)
        h2 = np.where(two & np.isfinite(D2) & okL, np.clip(1.0 - D2 / Lsafe, 0.0, 1.0), np.nan)
        h1 = np.where(two & np.isfinite(D1c) & okL, np.clip(1.0 - D1c / Lsafe, 0.0, 1.0), np.nan)
        sup0 = np.where(two & np.isfinite(D0) & okL, (L >= D0).astype(float), np.nan)
        sup2 = np.where(two & np.isfinite(D2) & okL, (L >= D2).astype(float), np.nan)
        dimb = np.where(two & ((db5 + da5) > 0), sx * (da5 - db5) / (db5 + da5), np.nan)
        lDp = np.log1p(Dp)
    Dp_ok = np.isfinite(lDp)
    t = t.assign(sbid0=sb, sask0=sa, s_t0=sw["s_t"].to_numpy(float), s_two0=two.astype(int), D=D, D0=D0, D2=D2, L=L, h=h, h0=h0, h2=h2,
                 h1c=h1, zh=l3._z(h, spec["hollow"]["zh"]), superset=np.where(ok, (L >= D).astype(float), np.nan), superset0=sup0,
                 superset2=sup2, log1p_D=np.log1p(np.where(ok, D, np.nan)), log_L=np.log(np.where(okL, L, np.nan)),
                 sw_spread0=np.where(two, sa - sb, np.nan), dimb=np.nan_to_num(dimb, nan=0.0), dimb_missing=(~np.isfinite(dimb)).astype(int),
                 log1p_Dp=np.where(Dp_ok, lDp, 0.0), Dp_missing=(~Dp_ok).astype(int))
    hc = {"traded": len(t), "sweep_two_sided": int(two.sum()), "L_positive": int(okL.sum()), "h_defined": int(np.isfinite(h).sum()),
          "Dp_missing": int((~Dp_ok).sum()), "depth_def": dd}
    return _stamp(t, spec, commit), {**cnt, "hollow": hc}


def clock_fields(tr: pd.DataFrame, mkt: pd.Series, origin: np.ndarray, n_returned: np.ndarray, spec: dict) -> dict:
    """Per market: age of the newest trade row with ts < origin (any sign), rows in the 2 h before the origin and the
    clock status. The page is the newest rows, contiguous in time, so its newest pre-origin row is the true last trade
    before the origin whenever the page holds one."""
    c = spec["e021"]
    o_map = pd.Series(origin, index=mkt.astype(str).to_numpy())
    ts = pd.to_numeric(tr["ts"], errors="coerce").to_numpy(float)
    o = tr["market_id"].astype(str).map(o_map).to_numpy(float)
    with np.errstate(invalid="ignore"):
        pre = np.isfinite(o) & (ts < o)
        in2h = pre & (ts >= o - float(c["n2h_s"]))
    d = pd.DataFrame({"m": tr["market_id"].astype(str).to_numpy(), "ts": np.where(pre, ts, -np.inf), "n2h": in2h.astype(float),
                      "pre": pre.astype(float)})
    d["any_ts"] = ts
    g = d.groupby("m").agg(last=("ts", "max"), n2h=("n2h", "sum"), npre=("pre", "sum"), oldest=("any_ts", "min")).reindex(mkt.astype(str))
    last = g["last"].to_numpy(float)
    npre = g["npre"].fillna(0.0).to_numpy(float)
    age = np.where(npre > 0, origin - last, np.nan)
    full = np.asarray(n_returned, float) >= trade_sample.TRADE_LIMIT
    status = np.where(npre > 0, np.where(age <= float(c["max_age_s"]), "ok", "clock_inconsistent"),
                      np.where(full, "unclocked_truncated", "unclocked_no_prior")).astype(object)
    band = np.where(status != "ok", "", np.where(age <= float(c["fresh_max_s"]), "fresh",
                                                  np.where(age >= float(c["settled_min_s"]), "settled", "middle"))).astype(object)
    # n2h is under-counted when the page is full and its oldest row is after t - 2 h (page fill depends on post-origin
    # trading; R1 finding 3): flagged, excluded from E021's primary, counted
    with np.errstate(invalid="ignore"):
        n2h_tr = full & ~(g["oldest"].to_numpy(float) <= origin - float(c["n2h_s"]))
    return {"age": age, "n2h": g["n2h"].fillna(0.0).to_numpy(float), "clock": status, "band": band, "n2h_truncated": n2h_tr.astype(int)}


def freeze_clock(sample: dict, cap: dict, k: int, by_slot: dict, root: Path, spec: dict, role: str, commit: str,
                 feat_tr: tuple | None = None) -> tuple[pd.DataFrame, dict]:
    """E021 lines: sampled markets (status ok) that are |x| >= 1c movers at capture k (all classes kept; the analysis
    takes ``traded``), with the last-trade clock from rows with ts < the origin row's receipt."""
    feat, tr = feat_tr if feat_tr is not None else l3.load_sample(Path(sample["dir"]))
    ser_k, ser_p = l3.read_series(root, cap["id"]), l3.read_series(root, by_slot[k - 1]["id"])
    units, cnt = freeze_move(ser_k, ser_p, cap, k, spec, role, commit)
    f = feat.drop_duplicates("market_id")
    f = f.set_index(f["market_id"].astype(str).to_numpy())
    u = units[units["market_id"].astype(str).isin(f.index)].reset_index(drop=True)
    mk = u["market_id"].astype(str)
    origin = panel._epoch(f["origin_utc"].reindex(mk).astype(str))
    nret = f["n_returned"].reindex(mk).to_numpy(float)
    cf = clock_fields(tr[tr["market_id"].astype(str).isin(set(mk))], mk, origin, nret, spec)
    u = u.assign(sample_id=Path(sample["dir"]).name, origin_s=origin, n_returned=nret, age=cf["age"], n2h=cf["n2h"],
                 log1p_n2h=np.log1p(cf["n2h"]), clock=cf["clock"], band=cf["band"], n2h_truncated=cf["n2h_truncated"])
    tm = u["cls"] == "traded"
    cnt = {"sampled_ok": len(f), "sampled_movers": len(u), "sampled_traded": int(tm.sum()),
           "clock": {str(a): int(b) for a, b in u.loc[tm, "clock"].value_counts().items()},
           "band": {str(a): int(b) for a, b in u.loc[tm, "band"].value_counts().items()}}
    return _stamp(u, spec, commit), cnt


# --- E023 / E024: flow composition ----------------------------------------------------------------------------------


def composition(rows: pd.DataFrame, mkt: pd.Series, lo_s: float, hi_s: float) -> dict:
    """Per market over signed rows with o - lo_s <= ts < o - hi_s: OP (BUY notional share), C (largest row's notional
    share), HHI (Herfindahl of row notionals), o_leg / s_leg (signed opening / closing notional over total notional),
    OPno (share of BUY notional on outcome 1), Nsig (rows)."""
    ts, o, sg = rows["ts"].to_numpy(float), rows["o"].to_numpy(float), rows["sg"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        m = (ts >= o - lo_s) & (ts < o - hi_s) & (sg != 0)
    w = rows[m]
    nt = w["nt"].to_numpy(float)
    buy = w["side"].astype(str).to_numpy() == "BUY"
    oi = pd.to_numeric(w["outcome_index"], errors="coerce").to_numpy(float)
    d = pd.DataFrame({"m": w["market_id"].astype(str).to_numpy(), "nt": nt, "nt2": nt * nt, "bn": np.where(buy, nt, 0.0),
                      "bno": np.where(buy & (oi == 1), nt, 0.0), "on": np.where(buy, w["sg"].to_numpy(float) * nt, 0.0),
                      "sn": np.where(~buy, w["sg"].to_numpy(float) * nt, 0.0), "one": 1.0})
    g = d.groupby("m").agg(nt=("nt", "sum"), nt2=("nt2", "sum"), mx=("nt", "max"), bn=("bn", "sum"), bno=("bno", "sum"),
                           on=("on", "sum"), sn=("sn", "sum"), n=("one", "sum")).reindex(mkt.astype(str))
    NT = g["nt"].fillna(0.0).to_numpy(float)
    pos = NT > 0
    with np.errstate(invalid="ignore", divide="ignore"):
        return {"OP": np.where(pos, g["bn"].to_numpy(float) / NT, np.nan), "C": np.where(pos, g["mx"].to_numpy(float) / NT, np.nan),
                "HHI": np.where(pos, g["nt2"].to_numpy(float) / NT**2, np.nan),
                "o_leg": np.where(pos, g["on"].to_numpy(float) / NT, np.nan), "s_leg": np.where(pos, g["sn"].to_numpy(float) / NT, np.nan),
                "OPno": np.where(g["bn"].fillna(0.0).to_numpy(float) > 0, g["bno"].to_numpy(float) / g["bn"].to_numpy(float), np.nan),
                "Nsig": g["n"].fillna(0.0).to_numpy(float)}


def flow_inputs(sample: dict, cap: dict, root: Path, spec: dict, feat_tr: tuple) -> tuple[pd.Series, pd.DataFrame]:
    """(market ids in LT3 freeze_flow order, trade rows with sign / origin / notional): the same inputs LT3 uses."""
    feat, tr = feat_tr
    ser = l3.read_series(root, cap["id"])
    feat = feat[feat["market_id"].astype(str).isin(ser.index)].reset_index(drop=True)
    mkt = feat["market_id"].astype(str)
    s = ser.reindex(mkt)
    origin = panel._epoch(feat["origin_utc"])
    token0 = l3.token0_map(cap["dir"], mkt)
    token0.index = mkt.to_numpy()
    rows = l3.flow_rows(tr, pd.Series(origin, index=mkt.to_numpy()), pd.Series(s["tick"].to_numpy(float), index=mkt.to_numpy()), token0, spec)
    return mkt, rows


def freeze_flow(sample: dict, cap: dict, k: int, by_slot: dict, root: Path, spec: dict, role: str, commit: str,
                cache: dict | None = None, feat_tr: tuple | None = None) -> tuple[pd.DataFrame, dict]:
    """E023 / E024 lines: LT3's flow line (``live_tests3.freeze_flow``, unchanged: x6, W, H, N6, Size, coverage, controls,
    30-min-early versions) plus OP, C, HHI, the two legs and their standardised and early versions."""
    f = spec["flow"]
    feat_tr = feat_tr if feat_tr is not None else l3.load_sample(Path(sample["dir"]))
    fr, cnt = l3.freeze_flow(sample, cap, k, by_slot, root, spec, role, commit, cache, feat_tr)
    mkt, rows = flow_inputs(sample, cap, root, spec, feat_tr)
    assert len(mkt) == len(fr) and (mkt.to_numpy() == fr["market_id"].astype(str).to_numpy()).all()
    W6, lag = float(f["window_s"]), float(f["lag_s"])
    c6, cl = composition(rows, mkt, W6, 0.0), composition(rows, mkt, W6 + lag, lag)
    cov6, cov6l = fr["cov6"].to_numpy(int) == 1, fr["cov6_l30"].to_numpy(int) == 1
    out = {}
    for name in ("OP", "C", "HHI", "o_leg", "s_leg", "OPno", "Nsig"):
        out[name] = np.where(cov6, c6[name], np.nan)
        out[f"{name}_l30"] = np.where(cov6l, cl[name], np.nan)
    fr = fr.assign(**out)
    fr["zOP"], fr["zOP_l30"] = l3._z(fr["OP"], f["zOP"]), l3._z(fr["OP_l30"], f["zOP"])
    fr["zC"], fr["zC_l30"] = l3._z(fr["C"], f["zC"]), l3._z(fr["C_l30"], f["zC"])
    fr["o6s"] = np.clip(fr["o_leg"].to_numpy(float), -f["x6_clip"], f["x6_clip"]) / f["x6_sd"]
    return _stamp(fr, spec, commit), cnt


# --- outcomes ---------------------------------------------------------------------------------------------------------


def outcome_s(mids, sw: pd.DataFrame | None, missing: bool) -> pd.DataFrame:
    """LT3's sweep outcome plus the top sizes and the min order size (E020 S2, descriptive)."""
    out = l3.outcome_s(mids, sw, missing)
    for c in ("bsz1", "asz1", "minord"):
        out[c] = l3._look(sw, mids, c) if (sw is not None and not missing and c in sw) else np.nan
    return out


# --- the pass -------------------------------------------------------------------------------------------------------


def run_once(*, snapshot_root: Path = SNAPSHOT_ROOT, sample_root: Path = SAMPLE_ROOT, sweep_root: Path = SWEEP_ROOT,
             root: Path = OUT_ROOT, spec: dict | None = None, registered_utc: str = REGISTERED_UTC, end_utc: str = END_UTC,
             now: float | None = None, max_items: int = 40, allow_late: bool = False) -> dict:
    """Series, sweeps, freezes and due outcomes for everything new. Idempotent (write-once). ``allow_late`` is for DRY
    RUNS on past captures with an unpinned spec only (L6)."""
    if allow_late and spec is not None and spec.get("_pinned"):
        raise ValueError("allow_late is for dry runs with an unpinned spec only")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "run.lock", "a") as lk:
        try:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:  # another reader holds the root (L15)
            return {"status": "locked", "written": 0, "run_utc": iso(now_ts() if now is None else now)}
        return _run_locked(snapshot_root=snapshot_root, sample_root=sample_root, sweep_root=sweep_root, root=root, spec=spec,
                           registered_utc=registered_utc, end_utc=end_utc, now=now, max_items=max_items, allow_late=allow_late)


def _refuse_late(p: Path, now: float, stats: dict, log: list, kind: str, fid: str, k: int) -> None:
    stats["refused_late"] += 1
    write_once_csv(_marker(p, ".late.csv.gz"), pd.DataFrame({"late": [1], "checked_utc": [iso(now)]}))
    log.append({"kind": f"{kind}_refused_late", "id": fid, "slot": k, "written_utc": iso(now_ts())})


def _run_locked(*, snapshot_root: Path, sample_root: Path, sweep_root: Path, root: Path, spec: dict | None, registered_utc: str,
                end_utc: str, now: float | None, max_items: int, allow_late: bool) -> dict:
    spec = spec or load_spec()
    now = now_ts() if now is None else now
    commit = git_commit()
    st = l3.State(root)
    stats = {"run_utc": iso(now), "code_commit": commit, "spec_sha": spec["_sha256"][:16], "pinned": spec["_pinned"],
             "written": 0, "series": 0, "sweeps": 0, "outcomes": 0, "refused_late": 0, **{k: 0 for k in KINDS}}
    if root.exists() and dir_bytes(root) > DISK_CAP_BYTES:
        stats["status"] = "disk_cap"
        append_jsonl(root / "passes.jsonl", [{"kind": "disk_cap", **stats}])
        return stats
    t_reg, t_end = epoch(registered_utc), epoch(end_utc)
    by_slot = l3.scan_captures(snapshot_root, st, spec)
    samples = l3.scan_samples(sample_root, st)
    sweeps = l3.scan_sweeps(sweep_root, st)
    st.save()
    log: list[dict] = []
    budget = max_items
    pinned = spec["_pinned"]
    hi = t_end + 4 * GRID_S + l3.SLOT_TOL_S
    # 1. series + status, 2. sweep-1 files, for captures in [registered - 26 h, end + 4 slots)
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg - SERIES_LOOKBACK_S <= c["start"] < hi) or budget <= 0:
            continue
        if not ((root / "series" / f"{c['id']}.csv.gz").exists() and (root / "status" / f"{c['id']}.csv.gz").exists()):
            w, info = write_series(root, c, spec)
            if w:
                stats["series"] += 1
                budget -= 1
                log.append({"kind": "series", "id": c["id"], "slot": k, **info, "written_utc": iso(now_ts())})
        p = root / "sweeps" / f"{c['id']}.csv.gz"
        if c["id"] in sweeps and not p.exists() and budget > 0:
            if write_once_csv(p, sweep_frame(sweeps[c["id"]]["dir"], c["dir"])):
                stats["sweeps"] += 1
                budget -= 1
                log.append({"kind": "sweep", "id": c["id"], "sweep_id": sweeps[c["id"]]["id"], "written_utc": iso(now_ts())})
    # 3. capture freezes: move (E020 + mover lines), hollow (E022, needs sweep 1 of the pass)
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        role = l3.role_of(c["start"], registered_utc, end_utc, pinned)
        for kind in ("move", "hollow"):
            p = root / kind / "frozen" / f"{c['id']}.csv.gz"
            if p.exists() or any(_marker(p, s).exists() for s in MARKERS) or budget <= 0:
                continue
            late = not allow_late and l3.is_late(k + 1, now, spec)
            if late and kind == "hollow" and not (root / "sweeps" / f"{c['id']}.csv.gz").exists() and c["id"] not in sweeps:
                # sweep 1 of the pass did not exist by the deadline: missing for E022 (counted), not a late freeze; a sweep
                # that existed but was not yet written by this reader (budget) is a late freeze (R1 finding 11)
                write_once_csv(_marker(p, ".nosweep.csv.gz"), pd.DataFrame({"nosweep": [1], "checked_utc": [iso(now)]}))
                log.append({"kind": "hollow_no_sweep", "id": c["id"], "slot": k, "written_utc": iso(now_ts())})
                continue
            if late:
                _refuse_late(p, now, stats, log, kind, c["id"], k)
                continue
            if k - 1 not in by_slot:
                if l3.target_state(by_slot, k - 1, now, spec) == "pending":
                    continue
                write_once_csv(_marker(p, ".noprev.csv.gz"), pd.DataFrame({"noprev": [1]}))
                log.append({"kind": f"{kind}_no_previous_slot", "id": c["id"], "slot": k})
                continue
            if not l3.series_ready(root, by_slot, (k - 1, k)):
                continue
            ser_k, ser_p = l3.read_series(root, c["id"]), l3.read_series(root, by_slot[k - 1]["id"])
            if kind == "move":
                units, cnt = freeze_move(ser_k, ser_p, c, k, spec, role, commit)
            else:
                sst = l3.sweep_state(by_slot, sweeps, k, root, now, spec)
                if sst == "pending":
                    continue
                if sst == "missing":
                    write_once_csv(_marker(p, ".nosweep.csv.gz"), pd.DataFrame({"nosweep": [1]}))
                    log.append({"kind": "hollow_no_sweep", "id": c["id"], "slot": k})
                    continue
                units, cnt = freeze_hollow(ser_k, ser_p, l3.read_sweep(root, c["id"]), c, k, spec, role, commit,
                                           l3.read_sweep(root, by_slot[k - 1]["id"]))
            if write_once_csv(p, units):
                stats[kind] += 1
                budget -= 1
                log.append({"kind": f"{kind}_frozen", "id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
    # 4. sample freezes: clock (E021, first target k + 1) and flow (E023 / E024, target k + 3)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    rv_cache: dict = {}
    for sid in sorted(samples):
        k = slot_by_id.get(samples[sid]["snapshot_id"])
        if k is None:
            continue
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        role = l3.role_of(c["start"], registered_utc, end_utc, pinned)
        feat_tr = None
        for kind, first in (("clock", 1), ("flow", int(spec["flow"]["horizon_slots"]))):
            p = root / kind / "frozen" / f"{sid}.csv.gz"
            if p.exists() or any(_marker(p, s).exists() for s in MARKERS) or budget <= 0:
                continue
            if not allow_late and l3.is_late(k + first, now, spec):
                _refuse_late(p, now, stats, log, kind, sid, k)
                continue
            if kind == "clock":
                if k - 1 not in by_slot:
                    if l3.target_state(by_slot, k - 1, now, spec) == "pending":
                        continue
                    write_once_csv(_marker(p, ".noprev.csv.gz"), pd.DataFrame({"noprev": [1]}))
                    continue
                if not l3.series_ready(root, by_slot, (k - 1, k)):
                    continue
            elif not l3.series_ready(root, by_slot, range(k - int(spec["flow"]["rv_steps"]), k + 1)) or not (root / "series" / f"{c['id']}.csv.gz").exists():
                continue
            if feat_tr is None:
                feat_tr = l3.load_sample(Path(samples[sid]["dir"]))
            if kind == "clock":
                fr, cnt = freeze_clock(samples[sid], c, k, by_slot, root, spec, role, commit, feat_tr)
            else:
                fr, cnt = freeze_flow(samples[sid], c, k, by_slot, root, spec, role, commit, rv_cache, feat_tr)
            if write_once_csv(p, fr):
                stats[kind] += 1
                budget -= 1
                log.append({"kind": f"{kind}_frozen", "id": sid, "capture_id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
    # 5. outcomes: status + quote at k + h (series files) and the sweep-1 quote at k + s
    plan = {kind: (spec[kind]["horizons"], spec[kind]["sweep_tags"]) for kind in ("move", "hollow", "clock")}
    plan["flow"] = ([spec["flow"]["horizon_slots"]], spec["flow"]["sweep_tags"])
    for kind, (hs, ss) in plan.items():
        fdir = root / kind / "frozen"
        for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
            if p.name.endswith(MARKERS) or budget <= 0:
                continue
            fid = p.name[:-7]
            todo = [("h", h) for h in hs if not (root / kind / "outcomes" / f"{fid}.h{h}.csv.gz").exists()]
            todo += [("s", s) for s in ss if not (root / kind / "outcomes" / f"{fid}.s{s}.csv.gz").exists()]
            if not todo:
                continue
            k = l3._first_slot(p)
            if k is None:
                continue
            mids = None
            for typ, h in todo:
                if budget <= 0:
                    break
                j = k + h
                state = l3.target_state(by_slot, j, now, spec) if typ == "h" else l3.sweep_state(by_slot, sweeps, j, root, now, spec)
                if state == "pending" or (typ == "h" and state == "ready" and not l3.series_ready(root, by_slot, (j,))):
                    continue
                if mids is None:
                    mids = pd.read_csv(p, usecols=["market_id"], dtype={"market_id": str})["market_id"].to_numpy()
                if typ == "h":
                    out = l3.outcome_h(mids, by_slot, j, root, state == "missing")
                else:
                    out = outcome_s(mids, None if state == "missing" else l3.read_sweep(root, by_slot[j]["id"]), state == "missing")
                if write_once_csv(root / kind / "outcomes" / f"{fid}.{typ}{h}.csv.gz", out):
                    stats["outcomes"] += 1
                    budget -= 1
                    log.append({"kind": f"{kind}_outcome", "id": fid, "tag": f"{typ}{h}", "target_slot": j, "target": state,
                                "rows": len(out), "written_utc": iso(now_ts())})
    stats["written"] = sum(stats[k] for k in ("series", "sweeps", "outcomes", *KINDS))
    stats["status"] = "wrote" if stats["written"] else "nothing_new"
    for r in log:
        r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
    append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
    return stats


# --- operational counts (never reads a price, a move, a state value or a target) ----------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def ops_stats(root: Path = OUT_ROOT) -> dict:
    root = Path(root)
    out: dict = {"root": str(root), "bytes": dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "sweeps", *(f"{k}/frozen" for k in KINDS), *(f"{k}/outcomes" for k in KINDS)):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(MARKERS)]),
                    **{s.split(".")[1]: len([f for f in files if f.name.endswith(s)]) for s in MARKERS}}
    counts, status = {}, {}
    cols = {"move": ["role", "cls", "geom", "sports", "arrival", "tick_ok"], "hollow": ["role", "sports"],
            "clock": ["role", "cls", "clock", "band", "sports"], "flow": ["role", "sports", "cov6"]}
    for kind, cl in cols.items():
        d = root / kind / "frozen"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith(MARKERS):
                continue
            s = _read_ops(f, cl)
            for c in s.columns:
                for k, v in s[c].value_counts().items():
                    counts[f"{kind}:{c}:{k}"] = counts.get(f"{kind}:{c}:{k}", 0) + int(v)
        d = root / kind / "outcomes"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            tag = f.name[:-7].rsplit(".", 1)[-1]
            s = _read_ops(f, ["status"])
            for k, v in s["status"].value_counts().items():
                status[f"{kind}:{tag}:{k}"] = status.get(f"{kind}:{tag}:{k}", 0) + int(v)
    out.update(line_counts=counts, outcome_status_counts=status)
    return out


# --- censuses (counts only; pre-window data; sealed inputs; no target, no capture or sweep after the one classified) ---


def verify_files(seal: dict, files: list[tuple[str, Path]]) -> list[dict]:
    """[(archive path, local path)] against ``seal['files'][path]['sha256']``; a file missing locally, unsealed or with a
    different sha256 is returned as bad (L3: the census refuses)."""
    bad = []
    for rel, p in files:
        want = (seal.get("files", {}).get(rel) or {}).get("sha256")
        if not Path(p).exists():
            bad.append({"file": rel, "error": "missing"})
        elif want is None:
            bad.append({"file": rel, "error": "not sealed"})
        elif sha256_file(p) != want:
            bad.append({"file": rel, "error": "sha256 mismatch"})
    return bad


def capture_files(cap_dir: Path) -> list[tuple[str, Path]]:
    d = Path(cap_dir)
    out = [(f"data-dumps/research_lab/snapshots/{d.name}/{fn}", d / fn) for fn in ("rows.csv.gz", "manifest.json")]
    if (d / "rows_ext.csv.gz").exists():
        out.append((f"data-dumps/research_lab/snapshots/{d.name}/rows_ext.csv.gz", d / "rows_ext.csv.gz"))
    return out


def sweep_files(sweep_dir: Path) -> list[tuple[str, Path]]:
    d = Path(sweep_dir)
    return [(f"data-dumps/research_lab/book_sweeps/{d.name}/{fn}", d / fn) for fn in ("rows.csv.gz", "manifest.json")]


def _eff(df: pd.DataFrame, key: str = "market_id") -> pd.Series:
    """True for units in markets holding >= 2 units of the population (they survive the first-unit drop)."""
    n = df.groupby(key)[key].transform("size")
    return n >= 2


def _vif(df: pd.DataFrame, target: str, others: list[str]) -> float:
    """1 / (1 - R^2) of ``target`` on ``others`` (pooled OLS with intercept, finite rows only)."""
    d = df[[target, *others]].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(others) + 10:
        return float("nan")
    y = d[target].to_numpy()
    X = np.column_stack([np.ones(len(d)), d[others].to_numpy()])
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ c
    tss = float(((y - y.mean()) ** 2).sum())
    if tss <= 0:
        return float("nan")
    r2 = 1.0 - float((r**2).sum()) / tss
    return float(1.0 / max(1.0 - r2, 1e-12))


def _ms(v) -> dict:
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return {"centre": None, "scale": None, "n": 0}
    return {"centre": float(np.mean(v)), "scale": float(np.std(v, ddof=1)) if len(v) > 1 else None, "n": int(len(v)),
            "terciles": [float(x) for x in np.quantile(v, [1 / 3, 2 / 3])]}


def _day(t) -> np.ndarray:
    return pd.to_datetime(np.asarray(t, float), unit="s", utc=True).strftime("%Y-%m-%d").to_numpy()


def census_captures(*, seal: Path, snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT, work: Path,
                    days: list[str] | None = None, spec: dict | None = None, verify: bool = True) -> dict:
    """CQ (E020) and CH (E022): counts on the complete captures of ``days`` and sweep 1 of those passes, with slot k - 1
    for each. Every opened capture and sweep file is checked against the seal first (refused on any mismatch)."""
    spec = spec or load_spec(sha=None)
    days = days or spec["census_inputs"]["CQ_CH_days_utc"]
    work = Path(work)
    st = l3.State(work)
    by_slot = l3.scan_captures(snapshot_root, st, spec)
    sweeps = l3.scan_sweeps(sweep_root, st)
    ks = l3._days_of(by_slot, days)
    if not ks:
        return {"error": "no census captures", "days": days}
    need = sorted({j for k in ks for j in (k - 1, k) if j in by_slot})
    files = [f for j in need for f in capture_files(by_slot[j]["dir"])]
    files += [f for j in need if by_slot[j]["id"] in sweeps for f in sweep_files(sweeps[by_slot[j]["id"]]["dir"])]
    if verify:
        bad = verify_files(json.loads(Path(seal).read_text()), files)
        if bad:
            return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    for j in need:
        if not (work / "series" / f"{by_slot[j]['id']}.csv.gz").exists():
            write_series(work, by_slot[j], spec)
    U, H, per_cap = [], [], []
    for k in ks:
        c = by_slot[k]
        if k - 1 not in by_slot:
            per_cap.append({"capture": c["id"], "skipped": "no previous slot"})
            continue
        ser_k, ser_p = l3.read_series(work, c["id"]), l3.read_series(work, by_slot[k - 1]["id"])
        u, cm = freeze_move(ser_k, ser_p, c, k, spec, ROLE_UNREG, "census")
        u["day"] = _day([c["start"]] * len(u)) if len(u) else []
        U.append(u.drop(columns=["bid_k", "ask_k", "bid_p", "ask_p", "U_k"]))
        if c["id"] in sweeps:
            sw = sweep_frame(sweeps[c["id"]]["dir"], c["dir"]).set_index("market_id")
            pc = by_slot[k - 1]
            swp = sweep_frame(sweeps[pc["id"]]["dir"], pc["dir"]).set_index("market_id") if pc["id"] in sweeps else None
            h, ch = freeze_hollow(ser_k, ser_p, sw, c, k, spec, ROLE_UNREG, "census", swp)
            h["day"] = _day([c["start"]] * len(h)) if len(h) else []
            H.append(h[["market_id", "event_id", "skey", "sports", "day", "t_row", "geom", "x", "s_two0", "D0", "D2", "L", "h0", "h2",
                        "superset0", "superset2", *CONTROLS_E022]])
        else:
            ch = {"sweep": "missing"}
        per_cap.append({"capture": c["id"], "move": cm, "hollow": ch.get("hollow", ch)})
    U = pd.concat(U, ignore_index=True) if U else pd.DataFrame()
    H = pd.concat(H, ignore_index=True) if H else pd.DataFrame()
    scale = 21.0 / len(days)
    return {"days": days, "captures": [by_slot[k]["id"] for k in ks], "per_capture": per_cap, "inputs_verified": bool(verify),
            "CQ": census_cq(U, spec, scale, days), "CH": census_ch(H, U, spec, scale, days)}


def perm_share(df: pd.DataFrame, t0: float, min_stratum: int) -> dict:
    """Share of units in permutable strata (>= ``min_stratum`` units) for market x UTC day and the pre-declared fallback
    market x two-day block (blocks from ``t0``), and the stratum the rule picks (R1 finding 2): day if its share >= 50%,
    else block2 if its share >= 50%, else none (the test is dropped)."""
    if df.empty:
        return {"day": 0.0, "block2": 0.0, "stratum": None}
    t = df["t_row"].to_numpy(float)
    day = np.floor((t - t0) / 86400.0).astype(int)
    out = {}
    for name, key in (("day", day), ("block2", day // 2)):
        st = df["market_id"].astype(str).to_numpy() + "|" + key.astype(str)
        sz = pd.Series(st).map(pd.Series(st).value_counts()).to_numpy()
        out[name] = float((sz >= min_stratum).mean())
    out["stratum"] = "day" if out["day"] >= 0.5 else ("block2" if out["block2"] >= 0.5 else None)
    return out


def design_effect(ev: pd.Series, scale: float, rho: float) -> dict:
    """Census-computed event design effect (R1 finding 8): m = sum n_e^2 / sum n_e on the census days, projected to 21 days
    as m x scale (pessimistic: every event recurs through the window), DE = 1 + (m_21 - 1) rho."""
    n = ev.value_counts().to_numpy(float)
    m = float((n**2).sum() / n.sum()) if len(n) else float("nan")
    m21 = m * scale
    return {"m_census": m, "m_21d": m21, "rho": rho, "DE": 1.0 + (m21 - 1.0) * rho if np.isfinite(m21) else float("nan")}


def _t0(days: list[str]) -> float:
    return epoch(f"{sorted(days)[0]}T00:00:00Z")


def _family_rule(pop: pd.DataFrame, cap: float) -> tuple[pd.DataFrame, str, float | None]:
    """Answer 9 (R1): if the top series family holds > ``cap`` of the population, it is excluded from the primary."""
    fam = pop["skey"].astype(str).value_counts()
    top = float(fam.iloc[0] / fam.sum()) if len(fam) else None
    if top is not None and top > cap:
        return pop[pop["skey"].astype(str) != fam.index[0]], str(fam.index[0]), top
    return pop, "", top


def census_cq(U: pd.DataFrame, spec: dict, scale: float, days: list[str] | None = None) -> dict:
    g = spec["census_gates"]["CQ_E020"]
    if U.empty:
        return {"error": "no units", "gate_E020": {"pass": False}}
    os_ = U[(U["sports"] == 0) & (U["cls"] == "quote_only") & (U["geom"] == "one_sided")]
    tick_known = float((np.isfinite(os_["tick_k"]) & np.isfinite(os_["tick_p"])).mean()) if len(os_) else float("nan")
    full = os_[(os_["tick_ok"] == 1) & os_["arrival"].isin([0, 1])]
    cs = full[full["common"] == 1] if "common" in full else full  # R1 finding 1: common-support primary
    pop, excl, top = _family_rule(cs, float(g["family_cap"]))
    eff = _eff(pop) if len(pop) else pd.Series(dtype=bool)
    A, C = int((pop["arrival"] == 1).sum()), int((pop["arrival"] == 0).sum())
    a_eff, c_eff = float(((pop["arrival"] == 1) & eff).sum() * scale), float(((pop["arrival"] == 0) & eff).sum() * scale)
    share = A / (A + C) if A + C else float("nan")
    de = design_effect(pop["event_id"], scale, float(g["rho"]))
    a = {**g["mde_assumptions"], "deff_event": de["DE"]}
    mde = l3.mde_eff(a_eff, c_eff, a) * 100.0 if np.isfinite(de["DE"]) else float("inf")
    ps = perm_share(pop, _t0(days) if days else float(np.nanmin(pop["t_row"])) if len(pop) else 0.0, int(spec["gates"]["perm_min_stratum"]))
    res = {"one_sided_quote_only_non_sports": len(os_), "tick_known_share": tick_known, "full_population": len(full),
           "common_support": len(cs), "common_support_share": len(cs) / len(full) if len(full) else None,
           "full_by_class": {str(k): int(v) for k, v in full["arrival"].value_counts().items()},
           "exclude_family": excl, "top_family_share": top, "population": len(pop),
           "arrivals": A, "cancellations": C, "arrival_share": share, "arrivals_21d": A * scale, "cancellations_21d": C * scale,
           "arrivals_eff_21d": a_eff, "cancellations_eff_21d": c_eff, "design_effect": de, "mde_eff_c": mde,
           "perm_share": ps, "events": int(pop["event_id"].nunique()),
           "by_side": {str(k): int(v) for k, v in pop["side_moved"].value_counts().items()},
           "sports_one_sided": int(((U["sports"] == 1) & (U["cls"] == "quote_only") & (U["geom"] == "one_sided")).sum())}
    lo, hi = g["arrival_share"]
    res["gate_E020"] = _gate({"tick_known": bool(tick_known >= g["tick_known_min"]), "arrival_share": bool(lo <= share <= hi),
                              "arrivals_21d": res["arrivals_21d"] >= g["arrivals_21d"], "cancellations_21d": res["cancellations_21d"] >= g["cancellations_21d"],
                              "perm_share": ps["stratum"] is not None, "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return res


def census_ch(H: pd.DataFrame, U: pd.DataFrame, spec: dict, scale: float, days: list[str] | None = None) -> dict:
    """CH (E022): fixes the depth definition by the pre-declared counts rule (R1 finding 6: ``both`` if L >= D0 + D1 in
    >= 90% of covered books, else ``token0`` if L >= D0 in >= 90%, else drop), then the within-market identification
    (finding 4: VIF of zh on its expanding-past-demeaned controls; within-market IQR of the residual of h after the depth
    control), the design effect, the permuted share and the planning MDE."""
    g = spec["census_gates"]["CH_E022"]
    trad = U[(U["sports"] == 0) & (U["cls"] == "traded")] if len(U) else U
    if H.empty or not len(trad):
        return {"error": "no units", "gate_E022": {"pass": False}}
    hn = H[(H["sports"] == 0) & (H["s_two0"] == 1) & (H["L"] > 0)]
    sup0 = float(hn["superset0"].mean()) if len(hn) else float("nan")
    sup2 = float(hn["superset2"].mean()) if len(hn) else float("nan")
    dd = "both" if sup2 >= g["superset_min"] else ("token0" if sup0 >= g["superset_min"] else None)
    q = {}
    for nm, col in (("token0", "D0"), ("both", "D2")):
        r = (hn["L"] / hn[col].where(hn[col] > 0)).dropna()
        q[nm] = [float(x) for x in np.quantile(r, [0.1, 0.25, 0.5, 0.75, 0.9])] if len(r) else None
    res = {"traded_non_sports": len(trad), "superset_share": {"token0": sup0, "both": sup2}, "L_over_D_quantiles": q, "depth_def": dd}
    if dd is None:
        return {**res, "gate_E022": _gate({"depth_def": False})}
    hc = "h2" if dd == "both" else "h0"
    cov0 = hn[np.isfinite(hn[hc])].copy()
    cov0["h"] = cov0[hc]
    cov, excl, top = _family_rule(cov0, float(g["family_cap"]))
    cov = cov.sort_values(["market_id", "t_row"], kind="mergesort").reset_index(drop=True)
    cov_share = len(cov0) / len(trad)
    sc = _ms(cov["h"])
    cov["zh"] = (cov["h"] - (sc["centre"] or 0.0)) / (sc["scale"] or 1.0)
    cuts = sc.get("terciles") or [np.nan, np.nan]
    top_t, bot_t = cov[cov["h"] > cuts[1]], cov[cov["h"] <= cuts[0]]
    gap = float(top_t["zh"].mean() - bot_t["zh"].mean()) if len(top_t) and len(bot_t) else float("nan")
    dm = bd.expanding_demean(cov, ["zh", *CONTROLS_E022], "market_id", "t_row")
    vif_within = _vif(dm, "zh", CONTROLS_E022)
    vif_pooled = _vif(cov, "zh", CONTROLS_E022)
    iqrs = []
    for _, gm in cov[cov["Dp_missing"] == 0].groupby("market_id"):
        if len(gm) < g["iqr_min_units"]:
            continue
        X = np.column_stack([np.ones(len(gm)), gm["log1p_Dp"].to_numpy(float)])
        y = gm["h"].to_numpy(float)
        c_, *_ = np.linalg.lstsq(X, y, rcond=None)
        e = y - X @ c_
        iqrs.append(float(np.quantile(e, 0.75) - np.quantile(e, 0.25)))
    iqr_share = float(np.mean(np.asarray(iqrs) >= g["resid_iqr_min"])) if iqrs else float("nan")
    de = design_effect(cov["event_id"], scale, float(g["rho"]))
    n_eff = float(_eff(cov).sum() * scale) if len(cov) else 0.0
    a = g["mde_assumptions"]
    ok = n_eff > 0 and np.isfinite(vif_within) and np.isfinite(de["DE"])
    mde_sd = (a["t_sum"] * a["sd_c"] / math.sqrt(n_eff) * math.sqrt(de["DE"]) * a["day_factor"] * math.sqrt(vif_within)) if ok else float("inf")
    mde_t = mde_sd * gap if np.isfinite(gap) else float("inf")
    ps = perm_share(cov, _t0(days) if days else float(cov["t_row"].min()), int(spec["gates"]["perm_min_stratum"]))
    res.update({"covered": len(cov0), "covered_share": cov_share, "exclude_family": excl, "top_family_share": top, "population": len(cov),
                "markets_ge_min_units": len(iqrs), "resid_iqr_share": iqr_share, "h_scale": sc, "h_tercile_cuts": cuts, "gap_sd": gap,
                "vif_zh_within": vif_within, "vif_zh_pooled": vif_pooled, "design_effect": de, "covered_eff_21d": n_eff,
                "mde_per_sd_c": mde_sd * 100.0, "mde_tercile_c": mde_t * 100.0, "perm_share": ps, "events": int(cov["event_id"].nunique()),
                "Dp_missing_share": float(cov["Dp_missing"].mean()) if len(cov) else None})
    res["gate_E022"] = _gate({"depth_def": True, "covered_share": bool(cov_share >= g["covered_share_min"]),
                              "resid_iqr": bool(len(iqrs) >= g["iqr_min_markets"] and iqr_share >= g["iqr_share_min"]),
                              "perm_share": ps["stratum"] is not None, "mde_plan": bool(mde_t <= g["mde_max"])})
    return res


def touch_direction(sg: pd.DataFrame, by_slot: dict, k: int, work: Path) -> np.ndarray:
    """Touch-implied direction of signed fills (LT3 C2 rule): the quote of the most recent capture row of slots k - 3 .. k
    at most 300 s before the fill; outcome-0 price at or above the ask = +1, at or below the bid = -1, else 0."""
    imp = np.zeros(len(sg))
    mm = sg["market_id"].astype(str).to_numpy()
    oi = pd.to_numeric(sg["outcome_index"], errors="coerce").to_numpy(float)
    p0 = np.where(oi == 1, 1.0 - sg["p"].to_numpy(float), sg["p"].to_numpy(float))
    ts = sg["ts"].to_numpy(float)
    for jj in range(k - 3, k + 1):
        sj = l3.read_series(work, by_slot.get(jj, {}).get("id"))
        if sj is None:
            continue
        tq, bq, aq = l3._look(sj, mm, "t_row"), l3._look(sj, mm, "bid"), l3._look(sj, mm, "ask")
        with np.errstate(invalid="ignore"):
            near = np.isfinite(tq) & (ts >= tq) & (ts - tq <= 300.0) & np.isin(oi, (0.0, 1.0))
            v = np.where(p0 >= aq - 1e-6, 1.0, np.where(p0 <= bq + 1e-6, -1.0, 0.0))
        imp = np.where(near & (v != 0), v, imp)
    return imp


def census_flow(*, seal: Path, capture_seal: Path, sample_roots: list[Path], snapshot_root: Path = SNAPSHOT_ROOT, work: Path,
                spec: dict | None = None, verify: bool = True) -> dict:
    """CF (E021, E023, E024) on the sealed trade samples (LT3's C2 seal) and their captures k - 12 .. k (LT4's capture
    seal): pre-origin rows only; prints the clock, the open share, the concentration, side-touch agreement by arm,
    V*, scales, cuts, correlations, VIFs and the gates."""
    spec = spec or load_spec(sha=None)
    sl = json.loads(Path(seal).read_text())
    cseal = json.loads(Path(capture_seal).read_text()) if verify else {}
    work = Path(work)
    st = l3.State(work)
    by_slot = l3.scan_captures(snapshot_root, st, spec)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    f = spec["flow"]
    spec_c = json.loads(json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}))
    for z in ("zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE", "zOP", "zC"):
        spec_c["flow"][z] = {"centre": 0.0, "scale": 1.0}
    spec_c["flow"]["vol24_cap"] = None
    spec_c["hollow"]["zh"] = {"centre": 0.0, "scale": 1.0}
    spec_c["_sha256"], spec_c["_pinned"] = spec["_sha256"], False
    bad, frames, clocks = [], [], []
    tot = {"rows_pre_origin": 0, "ts_not_minute": 0, "side_unusable": 0, "signed": 0, "sell": 0}
    agree = {"buy": [0, 0], "sell": [0, 0], "largest": [0, 0], "other": [0, 0]}
    cache: dict = {}
    for sid in sl["samples"]:
        sdir = next((Path(r) / sid for r in sample_roots if (Path(r) / sid / "trades.csv.gz").exists()), None)
        if sdir is None:
            bad.append({"sample": sid, "error": "not found"})
            continue
        if verify:
            bad += [{"sample": sid, **b} for b in verify_files(sl, [(f"data-dumps/research_lab/trade_samples/{sid}/{fn}", sdir / fn)
                                                                 for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz")])]
        m = l3._manifest(sdir / "manifest.json")
        k = slot_by_id.get(m.get("snapshot_id"))
        if k is None:
            bad.append({"sample": sid, "error": "capture not found"})
            continue
        slots = [j for j in range(k - int(f["rv_steps"]), k + 1) if j in by_slot]
        if verify:
            bad += [{"sample": sid, **b} for j in slots for b in verify_files(cseal, capture_files(by_slot[j]["dir"]))]
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    for sid in sl["samples"]:
        sdir = next(Path(r) / sid for r in sample_roots if (Path(r) / sid / "trades.csv.gz").exists())
        k = slot_by_id[l3._manifest(sdir / "manifest.json").get("snapshot_id")]
        for j in range(k - int(f["rv_steps"]), k + 1):
            if j in by_slot and not (work / "series" / f"{by_slot[j]['id']}.csv.gz").exists():
                write_series(work, by_slot[j], spec)
        feat_tr = l3.load_sample(sdir)
        fr, _ = freeze_flow({"dir": sdir}, by_slot[k], k, by_slot, work, spec_c, ROLE_UNREG, "census", cache, feat_tr)
        fr["day"] = sid[:8]
        frames.append(fr)
        if k - 1 in by_slot:
            ck, _ = freeze_clock({"dir": sdir}, by_slot[k], k, by_slot, work, spec_c, ROLE_UNREG, "census", feat_tr)
            ck["day"] = sid[:8]
            clocks.append(ck[["market_id", "event_id", "sports", "day", "t_row", "cls", "clock", "band", "age", "n2h", "n2h_truncated"]])
        # row-level checks (pre-origin rows; signed rows for the agreement arms)
        mkt, rows = flow_inputs({"dir": sdir}, by_slot[k], work, spec, feat_tr)
        pre = rows[rows["ts"].to_numpy(float) < rows["o"].to_numpy(float)]
        tot["rows_pre_origin"] += len(pre)
        tot["ts_not_minute"] += int((np.mod(pre["ts"].to_numpy(float), 60.0) != 0).sum())
        tot["side_unusable"] += int((pre["sg"].to_numpy(float) == 0).sum())
        sg = pre[(pre["sg"] != 0) & (pre["ts"].to_numpy(float) >= pre["o"].to_numpy(float) - float(f["window_s"]))].copy()
        tot["signed"] += len(sg)
        sell = sg["side"].astype(str).to_numpy() == "SELL"
        tot["sell"] += int(sell.sum())
        imp = touch_direction(sg, by_slot, k, work)
        has = imp != 0
        same = sg["sg"].to_numpy(float) == imp
        rk = sg.groupby("market_id")["nt"].rank(method="first", ascending=False).to_numpy() == 1
        for lab, msk in (("buy", has & ~sell), ("sell", has & sell), ("largest", has & rk), ("other", has & ~rk)):
            agree[lab][0] += int((same & msk).sum())
            agree[lab][1] += int(msk.sum())
    F = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    K = pd.concat(clocks, ignore_index=True) if clocks else pd.DataFrame()
    if F.empty:
        return {"error": "no usable sample"}
    n_days = len({str(s)[:8] for s in sl["samples"]})
    scale = 21.0 / max(n_days, 1)
    day1 = sorted({str(s)[:8] for s in sl["samples"]})[0]
    res = {"seal": str(seal), "capture_seal": str(capture_seal), "inputs_verified": bool(verify), "samples": len(frames), "totals": tot,
           "CF_E021": census_clock(K, spec, scale, day1, tot), **census_comp(F, spec, scale, day1, agree, tot)}
    return res


def census_clock(K: pd.DataFrame, spec: dict, scale: float, day1: str, tot: dict) -> dict:
    g = spec["census_gates"]["CF_E021"]
    if K.empty:
        return {"error": "no clock lines", "gate_E021": {"pass": False}}
    tm = K[K["cls"] == "traded"]
    ok = tm[tm["clock"] == "ok"]
    band = ok[ok["band"].isin(["fresh", "settled"])]
    pop = band[band["n2h_truncated"] == 0]  # R1 finding 3: n2h under-counted when the page is full
    eff = _eff(pop) if len(pop) else pd.Series(dtype=bool)
    nf_eff, ns_eff = float(((pop["band"] == "fresh") & eff).sum() * scale), float(((pop["band"] == "settled") & eff).sum() * scale)
    de = design_effect(pop["event_id"], scale, float(g["rho"]))
    a = {**g["mde_assumptions"], "deff_event": de["DE"]}
    mde = l3.mde_eff(nf_eff, ns_eff, a) * 100.0 if np.isfinite(de["DE"]) else float("inf")
    fs = float((ok["band"] == "fresh").mean()) if len(ok) else float("nan")
    ss = float((ok["band"] == "settled").mean()) if len(ok) else float("nan")
    trunc = float((tm["clock"] == "unclocked_truncated").mean()) if len(tm) else float("nan")
    n2t = float(band["n2h_truncated"].mean()) if len(band) else float("nan")
    t0 = epoch(f"{day1[:4]}-{day1[4:6]}-{day1[6:8]}T00:00:00Z")
    ps = perm_share(pop, t0, int(spec["gates"]["perm_min_stratum"]))
    dec = pd.qcut(band["n2h"].rank(method="first"), 10, labels=False) if len(band) >= 10 else pd.Series(dtype=int)
    res = {"traded_sampled_movers": len(tm), "clock_status": {str(a_): int(b) for a_, b in tm["clock"].value_counts().items()},
           "band": {str(a_): int(b) for a_, b in ok["band"].value_counts().items()}, "fresh_share": fs, "settled_share": ss,
           "clocked_21d": float(len(ok) * scale), "unclocked_truncated_share": trunc, "n2h_truncated_share": n2t,
           "fresh_eff_21d": nf_eff, "settled_eff_21d": ns_eff, "design_effect": de, "mde_eff_c": mde, "perm_share": ps,
           "sports_share": float((pop["sports"] == 1).mean()) if len(pop) else None,
           "band_by_n2h_decile": {str(int(d)): {str(b): int(v) for b, v in band.loc[dec.index[dec == d], "band"].value_counts().items()}
                                  for d in sorted(dec.unique())} if len(dec) else {},
           "age_quantiles_s": [float(x) for x in np.quantile(ok["age"], [0.1, 0.25, 0.5, 0.75, 0.9])] if len(ok) else None}
    tsn = tot["ts_not_minute"] / tot["rows_pre_origin"] if tot.get("rows_pre_origin") else float("nan")
    res["ts_not_minute_share"] = tsn
    return {**res, "gate_E021": _gate({"ts_second_level": bool(tsn >= g["ts_not_minute_min"]), "fresh_share": bool(fs >= g["band_share_min"]),
                                       "settled_share": bool(ss >= g["band_share_min"]), "clocked_21d": res["clocked_21d"] >= g["clocked_21d"],
                                       "unclocked_truncated": bool(trunc <= g["unclocked_truncated_max"]),
                                       "perm_share": ps["stratum"] is not None, "mde_eff": bool(mde <= g["mde_max"] * 100.0)})}


def _gate(d: dict) -> dict:
    d["pass"] = all(d.values())
    return d


def census_comp(F: pd.DataFrame, spec: dict, scale: float, day1: str, agree: dict, tot: dict) -> dict:
    """E023 / E024 parts of CF: V*, the covered population, scales, cuts, correlations, VIFs, agreement and the gates."""
    f = spec["flow"]
    g3, g4 = spec["census_gates"]["CF_E023"], spec["census_gates"]["CF_E024"]
    base = F[(F["tight_i"] == 1) & (F["end_ok_7h"] == 1)]
    cand = base[(base["cov6"] == 0) | (np.nan_to_num(base["N6"].to_numpy(float)) > 0)]
    trunc = pd.DataFrame({"vol24_i": cand["vol24_i"].to_numpy(float), "trunc6": (cand["cov6"].to_numpy(int) == 0).astype(int)})
    vstar = l3.vol24_cap_rule(trunc, float(f["vol24_cap_max_trunc_share"]))
    cov = base[(base["cov6"] == 1) & (np.nan_to_num(base["N6"].to_numpy(float)) > 0)]
    cov = cov[cov["vol24_i"] <= vstar] if np.isfinite(vstar) else cov
    with np.errstate(divide="ignore", invalid="ignore"):
        z = pd.DataFrame({"W": cov["W"], "H": cov["H"], "OP": cov["OP"], "C": cov["C"].where(cov["Nsig"] >= f["min_rows_C"]),
                          "lN": np.log(cov["N6"]), "lS": np.log(cov["Size"]), "SPR": cov["spread_i"], "lRV": np.log(cov["rv"] + 1e-4),
                          "lHTE": np.where(cov["hte_missing"] == 0, cov["log_hte"], np.nan)})
    scales = {"zW": _ms(z["W"]), "zH": _ms(z["H"]), "zN": _ms(z["lN"]), "zSize": _ms(z["lS"]), "zSPR": _ms(z["SPR"]),
              "zRV": _ms(z["lRV"]), "zHTE": _ms(z["lHTE"]), "zOP": _ms(z["OP"]), "zC": _ms(z["C"])}
    zs = pd.DataFrame({k: (z[c] - (scales[k]["centre"] or 0.0)) / (scales[k]["scale"] or 1.0)
                       for k, c in (("zW", "W"), ("zH", "H"), ("zN", "lN"), ("zSize", "lS"), ("zSPR", "SPR"), ("zRV", "lRV"),
                                    ("zHTE", "lHTE"), ("zOP", "OP"), ("zC", "C"))})

    def corr(a: str, b: str) -> float:
        d = z[[a, b]].dropna()
        return float(np.corrcoef(d[a], d[b])[0, 1]) if len(d) > 2 else float("nan")

    ev_all = set(cov["event_id"])
    ev1 = set(cov.loc[cov["day"] == day1, "event_id"])
    e21 = l3.project_events(ev1, ev_all, len({*cov["day"]}) or 1)
    base_mde = float(g3["mde_base"])
    # R1 finding 9: VIF of the tested interaction x6 * zM against the model's other x6 terms, after expanding-past demeaning
    x6 = cov["x6"].to_numpy(float)
    it = pd.DataFrame({"market_id": cov["market_id"].astype(str).to_numpy(), "t_row": cov["t_row"].to_numpy(float), "x6": x6,
                       "x6_absdev": x6 * cov["abs_dev"].to_numpy(float)})
    for zc in ("zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE", "zOP", "zC"):
        it[f"x6_{zc}"] = x6 * zs[zc].to_numpy(float)
    it = it.sort_values(["market_id", "t_row"], kind="mergesort").reset_index(drop=True)
    ints = [c for c in it.columns if c.startswith("x6")]
    dm = bd.expanding_demean(it, ints, "market_id", "t_row")
    base_terms = ["x6", "x6_absdev", "x6_zN", "x6_zSize", "x6_zSPR", "x6_zRV", "x6_zHTE"]
    vif_op = _vif(dm, "x6_zOP", base_terms)
    vif_c = _vif(dm, "x6_zC", [*base_terms, "x6_zW", "x6_zH"])
    res_vif_pooled = {"zOP": _vif(zs, "zOP", ["zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE"]),
                      "zC": _vif(zs, "zC", ["zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE"])}
    mde = {n: (base_mde * math.sqrt(5000.0 / e21) * math.sqrt(v)) if e21 > 0 and np.isfinite(v) else float("inf") for n, v in (("OP", vif_op), ("C", vif_c))}
    ag = {k: (v[0] / v[1] if v[1] else None) for k, v in agree.items()}
    n_min = int(g3["agreement_min_rows"])
    gap3 = (ag["buy"] - ag["sell"]) if None not in (ag["buy"], ag["sell"]) else None
    gap4 = (ag["other"] - ag["largest"]) if None not in (ag["other"], ag["largest"]) else None
    op_int = np.isfinite(z["OP"]) & (z["OP"] > 0) & (z["OP"] < 1)
    c_int = np.isfinite(z["C"]) & (z["C"] < 1)
    sell_share = tot["sell"] / tot["signed"] if tot["signed"] else float("nan")
    unusable = tot["side_unusable"] / tot["rows_pre_origin"] if tot["rows_pre_origin"] else float("nan")
    lo, hi = g3["sell_share"]
    res = {"vol24_cap": vstar, "trunc6_share": float(trunc["trunc6"].mean()) if len(trunc) else None, "covered_units": len(cov),
           "covered_21d": float(len(cov) * scale), "events": len(ev_all), "events_21d": e21, "scales": scales,
           "ts_not_minute_share": tot["ts_not_minute"] / tot["rows_pre_origin"] if tot["rows_pre_origin"] else None,
           "sell_share": sell_share, "side_unusable_share": unusable,
           "OP_interior_share": float(op_int.mean()) if len(z) else None, "OP_interior_21d": float(op_int.sum() * scale),
           "C_interior_21d": float(c_int.sum() * scale),
           "corr": {"OP_W": corr("OP", "W"), "OP_H": corr("OP", "H"), "C_W": corr("C", "W"), "C_H": corr("C", "H"), "C_lN": corr("C", "lN")},
           "max_abs_corr_controlled": {m: _max_corr(z, m, ctl) for m, ctl in (("OP", ["W", "H", "lN", "lS", "SPR", "lRV", "lHTE"]),
                                                                              ("C", ["W", "H", "lN", "lS", "SPR", "lRV", "lHTE"]))},
           "vif": {"x6_zOP_within": vif_op, "x6_zC_within": vif_c, "pooled_main_effects": res_vif_pooled}, "mde_plan": mde,
           "agreement": {"rates": ag, "n": {k: v[1] for k, v in agree.items()}, "gap_buy_minus_sell": gap3, "gap_other_minus_largest": gap4,
                         "min_rows_per_arm": n_min},
           "econ_cuts": {"OP_upper_cut": (scales["zOP"].get("terciles") or [None, None])[1], "C_upper_cut": (scales["zC"].get("terciles") or [None, None])[1]}}
    ok3 = agree["buy"][1] >= n_min and agree["sell"][1] >= n_min
    ok4 = agree["largest"][1] >= n_min and agree["other"][1] >= n_min
    c = res["corr"]
    res["CF_E023"] = {"gate_E023": _gate({
        "vol24_cap_defined": bool(not math.isnan(vstar)), "sell_share": bool(lo <= sell_share <= hi),
        "side_unusable": bool(unusable <= g3["side_unusable_max"]),
        "OP_interior": bool((res["OP_interior_share"] or 0.0) >= g3["OP_interior_share_min"] and res["OP_interior_21d"] >= g3["OP_interior_21d"]),
        "corr": bool(np.isfinite(c["OP_W"]) and np.isfinite(c["OP_H"]) and abs(c["OP_W"]) <= g3["corr_max"] and abs(c["OP_H"]) <= g3["corr_max"]),
        "agreement_gap": bool(ok3 and gap3 is not None and gap3 <= g3["agreement_gap_max"]),
        "corr_controlled": bool(res["max_abs_corr_controlled"]["OP"] <= g3["corr_max"]),
        "mde_plan": bool(mde["OP"] <= g3["mde_max"])})}
    res["CF_E024"] = {"gate_E024": _gate({
        "vol24_cap_defined": bool(not math.isnan(vstar)), "C_interior_21d": res["C_interior_21d"] >= g4["C_interior_21d"],
        "corr": bool(np.isfinite(c["C_W"]) and np.isfinite(c["C_H"]) and abs(c["C_W"]) <= g4["corr_max"] and abs(c["C_H"]) <= g4["corr_max"]),
        "agreement_gap": bool(ok4 and gap4 is not None and gap4 <= g4["agreement_gap_max"]),
        "corr_controlled": bool(res["max_abs_corr_controlled"]["C"] <= g4["corr_max"]),
        "mde_plan": bool(mde["C"] <= g4["mde_max"])})}
    return res


def _max_corr(z: pd.DataFrame, m: str, others: list[str]) -> float:
    """Largest |corr| of moderator ``m`` with the moderators whose x6 interactions are controls (NaN fails the gate):
    the donor gate is size-checked only up to 0.5 (LIVE_TESTS_4.md 14.5)."""
    vals = []
    for o in others:
        d = z[[m, o]].dropna()
        vals.append(abs(float(np.corrcoef(d[m], d[o])[0, 1])) if len(d) > 2 else float("nan"))
    return float("nan") if not vals or any(not np.isfinite(v) for v in vals) else max(vals)


def cleanup_census(work: Path) -> None:
    shutil.rmtree(work, ignore_errors=True)

