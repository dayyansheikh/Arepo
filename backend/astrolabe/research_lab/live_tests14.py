# ruff: noqa: E501
"""LT14 census: the schema pre-check, the seal, the restore readiness and the counts-only census CC14 of CH262 (docs/research_lab/LIVE_TESTS_14.md section 3 and 6, design text frozen at
sha256 f047c000...). DRAFT: nothing is registered. Research tooling only; never trades; makes no network request.

Scope: section 3 only. NOT here: the size check, the placebo, F, the analysis, the window reader, ops-stats. The census reads origin-side fields of capture k; its ONLY later-slot reads are
``st`` and ``t_off`` of ``quotes/`` at k + 1 (the unavailable shares and the horizon rule); no ``g`` and no later bid, ask or mid is ever formed (:class:`live_tests14_base.EngineReader`).
It runs ONCE (a write-once marker beside the seal) and prints counts only.
"""

from __future__ import annotations

import json
import math
import resource
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import live_tests12 as lt12
from . import live_tests12_base as b
from . import live_tests14_base as t

epoch, iso = b.epoch, b.iso
Refused = t.Refused
TEMPFAIL = t.TEMPFAIL
CENSUS_UNAVAILABLE, CENSUS_DROPPED, CENSUS_PASS = t.CENSUS_UNAVAILABLE, t.CENSUS_DROPPED, t.CENSUS_PASS
FEAT_COLS = t.DECLARED["columns"]["features"]
PRED_COLS = t.DECLARED["columns"]["pred"]
QUOTE_COLS = t.DECLARED["columns"]["quotes"]
CAP_KINDS = ("meta", "quotes", "features")
CENSUS_DROPPED_FAILSAFE = f"{CENSUS_DROPPED} (classifier fail-safe)"
GATE_FIELDS = {"units_median": "units_median_min", "projected_labelled_units": "units_projected_min", "nonstationarity_median_over_mean": "nonstationarity_min",
               "venue_clock_max_slot_share": "venue_clock_max", "distinct_events": "events_min", "g_eff": "g_eff_min", "unavailable_gap_points": "unavailable_gap_max_points",
               "tier_finite_share": "tier_finite_min", "mid_check_share": "mid_check_share_min", "mde_c": "mde_max_c", "f_mde_c": "f_mde_max_c"}
SEAL_GLOB = "lt14_census_inputs*"  # any LT14 seal in the seals directory (SHOULD 5: the seal is written ONCE across paths)


def rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(r) / (1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0)


# --- schema pre-check (6 job 1; headers and registry only, no value) --------------------------------------------------------------------------------------


def schema_precheck(*, engine_root: Path, snapshot_root, spec_dir: Path | None = None) -> dict:
    """6 job 1: P's registry sha and status, the column names and types of 1.2 in one capture's ``predictions`` / ``quotes`` / ``features`` file, the log fields, the sidecar header, and the
    input-clock audit (1.3). Reads no value (parquet schemas, a csv header and the registry only). The newest capture present in all three stores is used."""
    root = Path(engine_root)
    au = t.audit_input_clock(spec_dir)
    out: dict = {"audit": au, "problems": []}
    caps = sorted(p.stem for p in (root / "quotes").glob("*.parquet")) if (root / "quotes").exists() else []
    caps = [c for c in caps if (root / "features" / f"{c}.parquet").exists() and (root / "predictions" / c / f"{t.PINNED_MODEL}.parquet").exists()]
    if not caps:
        out["problems"].append("no capture holds quotes, features and P's predictions file")
        return out
    c = caps[-1]
    out["capture"] = c
    dc = t.DECLARED["columns"]
    out["problems"] += [f"predictions: {x}" for x in t.schema_problems(root / "predictions" / c / f"{t.PINNED_MODEL}.parquet", dc["pred"], dc["pred_types"])]
    out["problems"] += [f"quotes: {x}" for x in t.schema_problems(root / "quotes" / f"{c}.parquet", dc["quotes"])]
    out["problems"] += [f"features: {x}" for x in t.schema_problems(root / "features" / f"{c}.parquet", dc["features"])]
    out["pred_meta_keys"] = sorted(t.parquet_meta(root / "predictions" / c / f"{t.PINNED_MODEL}.parquet"))
    sc = None
    for r in (snapshot_root if isinstance(snapshot_root, (list, tuple)) else [snapshot_root]):
        if (Path(r) / c / "rows_ext.csv.gz").exists():
            sc = Path(r) / c / "rows_ext.csv.gz"
    if sc is None:
        out["problems"].append("sidecar rows_ext.csv.gz not found for the capture")
    else:
        hdr = list(pd.read_csv(sc, nrows=0).columns)
        out["sidecar_header_missing"] = [x for x in dc["sidecar"] if x not in hdr]
        out["problems"] += [f"sidecar: missing {x}" for x in out["sidecar_header_missing"] if x != "fees_enabled"]
    logs = sorted((root / "logs").glob("predictions-*.jsonl")) if (root / "logs").exists() else []
    if logs:
        line = next((ln for ln in logs[-1].read_text().splitlines()[::-1] if t.PINNED_MODEL in ln), None)
        have = sorted(json.loads(line)) if line else []
        out["log_fields_missing"] = [f for f in dc["log_fields"] if f not in have]
        out["problems"] += [f"log: missing {f}" for f in out["log_fields_missing"]]
    else:
        out["problems"].append("no predictions log")
    out["pass"] = bool(au["pass"] and not out["problems"])
    return out


# --- seal and restore readiness (3, 6 jobs 2) -------------------------------------------------------------------------------------------------------------


def restore_readiness(snapshot_roots, spec: dict, now: float) -> dict:
    """The one-shot restore's ONLY refusal, LT12 / LT13's rule unchanged (it reads the spec's grid, span and ``lag_slots_after``, which LT14 declares identically)."""
    return lt12.restore_readiness(snapshot_roots, spec, now)


def _meta_by_slot(root: Path, lo: int, hi: int) -> dict[int, dict]:
    out: dict[int, dict] = {}
    d = root / "meta"
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            m = json.loads(p.read_text())
            k = int(m["slot"])
        except (OSError, ValueError, KeyError):
            continue
        if lo <= k <= hi:
            out.setdefault(k, m)  # the first (sorted) capture of a slot wins, as the engine's own index
    return out


def _pred_log(root: Path, lo_day: str, hi_day: str) -> dict[str, dict]:
    """The first valid line per capture for P from ``logs/predictions-YYYYMMDD.jsonl`` (UTC days in [lo_day, hi_day]): its receipt time ``written_utc`` and spec / fit / file hashes."""
    out: dict[str, dict] = {}
    d = root / "logs"
    need = t.DECLARED["columns"]["log_fields"]
    for p in sorted(d.glob("predictions-*.jsonl")) if d.exists() else []:
        day = p.stem.rsplit("-", 1)[-1]
        if not (lo_day <= day <= hi_day):
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if r.get("model_id") == t.PINNED_MODEL and all(r.get(f) for f in need) and r["capture_id"] not in out:
                out[r["capture_id"]] = {f: r.get(f) for f in (*need, "slot", "n_rows")}
    return out


def seal_inputs(*, engine_root: Path, snapshot_root, spec_dir: Path | None = None, spec: dict | None = None, design_path: Path | None = None, ledger_path: Path | None = None,
                now: float | None = None, seals_dir: Path | None = None) -> dict:
    """The LT14 seal (3, once): the engine files the census may open, each hashed (``meta``, ``quotes`` for every slot of the span and its three tail slots; ``features``, P's
    ``predictions`` file and the sidecar for the span's slots), P's first valid log line per capture (the receipt time), the champion-history lines, the registry sha, the frozen design-text
    sha256, the input-clock audit and the code / declaration hashes. Refuses on a design / ledger mismatch, an imported-file mismatch, a failed audit (``withdrawn_pre_census (input
    clock)``), a sidecar found in two roots with different bytes, an LT14 seal that already exists under ``seals_dir`` (once, across paths), or before the last tail slot is complete or
    past its tolerance. Files the stores should hold but do not are recorded as ``absent_files`` (a later read returns missing, never a refusal)."""
    spec = spec or t.load_spec()
    for chk in (lambda: t.spec_error(spec), lambda: t.design_text_error(design_path, ledger_path), t.imported_error):
        if (err := chk()):
            return err
    sdir = Path(seals_dir or t.SEALS)
    if (prev := sorted(sdir.glob(SEAL_GLOB)) if sdir.exists() else []):
        return {"error": f"an LT14 seal already exists ({prev[0]}): the seal is written once; refused"}
    au = t.audit_input_clock(spec_dir)
    if not au["pass"]:
        return {"error": "P fails the input-clock audit (1.3): LT14 is withdrawn_pre_census (input clock); no seal is written", "status": t.WITHDRAWN_CLOCK, "audit": au}
    root = Path(engine_root)
    ci = spec["census_inputs"]
    sp, tl = t.span_slots(spec), t.tail_slots(spec)
    now = b.now_ts() if now is None else now
    metas = _meta_by_slot(root, sp[0], tl[-1])
    if now < epoch(ci["seal_not_before_utc"]) and tl[-1] not in metas:
        return {"error": f"the seal waits for the {iso(t.slot_time(tl[-1]))} capture to be complete or past its tolerance (3)", "retry": True}
    files: dict[str, dict] = {}
    absent_files: list[str] = []
    slots: dict[str, str] = {}
    conflicts: list[dict] = []
    pred_meta: dict[str, dict] = {}
    roots = [Path(r) for r in (snapshot_root if isinstance(snapshot_root, (list, tuple)) else [snapshot_root])]
    for k in sp + tl:
        m = metas.get(k)
        if m is None:
            continue
        cid = m["capture_id"]
        slots[str(k)] = cid
        rels = [f"meta/{cid}.json", f"quotes/{cid}.parquet"]
        if k in sp:
            rels += [f"features/{cid}.parquet", f"predictions/{cid}/{t.PINNED_MODEL}.parquet"]
        for rel in rels:
            p = root / rel
            if p.exists():
                files[rel] = {"sha256": b.sha256_file(p), "kind": rel.split("/")[0], "capture": cid}
            else:
                absent_files.append(rel)
        if k in sp:
            found = [r / cid / "rows_ext.csv.gz" for r in roots if (r / cid / "rows_ext.csv.gz").exists()]
            if found:
                h = b.sha256_file(found[0])
                for q in found[1:]:
                    if b.sha256_file(q) != h:
                        conflicts.append({"capture": cid, "root_a": str(found[0]), "root_b": str(q)})
                files[f"snapshots/{cid}/rows_ext.csv.gz"] = {"sha256": h, "kind": "sidecar", "capture": cid}
            pp = root / f"predictions/{cid}/{t.PINNED_MODEL}.parquet"
            if pp.exists():
                md = t.parquet_meta(pp)
                pred_meta[cid] = {f: md.get(f) for f in ("spec_sha256", "fit_id", "features_sha256", "n_rows")}
    if conflicts:
        return {"error": "a sidecar exists in two roots with different bytes: LT14 seal refused", "conflicts": conflicts[:50]}
    day0, day1 = iso(epoch(ci["span"]["start_utc"]))[:10].replace("-", ""), iso(t.slot_time(tl[-1]))[:10].replace("-", "")
    hist = root / "champion" / "history.jsonl"
    champ = []
    if hist.exists():
        for ln in hist.read_text().splitlines():
            try:
                champ.append(json.loads(ln))
            except ValueError:
                continue
    miss = [iso(t.slot_time(k)) for k in sp + tl if str(k) not in slots]
    return {"purpose": "LT14 census inputs (LIVE_TESTS_14.md 3): every engine file the census may open, each hashed; counts-only use; no later-slot price",
            "written_utc": iso(now), "design_text_sha256": t.DESIGN_TEXT_SHA256, "declaration_sha256": t.declaration_sha256(), "code_sha256": t.code_hashes(),
            "imported_sha256": t.imported_hashes(), "pinned_model": {"model_id": t.PINNED_MODEL, "spec_sha256": t.PINNED_SPEC_SHA256}, "audit": au, "registry_sha256": au.get("registry_sha256"),
            "registry_entry": au.get("registry_entry"), "spec_canonical_sha256": au.get("spec_canonical_sha256"),
            "span": ci["span"], "tail_slots_utc": [iso(t.slot_time(k)) for k in tl], "refuse_at_or_after_utc": ci["refuse_at_or_after_utc"],
            "slots": slots, "slot_times": {str(k): iso(t.slot_time(k)) for k in sp + tl}, "pred_log": {c: v for c, v in _pred_log(root, day0, day1).items() if c in {slots[str(k)] for k in sp if str(k) in slots}}, "pred_meta": pred_meta, "champion_history": champ,
            "missing": {"slots": miss}, "n_missing": len(miss), "absent_files": sorted(absent_files), "n_files": len(files), "files": dict(sorted(files.items()))}


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = [{"what": d, "value": s_, "error": "at or after the sealed bound"} for d, s_ in (seal.get("slot_times") or {}).items() if epoch(s_) >= bound]
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def p_status(seal: dict, k: int, spec: dict) -> str:
    """1.5 step 1 / 1.4 on-time rule, from the seal alone: ``absent`` (no P file or no log line), ``spec_mismatch`` (the log or the file metadata carries another spec sha), ``late`` (the
    log line is at or after slot k + 1's time), ``log_file_mismatch`` (the log line's sha256 is not the sealed file's) or ``ok``."""
    cid = seal["slots"].get(str(k))
    if cid is None or f"predictions/{cid}/{t.PINNED_MODEL}.parquet" not in seal["files"] or cid not in (seal.get("pred_log") or {}):
        return "absent"
    ln, md = seal["pred_log"][cid], (seal.get("pred_meta") or {}).get(cid, {})
    if ln.get("spec_sha256") != t.PINNED_SPEC_SHA256 or md.get("spec_sha256") != t.PINNED_SPEC_SHA256:
        return "spec_mismatch"
    if ln.get("sha256") != seal["files"][f"predictions/{cid}/{t.PINNED_MODEL}.parquet"]["sha256"]:
        return "log_file_mismatch"  # the log line attests another file than the sealed one: its written_utc proves nothing about this file (SHOULD 3)
    if not (epoch(ln["written_utc"]) < t.slot_time(k + 1)):
        return "late"
    return "ok"


def seal_coverage(seal: dict, spec: dict) -> dict:
    """3 'Coverage first', from the seal manifest BEFORE any row is read: a covered origin is a span slot whose ``meta``, ``quotes``, ``features`` and sidecar are all sealed (ambiguity A1);
    covered days = covered origins / 12 (>= 7.0); P's on-time files must cover >= 90% of the 120 census captures."""
    sp = t.span_slots(spec)
    ci = spec["census_inputs"]
    cov = []
    for k in sp:
        cid = seal["slots"].get(str(k))
        if cid and all(f"{a}/{cid}.parquet" in seal["files"] or f"{a}/{cid}.json" in seal["files"] for a in ("meta", "quotes", "features")) and f"snapshots/{cid}/rows_ext.csv.gz" in seal["files"]:
            cov.append(k)
    stat = {k: p_status(seal, k, spec) for k in sp}
    ok_n = sum(1 for v in stat.values() if v == "ok")
    cd = len(cov) / 12.0
    pshare = ok_n / float(ci["expected_origins"])
    return {"covered_origins": len(cov), "covered_days": cd, "min_covered_days": ci["min_covered_days"], "p_ontime_files": ok_n, "p_ontime_share": pshare, "p_ontime_min": ci["p_ontime_min"],
            "p_status_counts": dict(Counter(stat.values())), "ok": bool(cd >= ci["min_covered_days"] and pshare >= ci["p_ontime_min"]), "origins": cov}


def _durable(status: str, error: str, extra: dict) -> dict:
    """A refusal that is also a durable census outcome (SHOULD 2): the runner writes it (write-once) instead of exiting without a record."""
    return {"error": error, "durable": True, "status": status, "statuses": {"CH262": status},
            "lists": {"k_tests": [], "dropped_tests": [], "census_unavailable": [], "withdrawn_pre_census": ["CH262"] if status == t.WITHDRAWN_CLOCK else []}, **extra}


def _load_for_census(seal: Path, engine_root: Path, spec: dict, verify: bool, design_path, ledger_path, blocks, spec_dir, snapshot_root=()) -> dict:
    """The refusals every census runs first (3, 'Refusals'), in order: a forbidden block; the design text and the ledger freeze hash; the seal's design hash and declaration; the imported-file
    pins; the code files; a P that fails the (re-run) input-clock audit; the sealed bound; then every sealed file present and hash-equal (an unsealed or altered input refuses)."""
    t.check_blocks(blocks)
    if (serr := t.spec_error(spec)):
        return serr
    seal_d = json.loads(Path(seal).read_text())
    if (derr := t.design_text_error(design_path, ledger_path)):
        return derr
    if seal_d.get("design_text_sha256") != t.DESIGN_TEXT_SHA256:
        return {"error": "the seal was written against a different LIVE_TESTS_14.md (its design-text sha256 is not the ledger's freeze hash): census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
    if seal_d.get("declaration_sha256") != t.declaration_sha256():
        return {"error": "the declared constants differ from those at seal time (declaration_sha256): census refused"}
    if (ierr := t.imported_error()):
        return ierr
    if seal_d.get("imported_sha256") != t.imported_hashes():
        return {"error": "the imported helper files differ from those at seal time: census refused"}
    if seal_d.get("code_sha256") != t.code_hashes():
        return {"error": "the LT14 code files differ from those at seal time (code_sha256): census refused", "seal": seal_d.get("code_sha256"), "code": t.code_hashes()}
    au = t.audit_input_clock(spec_dir)
    if not au["pass"]:
        return _durable(t.WITHDRAWN_CLOCK, "P fails the input-clock audit (1.3), re-run at the start: LT14 is withdrawn_pre_census (input clock)",
                        {"audit": au, "design_text_sha256": t.DESIGN_TEXT_SHA256, "declaration_sha256": t.declaration_sha256(), "code_sha256": t.code_hashes()})
    # re-check F3: only model_id, spec_sha256 and added_utc of P's entry are compared (with the spec's canonical sha256); ``status`` is printed, never compared (a demotion of P is not a
    # refusal: the audit does not read it, and a P that stopped is ``unavailable_spec``, not a refusal, design 1.4 / l.217-219)
    cmp_keys = ("model_id", "spec_sha256", "added_utc")
    ent_s, ent_n = seal_d.get("registry_entry") or {}, au.get("registry_entry") or {}
    if {k_: ent_n.get(k_) for k_ in cmp_keys} != {k_: ent_s.get(k_) for k_ in cmp_keys} or not ent_s or au.get("spec_canonical_sha256") != seal_d.get("spec_canonical_sha256"):
        return {"error": "P's registry entry (model_id, spec_sha256, added_utc) or P's spec file (canonical sha256) differs from the sealed one: census refused",
                "sealed": {"registry_entry": seal_d.get("registry_entry"), "spec_canonical_sha256": seal_d.get("spec_canonical_sha256")},
                "now": {"registry_entry": au.get("registry_entry"), "spec_canonical_sha256": au.get("spec_canonical_sha256")}}
    # the whole registry file's sha256 is PRINT ONLY: other models may be added after the seal without voiding it (MUST 4)
    if (viol := bound_violations(seal_d, spec)):
        return {"error": "sealed bound violated: census refused", "bad": viol[:20]}
    bad = []
    roots = [Path(r) for r in (snapshot_root if isinstance(snapshot_root, (list, tuple)) else [snapshot_root])] if snapshot_root else []
    if verify:
        for rel, v in seal_d["files"].items():
            if v["kind"] == "sidecar":  # every copy of a sealed sidecar in the snapshot roots must hash to the sealed sha256, and one must exist (MUST 1)
                found = [r / v["capture"] / "rows_ext.csv.gz" for r in roots if (r / v["capture"] / "rows_ext.csv.gz").exists()]
                if not found:
                    bad.append({"file": rel, "error": "absent"})
                bad += [{"file": rel, "error": "sha256 mismatch", "root": str(q.parents[1])} for q in found if b.sha256_file(q) != v["sha256"]]
                continue
            p = Path(engine_root) / rel
            if not p.exists() or b.sha256_file(p) != v["sha256"]:
                bad.append({"file": rel, "error": "absent" if not p.exists() else "sha256 mismatch"})
    if bad:
        return {"error": "input identity check failed (an input is not named in the seal with an equal sha256): census refused", "bad": bad[:50], "n_bad": len(bad)}
    return {"seal": seal_d, "registry_sha256_now": au.get("registry_sha256"),
            "p_registry_status": {"sealed": (seal_d.get("registry_entry") or {}).get("status"), "now": (au.get("registry_entry") or {}).get("status")}}  # print only (F3)


# --- the data pass ------------------------------------------------------------------------------------------------------------------------------------


def _event_sizes(feat: pd.DataFrame) -> pd.Series:
    ev = feat["event_id"].to_numpy(np.int64)
    s = pd.Series(ev[ev >= 0]).value_counts()
    return s


def census_units(*, seal: Path, engine_root: Path, snapshot_root, spec: dict | None = None, spec_dir: Path | None = None, verify: bool = True, design_path=None, ledger_path=None,
                 blocks=("CH262",)) -> dict:
    """CC14's data pass: one streaming pass over the sealed span, one capture at a time. Returns ``{"error"}``, ``{"unavailable"}`` (coverage first: NO row opened) or the accumulators."""
    spec = spec or t.load_spec()
    ld = _load_for_census(seal, engine_root, spec, verify, design_path, ledger_path, blocks, spec_dir, snapshot_root)
    if "error" in ld:
        return ld
    sd = ld["seal"]
    cov = seal_coverage(sd, spec)
    head = {"design_text_sha256": t.DESIGN_TEXT_SHA256, "declaration_sha256": t.declaration_sha256(), "code_sha256": t.code_hashes(), "imported_sha256": t.imported_hashes(),
            "spec_used_sha256": t.spec_hash(spec), "pinned_model": sd["pinned_model"], "audit": sd["audit"], "registry_sha256_sealed": sd.get("registry_sha256"),
            "registry_sha256_now": ld["registry_sha256_now"], "p_registry_status": ld["p_registry_status"], "coverage": cov, "span": sd["span"]}
    if not cov["ok"]:
        return {"unavailable": {**head, "status": CENSUS_UNAVAILABLE, "statuses": {"CH262": CENSUS_UNAVAILABLE}}}
    rdr = t.EngineReader(engine_root, snapshot_root, {int(k): v for k, v in sd["slots"].items()}, allowed=set(sd["files"]), absent=set(sd.get("absent_files") or ()))
    sp = t.span_slots(spec)
    covered = set(cov["origins"])
    # the crypto classifier fail-safe BEFORE the data pass (the sidecars' distinct fee_category values only; SHOULD 2)
    pre_cat: Counter = Counter()
    for k in sp:
        if k in covered:
            e0 = t.load_sidecar(rdr.sidecar_path(k))
            if e0 is not None:
                pre_cat.update(e0["fee_category"].map(lambda v: "" if pd.isna(v) else str(v)).value_counts().to_dict())
    fs = b.crypto_failsafe(dict(pre_cat))
    if not fs["classifier_shown_to_work"]:
        gates = {g_: {"value": None, "pass": False, "line": spec["census_gates"][f_]} for g_, f_ in GATE_FIELDS.items()}
        return {"dropped": {**head, "scope": "CH262 only", "crypto_classifier_shown_to_work": False, "fee_category_values": fs["distinct_values"],
                            "CH262": {"status": CENSUS_DROPPED_FAILSAFE, "gates": gates, "failed": list(gates), "reason": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN (LT12 rule)"},
                            "status": CENSUS_DROPPED_FAILSAFE, "statuses": {"CH262": CENSUS_DROPPED_FAILSAFE}, "lists": {"k_tests": [], "dropped_tests": ["CH262"], "census_unavailable": []}}}
    rss_max = spec["census_inputs"]["rss_refuse_mb"]
    per_cap, U_parts, M_parts, rest_parts, pre_parts = [], [], [], [], []
    fee_abs, fee_sgn = [], []
    sgn_counts, abs_counts, arm_counts = {}, {}, {"sports": {}, "crypto": {}}
    cat_values: Counter = Counter()
    lc, toff_k, toff_k1 = {}, [], []
    pstat = {}
    for k in sp:
        if k not in covered:
            per_cap.append({"slot": k, "covered": False})
            continue
        cid = rdr.cap(k)
        meta = rdr.meta(k)
        ext = t.load_sidecar(rdr.sidecar_path(k))
        if ext is not None:
            cat_values.update(ext["fee_category"].map(lambda v: "" if pd.isna(v) else str(v)).value_counts().to_dict())
        stt = p_status(sd, k, spec)
        row = {"slot": k, "cap": cid, "covered": True, "p_status": stt}
        if stt != "ok":
            pstat[cid] = {"p_status": stt}
            per_cap.append(row)
            continue
        feat = rdr.features(k, FEAT_COLS)
        pred = t.read_cols(rdr.pred_path(k, t.PINNED_MODEL), PRED_COLS)
        pm = sd["pred_meta"].get(cid, {})
        fsha = sd["files"][f"features/{cid}.parquet"]["sha256"]
        if len(pred) != len(feat) or (pm.get("features_sha256") and pm["features_sha256"] != fsha):
            row["p_status"] = "misaligned"
            per_cap.append(row)
            continue
        quo = rdr.quotes(k, k, QUOTE_COLS)
        C, steps, pre = t.candidates(feat, pred, quo, ext)
        row["steps"] = steps
        nxt_meta = rdr.meta(k + 1) if rdr.cap(k + 1) else None
        nxt = rdr.quotes(k, k + 1, ["market_id", "t_off", "st"]) if nxt_meta is not None and rdr.cap(k + 1) else None
        start_next = epoch(nxt_meta["started_utc"]) if nxt_meta else None
        C["cls"] = t.classify_next(C["market_id"].to_numpy(np.int64), C["t_row"].to_numpy(np.float64), nxt, start_next)
        if nxt is not None:
            q1 = nxt.drop_duplicates("market_id").set_index("market_id")["t_off"]
            C["t_off_k1"] = q1.reindex(C["market_id"].to_numpy()).to_numpy(np.float64)
        else:
            C["t_off_k1"] = np.nan
        dc = t.deciles(C)
        ds = t.deciles(C, signed=True)
        row["n_C"], row["n_top"] = int(len(C)), int(dc["n_top"])
        w = epoch(sd["pred_log"][cid]["written_utc"])
        fin_t = epoch(meta.get("finished_utc")) if meta else math.nan
        lc[k] = w - fin_t
        # |s| decile and signed decile counts by tier, summed fee splits
        abs_counts[k] = np.bincount(C["tier"].to_numpy()[dc["top"]], minlength=4)
        sgn_counts[k] = np.bincount(C["tier"].to_numpy()[ds["top"]], minlength=4)
        fee_abs.append(t.fee_split(C, dc["top"]))
        fee_sgn.append(t.fee_split(C, ds["top"]))
        pre_parts.append(pre.groupby(["tier", "category", "label"]).size().rename("n").reset_index())
        for sc in ("sports", "crypto"):
            Ca, _, _ = t.candidates(feat, pred, None, ext, scope=sc)
            arm_counts[sc][k] = np.bincount(Ca["tier"].to_numpy()[t.deciles(Ca)["top"]], minlength=4) if len(Ca) else np.zeros(4, int)
        # the top decile (all tiers), with the origin-side fields the gates and prints need; ``rest`` aggregated by (tier, family, class)
        top = C.iloc[dc["top"]].copy()
        esz = _event_sizes(feat)
        top["esize"] = top["event_id"].map(esz).fillna(1).to_numpy()
        top["slot"], top["sod"], top["day"] = k, k % 12, k // 12
        top["sign"] = np.sign(top["s_int"].to_numpy())
        top["mid_diff"] = np.abs(top["mid_k"].to_numpy() - top["ms_mid"].to_numpy(np.float64))
        U_parts.append(top[["slot", "sod", "day", "market_id", "ekey", "event_id", "tier", "fee_class", "category", "fam", "sign", "spread_c", "mid_k", "mid_diff", "t_off_k", "t_off_k1", "ms_neg_risk", "mo_d2h", "esize", "cls", "s_int"]])
        rest = C.iloc[dc["rest"]]
        rest_parts.append(rest.groupby(["tier", "fam", "cls"]).size().rename("n").reset_index())
        # M6's census design rows (10k-100k tier: the top decile D = 1, the middle deciles 4-6 D = 0)
        mid_rows = C.iloc[dc["middle"]]
        tp = top[top["tier"] == t.PRIMARY_TIER]
        mp = mid_rows[mid_rows["tier"] == t.PRIMARY_TIER]
        for part, dval in ((tp, 1.0), (mp, 0.0)):
            if len(part):
                x = part[["market_id", "t_row", "spread_c", "ms_log_liq", "ms_mid", "ms_hours_to_end", "ms_rv24", "mo_d2h", "fam"]].copy()
                x["D"], x["sod"], x["stratum"] = dval, k % 12, part["market_id"].astype(str) + "|" + str(k // 12)
                M_parts.append(x)
        toff_k.append(tp["t_off_k"].to_numpy(np.float64))
        toff_k1.append(tp.loc[tp["cls"] == "labelled", "t_off_k1"].to_numpy(np.float64))
        per_cap.append(row)
        if rss_mb() > rss_max:
            raise Refused(f"peak RSS {rss_mb():.0f} MB exceeds the {rss_max:.0f} MB refusal line (6 job 3)")
    return {"head": head, "cov": cov, "per_cap": per_cap, "U": pd.concat(U_parts, ignore_index=True) if U_parts else pd.DataFrame(), "M": pd.concat(M_parts, ignore_index=True) if M_parts else pd.DataFrame(),
            "rest": pd.concat(rest_parts, ignore_index=True) if rest_parts else pd.DataFrame(), "pre": pd.concat(pre_parts, ignore_index=True) if pre_parts else pd.DataFrame(),
            "fee_abs": fee_abs, "fee_sgn": fee_sgn, "abs_counts": abs_counts, "sgn_counts": sgn_counts, "arm_counts": arm_counts, "cat_values": dict(cat_values), "lc": lc,
            "toff_k": np.concatenate(toff_k) if toff_k else np.array([]), "toff_k1": np.concatenate(toff_k1) if toff_k1 else np.array([]), "seal": sd}


# --- the gates and prints -----------------------------------------------------------------------------------------------------------------------------


def _q(a, qs=range(10, 100, 10)) -> dict:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return {f"q{q}": (float(np.percentile(a, q)) if len(a) else None) for q in qs}


def _tier_matrix(counts: dict, covered: list[int]) -> dict:
    out = {}
    for ti, name in enumerate(t.TIER_NAMES):
        out[name] = t.dist([int(counts[k][ti]) if k in counts else 0 for k in covered])
    return out


def census_ch262(cu: dict, spec: dict) -> dict:
    """3: the CH262 gate block (10k-100k tier), the census-fixed values and the prints, from the accumulators."""
    gt, mde = spec["census_gates"], spec["mde"]
    cov = cu["cov"]
    covered = list(cov["origins"])
    f = mde["projection_days"] / cov["covered_days"]
    U = cu["U"]
    fam_ex: dict[str, list[str]] = {}
    for ti, name in enumerate(t.TIER_NAMES):
        u = U[U["tier"] == ti]
        sh = u["fam"].value_counts(normalize=True) if len(u) else pd.Series(dtype=float)
        fam_ex[name] = sorted(sh[sh > spec["decile"]["family_exclusion_share"]].index.tolist())
    P = U[(U["tier"] == t.PRIMARY_TIER) & ~U["fam"].isin(fam_ex[t.TIER_NAMES[t.PRIMARY_TIER]])].copy()
    per_cap_n = P.groupby("slot").size().reindex(covered, fill_value=0)
    lab_m = P["cls"] == "labelled"
    n_units, n_lab = int(len(P)), int(lab_m.sum())
    n_proj = n_lab * f
    markets = int(P["market_id"].nunique())
    m21 = (n_units / markets * f) if markets else math.nan
    de_gate = max(mde["de_floor"], 1.0 + (m21 - 1.0) * mde["de_rho"]) if math.isfinite(m21) else math.nan
    sd_plan = max(mde["sd_floor_c"], 100.0 * float(np.nanstd(P["mo_d2h"].to_numpy(np.float64), ddof=1))) if n_units > 1 else math.nan
    mult = mde["t_sum"] * mde["day_factor"]
    mde_decl = mult * sd_plan * math.sqrt(de_gate / (mde["n_eff_frac"] * n_proj)) if n_proj > 0 and math.isfinite(sd_plan) and math.isfinite(de_gate) else math.nan
    L = P[lab_m]
    sz_e, sz_d, sz_c = L.groupby("ekey").size().to_numpy(), L.groupby("day").size().to_numpy(), L.groupby(["ekey", "day"]).size().to_numpy()
    # the cluster sizes are the census's own, UNSCALED labelled-unit counts (a 21-day window has more days, not more units per day; MUST 3); n is the projected labelled units
    de_e, de_d, de_c = (t.de_cluster(s_, 1.0, mde["de_rho"]) for s_ in (sz_e, sz_d, sz_c))
    de_tw = de_e + de_d - de_c
    ses = {"event": t.design_se(n_proj, sd_plan, de_e), "twoway": t.design_se(n_proj, sd_plan, de_tw), "day": t.design_se(n_proj, sd_plan, de_d)}
    se_max = max(ses.values()) if all(math.isfinite(v) for v in ses.values()) else math.nan
    mde_design = mult * se_max
    fm = math.sqrt(2.0 / (1.0 - max(0.0, mde["planning_r"])))
    # print only: the same quantities with cluster sizes scaled by the projection factor f (the superseded reading, A6(a))
    s_e, s_d, s_c = (t.de_cluster(s_, f, mde["de_rho"]) for s_ in (sz_e, sz_d, sz_c))
    s_tw = s_e + s_d - s_c
    s_ses = {"event": t.design_se(n_proj, sd_plan, s_e), "twoway": t.design_se(n_proj, sd_plan, s_tw), "day": t.design_se(n_proj, sd_plan, s_d)}
    s_mde = mult * max(s_ses.values()) if all(math.isfinite(v) for v in s_ses.values()) else math.nan
    scaled_print = {"DE": {"event": s_e, "twoway": s_tw, "day": s_d}, "ses_c": s_ses, "mde_design_c": s_mde, "f_mde_design_c": s_mde * fm, "note": "print only; never a gate (MUST 3)"}
    mde_gate_v = max(mde_decl, mde_design) if math.isfinite(mde_decl) and math.isfinite(mde_design) else math.nan
    ev_sizes = P.groupby("ekey").size().to_numpy()
    ge = t.kish(ev_sizes)
    sod_share = (P.groupby("sod").size() / n_units).max() if n_units else math.nan
    rs = cu["rest"]
    rs = rs[(rs["tier"] == t.PRIMARY_TIER) & ~rs["fam"].isin(fam_ex[t.TIER_NAMES[t.PRIMARY_TIER]])] if len(rs) else rs
    rest_n = int(rs["n"].sum()) if len(rs) else 0
    rest_un = int(rs.loc[rs["cls"] != "labelled", "n"].sum()) if len(rs) else 0
    top_sh = 1.0 - n_lab / n_units if n_units else math.nan
    rest_sh = rest_un / rest_n if rest_n else math.nan
    gap = 100.0 * (top_sh - rest_sh) if math.isfinite(top_sh) and math.isfinite(rest_sh) else math.nan
    steps = [r["steps"] for r in cu["per_cap"] if r.get("steps")]
    in_scope, tier_na = sum(s_["in_scope"] for s_ in steps), sum(s_["tier_na"] for s_ in steps)
    finite_share = 1.0 - tier_na / in_scope if in_scope else math.nan
    md = P["mid_diff"].to_numpy(np.float64)
    mid_share = float(np.mean(np.isfinite(md) & (md <= spec["mid_check"]["tol"]))) if len(md) else math.nan
    gates = {
        "units_median": {**t.gate(float(per_cap_n.median()) if len(per_cap_n) else math.nan, lambda v: v >= gt["units_median_min"]), "line": gt["units_median_min"]},
        "projected_labelled_units": {**t.gate(n_proj, lambda v: v >= gt["units_projected_min"]), "line": gt["units_projected_min"]},
        "nonstationarity_median_over_mean": {**t.gate(float(per_cap_n.median() / per_cap_n.mean()) if len(per_cap_n) and per_cap_n.mean() > 0 else math.nan, lambda v: v >= gt["nonstationarity_min"]), "line": gt["nonstationarity_min"]},
        "venue_clock_max_slot_share": {**t.gate(float(sod_share), lambda v: v <= gt["venue_clock_max"]), "line": gt["venue_clock_max"]},
        "distinct_events": {**t.gate(float(P["ekey"].nunique()) if n_units else math.nan, lambda v: v >= gt["events_min"]), "line": gt["events_min"]},
        "g_eff": {**t.gate(ge, lambda v: v >= gt["g_eff_min"]), "line": gt["g_eff_min"]},
        "unavailable_gap_points": {**t.gate(gap, lambda v: v <= gt["unavailable_gap_max_points"]), "line": gt["unavailable_gap_max_points"]},
        "tier_finite_share": {**t.gate(finite_share, lambda v: v >= gt["tier_finite_min"]), "line": gt["tier_finite_min"]},
        "mid_check_share": {**t.gate(mid_share, lambda v: v >= gt["mid_check_share_min"]), "line": gt["mid_check_share_min"]},
        "mde_c": {**t.gate(mde_gate_v, lambda v: v <= gt["mde_max_c"]), "line": gt["mde_max_c"]},
        "f_mde_c": {**t.gate(mde_gate_v * fm if math.isfinite(mde_gate_v) else math.nan, lambda v: v <= gt["f_mde_max_c"]), "line": gt["f_mde_max_c"]},
    }
    passed = all(g_["pass"] for g_ in gates.values())
    sp_ = P["spread_c"].to_numpy(np.float64)
    hf = spec["hurdle_formula"]
    h_mean = 2.0 * (hf["AS_c"] - float(np.nanmean(sp_)) / 2.0) - hf["rebates_c"] if n_units else math.nan
    h_p50 = 2.0 * (hf["AS_c"] - float(np.nanmedian(sp_)) / 2.0) - hf["rebates_c"] if n_units else math.nan
    ev_sorted = np.sort(ev_sizes)[::-1]
    top10 = float(ev_sorted[: max(1, int(math.ceil(len(ev_sorted) / 10.0)))].sum() / ev_sorted.sum()) if len(ev_sorted) else math.nan
    # M6 census design: control rank, dropped columns, VIF of D (no target)
    M = cu["M"]
    m6 = {"rows": int(len(M))}
    if len(M):
        M = M[~M["fam"].isin(fam_ex[t.TIER_NAMES[t.PRIMARY_TIER]])]
        Dm = t.m6_design(M)
        res = t.resolve_aliased_controls14(Dm, "D", spec["m6"]["controls"])
        m6.update({"rows_after_exclusion": int(len(M)), "rank": res["rank"], "n_cols": res["n_cols"], "n_cols_before": res.get("n_cols_before"), "dropped": res["dropped"],
                   "zero_variance_dropped": res["zero_variance_dropped"], "status": res["status"], "reason": res["reason"], "term_aliased": res["term_aliased"],
                   "vif_D": t.vif_of(Dm, "D", res["keep"]) if res["status"] == "ok" else None})
    # tenure of primary units (consecutive-capture runs per market), distinct markets
    runs = []
    for _, g_ in P.groupby("market_id")["slot"]:
        s_ = np.sort(g_.to_numpy())
        br = np.nonzero(np.diff(s_) != 1)[0]
        edges = np.concatenate([[0], br + 1, [len(s_)]])
        runs += list(np.diff(edges))
    uc = P["cls"].value_counts().to_dict()
    unav_top = {t.TIER_NAMES[ti]: U[U["tier"] == ti]["cls"].value_counts().to_dict() for ti in range(4)}
    rest_all = cu["rest"]
    unav_rest = {t.TIER_NAMES[ti]: (rest_all[rest_all["tier"] == ti].groupby("cls")["n"].sum().to_dict() if len(rest_all) else {}) for ti in range(4)}
    ge100 = U[U["tier"] == 3]
    g100_cap = ge100.groupby("slot").size().reindex(covered, fill_value=0)
    pre = cu["pre"]
    confusion = (pre.groupby(["tier", "category", "label"])["n"].sum().reset_index().to_dict("records") if len(pre) else [])
    champs = cu["seal"].get("champion_history") or []
    fee_class_tier = sum_fee(cu)
    prints = {
        "units_per_capture_by_tier_abs_decile": _tier_matrix(cu["abs_counts"], covered), "units_per_capture_by_tier_signed_decile": _tier_matrix(cu["sgn_counts"], covered),
        "primary_units_per_capture": t.dist(per_cap_n.to_numpy()), "fee_class_by_tier_summed_abs": fee_class_tier["abs"], "fee_class_by_tier_summed_signed": fee_class_tier["signed"],
        "category_x_pinned_classifier_pre_scope": confusion, "up_down": {"up": int((P["sign"] > 0).sum()), "down": int((P["sign"] < 0).sum())},
        "exclusion_steps_per_capture": [{"slot": r["slot"], "cap": r.get("cap"), **(r.get("steps") or {}), "p_status": r.get("p_status")} for r in cu["per_cap"] if r.get("covered")],
        "distinct_markets": markets, "distinct_events": int(P["ekey"].nunique()), "tenure_run_lengths": t.dist(runs), "units_per_market": (n_units / markets) if markets else None,
        "unavailable_by_class_top_by_tier": unav_top, "unavailable_by_class_rest_by_tier": unav_rest, "primary_class_counts": uc,
        "L_c_per_capture": {str(k): v for k, v in sorted(cu["lc"].items())}, "t_off_k_quantiles": _q(cu["toff_k"]), "t_off_k1_quantiles_labelled": _q(cu["toff_k1"]),
        "m6_census_design": m6, "p_spec_sha_per_capture": {r["cap"]: (cu["seal"]["pred_meta"].get(r["cap"], {}).get("spec_sha256")) for r in cu["per_cap"] if r.get("covered") and r.get("cap")},
        "p_status_counts": cov["p_status_counts"], "champion_history_lines": len(champs), "champions_in_history": sorted({str(c.get("champion")) for c in champs if c.get("champion")}),
        "two_member_neg_risk_share": float(((P["esize"] == 2) & (P["ms_neg_risk"] == 1)).mean()) if n_units else None,
        "arm_ge100k_print": {"median_units_per_capture": float(g100_cap.median()) if len(g100_cap) else None, "markets": int(ge100["market_id"].nunique()),
                             "median_ge_10": bool(len(g100_cap) and g100_cap.median() >= gt["arm_ge100k_print"]["median_min"]), "markets_ge_40": bool(ge100["market_id"].nunique() >= gt["arm_ge100k_print"]["markets_min"]),
                             "note": "printed pass / fail, never a gate"},
        "sports_arm_units_per_capture_by_tier": _tier_matrix(cu["arm_counts"]["sports"], covered), "crypto_arm_units_per_capture_by_tier": _tier_matrix(cu["arm_counts"]["crypto"], covered),
        "recomputed_hurdles_c": {"formula_from_mean_spread": h_mean, "tier_spread_figure_from_p50": h_p50, "mean_spread_c": float(np.nanmean(sp_)) if n_units else None, "p50_spread_c": float(np.nanmedian(sp_)) if n_units else None,
                                 "note": "print only; they never replace H = 1.30c"},
        "fee_category_values": cu["cat_values"], "projection_factor": f,
        "mid_k_nan_units_primary": int(P["mid_k"].isna().sum()) if n_units else 0, "mid_k_nan_units_top_all_tiers": int(U["mid_k"].isna().sum()) if len(U) else 0,
    }
    fixed = {"exclude_family": fam_ex, "event_size_quantiles": _q(ev_sizes), "event_top10pct_share": top10, "spread_quantiles_c": _q(sp_), "up_share": float((P["sign"] > 0).mean()) if n_units else None,
             "unavailable_share": top_sh, "SD_plan_c": sd_plan, "L_c_median": float(np.nanmedian(list(cu["lc"].values()))) if cu["lc"] else None}
    recorded = {"DE_gate": de_gate, "m_21": m21, "mde_declared_c": mde_decl, "mde_design_c": mde_design, "ses_c": ses, "DE": {"event": de_e, "twoway": de_tw, "day": de_d}, "f_mde_declared_c": mde_decl * fm,
                "f_mde_design_c": mde_design * fm, "n_units": n_units, "n_labelled": n_lab, "n_projected_labelled": n_proj, "print_only_scaled_cluster": scaled_print, "n_units_before_family_exclusion": int((U["tier"] == t.PRIMARY_TIER).sum())}
    return {"status": CENSUS_PASS if passed else CENSUS_DROPPED, "gates": gates, "failed": [k_ for k_, g_ in gates.items() if not g_["pass"]], "census_fixed": fixed, "recorded": recorded, "prints": prints}


def sum_fee(cu: dict) -> dict:
    return {"abs": t.sum_fee_splits(cu["fee_abs"]), "signed": t.sum_fee_splits(cu["fee_sgn"])}


def census_captures(*, seal: Path, engine_root: Path, snapshot_root, spec: dict | None = None, spec_dir: Path | None = None, verify: bool = True, design_path=None, ledger_path=None,
                    blocks=("CH262",)) -> dict:
    """CC14: coverage first (``census_unavailable (coverage)`` and nothing else), then the CH262 gate block. Counts only."""
    spec = spec or t.load_spec()
    cu = census_units(seal=seal, engine_root=engine_root, snapshot_root=snapshot_root, spec=spec, spec_dir=spec_dir, verify=verify, design_path=design_path, ledger_path=ledger_path, blocks=blocks)
    if "error" in cu:
        return cu
    if "unavailable" in cu:
        return {**cu["unavailable"], "lists": {"k_tests": [], "dropped_tests": [], "census_unavailable": ["CH262"]}}
    if "dropped" in cu:
        return bd._clean(cu["dropped"])
    head = cu["head"]
    blk = census_ch262(cu, spec)
    lists = {"k_tests": [], "dropped_tests": [], "census_unavailable": []}
    lists["k_tests" if blk["status"] == CENSUS_PASS else "dropped_tests"].append("CH262")
    return bd._clean({**head, "scope": "CH262 only; no g, no later-slot price, no LT11-LT13 or M1 / M2 object", "crypto_classifier_shown_to_work": True, "CH262": blk,
                      "statuses": {"CH262": blk["status"]}, "lists": lists})


# --- write-once (3: "a second run") ------------------------------------------------------------------------------------------------------------------


def run_marker(seal: Path) -> Path:
    return Path(str(seal) + ".census_ran")


def claim_run(seal: Path, out: Path | None, payload: dict) -> str | None:
    """The census runs ONCE: an existing marker beside the seal, or an existing ``out``, refuses. The marker is created atomically (O_EXCL) when the result is about to be written, so a crash
    before any output does not burn the run. Returns an error text or None."""
    m = run_marker(seal)
    if m.exists():
        return f"the LT14 census already ran on this seal ({m}): a second run is refused (3, write-once)"
    if out is not None and Path(out).exists():
        return f"refusing to overwrite {out}"
    return t.write_once_marker(m, payload)
