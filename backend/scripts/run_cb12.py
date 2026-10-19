# ruff: noqa: E501
"""CB12 runner (docs/research_lab/CREATIVE_BATCH_12.md section 4). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or
profitability claim. This file covers common + smoke + X + M (queue ids q0240, q0241, q0242, q0243, q0248 (M), q0249 (M part), q0251, q0252, q0255, q0256), O
(q0260 opt-smoke, q0261 opt-live, q0262 census O, q0263 screen O, q0264 rep O) and E (q0244 quake-frame, q0245 quake-prices, q0266 census E, q0253 screen E, q0257 quake-live,
q0258 rep E); F subcommands arrive with their module and are refused here.

    python scripts/run_cb12.py rules                       # write docs/research_lab/seals/cb12_rules.json (one sha256 per part: common, M, E, F, X, O); commit before q0240
    python scripts/run_cb12.py freeze-part --part M|X      # print a part of the CB12 freeze declaration (model_specs/cb12_v1.json carries one entry per family part)
    python scripts/run_cb12.py smoke ...                   # q0240: counts only, WRITE-ONCE (families M and X now)
    python scripts/run_cb12.py exclusion-keys ...          # q0241: CB11 q0221 key file (sha256 pin MANDATORY) + every set created since + seal copies + C1 ids (resumable)
    python scripts/run_cb12.py say-frame | say-prices ...  # q0242 / q0243 (CB12-M)
    python scripts/run_cb12.py seal --family M|auto ...    # q0248 (M HOLDOUT listing + outcome file sha256)
    python scripts/run_cb12.py quake-frame | quake-prices  # q0244 / q0245 (CB12-E: Gamma tag events, parser, USGS catalogue; prices-history)
    python scripts/run_cb12.py quake-live ...              # q0257: the E collector (cron 10:00Z and 16:00Z; refuses before the E freeze)
    python scripts/run_cb12.py census --family M|X|O|E     # q0249 (M part) / q0251 / q0262 / q0266 (E): counts only; gates; coverage; MDEs
    python scripts/run_cb12.py screen --family M|X|O|E     # q0252 / q0255 / q0263 / q0253 (refuse before the family's freeze entry)
    python scripts/run_cb12.py rep --family M|O|E          # q0256 / q0264 / q0258 (verifies the seal / the pinned Stage-1 results first)
    python scripts/run_cb12.py opt-smoke ...               # q0260: one live checkpoint dry run in a regular session (exit 75 outside), WRITE-ONCE opt_smoke.json
    python scripts/run_cb12.py opt-live ...                # q0261: the O collector (cron every 5 min on weekdays; refuses before the O freeze)

Exit codes: 0 ok / transient pause / declared stall (the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules hash of the command's part, smoke
result exists or missing, run id, refused root, declared argument changed, before the family's freeze for analysis jobs, HOLDOUT, guarded file, results exist); 4 disk
budget; 75 (EX_TEMPFAIL) a time gate, data-dumps / free-disk headroom, an upstream job not finished or a transient network give-up: "pending", no trials line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4
IMPLEMENTED = ("M", "X", "O", "E")
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.01, "say-frame": 0.005, "say-prices": 0.08, "opt-live": 0.3, "quake-frame": 0.03, "quake-prices": 0.01, "quake-live": 0.01}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "say-frame": 2.0, "say-prices": 2.0, "seal": 2.0, "opt-smoke": 2.0, "opt-live": 2.0, "quake-frame": 2.0, "quake-prices": 2.0, "quake-live": 1.0}


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _guarded(fn):
    def wrapper(a) -> int:
        from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

        try:
            code, payload = fn(a)
        except cm.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except cm.NotNow as exc:
            _emit({"tempfail": str(exc), "science": "pending (no trials line)"})
            return TEMPFAIL
        except (cm.SealError, FileNotFoundError) as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except Exception as exc:
            _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
            return 1
        _emit(payload)
        return code

    return wrapper


def _c12():
    from astrolabe.research_lab import cb12_common as c12  # noqa: PLC0415

    return c12


def _root(a) -> Path:
    c12 = _c12()
    return c12.refuse_path(Path(a.root) if getattr(a, "root", None) else c12.CB12_DIR)


def _hist(a) -> Path:
    c12 = _c12()
    return c12.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c12.HIST_ROOT)


def _cv_root(a) -> Path:
    c12 = _c12()
    return c12.refuse_path(Path(a.cv_root) if getattr(a, "cv_root", None) else c12.CV_DIR, allow=c12.X_READABLE_ROOTS)


def _declared(a, cmd: str) -> None:
    c12 = _c12()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c12.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c12.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")
    if float(getattr(a, "data_dumps_cap_gb", c12.DATA_DUMPS_CAP_GB)) > c12.DATA_DUMPS_CAP_GB + 1e-9:
        raise c12.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c12.DATA_DUMPS_CAP_GB!r}")


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(rps=a.rps, data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _rules(a, part: str) -> str:
    """Verify ONE rules part (the command's own). Returns that part's sha256. A part that is not declared in the file or the code refuses (exit 2)."""
    return _c12().verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False), part=part)


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _smoke_path(a) -> Path:
    return Path(a.smoke) if getattr(a, "smoke", None) else _c12().SMOKE_DEFAULT


def _smoke_paths(a, fam: str) -> list[Path]:
    """The smoke files a family reads, oldest first. A family with a later smoke (M: smoke_M_v2.json, which supersedes the v1 criterion m_prices_history by
    m_prices_history_v2) reads both; the family's SMOKE_NEEDS name only the criteria that exist in the latest version. ``--smoke`` pins a single file."""
    if getattr(a, "smoke", None):
        return [Path(a.smoke)]
    paths = [_c12().SMOKE_DEFAULT]
    for mod in _c12().family_modules(fam):
        v2 = getattr(mod, "SMOKE_V2_DEFAULT", None)
        if v2 is not None:
            paths.append(Path(v2))
    return paths


def _keys_path(a) -> Path:
    return Path(a.exclusion_keys) if getattr(a, "exclusion_keys", None) else _c12().EXCLUSION_KEYS_DEFAULT


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _seals_dir(a) -> Path | None:
    return Path(a.seals_dir) if getattr(a, "seals_dir", None) else None


def _committed(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    return None if getattr(a, "allow_uncommitted_rules", False) else cb1_history.spec_committed


def _freeze(a, part: str) -> str:
    return _c12().require_freeze(part, Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False))


def _freeze_entry(a, part: str) -> tuple[str, dict]:
    """(sha256, entry) of one family part of the committed CB12 freeze declaration."""
    c12 = _c12()
    sha = _freeze(a, part)
    p = Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else Path(c12.__file__).resolve().parent / "model_specs" / "cb12_v1.json"
    return sha, json.loads(p.read_text())[part]


def _o_frozen_epoch(entry: dict) -> float:
    c12 = _c12()
    t = c12.parse_iso(entry.get("frozen_utc"))
    if not t == t:  # NaN
        raise c12.Refused("the freeze entry has no frozen_utc (O: window 1 starts at the first session >= 1 day after it; E: T12_E2_start is the first market listed >= 1 day after it)")
    return t


def _o_convention(a, entry: dict) -> str | None:
    """The iv time convention written into the O freeze entry (``iv_convention``); it must equal the smoke's choice. "none" -> Phi(d2) units are excluded."""
    from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415

    c12 = _c12()
    conv = entry.get("iv_convention")
    sp = Path(a.opt_smoke) if getattr(a, "opt_smoke", None) else o12.SMOKE_V2_DEFAULT
    if not sp.exists():
        raise c12.Refused(f"{sp.name} missing (q0260 first)")
    choice = ((json.loads(sp.read_text()).get("detail") or {}).get("O") or {}).get("o_iv_convention_checked", {}).get("choice")
    if conv not in (*o12.CONVENTIONS, "none") or conv != choice:
        raise c12.Refused(f"O freeze iv_convention {conv!r} differs from the smoke's choice {choice!r} (or is missing)")
    return None if conv == "none" else conv


def _o_earnings_identified(a) -> bool:
    from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415

    sp = Path(a.opt_smoke) if getattr(a, "opt_smoke", None) else o12.SMOKE_V2_DEFAULT
    return bool((json.loads(sp.read_text()).get("criteria") or {}).get("o_earnings_keyless")) if sp.exists() else False


def _o_sources(a):
    from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    live = None if getattr(a, "standalone", False) else hb.live_pass_or_lock
    pm = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, o12.PM_RPS), live_check=live)
    ext = hb.Limiter(o12.ext_transport(), rps=o12.EXT_RPS, live_check=live)
    return o12.Sources(pm, ext)


def _family(a) -> str:
    c12 = _c12()
    fam = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if len(fam) != 1 or fam[0] not in c12.FAMILY_PARTS:
        raise c12.Refused(f"family {a.family!r}: exactly one of {c12.FAMILY_PARTS} (the M, E, F, X and O jobs are separate)")
    if fam[0] not in IMPLEMENTED:
        raise c12.Refused(f"family {fam[0]} is not implemented in this runner yet (CB12-{fam[0]} code and its rules part arrive later)")
    return fam[0]


# ---- rules ------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c12 = _c12()
    try:
        out = c12.write_rules(Path(a.path) if a.path else None)
        doc = c12.rules_file_doc()
    except c12.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "funcs_sha256": v.get("funcs_sha256")} for k, v in doc["parts"].items()}})
    return 0


def cmd_freeze_part(a) -> int:
    """Print one family part of the freeze declaration (what ``model_specs/cb12_v1.json`` carries under that part); writes nothing."""
    c12 = _c12()
    try:
        d = c12.rules_part_file_doc(a.part)
        if d.get("part_declared") is False:
            raise c12.Refused(f"part {a.part} is not declared: {d.get('reason')}")
    except c12.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"part": a.part, "rules_sha256": d["rules_sha256"], "declaration": d["declared"]})
    return 0


# ---- q0240 smoke ------------------------------------------------------------------------------------------------------------------------------


_TRANSIENT_STATUS = re.compile(r"status (None|0|408|429|5\d\d)\b")


def _not_now_if_transient(source: str, exc: Exception) -> None:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if _TRANSIENT_STATUS.search(str(exc)):
        raise cm.NotNow(f"smoke: {source} returned a transient status ({str(exc)[:80]}); nothing written") from None


def _smoke_families(a) -> list[str]:
    c12 = _c12()
    spec = str(a.families)
    if spec == "auto":
        return [f for f in c12.FAMILY_PARTS if c12.family_modules(f)]
    fam = [x.strip() for x in spec.split(",") if x.strip()]
    bad = [f for f in fam if f not in c12.FAMILY_PARTS]
    if bad or not fam:
        raise c12.Refused(f"smoke families {bad or spec!r} unknown")
    return fam


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "smoke")
    fams = _smoke_families(a)
    later = [getattr(mod, "SMOKE_V2_DEFAULT", None) for f in fams for mod in c12.family_modules(f)]
    default_out = later[0] if later and all(later) else c12.SMOKE_DEFAULT  # a run of only families that have a later smoke writes that smoke's file
    out = c12.refuse_path(Path(a.out) if a.out else default_out)
    if out.exists():
        raise c12.Refused(f"smoke result {out} already exists; it is write-once")
    shas = {"common": _rules(a, "common"), **{f: _rules(a, f) for f in fams}}
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    now = time.time()
    ctx = {"cv_root": str(_cv_root(a)), "now": now}
    try:
        crit, detail = sm.collect_checks(tuple(fams), ctx, lim)
    except cm.ApiError as exc:
        _not_now_if_transient("a CB12 source", exc)
        raise
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    res = {"smoke_version": c12.SMOKE_VERSION, "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True, "families_covered": fams,
           "supersedes": ({"file": "smoke.json", "criterion": "m_prices_history", "by": "m_prices_history_v2", "note": "v1 FAIL kept untouched; disclosed in CREATIVE_BATCH_12.md section 11 A6"} if out != c12.SMOKE_DEFAULT and "M" in fams else None),
           "family_smoke_versions": {f: getattr(c12.family_modules(f)[0], "SMOKE_FAMILY_VERSION", c12.SMOKE_VERSION) for f in fams},
           "requests": lim.requests, "criteria": crit, "pass": all(crit.values()), "detail": detail,
           "consequences": {"a failed criterion": "the dependent family is not testable (source), counted", "rule": "no rule is re-fitted; jobs downstream stall (exit 0, label carried)"}}
    cm.write_once_json(out, res)
    c12.log_descriptive("smoke", {"pass": res["pass"], "criteria": crit, "families": fams, "smoke_path": str(out)}, trials_path=_tp(a))
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": res["requests"]}


def _require_smoke(a, fam: str) -> None:
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415

    c12 = _c12()
    bad = sm.smoke_failures(_smoke_paths(a, fam), sm.family_needs(fam))
    if bad:
        raise c12.Refused(f"smoke criteria for family {fam} not met: {bad}")


# ---- q0241 exclusion keys -----------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "exclusion-keys")
    sha = _rules(a, "common")
    hist = _hist(a)
    m = c12.exclusion_keys(_root(a), hb.httpx_transport(), rules_sha=sha, hist_root=hist, base_path=Path(a.base_path) if a.base_path else c12.CB11_KEYS_DEFAULT,
                           base_sha256=a.base_sha256 or c12.PIN_UNSET, seals_dir=_seals_dir(a), matches_path=_cv_root(a) / "matches.json", is_committed=_committed(a),
                           disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0242 / q0243 M data ---------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_say_frame(a):
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "say-frame")
    sha = _rules(a, "M")
    m = m12.say_frame(_hist(a), hb.httpx_transport(), rules_sha=sha, smoke_paths=_smoke_paths(a, "M"), exclusion_keys_path=_keys_path(a), now=time.time(),
                      disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_say_prices(a):
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "say-prices")
    sha = _rules(a, "M")
    hist = _hist(a)
    m = m12.say_prices(hist, hist / m12.FRAME_RUN, hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0244 / q0245 E data ---------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_quake_frame(a):
    from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "quake-frame")
    sha = _rules(a, "E")
    kw = _net_kw(a)
    m = e12.quake_frame(_hist(a), hb.httpx_transport(), rules_sha=sha, smoke_paths=_smoke_paths(a, "E"), exclusion_keys_path=_keys_path(a), now=time.time(),
                        usgs_rps=min(a.usgs_rps, e12.USGS_RPS), disk_cap=int(a.disk_cap_gb * 1024**3), **kw)
    return _result(m)


@_guarded
def cmd_quake_prices(a):
    from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "quake-prices")
    sha = _rules(a, "E")
    m = e12.quake_prices(_hist(a), hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0248 seal --------------------------------------------------------------------------------------------------------------------------------


def seal_m(a) -> dict:
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    rdir = _hist(a) / m12.FRAME_RUN
    if not c12.stall_of(rdir) and not c12.manifest_complete(rdir, (m12.PRICES_STATUS,)):
        raise c12.NotNow(f"{rdir.name} prices are not finished yet; pending")  # before any rules read: another family must still seal when this one has not run
    sha = _rules(a, "M")
    rows = m12.seal_rows(rdir) if not c12.stall_of(rdir) else []
    xr = _root(a) / c12.c9.EXCLUSION_REPORT_NAME  # the id-source frames q0241 recorded "absent" are re-read here
    if not xr.is_file():
        raise c12.Refused(f"{xr} is missing (q0241 first); the sets absent at q0241 cannot be re-read")
    absent = json.loads(xr.read_text()).get("sets_absent_at_q0241") or []
    return c12.seal_holdout(rdir, family="say", statuses=(m12.PRICES_STATUS,), copy_name="cb12_say_holdout_SEAL.json", rows=rows, rules_sha=sha, transport=hb.httpx_transport(),
                            seals_dir=_seals_dir(a), rps=a.rps, live_check=None if a.standalone else hb.live_pass_or_lock, is_committed=_committed(a),
                            outcome_files=("holdout/outcomes_guarded_holdout.csv.gz",), hist_root=_hist(a), absent_sets=absent)


SEAL_FAMILIES = {"M": seal_m}


@_guarded
def cmd_seal(a):
    c12 = _c12()
    _declared(a, "seal")
    fams = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if "auto" in fams:
        fams = sorted(SEAL_FAMILIES)
    done, pending = {}, []
    for f in fams:
        fn = SEAL_FAMILIES.get(f)
        if fn is None:
            raise c12.Refused(f"seal family {f!r} is not implemented in this runner")
        try:
            done[f] = fn(a)
        except c12.NotNow as exc:
            pending.append(f"{f}: {exc}")
    if pending:
        raise c12.NotNow("; ".join(pending))
    return 0, {"status": "seal_all_complete", "families": done}


# ---- census ------------------------------------------------------------------------------------------------------------------------------------


def census_m_block(a) -> dict:
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415

    c12 = _c12()
    rdir = _hist(a) / m12.FRAME_RUN
    st = c12.stall_of(rdir)
    if st:
        return {"status": "stalled", "stall": st, "label_M": st.get("label")}
    c12.verify_fetch(rdir, (m12.PRICES_STATUS,), "say_prices (q0243)")
    c12.verify_holdout_seal(rdir, "cb12_say_holdout_SEAL.json", _seals_dir(a), require_committed=not getattr(a, "allow_uncommitted_rules", False))
    return m12.census_m(rdir)


def census_x_block(a) -> dict:
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_x as x12  # noqa: PLC0415

    root = _cv_root(a)
    bad = sm.smoke_failures(_smoke_path(a), sm.family_needs("X"))  # a missing smoke file is still a refusal (q0240 first); a FAILED criterion is a counted outcome
    if bad:
        return x12.source_failure_census(f"smoke criteria not met: {bad}")
    try:
        loaded = x12.load_c1(root, expected=None if a.allow_unpinned_c1 else x12.C1_EXPECTED, verify=not a.allow_unpinned_c1)
    except x12.C1ReproductionError as exc:
        return x12.source_failure_census(f"C1 reproduction failed: {exc}"[:300])
    return x12.census_x(loaded["pairs"], loaded["report"])


def census_o_block(a) -> dict:
    """q0262: window-1 census of the O collector (counts only). Needs the O freeze entry (frozen_utc, iv_convention); waits (exit 75) until window 1 closed and the
    outcome step is final for its dates; a failed smoke criterion is the counted label "not testable (source)"."""
    from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415

    _fsha, entry = _freeze_entry(a, "O")
    root = _hist(a) / o12.RUN
    bad = sm.smoke_failures(_smoke_paths(a, "O"), sm.family_needs("O"))
    if bad:
        return {"label_O": "not testable (source)", "smoke_failures": bad, "counts_only": True}
    conv = _o_convention(a, entry)
    win = o12.windows(root, _o_frozen_epoch(entry), time.time())
    return o12.census_o(root, win["w1"], conv) | {"windows": win}


def _e_frame_rules_guard(rdir: Path, sha: str) -> None:
    """Refuse an E frame / prices run whose manifest records a rules hash other than the current E part (a frame fetched under other code is not this code's frame)."""
    c12 = _c12()
    mp = Path(rdir) / "manifest.json"
    rec = (json.loads(mp.read_text()) if mp.exists() else {}).get("rules_sha256")
    if isinstance(rec, dict):
        rec = rec.get("E")
    if rec != sha:
        raise c12.Refused(f"frame/prices manifest {mp.name} in {Path(rdir).name} was fetched under E rules {str(rec)[:12]} but the current E part is {sha[:12]}; refusing")


def census_e_block(a) -> dict:
    """q0266: counts only (no outcome file opened; the catalogue only through the t - 72 h accessor). A stalled frame/prices run carries its label."""
    from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415

    c12 = _c12()
    rdir = _hist(a) / e12.FRAME_RUN
    st = c12.stall_of(rdir)
    if st:
        return {"status": "stalled", "stall": st, "label_E": st.get("label") or "not testable (source)"}
    c12.verify_fetch(rdir, (e12.PRICES_STATUS,), "quake_prices (q0245)")
    _e_frame_rules_guard(rdir, _rules(a, "E"))
    return e12.census_e(rdir)


CENSUS_BLOCKS = {"M": census_m_block, "X": census_x_block, "O": census_o_block, "E": census_e_block}


@_guarded
def cmd_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c12 = _c12()
    fam = _family(a)
    sha = _rules(a, fam)
    out = Path(a.out) if a.out else _root(a) / f"census_{fam}{a.census_tag}.json"
    if out.exists():
        raise c12.Refused(f"{out} exists; the census is written once")
    ver = int(a.census_tag[2:]) if re.fullmatch(r"_v[0-9]+", a.census_tag or "") else 1
    doc = {"version": f"cb12-census-{fam}-v{ver}", "counts_only": True, "rules_sha256": sha, fam: CENSUS_BLOCKS[fam](a)}
    cm.write_once_json(out, doc)
    c12.log_descriptive(f"census_{fam}", {"census_sha256": cm.sha_obj(doc), "path": str(out)}, trials_path=_tp(a), role="prospective" if fam == "O" else c12.EVIDENCE_ROLE_HIST)
    return 0, {"status": "census_complete", "written": str(out), "label": doc[fam].get(f"label_{fam}")}


# ---- screens -----------------------------------------------------------------------------------------------------------------------------------


def _by_triage(res: dict, trials_path: Path | None) -> dict:
    """BY label (q = 0.10 over ``battery2.cumulative_count()`` at the run): triage only, never the gate."""
    from astrolabe.research_lab import battery2, provenance  # noqa: PLC0415

    tp = trials_path or provenance.TRIALS_PATH
    try:
        total = int(battery2.cumulative_count(tp)["total"])
    except (OSError, ValueError, KeyError) as exc:
        return {"unavailable": f"cumulative count unreadable: {type(exc).__name__}", "trials_path": str(tp)}
    by = battery2.apply_by2({t: {"p": r.get("p", 1.0), "testable": r.get("testable", False)} for t, r in res.items()}, total)
    return {"cumulative_count": total, "q": by["q"], "m_total": by["m_total"], "survivors": by["survivors"], "triage_only": True}


def _line(r: dict, *, advance_key: str = "advance") -> dict:
    return {"p": r.get("p", 1.0), "advance": r.get(advance_key), "testable": r.get("testable"), "effect": r.get("effect"), "n": r.get("n"), "verdict": r.get("verdict")}


def _placebos(res: dict, tids: tuple[str, ...]) -> dict:
    out = {}
    for t in tids:
        pl = (res.get(t) or {}).get("placebo")
        if pl:
            out[t] = {"note": pl.get("note", f"{t} binding placebo"), "advance_rate": pl.get("advance_rate"), "n_draws": pl.get("n_draws")}
    return out


@_guarded
def cmd_screen(a):
    c12 = _c12()
    fam = _family(a)
    freeze_sha = _freeze(a, fam)
    sha = _rules(a, fam)
    root = _root(a)
    cpath = Path(a.census) if a.census else root / f"census_{fam}{a.census_tag}.json"
    if not cpath.exists():
        raise c12.NotNow(f"{cpath.name} missing (the census first)")
    cdoc = json.loads(cpath.read_text())
    if cdoc.get("rules_sha256") != sha:  # a census written under other code is not the census of this code
        raise c12.Refused(f"{cpath.name} was written under rules {str(cdoc.get('rules_sha256'))[:12]} but the current {fam} part is {sha[:12]}; re-run the census")
    census = cdoc[fam]
    tids = c12.FAMILY_TESTS[fam]
    if fam == "M":
        from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415

        rdir = _hist(a) / m12.FRAME_RUN
        if not c12.stall_of(rdir):
            c12.verify_fetch(rdir, (m12.PRICES_STATUS,), "say_prices")
            c12.verify_holdout_seal(rdir, "cb12_say_holdout_SEAL.json", _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
        body = m12.screen_m(rdir, census)
    elif fam == "E":
        from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415

        rdir = _hist(a) / e12.FRAME_RUN
        if not census.get("label_E"):
            c12.verify_fetch(rdir, (e12.PRICES_STATUS,), "quake_prices")
            _e_frame_rules_guard(rdir, sha)
        body = e12.screen_e(rdir, census)
    elif fam == "O":
        from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415

        _fsha, entry = _freeze_entry(a, "O")
        conv = _o_convention(a, entry) if not census.get("label_O") else None
        body = o12.screen_o(_hist(a) / o12.RUN, census, conv, earnings_identified=_o_earnings_identified(a), frozen_epoch=_o_frozen_epoch(entry))
    else:
        from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
        from astrolabe.research_lab import cb12_x as x12  # noqa: PLC0415

        bad = sm.smoke_failures(_smoke_path(a), sm.family_needs("X")) if not census.get("label_X") else []
        if census.get("label_X"):
            body = x12.screen_x([], census)
        elif bad:  # a failed smoke criterion is a counted "not testable (source)" outcome (p = 1 trial line), not a refusal
            body = x12.screen_x([], {"label_X": x12.SOURCE_LABEL})
        else:
            try:
                loaded = x12.load_c1(_cv_root(a), expected=None if a.allow_unpinned_c1 else x12.C1_EXPECTED, verify=not a.allow_unpinned_c1)
            except x12.C1ReproductionError:
                body = x12.screen_x([], {"label_X": x12.SOURCE_LABEL})
            else:
                body = x12.screen_x(loaded["pairs"], census)
    doc = {**body, "rules_sha256": sha, "freeze_part": fam, "freeze_sha256": freeze_sha, "census_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(), "written_epoch": time.time()}
    doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
    rsha = c12.write_results_once(Path(a.out) if a.out else root / f"results_{fam}.json", doc)
    c12.log_family(fam, {t: _line(doc[t]) for t in tids}, trials_path=_tp(a), results_sha256=rsha, placebos=_placebos(doc, tids),
                   role="prospective" if fam == "O" else c12.EVIDENCE_ROLE_HIST)
    return 0, {"status": f"screen_{fam}_complete", **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in tids}}


def _pinned_stage1(a, fam: str, root: Path) -> tuple[dict, tuple[str, ...]]:
    c12 = _c12()
    rp = root / f"results_{fam}.json"
    if not rp.exists():
        raise c12.NotNow(f"results_{fam}.json missing: Stage 1 first")
    res = json.loads(rp.read_text())
    adv = tuple(t for t in c12.FAMILY_TESTS[fam] if (res.get(t) or {}).get("advance") is True)
    if not adv:
        raise c12.Refused(f"no CB12-{fam} test advanced: there is no {fam} Stage 2")
    if not a.results_sha256:
        raise c12.Refused(f"--results-sha256 is required for the {fam} replication (pin the committed Stage-1 results_{fam}.json first)")
    if hashlib.sha256(rp.read_bytes()).hexdigest() != a.results_sha256.lower():
        raise c12.Refused(f"results_{fam}.json sha256 differs from --results-sha256: Stage 2 stays closed")
    return res, adv


@_guarded
def cmd_rep(a):
    c12 = _c12()
    fam = _family(a)
    if fam not in ("M", "O", "E"):
        raise c12.Refused(f"family {fam} has no Stage 2 in this runner")
    freeze_sha = _freeze(a, fam)
    sha = _rules(a, fam)
    root = _root(a)
    _res, adv = _pinned_stage1(a, fam, root)
    if fam == "M":
        from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415

        rdir = _hist(a) / m12.FRAME_RUN
        census = json.loads((root / "census_M.json").read_text())["M"]
        c12.verify_fetch(rdir, (m12.PRICES_STATUS,), "say_prices")
        seal = c12.verify_holdout_seal(rdir, "cb12_say_holdout_SEAL.json", _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
        body = m12.rep_m(rdir, census, adv, seal, k2=a.stage2_k)
    elif fam == "E":
        from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415

        # E1 advanced -> its replication AND the economic check E2 run on the same Stage-2 units (CB12-E Stage 2)
        adv = c12.FAMILY_REP_TESTS["E"]
        _fsha, entry = _freeze_entry(a, "E")
        rdir = _hist(a) / e12.FRAME_RUN
        c12.verify_fetch(rdir, (e12.PRICES_STATUS,), "quake_prices")
        _e_frame_rules_guard(rdir, _rules(a, "E"))
        live = _hist(a) / e12.LIVE_RUN
        model, maxima = e12.model_inputs(e12.load_frame(rdir))
        body = e12.rep_e(live, adv, frozen_epoch=_o_frozen_epoch(entry), now=time.time(), model=model, maxima=maxima, gamma_rows=e12.open_live_outcomes(live, "rep-E"), k2=a.stage2_k)
    else:
        from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415

        _fsha, entry = _freeze_entry(a, "O")
        orun = _hist(a) / o12.RUN
        win = o12.windows(orun, _o_frozen_epoch(entry), time.time())
        o12.require_outcomes_final(orun, o12.window_dates(win["w2"]))
        body = o12.rep_o(orun, win["w2"], _o_convention(a, entry), adv, earnings_identified=_o_earnings_identified(a), k2=a.stage2_k, frozen_epoch=_o_frozen_epoch(entry))
    doc = {**body, "rules_sha256": sha, "freeze_sha256": freeze_sha, "stage1_results_sha256": a.results_sha256.lower()}
    rsha = c12.write_results_once(Path(a.out) if a.out else root / f"results_{fam}_rep.json", doc)
    lines = {t: _line(doc[f"{t}_rep"], advance_key="stage2_pass_alpha_over_k") for t in adv}
    c12.log_family(fam, lines, replication=True, trials_path=_tp(a), results_sha256=rsha, n_triggered=len(adv), placebos=_placebos({t: doc[f"{t}_rep"] for t in adv}, adv),
                   role="prospective" if fam in ("O", "E") else c12.EVIDENCE_ROLE_HIST)
    return 0, {"status": f"rep_{fam}_complete", "tests": list(adv)}


# ---- q0260 / q0261 CB12-O ----------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_opt_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "opt-smoke")
    out = c12.refuse_path(Path(a.out) if a.out else o12.SMOKE_V2_DEFAULT)
    if out.exists():
        raise c12.Refused(f"smoke result {out} already exists; it is write-once")
    shas = {"common": _rules(a, "common"), "O": _rules(a, "O")}
    now = time.time()
    if not o12.in_smoke_session(now):  # exit 75 while waiting, a clean idle heartbeat at least every 10 h (the queue's 48-tempfail cap never fires over a weekend)
        return 0, cm.idle(out.parent / "opt_smoke_wait", "opt-smoke runs only inside a regular US session (10:00-15:45 ET); pending", now)
    src = _o_sources(a)
    try:
        crit, detail = sm.collect_checks(("O",), {"o_sources": src, "now": now}, src.pm)
    except cm.ApiError as exc:
        _not_now_if_transient("a CB12-O source", exc)
        raise
    except RuntimeError:
        raise cm.NotNow("opt-smoke: a request failed (network); nothing written") from None
    need = set(o12.SMOKE_NEEDS)
    res = {"smoke_version": c12.SMOKE_VERSION, "family_smoke_versions": {"O": o12.SMOKE_FAMILY_VERSION}, "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now),
           "counts_only": True, "families_covered": ["O"], "requests": src.pm.requests + src.ext.requests, "criteria": crit, "pass": all(v for k, v in crit.items() if k in need),
           "iv_convention": detail["O"]["o_iv_convention_checked"]["choice"], "detail": detail, "no_unit_kept": True,
           "consequences": {"a failed needed criterion": "O not testable (source), counted", "iv_convention": "written into the O freeze entry (iv_convention) before the freeze; none -> Phi(d2) units excluded"}}
    cm.write_once_json(out, res)
    c12.log_descriptive("opt_smoke", {"pass": res["pass"], "criteria": crit, "iv_convention": res["iv_convention"], "smoke_path": str(out)}, trials_path=_tp(a), role="prospective")
    return 0, {"smoke": res["pass"], "criteria": crit, "iv_convention": res["iv_convention"], "written": str(out), "requests": res["requests"]}


@_guarded
def cmd_opt_live(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_o as o12  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "opt-live")
    sha = _rules(a, "O")
    _fsha, entry = _freeze_entry(a, "O")
    frozen = _o_frozen_epoch(entry)
    root = c12.require_output_root(_hist(a) / o12.RUN)
    dd = Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS
    cap = int(a.disk_cap_gb * 1024**3)
    res = o12.opt_live_tick(root, now=time.time(), src=_o_sources(a), rules_sha=sha, frozen_epoch=frozen,
                            disk_check=lambda: c12.require_disk(dd, a.data_dumps_cap_gb, cap), root_cap_bytes=cap, sleep=time.sleep)
    if res.get("status") in ("outcomes", "daily"):
        cm.write_json_atomic(root / "windows.json", {**o12.windows(root, frozen, time.time()), "updated_utc": cm.iso(time.time())})
    return 0, res


# ---- q0257 CB12-E collector ---------------------------------------------------------------------------------------------------------------------


def _e_sources(a):
    from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    live = None if getattr(a, "standalone", False) else hb.live_pass_or_lock
    pm = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    ext = hb.Limiter(hb.httpx_transport(), rps=e12.USGS_RPS, live_check=live)
    return e12.LiveSources(pm, ext)


@_guarded
def cmd_quake_live(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_e as e12  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "quake-live")
    sha = _rules(a, "E")
    _fsha, entry = _freeze_entry(a, "E")
    frozen = _o_frozen_epoch(entry)
    root = c12.require_output_root(_hist(a) / e12.LIVE_RUN)
    dd = Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS
    cap = int(a.disk_cap_gb * 1024**3)
    res = e12.quake_live_tick(root, now=time.time(), src=_e_sources(a), rules_sha=sha, frozen_epoch=frozen, disk_check=lambda: c12.require_disk(dd, a.data_dumps_cap_gb, cap), sleep=time.sleep)
    return 0, res


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c12 = _c12()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch12 root (default data-dumps/research_lab/creative_batch12)")
        q.add_argument("--history-root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--cv-root", default=None, help="cross_venue root (default data-dumps/research_lab/cross_venue; cross_venue_live is always refused)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)

    def net(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c12.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("freeze-part", help="print one part of the CB12 freeze declaration")
    q.add_argument("--part", required=True, choices=c12.FAMILY_PARTS)
    q.set_defaults(fn=cmd_freeze_part)

    q = sub.add_parser("smoke", help="q0240")
    common(q, rps=1.0)
    q.add_argument("--out", default=None)
    q.add_argument("--families", default="auto", help="auto (every family with a module) or a comma list of M,E,F,X,O")
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0241")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--base-path", default=None, help="CB11 q0221 key file (default creative_batch11/exclusion_keys.csv.gz)")
    q.add_argument("--base-sha256", default=None, help="MANDATORY pin of the CB11 q0221 key file (the coordinator fills it from `sha256sum` on the host)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("say-frame", help="q0242")
    common(q)
    net(q, disk_cap=0.005)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.set_defaults(fn=cmd_say_frame)

    q = sub.add_parser("say-prices", help="q0243")
    common(q)
    net(q, disk_cap=0.08)
    q.set_defaults(fn=cmd_say_prices)

    q = sub.add_parser("quake-frame", help="q0244 (CB12-E frame and USGS catalogue)")
    common(q)
    net(q, disk_cap=0.03)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--usgs-rps", type=float, default=1.0)
    q.set_defaults(fn=cmd_quake_frame)

    q = sub.add_parser("quake-prices", help="q0245 (CB12-E prices-history)")
    common(q)
    net(q, disk_cap=0.01)
    q.set_defaults(fn=cmd_quake_prices)

    q = sub.add_parser("quake-live", help="q0257 (CB12-E collector; cron)")
    common(q, rps=1.0)
    net(q, disk_cap=0.01)
    q.add_argument("--freeze-spec", default=None)
    q.set_defaults(fn=cmd_quake_live)

    q = sub.add_parser("seal", help="q0248")
    common(q)
    q.add_argument("--family", default="auto", help="M | auto (every implemented family; one still fetching is pending)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_seal)

    q = sub.add_parser("census", help="q0249 (M) / q0251 (X) / q0262 (O) / q0266 (E)")
    common(q)
    q.add_argument("--family", required=True, help="M | X | O | E (one family per job)")
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--opt-smoke", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--allow-unpinned-c1", action="store_true", help="tests only: skip the X input pins and the C1 count assertion")
    q.add_argument("--census-tag", default="", help="file-name suffix of the census (e.g. _v2: a census re-run under amended code; the earlier file is kept)")
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0252 (M) / q0255 (X) / q0263 (O) / q0253 (E)")
    common(q)
    q.add_argument("--family", required=True, help="M | X | O | E")
    q.add_argument("--opt-smoke", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--census", default=None)
    q.add_argument("--census-tag", default="", help="reads census_<family><tag>.json (default: the untagged file)")
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--allow-unpinned-c1", action="store_true", help="tests only")
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("rep", help="q0256 (M) / q0264 (O) / q0258 (E)")
    common(q)
    q.add_argument("--family", required=True, help="M | O | E")
    q.add_argument("--opt-smoke", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--stage2-k", type=int, default=None)
    q.add_argument("--results-sha256", default=None, help="pinned sha256 of the committed Stage-1 results_<family>.json (required)")
    q.set_defaults(fn=cmd_rep)

    q = sub.add_parser("opt-smoke", help="q0260 (CB12-O smoke, one live checkpoint dry run)")
    common(q)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_opt_smoke)

    q = sub.add_parser("opt-live", help="q0261 (CB12-O collector; cron)")
    common(q)
    net(q, disk_cap=0.3)
    q.add_argument("--freeze-spec", default=None)
    q.set_defaults(fn=cmd_opt_live)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
