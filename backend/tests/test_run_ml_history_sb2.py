"""SB2 J7/J8 flags of scripts/run_ml_history.py (small synthetic inputs only)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_ml_history.py"
spec = importlib.util.spec_from_file_location("run_ml_history_under_test", SCRIPT)
rmh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rmh
spec.loader.exec_module(rmh)


def _panel(path: Path, n_markets: int = 40, per: int = 5) -> None:
    ids = [str(100 + i) for i in range(n_markets) for _ in range(per)]
    pd.DataFrame({"market_id": ids}).to_csv(path, index=False)


def test_cells_restrict_declared_cells_only():
    cm = rmh.parse_cells("direction:1,updown:1,updown:3")
    assert cm == {1: ["direction", "updown"], 3: ["updown"]}
    args = SimpleNamespace(kinds=["direction", "absmove", "updown"], cells_map=cm)
    assert rmh.kinds_for(args, 1) == ["direction", "updown"]
    assert rmh.kinds_for(args, 3) == ["updown"]
    assert rmh.kinds_for(args, 12) == []
    assert rmh.kinds_for(SimpleNamespace(kinds=["direction"], cells_map=None), 12) == ["direction"]
    assert rmh.parse_cells(None) is None
    with pytest.raises(ValueError):
        rmh.parse_cells("direction:7")


def test_exclude_markets_removes_every_listed_market_before_sampling(tmp_path):
    panel = tmp_path / "panel.csv"
    _panel(panel)
    base, _ = rmh.pick_markets(panel, 120, 7)
    again, rows = rmh.pick_markets(panel, 120, 7)
    assert base == again  # default path unchanged and deterministic
    lst = tmp_path / "sample_markets.csv"
    pd.DataFrame({"market_id": sorted(base)}).to_csv(lst, index=False)
    ex, _src = rmh.load_market_list(str(lst), panel)
    assert ex == base
    kept, rows2 = rmh.pick_markets(panel, 120, 7, exclude=ex)
    assert kept and not (kept & ex) and rows2 <= 120
    # the seed spec regenerates the original subset deterministically
    regen, _ = rmh.load_market_list("seed:7:120", panel)
    assert regen == base
    js = tmp_path / "m.json"
    js.write_text(json.dumps({"market_ids": ["100", "101"]}))
    assert rmh.load_market_list(str(js), panel)[0] == {"100", "101"}
    txt = tmp_path / "m.txt"
    txt.write_text("market_id\n100\n102\n")
    assert rmh.load_market_list(str(txt), panel)[0] == {"100", "102"}


def test_frozen_with_nothing_advanced_exits_zero(tmp_path, capsys):
    frozen = tmp_path / "r.json"
    frozen.write_text(json.dumps({"1": {"direction": {"regime_ix": {
        "advanced": {"contrasts": [], "pairs": []}}}}}))
    root = tmp_path / "hist"
    rc = rmh.main(["--run-id", "h3", "--root", str(root), "--frozen-from", str(frozen),
                   "--revision", "h3_r5_rep", "--trials-path", str(tmp_path / "t.jsonl")])
    assert rc == 0
    assert "nothing to replicate" in capsys.readouterr().out
    out = json.loads((root / "h3" / "ml_history_results_h3_r5_rep.json").read_text())
    assert out["nothing_to_replicate"] is True
    assert not (tmp_path / "t.jsonl").exists()  # no panel read, no trial logged


def test_prior_tests_equals_battery2_cumulative_total(tmp_path, monkeypatch):
    from astrolabe.research_lab import battery2, ml_explain

    trials = tmp_path / "trials.jsonl"
    lines = [{"kind": "ml_explain", "n_tests": 4, "evidence_role": "exploratory_historical"},
             {"kind": "ml_explain", "n_tests": 3, "evidence_role": "placebo"},
             {"kind": "ml_explain", "n_tests": 5, "evidence_role": "exploratory_historical",
              "source": "hypothesis_battery_1"}]
    trials.write_text("\n".join(json.dumps(r) for r in lines) + "\n")
    prior = rmh.load_prior_tests(trials)
    assert prior["total"] == battery2.cumulative_count(trials)["total"] == 9
    seen = {}

    def fake(*a, **kw):
        seen.update(kw)
        return {"declaration_hash": "h", "advanced": {"contrasts": [], "pairs": []},
                "contrasts": {}}

    monkeypatch.setattr(ml_explain, "regime_ix_discover", fake)
    lab = pd.DataFrame({"y_absmove": [0, 1], "market_id": ["1", "2"]})
    args = SimpleNamespace(prior_tests=prior, interactions=0, regimes=True, discover_frac=0.5,
                           n_boot_abl=10, lookahead_markets=None, n_cells=1,
                           trials_path=trials, revision="r5_regime_ix")
    rmh.run_regime_ix("updown", lab, "y_absmove", [], None, None, {}, (), args, {})
    assert seen["prior_tests"] == 9
    assert seen["family_tests"] == 4
    recs = [json.loads(ln) for ln in trials.read_text().splitlines()]
    assert recs[-1]["source"] == "screening_batch_2:J7" and recs[-1]["prior_tests"] == 9
