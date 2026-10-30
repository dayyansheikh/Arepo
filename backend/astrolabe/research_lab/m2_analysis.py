# ruff: noqa: E501
"""M2-A analysis (``MEASUREMENT_M2_CH264.md`` sections 4-8, 10, 11, 9.5). Descriptive measurement; no test, no p-value.

Refuses before ``READOUT_UTC`` + 12 h, without ``out``, over an existing ``out`` and on any pin mismatch. Keeps only unit lines whose ``spec_sha`` and ``code_sha``
equal the pins and whose role is ``prospective_measurement``. Money units are dollars a share (the text's "c" in the coarse thresholds means cents).

One event bootstrap serves everything (7.1): B = 10,000 draws of events, ``default_rng(20261125)``, all of an event's units together; every component, split cell,
contrast and the hazard use the SAME draws (a cell restricted to its units; draws with no final-state unit in a cell are counted and left out of its percentiles).
"""

from __future__ import annotations

import gzip
import json
import math
import re
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.stats import beta

from . import boundary_map_ch240 as c240
from . import m2_j2 as j2
from . import m2_spec as sp

BANNED = re.compile(r"\b(supported|confirmed|significant|edge|profitable|route exists)\b|p-value", re.I)
NONFINAL_CLASSES = ("pending", "not_found", "unavailable_fetch", "no_readout_record")
UNCOVERED = ("unavailable_fetch", "no_readout_record")  # 8.4: covered = a definite answer; not_found is carried by theta_NF, the band and the backlog label
SPLITS = ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12")
EMPTY_FORMS = ("", "[]", "nan", "none")
TMAX = 360  # 30 d in 2 h slots


# --- loading -----------------------------------------------------------------------------------------------------------------------------

def parse_closed(v) -> float:
    if v in (None, ""):
        return math.nan
    s = str(v).strip().replace(" ", "T", 1)
    if re.search(r"[+-]\d\d$", s):
        s += ":00"
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return math.nan
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).timestamp()


def parse_iso(v) -> float:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp() if v else math.nan
    except ValueError:
        return math.nan


def load_units(store: Path, pins: dict) -> tuple[list[dict], dict]:
    units: list = []
    cnt: Counter = Counter()
    for p in sorted((Path(store) / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                if not line.strip():
                    continue
                u = json.loads(line)
                cnt["lines"] += 1
                if u.get("spec_sha") != pins["spec_sha"] or u.get("code_sha") != pins["code_sha"] or u.get("role") != sp.ROLE:
                    cnt["dropped_pin_or_role_mismatch"] += 1
                    continue
                units.append(u)
    return units, dict(cnt)


def load_nofav(store: Path) -> list[dict]:
    out: list = []
    for p in sorted((Path(store) / "nofav").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            out += [json.loads(x) for x in fh if x.strip()]
    return out


def load_readout(store: Path) -> dict:
    p = Path(store) / "readout" / "readout.jsonl.gz"
    out: dict = {}
    if p.exists():
        with gzip.open(p, "rt") as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    out[int(d["market_id"])] = d
    return out


def classify_units(units: list[dict], readout: dict, spec: dict) -> Counter:
    """Adds ``cls`` (8.1), ``Q``, ``final``, ``w_h``, ``cap``, ``n1``, ``n2``, ``n_loss``, ``n_win`` to each unit; returns wait-rule counts."""
    notes: Counter = Counter()
    rate, hpy = spec["capital_rate"], spec["hours_per_year"]
    for u in units:
        r = readout.get(u["market_id"])
        st = r["state"] if r else "no_readout_record"
        if r is None:
            notes["no_readout_record"] += 1
        Q = None
        if st == "resolved":
            fav = (r["y"] == 1) if u["side"] == "YES" else (r["y"] == 0)
            u["cls"], Q = ("resolved_favoured", 1.0) if fav else ("resolved_other", 0.0)
        elif st == "split_50_50":
            u["cls"], Q = "split_50_50", 0.5
        elif st in ("pending", "not_found", "unavailable_fetch", "no_readout_record"):
            u["cls"] = st
        else:
            u["cls"] = st  # unavailable_other_price_vector / unavailable_bad_prices: named sub-classes of `unavailable`
        u["Q"], u["final"] = Q, Q is not None
        u["uma"] = r.get("uma") if r else None
        u["sub_class"] = r.get("sub_class") if r else None
        fetched = parse_iso(r.get("fetched_utc")) if r else math.nan
        ct = parse_closed(r.get("closed_time")) if r else math.nan
        t_d = u["t_d"]
        u["closed_time_ts"] = ct
        u["fetched_ts"] = fetched
        u["w_upper_bound"] = False
        if math.isfinite(ct):
            w = 0.0 if ct < t_d else (ct - t_d) / 3600.0
            if ct < t_d:
                notes["wait_clock_anomaly"] += 1
        elif math.isfinite(fetched):
            w = max(0.0, (fetched - t_d) / 3600.0)
            u["w_upper_bound"] = True
            notes["wait_upper_bound"] += 1
        else:
            w = 0.0
            notes["wait_unknown_zero"] += 1
        u["w_h"] = w
        u["cap"] = u["ask_f"] * rate * w / hpy
        base = -u["ask_f"]
        u["n1"] = None if Q is None else Q + base - u["fee_l1"]
        u["n2"] = None if Q is None else Q + base - u["fee_l2"]
        u["n_loss"] = 0.0 + base - u["fee_l1"]  # Q = 0: the stake is lost (theta_NF, theta_W)
        u["n_win"] = 1.0 + base - u["fee_l1"]  # Q = 1 (theta_B)
        u["pi"] = None if Q is None else Q - u["mid_f"]
    return notes


# --- bootstrap engine --------------------------------------------------------------------------------------------------------------------

class Boot:
    """Event bootstrap of ratio statistics ``sum_e num_e / sum_e den_e``, event-level hazards and time-to-close curves on one shared draw stream (7.1)."""

    def __init__(self, units: list[dict], spec: dict) -> None:
        self.spec = spec
        self.units = units
        keys = sorted({u["event_id"] for u in units})
        self.E = len(keys)
        pos = {k: i for i, k in enumerate(keys)}
        self.ev = np.array([pos[u["event_id"]] for u in units], dtype=int)
        self.names: list = []
        self.num: list = []
        self.den: list = []
        self.diffs: list = []
        self.aj: dict = {}
        self.km: dict = {}
        self.res: dict = {}

    def ratio(self, name: str, vals: np.ndarray, mask: np.ndarray) -> None:
        v = np.where(mask, vals, 0.0)
        self.names.append(name)
        self.num.append(np.bincount(self.ev, weights=v, minlength=self.E))
        self.den.append(np.bincount(self.ev, weights=mask.astype(float), minlength=self.E))

    def ratio_event_weighted(self, name: str, vals: np.ndarray, mask: np.ndarray) -> None:
        """Event-weighted mean: each event with a masked unit weighs 1, split equally over its masked units."""
        v = np.where(mask, vals, 0.0)
        s = np.bincount(self.ev, weights=v, minlength=self.E)
        c = np.bincount(self.ev, weights=mask.astype(float), minlength=self.E)
        self.names.append(name)
        self.num.append(np.divide(s, c, out=np.zeros(self.E), where=c > 0))
        self.den.append((c > 0).astype(float))

    def diff(self, name: str, a: str, b: str) -> None:
        self.diffs.append((name, a, b))

    def add_aj(self, name: str, T: np.ndarray, typ: np.ndarray, idx: np.ndarray) -> None:
        """Right-censored competing risks for the units ``idx``: T in 2 h slots (>= 1), typ 0 censored / 1 P / 2 C. Per-event count matrices over t = 0..TMAX."""
        Tc = np.minimum(T, TMAX)
        typc = np.where(T > TMAX, 0, typ)
        evs = self.ev[idx]
        n_end = np.zeros((self.E, TMAX + 1))
        dP = np.zeros((self.E, TMAX + 1))
        dC = np.zeros((self.E, TMAX + 1))
        np.add.at(n_end, (evs, Tc), 1.0)
        np.add.at(dP, (evs, Tc), (typc == 1).astype(float))
        np.add.at(dC, (evs, Tc), (typc == 2).astype(float))
        self.aj[name] = (n_end, dP, dC)

    def add_km(self, name: str, idx: np.ndarray, hours: np.ndarray, event: np.ndarray) -> None:
        order = np.argsort(hours, kind="stable")
        self.km[name] = (idx[order], hours[order], event[order])

    # -- running ---------------------------------------------------------------------------------------------------------------------
    def _chunks(self):
        b = self.spec["bootstrap"]
        rng = np.random.default_rng(b["seed"])
        done = 0
        while done < b["B"]:
            m = min(b["chunk"], b["B"] - done)
            idx = rng.integers(0, self.E, size=(m, self.E))
            w = np.zeros((m, self.E))
            np.add.at(w, (np.arange(m)[:, None], idx), 1.0)
            yield w
            done += m

    @staticmethod
    def _aj(n_end, dP, dC, horizons):
        """Aalen-Johansen from count matrices (m x (TMAX+1)): (cif_P at horizons, cif_C at horizons, discrete P hazard 1..12, at-risk 1..12)."""
        at_risk = np.cumsum(n_end[:, ::-1], axis=1)[:, ::-1]
        m = n_end.shape[0]
        S = np.ones(m)
        cp = np.zeros(m)
        cc = np.zeros(m)
        out_p, out_c = {}, {}
        hz = np.full((m, 13), np.nan)
        for t in range(1, TMAX + 1):
            n = at_risk[:, t]
            ok = n > 0
            d1 = np.divide(dP[:, t], n, out=np.zeros(m), where=ok)
            d2 = np.divide(dC[:, t], n, out=np.zeros(m), where=ok)
            cp = cp + S * d1
            cc = cc + S * d2
            S = S * (1.0 - d1 - d2)
            if t <= 12:
                hz[:, t] = np.where(ok, d1, np.nan)
            if t in horizons.values():
                out_p[t], out_c[t] = cp.copy(), cc.copy()
        return out_p, out_c, hz, at_risk[:, 1:13]

    def _km(self, wmat: np.ndarray, spec_km):
        """Weighted Kaplan-Meier over units sorted by time; wmat is (m x E) event multiplicities. Returns (median hours, share closed by 7 d, by 30 d) arrays."""
        idx, hours, ev = spec_km
        m = wmat.shape[0]
        wu = wmat[:, self.ev[idx]]
        starts = np.concatenate([[0], np.nonzero(np.diff(hours) != 0)[0] + 1]) if len(hours) else np.array([], dtype=int)
        if not len(hours):
            nan = np.full(m, np.nan)
            return nan, nan, nan
        gt = hours[starts]
        d = np.add.reduceat(wu * ev[None, :], starts, axis=1)
        c = np.add.reduceat(wu, starts, axis=1)
        n = np.cumsum(c[:, ::-1], axis=1)[:, ::-1]
        factor = np.where(n > 0, 1.0 - d / np.where(n > 0, n, 1.0), 1.0)
        S = np.cumprod(factor, axis=1)
        below = S <= 0.5
        first = np.where(below.any(axis=1), below.argmax(axis=1), -1)
        med = np.where(first >= 0, gt[np.maximum(first, 0)], np.nan)

        def share(h):
            j = int(np.searchsorted(gt, h, side="right")) - 1
            return 1.0 - S[:, j] if j >= 0 else np.zeros(m)

        return med, share(168.0), share(720.0)

    def run(self) -> None:
        if not self.E:
            return
        S = len(self.names)
        NUM = np.array(self.num).T if S else np.zeros((self.E, 0))
        DEN = np.array(self.den).T if S else np.zeros((self.E, 0))
        h = self.spec["hazard"]["cif_slots"]
        vals_chunks: list = []
        aj_chunks: dict = {k: [] for k in self.aj}
        km_chunks: dict = {k: [] for k in self.km}
        for w in self._chunks():
            nb, db = w @ NUM, w @ DEN
            vals_chunks.append(np.divide(nb, db, out=np.full(nb.shape, np.nan), where=db > 0))
            for k, (ne, dp, dc) in self.aj.items():
                aj_chunks[k].append(self._aj(w @ ne, w @ dp, w @ dc, h))
            for k, spec_km in self.km.items():
                km_chunks[k].append(self._km(w, spec_km))
        draws = np.concatenate(vals_chunks, axis=0) if vals_chunks else np.zeros((0, S))
        ones = np.ones((1, self.E))
        pn, pd = ones @ NUM, ones @ DEN
        point = np.divide(pn, pd, out=np.full(pn.shape, np.nan), where=pd > 0)[0]
        self.draws = {n: draws[:, i] for i, n in enumerate(self.names)}
        self.point = {n: (float(point[i]) if math.isfinite(point[i]) else None) for i, n in enumerate(self.names)}
        for name, a, b in self.diffs:
            self.draws[name] = self.draws[a] - self.draws[b]
            pa, pb = self.point[a], self.point[b]
            self.point[name] = None if pa is None or pb is None else pa - pb
        self.aj_res = {}
        for k, (ne, dp, dc) in self.aj.items():
            p_pt, c_pt, hz_pt, ar_pt = self._aj(ones @ ne, ones @ dp, ones @ dc, h)
            parts = aj_chunks[k]
            res: dict = {"cif_P": {}, "cif_C": {}}
            for lab, t in h.items():
                dpv = np.concatenate([x[0][t] for x in parts]) if parts else np.array([])
                dcv = np.concatenate([x[1][t] for x in parts]) if parts else np.array([])
                res["cif_P"][lab] = {"est": float(p_pt[t][0]), **ci_dict(dpv, self.spec)}
                res["cif_C"][lab] = {"est": float(c_pt[t][0]), **ci_dict(dcv, self.spec)}
                self.draws[f"{k}|cifP|{lab}"] = dpv
                self.point[f"{k}|cifP|{lab}"] = float(p_pt[t][0])
            hzd = np.concatenate([x[2] for x in parts], axis=0) if parts else np.zeros((0, 13))
            res["hazard_P_per_slot"] = {str(t): {"est": None if not math.isfinite(hz_pt[0, t]) else float(hz_pt[0, t]), "at_risk": float(ar_pt[0, t - 1]), **ci_dict(hzd[:, t], self.spec)} for t in range(1, 13)}
            self.aj_res[k] = res
        self.km_res = {}
        for k, spec_km in self.km.items():
            pm, p7, p30 = self._km(ones, spec_km)
            parts = km_chunks[k]
            self.km_res[k] = {"units": int(len(spec_km[0])), "median_hours": {"est": _f(pm[0]), **ci_dict(np.concatenate([x[0] for x in parts]), self.spec)},
                              "closed_by_7d": {"est": _f(p7[0]), **ci_dict(np.concatenate([x[1] for x in parts]), self.spec)},
                              "closed_by_30d": {"est": _f(p30[0]), **ci_dict(np.concatenate([x[2] for x in parts]), self.spec)}}

    def ci(self, name: str) -> dict:
        return {"est": self.point.get(name), **ci_dict(self.draws[name], self.spec)}


def _f(x) -> float | None:
    return float(x) if x is not None and math.isfinite(x) else None


def ci_dict(draws: np.ndarray, spec: dict) -> dict:
    """Percentile 95% interval over the finite draws; draws that are undefined (no final-state unit / nobody at risk) are counted and left out."""
    d = np.asarray(draws, dtype=float)
    fin = d[np.isfinite(d)]
    a = (1 - spec["bootstrap"]["ci"]) / 2 * 100
    if not len(fin):
        return {"lo": None, "hi": None, "degenerate": None, "draws_used": 0, "draws_left_out": int(len(d))}
    lo, hi = np.percentile(fin, [a, 100 - a])
    return {"lo": float(lo), "hi": float(hi), "degenerate": bool(lo == hi), "draws_used": int(len(fin)), "draws_left_out": int(len(d) - len(fin))}


def day_block_boot(day_idx: np.ndarray, vals: np.ndarray, mask: np.ndarray, spec: dict) -> dict:
    """7.1: block bootstrap over the window's UTC days of k (same B and seed). It splits events whose units have k on different days (disclosed)."""
    days = np.unique(day_idx)
    if not len(days):
        return {}
    pos = {d: i for i, d in enumerate(days)}
    di = np.array([pos[d] for d in day_idx], dtype=int)
    s = np.bincount(di, weights=np.where(mask, vals, 0.0), minlength=len(days))
    n = np.bincount(di, weights=mask.astype(float), minlength=len(days))
    b = spec["bootstrap"]
    rng = np.random.default_rng(b["seed"])
    acc = []
    done = 0
    while done < b["B"]:
        m = min(b["chunk"], b["B"] - done)
        idx = rng.integers(0, len(days), size=(m, len(days)))
        den = n[idx].sum(axis=1)
        acc.append(np.divide(s[idx].sum(axis=1), den, out=np.full(m, np.nan), where=den > 0))
        done += m
    tot = n.sum()
    return {"est": float(s.sum() / tot) if tot else None, "days": int(len(days)), **ci_dict(np.concatenate(acc), spec)}


def cr1_se(units_vals: np.ndarray, ev: np.ndarray) -> dict:
    """CR1 event-clustered standard error of a mean: G/(G-1) * sum_g (sum_i (x_i - mean))^2 / N^2 (K = 1, so the (N-1)/(N-K) factor is 1)."""
    n = len(units_vals)
    if n < 2:
        return {"se": None, "clusters": int(len(set(ev.tolist())))}
    m = units_vals.mean()
    g = np.bincount(ev, weights=units_vals - m)
    G = int((np.bincount(ev) > 0).sum())
    if G < 2:
        return {"se": None, "clusters": G}
    return {"se": float(math.sqrt(G / (G - 1) * float((g ** 2).sum()) / n ** 2)), "clusters": G}


# --- 7.2 bound ---------------------------------------------------------------------------------------------------------------------------

def stratum_of(n: int) -> str:
    return "1" if n <= 1 else "2-3" if n <= 3 else "4-9" if n <= 9 else "10+"


def event_bound(basis: list[dict], spec: dict) -> dict:
    """7.2: basis = final-state plus not_found units (N_D, E_D); I_e = 1 if any basis unit of the event is split_50_50 or not_found; strata = basis units per
    event; one-sided Clopper-Pearson upper bound at 1 - alpha/S; B_U = sum_s N_s/N_D p_U,s; an empty stratum contributes 0."""
    strata = spec["bound"]["strata"]
    level = 1 - spec["bound"]["alpha"] / len(strata)
    by_ev: dict = defaultdict(list)
    for u in basis:
        by_ev[u["event_id"]].append(u)
    per = {s: {"events": 0, "units": 0, "flagged_events": 0, "p_upper": 0.0} for s in strata}
    for evu in by_ev.values():
        s = stratum_of(len(evu))
        per[s]["events"] += 1
        per[s]["units"] += len(evu)
        per[s]["flagged_events"] += int(any(u["cls"] in ("split_50_50", "not_found") for u in evu))
    nd = len(basis)
    bu = 0.0
    for d in per.values():
        if d["events"]:
            r, e = d["flagged_events"], d["events"]
            d["p_upper"] = 1.0 if r >= e else float(beta.ppf(level, r + 1, e - r))
            bu += d["units"] / nd * d["p_upper"]
    top = sorted(((k, len(v), int(any(u["cls"] in ("split_50_50", "not_found") for u in v))) for k, v in by_ev.items()), key=lambda t: (-t[1], str(t[0])))[:10]
    return {"B_U": bu if nd else None, "level": level, "N_D": nd, "E_D": len(by_ev), "strata": per,
            "ten_largest_events": [{"event": k, "basis_units": n, "I_e": i} for k, n, i in top],
            "assumption": "homogeneity within a stratum: an event's rate does not depend on its unit count; without it B_U bounds an event-weighted share"}


# --- follow-up (7.3) ---------------------------------------------------------------------------------------------------------------------

def followup_events(store: Path, units: list[dict], spec: dict) -> tuple[dict, Counter]:
    """Reads the follow-up files (first read, after the follow-up manifest is verified). Per unit: (T in slots, type 0 censored / 1 P / 2 C). P: a whole token
    proposed / disputed / resolved in the status string (same capture beats C); C: row absent or closed with no earlier P; censored at the last observed capture."""
    chain, _ = j2.load_statuses(store)
    slot_of_id = {d["id"]: d["slot"] for d in chain if d["kind"] == "processed"}
    ptok = set(spec["hazard"]["p_tokens"])
    k_slot = {u["unit_id"]: sp.slot_of(spec, parse_iso(u["k_start_utc"]))[0] for u in units}
    state = {uid: [k, k, 0, 0] for uid, k in k_slot.items()}  # [k_slot, last_obs_slot, type, T]
    notes: Counter = Counter()
    files = sorted(((slot_of_id.get(p.name.removesuffix(".jsonl.gz")), p) for p in (Path(store) / "followup").glob("*.jsonl.gz")), key=lambda t: (t[0] is None, t[0]))
    for slot, p in files:
        if slot is None:
            notes["followup_file_without_chain_status"] += 1
            continue
        with gzip.open(p, "rt") as fh:
            for line in fh:
                d = json.loads(line)
                st = state.get(d["unit_id"])
                if st is None or st[2] != 0 or slot <= st[0]:
                    continue
                if slot - st[1] > 1:
                    notes["interval_spans_missing"] += 1
                st[1] = slot
                present = bool(d.get("row_present"))
                raw = d.get("uma_raw")
                s = str(raw).strip().lower() if raw is not None else ""
                toks = set(re.split(r"[^a-z]+", s)) - {""}
                if present and toks & ptok:
                    st[2], st[3] = 1, slot - st[0]
                elif (not present) or c240._truthy(d.get("closed")):
                    st[2], st[3] = 2, slot - st[0]
                elif s not in EMPTY_FORMS:
                    notes["uma_other_followup"] += 1
    out = {}
    for uid, (k, last, typ, t) in state.items():
        out[uid] = (t, typ) if typ else (last - k, 0)
    return out, notes


# --- blocks ------------------------------------------------------------------------------------------------------------------------------

def mean(xs) -> float | None:
    xs = list(xs)
    return float(sum(xs) / len(xs)) if xs else None


def quantiles(xs) -> dict:
    v = np.array(sorted(x for x in xs if x is not None and math.isfinite(x)), dtype=float)
    if not len(v):
        return {"n": 0}
    p = np.percentile(v, [10, 25, 50, 75, 90])
    return {"n": int(len(v)), "p10": float(p[0]), "p25": float(p[1]), "median": float(p[2]), "p75": float(p[3]), "p90": float(p[4]), "max": float(v[-1])}


def cell_list(spec: dict, name: str) -> list[str]:
    if name == "S12":
        return [f"{a}|{b}" for a in spec["cells"]["S1"] for b in spec["cells"]["S2"]]
    return list(spec["cells"][name])


def build_stats(units: list[dict], spec: dict) -> Boot:
    """Registers every ratio statistic of 4 and 6 on the shared bootstrap (headline, components, secondaries, 69 cells, the two contrasts)."""
    bt = Boot(units, spec)
    N = len(units)
    nan = float("nan")
    arr = lambda k, none=nan: np.array([u[k] if u[k] is not None else none for u in units], dtype=float)  # noqa: E731
    fin = np.array([u["final"] for u in units])
    nfm = np.array([u["cls"] == "not_found" for u in units])
    Q, midf = arr("Q"), arr("mid_f")
    half, fee1, fee2, cap = arr("half_spread"), arr("fee_l1"), arr("fee_l2"), arr("cap")
    n1, n2, nloss, pi = arr("n1"), arr("n2"), arr("n_loss"), arr("pi")
    basis_nf = fin | nfm
    n_nf = np.where(fin, n1, nloss)

    def comps(prefix: str, mask: np.ndarray, full: bool) -> None:
        f = mask & fin
        bt.ratio(f"{prefix}theta", n1, f)
        bt.ratio(f"{prefix}theta_NF", n_nf, mask & basis_nf)
        bt.ratio(f"{prefix}q_eff", Q, f)
        bt.ratio(f"{prefix}mid_f", midf, f)
        bt.ratio(f"{prefix}h", half, f)
        bt.ratio(f"{prefix}fee_l1", fee1, f)
        bt.ratio(f"{prefix}pi", pi, f)
        if full:
            bt.ratio(f"{prefix}fee_l2", fee2, f)
            bt.ratio(f"{prefix}theta_L2", n2, f)
            bt.ratio(f"{prefix}theta_cap", n1 - cap, f)
            bt.ratio(f"{prefix}mean_cap", cap, f)
            bt.ratio(f"{prefix}p_win", (Q == 1.0).astype(float), f)
            bt.ratio(f"{prefix}p_loss", (Q == 0.0).astype(float), f)
            bt.ratio(f"{prefix}p_split", (Q == 0.5).astype(float), f)
            bt.ratio_event_weighted(f"{prefix}theta_E", n1, f)

    allm = np.ones(N, dtype=bool)
    comps("H|", allm, True)
    for name in SPLITS:
        cells = cell_list(spec, name)
        vals = np.array([u["cells"][name] for u in units])
        for c in cells:
            comps(f"{name}|{c}|", vals == c, False)
        for c in sorted(set(vals.tolist()) - set(cells)):
            comps(f"{name}|_unlisted:{c}|", vals == c, False)
    for lab, hi_, lo_ in (("D1", "S1|high|", "S1|low|"), ("D2", "S2|scheduled|", "S2|barrier|")):
        bt.diff(f"{lab}|theta", hi_ + "theta", lo_ + "theta")
        bt.diff(f"{lab}|pi", hi_ + "pi", lo_ + "pi")
    return bt


def cell_row(bt: Boot, units: list[dict], prefix: str, mask: np.ndarray, spec: dict) -> dict:
    cu = [u for u, m in zip(units, mask.tolist(), strict=True) if m]
    fin = [u for u in cu if u["final"]]
    fe = len({u["event_id"] for u in fin})
    return {"N": len(cu), "events": len({u["event_id"] for u in cu}), "final": len(fin), "final_events": fe,
            **{k: bt.ci(prefix + k) for k in ("q_eff", "mid_f", "h", "fee_l1", "theta", "theta_NF")},
            "nonfinal": dict(Counter(u["cls"] for u in cu if not u["final"])),
            "thin": bool(len(fin) < spec["thin"]["final_units"] or fe < spec["thin"]["events"])}


# --- 8.2 / cross-check / m1 overlap -------------------------------------------------------------------------------------------------------

def post_k_classes(units: list[dict]) -> dict:
    """8.2: read only at read-out; each unit stays in every estimand; counts and mean n_i (final units of the class) per class."""
    def blk(us):
        f = [u for u in us if u["final"]]
        return {"units": len(us), "final": len(f), "mean_n": mean(u["n1"] for u in f)}

    ch, c0, c1 = [], [], []
    for u in units:
        end_ro = parse_iso(u.get("readout_end_date"))
        if math.isfinite(end_ro) and abs(end_ro - u["end_date_k"]) > 1.0:
            ch.append(u)
        ct = u["closed_time_ts"]
        if math.isfinite(ct):
            if ct < u["t_d"]:
                c0.append(u)
            elif ct < u["t_d"] + 7200.0:
                c1.append(u)
    return {"end_date_changed_after_k": blk(ch), "closed_before_t_d": blk(c0), "closed_within_one_slot": blk(c1)}


def m1_overlap(units: list[dict], m1_store: Path | None) -> dict | str:
    """Section 2: at read-out only, the markets that are also M1 units (unit ids only; a pattern match on ``market_id``; no other field is parsed or kept)."""
    if m1_store is None or not (Path(m1_store) / "units").is_dir():
        return "unavailable"
    mid_re = re.compile(r'"market_id":\s*(\d+)')
    seen: set = set()
    missing = 0
    for p in sorted((Path(m1_store) / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                a = mid_re.search(line)
                if a:
                    seen.add(int(a.group(1)))
                elif line.strip():
                    missing += 1
    ov = [u for u in units if int(u["market_id"]) in seen]
    f = [u for u in ov if u["final"]]
    return {"count": len(ov), "m1_unit_markets_read": len(seen), "m1_lines_missing_the_key": missing, "mean_n": mean(u["n1"] for u in f), "pooled": False}


def engine_log(engine_root: Path | None) -> dict:
    out: dict = {}
    if engine_root is None:
        return out
    for p in sorted((Path(engine_root) / "logs").glob("resolutions-*.jsonl")):
        for line in p.read_text().splitlines():
            try:
                d = json.loads(line)
                out[int(d["market_id"])] = d
            except (ValueError, KeyError, TypeError):
                continue
    return out


def cross_check(units: list[dict], log: dict) -> dict:
    """8.4, read-out only: agreement of state and y with the engine's resolution log for units also present there. The pinned source governs."""
    agree = dis = 0
    lst = []
    for u in units:
        d = log.get(u["market_id"])
        if d is None:
            continue
        mine_y = None if u["cls"] not in ("resolved_favoured", "resolved_other") else (1 if (u["side"] == "YES") == (u["cls"] == "resolved_favoured") else 0)
        if d.get("state") == "resolved":
            ok = mine_y is not None and d.get("y") == mine_y
        elif u["final"]:
            ok = u["cls"] == d.get("state")
        else:
            ok = d.get("state") not in ("resolved", "split_50_50")
        agree += int(ok)
        if not ok:
            dis += 1
            lst.append({"market_id": u["market_id"], "m2": u["cls"], "engine_state": d.get("state"), "engine_y": d.get("y")})
    return {"units_in_log": agree + dis, "agree": agree, "disagree": dis, "disagreements": lst[:100], "note": "the pinned source governs"}


def counted_classes(store: Path) -> dict:
    """1.4: every counted class of J1 (status-file counts and notes, funnel, side statuses) added up into the output."""
    chain, side = j2.load_statuses(store)
    counts: Counter = Counter()
    funnel: Counter = Counter()
    for d in chain:
        if d["kind"] == "processed":
            counts.update(d.get("counts", {}))
            funnel.update(d.get("funnel", {}))
        else:
            counts["missing_capture_slots_chain"] += 1
    return {"j1_status_counts": dict(sorted(counts.items())), "funnel_k_time": dict(sorted(funnel.items())),
            **{k: len(v) for k, v in side.items()}}


# --- pins and manifests ------------------------------------------------------------------------------------------------------------------

def verify_manifest(store: Path, name: str, sha_pin: str | None) -> tuple[dict | None, list]:
    """(manifest or None, problems). A missing manifest, a hash differing from the pin and files differing from their listed hashes are void (11.2(b), 11.7)."""
    mp = Path(store) / name
    if not mp.exists():
        return None, [f"{name} missing"]
    problems = []
    if sp.sha256_file(mp) != sha_pin:
        problems.append(f"{name} hash differs from the pin")
    man = json.loads(mp.read_text())
    bad = [f for f, h in man["files"].items() if not (Path(store) / f).exists() or sp.sha256_file(Path(store) / f) != h]
    if bad:
        problems.append(f"files differ from {name}: {bad[:5]}")
    return man, problems


# --- the analysis ------------------------------------------------------------------------------------------------------------------------

def run_analysis(store: Path, pins: dict, out: Path | None, spec: dict = sp.SPEC, now: float | None = None, engine_root: Path | None = None,
                 paths: dict | None = None, design: Path | None = None, m1_store: Path | None = None) -> dict:
    now = time.time() if now is None else now
    if now < sp.ts(spec, "readout_utc") + spec["analysis_after_readout_s"]:
        raise sp.M2Refusal("analysis refuses before READOUT_UTC + 12 h")
    if out is None:
        raise sp.M2Refusal("analysis requires --out")
    out = Path(out)
    if out.exists():
        raise sp.M2Refusal("analysis refuses to overwrite --out")
    pin_rec = sp.check_pins(spec, paths, design)
    sp.check_run_pins(pins, spec)
    reg_commit = pins.get("registration_commit_utc")
    if not (reg_commit and math.isfinite(parse_iso(reg_commit))):
        raise sp.M2Refusal("analysis refuses: the pins file lacks a parseable registration_commit_utc (void condition 11.6 cannot be checked)")
    store = Path(store)
    void: list = []
    man, probs = verify_manifest(store, "manifest.json", pins.get("manifest_sha256"))
    void += [f"11.7 {p}" for p in probs]
    fman, fprobs = verify_manifest(store, "followup_manifest.json", pins.get("followup_manifest_sha256"))
    void += [f"11.2(b) {p}" for p in fprobs]
    res: dict = {"kind": "M2-A analysis (descriptive measurement; no test)", "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "role": sp.ROLE, "pin_check": pin_rec,
                 "manifest_sha256": pins.get("manifest_sha256"), "followup_manifest_sha256": pins.get("followup_manifest_sha256"), "void_reasons": void}
    if man is None:
        res["void"] = True
        _finish(res, out)
        return res
    audit = j2.audit_chain(store, spec)
    if not audit["ok"]:
        void.append(f"11.2(a) chain broken: {audit['breaks'][:5]}")
    units, lc = load_units(store, pins)
    readout = load_readout(store)
    ro_ends = {m: r.get("end_date") for m, r in readout.items()}
    wait_notes = classify_units(units, readout, spec)
    for u in units:
        u["readout_end_date"] = ro_ends.get(u["market_id"])
    nofav = load_nofav(store)
    nf_q = _nofav_block(nofav, readout)
    counted = counted_classes(store)
    classes = Counter(u["cls"] for u in units)
    n_units = len(units)
    final = [u for u in units if u["final"]]
    nf = len(final)
    nonfinal = sum(1 for u in units if not u["final"])
    events_all = {u["event_id"] for u in units}
    cov_units = sum(1 for u in units if u["cls"] not in UNCOVERED) / n_units if n_units else None
    by_ev: dict = defaultdict(list)
    for u in units:
        by_ev[u["event_id"]].append(u["cls"] not in UNCOVERED)
    cov_events = sum(1 for v in by_ev.values() if all(v)) / len(by_ev) if by_ev else None
    if n_units and (cov_units < spec["coverage_floor"] or cov_events < spec["coverage_floor"]):
        void.append(f"11.4 coverage below the floor: units {cov_units:.4f}, events {cov_events:.4f}")
    if lc.get("lines") and lc.get("dropped_pin_or_role_mismatch", 0) / lc["lines"] > spec["void_sha_mismatch_share"]:
        void.append("11.5 unit lines with a different spec_sha / code_sha / role exceed 1%")
    if sp.ts(spec, "registered_utc") < parse_iso(reg_commit) + 86400:
        void.append("11.6 the window started before the registration commit plus 24 h")
    res.update({"chain_audit": audit, "unit_lines": lc, "wait_notes": dict(wait_notes), "counted_classes": counted, "classes": dict(sorted(classes.items())),
                "eligible_units": n_units, "final_units": nf, "events": len(events_all), "no_favourite": nf_q,
                "coverage": {"units": cov_units, "events_all_units_covered": cov_events, "floor": spec["coverage_floor"], "final_share_of_units": nf / n_units if n_units else None},
                "uma_status_by_class": {c: dict(Counter(str(u["uma"]) for u in units if u["cls"] == c)) for c in sorted(classes)},
                "backlog": {"not_found_plus_split_share": (classes["not_found"] + classes["split_50_50"]) / n_units if n_units else None,
                            "label": "the population behaves as the venue's backlog, not a route" if n_units and (classes["not_found"] + classes["split_50_50"]) / n_units > spec["backlog_share"] else None},
                "post_k_classes": post_k_classes(units), "m1_overlap": m1_overlap(units, m1_store)})
    nums: dict = {}
    if nf:
        nums = _numbers(store, units, final, readout, man, fman, fprobs, spec)
        nums["coarse"] = _coarse(nums, nf, n_units, nonfinal, man, fman, spec)
        h = nums["headline_ci"]
        nums["ledger_line"] = _ledger_line(nums, h, nums["coarse"])
    elif not void:
        res["note"] = "no final-state units"
    log = engine_log(engine_root)
    if log:
        res["cross_check_engine_log"] = cross_check(units, log)
    res["void"] = bool(void)
    if void:
        res["not_a_measurement"] = nums
    else:
        res.update(nums)
    _finish(res, out)
    return res


def _finish(res: dict, out: Path) -> None:
    hit = BANNED.search(json.dumps(res, default=str))
    if hit:
        raise sp.M2Refusal(f"analysis refuses: banned wording {hit.group(0)!r} in the output")
    j2.write_once(out, json.dumps(res, sort_keys=True, default=str, indent=1).encode())


def _nofav_block(nofav: list[dict], readout: dict) -> dict:
    """E9: count, YES-resolved share and fetch coverage of the ``no_favourite`` class (printed separately; never in an estimand)."""
    ids = sorted({int(x["market_id"]) for x in nofav})
    recs = [readout.get(i) for i in ids]
    got = [r for r in recs if r is not None and r["state"] != "unavailable_fetch"]
    res = [r for r in recs if r is not None and r["state"] == "resolved"]
    yes = sum(1 for r in res if r["y"] == 1)
    return {"count": len(ids), "fetch_coverage": len(got) / len(ids) if ids else None, "resolved": len(res), "yes_resolved_share": yes / len(res) if res else None,
            "mean_Q_as_yes": yes / len(res) if res else None, "note": "never in an estimand (E9)"}


def _numbers(store: Path, units: list[dict], final: list[dict], readout: dict, man: dict, fman: dict | None, fprobs: list, spec: dict) -> dict:
    N = len(units)
    bt = build_stats(units, spec)
    ev = bt.ev
    # follow-up (7.3) and time to close (7.4) groups, registered before the shared draws run
    fu_notes: Counter = Counter()
    hazard_available = fman is not None and not fprobs
    s1 = np.array([u["cells"]["S1"] for u in units])
    s2 = np.array([u["cells"]["S2"] for u in units])
    groups = {"all": np.ones(N, dtype=bool)} | {f"S1={c}": s1 == c for c in spec["cells"]["S1"]} | {f"S2={c}": s2 == c for c in spec["cells"]["S2"]}
    fu_share = None
    if hazard_available:
        ev_map, fu_notes = followup_events(store, units, spec)
        T = np.array([ev_map[u["unit_id"]][0] for u in units])
        typ = np.array([ev_map[u["unit_id"]][1] for u in units])
        for g, m in groups.items():
            idx = np.nonzero(m & (T >= 1))[0]
            bt.add_aj(g, T[idx], typ[idx], idx)
        fin_idx = [i for i, u in enumerate(units) if u["final"]]
        fu_share = float(np.mean([typ[i] != 1 for i in fin_idx])) if fin_idx else None
    hours = np.array([u["w_h"] for u in units])
    # 7.4: the event is the close; a pending record that is not closed is censored at the fetch (w_h is then fetched - t_d, an upper bound)
    kmev = np.array([1.0 if (u["final"] or (u["cls"] == "pending" and u["sub_class"] == "closed_not_uma_resolved")) else 0.0 for u in units])
    in_km = np.array([u["final"] or u["cls"] == "pending" for u in units])
    for g, m in groups.items():
        idx = np.nonzero(m & in_km)[0]
        bt.add_km(f"KM|{g}", idx, hours[idx], kmev[idx])
    bt.run()
    # D1 proposal incidence difference (24 h) from the shared draws
    d1_inc = None
    if hazard_available and "S1=high|cifP|24h" in bt.draws and "S1=low|cifP|24h" in bt.draws:
        dd = bt.draws["S1=high|cifP|24h"] - bt.draws["S1=low|cifP|24h"]
        d1_inc = {"est": bt.point["S1=high|cifP|24h"] - bt.point["S1=low|cifP|24h"], **ci_dict(dd, spec)}
    H = lambda k: bt.ci("H|" + k)  # noqa: E731
    hp = {k: bt.point["H|" + k] for k in ("theta", "pi", "mid_f", "h", "fee_l1", "q_eff")}
    ident = abs(hp["theta"] - (hp["pi"] - hp["h"] - hp["fee_l1"]))
    fin_arr = np.array([u["final"] for u in units])
    n1 = np.array([u["n1"] if u["final"] else math.nan for u in units])
    day_idx = np.array([int((parse_iso(u["k_start_utc"]) - sp.ts(spec, "registered_utc")) // 86400) for u in units])
    basis = np.array([u["final"] or u["cls"] == "not_found" for u in units])
    n_nf = np.array([u["n1"] if u["final"] else u["n_loss"] for u in units])
    theta_ci, nf_ci = H("theta"), H("theta_NF")
    day_th = day_block_boot(day_idx, np.nan_to_num(n1), fin_arr, spec)
    day_nf = day_block_boot(day_idx, n_nf, basis, spec)
    width = (theta_ci["hi"] - theta_ci["lo"]) if theta_ci["lo"] is not None else None
    dw = (day_th["hi"] - day_th["lo"]) if day_th.get("lo") is not None else None
    wider = ("day_block_bootstrap" if (dw is not None and width is not None and dw > width) else "event_bootstrap")
    nonfin_kinds = [u for u in units if not u["final"]]
    th_w = mean([u["n1"] if u["final"] else u["n_loss"] for u in units])
    th_b = mean([u["n1"] if u["final"] else u["n_win"] for u in units])
    waits = [u["w_h"] for u in final]
    liq = {c: quantiles([u["liquidity"] for u in units if u["cells"]["S1"] == c]) for c in spec["cells"]["S1"]}
    t001 = [u for u in units if u["cells"]["S9"] == "0.001"]
    t01 = [u for u in units if u["cells"]["S9"] == "0.01"]
    ref: dict = {"tick_0.01": {"units": len(t01), "reference_lines": {"mid_floor_cents": 0.5, "spread_floor_cents": 1.0}, "note": "reference lines, never thresholds (5.4)"}}
    if t001:
        from . import costs

        med_h = float(np.median([u["half_spread"] for u in t001]))
        med_ask = float(np.median([u["ask_f"] for u in t001]))
        med_rate = float(np.median([u["rate_l2"] for u in t001]))
        med_exp = float(np.median([u["exponent"] for u in t001]))
        fee_at = costs.taker_fee_ps(med_ask, med_rate, med_exp)
        ref["tick_0.001"] = {"units": len(t001), "recorded_round_trip": med_h + fee_at, "median_h": med_h, "fee_l2_at_median_ask_f": fee_at, "one_tick": 0.001,
                             "note": "median h at k plus the L2 fee at the median ask_f (5.4); a reference line, never a threshold"}
    cell_blocks: dict = {}
    for name in SPLITS:
        vals = np.array([u["cells"][name] for u in units])
        cells = cell_list(spec, name)
        cell_blocks[name] = {c: cell_row(bt, units, f"{name}|{c}|", vals == c, spec) for c in cells}
        for c in sorted(set(vals.tolist()) - set(cells)):
            cell_blocks[name][f"_unlisted:{c}"] = cell_row(bt, units, f"{name}|_unlisted:{c}|", vals == c, spec)
    cr1 = {"theta": cr1_se(np.array([u["n1"] for u in final]), ev[fin_arr]),
           "theta_NF": cr1_se(n_nf[basis], ev[basis])}
    comps = {k: H(k) for k in ("q_eff", "p_win", "p_loss", "p_split", "mid_f", "h", "fee_l1", "fee_l2", "pi", "mean_cap")}
    out: dict = {
        "headline_ci": {"theta": theta_ci, "theta_NF": nf_ci, "theta_W": th_w, "theta_B": th_b},
        "band": {"theta_W": th_w, "theta_B": th_b, "note": "bounds, not estimates: every pending, not_found and unavailable unit at Q = 0 / Q = 1"},
        "headline_components": comps, "theta_L2": H("theta_L2"), "theta_cap": H("theta_cap"), "theta_E": H("theta_E"),
        "identity": {"theta_minus_pi_plus_h_plus_fee": ident, "tolerance": spec["identity_tol"], "ok": bool(ident <= spec["identity_tol"])},
        "cr1_event_clustered_se": cr1, "day_block_bootstrap": {"theta": day_th, "theta_NF": day_nf, "wider_interval_for_theta": wider},
        "event_bound": event_bound([u for u in units if u["final"] or u["cls"] == "not_found"], spec),
        "pending_unavailable_outside_bound_basis": sum(1 for u in nonfin_kinds if u["cls"] != "not_found"),
        "splits": cell_blocks,
        "contrasts": {"D1": {"theta": bt.ci("D1|theta"), "pi": bt.ci("D1|pi"), "proposal_incidence_24h": d1_inc},
                      "D2": {"theta": bt.ci("D2|theta"), "pi": bt.ci("D2|pi")},
                      "note": "descriptive differences with event-bootstrap intervals; never read as ambiguity or inattention (13)"},
        "wait_hours": quantiles(waits), "time_to_close": bt.km_res,
        "liquidity_proxy_not_capacity": liq, "capacity": "unavailable (no book is read for past-end markets, 5.3)", "rule25_reference_lines": ref,
        "bootstrap": spec["bootstrap"], "selection_width": {"splits": 12, "cells": 69, "contrasts": 2},
    }
    if hazard_available:
        out["proposal_hazard"] = {"groups": bt.aj_res, "final_units_without_P_ever_seen": fu_share, "followup_notes": dict(fu_notes), "followup_slot_coverage": fman["slot_coverage"],
                                  "label": "first capture showing a state, not the proposal time; right-censored at the read-out (7.3)"}
    else:
        out["proposal_hazard"] = "unavailable: the follow-up manifest is missing or differs from the pin (void 11.2(b))"
    return out


def _coarse(nums: dict, nf: int, n_units: int, nonfinal: int, man: dict, fman: dict | None, spec: dict) -> dict:
    co = spec["coarse"]
    th = nums["headline_ci"]["theta"]
    hw = (th["hi"] - th["lo"]) / 2 if th["lo"] is not None else None
    fcov = fman["slot_coverage"] if fman else None
    rules = {"1_final_units_below": nf < co["min_final_units"], "2_ci_half_width_above": hw is None or hw > co["max_ci_half_width_ps"],
             "3_nonfinal_share_above": (nonfinal / n_units) > co["max_nonfinal_share"], "4_window_slot_coverage_below": man["slot_coverage"] < co["min_slot_coverage"],
             "5_followup_slot_coverage_below": fcov is None or fcov < co["min_followup_slot_coverage"]}
    return {"rules_fired": rules, "coarse": any(v for k, v in rules.items() if not k.startswith("5_")), "rule_5_affects_the_hazard_line_only": rules["5_followup_slot_coverage_below"],
            "thresholds": co, "ci_half_width": hw, "nonfinal_share": nonfinal / n_units, "window_slot_coverage": man["slot_coverage"], "followup_slot_coverage": fcov}


def _ledger_line(nums: dict, h: dict, co: dict) -> str:
    th, tn = h["theta"], h["theta_NF"]
    fmt = lambda c: f"{c['est']:.6f} [{c['lo']:.6f}, {c['hi']:.6f}]"  # noqa: E731
    return (f"measured (prospective, k = 0; units seen at their first overdue 2 h capture, open, unproposed, two-sided and interior at k): theta = {fmt(th)}, "
            f"theta_NF = {fmt(tn)}, band [theta_W, theta_B] = [{h['theta_W']:.6f}, {h['theta_B']:.6f}], cost-model-v1, conservative fee, touch, size-unlimited, "
            f"capacity unavailable (no book is read for past-end markets){' [reported coarse]' if co['coarse'] else ''}.")
