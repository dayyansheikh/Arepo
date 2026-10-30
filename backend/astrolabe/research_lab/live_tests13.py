# ruff: noqa: E501
"""LT13 stage A: the seal, the restore readiness and the counts-only census CC13 of CH253 (docs/research_lab/LIVE_TESTS_13.md section 6, design text frozen at sha256
ae594aa1...). DRAFT: nothing is registered. Research tooling only; never trades; makes no network request.

Scope (stage A, 7 build order): seal, census, header pre-check. NOT here: the target reader, worlds, size check, state-shift gate, analysis (stage B, only for tests in ``k_tests``).
CH252 is ``withdrawn_pre_census (fee reading unresolved)``: it is listed in the output and nothing is built for it. The census runs ONCE (write-once marker) and prints counts only: no
own target (no k + 1 outcome of any unit); the single later-slot quantity is the twin STATE over (k + 2, k + 3], returned by :func:`live_tests13_base.lag_twin_state` as one number per unit.
"""

from __future__ import annotations

import errno
import json
import math
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import live_tests12 as lt12
from . import live_tests12_base as b
from . import live_tests13_base as t

epoch, iso = b.epoch, b.iso
Refused = t.Refused
TEMPFAIL = t.TEMPFAIL
CENSUS_UNAVAILABLE, CENSUS_DROPPED, CENSUS_PASS = t.CENSUS_UNAVAILABLE, t.CENSUS_DROPPED, t.CENSUS_PASS
EPS = t.EPS


# --- seal windows and restore readiness (6; LT12 7's rules, reused) -------------------------------------------------------------------------------


def seal_windows(spec: dict) -> dict:
    """Sealed slot range: from 12 slots before the span (look-back, raw rows only) to 3 slots after it (twins only). No feed window: no feed capture is sealed (CH252 withdrawn)."""
    ci = spec["census_inputs"]
    sl = lt12._span_slots(spec)
    return {"captures": (sl[0] - ci["lookback_capture_slots"], sl[-1] + ci["lag_slots_after"])}


def restore_readiness(snapshot_roots, spec: dict, now: float) -> dict:
    """The one-shot restore's ONLY refusal (6 / 1.14, LT12 7 final verification fix 2): while a lag-slot capture is in progress; a final non-complete capture, one still open one slot after
    its start or none past the slot tolerance is MISSING (counted by the seal), never awaited. Reuses :func:`live_tests12.restore_readiness` unchanged (it reads only the spec's grid and
    census_inputs, which LT13 declares identically)."""
    return lt12.restore_readiness(snapshot_roots, spec, now)


def imported_error() -> dict | None:
    got, want = t.imported_hashes(), t.DECLARED["imported_sha256"]
    bad = {k_: {"got": got[k_], "declared": want.get(k_)} for k_ in got if got[k_] != want.get(k_)}
    return {"error": "an imported helper file differs from its declared sha256 (LT12 / CH251 code is pinned by hash): refused", "files": bad} if bad else None


def seal_inputs(*, snapshot_root, work: Path, spec: dict | None = None, unavailable=None, design_path: Path | None = None, ledger_path: Path | None = None) -> dict:
    """The LT13 seal (6): every complete capture (rows, manifest, sidecar) of the sealed window found in the roots (host copies first, then restore trees), each hashed. A directory
    found in two roots with different bytes refuses. Records the slot assignment, the frozen design-text sha256 (refused unless the file and the ledger agree), the spec's blocks, the
    header pre-check result (``k_block``, already filled) and the **batch-join code sha256** (the census refuses a seal without it). No feed capture is sealed."""
    spec = spec or t.load_spec()
    for chk in (lambda: t.design_text_error(design_path, ledger_path), lambda: t.reward_rule_error(spec), lambda: t.k_block_error(spec), lambda: t.scope_error(spec), imported_error):
        if (err := chk()):
            return err
    win = seal_windows(spec)
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    by_slot, _ = b._scan(Path(work), snapshot_root, [], spec)
    files, slots, conflicts = {}, {}, []
    caps_k = sorted(k for k in by_slot if win["captures"][0] <= k <= win["captures"][1])
    for k in caps_k:
        c = by_slot[k]
        if c["start"] >= bound:
            continue
        for rel, p in b.capture_files(c["dir"]):
            h = b.sha256_file(p)
            for r in b._roots(snapshot_root):
                q = Path(r) / c["id"] / p.name
                if q.exists() and q.parent != p.parent and b.sha256_file(q) != h:
                    conflicts.append({"file": rel, "root_a": str(p), "root_b": str(q)})
            files[rel] = {"sha256": h, "root": str(p.parent.parent), "kind": "capture", "capture": c["id"]}
        slots[c["id"]] = iso(b.slot_time(k, spec))
    if conflicts:
        return {"error": "a sealed directory exists in two roots with different bytes: LT13 seal refused", "conflicts": conflicts[:50], "n_conflicts": len(conflicts)}
    miss = [iso(b.slot_time(k, spec)) for k in range(win["captures"][0], win["captures"][1] + 1) if k not in caps_k]
    unavail = sorted(b.load_unavailable(unavailable)) if unavailable else []
    return {"purpose": "LT13 census inputs (LIVE_TESTS_13.md section 6): every capture the census may open, each hashed; counts-only use; CH252 withdrawn_pre_census, no feed capture sealed",
            "written_utc": iso(b.now_ts()), "spec_sha256": spec.get("_sha256"), "design_text_sha256": t.DESIGN_TEXT_SHA256, "declaration_sha256": t.declaration_sha256(),
            "spec_blocks_sha256": t.spec_blocks_sha(spec), "batch_join_code_sha256": t.batch_join_sha(), "code_sha256": t.code_hashes(), "imported_sha256": t.imported_hashes(),
            "k_block": spec["k_block"], "span": spec["census_inputs"]["span"], "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"],
            "windows": {k_: [v_[0], v_[1]] for k_, v_ in win.items()}, "slots": dict(sorted(slots.items())), "feeds": {}, "needs": {"captures": len(caps_k), "feeds": 0},
            "span_slots": len(lt12._span_slots(spec)), "missing": {"captures": miss}, "n_missing": {"captures": len(miss)}, "unavailable_declared": unavail,
            "n_files": len(files), "files": dict(sorted(files.items()))}


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = [{"what": d, "value": s_, "error": "at or after the sealed bound"} for d, s_ in (seal.get("slots") or {}).items() if epoch(s_) >= bound]
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def sealed_slot_map(seal: dict, spec: dict) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {}
    for d in b.sealed_dirs(seal, "snapshots"):
        k = b.slot_of(epoch(seal["slots"][d]), spec) if d in seal.get("slots", {}) else None
        if k is not None:
            out.setdefault(k, set()).add(d)
    return out


def seal_coverage(seal: dict, spec: dict) -> dict:
    """6: the minimum covered days, from the seal manifest BEFORE any row is read: a covered origin is a span slot whose capture and the capture of the slot before it are both sealed with rows,
    sidecar and manifest; a covered twin origin also has the captures of slots k + 2 and k + 3. ``ok`` needs >= 7.0 covered days and >= 5.0 covered twin days."""
    full = set()
    for d, rels in b.sealed_dirs(seal, "snapshots").items():
        names = {r.rsplit("/", 1)[1] for r in rels}
        if {"rows.csv.gz", "rows_ext.csv.gz", "manifest.json"} <= names and d in seal.get("slots", {}):
            k = b.slot_of(epoch(seal["slots"][d]), spec)
            if k is not None:
                full.add(k)
    span = lt12._span_slots(spec)
    org = [k for k in span if k in full and (k - 1) in full]
    twin = [k for k in org if (k + 2) in full and (k + 3) in full]
    mins = spec["census_inputs"]["min_covered_days"]
    cd, td = len(org) / 12.0, len(twin) / 12.0
    return {"covered_origins": len(org), "covered_days": cd, "twin_origins": len(twin), "twin_days": td, "min_covered_days": mins["CC13"], "min_twin_days": mins["CC13_twins"],
            "ok": bool(cd >= mins["CC13"] and td >= mins["CC13_twins"]), "origins": org}


def _load_for_census(seal: Path, snapshot_root, work: Path, spec: dict, verify: bool, design_path, ledger_path, blocks) -> dict:
    """The refusals every census runs first (6, "what the census code must refuse"), in order: a forbidden block; the design text and the ledger freeze hash; the seal's design hash; the batch-join
    code sha256 pinned in the seal and equal to the code's; the imported-file pins; the scope of the spec's four lists; the sealed bound; the seal-time spec blocks; the reward rule and the
    header pre-check; no feed file in the seal (CH252); an empty work dir; then every sealed capture present locally with every file hash-equal (an unsealed or altered input refuses)."""
    t.check_blocks(blocks)
    seal_d = json.loads(Path(seal).read_text())
    if (derr := t.design_text_error(design_path, ledger_path)):
        return derr
    if seal_d.get("design_text_sha256") != t.DESIGN_TEXT_SHA256:
        return {"error": "the seal was written against a different LIVE_TESTS_13.md (its design-text sha256 is not the ledger's freeze hash): census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
    pinned = seal_d.get("batch_join_code_sha256")
    if not pinned:
        return {"error": "the seal does not pin the batch join's code sha256: census refused (6)"}
    if pinned != t.batch_join_sha():
        return {"error": "the batch join's code sha256 differs from the one pinned in the seal: census refused", "pinned": pinned, "code": t.batch_join_sha()}
    if (ierr := imported_error()):
        return ierr
    if seal_d.get("code_sha256") != t.code_hashes():
        return {"error": "the LT13 code files differ from those at seal time (code_sha256): census refused", "seal": seal_d.get("code_sha256"), "code": t.code_hashes()}
    if seal_d.get("imported_sha256") != t.imported_hashes():
        return {"error": "the imported helper files differ from those at seal time: census refused"}
    if (serr := t.scope_error(spec)):
        return serr
    if (viol := bound_violations(seal_d, spec)):
        return {"error": "sealed bound violated: census refused", "bad": viol[:20]}
    if seal_d.get("spec_blocks_sha256") != t.spec_blocks_sha(spec):
        return {"error": "the spec's blocks differ from those at seal time: census refused", "seal_blocks_sha256": seal_d.get("spec_blocks_sha256"), "spec_blocks_sha256": t.spec_blocks_sha(spec)}
    for chk in (t.reward_rule_error, t.k_block_error):
        if (err := chk(spec)):
            return err
    if seal_d.get("feeds") or any(v.get("kind") == "feed" for v in (seal_d.get("files") or {}).values()):
        return {"error": "the seal holds a CLOB reward-feed capture: CH252 is withdrawn_pre_census and no feed file is read by the LT13 census: refused"}
    w = Path(work)
    if w.exists() and any(w.iterdir()):
        return {"error": f"work directory {w} is not empty: a stale series file would be reused (census refused)"}
    by_slot, _ = b._scan(w, snapshot_root, [], spec)
    sc = sealed_slot_map(seal_d, spec)
    bad = []
    for k, names in sorted(sc.items()):
        cc = by_slot.get(k)
        if cc is None:
            bad.append({"slot": k, "sealed": sorted(names), "error": "sealed capture is absent from every root"})
        elif cc["id"] not in names:
            bad.append({"slot": k, "sealed": sorted(names), "scanned": cc["id"], "error": "the scanned capture differs from the sealed one"})
    by_slot = {k: v for k, v in by_slot.items() if k in sc and v["id"] in sc[k]}  # only sealed captures are ever opened
    files_checked = 0
    if verify and sc:
        comp = b.seal_completeness(seal_d, by_slot, {}, set(sc), set(), spec, None)
        bad += comp["bad"]
        files_checked = comp["files_checked"]
    if bad:
        return {"error": "input identity check failed (an input is not named in the seal with an equal sha256): census refused", "bad": bad[:50], "n_bad": len(bad)}
    return {"seal": seal_d, "by_slot": by_slot, "files_checked": files_checked}


# --- the data pass -----------------------------------------------------------------------------------------------------------------------------


def class_changes(ser_k: pd.DataFrame, ser_p: pd.DataFrame) -> dict:
    """1.13 / 6 print: markets (two-sided at k - 1 and k) whose fee class (the vendored ``fee_class``), verbatim ``fee_category`` or sports class changed between k - 1 and k."""
    idx = ser_k.index.intersection(ser_p.index)
    if not len(idx):
        return {"n_common": 0, "fee_class_changed": 0, "category_changed": 0, "sports_changed": 0}
    a, p = ser_k.loc[idx], ser_p.loc[idx]
    ca = np.array([t.cat_verbatim(v) for v in a["fee_cat"].to_numpy(object)], dtype=object)
    cp = np.array([t.cat_verbatim(v) for v in p["fee_cat"].to_numpy(object)], dtype=object)
    return {"n_common": int(len(idx)), "fee_class_changed": int((a["fclass"].astype(str).to_numpy() != p["fclass"].astype(str).to_numpy()).sum()),
            "category_changed": int((ca != cp).sum()), "sports_changed": int((a["sports"].to_numpy(float) != p["sports"].to_numpy(float)).sum())}


def census_units(*, seal: Path, snapshot_root, work: Path, spec: dict | None = None, verify: bool = True, design_path=None, ledger_path=None, blocks=("CH253",), commit: str = "unknown") -> dict:
    """The data pass of CC13 (6): the refusals, the coverage check (FIRST: if it fails nothing else runs and no row is opened) and ONE streaming pass over the sealed captures in time order
    (registry updated capture by capture, causal), building the units of every covered origin, then the twin state through the lag-slot loader. Counts only: no own target is read."""
    spec = spec or t.load_spec()
    work = Path(work)
    loaded = _load_for_census(seal, snapshot_root, work, spec, verify, design_path, ledger_path, blocks)
    if "error" in loaded:
        return loaded
    cov = seal_coverage(loaded["seal"], spec)
    head = {"span": spec["census_inputs"]["span"], "inputs_verified": bool(verify), "files_checked": loaded["files_checked"], "design_text_sha256": t.DESIGN_TEXT_SHA256,
            "declaration_sha256": t.declaration_sha256(), "spec_blocks_sha256": t.spec_blocks_sha(spec), "batch_join_code_sha256": t.batch_join_sha(), "code_sha256": t.code_hashes(),
            "imported_sha256": t.imported_hashes(), "reward_null_rule": spec.get("reward_null_rule"), "k_block": spec.get("k_block"),
            "coverage": {k_: v_ for k_, v_ in cov.items() if k_ != "origins"}}
    if not cov["ok"]:  # BEFORE any gate block is built and before a row is opened
        return {"unavailable": {**head, "statuses": {"CH253": CENSUS_UNAVAILABLE}, "CH253": {"status": CENSUS_UNAVAILABLE, "covered_days": cov["covered_days"], "twin_days": cov["twin_days"]}}}
    by_slot = loaded["by_slot"]
    ORG = sorted(cov["origins"])
    org_set = set(ORG)
    store = t.SlotStore13(work, by_slot, spec, cache_slots=30)
    reg = t.Registry()
    parts: list[pd.DataFrame] = []
    tot: dict = {}
    cells, qual, fee_counts = Counter(), Counter(), {}
    gap_mk, gap_slot, gap_val, changes, per_cap = [], [], [], [], {}
    prev_key = None
    renamed = {"markets": 0, "batch_keys": set()}
    for k in sorted(s_ for s_ in by_slot if s_ <= ORG[-1]):
        cap = by_slot[k]
        store.limit = None
        t.write_series13(work, cap, spec)
        reg.add(t.read_reg13(work, cap["id"]))
        ser = store.ser(k)
        if ser is not None:
            b._fee_counts(ser, fee_counts)
        if k not in org_set:
            continue
        bt_k = reg.batches()
        keys_k = pd.Series(np.array(bt_k.key, dtype=object)[bt_k.bid], index=pd.Index(bt_k.ids)) if len(bt_k.ids) else pd.Series(dtype=object)
        if prev_key is not None and len(keys_k):  # A5: a batch renamed because an earlier-created member joined the chain
            old = prev_key.reindex(keys_k.index)
            ch = old.notna() & (old != keys_k)
            renamed["markets"] += int(ch.sum())
            renamed["batch_keys"] |= set(old[ch].unique())
        prev_key = keys_k
        u, cnt = t.units13(store, bt_k, k, spec, commit=commit)
        ex = cnt.pop("_extras", {})
        store.limit = k
        changes.append({"slot": k, "slot_utc": iso(b.slot_time(k, spec)), **class_changes(store.ser(k), store.ser(k - 1))})
        store.limit = None
        b._merge_counts(tot, cnt)
        per_cap[k] = int(cnt.get("units_primary", 0))
        cells.update(ex.get("elig", {}).get("cells", {}))
        qual.update(ex.get("qual_all", {}).get("cells", {}))
        if len(u):
            prim = u["arm"] == "primary"
            tw = np.full(len(u), np.nan)
            if (k + 2) in by_slot and (k + 3) in by_slot and prim.any():
                tw[prim.to_numpy()] = t.lag_twin_state(by_slot[k + 2]["dir"], by_slot[k + 3]["dir"], u[prim], ex.get("batches", {}), spec)  # the ONLY later-slot read: one number per unit
            u["mbar_tw"] = tw
            parts.append(u)
        gm, gv = ex.get("gaps", (np.zeros(0, object), np.zeros(0)))
        if len(gm):
            gap_mk.append(np.asarray(gm, dtype=object))
            gap_val.append(np.asarray(gv, float))
            gap_slot.append(np.full(len(gm), k, int))
    if store.reads and max(store.reads) > ORG[-1]:
        raise Refused("causality: the unit builders read a slot after the last origin")
    bt = reg.batches()
    return {"head": head, "cov": cov, "by_slot": by_slot, "ORG": ORG, "parts": parts, "tot": tot, "cells": dict(cells), "qual": dict(qual), "fee_counts": fee_counts, "changes": changes,
            "per_cap": per_cap, "gaps": (np.concatenate(gap_mk) if gap_mk else np.zeros(0, object), np.concatenate(gap_slot) if gap_slot else np.zeros(0, int), np.concatenate(gap_val) if gap_val else np.zeros(0)),
            "registry": {"batch_renames": {"markets": renamed["markets"], "old_keys": len(renamed["batch_keys"])}, "markets": int(len(reg)), "batches": int(len(bt.start)), "size_hist": _size_hist(bt.size), "cross_event_batches_ge3": int(bt.cross.sum()),
                         "cross_event_share_of_batches_ge3": float(bt.cross.sum() / max(int((bt.size >= 3).sum()), 1))}}


def _size_hist(size: np.ndarray) -> dict:
    edges = [(1, 1), (2, 2), (3, 5), (6, 10), (11, 30), (31, 100), (101, 10**9)]
    return {f"{lo}-{hi}" if hi < 10**9 else f"{lo}+": int(((size >= lo) & (size <= hi)).sum()) for lo, hi in edges}


# --- gates and prints (6, the CH253 row) --------------------------------------------------------------------------------------------------------


def _adapt(df: pd.DataFrame) -> pd.DataFrame:
    """LT12's statistics cluster and demean by ``event_id`` x UTC day; for CH253 the cluster and the demeaning stratum are the BATCH (1.7). The adapter is the only place the two meet:
    ``event_id`` := ``batch_id`` (the real event key stays in ``ekey``). Stage A ambiguity A2."""
    return df.assign(event_id=df["batch_id"].astype(str))


def identification(T: pd.DataFrame, g: dict) -> dict:
    """6 (LT12's form, R1 MUST 4): (i) the share of units in batch x UTC-day strata where the RAW ``mbar`` is non-zero on >= 3 units; (ii) the share of the sum of squared demeaned ``zs_bt``
    held by the top 1% of units (ceil, at least one) and by the largest single batch."""
    if T.empty:
        return {"nonzero_share": float("nan"), "top_share": float("nan"), "batch_share_max": float("nan")}
    st = T["batch_id"].astype(str) + "|" + T["day"].astype(str)
    nz = (np.abs(T["mbar"].to_numpy(float)) > EPS).astype(int)
    per = pd.Series(nz, index=T.index).groupby(st.to_numpy()).transform("sum").to_numpy()
    nonzero_share = float((per >= int(g["ident_nonzero_min"])).mean())
    A = _adapt(T)
    dm = lt12.strict_expanding_demean(lt12.stratum_codes(A), A["slot"].to_numpy(float), A["zs"].to_numpy(float))
    ok = np.isfinite(dm)
    v2 = dm[ok] ** 2
    tot = float(v2.sum())
    if tot <= 0 or not ok.any():
        return {"nonzero_share": nonzero_share, "top_share": float("nan"), "batch_share_max": float("nan"), "n_demeaned": int(ok.sum())}
    ntop = max(1, math.ceil(float(g["leverage_top_frac"]) * len(v2) - 1e-9))
    top_share = float(np.sort(v2)[::-1][:ntop].sum() / tot)
    bs = pd.Series(v2).groupby(T["batch_id"].astype(str).to_numpy()[ok]).sum() / tot
    return {"nonzero_share": nonzero_share, "top_share": top_share, "top_units": ntop, "batch_share_max": float(bs.max()), "n_demeaned": int(ok.sum())}


def same_slot(T: pd.DataFrame, g: dict) -> dict:
    """6: among batches with >= 24 units, the share with within-batch ``|corr(own innovation, mbar)| >= 0.8`` (an undefined correlation is counted apart and left out of the share, as LT12 A17)."""
    n = T.groupby("batch_id").size()
    big = n[n >= int(g["same_slot_min_units"])].index
    vals, undef = [], 0
    for e in big:
        d = T[T["batch_id"] == e]
        if d["own_ds_c"].std() > 0 and d["mbar"].std() > 0:
            vals.append(abs(float(np.corrcoef(d["own_ds_c"], d["mbar"])[0, 1])))
        else:
            undef += 1
    v = np.asarray(vals)
    return {"batches": int(len(big)), "defined": int(len(v)), "undefined": undef, "share": float((v >= float(g["same_slot_abs_corr"]) - 1e-12).mean()) if len(v) else float("nan"),
            "abs_corr_quantiles": b._q(v, (0.1, 0.5, 0.9))}


def _by_cells(df: pd.DataFrame, cols: list[str]) -> dict:
    if df.empty:
        return {}
    return {"|".join(map(str, k_ if isinstance(k_, tuple) else (k_,))): int(v) for k_, v in df.groupby(cols).size().items()}


def census_ch253(U: pd.DataFrame, cu: dict, spec: dict) -> dict:
    """CH253's gates (6, last row) after the coverage check has passed. Every NaN fails. ``U`` = every unit line (arms ``primary`` and ``gt30``)."""
    g, a = spec["census_gates"]["CH253"], b.mde_common(spec)
    cd, td = cu["cov"]["covered_days"], cu["cov"]["twin_days"]
    scale, scale_f = lt12._scale(cd), lt12._scale(td)
    tot, ORG = cu["tot"], cu["ORG"]
    n_elig = tot.get("eligible_registered", 0) + tot.get("elig_unregistered", 0)
    coverage = tot.get("elig_in_cross_batch", 0) / n_elig if n_elig else float("nan")
    completeness = tot.get("bc_complete", 0) / tot["bc_members"] if tot.get("bc_members") else float("nan")
    res: dict = {"covered_days": cd, "twin_days": td, "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}, "coverage_cross_event_batch": coverage,
                 "batch_completeness_pooled": completeness, "batch_members_absent_share_of_members": (tot.get("bc_members_absent", 0) / tot["bc_members"]) if tot.get("bc_members") else float("nan"),
                 "batch_members_absent_share_of_incomplete": (tot.get("bc_members_absent", 0) / (tot["bc_members"] - tot["bc_complete"])) if tot.get("bc_members", 0) > tot.get("bc_complete", 0) else float("nan"), "registry": cu["registry"]}
    T0 = U[U["arm"] == "primary"] if len(U) else U
    if T0.empty:
        res["gate_CH253"] = {"batch_join_pinned": True, "units": False, "pass": False, "no_units": True}
        res["status"] = CENSUS_DROPPED
        return res
    T1, excl, top = b._fam(T0.assign(skey=T0["fam"]), a["family_cap"])
    T = T1.copy().reset_index(drop=True)
    s_bt = float(np.std(T["mbar"].to_numpy(float), ddof=0))
    ok_s = np.isfinite(s_bt) and s_bt > 0
    T["zs"] = T["mbar"].to_numpy(float) / s_bt if ok_s else np.nan
    T["zs_pb"] = T["mbar_pb"].to_numpy(float) / s_bt if ok_s else np.nan
    T["zs_tw"] = T["mbar_tw"].to_numpy(float) / s_bt if ok_s else np.nan
    T["thin_x_zs"] = T["thin"].to_numpy(float) * T["zs"].to_numpy(float)
    A = _adapt(T)
    dm = lt12.strict_expanding_demean(lt12.stratum_codes(A), A["slot"].to_numpy(float), A["zs"].to_numpy(float))
    s_w = float(np.std(dm[np.isfinite(dm)], ddof=0)) if np.isfinite(dm).any() else float("nan")
    t1, t2, gap = b.terciles(T["zs"])
    xo, xm = T["own_ds_c"].to_numpy(float), T["mbar"].to_numpy(float)
    rho = float(np.corrcoef(xo, xm)[0, 1]) if (np.std(xo) > 0 and np.std(xm) > 0) else float("nan")
    gm, gs, gv = cu["gaps"]
    keep_u = set(zip(T["market_id"].astype(str), T["slot"].astype(int), strict=True))
    sel = np.fromiter(((m_, s_) in keep_u for m_, s_ in zip(gm.astype(str), gs, strict=True)), dtype=bool, count=len(gm)) if len(gm) else np.zeros(0, bool)
    gq = lt12.span_summary(gv[sel])
    A, fc_names, fc_levels = t.fee_cat_dummies(A)
    controls = t.controls13(A, fc_names, spec)
    de = b._de(A, scale, g["de_floor"], a)
    nb_units = T.groupby("batch_id").size()
    n_batches, n_ge48 = int(nb_units.size), int((nb_units >= g["events_min_units"]).sum())
    ge = lt12.g_eff(T["batch_id"])
    ss = same_slot(T, g)
    ident = identification(T, g)
    vif_gate = lt12.design_ss12(A, "zs", ["cbar", "own_ds_c"])
    corr_x = {x: lt12.wcorr12(A, "zs", x) for x in ("log1p_liq", "log_rv24s", "d")}
    zz = A[np.abs(A["zs"].to_numpy(float)) >= float(g["venue_clock_abs_z"])]
    clock = lt12._slot_share(zz) if len(zz) else float("nan")
    bshare = lt12.block_share12(A, int(g["block_min_captures"]))
    pl_cov = float(np.isfinite(T["zs_pb"].to_numpy(float)).mean())
    # the aliased-controls rule (3.3) on the demeaned controls WITHOUT zs_bt; the MDE gates use the resolved control set
    Dm = lt12.demeaned_frame(A, ["zs", *controls])
    rank = t.resolve_aliased_controls(Dm, "zs", controls, fc_levels)
    kept = rank["keep"] if rank["status"] == "ok" else None
    if kept is not None:
        sm = lt12.slope_mde12(A, "zs", kept, scale, a, de["DE_gate"], a[g["sd"]], gap, s_w)
        F = A[(A["f_end_ok"] == 1) & np.isfinite(A["zs_tw"].to_numpy(float))]
        rg = lt12.r_gate12(F, "zs", "zs_tw")
        fm = lt12.f_mde_gate(sm["mde_c"], rg["r_gate"], lt12.f_design_c(F, "zs", "zs_tw", kept, scale_f, a, a[g["sd"]], gap))
    else:
        sm = {"mde_c": float("inf"), "declared_c": float("inf"), "design_c": float("inf"), "note": f"controls unavailable: {rank.get('reason')}"}
        F = A[(A["f_end_ok"] == 1) & np.isfinite(A["zs_tw"].to_numpy(float))]
        rg = lt12.r_gate12(F, "zs", "zs_tw")
        fm = {"f_mde_c": float("inf"), "declared_c": float("inf"), "design_c": float("inf"), "r_gate": rg["r_gate"]}
    proj = float(len(T) * scale)
    pc = pd.Series([cu["per_cap"].get(k, 0) for k in ORG], dtype=float)
    age = T["batch_age_days"].to_numpy(float)
    ph = T.groupby("age_decile").apply(lambda d: int((~np.isfinite(d["zs_pb"].to_numpy(float))).sum()), include_groups=False) if len(T) else pd.Series(dtype=int)
    n_all = len(U)
    res.update({
        "units_primary": int(len(T0)), "units_after_family_exclusion": int(len(T)), "units_projected_21d": proj, "units_per_capture": {"median": float(pc.median()), "mean": float(pc.mean()), "min": float(pc.min()), "n_captures": int(len(pc))},
        "batches_with_unit_unprojected": n_batches, "batches_ge48_units_unprojected": n_ge48, "g_eff_batch": ge, "same_slot": ss, "identification": ident, "vif_w_gate": vif_gate, "corr_x": corr_x,
        "venue_clock": clock, "block_share": bshare, "placebo_coverage": pl_cov, "r_gate": rg, "slope": sm, "F": fm, "design_effect": de, "exclude_family": excl, "top_family_share": top,
        "controls_rank": {k_: v_ for k_, v_ in rank.items()}, "fee_dummies": fc_names, "twin_units": int(len(F)),
        "census_prints": {
            "batch_size_distribution_registry": cu["registry"]["size_hist"], "cross_event_share": cu["registry"]["cross_event_share_of_batches_ge3"],
            "batch_incomplete_units": int(tot.get("batch_incomplete_units", 0)), "batch_incomplete_batch_captures": int(tot.get("bc_incomplete_batches", 0)), "receipt_span_units": int(tot.get("receipt_span_units", 0)),
            "mates_lt2_units": int(tot.get("mates_lt2_units", 0)), "placebo_none": int(tot.get("placebo_none", 0)), "placebo_none_by_age_decile": {str(int(k_)): int(v_) for k_, v_ in ph.items()},
            "units_by_batch_age_days": {"le7": int((age <= 7).sum()), "gt7": int((age > 7).sum()), "genesis_share": float((age <= 7).mean()) if len(age) else float("nan")},
            "gt30_arm_units": int(tot.get("gt30_units", 0)), "gt30_arm_units_registry_mates_reading": int(tot.get("gt30_units_registry_mates", 0)), "sports_arm_units": int(tot.get("sports_arm_units", 0)),
            "sports_mate_share": float(T["n_sports_mates"].sum() / T["n_mates"].sum()) if T["n_mates"].sum() else float("nan"),
            "units_by_fee_type_x_fee_category": _by_cells(T, ["fee_type", "cat"]), "pseudo_candidates_by_fee_type_x_fee_category": dict(sorted(cu["cells"].items())),
            "placebo_none_by_fee_type_x_fee_category": _by_cells(T[~np.isfinite(T["zs_pb"].to_numpy(float))], ["fee_type", "cat"]),
            "units_by_fee_type_x_sports_slug": _by_cells(T, ["fee_type", "slug_sports"]), "rows_by_fee_type_x_sports_slug_x_sports_class": dict(sorted(cu["qual"].items())),
            "fee_class_and_category_changes_per_capture": cu["changes"], "fee_class_unknown_units": int(tot.get("fee_class_unknown", 0)), "sidecar_missing": int(tot.get("sidecar_missing", 0)), "series_not_registered": int(tot.get("series_not_registered", 0)),
            "arms_total_unit_lines": int(n_all)},
    })
    gate = {"batch_join_pinned": True, "coverage": bool(np.isfinite(coverage) and coverage >= g["coverage_min"]), "completeness": bool(np.isfinite(completeness) and completeness >= g["completeness_min"]),
            "units_projected": bool(proj >= g["units_projected_min"]), "batches_with_unit": n_batches >= g["batches_with_unit_min"], "batches_ge48": n_ge48 >= g["batches_ge48_min"],
            "g_eff": bool(np.isfinite(ge) and ge >= a["g_eff_min"]), "same_slot": bool(np.isfinite(ss["share"]) and ss["share"] <= g["same_slot_share_max"]),
            "ident_nonzero": bool(np.isfinite(ident["nonzero_share"]) and ident["nonzero_share"] >= g["ident_share_min"]),
            "ident_top1": bool(np.isfinite(ident["top_share"]) and ident["top_share"] <= g["leverage_top_share_max"]),
            "ident_batch": bool(np.isfinite(ident["batch_share_max"]) and ident["batch_share_max"] <= g["leverage_batch_share_max"]),
            "vif_w": bool(np.isfinite(vif_gate["vif_w"]) and vif_gate["vif_w"] <= g["vif_w_max"]), **{f"corr_zs_{x}": b.corr_ok(c_, g["corr_max"], both=True) for x, c_ in corr_x.items()},
            "placebo_coverage": bool(np.isfinite(pl_cov) and pl_cov >= g["placebo_coverage_min"]), "block_share": bool(np.isfinite(bshare) and bshare >= g["block_share_min"]),
            "venue_clock": bool(np.isfinite(clock) and clock <= g["venue_clock_max"]), "r_gate": bool(np.isfinite(rg["r_gate"]) and rg["r_gate"] <= g["r_gate_max"]),
            "slope_mde": bool(sm["mde_c"] <= a["mde_max_c"]["CH253"]), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max_c"]["CH253"])}
    res["gate_CH253"] = b._gate(gate)
    res["status"] = CENSUS_PASS if res["gate_CH253"]["pass"] else CENSUS_DROPPED
    q50, q90 = gq.get("q50"), gq.get("q90")
    res["census_fixed"] = {"s_bt": s_bt, "s_w": s_w, "zs_cuts": [t1, t2], "zs_gap": gap, "rgap_q50_s": q50, "rgap_q50_s_floored_5s": (max(q50, 5.0) if q50 is not None else None), "rgap_q90_s": q90,
                           "rho_census": rho if np.isfinite(rho) else None, "rho_census_nan": bool(not np.isfinite(rho)), "exclude_family": excl}
    res["receipt_gap_distribution"] = gq
    res["census_gate_values"] = {"mde_c": sm["mde_c"]}
    return res


def census_gates(cu: dict, spec: dict) -> dict:
    head = cu["head"]
    fs = b.crypto_failsafe(cu["fee_counts"])
    lists = {"k_tests": [], "dropped_tests": [], "census_unavailable": [], "withdrawn_pre_census": ["CH252"]}
    if not fs["classifier_shown_to_work"]:
        return {**head, "error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    U = pd.concat(cu["parts"], ignore_index=True) if cu["parts"] else pd.DataFrame()
    blk = census_ch253(U, cu, spec)
    lists["k_tests" if blk["status"] == CENSUS_PASS else "dropped_tests"].append("CH253")
    return {**head, "scope": "CH253 only; CH252 is withdrawn_pre_census (fee reading unresolved) and is never built", "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": True,
            "covered_origins": len(cu["ORG"]), "expected_origins": spec["census_inputs"]["expected_origins"].get("CC13"), "CH253": blk, "statuses": {"CH253": blk["status"]}, "lists": lists,
            "withdrawn_pre_census": dict(t.WITHDRAWN), "census_fixed_CH252": "withdrawn_pre_census: support_cells, M_on, panel shares and spread quantiles are not computed"}


def census_captures(*, seal: Path, snapshot_root, work: Path, spec: dict | None = None, verify: bool = True, design_path=None, ledger_path=None, blocks=("CH253",), commit: str = "unknown") -> dict:
    """CC13 (6): the CH253 gate block on the sealed captures (counts only). The coverage check is evaluated FIRST: if it fails, NO row is opened, no gate is computed or printed, and the test
    is ``census_unavailable (coverage)`` (distinct from ``census_dropped``) with the four lists and nothing else."""
    spec = spec or t.load_spec()
    cu = census_units(seal=seal, snapshot_root=snapshot_root, work=work, spec=spec, verify=verify, design_path=design_path, ledger_path=ledger_path, blocks=blocks, commit=commit)
    if "error" in cu:
        return cu
    if "unavailable" in cu:
        return {**cu["unavailable"], "lists": {"k_tests": [], "dropped_tests": [], "census_unavailable": ["CH253"], "withdrawn_pre_census": ["CH252"]}, "withdrawn_pre_census": dict(t.WITHDRAWN)}
    return bd._clean(census_gates(cu, spec))


# --- write-once (6: "a second run") --------------------------------------------------------------------------------------------------------------


def run_marker(seal: Path) -> Path:
    return Path(str(seal) + ".census_ran")


def claim_run(seal: Path, out: Path | None, payload: dict) -> str | None:
    """The census runs ONCE: an existing marker beside the seal, or an existing ``out``, refuses. The marker is created atomically (O_EXCL) when the result is about to be written, so a crash
    before any output (``max_retries 1``) does not burn the run. Returns an error text or None."""
    m = run_marker(seal)
    if m.exists():
        return f"the LT13 census already ran on this seal ({m}): a second run is refused (6, write-once)"
    if out is not None and Path(out).exists():
        return f"refusing to overwrite {out}"
    try:
        fd = os.open(m, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as e:  # pragma: no cover - race
        if e.errno == errno.EEXIST:
            return f"the LT13 census already ran on this seal ({m}): a second run is refused"
        raise
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps({"ran_utc": iso(b.now_ts()), **payload}, sort_keys=True))
    return None


def header_precheck(*, capture_dir: Path | None = None, spec: dict | None = None) -> dict:
    """6: the header pre-check (headers only, NO rows): which of 1.2's row and sidecar fields one capture carries (``created_at``, ``fees_enabled``, ``fee_schedule``, ``series_slugs``,
    ``event_ids``, ``liquidity``, ``clob_rewards`` included) and whether ``chg_1d`` / ``chg_1w`` exist (they fix K's columns, 1.7). Committed before the seal."""
    return lt12.header_precheck(capture_dir=capture_dir, feed_dir=None, spec=spec or t.load_spec())
