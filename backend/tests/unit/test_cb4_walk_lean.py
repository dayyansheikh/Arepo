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


# ---- assemble_units_lean (q0082 stage all) -------------------------------------------------------------------------------------------


def _assembly_events():
    """Many series: daily/weekly, sports and crypto, multi-market, weather, shared events, history/h5 overlaps, skipped successors."""
    base = ep("2026-03-01T12:00:00Z")
    out = []
    for s in range(14):
        step = 86400 if s % 2 else 7 * 86400
        for k in range(12):
            end = iso(base + k * step + s * 600)
            e = gevent(f"s{s}e{k}", end, series=f"S{s}", slug=f"slug{s}", winner="Up" if (k + s) % 3 else "Down",
                       fee="sports" if s % 5 == 0 else "crypto", closed=True)
            if s % 4 == 1:  # multi-member (neg-risk style) events
                e["markets"] = [gmarket(f"s{s}e{k}m{j}", end, fee=e["markets"][0]["feeType"], group=f"G{j}", closed=True,
                                        prices='["1","0"]' if j == (k % 3) else '["0","1"]', closed_time=iso(ep(end) + 3600),
                                        created=iso(ep(end) - 2 * 86400)) for j in range(3)]
            if k == 5:  # a successor created late: forces a skipped successor
                for m in e["markets"]:
                    m["createdAt"] = iso(ep(end) - 3600)
                e["createdAt"] = iso(ep(end) - 3600)
            out.append(e)
    out.append(gevent("wxa", iso(base), series="W1", slug="wx", title="Highest temperature in NYC on March 4?"))
    out.append(gevent("wxb", iso(base + 86400), series="W1", slug="wx", title="Highest temperature in NYC on March 5?"))
    shared = gevent("s2e3", iso(base + 3 * 86400 + 1200), series="S2", slug="slug2", closed=True)
    shared["series"].append({"id": "S3", "slug": "slug3"})  # one event in two series (same id seen once, later copy dropped by the walk)
    out.append(shared)
    return out


def _write_walk_files(rdir):
    s, e, modes = (ep("2026-02-20"), ep("2026-06-30"), (True, False))
    ev, g, _rep, st = d.walk_series_events(_lim(FakeNet(events=_assembly_events())), s, e, modes, rdir=rdir, base_days=9, min_width_s=3600)
    assert st is None and len(ev) > 100
    wpath, wgpath = rdir / "walk_events.jsonl.gz", rdir / "walk_guarded.jsonl.gz"
    wpath.write_bytes(d._gz_jsonl_bytes([ev[k] for k in sorted(ev)]))
    wgpath.write_bytes(d._gz_jsonl_bytes([g[k] for k in sorted(g)]))
    return wpath, wgpath


def _asm_kwargs(**over):
    kw = dict(seed="s", n_series=6, n_sports=2, members=5, r_from=ep("2026-03-01"), r_to=ep("2026-06-01"),
              history_ids={"s1e2m0", "s3e4", "Ms6e3"}, h5_ids={"Ms7e6", "Ms8e1"}, sports_cats=("sports",))
    kw.update(over)
    return kw


def test_assemble_units_lean_identical_to_pinned(tmp_path):
    wpath, wgpath = _write_walk_files(tmp_path)
    for over in ({}, {"members": 31, "n_series": 20, "n_sports": 5}, {"members": 3, "n_series": 2, "n_sports": 1},
                 {"history_ids": set(), "h5_ids": set()}):
        kw = _asm_kwargs(**over)
        old = d.assemble_units({e["event_id"]: e for e in d._load_jsonl_gz(wpath)}, {g["event_id"]: g for g in d._load_jsonl_gz(wgpath)}, **kw)
        new = lean.assemble_units_lean(wpath, wgpath, **kw)
        assert json.dumps(old, sort_keys=True, default=float) == json.dumps(new, sort_keys=True, default=float)
        assert old["units"] and len(old["series"]) >= 1
    # the fixture really exercises drops, skipped successors and shared events
    rep = d.assemble_units({e["event_id"]: e for e in d._load_jsonl_gz(wpath)}, {g["event_id"]: g for g in d._load_jsonl_gz(wgpath)}, **_asm_kwargs())["report"]
    assert rep["units_succ_skipped"] >= 1 and rep["series_weather_excluded"] == 1 and rep["unit_drops"]


def test_series_fetch_stage_all_old_vs_lean_assembly_and_resume(tmp_path, monkeypatch):
    """Whole stage-all run (frame first, then units, then a resumed fetch): byte-identical frame/unit files and progress with the
    pinned whole-load assembly and with the lean one; the second run resumes from the first run's partial progress."""
    from tests.unit import test_cb4_data as t

    def old_assemble(wpath, wgpath, **kw):
        return d.assemble_units({e["event_id"]: e for e in d._load_jsonl_gz(wpath)}, {g["event_id"]: g for g in d._load_jsonl_gz(wgpath)}, **kw)

    outs = {}
    for name, fn in (("old", old_assemble), ("new", lean.assemble_units_lean)):
        monkeypatch.setattr(lean, "assemble_units_lean", fn)
        sub = tmp_path / name
        sub.mkdir()
        net = t.series_net(series_ok=True)
        n = {"c": 0}

        def stop(n=n):
            n["c"] += 1
            return n["c"] == 2  # one base window recorded, then pause; the second run resumes the walk, then assembles and fetches

        m1 = t.series_kw(sub, net, should_stop=stop, walk_base_days=3, stage="frame")
        assert m1["complete"] is False and (sub / "hist" / "h7_cb4_series" / "walk_partial.jsonl").exists()
        m2 = t.series_kw(sub, net, walk_base_days=3)
        assert m2["status"] == "series_fetch_complete"
        rdir = sub / "hist" / "h7_cb4_series"
        outs[name] = {p.name: p.read_bytes() for p in sorted(rdir.iterdir()) if p.is_file()
                      and p.name in ("units.jsonl.gz", "series.jsonl.gz", "outcomes_guarded.csv.gz", "units_report.json", "walk_events.jsonl.gz",
                                     "walk_guarded.jsonl.gz", "frame_report.json")}
    assert outs["old"].keys() == outs["new"].keys() and len(outs["old"]) == 7
    assert outs["old"] == outs["new"]
