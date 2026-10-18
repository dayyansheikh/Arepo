# ruff: noqa: E501
"""CB11-P: political long-horizon underconfidence carry (docs/research_lab/CREATIVE_BATCH_11.md CB11-P, 1.2-1.4, 2.1-2.7, CB11-F q0225 / q0226 / q0239 / q0233 / q0236).

Frame (Gamma ``tag_id=2`` politics and a control walk; whitelisted fields; no resolution-status or outcome-cleanliness filter; outcomes, UMA status and close times
only in the guarded files), origins ``t_h = end - h`` (30 / 60 / 90 d), one ``prices-history`` request over ``[t_h - 7 d, t_h]`` per unit (price and the causal
activity proxy), P1 (mean favourite excess), P2 (carry at a declared ask), the GPP power gate with the shared week factor, the copula placebo, the election
concentration and the round-1 robustness checks. EXPLORATORY; every result is labelled ``L1, hindsight end date``; no edge or profitability claim.
"""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb11_common as c11
from . import cb11_pa as pa
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow
DAY, HOUR = pa.DAY, pa.HOUR

P_SCREEN = ("2024-07-01", "2026-01-01")
P_HOLD = ("2026-01-01", "2026-09-01")
P_SCREEN_HALVES = (("2024-07-01", "2025-04-01"), ("2025-04-01", "2026-01-01"))
T5_OVERLAP = ("2025-10-11", "2026-01-01")
POL_TAG = 2
HORIZONS = (30, 60, 90)
BAND = (0.60, 0.85)
BAND_WIDE = (0.55, 0.90)
MIN_LIFE_D = 60.0
LISTED_BEFORE_D = 7.0
START_FILTER_D = 53.0  # start_date_max = window start - 53 d (= window end - 60 d for a weekly window): server-side prefilter, exact life filter local
WINDOW_S = 7 * 86400
MIN_SPLIT_S = 3600
LAG_S = 600.0
AGE_MAX_S = DAY
FIDELITY = hb.FIDELITY_MIN
N_POL = {"screen": 4000, "holdout": 3000}
N_CTL = {"screen": 2000, "holdout": 1500}
MAX_PER_EVENT = 4
CONTROL_POOL_MULT = 3
CONTROL_MAX_REQUESTS = 2000
SEED_POL_CAP = "arepo-cb11-pol-cap"
SEED_POL_SAMPLE = "arepo-cb11-pol-sample"
SEED_CTL_CAP = "arepo-cb11-ctl-cap"
SEED_CTL_SAMPLE = "arepo-cb11-ctl-sample"
SEED_CTL_WINDOWS = "arepo-cb11-ctl-windows"
EXCLUDED_TOPICS = ("sports", "crypto", "weather")
ASK_HALF_SPREAD = 0.015
ASK_HALF_SPREAD_ROBUST = 0.025
FEE_R_MIN = 0.04
RF_RATE = 0.045
P1_FLOOR = 0.03
P1_FLAG_FLOOR = 0.015
ELECTION_FLOOR = 0.015
ATTR_CTRL_GAP = 0.015
P2_NET_FLOOR = 0.02
P2_RANN_FLOOR = 0.10
GP = {"markets": 800, "events": 250, "weeks": 40}
COVER_MIN = 0.90
AVAIL_MIN = 0.60
GPP_MAX_MDE = 0.06
GPP_DRAWS = 500
GPP_INNER = 200
GPP_LOADINGS = (0.2, 0.4, 0.4)  # week, event, market (variance shares; Z = sqrt(.2) W + sqrt(.4) V + sqrt(.4) e)
MDE_FACTOR = 1.2
DATA_PAGE_LIMIT = 1000
DATA_PAGES = 2
TAKER_ONLY = "true"
FRAME_OUTPUT_CAP_GB = 0.01
PRICES_OUTPUT_CAP_GB = 0.03
FRAME_STATUS = "pol_frame_complete"
PRICES_STATUS = "pol_prices_complete"
RUN = c11.H11_POL
HOLD_DIR = "holdout"
SEAL_COPY_NAME = "cb11_pol_holdout_SEAL.json"
LATE_CLOSE_S = 7 * DAY
EDIT_DAYS = 1.0

FRAME_COLUMNS = ["market_id", "condition_id", "token0", "token1", "start_epoch", "end_epoch", "neg_risk", "neg_risk_market_id", "event_id", "event_ids", "series_ids", "tag_ids", "fee_rate",
                 "group", "split", "event_key", "open_30", "open_60", "open_90"]
FLAG_COLUMNS = ["market_id", "edit_detected", "election2024"]
GUARDED_COLUMNS = ["market_id", "outcome_prices", "uma_status", "closed_epoch", "late_close"]
ORIGIN_COLUMNS = ["market_id", "h", "label", "p", "n_points", "n_distinct", "t_h"]
REACH_COLUMNS = ["market_id", "status", "oldest_ts", "truncated", "n_prints"]
GUARDED_NAMES = ("outcomes_guarded.csv.gz", "outcomes_guarded_hold.csv.gz")
HOLD_ONLY = ("outcomes_guarded_hold.csv.gz",)
CENSUS_FORBIDDEN = ("outcome_prices", "uma_status", "closed_epoch", "late_close", "Y", "E", "net", "pnl", "excess", "outcomes_guarded")

LABEL_OK = "ok"
LABEL_INACTIVE = "inactive_proxy"
LABEL_NO_PRICE = "no_price"
LABEL_NOT_LISTED = "not_listed"
LABEL_CLOSED = "closed_before_t"
LABEL_NO_CLOSE = "close_time_missing"
LABEL_FAILED = "fetch_failed"
ELIGIBLE_LABELS = (LABEL_OK, LABEL_INACTIVE, LABEL_NO_PRICE, LABEL_FAILED)
PRICED_LABELS = (LABEL_OK, LABEL_INACTIVE)

# ---- frozen text rules (hashed with the rules file before any read) -------------------------------------------------------------------------------
CAL_DATE_RE = (r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
               r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d{2}))?\b")
ISO_DATE_RE = r"\b(20\d{2})-(\d{2})-(\d{2})\b"
ELECTION_END_WINDOW = ("2024-10-01", "2025-01-31")
ELECTION_YEAR_RE = r"2024"
ELECTION_WITH_YEAR_RE = r"\b(president|presidential|electoral|popular vote|senate|house|governor|swing state)\b"
ELECTION_NAME_RE = r"\b(harris|walz|vance|trump)\b"
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _ep(d: str) -> float:
    return pa.ep(d)


E_SCREEN = (_ep(P_SCREEN[0]), _ep(P_SCREEN[1]))
E_HOLD = (_ep(P_HOLD[0]), _ep(P_HOLD[1]))
E_ALL = (E_SCREEN[0], E_HOLD[1])


def split_of(end_epoch: float) -> str | None:
    if not math.isfinite(end_epoch):
        return None
    if E_SCREEN[0] <= end_epoch < E_SCREEN[1]:
        return "screen"
    if E_HOLD[0] <= end_epoch < E_HOLD[1]:
        return "holdout"
    return None


def t_h(end_epoch: float, h: int) -> float:
    return end_epoch - h * DAY


# =====================================================================================================================================
# Frozen flags (computed at frame time from listing text; closedTime only through the guarded accessor)
# =====================================================================================================================================


def named_dates(text: str, end_epoch: float) -> list[float]:
    """Explicit calendar dates named in ``text`` ('March 5, 2026', 'Dec 31', '2025-12-31') as UTC-midnight epochs. A date without a year takes the year (end year
    - 1, end year, end year + 1) that puts it nearest to ``end_epoch``."""
    out: list[float] = []
    ey = datetime.fromtimestamp(end_epoch, UTC).year if math.isfinite(end_epoch) else 2025
    for m in re.finditer(CAL_DATE_RE, text or "", flags=re.IGNORECASE):
        mo, d = _MONTHS[m.group(1)[:3].lower()], int(m.group(2))
        years = [int(m.group(3))] if m.group(3) else [ey - 1, ey, ey + 1]
        cands = []
        for y in years:
            try:
                cands.append(datetime(y, mo, d, tzinfo=UTC).timestamp())
            except ValueError:
                continue
        if cands:
            out.append(min(cands, key=lambda e: abs(e - end_epoch)) if len(cands) > 1 and math.isfinite(end_epoch) else cands[0])
    for m in re.finditer(ISO_DATE_RE, text or ""):
        try:
            out.append(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=UTC).timestamp())
        except ValueError:
            continue
    return out


def edit_detected(end_epoch: float, event_end: float, question: str, event_title: str) -> bool:
    """``endDate`` of the market differs by more than 1 day from its event's ``endDate``, or the question / event title names an explicit calendar date more than
    1 day from ``endDate``."""
    if not math.isfinite(end_epoch):
        return False
    if math.isfinite(event_end) and abs(end_epoch - event_end) > EDIT_DAYS * DAY:
        return True
    end_mid = pa.utc_midnight(end_epoch)
    return any(abs(d - end_mid) > EDIT_DAYS * DAY for d in named_dates(f"{question} . {event_title}", end_epoch))


def election_2024(end_epoch: float, question: str, event_title: str) -> bool:
    """Frozen keyword rule: scheduled end in ``[2024-10-01, 2025-01-31]`` and the event title (or the question) matches ``2024`` together with any of president,
    presidential, electoral, popular vote, Senate, House, governor, swing state, or any of Harris, Walz, Vance, Trump (case-insensitive)."""
    if not math.isfinite(end_epoch) or not (_ep(ELECTION_END_WINDOW[0]) <= end_epoch < _ep(ELECTION_END_WINDOW[1]) + DAY):
        return False
    text = f"{event_title} . {question}"
    low = text.lower()
    return bool((re.search(ELECTION_YEAR_RE, low) and re.search(ELECTION_WITH_YEAR_RE, low)) or re.search(ELECTION_NAME_RE, low))


def late_close(end_epoch: float, closed_epoch: float) -> bool:
    return bool(math.isfinite(end_epoch) and math.isfinite(closed_epoch) and closed_epoch > end_epoch + LATE_CLOSE_S)


# =====================================================================================================================================
# Frame walk (q0225)
# =====================================================================================================================================


def week_windows(lo: float = E_ALL[0], hi: float = E_ALL[1]) -> list[tuple[int, int]]:
    out, a = [], int(lo)
    while a < hi:
        out.append((a, int(min(a + WINDOW_S, hi))))
        a += WINDOW_S
    return out


def walk_window(lim: hb.Limiter, base: dict, a: int, b: int, acc: dict, *, split: bool = True) -> None:
    """One ``/markets`` end-date window by offset (limit 100, offset <= 2,000). A capped window is split in half down to one hour when ``split`` (counted); a
    capped one-hour window, or any capped window when not ``split``, keeps its first 2,000 rows by id and is counted ``capped_kept``. A failed request makes the
    window ``failed`` (never read as capped)."""
    from . import cb4_data as c4  # noqa: PLC0415

    f = "%Y-%m-%dT%H:%M:%SZ"
    p = {**base, "order": "id", "ascending": "true", "end_date_min": datetime.fromtimestamp(a, UTC).strftime(f), "end_date_max": datetime.fromtimestamp(b, UTC).strftime(f),
         "start_date_max": datetime.fromtimestamp(a - START_FILTER_D * DAY, UTC).strftime(f)}
    batch, capped, failed = c4._paged_strict(lim, p, hb.GAMMA_OFFSET_CAP)
    if failed:
        acc["failed_windows"] += 1
        return
    if capped and split and b - a > MIN_SPLIT_S:
        acc["splits"] += 1
        mid = a + (b - a) // 2
        walk_window(lim, base, a, mid, acc, split=split)
        walk_window(lim, base, mid, b, acc, split=split)
        return
    acc["windows"] += 1
    if capped:
        acc["capped_kept"] += 1
    acc["batches"].extend(batch)


def frame_record(m: dict, group: str, a: float, b: float) -> dict | None:
    """The stored candidate of one raw market, or ``None`` if a static local filter drops it (not binary, end outside the window, life below 60 d, sports / crypto
    / weather, or (control) politics-tagged). The row, the frozen flags, the horizon open-booleans and the guarded fields are the only things kept."""
    r = pa.pa_row(m)
    if r is None:
        return None
    end, start = r["end_epoch"], r["start_epoch"]
    if not (math.isfinite(end) and math.isfinite(start) and a <= end < b and (end - start) / DAY >= MIN_LIFE_D):
        return None
    aux = pa.pa_aux(m)
    topic = pa.topic_label(r, aux)
    if topic in EXCLUDED_TOPICS:
        return None
    if group == "ctl" and (str(POL_TAG) in str(r["tag_ids"]).split(";") or topic == "politics"):
        return None
    g = pa.pa_guarded(m)
    closed = g["closed_epoch"]
    opens = {}
    for h in HORIZONS:
        opens[f"open_{h}"] = "" if not math.isfinite(closed) else int(closed > t_h(end, h))
    r = {**r, "group": group, **opens}
    return {"r": {k: pa.blank(v) for k, v in r.items()}, "g": {**g, "closed_epoch": pa.blank(closed), "late_close": int(late_close(end, closed))},
            "f": {"edit_detected": int(edit_detected(end, aux["event_end"], aux["question"], aux["event_title"])),
                  "election2024": int(election_2024(end, aux["question"], aux["event_title"]))}}


def assemble(recs: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], ext_ids: dict[str, set[str]] | None = None) -> tuple[dict, dict]:
    """Dedupe, id / key drops (full rule, series included), <= 4 markets per event per group (seeded), out-of-time split at 2026-01-01, seeded samples (politics
    4,000 / 3,000, control 2,000 / 1,500). Reads ids, events and dates only. Returns ({(group, split): [rec]}, report)."""
    from . import cb10_common as c10  # noqa: PLC0415

    seen: dict[str, dict] = {}
    for rec in recs:
        seen.setdefault(str(rec["r"]["market_id"]), rec)
    pool = list(seen.values())
    rep: dict = {"n_candidates": len(pool), "drops": {}, "per_event_capped_out": {}, "sampled": {}, "pool_by_month": {}}
    ext = ext_ids or {}
    rep["external_id_hits"] = {k: sum(1 for x in pool if str(x["r"]["market_id"]) in v) for k, v in ext.items()}
    rows = [{**x["r"], "_rec": x} for x in pool]
    kept, drops = c10.drop_by_keys(rows, excl_ids, excl_keys)
    rep["drops"] = drops
    out: dict[tuple[str, str], list[dict]] = {}
    for grp, seed_cap, seed_sample, n_by in (("pol", SEED_POL_CAP, SEED_POL_SAMPLE, N_POL), ("ctl", SEED_CTL_CAP, SEED_CTL_SAMPLE, N_CTL)):
        g_rows = [r for r in kept if r["group"] == grp]
        by_ev: dict[str, list[dict]] = {}
        for r in g_rows:
            by_ev.setdefault(pa.event_key(r), []).append(r)
        capped = [x for ev in by_ev.values() for x in sorted(ev, key=lambda r: c11.rank(seed_cap, str(r["market_id"])))[:MAX_PER_EVENT]]
        rep["per_event_capped_out"][grp] = len(g_rows) - len(capped)
        for sp in ("screen", "holdout"):
            cand = [r for r in capped if split_of(float(r["end_epoch"])) == sp]
            rep["pool_by_month"][f"{grp}|{sp}"] = dict(sorted(Counter(pa.month_of(float(r["end_epoch"])) for r in cand).items()))
            samp = sorted(cand, key=lambda r: c11.rank(seed_sample, str(r["market_id"])))[: n_by[sp]]
            rep["sampled"][f"{grp}|{sp}"] = {"pool": len(cand), "n": len(samp), "events": len({pa.event_key(r) for r in samp})}
            out[(grp, sp)] = sorted(({**r["_rec"], "event_key": pa.event_key(r)} for r in samp), key=lambda x: str(x["r"]["market_id"]))
    return out, rep


def _walk_records(fr, rdir: Path, group: str, windows: list[tuple[int, int]], pp: Path, pf: Path, should_stop: Callable[[], bool] | None, *, split: bool, stop_when=None) -> str | None:
    """Walk ``windows`` for ``group`` (resumable: one gzip member per finished window in ``pp``). Returns a stop reason or None when done."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415

    base = {"closed": "true", **({"tag_id": POL_TAG} if group == "pol" else {})}
    have = {(rec["group"], rec["a"]) for rec in c6.iter_partial(pp)}
    fails = c7.walk_failed_days(pf)
    for a, b in windows:
        key = f"{group}|{a}"
        if (group, a) in have or fails.get(key, 0) >= cm.MAX_ITEM_ATTEMPTS:
            continue
        if stop_when is not None and stop_when(a):
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return why
        acc = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "capped_kept": 0}
        n0 = fr.lim.requests
        walk_window(fr.lim, base, a, b, acc, split=split)
        if acc["failed_windows"]:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": key}) + "\n")
            continue
        raw = [m for m in acc["batches"] if isinstance(m, dict)]
        rows = [x for x in (frame_record(m, group, a, b) for m in raw) if x is not None]
        c7.append_member(fr, pp, {"group": group, "a": a, "b": b, "rows": rows, "n_raw": len(raw), "splits": acc["splits"], "capped_kept": acc["capped_kept"],
                                  "req": fr.lim.requests - n0})
    return None


def pol_frame(hist_root: Path, transport, *, rules_sha: str, smoke_path: Path, exclusion_keys_path: Path, now: float, external_dir: Path | None = None, rps: float = 2.0,
              disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time,
              snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, free_fn=None,
              windows: list[tuple[int, int]] | None = None) -> dict:
    """q0225, one resumable chunk: politics walk (every weekly window, capped windows split), control walk (windows in seeded rank order until the pool is 3x the
    sample, capped windows kept truncated and counted, <= 2,000 requests), then the assembly and the files before any price request."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb11_smoke as sm  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    hist_root = Path(hist_root)
    rdir = c11.require_output_root(hist_root / RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    if c11.manifest_complete(rdir, (FRAME_STATUS, PRICES_STATUS)) or pa.state_flag(rdir, "frame_complete"):
        done = json.loads((rdir / "manifest.json").read_text())
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    bad = sm.smoke_failures(smoke_path, sm.FAMILY_NEEDS["P"])
    if bad:
        return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c11.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c11.UNVERIFIED:
        return c11.write_stall(rdir, c11.STALL_DISJOINTNESS, "q0221: > 2% of exclusion ids without metadata (design 1.3)")
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(hist_root, RUN, transport, allowed_run_id=RUN, kind="cb11_pol_frame", label="CB11-P frame",
                     params={"exclusion_keys_sha256": ksha, "evidence_role": c11.EVIDENCE_ROLE_HIST, "c1_t5_status": krep.get("c1_t5_status", "absent")}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    try:
        pp, pf = rdir / "frame_partial.jsonl.gz", rdir / "frame_fail.jsonl"
        wins = windows if windows is not None else week_windows()
        why = _walk_records(fr, rdir, "pol", wins, pp, pf, should_stop, split=True)
        if why:
            return pa.in_progress(fr, why)
        recs = list(c6.iter_partial(pp))
        ctl_wins = sorted(wins, key=lambda w: c11.rank(SEED_CTL_WINDOWS, str(w[0])))

        def pool_count(sp: str) -> int:
            return sum(1 for rec in recs if rec["group"] == "ctl" for x in rec["rows"] if split_of(float(x["r"]["end_epoch"])) == sp)

        def full(a: int) -> bool:
            sp = split_of(float(a))
            return bool(sp) and pool_count(sp) >= CONTROL_POOL_MULT * N_CTL[sp]

        # control windows one at a time so the pool counts stay current; stop at the pool or at the request cap
        for w in ctl_wins:
            recs = list(c6.iter_partial(pp))
            if sum(int(rec.get("req", 0)) for rec in recs if rec["group"] == "ctl") >= CONTROL_MAX_REQUESTS:
                break
            why = _walk_records(fr, rdir, "ctl", [w], pp, pf, should_stop, split=False, stop_when=full)
            if why:
                return pa.in_progress(fr, why)
        recs = list(c6.iter_partial(pp))
        ext_dir = Path(external_dir or c11.EXTERNAL_IDS_DIR)
        ext = {fn.split("_")[0]: c11.read_id_set(ext_dir / fn) for fn in c11.EXTERNAL_ID_FILES if (ext_dir / fn).exists()}
        flat = [x for rec in recs for x in rec["rows"]]
        out, rep = assemble(flat, ids, keys, ext)
        rep["walk"] = {"windows_pol": sum(1 for rec in recs if rec["group"] == "pol"), "windows_ctl": sum(1 for rec in recs if rec["group"] == "ctl"),
                       "splits": sum(rec["splits"] for rec in recs), "capped_kept_windows": sum(rec["capped_kept"] for rec in recs), "n_raw": sum(rec["n_raw"] for rec in recs),
                       "control_requests": sum(int(rec.get("req", 0)) for rec in recs if rec["group"] == "ctl"),
                       "failed_windows": sorted(k for k, n in c7_fails(pf).items() if n >= cm.MAX_ITEM_ATTEMPTS)}
        for sp in ("screen", "holdout"):
            prefix = "" if sp == "screen" else HOLD_DIR + "/"
            sfx = "" if sp == "screen" else "_hold"
            rows = [x for grp in ("pol", "ctl") for x in out[(grp, sp)]]
            fr.budget.write_gz_csv(rdir / f"{prefix}frame{sfx}.csv.gz", FRAME_COLUMNS, ([{**x["r"], "split": sp, "event_key": x["event_key"]}.get(c, "") for c in FRAME_COLUMNS] for x in rows))
            fr.budget.write_gz_csv(rdir / f"{prefix}flags{sfx}.csv.gz", FLAG_COLUMNS, ([x["r"]["market_id"], x["f"]["edit_detected"], x["f"]["election2024"]] for x in rows))
            fr.budget.write_gz_csv(rdir / f"{prefix}outcomes_guarded{sfx}.csv.gz", GUARDED_COLUMNS, ([x["g"].get(c, "") for c in GUARDED_COLUMNS] for x in rows))
            for nm in (f"{prefix}frame{sfx}.csv.gz", f"{prefix}flags{sfx}.csv.gz", f"{prefix}outcomes_guarded{sfx}.csv.gz"):
                fr.record_file(rdir / nm)
        fr.budget.write(rdir / "split.json", json.dumps({"seeds": {"pol_cap": SEED_POL_CAP, "pol_sample": SEED_POL_SAMPLE, "ctl_cap": SEED_CTL_CAP, "ctl_sample": SEED_CTL_SAMPLE,
                                                                   "ctl_windows": SEED_CTL_WINDOWS}, "split_at": P_HOLD[0], "report": rep, "exclusion_keys_sha256": ksha,
                                                         "c1_t5_status": krep.get("c1_t5_status", "absent")}, indent=1, sort_keys=True, default=float).encode())
        fr.record_file(rdir / "split.json")
        pp.unlink(missing_ok=True)
        pf.unlink(missing_ok=True)
        fr.counts.update({f"{g}_{s}": len(out[(g, s)]) for g in ("pol", "ctl") for s in ("screen", "holdout")})
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    _ = (c6, h5_seal)
    fr.extra_state["frame_complete"] = True
    m = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m["status"] = FRAME_STATUS
    return m


def c7_fails(pf: Path) -> dict[str, int]:
    from . import cb7_common as c7  # noqa: PLC0415

    return c7.walk_failed_days(pf)


# =====================================================================================================================================
# Prices (q0226)
# =====================================================================================================================================


def read_frame(rdir: Path, split: str, *, job: str) -> list[dict]:
    """SCREEN rows (frame.csv.gz) or HOLDOUT rows (holdout/frame_hold.csv.gz, only ``rep-P`` after the seal is verified)."""
    rdir = Path(rdir)
    if split == "holdout":
        if job != "rep-P":
            raise Refused("P HOLDOUT is sealed: only rep-P loads it (after verify_holdout_seal)")
        path = rdir / HOLD_DIR / "frame_hold.csv.gz"
    elif split == "screen":
        path = rdir / "frame.csv.gz"
    else:
        raise Refused(f"unknown split {split!r}")
    return [dict(r) for r in c11.read_csv_gz(path)]


def read_frame_for_fetch(rdir: Path) -> list[tuple[str, dict]]:
    """The fetch jobs (q0226) read both frame files to know which markets to request; they never read a guarded file."""
    rdir = Path(rdir)
    return [(sp, dict(r)) for sp, p in (("screen", rdir / "frame.csv.gz"), ("holdout", rdir / HOLD_DIR / "frame_hold.csv.gz")) for r in c11.read_csv_gz(p)]


def price_point(history: list[dict], t: float) -> tuple[float, int, int]:
    """(price at ``t``, n points known, n distinct values known) from ``prices-history`` points ``{t, p}``. A point is known from its stamp + 600 s; the price is
    the last known point strictly before ``t`` with age (``t`` - stamp) <= 24 h, else NaN. The distinct count runs over the points known in ``[t - 7 d, t)`` (the
    causal activity proxy)."""
    pts = sorted((float(h["t"]), float(h["p"])) for h in history if isinstance(h, dict) and "t" in h and "p" in h)
    known = [(s, p) for s, p in pts if s + LAG_S < t]
    in_win = [p for s, p in known if s + LAG_S >= t - 7 * DAY]
    price = math.nan
    if known and t - known[-1][0] <= AGE_MAX_S:
        price = known[-1][1]
    return price, len(in_win), len({round(p, 6) for p in in_win})


def unit_label(start_epoch: float, t: float, open_flag, price: float, n_distinct: int) -> str:
    """Eligibility and activity label of one (market, horizon) unit."""
    if not (math.isfinite(start_epoch) and start_epoch <= t - LISTED_BEFORE_D * DAY):
        return LABEL_NOT_LISTED
    if str(open_flag) == "":
        return LABEL_NO_CLOSE
    if str(open_flag) in ("0", "False"):
        return LABEL_CLOSED
    if not math.isfinite(price):
        return LABEL_NO_PRICE
    return LABEL_OK if n_distinct >= 2 else LABEL_INACTIVE


def pol_prices(hist_root: Path, transport, *, rules_sha: str, now: float, smoke_path: Path | None = None, rps: float = 2.0, disk_cap: int = int(PRICES_OUTPUT_CAP_GB * 1024**3),
               budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None,
               data_dumps: Path | None = None, data_dumps_cap_gb: float = c11.DATA_DUMPS_CAP_GB, free_fn=None, pages: int = DATA_PAGES, page_limit: int = DATA_PAGE_LIMIT) -> dict:
    """q0226, one resumable chunk: per sampled market and eligible horizon one ``prices-history`` request over ``[t_h - 7 d, t_h]``; for the politics SCREEN
    markets also <= 2 newest-first Data API pages (aggregated to transactions inside the 7-day windows; reach recorded). HOLDOUT rows go to ``holdout/``. No
    outcome field is read."""
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb10_dlad as dl  # noqa: PLC0415
    from . import cb11_smoke as sm  # noqa: PLC0415
    from . import cb11_w as w  # noqa: PLC0415

    hist_root = Path(hist_root)
    rdir = c11.require_output_root(hist_root / RUN)
    st = c11.stall_of(rdir)
    if st:
        return st
    if smoke_path is not None:
        bad = sm.smoke_failures(smoke_path, sm.FAMILY_NEEDS["P"])
        if bad:
            return c11.write_stall(rdir, c11.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    if not (c11.manifest_complete(rdir, (FRAME_STATUS, PRICES_STATUS)) or pa.state_flag(rdir, "frame_complete")):
        raise NotNow("q0226 waits for q0225 (pol_frame) to finish")
    done = c11.manifest_complete(rdir, (PRICES_STATUS,))
    if done:
        return {"stopped": None, "status": PRICES_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c11.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(hist_root, RUN, transport, allowed_run_id=RUN, kind="cb11_pol_prices", label="CB11-P prices", params={"evidence_role": c11.EVIDENCE_ROLE_HIST, "pages": pages},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    pp = rdir / "origins_partial.jsonl.gz"
    try:
        from . import cb6_tail as c6  # noqa: PLC0415

        have = {rec["market_id"] for rec in c6.iter_partial(pp)}
        for sp, r in read_frame_for_fetch(rdir):
            mid = str(r["market_id"])
            if mid in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return pa.in_progress(fr, why)
            end, start = pa.fnum(r["end_epoch"]), pa.fnum(r["start_epoch"])
            units, failed = [], False
            for h in HORIZONS:
                t = t_h(end, h)
                pre = unit_label(start, t, r[f"open_{h}"], 1.0, 2)
                if pre in (LABEL_NOT_LISTED, LABEL_CLOSED, LABEL_NO_CLOSE):
                    units.append({"h": h, "label": pre, "p": "", "n_points": 0, "n_distinct": 0, "t_h": t})
                    continue
                try:
                    stt, data = fr.lim.get(hb.CLOB_PRICES, {"market": r["token0"], "startTs": int(t - 7 * DAY), "endTs": int(t), "fidelity": FIDELITY})
                    if stt != 200 or not isinstance(data, dict):
                        raise cm.ApiError(f"prices-history status {stt}")
                    price, npts, nd = price_point(data.get("history") or [], t)
                    units.append({"h": h, "label": unit_label(start, t, r[f"open_{h}"], price, nd), "p": pa.blank(price), "n_points": npts, "n_distinct": nd, "t_h": t})
                except (cm.ApiError, RuntimeError) as exc:
                    fails = fr.extra_state.setdefault("fails", {})
                    fails[mid] = fails.get(mid, 0) + 1
                    if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                        return pa.in_progress(fr, f"prices_failed {mid}: {exc}"[:200])
                    units.append({"h": h, "label": LABEL_FAILED, "p": "", "n_points": 0, "n_distinct": 0, "t_h": t})
                    failed = True
            reach = {"market_id": mid, "status": "not_requested", "oldest_ts": "", "truncated": "", "n_prints": 0}
            is_pol_screen = sp == "screen" and r["group"] == "pol"
            elig = [h for h in HORIZONS if any(u["h"] == h and u["label"] in ELIGIBLE_LABELS for u in units)]
            if is_pol_screen and elig and not failed:
                t_stop = min(t_h(end, h) for h in elig) - 7 * DAY
                try:
                    prints, info = w.fetch_prints_until(fr.lim, r["condition_id"], t_stop, limit=page_limit, pages=pages)
                    tx = dl.aggregate_transactions(prints, 0)
                    keep = [x for x in tx if any(t_h(end, h) - 7 * DAY <= x[0] < t_h(end, h) for h in elig)]
                    pa.write_tx_file(fr, rdir / "screen" / "tx" / f"{mid}.tx.csv.gz", keep)
                    reach = {"market_id": mid, "status": "ok", "oldest_ts": pa.blank(info["oldest_ts"]), "truncated": int(info["truncated"]), "n_prints": info["n_prints"]}
                except (cm.ApiError, RuntimeError) as exc:
                    fails = fr.extra_state.setdefault("fails", {})
                    fails[mid] = fails.get(mid, 0) + 1
                    if fails[mid] < cm.MAX_ITEM_ATTEMPTS:
                        return pa.in_progress(fr, f"prints_failed {mid}: {exc}"[:200])
                    reach = {"market_id": mid, "status": "fetch_failed", "oldest_ts": "", "truncated": 1, "n_prints": 0}
            c7.append_member(fr, pp, {"market_id": mid, "split": sp, "group": r["group"], "units": units, "reach": reach})
            have.add(mid)
        recs = list(c6.iter_partial(pp))
        for sp in ("screen", "holdout"):
            sub = [rec for rec in recs if rec["split"] == sp]
            prefix = Path(sp)
            fr.budget.write_gz_csv(rdir / prefix / "origins.csv.gz", ORIGIN_COLUMNS, ([rec["market_id"], u["h"], u["label"], u["p"], u["n_points"], u["n_distinct"], u["t_h"]]
                                                                                       for rec in sorted(sub, key=lambda x: x["market_id"]) for u in rec["units"]))
            fr.record_file(rdir / prefix / "origins.csv.gz")
            if sp == "screen":
                fr.budget.write_gz_csv(rdir / prefix / "reach.csv.gz", REACH_COLUMNS, ([rec["reach"][c] for c in REACH_COLUMNS] for rec in sorted(sub, key=lambda x: x["market_id"])))
                fr.record_file(rdir / prefix / "reach.csv.gz")
        pp.unlink(missing_ok=True)
        fr.counts.update(markets_priced=len(recs), units=sum(len(rec["units"]) for rec in recs))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    fr.extra_state["frame_complete"] = True
    m = fr.manifest(None, {"complete": True, "status": PRICES_STATUS})
    m["status"] = PRICES_STATUS
    return m


# =====================================================================================================================================
# Loaders (guards) and unit construction
# =====================================================================================================================================


def open_p_guarded(path: Path, job: str) -> list[dict]:
    """Guarded P files: ``screen-P`` and ``rep-P`` open the SCREEN file, only ``rep-P`` the ``*_hold`` one."""
    p = Path(path)
    if p.name in HOLD_ONLY and job != "rep-P":
        raise Refused(f"{p.name} is sealed: only rep-P opens it")
    return c11.open_guarded(p, job if job in ("screen-P", "rep-P") else "refused", GUARDED_NAMES)


def log_access(rdir: Path, job: str, files: list[str]) -> None:
    with (Path(rdir) / c11.ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "files": files}) + "\n")


def load_origins(rdir: Path, split: str, *, job: str) -> list[dict]:
    if split == "holdout" and job != "rep-P":
        raise Refused("P HOLDOUT origins are sealed: only rep-P loads them")
    path = Path(rdir) / (HOLD_DIR if split == "holdout" else split) / "origins.csv.gz"
    return [dict(r) for r in c11.read_csv_gz(path)]


def load_reach(rdir: Path) -> dict[str, dict]:
    p = Path(rdir) / "screen" / "reach.csv.gz"
    return {str(r["market_id"]): dict(r) for r in c11.read_csv_gz(p)} if p.exists() else {}


def y_fav(prices_json: str, k: int, unclean: float = 0.5) -> tuple[float, str]:
    """(Y_f, status) from the guarded outcome vector for the favourite token ``k``: [1,0] / [0,1] clean; [0.5,0.5] a clean 50-50 (0.5); anything else (unresolved,
    voided, unclean) is scored ``unclean`` (0.5 in the primary, the venue's void convention; 0.0 in the worst-case check)."""
    try:
        p = [float(x) for x in json.loads(prices_json)]
    except (ValueError, TypeError):
        return unclean, "unclean"
    if len(p) != 2:
        return unclean, "unclean"
    if sorted(p) == [0.0, 1.0]:
        return float(p[k]), "clean"
    if p == [0.5, 0.5]:
        return 0.5, "fifty"
    return unclean, "unclean"


def fav_of(p: float) -> tuple[int, float]:
    """(favourite token index, p_f): the outcome-0 token at ``p >= 0.5`` (a tie goes to outcome 0), p_f = max(p, 1 - p)."""
    return (0, p) if p >= 0.5 else (1, 1.0 - p)


def build_units(frame: list[dict], origins: list[dict], flags: dict[str, dict], guarded: dict[str, dict] | None, *, labels: tuple[str, ...] = (LABEL_OK,)) -> list[dict]:
    """One dict per (market, horizon) unit with a label in ``labels`` (default: priced and active). ``guarded`` is None for the census (no outcome fields)."""
    fm = {str(r["market_id"]): r for r in frame}
    out = []
    for o in origins:
        r = fm.get(str(o["market_id"]))
        if r is None or o["label"] not in labels:
            continue
        p = pa.fnum(o["p"])
        end = float(r["end_epoch"])
        k, pf = fav_of(p) if math.isfinite(p) else (0, math.nan)
        u = {"market_id": str(r["market_id"]), "group": r["group"], "event": r["event_key"], "week": pa.iso_week_of(end), "month": pa.month_of(end), "end": end, "h": int(o["h"]),
             "t_h": float(o["t_h"]), "p": p, "k": k, "p_f": pf, "label": o["label"], "n_distinct": int(float(o["n_distinct"] or 0)), "fee_rate": pa.fnum(r["fee_rate"]),
             "edit": int(str(flags.get(str(r["market_id"]), {}).get("edit_detected", 0)) in ("1", "True")), "elec": int(str(flags.get(str(r["market_id"]), {}).get("election2024", 0)) in ("1", "True"))}
        if guarded is not None:
            g = guarded.get(u["market_id"], {})
            y, st = y_fav(g.get("outcome_prices", ""), k) if g else (0.5, "unclean")
            y0, _ = y_fav(g.get("outcome_prices", ""), k, 0.0) if g else (0.0, "unclean")
            u.update(Y=y, Y_worst=y0, ystat=st, late=int(str(g.get("late_close", 0)) in ("1", "True")), closed=pa.fnum(g.get("closed_epoch")), uma=str(g.get("uma_status", "")))
        out.append(u)
    return out


def in_band(u: dict, band: tuple[float, float] = BAND) -> bool:
    return bool(math.isfinite(u["p_f"]) and band[0] <= u["p_f"] <= band[1])


def market_means(units: list[dict], field: str = "E") -> list[dict]:
    """Market value = mean over the market's units (each market weight 1)."""
    by: dict[str, list[dict]] = {}
    for u in units:
        by.setdefault(u["market_id"], []).append(u)
    out = []
    for mid, us in sorted(by.items()):
        out.append({"market_id": mid, "event": us[0]["event"], "week": us[0]["week"], "month": us[0]["month"], "end": us[0]["end"], "elec": us[0]["elec"], "edit": us[0]["edit"],
                    "late": us[0].get("late", 0), "v": float(np.mean([u[field] for u in us])), "n_units": len(us)})
    return out


def with_excess(units: list[dict], *, worst: bool = False, price_key: str = "p_f") -> list[dict]:
    return [{**u, "E": (u["Y_worst"] if worst else u["Y"]) - u[price_key]} for u in units]


# =====================================================================================================================================
# P1
# =====================================================================================================================================


def p1_core(mk: list[dict], *, alpha: float | None = None) -> dict:
    """Ē = mean over markets of the market value; one-sided p > 0 as the max over the event way and the ISO-week way (CB10 small-G rule for the week way)."""
    if len(mk) < 2:
        return {"n": len(mk), "mean": math.nan, "testable": False, "p": 1.0, "week_rule_holds": False}
    v = np.array([m["v"] for m in mk], float)
    cp = c11.cluster_p_week(v, {"event": np.array([m["event"] for m in mk])}, np.array([m["week"] for m in mk]), alpha=alpha)
    return {"n": len(mk), "mean": float(v.mean()), "testable": bool(cp["testable"]), "p": float(cp["p"]), "week_rule_holds": bool(cp.get("week_rule_holds", True)), "ways": cp.get("ways"),
            "week": cp.get("week")}


def p1_ok(r: dict, floor: float, *, gate: float = c11.GATE_P) -> bool:
    return bool(r["testable"] and r["week_rule_holds"] and r["p"] < gate and r["mean"] >= floor)


def drop_masks(mk: list[dict]) -> dict[str, np.ndarray]:
    """Keep-masks for the election-concentration checks: without the single largest ISO week (by markets) / (by summed excess) and the single largest event (the
    same two ways). Both readings of 'largest' are applied (the stricter of the two binds)."""
    wk = np.array([m["week"] for m in mk])
    ev = np.array([m["event"] for m in mk])
    v = np.array([m["v"] for m in mk], float)
    out = {}
    for name, cl in (("week", wk), ("event", ev)):
        cnt = Counter(cl.tolist())
        by_n = sorted(cnt, key=lambda k: (-cnt[k], k))[0]
        sums: dict[str, float] = {}
        for k, x in zip(cl.tolist(), v.tolist(), strict=True):
            sums[k] = sums.get(k, 0.0) + x
        by_v = sorted(sums, key=lambda k: (-sums[k], k))[0]
        out[f"{name}_by_count"] = cl != by_n
        out[f"{name}_by_excess"] = cl != by_v
    return out


def copula_pstar(week_code: np.ndarray, event_code: np.ndarray, unit_mk: np.ndarray, unit_pf: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Per-market mean of ``Y* - p_f`` with ``Y*_m = 1{Phi(Z_m) < p_f}``, ``Z_m = sqrt(.2) W_week + sqrt(.4) V_event + sqrt(.4) e_m`` (one Z per market, shared by
    its horizons)."""
    from scipy.stats import norm  # noqa: PLC0415

    nm = int(unit_mk.max()) + 1 if len(unit_mk) else 0
    wk = rng.standard_normal(int(week_code.max()) + 1 if len(week_code) else 0)
    ev = rng.standard_normal(int(event_code.max()) + 1 if len(event_code) else 0)
    eps = rng.standard_normal(nm)
    z = math.sqrt(GPP_LOADINGS[0]) * wk[week_code] + math.sqrt(GPP_LOADINGS[1]) * ev[event_code] + math.sqrt(GPP_LOADINGS[2]) * eps
    y = (norm.cdf(z)[unit_mk] < unit_pf).astype(float)
    e = y - unit_pf
    return np.bincount(unit_mk, weights=e, minlength=nm) / np.maximum(np.bincount(unit_mk, minlength=nm), 1)


def sim_arrays(units: list[dict]) -> dict:
    import pandas as pd  # noqa: PLC0415

    mk = market_means([{**u, "E": 0.0} for u in units])
    mid_code = {m["market_id"]: i for i, m in enumerate(mk)}
    wcodes, _ = pd.factorize(np.array([m["week"] for m in mk]))
    ecodes, _ = pd.factorize(np.array([m["event"] for m in mk]))
    return {"mk": mk, "week_code": np.asarray(wcodes, int), "event_code": np.asarray(ecodes, int), "unit_mk": np.array([mid_code[u["market_id"]] for u in units], int),
            "unit_pf": np.array([u["p_f"] for u in units], float)}


def gpp(units: list[dict], *, n_draws: int = GPP_DRAWS, n_inner: int = GPP_INNER, seed: int = c11.SEED_GPP) -> dict:
    """Power gate (feature-only; round 1 item 4): simulate calibrated outcomes with the shared week factor, take the event-way and week-way cluster-bootstrap SEs of
    Ē*; ``SD_P = max(SD(Ē*) across draws, mean event SE, mean week SE)``; ``MDE_P1 = (z_.99 + z_.80) x 1.2 x SD_P``. MDE > 6.0c -> 'not run (power)'."""
    if len(units) < 10:
        return {"mde": math.nan, "pass": False, "n_units": len(units), "note": "too few units"}
    A = sim_arrays(units)
    rng = np.random.default_rng(seed)
    means, se_e, se_w = [], [], []
    ev = np.array([m["event"] for m in A["mk"]])
    wk = np.array([m["week"] for m in A["mk"]])
    for _ in range(n_draws):
        e = copula_pstar(A["week_code"], A["event_code"], A["unit_mk"], A["unit_pf"], rng)
        means.append(float(e.mean()))
        se_e.append(pa.boot_se(e, ev, rng, n_inner))
        se_w.append(pa.boot_se(e, wk, rng, n_inner))
    sd_draws = float(np.std(means, ddof=1))
    sd_p = max(sd_draws, float(np.nanmean(se_e)), float(np.nanmean(se_w)))
    mde = pa.MDE_Z * MDE_FACTOR * sd_p
    return {"mde": float(mde), "sd_across_draws": sd_draws, "mean_se_event": float(np.nanmean(se_e)), "mean_se_week": float(np.nanmean(se_w)), "sd_p": sd_p, "max_mde": GPP_MAX_MDE,
            "pass": bool(mde <= GPP_MAX_MDE), "n_draws": n_draws, "n_markets": len(A["mk"]), "n_units": len(units), "seed": seed}


def p1_placebo(units: list[dict], *, n_draws: int = c11.PLACEBO_DRAWS, seed: int = c11.PLACEBO_SEEDS["P1_copula"]) -> dict:
    """Binding calibration placebo: outcomes replaced by calibrated copula outcomes with the shared week factor; a draw advances iff its p < 0.01 (floors off)."""
    A = sim_arrays(units)
    rng = np.random.default_rng(seed)
    ev = np.array([m["event"] for m in A["mk"]])
    wk = np.array([m["week"] for m in A["mk"]])
    ps = []
    for _ in range(n_draws):
        e = copula_pstar(A["week_code"], A["event_code"], A["unit_mk"], A["unit_pf"], rng)
        cp = c11.cluster_p_week(e, {"event": ev}, wk, alpha=c11.GATE_P)
        ps.append(float(cp["p"]) if cp["testable"] else 1.0)
    out = c11.placebo_advance_rate(ps)
    out["note"] = "P1 copula placebo with the shared week factor (calibrated outcomes); advance iff p < 0.01 (floors off)"
    return out


def horizon_means(units: list[dict]) -> dict:
    out = {}
    for h in HORIZONS:
        us = [u for u in units if u["h"] == h]
        out[str(h)] = {"n": len(us), "mean": float(np.mean([u["E"] for u in us])) if us else math.nan}
    return out


def p1_stat(units_pol: list[dict], units_ctl: list[dict], *, ext: dict, alpha: float = c11.GATE_P, n_draws: int = c11.PLACEBO_DRAWS, placebo: bool = True,
            reach: dict[str, dict] | None = None, tx_loader: Callable[[str], tuple | None] | None = None) -> dict:
    """P1 on SCREEN (or HOLDOUT) politics units. ``units_*`` carry ``Y``, ``Y_worst`` and the flags; ``ext`` carries ``t5_absent``, the half-window bounds and the
    counts of unresolved / voided / unclean markets."""
    P = with_excess([u for u in units_pol if in_band(u)])
    mk = market_means(P)
    core = p1_core(mk, alpha=None)
    out: dict = {**{k: core[k] for k in ("n", "mean", "testable", "p", "week_rule_holds")}, "ways": core.get("ways"), "week": core.get("week"), "floor": P1_FLOOR,
                 "label": "L1, hindsight end date", "n_units": len(P), "by_horizon": horizon_means(P)}
    out["core_ok"] = p1_ok(core, P1_FLOOR, gate=alpha)
    if not core["testable"]:
        return {**out, "advance": False, "p": 1.0, "verdict": "not testable (units or clusters)"}
    out["placebo"] = p1_placebo(P, n_draws=n_draws) if placebo else {"n_draws": 0, "holds": True, "advance_rate": None, "note": "skipped"}
    # election concentration (binding)
    masks = drop_masks(mk)
    conc = {}
    for name, keep in masks.items():
        sub = [m for m, k in zip(mk, keep, strict=True) if k]
        r = p1_core(sub, alpha=None)
        conc[name] = {"n": r["n"], "mean": r["mean"], "p": r["p"], "ok": bool(r["testable"] and r["week_rule_holds"] and r["p"] < alpha and r["mean"] >= ELECTION_FLOOR)}
    out["concentration"] = conc
    out["concentration_ok"] = all(v["ok"] for v in conc.values())
    # attribution (label only)
    C = with_excess([u for u in units_ctl if in_band(u)])
    mc = market_means(C)
    ec = float(np.mean([m["v"] for m in mc])) if mc else math.nan
    out["attribution_control"] = {"n_control_markets": len(mc), "mean_control": ec, "gap": out["mean"] - ec if math.isfinite(ec) else math.nan,
                                  "politics_specific": bool(math.isfinite(ec) and out["mean"] - ec >= ATTR_CTRL_GAP), "label_if_not": "long-horizon favourite underpricing, not political"}
    out["robustness"] = p1_robustness(P, mk, units_pol, ext=ext, alpha=alpha)
    # top-5 cluster drops (common robustness ii)
    drop = {}
    v = np.array([m["v"] for m in mk], float)
    for way in ("event", "week"):
        cl = np.array([m[way] for m in mk])
        keep = c11.c9.top_k_drop_mask(v, cl, c11.TOP_DROP)
        r = p1_core([m for m, k in zip(mk, keep, strict=True) if k], alpha=None)
        drop[way] = {"n": r["n"], "mean": r["mean"], "p": r["p"], "ok": p1_ok(r, P1_FLOOR, gate=alpha)}
    out["without_top5"] = drop
    out["without_top5_ok"] = all(x["ok"] for x in drop.values())
    # reported (uncounted)
    out["reported"] = p1_reported(P, C, units_pol, reach, tx_loader, ext)
    out["advance"] = bool(out["core_ok"] and out["placebo"].get("holds") and out["concentration_ok"] and out["robustness"]["ok"] and out["without_top5_ok"])
    out["verdict"] = "advance" if out["advance"] else ("floor / p not met" if not out["core_ok"] else "placebo or robustness failed")
    return out


def _mean_v(mk: list[dict]) -> float:
    return float(np.mean([m["v"] for m in mk])) if mk else math.nan


def p1_robustness(P: list[dict], mk: list[dict], units_all: list[dict], *, ext: dict, alpha: float) -> dict:
    """Binding robustness: each horizon keeps the sign; print-based price keeps the sign and >= half (see ``p1_reported`` for the data); band [0.55, 0.90] keeps the
    sign; each SCREEN half keeps the sign; excluding ``late_close`` / ``edit_detected`` markets, and excluding the 2024-election events, keep p < 0.01 and Ē >= 1.5c;
    unclean outcomes scored 0 keep the sign; if the T5 ids were absent, excluding SCREEN ends in the T5 overlap keeps the sign."""
    out: dict = {}
    hz = horizon_means(P)
    out["by_horizon"] = {h: {**v, "ok": bool(v["n"] > 0 and v["mean"] > 0)} for h, v in hz.items()}
    wide = with_excess([u for u in units_all if in_band(u, BAND_WIDE)])
    out["band_wide"] = {"mean": _mean_v(market_means(wide)), "ok": bool(wide and _mean_v(market_means(wide)) > 0)}
    halves = {}
    for lo, hi in ext.get("halves", P_SCREEN_HALVES):
        sub = [m for m in mk if _ep(lo) <= m["end"] < _ep(hi)]
        halves[f"{lo}..{hi}"] = {"n": len(sub), "mean": _mean_v(sub), "ok": bool(sub and _mean_v(sub) > 0)}
    out["halves"] = halves
    for name, pred in (("exclude_flagged", lambda m: not (m["edit"] or m["late"])), ("exclude_election2024", lambda m: not m["elec"])):
        sub = [m for m in mk if pred(m)]
        r = p1_core(sub, alpha=None)
        out[name] = {"n": r["n"], "mean": r["mean"], "p": r["p"], "ok": bool(r["testable"] and r["week_rule_holds"] and r["p"] < alpha and r["mean"] >= P1_FLAG_FLOOR)}
    worst = with_excess([u for u in units_all if in_band(u)], worst=True)
    out["unclean_as_zero"] = {"mean": _mean_v(market_means(worst)), "ok": bool(worst and _mean_v(market_means(worst)) > 0)}
    if ext.get("t5_absent"):
        sub = [m for m in mk if not (_ep(T5_OVERLAP[0]) <= m["end"] < _ep(T5_OVERLAP[1]))]
        out["exclude_t5_window"] = {"n": len(sub), "mean": _mean_v(sub), "ok": bool(sub and _mean_v(sub) > 0), "binding": True}
    flat = [v for k, v in out.items() if isinstance(v, dict) and "ok" in v]
    flat += [v for h in (out["by_horizon"], halves) for v in h.values()]
    out["ok"] = all(x["ok"] for x in flat)
    return out


def p1_reported(P: list[dict], C: list[dict], units_all: list[dict], reach: dict[str, dict] | None, tx_loader, ext: dict) -> dict:
    """Reported (uncounted): logistic calibration slopes (politics vs control), the liquidity stratum, the unclean / voided counts, the print-price variant and the
    Data-API-verified-activity variant on the reachable subset."""
    out: dict = {}
    for name, us in (("politics", P), ("control", C)):
        cl = [u for u in us if u["ystat"] == "clean"]
        if len(cl) >= 10:
            x = np.log(np.array([u["p"] if u["k"] == 0 else 1 - u["p"] for u in cl]) / (1 - np.array([u["p"] if u["k"] == 0 else 1 - u["p"] for u in cl])))
            out[f"slope_{name}"] = pa.logistic_slope(np.array([u["Y"] for u in cl]), x)
    if P:
        terc = pa.tercile_labels(np.array([u["n_distinct"] for u in P], float))
        out["liquidity_stratum"] = {t: {"n": int((terc == t).sum()), "mean": _mean_v(market_means([u for u, tt in zip(P, terc, strict=True) if tt == t]))} for t in ("low", "mid", "high")}
    out["counts_unclean"] = dict(Counter(u["ystat"] for u in {u["market_id"]: u for u in P}.values()))
    if reach and tx_loader:
        pr, ver = [], []
        for u in P:
            r = reach.get(u["market_id"])
            if not r or r["status"] != "ok":
                continue
            tx = tx_loader(u["market_id"])
            oldest = pa.fnum(r["oldest_ts"])
            trunc = str(r["truncated"]) in ("1", "True")
            if (not trunc or (math.isfinite(oldest) and oldest <= u["t_h"] - DAY)) and tx is not None and len(tx[0]):
                lo = np.searchsorted(tx[0], u["t_h"] - DAY, side="left")
                hi = np.searchsorted(tx[0], u["t_h"], side="left")
                if hi > lo:
                    p_last = float(tx[1][hi - 1])
                    pf_last = p_last if u["k"] == 0 else 1.0 - p_last
                    pr.append({**u, "E": u["Y"] - pf_last})
            if (not trunc or (math.isfinite(oldest) and oldest <= u["t_h"] - 7 * DAY)) and tx is not None and len(tx[0]):
                lo = np.searchsorted(tx[0], u["t_h"] - 7 * DAY, side="left")
                hi = np.searchsorted(tx[0], u["t_h"], side="left")
                if hi > lo:
                    ver.append({**u, "E": u["Y"] - u["p_f"]})
        out["print_price_variant"] = {"n_units": len(pr), "mean": _mean_v(market_means(pr)) if pr else math.nan}
        out["verified_activity_variant"] = {"n_units": len(ver), "mean": _mean_v(market_means(ver)) if ver else math.nan}
        base_sub = {u["market_id"] for u in pr}
        base = with_excess([u for u in P if u["market_id"] in base_sub])
        out["print_price_variant"]["primary_on_same_subset"] = _mean_v(market_means(base)) if base else math.nan
        pm, bm = out["print_price_variant"]["mean"], out["print_price_variant"]["primary_on_same_subset"]
        out["print_price_variant"]["ok"] = bool(pr and math.isfinite(pm) and pm > 0 and (not math.isfinite(bm) or pm >= 0.5 * bm))
    return out


# =====================================================================================================================================
# P2
# =====================================================================================================================================


def fee_r(rate: float) -> float:
    return max(rate if math.isfinite(rate) else 0.0, FEE_R_MIN)


def p2_entries(units: list[dict], *, half_spread: float = ASK_HALF_SPREAD, exclude=None) -> list[dict]:
    """One entry per market at its earliest P unit (90, else 60, else 30 days) at ``a = p_f + half_spread``, fee ``r a (1 - a)``, held to resolution."""
    best: dict[str, dict] = {}
    for u in units:
        if exclude and exclude(u):
            continue
        b = best.get(u["market_id"])
        if b is None or u["h"] > b["h"]:
            best[u["market_id"]] = u
    out = []
    for _mid, u in sorted(best.items()):
        a = min(u["p_f"] + half_spread, 0.999)
        fee = fee_r(u["fee_rate"]) * a * (1 - a)
        close = u.get("closed", math.nan)
        d = (close - u["t_h"]) / DAY if math.isfinite(close) else h_days(u)
        out.append({**u, "a": a, "fee": fee, "net": u["Y"] - a - fee, "hold_d": d, "hold_fallback": not math.isfinite(close), "v": u["Y"] - a - fee})
    return out


def h_days(u: dict) -> float:
    return float(u["h"])  # scheduled hold (end - t_h) when the close time is missing (counted)


def r_ann(entries: list[dict]) -> float:
    """``365 * sum(net) / sum(a * max(d, 1))`` (CB1 definition, days)."""
    den = sum(e["a"] * max(e["hold_d"], 1.0) for e in entries)
    return float(365.0 * sum(e["net"] for e in entries) / den) if den > 0 else math.nan


def p2_core(entries: list[dict], *, alpha: float | None = None) -> dict:
    mk = [{"market_id": e["market_id"], "event": e["event"], "week": e["week"], "v": e["net"]} for e in entries]
    return p1_core(mk, alpha=alpha)


def p2_stat(units_pol: list[dict], *, ext: dict, alpha: float = c11.GATE_P) -> dict:
    P = [u for u in units_pol if in_band(u)]
    ent = p2_entries(P)
    core = p2_core(ent)
    rann = r_ann(ent)
    out: dict = {"n": len(ent), "net_mean": core["mean"], "p": core["p"], "testable": core["testable"], "week_rule_holds": core["week_rule_holds"], "r_ann": rann,
                 "r_ann_excess": rann - RF_RATE if math.isfinite(rann) else math.nan, "floors": {"net": P2_NET_FLOOR, "r_ann_excess": P2_RANN_FLOOR},
                 "label": "L1, hindsight end date; modelled ask (declared half-spread 1.5c)", "hold_fallback": int(sum(e["hold_fallback"] for e in ent)), "effect": core["mean"]}
    out["by_horizon"] = {}
    for h in HORIZONS:
        eh = p2_entries([u for u in P if u["h"] == h])
        out["by_horizon"][str(h)] = {"n": len(eh), "net_mean": float(np.mean([e["net"] for e in eh])) if eh else math.nan, "r_ann": r_ann(eh)}
    out["resolved_before_scheduled_end_share"] = float(np.mean([e["closed"] < e["end"] for e in ent if math.isfinite(e.get("closed", math.nan))])) if any(math.isfinite(e.get("closed", math.nan)) for e in ent) else math.nan
    if not core["testable"]:
        return {**out, "advance": False, "p": 1.0, "verdict": "not testable (units or clusters)"}
    floors = {"net": bool(core["mean"] >= P2_NET_FLOOR), "r_ann_excess": bool(math.isfinite(rann) and rann - RF_RATE >= P2_RANN_FLOOR), "p": bool(core["p"] < alpha and core["week_rule_holds"])}
    out["floors"] = floors
    rob: dict = {}
    wide = p2_entries(P, half_spread=ASK_HALF_SPREAD_ROBUST)
    rob["half_spread_2_5c"] = {"net_mean": float(np.mean([e["net"] for e in wide])) if wide else math.nan, "ok": bool(wide and np.mean([e["net"] for e in wide]) > 0)}
    for name, ex in (("exclude_flagged", lambda u: bool(u["edit"] or u["late"])), ("exclude_election2024", lambda u: bool(u["elec"]))):
        e2 = p2_entries(P, exclude=ex)
        rob[name] = {"n": len(e2), "net_mean": float(np.mean([e["net"] for e in e2])) if e2 else math.nan, "ok": bool(e2 and np.mean([e["net"] for e in e2]) > 0)}
    halves = {}
    for lo, hi in ext.get("halves", P_SCREEN_HALVES):
        e2 = [e for e in ent if _ep(lo) <= e["end"] < _ep(hi)]
        halves[f"{lo}..{hi}"] = {"n": len(e2), "net_mean": float(np.mean([e["net"] for e in e2])) if e2 else math.nan, "ok": bool(e2 and np.mean([e["net"] for e in e2]) > 0)}
    rob["halves"] = halves
    top = {}
    v = np.array([e["net"] for e in ent], float)
    for way in ("event", "week"):
        cl = np.array([e[way] for e in ent])
        keep = c11.c9.top_k_drop_mask(v, cl, c11.TOP_DROP)
        r = p2_core([e for e, k in zip(ent, keep, strict=True) if k])
        top[way] = {"n": r["n"], "net_mean": r["mean"], "p": r["p"], "ok": bool(r["testable"] and r["week_rule_holds"] and r["p"] < alpha and r["mean"] >= P2_NET_FLOOR)}
    rob["without_top5"] = top
    rob["ok"] = bool(rob["half_spread_2_5c"]["ok"] and rob["exclude_flagged"]["ok"] and rob["exclude_election2024"]["ok"] and all(x["ok"] for x in halves.values())
                     and all(x["ok"] for x in top.values()))
    out["robustness"] = rob
    out["advance"] = bool(all(floors.values()) and rob["ok"])
    out["verdict"] = "advance" if out["advance"] else "floors or robustness not met"
    return out


# =====================================================================================================================================
# Census (q0239, P part): counts only
# =====================================================================================================================================


def census_p(rdir: Path, *, n_draws: int = GPP_DRAWS, n_inner: int = GPP_INNER) -> dict:
    """Counts only (design 2.7 P). Reads the SCREEN frame, flags and origins (never a guarded file) and the HOLDOUT unit COUNT (rows, never the prices). Computes GP,
    the coverage audit and GPP (feature-only). No outcome, excess, ``late_close`` flag or P&L is computed here."""
    rdir = Path(rdir)
    frame = read_frame(rdir, "screen", job="census")
    flags = {str(r["market_id"]): r for r in c11.read_csv_gz(rdir / "flags.csv.gz")}
    origins = load_origins(rdir, "screen", job="census")
    split = json.loads((rdir / "split.json").read_text())
    c1t5 = split.get("c1_t5_status", "absent")
    n_hold_origins = sum(1 for _ in c11.read_csv_gz(rdir / HOLD_DIR / "origins.csv.gz")) if (rdir / HOLD_DIR / "origins.csv.gz").exists() else 0
    n_hold_markets = sum(1 for _ in c11.read_csv_gz(rdir / HOLD_DIR / "frame_hold.csv.gz")) if (rdir / HOLD_DIR / "frame_hold.csv.gz").exists() else 0
    pol = [r for r in frame if r["group"] == "pol"]
    lab_by_h = {h: Counter(o["label"] for o in origins if int(o["h"]) == h and next((r["group"] for r in pol if r["market_id"] == o["market_id"]), None) == "pol") for h in HORIZONS}
    pol_ids = {r["market_id"] for r in pol}
    pol_orig = [o for o in origins if o["market_id"] in pol_ids]
    units = build_units(pol, pol_orig, flags, None)
    P = [u for u in units if in_band(u)]
    markets_p = {u["market_id"] for u in P}
    events, weeks = {u["event"] for u in P}, {u["week"] for u in P}
    labels = Counter(o["label"] for o in pol_orig)
    elig = sum(labels[x] for x in ELIGIBLE_LABELS)
    priced = labels[LABEL_OK] + labels[LABEL_INACTIVE]
    gp = {"markets": len(markets_p), "events": len(events), "weeks": len(weeks), "need": GP, "pass": bool(len(markets_p) >= GP["markets"] and len(events) >= GP["events"] and len(weeks) >= GP["weeks"])}
    cover = {"eligible_units": elig, "priced_units": priced, "share": priced / elig if elig else 0.0, "min": COVER_MIN, "pass": bool(elig and priced / elig >= COVER_MIN)}
    fm = {r["market_id"]: r for r in pol}
    month_ct = Counter(pa.month_of(float(fm[m]["end_epoch"])) for m in markets_p)
    terc = pa.tercile_labels(np.array([u["n_distinct"] for u in P], float)) if P else np.array([])
    doc: dict = {"version": "cb11-p-census-v1", "counts_only": True, "frame": {"n_screen": len(frame), "n_pol": len(pol), "n_ctl": len(frame) - len(pol), "split_report": split.get("report"),
                                                                                  "hold_markets": n_hold_markets, "hold_origin_rows": n_hold_origins},
                 "c1_t5_status": c1t5, "labels": dict(labels), "labels_by_horizon": {str(h): dict(c) for h, c in lab_by_h.items()},
                 "units_in_band_by_horizon": {str(h): sum(1 for u in P if u["h"] == h) for h in HORIZONS}, "markets_with_p_unit": len(markets_p), "events": len(events), "weeks": len(weeks),
                 "markets_by_month": dict(sorted(month_ct.items())), "flags": {"edit_detected": sum(1 for m in markets_p if str(flags.get(m, {}).get("edit_detected")) in ("1", "True")),
                                                                              "election2024": sum(1 for m in markets_p if str(flags.get(m, {}).get("election2024")) in ("1", "True")),
                                                                              "late_close_flag": "guarded (closedTime): not read by the census"},
                 "liquidity_terciles": {t: int((terc == t).sum()) for t in ("low", "mid", "high")} if len(terc) else {}, "GP": gp, "coverage_audit": cover}
    label = None
    if not gp["pass"]:
        label = "not testable (GP: markets, events or weeks)"
    elif not cover["pass"]:
        label = "not testable (source limited)"
    doc["GPP"] = gpp(P, n_draws=n_draws, n_inner=n_inner) if P else {"pass": False, "note": "no units"}
    if label is None and not doc["GPP"]["pass"]:
        label = "not run (power)"
    doc["label_P1"] = doc["label_P2"] = label
    doc["p_runs"] = label is None
    return doc


# =====================================================================================================================================
# Screen / rep
# =====================================================================================================================================


def _ext(rdir: Path, census: dict) -> dict:
    return {"t5_absent": (census.get("P") or {}).get("c1_t5_status", "absent") != "retrieved", "halves": P_SCREEN_HALVES}


def tx_loader_for(rdir: Path) -> Callable[[str], tuple | None]:
    def load(mid: str):
        p = Path(rdir) / "screen" / "tx" / f"{mid}.tx.csv.gz"
        return pa.read_tx_file(p) if p.exists() else None

    return load


def _prepare(rdir: Path, split: str, job: str) -> tuple[list[dict], list[dict]]:
    rdir = Path(rdir)
    gname = "outcomes_guarded.csv.gz" if split == "screen" else "outcomes_guarded_hold.csv.gz"
    gpath = rdir / ("" if split == "screen" else HOLD_DIR) / gname
    fpath = "flags.csv.gz" if split == "screen" else "flags_hold.csv.gz"
    frame = read_frame(rdir, split, job=job)
    flags = {str(r["market_id"]): r for r in c11.read_csv_gz(rdir / ("" if split == "screen" else HOLD_DIR) / fpath)}
    guarded = {str(r["market_id"]): r for r in open_p_guarded(gpath, job)}
    origins = load_origins(rdir, split, job=job)
    unit_all = build_units(frame, origins, flags, guarded, labels=(LABEL_OK,))
    return [u for u in unit_all if u["group"] == "pol"], [u for u in unit_all if u["group"] == "ctl"]


def availability(origins: list[dict], group: str, ids: set[str]) -> dict:
    sub = [o for o in origins if o["market_id"] in ids]
    c = Counter(o["label"] for o in sub)
    elig = sum(c[x] for x in ELIGIBLE_LABELS)
    priced = c[LABEL_OK] + c[LABEL_INACTIVE]
    return {"eligible": elig, "available": priced, "share": priced / elig if elig else 0.0, "min": AVAIL_MIN, "ok": bool(elig and priced / elig >= AVAIL_MIN), "labels": dict(c)}


def screen_p(rdir: Path, census: dict, *, n_draws: int = c11.PLACEBO_DRAWS) -> dict:
    """P1 and P2 Stage 1 on the SCREEN markets (the caller checked the freeze, the census labels and the fetch manifest). Opens the SCREEN guarded file only."""
    rdir = Path(rdir)
    cp = census.get("P") or {}
    res: dict = {}
    lab = cp.get("label_P1")
    if lab:
        return {"P1": {"testable": False, "p": 1.0, "advance": False, "verdict": lab}, "P2": {"testable": False, "p": 1.0, "advance": False, "verdict": cp.get("label_P2") or lab}}
    pol, ctl = _prepare(rdir, "screen", "screen-P")
    frame = read_frame(rdir, "screen", job="screen-P")
    origins = load_origins(rdir, "screen", job="screen-P")
    av = availability(origins, "pol", {r["market_id"] for r in frame if r["group"] == "pol"})
    if not av["ok"]:
        v = "not testable (availability)"
        return {"P1": {"testable": False, "p": 1.0, "advance": False, "verdict": v, "availability": av}, "P2": {"testable": False, "p": 1.0, "advance": False, "verdict": v, "availability": av}}
    ext = _ext(rdir, census)
    reach = load_reach(rdir)
    res["P1"] = p1_stat(pol, ctl, ext=ext, n_draws=n_draws, reach=reach, tx_loader=tx_loader_for(rdir))
    res["P1"]["availability"] = av
    res["P2"] = p2_stat(pol, ext=ext)
    res["P2"]["availability"] = av
    return res


def rep_p(rdir: Path, census: dict, advanced: tuple[str, ...], k: int, *, n_draws: int = c11.PLACEBO_DRAWS, seals_dir: Path | None = None) -> dict:
    """Stage 2 on the sealed HOLDOUT ends [2026-01-01, 2026-09-01) (same rules; judged at alpha / k by the caller). Verifies the seal first and logs the access."""
    rdir = Path(rdir)
    c11.verify_holdout_seal(rdir, SEAL_COPY_NAME, seals_dir)
    log_access(rdir, "rep-P", ["holdout/frame_hold.csv.gz", "holdout/origins.csv.gz", "holdout/outcomes_guarded_hold.csv.gz"])
    thr = c11.STAGE2_ALPHA / k
    cp = census.get("P") or {}
    absent = cp.get("c1_t5_status", "absent") != "retrieved"
    out: dict = {"label": "possibly touched holdout (L1, not L2)" if absent else "out-of-time replication on sealed later ends (L2)", "stage2_alpha_over_k": thr, "k": k}
    pol, ctl = _prepare(rdir, "holdout", "rep-P")
    ext = {"t5_absent": False, "halves": ((P_HOLD[0], "2026-05-01"), ("2026-05-01", P_HOLD[1]))}
    if "P1" in advanced:
        r = p1_stat(pol, ctl, ext=ext, alpha=thr, n_draws=n_draws)
        r["stage2_pass_alpha_over_k"] = bool(r.get("testable") and r.get("p", 1.0) <= thr and r.get("advance"))
        out["P1_rep"] = r
    if "P2" in advanced:
        r = p2_stat(pol, ext=ext, alpha=thr)
        r["stage2_pass_alpha_over_k"] = bool(r.get("testable") and r.get("p", 1.0) <= thr and r.get("advance"))
        out["P2_rep"] = r
    return out


def holdout_counts(rdir: Path) -> dict:
    """Census access to HOLDOUT: the listing's file and row counts only (never the prices)."""
    rdir = Path(rdir)
    fh = rdir / HOLD_DIR / "frame_hold.csv.gz"
    return {"n_markets": sum(1 for _ in c11.read_csv_gz(fh)) if fh.exists() else 0}


def seal_rows(rdir: Path) -> list[dict]:
    """The HOLDOUT markets (ids and keys only) for the seal-time drops."""
    p = Path(rdir) / HOLD_DIR / "frame_hold.csv.gz"
    return [{"market_id": r["market_id"], "event_ids": r["event_ids"], "neg_risk_market_id": r["neg_risk_market_id"], "series_ids": r["series_ids"]} for r in c11.read_csv_gz(p)] if p.exists() else []


def declared() -> dict:
    return {"windows": {"screen": list(P_SCREEN), "holdout": list(P_HOLD), "halves": [list(x) for x in P_SCREEN_HALVES], "t5_overlap": list(T5_OVERLAP)},
            "tag_id": POL_TAG, "horizons": list(HORIZONS), "band": list(BAND), "band_wide": list(BAND_WIDE), "min_life_d": MIN_LIFE_D, "listed_before_d": LISTED_BEFORE_D,
            "frame": {"start_filter_d": START_FILTER_D, "window_s": WINDOW_S, "per_event": MAX_PER_EVENT, "n_pol": N_POL, "n_ctl": N_CTL, "control_pool_mult": CONTROL_POOL_MULT,
                      "control_max_requests": CONTROL_MAX_REQUESTS, "seeds": [SEED_POL_CAP, SEED_POL_SAMPLE, SEED_CTL_CAP, SEED_CTL_SAMPLE, SEED_CTL_WINDOWS],
                      "excluded_topics": list(EXCLUDED_TOPICS), "no_status_filter": True},
            "price_rule": {"lag_s": LAG_S, "age_max_s": AGE_MAX_S, "fidelity": FIDELITY, "window": "[t_h - 7 d, t_h]", "activity": ">= 2 distinct values among points known in [t_h - 7 d, t_h)",
                           "favourite_tie": "outcome 0 at p = 0.5"},
            "prints": {"limit": DATA_PAGE_LIMIT, "pages": DATA_PAGES, "taker_only": TAKER_ONLY},
            "flags": {"cal_date_re": CAL_DATE_RE, "iso_date_re": ISO_DATE_RE, "edit_days": EDIT_DAYS, "late_close_s": LATE_CLOSE_S, "election_end_window": list(ELECTION_END_WINDOW),
                      "election_year_re": ELECTION_YEAR_RE, "election_with_year_re": ELECTION_WITH_YEAR_RE, "election_name_re": ELECTION_NAME_RE},
            "floors": {"p1": P1_FLOOR, "p1_flag": P1_FLAG_FLOOR, "election": ELECTION_FLOOR, "attr_gap": ATTR_CTRL_GAP, "p2_net": P2_NET_FLOOR, "p2_rann_excess": P2_RANN_FLOOR, "rf": RF_RATE},
            "costs": {"ask_half_spread": ASK_HALF_SPREAD, "ask_half_spread_robust": ASK_HALF_SPREAD_ROBUST, "fee_r_min": FEE_R_MIN},
            "gates": {"GP": GP, "coverage_min": COVER_MIN, "availability_min": AVAIL_MIN, "GPP": {"max_mde": GPP_MAX_MDE, "draws": GPP_DRAWS, "inner": GPP_INNER, "loadings": list(GPP_LOADINGS),
                                                                                              "factor": MDE_FACTOR, "seed": c11.SEED_GPP}},
            "placebo": {"seed": c11.PLACEBO_SEEDS["P1_copula"], "draws": c11.PLACEBO_DRAWS}, "unclean_outcome_value": 0.5, "census_forbidden": list(CENSUS_FORBIDDEN),
            "columns": {"frame": FRAME_COLUMNS, "guarded": GUARDED_COLUMNS, "origins": ORIGIN_COLUMNS}, "labels": [LABEL_OK, LABEL_INACTIVE, LABEL_NO_PRICE, LABEL_NOT_LISTED, LABEL_CLOSED, LABEL_NO_CLOSE, LABEL_FAILED]}


def rule_funcs() -> tuple:
    return (split_of, t_h, named_dates, edit_detected, election_2024, late_close, week_windows, walk_window, frame_record, assemble, _walk_records, pol_frame, read_frame,
            read_frame_for_fetch, price_point, unit_label, pol_prices, open_p_guarded, load_origins, load_reach, y_fav, fav_of, build_units, in_band, market_means, with_excess,
            p1_core, p1_ok, drop_masks, copula_pstar, sim_arrays, gpp, p1_placebo, horizon_means, p1_stat, p1_robustness, p1_reported, fee_r, p2_entries, r_ann, p2_core, p2_stat,
            census_p, availability, screen_p, rep_p, seal_rows, declared)
