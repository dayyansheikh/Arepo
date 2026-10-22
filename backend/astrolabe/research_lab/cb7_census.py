# ruff: noqa: E501
"""CB7 pre-freeze census (q0147; docs/research_lab/CREATIVE_BATCH_7.md section 2.7). COUNTS ONLY.

No beta, net, mark-out, YES rate or log loss is computed. Every reader is field-restricted:
- S (``h8_text``) reads ``sample.csv.gz``, ``text_features.csv.gz``, ``origin_prices.csv.gz``, ``drops.csv.gz`` and the small count
  reports; it never opens ``outcomes_guarded.csv.gz``, ``origin_prints.csv.gz`` or ``frame.csv.gz`` and never uses the description text.
- G (``h8_geo``) reads ``sample.csv.gz``, ``frame.csv.gz`` (tag / topic counts), ``origin_prices.csv.gz``, ``capped.csv.gz``,
  ``drops.csv.gz`` and the count reports; never the outcomes or the prints. ``h_geo`` reads best bid / best ask (and the fee category) of
  complete captures in ``[2026-10-22T00:00Z, 2026-10-25T00:00Z)`` only.
- X reads ``creative_batch7/xv_prints`` (pair key, ``ts``, side), the pair list and the stored Kalshi candles / Polymarket history points of
  ``cross_venue/series/*.npz`` (prices as the usability rule needs them; no later price is ever compared with an earlier one).
The committed seals ``h8_text``, ``h8_geo`` and ``h8_tail`` are checked by sha256 against the host copies first; any mismatch refuses.
The result is write-once JSON; a key naming an outcome, a mark or a point estimate is refused (``assert_counts_only``).
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import statistics
import time
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb6_tail as c6
from . import cb7_common as cm
from . import cb7_geo as cg
from . import cb7_xv as xv
from . import h5_seal
from . import history_backfill as hb

Refused, NotNow = cm.Refused, cm.NotNow

CENSUS_VERSION = "cb7-census-v1"
RESULT_NAME = "census.json"
FAMILIES = ("S", "G", "X")
SEALED_RUNS = (cm.TEXT_RUN_ID, cm.GEO_RUN_ID, "h8_tail")
JOB = "q0147_cb7_census"
H_GEO_WINDOW = ("2026-10-22T00:00:00Z", "2026-10-25T00:00:00Z")
H_GEO_MID = (0.02, 0.10)

# gates (CB7 section 2.7; never revised from the census)
GS = {"units": 3000, "event_week_clusters": 1000, "series_event_clusters": 300, "within_cell_sd_c": 0.5}
GG = {"units": 300, "event_clusters": 100, "theme_clusters": 15, "sum_m": 15.0}
GX = {"s_prints": 2000, "skip_windows_with_s": 300, "event_clusters": 30, "utc_dates": 30}
SD_G_WITHIN_CELL_ASSUMED = 0.39  # the design's assumption (CB7-S MDE); the census reads no outcome so it cannot measure it
Z_MDE = 2.33 + 0.84
FORBIDDEN_KEY_PARTS = ("outcome", "beta", "markout", "mark_out", "yes_rate", "log_loss", "logloss", "payout", "pnl", "uma_", "target",
                       "net_per", "y_mean", "realised", "realized")

S_FILES = ("sample.csv.gz", "text_features.csv.gz", "origin_prices.csv.gz", "drops.csv.gz", "frame_report.json", "key_drops.json",
           "cut_points.json", "drops_report.json", "manifest.json")
G_FILES = ("sample.csv.gz", "frame.csv.gz", "origin_prices.csv.gz", "capped.csv.gz", "drops.csv.gz", "frame_report.json", "key_drops.json",
           "drops_report.json", "manifest.json")
S_SAMPLE_COLS = ("market_id", "event_id", "event_ids", "neg_risk_market_id", "series_ids", "end_epoch", "close_epoch", "closed_after_cap",
                 "status", "stratum", "desc_len", "clarified", "c", "m1", "m2", "m3", "m4", "m5", "m6", "m7")
G_SAMPLE_COLS = ("market_id", "event_id", "event_ids", "neg_risk_market_id", "question", "event_title", "slug", "fee_category", "end_epoch",
                 "close_epoch", "closed_after_cap", "market_tag_ids", "event_tag_ids")


# ---- guards ---------------------------------------------------------------------------------------------------------------------


def assert_counts_only(obj, path: str = "") -> None:
    """Refuse a result that carries a key naming an outcome, a mark, a point estimate or a target (a unit test also plants one)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if any(p in lk for p in FORBIDDEN_KEY_PARTS):
                raise Refused(f"census result key {path}/{k} names a forbidden quantity (outcome / mark / estimate); counts only")
            assert_counts_only(v, f"{path}/{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj[:50]):
            assert_counts_only(v, f"{path}[{i}]")


def read_cols(path: Path, wanted: tuple[str, ...], *, required: tuple[str, ...] = ()) -> Iterator[dict]:
    """Stream a gzip CSV extracting ONLY the ``wanted`` columns (everything else in the row is dropped at once)."""
    csv.field_size_limit(10**9)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, [])
        miss = [c for c in required if c not in head]
        if miss:
            raise Refused(f"{path.name}: required columns {miss} missing")
        idx = {c: head.index(c) for c in wanted if c in head}
        for row in rd:
            yield {c: row[i] for c, i in idx.items()}


def _f(v, default: float = math.nan) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _ci(v) -> int:
    return int(_f(v, 0.0))


def iso_week(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%G-W%V")


# ---- seals ------------------------------------------------------------------------------------------------------------------------


def verify_seal_copies(root: Path, seals_dir: Path) -> dict:
    """The committed ``<run>_SEAL.json`` of h8_text, h8_geo and h8_tail must be byte-identical (sha256) to the host's ``<run>/SEAL.json``.
    A run with no committed seal is accepted only as an explicit terminal record (committed ``<run>_NOT_RUN.json`` or the host's
    ``NOT_RUN_DEADLINE.json`` / unverified marker); otherwise, or on any mismatch or missing host copy, :class:`Refused`. h8_tail is
    only hashed: none of its data is opened. Returns ``{run: {"state": "sealed"|"not_run_deadline"|"disjointness_unverified"|"source_unverified", "sha256": ...}}``; the three
    terminal states stay distinct (unverified = "not testable", not "not run")."""
    root, seals_dir = Path(root), Path(seals_dir)
    out: dict[str, dict] = {}
    for run in SEALED_RUNS:
        committed = h5_seal.committed_seal_path(run, seals_dir)
        host = root / run / h5_seal.SEAL_NAME
        if committed.exists():
            if not host.is_file():
                raise Refused(f"{run}: committed seal {committed.name} exists but the host copy {host} is missing; refusing")
            a, b = h5_seal.sha256_file(committed), h5_seal.sha256_file(host)
            if a != b:
                raise Refused(f"{run}: committed seal sha256 {a} != host seal sha256 {b}; refusing")
            out[run] = {"state": "sealed", "sha256": a}
            continue
        rdir = root / run
        state = None
        if (seals_dir / f"{run}_NOT_RUN.json").exists() or (rdir / cm.NOT_RUN_FILE).exists():
            state = cm.NOT_RUN_TOKEN
        elif (rdir / cm.UNVERIFIED_FILE).exists():
            state = cm.UNVERIFIED_TOKEN
        elif (rdir / cm.SOURCE_UNVERIFIED_FILE).exists():
            state = cm.SOURCE_UNVERIFIED_TOKEN
        if run == "h8_tail" or state is None:
            raise Refused(f"{run}: no committed seal copy {committed.name} and no terminal (not-run) record; refusing")
        out[run] = {"state": state, "sha256": None}
    return out


def sealed_paths(root: Path, run: str, files: tuple[str, ...], seals_dir: Path) -> dict[str, Path]:
    """Full seal verification (listing hash against the committed copy), one ACCESS_LOG record, and only the whitelisted files."""
    rdir = Path(root) / run
    got = h5_seal.read_sealed(rdir, JOB, list(files), h5_seal.committed_seal_path(run, seals_dir))
    return {p.name: p for p in got}


# ---- shared statistics (pure) ------------------------------------------------------------------------------------------------------


def event_keys(rows: list[dict]) -> dict[str, str]:
    """``market_id -> event key`` (Gamma event id, neg-risk members merged: CB6's ``event_key_split`` key)."""
    return {m: k for m, (k, _) in c6.event_key_split(rows).items()}


def icc_oneway(y: list[float], g: list[str]) -> float:
    """ANOVA intraclass correlation of ``y`` within clusters ``g`` (clamped to [0, 1]); ``nan`` with fewer than two clusters or no
    within-cluster degrees of freedom."""
    n = len(y)
    by: dict[str, list[float]] = {}
    for v, k in zip(y, g, strict=True):
        by.setdefault(k, []).append(v)
    k = len(by)
    if k < 2 or n <= k:
        return math.nan
    mean = sum(y) / n
    n0 = (n - sum(len(v) ** 2 for v in by.values()) / n) / (k - 1)
    msb = sum(len(v) * (sum(v) / len(v) - mean) ** 2 for v in by.values()) / (k - 1)
    msw = sum(sum((x - sum(v) / len(v)) ** 2 for x in v) for v in by.values()) / (n - k)
    den = msb + (n0 - 1) * msw
    if den <= 0:
        return math.nan
    return min(1.0, max(0.0, (msb - msw) / den))


def cell_demean(values: list[float], cells: list[str]) -> list[float]:
    sums: dict[str, list[float]] = {}
    for v, c in zip(values, cells, strict=True):
        s = sums.setdefault(c, [0.0, 0.0])
        s[0] += v
        s[1] += 1
    return [v - sums[c][0] / sums[c][1] for v, c in zip(values, cells, strict=True)]


def deff_text_only(c_dm: list[float], clusters: dict[str, list[str]]) -> dict:
    """``deff_S = 1 + (m_bar - 1) * rho_C`` per clustering way (``m_bar`` = units per cluster, ``rho_C`` = intraclass correlation of the
    cell-demeaned C within clusters); the larger way is binding. The outcome's within-cluster correlation is taken as 1 (an upper bound):
    no outcome is read. ``None`` when a way cannot be computed (an unknown never counts as met)."""
    ways = {}
    for name, g in clusters.items():
        rho = icc_oneway(c_dm, g)
        k = len(set(g))
        mbar = len(g) / k if k else math.nan
        ways[name] = {"clusters": k, "m_bar": mbar, "rho_c": None if math.isnan(rho) else rho,
                      "deff": None if math.isnan(rho) else 1.0 + (mbar - 1.0) * rho}
    vals = [w["deff"] for w in ways.values() if w["deff"] is not None]
    return {"ways": ways, "deff_s": max(vals) if len(vals) == len(ways) and vals else None}


def _jsonable(o):
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    return o


def cell_band(m: float) -> str | None:
    for lo, hi in cm.TEXT_CELL_BANDS:
        if lo <= m < hi or (hi == cm.TEXT_BAND[1] and m == hi):
            return f"[{lo:.2f},{hi:.2f}{']' if hi == cm.TEXT_BAND[1] else ')'}"
    return None


# ---- S ----------------------------------------------------------------------------------------------------------------------------


def census_s(root: Path, seals_dir: Path) -> dict:
    paths = sealed_paths(root, cm.TEXT_RUN_ID, S_FILES, seals_dir)
    manifest = json.loads(paths["manifest.json"].read_text())
    frame_rep = json.loads(paths["frame_report.json"].read_text())
    key_drops = json.loads(paths["key_drops.json"].read_text())
    cuts = json.loads(paths["cut_points.json"].read_text())
    drops_rep = json.loads(paths["drops_report.json"].read_text())
    dropped = {r["market_id"]: r["block"] for r in read_cols(paths["drops.csv.gz"], ("market_id", "block"), required=("market_id", "block"))}
    topics = {r["market_id"]: r["cb1_topic"] for r in read_cols(paths["text_features.csv.gz"], ("market_id", "cb1_topic"), required=("market_id", "cb1_topic"))}
    prices = {r["market_id"]: r for r in read_cols(paths["origin_prices.csv.gz"], ("market_id", "eligible", "m", "price_status", "staleness_s", "full_page"),
                                                    required=("market_id", "eligible", "m"))}
    rows = [r for r in read_cols(paths["sample.csv.gz"], S_SAMPLE_COLS, required=("market_id", "end_epoch", "c", "clarified")) if r["market_id"] not in dropped]
    ekey = event_keys(rows)
    by_topic_sample: Counter = Counter()
    clar_by_topic: dict[str, list[int]] = {}
    status_counts: Counter = Counter()
    c_dist: dict[str, Counter] = {}
    marker_n = [0] * 7
    long_desc = 0
    closed_end_lt_1h = closed_lt_end7 = closed_known = 0
    elig_by_cell: Counter = Counter()
    elig_units: list[dict] = []
    n_elig = n_elig_all_topics = closed_before_t7 = closed_before_t7_s1 = 0
    for r in rows:
        tp = topics.get(r["market_id"], "")
        by_topic_sample[tp] += 1
        clar_by_topic.setdefault(tp, []).append(_ci(r["clarified"]))
        status_counts[str(r.get("status", ""))] += 1
        c_dist.setdefault(tp, Counter())[_ci(r["c"])] += 1
        for i in range(7):
            marker_n[i] += _ci(r.get(f"m{i + 1}"))
        long_desc += int(_ci(r.get("desc_len")) > cm.DESCRIPTION_CHARS)
        end, close = _f(r["end_epoch"]), _f(r.get("close_epoch"))
        if math.isfinite(close) and math.isfinite(end):
            closed_known += 1
            closed_end_lt_1h += int(abs(close - end) < 3600)
            closed_lt_end7 += int(close < end - 7 * cm.DAY)
        pr = prices.get(r["market_id"])
        if pr is None or _ci(pr["eligible"]) != 1:
            continue
        n_elig_all_topics += 1
        t7 = end - cm.TEXT_ORIGIN_DAYS * cm.DAY
        early = int(math.isfinite(close) and close < t7)
        closed_before_t7 += early
        band = cell_band(_f(pr["m"]))
        if band is not None:
            elig_by_cell[f"{tp}|{band}"] += 1
        if tp != "sports" and _ci(r["clarified"]) == 0 and band is not None:
            n_elig += 1
            closed_before_t7_s1 += early
            elig_units.append({"market_id": r["market_id"], "topic": tp, "cell": f"{tp}|{band}", "c": float(_ci(r["c"])), "end": end,
                               "series": next((s for s in str(r.get("series_ids", "")).split(";") if s), "") or ekey[r["market_id"]]})
    # S1 population statistics
    c_dm = cell_demean([u["c"] for u in elig_units], [u["cell"] for u in elig_units]) if elig_units else []
    n_u = len(elig_units)
    sd_n = math.sqrt(sum(x * x for x in c_dm) / n_u) if n_u else math.nan
    n_cells = len({u["cell"] for u in elig_units})
    sd_df = math.sqrt(sum(x * x for x in c_dm) / (n_u - n_cells)) if n_u > n_cells else math.nan
    clusters = {"event_x_resolution_week": [f"{ekey[u['market_id']]}|{iso_week(u['end'])}" for u in elig_units],
                "series_or_event": [u["series"] for u in elig_units]}
    de = deff_text_only(c_dm, clusters) if n_u else {"ways": {}, "deff_s": None}
    se = mde = None
    if n_u and de["deff_s"] is not None and sd_n and not math.isnan(sd_n) and sd_n > 0:
        se = SD_G_WITHIN_CELL_ASSUMED / (sd_n * math.sqrt(n_u)) * math.sqrt(de["deff_s"])
        mde = Z_MDE * se
    ms = [m for m in (_f(prices[u["market_id"]]["m"]) for u in elig_units) if math.isfinite(m)]
    sd_g_secondary = math.sqrt(sum(m * (1 - m) for m in ms) / len(ms)) if ms else None
    ew = de["ways"].get("event_x_resolution_week", {}).get("clusters", 0)
    se_c = de["ways"].get("series_or_event", {}).get("clusters", 0)
    gate = {"units": {"value": n_u, "need": GS["units"], "met": n_u >= GS["units"]},
            "event_week_clusters": {"value": ew, "need": GS["event_week_clusters"], "met": ew >= GS["event_week_clusters"]},
            "series_event_clusters": {"value": se_c, "need": GS["series_event_clusters"], "met": se_c >= GS["series_event_clusters"]},
            "within_cell_sd_c": {"value": None if math.isnan(sd_n) else sd_n, "need": GS["within_cell_sd_c"], "met": bool(not math.isnan(sd_n) and sd_n >= GS["within_cell_sd_c"])}}
    gate["GS"] = all(v["met"] for v in gate.values())
    n_rows = len(rows)
    return {
        "status": "ok", "seal_listing_sha256": json.loads(h5_seal.committed_seal_path(cm.TEXT_RUN_ID, seals_dir).read_text()).get("listing_sha256"),
        "t_fetch": manifest.get("request_clock_now"), "rules_sha256": manifest.get("rules_sha256"),
        "frame": {k: frame_rep.get(k) for k in ("frame_rows", "filter_dropped", "exclusion_id_dropped", "exclusion_key_dropped", "kept_by_key_stage",
                                                "descriptions_longer_than_stored", "clarified_in_frame", "closed_after_cap_in_frame", "windows",
                                                "windows_dropped_capped", "rows_in_dropped_windows", "windows_failed", "days", "raw", "n_sample",
                                                "sampled_descriptions_longer_than_stored", "sample")},
        "exclusion_report": {k: (manifest.get("exclusion_report") or {}).get(k) for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys")},
        "key_drops": key_drops, "seal_drops": drops_rep.get("counts") or (drops_rep.get("drops") or {}).get("counts"),
        "seal_drop_sources": drops_rep.get("sources"), "n_sample_after_seal_drops": n_rows,
        "sample_by_topic": dict(sorted(by_topic_sample.items())),
        "clarification_marked_share_by_topic": {t: sum(v) / len(v) for t, v in sorted(clar_by_topic.items())},
        "status_at_fetch": dict(sorted(status_counts.items())),
        "censored_share": (status_counts.get("active", 0) / n_rows) if n_rows else None,
        "origin_requests_failed_final": (manifest.get("counts") or {}).get("print_request_failed"),
        "eligible_units_all_topics": n_elig_all_topics, "eligible_by_topic_x_band": dict(sorted(elig_by_cell.items())),
        "s1_population": {"definition": "eligible, kept after seal drops, not sports, not clarification-marked", "units": n_u,
                          "cells": n_cells},
        "c_distribution_by_topic": {t: {str(k): v for k, v in sorted(c.items())} for t, c in sorted(c_dist.items())},
        "cut_points_frozen": cuts.get("by_topic"),
        "marker_prevalence": {f"m{i + 1}": (marker_n[i] / n_rows if n_rows else None) for i in range(7)},
        "within_cell_sd_c": {"n_denominator": None if math.isnan(sd_n) else sd_n, "df_corrected": None if math.isnan(sd_df) else sd_df,
                             "binding": "n_denominator (the smaller; conservative)"},
        "closed_time": {"rows_with_closed_time": closed_known, "abs_diff_end_lt_1h": closed_end_lt_1h, "before_end_minus_7d": closed_lt_end7,
                        "eligible_units_closed_before_t7": closed_before_t7, "s1_units_closed_before_t7": closed_before_t7_s1},
        "descriptions_longer_than_4000": {"count": long_desc, "share": (long_desc / n_rows) if n_rows else None},
        "text_only_design_effect": de, "assumed_sd_g_within_cell": SD_G_WITHIN_CELL_ASSUMED, "secondary_sqrt_mean_m_one_minus_m_s1": sd_g_secondary,
        "s1_se_per_marker_price_units": se, "s1_mde_per_marker_cents": None if mde is None else 100 * mde,
        "gate_GS": gate,
    }


# ---- G ----------------------------------------------------------------------------------------------------------------------------


def _topic(r: dict) -> str:
    from . import history_topics  # noqa: PLC0415

    return history_topics.topic_of(r.get("question", ""), r.get("event_title", ""), r.get("slug", ""), r.get("fee_category", ""))


def census_g(root: Path, seals_dir: Path, h_geo: dict) -> dict:
    paths = sealed_paths(root, cm.GEO_RUN_ID, G_FILES, seals_dir)
    manifest = json.loads(paths["manifest.json"].read_text())
    frame_rep = json.loads(paths["frame_report.json"].read_text())
    key_drops = json.loads(paths["key_drops.json"].read_text())
    drops_rep = json.loads(paths["drops_report.json"].read_text())
    dropped = {r["market_id"]: r["block"] for r in read_cols(paths["drops.csv.gz"], ("market_id", "block"), required=("market_id", "block"))}
    capped_events = Counter(r["event_key"] for r in read_cols(paths["capped.csv.gz"], ("market_id", "event_key")))
    frame_n = frame_tag_only = 0
    for r in read_cols(paths["frame.csv.gz"], ("question", "event_title", "slug", "fee_category")):
        frame_n += 1
        frame_tag_only += int(_topic(r) != "geopolitics")
    rows = [r for r in read_cols(paths["sample.csv.gz"], G_SAMPLE_COLS, required=("market_id", "end_epoch")) if r["market_id"] not in dropped]
    by_id = {r["market_id"]: r for r in rows}
    ekey = event_keys(rows)
    sample_tag_only = sum(1 for r in rows if _topic(r) != "geopolitics")
    units = []
    for p in read_cols(paths["origin_prices.csv.gz"], ("market_id", "k", "origin_ts", "m", "eligible", "price_status"), required=("market_id", "k", "eligible")):
        r = by_id.get(p["market_id"])
        if r is None or _ci(p["eligible"]) != 1:
            continue
        close, t = _f(r.get("close_epoch")), _f(p["origin_ts"])
        topic_ok = _topic(r) == "geopolitics"
        theme = cg.theme_of(r.get("question", ""), r.get("event_title", ""))
        units.append({"k": _ci(p["k"]), "m": _f(p["m"]), "market_id": p["market_id"], "event": ekey[p["market_id"]], "week": iso_week(_f(r["end_epoch"])),
                      "theme": theme or f"own:{ekey[p['market_id']]}", "named_theme": theme, "early": int(math.isfinite(close) and math.isfinite(t) and close < t),
                      "tag_and_topic": topic_ok})
    by_k: dict[str, dict] = {}
    for k in cm.GEO_ORIGIN_DAYS:
        us = [u for u in units if u["k"] == k]
        by_k[str(k)] = {"eligible_units": len(us), "closed_time_before_origin": sum(u["early"] for u in us)}
    n = len(units)
    ev = len({u["event"] for u in units})
    ew = len({(u["event"], u["week"]) for u in units})
    themes = len({u["theme"] for u in units})
    named = sorted({u["named_theme"] for u in units if u["named_theme"]})
    sum_m = sum(u["m"] for u in units if math.isfinite(u["m"]))
    tt = [u for u in units if u["tag_and_topic"]]
    gate = {"units": {"value": n, "need": GG["units"], "met": n >= GG["units"]},
            "event_clusters": {"value": ev, "need": GG["event_clusters"], "met": ev >= GG["event_clusters"]},
            "theme_clusters": {"value": themes, "need": GG["theme_clusters"], "met": themes >= GG["theme_clusters"]},
            "sum_m": {"value": sum_m, "need": GG["sum_m"], "met": sum_m >= GG["sum_m"]}}
    hg = h_geo.get("h_geo_binding")
    gate["h_geo_measured"] = {"value": hg, "met": hg is not None}
    gate["GG"] = all(gate[k]["met"] for k in ("units", "event_clusters", "theme_clusters", "sum_m"))
    return {
        "status": "ok", "seal_listing_sha256": json.loads(h5_seal.committed_seal_path(cm.GEO_RUN_ID, seals_dir).read_text()).get("listing_sha256"),
        "t_fetch": manifest.get("request_clock_now"),
        "frame": {k: frame_rep.get(k) for k in ("frame_rows", "filter_dropped", "exclusion_id_dropped", "exclusion_key_dropped", "kept_before_cap", "capped_out",
                                                "closed_after_cap_in_frame", "windows", "excluded_capped_at_one_day", "splits", "rows_in_excluded_windows",
                                                "windows_failed", "months", "n_markets", "n_markets_without_origin", "n_origins")},
        "exclusion_by_reason": {**(frame_rep.get("filter_dropped") or {}), "exclusion_id": frame_rep.get("exclusion_id_dropped"),
                                "exclusion_key": frame_rep.get("exclusion_key_dropped"), "event_cap": frame_rep.get("capped_out"),
                                "seal_drops": drops_rep.get("counts") or (drops_rep.get("drops") or {}).get("counts")},
        "key_drops": key_drops, "event_cap": {"capped_out_markets": sum(capped_events.values()), "events_hit_by_cap": len(capped_events)},
        "n_sample_after_seal_drops": len(rows), "eligible_units": n, "eligible_by_origin": by_k,
        "event_clusters": ev, "event_week_clusters": ew, "theme_clusters": themes, "named_themes_with_unit": named,
        "expected_yes_sum_m": sum_m,
        "tag_only_share": {"frame": {"tagged_markets": frame_n, "topic_not_geopolitics": frame_tag_only, "share": (frame_tag_only / frame_n) if frame_n else None},
                           "sample": {"markets": len(rows), "topic_not_geopolitics": sample_tag_only, "share": (sample_tag_only / len(rows)) if rows else None}},
        "tag_and_topic_subset": {"eligible_units": len(tt), "event_clusters": len({u["event"] for u in tt}), "sum_m": sum(u["m"] for u in tt if math.isfinite(u["m"]))},
        "closed_time_before_origin_total": sum(u["early"] for u in units), "origin_requests_failed_final": (manifest.get("counts") or {}).get("print_request_failed"),
        "h_geo": h_geo, "gate_GG": gate,
    }


# ---- h_geo ------------------------------------------------------------------------------------------------------------------------


_CAPTURE_RE = re.compile(r"^(\d{8}T\d{6}Z)_[0-9a-f]+$")


def measure_h_geo(snap_root: Path, *, window: tuple[str, str] = H_GEO_WINDOW, mid_band: tuple[float, float] = H_GEO_MID,
                  wall_clock: Callable[[], float] = time.time) -> dict:
    """Median half-spread ``(ask - bid) / 2`` of geopolitics markets (``fee_category == "geopolitics"``, or the topic rule when the capture rows carry a
    question) with a two-sided quote and YES mid in ``mid_band``, over the complete captures whose start lies in ``window``. Reads only
    ``market_id``, ``best_bid``, ``best_ask`` (rows.csv.gz) and ``fee_category`` (rows_ext.csv.gz): spreads, no outcome. First row per market per
    capture. Raises :class:`NotNow` until the window has closed. ``h_geo_binding`` is the larger of the pooled and the per-market median."""
    lo, hi = cm._ep(window[0]), cm._ep(window[1])
    if wall_clock() < hi:
        raise NotNow(f"h_geo window {window[0]}..{window[1]} is not closed yet")
    root = Path(snap_root)
    cm.refuse_path(root)
    if root.name != "snapshots":
        raise Refused(f"h_geo reads only a snapshots/ directory, not {root}")
    obs: list[float] = []
    per_market: dict[str, list[float]] = {}
    n_cap = n_side_skipped = n_geo_ids = 0
    for d in sorted(root.iterdir() if root.exists() else []):
        m = _CAPTURE_RE.match(d.name)
        if not m or not d.is_dir():
            continue
        start = datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
        if not (lo <= start < hi):
            continue
        try:
            man = json.loads((d / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        if str(man.get("state")) != "complete":
            continue
        if str(man.get("sidecar_status")) != "complete":
            n_side_skipped += 1
            continue
        geo_ids = {r["market_id"] for r in read_cols(d / "rows_ext.csv.gz", ("market_id", "fee_category")) if r.get("fee_category") == "geopolitics"}
        n_cap += 1
        n_geo_ids += len(geo_ids)
        seen: set[str] = set()
        for r in read_cols(d / "rows.csv.gz", ("market_id", "best_bid", "best_ask")):
            mid_id = r["market_id"]
            if mid_id in seen:
                continue
            seen.add(mid_id)
            if mid_id not in geo_ids:
                continue
            bid, ask = _f(r.get("best_bid")), _f(r.get("best_ask"))
            if not (math.isfinite(bid) and math.isfinite(ask)) or not (0.0 < bid < ask < 1.0):
                continue
            if not (mid_band[0] <= (bid + ask) / 2 <= mid_band[1]):
                continue
            h = (ask - bid) / 2
            obs.append(h)
            per_market.setdefault(mid_id, []).append(h)
    if n_cap == 0:
        raise Refused(f"h_geo: no complete capture with a complete sidecar in {window[0]}..{window[1]} under {root} ({n_side_skipped} skipped for sidecar); check the host")
    if n_geo_ids == 0:
        raise Refused("h_geo: no market with fee_category == 'geopolitics' in any complete capture: misconfiguration (fee category string or sidecar); refusing")
    res = {"window": list(window), "complete_captures": n_cap, "captures_skipped_sidecar_not_complete": n_side_skipped, "observations": len(obs), "markets": len(per_market),
           "geopolitics_rule": "rows_ext fee_category == 'geopolitics' (capture rows carry no question)"}
    if not obs:
        return {**res, "median_half_spread_pooled": None, "median_half_spread_by_market": None, "h_geo_binding": None, "status": "unavailable"}
    pooled = statistics.median(obs)
    by_mkt = statistics.median(statistics.median(v) for v in per_market.values())
    return {**res, "median_half_spread_pooled": pooled, "median_half_spread_by_market": by_mkt, "h_geo_binding": max(pooled, by_mkt), "status": "ok"}


# ---- X ----------------------------------------------------------------------------------------------------------------------------


def require_xv_complete(xv_dir: Path) -> dict:
    cm.refuse_path(xv_dir)
    mp = Path(xv_dir) / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if not (man.get("complete") is True and man.get("status") == xv.XV_COMPLETE):
        raise NotNow(f"xv_prints is not {xv.XV_COMPLETE}; run q0146 first")
    return man


def census_x(xv_dir: Path, cv_root: Path) -> dict:
    cm.refuse_path(cv_root)
    man = require_xv_complete(xv_dir)
    legs = {r["pair_key"]: r for r in cm.read_csv_gz(Path(xv_dir) / "legs.csv.gz")}
    days = Counter()
    days_by_group: dict[str, Counter] = {"nonsports": Counter(), "sports": Counter()}
    for r in read_cols(Path(xv_dir) / "days.csv.gz", ("pair_key", "status")):
        days[r["status"]] += 1
        lg = legs.get(r["pair_key"], {})
        days_by_group["sports" if str(lg.get("k_cat", "")).strip().lower() == "sports" else "nonsports"][r["status"]] += 1
    tot = {"all": Counter(), "nonsports": Counter(), "sports": Counter()}
    moves = {"all": Counter(), "nonsports": Counter(), "sports": Counter()}
    clusters = {g: {"event": set(), "date": set(), "window": set()} for g in tot}
    prints_per_pair: dict[str, int] = {}
    grid_total = grid_gap = 0
    for key, leg in sorted(legs.items()):
        grp = "sports" if str(leg.get("k_cat", "")).strip().lower() == "sports" else "nonsports"
        z = np.load(Path(cv_root) / "series" / f"{key}.npz")
        km = xv.KalshiMid(z["kc"])
        gt, gg = km.minutes_without_candle()
        grid_total += gt
        grid_gap += gg
        up, down = xv.move_events(km)
        for g in ("all", grp):
            moves[g]["up"] += len(up)
            moves[g]["down"] += len(down)
        pf = Path(xv_dir) / "prints" / f"{key}.csv.gz"
        pr = [(float(r["ts"]), _ci(r["side"])) for r in read_cols(pf, ("ts", "side"), required=("ts", "side"))] if pf.exists() else []
        prints_per_pair[key] = len(pr)
        ps = np.asarray(z["ps"], float).reshape(-1, 2)
        if len(ps):
            ps = ps[np.argsort(ps[:, 0], kind="stable")]
        res = xv.classify_prints(pr, up, down, km, ps[:, 0] if len(ps) else np.empty(0), ps[:, 1] if len(ps) else np.empty(0))
        for g in ("all", grp):
            for k in ("n_prints", "excluded_both_states", "excluded_unusable", "S", "Sp", "N", "S_mark_available"):
                tot[g][k] += res[k]
            clusters[g]["event"].update({leg["p_event_id"]} if res["S"] else set())
            clusters[g]["date"].update(datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d") for t in res["s_ts"])
            clusters[g]["window"].update((key, d, w) for d, w in res["s_window"])
    ns = tot["nonsports"]
    gate = {"s_prints": {"value": ns["S"], "need": GX["s_prints"], "met": ns["S"] >= GX["s_prints"]},
            "skip_windows_with_s": {"value": len(clusters["nonsports"]["window"]), "need": GX["skip_windows_with_s"],
                                    "met": len(clusters["nonsports"]["window"]) >= GX["skip_windows_with_s"]},
            "event_clusters": {"value": len(clusters["nonsports"]["event"]), "need": GX["event_clusters"], "met": len(clusters["nonsports"]["event"]) >= GX["event_clusters"]},
            "utc_dates": {"value": len(clusters["nonsports"]["date"]), "need": GX["utc_dates"], "met": len(clusters["nonsports"]["date"]) >= GX["utc_dates"]}}
    gate["GX"] = all(v["met"] for v in gate.values())
    return {
        "status": "ok", "xv_manifest_status": man.get("status"), "pairs": len(legs), "pairs_nonsports": sum(1 for v in legs.values() if str(v.get("k_cat", "")).strip().lower() != "sports"),
        "pair_day_items": sum(days.values()), "days_by_status": dict(sorted(days.items())), "days_by_status_by_group": {g: dict(sorted(c.items())) for g, c in days_by_group.items()},
        "kalshi_move_grid": {"minute_ends": grid_total, "minutes_without_a_candle": grid_gap}, "capped_days": days.get("capped", 0),
        "legs_without_condition_id": man.get("legs_without_condition_id"),
        "prints_per_pair": {"min": min(prints_per_pair.values()) if prints_per_pair else None, "median": statistics.median(prints_per_pair.values()) if prints_per_pair else None,
                            "max": max(prints_per_pair.values()) if prints_per_pair else None, "total": sum(prints_per_pair.values())},
        "kalshi_move_events": {g: dict(c) for g, c in moves.items()},
        "print_classes": {g: dict(c) for g, c in tot.items()},
        "s_clusters": {g: {"events": len(v["event"]), "utc_dates": len(v["date"]), "skip_windows": len(v["window"])} for g, v in clusters.items()},
        "gate_GX": gate,
    }


# ---- the census ---------------------------------------------------------------------------------------------------------------------


def _terminal(state: str) -> dict:
    """A family whose run ended without a seal: ``not_run_deadline`` is "not run"; the two unverified states are "not testable"."""
    return {"status": state, "testable": False} if state != cm.NOT_RUN_TOKEN else {"status": state}


def census_declaration() -> dict:
    """Item 4 (CB7 section 5.2 declaration guard): sha256 of the CB7-X definitions block of ``cb7_xv`` (source of every definition function and
    constant), of ``cb7_census.py`` and of the gate / constant dicts. Written into ``census.json``; re-checked at the CB7 freeze and q0150."""
    import hashlib  # noqa: PLC0415
    import inspect  # noqa: PLC0415

    xv_src = "\n".join(inspect.getsource(f) for f in (xv.valid_mid, xv.KalshiMid, xv.move_events, xv.in_skip, xv.skip_windows, xv.poly_point_ok,
                                                      xv.mark_available, xv.classify_prints, xv.map_trade_row))
    consts = {"GS": GS, "GG": GG, "GX": GX, "Z_MDE": Z_MDE, "SD_G": SD_G_WITHIN_CELL_ASSUMED, "H_GEO_WINDOW": list(H_GEO_WINDOW), "H_GEO_MID": list(H_GEO_MID),
              "xv": {k: getattr(xv, k) for k in ("K_MAX_AGE_S", "K_MAX_SPREAD", "MID_RANGE", "MOVE_LOOKBACK_S", "MOVE_THRESHOLD", "SKIP_LAG_S", "SKIP_LEN_S",
                                                  "POLY_MARK_MIN_AGE_S", "POLY_MARK_MAX_AGE_S", "DAY_PAGES", "PAGE_LIMIT")}}
    sha = lambda x: hashlib.sha256(x.encode()).hexdigest()  # noqa: E731
    return {"cb7_xv_definitions_sha256": sha(xv_src), "cb7_census_source_sha256": sha(Path(__file__).read_text()),
            "constants_sha256": sha(json.dumps(consts, sort_keys=True, default=list)), "constants": _jsonable(consts)}


def run_census(families: list[str], *, root: Path, seals_dir: Path, cb7_dir: Path, cv_root: Path, snapshot_root: Path,
               rules_path: Path | None = None, require_committed: bool = True, wall_clock: Callable[[], float] = time.time,
               trials_path: Path | None = None, out: Path | None = None, pins=None) -> dict:
    """Verify the seal copies (before anything is read), run the requested families and write ``census.json`` once. A family whose run is a
    recorded ``not_run`` terminal state is recorded as such and the others proceed."""
    fams = [f.strip().upper() for f in families if f.strip()]
    bad = [f for f in fams if f not in FAMILIES]
    if bad or not fams:
        raise Refused(f"unknown census family {bad or fams!r}; declared: {FAMILIES}")
    root, seals_dir, cb7_dir = Path(root), Path(seals_dir), Path(cb7_dir)
    for p in (root, cb7_dir, Path(cv_root)):
        cm.refuse_path(p)
    out = Path(out) if out else cb7_dir / RESULT_NAME
    if out.resolve().parent != cb7_dir.resolve():
        raise Refused(f"--out {out} is outside {cb7_dir}; the census is written only there")
    if not (out.name.startswith("census") and out.name.endswith(".json")):
        raise Refused(f"--out {out.name} must be named census*.json, so the write-once check sees it")
    if out.exists() or (cb7_dir.exists() and any(cb7_dir.glob("census*.json"))):
        raise Refused(f"a census result already exists in {cb7_dir}; the census is write-once")
    if "X" in fams:  # readiness before any S / G read, so a tempfail leaves no ACCESS_LOG entry
        require_xv_complete(cb7_dir / xv.XV_RUN_ID)
    seals = verify_seal_copies(root, seals_dir)
    rules_sha = cm.verify_rules(Path(rules_path) if rules_path else cm.RULES_FILE, require_committed=require_committed, pins=pins)
    res: dict = {"version": CENSUS_VERSION, "job": JOB, "evidence_role": hb.EVIDENCE_ROLE, "kind": "cb7_descriptive", "families": fams,
                 "rules_sha256": rules_sha, "declaration": census_declaration(), "seals": seals, "git_commit": hb._git_commit(),
                 "note": "counts only; no outcome, mark, YES rate or estimate is computed; floors, windows and thresholds are never revised from these counts"}
    h_geo: dict | None = None
    if "G" in fams and seals[cm.GEO_RUN_ID]["state"] == "sealed":
        h_geo = measure_h_geo(Path(snapshot_root), wall_clock=wall_clock)
    for fam in fams:
        if fam == "S":
            res["S"] = census_s(root, seals_dir) if seals[cm.TEXT_RUN_ID]["state"] == "sealed" else _terminal(seals[cm.TEXT_RUN_ID]["state"])
        elif fam == "G":
            res["G"] = census_g(root, seals_dir, h_geo or {}) if seals[cm.GEO_RUN_ID]["state"] == "sealed" else _terminal(seals[cm.GEO_RUN_ID]["state"])
        else:
            res["X"] = census_x(cb7_dir / xv.XV_RUN_ID, Path(cv_root))
    res = _jsonable(res)
    assert_counts_only(res)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out.open("x") as fh:
            fh.write(json.dumps(res, indent=1, sort_keys=True))
    except FileExistsError:
        raise Refused(f"{out} already exists; the census is write-once") from None
    from . import provenance  # noqa: PLC0415

    gates = {f: (res.get(f) or {}).get(f"gate_G{f}", {}) for f in fams}
    provenance.append_trial({"kind": "cb7_descriptive", "label": "EXPLORATORY", "evidence_role": hb.EVIDENCE_ROLE, "source": "creative_batch_7:census",
                             "n_tests": 0, "families": fams, "result_path": str(out), "census_sha256": h5_seal.sha256_file(out),
                             "gates": {f: g.get(f"G{f}") for f, g in gates.items() if g}, "note": "CB7 pre-freeze census, counts only"},
                            Path(trials_path) if trials_path else provenance.TRIALS_PATH)
    return res
