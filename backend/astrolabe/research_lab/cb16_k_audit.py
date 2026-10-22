# ruff: noqa: E501
"""CB16-K topic-audit sample (q0393). Counts-free and outcome-free. NOT part of the hashed rules part ``K`` (cb16_k.py is untouched; this module only reuses its readers, labeller and text rule).

Purpose: the declared re-entry rule needs "a seeded blind audit of 100 PRESENT-TOPIC pairs (science-reviewer, titles only, seed 16141) finds at least 90% to be genuine same-event twins".
This module draws that sample reproducibly and writes the auditor's file (titles and the two dates the 3-day rule used) apart from the key file (ids).

Procedure (documented, reproducible):
1. Refuse unless ``census_K.json`` exists, its recorded pins equal ``cb16_k.CROSS_VENUE_PINS`` (and the files on disk hash to them), its ``re_entry.counts_pass`` is true and its
   ``topic_audit_seed`` is 16141. The PRESENT-TOPIC markets are re-derived with the census's own functions (``label_markets`` on the same pinned inputs); the re-derived count must equal the
   census's ``label_counts['PRESENT-TOPIC']`` or the job refuses.
2. Pair = (Polymarket market, ONE Kalshi twin). A market with several qualifying twins (|close - end| <= 3 d, >= 2 shared content words, word Jaccard >= 0.30) shows the WEAKEST one: the
   lowest Jaccard, ties by the smaller |gap|, then by the ticker (conservative: a pass on the weakest twin holds for the label; the labeller itself only records that some twin exists).
3. Pair keys ``(market_id, ticker)`` are sorted canonically (by market_id string, then ticker); ``numpy.random.default_rng(16141).choice(N, size=min(100, N), replace=False)`` selects the
   rows; the draw order is the pair index (so the index carries no information about the key order).
Auditor file fields: pair index, Polymarket question and item, Polymarket end date, Kalshi title and subtitle (yes_sub), Kalshi close time. Nothing else is written there.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb16_common as c16
from . import cb16_k as k

Refused = k.Refused
VERSION = "cb16-k-audit-sample-v1"
SAMPLE_N = 100
SAMPLE_NAME, KEYS_NAME, MANIFEST_NAME = "audit_K_sample.json", "audit_K_keys.json", "audit_K_manifest.json"
SAMPLE_FIELDS = ("pair", "polymarket_question", "polymarket_item", "polymarket_end_date", "kalshi_title", "kalshi_subtitle", "kalshi_close_time")
KEY_FIELDS = ("pair", "market_id", "kalshi_ticker", "n_qualifying_twins")
TWIN_RULE = "weakest qualifying twin: lowest word Jaccard, then smaller |close - end|, then ticker"
PROCEDURE = ("sort PRESENT-TOPIC pair keys (market_id, ticker) canonically; numpy.random.default_rng(16141).choice(N, size=min(100, N), replace=False); pair index = draw order; "
             "twin shown = " + TWIN_RULE)


def check_census(census: dict, root: Path) -> dict:
    """Refuse unless the census K document is complete, passed its counts, names the audit seed and its pins equal the code's and the files'."""
    block = census.get("K") if isinstance(census, dict) else None
    if not isinstance(block, dict) or census.get("version") != "cb16-census-K-v1":
        raise Refused("census_K.json is not a cb16-census-K-v1 document")
    pins = (block.get("pins") or {}).get("sha256") or {}
    bad = sorted(n for n, v in k.CROSS_VENUE_PINS.items() if pins.get(n) != v)
    if bad:
        raise Refused(f"census_K.json pins differ from the code's pinned sha256s: {bad}")
    re_entry = block.get("re_entry") or {}
    if not re_entry.get("counts_pass"):
        raise Refused("the census did not pass the re-entry counts; no audit is drawn")
    if re_entry.get("topic_audit_seed") != c16.SEED_K_AUDIT:
        raise Refused(f"census topic_audit_seed {re_entry.get('topic_audit_seed')!r} != {c16.SEED_K_AUDIT}")
    live = k.verify_pins(root)
    if not live["ok"]:
        raise Refused(f"cross_venue inputs differ from the pinned sha256s: mismatch {live['mismatch']} missing {live['missing']}")
    n = (block.get("label_counts") or {}).get("PRESENT-TOPIC")
    if not isinstance(n, int) or n <= 0:
        raise Refused("census has no PRESENT-TOPIC count")
    return {"present_topic_count": n}


def _passes(pw_n: int, idset: set[int], kw: tuple[int, ...]) -> tuple[bool, float]:
    """The census's text rule on word-id sets (identical arithmetic to ``KalshiIndex.best`` / ``text_twin``). Returns (pass, Jaccard)."""
    sh = sum(1 for x in kw if x in idset)
    union = pw_n + len(kw) - sh
    jac = sh / union if union > 0 else 0.0
    return bool(sh >= k.TOPIC_MIN_SHARED and union > 0 and jac >= k.TOPIC_MIN_JACCARD - 1e-12), jac


def derive_topic_pairs(root: Path) -> list[dict]:
    """Re-derive every PRESENT-TOPIC market and its weakest topic twin from the pinned inputs, with the census's own readers and labeller. Sorted by (market_id, ticker)."""
    root = Path(root)
    matches = k.read_matches(root)
    conflicts = k.read_rule_conflicts(root)
    strict_ids = {str(r["p_market_id"]) for r in matches}
    conflict_ids = {str(r["p_market_id"]) for r in matches if r.get("k_ticker") in conflicts}
    ix = k.KalshiIndex()
    tickers: list[str] = []
    for m in k.iter_kalshi(root):
        tickers.append(str(m["ticker"]))
        ix.add(m)
    ix.finish()
    frame = [m for m in k.iter_json_array(root / "poly_markets.json", k.POLY_KEEP) if k.in_frame(m)]
    recs, _cnt = k.label_markets(frame, ix, strict_ids, conflict_ids)
    if len(recs) != len(frame):
        raise Refused("labeller / frame length mismatch")
    fin = sorted((c, i) for i, c in enumerate(ix.close) if math.isfinite(c))
    closes = np.array([c for c, _ in fin])
    kids = np.array([i for _, i in fin], dtype=np.int64)
    out: list[dict] = []
    for m, rec in zip(frame, recs, strict=True):
        if rec["label"] != "PRESENT-TOPIC":
            continue
        pw = k.words_of(k.poly_text(m))
        end = k.poly_end(m)
        idset = {ix.vocab[w] for w in pw if w in ix.vocab}
        a = int(np.searchsorted(closes, end - k.TOPIC_MAX_GAP_S - 1e-9, side="left"))
        b = int(np.searchsorted(closes, end + k.TOPIC_MAX_GAP_S + 1e-9, side="right"))
        twins = []
        for kid in kids[a:b].tolist():
            ok, jac = _passes(len(pw), idset, ix.words[kid])
            if ok:
                twins.append((jac, abs(ix.close[kid] - end), tickers[kid]))
        if not twins:
            raise Refused(f"market {rec['market_id']} is PRESENT-TOPIC by the labeller but no twin re-derived (internal inconsistency)")
        jac, gap, tk = min(twins)
        out.append({"market_id": rec["market_id"], "ticker": tk, "n_twins": len(twins), "jaccard": jac, "gap_s": gap,
                    "poly": {"question": m.get("question") or "", "item": m.get("item") or "", "end": m.get("end")}})
    out.sort(key=lambda r: (r["market_id"], r["ticker"]))
    return out


def draw(pairs: list[dict], seed: int = c16.SEED_K_AUDIT, n: int = SAMPLE_N) -> list[dict]:
    """``pairs`` must already be canonically sorted. Exactly ``n`` pairs, or all of them if fewer; in draw order."""
    keys = [(p["market_id"], p["ticker"]) for p in pairs]
    if keys != sorted(keys):
        raise Refused("pair keys are not canonically sorted")
    take = min(n, len(pairs))
    if not take:
        return []
    idx = np.random.default_rng(seed).choice(len(pairs), size=take, replace=False)
    return [pairs[int(i)] for i in idx]


def kalshi_texts(root: Path, tickers: set[str]) -> dict[str, dict]:
    got: dict[str, dict] = {}
    for m in k.iter_kalshi(root):
        if m["ticker"] in tickers:
            got[m["ticker"]] = {"title": m.get("title") or "", "subtitle": m.get("yes_sub") or "", "close_time": m.get("close_time")}
    return got


def build_files(chosen: list[dict], kal: dict[str, dict]) -> tuple[dict, dict]:
    sample, keys = [], []
    for i, p in enumerate(chosen):
        kt = kal[p["ticker"]]
        sample.append({"pair": i, "polymarket_question": p["poly"]["question"], "polymarket_item": p["poly"]["item"], "polymarket_end_date": p["poly"]["end"], "kalshi_title": kt["title"],
                       "kalshi_subtitle": kt["subtitle"], "kalshi_close_time": kt["close_time"]})
        keys.append({"pair": i, "market_id": p["market_id"], "kalshi_ticker": p["ticker"], "n_qualifying_twins": p["n_twins"]})
    return ({"version": VERSION, "for_auditor": True, "pairs": sample}, {"version": VERSION, "NOT_FOR_AUDITOR": True, "pairs": keys})


def sample_run(root: Path, census: dict, census_sha256: str, out_dir: Path, *, n: int = SAMPLE_N) -> dict:
    """The whole job. Refuses (before writing anything) if any output exists. Writes the auditor sample, the key file and the manifest (write-once)."""
    out_dir = Path(out_dir)
    paths = {nm: out_dir / nm for nm in (SAMPLE_NAME, KEYS_NAME, MANIFEST_NAME)}
    exists = [nm for nm, p in paths.items() if p.exists()]
    if exists:
        raise Refused(f"{exists} exist; the audit sample is written once")
    info = check_census(census, root)
    pairs = derive_topic_pairs(root)
    if len(pairs) != info["present_topic_count"]:
        raise Refused(f"re-derived PRESENT-TOPIC count {len(pairs)} != census {info['present_topic_count']}")
    chosen = draw(pairs, c16.SEED_K_AUDIT, n)
    sample, keys = build_files(chosen, kalshi_texts(root, {p["ticker"] for p in chosen}))
    for nm, doc in ((SAMPLE_NAME, sample), (KEYS_NAME, keys)):
        cm.write_once_json(paths[nm], doc)
    sha = {nm: hashlib.sha256(paths[nm].read_bytes()).hexdigest() for nm in (SAMPLE_NAME, KEYS_NAME)}
    manifest = {"version": VERSION, "outcome_free": True, "seed": c16.SEED_K_AUDIT, "n_requested": n, "n_drawn": len(chosen), "n_present_topic_pairs": len(pairs), "procedure": PROCEDURE,
                "numpy_version": np.__version__, "sample_sha256": sha[SAMPLE_NAME], "keys_sha256": sha[KEYS_NAME], "census_K_sha256": census_sha256,
                "cross_venue_pins_sha256": dict(k.CROSS_VENUE_PINS), "matches_all_pin_meta": dict(k.MATCHES_ALL_PIN_META),
                "weakest_twin_jaccard_min_max": [min(p["jaccard"] for p in chosen), max(p["jaccard"] for p in chosen)] if chosen else None,
                "sample_fields": list(SAMPLE_FIELDS), "key_fields": list(KEY_FIELDS)}
    cm.write_once_json(paths[MANIFEST_NAME], manifest)
    return {"paths": {nm: str(p) for nm, p in paths.items()}, "manifest_sha256": hashlib.sha256(paths[MANIFEST_NAME].read_bytes()).hexdigest(),
            "n_drawn": len(chosen), "n_present_topic_pairs": len(pairs), "sample_sha256": sha[SAMPLE_NAME], "keys_sha256": sha[KEYS_NAME]}
