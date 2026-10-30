# ruff: noqa: E501
"""CB4 measurements (docs/research_lab/CREATIVE_BATCH_4.md section 4.1): CH52 / CB4-N (taker-tier natural experiment on pmxt neg-risk books) and
CH53 / CB4-E (fee-rollout natural experiment on ``h7_cb4_era``), family M (single stage, two-sided Holm), and the cost-register commit.

Measurements have no money route and are never read as edge. They feed ``cost_regimes_v1.json`` only in one direction (rule R0). Pure functions;
the only I/O is the pmxt hour reader (``read_hour_events``), which takes injectable fetch/meter objects. Every constant comes from
``cb4_declaration`` (hashed).
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import cb1_history as H1
from . import cb4_data, cost_regimes
from . import cb4_declaration as D
from . import history_backfill as hb

HOUR, DAY = 3600.0, 86400.0
BANDS = ("hi", "mid", "lo", "none")

INTERPRETATIONS = (
    "Two-sided p for regressions: normal reference, max over event and calendar-day ways; a way with fewer than 30 clusters makes the test not testable (p = 1) rather than approximated.",
    "E origins use the HB1 origin_frame formulas re-implemented locally on the 2h grid inside [endDate - 72h, endDate); closedTime is never used (closed = False).",
    "f_net_6h is the sum of sign x size x YES-terms price over taker prints in [t - 6h, t), sign in YES terms (BUY of outcome 0 or SELL of outcome 1 = +1).",
    "Judgement rows: mid in (0.02, 0.98), at least one trade before t, d6h and f_net_6h defined.",
    "A false pseudo-band premise (mid band not the most negative) blocks adoption of N1/N2; the band-map is published regardless.",
    "Freeze-check fix 2: a placebo (CH52 in-time, CH53 parallel trends) that is not testable is 'unverified' and blocks adoption; it never counts as 'does not reject'.",
    "Freeze-check fix 2: the CH52 in-time placebo halves span 28 and 27 days, so their calendar-day way needs G >= 15 (the section 2.3 small-G testability minimum) "
    "instead of 30 and uses CR1 with the normal reference (no CR2/t(G-1) or wild-bootstrap enlargement): for a placebo, whose rejection blocks adoption, the "
    "smaller CR1 p is the conservative direction. The event way still needs 30 clusters.",
)


# ---- regression with clustered contrasts ---------------------------------------------------------------------------------------


def _codes(cl) -> tuple[np.ndarray, int]:
    c, u = pd.factorize(np.asarray(cl).astype(str))
    return c, len(u)


def ols_contrast(y, X, contrast, ways: dict[str, np.ndarray], *, n_boot: int = 0, seed: int = D.SEED_BOOT, min_units: int = D.MIN_UNITS,
                 min_clusters: int = D.MIN_CLUSTERS, robust: bool = False, min_clusters_by_way: dict[str, int] | None = None) -> dict:
    """OLS of y on X; the linear combination ``contrast' beta`` with CR1 sandwich SEs for each cluster way and the two-sided normal p = max over ways.
    Not testable (p = 1) with fewer than ``min_units`` rows or ``min_clusters`` clusters in any way. CI: percentile bootstrap resampling the first way.
    ``robust=True`` adds the section 2.6 checks per way: ``top5_dropped`` (refit without the 5 clusters of that way with the largest absolute contribution
    to the estimate) and ``cluster_equal_sign`` (the estimate with every cluster of that way weighted equally has the sign of the unweighted one)."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    c = np.asarray(contrast, float)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    ways = {k: np.asarray(v)[ok] for k, v in ways.items()}
    n, k = X.shape
    gs = {w: _codes(v)[1] for w, v in ways.items()}
    why = []
    if n < min_units:
        why.append(f"units {n} < {min_units}")
    need = {w: (min_clusters_by_way or {}).get(w, min_clusters) for w in gs}
    why += [f"{w} clusters {g} < {need[w]}" for w, g in gs.items() if g < need[w]]
    if why:
        return {"testable": False, "p": 1.0, "n": int(n), "reason": why, "clusters": gs, "estimate": math.nan}
    XtXi = np.linalg.pinv(X.T @ X)
    beta = XtXi @ (X.T @ y)
    est = float(c @ beta)
    res = y - X @ beta
    ses, ps = {}, {}
    for w, cl in ways.items():
        codes, g = _codes(cl)
        S = np.zeros((g, k))
        np.add.at(S, codes, X * res[:, None])
        adj = g / (g - 1.0) * (n - 1.0) / max(n - k, 1)
        var = float(c @ XtXi @ (S.T @ S) @ XtXi @ c) * adj
        se = math.sqrt(max(var, 0.0))
        ses[w] = se
        ps[w] = float(2.0 * norm.sf(abs(est) / se)) if se > 0 else 1.0
    out = {"testable": True, "estimate": est, "se_by_way": ses, "p_by_way": ps, "p": float(max(ps.values())), "n": int(n), "clusters": gs}
    if n_boot:
        codes, g = _codes(next(iter(ways.values())))
        A = np.zeros((g, k, k))
        b = np.zeros((g, k))
        for i in range(g):
            m = codes == i
            A[i] = X[m].T @ X[m]
            b[i] = X[m].T @ y[m]
        rng = np.random.default_rng(seed)
        bs = np.empty(n_boot)
        for i in range(n_boot):
            w = np.bincount(rng.integers(0, g, g), minlength=g).astype(float)
            bs[i] = float(c @ (np.linalg.pinv(np.tensordot(w, A, 1)) @ (w @ b)))
        out["ci95"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    if robust:
        top5, ceq = {}, {}
        for w, cl in ways.items():
            cs = np.asarray(cl).astype(str)
            contrib = pd.Series((X @ (XtXi @ c)) * y).groupby(cs).sum()  # sum over a cluster of (c' (X'X)^-1 x_i) y_i; sums to the estimate
            drop = set(contrib.abs().sort_values(ascending=False).index[:D.TOP_CLUSTERS_DROPPED])
            keep = ~np.isin(cs, list(drop))
            r = ols_contrast(y[keep], X[keep], c, {a: np.asarray(b)[keep] for a, b in ways.items()}, min_units=min_units, min_clusters=min_clusters,
                             min_clusters_by_way=min_clusters_by_way)
            top5[w] = {"testable": bool(r.get("testable")), "p": float(r.get("p", 1.0)), "estimate": float(r.get("estimate", math.nan))}
            size = pd.Series(cs).map(pd.Series(cs).value_counts()).to_numpy(float)
            wt = 1.0 / size
            Xw = X * wt[:, None]
            bw = np.linalg.pinv(X.T @ Xw) @ (Xw.T @ y)
            e_w = float(c @ bw)
            ceq[w] = bool(np.isfinite(e_w) and e_w != 0 and np.sign(e_w) == np.sign(est))
        out["top5_dropped"], out["cluster_equal_sign"] = top5, ceq
    return out


def did_design(post, treated) -> tuple[np.ndarray, np.ndarray]:
    """Stacked 2x2 DiD design [1, post, treated, post x treated]; the contrast picks the interaction."""
    post, tr = np.asarray(post, float), np.asarray(treated, float)
    return np.column_stack([np.ones(len(post)), post, tr, post * tr]), np.array([0.0, 0.0, 0.0, 1.0])


# ---- CH52: windows, hours, events -----------------------------------------------------------------------------------------------


def _day_list(a: str, b: str) -> list[datetime]:
    d, e = datetime.fromisoformat(a.replace("Z", "+00:00")), datetime.fromisoformat(b.replace("Z", "+00:00"))
    out = []
    while d < e:
        out.append(d)
        d += timedelta(days=1)
    return out


def window_of(day: datetime) -> str | None:
    """'pre' / 'post' for a UTC day under the declared windows (05-28 and 05-29, the pmxt gap and anything at or after 07-02 are excluded)."""
    t = day.replace(tzinfo=UTC).timestamp()
    ep = D.epoch
    if ep(D.DATES["W_pre_N"][0]) <= t < ep(D.DATES["W_pre_N"][1]):
        return "pre"
    for a, b in D.DATES["W_post_N"]:
        if ep(a) <= t < ep(b):
            return "post"
    return None


def analysis_days() -> list[tuple[datetime, str]]:
    out = []
    for a, b in ((D.DATES["W_pre_N"][0], D.DATES["W_pre_N"][1]), *D.DATES["W_post_N"]):
        out += [(d, window_of(d)) for d in _day_list(a, b) if window_of(d)]
    return out  # type: ignore[return-value]


def sample_hours(seed: str, days: list[tuple[datetime, str]], k: float) -> list[dict]:
    """For each day, ``k`` hours (k = 1.5 alternates 1 and 2): one hour drawn uniformly in each of n equal blocks of the UTC day by sha256(seed|day|block).
    Uses no book data."""
    out = []
    for i, (d, w) in enumerate(days):
        n = int(math.floor(k)) + (1 if (k % 1) and i % 2 == 0 else 0)
        n = max(n, 1)
        blk = 24.0 / n
        for b in range(n):
            lo = int(round(b * blk))
            hi = max(int(round((b + 1) * blk)), lo + 1)
            r = int(hashlib.sha256(f"{seed}|{d.date().isoformat()}|{b}".encode()).hexdigest(), 16)
            out.append({"hour": d.replace(hour=lo + r % (hi - lo), minute=0, second=0, microsecond=0, tzinfo=UTC), "window": w})
    return out


def hour_order(seed: str, hours: list[dict]) -> list[dict]:
    """Seeded random order alternating pre and post."""
    key = lambda h: hashlib.sha256(f"{seed}|order|{h['hour'].isoformat()}".encode()).hexdigest()  # noqa: E731
    pre = sorted((h for h in hours if h["window"] == "pre"), key=key)
    post = sorted((h for h in hours if h["window"] == "post"), key=key)
    out = []
    for i in range(max(len(pre), len(post))):
        if i < len(pre):
            out.append(pre[i])
        if i < len(post):
            out.append(post[i])
    return out


class IngressMeter:
    """Counts bytes read from the pmxt host and stops at the declared cap (150 GB measurement, 15 GB pilot)."""

    def __init__(self, cap_bytes: float):
        self.cap, self.used = float(cap_bytes), 0.0

    def add(self, n: float) -> None:
        self.used += float(n)

    @property
    def exceeded(self) -> bool:
        return self.used >= self.cap


def scheduled_open_over_hour(ev: dict, hour_epoch: float) -> bool:
    """Every member has ``createdAt <= h - 1h`` and scheduled ``endDate >= h + 1h``. No closedTime enters."""
    if not ev.get("markets"):
        return False
    return all(m.get("created_epoch") is not None and m["created_epoch"] <= hour_epoch - HOUR for m in ev["markets"]) and ev["end_epoch"] >= hour_epoch + HOUR


def sample_events(hour_epoch: float, events: list[dict], seed: str, max_events: int = D.N["events_per_hour"], max_members: int = D.N["members_per_hour"]) -> list[dict]:
    """Up to 15 events with at most 90 members in total, by seeded rank over ids and member counts only."""
    open_ = [e for e in events if scheduled_open_over_hour(e, hour_epoch)]
    open_.sort(key=lambda e: hashlib.sha256(f"{seed}|{int(hour_epoch)}|{e['event_id']}".encode()).hexdigest())
    out, tot = [], 0
    for e in open_:
        n = len(e["markets"])
        if len(out) >= max_events:
            break
        if tot + n > max_members:
            continue
        out.append(e)
        tot += n
    return out


def keep_negrisk_event(e: dict, rep: dict) -> bool:
    """Population rule: negRisk, not augmented, 2 to 10 members, every member with condition id, both tokens and outcomes[0] == "Yes" (YES-token check), no 'Other' placeholder, not weather."""
    ms = [m for m in (e.get("markets") or []) if isinstance(m, dict)]
    if not e.get("negRisk"):
        rep["not_negrisk"] = rep.get("not_negrisk", 0) + 1
        return False
    if e.get("negRiskAugmented"):
        rep["augmented"] = rep.get("augmented", 0) + 1
        return False
    if not (D.N["members"][0] <= len(ms) <= D.N["members"][1]):
        rep["member_count"] = rep.get("member_count", 0) + 1
        return False
    if any(m.get("negRiskOther") or str(m.get("groupItemTitle") or "").strip().lower() == "other" for m in ms):
        rep["other_placeholder"] = rep.get("other_placeholder", 0) + 1
        return False
    for m in ms:
        toks = cb4_data._json_list(m.get("clobTokenIds"))
        if not m.get("conditionId") or len(toks) < 2:
            rep["missing_ids"] = rep.get("missing_ids", 0) + 1
            return False
        # the YES token is clobTokenIds[0] (slim_event ``token0``): that is only right when outcomes[0] is "Yes"; any other label, or no label, is rejected and counted
        outs = cb4_data._json_list(m.get("outcomes"))
        if not outs or str(outs[0]).strip().lower() != "yes":
            rep["yes_token_unverified"] = rep.get("yes_token_unverified", 0) + 1
            return False
    if cb4_data.is_weather_text(e.get("title"), *[m.get("question") for m in ms]) or any(cb4_data.is_weather_market(hb.fee_category(m.get("feeType"))) for m in ms):
        rep["weather"] = rep.get("weather", 0) + 1
        return False
    return True


def walk_negrisk_events(lim, start: float, end: float, *, modes=(False, True), min_width_s: int = 3600, base_days: int = 7) -> tuple[list[dict], dict]:
    """Gamma /events over end-date windows (closed false then true); a capped window is halved to ``min_width_s`` and then dropped and counted; a failed
    request is counted as failed (never as capped). Returns slim neg-risk events (ids, tokens, scheduled create/end times; no outcome fields)."""
    rep: dict = {"requests": 0, "splits": 0, "dropped_capped": 0, "failed": 0, "events_seen": 0}
    out: dict[str, dict] = {}
    for mode in modes:
        t = start
        while t < end:
            stack = [(t, min(t + base_days * DAY, end))]
            t += base_days * DAY
            while stack:
                x, y = stack.pop(0)
                rows, off, capped, failed = [], 0, False, False
                while True:
                    try:
                        st, data = lim.get(cb4_data.GAMMA_EVENTS, {"closed": "true" if mode else "false", "end_date_min": cb4_data._iso(x), "end_date_max": cb4_data._iso(y), "limit": 100, "offset": off})
                    except RuntimeError:
                        st, data = 599, None
                    rep["requests"] += 1
                    if st != 200 or not isinstance(data, list):
                        failed = True
                        break
                    rows += data
                    if len(data) < 100:
                        break
                    off += 100
                    if off >= hb.GAMMA_OFFSET_CAP:
                        capped = True
                        break
                if failed:
                    rep["failed"] += 1
                    continue
                if capped and (y - x) > min_width_s:
                    mid = x + math.floor((y - x) / 2)
                    stack[:0] = [(x, mid), (mid, y)]
                    rep["splits"] += 1
                    continue
                if capped:
                    rep["dropped_capped"] += 1
                    continue
                for e in rows:
                    rep["events_seen"] += 1
                    if not keep_negrisk_event(e, rep):
                        continue
                    sg = cb4_data.slim_event(e, bool(mode))
                    if sg is not None and sg[0]["created_epoch"] is not None:
                        out.setdefault(sg[0]["event_id"], sg[0])
    rep["kept"] = len(out)
    return list(out.values()), rep


# ---- CH52: pmxt hour reading and minute replay -------------------------------------------------------------------------------------


READ_BATCH_ROWS = 4096  # rows per streamed record batch in read_hour_events (memory bound; no effect on the returned events)


def read_hour_events(hour: datetime, tokens: dict[str, str], *, fetch, size_fn, meter: IngressMeter | None = None, lookback_hours: int = 1) -> dict[str, list[dict]]:
    """Book events of ``tokens`` (token -> condition id) in the pmxt hour file containing ``hour`` and, for tokens with no ``book`` event yet, up to
    ``lookback_hours`` earlier files (the minute-0 lookback). Row groups are pruned on the ``market`` statistics. The bytes fetched are added to ``meter``."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    from . import history_sources as hs

    cols = ["timestamp_received", "timestamp", "market", "event_type", "asset_id", "bids", "asks", "price", "size", "side", "new_tick_size"]
    end_ts = pa.scalar(int((hour + timedelta(hours=1)).timestamp() * 1000), pa.timestamp("ms", "UTC"))
    ev: dict[str, list[dict]] = {t: [] for t in tokens}
    has_book: set[str] = set()
    for back in range(lookback_hours + 1):
        pending = [t for t in tokens if t not in has_book]
        if not pending:
            break
        h = hour - timedelta(hours=back)
        url = hs.pmxt_url(h)
        try:
            rf = hs.RangeFile(url, size_fn(url), fetch)
        except FileNotFoundError:
            continue
        pf = pq.ParquetFile(rf)
        midx = pf.schema_arrow.get_field_index("market")
        want = {tokens[t].lower() for t in pending}
        value_set = pa.array(sorted(pending))
        for rg in range(pf.num_row_groups):
            ms = pf.metadata.row_group(rg).column(midx).statistics
            if ms is not None and ms.has_min_max and not any(hs._b(ms.min) <= c <= hs._b(ms.max) for c in want):
                continue
            # Stream the row group in small record batches (a row group's bids/asks are large) and materialise only matching rows.
            for batch in pf.iter_batches(batch_size=READ_BATCH_ROWS, row_groups=[rg], columns=cols, use_threads=False):
                keep = pc.and_(pc.is_in(batch.column("asset_id"), value_set=value_set), pc.less_equal(batch.column("timestamp_received"), end_ts))
                if not pc.any(keep).as_py():
                    continue
                for r in batch.filter(keep).to_pylist():
                    e = {**r, "receipt_ms": int(r["timestamp_received"].timestamp() * 1000), "venue_ms": int(r["timestamp"].timestamp() * 1000)}
                    ev[r["asset_id"]].append(e)
                    if r["event_type"] == "book":
                        has_book.add(r["asset_id"])
                del keep, batch
        if meter is not None:
            meter.add(rf.bytes_fetched)
    for t in ev:
        ev[t].sort(key=lambda e: (e["venue_ms"], e["receipt_ms"]))
    return ev


class _Book:
    """Incremental book from time-ordered events (the ``history_sources.rebuild_book`` rule: last ``book`` then ``price_change`` with absolute level sizes)."""

    def __init__(self) -> None:
        self.bids: dict[float, float] | None = None
        self.asks: dict[float, float] = {}
        self.last_receipt: int | None = None

    def apply(self, e: dict) -> None:
        et = e["event_type"]
        if et == "book":
            self.bids = {float(p): float(s) for p, s in (json.loads(e["bids"]) if isinstance(e.get("bids"), str) and e.get("bids") else [])}
            self.asks = {float(p): float(s) for p, s in (json.loads(e["asks"]) if isinstance(e.get("asks"), str) and e.get("asks") else [])}
        elif et == "price_change" and self.bids is not None and e.get("price") is not None:
            side = self.bids if str(e.get("side")).upper() == "BUY" else self.asks
            p, s = float(e["price"]), float(e["size"])
            if s <= 0:
                side.pop(p, None)
            else:
                side[p] = s
        else:
            return
        self.last_receipt = e["receipt_ms"]

    def snapshot(self) -> dict | None:
        if self.bids is None:
            return None
        bids = sorted(self.bids.items(), reverse=True)
        asks = sorted(self.asks.items())
        return {"bid": bids[0][0] if bids else math.nan, "ask": asks[0][0] if asks else math.nan, "asks": asks, "bids": bids, "last_receipt_ms": self.last_receipt}


def replay_minutes(events: dict[str, list[dict]], hour: datetime, *, stale_min: int = D.N["stale_min"]) -> dict[str, list[dict | None]]:
    """Per token, the book at the end of each minute m = 0..59 of ``hour`` using events with BOTH clocks <= that time (loader rule). A state carries
    ``crossed`` and ``stale`` (last applied event more than ``stale_min`` minutes old by the receipt clock); ``None`` = no book basis."""
    out: dict[str, list[dict | None]] = {}
    h0 = int(hour.timestamp() * 1000)
    for tok, evs in events.items():
        bk, i, rows = _Book(), 0, []
        for m in range(60):
            t_end = h0 + (m + 1) * 60_000
            while i < len(evs) and evs[i]["venue_ms"] <= t_end and evs[i]["receipt_ms"] <= t_end:
                bk.apply(evs[i])
                i += 1
            s = bk.snapshot()
            if s is not None:
                s["crossed"] = bool(np.isfinite(s["bid"]) and np.isfinite(s["ask"]) and s["bid"] >= s["ask"])
                s["stale"] = bool(s["last_receipt_ms"] is None or t_end - s["last_receipt_ms"] > stale_min * 60_000)
            rows.append(s)
        out[tok] = rows
    return out


def vwap_ask(asks: list[tuple[float, float]], shares: float = D.N["vwap_shares"]) -> float:
    """VWAP of buying ``shares`` from the ask ladder (``economics.sweep_fill`` rule); NaN if the side holds fewer than ``shares``."""
    need, cash = shares, 0.0
    for p, s in asks:
        take = min(need, s)
        cash += take * p
        need -= take
        if need <= 1e-12:
            return cash / shares
    return math.nan


def classify(gap: float, f0: float, rho: float = D.N["rho"], mu: float = D.N["margin"]) -> str:
    """hi: G - F0 > mu; mid: G - (1-rho) F0 > mu and G - F0 <= mu; lo: G > mu and G - (1-rho) F0 <= mu; else none."""
    if gap - f0 > mu:
        return "hi"
    if gap - (1.0 - rho) * f0 > mu:
        return "mid"
    if gap > mu:
        return "lo"
    return "none"


def event_minute_states(minute_books: dict[str, list[dict | None]], rates: dict[str, float], *, rho: float = D.N["rho"], mu: float = D.N["margin"],
                        shares: float = D.N["vwap_shares"]) -> pd.DataFrame:
    """Per minute of one event: eligibility (every member two-sided, not crossed, not stale, >= 10 shares on the ask side), ``G = 1 - sum a_j``,
    ``F0 = sum r_j a_j (1 - a_j)``, band at ``rho``, ``x = G - F0 - mu`` and the equal-width pseudo-band index (width rho F0)."""
    toks = list(minute_books)
    rows = []
    for m in range(60):
        a, ok, why = [], True, ""
        for t in toks:
            s = minute_books[t][m]
            if s is None or not np.isfinite(s["bid"]) or not np.isfinite(s["ask"]):
                ok, why = False, "one_sided_or_no_book"
                break
            if s["crossed"]:
                ok, why = False, "crossed"
                break
            if s["stale"]:
                ok, why = False, "stale"
                break
            v = vwap_ask(s["asks"], shares)
            if not np.isfinite(v):
                ok, why = False, "thin_ask"
                break
            a.append(v)
        if not ok:
            rows.append({"minute": m, "eligible": False, "why": why, "gap": math.nan, "f0": math.nan, "band": None, "x": math.nan, "pseudo": None})
            continue
        gap = 1.0 - sum(a)
        f0 = sum(rates[t] * x * (1.0 - x) for t, x in zip(toks, a, strict=True))
        x = gap - f0 - mu
        w = rho * f0
        pk = int(math.floor(x / w)) if w > 0 else None
        rows.append({"minute": m, "eligible": True, "why": "", "gap": gap, "f0": f0, "band": classify(gap, f0, rho, mu), "x": x, "pseudo": pk if pk is not None and -3 <= pk <= 1 else None})
    return pd.DataFrame(rows)


def onsets_p5(state: np.ndarray, eligible: np.ndarray, persist: int = D.N["persist_min"], max_minute: int = D.N["onset_max_minute"]) -> dict:
    """Onsets: minute m <= 54 where the state is false at m-1 and true at m, both eligible. ``P5`` = 1/0 for the state at m+5 (eligible); an
    ineligible m+5 is dropped and counted."""
    p5, dropped, n = [], 0, 0
    for m in range(1, min(max_minute, len(state) - 1) + 1):
        if eligible[m] and eligible[m - 1] and state[m] and not state[m - 1]:
            n += 1
            if m + persist < len(state) and eligible[m + persist]:
                p5.append(float(state[m + persist]))
            else:
                dropped += 1
    return {"n_onsets": n, "n_dropped": dropped, "p5": float(np.mean(p5)) if p5 else math.nan}


def event_hour_unit(states: pd.DataFrame) -> dict | None:
    """The event-hour unit: needs >= 30 eligible minutes. Shares of eligible minutes in hi/mid/lo/none, onsets for 'mid or hi' and 'lo', and the pseudo-band
    shares and onset persistence."""
    el = states["eligible"].to_numpy(bool)
    if el.sum() < D.N["min_eligible_minutes"]:
        return None
    band = states["band"].to_numpy(object)
    out = {"n_eligible": int(el.sum()), "minutes_lost": int(60 - el.sum())}
    for b in BANDS:
        out[f"I_{b}"] = float(((band == b) & el).sum() / el.sum())
    mh = np.isin(band, ["mid", "hi"]) & el
    lo = (band == "lo") & el
    a, b = onsets_p5(mh, el), onsets_p5(lo, el)
    out.update({"n_on_mh": a["n_onsets"], "P5_mh": a["p5"], "n_on_lo": b["n_onsets"], "P5_lo": b["p5"], "dropped_p5": a["n_dropped"] + b["n_dropped"]})
    pk = states["pseudo"].to_numpy(object)
    for k in D.N["pseudo_bands"]["k"]:
        sk = np.array([v == k for v in pk]) & el
        out[f"PI_{k}"] = float(sk.sum() / el.sum())
        o = onsets_p5(sk, el)
        out[f"PP5_{k}"] = o["p5"]
    return out


# ---- CH52: tests --------------------------------------------------------------------------------------------------------------


def _stack(units: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Two rows per event-hour (band a coded mid=1, band b coded 0)."""
    ra = units.assign(treated=1.0, val=units[a])
    rb = units.assign(treated=0.0, val=units[b])
    return pd.concat([ra, rb], ignore_index=True)


PLACEBO_MIN_CLUSTERS = {"event": D.MIN_CLUSTERS, "day": D.G_MIN}


def n_tests(units: pd.DataFrame, *, n_boot: int = D.N_BOOT, seed: int = D.SEED_BOOT, placebo: bool = False) -> dict:
    """N1 = beta_3 of ``I = a + b1 post + b2 mid + b3 post x mid`` on stacked (mid, lo) rows per event-hour; N2 the same with ``P5_mh`` and ``P5_lo`` on
    event-hours with >= 1 onset of the type. p = max over event and calendar day (CR1, two-sided). ``units``: event_id, day, post (0/1), I_*, P5_*, n_on_*.
    ``placebo=True`` (in-time placebos, freeze-check fix 2): the day way needs G >= 15 (``PLACEBO_MIN_CLUSTERS``), no robustness refits."""
    out = {}
    mc = PLACEBO_MIN_CLUSTERS if placebo else None
    s1 = _stack(units, "I_mid", "I_lo")
    X, c = did_design(s1["post"], s1["treated"])
    out["N1"] = ols_contrast(s1["val"], X, c, {"event": s1["event_id"].to_numpy(), "day": s1["day"].to_numpy()}, n_boot=n_boot, seed=seed, robust=not placebo,
                             min_clusters_by_way=mc)
    a = units[(units["n_on_mh"] > 0)]
    b = units[(units["n_on_lo"] > 0)]
    r = pd.concat([a.assign(treated=1.0, val=a["P5_mh"]), b.assign(treated=0.0, val=b["P5_lo"])], ignore_index=True)
    X, c = did_design(r["post"], r["treated"])
    out["N2"] = ols_contrast(r["val"], X, c, {"event": r["event_id"].to_numpy() if len(r) else np.array([]), "day": r["day"].to_numpy() if len(r) else np.array([])}, n_boot=n_boot, seed=seed + 1,
                             robust=not placebo, min_clusters_by_way=mc)
    return out


def pseudo_band_check(units: pd.DataFrame, prefix: str, *, n_boot: int = 0, seed: int = D.SEED_BOOT) -> dict:
    """Binding for adopting N1/N2: over five equal-width bands in ``x = G - F0 - mu`` (width rho F0, k = -3..1; k = -1 is the mid band) the mid band's
    pre-to-post change is the most negative, and (mid change - mean change of the other four) has the sign of the mid change with two-sided p < 0.05 (event and
    day clusters). ``prefix`` is ``PI`` (shares) or ``PP5`` (onset persistence)."""
    ks = D.N["pseudo_bands"]["k"]
    ch = {}
    for k in ks:
        col = units[f"{prefix}_{k}"]
        m = np.isfinite(col)
        post = units.loc[m & (units["post"] == 1), col.name]
        pre = units.loc[m & (units["post"] == 0), col.name]
        ch[k] = float(post.mean() - pre.mean()) if len(post) and len(pre) else math.nan
    mid_k = -1
    others = [ch[k] for k in ks if k != mid_k]
    most_neg = bool(np.isfinite(ch[mid_k]) and all(np.isfinite(o) and ch[mid_k] < o for o in others))
    cols = [f"{prefix}_{k}" for k in ks if k != mid_k]
    diff = units[f"{prefix}_{mid_k}"] - units[cols].mean(axis=1)
    d = units.assign(diff=diff)
    d = d[np.isfinite(d["diff"])]
    X = np.column_stack([np.ones(len(d)), d["post"].to_numpy(float)])
    t = ols_contrast(d["diff"], X, [0.0, 1.0], {"event": d["event_id"].to_numpy(), "day": d["day"].to_numpy()}, n_boot=n_boot, seed=seed)
    same_sign = bool(np.isfinite(ch[mid_k]) and np.isfinite(t.get("estimate", math.nan)) and np.sign(t["estimate"]) == np.sign(ch[mid_k]))
    ok = bool(most_neg and t.get("testable") and t["p"] < D.PLACEBO_PSEUDO_P_MIN and same_sign)
    return {"changes": {str(k): v for k, v in ch.items()}, "mid_most_negative": most_neg, "mid_minus_others": t, "same_sign": same_sign, "ok": ok}


def in_time_placebos(units: pd.DataFrame, *, n_boot: int = 0) -> dict:
    """In-time placebos: the same DiD with a fake 'post' break at 2026-05-14 (pre window only) and 2026-06-18 (post window only). Two-sided p >= 0.05 for
    the placebo not to reject."""
    out = {}
    for name, brk, win in (("2026-05-14", "2026-05-14", "pre"), ("2026-06-18", "2026-06-18", "post")):
        u = units[units["window"] == win].copy()
        u["post"] = (u["day"] >= brk).astype(float)
        out[name] = n_tests(u, n_boot=n_boot, placebo=True) if len(u) else {"N1": {"testable": False, "p": 1.0}, "N2": {"testable": False, "p": 1.0}}
    return out


def placebo_p(placebos: list[dict]) -> float | None:
    """The placebo p used by adoption: the smallest two-sided p over the test's placebo fits, or None ('unverified', blocks adoption) if there is none
    or any of them is not testable (freeze-check fix 2: an untestable placebo never counts as 'does not reject')."""
    if not placebos or any(not (x or {}).get("testable") for x in placebos):
        return None
    return float(min(float(x["p"]) for x in placebos))


def band_shares_and_distribution(minutes: pd.DataFrame) -> dict:
    """Descriptive: shares of hi/mid/lo/none by window, and deciles plus a 0.25c histogram of ``G - F0`` over eligible event-minutes. ``minutes``: window,
    band, gap, f0."""
    out: dict = {"shares": {}, "deciles": {}, "hist": {}}
    for w in ("pre", "post"):
        m = minutes[(minutes["window"] == w) & minutes["band"].notna()]
        out["shares"][w] = {b: float((m["band"] == b).mean()) if len(m) else math.nan for b in BANDS}
        x = (m["gap"] - m["f0"]).to_numpy(float)
        out["deciles"][w] = [float(v) for v in np.percentile(x, np.arange(10, 100, 10))] if len(x) else []
        edges = np.arange(-0.10, 0.10001, 0.0025)
        out["hist"][w] = np.histogram(x, bins=edges)[0].astype(int).tolist() if len(x) else []
    return out


def band_map(minutes: pd.DataFrame) -> dict:
    """Post-window residual band map (planning only): incidence per band and persistence summaries by category. Never a gate input."""
    m = minutes[(minutes["window"] == "post") & minutes["band"].notna()]
    out = {"post_minutes": int(len(m)), "rho": D.N["rho"], "margin": D.N["margin"], "by_category": {}}
    for cat, g in m.groupby(m["category"].fillna("unknown")):
        out["by_category"][str(cat)] = {b: float((g["band"] == b).mean()) for b in BANDS}
    return out


def design_effect_from_clusters(values, clusters) -> float:
    """Design effect 1 + (mean cluster size - 1) * ICC from the pilot's event clustering (CREATIVE_BATCH_4.md section CB4-N; one-way ANOVA ICC,
    clipped to [0, 1]). Fewer than two clusters or no repeated cluster -> NaN (the caller then uses the declared floor)."""
    df = pd.DataFrame({"v": pd.to_numeric(pd.Series(list(values)), errors="coerce"), "c": list(clusters)}).dropna()
    k, n = df["c"].nunique(), len(df)
    if k < 2 or n <= k:
        return math.nan
    g = df.groupby("c")["v"]
    sizes, means = g.size().to_numpy(float), g.mean().to_numpy(float)
    grand = float(df["v"].mean())
    ssb = float((sizes * (means - grand) ** 2).sum())
    ssw = float(((df["v"] - g.transform("mean")) ** 2).sum())
    msb, msw = ssb / (k - 1), ssw / (n - k)
    n0 = (n - float((sizes**2).sum()) / n) / (k - 1)
    denom = msb + (n0 - 1.0) * msw
    icc = 0.0 if denom <= 0 else min(max((msb - msw) / denom, 0.0), 1.0)
    return 1.0 + (n / k - 1.0) * icc


def e_predicted_mde(rows_by_cell: dict[str, int], events_by_cell: dict[str, int], *, halves: bool = False) -> dict:
    """Predicted MDEs of the E tests from census counts under the declared scaling (CREATIVE_BATCH_4.md section CB4-E): E1 cell SE = 0.057c per SD of the
    scaled flow on 33,042 rows (HB1 FL2), scaled by sqrt(33,042 / rows); E2 cell SE = 4c print SD / sqrt(event clusters). ``delta`` combines the six cells with
    coefficients (S0 -1/2, S1 1, S2 -1/2, O0 1/2, O1 -1, O2 1/2); ``halves`` gives the 2x2 parallel-trends placebo (all coefficients 1). MDE = (z(0.0125/2)
    + z(0.8)) x SE (two-sided Holm first step, 80% power). No price change or mark-out is computed."""
    z = norm.isf(0.0125 / 2) + norm.isf(0.2)
    coef = {"S0": 1.0, "S1": 1.0, "O0": 1.0, "O1": 1.0} if halves else {"SP0": 0.5, "SP1": 1.0, "SP2": 0.5, "OP0": 0.5, "OP1": 1.0, "OP2": 0.5}
    out: dict = {}
    for name, per in (("E1_cents_per_sd", lambda c: 0.057 * math.sqrt(33042.0 / max(rows_by_cell.get(c, 0), 1))), ("E2_cents_per_print", lambda c: 4.0 / math.sqrt(max(events_by_cell.get(c, 0), 1)))):
        if any(rows_by_cell.get(c, 0) <= 0 for c in coef):
            out[name] = None
            continue
        se = math.sqrt(sum((k * per(c)) ** 2 for c, k in coef.items()))
        out[name] = {"se": se, "mde": z * se}
    return out


def pilot_power(g_bytes_per_hour: float, sd_i: float, n_event_hours_per_hour: float, deff: float, *, cap_bytes: float = D.N["ingress_cap_gb"]["measure"] * 1e9,
                stop: bool = False) -> dict:
    """Frozen H rule: ``H_cap`` = largest H in {84,168,252,336} with 1.2 H g <= cap; ``H_mde`` = smallest H whose predicted N1 MDE (two-sided Holm first
    step alpha 0.0125, power 0.8, deff >= 1.5) is <= 1.0 pp (336 if none); ``H = min(H_mde, H_cap)``; ``H_cap < 84`` = not testable.
    ``stop`` is the frozen stop rule (fewer than 5 eligible events per hour, or more than 30% of hours missing): when true N1 and N2 are not testable
    whatever H_cap is (``testable`` false); the H arithmetic is still reported, descriptively."""
    z = norm.isf(0.0125 / 2) + norm.isf(0.2)
    deff = max(deff, 1.5)
    mde = {}
    for H in D.N["H_grid"]:
        n = max(H * n_event_hours_per_hour, 1.0)
        se = math.sqrt(deff * 2.0 * 2.0 * sd_i**2 / n)  # DiD of two stacked bands, two periods
        mde[H] = z * se
    caps = [H for H in D.N["H_grid"] if 1.2 * H * g_bytes_per_hour <= cap_bytes]
    h_cap = max(caps) if caps else 0
    h_mde = next((H for H in D.N["H_grid"] if mde[H] <= 0.01), D.N["H_grid"][-1])
    return {"mde_by_H": {str(k): v for k, v in mde.items()}, "H_cap": h_cap, "H_mde": h_mde, "H": min(h_mde, h_cap) if h_cap else 0, "testable": bool(h_cap >= D.N["H_grid"][0] and not stop),
            "stop": bool(stop), "states_larger_mde": bool(h_cap and h_cap < h_mde)}


# ---- CH53: periods, origins, panel -------------------------------------------------------------------------------------------


def period_of(end_epoch: float) -> str | None:
    """P0 / P1 / P2 containing the scheduled end (the 7 days after each treatment date lie outside all three)."""
    for name, a, b in cb4_data.ERA_PERIODS:
        if D.epoch(a) <= end_epoch < D.epoch(b):
            return name
    return None


def era_fetch_windows(end_epoch: float) -> dict:
    """Fetch windows anchored on the scheduled end only (coverage invariance): prices [end - 72h - 8d, end + 1d]."""
    return {"prices": (end_epoch - D.E["origin_window_h"] * HOUR - cb4_data.ERA_PRICE_LOOKBACK_D * DAY, end_epoch + DAY)}


def era_origins(end_epoch: float) -> pd.DataFrame:
    """The 2h UTC grid in [end - 72h, end) with time-to-end buckets (0-24, 24-48, 48-72 h)."""
    g = hb.GRID_S
    lo = math.ceil((end_epoch - D.E["origin_window_h"] * HOUR) / g) * g
    t = np.arange(lo, end_epoch, g, dtype=float)
    tte = (end_epoch - t) / HOUR
    return pd.DataFrame({"t": t, "tte_h": tte, "bucket": np.minimum((tte // 24).astype(int), 2)})


def _yes_terms(tr: pd.DataFrame) -> tuple[np.ndarray, ...]:
    oi = tr["outcome_index"].astype(int).to_numpy()
    px = np.where(oi == 0, tr["price"].to_numpy(float), 1.0 - tr["price"].to_numpy(float))
    sgn = np.where((tr["side"].astype(str).str.upper().to_numpy() == "BUY") == (oi == 0), 1.0, -1.0)
    return tr["ts"].to_numpy(float), px, sgn, tr["size"].to_numpy(float)


def era_panel(rec: dict, ts: np.ndarray, vals: np.ndarray, trades: pd.DataFrame | None, truncated: bool, oldest_ts) -> pd.DataFrame:
    """E1 panel rows of one market at its origins: target ``d6h``, HB1 C0 controls (logit mid, |mid - 0.5|, 1h/1d/1w changes with missing flags, previous
    2h change), ``f_net_6h`` (signed notional, YES terms; ``d6h`` in cents) and ``f_imb_6h`` (reported only). Judgement-row filter applied. ``rec``: market_id, event_id, end_epoch,
    group, period, fee_category."""
    o = era_origins(float(rec["end_epoch"]))
    if not len(o) or len(ts) < 2:
        return pd.DataFrame()
    t = o["t"].to_numpy(float)
    asof = lambda x: hb._asof(ts, vals, x, hb.MAX_QUOTE_AGE_S)[0]  # noqa: E731
    mid = asof(t)
    d6 = 100.0 * (asof(t + 6 * HOUR) - mid)  # cents, as markouts (the E1 floor 0.10 is in cents per unit of scaled flow)
    d6 = np.where(t + 6 * HOUR <= ts[-1] + hb.MAX_QUOTE_AGE_S, d6, np.nan)
    f = {"c_chg_1h": mid - asof(t - HOUR), "c_chg_1d": mid - asof(t - DAY), "c_chg_1w": mid - asof(t - 7 * DAY), "c_dprev": mid - asof(t - hb.GRID_S)}
    out = pd.DataFrame({"market_id": rec["market_id"], "event_id": rec.get("event_id") or "m:" + str(rec["market_id"]), "group": rec["group"], "period": rec["period"], "bucket": o["bucket"], "t": t,
                        "mid": mid, "d6h": d6})
    with np.errstate(divide="ignore", invalid="ignore"):
        out["c_logit"] = np.log(mid / (1 - mid))
    out["c_absdev"] = np.abs(mid - 0.5)
    for k, v in f.items():
        out[k] = np.nan_to_num(v, nan=0.0)
        out[f"{k}_missing"] = np.isnan(v).astype(float)
    net = np.full(len(t), np.nan)
    imb = np.full(len(t), np.nan)
    traded = np.zeros(len(t), bool)
    if trades is not None and len(trades):
        tts, px, sgn, sz = _yes_terms(trades)
        order = np.argsort(tts, kind="stable")
        tts, px, sgn, sz = tts[order], px[order], sgn[order], sz[order]
        notion = sz * px
        cs, cg = np.concatenate([[0.0], np.cumsum(sgn * notion)]), np.concatenate([[0.0], np.cumsum(notion)])
        hi, lo = np.searchsorted(tts, t, side="left"), np.searchsorted(tts, t - 6 * HOUR, side="left")
        covered = (not truncated) or (t - 6 * HOUR >= H1.oldest_or_inf(oldest_ts))
        net = np.where(covered, cs[hi] - cs[lo], np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            imb = np.where(covered & (cg[hi] - cg[lo] > 0), (cs[hi] - cs[lo]) / (cg[hi] - cg[lo]), np.nan)
        traded = hi > 0
    elif trades is not None and not truncated:
        net, imb = np.zeros(len(t)), np.full(len(t), np.nan)
    out["f_net_6h"], out["f_imb_6h"], out["traded"] = net, imb, traded
    ok = np.isfinite(out["mid"]) & (out["mid"] > 0.02) & (out["mid"] < 0.98) & out["traded"] & np.isfinite(out["d6h"]) & np.isfinite(out["f_net_6h"])
    return out[ok].reset_index(drop=True)


def scale_flow(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """``f_net_6h`` winsorised at the pooled 1st and 99th percentiles and divided by its pooled SD over all cells."""
    p = panel.copy()
    lo, hi = np.percentile(p["f_net_6h"], [D.E["winsor"][0] * 100, D.E["winsor"][1] * 100])
    w = p["f_net_6h"].clip(lo, hi)
    sd = float(w.std(ddof=1))
    p["x"] = w / sd if sd > 0 else w
    return p, {"lo": float(lo), "hi": float(hi), "pooled_sd": sd}


def markouts(rec: dict, ts: np.ndarray, vals: np.ndarray, trades: pd.DataFrame) -> pd.DataFrame:
    """Maker mark-out per print in YES terms (cents): ``m = s (p(ts + 2h) - price_YES)``, ``s = +1`` if the maker bought YES (taker sold YES or bought NO).
    Components: spread ``s (p(ts) - price_YES)``, drift ``s (p(ts + 2h) - p(ts))``; they sum to ``m``. Prints in [end - 72h, end) with history prices usable at
    ``ts`` and ``ts + 2h``. ``AS = -m``."""
    if trades is None or not len(trades) or len(ts) < 2:
        return pd.DataFrame()
    end = float(rec["end_epoch"])
    tts, px, sgn, _sz = _yes_terms(trades)
    s = -sgn  # taker net-buys YES -> maker sold YES -> -1
    m = (tts >= end - D.E["origin_window_h"] * HOUR) & (tts < end)
    tts, px, s = tts[m], px[m], s[m]
    p0 = hb._asof(ts, vals, tts, hb.MAX_QUOTE_AGE_S)[0]
    p2 = hb._asof(ts, vals, tts + 2 * HOUR, hb.MAX_QUOTE_AGE_S)[0]
    ok = np.isfinite(p0) & np.isfinite(p2)
    spread, drift = 100.0 * s * (p0 - px), 100.0 * s * (p2 - p0)
    out = pd.DataFrame({"market_id": rec["market_id"], "event_id": rec.get("event_id") or "m:" + str(rec["market_id"]), "group": rec["group"], "period": rec["period"], "t": tts,
                        "bucket": np.minimum(((end - tts) // (24 * HOUR)).astype(int), 2), "mark": spread + drift, "spread": spread, "drift": drift})
    out["AS"] = -out["mark"]
    return out[ok].reset_index(drop=True)


def cell_columns(df: pd.DataFrame) -> list[str]:
    cells = [f"{g}{p}" for g in ("S", "O") for p in ("P0", "P1", "P2")]
    for c in cells:
        df[f"cell_{c}"] = ((df["group"] + df["period"]) == c).astype(float)
    return [f"cell_{c}" for c in cells]


def two_cohort_contrasts() -> dict[str, np.ndarray]:
    """Contrast vectors over the six cell parameters ordered SP0, SP1, SP2, OP0, OP1, OP2: delta_S = (S1 - S0) - (O1 - O0), delta_O = (O2 - O1) - (S2 - S1),
    delta = (delta_S + delta_O)/2."""
    ds = np.array([-1, 1, 0, 1, -1, 0], float)
    do = np.array([0, 1, -1, 0, -1, 1], float)
    return {"delta_S": ds, "delta_O": do, "delta": (ds + do) / 2.0}


def two_cohort_did(df: pd.DataFrame, y: str, *, slope: bool, controls: list[str] | None = None, n_boot: int = D.N_BOOT, seed: int = D.SEED_BOOT) -> dict:
    """One stacked regression with group x period cells. E1 (``slope=True``): y on x interacted with the six cells, cell intercepts, time-to-end bucket dummies and
    the C0 controls. E2 (``slope=False``): y on cell dummies (cell means) and bucket dummies. Reports delta, delta_S, delta_O with their own p (two-sided,
    event and day clusters) and the sign agreement of delta_S and delta_O. Needs >= 30 event clusters and >= 1,000 rows in every cell."""
    d = df.copy()
    cells = cell_columns(d)
    counts = {c: int(d[c].sum()) for c in cells}
    ev_counts = {c: int(d.loc[d[c] == 1, "event_id"].nunique()) for c in cells}
    if min(counts.values()) < D.E["min_rows_per_cell"] or min(ev_counts.values()) < D.E["min_clusters_per_cell"]:
        return {"testable": False, "p": 1.0, "reason": ["a cell has fewer than 30 event clusters or 1,000 rows"], "rows_per_cell": counts, "events_per_cell": ev_counts}
    bk = [(d["bucket"] == b).astype(float).to_numpy() for b in (1, 2)]
    cols = [d[c].to_numpy(float) for c in cells]
    if slope:
        cols += [d[c].to_numpy(float) * d["x"].to_numpy(float) for c in cells]
    cols += bk
    if slope and controls:
        cols += [d[c].to_numpy(float) for c in controls]
    X = np.column_stack(cols)
    off = len(cells) if slope else 0
    ways = {"event": d["event_id"].to_numpy(), "day": (d["t"] // DAY).astype(int).to_numpy()}
    out: dict = {"testable": True, "rows_per_cell": counts, "events_per_cell": ev_counts}
    for name, c6 in two_cohort_contrasts().items():
        c = np.zeros(X.shape[1])
        c[off:off + 6] = c6
        out[name] = ols_contrast(d[y].to_numpy(float), X, c, ways, n_boot=n_boot if name == "delta" else 0, seed=seed, robust=(name == "delta"))
    out["delta_S_O_sign_agree"] = bool(np.sign(out["delta_S"].get("estimate", 0.0)) == np.sign(out["delta_O"].get("estimate", 0.0)) != 0)
    out["p"] = out["delta"]["p"]
    out["estimate"] = out["delta"].get("estimate", math.nan)
    out["top5_dropped"], out["cluster_equal_sign"] = out["delta"].get("top5_dropped"), out["delta"].get("cluster_equal_sign")
    return out


def parallel_trends_placebo(df: pd.DataFrame, y: str, *, slope: bool, controls: list[str] | None = None) -> dict:
    """The same DiD inside P0 only, split at 2026-01-15 by scheduled end: 'post' = second half; sports vs others (no fees in either half)."""
    d = df[df["period"] == "P0"].copy()
    d["period"] = np.where(d["end_epoch"] >= D.epoch(D.DATES["D_pl_E"]), "P1", "P0")
    out = two_cohort_did_two_period(d, y, slope=slope, controls=controls)
    return out


def two_cohort_did_two_period(d: pd.DataFrame, y: str, *, slope: bool, controls: list[str] | None = None) -> dict:
    """Plain 2x2 DiD (sports vs others, first vs second half) with the same clustering; used by the parallel-trends placebo."""
    if not len(d):
        return {"testable": False, "p": 1.0, "reason": ["no rows"]}
    post = (d["period"] == "P1").astype(float).to_numpy()
    tr = (d["group"] == "S").astype(float).to_numpy()
    ways = {"event": d["event_id"].to_numpy(), "day": (d["t"] // DAY).astype(int).to_numpy()}
    if slope:
        x = d["x"].to_numpy(float)
        X = np.column_stack([np.ones(len(d)), post, tr, post * tr, x, x * post, x * tr, x * post * tr] + ([d[c].to_numpy(float) for c in controls] if controls else []))
        c = np.zeros(X.shape[1])
        c[7] = 1.0
    else:
        X, c = did_design(post, tr)
    return ols_contrast(d[y].to_numpy(float), X, c, ways)


def balanced_wallet_share(trades: pd.DataFrame, cell: str) -> dict:
    """Descriptive: share of notional from wallets with >= 4 trades in a market and |net shares| <= 5% of gross (wash-like activity defined here; not CH41's
    farmer rule)."""
    if trades is None or not len(trades):
        return {"cell": cell, "share": math.nan}
    d = trades.copy()
    d["signed"] = np.where(d["side"].astype(str).str.upper() == "BUY", 1.0, -1.0) * d["size"]
    d["notional"] = d["size"] * d["price"]
    g = d.groupby(["market_id", "wallet_hash"]).agg(n=("size", "size"), net=("signed", "sum"), gross=("size", "sum"), notional=("notional", "sum"))
    bal = g[(g["n"] >= 4) & (g["net"].abs() <= 0.05 * g["gross"])]
    tot = float(g["notional"].sum())
    return {"cell": cell, "share": float(bal["notional"].sum() / tot) if tot > 0 else math.nan}


# ---- family M: adoption and the cost register ----------------------------------------------------------------------------------


def _top5_ok(t: str, r: dict, ps: dict[str, float]) -> bool:
    """Section 2.6 (ii) per declared way: with the way's top-5 clusters dropped, the test is testable, keeps its sign, meets its floor and still rejects under
    Holm (its p replaced by the dropped-sample p, the other tests' p unchanged). Without ``top5_dropped`` only an explicit ``top5_ok`` counts."""
    d = r.get("top5_dropped")
    if not d:
        return bool(r.get("top5_ok"))
    est = r.get("estimate", math.nan)
    for x in d.values():
        e = x.get("estimate", math.nan)
        if not (x.get("testable") and np.isfinite(e) and np.isfinite(est) and np.sign(e) == np.sign(est) and abs(e) >= D.FLOORS[t]):
            return False
        if not CCholm({**ps, t: float(x["p"])})[t]["reject"]:
            return False
    return True


def _cluster_equal_ok(r: dict) -> bool:
    """Section 2.6 (iii) per declared way; a missing value blocks."""
    c = r.get("cluster_equal_sign")
    return bool(c) and all(bool(v) for v in (c.values() if isinstance(c, dict) else [c]))


def adoption(results: dict) -> dict:
    """Family M decision. ``results[test]``: estimate, ci95, p (two-sided), placebo_p, ``top5_dropped`` (per way) and ``cluster_equal_sign`` (per way) from
    ``ols_contrast(robust=True)``, plus pseudo_band_ok (N1/N2) or sign_agree (E1/E2). Holm at alpha 0.05 over the four two-sided p. Adopted iff Holm
    rejects, the floor is met, the in-time/parallel placebo does not reject (p >= 0.05) and the binding robustness (i)-(vi) holds."""
    ids = list(D.TESTS["M"])
    ps = {t: float(results.get(t, {}).get("p", 1.0)) for t in ids}
    hm = CCholm(ps)
    out = {}
    for t in ids:
        r = results.get(t, {})
        est = r.get("estimate", math.nan)
        floor_met = bool(np.isfinite(est) and abs(est) >= D.FLOORS[t])
        pp = r.get("placebo_p")
        placebo_ok = bool(pp is not None and np.isfinite(pp) and pp >= D.PLACEBO_PSEUDO_P_MIN)  # None = unverified placebo: blocks
        top5, ceq = _top5_ok(t, r, ps), _cluster_equal_ok(r)
        robust = bool(top5 and ceq and bool(r.get("pseudo_band_ok") if t in ("N1", "N2") else r.get("sign_agree")))
        reject = bool(hm[t]["reject"])
        out[t] = {"estimate": est, "ci95": r.get("ci95"), "p": ps[t], "p_holm": hm[t]["p_holm"], "holm_reject": reject, "floor": D.FLOORS[t], "floor_met": floor_met,
                  "placebo_p": pp, "placebo_ok": placebo_ok, "placebo_status": "unverified" if pp is None else ("not rejected" if placebo_ok else "rejected"), "robust": robust, "top5_ok": top5, "cluster_equal_ok": ceq,
                  "adopted": bool(reject and floor_met and placebo_ok and robust), "label": cost_regimes.LABEL}
    return out


def CCholm(ps: dict[str, float]) -> dict:  # noqa: N802
    from . import cb3_common as CC

    return CC.holm(ps, D.ALPHA_M)


def commit_register(results: dict, band_map_: dict | None, path: Path | None = None) -> dict:
    """Write ``cost_regimes_v1.json`` (once) from the family-M results under rule R0: ``a_AS`` = the upper 95% bound of E2's delta (cents) iff E2 is adopted with
    a positive sign, else 0; ``era_rule`` = post_rollout_or_interaction iff E1 or E2 is adopted; fee/half-spread additions are 0 (a measurement never changes
    them here). Refuses if any of N1, N2, E1, E2 is missing."""
    missing = [t for t in D.TESTS["M"] if t not in results]
    if missing:
        raise cost_regimes.CostRegimeError(f"family M incomplete: {missing}")
    ad = adoption(results)
    a_as = 0.0
    if ad["E2"]["adopted"] and ad["E2"]["estimate"] > 0:
        ci = ad["E2"].get("ci95") or [0.0, 0.0]
        a_as = max(float(ci[1]), 0.0)
    era = cost_regimes.ERA_RULE_POST if (ad["E1"]["adopted"] or ad["E2"]["adopted"]) else cost_regimes.ERA_RULE_POOLED
    payload = {"version": cost_regimes.VERSION, "label": cost_regimes.LABEL, "fee_eras": cost_regimes.FEE_ERAS, "excluded_regime_dates": cost_regimes.EXCLUDED_REGIME_DATES,
               "measurements": ad, "family_M_complete": True, "a_AS_cents": a_as, "era_rule": era, "fee_rate_add": 0.0, "half_spread_add": 0.0, "band_map": band_map_,
               "declaration_sha256": D.declaration_sha256()}
    return cost_regimes.write_register(payload, path)
