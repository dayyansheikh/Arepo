# ruff: noqa: E501
"""LIVE prospective tests LT6 (docs/research_lab/LIVE_TESTS_6.md, as amended by sections 14 and 15; section 15 governs, then 14).
DRAFT: nothing is registered; E-numbers are assigned at registration; the dates are null placeholders until E022 is
registered or dropped. Research tooling only; never trades; no network request.

This first code unit holds the pure, synthetic-testable rules the four tests (V the makers' vote, K clip trains, D deadline
moves, B sibling birth) share with the future reader and the censuses:

* the spec loader and the code pins (LT5 style; ``SPEC_SHA256 = None`` while a DRAFT);
* the registration-date rule and V's E022 freeze condition (1.1): a pin at or after either E022 time refuses;
* the pinned crypto classifier (section 5 as pinned by the R1 re-check);
* K's deterministic greedy clip-train algorithm (section 3 as amended by R1 item 12 and the re-check): ``Decimal`` sizes,
  ``statistics.median``, ``2 x order_min_size`` in ``Decimal``;
* V's state (vote, pre-move vote, toward / away depth, hollowness) and the depletion gates (section 7);
* D's deadline-template classifier, parse rules, change classes, ``theta24``;
* B's newcomer, birth, lagged-appearance and clean no-birth classes, the guard, the fake-birth draw;
* the washout rule of 1.7.

LT3/LT4/LT5 code is used by importing the existing helpers (``live_tests5_base``, ``live_tests5``, ``live_tests3``); none is
edited. The design's 8.1 asks for a generated vendored base after LT5's pin; that step is deferred (see the spec's
``vendored_source_drift_rule``).
"""

from __future__ import annotations

import json
import math
import re
import statistics
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import forecast
from . import live_tests5_base as b

VERSION = "live-tests6-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = ROOT / "data-dumps" / "research_lab" / "trade_samples"
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests6"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests6_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration
REGISTERED_UTC: str | None = None  # DRAFT: null until E022 registers or drops (1.1); see registered_utc_rule
END_UTC: str | None = None
ANALYSIS_NOT_BEFORE: str | None = None
TEMPFAIL = 75
DAY_S = 86400.0
FLOOR_REGISTERED_UTC = "2026-11-16T00:00:00Z"
CODE_FILES = ("live_tests6.py", "live_tests6_analysis.py",
              # imported helpers and dependencies (the vendored base of design 8.1 is replaced by these imports for now)
              "live_tests5_base.py", "live_tests5.py", "live_tests3.py", "live_tests3_analysis.py", "bounce_decomp.py",
              "maker_rewards.py", "panel.py", "trade_sample.py", "cb17_census.py", "cb13_label.py", "economics.py", "forecast.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)

epoch, iso, sha256_file, _json = b.epoch, b.iso, b.sha256_file, b._json


# --- pins and spec ---------------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    import hashlib

    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    """Normalised hash of every code file; a file that does not exist yet (the analysis module before step 3) maps to None."""
    here = Path(__file__).resolve().parent
    return {n: (code_sha256(here / n) if (here / n).exists() else None) for n in CODE_FILES}


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    """The spec as written. DRAFT (``sha is None``): null placeholders are allowed. Pinned: the hash must match, no
    placeholder may remain null (see :func:`unfilled`) and the spec's dates must equal the module constants (L6)."""
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"live_tests6 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests6 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    if sha is not None:
        miss = unfilled(spec)
        if miss:
            raise RuntimeError(f"live_tests6 pinned spec has null / NaN placeholders: {miss[:10]}")
    return spec


def _nanlike(v) -> bool:
    """None, a non-finite float, a "nan"-like string, or a list / dict holding one."""
    if isinstance(v, (list, tuple)):
        return any(_nanlike(x) for x in v)
    if isinstance(v, dict):
        return any(_nanlike(x) for x in v.values())
    return v is None or (isinstance(v, float) and not math.isfinite(v)) or (isinstance(v, str) and v.strip().lower() in ("nan", "inf", "-inf"))


# Placeholders that must be filled at registration. Everything else that is null in a DRAFT spec is allowed to stay null.
REQUIRED_AT_PIN = ("registered_utc", "end_utc", "analysis_not_before", "k_tests", "code_sha256", "e022.registered", "e022.dropped",
                   "labels.partially_seen_d")


def unfilled(spec: dict) -> list[str]:
    """Paths of null / NaN values a pinned spec must not contain: the registration placeholders, and for every test in
    ``k_tests`` its census-fixed values (centres, scales, terciles, family exclusion, permutation stratum)."""
    out = []

    def get(path: str):
        cur = spec
        for part in path.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        return cur

    for p in REQUIRED_AT_PIN:
        if p == "e022.registered":  # exactly one of registered / dropped must be set (a recorded fact), the other may be null
            if get("e022.registered") is None and get("e022.dropped") is None:
                out.append("e022.registered|e022.dropped")
        elif p == "e022.dropped":
            continue
        elif _nanlike(get(p)):
            out.append(p)
    needs = {"V": ("c_v", "s_v", "terciles", "tercile_gap", "exclude_family"), "K": ("exclude_family", "perm_stratum"),
             "D": ("exclude_family", "perm_stratum"), "B": ("exclude_family", "perm_stratum", "fake_birth_terciles")}
    for t in spec.get("k_tests") or []:
        for f in needs.get(t, ()):
            if _nanlike(spec[t.lower()].get(f)):
                out.append(f"{t.lower()}.{f}")
    return out


# --- registration dates and V's E022 freeze condition (1.1) ------------------------------------------------------------


def _parse_utc(v: str | datetime) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(UTC)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def registered_utc_rule(*, commit_utc: str, lt5_registered_utc: str, e022_end_utc: str | None = None, e022_registered: bool = False) -> dict:
    """1.1: ``REGISTERED_UTC`` is the first 00:00Z that is (a) at least 24 h after the LT6 registration commit, (b) at least
    48 h after LT5's ``REGISTERED_UTC``, (c) at or after E022's own ``END_UTC`` if E022 is registered, (d) never before
    2026-11-16T00:00Z. ``END_UTC`` = +21 d; the analysis date = ``END_UTC`` + 36 h. Uses no data. If E022 is registered
    its ``END_UTC`` must be given (while neither exists LT6 cannot register: refuse)."""
    if e022_registered and e022_end_utc is None:
        raise ValueError("E022 is registered but its END_UTC is unknown: (c) is undefined, LT6 cannot register")
    bounds = [_parse_utc(commit_utc) + timedelta(hours=24), _parse_utc(lt5_registered_utc) + timedelta(hours=48), _parse_utc(FLOOR_REGISTERED_UTC)]
    if e022_registered:
        bounds.append(_parse_utc(e022_end_utc))
    lo = max(bounds)
    day = lo.replace(hour=0, minute=0, second=0, microsecond=0)
    reg = day if day >= lo else day + timedelta(days=1)
    end = reg + timedelta(days=21)
    return {"registered_utc": _fmt(reg), "end_utc": _fmt(end), "analysis_not_before": _fmt(end + timedelta(hours=36)),
            "binding_lower_bound": _fmt(lo)}


def t_e022(analysis_job_start_utc: str | None, analysis_commit_utc: str | None) -> datetime | None:
    """``T_E022`` = the earlier of E022's analysis job start (the queue log's start time) and its analysis commit. None while
    neither exists (the analysis has not started)."""
    ts = [_parse_utc(x) for x in (analysis_job_start_utc, analysis_commit_utc) if x]
    return min(ts) if ts else None


def v_freeze_check(*, pin_commit_utc: str, e022_registered: bool, e022_dropped: bool = False, analysis_job_start_utc: str | None = None,
                   analysis_commit_utc: str | None = None) -> dict:
    """V's freeze condition (1.1; R1 re-check item 1). If E022 is registered, V may be pinned only if the LT6 registration
    commit is STRICTLY before ``T_E022`` (the earlier of E022's analysis job start and analysis commit): a pin at or after
    either time refuses, so V is dropped uncounted and k reduced before the pin. The condition lapses if E022 was dropped
    before its registration. ``ok`` False means V must be dropped."""
    if e022_dropped and not e022_registered:
        return {"ok": True, "reason": "E022 dropped before registration: the condition lapses", "t_e022": None}
    if not e022_registered:
        return {"ok": False, "reason": "E022 neither registered nor recorded as dropped: LT6 cannot register (1.1)", "t_e022": None}
    t = t_e022(analysis_job_start_utc, analysis_commit_utc)
    if t is None:
        return {"ok": True, "reason": "E022's analysis has neither started nor been committed", "t_e022": None}
    pin = _parse_utc(pin_commit_utc)
    ok = pin < t
    return {"ok": bool(ok), "t_e022": _fmt(t),
            "reason": "pin before T_E022" if ok else "pin at or after T_E022 (the earlier of E022's analysis job start and commit): V dropped uncounted"}


def v_first_origin_ok(cap_prev_start_utc: str, sweep_prev_start_utc: str, e022_end_utc: str | None) -> bool:
    """V's first origin (1.1, R1 item 7): the k - 1 capture AND the k - 1 sweep both start at or after E022's ``END_UTC``.
    A pass failing this is counted ``e022_boundary``. No E022 END_UTC (E022 dropped): rule (d) alone floors the window."""
    if e022_end_utc is None:
        return True
    e = _parse_utc(e022_end_utc)
    return bool(_parse_utc(cap_prev_start_utc) >= e and _parse_utc(sweep_prev_start_utc) >= e)


# --- the pinned crypto classifier (section 5; R1 re-check item 2) -----------------------------------------------------------

_NULL_LIKE = {"", "nan", "none", "null"}


def _norm_cat(v) -> str | None:
    """``strip().casefold()`` of a fee_category; None when absent or null-like."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip().casefold()
    return None if s in _NULL_LIKE else s


def crypto_class(fee_category, sidecar_present: bool = True, sports: int = 0) -> str:
    """``crypto`` when the sidecar row exists and its fee_category contains ``crypto`` (after strip and casefold);
    ``non_crypto`` when it exists, is non-empty, not null-like and has no ``crypto``; ``unknown`` otherwise (sidecar missing,
    field absent, empty, null-like, or the market's ``sports == -1``). Unknown is counted separately and counted as crypto in
    the gate's numerator, never defaulted to non-crypto."""
    if not sidecar_present or sports == -1:
        return "unknown"
    s = _norm_cat(fee_category)
    if s is None:
        return "unknown"
    return "crypto" if "crypto" in s else "non_crypto"


def crypto_gate_share(classes) -> dict:
    """Crypto share for the gates: (crypto + unknown) / all. Empty input gives NaN (the gate fails)."""
    c = pd.Series(list(classes), dtype=object)
    n = len(c)
    k = {x: int((c == x).sum()) for x in ("crypto", "non_crypto", "unknown")}
    share = (k["crypto"] + k["unknown"]) / n if n else float("nan")
    return {"n": n, **k, "share_as_crypto": share}


def crypto_failsafe(values) -> dict:
    """The fail-safe: ``values`` are the distinct ``fee_category`` values of the WHOLE sealed sidecar set (with counts). If none
    contains ``crypto`` (strip, casefold) the classifier is not shown to work and the dependent gates are NaN (fail)."""
    cnt: dict[str, int] = {}
    it = values.items() if isinstance(values, dict) else ((v, 1) for v in values)
    for v, n in it:
        key = "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)
        cnt[key] = cnt.get(key, 0) + int(n)
    works = any((_norm_cat(v) or "").find("crypto") >= 0 for v in cnt)
    return {"classifier_shown_to_work": bool(works), "distinct_values": dict(sorted(cnt.items())), "gate_value": None if works else float("nan")}


# --- K: clip trains by size identity (section 3; R1 item 12 and re-check n5) ------------------------------------------------


def size_key(text) -> Decimal | None:
    """The size key: ``Decimal(stored text).normalize()``. ``"10"``, ``"10.0"`` and ``"1E+1"`` are one key; no float is
    involved. None for an unparseable or non-finite value (the row is then excluded and counted by the caller)."""
    try:
        d = Decimal(str(text).strip())
    except InvalidOperation:
        return None
    return d.normalize() if d.is_finite() else None


def size_from_json_number(raw: str) -> Decimal:
    """A JSON-number size parsed without float rounding (``parse_float=Decimal``)."""
    return Decimal(json.loads(raw, parse_float=Decimal)) if raw else Decimal("NaN")


def _ts_dec(v) -> Decimal:
    if isinstance(v, str):
        return Decimal(v)
    if isinstance(v, (int, np.integer)):
        return Decimal(int(v))
    return Decimal(repr(float(v)))


def min_size_cutoff(order_min_size_text, mult: int = 2) -> Decimal | None:
    """``mult x order_min_size`` in ``Decimal`` (the sidecar value read as text, never via float). None if unknown."""
    if order_min_size_text is None or (isinstance(order_min_size_text, float) and math.isnan(order_min_size_text)):
        return None
    try:
        d = Decimal(str(order_min_size_text).strip())
    except InvalidOperation:
        return None
    return d * mult if d.is_finite() and d > 0 else None


def greedy_runs(ts: list[Decimal], tx: list, *, min_gap: Decimal, max_span: Decimal, band_lo: Decimal, band_hi: Decimal, min_rows: int = 3) -> list[list[int]]:
    """The declared deterministic algorithm on one group, rows already sorted by (ts, tx_hash). Returns trains as index lists.

    1. start a run at the first unassigned row ``i``;
    2. scan ``j = i + 1, ...``: SKIP (leave unassigned) a row whose gap to the run's last row is ``< min_gap`` or whose
       ``tx_hash`` is already in the run; otherwise, with ``g`` the gap to the run's last row: a one-row run appends ``j`` when
       the span stays ``<= max_span``; a run of two or more appends ``j`` when ``g`` lies in ``[band_lo, band_hi] x`` the
       ``statistics.median`` of the run's current gaps AND the span stays ``<= max_span``; else the run CLOSES;
    3. a closed run of ``>= min_rows`` is a train and the next run starts at the first row after the train's last row; a
       shorter run assigns nothing and the next run starts at ``i + 1``. No overlaps."""
    n = len(ts)
    trains: list[list[int]] = []
    i = 0
    while i < n:
        run = [i]
        seen = {tx[i]} if tx[i] else set()
        gaps: list[Decimal] = []
        j = i + 1
        while j < n:
            g = ts[j] - ts[run[-1]]
            if g < min_gap or (tx[j] and tx[j] in seen):
                j += 1
                continue
            span = ts[j] - ts[run[0]]
            if len(run) == 1:
                ok = span <= max_span
            else:
                med = statistics.median(gaps)
                ok = (band_lo * med <= g <= band_hi * med) and span <= max_span
            if not ok:
                break
            run.append(j)
            gaps.append(g)
            if tx[j]:
                seen.add(tx[j])
            j += 1
        if len(run) >= min_rows:
            trains.append(run)
            i = run[-1] + 1
        else:
            i += 1
    return trains


def clip_trains(rows: pd.DataFrame, order_min_size_text, spec: dict, *, keys: list | None = None, apply_min_size: bool = True) -> dict:
    """K's clip trains on the rows of ONE market's interval ``t_{k-1} <= ts < t_k`` (the caller filters; rows with an unknown
    outcome are removed by the caller and counted). ``rows`` needs ``ts``, ``asset``, ``size`` (TEXT, ``dtype=str``) and
    ``tx_hash``. Rows with ``size <= 2 x order_min_size`` are removed first (in ``Decimal``) when ``apply_min_size``; the rest
    are grouped by (asset, size key) -- or by ``keys`` (the near-identical placebo's group labels) -- and the greedy rule runs
    inside each group. Returns ``train_id`` (per input row, -1 = not in a train), ``removed_min_size`` and ``bad_size``."""
    c = spec["k"]
    n = len(rows)
    train_id = np.full(n, -1, dtype=int)
    removed = np.zeros(n, bool)
    bad = np.zeros(n, bool)
    cutoff = min_size_cutoff(order_min_size_text, int(c["min_size_multiple"])) if apply_min_size else None
    if apply_min_size and cutoff is None:
        return {"train_id": train_id, "removed_min_size": removed, "bad_size": bad, "cutoff_unknown": True, "n_trains": 0, "trains": []}
    groups: dict = {}
    ts_col, as_col, sz_col, tx_col = rows["ts"].tolist(), rows["asset"].tolist(), rows["size"].tolist(), rows["tx_hash"].tolist()
    for idx in range(n):
        d = size_key(sz_col[idx])
        if d is None:
            bad[idx] = True
            continue
        if cutoff is not None and d <= cutoff:
            removed[idx] = True
            continue
        g = (as_col[idx], d) if keys is None else (as_col[idx], keys[idx])
        groups.setdefault(g, []).append(idx)
    kw = dict(min_gap=Decimal(str(c["min_gap_s"])), max_span=Decimal(str(c["max_span_s"])), band_lo=Decimal(str(c["band_lo"])),
              band_hi=Decimal(str(c["band_hi"])), min_rows=int(c["min_run_rows"]))
    trains = []
    for g in sorted(groups, key=lambda x: (str(x[0]), str(x[1]))):
        idxs = sorted(groups[g], key=lambda i: (_ts_dec(ts_col[i]), "" if tx_col[i] is None or (isinstance(tx_col[i], float) and math.isnan(tx_col[i])) else str(tx_col[i])))
        txs = [None if (tx_col[i] is None or (isinstance(tx_col[i], float) and math.isnan(tx_col[i])) or str(tx_col[i]) == "") else str(tx_col[i]) for i in idxs]
        for run in greedy_runs([_ts_dec(ts_col[i]) for i in idxs], txs, **kw):
            members = [idxs[r] for r in run]
            train_id[members] = len(trains)
            trains.append(members)
    return {"train_id": train_id, "removed_min_size": removed, "bad_size": bad, "cutoff_unknown": False, "n_trains": len(trains), "trains": trains}


def near_identical_keys(rows: pd.DataFrame, pct: float = 0.05) -> list:
    """P1's deterministic grouping (section 3): rows of one token sorted by size; a group is a maximal run whose largest size is
    within ``pct`` of its smallest, with no two rows of identical size. A row whose size equals the previous row's, or exceeds
    ``(1 + pct) x`` the group's smallest, closes the group and starts the next one. Returns a group label per input row
    (``None`` for an unparseable size). Combined with the asset the key is unique per token."""
    n = len(rows)
    keys: list = [None] * n
    d = [size_key(s) for s in rows["size"].tolist()]
    asset = rows["asset"].tolist()
    ts = rows["ts"].tolist()
    order = sorted((i for i in range(n) if d[i] is not None), key=lambda i: (str(asset[i]), d[i], _ts_dec(ts[i])))
    gid, start, last, cur_asset = -1, None, None, None
    pc = Decimal(str(1 + pct))
    for i in order:
        new = asset[i] != cur_asset or start is None or d[i] == last or d[i] > start * pc
        if new:
            gid += 1
            start, cur_asset = d[i], asset[i]
        last = d[i]
        keys[i] = gid
    return keys


def clip_unit_features(rows: pd.DataFrame, order_min_size_text, t_k: float, spec: dict) -> dict:
    """K's frozen state for one unit from the interval rows (``t_{k-1} <= ts < t_k``, known outcome, TEXT sizes): ``clip_share``
    (notional = size x price share of the interval's rows that lie in clip trains), ``round_share`` (notional share of rows whose
    size is a multiple of 10 shares), ``minsize_share`` (notional share at ``<= 2 x order_min_size``), ``n_trains``, ``last_clip_age``
    (``t_k`` minus the latest clip row's ts, NaN if none), ``H_unsigned`` (E018's M3 unsigned train share on these rows, LT3's
    ``train_flags`` with a 300 s gap and no sign), ``n_int``, plus the census-only would-be-clip notional shares measured before
    the min-size exclusion."""
    from . import live_tests3 as l3

    c = spec["k"]
    n = len(rows)
    price = pd.to_numeric(rows["price"], errors="coerce").to_numpy(float)
    sz = np.array([float(x) if x is not None else float("nan") for x in (size_key(s) for s in rows["size"].tolist())], float)
    notional = sz * price
    tot = float(np.nansum(notional))
    res = clip_trains(rows, order_min_size_text, spec)
    all_ = clip_trains(rows, order_min_size_text, spec, apply_min_size=False)
    cutoff = min_size_cutoff(order_min_size_text, int(c["min_size_multiple"]))
    in_train = res["train_id"] >= 0
    mult = Decimal(int(c["round_multiple"]))
    rnd = np.array([(d is not None and d % mult == 0) for d in (size_key(s) for s in rows["size"].tolist())], bool)
    small = res["removed_min_size"]
    ts = pd.to_numeric(rows["ts"], errors="coerce").to_numpy(float)
    flags = l3.train_flags(np.zeros(n, dtype=np.int64), ts, np.zeros(n), float(c["unsigned_gap_s"]), same_sign=False) if n else np.zeros(0, bool)

    def share(mask) -> float:
        return float(np.nansum(notional[mask]) / tot) if tot > 0 else float("nan")

    a_in = all_["train_id"] >= 0
    clip_notional_all = float(np.nansum(notional[a_in]))
    a_small = np.array([(cutoff is not None and (d is not None) and d <= cutoff) for d in (size_key(s) for s in rows["size"].tolist())], bool)
    return {"n_int": n, "clip_share": share(in_train), "round_share": share(rnd), "minsize_share": share(small), "n_trains": res["n_trains"],
            "last_clip_age": float(t_k - np.nanmax(ts[in_train])) if in_train.any() else float("nan"), "H_unsigned": share(flags),
            "cutoff_unknown": res["cutoff_unknown"], "bad_size_rows": int(res["bad_size"].sum()),
            "would_be_clip_notional": clip_notional_all,
            "would_be_clip_notional_minsize": float(np.nansum(notional[a_in & a_small])),
            "would_be_clip_notional_round": float(np.nansum(notional[a_in & rnd]))}


def interval_rows(tr: pd.DataFrame, t_p: float, t_k: float, outcome_known=None) -> pd.DataFrame:
    """The rows of K's interval ``t_{k-1} <= ts < t_k`` (strictly before the decision time: a row at or after ``t_k`` is never
    read) with a known outcome (``outcome_known`` a boolean array aligned to ``tr``; rows of unknown outcome are dropped and
    counted by the caller)."""
    ts = pd.to_numeric(tr["ts"], errors="coerce").to_numpy(float)
    m = (ts >= t_p) & (ts < t_k)
    if outcome_known is not None:
        m &= np.asarray(outcome_known, bool)
    return tr[m].reset_index(drop=True)


def clip_class(clip_share: float, spec: dict) -> str:
    """``clip`` when ``clip_share >= 0.25``; ``clip_free`` when exactly 0; ``interior`` otherwise (reported, S1); ``nan`` if undefined."""
    if not math.isfinite(clip_share):
        return "nan"
    if clip_share >= spec["k"]["clip_share_min"] - 1e-12:
        return "clip"
    return "clip_free" if clip_share == 0.0 else "interior"


# --- V: the makers' vote (section 2) and its depletion gates (section 7) ----------------------------------------------------


def imbalance(dbid, dask) -> np.ndarray:
    """``imb = (D_bid - D_ask) / (D_bid + D_ask)`` on the outcome-0 book (shares); NaN where either depth is missing or the sum is not positive."""
    db, da = np.asarray(dbid, float), np.asarray(dask, float)
    s = db + da
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(np.isfinite(s) & (s > 0), (db - da) / s, np.nan)


def toward_away(sign_x, dbid, dask) -> tuple[np.ndarray, np.ndarray]:
    """Toward-side and away-side depth: toward = asks for a rise (sign +1), bids for a fall (sign -1)."""
    sx = np.sign(np.asarray(sign_x, float))
    db, da = np.asarray(dbid, float), np.asarray(dask, float)
    return np.where(sx > 0, da, np.where(sx < 0, db, np.nan)), np.where(sx > 0, db, np.where(sx < 0, da, np.nan))


def v_fields(u: pd.DataFrame) -> pd.DataFrame:
    """V's frozen state (decision time = sweep 1 of pass k) from the columns ``x`` (the capture's 2 h mid move, sign taken),
    ``dbid5_k, dask5_k, dbid5_p, dask5_p`` (5c depths of sweeps k, k - 1), ``dbid1_*`` / ``dask1_*`` likewise at 1c, ``sbid_k,
    sask_k`` (sweep touches of k, for the notional), ``liq`` (Gamma liquidity at k). Adds: ``sx``, ``v = sign(x) imb_k``, ``v_prev =
    sign(x) imb_{k-1}``, ``lt`` / ``la`` (toward / away log depth ratios at 5c, +1 in both numerator and denominator), the same
    at 1c (``lt1`` / ``la1``), ``D0_k``, ``D0_p`` (5c shares), ``h0 = clip(1 - D0_notional / liq, 0, 1)`` with D0_notional =
    depth_bid_5c x sbid + depth_ask_5c x sask on the outcome-0 token (E022's hollowness, declared on outcome 0), ``dspread`` if
    ``spread_sw_k`` / ``spread_sw_p`` are present. NaN where an input is missing; nothing is imputed."""
    o = u.copy()
    sx = np.sign(o["x"].to_numpy(float))
    o["sx"] = sx
    o["v"] = sx * imbalance(o["dbid5_k"], o["dask5_k"])
    o["v_prev"] = sx * imbalance(o["dbid5_p"], o["dask5_p"])
    for band, tag in (("5", ""), ("1", "1")):
        tk, ak = toward_away(sx, o[f"dbid{band}_k"], o[f"dask{band}_k"])
        tp, ap = toward_away(sx, o[f"dbid{band}_p"], o[f"dask{band}_p"])
        with np.errstate(invalid="ignore", divide="ignore"):
            o[f"lt{tag}"] = np.log((tk + 1.0) / (tp + 1.0))
            o[f"la{tag}"] = np.log((ak + 1.0) / (ap + 1.0))
    o["D0_k"] = o["dbid5_k"] + o["dask5_k"]
    o["D0_p"] = o["dbid5_p"] + o["dask5_p"]
    notional = o["dbid5_k"].to_numpy(float) * o["sbid_k"].to_numpy(float) + o["dask5_k"].to_numpy(float) * o["sask_k"].to_numpy(float)
    liq = o["liq"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        o["h0"] = np.where(np.isfinite(notional) & np.isfinite(liq) & (liq > 0), np.clip(1.0 - notional / liq, 0.0, 1.0), np.nan)
    if {"spread_sw_k", "spread_sw_p"} <= set(o.columns):
        o["dspread"] = o["spread_sw_k"] - o["spread_sw_p"]
    return o


def depletion_gate(u: pd.DataFrame, g: dict) -> dict:
    """Section 7 / R1 item 6 (both bind). Among TRADED units (the caller passes only those): ``share(toward-side 1c depth at sweep
    k below half its level at k - 1) - share(away-side 1c depth likewise halved) <= 20 pp``, a unit whose toward- or away-side 1c
    depth at k - 1 is 0 excluded from BOTH shares and counted (R1 re-check n6); AND the toward-side 5c halving share <= 50%. The
    round's original share (toward-side 5c depth below its k - 1 level) is printed. Columns: ``x``, ``dbid1_k, dask1_k, dbid1_p,
    dask1_p, dbid5_k, dask5_k, dbid5_p, dask5_p``. NaN anywhere fails (gate value NaN)."""
    r = float(g["depletion_halving_ratio"])
    sx = np.sign(u["x"].to_numpy(float))
    t1k, a1k = toward_away(sx, u["dbid1_k"], u["dask1_k"])
    t1p, a1p = toward_away(sx, u["dbid1_p"], u["dask1_p"])
    t5k, _ = toward_away(sx, u["dbid5_k"], u["dask5_k"])
    t5p, _ = toward_away(sx, u["dbid5_p"], u["dask5_p"])
    ok1 = np.isfinite(t1k) & np.isfinite(a1k) & np.isfinite(t1p) & np.isfinite(a1p)
    zero_p = ok1 & ((t1p <= 0) | (a1p <= 0))
    use = ok1 & ~zero_p
    ok5 = np.isfinite(t5k) & np.isfinite(t5p) & (t5p > 0)
    n1, n5 = int(use.sum()), int(ok5.sum())
    with np.errstate(invalid="ignore"):
        s_t = float((t1k[use] < r * t1p[use]).mean()) if n1 else float("nan")
        s_a = float((a1k[use] < r * a1p[use]).mean()) if n1 else float("nan")
        s5 = float((t5k[ok5] < r * t5p[ok5]).mean()) if n5 else float("nan")
        orig = float((t5k[ok5] < t5p[ok5]).mean()) if n5 else float("nan")
    asym = s_t - s_a
    return {"n_1c": n1, "n_1c_excluded_zero_prev": int(zero_p.sum()), "toward_halved_1c": s_t, "away_halved_1c": s_a, "asym_pp": asym,
            "n_5c": n5, "toward_halved_5c": s5, "round_original_toward_below_prev_5c": orig,
            "pass_1c": bool(np.isfinite(asym) and asym <= g["depletion_1c_asym_pp_max"]),
            "pass_5c": bool(np.isfinite(s5) and s5 <= g["depletion_5c_toward_share_max"])}


def v_target(smid_k1, smid_k3, sign_x) -> np.ndarray:
    """``c_vskip = sign(x) x (smid_{k+3} - smid_{k+1})`` (sweep-1 outcome-0 mids; the caller applies the joint status and late mask)."""
    return np.sign(np.asarray(sign_x, float)) * (np.asarray(smid_k3, float) - np.asarray(smid_k1, float))


# --- D: deadline moves (section 4) ------------------------------------------------------------------------------------------

_NY = ZoneInfo("America/New_York")
_DATE_ONLY = re.compile(r"^\s*\d{4}-\d{2}-\d{2}\s*$")


def parse_end_date(v) -> datetime | None:
    """The pinned parse rule: ``datetime.fromisoformat`` after a trailing ``Z`` is replaced by ``+00:00``; a naive timestamp is
    UTC; a date-only string or an unparseable value gives None (no template and no class: excluded, counted, never
    "unchanged"). The microseconds are dropped (equality is to the second)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    if not s or _DATE_ONLY.match(s):
        return None
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return dt.replace(microsecond=0)


def bydate_template(end: datetime | None, spec: dict | None = None) -> bool | None:
    """``bydate = 1`` when the end date, converted to America/New_York (DST by ``zoneinfo``), has a clock time within 1 minute of
    23:59:00 or 00:00:00 (inclusive). None when the end date is missing / unparseable."""
    if end is None:
        return None
    tol = 60 if spec is None else int(spec["d"]["bydate_tolerance_s"])
    loc = end.astimezone(_NY)
    s = loc.hour * 3600 + loc.minute * 60 + loc.second
    return bool(abs(s - 86340) <= tol or s <= tol)  # within tol of 23:59:00, or within tol of 00:00:00 (from above)


def end_change_class(old, new, t_k: float, series_slugs_nonempty: bool, spec: dict | None = None) -> dict:
    """The change class of an ``end_date`` between captures k - 1 and k (``old`` / ``new`` raw values, ``t_k`` the capture's
    epoch). Returns ``cls`` in: ``unparseable`` (either side; excluded, never unchanged), ``no_change`` (equal to the second),
    ``later`` (delta >= 1 h and not excluded below), ``earlier`` (delta <= -1 h; descriptive), ``small`` (0 < |delta| < 1 h; excluded),
    ``overdue`` (a later move whose OLD end was <= t_k: CH189's object; excluded, S7) and ``rollover`` (a later move on a series
    market with |delta| within 1 h of 1, 7, 30 or 31 days; excluded). Also ``delta_s``, ``bydate`` (template of the OLD end at
    k - 1) and ``T_new_h`` (hours from t_k to the new end)."""
    c = (spec or {"d": {"later_min_s": 3600, "rollover_days": [1, 7, 30, 31], "rollover_tol_s": 3600, "bydate_tolerance_s": 60}})["d"]
    o, n = parse_end_date(old), parse_end_date(new)
    if o is None or n is None:
        return {"cls": "unparseable", "delta_s": float("nan"), "bydate": None, "T_new_h": float("nan")}
    delta = (n - o).total_seconds()
    by = bydate_template(o, spec)
    t_new = (n.timestamp() - t_k) / 3600.0
    if delta == 0:
        cls = "no_change"
    elif delta >= c["later_min_s"]:
        if o.timestamp() <= t_k:
            cls = "overdue"
        elif series_slugs_nonempty and any(abs(delta - d * DAY_S) <= c["rollover_tol_s"] for d in c["rollover_days"]):
            cls = "rollover"
        else:
            cls = "later"
    elif delta <= -c["later_min_s"]:
        cls = "earlier"
    else:
        cls = "small"
    return {"cls": cls, "delta_s": delta, "bydate": by, "T_new_h": t_new}


def theta24(mid_k, T_k_hours) -> np.ndarray:
    """The constant-hazard time-decay control: ``24 x (1 - mid) ln(1 - mid) / T`` (hours to end ``T``; the NEW end for later
    units). Under ``P = 1 - exp(-lambda T)`` the YES drift per hour is ``(1 - P) ln(1 - P) / T``."""
    m, T = np.asarray(mid_k, float), np.asarray(T_k_hours, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((m > 0) & (m < 1) & (T > 0), 24.0 * (1.0 - m) * np.log(1.0 - m) / T, np.nan)


# --- washout (1.7) ----------------------------------------------------------------------------------------------------------


def washout(unit_slots, label_slots, width: int = 11) -> np.ndarray:
    """True for a class-0 unit (no-change for D, no-birth for B) at slot ``s`` of a market for which some labelled unit of the
    SAME market sits at slot ``L`` with ``1 <= s - L <= width``: its 22 h target overlaps the labelled event's aftermath.
    ``label_slots`` includes labelled units seen only in look-back lines (they can only remove units)."""
    s = np.asarray(unit_slots, int)
    L = np.asarray(sorted(set(int(x) for x in label_slots)), int)
    if not len(L) or not len(s):
        return np.zeros(len(s), bool)
    d = s[:, None] - L[None, :]
    return ((d >= 1) & (d <= width)).any(axis=1)


# --- B: sibling birth (section 5) -------------------------------------------------------------------------------------------


def newcomer_kind(*, created_ts: float, t_prev: float, t_k: float, members_prev: int, recurring: bool, min_members: int = 2) -> str:
    """Kind of one newcomer (a market present in capture k and absent from k - 1): ``created_unparseable`` (``created_at`` missing /
    unparseable: not a birth), ``lagged`` (``created_at`` outside ``[t_{k-1}, t_k)``: a lagged appearance, reported, not a birth),
    ``not_existing`` (the event held fewer than 2 markets at k - 1), ``recurring`` (``series_slugs`` non-empty on the newcomer or
    an incumbent), ``birth`` otherwise."""
    if created_ts is None or not math.isfinite(created_ts):
        return "created_unparseable"
    if not (t_prev <= created_ts < t_k):
        return "lagged"
    if members_prev < min_members:
        return "not_existing"
    if recurring:
        return "recurring"
    return "birth"


def incumbent_birth_class(newcomers: list[dict], inc_t_row: float, guard_s: float = 5.0) -> dict:
    """Class of one incumbent at capture k from its event's newcomers (each ``{"kind", "t_row"}``). ``birth`` when the event has a
    ``birth`` newcomer and every birth newcomer's row was received within ``guard_s`` seconds of the incumbent's (stricter reading
    of the 5 s guard when there are several); ``nobirth`` ONLY when the event has no newcomer and no lagged appearance. Everything
    else is EXCLUDED with a reason, never class 0. Precedence (stricter first): ``created_unparseable`` > ``recurring_newcomer`` >
    ``guard_loss`` > ``lagged_only`` (a lagged appearance or a not-existing newcomer without a birth). ``n_born`` = the birth newcomers."""
    kinds = [n["kind"] for n in newcomers]
    if not kinds:
        return {"cls": "nobirth", "reason": "", "n_born": 0}
    if "created_unparseable" in kinds:
        return {"cls": "excluded", "reason": "created_unparseable", "n_born": 0}
    if "recurring" in kinds:
        return {"cls": "excluded", "reason": "recurring_newcomer", "n_born": 0}
    births = [n for n in newcomers if n["kind"] == "birth"]
    if births:
        if all(float(n["t_row"]) - inc_t_row <= guard_s for n in births):
            return {"cls": "birth", "reason": "", "n_born": len(births)}
        return {"cls": "excluded", "reason": "guard_loss", "n_born": len(births)}
    return {"cls": "excluded", "reason": "lagged_only", "n_born": 0}


def fake_birth_slot(real_slots: list[int], window_slots: list[int], tercile_of_slot: dict, real_tercile: int, rng: np.random.Generator,
                    min_distance: int = 12) -> int | None:
    """The placebo's fake birth for one real birth of an event: one capture drawn uniformly from the window's captures at least
    ``min_distance`` slots from EVERY real birth of that event and in the same tercile of the event's leave-one-out ``|2 h|`` move as
    the real birth. None if no capture qualifies (counted). ``rng`` is seeded by the caller (spec seed 20261364)."""
    cand = sorted(s for s in window_slots if all(abs(s - r) >= min_distance for r in real_slots) and tercile_of_slot.get(s) == real_tercile)
    return int(cand[int(rng.integers(len(cand)))]) if cand else None
