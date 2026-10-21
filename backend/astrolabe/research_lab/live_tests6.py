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
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import forecast, panel
from . import live_tests3 as l3
from . import live_tests5 as l5
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
        enforce_v_freeze(spec)
    return spec


def _nanlike(v) -> bool:
    """None, a non-finite float, a "nan"-like string, or a list / dict holding one."""
    if isinstance(v, (list, tuple)):
        return any(_nanlike(x) for x in v)
    if isinstance(v, dict):
        return any(_nanlike(x) for x in v.values())
    return v is None or (isinstance(v, float) and not math.isfinite(v)) or (isinstance(v, str) and v.strip().lower() in ("nan", "inf", "-inf"))


# Placeholders that must be filled at registration. Everything else that is null in a DRAFT spec is allowed to stay null.
REQUIRED_AT_PIN = ("registered_utc", "end_utc", "analysis_not_before", "k_tests", "code_sha256", "e022.registered", "e022.dropped", "e022.end_utc",
                   "labels.partially_seen_d", "size_check.result_path", "size_check.result_sha256")


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
        elif p == "e022.end_utc":  # freeze-check fix: required unless E022 was recorded as dropped (then rule (d) alone floors the window)
            if get("e022.end_utc") is None and not (get("e022.dropped") and not get("e022.registered")):
                out.append(p)
        elif _nanlike(get(p)):
            out.append(p)
    needs = {"V": ("c_v", "s_v", "terciles", "tercile_gap", "exclude_family"), "K": ("exclude_family", "perm_stratum"),
             "D": ("exclude_family", "perm_stratum"), "B": ("exclude_family", "perm_stratum", "fake_birth_terciles")}
    for t in spec.get("k_tests") or []:
        for f in needs.get(t, ()):
            if _nanlike(spec[t.lower()].get(f)):
                out.append(f"{t.lower()}.{f}")
    if "V" in (spec.get("k_tests") or []) and get("e022.registered") and _nanlike(get("e022.pin_commit_utc")):
        out.append("e022.pin_commit_utc")  # V's freeze condition (1.1) needs the LT6 registration commit time
    return out


def enforce_v_freeze(spec: dict) -> dict | None:
    """Freeze-check fix: a pinned spec that keeps V in ``k_tests`` must satisfy :func:`v_freeze_check` (the LT6 registration commit
    strictly before E022's ``T_E022``, or E022 dropped before registration). Raises RuntimeError otherwise; None if V is not in k_tests."""
    if "V" not in (spec.get("k_tests") or []):
        return None
    e = spec.get("e022") or {}
    chk = v_freeze_check(pin_commit_utc=e.get("pin_commit_utc") or "9999-12-31T00:00:00Z", e022_registered=bool(e.get("registered")),
                         e022_dropped=bool(e.get("dropped")), analysis_job_start_utc=e.get("analysis_job_start_utc"),
                         analysis_commit_utc=e.get("analysis_commit_utc"))
    if not chk["ok"]:
        raise RuntimeError(f"live_tests6 V freeze condition fails (1.1): {chk['reason']}; V must be dropped from k_tests before the pin")
    return chk


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


def v_first_origin_ok(cap_prev_start_utc: str, sweep_prev_start_utc: str, e022_end_utc: str | None, e022_dropped: bool = False) -> bool:
    """V's first origin (1.1, R1 item 7): the k - 1 capture AND the k - 1 sweep both start at or after E022's ``END_UTC``.
    A pass failing this is counted ``e022_boundary``. No E022 END_UTC is accepted only when E022 is recorded as dropped (``e022_dropped``);
    otherwise it refuses (False): rule (d) alone floors the window only for a dropped E022."""
    if e022_end_utc is None:
        return bool(e022_dropped)  # freeze-check fix: an unknown END_UTC fails closed unless E022 is recorded as dropped
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


def notional_cent_keys(rows: pd.DataFrame) -> list:
    """S3's grouping key (section 3): ``size x price`` rounded to the cent (``Decimal``, half-up) in place of the size key, so identical
    notionals group even when size and price differ. ``None`` (unparseable size or price) is counted as a bad row by :func:`clip_trains`."""
    out: list = []
    for sz, px in zip(rows["size"].tolist(), rows["price"].tolist(), strict=True):
        d = size_key(sz)
        try:
            p_ = Decimal(str(px).strip())
        except (InvalidOperation, ValueError):
            p_ = None
        out.append(None if d is None or p_ is None or not p_.is_finite() else (d * p_).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return out


def clip_unit_features(rows: pd.DataFrame, order_min_size_text, t_k: float, spec: dict) -> dict:
    """K's frozen state for one unit from the interval rows (``t_{k-1} <= ts < t_k``, known outcome, TEXT sizes): ``clip_share``
    (notional = size x price share of the interval's rows that lie in clip trains), ``round_share`` (notional share of rows whose
    size is a multiple of 10 shares), ``minsize_share`` (notional share at ``<= 2 x order_min_size``), ``n_trains``, ``last_clip_age``
    (``t_k`` minus the latest clip row's ts, NaN if none), ``H_unsigned`` (E018's M3 unsigned train share on these rows, LT3's
    ``train_flags`` with a 300 s gap and no sign), ``n_int``, plus the census-only would-be-clip notional shares measured before
    the min-size exclusion."""
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

    # Frozen now because trade samples rotate off after about 3 days (they cannot be recomputed at the analysis): the placebo P1 (the train
    # rule on near-identical, never identical, sizes within +/-5%) and the secondary S3 (identical size x price to the cent), both with the same
    # min-size removal, rows of the interval only.
    p1 = clip_trains(rows, order_min_size_text, spec, keys=near_identical_keys(rows)) if n else {"train_id": np.zeros(0, int), "n_trains": 0}
    s3 = clip_trains(rows, order_min_size_text, spec, keys=notional_cent_keys(rows)) if n else {"train_id": np.zeros(0, int), "n_trains": 0}
    a_in = all_["train_id"] >= 0
    clip_notional_all = float(np.nansum(notional[a_in]))
    a_small = np.array([(cutoff is not None and (d is not None) and d <= cutoff) for d in (size_key(s) for s in rows["size"].tolist())], bool)
    return {"n_int": n, "clip_share": share(in_train), "round_share": share(rnd), "minsize_share": share(small), "n_trains": res["n_trains"],
            "last_clip_age": float(t_k - np.nanmax(ts[in_train])) if in_train.any() else float("nan"), "H_unsigned": share(flags),
            "cutoff_unknown": res["cutoff_unknown"], "bad_size_rows": int(res["bad_size"].sum()),
            "p1_clip_share": share(p1["train_id"] >= 0), "p1_n_trains": p1["n_trains"], "s3_clip_share": share(s3["train_id"] >= 0), "s3_n_trains": s3["n_trains"],
            "clip_notional": float(np.nansum(notional[in_train])), "clip_notional_round": float(np.nansum(notional[in_train & rnd])),
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


# =====================================================================================================================
# Unit 2: capture frames, unit builders and the counts-only censuses (section 7)
# =====================================================================================================================
#
# Censuses read origin-side fields only: no capture, sweep or sample after the one classified, no target, no P&L. They refuse
# any input that is not in the LT6 seal with an equal sha256 (L3), anything at or after the sealed bound, and every census
# whose covered days fall below its minimum (all its gates are then NaN and fail). LT5's helpers are used by import.

SNAP_COLS6 = [*b.SNAP_COLS, "liquidity", "clob_token_id_0", "updated_at"]
EXT_COLS6 = [*b.EXT_COLS, "order_min_size"]
# K reuses LT5 J's path_fields, whose spec block it reads is ``spec["j"]``; LT6 supplies the same three constants.
_J_SHIM = {"j": {"jump_max": 0.25, "grind_min": 0.75, "fresh_max_s": 900.0}}
_CENSUS_KEYS = ("CD", "CB", "CV", "CK")


def load_rows6(cap_dir: Path) -> pd.DataFrame:
    """All rows of a capture (every status), one per market_id and per condition_id, with LT6's extra columns."""
    cols = set(SNAP_COLS6)
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in cols,
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category", "end_date": str,
                              "closed": str, "active": str, "neg_risk": str, "clob_token_id_0": str, "updated_at": str})
    for c in ("liquidity", "updated_at"):
        if c not in rows:
            rows[c] = np.nan
    rows = rows.drop_duplicates("market_id")
    cond = rows["condition_id"].fillna("")
    rows = rows[~(cond.ne("") & cond.duplicated()).to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows


def load_ext6(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS6), dtype=str)
    for c in EXT_COLS6:
        if c not in ext:
            ext[c] = None
    return ext.drop_duplicates("market_id").set_index("market_id")


def _has_slug(v) -> bool:
    """True when ``series_slugs`` is non-empty (a JSON list with at least one slug, or a bare non-empty string)."""
    from . import cb13_label as lab

    return bool(lab.first_series_slug(v if isinstance(v, str) else None))


def _sidecar_cols(ext: pd.DataFrame | None, mids: pd.Index) -> dict:
    """Sidecar-derived columns aligned to ``mids``: ``present`` (a sidecar row with data exists), ``has_slug``, ``fee_cat``, ``osz`` (text)."""
    n = len(mids)
    if ext is None:
        return {"present": np.zeros(n, bool), "has_slug": np.zeros(n, bool), "fee_cat": np.array([None] * n, dtype=object), "osz": np.array([None] * n, dtype=object)}
    e = ext.reindex(mids)
    present = (e["fee_type"].notna() | e["series_slugs"].notna() | e["created_at"].notna()).to_numpy()
    slug = np.array([_has_slug(v) for v in e["series_slugs"].tolist()], bool)
    fc = e["fee_category"].where(e["fee_category"].notna(), None).to_numpy(dtype=object)
    osz = e["order_min_size"].where(e["order_min_size"].notna(), None).to_numpy(dtype=object)
    return {"present": present, "has_slug": slug, "fee_cat": fc, "osz": osz}


def ser6_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, with_status: bool = False):
    """LT5's series (two-sided quotes of open active binary markets, the vendored LT3 builder) plus LT6's columns: Gamma
    ``liq``, the raw ``end_raw`` string (parsed by :func:`parse_end_date`, never by float), ``upd_ts`` (``updated_at``),
    ``has_slug``, ``fee_cat``, ``crypto6`` (the pinned classifier), ``osz`` (``order_min_size`` as text) and ``present``."""
    ser, status = b.series_frame(rows, ext, spec)
    mids = pd.Index(ser["market_id"].astype(str))
    rr = rows.set_index(rows["market_id"].astype(str))
    ser["liq"] = rr["liquidity"].reindex(mids).to_numpy(float)
    ser["end_raw"] = rr["end_date"].astype(object).reindex(mids).to_numpy(dtype=object)
    ser["upd_ts"] = panel._epoch(rr["updated_at"].reindex(mids)) if "updated_at" in rr else np.nan
    sc = _sidecar_cols(ext, mids)
    ser["has_slug"] = sc["has_slug"].astype(int)
    ser["fee_cat"] = sc["fee_cat"]
    ser["osz"] = sc["osz"]
    ser["present"] = sc["present"].astype(int)
    ser["crypto6"] = [crypto_class(fc, bool(p), int(sp)) for fc, p, sp in zip(sc["fee_cat"], sc["present"], ser["sports"].to_numpy(), strict=False)]
    return (ser, status) if with_status else ser


def members_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict) -> pd.DataFrame:
    """Every row of a capture, whatever its status (B's newcomers may be one-sided): market, event, row receipt, ``created_ts``,
    ``has_slug``, pinned crypto class, sports flag and series key."""
    mids = pd.Index(rows["market_id"].astype(str))
    cat = b.category_cols(ext, rows["market_id"].astype(str), rows["event_id"], spec)
    sc = _sidecar_cols(ext, mids)
    return pd.DataFrame({"market_id": mids.to_numpy(), "event_id": rows["event_id"].astype(str).to_numpy(), "t_row": rows["t_row"].to_numpy(float),
                         "created_ts": cat["created_ts"], "has_slug": sc["has_slug"].astype(int), "sports": cat["sports"], "skey": cat["skey"],
                         "crypto6": [crypto_class(fc, bool(p), int(sp)) for fc, p, sp in zip(sc["fee_cat"], sc["present"], cat["sports"], strict=False)],
                         "fee_cat": sc["fee_cat"], "binary": rows["binary"].to_numpy(float) if "binary" in rows else np.nan})


def read_ser6(root: Path, cap_id: str | None, sub: str = "series6") -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / sub / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "event_id": str, "skey": str, "end_raw": str, "fee_cat": str, "osz": str, "crypto6": str},
                       keep_default_na=True).set_index("market_id")


def write_frames6(work: Path, cap: dict, spec: dict) -> None:
    """Write-once ``series6/`` and ``members6/`` for one capture."""
    s, m = Path(work) / "series6" / f"{cap['id']}.csv.gz", Path(work) / "members6" / f"{cap['id']}.csv.gz"
    if s.exists() and m.exists():
        return
    rows, ext = load_rows6(cap["dir"]), load_ext6(cap["dir"])
    b.write_once_csv(s, ser6_frame(rows, ext, spec))
    b.write_once_csv(m, members_frame(rows, ext, spec))


def _utc_day(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y%m%d")


# --- D units -------------------------------------------------------------------------------------------------------------


def deadline_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, ser_12: pd.DataFrame | None, k: int, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """D's units at capture ``k`` (section 4): non-sports markets passing 1.4 items 1-3, 6, 7 at k - 1 and k with ``mid_k`` in
    [0.05, 0.95] whose OLD end date (k - 1) is on a by-date clock time, as-of NEW end more than 27 h after ``t_k``. Classes from
    :func:`end_change_class`. ``no_change`` units are kept only for by-date markets; changed units are kept whether or not by-date
    (the crypto / roll-over kill line counts every later-direction non-sports interior move; P1's placebo is the non-bydate
    arm). ``lookback_missing`` (no capture or no row at k - 12) leaves ``d24`` NaN. Uses captures k - 12, k - 1, k only."""
    d = spec["d"]
    j, cnt = b.move_join(ser_k, ser_p, cap, spec, d["mid_lo"], d["mid_hi"], -1e9)
    cnt["sports_unknown"] = int((j["sports"] == -1).sum())
    cnt["sports"] = int((j["sports"] == 1).sum())
    j = j[j["sports"] == 0].copy()
    mk = j["market_id"].astype(str)
    old = ser_p["end_raw"].reindex(mk).to_numpy(dtype=object)
    new = j["end_raw"].to_numpy(dtype=object)
    cnt["candidates"] = len(j)
    parsed_old = {s: parse_end_date(s) for s in pd.unique(pd.Series(old).astype(str))}
    parsed_new = {s: parse_end_date(s) for s in pd.unique(pd.Series(new).astype(str))}
    unp = np.array([parsed_old[str(o)] is None or parsed_new[str(n)] is None for o, n in zip(old, new, strict=False)], bool)
    cnt["unparseable_end_date"] = int(unp.sum())
    t_k = j["t_row"].to_numpy(float)
    slugs = (j["has_slug"].to_numpy(int) > 0) | (ser_p["has_slug"].reindex(mk).to_numpy(float) > 0)
    recs = []
    for i in np.flatnonzero(~unp):
        o, n = str(old[i]), str(new[i])
        if o == n:  # byte-equal raw strings parse equal: no_change without the full classifier
            by = bydate_template(parsed_old[o], spec)
            if not by:
                continue
            recs.append((i, "no_change", 0.0, True, (parsed_new[n].timestamp() - t_k[i]) / 3600.0))
            continue
        c = end_change_class(o, n, float(t_k[i]), bool(slugs[i]), spec)
        if c["cls"] == "no_change" and not c["bydate"]:
            continue
        recs.append((i, c["cls"], c["delta_s"], c["bydate"], c["T_new_h"]))
    clock = {}
    for s_, n_ in pd.Series(old).astype(str).value_counts().items():
        dt = parsed_old.get(s_)
        if dt is not None:
            key = dt.astimezone(_NY).strftime("%H:%M")
            clock[key] = clock.get(key, 0) + int(n_)
    cnt["et_clock"] = dict(sorted(clock.items(), key=lambda kv: -kv[1])[:20])
    cnt["unparseable_or_date_only_share"] = cnt["unparseable_end_date"] / max(cnt["candidates"], 1)
    if not recs:
        return pd.DataFrame(), cnt
    idx = np.array([r[0] for r in recs])
    u = j.iloc[idx].copy().reset_index(drop=True)
    u["cls"] = [r[1] for r in recs]
    u["delta_s"] = [r[2] for r in recs]
    u["bydate"] = [bool(r[3]) for r in recs]
    u["T_new_h"] = [r[4] for r in recs]
    cnt["end_too_soon"] = int((u["T_new_h"] <= d["end_margin_h"]).sum())
    u = u[u["T_new_h"] > d["end_margin_h"]].reset_index(drop=True)
    mid = (u["bid"] + u["ask"]) / 2.0
    um = u["market_id"].astype(str)
    u["x"] = mid - (u["bid_p"] + u["ask_p"]) / 2.0
    m12 = (b._mid(ser_12, um) if ser_12 is not None else np.full(len(u), np.nan))
    u["d24"] = mid.to_numpy(float) - m12
    cnt["lookback_missing"] = int(np.isnan(u["d24"]).sum())
    u["theta24"] = theta24(mid, u["T_new_h"])
    u["log_T"] = np.log(u["T_new_h"].clip(lower=1e-9))
    u["slot"] = k
    u["day"] = _utc_day(cap["start"])
    u["mid"] = mid
    uk, up = u["upd_ts"].to_numpy(float), ser_p["upd_ts"].reindex(um).to_numpy(float)
    # a missing updated_at at k - 1 or k stays missing (NaN, 1.5): never "changed"; the unit is excluded from the regressions and counted
    u["updated_changed"] = np.where(np.isnan(uk) | np.isnan(up), np.nan, (uk != up).astype(float))
    cnt["updated_at_missing"] = int(u["updated_changed"].isna().sum())
    u["old_end_days"] = [(parsed_old[str(o)].timestamp() - tk) / DAY_S if parsed_old[str(o)] else np.nan
                         for o, tk in zip(ser_p["end_raw"].reindex(um).to_numpy(dtype=object), u["t_row"].to_numpy(float), strict=False)]
    return u, cnt


def apply_washout(U: pd.DataFrame, class0: str, label_classes: tuple[str, ...], width: int, extra: dict | None = None) -> tuple[pd.DataFrame, int]:
    """Drop class-0 units that are inside the washout of a labelled unit of the same market (1.7); returns (units, n dropped).
    ``extra`` maps market -> labelled slots seen elsewhere (look-back lines before REGISTERED, or labelled units outside the
    analysis sample): they can only remove units."""
    if U.empty:
        return U, 0
    keep = np.ones(len(U), bool)
    lab = {m: list(v) for m, v in U[U["cls"].isin(label_classes)].groupby(U["market_id"].astype(str))["slot"].apply(list).to_dict().items()}
    for m, v in (extra or {}).items():
        lab.setdefault(str(m), []).extend(int(x) for x in v)
    for m, idx in U[U["cls"] == class0].groupby(U["market_id"].astype(str)).groups.items():
        if m in lab:
            pos = U.index.get_indexer(idx)
            keep[pos] = ~washout(U.loc[idx, "slot"].to_numpy(int), lab[m], width)
    return U[keep].reset_index(drop=True), int((~keep).sum())


# --- B units -------------------------------------------------------------------------------------------------------------


def birth_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, mem_k: pd.DataFrame, mem_p: pd.DataFrame, ser_hist: dict[int, pd.DataFrame | None],
                k: int, cap: dict, cap_prev: dict, spec: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """B's incumbent units at capture ``k`` and the table of newcomer kinds (section 5). A newcomer is a market in capture k and
    not in k - 1 (any status), with ``created_at`` in ``[t_{k-1}, t_k)`` where the bounds are the START times of captures k - 1 and
    k (stricter than a row receipt). The event is existing if k - 1 holds >= 2 markets with that ``event_id``; recurring if the
    newcomer or any incumbent has series slugs. Incumbents: non-sports markets of multi-member non-recurring events passing 1.4
    items 1-3, 6, 7 at k - 1 and k with ``mid_k`` in [0.05, 0.95]; classes from :func:`incumbent_birth_class` (a lagged appearance,
    a guard loss, an unparseable ``created_at`` or a recurring newcomer is EXCLUDED and counted, never class 0). The leave-one-out
    mean absolute 2 h move is over the other incumbents of the event. Returns (units, counts, newcomer table)."""
    bcfg = spec["b"]
    t_prev, t_cur = float(cap_prev["start"]), float(cap["start"])
    cnt: dict = {}
    new_ids = set(mem_k["market_id"]) - set(mem_p["market_id"])
    nk = mem_k[mem_k["market_id"].isin(new_ids) & mem_k["event_id"].ne("") & mem_k["event_id"].ne("nan")].copy()
    n_prev = mem_p.groupby("event_id")["market_id"].size()
    slug_prev = mem_p.groupby("event_id")["has_slug"].max()
    nk["members_prev"] = nk["event_id"].map(n_prev).fillna(0).astype(int)
    nk["event_slug_prev"] = nk["event_id"].map(slug_prev).fillna(0).astype(int)
    nk["kind"] = [newcomer_kind(created_ts=c, t_prev=t_prev, t_k=t_cur, members_prev=int(mp), recurring=bool(hs) or bool(es), min_members=bcfg["min_members_prev"])
                  for c, mp, hs, es in zip(nk["created_ts"], nk["members_prev"], nk["has_slug"], nk["event_slug_prev"], strict=False)]
    cnt["newcomers"] = len(nk)
    cnt["newcomer_kinds"] = {str(a): int(c) for a, c in nk["kind"].value_counts().items()}
    j, c0 = b.move_join(ser_k, ser_p, cap, spec, bcfg["mid_lo"], bcfg["mid_hi"], bcfg["end_margin_h"])
    cnt.update({f"join_{a}": v for a, v in c0.items()})
    # 1.4/1.5: B requires a KNOWN as-of end > t_k + 27 h; the unknown-end indicator is allowed only for V and K (counted exclusion)
    unk_end = j["end_ts"].isna().to_numpy()
    cnt["unknown_end_excluded"] = int(unk_end.sum())
    j = j[~unk_end].copy()
    j = j[(j["sports"] == 0)].copy()
    j["members_prev"] = j["event_id"].map(n_prev).fillna(0).astype(int)
    j = j[j["members_prev"] >= bcfg["min_members_prev"]].copy()
    cnt["multi_member"] = len(j)
    j["event_slug"] = j["event_id"].map(slug_prev).fillna(0).astype(int)
    cnt["recurring_event"] = int((j["event_slug"] > 0).sum())
    j = j[j["event_slug"] == 0].copy()
    if j.empty:
        return pd.DataFrame(), cnt, nk
    by_ev = {e: g[["kind", "t_row"]].to_dict("records") for e, g in nk.groupby("event_id")}
    recs = [incumbent_birth_class(by_ev.get(e, []), float(t), float(bcfg["guard_s"])) for e, t in zip(j["event_id"], j["t_row"], strict=False)]
    j["cls"] = [r["cls"] for r in recs]
    j["reason"] = [r["reason"] for r in recs]
    j["n_born"] = [r["n_born"] for r in recs]
    cnt["excluded_by_reason"] = {str(a): int(c) for a, c in j.loc[j["cls"] == "excluded", "reason"].value_counts().items()}
    cnt["birth_units"] = int((j["cls"] == "birth").sum())
    cnt["nobirth_units_pre_washout"] = int((j["cls"] == "nobirth").sum())
    j = j[j["cls"] != "excluded"].copy().reset_index(drop=True)
    um = j["market_id"].astype(str)
    mid = (j["bid"] + j["ask"]) / 2.0
    j["mid"] = mid
    j["a1"] = np.abs(mid - (j["bid_p"] + j["ask_p"]) / 2.0)
    for lag, nm in ((3, "a6"), (12, "a24")):
        prev = ser_hist.get(k - lag)
        j[nm] = np.abs(mid.to_numpy(float) - (b._mid(prev, um) if prev is not None else np.nan))
    cnt["lookback_missing"] = int(j[["a6", "a24"]].isna().any(axis=1).sum())
    grp_sum = j.groupby("event_id")["a1"].transform("sum")
    grp_n = j.groupby("event_id")["a1"].transform("size")
    j["loo_a1"] = np.where(grp_n > 1, (grp_sum - j["a1"]) / (grp_n - 1).clip(lower=1), np.nan)
    j["slot"], j["day"] = k, _utc_day(cap["start"])
    j["log_event_size"] = np.log(j["members_prev"].clip(lower=1))
    j["crypto_birth"] = ""
    if (j["cls"] == "birth").any():
        cr = nk[nk["kind"] == "birth"].groupby("event_id")["crypto6"].apply(list).to_dict()
        j.loc[j["cls"] == "birth", "crypto_birth"] = [("unknown" if "unknown" in cr.get(e, []) else ("crypto" if "crypto" in cr.get(e, []) else "non_crypto"))
                                                      for e in j.loc[j["cls"] == "birth", "event_id"]]
    return j, cnt, nk


# --- V units -------------------------------------------------------------------------------------------------------------


def vote_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, sw_k: pd.DataFrame | None, sw_p: pd.DataFrame | None, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """V's units of one pass (section 2): non-sports traded or quote-only movers at k (1.4 with ``|x| >= 0.01``) with sweep 1 of
    BOTH pass k - 1 and pass k two-sided on the outcome-0 token, tight (<= 0.10), both 5c depths present, ``D0 > 0`` at both and
    Gamma ``liquidity_k > 0``. ``sw_*`` are :func:`live_tests5_base.sweep_frame` outputs indexed by market_id (None = no sweep: ``.nosweep``
    / ``.noprevsweep`` counted). Origin-side only: no sweep after pass k is read."""
    v = spec["v"]
    j, cnt = b.move_join(ser_k, ser_p, cap, spec, spec["move"]["mid_lo"], spec["move"]["mid_hi"], spec["move"]["end_margin_h"])
    j["x"] = (j["bid"] + j["ask"]) / 2.0 - (j["bid_p"] + j["ask_p"]) / 2.0
    j = j[np.abs(j["x"]) >= v["min_abs_x"] - 1e-12]
    cls, geom = b.classify(j["bid_p"], j["ask_p"], j["bid"], j["ask"], j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    j = j.assign(cls=cls, geom=geom)
    cnt["sports_unknown"] = int((j["sports"] == -1).sum())
    j = j[(j["sports"] == 0) & j["cls"].isin(["traded", "quote_only"])].copy()
    cnt["non_sports_movers"] = len(j)
    if sw_k is None:
        cnt["nosweep"] = 1
        return pd.DataFrame(), cnt
    if sw_p is None:
        cnt["noprevsweep"] = 1
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    cols = ["sbid", "sask", "s_t", "s_two", "dbid1", "dask1", "dbid5", "dask5"]
    a = sw_k.reindex(mk)[cols].reset_index(drop=True)
    p = sw_p.reindex(mk)[cols].reset_index(drop=True)
    j = j.reset_index(drop=True)
    for c in cols:
        j[f"{c}_k"], j[f"{c}_p"] = a[c].to_numpy(float), p[c].to_numpy(float)
    two = (j["s_two_k"] == 1) & (j["s_two_p"] == 1)
    tight = ((j["sask_k"] - j["sbid_k"]) <= v["sweep_spread_max"] + 1e-12) & ((j["sask_p"] - j["sbid_p"]) <= v["sweep_spread_max"] + 1e-12)
    dep = np.isfinite(j[["dbid5_k", "dask5_k", "dbid5_p", "dask5_p"]]).all(axis=1) & ((j["dbid5_k"] + j["dask5_k"]) > 0) & ((j["dbid5_p"] + j["dask5_p"]) > 0)
    liq = j["liq"] > 0
    cnt["no_both_sweeps"] = int((~two).sum())
    cnt["sweep_not_tight"] = int((two & ~tight).sum())
    cnt["depth_missing_or_zero"] = int((two & tight & ~dep).sum())
    cnt["liquidity_missing"] = int((two & tight & dep & ~liq).sum())
    u = j[two & tight & dep & liq].copy().reset_index(drop=True)
    u["spread_sw_k"], u["spread_sw_p"] = u["sask_k"] - u["sbid_k"], u["sask_p"] - u["sbid_p"]
    u = v_fields(u)
    u["day"] = _utc_day(cap["start"])
    u["slot"] = b.slot_of(cap["start"], spec)
    cnt["units"] = len(u)
    return u, cnt


# --- K units -------------------------------------------------------------------------------------------------------------


def load_sample6(sdir: Path, markets=None, before: float | None = None, chunksize: int = 200_000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """features (status ok) and the trade rows K reads: ``side`` and wallet fields are NEVER read; ``size``, ``price`` and ``ts`` stay TEXT.
    With ``markets`` (the movers that can become units) and ``before`` (the latest decision time ``t_k``) the file is read in chunks and
    only rows of those markets with ``ts < before`` are kept: a row at or after the decision time is never held, and the peak memory
    of a 1M-row sample drops to the movers' rows (the reader's memory plan, 8.2)."""
    feat = pd.read_csv(Path(sdir) / "features.csv.gz", dtype={"market_id": str, "condition_id": str})
    feat = feat[feat["status"] == "ok"].drop_duplicates("market_id").reset_index(drop=True)
    keep = None if markets is None else {str(m) for m in markets}
    parts = []
    for ch in pd.read_csv(Path(sdir) / "trades.csv.gz", usecols=["market_id", "ts", "price", "size", "outcome_index", "asset", "tx_hash"], dtype=str,
                          chunksize=chunksize):
        if keep is not None:
            ch = ch[ch["market_id"].isin(keep)]
        if before is not None and len(ch):
            ch = ch[pd.to_numeric(ch["ts"], errors="coerce") < before]
        if len(ch):
            parts.append(ch)
    cols = ["market_id", "ts", "price", "size", "outcome_index", "asset", "tx_hash"]
    tr = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame({c: pd.Series(dtype=str) for c in cols})
    return feat, tr


def clip_movers(ser_k: pd.DataFrame, ser_p: pd.DataFrame, feat: pd.DataFrame, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """The origin-side half of K's filters, before any trade row is read (so the reader can load only the movers' rows): sampled
    (status ok) traded ``|x| >= 1c`` movers (1.4), tick known and equal at k - 1 and k with ``steps >= 1``, sidecar
    ``order_min_size`` known. Adds ``t_k`` (the sample's ``origin_utc``), ``t_p`` (the market's row receipt at k - 1) and ``n_ret``."""
    c, m = spec["k"], spec["move"]
    j, cnt = b.move_join(ser_k, ser_p, cap, spec, m["mid_lo"], m["mid_hi"], m["end_margin_h"])
    j["x"] = (j["bid"] + j["ask"]) / 2.0 - (j["bid_p"] + j["ask_p"]) / 2.0
    j = j[np.abs(j["x"]) >= m["min_abs_x"] - 1e-12]
    cls, geom = b.classify(j["bid_p"], j["ask_p"], j["bid"], j["ask"], j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    j = j.assign(cls=cls, geom=geom)
    f = feat.drop_duplicates("market_id")
    f = f.set_index(f["market_id"].astype(str))
    j = j[j["market_id"].astype(str).isin(f.index)]
    cnt["sampled_movers"] = len(j)
    j = j[j["cls"] == "traded"].copy()
    cnt["sampled_traded"] = len(j)
    mk = j["market_id"].astype(str)
    tick_p = ser_p["tick"].reindex(mk).to_numpy(float)
    tick_k = j["tick"].to_numpy(float)
    tok = np.isfinite(tick_k) & np.isfinite(tick_p) & (np.abs(tick_k - tick_p) <= 1e-12) & (tick_k > 0)
    cnt["tick_unknown_or_changed"] = int((~tok).sum())
    j = j[tok].copy()
    j["steps"] = np.round(np.abs(j["x"].to_numpy(float)) / j["tick"].to_numpy(float))
    st = j["steps"] >= 1
    cnt["steps_below_1"] = int((~st).sum())
    j = j[st].copy()
    mk = j["market_id"].astype(str)
    j["osz"] = ser_k["osz"].reindex(mk).to_numpy(dtype=object)
    cnt["at_osz_stage"] = len(j)
    osz_ok = np.array([min_size_cutoff(v_, int(c["min_size_multiple"])) is not None for v_ in j["osz"]], bool)
    cnt["order_min_size_unknown"] = int((~osz_ok).sum())
    j = j[osz_ok].copy()
    mk = j["market_id"].astype(str)
    j["t_k"] = panel._epoch(f["origin_utc"].reindex(mk).astype(str))
    j["t_p"] = ser_p["t_row"].reindex(mk).to_numpy(float)
    j["n_ret"] = pd.to_numeric(f["n_returned"], errors="coerce").reindex(mk).to_numpy(float)
    return j.reset_index(drop=True), cnt


def clip_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, feat: pd.DataFrame, tr: pd.DataFrame, token0: pd.Series | None, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """K's units of one pass (section 3), origin-side filters in the declared order, each counted: :func:`clip_movers`, then interval
    coverage (``interval_truncated``) and ``n_int >= 4`` rows of known outcome with ``t_{k-1} <= ts < t_k``. Clip features from
    :func:`clip_unit_features`; ``g_path``, ``maxstep_share``, ``age``, ``fresh`` from LT5 J's ``path_fields``. Reads trade rows
    with ``ts < t_k`` only (the interval)."""
    j, cnt = clip_movers(ser_k, ser_p, feat, cap, spec)
    return clip_finish(j, cnt, tr, token0, cap, spec)


def clip_finish(j: pd.DataFrame, cnt: dict, tr: pd.DataFrame, token0: pd.Series | None, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    c = spec["k"]
    nret = j["n_ret"].to_numpy(float)
    pf = l5.path_fields(tr, j, nret, token0, _J_SHIM)
    j = pd.concat([j, pf], axis=1)
    cnt["traded_ge4_rows"] = int((j["n_int_all"] >= c["n_int_min"]).sum())
    cnt["traded_ge4_truncated"] = int(((j["n_int_all"] >= c["n_int_min"]) & (j["interval_truncated"] == 1)).sum())
    cnt["interval_truncated"] = int(j["interval_truncated"].sum())
    cnt["interval_rows_all"] = int(np.nansum(j["n_int_all"]))
    cnt["interval_rows_not_minute"] = int(np.nansum(j["n_int_not_minute"]))
    j = j[j["interval_truncated"] == 0]
    ok = j["n_int"] >= c["n_int_min"]
    cnt["rows_below_min"] = int((~ok).sum())
    j = j[ok].reset_index(drop=True)
    if j.empty:
        cnt["qualifying"] = 0
        return j, cnt
    known = ~np.isnan(l5.yes_price(tr, token0))
    by_mkt = {m_: g for m_, g in tr.assign(_known=known).groupby(tr["market_id"].astype(str))}
    feats = []
    for i in range(len(j)):
        g = by_mkt.get(str(j["market_id"].iloc[i]))
        sub = interval_rows(g, float(j["t_p"].iloc[i]), float(j["t_k"].iloc[i]), g["_known"].to_numpy()) if g is not None else tr.iloc[0:0]
        feats.append(clip_unit_features(sub, j["osz"].iloc[i], float(j["t_k"].iloc[i]), spec))
    ff = pd.DataFrame(feats)
    j = pd.concat([j.drop(columns=["n_int"]), ff.drop(columns=["cutoff_unknown"])], axis=1)
    j["class_k"] = [clip_class(s, spec) for s in j["clip_share"]]
    j["slot"] = b.slot_of(cap["start"], spec)
    j["day"] = _utc_day(cap["start"])
    j["mid"] = (j["bid"] + j["ask"]) / 2.0
    cnt["qualifying"] = len(j)
    return j, cnt


# --- shared census statistics --------------------------------------------------------------------------------------------


def m_co_of(lab: pd.DataFrame) -> float:
    """The size-weighted mean number of labelled units per event x capture cell with >= 1 labelled unit: ``sum m^2 / sum m``
    (D, B; 1 for V and K). NaN for no labelled unit."""
    if lab.empty:
        return float("nan")
    m = lab.groupby([lab["event_id"].astype(str), lab["slot"]]).size().to_numpy(float)
    return float((m**2).sum() / m.sum())


def de_gate6(pop: pd.DataFrame, key: str, scale: float, a: dict, m_co: float = 1.0) -> dict:
    """``DE_gate = max(3.0, 1 + (m_21 - 1) 0.02, 1 + (m_co - 1) 0.5)`` (section 7). NaN stays NaN (the gate fails)."""
    de = b.design_effect(pop[key].astype(str), scale, float(a["de_rho"]))
    terms = [float(a["de_floor"]), de["DE"], 1.0 + (m_co - 1.0) * float(a["de_rho_co"])]
    de["m_co"] = m_co
    de["DE_gate"] = float(max(terms)) if all(np.isfinite(t) for t in terms) else float("nan")
    return de


def mde_class6(n1: float, n2: float, sd: float, de_gate: float, a: dict, vif_w: float) -> float:
    """Class MDE (price units): ``3.388 SD sqrt(1/n1 + 1/n2) sqrt(DE_gate) 1.5 sqrt(max(1, VIF_w))``. A NaN ``VIF_w`` gives inf (the gate fails)."""
    if not np.isfinite(vif_w):
        return float("inf")
    return l5.mde_class(n1, n2, sd, de_gate, a, vif_w)


def perm_share_labelled(pop: pd.DataFrame, label: np.ndarray, t0: float, min_stratum: int) -> dict:
    """Share of the LABELLED units (clip, later, birth) that sit in permutable strata (>= ``min_stratum`` units of the test's
    population in the stratum): market x UTC day, else market x two-day block (section 1.8). ``stratum`` None = the test fails."""
    label = np.asarray(label, bool)
    if pop.empty or not label.any():
        return {"day": 0.0, "block2": 0.0, "stratum": None}
    day = np.floor((pop["t_row"].to_numpy(float) - t0) / DAY_S).astype(int)
    out = {}
    for name, key in (("day", day), ("block2", day // 2)):
        st = pop["market_id"].astype(str).to_numpy() + "|" + key.astype(str)
        sz = pd.Series(st).map(pd.Series(st).value_counts()).to_numpy()
        out[name] = float((sz[label] >= min_stratum).mean())
    out["stratum"] = "day" if out["day"] >= 0.5 else ("block2" if out["block2"] >= 0.5 else None)
    return out


def _derived(pop: pd.DataFrame, vol: str = "vol24") -> pd.DataFrame:
    """Common transformed columns used as controls (logit mid, |mid - 0.5|, log1p volume and liquidity, hours to end with a flag).
    ``vol`` names the volume24hr column (``vol24`` = at k; ``vol24_p`` = at k - 1, V's and K's control)."""
    pop = pop.copy()
    mid = pop["mid"] if "mid" in pop else (pop["bid"] + pop["ask"]) / 2.0
    pop["logit_mid"] = np.log(mid / (1 - mid))
    pop["abs_dev"] = np.abs(mid - 0.5)
    pop["log1p_vol"] = np.log1p(pop[vol].clip(lower=0))
    pop["log1p_liq"] = np.log1p(pop["liq"].clip(lower=0))
    hte = (pop["end_ts"] - pop["t_row"]) / 3600.0
    pop["hte_unknown"] = hte.isna().astype(float)
    pop["log_hte"] = np.log(hte.clip(lower=1e-6)).where(hte.notna(), 0.0)  # declared exception: unknown end enters as 0 with its flag
    for c in ("chg_1d", "chg_1w"):
        pop[f"{c}_flag"] = pop[c].isna().astype(float)
        pop[c] = pop[c].fillna(0.0)
    return pop


def _gate_min_days(res: dict, key: str, covered_days: float, minimum: float) -> dict:
    """Below its minimum covered days every gate of the census is NaN and fails (R1 item 9)."""
    res["covered_days"], res["min_covered_days"] = covered_days, minimum
    if not (np.isfinite(covered_days) and covered_days >= minimum):
        g = res.get(key, {})
        res[key] = {**{k_: False for k_ in g if k_ != "pass"}, "covered_days": False, "pass": False, "values_nan": True}
    else:
        res[key]["covered_days"] = True
    return res


CONTROLS_V = ["z_vprev", "a_traded", "a_parallel", "a_one_sided", "a_spread_change", "z_log_abs_x", "log1p_D0k", "log1p_D0p", "zh0", "spread_sw_k", "spread_sw_p",
              "logit_mid", "abs_dev", "log1p_vol", "log1p_liq", "tick001", "log_hte", "hte_unknown"]
CONTROLS_K = ["log1p_n_int", "log_abs_x", "g_path", "maxstep_share", "fresh", "log1p_age", "round_share", "H_unsigned", "a_parallel", "a_one_sided", "a_spread_change",
              "spread", "logit_mid", "abs_dev", "log1p_vol", "log1p_liq", "tick001", "log_hte", "hte_unknown"]
CONTROLS_D = ["theta24", "log_T", "x", "d24", "chg_1d", "chg_1w", "chg_1d_flag", "chg_1w_flag", "logit_mid", "abs_dev", "spread", "log1p_vol", "log1p_liq", "neg_risk", "updated_changed"]
CONTROLS_B = ["a1", "a6", "a24", "loo_a1", "log_event_size", "neg_risk", "logit_mid", "abs_dev", "spread", "log1p_vol", "log1p_liq", "log_hte", "chg_1d", "chg_1d_flag"]


def prepare_v(pop: pd.DataFrame, centre: float, scale: float) -> pd.DataFrame:
    """V's regression columns (census and analysis share this): ``zv = (v - centre) / scale`` and ``z_vprev`` on the SAME centre and
    scale, ``zh0``, the anatomy dummies (traded, parallel, one-sided, spread-change; same-side-unequal the base), ``z_log_abs_x``,
    ``log1p`` depths, ``tick001`` and the common derived columns (``vol24_p`` = volume24hr at k - 1)."""
    pop = _derived(pop, "vol24_p")
    ok = scale is not None and np.isfinite(scale) and scale > 0
    pop["zv"] = (pop["v"] - centre) / scale if ok else np.nan
    pop["z_vprev"] = (pop["v_prev"] - centre) / scale if ok else np.nan
    sh = pop["h0"].std()
    pop["zh0"] = (pop["h0"] - pop["h0"].mean()) / sh if sh and np.isfinite(sh) and sh > 0 else np.nan
    pop["traded"] = (pop["cls"] == "traded").astype(float)
    la_ = np.log(np.abs(pop["x"]))
    sd = la_.std()
    pop["z_log_abs_x"] = (la_ - la_.mean()) / sd if sd and np.isfinite(sd) and sd > 0 else np.nan
    pop["log1p_D0k"], pop["log1p_D0p"] = np.log1p(pop["D0_k"]), np.log1p(pop["D0_p"])
    # E015's anatomy as ONE categorical (freeze-check fix; design V controls): traded, else the geometry; same-side-unequal is the base.
    # The four dummies are mutually exclusive (a traded unit is 'traded' only), so with the intercept they are not collinear.
    traded = pop["cls"].eq("traded")
    pop["anatomy"] = np.where(traded, "traded", pop["geom"].astype(str))
    for d_ in ("traded", "parallel", "one_sided", "spread_change"):
        pop[f"a_{d_}"] = pop["anatomy"].eq(d_).astype(float)
    pop["tick001"] = (np.abs(pop["tick"] - 0.001) <= 1e-12).astype(float)
    return pop


def prepare_k(pop: pd.DataFrame) -> pd.DataFrame:
    """K's regression columns: ``CL = 1[clip]`` and the controls of section 3 (``vol24_p`` = volume24hr at k - 1)."""
    pop = _derived(pop, "vol24_p")
    pop["CL"] = (pop["class_k"] == "clip").astype(float)
    pop["log1p_n_int"] = np.log1p(pop["n_int"])
    pop["log_abs_x"] = np.log(np.abs(pop["x"]))
    pop["log1p_age"] = np.log1p(pop["age"].clip(lower=0))
    pop["tick001"] = (np.abs(pop["tick"] - 0.001) <= 1e-12).astype(float)
    for d_ in ("parallel", "one_sided", "spread_change"):
        pop[f"a_{d_}"] = pop["geom"].eq(d_).astype(float)
    return pop


def prepare_d(pop: pd.DataFrame) -> pd.DataFrame:
    """D's regression columns: ``LT = 1[later]`` and the controls of section 4 (``vol24`` = volume24hr at k)."""
    pop = _derived(pop)
    pop["LT"] = (pop["cls"] == "later").astype(float)
    return pop


def prepare_b(pop: pd.DataFrame) -> pd.DataFrame:
    """B's regression columns: ``BR = 1[birth]`` and the controls of section 5 (``vol24`` = volume24hr at k)."""
    pop = _derived(pop)
    pop["BR"] = (pop["cls"] == "birth").astype(float)
    return pop


def _fam(pop: pd.DataFrame, cap: float) -> tuple[pd.DataFrame, str, float | None]:
    return b._family_rule(pop, float(cap)) if len(pop) else (pop, "", None)


# --- the four censuses ----------------------------------------------------------------------------------------------------


def census_d(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, block_t0: float, crypto_fs: dict) -> dict:
    """CD (D): counts only. Washout and the primary population (by-date later and no-change units, ``d24`` known) are applied BEFORE
    every projected count, ``n2_eff`` and ``VIF_w`` (R1 re-check n8)."""
    g, a = spec["census_gates"]["CD_D"], spec["census_gates"]["mde_common"]
    mind = spec["census_inputs"]["min_covered_days"]["CD"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_D": {"pass": False}}, "gate_D", covered_days, mind)
    dirm = U[U["cls"].isin(["later", "rollover", "overdue"])]
    cr_cls = dirm["crypto6"].isin(["crypto", "unknown"])
    kill = ((dirm["cls"] == "rollover") | cr_cls)
    kill_share = float(kill.mean()) if len(dirm) and crypto_fs.get("classifier_shown_to_work") else float("nan")
    Uw, n_wash = apply_washout(U, "no_change", ("later", "earlier"), int(spec["d"]["washout_slots"]))
    pop0 = Uw[Uw["bydate"] & Uw["cls"].isin(["later", "no_change"])]
    lb = int(pop0["d24"].isna().sum())
    pop0 = pop0[pop0["d24"].notna()]
    updated_missing = int(pop0["updated_changed"].isna().sum())  # 1.5: a missing control excludes the unit, counted
    pop0 = pop0[pop0["updated_changed"].notna()]
    pop, excl, top = _fam(pop0, g["family_cap"])
    pop = prepare_d(pop.copy())
    if pop.empty or not (pop["cls"] == "later").any():
        res = {"error": "no later units", "units": len(U), "by_class": {str(k_): int(v) for k_, v in U["cls"].value_counts().items()}, "exclude_family": excl,
               "top_family_share": top, "washout_dropped": n_wash, "rollover_plus_crypto_share": kill_share, "crypto_failsafe": crypto_fs.get("classifier_shown_to_work"),
               "gate_D": {"pass": False}}
        return _gate_min_days(res, "gate_D", covered_days, mind)
    ctrl = CONTROLS_D
    eff = b._eff(pop)
    n1, n2 = float(((pop["LT"] == 1) & eff).sum() * scale), float(((pop["LT"] == 0) & eff).sum() * scale)
    lab = pop[pop["LT"] == 1]
    de = de_gate6(pop, "event_id", scale, a, m_co_of(lab))
    dsg = l5.design_ss(pop, "LT", ctrl)
    mde = mde_class6(n1, n2, a["sd_D"], de["DE_gate"], a, dsg["vif_w"]) * 100.0
    ps = perm_share_labelled(pop, (pop["LT"] == 1).to_numpy(), block_t0, int(spec["gates"]["perm_min_stratum"]))
    c_th, c_x, c_liq = l5.wcorr(pop, "LT", "theta24"), l5.wcorr(pop, "LT", "x"), l5.wcorr(pop, "LT", "log1p_liq")
    unp = tot.get("unparseable_end_date", 0) / max(tot.get("candidates", 0), 1) if tot.get("candidates", 0) else float("nan")
    later_21d = float(len(lab) * scale)
    res = {"units": len(U), "by_class": {str(k_): int(v) for k_, v in U["cls"].value_counts().items()}, "washout_dropped": n_wash, "lookback_missing": lb, "updated_at_missing_excluded": updated_missing,
           "exclude_family": excl, "top_family_share": top, "later_21d": later_21d, "later_eff_21d": n1, "nochange_eff_21d": n2,
           "later_direction_moves": len(dirm), "rollover_plus_crypto_share": kill_share, "crypto_failsafe": crypto_fs.get("classifier_shown_to_work"),
           "unparseable_end_date_share": unp, "design_effect": de, "design": dsg, "mde_eff_c": mde, "perm_share": ps, "corr_later_theta24": c_th,
           "corr_later_x": c_x, "corr_later_liq": c_liq, "events_with_later": int(lab["event_id"].nunique()),
           "later_per_market": _per_market_sums(lab["market_id"]),
           "bydate_clock_hist_ET": tot.get("bydate_hist", {}),
           "old_end_ge7d_later_21d": float(((lab["old_end_days"] >= spec["d"]["old_end_subset_days"]).sum()) * scale)}
    res["gate_D"] = b._gate({"later_units": later_21d >= g["later_units_projected_min"],
                             "rollover_crypto": bool(np.isfinite(kill_share) and kill_share <= g["rollover_plus_crypto_share_max"]),
                             "unparseable": bool(np.isfinite(unp) and unp <= g["unparseable_end_date_max"]),
                             "corr_theta24": l5.corr_ok(c_th, g["corr_max"]), "corr_x": l5.corr_ok(c_x, g["corr_max"]),
                             "corr_liq": l5.corr_ok(c_liq, g["corr_max"], both=True), "perm_share": bool(ps["stratum"] is not None and ps[ps["stratum"]] >= g["perm_share_min"]),
                             "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return _gate_min_days(res, "gate_D", covered_days, mind)


def census_b(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, block_t0: float, crypto_fs: dict) -> dict:
    """CB (B): counts only. The clean no-birth rule (lagged appearances, guard losses, unparseable ``created_at`` and recurring
    newcomers are excluded, never class 0) and the washout are applied BEFORE the projections, ``n2_eff`` and ``VIF_w``."""
    g, a = spec["census_gates"]["CB_B"], spec["census_gates"]["mde_common"]
    mind = spec["census_inputs"]["min_covered_days"]["CB"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_B": {"pass": False}}, "gate_B", covered_days, mind)
    ex_all = tot.get("excluded_by_reason", {})
    births_ev = U[U["cls"] == "birth"].drop_duplicates(["event_id", "slot"])
    cg = crypto_gate_share(births_ev["crypto_birth"]) if len(births_ev) else {"share_as_crypto": float("nan")}
    crypto_share = cg["share_as_crypto"] if crypto_fs.get("classifier_shown_to_work") else float("nan")
    Uw, n_wash = apply_washout(U, "nobirth", ("birth",), int(spec["b"]["washout_slots"]))
    pop0 = Uw[Uw["cls"].isin(["birth", "nobirth"])]
    lb = int(pop0[["a6", "a24"]].isna().any(axis=1).sum())
    pop0 = pop0.dropna(subset=["a6", "a24"])
    pop, excl, top = _fam(pop0, g["family_cap"])
    pop = prepare_b(pop.copy())
    if pop.empty or not (pop["cls"] == "birth").any():
        res = {"error": "no birth units", "units": len(U), "by_class": {str(k_): int(v) for k_, v in U["cls"].value_counts().items()}, "excluded_by_reason": ex_all,
               "exclude_family": excl, "top_family_share": top, "washout_dropped": n_wash, "crypto_failsafe": crypto_fs.get("classifier_shown_to_work"),
               "gate_B": {"pass": False}}
        return _gate_min_days(res, "gate_B", covered_days, mind)
    ctrl = CONTROLS_B
    pop2 = pop.dropna(subset=["loo_a1"])
    eff = b._eff(pop2)
    n1, n2 = float(((pop2["BR"] == 1) & eff).sum() * scale), float(((pop2["BR"] == 0) & eff).sum() * scale)
    lab = pop2[pop2["BR"] == 1]
    de = de_gate6(pop2, "event_id", scale, a, m_co_of(lab))
    dsg = l5.design_ss(pop2, "BR", ctrl)
    mde = mde_class6(n1, n2, a["sd_B"], de["DE_gate"], a, dsg["vif_w"]) * 100.0
    ps = perm_share_labelled(pop2, (pop2["BR"] == 1).to_numpy(), block_t0, int(spec["gates"]["perm_min_stratum"]))
    c24, cl1, cliq = l5.wcorr(pop2, "BR", "a24"), l5.wcorr(pop2, "BR", "loo_a1"), l5.wcorr(pop2, "BR", "log1p_liq")
    kinds = tot.get("newcomer_kinds", {})
    n_new = sum(kinds.values())
    parse_share = 1.0 - kinds.get("created_unparseable", 0) / n_new if n_new else float("nan")
    ex = tot.get("excluded_by_reason", {})
    n_birth_units = int((U["cls"] == "birth").sum())
    gl = ex.get("guard_loss", 0) / max(n_birth_units + ex.get("guard_loss", 0), 1) if (n_birth_units + ex.get("guard_loss", 0)) else float("nan")
    births_21d = float(len(births_ev) * scale)
    cuts = [float(x) for x in np.quantile(lab["loo_a1"], [1 / 3, 2 / 3])] if len(lab) >= 3 else None
    res = {"units": len(U), "by_class": {str(k_): int(v) for k_, v in U["cls"].value_counts().items()}, "excluded_by_reason": ex, "newcomer_kinds": kinds,
           "washout_dropped": n_wash, "lookback_missing": lb, "exclude_family": excl, "top_family_share": top, "births_21d": births_21d,
           "birth_units_21d": float(len(lab) * scale), "birth_eff_21d": n1, "nobirth_eff_21d": n2, "created_at_parseable_share": parse_share,
           "guard_loss_share": gl, "crypto_births": cg, "crypto_failsafe": crypto_fs.get("classifier_shown_to_work"), "design_effect": de, "design": dsg,
           "mde_eff_c": mde, "perm_share": ps, "corr_birth_a24": c24, "corr_birth_loo": cl1, "corr_birth_liq": cliq, "fake_birth_terciles": cuts,
           "birth_events": int(lab["event_id"].nunique()), "incumbents_per_birth": float(len(lab) / max(len(births_ev), 1)),
           "birth_per_market": _per_market_sums(lab["market_id"])}
    res["gate_B"] = b._gate({"births": births_21d >= g["births_projected_min"], "birth_units": res["birth_units_21d"] >= g["birth_units_projected_min"],
                             "created_at_parseable": bool(np.isfinite(parse_share) and parse_share >= g["created_at_parseable_min"]),
                             "guard_loss": bool(np.isfinite(gl) and gl <= g["guard_loss_max"]), "corr_a24": l5.corr_ok(c24, g["corr_max"]),
                             "corr_loo": l5.corr_ok(cl1, g["corr_max"]), "corr_liq": l5.corr_ok(cliq, g["corr_max"], both=True),
                             "crypto_births": bool(np.isfinite(crypto_share) and crypto_share <= g["crypto_births_share_max"]),
                             "perm_share": bool(ps["stratum"] is not None and ps[ps["stratum"]] >= g["perm_share_min"]), "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return _gate_min_days(res, "gate_B", covered_days, mind)


def census_v(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, block_t0: float) -> dict:
    """CV (V): counts only, from sweep 1 of passes k - 1 and k. ``zv`` is standardised on the census population (its centre, scale and
    tercile cuts are the values fixed into the spec). The MDE is the slope formula per SD times the tercile gap with
    ``max(declared, design)`` (section 7)."""
    g, a = spec["census_gates"]["CV_V"], spec["census_gates"]["mde_common"]
    mind = spec["census_inputs"]["min_covered_days"]["CV"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_V": {"pass": False}}, "gate_V", covered_days, mind)
    pop, excl, top = _fam(U, g["family_cap"])
    movers = tot.get("non_sports_movers", 0)
    cov = len(U) / movers if movers else float("nan")
    cv, sv = float(pop["v"].mean()), float(pop["v"].std())
    pop = prepare_v(pop.copy(), cv, sv)
    ctrl = CONTROLS_V
    t1, t2 = np.quantile(pop["zv"].dropna(), [1 / 3, 2 / 3]) if pop["zv"].notna().sum() >= 3 else (np.nan, np.nan)
    gap = float(pop.loc[pop["zv"] >= t2, "zv"].mean() - pop.loc[pop["zv"] <= t1, "zv"].mean()) if np.isfinite(t1) else float("nan")
    eff = b._eff(pop)
    de = de_gate6(pop, "event_id", scale, a, 1.0)
    dsg = l5.design_ss(pop[eff], "zv", ctrl)
    mde_sd = max(l5.mde_slope_design(dsg["ss_resid"], scale, a["sd_V"], de["DE_gate"], a),
                 l5.mde_slope_declared(float(eff.sum()) * scale, a["sd_V"], de["DE_gate"], a, dsg["vif_w"]))
    mde = mde_sd * gap * 100.0 if np.isfinite(gap) and np.isfinite(dsg["vif_w"]) else float("inf")
    dep = depletion_gate(pop[pop["cls"] == "traded"], g)
    dep_q = depletion_gate(pop[pop["cls"] == "quote_only"], g)
    iq = pop.groupby("market_id")["v"].agg(lambda s: float(np.quantile(s, 0.75) - np.quantile(s, 0.25)) if len(s) >= g["iqr_min_units"] else np.nan).dropna()
    iqr_share = float((iq >= g["iqr_min"]).mean()) if len(iq) else float("nan")
    rec = float((pop.groupby("market_id")["market_id"].transform("size") >= 2).mean())
    cps = [("vprev", "z_vprev"), ("h0", "zh0"), ("traded", "traded"), ("log_abs_x", "z_log_abs_x")]
    corr = {nm: l5.wcorr(pop, "zv", col) for nm, col in cps}
    cl = l5.wcorr(pop, "zv", "log1p_liq")
    projected = float(len(U) * scale)
    res = {"units": len(U), "projected_units_21d": projected, "both_sweep_coverage": cov, "exclude_family": excl, "top_family_share": top,
           "v": {"centre": cv, "scale": sv, "terciles": [float(t1), float(t2)], "tercile_gap": gap}, "design_effect": de, "design": dsg, "mde_per_sd_c": mde_sd * 100.0,
           "mde_tercile_c": mde, "depletion_traded": dep, "depletion_quote_only_printed": dep_q, "corr": corr, "corr_liq": cl, "iqr_share": iqr_share, "iqr_markets": len(iq),
           "block_recurrence_share": rec, "by_class": {str(k_): int(v_) for k_, v_ in pop["cls"].value_counts().items()},
           "sports_note": "non-sports population", "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_V"] = b._gate({"units": projected >= g["units_projected_min"], "both_sweep_coverage": bool(np.isfinite(cov) and cov >= g["both_sweep_coverage_min"]),
                             "depletion_1c_asym": bool(dep["pass_1c"]), "depletion_5c_toward": bool(dep["pass_5c"]),
                             **{f"corr_{nm}": l5.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, "corr_liq": l5.corr_ok(cl, g["corr_max"], both=True),
                             "iqr": bool(np.isfinite(iqr_share) and iqr_share >= g["iqr_share_min"] and len(iq) >= g["iqr_markets_min"]),
                             "block_recurrence": bool(rec >= g["block_share_min"]), "mde_tercile": bool(mde <= g["mde_max"] * 100.0)})
    return _gate_min_days(res, "gate_V", covered_days, mind)


def _per_market_sums(market_ids: pd.Series) -> dict:
    """Counts only (design 7 / R1 recommended): the distribution of labelled units per market and the share of labelled units in
    markets with exactly one. No gate."""
    per = market_ids.astype(str).value_counts()
    dist = per.value_counts().sort_index()
    return {"markets": int(len(per)), "labelled_units": int(per.sum()), "units_per_market_hist": {str(int(k_)): int(v) for k_, v in dist.items()},
            "share_in_markets_with_one": float(market_ids.astype(str).map(per).eq(1).mean()) if len(market_ids) else float("nan")}


def census_k(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, block_t0: float) -> dict:
    """CK (K): counts only, from the sealed active-frame samples (interval rows with ``ts < t_k`` only)."""
    g, a = spec["census_gates"]["CK_K"], spec["census_gates"]["mde_common"]
    mind = spec["census_inputs"]["min_covered_days"]["CK"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_K": {"pass": False}}, "gate_K", covered_days, mind)
    pop0 = U[U["class_k"].isin(["clip", "clip_free"])]
    pop, excl, top = _fam(pop0, g["family_cap"])
    pop = prepare_k(pop.copy())
    ctrl = CONTROLS_K
    eff = b._eff(pop)
    n1, n2 = float(((pop["CL"] == 1) & eff).sum() * scale), float(((pop["CL"] == 0) & eff).sum() * scale)
    de = de_gate6(pop, "event_id", scale, a, 1.0)
    dsg = l5.design_ss(pop, "CL", ctrl)
    mde = mde_class6(n1, n2, a["sd_K"], de["DE_gate"], a, dsg["vif_w"]) * 100.0
    ps = perm_share_labelled(pop, (pop["CL"] == 1).to_numpy(), block_t0, int(spec["gates"]["perm_min_stratum"]))
    corr = {nm: l5.wcorr(pop, "CL", col) for nm, col in (("g_path", "g_path"), ("fresh", "fresh"), ("n_int", "log1p_n_int"), ("H_unsigned", "H_unsigned"))}
    cl = l5.wcorr(pop, "CL", "log1p_liq")
    n_q = len(U)
    n_clip = int((U["class_k"] == "clip").sum())
    n_free = int((U["class_k"] == "clip_free").sum())
    wb, wb_min, wb_rnd = float(U["would_be_clip_notional"].sum()), float(U["would_be_clip_notional_minsize"].sum()), float(U["clip_notional_round"].sum())
    cn = float(U["clip_notional"].sum())
    minsize_share = wb_min / wb if wb > 0 else float("nan")
    round_share = wb_rnd / cn if cn > 0 else float("nan")
    tsn = tot["interval_rows_not_minute"] / tot["interval_rows_all"] if tot.get("interval_rows_all") else float("nan")
    osz_share = 1.0 - tot.get("order_min_size_unknown", 0) / tot["at_osz_stage"] if tot.get("at_osz_stage") else float("nan")
    trunc = tot.get("traded_ge4_truncated", 0) / tot["traded_ge4_rows"] if tot.get("traded_ge4_rows") else float("nan")
    res = {"qualifying": n_q, "qualifying_21d": n_q * scale, "clip_units": n_clip, "clip_21d": n_clip * scale, "clip_free_21d": n_free * scale,
           "clip_share_of_qualifying": n_clip / n_q if n_q else float("nan"), "interior_units": int((U["class_k"] == "interior").sum()),
           "exclude_family": excl, "top_family_share": top, "clip_eff_21d": n1, "clip_free_eff_21d": n2, "design_effect": de, "design": dsg, "mde_eff_c": mde,
           "perm_share": ps, "corr": corr, "corr_liq": cl, "minsize_would_be_clip_notional_share": minsize_share, "round_clip_notional_share": round_share,
           "ts_not_minute_share": tsn, "order_min_size_present_share": osz_share, "interval_truncated_share": trunc,
           "clip_share_hist": {str(k_): int(v) for k_, v in pd.cut(U["clip_share"], [-1e-9, 0, 0.1, 0.25, 0.5, 1.0]).value_counts().sort_index().items()},
           "n_trains_mean": float(U["n_trains"].mean()), "sports_share": float((pop["sports"] == 1).mean()),
           "clip_per_market": _per_market_sums(pop.loc[pop["CL"] == 1, "market_id"])}
    res["gate_K"] = b._gate({"ts_second_level": bool(np.isfinite(tsn) and tsn >= g["ts_not_minute_min"]),
                             "order_min_size": bool(np.isfinite(osz_share) and osz_share >= g["order_min_size_present_min"]),
                             "qualifying": res["qualifying_21d"] >= g["qualifying_projected_min"],
                             "clip_share": bool(n_q and n_clip / n_q >= g["clip_share_of_qualifying_min"]), "clip_units": res["clip_21d"] >= g["clip_projected_min"],
                             "clip_free": res["clip_free_21d"] >= g["clip_free_projected_min"],
                             "min_size_notional": bool(np.isfinite(minsize_share) and minsize_share <= g["minsize_would_be_clip_notional_max"]),
                             "round_notional": bool(np.isfinite(round_share) and round_share <= g["round_clip_notional_max"]),
                             "interval_truncated": bool(np.isfinite(trunc) and trunc <= g["truncated_max"]),
                             **{f"corr_{nm}": l5.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, "corr_liq": l5.corr_ok(cl, g["corr_max"], both=True),
                             "perm_share": ps["stratum"] is not None, "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return _gate_min_days(res, "gate_K", covered_days, mind)


# --- sealed inputs and the census drivers ---------------------------------------------------------------------------------


def census_span_slots(spec: dict) -> list[int]:
    """Every grid slot of the CD / CB span (spec ``census_inputs.cd_cb_span``), present or not."""
    sp = spec["census_inputs"]["cd_cb_span"]
    k0, k1 = b.slot_of(epoch(sp["first_slot_utc"]), spec), b.slot_of(epoch(sp["last_slot_utc"]), spec)
    return list(range(k0, k1 + 1))


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    """Refuse anything at or after the sealed bound (``census_inputs.refuse_at_or_after_utc``): the span itself, and every slot the
    seal assigns to a directory."""
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = []
    last = epoch(spec["census_inputs"]["cd_cb_span"]["last_slot_utc"])
    if last >= bound:
        bad.append({"what": "span.last_slot_utc", "value": spec["census_inputs"]["cd_cb_span"]["last_slot_utc"], "error": "at or after the sealed bound"})
    for d, s in (seal.get("slots") or {}).items():
        if epoch(s) >= bound:
            bad.append({"what": d, "value": s, "error": "at or after the sealed bound"})
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def _src_hashes(source_seals: list[Path]) -> tuple[dict, list, dict]:
    """(rel path -> sha256, sample ids, seal shas) of the source seals; a file named with two different hashes is an error."""
    src: dict[str, str] = {}
    samples: list[str] = []
    shas: dict[str, str] = {}
    for pth in source_seals:
        d = json.loads(Path(pth).read_text())
        shas[str(pth)] = sha256_file(Path(pth))
        for rel, v in (d.get("files") or {}).items():
            sha = v["sha256"] if isinstance(v, dict) else v
            if rel in src and src[rel] != sha:
                raise ValueError(f"source seals name {rel} with two different hashes")
            src[rel] = sha
        samples += [s for s in d.get("samples", []) if s not in samples]
    return src, samples, shas


def seal_inputs(*, snapshot_root, sweep_root, sample_root, work: Path, source_seals: list[Path], spec: dict | None = None) -> dict:
    """The LT6 seal (section 7). Selection rule, declared now: a capture (rows, manifest and its sidecar if present), its sweep 1, or a
    sample is selected only if EVERY file it opens is named in a source seal (LT5's capture seal, LT3's C2 sample seal, LT4's
    capture seal) with an equal sha256 and its slot lies in the span. A capture with a missing, unsealed or different-hash file
    is NOT selected: a hash mismatch refuses the seal; a slot with no selectable capture is genuinely missing (counted per
    slot, never substituted). Hashes bytes only; parses no rows; nothing at or after the sealed bound is hashed."""
    spec = spec or load_spec(sha=None)
    src, samples, shas = _src_hashes(list(source_seals))
    # freeze-check fix: the LT5 capture seal's sha256 is pinned in the spec (filled after LT5's seal is committed); refuse while it is null
    pin = (spec["census_inputs"].get("source_seals") or {}).get("lt5_capture_seal_sha256")
    if not pin:
        return {"error": "spec census_inputs.source_seals.lt5_capture_seal_sha256 is null: the LT6 seal is refused until the LT5 capture seal's sha256 is pinned"}
    if pin not in shas.values():
        return {"error": "no source seal given has the pinned lt5_capture_seal_sha256: LT6 seal refused", "pinned": pin, "given": shas}
    by_slot, sweeps = l5._scan(Path(work), snapshot_root, sweep_root, spec)
    span = census_span_slots(spec)
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    files: dict[str, dict] = {}
    slots: dict[str, str] = {}
    mism: list[dict] = []
    not_sel: list[dict] = []
    sel_slots: set[int] = set()

    def take(rels: list[tuple[str, Path]], extra: dict) -> bool:
        """All-or-nothing: select the group only if every file is sealed with an equal hash."""
        ok = True
        got = {}
        for rel, pth in rels:
            want = src.get(rel)
            if want is None:
                not_sel.append({"file": rel, "reason": "not named in any source seal"})
                ok = False
                continue
            sha = sha256_file(pth)
            if sha != want:
                mism.append({"file": rel, "want": want, "got": sha})
                ok = False
                continue
            got[rel] = {"sha256": sha, **extra}
        if ok:
            files.update(got)
        return ok

    for k in span:
        c = by_slot.get(k)
        if c is None or c["start"] >= bound:
            continue
        if take(b.capture_files(c["dir"]), {"root": str(Path(c["dir"]).parent)}):
            slots[c["id"]] = iso(b.slot_time(k, spec))
            sel_slots.add(k)
            if c["id"] in sweeps:
                sd = Path(sweeps[c["id"]]["dir"])
                if take(b.sweep_files(sd), {"root": str(sd.parent), "capture": c["id"]}):
                    slots[sd.name] = iso(b.slot_time(k, spec))
    smp_roots = l5._roots(sample_root)
    used_samples = []
    for sid in samples:
        sdir = next((r / sid for r in smp_roots if (r / sid / "trades.csv.gz").exists()), None)
        if sdir is None:
            not_sel.append({"sample": sid, "reason": "absent locally"})
            continue
        if take([(f"data-dumps/research_lab/trade_samples/{sid}/{fn}", sdir / fn) for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz")],
                {"root": str(sdir.parent)}):
            used_samples.append(sid)
    if mism:
        return {"error": "hash mismatch against a source seal: LT6 seal refused", "mismatches": mism[:50], "n_mismatches": len(mism)}
    missing = [iso(b.slot_time(k, spec)) for k in span if k not in sel_slots]
    return {"purpose": "LT6 census inputs (LIVE_TESTS_6.md section 7): exactly the files the censuses open, each named in a source seal with an equal sha256; counts-only use",
            "written_utc": iso(b.now_ts()), "spec_sha256": sha256_file(SPEC_PATH), "source_seals": shas, "span": spec["census_inputs"]["cd_cb_span"],
            "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"], "slots": slots, "samples": used_samples,
            "missing_slots": missing, "n_missing_slots": len(missing), "not_selected": not_sel[:100], "n_not_selected": len(not_sel),
            "n_files": len(files), "files": dict(sorted(files.items()))}


def _seal_scan(seal: dict, snapshot_root, sweep_root, work: Path, spec: dict) -> tuple[dict, dict]:
    """Complete captures and sweeps found locally, restricted to those the seal names (a local file the seal does not name is
    never opened: its slot counts as unsealed / missing). ``slots`` of the seal lists capture and sweep directory names."""
    by_slot, sweeps = l5._scan(Path(work), snapshot_root, sweep_root, spec)
    sealed = set(seal.get("slots", {}))
    by_slot = {k: c for k, c in by_slot.items() if c["id"] in sealed}
    sweeps = {sid: v for sid, v in sweeps.items() if Path(v["dir"]).name in sealed}
    return by_slot, sweeps


def _frames(work: Path, by_slot: dict, k: int, spec: dict, cache: dict) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    if k not in by_slot:
        return None, None
    if k not in cache:
        write_frames6(work, by_slot[k], spec)
        cache[k] = (read_ser6(work, by_slot[k]["id"]), read_ser6(work, by_slot[k]["id"], "members6").reset_index())
    return cache[k]


def _merge_counts(tot: dict, cnt: dict) -> None:
    for a, v in cnt.items():
        if isinstance(v, dict):
            d = tot.setdefault(a, {})
            for kk, vv in v.items():
                d[kk] = d.get(kk, 0) + vv
        elif isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
            tot[a] = tot.get(a, 0) + v


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, sweep_root=SWEEP_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CD (D), CB (B) and CV (V) on the sealed capture span. Before anything is parsed: the bound check, then every sealed capture
    or sweep in a needed slot must be present with every sealed file, and every opened file must be sealed with an equal sha256
    (LT5's ``seal_completeness``), else the census is refused (L3). Slots with no sealed capture are counted as missing, a pair
    across a gap is no pair. CD / CB use every pair of consecutive complete slots with the 12-slot look-back inside the span; CV
    uses the passes of the spec's ``cv_days_utc`` (each with its pass k - 1 sweep)."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    seal_d = json.loads(Path(seal).read_text())
    viol = bound_violations(seal_d, spec)
    if viol:
        return {"error": "sealed bound violated: census refused", "bad": viol, "n_bad": len(viol)}
    by_slot, sweeps = _seal_scan(seal_d, snapshot_root, sweep_root, work, spec)
    span = census_span_slots(spec)
    cv_days = spec["census_inputs"]["cv_days_utc"]
    cv_k = [k for k in l5.census_slots(cv_days, spec)]
    cap_slots = set(span)
    sweep_slots = {j for k in cv_k for j in (k - 1, k)}
    comp = l5.seal_completeness(seal_d, by_slot, sweeps, cap_slots, sweep_slots, spec, sweep_root) if verify else {"bad": [], "missing_slots": [], "n_missing_slots": 0, "files_checked": 0}
    if verify and comp["bad"]:
        return {"error": "input identity check failed (L3): census refused", "bad": comp["bad"][:50], "n_bad": len(comp["bad"])}
    cache: dict = {}
    UD, UB, UV = [], [], []
    totd: dict = {}
    totb: dict = {}
    totv: dict = {}
    fee_counts: dict = {}
    pairs = 0
    cv_passes = 0
    per_cap = []
    for k in span:
        if k not in by_slot:
            continue
        c = by_slot[k]
        ser_k, mem_k = _frames(work, by_slot, k, spec, cache)
        vc = mem_k["fee_cat"].where(mem_k["fee_cat"].notna(), "<none>").value_counts()
        for kk, vv in vc.items():
            fee_counts[kk] = fee_counts.get(kk, 0) + int(vv)
        rec = {"capture": c["id"]}
        if k - 1 in by_slot:
            ser_p, mem_p = _frames(work, by_slot, k - 1, spec, cache)
            pairs += 1
            ser_12 = cache.get(k - 12, (None, None))[0] if k - 12 in by_slot else None
            if k - 12 in by_slot and k - 12 not in cache:
                ser_12 = _frames(work, by_slot, k - 12, spec, cache)[0]
            ud, cd = deadline_units(ser_k, ser_p, ser_12, k, c, spec)
            hist = {j: (_frames(work, by_slot, j, spec, cache)[0] if j in by_slot else None) for j in (k - 3, k - 12)}
            ub, cb_, nk = birth_units(ser_k, ser_p, mem_k, mem_p, hist, k, c, by_slot[k - 1], spec)
            if len(ud):
                UD.append(ud)
            if len(ub):
                UB.append(ub)
            _merge_counts(totd, cd)
            _merge_counts(totb, cb_)
            rec["D"], rec["B"] = {a: v for a, v in cd.items() if isinstance(v, (int, float))}, {a: v for a, v in cb_.items() if isinstance(v, (int, float))}
            if k in cv_k:
                sw_k = b.sweep_frame(sweeps[c["id"]]["dir"], c["dir"]).set_index("market_id") if c["id"] in sweeps else None
                pc = by_slot[k - 1]
                sw_p = b.sweep_frame(sweeps[pc["id"]]["dir"], pc["dir"]).set_index("market_id") if pc["id"] in sweeps else None
                uv, cv = vote_units(ser_k, ser_p, sw_k, sw_p, c, spec)
                if len(uv):
                    UV.append(uv)
                    cv_passes += 1
                _merge_counts(totv, cv)
                rec["V"] = {a: v for a, v in cv.items() if isinstance(v, (int, float))}
        else:
            rec["skipped"] = "no previous slot"
        per_cap.append(rec)
        for j in [j for j in list(cache) if j < k - 13]:
            cache.pop(j)
    fs = crypto_failsafe(fee_counts)
    days = b._days_of(by_slot, sorted({_utc_day_iso(c["start"]) for c in by_slot.values()}))
    t0 = b.block_anchor(spec, [min(_utc_day_iso(c["start"]) for c in by_slot.values())]) if by_slot else 0.0
    cov_pairs = pairs / 12.0
    sc_d = 21.0 / cov_pairs if cov_pairs else float("nan")
    cov_v = cv_passes / 12.0
    sc_v = 21.0 / cov_v if cov_v else float("nan")
    Ud = pd.concat(UD, ignore_index=True) if UD else pd.DataFrame()
    Ub = pd.concat(UB, ignore_index=True) if UB else pd.DataFrame()
    Uv = pd.concat(UV, ignore_index=True) if UV else pd.DataFrame()
    return {"span": spec["census_inputs"]["cd_cb_span"], "n_captures": len(by_slot), "inputs_verified": bool(verify), "missing_slots": comp.get("missing_slots"),
            "n_missing_slots": comp.get("n_missing_slots"), "covered_pairs": pairs, "covered_days_cd_cb": cov_pairs, "cv_passes": cv_passes, "covered_days_cv": cov_v,
            "files_checked": comp.get("files_checked"), "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"],
            "per_capture": per_cap, "n_days": len(days),
            "CD": census_d(Ud, totd, spec, sc_d, cov_pairs, t0, fs), "CB": census_b(Ub, totb, spec, sc_d, cov_pairs, t0, fs),
            "CV": census_v(Uv, totv, spec, sc_v, cov_v, t0)}


def _utc_day_iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d")


def census_flow(*, seal: Path, sample_roots: list[Path], snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CK (K) on the sealed active-frame samples with their captures k - 1 and k; refused on any mismatch or on the bound. Trade rows
    with ``ts < t_k`` only; ``side`` is never read."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    sl = json.loads(Path(seal).read_text())
    viol = bound_violations(sl, spec)
    if viol:
        return {"error": "sealed bound violated: census refused", "bad": viol, "n_bad": len(viol)}
    by_slot, _ = _seal_scan(sl, snapshot_root, None, work, spec)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    bad, found = [], {}
    for sid in sl.get("samples", []):
        sdir = next((Path(r) / sid for r in sample_roots if (Path(r) / sid / "trades.csv.gz").exists()), None)
        if sdir is None:
            bad.append({"sample": sid, "error": "not found"})
            continue
        if verify:
            bad += [{"sample": sid, **x} for x in b.verify_files(sl, [(f"data-dumps/research_lab/trade_samples/{sid}/{fn}", sdir / fn)
                                                                     for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz")])]
        k = slot_by_id.get(b._manifest(sdir / "manifest.json").get("snapshot_id"))
        if k is None:
            bad.append({"sample": sid, "error": "capture not found among the sealed captures"})
            continue
        found[sid] = (sdir, k)
    cap_slots = {j for _, k in found.values() for j in (k - 1, k)}
    comp = l5.seal_completeness(sl, by_slot, {}, cap_slots, set(), spec) if verify and cap_slots else {"bad": [], "missing_slots": [], "n_missing_slots": 0}
    bad += comp.get("bad", [])
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    U, per, tot = [], [], {}
    used = 0
    for sid, (sdir, k) in found.items():
        if k - 1 not in by_slot:
            per.append({"sample": sid, "skipped": "no previous slot"})
            continue
        ser_k, _ = _frames(work, by_slot, k, spec, {})
        ser_p, _ = _frames(work, by_slot, k - 1, spec, {})
        feat, tr = load_sample6(sdir)
        tok = b.token0_map(by_slot[k]["dir"], feat["market_id"].astype(str)) if len(feat) else None
        u, cnt = clip_units(ser_k, ser_p, feat, tr, tok, by_slot[k], spec)
        if len(u):
            u["sample_id"] = sid
            U.append(u)
        _merge_counts(tot, cnt)
        used += 1
        per.append({"sample": sid, "K": {a: v for a, v in cnt.items() if isinstance(v, (int, float))}})
    cov = used / 12.0
    scale = 21.0 / cov if cov else float("nan")
    Uk = pd.concat(U, ignore_index=True) if U else pd.DataFrame()
    t0 = b.block_anchor(spec, [min(_utc_day_iso(by_slot[k]["start"]) for _, k in found.values())]) if found else 0.0
    return {"seal": str(seal), "inputs_verified": bool(verify), "samples": used, "covered_days": cov, "missing_capture_slots": comp.get("missing_slots"),
            "per_sample": per, "CK": census_k(Uk, tot, spec, scale, cov, t0)}


def cleanup_census(work: Path) -> None:
    b.cleanup_census(work)


# =====================================================================================================================
# Unit 4: the reader (sections 8.1-8.2 as amended by 14 and 15)
# =====================================================================================================================
#
# One pass per host pass, write-once (``%.17g``, atomic hard link), in this order: (1) ``series/`` ``status/`` ``members/`` for
# every capture in [REGISTERED - 26 h, END + 13 slots) and ``sweeps/`` for its sweep 1 -- ALWAYS, also on a pass whose freezes are
# late, so the next pass's k - 1 inputs survive; look-back labels for captures before REGISTERED (never units); (2) the freezes of
# captures / samples in [REGISTERED, END) that are not late; (3) the due outcomes. Markers (``.late`` ``.noprev`` ``.nosweep``
# ``.noprevsweep`` ``.e022boundary``) record a unit file that was refused, never re-read. The reader never reads a target to decide
# anything, and ``ops_stats`` reads no price column.

import fcntl  # noqa: E402

DISK_CAP_BYTES = int(1.5e9)
GRID_S, SLOT_TOL_S = b.GRID_S, b.SLOT_TOL_S
SERIES_LOOKBACK_S = 26 * 3600.0  # D's / B's k - 12 (24 h) plus the 2 h tolerance: the earliest input of the first origin
LOOKBACK_SLOTS_BEFORE = 13  # captures after END_UTC still needed as k + 12 targets
MISSING_AFTER_S = l3.MISSING_AFTER_S
ROLE_CONF, ROLE_UNREG = l3.ROLE_CONF, l3.ROLE_UNREG
MARKERS = (".late.csv.gz", ".noprev.csv.gz", ".nosweep.csv.gz", ".noprevsweep.csv.gz", ".e022boundary.csv.gz")
KINDS = ("vote", "clips", "deadline", "birth")
TEST_OF_KIND = {"vote": "V", "clips": "K", "deadline": "D", "birth": "B"}
# kind -> (Gamma-capture horizons h, sweep-1 horizons s) of the outcome files (slots k + h; section 1.3)
OUTCOME_PLAN = {"vote": ([1, 3], [1, 3]), "clips": ([1, 3], [1, 3]), "deadline": ([1, 3, 12], []), "birth": ([1, 3, 12], [])}
READER_FILES = ("live_tests6.py", "live_tests5.py", "live_tests5_base.py", "live_tests3.py")
OPS_COLS = frozenset({"role", "cls", "class_k", "geom", "sports", "reason", "status", "late", "checked_utc", "noprev", "nosweep", "crypto6", "crypto_birth", "slot"})
DROP_FROZEN = ("end_raw", "fee_cat", "osz", "present")


def reader_sha() -> str:
    """16 hex digits identifying the reader code: the joint hash of the modules the reader runs (stamped on every frozen line)."""
    import hashlib

    h = code_hashes()
    return hashlib.sha256("".join(str(h.get(n)) for n in READER_FILES).encode("utf-8")).hexdigest()[:16]


def pinned_reader_sha(spec: dict) -> str | None:
    """The same joint hash from the spec's ``code_sha256`` map (what a pinned analysis keeps)."""
    import hashlib

    pins = spec.get("code_sha256") or {}
    if any(pins.get(n) is None for n in READER_FILES):
        return None
    return hashlib.sha256("".join(str(pins.get(n)) for n in READER_FILES).encode("utf-8")).hexdigest()[:16]


def check_pinned_code(spec: dict) -> None:
    """Fail loudly (every pass) when a pinned spec's code hashes differ from the running code: lines written by other code would carry
    another ``code_sha`` and be silently dropped at analysis (as E026's ``check_pinned_code``)."""
    if not spec.get("_pinned"):
        return
    h, want = code_hashes(), spec.get("code_sha256") or {}
    bad = [f for f in CODE_FILES if h.get(f) != want.get(f)]
    if bad:
        raise RuntimeError(f"LIVE_TESTS6_CODE_MISMATCH: running code differs from the pinned hashes for {bad}")


def running_capture_start(snapshot_root: Path, lo: float, now: float, max_age_s: float = 4 * 3600) -> float:
    """Vendored from the E026 pattern (not imported). Earliest start (>= ``lo``) of a capture that is NOT complete yet but started less
    than ``max_age_s`` ago (still being written). A later complete capture must not be processed before it: its k - 1 would look
    missing and its units would be marked ``.noprev``. Older incomplete captures are failed ones and are ignored. ``inf`` if none."""
    out = math.inf
    for p in Path(snapshot_root).glob("*/manifest.json"):
        try:
            started = epoch(datetime.strptime(p.parent.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat())
        except ValueError:
            continue
        if not math.isfinite(started) or started < lo - 3600 or now - started >= max_age_s:
            continue
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            m = {}
        t = epoch(m.get("started_utc")) if m.get("started_utc") else started
        t = t if math.isfinite(t) else started
        if t >= lo and not (m.get("state") == "complete" and (p.parent / "rows.csv.gz").exists()):
            out = min(out, t)
    return out


def enabled_kinds(spec: dict) -> dict[str, bool]:
    """Which kinds the pass collects: a kind whose test is not in ``k_tests`` is switched off once ``k_tests`` is fixed (LT3 13.16 fix 2)."""
    kt = spec.get("k_tests")
    return {k: (kt is None or TEST_OF_KIND[k] in kt) for k in KINDS}


def _marker(p: Path, suffix: str) -> Path:
    return p.with_name(p.name.replace(".csv.gz", suffix))


def _stamp(df: pd.DataFrame, spec: dict, commit: str, role: str, cap_start: float) -> pd.DataFrame:
    df = df.drop(columns=[c for c in (*DROP_FROZEN, "frozen_utc", "code_commit", "spec_sha", "code_sha", "role", "capture_t") if c in df.columns])
    df["role"], df["capture_t"], df["frozen_utc"] = role, cap_start, iso(b.now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"] = commit, spec["_sha256"][:16], reader_sha()
    return df


def write_capture_files(root: Path, cap: dict, spec: dict) -> tuple[bool, dict]:
    """Write-once ``series/`` (LT6's compact series), ``status/`` and ``members/`` of one capture."""
    rows, ext = load_rows6(cap["dir"]), load_ext6(cap["dir"])
    ser, sta = ser6_frame(rows, ext, spec, with_status=True)
    w = [b.write_once_csv(Path(root) / "series" / f"{cap['id']}.csv.gz", ser), b.write_once_csv(Path(root) / "status" / f"{cap['id']}.csv.gz", sta),
         b.write_once_csv(Path(root) / "members" / f"{cap['id']}.csv.gz", members_frame(rows, ext, spec))]
    return any(w), {"rows": len(ser), "status_rows": len(sta), "sidecar": bool((ser["sports"] != -1).any()) if len(ser) else None}


def _ser(root: Path, by_slot: dict, j: int) -> pd.DataFrame | None:
    return read_ser6(root, by_slot[j]["id"], "series") if j in by_slot else None


def _mem(root: Path, by_slot: dict, j: int) -> pd.DataFrame | None:
    m = read_ser6(root, by_slot[j]["id"], "members") if j in by_slot else None
    return None if m is None else m.reset_index()


def write_lookback_labels(root: Path, by_slot: dict, k: int, spec: dict, kinds: dict | None = None) -> dict:
    """Look-back labels of a capture BEFORE REGISTERED (never units): the later / earlier D changes and the B births seen at k, as
    ``deadline/lookback/<capture>.csv.gz`` and ``birth/lookback/<capture>.csv.gz`` (market, slot, class). They only mark the washout of
    the first window units (stricter: a pre-window event can only remove units)."""
    root, c = Path(root), by_slot[k]
    out = {"written": 0}
    kinds = kinds or enabled_kinds(spec)
    pd_, pb_ = root / "deadline" / "lookback" / f"{c['id']}.csv.gz", root / "birth" / "lookback" / f"{c['id']}.csv.gz"
    if (pd_.exists() or not kinds["deadline"]) and (pb_.exists() or not kinds["birth"]):
        return out
    if not (_ser(root, by_slot, k) is not None and (k - 1) in by_slot and _ser(root, by_slot, k - 1) is not None):
        out["no_previous"] = 1
        return out
    ser_k, ser_p = _ser(root, by_slot, k), _ser(root, by_slot, k - 1)
    mem_k, mem_p = _mem(root, by_slot, k), _mem(root, by_slot, k - 1)
    ud, _ = deadline_units(ser_k, ser_p, _ser(root, by_slot, k - 12), k, c, spec)
    lab_d = ud[ud["cls"].isin(["later", "earlier"])][["market_id", "slot", "cls"]] if len(ud) else pd.DataFrame({"market_id": [], "slot": [], "cls": []})
    hist = {j: _ser(root, by_slot, j) for j in (k - 3, k - 12)}
    ub, _, _ = birth_units(ser_k, ser_p, mem_k, mem_p, hist, k, c, by_slot[k - 1], spec)
    lab_b = ub[ub["cls"] == "birth"][["market_id", "slot", "cls"]] if len(ub) else pd.DataFrame({"market_id": [], "slot": [], "cls": []})
    out["written"] = (int(b.write_once_csv(pd_, lab_d)) if kinds["deadline"] else 0) + (int(b.write_once_csv(pb_, lab_b)) if kinds["birth"] else 0)
    return out


def run_once(*, snapshot_root: Path = SNAPSHOT_ROOT, sample_root: Path = SAMPLE_ROOT, sweep_root: Path = SWEEP_ROOT, root: Path = OUT_ROOT,
             spec: dict | None = None, registered_utc: str | None = None, end_utc: str | None = None, now: float | None = None,
             max_items: int = 40, allow_late: bool = False, mode: str = "run") -> dict:
    """Series, sweeps, look-back labels, freezes and due outcomes for everything new. Idempotent (write-once). ``mode='backfill'``
    writes only the series / status / members / sweeps / look-back labels (``backfill-series``). ``allow_late`` is for DRY RUNS on past
    captures with an unpinned spec only (L6). An internal non-blocking flock on ``run.lock`` serialises readers."""
    spec = spec or load_spec()
    if allow_late and spec.get("_pinned"):
        raise ValueError("allow_late is for dry runs with an unpinned spec only")
    registered_utc, end_utc = registered_utc or spec.get("registered_utc"), end_utc or spec.get("end_utc")
    if registered_utc is None or end_utc is None:
        raise ValueError("registered_utc / end_utc are null in the DRAFT spec: pass them explicitly for a dry run")
    if mode not in ("run", "backfill"):
        raise ValueError(f"unknown mode {mode!r}")
    check_pinned_code(spec)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "run.lock", "a") as lk:
        try:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "locked", "written": 0, "run_utc": iso(b.now_ts() if now is None else now)}
        return _run_locked(snapshot_root=snapshot_root, sample_root=sample_root, sweep_root=sweep_root, root=root, spec=spec, registered_utc=registered_utc,
                           end_utc=end_utc, now=b.now_ts() if now is None else now, max_items=max_items, allow_late=allow_late, mode=mode)


def _refuse(p: Path, suffix: str, now: float, stats: dict, log: list, kind: str, fid: str, k: int, key: str = "refused_late") -> None:
    stats[key] = stats.get(key, 0) + 1
    b.write_once_csv(_marker(p, suffix), pd.DataFrame({suffix.split(".")[1]: [1], "checked_utc": [iso(now)]}))
    log.append({"kind": f"{kind}_{suffix.split('.')[1]}", "id": fid, "slot": k, "written_utc": iso(b.now_ts())})


def _run_locked(*, snapshot_root, sample_root, sweep_root, root: Path, spec: dict, registered_utc: str, end_utc: str, now: float, max_items: int,
                allow_late: bool, mode: str) -> dict:
    commit = b.git_commit()
    stats: dict = {"run_utc": iso(now), "code_commit": commit, "spec_sha": spec["_sha256"][:16], "pinned": spec["_pinned"], "mode": mode, "written": 0,
                   "series": 0, "sweeps": 0, "lookback_labels": 0, "outcomes": 0, "refused_late": 0, **{k: 0 for k in KINDS}}
    if root.exists() and b.dir_bytes(root) > DISK_CAP_BYTES:
        stats["status"] = "disk_cap"
        b.append_jsonl(root / "passes.jsonl", [{"kind": "disk_cap", **stats}])
        return stats
    t_reg, t_end = epoch(registered_utc), epoch(end_utc)
    st = b.State(root)
    by_slot = b.scan_captures(snapshot_root, st, spec)
    samples = b.scan_samples(sample_root, st) if mode == "run" else {}
    sweeps = b.scan_sweeps(sweep_root, st)
    st.save()
    # running-capture guard: a capture still being written blocks every LATER capture (its k - 1 would look missing)
    block = running_capture_start(snapshot_root, t_reg - SERIES_LOOKBACK_S - 3600.0, now)
    if math.isfinite(block):
        stats["blocked_by_running_capture"] = sum(1 for c in by_slot.values() if c["start"] > block)
        by_slot = {k: c for k, c in by_slot.items() if c["start"] < block}
    log: list[dict] = []
    budget = max_items
    pinned = spec["_pinned"]
    hi = t_end + LOOKBACK_SLOTS_BEFORE * GRID_S + SLOT_TOL_S
    kinds = enabled_kinds(spec)
    # 1. series / status / members, sweep 1 (ALWAYS, also for passes whose freezes are late), look-back labels
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg - SERIES_LOOKBACK_S <= c["start"] < hi) or budget <= 0:
            continue
        if not all((root / sub / f"{c['id']}.csv.gz").exists() for sub in ("series", "status", "members")):
            w, info = write_capture_files(root, c, spec)
            if w:
                stats["series"] += 1
                budget -= 1
                log.append({"kind": "lookback_series" if c["start"] < t_reg else "series", "id": c["id"], "slot": k, **info, "written_utc": iso(b.now_ts())})
        p = root / "sweeps" / f"{c['id']}.csv.gz"
        if c["id"] in sweeps and not p.exists() and budget > 0:
            if b.write_once_csv(p, b.sweep_frame(sweeps[c["id"]]["dir"], c["dir"])):
                stats["sweeps"] += 1
                budget -= 1
                log.append({"kind": "lookback_sweep" if c["start"] < t_reg else "sweep", "id": c["id"], "sweep_id": sweeps[c["id"]]["id"], "written_utc": iso(b.now_ts())})
        if c["start"] < t_reg and budget > 0 and (root / "series" / f"{c['id']}.csv.gz").exists():
            lb = write_lookback_labels(root, by_slot, k, spec, kinds)
            if lb["written"]:
                stats["lookback_labels"] += lb["written"]
                log.append({"kind": "lookback_labels", "id": c["id"], "slot": k, "written_utc": iso(b.now_ts())})
    if mode == "run":
        budget = _freezes(root, by_slot, samples, sweeps, spec, t_reg, t_end, now, budget, allow_late, pinned, registered_utc, end_utc, commit, kinds, stats, log)
        budget = _outcomes(root, by_slot, sweeps, spec, now, budget, kinds, stats, log)
    stats["written"] = sum(stats[k] for k in ("series", "sweeps", "lookback_labels", "outcomes", *KINDS))
    stats["status"] = "wrote" if stats["written"] else "nothing_new"
    for r in log:
        r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
    b.append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
    return stats


def _freezes(root, by_slot, samples, sweeps, spec, t_reg, t_end, now, budget, allow_late, pinned, registered_utc, end_utc, commit, kinds, stats, log) -> int:
    e022_end = (spec.get("e022") or {}).get("end_utc")
    # a DRAFT (unpinned) spec has no E022 decision yet: dry runs (the 8.2 ladder, tests) keep the old permissive behaviour; a pinned one never does
    e022_dropped = bool((spec.get("e022") or {}).get("dropped")) or not pinned
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        role = l3.role_of(c["start"], registered_utc, end_utc, pinned)
        for kind in ("vote", "deadline", "birth"):
            p = root / kind / "frozen" / f"{c['id']}.csv.gz"
            if not kinds[kind] or p.exists() or any(_marker(p, s).exists() for s in MARKERS) or budget <= 0:
                continue
            late = not allow_late and l3.is_late(k + 1, now, spec)
            pc = by_slot.get(k - 1)
            if late:  # freeze-check fix: a late pass is .late whether or not its sweep exists (the late rule is first; units lost, counted)
                _refuse(p, ".late.csv.gz", now, stats, log, kind, c["id"], k)
                continue
            if k - 1 not in by_slot:
                if l3.target_state(by_slot, k - 1, now, spec) == "pending":
                    continue
                b.write_once_csv(_marker(p, ".noprev.csv.gz"), pd.DataFrame({"noprev": [1]}))
                log.append({"kind": f"{kind}_no_previous_slot", "id": c["id"], "slot": k})
                continue
            if not l3.series_ready(root, by_slot, (k - 1, k)):
                continue
            ser_k, ser_p = _ser(root, by_slot, k), _ser(root, by_slot, k - 1)
            if kind == "vote":
                sk, sp = l3.sweep_state(by_slot, sweeps, k, root, now, spec), l3.sweep_state(by_slot, sweeps, k - 1, root, now, spec)
                if "pending" in (sk, sp):
                    continue
                if sk == "missing":
                    _refuse(p, ".nosweep.csv.gz", now, stats, log, kind, c["id"], k, "nosweep")
                    continue
                if sp == "missing":
                    _refuse(p, ".noprevsweep.csv.gz", now, stats, log, kind, c["id"], k, "noprevsweep")
                    continue
                sdir_p = sweeps[pc["id"]]["dir"] if pc["id"] in sweeps else None
                sw_start = l5._name_time(Path(sdir_p).name) if sdir_p else pc["start"]
                if not v_first_origin_ok(iso(pc["start"]), iso(sw_start), e022_end, e022_dropped):
                    _refuse(p, ".e022boundary.csv.gz", now, stats, log, kind, c["id"], k, "e022_boundary")
                    continue
                units, cnt = vote_units(ser_k, ser_p, l3.read_sweep(root, c["id"]), l3.read_sweep(root, pc["id"]), c, spec)
            elif kind == "deadline":
                units, cnt = deadline_units(ser_k, ser_p, _ser(root, by_slot, k - 12), k, c, spec)
            else:
                units, cnt, _ = birth_units(ser_k, ser_p, _mem(root, by_slot, k), _mem(root, by_slot, k - 1),
                                            {j: _ser(root, by_slot, j) for j in (k - 3, k - 12)}, k, c, pc, spec)
            if len(units):
                units = units.assign(capture_id=c["id"], k_slot=k)
            fr = _stamp(units, spec, commit, role, c["start"]) if len(units) else pd.DataFrame(
                {"capture_t": [], "role": [], "market_id": [], "slot": [], "frozen_utc": [], "code_commit": [], "spec_sha": [], "code_sha": []})
            if b.write_once_csv(p, fr):
                stats[kind] += 1
                budget -= 1
                log.append({"kind": f"{kind}_frozen", "id": c["id"], "slot": k, "counts": {a: v for a, v in cnt.items() if isinstance(v, (int, float, dict))}, "written_utc": iso(b.now_ts())})
    # K: one freeze per complete active-frame sample
    if not kinds["clips"]:
        return budget
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    for sid in sorted(samples):
        k = slot_by_id.get(samples[sid]["snapshot_id"])
        if k is None:
            continue
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        p = root / "clips" / "frozen" / f"{sid}.csv.gz"
        if p.exists() or any(_marker(p, s).exists() for s in MARKERS) or budget <= 0:
            continue
        if not allow_late and l3.is_late(k + 1, now, spec):
            _refuse(p, ".late.csv.gz", now, stats, log, "clips", sid, k)
            continue
        if k - 1 not in by_slot:
            if l3.target_state(by_slot, k - 1, now, spec) == "pending":
                continue
            b.write_once_csv(_marker(p, ".noprev.csv.gz"), pd.DataFrame({"noprev": [1]}))
            continue
        if not l3.series_ready(root, by_slot, (k - 1, k)):
            continue
        role = l3.role_of(c["start"], registered_utc, end_utc, pinned)
        ser_k, ser_p = _ser(root, by_slot, k), _ser(root, by_slot, k - 1)
        sdir = Path(samples[sid]["dir"])
        feat0, _ = load_sample6(sdir, markets=[])  # features only
        j, cnt = clip_movers(ser_k, ser_p, feat0, c, spec)
        feat, tr = load_sample6(sdir, markets=j["market_id"].astype(str), before=float(j["t_k"].max()) if len(j) else None)
        tok = b.token0_map(c["dir"], j["market_id"].astype(str)) if len(j) else None
        units, cnt2 = clip_finish(j, cnt, tr, tok, c, spec) if len(j) else (j, cnt)
        del tr
        if len(units):
            units = units.assign(capture_id=c["id"], sample_id=sid, k_slot=k)
        fr = _stamp(units, spec, commit, role, c["start"]) if len(units) else pd.DataFrame(
            {"capture_t": [], "role": [], "market_id": [], "slot": [], "frozen_utc": [], "code_commit": [], "spec_sha": [], "code_sha": []})
        if b.write_once_csv(p, fr):
            stats["clips"] += 1
            budget -= 1
            log.append({"kind": "clips_frozen", "id": sid, "capture_id": c["id"], "slot": k, "counts": {a: v for a, v in cnt2.items() if isinstance(v, (int, float))},
                        "written_utc": iso(b.now_ts())})
    return budget


def _outcomes(root, by_slot, sweeps, spec, now, budget, kinds, stats, log) -> int:
    for kind, (hs, ss) in OUTCOME_PLAN.items():
        if not kinds[kind]:
            continue
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
                out = l3.outcome_h(mids, by_slot, j, root, state == "missing") if typ == "h" else l3.outcome_s(
                    mids, None if state == "missing" else l3.read_sweep(root, by_slot[j]["id"]), state == "missing")
                if b.write_once_csv(root / kind / "outcomes" / f"{fid}.{typ}{h}.csv.gz", out):
                    stats["outcomes"] += 1
                    budget -= 1
                    log.append({"kind": f"{kind}_outcome", "id": fid, "tag": f"{typ}{h}", "target_slot": j, "target": state, "rows": len(out), "written_utc": iso(b.now_ts())})
    return budget


# --- operational counts (never reads a price, a move, a state value or a target) ----------------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def lookback_slots_missing(root: Path, spec: dict, registered_utc: str) -> list[str]:
    """Slots in [REGISTERED - 26 h, REGISTERED) with no ``series/`` line (neither backfill nor arrival): ``lookback_missing`` (counted
    per slot, never imputed or restored from a later file). Names are slot times; a slot is covered by any series file whose capture id
    starts within the 30-minute tolerance."""
    t_reg = epoch(registered_utc)
    have = []
    for f in (Path(root) / "series").glob("*.csv.gz") if (Path(root) / "series").exists() else []:
        try:
            have.append(epoch(datetime.strptime(f.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()))
        except ValueError:
            continue
    k_first = int(math.ceil((t_reg - b.grid0(spec)) / GRID_S))  # the first origin slot: the first capture starting at or after REGISTERED_UTC
    out = []
    for k in range(k_first - 12, k_first):  # its inputs reach back to slot k - 12 (24 h)
        ts = b.slot_time(k, spec)
        if not any(abs(h - ts) <= SLOT_TOL_S for h in have):
            out.append(iso(ts))
    return out


def ops_stats(root: Path = OUT_ROOT, spec: dict | None = None, registered_utc: str | None = None) -> dict:
    root = Path(root)
    out: dict = {"root": str(root), "bytes": b.dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "members", "sweeps", *(f"{k}/frozen" for k in KINDS), *(f"{k}/outcomes" for k in KINDS), "deadline/lookback", "birth/lookback"):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(MARKERS)]), **{s.split(".")[1]: len([f for f in files if f.name.endswith(s)]) for s in MARKERS}}
    counts, status = {}, {}
    cols = {"vote": ["role", "cls", "geom", "sports"], "clips": ["role", "class_k", "geom", "sports"], "deadline": ["role", "cls", "sports", "crypto6"],
            "birth": ["role", "cls", "reason", "sports", "crypto_birth"]}
    for kind, cl in cols.items():
        d = root / kind / "frozen"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith(MARKERS):
                continue
            s = _read_ops(f, cl)
            for c in s.columns:
                for k_, v in s[c].value_counts().items():
                    counts[f"{kind}:{c}:{k_}"] = counts.get(f"{kind}:{c}:{k_}", 0) + int(v)
        d = root / kind / "outcomes"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            tag = f.name[:-7].rsplit(".", 1)[-1]
            s = _read_ops(f, ["status"])
            for k_, v in s["status"].value_counts().items():
                status[f"{kind}:{tag}:{k_}"] = status.get(f"{kind}:{tag}:{k_}", 0) + int(v)
    out.update(line_counts=counts, outcome_status_counts=status)
    reg = registered_utc or (spec or {}).get("registered_utc")
    if reg and spec:
        miss = lookback_slots_missing(root, spec, reg)
        out["lookback_missing"] = {"n": len(miss), "slots": miss}
    return out
