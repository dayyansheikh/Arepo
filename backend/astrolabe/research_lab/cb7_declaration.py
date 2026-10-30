# ruff: noqa: E501
"""CB7 declaration (docs/research_lab/CREATIVE_BATCH_7.md 5.1): the content of the CB7 freeze file ``model_specs/cb7_v1.json``.

DRAFT GENERATOR ONLY. The freeze file binds the test tables, so it is written exactly once, AT THE CB7 FREEZE (after the science-reviewer code freeze check and the committed
census), by ``run_cb7.py write-spec``, and committed in its own commit. Until then ``screen`` refuses for every family. ``write-spec --dry-run`` prints the would-be content.

``declaration_sha256()`` hashes: the hypothesis table; the counting, date and Holm rules; every UPPER_CASE constant and the source of every function and class defined in the
CB7 analysis modules (``cb7_astats``, ``cb7_g_analysis``, ``cb7_x_analysis``, ``cb7_s_analysis``); the source of every imported function the analysis relies on (CB2 small-G helper,
CB1 Holm / Wilson / half-spread / payout parser, the CB7 theme and X definitions, the census readers) and the constant tables it reads (half-spread, fee and rebate tables, status-quo
and theme patterns, census gates); and the committed rules file's ``rules_sha256`` (populations, windows, regexes, markers, cut rule, seeds, pins). The spec additionally pins the
sha256 of the source FILES of the CB7 modules and of ``run_cb7.py``, the census.json sha256 and the seal / h_geo pins it carries. Dates and the screen time are in the spec, not in the hash.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

VERSION = "cb7-declaration-v1"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb7_v1.json"
SOURCE_FILES = ("cb7_declaration", "cb7_astats", "cb7_g_analysis", "cb7_x_analysis", "cb7_s_analysis", "cb7_census", "cb7_xv", "cb7_common")
T7_X_LIST_FLOOR = "2026-11-03T06:00:00Z"

HYPOTHESES_CB7 = {
    "S1": {"family": "S", "kind": "mechanism", "direction": "> 0", "unit": "eligible h8_text market at t7 (one origin)",
           "statistic": "within-cell slope of (price - outcome) on the condition count C; recorded NOT TESTABLE (gate GS false in the census, 787 units against 3,000), p = 1, counted"},
    "G1": {"family": "G", "kind": "economic", "direction": "> 0", "unit": "eligible (market, origin) of h8_geo, YES in [0.02, 0.10] at 30 / 14 / 7 days before the scheduled end",
           "statistic": "mean net per share of buying YES at the modelled ask, held to resolution; inverted tail gate; >= 10 YES event clusters; carried to Stage P only if it meets the Stage-1 batch Holm (alpha 0.01, k1 = 3)"},
    "X1": {"family": "X", "kind": "economic", "direction": "< 0", "unit": "print in S (non-sports C1 pairs)",
           "statistic": "mean resting-maker mark-out at 1 h plus the forgone rebate over the fills a 20-minute Kalshi-skewed step-aside would skip; route gate on kept fills"},
}
COUNTING = {
    "fixed": ["S1", "G1", "X1"], "conditional": ["X1-rep"], "not_run": ["S1-rep", "S2"], "stage1_alpha": 0.01, "k1": 3,
    "stage2": "Holm, one-sided alpha 0.05; k2 = 1 if X1 advances, else 0 (S1-rep and S2 do not run because S1 is not testable; freeze check 2026-10-30)",
    "counts": "creative_batch_7:S|G|X ml_explain lines (n_tests 1 each; S1 is counted at p = 1)",
}
DATES = {"T7_X_list": f"max({T7_X_LIST_FLOOR}, freeze + 24 h)", "T7_S_rep_start": "not applicable (S1 not testable; the textorig step is not deployed)",
         "T7_X_rep_start": "first 00:00Z at least 2 h after the audited pair list is committed and >= 2026-11-04T00:00Z", "T7_X_rep_end": "T7_X_rep_start + 21 d"}


def _modules() -> list:
    from . import cb7_astats, cb7_g_analysis, cb7_s_analysis, cb7_x_analysis  # noqa: PLC0415

    return [cb7_astats, cb7_g_analysis, cb7_x_analysis, cb7_s_analysis]


def _externals() -> list:
    from . import battery as B  # noqa: PLC0415
    from . import cb1_history as c1  # noqa: PLC0415
    from . import cb2_weather as w2  # noqa: PLC0415
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_census as cc  # noqa: PLC0415
    from . import cb7_geo as cg  # noqa: PLC0415
    from . import cb7_xv as xv  # noqa: PLC0415
    from . import history_topics  # noqa: PLC0415

    return [w2.small_g_pvalue, w2._cluster_sums, B._cr_var_of_sum, c1.holm, c1.wilson_bound, c1.half_spread, c1.parse_outcome0, c6.event_key_split, cg.theme_of,
            history_topics.topic_of, xv.valid_mid, xv.KalshiMid, xv.move_events, xv.in_skip, xv.skip_windows, xv.poly_point_ok, xv.mark_available, xv.classify_prints,
            xv.map_trade_row, cc.event_keys, cc.iso_week, cc._f, cc._ci, cc.read_cols, cc.verify_seal_copies, cc.census_declaration]


def _plain(v):
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_plain(x) for x in (sorted(v, key=str) if isinstance(v, (set, frozenset)) else v)]
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return repr(v)


def module_constants() -> dict[str, dict]:
    out = {}
    for m in _modules():
        out[m.__name__.rsplit(".", 1)[-1]] = {k: _plain(getattr(m, k)) for k in sorted(dir(m))
                                              if k.isupper() and not k.startswith("_") and not isinstance(getattr(m, k), Path) and k != "FREEZE_SPEC"}
    return out


def external_constants() -> dict:
    from . import cb1_history as c1  # noqa: PLC0415
    from . import cb2_weather as w2  # noqa: PLC0415
    from . import cb7_census as cc  # noqa: PLC0415
    from . import cb7_geo as cg  # noqa: PLC0415
    from . import cb7_xv as xv  # noqa: PLC0415
    from . import economics  # noqa: PLC0415

    return _plain({"HALF_SPREAD": c1.HALF_SPREAD, "DOCS_CATEGORY_RATE": economics.DOCS_CATEGORY_RATE, "REBATE_SHARE": economics.REBATE_SHARE,
                   "w2": {"G_NORMAL": w2.G_NORMAL, "G_MIN": w2.G_MIN, "N_WILD": w2.N_WILD}, "STATUS_QUO_PATTERNS": cg.STATUS_QUO_PATTERNS, "THEME_PATTERNS": cg.THEME_PATTERNS,
                   "census_gates": {"GS": cc.GS, "GG": cc.GG, "GX": cc.GX}, "H_GEO_WINDOW": cc.H_GEO_WINDOW, "H_GEO_MID": cc.H_GEO_MID,
                   "xv": {k: getattr(xv, k) for k in ("K_MAX_AGE_S", "K_MAX_SPREAD", "MID_RANGE", "MOVE_LOOKBACK_S", "MOVE_THRESHOLD", "SKIP_LAG_S", "SKIP_LEN_S",
                                                       "POLY_MARK_MIN_AGE_S", "POLY_MARK_MAX_AGE_S")}})


def function_sources() -> dict[str, str]:
    """sha256 of the source of every function / class defined in the analysis modules and of every imported function the analysis relies on."""
    out = {}
    for m in _modules():
        for name, obj in sorted(inspect.getmembers(m)):
            if (inspect.isfunction(obj) or inspect.isclass(obj)) and obj.__module__ == m.__name__:
                out[f"{m.__name__.rsplit('.', 1)[-1]}.{name}"] = hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()
    for f in _externals():
        out[f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}"] = hashlib.sha256(inspect.getsource(f).encode()).hexdigest()
    return out


def rules_sha256() -> str:
    from . import cb7_common as cm  # noqa: PLC0415

    return cm.rules_file_doc()["rules_sha256"]


def declaration_blob() -> dict:
    return {"version": VERSION, "hypotheses": HYPOTHESES_CB7, "counting": COUNTING, "dates": DATES, "constants": module_constants(), "external_constants": external_constants(),
            "function_sources_sha256": function_sources(), "rules_sha256": rules_sha256()}


def declaration_sha256() -> str:
    return hashlib.sha256(json.dumps(declaration_blob(), sort_keys=True, default=str).encode()).hexdigest()


def _script_path() -> Path:
    here = Path(__file__).resolve().parents[2]  # backend/
    return here / "scripts" / "run_cb7.py"


def file_hashes() -> dict[str, str]:
    here = Path(__file__).resolve().parent
    out = {f"astrolabe/research_lab/{m}.py": hashlib.sha256((here / f"{m}.py").read_bytes()).hexdigest() for m in SOURCE_FILES}
    out["scripts/run_cb7.py"] = hashlib.sha256(_script_path().read_bytes()).hexdigest()
    return out


def mismatches(spec: dict) -> list[str]:
    """Keys of a freeze spec that differ from this code: version, declaration hash, rules hash, every pinned source file."""
    bad = []
    if spec.get("version") != VERSION:
        bad.append("version")
    if spec.get("declaration_sha256") != declaration_sha256():
        bad.append("declaration_sha256")
    if spec.get("rules_sha256") != rules_sha256():
        bad.append("rules_sha256")
    cur = file_hashes()
    for k, v in cur.items():
        if (spec.get("sources") or {}).get(k) != v:
            bad.append(f"sources:{k}")
    return bad


def _pins_from_census(census: dict) -> dict:
    g = (census.get("G") or {}).get("h_geo") or {}
    return {"seals": census.get("seals"), "h_geo": {"capture_pins": g.get("capture_pins"), "text_table_sha256": g.get("text_table_sha256"), "h_geo_binding": g.get("h_geo_binding")},
            "census_constants_sha256": (census.get("declaration") or {}).get("constants_sha256"),
            "census_xv_definitions_sha256": (census.get("declaration") or {}).get("cb7_xv_definitions_sha256")}


def t7_x_list(freeze_utc: str) -> str:
    f = datetime.strptime(freeze_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    floor = datetime.strptime(T7_X_LIST_FLOOR, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return max(floor, f + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")


def spec_payload(*, census_json: Path, freeze_utc: str, screen_not_before_utc: str) -> dict:
    """The freeze file content. ``freeze_utc`` is the freeze commit time; ``screen_not_before_utc`` the declared time before which no screen runs or opens an outcome
    file (it must not precede the freeze)."""
    from . import cb7_census as cc  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    f = datetime.strptime(freeze_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    nb = datetime.strptime(screen_not_before_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    if nb < f:
        raise ValueError("screen_not_before_utc precedes the freeze")
    census_json = Path(census_json)
    census = json.loads(census_json.read_text())
    want = cc.census_declaration()
    got = census.get("declaration") or {}
    stale = [k for k in ("cb7_xv_definitions_sha256", "constants_sha256") if got.get(k) != want[k]]
    if stale:
        raise ValueError(f"census declaration hashes differ from this code: {stale}")
    return {"version": VERSION, "declaration_sha256": declaration_sha256(), "rules_sha256": rules_sha256(), "sources": file_hashes(),
            "census_json_sha256": h5_seal.sha256_file(census_json), **_pins_from_census(census),
            "dates": {"freeze_utc": freeze_utc, "screen_not_before_utc": screen_not_before_utc, "T7_X_list": t7_x_list(freeze_utc), "T7_S_rep_start": "not applicable"},
            "queue": {"promote": ["q0148", "q0149", "q0150"], "do_not_promote": ["q0151", "q0152", "q0156"], "conditional_on_x1_advance": ["q0153", "q0154", "q0155"]},
            "hypotheses": HYPOTHESES_CB7, "counting": COUNTING}


def write_spec(path: Path | None = None, *, census_json: Path, freeze_utc: str, screen_not_before_utc: str) -> dict:
    """Write the CB7 freeze file. Refuses to overwrite. Run ONLY at the CB7 freeze, after the rules file is committed and the science-reviewer freeze check."""
    from . import cb7_common as cm  # noqa: PLC0415

    path = Path(path or SPEC_PATH)
    if path.exists():
        raise cm.Refused(f"{path} exists; a frozen declaration is never overwritten")
    cm.verify_rules(require_committed=True)
    p = spec_payload(census_json=census_json, freeze_utc=freeze_utc, screen_not_before_utc=screen_not_before_utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    return p
