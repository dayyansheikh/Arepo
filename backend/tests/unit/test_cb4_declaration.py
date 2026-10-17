# ruff: noqa: E501
"""CB4 declaration: stable hash, rule-module guard, immutability of the freeze file, pins, date gates."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from astrolabe.research_lab import cb4_declaration as D


def test_hash_is_stable_and_blob_serialises():
    assert D.declaration_sha256() == D.declaration_sha256()
    json.dumps(D.declaration_blob(), default=float)


def test_hash_covers_constants(monkeypatch):
    h = D.declaration_sha256()
    monkeypatch.setitem(D.FLOORS, "C1", 0.02)
    assert D.declaration_sha256() != h


def test_hash_covers_source_of_rule_functions():
    src = D.source_hashes()
    for k in ("cb4_declaration.require_declaration", "cost_regimes.cost_regime", "cb4_data.cadence_class", "economics.sweep_fill", "cb2_weather.small_g_pvalue"):
        assert k in src and len(src[k]) == 64


def test_floors_match_the_design():
    assert D.FLOORS == {"C1": 0.010, "C2": 0.010, "S2": 0.0050, "S3": 0.0050, "N1": 0.0050, "N2": 0.050, "E1": 0.10, "E2": 0.25}
    assert D.N["rho"] == 0.50 and D.N["margin"] == 0.005 and D.FAMILY_M_K == 4
    assert sorted(D.HYPOTHESES_CB4) == sorted(t for v in D.TESTS.values() for t in v)


def test_absent_rule_module_blocks_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "CB4_RULE_MODULES", (*D.CB4_RULE_MODULES, "cb4_not_written_yet"))
    assert "cb4_not_written_yet" in D.absent_modules()
    with pytest.raises(D.DeclarationError):
        D.write_spec(tmp_path / "s.json")
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"declaration_sha256": D.declaration_sha256()}))
    with pytest.raises(D.DeclarationError):
        D.require_declaration(p, require_committed=False)


def _complete(monkeypatch):
    monkeypatch.setattr(D, "CB4_RULE_MODULES", tuple(m for m in D.CB4_RULE_MODULES if m not in D.absent_modules()))


def test_write_spec_never_overwrites_and_pins_are_restricted(tmp_path, monkeypatch):
    _complete(monkeypatch)
    p = tmp_path / "cb4_v1.json"
    pins = {"H": 168, "rho": 0.5, "uma_extra_statuses": []}
    D.write_spec(p, census_pins=pins, census_sha256="a" * 64)
    with pytest.raises(FileExistsError):
        D.write_spec(p)
    assert D.require_declaration(p, require_committed=False) == D.declaration_sha256()
    assert D.load_pins(p) == pins
    with pytest.raises(D.DeclarationError):
        D.spec_payload({"floor_C1": 0.0})  # floors can never be pinned from the census


def test_mutated_hash_or_pins_refused(tmp_path, monkeypatch):
    _complete(monkeypatch)
    p = tmp_path / "s.json"
    spec = D.spec_payload({"H": 84}, "b" * 64)
    spec["declaration_sha256"] = "0" * 64
    p.write_text(json.dumps(spec))
    with pytest.raises(D.DeclarationError, match="hash mismatch"):
        D.require_declaration(p, require_committed=False)
    spec = D.spec_payload({"H": 84}, "b" * 64)
    spec["census_pins"] = {"H": 336}
    p.write_text(json.dumps(spec))
    with pytest.raises(D.DeclarationError, match="census_pins_sha256"):
        D.require_declaration(p, require_committed=False)


def test_uncommitted_spec_refused_when_commit_required(tmp_path, monkeypatch):
    _complete(monkeypatch)
    p = tmp_path / "s.json"
    D.write_spec(p, census_pins={"H": 84}, census_sha256="c" * 64)
    with pytest.raises(D.DeclarationError, match="not committed"):
        D.require_declaration(p)


def test_pins_must_match_census(tmp_path, monkeypatch):
    _complete(monkeypatch)
    census = tmp_path / "census.json"
    pins = {"H": 168, "rho": 0.5, "uma_extra_statuses": []}
    census.write_text(json.dumps({"pin_proposal": pins}))
    from astrolabe.research_lab import provenance

    sp = tmp_path / "s.json"
    D.write_spec(sp, census_pins=pins, census_sha256=provenance.sha256_file(census))
    D.verify_pins_against_census(sp, census)
    census.write_text(json.dumps({"pin_proposal": {**pins, "H": 84}}))
    with pytest.raises(D.DeclarationError):
        D.verify_pins_against_census(sp, census)


def test_refused_runs_and_roots():
    for r in ("h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather"):
        with pytest.raises(D.RefusedRun):
            D.refuse_run_id(r)
    D.refuse_run_id("h7_cb4_era")
    with pytest.raises(D.RefusedRun):
        D.refuse_path("/x/data-dumps/research_lab/cb1_extract/t.csv")
    with pytest.raises(D.RefusedRun):
        D.refuse_path("/x/cb2_extract/t")


def test_rep_pin_max_rule(tmp_path):
    p = tmp_path / "pin.json"
    with pytest.raises(D.WindowError):  # first capture < freeze + 2h
        D.pin_rep_start("abcdef1", "2026-10-28T00:00:00Z", "2026-10-28T01:00:00Z", "2026-10-28T01:00:00Z", p)
    with pytest.raises(D.WindowError):  # not the max rule (floor binds, 10-27)
        D.pin_rep_start("abcdef1", "2026-10-20T00:00:00Z", "2026-10-20T04:00:00Z", "2026-10-20T04:00:00Z", p)
    doc = D.pin_rep_start("abcdef1", "2026-10-20T00:00:00Z", "2026-10-20T04:00:00Z", "2026-10-27T00:00:00Z", p)
    assert doc["t4_rep_end"] == "2026-11-24T00:00:00Z" and doc["t4_rep_out"] == "2026-12-15T00:00:00Z"
    with pytest.raises(D.WindowError):  # pinned once
        D.pin_rep_start("abcdef1", "2026-10-20T00:00:00Z", "2026-10-20T04:00:00Z", "2026-10-27T00:00:00Z", p)
    assert D.rep_window(p)[1] - D.rep_window(p)[0] == 28 * 86400.0
    late = D.pin_rep_start("abcdef2", "2026-10-30T00:00:00Z", "2026-10-30T03:00:00Z", "2026-10-30T03:00:00Z", tmp_path / "p2.json")
    assert late["t4_rep_start"] == "2026-10-30T03:00:00Z"


def test_outcome_reads_refused_before_out_dates(tmp_path):
    early = datetime(2026, 11, 1, tzinfo=UTC)
    with pytest.raises(D.TooEarly):
        D.check_outcome_allowed("dev", early)
    D.check_outcome_allowed("dev", datetime(2026, 11, 8, tzinfo=UTC))
    pin = tmp_path / "p.json"
    D.pin_rep_start("abcdef1", "2026-10-20T00:00:00Z", "2026-10-20T04:00:00Z", "2026-10-27T00:00:00Z", pin)
    with pytest.raises(D.TooEarly):
        D.check_outcome_allowed("rep", datetime(2026, 12, 14, tzinfo=UTC), pin)
    D.check_outcome_allowed("rep", datetime(2026, 12, 15, tzinfo=UTC), pin)


def test_pmxt_window_overlap_and_series_screen_needs_register(tmp_path):
    assert D.in_pmxt_window("2026-05-01", "2026-05-02") and not D.in_pmxt_window("2026-08-12", "2026-09-01")
    with pytest.raises(D.DeclarationError):
        D.check_series_screen_allowed(tmp_path / "missing.json")
    f = tmp_path / "r.json"
    f.write_text("{}")
    with pytest.raises(D.DeclarationError):  # present but not committed
        D.check_series_screen_allowed(f)


def test_hash_is_an_explicit_rule_list_not_every_function():
    src = D.source_hashes()
    assert "cb4_data.run_closewin" not in src and "cb4_data.ReleaseCopies" not in src and "cb4_analysis._census" not in src and "cb4_analysis.fetch_flip_trades" not in src
    for k in ("cb4_data.walk_series_events", "cb4_data.series_roll_to", "cb4_analysis.c_run", "cb4_analysis.stage2_expected", "cb1_history.oldest_or_inf", "cb1_history.taker_fee_ps",
              "cb1_history.parse_outcome0", "history_backfill._asof", "history_sources.rebuild_book", "cb4_rules.s_census_counts"):
        assert k in src and len(src[k]) == 64


def test_every_explicit_rule_function_exists():
    import importlib

    for mod, names in D.EXPLICIT_RULE_FUNCTIONS.items():
        m = importlib.import_module(f"astrolabe.research_lab.{mod}")
        assert all(hasattr(m, n) for n in names), mod


@pytest.mark.parametrize("key", ["MAX_QUOTE_AGE_S", "GRID_S", "ERA_BUFFER_D"])
def test_rule_constants_are_in_the_hash(key, monkeypatch):
    from astrolabe.research_lab import cost_regimes
    from astrolabe.research_lab import history_backfill as hb

    h = D.declaration_sha256()
    assert {"C_SMALL_G", "S_SMALL_G", "INTERPRETATIONS", "FEE_ERAS"} <= set(D.rule_constants())
    target = {"MAX_QUOTE_AGE_S": (hb, 1), "GRID_S": (hb, 1), "ERA_BUFFER_D": (cost_regimes, 1)}[key][0]
    monkeypatch.setattr(target, key, getattr(target, key) + 1)
    assert D.declaration_sha256() != h


@pytest.mark.parametrize("mod,key,val", [("cb1_history", "HALF_SPREAD", ((1.0000001, 0.5),)), ("economics", "MAX_DOCS_RATE", 0.5), ("cb2_weather", "G_MIN", 10),
                                         ("cb2_weather", "N_WILD", 99), ("cb3_declaration", "G_MIN", 10), ("cb3_declaration", "MIN_CLUSTERS", 5),
                                         ("cb4_measure", "PLACEBO_MIN_CLUSTERS", {"event": 30, "day": 30}), ("cb4_rules", "C_TIME_WAY", "week")])
def test_fix6_constants_are_in_the_hash(mod, key, val, monkeypatch):
    import importlib

    h = D.declaration_sha256()
    monkeypatch.setattr(importlib.import_module(f"astrolabe.research_lab.{mod}"), key, val)
    assert D.declaration_sha256() != h


def test_fix6_imported_functions_are_hashed():
    src = D.source_hashes()
    for k in ("cb3_common._codes", "cb3_common.n_clusters", "cb3_common._p_from_z", "history_backfill.load_trades", "history_backfill.load_prices",
              "history_backfill.fee_category", "cb4_analysis.census_gates", "cb4_analysis.load_guarded_outcomes", "cb4_analysis.census_frame"):
        assert k in src and len(src[k]) == 64


def test_a_c1_recorded_in_the_declaration():
    assert D.C["clusters"]["C1"] == ["event", "utc_day_of_e"] and "amendment_A_C1" in D.C
    assert D.ALPHA_STAGE1_ROUTE == 0.01 and D.ALPHA_STAGE2 == 0.05 and D.FLOORS["C1"] == 0.010 and D.FLOORS["C2"] == 0.010 and D.G_MIN == 15
