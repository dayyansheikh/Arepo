# ruff: noqa: E501
"""CB16-K: the Kalshi-absent map (docs/research_lab/CREATIVE_BATCH_16.md CB16-K, section 9 items 14-16, section 10). CENSUS ONLY, k = 0: no counted test, no outcome, no price, no network.
Rules part ``K`` (it binds on its rules part alone; there is no K freeze).

Streaming, field-restricted readers of the host's ``cross_venue/`` files (2026-10-12): ``poly_markets.json`` (a top-level JSON array, 171 MB), ``kalshi_markets*.jsonl`` and
``matches_all.json`` (+ the rule keys of ``audit_flags.json``). An allow-list object hook drops every other key WHILE DECODING: ``outcome_prices``, ``closed_time``, Kalshi ``result`` and
``settlement_value``, matches' hindsight ``p_end`` and ``audit_flags``' resolution list are never parsed into a row (unit-tested with fixtures carrying them).

Labels (frozen, outcome-free): PRESENT-STRICT (market id in ``matches_all.json``, the r1 audit-rule conflicts excluded and counted); PRESENT-TOPIC (not strict; a Kalshi market with
``|close - end| <= 3 d``, >= 2 shared content words and word Jaccard >= 0.30); FAR-TOPIC (the same text rule at ``30 d <= |close - end| <= 180 d``; disjoint from PRESENT-TOPIC by construction);
ABSENT (liquid-universe) = neither strict nor topic (FAR-TOPIC is a counted subset); UNLISTABLE = a reported subset of ABSENT by the frozen regex. Cells: LABELLER class x lifetime-volume
decile (hindsight, labelled). The Kalshi universe holds only liquid, settled, non-multivariate markets of series sharing a content bigram with a Polymarket title, so ABSENT means no
such twin, not no twin (round 1 item 14).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb13_label as lab
from . import cb16_common as c16
from . import cross_venue as cv

Refused = cm.Refused
NotNow = cm.NotNow

LABEL_ABSENT = "ABSENT (liquid-universe)"
LABEL_SELECTED_ON_VOLUME = "selected on lifetime volume"
LABEL_HINDSIGHT_VOLUME = "lifetime volume is hindsight"
EXPECTED_COUNTS = {"poly_markets": 148384, "kalshi_markets": 326380, "matches": 958}
FRAME_END = ("2025-10-13T00:00:00Z", "2026-10-01T00:00:00Z")
TOPIC_MAX_GAP_S = 3 * 86400.0
FAR_GAP_S = (30 * 86400.0, 180 * 86400.0)
TOPIC_MIN_SHARED = 2
TOPIC_MIN_JACCARD = 0.30
CELL_MIN_EVENTS = 30
RE_ENTRY_MIN_CELLS = 5
RE_ENTRY_MDE_PP = 2.0
MDE_SD_OPTIMISTIC = 0.10
MDE_SD_MAX = 0.24
DECILES = 10
UNLISTABLE_RE = re.compile(r"(?i)(\bassassinat\w*|\bterroris\w*|\bdeclar\w* (?:of )?war\b|\bwar declaration\b|\binvasion\b|\binvade\w*|\b(?:military|air) strikes?\b|\bnuclear (?:detonation|weapon|test)\w*|\bcoup\b)")
POLY_KEEP = ("market_id", "event_id", "condition_id", "question", "item", "outcomes", "end", "event_title", "slug", "volume", "volume_num", "volumeNum", "volume_total",
             "neg_risk_market_id", "negRiskMarketID", "fee_category")
KALSHI_KEEP = ("ticker", "title", "yes_sub", "close_time", "cat", "series", "volume")
MATCH_KEEP = ("p_market_id", "p_event_id", "k_ticker", "k_cat")
FLAG_KEEP = ("rule",)  # audit_flags.json: only the rule-based conflicts; the resolution-disagreement list is outcome-based and is never parsed
POLY_VOLUME_KEYS = ("volume", "volume_num", "volumeNum", "volume_total")
CROSS_VENUE_PINS = {  # sha256 of the 2026-10-12 files (the CB12-X pins for the same bytes); matches_all.json pinned by the coordinator (size/mtime in MATCHES_ALL_PIN_META)
    "poly_markets.json": "749adfa6faf34c4948fec9dc9e6bac2485133713370893e489aa5bd6434a23b2",
    "audit_flags.json": "a7273ea747c8bb3162effe790363108fb820599c884a14d539b4ca464b6b7629",
    "kalshi_markets.jsonl": "703fda587da8581651c1f8500c20ed7388647ecbf9234c748cf5540f7b3c073c",
    "kalshi_markets_b.jsonl": "47f49f5bd6875318a2fc92f54502c2df6a802d11f24de709658ec715862bedea",
    "kalshi_markets_s0.jsonl": "80445c4e2123a00d51eb3442b9f9cb5ace3b5bbb61ecede49fc8b544e5c55af0",
    "kalshi_markets_s1.jsonl": "a1a36adfd7b0fb9466df5905e58d7dded446897276b941435890ed352772943b",
    "kalshi_markets_s2.jsonl": "39975faf55e23d456bc28f80c56229391320321fac77ad9d75463b4a76713b55",
    "kalshi_markets_s3.jsonl": "0e13ffcac5f97cd1c52cbed939a34fae8997dee6aefd5e68bab61113ebd23755",
    "kalshi_markets_s4.jsonl": "6a47c20aea5b1de400b6d3a620d688915a9af950c3c232a09fd577c24b254234",
    "kalshi_markets_s5.jsonl": "9479b4cc7a089fe6e96bc99da4815854d7b73d6440869c260eee6d7438934d15",
    "matches_all.json": "f4cde1e952d85fbe6bca8ac1d42620fcee4bc755468381ccaf5cd639d27ca326",  # measured read-only on the host by the coordinator (freeze-check amendment 5)
}
MATCHES_ALL_PIN_META = {"size_bytes": 603444, "mtime_utc": "2026-10-12T20:52:48Z", "host_path": "~/arepo/data-dumps/research_lab/cross_venue/matches_all.json",
                        "limitation": "matches_all.json is not re-derived from the pinned inputs and its hindsight p_end is never parsed"}
SMOKE_NEEDS = ("k_inputs_pinned", "k_counts_exact", "k_no_outcome_fields", "k_topic_rule")


def part_unready() -> str | None:
    bad = sorted(k for k, v in CROSS_VENUE_PINS.items() if not v or v == c16.PIN_UNSET)
    return f"K input sha256 pins unset: {bad}" if bad else None


# =====================================================================================================================================================
# Streaming, field-restricted readers
# =====================================================================================================================================================


def _hook(keep: tuple[str, ...]):
    ks = frozenset(keep)
    return lambda kv: {k: v for k, v in kv if k in ks}


def iter_json_array(path: Path, keep: tuple[str, ...], chunk: int = 1 << 20) -> Iterator[dict]:
    """Stream the objects of a top-level JSON array one at a time (never ``json.load``), keeping only the ``keep`` keys of every object (and of nested objects) at decode time."""
    c16.guard_cross_venue_file(Path(path))
    dec = json.JSONDecoder(object_pairs_hook=_hook(keep))
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
            if isinstance(obj, dict):
                yield obj


def iter_kalshi(root: Path) -> Iterator[dict]:
    """``kalshi_markets*.jsonl`` line by line in glob order; the first occurrence of a ticker wins (the study's rule). Allow-listed keys only."""
    hook = _hook(KALSHI_KEEP)
    seen: set[str] = set()
    for f in sorted(Path(root).glob("kalshi_markets*.jsonl")):
        c16.guard_cross_venue_file(f)
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                m = json.loads(line, object_pairs_hook=hook)
                t = m.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    yield m


def read_matches(root: Path) -> list[dict]:
    p = c16.guard_cross_venue_file(Path(root) / "matches_all.json")
    rows = json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=_hook(MATCH_KEEP))
    return [r for r in rows if isinstance(r, dict)]


def read_rule_conflicts(root: Path) -> set[str]:
    """The Kalshi tickers of the r1 audit-RULE conflicts (audit words and hand verdicts). The resolution-disagreement list of ``audit_flags.json`` is outcome-based and never parsed."""
    p = Path(root) / "audit_flags.json"
    if not p.exists():
        return set()
    c16.guard_cross_venue_file(p)
    top = _hook(FLAG_KEEP)
    # the top-level object (the one holding the study's result lists) keeps only ``rule``; a nested object (the ticker -> reason map) is kept whole
    doc = json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=lambda kv: top(kv) if {"rule", "resolution_disagree"} & {k for k, _ in kv} else dict(kv))
    rule = doc.get("rule") if isinstance(doc, dict) else None
    return set(rule) if isinstance(rule, dict) else set()


def sha256_files(root: Path) -> dict[str, str]:
    root = Path(root)
    out = {}
    for name in sorted(CROSS_VENUE_PINS):
        p = root / name
        if p.exists():
            out[name] = c16.sha256_file(c16.guard_cross_venue_file(p))
    for f in sorted(root.glob("kalshi_markets*.jsonl")):
        out.setdefault(f.name, c16.sha256_file(c16.guard_cross_venue_file(f)))
    return out


def verify_pins(root: Path) -> dict:
    got = sha256_files(root)
    unset = sorted(k for k, v in CROSS_VENUE_PINS.items() if not v or v == c16.PIN_UNSET)  # an unset pin is REFUSED, never skipped (freeze-check amendment 5)
    bad = sorted(set(unset) | {k for k, v in CROSS_VENUE_PINS.items() if got.get(k) != v and k in got})
    missing = sorted(k for k in CROSS_VENUE_PINS if k not in got)
    return {"ok": not bad and not missing, "mismatch": bad, "missing": missing, "unset": unset, "sha256": got}


def count_files(root: Path) -> dict:
    """The published counts, from the streaming readers (any other count is a smoke FAIL): Polymarket markets, Kalshi markets (unique tickers), strict matches."""
    root = Path(root)
    poly = sum(1 for _ in iter_json_array(root / "poly_markets.json", ("market_id",)))
    kal = sum(1 for _ in iter_kalshi(root))
    mt = len(read_matches(root))
    return {"poly_markets": poly, "kalshi_markets": kal, "matches": mt}


# =====================================================================================================================================================
# Text rules
# =====================================================================================================================================================


def poly_text(m: dict) -> str:
    return cv.p_text({"question": m.get("question") or "", "item": m.get("item") or ""})


def kalshi_text(m: dict) -> str:
    return cv.k_text({"title": m.get("title") or "", "yes_sub": m.get("yes_sub") or ""})


def poly_end(m: dict) -> float:
    e = cv._epoch(m.get("end"))
    return e


def poly_volume(m: dict) -> float:
    for k in POLY_VOLUME_KEYS:
        v = c16.num(m.get(k))
        if math.isfinite(v):
            return v
    return math.nan


def is_binary_yes_no(m: dict) -> bool:
    return list(m.get("outcomes") or []) == ["Yes", "No"]


def in_frame(m: dict) -> bool:
    e = poly_end(m)
    return bool(is_binary_yes_no(m) and math.isfinite(e) and c16.ep(FRAME_END[0]) <= e < c16.ep(FRAME_END[1]))


def words_of(text: str) -> frozenset[str]:
    return cv.tokenize(text)[0]


def text_twin(pw: frozenset[str], kw: frozenset[str]) -> bool:
    """The topic text rule: >= 2 shared content words AND word Jaccard >= 0.30 (the matcher's tokeniser and stop words)."""
    sh = len(pw & kw)
    union = len(pw) + len(kw) - sh
    return bool(sh >= TOPIC_MIN_SHARED and union > 0 and sh / union >= TOPIC_MIN_JACCARD - 1e-12)


def gap_class(gap_s: float) -> str | None:
    """'topic' for ``|gap| <= 3 d``; 'far' for ``30 d <= |gap| <= 180 d``; else None (the classes are disjoint by construction)."""
    a = abs(gap_s)
    if a <= TOPIC_MAX_GAP_S + 1e-9:
        return "topic"
    if FAR_GAP_S[0] - 1e-9 <= a <= FAR_GAP_S[1] + 1e-9:
        return "far"
    return None


def is_unlistable(text: str) -> bool:
    return bool(UNLISTABLE_RE.search(text or ""))


class KalshiIndex:
    """Kalshi markets as word-id tuples with an inverted index (word -> sorted close days); memory-lean (word ids, not strings)."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.words: list[tuple[int, ...]] = []
        self.close: list[float] = []
        self.cat: list[str] = []
        self._post: dict[int, list[tuple[float, int]]] = {}
        self._frozen: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self.df: Counter = Counter()

    def add(self, m: dict) -> None:
        w = words_of(kalshi_text(m))
        ids = tuple(sorted(self.vocab.setdefault(x, len(self.vocab)) for x in w))
        c = cv._epoch(m.get("close_time"))
        kid = len(self.words)
        self.words.append(ids)
        self.close.append(c)
        self.cat.append(str(m.get("cat") or ""))
        if not math.isfinite(c):
            return
        for i in ids:
            self._post.setdefault(i, []).append((c, kid))
            self.df[i] += 1

    def finish(self) -> None:
        for i, lst in self._post.items():
            lst.sort()
            self._frozen[i] = (np.array([x[0] for x in lst]), np.array([x[1] for x in lst], dtype=np.int64))
        self._post = {}

    def best(self, pw: frozenset[str], end: float, gap_lo: float, gap_hi: float) -> bool:
        """Does some Kalshi market with ``gap_lo <= |close - end| <= gap_hi`` pass the text rule against the Polymarket word set ``pw``? A qualifying twin shares >= 2 words, so scanning the
        postings of all but the most frequent shared-capable word suffices (prefix filter): the n - 1 rarest known words."""
        ids = sorted((self.vocab[w] for w in pw if w in self.vocab), key=lambda i: self.df[i])
        if len(ids) < TOPIC_MIN_SHARED:
            return False
        scan = ids[:-1]
        seen: set[int] = set()
        idset = set(ids)
        for i in scan:
            days, kids = self._frozen.get(i, (np.array([]), np.array([], dtype=np.int64)))
            for lo, hi in ((end - gap_hi, end - gap_lo), (end + gap_lo, end + gap_hi)):
                a, b = int(np.searchsorted(days, lo - 1e-9, side="left")), int(np.searchsorted(days, hi + 1e-9, side="right"))
                for kid in kids[a:b].tolist():
                    if kid in seen:
                        continue
                    seen.add(kid)
                    kw = self.words[kid]
                    sh = sum(1 for x in kw if x in idset)
                    union = len(pw) + len(kw) - sh
                    if sh >= TOPIC_MIN_SHARED and union > 0 and sh / union >= TOPIC_MIN_JACCARD - 1e-12:
                        return True
        return False


def build_kalshi_index(rows: Iterable[dict]) -> KalshiIndex:
    ix = KalshiIndex()
    for m in rows:
        ix.add(m)
    ix.finish()
    return ix


# =====================================================================================================================================================
# Labels, cells, counts
# =====================================================================================================================================================


def class_of(m: dict) -> str:
    return lab.classify(m.get("question") or "", m.get("slug") or "", "", m.get("fee_category") or "", "", "", has_sidecar=False)[0]


def label_markets(poly_rows: Iterable[dict], ix: KalshiIndex, strict_ids: set[str], conflict_ids: set[str]) -> tuple[list[dict], dict]:
    """One record per frame market: id, event, class, volume, label, FAR-TOPIC and UNLISTABLE flags. ``strict_ids`` are the strict-match market ids, ``conflict_ids`` those among them whose
    Kalshi ticker is an r1 audit-rule conflict (excluded from PRESENT-STRICT and counted; they are then labelled by the text rule like any other market)."""
    out = []
    cnt: Counter = Counter()
    for m in poly_rows:
        cnt["rows"] += 1
        if not in_frame(m):
            cnt["outside_frame"] += 1
            continue
        mid = str(m.get("market_id"))
        txt = poly_text(m)
        pw = words_of(txt)
        end = poly_end(m)
        strict = mid in strict_ids and mid not in conflict_ids
        if mid in conflict_ids:
            cnt["r1_conflict_excluded"] += 1
        topic = far = False
        if not strict:
            topic = ix.best(pw, end, 0.0, TOPIC_MAX_GAP_S)
            if not topic:
                far = ix.best(pw, end, FAR_GAP_S[0], FAR_GAP_S[1])
        label = "PRESENT-STRICT" if strict else ("PRESENT-TOPIC" if topic else LABEL_ABSENT)
        unl = is_unlistable(txt)
        rec = {"market_id": mid, "event_id": str(m.get("event_id") or "") or f"market:{mid}", "class": class_of(m), "volume": poly_volume(m), "label": label, "far_topic": int(far),
               "unlistable": int(unl and label == LABEL_ABSENT), "rule_conflict": int(unl and label != LABEL_ABSENT)}
        cnt["frame"] += 1
        cnt[label] += 1
        cnt["far_topic"] += int(far)
        cnt["unlistable_absent"] += rec["unlistable"]
        cnt["unlistable_rule_conflict"] += rec["rule_conflict"]
        out.append(rec)
    return out, dict(cnt)


def add_deciles(recs: list[dict]) -> list[float]:
    """Lifetime-volume decile (0-9) among the non-sports frame markets (hindsight, labelled); sports and unknown-volume markets carry decile -1 and are reported separately."""
    vols = np.array([r["volume"] for r in recs if r["class"] != lab.SPORTS and math.isfinite(r["volume"])])
    edges = [float(x) for x in np.percentile(vols, [10 * i for i in range(1, DECILES)])] if len(vols) >= DECILES else []
    for r in recs:
        r["decile"] = int(np.digitize(r["volume"], edges)) if (r["class"] != lab.SPORTS and math.isfinite(r["volume"]) and edges) else -1
    return edges


def cell_counts(recs: list[dict]) -> dict:
    """Markets and distinct events per label per cell (class x decile). SPORTS-FEED is reported separately (decile -1 cells)."""
    cells: dict[str, dict] = {}
    for r in recs:
        key = f"{r['class']}|{r['decile']}"
        c = cells.setdefault(key, {"class": r["class"], "decile": r["decile"], "markets": Counter(), "events": {}})
        for lb in (r["label"], "FAR-TOPIC" if r["far_topic"] else None, "UNLISTABLE" if r["unlistable"] else None):
            if lb:
                c["markets"][lb] += 1
                c["events"].setdefault(lb, set()).add(r["event_id"])
    out = {}
    for k, c in sorted(cells.items()):
        out[k] = {"class": c["class"], "decile": c["decile"], "markets": dict(c["markets"]), "events": {lb: len(s) for lb, s in c["events"].items()}}
    return out


def eligible_cells(cells: dict, present_labels: tuple[str, ...]) -> list[str]:
    """Cells holding BOTH a PRESENT label (any of ``present_labels``, events summed) and ABSENT with at least 30 events each; sports cells (decile -1) are never eligible."""
    out = []
    for k, c in cells.items():
        if c["decile"] < 0:
            continue
        pres = sum(c["events"].get(lb, 0) for lb in present_labels)
        if pres >= CELL_MIN_EVENTS and c["events"].get(LABEL_ABSENT, 0) >= CELL_MIN_EVENTS:
            out.append(k)
    return out


def mde_bounds(cells: dict, present_labels: tuple[str, ...]) -> dict:
    """Feature-free MDE bounds (section 2.7 / CH143): ``MDE = 3.80 x SD x sqrt(1/G_present + 1/G_absent)`` over the eligible cells (events pooled), at SD 0.10 (optimistic) and 0.24 (the maximum
    under calibration), in percentage points of the Brier residual."""
    el = eligible_cells(cells, present_labels)
    gp = sum(sum(cells[k]["events"].get(lb, 0) for lb in present_labels) for k in el)
    ga = sum(cells[k]["events"].get(LABEL_ABSENT, 0) for k in el)
    out: dict = {"eligible_cells": len(el), "cells": el, "events_present": gp, "events_absent": ga}
    for name, sd in (("optimistic_sd_0_10", MDE_SD_OPTIMISTIC), ("max_sd_0_24", MDE_SD_MAX)):
        out[name + "_pp"] = float(100.0 * c16.MDE_FACTOR * sd * math.sqrt(1.0 / gp + 1.0 / ga)) if gp > 0 and ga > 0 else None
    return out


def far_topic_cells(cells: dict, eligible: list[str]) -> int:
    """Eligible cells holding at least 30 FAR-TOPIC events (the re-entry rule's composition-placebo support)."""
    return sum(1 for k in eligible if cells[k]["events"].get("FAR-TOPIC", 0) >= CELL_MIN_EVENTS)


def re_entry(strict: dict, union: dict, cells: dict) -> dict:
    """The declared re-entry rule (no CB16 test): a counted K may be designed in a later batch only if the strict-or-topic label gives >= 5 eligible cells and an optimistic MDE <= 2 pp, a
    seeded blind audit of 100 PRESENT-TOPIC pairs finds >= 90% genuine twins (NOT computable here; titles only, later), and FAR-TOPIC has >= 30 events in >= 5 of the eligible cells."""
    el = union["cells"]
    n_far = far_topic_cells(cells, el)
    counts_ok = bool(union["eligible_cells"] >= RE_ENTRY_MIN_CELLS and union["optimistic_sd_0_10_pp"] is not None and union["optimistic_sd_0_10_pp"] <= RE_ENTRY_MDE_PP and n_far >= RE_ENTRY_MIN_CELLS)
    return {"counts_pass": counts_ok, "eligible_cells_union": union["eligible_cells"], "eligible_cells_strict": strict["eligible_cells"], "optimistic_mde_pp_union": union["optimistic_sd_0_10_pp"],
            "far_topic_cells": n_far, "topic_audit_seed": c16.SEED_K_AUDIT, "topic_audit": "only if the counts pass: 100 PRESENT-TOPIC pairs, titles only, science-reviewer, >= 90% genuine twins",
            "verdict": "counts pass: a topic audit may proceed (no counted K is registered)" if counts_ok else "CH143 recorded as not testable at the floor with available or feasibly collectable data"}


def key_overlaps(recs: list[dict], key_sources: dict[str, set[str]]) -> dict:
    """Frame markets carrying an exclusion key, by source and label (counts only; K computes no statistic from them)."""
    out: dict[str, Counter] = {}
    for r in recs:
        for s in key_sources.get(r["market_id"], ()):
            out.setdefault(s, Counter())[r["label"]] += 1
    return {s: dict(c) for s, c in sorted(out.items())}


def census(root: Path, key_sources: dict[str, set[str]] | None = None) -> dict:
    """The whole K census (counts only): pins verified, the readers' file counts, the labels, the cells, the eligible-cell counts for strict and for strict-or-topic, FAR-TOPIC support,
    the key overlaps and the feature-free MDE bounds, the re-entry verdict. No outcome and no price is read."""
    root = Path(root)
    pins = verify_pins(root)
    if not pins["ok"]:
        raise Refused(f"cross_venue inputs differ from the pinned sha256s: mismatch {pins['mismatch']} missing {pins['missing']}")
    matches = read_matches(root)
    conflicts = read_rule_conflicts(root)
    strict_ids = {str(r["p_market_id"]) for r in matches}
    conflict_ids = {str(r["p_market_id"]) for r in matches if r.get("k_ticker") in conflicts}
    ix = build_kalshi_index(iter_kalshi(root))
    recs, lab_counts = label_markets(iter_json_array(root / "poly_markets.json", POLY_KEEP), ix, strict_ids, conflict_ids)
    edges = add_deciles(recs)
    cells = cell_counts(recs)
    strict_m = mde_bounds(cells, ("PRESENT-STRICT",))
    union_m = mde_bounds(cells, ("PRESENT-STRICT", "PRESENT-TOPIC"))
    by_class = {c: dict(Counter(r["label"] for r in recs if r["class"] == c)) for c in lab.CLASSES}
    return {"counts_only": True, "labels": [LABEL_ABSENT, LABEL_SELECTED_ON_VOLUME, LABEL_HINDSIGHT_VOLUME], "pins": pins, "label_counts": lab_counts, "kalshi_markets_indexed": len(ix.words),
            "matches": len(matches), "r1_rule_conflicts_in_matches": len(conflict_ids), "volume_decile_edges": edges, "by_class": by_class, "cells": cells,
            "cells_both_labels_ge30_events": {"strict": strict_m["eligible_cells"], "strict_or_topic": union_m["eligible_cells"]},
            "mde_bounds_pp": {"strict": strict_m, "strict_or_topic": union_m}, "key_overlaps": key_overlaps(recs, key_sources or {}), "re_entry": re_entry(strict_m, union_m, cells),
            "sports_reported_separately": {lb: sum(1 for r in recs if r["class"] == lab.SPORTS and r["label"] == lb) for lb in ("PRESENT-STRICT", "PRESENT-TOPIC", LABEL_ABSENT)}}


# =====================================================================================================================================================
# Smoke (no network) and declaration
# =====================================================================================================================================================


def smoke_offline(ctx: dict) -> dict:
    """Part K smoke: the pins verify, the streaming readers reproduce EXACTLY 148,384 / 326,380 / 958 (any other count FAILS, no 'the file's own count'), no outcome field is parsed (a
    fixture carrying every forbidden field), and the topic / FAR-TOPIC rule edges (3 d, 2 words, Jaccard 0.30, 30 d and 180 d, disjointness)."""
    out: dict = {}
    d = Path(ctx["cross_venue_dir"]) if ctx.get("cross_venue_dir") else c16.CROSS_VENUE_DIR
    try:
        pins = verify_pins(d)
        out["k_inputs_pinned"] = {"pass": bool(pins["ok"]), "mismatch": pins["mismatch"], "missing": pins["missing"], "sha256": pins["sha256"]}
        counts = count_files(d)
        out["k_counts_exact"] = {"pass": counts == EXPECTED_COUNTS, "counts": counts, "expected": dict(EXPECTED_COUNTS)}
    except (OSError, ValueError, Refused) as exc:
        out.setdefault("k_inputs_pinned", {"pass": False, "error": f"{type(exc).__name__}: {exc}"[:200]})
        out["k_counts_exact"] = {"pass": False, "error": f"{type(exc).__name__}: {exc}"[:200]}
    fx = ('[{"market_id":"1","event_id":"e","question":"Q?","outcomes":["Yes","No"],"end":"2026-01-01T00:00:00Z","outcome_prices":"[1,0]","closed_time":"2026-01-02","outcomePrices":"x",'
          '"umaResolutionStatus":"resolved","result":"yes","settlement_value":1,"p_end":"2026-01-02"}]')
    import tempfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cross_venue"
        p.mkdir()
        (p / "poly_markets.json").write_text(fx)
        (p / "kalshi_markets.jsonl").write_text(json.dumps({"ticker": "T", "title": "x", "close_time": "2026-01-01", "result": "yes", "settlement_value": 1, "volume": 3}) + "\n")
        (p / "matches_all.json").write_text(json.dumps([{"p_market_id": "1", "p_event_id": "e", "k_ticker": "T", "k_cat": "c", "p_end": "x", "result": "y"}]))
        rows = list(iter_json_array(p / "poly_markets.json", POLY_KEEP)) + list(iter_kalshi(p)) + read_matches(p)
        parsed = {k for r in rows for k in r}
    bad = set(c16.FORBIDDEN_PARSE_FIELDS) & parsed
    out["k_no_outcome_fields"] = {"pass": not bad and "p_end" not in parsed and "result" not in parsed, "leaked": sorted(bad)}
    a, b = frozenset("alpha beta gamma delta".split()), frozenset("alpha beta epsilon zeta eta theta iota kappa".split())
    t_ok = [gap_class(3 * 86400.0) == "topic", gap_class(3 * 86400.0 + 1) is None, gap_class(30 * 86400.0) == "far", gap_class(30 * 86400.0 - 1) is None, gap_class(180 * 86400.0) == "far",
            gap_class(180 * 86400.0 + 1) is None, gap_class(-3 * 86400.0) == "topic",
            text_twin(frozenset("a1 b1 c1".split()), frozenset("a1 b1 d1 e1".split())) is True,  # 2 shared, Jaccard 2/5 = 0.40
            text_twin(frozenset("a1 b1 c1 d1".split()), frozenset("a1 b1 e1 f1 g1 h1".split())) is False,  # 2 shared, Jaccard 2/8 = 0.25
            text_twin(frozenset("a1 b1 c1 d1".split()), frozenset("a1 b1 c1 d1 e1 f1".split())) is True,
            text_twin(frozenset("a1 b1 c1".split()), frozenset("a1 d1 e1".split())) is False,  # 1 shared word
            text_twin(frozenset("a1 b1 c1 d1 e1 f1".split()), frozenset("a1 b1 g1 h1 i1 j1 k1 l1".split())) is False and text_twin(a, b) is False]
    out["k_topic_rule"] = {"pass": bool(all(t_ok)), "checks": [bool(x) for x in t_ok]}
    return out


def declared() -> dict:
    return {"family": "K (CH143): census only, k = 0", "inputs": sorted(CROSS_VENUE_PINS), "pins": {k: v for k, v in CROSS_VENUE_PINS.items()}, "matches_all_pin_meta": dict(MATCHES_ALL_PIN_META), "expected_counts": dict(EXPECTED_COUNTS),
            "frame": {"end": list(FRAME_END), "binary": "outcomes == ['Yes', 'No']", "selection": LABEL_SELECTED_ON_VOLUME},
            "fields": {"poly": list(POLY_KEEP), "kalshi": list(KALSHI_KEEP), "matches": list(MATCH_KEEP), "audit_flags": list(FLAG_KEEP)},
            "never_parsed": list(c16.FORBIDDEN_PARSE_FIELDS), "labels": {"present_strict": "market id in matches_all.json minus r1 audit-rule conflicts (counted)",
                                                                           "present_topic": {"max_gap_s": TOPIC_MAX_GAP_S, "min_shared": TOPIC_MIN_SHARED, "min_jaccard": TOPIC_MIN_JACCARD},
                                                                           "far_topic": {"gap_s": list(FAR_GAP_S), "same_text_rule": True, "disjoint_from_present_topic": True},
                                                                           "absent": LABEL_ABSENT, "unlistable_regex": UNLISTABLE_RE.pattern},
            "cells": "LABELLER class x lifetime-volume decile (hindsight); sports reported separately", "cell_min_events": CELL_MIN_EVENTS,
            "mde": {"factor": c16.MDE_FACTOR, "sd": [MDE_SD_OPTIMISTIC, MDE_SD_MAX], "formula": "3.80 x SD x sqrt(1/G_present + 1/G_absent) over eligible cells"},
            "re_entry": {"min_cells": RE_ENTRY_MIN_CELLS, "optimistic_mde_pp": RE_ENTRY_MDE_PP, "audit_seed": c16.SEED_K_AUDIT, "audit_n": 100, "audit_genuine_min": 0.90,
                         "far_topic_min_events": CELL_MIN_EVENTS, "far_topic_min_cells": RE_ENTRY_MIN_CELLS}}


def sha_of(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
