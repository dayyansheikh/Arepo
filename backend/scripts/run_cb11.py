# ruff: noqa: E501
"""CB11 runner (docs/research_lab/CREATIVE_BATCH_11.md section 4, q0220-q0239). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA ONLY: no
edge, calibration or profitability claim.

    python scripts/run_cb11.py rules                           # write docs/research_lab/seals/cb11_rules.json (v2: part W hashed; P / A rules live in the separate
                                                               #        cb11_pa_rules.json; commit before q0220)
    python scripts/run_cb11.py smoke ...                       # q0220: frames, loader fixture, Gamma politics paging, prices-history, Data API reach, Wikipedia
                                                               #        summary + pageview lag, closed=false window count, OOV2 pin attempt; counts only, WRITE-ONCE
    python scripts/run_cb11.py exclusion-keys ...              # q0221: h8_tail_b keys + every sampled set (h2/h3 samples mandatory, pinned) + seal copies + staged C1/T5 ids
                                                               #        (mandatory: exit 75 until staged; --allow-absent-c1-t5 only by explicit decision) (resumable)
    python scripts/run_cb11.py w-frame | w-prints | w-censoring ...   # q0222 / q0223 / q0224
    python scripts/run_cb11.py seal --family W|auto ...        # q0230 (W holdout prints); P and A families join with their commit
    python scripts/run_cb11.py census --family W               # q0231: counts only; gates GWC, GW, GW2; coverage audit; MDEs
    python scripts/run_cb11.py screen --family W               # q0232 (refuses before the CB11 W freeze)
    python scripts/run_cb11.py stage1-label                    # batch-Holm label over W1, W2, P1, P2, A1, A2 (k1 = 6; not run -> p = 1)
    python scripts/run_cb11.py rep --family W                  # q0235

Exit codes: 0 ok / transient pause / declared stall (non-stalling chain: the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules
hash, smoke result exists or missing, run id, refused root, declared argument changed, before the CB11 freeze for analysis jobs, HOLDOUT, guarded file, results
exist); 4 disk budget; 75 (EX_TEMPFAIL) a time gate ("not yet"), data-dumps / free-disk headroom, an upstream job not finished or a transient network give-up:
"pending", no trials line.
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
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.01, "w-frame": 0.02, "w-prints": 0.03, "w-censoring": 0.001}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "w-prints": 2.0, "w-censoring": 2.0, "seal": 2.0}


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


def _c11():
    from astrolabe.research_lab import cb11_common as c11  # noqa: PLC0415

    return c11


def _root(a) -> Path:
    c11 = _c11()
    return c11.refuse_path(Path(a.root) if getattr(a, "root", None) else c11.CB11_DIR)


def _hist(a) -> Path:
    c11 = _c11()
    return c11.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c11.HIST_ROOT)


def _declared(a, cmd: str) -> None:
    c11 = _c11()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c11.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c11.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(rps=a.rps, data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _rules(a, part: str = "W") -> str:
    """Verify one rules part (W jobs: part W only; P / A jobs verify part PA). Returns that part's sha256."""
    c11 = _c11()
    return c11.verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False), part=part)


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _smoke_path(a) -> Path:
    return Path(a.smoke) if getattr(a, "smoke", None) else _c11().SMOKE_DEFAULT


def _keys_path(a) -> Path:
    return Path(a.exclusion_keys) if getattr(a, "exclusion_keys", None) else _c11().EXCLUSION_KEYS_DEFAULT


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


# ---- rules ------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c11 = _c11()
    try:
        out = c11.write_rules(Path(a.path) if a.path else None)
        doc = c11.rules_file_doc()
    except c11.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    parts = doc["parts"]
    _emit({"written": str(out), "rules_version": doc["rules_version"], "rules_sha256": parts["W"]["rules_sha256"], "funcs_sha256": parts["W"]["funcs_sha256"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256")} for k, v in parts.items()}})
    return 0


# ---- q0220 smoke ------------------------------------------------------------------------------------------------------------------------------


_TRANSIENT_STATUS = re.compile(r"status (None|0|408|429|5\d\d)\b")


def _not_now_if_transient(source: str, exc: Exception) -> None:
    """A rate-limit, timeout or server-side status from a smoke source is a 'not now' (exit 75, nothing written), never a write-once FAIL."""
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if _TRANSIENT_STATUS.search(str(exc)):
        raise cm.NotNow(f"smoke: {source} returned a transient status ({str(exc)[:80]}); nothing written") from None


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb11_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c11 = _c11()
    _declared(a, "smoke")
    out = c11.refuse_path(Path(a.out) if a.out else c11.SMOKE_DEFAULT)
    if out.exists():
        raise c11.Refused(f"smoke result {out} already exists; it is write-once")
    sha = _rules(a)
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    limw = hb.Limiter(_wiki_transport(a), rps=min(a.rps, 1.0), live_check=None)
    now = time.time()
    try:
        frames = sm.smoke_frames(_hist(a))
        loader = sm.smoke_loader_fixture()
        try:
            pol = sm.smoke_gamma_politics(lim)
        except cm.ApiError as exc:
            _not_now_if_transient("gamma politics", exc)
            pol = {"pass": False, "markets": [], "error": str(exc)[:100]}
        markets = pol.get("markets") or []
        try:
            ph = sm.smoke_prices_history(lim, markets)
        except cm.ApiError as exc:
            _not_now_if_transient("prices-history", exc)
            ph = {"pass": False, "error": str(exc)[:100]}
        try:
            dapi = sm.smoke_data_api(lim, markets)
        except cm.ApiError as exc:
            _not_now_if_transient("data-api", exc)
            dapi = {"pass": False, "error": str(exc)[:100]}
        try:
            cw = sm.smoke_censor_window(lim)
        except cm.ApiError as exc:
            _not_now_if_transient("gamma window count", exc)
            cw = {"pass": False, "error": str(exc)[:100]}
        try:
            ws = sm.smoke_wiki_summary(limw)
            wl = sm.smoke_wiki_lag(limw, now)
        except cm.ApiError as exc:
            _not_now_if_transient("wikipedia", exc)
            ws, wl = {"pass": False, "error": str(exc)[:100]}, {"pass": False}
        oov2 = sm.smoke_oov2(lim)
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    crit = {"w_frames": frames["pass"], "w_loader": loader["pass"], "gamma_pol_paging": pol["pass"], "prices_history": ph["pass"], "data_api_reach": dapi["pass"],
            "wiki_summary": ws["pass"], "wiki_lag": wl["pass"], "w_censor_window": cw["pass"]}
    res = {"smoke_version": sm.SMOKE_VERSION, "rules_sha256": sha, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True,
           "requests": lim.requests + limw.requests, "criteria": crit, "pass": all(crit.values()), "frames": frames, "loader": loader,
           "gamma_politics": {k: v for k, v in pol.items() if k != "markets"}, "prices_history": ph, "data_api": dapi, "censor_window": cw, "wiki_summary": ws, "wiki_lag": wl, "oov2": oov2,
           "consequences": {"w_frames / w_loader / w_censor_window fail": "W not testable (source), counted", "data_api_reach fails": "W2, P and A not testable (source), counted",
                            "gamma_pol_paging / prices_history fail": "P not testable (source), counted", "wiki_summary / wiki_lag fail": "A not testable (source), counted "
                            "(wiki_lag fail: lag 72 h and origin X + 4 d, outcome-blind, before the freeze)", "oov2": "gates only the uncounted q0238 variant",
                            "rule": "jobs downstream stall (exit 0, label carried); no rule is re-fitted"}}
    cm.write_once_json(out, res)
    c11.log_descriptive("smoke", {"pass": res["pass"], "criteria": crit, "smoke_path": str(out)}, trials_path=_tp(a))
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": res["requests"]}


def _wiki_transport(a):
    from astrolabe.research_lab import cb11_smoke as sm  # noqa: PLC0415

    return sm.wiki_transport()


# ---- q0221 exclusion keys ---------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c11 = _c11()
    _declared(a, "exclusion-keys")
    sha = _rules(a)
    hist = _hist(a)
    m = c11.exclusion_keys(_root(a), hb.httpx_transport(), rules_sha=sha, hist_root=hist, base_sha256=a.base_sha256 or c11.H8_TAIL_B_KEYS_SHA256,
                           seals_dir=Path(a.seals_dir) if a.seals_dir else None, external_dir=Path(a.external_dir) if a.external_dir else None,
                           cb8_root=Path(a.cb8_root) if a.cb8_root else hist.parent / "creative_batch8", is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed,
                           disk_cap=int(a.disk_cap_gb * 1024**3), allow_absent_c1_t5=bool(a.allow_absent_c1_t5), **_net_kw(a))
    return _result(m)


# ---- q0222 - q0224 W data -----------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_w_frame(a):
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415

    c11 = _c11()
    _declared(a, "w-frame")
    sha = _rules(a)
    m = w.w_frame(_root(a), _hist(a), rules_sha=sha, smoke_path=_smoke_path(a), exclusion_keys_path=_keys_path(a), seals_dir=Path(a.seals_dir) if a.seals_dir else None, now=time.time(),
                  data_dumps=Path(a.data_dumps) if a.data_dumps else c11.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb, disk_cap=int(a.disk_cap_gb * 1024**3),
                  h2_sha=None if a.allow_unpinned_frames else c11.H2_FRAME_SHA256, h3_sha=None if a.allow_unpinned_frames else c11.H3_FRAME_SHA256)
    return _result(m)


@_guarded
def cmd_w_prints(a):
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "w-prints")
    sha = _rules(a)
    m = w.w_prints(_hist(a), _root(a) / w.FRAME_RUN, hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), smoke_path=_smoke_path(a), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_w_censoring(a):
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "w-censoring")
    sha = _rules(a)
    m = w.w_censoring(_root(a), _root(a) / w.FRAME_RUN, hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0230 seal --------------------------------------------------------------------------------------------------------------------------------


def _families(spec: str) -> list[str]:
    fam = [x.strip() for x in str(spec).split(",") if x.strip()]
    allowed = ("W", "P", "A", "auto")
    bad = [x for x in fam if x not in allowed]
    if bad:
        raise _c11().Refused(f"unknown seal family {bad}")
    return fam


def seal_w(a) -> dict:
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c11 = _c11()
    sha = _rules(a)
    wdir = _root(a) / w.FRAME_RUN
    rows = [{"market_id": r["market_id"], "event_ids": r["event_id"]} for r in c11.read_csv_gz(wdir / w.HOLD_DIR / "w2_sample_hold.csv.gz")] if (wdir / w.HOLD_DIR / "w2_sample_hold.csv.gz").exists() else []
    pdir = _hist(a) / c11.H11_WPRINTS
    return c11.seal_holdout(pdir, family="wprints", statuses=(w.PRINTS_STATUS,), copy_name="cb11_wprints_holdout_SEAL.json", rows=rows, rules_sha=sha, transport=hb.httpx_transport(),
                            seals_dir=Path(a.seals_dir) if a.seals_dir else None, rps=a.rps, live_check=None if a.standalone else hb.live_pass_or_lock,
                            is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed)


SEAL_FAMILIES = {"W": seal_w}


@_guarded
def cmd_seal(a):
    c11 = _c11()
    _declared(a, "seal")
    fams = _families(a.family)
    if "auto" in fams:
        fams = sorted(SEAL_FAMILIES)
    done, pending = {}, []
    for f in fams:
        fn = SEAL_FAMILIES.get(f)
        if fn is None:
            raise c11.Refused(f"seal family {f!r} is not implemented in this runner")
        try:
            done[f] = fn(a)
        except c11.NotNow as exc:
            pending.append(f"{f}: {exc}")
    if pending:
        raise c11.NotNow("; ".join(pending))
    return 0, {"status": "seal_all_complete", "families": done}


# ---- q0231 census ------------------------------------------------------------------------------------------------------------------------------


def census_w_block(a) -> dict:
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415

    c11 = _c11()
    root, hist = _root(a), _hist(a)
    wdir, cdir, pdir = root / w.FRAME_RUN, root / w.CENSOR_RUN, hist / c11.H11_WPRINTS
    st = c11.stall_of(wdir)
    if st:
        lab = st.get("label")
        return {"status": "stalled", "stall": st, "label_W1": lab, "label_W2": lab, "label_W1_hold": lab, "label_W2_hold": lab, "w1_runs": False, "w2_runs": False}
    committed = not getattr(a, "allow_uncommitted_rules", False)
    c11.require_complete(wdir, (w.FRAME_STATUS,), "w_frame (q0222)")
    w.verify_hold_seal(wdir, Path(a.seals_dir) if getattr(a, "seals_dir", None) else None, require_committed=committed)
    stc = c11.stall_of(cdir)
    if stc:
        lab = stc.get("label")
        return {"status": "stalled", "stall": stc, "label_W1": lab, "label_W2": lab, "label_W1_hold": lab, "label_W2_hold": lab, "w1_runs": False, "w2_runs": False}
    c11.require_complete(cdir, (w.CENSOR_STATUS,), "w_censoring (q0224)")
    censoring = json.loads((cdir / "censoring.json").read_text())
    stp = c11.stall_of(pdir)
    if stp:
        return w.census_w(wdir, hist, censoring, None, prints_stall=stp)
    c11.require_complete(pdir, (w.PRINTS_STATUS,), "w_prints (q0223)")
    c11.verify_holdout_seal(pdir, "cb11_wprints_holdout_SEAL.json", Path(a.seals_dir) if getattr(a, "seals_dir", None) else None, require_committed=committed)
    return w.census_w(wdir, hist, censoring, w.coverage_audit(pdir, wdir))


@_guarded
def cmd_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c11 = _c11()
    root = _root(a)
    fam = [x.strip() for x in a.family.split(",") if x.strip()]
    if fam == ["W"]:
        out = Path(a.out) if a.out else root / "census_W.json"
        if out.exists():
            raise c11.Refused(f"{out} exists; the census is written once")
        sha = _rules(a)  # N5: the census verifies the W rules part like every other job
        doc = {"version": "cb11-census-W-v2", "counts_only": True, "rules_sha256": sha, "W": census_w_block(a)}
        cm.write_once_json(out, doc)
        c11.log_descriptive("census_W", {"census_sha256": cm.sha_obj(doc), "path": str(out)}, trials_path=_tp(a))
        return 0, {"status": "census_complete", "written": str(out), "label_W1": doc["W"].get("label_W1"), "label_W2": doc["W"].get("label_W2")}
    raise c11.Refused(f"census family {a.family!r} is not implemented in this runner")


# ---- q0232 screens -----------------------------------------------------------------------------------------------------------------------------


def _w_effect(r: dict) -> dict:
    return {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "n": r.get("n") or r.get("n_filled"), "verdict": r.get("verdict")}


def _by_triage(doc: dict, trials_path: Path | None) -> dict:
    """BY label (q = 0.10 over ``battery2.cumulative_count()`` at the run): triage only, never the gate. Recorded with the denominator (N6)."""
    from astrolabe.research_lab import battery2, provenance  # noqa: PLC0415

    tp = trials_path or provenance.TRIALS_PATH
    try:
        total = int(battery2.cumulative_count(tp)["total"])
    except (OSError, ValueError, KeyError) as exc:
        return {"unavailable": f"cumulative count unreadable: {type(exc).__name__}", "trials_path": str(tp)}
    res = {t: {"p": doc[t].get("p", 1.0), "testable": doc[t].get("testable", False)} for t in ("W1", "W2") if isinstance(doc.get(t), dict)}
    by = battery2.apply_by2(res, total)
    return {"cumulative_count": total, "q": by["q"], "m_total": by["m_total"], "survivors": by["survivors"],
            "per_test": {t: {"p_by_cumulative": r["p_by_cumulative"], "pass_by_cumulative": r["pass_by_cumulative"]} for t, r in res.items()}, "triage_only": True}


@_guarded
def cmd_screen(a):
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415

    c11 = _c11()
    if a.family != "W":
        raise c11.Refused(f"screen family {a.family!r} is not implemented in this runner")
    freeze_sha = c11.require_freeze("W", Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha = _rules(a)
    root, hist = _root(a), _hist(a)
    cpath = Path(a.census) if a.census else root / "census_W.json"
    if not cpath.exists():
        raise c11.NotNow("census_W.json missing (q0231 first)")
    census = json.loads(cpath.read_text())
    wdir, cdir, pdir = root / w.FRAME_RUN, root / w.CENSOR_RUN, hist / c11.H11_WPRINTS
    if not c11.stall_of(wdir):
        c11.verify_fetch(wdir, (w.FRAME_STATUS,), "w_frame")
        w.verify_hold_seal(wdir, Path(a.seals_dir) if a.seals_dir else None, require_committed=not a.allow_uncommitted_rules)
        # N5: the screen re-checks the fetch manifests and file hashes of the data it is about to open (the census checked them once, earlier)
        if not (census.get("W") or {}).get("label_W1") or not (census.get("W") or {}).get("label_W2"):
            if not c11.stall_of(cdir):
                c11.verify_fetch(cdir, (w.CENSOR_STATUS,), "w_censoring")
            if not c11.stall_of(pdir):
                c11.verify_fetch(pdir, (w.PRINTS_STATUS,), "w_prints")
    doc = {**w.screen_w(wdir, hist, census), "rules_sha256": sha, "freeze_W_sha256": freeze_sha, "census_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(),
           "written_epoch": time.time()}
    doc["by_triage"] = _by_triage(doc, _tp(a))
    rsha = c11.write_results_once(Path(a.out) if a.out else root / "results_W.json", doc)
    for tid in ("W1", "W2"):
        r = doc[tid]
        pl = r.get("placebo") if tid == "W1" else None
        eff = r.get("R_B0") if tid == "W1" else r.get("effect")
        c11.log_test("W", tid, {**_w_effect(r), "effect": eff}, trials_path=_tp(a), results_sha256=rsha,
                     placebo={"note": "W1 category x month target permutation", "advance_rate": pl.get("advance_rate"), "n_draws": pl.get("n_draws")} if pl else None)
    return 0, {"status": "screen_W_complete", **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in ("W1", "W2")}}


@_guarded
def cmd_stage1_label(a):
    c11 = _c11()
    root = _root(a)
    pv: dict[str, float | None] = dict.fromkeys(c11.STAGE1_HOLM_FAMILY)
    for name, tests in c11.STAGE1_RESULTS.items():
        p = root / name
        if p.exists():
            d = json.loads(p.read_text())
            for t in tests:
                if isinstance(d.get(t), dict) and d[t].get("testable"):
                    pv[t] = float(d[t].get("p", 1.0))
    return 0, {"batch_holm": c11.batch_holm_label(pv), "note": "label only; not run / pending / not testable enter with p = 1; k1 = 6 fixed"}


# ---- q0235 rep ----------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_rep(a):
    from astrolabe.research_lab import cb11_w as w  # noqa: PLC0415

    c11 = _c11()
    if a.family != "W":
        raise c11.Refused(f"rep family {a.family!r} is not implemented in this runner")
    freeze_sha = c11.require_freeze("W", Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha = _rules(a)
    root, hist = _root(a), _hist(a)
    derived = c11.stage2_k(root, own="W")  # N7: W's rep depends only on results_W.json; unfinished P / A tests are assumed to advance (k only too large)
    if a.stage2_k is not None and int(a.stage2_k) != derived["k"]:
        raise c11.Refused(f"--stage2-k {a.stage2_k} differs from the k derived from the Stage-1 results ({derived['k']}: {derived['advanced']})")
    resw = json.loads((root / "results_W.json").read_text())
    adv = tuple(t for t in ("W1", "W2") if (resw.get(t) or {}).get("advance") is True)
    if not adv:
        raise c11.Refused("neither W1 nor W2 advanced: there is no W Stage 2")
    if not a.w_results_sha256:
        raise c11.Refused("--w-results-sha256 is required for the W replication (pin the committed Stage-1 results_W.json before W_hold is opened)")
    if hashlib.sha256((root / "results_W.json").read_bytes()).hexdigest() != a.w_results_sha256.lower():
        raise c11.Refused("results_W.json sha256 differs from --w-results-sha256: W_hold stays closed")
    census = json.loads((root / "census_W.json").read_text())
    committed = not a.allow_uncommitted_rules
    c11.verify_fetch(root / w.FRAME_RUN, (w.FRAME_STATUS,), "w_frame")
    c11.verify_fetch(hist / c11.H11_WPRINTS, (w.PRINTS_STATUS,), "w_prints")
    c11.verify_holdout_seal(hist / c11.H11_WPRINTS, "cb11_wprints_holdout_SEAL.json", Path(a.seals_dir) if a.seals_dir else None, require_committed=committed)
    doc = {**w.rep_w(root / w.FRAME_RUN, hist, census, adv, derived["k"], seals_dir=Path(a.seals_dir) if a.seals_dir else None, committed_seals=committed), "rules_sha256": sha,
           "freeze_W_sha256": freeze_sha, "stage2_k_derived": derived}
    rsha = c11.write_results_once(Path(a.out) if a.out else root / "results_W_rep.json", doc)
    for t in adv:
        r = doc[f"{t}_rep"]
        c11.log_test("W", f"{t}-rep", {"p": r.get("p", 1.0), "advance": r.get("stage2_pass_alpha_over_k"), "testable": r.get("testable"),
                                       "effect": r.get("R_B0") if t == "W1" else r.get("effect"), "n": r.get("n") or r.get("n_filled"), "verdict": r.get("verdict")},
                     replication=True, trials_path=_tp(a), results_sha256=rsha)
    return 0, {"status": "rep_W_complete", "tests": list(adv)}


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c11 = _c11()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch11 root (default data-dumps/research_lab/creative_batch11)")
        q.add_argument("--history-root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)

    def net(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c11.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("smoke", help="q0220")
    common(q, rps=1.0)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0221")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--base-sha256", default=None, help="pin of the h8_tail_b key file (default: the pin in the rules)")
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--external-dir", default=None, help="staged C1 / T5 id lists (default creative_batch11/external_ids)")
    q.add_argument("--cb8-root", default=None)
    q.add_argument("--allow-absent-c1-t5", action="store_true",
                   help="record the C1 / T5 id lists as permanently absent instead of waiting (exit 75) for them to be staged; never set in a queue draft")
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("w-frame", help="q0222")
    common(q)
    net(q, disk_cap=0.02)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--allow-unpinned-frames", action="store_true", help="tests only: skip the frame sha256 pins")
    q.set_defaults(fn=cmd_w_frame)

    q = sub.add_parser("w-prints", help="q0223")
    common(q)
    net(q, disk_cap=0.03)
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_w_prints)

    q = sub.add_parser("w-censoring", help="q0224")
    common(q)
    net(q, disk_cap=0.001)
    q.set_defaults(fn=cmd_w_censoring)

    q = sub.add_parser("seal", help="q0230")
    common(q)
    q.add_argument("--family", default="auto", help="W | auto (P and A join with their commit)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_seal)

    q = sub.add_parser("census", help="q0231 (W)")
    common(q)
    q.add_argument("--family", required=True, help="W (P,A join with their commit)")
    q.add_argument("--out", default=None)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0232 (W)")
    common(q)
    q.add_argument("--family", choices=("W", "P", "A"), required=True)
    q.add_argument("--census", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("stage1-label")
    common(q)
    q.set_defaults(fn=cmd_stage1_label)

    q = sub.add_parser("rep", help="q0235 (W)")
    common(q)
    q.add_argument("--family", choices=("W", "P", "A"), required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--stage2-k", type=int, default=None)
    q.add_argument("--w-results-sha256", default=None, help="W family: pinned sha256 of the committed Stage-1 results_W.json (required)")
    q.set_defaults(fn=cmd_rep)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
