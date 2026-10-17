# ruff: noqa: E501
"""CB8 shared parts: strict wallet key, fingerprint, rules files, windowed prints, idle heartbeat, manifest re-hash. No network."""

from __future__ import annotations

import json

import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import history_backfill as hb
from astrolabe.research_lab import wallet_sidecar as ws
from tests.unit._cb8_fakes import RAW_PREFIX, T0, Api, make_key, nosleep, print_row


def test_strict_loader_never_creates_a_key(tmp_path):
    missing = tmp_path / "nokey" / "wallet_hash_key"
    with pytest.raises(cm.Refused):
        cm.load_wallet_key_strict(missing)
    assert not missing.exists() and not missing.parent.exists()
    with pytest.raises(cm.Refused):  # the env-var default of the unit-test isolation points at a missing file too
        cm.load_wallet_key_strict()


def test_strict_loader_modes_empty_and_fingerprint(tmp_path):
    p = make_key(tmp_path, mode=0o644)
    with pytest.raises(cm.Refused, match="mode 600"):
        cm.load_wallet_key_strict(p)
    p = make_key(tmp_path, content=b"")
    with pytest.raises(cm.Refused, match="empty"):
        cm.load_wallet_key_strict(p)
    p = make_key(tmp_path)
    key = cm.load_wallet_key_strict(p)
    fp = cm.key_fingerprint(key)
    assert len(fp) == 16 and fp != key.decode()[:16]
    assert cm.load_wallet_key_strict(p, fp) == key
    with pytest.raises(cm.Refused, match="fingerprint"):
        cm.load_wallet_key_strict(p, "0" * 16)
    other = make_key(tmp_path / "o", content=b"z" * 64)
    assert cm.key_fingerprint(cm.load_wallet_key_strict(other)) != fp


def test_hash_matches_sidecar_prefix_and_blank_is_none(tmp_path):
    key = cm.load_wallet_key_strict(make_key(tmp_path))
    h = cm.hash_wallet(key, "0xABC")
    assert h == ws.hash_wallet(key, "0xabc")[:32] and len(h) == 32
    assert cm.hash_wallet(key, "  ") is None and cm.hash_wallet(key, None) is None


@pytest.mark.parametrize("kind", ["holders", "flow"])
def test_rules_roundtrip_and_tamper(tmp_path, kind):
    path = tmp_path / "rules.json"
    fp = "ab" * 8
    cm.write_rules(kind, path, fp)
    sha, got_fp = cm.verify_rules(kind, path, require_committed=False)
    assert got_fp == fp and sha == cm.rules_file_doc(kind, fp)["rules_sha256"]
    assert cm.write_rules(kind, path, fp) == path  # same content: idempotent
    with pytest.raises(cm.Refused, match="never rewritten"):
        cm.write_rules(kind, path, "cd" * 8)
    doc = json.loads(path.read_text())
    doc["declared"]["wallet_hash_hex"] = 8 if kind == "holders" else None
    doc["declared"]["disk"] = {"x": 1}
    path.write_text(json.dumps(doc))
    with pytest.raises(cm.Refused, match="mismatch"):
        cm.verify_rules(kind, path, require_committed=False)
    with pytest.raises(cm.Refused, match="not committed"):
        cm.write_rules(kind, tmp_path / "r2.json", fp) and cm.verify_rules(kind, tmp_path / "r2.json", require_committed=True)


def test_rules_hash_changes_with_function_source(tmp_path, monkeypatch):
    base = cm.rules_file_doc("holders", "ab" * 8)["rules_sha256"]
    from astrolabe.research_lab import cb8_holders as h

    def concentration(rows, oi):  # a different function body with the same qualified name is a different rule
        return {}

    monkeypatch.setattr(h, "concentration", concentration)
    assert cm.rules_file_doc("holders", "ab" * 8)["rules_sha256"] != base


def test_committed_rules_file_matches_code():
    p = cm.HOLDERS_RULES_FILE
    if p.exists():
        sha, fp = cm.verify_rules("holders", p, require_committed=False)
        assert len(fp) == 16 and len(sha) == 64


def lim_for(api):
    return hb.Limiter(api, rps=1000.0, sleep=nosleep)


def test_windowed_prints_paging_window_dedupe_and_no_raw_wallet(tmp_path):
    key = cm.load_wallet_key_strict(make_key(tmp_path))
    api = Api()
    base = int(T0)
    rows = [print_row("c1", base + i, wallet=f"{RAW_PREFIX}_{i % 3}") for i in range(25)]
    rows.append(rows[3] | {})  # exact duplicate
    api.trades["c1"] = rows
    got, info = cm.windowed_prints(lim_for(api), "c1", base, base + 100, 5, key, limit=10)
    assert len(got) == 25 and info["duplicates"] == 1 and info["pages"] == 3 and not info["capped"] and info["order_ok"]
    assert all(p["wallet"] and len(p["wallet"]) == 32 for p in got)
    assert RAW_PREFIX not in json.dumps(got)
    got2, info2 = cm.windowed_prints(lim_for(api), "c1", base + 5, base + 9, 5, key, limit=10)
    assert [p["ts"] for p in got2] == [base + 9, base + 8, base + 7, base + 6, base + 5] and info2["out_of_window"] == 0
    # yes terms: buying token 1 at 0.3 is selling YES at 0.7
    api.trades["c2"] = [print_row("c2", base, idx=1, side="BUY", price=0.3)]
    p = cm.windowed_prints(lim_for(api), "c2", base, base, 2, key)[0][0]
    assert p["yes_price"] == pytest.approx(0.7) and p["yes_side"] == -1 and p["side"] == 1


def test_windowed_prints_capped_failed_and_malformed(tmp_path):
    key = cm.load_wallet_key_strict(make_key(tmp_path))
    api = Api()
    base = int(T0)
    api.trades["c1"] = [print_row("c1", base + i) for i in range(30)] + [{"timestamp": base + 5}]
    _, info = cm.windowed_prints(lim_for(api), "c1", base, base + 100, 2, key, limit=10)
    assert info["capped"] is True and info["pages"] == 2
    api.fail_trades.add("c1")
    with pytest.raises(RuntimeError):  # a failed request is never "no data" (the limiter gives up after its retries)
        cm.windowed_prints(lim_for(api), "c1", base, base + 100, 2, key)


def test_idle_is_tempfail_with_a_heartbeat_every_ten_hours(tmp_path):
    r = cm.idle(tmp_path / "j", "waiting", T0)
    assert r["status"] == "idle_heartbeat" and r["complete"] is False
    with pytest.raises(cm.NotNow):
        cm.idle(tmp_path / "j", "waiting", T0 + 3600)
    assert cm.idle(tmp_path / "j", "waiting", T0 + cm.HEARTBEAT_S)["status"] == "idle_heartbeat"


def test_refusals_for_run_ids_and_paths(tmp_path):
    with pytest.raises(cm.Refused):
        cm.refuse_run_id("h8_geo", "h9_flow")
    with pytest.raises(cm.Refused):
        cm.refuse_run_id("other", "h9_flow")
    with pytest.raises(cm.Refused):
        cm.refuse_path(tmp_path / "cb7_extract" / "x")
    assert cm.refuse_path(tmp_path / "creative_batch8") == tmp_path / "creative_batch8"


def test_verify_manifest_files(tmp_path):
    d = tmp_path / "run"
    (d / "screen").mkdir(parents=True)
    f = d / "screen" / "a.csv.gz"
    f.write_bytes(b"x")
    from astrolabe.research_lab import h5_seal

    man = {"file_sha256": {"screen/a.csv.gz": h5_seal.sha256_file(f)}}
    assert cm.verify_manifest_files(d, man) == 1
    (d / "screen" / "b.csv.gz").write_bytes(b"y")
    with pytest.raises(cm.Refused, match="not in the manifest"):
        cm.verify_manifest_files(d, man)
    (d / "screen" / "b.csv.gz").unlink()
    f.write_bytes(b"changed")
    with pytest.raises(cm.Refused, match="differs"):
        cm.verify_manifest_files(d, man)


def test_b_and_flow_rules_hashes_are_independent_of_the_holders_v2_code():
    """The H v2 change (cb8_holders.py, new cb8_common constants) must not move the committed B (cb8_rules.json) or flow rules hashes."""
    from astrolabe.research_lab import cb8_updown as u

    flow = json.loads(cm.FLOW_RULES_FILE.read_text())
    assert cm.rules_file_doc("flow", flow["wallet_key_fingerprint"]) == flow
    assert json.loads(u.RULES_FILE.read_text()) == u.rules_file_doc()
    assert cm.HOLDERS_RULES_FILE.name == "cb8_holders_rules_v2.json" and cm.HOLDERS_RULES_FILE_V1.name == "cb8_holders_rules.json"
    assert cm.rules_doc("holders")["rules_version"] == "cb8-holders-rules-v2"
