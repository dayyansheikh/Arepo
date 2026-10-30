# ruff: noqa: E501
"""CB8-W analysis side (docs/research_lab/CREATIVE_BATCH_8.md 2.3-2.7, CB8-W "Definitions" .. "Stop rule", 4, 5.1): the W part of the pre-freeze census
(q0169), the W1 Stage-1 screen on SCREEN events (q0171) and W1-rep on the sealed HOLDOUT events (q0175).

EXPLORATORY HISTORICAL ANALYSIS ONLY: no edge, calibration or profitability claim; every mark-out is a paper resting-maker rule at recorded print prices.
Access rules:
- Every stage first verifies the committed seal copy ``seals/h9_flow_SEAL.json`` (byte-equal to the run's ``SEAL.json``, committed, its file table and
  declaration hashes intact, the flow rules hash and the pinned wallet-key fingerprint), then re-hashes the files it reads against the seal. HOLDOUT
  files (``holdout/``) are not re-hashed, listed or opened before ``replicate`` unlocks them; the census counts HOLDOUT files from the seal listing (names
  only) and HOLDOUT events from ``sample.csv.gz`` (ids only).
- The census never computes a mark: :class:`MarkIndex` built for the purpose ``census`` holds counts only (no price sums) and refuses ``values``. No
  mark-out, W1 or route-gate value is computed by the census.
- Mark values (the target) are computed only for the purposes ``screen`` and ``replicate``. ``replicate`` refuses unless the committed Stage-1 copy shows W1
  advanced, and verifies the HOLDOUT listing sha256 against the seal BEFORE any HOLDOUT read. Reads are appended to the run's ``ACCESS_LOG.jsonl``.
- Seal-time ``DROPPED_*`` markets (``drops.csv.gz``) are removed by id from every count and estimate.

The rules of this module are hashed into ``seals/cb8_w_analysis_rules.json`` (``cb8-w-analysis-rules-v1``); the W data rules (``seals/cb8_flow_rules.json``)
are untouched. Readings taken where the design is silent are in ``INTERPRETATIONS`` (written into every output).
"""

from __future__ import annotations

import bisect
import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import cb8_b_analysis as ba
from . import cb8_common as cm
from . import cb8_flow as F
from . import cb8_wh_common as wc
from . import economics, h5_seal

RULES_VERSION = "cb8-w-analysis-rules-v1"
RULES_FILE = cm.SEALS_DIR / "cb8_w_analysis_rules.json"
WALLET_KEY_FP = "80ce5e81a539a570"  # pinned in seals/cb8_flow_rules.json (and every CB8 manifest)
TEST = "W1"
FAMILY = "W"
RULES_KEY = "w_analysis_rules_sha256"
DATA_KEY = "w_data_rules_sha256"
STAGE1_COPY_NAME = "cb8_w1_stage1.json"
CENSUS_NAME, RESULTS_S1, RESULTS_S2 = "census_W.json", "results_W1.json", "results_W1_rep.json"
RUN_ID = F.RUN_ID
SEAL_COPY_NAME = f"{F.RUN_ID}_SEAL.json"
SIGN = -1  # W1 < 0: the skipped same-side fills lose for the resting maker

# ---- declared values (CREATIVE_BATCH_8.md CB8-W, 2.1, 2.6) -------------------------------------------------------------------------------------------
CLIP_GAP_S = 2
TRIG_GAP_S = (20, 600)
SIZE_RATIO = (0.5, 2.0)
MIN_NOTIONAL = 50.0
RUN_START_S = 600
OPP_LOOKBACK_S = 1800
LAG_S, LAG_ROBUST_S = 60, 300
BASE_S, CAP_S = 600, 3600
USABLE = (0.03, 0.97)
MARK_HALF_S = 900
HORIZON_S = 7200
ALT_HORIZONS_S = (3600, 10800)
REPORT_HORIZON_S = 3600
UNIT_WINDOW_S = int(F.WINDOW_H * cm.HOUR)
REBATE_FROM = "2026-03-30T00:00:00Z"
SEED_TIMESHIFT = 8182
SHIFT_RANGE_S = (6 * 3600, 66 * 3600)
GW_MIN_S_MARKED, GW_MIN_WINDOWS, GW_MIN_EVENTS, GW_MIN_DAYS, GW_MIN_WALLETS = 2000, 300, 30, 30, 30
MONTH_MIN_UNITS = 500
CONTINUATION_S = 600
SEQ_MIN_CLIPS, SEQ_CV_MAX = 4, 0.5
REVERSAL_FROM_S, REVERSAL_TO_S = 900, 7200
STRATUM_GAP_DAYS = 14.0
MDE_SE_REF, MDE_G_REF = 0.0015, 500  # design MDE: SE about 0.15c at about 500 events (event, day and wallet ways)

INTERPRETATIONS = (
    "Clip: prints of one wallet hash on one YES side of one market chained while consecutive prints are <= 2 s apart; size summed, VWAP YES price, "
    "notional = sum(size x token price) (the dollars traded). A clip's time is its LAST print (the clip and its size are complete only then). Prints without a "
    "wallet hash never form clips (they still count as prints, units and mark inputs).",
    "Trigger: clip c2 of wallet w with some same-side clip c1 of w satisfying every declared rule; one trigger per c2 (the latest qualifying c1 is recorded). "
    "Every qualifying c2 is a trigger (a run of clips yields several overlapping windows, merged).",
    "Skip window [tau, e): tau = t(c2) + 60 s; e starts at tau + 600 s and each further same-side clip of w with t(c2) < t_k < e moves e to max(e, t_k + 600), "
    "capped at tau + 3,600 s. Overlapping same-side windows merge (half-open; touching windows stay separate); a merged window carries the union of its trigger wallets.",
    "Availability (capped / failed / missing days and the window edges): a print at s is a usable UNIT only if [s - reach, s] lies in the fetched window with "
    "no unavailable day, reach = 1,800 + 600 + lag + 3,600 s (6,060 s at lag 60; 6,300 s at lag 300). Any trigger whose window could cover s is then fully "
    "observable (exact S / S' / N classification), and a trigger whose look-back is not observable can only cover unavailable units.",
    "Units are restricted to the declared 72-h window [w0, w0 + 72 h) and YES price in [0.03, 0.97]; prints in (w0 + 72 h, w0 + 74.5 h) serve marks only. A print "
    "inside windows of both sides is excluded (counted).",
    "Mark M(u): (ask-side VWAP + bid-side VWAP) / 2 of all prints in [u - 900, u + 900] (any price), ask side = YES-side +1, excluding the trigger wallets of the "
    "unit's merged window (N units: no exclusion); both sides need positive size and the interval must be observable, else the unit is mark-unavailable.",
    "Maker mark-out per share = yes_side x (p - M(s + 7,200)) with p the print's YES price; forgone rebate = REBATE_SHARE[cat] x DOCS_CATEGORY_RATE[cat] x p(1 - p) "
    "for prints on or after 2026-03-30 (cat = the sample's fee_category; unknown category -> 0). W1 = mean(mark-out + rebate) over S units of non-sports markets.",
    "Cluster ways: Gamma event (cb8_flow.event_key), UTC day of the print, and trigger wallet: wallets that share a merged window are united (union-find over the "
    "stage), so a merged window never splits across wallet clusters (conservative: fewer, larger clusters).",
    "Route gate (binding at the point estimate): mean mark-out over N u S' (non-sports, mark available) >= 0, WITHOUT the rebate the kept fills would earn "
    "(conservative); the with-rebate version is reported.",
    "GW (>= 2,000 S prints with a mark, >= 300 merged skip windows, >= 30 events, 30 days and 30 trigger-wallet clusters among the marked S units; non-sports) "
    "is applied at both stages on the stage's own units; a fail, unverified disjointness or a missing seal -> W1 not testable, p = 1, counted.",
    "Time-shift placebo: per market and draw one offset U[6 h, 66 h]; every trigger window [tau, e) keeps its length and wallets and moves to "
    "w0 + ((tau - w0 + offset) mod 72 h), wrapping at w0 + 72 h; shifted windows are merged; S units as W1 (same availability); advance = the p condition (floor off); "
    "200 draws, seed 8182; calibrated iff the advance rate <= 1.5%.",
    "Pseudo-pairs: consecutive same-side clips of the market (all wallets, time order) by different wallets meeting the gap, size-ratio and notional rules (no "
    "run-start or opposite-side rule); windows extend on ANY same-side clip; marks exclude both wallets. Credited iff W1 - W1_pseudo <= -|W1| / 2; no pseudo unit "
    "-> unverified (never credited; does not block).",
    "Robustness (i): the mark averaged over s + 3,600 and s + 10,800 (both required); keeps the sign and >= half of |W1|. (ii) top 5 events / days by absolute "
    "summed value dropped: p condition and floor. (iii) size-weighted sign. (iv) months with >= 500 S units: declared sign in >= 2/3 (no qualifying month -> "
    "unverified, blocks). (v) worst case: mark-unavailable S units enter with mark-out max(0, kept-fill mean) plus their rebate; sign and p condition. (vi) lag 300 s: "
    "sign and >= half of |W1|.",
    "Stage 2 uses p < alpha2 / k_used wherever Stage 1 uses 0.01; k_used = 1 + the other CB8 tests that advanced or have no final Stage-1 file yet.",
    "BY triage label: p <= q / (m H_m), m = battery2.cumulative_count() at run time. Batch-Holm label k1 = 3, alpha 0.01; tests without a final file enter as p = 1.",
    "MDE: the design's assumptions (SE about 0.15c at about 500 events) scaled by sqrt(500 / G_event) of the census; MDE = (z_0.99 + z_0.80) x SE; never used to change a floor.",
)


# ---- small helpers ------------------------------------------------------------------------------------------------------------------------------------


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(int(ts)))


def rebate(p: np.ndarray, ts: np.ndarray, cat: str) -> np.ndarray:
    key = str(cat or "").split(":")[0]
    r = economics.REBATE_SHARE.get(key, 0.0) * economics.DOCS_CATEGORY_RATE.get(key, 0.0)
    return np.where(np.asarray(ts) >= cm.ep(REBATE_FROM), r * np.asarray(p) * (1.0 - np.asarray(p)), 0.0)


def reach_s(lag: int) -> int:
    return OPP_LOOKBACK_S + TRIG_GAP_S[1] + lag + CAP_S


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, xs) -> None:
        xs = list(xs)
        if not xs:
            return
        r = self.find(xs[0])
        for x in xs[1:]:
            q = self.find(x)
            if q != r:
                self.parent[q] = r


# ---- inputs: seal, listing ---------------------------------------------------------------------------------------------------------------------------------


def verify_inputs(hist_root: Path, flow_sha: str, fp: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None, *, holdout: bool) -> dict:
    """Refuse unless the h9_flow run is complete under the flow rules and the pinned fingerprint, sealed, and the committed seal copy equals the run's seal;
    re-hash every sealed file the stage may read (HOLDOUT only when ``holdout``). A run that ended 'disjointness unverified' returns that status (no seal)."""
    rdir = Path(hist_root) / RUN_ID
    cm.refuse_path(rdir)
    mp = rdir / "manifest.json"
    if not mp.exists():
        raise cm.Refused(f"{RUN_ID} has no manifest")
    man = json.loads(mp.read_text())
    if man.get("rules_sha256") != flow_sha:
        raise cm.Refused(f"{RUN_ID} manifest rules hash {man.get('rules_sha256')} != flow rules {flow_sha}")
    if man.get("wallet_key_fingerprint") != fp or fp != WALLET_KEY_FP:
        raise cm.Refused("h9_flow wallet_key_fingerprint differs from the pin; mixed fingerprints are refused")
    if man.get("status") == F.UNVERIFIED or (rdir / "DISJOINTNESS_UNVERIFIED.json").exists():
        return {"status": F.UNVERIFIED, "seal": None, "rdir": rdir}
    if not (man.get("complete") is True and man.get("status") == F.COMPLETE and not man.get("stopped")):
        raise cm.Refused(f"{RUN_ID} is not {F.COMPLETE}")
    run_seal, copy = rdir / h5_seal.SEAL_NAME, Path(seals_dir) / SEAL_COPY_NAME
    if not run_seal.exists() or not copy.exists():
        raise cm.Refused("h9_flow seal or its committed copy is missing")
    if run_seal.read_bytes() != copy.read_bytes():
        raise cm.Refused("h9_flow seal copy differs from the run's seal")
    if is_committed is not None and not is_committed(copy):
        raise cm.Refused(f"{copy} is not committed")
    seal = json.loads(copy.read_text())
    files = seal.get("files") or {}
    if h5_seal.listing_sha256(files) != seal.get("listing_sha256") or h5_seal.declaration_sha256(seal.get("declaration", {})) != seal.get("declaration_sha256"):
        raise cm.Refused("h9_flow seal file table or declaration does not match its hashes")
    if seal.get("wallet_key_fingerprint") != fp or seal.get("rules_sha256") != flow_sha:
        raise cm.Refused("h9_flow seal carries another fingerprint or rules hash")
    n = 0
    for rel, sha in sorted(files.items()):
        if rel.startswith("holdout/") and not holdout:
            continue
        p = rdir / rel
        if not p.is_file() or h5_seal.sha256_file(p) != sha:
            raise cm.Refused(f"{RUN_ID}/{rel} is missing or differs from the seal")
        n += 1
    on_disk = {p.relative_to(rdir).as_posix() for p in (rdir / "screen").glob("*")} if (rdir / "screen").exists() else set()
    if on_disk - set(files):
        raise cm.Refused(f"SCREEN files not in the seal: {sorted(on_disk - set(files))[:3]}")
    return {"status": "sealed", "seal": seal, "rdir": rdir, "n_rehashed": n, "seal_sha256": h5_seal.sha256_file(copy), "manifest_sha256": h5_seal.sha256_file(mp)}


def verify_holdout_listing(rdir: Path, seal: dict) -> int:
    """Recompute the HOLDOUT listing and refuse unless its files equal the seal's ``holdout/`` entries and its sha256 equals ``drops.holdout_listing_sha256``."""
    files = {k: v for k, v in h5_seal.list_files(Path(rdir)).items() if k.startswith("holdout/")}
    want = {k: v for k, v in (seal.get("files") or {}).items() if k.startswith("holdout/")}
    if files != want or h5_seal.listing_sha256(files) != ((seal.get("drops") or {}).get("holdout_listing_sha256")):
        raise cm.Refused("HOLDOUT listing differs from the seal; refusing to read HOLDOUT")
    return len(files)


def holdout_counts(seal: dict | None, sample_rows: list[dict]) -> dict:
    """HOLDOUT file counts from the seal listing (names only) and HOLDOUT markets / events from sample.csv.gz (ids only)."""
    names = sorted(k for k in ((seal or {}).get("files") or {}) if k.startswith("holdout/"))
    rows = [r for r in sample_rows if r.get("split") == "holdout"]
    return {"n_files": len(names), "n_markets": len(rows), "n_events": len({F.event_key(r) for r in rows}),
            "n_events_non_sports": len({F.event_key(r) for r in rows if r.get("group") == "main"}),
            "holdout_listing_sha256": ((seal or {}).get("drops") or {}).get("holdout_listing_sha256")}


# ---- field-restricted access -------------------------------------------------------------------------------------------------------------------------------


class FlowView:
    """Files of ONE split of the sealed h9_flow run. HOLDOUT prints only when ``holdout_unlocked`` (set by ``replicate`` after the seal checks)."""

    def __init__(self, rdir: Path, split: str, *, holdout_unlocked: bool = False) -> None:
        if split not in ("screen", "holdout"):
            raise cm.Refused(f"unknown split {split!r}")
        if split == "holdout" and not holdout_unlocked:
            raise cm.Refused("HOLDOUT is sealed: only replicate opens it, after W1 advanced and the seal checks")
        self.rdir, self.split = Path(rdir), split
        self.opened: list[str] = []
        self._dropped: set[str] | None = None

    def _note(self, p: Path) -> Path:
        rel = Path(p).relative_to(self.rdir)
        if self.split == "screen" and rel.parts and rel.parts[0] == "holdout":
            raise cm.Refused(f"the SCREEN view never opens HOLDOUT ({rel.as_posix()})")
        self.opened.append(rel.as_posix())
        return Path(p)

    def dropped(self) -> set[str]:
        if self._dropped is None:
            p = self._note(self.rdir / "drops.csv.gz")
            self._dropped = {r["market_id"] for r in ba.c7.read_csv_gz(p) if str(r.get("block", "")).startswith("DROPPED")} if p.exists() else set()
        return self._dropped

    def sample_all(self) -> list[dict]:
        return list(ba.c7.read_csv_gz(self._note(self.rdir / "sample.csv.gz")))

    def sample(self) -> list[dict]:
        drop = self.dropped()
        return [r for r in self.sample_all() if r.get("split") == self.split and r["market_id"] not in drop]

    def day_status(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for r in ba.c7.read_csv_gz(self._note(self.rdir / "days.csv.gz")):
            out.setdefault(r["market_id"], {})[r["day"]] = r["status"]
        return out

    def split_report(self) -> dict:
        return json.loads(self._note(self.rdir / "split.json").read_text()).get("report", {})

    def prints(self, market_id: str) -> pd.DataFrame | None:
        p = self.rdir / self.split / f"{market_id}.csv.gz"
        self._note(p)
        if not p.exists():
            return None
        return pd.read_csv(p, compression="gzip", dtype={"wallet_hash": str}, keep_default_na=False)


# ---- one market ---------------------------------------------------------------------------------------------------------------------------------------------


@dataclass
class Market:
    market_id: str
    event: str
    group: str
    cat: str
    gap_days: float
    w0: int
    wend: int
    unav: list[tuple[int, int]]
    ts: np.ndarray
    yside: np.ndarray
    yp: np.ndarray
    price: np.ndarray
    size: np.ndarray
    wcode: np.ndarray
    clips: list[tuple] = field(default_factory=list)  # (wallet, side, start, t, size, vwap, notional)
    n_day_status: dict = field(default_factory=dict)

    @property
    def uend(self) -> int:
        return self.w0 + UNIT_WINDOW_S

    def observable(self, a, b) -> np.ndarray:
        """Vectorised: [a, b] lies in the fetched window and overlaps no unavailable day."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        ok = (a >= self.w0) & (b <= self.wend - 1)
        for ua, ub in self.unav:
            ok &= ~((a <= ub) & (b >= ua))
        return ok


def load_market(view: FlowView, row: dict, status: dict[str, str], enc: dict[str, int]) -> Market:
    w0, wend = int(row["w0_epoch"]), int(row["window_end_epoch"])
    unav, counts = [], {}
    for day, a, b in F.day_segments(w0, wend):
        st = status.get(day, "missing")
        counts[st] = counts.get(st, 0) + 1
        if st != "ok":
            unav.append((a, b))
    df = view.prints(row["market_id"])
    if df is None or not len(df):
        z = np.zeros(0)
        arrs = (z.astype(np.int64), z.astype(np.int64), z, z, z, z.astype(np.int64))
    else:
        df = df.sort_values(["ts", "token_idx", "side", "price", "size", "wallet_hash"], kind="mergesort")
        wc_ = np.array([enc.setdefault(w, len(enc)) if w else -1 for w in df["wallet_hash"].astype(str)], dtype=np.int64)
        arrs = (df["ts"].to_numpy(np.int64), df["yes_side"].to_numpy(np.int64), df["yes_price"].to_numpy(float), df["price"].to_numpy(float),
                df["size"].to_numpy(float), wc_)
    try:
        gap = float(row.get("gap_to_end_days") or "nan")
    except ValueError:
        gap = math.nan
    m = Market(row["market_id"], F.event_key(row), row.get("group") or "", row.get("fee_category") or "", gap, w0, wend, unav, *arrs, n_day_status=counts)
    m.clips = clips(m)
    return m


def clips(m: Market) -> list[tuple]:
    """Merge prints of one wallet on one YES side chained within 2 s. Returns (wallet, side, start, t_last, size, vwap_yes, notional) sorted by (t, wallet, side)."""
    out = []
    idx = np.where(m.wcode >= 0)[0]
    if not len(idx):
        return out
    order = idx[np.lexsort((m.ts[idx], m.yside[idx], m.wcode[idx]))]
    cur = None
    for i in order:
        w, s, t = int(m.wcode[i]), int(m.yside[i]), int(m.ts[i])
        if cur is not None and cur[0] == w and cur[1] == s and t - cur[3] <= CLIP_GAP_S:
            cur[3] = t
            cur[4] += m.size[i]
            cur[5] += m.size[i] * m.yp[i]
            cur[6] += m.size[i] * m.price[i]
            continue
        if cur is not None:
            out.append(cur)
        cur = [w, s, t, t, float(m.size[i]), float(m.size[i] * m.yp[i]), float(m.size[i] * m.price[i])]
    out.append(cur)
    res = [(c[0], c[1], c[2], c[3], c[4], (c[5] / c[4]) if c[4] > 0 else math.nan, c[6]) for c in out]
    return sorted(res, key=lambda c: (c[3], c[0], c[1]))


def _clip_ok_pair(c1: tuple, c2: tuple) -> bool:
    dt = c2[3] - c1[3]
    return bool(TRIG_GAP_S[0] <= dt <= TRIG_GAP_S[1] and c1[4] > 0 and SIZE_RATIO[0] <= c2[4] / c1[4] <= SIZE_RATIO[1]
                and c1[6] >= MIN_NOTIONAL and c2[6] >= MIN_NOTIONAL)


def _extend(tau: int, t2: int, later_same_side: list[int]) -> int:
    e, cap = tau + BASE_S, tau + CAP_S
    for tk in later_same_side:
        if tk <= t2:
            continue
        if tk >= e:
            break
        e = min(max(e, tk + BASE_S), cap)
    return e


def triggers(m: Market, lag: int = LAG_S) -> list[dict]:
    """Worked-order triggers of the market: c2 of wallet w with a same-side c1 of w (gap 20-600 s, size ratio 0.5-2, both notionals >= $50), c1 starting a run
    (no same-side clip of w in [t1 - 600, t1)) and no opposite-side clip of w in [t1 - 1,800, t2]. Each carries its skip window [tau, e)."""
    by_w: dict[int, list[tuple]] = {}
    for c in m.clips:
        by_w.setdefault(c[0], []).append(c)
    out = []
    for w, cs in by_w.items():
        ts = [c[3] for c in cs]
        for i, c2 in enumerate(cs):
            found = None
            for j in range(i - 1, -1, -1):
                c1 = cs[j]
                if c2[3] - c1[3] > TRIG_GAP_S[1]:
                    break
                if c1[1] != c2[1] or not _clip_ok_pair(c1, c2):
                    continue
                lo = bisect.bisect_left(ts, c1[3] - OPP_LOOKBACK_S)
                hi = bisect.bisect_right(ts, c2[3])
                if any(cs[k][1] != c2[1] for k in range(lo, hi)):
                    continue
                if any(cs[k][1] == c2[1] and c1[3] - RUN_START_S <= cs[k][3] < c1[3] for k in range(lo, j)):
                    continue
                found = c1
                break
            if found is None:
                continue
            tau = c2[3] + lag
            later = [c[3] for c in cs[i + 1:] if c[1] == c2[1]]
            out.append({"wallet": w, "side": c2[1], "t1": found[3], "t2": c2[3], "tau": tau, "e": _extend(tau, c2[3], later), "wallets": (w,),
                        "continued": any(c2[3] < t <= c2[3] + CONTINUATION_S for t in later)})
    return sorted(out, key=lambda x: (x["tau"], x["wallet"], x["side"]))


def pseudo_triggers(m: Market, lag: int = LAG_S) -> list[dict]:
    """Pseudo-pairs: consecutive same-side clips of the market by DIFFERENT wallets meeting the gap, size-ratio and notional rules; windows extend on any
    same-side clip; both wallets are excluded from the marks."""
    out = []
    for side in (1, -1):
        cs = [c for c in m.clips if c[1] == side]
        ts = [c[3] for c in cs]
        for i in range(1, len(cs)):
            c1, c2 = cs[i - 1], cs[i]
            if c1[0] == c2[0] or not _clip_ok_pair(c1, c2):
                continue
            tau = c2[3] + lag
            later = ts[i + 1:]
            out.append({"wallet": c2[0], "side": side, "t1": c1[3], "t2": c2[3], "tau": tau, "e": _extend(tau, c2[3], later), "wallets": (c1[0], c2[0]),
                        "continued": any(c2[3] < cs[k][3] <= c2[3] + CONTINUATION_S and cs[k][0] == c2[0] for k in range(i + 1, len(cs)))})
    return sorted(out, key=lambda x: (x["tau"], x["wallet"], x["side"]))


def merge_windows(wins: list[tuple[int, int, int, tuple]]) -> dict[int, list[list]]:
    """Merge overlapping same-side windows ``(side, start, end, wallets)`` (half-open). Returns side -> [[start, end, set(wallets)], ...] sorted."""
    out: dict[int, list[list]] = {1: [], -1: []}
    for side in (1, -1):
        for _s, a, b, ws in sorted((w for w in wins if w[0] == side), key=lambda w: (w[1], w[2])):
            cur = out[side][-1] if out[side] else None
            if cur is not None and a < cur[1]:
                cur[1] = max(cur[1], b)
                cur[2].update(ws)
            else:
                out[side].append([a, b, set(ws)])
    return out


def shift_windows(m: Market, trig: list[dict], offset: int) -> list[tuple]:
    """Time-shift placebo: each trigger window keeps its length and wallets and moves circularly within the 72-h window."""
    out = []
    L = UNIT_WINDOW_S
    for t in trig:
        ln = t["e"] - t["tau"]
        a = m.w0 + ((t["tau"] - m.w0 + offset) % L)
        b = a + ln
        if b <= m.w0 + L:
            out.append((t["side"], a, b, t["wallets"]))
        else:
            out.append((t["side"], a, m.w0 + L, t["wallets"]))
            out.append((t["side"], m.w0, m.w0 + (b - (m.w0 + L)), t["wallets"]))
    return out


def classify(m: Market, merged: dict[int, list[list]], lag: int) -> dict:
    """Unit classes of the market's prints: usable (YES price in [0.03, 0.97], s in [w0, w0 + 72 h), [s - reach, s] observable), then S / S' / N / both."""
    ts = m.ts
    usable = (m.yp >= USABLE[0]) & (m.yp <= USABLE[1]) & (ts >= m.w0) & (ts < m.uend)
    obs = m.observable(ts - reach_s(lag), ts)
    unit = usable & obs
    win = {}
    for side in (1, -1):
        ws = merged[side]
        if ws:
            starts = np.array([w[0] for w in ws])
            ends = np.array([w[1] for w in ws])
            k = np.searchsorted(starts, ts, side="right") - 1
            inside = (k >= 0) & (ts < ends[np.maximum(k, 0)])
            win[side] = (inside, np.where(inside, k, -1))
        else:
            win[side] = (np.zeros(len(ts), bool), np.full(len(ts), -1))
    both = win[1][0] & win[-1][0]
    in_same = np.where(m.yside == 1, win[1][0], win[-1][0]) & ~both
    in_opp = np.where(m.yside == 1, win[-1][0], win[1][0]) & ~both
    wid_same = np.where(m.yside == 1, win[1][1], win[-1][1])
    wid_opp = np.where(m.yside == 1, win[-1][1], win[1][1])
    return {"usable": usable, "unit": unit, "S": unit & in_same, "Sp": unit & in_opp, "N": unit & ~win[1][0] & ~win[-1][0], "both": unit & both,
            "wid_same": wid_same, "wid_opp": wid_opp, "n_unavailable_usable": int((usable & ~obs).sum())}


# ---- marks --------------------------------------------------------------------------------------------------------------------------------------------------


def _cum(x: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(x, dtype=float)])


class MarkIndex:
    """Two-sided print marks of one market. For the purpose ``census`` it holds positive-size print COUNTS only (no price sums) and ``values`` refuses;
    mark values exist only for ``screen`` / ``replicate``."""

    def __init__(self, m: Market, purpose: str) -> None:
        self.m, self.purpose = m, purpose
        self.valued = purpose in wc.GUARDED_PURPOSES
        pos = m.size > 0
        self.cnt = {s: _cum((m.yside == s) & pos) for s in (1, -1)}
        if self.valued:
            self.sz = {s: _cum(np.where(m.yside == s, m.size, 0.0)) for s in (1, -1)}
            self.vl = {s: _cum(np.where(m.yside == s, m.size * m.yp, 0.0)) for s in (1, -1)}
        self._w: dict[int, dict] = {}

    def _wallet(self, w: int) -> dict:
        if w not in self._w:
            idx = np.where(self.m.wcode == w)[0]
            pos = self.m.size[idx] > 0
            d = {"idx": idx, "cnt": {s: _cum((self.m.yside[idx] == s) & pos) for s in (1, -1)}}
            if self.valued:
                d["sz"] = {s: _cum(np.where(self.m.yside[idx] == s, self.m.size[idx], 0.0)) for s in (1, -1)}
                d["vl"] = {s: _cum(np.where(self.m.yside[idx] == s, self.m.size[idx] * self.m.yp[idx], 0.0)) for s in (1, -1)}
            self._w[w] = d
        return self._w[w]

    def _sums(self, us: np.ndarray, excl, what: str) -> tuple[dict, np.ndarray]:
        us = np.asarray(us, float)
        lo = np.searchsorted(self.m.ts, us - MARK_HALF_S, side="left")
        hi = np.searchsorted(self.m.ts, us + MARK_HALF_S, side="right")
        src = getattr(self, what)
        out = {s: src[s][hi] - src[s][lo] for s in (1, -1)}
        for w in excl or ():
            d = self._wallet(int(w))
            a, b = np.searchsorted(d["idx"], lo, side="left"), np.searchsorted(d["idx"], hi, side="left")
            for s in (1, -1):
                out[s] = out[s] - (d[what][s][b] - d[what][s][a])
        obs = self.m.observable(us - MARK_HALF_S, us + MARK_HALF_S)
        return out, obs

    def available(self, us, excl=()) -> np.ndarray:
        c, obs = self._sums(us, excl, "cnt")
        return obs & (c[1] > 0) & (c[-1] > 0)

    def values(self, us, excl=()) -> np.ndarray:
        """M(u) for every u (NaN where unavailable). Screen / replicate only."""
        if not self.valued:
            raise cm.Refused(f"mark values are computed only for {wc.GUARDED_PURPOSES}, not {self.purpose!r}")
        ok = self.available(us, excl)
        n, _ = self._sums(us, excl, "sz")
        v, _ = self._sums(us, excl, "vl")
        with np.errstate(divide="ignore", invalid="ignore"):
            mk = (v[1] / n[1] + v[-1] / n[-1]) / 2.0
        return np.where(ok & (n[1] > 0) & (n[-1] > 0), mk, np.nan)


def _groups(mask: np.ndarray, wside: np.ndarray, wid: np.ndarray) -> dict[tuple[int, int], np.ndarray]:
    """Unit indices grouped by (window side, merged-window index)."""
    out: dict[tuple[int, int], list[int]] = {}
    for i in np.where(mask)[0]:
        out.setdefault((int(wside[i]), int(wid[i])), []).append(int(i))
    return {k: np.array(v, dtype=np.int64) for k, v in out.items()}


def unit_marks(mi: MarkIndex, merged: dict[int, list[list]], cls: dict, cname: str, horizon: int, *, values: bool) -> tuple[np.ndarray, np.ndarray]:
    """Per-print mark at s + horizon for the class ``cname`` (S / Sp / N), excluding the trigger wallets of the print's merged window (N: none). Returns
    (indices in ascending order, marks (NaN = unavailable) or availability)."""
    m = mi.m
    mask = cls[cname]
    if cname == "N":
        idx = np.where(mask)[0]
        us = m.ts[idx] + horizon
        return idx, (mi.values(us) if values else mi.available(us))
    wside = m.yside if cname == "S" else -m.yside
    wid = cls["wid_same"] if cname == "S" else cls["wid_opp"]
    idx_all, out_all = [], []
    for (side, k), idx in _groups(mask, wside, wid).items():
        excl = merged[side][k][2]
        us = m.ts[idx] + horizon
        idx_all.append(idx)
        out_all.append(mi.values(us, excl) if values else mi.available(us, excl))
    if not idx_all:
        return np.zeros(0, dtype=np.int64), (np.zeros(0) if values else np.zeros(0, bool))
    idx, out = np.concatenate(idx_all), np.concatenate(out_all)
    o = np.argsort(idx, kind="mergesort")
    return idx[o], out[o]


# ---- one stage -------------------------------------------------------------------------------------------------------------------------------------------


@dataclass
class Stage:
    markets: list[Market]
    purpose: str
    trig: dict[str, list[dict]] = field(default_factory=dict)
    marks: dict[str, MarkIndex] = field(default_factory=dict)
    uf: UnionFind = field(default_factory=UnionFind)


def build_stage(view: FlowView, purpose: str) -> Stage:
    status = view.day_status()
    enc: dict[str, int] = {}
    markets = [load_market(view, r, status.get(r["market_id"], {}), enc) for r in sorted(view.sample(), key=lambda r: r["market_id"])]
    st = Stage(markets, purpose)
    for m in markets:
        st.trig[m.market_id] = triggers(m, LAG_S)
        st.marks[m.market_id] = MarkIndex(m, purpose)
    return st


def _windows(trig: list[dict]) -> list[tuple]:
    return [(t["side"], t["tau"], t["e"], t["wallets"]) for t in trig]


def collect_units(st: Stage, group: str, trig_of: Callable[[Market], list[dict]] | None = None, *, lag: int = LAG_S, horizon: int = HORIZON_S,
                  values: bool, windows_of: Callable[[Market], list[tuple]] | None = None, kept: bool = False, uf: UnionFind | None = None) -> dict:
    """S units (and, with ``kept``, the N u S' kept fills) of the stage's markets of ``group``. ``values`` False: availability only (census)."""
    uf = uf if uf is not None else UnionFind()
    s_units, kept_units = [], []
    counts = {"triggers": 0, "merged_windows": 0, "S": 0, "Sp": 0, "N": 0, "both_sides": 0, "usable_unavailable": 0, "S_mark": 0, "kept_mark": 0, "markets": 0}
    per: list[tuple] = []
    for m in st.markets:
        if m.group != group:
            continue
        counts["markets"] += 1
        wins = windows_of(m) if windows_of else _windows((trig_of or (lambda x: st.trig[x.market_id]))(m))
        merged = merge_windows(wins)
        for side in (1, -1):
            for w in merged[side]:
                uf.union(w[2])
        counts["triggers"] += len(wins)
        counts["merged_windows"] += len(merged[1]) + len(merged[-1])
        cls = classify(m, merged, lag)
        for k in ("S", "Sp", "N"):
            counts[k] += int(cls[k].sum())
        counts["both_sides"] += int(cls["both"].sum())
        counts["usable_unavailable"] += cls["n_unavailable_usable"]
        per.append((m, merged, cls))
    for m, merged, cls in per:
        mi = st.marks[m.market_id]
        idx, mk = unit_marks(mi, merged, cls, "S", horizon, values=values)
        reb = rebate(m.yp[idx], m.ts[idx], m.cat)
        wid = cls["wid_same"]
        for j, i in enumerate(idx):
            side = int(m.yside[i])
            w_any = next(iter(merged[side][int(wid[i])][2]))
            avail = bool(np.isfinite(mk[j])) if values else bool(mk[j])
            u = {"market_id": m.market_id, "event": m.event, "day": _day(m.ts[i]), "month": _day(m.ts[i])[:7], "w_any": w_any, "size": float(m.size[i]),
                 "p": float(m.yp[i]), "side": side, "ts": int(m.ts[i]), "rebate": float(reb[j]), "avail": avail, "gap_days": m.gap_days}
            if values and avail:
                u["mo"] = float(side * (m.yp[i] - mk[j]))
                u["v"] = u["mo"] + u["rebate"]
            s_units.append(u)
        if kept:
            for cname in ("Sp", "N"):
                kidx, kmk = unit_marks(mi, merged, cls, cname, horizon, values=values)
                ok = np.isfinite(kmk) if values else kmk.astype(bool)
                counts["kept_mark"] += int(ok.sum())
                if values and ok.any():
                    ki = kidx[ok]
                    mo = m.yside[ki] * (m.yp[ki] - kmk[ok])
                    kept_units.extend(zip(mo.tolist(), rebate(m.yp[ki], m.ts[ki], m.cat).tolist(), strict=True))
    for u in s_units:
        u["wallet"] = f"wc{uf.find(u['w_any'])}"
    counts["S_mark"] = sum(1 for u in s_units if u["avail"])
    return {"S": s_units, "kept": kept_units, "counts": counts, "uf": uf}


def gw_gate(s_units: list[dict], counts: dict) -> dict:
    marked = [u for u in s_units if u["avail"]]
    n_ev, n_day, n_w = len({u["event"] for u in marked}), len({u["day"] for u in marked}), len({u["wallet"] for u in marked})
    ok = (len(marked) >= GW_MIN_S_MARKED and counts["merged_windows"] >= GW_MIN_WINDOWS and n_ev >= GW_MIN_EVENTS and n_day >= GW_MIN_DAYS and n_w >= GW_MIN_WALLETS)
    return {"ok": bool(ok), "n_S_marked": len(marked), "n_skip_windows": counts["merged_windows"], "n_events": n_ev, "n_days": n_day, "n_trigger_wallets": n_w,
            "thresholds": [GW_MIN_S_MARKED, GW_MIN_WINDOWS, GW_MIN_EVENTS, GW_MIN_DAYS, GW_MIN_WALLETS],
            "fail_label": None if ok else "not testable (GW failed)"}


# ---- census (q0169, W part): counts only --------------------------------------------------------------------------------------------------------------------


def census_w(hist_root: Path, *, flow_sha: str, fp: str, analysis_rules_sha: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None) -> dict:
    """Counts only on SCREEN units; HOLDOUT file counts from the seal listing and HOLDOUT events from sample ids. Never computes a mark value."""
    inp = verify_inputs(hist_root, flow_sha, fp, seals_dir, is_committed, holdout=False)
    out: dict = {"census": "CB8-W pre-freeze census (counts only; SCREEN events; HOLDOUT file and event counts only)", "rules_version": RULES_VERSION,
                 RULES_KEY: analysis_rules_sha, DATA_KEY: flow_sha, "wallet_key_fingerprint": fp, "evidence_role": wc.EVIDENCE_ROLE, "label": wc.LABEL,
                 "inputs": {k: v for k, v in inp.items() if k not in ("seal", "rdir")}}
    if inp["status"] == F.UNVERIFIED:
        out["gate_GW"] = {"ok": False, "fail_label": "not testable (disjointness unverified)"}
        out["mde_W1"] = {"mde": None}
        out["interpretations"] = list(INTERPRETATIONS)
        return ba._clean(out)
    view = FlowView(inp["rdir"], "screen")
    rep = view.split_report()
    out["frame"] = {"n_frame_in": rep.get("n_frame_in"), "filtered": rep.get("filtered"), "dropped_id": rep.get("dropped_id"), "dropped_keys": rep.get("dropped_keys"),
                    "window_empty": rep.get("window_empty"), "capped_out_per_event": rep.get("capped_out_per_event"), "n_sample": rep.get("n_sample"),
                    "n_screen": rep.get("n_screen"), "n_holdout": rep.get("n_holdout"), "seal_time_drops": len(view.dropped()),
                    "disjointness": ((inp["seal"].get("drops") or {}).get("disjointness"))}
    st = build_stage(view, "census")
    status: dict[str, int] = {}
    per_md = []
    for m in st.markets:
        for k, v in m.n_day_status.items():
            status[k] = status.get(k, 0) + v
        for _d, a, b in F.day_segments(m.w0, m.wend):
            per_md.append(int(((m.ts >= a) & (m.ts <= b)).sum()))
    out["days"] = {"by_status": dict(sorted(status.items())), "prints_per_market_day": {"n": len(per_md), "median": float(np.median(per_md)) if per_md else None,
                                                                                        "p90": float(np.percentile(per_md, 90)) if per_md else None}}
    res = {}
    for group in ("main", "sports"):
        r = collect_units(st, group, values=False, kept=True)
        res[group] = r
    main = res["main"]
    gw = gw_gate(main["S"], main["counts"])
    trig_all = [t for m in st.markets if m.group == "main" for t in st.trig[m.market_id]]
    out["units_non_sports"] = {**main["counts"], "S_mark_share": (main["counts"]["S_mark"] / main["counts"]["S"]) if main["counts"]["S"] else None,
                               "triggers_continued": sum(1 for t in trig_all if t["continued"]),
                               "clusters_S_marked": {k: gw[k] for k in ("n_events", "n_days", "n_trigger_wallets")},
                               "stratum_gap_ge_14d": {"S": sum(1 for u in main["S"] if u["gap_days"] >= STRATUM_GAP_DAYS),
                                                      "S_marked": sum(1 for u in main["S"] if u["avail"] and u["gap_days"] >= STRATUM_GAP_DAYS),
                                                      "markets": sum(1 for m in st.markets if m.group == "main" and m.gap_days >= STRATUM_GAP_DAYS)}}
    out["units_sports_stratum"] = dict(res["sports"]["counts"])
    out["gate_GW"] = gw
    out["mde_W1"] = {"mde": wc.mde_scaled(gw["n_events"], MDE_SE_REF, MDE_G_REF), "assumptions": {"se_ref": MDE_SE_REF, "g_ref_events": MDE_G_REF},
                     "n_events": gw["n_events"], "note": "never used to change a floor, window or threshold"}
    out["holdout"] = holdout_counts(inp["seal"], view.sample_all())
    out["opened_files_n"] = len(set(view.opened))
    out["opened_holdout"] = sorted({f for f in view.opened if f.startswith("holdout/")})
    out["interpretations"] = list(INTERPRETATIONS)
    return ba._clean(out)


# ---- evaluation (screen and replicate) ---------------------------------------------------------------------------------------------------------------------


def _test(units: list[dict], alpha: float | None = None, val: str = "v") -> dict:
    return wc.ways_test([u[val] for u in units], [u["event"] for u in units], [u["day"] for u in units], {"wallet": [u["wallet"] for u in units]},
                        sign=SIGN, alpha=alpha)


def time_shift_placebo(st: Stage, *, alpha: float, draws: int = wc.PLACEBO_DRAWS, seed: int = SEED_TIMESHIFT) -> dict:
    rng = np.random.default_rng(seed)
    mains = [m for m in st.markets if m.group == "main"]
    adv = 0
    for _ in range(draws):
        offs = {m.market_id: int(rng.integers(SHIFT_RANGE_S[0], SHIFT_RANGE_S[1] + 1)) for m in mains}
        r = collect_units(st, "main", values=True, windows_of=lambda m, o=offs: shift_windows(m, st.trig[m.market_id], o[m.market_id]))
        us = [u for u in r["S"] if u["avail"]]
        adv += int(wc.p_ok(_test(us, alpha), alpha))
    return wc.placebo_summary(adv, draws, seed)


def evaluate_w1(st: Stage, *, alpha: float, disjointness: str | None, cumulative: int) -> dict:
    res: dict = {"split": None, "alpha": alpha, "floor": -wc.EDGE_FLOOR}
    blockers = []
    if disjointness != "verified":
        blockers.append(f"not testable (disjointness {disjointness})")
    prim = collect_units(st, "main", values=True, kept=True)
    s_all = prim["S"]
    units = [u for u in s_all if u["avail"]]
    unav = [u for u in s_all if not u["avail"]]
    gw = gw_gate(s_all, prim["counts"])
    res.update(counts=prim["counts"], gate_GW=gw)
    if not gw["ok"]:
        blockers.append("GW failed: not testable")
    t = _test(units)
    v = [u["v"] for u in units]
    t["ci95_event_bootstrap"] = ba.boot_ci(v, [u["event"] for u in units]) if units else None
    res["W1"] = t
    kept_mo = [k[0] for k in prim["kept"]]
    kept_mean = float(np.mean(kept_mo)) if kept_mo else math.nan
    res["route_gate"] = {"n": len(kept_mo), "mean_mark_out": kept_mean, "ok": bool(kept_mo and kept_mean >= 0),
                         "with_rebate_reported": float(np.mean([a + b for a, b in prim["kept"]])) if kept_mo else None}
    testable = bool(t["testable"]) and not blockers
    res["placebo_time_shift"] = time_shift_placebo(st, alpha=alpha) if testable else {"skipped": "not testable"}
    pse = collect_units(st, "main", trig_of=lambda m: pseudo_triggers(m, LAG_S), values=True)
    res["wallet_attribution"] = wc.attribution(t["mean"], [u["v"] for u in pse["S"] if u["avail"]], SIGN,
                                               ("worked-order footprint credited", "post-burst fills adverse whoever trades: a burst rule, not a footprint rule"), "wallet")
    rob: dict = {}
    if testable:
        rob = robustness(st, units, unav, kept_mean, t["mean"], alpha=alpha)
    res["robustness"] = rob
    res["reported"] = reported(st, units, prim, pse, t["mean"]) if units else {}
    checks = {"p": wc.p_ok(t, alpha) if testable else False, "floor": bool(testable and wc.floor_ok(t["mean"], SIGN)), "route_gate": res["route_gate"]["ok"],
              "placebo_time_shift": res["placebo_time_shift"].get("calibrated") if testable else False}
    checks.update({f"robust_{k}": r.get("ok") for k, r in rob.items()})
    failed = sorted(k for k, x in checks.items() if x is False)
    unverified = sorted(k for k, x in checks.items() if x is None)
    advance = bool(testable and not failed and not unverified)
    res.update(testable=testable, blockers=blockers, p=float(t["p"]) if testable else 1.0, effect=t["mean"], n=t["n"], checks=checks, failed_checks=failed,
               unverified_checks=unverified, advance=advance, cumulative_count_at_run=cumulative)
    if not testable:
        res["verdict"] = blockers[0] if blockers else f"not testable ({t.get('reason')})"
    elif advance:
        res["verdict"] = "advanced" + ("" if res["wallet_attribution"].get("credited") else f" ({res['wallet_attribution']['label']})")
    elif wc.core_ok(t, alpha, SIGN) and not res["route_gate"]["ok"]:
        res["verdict"] = "skipping helps, but the maker still loses: no route"
    else:
        res["verdict"] = f"not detected at MDE (failed: {', '.join(failed + unverified)})"
    return res


def robustness(st: Stage, units: list[dict], unav: list[dict], kept_mean: float, w1: float, *, alpha: float) -> dict:
    out: dict = {}
    # (i) alternative mark: average of the marks at s + 3,600 and s + 10,800 (both required)
    a1 = collect_units(st, "main", values=True, horizon=ALT_HORIZONS_S[0])["S"]
    a2 = collect_units(st, "main", values=True, horizon=ALT_HORIZONS_S[1])["S"]
    alt = [0.5 * (x["mo"] + y["mo"]) + x["rebate"] for x, y in zip(a1, a2, strict=True) if x["avail"] and y["avail"]]  # the S set does not depend on the horizon
    am = float(np.mean(alt)) if alt else math.nan
    out["alt_mark"] = {"n": len(alt), "mean": am, "ok": wc.half_magnitude_ok(am, w1, SIGN)}
    # (ii) top 5 events / days
    for k, name in (("event", "top5_events"), ("day", "top5_days")):
        sub = wc.drop_top(units, k)
        t = _test(sub, alpha)
        out[name] = {"n": t["n"], "mean": t["mean"], "p": t["p"], "ok": wc.core_ok(t, alpha, SIGN)}
    # (iii) size-weighted sign
    out["weighted_sign"] = wc.weighted_sign(units, w1, "size")
    # (iv) sign by month
    out["month_sign"] = wc.month_sign(units, SIGN, MONTH_MIN_UNITS)
    # (v) worst case: mark-unavailable S units at max(0, kept mean) + rebate
    fill = max(0.0, kept_mean) if np.isfinite(kept_mean) else 0.0
    wcu = units + [{**u, "v": fill + u["rebate"]} for u in unav]
    t = _test(wcu, alpha)
    out["worst_case"] = {"n_added": len(unav), "fill_mark_out": fill, "mean": t["mean"], "p": t["p"],
                         "ok": bool(np.isfinite(t["mean"]) and SIGN * t["mean"] > 0 and wc.p_ok(t, alpha))}
    # (vi) latency 300 s
    lat = collect_units(st, "main", trig_of=lambda m: triggers(m, LAG_ROBUST_S), lag=LAG_ROBUST_S, values=True)["S"]
    lv = [u["v"] for u in lat if u["avail"]]
    lm = float(np.mean(lv)) if lv else math.nan
    out["latency"] = {"n": len(lv), "mean": lm, "ok": wc.half_magnitude_ok(lm, w1, SIGN)}
    return out


def reported(st: Stage, units: list[dict], prim: dict, pse: dict, w1: float) -> dict:
    """Reported, not binding: continuation (triggers vs pseudo), the sequence reversal R, the lead-implied split, the sports stratum, 1-h horizon, the
    >= 14 d stratum and the with-rebate route gate."""

    def summ(vs: list[float]) -> dict:
        return {"n": len(vs), "mean": float(np.mean(vs)) if vs else None}

    out: dict = {}
    trig = [t for m in st.markets if m.group == "main" for t in st.trig[m.market_id]]
    ptrig = [t for m in st.markets if m.group == "main" for t in pseudo_triggers(m, LAG_S)]
    out["continuation"] = {"triggers": summ([float(t["continued"]) for t in trig]), "pseudo_pairs": summ([float(t["continued"]) for t in ptrig])}
    sp = collect_units(st, "sports", values=True)["S"]
    out["sports_stratum"] = summ([u["v"] for u in sp if u["avail"]])
    h1 = collect_units(st, "main", values=True, horizon=REPORT_HORIZON_S)["S"]
    out["horizon_1h"] = summ([u["v"] for u in h1 if u["avail"]])
    out["stratum_gap_ge_14d"] = summ([u["v"] for u in units if u["gap_days"] >= STRATUM_GAP_DAYS])
    out["stratum_gap_lt_14d"] = summ([u["v"] for u in units if not u["gap_days"] >= STRATUM_GAP_DAYS])
    s2 = collect_units(st, "main", values=True)["S"]
    h0 = collect_units(st, "main", values=True, horizon=0)["S"]
    spread = [z["mo"] for x, z in zip(s2, h0, strict=True) if x["avail"] and z["avail"]]
    drift = [x["mo"] - z["mo"] for x, z in zip(s2, h0, strict=True) if x["avail"] and z["avail"]]
    out["lead_implied_split"] = {"spread_captured": summ(spread), "drift": summ(drift)}
    out["sequence_reversal"] = sequence_reversal(st)
    out["route_gate_with_rebate"] = summ([a + b for a, b in prim["kept"]])
    out["pseudo_W1"] = summ([u["v"] for u in pse["S"] if u["avail"]])
    return out


def sequence_reversal(st: Stage) -> dict:
    """Descriptive only (uses future clips; never a selection rule): runs of >= 4 same-side clips of one wallet (consecutive gaps <= 600 s, no opposite clip of
    the wallet in between) with inter-arrival and size CV < 0.5; R = d x (M(e_last + 2 h) - M(e_last + 15 min)) excluding the wallet."""
    rs = []
    for m in st.markets:
        if m.group != "main":
            continue
        mi = st.marks[m.market_id]
        by_w: dict[int, list[tuple]] = {}
        for c in m.clips:
            by_w.setdefault(c[0], []).append(c)
        for w, cs in by_w.items():
            run: list[tuple] = []
            for c in cs + [None]:
                if c is not None and run and c[1] == run[-1][1] and c[3] - run[-1][3] <= TRIG_GAP_S[1]:
                    run.append(c)
                    continue
                if len(run) >= SEQ_MIN_CLIPS:
                    gaps = np.diff([x[3] for x in run]).astype(float)
                    sizes = np.array([x[4] for x in run], float)
                    cv_g = float(gaps.std() / gaps.mean()) if gaps.mean() > 0 else math.inf
                    cv_s = float(sizes.std() / sizes.mean()) if sizes.mean() > 0 else math.inf
                    if cv_g < SEQ_CV_MAX and cv_s < SEQ_CV_MAX:
                        e = run[-1][3]
                        a, b = mi.values(np.array([e + REVERSAL_TO_S, e + REVERSAL_FROM_S], float), (w,))
                        if np.isfinite(a) and np.isfinite(b):
                            rs.append(run[0][1] * (a - b))
                run = [c] if c is not None else []
    return {"n": len(rs), "mean_R": float(np.mean(rs)) if rs else None}


# ---- runs ------------------------------------------------------------------------------------------------------------------------------------------------------


def run_census(out_root: Path, hist_root: Path, *, flow_sha: str, fp: str, analysis_rules_sha: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None,
               trials_path: Path) -> dict:
    """q0169 (W part): write ``census_W.json`` (write-once) and one ``cb8_descriptive`` line."""
    out_p = Path(out_root) / CENSUS_NAME
    if out_p.exists():
        raise cm.Refused(f"{out_p} already exists; the census is write-once")
    doc = census_w(hist_root, flow_sha=flow_sha, fp=fp, analysis_rules_sha=analysis_rules_sha, seals_dir=seals_dir, is_committed=is_committed)
    doc["run_utc"] = wc.now_iso()
    doc["cumulative_count_at_run"] = wc.cumulative(trials_path)
    sha = wc.write_results(out_p, doc)
    from . import provenance  # noqa: PLC0415

    provenance.append_trial({"kind": "cb8_descriptive", "label": wc.LABEL, "evidence_role": wc.EVIDENCE_ROLE, "dataset": wc.DATASET, "preset": "W:census", "family": FAMILY,
                             "result_path": str(out_p), "results_sha256": sha, RULES_KEY: analysis_rules_sha, "n_tests": 0,
                             "summary": ba._clean({"gate_GW": doc["gate_GW"], "mde_W1": doc["mde_W1"]["mde"], "holdout": doc.get("holdout")})}, trials_path)
    gw = doc["gate_GW"]
    return {"status": "census_W_complete", "gate_GW": gw.get("ok"), "gw_fail_label": gw.get("fail_label"), "n_S_marked": gw.get("n_S_marked"),
            "n_skip_windows": gw.get("n_skip_windows"), "mde": doc["mde_W1"]["mde"], "written": str(out_p), "census_sha256": sha}


def _not_testable_doc(label: str, cumulative: int) -> dict:
    return {"testable": False, "advance": False, "p": 1.0, "effect": None, "n": 0, "verdict": label, "blockers": [label], "checks": {}, "cumulative_count_at_run": cumulative,
            "placebo_time_shift": {"skipped": "not testable"}}


def screen_w(out_root: Path, hist_root: Path, *, flow_sha: str, fp: str, analysis_rules_sha: str, freeze_sha: str, seals_dir: Path,
             is_committed: Callable[[Path], bool] | None, trials_path: Path) -> dict:
    """q0171: W1 Stage 1 on SCREEN events. Results are write-once; the Stage-1 copy goes to ``seals/cb8_w1_stage1.json`` (commit it)."""
    out_root, seals_dir = Path(out_root), Path(seals_dir)
    out_p, copy = out_root / RESULTS_S1, seals_dir / STAGE1_COPY_NAME
    if out_p.exists() or copy.exists():
        raise cm.Refused(f"{out_p.name} or its Stage-1 copy already exists; results are never overwritten")
    census = out_root / CENSUS_NAME
    if not census.exists() or json.loads(census.read_text()).get(RULES_KEY) != analysis_rules_sha:
        raise cm.Refused("census_W.json (q0169) missing or produced under different W analysis rules")
    inp = verify_inputs(hist_root, flow_sha, fp, seals_dir, is_committed, holdout=False)
    cum = wc.cumulative(trials_path)
    opened: list[str] = []
    if inp["status"] == F.UNVERIFIED:
        res = _not_testable_doc("not testable (disjointness unverified)", cum)
    else:
        h5_seal.log_access(inp["rdir"], "cb8_screen_W", ["screen/*", "sample.csv.gz", "days.csv.gz", "drops.csv.gz"])
        view = FlowView(inp["rdir"], "screen")
        st = build_stage(view, "screen")
        res = evaluate_w1(st, alpha=wc.ALPHA1, disjointness=(inp["seal"].get("drops") or {}).get("disjointness"), cumulative=cum)
        opened = sorted(set(view.opened))
    res["split"] = "screen"
    res["labels_stage1"] = {"by": ba.by_label(res["p"], cum), "batch_holm": wc.batch_holm_label(TEST, res["p"], out_root)}
    doc = {"test": TEST, "stage": 1, "rules_version": RULES_VERSION, RULES_KEY: analysis_rules_sha, DATA_KEY: flow_sha, "wallet_key_fingerprint": fp,
           "freeze_spec_sha256": freeze_sha, "inputs": {k: v for k, v in inp.items() if k not in ("seal", "rdir")}, "evidence_role": wc.EVIDENCE_ROLE, "label": wc.LABEL,
           "run_utc": wc.now_iso(), "interpretations": list(INTERPRETATIONS), **res, "opened_files_n": len(opened),
           "opened_holdout": [f for f in opened if f.startswith("holdout/")]}
    sha = wc.write_results(out_p, doc)
    wc.write_stage1_copy(out_p, copy)
    wc.log_trials(res, family=FAMILY, test=TEST, replication=False, results_path=out_p, results_sha=sha, rules_key=RULES_KEY, rules_sha=analysis_rules_sha,
                  freeze_sha=freeze_sha, trials_path=trials_path, placebo_key="placebo_time_shift", descriptive=_descriptive(res))
    return {"status": "screen_W_complete", "advance": res["advance"], "p": res["p"], "testable": res["testable"], "verdict": res["verdict"], "results_sha256": sha,
            "written": str(out_p), "stage1_copy": str(copy)}


def _descriptive(res: dict) -> dict:
    return {"gate_GW": {k: (res.get("gate_GW") or {}).get(k) for k in ("ok", "n_S_marked", "n_skip_windows", "n_events", "n_days", "n_trigger_wallets")},
            "route_gate": {k: (res.get("route_gate") or {}).get(k) for k in ("n", "mean_mark_out", "ok")},
            "wallet_attribution": {k: (res.get("wallet_attribution") or {}).get(k) for k in ("credited", "label")}}


def replicate_w(out_root: Path, hist_root: Path, *, flow_sha: str, fp: str, analysis_rules_sha: str, freeze_sha: str, seals_dir: Path,
                is_committed: Callable[[Path], bool] | None, trials_path: Path) -> dict:
    """q0175: W1-rep on the sealed HOLDOUT events. Refuses unless W1 advanced (committed Stage-1 copy), then verifies the seal copy and the HOLDOUT listing
    sha256 BEFORE any HOLDOUT read."""
    out_root, seals_dir = Path(out_root), Path(seals_dir)
    out_p = out_root / RESULTS_S2
    if out_p.exists():
        raise cm.Refused(f"{out_p.name} already exists; results are never overwritten")
    s1 = wc.require_stage1_advanced(out_root, seals_dir, test=TEST, results_name=RESULTS_S1, copy_name=STAGE1_COPY_NAME, rules_key=RULES_KEY,
                                    rules_sha=analysis_rules_sha, is_committed=is_committed)
    inp0 = verify_inputs(hist_root, flow_sha, fp, seals_dir, is_committed, holdout=False)
    if inp0["status"] != "sealed":
        raise cm.Refused("h9_flow is not sealed; W1 cannot have advanced")
    n_listed = verify_holdout_listing(inp0["rdir"], inp0["seal"])
    inp = verify_inputs(hist_root, flow_sha, fp, seals_dir, is_committed, holdout=True)
    h5_seal.log_access(inp["rdir"], "cb8_rep_W", ["holdout/*", "sample.csv.gz", "days.csv.gz", "drops.csv.gz"])
    view = FlowView(inp["rdir"], "holdout", holdout_unlocked=True)
    st = build_stage(view, "replicate")
    k = wc.stage2_k(out_root, TEST)
    alpha = wc.ALPHA2 / k["k_used"]
    cum = wc.cumulative(trials_path)
    res = evaluate_w1(st, alpha=alpha, disjointness=(inp["seal"].get("drops") or {}).get("disjointness"), cumulative=cum)
    res["split"] = "holdout"
    res["stage2_holm"] = {**k, "alpha2": wc.ALPHA2, "alpha_used": alpha, "label": "sealed same-calendar holdout replication (L2)" if res["advance"] else None}
    doc = {"test": f"{TEST}-rep", "stage": 2, "rules_version": RULES_VERSION, RULES_KEY: analysis_rules_sha, DATA_KEY: flow_sha, "wallet_key_fingerprint": fp,
           "freeze_spec_sha256": freeze_sha, "stage1_sha256": h5_seal.sha256_file(seals_dir / STAGE1_COPY_NAME), "stage1_p": s1.get("p"),
           "holdout_listing_sha256": (inp["seal"].get("drops") or {}).get("holdout_listing_sha256"), "n_holdout_files_verified": n_listed,
           "inputs": {k_: v for k_, v in inp.items() if k_ not in ("seal", "rdir")}, "evidence_role": wc.EVIDENCE_ROLE, "label": wc.LABEL, "run_utc": wc.now_iso(),
           "interpretations": list(INTERPRETATIONS), **res, "opened_files_n": len(set(view.opened)),
           "disclosure": "the event-split holdout is a selection guard only (same calendar and regimes); Stage P-W is the out-of-time check"}
    sha = wc.write_results(out_p, doc)
    wc.log_trials(res, family=FAMILY, test=TEST, replication=True, results_path=out_p, results_sha=sha, rules_key=RULES_KEY, rules_sha=analysis_rules_sha,
                  freeze_sha=freeze_sha, trials_path=trials_path, placebo_key="placebo_time_shift", descriptive=_descriptive(res))
    return {"status": "replicate_W_complete", "pass": res["advance"], "p": res["p"], "alpha_used": alpha, "testable": res["testable"], "verdict": res["verdict"],
            "results_sha256": sha, "written": str(out_p)}


# ---- rules file -----------------------------------------------------------------------------------------------------------------------------------------------


def declared() -> dict:
    return {
        "scope": "CB8-W analysis: census (q0169 W part), W1 Stage 1 (q0171), W1-rep Stage 2 (q0175)",
        "definitions": {"clip_gap_s": CLIP_GAP_S, "trigger_gap_s": list(TRIG_GAP_S), "size_ratio": list(SIZE_RATIO), "min_notional": MIN_NOTIONAL, "run_start_s": RUN_START_S,
                        "opp_lookback_s": OPP_LOOKBACK_S, "lag_s": LAG_S, "base_s": BASE_S, "cap_s": CAP_S, "usable": list(USABLE), "mark_half_s": MARK_HALF_S,
                        "horizon_s": HORIZON_S, "unit_window_s": UNIT_WINDOW_S, "rebate_from": REBATE_FROM},
        "decision": {"sign": SIGN, "alpha1": wc.ALPHA1, "alpha2": wc.ALPHA2, "by_q": wc.BY_Q, "batch_holm_k1": wc.BATCH_HOLM_K1, "floor": -wc.EDGE_FLOOR,
                     "min_units": wc.MIN_UNITS, "min_event_clusters": wc.MIN_EVENT_CLUSTERS, "g_min": wc.G_MIN, "ways": ["event", "day (A-C1)", "trigger wallet"],
                     "n_boot": wc.N_BOOT, "seed_boot": wc.SEED_BOOT, "n_wild": wc.N_WILD, "route_gate": "mean mark-out of N u S' >= 0 (no rebate)"},
        "gw": {"min_S_marked": GW_MIN_S_MARKED, "min_windows": GW_MIN_WINDOWS, "min_events": GW_MIN_EVENTS, "min_days": GW_MIN_DAYS, "min_wallets": GW_MIN_WALLETS},
        "placebo": {"time_shift": {"draws": wc.PLACEBO_DRAWS, "seed": SEED_TIMESHIFT, "range_s": list(SHIFT_RANGE_S), "max_rate": wc.PLACEBO_MAX_RATE},
                    "wallet_attribution": {"share": wc.ATTRIBUTION_SHARE}},
        "robustness": {"alt_horizons_s": list(ALT_HORIZONS_S), "top_k": wc.TOP_K, "month_min_units": MONTH_MIN_UNITS, "month_sign_share": wc.MONTH_SIGN_SHARE,
                       "half": wc.HALF, "lag_robust_s": LAG_ROBUST_S, "worst_case": "mark-unavailable S units at max(0, kept-fill mean) + rebate"},
        "reported": {"continuation_s": CONTINUATION_S, "seq_min_clips": SEQ_MIN_CLIPS, "seq_cv_max": SEQ_CV_MAX, "reversal_s": [REVERSAL_FROM_S, REVERSAL_TO_S],
                     "report_horizon_s": REPORT_HORIZON_S, "stratum_gap_days": STRATUM_GAP_DAYS},
        "mde": {"se_ref": MDE_SE_REF, "g_ref_events": MDE_G_REF, "power": wc.MDE_POWER, "alpha": wc.ALPHA1},
        "outputs": {"census": CENSUS_NAME, "stage1": RESULTS_S1, "stage2": RESULTS_S2, "stage1_copy": STAGE1_COPY_NAME, "output_cap_gb": wc.OUTPUT_CAP_GB},
        "wallet_key_fingerprint": WALLET_KEY_FP,
        "freeze": f"screen and replicate need a committed model_specs/cb8_v1.json carrying {RULES_KEY} and {DATA_KEY} equal to the code's",
        "interpretations": list(INTERPRETATIONS),
    }


def data_rules_sha() -> str:
    return cm.rules_file_doc("flow", WALLET_KEY_FP)["rules_sha256"]


def rule_funcs() -> list:
    own = [declared, data_rules_sha, _day, rebate, reach_s, UnionFind.find, UnionFind.union, verify_inputs, verify_holdout_listing, holdout_counts,
           FlowView.__init__, FlowView._note, FlowView.dropped, FlowView.sample_all, FlowView.sample, FlowView.day_status, FlowView.split_report, FlowView.prints,
           Market.observable, load_market, clips, _clip_ok_pair, _extend, triggers, pseudo_triggers, merge_windows, shift_windows, classify, _cum,
           MarkIndex.__init__, MarkIndex._wallet, MarkIndex._sums, MarkIndex.available, MarkIndex.values, _groups, unit_marks, build_stage, _windows, collect_units,
           gw_gate, census_w, _test, time_shift_placebo, evaluate_w1, robustness, reported, sequence_reversal, run_census, _not_testable_doc, screen_w, _descriptive,
           replicate_w]
    deps = [F.event_key, F.day_segments, h5_seal.list_files, h5_seal.listing_sha256, h5_seal.sha256_file, h5_seal.declaration_sha256, h5_seal.log_access]
    return own + deps + wc.rule_funcs()


def rules_file_doc() -> dict:
    return wc.make_rules_doc(RULES_VERSION, declared(), data_rules_sha(), rule_funcs())


def write_rules(path: Path | None = None) -> Path:
    return wc.write_rules_file(Path(path or RULES_FILE), rules_file_doc())


def verify_analysis_rules(path: Path | None = None, *, require_committed: bool = True) -> str:
    return wc.verify_rules_file(Path(path or RULES_FILE), rules_file_doc(), "W analysis", require_committed=require_committed)


def require_freeze(spec_path: Path | None, analysis_sha: str, data_sha: str, *, require_committed: bool = True) -> str:
    return wc.require_freeze(spec_path, {RULES_KEY: analysis_sha, DATA_KEY: data_sha}, require_committed=require_committed)
