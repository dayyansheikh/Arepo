# ruff: noqa: E501
"""CB17-C window code (docs/research_lab/CREATIVE_BATCH_17.md section CB17-C; rules part ``C`` = ``cb17_rules_c``): event-interval units, the k + 1 mark reader, the census block,
C1 (mint share), its replication and the econ line.

Frame (q0406 SCREEN_8 arm 0; q0410 REP_8 arm 1): (event, interval k) units. ELIGIBILITY, the class, the strata and C_pre use captures k - 2, k - 1 and k only (finding 1); the trailing
tercile cut points use the event's EARLIER traded intervals inside the read window only (finding 6). Capture k + 1 (and k + 2 for the 4 h robustness) is read for each member's
availability status only (capture missing, member closed, one-sided, wide, extreme mid) in the frame; the screen reads the k + 1 values from the raw captures and the REP frame seals them.
"""

from __future__ import annotations

import math
import time
from collections import Counter, deque
from pathlib import Path

import numpy as np

from . import cb13_t as t13
from . import cb17_census as cen
from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_rules_c as rc
from . import cb17_wcommon as w
from . import cb17_win as win

Refused = c17.Refused

UNITS_NAME = "c_units.npz"
MEMBERS_NAME = "c_members.npz"
META_NAME = "c_meta.json.gz"
MARKS_NAME = "c_marks.npz"
CLS_CODE = {rc.CLASS_TRANSFER: 0, rc.CLASS_MINT: 1, rc.CLASS_MERGE: 2}
CLS_NAME = {v: k for k, v in CLS_CODE.items()}
REASON_CODE = {None: 0, "capture missing": 1, "member closed": 2, "one-sided": 3, "wide": 4, "extreme mid": 5}
REASON_NAME = {v: (k or "ok") for k, v in REASON_CODE.items()}
CAP_ROWS = ("market_id", "closed", "best_bid", "best_ask", "end_date", "liquidity")
CAP_EXT = ("market_id", "event_id", "fee_type", "fee_category", "series_slugs", "neg_risk_market_id", "event_open_interest", "event_volume")
U_F64 = ("T", "T1", "r", "dv", "r_lag")
U_F32 = ("abs_dm", "c_pre", "spread", "log_liq")
U_I8 = ("cls", "dv_t", "dv_above", "n_moving", "cls_lag", "cls_ww", "single", "negrisk", "doi_zero", "k1_ok", "k2_ok")
U_I32 = ("ev", "path", "cap", "cap1", "cap2")
M_COLS = {"unit": np.int32, "mkt": np.int32, "dm": np.float32, "m_k": np.float64, "st1": np.int8, "st2": np.int8}


def load_capture(cdir: Path) -> dict:
    """One capture: T (last page received_utc), quotes {market: (bid, ask)}, closed set, end {market}, liquidity {market}, events {event: [oi, vol, members, sports, neg_risk, slug]}."""
    q: dict[str, tuple[float, float]] = {}
    closed: set[str] = set()
    end: dict[str, float] = {}
    liq: dict[str, float] = {}
    t_max = -math.inf
    for mk, cl, bid, ask, ed, lq, t in win.iter_rows(Path(cdir) / "rows.csv.gz", CAP_ROWS, c17.CAPTURE_FIELDS, "received_utc"):
        t_max = max(t_max, t)
        q[mk] = (c17.num(bid), c17.num(ask))
        if cen.is_true(cl):
            closed.add(mk)
        if ed:
            end[mk] = cen.ep_cached(ed)
        liq[mk] = c17.num(lq)
    ev: dict[str, list] = {}
    for mk, e, ft, fc, ss, nrm, oi, vol, t in win.iter_rows(Path(cdir) / "rows_ext.csv.gz", CAP_EXT, c17.SIDECAR_FIELDS, "received_utc"):
        t_max = max(t_max, t)
        if not e:
            continue
        rec = ev.get(e)
        if rec is None:
            rec = ev[e] = [c17.num(oi), c17.num(vol), [], False, False, cen.lab.first_series_slug(ss) or ""]
        rec[2].append(mk)
        rec[3] = rec[3] or cen.is_sports_sidecar(ft, fc, ss)
        rec[4] = rec[4] or bool(nrm)
    mids = {mk: rc.member_mid(b, a) for mk, (b, a) in q.items()}
    return {"T": t_max, "q": q, "mid": mids, "closed": closed, "end": end, "liq": liq, "ev": ev}


def _row(state: dict, mk: str) -> dict | None:
    if mk not in state["q"]:
        return None
    b, a = state["q"][mk]
    return {"bid": b, "ask": a, "closed": mk in state["closed"]}


def build_frame(snap_root: Path, *, units: tuple[float, float], read_lo: float, marks_hi: float, arm: int, drops: dict[str, str] | None = None, budget_s: float | None = None,
                clock=time.monotonic) -> dict:
    """Stream the complete captures in time order (three states in memory). Units at capture k use k - 2, k - 1, k; the k + 1 / k + 2 statuses are filled when those captures arrive."""
    t0 = clock()
    stats: Counter = Counter()
    excl: Counter = Counter()
    drops = drops or {}
    floor = c17.ep(c17.LOOKBACK_FLOOR)
    caps = win.list_captures(snap_root, read_lo, marks_hi, stats)
    V = {k: win.Vocab() for k in ("ev", "path", "mkt")}
    U: dict[str, list] = {k: [] for k in (*U_F64, *U_F32, *U_I8, *U_I32)}
    M: dict[str, list] = {k: [] for k in M_COLS}
    members_of: list[list[int]] = []
    hist: dict[str, list[tuple[float, float, float]]] = {}
    allr: dict[str, list[tuple[int, float]]] = {}
    gcu: Counter = Counter()
    states: deque = deque(maxlen=3)  # (capture index, state)
    pend1: list[int] = []
    pend2: list[int] = []
    cap_list = []
    for j, cap in enumerate(caps):
        if budget_s is not None and clock() - t0 > budget_s:
            raise c17.NotNow(f"C frame unfinished after {j} of {len(caps)} captures (budget); the job repeats from the start of the stage (pending)")
        cur = load_capture(cap["dir"])
        if not cur["ev"] and not cur["q"]:
            stats["captures_empty"] += 1
            continue
        cap_list.append({"i": len(cap_list), "id": cap["capture_id"], "T": cur["T"]})
        ci = len(cap_list) - 1
        prv = states[-1][1] if states else None
        gap_ok = prv is not None and rc.interval_ok(cur["T"] - prv["T"])
        # ---- k + 2 statuses (units made two captures ago; needs k + 1 consecutive and this capture consecutive to it) ----
        for u in pend2:
            ok2 = bool(U["k1_ok"][u]) and gap_ok
            U["k2_ok"][u] = int(ok2)
            U["cap2"][u] = ci if ok2 else -1
            for mi in members_of[u]:
                M["st2"][mi] = REASON_CODE[rc.mark_reason(ok2, _row(cur, V["mkt"].items[M["mkt"][mi]]))]
        # ---- k + 1 statuses (units made at the previous capture) ----
        for u in pend1:
            U["k1_ok"][u] = int(gap_ok)
            U["cap1"][u] = ci if gap_ok else -1
            U["T1"][u] = cur["T"] if gap_ok else math.nan
            for mi in members_of[u]:
                M["st1"][mi] = REASON_CODE[rc.mark_reason(gap_ok, _row(cur, V["mkt"].items[M["mkt"][mi]]))]
        pend2, pend1 = pend1, []
        # ---- intervals ending at this capture ----
        if prv is None or not gap_ok:
            if prv is None or cur["T"] - pre.CAP_GAP_S[1] < floor:
                stats["interval_unavailable_lookback_floor_or_first"] += 1
            else:
                stats["interval_gap_outside_100_140min"] += 1
            states.append((ci, cur))
            continue
        pre2 = states[-2][1] if len(states) >= 2 and rc.interval_ok(prv["T"] - states[-2][1]["T"]) else None
        in_units = units[0] <= cur["T"] < units[1]
        for e, (oi1, v1, members, sports, nr, slug) in cur["ev"].items():
            r0 = prv["ev"].get(e)
            if sports:
                stats["sports_event_intervals"] += 1
                continue
            if r0 is None:
                continue
            oi0, v0 = r0[0], r0[1]
            st = rc.r_state(oi0, oi1, v0, v1)
            evk = w.event_key(e, members[0] if members else "")
            is_arm = w.arm(evk) == arm
            if st is None:
                if in_units and is_arm:
                    excl["OI or volume missing" if not all(math.isfinite(x) for x in (oi0, oi1, v0, v1)) else "not traded (dV <= 0)"] += 1
                continue
            r, dv = st
            rl = math.nan
            if pre2 is not None and e in pre2["ev"]:
                rl = rc.r_lag(oi0, oi1, pre2["ev"][e][1], v0)
            prior = list(hist.get(e, ()))  # a COPY before this interval is added: r_k never enters its own cut points
            hist.setdefault(e, []).append((r, dv, rl))
            allr.setdefault(e, []).append((ci, r))
            if not (in_units and is_arm):
                continue
            gcu["traded"] += 1
            gcu["oi_changed"] += oi1 != oi0
            if win.in_night_span(cur["T"], pre.CAP_GAP_S[1]):
                excl["election night"] += 1
                continue
            if any(win.key_drop(drops, m, evk) for m in members):
                excl["dropped: key"] += 1
                continue
            if any(m in prv["closed"] or m in cur["closed"] for m in members):
                excl["member closed at k-1 or k"] += 1
                continue
            if any(cur["end"].get(m, math.inf) <= cur["T"] + pre.MEMBER_END_BUFFER_S for m in members):
                excl["member closing within 3 h of k"] += 1
                continue
            moves = rc.qualifying_moves(members, prv["mid"], cur["mid"])
            if not moves:
                excl["no qualifying member"] += 1
                continue
            cls = rc.classify(r, [p[0] for p in prior])
            tdv = pre.trailing_dv([p[1] for p in prior], dv)
            if cls is None or tdv is None:
                excl["thin history"] += 1
                continue
            cpre = []
            if pre2 is not None:
                for m, dm in moves:
                    a, b = pre2["mid"].get(m, math.nan), prv["mid"].get(m, math.nan)
                    if math.isfinite(a) and math.isfinite(b):
                        cpre.append((1.0 if dm > 0 else -1.0) * 100.0 * (b - a))
            lag_prior = [p[2] for p in prior if math.isfinite(p[2])]
            cls_lag = rc.classify(rl, lag_prior) if math.isfinite(rl) else None
            sps = [cur["q"][m][1] - cur["q"][m][0] for m, _ in moves]
            lq = [cur["liq"].get(m, math.nan) for m in members]
            lq = [x for x in lq if math.isfinite(x)]
            u = len(U["ev"])
            vals = {"ev": V["ev"].code(evk), "path": V["path"].code(w.path_key(slug, evk)), "cap": ci, "cap1": -1, "cap2": -1, "T": cur["T"], "T1": math.nan, "r": r, "dv": dv, "r_lag": rl,
                    "abs_dm": float(np.mean([abs(dm) for _, dm in moves])), "c_pre": float(np.mean(cpre)) if cpre else math.nan, "spread": float(np.mean(sps)),
                    "log_liq": math.log(max(sum(lq), 1.0)) if lq else math.nan, "cls": CLS_CODE[cls], "dv_t": tdv[0], "dv_above": tdv[1], "n_moving": min(len(moves), 100),
                    "cls_lag": CLS_CODE[cls_lag] if cls_lag else -1, "cls_ww": -1, "single": int(len(members) == 1), "negrisk": int(bool(nr)), "doi_zero": int(oi1 == oi0), "k1_ok": 0, "k2_ok": 0}
            for k, v in vals.items():
                U[k].append(v)
            mis = []
            for m, dm in moves:
                M["unit"].append(u)
                M["mkt"].append(V["mkt"].code(m))
                M["dm"].append(dm)
                M["m_k"].append(cur["mid"][m])
                M["st1"].append(REASON_CODE["capture missing"])
                M["st2"].append(REASON_CODE["capture missing"])
                mis.append(len(M["unit"]) - 1)
            members_of.append(mis)
            pend1.append(u)
        states.append((ci, cur))
    # ---- whole-window terciles leaving intervals k and k + 1 out (a binding robustness; features only) ----
    evn = V["ev"].items
    for u in range(len(U["ev"])):
        e_items = allr.get(_raw_event(evn[U["ev"][u]]), [])
        k = U["cap"][u]
        vals = [rr for (cc, rr) in e_items if cc not in (k, k + 1)]
        ww = rc.whole_window_class(U["r"][u], vals)
        U["cls_ww"][u] = CLS_CODE[ww] if ww else -1
    units_a = {k: np.asarray(v, dtype=np.float64 if k in U_F64 else np.float32 if k in U_F32 else np.int8 if k in U_I8 else np.int32) for k, v in U.items()}
    mem_a = {k: np.asarray(M[k], dtype=t) for k, t in M_COLS.items()}
    return {"units": units_a, "members": mem_a, "vocab": {k: v.items for k, v in V.items()}, "captures": cap_list, "stats": dict(stats), "exclusions": dict(excl), "gcu": dict(gcu)}


def _raw_event(evk: str) -> str:
    """The event key IS the Gamma event id (else the market id, which then has no event intervals)."""
    return evk


def write_frame(out_dir: Path, fr: dict) -> list[Path]:
    a = win.write_arrays(Path(out_dir) / UNITS_NAME, fr["units"])
    b = win.write_arrays(Path(out_dir) / MEMBERS_NAME, fr["members"])
    c = win.write_json_gz(Path(out_dir) / META_NAME, {k: fr[k] for k in ("vocab", "captures", "stats", "exclusions", "gcu")})
    return [a, b, c]


def load_frame(rdir: Path) -> dict:
    return {"U": win.read_arrays(Path(rdir) / UNITS_NAME), "M": win.read_arrays(Path(rdir) / MEMBERS_NAME), "_meta": win.read_json_gz(Path(rdir) / META_NAME)}


# =====================================================================================================================================================
# mark values (k + 1 and k + 2 member quotes)
# =====================================================================================================================================================


def mark_tables(snap_root: Path, F: dict, *, read_lo: float, marks_hi: float) -> dict[str, np.ndarray]:
    """bid / ask of every member at capture k + 1 (``b1``, ``a1``) and k + 2 (``b2``, ``a2``), read from the raw captures listed in the frame (whitelisted market, bid, ask)."""
    stats: Counter = Counter()
    U, M = F["U"], F["M"]
    caps = {c["capture_id"]: c for c in win.list_captures(snap_root, read_lo, marks_hi, stats)}
    cl = F["_meta"]["captures"]
    mk = F["_meta"]["vocab"]["mkt"]
    n = len(M["unit"])
    out = {k: np.full(n, np.nan) for k in ("b1", "a1", "b2", "a2")}
    need: dict[int, dict[str, list[tuple[str, int]]]] = {}
    for col, capcol in (("1", "cap1"), ("2", "cap2")):
        cu = U[capcol][M["unit"]]
        for mi in np.nonzero(cu >= 0)[0]:
            need.setdefault(int(cu[mi]), {}).setdefault(mk[int(M["mkt"][mi])], []).append((col, int(mi)))
    for ci in sorted(need):
        cid = cl[ci]["id"]
        if cid not in caps:
            raise Refused(f"mark capture {cid} is not in the read window or missing (restore it byte for byte)")
        want = need[ci]
        for m, bid, ask, _t in win.iter_rows(caps[cid]["dir"] / "rows.csv.gz", ("market_id", "best_bid", "best_ask"), c17.CAPTURE_FIELDS, "received_utc"):
            for col, mi in want.get(m, ()):
                out[f"b{col}"][mi], out[f"a{col}"][mi] = c17.num(bid), c17.num(ask)
    return out


# =====================================================================================================================================================
# analysis
# =====================================================================================================================================================


def member_values(F: dict, MV: dict, *, horizon: str = "1") -> np.ndarray:
    """Member continuation ``C_j = sign(dm) x 100 x (m_k+h - m_k)`` where the member's status at that capture is ok, else NaN (rules C ``continuation``)."""
    M = F["M"]
    st = M["st1"] if horizon == "1" else M["st2"]
    b, a = MV[f"b{horizon}"], MV[f"a{horizon}"]
    m1 = (b + a) / 2.0
    dm = M["dm"].astype(float)
    out = np.where((st == 0) & np.isfinite(m1), np.sign(dm) * 100.0 * (m1 - M["m_k"]), np.nan)
    return out


def unit_means(F: dict, cvals: np.ndarray) -> np.ndarray:
    """Unit value = mean over the members with an available mark (NaN when none)."""
    n = len(F["U"]["ev"])
    unit = F["M"]["unit"].astype(np.int64)
    ok = np.isfinite(cvals)
    s = np.bincount(unit[ok], weights=cvals[ok], minlength=n)
    c = np.bincount(unit[ok], minlength=n)
    return np.where(c > 0, s / np.maximum(c, 1), np.nan)


def worst_case_values(F: dict, MV: dict, cvals: np.ndarray) -> np.ndarray:
    """Binding worst case (rules C ``worst_member``): every unavailable member at the bound adverse to the hypothesis (transfer p5, mint / merge p95 of the available member C), or the
    one-sided k + 1 touch adverse to continuation where more adverse; unit value = mean over ALL qualifying members."""
    U, M = F["U"], F["M"]
    avail = cvals[np.isfinite(cvals)]
    out = np.array(cvals, copy=True)
    unit = M["unit"].astype(np.int64)
    for mi in np.nonzero(~np.isfinite(cvals))[0]:
        cls = CLS_NAME[int(U["cls"][unit[mi]])]
        one = math.nan
        if int(M["st1"][mi]) == REASON_CODE["one-sided"]:
            one = rc.onesided_adverse(float(M["dm"][mi]), float(M["m_k"][mi]), {"bid": MV["b1"][mi], "ask": MV["a1"][mi]})
        out[mi] = rc.worst_member(cls, avail, one)
    n = len(U["ev"])
    ok = np.isfinite(out)
    s = np.bincount(unit[ok], weights=out[ok], minlength=n)
    c = np.bincount(unit[ok], minlength=n)
    return np.where(c > 0, s / np.maximum(c, 1), np.nan)


def dataset(F: dict) -> dict:
    U = F["U"]
    D = dict(U)
    return win.set_ways(D, U["ev"], U["path"], U["T"])


def x_of(cls: np.ndarray) -> np.ndarray:
    """[transfer, merge] indicators (mint-heavy baseline)."""
    c = np.asarray(cls)
    return np.column_stack([(c == 0).astype(float), (c == 2).astype(float)])


def census(F: dict) -> dict:
    """GCU, GC, GCP (SE only), the informativeness share at level 2 (three-class rule), unavailable-mark shares by class and reason, exclusions."""
    U, M, meta = F["U"], F["M"], F["_meta"]
    g = meta["gcu"]
    gcu = rc.gate_gcu(int(g.get("oi_changed", 0)), int(g.get("traded", 0)))
    gc = rc.gate_gc(len(set(U["ev"].tolist())), int(len(U["ev"])))
    D = dataset(F)
    i = np.nonzero(np.isfinite(U["c_pre"]))[0]
    se = pre.fe_cluster_se(U["c_pre"][i].astype(float).tolist(), x_of(U["cls"][i]).tolist(), U["ev"][i].tolist(), {k: D[f"way_{k}"][i].tolist() for k in w.WAYS}, coef=0) if len(i) else {"n": 0, "se": None}
    info = pre.informativeness("C", (((int(U["ev"][k]), (pre.abs_dm_2band(float(U["abs_dm"][k])),)), CLS_NAME[int(U["cls"][k])]) for k in range(len(U["ev"]))))
    un: dict[str, dict] = {}
    unit = M["unit"].astype(np.int64)
    for code, name in CLS_NAME.items():
        sel = U["cls"][unit] == code
        un[name] = {"members_by_reason": {REASON_NAME[r]: int(((M["st1"] == r) & sel).sum()) for r in REASON_NAME},
                    "units": int((U["cls"] == code).sum()), "units_with_an_available_member": int(len(set(unit[sel & (M["st1"] == 0)].tolist())))}
    return {"units": int(len(U["ev"])), "events": len(set(U["ev"].tolist())), "gates": {"GCU": gcu, "GC": gc, "GCP": w.power_gate(se.get("se"))}, "planning_se": {"C1_C_pre": se},
            "informativeness": {"C": {"level": rc.STRATA_LEVEL_C, **info}, "window_rule": w.INFORMATIVE_MIN}, "unavailable_mark": un,
            "classes": {CLS_NAME[k]: int((U["cls"] == k).sum()) for k in CLS_NAME}, "exclusions": meta["exclusions"], "stats": meta["stats"], "captures": len(meta["captures"])}


def _keep_sign(make_v, idx: np.ndarray) -> bool | None:
    if len(idx) < 3:
        return None
    e = win.est_only(make_v, idx)
    return bool(math.isfinite(e) and e > 0)


def c1_test(F: dict, MV: dict, census_c: dict | None, *, n_draws: int = w.PLACEBO_DRAWS, rep: bool = False) -> dict:
    """C1: ``beta_C`` = coefficient on ``transfer`` in an event-FE OLS of the 2 h continuation on the transfer and merge indicators (mint-heavy baseline), one-sided > 0, floor +0.5c."""
    U = F["U"]
    D = dataset(F)
    labels = [w.LABEL_REP if rep else w.LABEL_SCREEN]
    if census_c is not None:
        gates = census_c["gates"]
        if not gates["GCU"]["pass"]:
            return win.not_testable(w.NOT_TESTABLE_FIELD, labels=labels)
        if not gates["GC"]["pass"]:
            return win.not_testable(w.NOT_TESTABLE_POP, labels=labels)
        if not rep and not gates["GCP"]["run"]:
            return win.not_testable(w.NOT_RUN_POWER, labels=labels, power=gates["GCP"])
    cv = member_values(F, MV)
    y = unit_means(F, cv)
    n = len(U["ev"])
    av = w.availability(int(np.isfinite(y).sum()), n)
    info = {"availability": av, "rep": rep, "labels": labels}
    if not av["ok"]:
        return {**win.not_testable(w.NOT_TESTABLE_AVAIL), **info}
    cls = U["cls"].astype(np.int64)
    ev = U["ev"].astype(np.int64)
    X = x_of(cls)
    idx = np.nonzero(np.isfinite(y))[0]
    mk = win.make_fe(y, X, ev)
    res = {**win.analyse(mk, idx, D, w.FLOOR_C), **info}
    res["classes"] = {CLS_NAME[k]: int((cls[idx] == k).sum()) for k in CLS_NAME}
    if not res["testable"]:
        res.update(advance=False, checks_ok=False, verdict="not testable (population / clusters)")
        return res
    est = res["est"]
    band = np.array([pre.abs_dm_2band(float(a)) for a in U["abs_dm"]], dtype=np.int64)
    comp = win.composition_guard(D, idx, y, cls, x_of, ev, band, est, family="C", info_units=(((int(ev[i]), (int(band[i]),)), CLS_NAME[int(cls[i])]) for i in idx),
                                 seed=w.SEEDS["C1_composition"], n_draws=n_draws)
    res["composition_guard"] = comp
    res["calibration_placebo"] = {**win.calibration(D, idx, y, cls, x_of, ev, U["T"], seed=w.SEEDS["C1_calibration"], n_draws=n_draws),
                                  "note": "C1 calibration: class circularly shifted within event over its intervals"}
    ip = np.nonzero(np.isfinite(U["c_pre"]))[0]
    pp = win.p_of(win.make_fe(U["c_pre"].astype(float), X, ev), ip, D, alpha=w.GATE_P)
    res["pre_interval_placebo"] = {"p": pp["p"], "n": pp["n"], "holds": bool((not pp["testable"]) or pp["p"] >= w.GATE_P)}
    cpre = U["c_pre"].astype(float)
    cov = [np.nan_to_num(cpre, nan=0.0), (~np.isfinite(cpre)).astype(float), U["spread"].astype(float), np.nan_to_num(U["log_liq"].astype(float), nan=0.0),
           (~np.isfinite(U["log_liq"])).astype(float), U["n_moving"].astype(float)]
    names = ["C_pre", "C_pre_missing", "mean_member_spread", "log_event_liquidity", "liquidity_missing", "moving_members"]
    for arr, nm in ((np.array([pre.abs_dm_band(float(a)) for a in U["abs_dm"]]), "abs_dm_band"), (U["dv_t"], "dv_tercile"), (np.array([c17.band6(float(t)) for t in U["T"]]), "utc6")):
        c, n_ = win.dummies(arr, nm)
        cov += c
        names += n_
    res["attribution"] = win.attribution(y, X, cov, names, ev, idx, est, credit="mint share", debit="composition, not mint share")
    rob: dict[str, bool | None] = {}
    yw = worst_case_values(F, MV, cv)
    rob["unavailable_mark_worst_case"] = _keep_sign(win.make_fe(yw, X, ev), np.nonzero(np.isfinite(yw))[0])
    il = np.nonzero(np.isfinite(y) & (U["cls_lag"] >= 0))[0]
    rob["oi_lag_variant"] = _keep_sign(win.make_fe(y, x_of(U["cls_lag"].astype(np.int64)), ev), il)
    iw = np.nonzero(np.isfinite(y) & (U["cls_ww"] >= 0))[0]
    rob["whole_window_terciles_leave_k_k1_out"] = _keep_sign(win.make_fe(y, x_of(U["cls_ww"].astype(np.int64)), ev), iw)
    rob["single_market_events"] = _keep_sign(mk, idx[U["single"][idx] == 1])
    rob["non_neg_risk_events"] = _keep_sign(mk, idx[U["negrisk"][idx] == 0])
    c4 = unit_means(F, member_values(F, MV, horizon="2"))
    rob["continuation_4h"] = _keep_sign(win.make_fe(c4, X, ev), np.nonzero(np.isfinite(c4))[0])
    q99 = float(np.quantile(U["dv"][idx], 1.0 - rc.TOP_DV_EXCLUDE_SHARE)) if len(idx) else math.inf
    rob["exclude_top_1pct_dv"] = _keep_sign(mk, idx[U["dv"][idx] <= q99])
    res["robustness"] = rob
    res["robust_ok"] = bool(all(v for v in rob.values() if v is not None) and rob["unavailable_mark_worst_case"] is not None and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["small_g_rules_hold"] and comp["holds"] and res["calibration_placebo"]["holds"] and res["pre_interval_placebo"]["holds"] and res["robust_ok"])
    res["advance"] = w.stage1_advance(res["p"] if res["testable"] else None, res["checks_ok"])
    rep_ = {"merge_minus_mint": win.est_only(win.make_fe(y, X, ev, j=1), idx)}
    s0 = idx[(U["r"][idx] >= 0)]
    rep_["sign_only_doi_zero_minus_positive"] = win.est_only(win.make_fe(y, U["doi_zero"].astype(float), ev), s0)
    rep_["neg_risk_events_alone"] = win.est_only(mk, idx[U["negrisk"][idx] == 1])
    res["reported"] = rep_
    if not comp["informative"]:
        labels.append(w.UNINFORMATIVE)
    res["labels"] = labels
    res["verdict"] = ("advance" if res["advance"] else "no advance") + (f"; {res['attribution']['label']}" if res["advance"] else "")
    return res


def c1_econ_classes(fills: list[dict], F: dict) -> list[str | None]:
    """Per fill: the class of the event's classified interval k with tau in (capture k, capture k + 1] (None when no such interval)."""
    U = F["U"]
    evn = F["_meta"]["vocab"]["ev"]
    by: dict[str, list[tuple[float, float, int]]] = {}
    for u in range(len(U["ev"])):
        if math.isfinite(U["T1"][u]):
            by.setdefault(evn[int(U["ev"][u])], []).append((float(U["T"][u]), float(U["T1"][u]), int(U["cls"][u])))
    out = []
    for f in fills:
        hit = None
        for a, b, c in by.get(w.event_key(f.get("event_id"), f.get("market_id")), ()):
            if a < float(f["tau"]) <= b:
                hit = CLS_NAME[c]
                break
        out.append(hit)
    return out


def declared() -> dict:
    return {"units": UNITS_NAME, "members": MEMBERS_NAME, "meta": META_NAME, "marks": MARKS_NAME, "classes": {str(v): k for k, v in CLS_CODE.items()},
            "reasons": {str(k): v for k, v in REASON_NAME.items()}, "t13_two_sided": t13.two_sided.__name__}
