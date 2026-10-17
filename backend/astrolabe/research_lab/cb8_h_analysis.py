# ruff: noqa: E501
"""CB8-H analysis side (docs/research_lab/CREATIVE_BATCH_8.md 2.3-2.7, CB8-H "Definitions" .. "Stop rule", 4, 5.1): the window-1 census (q0172), the H1
Stage-1 screen on window 1 (q0173) and H1-rep on window 2 (q0176, post-freeze, out of time).

PROSPECTIVE DATA, EXPLORATORY ANALYSIS ONLY: no edge, calibration or profitability claim. Even a full pass supports only a PRESENCE FILTER for makers, not a
trading route (a maker cannot target an exit). Access rules:
- Inputs are the q0162 snapshot run (``holders/snap``) and the q0163 prints run (``holders/prints``); both manifests must carry the binding holders rules
  hash (v3) and the pinned wallet-key fingerprint, and every file read is re-hashed against its manifest. Only the market-days of the stage's window are
  read (window 1: ``[T8_H1_start, T8_H1_end)``; window 2: ``[T8_H2_start, T8_H2_end)`` from ``h2_pin.json``).
- Capture marks are the target. The census reads them only through :class:`MarkBook` built for the purpose ``census``, which answers availability (first
  capture within 2.5 h, spread <= 5c) and refuses mids; no mark-out, contrast or route value is computed by the census.
- ``census`` refuses before ``T8_H1_end`` + 30 h; ``replicate`` refuses unless the committed Stage-1 copy shows H1 advanced, before ``T8_H2_end`` + 30 h, and
  records "not run (freeze slip)" (counted) when the window-2 pin says so.

The rules of this module are hashed into ``seals/cb8_h_analysis_rules.json`` (``cb8-h-analysis-rules-v1``); the holders data rules
(``seals/cb8_holders_rules_v3.json``) are untouched. Readings taken where the design is silent are in ``INTERPRETATIONS``.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import cb8_b_analysis as ba
from . import cb8_common as cm
from . import cb8_holders as H
from . import cb8_wh_common as wc
from . import h5_seal

RULES_VERSION = "cb8-h-analysis-rules-v2"  # v2: embeds the holders data rules v4 hash (H-v4); the v1 file (embeds v3 b6ac7f7f) is superseded, never rewritten
RULES_FILE_V1 = cm.SEALS_DIR / "cb8_h_analysis_rules.json"
RULES_FILE = cm.SEALS_DIR / "cb8_h_analysis_rules_v2.json"
WALLET_KEY_FP = "80ce5e81a539a570"  # pinned in seals/cb8_holders_rules_v4.json (and v3, and every CB8 manifest) (and every CB8 manifest)
TEST = "H1"
FAMILY = "H"
RULES_KEY = "h_analysis_rules_sha256"
DATA_KEY = "h_data_rules_sha256"
STAGE1_COPY_NAME = "cb8_h1_stage1.json"
CENSUS_NAME, RESULTS_S1, RESULTS_S2 = "census_H.json", "results_H1.json", "results_H1_rep.json"
SIGN = 1  # H1 > 0: exits are cheaper for the maker to buy than matched other sells

# ---- declared values (CREATIVE_BATCH_8.md CB8-H, 2.1, 2.6, 2.7) ---------------------------------------------------------------------------------------------
CONC_MIN = H.CONC_MIN  # 0.5
CONC_LOW = 0.2  # H1_low: rank-1 exits with c < 0.2
EXIT_FROM_S, EXIT_FROM_ROBUST_S = 60, 900
EXIT_TO_S = 24 * 3600
USABLE = (0.03, 0.97)
CONTROL_WINDOW_S = 6 * 3600
SIZE_BANDS = ((0.5, 2.0), (0.25, 4.0))
TOP_EXCLUDED = 5
HORIZON_S = 7200
MARK_WINDOW_S = 2.5 * 3600
MARK_MAX_SPREAD = 0.05
READY_AFTER_END_S = 30 * 3600
SEED_SHUFFLE = 8183
GH_MIN_PAIRS, GH_MIN_EVENTS, GH_MIN_DAYS, GH_MIN_HOLDERS = 150, 50, 15, 30
MONTH_MIN_UNITS = 50  # reported, not binding for H (2.6 iv)
REPORTED_RANKS = (2, 3)
MDE_SD, MDE_DEFF = 0.06, 2.0  # design: SD of the paired difference about 6c, deff about 2
EPS = 1e-12

INTERPRETATIONS = (
    "Market-days: snapshot rows with status 'ok' whose snapshot time h lies in the stage's window; the print request status must be 'ok' (capped / failed -> "
    "unavailable, counted). c_j is recomputed from the stored top-20 holders and the stored /oi value at t_f with cb8_holders.concentration (the hashed data rule).",
    "Exit: taker SELL (side -1) of token j by the rank-1 holder of j at h, ts in (h + 60 s, h + 24 h], c_j >= 0.5, token price in [0.03, 0.97]. A print that "
    "qualifies under two consecutive snapshots (overlapping windows) is ONE exit, kept with the earliest snapshot.",
    "Control: from the exit's own market-day stored prints (stored in full because c_j >= 0.5): taker SELL of token j, price in [0.03, 0.97] (the exit's price "
    "rule, applied to controls too), wallet hash present and not among the top-5 holders of either token at h, |ts - ts_exit| <= 6 h; nearest in time within "
    "0.5x-2x of the exit's size, else within 0.25x-4x, else none (exit excluded, counted); ties by earlier ts; without replacement per market, exits in time order.",
    "Mark M_j(u): the FIRST complete capture of the market-day's marks with received_utc in [u, u + 2.5 h]; if its spread (ask - bid of YES) exceeds 5c or a "
    "quote is missing, the mark is unavailable (the literal 'spread <= 5c at that capture'; no search for a tighter later capture). Token 1 mid = 1 - YES mid.",
    "mo(x) = M_j(ts_x + 2 h) - p_x; unit = matched pair, value mo(exit) - mo(control); a pair with either mark unavailable is unavailable (counted; worst case).",
    "Cluster ways: Gamma event (event id, else market id), UTC day of the exit, holder (exit wallet hash). Day way under A-C1.",
    "Route gate (binding at the point estimate): mean mo(exit) >= +0.5c with no rebate. The with-rebate version is NOT computable: the H data store no fee "
    "category (reported as unavailable).",
    "GH (>= 150 matched exits with both marks, >= 50 events, >= 15 days, >= 30 holders; non-sports) is applied at both stages on the stage's own units; a fail -> "
    "not testable, p = 1, counted; no window extension. If no rank-1 hash of a concentrated token ever appears among the stored print wallets -> not testable (source).",
    "Label-shuffle placebo: one fair coin per holder x market x snapshot-day block flips the sign of every pair in the block (label swap); advance = the p "
    "condition (floor off); 200 draws, seed 8183; calibrated iff the advance rate <= 1.5%.",
    "Concentration attribution: H1_low = the same contrast for rank-1 exits of tokens with c < 0.2. Controls exist only where the market-day was stored in full "
    "(the other token had c >= 0.5), so H1_low may have few or no units; none -> unverified (never credited; does not block).",
    "Robustness (i): the next-but-one capture as the mark (the SECOND capture with received_utc >= u in the market-day's marks, spread <= 5c at that capture); "
    "sign and >= half of H1. (ii) top 5 events / days dropped: p condition and floor. (iii) exit-size-weighted sign. (iv) months with >= 50 pairs: reported only. "
    "(v) worst case: unavailable pairs enter with contrast 0; sign and p condition. (vi) exits only from h + 15 min (controls re-matched): sign and >= half of H1.",
    "Stage 2 uses p < alpha2 / k_used wherever Stage 1 uses 0.01; k_used = 1 + the other CB8 tests that advanced or have no final Stage-1 file yet. Window 2 must "
    "start at or after the first commit of the freeze spec + 2 h (checked when committed files are required).",
    "BY triage label: p <= q / (m H_m), m = battery2.cumulative_count() at run time. Batch-Holm label k1 = 3, alpha 0.01; tests without a final file enter as p = 1.",
    "MDE: (z_0.99 + z_0.80) x 6c x sqrt(2 / n_pairs) (design SD and deff); never used to change a floor.",
)


# ---- small helpers ------------------------------------------------------------------------------------------------------------------------------------------


def _f(x) -> float | None:
    return ba._f(x)


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(int(ts)))


def _days_between(a: float, b: float) -> list[str]:
    out, t = [], int(a // cm.DAY * cm.DAY)
    while t < b:
        out.append(_day(t))
        t += int(cm.DAY)
    return out


def _fp(r: dict) -> tuple:
    return (r["market_id"], r["ts"], r["token_idx"], r["side"], r["price"], r["size"], r["wallet"])


# ---- windows, inputs ----------------------------------------------------------------------------------------------------------------------------------------


def window_of(holders_dir: Path, stage: int) -> dict:
    """Window 1 from ``snap/t8_h1_start.json``; window 2 from ``h2_pin.json`` (freeze-slip flag included)."""
    pins = H.read_pins(holders_dir)
    if not pins:
        raise cm.Refused("window 1 is not pinned (no snapshot has run)")
    if stage == 1:
        return {"stage": 1, "start": cm.ep(pins["t8_h1_start_utc"]), "end": float(pins["h1_end_epoch"]), "freeze_slip": False}
    p = Path(holders_dir) / "h2_pin.json"
    if not p.exists():
        raise cm.Refused("window 2 is not pinned (holders-pin-h2 after the CB8 freeze commit + 2 h)")
    d = json.loads(p.read_text())
    return {"stage": 2, "start": float(d["h2_start_epoch"]), "end": float(d["h2_end_epoch"]), "freeze_slip": bool(d.get("freeze_slip")), "pinned_epoch": d.get("pinned_epoch")}


def require_ready(win: dict, now: float) -> None:
    if now < win["end"] + READY_AFTER_END_S:
        raise cm.NotNow(f"window {win['stage']} ends at {cm.iso(win['end'])}; its analysis waits until end + 30 h ({cm.iso(win['end'] + READY_AFTER_END_S)})")


def _manifest(rdir: Path, holders_sha: str, fp: str) -> dict:
    mp = Path(rdir) / "manifest.json"
    if not mp.exists():
        raise cm.Refused(f"{Path(rdir).name} run has no manifest")
    man = json.loads(mp.read_text())
    if man.get("rules_sha256") != holders_sha:
        raise cm.Refused(f"{Path(rdir).name} manifest rules hash {man.get('rules_sha256')} != holders rules {holders_sha}")
    if man.get("wallet_key_fingerprint") != fp or fp != WALLET_KEY_FP:
        raise cm.Refused(f"{Path(rdir).name} wallet_key_fingerprint differs from the pin; mixed fingerprints are refused")
    return man


# ---- field-restricted access --------------------------------------------------------------------------------------------------------------------------------


class HoldersView:
    """Market-days of ONE window. Every file read is re-hashed against its run manifest. Marks are reachable only through :meth:`markbook`."""

    def __init__(self, holders_dir: Path, win: dict, holders_sha: str, fp: str) -> None:
        self.dir = Path(holders_dir)
        cm.refuse_path(self.dir)
        self.win = win
        self.snap, self.prints_dir = self.dir / H.SNAP_RUN, self.dir / H.PRINTS_RUN
        self.snap_man = _manifest(self.snap, holders_sha, fp)
        self.prints_man = _manifest(self.prints_dir, holders_sha, fp)
        self.opened: list[str] = []

    def _read(self, rdir: Path, man: dict, rel: str) -> list[dict]:
        p = rdir / rel
        want = (man.get("file_sha256") or {}).get(rel)
        if want is None or not p.is_file() or h5_seal.sha256_file(p) != want:
            raise cm.Refused(f"{rdir.name}/{rel} is missing, unlisted or differs from its manifest")
        self.opened.append(f"{rdir.name}/{rel}")
        return list(ba.c7.read_csv_gz(p))

    def days(self) -> list[str]:
        return _days_between(self.win["start"], self.win["end"])

    def day_markers(self) -> dict:
        out = {"missed": [], "incomplete": [], "no_snapshot": []}
        for d in self.days():
            if (self.snap / f"{d}.MISSED.json").exists():
                out["missed"].append(d)
            elif (self.snap / f"{d}.INCOMPLETE.json").exists():
                out["incomplete"].append(d)
            if not (self.snap / f"{d}.markets.csv.gz").exists():
                out["no_snapshot"].append(d)
        return out

    def snapshot(self, day: str) -> tuple[list[dict], list[dict]]:
        if not (self.snap / f"{day}.markets.csv.gz").exists():
            return [], []
        mk = [r for r in self._read(self.snap, self.snap_man, f"{day}.markets.csv.gz") if self.win["start"] <= float(r["h_epoch"]) < self.win["end"]]
        if not mk:
            return [], []
        ids = {r["market_id"] for r in mk}
        hold = [r for r in self._read(self.snap, self.snap_man, f"{day}.holders.csv.gz") if r["market_id"] in ids]
        return mk, hold

    def prints_status(self, day: str) -> dict[str, dict] | None:
        if not (self.prints_dir / f"{day}.markets.csv.gz").exists():
            return None
        return {r["market_id"]: r for r in self._read(self.prints_dir, self.prints_man, f"{day}.markets.csv.gz")}

    def prints(self, day: str) -> list[dict]:
        rows = self._read(self.prints_dir, self.prints_man, f"prints/{day}.csv.gz")
        out = []
        for r in rows:
            out.append({"market_id": r["market_id"], "ts": int(float(r["ts"])), "token_idx": int(float(r["token_idx"])), "side": int(float(r["side"])),
                        "price": float(r["price"]), "size": float(r["size"]), "wallet": r.get("wallet_hash") or "", "stored_reason": r.get("stored_reason", "")})
        return out

    def markbook(self, day: str, purpose: str) -> MarkBook:
        rows = self._read(self.prints_dir, self.prints_man, f"marks/{day}.csv.gz")
        return MarkBook(rows, purpose)

    def window_record(self, day: str) -> dict | None:
        """The capture-window accounting of a prints day (expected window, earliest capture available, unreadable captures); hashed like every input."""
        rel = f"marks/{day}.window.json"
        p = self.prints_dir / rel
        if not p.exists():
            return None
        want = (self.prints_man.get("file_sha256") or {}).get(rel)
        if want is None or h5_seal.sha256_file(p) != want:
            raise cm.Refused(f"{self.prints_dir.name}/{rel} is unlisted or differs from its manifest")
        self.opened.append(f"{self.prints_dir.name}/{rel}")
        return json.loads(p.read_text())

    def prints_terminal(self) -> bool:
        return self.prints_man.get("status") in (H.PRINTS_COMPLETE, cm.DISK_BUDGET_TOKEN)


class MarkBook:
    """Capture marks of one prints day. For the purpose ``census`` it answers availability only; mids exist only for ``screen`` / ``replicate``."""

    def __init__(self, rows: list[dict], purpose: str) -> None:
        self.purpose = purpose
        self.valued = purpose in wc.GUARDED_PURPOSES
        by: dict[str, list[tuple[float, float | None, float | None]]] = {}
        for r in rows:
            t = cm.c4._parse_ts(r.get("received_utc")) if r.get("received_utc") else None
            if t is None:
                continue
            by.setdefault(r["market_id"], []).append((t, _f(r.get("best_bid")), _f(r.get("best_ask"))))
        self._by = {k: sorted(v, key=lambda x: x[0]) for k, v in by.items()}

    def _pick(self, mid: str, u: float, nth: int, window: float | None) -> tuple | None:
        rows = [x for x in self._by.get(mid, []) if x[0] >= u and (window is None or x[0] <= u + window)]
        if len(rows) < nth:
            return None
        t, b, a = rows[nth - 1]
        if b is None or a is None or a < b or a - b > MARK_MAX_SPREAD + EPS:
            return None
        return (t, b, a)

    def available(self, mid: str, u: float, *, nth: int = 1) -> bool:
        return self._pick(mid, u, nth, MARK_WINDOW_S if nth == 1 else None) is not None

    def mid(self, mid: str, j: int, u: float, *, nth: int = 1) -> float | None:
        """Token-j mid at the first (``nth`` = 1, within 2.5 h) or next-but-one (``nth`` = 2) capture; screen / replicate only."""
        if not self.valued:
            raise cm.Refused(f"capture mids are read only by {wc.GUARDED_PURPOSES}, not {self.purpose!r}")
        x = self._pick(mid, u, nth, MARK_WINDOW_S if nth == 1 else None)
        if x is None:
            return None
        m = (x[1] + x[2]) / 2.0
        return m if j == 0 else 1.0 - m

    def spreads(self, mid: str) -> list[float | None]:
        if not self.valued:
            raise cm.Refused("spreads are read only by screen / replicate")
        return [(a - b) if (a is not None and b is not None) else None for _, b, a in self._by.get(mid, [])]


# ---- market-days, exits, controls ------------------------------------------------------------------------------------------------------------------------


def market_days(view: HoldersView) -> tuple[list[dict], dict]:
    """Every snapshot market-day of the window with its holders, c_j, top-5 set, print status and stored prints (no mark)."""
    out, counts = [], {"snapshot_rows": 0, "snapshot_ok": 0, "prints_missing_day": 0, "by_prints_status": {}, "oi_below_sum": 0, "snapshots_per_day": {}}
    for day in view.days():
        mk, hold = view.snapshot(day)
        if not mk:
            continue
        counts["snapshot_rows"] += len(mk)
        by_m: dict[str, list[list]] = {}
        for r in hold:
            by_m.setdefault(r["market_id"], []).append([int(float(r["token_idx"])), int(float(r["rank"])), r["wallet_hash"], float(r["amount"])])
        pst = view.prints_status(day)
        prints = view.prints(day) if pst is not None else []
        pr_by: dict[str, list[dict]] = {}
        for p in prints:
            pr_by.setdefault(p["market_id"], []).append(p)
        n_ok = 0
        for r in mk:
            if r.get("status") != "ok":
                continue
            n_ok += 1
            rows = by_m.get(r["market_id"], [])
            conc = H.concentration(rows, _f(r.get("oi_tf")) if _f(r.get("oi_tf")) is not None else float("nan"))
            counts["oi_below_sum"] += int(conc["oi_below_sum"])
            ranks = {(x[0], x[1]): x[2] for x in rows}
            top5 = {x[2] for x in rows if x[1] <= TOP_EXCLUDED}
            ps = (pst or {}).get(r["market_id"])
            st = ps["status"] if ps else ("prints_day_missing" if pst is None else "not_in_prints_day")
            counts["by_prints_status"][st] = counts["by_prints_status"].get(st, 0) + 1
            out.append({"market_id": r["market_id"], "event": r.get("event_id") or f"m{r['market_id']}", "group": r.get("group") or "", "day": day,
                        "h": float(r["h_epoch"]), "c": {0: conc["c0"], 1: conc["c1"]}, "ranks": ranks, "top5": top5, "prints_status": st,
                        "stored_all": bool(ps and str(ps.get("stored_all")) in ("1", "1.0", "True", "true")), "prints": pr_by.get(r["market_id"], []) if st == "ok" else []})
        counts["snapshot_ok"] += n_ok
        counts["snapshots_per_day"][day] = n_ok
        if pst is None:
            counts["prints_missing_day"] += 1
    return out, counts


def _usable(p: dict) -> bool:
    return USABLE[0] <= p["price"] <= USABLE[1]


def exits(mds: list[dict], *, group: str, rank: int = 1, c_rule: Callable[[float], bool] = lambda c: c >= CONC_MIN, exit_from: int = EXIT_FROM_S) -> list[dict]:
    """Taker SELLs of token j by the rank-``rank`` holder of j at h with ts in (h + exit_from, h + 24 h], c_j passing ``c_rule``, price usable. Deduplicated across
    overlapping snapshot windows (the earliest snapshot keeps the print)."""
    out, seen = [], set()
    for md in sorted((m for m in mds if m["group"] == group and m["prints_status"] == "ok"), key=lambda m: (m["market_id"], m["h"])):
        for j in (0, 1):
            c = md["c"][j]
            w = md["ranks"].get((j, rank))
            if w is None or not (isinstance(c, float) and c == c and c_rule(c)):
                continue
            for p in md["prints"]:
                if p["token_idx"] != j or p["side"] != -1 or p["wallet"] != w or not (md["h"] + exit_from < p["ts"] <= md["h"] + EXIT_TO_S) or not _usable(p):
                    continue
                k = _fp(p)
                if k in seen:
                    continue
                seen.add(k)
                out.append({**p, "md": md, "j": j, "c": c, "holder": w})
    return sorted(out, key=lambda e: (e["market_id"], e["ts"], e["j"], e["size"], e["price"]))


def match_controls(ex: list[dict]) -> tuple[list[tuple[dict, dict]], int]:
    """Nearest-in-time size-banded controls without replacement (per market, exits in time order). Returns (pairs, exits without a control)."""
    used: set = set()
    pairs, none = [], 0
    for e in ex:
        md = e["md"]
        pool = [p for p in md["prints"] if p["token_idx"] == e["j"] and p["side"] == -1 and p["wallet"] and p["wallet"] not in md["top5"] and _usable(p)
                and abs(p["ts"] - e["ts"]) <= CONTROL_WINDOW_S and _fp(p) not in used]
        best = None
        for lo, hi in SIZE_BANDS:
            cand = [p for p in pool if e["size"] > 0 and lo <= p["size"] / e["size"] <= hi]
            if cand:
                best = min(cand, key=lambda p: (abs(p["ts"] - e["ts"]), p["ts"], _fp(p)))
                break
        if best is None:
            none += 1
            continue
        used.add(_fp(best))
        pairs.append((e, best))
    return pairs, none


def pair_units(pairs: list[tuple[dict, dict]], books: dict[str, MarkBook], *, values: bool, nth: int = 1) -> list[dict]:
    """One unit per pair; with ``values`` the contrast mo(exit) - mo(control) (screen / replicate only), otherwise availability only (census)."""
    out = []
    for e, c in pairs:
        md = e["md"]
        mb = books[md["day"]]
        u = {"market_id": e["market_id"], "event": md["event"], "day": _day(e["ts"]), "month": _day(e["ts"])[:7], "holder": e["holder"],
             "block": f"{e['holder']}|{e['market_id']}|{md['day']}", "size": e["size"], "c": e["c"]}
        if values:
            me, mc = mb.mid(e["market_id"], e["j"], e["ts"] + HORIZON_S, nth=nth), mb.mid(e["market_id"], e["j"], c["ts"] + HORIZON_S, nth=nth)
            u["avail"] = me is not None and mc is not None
            if u["avail"]:
                u["mo_exit"], u["mo_control"] = me - e["price"], mc - c["price"]
                u["v"] = u["mo_exit"] - u["mo_control"]
        else:
            u["avail"] = mb.available(e["market_id"], e["ts"] + HORIZON_S, nth=nth) and mb.available(e["market_id"], c["ts"] + HORIZON_S, nth=nth)
        out.append(u)
    return out


def hash_join(mds: list[dict]) -> dict:
    """How many rank-1 hashes of concentrated tokens appear among the stored print wallets of their market-day (any side or token)."""
    r1, joined = set(), set()
    for md in mds:
        wallets = {p["wallet"] for p in md["prints"] if p["wallet"]}
        for j in (0, 1):
            c, w = md["c"][j], md["ranks"].get((j, 1))
            if w is None or not (isinstance(c, float) and c == c and c >= CONC_MIN) or md["prints_status"] != "ok":
                continue
            r1.add(w)
            if w in wallets:
                joined.add(w)
    return {"n_rank1_hashes": len(r1), "n_joined": len(joined), "ok": bool(joined)}


def gh_gate(units: list[dict]) -> dict:
    av = [u for u in units if u["avail"]]
    n_ev, n_day, n_h = len({u["event"] for u in av}), len({u["day"] for u in av}), len({u["holder"] for u in av})
    ok = len(av) >= GH_MIN_PAIRS and n_ev >= GH_MIN_EVENTS and n_day >= GH_MIN_DAYS and n_h >= GH_MIN_HOLDERS
    return {"ok": bool(ok), "n_pairs_with_marks": len(av), "n_events": n_ev, "n_days": n_day, "n_holders": n_h,
            "thresholds": [GH_MIN_PAIRS, GH_MIN_EVENTS, GH_MIN_DAYS, GH_MIN_HOLDERS], "fail_label": None if ok else "not testable (GH failed; no window extension)"}


def mde(n_pairs: int) -> float | None:
    if n_pairs <= 0:
        return None
    return float(wc._mde_z() * MDE_SD * math.sqrt(MDE_DEFF / n_pairs))


def _books(view: HoldersView, mds: list[dict], purpose: str) -> dict[str, MarkBook]:
    return {d: view.markbook(d, purpose) for d in sorted({m["day"] for m in mds if m["prints_status"] == "ok"})}


# ---- census (q0172): counts only ---------------------------------------------------------------------------------------------------------------------------


def census_h(holders_dir: Path, *, holders_sha: str, fp: str, analysis_rules_sha: str, now: float) -> dict:
    """Window-1 counts only. Refuses before T8_H1_end + 30 h; waits (exit 75) while window-1 print days are still missing and the prints run is not terminal."""
    win = window_of(holders_dir, 1)
    require_ready(win, now)
    view = HoldersView(holders_dir, win, holders_sha, fp)
    mds, counts = market_days(view)
    if counts["prints_missing_day"] and not view.prints_terminal():
        raise cm.NotNow(f"{counts['prints_missing_day']} window-1 snapshot day(s) have no prints day yet")
    books = _books(view, mds, "census")
    out: dict = {"census": "CB8-H window-1 census (counts only; no mark value, mark-out or contrast)", "rules_version": RULES_VERSION, RULES_KEY: analysis_rules_sha,
                 DATA_KEY: holders_sha, "wallet_key_fingerprint": fp, "window": {k: (cm.iso(v) if k in ("start", "end") else v) for k, v in win.items()},
                 "evidence_role": "prospective", "label": wc.LABEL}
    out["snapshots"] = {**{k: v for k, v in counts.items() if k != "oi_below_sum"}, "day_markers": view.day_markers(),
                        "oi_inconsistency_share": (counts["oi_below_sum"] / counts["snapshot_ok"]) if counts["snapshot_ok"] else None}
    for group, name in (("main", "non_sports"), ("sports", "sports_stratum")):
        g = [m for m in mds if m["group"] == group]
        ex = exits(mds, group=group)
        pairs, none = match_controls(ex)
        units = pair_units(pairs, books, values=False)
        out[name] = {"market_days": len(g), "concentrated_market_days": sum(1 for m in g if any(isinstance(m["c"][j], float) and m["c"][j] >= CONC_MIN for j in (0, 1))),
                     "rank1_exits": len(ex), "exits_with_control": len(pairs), "exits_without_control": none,
                     "exits_with_control_and_both_marks": sum(1 for u in units if u["avail"]), "gate": gh_gate(units)}
    gh = out["non_sports"]["gate"]
    out["hash_join"] = hash_join([m for m in mds if m["group"] == "main"])
    wins = [w for w in (view.window_record(d) for d in sorted({m["day"] for m in mds if m["prints_status"] == "ok"})) if w]
    out["capture_windows"] = {"days": len(wins), "window_start_not_covered": sum(1 for w in wins if w.get("window_start_covered") is False),
                              "captures_unreadable": sum(int(w.get("captures_unreadable") or 0) for w in wins)}
    out["gate_GH"] = {**gh, "hash_join_ok": out["hash_join"]["ok"], "ok": bool(gh["ok"] and out["hash_join"]["ok"]),
                      "fail_label": None if (gh["ok"] and out["hash_join"]["ok"]) else (gh["fail_label"] or "not testable (source): no rank-1 hash joins a print wallet")}
    out["mde_H1"] = {"mde": mde(gh["n_pairs_with_marks"]), "assumptions": {"sd": MDE_SD, "deff": MDE_DEFF}, "n": gh["n_pairs_with_marks"],
                     "note": "never used to change a floor, window or threshold"}
    out["opened_files_n"] = len(set(view.opened))
    out["interpretations"] = list(INTERPRETATIONS)
    return ba._clean(out)


# ---- evaluation (screen and replicate) ---------------------------------------------------------------------------------------------------------------------


def _test(units: list[dict], alpha: float | None = None, val: str = "v") -> dict:
    return wc.ways_test([u[val] for u in units], [u["event"] for u in units], [u["day"] for u in units], {"holder": [u["holder"] for u in units]},
                        sign=SIGN, alpha=alpha)


def label_shuffle_placebo(units: list[dict], *, alpha: float, draws: int = wc.PLACEBO_DRAWS, seed: int = SEED_SHUFFLE) -> dict:
    if not units:
        return {**wc.placebo_summary(0, 0, seed), "n_draws": 0}
    blocks = sorted({u["block"] for u in units})
    bi = np.array([blocks.index(u["block"]) for u in units])
    v = np.array([u["v"] for u in units])
    rng = np.random.default_rng(seed)
    adv = 0
    for _ in range(draws):
        flip = np.where(rng.random(len(blocks)) < 0.5, -1.0, 1.0)[bi]
        t = wc.ways_test(v * flip, [u["event"] for u in units], [u["day"] for u in units], {"holder": [u["holder"] for u in units]}, sign=SIGN, alpha=alpha)
        adv += int(wc.p_ok(t, alpha))
    return wc.placebo_summary(adv, draws, seed)


def evaluate_h1(view: HoldersView, purpose: str, *, alpha: float, cumulative: int) -> dict:
    res: dict = {"alpha": alpha, "floor": wc.EDGE_FLOOR}
    mds, counts = market_days(view)
    books = _books(view, mds, purpose)
    main = [m for m in mds if m["group"] == "main"]
    ex = exits(mds, group="main")
    pairs, none = match_controls(ex)
    all_units = pair_units(pairs, books, values=True)
    units = [u for u in all_units if u["avail"]]
    unav = [u for u in all_units if not u["avail"]]
    gh = gh_gate(all_units)
    hj = hash_join(main)
    res.update(counts={**{k: v for k, v in counts.items() if k != "snapshots_per_day"}, "rank1_exits": len(ex), "exits_without_control": none, "pairs": len(all_units),
                       "pairs_unavailable": len(unav)}, gate_GH=gh, hash_join=hj)
    blockers = []
    if not gh["ok"]:
        blockers.append(gh["fail_label"])
    if not hj["ok"]:
        blockers.append("not testable (source): no rank-1 hash joins a print wallet")
    t = _test(units)
    t["ci95_event_bootstrap"] = ba.boot_ci([u["v"] for u in units], [u["event"] for u in units]) if units else None
    res["H1"] = t
    me = [u["mo_exit"] for u in units]
    rm = float(np.mean(me)) if me else math.nan
    res["route_gate"] = {"n": len(me), "mean_mo_exit": rm, "ok": bool(me and rm >= wc.EDGE_FLOOR), "with_rebate": "not computable (no fee category in the H data)",
                         "reading": "even a pass supports only a presence filter for makers, not a standalone route"}
    testable = bool(t["testable"]) and not blockers
    res["placebo_label_shuffle"] = label_shuffle_placebo(units, alpha=alpha) if testable else {"skipped": "not testable"}
    lo_ex = exits(mds, group="main", c_rule=lambda c: c < CONC_LOW)
    lo_units = [u for u in pair_units(match_controls(lo_ex)[0], books, values=True) if u["avail"]]
    res["concentration_attribution"] = wc.attribution(t["mean"], [u["v"] for u in lo_units], SIGN,
                                                      ("concentration credited", "top-holder exits are cheap whatever the concentration"), "concentration")
    rob = robustness(mds, books, pairs, units, unav, t["mean"], alpha=alpha) if testable else {}
    res["robustness"] = rob
    res["reported"] = reported(mds, books, units) if units else {}
    checks = {"p": wc.p_ok(t, alpha) if testable else False, "floor": bool(testable and wc.floor_ok(t["mean"], SIGN)), "route_gate": res["route_gate"]["ok"],
              "placebo_label_shuffle": res["placebo_label_shuffle"].get("calibrated") if testable else False}
    checks.update({f"robust_{k}": r.get("ok") for k, r in rob.items() if k != "month_sign"})  # (iv) is reported, not binding, for H
    failed = sorted(k for k, x in checks.items() if x is False)
    unverified = sorted(k for k, x in checks.items() if x is None)
    advance = bool(testable and not failed and not unverified)
    res.update(testable=testable, blockers=blockers, p=float(t["p"]) if testable else 1.0, effect=t["mean"], n=t["n"], checks=checks, failed_checks=failed,
               unverified_checks=unverified, advance=advance, cumulative_count_at_run=cumulative)
    if not testable:
        res["verdict"] = blockers[0] if blockers else f"not testable ({t.get('reason')})"
    elif advance:
        res["verdict"] = "advanced (a candidate presence filter, not a route)" + ("" if res["concentration_attribution"].get("credited") else f" ({res['concentration_attribution']['label']})")
    elif wc.core_ok(t, alpha, SIGN) and not res["route_gate"]["ok"]:
        res["verdict"] = "exits are less adverse than other sells, but buying them does not pay: no route"
    else:
        res["verdict"] = f"not detected at MDE (failed: {', '.join(failed + unverified)})"
    return res


def robustness(mds: list[dict], books: dict[str, MarkBook], pairs: list, units: list[dict], unav: list[dict], h1: float, *, alpha: float) -> dict:
    out: dict = {}
    nb = [u["v"] for u in pair_units(pairs, books, values=True, nth=2) if u["avail"]]
    nm = float(np.mean(nb)) if nb else math.nan
    out["next_but_one_capture"] = {"n": len(nb), "mean": nm, "ok": wc.half_magnitude_ok(nm, h1, SIGN)}
    for k, name in (("event", "top5_events"), ("day", "top5_days")):
        sub = wc.drop_top(units, k)
        t = _test(sub, alpha)
        out[name] = {"n": t["n"], "mean": t["mean"], "p": t["p"], "ok": wc.core_ok(t, alpha, SIGN)}
    out["weighted_sign"] = wc.weighted_sign(units, h1, "size")
    out["month_sign"] = {**wc.month_sign(units, SIGN, MONTH_MIN_UNITS), "binding": False}
    t = _test(units + [{**u, "v": 0.0} for u in unav], alpha)
    out["worst_case"] = {"n_added": len(unav), "mean": t["mean"], "p": t["p"], "ok": bool(np.isfinite(t["mean"]) and SIGN * t["mean"] > 0 and wc.p_ok(t, alpha))}
    lat = [u["v"] for u in pair_units(match_controls(exits(mds, group="main", exit_from=EXIT_FROM_ROBUST_S))[0], books, values=True) if u["avail"]]
    lm = float(np.mean(lat)) if lat else math.nan
    out["latency"] = {"n": len(lat), "mean": lm, "ok": wc.half_magnitude_ok(lm, h1, SIGN)}
    return out


def reported(mds: list[dict], books: dict[str, MarkBook], units: list[dict]) -> dict:
    """Reported, not binding: c-tercile table, rank-2..3 exits, wide-state frequency by concentration tercile, the sports stratum; with-rebate and pre-close
    dump size are not computable from the H data."""

    def summ(vs: list[float]) -> dict:
        return {"n": len(vs), "mean": float(np.mean(vs)) if vs else None}

    out: dict = {}
    cs = sorted(u["c"] for u in units)
    if cs:
        q1, q2 = cs[len(cs) // 3], cs[2 * len(cs) // 3]
        out["c_terciles"] = {"cuts": [q1, q2], "t0": summ([u["v"] for u in units if u["c"] < q1]), "t1": summ([u["v"] for u in units if q1 <= u["c"] < q2]),
                             "t2": summ([u["v"] for u in units if u["c"] >= q2])}
    for r in REPORTED_RANKS:
        out[f"rank{r}_exits"] = summ([u["v"] for u in pair_units(match_controls(exits(mds, group="main", rank=r))[0], books, values=True) if u["avail"]])
    sp = [u["v"] for u in pair_units(match_controls(exits(mds, group="sports"))[0], books, values=True) if u["avail"]]
    out["sports_stratum"] = summ(sp)
    cm_ = sorted(max(x for x in (m["c"][0], m["c"][1]) if isinstance(x, float) and x == x) for m in mds
                 if m["group"] == "main" and m["prints_status"] == "ok" and any(isinstance(m["c"][j], float) and m["c"][j] == m["c"][j] for j in (0, 1)))
    if cm_:
        q1, q2 = cm_[len(cm_) // 3], cm_[2 * len(cm_) // 3]
        tab: dict[str, list[float]] = {"t0": [], "t1": [], "t2": []}
        for m in mds:
            if m["group"] != "main" or m["prints_status"] != "ok":
                continue
            vals = [x for x in (m["c"][0], m["c"][1]) if isinstance(x, float) and x == x]
            if not vals:
                continue
            c = max(vals)
            k = "t0" if c < q1 else ("t1" if c < q2 else "t2")
            for s in books[m["day"]].spreads(m["market_id"]):
                tab[k].append(1.0 if (s is None or s > MARK_MAX_SPREAD + EPS) else 0.0)
        out["wide_state_share_by_c_max_tercile"] = {"cuts": [q1, q2], **{k: summ(v) for k, v in tab.items()}}
    out["with_rebate"] = "not computable (no fee category in the H data)"
    out["pre_close_dump_size"] = "not computable (no end date in the H data)"
    return out


# ---- runs ------------------------------------------------------------------------------------------------------------------------------------------------------


def run_census(out_root: Path, holders_dir: Path, *, holders_sha: str, fp: str, analysis_rules_sha: str, trials_path: Path, now: float | None = None) -> dict:
    """q0172: write ``census_H.json`` (write-once) and one ``cb8_descriptive`` line."""
    out_p = Path(out_root) / CENSUS_NAME
    if out_p.exists():
        raise cm.Refused(f"{out_p} already exists; the census is write-once")
    doc = census_h(holders_dir, holders_sha=holders_sha, fp=fp, analysis_rules_sha=analysis_rules_sha, now=time.time() if now is None else now)
    doc["run_utc"] = wc.now_iso()
    doc["cumulative_count_at_run"] = wc.cumulative(trials_path)
    sha = wc.write_results(out_p, doc)
    from . import provenance  # noqa: PLC0415

    provenance.append_trial({"kind": "cb8_descriptive", "label": wc.LABEL, "evidence_role": "prospective", "dataset": wc.DATASET, "preset": "H:census", "family": FAMILY,
                             "result_path": str(out_p), "results_sha256": sha, RULES_KEY: analysis_rules_sha, "n_tests": 0,
                             "summary": ba._clean({"gate_GH": doc["gate_GH"], "mde_H1": doc["mde_H1"]["mde"], "hash_join": doc["hash_join"]})}, trials_path)
    gh = doc["gate_GH"]
    return {"status": "census_H_complete", "gate_GH": gh["ok"], "gh_fail_label": gh["fail_label"], "n_pairs_with_marks": gh["n_pairs_with_marks"], "mde": doc["mde_H1"]["mde"],
            "written": str(out_p), "census_sha256": sha}


def _descriptive(res: dict) -> dict:
    return {"gate_GH": {k: (res.get("gate_GH") or {}).get(k) for k in ("ok", "n_pairs_with_marks", "n_events", "n_days", "n_holders")},
            "route_gate": {k: (res.get("route_gate") or {}).get(k) for k in ("n", "mean_mo_exit", "ok")},
            "concentration_attribution": {k: (res.get("concentration_attribution") or {}).get(k) for k in ("credited", "label")}, "hash_join": res.get("hash_join")}


def screen_h(out_root: Path, holders_dir: Path, *, holders_sha: str, fp: str, analysis_rules_sha: str, freeze_sha: str, seals_dir: Path, trials_path: Path,
             now: float | None = None) -> dict:
    """q0173: H1 Stage 1 on window 1. Needs the committed-rules census (GH result). Results are write-once; the Stage-1 copy goes to
    ``seals/cb8_h1_stage1.json`` (commit it)."""
    out_root, seals_dir = Path(out_root), Path(seals_dir)
    out_p, copy = out_root / RESULTS_S1, seals_dir / STAGE1_COPY_NAME
    if out_p.exists() or copy.exists():
        raise cm.Refused(f"{out_p.name} or its Stage-1 copy already exists; results are never overwritten")
    census = out_root / CENSUS_NAME
    if not census.exists() or json.loads(census.read_text()).get(RULES_KEY) != analysis_rules_sha:
        raise cm.Refused("census_H.json (q0172) missing or produced under different H analysis rules")
    win = window_of(holders_dir, 1)
    require_ready(win, time.time() if now is None else now)
    view = HoldersView(holders_dir, win, holders_sha, fp)
    cum = wc.cumulative(trials_path)
    res = evaluate_h1(view, "screen", alpha=wc.ALPHA1, cumulative=cum)
    res["window"] = {"stage": 1, "start": cm.iso(win["start"]), "end": cm.iso(win["end"])}
    res["labels_stage1"] = {"by": ba.by_label(res["p"], cum), "batch_holm": wc.batch_holm_label(TEST, res["p"], out_root)}
    doc = {"test": TEST, "stage": 1, "rules_version": RULES_VERSION, RULES_KEY: analysis_rules_sha, DATA_KEY: holders_sha, "wallet_key_fingerprint": fp,
           "freeze_spec_sha256": freeze_sha, "census_sha256": h5_seal.sha256_file(census), "evidence_role": "prospective", "label": wc.LABEL, "run_utc": wc.now_iso(),
           "interpretations": list(INTERPRETATIONS), **res, "opened_files_n": len(set(view.opened))}
    sha = wc.write_results(out_p, doc)
    wc.write_stage1_copy(out_p, copy)
    wc.log_trials(res, family=FAMILY, test=TEST, replication=False, results_path=out_p, results_sha=sha, rules_key=RULES_KEY, rules_sha=analysis_rules_sha,
                  freeze_sha=freeze_sha, trials_path=trials_path, placebo_key="placebo_label_shuffle", descriptive=_descriptive(res))
    return {"status": "screen_H_complete", "advance": res["advance"], "p": res["p"], "testable": res["testable"], "verdict": res["verdict"], "results_sha256": sha,
            "written": str(out_p), "stage1_copy": str(copy)}


def replicate_h(out_root: Path, holders_dir: Path, *, holders_sha: str, fp: str, analysis_rules_sha: str, freeze_sha: str, seals_dir: Path,
                is_committed: Callable[[Path], bool] | None, trials_path: Path, freeze_spec: Path | None = None, now: float | None = None) -> dict:
    """q0176: H1-rep on window 2 (post-freeze, out of time). Refuses unless H1 advanced (committed Stage-1 copy); a freeze slip is recorded as 'not run
    (freeze slip)', counted; refuses (exit 75) before T8_H2_end + 30 h."""
    out_root, seals_dir = Path(out_root), Path(seals_dir)
    out_p = out_root / RESULTS_S2
    if out_p.exists():
        raise cm.Refused(f"{out_p.name} already exists; results are never overwritten")
    s1 = wc.require_stage1_advanced(out_root, seals_dir, test=TEST, results_name=RESULTS_S1, copy_name=STAGE1_COPY_NAME, rules_key=RULES_KEY,
                                    rules_sha=analysis_rules_sha, is_committed=is_committed)
    win = window_of(holders_dir, 2)
    cum = wc.cumulative(trials_path)
    k = wc.stage2_k(out_root, TEST)
    alpha = wc.ALPHA2 / k["k_used"]
    base = {"test": f"{TEST}-rep", "stage": 2, "rules_version": RULES_VERSION, RULES_KEY: analysis_rules_sha, DATA_KEY: holders_sha, "wallet_key_fingerprint": fp,
            "freeze_spec_sha256": freeze_sha, "stage1_sha256": h5_seal.sha256_file(seals_dir / STAGE1_COPY_NAME), "stage1_p": s1.get("p"), "evidence_role": "prospective",
            "label": wc.LABEL, "interpretations": list(INTERPRETATIONS), "window": {"stage": 2, "start": cm.iso(win["start"]), "end": cm.iso(win["end"])}}
    if win["freeze_slip"]:
        res = {"testable": False, "advance": False, "p": 1.0, "effect": None, "n": 0, "verdict": "not run (freeze slip)", "blockers": ["not run (freeze slip)"],
               "cumulative_count_at_run": cum, "placebo_label_shuffle": {"skipped": "not run (freeze slip)"}}
    else:
        if is_committed is not None:
            fc = wc.freeze_commit_epoch(freeze_spec)
            if fc is None or win["start"] < fc + 2 * cm.HOUR:
                raise cm.Refused("window 2 does not start at least 2 h after the first commit of the CB8 freeze spec")
        require_ready(win, time.time() if now is None else now)
        view = HoldersView(holders_dir, win, holders_sha, fp)
        res = evaluate_h1(view, "replicate", alpha=alpha, cumulative=cum)
        base["opened_files_n"] = len(set(view.opened))
    res["stage2_holm"] = {**k, "alpha2": wc.ALPHA2, "alpha_used": alpha, "label": "out-of-time replication on post-freeze data (L2)" if res["advance"] else None}
    doc = {**base, "run_utc": wc.now_iso(), **res}
    sha = wc.write_results(out_p, doc)
    wc.log_trials(res, family=FAMILY, test=TEST, replication=True, results_path=out_p, results_sha=sha, rules_key=RULES_KEY, rules_sha=analysis_rules_sha,
                  freeze_sha=freeze_sha, trials_path=trials_path, placebo_key="placebo_label_shuffle", descriptive=_descriptive(res))
    return {"status": "replicate_H_complete", "pass": res["advance"], "p": res["p"], "alpha_used": alpha, "testable": res["testable"], "verdict": res["verdict"],
            "results_sha256": sha, "written": str(out_p)}


# ---- rules file -----------------------------------------------------------------------------------------------------------------------------------------------


def declared() -> dict:
    return {
        "scope": "CB8-H analysis: census (q0172), H1 Stage 1 (q0173, window 1), H1-rep Stage 2 (q0176, window 2)",
        "definitions": {"conc_min": CONC_MIN, "conc_low": CONC_LOW, "exit_from_s": EXIT_FROM_S, "exit_to_s": EXIT_TO_S, "usable": list(USABLE),
                        "control_window_s": CONTROL_WINDOW_S, "size_bands": [list(b) for b in SIZE_BANDS], "top_excluded": TOP_EXCLUDED, "horizon_s": HORIZON_S,
                        "mark_window_s": MARK_WINDOW_S, "mark_max_spread": MARK_MAX_SPREAD, "ready_after_end_s": READY_AFTER_END_S},
        "decision": {"sign": SIGN, "alpha1": wc.ALPHA1, "alpha2": wc.ALPHA2, "by_q": wc.BY_Q, "batch_holm_k1": wc.BATCH_HOLM_K1, "floor": wc.EDGE_FLOOR,
                     "route_gate": f"mean mo(exit) >= {wc.EDGE_FLOOR} (no rebate)", "min_units": wc.MIN_UNITS, "min_event_clusters": wc.MIN_EVENT_CLUSTERS,
                     "g_min": wc.G_MIN, "ways": ["event", "day (A-C1)", "holder"], "n_boot": wc.N_BOOT, "seed_boot": wc.SEED_BOOT, "n_wild": wc.N_WILD},
        "gh": {"min_pairs": GH_MIN_PAIRS, "min_events": GH_MIN_EVENTS, "min_days": GH_MIN_DAYS, "min_holders": GH_MIN_HOLDERS},
        "placebo": {"label_shuffle": {"draws": wc.PLACEBO_DRAWS, "seed": SEED_SHUFFLE, "block": "holder x market x snapshot day", "max_rate": wc.PLACEBO_MAX_RATE},
                    "concentration_attribution": {"share": wc.ATTRIBUTION_SHARE, "c_low": CONC_LOW}},
        "robustness": {"next_but_one_capture": True, "top_k": wc.TOP_K, "month_min_units": MONTH_MIN_UNITS, "month_sign_binding": False, "half": wc.HALF,
                       "exit_from_robust_s": EXIT_FROM_ROBUST_S, "worst_case": "unavailable pairs at contrast 0"},
        "reported": {"ranks": list(REPORTED_RANKS)},
        "mde": {"sd": MDE_SD, "deff": MDE_DEFF, "power": wc.MDE_POWER, "alpha": wc.ALPHA1},
        "outputs": {"census": CENSUS_NAME, "stage1": RESULTS_S1, "stage2": RESULTS_S2, "stage1_copy": STAGE1_COPY_NAME, "output_cap_gb": wc.OUTPUT_CAP_GB},
        "wallet_key_fingerprint": WALLET_KEY_FP,
        "freeze": f"screen and replicate need a committed model_specs/cb8_v1.json carrying {RULES_KEY} and {DATA_KEY} equal to the code's",
        "interpretations": list(INTERPRETATIONS),
    }


def data_rules_sha() -> str:
    return cm.rules_file_doc("holders", WALLET_KEY_FP)["rules_sha256"]


def rule_funcs() -> list:
    own = [declared, data_rules_sha, _f, _day, _days_between, _fp, window_of, require_ready, _manifest, HoldersView.__init__, HoldersView._read, HoldersView.days,
           HoldersView.day_markers, HoldersView.snapshot, HoldersView.prints_status, HoldersView.prints, HoldersView.markbook, HoldersView.window_record, HoldersView.prints_terminal,
           MarkBook.__init__, MarkBook._pick, MarkBook.available, MarkBook.mid, MarkBook.spreads, market_days, _usable, exits, match_controls, pair_units, hash_join,
           gh_gate, mde, _books, census_h, _test, label_shuffle_placebo, evaluate_h1, robustness, reported, run_census, _descriptive, screen_h, replicate_h]
    deps = [H.concentration, H.read_pins, cm.c4._parse_ts, ba._f, h5_seal.sha256_file]
    return own + deps + wc.rule_funcs()


def rules_file_doc() -> dict:
    return wc.make_rules_doc(RULES_VERSION, declared(), data_rules_sha(), rule_funcs())


def write_rules(path: Path | None = None) -> Path:
    return wc.write_rules_file(Path(path or RULES_FILE), rules_file_doc())


def verify_analysis_rules(path: Path | None = None, *, require_committed: bool = True) -> str:
    return wc.verify_rules_file(Path(path or RULES_FILE), rules_file_doc(), "H analysis", require_committed=require_committed)


def require_freeze(spec_path: Path | None, analysis_sha: str, data_sha: str, *, require_committed: bool = True) -> str:
    return wc.require_freeze(spec_path, {RULES_KEY: analysis_sha, DATA_KEY: data_sha}, require_committed=require_committed)
