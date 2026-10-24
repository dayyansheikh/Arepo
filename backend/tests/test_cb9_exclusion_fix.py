# ruff: noqa: E501
"""q0182b fixes: composite seal ids never reach Gamma's integer ``id`` filter in CB9 exclusion-keys, with the CB8 q0164b mapping rule, and incomplete runs exit 75."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb6_tail as c6
from astrolabe.research_lab import cb8_books as bk
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_exclusion_fix as f8
from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_exclusion_fix as fix

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb9  # noqa: E402


class FakeLim:
    """Mimics Gamma: a non-integer id is a 422 for the whole request."""

    def __init__(self):
        self.calls = []

    def get(self, url, params):
        ids = params["id"]
        self.calls.append(list(ids))
        if any(not str(i).isdigit() for i in ids):
            return 422, {"type": "validation error"}
        return 200, [{"id": i, "events": [{"id": f"e{i}"}], "negRiskMarketID": ""} for i in ids]


def _seal(d, name, rels):
    p = Path(d) / f"{name}_SEAL.json"
    p.write_text(json.dumps({"files": {r: "x" for r in rels}}))
    return p


def _seals(tmp_path):
    _seal(tmp_path, "h7_cb4_series", ["prices/102__555.csv.gz", "trades/102__555.csv.gz", "pred_prices/200__555.csv.gz", "pred_trades/102__556.csv.gz"])
    _seal(tmp_path, "h8_tail", ["prices/300.csv.gz"])
    _seal(tmp_path, "h8_text", ["sample.csv.gz"])
    return tmp_path


def test_seal_plan_uses_cb8_rule_and_counts(tmp_path):
    d = _seals(tmp_path)
    ids, used, skipped, _ = bk.seal_copy_ids_audited(d, own=())
    assert "102__555" in ids and used == ["h7_cb4_series_SEAL.json", "h8_tail_SEAL.json"] and skipped[0]["reason"] == "no_market_ids"
    final, sp, pm = fix.build_seal_plan(d, used, ids)
    assert final == {"102", "200", "300"} and pm == {"200": {"555"}, "102": {"556"}}
    c = sp["counts"]
    assert (c["n_composite_replaced"], c["n_pred_market_ids"], c["n_pred_market_ids_new"], c["n_pred_event_ids"]) == (1, 2, 1, 2)
    assert sp["per_pin"]["h7_cb4_series_SEAL.json"]["n_pred_market_ids"] == 2
    assert f8.normalise_ids({"102__555", "1"})[0] == {"102", "1"}  # the very same function as CB8


def test_unresolvable_ids_refuse(tmp_path):
    with pytest.raises(cm.Refused, match="cannot be resolved"):
        fix.build_seal_plan(_seals(tmp_path), [], {"100", "bad__1x"})
    _seal(tmp_path, "badpred", ["pred_prices/abc__1.csv.gz"])
    with pytest.raises(cm.Refused):
        fix.build_seal_plan(tmp_path, ["badpred_SEAL.json"], set())


class FakeFr:
    def __init__(self, rdir):
        self.rdir, self.recorded, self.params = rdir, [], {}

    def record_file(self, p):
        self.recorded.append(Path(p).name)


PLAN = {"ids_sha256": "a" * 64, "pins": [{"name": "x", "kind": "seal", "sha256": "b" * 64}], "counts": {}}


def test_sidecar_write_once_and_repeat_with_other_set_refuses(tmp_path):
    fr = FakeFr(tmp_path)
    fix._sidecar_and_aside(fr, PLAN)
    assert fix.SIDECAR in fr.recorded and json.loads((tmp_path / fix.SIDECAR).read_text())["ids_sha256"] == "a" * 64
    fix._sidecar_and_aside(FakeFr(tmp_path), PLAN)
    with pytest.raises(cm.Refused, match="differs"):
        fix._sidecar_and_aside(FakeFr(tmp_path), {**PLAN, "ids_sha256": "0" * 64})
    with pytest.raises(cm.Refused, match="differs"):
        fix._sidecar_and_aside(FakeFr(tmp_path), {**PLAN, "pins": []})


def test_failed_manifest_copied_aside_once_never_overwritten(tmp_path):
    failed = b'{"stopped": "stage_failed: gamma markets lookup status 422"}'
    (tmp_path / "manifest.json").write_bytes(failed)
    fr = FakeFr(tmp_path)
    fix._sidecar_and_aside(fr, PLAN)
    assert (tmp_path / fix.ASIDE).read_bytes() == failed
    assert (tmp_path / fix.ASIDE_SHA).read_text().strip() == hashlib.sha256(failed).hexdigest() and {fix.ASIDE, fix.ASIDE_SHA, fix.SIDECAR} <= set(fr.recorded)
    (tmp_path / "manifest.json").write_bytes(b"{}")
    fix._sidecar_and_aside(FakeFr(tmp_path), PLAN)
    assert (tmp_path / fix.ASIDE).read_bytes() == failed
    d2 = tmp_path / "r2"
    d2.mkdir()
    (d2 / "manifest.json").write_bytes(failed)
    (d2 / fix.ASIDE).write_bytes(b"other")
    with pytest.raises(cm.Refused, match="overwrite"):
        fix._sidecar_and_aside(FakeFr(d2), PLAN)
    d3 = tmp_path / "r3"  # no manifest (the host state of q0182): no aside copy, sidecar only
    d3.mkdir()
    fix._sidecar_and_aside(FakeFr(d3), PLAN)
    assert not (d3 / fix.ASIDE).exists() and (d3 / fix.SIDECAR).exists()


def test_stage_wrapper_normalises_refuses_non_integer_and_restores(tmp_path, monkeypatch):
    (tmp_path / "s").mkdir()
    d = _seals(tmp_path / "s")
    orig = (bk.seal_copy_ids_audited, c9.load_exclusion_keys, c6.exclusion_stage, c6.lookup_keys)
    seen = {}
    monkeypatch.setattr(c6, "exclusion_stage", lambda fr, ids, should_stop=None: seen.setdefault("ids", set(ids)) and (None, "x"))
    monkeypatch.setattr(c9, "load_exclusion_keys", lambda p: ({"102"}, {}, {}, ""))
    rdir = tmp_path / "run"
    rdir.mkdir()
    fr = FakeFr(rdir)
    with fix.normalised_exclusion_ids([{"name": "holders", "sha256": "c" * 64}]) as stats:
        c9.load_exclusion_keys("k")
        ids, used, _sk, shas = bk.seal_copy_ids_audited(d, own=())
        assert not [i for i in ids if not i.isdigit()] and shas
        c6.exclusion_stage(fr, ids - {"102"}, None)
        assert seen["ids"] == {"200", "300"} and fr.params["exclusion_fix"]["counts"]["n_cb8_ids"] == 1 and fr.params["exclusion_fix"]["counts"]["n_new_ids_final"] == 2
        side = json.loads((rdir / fix.SIDECAR).read_text())
        assert {"name": "holders", "kind": "ids", "sha256": "c" * 64} in side["pins"] and side["ids_sha256"] == f8.ids_sha256({"200", "300"})
        with pytest.raises(cm.Refused, match="not integer"):
            c6.exclusion_stage(fr, {"100", "1__x"}, None)
    assert stats["n_composite_replaced"] == 1
    assert bk.seal_copy_ids_audited is orig[0] and c9.load_exclusion_keys is not None and c6.lookup_keys is orig[3]
    assert c6.exclusion_stage is not None and "fix" not in c6.exclusion_stage.__qualname__


def test_pred_event_ids_attached_to_new_markets(tmp_path, monkeypatch):
    d = _seals(tmp_path)
    lim = FakeLim()
    with fix.normalised_exclusion_ids() as stats:
        ids, used, _, _ = bk.seal_copy_ids_audited(d, own=())
        found, _ = c6.lookup_keys(lim, sorted(ids))  # the unchanged lookup now sees only integers: no 422
    assert found["200"]["event_ids"].split(";") == ["e200", "555"] and found["102"]["event_ids"].split(";") == ["e102", "556"]
    assert stats["pred_event_ids_attached_new_this_session"] == 2 and len(lim.calls) == 1


def test_exit_code_incomplete_is_75_budget_pause_and_complete_are_0():
    f = run_cb9.exclusion_exit_code
    assert f({"complete": False, "stopped": "stage_failed: gamma markets lookup status 422", "transient": True}) == run_cb9.TEMPFAIL == 75
    assert f({"complete": False, "stopped": "paused_429_chunk_limit", "transient": True}) == 75
    assert f({"complete": False, "stopped": "budget reached", "transient": True}) == 0
    assert f({"complete": True, "stopped": None}) == 0


def test_cli_flag_and_job_spec_wiring():
    a = run_cb9.build_parser().parse_args(["exclusion-keys", "--cb8-keys-sha256", "0" * 64, "--normalise-ids"])
    assert a.normalise_ids is True
    root = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "queue" / "jobs"
    old, new = (json.loads((root / f"{n}_cb9_exclusion_keys.json").read_text()) for n in ("q0182", "q0182b"))
    assert new["argv"] == old["argv"] + ["--normalise-ids"]
    for k in ("resources", "timeout_s", "max_retries", "depends_on", "data", "outputs"):
        assert new[k] == old[k]
    assert "--normalise-ids" not in old["argv"]  # q0182 stays recorded as registered
    draft = json.loads((root.parent / "drafts" / "q0201_cb10_exclusion_keys.json").read_text())
    assert "q0182b_cb9_exclusion_keys" in draft["depends_on"] and "q0182_cb9_exclusion_keys" not in draft["depends_on"]
