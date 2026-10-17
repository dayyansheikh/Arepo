# ruff: noqa: E501
"""CB4 analysis commands (docs/research_lab/CREATIVE_BATCH_4.md section 4.2), plugged into ``scripts/run_cb4.py`` as ``cmd_<name>(args)``.

Uncounted (no declaration; counts only, outcome columns never read): ``pilot``, ``flip-trades``, ``census``.
Counted (refused unless the committed ``model_specs/cb4_v1.json`` carries this code's declaration hash; results are never overwritten):
``measure-N``, ``measure-E``, ``measure-commit``, ``fetch-outcomes``, ``screen``, ``replicate``. CB4 declares no Stage P, so there is no ``stagep`` command.
Exit codes: 0 ok / nothing advanced, 3 refused by a guard.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import battery2, cb4_data, cost_regimes, forecast, provenance
from . import cb1_history as H1
from . import cb3_common as CC
from . import cb4_declaration as D
from . import cb4_measure as M
from . import cb4_rules as R
from . import history_backfill as hb

REFUSED_EXIT = 3
OUT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "creative_batch4"
HIST_ROOT = cb4_data.HIST_ROOT
LABEL = D.LABEL
HOUR, DAY = 3600.0, 86400.0


class Refusal(RuntimeError):
    """A guard refused the command."""


@dataclass
class Ctx:
    """Run values. The CLI has no flag for any declared quantity; tests build a Ctx directly (never reachable from the command line)."""

    spec: Path = D.SPEC_PATH
    require_committed: bool = True
    trials: Path = provenance.TRIALS_PATH
    now: datetime | None = None
    out_root: Path = OUT_ROOT
    hist_root: Path = HIST_ROOT
    extract_root: Path = cb4_data.CB4_ROOT
    rep_pin: Path | None = None
    register: Path | None = None
    n_boot: int = D.N_BOOT
    placebo_draws: int = D.PLACEBO_DRAWS
    lim: object | None = None  # injectable limiter (tests); real runs build one
    pmxt_fetch: object | None = None
    pmxt_size: object | None = None


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _parser(cmd: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog=f"run_cb4.py {cmd}")
    for f in ("--family", "--window", "--run-id", "--extract-root", "--from", "--to", "--seed"):
        ap.add_argument(f, default=None)
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--n-boot", type=int, default=None)
    ap.add_argument("--hours", type=int, default=None)
    ap.add_argument("--ingress-cap-gb", type=float, default=None)
    ap.add_argument("--budget-min", type=float, default=None)
    ap.add_argument("--hours-from-census", action="store_true")
    return ap


def _args(cmd: str, a) -> argparse.Namespace:
    extra = list(getattr(a, "extra", []) or [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    return _parser(cmd).parse_args(extra)


def _limiter(ctx: Ctx, rps: float):
    return ctx.lim if ctx.lim is not None else hb.Limiter(hb.httpx_transport(), rps=min(rps, 4.0))


def _gate(ctx: Ctx, a: argparse.Namespace, *, counted: bool) -> str | None:
    """Declared-value and run-id guards. Counted commands also need the committed declaration (hash equals the code's)."""
    D.refuse_run_id(a.run_id)
    if a.extract_root:
        D.refuse_path(a.extract_root)
    D.refuse_path(ctx.extract_root)
    if a.n_boot is not None and a.n_boot != D.N_BOOT and ctx is not None and ctx.n_boot == D.N_BOOT:
        raise Refusal(f"--n-boot {a.n_boot} differs from the declared {D.N_BOOT}")
    return D.require_declaration(ctx.spec, require_committed=ctx.require_committed) if counted else None


# ---- trials -----------------------------------------------------------------------------------------------------------------------


def log_trials(job: str, tests: dict, *, kind: str, role: str, dataset: str, results_path: str, sha: str, decl: str | None, cumulative, placebo: dict | None,
               descriptive: dict | None, trials_path: Path, count_source: str) -> None:
    """One line per counted test, one placebo summary line per test (count 0), one ``cb4_descriptive`` line per descriptive item and one ``ml_explain``
    count line (``creative_batch_4:<C|S|M>``, ``n_tests``)."""
    prov = provenance.run_provenance()
    keys = ("effect", "p", "n", "advance", "testable", "placebo_status", "replicated", "adopted")
    for name, t in tests.items():
        provenance.append_trial({"status": "ok", "dataset": dataset, "preset": name, "label": LABEL, "kind": kind, "evidence_role": role, "revision": D.VERSION,
                                 "result_path": results_path, "results_sha256": sha, "declaration_sha256": decl, "cumulative_count_at_run": cumulative,
                                 "summary": {k: t.get(k) for k in keys}, "provenance": prov}, trials_path)
    for name, p in (placebo or {}).items():
        provenance.append_trial({"status": "ok", "dataset": dataset, "preset": f"{name}:placebo", "label": LABEL, "kind": kind, "evidence_role": "placebo", "revision": D.VERSION,
                                 "result_path": results_path, "results_sha256": sha, "declaration_sha256": decl, "summary": {k: p.get(k) for k in ("n_draws", "advance_rate", "calibrated")}}, trials_path)
    for name, d in (descriptive or {}).items():
        provenance.append_trial({"status": "ok", "dataset": dataset, "preset": name, "label": LABEL, "kind": D.KIND_DESCRIPTIVE, "evidence_role": role, "revision": D.VERSION,
                                 "result_path": results_path, "results_sha256": sha, "declaration_sha256": decl, "summary": d}, trials_path)
    provenance.append_trial({"dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY", "n_tests": len(tests), "revision": D.VERSION,
                             "source": count_source, "results_sha256": sha, "declaration_sha256": decl, "note": "CB4 count line; per-test cb4_* lines are EXCLUDEd in battery2.KIND_RULES"}, trials_path)


def _header(job: str, decl: str | None, **kw) -> dict:
    return {"label": LABEL, "version": D.VERSION, "job": job, "declaration_sha256": decl, "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cumulative_count_at_run": battery2.cumulative_count()["total"], "provenance": provenance.run_provenance(), "interpretations": [*R.INTERPRETATIONS, *M.INTERPRETATIONS], **kw}


def _write(ctx: Ctx, rel: str, doc: dict) -> tuple[Path, str]:
    p = ctx.out_root / rel
    if "history" in p.parts and "creative_batch4" not in p.parts:
        raise Refusal("results are never written inside a sealed run directory")
    return p, CC.write_new(p, doc)


def _jload(p: Path) -> dict | None:
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


# ---- loaders -----------------------------------------------------------------------------------------------------------------------


def load_captures(root: Path, start: float, end: float) -> tuple[list[pd.DataFrame], dict[str, set[str]]]:
    """Parsed closewin captures with ``start <= capture_start < end`` and the departures sets per capture id."""
    caps, deps = [], {}
    cdir = Path(root) / "closewin"
    for f in sorted(cdir.glob("*.csv.gz")) if cdir.exists() else []:
        df = cb4_data.read_closewin(root, f.name[: -len(".csv.gz")])
        if not len(df):
            continue
        p = R.parse_closewin(df)
        t = float(p["cap_start"].iloc[0])
        if start <= t < end:
            caps.append(p)
            dp = Path(root) / "departures" / f.name
            if dp.exists():
                deps[str(p["capture_id"].iloc[0])] = set(cb4_data.read_closewin(root, f.name[: -len(".csv.gz")], departures=True)["market_id"])
    return caps, deps


def load_trades_dir(tdir: Path) -> dict[str, R.Trades]:
    out = {}
    man = _jload(Path(tdir) / "manifest.json") or {}
    meta = man.get("markets", {})
    for f in sorted(Path(tdir).glob("*.csv.gz")) if Path(tdir).exists() else []:
        mid = f.name[: -len(".csv.gz")]
        m = meta.get(mid, {})
        out[mid] = R.Trades(hb.load_trades(f), bool(m.get("trades_truncated", False)), m.get("trades_oldest_ts"))
    return out


def fetch_flip_trades(ctx: Ctx, market_ids: dict[str, str], tdir: Path, rps: float = 4.0, ts_cap: float | None = None) -> dict:
    """Data API trades for ``market_id -> condition_id`` (newest first, <= 10,000), strict (a failed page fails the market, never 'truncated'). Writes
    ``<mid>.csv.gz`` and a manifest with truncation facts; resumable (existing files are kept)."""
    lim, key = _limiter(ctx, rps), hb.load_or_create_key()
    Path(tdir).mkdir(parents=True, exist_ok=True)
    man = _jload(Path(tdir) / "manifest.json") or {"markets": {}}
    failed = 0
    for mid, cid in sorted(market_ids.items()):
        if mid in man["markets"]:
            continue
        try:
            rows, st = cb4_data.fetch_trades_strict(lim, cid, key, D.C["max_trades"], ts_cap=ts_cap)
        except cb4_data.ApiError:
            failed += 1
            continue
        (Path(tdir) / f"{mid}.csv.gz").write_bytes(hb._gz_csv_bytes(hb.TRADE_COLUMNS, rows))
        man["markets"][mid] = {"trades": st["n"], "trades_truncated": bool(st["truncated"]), "trades_oldest_ts": st["oldest_ts"]}
    (Path(tdir) / "manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return {"markets": len(man["markets"]), "failed": failed}


def fetch_market_outcomes(lim, ids: list[str], batch: int = 20) -> dict[str, dict]:
    """Gamma outcomes for markets (guarded: only called by commands that passed the outcome-date guard). ``y0`` = payout of token 0 (None if undecided)."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), batch):
        status, data = lim.get(hb.GAMMA_MARKETS, [("id", x) for x in ids[i:i + batch]] + [("limit", batch)])
        if status != 200 or not isinstance(data, list):
            continue
        for m in data:
            ct = cb4_data._parse_ts(m.get("closedTime")) if m.get("closedTime") else None
            out[str(m.get("id"))] = {"y0": H1.parse_outcome0(m.get("outcomePrices")) if m.get("closed") else None, "closed_time": ct if ct is not None else math.nan}
    return out


def load_era(rdir: Path) -> tuple[pd.DataFrame, dict[str, dict]]:
    sample = pd.read_csv(Path(rdir) / "sample.csv.gz", dtype={"market_id": str, "event_id": str})
    prog: dict[str, dict] = {}
    p = Path(rdir) / "progress.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "done":
                    prog[str(r["market_id"])] = r
    return sample, prog


def era_frames(rdir: Path, max_markets: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """E1 panel and E2 mark-outs over the sealed era run (no outcome file opened)."""
    sample, prog = load_era(rdir)
    panels, marks, diag = [], [], {"markets": 0, "no_files": 0}
    for _, r in sample.iterrows():
        mid = str(r["market_id"])
        pf, tf = Path(rdir) / "prices" / f"{mid}.csv.gz", Path(rdir) / "trades" / f"{mid}.csv.gz"
        if mid not in prog or not pf.exists() or not tf.exists():
            diag["no_files"] += 1
            continue
        if max_markets and diag["markets"] >= max_markets:
            break
        diag["markets"] += 1
        ts, vals = hb.load_prices(pf)
        tr = hb.load_trades(tf)
        rec = {"market_id": mid, "event_id": str(r["event_id"]) if str(r["event_id"]) not in ("nan", "") else None, "end_epoch": float(r["end_epoch"]), "group": r["group"], "period": r["period"]}
        pr = prog[mid]
        pan = M.era_panel(rec, ts, vals, tr, bool(pr.get("trades_truncated")), pr.get("trades_oldest_ts"))
        if len(pan):
            pan["end_epoch"] = rec["end_epoch"]
            panels.append(pan)
        mk = M.markouts(rec, ts, vals, tr)
        if len(mk):
            mk["end_epoch"] = rec["end_epoch"]
            marks.append(mk)
    return (pd.concat(panels, ignore_index=True) if panels else pd.DataFrame()), (pd.concat(marks, ignore_index=True) if marks else pd.DataFrame()), diag


def load_series(rdir: Path, which: str | None, *, job: str, decl: str | None, log_access: bool, keep_ids: set[str] | None = None) -> tuple[list[R.SuccData], dict]:
    """Roll units of the SCREEN or HOLDOUT half (``which`` None = all non-embargo, census), after the era-overlap drop. Reads units, the per-unit price and
    trade files, and only ``unit_id, side_market_id, side_token_index`` from the guarded file. A HOLDOUT read is appended to ACCESS_LOG.jsonl."""
    rdir = Path(rdir)
    units = cb4_data._load_jsonl_gz(rdir / "units.jsonl.gz")
    era_ids = cb4_data._era_market_ids(rdir.parent / cb4_data.ERA_RUN_ID)
    kept, _dropped = cb4_data.drop_era_overlap(units, era_ids or set())
    sp = cb4_data.split_h7s(kept)
    ids = set(sp["screen"]) | (set(sp["holdout"]) if which in ("holdout", None) else set())
    if which == "screen":
        ids = set(sp["screen"])
    elif which == "holdout":
        ids = set(sp["holdout"])
    if keep_ids is not None:
        ids &= keep_ids
    if log_access:
        hb_files = ["units.jsonl.gz", "prices/*", "trades/*", "outcomes_guarded.csv.gz[unit_id,side_market_id,side_token_index]"]
        from . import h5_seal

        h5_seal.log_access(rdir, job, hb_files, declaration_sha=decl or "")
    side = pd.read_csv(rdir / cb4_data.OUTCOME_FILE, usecols=["unit_id", "side_market_id", "side_token_index"], dtype=str).set_index("unit_id")
    prog = {}
    pp = rdir / "progress.jsonl"
    if pp.exists():
        for line in pp.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "done":
                    prog[r["unit_id"]] = r
    out: list[R.SuccData] = []
    diag = {"units_in_half": len(ids), "missing_files": 0, "dropped_era_overlap": len(units) - len(kept)}
    raw: dict[str, pd.DataFrame] = {}
    for u in kept:
        uid = u["unit_id"]
        if uid not in ids:
            continue
        pr = prog.get(uid)
        if pr is None or uid not in side.index:
            diag["missing_files"] += 1
            continue
        k = int(side.loc[uid, "side_token_index"])
        pf, tf = rdir / "prices" / f"{pr['file']}.csv.gz", rdir / "trades" / f"{pr['file']}.csv.gz"
        if not pf.exists() or not tf.exists():
            diag["missing_files"] += 1
            continue
        ts, vals = hb.load_prices(pf)
        tr = hb.load_trades(tf)
        t_ts, t_buy, t_px, t_sz = R.map_trades_to_token(tr, k)
        raw[uid] = tr
        out.append(R.SuccData(unit_id=uid, series_id=u["series_id"], cadence=u["cadence"], category=u["modal_fee_category"], sports=bool(u["sports"]), t0=float(u["t0_epoch"]),
                              pred_end=float(u["pred_end_epoch"]), succ_created=float(u["succ_created_epoch"]), succ_end=float(u["succ_end_epoch"]), M=float(u["M_h"]) * HOUR,
                              V=float(u["V_end_h"]) * HOUR, ts=ts, vals=vals, tr_ts=t_ts, tr_buy=t_buy, tr_px=t_px, tr_size=t_sz, truncated=bool(pr.get("trades_truncated")),
                              oldest_ts=pr.get("trades_oldest_ts"), covers_t0=bool(pr.get("covers_t0")), covers_alt=bool(pr.get("covers_alt")), extra={"k": k, "pred_file": pr.get("pred_file")}))
    diag["raw_trades"] = raw
    return out, diag


# ---- C pipeline --------------------------------------------------------------------------------------------------------------------


def c_inputs(ctx: Ctx, window: str, root: Path | None = None) -> dict:
    """Dev or rep captures, C2 units at tau0, strata and the trades dir for that window (no outcomes)."""
    root = Path(root) if root else ctx.extract_root
    if window == "dev":
        t0, t1 = D.epoch(D.DATES["T4_dev_start"]), D.epoch(D.DATES["T4_dev_end"])
    else:
        t0, t1 = D.rep_window(ctx.rep_pin)
    caps, deps = load_captures(root, t0, t1)
    cw = pd.concat(caps, ignore_index=True) if caps else pd.DataFrame()
    c2, rep2 = R.c2_units_at_tau0(cw) if len(cw) else (pd.DataFrame(), {})
    strata, reps = R.assign_strata(caps, deps)
    return {"caps": caps, "cw": cw, "c2": c2, "rep_c2": rep2, "strata": strata, "rep_strata": reps, "window": [t0, t1], "tdir": ctx.out_root / "flip_trades" / window}


def c_run(ctx: Ctx, window: str, stage: int, decl: str, only: list[str] | None = None) -> dict:
    """C1 and C2 for one window: dev (Stage 1) or rep (Stage 2). Outcomes are read here, so the caller has passed ``check_outcome_allowed``."""
    inp = c_inputs(ctx, window)
    trades = load_trades_dir(inp["tdir"])
    strata = inp["strata"]
    if len(strata):
        strata = strata[~strata["fee_category"].map(R._is_weather)]
    s_prim = strata[(strata["stratum"] == "S") & ~strata["fee_category"].map(H1.is_sports)] if len(strata) else strata
    n_cls = strata[(strata["stratum"] == "N") & ~strata["fee_category"].map(H1.is_sports)] if len(strata) else strata
    c1, rep1 = R.c1_units(s_prim, trades)
    n_units, _ = R.c1_units(n_cls, trades)
    c1_buy, _ = R.c1_units(s_prim, trades, side="BUY")
    c2 = inp["c2"]
    c2p = c2[~c2["sports"]] if len(c2) else c2
    bids = R.c2_paper_bids(c2p, trades) if len(c2p) else pd.DataFrame(columns=[*c2.columns, "fill_state", "t_fill", "fill_price", "fill_size"])
    fm = bids[bids["fill_state"] == 1] if len(bids) else bids
    lim = _limiter(ctx, 4.0)
    outs = fetch_market_outcomes(lim, sorted(set(fm["market_id"]))) if len(fm) else {}
    mark = D.epoch(D.DATES["T4_dev_out"]) if window == "dev" else D.rep_out(ctx.rep_pin)
    last_bid = {}
    if len(inp["cw"]):
        lastrows = inp["cw"].sort_values("cap_start").groupby("market_id").tail(1)
        for _, r in lastrows.iterrows():
            last_bid[(r["market_id"], 0)] = float(r["best_bid"]) if np.isfinite(r["best_bid"]) else math.nan
            last_bid[(r["market_id"], 1)] = 1.0 - float(r["best_ask"]) if np.isfinite(r["best_ask"]) else math.nan
    filled = R.attach_c2_outcomes(bids, outs, last_bid, mark) if len(bids) else pd.DataFrame()
    g = R.g46_gate(c1, c2p, (inp["window"][1] - inp["window"][0]) / DAY)
    tests, placebo = {}, {}
    if not g["ok"] and stage == 1:
        for t in ("C1", "C2"):
            tests[t] = {"testable": False, "p": 1.0, "advance": False, "reason": ["G46 failed"], "effect": math.nan}
    else:
        if not only or "C1" in only:
            tests["C1"] = R.c1_test(c1, n_units, stage=stage, n_boot=ctx.n_boot, placebo_draws=ctx.placebo_draws, wb_added=rep1.get("baseline_unavailable_candidates", 0), c1_buy=c1_buy)
        if not only or "C2" in only:
            tests["C2"] = R.c2_test(filled, bids, stage=stage, n_boot=ctx.n_boot, placebo_draws=ctx.placebo_draws)
    for t, v in list(tests.items()):
        if v.get("placebo"):
            placebo[t] = v["placebo"]
    return {"tests": tests, "placebo": placebo, "descriptive": {"g46": g, "strata": inp["rep_strata"], "c2_population": inp["rep_c2"], "c1_report": rep1},
            "window": {"start": D.iso(inp["window"][0]), "end": D.iso(inp["window"][1])}}


# ---- commands ----------------------------------------------------------------------------------------------------------------------


def _wrap(name: str, a, fn, ctx: Ctx | None):
    ctx = ctx or Ctx()
    try:
        return fn(_args(name, a), ctx)
    except (Refusal, D.DeclarationError, D.RefusedRun, D.WindowError, D.TooEarly, cb4_data.Cb4Error, FileExistsError, cost_regimes.CostRegimeError) as exc:
        print(f"refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return REFUSED_EXIT


def cmd_flip_trades(a, ctx: Ctx | None = None) -> int:
    return _wrap("flip-trades", a, _flip_trades, ctx)


def _flip_trades(args, ctx: Ctx) -> int:
    _gate(ctx, args, counted=False)
    window = args.window or "dev"
    inp = c_inputs(ctx, window, Path(args.extract_root) if args.extract_root else None)
    ids: dict[str, str] = {}
    cw = inp["cw"]
    if len(cw):
        cid = cw.drop_duplicates("market_id").set_index("market_id")["condition_id"]
        want = set(inp["c2"]["market_id"]) if len(inp["c2"]) else set()
        if len(inp["strata"]):
            want |= set(inp["strata"][inp["strata"]["stratum"].isin(["S", "N", "E", "L"])]["market_id"])
        ids = {m: cid[m] for m in want if m in cid.index}
    res = fetch_flip_trades(ctx, ids, inp["tdir"], args.rps)
    _emit({"cb4": D.VERSION, "cmd": "flip-trades", "window": window, **res})
    return 0


def cmd_pilot(a, ctx: Ctx | None = None) -> int:
    return _wrap("pilot", a, _pilot, ctx)


def _read_hours(ctx: Ctx, hours: list[dict], events_meta: list[dict], seed: str, meter: M.IngressMeter, rates_for) -> tuple[list[dict], dict]:
    """Process hours in order until the cap: each hour reads the pmxt file for the sampled events, replays minutes, builds event-hour units and minutes."""
    from . import history_sources as hs

    fetch = ctx.pmxt_fetch or hs.httpx_range_fetch()
    size_fn = ctx.pmxt_size or hs.httpx_size
    units, minutes, done, missing, per_hour_bytes = [], [], 0, 0, []
    for h in hours:
        if meter.exceeded:
            break
        he = h["hour"].timestamp()
        evs = M.sample_events(he, events_meta, f"{seed}|events")
        if not evs:
            continue
        tokens = {m["token0"]: m["condition_id"] for e in evs for m in e["markets"]}
        before = meter.used
        try:
            raw = M.read_hour_events(h["hour"], tokens, fetch=fetch, size_fn=size_fn, meter=meter)
        except Exception:
            missing += 1
            continue
        done += 1
        per_hour_bytes.append(meter.used - before)
        mb = M.replay_minutes(raw, h["hour"])
        for e in evs:
            st = M.event_minute_states({m["token0"]: mb[m["token0"]] for m in e["markets"]}, rates_for(e), rho=D.N["rho"])
            u = M.event_hour_unit(st)
            for _, r in st.iterrows():
                minutes.append({"window": h["window"], "band": r["band"], "gap": r["gap"], "f0": r["f0"], "category": e["markets"][0].get("fee_category"), "event_id": e["event_id"]})
            if u is not None:
                units.append({**u, "event_id": e["event_id"], "day": h["hour"].date().isoformat(), "post": float(h["window"] == "post"), "window": h["window"], "hour": h["hour"].isoformat()})
    return units, {"hours_done": done, "hours_missing": missing, "bytes_per_hour": per_hour_bytes, "minutes": minutes, "bytes": meter.used}


def _events_meta(ctx: Ctx, start: str, end: str) -> tuple[list[dict], dict]:
    lim = _limiter(ctx, 4.0)
    return M.walk_negrisk_events(lim, D.epoch(start), D.epoch(end))


def _rates(e: dict) -> dict:
    return {m["token0"]: H1.fee_rate(m.get("fee_category")) for m in e["markets"]}


def _pilot(args, ctx: Ctx) -> int:
    _gate(ctx, args, counted=False)
    a0, b0 = D.DATES["W_pilot_N"]
    if args.__dict__.get("from") and (D.epoch(args.__dict__["from"]) < D.epoch(a0) or D.epoch(args.__dict__["to"]) > D.epoch(b0)):
        raise Refusal("the pilot reads only the declared pilot window 2026-07-12..2026-08-10")
    seed = args.seed or D.N["seed"] + "-pilot"
    cap = (args.ingress_cap_gb or D.N["ingress_cap_gb"]["pilot"]) * 1e9
    days = [(d, "pre" if i % 2 == 0 else "post") for i, d in enumerate(M._day_list(a0, b0))]
    hours = M.hour_order(seed, M.sample_hours(seed, days, 1.0))[: (args.hours or D.N["pilot_hours"])]
    meta, wrep = _events_meta(ctx, a0, b0)
    units, info = _read_hours(ctx, hours, meta, seed, M.IngressMeter(cap), _rates)
    g = float(np.mean(info["bytes_per_hour"])) if info["bytes_per_hour"] else math.nan
    u = pd.DataFrame(units)
    sd = float(u["I_mid"].std()) if len(u) > 1 else 0.0
    per_hour = len(u) / max(info["hours_done"], 1)
    power = M.pilot_power(g, sd, per_hour, 1.5) if np.isfinite(g) else {"H": 0, "testable": False}
    doc = {"label": LABEL, "job": "pilot", "descriptive": True, "n_event_hours": len(u), "eligible_events_per_hour": per_hour, "hours_done": info["hours_done"], "hours_missing": info["hours_missing"],
           "ingress_gb_per_hour": g / 1e9 if np.isfinite(g) else None, "base_rates": {k: float(u[k].mean()) for k in ("I_hi", "I_mid", "I_lo", "I_none")} if len(u) else {}, "sd_I_mid": sd,
           "power": power, "walk": wrep, "stop": bool(per_hour < D.N["stop_eligible_events_per_hour"] or info["hours_missing"] > D.N["stop_missing_hour_share"] * max(len(hours), 1))}
    p, sha = _write(ctx, "N_pilot/pilot.json", doc)
    _emit({"cb4": D.VERSION, "cmd": "pilot", "results": str(p), "sha256": sha, "H": power.get("H")})
    return 0


def _pins(ctx: Ctx) -> dict:
    return D.load_pins(ctx.spec)


def cmd_measure_N(a, ctx: Ctx | None = None) -> int:
    return _wrap("measure-N", a, _measure_n, ctx)


def _measure_n(args, ctx: Ctx) -> int:
    decl = _gate(ctx, args, counted=True)
    pins = _pins(ctx)
    H = int(pins["H"])
    if H < D.N["H_grid"][0]:
        doc = {**_header("N", decl), "tests": {t: {"testable": False, "p": 1.0, "estimate": math.nan, "reason": ["H_cap < 84: not testable"]} for t in ("N1", "N2")}}
        p, sha = _write(ctx, "N/results.json", doc)
        log_trials("N", doc["tests"], kind=D.KIND_MEASURE, role="exploratory_historical", dataset="pmxt_v2:N", results_path=str(p), sha=sha, decl=decl, cumulative=doc["cumulative_count_at_run"],
                   placebo=None, descriptive=None, trials_path=ctx.trials, count_source="creative_batch_4:M")
        _emit({"cb4": D.VERSION, "cmd": "measure-N", "status": "not testable (H_cap < 84)"})
        return 0
    seed = D.N["seed"]
    hours = M.hour_order(seed, M.sample_hours(seed, M.analysis_days(), H / 56.0))
    meta, wrep = _events_meta(ctx, D.DATES["W_pre_N"][0], D.DATES["W_post_N"][-1][1])
    cap = (args.ingress_cap_gb or D.N["ingress_cap_gb"]["measure"]) * 1e9
    if args.ingress_cap_gb and args.ingress_cap_gb > D.N["ingress_cap_gb"]["measure"]:
        raise Refusal("ingress cap above the declared 150 GB")
    units, info = _read_hours(ctx, hours, meta, seed, M.IngressMeter(cap), _rates)
    u = pd.DataFrame(units)
    res = M.n_tests(u, n_boot=ctx.n_boot) if len(u) else {"N1": {"testable": False, "p": 1.0}, "N2": {"testable": False, "p": 1.0}}
    pbo = M.in_time_placebos(u) if len(u) else {}
    pb = {t: M.pseudo_band_check(u, "PI" if t == "N1" else "PP5") if len(u) else {"ok": False} for t in ("N1", "N2")}
    mins = pd.DataFrame(info["minutes"])
    tests = {}
    for t in ("N1", "N2"):
        r = res[t]
        placebo_p = min((pbo[k][t].get("p", 1.0) for k in pbo), default=1.0)
        tests[t] = {**{k: r.get(k) for k in ("estimate", "ci95", "p", "n", "testable", "clusters")}, "placebo_p": placebo_p, "pseudo_band_ok": pb[t]["ok"], "pseudo_band": pb[t],
                    "top5_ok": bool(r.get("testable")), "label": cost_regimes.LABEL}
    doc = {**_header("N", decl, H=H, hours=len(hours), hours_done=info["hours_done"], hours_missing=info["hours_missing"], ingress_gb=info["bytes"] / 1e9, walk=wrep), "tests": tests,
           "descriptive": {"shares_and_distribution": M.band_shares_and_distribution(mins) if len(mins) else {}}, "band_map": M.band_map(mins) if len(mins) else None, "placebos": pbo}
    p, sha = _write(ctx, "N/results.json", doc)
    log_trials("N", tests, kind=D.KIND_MEASURE, role="exploratory_historical", dataset="pmxt_v2:N", results_path=str(p), sha=sha, decl=decl, cumulative=doc["cumulative_count_at_run"], placebo=None,
               descriptive={"N_band_map": {"post_minutes": (doc["band_map"] or {}).get("post_minutes")}}, trials_path=ctx.trials, count_source="creative_batch_4:M")
    _emit({"cb4": D.VERSION, "cmd": "measure-N", "results": str(p), "sha256": sha, "measure_N_complete": True})
    return 0


def cmd_measure_E(a, ctx: Ctx | None = None) -> int:
    return _wrap("measure-E", a, _measure_e, ctx)


def _measure_e(args, ctx: Ctx) -> int:
    decl = _gate(ctx, args, counted=True)
    rid = args.run_id or cb4_data.ERA_RUN_ID
    if rid != cb4_data.ERA_RUN_ID:
        raise Refusal("measure-E reads only h7_cb4_era")
    rdir = ctx.hist_root / rid
    cb4_data.verify_h7(ctx.hist_root, rid)
    from . import h5_seal

    h5_seal.log_access(rdir, "measure-E", ["sample.csv.gz", "prices/*", "trades/*"], declaration_sha=decl)
    panel, marks, diag = era_frames(rdir)
    if not len(panel) or not len(marks):
        tests = {t: {"testable": False, "p": 1.0, "estimate": math.nan, "reason": ["no rows"]} for t in ("E1", "E2")}
        doc = {**_header("E", decl), "tests": tests, "diag": {k: v for k, v in diag.items()}}
    else:
        pan, sc = M.scale_flow(panel)
        ctl = [c for c in pan.columns if c.startswith("c_")]
        e1 = M.two_cohort_did(pan, "d6h", slope=True, controls=ctl, n_boot=ctx.n_boot)
        e2 = M.two_cohort_did(marks, "AS", slope=False, n_boot=ctx.n_boot)
        pl1 = M.parallel_trends_placebo(pan.assign(event_id=pan["event_id"]), "d6h", slope=True, controls=ctl)
        pl2 = M.parallel_trends_placebo(marks, "AS", slope=False)
        tests = {}
        for t, r, pl in (("E1", e1, pl1), ("E2", e2, pl2)):
            tests[t] = {"estimate": r.get("estimate", math.nan), "ci95": (r.get("delta") or {}).get("ci95"), "p": r.get("p", 1.0), "testable": r.get("testable", False), "delta_S": r.get("delta_S"),
                        "delta_O": r.get("delta_O"), "sign_agree": bool(r.get("delta_S_O_sign_agree")), "placebo_p": pl.get("p", 1.0), "top5_ok": bool(r.get("testable")), "label": cost_regimes.LABEL}
        desc = {"scaling": sc, "rows_per_cell": e1.get("rows_per_cell"), "balanced_wallet": "not computed in this run (needs wallet-level trades per cell)",
                "E2_components": {"spread_mean": float(marks["spread"].mean()), "drift_mean": float(marks["drift"].mean())}}
        doc = {**_header("E", decl), "tests": tests, "descriptive": desc, "diag": {k: v for k, v in diag.items()}}
    p, sha = _write(ctx, "E/results.json", doc)
    log_trials("E", doc["tests"], kind=D.KIND_MEASURE, role="exploratory_historical", dataset=rid, results_path=str(p), sha=sha, decl=decl, cumulative=doc["cumulative_count_at_run"], placebo=None,
               descriptive=None, trials_path=ctx.trials, count_source="creative_batch_4:M")
    _emit({"cb4": D.VERSION, "cmd": "measure-E", "results": str(p), "sha256": sha})
    return 0


def cmd_measure_commit(a, ctx: Ctx | None = None) -> int:
    return _wrap("measure-commit", a, _measure_commit, ctx)


def _measure_commit(args, ctx: Ctx) -> int:
    _gate(ctx, args, counted=True)
    n, e = _jload(ctx.out_root / "N" / "results.json"), _jload(ctx.out_root / "E" / "results.json")
    if n is None or e is None:
        raise Refusal("measure-commit refuses unless both N and E results exist")
    res = {**n["tests"], **e["tests"]}
    out = M.commit_register(res, n.get("band_map"), ctx.register)
    _emit({"cb4": D.VERSION, "cmd": "measure-commit", **out})
    return 0


def cmd_fetch_outcomes(a, ctx: Ctx | None = None) -> int:
    return _wrap("fetch-outcomes", a, _fetch_outcomes, ctx)


def _fetch_outcomes(args, ctx: Ctx) -> int:
    decl = _gate(ctx, args, counted=True)
    if (args.family or "C").upper() != "C":
        raise Refusal("fetch-outcomes is for family C")
    window = args.window or "dev"
    D.check_outcome_allowed(window, ctx.now, ctx.rep_pin)
    inp = c_inputs(ctx, window)
    c2 = inp["c2"]
    trades = load_trades_dir(inp["tdir"])
    bids = R.c2_paper_bids(c2[~c2["sports"]], trades) if len(c2) else pd.DataFrame()
    ids = sorted(set(bids[bids["fill_state"] == 1]["market_id"])) if len(bids) else []
    outs = fetch_market_outcomes(_limiter(ctx, args.rps), ids)
    p, sha = _write(ctx, f"C_{window}/outcomes_guarded.json", {"label": LABEL, "declaration_sha256": decl, "window": window, "outcomes": outs})
    _emit({"cb4": D.VERSION, "cmd": "fetch-outcomes", "window": window, "n": len(outs), "results": str(p), "sha256": sha})
    return 0


def _series_dir(ctx: Ctx, run_id: str | None) -> Path:
    rid = run_id or cb4_data.SERIES_RUN_ID
    if rid != cb4_data.SERIES_RUN_ID:
        raise Refusal("family S reads only h7_cb4_series")
    return ctx.hist_root / rid


def _guard_s_register(ctx: Ctx) -> None:
    D.check_series_screen_allowed(ctx.register)


def cmd_screen(a, ctx: Ctx | None = None) -> int:
    return _wrap("screen", a, _screen, ctx)


def _screen(args, ctx: Ctx) -> int:
    decl = _gate(ctx, args, counted=True)
    fam = (args.family or "").upper()
    if fam == "C":
        D.check_outcome_allowed("dev", ctx.now, ctx.rep_pin)
        res = c_run(ctx, "dev", 1, decl or "")
        kind, role, dataset, rel = D.KIND_TEST, "exploratory_dev", "cb4_extract:closewin<T4_dev_end", "C_dev/results.json"
    elif fam == "S":
        _guard_s_register(ctx)
        rdir = _series_dir(ctx, args.run_id)
        cb4_data.verify_h7(ctx.hist_root, cb4_data.SERIES_RUN_ID)
        units, diag = load_series(rdir, "screen", job="screen_S", decl=decl, log_access=True)
        res = R.s_tests(units, stage=1, n_boot=ctx.n_boot, placebo_draws=ctx.placebo_draws)
        res["descriptive"]["load"] = {k: v for k, v in diag.items() if k != "raw_trades"}
        kind, role, dataset, rel = D.KIND_TEST, "exploratory_historical", cb4_data.SERIES_RUN_ID + ":SCREEN", "S_screen/results.json"
    else:
        raise Refusal("screen takes --family C or S")
    doc = {**_header(f"screen_{fam}", decl, family=fam, stage=1), **res}
    p, sha = _write(ctx, rel, doc)
    log_trials(fam, res["tests"], kind=kind, role=role, dataset=dataset, results_path=str(p), sha=sha, decl=decl, cumulative=doc["cumulative_count_at_run"], placebo=res.get("placebo"),
               descriptive={k: v for k, v in (res.get("descriptive") or {}).items() if isinstance(v, dict)}, trials_path=ctx.trials, count_source=f"creative_batch_4:{fam}")
    adv = sorted(k for k, v in res["tests"].items() if v.get("advance"))
    _emit({"cb4": D.VERSION, "cmd": "screen", "family": fam, "results": str(p), "sha256": sha, "advance": adv})
    return 0


def stage2_expected(c_dev: dict | None, s_screen: dict | None) -> list[str]:
    """Route tests reaching Stage 2: those that advanced at Stage 1 (k <= 4, fixed when Stage 1 ends). Both Stage-1 files must exist."""
    if c_dev is None or s_screen is None:
        raise Refusal("both Stage-1 route files (C_dev, S_screen) are required: a missing file would silently lower k")
    out = []
    for doc in (c_dev, s_screen):
        out += [k for k, v in doc.get("tests", {}).items() if v.get("advance")]
    return sorted(out)


def cmd_replicate(a, ctx: Ctx | None = None) -> int:
    return _wrap("replicate", a, _replicate, ctx)


def _replicate(args, ctx: Ctx) -> int:
    decl = _gate(ctx, args, counted=True)
    fam = (args.family or "").upper()
    c_dev, s_scr = _jload(ctx.out_root / "C_dev" / "results.json"), _jload(ctx.out_root / "S_screen" / "results.json")
    if fam == "C":
        D.check_outcome_allowed("rep", ctx.now, ctx.rep_pin)
        mine = sorted(k for k, v in (c_dev or {}).get("tests", {}).items() if v.get("advance"))
        rel = "C_rep/results.json"
    elif fam == "S":
        _guard_s_register(ctx)
        mine = sorted(k for k, v in (s_scr or {}).get("tests", {}).items() if v.get("advance"))
        rel = "S_holdout/results.json"
    else:
        raise Refusal("replicate takes --family C or S")
    if s_scr is None and c_dev is None:
        raise Refusal("no Stage-1 result exists")
    if not mine:
        doc = {**_header(f"replicate_{fam}", decl, family=fam, stage=2), "tests": {}, "note": "nothing advanced"}
        _write(ctx, rel, doc)
        _emit({"cb4": D.VERSION, "cmd": "replicate", "family": fam, "status": "nothing advanced"})
        return 0
    if fam == "C":
        res = c_run(ctx, "rep", 2, decl or "", only=mine)
        role, dataset = "prospective", "cb4_extract:closewin:rep"
    else:
        rdir = _series_dir(ctx, args.run_id)
        cb4_data.verify_h7(ctx.hist_root, cb4_data.SERIES_RUN_ID)
        units, diag = load_series(rdir, "holdout", job="holdout_S", decl=decl, log_access=True)
        res = R.s_tests(units, stage=2, n_boot=ctx.n_boot, placebo_draws=ctx.placebo_draws)
        res["tests"] = {k: v for k, v in res["tests"].items() if k in mine}
        res["descriptive"]["load"] = {k: v for k, v in diag.items() if k != "raw_trades"}
        role, dataset = "exploratory_dev", cb4_data.SERIES_RUN_ID + ":HOLDOUT"
    expected = stage2_expected(c_dev, s_scr) if (c_dev is not None and s_scr is not None) else mine
    k = max(len(expected), 1)
    for t in res["tests"].values():
        t["bonferroni_alpha"] = D.ALPHA_STAGE2 / k
        t["bonferroni_reject"] = bool(t.get("p", 1.0) < D.ALPHA_STAGE2 / k)
    doc = {**_header(f"replicate_{fam}", decl, family=fam, stage=2), **res, "expected_family": expected}
    p, sha = _write(ctx, rel, doc)
    log_trials(fam, res["tests"], kind=D.KIND_REP, role=role, dataset=dataset, results_path=str(p), sha=sha, decl=decl, cumulative=doc["cumulative_count_at_run"], placebo=res.get("placebo"),
               descriptive=None, trials_path=ctx.trials, count_source=f"creative_batch_4:{fam}")
    docs = [(n, d) for n, d in (("C_rep", _jload(ctx.out_root / "C_rep" / "results.json")), ("S_holdout", _jload(ctx.out_root / "S_holdout" / "results.json"))) if d and d.get("tests")]
    bh = CC.batch_holm(docs, expected, alpha=D.ALPHA_STAGE2) if c_dev is not None and s_scr is not None else None
    _emit({"cb4": D.VERSION, "cmd": "replicate", "family": fam, "results": str(p), "sha256": sha, "batch_holm_so_far": (bh or {}).get("replicated"), "k": k})
    return 0


# ---- census (counts only) ------------------------------------------------------------------------------------------------------------


def cmd_census(a, ctx: Ctx | None = None) -> int:
    return _wrap("census", a, _census, ctx)


def _census(args, ctx: Ctx) -> int:
    _gate(ctx, args, counted=False)
    fams = [f.strip().upper() for f in (args.family or "C,S,E,N").split(",") if f.strip()]
    out: dict = {"label": LABEL, "version": D.VERSION, "job": "census", "declaration_sha256": D.declaration_sha256(),
                 "note": "counts only; no outcome, mark-out, price change or test statistic is computed", "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    pins: dict = {}
    if "C" in fams:
        inp = c_inputs(ctx, "dev", Path(args.extract_root) if args.extract_root else None)
        trades = load_trades_dir(inp["tdir"])
        strata = inp["strata"]
        s_ = strata[strata["stratum"] == "S"] if len(strata) else strata
        n_ = strata[strata["stratum"] == "N"] if len(strata) else strata
        c1, r1 = R.c1_units(s_, trades) if len(s_) else (pd.DataFrame(), {})
        cn, _ = R.c1_units(n_, trades) if len(n_) else (pd.DataFrame(), {})
        cells = sorted(set(c1["cell"]) & set(cn["cell"])) if len(c1) and len(cn) else []
        c2 = inp["c2"]
        sa = {}
        if len(inp["cw"]) and trades:
            pr = pd.concat([t.df.assign(market_id=m) for m, t in trades.items() if len(t.df)], ignore_index=True) if any(len(t.df) for t in trades.values()) else pd.DataFrame()
            sa = R.side_audit_two_sided(pr, inp["cw"]) if len(pr) else {"ok": False, "note": "no prints"}
        uma = {}
        if len(inp["cw"]):
            for s in inp["cw"]["uma_set"]:
                for t in s:
                    uma[t] = uma.get(t, 0) + 1
        out["C"] = {"c2_units": int(len(c2)), "c2_population": inp["rep_c2"], "flip_strata": inp["rep_strata"], "c1_units": int(len(c1)), "c1_report": r1, "n_class_units": int(len(cn)),
                    "matched_cells": len(cells), "uma_statuses_observed": uma, "side_audit_two_sided": sa,
                    "g46": R.g46_gate(c1, c2, (inp["window"][1] - inp["window"][0]) / DAY), "clusters": {"events": int(c1["event_id"].nunique()) if len(c1) else 0, "iso_weeks": int(c1["week_e"].nunique()) if len(c1) else 0}}
        out["C"]["note_week_way"] = "the ISO-week cluster way needs >= 15 weeks under the literal small-G rule; the dev window holds 2-3 (see INTERPRETATIONS)"
    if "S" in fams:
        rdir = _series_dir(ctx, args.run_id)
        units, diag = load_series(rdir, "screen", job="census_S", decl=None, log_access=False)
        pred = {}
        for u in units:
            pf = rdir / "pred_prices" / f"{u.extra['pred_file']}.csv.gz"
            tf = rdir / "pred_trades" / f"{u.extra['pred_file']}.csv.gz"
            if pf.exists() and tf.exists():
                p = hb.load_prices(pf)
                pred[u.unit_id] = (p, hb.load_trades(tf)["ts"].to_numpy(float))
        pub = R.t0_publicity_check({k: v[1] for k, v in pred.items()}, {k: v[0] for k, v in pred.items()}, {u.unit_id: u.t0 for u in units if u.unit_id in pred})
        sa = R.side_audit_history(units, diag["raw_trades"], {u.unit_id: u.extra["k"] for u in units})
        df = R.s_values(units)
        out["S"] = {"load": {k: v for k, v in diag.items() if k != "raw_trades"}, "g50": R.g50_gate(units), "t0_publicity": pub, "h7_side_audit": sa, "drops": df["drops"],
                    "n_units_eligible": int(len(df["df"])), "p_a_available": int(np.isfinite(df["df"]["neg_v"]).sum()),
                    "series": int(df["df"]["series"].nunique()) if len(df["df"]) else 0, "series_x_week": int((df["df"]["series"] + "|" + df["df"]["week"]).nunique()) if len(df["df"]) else 0}
    if "E" in fams:
        rdir = ctx.hist_root / cb4_data.ERA_RUN_ID
        panel, marks, diag = era_frames(rdir)
        cells = {}
        if len(panel):
            for (g, p), d in panel.groupby(["group", "period"]):
                cells[f"{g}{p}"] = {"judgement_rows": int(len(d)), "markets": int(d["market_id"].nunique()), "events": int(d["event_id"].nunique()), "days": int((d["t"] // DAY).nunique())}
        out["E"] = {"cells": cells, "prints": int(len(marks)), "diag": diag}
    if "N" in fams:
        pil = _jload(ctx.out_root / "N_pilot" / "pilot.json")
        out["N"] = {"pilot": pil and {k: pil.get(k) for k in ("eligible_events_per_hour", "hours_done", "hours_missing", "ingress_gb_per_hour", "power", "stop")}, "venue_rho_check": "manual: docs.polymarket.com/trading/taker-rebates"}
        if pil:
            pins["H"] = int(pil["power"].get("H", 0))
    pins.setdefault("rho", D.N["rho"])
    pins.setdefault("uma_extra_statuses", [])
    out["pin_proposal"] = pins
    p, sha = _write(ctx, "census.json", out)
    provenance.append_trial({"status": "ok", "dataset": "cb4", "preset": "census", "label": LABEL, "kind": D.KIND_DESCRIPTIVE, "evidence_role": "exploratory_dev", "revision": D.VERSION,
                             "result_path": str(p), "results_sha256": sha, "summary": {"families": fams}}, ctx.trials)
    _emit({"cb4": D.VERSION, "cmd": "census", "families": fams, "results": str(p), "sha256": sha})
    return 0

