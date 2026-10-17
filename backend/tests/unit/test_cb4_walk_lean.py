# ruff: noqa: E501
"""Old (pinned ``cb4_data.walk_series_events`` + whole-dict writers) vs lean walk: identical reports, frame counts, output
bytes and partial files on a synthetic Gamma fixture (docs/research_lab/queue q0082f OOM fix)."""

from __future__ import annotations

import json
import shutil

from astrolabe.research_lab import cb4_data as d
from astrolabe.research_lab import cb4_walk_lean as lean
from astrolabe.research_lab import history_backfill as hb
from tests.unit.test_cb4_data import FakeNet, ep, gevent, gmarket, iso


def _events():
    base = ep("2026-03-01T12:00:00Z")
    evs = []
    for k in range(40):
        e = gevent(f"ev{k}", iso(base + k * 86400 * 0.7), series=f"S{k % 3}", slug=f"s{k % 3}", fee="crypto" if k % 2 else "sports", closed=bool(k % 4))
        if k % 5 == 0:
            e["markets"] += [gmarket(f"x{k}_{j}", e["endDate"], fee="politics", closed=e["closed"]) for j in range(3)]
        evs.append(e)
    evs.append(gevent("wx1", iso(base + 3600), series="W1", slug="wx", title="Highest temperature in NYC on March 4?"))
    evs.append(gevent("noser", iso(base + 7200), series=None))
    dup = gevent("ev3", iso(base + 9 * 86400), series="S0", slug="s0", closed=True)  # same id, later window: first occurrence wins
    dup["markets"][0]["id"] = "DUPM"
    evs.append(dup)
    nomk = gevent("nomk", iso(base + 5 * 86400), series="S1", slug="s1")
    nomk["markets"] = []
    evs.append(nomk)
    return evs


def _lim(net):
    return hb.Limiter(net, rps=4.0, sleep=lambda s: None)


def _args():
    return (ep("2026-03-01"), ep("2026-04-05"), (True, False))


def _old_outputs(events, guarded):
    return d._gz_jsonl_bytes([events[k] for k in sorted(events)]), d._gz_jsonl_bytes([guarded[k] for k in sorted(guarded)])


def _same(old_dir, new_dir, *, stop_after=None, chunk=lean.CHUNK_BYTES):
    s, e, modes = _args()
    ev, g, rep, st = d.walk_series_events(_lim(FakeNet(events=_events())), s, e, modes, rdir=old_dir, base_days=3, min_width_s=3600)
    store, rep2, st2 = lean.walk_series_events_lean(_lim(FakeNet(events=_events())), s, e, modes, rdir=new_dir, base_days=3, min_width_s=3600)
    assert (st, rep) == (st2, rep2)
    assert store.frame_counts() == d.series_frame_counts(ev)
    eb, gb = _old_outputs(ev, g)
    b = hb.DiskBudget(new_dir, 10**9)
    store.write_events(b, new_dir / "ev.gz", chunk)
    store.write_guarded(b, new_dir / "g.gz", chunk)
    assert (new_dir / "ev.gz").read_bytes() == eb and (new_dir / "g.gz").read_bytes() == gb
    assert (old_dir / "walk_partial.jsonl").read_bytes() == (new_dir / "walk_partial.jsonl").read_bytes()
    assert (old_dir / "walk_partial_guarded.jsonl").read_bytes() == (new_dir / "walk_partial_guarded.jsonl").read_bytes()
    assert len(ev) > 20 and len(g) == len(ev)
    return ev


def test_fresh_walk_identical(tmp_path):
    for sub in ("o", "n"):
        (tmp_path / sub).mkdir()
    _same(tmp_path / "o", tmp_path / "n")


def test_chunked_output_identical(tmp_path):
    for sub in ("o", "n"):
        (tmp_path / sub).mkdir()
    _same(tmp_path / "o", tmp_path / "n", chunk=1)  # one event per chunk


def test_resume_from_old_partials_with_duplicates_and_fail_lines(tmp_path):
    s, e, modes = _args()
    n = {"c": 0}

    def stop():
        n["c"] += 1
        return n["c"] > 6

    src = tmp_path / "src"
    src.mkdir()
    _ev, _g, _rep, st = d.walk_series_events(_lim(FakeNet(events=_events())), s, e, modes, rdir=src, base_days=3, min_width_s=3600, should_stop=stop)
    assert st == "walk_paused"
    pg = src / "walk_partial_guarded.jsonl"
    pp = src / "walk_partial.jsonl"
    lines = pg.read_text().splitlines()
    first = json.loads(lines[0])
    changed = {**first, "guarded": [{**x, "event_closed": not x["event_closed"]} for x in first["guarded"]]}
    pg.write_text("\n".join(lines) + "\n" + json.dumps(changed, default=float) + "\n")  # later guarded line for the same window wins
    with pp.open("a") as fh:  # a dangling failed attempt and a guarded line without its slim line
        fh.write(json.dumps({"mode": True, "a": "2026-03-01T00:00:00Z", "fail": True}) + "\n")
        fh.write(json.dumps({"mode": False, "a": "2099-01-01T00:00:00Z", "fail": True}) + "\n")
    with pg.open("a") as fh:
        fh.write(json.dumps({"mode": False, "a": "2099-02-01T00:00:00Z", "guarded": []}) + "\n")
    o, nw = tmp_path / "o", tmp_path / "n"
    shutil.copytree(src, o)
    shutil.copytree(src, nw)
    ev, g, rep, st1 = d.walk_series_events(_lim(FakeNet(events=_events())), s, e, modes, rdir=o, base_days=3, min_width_s=3600)
    store, rep2, st2 = lean.walk_series_events_lean(_lim(FakeNet(events=_events())), s, e, modes, rdir=nw, base_days=3, min_width_s=3600)
    assert (st1, rep) == (st2, rep2)
    assert store.frame_counts() == d.series_frame_counts(ev)
    eb, gb = _old_outputs(ev, g)
    b = hb.DiskBudget(nw, 10**9)
    store.write_events(b, nw / "ev.gz", 200)
    store.write_guarded(b, nw / "g.gz", 200)
    assert (nw / "ev.gz").read_bytes() == eb and (nw / "g.gz").read_bytes() == gb
    # the changed (later) guarded line really won in both
    assert any(x["event_closed"] != json.loads(lines[0])["guarded"][0]["event_closed"] for x in g.values() if x["event_id"] == first["guarded"][0]["event_id"])


def test_pause_and_failed_window_returns_match(tmp_path):
    s, e, modes = _args()
    for sub in ("o", "n"):
        (tmp_path / sub).mkdir()
    c = {"o": 0, "n": 0}

    def mk(key):
        def stop():
            c[key] += 1
            return c[key] == 3
        return stop

    _, _, rep, st = d.walk_series_events(_lim(FakeNet(events=_events())), s, e, modes, rdir=tmp_path / "o", base_days=3, min_width_s=3600, should_stop=mk("o"))
    _, rep2, st2 = lean.walk_series_events_lean(_lim(FakeNet(events=_events())), s, e, modes, rdir=tmp_path / "n", base_days=3, min_width_s=3600, should_stop=mk("n"))
    assert (st, rep) == (st2, rep2) == ("walk_paused", rep)
    bad = FakeNet(events=_events())
    orig = bad.__call__
    bad_n = {"c": 0}

    def flaky(url, params):
        bad_n["c"] += 1
        return (500, b"{}", {}) if bad_n["c"] > 4 else orig(url, params)

    _, rep3, st3 = lean.walk_series_events_lean(_lim(flaky), s, e, modes, rdir=tmp_path / "n", base_days=3, min_width_s=3600)
    assert st3.startswith("walk_failed_window") and rep3["events_kept"] == 0


def test_over_budget_write_is_refused_and_leaves_no_file(tmp_path):
    import pytest

    s, e, modes = _args()
    store, _r, _s = lean.walk_series_events_lean(_lim(FakeNet(events=_events())), s, e, modes, rdir=tmp_path, base_days=3, min_width_s=3600)
    with pytest.raises(OSError):
        store.write_events(hb.DiskBudget(tmp_path, 1), tmp_path / "ev.gz")
    assert not (tmp_path / "ev.gz").exists() and not (tmp_path / "ev.gz.tmp").exists()
