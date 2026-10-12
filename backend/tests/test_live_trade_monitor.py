"""Live large-trade monitor: dedup, privacy, alert/outcome ordering, immutability, controls."""

from __future__ import annotations

import json
import math

import pytest

from astrolabe.research_lab import live_trade_monitor as ltm

ADDRS = [f"0x{i:040x}" for i in range(1, 40)]
KEY = b"test-key-not-secret"
NOW = 1_800_000_000.0


def trade(i, cid="0xc1", cash=5000.0, addr=None, ts=None, side="BUY", oi=0, price=0.4):
    return {"proxyWallet": addr or ADDRS[i % len(ADDRS)], "side": side, "asset": f"tok{cid}{oi}",
            "conditionId": cid, "size": cash / price, "price": price,
            "timestamp": int((ts or NOW - 30) - i), "outcomeIndex": oi,
            "transactionHash": f"0x{i:064x}", "title": "t", "slug": "s", "name": "NAME",
            "pseudonym": "PSEUDO"}


class FakeLim:
    def __init__(self, feed, flow=None, first=None):
        self.feed, self.flow, self.first = feed, flow or {}, first or {}
        self.requests = self.throttled = 0
        self.urls = []

    def get(self, url, params):
        self.requests += 1
        self.urls.append(url)
        if url.endswith("/trades") and "market" not in params:
            off = params["offset"]
            return 200, self.feed[off: off + params["limit"]]
        if url.endswith("/trades"):
            cid = params["market"]
            return 200, self.flow.get(cid) or [
                {"proxyWallet": ADDRS[(7 * k) % len(ADDRS)], "side": "BUY", "asset": f"tok{cid}0",
                 "size": 100 + k, "price": 0.4, "timestamp": int(NOW - 100 - 60 * k),
                 "outcomeIndex": 0} for k in range(40)]
        if url.endswith("/activity"):
            t = self.first.get(params["user"])
            return 200, [{"timestamp": t}] if t else []
        if url.endswith("/public-profile"):
            return 200, {"createdAt": "2026-10-01T00:00:00Z"}
        if url.endswith("/markets"):
            cid = params["condition_ids"]
            return 200, [{"id": "m" + cid, "bestBid": 0.39, "bestAsk": 0.41, "spread": 0.02,
                          "liquidityNum": 50000, "volume24hr": 1e5, "endDate": "2026-12-01",
                          "oneHourPriceChange": 0.01, "lastTradePrice": 0.4,
                          "clobTokenIds": json.dumps([f"tok{cid}0", f"tok{cid}1"]),
                          "outcomePrices": "[0.4,0.6]", "feeType": "politics",
                          "events": [{"id": "e1"}], "closed": False}]
        return 404, None


@pytest.fixture
def mk(tmp_path):
    def make(feed, **kw):
        lim = FakeLim(feed, **kw)
        cfg = ltm.MonitorConfig(profile=True)
        m = ltm.Monitor(lim, root=tmp_path / "lt", cfg=cfg, key=KEY, clock=lambda: NOW)
        return m, lim
    return make


def all_text(root):
    return "".join(p.read_text() for p in root.rglob("*") if p.is_file())


def test_dedup_across_cycles(mk):
    feed = [trade(i) for i in range(5)]
    m, _ = mk(feed)
    s1 = m.run_cycle()
    assert s1["new_trades"] == 5
    assert m.run_cycle()["new_trades"] == 0  # same feed again
    feed.insert(0, trade(50, ts=NOW - 5))
    assert m.run_cycle()["new_trades"] == 1
    rows = list(ltm.read_jsonl(m.root / f"trades-{ltm._day(NOW)}.jsonl"))
    assert len({r["key"] for r in rows}) == len(rows) == 6
    # a restarted process reloads keys from disk and does not re-store the prints
    m2 = ltm.Monitor(FakeLim(feed), root=m.root, cfg=m.cfg, key=KEY, clock=lambda: NOW)
    assert m2.run_cycle()["new_trades"] == 0


def test_min_cash_filter_and_paging(mk):
    feed = [trade(i, cash=5000) for i in range(600)] + [trade(700, cash=10)]
    m, lim = mk(feed)
    m.cfg.max_pages = 2
    assert m.run_cycle()["new_trades"] == 600
    assert sum(u.endswith("/trades") for u in lim.urls) >= 2


def test_no_raw_address_in_any_output(mk):
    feed = [trade(i, cid=f"0xc{i % 3}") for i in range(12)]
    m, lim = mk(feed, first={a: 1_700_000_000 for a in ADDRS})
    m.cfg.alert_score_min = -99.0  # force alerts and controls
    m.run_cycle()
    text = all_text(m.root).lower()
    for a in ADDRS:
        assert a.lower() not in text
        assert a[2:].lower() not in text
    assert "pseudo" not in text and '"name"' not in text
    assert (m.root / "wallets.jsonl").exists()


def test_alerts_written_with_hash_before_outcomes_and_controls(mk):
    feed = [trade(i, cid=f"0xc{i % 4}", cash=2000 + 10 * i) for i in range(20)]
    first = {a: (NOW - 30 * 86400 if k % 2 else NOW - 600) for k, a in enumerate(ADDRS)}
    m, _ = mk(feed, first=first)
    m.cfg.alert_score_min = -99.0
    m.cfg.max_alerts_per_rule = 3
    m.run_cycle()
    lines = list(ltm.read_jsonl(m.root / "alerts.jsonl"))
    alerts = [x for x in lines if x["type"] == "alert"]
    ctrls = [x for x in lines if x["type"] == "control"]
    assert alerts and ctrls
    frozen = m.registry.entries()
    for a in alerts:
        assert a["rule_sha256"] == frozen[a["rule_id"]]["sha256"]
        assert "outcome" not in json.dumps(a).lower().replace("outcome_index", "")
        assert a["features"] and a["written_utc"]
        assert not (m.root / "outcomes.jsonl").exists()
    for c in ctrls:
        assert c["control_for"] in {a["alert_id"] for a in alerts}
        assert c["features"]["wallet_age_h"] >= ltm.NEW_DAYS * 24
    assert not (m.root / "outcomes.jsonl").exists()


def test_outcome_writer_never_mutates_alerts(mk, tmp_path):
    feed = [trade(i, cid=f"0xc{i % 4}") for i in range(12)]
    m, _ = mk(feed, first={a: NOW - 30 * 86400 for a in ADDRS})
    m.cfg.alert_score_min = -99.0
    m.run_cycle()
    ap = m.root / "alerts.jsonl"
    before = ap.read_bytes()
    assert before

    class Px(FakeLim):
        def get(self, url, params):
            self.requests += 1
            if "prices-history" in url:
                due = (params["startTs"] + params["endTs"]) // 2
                return 200, {"history": [{"t": due + 30, "p": 0.55}]}
            return 200, [{"closed": True, "outcomePrices": "[1,0]"}]

    st = ltm.write_outcomes(Px([]), m.root, now=NOW + 80 * 3600)
    assert st.written > 0
    assert ap.read_bytes() == before
    outs = list(ltm.read_jsonl(m.root / "outcomes.jsonl"))
    ev = [o for o in outs if o.get("status") == "evaluated"]
    assert {o["horizon_h"] for o in ev} == {1, 6, 24, 72}
    assert all(math.isclose(o["move_outcome0"], 0.55 - o["mid_at_receipt"]) for o in ev)
    assert any(o["what"] == "resolution" and o["resolved_outcome0"] == 1.0 for o in outs)
    # idempotent: a second pass writes nothing new
    assert ltm.write_outcomes(Px([]), m.root, now=NOW + 80 * 3600).written == 0
    assert ap.read_bytes() == before


def test_outcomes_not_due_stay_pending(mk):
    m, _ = mk([trade(i, cid=f"0xc{i % 4}") for i in range(8)],
              first={a: NOW - 30 * 86400 for a in ADDRS})
    m.cfg.alert_score_min = -99.0
    m.run_cycle()

    class Never(FakeLim):
        def get(self, url, params):
            raise AssertionError("no request should be needed")

    st = ltm.write_outcomes(Never([]), m.root, now=NOW + 60)
    assert st.written == 0 and st.pending > 0


def row(key, cid, cat, cash, wh, age):
    return {"key": key, "condition_id": cid, "category": cat, "cash": cash, "wallet_hash": wh,
            "wallet_age_h": age}


def test_control_selection():
    a = row("a", "m1", "pol", 5000, "wa", 1.0)
    pool = [a,
            row("same_market", "m1", "pol", 5000, "w1", 900),
            row("other_cat", "m2", "sports", 5000, "w2", 900),
            row("too_big", "m3", "pol", 50000, "w3", 900),
            row("fresh", "m4", "pol", 5000, "w4", 2.0),
            row("unknown_age", "m5", "pol", 5000, "w5", None),
            row("same_wallet", "m6", "pol", 5000, "wa", 900),
            row("ok1", "m7", "pol", 6000, "w7", 900),
            row("ok2", "m8", "pol", 3000, "w8", 400)]
    c, why = ltm.select_control(a, pool)
    assert why == "ok" and c["key"] in {"ok1", "ok2"}
    assert ltm.select_control(a, pool)[0]["key"] == c["key"]  # deterministic
    c2, _ = ltm.select_control(a, pool, exclude={c["key"]})
    assert c2["key"] != c["key"]
    none, why = ltm.select_control(a, pool[:7])
    assert none is None and why == "no_control_available"


def test_total_cap_stops(mk):
    m, _ = mk([trade(1)])
    m.cfg.total_cap_bytes = 1
    (m.root / "x.jsonl").write_text("data")
    with pytest.raises(ltm.CapReached):
        m.run_cycle()


def test_day_cap_pauses(mk):
    m, _ = mk([trade(1)])
    m.cfg.day_cap_bytes = 1
    (m.root / f"trades-{ltm._day(NOW)}.jsonl").write_text("xx")
    assert m.run_cycle()["status"] == "day_cap"
