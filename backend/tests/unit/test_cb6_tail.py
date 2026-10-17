# ruff: noqa: E501
"""CB6 ``h8_tail`` fetch and seal (astrolabe.research_lab.cb6_tail, scripts/run_cb6.py;
docs/research_lab/CREATIVE_BATCH_6.md CB6-F and 10.3). Everything runs against a fake Gamma/CLOB/Data API."""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import sys
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from astrolabe.research_lab import cb6_tail as t
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb6 as script  # noqa: E402

DAY = 86400
NOW = datetime(2026, 10, 17, 12, tzinfo=UTC).timestamp()
CUTOFF = NOW - 7 * DAY
KEY = b"unit-test-key"
END_FROM = "2026-04-01"
SEED = t.SEED


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=UTC).timestamp()


def iso(x: float) -> str:
    return datetime.fromtimestamp(x, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def gm(mid, end, *, created=None, closed=False, event=None, neg="", series=(), desc="plain description", q=None, fee=None):
    return {"id": str(mid), "conditionId": f"c{mid}", "clobTokenIds": json.dumps([f"tok{mid}a", f"tok{mid}b"]),
            "createdAt": iso(created if created is not None else end - 40 * DAY), "startDate": iso(created if created is not None else end - 40 * DAY),
            "endDate": iso(end), "closed": closed, "closedTime": iso(end + 3600) if closed else None,
            "question": q or f"Will thing {mid} happen?", "slug": f"thing-{mid}", "description": desc, "feeType": fee,
            "outcomes": '["Yes","No"]', "outcomePrices": '["0.04","0.96"]' if closed else None,
            "umaResolutionStatus": "resolved" if closed else "", "volumeNum": 1234.5, "liquidityNum": 55.5,
            "negRisk": bool(neg), "negRiskMarketID": neg or None,
            "events": [{"id": str(event if event is not None else f"E{mid}"), "title": f"event {mid}",
                        "series": [{"id": str(s)} for s in series]}]}


def slot_start(day, seed=SEED, wpd=1):
    """First picked 15-minute window start of ``day`` (mirrors walk_tail_frame)."""
    dkey = f"{day:%Y-%m-%d}"
    d0 = datetime(day.year, day.month, day.day, tzinfo=UTC)
    valid = [k for k in range(96) if (d0 + timedelta(minutes=(k + 1) * 15)).timestamp() <= CUTOFF]
    rng = random.Random(f"{seed}|{dkey}")
    k = sorted(rng.sample(valid, min(wpd, len(valid))))[0]
    return (d0 + timedelta(minutes=k * 15)).timestamp()


class FakeApi:
    """Gamma /markets (windows and id lookups), CLOB prices-history, Data /trades and /activity."""

    def __init__(self, markets, trades=None, *, young=False):
        self.markets = {m["id"]: m for m in markets}
        self.trades = trades or {}
        self.log: list[tuple[str, dict]] = []
        self.hooks = []
        self.young = young

    def __call__(self, url, params):
        kind = ("gamma_ids" if "id" in params else "gamma_window") if url.endswith("/markets") else \
            "prices" if "prices-history" in url else "activity" if url.endswith("/activity") else "trades"
        self.log.append((kind, dict(params)))
        for h in self.hooks:
            h(kind, params)
        if kind == "gamma_ids":
            want = [str(x) for x in params["id"]]
            closed = params.get("closed")
            out = [self.markets[i] for i in want if i in self.markets
                   and (closed == "true" or not self.markets[i]["closed"]) and self.markets[i].get("hide") is not True]
            return 200, json.dumps(out).encode(), {}
        if kind == "gamma_window":
            lo, hi = ep(params["end_date_min"]), ep(params["end_date_max"])
            closed = params["closed"] == "true"
            rows = sorted((m for m in self.markets.values() if m["closed"] == closed and lo <= ep(m["endDate"]) < hi), key=lambda m: int(m["id"]))
            off, lim = int(params["offset"]), int(params["limit"])
            return 200, json.dumps(rows[off:off + lim]).encode(), {}
        if kind == "prices":
            a, b = int(params["startTs"]), int(params["endTs"])
            assert int(params["fidelity"]) == 60
            first = (a + 3599) // 3600 * 3600
            hist = [{"t": x, "p": 0.05} for x in range(first, b + 1, 3600)]
            return 200, json.dumps({"history": hist}).encode(), {}
        if kind == "trades":
            assert params["takerOnly"] == "true"
            rows = [x for x in self.trades.get(params["market"], []) if int(params["start"]) <= x["timestamp"] <= int(params["end"])]
            rows.sort(key=lambda x: -x["timestamp"])
            off, lim = int(params["offset"]), int(params["limit"])
            return 200, json.dumps(rows[off:off + lim]).encode(), {}
        first = (NOW - 400 * DAY) if not self.young else (NOW - 3 * DAY)
        return 200, json.dumps([{"timestamp": int(first)}]).encode(), {}


def make_trades(mid, created, end):
    """Small prints every 6 h and a large BUY of outcome 0 two hours before every Monday 00:00."""
    out = []
    ts = int(created)
    while ts < min(end, NOW):
        out.append({"timestamp": ts, "side": "BUY", "size": 10.0, "price": 0.05, "outcomeIndex": 0,
                    "proxyWallet": f"0xwalletaddr_small_{mid}_{ts % 7}", "transactionHash": f"h{mid}_{ts}", "asset": f"tok{mid}a"})
        ts += 6 * 3600
    d = int(created // DAY)
    d += (4 - d) % 7
    while d * DAY < min(end, NOW):
        out.append({"timestamp": d * DAY - 7200, "side": "BUY", "size": 4000.0, "price": 0.05, "outcomeIndex": 0,
                    "proxyWallet": f"0xwalletaddr_BIG_{mid}", "transactionHash": f"hb{mid}_{d}", "asset": f"tok{mid}a"})
        d += 7
    return out


def write_sample(path: Path, ids, end_epoch=None, closed=1, life_days=60.0, close_minus_end_days=0.0, created=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with gzip.open(path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["market_id", "token0", "end_epoch", "closed", "created_at", "close_epoch"])
        for i in ids:
            end = end_epoch if end_epoch is not None else ep("2025-06-15T00:00:00Z")
            w.writerow([i, f"tok{i}a", end, closed, iso(end - life_days * 86400) if created else "",
                        end + close_minus_end_days * 86400])


def write_seal_copy(path: Path, ids):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"run_id": path.stem.replace("_SEAL", ""), "files": {f"prices/{i}.csv.gz": "x" for i in ids}, "listing_sha256": "x"}))


class World:
    """Exclusion files, rules file, markets and a FakeApi in a tmp dir."""

    def __init__(self, tmp: Path, *, n_missing_meta=0, extra_markets=(), n_markets=30):
        self.tmp = tmp
        self.root = tmp / "history"
        self.seals = tmp / "seals"
        self.n_markets = n_markets
        h1 = [f"9{i:03d}" for i in range(0, 12)]
        h2 = [f"9{i:03d}" for i in range(12, 24)]
        h3 = [f"9{i:03d}" for i in range(24, 36)]
        h5 = [f"9{i:03d}" for i in range(36, 40)]
        h5l = [f"9{i:03d}" for i in range(40, 44)]
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
        self.rules = tmp / "cb6_tail_rules.json"
        self.rules.write_text(json.dumps(t.rules_file_doc(self.pins), indent=1, sort_keys=True))
        far = ep("2025-06-15T00:00:00Z")
        ex = []
        for i, mid in enumerate(self.excl_ids):
            kw = {}
            if mid == "9000":
                kw = {"event": 900}
            elif mid == "9001":
                kw = {"neg": "NR1", "event": 901}
            elif mid == "9002":
                kw = {"series": [77], "event": 902}
            m = gm(mid, far, closed=(i % 2 == 0), **kw)
            if i < n_missing_meta:
                m["hide"] = True
            ex.append(m)
        days = [datetime(2026, 4, 1, tzinfo=UTC).date() + timedelta(days=i) for i in range((datetime.fromtimestamp(CUTOFF, UTC).date() - datetime(2026, 4, 1, tzinfo=UTC).date()).days + 1)]
        self.frame_markets = []
        nid = 100000
        self.special = {}
        for di, d in enumerate(days):
            s = slot_start(d)
            for j in range(2):
                nid += 1
                self.frame_markets.append(gm(nid, s + j * 60))
            if di == 10:
                self.special["event_sib"] = nid + 1
                self.special["neg_sib"] = nid + 2
                self.special["series_sib"] = nid + 3
                self.special["excl_id"] = "9005"
                self.frame_markets += [gm(nid + 1, s + 120, event=900), gm(nid + 2, s + 180, neg="NR1", event=950),
                                       gm(nid + 3, s + 240, event=951, series=[77]),
                                       gm("9005", s + 300, closed=False)]
                nid += 3
            if di == 20:  # one market that fails the life filter and one weather market
                self.special["short_life"] = nid + 1
                self.special["weather"] = nid + 2
                self.frame_markets += [gm(nid + 1, s + 120, created=s + 120 - 5 * DAY),
                                       gm(nid + 2, s + 180, q="Highest temperature in Paris on April 3?", fee="weather")]
                nid += 2
            if di == 30:  # neg-risk event with two members and a market with a clarification marker
                self.special["neg_a"] = nid + 1
                self.special["neg_b"] = nid + 2
                self.frame_markets += [gm(nid + 1, s + 120, neg="NRX", event=5001), gm(nid + 2, s + 180, neg="NRX", event=5002)]
                nid += 2
        self.markets = ex + self.frame_markets + list(extra_markets)
        trades = {}
        for m in self.frame_markets:
            end = ep(m["endDate"])
            created = ep(m["createdAt"])
            trades[m["conditionId"]] = make_trades(m["id"], created, end)
        first = next(m for m in self.frame_markets if m["id"] not in {str(v) for v in self.special.values()})
        trades[first["conditionId"]].append({"timestamp": int(NOW + 100), "side": "BUY", "size": 1.0, "price": 0.05, "outcomeIndex": 0,
                                             "proxyWallet": "0xwalletaddr_future", "transactionHash": "hfuture", "asset": "x"})
        self.api = FakeApi(self.markets, trades)

    def run(self, *, api=None, **kw):
        base = dict(history_root=self.root, seals_dir=self.seals, rules_path=self.rules, pins=self.pins, n_markets=self.n_markets,
                    end_from=END_FROM, rps=4.0, key=KEY, now=NOW, sleep=lambda s: None, live_check=None, require_committed=False,
                    require_smoke=False, wall_clock=lambda: NOW + 3600, disk_cap=int(0.25 * 1024**3))
        base.update(kw)
        return t.tail_fetch(self.root, t.RUN_ID, api or self.api, **base)

    @property
    def rdir(self) -> Path:
        return self.root / t.RUN_ID


def read_csv_gz(path):
    return list(t._read_csv_gz(path))


@pytest.fixture(scope="module")
def full(tmp_path_factory):
    w = World(tmp_path_factory.mktemp("w"))
    origins_before_price = []

    def hook(kind, params):
        if kind == "prices" and not origins_before_price:
            origins_before_price.append((w.rdir / "origins.csv.gz").exists() and (w.rdir / "sample.csv.gz").exists())

    w.api.hooks.append(hook)
    m = w.run()
    return w, m, origins_before_price


# ---- rules file and pins --------------------------------------------------------------------------------------------


def test_rules_file_roundtrip_and_refusals(tmp_path):
    p = tmp_path / "r.json"
    t.write_rules(p)
    doc = json.loads(p.read_text())
    assert t.verify_rules(p, require_committed=False) == doc["rules_sha256"]
    assert doc["seeds"] == {"sample": "arepo-h8-tail", "origins": "arepo-h8-tail-origins", "smoke": "arepo-h8-smoke2", "split": "arepo-cb6-tail-split"}
    assert doc["rules_version"] == "cb6-tail-rules-v3" and doc["smoke"]["version"] == "h8-tail-smoke-v2"
    assert doc["topup"]["windows_per_day"] == 9 and doc["topup"]["parent"] == "h8_tail" and doc["smoke"]["carry_over"]["from_rules_sha256"]
    assert doc["smoke"]["min_pass"] == 18 and doc["smoke"]["min_fraction_of_expected_points"] == 0.8
    assert doc["smoke"]["median_spacing_s"] == [3600.0, 300.0] and doc["smoke"]["superseded"]["result"] == "FAIL"
    assert len(doc["exclusion"]["files"]) == 5 and all(len(f["sha256"]) == 64 for f in doc["exclusion"]["files"])
    assert doc["exclusion"]["max_unverified_key_share"] == 0.02 and doc["dates"]["end_before_fetch_days"] == 7
    bad = {**doc, "features": {**doc["features"], "drift_min": 0.02}}
    p.write_text(json.dumps(bad))
    with pytest.raises(t.Refused):
        t.verify_rules(p, require_committed=False)
    with pytest.raises(t.Refused):
        t.verify_rules(tmp_path / "missing.json", require_committed=False)
    with pytest.raises(t.Refused):  # a rules file is never rewritten
        t.write_rules(p)


def test_committed_rules_file_matches_code():
    if not t.RULES_FILE.exists():
        pytest.skip("rules file not generated yet")
    assert t.verify_rules(t.RULES_FILE, require_committed=False)


@pytest.mark.parametrize("which", ["h1_first", "h2_main", "h3_power", "h5_cb1", "h5_cb1_ladders"])
@pytest.mark.parametrize("mode", ["missing", "changed"])
def test_any_exclusion_file_missing_or_changed_refuses(tmp_path, which, mode):
    w = World(tmp_path)
    pin = next(p for p in w.pins if p["name"] == which)
    path = (w.root if pin["kind"] == "sample" else w.seals) / pin["path"]
    if mode == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(t.Refused):
        w.run()
    assert not w.api.log  # refused before any request
    assert not (w.rdir / "manifest.json").exists()


def test_refuses_without_smoke_pass_and_on_run_ids(tmp_path):
    w = World(tmp_path)
    with pytest.raises(t.Refused):
        w.run(require_smoke=True, smoke_path=tmp_path / "none.json")
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"pass": False, "rules_sha256": json.loads(w.rules.read_text())["rules_sha256"]}))
    with pytest.raises(t.Refused):
        w.run(require_smoke=True, smoke_path=smoke)
    smoke.write_text(json.dumps({"pass": True, "rules_sha256": "other"}))
    with pytest.raises(t.Refused):
        w.run(require_smoke=True, smoke_path=smoke)
    for rid in ("h3_power", "h5_cb1", "h7_cb4_era", "h6_weather", "h2_main"):
        with pytest.raises(t.Refused):
            t.refuse_run_id(rid)
    with pytest.raises(t.Refused):
        t.refuse_path(tmp_path / "cb4_extract" / "x")


def test_headroom_refusal_is_tempfail(tmp_path):
    w = World(tmp_path)
    (tmp_path / "dd").mkdir()
    (tmp_path / "dd" / "big.bin").write_bytes(b"0" * 2_000_000)
    with pytest.raises(t.NotNow):
        w.run(data_dumps=tmp_path / "dd", data_dumps_cap_gb=0.001)
    assert not w.api.log


# ---- disjointness -----------------------------------------------------------------------------------------------------------


def test_unverified_disjointness_is_terminal_no_sample_no_prices(tmp_path):
    w = World(tmp_path, n_missing_meta=10)  # 10 of 44 ids without metadata (> 2%)
    m = w.run()
    assert m["status"] == t.UNVERIFIED_TOKEN and m["complete"] is False
    assert (w.rdir / t.UNVERIFIED_FILE).exists()
    assert not (w.rdir / "sample.csv.gz").exists() and not (w.rdir / "origins.csv.gz").exists()
    kinds = {k for k, _ in w.api.log}
    assert kinds <= {"gamma_ids"}
    n = len(w.api.log)
    again = w.run()
    assert again["status"] == t.UNVERIFIED_TOKEN and len(w.api.log) == n  # terminal: no new request
    with pytest.raises(t.Refused):
        t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals)


def test_closed_markets_are_found_by_the_closed_true_retry(tmp_path):
    w = World(tmp_path)
    m = w.run(stage="keys")
    rep = json.loads((w.rdir / "exclusion_report.json").read_text())
    assert m["status"] == "exclusion_keys_complete" and rep["disjointness"] == "verified"
    assert rep["found_only_with_closed_true"] > 0  # closed markets are found by the closed=true retry
    ids_per_request = [len(p["id"]) for k, p in w.api.log if k == "gamma_ids"]
    assert max(ids_per_request) <= 50


# ---- full run ---------------------------------------------------------------------------------------------------------------------


def test_full_run_completes_and_filters_by_key(full):
    w, m, _ = full
    assert m["status"] == t.COMPLETE_TOKEN and m["complete"] is True and m["stopped"] is None
    sample = {r["market_id"]: r for r in read_csv_gz(w.rdir / "sample.csv.gz")}
    sp = {k: str(v) for k, v in w.special.items()}
    assert sp["event_sib"] not in sample  # shares event 900 with an excluded market
    assert sp["neg_sib"] not in sample  # shares negRiskMarketID NR1
    assert sp["series_sib"] not in sample  # shares series 77
    assert sp["excl_id"] not in sample  # an excluded id itself
    assert sp["short_life"] not in sample and sp["weather"] not in sample
    kd = json.loads((w.rdir / "key_drops.json").read_text())
    assert kd["by_type_any_match"] == {"event": 1, "neg_risk_market": 1, "series": 1}
    rep = json.loads((w.rdir / "frame_report.json").read_text())
    assert rep["exclusion_id_dropped"] == 1 and rep["exclusion_key_dropped"] == 3
    assert rep["filter_dropped"].get("life_lt_14d") == 1 and rep["filter_dropped"].get("weather") == 1
    assert 0 < len(sample) <= w.n_markets and rep["n_sample"] == len(sample)
    assert all(float(r["inclusion_prob"]) > 0 and float(r["sample_weight"]) >= 1 for r in sample.values())
    assert {"event_ids", "neg_risk_market_id", "series_ids", "description"} <= set(next(iter(sample.values())))


def test_no_forward_walk_and_no_row_after_cutoff(full):
    w, _, _ = full
    windows = [p for k, p in w.api.log if k == "gamma_window"]
    assert windows
    assert max(ep(p["end_date_max"]) for p in windows) <= CUTOFF
    assert min(ep(p["end_date_min"]) for p in windows) >= ep(END_FROM)
    for r in read_csv_gz(w.rdir / "frame.csv.gz"):
        assert float(r["end_epoch"]) <= CUTOFF
    # closed=false is walked before closed=true within a window
    first = {}
    for k, p in w.api.log:
        if k == "gamma_window":
            first.setdefault(p["end_date_min"], []).append(p["closed"])
    assert all(v[0] == "false" for v in first.values())


def test_origins_written_before_any_price_request_and_are_mondays(full):
    w, _, before = full
    assert before == [True]
    origins = read_csv_gz(w.rdir / "origins.csv.gz")
    sample = {r["market_id"]: r for r in read_csv_gz(w.rdir / "sample.csv.gz")}
    per: dict[str, list[int]] = {}
    for o in origins:
        ts = int(o["origin_ts"])
        assert datetime.fromtimestamp(ts, UTC).weekday() == 0 and ts % DAY == 0
        per.setdefault(o["market_id"], []).append(ts)
    assert per and all(1 <= len(v) <= 3 for v in per.values())
    for mid, v in per.items():
        r = sample[mid]
        for ts in v:
            assert ep(r["created_at"]) + 7 * DAY <= ts <= float(r["end_epoch"]) - DAY and ts <= NOW - 60 * DAY


def test_guarded_outcomes_only_in_guarded_file(full):
    w, _, _ = full
    g = read_csv_gz(w.rdir / t.OUTCOME_FILE)
    assert set(g[0]) == set(t.GUARDED_COLUMNS) and {r["market_id"] for r in g} == {r["market_id"] for r in read_csv_gz(w.rdir / "sample.csv.gz")}
    for name in ("frame.csv.gz", "sample.csv.gz", "origins.csv.gz", "exclusion_keys.csv.gz", "origin_windows.csv.gz"):
        head = read_csv_gz(w.rdir / name)[0]
        assert not ({"outcome_prices", "uma_status", "closed_time", "volume", "liquidity"} & set(head))
    man = (w.rdir / "manifest.json").read_text()
    assert "outcomePrices" not in man and "umaResolution" not in man


def test_no_raw_wallet_address_is_written(full):
    w, _, _ = full
    n = 0
    for p in w.rdir.rglob("*"):
        if p.is_file():
            raw = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
            assert b"walletaddr" not in raw.lower(), p
            n += 1
    assert n > 20
    wf = read_csv_gz(w.rdir / "wallet_first.csv.gz")
    assert wf and all(len(r["wallet_hash"]) == 64 for r in wf)  # one hashed first-trade row per qualifying buyer
    assert (w.rdir / "wallet_first.jsonl").exists() is False


def test_prices_prints_cap_and_windows(full):
    w, m, _ = full
    ow = read_csv_gz(w.rdir / "origin_windows.csv.gz")
    assert ow and all(int(r["print_pages"]) >= 1 for r in ow)
    assert sum(int(r["dropped_post_cap"] or 0) for r in ow) >= 0
    # the fidelity-60 request window is [t - 8 d, t + 2 d] and prints are windowed and taker-only
    pr = [p for k, p in w.api.log if k == "prices"]
    assert pr and all(int(p["endTs"]) - int(p["startTs"]) == 10 * DAY for p in pr)
    tr = [p for k, p in w.api.log if k == "trades"]
    assert tr and all(int(p["end"]) - int(p["start"]) == 30 * DAY + 6 * 3600 and p["takerOnly"] == "true" and int(p["limit"]) == 1000 for p in tr)
    some = next(r for r in ow if r["wallet_status"] == "ok")
    assert int(some["qualifying_wallets"]) >= 1
    assert m["counts"]["wallet_lookups_requested"] > 0
    assert sum(1 for k, _ in w.api.log if k == "activity") <= m["counts"]["wallet_lookups_requested"]  # cached lookups reused
    mid = next(iter({r["market_id"] for r in ow}))
    rows = read_csv_gz(w.rdir / "trades" / f"{mid}.csv.gz")
    assert rows and set(rows[0]) == set(hb.TRADE_COLUMNS)
    px = read_csv_gz(w.rdir / "prices" / f"{mid}.csv.gz")
    assert px and set(px[0]) == {"origin_ts", "t", "p"}


def test_rows_after_the_cap_are_dropped_and_counted():
    cap = 1_000_000.0
    prints = [{"timestamp": ts, "side": "BUY", "size": 1.0, "price": 0.05, "outcomeIndex": 0, "proxyWallet": "0xwalletaddr_x",
               "transactionHash": f"h{ts}", "asset": "a"} for ts in (900_000, 999_999, 1_000_000, 1_000_001, 1_500_000)]

    def api(url, params):
        if "prices-history" in url:
            return 200, json.dumps({"history": [{"t": x, "p": 0.05} for x in (990_000, 1_000_000, 1_000_600)]}).encode(), {}
        return 200, json.dumps(prints).encode(), {}  # the fake ignores the window: the cap must still hold

    lim = hb.Limiter(api, rps=4.0, sleep=lambda s: None)
    rows, info, addr = t.fetch_prints(lim, "c1", KEY, 0, 2_000_000, cap_epoch=cap, addr_from=0, addr_to=2_000_000)
    assert [r[0] for r in rows] == [900_000, 999_999, 1_000_000] and info["dropped_post_cap"] == 2
    assert len(addr) == 3 and all("walletaddr" not in str(r) for r in rows)  # rows carry hashes only
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        rec = t.fetch_tail_market(lim, {"market_id": "1", "token0": "tok", "condition_id": "c1"}, [995_000], KEY, Path(d),
                                  hb.DiskBudget(Path(d), 10**8), cap_epoch=cap)
        w = rec["origins"][0]
        assert w["price_dropped_post_cap"] >= 1 and w["dropped_post_cap"] == 2


def test_manifest_has_file_hashes_run_location_and_rules_hash(full):
    w, m, _ = full
    man = json.loads((w.rdir / "manifest.json").read_text())
    assert man["rules_sha256"] == json.loads(w.rules.read_text())["rules_sha256"]
    assert man["run_location"]["host"] and man["file_sha256"]["sample.csv.gz"] == hashlib.sha256((w.rdir / "sample.csv.gz").read_bytes()).hexdigest()
    assert "manifest.json" not in man["file_sha256"] and "frame_partial.jsonl.gz" not in man["file_sha256"]
    assert json.loads((w.rdir / "request_clock.json").read_text())["request_clock_epoch"] == NOW


# ---- resume, deadline -----------------------------------------------------------------------------------------------------------------


def test_resume_gives_same_result_and_never_refetches_done_markets(tmp_path):
    a = World(tmp_path / "a")
    a.run()
    b = World(tmp_path / "b")
    calls = {"n": 0}

    def stop_after_prices():
        return calls["n"] >= 8

    b.api.hooks.append(lambda k, p: calls.__setitem__("n", calls["n"] + (k == "prices")))
    m1 = b.run(should_stop=stop_after_prices)
    assert m1["stopped"] == "should_stop" and m1.get("status") == "in_progress"
    done_before = {json.loads(x)["market_id"] for x in (b.rdir / "progress.jsonl").read_text().splitlines()}
    assert 0 < len(done_before) < 30
    b.api.log.clear()
    m2 = b.run()
    assert m2["status"] == t.COMPLETE_TOKEN
    tokens = {p["market"] for k, p in b.api.log if k == "prices"}
    assert not any(f"tok{mid}a" in tokens for mid in done_before)  # finished markets are not fetched again
    assert not any(k in ("gamma_ids", "gamma_window") for k, _ in b.api.log)  # finished stages are skipped
    for name in ("sample.csv.gz", "origins.csv.gz", "exclusion_keys.csv.gz"):
        assert gzip.decompress((a.rdir / name).read_bytes()) == gzip.decompress((b.rdir / name).read_bytes())
    pa = {r["market_id"]: r for r in read_csv_gz(a.rdir / "origin_windows.csv.gz")}
    pb = {r["market_id"]: r for r in read_csv_gz(b.rdir / "origin_windows.csv.gz")}
    assert pa == pb


def test_deadline_no_chunk_starts_at_or_after_t_seal(tmp_path):
    w = World(tmp_path)
    m = w.run(wall_clock=lambda: t.T_SEAL_EPOCH + 1)
    assert m["status"] == t.NOT_RUN_TOKEN
    assert (w.rdir / t.NOT_RUN_FILE).exists() and not w.api.log
    man = json.loads((w.rdir / "manifest.json").read_text())
    assert man["stopped"] == t.NOT_RUN_TOKEN and man["complete"] is False
    assert w.run(wall_clock=lambda: NOW)["status"] == t.NOT_RUN_TOKEN  # terminal even if the clock were earlier
    with pytest.raises(t.Refused):
        t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals)


def test_deadline_reached_mid_chunk_stops_and_marks_not_run(tmp_path):
    w = World(tmp_path)
    clock = {"now": NOW}
    n = {"c": 0}

    def tick(kind, params):
        n["c"] += kind == "prices"
        if n["c"] > 6:
            clock["now"] = t.T_SEAL_EPOCH + 5

    w.api.hooks.append(tick)
    m = w.run(wall_clock=lambda: clock["now"])
    assert m["status"] == t.NOT_RUN_TOKEN
    assert (w.rdir / t.NOT_RUN_FILE).exists()
    count = len(w.api.log)
    assert w.run(wall_clock=lambda: clock["now"])["status"] == t.NOT_RUN_TOKEN and len(w.api.log) == count


# ---- pure rules --------------------------------------------------------------------------------------------------------------------------


def test_origin_draw_uses_dates_only_and_is_deterministic():
    created, end = ep("2026-02-01T10:00:00Z"), ep("2026-07-01T00:00:00Z")
    a = t.draw_origins("123", created, end, NOW)
    assert a == t.draw_origins("123", created, end, NOW) and 1 <= len(a) <= 3 and a == sorted(set(a))
    for ts in a:
        assert datetime.fromtimestamp(ts, UTC).weekday() == 0 and created + 7 * DAY <= ts <= end - DAY
    assert t.draw_origins("123", created, ep("2026-02-05T00:00:00Z"), NOW) == []  # no Monday inside the life
    assert t.draw_origins("123", created, end, ep("2026-03-01T00:00:00Z")) == []  # T_fetch8 - 60 d before the grid
    assert t.monday_grid(0, 20 * DAY) == [4 * DAY, 11 * DAY, 18 * DAY]


def test_class_regex_and_clarification_markers():
    assert t.class_d("Will the court rule against X?", "")
    assert not t.class_d("Will the price be above 5?", "")
    assert not t.class_d("Will the strike price exceed 3?", "")  # strike (D) and price (C) -> not D
    assert t.class_d("Will it happen?", "The ministry will announce the result.")  # description fallback
    assert not t.class_d("Will it happen?", "x" * 600 + " announce")  # only the first 500 characters
    assert t.has_clarification("Update: the rules changed") and t.has_clarification("Note: 12 March was added")
    assert not t.has_clarification("a note about updates") or t.has_clarification("updated")
    assert not t.has_clarification("nothing to see")


def test_usable_point_and_large_buy_rule():
    ts, vals = [1000.0, 4600.0], [0.04, 0.05]
    assert t.usable_point(ts, vals, 4600 + 540) == 0.04  # 9 minutes after the point: not usable, take the earlier one
    assert t.usable_point(ts, vals, 4600 + 600) == 0.05  # 10 minutes: usable
    assert t.usable_point(ts, vals, 4600 + 600 + 7200) is None  # too old
    T = 100 * DAY
    prints = [[T - 3 * DAY + i * 600, "BUY", 10.0, 0.05, 0, f"w{i}", f"k{i}"] for i in range(20)]
    prints.append([T - 3600, "BUY", 400.0, 0.05, 0, "big", "kb"])
    prints.append([T, "BUY", 9999.0, 0.05, 0, "now", "kn"])  # at t: strictly before only
    prints.append([T - 1800, "SELL", 400.0, 0.95, 1, "bigsell", "ks"])  # SELL of the other token buys c at 1 - 0.95
    prints.append([T - 900, "SELL", 400.0, 0.05, 0, "seller", "kq"])  # a SELL of c is not a buy of c
    st, q = t.qualifying_buyers(prints, T, 0, False)
    assert st == "ok" and set(q) == {"big", "bigsell"}  # bigsell: 400 x (1 - 0.95) = 20 >= 5 x median 0.5
    st2, q2 = t.qualifying_buyers(prints, T, 0, True)
    assert st2 == "unavailable_truncated" and q2 == {}
    assert t.qualifying_buyers(prints[:5], T, 0, False)[0] == "unavailable_median"


# ---- streaming ---------------------------------------------------------------------------------------------------------------------------


def test_frame_filtering_streams_with_bounded_memory(tmp_path):
    from astrolabe.research_lab import history_backfill as hbm

    rdir = tmp_path / "run"
    rdir.mkdir()
    rng = random.Random(1)
    day0 = datetime(2026, 3, 1, tzinfo=UTC)
    n_days, per_day = 40, 100
    total_chars = 0
    for d in range(n_days):
        rows, outs = [], []
        for j in range(per_day):
            mid = str(d * per_day + j + 1)
            end = (day0 + timedelta(days=d, minutes=j)).timestamp()
            desc = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789 ") for _ in range(3000))
            total_chars += len(desc)
            r = {c: "" for c in t.MAIN_COLUMNS}
            r.update(market_id=mid, condition_id=f"c{mid}", token0="a", token1="b", event_id=f"E{mid}", event_ids=f"E{mid}",
                     status="closed", closed=1, created_at=iso(end - 30 * DAY), end_epoch=end, topic="other",
                     question=f"q {mid}", event_title="e", slug="s", description=desc, fee_category="unknown")
            rows.append(r)
            outs.append({c: "" for c in t.GUARDED_COLUMNS} | {"market_id": mid})
        w = {"day": f"d{d}", "rows": rows, "outs": outs, "windows": {"closed": 1, "active": 1}, "dropped": {"closed": 0, "active": 0},
             "dropped_rows": 0, "raw": per_day, "invalid": 0, "dups": 0, "failed_windows": 0}
        with (rdir / "frame_partial.jsonl.gz").open("ab") as fh:
            fh.write(t._gz_jsonl_member(w))
    assert total_chars == 12_000_000  # 12 MB of descriptions, all in the partial file
    fr = SimpleNamespace(rdir=rdir, budget=hbm.DiskBudget(rdir, 10**9))
    tracemalloc.start()
    rep = t.build_frame_outputs(fr, cutoff_epoch=NOW, excl_ids=set(), excl_keys={"event": set(), "neg_risk_market": set(), "series": set()},
                                n_markets=40, seed=SEED, t_fetch=NOW)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert rep["frame_rows"] == n_days * per_day and rep["n_sample"] == 40
    assert peak < 6_000_000, peak  # far below the 12 MB of raw descriptions: nothing is accumulated
    assert not (rdir / "frame_partial.jsonl.gz").exists() and (rdir / "frame_report.json").exists()


# ---- smoke ----------------------------------------------------------------------------------------------------------------------------------


def _smoke_world(tmp_path, n_good):
    w = World(tmp_path)
    files = t.verify_exclusion_files(w.pins, history_root=w.root, seals_dir=w.seals)
    # 36 sample ids exist (h1/h2/h3), 20 are drawn; make the first n_good drawn ids return hourly data
    cands = t.smoke_candidates(files, w.pins)[:20]
    good = {f"tok{c['market_id']}a" for c in cands[:n_good]}

    def api(url, params):
        if "prices-history" in url:
            a, b = int(params["startTs"]), int(params["endTs"])
            step = 3600 if params["market"] in good else 21600
            return 200, json.dumps({"history": [{"t": x, "p": 0.5} for x in range(a, b, step)]}).encode(), {}
        raise AssertionError(url)

    lim = hb.Limiter(api, rps=4.0, sleep=lambda s: None)
    return w, files, lim


@pytest.mark.parametrize(("n_good", "expect"), [(20, True), (18, True), (17, False)])
def test_smoke_pass_rule_is_18_of_20_and_stores_counts_only(tmp_path, n_good, expect):
    w, files, lim = _smoke_world(tmp_path, n_good)
    res = t.run_smoke(lim, files, w.pins, "abc")
    assert res["pass"] is expect and res["n_requested"] == 20 and res["n_pass"] == n_good
    text = json.dumps(res)
    assert "tok" not in text and "9000" not in text and res["counts_only"] is True
    assert res["rules_sha256"] == "abc"


def test_smoke_fails_when_fewer_than_20_candidates(tmp_path):
    w = World(tmp_path)
    write_sample(w.root / "h1_first" / "sample.csv.gz", ["9000"])
    pins = [{**p, "sha256": hashlib.sha256((w.root / p["path"]).read_bytes()).hexdigest()} if p["kind"] == "sample" else p for p in w.pins]
    files = t.verify_exclusion_files(pins, history_root=w.root, seals_dir=w.seals)
    for k in ("h2_main", "h3_power"):
        write_sample(w.root / k / "sample.csv.gz", [])
    pins = [{**p, "sha256": hashlib.sha256((w.root / p["path"]).read_bytes()).hexdigest()} if p["kind"] == "sample" else p for p in pins]
    files = t.verify_exclusion_files(pins, history_root=w.root, seals_dir=w.seals)
    lim = hb.Limiter(lambda u, p: (200, b'{"history": []}', {}), rps=4.0, sleep=lambda s: None)
    assert t.run_smoke(lim, files, pins, "x")["pass"] is False


# ---- split and seal -----------------------------------------------------------------------------------------------------------------------------


def test_event_key_split_keeps_neg_risk_members_together():
    rows = [{"market_id": "1", "event_ids": "10", "neg_risk_market_id": "NR"}, {"market_id": "2", "event_ids": "11", "neg_risk_market_id": "NR"},
            {"market_id": "3", "event_ids": "12", "neg_risk_market_id": ""}, {"market_id": "4", "event_ids": "", "neg_risk_market_id": ""},
            {"market_id": "5", "event_ids": "10", "neg_risk_market_id": ""}]
    s = t.event_key_split(rows)
    assert s["1"] == s["2"] == s["5"] and s["1"][0] == "10"
    assert s["4"][0] == "m4"
    first = hashlib.sha256(f"{t.SPLIT_SEED}|10".encode()).digest()[0]
    assert s["1"][1] == ("SCREEN" if first % 2 == 0 else "HOLDOUT")
    many = t.event_key_split([{"market_id": str(i), "event_ids": str(i), "neg_risk_market_id": ""} for i in range(400)])
    assert {b for _, b in many.values()} == {"SCREEN", "HOLDOUT"}


def test_seal_split_h7_drop_recheck_and_committed_copy(tmp_path):
    w = World(tmp_path)
    assert w.run()["status"] == t.COMPLETE_TOKEN
    sample = read_csv_gz(w.rdir / "sample.csv.gz")
    by_id = {r["market_id"]: r for r in sample}
    # h7 pending: not now
    with pytest.raises(t.NotNow):
        t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals)
    victim = sample[0]["market_id"]
    sibling = next(r["market_id"] for r in sample if r["market_id"] != victim)
    # an h7 market (id h7x) shares the event of `sibling`; `victim` itself is in the h7 seal copy
    h7x = gm("777001", ep("2026-05-01T00:00:00Z"), event=by_id[sibling]["event_ids"].split(";")[0])
    h7y = gm(victim, ep("2026-05-01T00:00:00Z"))
    api = FakeApi([h7x, h7y])
    write_seal_copy(w.seals / "h7_cb4_era_SEAL.json", ["777001", victim])
    (w.seals / "h7_cb4_series_NOT_RUN.json").write_text("{}")
    # a residual key match (expected 0) planted in the stored key set
    resid = next(r["market_id"] for r in sample if r["market_id"] not in (victim, sibling))
    keys = read_csv_gz(w.rdir / "exclusion_keys.csv.gz")
    keys[0]["event_ids"] += ";" + by_id[resid]["event_ids"].split(";")[0]
    import csv
    import io

    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=t.KEY_COLUMNS)
    wr.writeheader()
    wr.writerows(keys)
    (w.rdir / "exclusion_keys.csv.gz").write_bytes(gzip.compress(buf.getvalue().encode()))
    mf = json.loads((w.rdir / "manifest.json").read_text())  # the planted file is re-pinned: the seal checks fetch hashes
    mf["file_sha256"]["exclusion_keys.csv.gz"] = hashlib.sha256((w.rdir / "exclusion_keys.csv.gz").read_bytes()).hexdigest()
    (w.rdir / "manifest.json").write_text(json.dumps(mf))
    trials = tmp_path / "trials.jsonl"
    res = t.seal_tail(w.root, t.RUN_ID, transport=api, seals_dir=w.seals, trials_path=trials, sleep=lambda s: None)
    assert res["sealed"] and res["residual_key_matches"] >= 1 and res["h7_dropped"] >= 2
    split = {r["market_id"]: r for r in read_csv_gz(w.rdir / "split.csv.gz")}
    assert split[victim]["block"] == "DROPPED_H7" and split[sibling]["block"] == "DROPPED_H7" and split[resid]["block"] == "DROPPED_KEY"
    blocks = {r["block"] for r in split.values()}
    assert {"SCREEN", "HOLDOUT"} & blocks
    assert set(split) == {r["market_id"] for r in sample}
    seal = json.loads((w.rdir / "SEAL.json").read_text())
    assert seal["read_location"]["location"] in ("host", "mac") and seal["split"]["counts"]["DROPPED_H7"] == res["h7_dropped"]
    assert seal["key_recheck"]["h7"] == {"h7_cb4_era": "sealed", "h7_cb4_series": "not_run"}
    assert (w.rdir / "ACCESS_LOG.jsonl").exists()
    copy = w.seals / "h8_tail_SEAL.json"
    assert copy.read_bytes() == (w.rdir / "SEAL.json").read_bytes()
    assert t.verify_tail(w.root, t.RUN_ID, w.seals)["listing_sha256"] == seal["listing_sha256"]
    line = json.loads(trials.read_text().splitlines()[-1])
    assert line["kind"] == "history_seal_declaration" and line["run_id"] == t.RUN_ID
    assert {"split.csv.gz", "h7_drop.csv.gz", "key_recheck.json", "outcomes_guarded.csv.gz"} <= set(seal["files"])
    with pytest.raises(t.Refused):  # sealed runs are never fetched into again
        w.run()
    with pytest.raises(t.SealError):
        t.seal_tail(w.root, t.RUN_ID, transport=api, seals_dir=w.seals, trials_path=trials, sleep=lambda s: None)
    (w.rdir / "sample.csv.gz").write_bytes(b"tampered")
    with pytest.raises(t.SealError):
        t.verify_tail(w.root, t.RUN_ID, w.seals)


def test_seal_refuses_an_incomplete_run(tmp_path):
    w = World(tmp_path)
    w.run(should_stop=lambda: len([1 for k, _ in w.api.log if k == "prices"]) >= 3)
    write_seal_copy(w.seals / "h7_cb4_era_SEAL.json", [])
    (w.seals / "h7_cb4_series_NOT_RUN.json").write_text("{}")
    with pytest.raises(t.Refused):
        t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals)


# ---- runner -----------------------------------------------------------------------------------------------------------------------------------------


def test_runner_refuses_changed_declaration_and_writes_rules(tmp_path, capsys):
    assert script.main(["tail-fetch", "--seed", "other", "--root", str(tmp_path / "r")]) == 2
    assert script.main(["tail-fetch", "--n-markets", "100", "--root", str(tmp_path / "r")]) == 2
    assert script.main(["tail-fetch", "--cap-at", "2026-11-01T00:00Z", "--root", str(tmp_path / "r")]) == 2
    assert script.main(["tail-fetch", "--exclude-runs", "h1_first", "--root", str(tmp_path / "r")]) == 2
    p = tmp_path / "rules.json"
    assert script.main(["rules", "--path", str(p)]) == 0
    assert t.verify_rules(p, require_committed=False)
    out = capsys.readouterr().out
    assert "rules_sha256" in out
    # declared arguments but no rules file / pins at this root: a refusal, not a crash
    assert script.main(["tail-fetch", "--root", str(tmp_path / "r"), "--rules", str(tmp_path / "none.json"), "--standalone"]) == 2
    parser = script.build_parser()
    for sub in ("tail-smoke", "tail-fetch", "tail-seal", "fetch", "seal", "exclusion-keys", "verify-seal", "rules"):
        assert parser.parse_args([sub]).cmd == sub


# ---- freeze-check fixes (2026-10-17) -----------------------------------------------------------------------------------------------------------------


def test_seal_refuses_a_file_changed_or_missing_since_the_fetch(tmp_path):
    w = World(tmp_path)
    assert w.run()["status"] == t.COMPLETE_TOKEN
    write_seal_copy(w.seals / "h7_cb4_era_SEAL.json", [])
    (w.seals / "h7_cb4_series_NOT_RUN.json").write_text("{}")
    f = w.rdir / "origins.csv.gz"
    good = f.read_bytes()
    f.write_bytes(good + b"x")
    with pytest.raises(t.Refused, match="sha256"):
        t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals)
    f.unlink()
    with pytest.raises(t.Refused, match="missing"):
        t.seal_tail(w.root, t.RUN_ID, seals_dir=w.seals)
    f.write_bytes(good)
    assert t.seal_tail(w.root, t.RUN_ID, transport=FakeApi([]), seals_dir=w.seals, trials_path=tmp_path / "tr.jsonl",
                       sleep=lambda s: None)["sealed"]


def test_outcomes_resolved_after_the_run_clock_are_censored_and_counted(tmp_path):
    w = World(tmp_path)
    for m in w.frame_markets:
        late = int(m["id"]) % 2 == 0
        m["closed"] = True
        m["closedTime"] = iso(NOW + 3600) if late else iso(ep(m["endDate"]) + 3600)
        m["outcomePrices"] = '["0.04","0.96"]'
        m["umaResolutionStatus"] = "resolved"
    assert w.run()["status"] == t.COMPLETE_TOKEN
    rep = json.loads((w.rdir / "frame_report.json").read_text())
    g = read_csv_gz(w.rdir / t.OUTCOME_FILE)
    blank = [r for r in g if r["close_epoch"] == ""]
    kept = [r for r in g if r["close_epoch"] != ""]
    assert blank and kept and rep["outcomes_censored_post_cap"] == len(blank)
    assert all(int(r["market_id"]) % 2 == 0 and not r["outcome_prices"] and not r["uma_status"] and not r["closed_time"] for r in blank)
    assert all(int(r["market_id"]) % 2 == 1 and r["outcome_prices"] and float(r["close_epoch"]) <= NOW for r in kept)


def test_full_disk_budget_is_a_declared_end_state_with_exit_4(tmp_path):
    w = World(tmp_path)
    m = w.run(disk_cap=60_000)
    assert m["status"] == t.DISK_BUDGET_TOKEN and str(m["stopped"]).startswith("disk_budget")
    on_disk = json.loads((w.rdir / "manifest.json").read_text())
    assert on_disk["status"] == t.DISK_BUDGET_TOKEN and on_disk["complete"] is False
    assert script.DISK_BUDGET == 4 and script.DISK_BUDGET not in (script.TEMPFAIL, script.REFUSED)


def _pins_for(w):
    return [{**p, "sha256": hashlib.sha256((w.root / p["path"]).read_bytes()).hexdigest()} if p["kind"] == "sample" else p
            for p in w.pins]


def test_smoke_v2_pool_keeps_only_windows_inside_the_market_life(tmp_path):
    w = World(tmp_path)
    end = ep("2025-06-15T00:00:00Z")
    write_sample(w.root / "h1_first" / "sample.csv.gz", ["a1", "a2"])  # life 60 d, closes at end: kept
    write_sample(w.root / "h2_main" / "sample.csv.gz", ["b1", "b2", "b3"], life_days=6.5)  # v1 failure mode: dropped
    write_sample(w.root / "h3_power" / "sample.csv.gz", ["c1"], close_minus_end_days=-3.0)  # early close: dropped
    pins = _pins_for(w)
    files = t.verify_exclusion_files(pins, history_root=w.root, seals_dir=w.seals)
    pool, counts = t.smoke_pool(files, pins)
    assert {r["market_id"] for r in pool} == {"a1", "a2"}
    assert counts == {"n_closed_end_2025": 6, "drop_no_created": 0, "drop_life_lt_14d": 3, "drop_no_close": 0,
                      "drop_closed_before_window_end": 1, "n_pool": 2}
    # exactly 14 d of life is kept; close exactly at end - 2 d is kept (window end inclusive)
    write_sample(w.root / "h2_main" / "sample.csv.gz", ["d1"], life_days=14.0)
    write_sample(w.root / "h3_power" / "sample.csv.gz", ["e1"], close_minus_end_days=-2.0)
    write_sample(w.root / "h1_first" / "sample.csv.gz", ["f1"], created=False)
    pins = _pins_for(w)
    files = t.verify_exclusion_files(pins, history_root=w.root, seals_dir=w.seals)
    pool, counts = t.smoke_pool(files, pins)
    assert {r["market_id"] for r in pool} == {"d1", "e1"} and counts["drop_no_created"] == 1
    assert all(r["end_epoch"] == end for r in pool) and set(pool[0]) == {"market_id", "token0", "end_epoch"}


def test_smoke_v2_result_carries_version_and_pool_counts(tmp_path):
    w, files, lim = _smoke_world(tmp_path, 20)
    res = t.run_smoke(lim, files, w.pins, "abc")
    assert res["smoke_version"] == "h8-tail-smoke-v2" and res["pool_counts"]["n_pool"] == res["n_candidates_available"]
    assert res["supersedes"] == t.SMOKE_V1_RECORD["copy_sha256"]


def test_smoke_ok_refuses_a_v1_result_even_if_pass(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"pass": True, "rules_sha256": "abc", "smoke_version": "h8-tail-smoke-v1"}))
    with pytest.raises(t.Refused):
        t.smoke_ok(p, "abc")
    p.write_text(json.dumps({"pass": True, "rules_sha256": "abc", "smoke_version": "h8-tail-smoke-v2"}))
    assert t.smoke_ok(p, "abc")["pass"] is True


def test_smoke_v2_refuses_the_v1_result_name(tmp_path, capsys):
    out = tmp_path / "tail_smoke.json"
    assert script.main(["tail-smoke", "--out", str(out), "--root", str(tmp_path / "r")]) == 2
    assert not out.exists() and "smoke v1 result name" in capsys.readouterr().out
    assert t.SMOKE_DEFAULT.name == "tail_smoke2.json"


def test_smoke_v1_fail_copy_is_recorded_byte_identical():
    copy = Path(__file__).resolve().parents[3] / t.SMOKE_V1_RECORD["copy"]
    if not copy.exists():
        pytest.skip("FAIL copy not present")
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == t.SMOKE_V1_RECORD["copy_sha256"]
    d = json.loads(copy.read_text())
    assert d["pass"] is False and d["n_pass"] == 4 and d["rules_sha256"] == t.SMOKE_V1_RECORD["rules_sha256"]


def test_v1_rules_file_is_kept_and_differs_from_v2():
    if not t.RULES_FILE_V1.exists():
        pytest.skip("v1 rules file not present")
    assert json.loads(t.RULES_FILE_V1.read_text())["rules_sha256"] == t.SMOKE_V1_RECORD["rules_sha256"]
    assert t.RULES_FILE != t.RULES_FILE_V1


def test_smoke_result_is_write_once(tmp_path, capsys):
    out = tmp_path / "smoke.json"
    out.write_text(json.dumps({"pass": False}))
    assert script.main(["tail-smoke", "--out", str(out), "--root", str(tmp_path / "r")]) == 2
    assert json.loads(out.read_text()) == {"pass": False}
    assert "write-once" in capsys.readouterr().out


def test_rule_funcs_cover_split_topic_weather_and_row_builder():
    names = {f.__name__ for f in t.RULE_FUNCS}
    assert {"event_key_split", "cb1_topic", "_is_weather", "tail_row"} <= names
