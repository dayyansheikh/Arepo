# ruff: noqa: E501
"""CB12-X: horizon-dependent staleness on the audited C1 cross-venue pairs (docs/research_lab/CREATIVE_BATCH_12.md CB12-X, section 10 item 22). Rules part ``X``.

Host files only (``cross_venue/``, the 2026-10-12 historical study): no fetch, no network. The C1 set is reproduced through ``scripts/run_cross_venue.py``
(``load_pair_series`` and ``audit_sets``; no fork of the definitions): 316 pairs, 183 events, 517,616 usable steps. Horizon ``tau(t) = endDate_PM - t`` with the *scheduled*
end from ``poly_markets.json`` (streamed, ids and ``end`` / volume only). The statistic is the pooled AR(1) half-life of the pair-demeaned gap by horizon bin, and X1 is
``HL_long - HL_short`` (one-sided > 0, floor 60 min). Label on every line: "L1, worn set, new moderator, hindsight end date". No edge claim.

This module imports ``cb12_common`` (and the study's ``cross_venue``) and nothing from the other CB12 families, so its rules hash is independent of M / E / F / O code.
The census (counts only) never calls ``gap_of``: it sees usable-step masks, horizons and categories only (unit-tested with ``gap_of`` poisoned). ``cross_venue_live/``
is refused by every path; any grid step at or after ``T12_X_END`` and any input file modified at or after 2026-10-13T00:00Z is refused.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb12_common as c12
from . import cross_venue as cv

Refused = cm.Refused


class C1ReproductionError(Refused):
    """The C1 reproduction did not give 316 / 183 / 517,616: a counted ``not testable (source)`` outcome (census and screen), not a free refusal."""

LABEL_X = "L1, worn set, new moderator, hindsight end date"
SOURCE_LABEL = "not testable (source)"
X_DIR_NAME = "cross_venue"
GRID_MIN = 10.0
BIN_SHORT_S = 3 * 86400.0  # short: tau <= 3 d
BIN_LONG_S = 30 * 86400.0  # long: tau > 30 d; mid in between
BINS = ("short", "mid", "long")
HL_CAP_MIN = 7 * 24 * 60.0  # rho >= 1 -> HL = inf (reported); the bootstrap and the contrast use the 7 d cap
X1_FLOOR_MIN = 60.0
GX_MIN = {"pairs": 30, "events": 20, "steps": 20000}
EDIT_FLAG_S = 7 * 86400.0
LARGE_GAP = 0.03
FRESH_MAX_AGE_S = 600.0
CAUSAL_WINDOW_S = 3 * 86400.0
CAUSAL_MIN_OBS = 1  # ambiguity (design silent): the minimum that defines a past mean
STRATA = ("sports", "elections")
STRATUM_MIN_PAIRS = 10
TERCILES_MIN_HOLD = 2
AVAIL_MIN = 0.60
C1_EXPECTED = {"pairs": 316, "events": 183, "steps": 517616}
POLY_ID_KEY = "market_id"
POLY_END_KEY = "end"  # the SCHEDULED end (matches.json ``p_end`` is closed_time-first, i.e. the actual close: not used)
POLY_VOLUME_KEYS = ("volume", "volume_num", "volumeNum", "volume_total")
KALSHI_CLOSE_KEY = "close_time"
SMOKE_NEEDS = ("guards_fixture_X", "x_inputs_pinned", "x_c1_reproduction")
X_PINS = {
    "matches.json": "f21457665518e6a8a7d2afe7337c730fac3ebb889fa3476ff51bc1ae16d0e945",
    "audit_flags.json": "a7273ea747c8bb3162effe790363108fb820599c884a14d539b4ca464b6b7629",
    "audit_sample100.json": "9e8eb51a51dd49246a227a40d9c988afd09c48089c8ce97a363d7c6b8bcdb8ec",
    "poly_markets.json": "749adfa6faf34c4948fec9dc9e6bac2485133713370893e489aa5bd6434a23b2",
    "kalshi_markets.jsonl": "703fda587da8581651c1f8500c20ed7388647ecbf9234c748cf5540f7b3c073c",
    "kalshi_markets_b.jsonl": "47f49f5bd6875318a2fc92f54502c2df6a802d11f24de709658ec715862bedea",
    "kalshi_markets_s0.jsonl": "80445c4e2123a00d51eb3442b9f9cb5ace3b5bbb61ecede49fc8b544e5c55af0",
    "kalshi_markets_s1.jsonl": "a1a36adfd7b0fb9466df5905e58d7dded446897276b941435890ed352772943b",
    "kalshi_markets_s2.jsonl": "39975faf55e23d456bc28f80c56229391320321fac77ad9d75463b4a76713b55",
    "kalshi_markets_s3.jsonl": "0e13ffcac5f97cd1c52cbed939a34fae8997dee6aefd5e68bab61113ebd23755",
    "kalshi_markets_s4.jsonl": "6a47c20aea5b1de400b6d3a620d688915a9af950c3c232a09fd577c24b254234",
    "kalshi_markets_s5.jsonl": "9479b4cc7a089fe6e96bc99da4815854d7b73d6440869c260eee6d7438934d15",
}
X_SERIES_PIN = {"count": 493, "listing_sha256": "f930d276d1f49509bb90be21d8cab6b2c4bbb2d883e60b2b0c9791691028d6fd"}  # sha256 of "\n".join(f"{name} {sha256}") over sorted series/*.npz
CV_SCRIPT_REL = "backend/scripts/run_cross_venue.py"
CV_MODULE_REL = "backend/astrolabe/research_lab/cross_venue.py"
# The study code CB12-X executes (``exec_module`` of the script; ``cross_venue`` is imported by it) is sha256-pinned: a different byte refuses (exit 2) before anything runs.
CV_SOURCE_PINS = {CV_SCRIPT_REL: "cab073ab1caa66f41e9cfc543d60d64ac640738cfb2fce10f4cbbd021982f7b5", CV_MODULE_REL: "5264083948a77679189f14471290c2f84bf71dac01fc9632cb0633fdb59ace99"}
CV_CALLS = ("load_pair_series(cv.POINT_LAG_S)", "audit_sets(pairs, kept)['rule']")


def part_unready() -> str | None:
    bad = [k for k, v in X_PINS.items() if not v or v == c12.PIN_UNSET]
    if bad or not X_SERIES_PIN.get("listing_sha256") or X_SERIES_PIN["listing_sha256"] == c12.PIN_UNSET:
        return f"X input sha256 pins unset: {bad or ['series listing']}"
    return None


# =====================================================================================================================================================
# Guards and pinned inputs
# =====================================================================================================================================================


def refuse_step_time(t: float) -> None:
    """The runner refuses any step at or after ``T12_X_END`` (2026-10-12T00:00Z)."""
    if float(t) >= c12.T12_X_END_EPOCH:
        raise Refused(f"X step time {datetime.fromtimestamp(float(t), UTC):%Y-%m-%dT%H:%MZ} is at or after T12_X_end {c12.T12_X_END}; refusing")


def refuse_mtime(path: Path) -> None:
    if Path(path).stat().st_mtime >= c12.X_MTIME_MAX_EPOCH:
        raise Refused(f"X input {path} was modified at or after 2026-10-13T00:00Z; refusing")


def x_root(root: Path) -> Path:
    r = c12.refuse_path(Path(root), allow=c12.X_READABLE_ROOTS)
    if c12.LIVE_ROOT_NAME in str(r):
        raise Refused("cross_venue_live is never opened by a CB12 path")
    return r


def series_listing_sha(root: Path) -> tuple[int, str]:
    from . import h5_seal  # noqa: PLC0415

    files = sorted((Path(root) / "series").glob("*.npz"))
    for f in files:
        refuse_mtime(f)
    return len(files), hashlib.sha256("\n".join(f"{f.name} {h5_seal.sha256_file(f)}" for f in files).encode()).hexdigest()


def verify_inputs(root: Path, *, pins: dict | None = None, series_pin: dict | None = None, check_series: bool = True) -> dict:
    """Every pinned file exists, was written before 2026-10-13T00:00Z and matches its sha256; the series listing matches its pin. Exit 2 (``Refused``) otherwise."""
    from . import h5_seal  # noqa: PLC0415

    root = x_root(root)
    unready = part_unready()
    if unready and pins is None:
        raise Refused(unready)
    out = {}
    for name, want in (pins if pins is not None else X_PINS).items():
        p = root / name
        if not p.is_file():
            raise Refused(f"X input {name} missing under {root}")
        refuse_mtime(p)
        got = h5_seal.sha256_file(p)
        if got != want:
            raise Refused(f"X input {name} sha256 {got} != pinned {want}")
        out[name] = got
    sp = series_pin if series_pin is not None else X_SERIES_PIN
    if check_series:
        n, sha = series_listing_sha(root)
        if n != sp["count"] or sha != sp["listing_sha256"]:
            raise Refused(f"X series listing ({n} files, {sha}) != pinned ({sp['count']}, {sp['listing_sha256']})")
        out["series"] = {"count": n, "listing_sha256": sha}
    return out


def iter_json_array(path: Path, chunk: int = 1 << 20):
    """Stream the objects of a top-level JSON array one at a time (never ``json.load``: ``poly_markets.json`` is 171 MB)."""
    dec = json.JSONDecoder()
    with open(path, encoding="utf-8") as fh:
        buf, pos, eof, started = "", 0, False, False
        while True:
            if pos > chunk:
                buf, pos = buf[pos:], 0
            if not started:
                while pos < len(buf) and buf[pos] in " \n\r\t":
                    pos += 1
                if pos >= len(buf):
                    s = fh.read(chunk)
                    if not s:
                        return
                    buf += s
                    continue
                if buf[pos] != "[":
                    raise Refused(f"{path} is not a JSON array")
                pos += 1
                started = True
                continue
            while pos < len(buf) and buf[pos] in " \n\r\t,":
                pos += 1
            if pos >= len(buf):
                if eof:
                    raise Refused(f"{path}: truncated JSON array")
                s = fh.read(chunk)
                if not s:
                    eof = True
                buf += s
                continue
            if buf[pos] == "]":
                return
            try:
                obj, end = dec.raw_decode(buf, pos)
            except json.JSONDecodeError:
                if eof:
                    raise Refused(f"{path}: truncated JSON array") from None
                s = fh.read(chunk)
                if not s:
                    eof = True
                buf += s
                continue
            pos = end
            yield obj


def restricted_universes(root: Path, tickers: set[str], poly_ids: set[str]) -> tuple[list[dict], list[dict]]:
    """The Kalshi and Polymarket universe rows of the matched pairs only (``audit_sets`` reads nothing else), streamed: the Kalshi ``kalshi_markets*.jsonl`` line by line in the
    study's glob order (first occurrence of a ticker wins) and ``poly_markets.json`` object by object."""
    root = x_root(root)
    kalshi, seen = [], set()
    for f in sorted(root.glob("kalshi_markets*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                m = json.loads(line)
                t = m.get("ticker")
                if t in tickers and t not in seen:
                    seen.add(t)
                    kalshi.append(m)
    poly = [m for m in iter_json_array(root / "poly_markets.json") if isinstance(m, dict) and str(m.get(POLY_ID_KEY)) in poly_ids]
    return kalshi, poly


def poly_volume_key(m: dict) -> str | None:
    """The first key of ``POLY_VOLUME_KEYS`` with a finite value in the row (None if none): the census reports which one matched."""
    for k in POLY_VOLUME_KEYS:
        if math.isfinite(c12.num(m.get(k))):
            return k
    return None


def poly_volume(m: dict) -> float:
    k = poly_volume_key(m)
    return math.nan if k is None else c12.num(m.get(k))


def verify_source(*, pins: dict | None = None, repo_root: Path | None = None) -> dict:
    """The study code is read from the repo and must match ``CV_SOURCE_PINS`` byte for byte (script and ``cross_venue.py``); ``Refused`` otherwise."""
    from . import (
        h5_seal,  # noqa: PLC0415
        provenance,  # noqa: PLC0415
    )

    root = Path(repo_root) if repo_root is not None else provenance.REPO_ROOT
    out = {}
    for rel, want in (pins if pins is not None else CV_SOURCE_PINS).items():
        p = root / rel
        if not p.is_file():
            raise Refused(f"X study source {rel} missing; refusing")
        got = h5_seal.sha256_file(p)
        if got != want:
            raise Refused(f"X study source {rel} sha256 {got} != pinned {want}; refusing to execute it")
        out[rel] = got
    return out


# =====================================================================================================================================================
# The C1 set
# =====================================================================================================================================================


@dataclass
class XPair:
    pair_id: str
    event: str
    month: str
    cat: str
    t: np.ndarray  # grid times (10-minute grid)
    ok: np.ndarray  # usable step (both prices inside [3%, 97%]); a feature
    gap: object  # the raw gap k - p (nan where unusable); read ONLY through ``gap_of`` (never by the census)
    fresh: np.ndarray  # both venues' points aged <= 10 min at the step
    t_res: float  # the earlier actual resolution (window end)
    end_pm: float  # scheduled Polymarket end (nan if unknown)
    k_close: float  # Kalshi scheduled close (nan if unknown)
    vol: float = math.nan
    p: object = field(default=None, repr=False)
    k: object = field(default=None, repr=False)

    @property
    def edit(self) -> bool:
        return bool(math.isfinite(self.end_pm) and math.isfinite(self.k_close) and abs(self.end_pm - self.k_close) > EDIT_FLAG_S)

    @property
    def delta(self) -> float:
        return self.end_pm - self.t_res


def gap_of(pair: XPair) -> np.ndarray:
    """The raw gap ``g = p_K - p_PM`` on usable steps (nan elsewhere). The ONLY accessor of the gap values: census paths never call it."""
    return np.asarray(pair.gap, float)


def _age_fresh(pts: np.ndarray, kc: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Both venues' points aged <= 10 min at each grid step. Polymarket's point is known from stamp + 600 s, so its age is measured from when it becomes usable
    (``t - stamp - POINT_LAG_S <= FRESH_MAX_AGE_S``, i.e. a stamp in ``[t - 1200, t - 600]``; amendment A7); Kalshi's age is ``t - stamp``."""
    out = np.zeros(len(t), bool)
    if not len(pts) or not len(t):
        return out
    pt = np.asarray(pts[:, 0], float)
    ip = cv.asof_index(pt, t, cv.POINT_LAG_S, cv.MAX_AGE_PM_S)
    kt, _km, _ks = cv.k_mid_series(kc)
    if not len(kt):
        return out
    ik = cv.asof_index(kt, t, 0.0, cv.MAX_AGE_K_S)
    age_p = np.where(ip >= 0, t - pt[np.clip(ip, 0, None)] - cv.POINT_LAG_S, np.inf)
    age_k = np.where(ik >= 0, t - kt[np.clip(ik, 0, None)], np.inf)
    return (age_p <= FRESH_MAX_AGE_S) & (age_k <= FRESH_MAX_AGE_S)


def load_c1(root: Path, *, expected: dict | None = None, pins: dict | None = None, series_pin: dict | None = None, verify: bool = True, script: Path | None = None,
            source_pins: dict | bool | None = None) -> dict:
    """The audited C1 set with horizons: ``run_cross_venue.load_pair_series(POINT_LAG_S)`` minus ``audit_sets(...)['rule']``; the universes ``audit_sets`` reads are replaced by their
    streamed restrictions to the matched ids (same rows, no 1.5 GB ``json.load``). Returns ``{"pairs", "report"}`` and asserts the declared counts when ``expected`` is given."""
    from . import provenance  # noqa: PLC0415

    root = x_root(root)
    inputs = verify_inputs(root, pins=pins, series_pin=series_pin) if verify else {}
    source = {} if source_pins is False else verify_source(pins=source_pins if isinstance(source_pins, dict) else None)  # False: tests with a fixture script only
    spec = importlib.util.spec_from_file_location("run_cross_venue_cb12", Path(script) if script else provenance.REPO_ROOT / CV_SCRIPT_REL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.ROOT = root
    rows = json.loads((root / "matches.json").read_text())
    tickers, ids = {r["k_ticker"] for r in rows}, {str(r["p_market_id"]) for r in rows}
    kal, pol = restricted_universes(root, tickers, ids)
    mod.load_universes = lambda: (kal, pol)
    pairs, kept = mod.load_pair_series(cv.POINT_LAG_S)
    rule = mod.audit_sets(pairs, kept)["rule"]
    pb = {str(m[POLY_ID_KEY]): m for m in pol}
    vol_keys = Counter(poly_volume_key(m) or "none" for m in pb.values())
    vol_like = Counter(k for m in pb.values() for k in m if "vol" in str(k).lower())
    kb = {m["ticker"]: m for m in kal}
    out: list[XPair] = []
    for ps, row in zip(pairs, kept, strict=True):
        if row["k_ticker"] in rule:
            continue
        z = np.load(root / "series" / f"{row['k_ticker']}.npz")
        t = np.asarray(ps.g["t"], float)
        t_res = float(z["win"][1])
        if len(t):
            refuse_step_time(float(t.max()))
        refuse_step_time(t_res)
        pm = pb.get(str(row["p_market_id"]), {})
        end_pm = cv._epoch(pm.get(POLY_END_KEY))
        k_close = cv._epoch((kb.get(row["k_ticker"]) or {}).get(KALSHI_CLOSE_KEY))
        ok = np.asarray(ps.ok, bool)
        gap = np.where(ok, np.asarray(ps.g["k"], float) - np.asarray(ps.g["p"], float), np.nan)
        out.append(XPair(ps.pair_id, str(ps.cluster), datetime.fromtimestamp(t_res, UTC).strftime("%Y-%m"), str(ps.cat), t, ok, gap,
                         _age_fresh(np.asarray(z["ps"], float).reshape(-1, 2), np.asarray(z["kc"], float), t), t_res, end_pm, k_close, poly_volume(pm),
                         np.asarray(ps.g["p"], float), np.asarray(ps.g["k"], float)))
    rep = {"pairs": len(out), "events": len({p.event for p in out}), "steps": int(sum(int(p.ok.sum()) for p in out)), "audit_rule_drops": len(rule), "matched_rows": len(rows),
           "inputs_sha256": inputs, "source_sha256": source, "volume_key_matched": dict(vol_keys), "volume_keys_declared": list(POLY_VOLUME_KEYS),
           "volume_like_keys_in_rows": dict(vol_like), "matched_poly_rows": len(pb), "end_pm_missing": sum(1 for p in out if not math.isfinite(p.end_pm)), "calls": list(CV_CALLS)}
    if expected is not None:
        got = {k: rep[k] for k in ("pairs", "events", "steps")}
        if got != {k: expected[k] for k in got}:
            raise C1ReproductionError(f"C1 reproduction failed: {got} != {expected}")
    return {"pairs": out, "report": rep}


# =====================================================================================================================================================
# Horizons and bins
# =====================================================================================================================================================


def bins_of(tau) -> np.ndarray:
    """0 short (tau <= 3 d, including a step after the scheduled end), 1 mid, 2 long (tau > 30 d); -1 where tau is undefined."""
    tau = np.asarray(tau, float)
    b = np.where(tau <= BIN_SHORT_S, 0, np.where(tau > BIN_LONG_S, 2, 1))
    return np.where(np.isfinite(tau), b, -1)


def tercile_of(vols: np.ndarray) -> np.ndarray:
    """0, 1, 2 by the 1/3 and 2/3 quantiles of the available volumes; -1 where the volume is unknown (a look-ahead stratum, disclosed)."""
    v = np.asarray(vols, float)
    ok = np.isfinite(v)
    if ok.sum() < 3:
        return np.full(len(v), -1)
    q1, q2 = np.quantile(v[ok], [1 / 3, 2 / 3])
    return np.where(~ok, -1, np.where(v <= q1, 0, np.where(v <= q2, 1, 2)))


# =====================================================================================================================================================
# Census (counts only): usable-step masks, horizons, categories. Never the gap, rho or a half-life.
# =====================================================================================================================================================


def census_x(pairs: list[XPair], report: dict | None = None) -> dict:
    tau_pairs, fresh_pairs = [], []
    n_undef = n_past = n_total = 0
    for p in pairs:
        c = p.ok[:-1] & p.ok[1:]
        idx = np.nonzero(c)[0]
        fresh_pairs.append(np.asarray(p.fresh, bool)[idx] & np.asarray(p.fresh, bool)[idx + 1])
        tau = p.end_pm - p.t[idx] if math.isfinite(p.end_pm) else np.full(len(idx), np.nan)
        n_total += len(idx)
        n_undef += int((~np.isfinite(tau)).sum())
        n_past += int((tau <= 0).sum())
        tau_pairs.append(bins_of(tau))
    terc = tercile_of(np.array([p.vol for p in pairs]))
    by_bin: dict = {}
    for bi, name in enumerate(BINS):
        ps = [i for i, b in enumerate(tau_pairs) if (b == bi).any()]
        steps = int(sum(int((b == bi).sum()) for b in tau_pairs))
        events = {pairs[i].event for i in ps}
        months = {pairs[i].month for i in ps}
        fresh = int(sum(int(((b == bi) & f).sum()) for b, f in zip(tau_pairs, fresh_pairs, strict=True)))  # PM point usable (stamp + 600 s <= t) and <= 10 min past usability, i.e. stamp in [t - 1200, t - 600], K <= 10 min old (A7)
        by_bin[name] = {"pairs": len(ps), "events": len(events), "months": len(months), "step_pairs": steps, "fresh_step_pairs": fresh,
                        "by_category": dict(Counter(pairs[i].cat for i in ps)), "by_volume_tercile": dict(Counter(int(terc[i]) for i in ps))}
    gx = {n: bool(by_bin[n]["pairs"] >= GX_MIN["pairs"] and by_bin[n]["events"] >= GX_MIN["events"] and by_bin[n]["step_pairs"] >= GX_MIN["steps"]) for n in ("short", "long")}
    gx_pass = bool(gx["short"] and gx["long"])
    avail = (n_total - n_undef) / n_total if n_total else 0.0
    out = {"version": "cb12-census-X-v1", "counts_only": True, "label": LABEL_X, "pairs": len(pairs), "events": len({p.event for p in pairs}), "usable_steps": int(sum(int(p.ok.sum()) for p in pairs)),
           "usable_consecutive_step_pairs": n_total, "steps_tau_undefined": n_undef, "steps_after_scheduled_end": n_past, "by_horizon_bin": by_bin,
           "edit_flag_pairs": sum(1 for p in pairs if p.edit), "edit_flag_unknown_pairs": sum(1 for p in pairs if not (math.isfinite(p.end_pm) and math.isfinite(p.k_close))),
           "volume_unknown_pairs": int((terc < 0).sum()), "category_counts": dict(Counter(p.cat for p in pairs)),
           "G_by_way": {"event": len({p.event for p in pairs}), "resolution_month": len({p.month for p in pairs})},
           "G_by_way_and_bin": {n: {"event": by_bin[n]["events"], "resolution_month": by_bin[n]["months"]} for n in BINS},
           "availability_share": avail, "volume_key_matched": (report or {}).get("volume_key_matched"), "volume_keys_declared": (report or {}).get("volume_keys_declared"),
           "volume_like_keys_in_rows": (report or {}).get("volume_like_keys_in_rows"), "GX": {"min": GX_MIN, "short": gx["short"], "long": gx["long"], "pass": gx_pass}, "c1_reproduction": report or {}}
    if not gx_pass:
        out["label_X"] = "not testable (horizon range)"
    elif avail < AVAIL_MIN:
        out["label_X"] = "not testable (availability)"
    else:
        out["label_X"] = None
    return out


def source_failure_census(reason: str) -> dict:
    """The counted outcome of a smoke or C1 failure: no computation, ``label_X`` = "not testable (source)" (the screen then writes the p = 1 trial line)."""
    return {"version": "cb12-census-X-v1", "counts_only": True, "label": LABEL_X, "label_X": SOURCE_LABEL, "source_failure": reason, "GX": {"min": GX_MIN, "pass": False}}


# =====================================================================================================================================================
# Statistic
# =====================================================================================================================================================


def causal_demean(t: np.ndarray, g: np.ndarray) -> np.ndarray:
    """g minus the mean of the usable gaps in the 3 days strictly before the step (needs ``CAUSAL_MIN_OBS`` past observations, else nan)."""
    ok = np.isfinite(g)
    out = np.full(len(g), np.nan)
    if not ok.any():
        return out
    tt, gg = t[ok], g[ok]
    cs = np.concatenate([[0.0], np.cumsum(gg)])
    lo = np.searchsorted(tt, tt - CAUSAL_WINDOW_S, side="left")
    hi = np.arange(len(tt))
    cnt = hi - lo
    mean = np.where(cnt >= CAUSAL_MIN_OBS, (cs[hi] - cs[lo]) / np.maximum(cnt, 1), np.nan)
    out[ok] = gg - mean
    return out


@dataclass
class Tab:
    a: np.ndarray  # demeaned gap at the first step
    b: np.ndarray  # demeaned gap at the next step
    pi: np.ndarray  # pair index
    rem: np.ndarray  # t_res - t at the first step
    absg: np.ndarray  # |raw gap| at the first step
    fresh: np.ndarray
    tt: np.ndarray
    delta: np.ndarray  # per pair: endDate_PM - t_res (nan if unknown)
    cat: list[str]
    event_idx: np.ndarray
    month_idx: np.ndarray
    edit: np.ndarray
    vol: np.ndarray
    n_pairs: int

    @property
    def tau(self) -> np.ndarray:
        return self.rem + self.delta[self.pi]


def make_tab(pairs: list[XPair], *, demean: str = "whole") -> Tab:
    """Consecutive usable step pairs (both steps usable) with the pair-demeaned gap (whole window, or the rolling 3-day past mean for the causal variant)."""
    A, B, PI, REM, AG, FR, TT = [], [], [], [], [], [], []
    for i, p in enumerate(pairs):
        g = gap_of(p)
        ok = np.isfinite(g)
        if len(g) < 2 or not ok.any():
            continue
        gt = g - np.nanmean(g) if demean == "whole" else causal_demean(np.asarray(p.t, float), g)
        idx = np.nonzero(ok[:-1] & ok[1:] & np.isfinite(gt[:-1]) & np.isfinite(gt[1:]))[0]
        if not len(idx):
            continue
        A.append(gt[idx])
        B.append(gt[idx + 1])
        PI.append(np.full(len(idx), i))
        REM.append(p.t_res - np.asarray(p.t, float)[idx])
        AG.append(np.abs(g[idx]))
        FR.append(np.asarray(p.fresh, bool)[idx] & np.asarray(p.fresh, bool)[idx + 1])
        TT.append(np.asarray(p.t, float)[idx])
    cat = [p.cat.strip().lower() for p in pairs]
    ev = {e: j for j, e in enumerate(sorted({p.event for p in pairs}))}
    mo = {m: j for j, m in enumerate(sorted({p.month for p in pairs}))}

    def cat_(xs, dt=float):
        return np.concatenate(xs) if xs else np.zeros(0, dt)

    return Tab(cat_(A), cat_(B), cat_(PI, int), cat_(REM), cat_(AG), cat_(FR, bool), cat_(TT), np.array([p.delta for p in pairs], float), cat,
               np.array([ev[p.event] for p in pairs], int), np.array([mo[p.month] for p in pairs], int), np.array([p.edit for p in pairs], bool),
               np.array([p.vol for p in pairs], float), len(pairs))


def cluster_sums(tab: Tab, mask: np.ndarray, clus: np.ndarray, G: int, tau: np.ndarray | None = None) -> np.ndarray:
    """(G, 3 bins, 3) sufficient statistics ``[sum a^2, sum a b, n]`` per cluster and horizon bin."""
    tau = tab.tau if tau is None else tau
    b = bins_of(tau)
    use = mask & (b >= 0)
    key = clus[tab.pi[use]] * 3 + b[use]
    a, bb = tab.a[use], tab.b[use]
    S = np.zeros((G, 3, 3))
    S[:, :, 0] = np.bincount(key, a * a, minlength=G * 3).reshape(G, 3)
    S[:, :, 1] = np.bincount(key, a * bb, minlength=G * 3).reshape(G, 3)
    S[:, :, 2] = np.bincount(key, minlength=G * 3).reshape(G, 3)
    return S


def hl_of(saa, sab, *, cap: bool = True):
    """Half-life in minutes of the pooled AR(1) ``rho = Sab / Saa``: ``10 ln 2 / (-ln rho)``; ``rho >= 1`` -> the 7-day cap (infinity reported by ``rho_report``), ``rho <= 0`` -> 0
    (the gap closes within one step; ambiguity: the design is silent), no data -> nan."""
    saa, sab = np.asarray(saa, float), np.asarray(sab, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = sab / saa
        r = np.clip(rho, 1e-12, 1 - 1e-12)
        hl = GRID_MIN * math.log(2) / (-np.log(r))
    hl = np.where(rho >= 1, HL_CAP_MIN, np.where(rho <= 0, 0.0, np.minimum(hl, HL_CAP_MIN) if cap else hl))
    return np.where(~np.isfinite(rho) | (saa <= 0), np.nan, hl)


def contrast_of(S) -> np.ndarray:
    """``HL_long - HL_short`` from (…, 3, 3) sums."""
    S = np.asarray(S, float)
    hl = hl_of(S[..., 0], S[..., 1])
    return hl[..., 2] - hl[..., 0]


def point(tab: Tab, mask: np.ndarray, tau: np.ndarray | None = None) -> dict:
    S = cluster_sums(tab, mask, np.zeros(tab.n_pairs, int), 1, tau)[0]
    hl = hl_of(S[:, 0], S[:, 1])
    rho = np.where(S[:, 0] > 0, S[:, 1] / np.where(S[:, 0] > 0, S[:, 0], 1.0), np.nan)
    return {"hl_min": dict(zip(BINS, [None if not np.isfinite(x) else float(x) for x in hl], strict=True)), "rho": dict(zip(BINS, [None if not np.isfinite(x) else float(x) for x in rho], strict=True)),
            "hl_infinite": {n: bool(np.isfinite(r) and r >= 1) for n, r in zip(BINS, rho, strict=True)}, "n_step_pairs": dict(zip(BINS, [int(x) for x in S[:, 2]], strict=True)),
            "contrast": float(hl[2] - hl[0]) if np.isfinite(hl[2]) and np.isfinite(hl[0]) else math.nan}


def _boot_weights(G: int, n_boot: int, seed: int, cache: dict | None) -> np.ndarray:
    if cache is not None and G in cache:
        return cache[G]
    W = np.random.default_rng(seed).multinomial(G, np.full(G, 1.0 / G), size=n_boot).astype(float)
    if cache is not None:
        cache[G] = W
    return W


def way_inference(S: np.ndarray, *, n_boot: int = c12.N_BOOT, seed: int = c12.SEED_BOOT, wcache: dict | None = None) -> dict:
    """One cluster way. G >= 30: 2,000-draw cluster bootstrap (one-sided p that the contrast is <= 0). 15 <= G < 30 (CB10 small-G rule): leave-one-cluster-out pseudo-values with
    CR2 + Webb wild bootstrap. G < 15: the way leaves the max and the leave-one-cluster-out sign rule binds."""
    S = S[S[:, :, 2].sum(1) > 0]
    G = len(S)
    tot = S.sum(0)
    est = float(contrast_of(tot)) if G else math.nan
    out = {"G": int(G), "contrast": est}
    if G < 2 or not math.isfinite(est):
        return {**out, "p": 1.0, "method": "no_data", "in_max": False, "testable": False}
    loo = np.array([contrast_of(tot - S[i]) for i in range(G)], float)
    out["loo_sign_holds"] = bool(np.isfinite(loo).all() and (loo > 0).all())
    if G >= c12.MIN_CLUSTERS:
        W = _boot_weights(G, n_boot, seed, wcache)
        c = contrast_of(np.tensordot(W, S, axes=(1, 0)))
        return {**out, "p": c12.one_sided_boot_p(c), "method": "cluster_bootstrap", "n_boot": n_boot, "in_max": True, "testable": True}
    if G >= 15 and np.isfinite(loo).all():
        from . import cb2_weather as w  # noqa: PLC0415

        pseudo = G * est - (G - 1) * loo
        r = w.small_g_pvalue(pseudo, np.arange(G).astype(str), sign=1, n_wild=c12.N_WILD, seed=seed)
        return {**out, "p": float(r["p"]), "method": r["method"] + "_on_jackknife_pseudo_values", "in_max": True, "testable": bool(r["testable"])}
    return {**out, "p": 1.0, "method": "G<15: leaves the max; leave-one-cluster-out sign rule binds", "in_max": False, "testable": True}


def evaluate(tab: Tab, mask: np.ndarray, *, n_boot: int = c12.N_BOOT, seed: int = c12.SEED_BOOT, tau: np.ndarray | None = None, wcache: dict | None = None) -> dict:
    """Point estimates by bin, the contrast and p = max over the event and resolution-month ways (small-G rule per way)."""
    ways = {"event": (tab.event_idx, int(tab.event_idx.max()) + 1 if tab.n_pairs else 0), "resolution_month": (tab.month_idx, int(tab.month_idx.max()) + 1 if tab.n_pairs else 0)}
    res = {"point": point(tab, mask, tau), "ways": {}}
    ps = []
    for name, (clus, G) in ways.items():
        if G == 0:
            continue
        r = way_inference(cluster_sums(tab, mask, clus, G, tau), n_boot=n_boot, seed=seed, wcache=wcache)
        res["ways"][name] = r
        if r["in_max"] and r["testable"]:
            ps.append(r["p"])
    n_units = min(res["point"]["n_step_pairs"]["short"], res["point"]["n_step_pairs"]["long"])
    res["testable"] = bool(ps and n_units >= c12.MIN_UNITS and max((w["G"] for w in res["ways"].values()), default=0) >= c12.MIN_CLUSTERS and np.isfinite(res["point"]["contrast"]))
    res["p"] = float(max(ps)) if res["testable"] else 1.0
    res["loo_sign_rule_holds"] = all(w.get("loo_sign_holds", False) for w in res["ways"].values() if not w["in_max"]) if res["ways"] else False
    return res


def _sign_ok(tab: Tab, mask: np.ndarray) -> bool:
    c = point(tab, mask)["contrast"]
    return bool(math.isfinite(c) and c > 0)


def horizon_placebo(tab: Tab, mask: np.ndarray, *, n_draws: int = c12.PLACEBO_DRAWS, seed: int = c12.PLACEBO_SEEDS["X1_horizon_offset"], n_boot: int = c12.N_BOOT) -> dict:
    """Binding horizon-offset placebo: ``delta = endDate_PM - t_res`` is permuted across pairs within category and ``tau = (t_res - t) + delta_perm`` is recomputed; the advance rate
    (p < 0.01 under the same inference; floors off) must be <= 1.5%. If scheduled horizon and life-cycle are collinear in C1 this placebo advances and X1 is 'not identifiable'."""
    rng = np.random.default_rng(seed)
    valid = np.isfinite(tab.delta)
    cats: dict[str, list[int]] = {}
    for i in np.nonzero(valid)[0]:
        cats.setdefault(tab.cat[i], []).append(int(i))
    wcache: dict = {}
    ps = []
    for _ in range(n_draws):
        dp = tab.delta.copy()
        for idx in cats.values():
            ia = np.array(idx)
            dp[ia] = tab.delta[ia[rng.permutation(len(ia))]]
        r = evaluate(tab, mask, n_boot=n_boot, tau=tab.rem + dp[tab.pi], wcache=wcache)
        ps.append(r["p"] if r["testable"] else None)
    return {**c12.placebo_advance_rate(ps), "note": "X1 horizon-offset placebo (delta permuted within category)", "seed": seed}


def top5_cluster_drop(tab: Tab, mask: np.ndarray, clus: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """Drop the 5 clusters (of one way) whose removal lowers the contrast most (largest positive influence; leave-one-cluster-out); returns the keep mask over steps."""
    G = int(clus.max()) + 1
    S = cluster_sums(tab, mask, clus, G)
    tot = S.sum(0)
    loo = np.array([contrast_of(tot - S[i]) if S[i, :, 2].sum() > 0 else np.inf for i in range(G)], float)
    loo = np.where(np.isfinite(loo), loo, np.inf)
    drop = [int(i) for i in np.argsort(loo, kind="stable")[: c12.TOP_DROP] if np.isfinite(loo[i])]
    keep_pair = ~np.isin(clus, drop)
    return mask & keep_pair[tab.pi], drop


def top5_event_drop(tab: Tab, mask: np.ndarray, n_boot: int) -> tuple[np.ndarray, list[int]]:
    return top5_cluster_drop(tab, mask, tab.event_idx)


def top5_month_drop(tab: Tab, mask: np.ndarray, n_boot: int) -> tuple[np.ndarray, list[int]]:
    return top5_cluster_drop(tab, mask, tab.month_idx)


def x1_test(pairs: list[XPair], *, n_boot: int = c12.N_BOOT, n_draws: int = c12.PLACEBO_DRAWS, placebo: bool = True) -> dict:
    tab = make_tab(pairs)
    allm = np.ones(len(tab.a), bool)
    tau_def = np.isfinite(tab.tau)
    avail = float(tau_def.mean()) if len(tau_def) else 0.0
    base = evaluate(tab, allm, n_boot=n_boot)
    pt = base["point"]
    contrast = pt["contrast"]
    res: dict = {"test": "X1", "label": LABEL_X, "n": int(min(pt["n_step_pairs"]["short"], pt["n_step_pairs"]["long"])), "hl_min": pt["hl_min"], "rho": pt["rho"], "hl_infinite": pt["hl_infinite"],
                 "n_step_pairs": pt["n_step_pairs"], "contrast_min": contrast, "effect": contrast, "floor_min": X1_FLOOR_MIN, "floor_ok": bool(math.isfinite(contrast) and contrast >= X1_FLOOR_MIN),
                 "p": base["p"], "testable": base["testable"], "ways": base["ways"], "availability_share": avail}
    if avail < AVAIL_MIN:
        return {**res, "p": 1.0, "testable": False, "advance": False, "verdict": "not testable (availability)"}
    if not base["testable"]:
        return {**res, "p": 1.0, "advance": False, "verdict": "not testable (units / clusters)"}
    rob: dict = {}
    # strata (both with >= 10 pairs in both bins) - the stricter reading: both strata must qualify and hold
    strata = {}
    for s in STRATA:
        pm = np.array([c == s for c in tab.cat], bool)
        sm = allm & pm[tab.pi]
        bins = bins_of(tab.tau)
        npairs = [len({int(i) for i in tab.pi[sm & (bins == b)]}) for b in (0, 2)]
        strata[s] = {"pairs_short": npairs[0], "pairs_long": npairs[1], "qualifies": bool(min(npairs) >= STRATUM_MIN_PAIRS), "sign": _sign_ok(tab, sm) if min(npairs) >= STRATUM_MIN_PAIRS else None}
    rob["strata_sign"] = bool(all(v["qualifies"] and v["sign"] for v in strata.values()))
    # volume terciles (>= 2 of 3 hold)
    terc = tercile_of(tab.vol)
    holds = 0
    for k in range(3):
        sm = allm & (terc == k)[tab.pi]
        holds += int(_sign_ok(tab, sm)) if sm.any() else 0
    rob["volume_terciles_hold"] = bool(holds >= TERCILES_MIN_HOLD)
    tab_c = make_tab(pairs, demean="causal")
    pc = point(tab_c, np.ones(len(tab_c.a), bool))
    rob["causal_demeaning"] = bool(math.isfinite(pc["contrast"]) and pc["contrast"] > 0 and pc["contrast"] >= 0.5 * contrast)
    rob["large_gap_3c"] = _sign_ok(tab, allm & (tab.absg >= LARGE_GAP))
    rob["edit_flag_excluded"] = _sign_ok(tab, allm & ~tab.edit[tab.pi])
    rob["fresh_steps"] = _sign_ok(tab, allm & tab.fresh)
    km, dropped = top5_event_drop(tab, allm, n_boot)
    t5 = evaluate(tab, km, n_boot=n_boot)
    rob["top5_event_drop"] = bool(t5["testable"] and t5["p"] < c12.GATE_P and math.isfinite(t5["point"]["contrast"]) and t5["point"]["contrast"] >= X1_FLOOR_MIN)
    kmm, dropped_m = top5_month_drop(tab, allm, n_boot)  # section 2.6 (ii): the p threshold and the floor hold without the top 5 clusters of EACH way
    t5m = evaluate(tab, kmm, n_boot=n_boot)
    rob["top5_resolution_month_drop"] = bool(t5m["testable"] and t5m["p"] < c12.GATE_P and math.isfinite(t5m["point"]["contrast"]) and t5m["point"]["contrast"] >= X1_FLOOR_MIN)
    lo, hi = float(tab.tt.min()), float(tab.tt.max())
    edges = [lo, lo + (hi - lo) / 3, lo + 2 * (hi - lo) / 3, hi + 1]
    rob["thirds_sign"] = bool(all(_sign_ok(tab, allm & (tab.tt >= edges[k]) & (tab.tt < edges[k + 1])) for k in range(3)))
    rob["loo_sign_rule_for_small_G_ways"] = bool(base["loo_sign_rule_holds"])
    plc = horizon_placebo(tab, allm, n_draws=n_draws, n_boot=n_boot) if placebo else None
    rob_ok = all(v is True for v in rob.values())
    res.update(robustness=rob, robustness_ok=rob_ok, strata=strata, top5_dropped_event_idx=dropped, top5_dropped_month_idx=dropped_m, placebo=plc, reported=x_reported(pairs, tab, strata))
    ok = bool(res["p"] < c12.GATE_P and res["floor_ok"] and rob_ok and (plc is None or plc["holds"]))
    res.update(stage1_pass=ok, early_holm_ok=c12.early_stage1_ok(res["p"]), advance=bool(ok and c12.early_stage1_ok(res["p"])), holm_pending=bool(ok and not c12.early_stage1_ok(res["p"])))
    if plc is not None and not plc["holds"]:
        res["verdict"] = "not identifiable (horizon-offset placebo advanced)"
    else:
        res["verdict"] = "advance (early Holm)" if res["advance"] else ("pending the full step-down (p in [0.005, 0.01))" if res["holm_pending"] else "no advance")
    return res


def x_reported(pairs: list[XPair], tab: Tab, strata: dict) -> dict:
    """Uncounted: ``HL_mid``, lag-1..12 cross-correlations of the 10-minute changes by horizon bin (K->P and P->K), the gap size by bin and category, and the Polymarket adjustment share
    ``sum|dP| / (sum|dP| + sum|dK|)`` by bin."""
    m = np.ones(len(tab.a), bool)
    bins = bins_of(tab.tau)
    gap_size = {}
    for bi, name in enumerate(BINS):
        sel = m & (bins == bi)
        gap_size[name] = float(tab.absg[sel].mean()) if sel.any() else None
    by_cat: dict[str, dict] = {}
    for c in sorted(set(tab.cat)):
        pm = np.array([x == c for x in tab.cat])
        by_cat[c] = {name: (float(tab.absg[m & (bins == bi) & pm[tab.pi]].mean()) if (m & (bins == bi) & pm[tab.pi]).any() else None) for bi, name in enumerate(BINS)}
    xc: dict = {n: {} for n in BINS}
    adj = {n: [0.0, 0.0] for n in BINS}
    pieces = {n: {L: ([], [], [], []) for L in range(1, 13)} for n in BINS}
    for p in pairs:
        if p.p is None or p.k is None or not math.isfinite(p.end_pm):
            continue
        ok = np.asarray(p.ok, bool)
        dp, dk = cv.lagged_diff(np.asarray(p.p, float), ok, 1), cv.lagged_diff(np.asarray(p.k, float), ok, 1)
        tau = p.end_pm - np.asarray(p.t, float)
        b = bins_of(tau)
        for bi, name in enumerate(BINS):
            sel = (b == bi) & np.isfinite(dp) & np.isfinite(dk)
            adj[name][0] += float(np.abs(dp[sel]).sum())
            adj[name][1] += float(np.abs(dk[sel]).sum())
            for L in range(1, 13):
                n = len(dp) - L
                if n <= 0:
                    continue
                s2 = (b[:n] == bi) & np.isfinite(dk[:n]) & np.isfinite(dp[L:]) & np.isfinite(dp[:n]) & np.isfinite(dk[L:])
                pieces[name][L][0].append(dk[:n][s2])
                pieces[name][L][1].append(dp[L:][s2])
                pieces[name][L][2].append(dp[:n][s2])
                pieces[name][L][3].append(dk[L:][s2])
    for name in BINS:
        for L in range(1, 13):
            a, b_, c, d = (np.concatenate(x) if x else np.zeros(0) for x in pieces[name][L])
            xc[name][str(L)] = {"K_to_P": float(np.corrcoef(a, b_)[0, 1]) if len(a) > 30 and a.std() > 0 and b_.std() > 0 else None,
                                "P_to_K": float(np.corrcoef(c, d)[0, 1]) if len(c) > 30 and c.std() > 0 and d.std() > 0 else None}
    return {"HL_mid_min": point(tab, m)["hl_min"]["mid"], "gap_size_by_bin": gap_size, "gap_size_by_bin_and_category": by_cat, "lag_xcorr_by_bin": xc,
            "pm_adjustment_share_by_bin": {n: (v[0] / (v[0] + v[1]) if v[0] + v[1] > 0 else None) for n, v in adj.items()}, "strata_detail": strata}


def not_run_result(label: str) -> dict:
    return {"test": "X1", "p": 1.0, "testable": False, "advance": False, "verdict": label, "label": LABEL_X, "effect": None, "n": 0}


def screen_x(pairs: list[XPair], census: dict, *, n_boot: int = c12.N_BOOT, n_draws: int = c12.PLACEBO_DRAWS) -> dict:
    """q0255. Refuses to compute unless the census passed GX (else the counted ``not testable`` line, p = 1)."""
    lab = census.get("label_X")
    if lab:
        return {"X1": not_run_result(lab), "label": LABEL_X, "census_label": lab}
    return {"X1": x1_test(pairs, n_boot=n_boot, n_draws=n_draws), "label": LABEL_X, "census_label": None}


# =====================================================================================================================================================
# Smoke (family checks) and declared
# =====================================================================================================================================================


def smoke_offline(ctx: dict) -> dict:
    """Guard fixtures (cross_venue_live, a step at ``T12_X_END``, the mtime guard), the pinned input sha256s and the exact C1 reproduction (316 / 183 / 517,616)."""
    import os  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    res = []
    for fn in (lambda: x_root(Path("x/cross_venue_live/series")), lambda: refuse_step_time(c12.T12_X_END_EPOCH), lambda: refuse_step_time(c12.T12_X_END_EPOCH + 600.0)):
        try:
            fn()
            res.append(False)
        except Refused:
            res.append(True)
    try:
        refuse_step_time(c12.T12_X_END_EPOCH - 600.0)
        res.append(True)
    except Refused:
        res.append(False)
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "late.json"
        f.write_text("[]")
        os.utime(f, (c12.X_MTIME_MAX_EPOCH + 1, c12.X_MTIME_MAX_EPOCH + 1))
        try:
            refuse_mtime(f)
            res.append(False)
        except Refused:
            res.append(True)
    out = {"guards_fixture_X": {"pass": bool(all(res)), "refusals": res}}
    root = ctx.get("cv_root")
    if not root:
        out["x_inputs_pinned"] = {"pass": False, "note": "no cross_venue root given"}
        out["x_c1_reproduction"] = {"pass": False, "note": "no cross_venue root given"}
        return out
    try:
        inputs = verify_inputs(Path(root))
        out["x_inputs_pinned"] = {"pass": True, "files": len(inputs) - 1, "series_listing_sha256": inputs["series"]["listing_sha256"]}
    except Refused as exc:
        out["x_inputs_pinned"] = {"pass": False, "error": str(exc)[:200]}
        out["x_c1_reproduction"] = {"pass": False, "note": "inputs not verified"}
        return out
    try:
        rep = load_c1(Path(root), expected=C1_EXPECTED, verify=False)["report"]
        out["x_c1_reproduction"] = {"pass": True, **{k: rep[k] for k in ("pairs", "events", "steps", "audit_rule_drops", "end_pm_missing")}}
    except (Refused, AssertionError) as exc:
        out["x_c1_reproduction"] = {"pass": False, "error": str(exc)[:200]}
    return out


def smoke_online(lim, ctx: dict) -> dict:
    return {}


def declared() -> dict:
    return {"label": LABEL_X, "bins_s": {"short_max": BIN_SHORT_S, "long_min": BIN_LONG_S}, "estimator": "pooled AR(1) of the pair-demeaned gap on consecutive usable steps by horizon bin of the first step; HL = 10 min ln2 / (-ln rho); "
            "rho >= 1 -> inf (reported) and the 7 d cap in the contrast and bootstrap", "x1": {"contrast": "HL_long - HL_short", "floor_min": X1_FLOOR_MIN, "one_sided": ">0",
            "ways": ["polymarket event", "calendar month of the earlier resolution"], "inference": "2000-draw cluster bootstrap, seed 1212; CB10 small-G rule per way"},
            "placebo": {"name": "horizon-offset", "draws": c12.PLACEBO_DRAWS, "seed": c12.PLACEBO_SEEDS["X1_horizon_offset"], "judged_on": "p < 0.01 under the same inference (floors off)"},
            "robustness": ["sports and elections strata (>= 10 pairs per bin each)", "volume terciles (>= 2 of 3)", "causal demeaning (3-day past mean) keeps sign and >= half", "|g| >= 3c", "edit-flag excluded",
                           "fresh steps (both points <= 10 min)", "top-5 events", "top-5 resolution months", "sign in each third by step date", "leave-one-cluster-out sign for any way with G < 15"],
            "gate_GX": GX_MIN, "c1_expected": C1_EXPECTED, "horizon_source": "poly_markets.json 'end' (scheduled), streamed", "inputs": sorted(X_PINS), "study_source_pins": CV_SOURCE_PINS, "series_pin": X_SERIES_PIN,
            "guards": "cross_venue_live refused; steps at or after T12_X_end refused; input mtime >= 2026-10-13 refused", "reads": "no outcome, no wallet, no side"}
