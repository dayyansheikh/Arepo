# ruff: noqa: E501
"""CB14-W (docs/research_lab/CREATIVE_BATCH_14.md CB14-W): offline, synthetic fixtures and fake transports only; no network, no real CB14 quantity."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import numpy as np
import pytest

from astrolabe.research_lab import cb11_a
from astrolabe.research_lab import cb14_common as c14
from astrolabe.research_lab import cb14_w as w

H = 3600.0
D_ = 86400.0


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def rev(ts, user="A", size=1000, parent=900, tags=(), comment="", uid=None, hidden=False, revid=1):
    d = {"revid": revid, "parentid": 1, "timestamp": iso(ts), "size": size, "comment": comment, "tags": list(tags)}
    if hidden:
        d["userhidden"] = True
    else:
        d["user"] = user
        d["userid"] = uid if uid is not None else abs(hash(user)) % 10000 + 1
    return d


def revrow(ts, uidx=1, delta=60.0, bot=0, revert=0, unknown=0, revid=1):
    return {"page_id": "p", "revid": revid, "ts": ts, "size": 1000.0, "delta": delta, "uidx": uidx, "bot": bot, "revert": revert, "unknown_user": unknown}


# =====================================================================================================================================================
# Guards, parsing, rules
# =====================================================================================================================================================


def test_rows_at_w_end_refused_and_before_accepted():
    end = w.w_end()
    assert w.require_before_w_end(end - 1) == end - 1
    with pytest.raises(w.Refused):
        w.require_before_w_end(end)
    rows = [{"ts": end - 1}, {"ts": end}, {"ts": end + 5}]
    assert w.keep_before_w_end(rows) == [{"ts": end - 1}]


def test_listing_date_rule_ignores_status_and_close_time():
    a, b = w.listed_window()
    assert w.listing_ok(a) and w.listing_ok(b - 1) and not w.listing_ok(a - 1) and not w.listing_ok(b)
    row = {"market_id": "1", "event_id": "e", "series_id": "", "neg_risk_market_id": "", "created_epoch": a + 5, "sports_tag": 0, "sports_re": 0, "mention": 0, "entertainment": 0, "death": 0}
    for fetched in ("closed", "active"):
        assert w.frame_status({**row, "fetched_as": fetched}, set(), {})[0] == "kept"
    assert w.frame_status({**row, "created_epoch": b + 1}, set(), {})[0] == "dropped:window"


def test_frame_status_order_and_full_series_key():
    a, _ = w.listed_window()
    row = {"market_id": "1", "event_id": "e1", "series_id": "s1", "neg_risk_market_id": "n1", "created_epoch": a + 5, "sports_tag": 0, "sports_re": 0, "mention": 0, "entertainment": 0, "death": 0}
    keys = {"event": set(), "neg_risk_market": set(), "series": {"s1"}}
    assert w.frame_status(row, set(), keys) == ("dropped:key", "series")  # a date ladder's whole series is dropped
    assert w.frame_status(row, {"1"}, {"event": set(), "neg_risk_market": set(), "series": set()}) == ("dropped:key", "market")
    assert w.frame_status({**row, "sports_re": 1}, set(), {})[0] == "dropped:sports"
    assert w.frame_status({**row, "mention": 1}, set(), {})[0] == "dropped:mention"
    assert w.frame_status({**row, "death": 1}, set(), {})[0] == "stratum:death"
    assert w.full_series_counterfactual(row, keys)


def mk_market(mid="m1", q="Will Keir Starmer resign by December 31?", created="2025-01-02T00:00:00Z", labels=("Yes", "No"), **kw):
    return {"id": mid, "question": q, "outcomes": json.dumps(list(labels)), "clobTokenIds": json.dumps(["ty", "tn"]), "conditionId": "c" + mid, "createdAt": created, "endDate": "2025-12-31T00:00:00Z",
            "negRiskMarketID": kw.get("nr", ""), "feeSchedule": {"rate": 0.04}, "outcomePrices": json.dumps(["0", "1"]), "umaResolutionStatus": "resolved", "closedTime": "2025-02-01T00:00:00Z"}


def test_parse_market_whitelist_classes_and_non_binary():
    ev = {"id": "e1", "title": "Starmer out?", "tags": [{"id": "2"}], "series": []}
    row = w.parse_market(mk_market(), ev, fetched_as="closed", term="resign", sports_ids=set())
    assert row["cls"] == "resign" and row["yes_index"] == 0 and row["token_yes"] == "ty"
    for forbidden in ("outcomePrices", "outcome_prices", "closedTime", "uma_status", "umaResolutionStatus"):
        assert forbidden not in row
    assert w.parse_market(mk_market(labels=("Up", "Down")), ev, fetched_as="closed", term="resign", sports_ids=set()) is None
    assert w.parse_market(mk_market(q="Will it rain?"), ev, fetched_as="closed", term="resign", sports_ids=set()) is None
    assert w.market_class("Will Biden be indicted?") == "indicted"
    assert w.market_class("Will Powell be fired?") == "fired"
    assert w.market_class("Macron out as President by June?") == "out_as"
    assert w.market_class("Will X be removed from office?") == "removed"
    assert w.market_class("Will the Queen die this year?") == "death"
    sports = w.parse_market(mk_market(q="Will the head coach be fired?"), {**ev, "tags": [{"id": "1"}]}, fetched_as="closed", term="fired", sports_ids={"1"})
    assert sports["sports_tag"] == 1 and sports["sports_re"] == 1
    mention = w.parse_market(mk_market(q="Will Trump say resign?"), {**ev, "tags": [{"id": "100343"}]}, fetched_as="closed", term="resign", sports_ids=set())
    assert mention["mention"] == 1
    assert w.parse_outcome(mk_market(), ev, 0)["uma_status"] == "resolved"


def test_search_all_pages_to_has_more_false_and_refuses_on_loop():
    pages = {1: {"events": [{"id": "a"}], "pagination": {"hasMore": True, "totalResults": 3}}, 2: {"events": [{"id": "b"}], "pagination": {"hasMore": True}},
             3: {"events": [{"id": "c"}], "pagination": {"hasMore": False}}}

    class Lim:
        def __init__(self):
            self.calls = []

        def get(self, url, params):
            self.calls.append(params["page"])
            return 200, pages[params["page"]]

    lim = Lim()
    evs, info = w.search_all(lim, "resign", "closed")
    assert [e["id"] for e in evs] == ["a", "b", "c"] and info["pages"] == 3 and info["total"] == 3 and lim.calls == [1, 2, 3]

    class Loop:
        def get(self, url, params):
            return 200, {"events": [], "pagination": {"hasMore": True}}

    with pytest.raises(w.Refused):
        w.search_all(Loop(), "resign", "closed", max_pages=3)


def test_entity_rule_pin_stop_list_and_candidate():
    assert w.entity_source_sha256() == w.ENTITY_SOURCE_SHA256 == w.check_entity_source()
    assert set(cb11_a.STOP_LIST) <= set(w.STOP_LIST) and "prime minister" in w.STOP_LIST
    assert w.entity_candidate("Will Keir Starmer resign by December 31?", "Starmer out?") == "Keir Starmer"
    assert w.entity_candidate("Will the President resign?", "") == ""  # office words are stop-listed


def test_country_map_first_match_and_singleton_and_heads():
    assert w.country_of("British politician, Prime Minister") == "GB"
    assert w.country_of("American businessman and politician") == "US"
    a, b = w.country_of("Tuvaluan official", "X Y"), w.country_of("Tuvaluan official", "Z W")
    assert a.startswith("single:") and a != b  # an unmatched description is its own country
    assert w.country_of("French-born American politician") == "US"  # the first entry in the frozen map order that matches wins, not the first word in the text
    assert w.is_head("British politician; Prime Minister of the United Kingdom") and not w.is_head("American journalist")


def test_audit_reading_precision_and_drops(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"version": w.AUDIT_VERSION, "rule_revision": 1, "labels": {"A": "match", "B": "match", "C": "not"}}))
    a = w.read_audit(p, require_committed=False)
    assert a["precision"] == pytest.approx(2 / 3) and not a["pass"] and a["drop"] == ["C"]
    p.write_text(json.dumps({"version": w.AUDIT_VERSION, "labels": {f"e{i}": ("match" if i else "not") for i in range(10)}}))
    assert w.read_audit(p, require_committed=False)["pass"]
    with pytest.raises(w.NotNow):
        w.read_audit(tmp_path / "missing.json")
    with pytest.raises(w.Refused):
        w.read_audit(p, require_committed=True)  # a file outside the repo is never 'committed'
    p.write_text(json.dumps({"version": "x", "labels": {}}))
    with pytest.raises(w.Refused):
        w.read_audit(p, require_committed=False)


# =====================================================================================================================================================
# Revisions and bursts
# =====================================================================================================================================================


def test_rev_row_never_writes_user_and_ignores_mw_reverted_and_hidden_is_unknown():
    users: dict = {}
    r1 = w.rev_row(rev(1000, "Alice", tags=["mw-reverted"]), 900.0, users, set(), "p")
    assert set(r1) == set(w.REV_COLUMNS) and r1["revert"] == 0 and r1["uidx"] == 1 and r1["delta"] == 100.0
    r2 = w.rev_row(rev(1010, hidden=True, revid=2), 1000.0, users, set(), "p")
    assert r2["unknown_user"] == 1 and r2["uidx"] == 0 and len(users) == 1  # a revision-deleted name is never a distinct user
    r3 = w.rev_row(rev(1020, "Alice", revid=3), 1000.0, users, set(), "p")
    assert r3["uidx"] == 1  # same user, same index
    r4 = w.rev_row(rev(1030, "Bob", revid=4), 1000.0, users, set(), "p")
    assert r4["uidx"] == 2
    blob = json.dumps([r1, r2, r3, r4])
    assert "Alice" not in blob and "Bob" not in blob
    for forb in c14.FORBIDDEN_OUTPUT_COLUMNS:
        assert forb not in set(r1)
    assert w.is_revert_at_save(["mw-undo"], "") and w.is_revert_at_save([], "Reverted edits by X") and not w.is_revert_at_save(["mw-reverted"], "fix typo")
    bot = w.rev_row(rev(1040, "SomeBot", revid=5), 1000.0, users, set(), "p")
    assert bot["bot"] == 1
    keyed = w.rev_row(rev(1050, "Cleaner", revid=6), 1000.0, users, {w.bot_key("Cleaner")}, "p")
    assert keyed["bot"] == 1


def test_parse_revision_batch_chains_parent_sizes():
    revs = [{**rev(1000, "A", size=500, revid=1), "parentid": 0}, rev(1100, "B", size=650, revid=2), rev(1200, "A", size=640, revid=3)]
    rows, last = w.parse_revision_batch(revs, "p", {}, set(), None)
    assert [r["delta"] for r in rows] == [500.0, 150.0, -10.0] and last == 640.0


T0 = ep("2025-06-01T12:00:00Z")


def burst_page(extra=(), n_baseline_days=40):
    """A quiet page (1 edit/day) plus the given revisions."""
    base = [revrow(T0 - i * D_ - 5 * H, uidx=(i % 3) + 1, delta=10.0, revid=1000 + i) for i in range(2, n_baseline_days)]
    return sorted([*base, *extra], key=lambda r: r["ts"])


def burst_edits(t, n=3, users=(1, 2, 1), delta=60.0, start_id=1):
    return [revrow(t - 60 * (n - 1 - i), uidx=users[i % len(users)], delta=delta, revid=start_id + i) for i in range(n)]


def test_burst_rule_edges():
    hs = T0 - 100 * D_
    ok = burst_page(burst_edits(T0))
    bl, info = w.detect_bursts(ok, hist_start=hs)
    assert len(bl) == 1 and bl[0]["b"] == T0 and bl[0]["count"] == 3
    # 2 edits only
    assert w.detect_bursts(burst_page(burst_edits(T0, n=2)), hist_start=hs)[0] == []
    # 3 edits by one user
    assert w.detect_bursts(burst_page(burst_edits(T0, users=(1,))), hist_start=hs)[0] == []
    # a bot edit does not count: 3 edits of which one is a bot
    es = burst_edits(T0)
    es[1]["bot"] = 1
    assert w.detect_bursts(burst_page(es), hist_start=hs)[0] == []
    # a revert at save does not count
    es = burst_edits(T0)
    es[0]["revert"] = 1
    assert w.detect_bursts(burst_page(es), hist_start=hs)[0] == []
    # 99 bytes vs 100 bytes in total
    assert w.detect_bursts(burst_page(burst_edits(T0, delta=33.0)), hist_start=hs)[0] == []
    assert len(w.detect_bursts(burst_page(burst_edits(T0, delta=100 / 3)), hist_start=hs)[0]) == 1
    # unknown-user revisions count as revisions but never as distinct users
    es = burst_edits(T0, users=(1, 0, 0))
    assert w.detect_bursts(burst_page(es), hist_start=hs)[0] == []
    es = burst_edits(T0, users=(1, 2, 0))
    assert len(w.detect_bursts(burst_page(es), hist_start=hs)[0]) == 1


def test_burst_percentile_is_causal_and_baseline_requires_history():
    hs = T0 - 100 * D_
    # a heavy history at b - 5 d raises the 99th percentile above 3, so a plain triple at b is not a burst
    heavy = [r for k in range(150) for r in burst_edits(T0 - 5 * D_ + k * 600, n=6, users=(1, 2, 3), start_id=5000 + k * 10)]
    bl, info = w.detect_bursts(burst_page([*heavy, *burst_edits(T0)]), hist_start=hs, since=T0)
    assert bl == [] and info["below_percentile"] >= 1
    # the same heavy activity at b - 12 h (inside the excluded last day) must NOT enter the baseline
    late = [r for k in range(10) for r in burst_edits(T0 - 12 * H + k * 600, n=6, users=(1, 2, 3), start_id=7000 + k * 10)]
    bl, _ = w.detect_bursts(burst_page([*late, *burst_edits(T0)]), hist_start=hs, since=T0)
    assert [b["b"] for b in bl] == [T0]
    # no baseline: the page's history starts less than 30 days before b
    bl, info = w.detect_bursts(burst_page(burst_edits(T0)), hist_start=T0 - 10 * D_)
    assert bl == [] and info["no_baseline"] >= 1


def test_burst_refractory_one_per_six_hours():
    hs = T0 - 100 * D_
    two = [*burst_edits(T0), *burst_edits(T0 + 3 * H, start_id=50), *burst_edits(T0 + 6 * H + 60, start_id=90)]
    bl, info = w.detect_bursts(burst_page(two), hist_start=hs)
    assert [round(b["b"]) for b in bl] == [round(T0), round(T0 + 6 * H + 60)] and info["refractory"] >= 1


def test_baseline_threshold_uses_only_30d_to_1d():
    t = np.array([T0 - 3 * D_ + k for k in (0, 60, 120)] + [T0 - 2 * H + k for k in range(0, 600, 60)], float)
    thr_all = w.baseline_threshold(t, T0, 600.0, 100.0)
    assert thr_all == 3.0  # the three edits 3 days earlier; the 10 edits at b - 2 h lie in the excluded last day


# =====================================================================================================================================================
# Prints, state, decisive moves, W1
# =====================================================================================================================================================

DD = ep("2025-06-10T12:00:00Z")  # a decisive-move time inside the W calendar


def mk_tx(points, truncated=False, oldest=math.nan):
    return w.TxSeries([{"ts": t, "price": p, "size": s} for t, p, s in points], oldest_ts=oldest, truncated=truncated)


def ramp(prices_at: dict[float, float], start: float, end: float, step=300.0, default=0.30, size=100.0):
    """A print every ``step`` seconds from ``start`` to ``end`` at ``default`` unless ``prices_at`` overrides that time."""
    pts, t = [], start
    while t <= end:
        pts.append((t, prices_at.get(t, default), size))
        t += step
    return pts


def test_tx_series_state_coverage_vwap():
    tx = mk_tx([(1000, 0.3, 10), (2000, 0.5, 30), (9000, 0.7, 10)])
    assert tx.state(2001) == 0.5 and tx.state(1000) is None  # [t - 6 h, t): the print at t itself is not in the state
    assert tx.vwap(0, 3000) == pytest.approx((0.3 * 10 + 0.5 * 30) / 40)
    assert tx.state(9000 + 7 * H) is None  # nothing in the last 6 h
    unc = mk_tx([(100000, 0.5, 1)], truncated=True, oldest=90000)
    assert unc.covered(90000) and not unc.covered(89999)
    assert unc.state(95000) is None  # [t - 6 h, t) reaches before the oldest print: uncovered, no state
    assert unc.max_print(0, 1e9) == (0.5, 100000.0, 1.0)


def move_path(d0, v=0.30):
    """A path whose decisive move starts at ``d0`` (0.30 flat, a 0.55 print at d0, 0.92 at d0 + 30 min, 0.93 at + 35 min)."""
    over = {d0: 0.55, d0 + 1800: 0.92, d0 + 2100: 0.93}
    pts = ramp({}, d0 - 80 * H, d0 - 300) + [(d0, 0.55, 100.0), (d0 + 600, 0.55, 100.0), (d0 + 1800, 0.92, 100.0), (d0 + 2100, 0.93, 100.0)]
    del over
    return sorted(pts)


def test_decisive_move_rules():
    d0 = DD
    mv = w.decisive_move(mk_tx(move_path(d0)))
    assert mv["D"] == d0 + 1800 and mv["D0"] == d0 and mv["V"] == pytest.approx(0.30)
    # the 30-minute confirmation print is needed
    no_conf = [p for p in move_path(d0) if p[0] != d0 + 2100]
    assert w.decisive_move(mk_tx(no_conf)) is None
    late_conf = [*no_conf, (d0 + 1800 + 1801, 0.93, 100.0)]
    assert w.decisive_move(mk_tx(late_conf)) is None
    # V_D boundary: 0.50 accepted, 0.51 not (a 0.30 -> 0.70 -> 0.92 path puts D0 at the 0.70 print)
    for v, ok in ((0.50, True), (0.51, False)):
        pts = ramp({}, d0 - 80 * H, d0 - 300, default=v) + [(d0 - 1800, 0.95, 100.0), (d0 - 1500, 0.95, 100.0)]
        assert (w.decisive_move(mk_tx(sorted(pts))) is not None) is ok
    path = ramp({}, d0 - 80 * H, d0 - 7000) + [(d0 - 3600, 0.70, 100.0), (d0, 0.92, 100.0), (d0 + 600, 0.93, 100.0)]
    mv2 = w.decisive_move(mk_tx(sorted(path)))
    assert mv2["D"] == d0 and mv2["D0"] == d0 - 3600 and mv2["V"] == pytest.approx(0.30)  # D0 is the 0.70 print, not the 0.92 crossing
    # uncovered V window -> no move
    unc = mk_tx(sorted(move_path(d0)), truncated=True, oldest=d0)
    assert w.decisive_move(unc) is None
    # outside the W calendar -> none
    far = ep("2026-05-01T00:00:00Z")
    assert w.decisive_move(mk_tx(move_path(far))) is None


def test_dedupe_one_move_per_subject_per_7_days():
    mvs = [{"subject": "s", "market_id": "b", "D": 10 * D_}, {"subject": "s", "market_id": "a", "D": 3 * D_}, {"subject": "s", "market_id": "c", "D": 11 * D_}, {"subject": "t", "market_id": "d", "D": 4 * D_}]
    kept = w.dedupe_moves(mvs)
    assert [(m["subject"], m["D"]) for m in kept] == [("s", 3 * D_), ("t", 4 * D_), ("s", 10 * D_)]


def test_lead_indicator_state_cap_and_entry_print():
    d0 = DD
    tx = mk_tx(move_path(d0))
    v = 0.30
    assert w.lead_indicator([d0 - 1800], tx, d0, v) == 1
    assert w.lead_indicator([d0 - 100], tx, d0, v) == 0  # inside 5 min of D0: not a lead
    assert w.lead_indicator([d0 - 121 * 60], tx, d0, v) == 0  # more than 120 min before
    # state cap v + 5c: a drift to 0.36 before the burst disqualifies, 0.35 qualifies
    for px, ok in ((0.36, 0), (0.35, 1)):
        pts = [(t, (px if d0 - 3000 <= t < d0 - 1700 else p), s) for t, p, s in move_path(d0)]
        assert w.lead_indicator([d0 - 1500], mk_tx(pts), d0, v) == ok
    # no entry print in [b + 60 s, b + 15 min] -> 0 (conservative)
    sparse = mk_tx([(d0 - 4 * H, 0.30, 10), (d0 + 3600, 0.9, 10)])
    assert w.lead_indicator([d0 - 1800], sparse, d0, v) == 0
    # a burst whose state cannot be computed (uncovered) is no lead
    unc = mk_tx(move_path(d0), truncated=True, oldest=d0 - 1000)
    assert w.lead_indicator([d0 - 1800], unc, d0, v) == 0


def test_placebo_anchors_and_no_placebo_when_listed_late():
    d0 = DD
    tx = mk_tx(move_path(d0))
    a = w.placebo_anchors(d0, tx, d0 - 80 * H)
    assert len(a) == 11 and a[0][0] == d0 - 6 * H and a[-1][0] == d0 - 66 * H and all(v == pytest.approx(0.30) for _, v in a)
    assert len(w.placebo_anchors(d0, tx, d0 - 17 * H)) == 2  # listed < 18 h before D0: anchors k = 1, 2 only
    unit = {"D0": d0, "V": 0.30, "created": d0 - 17 * H}
    val, det = w.w1_value(unit, [], tx)
    assert math.isnan(val) and det["label"] == "no placebo"


def test_w1_value_excess_over_hot_period():
    d0 = DD
    tx = mk_tx(move_path(d0))
    unit = {"D0": d0, "V": 0.30, "created": d0 - 80 * H}
    bursts = sorted([d0 - 1800, d0 - 6 * H - 3600, d0 - 12 * H - 3600])
    val, det = w.w1_value(unit, bursts, tx)
    assert det["L"] == 1 and det["pi_hat"] == pytest.approx(2 / 11) and val == pytest.approx(1 - 2 / 11)
    val0, det0 = w.w1_value(unit, [d0 - 6 * H - 3600], tx)
    assert det0["L"] == 0 and val0 == pytest.approx(-1 / 11)


def test_shifted_bursts_one_offset_per_subject_in_range():
    rng = np.random.default_rng(1)
    base = {"a": [1e9, 1e9 + 100], "b": [2e9]}
    sh = w.shifted_bursts(base, rng)
    off_a = [x - y for x, y in zip(sh["a"], base["a"], strict=True)]
    assert off_a[0] == pytest.approx(off_a[1]) and -60 * D_ <= off_a[0] <= -30 * D_ and -60 * D_ <= sh["b"][0] - 2e9 <= -30 * D_


# =====================================================================================================================================================
# W2: market choice, round trip, units, worst case, test pipeline
# =====================================================================================================================================================

B0 = ep("2025-03-05T12:00:00Z")


def mk_m(mid="m1", created=None, end=None, rate=0.04):
    return {"market_id": mid, "created_epoch": B0 - 60 * D_ if created is None else created, "end_epoch": B0 + 10 * D_ if end is None else end, "fee_rate": rate, "yes_index": 0}


def flat_series(price, start=None, end=None, step=300.0):
    return mk_tx(ramp({}, B0 - 10 * H if start is None else start, B0 + 4 * H if end is None else end, step=step, default=price))


def test_choose_market_nearest_end_band_and_labels():
    near, far = mk_m("near", end=B0 + 4 * H), mk_m("far", end=B0 + 20 * D_)
    txs = {"near": flat_series(0.30), "far": flat_series(0.30)}
    m, lab, det = w.choose_market([far, near], txs, B0)
    assert m["market_id"] == "near" and lab == "ok" and det["state"] == pytest.approx(0.30)
    # end before t + 3 h -> not a candidate
    m, lab, _ = w.choose_market([mk_m("soon", end=B0 + 2 * H)], {"soon": flat_series(0.30)}, B0)
    assert m is None and lab == "no market"
    # state outside [0.05, 0.60]
    assert w.choose_market([near], {"near": flat_series(0.70)}, B0)[1] == "state outside band"
    assert w.choose_market([near], {"near": flat_series(0.05)}, B0)[0]["market_id"] == "near"  # the band is closed at 0.05
    # no state
    assert w.choose_market([near], {"near": mk_tx([(B0 - 20 * H, 0.3, 1)] + [(B0 + H, 0.3, 1)])}, B0)[1] == "no state"
    # uncovered
    unc = mk_tx(ramp({}, B0 - 3 * H, B0 + 4 * H), truncated=True, oldest=B0 - 3 * H)
    assert w.choose_market([near], {"near": unc}, B0)[1] == "uncovered"
    # the nearest end that qualifies wins even when a nearer one fails
    m, lab, _ = w.choose_market([near, mk_m("mid", end=B0 + 5 * D_)], {"near": flat_series(0.80), "mid": flat_series(0.30)}, B0)
    assert m["market_id"] == "mid" and lab == "ok"


def test_round_trip_entry_max_exit_min_stale_size_and_fees():
    t = B0
    pts = [(t + 120, 0.40, 250.0), (t + 300, 0.38, 10.0), (t + 2 * H + 60, 0.50, 5.0), (t + 2 * H + 600, 0.52, 5.0)]
    rt = w.round_trip(mk_tx(pts), t, 0.04)
    assert rt["label"] == "ok" and rt["e"] == 0.40 and rt["x"] == 0.50 and rt["size"] == 100.0  # min(100, 250); the exit is the MIN print in [2 h, 2 h 30]
    assert rt["net"] == pytest.approx(0.50 - 0.40 - 0.04 * 0.40 * 0.60 - 0.04 * 0.5 * 0.5)
    # stale exit: nothing in [2 h, 2 h 30], the last print AFTER the entry print
    rt2 = w.round_trip(mk_tx([(t + 120, 0.40, 50.0), (t + 3000, 0.45, 5.0), (t + 3 * H, 0.9, 5.0)]), t, 0.04)
    assert rt2["label"] == "stale exit" and rt2["x"] == 0.45 and rt2["size"] == 50.0
    # no exit when nothing follows the entry print
    assert w.round_trip(mk_tx([(t + 120, 0.40, 50.0)]), t, 0.04)["label"] == "no exit"
    # the entry print itself is never its own exit; a print BEFORE the entry print is never a stale exit
    assert w.round_trip(mk_tx([(t + 100, 0.30, 5.0), (t + 120, 0.40, 50.0)]), t, 0.04)["label"] in ("no exit", "ok") and w.round_trip(mk_tx([(t + 100, 0.30, 5.0), (t + 120, 0.40, 50.0)]), t, 0.04)["label"] == "no exit"
    assert w.round_trip(mk_tx([(t + 10, 0.4, 1.0)]), t, 0.04)["label"] == "no entry print"  # [b + 60 s, ...] excludes b + 10 s
    # +1c per side lowers the net by 2c
    assert w.net_of(0.4, 0.5, 0.04, 0.01) == pytest.approx(w.net_of(0.4, 0.5, 0.04) - 0.02)
    assert w.net_of(0.4, 0.5, 0.04) == pytest.approx(0.0804)


def test_worst_case_net_is_min_of_p90_and_false_burst_mean():
    units = [{"net": -0.02, "rise": False}, {"net": -0.04, "rise": False}, {"net": 0.30, "rise": True}]
    assert w.worst_case_net(units) == pytest.approx(-0.093)  # the false-burst mean (-3c) is better than the p90, so the p90 binds
    units2 = [{"net": -0.20, "rise": False}, {"net": 0.30, "rise": True}]
    assert w.worst_case_net(units2) == pytest.approx(-0.20)


def mk_D(n_sub=40, bursts_per=8, seed=3, drift=0.0):
    """A synthetic W dataset: ``n_sub`` subjects with one market each, weekly bursts, prices a noisy 0.30 level (``drift`` is added after each burst)."""
    rng = np.random.default_rng(seed)
    subjects, by_subject, markets, txs, bursts, pages = {}, {}, {}, {}, {}, {}
    t_start = ep("2025-01-06T00:00:00Z")
    for s in range(n_sub):
        sid, mid = f"p{s}", f"m{s}"
        bl = [t_start + (k * 7 + (s % 7)) * D_ + 12 * H for k in range(bursts_per)]
        bursts[sid] = bl
        pts = []
        t = t_start - 30 * D_
        end = t_start + (bursts_per * 7 + 8) * D_
        base = {}
        while t <= end:
            pts.append((t, float(np.clip(0.30 + rng.normal(0, 0.01), 0.06, 0.58)), 50.0))
            t += 900.0
        for b in bl:
            base[b] = drift
        pts = [(t, p + (drift if any(b <= t <= b + 2 * H for b in bl) else 0.0), sz) for t, p, sz in pts]
        txs[mid] = mk_tx(pts)
        m = {"market_id": mid, "event_id": f"e{s}", "created_epoch": t_start - 40 * D_, "end_epoch": end + 5 * D_, "fee_rate": 0.04, "yes_index": 0, "cls": "resign", "subject": sid}
        markets[mid] = m
        by_subject[sid] = [m]
        subjects[sid] = {"entity": f"E{s}", "canonical": f"E{s}", "description": "British politician" if s % 2 else "French politician", "country": "GB" if s % 2 else "FR", "head": False, "n_markets": 1, "attn": s == 0}
        pages[sid] = {"fetch_start": t_start - 70 * D_, "first_rev_ts": t_start - 500 * D_, "n_rev": 100, "status": "ok"}
    return {"subjects": subjects, "by_subject": by_subject, "markets": markets, "txs": txs, "bursts": bursts, "pages": pages, "burst_info": {}, "frame_rows": []}


def test_w2_units_labels_and_columns():
    D = mk_D(n_sub=3, bursts_per=4)
    pk = w.w2_units(D)
    assert len(pk["units"]) == 12 and pk["labels"]["unit"] == 12
    u = pk["units"][0]
    assert set(u) >= {"subject", "b", "e", "x", "net", "size", "state", "state_prev", "rise", "week", "story", "market_id", "stale"}
    assert u["story"].endswith(("|FR", "|GB")) and 0.05 <= u["state"] <= 0.60
    # uncovered market -> counted, and part of the worst-case set
    D2 = mk_D(n_sub=2, bursts_per=2)
    D2["txs"]["m0"].truncated, D2["txs"]["m0"].oldest_ts = True, D2["bursts"]["p0"][-1] + 10 * D_
    pk2 = w.w2_units(D2)
    assert pk2["labels"].get("uncovered", 0) >= 1 and any(a["why"] == "uncovered" for a in pk2["would_be"])
    # a burst whose 2 h 30 min window ends at or after T14_W_END is outside the calendar
    D3 = mk_D(n_sub=1, bursts_per=1)
    D3["bursts"]["p0"] = [w.w_end() - 3600]
    assert w.w2_units(D3)["labels"]["outside calendar"] == 1


def test_proxy_writes_only_clustered_se_never_a_point_estimate():
    D = mk_D(n_sub=40, bursts_per=6)
    prox = w.proxy_se(w.proxy_units(D))
    assert set(prox) == {"n", "se_max_over_ways", "mde"} and prox["n"] > 100 and prox["mde"] == pytest.approx(3.16 * 1.2 * prox["se_max_over_ways"])
    assert not any("mean" in k or "net" in k or "estimate" in k for k in prox)


def test_w2_test_pipeline_structure_and_checks():
    D = mk_D(n_sub=40, bursts_per=20, drift=0.04)
    r = w.w2_test(D)
    assert r["n"] == 800 and r["testable"] and r["p"] <= 1.0 and set(r["ways"]) == {"subject", "week", "story"}
    for k in ("pre_burst_placebo", "before_the_move", "worst_case_reach", "cost_plus_1c_per_side", "exit_1h", "band_05_40", "entry_window_3_15", "drop_cb11a_entities", "drop_stale_exit",
              "top5_subject", "top5_week", "top5_story", "loqo_sign", "halves_sign"):
        assert k in r["checks"], k
    assert isinstance(r["checks_met"], bool) and r["checks"]["drop_cb11a_entities"]["n_dropped"] == 20
    fin = w.finish(dict(r), w.W2_FLOOR)
    assert fin["advance"] is (bool(r["testable"]) and r["p"] < 0.01 and r["effect"] >= 0.01 and r["checks_met"])
    # flat prices: no edge, W2 does not advance (fees alone make the round trip lose)
    flat = w.w2_test(mk_D(n_sub=40, bursts_per=20, drift=0.0))
    assert flat["effect"] < 0 and not w.finish(dict(flat), w.W2_FLOOR)["advance"]


def test_w2_pre_burst_placebo_check_uses_shifted_rule_time():
    D = mk_D(n_sub=5, bursts_per=3)
    shifted = w.w2_units(D, shift_s=w.PREBURST_SHIFT_S)["units"]
    plain = w.w2_units(D)["units"]
    assert shifted and all(abs(u["t"] - (u["b"] - w.PREBURST_SHIFT_S)) < 1e-6 for u in shifted) and len(plain) == 15


# =====================================================================================================================================================
# W1 pipeline
# =====================================================================================================================================================


def mk_D_w1(n_sub=40, led_every=2, extra_bursts=None):
    """``n_sub`` subjects with one decisive move each, spaced 10 days apart; every ``led_every``-th subject has a burst 30 min before its D0."""
    subjects, by_subject, markets, txs, bursts, pages = {}, {}, {}, {}, {}, {}
    first = ep("2025-02-03T12:00:00Z")
    for s in range(n_sub):
        d0 = first + s * 10 * D_
        sid, mid = f"p{s}", f"m{s}"
        txs[mid] = mk_tx(move_path(d0))
        bursts[sid] = sorted(([d0 - 1800] if s % led_every == 0 else []) + list((extra_bursts or {}).get(s, [])))
        m = {"market_id": mid, "event_id": f"e{s}", "created_epoch": d0 - 80 * H, "end_epoch": d0 + 30 * D_, "fee_rate": 0.04, "yes_index": 0, "cls": "resign", "subject": sid}
        markets[mid], by_subject[sid] = m, [m]
        subjects[sid] = {"entity": f"E{s}", "canonical": f"E{s}", "description": "French politician", "country": "FR", "head": False, "n_markets": 1, "attn": s == 0}
        pages[sid] = {"fetch_start": d0 - 120 * D_, "first_rev_ts": d0 - 900 * D_, "n_rev": 10, "status": "ok"}
    return {"subjects": subjects, "by_subject": by_subject, "markets": markets, "txs": txs, "bursts": bursts, "pages": pages, "burst_info": {}, "frame_rows": []}


def test_w1_units_age_rule_and_moves():
    D = mk_D_w1(5)
    units, info = w.w1_units(D)
    assert len(units) == 5 and units[0]["D0"] == ep("2025-02-03T12:00:00Z")
    D["pages"]["p0"]["first_rev_ts"] = D["markets"]["m0"]["created_epoch"] + 0  # the article is created by the event: too new
    units, info = w.w1_units(D)
    assert len(units) == 4 and info["article too new"] == 1


def test_w1_test_pipeline_advances_on_a_planted_lead_and_not_on_nothing():
    D = mk_D_w1(40)
    r = w.w1_test(D, n_draws=12)
    assert r["testable"] and r["effect"] == pytest.approx(0.5) and r["p"] < 0.01 and r["n"] == 40
    for k in ("lead_window_60_5", "state_cap_2c", "entry_window_3_15", "drop_cb11a_entities", "drop_heads_of_government", "class_resign", "class_out_as", "half_first", "half_second", "top5_subject", "top5_week"):
        assert k in r["checks"], k
    assert r["placebo"]["n_draws"] == 12 and r["placebo_ok"] and r["checks_met"]
    fin = w.finish(dict(r), w.W1_FLOOR, placebo_key="placebo_ok")
    assert fin["advance"] and fin["verdict"] == "advance to Stage 2" and "reported" in r
    none = w.w1_test(mk_D_w1(40, led_every=10_000_000, extra_bursts=None), n_draws=5)
    assert none["effect"] < w.W1_FLOOR and not w.finish(dict(none), w.W1_FLOOR, placebo_key="placebo_ok")["advance"]


def test_w1_hot_period_comparator_absorbs_a_story_that_is_already_hot():
    # every subject has bursts in all hot-period windows as well as before D0: the excess over the hot rate is ~0 and W1 does not advance
    hot = {s: [d - 6 * H * k - 3600 for d in [ep("2025-02-03T12:00:00Z") + s * 10 * D_] for k in range(1, 12)] for s in range(40)}
    r = w.w1_test(mk_D_w1(40, led_every=1, extra_bursts=hot), n_draws=5)
    assert r["effect"] == pytest.approx(0.0, abs=1e-9)
    assert not w.finish(dict(r), w.W1_FLOOR, placebo_key="placebo_ok")["advance"]


def test_w1_gates_not_testable_below_forty_moves():
    D = mk_D_w1(39)
    units, _ = w.w1_units(D)
    pk = w.w2_units(D)
    g = w.gates_w(D, units, pk, {"mde": None})
    assert not g["GW_W1"]["pass"] and g["GW_W1"]["usable_moves"] == 39
    D40 = mk_D_w1(40)
    u40, _ = w.w1_units(D40)
    g40 = w.gates_w(D40, u40, w.w2_units(D40), {"mde": None})
    assert g40["GW_W1"]["pass"] and g40["GWP_W1"]["pass"] and g40["GWP_W1"]["mde"] == pytest.approx(3.16 * 1.2 * 0.5 / math.sqrt(min(40, 40)))
    assert w.mde_w1(10) > w.GWP_W1_MAX_MDE  # a small G fails the power gate (MDE above twice the floor)


# =====================================================================================================================================================
# Live poller (q0310): overlap, continuation, de-duplication inputs, gaps, bot/revert rules, window
# =====================================================================================================================================================


class FakeWiki:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get(self, url, params):
        self.calls.append(dict(params))
        if not self.pages:
            raise RuntimeError("give up")
        p = self.pages.pop(0)
        if isinstance(p, tuple):
            return p
        return 200, p


def rcrec(rcid, ts, user="U1", old=1000, new=1060, page=7, tags=(), comment=""):
    return {"type": "edit", "ns": 0, "title": "X", "pageid": page, "rcid": rcid, "revid": rcid * 10, "oldlen": old, "newlen": new, "timestamp": iso(ts), "user": user, "userid": 100 + int(user[1:]), "tags": list(tags), "comment": comment}


def test_rc_params_carry_start_namespace_and_maxlag_and_no_mw_reverted():
    p = w.rc_params(ep("2026-10-26T00:00:00Z"), {"rccontinue": "x|1"})
    assert p["list"] == "recentchanges" and p["rcnamespace"] == 0 and p["rclimit"] == 500 and p["rcdir"] == "newer" and p["maxlag"] == w.MW_MAXLAG
    assert p["rcstart"] == "2026-10-26T00:00:00Z" and p["rccontinue"] == "x|1"
    assert "mw-reverted" not in json.dumps(p)


def test_poll_follows_rccontinue_to_exhaustion_and_reports_oldest_newest():
    t0 = ep("2026-10-26T01:00:00Z")
    fw = FakeWiki([{"query": {"recentchanges": [rcrec(1, t0)]}, "continue": {"rccontinue": "a|2"}}, {"query": {"recentchanges": [rcrec(2, t0 + 30)]}}])
    out = w.poll_recent_changes(fw, t0 - 120)
    assert out["ok"] and len(out["changes"]) == 2 and out["oldest"] == t0 and out["newest"] == t0 + 30
    assert fw.calls[1]["rccontinue"] == "a|2"


def test_poll_failure_is_not_an_exception_and_marks_the_poll_not_ok():
    out = w.poll_recent_changes(FakeWiki([(503, {})]), 0.0)
    assert out["ok"] is False and out["changes"] == []
    out = w.poll_recent_changes(FakeWiki([(200, {"error": {"code": "maxlag"}})]), 0.0)
    assert out["ok"] is False
    # a continuation that never ends is a failed poll, not an infinite loop
    loop = FakeWiki([{"query": {"recentchanges": []}, "continue": {"rccontinue": "z"}}] * 30)
    assert w.poll_recent_changes(loop, 0.0, max_batches=5)["ok"] is False


def _chg(rcid, ts, uk, delta=60.0, bot=0, revert=0):
    return {"rcid": rcid, "page_id": "7", "rc_ts": ts, "delta": delta, "uk": uk, "bot": bot, "revert": revert}


def test_live_burst_rule_edges_refractory_gap_and_threshold():
    b = ep("2026-10-27T00:00:00Z")
    three = [_chg(1, b - 300, "a"), _chg(2, b - 200, "b"), _chg(3, b, "a")]
    assert w.live_burst_check(three, three[-1], 3.0, -math.inf, [])["status"] == "ok"
    assert w.live_burst_check(three, three[-1], 4.0, -math.inf, []) is None  # below the causal 99th percentile
    assert w.live_burst_check(three, three[-1], None, -math.inf, []) is None  # no baseline: no burst
    one_user = [_chg(1, b - 300, "a"), _chg(2, b - 200, "a"), _chg(3, b, "a")]
    assert w.live_burst_check(one_user, one_user[-1], 3.0, -math.inf, []) is None
    small = [_chg(1, b - 300, "a", 10), _chg(2, b - 200, "b", 10), _chg(3, b, "a", 10)]
    assert w.live_burst_check(small, small[-1], 3.0, -math.inf, []) is None  # 30 bytes < 100
    assert w.live_burst_check(three, three[-1], 3.0, b - 3600, []) is None  # 6 h refractory
    assert w.live_burst_check(three, three[-1], 3.0, b - 7 * 3600, [])["status"] == "ok"
    bot = [_chg(1, b - 300, "a"), _chg(2, b - 200, "b"), _chg(3, b, "c", bot=1)]
    assert w.live_burst_check(bot, bot[-1], 3.0, -math.inf, []) is None
    assert w.live_burst_check(three, three[-1], 3.0, -math.inf, [(b - 400, b - 350)])["status"] == "unavailable (gap)"
    assert w.live_burst_check(three, three[-1], 3.0, -math.inf, [(b - 5000, b - 4000)])["status"] == "ok"


def test_norm_change_pseudonymises_users_per_salt_and_treats_hidden_as_unknown():
    t = ep("2026-10-27T00:00:00Z")
    a = w.norm_change(rcrec(1, t, "U1"), set(), b"s1")
    b = w.norm_change(rcrec(2, t, "U1"), set(), b"s2")
    assert a["uk"] and a["uk"] != b["uk"] and "user" not in a and "U1" not in json.dumps(a)
    hid = rcrec(3, t, "U2")
    hid["userhidden"] = True
    h = w.norm_change(hid, set(), b"s1")
    assert h["unknown_user"] == 1 and h["uk"] == ""
    rv = w.norm_change(rcrec(4, t, "U3", tags=["mw-undo"]), set(), b"s1")
    assert rv["revert"] == 1


def test_live_window_start_is_max_of_floor_and_freeze_plus_one_day_and_stop_counts_bursts_only(tmp_path):
    floor = ep(w.T14_W2_FLOOR)
    assert w.live_window(None)[0] == floor
    assert w.live_window(floor + 5 * D_)[0] == floor + 6 * D_
    assert w.live_window(floor - 30 * D_)[0] == floor
    assert w.live_window(None)[1] == ep(w.T14_W2_CAP)
    assert w.live_stop_reached(tmp_path, floor, floor + 100 * D_) is False  # no bursts logged
