# ruff: noqa: E501
"""CB9-S tests (offline; constructed receipts, no network)."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_sign as sg

KEY = b"k" * 32
W = "0x" + "a1" * 20  # taker proxy wallet
M = "0x" + "b2" * 20  # maker
M2 = "0x" + "c3" * 20
YES, NO = 111, 222
EX1, EX2 = sg.EXCHANGES_V1[1], sg.EXCHANGES_V2[1]
T = sg.topics()


def _w(x) -> str:
    if isinstance(x, str):
        return x[2:].rjust(64, "0")
    return format(int(x), "064x")


def _log(kind: str, addr: str, indexed: list, data: list, li: int) -> dict:
    return {"address": addr, "topics": [T[kind]] + ["0x" + _w(v) for v in indexed], "data": "0x" + "".join(_w(v) for v in data), "logIndex": hex(li)}


def _transfer(frm: str, to: str, tid: int, val: int, li: int) -> dict:
    return _log("transfer_single", sg.CTF, [sg.EXCHANGES_V2[0], frm, to], [tid, val], li)


def _batch(frm: str, to: str, ids: list[int], vals: list[int], li: int) -> dict:
    n = len(ids)
    words = [64, 64 + 32 * (n + 1), n, *ids, n, *vals]
    return _log("transfer_batch", sg.CTF, [EX1, frm, to], words, li)


def _hash_addr(a: str):
    return cm.hash_wallet(KEY, a)


def v2_receipt_normal() -> dict:
    """Taker W BUYs 10 YES from maker M (maker SELL), v2 exchange; CTF transfer M -> W."""
    return {"logs": [
        _log("v2_order_filled", EX2, ["0x" + "01" * 32, M, W], [1, YES, 10_000_000, 5_200_000, 0, "0x" + "00" * 32, "0x" + "00" * 32], 1),
        _transfer(M, W, YES, 10_000_000, 2),
        _log("v2_orders_matched", EX2, ["0x" + "02" * 32, W], [0, YES, 5_200_000, 10_000_000], 3),
    ]}


def v1_receipt_mint() -> dict:
    """v1: taker W BUYs 7 NO (makerAssetId 0); maker M BUYs YES (complement) and a PositionSplit mints; TransferBatch exchange -> W of NO."""
    return {"logs": [
        _log("v1_order_filled", EX1, ["0x" + "03" * 32, M, W], [0, YES, 3_000_000, 7_000_000, 0], 4),
        _log("position_split", sg.CTF, [EX1, "0x" + "00" * 32, "0x" + "04" * 32], [EX1, 64 + 32, 2, 1, 2, 7_000_000][:2] + [96, 7_000_000, 2, 1, 2][:0], 5)
        | {"data": "0x" + _w(sg.CTF) + _w(64) + _w(7_000_000) + _w(2) + _w(1) + _w(2)},
        _batch(EX1, W, [NO], [7_000_000], 6),
        _log("v1_order_filled", EX1, ["0x" + "05" * 32, W, EX1], [0, NO, 4_000_000, 7_000_000, 0], 7),
        _log("v1_orders_matched", EX1, ["0x" + "05" * 32, W], [0, NO, 4_000_000, 7_000_000], 8),
    ]}


def v1_receipt_sell() -> dict:
    """v1: taker W SELLs 3 YES (makerAssetId = YES); maker M2 BUYs YES; CTF W -> M2."""
    return {"logs": [
        _log("v1_order_filled", EX1, ["0x" + "06" * 32, M2, W], [0, YES, 1_500_000, 3_000_000, 0], 1),
        _transfer(W, M2, YES, 3_000_000, 2),
        _log("v1_orders_matched", EX1, ["0x" + "07" * 32, W], [YES, 0, 3_000_000, 1_500_000], 3),
    ]}


# ---- keccak and pins ---------------------------------------------------------------------------------------------------------


def test_keccak_vectors():
    assert sg.keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert sg.topic("Transfer(address,address,uint256)") == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    assert sg.keccak256(b"a" * 200).hex() == sg.keccak256(b"a" * 200).hex()  # multi-block path runs


def test_topic_pins_match_local_keccak():
    chk = sg.topic_pins_ok()
    assert chk["ok"], chk
    for k, v in sg.PINNED_TOPICS.items():
        assert sg.topic(sg.SIG[k]) == v
    assert T["transfer_single"] == "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
    assert T["transfer_batch"] == "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"


def test_bad_pin_refused(monkeypatch):
    monkeypatch.setitem(sg.PINNED_TOPICS, "v2_orders_matched", "0x" + "0" * 64)
    with pytest.raises(c9.Refused):
        sg.require_topic_pins()


# ---- decoder, T1, T2, fill types ---------------------------------------------------------------------------------------------


def test_v2_decode_t1_t2_normal():
    dec = sg.decode_receipt(v2_receipt_normal())
    assert len(dec["matches"]) == 1 and dec["matches"][0]["era"] == "v2"
    m = dec["matches"][0]
    assert m["taker"] == W and m["side"] == "BUY" and m["token"] == YES and m["shares"] == pytest.approx(10.0)
    assert sg.t1_of(m) == ("BUY", YES)
    assert sg.t2_of(dec, W, (YES, NO)) == ("ok", ("BUY", YES))
    assert sg.fill_type(dec, m, (YES, NO)) == "normal"


def test_v1_decode_mint_batch_transfer():
    dec = sg.decode_receipt(v1_receipt_mint())
    m = [x for x in dec["matches"] if x["taker"] == W][0]
    assert m["era"] == "v1" and sg.t1_of(m) == ("BUY", NO) and m["shares"] == pytest.approx(7.0)
    assert sg.t2_of(dec, W, (YES, NO)) == ("ok", ("BUY", NO))
    assert dec["splits"] and sg.fill_type(dec, m, (YES, NO)) == "mint"


def test_v1_sell():
    dec = sg.decode_receipt(v1_receipt_sell())
    m = dec["matches"][0]
    assert sg.t1_of(m) == ("SELL", YES) and m["shares"] == pytest.approx(3.0)
    assert sg.t2_of(dec, W, (YES, NO)) == ("ok", ("SELL", YES))
    assert sg.fill_type(dec, m, (YES, NO)) == "normal"


def test_unpinned_address_ignored_and_bad_data_counted():
    r = v2_receipt_normal()
    r["logs"][2]["address"] = "0x" + "99" * 20
    assert sg.decode_receipt(r)["matches"] == []
    r = v2_receipt_normal()
    r["logs"][2]["data"] = r["logs"][2]["data"][:-64]
    assert sg.decode_receipt(r)["undecodable"] == 1


def test_t2_ambiguous_and_absent():
    dec = sg.decode_receipt(v2_receipt_normal())
    dec["transfers"].append((9, W, M, NO, 5))
    assert sg.t2_of(dec, W, (YES, NO))[0] == "ambiguous"
    assert sg.t2_of(dec, M2, (YES, NO))[0] == "absent"


def test_classify_print_t1_equals_t2_on_fixtures():
    for rcpt, tok, side, size, idx in ((v2_receipt_normal(), YES, "BUY", 10.0, 0), (v1_receipt_mint(), NO, "BUY", 7.0, 1), (v1_receipt_sell(), YES, "SELL", 3.0, 0)):
        pr = {"stratum": "a", "market_id": "m1", "tx": "0x" + "ab" * 32, "asset": tok, "side": side, "idx": idx, "size": size, "price": 0.5,
              "wallet": cm.hash_wallet(KEY, W)}
        row = sg.classify_print(pr, rcpt, sg.ENDPOINTS[0], (YES, NO), _hash_addr, T)
        assert row["match_status"] == "matched" and row["t1_available"] == 1 and row["t2_available"] == 1
        assert (row["t1_side"], row["t1_idx"]) == (row["t2_side"], row["t2_idx"])
        assert "0x" + "a1" * 20 not in json.dumps(row)  # the raw address is never stored


# ---- match rule --------------------------------------------------------------------------------------------------------------


def _two_matches(size2: int) -> dict:
    r = v2_receipt_normal()
    r["logs"].append(_log("v2_orders_matched", EX2, ["0x" + "09" * 32, W], [0, YES, 2_000_000, size2], 10))
    return r


def test_match_ambiguity_and_size_tiebreak():
    wh = cm.hash_wallet(KEY, W)
    dec = sg.decode_receipt(_two_matches(4_000_000))
    st, m, n = sg.match_print(dec, wh, (YES, NO), 10.0, _hash_addr)
    assert st == "matched" and n == 2 and m["shares"] == pytest.approx(10.0)
    dec = sg.decode_receipt(_two_matches(10_000_000))
    assert sg.match_print(dec, wh, (YES, NO), 10.0, _hash_addr)[0] == "unmatched_ambiguous"
    dec = sg.decode_receipt(_two_matches(4_000_000))
    assert sg.match_print(dec, wh, (YES, NO), 6.0, _hash_addr)[0] == "unmatched_size"
    assert sg.match_print(dec, cm.hash_wallet(KEY, M2), (YES, NO), 10.0, _hash_addr)[0] == "unmatched_none"
    assert sg.match_print(dec, wh, (333, 444), 10.0, _hash_addr)[0] == "unmatched_none"


def test_complement_token_matches():
    dec = sg.decode_receipt(v2_receipt_normal())
    st, m, _ = sg.match_print(dec, cm.hash_wallet(KEY, W), (NO, YES), 10.0, _hash_addr)
    assert st == "matched" and m["token"] == YES


def test_yes_sign_convention():
    assert sg.yes_sign("BUY", 0) == 1 and sg.yes_sign("SELL", 1) == 1
    assert sg.yes_sign("SELL", 0) == -1 and sg.yes_sign("BUY", 1) == -1


# ---- RPC client --------------------------------------------------------------------------------------------------------------


def test_rpc_fallback_order_and_unavailable():
    calls = []

    def post(url, payload):
        calls.append(url)
        if url == sg.ENDPOINTS[2]:
            return 200, json.dumps({"result": {"logs": []}}).encode()
        return (403, b"") if url == sg.ENDPOINTS[0] else (200, json.dumps({"result": None}).encode())

    rpc = sg.RpcClient(post, sleep=lambda s: None)
    rc, ep = rpc.receipt("0x" + "00" * 32)
    assert rc == {"logs": []} and ep == sg.ENDPOINTS[2]
    assert calls == [sg.ENDPOINTS[0]] * 2 + [sg.ENDPOINTS[1]] * 2 + [sg.ENDPOINTS[2]]
    calls.clear()
    rpc2 = sg.RpcClient(lambda u, p: (calls.append(u), (500, b""))[1], sleep=lambda s: None)
    assert rpc2.receipt("0x" + "00" * 32) == (None, "unavailable")
    assert len(calls) == 2 * len(sg.ENDPOINTS) and rpc2.n_unavailable == 1


def test_rpc_rate_ceiling_and_pacing():
    with pytest.raises(c9.Refused):
        sg.RpcClient(lambda u, p: (200, b""), rps=3.0)
    slept = []
    clock = iter(np.arange(0, 100, 0.1))
    rpc = sg.RpcClient(lambda u, p: (200, json.dumps({"result": {"logs": []}}).encode()), sleep=slept.append, clock=lambda: float(next(clock)))
    rpc.receipt("0x1")
    rpc.receipt("0x2")
    assert slept and all(s <= 0.5 for s in slept)


# ---- S0 statistic and verdicts ------------------------------------------------------------------------------------------------


def _rows(n_markets: int, per: int, agree_share: float = 1.0, unmatched: int = 0, stratum: str = "a") -> list[dict]:
    rows, k = [], 0
    n_agree = round(n_markets * per * agree_share)
    for i in range(n_markets):
        for _ in range(per):
            ok = k < n_agree
            rows.append({"stratum": stratum, "market_id": f"m{i}", "match_status": "matched", "t1_available": "1", "t2_available": "1", "api_side": "BUY",
                         "api_idx": "0", "t1_side": "BUY" if ok else "SELL", "t1_idx": "0", "t2_side": "BUY" if ok else "SELL", "t2_idx": "0",
                         "notional": "2.0", "fill_type": "normal", "liq_tercile": "T1", "price_band": "0.30-0.70", "sports": "0", "feed_side": ""})
            k += 1
    rows += [{"stratum": stratum, "market_id": f"u{j}", "match_status": "unmatched_none", "t1_available": "0", "t2_available": "0"} for j in range(unmatched)]
    return rows


def test_s0_near_truth_all_agree_degenerate_bootstrap_uses_wilson():
    r = sg.s0_stratum(_rows(320, 1), n_boot=200)
    assert r["q_hat"] == 1.0 and r["q_lb_bootstrap"] == 1.0
    assert r["q_lb"] == r["q_lb_wilson_markets"] < 1.0
    assert r["verdict"] == "near-truth"


def test_s0_bound_limited_by_n():
    r = sg.s0_stratum(_rows(80, 4), n_boot=200)
    assert r["q_hat"] == 1.0 and r["q_lb"] < sg.NEAR_TRUTH_LB
    assert r["verdict"] == "minor noise or better (bound limited by n)"


def test_s0_material_noise_and_qwc():
    r = sg.s0_stratum(_rows(100, 4, agree_share=0.85), n_boot=200)
    assert r["verdict"] == "material noise" and r["s1_triggered"]
    r = sg.s0_stratum(_rows(100, 4, agree_share=0.95, unmatched=30), n_boot=200)
    assert r["q_wc"] == pytest.approx(380 / 430)
    assert r["gate_GS"] is True


def test_s0_gs_fail_unverified_never_inherited():
    rows = {"a": _rows(100, 4), "b": _rows(50, 4, unmatched=100, stratum="b"), "c": []}
    doc = sg.s0_screen(rows)
    assert doc["strata"]["a"]["testable"]
    assert doc["strata"]["b"]["verdict"] == "not testable (source)" and doc["strata"]["b"]["mapped_results"] == "unverified"
    assert doc["strata"]["c"]["verdict"] == "not testable (source)"
    assert doc["strata"]["b"]["era_map"]["informs"] == sg.ERA_MAP["b"]["informs"]


def test_s0_source_gate_t1_t2():
    rows = _rows(100, 4)
    for r in rows[:10]:
        r["t2_side"] = "SELL"
    assert sg.s0_stratum(rows, n_boot=100)["verdict"] == "not testable (on-chain truth ambiguous)"


def test_s0_notional_weighted_reported():
    rows = _rows(100, 4, agree_share=0.95)
    for r in rows:
        if r["t1_side"] == "SELL":
            r["notional"] = "100.0"
    rep = sg.s0_stratum(rows, n_boot=100)["reported"]
    assert rep["notional_weighted_q"] < 0.95 and rep["a_tok"] == pytest.approx(0.95)


def test_census_s_counts_only_and_forbidden_fields():
    rows = [{k: r.get(k, "") for k in sg.CENSUS_COLUMNS_S} for r in _rows(10, 4)]
    out = sg.census_s({"a": rows})
    assert out["a"]["n_matched"] == 40 and out["a"]["gate_GS"] is False
    assert "q_hat" not in json.dumps(out)
    with pytest.raises(c9.Refused):
        sg.census_s({"a": [{**rows[0], "t1_side": "BUY"}]})


def test_read_census_rows_field_restricted(tmp_path):
    from astrolabe.research_lab import history_backfill as hb

    p = tmp_path / "prints_classes.csv.gz"
    rows = _rows(3, 2)
    p.write_bytes(hb._gz_csv_bytes(sg.PRINT_COLUMNS, [[r.get(c, "") for c in sg.PRINT_COLUMNS] for r in rows]))
    got = sg.read_census_rows(p)
    assert set(got[0]) == set(sg.CENSUS_COLUMNS_S)
    with pytest.raises(c9.Refused):
        c9.read_csv_gz_restricted(p, ("market_id", "t1_side"), sg.CENSUS_FORBIDDEN_S)


# ---- samples ------------------------------------------------------------------------------------------------------------------


def test_sample_markets_seeded_and_event_cap():
    frame = [{"market_id": str(i), "event_id": str(i // 10)} for i in range(100)]
    a = sg.sample_markets(frame, "s", n=20)
    assert a == sg.sample_markets(list(reversed(frame)), "s", n=20)
    per = {}
    for r in a:
        per[r["event_id"]] = per.get(r["event_id"], 0) + 1
    assert max(per.values()) <= 3


def _kd_prints(n_markets: int, per: int) -> list[dict]:
    return [{"market_id": f"m{i}", "tx": "0x" + f"{i:02x}{j:02x}".rjust(64, "0"), "asset": YES, "side": "BUY", "size": float(j + 1), "ts": 1000 + j,
             "split": "screen"} for i in range(n_markets) for j in range(per)]


def test_s0b_sample_streaming_equals_draw_prints_and_caps():
    pr = _kd_prints(400, 7)
    out = sg.s0b_sample(pr)
    assert len(out) == 1000
    per = {}
    for p in out:
        per[p["market_id"]] = per.get(p["market_id"], 0) + 1
    assert max(per.values()) <= 4
    mid = out[0]["market_id"]
    assert [p["tx"] for p in out if p["market_id"] == mid] == [p["tx"] for p in sg.draw_prints([p for p in pr if p["market_id"] == mid], sg.SEEDS["b"], mid)]


def test_s0b_holdout_refused():
    with pytest.raises(c9.Refused):
        sg.s0b_sample([{**_kd_prints(1, 1)[0], "split": "holdout"}])


def test_sign_audit_refuses_before_t_seal(tmp_path):
    with pytest.raises(c9.Refused):
        sg.sign_audit(tmp_path, "a", None, None, key=KEY, fp="0" * 16, rules_sha="x", smoke_path=tmp_path / "smoke.json", now=c9.T_SEAL_EPOCH - 1)


def test_smoke_ok_gate(tmp_path):
    p = tmp_path / "smoke.json"
    with pytest.raises(c9.Refused):
        sg.smoke_ok(p, need=("receipts_v2",))
    p.write_text(json.dumps({"smoke_version": sg.SMOKE_VERSION, "criteria": {"receipts_v2": True, "receipts_v1": False}}))
    assert sg.smoke_ok(p, need=("receipts_v2",))
    with pytest.raises(c9.Refused):
        sg.smoke_ok(p, need=("receipts_v1",))


# ---- S1 -----------------------------------------------------------------------------------------------------------------------


def _s1_units(n_events: int, noise: float, rng) -> tuple[list[dict], list[str]]:
    units, ev = [], []
    for e in range(n_events):
        for _ in range(30):
            xc = rng.uniform(-1, 1)
            xa = xc if rng.random() > noise else -xc
            units.append({"x_api": xa, "x_chain": xc, "d": 0.02 * xc + rng.normal(0, 0.002)})
            ev.append(f"e{e}")
    return units, ev


def test_s1_pass_under_strong_attenuation():
    u, ev = _s1_units(60, 0.35, np.random.default_rng(1))
    r = sg.s1_ratio(u, ev, n_boot=300)
    assert r["testable"] and r["r_hat"] > 1.5 and r["lb_1pct"] > 1.5 and r["pass"] and r["p"] < 0.01


def test_s1_fails_without_attenuation_and_negative_beta_api_counts_as_failure():
    u, ev = _s1_units(60, 0.0, np.random.default_rng(2))
    r = sg.s1_ratio(u, ev, n_boot=300)
    assert not r["pass"] and r["r_hat"] == pytest.approx(1.0, abs=0.05)
    u2 = [{**x, "x_api": -x["x_chain"]} for x in u]  # beta_api < 0 everywhere -> every draw is a failure
    r2 = sg.s1_ratio(u2, ev, n_boot=100)
    assert r2["p"] == 1.0 and not r2["pass"]


def test_s1_units_identical_prints_and_anchor_tolerance():
    w0 = 0.0
    dense = [{"ts": w0 + 600 * k + 60, "idx": 0, "api_side": "BUY", "price": 0.5, "size": 10.0, "t1_side": "SELL", "t1_idx": 0} for k in range(72 * 6)]
    dense.append({"ts": 100.0, "idx": 0, "api_side": "BUY", "price": 0.9, "size": 1e6, "t1_side": "", "t1_idx": 0})  # no T1: excluded from both
    us = sg.s1_units(dense, w0, w0 + 72 * 3600)
    assert us and all(u["x_api"] == 1.0 and u["x_chain"] == -1.0 for u in us)
    assert all(np.isfinite(u["d"]) and u["d"] == 0.0 for u in us)
    hourly = [{**p, "ts": w0 + 3600 * h + 60} for h, p in enumerate(dense[:72])]
    assert all(not np.isfinite(u["d"]) for u in sg.s1_units(hourly, w0, w0 + 72 * 3600))  # last print 59 min before t: anchor > 30 min, unavailable


def test_h10_exclusions_need_every_cb9_source():
    with pytest.raises(c9.Refused):
        sg.h10_exclusions({"1"}, {}, {"kd_frame": {"2"}})
    ids, info = sg.h10_exclusions({"1"}, {"event": set()}, {"kd_frame": {"2"}, "pyth_frame": {"3"}, "s0a": {"4"}, "s0b": {"5"}, "s0c": {"6"}})
    assert ids == {"1", "2", "3", "4", "5", "6"} and info["n_kd_frame"] == 1


def test_h10_window_seeded_inside_life():
    m = {"market_id": "7", "start_epoch": cm.ep("2026-05-03"), "end_epoch": cm.ep("2026-05-20")}
    w = sg.h10_window(m, (cm.ep("2026-05-01"), cm.ep("2026-10-01")))
    assert w and w[0] >= m["start_epoch"] and w[1] <= m["end_epoch"] and w[1] - w[0] == 72 * 3600
    assert sg.h10_window({**m, "end_epoch": cm.ep("2026-05-05")}, (cm.ep("2026-05-01"), cm.ep("2026-10-01"))) is None


# ---- HMAC strict loader and rules ----------------------------------------------------------------------------------------------


def test_strict_loader_never_creates_and_refuses_unsafe(tmp_path):
    p = tmp_path / "key"
    with pytest.raises(c9.Refused):
        cm.load_wallet_key_strict(p)
    assert not p.exists()
    p.write_bytes(KEY)
    os.chmod(p, 0o644)
    with pytest.raises(c9.Refused):
        cm.load_wallet_key_strict(p)
    os.chmod(p, 0o600)
    fp = cm.key_fingerprint(KEY)
    assert cm.load_wallet_key_strict(p, fp) == KEY
    with pytest.raises(c9.Refused):
        cm.load_wallet_key_strict(p, "0" * 16)


def test_sign_rules_pin_fingerprint_and_roundtrip(tmp_path):
    with pytest.raises(c9.Refused):
        c9.rules_file_doc("sign", None)
    fp = cm.key_fingerprint(KEY)
    p = c9.write_rules("sign", tmp_path / "r.json", fp)
    sha, got = c9.verify_rules("sign", p, require_committed=False)
    assert got == fp and sha == json.loads(p.read_text())["rules_sha256"]
    d = json.loads(p.read_text())["declared"]
    assert d["topics"]["pins_ok"] is True and d["endpoints"]["order"] == list(sg.ENDPOINTS)
    assert d["smoke"]["yahoo"]["bar_clock"]["full_bars"] == 7
