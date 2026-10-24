# ruff: noqa: E501
"""CB7 fetch side (astrolabe.research_lab.cb7_common / cb7_text / cb7_geo / cb7_seal, scripts/run_cb7.py;
docs/research_lab/CREATIVE_BATCH_7.md CB7-F, CB7-S, CB7-G). Everything runs against a fake Gamma/Data API: no network."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from astrolabe.research_lab import cb6_tail as c6
from astrolabe.research_lab import cb7_common as cm
from astrolabe.research_lab import cb7_geo as cg
from astrolabe.research_lab import cb7_seal as cs
from astrolabe.research_lab import cb7_text as ct
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb7 as script  # noqa: E402

DAY = 86400
NOW = datetime(2026, 10, 17, 12, tzinfo=UTC).timestamp()
CUTOFF = NOW - 7 * DAY
END_FROM = "2026-04-01"
GEO_FROM = "2026-04-01"


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=UTC).timestamp()


def iso(x: float) -> str:
    return datetime.fromtimestamp(x, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def gm(mid, end, *, created=None, closed=False, event=None, neg="", series=(), desc="plain description", q=None, fee=None,
       tags=("100265", "7"), event_title=None, close_at=None, group_title=None, other=False, outcomes='["Yes","No"]'):
    cr = created if created is not None else end - 40 * DAY
    close_t = close_at if close_at is not None else end + 3600
    return {"id": str(mid), "conditionId": f"c{mid}", "clobTokenIds": json.dumps([f"tok{mid}a", f"tok{mid}b"]),
            "createdAt": iso(cr), "startDate": iso(cr), "endDate": iso(end), "closed": closed,
            "closedTime": iso(close_t) if closed else None, "question": q or f"Will thing {mid} happen?", "slug": f"thing-{mid}",
            "description": desc, "feeType": fee, "outcomes": outcomes, "outcomePrices": '["0.04","0.96"]' if closed else None,
            "umaResolutionStatus": "resolved" if closed else "", "volumeNum": 20000.0, "liquidityNum": 55.5, "negRisk": bool(neg),
            "negRiskMarketID": neg or None, "negRiskOther": other, "groupItemTitle": group_title,
            "tags": [{"id": "55"}],
            "events": [{"id": str(event if event is not None else f"E{mid}"), "title": event_title or f"event {mid}",
                        "series": [{"id": str(s)} for s in series], "tags": [{"id": t, "label": "x"} for t in tags]}]}


def prints_for(cid, t7, *, n=6, price=0.30, idx=0, spacing=3600):
    """Prints at t7 - spacing * i (strictly before t7), plus one planted at t7 (must never be used)."""
    out = [{"timestamp": int(t7 - spacing * (i + 1)), "side": "BUY", "size": 10.0, "price": price, "outcomeIndex": idx,
            "proxyWallet": f"0xwallet_{cid}_{i}", "transactionHash": f"h{cid}{i}", "asset": "a"} for i in range(n)]
    out.append({"timestamp": int(t7), "side": "BUY", "size": 999.0, "price": 0.99, "outcomeIndex": 0,
                "proxyWallet": "0xplanted", "transactionHash": f"hp{cid}", "asset": "a"})
    return out


class FakeApi:
    """Gamma /markets (windows, tag filter, id lookups), /tags/slug, Data /trades. Any CLOB prices-history call is a bug."""

    def __init__(self, markets, trades=None, *, fail_cids=(), slug_id="100265"):
        self.markets = {m["id"]: m for m in markets}
        self.trades = trades or {}
        self.fail_cids = set(fail_cids)
        self.slug_id = slug_id
        self.log: list[tuple[str, dict]] = []
        self.hooks = []

    def __call__(self, url, params):
        if "prices-history" in url:
            raise AssertionError("CB7 must not call CLOB prices-history")
        if "/tags/slug/" in url:
            kind = "tag"
        elif url.endswith("/markets"):
            kind = "gamma_ids" if "id" in params else "gamma_window"
        else:
            kind = "trades"
        self.log.append((kind, dict(params)))
        for h in self.hooks:
            h(kind, params)
        if kind == "tag":
            return 200, json.dumps({"id": self.slug_id, "slug": "geopolitics"}).encode(), {}
        if kind == "gamma_ids":
            want = [str(x) for x in params["id"]]
            closed = params.get("closed")
            out = [self.markets[i] for i in want if i in self.markets and (closed == "true" or not self.markets[i]["closed"])
                   and self.markets[i].get("hide") is not True]
            return 200, json.dumps(out).encode(), {}
        if kind == "gamma_window":
            lo, hi = ep(params["end_date_min"]), ep(params["end_date_max"])
            closed = params["closed"] == "true"
            rows = [m for m in self.markets.values() if m["closed"] == closed and lo <= ep(m["endDate"]) < hi]
            if "tag_id" in params:
                rows = [m for m in rows if any(t["id"] == str(params["tag_id"]) for t in m["events"][0]["tags"])]
            rows.sort(key=lambda m: int(m["id"]))
            off, lim = int(params["offset"]), int(params["limit"])
            return 200, json.dumps(rows[off:off + lim]).encode(), {}
        assert params["takerOnly"] == "true" and "offset" not in params
        cid = params["market"]
        if cid in self.fail_cids:
            return 500, b"", {}
        rows = [x for x in self.trades.get(cid, []) if int(params["start"]) <= x["timestamp"] <= int(params["end"])]
        rows.sort(key=lambda x: -x["timestamp"])
        return 200, json.dumps(rows[:int(params["limit"])]).encode(), {}

    def kinds(self, kind):
        return [p for k, p in self.log if k == kind]


def write_sample(path: Path, ids):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["market_id", "token0", "end_epoch", "closed", "created_at", "close_epoch", "start_epoch", "fee_category", "volume"])
        for i in ids:
            w.writerow([i, f"tok{i}a", ep("2025-06-15T00:00:00Z"), 1, "2025-05-01T00:00:00Z", ep("2025-06-15T00:00:00Z"),
                        ep("2025-05-01T00:00:00Z"), "", 20000.0])


def write_seal_copy(path: Path, ids):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"run_id": path.stem.replace("_SEAL", ""), "files": {f"prices/{i}.csv.gz": "x" for i in ids}, "listing_sha256": "x"}))


def window_epochs(day: date, seed: str, wpd: int = 5) -> list[float]:
    d0, picks = cm.pick_windows(day, seed, CUTOFF, wpd, 15)
    return [(d0 + timedelta(minutes=k * 15)).timestamp() for k in picks]


def day_list(first: str, n: int) -> list[date]:
    d0 = datetime.fromisoformat(first).date()
    return [d0 + timedelta(days=i) for i in range(n)]


class World:
    """Exclusion files with pins, a rules file, smoke result, exclusion keys, markets and a FakeApi in a tmp dir."""

    def __init__(self, tmp: Path, *, n_missing_meta=0, text_extra=(), geo_extra=(), n_markets=1000, fail_cids=()):
        self.tmp = tmp
        self.root = tmp / "history"
        self.seals = tmp / "seals"
        self.dd = tmp / "dd"
        self.n_markets = n_markets
        h1, h2, h3 = ([f"9{i:03d}" for i in range(a, a + 10)] for a in (0, 10, 20))
        h5, h5l = [f"9{i:03d}" for i in range(30, 33)], [f"9{i:03d}" for i in range(33, 36)]
        write_sample(self.root / "h1_first" / "sample.csv.gz", h1)
        write_sample(self.root / "h2_main" / "sample.csv.gz", h2)
        write_sample(self.root / "h3_power" / "sample.csv.gz", h3)
        write_seal_copy(self.seals / "h5_cb1_SEAL.json", h5)
        write_seal_copy(self.seals / "h5_cb1_ladders_SEAL.json", h5l)
        self.excl_ids = h1 + h2 + h3 + h5 + h5l
        self.pins = []
        for name, kind, rel in (("h1_first", "sample", "h1_first/sample.csv.gz"), ("h2_main", "sample", "h2_main/sample.csv.gz"),
                                ("h3_power", "sample", "h3_power/sample.csv.gz"), ("h5_cb1", "seal", "h5_cb1_SEAL.json"),
                                ("h5_cb1_ladders", "seal", "h5_cb1_ladders_SEAL.json")):
            p = (self.root if kind == "sample" else self.seals) / rel
            self.pins.append({"name": name, "kind": kind, "path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        self.rules = tmp / "cb7_rules.json"
        self.rules.write_text(json.dumps(cm.rules_file_doc(self.pins), indent=1, sort_keys=True))
        self.rules_sha = json.loads(self.rules.read_text())["rules_sha256"]
        self.smoke = tmp / "smoke.json"
        self.write_smoke(a=True, b=True, c=True)
        far = ep("2025-06-15T00:00:00Z")
        ex = []
        for i, mid in enumerate(self.excl_ids):
            kw = {"event": 900} if mid == "9000" else {"neg": "NR1", "event": 901} if mid == "9001" else {"series": [77], "event": 902} if mid == "9002" else {}
            m = gm(mid, far, closed=(i % 2 == 0), **kw)
            if i < n_missing_meta:
                m["hide"] = True
            ex.append(m)
        self.special: dict[str, str] = {}
        self.text_markets = self._text_markets()
        self.geo_markets = self._geo_markets()
        trades = {}
        for m in self.text_markets + self.geo_markets:
            if m["id"] in self.special.get("no_prints", ()):
                continue
            end = ep(m["endDate"])
            for k in (30, 14, 7):
                trades.setdefault(m["conditionId"], []).extend(prints_for(m["conditionId"], end - k * DAY, n=4 + (k % 5), price=0.06 if m["id"] in self.special.get("geo_ids", ()) else 0.30))
        self.api = FakeApi(ex + self.text_markets + self.geo_markets + list(text_extra) + list(geo_extra), trades, fail_cids=fail_cids)

    def write_smoke(self, *, a, b, c):
        self.smoke.write_text(json.dumps({"smoke_version": cm.SMOKE_VERSION, "rules_sha256": self.rules_sha,
                                          "criterion_a_slug_resolves_to_pinned_id": a, "criterion_b_bounds_and_order": b,
                                          "criterion_c_coverage": c, "pass": a and b and c}))

    def _text_markets(self) -> list[dict]:
        out = []
        nid = 100000
        days = day_list(END_FROM, 190)
        for di, d in enumerate(days):
            if di % 6 != 0:
                continue
            s = window_epochs(d, cm.TEXT_SEED)[0]
            for j in range(3):
                nid += 1
                out.append(gm(nid, s + j * 60, desc="Resolves per the official source and must be before 5:00 PM ET. See https://example.com."))
            if di == 12:
                self.special.update(sports=str(nid))
                out.append(gm(nid + 1, s + 200, fee="sports"))
                out.append(gm(nid + 2, s + 260, q="Will the war in Ukraine end?"))  # geopolitics by topic: excluded
                out.append(gm(nid + 3, s + 320, q="Highest temperature in Paris on April 3?", fee="weather"))
                out.append(gm(nid + 4, s + 380, neg="NRX", event=5001, other=True))  # Other placeholder
                out.append(gm(nid + 5, s + 440, outcomes='["Up","Down"]'))
                out.append(gm(nid + 6, s + 500, event=900))  # event key shared with an excluded market
                out.append(gm(nid + 7, s + 560, desc="x" * 4500 + " Update: clarified later by 10 pm ET"))  # long text, marker past 4000
                self.special.update(long_text=str(nid + 7), event_sib=str(nid + 6), geopol=str(nid + 2), weather=str(nid + 3),
                                    other=str(nid + 4), nonbinary=str(nid + 5))
                nid += 7
            if di == 18:  # closed only after the cap: censored, outcome blank
                out.append(gm(nid + 1, s + 120, closed=True, close_at=NOW + 500))
                self.special["after_cap"] = str(nid + 1)
                out.append(gm(nid + 2, s + 180))
                self.special["no_prints"] = (str(nid + 2),)
                nid += 2
            if di == 24:  # closed markets (ended and resolved before the cap)
                out.append(gm(nid + 1, s + 100, closed=True))
                out.append(gm(nid + 2, s + 160, closed=True))
                nid += 2
        for m in out:  # text markets are not geopolitics-tagged
            m["events"][0]["tags"] = [{"id": "7", "label": "x"}]
        return out

    def _geo_markets(self) -> list[dict]:
        out = []
        nid = 300000
        s0 = ep("2026-06-10T00:00:00Z")
        # event G1: 20 members -> exactly 8 after the cap; event G2: 12 members of which 4 status-quo, 1 excluded id, 1 life<9d
        # and 1 continuous (7 clean ones remain, all under the cap: cap-first would drop some)
        for j in range(20):
            nid += 1
            out.append(gm(nid, s0 + j * 600, event="G1", q=f"Will Russia strike target {j}?", event_title="Russia war"))
        for j in range(12):
            nid += 1
            q = f"Will Iran do act {j}?"
            if j < 4:
                q = f"Will Iran still hold talks {j}?"
            if j == 4:
                q = "Will the oil price in Iran rise?"
            out.append(gm(nid, s0 + 20 * DAY + j * 600, event="G2", q=q, created=(s0 + 20 * DAY - 3 * DAY) if j == 5 else None, event_title="Iran"))
        self.special["g2_first"] = str(nid - 11)
        out.append(gm(9999, s0 + 30 * DAY, event="G2", q="Will Iran test a missile?"))
        self.special["geo_ids"] = tuple(m["id"] for m in out)
        self.special["g1_ids"] = tuple(m["id"] for m in out if m["events"][0]["id"] == "G1")
        self.special["g2_ids"] = tuple(m["id"] for m in out if m["events"][0]["id"] == "G2")
        out.append(gm(nid + 100, s0 + 40 * DAY, event="E-other", tags=("2",), q="Will a team win?"))  # different tag: not walked
        return out

    def keys(self, **kw):
        base = dict(history_root=self.root, seals_dir=self.seals, rules_path=self.rules, pins=self.pins, require_committed=False,
                    rps=4.0, sleep=lambda s: None, live_check=None, now=NOW, wall_clock=lambda: NOW + 3600)
        base.update(kw)
        return cm.exclusion_keys(self.dd / "research_lab", self.api, **base)

    @property
    def keys_path(self) -> Path:
        return self.dd / "research_lab" / "creative_batch7" / "exclusion_keys.csv.gz"

    def common(self, **kw):
        base = dict(history_root=self.root, seals_dir=self.seals, rules_path=self.rules, pins=self.pins, require_committed=False,
                    smoke_path=self.smoke, exclusion_keys_path=self.keys_path, rps=4.0, now=NOW, sleep=lambda s: None,
                    live_check=None, wall_clock=lambda: NOW + 3600, require_smoke=True)
        base.update(kw)
        return base

    def text(self, **kw):
        return ct.text_fetch(self.root, cm.TEXT_RUN_ID, kw.pop("api", None) or self.api,
                             **self.common(n_markets=self.n_markets, end_from=END_FROM, **kw))

    def geo(self, **kw):
        return cg.geo_fetch(self.root, cm.GEO_RUN_ID, kw.pop("api", None) or self.api, **self.common(end_from=GEO_FROM, **kw))

    @property
    def tdir(self) -> Path:
        return self.root / cm.TEXT_RUN_ID

    @property
    def gdir(self) -> Path:
        return self.root / cm.GEO_RUN_ID


def rd(path):
    return list(cm.read_csv_gz(path))


def run_until_terminal(fn, limit=8, **kw):
    for _ in range(limit):
        m = fn(**kw)
        if m.get("status") not in (None, "in_progress"):
            return m
    raise AssertionError("did not reach a terminal state")


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = World(tmp_path_factory.mktemp("w"))
    rep = w.keys()
    assert rep["status"] == cm.KEYS_COMPLETE
    return w


@pytest.fixture(scope="module")
def text_done(world):
    first_trades = []

    def hook(kind, params):
        if kind == "trades" and not first_trades:
            first_trades.append({f: (world.tdir / f).exists() for f in ("origins.csv.gz", "text_features.csv.gz", "cut_points.json", "sample.csv.gz", "frame_report.json")})

    world.api.hooks.append(hook)
    m = world.text()
    world.api.hooks.remove(hook)
    return m, first_trades


@pytest.fixture(scope="module")
def geo_done(world):
    return world.geo()


# ---- rules file and pins -----------------------------------------------------------------------------------------------------------


def test_rules_file_roundtrip_content_and_refusals(tmp_path):
    p = tmp_path / "r.json"
    cm.write_rules(p)
    doc = json.loads(p.read_text())
    assert cm.verify_rules(p, require_committed=False) == doc["rules_sha256"]
    assert doc["seeds"]["text_sample"] == "arepo-h8-text" and doc["seeds"]["geo"] == "arepo-h8-geo" and doc["seeds"]["smoke"] == "arepo-cb7-smoke-v2"
    assert doc["geo"]["tag_id"] == "100265" and doc["geo"]["max_per_event"] == 8 and doc["geo"]["band"] == [0.02, 0.10]
    assert [m["name"][:2] for m in doc["text"]["markers"]] == ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
    assert doc["text"]["markers"][3]["text"] == "question" and doc["text"]["markers"][5]["case_insensitive"] is False
    assert doc["prints"]["clob_history_used"] is False and doc["prints"]["wallets_kept"] is False
    assert doc["text"]["n_markets"] == 18000 and doc["text"]["weights"] == {"sports": 0.25, "other": 1.0}
    assert len(doc["exclusion"]["files"]) == 5 and "h1_first" in doc["exclusion"]["refused_run_ids"]
    assert len(doc["func_sources_sha256"]) >= 25 and len(doc["funcs_sha256"]) == 64
    bad = {**doc, "geo": {**doc["geo"], "band": [0.02, 0.2]}}
    p.write_text(json.dumps(bad))
    with pytest.raises(cm.Refused):
        cm.verify_rules(p, require_committed=False)
    with pytest.raises(cm.Refused):
        cm.verify_rules(tmp_path / "missing.json", require_committed=False)
    with pytest.raises(cm.Refused):  # a rules file is never rewritten
        cm.write_rules(p)


def test_pins_and_clarification_strings_identical_to_cb6():
    assert list(cm.EXCLUSION_PINS) == list(c6.EXCLUSION_PINS)
    assert cm.CLARIFICATION_MARKERS == c6.CLARIFICATION_MARKERS and cm.NOTE_DATE_PATTERN == c6.NOTE_DATE_PATTERN
    assert cm.CLASS_C_PATTERNS == c6.CLASS_C_PATTERNS
    for t in ("Updated: x", "see note: 2026-01-02", "additional context", "plain"):
        assert cm.has_clarification(t) == c6.has_clarification(t)


def test_committed_rules_file_matches_code():
    if not cm.RULES_FILE.exists():
        pytest.skip("rules file not generated yet")
    assert cm.verify_rules(cm.RULES_FILE, require_committed=False)


def test_function_source_change_invalidates_rules(tmp_path, monkeypatch):
    p = tmp_path / "r.json"
    cm.write_rules(p)

    def fake(*a, **k):  # a different function source in the hashed set
        return 1

    orig = cm.rule_funcs
    monkeypatch.setattr(cm, "rule_funcs", lambda: (*orig(), fake))
    with pytest.raises(cm.Refused):
        cm.verify_rules(p, require_committed=False)


# ---- text features ---------------------------------------------------------------------------------------------------------------


def test_markers_each_regex_case_and_fields():
    q = "Will A and B meet?"
    d = "It must be official, according to https://x.org, before 5:30 pm, 11PM ET."
    assert ct.markers(q, d) == [1, 1, 1, 1, 1, 1, 1]
    assert ct.markers("Will A meet?", "nothing") == [0] * 7
    assert ct.markers("Will A meet?", "closes 10 pm et")[5] == 0 and ct.markers("Will A meet?", "closes 10 pm ET")[5] == 1  # M6 case-sensitive
    assert ct.markers("Will A meet?", "must and must and and")[3] == 0  # M4 is read on the question only
    assert ct.markers("Rock & Roll?", "")[3] == 1
    assert ct.markers("q", "no later than 9am")[4] == 1 and ct.markers("q", "by 12:00 p.m.")[4] == 1 and ct.markers("q", "by Friday")[4] == 0
    assert ct.markers("q", "see www.example.org")[6] == 1 and ct.markers("q", "MUST")[0] == 1 and ct.markers("q", "OFFICIALLY")[1] == 1
    assert ct.condition_count(ct.markers("q", "must must must official")) == 2  # types, not occurrences


def test_markers_and_clarification_on_full_text_beyond_4000_chars():
    desc = "x" * 4500 + " this must be official. Note: 2026-03-01. Updated by 10 pm ET"
    f = ct.text_features("Will it?", desc)
    assert f["desc_len"] == len(desc) and f["desc_sha256"] == hashlib.sha256(desc.encode()).hexdigest()
    assert (f["m1"], f["m2"], f["m5"], f["m6"], f["clarified"]) == (1, 1, 1, 1, 1)
    assert f["c"] == 4
    r = ct.text_row(gm(1, NOW - 20 * DAY, desc=desc), NOW)[0]
    assert len(r["description"]) == cm.DESCRIPTION_CHARS and r["desc_len"] == len(desc) and r["c"] == 4 and r["clarified"] == 1


def test_cut_points_text_only_and_stable_under_price_change():
    cs_ = {"politics": [0, 0, 0, 1, 1, 2, 3, 4, 5], "other": [2, 2, 2, 2]}
    out = ct.cut_points(cs_)
    assert out["politics"] == {"n": 9, "c_L": 0, "c_H": 3, "contrast": True}
    assert out["other"]["contrast"] is False and out["other"]["c_L"] == 2 and out["other"]["c_H"] == 2
    assert ct.cut_points(dict(cs_)) == out


# ---- origin price helpers --------------------------------------------------------------------------------------------------------


def lim_for(api):
    return hb.Limiter(api, rps=100.0, sleep=lambda s: None)


def test_origin_prints_one_request_bounds_yes_mapping_and_planted_print():
    t = ep("2026-05-01T00:00:00Z")
    tr = prints_for("cA", t, n=3, price=0.30, idx=1)
    api = FakeApi([], {"cA": tr})
    rows, info = cm.origin_prints(lim_for(api), "cA", t)
    req = api.kinds("trades")
    assert len(req) == 1 and req[0]["start"] == int(t - 7 * DAY) and req[0]["end"] == int(t) - 1 and req[0]["limit"] == 50
    assert req[0]["takerOnly"] == "true" and "offset" not in req[0]
    assert len(rows) == 3 and all(abs(r[1] - 0.70) < 1e-9 for r in rows) and all(r[0] < t for r in rows)  # NO print at 0.30 -> YES 0.70
    assert rows[0][3] == -1 or rows[0][3] == 1
    assert all(len(r) == 4 for r in rows)  # [ts, yes_price, size, yes_side]: no wallet kept
    assert info["n_raw"] == 3 and info["dropped_cap"] == 0


def test_origin_prints_cap_and_window_drops_counted_and_failure_raises():
    t = ep("2026-05-01T00:00:00Z")
    tr = prints_for("cA", t, n=4)
    api = FakeApi([], {"cA": tr})
    rows, info = cm.origin_prints(lim_for(api), "cA", t, cap_epoch=t - 2.5 * 3600)
    assert info["dropped_cap"] == 2 and len(rows) == 2

    class Bad:
        def __call__(self, url, params):
            return 500, b"", {}

    with pytest.raises(RuntimeError):  # a failed request is never "no prints"
        cm.origin_prints(hb.Limiter(Bad(), rps=100.0, sleep=lambda s: None), "cA", t)

    class NotJson:
        def __call__(self, url, params):
            return 200, b'{"x": 1}', {}

    with pytest.raises(cm.ApiError):
        cm.origin_prints(hb.Limiter(NotJson(), rps=100.0, sleep=lambda s: None), "cA", t)


def test_origin_price_vwap24_else_latest_staleness_and_band_edges():
    t = 1_000_000.0
    day_ago = 24 * 3600
    prints = [[t - 3 * 86400, 0.50, 5.0, 1], [t - 2 * 3600, 0.20, 10.0, 1], [t - 1 * 3600, 0.40, 30.0, -1]]
    p = cm.origin_price(prints, t, (0.05, 0.95))
    assert p["m_source"] == "vwap24h" and abs(p["m"] - (0.2 * 10 + 0.4 * 30) / 40) < 1e-12 and p["n_prints_24h"] == 2 and p["eligible"] == 1
    old = [[t - 3 * 86400, 0.50, 5.0, 1], [t - 3 * 86400, 0.70, 15.0, 1], [t - 4 * 86400, 0.10, 1.0, 1]]
    p = cm.origin_price(old, t, (0.05, 0.95))
    assert p["m_source"] == "latest" and abs(p["m"] - (0.5 * 5 + 0.7 * 15) / 20) < 1e-12 and p["staleness_s"] == 3 * 86400
    assert cm.origin_price([[t - day_ago - 1, 0.05, 1.0, 1]], t, (0.05, 0.95))["eligible"] == 1  # band edge 0.05 included
    assert cm.origin_price([[t - 5, 0.96, 1.0, 1]], t, (0.05, 0.95))["eligible"] == 0
    assert cm.origin_price([[t - 5, 0.96, 1.0, 1]], t, (0.05, 0.95))["price_status"] == "out_of_band"
    assert cm.origin_price([[t, 0.5, 1.0, 1]], t, (0.05, 0.95))["price_status"] == "no_print"  # a print at t is never used
    assert cm.origin_price([[t - 8 * 86400, 0.5, 1.0, 1]], t, (0.05, 0.95))["price_status"] == "no_print"
    assert cm.origin_price([], t, (0.02, 0.10))["eligible"] == 0


# ---- smoke ----------------------------------------------------------------------------------------------------------------------


def test_smoke_verdict_and_gate(tmp_path):
    assert cm.smoke_verdict(True, True, True, 10, 14, 20)["pass"] is True
    assert cm.smoke_verdict(True, True, True, 9, 14, 20)["b"] is False  # < 10 non-empty
    assert cm.smoke_verdict(True, True, True, 12, 13, 20)["c"] is False  # coverage 13/20
    assert cm.smoke_verdict(True, False, True, 12, 15, 20)["b"] is False and cm.smoke_verdict(True, True, False, 12, 15, 20)["b"] is False
    assert cm.smoke_verdict(False, True, True, 12, 15, 20) == {"a": False, "b": True, "c": True, "pass": False}
    assert cm.smoke_verdict(True, True, True, 12, 15, 19)["pass"] is False  # fewer than 20 markets
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"smoke_version": cm.SMOKE_VERSION, "rules_sha256": "r", "criterion_a_slug_resolves_to_pinned_id": False,
                             "criterion_b_bounds_and_order": True, "criterion_c_coverage": True}))
    cm.smoke_ok(p, "r", ("b", "c"))  # text may run on an (a) FAIL ...
    with pytest.raises(cm.Refused):  # ... geo may not
        cm.smoke_ok(p, "r", ("a", "b", "c"))
    with pytest.raises(cm.Refused):
        cm.smoke_ok(p, "other", ("b", "c"))
    with pytest.raises(cm.Refused):
        cm.smoke_ok(tmp_path / "none.json", "r", ("b", "c"))


def test_run_smoke_counts_only_and_criteria(tmp_path):
    w = World(tmp_path)
    files = c6.verify_exclusion_files(w.pins, history_root=w.root, seals_dir=w.seals)
    # make every worn exclusion market eligible: 2025 end, >= $10k volume; give each some prints in [end-14d, end-7d-1]
    end = ep("2025-06-15T00:00:00Z")
    tr = {}
    for mid in w.excl_ids:
        tr[f"c{mid}"] = [{"timestamp": int(end - 10 * DAY + i), "side": "BUY", "size": 1.0, "price": 0.4, "outcomeIndex": 0, "proxyWallet": "0xw",
                          "transactionHash": f"t{mid}{i}", "asset": "a"} for i in range(3)]
    w.api.trades.update(tr)
    res = cm.run_smoke(lim_for(w.api), files, w.pins, w.rules_sha)
    assert res["criterion_a_slug_resolves_to_pinned_id"] is True and res["counts_only"] is True
    # 36 worn markets, all in 2025: pool 36, first 20 requested; coverage 20/20, bounds and newest-first hold
    assert res["n_requested"] == 20 and res["n_covered"] == 20 and res["pass"] is True
    blob = json.dumps(res)
    assert "tok" not in blob and "Will thing" not in blob  # no id, price, text or timestamp kept
    w.api.slug_id = "1"
    assert cm.run_smoke(lim_for(w.api), files, w.pins, w.rules_sha)["criterion_a_slug_resolves_to_pinned_id"] is False
    w.api.trades.clear()
    low = cm.run_smoke(lim_for(w.api), files, w.pins, w.rules_sha)
    assert low["criterion_c_coverage"] is False and low["pass"] is False


def test_smoke_cli_is_write_once(tmp_path, capsys):
    out = tmp_path / "smoke.json"
    out.write_text("{}")
    rc = script.main(["smoke", "--out", str(out), "--rules", str(tmp_path / "x.json"), "--standalone"])
    assert rc == 2 and "write-once" in capsys.readouterr().out and out.read_text() == "{}"
    rc = script.main(["smoke", "--out", str(tmp_path / "new.json"), "--n", "5", "--standalone"])
    assert rc == 2  # declared argument changed
    assert not (tmp_path / "new.json").exists()


# ---- exclusion keys ---------------------------------------------------------------------------------------------------------------


def test_exclusion_keys_report_and_h1_first_in_refusal_list(world):
    rep = json.loads((world.keys_path.with_name(cm.EXCLUSION_REPORT_NAME)).read_text())
    assert rep["n_ids"] == len(world.excl_ids) == 36 and rep["n_missing"] == 0 and rep["disjointness"] == "verified"
    assert rep["keys"]["event"] >= 3 and rep["keys"]["neg_risk_market"] == 1 and rep["keys"]["series"] == 1
    assert "h1_first" in cm.REFUSED_RUN_IDS and "h8_tail" in cm.REFUSED_RUN_IDS
    with pytest.raises(cm.Refused):
        cm.refuse_run_id("h1_first", cm.TEXT_RUN_ID)
    with pytest.raises(cm.Refused):
        cm.refuse_run_id("h2_main", cm.TEXT_RUN_ID)
    with pytest.raises(cm.Refused):
        cm.refuse_run_id("h8_geo", cm.TEXT_RUN_ID)
    with pytest.raises(cm.Refused):
        cm.refuse_path(Path("/x/cb4_extract/y"))
    with pytest.raises(cm.Refused):
        cm.refuse_path(Path("/x/cross_venue_live"))


def test_exclusion_keys_unverified_over_two_percent(tmp_path):
    w = World(tmp_path, n_missing_meta=8)
    assert w.keys()["status"] == cm.UNVERIFIED_TOKEN
    m = w.text()  # fetchers end in the terminal state, no sample, no prints
    assert m["status"] == cm.UNVERIFIED_TOKEN and not (w.tdir / "sample.csv.gz").exists() and not w.api.kinds("trades")
    assert (w.tdir / cm.UNVERIFIED_FILE).exists()
    assert w.text()["status"] == cm.UNVERIFIED_TOKEN  # sticky


@pytest.mark.parametrize("which", ["h1_first", "h2_main", "h3_power", "h5_cb1", "h5_cb1_ladders"])
@pytest.mark.parametrize("mode", ["missing", "changed"])
def test_any_exclusion_file_missing_or_changed_refuses_before_any_request(tmp_path, which, mode):
    w = World(tmp_path)
    pin = next(p for p in w.pins if p["name"] == which)
    path = (w.root if pin["kind"] == "sample" else w.seals) / pin["path"]
    if mode == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(cm.Refused):
        w.keys()
    with pytest.raises(cm.Refused):
        w.text()
    with pytest.raises(cm.Refused):
        w.geo()
    assert not w.api.log and not (w.tdir / "manifest.json").exists()


def test_fetch_refusals_keys_file_smoke_runids_and_headroom(tmp_path):
    w = World(tmp_path)
    with pytest.raises(cm.Refused):  # no exclusion key file yet
        w.text()
    w.keys()
    w.write_smoke(a=True, b=False, c=True)
    with pytest.raises(cm.Refused):
        w.text()
    with pytest.raises(cm.Refused):
        w.geo()
    w.write_smoke(a=False, b=True, c=True)  # (a) FAIL blocks geo only
    with pytest.raises(cm.Refused):
        w.geo()
    kp = w.keys_path
    kp.write_bytes(kp.read_bytes() + b"x")  # key file no longer matches its report hash
    with pytest.raises(cm.Refused):
        w.text()
    for rid in ("h1_first", "h2_main", "h3_power", "h5_cb1", "h7_cb4_era", "h6_weather", "h8_tail", "h4_seal"):
        with pytest.raises(cm.Refused):
            cm.refuse_run_id(rid, cm.TEXT_RUN_ID)
    w2 = World(tmp_path / "b")
    w2.keys()
    (tmp_path / "dd2").mkdir()
    (tmp_path / "dd2" / "big.bin").write_bytes(b"0" * 2_000_000)
    n = len(w2.api.log)
    with pytest.raises(cm.NotNow):
        w2.text(data_dumps=tmp_path / "dd2", data_dumps_cap_gb=0.001)
    with pytest.raises(cm.NotNow):
        w2.geo(data_dumps=tmp_path / "dd2", data_dumps_cap_gb=0.001)
    assert len(w2.api.log) == n


# ---- h8_text end to end ------------------------------------------------------------------------------------------------------------


def test_text_fetch_complete_and_files(world, text_done):
    m, first = text_done
    assert m["status"] == cm.TEXT_COMPLETE and m["complete"] is True and m["stopped"] is None
    assert m["rules_sha256"] == world.rules_sha and len(m["exclusion_keys_sha256"]) == 64
    assert len(first) == 1 and all(first[0].values())  # origins, text features, cut points and the sample exist before the first print request
    assert world.api.kinds("gamma_window")
    for f in ("frame.csv.gz", "sample.csv.gz", "origins.csv.gz", "text_features.csv.gz", "outcomes_guarded.csv.gz", "origin_prices.csv.gz",
              "origin_prints.csv.gz", "cut_points.json", "key_drops.json", "frame_report.json"):
        assert (world.tdir / f).exists(), f
    assert not (world.tdir / "frame_partial.jsonl.gz").exists() and not (world.tdir / "prints_partial.jsonl.gz").exists()
    for rel, sha in m["file_sha256"].items():
        assert h5sha(world.tdir / rel) == sha
    assert m["text_features_sha256"] == h5sha(world.tdir / "text_features.csv.gz")


def h5sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_text_filters_before_sampling_and_key_drop(world, text_done):
    sample = {r["market_id"] for r in rd(world.tdir / "sample.csv.gz")}
    rep = json.loads((world.tdir / "frame_report.json").read_text())
    sp = world.special
    for k in ("geopol", "weather", "other", "nonbinary", "event_sib"):
        assert sp[k] not in sample, k
    fd = rep["filter_dropped"]
    assert fd.get("geopolitics", 0) >= 1 and fd.get("weather", 0) >= 1 and fd.get("not_yes_no", 0) >= 1 and fd.get("other_placeholder", 0) >= 1
    assert rep["exclusion_key_dropped"] == 1 and rep["key_drops"]["by_type_any_match"]["event"] == 1
    assert sp["sports"] in sample and sp["long_text"] in sample  # sports kept as a stratum
    assert rep["n_sample"] == len(sample) and rep["n_sample"] <= world.n_markets
    rows = {r["market_id"]: r for r in rd(world.tdir / "sample.csv.gz")}
    sports = rows[sp["sports"]]
    assert float(sports["sample_weight"]) > 0 and float(sports["inclusion_prob"]) <= 1
    assert not any(c in rows[sp["sports"]] for c in ("outcome_prices", "uma_status"))  # outcomes never in the sample file


def test_text_full_description_features_stored_not_truncated_markers(world, text_done):
    rows = {r["market_id"]: r for r in rd(world.tdir / "sample.csv.gz")}
    r = rows[world.special["long_text"]]
    assert int(r["desc_len"]) > 4500 and len(r["description"]) == 4000
    assert r["clarified"] == "1" and r["m6"] == "1" and r["m5"] == "1"  # marker text lies beyond character 4,000
    assert r["desc_sha256"] == hashlib.sha256(("x" * 4500 + " Update: clarified later by 10 pm ET").encode()).hexdigest()
    rep = json.loads((world.tdir / "frame_report.json").read_text())
    assert rep["sampled_descriptions_longer_than_stored"] >= 1 and rep["descriptions_longer_than_stored"] >= 1
    feats = {r["market_id"]: r for r in rd(world.tdir / "text_features.csv.gz")}
    assert feats[world.special["long_text"]]["c"] == r["c"]
    cuts = json.loads((world.tdir / "cut_points.json").read_text())
    assert cuts["by_topic"] and all({"n", "c_L", "c_H", "contrast"} <= set(v) for v in cuts["by_topic"].values())


def test_text_closed_time_status_cap_and_guarded_outcomes(world, text_done):
    sp = world.special
    frame = {r["market_id"]: r for r in rd(world.tdir / "frame.csv.gz")}
    r = frame[sp["after_cap"]]
    assert r["status"] == "active" and r["closed_time"] == "" and r["closed_after_cap"] == "1"  # closed after min(T_fetch, T_seal)
    assert "outcome_prices" not in r and "uma_status" not in r
    closed = [x for x in frame.values() if x["status"] == "closed"]
    assert closed and all(x["closed_time"] for x in closed)  # closed_time kept as a status field
    out = {r["market_id"]: r for r in rd(world.tdir / cm.OUTCOME_FILE)}
    assert out[sp["after_cap"]]["outcome_prices"] == ""  # censored: outcome not stored after the cap
    assert any(v["outcome_prices"] for v in out.values())
    rep = json.loads((world.tdir / "frame_report.json").read_text())
    assert rep["closed_after_cap_in_frame"] >= 1


def test_text_prints_one_request_per_market_no_wallet_no_clob(world, text_done):
    m, _ = text_done
    prices = rd(world.tdir / "origin_prices.csv.gz")
    sample = rd(world.tdir / "sample.csv.gz")
    assert len(prices) == len(sample) == m["counts"]["items_done"]
    reqs = [p for p in world.api.kinds("trades")]
    assert len(reqs) >= len(sample)  # the keys run used none; exactly one per market in this run
    cids = [p["market"] for p in reqs]
    assert len(cids) == len(set(cids))
    prints = rd(world.tdir / "origin_prints.csv.gz")
    assert prints and set(prints[0]) == {"item_id", "ts", "yes_price", "size", "yes_side"}
    blob = (world.tdir / "origin_prints.csv.gz").read_bytes() + (world.tdir / "origin_prices.csv.gz").read_bytes()
    assert b"0xwallet" not in gzip.decompress((world.tdir / "origin_prints.csv.gz").read_bytes()) and blob
    by = {p["market_id"]: p for p in prices}
    nop = by[world.special["no_prints"][0]]
    assert nop["price_status"] == "no_print" and nop["eligible"] == "0"
    ok = next(p for p in prices if p["price_status"] == "ok")
    assert ok["m_source"] == "vwap24h" and 0.29 < float(ok["m"]) < 0.31 and ok["eligible"] == "1"  # the planted print at t7 (0.99) is ignored
    assert all(int(p["ts"]) < int(next(x for x in prices if x["item_id"] == p["item_id"])["origin_ts"]) for p in prints)
    assert m["counts"]["print_request_failed"] == 0


def test_text_sample_size_cap_and_sports_weight(tmp_path):
    w = World(tmp_path, n_markets=30)
    w.keys()
    m = w.text()
    rep = json.loads((w.tdir / "frame_report.json").read_text())
    assert m["status"] == cm.TEXT_COMPLETE and rep["n_sample"] == 30 and rep["kept_by_key_stage"] > 30 and rep["sample"]["taken_all"] is False
    rows = rd(w.tdir / "sample.csv.gz")
    assert len(rows) == 30 and all(float(r["sample_weight"]) >= 1.0 for r in rows)
    assert len({r["market_id"] for r in rows}) == 30
    n_trades = len(w.api.kinds("trades"))
    assert n_trades == 30  # one print request per sampled market


def test_text_rerun_is_idempotent_complete(world, text_done):
    n = len(world.api.log)
    m = world.text()
    assert m["status"] == cm.TEXT_COMPLETE and len(world.api.log) == n


def test_text_resume_by_chunks_gives_identical_files(tmp_path, world):
    w = World(tmp_path)
    w.keys()
    stop = {"n": 0}

    def should_stop():
        stop["n"] += 1
        return stop["n"] % 40 == 0

    chunks = 0
    while True:
        chunks += 1
        m = w.text(should_stop=should_stop)
        if m.get("status") == cm.TEXT_COMPLETE:
            break
        assert m.get("status") == "in_progress", m
        assert chunks < 400
    assert chunks > 2
    ref = world.tdir
    for f in ("sample.csv.gz", "origin_prices.csv.gz", "origin_prints.csv.gz", "origins.csv.gz", "text_features.csv.gz", "cut_points.json"):
        assert gzip.decompress((w.tdir / f).read_bytes()) == gzip.decompress((ref / f).read_bytes()) if f.endswith(".gz") else (w.tdir / f).read_text() == (ref / f).read_text(), f


def test_text_failed_requests_counted_apart_from_no_data(tmp_path, world):
    sample_ids = [r["market_id"] for r in rd(world.tdir / "sample.csv.gz")]
    victim = sample_ids[3]
    w = World(tmp_path, fail_cids=[f"c{victim}"])
    w.keys()
    m = run_until_terminal(w.text, limit=12)
    assert m["status"] == cm.TEXT_COMPLETE
    assert m["counts"]["print_request_failed"] == 1 and m["counts"]["origin_no_print"] >= 1
    assert victim not in {r["market_id"] for r in rd(w.tdir / "origin_prices.csv.gz")}  # not stored as "no data"
    assert m["items_failed_final"] == 1


def test_text_deadline_no_chunk_at_or_after_t_seal(tmp_path):
    w = World(tmp_path)
    w.keys()
    n = len(w.api.log)
    m = w.text(wall_clock=lambda: cm.T_SEAL_EPOCH + 1)
    assert m["status"] == cm.NOT_RUN_TOKEN and (w.tdir / cm.NOT_RUN_FILE).exists() and len(w.api.log) == n
    assert json.loads((w.tdir / "manifest.json").read_text())["stopped"] == cm.NOT_RUN_TOKEN
    assert w.text(wall_clock=lambda: NOW)["status"] == cm.NOT_RUN_TOKEN  # sticky: no refetch, no moved cap
    w2 = World(tmp_path / "b")
    w2.keys()
    clock = {"t": NOW}
    calls = {"n": 0}

    def wall():
        calls["n"] += 1
        if calls["n"] > 300:  # the clock crosses T_seal mid-run
            clock["t"] = cm.T_SEAL_EPOCH + 5
        return clock["t"]

    m2 = w2.text(wall_clock=wall)
    assert m2["status"] == cm.NOT_RUN_TOKEN and (w2.tdir / cm.NOT_RUN_FILE).exists()
    assert not (w2.tdir / "SEAL.json").exists()


def test_text_cap_never_after_t_seal_or_t_fetch(tmp_path):
    w = World(tmp_path)
    w.keys()
    # a fetch whose request clock lies after T_seal still caps at T_seal
    m = w.text(now=cm.T_SEAL_EPOCH + 5 * DAY, wall_clock=lambda: cm.T_SEAL_EPOCH - 10)
    assert m["params"]["cap_utc"] == "2026-10-22T00:00:00Z"
    w2 = World(tmp_path / "b")
    w2.keys()
    assert w2.text(wall_clock=lambda: NOW + 3600)["params"]["cap_utc"] == iso(NOW)  # T_fetch earlier than T_seal: capped at T_fetch


def test_text_disk_budget_is_declared_end_state_not_75(tmp_path, capsys, monkeypatch):
    w = World(tmp_path)
    w.keys()
    m = w.text(disk_cap=60_000)
    assert m["status"] == cm.DISK_BUDGET_TOKEN and "disk_budget" in m["stopped"]
    assert w.text(disk_cap=60_000)["status"] == cm.DISK_BUDGET_TOKEN  # sticky, no new work
    monkeypatch.setattr(ct, "text_fetch", lambda *a, **k: m)
    rc = script.main(["text-fetch", "--disk-cap-gb", "0.15", "--standalone"])
    assert rc == script.DISK_BUDGET == 4 and rc != 75
    assert '"status": "disk_budget"' in capsys.readouterr().out


# ---- h8_geo end to end ------------------------------------------------------------------------------------------------------------


def test_geo_complete_no_clob_all_tags_event_titles_and_frame_kept(world, geo_done):
    m = geo_done
    assert m["status"] == cm.GEO_COMPLETE and m["complete"] is True and m["exclusion_keys_sha256"]
    frame = rd(world.gdir / "frame.csv.gz")
    assert len(frame) >= 33 and all(r["query_tag_id"] == "100265" for r in frame)
    r = next(x for x in frame if x["event_id"] == "G1")
    assert r["event_title"] == "Russia war" and "100265" in r["event_tag_ids"].split(";") and "7" in r["event_tag_ids"].split(";")
    assert r["market_tag_ids"] == "55" and "fee_category" in r
    assert "closed_time" in r and "status" in r
    assert "E-other" not in {x["event_id"] for x in frame}  # a market without the tag is never walked
    assert not [p for k, p in world.api.log if k == "gamma_window" and p.get("tag_id") not in (None, "100265")]


def test_geo_order_filters_then_key_drop_then_cap(world, geo_done):
    kept = {r["market_id"] for r in rd(world.gdir / "sample.csv.gz")}
    capped = rd(world.gdir / "capped.csv.gz")
    g1 = set(world.special["g1_ids"])
    assert len(kept & g1) == 8 and len([c for c in capped if c["event_key"] == "G1"]) == 12
    expect = sorted(g1, key=lambda x: hashlib.sha256(("arepo-h8-geo|" + x).encode()).hexdigest())[:8]
    assert kept & g1 == set(expect)  # seeded by market id only
    # G2: 13 members; 4 status-quo + 1 continuous + 1 short life are filtered BEFORE the cap, the event-key drop acts on G2 only
    # through excluded 9000-series ids (none here): the 7 clean members all survive (cap-first would not guarantee that)
    rep = json.loads((world.gdir / "frame_report.json").read_text())
    assert rep["filter_dropped"]["status_quo"] == 4 and rep["filter_dropped"]["continuous_class"] == 1 and rep["filter_dropped"]["life_lt_9d"] == 1
    g2 = set(world.special["g2_ids"])
    assert len(kept & g2) == 7 and rep["capped_out"] == 12 and rep["kept_before_cap"] == 20 + 7
    assert rep["max_per_event"] == 8


def test_geo_origins_two_day_rule_and_one_request_per_origin(world, geo_done):
    m = geo_done
    origins = rd(world.gdir / "origins.csv.gz")
    sample = {r["market_id"]: r for r in rd(world.gdir / "sample.csv.gz")}
    assert {o["k"] for o in origins} == {"30", "14", "7"}
    for o in origins:
        end = ep(sample[o["market_id"]]["end_at"])
        assert int(o["origin_ts"]) == int(end - int(o["k"]) * DAY)
    prices = rd(world.gdir / "origin_prices.csv.gz")
    assert len(prices) == len(origins) == m["counts"]["items_done"]
    assert all(p["item_id"] == f"{p['market_id']}|{p['k']}" for p in prices)
    ok = [p for p in prices if p["eligible"] == "1"]
    assert ok and all(0.02 <= float(p["m"]) <= 0.10 for p in ok)
    assert all(p["price_status"] in ("ok", "out_of_band", "no_print") for p in prices)
    assert not [1 for k, _ in world.api.log if k == "clob"] and m["counts"]["print_request_failed"] == 0


def test_geo_origin_rule_functions():
    end = ep("2026-07-01T00:00:00Z")
    assert [k for k, _ in cg.geo_origins(end - 40 * DAY, end)] == [30, 14, 7]
    assert [k for k, _ in cg.geo_origins(end - 20 * DAY, end)] == [14, 7]
    assert [k for k, _ in cg.geo_origins(end - 9 * DAY, end)] == [7] or cg.geo_origins(end - 9 * DAY, end) == [(7, int(end - 7 * DAY))]
    assert cg.geo_origins(end - 8 * DAY, end) == []  # t7 < created + 2 d
    assert cg.theme_of("Will Putin meet Zelensky?", "") == "ru-ua" and cg.theme_of("Will Iran and Israel clash?", "") == "il-ps"  # first match wins
    assert cg.theme_of("Will Hezbollah strike?", "Iran war") == "iran" and cg.theme_of("Will X happen?", "") == ""
    assert cg.theme_of("Will Maduro leave?", "") == "ve" and cg.theme_of("Kashmir ceasefire", "") == "in-pk"
    assert cg.split_window(0, 10) == ((0, 5), (5, 10)) and cg.split_window(0, 9) == ((0, 4), (4, 9))


def test_geo_window_split_while_capped_and_one_day_exclusion(tmp_path, monkeypatch):
    w = World(tmp_path)
    w.keys()
    monkeypatch.setattr(hb, "GAMMA_PAGE", 5)
    monkeypatch.setattr(hb, "GAMMA_OFFSET_CAP", 10)
    day = ep("2026-06-10T00:00:00Z")
    # 12 markets within one hour of one day: month window capped -> split down to one day -> still capped -> excluded and counted
    extra = [gm(500000 + j, day + 60 * j, event=f"S{j}") for j in range(12)]
    w.api.markets.update({m["id"]: m for m in extra})
    m = w.geo()
    rep = json.loads((w.gdir / "frame_report.json").read_text())
    assert rep["splits"] >= 1 and rep["excluded_capped_at_one_day"]["active"] + rep["excluded_capped_at_one_day"]["closed"] >= 1
    assert rep["rows_in_excluded_windows"] >= 10
    assert m["status"] in (cm.GEO_COMPLETE, "in_progress")
    assert not ({str(500000 + j) for j in range(12)} & {r["market_id"] for r in rd(w.gdir / "frame.csv.gz")})


def test_geo_source_unverified_when_over_two_percent_origins_fail(tmp_path):
    w = World(tmp_path)
    ids = w.special["g1_ids"][:12]
    w.api.fail_cids = {f"c{i}" for i in ids}
    w.keys()
    m = run_until_terminal(w.geo, limit=12)
    assert m["status"] == cm.SOURCE_UNVERIFIED_TOKEN and (w.gdir / cm.SOURCE_UNVERIFIED_FILE).exists()
    assert m["failed_origin_share"] > 0.02 and m["counts"]["print_request_failed"] > 0
    with pytest.raises(cm.Refused):
        cs.seal_cb7(w.root, cm.GEO_RUN_ID, seals_dir=w.seals, trials_path=tmp_path / "t.jsonl")


def test_geo_deadline_and_disk_budget(tmp_path):
    w = World(tmp_path)
    w.keys()
    m = w.geo(wall_clock=lambda: cm.T_SEAL_EPOCH)
    assert m["status"] == cm.NOT_RUN_TOKEN and (w.gdir / cm.NOT_RUN_FILE).exists()
    w2 = World(tmp_path / "b")
    w2.keys()
    d = w2.geo(disk_cap=3_000)
    assert d["status"] == cm.DISK_BUDGET_TOKEN


# ---- seals -----------------------------------------------------------------------------------------------------------------------


def seal_world(tmp_path):
    w = World(tmp_path)
    w.keys()
    assert w.geo()["status"] == cm.GEO_COMPLETE
    assert w.text()["status"] == cm.TEXT_COMPLETE
    return w


def test_seal_rehash_refuses_on_mismatch_and_pending_sources(tmp_path):
    w = seal_world(tmp_path)
    trials = tmp_path / "trials.jsonl"
    with pytest.raises(cm.NotNow):  # h8_tail / h7 seal copies are neither committed nor recorded not run
        cs.seal_cb7(w.root, cm.TEXT_RUN_ID, seals_dir=w.seals, trials_path=trials)
    for h in cs.DROP_RUNS:
        (w.seals / f"{h}_NOT_RUN.json").write_text("{}")
    f = w.tdir / "sample.csv.gz"
    orig = f.read_bytes()
    f.write_bytes(orig + b"\x00")
    with pytest.raises(cm.Refused, match="sha256 differs"):
        cs.seal_cb7(w.root, cm.TEXT_RUN_ID, seals_dir=w.seals, trials_path=trials)
    f.write_bytes(orig)
    (w.tdir / "stray.txt").write_text("x")
    with pytest.raises(cm.Refused, match="not in the fetch manifest"):
        cs.seal_cb7(w.root, cm.TEXT_RUN_ID, seals_dir=w.seals, trials_path=trials)
    (w.tdir / "stray.txt").unlink()
    (w.tdir / "origin_prices.csv.gz").unlink()
    with pytest.raises(cm.Refused, match="missing"):
        cs.seal_cb7(w.root, cm.TEXT_RUN_ID, seals_dir=w.seals, trials_path=trials)


def test_seal_text_and_geo_drop_blocks_by_id_and_key(tmp_path):
    w = seal_world(tmp_path)
    trials = tmp_path / "trials.jsonl"
    tsample = rd(w.tdir / "sample.csv.gz")
    drop_tail = tsample[0]
    tail_id = drop_tail["market_id"]
    # h8_tail seal copy lists one h8_text market id; its event key must also drop siblings (here: none, so the id drop only)
    write_seal_copy(w.seals / "h8_tail_SEAL.json", [tail_id])
    for h in ("h7_cb4_era", "h7_cb4_series"):
        (w.seals / f"{h}_NOT_RUN.json").write_text("{}")
    # the h8_text markets that share an id / key with the FULL h8_geo frame (before filters and cap) are dropped from h8_text
    geo_frame = rd(w.gdir / "frame.csv.gz")
    assert w.api.markets[tail_id]
    res = cs.seal_cb7(w.root, cm.GEO_RUN_ID, transport=w.api, seals_dir=w.seals, trials_path=trials, sleep=lambda s: None)
    assert res["sealed"] and (w.seals / "h8_geo_SEAL.json").exists()
    res = cs.seal_cb7(w.root, cm.TEXT_RUN_ID, transport=w.api, seals_dir=w.seals, trials_path=trials, sleep=lambda s: None)
    assert res["drop_counts"]["DROPPED_SEALED_RUNS"] == 1
    drops = rd(w.tdir / "drops.csv.gz")
    assert [d["market_id"] for d in drops] == [tail_id] and drops[0]["block"] == "DROPPED_SEALED_RUNS"
    rep = json.loads((w.tdir / "drops_report.json").read_text())
    assert rep["geo_frame"] == "frame" and rep["geo_frame_ids"] == len(geo_frame)
    assert cs.verify_cb7(w.root, cm.TEXT_RUN_ID, w.seals)["listing_sha256"] == res["listing_sha256"]
    with pytest.raises(cm.Refused):  # sealed runs are never touched by the fetch
        w.text()
    assert (w.tdir / "ACCESS_LOG.jsonl").exists() and trials.exists()
    assert "creative_batch_7:cb7_f_seal" in trials.read_text()


def test_seal_text_drops_markets_sharing_key_with_full_geo_frame(tmp_path):
    # an h8_text market sharing the EVENT with a walked-but-capped geo market is dropped from h8_text at seal
    w = World(tmp_path)
    shared = gm(700001, ep("2026-05-05T00:00:00Z"), event="G1", q="Will thing happen in a different category?", tags=("2",))
    w.api.markets["700001"] = shared  # lies in a text window?  force it in via a dedicated day below
    w.keys()
    # put the shared-event market inside a text window
    d = datetime(2026, 5, 5, tzinfo=UTC).date()
    s = window_epochs(d, cm.TEXT_SEED)[0]
    shared = gm(700001, s + 30, event="G1", q="Will thing happen in a different category?", tags=("2",))
    w.api.markets["700001"] = shared
    w.api.trades["c700001"] = prints_for("c700001", s + 30 - 7 * DAY)
    assert w.geo()["status"] == cm.GEO_COMPLETE
    assert w.text()["status"] == cm.TEXT_COMPLETE
    assert "700001" in {r["market_id"] for r in rd(w.tdir / "sample.csv.gz")}
    for h in cs.DROP_RUNS:
        (w.seals / f"{h}_NOT_RUN.json").write_text("{}")
    cs.seal_cb7(w.root, cm.GEO_RUN_ID, seals_dir=w.seals, trials_path=tmp_path / "t.jsonl")
    res = cs.seal_cb7(w.root, cm.TEXT_RUN_ID, seals_dir=w.seals, trials_path=tmp_path / "t.jsonl")
    drops = {d_["market_id"]: d_ for d_ in rd(w.tdir / "drops.csv.gz")}
    assert drops["700001"]["block"] == "DROPPED_GEO_FRAME" and "event" in drops["700001"]["reason"] and res["drop_counts"]["DROPPED_GEO_FRAME"] >= 1


# ---- runner ----------------------------------------------------------------------------------------------------------------------


def test_runner_refusals(tmp_path, capsys):
    assert script.main(["text-fetch", "--disk-cap-gb", "0.15", "--n-markets", "100", "--standalone"]) == 2
    assert script.main(["text-fetch", "--disk-cap-gb", "0.15", "--run-id", "h8_tail", "--standalone", "--rules", str(tmp_path / "x.json")]) == 2
    assert script.main(["geo-fetch", "--disk-cap-gb", "0.05", "--standalone"]) == 2  # --cap-after-filters absent: declared arguments differ
    assert script.main(["geo-fetch", "--disk-cap-gb", "0.05", "--cap-after-filters", "--run-id", "h8_text", "--standalone", "--rules", str(tmp_path / "x.json")]) == 2
    assert script.main(["text-fetch", "--disk-cap-gb", "0.15", "--cap-at", "2026-10-30T00:00Z", "--standalone"]) == 2
    out = capsys.readouterr().out
    assert "arguments differ" in out and "refused" in out


def test_runner_headroom_exit_75_and_text_cli_parses_declared_draft_flags(monkeypatch, capsys):
    def boom(*a, **k):
        raise cm.NotNow("headroom")

    monkeypatch.setattr(ct, "text_fetch", boom)
    rc = script.main(["text-fetch", "--run-id", "h8_text", "--rules", "r.json", "--seed", "arepo-h8-text", "--n-markets", "18000",
                      "--end-from", "2025-04-01", "--end-before-fetch-days", "7", "--windows-per-day", "5", "--window-minutes", "15",
                      "--min-life-days", "9", "--sports-weight", "0.25", "--origin-days-before-end", "7", "--print-limit", "50",
                      "--exclude-categories", "weather,geopolitics,crypto_updown", "--exclusion-keys", "k.csv.gz",
                      "--require-smoke", "s.json", "--cap-at", "2026-10-22T00:00Z", "--rps", "4", "--disk-cap-gb", "0.15",
                      "--data-dumps-cap-gb", "12.5", "--budget-min", "85", "--standalone"])
    assert rc == 75 and "tempfail" in capsys.readouterr().out
    monkeypatch.setattr(cg, "geo_fetch", boom)
    rc = script.main(["geo-fetch", "--run-id", "h8_geo", "--seed", "arepo-h8-geo", "--tag-slug", "geopolitics", "--tag-id", "100265",
                      "--end-from", "2025-06-01", "--end-before-fetch-days", "7", "--min-life-days", "9", "--max-per-event", "8",
                      "--cap-after-filters", "--origins-days-before-end", "30,14,7", "--print-limit", "50", "--band", "0.02,0.10",
                      "--max-failed-origin-share", "0.02", "--exclusion-keys", "k.csv.gz", "--require-smoke", "s.json",
                      "--cap-at", "2026-10-22T00:00Z", "--rps", "4", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "12.5",
                      "--budget-min", "85", "--standalone"])
    assert rc == 75


def test_runner_status_lines_match_queue_regexes(monkeypatch, capsys):
    import re

    for st in ("text_fetch_complete", "not_run_deadline", "disjointness_unverified", "disk_budget"):
        monkeypatch.setattr(ct, "text_fetch", lambda *a, st=st, **k: {"status": st, "stopped": None, "complete": st.endswith("complete")})
        rc = script.main(["text-fetch", "--disk-cap-gb", "0.15", "--standalone"])
        out = capsys.readouterr().out
        assert re.search(r"\"status\": \"(text_fetch_complete|not_run_deadline|disjointness_unverified|disk_budget)\"", out), out
        assert rc == (4 if st == "disk_budget" else 0)


def test_queue_drafts_argv_parse_and_match_declaration():
    drafts = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "drafts"
    files = sorted(drafts.glob("q014[0-5]_*.json"))
    if len(files) < 6:
        pytest.skip("drafts not present")
    ap = script.build_parser()
    for f in files:
        spec = json.loads(f.read_text())
        assert spec["argv"][0] == "scripts/run_cb7.py" and spec["resources"]["lane"] in ("net", "cpu")
        a = ap.parse_args(spec["argv"][1:])
        if spec["argv"][1] == "text-fetch":
            assert script._declared_text(a, cm) == [] and spec["resources"]["lane"] == "net"
        if spec["argv"][1] == "geo-fetch":
            assert script._declared_geo(a, cm) == [] and spec["resources"]["lane"] == "net"
        if spec["argv"][1] in ("text-fetch", "geo-fetch", "exclusion-keys"):
            import re

            rx = spec["repeat"]["until_log_regex"]
            for st in ("not_run_deadline", "disk_budget"):
                assert re.search(rx, f'{{"status": "{st}"}}'), (f.name, st)
            assert spec["repeat"]["max_runs"] >= 4
    assert {json.loads(f.read_text())["resources"]["lane"] for f in files[:4]} == {"net"}


def test_smoke_network_failure_is_tempfail_and_writes_nothing(tmp_path, monkeypatch, capsys):
    w = World(tmp_path)
    files = c6.verify_exclusion_files(w.pins, history_root=w.root, seals_dir=w.seals)

    class Down:
        def __call__(self, url, params):
            return 503, b"", {}

    with pytest.raises(cm.NotNow):
        cm.run_smoke(hb.Limiter(Down(), rps=100.0, sleep=lambda s: None), files, w.pins, w.rules_sha)
    real = w.api

    def trades_down(url, params):
        return (500, b"", {}) if url.endswith("/trades") else real(url, params)

    with pytest.raises(cm.NotNow):
        cm.run_smoke(hb.Limiter(trades_down, rps=100.0, sleep=lambda s: None), files, w.pins, w.rules_sha)
    out = tmp_path / "fresh_smoke.json"

    def boom(*a, **k):
        raise cm.NotNow("net")

    monkeypatch.setattr(cm, "run_smoke", boom)
    monkeypatch.setattr(cm, "verify_rules", lambda *a, **k: "x")
    monkeypatch.setattr(cm.c6, "verify_exclusion_files", lambda *a, **k: {})
    rc = script.main(["smoke", "--out", str(out), "--standalone"])
    assert rc == 75 and not out.exists()


def test_geo_frame_state_terminal_cases_never_block_text_seal(tmp_path):
    root = tmp_path / "h"
    (root / "h8_geo").mkdir(parents=True)
    smoke = tmp_path / "s.json"
    assert cs.geo_frame_state(root, smoke)[0] == "pending"
    smoke.write_text(json.dumps({"criterion_a_slug_resolves_to_pinned_id": False}))
    assert cs.geo_frame_state(root, smoke)[0] == "not_run"  # q0143 refused
    smoke.write_text(json.dumps({"criterion_a_slug_resolves_to_pinned_id": True}))
    assert cs.geo_frame_state(root, smoke)[0] == "pending"
    (root / "h8_geo" / "manifest.json").write_text(json.dumps({"status": "disk_budget"}))
    assert cs.geo_frame_state(root, smoke)[0] == "not_run"
    (root / "h8_geo" / "manifest.json").write_text(json.dumps({"status": "source_unverified"}))
    assert cs.geo_frame_state(root, smoke)[0] == "not_run"


def test_seal_rerun_after_crash_tolerates_leftover_drops_files(tmp_path):
    w = World(tmp_path)
    w.keys()
    assert w.geo()["status"] == cm.GEO_COMPLETE
    for h in cs.DROP_RUNS:
        (w.seals / f"{h}_NOT_RUN.json").write_text("{}")
    (w.gdir / "drops.csv.gz").write_bytes(b"leftover")
    (w.gdir / "drops_report.json").write_text("{}")
    res = cs.seal_cb7(w.root, cm.GEO_RUN_ID, seals_dir=w.seals, trials_path=tmp_path / "t.jsonl")
    assert res["sealed"]


# ---- smoke v2 (q0140b) ------------------------------------------------------------------------------------------------------------


def _sample_rows(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["market_id", "token0", "end_epoch", "closed", "created_at", "close_epoch", "start_epoch", "fee_category", "volume", "question"]
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def test_smoke_pool_v2_recorded_field_rules(tmp_path):
    end = ep("2025-06-15T00:00:00Z")
    base = {"token0": "t", "closed": 1, "created_at": "", "end_epoch": end, "start_epoch": end - 30 * DAY, "close_epoch": end,
            "fee_category": "", "volume": 5.0, "question": "Will x happen?"}  # recorded volume 5 must NOT exclude
    rows = [dict(base, market_id="ok"),
            dict(base, market_id="short", start_epoch=end - 13 * DAY),
            dict(base, market_id="early_close", close_epoch=end - 8 * DAY),
            dict(base, market_id="no_close", close_epoch=""),
            dict(base, market_id="weather", fee_category="weather"),
            dict(base, market_id="updown", question="Bitcoin Up or Down - 5 PM"),
            dict(base, market_id="y2024", end_epoch=ep("2024-12-31T00:00:00Z"), start_epoch=ep("2024-11-01T00:00:00Z"), close_epoch=ep("2024-12-31T00:00:00Z")),
            dict(base, market_id="edge", close_epoch=end - 7 * DAY)]
    _sample_rows(tmp_path / "s.csv.gz", rows)
    pins = [{"name": "s", "kind": "sample"}]
    st: dict = {}
    ids = cm.smoke_pool_v2({"s": tmp_path / "s.csv.gz"}, pins, stats=st)
    assert sorted(ids) == ["edge", "ok"] and ids == sorted(ids, key=lambda x: hb._rank(cm.SMOKE_SEED_V2, x))
    assert st == {"n_sample_rows": 8, "n_recorded_pass": 2, "n_recorded_pass_volume_ge_min": 0}
    assert cm.SMOKE_SEED_V2 != cm.SMOKE_SEED


def test_run_smoke_v2_gamma_filters_and_fail_when_fewer_than_20(tmp_path):
    w = World(tmp_path)
    files = c6.verify_exclusion_files(w.pins, history_root=w.root, seals_dir=w.seals)
    end = ep("2025-06-15T00:00:00Z")
    w.api.trades.update({f"c{m}": [{"timestamp": int(end - 10 * DAY + i), "side": "BUY", "size": 1.0, "price": 0.4, "outcomeIndex": 0,
                                    "proxyWallet": "0xw", "transactionHash": f"t{m}{i}", "asset": "a"} for i in range(3)] for m in w.excl_ids})
    res = cm.run_smoke(lim_for(w.api), files, w.pins, w.rules_sha)
    assert res["smoke_version"] == "cb7-smoke-v2" and res["pass"] is True and res["n_requested"] == 20
    assert res["n_recorded_pass"] == 30 and res["n_recorded_pass_volume_ge_min"] == 30  # h1+h2+h3 sample ids only
    d = res["disclosure"]
    assert d["supersedes"]["result"] == "FAIL" and set(d["prior_probe_overlap_counts"]) >= {"cb7_smoke_v1_probed_in_v2_draws"}
    assert "tok" not in json.dumps(res)
    # 11 of the 30 recorded-pass ids fail at the Gamma step (labels / volume / Up-Down) -> 19 survive -> FAIL, no widening
    pool = [f"9{i:03d}" for i in range(30)]
    for x in pool[:4]:
        w.api.markets[x]["outcomes"] = '["Up","Down"]'
    for x in pool[4:8]:
        w.api.markets[x]["volumeNum"] = 9999.0
    for x in pool[8:11]:
        w.api.markets[x]["question"] = "Ethereum Up or Down - 3 PM"
    bad = cm.run_smoke(lim_for(w.api), files, w.pins, w.rules_sha)
    assert bad["n_in_pool"] == 19 and bad["n_requested"] == 19 and bad["pass"] is False
    assert bad["criterion_b_bounds_and_order"] is False and bad["criterion_c_coverage"] is False


def test_smoke_v2_gate_requires_v2_version_and_rules(tmp_path):
    p = tmp_path / "s.json"
    base = {"rules_sha256": "r", "criterion_a_slug_resolves_to_pinned_id": True, "criterion_b_bounds_and_order": True, "criterion_c_coverage": True}
    p.write_text(json.dumps({**base, "smoke_version": cm.SMOKE_V1_VERSION}))
    with pytest.raises(cm.Refused):  # a v1 result never satisfies the gate
        cm.smoke_ok(p, "r", ("b", "c"))
    p.write_text(json.dumps({**base, "smoke_version": "cb7-smoke-v2"}))
    assert cm.smoke_ok(p, "r", ("b", "c"))["smoke_version"] == "cb7-smoke-v2"
    assert cm.SMOKE_DEFAULT.name == "smoke_v2.json" and cm.RULES_FILE.name == "cb7_text_geo_rules_v2.json"
    assert cm.SMOKE_V1_PATH.name == "smoke.json" and cm.RULES_FILE_V1.name == "cb7_text_geo_rules.json"


def test_smoke_v2_cli_never_writes_v1_file(capsys):
    rc = script.main(["smoke", "--out", str(cm.SMOKE_V1_PATH), "--standalone"])
    assert rc == 2 and "v1" in capsys.readouterr().out


def test_rules_v2_differs_from_v1_only_in_smoke_block():
    if not cm.RULES_FILE_V1.exists():
        pytest.skip("v1 rules file not present")
    v1 = json.loads(cm.RULES_FILE_V1.read_text())
    v2 = cm.rules_file_doc()
    hashes = {"rules_sha256", "funcs_sha256", "func_sources_sha256"}
    assert {k for k in v1 if k not in hashes and v1[k] != v2.get(k)} == {"rules_version", "seeds", "smoke"}
    assert {k for k in v1["seeds"] if v1["seeds"][k] != v2["seeds"][k]} == {"smoke"}
    # every v1 hashed function is byte-identical in v2; v2 adds only the new pool function and run_smoke
    f1, f2 = v1["func_sources_sha256"], v2["func_sources_sha256"]
    assert all(f2[k] == f1[k] for k in f1)
    assert set(f2) - set(f1) == {"smoke_pool_v2", "run_smoke"}
    assert v1["rules_sha256"] != v2["rules_sha256"]
