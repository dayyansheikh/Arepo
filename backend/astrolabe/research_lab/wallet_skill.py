# ruff: noqa: E501
"""Causal wallet-skill profiles and market-level skilled-flow features (signal-engine family ``wallet_skill``).

Research tooling only. Nothing here trades, labels a wallet as informed, or claims an edge. Wallets are HMAC hashes
(``wallet_sidecar.hash_wallet``); no raw address is read or written.

Design: ``docs/research_lab/signal_engine/families/WALLET_SKILL.md``. Prior art: Gómez-Cram, Guo, Jensen & Kung
(2026) sign-randomisation skill test (PRIOR_ART_2026-10-19.md gap 7); long-shot buys (gap 1).

Point-in-time rule (the one invariant every function keeps)
-----------------------------------------------------------
A wallet profile "as of t" uses ONLY positions in markets whose resolution was KNOWN strictly before t
(``known_ts < t``), built from trades that were ingested before t. Every trade of a resolved market precedes its
close, so no trade after t can enter. Market features at an origin use trades with ``ts < t_cut`` (the origin's
price-aligned cut-off) and the skilled set of a profile snapshot taken at or before the origin.

Accounting (per trade i: direction d = +1 BUY / -1 SELL of outcome k at price p for ``size`` shares)
-------------------------------------------------------------------------------------------------
* realised P&L at resolution: ``x_i = d (payout_k - p) size`` (a SELL is a short of outcome k, or a close);
* cash at risk: ``c_i = size p`` (BUY) or ``size (1 - p)`` (SELL); the price-implied win chance of the trade is ``c_i / size``;
* per (wallet, market) the trades are pooled into one *position* g (the unit that is sign-flipped, since all trades
  in one market share one outcome): ``x_g = A0 pay0 + A1 pay1 - B`` with ``A_k = sum d size [k_i = k]`` and
  ``B = sum d size p``. These sums are linear, so pending positions are kept as 6 floats per (wallet, market) and the
  outcome is applied only when it is known.

Per wallet (over resolved positions g = 1..n)
---------------------------------------------
* ``pnl = sum x_g``, ``cost = sum c_g``, ``ppd = pnl / cost`` (realised P&L per dollar at risk);
* ``hit_rate = mean[x_g > 0]``, ``implied_rate = mean(c_g / shares_g)``;
  ``calib_excess = mean(x_g / shares_g)`` (= share-weighted win minus price-implied chance, averaged over positions);
* sign-randomisation skill: under H0 (no skill) each position's direction is a fair coin, so ``S* = sum e_g x_g`` with
  ``e_g = +-1``: mean 0, variance ``Q = sum x_g^2`` exactly. ``skill_z = pnl / sqrt(Q)``; the Monte-Carlo p-value is
  ``sign_flip_pvalue``. Shrinkage for small n: ``skill_score = skill_z * sqrt(n / (n + N0))``, ``ppd_shr = ppd n/(n+N0)``,
  ``calib_shr = sum(x_g/shares_g) / (n + N0)``.
* skilled set at t: eligible wallets (``n >= MIN_POS``) with ``skill_z > 0`` whose ``skill_score`` is in the top
  ``TOP_FRAC`` of eligible wallets.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

SKILL_VERSION = "wallet-skill-v1"
FAMILY = "wallet_skill"
RES_LAG_S = 2 * 86400.0  # history data: an outcome counts as known 48 h after closedTime (HB1 rule); live: fetch receipt
MIN_POS = 5  # resolved positions needed to be ranked
SHRINK_N0 = 10.0  # pseudo-positions of the shrinkage
TOP_FRAC = 0.10  # top skill decile
LONGSHOT_MAX = 0.35  # a long-shot buy pays <= 0.35 (gap 1 / ACDC threshold)
ZFLOW_CLIP = 3.0
MIN_ELIGIBLE_SNAPSHOT = 200  # a live snapshot with fewer eligible wallets gives NaN features (warm-up)
WINDOWS_S = {"1h": 3600.0, "6h": 21600.0, "24h": 86400.0}
COLUMNS = ["ws_has", "ws_net1h", "ws_net6h", "ws_net24h", "ws_share24", "ws_nskill24", "ws_ls24", "ws_zflow24",
           "ws_cov24"]
GENERIC_COLUMNS = ["gen_net1h", "gen_net6h", "gen_net24h"]  # same clock, all wallets (comparator, not family columns)
POS_COLS = ["a0", "a1", "b", "cost", "shares", "n_trades"]
PROFILE_SUMS = ["n_pos", "n_trades", "pnl", "q", "cost", "hits", "implied", "edge"]


# ---------------------------------------------------------------------------------------------- trades


def normalise_trades(df: pd.DataFrame, wallet_col: str = "wallet_hash") -> pd.DataFrame:
    """Canonical trade frame: market_id, ts, wallet, d (+1/-1), k (0/1), price, size. Invalid rows are dropped."""
    side = df["side"].astype(str).str.upper()
    d = np.where(side == "BUY", 1, np.where(side == "SELL", -1, 0)).astype(np.int8)
    k = pd.to_numeric(df["outcome_index"], errors="coerce").to_numpy(float)
    p = pd.to_numeric(df["price"], errors="coerce").to_numpy(float)
    s = pd.to_numeric(df["size"], errors="coerce").to_numpy(float)
    ts = pd.to_numeric(df["ts"], errors="coerce").to_numpy(float)
    w = df[wallet_col]
    with np.errstate(invalid="ignore"):
        ok = (d != 0) & np.isin(k, (0.0, 1.0)) & (p > 0) & (p < 1) & (s > 0) & np.isfinite(ts) & w.notna().to_numpy()
    out = pd.DataFrame({"market_id": pd.to_numeric(df["market_id"]).to_numpy(np.int64)[ok], "ts": ts[ok],
                        "wallet": w.astype(str).to_numpy()[ok], "d": d[ok], "k": k[ok].astype(np.int8),
                        "price": p[ok], "size": s[ok]})
    return out


def position_terms(t: pd.DataFrame) -> pd.DataFrame:
    """Per-trade linear terms of a position (see module docstring)."""
    d = t["d"].to_numpy(float)
    s = t["size"].to_numpy(float)
    p = t["price"].to_numpy(float)
    k = t["k"].to_numpy()
    return pd.DataFrame({"wallet": t["wallet"].to_numpy(), "market_id": t["market_id"].to_numpy(np.int64),
                         "a0": np.where(k == 0, d * s, 0.0), "a1": np.where(k == 1, d * s, 0.0), "b": d * s * p,
                         "cost": np.where(d > 0, s * p, s * (1.0 - p)), "shares": s, "n_trades": np.ones(len(t))})


def aggregate_positions(t: pd.DataFrame) -> pd.DataFrame:
    """(wallet, market_id) -> summed position terms."""
    if not len(t):
        return pd.DataFrame(columns=["wallet", "market_id", *POS_COLS])
    return position_terms(t).groupby(["wallet", "market_id"], sort=False, as_index=False)[POS_COLS].sum()


# ---------------------------------------------------------------------------------------------- resolutions


def payouts_from_prices(outcome_prices: object) -> tuple[float, float] | None:
    """(pay0, pay1) for a final price vector: (1,0), (0,1) or the 50/50 split; None otherwise (not final)."""
    v = outcome_prices
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return None
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        return None
    try:
        a, b = float(v[0]), float(v[1])
    except (TypeError, ValueError):
        return None
    for pa_, pb in ((1.0, 0.0), (0.0, 1.0), (0.5, 0.5)):
        if abs(a - pa_) < 1e-9 and abs(b - pb) < 1e-9:
            return pa_, pb
    return None


def resolutions_from_sample(sample: pd.DataFrame, lag_s: float = RES_LAG_S) -> pd.DataFrame:
    """History ``sample.csv``: closed markets with a final price vector; known_ts = close_epoch + lag."""
    rows = []
    for r in sample.itertuples(index=False):
        if int(getattr(r, "closed", 0) or 0) != 1:
            continue
        pay = payouts_from_prices(r.outcome_prices)
        ce = float(r.close_epoch) if r.close_epoch == r.close_epoch else math.nan
        if pay is None or not math.isfinite(ce):
            continue
        rows.append((int(r.market_id), pay[0], pay[1], ce + lag_s, ce))
    return pd.DataFrame(rows, columns=["market_id", "pay0", "pay1", "known_ts", "close_ts"]).drop_duplicates("market_id")


def resolutions_from_engine_log(res: pd.DataFrame) -> pd.DataFrame:
    """Signal-engine ``load_resolutions`` frame (index market_id; state, y, fetched_ts) -> payouts, receipt-timed."""
    r = res.reset_index()
    ok = r["state"].isin(["resolved", "split_50_50"])
    r = r[ok]
    y = pd.to_numeric(r["y"], errors="coerce").to_numpy(float)
    split = (r["state"] == "split_50_50").to_numpy()
    pay0 = np.where(split, 0.5, y)
    good = np.isfinite(pay0)
    return pd.DataFrame({"market_id": r["market_id"].to_numpy(np.int64)[good], "pay0": pay0[good],
                         "pay1": 1.0 - pay0[good], "known_ts": r["fetched_ts"].to_numpy(float)[good],
                         "close_ts": r["closed_ts"].to_numpy(float)[good] if "closed_ts" in r else np.nan})


# ---------------------------------------------------------------------------------------------- skill statistics


def resolve_positions(pos: pd.DataFrame, res: pd.DataFrame) -> pd.DataFrame:
    """Attach payouts and compute per-position x, hit, implied and edge. ``res`` indexed by market_id."""
    r = res.reindex(pos["market_id"].to_numpy())
    x = pos["a0"].to_numpy(float) * r["pay0"].to_numpy(float) + pos["a1"].to_numpy(float) * r["pay1"].to_numpy(float) - pos["b"].to_numpy(float)
    sh = pos["shares"].to_numpy(float)
    out = pd.DataFrame({"wallet": pos["wallet"].to_numpy(), "n_pos": np.ones(len(pos)),
                        "n_trades": pos["n_trades"].to_numpy(float), "pnl": x, "q": x * x,
                        "cost": pos["cost"].to_numpy(float), "hits": (x > 1e-12).astype(float),
                        "implied": pos["cost"].to_numpy(float) / sh, "edge": x / sh})
    return out


def wallet_sums(resolved: pd.DataFrame) -> pd.DataFrame:
    if not len(resolved):
        return pd.DataFrame(columns=PROFILE_SUMS, index=pd.Index([], name="wallet"))
    return resolved.groupby("wallet", sort=False)[PROFILE_SUMS].sum()


def finish_profiles(sums: pd.DataFrame, n0: float = SHRINK_N0, min_pos: int = MIN_POS) -> pd.DataFrame:
    """Derived per-wallet statistics from the additive sums."""
    p = sums.copy()
    n = p["n_pos"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        p["ppd"] = np.where(p["cost"] > 0, p["pnl"] / p["cost"], np.nan)
        p["ppd_shr"] = p["ppd"] * n / (n + n0)
        p["hit_rate"] = p["hits"] / n
        p["implied_rate"] = p["implied"] / n
        p["calib_excess"] = p["edge"] / n
        p["calib_shr"] = p["edge"] / (n + n0)
        z = np.where(p["q"] > 0, p["pnl"] / np.sqrt(p["q"]), 0.0)
        p["skill_z"] = z
        p["skill_score"] = z * np.sqrt(n / (n + n0))
    p["eligible"] = n >= min_pos
    return p


def sign_flip_pvalue(x: np.ndarray, n_perm: int = 10000, seed: int = 0, exact_max: int = 16) -> float:
    """One-sided P(S* >= S) with S = sum x, S* = sum e x, e iid +-1 (exact enumeration for n <= exact_max)."""
    x = np.asarray(x, float)
    s = float(x.sum())
    n = len(x)
    if n == 0:
        return 1.0
    if n <= exact_max:
        signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
        return float(np.mean(signs @ x >= s - 1e-12))
    rng = np.random.default_rng(seed)
    hits = 0
    done = 0
    while done < n_perm:
        m = min(2000, n_perm - done)
        e = rng.integers(0, 2, size=(m, n), dtype=np.int8) * 2 - 1
        hits += int(np.sum(e @ x >= s - 1e-12))
        done += m
    return (hits + 1.0) / (n_perm + 1.0)


def skilled_set(prof: pd.DataFrame, top_frac: float = TOP_FRAC) -> tuple[set, float]:
    """Wallets in the top ``top_frac`` of skill_score among eligible wallets, with skill_z > 0. Returns (set, threshold)."""
    e = prof[prof["eligible"]]
    if not len(e):
        return set(), math.inf
    thr = float(np.quantile(e["skill_score"].to_numpy(float), 1.0 - top_frac))
    sel = e[(e["skill_score"] >= thr) & (e["skill_z"] > 0)]
    return set(sel.index), thr


def build_profiles_batch(trades: pd.DataFrame, res: pd.DataFrame, t: float, n0: float = SHRINK_N0,
                         min_pos: int = MIN_POS) -> pd.DataFrame:
    """Reference implementation: profiles as of t from trades with ts < t in markets with known_ts < t."""
    r = res.set_index("market_id") if "market_id" in res.columns else res
    known = r.index[r["known_ts"].to_numpy(float) < t]
    tt = trades[(trades["ts"].to_numpy(float) < t) & trades["market_id"].isin(known).to_numpy()]
    pos = aggregate_positions(tt)
    return finish_profiles(wallet_sums(resolve_positions(pos, r)), n0, min_pos)


# ---------------------------------------------------------------------------------------------- incremental builder


class ProfileBuilder:
    """Incremental, memory-light profiles: pending positions (6 floats per open wallet-market) + per-wallet sums.

    Usage per day: ``add_trades`` (trades received so far), ``add_resolutions`` (records with their known time), then
    ``advance_to(boundary)`` applies every pending position whose market's outcome was known strictly before the
    boundary and ``snapshot()`` gives the profiles as of that boundary. Trades of a market that arrive after its
    outcome was applied are applied at the next ``advance_to`` as a separate position (late data, never earlier).
    """

    def __init__(self, n0: float = SHRINK_N0, min_pos: int = MIN_POS) -> None:
        self.n0, self.min_pos = n0, min_pos
        self.pending = pd.DataFrame(columns=["wallet", "market_id", *POS_COLS])
        self.sums = pd.DataFrame(columns=PROFILE_SUMS, index=pd.Index([], name="wallet"), dtype=float)
        self.res = pd.DataFrame(columns=["pay0", "pay1", "known_ts"], index=pd.Index([], dtype=np.int64, name="market_id"))
        self.applied: set[int] = set()
        self.as_of = -math.inf
        self.max_trade_ts = -math.inf

    def add_trades(self, trades: pd.DataFrame) -> None:
        if not len(trades):
            return
        self.max_trade_ts = max(self.max_trade_ts, float(trades["ts"].max()))
        new = aggregate_positions(trades)
        self.pending = (pd.concat([self.pending, new], ignore_index=True) if len(self.pending) else new)
        self.pending = self.pending.groupby(["wallet", "market_id"], sort=False, as_index=False)[POS_COLS].sum()

    def add_resolutions(self, res: pd.DataFrame) -> None:
        r = res.set_index("market_id")[["pay0", "pay1", "known_ts"]] if "market_id" in res.columns else res[["pay0", "pay1", "known_ts"]]
        r = r[~r.index.isin(self.res.index)]  # first record wins: an applied outcome is never rewritten
        self.res = pd.concat([self.res, r]) if len(self.res) else r.copy()

    def advance_to(self, t: float, allow_future_trades: bool = False) -> int:
        """Apply pending positions of markets known strictly before t. Returns the number of positions applied.

        Guard: refuses when a trade at or after t was ingested (it could not have been received by t), unless
        ``allow_future_trades`` is set by a caller that guarantees every trade precedes its market's close (the
        history study drops post-close prints, so a position can only apply after all of its trades)."""
        if t < self.as_of:
            raise ValueError("advance_to cannot go back in time")
        if self.max_trade_ts >= t and not allow_future_trades:
            raise ValueError("trades at or after t were ingested; profiles as of t would not be point-in-time")
        self.as_of = t
        if not len(self.pending) or not len(self.res):
            return 0
        known = self.res.index[self.res["known_ts"].to_numpy(float) < t]
        m = self.pending["market_id"].isin(known).to_numpy()
        if not m.any():
            return 0
        go = self.pending[m]
        self.pending = self.pending[~m].reset_index(drop=True)
        add = wallet_sums(resolve_positions(go, self.res))
        self.sums = self.sums.add(add, fill_value=0.0) if len(self.sums) else add.astype(float)
        self.applied.update(int(x) for x in go["market_id"].unique())
        return int(len(go))

    def snapshot(self) -> pd.DataFrame:
        return finish_profiles(self.sums, self.n0, self.min_pos)

    # persistence (parquet + json; write-once snapshots are the caller's job)
    def save(self, d: Path) -> None:
        d = Path(d)
        d.mkdir(parents=True, exist_ok=True)
        self.pending.to_parquet(d / "pending.parquet", index=False)
        self.sums.reset_index().to_parquet(d / "sums.parquet", index=False)
        self.res.reset_index().to_parquet(d / "resolutions.parquet", index=False)
        (d / "builder.json").write_text(json.dumps({"version": SKILL_VERSION, "as_of": self.as_of, "n0": self.n0,
                                                    "min_pos": self.min_pos, "max_trade_ts": self.max_trade_ts,
                                                    "applied": sorted(self.applied)}))

    @classmethod
    def load(cls, d: Path) -> ProfileBuilder:
        d = Path(d)
        meta = json.loads((d / "builder.json").read_text())
        b = cls(meta["n0"], meta["min_pos"])
        b.pending = pd.read_parquet(d / "pending.parquet")
        b.sums = pd.read_parquet(d / "sums.parquet").set_index("wallet")
        b.res = pd.read_parquet(d / "resolutions.parquet").set_index("market_id")
        b.applied = set(meta["applied"])
        b.as_of = meta["as_of"]
        b.max_trade_ts = meta["max_trade_ts"]
        return b


class TradeDeduper:
    """Drops trades already seen in an earlier overlapping sample: per market, a ts watermark + the keys at it."""

    def __init__(self) -> None:
        self.wm: dict[int, float] = {}
        self.keys: dict[int, set] = {}

    @staticmethod
    def _keys(t: pd.DataFrame) -> list[tuple]:
        return list(zip(t["wallet"], t["d"].astype(int), t["k"].astype(int), t["price"].round(8), t["size"].round(8), strict=True))

    def new_only(self, t: pd.DataFrame) -> pd.DataFrame:
        if not len(t):
            return t
        t = t.sort_values(["market_id", "ts"], kind="stable").reset_index(drop=True)
        wm = t["market_id"].map(self.wm).fillna(-np.inf).to_numpy(float)
        ts = t["ts"].to_numpy(float)
        keep = ts > wm
        tie = np.flatnonzero(ts == wm)
        if len(tie):
            sub = t.iloc[tie]
            for j, m, key in zip(tie, sub["market_id"].to_numpy(), self._keys(sub), strict=True):
                keep[j] = key not in self.keys.get(int(m), set())
        new = t[keep]
        if len(new):
            top = new.groupby("market_id")["ts"].transform("max").to_numpy(float)
            at = new[new["ts"].to_numpy(float) == top]
            for m, g in at.groupby("market_id", sort=False):
                m = int(m)
                mx = float(g["ts"].iloc[0])
                if mx > self.wm.get(m, -math.inf):
                    self.wm[m] = mx
                    self.keys[m] = set(self._keys(g))
                else:
                    self.keys.setdefault(m, set()).update(self._keys(g))
        return new


# ---------------------------------------------------------------------------------------------- market features


def _segment_cumsums(keys: np.ndarray, vals: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {k: np.concatenate([[0.0], np.cumsum(v)]) for k, v in vals.items()} | {"_keys": keys}


def market_features(trades: pd.DataFrame, origins: pd.DataFrame, skilled: Iterable, scores: pd.Series | None = None,
                    eligible: Iterable | None = None, longshot_max: float = LONGSHOT_MAX) -> pd.DataFrame:
    """Skilled-wallet flow features at each origin row (market_id, t_cut[, covered_from]).

    Windows are ``[t_cut - W, t_cut)``. A window that starts before ``covered_from`` (truncated trade history) is NaN.
    Covered window with no trades: shares are 0. Signs point to outcome 0 (BUY outcome 0 or SELL outcome 1 = +1).
    Returns COLUMNS + GENERIC_COLUMNS aligned with ``origins``.
    """
    n = len(origins)
    out = {c: np.full(n, np.nan) for c in (*COLUMNS, *GENERIC_COLUMNS)}
    if n == 0:
        return pd.DataFrame(out)
    skilled = set(skilled)
    elig = set(eligible) if eligible is not None else (set(scores.index) if scores is not None else set())
    mids_o = origins["market_id"].to_numpy(np.int64)
    tcut = origins["t_cut"].to_numpy(float)
    cov = origins["covered_from"].to_numpy(float) if "covered_from" in origins else np.full(n, -np.inf)
    t = trades[trades["market_id"].isin(np.unique(mids_o))]
    out["ws_has"] = np.ones(n)  # every origin row here comes with a wallet source; absent source = caller's NaN
    if not len(t):
        for c in (*COLUMNS[1:], *GENERIC_COLUMNS):
            W = WINDOWS_S["1h"] if c.endswith("1h") else WINDOWS_S["6h"] if c.endswith("6h") else WINDOWS_S["24h"]
            out[c] = np.where(cov <= tcut - W, 0.0, np.nan)
        return pd.DataFrame(out)
    uniq = np.unique(np.concatenate([mids_o, t["market_id"].to_numpy(np.int64)]))
    rank = {m: i for i, m in enumerate(uniq)}
    BIG = 1e10
    tk = np.array([rank[m] for m in t["market_id"].to_numpy(np.int64)], float) * BIG + t["ts"].to_numpy(float)
    order = np.argsort(tk, kind="stable")
    tk = tk[order]
    t = t.iloc[order]
    w = t["wallet"].to_numpy()
    notional = t["size"].to_numpy(float) * t["price"].to_numpy(float)
    dir0 = t["d"].to_numpy(float) * np.where(t["k"].to_numpy() == 0, 1.0, -1.0)
    is_sk = np.fromiter((x in skilled for x in w), bool, len(w))
    is_el = np.fromiter((x in elig for x in w), bool, len(w))
    if scores is not None and len(scores):
        sc = np.clip(scores.reindex(w).fillna(0.0).to_numpy(float), -ZFLOW_CLIP, ZFLOW_CLIP)
    else:
        sc = np.zeros(len(w))
    ls = is_sk & (t["d"].to_numpy() > 0) & (t["price"].to_numpy(float) <= longshot_max)
    cs = _segment_cumsums(tk, {"n": notional, "gen": dir0 * notional, "sk": is_sk * notional,
                               "sknet": is_sk * dir0 * notional, "ls": ls * dir0 * notional,
                               "el": is_el * notional, "z": sc * dir0 * notional})
    ok_base = np.array([rank[m] for m in mids_o], float) * BIG
    hi = np.searchsorted(tk, ok_base + tcut, side="left")
    for tag, W in WINDOWS_S.items():
        lo = np.searchsorted(tk, ok_base + tcut - W, side="left")
        covered = cov <= tcut - W
        tot = cs["n"][hi] - cs["n"][lo]

        def share(name: str, lo: np.ndarray = lo, tot: np.ndarray = tot, covered: np.ndarray = covered) -> np.ndarray:
            v = cs[name][hi] - cs[name][lo]
            return np.where(covered, np.where(tot > 0, v / np.where(tot > 0, tot, 1.0), 0.0), np.nan)

        out[f"ws_net{tag}"] = share("sknet")
        out[f"gen_net{tag}"] = share("gen")
        if tag == "24h":
            out["ws_share24"] = share("sk")
            out["ws_ls24"] = share("ls")
            out["ws_zflow24"] = share("z")
            out["ws_cov24"] = share("el")
            # distinct skilled wallets buying in the window
            bsel = np.flatnonzero(is_sk & (t["d"].to_numpy() > 0))
            cnt = np.zeros(n)
            if len(bsel):
                bk = tk[bsel]
                blo = np.searchsorted(bk, ok_base + tcut - W, side="left")
                bhi = np.searchsorted(bk, ok_base + tcut, side="left")
                lens = bhi - blo
                if lens.sum():
                    oid = np.repeat(np.arange(n), lens)
                    idx = np.concatenate([np.arange(a, b) for a, b in zip(blo, bhi, strict=True) if b > a])
                    pairs = pd.DataFrame({"o": oid, "w": w[bsel][idx]}).drop_duplicates()
                    vc = pairs["o"].value_counts()
                    cnt[vc.index.to_numpy()] = vc.to_numpy(float)
            out["ws_nskill24"] = np.where(covered, np.log1p(cnt), np.nan)
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------------- engine adapter


def snapshot_frame(prof: pd.DataFrame, as_of: float, top_frac: float = TOP_FRAC) -> pd.DataFrame:
    """Compact write-once daily snapshot: eligible wallets only (wallet, skill_score, skill_z, n_pos, skilled)."""
    sk, _thr = skilled_set(prof, top_frac)
    e = prof[prof["eligible"]]
    return pd.DataFrame({"wallet": e.index.to_numpy(), "skill_score": e["skill_score"].to_numpy(np.float32),
                         "skill_z": e["skill_z"].to_numpy(np.float32), "n_pos": e["n_pos"].to_numpy(np.float32),
                         "skilled": np.isin(e.index.to_numpy(), list(sk)), "as_of": np.full(len(e), as_of)})


def family_features(sample_dir: Path | None, f: pd.DataFrame, snap: pd.DataFrame | None,
                    min_eligible: int = MIN_ELIGIBLE_SNAPSHOT) -> pd.DataFrame:
    """Signal-engine family function (same contract as ``signal_engine.features.wallet_features``).

    ``f``: the capture's eligible-market key frame (``market_id`` used). ``snap``: the latest ``snapshot_frame`` whose
    ``as_of`` is <= the capture start (the caller selects it; never a later one). Trades come from the capture's trade
    sample ``wallets.csv.gz`` with ts < the market's origin row receipt (``features.csv.gz`` ``origin_utc``).
    Missing source -> all NaN (never filled).
    """
    import pyarrow as pa
    import pyarrow.csv as pacsv

    out = pd.DataFrame({c: np.full(len(f), np.nan) for c in COLUMNS})
    if sample_dir is None or snap is None or len(snap) < min_eligible:
        return out
    wp, mp = Path(sample_dir) / "wallets.csv.gz", Path(sample_dir) / "wallets_manifest.json"
    try:
        man = json.loads(mp.read_text())
    except (OSError, ValueError):
        return out
    if not wp.exists() or man.get("sidecar_status") != "complete":
        return out
    try:
        limit = int(json.loads((Path(sample_dir) / "manifest.json").read_text()).get("limit") or 0)
    except (OSError, ValueError):
        limit = 0
    fe = pacsv.read_csv(Path(sample_dir) / "features.csv.gz", convert_options=pacsv.ConvertOptions(
        include_columns=["market_id", "status", "origin_utc", "n_returned"],
        column_types={"market_id": pa.int64(), "status": pa.string(), "origin_utc": pa.timestamp("us", tz="UTC"),
                      "n_returned": pa.float64()})).to_pandas()
    fe = fe[fe["status"] == "ok"].drop_duplicates("market_id").set_index("market_id")
    ons = pd.to_datetime(fe["origin_utc"], utc=True).astype("datetime64[ns, UTC]")
    origin = pd.Series(np.where(ons.isna().to_numpy(), np.nan, ons.astype("int64").to_numpy() / 1e9), index=fe.index)
    raw = pacsv.read_csv(wp, convert_options=pacsv.ConvertOptions(
        include_columns=["market_id", "ts", "side", "outcome_index", "size", "price", "wallet_hash"],
        column_types={"market_id": pa.int64(), "ts": pa.float64(), "side": pa.string(), "outcome_index": pa.float64(),
                      "size": pa.float64(), "price": pa.float64(), "wallet_hash": pa.string()})).to_pandas()
    tr = normalise_trades(raw)
    ids = f["market_id"].to_numpy(np.int64)
    t0 = origin.reindex(ids).to_numpy(float)
    have = np.isfinite(t0)
    if not have.any():
        return out
    # The sample holds the newest ``limit`` trades of each market: when the page was full (n_returned >= limit, or the
    # limit is unknown) a window is covered only if it starts at or after the oldest sampled trade; otherwise the
    # market's whole history is in the page.
    first = tr.groupby("market_id")["ts"].min().reindex(ids).to_numpy(float)
    nret = fe["n_returned"].reindex(ids).to_numpy(float)
    full = ~(nret < limit) if limit else np.ones(len(ids), bool)
    covered_from = np.where(full, np.where(np.isfinite(first), first, np.inf), -np.inf)
    o = pd.DataFrame({"market_id": ids[have], "t_cut": t0[have], "covered_from": covered_from[have]})
    sc = snap.set_index("wallet")["skill_score"].astype(float)
    feats = market_features(tr, o, set(snap.loc[snap["skilled"], "wallet"]), sc, eligible=set(snap["wallet"]))
    for c in COLUMNS:
        out.loc[have, c] = feats[c].to_numpy(float)
    return out
