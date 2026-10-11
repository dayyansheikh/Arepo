"""Dependence-clustering diagnostic for the ML co-primary clusters and D120 group-disjointness.

Design-time analysis on current data only. It never fits, scores or reads a model; the only
outcome quantities are 2h Gamma mid changes (``panel.build_pair``) used as dependence proxies.
Numbers are reported in ``docs/research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md``.

Inputs, read one at a time and only the needed columns (peak RSS about 0.6 GB):

* the facts snapshot (``rows.csv.gz`` + the ``rows_ext.csv.gz`` sidecar): event ids, series
  slugs, ``neg_risk_market_id``, fee category, end date;
* optionally one fs2 frame, streamed page by page, for ``events[].parentEventId`` and event slugs,
  which the sidecar lacks (the D118 frame; it predates the facts snapshot by about 2h, so events
  created in between have no parent information and are counted);
* three consecutive complete snapshots, i.e. two 2h periods (gap 1.5-3h, as ``ml_panel``).

Non-sports links (section 8 of the doc): a deterministic dictionary/regex entity extractor on event
titles (economy/central bank, crypto and finance assets, AI/media organisations, named people,
geopolitical theatres, weather city, US elections), resolution-source domain and end timestamp,
tested within fee category over ``fixture_day`` clusters. Gamma tags are absent from the snapshot
rows, the sidecar and the ``/markets/keyset`` payload (counted, not assumed).

Group definitions are built with ``pairing.dependence_groups`` (imported, never reimplemented);
the ``season_series`` definition is asserted equal to ``ml_panel.dependence_group_ids``.

    cd backend && python scripts/dependence_clustering_analysis.py [--out report.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import ml_panel, panel
from astrolabe.research_panel import pairing

REPO = Path(__file__).resolve().parents[2]
SNAPS = REPO / "data-dumps" / "research_lab" / "snapshots"
FACTS = "20261011T123356Z_9cd3cdb9"
PERIODS = ("20261011T081844Z_24399984", "20261011T103157Z_4e5e3b7f", FACTS)
FRAME = REPO / "data-dumps" / "fs2_capture_52eead5d6a984264a9eb0828502fb697"
ROW_COLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid",
            "best_ask", "spread", "end_date", "chg_1h", "chg_1d", "chg_1w", "liquidity",
            "volume24hr", "last_trade_price", "neg_risk_market_id"]
EXT_COLS = ["market_id", "received_utc", "fee_category", "event_ids", "series_slugs"]
IDS = {"market_id": str, "event_id": str, "neg_risk_market_id": str}
D120_LIQUIDITY = 1000.0
SEED, N_PERM = 116, 300
PROXIES = ("dmid", "absd", "moved")
# name: (parent, underlying rule, series rule). underlying: 'ud' = token x UTC end date (ML),
# 'u' = token, all dates (D120). series: None, 'season' (slug), 'day' (slug x UTC end date),
# 'crypto' (slug, crypto fee category only).
DEFS = {
    "event": (False, None, None),
    "event_parent": (True, None, None),
    "outcome_ud": (True, "ud", None),
    "outcome": (True, "u", None),
    "outcome_cryptoseries": (True, "u", "crypto"),
    "fixture_day": (True, "u", "day"),
    "fixture_day_sidecar": (False, "ud", "day"),  # computable from the current sidecar
    "season_series": (False, "ud", "season"),  # = ml_panel dep_group (commit 6c5a074)
    "d120_v2": (True, "u", "season"),  # D120 fs2-dependence-groups-v2 (+ event-slug tokens)
}


NON_SPORTS = ["politics", "economics", "finance", "crypto", "weather", "tech", "culture", "unknown"]
D120_ECON_PAIR = ("999108", "1124260")  # D120 economics trigger/control (ECB cut / EZ inflation)
# Deterministic entity table on lower-cased event titles: first match wins (most specific first).
_ECON = [
    ("econ:EA", r"\b(ecb|european central bank|eurozone|euro area|euro zone|eurostat|lagarde)\b"),
    ("econ:US", r"\b(fed|fomc|federal reserve|powell|us cpi|us inflation|us gdp|us unemployment|"
                r"nonfarm|payrolls|treasury|us recession|us trade deficit|us dollar index|dxy)\b"),
    ("econ:UK", r"\b(boe|bank of england|uk inflation|inflation uk|uk gdp|uk cpi)\b"),
    ("econ:JP", r"\b(boj|bank of japan|japan|japanese|nikkei)\b"),
    ("econ:CN", r"\b(pboc|people's bank of china|china annual inflation|china gdp|yuan)\b"),
    ("econ:CA", r"\b(bank of canada|canada annual inflation|canada inflation|canada gdp)\b"),
    ("econ:AU", r"\b(rba|reserve bank of australia|australia inflation)\b"),
    ("econ:IN", r"\b(rbi|reserve bank of india|india inflation)\b"),
    ("econ:CO", r"\b(central bank of colombia|colombia)\b"),
    ("econ:BR", r"\b(central bank of brazil|selic|brazil inflation)\b"),
    ("econ:MX", r"\b(banxico|bank of mexico)\b"),
    ("econ:TR", r"\b(central bank of turkey|turkey inflation|turkish lira)\b"),
    ("econ:CH", r"\b(snb|swiss national bank)\b"),
]
_ENTITIES = [
    ("person:trump", r"\btrump\b"), ("person:musk", r"\b(elon musk|musk)\b"),
    ("person:putin", r"\bputin\b"), ("person:zelensky", r"\bzelensky[iy]?\b"),
    ("person:netanyahu", r"\bnetanyahu\b"), ("person:vance", r"\bvance\b"),
    ("person:newsom", r"\bnewsom\b"), ("person:mamdani", r"\bmamdani\b"),
    ("person:xi", r"\bxi jinping\b"), ("person:maduro", r"\bmaduro\b"),
    ("person:starmer", r"\bstarmer\b"), ("person:macron", r"\bmacron\b"),
    ("person:swift", r"\btaylor swift\b"), ("person:mrbeast", r"\bmrbeast\b"),
    ("asset:btc", r"\b(bitcoin|btc|microstrategy|mstr)\b"), ("asset:eth", r"\b(ethereum|eth)\b"),
    ("asset:sol", r"\b(solana|sol)\b"), ("asset:xrp", r"\b(xrp|ripple)\b"),
    ("asset:doge", r"\b(dogecoin|doge)\b"), ("asset:bnb", r"\bbnb\b"),
    ("asset:hype", r"\b(hyperliquid|hype)\b"), ("asset:zec", r"\b(zcash|zec)\b"),
    ("asset:ada", r"\b(cardano|ada)\b"), ("asset:pepe", r"\bpepe\b"), ("asset:sui", r"\bsui\b"),
    ("asset:spx", r"\b(s&p 500|s&p500|spx|spy)\b"), ("asset:ndx", r"\b(nasdaq|ndx|qqq)\b"),
    ("asset:oil", r"\b(wti|crude oil|brent|oil price)\b"), ("asset:gold", r"\b(gold|xau)\b"),
    ("asset:silver", r"\b(silver|xag)\b"),
    ("org:openai", r"\b(openai|chatgpt|gpt)\b"), ("org:anthropic", r"\b(anthropic|claude)\b"),
    ("org:google", r"\b(google|gemini|deepmind)\b"), ("org:xai", r"\b(xai|grok)\b"),
    ("org:deepseek", r"\bdeepseek\b"), ("org:meta", r"\b(meta|llama)\b"),
    ("org:alibaba", r"\b(alibaba|qwen)\b"), ("org:netflix", r"\bnetflix\b"),
    ("org:apple", r"\bapple\b"), ("org:tesla", r"\b(tesla|tsla)\b"),
    ("org:nvidia", r"\b(nvidia|nvda)\b"),
    *_ECON,
    ("geo:russia-ukraine", r"\b(russia|russian|ukraine|ukrainian|kyiv|donbas|crimea|pokrovsk|"
                           r"kupiansk|lyman|sloviansk|kramatorsk|zaporizhzhia|kherson)\b"),
    ("geo:israel-iran", r"\b(israel|israeli|iran|iranian|gaza|hamas|hezbollah|lebanon|houthi|"
                        r"yemen)\b"),
    ("geo:china-taiwan", r"\b(taiwan|china|chinese)\b"), ("geo:venezuela", r"\bvenezuela\b"),
    ("geo:korea", r"\b(north korea|south korea|korea)\b"),
    ("geo:india-pakistan", r"\b(india|pakistan|kashmir)\b"), ("geo:syria", r"\bsyria\b"),
]
_ENT_RE = [(lab, re.compile(pat)) for lab, pat in _ENTITIES]
_ECON_RE = [(lab, re.compile(pat)) for lab, pat in _ECON]
_CITY = re.compile(r"(?:temperature|precipitation|rain(?:fall)?|snow(?:fall)?|weather) in "
                   r"([a-z .'-]+?)(?: on | in | this | by |\?|$)")
_TICKER = re.compile(r"\(([A-Z]{1,5})\)")
_US_ELECTION = re.compile(r"\b([a-z]{2}-\d{2}|house|senate|governor|gubernatorial|"
                          r"congress(ional)?)\b.*\b(election|winner|margin|seats?|primary)\b|"
                          r"\bmidterms?\b")
# Category-aware groupings: fixture_day plus extra link nodes for the named fee categories.
CAT_RULES = {
    "category_aware": {"weather_city_day", "culture_source"},
    "category_aware+econ_driver": {"weather_city_day", "culture_source", "econ_driver"},
    "category_driver": {"weather_city_day", "culture_source", "crypto_window", "politics_end",
                        "finance_end"},
    "entity_all": {"entity"},
}


def entity(title) -> str | None:
    """Primary entity of an event title (one label per event, so events never chain)."""
    if not isinstance(title, str) or not title:
        return None
    low = title.lower()
    city = _CITY.search(low)
    if city:
        return "city:" + city.group(1).strip()
    for lab, pat in _ENT_RE:
        if pat.search(low):
            return lab
    tick = _TICKER.search(title)
    if tick:
        return "ticker:" + tick.group(1)
    return "us-elections" if _US_ELECTION.search(low) else None


def economy(title) -> str | None:
    """Economic-driver label: the economy or central bank named by an event title."""
    if not isinstance(title, str) or not title:
        return None
    low = title.lower()
    return next((lab for lab, pat in _ECON_RE if pat.search(low)), None)


def collectors_running() -> list[str]:
    try:
        out = subprocess.run(["pgrep", "-fl", "collect"], capture_output=True, text=True).stdout
    except OSError:
        return []
    return [ln for ln in out.splitlines() if ln and str(os.getpid()) not in ln.split()[:1]]


def manifest(snap: str) -> dict:
    m = json.loads((SNAPS / snap / "manifest.json").read_text())
    if m.get("state") != "complete":
        raise SystemExit(f"{snap} is not a complete snapshot: {m.get('state')}")
    return m


def load_rows(snap: str) -> pd.DataFrame:
    return pd.read_csv(SNAPS / snap / "rows.csv.gz", usecols=ROW_COLS, dtype=IDS)


def load_facts(snap: str) -> pd.DataFrame:
    """Facts snapshot rows with the sidecar merged as ``ml_panel.load_snapshot_rows`` does."""
    if json.loads((SNAPS / snap / "ext_manifest.json").read_text()).get(
            "sidecar_status") != "complete":
        raise SystemExit("facts snapshot needs a complete sidecar")
    rows = load_rows(snap)
    ext = pd.read_csv(SNAPS / snap / "rows_ext.csv.gz", usecols=EXT_COLS, dtype=str)
    ext = ext.drop_duplicates(["market_id", "received_utc"])
    rows = rows.merge(ext, on=["market_id", "received_utc"], how="left")
    rows["ext_present"] = 1.0
    return rows.drop_duplicates("market_id").reset_index(drop=True)


def stream_frame(frame: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """One frame page at a time: event id -> (parentEventId, slug, title); market id ->
    resolution-source domain; and counts of ``tags`` keys on market and event objects."""
    events: dict[str, tuple] = {}
    src: dict[str, str] = {}
    tags = {"market_objects": 0, "market_objects_with_tags": 0, "event_objects_with_tags": 0}
    for d in sorted(p for p in frame.iterdir() if (p / "parsed.json").is_file()):
        value = json.loads((d / "parsed.json").read_text()).get("value") or {}
        for m in value.get("markets") or []:
            tags["market_objects"] += 1
            tags["market_objects_with_tags"] += int("tags" in m)
            evs = [e for e in m.get("events") or [] if isinstance(e, dict)]
            for e in evs:
                tags["event_objects_with_tags"] += int("tags" in e)
                if e.get("id") is not None:
                    par = e.get("parentEventId")
                    events.setdefault(str(e["id"]), (None if par is None else str(par),
                                                     e.get("slug"), e.get("title")))
            rs = m.get("resolutionSource") or (evs[0].get("resolutionSource") if evs else None)
            hit = re.match(r"https?://(?:www\.)?([^/?#]+)", rs or "")
            if m.get("id") is not None and hit:
                src[str(m["id"])] = hit.group(1).lower()
    ev = pd.DataFrame([(k, *v) for k, v in events.items()],
                      columns=["event_id", "parent_event_id", "event_slug", "event_title"])
    return ev, pd.DataFrame(list(src.items()), columns=["market_id", "source"]), tags


def utc_day(epoch: np.ndarray) -> list:
    return [None if np.isnan(x) else pd.Timestamp(x, unit="s", tz="UTC").strftime("%Y-%m-%d")
            for x in epoch]


def prepare(f: pd.DataFrame, parents: pd.DataFrame | None,
            sources: pd.DataFrame | None = None) -> pd.DataFrame:
    f = f.copy()
    f["evs"] = f["event_ids"].map(ml_panel._json_list)
    f["sers"] = f["series_slugs"].map(ml_panel._json_list)
    f["ser"] = f["sers"].map(lambda s: s[0] if s else None)
    f["day"] = utc_day(panel._epoch(f["end_date"]))
    f["neg"] = [None if pd.isna(x) or not str(x).strip() else str(x)
                for x in f["neg_risk_market_id"]]
    pmap, smap, tmap = {}, {}, {}
    if parents is not None:
        p = parents.set_index("event_id")
        pmap = p["parent_event_id"].dropna().to_dict()
        smap = p["event_slug"].dropna().to_dict()
        tmap = p["event_title"].dropna().to_dict() if "event_title" in p else {}
        f["parent_info"] = [bool(e) and all(x in p.index for x in e) for e in f["evs"]]
    else:
        f["parent_info"] = False
    f["parents"] = [sorted({pmap[x] for x in e if x in pmap}) for e in f["evs"]]
    f["eslugs"] = [sorted({smap[x] for x in e if x in smap}) for e in f["evs"]]
    f["tok_ud"] = [pairing.underlyings({"series_slugs": s, "event_slugs": []}) for s in f["sers"]]
    f["tok_u"] = [pairing.underlyings({"series_slugs": s, "event_slugs": es})
                  for s, es in zip(f["sers"], f["eslugs"], strict=True)]
    titles = [next((tmap[x] for x in e if x in tmap), None) for e in f["evs"]]
    f["ent"] = [entity(t) for t in titles]
    f["econ"] = [economy(t) for t in titles]
    smk = {} if sources is None else dict(zip(sources["market_id"], sources["source"],
                                              strict=True))
    f["src"] = [smk.get(m) for m in f["market_id"]]
    f["endts"] = [None if pd.isna(x) else str(x) for x in f["end_date"]]
    return f


def build_groups(f: pd.DataFrame, parent: bool, und: str | None, series: str | None) -> np.ndarray:
    facts = {}
    for m, evs, sers, neg, day, tud, tu, pa, fee in zip(
            f["market_id"], f["evs"], f["sers"], f["neg"], f["day"], f["tok_ud"], f["tok_u"],
            f["parents"], f["fee_category"], strict=True):
        e = set(evs) | (set(pa) if parent else set())
        if und == "ud" and day:
            e |= {f"{ml_panel.UNDERLYING_DATE_PREFIX}{t}|{day}" for t in tud}
        if und == "u":
            e |= {f"u:{t}" for t in tu}
        s = []
        if series == "season" or (series == "crypto" and fee == "crypto"):
            s = list(sers)
        elif series == "day":
            e |= {f"sd:{x}|{day}" for x in sers}
        facts[m] = {"event_ids": sorted(e), "series_slugs": s, "event_slugs": [],
                    "neg_risk_market_id": neg}
    g = pairing.dependence_groups(facts, underlying=False)
    return np.array([g[m] for m in f["market_id"]], dtype=object)


def size_metrics(labels) -> dict:
    vc = pd.Series(labels).value_counts()
    n = vc.to_numpy(float)
    return {"n": int(n.sum()), "K": int(len(n)), "largest": int(n[0]),
            "largest_share": round(n[0] / n.sum(), 4),
            "G_eff_size": round(float(n.sum() ** 2 / (n ** 2).sum()), 1)}


def largest_cluster(f: pd.DataFrame, g: np.ndarray, mask: np.ndarray) -> dict:
    x = f[mask].assign(g=g[mask])
    top = x[x["g"] == x["g"].value_counts().index[0]]
    return {"markets": len(top), "events": int(top["event_id"].nunique()),
            "series": top["ser"].value_counts().head(3).to_dict(),
            "end_days": int(top["day"].nunique()), "fee": top["fee_category"].mode().iat[0]}


def chaining(f: pd.DataFrame, g: np.ndarray) -> dict:
    x = f.assign(g=g)
    nr = x.dropna(subset=["neg"]).groupby("neg")["event_id"].nunique()
    giant = x[x["g"] == pd.Series(g).value_counts().index[0]]
    per_group = x.groupby("g")["ser"].nunique()
    tops = x.dropna(subset=["ser"]).groupby("ser").agg(markets=("market_id", "size"),
                                                       events=("event_id", "nunique"))
    return {
        "markets_by_series_count": x["sers"].map(len).value_counts().sort_index().to_dict(),
        "markets_by_event_count": x["evs"].map(len).value_counts().sort_index().to_dict(),
        "negrisk_ids_spanning_events": int((nr > 1).sum()),
        "events_spanning_series": int((x.groupby("event_id")["ser"].nunique() > 1).sum()),
        "groups_with_2plus_series": int((per_group >= 2).sum()),
        "groups_by_series_count": per_group.clip(upper=2).value_counts().sort_index().to_dict(),
        "giant": {"markets": len(giant), "events": int(giant["event_id"].nunique()),
                  "series": sorted(giant["ser"].dropna().unique().tolist())[:5],
                  "events_with_parent": int(giant.drop_duplicates("event_id")["parents"]
                                            .map(len).gt(0).sum())},
        "top_series": tops.sort_values("markets", ascending=False).head(8).to_dict("index"),
        "parent_info_share": round(float(x["parent_info"].mean()), 4),
        "markets_with_parent": round(float(x["parents"].map(len).gt(0).mean()), 4),
        "events_with_parent": int(x.drop_duplicates("event_id")["parents"].map(len).gt(0).sum()),
        "events": int(x["event_id"].nunique()),
    }


def period_rows(snaps: tuple, facts: pd.DataFrame) -> pd.DataFrame:
    out = []
    for k in range(len(snaps) - 1):
        mi, mj = manifest(snaps[k]), manifest(snaps[k + 1])
        ti, tj = (ml_panel._start_epoch(m) for m in (mi, mj))
        if not ml_panel.GAP_MIN_H <= (tj - ti) / 3600 <= ml_panel.GAP_MAX_H:
            raise SystemExit(f"period {k}: gap outside the ml_panel rule")
        si = load_rows(snaps[k])
        sj = load_rows(snaps[k + 1])[["market_id", "received_utc", "best_bid", "best_ask",
                                      "closed"]]
        pr, _ = panel.build_pair(si, sj, tj, k)
        o = si.drop_duplicates("market_id").set_index("market_id").reindex(pr["market_id"])
        pr["tte_h"] = (panel._epoch(o["end_date"]) - ti) / 3600
        pr["liq"] = pd.to_numeric(o["liquidity"], errors="coerce").to_numpy(float)
        out.append(pr[pr["dmid"].notna()][["market_id", "period", "dmid", "mid", "spread",
                                           "tte_h", "liq"]])
        del si, sj
    d = pd.concat(out, ignore_index=True)
    d["market_id"] = d["market_id"].astype(str)
    d["in_facts"] = d["market_id"].isin(facts["market_id"])
    return d


def strata(d: pd.DataFrame) -> pd.Series:
    """Residual-proxy cells: fee x time-to-end x spread x liquidity x mid band (origin only)."""
    t = d["tte_h"].to_numpy(float)
    tb = np.select([np.isnan(t), t < 2, t < 6, t < 24, t < 168], list("uabcd"), "e")
    sb = np.select([d["spread"] <= 0.011, d["spread"] <= 0.03], ["1", "2"], "3")
    lb = np.select([d["liq"] < 1e3, d["liq"] < 1e4, d["liq"] < 1e5], ["1", "2", "3"], "4")
    mb = np.select([d["mid"] < 0.1, d["mid"] < 0.3, d["mid"] < 0.7, d["mid"] < 0.9],
                   list("1234"), "5")
    return d["fee"].astype(str) + "|" + tb + sb + lb + mb


def centred(d: pd.DataFrame, proxy: str, how: str) -> np.ndarray:
    key = ["period", "fee"] if how == "period_fee" else ["period", "cell"]
    return (d[proxy] - d.groupby(key)[proxy].transform("mean")).to_numpy()


def V(e: np.ndarray, labels) -> tuple[float, float]:
    """CR0 variance of the total, and the variance-estimator d.f. 3 (sum S^2)^2 / sum S^4."""
    s = pd.Series(e).groupby(np.asarray(labels)).sum().to_numpy()
    s2 = s ** 2
    return float(s2.sum()), float(3 * s2.sum() ** 2 / (s2 ** 2).sum())


def _merged_ratio(S, has, labels, own, vb) -> float:
    key = np.where(has, labels, own)
    return float((pd.Series(S).groupby(key).sum() ** 2).sum()) / vb


def perm_link(d: pd.DataFrame, e: np.ndarray, base: str, label: str, cats: list,
              rng) -> dict:
    """Variance ratio of (base merged by ``label``) over base, against a null that permutes the
    label across base clusters of the same fee category (cluster counts per label preserved)."""
    out = {}
    for cat in cats:
        if cat == "all":
            m = np.ones(len(d), bool)
        elif cat == "other":
            m = ~d["fee"].isin(["sports", "crypto"]).to_numpy()
        else:
            m = (d["fee"] == cat).to_numpy()
        sub = pd.DataFrame({"e": e[m], "b": d.loc[m, base].to_numpy(),
                            "lab": d.loc[m, label].to_numpy(), "fee": d.loc[m, "fee"].to_numpy()})
        bs = sub.groupby("b").agg(S=("e", "sum"), lab=("lab", "first"), fee=("fee", "first"))
        S, labs, fees = bs["S"].to_numpy(), bs["lab"].to_numpy(), bs["fee"].to_numpy()
        has = pd.notna(labs)
        vb = float((S ** 2).sum())

        own = bs.index.to_numpy()
        obs = _merged_ratio(S, has, labs, own, vb)
        null = []
        for _ in range(N_PERM):
            p = labs.copy()
            for fv in np.unique(fees[has]):
                idx = np.where(has & (fees == fv))[0]
                p[idx] = labs[rng.permutation(idx)]
            null.append(_merged_ratio(S, has, p, own, vb))
        null = np.asarray(null)
        out[cat] = {"ratio": round(obs, 3), "null_mean": round(float(null.mean()), 3),
                    "null_q95": round(float(np.quantile(null, 0.95)), 3),
                    "p": round(float(((null >= obs).sum() + 1) / (N_PERM + 1)), 4),
                    "base_clusters_with_label": int(has.sum())}
    return out


def series_icc(d: pd.DataFrame, e: np.ndarray, base: str, top: int = 6) -> list:
    """Per series: mean correlation of base-cluster sums, (S^2 - sum S_b^2) / ((m-1) sum S_b^2)."""
    b = pd.DataFrame({"e": e, "b": d[base].to_numpy(), "ser": d["ser"].to_numpy()})
    bs = b.groupby("b").agg(S=("e", "sum"), ser=("ser", "first")).dropna()
    g = bs.groupby("ser")["S"].agg(S="sum", SS=lambda x: float((x ** 2).sum()), m="size")
    g = g[g["m"] >= 3]
    g["excess"] = g["S"] ** 2 - g["SS"]
    g["rho"] = g["excess"] / ((g["m"] - 1) * g["SS"])
    g["excess_share"] = g["excess"] / g["excess"].clip(lower=0).sum()
    g = g.sort_values("excess", ascending=False).head(top)
    return [{"series": s, "clusters": int(r.m), "rho": round(float(r.rho), 3),
             "excess_share": round(float(r.excess_share), 3)} for s, r in g.iterrows()]


def category_period(d: pd.DataFrame, proxy: str, min_rows: int = 300) -> dict:
    out = {}
    for cat, g in d.groupby("fee"):
        dev, se = [], []
        for p in (0, 1):
            x = g[g["period"] == p]
            if len(x) < min_rows:
                break
            e = x[proxy] - x[proxy].mean()
            S = e.groupby(x["fixture_day"]).sum().to_numpy()
            dev.append(float(x[proxy].mean() - d.loc[d["period"] == p, proxy].mean()))
            se.append(float(np.sqrt((S ** 2).sum()) / len(x)))
        if len(dev) == 2:
            out[cat] = {"dev_p0": round(dev[0], 5), "dev_p1": round(dev[1], 5),
                        "z_p0": round(dev[0] / se[0], 1), "z_p1": round(dev[1] / se[1], 1),
                        "z_change": round((dev[1] - dev[0]) / float(np.hypot(*se)), 1)}
    return out


def build_category_groups(f: pd.DataFrame, base: np.ndarray, rule: set) -> np.ndarray:
    """``base`` (fixture_day) plus category-specific link nodes, by union-find."""
    facts = {}
    for m, b, fe, en, ec, src, ets, day in zip(
            f["market_id"], base, f["fee_category"], f["ent"], f["econ"], f["src"], f["endts"],
            f["day"], strict=True):
        n = [b]
        if "weather_city_day" in rule and fe == "weather" and en and en.startswith("city:"):
            n.append(f"wc:{en}|{day}")
        if "culture_source" in rule and fe == "culture" and src:
            n.append(f"cs:{src}")
        if "crypto_window" in rule and fe == "crypto" and ets:
            n.append(f"cw:{ets}")
        if "politics_end" in rule and fe == "politics" and ets:
            n.append(f"pe:{ets}")
        if "finance_end" in rule and fe == "finance" and ets:
            n.append(f"fe:{ets}")
        if "econ_driver" in rule and ec:
            n.append(f"ec:{ec}")
        if "entity" in rule and en and fe != "sports":
            n.append(f"en:{en}")
        facts[m] = {"event_ids": n, "series_slugs": [], "event_slugs": [],
                    "neg_risk_market_id": None}
    g = pairing.dependence_groups(facts, underlying=False)
    return np.array([g[m] for m in f["market_id"]], dtype=object)


def nonsports_links(d: pd.DataFrame, rng) -> dict:
    """Per non-sports category: each candidate link merged over fixture_day clusters, against the
    label-permutation null (rows without an observed 2h dmid are not in ``d``)."""
    out = {}
    for proxy in PROXIES:
        e = centred(d, proxy, "strata")
        out[proxy] = {}
        for lab in ("ent", "ent_day", "econ", "src", "endts"):
            r = perm_link(d, e, "fixture_day", lab, NON_SPORTS, rng)
            out[proxy][lab] = {c: v for c, v in r.items() if v["base_clusters_with_label"] >= 5}
    return out


def variance_share(d: pd.DataFrame, G: dict) -> dict:
    """Share of the panel CR variance (fixture_day) per category, and the within-category ratio
    of each category-aware grouping over fixture_day (strata centring)."""
    out = {}
    for proxy in PROXIES:
        e = centred(d, proxy, "strata")
        vt = V(e, d["fixture_day"])[0]
        out[proxy] = {"panel_ratio": {k: round(V(e, d[k])[0] / vt, 3) for k in G}}
        for cat in NON_SPORTS:
            m = (d["fee"] == cat).to_numpy()
            if m.sum() < 100:
                continue
            vb = V(e[m], d.loc[m, "fixture_day"])[0]
            out[proxy][cat] = {"variance_share": round(vb / vt, 4), **{
                k: round(V(e[m], d.loc[m, k])[0] / vb, 3) for k in G}}
    return out


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, help="write the JSON report here (default: stdout)")
    ap.add_argument("--facts", default=FACTS, help="snapshot id with a complete sidecar")
    ap.add_argument("--periods", nargs=3, default=list(PERIODS),
                    help="three consecutive complete snapshot ids (two 2h periods)")
    ap.add_argument("--frame", type=Path, default=FRAME, help="fs2 frame for parentEventId")
    ap.add_argument("--no-parents", action="store_true", help="skip the frame parentEventId pass")
    ap.add_argument("--force", action="store_true", help="run even if a collector is running")
    a = ap.parse_args(argv)
    busy = collectors_running()
    if busy and not a.force:
        print("collector running, refusing (memory rule):", busy, file=sys.stderr)
        return 2
    rep: dict = {"facts_snapshot": a.facts, "periods": list(a.periods), "seed": SEED,
                 "permutations": N_PERM}
    manifest(a.facts)
    f = load_facts(a.facts)
    parents, sources, tags = (None, None, None) if a.no_parents else stream_frame(a.frame)
    rep["parent_source"] = None if a.no_parents else a.frame.name
    rep["gamma_tags"] = {"rows_columns": int(any("tag" in c for c in ROW_COLS)),
                         "sidecar_columns": [c for c in json.loads(
                             (SNAPS / a.facts / "ext_manifest.json").read_text()).get(
                             "columns", []) if "tag" in c], "frame_markets_keyset": tags}
    f = prepare(f, parents, sources)
    del parents, sources
    G = {k: build_groups(f, *v) for k, v in DEFS.items()}
    dg = ml_panel.dependence_group_ids(f, f["market_id"].to_numpy())
    # ml_panel: dep_group_season = league-season (6c5a074 dep_group); dep_group = fixture-day
    # (no parent_event_ids column here, so it equals the sidecar-only definition)
    assert (dg["dep_group_season"].to_numpy() == G["season_series"]).all()
    assert (dg["dep_group"].to_numpy() == G["fixture_day_sidecar"]).all()
    rep["chaining"] = chaining(f, G["season_series"])
    rep["event_slug_token_only_markets"] = int(sum(
        bool(set(u) - set(ud)) for u, ud in zip(f["tok_u"], f["tok_ud"], strict=True)))
    # populations of the facts snapshot
    t0 = ml_panel._start_epoch(manifest(a.facts))
    b = (f["binary"] == 1).to_numpy()
    elig = np.zeros(len(f), bool)
    elig[np.where(b)[0][panel.eligibility_mask(f[b], t0 + 7200)]] = True
    end = panel._epoch(f["end_date"])
    liq = pd.to_numeric(f["liquidity"], errors="coerce").to_numpy(float)
    d120 = (liq >= D120_LIQUIDITY) & (np.isnan(end) | (end > t0))
    pops = {"universe": np.ones(len(f), bool), "ml_eligible": elig, "d120_population": d120}
    rep["sizes"] = {k: {p: size_metrics(G[k][m]) for p, m in pops.items()} for k in DEFS}
    rep["largest_cluster_ml_eligible"] = {k: largest_cluster(f, G[k], elig) for k in DEFS}
    # category-aware groupings (section 8): fixture_day + evidence-backed non-sports links
    CG = {k: build_category_groups(f, G["fixture_day"], r) for k, r in CAT_RULES.items()}
    pair = [int(np.where(f["market_id"] == m)[0][0]) for m in D120_ECON_PAIR]
    rep["category_sizes"] = {k: {**{p: size_metrics(g[m]) for p, m in pops.items()},
                                 "largest_ml_eligible": largest_cluster(f, g, elig),
                                 "d120_econ_pair_grouped": bool(g[pair[0]] == g[pair[1]])}
                             for k, g in {"fixture_day": G["fixture_day"], **CG}.items()}
    rep["d120_econ_pair"] = {m: {"ent": f["ent"].iat[i], "econ": f["econ"].iat[i],
                                 "src": f["src"].iat[i], "end": f["endts"].iat[i],
                                 "ml_eligible": bool(elig[i]), "d120_population": bool(d120[i])}
                             for m, i in zip(D120_ECON_PAIR, pair, strict=True)}
    rep["entity_coverage"] = {c: round(float(f.loc[f["fee_category"] == c, "ent"].notna().mean()),
                                       3) for c in NON_SPORTS}
    # two 2h periods
    d = period_rows(tuple(a.periods), f)
    rep["pair_rows"] = {"rows": int(len(d)), "in_facts": int(d["in_facts"].sum())}
    d = d[d["in_facts"]].reset_index(drop=True)
    idx = pd.Series(np.arange(len(f)), index=f["market_id"]).loc[d["market_id"]].to_numpy()
    for k in DEFS:
        d[k] = G[k][idx]
    d["fee"] = f["fee_category"].to_numpy()[idx]
    d["ser"] = f["ser"].to_numpy()[idx]
    days = f["day"].to_numpy()[idx]
    d["sday"] = [None if s is None else f"{s}|{dy}" for s, dy in zip(d["ser"], days, strict=True)]
    d["absd"] = d["dmid"].abs()
    d["moved"] = (d["absd"] > ml_panel.DELTA_PRIMARY + ml_panel._DELTA_EPS).astype(float)
    d["cell"] = strata(d)
    for c in ("ent", "econ", "src", "endts"):
        d[c] = f[c].to_numpy()[idx]
    d["ent_day"] = [None if x is None else f"{x}|{dy}" for x, dy in zip(d["ent"], days,
                                                                          strict=True)]
    for k, g in CG.items():
        d[k] = g[idx]
    rep["moved_share"] = round(float(d["moved"].mean()), 4)
    rep["pooled_sizes"] = {}
    for k in DEFS:
        k0 = set(d.loc[d["period"] == 0, k])
        rep["pooled_sizes"][k] = {**size_metrics(d[k]), "K_period0": len(k0),
                                  "K_period1": int(d.loc[d["period"] == 1, k].nunique()),
                                  "new_in_period1": int(len(set(d[k]) - k0))}
    rng = np.random.default_rng(SEED)
    rep["design_effects"], rep["permutation"], rep["series_icc"] = {}, {}, {}
    for proxy in PROXIES:
        for how in ("strata", "period_fee"):
            e = centred(d, proxy, how)
            ve, _ = V(e, d["event"])
            row = {"market": round(V(e, d["market_id"])[0] / ve, 3)}
            for k in DEFS:
                v, df = V(e, d[k])
                row[k] = {"DE_vs_event": round(v / ve, 3), "var_df": round(df, 1)}
            rep["design_effects"][f"{proxy}|{how}"] = row
            if how == "strata":
                cats = ["sports", "crypto", "other", "all"]
                rep["permutation"][proxy] = {
                    "season_over_outcome": perm_link(d, e, "outcome", "ser", cats, rng),
                    "day_over_outcome": perm_link(d, e, "outcome", "sday", cats, rng),
                    "season_over_fixture_day": perm_link(d, e, "fixture_day", "ser", ["all"],
                                                         rng),
                }
                rep["series_icc"][proxy] = series_icc(d, e, "outcome")
        # category x period: is the category-level component a shock or a fixed effect? Per
        # category, the deviation of its mean from the period mean in each period, and the z of
        # the period-to-period change (SE under fixture_day clustering, centred in the cell).
        rep.setdefault("category_period", {})[proxy] = category_period(d, proxy)
        # crypto underlying rule (within-crypto centring): all dates vs token x UTC end date
        cr = (d["fee"] == "crypto").to_numpy()
        sub = d[cr]
        out = {"rows": int(cr.sum())}
        for how in ("strata", "period_fee"):
            e = centred(d, proxy, how)[cr]
            out[f"outcome_u_over_ud|{how}"] = round(
                V(e, sub["outcome"])[0] / V(e, sub["outcome_ud"])[0], 3)
        rep.setdefault("crypto", {})[proxy] = out
    rep["d120_econ_pair_rows"] = {m: int((d["market_id"] == m).sum()) for m in D120_ECON_PAIR}
    rep["nonsports_links"] = nonsports_links(d, rng)
    rep["category_variance"] = variance_share(d, {"fixture_day": d["fixture_day"].to_numpy(),
                                                  **CG})
    text = json.dumps(clean(rep), indent=1)
    if a.out:
        a.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
