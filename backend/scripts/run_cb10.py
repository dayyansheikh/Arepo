# ruff: noqa: E501
"""CB10 runner (docs/research_lab/CREATIVE_BATCH_10.md section 4, q0200-q0212). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA
ONLY: no edge, calibration or profitability claim.

    python scripts/run_cb10.py rules                          # write docs/research_lab/seals/cb10_rules.json (commit before q0200)
    python scripts/run_cb10.py smoke ...                      # q0200: Deribit paging + iv range, ladder frame / flags / regex, live flags, Data API paging,
                                                              #        tx aggregation fixture, Gamma whitelist; counts only, WRITE-ONCE (may run before T_seal)
    python scripts/run_cb10.py exclusion-keys ...             # q0201: CB9 q0182 keys + CB9 P and K/D frame ids + seal copies since q0182
    python scripts/run_cb10.py dlad-frame ...                 # q0202: D frame, series-date exclusion, prints -> origin rows, guarded outcomes
    python scripts/run_cb10.py deribit-trades ...             # q0203: Deribit trades per origin time, perpetual bars, DVOL, guarded settlement index
    python scripts/run_cb10.py brk-frame | brk-prints | brk-seal ...   # q0204-q0206
    python scripts/run_cb10.py census                         # q0207: counts only (D and B), gates GD / GDP / GB / GB2, audits, frozen B1 weights
    python scripts/run_cb10.py screen --family D|B            # q0208 / q0209 (refuse before the CB10 freeze)
    python scripts/run_cb10.py stage1-label                   # batch-Holm label over D1, B1, B2 (k1 = 3; not run -> p = 1)
    python scripts/run_cb10.py dlad-live --origin auto ...    # q0210: one Stage-2 cron run (only if D1 advanced; outside the queue lanes)
    python scripts/run_cb10.py rep --family D|B               # q0211 / q0212

Exit codes: 0 ok / transient pause / declared stall (non-stalling chain: the label is carried, never exit 2) / declared end state; 1 error; 2 refusal
(rules hash, smoke result exists or missing, run id, refused root, declared argument changed, before T_seal for net-lane jobs, before the CB10 freeze
for analysis jobs, HOLDOUT, guarded file, trigger not met, results exist); 4 disk budget; 75 (EX_TEMPFAIL) data-dumps / free-disk headroom or an
upstream job not finished: "pending", no trials line.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.005, "dlad-frame": 0.01, "deribit-trades": 0.02, "brk-frame": 0.005, "brk-prints": 0.06, "dlad-live": 0.01}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "dlad-frame": 2.0, "deribit-trades": 2.0, "brk-frame": 2.0, "brk-prints": 2.0, "brk-seal": 2.0, "dlad-live": 1.0}


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


def _c10():
    from astrolabe.research_lab import cb10_common as c10  # noqa: PLC0415

    return c10


def _root(a) -> Path:
    c10 = _c10()
    return c10.refuse_path(Path(a.root) if getattr(a, "root", None) else c10.CB10_DIR)


def _hist(a, sub: str) -> Path:
    c10 = _c10()
    return c10.refuse_path((Path(a.history_root) if getattr(a, "history_root", None) else c10.HIST_ROOT) / sub)


def _declared(a, cmd: str) -> None:
    c10 = _c10()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c10.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c10.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(rps=a.rps, data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _rules(a) -> str:
    c10 = _c10()
    return c10.verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False))


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"),
               "transient": m.get("transient")}


def _commit_epoch(path: Path) -> float | None:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", str(path)], capture_output=True, text=True, cwd=ROOT, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return float(out) if out else None


def _smoke_path(a) -> Path:
    return Path(a.smoke) if getattr(a, "smoke", None) else _c10().SMOKE_DEFAULT


def _keys_path(a) -> Path:
    return Path(a.exclusion_keys) if getattr(a, "exclusion_keys", None) else _c10().EXCLUSION_KEYS_DEFAULT


# ---- rules ------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c10 = _c10()
    try:
        out = c10.write_rules(Path(a.path) if a.path else None)
        doc = c10.rules_file_doc()
    except c10.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_sha256": doc["rules_sha256"], "funcs_sha256": doc["funcs_sha256"]})
    return 0


# ---- q0200 smoke ------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c10 = _c10()
    _declared(a, "smoke")
    out = c10.refuse_path(Path(a.out) if a.out else c10.SMOKE_DEFAULT)
    if out.exists():
        raise c10.Refused(f"smoke result {out} already exists; it is write-once")
    sha = _rules(a)
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=None if a.standalone else hb.live_pass_or_lock)
    try:
        try:
            der = dl.smoke_deribit(lim)
        except cm.ApiError as exc:
            der = {"pass": False, "error": str(exc)[:100]}
        try:
            lad = dl.smoke_ladders(lim)
        except cm.ApiError as exc:
            lad = {"pass": False, "whitelist_pass": False, "data_api_cids": [], "error": str(exc)[:100]}
        try:
            live = dl.smoke_live_flags(lim, time.time())
        except cm.ApiError as exc:
            live = {"pass": False, "error": str(exc)[:100]}
        try:
            dapi = dl.smoke_data_api(lim, lad.get("data_api_cids") or [])
        except cm.ApiError as exc:
            dapi = {"pass": False, "error": str(exc)[:100]}
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    fix = dl.smoke_tx_fixture()
    crit = {"deribit": der["pass"], "ladder_frame": lad["pass"], "live_flags": live["pass"], "data_api_paging": dapi["pass"], "tx_aggregation": fix["pass"],
            "whitelist": lad.get("whitelist_pass", False)}
    res = {"smoke_version": dl.SMOKE_VERSION, "rules_sha256": sha, "git_commit": hb._git_commit(), "run_utc": cm.iso(time.time()), "counts_only": True,
           "requests": lim.requests, "criteria": crit, "pass": all(crit.values()), "deribit": der, "ladders": {k: v for k, v in lad.items() if k != "data_api_cids"},
           "live_flags": live, "data_api": dapi, "tx_fixture": fix,
           "consequences": {"deribit / ladder_frame / live_flags fail": "D not testable (source), counted", "data_api_paging / tx_aggregation / whitelist fail": "D and B not testable (source), counted",
                            "rule": "jobs downstream stall (exit 0, label carried); no rule is re-fitted"}}
    cm.write_once_json(out, res)
    c10.log_descriptive("smoke", {"pass": res["pass"], "criteria": crit, "smoke_path": str(out)}, trials_path=Path(a.trials_path) if a.trials_path else None)
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": lim.requests}


# ---- q0201 exclusion keys ------------------------------------------------------------------------------------------------------------------------


def _extra_pins(values: list[str] | None) -> list[dict]:
    c10 = _c10()
    out = []
    for v in values or []:
        parts = str(v).split(":")
        if len(parts) != 3 or len(parts[2]) != 64:
            raise c10.Refused(f"--extra-pin must be NAME:PATH:SHA256, got {v!r}")
        out.append({"name": parts[0], "path": parts[1], "sha256": parts[2]})
    return out


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c10 = _c10()
    _declared(a, "exclusion-keys")
    c10.require_after_t_seal(time.time(), "exclusion-keys")
    sha = _rules(a)
    m = c10.exclusion_keys(_root(a), hb.httpx_transport(), rules_sha=sha, cb9_keys_path=Path(a.cb9_keys) if a.cb9_keys else c10.CB9_KEYS_DEFAULT,
                           cb9_keys_sha256=a.cb9_keys_sha256, seals_dir=Path(a.seals_dir) if a.seals_dir else None, extra_pins=_extra_pins(a.extra_pin),
                           is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed, disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0202 / q0203 D data -----------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_dlad_frame(a):
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "dlad-frame")
    sha = _rules(a)
    m = dl.dlad_frame(_hist(a, _c10().H10_DLAD), hb.httpx_transport(), rules_sha=sha, smoke_path=_smoke_path(a), exclusion_keys_path=_keys_path(a), now=time.time(),
                      disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_deribit(a):
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "deribit-trades")
    sha = _rules(a)
    root = _hist(a, _c10().H10_DLAD)
    m = dl.deribit_fetch(root, hb.httpx_transport(), rules_sha=sha, smoke_path=_smoke_path(a), frame_dir=root / dl.FRAME_RUN, now=time.time(),
                         disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0204 - q0206 B data ------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_brk_frame(a):
    from astrolabe.research_lab import cb10_brk as br  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "brk-frame")
    sha = _rules(a)
    m = br.brk_frame(_hist(a, _c10().H10_BRK), hb.httpx_transport(), rules_sha=sha, smoke_path=_smoke_path(a), exclusion_keys_path=_keys_path(a), now=time.time(),
                     disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_brk_prints(a):
    from astrolabe.research_lab import cb10_brk as br  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "brk-prints")
    sha = _rules(a)
    root = _hist(a, _c10().H10_BRK)
    m = br.brk_prints(root, hb.httpx_transport(), rules_sha=sha, frame_dir=root / br.FRAME_RUN, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_brk_seal(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import cb10_brk as br  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "brk-seal")
    sha = _rules(a)
    root = _hist(a, _c10().H10_BRK)
    out = br.brk_seal(root, rules_sha=sha, frame_dir=root / br.FRAME_RUN, transport=hb.httpx_transport(), seals_dir=Path(a.seals_dir) if a.seals_dir else None,
                      rps=a.rps, live_check=None if a.standalone else hb.live_pass_or_lock, is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed)
    return 0, out


# ---- q0207 census ---------------------------------------------------------------------------------------------------------------------------------


def census_d_block(hroot: Path) -> dict:
    """D census from the FEATURE files only (frame, origins, Deribit trades, bars, DVOL); the guarded files are never opened here."""
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415

    c10 = _c10()
    fdir, ddir = hroot / dl.FRAME_RUN, hroot / dl.DERIBIT_RUN
    for d in (fdir, ddir):
        st = c10.stall_of(d)
        if st:
            return {"status": "stalled", "stall": st, "label_D1": st.get("label"), "d1_runs": False}
    if not (fdir / "origins.csv.gz").exists() or not (ddir / "trades.csv.gz").exists():
        raise c10.NotNow("D census inputs missing (q0202 / q0203 not finished)")
    fman = json.loads((fdir / "manifest.json").read_text())
    hc = dl.haircut_from_deribit(ddir)
    units, info = dl.build_units(fdir, ddir, h=hc.get("h"))
    doc = dl.census_d(units, {"status": fman.get("status"), "reasons": fman.get("reasons"), "drops": fman.get("drops"), "prints": fman.get("prints"), **info})
    doc["haircut_frozen"] = hc
    return doc


def census_b_block(hroot: Path) -> dict:
    from astrolabe.research_lab import cb10_brk as br  # noqa: PLC0415

    c10 = _c10()
    fdir, pdir = hroot / br.FRAME_RUN, hroot / br.PRINTS_RUN
    for d in (fdir, pdir):
        st = c10.stall_of(d)
        if st:
            return {"status": "stalled", "stall": st, "label_B1": st.get("label"), "label_B2": st.get("label"), "weights_frozen": {}}
    if not (pdir / br.SEAL_NAME).exists():
        raise c10.NotNow("B census waits for the seal (q0206)")
    eps, markets = br.load_episodes(pdir, fdir, br.SCREEN, job="census", census=True)
    doc = br.census_b(eps, markets, br.holdout_counts(pdir))
    seal = json.loads((pdir / br.SEAL_NAME).read_text())
    if (seal.get("drops") or {}).get("disjointness") == c10.UNVERIFIED:
        doc["label_B1"] = doc["label_B2"] = "not testable (disjointness unverified)"
    return doc


@_guarded
def cmd_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c10 = _c10()
    root = _root(a)
    out = Path(a.out) if a.out else root / "census.json"
    if out.exists():
        raise c10.Refused(f"{out} exists; the census is written once")
    hd, hbk = _hist(a, c10.H10_DLAD), _hist(a, c10.H10_BRK)
    doc = {"version": "cb10-census-v1", "counts_only": True, "D": census_d_block(hd), "B": census_b_block(hbk)}
    cm.write_once_json(out, doc)
    c10.log_descriptive("census", {"census_sha256": cm.sha_obj(doc), "path": str(out)}, trials_path=Path(a.trials_path) if a.trials_path else None)
    return 0, {"status": "census_complete", "written": str(out), "label_D1": doc["D"].get("label_D1"), "label_B1": doc["B"].get("label_B1"), "label_B2": doc["B"].get("label_B2")}


# ---- q0208 / q0209 screens -------------------------------------------------------------------------------------------------------------------------


def _y_of_factory(outcomes: dict[str, dict]):
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415

    def y_of(u: dict):
        o = outcomes.get(u["market_id"])
        return None if o is None else dl.outcome_y(json.loads(o["outcome_labels"]), json.loads(o["outcome_prices"]))

    return y_of


def screen_d_doc(hroot: Path, census: dict) -> dict:
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415

    cd = census.get("D") or {}
    if not cd.get("d1_runs"):
        return {"D1": {"testable": False, "p": 1.0, "advance": False, "verdict": cd.get("label_D1") or "not testable (census)"}}
    fdir, ddir = hroot / dl.FRAME_RUN, hroot / dl.DERIBIT_RUN
    units, _ = dl.build_units(fdir, ddir, h=(cd.get("haircut_frozen") or {}).get("h"))
    outcomes = {o["market_id"]: o for o in dl.open_guarded(fdir / "outcomes_guarded.csv.gz", "screen-D")}
    settle = {(r["currency"], r["d"]): float(r["index_price"]) for r in dl.open_guarded(ddir / "settle_index_guarded.csv.gz", "screen-D")}
    y_of = _y_of_factory(outcomes)
    src = dl.source_check([u for u in units if u.get("label") == "available"], settle, y_of)
    if not src["pass"]:
        return {"source_check": src, "D1": {"testable": False, "p": 1.0, "advance": False, "verdict": "not testable (source)"}}
    r = dl.d1_stat(units, y_of, cor_identifiable=bool((cd.get("features") or {}).get("attribution_identifiable")))
    return {"source_check": src, "D1": r}


def screen_b_doc(hroot: Path, census: dict) -> dict:
    from astrolabe.research_lab import cb10_brk as br  # noqa: PLC0415

    cb = census.get("B") or {}
    out = {}
    if cb.get("label_B1") and cb.get("label_B2"):
        return {t: {"testable": False, "p": 1.0, "advance": False, "verdict": cb[f"label_{t}"]} for t in ("B1", "B2")}
    eps, _ = br.load_episodes(hroot / br.PRINTS_RUN, hroot / br.FRAME_RUN, br.SCREEN, job="screen-B")
    w = {float(k): float(v) for k, v in (cb.get("weights_frozen") or {}).items()}
    out["B1"] = {"testable": False, "p": 1.0, "advance": False, "verdict": cb["label_B1"]} if cb.get("label_B1") else br.b1_stat(eps, w)
    out["B2"] = {"testable": False, "p": 1.0, "advance": False, "verdict": cb["label_B2"]} if cb.get("label_B2") else br.b2_stat(eps)
    return out


@_guarded
def cmd_screen(a):
    c10 = _c10()
    c10.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha = _rules(a)
    root = _root(a)
    cpath = Path(a.census) if a.census else root / "census.json"
    if not cpath.exists():
        raise c10.NotNow("census.json missing (q0207 first)")
    census = json.loads(cpath.read_text())
    tp = Path(a.trials_path) if a.trials_path else None
    fam = a.family
    if fam == "D":
        doc = {**screen_d_doc(_hist(a, c10.H10_DLAD), census), "rules_sha256": sha, "written_epoch": time.time()}
        rsha = c10.write_results_once(Path(a.out) if a.out else root / "results_D.json", doc)
        r = doc["D1"]
        pl = (r.get("placebo_signflip") or {}).get("week")
        c10.log_test("D", "D1", {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "effect": r.get("beta"), "n": r.get("n"),
                                 "verdict": r.get("verdict")}, trials_path=tp, results_sha256=rsha,
                     placebo={"note": "D1 week sign-flip calibration", "advance_rate": pl["advance_rate"], "n_draws": pl["n_draws"]} if pl else None)
        return 0, {"status": "screen_D_complete", "D1": {k: r.get(k) for k in ("p", "beta", "advance", "verdict")}}
    if fam == "B":
        doc = {**screen_b_doc(_hist(a, c10.H10_BRK), census), "rules_sha256": sha, "written_epoch": time.time()}
        rsha = c10.write_results_once(Path(a.out) if a.out else root / "results_B.json", doc)
        for tid, eff in (("B1", "b1_cents"), ("B2", "b2_cents")):
            r = doc[tid]
            pl = (r.get("placebo_label_swap") or {}).get("event")
            c10.log_test("B", tid, {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "effect": r.get(eff), "n": r.get("n_units") or r.get("n_filled"),
                                    "verdict": r.get("verdict")}, trials_path=tp, results_sha256=rsha,
                         placebo={"note": f"{tid} label-swap calibration", "advance_rate": pl["advance_rate"], "n_draws": pl["n_draws"]} if pl else None)
        return 0, {"status": "screen_B_complete", **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in ("B1", "B2")}}
    raise c10.Refused(f"unknown family {fam!r}")


@_guarded
def cmd_stage1_label(a):
    c10 = _c10()
    root = _root(a)
    pv: dict[str, float | None] = dict.fromkeys(c10.STAGE1_HOLM_FAMILY)
    for name, tests in c10.STAGE1_RESULTS.items():
        p = root / name
        if p.exists():
            d = json.loads(p.read_text())
            for t in tests:
                if isinstance(d.get(t), dict) and d[t].get("testable"):
                    pv[t] = float(d[t].get("p", 1.0))
    return 0, {"batch_holm": c10.batch_holm_label(pv), "note": "label only; not run / pending / not testable enter with p = 1; k1 = 3 fixed"}


# ---- q0210 D Stage 2 (cron) ------------------------------------------------------------------------------------------------------------------------


def _d1_advanced(root: Path) -> dict | None:
    p = root / "results_D.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return d if (d.get("D1") or {}).get("advance") is True else None


def _stage2_window(a, root: Path, res: dict) -> tuple[str, list[str]]:
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415

    c10 = _c10()
    t_freeze = _commit_epoch(Path(a.freeze_spec) if a.freeze_spec else c10.FREEZE_SPEC)
    if t_freeze is None:
        raise c10.Refused("CB10 freeze commit time unknown")
    t_res = float(res.get("written_epoch") or 0)
    if a.d1_result_commit_epoch is not None:
        if a.d1_result_commit_epoch < t_res:
            raise c10.Refused("--d1-result-commit-epoch precedes the D1 results file")
        t_res = a.d1_result_commit_epoch
    start = dl.t10_d2_start(max(t_freeze, t_res))
    return start, dl.stage2_dates(start)


@_guarded
def cmd_dlad_live(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c10 = _c10()
    _declared(a, "dlad-live")
    if a.origin != "auto":
        raise c10.Refused("--origin must be 'auto' (the 12:00 America/New_York check is in code)")
    root = _root(a)
    res = _d1_advanced(root)
    if res is None:
        raise c10.Refused("D1 did not advance at Stage 1: q0210 is not run")
    c10.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    _rules(a)
    start, dates = _stage2_window(a, root, res)
    now = time.time()
    end_epoch = c10.noon_et(c10.day_add(dates[-1], dl.STAGE2_OUTCOME_GRACE_DAYS))
    collect_max = c10.noon_et(c10.day_add(start, dl.STAGE2_COLLECT_MAX_DAYS))
    if now > min(end_epoch, collect_max):
        return 0, {"status": "stage2_over", "requests": 0}
    ldir = root / "dlad_live"
    ids, keys, _rep, _ = c10.load_exclusion_keys(_keys_path(a))
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)

    def disk_ok():
        c10.require_disk(Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))

    def frame_markets(d: str):
        return dl.live_frame_markets(lim, d, ids, keys)

    def book_get(token: str):
        st, doc = lim.get(dl.CLOB_BOOK, {"token_id": token})
        if st != 200:
            raise cm.ApiError(f"book status {st}")
        return doc, time.time()

    def deribit_get(cur: str, s: int, e: int):
        trades, _ = dl.deribit_trades(lim, cur, s, e)
        return trades, time.time()

    def summary_get(cur: str):
        st, doc = lim.get(dl.DERIBIT_SUMMARY, {"currency": cur, "kind": "option"})
        if st != 200:
            raise cm.ApiError(f"summary status {st}")
        return doc, time.time()

    def prints_get(cid: str):
        return dl.fetch_market_prints(lim, cid)

    out = dl.dlad_live_tick(ldir, now=now, dates=dates, frame_markets=frame_markets, book_get=book_get, deribit_get=deribit_get, summary_get=summary_get,
                            prints_get=prints_get, disk_ok=disk_ok)

    def frames():
        fs = []
        for p in sorted(ldir.glob("*/frame.json")):
            fs += json.loads(p.read_text())
        return fs

    def lookup(mids: list[str]):
        rows = []
        for i in range(0, len(mids), 50):
            st, data = lim.get(hb.GAMMA_MARKETS, {"id": mids[i:i + 50], "closed": "true", "limit": 50})
            if st != 200 or not isinstance(data, list):
                raise cm.ApiError(f"outcome lookup status {st}")
            rows += data
        return rows

    if out.get("status") != "not_this_line":
        try:
            out["outcome_sweep"] = dl.outcome_sweep(ldir, now=now, dates=dates, frames=frames, lookup=lookup, deribit_get=deribit_get)
        except (cm.ApiError, RuntimeError) as exc:
            out["outcome_sweep"] = {"error": str(exc)[:200], "note": "retried by the next run"}
    out["requests"] = lim.requests
    return 0, out


# ---- q0211 / q0212 rep --------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_rep(a):
    from astrolabe.research_lab import cb10_brk as br  # noqa: PLC0415
    from astrolabe.research_lab import cb10_dlad as dl  # noqa: PLC0415

    c10 = _c10()
    c10.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha = _rules(a)
    root = _root(a)
    derived = c10.stage2_k(root)
    if a.stage2_k is not None and int(a.stage2_k) != derived["k"]:
        raise c10.Refused(f"--stage2-k {a.stage2_k} differs from the k derived from the Stage-1 results ({derived['k']}: {derived['advanced']})")
    k = derived["k"]
    tp = Path(a.trials_path) if a.trials_path else None
    if a.family == "D":
        res = _d1_advanced(root)
        if res is None:
            raise c10.Refused("D1 did not advance: there is no D Stage 2")
        start, dates = _stage2_window(a, root, res)
        if time.time() < c10.noon_et(c10.day_add(dates[-1], dl.STAGE2_OUTCOME_GRACE_DAYS)):
            raise c10.NotNow("q0211 runs after T10_D2_end + 2 days")
        ldir = root / "dlad_live"
        origin_days = sorted({c10.day_add(d, -lag) for d in dates for lag in dl.ORIGIN_LAGS})
        units, statuses = dl.live_units(ldir, origin_days)
        outcomes = {o["market_id"]: o for o in dl.open_guarded(ldir / "outcomes_guarded.csv.gz", "rep-D")} if (ldir / "outcomes_guarded.csv.gz").exists() else {}
        doc = {**dl.rep_d_doc(units, statuses, origin_days, _y_of_factory(outcomes), k), "rules_sha256": sha, "stage2_k_derived": derived, "data_role": c10.DATA_ROLE_PROSP}
        rsha = c10.write_results_once(Path(a.out) if a.out else root / "results_D_rep.json", doc)
        for tid, key, eff in (("D1-rep", "D1_rep", "beta"), ("D2", "D2", "mean_cents")):
            r = doc[key]
            c10.log_test("D", tid, {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "effect": r.get(eff), "n": r.get("n"),
                                    "verdict": r.get("verdict")}, replication=True, trials_path=tp, results_sha256=rsha, data_role=c10.DATA_ROLE_PROSP)
        return 0, {"status": "rep_D_complete", "D1_rep": doc["D1_rep"].get("verdict"), "D2": doc["D2"].get("verdict")}
    if a.family == "B":
        resb = json.loads((root / "results_B.json").read_text()) if (root / "results_B.json").exists() else {}
        adv = [t for t in ("B1", "B2") if (resb.get(t) or {}).get("advance") is True]
        if not adv:
            raise c10.Refused("neither B1 nor B2 advanced: there is no B Stage 2")
        hroot = _hist(a, c10.H10_BRK)
        br.verify_holdout_seal(hroot / br.PRINTS_RUN, Path(a.seals_dir) if a.seals_dir else None)
        census = json.loads((root / "census.json").read_text())
        eps, _ = br.load_episodes(hroot / br.PRINTS_RUN, hroot / br.FRAME_RUN, br.HOLDOUT, job="rep-B")
        w = {float(x): float(v) for x, v in ((census.get("B") or {}).get("weights_frozen") or {}).items()}
        thr = c10.STAGE2_ALPHA / k
        doc = {"stage2_k_derived": derived, "label": "sealed same-calendar holdout replication (L2)", "rules_sha256": sha}
        for t in adv:
            r = br.b1_stat(eps, w) if t == "B1" else br.b2_stat(eps)
            eff = r.get("b1_cents") if t == "B1" else r.get("b2_cents")
            r["stage2_pass_alpha_over_k"] = bool(r.get("testable") and r.get("p", 1.0) <= thr and (eff or 0) > 0)
            doc[f"{t}_rep"] = r
        rsha = c10.write_results_once(Path(a.out) if a.out else root / "results_B_rep.json", doc)
        for t in adv:
            r = doc[f"{t}_rep"]
            c10.log_test("B", f"{t}-rep", {"p": r.get("p", 1.0), "advance": r.get("stage2_pass_alpha_over_k"), "testable": r.get("testable"),
                                           "effect": r.get("b1_cents") if t == "B1" else r.get("b2_cents"), "verdict": r.get("verdict")},
                         replication=True, trials_path=tp, results_sha256=rsha)
        return 0, {"status": "rep_B_complete", "tests": adv}
    raise c10.Refused(f"unknown family {a.family!r}")


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c10 = _c10()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch10 root (default data-dumps/research_lab/creative_batch10)")
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
        q.add_argument("--data-dumps-cap-gb", type=float, default=c10.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("smoke", help="q0200")
    common(q, rps=1.0)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0201")
    common(q)
    net(q, disk_cap=0.005)
    q.add_argument("--cb9-keys", default=None)
    q.add_argument("--cb9-keys-sha256", required=True, help="the pinned sha256 of CB9 q0182's exclusion_keys.csv.gz")
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--extra-pin", action="append", default=None, help="NAME:PATH:SHA256 of a CB9 frame id list (market_id column; ids only); repeatable")
    q.set_defaults(fn=cmd_exclusion_keys)

    for name, fn, cap, extra in (("dlad-frame", cmd_dlad_frame, 0.01, ("smoke", "exclusion-keys")), ("deribit-trades", cmd_deribit, 0.02, ("smoke",)),
                                 ("brk-frame", cmd_brk_frame, 0.005, ("smoke", "exclusion-keys")), ("brk-prints", cmd_brk_prints, 0.06, ())):
        q = sub.add_parser(name)
        common(q)
        net(q, disk_cap=cap)
        for e in extra:
            q.add_argument(f"--{e}", default=None)
        q.set_defaults(fn=fn)

    q = sub.add_parser("brk-seal", help="q0206")
    common(q)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_brk_seal)

    q = sub.add_parser("census", help="q0207")
    common(q)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0208 (D) / q0209 (B)")
    common(q)
    q.add_argument("--family", choices=("D", "B"), required=True)
    q.add_argument("--census", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("stage1-label")
    common(q)
    q.set_defaults(fn=cmd_stage1_label)

    q = sub.add_parser("dlad-live", help="q0210 (cron)")
    common(q, rps=1.0)
    net(q, disk_cap=0.01)
    q.add_argument("--origin", default="auto")
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--d1-result-commit-epoch", type=float, default=None)
    q.set_defaults(fn=cmd_dlad_live)

    q = sub.add_parser("rep", help="q0211 (D) / q0212 (B)")
    common(q)
    q.add_argument("--family", choices=("D", "B"), required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--stage2-k", type=int, default=None)
    q.add_argument("--d1-result-commit-epoch", type=float, default=None)
    q.set_defaults(fn=cmd_rep)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
