"""E010: live test of the CLEANED-set cross-venue model at 1h and 6h (research lab; read-only).

E010 rides on the E009 live stream (``cross_venue_live.Poller``): same pairs, same receipt-timed
quotes, same frozen feature definitions (``cross_venue_live.features``). It differs in the frozen
model (refitted once on the revision-r1 cleaned historical set C1, 316 pairs; Kalshi changes plus
the gap), the horizons (60 and 360 min, hourly origins) and its own append-only files
``predictions_e010.jsonl`` / ``outcomes_e010.jsonl`` with a separately hash-pinned spec
(``model_specs/cross_venue_live_e010_v1.json``). E009 files and statistics are untouched.

Dependence: E009 and E010 share pairs, quotes, features and time window, so their results are
correlated and must never be read as independent replications (EXPERIMENT_LEDGER E010).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import cross_venue as cv
from . import cross_venue_live as cvl

SPEC_PATH = cvl.SPEC_DIR / "cross_venue_live_e010_v1.json"
SPEC_SHA256 = "62b992c6af95ff9a508d8c3130c3ec3ae3333e582bf822d051ea72da46e4961c"
REGISTERED_UTC: str | None = "2026-10-13T02:00:00Z"  # E010 (EXPERIMENT_LEDGER.md)
END_UTC = "2026-11-03T00:00:00Z"
HORIZONS_MIN = (60, 360)
ORIGIN_GRID_S = 3600  # E010 predictions are written for origins with t % 3600 == 0 only
STEPS = {60: 6, 360: 36}
GAP_FEATURES = (*cvl.M0_FEATURES, "gap")
PRED_FILE = "predictions_e010.jsonl"
OUT_FILE = "outcomes_e010.jsonl"
QUOTE_KEEP_S = 360 * 60 + 3 * 3600


def evidence_role(t: float, registered_utc: str | None = REGISTERED_UTC) -> str:
    return cvl.evidence_role(t, registered_utc)


def load_spec(path: Path = SPEC_PATH, sha: str = SPEC_SHA256) -> dict:
    return cvl.load_spec(path, sha)


# --- freeze (once, historical C1) ---------------------------------------------------------------


def _coefs(b: np.ndarray, names: Sequence[str]) -> dict:
    return {"intercept": float(b[0]), **{n: float(v) for n, v in zip(names, b[1:], strict=True)}}


def freeze_spec(pairs: Sequence[cv.PairSeries], provenance: dict, hist_oos: dict) -> dict:
    """OLS (raw units, intercept) of the Polymarket mid change over 60/360 min on M0, M0 + gap and
    M0 + gap + Kalshi changes, all usable non-overlapping historical origins of the cleaned set."""
    models: dict[str, Any] = {}
    for hmin, h in STEPS.items():
        rows = [cvl.historical_design(ps, h) for ps in pairs]
        X = np.vstack([r[1] for r in rows if len(r[1])])
        y = np.concatenate([r[2] for r in rows if len(r[2])])
        b1 = cvl.ols_raw(X, y)
        bg = cvl.ols_raw(X[:, :5], y)
        b0 = cvl.ols_raw(X[:, :4], y)

        def sse(b, Z, y=y):
            e = y - (b[0] + Z @ b[1:])
            return float(e @ e)

        s0 = sse(b0, X[:, :4])
        models[str(hmin)] = {
            "m0": _coefs(b0, cvl.M0_FEATURES),
            "mgap": _coefs(bg, GAP_FEATURES),
            "m1": _coefs(b1, cvl.FEATURES),
            "n_obs": int(len(y)),
            "target_sd": float(y.std()),
            "in_sample_rel_mse_gain_m1": 1 - sse(b1, X) / s0,
            "in_sample_rel_mse_gain_mgap": 1 - sse(bg, X[:, :5]) / s0,
        }
    return {
        "spec_id": "cross_venue_live_e010_v1",
        "experiment": "E010",
        "frozen_utc": cvl.utc_iso(),
        "features": list(cvl.FEATURES),
        "feature_definitions": "identical to cross_venue_live_v1.json (cross_venue_live.features)",
        "models": models,
        "historical_walk_forward_C1": hist_oos,
        "fit": {
            "method": "unpenalised OLS with intercept, raw units, all usable non-overlapping "
            "historical origins per horizon (cross_venue._design stride); one fit, never refitted",
            "alignment": "cross_venue.align_pair with pm_lag_s=0 (as E009)",
            "pair_set": "revision r1 C1: the study analysis set minus results_r1.json audit.rule",
        },
        "provenance": provenance,
        "evidence_role_of_fit_data": cv.EVIDENCE_ROLE,
    }


# --- live writer --------------------------------------------------------------------------------


def make_prediction(pair: dict, t: float, q: dict, feats: dict, spec: dict) -> dict:
    y0, yg, y1 = {}, {}, {}
    for h in HORIZONS_MIN:
        m = spec["models"][str(h)]
        y0[str(h)] = cvl.predict(m["m0"], feats, cvl.M0_FEATURES)
        yg[str(h)] = cvl.predict(m["mgap"], feats, GAP_FEATURES)
        y1[str(h)] = cvl.predict(m["m1"], feats, cvl.FEATURES)
    cost = cvl.round_trip_cost(q["p_bid"], q["p_ask"], pair["fee_rate"])
    side = {str(h): (1 if y1[str(h)] > 0 else -1 if y1[str(h)] < 0 else 0) for h in HORIZONS_MIN}
    trade = {
        str(h): bool(side[str(h)] and math.isfinite(cost) and abs(y1[str(h)]) > cost)
        for h in HORIZONS_MIN
    }
    return {
        "id": f"{pair['pid']}|{int(t)}",
        "pid": pair["pid"],
        "ev": pair["p_event_id"],
        "t": int(t),
        "kr": q.get("k_recv"),
        "pr": q.get("p_recv"),
        "km": q["k_mid"],
        "pm": q["p_mid"],
        "pb": q["p_bid"],
        "pa": q["p_ask"],
        "f": feats,
        "y0": y0,
        "yg": yg,
        "y1": y1,
        "side": side,
        "cost": cost,
        "trade": trade,
        "fee": pair["fee_rate"],
        "role": evidence_role(t),
        "exp": "E010",
        "spec": spec["_sha256"][:16],
        "code": spec.get("_code", ""),
        "v": "cross-venue-live-e010-v1",
    }


class E010Writer:
    """Hooked into ``Poller.cycle`` (``on_cycle``) after the E009 lines are written. Appends E010
    predictions at hourly origins before any outcome quote exists, keeps a compact Polymarket
    quote window of ``QUOTE_KEEP_S``, and appends outcome lines at +60/+360 min."""

    def __init__(self, root: Path, spec: dict | None = None) -> None:
        self.root = Path(root)
        self.spec = spec or load_spec()
        self.quotes: dict[str, dict[int, tuple]] = {}
        self.pending: dict[tuple[str, int], dict] = {}
        self.done: set[tuple[str, int]] = set()
        self.totals = {"predictions": 0, "outcomes": 0}

    def _add_quote(self, q: dict) -> None:
        self.quotes.setdefault(q["pid"], {})[int(q["t"])] = (
            cvl._num(q.get("p_mid")),
            cvl._num(q.get("p_bid")),
            cvl._num(q.get("p_ask")),
            cvl._num(q.get("p_recv")),
        )

    def _add_pred(self, r: dict) -> None:
        for h in HORIZONS_MIN:
            if (r["id"], h) not in self.done:
                self.pending[(r["id"], h)] = r

    def recover(self, now: float) -> dict:
        lo = now - QUOTE_KEEP_S
        for o in cvl.read_jsonl(self.root / OUT_FILE):
            self.done.add((o["id"], int(o["h"])))
        n = 0
        for r in cvl.read_jsonl(self.root / PRED_FILE):
            if r["t"] >= now - 360 * 60 - 3600:
                self._add_pred(r)
                n += 1
        days = sorted(
            {datetime.fromtimestamp(x, UTC).strftime("%Y%m%d") for x in (lo, now - 43200, now)}
        )
        nq = 0
        for d in days:
            for f in (self.root / "quotes" / f"{d}.jsonl", self.root / "quotes" / f"{d}.jsonl.gz"):
                for q in cvl.read_jsonl(f):
                    if q["t"] >= lo:
                        self._add_quote(q)
                        nq += 1
        return {"predictions": n, "quotes": nq, "done": len(self.done)}

    def _find(self, pid: str, due: int):
        qs = self.quotes.get(pid, {})
        q = qs.get(due)
        if q is not None and math.isfinite(q[0]):
            return due, q
        best = None
        for t, v in qs.items():
            if abs(t - due) <= cvl.OUTCOME_TOL_S and math.isfinite(v[0]):
                if best is None or abs(t - due) < abs(best[0] - due):
                    best = (t, v)
        return best

    def on_cycle(self, t: float, ready: Sequence[tuple[dict, dict, dict]], quotes: Sequence[dict]):
        preds = []
        if int(t) % ORIGIN_GRID_S == 0:
            preds = [make_prediction(p, t, q, f, self.spec) for p, q, f in ready]
            cvl.append_jsonl(self.root / PRED_FILE, preds)  # before any outcome quote exists
            for r in preds:
                self._add_pred(r)
        for q in quotes:
            self._add_quote(q)
        rows = []
        for key, r in list(self.pending.items()):
            h = key[1]
            due = r["t"] + h * 60
            if t < due + cvl.OUTCOME_TOL_S:
                continue
            rows.append(outcome_row(r, h, self._find(r["pid"], due)))
            del self.pending[key]
            self.done.add(key)
        lo = t - QUOTE_KEEP_S
        for pid in list(self.quotes):
            qs = self.quotes[pid]
            for k in [k for k in qs if k < lo]:
                del qs[k]
            if not qs:
                del self.quotes[pid]
        cvl.append_jsonl(self.root / OUT_FILE, rows)
        self.totals["predictions"] += len(preds)
        self.totals["outcomes"] += len(rows)
        return len(preds), len(rows)


def outcome_row(r: dict, h: int, found) -> dict:
    base = {
        "id": r["id"],
        "pid": r["pid"],
        "ev": r["ev"],
        "h": h,
        "t0": r["t"],
        "due": r["t"] + h * 60,
        "role": r["role"],
        "exp": "E010",
        "written_utc": cvl.utc_iso(),
    }
    if found is None:
        return {**base, "status": "unavailable"}
    t_obs, (pm, pb, pa, precv) = found
    pnl = cvl.taker_pnl(
        r["side"][str(h)], cvl._num(r["pb"]), cvl._num(r["pa"]), pb, pa, cvl._num(r["fee"])
    )
    return {
        **base,
        "status": "evaluated",
        "t_obs": t_obs,
        "p_recv": precv,
        "pm_h": pm,
        "pb_h": pb,
        "pa_h": pa,
        "dp": pm - cvl._num(r["pm"]),
        "pnl_taker": pnl,
        "pnl_trade": pnl if r["trade"][str(h)] else None,
    }


# --- registered analysis (E010) -----------------------------------------------------------------


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def analyze(
    root: Path = cvl.ROOT,
    *,
    start_utc: str,
    end_utc: str = END_UTC,
    n_boot: int = 4000,
    seed: int = 20261013,
    role: str = "prospective_confirmation",
    now: float | None = None,
) -> dict:
    """E010 statistics: per horizon (60, 360) the relative MSE gain G of frozen M1 (and, secondary,
    of frozen M-gap) over frozen M0 on hourly origins in ``[start, end)``; event-clustered
    bootstrap, one-sided percentile-tail p, Holm over the two primaries. Same hygiene rules as
    E009 (dedup on (id, h), 60 s receipt-lag exclusion, missing-line counts)."""
    import time as _time

    lo = datetime.fromisoformat(start_utc.replace("Z", "+00:00")).timestamp()
    hi = datetime.fromisoformat(end_utc.replace("Z", "+00:00")).timestamp()
    now = _time.time() if now is None else now
    preds, late = {}, 0
    for r in cvl.read_jsonl(Path(root) / PRED_FILE):
        if not (lo <= r["t"] < hi and r["role"] == role and r["t"] % ORIGIN_GRID_S == 0):
            continue
        lags = [cvl._num(r.get(k)) - r["t"] for k in ("kr", "pr")]
        if not all(math.isfinite(x) and x <= cvl.MAX_RECV_LAG_S for x in lags):
            late += 1
            continue
        preds[r["id"]] = r
    outs: dict[int, list] = {h: [] for h in HORIZONS_MIN}
    unavail = {h: 0 for h in HORIZONS_MIN}
    seen: set = set()
    dups = 0
    for o in cvl.read_jsonl(Path(root) / OUT_FILE):
        h, key = int(o["h"]), (o["id"], int(o["h"]))
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        r = preds.get(o["id"])
        if r is None:
            continue
        if o["status"] != "evaluated" or not (
            cvl._num(o.get("p_recv")) - cvl._num(o.get("t_obs")) <= cvl.MAX_RECV_LAG_S
        ):
            unavail[h] += 1
            continue
        outs[h].append((r, o))
    missing = {
        h: sum(
            1
            for r in preds.values()
            if r["t"] + h * 60 + cvl.OUTCOME_TOL_S + 600 <= now and (r["id"], h) not in seen
        )
        for h in HORIZONS_MIN
    }
    res: dict[str, Any] = {
        "window": [start_utc, end_utc],
        "role": role,
        "origin_late": late,
        "duplicate_outcome_lines": dups,
        "unavailable": unavail,
        "missing_line": missing,
        "horizons": {},
    }

    def gain(s, i):
        return s[i] / s[0] if s[0] > 0 else cvl.NAN

    pv = {}
    for h in HORIZONS_MIN:
        per: dict[str, np.ndarray] = {}
        for r, o in outs[h]:
            y = o["dp"]
            e0 = y - r["y0"][str(h)]
            e1 = y - r["y1"][str(h)]
            eg = y - r["yg"][str(h)]
            v = np.array([e0 * e0, e0 * e0 - e1 * e1, e0 * e0 - eg * eg, 1.0])
            per[r["ev"]] = per.get(r["ev"], np.zeros(4)) + v
        if len(per) < 2:
            res["horizons"][str(h)] = {"status": "insufficient", "n_clusters": len(per)}
            continue
        S = np.vstack(list(per.values()))
        g1, b1 = cvl._boot(S, lambda s: gain(s, 1), n_boot, seed + h)
        gg, bg = cvl._boot(S, lambda s: gain(s, 2), n_boot, seed + h + 1)
        tot = S.sum(0)
        loo = [gain(tot - S[i], 1) for i in range(len(S))]
        p1 = float((np.sum(b1 <= 0) + 1) / (len(b1) + 1))
        pv[str(h)] = p1
        res["horizons"][str(h)] = {
            "status": "ok",
            "n_origins": int(tot[3]),
            "n_clusters": len(per),
            "rel_mse_gain_m1": g1,
            "ci_m1": [float(np.nanpercentile(b1, 2.5)), float(np.nanpercentile(b1, 97.5))],
            "p_one_sided_m1": p1,
            "rel_mse_gain_gap_only": gg,
            "ci_gap_only": [float(np.nanpercentile(bg, 2.5)), float(np.nanpercentile(bg, 97.5))],
            "largest_event_sse0_share": float(np.nanmax(S[:, 0] / tot[0])) if tot[0] > 0 else None,
            "leave_one_event_out_gain_range": [float(np.nanmin(loo)), float(np.nanmax(loo))],
        }
        res["horizons"][str(h)]["executable_pnl"] = cvl._pnl_stat(
            [(r["ev"], o.get("pnl_trade")) for r, o in outs[h]], n_boot, seed + h + 2
        )
    # Holm always over both registered primaries; a horizon without a test enters with p = 1.
    res["holm_m1"] = holm({str(h): pv.get(str(h), 1.0) for h in HORIZONS_MIN})
    return res


def spec_sha(path: Path = SPEC_PATH) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(obj) -> str:
    return json.dumps(obj, indent=1, default=float)
