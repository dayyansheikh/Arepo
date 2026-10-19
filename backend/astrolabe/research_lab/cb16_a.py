# ruff: noqa: E501
"""CB16 part A orchestration (docs/research_lab/CREATIVE_BATCH_16.md sections 3, 4, 5): the Q and U frames, census, Stage 1 screen and Stage 2 on host files, NO network.

Jobs (the runner calls these): q0382 ``grain_census`` (CB13-T SCREEN raw files through the pinned CB13 readers, features only, no mark), q0384 / q0387 ``frame_a`` (SCREEN_A / REP_A
fill tables, features only; REP_A also the raw mark-quote table, event-disjoint from SCREEN_A, sha256-sealed), q0385 ``census_a`` (counts only; gates GQ, GU, GQP, GUP), q0386
``screen_a`` (Q1 and U1; GAI; batch Holm k1 = 2), q0388 ``rep_a`` (Q1-rep, Q2, U1-rep, U2; pooled GAI; early alpha / 4). Q and U share units and mark-outs: one fill table, one
analysis dataset.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb13_common as c13
from . import cb13_t as t13
from . import cb16_common as c16
from . import cb16_q as q
from . import cb16_u as u

Refused = cm.Refused
NotNow = cm.NotNow

FRAME_STATUS = {"screen": "a_frame_complete", "rep": "a_rep_complete"}
FRAME_PROGRESS = {"screen": "a_frame_progress", "rep": "a_rep_progress"}
FRAME_DIRS = {"screen": "a_screen", "rep": "a_rep"}
LABEL_AUDIT_UNAUDITED = q.LABEL_UNAUDITED
GAI_CAND_WINDOW_S = t13.GTI_WINDOW_S
STAGE_TESTS = {"Q": ("Q1",), "U": ("U1",)}
SCREEN_MARK_TAIL_S = c16.MARK_TAIL_S


def mark_rows16(fills: list[dict], qi: q.QuoteIndex16) -> list[list]:
    """The raw mark-quote table (REP_A seal): bid, ask and the capture tick at each mark capture of each filled transaction and horizon, NO mark-out."""
    rows = []
    for f in fills:
        if f["status"] != q.S_FILL:
            continue
        for h, hs in q.MARK_H.items():
            mk = qi.mark_for(f, hs)
            rows.append([f["tx_id"], h, mk["status"], q._fmt(mk["recv"]), q._fmt(mk["bid"]), q._fmt(mk["ask"]), q._fmt(qi.tick_for(f, hs))])
    return rows


def tx_hash_index(trades_dir: Path, lo: float, hi: float) -> dict[tuple[str, float], str]:
    """In-memory only: ``(condition_id, ts) -> tx16`` of the window's prints (U2's receipt-lag join; the hash is never stored)."""
    out: dict[tuple[str, float], str] = {}
    for f in q.trade_files(trades_dir, lo, hi):
        for p in q.iter_prints(f, lo, hi):
            if p.get("tx16"):
                out.setdefault((p["condition_id"], p["ts"]), p["tx16"])
    return out


def wake_lags(trades_dir: Path, rows: list[dict], lo: float, hi: float) -> dict:
    """U2's actual-receipt-lag robustness input (rep frame only): ``recv_ts - ts`` of the wake-up transactions. ``recv_ts`` is read for nothing else and never written."""
    idx = tx_hash_index(trades_dir, lo, hi)
    wanted = {(r["condition_id"], idx[(r["condition_id"], r["tau"])]) for r in rows if r.get("wake") == 1 and (r["condition_id"], r["tau"]) in idx}
    lags: dict[tuple[str, str], float] = {}
    for f in q.trade_files(trades_dir, lo, hi):
        for cid, tx, lag in q.iter_recv_lag(f, lo, hi, wanted):
            lags.setdefault((cid, tx), lag)
    n = u.attach_wake_lags(rows, idx, lags)
    return {"wake_rows": sum(1 for r in rows if r.get("wake") == 1), "with_lag": n}


def frame_a(window: str, *, s_a: float, trades_dir: Path, snap_root: Path, sweep_root: Path | None, hist_root: Path, out_dir: Path, screen_events: set[str] | None = None,
            budget_s: float | None = None) -> tuple[dict, list[Path]]:
    """q0384 (window 'screen') / q0387 (window 'rep'): transactions of the window, the touch-mode quote index (NO mark accessor), exclusion keys (resumable, budgeted), the fill table with
    the silence state and the reported shape, features only. REP_A additionally drops every Gamma event with a SCREEN_A fill (binding even if thinned), reads the wake-up receipt lags and
    writes the raw mark-quote table (a SECOND, mark-mode index over the rep captures: bid, ask and tick at the mark captures; no mark-out). Returns (report, output files)."""
    if window not in ("screen", "rep"):
        raise Refused(f"unknown A window {window!r}")
    rep = window == "rep"
    if rep and screen_events is None:
        raise Refused("the REP_A frame needs the SCREEN_A fill events (event-disjointness binds even if thinned)")
    W = c16.windows(s_a)[window]
    ulo, uhi = W["units"]
    plo, _phi = W["prints"]
    clo, chi = W["captures"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    txs, tinfo = q.window_transactions(trades_dir, ulo, uhi, s_a, rep_open=rep)
    caps = q.list_captures(snap_root, clo, uhi)
    wanted = {t["condition_id"] for t in txs}
    qi = q.load_quote_index(caps, wanted, "touch")
    kstate = out_dir / q.KEYS_PARTIAL_NAME
    keys, krep = q.a_exclusion_keys(hist_root, [(ulo, uhi)], state_path=kstate, budget_s=budget_s)
    rows, counts = q.make_fills(txs, qi, keys)
    by_cid, all_ts, tl = q.timeline(trades_dir, plo, uhi)
    sil = u.add_silence(rows, by_cid, all_ts)
    sweeps = q.load_sweeps(sweep_root, {r["token0"] for r in rows if q.is_primary(r) and r["token0"]}, max(ulo - q.SWEEP_MAX_AGE_S, c16.ep(c16.LOOKBACK_FLOOR)), uhi)
    shape = q.add_shape(rows, sweeps)
    drep = None
    lag = None
    if rep:
        rows, drep = q.drop_screen_events(rows, screen_events or set())
        lag = wake_lags(trades_dir, rows, ulo, uhi)
    files = [q.write_fills(out_dir / q.FILLS_NAME, rows)]
    from . import history_backfill as hb  # noqa: PLC0415

    kp = out_dir / q.KEYS_NAME
    kp.write_bytes(hb._gz_csv_bytes(["key", "source"], sorted([k, s] for k, s in keys.items())))
    files.append(kp)
    if rep:
        mcaps = q.list_captures(snap_root, clo, chi)
        mqi = q.load_quote_index(mcaps, {r["condition_id"] for r in rows if r["status"] == q.S_FILL}, "mark", boundary_epoch=chi)
        mp = out_dir / q.MARKS_NAME
        mp.write_bytes(hb._gz_csv_bytes(q.MARK_COLUMNS, mark_rows16([r for r in rows if r["status"] == q.S_FILL], mqi)))
        files.append(mp)
    kstate.unlink(missing_ok=True)
    report = {"window": window, "units_window": [c16.iso(ulo), c16.iso(uhi)], "transactions": tinfo, "timeline": tl, "captures_used": len(caps), "status_counts": counts,
              "silence": sil, "key_drop_report": krep, "shape": shape, "rep_drop": drep, "wake_lags": lag,
              "n_fills": sum(1 for r in rows if r["status"] == q.S_FILL), "primary_fills": sum(1 for r in rows if q.is_primary(r))}
    return report, files


# =====================================================================================================================================================
# q0382: the grain census on CB13-T's SCREEN window (features only)
# =====================================================================================================================================================


def timeline_from_prints(prints: list[dict]) -> tuple[dict[str, np.ndarray], np.ndarray]:
    first: dict[tuple, float] = {}
    n = 0
    for p in prints:
        key = (p["tx16"], p["condition_id"]) if p.get("tx16") else (f"single:{n}", p["condition_id"])
        n += 1
        first[key] = min(first.get(key, math.inf), p["ts"])
    by: dict[str, list[float]] = {}
    for (_, cid), t in first.items():
        by.setdefault(cid, []).append(t)
    return {k: np.array(sorted(v)) for k, v in by.items()}, np.array(sorted(p["ts"] for p in prints))


def grain_census(trades_dir: Path, snap_root: Path, pin: dict) -> dict:
    """q0382 (counts only, features only): CB13-T's SCREEN window ``[10-12, 10-16)`` read from the raw files through CB13's own guarded readers and the pinned fill functions. No mark
    quote is opened (touch-mode index; the mark-capture tick is not read). GQG, the grain shares by touch tick and P band, and the count of silences >= 12 h the >= 5 prior-gap rule would
    drop (comparison with G1b's 459 + 127 >= 12 h gaps outside sports; lookback inside the SCREEN window only)."""
    prints, pinfo = t13.screen_prints(Path(trades_dir), "screen", pin)
    txs, _ = t13.build_transactions(prints)
    caps = c13.list_captures(Path(snap_root), "screen", pin)
    wanted = {t["condition_id"] for t in txs}
    qi = q.load_quote_index(caps, wanted, "touch", guard=lambda t: t)
    rows, counts = q.make_fills(txs, qi, None)
    by_cid, all_ts = timeline_from_prints(prints)
    sil = u.add_silence(rows, by_cid, all_ts, floor=0.0)
    gq = q.gate_gqg(rows)
    fs = [r for r in rows if q.is_primary(r)]
    return {"counts_only": True, "window": pinfo["window"], "n_prints": pinfo["n_prints"], "status_counts": counts, "gqg": gq, "silence": sil,
            "tick_by_primary_status": {k: dict(Counter(f"{r['tick_touch']}" for r in fs if r["status"] == k)) for k in {r["status"] for r in fs}},
            "dropped_long_silences": u.silence_dropped_counts(rows), "g1b_reference_ge_12h_outside_sports": {"enriched": 459, "unenriched": 127}, "pass": gq["pass"],
            "note": "lookback limited to the SCREEN window itself (before 2026-10-12 does not exist on the stream); features only; no mark quote opened"}


# =====================================================================================================================================================
# q0385: census (counts only)
# =====================================================================================================================================================


def gai_candidates(rows: list[dict]) -> dict:
    """GAI pair candidates (features only): primary fills with a later transaction of the same market in ``[tau + 2 h - 30 min, tau + 2 h + 30 min]``. The sign agreement needs the mark and is
    computed at the screen."""
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["condition_id"], []).append(r["tau"])
    for v in by.values():
        v.sort()
    n = 0
    for r in rows:
        if not q.is_primary(r):
            continue
        lo, hi = r["tau"] + 7200.0 - GAI_CAND_WINDOW_S, r["tau"] + 7200.0 + GAI_CAND_WINDOW_S
        ts = by.get(r["condition_id"], [])
        n += int(any(lo <= t <= hi for t in ts))
    return {"candidate_pairs": n, "min_pairs": q.GAI_MIN_PAIRS}


def census_a(rows: list[dict], *, window_label: str = "SCREEN_A") -> dict:
    """q0385, counts only: units by label (inside, inconsistent, one-sided, no row, censored, genesis, election night, single-grain markets, key drops by source); exclusion rates by grain
    and by x tercile; dropped >= 12 h silences; the politics share; gates GQ and GU (features); power gates GQP and GUP on the pre-fill proxy (clustered SEs and MDEs only: no proxy point
    estimate is written); the GAI pair-candidate count."""
    primary = [r for r in rows if q.is_primary(r)]
    sports = [r for r in rows if q.is_sports_arm(r)]
    out: dict = {"window": window_label, "counts_only": True, "n_transactions": len(rows), "n_primary_fills": len(primary), "n_sports_fills": len(sports)}
    out["status_counts"] = dict(Counter(r["status"] if not r["status"].startswith(t13.S_KEY) else t13.S_KEY for r in rows))
    out["key_drops_by_source"] = dict(Counter(r["status"][len(t13.S_KEY):].strip() for r in rows if r["status"].startswith(t13.S_KEY)))
    out["election_night_excluded"] = sum(1 for r in rows if r["status"] == q.S_ELECTION)
    out["fills_by_class"] = dict(Counter(r["label"] for r in rows if r["status"] == q.S_FILL))
    out["silence_status_primary_fills"] = dict(Counter(r["silence_status"] for r in primary))
    out["grain"] = {"eligible_fills": sum(1 for r in primary if int(r["grain_ok"]) == 1), "bot": sum(1 for r in primary if int(r["grain_ok"]) == 1 and int(r["g"]) == 1),
                    "human": sum(1 for r in primary if int(r["grain_ok"]) == 1 and int(r["g"]) == 0), "both_grain_markets": len(q.both_grain_markets(rows)),
                    "single_grain_markets": len({r["condition_id"] for r in primary if int(r["grain_ok"]) == 1}) - len(q.both_grain_markets(rows))}
    out["exclusion_by_grain"] = q.exclusion_by_grain(rows)
    out["exclusion_by_x_tercile"] = u.exclusion_by_x(rows)
    out["dropped_long_silences"] = u.silence_dropped_counts(rows)
    out["politics_share"] = (sum(int(r["politics"]) for r in primary) / len(primary)) if primary else None
    out["gq"] = q.q_gate_gq(rows)
    out["gu"] = u.u_gate_gu(rows)
    out["gqp"] = q.q_power(rows)
    out["gup"] = u.u_power(rows)
    out["gai_candidates"] = gai_candidates(rows)
    out["units"] = {"q_fills": out["gq"]["fills"], "u_units": out["gu"]["units"]}
    return out


# =====================================================================================================================================================
# q0386: Stage 1 (Q1, U1)
# =====================================================================================================================================================


def labeller_label(audit_path: Path | None, labeller_sha: str | None) -> str | None:
    """'labeller unaudited' if CB13-T's GL audit is absent or failed (Q and U still use the SPORTS-FEED class only)."""
    if audit_path is None or not labeller_sha:
        return LABEL_AUDIT_UNAUDITED
    gl = t13.gate_gl(audit_path, labeller_sha)
    return None if gl.get("pass") else LABEL_AUDIT_UNAUDITED


def gate_result(label: str) -> dict:
    return {**q.not_testable(label), "checks_ok": False}


def screen_a(fills: list[dict], txs: list[dict], qi, census: dict, *, terminals: dict[str, dict | None] | None = None, audit_label: str | None = None,
             n_draws: int = c16.PLACEBO_DRAWS) -> dict:
    """Stage 1. Q1 and U1 on the SCREEN_A dataset (mark-mode index). A counted terminal (smoke, GQG) or a failed gate yields the declared label with p = 1 (still counted by the runner). The
    batch Holm (k1 = 2, fixed) is information: a p < 0.01 always passes its first step 0.025."""
    terminals = terminals or {}
    D = q.build_dataset(fills, qi)
    gai = q.gate_gai(fills, D, txs)
    labels_common = [q.LABEL_A]
    if audit_label:
        labels_common.append(audit_label)
    if not gai.get("evaluable"):
        labels_common.append(t13.LABEL_CADENCE)
    cadence_fail = bool(gai.get("evaluable") and not gai.get("pass"))
    out: dict = {"gai": gai, "labels": labels_common, "n_dataset": int(len(D["tx_id"]))}
    gq, gqp, gu, gup = census["gq"], census["gqp"], census["gu"], census["gup"]
    if terminals.get("Q"):
        out["Q1"] = gate_result(terminals["Q"]["label"])
    elif not gq["pass"]:
        out["Q1"] = gate_result(q.NOT_TESTABLE_POP)
    elif not gqp.get("pass"):
        out["Q1"] = gate_result(q.NOT_RUN_POWER)
    elif cadence_fail:
        out["Q1"] = gate_result(q.NOT_TESTABLE_CADENCE)
    else:
        out["Q1"] = q.q1_test(D, n_draws=n_draws)
    if terminals.get("U"):
        out["U1"] = gate_result(terminals["U"]["label"])
    elif not gu["pass"]:
        out["U1"] = gate_result(q.NOT_TESTABLE_POP)
    elif not gup.get("pass"):
        out["U1"] = gate_result(q.NOT_RUN_POWER)
    elif cadence_fail:
        out["U1"] = gate_result(q.NOT_TESTABLE_CADENCE)
    else:
        out["U1"] = u.u1_test(D, n_draws=n_draws)
    out["sd_x"] = out["U1"].get("sd_x") if out["U1"].get("sd_x") is not None else (u.sd_of(D["x"][u.u_units(D)]) if len(D["tx_id"]) else None)
    out["stage1_holm"] = c16.stage1_holm({t: (out[t].get("p") if out[t].get("testable", True) else None) for t in c16.STAGE1_HOLM_FAMILY})
    out["reported"] = {"Q": q.q_reported(D, fills) if len(D["tx_id"]) else {}, "U": u.u_reported(D, fills, sd=out["sd_x"] if out["sd_x"] and math.isfinite(out["sd_x"]) else None) if len(D["tx_id"]) else {}}
    for t in c16.STAGE1_HOLM_FAMILY:
        out[t]["labels"] = [*(out[t].get("labels") or []), *labels_common]
    return out


# =====================================================================================================================================================
# q0388: Stage 2
# =====================================================================================================================================================


def stage2_annotate(res: dict) -> dict:
    """Early alpha / 4 and the all-checks flag; the CB16-wide final Holm (q0392) can only add passes."""
    p = res.get("p") if res.get("testable", True) else None
    res["stage2_early_alpha_ok"] = c16.early_stage2_ok(p)
    res["stage2_pass_alpha_over_k"] = bool(res.get("checks_ok") and res["stage2_early_alpha_ok"])
    return res


def rep_a(fills: list[dict], txs: list[dict], qi, screen: dict, triggered: dict[str, bool], *, drop_label: str | None = None, n_draws: int = c16.PLACEBO_DRAWS,
          terminals: dict[str, dict | None] | None = None) -> dict:
    """Stage 2 on REP_A (the sealed fill and mark-quote tables, ``MarkTable16``): Q1-rep / Q2 iff Q1 advanced, U1-rep / U2 iff U1 advanced. Q1-rep needs the GQ minimums on REP_A and
    U1-rep the GU minimums (else 'not run (power)', counted); Q2 and U2 need the POOLED SCREEN_A + REP_A GAI PASS (< 200 pooled pairs -> 'not testable (cadence)'). U1-rep scales ``x`` by
    SCREEN_A's frozen ``SD(x)`` and refuses to run without it."""
    terminals = terminals or {}
    D = q.build_dataset(fills, qi)
    gai_rep = q.gate_gai(fills, D, txs)
    pooled = q.gai_pooled(screen.get("gai"), gai_rep)
    out: dict = {"labels": [q.LABEL_REP, q.LABEL_RT], "gai_rep": gai_rep, "gai_pooled": pooled, "rep_drop_label": drop_label}
    gq, gu = q.q_gate_gq(fills), u.u_gate_gu(fills)
    out["gq_rep"], out["gu_rep"] = gq, gu
    sd = screen.get("sd_x")
    if triggered.get("Q1"):
        out["Q1"] = gate_result(terminals["Q"]["label"]) if terminals.get("Q") else (q.q1_test(D, n_draws=n_draws, rep=True, x_frozen_sd=sd) if gq["pass"] else gate_result(q.NOT_RUN_POWER))
        cad = gate_result(q.NOT_TESTABLE_CADENCE)
        if not pooled["evaluable"] or not pooled["pass"]:
            out["Q2"] = cad
        elif not gq["pass"]:
            out["Q2"] = gate_result(q.NOT_RUN_POWER)
        else:
            out["Q2"] = q.q2_test(D)
    if triggered.get("U1"):
        out["U1"] = gate_result(terminals["U"]["label"]) if terminals.get("U") else (u.u1_test(D, n_draws=n_draws, rep=True, sd=sd) if gu["pass"] and sd else gate_result(q.NOT_RUN_POWER))
        if not pooled["evaluable"] or not pooled["pass"]:
            out["U2"] = gate_result(q.NOT_TESTABLE_CADENCE)
        elif not gu["pass"]:
            out["U2"] = gate_result(q.NOT_RUN_POWER)
        else:
            out["U2"] = u.u2_test(D, u.wake_index(fills))
    for t in ("Q1", "Q2", "U1", "U2"):
        if t in out:
            stage2_annotate(out[t])
            out[t]["labels"] = [*(out[t].get("labels") or []), *out["labels"]]
    return out


def triggers_of(screen_doc: dict) -> dict[str, bool]:
    return {t: (screen_doc.get(t) or {}).get("advance") is True for t in c16.STAGE1_HOLM_FAMILY}


# =====================================================================================================================================================
# Declaration
# =====================================================================================================================================================


def declared() -> dict:
    return {"jobs": {"q0382": "grain_census (CB13-T SCREEN raw files, features only)", "q0384": "a-frame screen", "q0385": "census", "q0386": "screen", "q0387": "a-frame rep (sealed)", "q0388": "rep"},
            "order": "gates (smoke, GQG, GQ/GU, GQP/GUP, GAI) -> Q1 / U1 -> batch Holm k1 = 2 -> Stage 2 (Q1-rep, Q2, U1-rep, U2) -> CB16-wide final Holm",
            "frame_dirs": dict(FRAME_DIRS), "statuses": {"complete": dict(FRAME_STATUS), "progress": dict(FRAME_PROGRESS)}, "rep_event_disjoint": "binding even if thinned (round 1 item 20)",
            "network": False, "mark_mode": "frames read the touch-mode index (no mark accessor); the screen and rep read the mark-mode index / sealed mark-quote table"}
