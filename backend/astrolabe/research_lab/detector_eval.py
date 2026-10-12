"""Frozen-rule registry, rare-event evaluation engine and held-out harness for the unusual-flow
programme (``docs/research_lab/UNUSUAL_FLOW_PROGRAMME.md``).

IMPORTANT: nothing here identifies, labels or implies insider or informed trading. A "rule" selects
market-hours whose public, hashed taker-flow features look unusual; the engine asks whether those
hours are followed by large price moves more often than matched hours it did not select. Every
result is DEVELOPMENT / exploratory until a registered live test is scored.

Pieces
------
* ``RuleSpec``: declarative rule (conditions + weighted, clipped, standardised terms). Its sha256 is
  taken over canonical JSON, so the same spec hashes the same everywhere; ``center``/``scale`` are
  numbers written into the spec from tuning data, never recomputed from the evaluated panel.
* ``RuleRegistry`` / ``freeze_rules``: ``detector_specs/<rule_id>.json`` plus ``FROZEN.json``
  (sha256, engine version, freeze commit). A rule_id is never overwritten.
* ``normalise_panel``: maps the historical (``ml_tf_*``/``ml_wlt_*``) or live (``flow_*``/``wlt_*``)
  column names onto one canonical schema and records the mapping id.
* ``evaluate``: alert budget -> episodes -> matched-control excess precision with event-clustered
  bootstrap (primary), random-budget placebo, recall on large moves, lead time, cost-aware paper
  P&L through ``economics``. Rows without a trade before ``t`` are excluded (not executable prices).
* ``HeldOutHarness``: refuses any rule that is not frozen, whose spec no longer matches its frozen
  hash, whose engine version differs, or any run without a valid ``evidence_role``; appends one
  ``trials.jsonl`` line per run (kind ``detector_eval``).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from . import economics, provenance
from .ml_explain import cluster_boot, holm

ENGINE_VERSION = "detector-eval-v1"
TRIAL_KIND = "detector_eval"
HERE = Path(__file__).resolve().parent
SPEC_DIR = HERE / "detector_specs"
FROZEN_INDEX = "FROZEN.json"
DEFAULT_ROLE = "exploratory_historical"
PANEL_MAP_VERSION = "detector-panel-map-v1"

# Canonical panel schema (programme doc section 3). ``_s`` short window (1h live / 2h history),
# ``_l`` long window (6h live / 24h history).
FLOW_FEATURES = (
    "imb_s", "n_s", "n_l", "burst", "large_trade_rel", "top1_share_l", "hhi_l", "n_wallets_s",
    "n_wallets_l", "new_wallet_share_l", "new_wallets_s", "last_trade_age_h", "ltp_minus_mid",
    "mid_change_s",  # mid(t) - mid(t - short window): history ml_own_dmid_prev (2h), live chg_1h
)
# Derived at t from canonical columns (theory doc section 4 hand-off, batch 2). ``p_acq`` = price of
# the outcome the short-window flow acquires; ``resp_s`` = price response signed by the flow.
DERIVED_FEATURES = ("p_acq", "resp_s")
CONTEXT_FEATURES = ("mid", "liquidity", "spread")
RULE_FEATURES = (*FLOW_FEATURES, *DERIVED_FEATURES, *CONTEXT_FEATURES)
IDENTITY = ("market_id", "cluster", "t", "mid", "liquidity", "traded_before_t")
HORIZONS_H = (2, 6, 24)
OPS = {
    "gt": lambda x, v: x > v, "ge": lambda x, v: x >= v, "lt": lambda x, v: x < v,
    "le": lambda x, v: x <= v, "abs_ge": lambda x, v: np.abs(x) >= v,
    "abs_gt": lambda x, v: np.abs(x) > v,
}
TRANSFORMS = {"raw": lambda x: x, "abs": np.abs, "log1p": lambda x: np.log1p(np.maximum(x, 0.0)),
              "neg": lambda x: -x}
PRICE_BANDS = (0.05, 0.20, 0.45)  # on |mid - 0.5|
DAY_S = 86400.0
MIN_EPISODES = economics.MIN_TRADES
MIN_CLUSTERS = economics.MIN_CLUSTERS


class DetectorError(RuntimeError):
    """Base class for registry / harness refusals."""


class NotFrozenError(DetectorError):
    """The rule_id is not in FROZEN.json."""


class SpecTamperedError(DetectorError):
    """The spec's recomputed sha256 differs from the frozen one."""


class EngineVersionError(DetectorError):
    """The rule was frozen under a different engine version."""


class PanelError(ValueError):
    """The panel does not satisfy the canonical contract."""


# --- 1. rule specification --------------------------------------------------------------------


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    version: str
    theory_ref: str
    conditions: tuple[dict, ...] = ()
    terms: tuple[dict, ...] = ()
    min_terms_present: int = 1
    direction_feature: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id or not self.version or not self.theory_ref:
            raise ValueError("rule_id, version and theory_ref are required")
        for c in self.conditions:
            if set(c) != {"feature", "op", "value"}:
                raise ValueError(f"condition keys must be feature/op/value: {c}")
            if c["feature"] not in RULE_FEATURES or c["op"] not in OPS:
                raise ValueError(f"bad condition {c}")
            if not math.isfinite(float(c["value"])):
                raise ValueError(f"non-finite condition value {c}")
        if not self.terms and self.direction_feature is None and not self.conditions:
            raise ValueError("a rule needs at least one condition or term")
        for t in self.terms:
            if set(t) != {"feature", "transform", "center", "scale", "weight", "cap"}:
                raise ValueError(
                    f"term keys must be feature/transform/center/scale/weight/cap: {t}")
            if t["feature"] not in RULE_FEATURES or t["transform"] not in TRANSFORMS:
                raise ValueError(f"bad term {t}")
            vals = [float(t[k]) for k in ("center", "scale", "weight", "cap")]
            if not all(math.isfinite(v) for v in vals) or vals[1] <= 0 or vals[3] <= 0:
                raise ValueError(f"term needs finite numbers, scale > 0 and cap > 0: {t}")
        if self.min_terms_present < 0 or self.min_terms_present > len(self.terms):
            raise ValueError("min_terms_present must be in [0, len(terms)]")
        if self.direction_feature is not None and self.direction_feature not in RULE_FEATURES:
            raise ValueError(f"unknown direction_feature {self.direction_feature!r}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["conditions"] = [dict(c) for c in self.conditions]
        d["terms"] = [dict(t) for t in self.terms]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> RuleSpec:
        d = dict(d)
        d["conditions"] = tuple(dict(c) for c in d.get("conditions", ()))
        d["terms"] = tuple(dict(t) for t in d.get("terms", ()))
        return cls(**d)

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()


def score_rule(spec: RuleSpec, panel: pd.DataFrame) -> pd.DataFrame:
    """Per-row ``score`` (higher = more unusual), ``alertable`` and ``direction`` (+1 outcome 0,
    -1 outcome 1, 0 undirected / unknown). Nothing in the panel is used to set centres or scales."""
    n = len(panel)
    ok = np.ones(n, bool)
    for c in spec.conditions:
        x = panel[c["feature"]].to_numpy(float)
        ok &= np.isfinite(x) & OPS[c["op"]](x, float(c["value"]))
    score = np.zeros(n)
    present = np.zeros(n, int)
    for t in spec.terms:
        x = TRANSFORMS[t["transform"]](panel[t["feature"]].to_numpy(float))
        z = np.clip((x - float(t["center"])) / float(t["scale"]), -float(t["cap"]), float(t["cap"]))
        fin = np.isfinite(z)
        score += np.where(fin, float(t["weight"]) * z, 0.0)
        present += fin
    alertable = ok & (present >= spec.min_terms_present)
    direction = np.zeros(n, int)
    if spec.direction_feature is not None:
        dv = panel[spec.direction_feature].to_numpy(float)
        direction = np.where(np.isfinite(dv), np.sign(dv), 0).astype(int)
        alertable &= direction != 0
    return pd.DataFrame({"score": np.where(alertable, score, np.nan), "alertable": alertable,
                         "direction": direction}, index=panel.index)


# --- 2. registry and freezing -----------------------------------------------------------------


def _git_head() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True,
                           timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        return provenance.UNKNOWN
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else provenance.UNKNOWN


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_index(spec_dir: Path = SPEC_DIR) -> dict:
    p = Path(spec_dir) / FROZEN_INDEX
    if not p.exists():
        return {"frozen": []}
    return json.loads(p.read_text(encoding="utf-8"))


def freeze_rules(specs: list[RuleSpec], spec_dir: Path = SPEC_DIR, *, commit: str | None = None,
                 now: str | None = None) -> dict:
    """Write each spec and append it to FROZEN.json. Refuses to overwrite an existing rule_id."""
    spec_dir = Path(spec_dir)
    spec_dir.mkdir(parents=True, exist_ok=True)
    index = read_index(spec_dir)
    have = {e["rule_id"] for e in index["frozen"]}
    ids = [s.rule_id for s in specs]
    if len(set(ids)) != len(ids):
        raise DetectorError("duplicate rule_id in freeze batch")
    clash = have.intersection(ids)
    if clash:
        raise DetectorError(f"rule_id already frozen, never overwritten: {sorted(clash)}")
    stamp = now or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = commit or _git_head()
    for s in specs:
        _atomic_write(spec_dir / f"{s.rule_id}.json", json.dumps(s.to_dict(), indent=1,
                                                                 sort_keys=True) + "\n")
        index["frozen"].append({"rule_id": s.rule_id, "version": s.version, "sha256": s.sha256(),
                                "engine_version": ENGINE_VERSION, "frozen_utc": stamp,
                                "frozen_commit": head})
    _atomic_write(spec_dir / FROZEN_INDEX, json.dumps(index, indent=1, sort_keys=True) + "\n")
    return index


class RuleRegistry:
    """Read-only view of the frozen specs. ``load`` verifies hash and engine version."""

    def __init__(self, spec_dir: Path = SPEC_DIR) -> None:
        self.spec_dir = Path(spec_dir)

    def entries(self) -> dict[str, dict]:
        return {e["rule_id"]: e for e in read_index(self.spec_dir)["frozen"]}

    def frozen_ids(self) -> list[str]:
        return sorted(self.entries())

    def is_frozen(self, rule_id: str) -> bool:
        return rule_id in self.entries()

    def load(self, rule_id: str) -> RuleSpec:
        entry = self.entries().get(rule_id)
        if entry is None:
            raise NotFrozenError(f"rule {rule_id!r} is not frozen (not in {FROZEN_INDEX})")
        if entry.get("engine_version") != ENGINE_VERSION:
            raise EngineVersionError(f"rule {rule_id!r} frozen under engine "
                                     f"{entry.get('engine_version')!r}, running {ENGINE_VERSION!r}")
        path = self.spec_dir / f"{rule_id}.json"
        if not path.exists():
            raise SpecTamperedError(f"frozen spec file missing: {path.name}")
        spec = RuleSpec.from_dict(json.loads(path.read_text(encoding="utf-8")))
        self.verify(spec, entry)
        return spec

    def verify(self, spec: RuleSpec, entry: dict | None = None) -> str:
        """Return the frozen sha256 if ``spec`` matches it exactly; refuse otherwise."""
        entry = entry or self.entries().get(spec.rule_id)
        if entry is None:
            raise NotFrozenError(f"rule {spec.rule_id!r} is not frozen")
        digest = spec.sha256()
        if digest != entry["sha256"]:
            raise SpecTamperedError(
                f"rule {spec.rule_id!r}: spec sha256 {digest[:12]} differs from frozen "
                f"{entry['sha256'][:12]}; a changed rule is a new rule_id")
        return digest


# --- 3. panel normalisation -------------------------------------------------------------------


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    return df[name].astype(float) if name in df else pd.Series(np.nan, index=df.index)


def _history_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """history_backfill panels carry one horizon per row; pivot them to ``fwd_move_{h}h``."""
    if "horizon_target_h" not in df or "y_dmid" not in df:
        return df
    hs = sorted(int(h) for h in df["horizon_target_h"].dropna().unique())
    key = ["market_id", "t_i"]
    base = df[df["horizon_target_h"] == hs[0]].drop(columns=[c for c in (
        "t_j", "mid_j", "dmid", "horizon_h", "horizon_target_h", "y_class", "y_class_sens",
        "y_dmid", "y_absmove", "target_available", "target_quote_age_s") if c in df])
    for h in hs:
        sub = df.loc[df["horizon_target_h"] == h, [*key, "y_dmid"]].rename(
            columns={"y_dmid": f"fwd_move_{h}h"})
        base = base.merge(sub.drop_duplicates(key), on=key, how="left")
    return base


def normalise_panel(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Canonical detector panel from a ``history_backfill`` panel (``source='history'``) or a live
    ``flow_features`` frame (``source='live'``). Missing inputs become NaN; the mapping and the
    list of unmapped canonical columns are recorded in ``out.attrs``."""
    if source not in ("history", "live"):
        raise PanelError("source must be 'history' or 'live'")
    if source == "history":
        df = _history_outcomes(df)
    out = pd.DataFrame(index=df.index)
    out["market_id"] = df["market_id"].astype(str)
    ev = df["event_id"].astype(str) if "event_id" in df else pd.Series("", index=df.index)
    out["cluster"] = np.where(ev.str.len() > 0, ev, out["market_id"])
    if source == "history":
        out["t"] = _col(df, "t_i")
        out["mid"] = _col(df, "mid_i")
        share = _col(df, "ml_tf_buy_share_2h")
        m = {
            "imb_s": 2.0 * share - 1.0, "n_s": _col(df, "ml_tf_n_2h"),
            "n_l": _col(df, "ml_tf_n_24h"),
            "burst": _col(df, "ml_tf_burst_2h"), "large_trade_rel": _col(df, "ml_tf_large_2h"),
            "top1_share_l": _col(df, "ml_wlt_top1_24h"), "hhi_l": _col(df, "ml_wlt_hhi_24h"),
            "n_wallets_s": _col(df, "ml_tf_n_wallets_2h"),
            "n_wallets_l": _col(df, "ml_tf_n_wallets_24h"),
            "new_wallet_share_l": _col(df, "ml_wlt_new_share_24h"),
            "new_wallets_s": _col(df, "ml_wlt_new_n_2h"),
            "last_trade_age_h": _col(df, "ml_tf_last_age_h"),
            "ltp_minus_mid": _col(df, "ml_tf_ltp_minus_mid"),
            "mid_change_s": _col(df, "ml_own_dmid_prev"),
        }
        out["spread"] = _col(df, "spread")
    else:
        out["t"] = _col(df, "t") if "t" in df else _col(df, "origin_epoch")
        if "mid" in df:
            out["mid"] = _col(df, "mid")
        else:
            out["mid"] = (_col(df, "best_bid") + _col(df, "best_ask")) / 2.0
        n1, n6 = _col(df, "flow_n_1h"), _col(df, "flow_n_6h")
        with np.errstate(divide="ignore", invalid="ignore"):
            burst = np.where(n6 > 0, n1 / (n6 / 6.0), np.nan)
        m = {
            "imb_s": _col(df, "flow_imb_1h"), "n_s": n1, "n_l": n6,
            "burst": pd.Series(burst, df.index),
            # live flow_max_trade_liq_1h divides by liquidity, not mean trade size: not comparable
            "large_trade_rel": pd.Series(np.nan, index=df.index),
            "top1_share_l": _col(df, "wlt_top1_share_6h"), "hhi_l": _col(df, "wlt_hhi_6h"),
            "n_wallets_s": _col(df, "wlt_n_buy_1h") + _col(df, "wlt_n_sell_1h"),
            "n_wallets_l": _col(df, "wlt_n_buy_6h") + _col(df, "wlt_n_sell_6h"),
            "new_wallet_share_l": _col(df, "wlt_new_share_6h"),
            "new_wallets_s": pd.Series(np.nan, index=df.index),
            "last_trade_age_h": _col(df, "time_since_last_trade_s") / 3600.0,
            "ltp_minus_mid": _col(df, "last_trade_price") - out["mid"],
            "mid_change_s": _col(df, "chg_1h"),  # Gamma 1h change: shorter than the 2h history lag
        }
        out["spread"] = (_col(df, "spread") if "spread" in df
                         else _col(df, "best_ask") - _col(df, "best_bid"))
    for k, v in m.items():
        out[k] = np.asarray(v, float)
    add_derived(out)
    out["liquidity"] = _col(df, "liquidity")
    out["traded_before_t"] = _col(df, "traded_before_t")
    for c in ("fee_category", "fee_schedule", "fees_enabled", "news_ts", "control_group"):
        if c in df:
            out[c] = df[c].to_numpy()
    for h in HORIZONS_H:
        out[f"fwd_move_{h}h"] = _col(df, f"fwd_move_{h}h")
    unmapped = [c for c in (*FLOW_FEATURES, *DERIVED_FEATURES, "spread", "liquidity",
                            "traded_before_t")
                if not np.isfinite(out[c].to_numpy(float)).any()]
    out.attrs.update({"panel_map": PANEL_MAP_VERSION, "panel_source": source,
                      "unmapped_all_nan": unmapped})
    return out


def add_derived(panel: pd.DataFrame) -> pd.DataFrame:
    """Add ``p_acq`` and ``resp_s`` in place from ``imb_s``, ``mid`` and ``mid_change_s``.

    ``p_acq``: mid of the outcome the short-window net flow acquires (``mid`` when ``imb_s > 0``,
    ``1 - mid`` when ``imb_s < 0``); NaN when the flow is balanced or unknown.
    ``resp_s``: ``sign(imb_s) * mid_change_s``, the short-window price change in the direction of
    the flow (small or negative = pressure without price response). Uses only values at ``t``.
    """
    imb = panel["imb_s"].to_numpy(float)
    mid = panel["mid"].to_numpy(float)
    sgn = np.where(np.isfinite(imb), np.sign(imb), 0.0)
    panel["p_acq"] = np.where(sgn > 0, mid, np.where(sgn < 0, 1.0 - mid, np.nan))
    chg = panel["mid_change_s"].to_numpy(float) if "mid_change_s" in panel else np.full(len(panel),
                                                                                       np.nan)
    panel["resp_s"] = np.where(sgn != 0, sgn * chg, np.nan)
    return panel


def check_panel(panel: pd.DataFrame) -> None:
    missing = [c for c in IDENTITY if c not in panel]
    if missing:
        raise PanelError(f"panel lacks canonical columns {missing}; use normalise_panel")
    if not panel["market_id"].map(lambda v: isinstance(v, str)).all():
        raise PanelError("market_id must be str")


# --- 4. evaluation engine ---------------------------------------------------------------------


@dataclass
class EvalConfig:
    budget: float = 0.01  # share of alertable rows that may be alerted
    horizon_h: int = 24
    delta: float = 0.10  # large move, probability units
    cooloff_s: float = DAY_S  # alert rows of one market closer than this form one episode
    k_controls: int = 5
    n_boot: int = 1000
    n_placebo: int = 200
    seed: int = 116
    case_mode: bool = False  # held-out cases: recall / lead time only, precision refused
    news_window_s: float = 72 * 3600.0
    lead_lookahead_s: float = 72 * 3600.0
    shares: float = 5.0  # Polymarket min order size default
    spread_default: float = 0.02  # used when the panel has no spread (counted)
    fee_policy: str = "max_if_unknown"

    def __post_init__(self) -> None:
        if not 0 < self.budget <= 1:
            raise ValueError("budget must be in (0, 1]")
        if self.horizon_h not in HORIZONS_H:
            raise ValueError(f"horizon_h must be one of {HORIZONS_H}")
        if self.delta <= 0 or self.k_controls < 1 or self.n_boot < 1:
            raise ValueError("delta > 0, k_controls >= 1, n_boot >= 1")


def _episodes(rows: pd.DataFrame, cooloff_s: float) -> pd.DataFrame:
    """Head rows of per-market episodes (rows sorted by market, t; new episode after a gap)."""
    if rows.empty:
        return rows
    r = rows.sort_values(["market_id", "t"], kind="stable")
    same = r["market_id"].to_numpy() == np.roll(r["market_id"].to_numpy(), 1)
    gap = r["t"].to_numpy(float) - np.roll(r["t"].to_numpy(float), 1)
    head = ~(same & (gap < cooloff_s))
    head[0] = True
    return r[head]


def _strata(panel: pd.DataFrame) -> pd.Series:
    day = np.floor(panel["t"].to_numpy(float) / DAY_S).astype(int)
    dist = np.abs(panel["mid"].to_numpy(float) - 0.5)
    pband = np.digitize(dist, PRICE_BANDS)
    liq = panel["liquidity"]
    if liq.notna().sum() >= 3 and liq.nunique() >= 3:
        lband = pd.qcut(liq.rank(method="first"), 3, labels=False).astype("Int64").astype(str)
    else:
        lband = pd.Series("na", index=panel.index)
    lband = lband.where(liq.notna(), "na")
    return pd.Series([f"{d}|{p}|{b}" for d, p, b in zip(day, pband, lband, strict=True)],
                     index=panel.index)


def _hit(fwd: np.ndarray, direction: np.ndarray, delta: float) -> np.ndarray:
    """Directional hit when direction != 0, else either direction."""
    return np.where(direction != 0, direction * fwd >= delta, np.abs(fwd) >= delta)


def alerts_needed(base_rate: float, delta: float, power: float = 0.8, alpha: float = 0.05) -> int:
    """Alert episodes needed to detect precision ``base_rate + delta`` against ``base_rate`` with
    the given one-sided power (normal approximation, two independent proportions, equal n)."""
    if not 0 < base_rate < 1 or delta <= 0 or base_rate + delta >= 1:
        raise ValueError("need 0 < base_rate < 1, delta > 0, base_rate + delta < 1")
    nd = NormalDist()
    za, zb = nd.inv_cdf(1 - alpha), nd.inv_cdf(power)
    p1, pbar = base_rate + delta, base_rate + delta / 2.0
    num = za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(
        base_rate * (1 - base_rate) + p1 * (1 - p1))
    return int(math.ceil((num / delta) ** 2))


def _paper_pnl(ep: pd.DataFrame, cfg: EvalConfig, fwd_col: str) -> dict:
    """Paper round trip per directional alert episode: enter at mid +/- spread/2, exit at the
    horizon mid less half a spread, taker fee both legs (``economics``). Optimistic, not
    tradable."""
    d = ep[ep["direction"] != 0]
    d = d[np.isfinite(d[fwd_col].to_numpy(float))]
    if d.empty:
        return {"n": 0, "testable": False, "note": "no directional alerts with an outcome"}
    spread = d["spread"].to_numpy(float) if "spread" in d else np.full(len(d), np.nan)
    assumed = ~np.isfinite(spread)
    spread = np.where(assumed, cfg.spread_default, spread)
    mid, fwd = d["mid"].to_numpy(float), d[fwd_col].to_numpy(float)
    sgn = d["direction"].to_numpy(int)
    tok_in = np.where(sgn > 0, mid, 1.0 - mid)
    tok_out = np.where(sgn > 0, mid + fwd, 1.0 - (mid + fwd))
    entry = np.clip(tok_in + spread / 2.0, 0.0, 1.0)
    exit_ = np.clip(tok_out - spread / 2.0, 0.0, 1.0)
    rates = np.array([economics.resolve_rate(economics.fee_spec(
        r.get("fee_schedule"), r.get("fees_enabled"), r.get("fee_category")), cfg.fee_policy)
        for r in d.to_dict("records")])
    fees = np.array([economics.taker_fee(cfg.shares, e, r) + economics.taker_fee(cfg.shares, x, r)
                     for e, x, r in zip(entry, exit_, rates, strict=True)])
    pnl = cfg.shares * (exit_ - entry) - fees
    cl = d["cluster"].to_numpy()
    br = economics.boot_ratio(cl, pnl, np.ones(len(pnl)), n_boot=cfg.n_boot, seed=cfg.seed)
    ncl = int(pd.Series(cl).nunique())
    return {"n": int(len(pnl)), "shares": cfg.shares, "mean_pnl_usdc": br["mean"],
            "lower_5pct": br["lower_5pct"], "ci95": br["ci95_two_sided"], "n_clusters": ncl,
            "testable": bool(len(pnl) >= MIN_EPISODES and ncl >= MIN_CLUSTERS),
            "spread_assumed_n": int(assumed.sum()), "fee_policy": cfg.fee_policy,
            "label": "optimistic, not tradable (no depth walk; paper only)"}


def _lead_time_cases(panel: pd.DataFrame, alert_rows: pd.DataFrame, cfg: EvalConfig) -> dict:
    news = panel.loc[np.isfinite(panel["news_ts"].to_numpy(float)), ["market_id", "news_ts"]]
    news = news.groupby("market_id")["news_ts"].min()
    leads, fired = [], []
    for m, nt in news.items():
        a = alert_rows[(alert_rows["market_id"] == m) & (alert_rows["t"] >= nt - cfg.news_window_s)
                       & (alert_rows["t"] < nt)]
        fired.append(not a.empty)
        if not a.empty:
            leads.append(float(nt - a["t"].min()) / 3600.0)
    out = {"n_cases": int(len(news)), "n_cases_alerted_before_news": int(sum(fired)),
           "share_alerted_before_news": float(np.mean(fired)) if fired else None,
           "lead_hours": _dist(leads), "window_h": cfg.news_window_s / 3600.0}
    if "control_group" in panel:
        grp = panel.groupby("control_group")["market_id"].nunique()
        groups = panel[["market_id", "control_group"]].drop_duplicates("market_id")
        alerted = (alert_rows[["market_id"]].merge(groups, on="market_id", how="left")
                   if not alert_rows.empty else None)
        rates = {}
        for g, n_m in grp.items():
            n_a = (int(alerted[alerted["control_group"] == g]["market_id"].nunique())
                   if alerted is not None else 0)
            rates[str(g)] = {"markets": int(n_m), "markets_alerted": n_a,
                             "rate": n_a / n_m if n_m else None}
        out["alert_rate_by_group"] = rates
    return out


def _dist(x: list[float]) -> dict:
    if not x:
        return {"n": 0}
    a = np.asarray(x, float)
    return {"n": int(len(a)), "min": float(a.min()), "q25": float(np.percentile(a, 25)),
            "median": float(np.median(a)), "q75": float(np.percentile(a, 75)),
            "max": float(a.max())}


def evaluate(spec: RuleSpec, panel: pd.DataFrame, cfg: EvalConfig | None = None) -> dict:
    """Run one rule on one canonical panel. Returns a JSON-serialisable dict. See module doc."""
    cfg = cfg or EvalConfig()
    check_panel(panel)
    fwd_col = f"fwd_move_{cfg.horizon_h}h"
    if fwd_col not in panel:
        raise PanelError(f"panel lacks {fwd_col}")
    res: dict = {"engine_version": ENGINE_VERSION, "rule_id": spec.rule_id,
                 "spec_sha256": spec.sha256(), "config": asdict(cfg), "n_rows": int(len(panel)),
                 "panel_source": panel.attrs.get("panel_source"),
                 "panel_map": panel.attrs.get("panel_map")}
    tb = panel["traded_before_t"].to_numpy(float)
    keep = tb == 1.0
    res["n_excluded_untraded"] = int((tb == 0.0).sum())
    res["n_excluded_untraded_unknown"] = int((~np.isfinite(tb)).sum())
    p = panel[keep].copy()
    sc = score_rule(spec, p)
    p[["score", "alertable", "direction"]] = sc[["score", "alertable", "direction"]]
    a = p[p["alertable"]].copy()
    res["n_alertable"] = int(len(a))
    if a.empty:
        res["status"] = "no_alertable_rows"
        return res
    k = max(1, int(math.floor(cfg.budget * len(a))))
    a = a.sort_values(["score", "market_id", "t"], ascending=[False, True, True], kind="stable")
    alerts = a.iloc[:k].copy()
    res["n_alert_rows"] = int(k)
    res["score_threshold"] = float(alerts["score"].min())
    ep = _episodes(alerts, cfg.cooloff_s)
    res["n_alert_episodes"] = int(len(ep))
    fwd_ep = ep[fwd_col].to_numpy(float)
    has = np.isfinite(fwd_ep)
    res["n_episodes_outcome_unavailable"] = int((~has).sum())
    ep_o = ep[has]
    rng = np.random.default_rng(cfg.seed)

    if cfg.case_mode:
        res["precision"] = {"refused": "case mode: reporting-conditioned sample, no precision or "
                                       "base rate is computed (programme doc section 6)"}
        res["lead_time_cases"] = _lead_time_cases(p, alerts, cfg) if "news_ts" in p else {
            "error": "case_mode needs a news_ts column"}
        res["status"] = "ok"
        return res

    # --- matched controls and excess precision (primary) ---
    strata = _strata(a)
    a["stratum"] = strata
    alerted_idx = set(alerts.index)
    pool = a[~a.index.isin(alerted_idx) & np.isfinite(a[fwd_col].to_numpy(float))]
    by_stratum = {s: g for s, g in pool.groupby("stratum")}
    hits, d_i, ctrl_rates, n_ctrl = [], [], [], []
    for idx, row in ep_o.iterrows():
        h = bool(_hit(np.array([row[fwd_col]]), np.array([row["direction"]]), cfg.delta)[0])
        hits.append(h)
        cand = by_stratum.get(a.at[idx, "stratum"])
        if cand is not None:
            cand = cand[cand["market_id"] != row["market_id"]]
        if cand is None or cand.empty:
            d_i.append(np.nan)
            ctrl_rates.append(np.nan)
            n_ctrl.append(0)
            continue
        pick = cand.iloc[np.sort(rng.choice(len(cand), size=min(cfg.k_controls, len(cand)),
                                            replace=False))]
        ch = _hit(pick[fwd_col].to_numpy(float), np.full(len(pick), int(row["direction"])),
                  cfg.delta)
        ctrl_rates.append(float(ch.mean()))
        d_i.append(float(h) - float(ch.mean()))
        n_ctrl.append(int(len(pick)))
    hits_a = np.asarray(hits, float)
    d_arr = np.asarray(d_i, float)
    cl = ep_o["cluster"].to_numpy()
    boot = cluster_boot(d_arr, cl, n_boot=cfg.n_boot, seed=cfg.seed)
    n_cl = int(pd.Series(cl[np.isfinite(d_arr)]).nunique()) if len(cl) else 0
    base = float(np.nanmean(ctrl_rates)) if np.isfinite(ctrl_rates).any() else None
    prec = float(hits_a.mean()) if len(hits_a) else None
    res["precision"] = {
        "n_episodes": int(len(ep_o)), "n_hits": int(hits_a.sum()), "precision": prec,
        "control_base_rate": base, "lift": (prec / base) if prec is not None and base else None,
        "excess_mean": boot["mean"], "excess_ci95": boot["ci"], "p_one_sided": boot["p_pos"],
        "n_clusters": n_cl, "n_episodes_without_controls": int(np.sum(np.asarray(n_ctrl) == 0)),
        "controls_per_alert_mean": float(np.mean(n_ctrl)) if n_ctrl else 0.0,
        "testable": bool(len(ep_o) >= MIN_EPISODES and n_cl >= MIN_CLUSTERS),
        "directional": spec.direction_feature is not None,
    }
    # --- random-budget placebo (row level, same strata) ---
    a_o = a[np.isfinite(a[fwd_col].to_numpy(float))]
    obs_rows = alerts[np.isfinite(alerts[fwd_col].to_numpy(float))]
    obs_prec = float(_hit(obs_rows[fwd_col].to_numpy(float), obs_rows["direction"].to_numpy(int),
                          cfg.delta).mean()) if len(obs_rows) else None
    counts = a.loc[alerts.index, "stratum"].value_counts()
    groups = {s: g for s, g in a_o.groupby("stratum")}
    plc = []
    for _ in range(cfg.n_placebo):
        picked_hits = []
        for s, c in counts.items():
            g = groups.get(s)
            if g is None or g.empty:
                continue
            sel = g.iloc[rng.choice(len(g), size=min(int(c), len(g)), replace=False)]
            picked_hits.append(_hit(sel[fwd_col].to_numpy(float), sel["direction"].to_numpy(int),
                                    cfg.delta))
        if picked_hits:
            plc.append(float(np.concatenate(picked_hits).mean()))
    plc_a = np.asarray(plc, float)
    res["placebo_random_budget"] = {
        "n_draws": int(len(plc_a)), "observed_row_precision": obs_prec,
        "placebo_mean": float(plc_a.mean()) if len(plc_a) else None,
        "p_rank": (float((1 + (plc_a >= obs_prec).sum()) / (len(plc_a) + 1))
                   if len(plc_a) and obs_prec is not None else None),
    }
    # --- recall on large moves ---
    big = a_o[np.abs(a_o[fwd_col].to_numpy(float)) >= cfg.delta]
    big_ep = _episodes(big, cfg.cooloff_s)
    lookback = cfg.horizon_h * 3600.0
    al_by_m = {m: g["t"].to_numpy(float) for m, g in alerts.groupby("market_id")}
    caught = np.array([bool(((ts := al_by_m.get(m)) is not None) and
                            np.any((ts <= t) & (ts >= t - lookback)))
                       for m, t in zip(big_ep["market_id"], big_ep["t"].to_numpy(float),
                                       strict=True)], float)
    rb = (cluster_boot(caught, big_ep["cluster"].to_numpy(), n_boot=cfg.n_boot, seed=cfg.seed)
          if len(caught) else {"mean": None, "ci": [None, None]})
    res["recall_large_moves"] = {"n_large_move_episodes": int(len(big_ep)),
                                 "n_caught": int(caught.sum()) if len(caught) else 0,
                                 "recall": rb["mean"], "ci95": rb["ci"],
                                 "lookback_h": cfg.horizon_h}
    # --- lead time (broad): alert -> first large-move row of the same market ---
    big_by_m = {m: g["t"].to_numpy(float) for m, g in big.groupby("market_id")}
    leads = []
    for m, t in zip(ep["market_id"], ep["t"].to_numpy(float), strict=True):
        bt = big_by_m.get(m)
        if bt is None:
            continue
        later = bt[(bt >= t) & (bt <= t + cfg.lead_lookahead_s)]
        if len(later):
            leads.append(float(later.min() - t) / 3600.0)
    res["lead_time_broad_h"] = {**_dist(leads), "lookahead_h": cfg.lead_lookahead_s / 3600.0}
    if "news_ts" in p and np.isfinite(p["news_ts"].to_numpy(float)).any():
        res["lead_time_cases"] = _lead_time_cases(p, alerts, cfg)
    # --- cost-aware value ---
    res["paper_pnl"] = _paper_pnl(ep_o, cfg, fwd_col)
    res["status"] = "ok"
    return res


def holm_across_rules(results: dict[str, dict]) -> dict[str, dict]:
    """Holm over the primary one-sided p (excess precision > 0) of each evaluated rule."""
    pv = {rid: r["precision"]["p_one_sided"] for rid, r in results.items()
          if isinstance(r.get("precision"), dict) and r["precision"].get("p_one_sided") is not None}
    return holm(pv) if pv else {}


# --- 5. held-out harness and trial log --------------------------------------------------------


def prior_detector_trials(path: Path = provenance.TRIALS_PATH) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    n = 0
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            try:
                if json.loads(line).get("kind") == TRIAL_KIND:
                    n += 1
            except ValueError:
                continue
    return n


def _summary(res: dict) -> dict:
    keys = ("status", "n_rows", "n_excluded_untraded", "n_alertable", "n_alert_rows",
            "n_alert_episodes", "precision", "placebo_random_budget", "recall_large_moves",
            "lead_time_cases", "paper_pnl")
    return {k: res[k] for k in keys if k in res}


@dataclass
class HeldOutHarness:
    """Evaluates only frozen, unmodified rules and logs every run."""

    registry: RuleRegistry = field(default_factory=RuleRegistry)
    trials_path: Path = provenance.TRIALS_PATH

    def evaluate(self, rule_id: str, panel: pd.DataFrame, *, evidence_role: str, dataset: str,
                 cfg: EvalConfig | None = None, spec: RuleSpec | None = None, log: bool = True,
                 extra: dict | None = None) -> dict:
        if evidence_role not in provenance.EVIDENCE_ROLES:
            raise provenance.EvidenceRoleError(
                f"evidence_role {evidence_role!r} invalid; allowed {provenance.EVIDENCE_ROLES}")
        if evidence_role == provenance.CONFIRMATION_ROLE:
            provenance.require_confirmation_role(panel.attrs)
        frozen = self.registry.load(rule_id)
        if spec is not None:
            if spec.rule_id != rule_id:
                raise DetectorError("spec.rule_id does not match rule_id")
            self.registry.verify(spec)  # an in-memory modification is refused
        spec = frozen
        rec = {"kind": TRIAL_KIND, "label": "EXPLORATORY detector evaluation",
               "evidence_role": evidence_role, "dataset": dataset, "rule_id": rule_id,
               "spec_sha256": spec.sha256(), "engine_version": ENGINE_VERSION,
               "prior_detector_trials": prior_detector_trials(self.trials_path),
               "provenance": provenance.run_provenance([Path(__file__)]), **(extra or {})}
        try:
            res = evaluate(spec, panel, cfg)
        except Exception as e:  # the attempt is logged whatever happens, then re-raised
            if log:
                provenance.append_trial({**rec, "status": "failed", "error_type": type(e).__name__,
                                         "error": str(e)[:300]}, self.trials_path)
            raise
        res["evidence_role"] = evidence_role
        if log:
            rec["trial"] = provenance.append_trial({**rec, **_summary(res)}, self.trials_path)
        res["trial_record"] = rec.get("trial")
        return res


__all__ = [
    "ENGINE_VERSION", "DetectorError", "EngineVersionError", "EvalConfig", "HeldOutHarness",
    "NotFrozenError", "PanelError", "RuleRegistry", "RuleSpec", "SpecTamperedError",
    "add_derived", "alerts_needed", "check_panel", "evaluate", "freeze_rules", "holm_across_rules",
    "normalise_panel", "prior_detector_trials", "read_index", "score_rule",
]
