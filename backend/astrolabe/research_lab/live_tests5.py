# ruff: noqa: E501
"""LIVE prospective tests LT5 (docs/research_lab/LIVE_TESTS_5.md, as amended by sections 14-15). DRAFT: nothing is
registered; E-numbers are assigned at registration. Research tooling only; never trades; no network request.

This first code unit holds the counts-only pre-registration censuses (section 8) and the unit builders they share with
the future reader:

* J (CH180) jump or grind: ``path_units`` on a pass's active trade sample and captures k - 1, k;
* F (CH184) alone or with the crowd: ``family_units`` on captures k - 1, k;
* O (CH182) token-weighted overhang: ``overhang_units`` on a pass's trade sample and captures k - 12 .. k;
* H (CH181) the high-water mark: ``mark_units`` on the 00:31Z capture of a UTC day and its 96-slot look-back;
* R (CH183) the farmer's choice: ``rule_units`` on sweep 1 of passes k - 1, k and the sidecar of capture k.

Censuses read origin-side fields only: no capture, sweep or sample after the one classified, no target, no P&L. Every
opened input file is checked against a seal first (refused on any mismatch, L3). LT3/LT4 code is used only through the
vendored copies in ``live_tests5_base`` (R1 ruling 9).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast, maker_rewards, panel, trade_sample
from . import live_tests5_base as b

VERSION = "live-tests5-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = ROOT / "data-dumps" / "research_lab" / "trade_samples"
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests5"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests5_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration
REGISTERED_UTC = "2026-10-30T00:00:00Z"
END_UTC = "2026-11-20T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-11-21T12:00:00Z"
TEMPFAIL = 75
DAY_S = 86400.0
CODE_FILES = ("live_tests5.py", "live_tests5_analysis.py", "live_tests5_base.py", "bounce_decomp.py",
              # imported dependencies the censuses rely on (census code check finding 7)
              "maker_rewards.py", "panel.py", "trade_sample.py", "cb17_census.py", "cb13_label.py", "economics.py", "forecast.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)
X6_SCALE = 0.85782  # E013's x6 = clip(imb6, -1, 1) / 0.85782 (LIVE_TESTS_3.md 3, copied as a constant)

SNAP_COLS = [*b.SNAP_COLS, "liquidity", "clob_token_id_0"]
EXT_COLS = [*b.EXT_COLS, "rewards_min_size", "rewards_max_spread", "clob_rewards"]

epoch, iso, sha256_file, _json = b.epoch, b.iso, b.sha256_file, b._json


# --- pins and spec ---------------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    import hashlib

    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: code_sha256(here / n) for n in CODE_FILES}


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"live_tests5 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests5 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    return spec


# --- capture readers ---------------------------------------------------------------------------------------------------


def load_rows(cap_dir: Path) -> pd.DataFrame:
    """Origin-side capture columns (LT3's plus Gamma ``liquidity``): one row per market_id and per condition_id."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category",
                              "end_date": "category", "closed": str, "active": str, "neg_risk": str, "clob_token_id_0": str})
    for c in ("liquidity",):
        if c not in rows:
            rows[c] = np.nan
    rows = rows.drop_duplicates("market_id")
    cond = rows["condition_id"].fillna("")
    rows = rows[~(cond.ne("") & cond.duplicated()).to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows


def load_ext(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS), dtype=str)
    for c in EXT_COLS:
        if c not in ext:
            ext[c] = None
    return ext.drop_duplicates("market_id").set_index("market_id")


def series_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str) -> pd.DataFrame:
    """LT3's series (vendored) plus Gamma liquidity and the reward fields: ``rew_rate`` (summed daily rate active on the
    capture's UTC ``day``; NaN when the sidecar row or the field is absent, never 0), ``rew_min``, ``rew_maxspread``
    (cents)."""
    ser, _ = b.series_frame(rows, ext, spec)
    mids = pd.Index(ser["market_id"].astype(str))
    ser["liq"] = rows.set_index(rows["market_id"].astype(str))["liquidity"].reindex(mids).to_numpy(float)
    if ext is not None:
        e = ext.reindex(mids)
        cr = e["clob_rewards"]
        ser["rew_rate"] = [maker_rewards.parse_daily_rate(v, day) if isinstance(v, str) else np.nan for v in cr]
        ser["rew_min"] = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
        ser["rew_maxspread"] = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
    else:
        ser["rew_rate"], ser["rew_min"], ser["rew_maxspread"] = np.nan, np.nan, np.nan
    return ser


def write_series(work: Path, cap: dict, spec: dict) -> None:
    p = Path(work) / "series" / f"{cap['id']}.csv.gz"
    if p.exists():
        return
    day = b._day([cap["start"]])[0]
    b.write_once_csv(p, series_frame(load_rows(cap["dir"]), load_ext(cap["dir"]), spec, day))


def is_day_origin(k: int, spec: dict) -> bool:
    """True for the 00:31Z slot of a UTC day (H's only origin; section 5 as fixed by re-check finding 5)."""
    return (b.slot_time(k, spec) - b.grid0(spec)) % DAY_S == 0.0


# --- shared statistics (counts only) ---------------------------------------------------------------------------------


def wcorr(df: pd.DataFrame, a: str, c: str) -> dict:
    """Pooled and within-market (expanding-past demeaned, the estimator's own variation) correlations of two columns."""
    d = df[["market_id", "t_row", a, c]].replace([np.inf, -np.inf], np.nan).dropna()
    out = {"pooled": None, "within": None, "n": len(d)}
    if len(d) < 10:
        return out
    if d[a].astype(float).std() > 0 and d[c].astype(float).std() > 0:
        out["pooled"] = float(np.corrcoef(d[a].astype(float), d[c].astype(float))[0, 1])
    X = b.demean(d, [a, c], "market_id", "t_row", "expanding")
    X = X.replace([np.inf, -np.inf], np.nan).dropna()
    if len(X) >= 10 and X[a].std() > 0 and X[c].std() > 0:
        out["within"] = float(np.corrcoef(X[a], X[c])[0, 1])
    return out


def corr_ok(r: dict, cap: float, both: bool = False) -> bool:
    w, p = r.get("within"), r.get("pooled")
    if w is None or not np.isfinite(w):
        return False
    if both and (p is None or not np.isfinite(p) or abs(p) > cap):
        return False
    return bool(abs(w) <= cap)


def design_ss(df: pd.DataFrame, term: str, controls: list[str]) -> dict:
    """Within-market (expanding-past demeaned) design of ``term`` given ``controls``: the residual sum of squares of the
    demeaned term on the demeaned controls (what governs the coefficient's SE) and the within VIF."""
    cols = [term, *controls]
    d = df[["market_id", "t_row", *cols]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(cols) + 10:
        return {"n": len(d), "ss_resid": float("nan"), "vif_w": float("nan")}
    X = b.demean(d, cols, "market_id", "t_row", "expanding").replace([np.inf, -np.inf], np.nan).dropna()
    Z = X[controls].to_numpy() if controls else np.zeros((len(X), 0))
    xt = b._partial(Z, X[term].to_numpy())
    x0 = X[term].to_numpy() - X[term].mean()
    ss, ss0 = float(xt @ xt), float(x0 @ x0)
    return {"n": int(len(X)), "ss_resid": ss, "vif_w": float(ss0 / ss) if ss > 0 else float("inf")}


def mde_class(n1: float, n2: float, sd: float, de: float, a: dict, vif: float = 1.0) -> float:
    """Planning MDE (price units) of a two-class contrast on projected effective counts (section 8 formula)."""
    if not (n1 > 0 and n2 > 0 and np.isfinite(de)):
        return float("inf")
    return a["t_sum"] * sd * math.sqrt(1.0 / n1 + 1.0 / n2) * math.sqrt(de) * a["day_factor"] * math.sqrt(max(vif, 1.0))


def mde_slope_design(ss_resid: float, scale: float, sd: float, de: float, a: dict) -> float:
    """Planning MDE per unit of the (standardised) term from the census design: t_sum x SD / sqrt(projected residual SS)
    x sqrt(DE) x day. Equals section 8's slope formula with the demeaned term's own variance made explicit (section 16)."""
    if not (ss_resid > 0 and np.isfinite(de)):
        return float("inf")
    return a["t_sum"] * sd / math.sqrt(ss_resid * scale) * math.sqrt(de) * a["day_factor"]


def mde_slope_declared(n_eff: float, sd: float, de: float, a: dict, vif: float) -> float:
    """Section 8's slope formula per SD of the term: t_sum x SD / sqrt(n_eff) x sqrt(DE) x day x sqrt(VIF_w)."""
    if not (n_eff > 0 and np.isfinite(de) and np.isfinite(vif)):
        return float("inf")
    return a["t_sum"] * sd / math.sqrt(n_eff) * math.sqrt(de) * a["day_factor"] * math.sqrt(max(vif, 1.0))


def _de(pop: pd.DataFrame, key: str, scale: float, g: dict) -> dict:
    de = b.design_effect(pop[key].astype(str), scale, float(g["rho"]))
    de["DE_gate"] = b.de_gate(de, float(g["de_floor"]))
    return de


def _projected(n: float, scale: float) -> float:
    return float(n * scale)


# --- J: jump or grind (CH180) ------------------------------------------------------------------------------------------


def outcome_of(tr: pd.DataFrame, token0: pd.Series | None) -> np.ndarray:
    """Outcome (0 / 1) of each print from ``outcome_index``, else asset == token 0 (outcome 0); NaN when unknown."""
    oi = pd.to_numeric(tr["outcome_index"], errors="coerce").to_numpy(float)
    oi = np.where(np.isin(oi, (0.0, 1.0)), oi, np.nan)
    if token0 is not None:
        t0 = tr["market_id"].astype(str).map(token0).astype(str).to_numpy()
        oi = np.where(np.isfinite(oi), oi, np.where(tr["asset"].astype(str).to_numpy() == t0, 0.0, np.nan))
    return oi


def yes_price(tr: pd.DataFrame, token0: pd.Series | None) -> np.ndarray:
    """YES-terms (outcome 0) price of each print: ``price`` on outcome 0, ``1 - price`` on outcome 1; NaN when the
    outcome is unknown."""
    oi = outcome_of(tr, token0)
    p = pd.to_numeric(tr["price"], errors="coerce").to_numpy(float)
    return np.where(oi == 0, p, np.where(oi == 1, 1.0 - p, np.nan))


def path_fields(tr: pd.DataFrame, u: pd.DataFrame, n_returned: np.ndarray, token0: pd.Series | None, spec: dict) -> pd.DataFrame:
    """Per unit (rows of ``u``: market_id, t_k, t_p, tick, steps): interval rows ``t_p <= ts < t_k``, coverage, levels of
    the tick-snapped YES-terms prices, ``g_path``, ``maxstep_share`` and E021's age (newest row with ts < t_k)."""
    c = spec["j"]
    tr = tr[tr["market_id"].astype(str).isin(set(u["market_id"].astype(str)))].copy()
    tr["py"] = yes_price(tr, token0)
    tr["ts"] = pd.to_numeric(tr["ts"], errors="coerce").astype(float)
    tk = u.set_index(u["market_id"].astype(str))
    tr["t_k"] = tr["market_id"].astype(str).map(tk["t_k"]).astype(float)
    tr["t_p"] = tr["market_id"].astype(str).map(tk["t_p"]).astype(float)
    tr["tick"] = tr["market_id"].astype(str).map(tk["tick"]).astype(float)
    n = len(u)
    out = {k: np.full(n, np.nan) for k in ("n_int", "levels", "g_path", "maxstep_share", "age", "oldest", "n_unknown_outcome", "n_int_all", "n_int_not_minute")}
    grp = {m: g for m, g in tr.groupby(tr["market_id"].astype(str))}
    for i, m in enumerate(u["market_id"].astype(str)):
        g = grp.get(m)
        if g is None:
            out["n_int"][i] = 0
            continue
        ts = g["ts"].to_numpy()
        tkk, tpp, tick = float(u["t_k"].iloc[i]), float(u["t_p"].iloc[i]), float(u["tick"].iloc[i])
        out["oldest"][i] = np.nanmin(ts) if len(ts) else np.nan
        pre = ts < tkk
        out["age"][i] = tkk - ts[pre].max() if pre.any() else np.nan
        inw = (ts >= tpp) & (ts < tkk)
        out["n_int_all"][i] = float(inw.sum())
        out["n_int_not_minute"][i] = float((np.mod(ts[inw], 60.0) != 0).sum())
        py = g["py"].to_numpy()[inw]
        out["n_unknown_outcome"][i] = float(np.isnan(py).sum())
        known = np.isfinite(py)
        out["n_int"][i] = float(known.sum())
        if known.sum() == 0:
            continue
        snapped = np.round(py[known] / tick).astype(np.int64)
        lv = len(np.unique(snapped))
        out["levels"][i] = lv
        out["g_path"][i] = min(max((lv - 1) / float(u["steps"].iloc[i]), 0.0), 1.0)
        order = np.argsort(ts[inw][known], kind="mergesort")
        pp = py[known][order]
        out["maxstep_share"][i] = float(np.abs(np.diff(pp)).max() / abs(float(u["x"].iloc[i]))) if len(pp) > 1 else 0.0
    res = pd.DataFrame(out)
    full = np.asarray(n_returned, float) >= trade_sample.TRADE_LIMIT
    with np.errstate(invalid="ignore"):
        res["interval_truncated"] = (full & ~(res["oldest"].to_numpy() <= u["t_p"].to_numpy(float))).astype(int)
    res["cls_j"] = np.where(res["g_path"] <= c["jump_max"], "jump", np.where(res["g_path"] >= c["grind_min"], "grind", "interior"))
    res.loc[~np.isfinite(res["g_path"]), "cls_j"] = ""
    res["fresh"] = (res["age"] <= c["fresh_max_s"]).astype(int)
    return res


def path_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, feat: pd.DataFrame, tr: pd.DataFrame, token0: pd.Series | None,
               cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """J units of one pass (section 2 filters in order, each counted): sampled (status ok) traded |x| >= 1c movers at k
    (1.4), tick known and equal at k - 1 and k, steps >= 3, interval covered, >= 3 interval rows."""
    c, m = spec["j"], spec["move"]
    j, cnt = b.move_join(ser_k, ser_p, cap, spec, m["mid_lo"], m["mid_hi"], m["end_margin_h"])
    j["x"] = (j["bid"] + j["ask"]) / 2.0 - (j["bid_p"] + j["ask_p"]) / 2.0
    j = j[np.abs(j["x"]) >= m["min_abs_x"] - 1e-12]
    cls, geom = b.classify(j["bid_p"], j["ask_p"], j["bid"], j["ask"], j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    j = j.assign(cls=cls, geom=geom)
    f = feat.drop_duplicates("market_id").set_index(feat.drop_duplicates("market_id")["market_id"].astype(str))
    j = j[j["market_id"].astype(str).isin(f.index)]
    cnt["sampled_movers"] = len(j)
    j = j[j["cls"] == "traded"].copy()
    cnt["sampled_traded"] = len(j)
    tick_p = ser_p["tick"].reindex(j["market_id"].astype(str)).to_numpy(float)
    tick_k = j["tick"].to_numpy(float)
    tok = np.isfinite(tick_k) & np.isfinite(tick_p) & (np.abs(tick_k - tick_p) <= 1e-12) & (tick_k > 0)
    cnt["tick_unknown_or_changed"] = int((~tok).sum())
    j = j[tok].copy()
    j["steps"] = np.round(np.abs(j["x"].to_numpy(float)) / j["tick"].to_numpy(float))
    st = j["steps"] >= c["min_steps"]
    cnt["steps_below_min"] = int((~st).sum())
    j = j[st].copy()
    mk = j["market_id"].astype(str)
    j["t_k"] = panel._epoch(f["origin_utc"].reindex(mk).astype(str))
    j["t_p"] = ser_p["t_row"].reindex(mk).to_numpy(float)
    nret = f["n_returned"].reindex(mk).to_numpy(float)
    cnt["at_coverage"] = len(j)
    pf = path_fields(tr, j.reset_index(drop=True), nret, token0, spec)
    j = pd.concat([j.reset_index(drop=True), pf], axis=1)
    cnt["interval_truncated"] = int(j["interval_truncated"].sum())
    cnt["interval_rows_all"] = int(np.nansum(j["n_int_all"]))
    cnt["interval_rows_not_minute"] = int(np.nansum(j["n_int_not_minute"]))
    j = j[j["interval_truncated"] == 0]
    ok = j["n_int"] >= c["min_rows"]
    cnt["rows_below_min"] = int((~ok).sum())
    j = j[ok].reset_index(drop=True)
    cnt["qualifying"] = len(j)
    return j, cnt


# --- F: alone or with the crowd (CH184) ------------------------------------------------------------------------------


def family_members(ser_k: pd.DataFrame, ser_p: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Every market passing 1.4 items 1-3 and 7 at k - 1 and k (two-sided and tight at both; any |x|, including 0)."""
    sm = spec["eligibility"]["spread_max"]
    j = ser_k.join(ser_p[["bid", "ask", "spread"]].rename(columns=lambda c: c + "_p"), how="inner")
    t = b.tight_arr(j["bid"], j["ask"], j["spread"], sm) & b.tight_arr(j["bid_p"], j["ask_p"], j["spread_p"], sm)
    j = j[t]
    x = (j["bid"] + j["ask"]) / 2.0 - (j["bid_p"] + j["ask_p"]) / 2.0
    return pd.DataFrame({"market_id": j.index.astype(str), "event_id": j["event_id"].astype(str).to_numpy(), "x": x.to_numpy(float),
                         "t_row": j["t_row"].to_numpy(float), "neg_risk": j["neg_risk"].to_numpy(int), "skey": j["skey"].astype(str).to_numpy()})


def _is_series_key(k: str) -> bool:
    return not (k.startswith("event:") or k == "crypto:noslug" or k in ("", "nan", "None"))


def family_stats(units: pd.DataFrame, members: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Per unit: the declared hierarchy (non-neg-risk event with >= 3 other usable members, else the first series slug
    with >= 3, else not formed), with the receipt guard (a sibling enters only if received <= t_unit + guard_s) and, at the
    series level, without siblings in the unit's own neg-risk event. Leave-one-out mean move, share of siblings moving
    >= 1c, mean |x|, size, level, the latest receipt used (the decision time) and the guard loss."""
    c = spec["f"]
    g_s, mn, mv = float(c["guard_s"]), int(c["min_siblings"]), float(spec["move"]["min_abs_x"])
    by_ev = {k: v for k, v in members.groupby("event_id")}
    by_sk = {k: v for k, v in members.groupby("skey")}
    rows = []
    for u in units.itertuples(index=False):
        res = {"level": "", "fam_id": "", "n_sib": 0, "xbar": np.nan, "share_moving": np.nan, "fam_abs": np.nan,
               "t_dec": np.nan, "guard_loss": 0, "reason": "", "n_negrisk_excluded": 0}
        cand = []
        if not int(u.neg_risk):
            ev = by_ev.get(str(u.event_id))
            if ev is not None:
                cand.append(("event", "event:" + str(u.event_id), ev[ev["market_id"] != str(u.market_id)]))
        if _is_series_key(str(u.skey)):
            se = by_sk.get(str(u.skey))
            if se is not None:
                s = se[se["market_id"] != str(u.market_id)]
                if int(u.neg_risk):
                    same = s["event_id"] == str(u.event_id)
                    res["n_negrisk_excluded"] = int(same.sum())
                    s = s[~same]
                cand.append(("series", "series:" + str(u.skey), s))
        any_pre_guard = False
        for level, fid, sib in cand:
            if len(sib) >= mn:
                any_pre_guard = True
            use = sib[sib["t_row"].to_numpy(float) <= float(u.t_row) + g_s]
            if len(use) >= mn:
                xs = use["x"].to_numpy(float)
                res.update(level=level, fam_id=fid, n_sib=len(use), xbar=float(xs.mean()),
                           share_moving=float((np.abs(xs) >= mv - 1e-12).mean()), fam_abs=float(np.abs(xs).mean()),
                           t_dec=float(max(float(u.t_row), use["t_row"].max())))
                break
        if not res["level"]:
            res["reason"] = "guard_loss" if any_pre_guard else ("no_family" if not cand else "too_few_siblings")
            res["guard_loss"] = int(any_pre_guard)
        rows.append(res)
    return pd.DataFrame(rows, index=units.index)


def family_classes(x: np.ndarray, xbar: np.ndarray, spec: dict) -> np.ndarray:
    c = spec["f"]
    x, xbar = np.asarray(x, float), np.asarray(xbar, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.clip(xbar / x, -1.0, 2.0)
        idio = np.abs(xbar) < c["idio_max_share"] * np.abs(x)
        common = w >= c["common_min_share"]
    out = np.where(idio, "idio", np.where(common, "common", "interior")).astype(object)
    out[~np.isfinite(xbar)] = ""
    return out


def family_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """F units at capture k: non-sports |x| >= 1c movers (1.4) of E015's traded or quote-only classes with a family."""
    m = spec["move"]
    j, cnt = b.move_join(ser_k, ser_p, cap, spec, m["mid_lo"], m["mid_hi"], m["end_margin_h"])
    j["x"] = (j["bid"] + j["ask"]) / 2.0 - (j["bid_p"] + j["ask_p"]) / 2.0
    j = j[np.abs(j["x"]) >= m["min_abs_x"] - 1e-12]
    cls, geom = b.classify(j["bid_p"], j["ask_p"], j["bid"], j["ask"], j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    j = j.assign(cls=cls, geom=geom)
    cnt["movers"] = len(j)
    cnt["sports_or_unknown"] = int((j["sports"] != 0).sum())
    j = j[(j["sports"] == 0) & j["cls"].isin(["traded", "quote_only"])].reset_index(drop=True)
    cnt["non_sports_traded_or_quote_only"] = len(j)
    fs = family_stats(j, family_members(ser_k, ser_p, spec), spec)
    j = pd.concat([j, fs], axis=1)
    j["cls_f"] = family_classes(j["x"], j["xbar"], spec)
    j["anat"] = np.where(j["cls"] == "traded", "traded", j["geom"].astype(str))
    cnt["family_reason"] = {str(k): int(v) for k, v in j["reason"].value_counts().items()}
    cnt["formed"] = int((j["level"] != "").sum())
    return j, cnt


# --- O: token-weighted overhang (CH182) --------------------------------------------------------------------------------


def overhang_fields(tr: pd.DataFrame, u: pd.DataFrame, n_returned: np.ndarray, token0: pd.Series | None, spec: dict) -> pd.DataFrame:
    """Per unit (market_id, t_k, mid): rows with ``t_k - 24 h <= ts < t_k`` (outcome known): n24, VWAP (size-weighted
    YES-terms price), s_YES and s_NO (notional = size x token price), ``g = mid - VWAP``, ``m = s_YES - s_NO``,
    ``O = |g| m`` (section 4, R1 sign), the round's ``G = g m``, 24 h coverage, and E013's ``x6`` over 6 h."""
    c = spec["o"]
    tr = tr[tr["market_id"].astype(str).isin(set(u["market_id"].astype(str)))].copy()
    tr["ts"] = pd.to_numeric(tr["ts"], errors="coerce").astype(float)
    tr["py"] = yes_price(tr, token0)
    tr["p"] = pd.to_numeric(tr["price"], errors="coerce").astype(float)
    tr["sz"] = pd.to_numeric(tr["size"], errors="coerce").astype(float)
    tr["sg"] = b.signs(tr, token0)
    tr["oi0"] = outcome_of(tr, token0)
    grp = {m: g for m, g in tr.groupby(tr["market_id"].astype(str))}
    n = len(u)
    out = {k: np.full(n, np.nan) for k in ("n24", "vwap", "s_yes", "g", "m", "O", "G", "oldest", "x6")}
    win = float(c["window_s"])
    for i, (mk, tk, mid) in enumerate(zip(u["market_id"].astype(str), u["t_k"].to_numpy(float), u["mid"].to_numpy(float), strict=True)):
        g = grp.get(mk)
        if g is None:
            out["n24"][i] = 0
            continue
        ts = g["ts"].to_numpy()
        out["oldest"][i] = np.nanmin(ts)
        inw = (ts >= tk - win) & (ts < tk) & np.isfinite(g["py"].to_numpy())
        out["n24"][i] = float(inw.sum())
        if inw.sum() == 0:
            continue
        py, sz, p = g["py"].to_numpy()[inw], g["sz"].to_numpy()[inw], g["p"].to_numpy()[inw]
        o0 = g["oi0"].to_numpy()[inw] == 0
        vw = float((py * sz).sum() / sz.sum()) if sz.sum() > 0 else np.nan
        nt = sz * p
        tot = nt.sum()
        sy = float(nt[o0].sum() / tot) if tot > 0 else np.nan
        gg = mid - vw
        mm = sy - (1.0 - sy) if np.isfinite(sy) else np.nan
        out["vwap"][i], out["s_yes"][i], out["g"][i], out["m"][i] = vw, sy, gg, mm
        out["O"][i], out["G"][i] = abs(gg) * mm, gg * mm
        in6 = (ts >= tk - 6 * 3600.0) & (ts < tk) & (g["sg"].to_numpy() != 0)
        n6 = (g["sz"].to_numpy() * g["p"].to_numpy())[in6]
        if n6.sum() > 0:
            imb = float((g["sg"].to_numpy()[in6] * n6).sum() / n6.sum())
            out["x6"][i] = float(np.clip(imb, -1, 1) / X6_SCALE)
    res = pd.DataFrame(out)
    full = np.asarray(n_returned, float) >= trade_sample.TRADE_LIMIT
    with np.errstate(invalid="ignore"):
        res["trunc24"] = (full & ~(res["oldest"].to_numpy() <= u["t_k"].to_numpy(float) - win)).astype(int)
    return res


def overhang_units(ser_k: pd.DataFrame, by_slot_series: dict, k: int, feat: pd.DataFrame, tr: pd.DataFrame,
                   token0: pd.Series | None, cap: dict, spec: dict) -> tuple[pd.DataFrame, dict]:
    """O units of one pass: sampled (status ok) markets two-sided and tight at k (1.4 items 1-3, 5, 7), mid in
    [0.05, 0.95], >= 10 rows in the 24 h window, 24 h coverage; own mid changes over 2 h / 6 h / 24 h from the series of
    slots k - 1, k - 3, k - 12 (NaN when a slot is missing: never 0, re-check finding 7)."""
    c = spec["o"]
    sm = spec["eligibility"]["spread_max"]
    f = feat.drop_duplicates("market_id")
    f = f.set_index(f["market_id"].astype(str))
    s = ser_k[ser_k.index.astype(str).isin(f.index)]
    cnt = {"sampled_in_series": len(s)}
    s = s[b.tight_arr(s["bid"], s["ask"], s["spread"], sm)]
    mid = (s["bid"] + s["ask"]) / 2.0
    s = s[(mid >= c["mid_lo"]) & (mid <= c["mid_hi"])]
    end = s["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        s = s[np.isnan(end) | (end > s["t_row"].to_numpy(float) + spec["move"]["end_margin_h"] * 3600.0)]
    cnt["eligible"] = len(s)
    u = pd.DataFrame({"market_id": s.index.astype(str), "event_id": s["event_id"].astype(str).to_numpy(), "skey": s["skey"].astype(str).to_numpy(),
                      "sports": s["sports"].to_numpy(int), "t_row": s["t_row"].to_numpy(float), "mid": ((s["bid"] + s["ask"]) / 2.0).to_numpy(float),
                      "spread": s["spread"].to_numpy(float), "chg_1d": s["chg_1d"].to_numpy(float), "liq": s["liq"].to_numpy(float)})
    u["t_k"] = panel._epoch(f["origin_utc"].reindex(u["market_id"]).astype(str))
    for h, lag in (("d2h", 1), ("d6h", 3), ("d24h", 12)):
        sp = by_slot_series.get(k - lag)
        u[h] = u["mid"].to_numpy() - (b._mid(sp, u["market_id"]) if sp is not None else np.full(len(u), np.nan))
    nret = f["n_returned"].reindex(u["market_id"]).to_numpy(float)
    u = pd.concat([u, overhang_fields(tr, u, nret, token0, spec)], axis=1)
    ok = u["n24"] >= c["min_rows"]
    cnt["rows_below_min"] = int((~ok).sum())
    u = u[ok]
    cnt["with_min_rows"] = len(u)
    cnt["trunc24"] = int(u["trunc24"].sum())
    u = u[u["trunc24"] == 0].reset_index(drop=True)
    cnt["covered"] = len(u)
    return u, cnt


# --- H: the high-water mark (CH181) ------------------------------------------------------------------------------------


def mid_matrix(series_by_slot: dict[int, pd.DataFrame | None], slots: list[int], spread_max: float) -> tuple[pd.Index, np.ndarray]:
    """Markets x slots matrix of two-sided Gamma mids with spread <= ``spread_max`` (R1 finding 7); NaN otherwise or when
    the slot's capture is missing."""
    ids = pd.Index(sorted({m for s in slots if series_by_slot.get(s) is not None for m in series_by_slot[s].index.astype(str)}))
    M = np.full((len(ids), len(slots)), np.nan, dtype=np.float64)
    for j, s in enumerate(slots):
        ser = series_by_slot.get(s)
        if ser is None:
            continue
        ok = b.tight_arr(ser["bid"], ser["ask"], ser["spread"], spread_max)
        v = ((ser["bid"] + ser["ask"]) / 2.0).where(ok)
        M[:, j] = pd.Series(v.to_numpy(float), index=ser.index.astype(str)).reindex(ids).to_numpy(float)
    return ids, M


def max_gap(W: np.ndarray) -> np.ndarray:
    """Longest run of consecutive non-qualifying (NaN) slots per row."""
    out = np.zeros(W.shape[0], int)
    run = np.zeros(W.shape[0], int)
    for j in range(W.shape[1]):
        run = np.where(np.isfinite(W[:, j]), 0, run + 1)
        out = np.maximum(out, run)
    return out


def window_marks(M: np.ndarray, j_end: int, width: int) -> dict:
    """hi, lo, age_hi, age_lo (slots before column ``j_end``), the present count and the longest gap over columns
    j_end - width .. j_end - 1."""
    W = M[:, j_end - width:j_end]
    present = np.isfinite(W).sum(axis=1)
    with np.errstate(all="ignore"):
        hi = np.where(present > 0, np.nanmax(np.where(np.isfinite(W), W, -np.inf), axis=1), np.nan)
        lo = np.where(present > 0, np.nanmin(np.where(np.isfinite(W), W, np.inf), axis=1), np.nan)
    rev = W[:, ::-1]
    at_hi = np.isfinite(rev) & (np.abs(rev - hi[:, None]) <= 1e-12)
    at_lo = np.isfinite(rev) & (np.abs(rev - lo[:, None]) <= 1e-12)
    age_hi = np.where(at_hi.any(axis=1), at_hi.argmax(axis=1) + 1, -1).astype(float)
    age_lo = np.where(at_lo.any(axis=1), at_lo.argmax(axis=1) + 1, -1).astype(float)
    age_hi[present == 0], age_lo[present == 0] = np.nan, np.nan
    return {"hi": hi, "lo": lo, "age_hi": age_hi, "age_lo": age_lo, "present": present, "gap": max_gap(W)}


def mark_classes(mid: np.ndarray, mk: dict, spec: dict) -> tuple[np.ndarray, np.ndarray]:
    """(class, fold sign): near_high / near_low / far / rest / new_extreme (section 5)."""
    c = spec["h"]
    hi, lo = mk["hi"], mk["lo"]
    with np.errstate(invalid="ignore"):
        d_hi, d_lo = hi - mid, mid - lo
        new = (mid > hi + 1e-12) | (mid < lo - 1e-12)
        nh = ~new & (d_hi <= c["near_max"] + 1e-12) & (mk["age_hi"] >= c["min_age_slots"])
        nl = ~new & (d_lo <= c["near_max"] + 1e-12) & (mk["age_lo"] >= c["min_age_slots"])
        far = ~new & (d_hi >= c["far_min"] - 1e-12) & (d_lo >= c["far_min"] - 1e-12)
    cls = np.where(new, "new_extreme", np.where(nh, "near_high", np.where(nl, "near_low", np.where(far, "far", "rest")))).astype(object)
    s = np.where(cls == "near_high", 1.0, np.where(cls == "near_low", -1.0, np.sign(mid - (hi + lo) / 2.0)))
    return cls, s


def mark_units(series_by_slot: dict, k: int, spec: dict) -> tuple[pd.DataFrame, dict]:
    """H units at the 00:31Z slot ``k`` of a UTC day: non-sports markets two-sided and tight at k - 1 and k, end > t + 3 h,
    mid in [0.05, 0.95], a 7-day mark with >= 72 of 84 qualifying slots, range >= 5c, a state change since the
    previous day's origin (mid, hi or lo), not a new extreme. Look-back slots k - 96 .. k - 1 only."""
    c = spec["h"]
    cnt: dict = {}
    if not is_day_origin(k, spec):
        return pd.DataFrame(), {"not_day_origin": True}
    ser_k, ser_p = series_by_slot.get(k), series_by_slot.get(k - 1)
    if ser_k is None or ser_p is None:
        return pd.DataFrame(), {"capture_missing": True}
    w = int(c["window_slots"])
    slots = list(range(k - w - 12, k + 1))
    ids, M = mid_matrix(series_by_slot, slots, spec["eligibility"]["spread_max"])
    cur = window_marks(M, len(slots) - 1, w)
    prev = window_marks(M, len(slots) - 13, w)
    j, cnt0 = b.move_join(ser_k, ser_p, {"id": "", "dir": None}, spec, c["mid_lo"], c["mid_hi"], spec["move"]["end_margin_h"])
    cnt.update(cnt0)
    j = j[j["sports"] == 0].reset_index(drop=True)
    cnt["non_sports"] = len(j)
    pos = ids.get_indexer(j["market_id"].astype(str))
    take = {k_: np.where(pos >= 0, v[np.clip(pos, 0, None)], np.nan) for k_, v in cur.items()}
    tprev = {k_: np.where(pos >= 0, v[np.clip(pos, 0, None)], np.nan) for k_, v in prev.items()}
    mid = ((j["bid"] + j["ask"]) / 2.0).to_numpy(float)
    mid_prev = np.where(pos >= 0, M[np.clip(pos, 0, None), len(slots) - 13], np.nan)
    j = j.assign(mid=mid, hi=take["hi"], lo=take["lo"], age_hi=take["age_hi"], age_lo=take["age_lo"], present=take["present"], gap=take["gap"])
    inc = ~(j["present"].to_numpy(float) >= c["min_present"])
    gap = ~inc & (j["gap"].to_numpy(float) > c["max_gap_slots"])  # section 5: a gap of > 12 consecutive slots in the window
    ok_w = ~inc & ~gap
    cnt["hwm_incomplete"] = int(inc.sum())
    cnt["hwm_gap"] = int(gap.sum())
    with np.errstate(invalid="ignore"):
        rng_ok = (j["hi"] - j["lo"]).to_numpy(float) >= c["min_range"] - 1e-12
        mid_known = np.isfinite(mid_prev)
        prev_ok = tprev["present"] >= c["min_present"]
        chg_mid = mid_known & (np.abs(mid - mid_prev) > 1e-9)
        chg_ext = prev_ok & ((np.abs(take["hi"] - tprev["hi"]) > 1e-12) | (np.abs(take["lo"] - tprev["lo"]) > 1e-12))
    unknown = ~mid_known & ~prev_ok  # the previous day's state cannot be established: excluded, counted (never assumed)
    chg = chg_mid | chg_ext
    cnt["range_below_min"] = int((ok_w & ~rng_ok).sum())
    cnt["prev_state_unknown"] = int((ok_w & rng_ok & unknown).sum())
    cnt["dormant"] = int((ok_w & rng_ok & ~unknown & ~chg).sum())
    j = j[ok_w & rng_ok & chg].reset_index(drop=True)
    cls, s = mark_classes(j["mid"].to_numpy(float), {kk: j[kk].to_numpy(float) for kk in ("hi", "lo", "age_hi", "age_lo")}, spec)
    j["cls_h"], j["s"] = cls, s
    j["d_hi"], j["d_lo"] = j["hi"] - j["mid"], j["mid"] - j["lo"]
    sp24 = series_by_slot.get(k - 12)
    j["d24h"] = j["mid"].to_numpy() - (b._mid(sp24, j["market_id"]) if sp24 is not None else np.full(len(j), np.nan))
    j["s_d24h"] = j["s"] * j["d24h"]
    cnt["by_class"] = {str(a): int(v) for a, v in j["cls_h"].value_counts().items()}
    return j, cnt


def d_hi_panel(series_by_slot: dict, census_slots: list[int], spec: dict) -> pd.DataFrame:
    """d_hi at every census slot with a capture (the within-market SD gate of CHW), on H's population at that slot
    (census code check finding 3): non-sports, two-sided and tight at k - 1 and k, end > t + 3 h, mid in [0.05, 0.95]."""
    c = spec["h"]
    w = int(c["window_slots"])
    slots = list(range(min(census_slots) - w, max(census_slots) + 1))
    ids, M = mid_matrix(series_by_slot, slots, spec["eligibility"]["spread_max"])
    present_all = np.isfinite(M).sum(axis=1)
    out = []
    for k in census_slots:
        ser_k, ser_p = series_by_slot.get(k), series_by_slot.get(k - 1)
        if ser_k is None or ser_p is None:
            continue
        j, _ = b.move_join(ser_k, ser_p, {"id": "", "dir": None}, spec, c["mid_lo"], c["mid_hi"], spec["move"]["end_margin_h"])
        keep = set(j.loc[j["sports"] == 0, "market_id"].astype(str))
        jj = slots.index(k)
        mk = window_marks(M, jj, w)
        d = pd.DataFrame({"market_id": ids, "d_hi": mk["hi"] - M[:, jj], "present_all": present_all})
        out.append(d[d["market_id"].isin(keep)])
    if not out:
        return pd.DataFrame(columns=["market_id", "d_hi", "present_all"])
    P = pd.concat(out, ignore_index=True)
    return P[np.isfinite(P["d_hi"])]


# --- R: the farmer's choice (CH183) ----------------------------------------------------------------------------------


def fold(smid) -> np.ndarray:
    s = np.asarray(smid, float)
    return np.maximum(s, 1.0 - s)


def imbalance(dbid, dask) -> np.ndarray:
    d1, d2 = np.asarray(dbid, float), np.asarray(dask, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((d1 + d2) > 0, (d1 - d2) / (d1 + d2), np.nan)


def rule_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame | None, sw_k: pd.DataFrame, sw_p: pd.DataFrame | None,
               spec: dict) -> tuple[pd.DataFrame, dict]:
    """R units of pass k (section 6; rewarded and unrewarded, folded mid in [0.59, 0.96) for the fake cutoffs): open
    binary markets in capture k and k - 1, end > t + 3 h, tick 0.01 at k, sweep 1 two-sided and tight, outside the donut,
    a change of the sweep mid or of either imbalance since sweep 1 of pass k - 1. Depths at 1c and 5c are both kept;
    the census fixes the band. ``rewarded`` = summed daily rate active on the capture's day > 0; NaN rate excluded."""
    c = spec["r"]
    cnt: dict = {}
    s = ser_k[ser_k.index.astype(str).isin(set(ser_p.index.astype(str)))] if ser_p is not None else ser_k.iloc[0:0]
    cnt["in_k_and_k1"] = len(s)
    end = s["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        s = s[np.isnan(end) | (end > s["t_row"].to_numpy(float) + spec["move"]["end_margin_h"] * 3600.0)]
    s = s[np.abs(s["tick"].to_numpy(float) - c["tick"]) <= 1e-12]
    cnt["tick_ok"] = len(s)
    sw = sw_k.reindex(s.index.astype(str))
    two = (sw["s_two"].to_numpy(float) == 1) & ((sw["sask"] - sw["sbid"]).to_numpy(float) <= spec["eligibility"]["spread_max"] + 1e-12)
    s, sw = s[two], sw[two]
    cnt["sweep_two_sided_tight"] = len(s)
    smid = ((sw["sbid"] + sw["sask"]) / 2.0).to_numpy(float)
    f = fold(smid)
    with np.errstate(invalid="ignore"):
        band = (f >= c["band_lo_all"] - 1e-12) & (f < c["band_hi"] - 1e-12) & (np.abs(f - c["cutoff"]) >= c["donut"] - 1e-12)
    s, sw, smid, f = s[band], sw[band], smid[band], f[band]
    cnt["in_band_outside_donut"] = len(s)
    u = pd.DataFrame({"market_id": s.index.astype(str), "event_id": s["event_id"].astype(str).to_numpy(), "skey": s["skey"].astype(str).to_numpy(),
                      "sports": s["sports"].to_numpy(int), "t_row": sw["s_t"].to_numpy(float), "smid": smid, "f": f,
                      "rf": f - c["cutoff"], "inside": (f <= c["cutoff"] + 1e-12).astype(int),
                      "rew_rate": s["rew_rate"].to_numpy(float), "rew_min": s["rew_min"].to_numpy(float),
                      "rew_maxspread": s["rew_maxspread"].to_numpy(float), "sw_spread": (sw["sask"] - sw["sbid"]).to_numpy(float),
                      "dbid1": sw["dbid1"].to_numpy(float), "dask1": sw["dask1"].to_numpy(float),
                      "dbid5": sw["dbid5"].to_numpy(float), "dask5": sw["dask5"].to_numpy(float), "liq": s["liq"].to_numpy(float)})
    u["imb1"], u["imb5"] = imbalance(u["dbid1"], u["dask1"]), imbalance(u["dbid5"], u["dask5"])
    u["rewarded"] = np.where(np.isfinite(u["rew_rate"]), (u["rew_rate"] > 0).astype(float), np.nan)
    cnt["reward_unknown"] = int(u["rewarded"].isna().sum())
    u = u[np.isfinite(u["rewarded"])]
    if sw_p is not None:
        pp = sw_p.reindex(u["market_id"])
        smp = ((pp["sbid"] + pp["sask"]) / 2.0).to_numpy(float)
        i1p, i5p = imbalance(pp["dbid1"], pp["dask1"]), imbalance(pp["dbid5"], pp["dask5"])
        with np.errstate(invalid="ignore"):
            known = np.isfinite(smp)
            chg = known & ((np.abs(u["smid"].to_numpy() - smp) > 1e-12) | ~(np.abs(u["imb1"].to_numpy() - i1p) <= 1e-12)
                           | ~(np.abs(u["imb5"].to_numpy() - i5p) <= 1e-12))
    else:
        known, chg = np.zeros(len(u), bool), np.zeros(len(u), bool)
    cnt["prev_sweep_missing"] = int((~known).sum())
    cnt["dormant"] = int((known & ~chg).sum())
    u = u[chg].reset_index(drop=True)
    u["primary_band"] = (u["f"] >= c["band_lo"] - 1e-12).astype(int)
    cnt["units"] = len(u)
    return u, cnt


# --- census drivers (counts only; sealed inputs) ---------------------------------------------------------------------


def _roots(r) -> list[Path]:
    return [Path(x) for x in (r if isinstance(r, (list, tuple)) else [r])] if r is not None else []


def _scan(work: Path, snapshot_roots, sweep_roots, spec: dict) -> tuple[dict, dict]:
    """Complete captures by slot and sweep 1 by snapshot id over several roots (the host's originals and a restore tree,
    census code check finding 1). Each root is scanned with its own cache; per slot the earliest-starting complete capture
    wins (the vendored rule), per snapshot id the first root that holds a sweep 1."""
    by_slot: dict[int, dict] = {}
    sweeps: dict[str, dict] = {}
    for i, r in enumerate(_roots(snapshot_roots)):
        for k, c in b.scan_captures(r, b.State(Path(work) / f"scan_snap{i}"), spec).items():
            if k not in by_slot or c["start"] < by_slot[k]["start"]:
                by_slot[k] = c
    for i, r in enumerate(_roots(sweep_roots)):
        for sid, v in b.scan_sweeps(r, b.State(Path(work) / f"scan_sweep{i}")).items():
            sweeps.setdefault(sid, v)
    return by_slot, sweeps


def _name_time(name: str) -> float:
    """Start time from a capture / sweep directory name ``YYYYMMDDTHHMMSSZ_...``; NaN if unparseable."""
    m = re.match(r"^(\d{8})T(\d{6})Z", name)
    if not m:
        return float("nan")
    d, t = m.groups()
    return epoch(f"{d[:4]}-{d[4:6]}-{d[6:]}T{t[:2]}:{t[2:4]}:{t[4:]}Z")


def sealed_dirs(seal: dict, sub: str) -> dict[str, list[str]]:
    """{directory name: [sealed archive paths]} for ``data-dumps/research_lab/<sub>/<dir>/<file>`` entries of a seal."""
    out: dict[str, list[str]] = {}
    pre = f"data-dumps/research_lab/{sub}/"
    for rel in seal.get("files", {}):
        if rel.startswith(pre):
            d = rel[len(pre):].split("/", 1)[0]
            out.setdefault(d, []).append(rel)
    return out


def seal_completeness(seal: dict, by_slot: dict, sweeps: dict, cap_slots: set[int], sweep_slots: set[int], spec: dict,
                      sweep_roots=None) -> dict:
    """Census code check finding 1. (a) Every sealed capture or sweep whose start falls in a needed slot must be present
    locally with every sealed file, else the census is refused ("sealed but absent"). (b) Every opened capture or sweep
    file must itself be sealed with an equal sha256 (``verify_files``). (c) Needed slots with no local capture and no
    sealed capture are genuinely missing: counted, never refused, never imputed."""
    bad: list[dict] = []
    local_caps = {c["id"]: c for c in by_slot.values()}
    for d, rels in sealed_dirs(seal, "snapshots").items():
        k = b.slot_of(_name_time(d), spec) if np.isfinite(_name_time(d)) else None
        if k is None or k not in cap_slots:
            continue
        c = local_caps.get(d)
        if c is None:
            bad.append({"file": rels[0], "error": "sealed but absent locally (capture)"})
            continue
        for rel in rels:
            if not (Path(c["dir"]) / rel.rsplit("/", 1)[1]).exists():
                bad.append({"file": rel, "error": "sealed but absent locally"})
    for d, rels in sealed_dirs(seal, "book_sweeps").items():
        k = b.slot_of(_name_time(d), spec) if np.isfinite(_name_time(d)) else None
        if k is None or k not in sweep_slots:
            continue
        home = next((Path(r) / d for r in _roots(sweep_roots) if (Path(r) / d).is_dir()), None)
        for rel in rels:
            if home is None or not (home / rel.rsplit("/", 1)[1]).exists():
                bad.append({"file": rel, "error": "sealed but absent locally"})
    files = [f for j in sorted(cap_slots) if j in by_slot for f in b.capture_files(by_slot[j]["dir"])]
    files += [f for j in sorted(sweep_slots) if j in by_slot and by_slot[j]["id"] in sweeps
              for f in b.sweep_files(sweeps[by_slot[j]["id"]]["dir"])]
    bad += b.verify_files(seal, files)
    sealed_slots = {b.slot_of(_name_time(d), spec) for d in sealed_dirs(seal, "snapshots") if np.isfinite(_name_time(d))}
    missing = sorted(j for j in cap_slots if j not in by_slot and j not in sealed_slots)
    return {"bad": bad, "missing_slots": [b.iso(b.slot_time(j, spec)) for j in missing], "n_missing_slots": len(missing),
            "files_checked": len(files)}


def _read(work: Path, by_slot: dict, j: int, cache: dict) -> pd.DataFrame | None:
    if j not in by_slot:
        return None
    if j not in cache:
        cache[j] = b.read_series(work, by_slot[j]["id"])
    return cache[j]


def census_slots(days: list[str], spec: dict) -> list[int]:
    """Every grid slot whose slot time falls on one of the UTC ``days`` (present or not)."""
    out = []
    for d in days:
        t0 = epoch(f"{d}T00:00:00Z")
        k0 = b.slot_of(t0 + 31 * 60, spec)
        out += [k0 + i for i in range(12)]
    return sorted(out)


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, sweep_root=SWEEP_ROOT, work: Path,
                    days: list[str] | None = None, spec: dict | None = None, verify: bool = True) -> dict:
    """CF5 (F), CHW (H) and CRW (R) on the grid slots of the census ``days`` with H's 96-slot look-back and sweep 1 of the
    census passes and of the pass before the first. ``snapshot_root`` / ``sweep_root`` may be lists (the host originals
    and a restore tree). Before anything is parsed, every sealed capture or sweep in the needed slot range must be
    present locally and every file to be opened must be sealed with an equal sha256, else the census is refused; slots
    with no capture and no sealed capture are counted as missing (census code check finding 1). Nothing after the last
    census slot is opened."""
    spec = spec or load_spec(sha=None)
    days = days or spec["census_inputs"]["capture_days_utc"]
    work = Path(work)
    by_slot, sweeps = _scan(work, snapshot_root, sweep_root, spec)
    K = census_slots(days, spec)
    ks = [k for k in K if k in by_slot]
    if not ks:
        return {"error": "no census captures", "days": days}
    w = int(spec["h"]["window_slots"])
    origins = [k for k in K if is_day_origin(k, spec)]
    cap_slots = set(range(min(K) - 1, max(K) + 1)) | set(range(min(K) - w, max(K) + 1)) | {j for k in origins for j in range(k - w - 12, k + 1)}
    sweep_slots = set(range(min(K) - 1, max(K) + 1))
    comp = seal_completeness(json.loads(Path(seal).read_text()), by_slot, sweeps, cap_slots, sweep_slots, spec, sweep_root) if verify else {}
    if verify and comp["bad"]:
        return {"error": "input identity check failed (L3): census refused", "bad": comp["bad"][:50], "n_bad": len(comp["bad"])}
    need = sorted(j for j in cap_slots if j in by_slot)
    for j in need:
        write_series(work, by_slot[j], spec)
    cache: dict = {}
    F, H, R, per_cap = [], [], [], []
    for k in ks:
        c = by_slot[k]
        ser_k, ser_p = _read(work, by_slot, k, cache), _read(work, by_slot, k - 1, cache)
        rec = {"capture": c["id"]}
        if ser_p is None:
            rec["skipped"] = "no previous slot"
            per_cap.append(rec)
            continue
        fu, fc = family_units(ser_k, ser_p, c, spec)
        fu["day"] = b._day([c["start"]] * len(fu)) if len(fu) else []
        F.append(fu)
        rec["F"] = fc
        if is_day_origin(k, spec):
            sbs = {j: _read(work, by_slot, j, cache) for j in range(k - w - 12, k + 1)}
            hu, hc = mark_units(sbs, k, spec)
            if len(hu):
                hu["day"] = b._day([c["start"]] * len(hu))
                H.append(hu)
            rec["H"] = hc
        if c["id"] in sweeps:
            swk = b.sweep_frame(sweeps[c["id"]]["dir"], c["dir"]).set_index("market_id")
            pc = by_slot.get(k - 1)
            swp = b.sweep_frame(sweeps[pc["id"]]["dir"], pc["dir"]).set_index("market_id") if pc and pc["id"] in sweeps else None
            ru, rc = rule_units(ser_k, ser_p, swk, swp, spec)
            ru["day"] = b._day([c["start"]] * len(ru)) if len(ru) else []
            R.append(ru)
            rec["R"] = rc
        else:
            rec["R"] = {"sweep": "missing"}
        per_cap.append(rec)
        for j in [j for j in list(cache) if j < k - w - 13]:
            cache.pop(j)
    scale = 21.0 / len(days)
    Fd = pd.concat(F, ignore_index=True) if F else pd.DataFrame()
    Hd = pd.concat(H, ignore_index=True) if H else pd.DataFrame()
    Rd = pd.concat(R, ignore_index=True) if R else pd.DataFrame()
    sbs_all = {j: _read(work, by_slot, j, {}) for j in range(min(K) - w, max(K) + 1)}
    P = d_hi_panel(sbs_all, ks, spec)
    h_missing = [b.iso(b.slot_time(k, spec)) for k in origins if k not in by_slot]
    return {"days": days, "captures": [by_slot[k]["id"] for k in ks], "per_capture": per_cap, "inputs_verified": bool(verify),
            "missing_slots": comp.get("missing_slots"), "n_missing_slots": comp.get("n_missing_slots"), "h_origins_missing": h_missing,
            "files_checked": comp.get("files_checked"),
            "CF5": census_f(Fd, spec, scale, days), "CHW": census_h(Hd, P, spec, scale, days, [r_["H"] for r_ in per_cap if "H" in r_]), "CRW": census_r(Rd, spec, scale, days)}


def _fam_rule(pop: pd.DataFrame, g: dict) -> tuple[pd.DataFrame, str, float | None]:
    return b._family_rule(pop, float(g["family_cap"])) if len(pop) else (pop, "", None)


def census_f(U: pd.DataFrame, spec: dict, scale: float, days: list[str]) -> dict:
    g, a = spec["census_gates"]["CF5_F"], spec["census_gates"]["mde_common"]
    if U.empty:
        return {"error": "no units", "gate_F": {"pass": False}}
    formed = U[U["level"] != ""]
    pop0 = formed[formed["cls_f"].isin(["idio", "common"])].copy()
    pop, excl, top = _fam_rule(pop0, g)
    pop = pop.copy()
    pop["ID"] = (pop["cls_f"] == "idio").astype(float)
    pop["common"] = (pop["cls_f"] == "common").astype(float)
    pop["parallel_qo"] = (pop["anat"] == "parallel").astype(float)
    pop["log1p_liq"] = np.log1p(pop["liq"].clip(lower=0))
    for d in ("traded", "parallel", "one_sided", "spread_change"):
        pop[f"a_{d}"] = (pop["anat"] == d).astype(float)
    mid = (pop["bid"] + pop["ask"]) / 2.0
    pop["log_abs_x"] = np.log(np.abs(pop["x"]))
    pop["logit_mid"] = np.log(mid / (1 - mid))
    pop["abs_dev"] = np.abs(mid - 0.5)
    pop["log1p_vol"] = np.log1p(pop["vol24_p"].clip(lower=0))
    pop["log_fam"] = np.log(pop["n_sib"] + 1.0)
    pop["series_level"] = (pop["level"] == "series").astype(float)
    ctrl = ["a_traded", "a_parallel", "a_one_sided", "a_spread_change", "log_abs_x", "spread", "logit_mid", "abs_dev", "log1p_vol",
            "log_fam", "series_level", "log1p_liq", "share_moving", "fam_abs"]
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    ni, nc = float(((pop["ID"] == 1) & eff).sum() * scale), float(((pop["ID"] == 0) & eff).sum() * scale)
    de = _de(pop, "fam_id", scale, g)
    dsg = design_ss(pop, "ID", ctrl)
    m1 = mde_class(ni, nc, a["sd_F"], de["DE_gate"], a, dsg["vif_w"])
    m2 = mde_slope_design(dsg["ss_resid"], scale, a["sd_F"], de["DE_gate"], a)
    mde = max(m1, m2) * 100.0
    ps = b.perm_share(pop, b.block_anchor(spec, days), int(spec["gates"]["perm_min_stratum"]))
    cc = wcorr(pop, "common", "parallel_qo")
    cl = wcorr(pop, "common", "log1p_liq")
    gl = U["guard_loss"].astype(int)
    size_bucket = pd.cut(U["n_sib"].where(U["level"] != "", np.nan), [0, 5, 10, 30, np.inf], labels=["3-5", "6-10", "11-30", ">30"])
    crypto_common = float((pop.loc[pop["common"] == 1, "crypto"] == 1).mean()) if (pop["common"] == 1).any() else float("nan")
    res = {"units": len(U), "formed": len(formed), "by_level": {str(k): int(v) for k, v in formed["level"].value_counts().items()},
           "by_class": {str(k): int(v) for k, v in formed["cls_f"].value_counts().items()}, "exclude_family": excl, "top_family_share": top,
           "idio_21d": float((pop["ID"] == 1).sum() * scale), "common_21d": float((pop["ID"] == 0).sum() * scale),
           "idio_eff_21d": ni, "common_eff_21d": nc, "design_effect_family": de, "design": dsg, "mde_class_c": m1 * 100, "mde_design_c": m2 * 100,
           "mde_eff_c": mde, "perm_share": ps, "corr_common_parallel": cc, "corr_common_liq": cl, "crypto_share_common": crypto_common,
           "guard_loss_share": float(gl.sum() / max(int((U["level"] != "").sum() + gl.sum()), 1)),
           "formed_by_family_size": {str(k): int(v) for k, v in size_bucket.value_counts().items()},
           "neg_risk_movers": int((U["neg_risk"] == 1).sum()), "negrisk_siblings_excluded": int(U["n_negrisk_excluded"].sum()), "events": int(pop["event_id"].nunique()), "families": int(pop["fam_id"].nunique())}
    res["gate_F"] = b._gate({"idio_21d": res["idio_21d"] >= g["idio_21d"], "common_21d": res["common_21d"] >= g["common_21d"],
                             "corr_common_parallel": corr_ok(cc, g["corr_max"]), "crypto_common": bool(crypto_common <= g["crypto_common_max"]),
                             "guard_loss": bool(res["guard_loss_share"] <= g["guard_loss_max"]), "corr_liq": corr_ok(cl, g["corr_max"], both=True),
                             "perm_share": ps["stratum"] is not None, "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return res


def census_h(U: pd.DataFrame, P: pd.DataFrame, spec: dict, scale: float, days: list[str], hc: list[dict] | None = None) -> dict:
    g, a = spec["census_gates"]["CHW_H"], spec["census_gates"]["mde_common"]
    if U.empty:
        return {"error": "no units", "gate_H": {"pass": False}}
    pop0 = U[U["cls_h"].isin(["near_high", "near_low", "far"])].copy()
    pop, excl, top = _fam_rule(pop0, g)
    pop = pop.copy()
    pop["NR"] = pop["cls_h"].isin(["near_high", "near_low"]).astype(float)
    near, far = pop[pop["NR"] == 1], pop[pop["NR"] == 0]
    both_days = pop.groupby("market_id")["day"].transform("nunique") >= 2
    n_eff, f_eff = float(((pop["NR"] == 1) & both_days).sum() * scale), float(((pop["NR"] == 0) & both_days).sum() * scale)
    de = _de(pop, "event_id", scale, g)
    m1 = mde_class(n_eff, f_eff, a["sd_H"], de["DE_gate"], a)
    mde = m1 * 100.0
    crypto_near = float((near["crypto"] == 1).mean()) if len(near) else float("nan")
    sd_ok = P.groupby("market_id").agg(sd=("d_hi", "std"), pa=("present_all", "max"))
    sd_ok = sd_ok[sd_ok["pa"] >= g["sd_min_present"]]
    sd_share = float((sd_ok["sd"] >= g["sd_d_hi_min"]).mean()) if len(sd_ok) else float("nan")
    elig = int(U.shape[0])
    hc = hc or []
    n_ns = sum(int(x.get("non_sports", 0)) for x in hc)
    inc_share = sum(int(x.get("hwm_incomplete", 0)) for x in hc) / n_ns if n_ns else float("nan")
    gap_share = sum(int(x.get("hwm_gap", 0)) for x in hc) / n_ns if n_ns else float("nan")
    cr = wcorr(pop, "NR", "s_d24h")
    mshare = float(both_days.mean()) if len(pop) else float("nan")
    res = {"units": elig, "by_class": {str(k): int(v) for k, v in U["cls_h"].value_counts().items()}, "exclude_family": excl,
           "top_family_share": top, "near_21d": float(len(near) * scale), "far_21d": float(len(far) * scale), "near_eff_21d": n_eff,
           "far_eff_21d": f_eff, "design_effect": de, "mde_eff_c": mde, "crypto_share_near": crypto_near,
           "d_hi_sd_share": sd_share, "d_hi_sd_markets": len(sd_ok), "corr_near_sd24": cr, "market_strata_share": mshare,
           "hwm_incomplete_share": inc_share, "hwm_gap_share": gap_share}
    res["gate_H"] = b._gate({"near_21d": res["near_21d"] >= g["near_21d"], "far_21d": res["far_21d"] >= g["far_21d"],
                             "crypto_near": bool(crypto_near <= g["crypto_near_max"]), "d_hi_sd": bool(sd_share >= g["sd_share_min"]),
                             "corr": corr_ok(cr, g["corr_max"]), "market_strata": bool(mshare >= g["perm_share_min"]),
                             "hwm_incomplete": bool(inc_share <= g["hwm_incomplete_max"]),
                             "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return res


def census_r(U: pd.DataFrame, spec: dict, scale: float, days: list[str]) -> dict:
    g, a = spec["census_gates"]["CRW_R"], spec["census_gates"]["mde_common"]
    if U.empty:
        return {"error": "no units", "gate_R": {"pass": False}}
    prim = U[U["primary_band"] == 1]
    rw, un = prim[prim["rewarded"] == 1], prim[prim["rewarded"] == 0]
    ms = rw["rew_maxspread"].dropna()  # all rewarded band units, both sides (census code check finding 2; section 6)
    band = "5c" if (len(ms) and float(ms.median()) >= g["band_rule_maxspread_c"]) else "1c"
    ic, dbc, dac = ("imb5", "dbid5", "dask5") if band == "5c" else ("imb1", "dbid1", "dask1")
    pop0 = rw[np.isfinite(rw[ic])].copy()
    pop, excl, top = _fam_rule(pop0, g)
    pop = pop.copy()
    sd_imb = float(pop[ic].std()) if len(pop) > 1 else float("nan")
    pop["z"] = (pop[ic] - pop[ic].mean()) / sd_imb if sd_imb and np.isfinite(sd_imb) else np.nan
    pop["z_in"] = pop["z"] * pop["inside"]
    pop["z_rf"], pop["z_rf_in"] = pop["z"] * pop["rf"], pop["z"] * pop["rf"] * pop["inside"]
    pop["rf_in"] = pop["rf"] * pop["inside"]
    pop["log1p_D"] = np.log1p(pop[dbc] + pop[dac])
    mid = pop["smid"]
    pop["logit_mid"] = np.log(mid / (1 - mid))
    ctrl = ["z", "z_rf", "z_rf_in", "inside", "rf", "rf_in", "sw_spread", "log1p_D", "logit_mid"]
    de = _de(pop, "event_id", scale, g)
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    dsg = design_ss(pop[eff], "z_in", ctrl)
    m_dsg = mde_slope_design(dsg["ss_resid"], scale, a["sd_R"], de["DE_gate"], a)
    m_decl = mde_slope_declared(float(eff.sum()) * scale, a["sd_R"], de["DE_gate"], a, dsg["vif_w"])
    mde = max(m_dsg, m_decl) * g["gap_sd"] * 100.0
    nin, nout = int((pop["inside"] == 1).sum()), int((pop["inside"] == 0).sum())
    cross = pop.groupby("market_id")["inside"].transform("nunique") >= 2
    cross_share, cross_mk = float(cross.mean()) if len(pop) else float("nan"), int(pop.loc[cross, "market_id"].nunique())
    iq = pop.groupby("market_id")[ic].agg(lambda v: float(np.quantile(v, 0.75) - np.quantile(v, 0.25)) if len(v) >= 10 else np.nan).dropna()
    iqr_share = float((iq >= g["imb_iqr_min"]).mean()) if len(iq) else float("nan")
    ins = pop[pop["inside"] == 1]
    minsize = ((ins[dbc] >= ins["rew_min"]) | (ins[dac] >= ins["rew_min"])) if len(ins) else pd.Series(dtype=bool)
    ms_share = float(minsize.mean()) if len(ins) else float("nan")
    ps = b.perm_share(pop, b.block_anchor(spec, days), int(spec["gates"]["perm_min_stratum"]))
    res = {"units": len(U), "primary_band_units": len(prim), "depth_band": band, "rewards_max_spread_median_band": float(ms.median()) if len(ms) else None,
           "rewards_max_spread_quantiles": [float(x) for x in np.quantile(ms, [0.1, 0.25, 0.5, 0.75, 0.9])] if len(ms) else None,
           "exclude_family": excl, "top_family_share": top, "rewarded_inside_21d": nin * scale, "rewarded_outside_21d": nout * scale,
           "unrewarded_inside_21d": float((un["inside"] == 1).sum() * scale), "unrewarded_outside_21d": float((un["inside"] == 0).sum() * scale),
           "rewarded_markets": int(rw["market_id"].nunique()), "crossing_unit_share": cross_share, "crossing_markets": cross_mk,
           "imb_iqr_share": iqr_share, "imb_iqr_markets": len(iq), "min_size_depth_present_share": ms_share, "imb_sd": sd_imb,
           "design_effect": de, "design": dsg, "mde_2sd_design_c": m_dsg * g["gap_sd"] * 100.0, "mde_2sd_declared_c": m_decl * g["gap_sd"] * 100.0,
           "mde_2sd_c": mde, "perm_share": ps,
           "fake_cutoff_band_units": int((U["primary_band"] == 0).sum())}
    res["gate_R"] = b._gate({"rewarded_inside": res["rewarded_inside_21d"] >= g["rewarded_side_21d"], "rewarded_outside": res["rewarded_outside_21d"] >= g["rewarded_side_21d"],
                             "unrewarded_inside": res["unrewarded_inside_21d"] >= g["unrewarded_side_21d"],
                             "unrewarded_outside": res["unrewarded_outside_21d"] >= g["unrewarded_side_21d"],
                             "imb_iqr": bool(iqr_share >= g["iqr_share_min"]) and len(iq) >= g["iqr_markets_min"],
                             "min_size_depth_present": bool(ms_share >= g["min_size_share_min"]),
                             "crossing": bool(cross_share >= g["crossing_share_min"]) and cross_mk >= g["crossing_markets_min"],
                             "perm_share": ps["stratum"] is not None, "mde": bool(mde <= g["mde_max"] * 100.0)})
    return res


def census_flow(*, seal: Path, capture_seal: Path, sample_roots: list[Path], snapshot_root=SNAPSHOT_ROOT, work: Path,
                spec: dict | None = None, verify: bool = True) -> dict:
    """CJ (J) and CO (O) on the sealed active-frame samples (LT3's C2 seal) with their captures k - 12 .. k (LT4's capture
    seal); refused on any mismatch. Trade rows with ts < the origin only; no target."""
    spec = spec or load_spec(sha=None)
    sl = json.loads(Path(seal).read_text())
    cseal = json.loads(Path(capture_seal).read_text()) if verify else {}
    work = Path(work)
    by_slot, _ = _scan(work, snapshot_root, None, spec)
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    bad, found = [], {}
    for sid in sl["samples"]:
        sdir = next((Path(r) / sid for r in sample_roots if (Path(r) / sid / "trades.csv.gz").exists()), None)
        if sdir is None:
            bad.append({"sample": sid, "error": "not found"})
            continue
        if verify:
            bad += [{"sample": sid, **x} for x in b.verify_files(sl, [(f"data-dumps/research_lab/trade_samples/{sid}/{fn}", sdir / fn)
                                                                     for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz")])]
        k = slot_by_id.get(b._manifest(sdir / "manifest.json").get("snapshot_id"))
        if k is None:
            bad.append({"sample": sid, "error": "capture not found"})
            continue
        found[sid] = (sdir, k)
    cap_slots = {j for _, k in found.values() for j in range(k - 12, k + 1)}
    comp = seal_completeness(cseal, by_slot, {}, cap_slots, set(), spec) if verify else {}
    bad += comp.get("bad", [])
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    J, OV, per = [], [], []
    tot = {"rows_interval": 0, "ts_not_minute": 0, "samples_skipped": 0}
    for sid, (sdir, k) in found.items():
        for j in range(k - 12, k + 1):
            if j in by_slot:
                write_series(work, by_slot[j], spec)
        if k - 1 not in by_slot:
            per.append({"sample": sid, "skipped": "no previous slot"})
            tot["samples_skipped"] += 1
            continue
        sbs = {j: b.read_series(work, by_slot[j]["id"]) if j in by_slot else None for j in range(k - 12, k + 1)}
        feat, tr = b.load_sample(sdir)
        tok = b.token0_map(by_slot[k]["dir"], feat["market_id"].astype(str)) if len(feat) else None
        ju, jc = path_units(sbs[k], sbs[k - 1], feat, tr, tok, by_slot[k], spec)
        ju["day"], ju["sample_id"] = sid[:8], sid
        J.append(ju)
        ou, oc = overhang_units(sbs[k], sbs, k, feat, tr, tok, by_slot[k], spec)
        ou["day"], ou["sample_id"] = sid[:8], sid
        OV.append(ou)
        tot["rows_interval"] += int(jc.get("interval_rows_all", 0))
        tot["ts_not_minute"] += int(jc.get("interval_rows_not_minute", 0))
        per.append({"sample": sid, "J": jc, "O": oc})
    Jd = pd.concat(J, ignore_index=True) if J else pd.DataFrame()
    Od = pd.concat(OV, ignore_index=True) if OV else pd.DataFrame()
    days = sorted({str(s_)[:8] for s_ in sl["samples"]})
    scale = 21.0 / max(len(days), 1)
    n_samples = len(found) - tot["samples_skipped"]  # samples actually used (census code check finding 1)
    return {"missing_capture_slots": comp.get("missing_slots"), "seal": str(seal), "capture_seal": str(capture_seal), "inputs_verified": bool(verify), "samples": n_samples, "per_sample": per,
            "totals": tot, "CJ": census_j(Jd, spec, scale, days, n_samples, per, tot), "CO": census_o(Od, spec, scale, days, n_samples, trunc24_share(per))}


def census_j(U: pd.DataFrame, spec: dict, scale: float, days: list[str], n_samples: int, per: list, tot: dict) -> dict:
    g, a = spec["census_gates"]["CJ_J"], spec["census_gates"]["mde_common"]
    if U.empty:
        return {"error": "no units", "gate_J": {"pass": False}}
    jg = U[U["cls_j"].isin(["jump", "grind"])]
    pop, excl, top = _fam_rule(jg, g)
    pop = pop.copy()
    pop["JP"] = (pop["cls_j"] == "jump").astype(float)
    pop["log1p_n_int"] = np.log1p(pop["n_int"])
    pop["log1p_liq"] = np.log1p(pop["liq"].clip(lower=0))
    per_pass = len(U) / max(n_samples, 1)
    js, gs = float((U["cls_j"] == "jump").mean()), float((U["cls_j"] == "grind").mean())
    jumps = U[U["cls_j"] == "jump"]
    j001 = float((np.abs(jumps["tick"] - 0.01) <= 1e-12).mean()) if len(jumps) else float("nan")
    traded = sum(int(p_.get("J", {}).get("sampled_traded", 0)) for p_ in per)  # section 8: of traded sampled movers
    trunc = sum(int(p_.get("J", {}).get("interval_truncated", 0)) for p_ in per)
    trunc_share = trunc / traded if traded else float("nan")
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    nj, ng = float(((pop["JP"] == 1) & eff).sum() * scale), float(((pop["JP"] == 0) & eff).sum() * scale)
    de = _de(pop, "event_id", scale, g)
    mde = mde_class(nj, ng, a["sd_J"], de["DE_gate"], a) * 100.0
    ps = b.perm_share(pop, b.block_anchor(spec, days), int(spec["gates"]["perm_min_stratum"]))
    cf, cn, cl = wcorr(pop, "JP", "fresh"), wcorr(pop, "JP", "log1p_n_int"), wcorr(pop, "JP", "log1p_liq")
    tsn = tot["ts_not_minute"] / tot["rows_interval"] if tot.get("rows_interval") else float("nan")
    res = {"qualifying": len(U), "qualifying_per_pass": per_pass, "jump_share": js, "grind_share": gs, "jumps_tick_0.01_share": j001,
           "interval_truncated_share": trunc_share, "exclude_family": excl, "top_family_share": top, "jump_eff_21d": nj, "grind_eff_21d": ng,
           "design_effect": de, "mde_eff_c": mde, "perm_share": ps, "corr_jump_fresh": cf, "corr_jump_nint": cn, "corr_jump_liq": cl,
           "ts_not_minute_share": tsn, "sports_share": float((pop["sports"] == 1).mean()) if len(pop) else None,
           "by_tick": {str(k): int(v) for k, v in U["tick"].value_counts().items()}}
    res["gate_J"] = b._gate({"ts_second_level": bool(tsn >= g["ts_not_minute_min"]), "per_pass": per_pass >= g["qualifying_per_pass"],
                             "jump_share": bool(js >= g["class_share_min"]), "grind_share": bool(gs >= g["class_share_min"]),
                             "tick_0.01": bool(j001 <= g["jump_tick001_max"]), "interval_truncated": bool(trunc_share <= g["truncated_max"]),
                             "corr_fresh": corr_ok(cf, g["corr_max"]), "corr_nint": corr_ok(cn, g["corr_max"]),
                             "corr_liq": corr_ok(cl, g["corr_max"], both=True), "perm_share": ps["stratum"] is not None,
                             "mde_eff": bool(mde <= g["mde_max"] * 100.0)})
    return res


def census_o(U: pd.DataFrame, spec: dict, scale: float, days: list[str], n_samples: int, trunc_share: float = float("nan")) -> dict:
    g, a = spec["census_gates"]["CO_O"], spec["census_gates"]["mde_common"]
    if U.empty:
        return {"error": "no units", "gate_O": {"pass": False}}
    pop, excl, top = _fam_rule(U, g)
    pop = pop.copy()
    Oc = pop["O"] * 100.0
    cO, sO = float(Oc.mean()), float(Oc.std())
    pop["zO"] = (Oc - cO) / sO if sO > 0 else np.nan
    t1, t2 = np.quantile(pop["zO"].dropna(), [1 / 3, 2 / 3]) if pop["zO"].notna().sum() >= 3 else (np.nan, np.nan)
    gap = float(pop.loc[pop["zO"] >= t2, "zO"].mean() - pop.loc[pop["zO"] <= t1, "zO"].mean()) if np.isfinite(t1) else float("nan")
    pop["abs_g"] = np.abs(pop["g"])
    pop["m_abs_d24"] = pop["m"] * np.abs(pop["d24h"])
    pop["logit_mid"] = np.log(pop["mid"] / (1 - pop["mid"]))
    pop["abs_dev"] = np.abs(pop["mid"] - 0.5)
    pop["log1p_n24"] = np.log1p(pop["n24"])
    ctrl = ["g", "abs_g", "m", "d2h", "d6h", "d24h", "chg_1d", "x6", "m_abs_d24", "logit_mid", "abs_dev", "spread", "log1p_n24"]
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    de = _de(pop, "event_id", scale, g)
    dsg = design_ss(pop[eff], "zO", ctrl)
    mde_sd = max(mde_slope_design(dsg["ss_resid"], scale, a["sd_O"], de["DE_gate"], a),
                 mde_slope_declared(float(eff.sum()) * scale, a["sd_O"], de["DE_gate"], a, dsg["vif_w"]))
    mde = mde_sd * gap * 100.0 if np.isfinite(gap) else float("inf")
    per_pass = len(U) / max(n_samples, 1)
    deg = float((np.abs(U["m"]) > g["m_degenerate"]).mean())
    iq = pop.groupby("market_id")["O"].agg(lambda v: float(np.quantile(v, 0.75) - np.quantile(v, 0.25)) * 100.0 if len(v) >= 6 else np.nan).dropna()
    iqr_share = float((iq >= g["O_iqr_min_c"]).mean()) if len(iq) else float("nan")
    rec = float((pop.groupby("market_id")["market_id"].transform("size") >= 2).mean())
    c1, c2 = wcorr(pop, "zO", "d24h"), wcorr(pop, "zO", "m_abs_d24")
    res = {"covered": len(U), "covered_per_pass": per_pass, "m_degenerate_share": deg, "exclude_family": excl, "top_family_share": top,
           "zO": {"centre_c": cO, "scale_c": sO, "terciles": [float(t1), float(t2)], "gap_sd": gap}, "design_effect": de, "design": dsg,
           "mde_per_sd_c": mde_sd * 100.0, "mde_tercile_c": mde, "O_iqr_share": iqr_share, "O_iqr_markets": len(iq),
           "block_gate_recurrence_share": rec, "trunc24_share": trunc_share, "corr_zO_d24": c1, "corr_zO_m_abs_d24": c2,
           "sports_share": float((pop["sports"] == 1).mean()) if len(pop) else None}
    res["gate_O"] = b._gate({"per_pass": per_pass >= g["covered_per_pass"], "trunc24": bool(trunc_share <= g["trunc24_max"]), "m_degenerate": bool(deg <= g["m_degenerate_share_max"]),
                             "O_iqr": bool(iqr_share >= g["iqr_share_min"]) and len(iq) >= g["iqr_markets_min"],
                             "corr_d24": corr_ok(c1, g["corr_max"]), "corr_m_abs_d24": corr_ok(c2, g["corr_flow_max"]),
                             "block_recurrence": bool(rec >= g["block_share_min"]), "mde": bool(mde <= g["mde_max"] * 100.0)})
    return res


def trunc24_share(per: list) -> float:
    """O's 24 h truncation share among units with >= 10 rows (census gate)."""
    a = sum(int(p.get("O", {}).get("trunc24", 0)) for p in per)
    n = sum(int(p.get("O", {}).get("with_min_rows", 0)) for p in per)
    return a / n if n else float("nan")


def cleanup_census(work: Path) -> None:
    b.cleanup_census(work)
