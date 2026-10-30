# ruff: noqa: E501
"""CB7-G analysis (docs/research_lab/CREATIVE_BATCH_7.md CB7-G, 2.1-2.6): G1, buying geopolitics YES longshots (0.02-0.10) at the modelled ask at 30 / 14 / 7 days before the
scheduled end and holding to resolution. Single historical stage on ``h8_geo`` (L1); EXPLORATORY: no edge, calibration or profitability claim.

Every function and UPPER_CASE constant here is hashed into the CB7 declaration. Outcomes (``outcomes_guarded.csv.gz``) are opened only through
:class:`cb7_astats.OutcomeGate` (refuses before the declared time) and only after the units (prices, keys, status) are built from non-outcome files.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import cb1_history as c1
from . import cb7_astats as st
from . import cb7_census as cc
from . import cb7_common as cm
from . import cb7_geo as cg
from . import economics, h5_seal
from .history_topics import topic_of

Refused = cm.Refused

TEST = "G1"
JOB = "q0149_cb7_screen_G"
ASK_CAP = 0.999
FLOOR_NET = 0.01  # +1.0c per share (2.4)
FLOOR_RANN = 0.10  # R_ann >= 10% (2.4)
COST_ROBUST = 0.0075  # +0.75c on a (2.6 (i))
TAIL_CONF = 0.99
TAIL_MARGIN = 0.005
MIN_YES_CLUSTERS = 10
TAIL_BOOT = 500
CLOSE_DROP_DAYS = 2.0  # robustness (vii): drop closed_time < end_at - 2 d
MIN_CLUSTERS = {"event_week": 30, "theme": 15}
UNKNOWN_FEE_RATE = 0.07  # unknown or ``other:*`` (2.1)
SAMPLE_COLS = (*cc.G_SAMPLE_COLS, "status")
PRICE_COLS = ("market_id", "k", "origin_ts", "m", "eligible")
RESULT_KEY = "g_analysis"


# ---- cost model (2.1) -------------------------------------------------------------------------------------------------------------------


def fee_rate_g(cat) -> float:
    """``economics.DOCS_CATEGORY_RATE[fee_category]`` under CB1's conservative policy; unknown, empty or ``other:*`` -> 0.07 (CB7 2.1 text; CB1's own prefix rule would
    give 0.05 to ``other:*``, so it is not used)."""
    c = str(cat or "").strip()
    if not c or c == "unknown" or c.startswith("other:"):
        return UNKNOWN_FEE_RATE
    return float(economics.DOCS_CATEGORY_RATE.get(c.split(":")[0], UNKNOWN_FEE_RATE))


def ask_of(m: float, *, shift: float = 0.0, h_floor: float | None = None) -> float:
    """Modelled ask ``a = min(m + half_spread(m) [+ shift], 0.999)``; with ``h_floor`` (robustness ix) ``a = m + max(half_spread(m), h_geo)``."""
    h = c1.half_spread(m)
    if h_floor is not None:
        h = max(h, h_floor)
    return min(m + h + shift, ASK_CAP)


def fee_of(a: float, rate: float) -> float:
    return rate * a * (1.0 - a)


def priced(u: dict, *, shift: float = 0.0, h_floor: float | None = None) -> dict:
    """The unit with ``a``, ``f``, ``K`` (capital a + f) and, when ``y`` is known, ``net = Y - a - f(a)``."""
    a = ask_of(u["m"], shift=shift, h_floor=h_floor)
    f = fee_of(a, u["rate"])
    out = {**u, "a": a, "f": f, "K": a + f}
    if u.get("y") is not None:
        out["net"] = u["y"] - a - f
    return out


def r_ann(units: list[dict]) -> float:
    """``365 * sum(net) / sum(K * max(d, 1))`` with d the hold in days from the origin to the resolution mark (censored excluded)."""
    num = sum(u["net"] for u in units)
    den = sum(u["K"] * max(u["hold_d"], 1.0) for u in units)
    return float(365.0 * num / den) if den > 0 else math.nan


# ---- units ------------------------------------------------------------------------------------------------------------------------------


def yes_payout(raw) -> float | None:
    """Payout of the YES token from the guarded ``outcome_prices`` (1, 0, 0.5) or None."""
    return c1.parse_outcome0(raw)


def build_units(rows: list[dict], prices: list[dict], dropped: set[str]) -> list[dict]:
    """Eligible (market, origin) units from the sealed ``sample.csv.gz`` rows and ``origin_prices.csv.gz`` rows (no outcome field). Markets listed in ``drops.csv.gz``
    are removed. ``status`` here is the market's status at the fetch cap: ``closed`` or ``active`` (censored)."""
    rows = [r for r in rows if r["market_id"] not in dropped]
    by_id = {r["market_id"]: r for r in rows}
    ekey = cc.event_keys(rows)
    out = []
    for p in prices:
        r = by_id.get(p["market_id"])
        if r is None or cc._ci(p["eligible"]) != 1:
            continue
        m, t = cc._f(p["m"]), cc._f(p["origin_ts"])
        end, close = cc._f(r["end_epoch"]), cc._f(r.get("close_epoch"))
        theme = cg.theme_of(r.get("question", ""), r.get("event_title", ""))
        ek = ekey[p["market_id"]]
        out.append({"market_id": p["market_id"], "k": cc._ci(p["k"]), "m": m, "origin_ts": t, "end": end, "close": close, "event": ek,
                    "week": cc.iso_week(end), "ew": f"{ek}|{cc.iso_week(end)}", "theme": theme or f"own:{ek}", "named_theme": theme,
                    "neg_risk": bool(str(r.get("neg_risk_market_id") or "")), "fee_cat": str(r.get("fee_category") or ""), "rate": fee_rate_g(r.get("fee_category")),
                    "tag_topic": topic_of(r.get("question", ""), r.get("event_title", ""), r.get("slug", ""), r.get("fee_category", "")) == "geopolitics",
                    "closed": str(r.get("status", "")) == "closed" and cc._ci(r.get("closed_after_cap")) == 0,
                    "quarter": _quarter(end), "early_close": bool(math.isfinite(close) and close < end - CLOSE_DROP_DAYS * cm.DAY)})
    return out


def _quarter(ts: float) -> str:
    g = time.gmtime(int(ts))
    return f"{g.tm_year}-Q{(g.tm_mon - 1) // 3 + 1}"


def attach_outcomes(units: list[dict], outcomes: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """(resolved units with ``y`` and ``hold_d``, unresolved units). A closed market with a decisive payout is resolved; a market still active at the cap is censored;
    a closed market with a non-decisive or missing payout is undecided. Unresolved units carry ``y`` None and enter the worst case only."""
    res, unres = [], []
    for u in units:
        y = yes_payout(outcomes.get(u["market_id"])) if u["closed"] else None
        if u["closed"] and y is not None:
            res.append({**u, "y": y, "status": "resolved", "hold_d": ((u["close"] - u["origin_ts"]) / cm.DAY) if math.isfinite(u["close"]) else math.nan})
        else:
            unres.append({**u, "y": None, "status": "censored" if not u["closed"] else "undecided"})
    return res, unres


# ---- statistics -------------------------------------------------------------------------------------------------------------------------


def yes_event_clusters(units: list[dict]) -> int:
    return len({u["event"] for u in units if u["y"] == 1.0})


def g1_test(units: list[dict], *, alpha: float | None = None, shift: float = 0.0, h_floor: float | None = None, need_yes: bool = True) -> dict:
    """G1 = mean net per unit, one-sided > 0; p = max over (event x week) and theme. Fewer than 10 YES event clusters -> not testable (p = 1)."""
    pu = [priced(u, shift=shift, h_floor=h_floor) for u in units]
    v = np.array([u["net"] for u in pu])
    t = st.ways_test(v, {"event_week": [u["ew"] for u in pu], "theme": [u["theme"] for u in pu]}, sign=1, min_clusters=MIN_CLUSTERS, alpha=alpha)
    ny = yes_event_clusters(units)
    t["yes_event_clusters"] = ny
    if need_yes and ny < MIN_YES_CLUSTERS:
        t.update(testable=False, p=1.0, reason=[*t.get("reason", []), f"YES event clusters {ny} < {MIN_YES_CLUSTERS}"])
    if pu:
        t["r_ann"] = r_ann([u for u in pu if math.isfinite(u["hold_d"])]) if all("hold_d" in u for u in pu) else None
        t["pi_star"] = float(np.mean([u["K"] for u in pu]))
    return t


def floor_ok(t: dict, floor_net: float = FLOOR_NET) -> bool:
    """Materiality floor (2.4): mean net >= +1.0c per share and R_ann >= 10%."""
    return bool(np.isfinite(t["mean"]) and t["mean"] >= floor_net and t.get("r_ann") is not None and np.isfinite(t["r_ann"]) and t["r_ann"] >= FLOOR_RANN)


def inverted_tail_gate(units: list[dict]) -> dict:
    """Inverted tail gate (binding): pi = share of units whose YES wins (50-50 half); pi* = mean(a + f). The one-sided LOWER 99% bound on pi (Wilson on n / deff,
    deff from the event-cluster bootstrap of the YES share, floored at 1) must exceed pi* + 0.005. Fewer than 10 YES event clusters -> not testable."""
    pu = [priced(u) for u in units]
    n = len(pu)
    if n == 0:
        return {"passes": False, "testable": False, "n": 0, "reason": "no units"}
    y = np.array([u["y"] for u in pu], float)
    pi_hat, pi_star = float(y.mean()), float(np.mean([u["K"] for u in pu]))
    ny = yes_event_clusters(units)
    out = {"n": n, "pi_hat": pi_hat, "pi_star": pi_star, "required": pi_star + TAIL_MARGIN, "yes_event_clusters": ny, "conf": TAIL_CONF}
    if ny < MIN_YES_CLUSTERS:
        return {**out, "testable": False, "passes": False, "reason": f"YES event clusters {ny} < {MIN_YES_CLUSTERS}"}
    uniq, codes = np.unique([u["event"] for u in pu], return_inverse=True)
    g = len(uniq)
    s, c = np.bincount(codes, weights=y, minlength=g), np.bincount(codes, minlength=g).astype(float)
    rng = np.random.default_rng(st.SEEDS["G_tail_bootstrap"])
    bs = np.empty(TAIL_BOOT)
    for i in range(TAIL_BOOT):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ s) / max(m @ c, 1e-12)
    var_bin = pi_hat * (1.0 - pi_hat) / n
    deff = max(1.0, float(bs.var(ddof=1)) / var_bin) if var_bin > 0 else 1.0
    bound = c1.wilson_bound(pi_hat, n / deff, TAIL_CONF, "lower")
    return {**out, "testable": True, "deff": deff, "n_eff": n / deff, "lower_bound": bound, "passes": bool(bound > pi_star + TAIL_MARGIN)}


def placebo_structure(units: list[dict]) -> dict:
    """Per-unit event index, break-even probability ``q = a + f``, and the disjoint sub-interval offset / scale that makes neg-risk members of one event mutually
    exclusive (at most one YES); non-neg-risk markets of an event share the event uniform from 0 (comonotone)."""
    pu = [priced(u) for u in units]
    ev_idx: dict[str, int] = {}
    for u in pu:
        ev_idx.setdefault(u["event"], len(ev_idx))
    q = np.array([u["K"] for u in pu], float)
    e = np.array([ev_idx[u["event"]] for u in pu], int)
    width: dict[tuple[int, str], float] = {}
    for u, qi, ei in zip(pu, q, e, strict=True):
        if u["neg_risk"]:
            key = (int(ei), u["market_id"])
            width[key] = max(width.get(key, 0.0), float(qi))
    tot: dict[int, float] = {}
    for (ei, _), w in width.items():
        tot[ei] = tot.get(ei, 0.0) + w
    scale = {ei: (1.0 / t if t > 1.0 else 1.0) for ei, t in tot.items()}
    off: dict[tuple[int, str], float] = {}
    run: dict[int, float] = {}
    for key in sorted(width):
        ei = key[0]
        off[key] = run.get(ei, 0.0)
        run[ei] = run.get(ei, 0.0) + width[key] * scale[ei]
    offset = np.array([off.get((int(ei), u["market_id"]), 0.0) if u["neg_risk"] else 0.0 for u, ei in zip(pu, e, strict=True)], float)
    sc = np.array([scale.get(int(ei), 1.0) if u["neg_risk"] else 1.0 for u, ei in zip(pu, e, strict=True)], float)
    return {"n_events": len(ev_idx), "e": e, "q": q, "offset": offset, "scale": sc, "units": pu}


def breakeven_g1(units: list[dict], *, alpha: float = st.ALPHA1, draws: int = st.PLACEBO_DRAWS, seed: int | None = None) -> dict:
    """G1 break-even placebo (calibration; binding): ``Y' ~ Bern(a + f(a))`` per event (one uniform per event, neg-risk members on disjoint sub-intervals so at most one
    resolves YES), expected net 0; the G1 p condition AND the inverted tail gate on 200 draws (floor and R_ann off); calibrated iff the advance rate <= 1.5%."""
    seed = st.SEEDS["G_breakeven"] if seed is None else seed
    if not units:
        return {"skipped": "no units"}
    ps = placebo_structure(units)
    rng = np.random.default_rng(seed)
    adv = 0
    for _ in range(draws):
        u_e = rng.random(ps["n_events"])[ps["e"]]
        y = ((u_e >= ps["offset"]) & (u_e < ps["offset"] + ps["q"] * ps["scale"])).astype(float)
        drawn = [{**u, "y": float(yi)} for u, yi in zip(ps["units"], y, strict=True)]
        t = g1_test(drawn, alpha=alpha)
        if st.p_ok(t, alpha) and inverted_tail_gate(drawn)["passes"]:
            adv += 1
    return st.placebo_summary(adv, draws, seed)


def _robust_t(units: list[dict], alpha: float, **kw) -> dict:
    t = g1_test(units, alpha=alpha, **kw)
    return {"p": t["p"], "mean": t["mean"], "n": t["n"], "testable": t["testable"], "ok": bool(st.p_ok(t, alpha) and t["mean"] > 0)}


def robustness(units: list[dict], unres: list[dict], h_geo: float | None, *, alpha: float = st.ALPHA1) -> dict:
    """Binding robustness for G1: (i) +0.75c on a keeps net > 0 (and the p threshold); (ii) without the top 5 clusters in EACH way (event x week, theme): p threshold and
    floor; (iv) quarter signs REPORTED, not binding; (v) censored / undecided units at Y = 0; (vii) closed_time < end_at - 2 d dropped; (ix) measured spread
    ``a = m + max(half_spread, h_geo)`` (unverified if h_geo is unavailable); (x) tag-and-topic subset. (iii), (vi), (viii), (xi) belong to S1 / X1."""
    out: dict = {}
    pu = [priced(u) for u in units]
    t_cost = g1_test(units, alpha=alpha, shift=COST_ROBUST)
    out["i_cost_0.75c"] = {"mean": t_cost["mean"], "p": t_cost["p"], "ok": bool(t_cost["mean"] > 0 and st.p_ok(t_cost, alpha))}
    drops = {}
    for way in ("ew", "theme"):
        kept_units = st.drop_top([{**u, "v": u["net"]} for u in pu], way)
        t = g1_test(kept_units, alpha=alpha)
        drops[way] = {"n": t["n"], "mean": t["mean"], "p": t["p"], "r_ann": t.get("r_ann"), "ok": bool(st.p_ok(t, alpha) and floor_ok(t))}
    out["ii_without_top5"] = {**drops, "ok": all(d["ok"] for d in drops.values())}
    cens = [{**u, "y": 0.0, "hold_d": 1.0} for u in unres]
    out["v_censored_y0"] = _robust_t([*units, *cens], alpha) if units else {"ok": None}
    kept7 = [u for u in units if not u["early_close"]]
    out["vii_drop_closed_before_end_minus_2d"] = {**_robust_t(kept7, alpha), "n_dropped": len(units) - len(kept7)}
    out["ix_measured_spread"] = _robust_t(units, alpha, h_floor=h_geo) if h_geo is not None else {"ok": None, "reason": "h_geo unavailable"}
    out["x_tag_and_topic_subset"] = _robust_t([u for u in units if u["tag_topic"]], alpha)
    qs: dict[str, list[float]] = {}
    for u in pu:
        qs.setdefault(u["quarter"], []).append(u["net"])
    out["iv_quarter_signs_reported_not_binding"] = {q: {"n": len(v), "mean": float(np.mean(v))} for q, v in sorted(qs.items())}
    return out


def reported(units: list[dict], unres: list[dict]) -> dict:
    """Reported, not binding: by theme, by fee category, by origin k, without the top theme (p threshold is not applied), the units' YES rate and the censoring counts."""
    pu = [priced(u) for u in units]
    out: dict = {"n_units": len(pu), "n_unresolved": len(unres), "unresolved_by_status": {s: sum(1 for u in unres if u["status"] == s) for s in ("censored", "undecided")}}
    for name, key in (("by_theme", "theme"), ("by_fee_category", "fee_cat"), ("by_k", "k")):
        d: dict[str, list[dict]] = {}
        for u in pu:
            d.setdefault(str(u[key]), []).append(u)
        out[name] = {k: {"n": len(v), "mean_net": float(np.mean([x["net"] for x in v])), "yes": float(sum(x["y"] for x in v))} for k, v in sorted(d.items())}
    if pu:
        top = max(out["by_theme"], key=lambda k: abs(out["by_theme"][k]["mean_net"] * out["by_theme"][k]["n"]))
        rest = [u for u in units if u["theme"] != top]
        t = g1_test(rest) if rest else {"mean": math.nan, "p": 1.0}
        out["without_top_theme"] = {"theme": top, "n": len(rest), "mean": t["mean"], "p": t["p"]}
        out["status_quo_variant"] = "not producible: status-quo questions are removed at the fetch (CB7 section 10 deviation 1; counts only in frame_report.json)"
    return out


# ---- evaluation and screen --------------------------------------------------------------------------------------------------------------------


def evaluate_g1(units: list[dict], unres: list[dict], *, h_geo: float | None, cumulative_count: int, alpha: float = st.ALPHA1, with_placebo: bool = True) -> dict:
    """The full G1 evaluation on resolved ``units`` (and unresolved ``unres`` for the worst case). ``advance`` here means the unit-level gates of 2.3 (p threshold,
    floor, inverted tail gate, >= 10 YES clusters, calibrated placebo, every binding robustness); the batch Holm (k1 = 3) is applied by the caller."""
    t = g1_test(units, alpha=alpha)
    res: dict = {"G1": {**{k: v for k, v in t.items()}, "ci95_event_week_bootstrap": st.boot_ci([priced(u)["net"] for u in units], [u["ew"] for u in units]) if units else None}}
    res["tail_gate"] = inverted_tail_gate(units) if units else {"passes": False, "testable": False}
    testable = bool(t["testable"])
    res["placebo_breakeven"] = breakeven_g1(units, alpha=alpha) if testable else {"skipped": "not testable"}
    res["robustness"] = robustness(units, unres, h_geo, alpha=alpha) if testable else {}
    res["reported"] = reported(units, unres)
    checks = {"p": bool(st.p_ok(t, alpha)) if testable else False, "floor": floor_ok(t) if testable else False, "tail_gate": bool(res["tail_gate"].get("passes")),
              "yes_event_clusters": bool(t.get("yes_event_clusters", 0) >= MIN_YES_CLUSTERS), "placebo_breakeven": res["placebo_breakeven"].get("calibrated") if testable else False}
    for k, r in res["robustness"].items():
        if "reported" not in k:
            checks[f"robust_{k}"] = r.get("ok")
    failed = sorted(k for k, x in checks.items() if x is False)
    unverified = sorted(k for k, x in checks.items() if x is None)
    res.update(testable=testable, p=float(t["p"]) if testable else 1.0, effect=t["mean"], n=t["n"], checks=checks, failed_checks=failed, unverified_checks=unverified,
               unit_level_pass=bool(testable and not failed and not unverified), cumulative_count_at_run=cumulative_count)
    return res


def decide(res: dict, holm: dict) -> dict:
    """G1 advances to a Stage P registration only if the unit-level gates pass AND it meets the Stage-1 batch Holm (alpha 0.01, k1 = 3). A provisional Holm (sibling
    files missing, entered at p = 1) can only be harder; ``final`` is recorded."""
    reject = bool(((holm.get("tests") or {}).get("G1") or {}).get("reject"))
    adv = bool(res.get("unit_level_pass") and reject)
    res["batch_holm_reject"] = reject
    res["advance"] = adv
    if not res["testable"]:
        res["verdict"] = f"not testable ({(res['G1'].get('reason') or ['?'])[0]})"
    elif adv:
        res["verdict"] = "geopolitics YES longshots paid at modelled asks (single-stage historical screen, unreplicated, L1): Stage P-G registration"
    else:
        res["verdict"] = "not advanced (failed: " + (", ".join([*res["failed_checks"], *res["unverified_checks"], *([] if reject else ["batch_holm"])]) or "none") + ")"
    return res


def _terminal_doc(g: dict, cumulative_count: int) -> dict:
    state = str(g.get("status"))
    label = "not run (deadline)" if state == cm.NOT_RUN_TOKEN else f"not testable ({state})"
    return st.not_testable_doc(label, cumulative_count, placebo_breakeven={"skipped": label})


def screen_g(cb7_dir: Path, root: Path, seals_dir: Path, *, freeze: dict, census: dict, trials_path: Path, wall_clock: Callable[[], float] = time.time) -> dict:
    """q0149: G1 on ``h8_geo``. Write-once results; the Stage-1 copy goes to ``seals/cb7_g1_stage1.json`` (commit it)."""
    from . import cb7_declaration as D  # noqa: PLC0415

    cb7_dir, seals_dir = Path(cb7_dir), Path(seals_dir)
    cum = st.cumulative(trials_path)
    g = census.get("G") or {}
    header = {"inputs": {"census_json_sha256": freeze["spec"].get("census_json_sha256"), "g_seal_listing_sha256": g.get("seal_listing_sha256")}}
    if g.get("status") != "ok" or not (g.get("gate_GG") or {}).get("GG"):
        res = _terminal_doc(g, cum) if g.get("status") != "ok" else st.not_testable_doc("not testable (GG failed in the census)", cum, placebo_breakeven={"skipped": "GG failed"})
        res["batch_holm_reject"] = False
        return st.finish(TEST, res, out_root=cb7_dir, seals_dir=seals_dir, freeze=freeze, declaration_sha=D.declaration_sha256(), trials_path=trials_path,
                         placebo=res.get("placebo_breakeven"), descriptive={"gate_GG": g.get("gate_GG"), "state": g.get("status")}, header=header, wall_clock=wall_clock)
    seals = cc.verify_seal_copies(Path(root), seals_dir)
    if seals[cm.GEO_RUN_ID]["state"] != "sealed":
        res = _terminal_doc({"status": seals[cm.GEO_RUN_ID]["state"]}, cum)
        return st.finish(TEST, res, out_root=cb7_dir, seals_dir=seals_dir, freeze=freeze, declaration_sha=D.declaration_sha256(), trials_path=trials_path,
                         placebo=res.get("placebo_breakeven"), descriptive={"state": seals[cm.GEO_RUN_ID]["state"]}, header=header, wall_clock=wall_clock)
    st.require_siblings_final(cb7_dir, TEST)  # before any sealed file is opened
    rdir = Path(root) / cm.GEO_RUN_ID
    got = h5_seal.read_sealed(rdir, JOB, ["sample.csv.gz", "origin_prices.csv.gz", "drops.csv.gz"], h5_seal.committed_seal_path(cm.GEO_RUN_ID, seals_dir))
    p = {x.name: x for x in got}
    dropped = {r["market_id"] for r in cc.read_cols(p["drops.csv.gz"], ("market_id", "block"), required=("market_id", "block"))}
    rows = list(cc.read_cols(p["sample.csv.gz"], SAMPLE_COLS, required=("market_id", "end_epoch")))
    prices = list(cc.read_cols(p["origin_prices.csv.gz"], PRICE_COLS, required=("market_id", "k", "eligible")))
    units0 = build_units(rows, prices, dropped)
    gate = st.OutcomeGate(freeze["not_before"], wall_clock)

    def _read_outcomes():
        h5_seal.log_access(rdir, JOB, list(st.OUTCOME_FILES))
        return {r["market_id"]: r["outcome_prices"] for r in cc.read_cols(rdir / cm.OUTCOME_FILE, ("market_id", "outcome_prices"), required=("market_id", "outcome_prices"))}

    outcomes = gate.read(_read_outcomes)
    units, unres = attach_outcomes(units0, outcomes)
    h_geo = (g.get("h_geo") or {}).get("h_geo_binding")
    res = evaluate_g1(units, unres, h_geo=h_geo, cumulative_count=cum)
    holm = st.batch_holm_label(TEST, res["p"], cb7_dir)
    res = decide(res, holm)
    header["inputs"].update(h_geo=h_geo, n_units_eligible=len(units0), n_resolved=len(units), n_unresolved=len(unres), outcome_reads=gate.reads)
    return st.finish(TEST, res, out_root=cb7_dir, seals_dir=seals_dir, freeze=freeze, declaration_sha=D.declaration_sha256(), trials_path=trials_path,
                     placebo=res.get("placebo_breakeven"), descriptive=_descriptive(res), header=header, wall_clock=wall_clock)


def _descriptive(res: dict) -> dict:
    return {"gate_checks": res.get("checks"), "tail_gate": {k: (res.get("tail_gate") or {}).get(k) for k in ("passes", "pi_hat", "pi_star", "lower_bound", "yes_event_clusters")},
            "batch_holm_reject": res.get("batch_holm_reject")}
