# ruff: noqa: E501
"""Single registered analysis of the live tests E020-E024 (docs/research_lab/LIVE_TESTS_4.md). DRAFT until registered.

Runs ONCE, after ``live_tests4.ANALYSIS_NOT_BEFORE``, on the write-once files of ``live_tests4``. One Holm family over the
k primaries that survived their census gates (spec ``k_tests``), one-sided, familywise alpha 0.05. A primary that is
unavailable or fails its gate enters Holm with p = 1. Mechanism readings, secondaries, labels and economics never change
a verdict and count 0.

Estimator: expanding-past demeaning (J4-R) for all five primaries (LT3's ``fit``, imported). Inference (LIVE_TESTS_4.md
1.7, rule L10): CR1 on the event, two-way event x UTC day, and UTC day; one-sided p = max(p_event on t with G_event - 1
df, p_two-way, p_day on t with G_day - 1 df). Gates: LT3's label-permutation gate (E020, E021; E022 with a continuous
label) and distant-donor gate (E023, E024), imported unmodified.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import live_tests3_analysis as la3
from . import live_tests4 as lt

TESTS = ("E020", "E021", "E022", "E023", "E024")
DIRECTION = {"E020": +1, "E021": -1, "E022": -1, "E023": +1, "E024": +1}
CONTROLS_E020, CONTROLS_E021, CONTROLS_E022 = lt.CONTROLS_E020, lt.CONTROLS_E021, lt.CONTROLS_E022
GATE_LABEL = {"E020": "SE check failed", "E021": "SE check failed", "E022": "SE check failed",
              "E023": "within-unit timing not shown", "E024": "within-unit timing not shown"}
TRIAL_KIND = "live_tests4"

strip, gross, econ, paper_taker, attrition, lee_bounds = la3.strip, la3.gross, la3.econ, la3.paper_taker, la3.attrition, la3.lee_bounds
floors_ok, check_fraction, attach, underpowered, verdict = la3.floors_ok, la3.check_fraction, la3.attach, la3.underpowered, la3.verdict
late_mask, mid_at, day_of, block_of, add_products = la3.late_mask, la3.mid_at, la3.day_of, la3.block_of, la3.add_products


def _nanlike(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


# --- pins -----------------------------------------------------------------------------------------------------------


def code_check(spec: dict) -> dict:
    """Compare the four modules on disk with the spec's ``code_sha256`` map. A pinned spec refuses on any mismatch, an
    unfilled map, null ``k_tests`` or a null / NaN census value its tests need (L2, L7); a DRAFT spec only labels."""
    pins = spec.get("code_sha256") or {}
    cur = lt.code_hashes()
    status = {n: ("not pinned" if pins.get(n) is None else ("match" if pins.get(n) == h else "MISMATCH")) for n, h in cur.items()}
    if spec.get("_pinned"):
        bad = {n: s for n, s in status.items() if s != "match"}
        if bad:
            raise RuntimeError(f"live_tests4 code sha256 does not match the registered pins: {bad}")
        k = spec.get("k_tests")
        if k is None:
            raise RuntimeError("live_tests4 spec pinned with null k_tests")
        f = spec["flow"]
        if any(t in k for t in ("E023", "E024")):
            vals = [f.get("vol24_cap")] + [f[z].get(q) for z in ("zW", "zH", "zN", "zSize", "zSPR", "zRV", "zHTE", "zOP", "zC") for q in ("centre", "scale")]
            if "E023" in k:
                vals.append(f["econ"].get("OP_upper_cut"))
            if "E024" in k:
                vals.append(f["econ"].get("C_upper_cut"))
            if any(_nanlike(v) for v in vals):
                raise RuntimeError("live_tests4 spec pinned with unfilled (null or NaN) flow census values")
        if "E022" in k:
            h = spec["hollow"]
            if any(_nanlike(v) for v in (h["zh"].get("centre"), h["zh"].get("scale"), *h["h_cuts"], h.get("gap"), h.get("depth_def"))):
                raise RuntimeError("live_tests4 spec pinned with unfilled (null or NaN) hollow census values")
        for t in ("E020", "E021", "E022"):  # R1 findings 2 and answer 9: census-fixed stratum and family exclusion
            if t in k and (spec[t.lower()].get("perm_stratum") not in ("day", "block2") or spec[t.lower()].get("exclude_family") is None):
                raise RuntimeError(f"live_tests4 spec pinned with unfilled {t.lower()}.perm_stratum / exclude_family")
        lt3_pins = (lt.l3.load_spec(sha=None).get("code_sha256") or {})
        for n in ("live_tests3.py", "live_tests3_analysis.py"):  # R1 finding 12: LT4 pins the LT3 code LT3 registered
            if lt3_pins.get(n) is not None and lt3_pins[n] != pins.get(n):
                raise RuntimeError(f"live_tests4 pin of {n} differs from LT3's registered pin")
    return {"current": cur, "pinned": {n: pins.get(n) for n in cur}, "status": status,
            "label": None if all(s == "match" for s in status.values()) else "DRAFT: code hashes not verified"}


# --- loading --------------------------------------------------------------------------------------------------------


def load_kind(root: Path, kind: str, start: float, end: float, roles: tuple[str, ...], spec: dict | None,
              tags: tuple[str, ...]) -> tuple[pd.DataFrame, dict]:
    """Frozen lines of origins in [start, end) with an allowed role (and, with a pinned spec, the pinned spec hash and
    joint reader hash), merged with their outcome files (columns suffixed ``_<tag>``). Counts dropped lines and markers."""
    fdir, odir = Path(root) / kind / "frozen", Path(root) / kind / "outcomes"
    pinned = bool(spec and spec.get("_pinned"))
    pins = (spec or {}).get("code_sha256") or {}
    want_spec = spec["_sha256"][:16] if pinned else None
    want_code = lt.joint_sha(pins.get("live_tests4.py"), pins.get("live_tests3.py")) if pinned else None
    acc = {"files": 0, "late_files": 0, "noprev_files": 0, "nosweep_files": 0, "dropped_role": 0, "dropped_spec_sha": 0, "dropped_code_sha": 0}
    parts = []
    for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
        if p.name.endswith(lt.MARKERS):
            acc[p.name.split(".")[-3] + "_files"] += 1
            continue
        fr = pd.read_csv(p, dtype={"market_id": str, "event_id": str, "spec_sha": str, "code_sha": str, "skey": str}, float_precision="round_trip")
        if not len(fr) or not (start <= float(fr["capture_t"].iloc[0]) < end):
            continue
        acc["files"] += 1
        keep = fr["role"].isin(roles)
        acc["dropped_role"] += int((~keep).sum())
        fr = fr[keep]
        if pinned:
            for col, want, key in (("spec_sha", want_spec, "dropped_spec_sha"), ("code_sha", want_code, "dropped_code_sha")):
                ok = fr[col].astype(str) == want
                acc[key] += int((~ok).sum())
                fr = fr[ok]
        fid = p.name[:-7]
        for tag in tags:
            op = odir / f"{fid}.{tag}.csv.gz"
            if op.exists():
                out = pd.read_csv(op, dtype={"market_id": str, "status": str, "cap_id": str}, float_precision="round_trip").drop_duplicates("market_id")
                out = out.rename(columns={c: f"{c}_{tag}" for c in out.columns if c != "market_id"})
                fr = fr.merge(out, on="market_id", how="left")
            else:
                fr[f"status_{tag}"] = "pending"
        fr["file"] = fid
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    tot = acc["files"] + acc["late_files"]
    acc["late_loss_share"] = acc["late_files"] / tot if tot else 0.0
    return df, acc


def _two(df: pd.DataFrame, tag: str) -> np.ndarray:
    return df.get(f"status_{tag}", pd.Series("", index=df.index)).astype(str).to_numpy() == "two_sided"


def _col(df: pd.DataFrame, c: str) -> np.ndarray:
    return df[c].to_numpy(float) if c in df else np.full(len(df), np.nan)


def move_frame(root: Path, start: float, end: float, roles, spec) -> tuple[pd.DataFrame, dict]:
    df, acc = load_kind(root, "move", start, end, roles, spec, ("h1", "h3", "s0", "s1"))
    if df.empty:
        return df, acc
    sx = np.sign(df["x"].to_numpy(float))
    bid_side = df["side_moved"].astype(str).to_numpy() == "bid"
    late1, late3 = late_mask(df, "h1"), late_mask(df, "h3")
    acc["late_lines_h1"] = int(late1.sum())
    U1 = np.where(_two(df, "h1"), np.where(bid_side, _col(df, "ask_h1"), _col(df, "bid_h1")), np.nan)
    U3 = np.where(_two(df, "h3"), np.where(bid_side, _col(df, "ask_h3"), _col(df, "bid_h3")), np.nan)
    Us0 = np.where(_two(df, "s0"), np.where(bid_side, _col(df, "sask_s0"), _col(df, "sbid_s0")), np.nan)
    Us1 = np.where(_two(df, "s1"), np.where(bid_side, _col(df, "sask_s1"), _col(df, "sbid_s1")), np.nan)
    df["r"] = np.where(late1, np.nan, sx * (U1 - df["U_k"].to_numpy(float)))
    df["r_skip"] = np.where(late3, np.nan, sx * (U3 - U1))
    df["r_sw"] = np.where(late1, np.nan, sx * (Us1 - Us0))
    df["c"] = np.where(late1, np.nan, sx * (mid_at(df, "h1") - df["mid_k"].to_numpy(float)))
    df["status_h1"] = np.where(late1, "late", df["status_h1"].astype(str))
    df["day"] = day_of(df["t_row"])
    df["block"] = block_of(df["t_row"], start)
    return df, acc


def clock_frame(root: Path, start: float, end: float, roles, spec) -> tuple[pd.DataFrame, dict]:
    df, acc = load_kind(root, "clock", start, end, roles, spec, ("h1", "h3", *(f"s{j}" for j in spec["clock"]["sweep_tags"])))
    if df.empty:
        return df, acc
    sx = np.sign(df["x"].to_numpy(float))
    late1, late3 = late_mask(df, "h1"), late_mask(df, "h3")
    acc["late_lines_h1"] = int(late1.sum())
    m1, m3 = mid_at(df, "h1"), mid_at(df, "h3")
    df["c"] = np.where(late1, np.nan, sx * (m1 - df["mid_k"].to_numpy(float)))
    df["c6"] = np.where(late3, np.nan, sx * (m3 - df["mid_k"].to_numpy(float)))
    df["c_skip"] = np.where(late3, np.nan, sx * (m3 - m1))
    df["c_sw"] = np.where(late1, np.nan, sx * (mid_at(df, "s1") - mid_at(df, "s0")))
    df["c_skip_sw"] = np.where(late3, np.nan, sx * (mid_at(df, "s3") - mid_at(df, "s1"))) if "status_s3" in df else np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        df["log_age"] = np.log(np.clip(df["age"].to_numpy(float), 1.0, None))
    df["status_h1"] = np.where(late1, "late", df["status_h1"].astype(str))
    df["day"] = day_of(df["t_row"])
    df["block"] = block_of(df["t_row"], start)
    return df, acc


def hollow_frame(root: Path, start: float, end: float, roles, spec) -> tuple[pd.DataFrame, dict]:
    df, acc = load_kind(root, "hollow", start, end, roles, spec, ("h1", "h3", "s1"))
    if df.empty:
        return df, acc
    sx = np.sign(df["x"].to_numpy(float))
    late1, late3 = late_mask(df, "h1"), late_mask(df, "h3")  # capture k + 1 starts before sweep 1 of pass k + 1
    smid0 = np.where(df["s_two0"].to_numpy(int) == 1, (df["sbid0"].to_numpy(float) + df["sask0"].to_numpy(float)) / 2.0, np.nan)
    m1, m3 = mid_at(df, "h1"), mid_at(df, "h3")
    df["c_sw"] = np.where(late1, np.nan, sx * (mid_at(df, "s1") - smid0))
    df["c_skip"] = np.where(late3, np.nan, sx * (m3 - m1))
    df["c_gamma"] = np.where(late1, np.nan, sx * (m1 - df["mid_k"].to_numpy(float)))
    df["status_s1"] = np.where(late1, "late", df["status_s1"].astype(str))
    df["day"] = day_of(df["t_row"])
    df["block"] = block_of(df["t_row"], start)
    return df, acc


def flow_frame(root: Path, start: float, end: float, roles, spec: dict) -> tuple[pd.DataFrame, dict]:
    df, acc = load_kind(root, "flow", start, end, roles, spec, ("h3", "s0", "s3"))
    if df.empty:
        return df, acc
    late = late_mask(df, "h3")
    acc["late_lines_h3"] = int(late.sum())
    df["y6"] = np.where(late, np.nan, mid_at(df, "h3") - df["mid_i"].to_numpy(float))
    df["y6_sw"] = np.where(late, np.nan, mid_at(df, "s3") - mid_at(df, "s0"))
    df["status_h3"] = np.where(late, "late", df["status_h3"].astype(str))
    df["day"] = day_of(df["t_row"])
    df["block"] = block_of(df["t_row"], start)
    df["rv_missing"] = (~np.isfinite(df["zRV"].to_numpy(float))).astype(int)
    df["zRV"] = np.nan_to_num(df["zRV"].to_numpy(float))
    return df, acc


# --- estimator wrapper (rule L10) ----------------------------------------------------------------------------------------


def fit(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, sign: int, **kw) -> dict:
    """LT3's expanding-past ``fit`` with the event p on t with G_event - 1 df, then p = max(that, p_two-way, p_day on t
    with G_day - 1 df) and the conservative CI widened to include beta +- 1.96 SE_two-way (LIVE_TESTS_4.md 1.7)."""
    r = la3.fit(df, y, term, controls, sign=sign, ev_t_ref=True, **kw)
    if r.get("testable"):
        r["p"] = max(float(r["p"]), float(r.get("p_twoway", 1.0)))
        lo, hi = r["ci95_cons"]
        r["ci95_cons"] = [min(lo, r["beta"] - 1.96 * r["se_twoway"]), max(hi, r["beta"] + 1.96 * r["se_twoway"])]
        r["p_rule"] = "max(p_event t on G_event-1, p_two-way event x day, p_day t on G_day-1)"
    return r


def _pop(df: pd.DataFrame, population: str) -> pd.DataFrame:
    return df[df["sports"] == 0] if population == "non_sports" else df[df["sports"] >= 0]


def _family_share(df: pd.DataFrame, ok) -> float | None:
    fam = df.loc[ok, "skey"].astype(str).value_counts() if len(df) and "skey" in df else pd.Series(dtype=int)
    return float(fam.iloc[0] / fam.sum()) if len(fam) else None


def _sub_fit(sub: pd.DataFrame, y: str, term: str, ctrl: list[str], sign: int, seed: int) -> dict:
    sub = sub.reset_index(drop=True)
    r = fit(sub, sub[y].to_numpy(float), term, ctrl, sign=sign, seed=seed, n_boot=200)
    return {"beta": r.get("beta"), "p": r.get("p"), "n": r.get("n")}


def _common(res: dict, pop: pd.DataFrame, prim: dict, acc: dict) -> None:
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    res["top_family_share"] = _family_share(pop, ok) if len(ok) else None
    res["late_loss_share"] = acc.get("late_loss_share", 0.0)


# --- Freedman-Lane permutation gate (R1 finding 7) -------------------------------------------------------------------------


def fl_perm_gate(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, sign: int, strata: np.ndarray, draws: int,
                 seed: int, min_stratum: int, group: str = "market_id", order: str = "t_row") -> dict:
    """Freedman-Lane permutation gate (LIVE_TESTS_4.md 13.R1 finding 7). After expanding-past demeaning of the term and the
    controls (once, on the real labels), the target's residuals from the REDUCED model (target on the controls) are
    permuted within strata with >= ``min_stratum`` rows and added back to the reduced fit; the full model is refitted.
    Unlike LT3's ``perm_gate`` (which permutes the label and so breaks its correlation with the controls), the null keeps the
    label-control correlation. p_perm = (1 + #{sign * draw >= sign * real}) / (1 + draws) < 0.05 passes."""
    X = la3.demean(df, [term, *controls], group, order, "expanding")
    yv = np.asarray(y, float)
    ok = np.isfinite(yv) & np.all(np.isfinite(X.to_numpy()), axis=1)
    if ok.sum() < 10:
        return {"testable": False, "passes": False, "reason": "fewer than 10 rows"}
    Z = X[controls].to_numpy()[ok] if controls else np.zeros((int(ok.sum()), 0))
    xt = la3._partial(Z, X[term].to_numpy()[ok])
    e = la3._partial(Z, yv[ok])  # reduced-model residuals
    sxx = float(xt @ xt)
    if sxx <= 1e-18:
        return {"testable": False, "passes": False, "reason": "no residual variation in the term"}
    real = float(xt @ e / sxx)
    codes = pd.factorize(pd.Series(np.asarray(strata)[ok]).astype(str))[0]
    perm_rows = np.bincount(codes)[codes] >= min_stratum
    by_code = np.argsort(codes, kind="mergesort")
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(draws):
        shuf = np.lexsort((rng.random(len(codes)), codes))
        ep = e.copy()
        ep[by_code] = e[shuf]
        ep[~perm_rows] = e[~perm_rows]
        b = float(xt @ ep / sxx)
        ge += int(sign * b >= sign * real)
    p = (1 + ge) / (1 + draws)
    return {"testable": True, "real": real, "p_perm": p, "passes": bool(p < 0.05), "draws": draws, "method": "Freedman-Lane",
            "share_rows_permuted": float(perm_rows.mean())}


def strata_of(df: pd.DataFrame, stratum: str | None) -> np.ndarray:
    """Market x UTC day, or the pre-declared fallback market x two-day block (spec ``perm_stratum``, fixed by the census)."""
    key = df["block"] if stratum == "block2" else df["day"]
    return (df["market_id"].astype(str) + "|" + key.astype(str)).to_numpy()


def _gate_fl(pop: pd.DataFrame, y, term: str, ctrl: list[str], sign: int, spec: dict, name: str, prim: dict) -> dict:
    if not prim.get("testable"):
        return {"testable": False, "passes": False}
    g = spec["gates"]
    st = spec[name.lower()].get("perm_stratum") or "day"
    r = fl_perm_gate(pop, y, term, ctrl, sign=sign, strata=strata_of(pop, st), draws=g["draws"], seed=spec["seeds"][f"{name}_gate"],
                     min_stratum=g["perm_min_stratum"])
    r["stratum"] = st
    return r


def _excl(df: pd.DataFrame, spec_t: dict) -> pd.DataFrame:
    fam = spec_t.get("exclude_family") or ""
    return df[df["skey"].astype(str) != fam] if fam else df


# --- E020 ----------------------------------------------------------------------------------------------------------------


def e020(df: pd.DataFrame, acc: dict, spec: dict) -> dict:
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd, e, lab = spec["seeds"], spec["e020"], spec["labels"]
    os_ = df[(df["cls"] == "quote_only") & (df["geom"] == "one_sided")]
    res: dict = {"load": acc, "counts": {"lines": len(df), "one_sided_quote_only": len(os_), "sidecar_missing": int((os_["sports"] == -1).sum()),
                                         "tick_flip_or_unknown": int((os_["tick_ok"] != 1).sum()), "neither": int((~os_["arrival"].isin([0, 1])).sum())}}
    full = _pop(os_[(os_["tick_ok"] == 1) & os_["arrival"].isin([0, 1])], e["population"]).reset_index(drop=True)
    full["AR"] = full["arrival"].astype(int)
    res["counts"]["off_common_support"] = int((full["common"] != 1).sum())
    pop = _excl(full[full["common"] == 1], e).reset_index(drop=True)  # R1 finding 1: common-support primary
    y = pop["r"].to_numpy(float)
    res["attrition"] = attrition(pop["status_h1"].to_numpy(), pop["AR"].to_numpy(), (1, 0), lab["attrition_pp"])
    prim = fit(pop, y, "AR", CONTROLS_E020, sign=+1, seed=sd["E020"])
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    cnt = {"arrivals": int((pop["AR"].to_numpy()[ok] == 1).sum()) if len(ok) else 0, "cancellations": int((pop["AR"].to_numpy()[ok] == 0).sum()) if len(ok) else 0,
           "events": int(pop.loc[ok, "event_id"].nunique()) if len(ok) else 0, "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["available"] = floors_ok(cnt, e["floors"])
    res["primary"] = strip(prim)
    res["gate"] = _gate_fl(pop, y, "AR", CONTROLS_E020, +1, spec, "E020", prim)
    res["sensitivity_full_population"] = strip(fit(full, full["r"].to_numpy(float), "AR", CONTROLS_E020, sign=+1, seed=sd["E020"] + 10, n_boot=200))
    res["sensitivity_series_family_clusters"] = strip(fit(pop, y, "AR", CONTROLS_E020, sign=+1, ev="skey", seed=sd["E020"] + 11, n_boot=200))
    res["M1_sweep"] = strip(fit(pop, pop["r_sw"].to_numpy(float), "AR", CONTROLS_E020, sign=+1, seed=sd["E020"] + 1, n_boot=200))
    res["M2_skip"] = strip(fit(pop, pop["r_skip"].to_numpy(float), "AR", CONTROLS_E020, sign=-1, seed=sd["E020"] + 2, n_boot=200))
    res["S1_mid_target"] = strip(fit(pop, pop["c"].to_numpy(float), "AR", CONTROLS_E020, sign=+1, seed=sd["E020"] + 3, n_boot=200))
    if {"bsz1_s0", "asz1_s0", "minord_s0"} <= set(pop.columns):
        sz = np.where(pop["side_moved"].astype(str) == "bid", pop["bsz1_s0"].to_numpy(float), pop["asz1_s0"].to_numpy(float))
        real = sz >= 2.0 * pop["minord_s0"].to_numpy(float)
        res["S2_sized"] = {f"{n}_{w}": gross(pop["r"][(pop["AR"] == a).to_numpy() & m], pop["event_id"][(pop["AR"] == a).to_numpy() & m])
                           for n, a in (("arrival", 1), ("cancellation", 0)) for w, m in (("real", real), ("dust", ~real))}
    res["S3_reward"] = {f"rew_{v}": _sub_fit(pop[pop["rew"] == v], "r", "AR", [c for c in CONTROLS_E020 if c != "rew"], +1, sd["E020"] + 4) for v in (0, 1)}
    ax = pop["x"].abs()
    res["S4_dose"] = {n: _sub_fit(pop[m.to_numpy()], "r", "AR", CONTROLS_E020, +1, sd["E020"] + 5)
                      for n, m in (("absx_1_2c", ax < 0.02), ("absx_2_5c", (ax >= 0.02) & (ax < 0.05)), ("absx_ge_5c", ax >= 0.05))}
    sp = os_[(os_["tick_ok"] == 1) & (os_["common"] == 1) & os_["arrival"].isin([0, 1]) & (os_["sports"] == 1)].reset_index(drop=True)
    sp["AR"] = sp["arrival"].astype(int)
    res["S5_sports_arm"] = _sub_fit(sp, "r", "AR", CONTROLS_E020, +1, sd["E020"] + 6)
    res["S6_counts"] = {f"{a}|{s}": int(v) for (a, s), v in pop.groupby(["AR", "side_moved"]).size().items()}
    with np.errstate(invalid="ignore"):
        jt = (_col(pop, "ask_h1") - _col(pop, "bid_h1")) <= spec["eligibility"]["spread_max"] + 1e-12
    res["sensitivity_j_tight"] = strip(fit(pop, np.where(jt, y, np.nan), "AR", CONTROLS_E020, sign=+1, seed=sd["E020"] + 7, n_boot=200))
    # spread_k - spread_{k-1} = -/+ 2|x| is the label itself for a one-sided move: with both spreads controlled the label is
    # nearly collinear (reported only, LIVE_TESTS_4.md section 2)
    res["sensitivity_spread_k_control"] = strip(fit(pop, y, "AR", ["spread_k", *CONTROLS_E020], sign=+1, seed=sd["E020"] + 9, n_boot=200))
    if res["attrition"]["triggered"]:
        res["attrition"]["bounds"] = lee_bounds(pop, y, pop["AR"].to_numpy(), (1, 0), res["attrition"],
                                                lambda d, yy: fit(d, yy, "AR", CONTROLS_E020, sign=+1, seed=sd["E020"], n_boot=200))
    can = pop[(pop["AR"] == 0) & (pop["x"].abs() >= e["econ_min_abs_x"]) & _two(pop, "h1")]
    res["economics"] = {"fade_cancellations_reported": econ(paper_taker(can["bid_k"], can["ask_k"], can["bid_h1"], can["ask_h1"], can["fee_rate"], can["fee_exp"],
                                                                        -np.sign(can["x"])), can["event_id"].to_numpy(), can["day"].to_numpy(), sd["E020"] + 8),
                        "maker_gross_r_by_class": {str(a): gross(g_["r"], g_["event_id"]) for a, g_ in pop.groupby("AR")}}
    _common(res, pop, prim, acc)
    return res


def e020_labels(res: dict, v: dict, spec: dict) -> list:
    out = []
    if str(v.get("verdict", "")).startswith("Supported"):
        b = (res.get("primary") or {}).get("beta")
        if not check_fraction(b, res.get("M1_sweep"), +1, True, spec["labels"]["fraction"]):
            out.append("Gamma-quote mechanics")
        m2 = res.get("M2_skip") or {}
        if m2.get("testable") and m2.get("beta") is not None and m2["beta"] < 0 and (m2.get("p") or 1.0) < 0.05:
            out.append("transient (spread-reversion mechanics)")
    return out


# --- E021 ----------------------------------------------------------------------------------------------------------------


def e021(df: pd.DataFrame, acc: dict, spec: dict) -> dict:
    """E021 after R1 (finding 3): the counted primary is the persistence beyond the first pass, ``c_skip = sign(x)
    (mid_{k+3} - mid_{k+1})``; the 2 h ``c`` (the bounce clock) is the mechanism reading M2. Units whose 2 h trade count
    is truncated by a full page are excluded and counted."""
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd, e, lab = spec["seeds"], spec["e021"], spec["labels"]
    tm = df[df["cls"] == "traded"]
    res: dict = {"load": acc, "counts": {"lines": len(df), "traded": len(tm),
                                         "clock": {str(a): int(b) for a, b in tm["clock"].value_counts().items()},
                                         "band": {str(a): int(b) for a, b in tm["band"].value_counts().items()}}}
    res["unclocked_truncated_share"] = float((tm["clock"] == "unclocked_truncated").mean()) if len(tm) else 0.0
    clocked = _pop(tm[tm["clock"] == "ok"], e["population"])
    banded = clocked[clocked["band"].isin(["fresh", "settled"])]
    res["n2h_truncated_share"] = float((banded["n2h_truncated"] == 1).mean()) if len(banded) else 0.0
    pop = _excl(banded[banded["n2h_truncated"] == 0], e).reset_index(drop=True)
    pop["F"] = (pop["band"] == "fresh").astype(int)
    y = pop["c_skip"].to_numpy(float)
    res["attrition"] = attrition(pop["status_h3"].to_numpy(), pop["F"].to_numpy(), (1, 0), lab["attrition_pp"])
    prim = fit(pop, y, "F", CONTROLS_E021, sign=-1, seed=sd["E021"])
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    cnt = {"fresh": int((pop["F"].to_numpy()[ok] == 1).sum()) if len(ok) else 0, "settled": int((pop["F"].to_numpy()[ok] == 0).sum()) if len(ok) else 0,
           "events": int(pop.loc[ok, "event_id"].nunique()) if len(ok) else 0, "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["available"] = floors_ok(cnt, e["floors"])
    res["primary"] = strip(prim)
    res["gate"] = _gate_fl(pop, y, "F", CONTROLS_E021, -1, spec, "E021", prim)
    res["M1_sweep_skip"] = strip(fit(pop, pop["c_skip_sw"].to_numpy(float) if "c_skip_sw" in pop else np.full(len(pop), np.nan), "F", CONTROLS_E021,
                                     sign=-1, seed=sd["E021"] + 1, n_boot=200))
    res["M2_two_hour_bounce_clock"] = strip(fit(pop, pop["c"].to_numpy(float), "F", CONTROLS_E021, sign=-1, seed=sd["E021"] + 2, n_boot=200))
    res["M3_two_hour_sweep"] = strip(fit(pop, pop["c_sw"].to_numpy(float), "F", CONTROLS_E021, sign=-1, seed=sd["E021"] + 3, n_boot=200))
    cl = clocked[clocked["n2h_truncated"] == 0].reset_index(drop=True)
    res["S1_log_age_dose"] = strip(fit(cl, cl["c_skip"].to_numpy(float), "log_age", CONTROLS_E021, sign=+1, seed=sd["E021"] + 4, n_boot=200))
    res["S2_parallel_only"] = _sub_fit(pop[pop["g_par"] == 1], "c_skip", "F", CONTROLS_E021[3:], -1, sd["E021"] + 5)
    res["S3_arms"] = {n: _sub_fit(pop[pop["sports"] == v], "c_skip", "F", CONTROLS_E021, -1, sd["E021"] + 6) for n, v in (("non_sports", 0), ("sports", 1))}
    res["S4_6h_from_origin"] = strip(fit(pop, pop["c6"].to_numpy(float), "F", CONTROLS_E021, sign=-1, seed=sd["E021"] + 7, n_boot=200))
    res["S5_series_family_clusters"] = strip(fit(pop, y, "F", CONTROLS_E021, sign=-1, ev="skey", seed=sd["E021"] + 9, n_boot=200))
    if res["attrition"]["triggered"]:
        res["attrition"]["bounds"] = lee_bounds(pop, y, pop["F"].to_numpy(), (1, 0), res["attrition"],
                                                lambda d, yy: fit(d, yy, "F", CONTROLS_E021, sign=-1, seed=sd["E021"], n_boot=200))
    fr = pop[(pop["F"] == 1) & (pop["x"].abs() >= e["econ_min_abs_x"]) & _two(pop, "s0") & _two(pop, "s1")]
    res["economics"] = {"fade_fresh_reported": econ(paper_taker(fr["sbid_s0"], fr["sask_s0"], fr["sbid_s1"], fr["sask_s1"], fr["fee_rate"], fr["fee_exp"],
                                                                -np.sign(fr["x"])), fr["event_id"].to_numpy(), fr["day"].to_numpy(), sd["E021"] + 8),
                        "note": "entry at the sweep-1 touch of pass k (before the sample receipt): optimistic, disclosed",
                        "maker_gross_c_skip_by_band": {str(a): gross(g_["c_skip"], g_["event_id"]) for a, g_ in clocked.groupby("band")}}
    _common(res, pop, prim, acc)
    return res


def e021_labels(res: dict, v: dict, spec: dict) -> list:
    out = []
    if str(v.get("verdict", "")).startswith("Supported"):
        b = (res.get("primary") or {}).get("beta")
        if not check_fraction(b, res.get("M1_sweep_skip"), -1, True, spec["labels"]["fraction"]):
            out.append("Gamma-quote mechanics")
    cap = spec["labels"]["unclocked_truncated_share"]
    if (res.get("unclocked_truncated_share") or 0.0) > cap:
        out.append(f"coverage-limited ({res['unclocked_truncated_share']:.1%} unclocked-truncated)")
    if (res.get("n2h_truncated_share") or 0.0) > cap:
        out.append(f"coverage-limited ({res['n2h_truncated_share']:.1%} n2h-truncated, excluded)")
    return out


def e022(df: pd.DataFrame, acc: dict, spec: dict) -> dict:
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd, e, hs, lab = spec["seeds"], spec["e022"], spec["hollow"], spec["labels"]
    res: dict = {"load": acc, "counts": {"lines": len(df), "sweep_not_two_sided": int((df["s_two0"] != 1).sum()),
                                         "h_undefined": int((~np.isfinite(df["h"].to_numpy(float))).sum())}}
    pop = _excl(_pop(df[(df["s_two0"] == 1) & np.isfinite(df["zh"].to_numpy(float))], e["population"]), e).reset_index(drop=True)
    y = pop["c_sw"].to_numpy(float)
    prim = fit(pop, y, "zh", CONTROLS_E022, sign=-1, seed=sd["E022"])
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    cnt = {"units": int(ok.sum()), "events": int(pop.loc[ok, "event_id"].nunique()) if len(ok) else 0, "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["available"] = floors_ok(cnt, e["floors"])
    res["primary"] = strip(prim)
    res["gate"] = _gate_fl(pop, y, "zh", CONTROLS_E022, -1, spec, "E022", prim)
    m1c = ["log_L", *CONTROLS_E022[2:]]
    res["sensitivity_depth_pass_k"] = strip(fit(pop, y, "zh", ["log1p_D", *CONTROLS_E022[2:]], sign=-1, seed=sd["E022"] + 8, n_boot=200))
    res["sensitivity_series_family_clusters"] = strip(fit(pop, y, "zh", CONTROLS_E022, sign=-1, ev="skey", seed=sd["E022"] + 9, n_boot=200))
    nos, fil = acc.get("nosweep_files", 0), acc.get("files", 0)
    res["sweep_missing_share"] = nos / (nos + fil) if (nos + fil) else 0.0
    res["M1_thin_book"] = strip(fit(pop, y, "zh", m1c, sign=-1, seed=sd["E022"] + 1, n_boot=200))
    res["M2_skip"] = strip(fit(pop, pop["c_skip"].to_numpy(float), "zh", CONTROLS_E022, sign=-1, seed=sd["E022"] + 2, n_boot=200))
    lo_cut, hi_cut = (hs.get("h_cuts") or [None, None])[:2]
    if not _nanlike(lo_cut) and not _nanlike(hi_cut):
        h = pop["h"].to_numpy(float)
        tb = pop[(h > hi_cut) | (h <= lo_cut)].copy()
        tb["TOP"] = (tb["h"] > hi_cut).astype(int)
        res["T_tercile"] = strip(fit(tb.reset_index(drop=True), tb["c_sw"].to_numpy(float), "TOP", CONTROLS_E022, sign=-1, seed=sd["E022"] + 3, n_boot=200))
        top = pop[(h > hi_cut) & (pop["x"].abs() >= e["econ_min_abs_x"]).to_numpy() & _two(pop, "s1")]
        res["economics"] = {"fade_top_tercile_reported": econ(paper_taker(top["sbid0"], top["sask0"], top["sbid_s1"], top["sask_s1"], top["fee_rate"], top["fee_exp"],
                                                                         -np.sign(top["x"])), top["event_id"].to_numpy(), top["day"].to_numpy(), sd["E022"] + 8),
                            "maker_gross_c_sw_by_tercile": {n: gross(pop["c_sw"][m], pop["event_id"][m]) for n, m in
                                                            (("bottom", h <= lo_cut), ("middle", (h > lo_cut) & (h <= hi_cut)), ("top", h > hi_cut))}}
    else:
        res["T_tercile"], res["economics"] = None, {"verdict": "not computed (census cuts not filled)"}
    zc = hs["zh"]
    if not _nanlike(zc.get("scale")) and zc.get("scale"):
        p1 = pop.assign(zh1=(pop["h1c"] - zc["centre"]) / zc["scale"])
        res["S1_depth_1c"] = strip(fit(p1, y, "zh1", CONTROLS_E022, sign=-1, seed=sd["E022"] + 4, n_boot=200))
    res["S2_reward"] = {f"rew_{v}": _sub_fit(pop[pop["rew"] == v], "c_sw", "zh", CONTROLS_E022, -1, sd["E022"] + 7) for v in (0, 1)}
    sp = df[(df["s_two0"] == 1) & np.isfinite(df["zh"].to_numpy(float)) & (df["sports"] == 1)]
    res["S3_sports_arm"] = _sub_fit(sp, "c_sw", "zh", CONTROLS_E022, -1, sd["E022"] + 5)
    res["S4_gamma_target_reported"] = strip(fit(pop, pop["c_gamma"].to_numpy(float), "zh", CONTROLS_E022, sign=-1, seed=sd["E022"] + 6, n_boot=200))
    med = np.nanmedian(pop["zh"].to_numpy(float)) if len(pop) else np.nan
    half = np.where(pop["zh"].to_numpy(float) >= med, "upper", "lower")
    res["attrition"] = attrition(pop["status_s1"].to_numpy(), half, ("upper", "lower"), lab["attrition_pp"])
    if res["attrition"]["triggered"]:
        res["attrition"]["bounds"] = lee_bounds(pop, y, half, ("upper", "lower"), res["attrition"],
                                                lambda d, yy: fit(d, yy, "zh", CONTROLS_E022, sign=-1, seed=sd["E022"], n_boot=200))
    _common(res, pop, prim, acc)
    return res


def e022_labels(res: dict, v: dict, spec: dict) -> list:
    out = []
    if str(v.get("verdict", "")).startswith("Supported"):
        b = (res.get("primary") or {}).get("beta")
        if not check_fraction(b, res.get("M2_skip"), -1, True, spec["labels"]["fraction"]):  # R1 finding 5: binding
            out.append("transient impact (no persistence beyond one pass)")
    if (res.get("sweep_missing_share") or 0.0) > spec["labels"]["sweep_missing_share"]:  # R1 finding 11
        out.append(f"sweep-missing ({res['sweep_missing_share']:.1%} of origin passes)")
    return out


def flow_controls(name: str, lag: bool = False) -> tuple[str, str, list[str]]:
    mod = {"E023": "zOP", "E024": "zC"}[name]
    x, m, ctrl = la3.flow_controls(mod, lag)
    ctrl = [f"{x}*abs_dev", *ctrl]  # R1 finding 9: longshot buying (x6 x |mid - 0.5|)
    if name == "E024":
        s = "_l30" if lag else ""
        ctrl = [f"{x}*zW{s}", f"zW{s}", f"{x}*zH{s}", f"zH{s}", *ctrl]
    return x, m, ctrl


def flow_test(df: pd.DataFrame, acc: dict, spec: dict, name: str) -> dict:
    if df.empty:
        return {"available": False, "reason": "no lines", "load": acc}
    sd, f, g = spec["seeds"], spec["flow"], spec["gates"]
    sign = DIRECTION[name]
    mod = {"E023": "OP", "E024": "C"}[name]
    cap = f.get("vol24_cap")
    cap = float("inf") if _nanlike(cap) else float(cap)
    base = df[(df["tight_i"] == 1) & (df["end_ok_7h"] == 1)]
    vpop = base[np.isfinite(base["vol24_i"].to_numpy(float)) & (base["vol24_i"].to_numpy(float) <= cap)]
    trunc = vpop["cov6"] == 0
    res: dict = {"load": acc, "counts": {"lines": len(df), "V*_population": len(vpop), "truncated": int(trunc.sum()),
                                         "truncated_share": float(trunc.mean()) if len(vpop) else None}}
    cov = vpop[(vpop["cov6"] == 1) & (np.nan_to_num(vpop["N6"].to_numpy(float)) > 0)]
    if name == "E024":
        cov = cov[np.nan_to_num(cov["Nsig"].to_numpy(float)) >= f["min_rows_C"]]
    pop = cov[np.isfinite(cov[f"z{mod}"].to_numpy(float))].copy()
    res["counts"]["moderator_missing"] = len(cov) - len(pop)
    x, m, ctrl = flow_controls(name)
    term = f"{x}*{m}"
    pop = add_products(pop, [term, *ctrl]).reset_index(drop=True)
    y = pop["y6"].to_numpy(float)
    prim = fit(pop, y, term, [m, *ctrl], sign=sign, seed=sd[name])
    ok = prim.get("_mask", np.zeros(len(pop), bool))
    cnt = {"units": int(ok.sum()), "events": int(pop.loc[ok, "event_id"].nunique()) if len(ok) else 0, "days": int(prim.get("n_day") or 0)}
    res["counts"]["fit"] = cnt
    res["counts"]["by_category"] = {str(k): int(v) for k, v in pop.loc[ok, "sports"].value_counts().items()} if len(ok) else {}
    res["available"] = floors_ok(cnt, spec[name.lower()]["floors"])
    res["primary"] = strip(prim)
    res["gate"] = la3.donor_gate(pop, y, x, m, ctrl, sign=sign, draws=g["draws"], seed=sd[f"{name}_gate"], min_units=g["donor_min_units"],
                                 min_sep_s=g["donor_min_sep_s"], min_donors=g["donor_min_donors"]) if prim.get("testable") else {"testable": False, "passes": False}
    xl, ml, cl = flow_controls(name, lag=True)
    pl = add_products(pop.copy(), [f"{xl}*{ml}", *cl])
    res["M1_lag30"] = strip(fit(pl, y, f"{xl}*{ml}", [ml, *cl], sign=sign, seed=sd[name] + 1, n_boot=200))
    res["M2_sweep"] = strip(fit(pop, pop["y6_sw"].to_numpy(float), term, [m, *ctrl], sign=sign, seed=sd[name] + 2, n_boot=200))
    res["sensitivity_two_day_blocks"] = strip(fit(pop, y, term, [m, *ctrl], sign=sign, time="block", seed=sd[name] + 3, n_boot=200))
    res["S_fe"] = strip(fit(pop, y, term, [m, *ctrl], sign=sign, estimator="fe", seed=sd[name] + 4, n_boot=200))
    if name == "E023":
        res["S1_two_leg_open_minus_close"] = strip(fit(pop, y, "o6s", ctrl, sign=+1, seed=sd[name] + 5, n_boot=200))
        p2 = pop.copy()
        p2["OPno_c"] = p2["OPno"] - np.nanmean(p2["OPno"].to_numpy(float)) if len(p2) else np.nan
        p2 = add_products(p2, ["x6*OPno_c"])
        res["S2_bet_against_opener"] = strip(fit(p2, y, "x6*OPno_c", ["OPno_c", m, *ctrl], sign=+1, seed=sd[name] + 6, n_boot=200))
    else:
        p2 = pop.copy()
        hh = p2["HHI"].to_numpy(float)
        p2["zHHI"] = (hh - np.nanmean(hh)) / (np.nanstd(hh) or 1.0) if len(p2) else np.nan
        p2 = add_products(p2, ["x6*zHHI"])
        res["S1_hhi"] = strip(fit(p2, y, "x6*zHHI", ["zHHI", *ctrl], sign=+1, seed=sd[name] + 5, n_boot=200))
    res["by_category"] = {("sports" if c else "non_sports"): _sub_fit(pop[pop["sports"] == c], "y6", term, [m, *ctrl], sign, sd[name] + 7) for c in (0, 1)}
    if res["counts"]["truncated_share"] is not None and res["counts"]["truncated_share"] > f["trunc_label_share"]:
        half = pop[pop["vol24_i"] <= cap / 2.0].reset_index(drop=True)
        res["sensitivity_half_cap"] = strip(fit(half, half["y6"].to_numpy(float), term, [m, *ctrl], sign=sign, seed=sd[name] + 8, n_boot=200))
    med = np.nanmedian(pop[m].to_numpy(float)) if len(pop) else np.nan
    hc = np.where(pop[m].to_numpy(float) >= med, "upper", "lower")
    res["attrition"] = attrition(pop["status_h3"].to_numpy(), hc, ("upper", "lower"), spec["labels"]["attrition_pp"])
    if res["attrition"]["triggered"]:
        res["attrition"]["bounds"] = lee_bounds(pop, y, hc, ("upper", "lower"), res["attrition"],
                                                lambda d, yy: fit(d, yy, term, [m, *ctrl], sign=sign, seed=sd[name], n_boot=200))
    ec = f["econ"]
    cut = ec.get(f"{mod}_upper_cut")
    if not _nanlike(cut):
        cell = pop[(pop[mod] >= cut) & (pop["imb6"].abs() >= ec["min_abs_imb"])]
        d = np.sign(cell["imb6"].to_numpy(float))
        gm = d * (mid_at(cell, "h3") - cell["mid_i"].to_numpy(float))
        res["economics"] = {"follow_cell": econ(paper_taker(cell["bid_i"], cell["ask_i"], cell["bid_h3"], cell["ask_h3"], cell["fee_rate"], cell["fee_exp"], d),
                                                cell["event_id"].to_numpy(), cell["day"].to_numpy(), sd[name] + 9),
                            "gross_cell": gross(gm, cell["event_id"])}
    else:
        res["economics"] = {"verdict": "not computed (census cut not filled)"}
    res["late_loss_share"] = acc.get("late_loss_share", 0.0)
    return res


def flow_labels(res: dict, v: dict, spec: dict, name: str) -> list:
    out = []
    b = (res.get("primary") or {}).get("beta")
    if str(v.get("verdict", "")).startswith("Supported") and not check_fraction(b, res.get("M1_lag30"), DIRECTION[name], True, spec["labels"]["fraction"]):
        out.append("possibly mechanical (stale-mid catch-up)")
    ts = (res.get("counts") or {}).get("truncated_share")
    if ts is not None and ts > spec["flow"]["trunc_label_share"]:
        out.append("coverage-limited")
    return out


# --- the single analysis -------------------------------------------------------------------------------------------------


def trial_record(res: dict) -> dict:
    """The single counted trials line (battery2 KIND_RULES 'live_tests4', n_tests = k). Gate draws, secondaries,
    mechanism readings, economics and censuses are not counted (LIVE_TESTS_4.md 1.11)."""
    ks = (res.get("holm") or {}).get("tests") or []
    return {"kind": TRIAL_KIND, "label": "PROSPECTIVE", "evidence_role": lt.ROLE_CONF, "experiments": list(ks),
            "n_tests": len(ks), "n_primary": len(ks), "holm": res.get("holm"),
            "verdicts": {k: (res.get(k) or {}).get("verdict") for k in ks},
            "spec_sha256": res.get("spec_sha"), "code_sha256": res.get("code_sha256"), "window": res.get("window")}


def underpowered_ref(t: str, spec: dict) -> float:
    if t in ("E020", "E021"):
        return float(spec[t.lower()]["floor_c"])
    if t == "E022":
        gap = spec["hollow"].get("gap")
        return float(spec["e022"]["floor_c"]) / (float(gap) if not _nanlike(gap) and gap else 2.2)
    return float(spec[t.lower()]["underpowered_ref"])


def is_material(t: str, r: dict, spec: dict) -> bool:
    if t in ("E020", "E021"):
        b = (r.get("primary") or {}).get("beta")
        return b is not None and DIRECTION[t] * b >= spec[t.lower()]["floor_c"]
    if t == "E022":
        b = (r.get("T_tercile") or {}).get("beta")
        return b is not None and DIRECTION[t] * b >= spec["e022"]["floor_c"]
    gm = ((r.get("economics") or {}).get("gross_cell") or {}).get("mean")
    return gm is not None and gm >= spec[t.lower()]["floor_gross_c"]


def analyze(root: Path = lt.OUT_ROOT, *, start_utc: str = lt.REGISTERED_UTC, end_utc: str = lt.END_UTC, spec: dict | None = None,
            roles: tuple[str, ...] = (lt.ROLE_CONF,), force: bool = False) -> dict:
    """The single registered analysis. Refuses before ANALYSIS_NOT_BEFORE unless ``force`` (tests only) and refuses a
    pinned spec whose code hashes or census values are unfilled or do not match."""
    if not force and lt.now_ts() < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        raise RuntimeError(f"analysis refused before {lt.ANALYSIS_NOT_BEFORE}")
    spec = spec or lt.load_spec()
    cc = code_check(spec)
    s, e = lt.epoch(start_utc), lt.epoch(end_utc)
    ktests = list(spec.get("k_tests") or TESTS)
    k = len(ktests)
    mv, macc = move_frame(root, s, e, roles, spec)
    ck, cacc = clock_frame(root, s, e, roles, spec)
    hl, hacc = hollow_frame(root, s, e, roles, spec)
    fl, facc = flow_frame(root, s, e, roles, spec)
    res = {"E020": e020(mv, macc, spec), "E021": e021(ck, cacc, spec), "E022": e022(hl, hacc, spec),
           "E023": flow_test(fl, facc, spec, "E023"), "E024": flow_test(fl, facc, spec, "E024")}
    pv = {t: verdict(res[t].get("primary") or {}, res[t].get("gate"), res[t].get("available", False), None, DIRECTION[t], GATE_LABEL[t])["p_for_holm"]
          for t in ktests}
    hp = bd.holm(pv)
    lab = spec["labels"]
    for t in TESTS:
        r = res[t]
        if t not in ktests:
            r["verdict"] = {"verdict": "dropped before registration (census gate); not in the Holm family"}
            continue
        v = verdict(r.get("primary") or {}, r.get("gate"), r.get("available", False), hp[t], DIRECTION[t], GATE_LABEL[t])
        r["holm_p"] = hp[t]
        if t in ("E023", "E024"):
            labels: list = flow_labels(r, v, spec, t)
        else:
            labels = {"E020": e020_labels, "E021": e021_labels, "E022": e022_labels}[t](r, v, spec)
        if is_material(t, r, spec):
            labels.append("material")
        prim = r.get("primary") or {}
        if str(v.get("verdict", "")) == "Inconclusive" and underpowered(prim, k, underpowered_ref(t, spec)):
            labels.append("underpowered")
        att = r.get("attrition") or {}
        if att.get("triggered"):
            labels.append(f"attrition-differential ({att['diff'] * 100:+.1f} pp)")
        if (r.get("late_loss_share") or 0.0) > lab["late_loss_share"]:
            labels.append(f"late-loss ({r['late_loss_share']:.1%} of origin files refused late)")
        if (r.get("top_family_share") or 0.0) > lab["series_concentration"]:
            labels.append(f"series-concentrated ({r['top_family_share']:.0%})")
        labels.append(cc["label"])
        r["verdict"] = attach(v, labels)
    res["holm"] = {"tests": ktests, "m": k, "p_raw": pv, "p_holm": hp, "alpha": 0.05, "one_sided": True}
    res["spec_sha"] = spec["_sha256"]
    res["code_sha256"] = cc["current"]
    res["code_check"] = cc
    res["window"] = [start_utc, end_utc]
    res["roles"] = list(roles)
    return bd._clean(res)


# --- simulated-null size of the gates (LIVE_TESTS_4.md 1.8; run on the code to be pinned) ------------------------------


def sim_cont_world(rng: np.random.Generator, *, n_mkt: int = 60, n_t: int = 40, effect: float = 0.0) -> tuple[pd.DataFrame, np.ndarray]:
    """A continuous-label panel with NO effect (``effect`` = 0): persistent market level of the label and AR(0.5) within
    market, market-specific target levels (what expanding-past demeaning must absorb)."""
    rows = []
    for m in range(n_mkt):
        lvl, lab, ylvl = rng.normal(0, 1), 0.0, rng.normal(0, 0.01)
        for i in range(n_t):
            lab = 0.5 * lab + rng.normal(0, 1)
            z = lvl + lab
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "zh": z,
                         "c1": rng.normal(), "y": ylvl + effect * z + rng.normal(0, 0.04)})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def sim_corr_label_world(rng: np.random.Generator, *, corr: float = 0.7, binary: bool = False, n_mkt: int = 60, n_t: int = 40,
                         effect: float = 0.0) -> tuple[pd.DataFrame, np.ndarray]:
    """A label correlated ``corr`` with a control ``c1`` that has a REAL effect on the target, and no label effect
    (``effect`` = 0): the case where permuting the raw label breaks the label-control correlation (R1 finding 7)."""
    rows = []
    for m in range(n_mkt):
        lvl = rng.normal(0, 0.01)
        for i in range(n_t):
            c1 = rng.normal()
            z = corr * c1 + math.sqrt(1 - corr**2) * rng.normal()
            lab = float(z > 0) if binary else z
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 3}", "t_row": i * 7200.0, "day": str(i // 12), "L": lab, "c1": c1,
                         "y": lvl + 0.02 * c1 + effect * lab + rng.normal(0, 0.04)})
    df = pd.DataFrame(rows)
    return df, df["y"].to_numpy(float)


def sim_corr_flow_world(rng: np.random.Generator, *, n_mkt: int = 40, n_t: int = 30, corr: float = 0.4, effect: float = 0.0
                        ) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """A flow panel where a control moderator zA has a REAL moderation (0.004 per SD) and the tested moderator zM is
    correlated ``corr`` with zA but has none (``effect`` = 0); x6*zA and zA are controls, as W and H are for E024."""
    rows = []
    for m in range(n_mkt):
        la_, lm = rng.normal(0, 0.5), rng.normal(0, 0.5)
        for i in range(n_t):
            za = la_ + rng.normal(0, 1)
            zm = lm + corr * za + math.sqrt(1 - corr**2) * rng.normal(0, 1)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 2}", "t_row": i * 7200.0, "day": str(i // 12),
                         "x6": rng.normal(0, 1), "zM": zm, "zA": za, "c1": rng.normal()})
    df = pd.DataFrame(rows)
    x = df["x6"].to_numpy()
    y = 0.003 * x + 0.004 * x * df["zA"].to_numpy() + effect * x * df["zM"].to_numpy() + rng.normal(0, 0.01, len(df))
    df["x6*zA"] = df["x6"] * df["zA"]
    return df, y, ["x6", "x6*zA", "zA", "c1"]


def size_check(*, worlds: int, draws: int, seed: int, nominal: float = 0.05) -> dict:
    """Pass rate of each gate under its simulated null (ten scenarios; R1 findings 7 and 10), criterion rate <= nominal +
    1.645 sqrt(nominal (1 - nominal) / worlds). The permutation scenarios use the Freedman-Lane gate LT4 registers."""
    rng = np.random.default_rng(seed)
    lim = nominal + 1.645 * float(np.sqrt(nominal * (1 - nominal) / worlds))
    out: dict = {"worlds": worlds, "draws": draws, "seed": seed, "limit": lim, "scenarios": {}}

    def donor(df, y, others) -> bool:
        return bool(la3.donor_gate(df, y, "x6", "zM", others, sign=+1, draws=draws, seed=int(rng.integers(1 << 31)), min_units=4,
                                   min_sep_s=43200.0, min_donors=2).get("passes"))

    def perm(df, y, term) -> bool:
        return bool(fl_perm_gate(df, y, term, ["c1"], sign=+1, strata=(df["market_id"] + "|" + df["day"]).to_numpy(), draws=draws,
                                 seed=int(rng.integers(1 << 31)), min_stratum=4).get("passes"))

    scen = {
        "fl_binary_iid": lambda: perm(*la3.sim_move_world(rng), "P"),
        "fl_binary_persistent": lambda: perm(*la3.sim_move_world(rng, persistent=True), "P"),
        "fl_binary_control_corr0.7": lambda: perm(*sim_corr_label_world(rng, corr=0.7, binary=True), "L"),
        "fl_continuous_persistent": lambda: perm(*sim_cont_world(rng), "zh"),
        "fl_continuous_control_corr0.7": lambda: perm(*sim_corr_label_world(rng, corr=0.7), "L"),
        "donor_iid": lambda: donor(*la3.sim_flow_world(rng)),
        "donor_ar0.6": lambda: donor(*la3.sim_flow_world(rng, ar=0.6)),
        "donor_lifecycle": lambda: donor(*la3.sim_flow_world(rng, lifecycle=True)),
        "donor_correlated_moderator0.4": lambda: donor(*sim_corr_flow_world(rng, corr=0.4)),
        "donor_correlated_moderator0.7": lambda: donor(*sim_corr_flow_world(rng, corr=0.7)),
    }
    for name, fn in scen.items():
        rej = sum(int(fn()) for _ in range(worlds))
        out["scenarios"][name] = {"rate": rej / worlds, "ok": rej / worlds <= lim}
    out["pass"] = all(v["ok"] for v in out["scenarios"].values())
    out["code_sha256"] = lt.code_hashes()
    return out
