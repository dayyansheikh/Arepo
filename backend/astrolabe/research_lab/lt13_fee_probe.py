# ruff: noqa: E501
"""q0717, the LT13 fee-reading probe (docs/research_lab/LIVE_TESTS_13.md 1.4.3, 7.5; LT13 challenger R1 MUST 3). COUNTS ONLY, k = 0, uncounted.

Why it exists: ``population_map_ch251.fee_class`` has not changed since 0b4c103b, yet the CH261 map's widening shares imply about 12,850
fee-free unrewarded *complete units* a capture (non-sports ex-crypto, captures 2026-10-20..10-28) against CH251's 4,577 fee-free unrewarded
*open rows* a capture (2026-10-13..10-23), and the lumpiness (mean >> median) moved from CH251's fee-free cell to CH261's fee-on cell.
This probe counts, per capture, the raw sidecar fee fields under both maps' cell definitions so the shift can be attributed (a row-vs-unit
definition, the spans, a change over time in how the venue serves ``fees_enabled`` / ``fee_schedule`` / ``feeType``, or a category
reclassification). It decides nothing; LIVE_TESTS_13.md 7.5 carries the declared decision rule.

Reads per capture: ``manifest.json``, ``rows.csv.gz`` through ``population_map_ch251.read_rows`` (open active binary rows; only the
two-sided flag is kept), ``rows_ext.csv.gz`` (the named columns of ``EXT_COLS`` only) and ``ext_manifest.json`` when present (its
``ext_version``). The cell reading reuses ``population_map_ch251.fee_class`` / ``fee_parse`` and the CH240 map's ``category_of`` /
``reward_status`` unchanged, so every row lands in the same fee x reward x category cell as in both maps (a test checks this against
``population_map_ch261.read_ext``). State of capture k and capture k - 1 only (two-sidedness and the fee / category class of k - 1);
never capture k + 1. No spread or price change, no volume, no target, no outcome, no P&L.

Cells (``CELLS``): ``ch251_open_row`` = every open active binary row at k (CH251's ``ch250/rows_open_binary``); ``two_sided_k`` = those
two-sided at k; ``ch261_complete_unit`` = two-sided at k - 1 and at k with capture k - 1 within 2 h 30 min (CH261's ``ch252/units_complete``).
Raw states per row: ``fees_enabled`` (col_absent / blank / true / false / other), ``fee_schedule`` (col_absent / empty / unparseable /
no_rate_key / rate_nonnumeric / rate_zero / rate_pos, and a sha256 prefix of the verbatim text), ``taker_base_fee`` (col_absent / blank /
zero / pos / other), ``fee_type`` and ``fee_category`` verbatim (the first ``MAX_DISTINCT`` values; later ones ``<other>``), the reward
reading (``clob_rewards`` non-empty), age class (``created_at`` before 2026-03-30) and whether the row has a sidecar row at all.
Captures in the span whose ``rows.csv.gz`` is gone are counted as missing (``rows_gone``), never restored.
"""

from __future__ import annotations

import hashlib
import json
import math
import resource
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import population_map_ch251 as c251

VERSION = "lt13-fee-probe-v1"
GRID_S, GAP_MAX_S, GRID_REF_S = c240.GRID_S, c240.GAP_MAX_S, c240.GRID_REF_S
PRE_FEE_DEPLOY = c251.PRE_FEE_DEPLOY
ELIG = "nonsports_excrypto"
CELLS = ("ch251_open_row", "two_sided_k", "ch261_complete_unit")
EXT_COLS = ("market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "fees_enabled", "fee_schedule", "taker_base_fee", "created_at")
MAX_DISTINCT = 64
MAX_SCHEDULES = 200
TEXT_MAX = 80
SCHEDULE_TEXT_MAX = 240
FEES = ("fee_free", "fee_on", "unknown")
CATS = c240.CATS
# Reference spans of the two maps (CH251_MAP_2026-10-23.md, CH261_MAP_2026-10-28.md); used only to group the per-capture series.
SPANS = {
    "ch251_span": ("2026-10-13T00:00:00Z", "2026-10-23T00:00:00Z"),
    "ch261_covered": ("2026-10-20T04:00:00Z", "2026-10-28T00:00:00Z"),
    "overlap": ("2026-10-20T04:00:00Z", "2026-10-23T00:00:00Z"),
    "after_ch251": ("2026-10-23T00:00:00Z", "2026-10-28T00:00:00Z"),
}
HEADLINE = {  # name -> (cell, category, reward, fee); summed over fee_src
    "ch251_def_fee_free_unrewarded_open_rows": ("ch251_open_row", ELIG, "unrewarded", "fee_free"),
    "ch251_def_fee_on_unrewarded_open_rows": ("ch251_open_row", ELIG, "unrewarded", "fee_on"),
    "ch251_def_unknown_fee_unrewarded_open_rows": ("ch251_open_row", ELIG, "unrewarded", "unknown"),
    "two_sided_fee_free_unrewarded_rows": ("two_sided_k", ELIG, "unrewarded", "fee_free"),
    "two_sided_fee_on_unrewarded_rows": ("two_sided_k", ELIG, "unrewarded", "fee_on"),
    "ch261_def_fee_free_unrewarded_complete_units": ("ch261_complete_unit", ELIG, "unrewarded", "fee_free"),
    "ch261_def_fee_on_unrewarded_complete_units": ("ch261_complete_unit", ELIG, "unrewarded", "fee_on"),
}
NOT_READ = {
    "capture_k_plus_1": "never opened for capture k's counts: every count of capture k uses capture k and capture k - 1 only",
    "prices_and_targets": "best_bid / best_ask are read only inside population_map_ch251.read_rows to set the two-sided flag; no spread, mid or price change is kept or counted; no target, outcome, resolution or P&L",
    "volume": "volume_num and liquidity are not read from the sidecar; the rows reader's liquidity value is discarded",
}
CODE_FILES = (Path(__file__), Path(__file__).resolve().parents[2] / "scripts" / "run_lt13_fee_probe.py")
_FS_MEMO: dict = {}
_FEE_IDX = {f: i for i, f in enumerate(FEES)}
_CAT_IDX = {c: i for i, c in enumerate(CATS)}


def code_sha256() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CODE_FILES if p.exists()}


def fe_state(has_col: bool, v) -> str:
    if not has_col:
        return "col_absent"
    s = str(v if v is not None else "").strip().lower()
    if s == "":
        return "blank"
    if s in ("true", "1", "1.0", "t"):
        return "true"
    if s in ("false", "0", "0.0", "f"):
        return "false"
    return "other"


def fs_state(has_col: bool, s) -> tuple[str, str]:
    """(state, sha256 prefix of the verbatim text or '-') of a fee_schedule field."""
    if not has_col:
        return "col_absent", "-"
    s = s if isinstance(s, str) else ""
    hit = _FS_MEMO.get(s)
    if hit is not None:
        return hit
    if not s.strip():
        out = ("empty", "-")
    else:
        h = hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
        try:
            d = json.loads(s)
        except ValueError:
            d = None
            out = ("unparseable", h)
        if d is not None:
            if not isinstance(d, dict) or "rate" not in d:
                out = ("no_rate_key", h)
            else:
                try:
                    r = float(d["rate"])
                except (TypeError, ValueError):
                    r = math.nan
                out = ("rate_nonnumeric", h) if not math.isfinite(r) else ("rate_zero", h) if r <= 0 else ("rate_pos", h)
    if len(_FS_MEMO) < 10000:
        _FS_MEMO[s] = out
    return out


def tbf_state(has_col: bool, v) -> str:
    if not has_col:
        return "col_absent"
    s = str(v if v is not None else "").strip()
    if s == "":
        return "blank"
    x = c240._f(s)
    return "other" if not math.isfinite(x) or x < 0 else "zero" if x == 0 else "pos"


def age_class(created) -> str:
    ct = c240.parse_utc(created) if created else math.nan
    return "age_na" if not math.isfinite(ct) else "pre_0330" if ct < PRE_FEE_DEPLOY else "post_0330"


class _Bucket:
    """Verbatim text values up to ``MAX_DISTINCT`` distinct ones (truncated to ``TEXT_MAX``); later new values read ``<other>``."""

    def __init__(self) -> None:
        self.seen: set = set()

    def __call__(self, v) -> str:
        s = str(v if v is not None else "").strip()[:TEXT_MAX]
        if s == "":
            return "<blank>"
        if s in self.seen:
            return s
        if len(self.seen) < MAX_DISTINCT:
            self.seen.add(s)
            return sys.intern(s)
        return "<other>"


NO_SIDECAR = ("unknown", "unknown", "unknown", "no_sidecar", "no_sidecar_row", "no_sidecar_row", "no_sidecar_row", "<no_sidecar_row>", "<no_sidecar_row>", "-", "age_na")


def read_ext_states(path: Path | None, keep, ft_bucket: _Bucket, fc_bucket: _Bucket) -> tuple[dict, dict, dict]:
    """({market_id: (cat, rw, fee, fee_src, fe, fs, tbf, fee_type, fee_category, schedule hash, age)} for ``keep`` only, {column: present},
    {schedule hash: verbatim fee_schedule text} of the distinct texts met, at most ``MAX_SCHEDULES``)."""
    out: dict = {}
    texts: dict = {}
    if path is None or not Path(path).exists():
        return out, {}, texts
    it = c240._iter_csv(path, EXT_COLS)
    present = next(it, None)
    if present is None:
        return out, {}, texts
    has = dict(zip(EXT_COLS, present, strict=True))
    for mid, ft, fc, ss, rw, fe, fs, tbf, cr in it:
        if mid not in keep:
            continue
        fee, src, _coef = c251.fee_class(fe, has["fees_enabled"], fs)
        f_s, f_h = fs_state(has["fee_schedule"], fs)
        if f_h != "-" and f_h not in texts and len(texts) < MAX_SCHEDULES:
            texts[f_h] = fs
        out[mid] = (c240.category_of(ft, fc, ss, True), c240.reward_status(rw, True, has["clob_rewards"]), fee, src,
                    fe_state(has["fees_enabled"], fe), f_s, tbf_state(has["taker_base_fee"], tbf), ft_bucket(ft), fc_bucket(fc), f_h, age_class(cr))
    return out, has, texts


def _code(two: bool, fee: str, cat: str) -> int:
    return int(two) | (_FEE_IDX.get(fee, 2) << 1) | (_CAT_IDX.get(cat, 3) << 3)


def _decode(c: int) -> tuple[bool, str, str]:
    return bool(c & 1), FEES[(c >> 1) & 3], CATS[(c >> 3) & 7]


class Probe:
    """Feeds captures in time order; keeps per market only a small integer code of capture k - 1 (two-sided, fee class, category)."""

    def __init__(self) -> None:
        self.prev: dict | None = None
        self.prev_t = math.nan
        self.ft_bucket, self.fc_bucket = _Bucket(), _Bucket()
        self.schedules: dict = {}
        self.per_capture: list[dict] = []
        self.by_date_fields: dict[str, Counter] = {}
        self.by_date_fee_text: dict[str, Counter] = {}
        self.by_date_schedule: dict[str, Counter] = {}
        self.by_date_switches: dict[str, Counter] = {}
        self.date_captures: Counter = Counter()
        self.notes: Counter = Counter()

    def note_schedule(self, h: str, text: str) -> str:
        if h == "-" or h in self.schedules:
            return h
        if len(self.schedules) < MAX_SCHEDULES:
            self.schedules[h] = text[:SCHEDULE_TEXT_MAX]
            return h
        return "<other>"

    def feed(self, t: float, cap_id: str, rows: dict, ext: dict, ext_cols: dict, ext_info: dict, schedule_text: dict) -> None:
        """``rows``: {market_id: two-sided at k} of capture k's open active binary rows."""
        day = c240.day_of(t)
        self.date_captures[day] += 1
        has_prev = self.prev is not None and 0 < t - self.prev_t <= GAP_MAX_S
        if not has_prev and self.prev is not None:
            self.notes["previous_capture_gap_too_large"] += 1
        prev = self.prev if has_prev else {}
        counts: Counter = Counter()
        raw: Counter = Counter()
        sw: Counter = Counter()
        bf = self.by_date_fields.setdefault(day, Counter())
        bt = self.by_date_fee_text.setdefault(day, Counter())
        bs = self.by_date_schedule.setdefault(day, Counter())
        bw = self.by_date_switches.setdefault(day, Counter())
        cur: dict = {}
        n_side = 0
        for mid, two in rows.items():
            two = bool(two)
            st = ext.get(mid)
            if st is None:
                st = NO_SIDECAR
            else:
                n_side += 1
            cat, rw, fee, src, fe, fs, tbf, ft, fc, fh, age = st
            fh = self.note_schedule(fh, schedule_text.get(fh, "")) if fh != "-" else fh
            pc = prev.get(mid)
            cur[mid] = _code(two, fee, cat)
            cells = ["ch251_open_row"]
            if two:
                cells.append("two_sided_k")
                if pc is not None and pc & 1:
                    cells.append("ch261_complete_unit")
            for cell in cells:
                counts[f"{cell}|{cat}|{rw}|{fee}|{src}"] += 1
                if cat in (ELIG, "unknown"):
                    raw[f"{cell}|{cat}|{rw}|{fee}|{src}|fe={fe}|fs={fs}|tbf={tbf}|age={age}"] += 1
                bf[f"{cell}|{cat}|{rw}|{fee}|{src}|fe={fe}|fs={fs}|tbf={tbf}|age={age}"] += 1
                bt[f"{cell}|{cat}|{fee}|ft={ft}|fc={fc}"] += 1
                if cell != "two_sided_k":
                    bs[f"{cell}|{cat}|{fee}|sched={fh}"] += 1
            if pc is not None:
                _p2, pf, pcat = _decode(pc)
                if pf != fee or pcat != cat:
                    key = f"fee {pf}->{fee}|cat {pcat}->{cat}"
                    sw[key] += 1
                    bw[key] += 1
                else:
                    sw["unchanged"] += 1
                    bw["unchanged"] += 1
        self.prev, self.prev_t = cur, t
        self.per_capture.append({
            "id": cap_id, "start_utc": datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "date": day, "has_previous_capture": has_prev,
            "open_binary_rows": len(rows), "rows_with_sidecar_row": n_side, "sidecar_file": ext_info.get("present", False),
            "ext_version": ext_info.get("ext_version"), "sidecar_columns_present": {k: v for k, v in ext_cols.items() if k != "market_id"},
            "counts": dict(sorted(counts.items())), "raw_fields_eligible_and_unknown": dict(sorted(raw.items())),
            "fee_or_category_class_changes_vs_km1": dict(sorted(sw.items())),
        })

    def finish(self) -> dict:
        series: dict = {}
        for name, (cell, cat, rw, fee) in HEADLINE.items():
            pref = f"{cell}|{cat}|{rw}|{fee}|"
            series[name] = [(p["start_utc"], p["has_previous_capture"], sum(v for k, v in p["counts"].items() if k.startswith(pref))) for p in self.per_capture]
        by_src: dict = {}
        for p in self.per_capture:
            for k, v in p["counts"].items():
                cell, cat, rw, fee, src = k.split("|")
                if cat == ELIG and rw == "unrewarded":
                    by_src.setdefault(f"{cell}|{fee}|{src}", []).append(v)

        def stats(vals: list) -> dict:
            st = c240._stats([float(v) for v in vals])
            if vals:
                top5 = sum(sorted(vals, reverse=True)[:5])
                st["top5_capture_share"] = top5 / st["total"] if st["total"] else None
                st["median_over_mean"] = st["median"] / st["mean"] if st["mean"] else None
            return st

        headline: dict = {}
        for name, ser in series.items():
            need_prev = HEADLINE[name][0] == "ch261_complete_unit"
            block: dict = {}
            for span, (a, z) in SPANS.items():
                block[span] = stats([v for s, hp, v in ser if a <= s < z and (hp or not need_prev)])
            block["all_covered"] = stats([v for _s, hp, v in ser if hp or not need_prev])
            block["by_date_mean"] = {}
            for d in sorted(self.date_captures):
                vals = [v for s, hp, v in ser if s[:10] == d and (hp or not need_prev)]
                block["by_date_mean"][d] = (sum(vals) / len(vals)) if vals else None
            headline[name] = block
        return {
            "headline_nonsports_excrypto_unrewarded": headline,
            "nonsports_excrypto_unrewarded_by_cell_fee_src_all_covered": {k: stats(v) for k, v in sorted(by_src.items())},
            "per_capture": self.per_capture,
            "by_date_fields": {d: dict(sorted(c.items())) for d, c in sorted(self.by_date_fields.items())},
            "by_date_fee_type_and_fee_category": {d: dict(sorted(c.items())) for d, c in sorted(self.by_date_fee_text.items())},
            "by_date_fee_schedule_hash": {d: dict(sorted(c.items())) for d, c in sorted(self.by_date_schedule.items())},
            "by_date_class_changes_vs_km1": {d: dict(sorted(c.items())) for d, c in sorted(self.by_date_switches.items())},
            "fee_schedule_texts_by_hash": dict(sorted(self.schedules.items())),
            "distinct_value_caps": {"fee_type_values_kept": len(self.ft_bucket.seen), "fee_category_values_kept": len(self.fc_bucket.seen), "max_distinct": MAX_DISTINCT,
                                    "fee_schedule_hashes_kept": len(self.schedules), "max_schedules": MAX_SCHEDULES},
            "captures_by_date": dict(sorted(self.date_captures.items())),
            "notes": dict(self.notes),
        }


def discover_all(roots: list[Path], start_utc: str, end_utc: str) -> tuple[list[dict], list[dict], list[dict]]:
    """(covered captures as ``boundary_map_ch240.discover``, captures whose rows file is gone, captures in a non-complete state), all in the span."""
    covered = c240.discover(roots, start_utc, end_utc)
    have = {int(round((c["start"] - GRID_REF_S) / GRID_S)) for c in covered}
    t0, t1 = c240.parse_utc(start_utc), c240.parse_utc(end_utc)
    gone: dict = {}
    other: dict = {}
    for root in roots:
        for p in sorted(Path(root).glob("*/manifest.json")):
            try:
                m = json.loads(p.read_text())
            except (OSError, ValueError):
                continue
            t = c240.parse_utc(m.get("started_utc"))
            if not math.isfinite(t) or not (t0 <= t < t1):
                continue
            slot = int(round((t - GRID_REF_S) / GRID_S))
            if slot in have:
                continue
            rec = {"id": p.parent.name, "start_utc": datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "state": m.get("state")}
            if m.get("state") == "complete":
                gone.setdefault(slot, rec)
            else:
                other.setdefault(slot, rec)
    return covered, [gone[k] for k in sorted(gone)], [other[k] for k in sorted(other) if k not in gone]


def run_probe(roots: list[Path], start_utc: str, end_utc: str) -> dict:
    caps, gone, not_complete = discover_all(roots, start_utc, end_utc)
    t0, t1 = c240.parse_utc(start_utc), c240.parse_utc(end_utc)
    pr = Probe()
    inputs: list[dict] = []
    for c in caps:
        d = Path(c["dir"])
        ext_p, em_p = d / "rows_ext.csv.gz", d / "ext_manifest.json"
        files = [d / "manifest.json", d / "rows.csv.gz"] + [f for f in (ext_p, em_p) if f.exists()]
        for f in files:
            inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": c240.sha256_file(f)})
        ext_info: dict = {"present": ext_p.exists()}
        if em_p.exists():
            try:
                ext_info["ext_version"] = json.loads(em_p.read_text()).get("ext_version")
            except (OSError, ValueError):
                ext_info["ext_version"] = "unreadable"
        rows = c251.read_rows(d / "rows.csv.gz")
        two = {mid: r[3] for mid, r in rows.items()}  # only the two-sided flag is kept (memory-light; no price is kept)
        del rows
        ext, cols, texts = read_ext_states(ext_p if ext_p.exists() else None, two, pr.ft_bucket, pr.fc_bucket)
        pr.feed(c["start"], c["id"], two, ext, cols, ext_info, texts)
        del two, ext, texts
    starts = [c["start"] for c in caps]
    gaps = []
    edges = [t0 - GRID_S / 2, *starts, t1 - GRID_S / 2 + 1]
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    for a, z in zip(edges, edges[1:], strict=False):
        if z - a > GAP_MAX_S:
            gaps.append({"after": datetime.fromtimestamp(a, UTC).strftime(fmt), "before": datetime.fromtimestamp(z, UTC).strftime(fmt), "hours": round((z - a) / 3600, 2)})
    res = pr.finish()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    expected = int((t1 - t0) // GRID_S)
    return {
        "version": VERSION,
        "kind": "q0717 LT13 fee-reading probe: counts only, k = 0, uncounted; captures k and k - 1 only; never capture k + 1; no spread or price change, no target, no outcome, no P&L",
        "span": {"start_utc": start_utc, "end_utc": end_utc, "expected_2h_slots": expected},
        "captures": {
            "covered": len(caps), "covered_ids": [c["id"] for c in caps],
            "covered_span": {"first_start_utc": datetime.fromtimestamp(starts[0], UTC).strftime(fmt) if starts else None,
                             "last_start_utc": datetime.fromtimestamp(starts[-1], UTC).strftime(fmt) if starts else None},
            "covered_days": len(caps) * GRID_S / 86400.0,
            "rows_gone_counted_missing_never_restored": gone, "non_complete_state": not_complete,
            "missing_expected": max(0, expected - len(caps)), "gaps_over_2h30": gaps,
        },
        "cells": {"ch251_open_row": "every open active binary row at k (CH251 ch250/rows_open_binary)", "two_sided_k": "open row two-sided at k (0 < bid < ask <= 1)",
                  "ch261_complete_unit": "two-sided at k - 1 and k, k - 1 within 2 h 30 min (CH261 ch252/units_complete)"},
        "readings": {"fee": "population_map_ch251.fee_class unchanged (fee_free = fees_enabled non-empty false, or fee_schedule rate <= 0; fee_on = rate > 0; unknown otherwise)",
                     "reward": "MAP reading: clob_rewards of capture k non-empty", "category": "as the CH240 / CH251 / CH261 maps (sidecar fee_type / fee_category / series_slugs); a row whose fee_category is the literal 'unknown' is non-crypto there",
                     "raw_states": "fees_enabled: col_absent / blank / true / false / other; fee_schedule: col_absent / empty / unparseable / no_rate_key / rate_nonnumeric / rate_zero / rate_pos (+ sha256[:16] of the text); taker_base_fee: col_absent / blank / zero / pos / other; fee_type, fee_category verbatim (first 64 values); age = created_at before 2026-03-30",
                     "reference_spans": SPANS},
        "not_read": NOT_READ,
        "peak_rss_mb": round(rss / (2**20 if sys.platform == "darwin" else 1024), 1),
        "inputs": inputs, "code_sha256": code_sha256(), **res,
    }
