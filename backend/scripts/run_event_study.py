"""Event study (Maduro case) and unusual-flow detector plumbing. EXPLORATORY_HISTORICAL only.

Subcommands
  find       Gamma search for markets matching keywords -> markets.json
  probe      does /trades honour a time window? -> trade_window_probe.json
  pull       prices (10-min fidelity) and ALL trades for the chosen markets over a window, hashed
             wallets only; then /activity first-trade time per wallet (cached by hash)
  timeline   bin features (10 min and 1 h) per market -> timeline_<id>_<bin>.csv.gz + summary
  bsample    Part B: seeded stratified sub-sample of an existing history run (no requests)

Live-collector yield, <= 3 rps, swap check before heavy steps. Raw addresses are held in memory
only during ``pull`` and dropped after the lookups.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import event_study as es  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab.wallet_sidecar import load_or_create_key  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data-dumps" / "research_lab" / "event_study"
RPS = 3.0


def _lim() -> hb.Limiter:
    return hb.Limiter(hb.httpx_transport(), rps=RPS, live_check=hb.live_pass_running)


def cmd_find(a) -> None:
    lim = _lim()
    found: dict[str, dict] = {}
    for q in a.q:
        for page in range(1, a.pages + 1):
            st, d = lim.get(es.GAMMA_SEARCH, {"q": q, "limit_per_type": 50, "page": page,
                                              "events_status": "all", "keep_closed_markets": 1})
            evs = (d or {}).get("events") or [] if isinstance(d, dict) else []
            for e in evs:
                st2, full = lim.get(es.GAMMA_EVENTS, {"slug": e.get("slug")})
                full = full[0] if isinstance(full, list) and full else e
                for m in full.get("markets") or []:
                    found[str(m.get("id"))] = {
                        "event_id": str(full.get("id")), "event_slug": full.get("slug"),
                        "event_title": full.get("title"), "market_id": str(m.get("id")),
                        "question": m.get("question"), "slug": m.get("slug"),
                        "condition_id": m.get("conditionId"),
                        "clob_token_ids": m.get("clobTokenIds"), "outcomes": m.get("outcomes"),
                        "outcome_prices": m.get("outcomePrices"),
                        "created_at": m.get("createdAt"), "start_date": m.get("startDate"),
                        "end_date": m.get("endDate"), "closed_time": m.get("closedTime"),
                        "closed": m.get("closed"), "uma_status": m.get("umaResolutionStatus"),
                        "volume": m.get("volumeNum"), "neg_risk": m.get("negRisk"),
                        "query": q}
            if len(evs) < 50:
                break
    OUT.mkdir(parents=True, exist_ok=True)
    es.write_json(OUT / "markets.json", {"queries": a.q, "retrieved_utc": hb.utc_iso(),
                                         "markets": list(found.values())})
    for m in sorted(found.values(), key=lambda m: -(m["volume"] or 0))[: a.show]:
        print(m["market_id"], m["event_slug"], "|", m["question"], "|", m["created_at"],
              m["closed_time"], m["outcome_prices"], round(m["volume"] or 0))


def _market(mid: str) -> dict:
    ms = json.loads((OUT / "markets.json").read_text())["markets"]
    return next(m for m in ms if m["market_id"] == mid)


def cmd_probe(a) -> None:
    m = _market(a.market)
    res = es.probe_trade_windows(_lim(), m["condition_id"], a.lo, a.hi)
    es.write_json(OUT / "trade_window_probe.json", {"market_id": a.market, "lo": a.lo,
                                                    "hi": a.hi, "result": res})
    print(json.dumps(res, indent=1))


def cmd_pull(a) -> None:
    es.heavy_gate()
    key = load_or_create_key()
    lim = _lim()
    wp = tuple(a.window_param.split("/")) if a.window_param else None
    ft_path = OUT / "first_trade.jsonl"
    for mid in a.markets:
        m = _market(mid)
        d = OUT / "markets" / mid
        tok0 = json.loads(m["clob_token_ids"])[0]
        pts, nreq = hb.fetch_prices(lim, tok0, a.start, a.end)
        d.mkdir(parents=True, exist_ok=True)
        (d / "prices.csv.gz").write_bytes(hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
        rows, st, addrs = es.fetch_trades_full(lim, m["condition_id"], key, a.start, a.end, wp,
                                               keep_addresses=True)
        es.write_trades(d / "trades.csv.gz", rows)
        first_ts: dict[str, int] = {}
        for r in rows:
            first_ts[r[5]] = min(first_ts.get(r[5], r[0]), r[0])
        wallets = {h: (addrs[h], ts) for h, ts in first_ts.items() if h in addrs}
        addrs.clear()
        lk = es.first_trade_lookups(lim, wallets, ft_path, budget_s=a.budget_min * 60)
        wallets.clear()  # raw addresses dropped
        es.write_json(d / "manifest.json", {
            "market_id": mid, "condition_id": m["condition_id"], "question": m["question"],
            "window": [a.start, a.end], "price_points": len(pts), "price_requests": nreq,
            "price_fidelity_min": hb.FIDELITY_MIN, "trades": st, "distinct_wallets": len(first_ts),
            "first_trade_lookups": lk, "requests": lim.requests, "http_429": lim.throttled,
            "yielded_to_live_s": lim.yielded_s, "retrieved_utc": hb.utc_iso(),
            "raw_addresses_stored": False, "key_id": hb.key_id(key)})
        print(mid, len(pts), st["n"], st["windows"], st["incomplete_windows"][:3],
              len(first_ts), lk)


def cmd_timeline(a) -> None:
    ft = es.read_first_trade_cache(OUT / "first_trade.jsonl")
    for mid in a.markets:
        d = OUT / "markets" / mid
        man = json.loads((d / "manifest.json").read_text())
        pr = pd.read_csv(d / "prices.csv.gz")
        tr = es.prepare_trades(hb.load_trades(d / "trades.csv.gz"), ft)
        covered = (-np.inf if not man["trades"].get("incomplete_windows")
                   and not man["trades"].get("truncated") else float(tr["ts"].min()))
        for bin_s in (600, 3600):
            df = es.bin_features(tr, pr["t"].to_numpy(float), pr["p"].to_numpy(float),
                                 man["window"][0], man["window"][1], bin_s, covered)
            df.to_csv(d / f"timeline_{bin_s}s.csv.gz", index=False)
        print(mid, "bins", len(df), "wallet age coverage",
              round(float(tr["wallet_age_days"].notna().mean()), 3))


def cmd_bsample(a) -> None:
    run = Path(a.run)
    s = pd.read_csv(run / "sample.csv.gz", dtype={"market_id": str, "token0": str, "token1": str,
                                                  "event_id": str}, keep_default_na=False)
    rows = s.to_dict("records")
    for r in rows:
        r.setdefault("status", "")
    sub, rep = hb.draw_sample(rows, a.n, a.seed, by_category=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sub).to_csv(OUT / "bsample.csv.gz", index=False)
    es.write_json(OUT / "bsample.manifest.json", {"source_run": str(run.relative_to(REPO)),
                                                  "report": rep, "created_utc": hb.utc_iso()})
    print(rep["n"], "markets", "pool", rep["pool"])


def _condition_ids(obj) -> set[str]:
    """Every ``condition_id``/``conditionId`` value anywhere in a JSON document (not printed)."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("condition_id", "conditionId") and isinstance(v, str) and v:
                out.add(v.lower())
            else:
                out |= _condition_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _condition_ids(v)
    return out


PANEL_KEEP = ("market_id", "event_id", "t_i", "mid_i", "horizon_target_h", "y_dmid",
              "traded_before_t", "fee_category", "status", "stratum")


def cmd_bpanel(a) -> None:
    """Broad panel for the frozen-rule evaluation: the ``build_panel`` outputs of an existing
    seeded history run, restricted to the seeded ``bsample`` sub-sample, minus Maduro/Venezuela
    and catalogue markets (by condition_id), normalised with ``detector_eval.normalise_panel``.
    Writes the discovery cut (row-time median of the normalised panel)."""
    from astrolabe.research_lab import detector_eval as de

    es.heavy_gate()
    run = Path(a.run)
    sub = pd.read_csv(OUT / "bsample.csv.gz", dtype={"market_id": str, "condition_id": str},
                      keep_default_na=False)
    excl = {m["condition_id"].lower() for m in
            json.loads((OUT / "markets.json").read_text())["markets"] if m.get("condition_id")}
    n_maduro = len(excl)
    cat = REPO / "docs" / "research_lab" / "case_catalogue_registry.json"
    cat_ids = _condition_ids(json.loads(cat.read_text())) if cat.exists() else set()
    # the registry holds slugs; the catalogue agent's pulled manifests hold condition ids (case
    # markets and their quiet controls, all excluded); re-checked at evaluation time
    for f in (REPO / "data-dumps" / "research_lab" / "case_studies").rglob("*.json"):
        try:
            cat_ids |= _condition_ids(json.loads(f.read_text()))
        except ValueError:
            continue
    excl |= cat_ids
    drop = sub["condition_id"].str.lower().isin(excl)
    keep_ids = set(sub.loc[~drop, "market_id"])
    parts = []
    for h in (2, 6, 24):
        it = pd.read_csv(run / f"panel_H{h}h.csv.gz", dtype={"market_id": str, "event_id": str},
                         keep_default_na=False, na_values=[""], chunksize=200_000,
                         usecols=lambda c: c in PANEL_KEEP or c.startswith(("ml_tf_", "ml_wlt_")))
        for ch in it:
            parts.append(ch[ch["market_id"].isin(keep_ids)])
    raw = pd.concat(parts, ignore_index=True)
    raw["event_id"] = raw["event_id"].fillna("").astype(str)
    panel = de.normalise_panel(raw, "history")
    panel["status"] = raw.drop_duplicates(["market_id", "t_i"]).set_index(
        ["market_id", "t_i"]).reindex(pd.MultiIndex.from_arrays(
            [panel["market_id"], panel["t"]]))["status"].to_numpy()
    attrs = dict(panel.attrs)
    cut = float(np.median(panel["t"].to_numpy(float)))
    panel["half"] = np.where(panel["t"] >= cut, "judgement", "discovery")
    panel.to_csv(OUT / "broad_panel.csv.gz", index=False)
    traded = panel["traded_before_t"]
    es.write_json(OUT / "broad_panel.manifest.json", {
        "source_run": str(run.relative_to(REPO)), "source_builder": "history_backfill.build_panel",
        "bsample_seed": json.loads((OUT / "bsample.manifest.json").read_text())["report"]["seed"],
        "markets_in_bsample": len(sub), "markets_excluded_maduro_venezuela_or_catalogue":
            int(drop.sum()), "maduro_venezuela_condition_ids": n_maduro,
        "catalogue_condition_ids": len(cat_ids),
        "markets_with_rows": int(panel["market_id"].nunique()), "rows": len(panel),
        "rows_traded_before_t": {"1": int((traded == 1).sum()), "0": int((traded == 0).sum()),
                                 "nan": int(traded.isna().sum())},
        "discovery_cut_epoch": cut, "discovery_cut_utc": hb.utc_iso(cut),
        "discovery_cut_rule": "median of t over all rows of the normalised broad panel "
        "(after exclusions, before the traded_before_t filter)",
        "rows_by_half": panel["half"].value_counts().to_dict(),
        "clusters_by_half": panel.groupby("half")["cluster"].nunique().to_dict(),
        "panel_attrs": attrs, "created_utc": hb.utc_iso(),
        "notes": ["liquidity is NaN in history panels (end-of-life Gamma value is look-ahead)",
                  "new_wallet_share_l is new-to-sample (FirstSeen over the 3,200-market run), "
                  "left-censored; not Polymarket wallet age"]})
    print(len(panel), "rows", panel["market_id"].nunique(), "markets; cut", hb.utc_iso(cut),
          "excluded", int(drop.sum()))


def main() -> None:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("find")
    f.add_argument("--q", nargs="+", default=["maduro"])
    f.add_argument("--pages", type=int, default=3)
    f.add_argument("--show", type=int, default=60)
    p = sp.add_parser("probe")
    p.add_argument("--market", required=True)
    p.add_argument("--lo", type=int, required=True)
    p.add_argument("--hi", type=int, required=True)
    u = sp.add_parser("pull")
    u.add_argument("--markets", nargs="+", required=True)
    u.add_argument("--start", type=int, required=True)
    u.add_argument("--end", type=int, required=True)
    u.add_argument("--window-param", default=None, help="e.g. start/end if /trades honours it")
    u.add_argument("--budget-min", type=float, default=90)
    t = sp.add_parser("timeline")
    t.add_argument("--markets", nargs="+", required=True)
    b = sp.add_parser("bsample")
    b.add_argument("--run", default=str(REPO / "data-dumps/research_lab/history/h2_main"))
    b.add_argument("--n", type=int, default=1500)
    b.add_argument("--seed", default="arepo-unusual-flow-b1")
    bp = sp.add_parser("bpanel")
    bp.add_argument("--run", default=str(REPO / "data-dumps/research_lab/history/h2_main"))
    a = ap.parse_args()
    t0 = time.time()
    {"find": cmd_find, "probe": cmd_probe, "pull": cmd_pull, "timeline": cmd_timeline,
     "bsample": cmd_bsample, "bpanel": cmd_bpanel}[a.cmd](a)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
