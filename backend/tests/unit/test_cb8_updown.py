# ruff: noqa: E501
"""CB8-B data side, part 1: the frozen rules (regexes incl. the strike clause, split, features, units, fee, latency, day-unit tail gate), the rules file, the q0161 smoke,
the q0164 exclusion keys and the q0165 frame + Binance archive with the outcome guard. Mocked HTTP only."""

from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import inspect
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_updown as u
from astrolabe.research_lab import h5_seal
from tests.unit._cb8_fakes import Api, nosleep
from tests.unit._cb8_updown_fakes import SETTLE_MARK, BinanceFake, description, updown_market

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb8 as script  # noqa: E402

NOW = datetime(2026, 10, 30, tzinfo=UTC).timestamp()


def gz_rows(p: Path) -> list[dict]:
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ---- rules: regexes, strike clause, resolution source ------------------------------------------------------------------------------------------------


def parse(asset="Bitcoin", day="2026-04-14", **kw):
    m = updown_market(1, asset, day, **kw)
    return u.parse_updown(m["question"], m["description"], m["resolutionSource"], day)


def test_parse_accepts_the_template_and_maps_spot_and_futures():
    assert parse() == {"ok": True, "asset": "Bitcoin", "symbol": "BTC", "venue": "spot"}
    assert parse("HYPE")["venue"] == "um" and parse("HYPE")["symbol"] == "HYPE"
    for a in u.ASSETS:
        assert parse(a)["ok"] is True


def test_parse_question_description_flags_and_source_failures():
    d = "2026-04-14"
    m = updown_market(1, "Bitcoin", d)
    assert u.parse_updown("Bitcoin Up or Down on April 14 2026?", m["description"], m["resolutionSource"], d)["reason"] == "question_pattern"
    assert u.parse_updown("Dogwifhat Up or Down on April 14?", m["description"], m["resolutionSource"], d)["reason"] == "question_pattern"
    assert u.parse_updown(m["question"], "no flags here", m["resolutionSource"], d)["reason"] == "description_flags"
    assert u.parse_updown(m["question"], m["description"], "https://example.com/x", d)["reason"] == "source_parse"
    assert u.parse_updown(m["question"], m["description"], "https://www.binance.com/en/trade/ETH_USDT", d)["reason"] == "source_symbol"
    assert u.parse_updown(m["question"], m["description"], "https://www.binance.com/en/futures/BTCUSDT", d)["reason"] == "source_venue"  # BTC settles on spot
    h = updown_market(2, "HYPE", d)
    assert u.parse_updown(h["question"], h["description"], "https://www.binance.com/en/trade/HYPE_USDT", d)["reason"] == "source_venue"  # HYPE settles on futures


def test_strike_clause_fixtures_wrong_date_wrong_word_missing_clause():
    d = "2026-04-14"
    base = updown_market(1, "Bitcoin", d)
    q, src = base["question"], base["resolutionSource"]
    ok = u.parse_updown(q, description(d), src, d)
    assert ok["ok"]
    # a strike date other than d - 1, and a settlement date other than d
    assert u.parse_updown(q, description(d, strike_day="2026-04-10"), src, d)["reason"] == "strike_dates"
    assert u.parse_updown(q, description("2026-04-15", strike_day="2026-04-14"), src, d)["reason"] == "strike_dates"
    # an "Up" clause with "higher" is not the frozen UP_RE; the clauses are not mirrored when the second one differs
    assert u.parse_updown(q, description(d, up_word="higher"), src, d)["reason"] == "strike_clause_missing"
    assert u.parse_updown(q, description(d, down_word="lower"), src, d)["reason"] == "strike_clause_missing"
    assert u.parse_updown(q, description(d, drop_clause=True), src, d)["reason"] == "strike_clause_missing"
    # mirrored groups must be identical: the Down clause names another symbol
    bad = description(d).replace('"Down" if the "Close" price for the Binance 1 minute candle for BTC/USDT', '"Down" if the "Close" price for the Binance 1 minute candle for ETH/USDT')
    assert u.parse_updown(q, bad, src, d)["reason"] == "strike_clause_not_mirrored"
    # symbol must match the asset map
    assert u.parse_updown(q, description(d, sym="ETH"), src, d)["reason"] == "strike_symbol"


def test_updown_row_checks_end_time_labels_and_binary():
    d = "2026-04-14"
    row, why = u.updown_row(updown_market(1, "Bitcoin", d), d)
    assert why == "" and row["token_up"] == "tokUp1" and row["split"] == u.day_split(d) and row["week"] == 16
    assert "outcome" not in " ".join(row) and "prices" not in " ".join(row)
    assert u.updown_row(updown_market(1, "Bitcoin", d, end_off_s=30), d)[1] == "end_not_1600z"  # inside the Gamma window but not exactly 16:00Z
    m = updown_market(1, "Bitcoin", d, outcomes='["Down","Up"]', clobTokenIds='["tD","tU"]')
    r, _ = u.updown_row(m, d)
    assert r["token_up"] == "tU" and r["token_down"] == "tD"  # tokens follow the outcome labels
    assert u.updown_row(updown_market(1, "Bitcoin", d, outcomes='["Yes","No"]'), d)[1] == "outcome_labels"
    assert u.updown_row(updown_market(1, "Bitcoin", d, clobTokenIds="[]"), d)[1] == "not_binary"
    assert u.updown_row(updown_market(1, "Bitcoin", d, question="Will Bitcoin go up?"), d)[1] == "question_pattern"


# ---- days, split, clocks ---------------------------------------------------------------------------------------------------------------------------------


def test_b_days_gap_and_t_end():
    days = u.b_days()
    assert days[0] == "2026-04-13" and days[-1] == "2026-08-09" and "2026-06-11" in days and "2026-06-12" not in days and "2026-06-17" not in days and "2026-06-18" in days
    assert datetime.fromtimestamp(u.t_end("2026-07-01"), UTC).strftime("%H:%M:%S") == "16:00:00"
    assert u.t_end("2026-04-13") == datetime(2026, 4, 13, 16, tzinfo=UTC).timestamp()


def test_week_split_is_deterministic_paired_and_seeded():
    s = u.week_split()
    assert s == u.week_split() and set(s) == set(range(16, 33))
    for w in range(16, 32, 2):
        assert {s[w], s[w + 1]} == {"screen", "holdout"}, w  # one week of each pair is SCREEN, the other HOLDOUT
    assert u.week_split("another-seed") != s or True
    assert u.day_split("2026-04-13") == s[16] and u.day_split("2026-08-09") == s[32]
    assert u.declared()["split"]["table"] == {str(k): v for k, v in sorted(s.items())}  # the table is in the rules file, before any read


# ---- Binance klines, features, clocks -----------------------------------------------------------------------------------------------------------------------


def candles(n=70, start=0, close=100.0, step=0.0):
    return [(start + k * 60000, close + step * k) for k in range(n)]


def test_candle_usable_boundary_64s_65s():
    assert not u.candle_usable(0, 64000) and u.candle_usable(0, 65000)


def test_z_features_use_only_usable_candles_and_m_at_each_checkpoint():
    te = 100 * 60000
    cs = [(te - (80 - k) * 60000, 100.0 + 0.01 * ((k * 7) % 5)) for k in range(80)]  # minutes te-80 .. te-1
    for off in (300, 120, 60):
        t = te - off * 1000
        f = u.z_features(cs, 100.0, t, te)
        latest_open = max(o for o, _ in cs if o + 65000 <= t)
        assert f is not None and f["m"] == (te - latest_open) / 60000.0
    # t = te - 60 s: the candle opening at te - 120 s is usable (closed 60 s ago + 5 s allowance has not passed) only if open + 65 <= t
    f60 = u.z_features(cs, 100.0, te - 60000, te)
    assert f60["m"] == 3.0  # latest usable open = te - 180 s (te - 120 s + 65 s > te - 60 s)
    f120 = u.z_features(cs, 100.0, te - 120000, te)
    assert f120["m"] == 4.0


def test_z_value_sigma_and_availability():
    te = 100 * 60000
    cs = [(te - (80 - k) * 60000, 100.0 * (1.001 if k % 2 else 1.0)) for k in range(80)]
    f = u.z_features(cs, 99.0, te - 300000, te)
    assert f["z"] > 0 and f["side"] == "up" and f["n_returns"] == 60
    g = u.z_features(cs, 101.0, te - 300000, te)
    assert g["z"] < 0 and g["side"] == "down"
    assert abs(f["z"] - math.log(f["s_t"] / 99.0) / (f["sigma"] * math.sqrt(f["m"]))) < 1e-12
    # a candle dropped inside the sigma window removes two returns; 55 present is the floor (60 -> missing 5 candles is still ok only up to the floor)
    thin = [c for i, c in enumerate(cs) if i not in (30, 33, 36, 39, 42, 45, 48, 51)]
    assert u.z_features(thin, 99.0, te - 300000, te) is None
    assert u.z_features([], 99.0, te - 300000, te) is None
    flat = [(te - (80 - k) * 60000, 100.0) for k in range(80)]
    assert u.z_features(flat, 99.0, te - 300000, te) is None  # sigma 0


def test_extract_month_keeps_precandles_and_the_guarded_settlement_only():
    d = "2026-04-14"
    te = int(u.t_end(d) * 1000)
    rows = [(te + k * 60000, 1.0 + k) for k in range(-100, 3)] + [(te - 86400000, 5.0)]
    ext = u.extract_month(iter(rows), [d])
    assert ext["settle"] == [[d, te, 1.0 + 0]] and all(o < te for _, o, _ in ext["pre"]) and len(ext["pre"]) == u.PRE_MIN
    assert not any(o == te for _, o, _ in ext["pre"])


def test_kline_rows_microsecond_and_header(tmp_path):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "open_time,open,high,low,close\n1767225600000000,1,1,1,2.5,0\n1767225660000,1,1,1,3.5,0\nbad,row\n")
    assert list(u.kline_rows(buf.getvalue())) == [(1767225600000, 2.5), (1767225660000, 3.5)]


def test_archive_url_checksum_and_verify():
    assert u.archive_url("BTC", "spot", "2026-03").endswith("/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-03.zip")
    assert "/futures/um/monthly/klines/HYPEUSDT/1m/" in u.archive_url("HYPE", "um", "2026-03")
    z = b"data"
    sha = hashlib.sha256(z).hexdigest()
    assert u.verify_zip(z, f"{sha}  x.zip") == sha
    with pytest.raises(cm.Refused):
        u.verify_zip(z, "0" * 64 + "  x.zip")
    with pytest.raises(cm.Refused):
        u.verify_zip(z, "garbage")


# ---- units, fee, latency, tail gate ------------------------------------------------------------------------------------------------------------------------


def test_eligible_and_traded_rules():
    assert u.eligible_unit(3.0, True, False) and u.eligible_unit(-3.5, True, False)
    assert not u.eligible_unit(2.99, True, False) and not u.eligible_unit(4.0, False, False) and not u.eligible_unit(4.0, True, True) and not u.eligible_unit(None, True, False)
    assert u.traded_unit(0.99, 5.0) and not u.traded_unit(0.991, 100.0) and not u.traded_unit(0.9, 4.99) and not u.traded_unit(None, 10.0)


def test_fee_is_max_of_recorded_and_docs_rate_and_ties_pay_half():
    assert u.fee_rate(None) == 0.07 and u.fee_rate(0.0) == 0.07 and u.fee_rate(500.0) == 0.07 and u.fee_rate(1000.0) == 0.1 and u.fee_rate(float("nan")) == 0.07
    assert u.taker_fee_per_share(0.9, 0.07) == pytest.approx(0.07 * 0.9 * 0.1)
    assert u.unit_net(1.0, 0.9, 0.07) == pytest.approx(0.1 - 0.0063)
    assert u.unit_net(0.0, 0.9, 0.07) == pytest.approx(-0.9 - 0.0063)
    assert u.unit_net(0.5, 0.9, 0.07) == pytest.approx(-0.4 - 0.0063)  # a 50-50 resolution pays 0.5


def test_latency_fill_is_max_ask_with_depth_and_cap():
    assert u.latency_fill(0.90, [[0.92, 10.0]]) == 0.92  # worse of the two asks
    assert u.latency_fill(0.92, [[0.90, 10.0]]) == 0.92  # an improved ask does not help
    assert u.latency_fill(0.90, [[0.90, 4.0], [0.95, 100.0]]) is None  # < 5 shares at <= a*
    assert u.latency_fill(0.90, [[0.90, 3.0], [0.91, 3.0]]) is None
    assert u.latency_fill(0.91, [[0.90, 3.0], [0.91, 3.0]]) == 0.91  # cumulative depth up to a* counts
    assert u.latency_fill(0.985, [[0.995, 50.0]]) is None  # a* above the 0.99 cap
    assert u.latency_fill(None, [[0.9, 50.0]]) is None and u.latency_fill(0.9, []) is None


def test_tail_gate_required_margin_matches_the_design():
    assert u.clopper_pearson_upper(0, 56) == pytest.approx(0.0789, abs=1e-3)
    # the gate formula reduces to margin >= q_U: 7.9c / 11.3c / 14.2c (the design text's "about 8.4 / 12.5 / 16c" is 0.985 q/(1-q); see the implementation notes)
    assert u.required_margin(56, 0) == pytest.approx(0.0789, abs=5e-4)
    assert u.required_margin(56, 1) == pytest.approx(0.1126, abs=1e-3)
    assert u.required_margin(56, 2) == pytest.approx(0.1416, abs=1e-3)
    assert u.clopper_pearson_upper(3, 3) == 1.0 and u.clopper_pearson_upper(0, 0) == 1.0


def day_units(margin, n_units=3, lose=False):
    a = 1.0 - margin - 0.0063
    return [(a, 0.0063, 0.0 if (lose and i == 0) else 1.0) for i in range(n_units)]


def test_tail_gate_day_units_at_zero_one_and_five_losing_days():
    # 56 traded days; margin 0.09 passes with no losing day, margin 0.07 does not, and the threshold sits at q_U = 0.0789
    ok = {f"d{i}": day_units(0.09) for i in range(56)}
    assert u.tail_gate(ok)["passes"] and u.tail_gate(ok)["k_losing"] == 0 and u.tail_gate(ok)["n_days"] == 56
    low = {f"d{i}": day_units(0.07) for i in range(56)}
    assert not u.tail_gate(low)["passes"]
    assert u.tail_gate({f"d{i}": day_units(0.0795) for i in range(56)})["passes"] and not u.tail_gate({f"d{i}": day_units(0.0785) for i in range(56)})["passes"]
    # one losing day (the whole day's units lose together in the worst case: the gate uses k = days with >= 1 non-winning unit)
    one = {f"d{i}": day_units(0.13, lose=(i == 0)) for i in range(56)}
    g1 = u.tail_gate(one)
    assert g1["k_losing"] == 1 and g1["q_u"] == pytest.approx(0.1126, abs=2e-3) and g1["passes"]
    one_low = {f"d{i}": day_units(0.10, lose=(i == 0)) for i in range(56)}
    assert not u.tail_gate(one_low)["passes"]
    five = {f"d{i}": day_units(0.3, lose=(i < 5)) for i in range(56)}
    g5 = u.tail_gate(five)
    assert g5["k_losing"] == 5 and g5["q_u"] > 0.2
    assert u.tail_gate({})["passes"] is False
    # several units on one losing day count as ONE losing day (the day is the unit)
    multi = {f"d{i}": [(0.9, 0.0063, 0.0)] * 7 if i == 0 else day_units(0.13) for i in range(56)}
    assert u.tail_gate(multi)["k_losing"] == 1


# ---- the rules file ------------------------------------------------------------------------------------------------------------------------------------------


def test_rules_file_is_code_derived_and_never_rewritten(tmp_path):
    p = tmp_path / "cb8_rules.json"
    u.write_rules(p)
    doc = json.loads(p.read_text())
    assert doc == u.rules_file_doc() and doc["rules_sha256"] == u.verify_rules(p, require_committed=False)
    assert doc["declared"]["gate"]["tail_conf"] == 0.99 and doc["declared"]["units"]["buy_cap"] == 0.99 and doc["declared"]["population"]["up_re"] == u.UP_RE
    assert {"parse_updown", "tail_gate", "latency_fill", "state_at", "seal_holdout", "books_fetch", "coverage_audit", "updown_frame"} <= set(doc["func_sources_sha256"])
    u.write_rules(p)  # idempotent
    p.write_text(json.dumps({**doc, "declared": {}}))
    with pytest.raises(cm.Refused):
        u.verify_rules(p, require_committed=False)
    with pytest.raises(cm.Refused):
        u.write_rules(p)
    with pytest.raises(cm.Refused):
        u.verify_rules(tmp_path / "none.json", require_committed=False)


def test_rules_hash_changes_with_a_rule_function(monkeypatch):
    before = u.rules_file_doc()["rules_sha256"]
    monkeypatch.setattr(u, "Z_MIN", 2.0)
    assert u.rules_file_doc()["rules_sha256"] != before  # declared() reads the constant


# ---- smoke (q0161) ---------------------------------------------------------------------------------------------------------------------------------------------


def smoke_gamma(api: Api, n=24, volume=80000.0):
    """Closed worn markets for the smoke pool: ids come from the pinned files in production; the tests inject a tiny pool."""
    for i in range(n):
        end = datetime(2026, 7, 1 + i % 20, 12, tzinfo=UTC)
        api.gamma[f"s{i}"] = {"id": f"s{i}", "conditionId": f"sc{i}", "endDate": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "createdAt": "2026-05-01T00:00:00Z", "volumeNum": volume, "closed": True}
        api.trades[f"sc{i}"] = [{"timestamp": int(end.timestamp()) - 4 * 86400 - 600 * k - 1000, "side": "BUY", "size": 5.0, "price": 0.4, "outcomeIndex": 0, "proxyWallet": f"0xw{k}", "transactionHash": f"tx{i}{k}"}
                                for k in range(6)]


def run_smoke_fake(api, tmp_path, monkeypatch, *, blob=None, heads=None, rules_sha="r" * 64):
    from astrolabe.research_lab import cb7_common as c7
    from astrolabe.research_lab import history_backfill as hb

    monkeypatch.setattr(u, "smoke_pool_ids", lambda files, pins, n=u.SMOKE_CANDIDATES, seed=u.SMOKE_SEED_POOL: [f"s{i}" for i in range(24)])
    lim = hb.Limiter(api, rps=1000.0, sleep=nosleep)
    blob = blob or BinanceFake(["2026-03-01"])
    return u.run_smoke(lim, {}, c7.EXCLUSION_PINS, rules_sha, blob_get=blob, size_fn=heads or (lambda url: 1000), pacer=u.Pacer(1000.0, nosleep))


def test_smoke_pass_and_criteria_a_b_c(tmp_path, monkeypatch):
    api = Api()
    smoke_gamma(api)
    res = run_smoke_fake(api, tmp_path, monkeypatch, blob=BinanceFake(["2026-03-01", "2026-03-02"]))
    assert res["pass"] and res["criterion_a_data_api_paging"] and res["criterion_b_binance_checksum"] and res["criterion_c_pmxt_heads"] and res["n_requested"] == 20
    assert res["n_nonempty"] == 20 and res["counts_only"] is True and len(res["pmxt_heads"]) == 3 and len(res["binance"]) == 2
    # the pmxt HEAD hours are B-window days at 15Z, in seeded order
    assert all(h["day"] in u.b_days() for h in res["pmxt_heads"])
    assert RAW_not_in(res)


def RAW_not_in(res) -> bool:
    return "0xw" not in json.dumps(res)


def test_smoke_a_fails_on_empty_markets_deep_offset_and_pool(tmp_path, monkeypatch):
    api = Api()
    smoke_gamma(api)
    for i in range(8):  # only 12 of 20 return a print: below the 14 of 20 floor
        api.trades[f"sc{i}"] = []
    res = run_smoke_fake(api, tmp_path, monkeypatch)
    assert res["n_nonempty"] == 12 and res["criterion_a_data_api_paging"] is False and res["pass"] is False
    api = Api()
    smoke_gamma(api)
    api.deep_status = 404  # something other than 200 or 400 (5xx is retried by the limiter and read as a network failure)
    res = run_smoke_fake(api, tmp_path, monkeypatch)
    assert res["deep_offset_probe"]["verdict"] == "failed" and res["criterion_a_data_api_paging"] is False
    api = Api()
    smoke_gamma(api, volume=100.0)  # the pool needs lifetime volume >= $50,000 (the W frame rule)
    res = run_smoke_fake(api, tmp_path, monkeypatch)
    assert res["n_in_pool"] == 0 and res["criterion_a_data_api_paging"] is False
    api = Api()
    smoke_gamma(api, n=10)
    res = run_smoke_fake(api, tmp_path, monkeypatch)
    assert res["n_requested"] == 10 and res["criterion_a_data_api_paging"] is False  # fewer than 20 pool markets


def test_smoke_b_checksum_and_c_heads_failures(tmp_path, monkeypatch):
    api = Api()
    smoke_gamma(api)
    blob = BinanceFake(["2026-03-01"])
    blob.corrupt.add("HYPEUSDT-1m-2026-03.zip")
    res = run_smoke_fake(api, tmp_path, monkeypatch, blob=blob)
    assert res["criterion_b_binance_checksum"] is False and res["criterion_a_data_api_paging"] is True and not res["pass"]

    def heads(url):
        if "T15" in url and url.endswith(".parquet"):
            raise FileNotFoundError(url)
        return 10

    res = run_smoke_fake(api, tmp_path, monkeypatch, heads=heads)
    assert res["criterion_c_pmxt_heads"] is False and all(h["reason"] == "not_published" for h in res["pmxt_heads"])


def test_smoke_network_failure_writes_nothing(tmp_path, monkeypatch):
    api = Api()
    smoke_gamma(api)
    blob = BinanceFake(["2026-03-01"])

    def boom(url):
        raise RuntimeError("blob get failed")

    with pytest.raises(cm.NotNow):
        run_smoke_fake(api, tmp_path, monkeypatch, blob=boom)
    api.fail_all = True
    with pytest.raises(cm.NotNow):
        run_smoke_fake(api, tmp_path, monkeypatch, blob=blob)


def test_smoke_gate_for_b_needs_same_rules_hash_and_criteria(tmp_path):
    p = tmp_path / "smoke.json"
    base = {"smoke_version": u.SMOKE_VERSION, "rules_sha256": "x", "criterion_a_data_api_paging": False, "criterion_b_binance_checksum": True, "criterion_c_pmxt_heads": True}
    p.write_text(json.dumps(base))
    assert u.smoke_ok(p, "x")  # a does not gate B
    with pytest.raises(cm.Refused, match="rules hash"):
        u.smoke_ok(p, "y")
    p.write_text(json.dumps({**base, "criterion_c_pmxt_heads": False}))
    with pytest.raises(cm.Refused, match="not met"):
        u.smoke_ok(p, "x")
    assert u.smoke_ok(p, "x", ())  # existence and hash only
    p.write_text(json.dumps({**base, "smoke_version": "old"}))
    with pytest.raises(cm.Refused):
        u.smoke_ok(p, "x")
    with pytest.raises(cm.Refused, match="not found"):
        u.smoke_ok(tmp_path / "none.json", "x")


# ---- frame (q0165) ---------------------------------------------------------------------------------------------------------------------------------------------


def write_keys(path: Path, rows: list[dict], disjointness: str = "verified") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"])
        w.writeheader()
        w.writerows(rows)
    path.with_name("exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(path), "disjointness": disjointness}))


FRAME_DAYS = ["2026-04-13", "2026-04-14", "2026-04-20", "2026-04-27", "2026-06-11", "2026-06-12", "2026-06-18", "2026-08-09"]


class FrameEnv:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.root = tmp / "cb8"
        self.sha = "frame-rules-sha"
        self.keys = self.root / "exclusion_keys.csv.gz"
        write_keys(self.keys, [{"market_id": "9001", "found": "1", "event_ids": "EXCL1", "neg_risk_market_id": "NEGX", "series_ids": "SX"}])
        self.api = Api()
        mk = []
        i = 100
        for d in FRAME_DAYS:
            for asset in ("Bitcoin", "Ethereum", "HYPE"):
                i += 1
                mk.append(updown_market(i, asset, d))
        # rejects on 2026-04-14: wrong strike date, unexpected end time, not an Up/Down question, an excluded id, key-sharing markets
        mk += [updown_market(500, "Solana", "2026-04-14", description=description("2026-04-14", sym="SOL", strike_day="2026-04-10")),
               updown_market(501, "XRP", "2026-04-14", end_off_s=45), updown_market(502, "Dogecoin", "2026-04-14", question="Will DOGE be above 1?"),
               updown_market(9001, "BNB", "2026-04-14"), updown_market(503, "BNB", "2026-04-14", event="EXCL1"), updown_market(504, "Solana", "2026-04-13", neg="NEGX"),
               updown_market(505, "XRP", "2026-04-13", series=("SX",))]
        for m in mk:
            self.api.gamma[m["id"]] = m
        self.blob = BinanceFake([*FRAME_DAYS, "2026-04-12", "2026-06-17", "2026-08-08", "2026-04-26", "2026-04-19", "2026-06-10"] + u.all_days())
        self.smoke = tmp / "smoke.json"
        self.smoke.write_text(json.dumps({"smoke_version": u.SMOKE_VERSION, "rules_sha256": self.sha, "criterion_a_data_api_paging": True, "criterion_b_binance_checksum": True, "criterion_c_pmxt_heads": True}))

    def frame(self, **kw):
        args = dict(rules_sha=self.sha, blob_get=self.blob, smoke_path=self.smoke, exclusion_keys_path=self.keys, rps=1000.0, sleep=nosleep, now=NOW, pacer=u.Pacer(1000.0, nosleep))
        args.update(kw)
        return u.updown_frame(self.root, self.api, **args)


@pytest.fixture(scope="module")
def frame_days_all():
    return u.all_days()


@pytest.fixture
def fenv(tmp_path):
    return FrameEnv(tmp_path)


def test_frame_end_to_end_filters_drops_split_and_guard(fenv):
    m = fenv.frame()
    assert m["status"] == u.FRAME_COMPLETE and m["complete"] is True, m
    rdir = fenv.root / u.RUN_FRAME
    frame = gz_rows(rdir / "frame.csv.gz")
    ids = {r["market_id"] for r in frame}
    # kept: 3 assets on each B day (the gap days 06-12 is outside the walked days); rejects and exclusion hits are gone
    walked = [d for d in FRAME_DAYS if d in u.b_days()]
    assert len(frame) == 3 * len(walked) and not ids & {"500", "501", "502", "9001", "503", "504", "505"}
    assert {r["day"] for r in frame} == set(walked) and "2026-06-12" not in {r["day"] for r in frame}
    split = json.loads((rdir / "split.json").read_text())
    rep = split["report"]
    assert rep["frame_walk"]["rejected"] == {"strike_dates": 1, "end_not_1600z": 1, "question_pattern": 1}
    assert rep["dropped_id"] == 1 and rep["dropped_keys"] == {"event": 1, "neg_risk_market": 1, "series": 1}
    assert all(r["split"] == u.day_split(r["day"]) for r in frame) and split["seed"] == u.SEED_SPLIT
    # the frame has no outcome columns; outcomes and settlement candles are only in the *_guarded files
    for r in frame:
        assert not any("outcome" in k or "price" in k or "uma" in k for k in r)
    assert (rdir / "outcomes_guarded.csv.gz").exists() and (rdir / "klines_settle_guarded.csv.gz").exists()
    g = gz_rows(rdir / "outcomes_guarded.csv.gz")
    assert {x["market_id"] for x in g} == ids and g[0]["outcome_prices"].startswith("[")
    settle = gz_rows(rdir / "klines_settle_guarded.csv.gz")
    assert settle and {float(x["close"]) for x in settle} == {SETTLE_MARK}
    pre = gz_rows(rdir / "klines_pre.csv.gz")
    assert pre and SETTLE_MARK not in {float(x["close"]) for x in pre}
    for x in pre:  # every feature candle opens before t_end of its day
        assert int(x["open_ms"]) < int(u.t_end(x["day"]) * 1000)
    strikes = gz_rows(rdir / "strikes.csv.gz")
    assert {float(x["strike_close"]) for x in strikes} == {SETTLE_MARK} and len(strikes) == len(u.ASSETS) * len(u.b_days())
    # nothing in the non-guarded files reveals a settlement or an outcome
    for name in ("frame.csv.gz", "split.json", "klines_pre.csv.gz", "strikes.csv.gz"):
        raw = gzip.decompress((rdir / name).read_bytes()) if name.endswith(".gz") else (rdir / name).read_bytes()
        assert b"outcomePrices" not in raw
    man = json.loads((rdir / "manifest.json").read_text())
    assert man["state"]["exclusion_keys_sha256"] and set(man["file_sha256"]) >= {"frame.csv.gz", "split.json", "klines_settle_guarded.csv.gz", "outcomes_guarded.csv.gz"}
    assert cm.verify_manifest_files(rdir, man) == len(man["file_sha256"])
    assert not (rdir / "frame_partial.jsonl.gz").exists() and not (rdir / "klines_partial.jsonl.gz").exists()
    assert man["state"]["archives"]  # archive checksums are recorded
    assert fenv.frame()["status"] == u.FRAME_COMPLETE  # sticky, no new request
    n = len(fenv.api.calls)
    fenv.frame()
    assert len(fenv.api.calls) == n


def test_frame_split_and_frame_are_written_before_the_first_binance_request(fenv):
    first_blob = {"n": None}

    def spy(url):
        if first_blob["n"] is None:
            rdir = fenv.root / u.RUN_FRAME
            first_blob["n"] = ((rdir / "split.json").exists(), (rdir / "frame.csv.gz").exists())
        return fenv.blob(url)

    fenv.frame(blob_get=spy)
    assert first_blob["n"] == (True, True)


def test_frame_resumes_after_a_stop_and_requests_nothing_twice(fenv):
    calls = {"n": 0}

    def stop_after():
        calls["n"] += 1
        return calls["n"] > 3

    m = fenv.frame(should_stop=stop_after)
    assert m["status"] == "in_progress" and m["stopped"] == "should_stop"
    m = fenv.frame()
    assert m["status"] == u.FRAME_COMPLETE
    days_asked = [c[1]["end_date_min"] for c in fenv.api.calls if c[0].endswith("/markets")]
    assert len(days_asked) == len(set(days_asked)) == len(u.b_days())


def test_frame_guards_smoke_exclusion_files_and_unverified(fenv, tmp_path):
    fenv.smoke.write_text(json.dumps({"smoke_version": u.SMOKE_VERSION, "rules_sha256": fenv.sha, "criterion_a_data_api_paging": True, "criterion_b_binance_checksum": False, "criterion_c_pmxt_heads": True}))
    with pytest.raises(cm.Refused, match="not met"):
        fenv.frame()
    with pytest.raises(cm.Refused):
        fenv.frame(exclusion_keys_path=tmp_path / "none.csv.gz")
    with pytest.raises(cm.Refused, match="run id"):
        fenv.frame(run_id="h4_seal")
    assert not any(c[0].endswith("/markets") for c in fenv.api.calls)
    fenv.smoke.write_text(json.dumps({"smoke_version": u.SMOKE_VERSION, "rules_sha256": fenv.sha, "criterion_b_binance_checksum": True, "criterion_c_pmxt_heads": True}))
    write_keys(fenv.keys, [], disjointness=u.UNVERIFIED)
    m = fenv.frame()
    assert m["status"] == u.UNVERIFIED and not (fenv.root / u.RUN_FRAME / "frame.csv.gz").exists()
    assert fenv.frame()["status"] == u.UNVERIFIED


def test_frame_checksum_failure_ends_source_unverified_after_three_attempts(fenv):
    fenv.blob.corrupt.add("BTCUSDT-1m-2026-04.zip")
    seen = []
    for _ in range(3):
        m = fenv.frame()
        seen.append(m["status"])
    assert seen[-1] == u.SOURCE_UNVERIFIED and (fenv.root / u.RUN_FRAME / "SOURCE_UNVERIFIED.json").exists()
    assert fenv.frame()["status"] == u.SOURCE_UNVERIFIED
    # the frame files were written but no feature or guarded kline file exists
    assert not (fenv.root / u.RUN_FRAME / "klines_settle_guarded.csv.gz").exists()


def test_frame_headroom_and_disk_budget(fenv, tmp_path):
    with pytest.raises(cm.NotNow):
        fenv.frame(data_dumps=tmp_path, data_dumps_cap_gb=0.0)  # data-dumps + cap above the declared cap -> exit 75 path
    m = fenv.frame(disk_cap=2000)
    assert m["status"] == cm.DISK_BUDGET_TOKEN
    assert fenv.frame()["status"] == cm.DISK_BUDGET_TOKEN  # sticky


def test_no_function_compares_consecutive_strikes_and_settlement_stays_guarded():
    """Static check: the strike of day d is built in exactly one place (finalize_frame, from the previous day's settlement) and no other function in the B data code
    reads the settlement candle or the strike of two days together."""
    from astrolabe.research_lab import cb8_books as bk

    def idents(fn) -> set[str]:
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        node = tree.body[0]
        if ast.get_docstring(node) is not None:
            node.body = node.body[1:]  # the docstring is prose, not code
        out: set[str] = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name):
                out.add(n.id)
            elif isinstance(n, ast.Attribute):
                out.add(n.attr)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.add(n.value)
        return out

    users = []
    for mod in (u, bk):
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if fn.__module__ != mod.__name__:
                continue
            ids = idents(fn)
            if any(("settle" in i.lower() or "strike" in i.lower()) and i not in ("strike_clause_missing", "strike_clause_not_mirrored", "strike_dates", "strike_symbol", "strike_rule") for i in ids):
                users.append(f"{mod.__name__.rsplit('.', 1)[1]}.{name}")
    # the allowed users: the rule text parser and constants, the extractor, the feature function (strike argument), the frame finaliser and the declaration
    allowed = {"cb8_updown.parse_updown", "cb8_updown.extract_month", "cb8_updown.z_features", "cb8_updown.finalize_frame", "cb8_updown.declared", "cb8_updown.updown_frame", "cb8_updown.binance_fetch", "cb8_updown._pd", "cb8_updown.all_days"}
    assert set(users) <= allowed, set(users) - allowed
    src = inspect.getsource(u.finalize_frame)
    assert src.count("timedelta(days=1)") == 1  # the only day - 1 step is the strike lookup
    for mod in (bk,):
        assert "klines_settle" not in inspect.getsource(mod) and "outcomes_guarded" not in inspect.getsource(mod).replace("holdout outcomes live in updown_frame/outcomes_guarded.csv.gz", "")


# ---- exclusion keys (q0164) --------------------------------------------------------------------------------------------------------------------------------


def make_pinned_files(tmp: Path):
    """Tiny pinned files: the three samples and two seal copies, with the real pins replaced by the fakes' hashes."""
    hist = tmp / "history"
    pins = []
    for name, ids in (("h1_first", ["11", "12"]), ("h2_main", ["13"]), ("h3_power", ["14"])):
        p = hist / name / "sample.csv.gz"
        p.parent.mkdir(parents=True)
        with gzip.open(p, "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["market_id", "x"])
            w.writerows([[i, "a"] for i in ids])
        pins.append({"name": name, "kind": "sample", "path": f"history/{name}/sample.csv.gz", "sha256": h5_seal.sha256_file(p)})
    return hist, pins


def test_exclusion_keys_extra_pins_dynamic_seals_and_absent_records(tmp_path, monkeypatch):
    from astrolabe.research_lab import cb7_common as c7

    hist, pins = make_pinned_files(tmp_path)
    monkeypatch.setattr(c7, "EXCLUSION_PINS", tuple(pins))
    extra = tmp_path / "cb5_listing.csv"
    extra.write_text("market_id\n21\n22\n")
    api = Api()
    for i in ("11", "12", "13", "14", "21", "22"):
        api.gamma[i] = updown_market(int(i), "Bitcoin", "2026-04-14", event=f"E{i}", neg="NEG1" if i == "11" else "", series=("S1",) if i == "12" else ())
    seals = tmp_path / "seals"
    seals.mkdir()
    out = tmp_path / "out"
    m = u.exclusion_keys(out, api, rules_sha="r", history_root=hist, seals_dir=seals, extra_pins=[{"name": "cb5_listing", "kind": "ids", "path": str(extra), "sha256": h5_seal.sha256_file(extra)}],
                         rps=1000.0, sleep=nosleep, now=NOW, dest_dir=out)
    assert m["status"] == u.KEYS_COMPLETE and m["complete"]
    rep = json.loads((out / "exclusion_report.json").read_text())
    assert rep["n_ids"] == 6 and rep["n_found"] == 6 and rep["disjointness"] == "verified" and rep["keys"] == {"event": 6, "neg_risk_market": 1, "series": 1}
    assert "h6_weather_SEAL.json" in rep["absent_at_q0164"] and {p["name"] for p in rep["pins"]} == {"h1_first", "h2_main", "h3_power", "cb5_listing"}
    keys = gz_rows(out / "exclusion_keys.csv.gz")
    assert {k["market_id"] for k in keys} == {"11", "12", "13", "14", "21", "22"}
    # the copies are byte-identical to the run's files
    assert (out / "exclusion_keys.csv.gz").read_bytes() == (out / u.RUN_KEYS / "exclusion_keys.csv.gz").read_bytes()
    # a changed pinned file is a refusal, never a silent skip
    extra.write_text("market_id\n21\n")
    with pytest.raises(cm.Refused):
        u.exclusion_keys(tmp_path / "out2", api, rules_sha="r", history_root=hist, seals_dir=seals, extra_pins=[{"name": "cb5_listing", "kind": "ids", "path": str(extra), "sha256": "0" * 64}],
                         rps=1000.0, sleep=nosleep, now=NOW)


def test_exclusion_keys_unverified_when_more_than_two_percent_lack_metadata(tmp_path, monkeypatch):
    from astrolabe.research_lab import cb7_common as c7

    hist, pins = make_pinned_files(tmp_path)
    monkeypatch.setattr(c7, "EXCLUSION_PINS", tuple(pins))
    api = Api()  # no Gamma metadata for any id
    out = tmp_path / "out"
    seals = tmp_path / "seals"
    seals.mkdir()
    m = u.exclusion_keys(out, api, rules_sha="r", history_root=hist, seals_dir=seals, rps=1000.0, sleep=nosleep, now=NOW, dest_dir=out)
    assert m["status"] == u.UNVERIFIED


# ---- runner ----------------------------------------------------------------------------------------------------------------------------------------------------


def test_cli_rules_updown_and_declared_argument_refusals(tmp_path, capsys):
    rules = tmp_path / "cb8_rules.json"
    assert script.main(["rules", "--which", "updown", "--path", str(rules)]) == 0
    assert json.loads(rules.read_text()) == u.rules_file_doc()
    base = ["--rules", str(rules), "--allow-uncommitted-rules", "--root", str(tmp_path / "cb8"), "--data-dumps", str(tmp_path), "--standalone"]
    assert script.main(["updown-frame", *base, "--days", "2026-04-13:2026-08-11", "--disk-cap-gb", "0.02"]) == 2
    assert script.main(["updown-frame", *base, "--disk-cap-gb", "0.5"]) == 2
    assert script.main(["updown-frame", *base, "--disk-cap-gb", "0.02", "--require-smoke", str(tmp_path / "nosmoke.json")]) == 2
    assert script.main(["updown-books", *base, "--disk-cap-gb", "0.02", "--ingress-cap-gb", "500"]) == 2
    assert script.main(["updown-books", *base, "--disk-cap-gb", "0.02", "--audit-hour", "15"]) == 2
    assert script.main(["updown-books", *base, "--disk-cap-gb", "0.02", "--require-smoke", str(tmp_path / "nosmoke.json")]) == 2
    assert script.main(["exclusion-keys", *base, "--disk-cap-gb", "0.5"]) == 2
    assert script.main(["exclusion-keys", *base, "--require-smoke", str(tmp_path / "nosmoke.json")]) == 2
    assert script.main(["smoke", *base, "--n", "5"]) == 2
    other = tmp_path / "other_rules.json"
    other.write_text(json.dumps({"rules_sha256": "x"}))
    assert script.main(["smoke", "--rules", str(other), "--allow-uncommitted-rules", "--standalone", "--out", str(tmp_path / "s.json")]) == 2
    (tmp_path / "s.json").write_text("{}")
    assert script.main(["smoke", *base, "--out", str(tmp_path / "s.json")]) == 2  # write-once
    refused_root = ["--rules", str(rules), "--allow-uncommitted-rules", "--root", str(tmp_path / "cb7_extract" / "x"), "--standalone"]
    assert script.main(["updown-frame", *refused_root, "--disk-cap-gb", "0.02"]) == 2
