# ruff: noqa: E501
"""CB9 runner (docs/research_lab/CREATIVE_BATCH_9.md section 4, q0180-q0198). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA
ONLY: no edge, calibration or profitability claim.

    python scripts/run_cb9.py rules --which sign|pyth|kd           # write docs/research_lab/seals/cb9_sign_rules.json | cb9_rules.json | cb9_kd_rules.json (commit first)
    python scripts/run_cb9.py key-fingerprint                       # the strict-loaded key's fingerprint (never the key)
    python scripts/run_cb9.py smoke ...                             # q0180: receipts per era, Yahoo bar clock, Gamma paging, pmxt HEADs; counts only, WRITE-ONCE
    python scripts/run_cb9.py sign-audit --strata a,c | b ...       # q0181 (S0a, S0c) / q0188 (S0b): prints, receipts, classes; no agreement
    python scripts/run_cb9.py exclusion-keys ...                    # q0182: CB8 q0164 keys + seal copies committed since
    python scripts/run_cb9.py pyth-frame ...                        # q0183: P frame, rule-text flags, Yahoo bars, guarded outcomes / closes
    python scripts/run_cb9.py pyth-books ...                        # q0184: pmxt states at the checkpoints, quote-window prints
    python scripts/run_cb9.py kd-frame | kd-books | kd-seal ...     # q0185-q0187 (cb9_kd)
    python scripts/run_cb9.py census                                # q0189: counts only, all families
    python scripts/run_cb9.py screen --family S0|P|S1|KD            # q0190 / q0191 / q0194 / q0192 (KD -> screen-kd); refuse before the CB9 freeze
    python scripts/run_cb9.py stage1-label                          # batch-Holm label over the fixed Stage-1 family (k1 = 5; not run -> p = 1)
    python scripts/run_cb9.py sign-fetch ...                        # q0193: h10_sign (only after an S0 'material noise' verdict)
    python scripts/run_cb9.py pyth-live ...                         # q0195: Stage-2 prospective collection (only if P1 or P2 advanced)
    python scripts/run_cb9.py rep --family P|KD                     # q0196 / q0197 (KD -> rep-kd)
    python scripts/run_cb9.py halfday-poll --days ...               # q0198: half-session books (descriptive, uncounted)

Exit codes: 0 ok / transient pause / idle heartbeat / declared end state; 1 error; 2 refusal (rules hash, key missing / unsafe / fingerprint, smoke
not met or result exists, run id, refused root, declared argument changed, before T_seal for net-lane jobs, before the CB9 freeze for analysis jobs,
HOLDOUT, guarded file, trigger not met); 4 disk budget (declared end state); 75 (EX_TEMPFAIL) data-dumps headroom, nothing due yet, or a network
failure in the smoke or more than 2 unavailable receipts in an era (nothing written).

Dependency-stall vocabulary (freeze check M5; shared with cb9_kd through cb9_common.STALL_*; forward to B):
    status "not_run_source"          label "not testable (source)"                  a smoke criterion / source check of THIS job failed
    status "disjointness_unverified" label "not testable (disjointness unverified)" q0182 or a seal step: > 2% exclusion ids without metadata
    status "upstream_not_testable"   label copied from the upstream manifest         an input job ended in one of the two states above
  A stalled job writes a terminal manifest (complete true, status, label, reason; cb9_common.write_stall / stall_of) and exits 0; it is never
  retried. The census copies the label per stratum / family; the screens log every affected test with p = 1, testable false. A MISSING smoke
  result or an unfinished upstream job is still a refusal (2) / not-yet (75): only a declared end state stalls.
Results files (screen, rep) are write-once (cb9_common.write_results_once): no overwrite, no second count line (M11).
Stage 2 (M10): one rule for both families, cb9_common.STAGE2_RULE; k derived by cb9_common.stage2_k from results_P.json + results_KD.json.
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
DECLARED_DISK_CAP_GB = {"sign-audit": 0.01, "exclusion-keys": 0.01, "pyth-frame": 0.01, "pyth-books": 0.02, "sign-fetch": 0.05, "pyth-live": 0.01, "halfday-poll": 0.01}
DECLARED_RPS_MAX = {"smoke": 1.0, "sign-audit": 2.0, "exclusion-keys": 2.0, "pyth-frame": 2.0, "pyth-books": 2.0, "sign-fetch": 2.0, "pyth-live": 1.0, "halfday-poll": 1.0}
HALFDAY_DAYS = "2026-11-27,2026-12-24"


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _guarded(fn):
    """Run ``fn`` and map the CB9 exceptions to exit codes; ``fn`` returns (exit code, payload dict)."""

    def wrapper(a) -> int:
        from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

        try:
            code, payload = fn(a)
        except cm.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except cm.NotNow as exc:
            _emit({"tempfail": str(exc)})
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


def _c9():
    from astrolabe.research_lab import cb9_common as c9  # noqa: PLC0415

    return c9


def _cb9_root(a) -> Path:
    c9 = _c9()
    return c9.refuse_path(Path(a.root) if getattr(a, "root", None) else c9.CB9_DIR)


def _declared(a, cmd: str) -> None:
    """Refuse (exit 2) when a declared argument differs: the output cap and the rate ceiling of each job."""
    c9 = _c9()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c9.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c9.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(rps=a.rps, data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _rules(a, kind: str) -> tuple[str, str]:
    c9 = _c9()
    path = Path(a.rules) if getattr(a, "rules", None) else c9.RULE_KINDS[kind][1]
    return c9.verify_rules(kind, path, require_committed=not getattr(a, "allow_uncommitted_rules", False))


def _key(a, fp: str) -> bytes:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    return cm.load_wallet_key_strict(Path(a.wallet_key_path) if getattr(a, "wallet_key_path", None) else None, fp)


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _commit_epoch(path: Path) -> float | None:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", str(path)], capture_output=True, text=True, cwd=ROOT, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return float(out) if out else None


# ---- rules / key ---------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c9 = _c9()
    try:
        kind = a.which
        fp = None
        if c9.RULE_KINDS[kind][3]:
            fp = a.key_fingerprint or cm.key_fingerprint(cm.load_wallet_key_strict(Path(a.wallet_key_path) if a.wallet_key_path else None))
        out = c9.write_rules(kind, Path(a.path) if a.path else None, fp)
        doc = c9.rules_file_doc(kind, fp)
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_sha256": doc["rules_sha256"], "funcs_sha256": doc["funcs_sha256"], "wallet_key_fingerprint": fp})
    return 0


def cmd_key_fp(a) -> int:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    try:
        _emit({"wallet_key_fingerprint": cm.key_fingerprint(cm.load_wallet_key_strict(Path(a.wallet_key_path) if a.wallet_key_path else None))})
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    return 0


# ---- q0180 smoke -----------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415
    from astrolabe.research_lab import cb9_sign as sg  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415
    from astrolabe.research_lab import history_sources as hs  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "smoke")
    out = c9.refuse_path(Path(a.out) if a.out else c9.SMOKE_DEFAULT)
    if out.exists():  # write-once: a FAIL can never be replaced by a later PASS
        raise c9.Refused(f"smoke result {out} already exists; it is write-once")
    sha, fp = _rules(a, "sign")
    key = _key(a, fp)
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    rpc = sg.RpcClient(sg.httpx_post(), rps=min(a.rps, 1.0), live_check=live)
    rec = sg.smoke_receipts(lim, rpc, key)
    ylim = hb.Limiter(py.yahoo_transport(), rps=min(a.rps, py.YAHOO_RPS), live_check=live)
    try:
        s0, s1 = py.et_epoch(py.SMOKE_SESSIONS[0], 0, 0), py.et_epoch(py.SMOKE_SESSIONS[-1], 23, 59)
        hdoc = py.yahoo_chart(ylim, py.SMOKE_TICKER, "1h", s0, s1)
        ddoc = py.yahoo_chart(ylim, py.SMOKE_TICKER, "1d", s0, s1)
        yah = py.smoke_yahoo_check(hdoc, ddoc)
    except cm.ApiError as exc:
        yah = {"pass": False, "error": str(exc)[:100]}
    except RuntimeError:
        raise cm.NotNow("smoke: Yahoo request failed (network); nothing written") from None
    try:
        gam = py.smoke_gamma_paging(lim)
        heads = py.smoke_pmxt_heads(hs.httpx_size)
    except RuntimeError:
        raise cm.NotNow("smoke: Gamma / pmxt request failed (network); nothing written") from None
    crit = {"receipts_v1": rec["receipts"]["v1"]["pass"], "receipts_v2": rec["receipts"]["v2"]["pass"], "yahoo_clock": yah["pass"],
            "gamma_paging": gam["pass"], "pmxt_heads": heads["pass"], "topic_pins": rec["topic_pins"]["ok"]}
    res = {"smoke_version": sg.SMOKE_VERSION, "rules_sha256": sha, "wallet_key_fingerprint": fp, "git_commit": hb._git_commit(), "run_utc": cm.iso(time.time()),
           "counts_only": True, "criteria": crit, "pass": all(crit.values()), "receipts": rec, "yahoo": yah, "gamma_paging": gam, "pmxt_heads": heads,
           "consequences": {"receipts_v1 fail": "S0c not run (source), counted", "receipts_v2 fail": "S0a/S0b not run (source), counted",
                            "yahoo_clock or gamma_paging fail": "P not testable (source), counted; the bar rule is never re-fitted"}}
    cm.write_once_json(out, res)
    c9.log_descriptive("smoke", {"pass": res["pass"], "criteria": crit, "smoke_path": str(out)}, trials_path=Path(a.trials_path) if a.trials_path else None)
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out)}


# ---- q0181 / q0188 sign audit ------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_sign_audit(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import cb9_sign as sg  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "sign-audit")
    strata = [s.strip() for s in a.strata.split(",") if s.strip()]
    if sorted(strata) not in (["a", "c"], ["b"]):
        raise c9.Refused(f"--strata must be 'a,c' (q0181) or 'b' (q0188), not {a.strata!r}")
    c9.require_after_t_seal(time.time(), "sign-audit")
    sha, fp = _rules(a, "sign")
    key = _key(a, fp)
    root = _cb9_root(a)
    kw = _net_kw(a)
    out = {}
    for s in strata:
        m = sg.sign_audit(root / "sign", s, hb.httpx_transport(), sg.httpx_post(), key=key, fp=fp, rules_sha=sha, now=time.time(),
                          smoke_path=Path(a.smoke) if a.smoke else c9.SMOKE_DEFAULT, cb7_keys_path=Path(a.cb7_keys) if a.cb7_keys else None,
                          seals_dir=Path(a.seals_dir) if a.seals_dir else None, is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed,
                          disk_cap=int(a.disk_cap_gb * 1024**3), s0b_input=(lambda: sg.kd_s0b_input(root)) if s == "b" else None,
                          s0b_stall=(lambda: sg.kd_upstream_stall(root)) if s == "b" else None, **kw)
        code, payload = _result(m)
        out[s] = {**payload, "label": m.get("label")}
        if code or m.get("status") not in ("sign_audit_complete", *c9.STALL_STATUSES):
            return code, {"strata": out}
    return 0, {"strata": out}


# ---- q0182 exclusion keys -------------------------------------------------------------------------------------------------------------------


def _extra_pins(values: list[str] | None) -> list[dict]:
    c9 = _c9()
    out = []
    for v in values or []:
        parts = str(v).split(":")
        if len(parts) != 3 or len(parts[2]) != 64:
            raise c9.Refused(f"--extra-pin must be NAME:PATH:SHA256, got {v!r}")
        out.append({"name": parts[0], "kind": "ids", "path": parts[1], "sha256": parts[2]})
    return out


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "exclusion-keys")
    c9.require_after_t_seal(time.time(), "exclusion-keys")
    sha, _ = _rules(a, "pyth")
    root = _cb9_root(a)
    kw = _net_kw(a)
    extra = _extra_pins(a.extra_pin)
    run_kw = dict(rules_sha=sha, cb8_keys_path=Path(a.cb8_keys) if a.cb8_keys else c9.CB8_KEYS_DEFAULT, cb8_keys_sha256=a.cb8_keys_sha256,
                  seals_dir=Path(a.seals_dir) if a.seals_dir else None, extra_pins=extra,
                  is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed, disk_cap=int(a.disk_cap_gb * 1024**3), **kw)
    if a.normalise_ids and getattr(a, "budget_min", None) is not None:
        raise c9.Refused("--budget-min is not supported with --normalise-ids (q0182b runs to completion inside its timeout and resumes by batch)")
    if not a.normalise_ids:  # q0182 as registered (fails on the composite h7_cb4_series ids); kept for reproducibility
        return _result(c9.exclusion_keys(root, hb.httpx_transport(), **run_kw))
    from astrolabe.research_lab import cb8_exclusion_budget as xb  # noqa: PLC0415
    from astrolabe.research_lab import cb9_exclusion_fix as fix  # noqa: PLC0415

    with xb.scratch_uncounted(), fix.normalised_exclusion_ids(extra) as norm:  # q0182b: composite seal ids -> market part (Gamma's id filter is integer-only); no hashed function is edited
        m = c9.exclusion_keys(root, hb.httpx_transport(), **run_kw)
    code, payload = _result(m)
    payload["id_normalisation"] = norm
    return (exclusion_exit_code(m) if code == 0 else code), payload


def exclusion_exit_code(m: dict) -> int:
    """0 only when complete / terminal; every transient incomplete stop, including 'budget reached' (the spec has no repeat block), is TEMPFAIL (75);
    a non-transient incomplete stop is an error (1), never 0, so the queue cannot mark a failed run done (q0164)."""
    if m.get("complete") is True or m.get("stopped") is None:
        return 0
    return TEMPFAIL if m.get("transient") else 1


# ---- q0183 / q0184 P data ---------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_pyth_frame(a):
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "pyth-frame")
    sha, _ = _rules(a, "pyth")
    root = _cb9_root(a)
    m = py.pyth_frame(root, hb.httpx_transport(), rules_sha=sha, smoke_path=Path(a.smoke) if a.smoke else c9.SMOKE_DEFAULT,
                      exclusion_keys_path=Path(a.exclusion_keys) if a.exclusion_keys else c9.EXCLUSION_KEYS_DEFAULT, now=time.time(),
                      disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_pyth_books(a):
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415
    from astrolabe.research_lab import history_sources as hs  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "pyth-books")
    if abs(a.ingress_cap_gb - py.INGRESS_CAP_GB) > 1e-9:
        raise c9.Refused(f"arguments differ from the declaration: ingress_cap_gb={a.ingress_cap_gb!r} (declared {py.INGRESS_CAP_GB!r})")
    sha, _ = _rules(a, "pyth")
    root = _cb9_root(a)
    m = py.pyth_books(root, hb.httpx_transport(), rules_sha=sha, smoke_path=Path(a.smoke) if a.smoke else c9.SMOKE_DEFAULT, frame_dir=root / "pyth_frame",
                      fetch=hs.httpx_range_fetch(), size_fn=hs.httpx_size, now=time.time(), ingress_cap_gb=a.ingress_cap_gb, disk_cap=int(a.disk_cap_gb * 1024**3),
                      **_net_kw(a))
    return _result(m)


# ---- q0189 census -------------------------------------------------------------------------------------------------------------------------------


def _kd_module():
    try:
        from astrolabe.research_lab import cb9_kd  # noqa: PLC0415
    except ImportError:
        return None
    return cb9_kd


def census_s_block(root: Path) -> dict:
    from astrolabe.research_lab import cb9_sign as sg  # noqa: PLC0415

    c9 = _c9()
    rows, stalls = {}, {}
    for s in sg.STRATA:
        rd = root / "sign" / f"s0{s}"
        st = c9.stall_of(rd)
        if st:
            stalls[s] = st
        p = rd / "prints_classes.csv.gz"
        rows[s] = sg.read_census_rows(p) if p.exists() else []
    out = sg.census_s(rows)
    for s, st in stalls.items():
        out[s].update(gate_GS=False, label=st["label"], stall=st["status"], stall_reason=st.get("reason"))
    return out


def census_p_block(root: Path) -> dict:
    """P census from the FEATURE files only (frame, bars_pre, strikes, states, prints); the guarded files are never opened here."""
    from astrolabe.research_lab import cb7_common as c7  # noqa: PLC0415
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415

    c9 = _c9()
    fdir, bdir = root / "pyth_frame", root / "pyth"
    st = c9.stall_of(fdir) or c9.stall_of(bdir)
    if st:
        return {"status": st["status"], "stall_reason": st.get("reason"), "label_P1": st["label"], "label_P2": st["label"], "gate_GP_P1": False, "gate_GP_P2": False}
    if not (fdir / "frame.csv.gz").exists() or not (bdir / "states.csv.gz").exists():
        return {"status": "inputs missing", "label_P1": "not testable (source unavailable)", "label_P2": "not testable (source unavailable)"}
    fman = json.loads((fdir / "manifest.json").read_text())
    frame = [r for r in c7.read_csv_gz(fdir / "frame.csv.gz") if r.get("ticker_status") == "ok"]
    bars = py.load_bars(fdir / "bars_pre.csv.gz")
    strikes = {(r["ticker"], r["day"]): float(r["k_d"]) for r in c7.read_csv_gz(fdir / "strikes.csv.gz")}
    states = list(c7.read_csv_gz(bdir / "states.csv.gz"))
    prints = list(c7.read_csv_gz(bdir / "prints.csv.gz"))
    units = py.build_units(frame, bars, strikes, states, prints)
    info = {"frame_status": fman.get("status"), "reasons": fman.get("reasons"), "drops": fman.get("drops"), "tickers": fman.get("tickers"),
            "n_frame_rows": len(frame), "n_tickers": len({r["ticker"] for r in frame})}
    return py.census_p(units, info)


@_guarded
def cmd_census(a):
    c9 = _c9()
    root = _cb9_root(a)
    out = Path(a.out) if a.out else root / "census.json"
    if out.exists():
        raise c9.Refused(f"{out} exists; the census is written once")
    doc = {"version": "cb9-census-v1", "counts_only": True, "S": census_s_block(root), "P": census_p_block(root)}
    kd = _kd_module()
    doc["kd"] = kd.kd_census(a) if kd is not None and hasattr(kd, "kd_census") else {"status": "cb9_kd unavailable"}
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    cm.write_json_atomic(out, doc)
    c9.log_descriptive("census", {"census_sha256": cm.sha_obj(doc), "path": str(out)}, trials_path=Path(a.trials_path) if a.trials_path else None)
    return 0, {"status": "census_complete", "written": str(out), "S_gates": {s: v.get("gate_GS") for s, v in doc["S"].items()},
               "P": {k: doc["P"].get(k) for k in ("label_P1", "label_P2")}}


# ---- screens and labels ------------------------------------------------------------------------------------------------------------------------


def _p_inputs(root: Path, job: str, lag_s: int | None = None, stale: bool = False):
    from astrolabe.research_lab import cb7_common as c7  # noqa: PLC0415
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415

    fdir, bdir = root / "pyth_frame", root / "pyth"
    frame = [r for r in c7.read_csv_gz(fdir / "frame.csv.gz") if r.get("ticker_status") == "ok"]
    bars = py.load_bars(fdir / "bars_pre.csv.gz")
    strikes = {(r["ticker"], r["day"]): float(r["k_d"]) for r in c7.read_csv_gz(fdir / "strikes.csv.gz")}
    states = list(c7.read_csv_gz(bdir / "states.csv.gz"))
    prints = list(c7.read_csv_gz(bdir / "prints.csv.gz"))
    outcomes = {o["market_id"]: o for o in py.open_guarded(fdir / "outcomes_guarded.csv.gz", job)}
    settle = py.open_guarded(fdir / "closes_settle_guarded.csv.gz", job)
    return frame, bars, strikes, states, prints, outcomes, settle


def screen_p_doc(root: Path, census: dict) -> dict:
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415

    c9 = _c9()
    st = c9.stall_of(root / "pyth_frame") or c9.stall_of(root / "pyth")
    if st:  # M5: the stall label is carried, both tests counted with p = 1
        return {t: {"testable": False, "p": 1.0, "advance": False, "verdict": st["label"], "stall": st["status"]} for t in ("P1", "P2")}
    frame, bars, strikes, states, prints, outcomes, settle = _p_inputs(root, "screen-P")

    def y_of(u: dict, token: str):
        o = outcomes.get(u["market_id"])
        return None if o is None else py.outcome_y(json.loads(o["outcome_labels"]), json.loads(o["outcome_prices"]), token)

    units = py.build_units(frame, bars, strikes, states, prints)
    stale = py.build_units(frame, bars, strikes, states, prints, stale=True)
    lat = py.build_units(frame, bars, strikes, states, prints, lag_s=py.LATENCY_LAG_S)
    src = py.source_check(frame, strikes, settle, outcomes)
    pc = census.get("P") or {}
    out = {"source_check": src}
    for tid, fn, gate_key, lab_key in (("P1", lambda: py.p1_stat(units, y_of, stale_units=stale, latency_units=lat), "gate_GP_P1", "label_P1"),
                                       ("P2", lambda: py.p2_stat(units, y_of, latency_units=lat), "gate_GP_P2", "label_P2")):
        if not src["pass"]:
            out[tid] = {"testable": False, "p": 1.0, "advance": False, "verdict": "not testable (source)"}
        elif not pc.get(gate_key) or not (pc.get("coverage_audit") or {}).get("pass"):
            out[tid] = {"testable": False, "p": 1.0, "advance": False, "verdict": pc.get(lab_key) or "not testable (gate GP)"}
        else:
            out[tid] = fn()
    return out


@_guarded
def cmd_screen(a):
    from astrolabe.research_lab import cb9_sign as sg  # noqa: PLC0415

    c9 = _c9()
    fam = a.family
    if fam == "KD":
        raise c9.Refused("screen --family KD is dispatched to screen-kd (cb9_kd); cb9_kd is unavailable")
    c9.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    root = _cb9_root(a)
    tp = Path(a.trials_path) if a.trials_path else None
    census = json.loads(Path(a.census or (root / "census.json")).read_text())
    if fam == "S0":
        _rules(a, "sign")
        rows = {s: list(_all_rows(root / "sign" / f"s0{s}" / "prints_classes.csv.gz")) for s in sg.STRATA}
        doc = sg.s0_screen(rows)
        rsha = c9.write_results_once(Path(a.out) if a.out else root / "results_S0.json", doc)
        c9.log_test("S", "S0", {"p": None, "advance": False, "testable": doc["testable"], "verdict": {s: v["verdict"] for s, v in doc["strata"].items()}},
                    trials_path=tp, results_sha256=rsha)
        return 0, {"status": "screen_S0_complete", "verdicts": {s: v["verdict"] for s, v in doc["strata"].items()}, "s1_triggered": doc["s1_triggered_eras"]}
    if fam == "P":
        sha, _ = _rules(a, "pyth")
        doc = {**screen_p_doc(root, census), "rules_sha256": sha}
        rsha = c9.write_results_once(Path(a.out) if a.out else root / "results_P.json", doc)
        for tid in ("P1", "P2"):
            r = doc[tid]
            pl = r.get("placebo_breakeven") or r.get("placebo_label_swap")
            c9.log_test("P", tid, {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"), "effect": r.get("mean_cents"), "n": r.get("n"),
                                   "verdict": r.get("verdict")}, trials_path=tp, results_sha256=rsha,
                        placebo={"note": f"{tid} calibration placebo", "advance_rate": pl["advance_rate"], "n_draws": pl["n_draws"]} if pl else None)
        return 0, {"status": "screen_P_complete", "P1": {k: doc["P1"].get(k) for k in ("p", "advance", "verdict")}, "P2": {k: doc["P2"].get(k) for k in ("p", "advance", "verdict")}}
    if fam == "S1":
        _rules(a, "sign")
        doc = screen_s1_doc(root, Path(a.history_root) if a.history_root else None)
        rsha = c9.write_results_once(Path(a.out) if a.out else root / "results_S1.json", doc)
        c9.log_test("S", "S1", {"p": doc.get("p", 1.0), "advance": doc.get("advance"), "testable": doc.get("testable"), "effect": doc.get("r_hat"), "n": doc.get("n"),
                                "verdict": doc.get("verdict")}, trials_path=tp, results_sha256=rsha)
        return 0, {"status": "screen_S1_complete", "verdict": doc.get("verdict"), "p": doc.get("p")}
    raise c9.Refused(f"unknown family {fam!r}")


def _all_rows(p: Path):
    from astrolabe.research_lab import cb7_common as c7  # noqa: PLC0415

    if not p.exists():
        return []
    return c7.read_csv_gz(p)


def screen_s1_doc(root: Path, history_root: Path | None) -> dict:
    """S1 on h10_sign: per market window the 2-h grid units on identical prints, event clusters; ratio rule."""
    from astrolabe.research_lab import cb7_common as c7  # noqa: PLC0415
    from astrolabe.research_lab import cb9_common as c9  # noqa: PLC0415
    from astrolabe.research_lab import cb9_sign as sg  # noqa: PLC0415

    hdir = Path(history_root or c9.HIST_ROOT) / c9.H10_RUN
    if not (hdir / "sample.json").exists():
        return {"testable": False, "p": 1.0, "advance": False, "verdict": "not run (h10_sign absent)"}
    smp = json.loads((hdir / "sample.json").read_text())
    units, events = [], []
    for r in smp:
        fp = hdir / "prints" / f"{r['market_id']}.csv.gz"
        if not fp.exists():
            continue
        prints = [{"ts": float(x["ts"]), "idx": int(x["idx"]), "api_side": "BUY" if str(x["api_side"]) in ("1", "BUY") else "SELL", "price": float(x["price"]),
                   "size": float(x["size"]), "t1_side": x["t1_side"], "t1_idx": int(x["t1_idx"]) if x["t1_idx"] not in ("", None) else 0}
                  for x in c7.read_csv_gz(fp) if x["match_status"] == "matched"]
        for u in sg.s1_units(prints, float(r["w0"]), float(r["w1"])):
            units.append(u)
            events.append(r.get("event_id") or r["market_id"])
    return sg.s1_ratio(units, events)


@_guarded
def cmd_stage1_label(a):
    c9 = _c9()
    root = _cb9_root(a)
    pv: dict[str, float | None] = dict.fromkeys(c9.STAGE1_HOLM_FAMILY)
    for name, keys in (("results_P.json", ("P1", "P2")), ("results_KD.json", ("K1", "D1"))):
        p = root / name
        if p.exists():
            d = json.loads(p.read_text())
            for k in keys:
                if isinstance(d.get(k), dict) and d[k].get("testable"):
                    pv[k] = float(d[k].get("p", 1.0))
    p = root / "results_S1.json"
    if p.exists():
        d = json.loads(p.read_text())
        pv["S1"] = float(d.get("p", 1.0)) if d.get("testable") else None
    return 0, {"batch_holm": c9.batch_holm_label(pv), "note": "label only; not run / pending / not testable enter with p = 1; k1 = 5 fixed"}


@_guarded
def cmd_stage2_label(a):
    """Holm step-down (one-sided alpha 0.05) over the final Stage-2 p values; a label only (each test was judged at alpha/k when it finished)."""
    c9 = _c9()
    root = _cb9_root(a)
    der = c9.stage2_k(root)
    pv = {}
    for name, keys in (("results_P_rep.json", ("P1_rep", "P2_rep")), ("results_KD_rep.json", ("K1_rep", "D1_rep"))):
        p = root / name
        if p.exists():
            d = json.loads(p.read_text())
            for k in keys:
                if isinstance(d.get(k), dict):
                    pv[k] = float(d[k].get("p", 1.0)) if d[k].get("testable") else 1.0
    pending = [f"{t}_rep" for t in der["advanced"] if f"{t}_rep" not in pv]
    return 0, {"stage2": der, "holm": c9.holm(pv, c9.STAGE2_ALPHA) if pv else {}, "pending": pending, "note": "label only"}


# ---- q0193 S1 fetch -------------------------------------------------------------------------------------------------------------------------------


def _ids_of(path: Path, col: str = "market_id") -> set[str]:
    from astrolabe.research_lab import cb7_common as c7  # noqa: PLC0415

    return {str(r[col]) for r in c7.read_csv_gz(path)}


@_guarded
def cmd_sign_fetch(a):
    from astrolabe.research_lab import cb9_sign as sg  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "sign-fetch")
    root = _cb9_root(a)
    res = root / "results_S0.json"
    if not res.exists():
        raise c9.Refused("results_S0.json missing: q0193 runs only after an S0 'material noise' verdict")
    trig = json.loads(res.read_text()).get("s1_triggered_eras") or []
    if not trig:
        raise c9.Refused("no S0 stratum gave 'material noise': S1 is not run")
    era = "v2" if any(s in ("a", "b") for s in trig) else "v1"
    sha, fp = _rules(a, "sign")
    key = _key(a, fp)
    ids, keys, _rep, _sha = c9.load_exclusion_keys(Path(a.exclusion_keys) if a.exclusion_keys else c9.EXCLUSION_KEYS_DEFAULT)
    kd = _kd_module()
    if kd is None:
        raise c9.Refused("cb9_kd unavailable: the K/D frame ids are required for the h10 exclusions")
    # A source that ended in a declared stall contributes no ids (recorded); Pyth markets are excluded by rule in the fetch anyway.
    srcs = {"kd_frame": (root / kd.FRAME_RUN, root / kd.FRAME_RUN / kd.FRAME_FILE, lambda p: _ids_of(p)),
            "pyth_frame": (root / "pyth_frame", root / "pyth_frame" / "frame_all.csv.gz", lambda p: _ids_of(p)),
            "s0a": (root / "sign" / "s0a", root / "sign" / "s0a" / "sample.json", lambda p: {r["market_id"] for r in json.loads(p.read_text())["markets"]}),
            "s0c": (root / "sign" / "s0c", root / "sign" / "s0c" / "sample.json", lambda p: {r["market_id"] for r in json.loads(p.read_text())["markets"]}),
            "s0b": (root / "sign" / "s0b", root / "sign" / "s0b" / "s0b_drawn.json", lambda p: {x["market_id"] for x in json.loads(p.read_text())})}
    cb9_ids = {}
    for name, (rdir, path, fn) in srcs.items():
        if path.exists():
            cb9_ids[name] = fn(path)
        elif c9.stall_of(rdir):
            cb9_ids[name] = set()
        else:
            raise c9.Refused(f"h10 exclusion source {name} missing ({path}) and not a declared stall")
    m = sg.sign_fetch_h10(Path(a.history_root) if a.history_root else c9.HIST_ROOT, hb.httpx_transport(), sg.httpx_post(), key=key, fp=fp, rules_sha=sha, era=era,
                          excl_ids=ids, excl_keys=keys, cb9_ids=cb9_ids, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0195 P Stage 2, q0196 rep, q0198 half days ----------------------------------------------------------------------------------------------------


def _p_advanced(root: Path) -> bool:
    p = root / "results_P.json"
    if not p.exists():
        return False
    d = json.loads(p.read_text())
    return bool((d.get("P1") or {}).get("advance") or (d.get("P2") or {}).get("advance"))


LIVE_COMPLETE, LIVE_COMPLETE_FILE = "pyth_live_complete", "COMPLETE.json"  # status printed by the CLI (q0195 repeat regex) and the marker rep-P requires
LIVE_LOOKAHEAD_S = 35 * 60  # queue re-run gap: 30 min exit-75 wait + 2 min cron tick; a step due within this look-ahead is waited for inside the run
REP_P_WAIT_AFTER_END_S = 2 * 86400  # rep-P waits until the last session's end + 2 d (settlement and outcomes)


def live_due_times(ldir: Path, day: str) -> list[float]:
    """Epochs of the not-yet-done q0195 steps of one session (pre-open fetch, the three checkpoints, the post-close step)."""
    py = _py()
    sp = Path(ldir) / day / "state.json"
    steps = json.loads(sp.read_text()).get("steps", {}) if sp.exists() else {}
    out = [] if "pre" in steps else [py.et_epoch(day, 8, 0)]
    out += [t for ci, _e, t in py.checkpoints(day) if f"ckpt{ci}" not in steps]
    if "post" not in steps:
        out.append(py.et_epoch(day, *py.close_et(day)) + 1800)
    return out


def wait_until_due(ldir: Path, sessions: list[str], now: float, sleep, lookahead_s: float = LIVE_LOOKAHEAD_S) -> float | None:
    """Sleep until the earliest pending step due within ``lookahead_s`` (+ 2 s); returns the epoch waited for, or None when nothing is due soon."""
    py = _py()
    due = [t for d in sessions if d in (py.et_day(now), py.et_day(now + lookahead_s)) for t in live_due_times(ldir, d) if now < t <= now + lookahead_s]
    if not due:
        return None
    sleep(min(due) - now + 2.0)
    return min(due)


def _py():
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415

    return py


@_guarded
def cmd_pyth_live(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "pyth-live")
    if a.sessions != py.STAGE2_SESSIONS:
        raise c9.Refused(f"arguments differ from the declaration: sessions={a.sessions} (declared {py.STAGE2_SESSIONS})")
    root = _cb9_root(a)
    if not _p_advanced(root):
        raise c9.Refused("P1 / P2 did not advance at Stage 1: q0195 is not run")
    c9.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    t_freeze = _commit_epoch(Path(a.freeze_spec) if a.freeze_spec else c9.FREEZE_SPEC)
    if t_freeze is None:
        raise c9.Refused("CB9 freeze commit time unknown")
    _rules(a, "pyth")
    start_day = py.t9_p2_start(t_freeze)
    ldir = root / "pyth_live"
    now0 = time.time()
    if now0 < py.et_epoch(start_day, 8, 0) - LIVE_LOOKAHEAD_S:  # re-check fix 3: before the window the job exits 75 at once (idle heartbeat every 10 h)
        return 0, cm.idle(ldir, f"Stage-2 window starts {start_day} 08:00 ET", now0)
    cm.require_room(Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    ids, keys, _rep, _ = c9.load_exclusion_keys(Path(a.exclusion_keys) if a.exclusion_keys else c9.EXCLUSION_KEYS_DEFAULT)
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    ylim = hb.Limiter(py.yahoo_transport(), rps=min(a.rps, py.YAHOO_RPS), live_check=live)
    cache: dict[str, list[dict]] = {}

    def frame_markets(day: str) -> list[dict]:
        if day not in cache:
            fp_ = ldir / day / "frame.json"
            if fp_.exists():
                cache[day] = json.loads(fp_.read_text())
            else:
                cache[day] = py.live_frame_markets(lim, day, ids, keys)
                fp_.parent.mkdir(parents=True, exist_ok=True)
                fp_.write_text(json.dumps(cache[day]))
        return cache[day]

    def yahoo_get(sym: str, interval: str, p1: float, p2: float):
        doc = py.yahoo_chart(ylim, sym, interval, p1, p2)
        return doc, time.time()

    def book_get(token: str):
        st, doc = lim.get(py.CLOB_BOOK, {"token_id": token})
        if st != 200:
            raise cm.ApiError(f"book status {st}")
        return doc, time.time()

    def prints_get(cid: str, s: int, e: int):
        try:
            rows, info = cm.windowed_prints(lim, cid, s, e, py.PRINT_PAGES, b"cb9-no-wallets")
        except cm.ApiError:
            return None
        return None if info["capped"] else [{k: p[k] for k in ("ts", "idx", "side", "price", "size")} for p in rows]

    def outcome_get(ids: list[str]) -> list[dict]:  # guarded: written only to <session>/outcomes_guarded.csv.gz by the collector
        st, rows = lim.get(hb.GAMMA_MARKETS, {"id": list(ids), "closed": "true", "limit": 50})
        if st != 200 or not isinstance(rows, list):
            raise cm.ApiError(f"gamma outcome status {st}")
        return rows

    # A queue re-run comes about every 30 minutes (exit-75 wait), the checkpoint window is 10 minutes: when a step falls due within the look-ahead the run
    # sleeps until it (re-check fix 3), so no checkpoint is missed by queue granularity.
    wait_until_due(ldir, py.stage2_sessions(start_day), time.time(), time.sleep)
    res = py.pyth_live_tick(ldir, now=time.time(), start_day=start_day, frame_markets=frame_markets, yahoo_get=yahoo_get, book_get=book_get,
                            prints_get=prints_get, outcome_get=outcome_get)
    if res["status"] == "idle":
        return 0, cm.idle(ldir, "no Stage-2 step due", time.time())
    if res["status"] == LIVE_COMPLETE:  # marker read by rep-P (re-check fix 4)
        cm.write_json_atomic(ldir / LIVE_COMPLETE_FILE, {"status": LIVE_COMPLETE, "utc": cm.iso(time.time())})
    return 0, res


def rep_p_doc(root: Path, now: float | None = None) -> dict:
    """P1-rep / P2-rep under the shared Stage-2 rule (M10): k derived from the Stage-1 results, early-finisher threshold alpha/k, and the floor,
    binding placebo and robustness checks evaluated at that threshold."""
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415

    c9 = _c9()
    der = c9.stage2_k(root)
    gate = c9.stage2_gate(der)
    t_freeze = _commit_epoch(c9.FREEZE_SPEC)
    if t_freeze is None:
        raise c9.Refused("CB9 freeze commit time unknown")
    sessions = py.stage2_sessions(py.t9_p2_start(t_freeze))
    ldir = root / "pyth_live"
    # re-check fix 4: nothing is scored (and no trial line is written) before pyth-live is complete, T9_P2_end + 2 d has passed and every outcome is final;
    # a pending session must never be scored "unavailable (source)".
    t_now = time.time() if now is None else now
    t_end = py.et_epoch(sessions[-1], 23, 59)
    if not (ldir / LIVE_COMPLETE_FILE).exists():
        raise c9.NotNow("rep-P: pyth-live (q0195) is not complete yet")
    if t_now < t_end + REP_P_WAIT_AFTER_END_S:
        raise c9.NotNow(f"rep-P: waits until T9_P2_end + 2 d ({sessions[-1]})")
    pending = [d for d in sessions if (ldir / d / "state.json").exists()
               and not ((json.loads((ldir / d / "state.json").read_text()).get("steps") or {}).get("outcomes") or {}).get("final")]
    if pending:
        raise c9.NotNow(f"rep-P: outcomes not final for {len(pending)} session(s), e.g. {pending[0]}")
    frames = {d: json.loads((ldir / d / "frame.json").read_text()) for d in sessions if (ldir / d / "frame.json").exists()}
    outcomes = {}
    for d in sessions:
        gp = ldir / d / "outcomes_guarded.csv.gz"
        if gp.exists():
            outcomes.update({o["market_id"]: o for o in py.open_guarded(gp, "rep-P")})

    def y_of(u: dict, token: str):
        o = outcomes.get(u["market_id"])
        return None if o is None else py.outcome_y(json.loads(o["outcome_labels"]), json.loads(o["outcome_prices"]), token)

    units, status = py.live_units(ldir, sessions, frames)
    avail = py.stage2_availability(status, sessions)
    out = {"stage2": {**der, "threshold": gate, "rule": c9.STAGE2_RULE}, "availability": avail, "label": "out-of-time replication on post-freeze sessions (L2)",
           "data_role": c9.DATA_ROLE_PROSP}
    for tid, fn in (("P1", lambda: py.p1_stat(units, y_of, gate_p=gate)), ("P2", lambda: py.p2_stat(units, y_of, gate_p=gate))):
        if tid not in der["advanced"]:
            continue
        if not avail["testable"]:
            out[f"{tid}_rep"] = {"testable": False, "p": 1.0, "advance": False, "verdict": avail["label"]}
            continue
        out[f"{tid}_rep"] = {**fn(), "stage2_threshold": gate}
    return out


@_guarded
def cmd_rep(a):
    c9 = _c9()
    if a.family == "KD":
        raise c9.Refused("rep --family KD is dispatched to rep-kd (cb9_kd); cb9_kd is unavailable")
    if a.family != "P":
        raise c9.Refused(f"unknown family {a.family!r}")
    c9.require_freeze(Path(a.freeze_spec) if a.freeze_spec else None, require_committed=not a.allow_uncommitted_rules)
    sha, _ = _rules(a, "pyth")
    root = _cb9_root(a)
    doc = {**rep_p_doc(root), "rules_sha256": sha}
    rsha = c9.write_results_once(Path(a.out) if a.out else root / "results_P_rep.json", doc)
    tp = Path(a.trials_path) if a.trials_path else None
    for tid in ("P1", "P2"):
        r = doc.get(f"{tid}_rep")
        if r is None:
            continue
        c9.log_test("P", f"{tid}-rep", {"p": r.get("p", 1.0), "advance": r.get("advance"), "testable": r.get("testable"),
                                        "effect": r.get("mean_cents"), "n": r.get("n"), "verdict": r.get("verdict")}, replication=True, trials_path=tp,
                    results_sha256=rsha, data_role=c9.DATA_ROLE_PROSP)
    return 0, {"status": "rep_P_complete", "tests": [k for k in ("P1_rep", "P2_rep") if k in doc]}


HALFDAY_COMPLETE, HALFDAY_DAY_DONE = "halfday_complete", "halfday_day_done"
HALFDAY_DONE_FILE = "DONE.json"


def halfday_next(hdir: Path, days: list[str]) -> str | None:
    """The first declared half day without a ``DONE.json`` (the CLI prints ``halfday_complete`` when there is none)."""
    for d in sorted(days):
        if not (Path(hdir) / d / HALFDAY_DONE_FILE).exists():
            return d
    return None


def halfday_session(hdir: Path, day: str, *, now_fn, sleep, frame_markets, book_get, yahoo_get) -> dict:
    """One half session inside one run: wait for 13:05 ET (the caller checked it is within the look-ahead), poll every minute until 16:00 ET (``py.halfday_tick``
    is idempotent per minute), then fetch the Yahoo 1-minute bars of the day once per ticker (a failure is recorded, never retried: descriptive, uncounted)
    and write ``DONE.json``. A half day whose window passed unseen is recorded ``missed_window`` (never back-filled)."""
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    py = _py()
    hdir = Path(hdir)
    t0, t1 = py.et_epoch(day, *py.HALFDAY_POLL_ET[0]), py.et_epoch(day, *py.HALFDAY_POLL_ET[1])
    if now_fn() > t1 and not list((hdir / day).glob("m*.json")):
        cm.write_json_atomic(hdir / day / HALFDAY_DONE_FILE, {"status": "missed_window", "utc": cm.iso(now_fn())})
        return {"status": HALFDAY_DAY_DONE, "day": day, "result": "missed_window"}
    if now_fn() < t0:
        sleep(t0 - now_fn() + 1.0)
    ticks = 0
    while now_fn() <= t1:
        r = py.halfday_tick(hdir, now=now_fn(), days=[day], frame_markets=frame_markets, book_get=book_get)
        ticks += int(r["status"] == "collected")
        nxt = t0 + (int((now_fn() - t0) // 60) + 1) * 60
        sleep(max(1.0, min(nxt, t1 + 1.0) - now_fn()))
    tickers = sorted({m["ticker"] for m in frame_markets(day)})
    yahoo: dict = {}
    for tk in tickers:
        try:
            doc = yahoo_get(tk, py.et_epoch(day, 9, 30), py.et_epoch(day, 16, 0))
            (hdir / day / f"yahoo_1m_{tk}.json").write_text(json.dumps(doc, default=float))
            yahoo[tk] = "ok"
        except Exception as exc:
            yahoo[tk] = f"failed: {type(exc).__name__}"[:60]
    cm.write_json_atomic(hdir / day / HALFDAY_DONE_FILE, {"status": "polled", "minutes_collected": ticks, "yahoo_1m": yahoo, "utc": cm.iso(now_fn())})
    return {"status": HALFDAY_DAY_DONE, "day": day, "minutes_collected": ticks, "yahoo_1m": yahoo}


@_guarded
def cmd_halfday(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb9_pyth as py  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c9 = _c9()
    _declared(a, "halfday-poll")
    days = [d.strip() for d in a.days.split(",") if d.strip()]
    if sorted(days) != sorted(HALFDAY_DAYS.split(",")):
        raise c9.Refused(f"arguments differ from the declaration: days={a.days!r} (declared {HALFDAY_DAYS})")
    _rules(a, "pyth")
    root = _cb9_root(a)
    hdir = root / "halfday"
    now0 = time.time()
    nxt = halfday_next(hdir, days)
    if nxt is None:
        return 0, {"status": HALFDAY_COMPLETE}
    if now0 < py.et_epoch(nxt, *py.HALFDAY_POLL_ET[0]) - LIVE_LOOKAHEAD_S:  # re-check SHOULD-FIX a: exit 75 (idle heartbeat) until the next half day is near
        return 0, cm.idle(hdir, f"next half session {nxt}", now0)
    cm.require_room(Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    ids, keys, _rep, _ = c9.load_exclusion_keys(Path(a.exclusion_keys) if a.exclusion_keys else c9.EXCLUSION_KEYS_DEFAULT)
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    ylim = hb.Limiter(py.yahoo_transport(), rps=min(a.rps, py.YAHOO_RPS), live_check=live)
    cache: dict[str, list[dict]] = {}

    def frame_markets(day: str) -> list[dict]:
        if day not in cache:
            cache[day] = py.live_frame_markets(lim, day, ids, keys)
        return cache[day]

    def book_get(token: str):
        st, doc = lim.get(py.CLOB_BOOK, {"token_id": token})
        if st != 200:
            raise cm.ApiError(f"book status {st}")
        return doc, time.time()

    def yahoo_get(sym: str, p1: float, p2: float):
        return py.yahoo_chart(ylim, sym, "1m", p1, p2)

    return 0, halfday_session(hdir, nxt, now_fn=time.time, sleep=time.sleep, frame_markets=frame_markets, book_get=book_get, yahoo_get=yahoo_get)


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c9 = _c9()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch9 root (default data-dumps/research_lab/creative_batch9)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)

    def net(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c9.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--which", choices=tuple(c9.RULE_KINDS), required=True)
    q.add_argument("--path", default=None)
    q.add_argument("--key-fingerprint", default=None, help="16 hex characters; default: computed from the strict-loaded key")
    q.add_argument("--wallet-key-path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("key-fingerprint")
    q.add_argument("--wallet-key-path", default=None)
    q.set_defaults(fn=cmd_key_fp)

    q = sub.add_parser("smoke", help="q0180")
    common(q, rps=1.0)
    q.add_argument("--wallet-key-path", default=None)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("sign-audit", help="q0181 (--strata a,c) / q0188 (--strata b)")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--strata", required=True)
    q.add_argument("--wallet-key-path", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--cb7-keys", default=None)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_sign_audit)

    q = sub.add_parser("exclusion-keys", help="q0182")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--cb8-keys", default=None)
    q.add_argument("--cb8-keys-sha256", required=True, help="the pinned sha256 of CB8 q0164's exclusion_keys.csv.gz")
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--extra-pin", action="append", default=None, help="NAME:PATH:SHA256 of an ids CSV / frame with a market_id column (ids only); repeatable")
    q.add_argument("--normalise-ids", action="store_true", help="q0182b: composite seal ids -> numeric market part + pred_* market ids (cb9_exclusion_fix); exit 75 on a transient incomplete stop")
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("pyth-frame", help="q0183")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.set_defaults(fn=cmd_pyth_frame)

    q = sub.add_parser("pyth-books", help="q0184")
    common(q)
    net(q, disk_cap=0.02)
    q.add_argument("--smoke", default=None)
    q.add_argument("--ingress-cap-gb", type=float, default=40.0)
    q.set_defaults(fn=cmd_pyth_books)

    q = sub.add_parser("census", help="q0189")
    common(q)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0190 (S0) / q0191 (P) / q0194 (S1); KD -> screen-kd")
    common(q)
    q.add_argument("--family", choices=("S0", "P", "S1", "KD"), required=True)
    q.add_argument("--census", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--history-root", default=None)
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("stage1-label", help="batch-Holm label over P1, P2, K1, D1, S1 (k1 = 5)")
    common(q)
    q.set_defaults(fn=cmd_stage1_label)

    q = sub.add_parser("stage2-label", help="Holm label over the final Stage-2 p values (k derived from the Stage-1 results)")
    common(q)
    q.set_defaults(fn=cmd_stage2_label)

    q = sub.add_parser("sign-fetch", help="q0193")
    common(q)
    net(q, disk_cap=0.05)
    q.add_argument("--wallet-key-path", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--history-root", default=None)
    q.set_defaults(fn=cmd_sign_fetch)

    q = sub.add_parser("pyth-live", help="q0195")
    common(q, rps=1.0)
    net(q, disk_cap=0.01)
    q.add_argument("--sessions", type=int, default=30)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.set_defaults(fn=cmd_pyth_live)

    q = sub.add_parser("rep", help="q0196 (P) / q0197 (KD -> rep-kd)")
    common(q)
    q.add_argument("--family", choices=("P", "KD"), required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.set_defaults(fn=cmd_rep)

    q = sub.add_parser("halfday-poll", help="q0198")
    common(q, rps=1.0)
    net(q, disk_cap=0.01)
    q.add_argument("--days", default=HALFDAY_DAYS)
    q.add_argument("--exclusion-keys", default=None)
    q.set_defaults(fn=cmd_halfday)

    kd = _kd_module()
    if kd is not None and hasattr(kd, "add_subparsers"):
        kd.add_subparsers(sub)
    return ap


def dispatch_argv(argv: list[str]) -> list[str]:
    """``screen --family KD`` -> ``screen-kd``; ``rep --family KD`` -> ``rep-kd`` (the cb9_kd subcommands), the other arguments unchanged."""
    argv = list(argv)
    if argv and argv[0] in ("screen", "rep"):
        for i, x in enumerate(argv):
            if x == "--family" and i + 1 < len(argv) and argv[i + 1] == "KD" and _kd_module() is not None:
                return [f"{argv[0]}-kd"] + argv[1:i] + argv[i + 2:]
            if x == "--family=KD" and _kd_module() is not None:
                return [f"{argv[0]}-kd"] + argv[1:i] + argv[i + 1:]
    return argv


def main(argv: list[str] | None = None) -> int:
    argv = dispatch_argv(sys.argv[1:] if argv is None else argv)
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
