# ruff: noqa: E501
"""q0201: CB10 exclusion keys: reachable NOT_EXTRACTABLE, composite-id normalisation, queue exit codes; no rules-hashed function edited."""
import csv
import gzip
import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb6_tail as c6
from astrolabe.research_lab import cb8_books as bk
from astrolabe.research_lab import cb8_exclusion_fix as f8
from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_exclusion_fix as fix9
from astrolabe.research_lab import cb10_common as c10
from astrolabe.research_lab import cb10_exclusion_fix as fix
from astrolabe.research_lab import h5_seal
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb10  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "docs" / "research_lab" / "seals" / "cb10_rules_v2.json"


def _seal(d, name, rels):
    p = Path(d) / f"{name}_SEAL.json"
    p.write_text(json.dumps({"files": {r: "x" for r in rels}}))
    return p


def _seals(d):
    _seal(d, "h7_cb4_series", ["prices/102__555.csv.gz", "pred_prices/200__555.csv.gz"])
    _seal(d, "h8_tail", ["prices/300.csv.gz"])
    _seal(d, "only_pred", ["pred_prices/400__777.csv.gz", "pred_trades/400__778.csv.gz"])  # no market ids, pred files only: was skipped entirely
    _seal(d, "nothing", ["sample.csv.gz"])  # nothing extractable
    return d


def test_cb9_baseline_skips_both_so_not_extractable_was_unreachable(tmp_path):
    ids, used, skipped, _ = bk.seal_copy_ids_audited(_seals(tmp_path), own=())
    assert used == ["h7_cb4_series_SEAL.json", "h8_tail_SEAL.json"]
    assert {(s["name"], s["reason"]) for s in skipped} == {("only_pred_SEAL.json", "no_market_ids"), ("nothing_SEAL.json", "no_market_ids")}
    _final, sp, _pm = fix9.build_seal_plan(tmp_path, used, ids)
    assert not [r for r in sp["per_pin"].values() if r.get("label")]  # label never produced


def test_not_extractable_is_counted_and_pred_only_seal_contributes(tmp_path):
    d = _seals(tmp_path)
    orig = (bk.seal_copy_ids_audited, fix9.build_seal_plan)
    with fix.cb10_exclusion_ids() as stats:
        ids, used, skipped, shas = bk.seal_copy_ids_audited(d, own=())
        assert "only_pred_SEAL.json" in used and "nothing_SEAL.json" in used and not skipped and set(shas) == set(used)
        assert shas["nothing_SEAL.json"] == h5_seal.sha256_file(d / "nothing_SEAL.json")
        assert not [i for i in ids if not i.isdigit()] and ids >= {"102", "300", "200", "400"}
        assert "400" in ids and "777" not in ids  # pred market id of the pred-only seal now reaches the exclusion set
    assert stats["n_not_extractable"] == 1 and stats["not_extractable_seals"] == ["nothing_SEAL.json"]
    assert stats["per_pin"]["nothing_SEAL.json"]["label"] == f8.NOT_EXTRACTABLE and "label" not in stats["per_pin"]["only_pred_SEAL.json"]
    assert stats["per_pin"]["only_pred_SEAL.json"]["n_pred_market_ids"] == 1 and stats["n_pred_event_ids"] == 3
    assert (bk.seal_copy_ids_audited, fix9.build_seal_plan) == orig  # restored


def test_unparseable_and_uncommitted_stay_skipped_with_original_reason(tmp_path):
    d = _seals(tmp_path)
    (d / "bad_SEAL.json").write_text("{not json")
    _seal(d, "draft", ["prices/999.csv.gz"])
    with fix.cb10_exclusion_ids():
        ids, used, skipped, _ = bk.seal_copy_ids_audited(d, own=(), is_committed=lambda p: p.name != "draft_SEAL.json")
    assert {(s["name"], s["reason"].split(":")[0]) for s in skipped} == {("bad_SEAL.json", "unparseable"), ("draft_SEAL.json", "not_committed")} and "999" not in ids


def test_unresolvable_ids_still_refuse(tmp_path):
    from astrolabe.research_lab import cb8_common as cm

    _seal(tmp_path, "badpred", ["pred_prices/abc__1.csv.gz"])
    with fix.cb10_exclusion_ids(), pytest.raises(cm.Refused):
        _i, used, _s, _h = bk.seal_copy_ids_audited(tmp_path, own=())
        c6_ids = {i for i in _i}
        fix9.build_seal_plan(tmp_path, used, c6_ids)


def test_end_to_end_c10_exclusion_keys_under_the_patch(tmp_path):
    seals = tmp_path / "seals"
    seals.mkdir()
    _seals(seals)
    keys = tmp_path / "creative_batch9" / "exclusion_keys.csv.gz"
    keys.parent.mkdir()
    keys.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), [["102", "1", "e102", "", ""], ["200", "1", "555", "", ""]]))
    ksha = h5_seal.sha256_file(keys)
    (keys.parent / c9.EXCLUSION_REPORT_NAME).write_text(json.dumps({"keys_sha256": ksha, "n_ids": 2, "n_missing": 0, "disjointness": "verified"}))
    asked: list[str] = []

    def tr(url, params):
        ids = list(params.get("id") or [])
        asked.extend(ids)
        return 200, json.dumps([{"id": x, "negRiskMarketID": "", "events": [{"id": f"e{x}"}]} for x in ids]).encode(), {}

    out = tmp_path / "cb10"
    with fix.cb10_exclusion_ids() as stats:
        m = c10.exclusion_keys(out, tr, rules_sha="r" * 64, cb9_keys_path=keys, cb9_keys_sha256=ksha, seals_dir=seals, is_committed=None, rps=1000.0, sleep=lambda s: None, data_dumps=None)
    assert sorted(asked) == ["300", "400"] and m["complete"] is True and stats["n_not_extractable"] == 1
    assert m["params"]["exclusion_fix"]["counts"]["n_not_extractable"] == 1 and "nothing_SEAL.json" in m["params"]["seal_copies_used"]
    with gzip.open(out / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        assert {r["market_id"] for r in csv.DictReader(fh)} == {"102", "200", "300", "400"}


def test_exit_codes_via_runner(monkeypatch, capsys, tmp_path):
    from astrolabe.research_lab import cb9_exit

    monkeypatch.setattr(c10, "verify_rules", lambda *a, **k: "r" * 64)  # the stub below would change the hashed source of exclusion_keys
    base = ["exclusion-keys", "--cb9-keys-sha256", "0" * 64, "--normalise-ids", "--root", str(tmp_path / "cb10"), "--rules", str(RULES), "--allow-uncommitted-rules"]
    for m, want in (({"complete": False, "stopped": "network", "transient": True, "status": "in_progress"}, 75),
                    ({"complete": False, "stopped": "walk_failed_terminal", "transient": False, "status": "in_progress"}, 1),
                    ({"complete": True, "stopped": None, "status": c10.EXCLUSION_KEYS_COMPLETE}, 0),
                    ({"complete": True, "stopped": None, "status": c10.UNVERIFIED}, 0)):
        monkeypatch.setattr(c10, "exclusion_keys", lambda *a, _m=m, **k: _m)
        monkeypatch.setattr(run_cb10.time, "time", lambda: c10.T_SEAL_EPOCH + 3600)
        code = run_cb10.main(base)
        out = capsys.readouterr().out
        assert code == want, (m, code, out)
    assert cb9_exit.incomplete_exit_code({"complete": False, "stopped": "x", "transient": False}) == 1
    code = run_cb10.main(base + ["--budget-min", "5"])
    assert code == 2 and "budget-min" in capsys.readouterr().out


def test_draft_spec_wiring():
    d = json.loads((ROOT / "docs" / "research_lab" / "queue" / "drafts" / "q0201_cb10_exclusion_keys.json").read_text())
    argv = d["argv"]
    assert "--normalise-ids" in argv and "repeat" not in d and argv[argv.index("--cb9-keys-sha256") + 1] == "e613604ab15b4e9741275d7860fdf58180525cbd9cb22fa2088a5efdcc6d375f"
    assert argv[argv.index("--data-dumps-cap-gb") + 1] == "50" and "q0182b_cb9_exclusion_keys" in d["depends_on"]
    p = run_cb10.build_parser().parse_args(["exclusion-keys", "--cb9-keys-sha256", "0" * 64, "--normalise-ids"])
    assert p.normalise_ids is True


def test_rules_hashes_unchanged_and_no_hashed_function_edited():
    assert c10.verify_rules(RULES, require_committed=False)
    doc = json.loads(RULES.read_text())
    assert doc["rules_sha256"] == c10.rules_file_doc()["rules_sha256"]
    hashed = " ".join(doc["func_sources_sha256"])
    assert "cb10_exclusion_fix" not in hashed and "cb9_exclusion_fix" not in hashed and "cb9_exit" not in hashed


def test_disclosure_fields_in_params_and_reader(tmp_path):
    seals = tmp_path / "seals"
    seals.mkdir()
    _seals(seals)
    (seals / "broken_SEAL.json").write_text("{not json")
    keys = tmp_path / "creative_batch9" / "exclusion_keys.csv.gz"
    keys.parent.mkdir()
    keys.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), [["102", "1", "e102", "", ""]]))
    ksha = h5_seal.sha256_file(keys)
    (keys.parent / c9.EXCLUSION_REPORT_NAME).write_text(json.dumps({"keys_sha256": ksha, "n_ids": 1, "n_missing": 0, "disjointness": "verified"}))

    def tr(url, params):
        ids = list(params.get("id") or [])
        return 200, json.dumps([{"id": x, "negRiskMarketID": "", "events": [{"id": f"e{x}"}]} for x in ids]).encode(), {}

    out = tmp_path / "cb10"
    orig = c6.exclusion_stage
    with fix.cb10_exclusion_ids():
        m = c10.exclusion_keys(out, tr, rules_sha="r" * 64, cb9_keys_path=keys, cb9_keys_sha256=ksha, seals_dir=seals, is_committed=None, rps=1000.0, sleep=lambda s: None, data_dumps=None)
    assert c6.exclusion_stage is orig
    fx = m["params"]["exclusion_fix"]
    assert fx["cb10_fix_module_sha256"] == fix.module_sha256() and fx["counts"]["n_not_extractable"] == 1
    assert fx["counts"]["n_unparseable_skipped"] == len(fx["unparseable_skipped"]) and "n_cb8_ids" in fx["notes"]
    (out / "manifest.json").write_text(json.dumps(m))
    d = fix.not_verified_disclosure(out / "exclusion_keys.csv.gz")
    assert d["available"] and d["n_not_extractable"] == 1 and d["not_extractable_seals"] == ["nothing_SEAL.json"] and "not verified" in d["note"]
    assert d["n_unparseable_skipped"] == len(fx["unparseable_skipped"])
    assert fix.not_verified_disclosure(tmp_path / "nowhere" / "k.csv.gz")["available"] is False


def test_draft_pins_kd_sample_and_depends_on_smoke():
    d = json.loads((ROOT / "docs/research_lab/queue/drafts/q0201_cb10_exclusion_keys.json").read_text())
    pins = [x for x in d["argv"] if x.startswith("cb9_")]
    assert any("kd_frame_v3/sample.csv.gz" in x for x in pins) and not any("kd_frame_v3/frame.csv.gz" in x for x in pins)
    assert "q0200_cb10_smoke" in d["depends_on"] and "pins_absent" in d["notes"]
