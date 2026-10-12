"""Case catalogue: pull data and build descriptive timelines (EXPLORATORY_HISTORICAL).

  python scripts/run_case_catalogue.py pull [case_id ...]
  python scripts/run_case_catalogue.py timeline
  python scripts/run_case_catalogue.py controls [case_id ...]
  python scripts/run_case_catalogue.py panel

Pull yields to the live collector (no request while arepo_pass.sh runs), paces at <= 4 req/s with
backoff, keeps the case_studies tree under 1 GB and refuses to start with < 250 MB swap free.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from astrolabe.research_lab import case_catalogue as cc
from astrolabe.research_lab import history_backfill as hb
from astrolabe.research_lab import history_sources as hs
from astrolabe.research_lab import provenance

REG = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "case_catalogue_registry.json"


def pull(ids: list[str]) -> None:
    cases = [c for c in cc.load_registry(REG) if c.slugs and (not ids or c.case_id in ids)]
    hs.heavy_gate()
    lim = cc.make_limiter(4.0)
    budget = hb.DiskBudget(cc.ROOT, cc.DISK_CAP_BYTES)
    for c in cases:
        d = cc.ROOT / c.case_id
        mf = d / "manifest.json"
        old = json.loads(mf.read_text()) if mf.exists() else None
        if old and old.get("version") == cc.CATALOGUE_VERSION and not any(
                "error" in v for v in old["markets"].values()):
            print(f"{c.case_id}: already pulled")
            continue
        m = cc.pull_case(c, d, lim=lim, budget=budget)
        print(f"{c.case_id}: requests so far {m['requests']}, used {budget.used / 1e6:.1f} MB",
              flush=True)


MADURO = cc.ROOT.parent / "event_study" / "markets.json"


def _excludes() -> tuple[set[str], set[str]]:
    import re

    cat = REG.parent / "CASE_CATALOGUE.md"  # the pinned case list
    cids, evs = set(re.findall(r"0x[0-9a-f]{64}", cat.read_text())), set()
    for c in cc.load_registry(REG):
        mf = cc.ROOT / c.case_id / "manifest.json"
        if mf.exists():
            for mm in json.loads(mf.read_text())["markets"].values():
                cids.add(mm.get("condition_id", ""))
    if MADURO.exists():
        for m in json.loads(MADURO.read_text())["markets"]:
            cids.add(m["condition_id"])
            evs.add(str(m.get("event_id", "")))
    return cids, evs


def controls(ids: list[str]) -> None:
    hs.heavy_gate()
    lim = cc.make_limiter(4.0)
    key = cc.wallet_sidecar.load_or_create_key()
    budget = hb.DiskBudget(cc.ROOT, cc.DISK_CAP_BYTES)
    ex_cids, ex_evs = _excludes()
    for c in cc.load_registry(REG):
        if ids and c.case_id not in ids:
            continue
        d = cc.ROOT / c.case_id
        man = json.loads((d / "manifest.json").read_text())
        out = d / "controls.json"
        if out.exists() and json.loads(out.read_text()).get("complete"):
            print(f"{c.case_id}: controls done")
            ex_cids |= {m["frame"]["condition_id"] for m in json.loads(out.read_text())["controls"]}
            continue
        primary = man["markets"][c.slugs[0]]
        case_fr = cc.gamma_market(lim, c.slugs[0])
        case_fr = cc.hb.frame_row(case_fr)
        prices = cc.read_gz_csv(d / f"prices_{primary['market_id']}.csv.gz")
        p72 = cc.price_at(prices[["ts", "p0"]].to_numpy(), c.news_ts - 72 * 3600)
        band = cc.price_band(float("nan") if p72 is None else p72)
        own_ev = {case_fr["event_id"]}
        sel = cc.select_controls(lim, case_fr, c.news_ts, band, ex_cids, ex_evs | own_ev)
        res = {"case_id": c.case_id, "rule": cc.CONTROL_RULE, "case_band": band,
               "case_p_news_minus_72h": p72, "case_fee_category": case_fr["fee_category"],
               "case_liquidity_band": cc.hb.liquidity_band(case_fr["volume"]),
               "pool_size": sel["pool_size"], "examined": sel["examined"],
               "reasons": sel["reasons"], "controls": [], "complete": False,
               "evidence_role": cc.EVIDENCE_ROLE}
        budget.write(out, json.dumps(res, indent=1, default=str).encode())
        cdir = d / "controls"
        for g in ("quiet_move", "quiet_nomove"):
            for ch in sel[g]:
                mw = cc.pull_market_window(lim, key, budget, ch["fr"], ch["tau"], cdir,
                                           cc.PANEL_WALLETS)
                mw["control_group"] = g
                res["controls"].append(mw)
                print(f"{c.case_id}: {g} {mw['market_id']} trades={mw['n_trades_window']}",
                      flush=True)
                budget.write(out, json.dumps(res, indent=1, default=str).encode())
        ex_cids |= {m["frame"]["condition_id"] for m in res["controls"]}  # no market reused
        res["complete"] = True
        budget.write(out, json.dumps(res, indent=1, default=str).encode())


def panel() -> None:
    """Case-mode panel: case markets (news_ts set, control_group 'case') + quiet controls."""
    import pandas as pd

    from astrolabe.research_lab import detector_eval as de
    from astrolabe.research_lab import event_study as es

    hs.heavy_gate()
    act = {h: d.get("first_trade_ts") for h, d in es.read_first_trade_cache(cc.FT_CACHE).items()
           if d.get("first_trade_ts") is not None}
    items = []  # (case_id, group, frame, prices, trades, tau, news_ts)
    lim = cc.make_limiter(2.0)
    for c in cc.load_registry(REG):
        d = cc.ROOT / c.case_id
        mf, cf = d / "manifest.json", d / "controls.json"
        if not mf.exists() or not cf.exists() or not json.loads(cf.read_text()).get("complete"):
            print(f"{c.case_id}: skipped (data or controls incomplete)")
            continue
        for slug, mm in json.loads(mf.read_text())["markets"].items():
            if "error" in mm:
                continue
            fr = cc.hb.frame_row(cc.gamma_market(lim, slug))
            mid = mm["market_id"]
            items.append((c.case_id, "case", fr, cc.read_gz_csv(d / f"prices_{mid}.csv.gz"),
                          cc.read_gz_csv(d / f"trades_{mid}.csv.gz"), c.news_ts, c.news_ts))
        for mw in json.loads(cf.read_text())["controls"]:
            cd = d / "controls"
            items.append((c.case_id, mw["control_group"], mw["frame"],
                          cc.read_gz_csv(cd / f"prices_{mw['market_id']}.csv.gz"),
                          cc.read_gz_csv(cd / f"trades_{mw['market_id']}.csv.gz"), mw["tau"], None))
    for it in items:
        it[4]["wallet_hash"] = it[4]["wallet_hash"].astype(str)
    sub = {}
    for it in items:
        for h in cc.top_wallets(it[4], it[5]):
            if h in act:
                sub[h] = act[h]
    fs = cc.panel_first_seen([it[4] for it in items], sub)
    frames = []
    for case_id, g, fr, pr, tr, _tau, news in items:
        rows = cc.market_rows(fr, pr, tr, fs, f"case_panel:{case_id}")
        if not len(rows):
            continue
        rows["news_ts"] = float(news) if news is not None else float("nan")
        rows["control_group"] = g
        rows["case_id"] = case_id
        frames.append(rows)
    df = pd.concat(frames, ignore_index=True)
    p = de.normalise_panel(df, "history")
    p["case_id"] = p["market_id"].map(df.drop_duplicates("market_id").set_index(
        "market_id")["case_id"])
    out = cc.ROOT / "case_panel.csv.gz"
    p.to_csv(out, index=False)
    meta = {"rows": int(len(p)), "markets": int(p["market_id"].nunique()),
            "by_group": p.groupby("control_group")["market_id"].nunique().to_dict(),
            "attrs": {k: v for k, v in p.attrs.items()}, "first_seen": "min(panel trades, "
            "/activity first trade of top-200 pre-tau notional wallets per market)",
            "evidence_role": cc.EVIDENCE_ROLE, "sha256": provenance.sha256_file(out)}
    (cc.ROOT / "case_panel.manifest.json").write_text(json.dumps(meta, indent=1, default=str))
    print(json.dumps(meta, indent=1, default=str))


def timeline() -> None:
    out = {}
    for c in cc.load_registry(REG):
        d = cc.ROOT / c.case_id
        mf = d / "manifest.json"
        if not mf.exists():
            continue
        man = json.loads(mf.read_text())
        w0, w1 = man["window"]
        res = {}
        for slug, mm in man["markets"].items():
            if "error" in mm:
                res[slug] = mm
                continue
            df = cc.load_case_market(d, mm["market_id"], mm, w0, w1)
            df.to_csv(d / f"timeline_{mm['market_id']}.csv.gz", index=False)
            prices = cc.read_gz_csv(d / f"prices_{mm['market_id']}.csv.gz")
            on = cc.unusual_onset(df, c.news_ts)
            mv = cc.first_move_ts(prices, c.news_ts)
            on["first_p0_ge_0.9_ts"] = mv
            on["first_move_minus_news_h"] = (None if mv is None
                                             else round((mv - c.news_ts) / 3600, 2))
            on["question"] = mm["question"]
            on["n_trades_window"] = mm["n_trades_window"]
            on["incomplete_windows"] = len(mm["trades"]["incomplete_windows"])
            on["coverage_from_ts"] = mm["coverage_from_ts"]
            on["coverage_h_before_news"] = round((c.news_ts - mm["coverage_from_ts"]) / 3600, 1)
            res[slug] = on
        out[c.case_id] = res
        provenance.append_trial({
            "kind": "history_case_timeline", "label": "EXPLORATORY",
            "evidence_role": cc.EVIDENCE_ROLE, "data_provenance": cc.PROVENANCE,
            "case_id": c.case_id, "status": c.status, "rule": cc.UNUSUAL_RULE,
            "results": res, "manifest_sha256": provenance.sha256_file(mf),
            "provenance": provenance.run_provenance(),
        })
    p = cc.ROOT / "timeline_summary.json"
    p.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "timeline"
    if cmd == "pull":
        pull(sys.argv[2:])
    elif cmd == "controls":
        controls(sys.argv[2:])
    elif cmd == "panel":
        panel()
    else:
        timeline()
