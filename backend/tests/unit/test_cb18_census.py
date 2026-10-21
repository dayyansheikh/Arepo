# ruff: noqa: E501
"""CB18 part ``pre`` censuses on a synthetic world (tests/unit/cb18_world.py). No real archive file is opened; counts only."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import cb18_world as w  # noqa: E402

from astrolabe.research_lab import cb18_common as c  # noqa: E402
from astrolabe.research_lab import cb18_map as cm  # noqa: E402
from astrolabe.research_lab import cb18_pre as cp  # noqa: E402
from astrolabe.research_lab import cb18_rules_pre as r  # noqa: E402


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return w.build_world(tmp_path_factory.mktemp("cb18"))


def _tree(world, snaps=None):
    return c.PinnedTree(world["seal"], snapshot_root=snaps or world["snapshots"], sweep_root=world["sweeps"], sample_root=world["samples"])


@pytest.fixture(scope="module")
def results(world):
    t = _tree(world)
    return {"S": cp.census_s(t), "F": cp.census_f(t), "P": cp.census_p(t), "R": cm.map_race(t), "M": cm.map_lastmid(t)}


def _walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_keys(v)


def _drop(path: Path) -> None:
    path.rename(path.with_suffix(path.suffix + ".gone"))


# ---- S ---------------------------------------------------------------------------------------------------------------


def test_s_waterfall_classes(results):
    wf = results["S"]["waterfall"]["non_sports"]
    assert wf["silent_1_11"] == 8  # m1: one silent capture in three, 4 a day, 2 census days
    assert wf["uma"] > 0  # m4: non-empty uma at k is excluded
    assert wf["book_touched"] > 0  # m2 / m9 / m10: a fresh book stamp
    assert wf["changed"] > 0  # m2 moves
    sp = results["S"]["waterfall"]["sports"]
    assert sp["silent_1_11"] == 0 and sp["quiet_1_11"] > 0  # m5 sports kept apart


def test_s_lookback_gap_is_unavailable_not_zero(results):
    assert "unavailable" in json.dumps(results["S"]["lookback"])


def test_s_no_burst_in_synthetic_world(results):
    assert all(pc["burst"] is False for pc in results["S"]["per_capture"])


# ---- F ---------------------------------------------------------------------------------------------------------------


def test_f_breakpoints(results):
    f = results["F"]
    assert set(f["breakpoints"]) == {str(b) for b in r.F_BREAKPOINTS}
    assert f["breakpoints"]["50"]["positions"] == 0 and f["breakpoints"]["50"]["churn_share"] is None
    assert f["breakpoints"]["10"]["crossings"] > 0  # m11 oscillates across rank 10


# ---- P ---------------------------------------------------------------------------------------------------------------


def test_p_states_and_gates(results):
    p = results["P"]
    assert p["counts"]["pass_pairs_unavailable_unsealed"] == 2
    st = p["non_sports"]["states"]
    assert st["fade"] > 0 and st["follow"] > 0  # m9 fades, m10 follows
    assert p["non_sports"]["truncated"] == 0
    assert p["gates_non_sports"]["GP5"] is False  # NaN proxy SE: GP5 fails closed
    assert p["route"]["route"] == "dropped uncounted"


# ---- R ---------------------------------------------------------------------------------------------------------------


def test_r_race_definition(results):
    R = results["R"]
    # per sample: 0xaa / 0xbb (same ts, different tx) are raced; the 0xcc pair (same tx) is not a race
    assert R["counts"]["rows_raced"] == 2 * R["pairs"]["pairs"]
    assert R["pairs"]["pairs"] == 23


def test_no_forbidden_keys_in_any_output(results):
    banned = set(r.FORBIDDEN_OUTPUT_KEYS)
    for fam, doc in results.items():
        assert not (banned & set(map(str, _walk_keys(doc)))), fam


# ---- M ---------------------------------------------------------------------------------------------------------------


def test_m_exits_gap_adjacent_and_reappearance(results):
    M = results["M"]
    assert M["exits"] == 2
    assert M["all"]["gap_adjacent"] == 1  # m7 last present at the last capture before the gap
    assert M["without_gap_adjacent"]["exits"] == 1
    assert M["reappearances_after_exit"] == 1  # m8
    assert len(M["gap_disclosure"]["gap_slots"]) == 6


# ---- guards ----------------------------------------------------------------------------------------------------------


def test_unpinned_and_mismatched_files_refused(world):
    seal = json.loads(json.dumps(world["seal"]))
    cap = sorted(c.seal_inventory(seal)["captures"])[0]
    key = f"{r.ARCHIVE_PREFIX}snapshots/{cap}/manifest.json"
    seal["files"][key]["sha256"] = "0" * 64
    t = c.PinnedTree(seal, snapshot_root=world["snapshots"], sweep_root=world["sweeps"], sample_root=world["samples"])
    with pytest.raises(r.Refused):
        t.path("snapshots", cap, "manifest.json")
    del seal["files"][key]
    t = c.PinnedTree(seal, snapshot_root=world["snapshots"], sweep_root=world["sweeps"], sample_root=world["samples"])
    with pytest.raises(r.Refused):
        t.path("snapshots", cap, "manifest.json")


def test_missing_file_is_notnow(world, tmp_path):
    snaps = tmp_path / "snapshots"
    shutil.copytree(world["snapshots"], snaps)
    cap = sorted(c.seal_inventory(world["seal"])["captures"])[3]
    _drop(snaps / cap / "rows.csv.gz")
    with pytest.raises(r.NotNow):
        _tree(world, snaps).path("snapshots", cap, "rows.csv.gz")


def test_forbidden_and_unlisted_fields_refused(world):
    t = _tree(world)
    cap = sorted(c.seal_inventory(world["seal"])["captures"])[0]
    for bad in ("outcome_prices", "closed_time", "question", "chg_1h"):
        with pytest.raises(r.Refused):
            c.read_capture(t, cap, ["market_id", bad])


def test_byteflag_exposes_no_value():
    f = c.ByteFlag("chg_1h", ["0.001", "0.002"])
    with pytest.raises(r.Refused):
        f._d  # noqa: B018
    with pytest.raises(r.Refused):
        c.ByteFlag("best_bid", ["1"])
    g = c.ByteFlag("chg_1h", ["0.001", "0.003"])
    assert list(c.bytes_equal(f, g)) == [True, False]
    u = c.ByteFlag("uma_resolution_statuses", ["[]", "", '["proposed"]'])
    assert list(c.is_empty_literal(u)) == [True, False, False]  # an empty field is 'missing', not the empty literal
    assert list(c.is_missing(u)) == [False, True, False]


def test_cutoff_refusal(world):
    cap = sorted(c.seal_inventory(world["seal"])["captures"])[-1]
    with pytest.raises(r.Refused):
        c.read_capture(_tree(world), cap, ["market_id"], cutoff="2026-10-11T00:00:00Z")


def test_root_must_carry_archive_name(world, tmp_path):
    with pytest.raises(r.Refused):
        c.PinnedTree(world["seal"], snapshot_root=tmp_path / "elsewhere")


# ---- runner ----------------------------------------------------------------------------------------------------------


def _runner():
    spec = importlib.util.spec_from_file_location("run_cb18", Path(__file__).resolve().parents[2] / "scripts" / "run_cb18.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _args(world, cmd, out, snaps=None, disk="20"):
    return [cmd, "--seal", str(world["seal_path"]), "--snapshot-root", str(snaps or world["snapshots"]), "--sweep-root", str(world["sweeps"]), "--sample-root", str(world["samples"]),
            "--out", str(out), "--disk-cap-gb", disk, "--data-dumps-cap-gb", "40", "--standalone", "--allow-uncommitted-rules", "--no-trials"]


def test_runner_census_is_written_once(world):
    run = _runner()
    out = world["out_dir"] / "F.json"
    assert run.main(_args(world, "census-f", out)) == 0
    doc = json.loads(out.read_text())
    assert doc["n_tests"] == 0 and doc["kind"] == r.TRIAL_KIND and doc["rules_version"] == r.RULES_VERSION
    assert run.main(_args(world, "census-f", out)) == run.REFUSED


def test_runner_refuses_excess_caps_and_foreign_output_root(world, tmp_path):
    run = _runner()
    assert run.main(_args(world, "census-f", world["out_dir"] / "F2.json", disk="21")) == run.REFUSED
    assert run.main(_args(world, "census-f", tmp_path / "F3.json")) == run.REFUSED


def test_runner_missing_input_is_exit_75_without_output(world, tmp_path):
    run = _runner()
    snaps = tmp_path / "snapshots"
    shutil.copytree(world["snapshots"], snaps)
    cap = next(cid for cid in sorted(c.seal_inventory(world["seal"])["captures"]) if cid.startswith("20261015T1"))  # inside S's census days (earlier captures are not read by S)
    _drop(snaps / cap / "rows.csv.gz")
    out = world["out_dir"] / "S4.json"
    assert run.main(_args(world, "census-s", out, snaps)) == run.TEMPFAIL
    assert not out.exists()
