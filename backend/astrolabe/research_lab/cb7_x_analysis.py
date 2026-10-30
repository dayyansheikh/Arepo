# ruff: noqa: E501
"""CB7-X analysis (docs/research_lab/CREATIVE_BATCH_7.md CB7-X, 2.1-2.6): X1, the resting maker's 1-hour mark-out (plus the forgone rebate) of the fills a 20-minute Kalshi-skewed
step-aside would skip. Stage 1 runs on the worn C1 pairs with the new prints (L1 at most, a gate for Stage 2, not evidence). EXPLORATORY: no edge, calibration or profitability claim.

No outcome field is read anywhere in this module (marks are Polymarket history points). Every function and UPPER_CASE constant is hashed into the CB7 declaration. The definitions
(Kalshi mid, move events, skip windows, usable print, mark availability) are those of ``cb7_xv`` / the census, re-expressed as numpy vectors; ``test_x_vectors_match_census`` checks
that the vector classification equals ``cb7_xv.classify_prints``.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import cb7_astats as st
from . import cb7_census as cc
from . import cb7_common as cm
from . import cb7_xv as xv
from . import economics

Refused = cm.Refused

TEST = "X1"
JOB = "q0150_cb7_screen_X"
HORIZON_S = 3600
LAG_S = xv.SKIP_LAG_S  # 120
LAG_ROBUST_S = 300  # robustness (viii)
SKIP_LEN_S = xv.SKIP_LEN_S  # 1200
SKIP_LEN_REPORTED_S = 600  # reported: 10-minute skip window
HORIZON_REPORTED_S = 1200  # reported: 20-minute horizon
ALT_WINDOW_S = (3000, 4200)  # [s + 50 min, s + 70 min]
FLOOR_MARKOUT = -0.005  # 2.4: mean mark-out (plus forgone rebate) <= -0.5c per share
MONTH_MIN_PRINTS = 500
SHIFT_MARGIN_S = 6 * 3600
REBATE_FROM = "2026-03-30T00:00:00Z"
MIN_CLUSTERS = {"event": 30, "date": 30}  # literal 2.3 "at least 30 clusters per way" (A1 amendment reverted at the code-freeze check)
SPORTS = "sports"


# ---- vector definitions ---------------------------------------------------------------------------------------------------------------


def rebate_rate(k_cat: str) -> float:
    """``REBATE_SHARE[cat] * DOCS_CATEGORY_RATE[cat]`` with cat = the lower-cased Kalshi category when it is a key of both tables. The legs carry only the Kalshi category
    (the Polymarket ``fee_category`` is not stored), so an unmatched category takes the LARGEST rebate rate of any category: a larger rebate makes X1 harder to pass
    (Reading A5)."""
    key = str(k_cat or "").strip().lower()
    table = {c: economics.REBATE_SHARE[c] * economics.DOCS_CATEGORY_RATE[c] for c in economics.REBATE_SHARE if c in economics.DOCS_CATEGORY_RATE}
    return float(table[key]) if key in table else float(max(table.values()))


def mark_at(ps_ts: np.ndarray, ps_px: np.ndarray, u: np.ndarray) -> np.ndarray:
    """``M(u)``: the latest Polymarket history point stamped in ``[u - 3,600, u - 600]`` (NaN if none)."""
    u = np.asarray(u, float)
    if not len(ps_ts):
        return np.full(len(u), np.nan)
    i = np.searchsorted(ps_ts, u - xv.POLY_MARK_MIN_AGE_S, side="right") - 1
    ok = (i >= 0) & (ps_ts[np.clip(i, 0, None)] >= u - xv.POLY_MARK_MAX_AGE_S)
    return np.where(ok, ps_px[np.clip(i, 0, None)], np.nan)


def in_skip_vec(taus: np.ndarray, s: np.ndarray, lag: float, length: float) -> np.ndarray:
    """Vector form of ``cb7_xv.in_skip``: some event ``tau`` has ``tau + lag <= s < tau + lag + length``."""
    if not len(taus):
        return np.zeros(len(s), bool)
    i = np.searchsorted(taus, s - lag, side="right") - 1
    return (i >= 0) & (s < taus[np.clip(i, 0, None)] + lag + length)


def alt_mark(ts: np.ndarray, side: np.ndarray, px: np.ndarray, size: np.ndarray) -> np.ndarray:
    """Alternative mark (robustness i): the midpoint of the ask-side and bid-side print VWAPs in ``[s + 50 min, s + 70 min]``; both sides required, else NaN. ``ts`` sorted."""
    out = np.full(len(ts), np.nan)
    if not len(ts):
        return out
    lo = np.searchsorted(ts, ts + ALT_WINDOW_S[0], side="left")
    hi = np.searchsorted(ts, ts + ALT_WINDOW_S[1], side="right")
    vw = {}
    for sd in (1, -1):
        w = np.where(side == sd, size, 0.0)
        cw = np.concatenate([[0.0], np.cumsum(w)])
        cpw = np.concatenate([[0.0], np.cumsum(w * px)])
        den = cw[hi] - cw[lo]
        vw[sd] = np.where(den > 0, (cpw[hi] - cpw[lo]) / np.where(den > 0, den, 1.0), np.nan)
    return (vw[1] + vw[-1]) / 2.0


class XSet:
    """All prints of a group of pairs as concatenated arrays (pair order) with per-pair Kalshi move events, Polymarket history and window."""

    def __init__(self) -> None:
        self.parts: list[dict] = []
        self.cols: dict[str, np.ndarray] = {}
        self.ranges: list[tuple[int, int]] = []

    def add_pair(self, key: str, event: str, k_cat: str, win: tuple[float, float], kc: np.ndarray, ps: np.ndarray, prints: np.ndarray) -> None:
        """``prints`` is an (n, 4) array ``ts, side, yes_price, size``; ``kc`` the Kalshi candles; ``ps`` the Polymarket history ``(stamp, price)``."""
        km = xv.KalshiMid(kc)
        up, down = xv.move_events(km)
        ps = np.asarray(ps, float).reshape(-1, 2)
        if len(ps):
            ps = ps[np.argsort(ps[:, 0], kind="stable")]
        pr = np.asarray(prints, float).reshape(-1, 4)
        if len(pr):
            pr = pr[np.argsort(pr[:, 0], kind="stable")]
        ts = pr[:, 0]
        kmid = km.at_many(ts) if len(ts) else np.empty(0)
        m0 = mark_at(ps[:, 0], ps[:, 1], ts) if len(ps) else np.full(len(ts), np.nan)
        usable = np.isfinite(kmid) & np.isfinite(m0) & (m0 >= xv.MID_RANGE[0] - 1e-12) & (m0 <= xv.MID_RANGE[1] + 1e-12)
        self.parts.append({"key": key, "event": event, "cat": k_cat, "win": win, "up": np.array(up), "down": np.array(down), "ps": ps, "pr": pr, "usable": usable, "m0": m0,
                           "alt": alt_mark(ts, pr[:, 1], pr[:, 2], pr[:, 3]) if len(ts) else np.empty(0)})

    def finish(self) -> XSet:
        n = [len(p["pr"]) for p in self.parts]
        edges = np.concatenate([[0], np.cumsum(n)]).astype(int)
        self.ranges = [(int(edges[i]), int(edges[i + 1])) for i in range(len(n))]

        def cat(f):
            return np.concatenate([f(p) for p in self.parts]) if self.parts else np.empty(0)

        ts = cat(lambda p: p["pr"][:, 0])
        self.cols = {
            "ts": ts, "side": cat(lambda p: p["pr"][:, 1]), "px": cat(lambda p: p["pr"][:, 2]), "size": cat(lambda p: p["pr"][:, 3]),
            "usable": cat(lambda p: p["usable"]).astype(bool), "m0": cat(lambda p: p["m0"]), "alt": cat(lambda p: p["alt"]),
            "event": cat(lambda p: np.full(len(p["pr"]), p["event"], dtype=object)).astype(str),
            "reb": cat(lambda p: np.where(p["pr"][:, 0] >= cm._ep(REBATE_FROM), rebate_rate(p["cat"]) * p["pr"][:, 2] * (1.0 - p["pr"][:, 2]), 0.0)),
        }
        t64 = ts.astype("datetime64[s]") if len(ts) else np.empty(0, "datetime64[s]")
        self.cols["date"] = t64.astype("datetime64[D]").astype(str)
        self.cols["month"] = t64.astype("datetime64[M]").astype(str)
        return self

    def __len__(self) -> int:
        return len(self.cols.get("ts", []))

    def skip_states(self, lag: float, length: float, taus_override: list[tuple[np.ndarray, np.ndarray]] | None = None) -> tuple[np.ndarray, np.ndarray]:
        up = np.zeros(len(self), bool)
        dn = np.zeros(len(self), bool)
        for i, (a, b) in enumerate(self.ranges):
            tu, td = (taus_override[i] if taus_override is not None else (self.parts[i]["up"], self.parts[i]["down"]))
            up[a:b] = in_skip_vec(tu, self.cols["ts"][a:b], lag, length)
            dn[a:b] = in_skip_vec(td, self.cols["ts"][a:b], lag, length)
        return up, dn

    def marks(self, horizon: float) -> np.ndarray:
        """``M(s + horizon)`` per print (NaN if the mark is unavailable)."""
        out = np.full(len(self), np.nan)
        for i, (a, b) in enumerate(self.ranges):
            ps = self.parts[i]["ps"]
            if len(ps) and b > a:
                out[a:b] = mark_at(ps[:, 0], ps[:, 1], self.cols["ts"][a:b] + horizon)
        return out


def classify(xs: XSet, up: np.ndarray, dn: np.ndarray) -> dict[str, np.ndarray]:
    """Usable prints are S (ask-side in an up-skip or bid-side in a down-skip), S' (the opposite sides in the same states) or N (neither state); prints in both
    states and unusable prints (no valid Kalshi mid or Polymarket point in [0.03, 0.97]) are excluded."""
    usable, side = xs.cols["usable"], xs.cols["side"]
    both = usable & up & dn
    one = usable & (up ^ dn)
    s = one & (((side > 0) & up) | ((side < 0) & dn))
    return {"S": s, "Sp": one & ~s, "N": usable & ~up & ~dn, "excluded_both": both, "excluded_unusable": ~usable}


def markout(xs: XSet, mark: np.ndarray) -> np.ndarray:
    """Maker mark-out per share: ask-side ``p - M``, bid-side ``M - p`` (= ``side * (p - M)``)."""
    return xs.cols["side"] * (xs.cols["px"] - mark)


def units_of(xs: XSet, mask: np.ndarray, mo: np.ndarray, with_rebate: bool = True) -> list[dict]:
    idx = np.flatnonzero(mask)
    c = xs.cols
    return [{"v": float(mo[i] + (c["reb"][i] if with_rebate else 0.0)), "event": str(c["event"][i]), "date": str(c["date"][i]), "month": str(c["month"][i]), "size": float(c["size"][i])}
            for i in idx]


def x1_test(units: list[dict], *, alpha: float | None = None) -> dict:
    """X1 = mean (mark-out + forgone rebate) over S, unweighted per print; one-sided < 0; p = max over (Polymarket event, UTC date)."""
    v = np.array([u["v"] for u in units])
    return st.ways_test(v, {"event": [u["event"] for u in units], "date": [u["date"] for u in units]}, sign=-1, min_clusters=MIN_CLUSTERS, alpha=alpha)


def floor_ok(t: dict) -> bool:
    return bool(np.isfinite(t["mean"]) and t["mean"] <= FLOOR_MARKOUT)


def core(xs: XSet, *, lag: float = LAG_S, length: float = SKIP_LEN_S, horizon: float = HORIZON_S, taus_override=None, mark: np.ndarray | None = None) -> dict:
    up, dn = xs.skip_states(lag, length, taus_override)
    cl = classify(xs, up, dn)
    m = xs.marks(horizon) if mark is None else mark
    mo = markout(xs, m)
    avail = np.isfinite(m)
    return {"cl": cl, "mark": m, "mo": mo, "avail": avail, "S_units": units_of(xs, cl["S"] & avail, mo)}


# ---- placebo, attribution, route, robustness ------------------------------------------------------------------------------------------


def shifted_taus(xs: XSet, rng: np.random.Generator) -> list[tuple[np.ndarray, np.ndarray]]:
    """Per pair and draw, the Kalshi move-event times are shifted circularly within the pair's window by an offset uniform in ``[6 h, W - 6 h]`` (the same offset for the
    up and down events of a pair)."""
    out = []
    for p in xs.parts:
        a, b = p["win"]
        w = float(b - a)
        lo, hi = float(SHIFT_MARGIN_S), w - SHIFT_MARGIN_S
        off = float(rng.uniform(lo, hi)) if hi > lo else lo
        out.append(tuple(np.sort(a + np.mod(t - a + off, w)) if len(t) and w > 0 else t for t in (p["up"], p["down"])))
    return out


def time_shift_placebo(xs: XSet, *, alpha: float = st.ALPHA1, draws: int = st.PLACEBO_DRAWS, seed: int | None = None) -> dict:
    """X1 time-shift calibration placebo (binding): X1 recomputed on 200 draws, p only (floor off); calibrated iff the advance rate (p < 0.01) is <= 1.5%."""
    seed = st.SEEDS["X_time_shift"] if seed is None else seed
    rng = np.random.default_rng(seed)
    m = xs.marks(HORIZON_S)
    mo = markout(xs, m)
    avail = np.isfinite(m)
    adv = 0
    for _ in range(draws):
        up, dn = xs.skip_states(LAG_S, SKIP_LEN_S, shifted_taus(xs, rng))
        s = classify(xs, up, dn)["S"] & avail
        t = x1_test(units_of(xs, s, mo), alpha=alpha)
        adv += int(st.p_ok(t, alpha))
    return st.placebo_summary(adv, draws, seed)


def route_gate(xs: XSet, c: dict) -> dict:
    """Binding route gate: the mean mark-out over N u S' (the fills the skewed maker keeps) must be >= 0 at the point estimate, WITHOUT the rebate those fills would earn
    (conservative literal reading; the with-rebate value is reported)."""
    kept = (c["cl"]["N"] | c["cl"]["Sp"]) & c["avail"]
    if not kept.any():
        return {"n": 0, "ok": None, "mean_markout": None}
    reb = float(xs.cols["reb"][kept].mean())
    mm = float(c["mo"][kept].mean())
    return {"n": int(kept.sum()), "mean_markout": mm, "mean_markout_with_rebate": mm + reb, "ok": bool(mm >= 0.0),
            "label": None if mm >= 0.0 else "skipping helps, but the maker still loses: no route"}


def lead_decomposition(xs: XSet, c: dict) -> dict:
    """Reported: X1 = spread captured ``mean_S(side * (p - M(s)))`` + drift against the maker ``mean_S(side * (M(s) - M(s + 3,600)))`` (+ forgone rebate)."""
    s = c["cl"]["S"] & c["avail"]
    if not s.any():
        return {}
    side, px, m0 = xs.cols["side"][s], xs.cols["px"][s], xs.cols["m0"][s]
    spread = float((side * (px - m0)).mean())
    drift = float((side * (m0 - c["mark"][s])).mean())
    return {"n": int(s.sum()), "spread_part": spread, "drift_part": drift, "rebate_part": float(xs.cols["reb"][s].mean()), "sum": spread + drift + float(xs.cols["reb"][s].mean())}


def worst_case(xs: XSet, c: dict, alpha: float) -> dict:
    """Robustness (v): S prints whose mark is unavailable enter with mark-out ``max(0, mean mark-out of the kept fills)`` plus their rebate (Reading A4: the CB7-X text declares
    no worst case; this is CB8-W's rule); the estimate must stay negative and keep the p threshold."""
    kept = (c["cl"]["N"] | c["cl"]["Sp"]) & c["avail"]
    kept_mean = float(c["mo"][kept].mean()) if kept.any() else 0.0
    miss = c["cl"]["S"] & ~c["avail"]
    mo = np.where(c["avail"], c["mo"], max(0.0, kept_mean))
    units = units_of(xs, c["cl"]["S"], mo)
    t = x1_test(units, alpha=alpha)
    return {"n_unavailable": int(miss.sum()), "mean": t["mean"], "p": t["p"], "ok": bool(t["mean"] < 0 and st.p_ok(t, alpha)) if t["n"] else None}


def robustness(xs: XSet, c: dict, main: dict, *, alpha: float = st.ALPHA1) -> dict:
    """Binding robustness for X1: (i) alternative mark keeps the sign and at least half the magnitude; (ii) without the top 5 clusters in EACH way: p threshold and floor;
    (iii) size-weighted estimate agrees in sign; (iv) negative in >= 2/3 of months with >= 500 skipped prints; (v) worst case; (viii) latency 300 s keeps the sign and >= half."""
    out: dict = {}
    s = c["cl"]["S"]
    alt = xs.cols["alt"]
    mo_alt = markout(xs, alt)
    ua = units_of(xs, s & np.isfinite(alt), mo_alt)
    am = float(np.mean([u["v"] for u in ua])) if ua else math.nan
    out["i_alternative_mark"] = {"n": len(ua), "mean": am, "ok": st.half_magnitude_ok(am, main["mean"], -1) if ua else None}
    drops = {}
    for way in ("event", "date"):
        t = x1_test(st.drop_top(c["S_units"], way), alpha=alpha)
        drops[way] = {"n": t["n"], "mean": t["mean"], "p": t["p"], "ok": bool(st.p_ok(t, alpha) and floor_ok(t))}
    out["ii_without_top5"] = {**drops, "ok": all(d["ok"] for d in drops.values())}
    w = np.array([u["size"] for u in c["S_units"]])
    v = np.array([u["v"] for u in c["S_units"]])
    wm = float((w * v).sum() / w.sum()) if len(v) and w.sum() > 0 else math.nan
    out["iii_size_weighted_sign"] = {"weighted_mean": wm, "ok": bool(np.isfinite(wm) and wm < 0 and main["mean"] < 0)}
    ms = st.month_sign(c["S_units"], -1, MONTH_MIN_PRINTS)
    out["iv_sign_by_month"] = ms | {"ok": ms["ok"]}
    out["v_worst_case_unavailable_marks"] = worst_case(xs, c, alpha)
    c3 = core(xs, lag=LAG_ROBUST_S)
    t3 = x1_test(c3["S_units"], alpha=alpha)
    out["viii_latency_300s"] = {"n": t3["n"], "mean": t3["mean"], "ok": st.half_magnitude_ok(t3["mean"], main["mean"], -1) if t3["n"] else None}
    return out


def reported(xs: XSet, c: dict, main: dict, sports: XSet | None) -> dict:
    out: dict = {"lead_decomposition": lead_decomposition(xs, c)}
    c20 = core(xs, horizon=HORIZON_REPORTED_S)
    t20 = x1_test(c20["S_units"])
    out["horizon_20min"] = {"n": t20["n"], "mean": t20["mean"], "p": t20["p"]}
    c10 = core(xs, length=SKIP_LEN_REPORTED_S)
    t10 = x1_test(c10["S_units"])
    out["skip_window_10min"] = {"n": t10["n"], "mean": t10["mean"], "p": t10["p"]}
    if sports is not None and len(sports):
        cs = core(sports)
        ts_ = x1_test(cs["S_units"])
        out["sports_stratum_uncounted"] = {"n": ts_["n"], "mean": ts_["mean"], "p": ts_["p"]}
    out["not_implemented_reported_variants"] = ["X1 with the 4 outcome-surfaced pairs re-added (pair ids are not in the declaration)", "+1c costs (X1 has no cost shift: the binding cost robustness is the alternative mark)"]
    return out


def evaluate_x1(xs: XSet, sports: XSet | None, *, cumulative_count: int, alpha: float = st.ALPHA1, with_placebo: bool = True) -> dict:
    c = core(xs)
    t = x1_test(c["S_units"])
    res: dict = {"X1": {**t, "ci95_event_bootstrap": st.boot_ci([u["v"] for u in c["S_units"]], [u["event"] for u in c["S_units"]]) if c["S_units"] else None},
                 "print_classes": {k: int(v.sum()) for k, v in c["cl"].items()}, "n_S_mark_available": len(c["S_units"])}
    testable = bool(t["testable"])
    res["route_gate"] = route_gate(xs, c)
    res["wrong_side"] = {**st.attribution(t["mean"], [u["v"] for u in units_of(xs, c["cl"]["Sp"] & c["avail"], c["mo"])], -1, ("skew credited", "post-move fills adverse on both sides: a pause, not a skew"), "wrong-side"), "binding_for": "crediting only"}
    res["placebo_time_shift"] = time_shift_placebo(xs, alpha=alpha) if testable and with_placebo else {"skipped": "not testable" if not testable else "disabled"}
    res["robustness"] = robustness(xs, c, t, alpha=alpha) if testable else {}
    res["reported"] = reported(xs, c, t, sports)
    checks = {"p": bool(st.p_ok(t, alpha)) if testable else False, "floor": floor_ok(t) if testable else False,
              "placebo_time_shift": res["placebo_time_shift"].get("calibrated") if testable else False, "route_gate": res["route_gate"]["ok"] if testable else False}
    for k, r in res["robustness"].items():
        checks[f"robust_{k}"] = r.get("ok")
    failed = sorted(k for k, x in checks.items() if x is False)
    unverified = sorted(k for k, x in checks.items() if x is None)
    adv = bool(testable and not failed and not unverified)
    res.update(testable=testable, p=float(t["p"]) if testable else 1.0, effect=t["mean"], n=t["n"], checks=checks, failed_checks=failed, unverified_checks=unverified, advance=adv,
               cumulative_count_at_run=cumulative_count)
    if not testable:
        res["verdict"] = f"not testable ({(t.get('reason') or ['?'])[0]})"
    elif adv:
        label = "" if res["wrong_side"].get("credited") else f" ({res['wrong_side']['label']})"
        res["verdict"] = "advanced to Stage 2 on fresh pairs (worn pairs, L1; a gate for Stage 2, not evidence)" + label
    elif res["route_gate"]["ok"] is False and st.p_ok(t, alpha) and t["mean"] < 0:
        res["verdict"] = "skipping helps, but the maker still loses: no route"
    else:
        res["verdict"] = "not detected at MDE (failed: " + ", ".join([*failed, *unverified]) + ")"
    return res


# ---- loading and screen ---------------------------------------------------------------------------------------------------------------


def load_xsets(xv_dir: Path, cv_root: Path) -> tuple[XSet, XSet, dict]:
    """(non-sports XSet, sports XSet, info) from the q0146 tables and the C1 series files (read-only; never ``cross_venue_live``)."""
    cm.refuse_path(Path(cv_root))
    legs = {r["pair_key"]: r for r in cm.read_csv_gz(Path(xv_dir) / "legs.csv.gz")}
    ns, sp = XSet(), XSet()
    for key, leg in sorted(legs.items()):
        z = np.load(Path(cv_root) / "series" / f"{key}.npz")
        pf = Path(xv_dir) / "prints" / f"{key}.csv.gz"
        rows = list(cc.read_cols(pf, ("ts", "side", "yes_price", "size"), required=("ts", "side"))) if pf.exists() else []
        pr = np.array([[cc._f(r["ts"]), cc._f(r["side"]), cc._f(r["yes_price"]), cc._f(r["size"])] for r in rows], float).reshape(-1, 4)
        tgt = sp if str(leg.get("k_cat", "")).strip().lower() == SPORTS else ns
        tgt.add_pair(key, str(leg["p_event_id"]), str(leg.get("k_cat", "")), (float(z["win"][0]), float(z["win"][1])), z["kc"], z["ps"], pr)
    return ns.finish(), sp.finish(), {"pairs": len(legs)}


def _descriptive(res: dict) -> dict:
    return {"gate_checks": res.get("checks"), "print_classes": res.get("print_classes"), "route_gate": {k: (res.get("route_gate") or {}).get(k) for k in ("n", "mean_markout", "ok")},
            "wrong_side": {k: (res.get("wrong_side") or {}).get(k) for k in ("credited", "label")}}


def screen_x(cb7_dir: Path, cv_root: Path, seals_dir: Path, *, freeze: dict, census: dict, trials_path: Path, wall_clock: Callable[[], float] = time.time, union_recorded_utc: str | None = None) -> dict:
    """q0150: X1 on the C1 pairs with the new prints. Write-once results; the Stage-1 copy goes to ``seals/cb7_x1_stage1.json`` (commit it)."""
    from . import cb7_declaration as D  # noqa: PLC0415

    cb7_dir, seals_dir = Path(cb7_dir), Path(seals_dir)
    decl = D.declaration_sha256()
    cum = st.cumulative(trials_path)
    x = census.get("X") or {}
    header = {"inputs": {"census_json_sha256": freeze["spec"].get("census_json_sha256")}}
    if x.get("status") != "ok" or not (x.get("gate_GX") or {}).get("GX"):
        label = "not testable (xv_prints terminal: " + str(x.get("status")) + ")" if x.get("status") != "ok" else "not testable (GX failed in the census)"
        res = st.not_testable_doc(label, cum, placebo_time_shift={"skipped": label}, route_gate={"ok": None}, wrong_side={})
        return st.finish(TEST, res, out_root=cb7_dir, seals_dir=seals_dir, freeze=freeze, declaration_sha=decl, trials_path=trials_path, placebo=res["placebo_time_shift"],
                         descriptive={"gate_GX": x.get("gate_GX"), "state": x.get("status")}, header=header, wall_clock=wall_clock, union_recorded_utc=union_recorded_utc)
    xv_dir = cb7_dir / xv.XV_RUN_ID
    cc.require_xv_complete(xv_dir)
    ns, sp, info = load_xsets(xv_dir, Path(cv_root))
    res = evaluate_x1(ns, sp, cumulative_count=cum)
    header["inputs"].update(info)
    return st.finish(TEST, res, out_root=cb7_dir, seals_dir=seals_dir, freeze=freeze, declaration_sha=decl, trials_path=trials_path, placebo=res.get("placebo_time_shift"),
                     descriptive=_descriptive(res), header=header, wall_clock=wall_clock, union_recorded_utc=union_recorded_utc)
