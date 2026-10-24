# ruff: noqa: E501
"""CB2-L (ladder dominance within / across events), CB2-X2 (mechanism) and CB2-P (placeholder gate), as declared in
``docs/research_lab/CREATIVE_BATCH_2.md`` (sections 0-2, CB2-L, CB2-P, 4.1, 4.2, 4.4, challenger round 1 + response).

EXPLORATORY research tooling. Nothing here is an edge, calibration or profitability claim; every P&L is a paper
rule at recorded prices and AREPO never trades. Pure functions (unit-tested in ``tests/unit/test_cb2_structural.py``)
plus thin IO helpers. No network except ``fetch_question_text`` (and CB1's ``fetch_outcomes``), which take an
injected, shared ``history_backfill.Limiter``.

Shared statistics are imported from ``cb1_structural`` / ``creative_batch1`` (cost model, gap filter, mean_gate,
r_ann, outcomes fetch), never copied. No P1 code exists (the P gate is counts only).

Extract formats read (written by ``creative_batch1`` extractor v2): ``ladder_candidates/<capture_id>.csv.gz`` (text
free, dev) and ``ladders/<capture_id>.csv.gz`` (list filtered, rep), both with ``creative_batch1.LADDER_COLUMNS``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import cb1_structural as c1
from . import creative_batch1 as cb
from . import economics, forecast, if_h2, provenance
from . import history_backfill as hb

VERSION = "cb2-structural-v1"
LABEL = "EXPLORATORY CB2 structural tests"
GROUPER_VERSION = "ladder-grouper-v2"
KIND_TEST = "cb2_test"
KIND_REP = "cb2_replication"
SEED = 216

SEALS_DIR = provenance.REPO_ROOT / "docs" / "research_lab" / "seals"
GROUPER_SEAL_FILE = SEALS_DIR / "cb2_grouper_rule.json"
T2_REP_START_FILE = SEALS_DIR / "cb2_t_rep_start.json"
MODEL_SPEC_FILE = Path(__file__).resolve().parent / "model_specs" / "cb2_v1.json"
OUT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "creative_batch2"
CB2_EXTRACT_ROOT = cb.CB2_EXTRACT_ROOT
CB1_EXTRACT_ROOT = cb.EXTRACT_ROOT

# ---- declared dates (CB2 section 1.2) --------------------------------------------------------------
T2_DEV_START = cb.T2_DEV_START
T2_DEV_END = cb.T2_DEV_END
T2_REP_START_FLOOR = "2026-10-26T00:00:00Z"
T2_REP_LEN_D = 28
T2_L_OUT_DAYS = 30  # T2_L_out = T2_rep_end + 30 d

# ---- declared parameters ---------------------------------------------------------------------------
ALPHA_STAGE1 = 0.01
ALPHA_STAGE2 = 0.05
MIN_CLUSTERS = 30
MIN_UNITS = 100
RANN_MIN = 0.10
COST_SENS = 0.0075  # +0.75c on every bought leg (binding); a pair buys two legs
TRIGGER_NET = 0.005  # trigger: 1 - C(c) >= 0.5c
GAP_H = (1.5, 3.0)  # next complete capture, as CB1-D
DEPTH_MIN_SIZE = 5.0
DEPTH_MIN_CLUSTERS = 30
PAYOFF_MAX_BELOW1 = 0.02
PAYOFF_MIN_DETERMINED = 30
FLOORS = {"L1": 0.005, "X1": 0.005, "X2": 0.01}
PERSISTENCE_DRAWS = 200
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE_RATE = 0.015
X2_PERM_DRAWS = 2000
X2_MIN_PER_TYPE = 30
AUDIT_PER_TYPE = 50
AUDIT_GAP = 0.20
AUDIT_MAX_NOT_GENUINE = 0.05
AUDIT_SEED = 216
CROSS_MIN_STEM_TOKENS = 4
TEXT_BATCH = 20
UNIVERSE_EXCLUDED_CATEGORIES = tuple(sorted(cb.CB2_EXCLUDED_CATEGORIES))
P_GATE = {"min_setups_per_day": 2.0, "min_gap": 0.05, "min_events": 30, "open_members": [2, 25]}
REFUSED_RUN_IDS = ("h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders")


class Cb2Error(RuntimeError):
    """Base class for CB2 guard refusals (the runner exits 3 on these)."""


class DeclarationError(Cb2Error):
    pass


class GrouperRuleError(Cb2Error):
    pass


class WindowError(Cb2Error):
    pass


class TooEarlyError(Cb2Error):
    pass


class CaptureListError(Cb2Error):
    pass


class RepStartError(Cb2Error):
    pass


class LadderListError(Cb2Error):
    pass


def _ep(s: str) -> float:
    return c1._ep(s)


def _iso_z(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def refuse_run_id(run_id: str | None) -> None:
    if run_id in REFUSED_RUN_IDS:
        raise Cb2Error(f"run id {run_id!r} is sealed or reserved and never read by CB2 (section 1.3)")


# =============================================================================================
# Grouper rules, hash, and the committed pre-text seal
# =============================================================================================

_PREFIX_RE = re.compile(r"\b(by|before|through|until|on|in)\s+(?:the\s+)?(?:end\s+of\s+)?$", re.I)
INC_WORDS = ("by", "before")
DEC_WORDS = ("through", "until")
_MASK_YEAR_RE = re.compile(r"\b(?:19|20)\d\d\b")

GROUPER_RULES = {
    "version": GROUPER_VERSION,
    "universe": "non-sports, non-weather, non-neg-risk markets open in the first complete capture >= 12:00Z of each day "
                "from T2_dev_start plus the latest capture; question text and description from Gamma /markets?id=",
    "date_phrase": "exactly one month-day date match (if_h2.DATE_RE) in the question; zero or several: excluded",
    "direction": "keyword immediately before the date: by|before -> INC; through|until -> DEC "
                 "(continue(s) through D is DEC); on|in|anything else: excluded",
    "deadline": "if_h2.parse_deadline(None, question, created_at): end of the named day, US Eastern; no year and no "
                "created_at: excluded",
    "stem": "if_h2.stem(question): date phrase removed, lowercased, whitespace and punctuation normalised",
    "within_ladder": "same event, same stem, same direction, >= 2 distinct deadlines; duplicate deadline keeps the lowest "
                     "numeric market id",
    "cross_ladder": "same stem and direction and equal masked description across >= 2 events, exactly one rung per event "
                    "(an event with several rungs under the key is excluded from X and counted), stem >= "
                    f"{CROSS_MIN_STEM_TOKENS} tokens, non-empty description; duplicate deadline across events keeps the "
                    "lowest numeric market id; >= 2 distinct deadlines",
    "description_mask": "dates (if_h2.DATE_RE) and 4-digit years replaced by a token, lowercased, non-alphanumerics "
                        "collapsed",
    "pairs": "adjacent deadlines D1 < D2 among the rungs VISIBLE at the capture (list-version rule), independent of prices",
    "regex": {"prefix": _PREFIX_RE.pattern, "date": if_h2.DATE_RE.pattern, "stem_date": if_h2.STEM_DATE.pattern,
              "stem_year": if_h2.STEM_YEAR.pattern, "mask_year": _MASK_YEAR_RE.pattern},
    "words": {"inc": list(INC_WORDS), "dec": list(DEC_WORDS)},
    "versions": "v1 applies retrospectively to every dev capture from T2_dev_start; v>=2 are additive and prospective "
                "(a rung added by v>=2 is visible only to captures strictly after that version's listed_utc)",
}


# Functions whose SOURCE is bound into the grouper hash (freeze-check fix 1): the rule text alone does not bind the code
# that applies it. Names resolve at call time (module globals, or ``if_h2`` for the ``if_h2.`` prefix).
GROUPER_CODE = ("parse_direction", "mask_description", "ladder_grouper_v2", "_dedupe_deadline", "_idkey", "_rung",
                "if_h2.stem", "if_h2.parse_deadline", "if_h2._deadline_epoch")


def _norm_source(fn) -> str:
    """Normalised source: trailing whitespace stripped, blank lines dropped (indentation kept)."""
    import inspect

    return "\n".join(ln.rstrip() for ln in inspect.getsource(fn).splitlines() if ln.strip())


def grouper_code_sha256() -> dict[str, str]:
    out = {}
    for name in GROUPER_CODE:
        fn = getattr(if_h2, name[6:]) if name.startswith("if_h2.") else globals()[name]
        out[name] = hashlib.sha256(_norm_source(fn).encode()).hexdigest()
    return out


def grouper_rule_sha256() -> str:
    return hashlib.sha256(json.dumps({"rules": GROUPER_RULES, "code": grouper_code_sha256()}, sort_keys=True).encode()).hexdigest()


def _git_committed(path: Path) -> bool:
    from .cb1_history import spec_committed  # noqa: PLC0415

    return spec_committed(path)


def require_grouper_seal(path: Path | None = None, *, require_committed: bool = False) -> str:
    """``ladder-list`` refuses unless the committed rule hash equals the code's (hashed before any text is read).
    The runner passes ``require_committed=True`` (tracked by git and identical to HEAD)."""
    path = Path(path) if path is not None else GROUPER_SEAL_FILE
    if require_committed and path.exists() and not _git_committed(path):
        raise GrouperRuleError(f"grouper seal {path} is not committed (or differs from HEAD)")
    if not path.exists():
        raise GrouperRuleError(f"no committed grouper-rule seal at {path}; question text is not read")
    rec = json.loads(path.read_text())
    if rec.get("sha256") != grouper_rule_sha256():
        raise GrouperRuleError(f"grouper rule hash mismatch: committed {rec.get('sha256')} != code {grouper_rule_sha256()}")
    return rec["sha256"]


def write_grouper_seal(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else GROUPER_SEAL_FILE
    if path.exists():
        raise GrouperRuleError(f"{path} exists; a committed grouper seal is never rewritten")
    rec = {"sha256": grouper_rule_sha256(), "grouper": GROUPER_VERSION, "module": "cb2_structural.GROUPER_RULES"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return rec


# =============================================================================================
# Declaration (L / X / P parts); the weather part lives in cb2_weather
# =============================================================================================


def __getattr__(name: str):  # GROUPER_RULE_SHA256 is derived on access (it binds function source)
    if name == "GROUPER_RULE_SHA256":
        return grouper_rule_sha256()
    raise AttributeError(name)


def declaration_structural() -> dict:
    return {
        "version": VERSION,
        "dates": {"T2_dev_start": T2_DEV_START, "T2_dev_end": T2_DEV_END, "T2_rep_start_floor": T2_REP_START_FLOOR,
                  "rep_len_d": T2_REP_LEN_D, "T2_L_out_days_after_rep_end": T2_L_OUT_DAYS},
        "stage": {"alpha1": ALPHA_STAGE1, "alpha2": ALPHA_STAGE2, "min_clusters": MIN_CLUSTERS, "min_units": MIN_UNITS,
                  "rann_min": RANN_MIN, "cost_sens_per_leg": COST_SENS, "seed": SEED, "top_clusters_dropped": 5},
        "floors": FLOORS,
        "L": {"trigger_net": TRIGGER_NET, "gap_h": list(GAP_H), "depth_min_size": DEPTH_MIN_SIZE,
              "depth_min_clusters": DEPTH_MIN_CLUSTERS, "payoff_max_below1": PAYOFF_MAX_BELOW1,
              "payoff_min_determined": PAYOFF_MIN_DETERMINED, "persistence_draws": PERSISTENCE_DRAWS,
              "eligibility": ["closed==false", "active==true", "accepting_orders==1", "0<bid<ask<1", "volume_num>0",
                              "unknown flag => ineligible"],
              "position": "INC: YES later deadline, NO earlier; DEC: YES earlier, NO later; C = sum(ask+fee) per leg",
              "tests": {"L1": "mean net per trigger, within-event, executed at next capture, >0",
                        "X1": "same, cross-event", "X2": "stratified ladder-level fee-free touch-violation rate, cross minus within"},
              "X2": {"strata": "modal sidecar fee_category of the ladder's rungs; retained if >=1 cross and >=1 within",
                     "weights": "stratum share of retained cross ladders", "perm_draws": X2_PERM_DRAWS,
                     "placebo_draws": PLACEBO_DRAWS, "min_per_type": X2_MIN_PER_TYPE,
                     "p": "max(stratified normal z, within-stratum label permutation)"},
              "clusters": "ladder; capture day (two-way via battery.mean_test)",
              "audit": {"per_type": AUDIT_PER_TYPE, "gap_pairs": AUDIT_GAP, "max_not_genuine": AUDIT_MAX_NOT_GENUINE,
                        "seed": AUDIT_SEED}},
        "grouper": {"version": GROUPER_VERSION, "rule_sha256": grouper_rule_sha256(),
                    "cross_min_stem_tokens": CROSS_MIN_STEM_TOKENS},
        "P": P_GATE,
        "refused_run_ids": list(REFUSED_RUN_IDS),
        "text_batch": TEXT_BATCH,
        "rules": ["P gate reads no outcome column (final_yes dropped; events with a closed member are excluded and counted)",
                  "never traded = volume_num missing or 0 AND last_trade_price empty",
                  "L/X adjacency over rungs visible at the capture, independent of prices",
                  "depth gate: inconclusive blocks a replication verdict, a sign disagreement blocks a dev advance",
                  "X2 stratum cell variance with n=1 uses the pooled variance of that type"],
    }


def declaration_sha256_structural() -> str:
    return hashlib.sha256(json.dumps(declaration_structural(), sort_keys=True).encode()).hexdigest()


def require_declaration(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Committed ``model_specs/cb2_v1.json`` must carry ``structural_sha256`` equal to this code's hash. If it also
    carries ``weather_sha256`` and ``cb2_weather`` exposes ``declaration_sha256_weather`` they must match too."""
    path = Path(path) if path is not None else MODEL_SPEC_FILE
    if not path.exists():
        raise DeclarationError(f"no committed declaration at {path}; counted CB2 runs are refused")
    if require_committed and not _git_committed(path):
        raise DeclarationError(f"declaration {path} is not committed (or differs from HEAD)")
    rec = json.loads(path.read_text())
    cur = declaration_sha256_structural()
    if rec.get("structural_sha256") != cur:
        raise DeclarationError(f"structural declaration mismatch: committed {rec.get('structural_sha256')} != current {cur}")
    if rec.get("weather_sha256"):
        try:
            from . import cb2_weather  # noqa: PLC0415 - optional, owned by the weather module

            fn = getattr(cb2_weather, "declaration_sha256_weather", None)
        except ImportError:
            fn = None
        if fn is not None and fn() != rec["weather_sha256"]:
            raise DeclarationError("weather declaration mismatch")
    return cur


# =============================================================================================
# Question parsing and the grouper
# =============================================================================================


def parse_direction(question: str, created_at: str | None = None) -> dict:
    """Direction of a deadline phrase. Returns ``{"direction": "INC"|"DEC"|None, "reason": ..., "stem": ..., "deadline": epoch|None}``.
    "by/before D" -> INC (probability rises with D); "through/until D" (incl. "continue(s) through D") -> DEC; "on D", "in
    <month>", several dates, no keyword: excluded."""
    q = question or ""
    dates = list(if_h2.DATE_RE.finditer(q))
    if len(dates) != 1:
        return {"direction": None, "reason": "no_date" if not dates else "several_dates", "stem": "", "deadline": None}
    m = _PREFIX_RE.search(q[:dates[0].start()])
    if m is None:
        return {"direction": None, "reason": "no_keyword", "stem": "", "deadline": None}
    w = m.group(1).lower()
    if w in INC_WORDS:
        d = "INC"
    elif w in DEC_WORDS:
        d = "DEC"
    else:
        return {"direction": None, "reason": f"point_or_period_{w}", "stem": "", "deadline": None}
    dl = if_h2.parse_deadline(None, q, created_at)
    if dl is None:
        return {"direction": None, "reason": "no_deadline", "stem": "", "deadline": None}
    return {"direction": d, "reason": "ok", "stem": if_h2.stem(q), "deadline": float(dl)}


def mask_description(desc: str | None) -> str:
    d = if_h2.DATE_RE.sub(" datetoken ", desc or "")
    d = _MASK_YEAR_RE.sub(" yeartoken ", d)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", d.lower()).split())


def _idkey(mid: str) -> tuple[int, str]:
    return (int(mid) if str(mid).isdigit() else 0, str(mid))


def _sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def _dedupe_deadline(rungs: list[dict]) -> tuple[list[dict], int]:
    by: dict[float, dict] = {}
    dropped = 0
    for r in rungs:
        prev = by.get(r["deadline"])
        if prev is None:
            by[r["deadline"]] = r
        else:
            dropped += 1
            if _idkey(r["market_id"]) < _idkey(prev["market_id"]):
                by[r["deadline"]] = r
    return [by[k] for k in sorted(by)], dropped


def ladder_grouper_v2(markets: list[dict]) -> dict:
    """Deterministic direction-aware grouper (``GROUPER_VERSION``). ``markets``: dicts with ``market_id``, ``event_id``,
    ``question``, ``description``, ``created_at``. Metadata only (no price, no outcome). Returns
    ``{"ladders": [...], "counts": {...}}``; every exclusion is counted."""
    cnt: dict[str, int] = {"markets": len(markets), "parsed": 0, "dup_deadline_dropped": 0, "cross_event_multi_rung": 0,
                           "cross_empty_description": 0, "cross_short_stem": 0}
    rows = []
    for m in markets:
        p = parse_direction(m.get("question") or "", m.get("created_at"))
        if p["direction"] is None:
            cnt[f"excluded_{p['reason']}"] = cnt.get(f"excluded_{p['reason']}", 0) + 1
            continue
        cnt["parsed"] += 1
        rows.append({"market_id": str(m["market_id"]), "event_id": str(m["event_id"]), "question": m.get("question") or "",
                     "direction": p["direction"], "stem": p["stem"], "deadline": p["deadline"],
                     "desc_key": mask_description(m.get("description"))})
    ladders = []
    by_within: dict[tuple, list[dict]] = {}
    by_cross: dict[tuple, list[dict]] = {}
    for r in rows:
        by_within.setdefault((r["event_id"], r["direction"], r["stem"]), []).append(r)
        by_cross.setdefault((r["direction"], r["stem"], r["desc_key"]), []).append(r)
    for (ev, d, stem), rs in sorted(by_within.items()):
        rungs, dr = _dedupe_deadline(rs)
        cnt["dup_deadline_dropped"] += dr
        if len(rungs) >= 2:
            ladders.append({"ladder_id": f"L:{ev}:{_sha8(d + '|' + stem)}", "type": "L", "direction": d, "stem": stem,
                            "event_ids": [ev], "rungs": [_rung(x) for x in rungs]})
    for (d, stem, dk), rs in sorted(by_cross.items()):
        if len({r["event_id"] for r in rs}) < 2:
            continue
        if len(stem.split()) < CROSS_MIN_STEM_TOKENS:
            cnt["cross_short_stem"] += 1
            continue
        if not dk:
            cnt["cross_empty_description"] += 1
            continue
        per_ev: dict[str, list[dict]] = {}
        for r in rs:
            per_ev.setdefault(r["event_id"], []).append(r)
        single = [v[0] for v in per_ev.values() if len(v) == 1]
        cnt["cross_event_multi_rung"] += sum(1 for v in per_ev.values() if len(v) > 1)
        rungs, dr = _dedupe_deadline(single)
        cnt["dup_deadline_dropped"] += dr
        if len(rungs) >= 2 and len({r["event_id"] for r in rungs}) >= 2:
            ladders.append({"ladder_id": f"X:{d}:{_sha8(stem + '|' + dk)}", "type": "X", "direction": d, "stem": stem,
                            "event_ids": sorted({r["event_id"] for r in rungs}), "rungs": [_rung(x) for x in rungs]})
    ladders.sort(key=lambda L: L["ladder_id"])
    cnt["ladders_L"] = sum(1 for x in ladders if x["type"] == "L")
    cnt["ladders_X"] = sum(1 for x in ladders if x["type"] == "X")
    return {"ladders": ladders, "counts": cnt}


def _rung(r: dict) -> dict:
    return {"market_id": r["market_id"], "event_id": r["event_id"], "deadline": r["deadline"], "question": r["question"]}


# =============================================================================================
# Versioned ladder list
# =============================================================================================


def _content_sha(doc: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in doc.items() if k != "sha256"}, sort_keys=True).encode()).hexdigest()


def ladder_list(grouped: dict, *, version: int, listed_utc: str, prev: dict | None = None, universe: dict | None = None) -> dict:
    """Versioned list. v1 applies retrospectively to every dev capture from ``T2_dev_start`` (inclusive). v>=2 are
    additive and prospective: previous rungs and ladders are never altered or removed; a rung first added by version
    v is visible only to captures strictly after that version's ``listed_utc``. The sha256 covers the whole document."""
    if version == 1:
        if prev is not None:
            raise LadderListError("v1 has no predecessor")
        versions = [{"version": 1, "listed_utc": listed_utc, "visible_from_utc": T2_DEV_START, "strict": False}]
        base: dict[str, dict] = {}
    else:
        if prev is None or prev.get("version") != version - 1:
            raise LadderListError(f"v{version} needs v{version - 1} as its predecessor")
        if _ep(listed_utc) <= _ep(prev["versions"][-1]["listed_utc"]):
            raise LadderListError("listed_utc must increase")
        versions = [*prev["versions"], {"version": version, "listed_utc": listed_utc, "visible_from_utc": listed_utc, "strict": True}]
        base = {L["ladder_id"]: json.loads(json.dumps(L)) for L in prev["ladders"]}
    vis = versions[-1]
    for L in grouped["ladders"]:
        cur = base.get(L["ladder_id"])
        known = {r["market_id"] for r in cur["rungs"]} if cur else set()
        new = []
        for r in L["rungs"]:
            if r["market_id"] in known:
                continue
            new.append({**r, "added_version": version, "visible_from_utc": vis["visible_from_utc"], "strict": vis["strict"]})
        if cur is None:
            base[L["ladder_id"]] = {**{k: v for k, v in L.items() if k != "rungs"}, "rungs": new}
        elif new:
            cur["rungs"] = sorted([*cur["rungs"], *new], key=lambda r: r["deadline"])
            cur["event_ids"] = sorted(set(cur["event_ids"]) | set(L["event_ids"]))
    ladders = sorted(base.values(), key=lambda L: L["ladder_id"])
    for L in ladders:
        L["rungs"].sort(key=lambda r: (r["deadline"], _idkey(r["market_id"])))
    doc = {"kind": "cb2_ladder_list", "version": version, "listed_utc": listed_utc, "grouper": GROUPER_VERSION,
           "grouper_rule_sha256": grouper_rule_sha256(), "versions": versions, "universe": universe or {},
           "counts": grouped["counts"], "n_ladders": len(ladders),
           "n_rungs": sum(len(L["rungs"]) for L in ladders), "ladders": ladders,
           "rungs": [{"market_id": r["market_id"], "visible_from_utc": r["visible_from_utc"], "strict": r["strict"]}
                     for L in ladders for r in L["rungs"]]}
    doc["sha256"] = _content_sha(doc)
    return doc


def lineage_id() -> str:
    """One lineage per grouper-rule hash (freeze-check fix 3): a grouper revision starts a new v1 in its own directory,
    rebuilt from ``ladder_text_cache.jsonl``; the old lineage stays untouched."""
    return grouper_rule_sha256()[:12]


def lineage_dir(root: Path, lineage: str | None = None) -> Path:
    return Path(root) / "ladder_lists" / (lineage or lineage_id())


def lineage_versions(root: Path, lineage: str | None = None) -> list[Path]:
    d = lineage_dir(root, lineage)
    return sorted(d.glob("ladder_list_v*.json"), key=lambda p: int(p.stem.rsplit("_v", 1)[1])) if d.exists() else []


def find_ladder_list(root: Path, sha256: str) -> dict:
    """Load the list with this content hash from any lineage (the dev run is pinned to one version, not the head)."""
    root = Path(root)
    for p in [root / cb.LADDER_LIST_NAME, *sorted((root / "ladder_lists").glob("*/ladder_list_v*.json"))]:
        if p.exists():
            try:
                if json.loads(p.read_text()).get("sha256") == sha256:
                    return load_ladder_list(p, sha256)
            except ValueError:
                continue
    raise LadderListError(f"no ladder list with sha256 {sha256} under {root}")


def write_ladder_list(doc: dict, root: Path) -> str:
    """Immutable ``ladder_lists/<lineage>/ladder_list_v<n>.json`` plus the ``ladder_list.json`` head (+ ``.sha256``) the
    extractor reads."""
    root = Path(root)
    vp = lineage_dir(root, doc["grouper_rule_sha256"][:12]) / f"ladder_list_v{doc['version']}.json"
    if vp.exists():
        raise LadderListError(f"refusing to overwrite {vp}")
    vp.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(doc, indent=1, sort_keys=True)
    vp.write_text(txt)
    cur = root / cb.LADDER_LIST_NAME
    tmp = cur.with_suffix(".tmp")
    tmp.write_text(txt)
    tmp.replace(cur)
    cur.with_name(cb.LADDER_LIST_NAME + ".sha256").write_text(doc["sha256"] + "\n")
    return doc["sha256"]


def load_ladder_list(path: Path, expected_sha256: str | None = None) -> dict:
    path = forecast.require_local(Path(path))
    doc = json.loads(path.read_text())
    if _content_sha(doc) != doc.get("sha256"):
        raise LadderListError(f"{path}: sha256 field does not match its content")
    if expected_sha256 is not None and expected_sha256 != doc["sha256"]:
        raise LadderListError(f"{path}: sha256 {doc['sha256']} != committed {expected_sha256}")
    if doc.get("grouper_rule_sha256") != grouper_rule_sha256():
        raise LadderListError(f"{path}: built under another grouper rule hash")
    return doc


def rung_visible(rung: dict, capture_start_epoch: float) -> bool:
    t = _ep(rung["visible_from_utc"])
    return capture_start_epoch > t if rung["strict"] else capture_start_epoch >= t


def ladder_pairs(doc: dict) -> pd.DataFrame:
    """Adjacent-deadline pairs per list-version epoch (adjacency over the rungs visible in that epoch; never a function
    of prices). Epoch v covers captures in (listed_v, listed_{v+1}] (v1: [T2_dev_start, listed_2])."""
    vers = doc["versions"]
    rows = []
    for i, v in enumerate(vers):
        lo = _ep(v["visible_from_utc"])
        hi = _ep(vers[i + 1]["listed_utc"]) if i + 1 < len(vers) else math.inf
        for L in doc["ladders"]:
            rs = [r for r in L["rungs"] if r["added_version"] <= v["version"]]
            rs.sort(key=lambda r: (r["deadline"], _idkey(r["market_id"])))
            for a, b in zip(rs[:-1], rs[1:], strict=True):
                inc = L["direction"] == "INC"
                yes_m, no_m = (b, a) if inc else (a, b)
                rows.append({"pair_id": f"{L['ladder_id']}|{a['market_id']}|{b['market_id']}", "ladder_id": L["ladder_id"],
                             "ltype": L["type"], "direction": L["direction"], "m1": a["market_id"], "m2": b["market_id"],
                             "yes_m": yes_m["market_id"], "no_m": no_m["market_id"], "deadline1": a["deadline"],
                             "deadline2": b["deadline"], "epoch": v["version"], "t_lo": lo, "strict": bool(v["strict"]), "t_hi": hi})
    return pd.DataFrame(rows, columns=["pair_id", "ladder_id", "ltype", "direction", "m1", "m2", "yes_m", "no_m", "deadline1",
                                       "deadline2", "epoch", "t_lo", "strict", "t_hi"])


def audit_sample(doc: dict, *, per_type: int = AUDIT_PER_TYPE, seed: int = AUDIT_SEED, extra_pair_ids=()) -> dict:
    """Random ``per_type`` adjacent pairs per ladder type plus every pair in ``extra_pair_ids`` (census: pairs with an
    apparent gap >= 20c), printed with question text for labelling (``genuine`` is filled by the reviewer)."""
    pairs = ladder_pairs(doc)
    pairs = pairs[pairs["epoch"] == pairs["epoch"].max()] if len(pairs) else pairs
    q = {r["market_id"]: r["question"] for L in doc["ladders"] for r in L["rungs"]}
    rng = np.random.default_rng(seed)
    pick: list[str] = []
    for t in ("L", "X"):
        ids = sorted(pairs.loc[pairs["ltype"] == t, "pair_id"])
        k = min(per_type, len(ids))
        pick += [ids[i] for i in sorted(rng.choice(len(ids), size=k, replace=False))] if k else []
    extra = sorted(set(extra_pair_ids) - set(pick))
    idx = pairs.set_index("pair_id")
    rows = []
    for pid in [*pick, *extra]:
        if pid not in idx.index:
            continue
        r = idx.loc[pid]
        rows.append({"pair_id": pid, "type": r["ltype"], "direction": r["direction"], "q1": q[r["m1"]], "q2": q[r["m2"]],
                     "deadline1": r["deadline1"], "deadline2": r["deadline2"], "source": "random" if pid in pick else "gap_ge_20c",
                     "genuine": None})
    return {"seed": seed, "per_type": per_type, "n": len(rows), "pairs": rows}


def audit_verdict(labels: dict[str, bool]) -> dict:
    """Grouper audit gate: more than 5% not genuine -> the rules are revised and re-hashed before the freeze."""
    n = len(labels)
    bad = sum(1 for v in labels.values() if not v)
    return {"n": n, "not_genuine": bad, "share_not_genuine": bad / n if n else math.nan,
            "pass": bool(n > 0 and bad / n <= AUDIT_MAX_NOT_GENUINE)}


# =============================================================================================
# Network: question text (shared Limiter), universe from captures
# =============================================================================================


def fetch_question_text(ids: list[str], lim, *, batch: int = TEXT_BATCH, cache_path: Path | None = None,
                        max_requests: int | None = None) -> tuple[dict[str, dict], dict]:
    """Gamma ``/markets?id=`` metadata (question, description, createdAt, groupItemTitle). Uses the shared ``Limiter``
    (live-collector yield, 429 back-off). A jsonl cache makes a stopped run resumable. Returns (texts, report)."""
    cache: dict[str, dict] = {}
    if cache_path is not None and Path(cache_path).exists():
        for line in Path(cache_path).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r["market_id"]] = r
    todo = [i for i in dict.fromkeys(str(x) for x in ids) if i not in cache]
    used = errors = 0
    stopped = None
    fh = open(cache_path, "a", encoding="utf-8") if cache_path is not None else None  # noqa: SIM115
    try:
        for i in range(0, len(todo), batch):
            if max_requests is not None and used >= max_requests:
                stopped = "max_requests"
                break
            chunk = todo[i:i + batch]
            used += 1
            status, data = lim.get(hb.GAMMA_MARKETS, [("id", x) for x in chunk] + [("limit", batch)])
            if status != 200 or not isinstance(data, list):
                errors += 1
                continue
            got = {str(m.get("id")): m for m in data}
            for mid in chunk:
                m = got.get(mid)
                rec = ({"market_id": mid, "missing": True} if m is None else
                       {"market_id": mid, "question": m.get("question") or "", "description": m.get("description") or "",
                        "group_item_title": m.get("groupItemTitle") or "", "created_at": m.get("createdAt") or ""})
                cache[mid] = rec
                if fh is not None:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
            if fh is not None:
                fh.flush()
    finally:
        if fh is not None:
            fh.close()
    rep = {"requests": used, "errors": errors, "stopped": stopped, "n_ids": len(set(ids)),
           "n_missing": sum(1 for i in set(map(str, ids)) if cache.get(i, {}).get("missing")),
           "complete": stopped is None and all(str(i) in cache for i in ids)}
    return cache, rep


def _is_false(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower() == "false"


def universe_captures(snapshot_root: Path, since: str, now_latest: bool = True) -> list[dict]:
    """First complete capture at or after 12:00Z of each UTC day from ``since``, plus the latest complete capture."""
    caps = [c for c in forecast.list_complete_captures(snapshot_root) if c["_start"] >= pd.Timestamp(since).to_pydatetime()]
    first: dict[str, dict] = {}
    for c in caps:
        if c["_start"].hour >= 12:
            first.setdefault(c["_start"].strftime("%Y-%m-%d"), c)
    out = list(first.values())
    if now_latest and caps and caps[-1] not in out:
        out.append(caps[-1])
    return sorted(out, key=lambda c: c["_start"])


def read_universe(caps: list[dict]) -> tuple[pd.DataFrame, dict]:
    """market_id -> event_id for non-sports, non-weather, non-neg-risk, not-closed markets of the given captures.
    Reads ids, event ids and fee categories only (no price or outcome)."""
    parts = []
    rep = {"captures": 0, "no_sidecar": 0}
    for cap in caps:
        cdir = Path(cap["dir"])
        rows_p = forecast.require_local(cdir / "rows.csv.gz")
        ext_p = cdir / "rows_ext.csv.gz"
        if not ext_p.exists():
            rep["no_sidecar"] += 1
            continue
        ext = cb._read_ext_cols(ext_p, ["market_id", "fee_category"], [])
        cat = ext["fee_category"].astype(str).str.strip().str.lower().str.split(":").str[0]
        rep["captures"] += 1
        for ch in cb._chunks(rows_p, ["market_id", "event_id", "neg_risk_market_id", "closed"], []):
            nrm = ch["neg_risk_market_id"].fillna("").astype(str).str.strip()
            c = ch["market_id"].map(cat).fillna("")
            ok = (nrm == "") & _is_false(ch["closed"]) & ~c.isin(UNIVERSE_EXCLUDED_CATEGORIES)
            if ok.any():
                parts.append(ch.loc[ok, ["market_id", "event_id"]])
    df = (pd.concat(parts, ignore_index=True).drop_duplicates("market_id") if parts
          else pd.DataFrame(columns=["market_id", "event_id"]))
    rep["n_markets"] = int(len(df))
    return df, rep


# =============================================================================================
# Pair states, triggers, payoffs
# =============================================================================================

_SIDE_COLS = ["best_bid", "best_ask", "closed", "active", "accepting_orders", "volume_num", "fee_schedule", "fee_category",
              "sw1_best_bid", "sw1_best_ask", "sw1_bid_size_1", "sw1_ask_size_1", "end_date"]


def _fee_params(sched: pd.Series, cat: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    key = sched.fillna("").astype(str) + "\x1f" + cat.fillna("").astype(str)
    uniq = pd.unique(key)
    table = {k: c1.leg_rate(k.split("\x1f")[0] or None, k.split("\x1f")[1] or None) for k in uniq}
    r = key.map(lambda k: table[k][0]).to_numpy(float)
    e = key.map(lambda k: table[k][1]).to_numpy(float)
    return r, e


def fee_vec(price, rate, exp) -> np.ndarray:
    """Vector form of ``economics.taker_fee(1, p, rate, exp)``: same formula and the same Python ``round(., 5)`` (numpy's
    ``np.round`` differs from it on ties), equivalence-tested against ``economics.taker_fee``."""
    p = np.clip(np.asarray(price, float), 0.0, 1.0)
    raw = np.broadcast_to(rate * (p * (1.0 - p)) ** exp, p.shape)
    return np.array([round(float(x), economics.FEE_DECIMALS) for x in raw.ravel()], float).reshape(p.shape)


def _eligible(d: pd.DataFrame, sfx: str) -> np.ndarray:
    bid, ask = d[f"best_bid{sfx}"].to_numpy(float), d[f"best_ask{sfx}"].to_numpy(float)
    vol = pd.to_numeric(d[f"volume_num{sfx}"], errors="coerce").to_numpy(float)
    closed, act, acc = (c1._flag(d[f"{c}{sfx}"]) for c in ("closed", "active", "accepting_orders"))
    with np.errstate(invalid="ignore"):
        return (closed == 0) & (act == 1) & (acc == 1) & (bid > 0) & (ask > bid) & (ask < 1) & (vol > 0)


def pair_states(cands: pd.DataFrame, pairs: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per ELIGIBLE pair-capture (both rungs visible per the list-version rule, open, accepting, two-sided,
    ``volume_num > 0``). ``cands``: rung rows with ``capture_id``, ``cs`` and ``LADDER_COLUMNS``. Columns: ``C`` (cost of
    the dominance position at the touch, fees summed per leg), ``gap`` (fee-free ``bid(no) - ask(yes)``), ``viol``
    (``gap > 0``), sweep fields. No outcome is read."""
    cnt = {"pair_captures_visible": 0, "pair_captures_eligible": 0}
    cols = ["capture_id", "cs", "market_id", *_SIDE_COLS]
    c = cands.reindex(columns=cols)
    for k in ("market_id", "capture_id"):
        c[k] = c[k].astype(str)
    y = c.rename(columns={k: f"{k}_y" for k in _SIDE_COLS}).rename(columns={"market_id": "yes_m"})
    n = c[["capture_id", "market_id", *_SIDE_COLS]].rename(columns={k: f"{k}_n" for k in _SIDE_COLS}).rename(columns={"market_id": "no_m"})
    m = pairs.merge(y, on="yes_m").merge(n, on=["capture_id", "no_m"])
    if len(m):
        lo_ok = np.where(m["strict"], m["cs"] > m["t_lo"], m["cs"] >= m["t_lo"])
        m = m[lo_ok & (m["cs"] <= m["t_hi"])]
    cnt["pair_captures_visible"] = int(len(m))
    ok = _eligible(m, "_y") & _eligible(m, "_n") if len(m) else np.array([], bool)
    m = m[ok].copy()
    cnt["pair_captures_eligible"] = int(len(m))
    if not len(m):
        return pd.DataFrame(columns=["pair_id", "ladder_id", "ltype", "capture_id", "cs", "day", "C", "gap", "viol", "deadline2",
                                     "sweep_ok", "net_sweep", "fee_category_y", "fee_category_n", "yes_m", "no_m", "direction"]), cnt
    ry, ey = _fee_params(m["fee_schedule_y"], m["fee_category_y"])
    rn, en = _fee_params(m["fee_schedule_n"], m["fee_category_n"])
    a_y = m["best_ask_y"].to_numpy(float)
    a_n = 1.0 - m["best_bid_n"].to_numpy(float)
    m["C"] = a_y + fee_vec(a_y, ry, ey) + a_n + fee_vec(a_n, rn, en)
    m["gap"] = m["best_bid_n"].to_numpy(float) - m["best_ask_y"].to_numpy(float)
    m["viol"] = m["gap"] > 0
    sa, sb = m["sw1_best_ask_y"].to_numpy(float), m["sw1_best_bid_n"].to_numpy(float)
    sz = np.minimum(m["sw1_ask_size_1_y"].to_numpy(float), m["sw1_bid_size_1_n"].to_numpy(float))
    sn = 1.0 - sb
    with np.errstate(invalid="ignore"):
        sw_ok = np.isfinite(sa) & np.isfinite(sb) & (sz >= DEPTH_MIN_SIZE)
    m["sweep_ok"] = sw_ok
    m["net_sweep"] = np.where(sw_ok, 1.0 - (sa + fee_vec(sa, ry, ey) + sn + fee_vec(sn, rn, en)), np.nan)
    m["day"] = pd.to_datetime(m["cs"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    keep = ["pair_id", "ladder_id", "ltype", "capture_id", "cs", "day", "C", "gap", "viol", "deadline2", "sweep_ok", "net_sweep",
            "fee_category_y", "fee_category_n", "yes_m", "no_m", "direction"]
    return m[keep].reset_index(drop=True), cnt


def pair_payoff(direction: str, y1: float, y2: float) -> float:
    """Payoff of the dominance position for final YES values of the earlier (1) and later (2) rung.
    INC: YES on the later, NO on the earlier. DEC: YES on the earlier, NO on the later. Structural minimum 1 in every
    logically consistent state; a value below 1 is an inconsistent resolution."""
    return (y2 + (1.0 - y1)) if direction == "INC" else (y1 + (1.0 - y2))


def realised_pair_payoff(direction: str, y1: float, y2: float) -> tuple[float, float, bool | None]:
    """(lo, hi, below1): payoff bounds when a final value is unknown (NaN -> [0, 1]); ``below1`` is None if undetermined."""
    def span(y):
        return (0.0, 1.0) if math.isnan(y) else (y, y)
    (a1, b1), (a2, b2) = span(y1), span(y2)
    if direction == "INC":
        lo, hi = a2 + (1.0 - b1), b2 + (1.0 - a1)
    else:
        lo, hi = a1 + (1.0 - b2), b1 + (1.0 - a2)
    below = True if hi < 1.0 - 1e-9 else (False if lo >= 1.0 - 1e-9 else None)
    return lo, hi, below


def lx_triggers(ps: pd.DataFrame, nxt: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """One row per trigger (``1 - C(c) >= 0.5c`` at an eligible origin capture with a kept next capture). Execution at
    the next complete capture (gap in [1.5, 3] h) at ``C(c')`` if both rungs are still eligible there; otherwise no trade
    (net 0, kept in the denominator)."""
    cnt = {"triggers": 0, "no_next_or_gap": 0, "executed": 0, "no_trade": 0}
    cols = ["pair_id", "ladder_id", "ltype", "capture_id", "exec_capture_id", "day", "C0", "executed", "net", "K", "d", "sweep_ok",
            "net_sweep", "yes_m", "no_m", "direction"]
    if not len(ps):
        return pd.DataFrame(columns=cols), cnt
    t = ps[(1.0 - ps["C"]) >= TRIGGER_NET - 1e-12]
    idx = ps.set_index(["pair_id", "capture_id"])
    rows = []
    for r in t.itertuples(index=False):
        j = nxt.get(r.capture_id)
        if j is None:
            cnt["no_next_or_gap"] += 1
            continue
        cnt["triggers"] += 1
        base = {"pair_id": r.pair_id, "ladder_id": r.ladder_id, "ltype": r.ltype, "capture_id": r.capture_id,
                "exec_capture_id": j, "day": r.day, "C0": r.C, "yes_m": r.yes_m, "no_m": r.no_m, "direction": r.direction}
        e = idx.loc[(r.pair_id, j)] if (r.pair_id, j) in idx.index else None
        if e is None:
            cnt["no_trade"] += 1
            rows.append({**base, "executed": False, "net": 0.0, "K": 0.0, "d": math.nan, "sweep_ok": False, "net_sweep": math.nan})
            continue
        cnt["executed"] += 1
        rows.append({**base, "executed": True, "net": 1.0 - float(e["C"]), "K": float(e["C"]),
                     "d": (float(e["deadline2"]) - float(e["cs"])) / 86400.0, "sweep_ok": bool(e["sweep_ok"]),
                     "net_sweep": float(e["net_sweep"])})
    return pd.DataFrame(rows, columns=cols), cnt


# =============================================================================================
# Tests: L1 / X1 (economic), X2 (mechanism), diagnostics
# =============================================================================================


def lx_gate(trig: pd.DataFrame, *, floor: float, alpha: float, n_boot: int, dev: bool, seed: int = SEED) -> dict:
    """mean net per trigger with the Stage gate (CB1 ``mean_gate``: p<alpha, floor, R_ann>=10%, +0.75c per bought leg
    keeps net>0, still passes without the top 5 ladders, leave-one-day-out in dev) plus the cluster-equal-weighted
    sign agreement (robustness iii)."""
    if not len(trig):
        return {"testable": False, "p": 1.0, "advance": False, "n": 0, "n_event": 0, "reason": "no triggers"}
    net = trig["net"].to_numpy(float)
    res = c1.mean_gate(net, trig["ladder_id"], trig["day"], floor=floor, alpha=alpha, n_boot=n_boot, seed=seed,
                       r_ann=c1.r_ann_of(net, trig["K"].to_numpy(float), trig["d"].to_numpy(float)), need_rann=True,
                       cost_add=np.full(len(trig), 2 * COST_SENS), lodo=dev, min_clusters=MIN_CLUSTERS, min_units=MIN_UNITS)
    if res.get("testable"):
        ceq = float(trig.groupby("ladder_id")["net"].mean().mean())
        res["cluster_equal_mean"] = ceq
        res["weighted_sign_agrees"] = bool(np.sign(ceq) == np.sign(res["mean"]) and ceq > 0)
        res["n_executed"] = int(trig["executed"].sum())
        if not res["weighted_sign_agrees"]:
            res["advance"] = False
    return res


def depth_gate(trig: pd.DataFrame) -> dict:
    """Recompute on triggers whose two legs were swept with size >= 5 at the next pass; must agree in sign (net > 0)."""
    sub = trig[trig["executed"] & trig["sweep_ok"]] if len(trig) else trig
    ncl = int(sub["ladder_id"].nunique()) if len(sub) else 0
    if ncl < DEPTH_MIN_CLUSTERS:
        return {"status": "inconclusive (depth unverified)", "n": int(len(sub)), "n_ladders": ncl}
    m = float(sub["net_sweep"].mean())
    return {"status": "ok" if m > 0 else "fail", "n": int(len(sub)), "n_ladders": ncl, "mean_net_sweep": m}


def payoff_gate(trig: pd.DataFrame, final_yes: dict[str, float]) -> dict:
    """Realised payoff gate (rep): share of determined, unique triggered pairs with payoff < 1 must be <= 2%."""
    sub = trig[trig["executed"]].drop_duplicates("pair_id") if len(trig) else trig  # per unique pair (CB1 fix 10)
    n_det = n_bad = 0
    nets = []
    for r in sub.itertuples(index=False):
        a = final_yes.get(str(r.no_m if r.direction == "INC" else r.yes_m), math.nan)  # earlier rung
        b = final_yes.get(str(r.yes_m if r.direction == "INC" else r.no_m), math.nan)  # later rung
        lo, hi, below = realised_pair_payoff(r.direction, a, b)
        if below is None:
            continue
        n_det += 1
        n_bad += int(below)
        if lo == hi:
            nets.append(lo - r.K)
    if n_det < PAYOFF_MIN_DETERMINED:
        return {"status": "inconclusive (payoff unverified)", "n_determined": n_det, "n_below1": n_bad}
    share = n_bad / n_det
    return {"status": "ok" if share <= PAYOFF_MAX_BELOW1 else "fail", "n_determined": n_det, "n_below1": n_bad,
            "share_below1": share, "mean_realised_net_exact": float(np.mean(nets)) if nets else math.nan, "n_exact": len(nets)}


def persistence_diagnostic(ps: pd.DataFrame, trig: pd.DataFrame, *, draws: int = PERSISTENCE_DRAWS, seed: int = SEED + 1) -> dict:
    """Replace each trigger's execution capture by a random OTHER eligible capture of the same pair and report the
    distribution of the mean net. A persistence diagnostic, NOT a null: a misgrouped pair's fake violation persists in
    every capture, so it cannot detect misgrouping (guards: grouper audit, realised-payoff gate)."""
    if not len(trig):
        return {"draws": draws, "n_triggers": 0}
    byp = {p: g[["capture_id", "C"]] for p, g in ps.groupby("pair_id")}
    cands = []
    for r in trig.itertuples(index=False):
        g = byp.get(r.pair_id)
        cands.append(g.loc[g["capture_id"] != r.capture_id, "C"].to_numpy(float) if g is not None else np.array([]))
    rng = np.random.default_rng(seed)
    means = np.empty(draws)
    for i in range(draws):
        tot = 0.0
        for c in cands:
            if len(c):
                tot += 1.0 - c[rng.integers(len(c))]
        means[i] = tot / len(cands)
    actual = float(trig["net"].mean())
    return {"draws": draws, "n_triggers": int(len(trig)), "actual_mean_net": actual, "mean_of_means": float(means.mean()),
            "q05": float(np.quantile(means, 0.05)), "q50": float(np.quantile(means, 0.5)), "q95": float(np.quantile(means, 0.95)),
            "share_draws_ge_actual": float((means >= actual).mean()), "is_null": False}


def ladder_rates(ps: pd.DataFrame, exclude_day: str | None = None) -> pd.DataFrame:
    """One row per ladder: share of its eligible pair-captures with a fee-free touch violation, ltype and the modal
    sidecar fee category of its rungs (stratum). Each ladder counts once however many pairs or captures it has."""
    d = ps if exclude_day is None else ps[ps["day"] != exclude_day]
    if not len(d):
        return pd.DataFrame(columns=["ladder_id", "ltype", "v", "n_pc", "stratum"])
    g = d.groupby("ladder_id").agg(ltype=("ltype", "first"), v=("viol", "mean"), n_pc=("viol", "size"))
    cat = pd.concat([ps[["ladder_id", "fee_category_y"]].rename(columns={"fee_category_y": "c"}),
                     ps[["ladder_id", "fee_category_n"]].rename(columns={"fee_category_n": "c"})])
    cat["c"] = cat["c"].fillna("unknown").astype(str).str.split(":").str[0].replace("", "unknown")
    modal = cat.groupby("ladder_id")["c"].agg(lambda s: sorted(s.value_counts().loc[lambda v: v == v.max()].index)[0])
    g["stratum"] = modal.reindex(g.index).fillna("unknown")
    return g.reset_index()


def _x2_cells(u: pd.DataFrame) -> tuple[list[dict], dict]:
    """Strata with >= 1 cross (type X) and >= 1 within (type L) ladder; dropped ladders are counted."""
    cells, dropped = [], {"strata_dropped": 0, "ladders_dropped": 0}
    var_all = {t: float(u.loc[u["ltype"] == t, "v"].var(ddof=1)) if (u["ltype"] == t).sum() > 1 else 0.0 for t in ("X", "L")}
    n_cross_total = 0
    for s, g in u.groupby("stratum"):
        c, w = g.loc[g["ltype"] == "X", "v"].to_numpy(float), g.loc[g["ltype"] == "L", "v"].to_numpy(float)
        if len(c) < 1 or len(w) < 1:
            dropped["strata_dropped"] += 1
            dropped["ladders_dropped"] += int(len(g))
            continue
        n_cross_total += len(c)
        vc = float(c.var(ddof=1)) if len(c) > 1 else var_all["X"]
        vw = float(w.var(ddof=1)) if len(w) > 1 else var_all["L"]
        cells.append({"stratum": s, "c": c, "w": w, "n_c": len(c), "n_w": len(w), "var_c": vc, "var_w": vw})
    for ce in cells:
        ce["wt"] = ce["n_c"] / n_cross_total
    return cells, dropped


def _x2_delta(cells: list[dict]) -> tuple[float, float]:
    delta = sum(ce["wt"] * (ce["c"].mean() - ce["w"].mean()) for ce in cells)
    var = sum(ce["wt"] ** 2 * (ce["var_c"] / ce["n_c"] + ce["var_w"] / ce["n_w"]) for ce in cells)
    return float(delta), float(var)


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def x2_estimate(u: pd.DataFrame, *, perm_draws: int = X2_PERM_DRAWS, seed: int = SEED, do_perm: bool = True) -> dict:
    """Stratified ladder-level difference ``sum_s w_s (mean_cross,s v - mean_within,s v)``; p = max(stratified normal z,
    within-stratum label permutation of the same estimator)."""
    cells, dropped = _x2_cells(u)
    n_c = sum(ce["n_c"] for ce in cells)
    n_w = sum(ce["n_w"] for ce in cells)
    out = {"n_cross": int(n_c), "n_within": int(n_w), "n_strata": len(cells), **dropped}
    if n_c < X2_MIN_PER_TYPE or n_w < X2_MIN_PER_TYPE:
        return {**out, "testable": False, "p": 1.0, "reason": f"not testable (cross={n_c}, within={n_w} < {X2_MIN_PER_TYPE})"}
    delta, var = _x2_delta(cells)
    se = math.sqrt(var)
    z = delta / se if se > 0 else 0.0
    p_z = _norm_sf(z)
    p_perm = math.nan
    if do_perm:
        rng = np.random.default_rng(seed)
        ge = 0
        for _ in range(perm_draws):
            tot = 0.0
            for ce in cells:
                pool = np.concatenate([ce["c"], ce["w"]])
                pool = pool[rng.permutation(len(pool))]
                tot += ce["wt"] * (pool[:ce["n_c"]].mean() - pool[ce["n_c"]:].mean())
            ge += int(tot >= delta - 1e-12)
        p_perm = (1 + ge) / (1 + perm_draws)
    p = max(p_z, p_perm) if do_perm else p_z
    return {**out, "testable": True, "mean": delta, "se": se, "z": z, "p_z": p_z, "p_perm": p_perm, "p": p}


def x2_placebo(u: pd.DataFrame, *, floor: float, alpha: float, draws: int = PLACEBO_DRAWS, seed: int = SEED + 2) -> dict:
    """Within-stratum label permutation placebo (same strata as the estimator): advance rate must be <= 1.5%.
    Each draw uses the stratified-z gate and the floor (the permutation p of a permuted label is uniform by design)."""
    rng = np.random.default_rng(seed)
    adv = 0
    for _ in range(draws):
        v = u.copy()
        for _s, idx in v.groupby("stratum").groups.items():
            lab = v.loc[idx, "ltype"].to_numpy()
            v.loc[idx, "ltype"] = lab[rng.permutation(len(lab))]
        r = x2_estimate(v, do_perm=False)
        adv += int(r.get("testable", False) and r["p"] < alpha and r["mean"] >= floor)
    return {"draws": draws, "n_advance": adv, "advance_rate": adv / max(draws, 1),
            "calibrated": adv / max(draws, 1) <= PLACEBO_MAX_ADVANCE_RATE}


def x2_tests(ps: pd.DataFrame, *, alpha: float, dev: bool, n_perm: int = X2_PERM_DRAWS, placebo_draws: int = PLACEBO_DRAWS,
             seed: int = SEED) -> tuple[dict, dict]:
    """X2 with its binding gates: p<alpha, floor +1pp, placebo calibrated, still passes without the top 5 ladders,
    and (dev) every leave-one-day-out estimate > 0."""
    u = ladder_rates(ps)
    base = x2_estimate(u, perm_draws=n_perm, seed=seed)
    if not base["testable"]:
        return {**base, "advance": False, "alpha": alpha, "floor": FLOORS["X2"]}, {}
    pl = x2_placebo(u, floor=FLOORS["X2"], alpha=alpha, draws=placebo_draws, seed=seed + 2)
    cells, _ = _x2_cells(u)
    contrib = {}
    for ce in cells:
        s = u[u["stratum"] == ce["stratum"]]
        for r in s.itertuples(index=False):
            if r.ltype == "X":
                contrib[r.ladder_id] = abs(ce["wt"] * (r.v - ce["c"].mean()) / ce["n_c"])
            else:
                contrib[r.ladder_id] = abs(ce["wt"] * (r.v - ce["w"].mean()) / ce["n_w"])
    top5 = set(sorted(contrib, key=contrib.get, reverse=True)[:5])
    t5 = x2_estimate(u[~u["ladder_id"].isin(top5)], do_perm=False)
    t5_ok = bool(t5.get("testable") and t5["p"] < alpha and t5["mean"] >= FLOORS["X2"])
    lodo = None
    if dev:
        lodo = {}
        for d in sorted(ps["day"].unique()):
            r = x2_estimate(ladder_rates(ps, exclude_day=d), do_perm=False)
            lodo[d] = r.get("mean", math.nan) if r.get("testable") else math.nan
    ok = bool(base["p"] < alpha and base["mean"] >= FLOORS["X2"] and pl["calibrated"] and t5_ok)
    if lodo is not None:
        ok = ok and all(v > 0 for v in lodo.values())
    return ({**base, "alpha": alpha, "floor": FLOORS["X2"], "without_top5_ladders": {"mean": t5.get("mean"), "p": t5.get("p"), "ok": t5_ok},
             "leave_one_day_out": lodo, "placebo_calibrated": pl["calibrated"], "advance": ok}, {"X2": pl})


# =============================================================================================
# Capture lists, windows, loading
# =============================================================================================


def pin_rep_start(freeze_commit: str, commit_time_iso: str, path: Path | None = None) -> dict:
    """Write the committed T2_rep_start pin once: ``max(floor, freeze commit time + 2h)``."""
    path = Path(path) if path is not None else T2_REP_START_FILE
    if path.exists():
        raise RepStartError(f"{path} exists; T2_rep_start is pinned once")
    sha = str(freeze_commit).strip().lower()
    if not (7 <= len(sha) <= 64) or any(c not in "0123456789abcdef" for c in sha):
        raise RepStartError(f"not a commit sha: {freeze_commit!r}")
    start = max(_ep(T2_REP_START_FLOOR), _ep(commit_time_iso) + 7200.0)
    doc = {"version": VERSION, "freeze_commit": sha, "t2_rep_start_floor": T2_REP_START_FLOOR, "t2_rep_start": _iso_z(start),
           "t2_rep_end": _iso_z(start + T2_REP_LEN_D * 86400.0),
           "rule": "max(floor, freeze commit time + 2h); the rep capture list from_utc must equal t2_rep_start"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return doc


def load_pinned_rep_start(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else T2_REP_START_FILE
    if not path.exists():
        raise RepStartError(f"no pinned T2_rep_start at {path}")
    doc = json.loads(path.read_text())
    if _ep(doc["t2_rep_start"]) < _ep(T2_REP_START_FLOOR):
        raise RepStartError("pinned T2_rep_start is before the declared floor")
    return doc


def window_bounds(window: str, pin_path: Path | None = None) -> tuple[float, float]:
    if window == "dev":
        return _ep(T2_DEV_START), _ep(T2_DEV_END)
    if window == "rep":
        p = load_pinned_rep_start(pin_path)
        return _ep(p["t2_rep_start"]), _ep(p["t2_rep_start"]) + T2_REP_LEN_D * 86400.0
    raise WindowError(f"unknown window {window!r}")


def check_window_allowed(window: str, now: datetime | None = None, pin_path: Path | None = None) -> None:
    """``rep`` is refused before T2_rep_end."""
    if window == "rep":
        _lo, hi = window_bounds("rep", pin_path)
        if (now or datetime.now(UTC)).timestamp() < hi:
            raise TooEarlyError(f"window rep is refused before T2_rep_end {_iso_z(hi)}")


def table_for_window(window: str) -> str:
    return "ladder_candidates" if window == "dev" else "ladders"


def freeze_cb2_list(window: str, root: Path, *, now: datetime | None = None, pin_path: Path | None = None) -> dict:
    """Write ``capture_lists/cb2_<window>.json`` from the cb2 extract manifest: captures inside the window whose window
    table is written. An existing list may only be extended. ``final`` once the window has ended."""
    root = Path(root)
    lo, hi = window_bounds(window, pin_path)
    tbl = table_for_window(window)
    man = json.loads(forecast.require_local(root / "manifest.json").read_text()).get("captures", {})
    ents = {cid: e for cid, e in man.items() if e.get("started_utc") and lo <= _ep(e["started_utc"]) < hi}
    ids = sorted(ents)
    missing = sorted(i for i in ids if ents[i].get(tbl, {}).get("status") != "written")
    path = root / "capture_lists" / f"cb2_{window}.json"
    if path.exists():
        prev = json.loads(path.read_text())
        if set(prev["capture_ids"]) - set(ids):
            raise CaptureListError(f"{path.name}: an existing list can only be extended")
    doc = {"kind": f"cb2_{window}", "table": tbl, "from_utc": _iso_z(lo), "until": _iso_z(hi), "capture_ids": ids, "n": len(ids),
           "final": bool((now or datetime.now(UTC)).timestamp() >= hi), "sha256": cb.ids_sha256(ids), "missing_ids": missing,
           "created_utc": cb.utc_now()}
    cb._atomic_write_json(path, doc)
    return doc


def load_cb2_list(root: Path, window: str, expected_sha256: str | None) -> dict:
    d = cb.load_capture_list(Path(root), f"cb2_{window}")
    if expected_sha256 is None or d["sha256"] != expected_sha256:
        raise CaptureListError(f"list sha256 {d['sha256']} != committed {expected_sha256}")
    if not d.get("final"):
        raise CaptureListError("list is not final (window not complete)")
    lo, hi = window_bounds(window)
    if _ep(d["from_utc"]) != lo or _ep(d["until"]) != hi:
        raise CaptureListError(f"list window [{d['from_utc']}, {d['until']}) != declared window")
    return d


def load_candidates(root: Path, cl: dict, window: str, listed_ids: set[str]) -> tuple[pd.DataFrame, dict[str, float], dict]:
    """Rung rows of the listed captures, restricted to rungs in the ladder list (the table is read whole per capture and
    filtered). A listed capture that is a ``missing_id`` is counted and skipped; any other without a table raises."""
    man = json.loads(forecast.require_local(Path(root) / "manifest.json").read_text()).get("captures", {})
    skip = set(cl.get("missing_ids", []))
    lo, hi = window_bounds(window)
    cs_by: dict[str, float] = {}
    parts = []
    tbl = table_for_window(window)
    for cid in cl["capture_ids"]:
        if cid in skip:
            continue
        st = _ep(man[cid]["started_utc"])
        if not (lo <= st < hi):
            raise WindowError(f"capture {cid} outside window {window}")
        cs_by[cid] = st
        d = pd.read_csv(forecast.require_local(Path(root) / tbl / f"{cid}.csv.gz"), dtype={"market_id": str, "event_id": str, "capture_id": str})
        d = d[d["market_id"].isin(listed_ids)].copy()
        d["cs"] = st
        d["capture_id"] = cid
        parts.append(d)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["capture_id", "cs", "market_id"])
    return df, cs_by, {"listed": len(cl["capture_ids"]), "missing_listed": len(skip), "loaded": len(cs_by)}


# =============================================================================================
# Orchestration
# =============================================================================================


def build_lx(root: Path, cl: dict, doc: dict, window: str) -> dict:
    listed = {r["market_id"] for L in doc["ladders"] for r in L["rungs"]}
    cands, cs_by, ccount = load_candidates(root, cl, window, listed)
    pairs = ladder_pairs(doc)
    ps, pcount = pair_states(cands, pairs)
    nxt, gcount = c1.next_capture_pairs(cs_by, GAP_H)
    trig, tcount = lx_triggers(ps, nxt)
    return {"ps": ps, "trig": trig, "counts": {"captures": ccount, "pairs": pcount, "gap_filter": gcount, "triggers": tcount,
                                               "n_pairs_listed": int(pairs["pair_id"].nunique()) if len(pairs) else 0,
                                               "n_ladders": int(doc["n_ladders"])}}


def run_lx(root: Path, cl: dict, doc: dict, window: str, *, n_boot: int, tests: tuple[str, ...] = ("L1", "X1", "X2"),
           final_yes: dict[str, float] | None = None, n_perm: int = X2_PERM_DRAWS, placebo_draws: int = PLACEBO_DRAWS
           ) -> tuple[dict, dict]:
    dev = window == "dev"
    alpha = ALPHA_STAGE1 if dev else ALPHA_STAGE2
    b = build_lx(root, cl, doc, window)
    ps, trig = b["ps"], b["trig"]
    out: dict = {"window": window, "stage": 1 if dev else 2, "counts": b["counts"], "tests": {}, "placebo": {}, "gates": {}}
    for name, typ in (("L1", "L"), ("X1", "X")):
        if name not in tests:
            continue
        sub = trig[trig["ltype"] == typ]
        r = lx_gate(sub, floor=FLOORS[name], alpha=alpha, n_boot=n_boot, dev=dev)
        dg = depth_gate(sub)
        out["gates"][name] = {"depth": dg}
        if dg["status"] == "fail":
            r["advance"] = False
        if not dev:
            pg = payoff_gate(sub, final_yes or {}) if final_yes is not None else {"status": "not evaluated (no outcomes)"}
            out["gates"][name]["payoff"] = pg
            r["replicated"] = bool(r.get("advance") and dg["status"] == "ok" and pg["status"] == "ok")
        r["depth_status"] = dg["status"]
        out["tests"][name] = r
    if "X2" in tests:
        r, pl = x2_tests(ps, alpha=alpha, dev=dev, n_perm=n_perm, placebo_draws=placebo_draws)
        out["tests"]["X2"] = r
        out["placebo"].update(pl)
    out["persistence_diagnostic"] = {t: persistence_diagnostic(ps, trig[trig["ltype"] == t]) for t in ("L", "X")}
    out["n_ladders_with_triggers"] = {t: int(trig.loc[trig["ltype"] == t, "ladder_id"].nunique()) for t in ("L", "X")}
    return out, b


def census_lx(root: Path, cl: dict, doc: dict) -> dict:
    """Counts only (no outcome): ladders, pairs, pair-captures, triggers per type, X2 strata sizes, and the audit sample
    including every pair with an apparent touch gap >= 20c."""
    b = build_lx(root, cl, doc, "dev")
    ps, trig = b["ps"], b["trig"]
    u = ladder_rates(ps)
    cells, dropped = _x2_cells(u) if len(u) else ([], {})
    big = sorted(set(ps.loc[ps["gap"] >= AUDIT_GAP, "pair_id"])) if len(ps) else []
    types = {}
    for t in ("L", "X"):
        s = ps[ps["ltype"] == t] if len(ps) else ps
        tr = trig[trig["ltype"] == t] if len(trig) else trig
        types[t] = {"ladders_in_list": sum(1 for L in doc["ladders"] if L["type"] == t),
                    "ladders_with_pair_capture": int(s["ladder_id"].nunique()) if len(s) else 0,
                    "eligible_pair_captures": int(len(s)),
                    "triggers": int(len(tr)), "trigger_ladders": int(tr["ladder_id"].nunique()) if len(tr) else 0,
                    "executed": int(tr["executed"].sum()) if len(tr) else 0}
    return {"counts_only": True, **b["counts"], "types": types,
            "x2_strata": [{"stratum": ce["stratum"], "n_cross": ce["n_c"], "n_within": ce["n_w"]} for ce in cells], "x2_dropped": dropped,
            "n_pairs_gap_ge_20c": len(big), "audit": audit_sample(doc, extra_pair_ids=big)}


# =============================================================================================
# CB2-P placeholder gate (counts only; no P1 code)
# =============================================================================================


def never_traded(volume_num, last_trade_price) -> np.ndarray:
    """Blank/zero ``volume_num`` AND empty ``last_trade_price``. A blank volume with a last trade is NOT never traded."""
    v = pd.to_numeric(pd.Series(volume_num), errors="coerce").to_numpy(float)
    ltp = pd.to_numeric(pd.Series(last_trade_price), errors="coerce").to_numpy(float)
    return (np.isnan(v) | (v == 0)) & np.isnan(ltp)


def placeholder_setups(g: pd.DataFrame, n_members: int | None) -> tuple[list[dict], str]:
    """Setups of one event-capture: exactly one never-traded member u, all others traded and two-sided. Events with a
    closed member are excluded (classifying a closed member needs an outcome; the gate reads none)."""
    g = g.drop_duplicates("market_id")
    if n_members is None:
        return [], "no_member_count"
    if not c1.member_complete(len(g), n_members):
        return [], "member_count_mismatch"
    if not (P_GATE["open_members"][0] <= len(g) <= P_GATE["open_members"][1]):
        return [], "member_count_range"
    aug, oth = c1._flag(g["event_neg_risk_augmented"]), c1._flag(g["neg_risk_other"])
    if np.any(np.isnan(aug)) or np.any(aug != 0):
        return [], "augmented"
    if np.any(np.isnan(oth)) or np.any(oth != 0):
        return [], "other"
    cl, act, acc = c1._flag(g["closed"]), c1._flag(g["active"]), c1._flag(g["accepting_orders"])
    if np.any(np.isnan(cl)) or np.any(cl != 0):
        return [], "closed_member"
    if np.any(act != 1) or np.any(acc != 1):
        return [], "member_not_open"
    nt = never_traded(g["volume_num"], g["last_trade_price"])
    if nt.sum() != 1:
        return [], "not_exactly_one_never_traded"
    bid, ask = g["best_bid"].to_numpy(float), g["best_ask"].to_numpy(float)
    oth_m = ~nt
    with np.errstate(invalid="ignore"):
        if not np.all((bid[oth_m] > 0) & (ask[oth_m] > bid[oth_m]) & (ask[oth_m] < 1)):
            return [], "others_not_two_sided"
    fair = float(np.clip(1.0 - ((bid[oth_m] + ask[oth_m]) / 2.0).sum(), 0.0, 1.0))
    i = int(np.flatnonzero(nt)[0])
    gaps = []
    if np.isfinite(ask[i]) and 0 < ask[i] < 1:
        gaps.append(fair - float(ask[i]))
    if np.isfinite(bid[i]) and bid[i] > 0:
        gaps.append(float(bid[i]) - fair)
    if not gaps:
        return [], "placeholder_no_quote"
    return [{"u": str(g["market_id"].iloc[i]), "fair": fair, "gap": max(gaps)}], "ok"


def placeholder_gate(df: pd.DataFrame, members, *, days: int | None = None) -> dict:
    """Counts only. ``df``: negrisk rows with ``capture_id``, ``cs``, ``neg_risk_market_id`` (the ``final_yes`` outcome
    column is dropped on entry). Pass iff >= 2 unique (event, u) setups per day with gap >= 5c on average over the window
    from >= 30 distinct events; otherwise CH10 is closed "not testable"."""
    if "final_yes" in df.columns:
        df = df.drop(columns=["final_yes"])
    reasons: dict[str, int] = {}
    rows = []
    cdays = set()
    if len(df):
        for (cid, gid), g in df.groupby(["capture_id", "neg_risk_market_id"], sort=False):
            cs0 = float(g["cs"].iloc[0])
            cdays.add(datetime.fromtimestamp(cs0, UTC).strftime("%Y-%m-%d"))
            mem = members(cs0) if callable(members) else members
            res, why = placeholder_setups(g, mem.get(str(gid)))
            reasons[why] = reasons.get(why, 0) + 1
            for s in res:
                rows.append({"capture_id": cid, "day": datetime.fromtimestamp(cs0, UTC).strftime("%Y-%m-%d"), "gid": str(gid), **s})
    st = pd.DataFrame(rows, columns=["capture_id", "day", "gid", "u", "fair", "gap"])
    big = st[st["gap"] >= P_GATE["min_gap"] - 1e-12]
    n_days = days if days is not None else len(cdays)
    uniq_day = big.drop_duplicates(["day", "gid", "u"])
    per_day = float(len(uniq_day) / n_days) if n_days else 0.0
    n_events = int(big["gid"].nunique()) if len(big) else 0
    return {"counts_only": True, "reads_outcomes": False, "n_days": int(n_days), "ineligible_reasons": reasons,
            "n_setups_all_gaps": int(len(st.drop_duplicates(['day', 'gid', 'u']))),
            "unique_setups_gap_ge_5c": int(len(big.drop_duplicates(["gid", "u"]))), "setups_per_day_gap_ge_5c": per_day,
            "distinct_events_gap_ge_5c": n_events, "events_with_closed_member_excluded": int(reasons.get("closed_member", 0)),
            "note": "upper-bound exclusions: events with a closed member are not evaluated (no outcome read), so counts are lower bounds on that axis",
            "gate_pass": bool(per_day >= P_GATE["min_setups_per_day"] and n_events >= P_GATE["min_events"])}


def census_p(extract_root: Path) -> dict:
    """P gate over CB1 extract ``negrisk/`` captures in [T2_dev_start, T2_dev_end)."""
    starts = c1.load_manifest_starts(extract_root)
    ids = sorted(c for c, t in starts.items() if _ep(T2_DEV_START) <= t < _ep(T2_DEV_END))
    parts = []
    for cid in ids:
        d = c1.read_capture_table(extract_root, "negrisk", cid)
        if "final_yes" in d.columns:
            d = d.drop(columns=["final_yes"])
        if len(d):
            d["cs"] = starts[cid]
            d["capture_id"] = cid
            parts.append(d)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    mem = c1.members_asof_loader(extract_root)
    res = placeholder_gate(df, mem, days=len({datetime.fromtimestamp(starts[c], UTC).strftime("%Y-%m-%d") for c in ids}))
    res["n_captures"] = len(ids)
    return res


# =============================================================================================
# Trial logging (CB2 kinds; count line source creative_batch_2:<family>)
# =============================================================================================


def log_trials(family: str, tests: dict, *, kind: str, role: str, dataset: str, results_path: str, results_sha256: str,
               run_id: str, prov: dict, decl_sha: str, placebo: dict | None = None, n_tests: int | None = None,
               path: Path = provenance.TRIALS_PATH) -> list[dict]:
    """One line per test (``cb2_test`` / ``cb2_replication``), one count line per run (ml_explain, source
    ``creative_batch_2:<family>``), one placebo line (count 0) per placebo."""
    written = []
    for name, t in tests.items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": name, "run_id": run_id, "label": LABEL, "kind": kind,
            "evidence_role": role, "revision": VERSION, "result_path": results_path, "results_sha256": results_sha256,
            "declaration_sha256": decl_sha,
            "summary": {k: t.get(k) for k in ("mean", "p", "n", "n_event", "ci95", "r_ann", "advance", "testable", "replicated")},
            "provenance": prov}, path))
    for name, p in (placebo or {}).items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": f"{name}:placebo", "run_id": run_id, "label": LABEL, "kind": kind,
            "evidence_role": "placebo", "revision": VERSION, "result_path": results_path, "results_sha256": results_sha256,
            "declaration_sha256": decl_sha, "summary": {k: p.get(k) for k in ("draws", "n_advance", "advance_rate", "calibrated")},
            "provenance": prov}, path))
    written.append(provenance.append_trial({
        "dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY",
        "n_tests": len(tests) if n_tests is None else n_tests, "revision": VERSION, "run_id": run_id,
        "source": f"creative_batch_2:{family}", "results_sha256": results_sha256,
        "note": "CB2 structural count line; per-test cb2_* lines are EXCLUDEd in battery2.KIND_RULES"}, path))
    return written


def write_json(path: Path, doc: dict) -> str:
    return c1.write_json(path, doc)


def utc_stamp(t: datetime | None = None) -> str:
    return (t or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def l_out_epoch(pin_path: Path | None = None) -> float:
    return window_bounds("rep", pin_path)[1] + timedelta(days=T2_L_OUT_DAYS).total_seconds()


# =============================================================================================
# Batch-wide Holm over the CB2 Stage-2 family (freeze-check fix 17); also used by the weather stage P
# =============================================================================================

STAGE2_IDS = ("W2", "W3", "L1", "X1", "X2")
STAGEP_IDS = ("W2", "W3")
STAGE2_PARENTS = ("W_holdout", "L_rep")
STAGEP_PARENTS = ("W_stageP",)
BATCH_ALPHA = ALPHA_STAGE2


def _stage_of(path: Path, doc: dict) -> str | None:
    parent = Path(path).parent.name
    st = doc.get("stage")
    if parent in STAGE2_PARENTS or st in (2, "2", "stage2") or doc.get("window") == "rep" and "W" not in parent:
        return "stage2"
    if parent in STAGEP_PARENTS or st in ("P", "stageP"):
        return "stageP"
    return None


def batch_holm(results_paths, *, stage1_paths=None, alpha: float = BATCH_ALPHA, family: str = "stage2") -> dict:
    """Holm over the CB2 Stage-2 tests (``family="stage2"``: W2, W3, L1, X1, X2 from ``W_holdout``/``L_rep`` results) or
    the stage-P tests (``family="stageP"``: W2, W3 from ``W_stageP``), one-sided p-values, no test id twice. Anything
    else (a screen, a dev window) is refused. With ``stage1_paths`` the expected family is the set of tests that
    advanced there; a Stage-2 file may not contain a test outside it, and an expected test with no Stage-2 result counts
    as p = 1 and is listed. Without it the family is exactly the tests found. ``replicated`` needs the test's own gate
    (``replicated`` if the file carries it, else ``advance``) AND the Holm rejection."""
    from .cb1_history import holm  # noqa: PLC0415

    if family not in ("stage2", "stageP"):
        raise Cb2Error(f"unknown family {family!r}")
    allowed = STAGE2_IDS if family == "stage2" else STAGEP_IDS
    pv: dict[str, dict] = {}
    for p in results_paths:
        doc = json.loads(Path(p).read_text())
        if _stage_of(Path(p), doc) != family:
            raise Cb2Error(f"{p}: not a CB2 {family} results file")
        tests = doc.get("tests")
        if not isinstance(tests, dict) or not tests:
            raise Cb2Error(f"{p}: no tests table")
        for tid, r in tests.items():
            if tid not in allowed:
                raise Cb2Error(f"{p}: test {tid!r} is not in the {family} family {list(allowed)}")
            if tid in pv:
                raise Cb2Error(f"test {tid} appears in both {pv[tid]['source']} and {p}")
            own = r.get("replicated") if r.get("replicated") is not None else r.get("advance")
            pv[tid] = {"p": float(r.get("p", 1.0)) if r.get("p") is not None else 1.0, "own_gate": bool(own), "source": str(p)}
    expected = set(pv)
    if stage1_paths is not None:
        expected = set()
        for p in stage1_paths:
            doc = json.loads(Path(p).read_text())
            expected |= {t for t, r in (doc.get("tests") or {}).items() if r.get("advance")}
        extra = sorted(set(pv) - expected)
        if extra:
            raise Cb2Error(f"Stage-2 tests {extra} did not advance at Stage 1 (expected family {sorted(expected)})")
    missing = sorted(expected - set(pv))
    for t in missing:
        pv[t] = {"p": 1.0, "own_gate": False, "source": "missing_stage2_p=1"}
    if not pv:
        return {"m": 0, "alpha": alpha, "family": family, "tests": {}, "replicated": [], "missing_counted_p1": []}
    hm = holm({t: r["p"] for t, r in pv.items()}, alpha)
    tests = {t: {**pv[t], **hm[t], "replicated": bool(pv[t]["own_gate"] and hm[t]["reject"])} for t in sorted(pv)}
    return {"m": len(pv), "alpha": alpha, "family": family, "tests": tests,
            "replicated": sorted(t for t, r in tests.items() if r["replicated"]),
            "expected_family": sorted(expected), "missing_counted_p1": missing}


def check_l_out_reached(now: datetime | None = None, pin_path: Path | None = None) -> None:
    """The counted L/X replication reads outcomes of triggered rungs, first allowed at T2_L_out = T2_rep_end + 30 d."""
    t = l_out_epoch(pin_path)
    if (now or datetime.now(UTC)).timestamp() < t:
        raise TooEarlyError(f"rep outcome read refused before T2_L_out {_iso_z(t)}")
