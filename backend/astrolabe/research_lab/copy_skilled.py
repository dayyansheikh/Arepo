# ruff: noqa: E501
"""LIVE prospective test E026 "copy skilled wallets with latency" (docs/research_lab/LIVE_TESTS_COPY.md). DRAFT until
the ledger registration.

Research tooling only. Nothing here trades, holds credentials or labels a wallet as informed or insider. A "copy" is a
PAPER position priced from quotes AREPO already captured; no order is ever sent. Wallets are HMAC hashes
(``wallet_sidecar.hash_wallet``); no raw address is read, stored or printed.

Pieces (each a pure function plus a thin I/O pass; every data file is WRITE-ONCE, atomic, floats ``%.17g``):

* ``freeze_skillset``: the frozen skilled set, built ONCE from the HB1 history panels with the frozen wallet-skill spec
  (``wallet_skill.build_profiles_batch`` at ``t_freeze`` = REGISTERED_UTC; only outcomes known strictly before it;
  MIN_POS 5, N0 10, top 10% of eligible by ``skill_score`` with ``skill_z > 0``). Written to ``skillset/``; its sha256
  is pinned in the spec at registration.
* ``signals_from_batch``: from one batch of observed taker trades with receipt times (one trade sample's wallet
  sidecar, or one UTC hour of the >= $1k live-print stream), the FIRST in-window trade of each (frozen-skilled wallet,
  market) not signalled before becomes a skilled copy signal; up to ``n_controls`` matched control trades (non-skilled
  wallets, same batch, same side, same trade-price bucket, same trade-age bucket, other event) are drawn by a
  deterministic hash. Lines go to ``signals/<batch>.csv.gz``.
* ``entries_for_capture``: a signal's paper entry for latency L is the quote of the FIRST complete-universe capture
  whose start is >= receipt + L (never earlier; receipt-timed rows); the fixed-horizon exit is the first capture
  starting >= entry row receipt + EXIT_H. Lines go to ``entries/<capture>.csv.gz``.
* ``label_resolutions``: Gamma resolution records (network, read-only GET), ``resolutions/<pass>.csv.gz``; the first
  final record per market wins at analysis.

Causality: a signal uses only trades received by its batch's receipt; its entry quote is received at or after
receipt + L; the skilled set is frozen before the window from outcomes known before it. Nothing is back-filled.
"""

from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import wallet_skill as ws

VERSION = "copy-skilled-v1"
EXPERIMENTS = ("E026-N", "E026-C")
ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_ROOT = ROOT / "data-dumps" / "research_lab" / "snapshots"
SAMPLE_ROOT = ROOT / "data-dumps" / "research_lab" / "trade_samples"
LIVE_TRADES_ROOT = ROOT / "data-dumps" / "research_lab" / "live_trades"
HISTORY_ROOT = ROOT / "data-dumps" / "research_lab" / "history"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "copy_skilled"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "copy_skilled_v1.json"
SPEC_SHA256 = None  # pinned at registration (LIVE_TESTS_COPY.md 9); None = DRAFT, every line is prospective_unregistered

REGISTERED_UTC = "2026-10-25T00:00:00Z"
END_UTC = "2026-11-15T00:00:00Z"
LABEL_CUTOFF_UTC = "2026-12-06T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-12-06T12:00:00Z"
IN_PROGRESS_GRACE_S = 4 * 3600  # a sample still not complete this long after its start is recorded missing
TEMPFAIL = 75
DISK_CAP_BYTES = int(1.0e9)
ROLE_CONF, ROLE_UNREG = "prospective_confirmation", "prospective_unregistered"
CODE_FILES = ("copy_skilled.py", "copy_skilled_analysis.py", "wallet_skill.py", "wallet_skill_dev.py", "costs.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)

ARMS = ("sidecar", "large_prints")
SIGNAL_COLS = ["signal_id", "arm", "role", "parent_id", "batch_id", "market_id", "condition_id", "event_id", "wallet",
               "skill_score", "skill_n_pos", "trade_ts", "side", "outcome_index", "trade_price", "trade_size",
               "trade_notional", "copy_token", "receipt_ts", "age_s", "price_bucket", "age_bucket", "end_ts_origin",
               "end_bucket", "prior_visible", "n_controls",
               "evidence_role", "spec_sha", "code_sha", "code_commit", "frozen_utc"]
ENTRY_COLS = ["signal_id", "kind", "latency_s", "due_ts", "capture_id", "capture_start_ts", "row_received_ts", "status",
              "best_bid", "best_ask", "spread", "last_trade_price", "liquidity", "volume24hr", "end_ts", "event_id",
              "fee_category", "fees_enabled", "fee_schedule_rate", "fee_exponent", "spec_sha", "code_sha", "frozen_utc"]
RES_COLS = ["market_id", "fetched_ts", "http_status", "closed", "outcome_prices", "pay0", "state", "uma_status",
            "spec_sha", "code_sha"]
SNAP_COLS = ["market_id", "condition_id", "event_id", "received_utc", "capture_start_utc", "closed", "active", "best_bid",
             "best_ask", "spread", "last_trade_price", "liquidity", "volume24hr", "end_date"]
EXT_COLS = ["market_id", "fee_category", "fees_enabled", "fee_schedule"]


# --- small utilities ------------------------------------------------------------------------------------------------


def epoch(v) -> float:
    try:
        return float(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return math.nan


def iso(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def now_ts() -> float:
    return datetime.now(UTC).timestamp()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=15)
        return out.stdout.strip()[:12] or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (the spec pins the code hashes and the code
    pins the spec hash, so the pin line itself stays outside the code hash)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: code_sha256(here / n) for n in CODE_FILES}


def reader_sha() -> str:
    """16 hex digits identifying the recorder code (this module + wallet_skill, which defines the trade normalisation)."""
    h = code_hashes()
    return hashlib.sha256((h["copy_skilled.py"] + h["wallet_skill.py"]).encode()).hexdigest()[:16]


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"copy_skilled spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"] = got
    spec["_pinned"] = sha is not None
    if sha is not None:  # a pinned spec must carry every pin it depends on (a null pin would silently skip its check)
        have = spec.get("code_sha256") or {}
        gaps = [k for k, ok in (("skillset_sha256", bool(spec.get("skillset_sha256"))),
                                ("code_sha256", all(have.get(f) for f in CODE_FILES)),
                                ("impact_table_sha256", bool(spec.get("impact_table_sha256")))) if not ok]
        if gaps:
            raise RuntimeError(f"copy_skilled pinned spec is missing {gaps}")
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("label_cutoff_utc", LABEL_CUTOFF_UTC),
                     ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"copy_skilled spec {key} {spec.get(key)!r} != module constant {val!r}")
    return spec


def role_of(receipt_ts: float, spec: dict) -> str:
    ok = bool(spec.get("_pinned")) and epoch(spec["registered_utc"]) <= receipt_ts < epoch(spec["end_utc"])
    return ROLE_CONF if ok else ROLE_UNREG


def write_once_csv(path: Path, df: pd.DataFrame) -> bool:
    """Gzip CSV (floats ``%.17g``, exact round trip) written only if ``path`` does not exist; atomic (tmp + hard link)."""
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    df.to_csv(tmp, index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.17g")
    with open(tmp, "rb") as fh:
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def append_jsonl(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def dir_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file()) if Path(path).exists() else 0


def bucket(x: np.ndarray, edges: Iterable[float]) -> np.ndarray:
    """Index of the half-open bucket [e_i, e_{i+1}) holding x (-1 if outside or NaN)."""
    e = np.asarray(list(edges), float)
    x = np.asarray(x, float)
    i = np.searchsorted(e, x, side="right") - 1
    bad = ~np.isfinite(x) | (i < 0) | (i >= len(e) - 1)
    return np.where(bad, -1, i).astype(int)


def signal_key(arm: str, wallet: str, market_id: int, ts: float, side: int, k: int, price: float, size: float) -> str:
    raw = f"{arm}|{wallet}|{int(market_id)}|{float(ts):.3f}|{int(side)}|{int(k)}|{float(price):.8f}|{float(size):.8f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _rank_key(parent: str, cand: str) -> str:
    return hashlib.sha256(f"{parent}|{cand}".encode()).hexdigest()


# --- frozen skilled set -----------------------------------------------------------------------------------------------


def skillset_frame(trades: pd.DataFrame, res: pd.DataFrame, t_freeze: float, skill: dict) -> pd.DataFrame:
    """Eligible wallets as of ``t_freeze`` (positions in markets known strictly before it), with the frozen skilled flag.

    Exactly the development construction (WALLET_SKILL.md 1-2): ``build_profiles_batch`` then ``snapshot_frame``."""
    prof = ws.build_profiles_batch(trades, res, t_freeze, n0=float(skill["n0"]), min_pos=int(skill["min_pos"]))
    snap = ws.snapshot_frame(prof, as_of=t_freeze, top_frac=float(skill["top_frac"]))
    return snap.sort_values("wallet", kind="stable").reset_index(drop=True)


def freeze_skillset(history_root: Path, out_dir: Path, spec: dict, *, now: float | None = None) -> dict:
    """Build and write the frozen skilled set once (write-once ``skillset.csv.gz`` + ``skillset_manifest.json``)."""
    from . import wallet_skill_dev as wd

    out_dir = Path(out_dir)
    path, man_path = out_dir / "skillset.csv.gz", out_dir / "skillset_manifest.json"
    if path.exists() or man_path.exists():
        raise RuntimeError(f"skillset already frozen at {out_dir}; it is never rebuilt")
    now = now_ts() if now is None else now
    t_freeze = epoch(spec["skill"]["t_freeze_utc"])
    if now >= t_freeze:
        raise RuntimeError("freeze refused at or after t_freeze (the set must exist before the window starts)")
    panels = tuple(spec["skill"]["history_panels"])
    h = wd.load_history(Path(history_root), panels=panels)
    pt, res = wd.profile_trades(h)
    snap = skillset_frame(pt, res, t_freeze, spec["skill"])
    chk = freeze_checks(int(len(snap)), int(snap["skilled"].sum()), float(res["known_ts"].max()) if len(res) else None,
                        spec["skill"].get("expected"))
    if chk["refuse"]:  # before anything is written: a wrong set must not become the (never rebuilt) frozen set
        raise RuntimeError(f"freeze refused, expectation mismatch: {chk}")
    if not write_once_csv(path, snap):
        raise RuntimeError("skillset write raced")
    man = {"version": VERSION, "skill_version": ws.SKILL_VERSION, "t_freeze_utc": spec["skill"]["t_freeze_utc"],
           "frozen_utc": iso(now), "history_panels": list(panels), "profile_trades": int(len(pt)),
           "resolved_markets": int(len(res)), "max_known_ts": float(res["known_ts"].max()) if len(res) else None,
           "max_trade_ts": float(pt["ts"].max()) if len(pt) else None, "eligible": int(len(snap)),
           "skilled": int(snap["skilled"].sum()), "checks": chk, "min_pos": spec["skill"]["min_pos"], "n0": spec["skill"]["n0"],
           "top_frac": spec["skill"]["top_frac"], "sha256": sha256_file(path), "code_commit": git_commit(),
           "code_sha": reader_sha(), "note": "wallet hashes only (HMAC); never committed to the repository"}
    tmp = man_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(man, indent=1, sort_keys=True))
    os.link(tmp, man_path)
    tmp.unlink()
    return man


def freeze_checks(eligible: int, skilled: int, max_known_ts: float | None, expected: dict | None) -> dict:
    """Recorded in the freeze manifest. With the spec's ``skill.expected`` (eligible / skilled counts from the planning
    census, ``max_known_ts_before_utc``), any mismatch sets ``refuse`` (the freeze writes nothing)."""
    out: dict = {"eligible": eligible, "skilled": skilled, "max_known_ts": max_known_ts, "expected": expected, "mismatch": []}
    if expected:
        if "eligible" in expected and int(expected["eligible"]) != eligible:
            out["mismatch"].append("eligible")
        if "skilled" in expected and int(expected["skilled"]) != skilled:
            out["mismatch"].append("skilled")
        lim = expected.get("max_known_ts_before_utc")
        if lim and not (max_known_ts is not None and max_known_ts < epoch(lim)):
            out["mismatch"].append("max_known_ts")
    out["refuse"] = bool(out["mismatch"])
    return out


def load_skillset(out_dir: Path, pinned_sha: str | None) -> pd.DataFrame:
    path = Path(out_dir) / "skillset.csv.gz"
    got = sha256_file(path)
    if pinned_sha and got != pinned_sha:
        raise RuntimeError(f"skillset sha256 {got} != pinned {pinned_sha}")
    s = pd.read_csv(path, dtype={"wallet": str})
    s["skilled"] = s["skilled"].astype(str).str.lower().isin(["true", "1"])
    return s


# --- signals ----------------------------------------------------------------------------------------------------------


def first_trades(tr: pd.DataFrame) -> pd.DataFrame:
    """Earliest trade of each (wallet, market) in a batch (ties: first in input order)."""
    if not len(tr):
        return tr
    t = tr.reset_index(drop=True)
    t["_o"] = np.arange(len(t))
    t = t.sort_values(["ts", "_o"], kind="stable")
    return t.drop_duplicates(["wallet", "market_id"], keep="first").drop(columns="_o").reset_index(drop=True)


def prior_visible_flag(tr: pd.DataFrame) -> np.ndarray:
    """True for a row whose wallet has a strictly earlier trade in the same market among ``tr`` (the sample's raw rows,
    before the seen-before filter): an add / close rather than a first-seen open. Uses only trades at or before the row."""
    if not len(tr):
        return np.zeros(0, bool)
    first = tr.groupby(["wallet", "market_id"])["ts"].transform("min").to_numpy(float)
    return tr["ts"].to_numpy(float) > first


def signals_from_batch(tr: pd.DataFrame, *, arm: str, batch_id: str, skill: pd.DataFrame, t0: float,
                       signalled: set, used_controls: set, event_of: dict, spec: dict,
                       end_of: dict | None = None) -> pd.DataFrame:
    """Skilled copy signals and their matched controls from one batch of received taker trades.

    ``event_of`` / ``end_of``: market id -> event id / Gamma end time (epoch s) as known at the batch's origin (the
    sample's origin capture, or the print line's Gamma context); a missing end gives end bucket -1 (no controls).
    ``tr``: normalised trades (``wallet_skill.normalise_trades`` columns) plus ``receipt_ts`` and ``condition_id``, all
    with ``ts <= receipt_ts``; already restricted to trades not visible in an earlier batch of the same market (the
    caller's ``last_sent`` rule). ``signalled`` (skilled (wallet, market) keys of this arm) and ``used_controls``
    ((wallet, market) keys ever used as a control in this arm) are updated in place.
    """
    m = spec["matching"]
    out_cols = SIGNAL_COLS
    tr = tr[np.isfinite(tr["ts"].to_numpy(float)) & (tr["ts"].to_numpy(float) >= t0)
            & (tr["ts"].to_numpy(float) <= tr["receipt_ts"].to_numpy(float))]
    if not len(tr):
        return pd.DataFrame(columns=out_cols)
    ft = first_trades(tr)
    sk = skill.set_index("wallet")
    skilled_w = set(skill.loc[skill["skilled"], "wallet"])
    is_sk = ft["wallet"].isin(skilled_w).to_numpy()
    keys = list(zip(ft["wallet"], ft["market_id"].astype(np.int64), strict=True))
    new_sk = is_sk & np.array([k not in signalled for k in keys], bool)
    price = ft["price"].to_numpy(float)
    age = ft["receipt_ts"].to_numpy(float) - ft["ts"].to_numpy(float)
    pb = bucket(price, m["price_edges"])
    ab = bucket(age, m["age_edges_s"])
    end_of = end_of or {}
    end = np.array([float(end_of.get(int(x), math.nan)) for x in ft["market_id"].to_numpy(np.int64)], float)
    eb = bucket(end - ft["receipt_ts"].to_numpy(float), m["end_edges_s"])
    ev = np.array([str(event_of.get(int(x), "")) for x in ft["market_id"].to_numpy(np.int64)], dtype=object)
    ev = np.where(np.isin(ev, ["nan", "None"]), "", ev).astype(object)
    pv = ft["prior_visible"].to_numpy(bool) if "prior_visible" in ft else np.zeros(len(ft), bool)
    sig_id = np.array([signal_key(arm, w, mk, ts, d, k, p, s) for w, mk, ts, d, k, p, s in zip(
        ft["wallet"], ft["market_id"], ft["ts"], ft["d"], ft["k"], ft["price"], ft["size"], strict=True)], dtype=object)
    pool = np.flatnonzero(~is_sk & np.array([k not in used_controls for k in keys], bool) & (pb >= 0) & (ab >= 0)
                          & (eb >= 0))
    dd = ft["d"].to_numpy(int)
    mk_arr = ft["market_id"].to_numpy(np.int64)
    cells: dict[tuple, list[int]] = {}
    for j in pool:
        cells.setdefault((int(pb[j]), int(ab[j]), int(eb[j]), int(dd[j]), bool(pv[j])), []).append(int(j))
    rows: list[dict] = []

    def row(i: int, role: str, parent: str, n_ctrl: float) -> dict:
        d, k = int(ft["d"].iat[i]), int(ft["k"].iat[i])
        w = ft["wallet"].iat[i]
        return {"signal_id": sig_id[i], "arm": arm, "role": role, "parent_id": parent, "batch_id": batch_id,
                "market_id": int(ft["market_id"].iat[i]), "condition_id": ft["condition_id"].iat[i] if "condition_id" in ft else "",
                "event_id": ev[i], "wallet": w,
                "skill_score": float(sk["skill_score"].get(w, math.nan)) if w in sk.index else math.nan,
                "skill_n_pos": float(sk["n_pos"].get(w, math.nan)) if w in sk.index else math.nan,
                "trade_ts": float(ft["ts"].iat[i]), "side": d, "outcome_index": k, "trade_price": float(price[i]),
                "trade_size": float(ft["size"].iat[i]), "trade_notional": float(price[i] * ft["size"].iat[i]),
                "copy_token": k if d > 0 else 1 - k, "receipt_ts": float(ft["receipt_ts"].iat[i]), "age_s": float(age[i]),
                "price_bucket": int(pb[i]), "age_bucket": int(ab[i]), "end_ts_origin": float(end[i]),
                "end_bucket": int(eb[i]), "prior_visible": int(pv[i]), "n_controls": n_ctrl}

    taken: set[int] = set()
    for i in np.flatnonzero(new_sk):
        signalled.add(keys[i])
        if pb[i] < 0 or ab[i] < 0 or eb[i] < 0:
            rows.append(row(i, "skilled", "", 0.0))
            continue
        cand = [j for j in cells.get((int(pb[i]), int(ab[i]), int(eb[i]), int(dd[i]), bool(pv[i])), [])
                if j not in taken and mk_arr[j] != mk_arr[i] and ev[j] != "" and ev[j] != ev[i]]
        cand.sort(key=lambda j: _rank_key(sig_id[i], sig_id[j]))
        pick = cand[: int(m["n_controls"])]
        rows.append(row(i, "skilled", "", float(len(pick))))
        for j in pick:
            taken.add(j)
            used_controls.add(keys[j])
            rows.append(row(j, "control", sig_id[i], math.nan))
    return pd.DataFrame(rows, columns=[c for c in out_cols if c not in ("evidence_role", "spec_sha", "code_sha", "code_commit", "frozen_utc")])


def stamp(df: pd.DataFrame, spec: dict, commit: str, now: float, role_col: str | None = "receipt_ts") -> pd.DataFrame:
    df = df.copy()
    if role_col is not None:
        df["evidence_role"] = [role_of(t, spec) for t in df[role_col].to_numpy(float)] if len(df) else []
    df["spec_sha"] = spec["_sha256"][:16]
    df["code_sha"] = reader_sha()
    if role_col is not None:
        df["code_commit"] = commit
    df["frozen_utc"] = iso(now)
    return df


# --- trade sources ------------------------------------------------------------------------------------------------------


def sample_receipts(manifest: dict) -> dict[int, float]:
    """market_id -> receipt (``received_utc``) of the successful request of a trade sample (last 200 attempt)."""
    out: dict[int, float] = {}
    for r in manifest.get("requests") or []:
        if r.get("status") == 200:
            t = epoch(r.get("received_utc"))
            if math.isfinite(t):
                out[int(r["market_id"])] = t
    return out


def sample_sent(features: pd.DataFrame) -> dict[int, float]:
    """market_id -> request sent time of the ok rows (the sampler kept trades with ts <= sent)."""
    f = features[features["status"] == "ok"]
    t = pd.to_datetime(f["sent_utc"], utc=True, errors="coerce", format="ISO8601")
    v = t.astype("int64").to_numpy() / 1e9
    v[t.isna().to_numpy()] = np.nan
    return {int(m): float(x) for m, x in zip(f["market_id"].to_numpy(np.int64), v, strict=True) if np.isfinite(x)}


def load_sample_batch(sdir: Path, last_sent: dict[int, float]) -> tuple[pd.DataFrame, dict, dict]:
    """Normalised sidecar trades of one sample with receipt times, keeping only trades not visible in an earlier
    processed sample of the same market (``ts > last_sent[m]``). Returns (trades, new sent map, counts)."""
    sdir = Path(sdir)
    man = json.loads((sdir / "manifest.json").read_text())
    feats = pd.read_csv(sdir / "features.csv.gz", usecols=["market_id", "status", "sent_utc"])
    sent = sample_sent(feats)
    rec = sample_receipts(man)
    wman = json.loads((sdir / "wallets_manifest.json").read_text()) if (sdir / "wallets_manifest.json").exists() else {}
    counts = {"sidecar_status": wman.get("sidecar_status", "missing"), "rows": 0, "kept": 0, "seen_before": 0,
              "no_receipt": 0}
    if wman.get("sidecar_status") != "complete" or not (sdir / "wallets.csv.gz").exists():
        # no wallet was observed in this sample: it does not count as an observation (last_sent is not advanced), so a
        # later sample of the market is the first observation of these trades (with its own, later receipt)
        if not (sdir / "wallets.csv.gz").exists():
            counts["sidecar_status"] = f"{counts['sidecar_status']}|file_missing"
        return pd.DataFrame(), {}, counts
    raw = pd.read_csv(sdir / "wallets.csv.gz", usecols=["market_id", "condition_id", "ts", "side", "outcome_index", "size",
                                                        "price", "wallet_hash"], dtype={"wallet_hash": str, "condition_id": str})
    counts["rows"] = int(len(raw))
    cond = raw[["market_id", "condition_id"]].drop_duplicates("market_id").set_index("market_id")["condition_id"]
    tr = ws.normalise_trades(raw)
    del raw  # the sample is ~240k rows: free the raw frame before the receipt / flag columns are added
    tr["condition_id"] = cond.reindex(tr["market_id"].to_numpy()).to_numpy()
    tr["receipt_ts"] = tr["market_id"].map(rec).astype(float)
    tr["prior_visible"] = prior_visible_flag(tr)  # from the raw rows, BEFORE the seen-before filter
    nr = ~np.isfinite(tr["receipt_ts"].to_numpy(float))
    counts["no_receipt"] = int(nr.sum())
    prev = tr["market_id"].map(last_sent).fillna(-np.inf).to_numpy(float)
    seen = tr["ts"].to_numpy(float) <= prev
    counts["seen_before"] = int((seen & ~nr).sum())
    tr = tr[~nr & ~seen].reset_index(drop=True)
    counts["kept"] = int(len(tr))
    return tr, sent, counts


def load_print_batch(lines: list[dict]) -> pd.DataFrame:
    """>= $1k live prints (monitor lines) -> normalised trades with receipt = ``recv_ts`` (market from the line's Gamma
    context; prints without a market id are dropped and counted by the caller)."""
    if not lines:
        return pd.DataFrame()
    df = pd.DataFrame(lines)
    df = df[df.get("ctx_market_id").notna()] if "ctx_market_id" in df else df.iloc[0:0]
    if not len(df):
        return pd.DataFrame()
    raw = pd.DataFrame({"market_id": pd.to_numeric(df["ctx_market_id"], errors="coerce"), "ts": df["ts"], "side": df["side"],
                        "outcome_index": df["outcome_index"], "size": df["size"], "price": df["price"],
                        "wallet_hash": df["wallet_hash"]})
    ok = raw["market_id"].notna().to_numpy()
    raw, df = raw[ok], df[ok]
    keep = _valid_mask(raw)
    raw, df = raw[keep], df[keep]
    tr = ws.normalise_trades(raw)  # drops nothing more: same mask
    tr["condition_id"] = df["condition_id"].astype(str).to_numpy()
    tr["receipt_ts"] = pd.to_numeric(df["recv_ts"], errors="coerce").to_numpy(float)
    tr["prior_visible"] = prior_visible_flag(tr)
    tr["event_hint"] = df["ctx_event_id"].astype(str).to_numpy() if "ctx_event_id" in df else ""
    tr["end_hint"] = pd.to_numeric(df["ctx_end_ts"], errors="coerce").to_numpy(float) if "ctx_end_ts" in df else math.nan
    return tr.reset_index(drop=True)


def _valid_mask(df: pd.DataFrame) -> np.ndarray:
    """The row mask ``wallet_skill.normalise_trades`` applies (kept in step by a unit test)."""
    side = df["side"].astype(str).str.upper()
    d = np.where(side == "BUY", 1, np.where(side == "SELL", -1, 0))
    k = pd.to_numeric(df["outcome_index"], errors="coerce").to_numpy(float)
    p = pd.to_numeric(df["price"], errors="coerce").to_numpy(float)
    s = pd.to_numeric(df["size"], errors="coerce").to_numpy(float)
    ts = pd.to_numeric(df["ts"], errors="coerce").to_numpy(float)
    with np.errstate(invalid="ignore"):
        return (d != 0) & np.isin(k, (0.0, 1.0)) & (p > 0) & (p < 1) & (s > 0) & np.isfinite(ts) & df["wallet_hash"].notna().to_numpy()


def read_print_lines(root: Path, lo: float, hi: float) -> list[dict]:
    """Monitor print lines with ``lo <= recv_ts < hi`` (files of the UTC days touching the interval)."""
    out: list[dict] = []
    days = {datetime.fromtimestamp(t, UTC).strftime("%Y%m%d") for t in (lo, hi - 1e-6, hi + 3600)}
    for day in sorted(days):
        p = Path(root) / f"trades-{day}.jsonl"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if '"recv_ts"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                t = r.get("recv_ts")
                if isinstance(t, (int, float)) and lo <= t < hi:
                    out.append(r)
    return out


# --- captures and entries ---------------------------------------------------------------------------------------------


def scan_captures(snapshot_root: Path, lo: float) -> list[dict]:
    """Complete captures with start >= lo, in start order (manifest ``state=complete`` and rows present)."""
    caps = []
    for p in sorted(Path(snapshot_root).glob("*/manifest.json")):
        try:
            started = epoch(datetime.strptime(p.parent.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat())
        except ValueError:
            continue
        if not math.isfinite(started) or started < lo - 3600:
            continue
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        t = epoch(m.get("started_utc"))
        if m.get("state") != "complete" or not (p.parent / "rows.csv.gz").exists() or not math.isfinite(t) or t < lo:
            continue
        caps.append({"id": p.parent.name, "start": t, "dir": p.parent})
    return sorted(caps, key=lambda c: c["start"])


def scan_samples(sample_root: Path, lo: float, hi: float) -> list[dict]:
    """Active-frame trade samples with start in [lo, hi), in start order, with their manifest state."""
    out = []
    for p in sorted(Path(sample_root).glob("*/manifest.json")):
        try:
            started = datetime.strptime(p.parent.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
        except ValueError:
            continue
        if not (lo <= started < hi):
            continue
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            m = {}
        out.append({"id": p.parent.name, "start": started, "dir": p.parent, "state": m.get("state"),
                    "frame": m.get("frame"), "snapshot_id": m.get("snapshot_id")})
    return sorted(out, key=lambda s: s["start"])


def _fee_rate(fs: object) -> tuple[float, float]:
    try:
        d = json.loads(str(fs))
        return float(d.get("rate", math.nan)), float(d.get("exponent", 1.0) or 1.0)
    except (TypeError, ValueError, AttributeError):
        return math.nan, 1.0


def load_capture(cap_dir: Path, market_ids: Iterable[int]) -> pd.DataFrame:
    """Rows of a capture for the given markets (first row per market id) with fee fields from ``rows_ext``."""
    ids = {int(x) for x in market_ids}
    rows = pd.read_csv(Path(cap_dir) / "rows.csv.gz", usecols=SNAP_COLS, dtype={"condition_id": str, "event_id": str,
                       "received_utc": str, "capture_start_utc": str, "end_date": str, "closed": str, "active": str})
    rows = rows[rows["market_id"].isin(ids)].drop_duplicates("market_id").set_index("market_id")
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if p.exists() and len(rows):
        ext = pd.read_csv(p, usecols=EXT_COLS, dtype={c: str for c in EXT_COLS[1:]})
        ext = ext[ext["market_id"].isin(ids)].drop_duplicates("market_id").set_index("market_id")
    else:
        ext = pd.DataFrame(index=pd.Index([], name="market_id"), columns=EXT_COLS[1:])
    rows = rows.join(ext, how="left")
    return rows


def quote_status(closed, active, bid, ask) -> str:
    if str(closed).strip().lower() in ("true", "1") or str(active).strip().lower() in ("false", "0"):
        return "closed_flag"
    b, a = float(bid) if bid == bid else math.nan, float(ask) if ask == ask else math.nan
    if math.isfinite(b) and math.isfinite(a) and 0.0 < b < a < 1.0:
        return "two_sided"
    return "one_sided"


def entries_for_capture(cap: dict, rows: pd.DataFrame, pending: pd.DataFrame) -> pd.DataFrame:
    """Entry / exit lines of ``pending`` items (signal_id, kind, latency_s, due_ts, market_id) whose due time is at or
    before the capture start: the capture's row for the market (``absent`` if the market is not in the capture)."""
    p = pending[pending["due_ts"].to_numpy(float) <= cap["start"]]
    out = []
    for r in p.itertuples(index=False):
        mid = int(r.market_id)
        base = {"signal_id": r.signal_id, "kind": r.kind, "latency_s": float(r.latency_s), "due_ts": float(r.due_ts),
                "capture_id": cap["id"], "capture_start_ts": float(cap["start"])}
        if mid not in rows.index:
            out.append({**base, "status": "absent"})
            continue
        x = rows.loc[mid]
        rate, expo = _fee_rate(x.get("fee_schedule"))
        out.append({**base, "row_received_ts": epoch(x["received_utc"]),
                    "status": quote_status(x["closed"], x["active"], x["best_bid"], x["best_ask"]),
                    "best_bid": x["best_bid"], "best_ask": x["best_ask"], "spread": x["spread"],
                    "last_trade_price": x["last_trade_price"], "liquidity": x["liquidity"], "volume24hr": x["volume24hr"],
                    "end_ts": epoch(x["end_date"]), "event_id": x["event_id"], "fee_category": x.get("fee_category"),
                    "fees_enabled": x.get("fees_enabled"), "fee_schedule_rate": rate, "fee_exponent": expo})
    return pd.DataFrame(out, columns=[c for c in ENTRY_COLS if c not in ("spec_sha", "code_sha", "frozen_utc")])


def pending_items(signals: pd.DataFrame, entries: pd.DataFrame, latencies: Iterable[float], exit_h: float,
                  primary_l: float) -> pd.DataFrame:
    """Entries not yet recorded (every signal x latency) plus fixed-horizon exits of recorded two-sided primary entries.

    Only the pending rows are ever materialised (per latency: signals without that entry; exits: recorded two-sided
    primary entries without an exit), so the pass memory stays flat as the stores grow."""
    cols = ["signal_id", "kind", "latency_s", "due_ts", "market_id"]
    if not len(signals):
        return pd.DataFrame(columns=cols)
    lat = [float(x) for x in latencies]
    s = signals[["signal_id", "market_id", "receipt_ts"]].drop_duplicates("signal_id")
    have = len(entries) > 0
    if have:
        e_lat = entries["latency_s"].astype(float).to_numpy()
        is_entry, is_exit = (entries["kind"] == "entry").to_numpy(), (entries["kind"] == "exit").to_numpy()
    parts = []
    for L in lat:
        miss = s if not have else s[~s["signal_id"].isin(entries["signal_id"][is_entry & (e_lat == L)])]
        parts.append(pd.DataFrame({"signal_id": miss["signal_id"].to_numpy(), "kind": "entry", "latency_s": L,
                                   "due_ts": miss["receipt_ts"].to_numpy(float) + L, "market_id": miss["market_id"].to_numpy()}))
    if have:
        pm = is_entry & (e_lat == float(primary_l)) & (entries["status"] == "two_sided").to_numpy()
        pe = entries[pm]
        pe = pe[~pe["signal_id"].isin(entries["signal_id"][is_exit & (e_lat == float(primary_l))])]
        if len(pe):
            mk = s.set_index("signal_id")["market_id"]
            parts.append(pd.DataFrame({"signal_id": pe["signal_id"].to_numpy(), "kind": "exit", "latency_s": float(primary_l),
                                       "due_ts": pe["row_received_ts"].to_numpy(float) + exit_h,
                                       "market_id": mk.reindex(pe["signal_id"].to_numpy()).to_numpy()}))
    parts = [x for x in parts if len(x)]
    return pd.concat(parts, ignore_index=True)[cols] if parts else pd.DataFrame(columns=cols)


# --- stores -------------------------------------------------------------------------------------------------------------


def read_store(root: Path, sub: str, usecols: list[str] | None = None) -> pd.DataFrame:
    """All write-once files of a store, concatenated; ``usecols`` keeps the recorder's memory flat as the store grows."""
    files = sorted((Path(root) / sub).glob("*.csv.gz"))
    want = None if usecols is None else set(usecols)
    frames = [pd.read_csv(f, dtype={"wallet": str, "event_id": str, "condition_id": str, "signal_id": str,
                                    "parent_id": str, "capture_id": str, "batch_id": str, "fee_category": str,
                                    "spec_sha": str, "code_sha": str, "code_commit": str, "state": str, "uma_status": str},
                          float_precision="round_trip", usecols=None if want is None else (lambda c: c in want))
              for f in files if f.stat().st_size > 0]
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


class State:
    """Cache only (``state.json``): the per-market last sent time of processed samples and the labeller's recheck times.
    The write-once files (signals, missing markers, entries) are the ground truth; ``last_sent`` is rebuilt from the
    processed samples still on disk if the cache is lost (``rebuild_last_sent``)."""

    def __init__(self, root: Path) -> None:
        self.path = Path(root) / "state.json"
        self.d = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.d.setdefault("last_sent", {})
        self.d.setdefault("label_checked", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, sort_keys=True))
        os.replace(tmp, self.path)


def _batch_done(root: Path, batch: str) -> bool:
    """A batch is done once its write-once signals file or its write-once missing marker exists."""
    d = Path(root) / "signals"
    return (d / f"{batch}.csv.gz").exists() or (d / f"{batch}.missing.json").exists()


def mark_missing(root: Path, batch: str, reason: str, now: float) -> bool:
    """Write-once marker of a batch that is never read (not complete, wrong frame, files retired). Ground truth on
    disk (not in the state cache), so a lost cache can never let a late batch be read out of order."""
    path = Path(root) / "signals" / f"{batch}.missing.json"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"batch": batch, "reason": reason, "at": iso(now)}, sort_keys=True))
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def rebuild_last_sent(root: Path, sample_root: Path, t0: float, t_end: float) -> dict[int, float]:
    """``last_sent`` from the processed samples still on disk (used only if the state cache was lost). Samples whose
    features file was already retired cannot contribute; the caller logs the rebuild."""
    out: dict[int, float] = {}
    for s in scan_samples(sample_root, t0, t_end):
        if not (Path(root) / "signals" / f"{s['id']}.csv.gz").exists() or not (s["dir"] / "features.csv.gz").exists():
            continue
        feats = pd.read_csv(s["dir"] / "features.csv.gz", usecols=["market_id", "status", "sent_utc"])
        for mk, t in sample_sent(feats).items():
            out[mk] = max(out.get(mk, -math.inf), t)
    return out


# --- the recorder pass --------------------------------------------------------------------------------------------------


def run_once(*, root: Path = OUT_ROOT, snapshot_root: Path = SNAPSHOT_ROOT, sample_root: Path = SAMPLE_ROOT,
             prints_root: Path = LIVE_TRADES_ROOT, spec: dict | None = None, now: float | None = None,
             max_items: int = 40, log: Callable[[str], None] = print, capture_hi: float = math.inf,
             exits: bool = True) -> dict:
    """One recorder pass (locked). Exit-code semantics for the runner: returns stats with ``tempfail`` when nothing is
    new or the skill set is absent, and ``closed`` once the window and every pending entry/exit are done.

    ``capture_hi`` and ``exits`` exist for the pre-window planning census only: no capture starting at or after
    ``capture_hi`` is opened, and with ``exits=False`` no fixed-horizon exit quote is recorded (entries only). The
    registered recorder uses the defaults."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / ".lock", "w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return {"tempfail": True, "reason": "locked"}
        return _run_locked(root=root, snapshot_root=snapshot_root, sample_root=sample_root, prints_root=prints_root,
                           spec=spec or load_spec(), now=now if now is not None else now_ts(), max_items=max_items, log=log,
                           capture_hi=capture_hi, exits=exits)


def _run_locked(*, root: Path, snapshot_root: Path, sample_root: Path, prints_root: Path, spec: dict, now: float,
                max_items: int, log, capture_hi: float = math.inf, exits: bool = True) -> dict:
    stats: dict = {"started": iso(now), "samples": 0, "print_hours": 0, "captures": 0, "signals_skilled": 0,
                   "signals_control": 0, "entries": 0, "skipped_samples": 0}
    if dir_bytes(root) > DISK_CAP_BYTES:
        log(f"COPY_SKILLED disk cap reached ({dir_bytes(root)} bytes); nothing written")
        return {**stats, "tempfail": True, "reason": "disk_cap"}
    skdir = root / "skillset"
    if not (skdir / "skillset.csv.gz").exists():
        log("COPY_SKILLED skill set not frozen yet; nothing to do")
        return {**stats, "tempfail": True, "reason": "no_skillset"}
    skill = load_skillset(skdir, spec.get("skillset_sha256"))
    st = State(root)
    t0 = epoch(spec["registered_utc"])
    t_end = epoch(spec["end_utc"])
    commit = git_commit()
    lat = [float(x) for x in spec["latencies_s"]]
    exit_h = float(spec["exit_horizon_s"])
    work = 0
    # 1. sidecar batches, strictly in start order; an in-progress sample blocks later ones
    signals_all = read_store(root, "signals", ["arm", "role", "wallet", "market_id"])
    sig_keys = {a: set() for a in ARMS}
    ctl_keys = {a: set() for a in ARMS}
    if len(signals_all):
        for a, r, w, mk in zip(signals_all["arm"], signals_all["role"], signals_all["wallet"],
                               signals_all["market_id"].astype(np.int64), strict=True):
            (sig_keys if r == "skilled" else ctl_keys)[a].add((w, int(mk)))
    if not st.path.exists() and any((root / "signals").glob("*.csv.gz")):
        st.d["last_sent"] = {str(k): v for k, v in rebuild_last_sent(root, sample_root, t0, t_end).items()}
        append_jsonl(root / "passes.jsonl", [{"kind": "state_rebuilt", "markets": len(st.d["last_sent"]), "at": iso(now)}])
    last_sent = {int(k): float(v) for k, v in st.d["last_sent"].items()}
    for s in scan_samples(sample_root, t0, t_end):
        if work >= max_items:
            break
        if _batch_done(root, s["id"]):
            continue
        if s["state"] != "complete":
            if now - s["start"] < IN_PROGRESS_GRACE_S:
                break  # still running: later samples wait (order matters for first observation)
            reason = f"state={s['state']}"
        elif s["frame"] != "active":
            reason = f"frame={s['frame']}"
        elif not (s["dir"] / "features.csv.gz").exists():
            # retired by the 3-day trade-sample retention before it was read (recorder outage): missing stays missing
            reason = "files_retired"
        else:
            reason = ""
        if reason:
            mark_missing(root, s["id"], reason, now)
            if not reason.startswith("frame="):
                stats["skipped_samples"] += 1
                append_jsonl(root / "passes.jsonl", [{"kind": "sample_missing", "id": s["id"], "reason": reason,
                                                      "at": iso(now)}])
            continue
        tr, sent, cnt = load_sample_batch(s["dir"], last_sent)
        event_of, end_of = _event_map(snapshot_root / str(s["snapshot_id"]), tr["market_id"].unique() if len(tr) else [])
        sig = signals_from_batch(tr, arm="sidecar", batch_id=s["id"], skill=skill, t0=t0, signalled=sig_keys["sidecar"],
                                 used_controls=ctl_keys["sidecar"], event_of=event_of, spec=spec, end_of=end_of) if len(tr) else \
            pd.DataFrame(columns=SIGNAL_COLS[:-5])
        write_once_csv(root / "signals" / f"{s['id']}.csv.gz", stamp(sig, spec, commit, now))
        for mk, t in sent.items():
            last_sent[mk] = max(last_sent.get(mk, -math.inf), t)
        st.d["last_sent"] = {str(k): v for k, v in last_sent.items()}
        st.save()
        append_jsonl(root / "passes.jsonl", [{"kind": "sample", "id": s["id"], "counts": cnt, "skilled": int((sig["role"] == "skilled").sum()) if len(sig) else 0,
                                              "controls": int((sig["role"] == "control").sum()) if len(sig) else 0, "at": iso(now)}])
        stats["samples"] += 1
        stats["signals_skilled"] += int((sig["role"] == "skilled").sum()) if len(sig) else 0
        stats["signals_control"] += int((sig["role"] == "control").sum()) if len(sig) else 0
        work += 1
    # 2. large-print hours (complete hours only, 10 min grace for the monitor's writes)
    h = math.floor(t0 / 3600) * 3600
    while h + 3600 + 600 <= now and h < t_end and work < max_items:
        bid = "lp_" + datetime.fromtimestamp(h, UTC).strftime("%Y%m%dT%H")
        if not _batch_done(root, bid):
            lines = read_print_lines(prints_root, h, h + 3600)
            tr = load_print_batch(lines)
            ev = {int(m): e for m, e in zip(tr.get("market_id", []), tr.get("event_hint", []), strict=False)} if len(tr) else {}
            en = {int(m): e for m, e in zip(tr.get("market_id", []), tr.get("end_hint", []), strict=False)} if len(tr) else {}
            sig = signals_from_batch(tr, arm="large_prints", batch_id=bid, skill=skill, t0=t0,
                                     signalled=sig_keys["large_prints"], used_controls=ctl_keys["large_prints"],
                                     event_of=ev, spec=spec, end_of=en) if len(tr) else pd.DataFrame(columns=SIGNAL_COLS[:-5])
            write_once_csv(root / "signals" / f"{bid}.csv.gz", stamp(sig, spec, commit, now))
            append_jsonl(root / "passes.jsonl", [{"kind": "prints", "id": bid, "lines": len(lines), "trades": int(len(tr)),
                                                  "skilled": int((sig["role"] == "skilled").sum()) if len(sig) else 0, "at": iso(now)}])
            stats["print_hours"] += 1
            work += 1
        h += 3600
    # 3. entries / exits per complete capture, in order, once every batch that could feed it is processed
    signals_all = sig_keys = ctl_keys = None  # release the step-1 key sets before the (larger) step-3 reads
    signals_all = read_store(root, "signals", ["signal_id", "market_id", "receipt_ts"])
    entries = read_store(root, "entries", ["signal_id", "kind", "latency_s", "status", "row_received_ts"])
    blocked_from = _first_unprocessed_batch(root, sample_root, t0, t_end, now, st)
    pend = pending_items(signals_all, entries, lat, exit_h, float(spec["primary_latency_s"]))
    signals_all = entries = None  # the pending list is maintained incrementally below (flat memory per capture)
    if not exits and len(pend):
        pend = pend[pend["kind"] == "entry"]
    primary_l = float(spec["primary_latency_s"])
    for cap in scan_captures(snapshot_root, t0):
        if work >= max_items:
            break
        if (root / "entries" / f"{cap['id']}.csv.gz").exists():
            continue
        if cap["start"] >= blocked_from or cap["start"] >= capture_hi:
            break
        is_due = pend["due_ts"].to_numpy(float) <= cap["start"] if len(pend) else np.zeros(0, bool)
        due = pend[is_due] if len(pend) else pend
        rows = load_capture(cap["dir"], due["market_id"].unique()) if len(due) else pd.DataFrame()
        ent = entries_for_capture(cap, rows, due) if len(due) else pd.DataFrame(columns=ENTRY_COLS[:-3])
        write_once_csv(root / "entries" / f"{cap['id']}.csv.gz", stamp(ent, spec, commit, now, role_col=None))
        if len(ent):  # every due item got a line: it leaves the pending list; a two-sided primary entry adds its exit
            pend = pend[~is_due]
            if exits:
                pe = ent[(ent["kind"] == "entry") & (ent["latency_s"].astype(float) == primary_l) & (ent["status"] == "two_sided")]
                if len(pe):
                    mk = due.drop_duplicates("signal_id").set_index("signal_id")["market_id"]
                    pend = pd.concat([pend, pd.DataFrame({
                        "signal_id": pe["signal_id"].to_numpy(), "kind": "exit", "latency_s": primary_l,
                        "due_ts": pe["row_received_ts"].to_numpy(float) + exit_h,
                        "market_id": mk.reindex(pe["signal_id"].to_numpy()).to_numpy()})], ignore_index=True)
        stats["captures"] += 1
        stats["entries"] += int(len(ent))
        work += 1
    st.save()
    closed = now >= t_end + max(lat) + exit_h + 6 * 3600 and len(pend) == 0
    stats["pending"] = int(len(pend))
    stats["closed"] = bool(closed)
    append_jsonl(root / "passes.jsonl", [{"kind": "pass", **stats, "at": iso(now)}])
    if closed:
        log("COPY_SKILLED_WINDOW_CLOSED")
    if work == 0 and not closed:
        stats["tempfail"] = True
    log(json.dumps(stats, sort_keys=True))
    return stats


def _event_map(cap_dir: Path, market_ids) -> tuple[dict, dict]:
    """(market_id -> event_id, market_id -> Gamma end time) from the sample's origin capture (empty if absent)."""
    p = Path(cap_dir) / "rows.csv.gz"
    ids = {int(x) for x in market_ids}
    if not ids or not p.exists():
        return {}, {}
    r = pd.read_csv(p, usecols=["market_id", "event_id", "end_date"], dtype={"event_id": str, "end_date": str})
    r = r[r["market_id"].isin(ids)].drop_duplicates("market_id")
    mk = r["market_id"].astype(int).to_numpy()
    end = [epoch(x) for x in r["end_date"].to_numpy()]
    return dict(zip(mk, r["event_id"].fillna(""), strict=True)), dict(zip(mk, end, strict=True))


def _first_unprocessed_batch(root: Path, sample_root: Path, t0: float, t_end: float, now: float, st: State) -> float:
    """Start time of the earliest batch that could still create a signal with receipt before a capture start: the
    earliest unprocessed in-window sample, and the earliest unprocessed large-print hour (its start)."""
    b = math.inf
    for s in scan_samples(sample_root, t0, t_end):
        if not _batch_done(root, s["id"]):
            b = min(b, s["start"])
            break
    h = math.floor(t0 / 3600) * 3600
    while h < min(t_end, now):
        bid = "lp_" + datetime.fromtimestamp(h, UTC).strftime("%Y%m%dT%H")
        if not _batch_done(root, bid):
            b = min(b, h)
            break
        h += 3600
    return b


# --- resolution labeller (network; read-only public GET) ---------------------------------------------------------------

GAMMA = "https://gamma-api.polymarket.com"
Transport = Callable[[str, list], tuple[int, object]]


def httpx_transport(timeout: float = 30.0) -> Transport:
    import httpx

    client = httpx.Client(timeout=timeout, headers={"User-Agent": "arepo-research-lab/1", "Accept-Encoding": "gzip"})

    def get(url: str, params: list) -> tuple[int, object]:
        r = client.get(url, params=params)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None

    return get


def resolution_rows(body: object, asked: Iterable[int], fetched: float, code: int) -> list[dict]:
    """One row per asked market: final payouts (``wallet_skill.payouts_from_prices``) or a non-final state."""
    by_id = {}
    if isinstance(body, list):
        for m in body:
            try:
                by_id[int(m.get("id"))] = m
            except (TypeError, ValueError, AttributeError):
                continue
    out = []
    for mid in asked:
        m = by_id.get(int(mid))
        if m is None:
            out.append({"market_id": int(mid), "fetched_ts": fetched, "http_status": code, "state": "missing"})
            continue
        closed = bool(m.get("closed"))
        pay = ws.payouts_from_prices(m.get("outcomePrices")) if closed else None
        state = "open" if not closed else ("resolved" if pay is not None and pay[0] in (0.0, 1.0) else
                                           "split_50_50" if pay is not None else "closed_not_final")
        out.append({"market_id": int(mid), "fetched_ts": fetched, "http_status": code, "closed": closed,
                    "outcome_prices": str(m.get("outcomePrices")), "pay0": pay[0] if pay else math.nan, "state": state,
                    "uma_status": str(m.get("umaResolutionStatus") or "")})
    return out


def label_resolutions(*, root: Path = OUT_ROOT, spec: dict | None = None, transport: Transport | None = None,
                      now: float | None = None, batch: int = 20, max_requests: int = 600, delay_s: float = 1.0,
                      recheck_s: float = 20 * 3600, sleep: Callable[[float], None] = time.sleep,
                      log: Callable[[str], None] = print) -> dict:
    """Fetch Gamma records for signal markets without a final record (each market at most once per ``recheck_s``).
    Only rows with a final state are written (``resolutions/<pass>.csv.gz``, write-once). Stops after the cutoff."""
    spec = spec or load_spec()
    now = now_ts() if now is None else now
    root = Path(root)
    if now >= epoch(spec["label_cutoff_utc"]) + 86400:
        log("COPY_SKILLED_LABELS_CLOSED")
        return {"closed": True}
    sig = read_store(root, "signals", ["signal_id", "market_id"])
    if not len(sig):
        return {"tempfail": True, "reason": "no_signals"}
    res = read_store(root, "resolutions", ["market_id", "state"])
    final = set(res.loc[res["state"].isin(["resolved", "split_50_50"]), "market_id"].astype(int)) if len(res) else set()
    st = State(root)
    chk = st.d["label_checked"]
    todo = sorted({int(x) for x in sig["market_id"].astype(np.int64)} - final)
    todo = [m for m in todo if now - float(chk.get(str(m), -math.inf)) >= recheck_s]
    n_due = len(todo)
    # Until 7 days before the label cutoff, markets whose latest recorded Gamma end date is more than a day ahead are not
    # asked yet (load control; a market with no recorded end date is asked); markets past their end date go first. The
    # gate cannot change a label (it only delays a request), and it is OFF from cutoff - 7 d so that a later end-date
    # extension can never hold an early-resolved market back past the cutoff: every due market is then asked.
    gate_on = now < epoch(spec["label_cutoff_utc"]) - 7 * 86400
    end_of: dict[int, float] = {}
    ent = read_store(root, "entries", ["signal_id", "end_ts"])  # end dates also order the requests (past-end first)
    if len(ent) and "end_ts" in ent:
        mk = ent["signal_id"].map(sig.drop_duplicates("signal_id").set_index("signal_id")["market_id"])
        end_of = {int(k): float(v) for k, v in ent["end_ts"].astype(float).groupby(mk).max().dropna().items()}
    del ent
    n_gated = 0
    if gate_on:
        kept = [m for m in todo if end_of.get(m, -math.inf) <= now + 86400]
        n_gated = len(todo) - len(kept)
        todo = kept
    todo.sort(key=lambda m: (end_of.get(m, now), m))
    get = transport or httpx_transport()
    rows, n_req = [], 0
    wall0 = time.time()
    for i in range(0, len(todo), batch):
        if n_req >= max_requests:
            break
        ids = todo[i:i + batch]
        # closed=true is required: Gamma /markets defaults to open markets only, so an id list without it never returns a
        # resolved market (found in the 2026-10-21 host dry run). An open market is simply absent from the reply.
        params = [("id", str(x)) for x in ids] + [("closed", "true"), ("limit", str(len(ids)))]
        try:
            code, body = get(f"{GAMMA}/markets", params)
        except Exception as exc:  # network failure: retried next pass
            log(f"label request failed ({type(exc).__name__})")
            code, body = 0, None
        n_req += 1
        t = now + (time.time() - wall0)  # the pass clock (= wall clock in a live pass)
        if code == 200:
            rr = resolution_rows(body, ids, t, code)
            rows += [r for r in rr if r["state"] in ("resolved", "split_50_50")]
            for x in ids:
                chk[str(x)] = t
        sleep(delay_s)
    st.save()
    if rows:
        df = pd.DataFrame(rows).reindex(columns=RES_COLS[:-2])
        df["spec_sha"] = spec["_sha256"][:16]
        df["code_sha"] = reader_sha()
        write_once_csv(root / "resolutions" / f"{datetime.fromtimestamp(now, UTC).strftime('%Y%m%dT%H%M%S')}.csv.gz", df)
    asked = min(len(todo), n_req * batch)
    out = {"asked": asked, "requests": n_req, "final_new": len(rows), "final_total": len(final) + len(rows),
           "due": n_due, "gated": n_gated, "due_unasked": n_due - asked, "gate_on": bool(gate_on)}
    append_jsonl(root / "passes.jsonl", [{"kind": "label_pass", **out, "at": iso(now)}])
    log(json.dumps(out))
    return out


def sample_coverage(root: Path, t0: float, t1: float, cadence_s: float = 7200.0) -> dict:
    """Trade-sample coverage of the window from ``passes.jsonl``: samples read with a complete wallet sidecar vs samples
    missing (not complete, retired before reading, or sidecar incomplete). Expected = window / cadence (2 h)."""
    ok, bad = set(), set()
    p = Path(root) / "passes.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            sid = str(r.get("id", ""))
            try:
                t = datetime.strptime(sid[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
            except ValueError:
                continue
            if not (t0 <= t < t1):
                continue
            if r.get("kind") == "sample" and (r.get("counts") or {}).get("sidecar_status") == "complete":
                ok.add(sid)
            elif r.get("kind") in ("sample", "sample_missing"):
                bad.add(sid)
    expected = (t1 - t0) / cadence_s
    n_ok = len(ok)
    return {"samples_ok": n_ok, "samples_missing": len(bad - ok), "expected": expected,
            "missing_share": float(max(0.0, 1.0 - n_ok / max(expected, n_ok + len(bad - ok), 1.0)))}


def gz_lines(path: Path) -> int:
    with gzip.open(path, "rt") as fh:
        return sum(1 for _ in fh) - 1
