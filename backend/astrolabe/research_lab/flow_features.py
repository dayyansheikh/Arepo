"""Origin-time trade-flow and wallet-behaviour features (research lab, DEVELOPMENT only).

IMPORTANT: none of these features identifies, labels or implies insider or informed trading.
Wallet quantities describe concentration and recency of pseudonymous (HMAC-hashed) addresses in
public taker trades; they are descriptive covariates whose predictive value is untested. Feature
names are deliberately neutral (``flow_*`` / ``wlt_*``).

Causality: every feature uses only trades with ``ts`` strictly before the market's snapshot
origin (``origin_epoch``). Trades at or after the origin are ignored. The first-seen index used for
"new-to-AREPO" is built only from previously collected sidecars (see ``FirstSeenIndex``).

Input is the ``wallets.csv.gz`` sidecar of one trade sample (same trades as ``trades.csv.gz`` with
hashed wallets). Sign convention is ``trade_sample._sign`` (signed on outcome 0).

Windows: 15 min, 1 h and 6 h before origin. The Data API returns at most 500 newest trades; if the
returned page does not reach back to the start of a window (page full and oldest trade younger than
the window start) that window is ``uncovered`` and its features are NaN, never extrapolated.

Definitions (all NaN when undefined; nothing is imputed):
  flow_imb_W           signed outcome-0 volume / volume in window W (W in 15m, 1h, 6h), in [-1, 1]
  flow_n_W             trade count in window W
  flow_burstiness_1h   (sigma - mu) / (sigma + mu) of inter-trade gaps in the last hour (Goh and
                       Barabasi B; needs >= 4 trades; -1 regular, 0 Poisson-like, -> 1 bursty)
  flow_accel_15m       log((n_15m/0.25 + 1) / (n_(15m,1h]/0.75 + 1)): trade-rate (per hour) of the
                       last 15 min relative to the preceding 45 min, +1 smoothed
  flow_max_trade_liq_1h  largest 1h trade notional (size*price) / market liquidity (origin value)
  flow_price_agree     +1 if sign(flow_imb_1h) == sign(recent outcome-0 price change), -1 if
                       opposite, NaN if either is zero/undefined. Recent price change defaults to
                       last minus first outcome-0 trade price within the last hour (>= 2 trades);
                       pass ``recent_price_change`` to use a panel quote change instead
  wlt_new_share_W      share of window volume (trades with a wallet) from wallets that are
                       "new-to-AREPO" at origin (W in 1h, 6h)
  wlt_hhi_W            Herfindahl index of per-wallet volume shares
  wlt_top1_share_W / wlt_top3_share_W   volume share of the largest 1 / 3 wallets
  wlt_n_buy_W / wlt_n_sell_W  distinct wallets whose net signed outcome-0 volume is > 0 / < 0
  wlt_agree_W          |n_buy - n_sell| / (n_buy + n_sell): same-direction agreement among
                       distinct wallets (1 = all net on one side)
  wlt_top3_exposure_liq_W  summed signed notional of the 3 largest wallets / liquidity
  wlt_age_activity_median_days   OPTIONAL, only if ``wallet_age_fn`` is supplied (see below)

"New-to-AREPO" (the only 'newness' used): a wallet is new at origin O with horizon N days iff the
index holds no trade of it with ts < O (never seen in AREPO's earlier collected samples), or its
first indexed ts satisfies O - first_ts < N days. Because AREPO's history is short, the share is
NaN unless the index spans at least N days before O (``wlt_index_span_days`` reports the span), so
early-history "everyone is new" artefacts are never emitted. This is NOT wallet age on Polymarket.

Wallet-age hook (not wired, no per-wallet requests are made here): ``wallet_age_fn`` maps a
wallet_hash to an age in days or None. A real implementation needs the raw address, which the
hash-only sidecar does not keep, and one Data API ``/activity?user=`` (or ``/positions``) call per
distinct wallet. At ~hundreds to thousands of distinct wallets per 2 h pass that is a large extra
request load on top of the ~2000 market requests, so it would have to run in the collector at
fetch time against raw addresses held only in memory, with its own rate budget and a persistent
hash -> age cache. Out of scope until separately approved.
"""

from __future__ import annotations

import gzip
import io
import json
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from .trade_sample import TRADE_LIMIT, _sign

VERSION = "flow-features-v1"
WINDOWS = {"15m": 900.0, "1h": 3600.0, "6h": 21600.0}
WALLET_WINDOWS = ("1h", "6h")
NEW_DAYS = 7.0
DAY_S = 86400.0
NAN = float("nan")


def feature_names() -> list[str]:
    names = []
    for w in WINDOWS:
        names += [f"flow_imb_{w}", f"flow_n_{w}", f"flow_covered_{w}"]
    names += ["flow_burstiness_1h", "flow_accel_15m", "flow_max_trade_liq_1h", "flow_price_agree"]
    for w in WALLET_WINDOWS:
        names += [f"wlt_new_share_{w}", f"wlt_hhi_{w}", f"wlt_top1_share_{w}",
                  f"wlt_top3_share_{w}", f"wlt_n_buy_{w}", f"wlt_n_sell_{w}", f"wlt_agree_{w}",
                  f"wlt_top3_exposure_liq_{w}", f"wlt_n_missing_{w}"]
    names += ["wlt_index_span_days", "wlt_age_activity_median_days"]
    return names


# --- first-seen index (point in time) ---------------------------------------------------------


class FirstSeenIndex:
    """wallet_hash -> earliest trade ts seen in previously collected sidecars.

    Build with ``build(sample_root, before_sample_id)``: only samples whose id sorts strictly
    before ``before_sample_id`` are read (sample ids start with a UTC timestamp, so lexical order
    is time order), in sorted order; the result is a pure function of those files, hence
    deterministic and rebuildable. A sample never sees its own or later samples.
    """

    def __init__(self) -> None:
        self.first_ts: dict[str, int] = {}
        self.min_ts: int | None = None  # earliest ts of any row (index span anchor)
        self.sample_ids: list[str] = []

    def add_frame(self, df: pd.DataFrame, sample_id: str | None = None) -> None:
        d = df[df["wallet_hash"].notna()]
        if len(d):
            for w, t in d.groupby("wallet_hash")["ts"].min().items():
                t = int(t)
                cur = self.first_ts.get(w)
                if cur is None or t < cur:
                    self.first_ts[w] = t
        if len(df):
            m = int(df["ts"].min())
            self.min_ts = m if self.min_ts is None else min(self.min_ts, m)
        if sample_id is not None:
            self.sample_ids.append(sample_id)

    @classmethod
    def build(cls, sample_root: Path, before_sample_id: str | None = None) -> FirstSeenIndex:
        idx = cls()
        root = Path(sample_root)
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            if before_sample_id is not None and d.name >= before_sample_id:
                break
            f = d / "wallets.csv.gz"
            if not f.exists():  # sidecar missing: skipped, never reconstructed
                continue
            idx.add_frame(read_wallets(f), d.name)
        return idx

    def first_seen(self, wallet_hash: str, origin_epoch: float) -> int | None:
        """Earliest indexed ts strictly before the origin, else None."""
        t = self.first_ts.get(wallet_hash)
        return t if t is not None and t < origin_epoch else None

    def span_days(self, origin_epoch: float) -> float:
        if self.min_ts is None or self.min_ts >= origin_epoch:
            return 0.0
        return (origin_epoch - self.min_ts) / DAY_S

    def is_new(self, wallet_hash: str, origin_epoch: float, new_days: float = NEW_DAYS) -> bool:
        t = self.first_seen(wallet_hash, origin_epoch)
        return t is None or (origin_epoch - t) < new_days * DAY_S

    def digest(self) -> str:
        import hashlib
        h = hashlib.sha256()
        for w in sorted(self.first_ts):
            h.update(f"{w},{self.first_ts[w]}\n".encode())
        return h.hexdigest()

    def write(self, path: Path) -> None:
        """Deterministic csv.gz (sorted by wallet_hash; mtime 0) for inspection/caching."""
        df = pd.DataFrame(sorted(self.first_ts.items()), columns=["wallet_hash", "first_ts"])
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
            gz.write(df.to_csv(index=False).encode())
        path.write_bytes(buf.getvalue())


def read_wallets(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"market_id": str, "condition_id": str, "asset": str,
                                    "wallet_hash": str})


# --- feature computation ----------------------------------------------------------------------


def _signed(df: pd.DataFrame, token0: str | None) -> np.ndarray:
    return np.array([_sign({"outcome_index": None if pd.isna(oi) else int(oi), "side": s,
                            "asset": None if pd.isna(a) else str(a)}, token0)
                     for oi, s, a in zip(df["outcome_index"], df["side"], df["asset"],
                                         strict=True)], dtype=float)


def _p0(df: pd.DataFrame) -> pd.DataFrame:
    """Known-outcome rows with ``p0`` = outcome-0 implied price (1 - price for outcome 1)."""
    k = df[df["outcome_index"].isin([0, 1])].copy()
    k["p0"] = np.where(k["outcome_index"] == 1, 1.0 - k["price"], k["price"])
    return k.sort_values("ts", kind="stable")


def _burstiness(ts: np.ndarray) -> float:
    if len(ts) < 4:
        return NAN
    gaps = np.diff(np.sort(ts))
    mu, sd = gaps.mean(), gaps.std()
    return float((sd - mu) / (sd + mu)) if (sd + mu) > 0 else NAN


def compute_flow_features(
        trades: pd.DataFrame, origin_epoch: float, *, liquidity: float | None = None,
        token0: str | None = None, first_seen: FirstSeenIndex | None = None,
        n_returned: int | None = None, limit: int = TRADE_LIMIT,
        recent_price_change: float | None = None, new_days: float = NEW_DAYS,
        wallet_age_fn: Callable[[str], float | None] | None = None) -> dict:
    """Features for ONE market from its sidecar rows; uses only ``ts < origin_epoch``.

    ``n_returned``: size of the API page (defaults to ``len(trades)``); a full page that does not
    reach back to a window's start marks that window uncovered (features NaN).
    """
    out = {k: NAN for k in feature_names()}
    n_ret = len(trades) if n_returned is None else n_returned
    oldest = float(trades["ts"].min()) if len(trades) else None
    d = trades[trades["ts"] < origin_epoch].copy()
    d["sign"] = _signed(d, token0) if len(d) else np.array([])
    d["notional"] = d["size"] * d["price"]
    liq_ok = liquidity is not None and np.isfinite(liquidity) and liquidity > 0

    def covered(w: float) -> bool:
        return not (n_ret >= limit and oldest is not None and oldest > origin_epoch - w)

    win = {}
    for name, w in WINDOWS.items():
        cov = covered(w)
        sub = d[d["ts"] >= origin_epoch - w]
        win[name] = sub
        out[f"flow_covered_{name}"] = float(cov)
        out[f"flow_n_{name}"] = float(len(sub)) if cov else NAN
        vol = float(sub["size"].sum())
        if cov and vol > 0:
            out[f"flow_imb_{name}"] = float((sub["sign"] * sub["size"]).sum() / vol)

    h1 = win["1h"]
    if covered(WINDOWS["1h"]):
        out["flow_burstiness_1h"] = _burstiness(h1["ts"].to_numpy(float))
        n15 = float((h1["ts"] >= origin_epoch - WINDOWS["15m"]).sum())
        nrest = float(len(h1)) - n15
        out["flow_accel_15m"] = math.log((n15 / 0.25 + 1.0) / (nrest / 0.75 + 1.0))
        if liq_ok and len(h1):
            out["flow_max_trade_liq_1h"] = float(h1["notional"].max() / liquidity)
        if recent_price_change is not None and np.isfinite(recent_price_change):
            dp = float(recent_price_change)
        else:
            k = _p0(h1)
            dp = float(k["p0"].iloc[-1] - k["p0"].iloc[0]) if len(k) >= 2 else NAN
        imb = out["flow_imb_1h"]
        if np.isfinite(dp) and np.isfinite(imb) and dp != 0 and imb != 0:
            out["flow_price_agree"] = float(np.sign(imb) * np.sign(dp))

    if first_seen is not None:
        out["wlt_index_span_days"] = first_seen.span_days(origin_epoch)
    for name in WALLET_WINDOWS:
        if not covered(WINDOWS[name]):
            continue
        sub = win[name]
        has = sub["wallet_hash"].notna()
        out[f"wlt_n_missing_{name}"] = float((~has).sum())
        s = sub[has]
        vol = float(s["size"].sum())
        if len(s) == 0 or vol <= 0:
            continue
        per = s.groupby("wallet_hash").agg(vol=("size", "sum"))
        per["net"] = (s["sign"] * s["size"]).groupby(s["wallet_hash"]).sum()
        per["net_notional"] = (s["sign"] * s["notional"]).groupby(s["wallet_hash"]).sum()
        per = per.sort_values(["vol"], ascending=False, kind="stable")
        share = (per["vol"] / vol).to_numpy()
        out[f"wlt_hhi_{name}"] = float((share ** 2).sum())
        out[f"wlt_top1_share_{name}"] = float(share[:1].sum())
        out[f"wlt_top3_share_{name}"] = float(share[:3].sum())
        nb, ns = int((per["net"] > 0).sum()), int((per["net"] < 0).sum())
        out[f"wlt_n_buy_{name}"], out[f"wlt_n_sell_{name}"] = float(nb), float(ns)
        if nb + ns > 0:
            out[f"wlt_agree_{name}"] = abs(nb - ns) / (nb + ns)
        if liq_ok:
            out[f"wlt_top3_exposure_liq_{name}"] = float(per["net_notional"].iloc[:3].sum()
                                                         / liquidity)
        if first_seen is not None and first_seen.span_days(origin_epoch) >= new_days:
            new = per.index.map(lambda w: first_seen.is_new(w, origin_epoch, new_days))
            out[f"wlt_new_share_{name}"] = float(per["vol"][np.asarray(new, bool)].sum() / vol)
    if wallet_age_fn is not None and covered(WINDOWS["6h"]):
        ages = [a for a in (wallet_age_fn(w) for w in
                            d[d["ts"] >= origin_epoch - WINDOWS["6h"]]["wallet_hash"].dropna()
                            .unique()) if a is not None and np.isfinite(a)]
        if ages:
            out["wlt_age_activity_median_days"] = float(np.median(ages))
    return out


def features_for_sample(sample_dir: Path, liquidity: dict[str, float] | None = None, *,
                        first_seen: FirstSeenIndex | None = None,
                        sample_root: Path | None = None, new_days: float = NEW_DAYS,
                        wallet_age_fn: Callable[[str], float | None] | None = None
                        ) -> pd.DataFrame:
    """One row per market of a sample (plan order). ``liquidity``: market_id -> origin liquidity.

    If ``first_seen`` is omitted it is rebuilt from the sidecars in ``sample_root`` (default: the
    sample's parent directory) strictly earlier than this sample.
    """
    d = Path(sample_dir)
    plan = json.loads((d / "plan.json").read_text())
    if first_seen is None:
        first_seen = FirstSeenIndex.build(sample_root or d.parent, d.name)
    w = read_wallets(d / "wallets.csv.gz")
    feats = pd.read_csv(d / "features.csv.gz", dtype={"market_id": str})
    nret = dict(zip(feats["market_id"], feats["n_returned"], strict=True))
    by_market = {k: g for k, g in w.groupby("market_id")}
    empty = w.iloc[0:0]
    rows = []
    for m in plan["sample"]:
        mid = m["market_id"]
        origin = pd.Timestamp(m["origin_utc"]).timestamp()
        nr = nret.get(mid)
        f = compute_flow_features(
            by_market.get(mid, empty), origin,
            liquidity=None if liquidity is None else liquidity.get(mid), token0=m.get("token0"),
            first_seen=first_seen, n_returned=None if pd.isna(nr) else int(nr),
            new_days=new_days, wallet_age_fn=wallet_age_fn)
        rows.append({"sample_id": plan["sample_id"], "market_id": mid, **f})
    return pd.DataFrame(rows)

