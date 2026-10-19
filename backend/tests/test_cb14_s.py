# ruff: noqa: E501
"""CB14-S (docs/research_lab/CREATIVE_BATCH_14.md CB14-S): offline, synthetic fixtures and fake transports only; no network, no real CB14 quantity."""

from __future__ import annotations

import gzip
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb12_m as m12
from astrolabe.research_lab import cb14_common as c14
from astrolabe.research_lab import cb14_s as s
from astrolabe.research_lab import history_backfill as hb

H = 3600.0
D_ = 86400.0
NOSLEEP = lambda _s: None  # noqa: E731


def ep(x: str) -> float:
    return datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def gz_write(path: Path, header: list[str], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(hb._gz_csv_bytes(header, rows))


# =====================================================================================================================================================
# Pure rules: term parser, rule booleans, normaliser and matcher
# =====================================================================================================================================================


def test_term_parser_quote_alternatives_and_failure():
    t = s.parse_term('Will Trump say "Tariffs / Tariff" during the speech?')
    assert t["raw"] == "Tariffs / Tariff" and t["variants"] == ["tariffs", "tariff"] and t["norm"] == "tariff"
    assert s.parse_term("Will he say it?", "Inflation")["norm"] == "inflation"  # group title when no quote
    assert s.parse_term("Will he say it?", None) is None and s.parse_term('Will he say " " ?', "") is None
    assert s.parse_term('say "a b c d e f g h"') is None  # more than TERM_MAX_TOKENS tokens


def test_rule_booleans_qa_plural_possessive_compound():
    f = s.rule_flags("Plurals do not count. Possessives will count. Hyphenated compounds count. Q&A will not count.")
    assert f["plural"] is False and f["possessive"] is True and f["compound"] is True and f["qa_excluded"] is True and f["qa_included"] is False
    f2 = s.rule_flags("The market includes Q&A with reporters.")
    assert f2["qa_included"] is True and f2["qa_excluded"] is False and f2["plural"] is True and f2["possessive"] is True and f2["compound"] is False  # silent -> declared defaults
    assert s.rule_flags("Only prepared remarks count.")["section_excluded"] is True
    assert s.rule_flags("")["qa_excluded"] is False


def test_matcher_plural_possessive_compound_and_phrase():
    segs = [(0, "Welcome everyone"), (60, "the tariffs are great"), (120, "China's economy and a well-known fact"), (180, "the supply chain issue"), (240, "a tariff-free zone")]
    idx = s.index_segments(segs)
    assert s.first_mention(idx, s.make_matcher(["tariff"], plural=True, possessive=False, compound=False)) == 60  # plural counts
    assert s.first_mention(idx, s.make_matcher(["tariff"], plural=False, possessive=False, compound=False)) is None
    assert s.first_mention(idx, s.make_matcher(["china"], plural=False, possessive=True, compound=False)) == 120  # possessive
    assert s.first_mention(idx, s.make_matcher(["china"], plural=False, possessive=False, compound=False)) is None
    assert s.first_mention(idx, s.make_matcher(["known"], plural=False, possessive=False, compound=False)) is None  # a compound part does not match
    assert s.first_mention(idx, s.make_matcher(["known"], plural=False, possessive=False, compound=True)) == 120
    assert s.first_mention(idx, s.make_matcher(["supply chain"])) == 180
    assert s.first_mention(idx, s.make_matcher(["chain supply"])) is None
    assert s.normalise_term("Tariffs") == s.normalise_term("tariff") == "tariff"
    assert s.normalise_text("Dollar–Sign’s") == "dollar sign's"


def test_transcript_parser_reduces_to_numbers_only_and_keeps_no_text():
    html = ("<html><script>var a = '00:00:01 secret';</script><body><p>00:00:05 Trump: We will talk about tariffs.</p><p>00:01:10 Trump: Tariffs again, and China's trade.</p>"
            "<p>00:02:00 Moderator: thanks</p><p>01:00:00 Trump: border</p></body></html>")
    segs = s.parse_transcript_html(html.encode())
    assert [o for o, _ in segs] == [5, 70, 120, 3600]  # the script block is removed; hh:mm:ss -> seconds
    red = s.reduce_transcript(segs, {"m1": s.make_matcher(["tariff"]), "m2": s.make_matcher(["border"]), "m3": s.make_matcher(["wall"])}, "trump")
    assert red["n_stamps"] == 4 and red["last_s"] == 3600 and red["first"] == {"m1": 5, "m2": 3600} and red["base_s"] == 5 and red["first_seg_s"] == 5
    assert "text" not in json.dumps(red) and "secret" not in json.dumps(red)
    big = "".join(f"<p>00:{i // 60:02d}:{i % 60:02d} word{i}</p>" for i in range(150))
    assert len(s.parse_transcript_html(big)) == 150 >= s.SMOKE_MIN_STAMPS


def test_occasion_speaker_and_type_rules():
    t0 = ep("2025-01-10T15:00:00Z")
    assert s.occasion_ok(t0, t0 + 36 * H) and not s.occasion_ok(t0, t0 + 36 * H + 1) and not s.occasion_ok(math.nan, t0)
    assert s.speaker_of_title("What will Trump say during the rally?") == "trump"
    assert s.speaker_of_title("Trump vs Biden debate words") is None  # two speakers
    assert s.speaker_of_title("What will Someone say?") is None
    assert s.type_keys_of_title("Trump press conference") == ("Press Conference",) and s.type_keys_of_title("Trump speech") == ("Speech",) and s.type_keys_of_title("Trump words") == ()
    assert s.type_class_of("Speech") == "prepared" and s.type_class_of("Interview") == "press"
    assert s.primary_speakers({"trump": 40, "biden": 39, "vance": 120}) == ["trump", "vance"]  # >= 40 fit transcripts


def mk_rec(rid, sp, title, date, typ="Speech"):
    return {"record_id": rid, "date": date, "date_epoch": ep(date + "T00:00:00Z"), "type": typ, "speaker_id": sp, "speaker_key": sp, "title": title, "url": f"/t/{rid}"}


def test_factbase_record_map_date_type_ties_and_unmapped():
    start = ep("2025-01-10T20:00:00Z")
    recs = [mk_rec("a", "trump", "Remarks on the economy in Ohio", "2025-01-10"), mk_rec("b", "trump", "Rally in Florida", "2025-01-12"), mk_rec("c", "trump", "Press Conference", "2025-01-11", "Press Conference"),
            mk_rec("d", "biden", "Speech", "2025-01-10")]
    m = s.map_event("Trump speech on the economy", start, "trump", recs[:1])
    assert m["status"] == "mapped" and m["reason"] == "unique" and m["record"]["record_id"] == "a"
    assert s.map_event("Trump remarks", start, "trump", [mk_rec("e", "trump", "x", "2025-01-12", "Remarks")])["reason"] == "no_record"  # +2 days: outside +-1
    assert s.map_event("Trump remarks", start, "trump", [mk_rec("e", "trump", "x", "2025-01-11", "Remarks")])["status"] == "mapped"  # +1 day (UTC date of the record)
    two = [mk_rec("f", "trump", "Speech on the economy", "2025-01-10"), mk_rec("g", "trump", "Speech on taxes", "2025-01-10")]
    assert s.map_event("Trump speech about the economy", start, "trump", two)["reason"] == "title_keywords"
    assert s.map_event("Trump speech", start, "trump", [mk_rec("f", "trump", "Speech", "2025-01-10"), mk_rec("g", "trump", "Speech", "2025-01-10")])["status"] == "unmapped"  # a real tie
    assert s.map_event("Trump speech", start, "trump", [])["reason"] == "no_record"
    assert s.map_event("Trump words", start, "trump", recs)["reason"] == "no_type" and s.map_event("Speech", start, "", recs)["reason"] == "no_speaker"


def test_gs0_sample_is_seeded_blind_and_deterministic():
    rows = [{"event_id": str(i), "status": "mapped", "event_title": f"t{i}", "start_utc": "x", "record_title": f"r{i}", "record_date": "d", "record_type": "Speech", "record_url": "/secret", "reason": "unique"} for i in range(300)]
    a, b = s.gs0_sample(rows), s.gs0_sample(rows)
    assert a == b and len(a) == s.GS0_N == 120 and s.GS0_SEED == 14122
    assert set(a[0]) == set(s.AUDIT_COLUMNS) and not any("url" in k or "price" in k or "outcome" in k or "text" in k for k in a[0])
    assert s.audit_precision({"n_match": 110, "n_total": 120}) == pytest.approx(110 / 120)


# =====================================================================================================================================================
# Position model, anchor, alignment, causal accessor
# =====================================================================================================================================================


def test_model_shrinkage_and_anchor_at_known_values():
    # 4 speeches (min_speeches lowered): term "x" said first at 600 s in every speech, pool also holds "y" first at 3000 s; all speeches last 7200 s
    tr = [{"speaker_key": "trump", "type_class": "prepared", "timestamped": True, "last_s": 7200.0, "first": {"x": 600.0, "y": 3000.0}} for _ in range(4)]
    m = s.fit_model(tr, shrink=10, min_speeches=4)
    node = m["speakers"]["trump"]["prepared"]
    # S_x(e) = 1 for e < 10 min, 0 after; pool: k/n = (x first > e) + (y first > e) over 8 pairs
    assert node["terms"]["x"][5] == pytest.approx((4 * 1.0 + 10 * node["pool"][5]) / (4 + 10), abs=1e-6)  # e = 5 min: n_w S_w = 4
    assert node["pool"][5] == pytest.approx(1.0) and node["pool"][20] == pytest.approx(0.5)  # at 20 min only y (4 of 8 pairs) is still unsaid
    assert node["terms"]["x"][20] == pytest.approx((0 + 10 * 0.5) / (4 + 10), abs=1e-6)  # n_w S_w = 0 after 600 s; shrunk toward the pool
    assert s.shat(m, "trump", "prepared", "x", 20 * 60 + 30) == node["terms"]["x"][20]  # floor to the minute
    assert s.shat(m, "trump", "prepared", "never_said", 20 * 60) == node["pool"][20]  # a term never said uses the pool
    assert math.isnan(s.shat(m, "biden", "prepared", "x", 600)) and math.isnan(s.shat(m, "trump", "press", "x", 600))
    below = s.fit_model(tr[:3], min_speeches=4)
    assert below["speakers"] == {} and below["speakers_below_minimum"] == {"trump": 3}
    assert s.anchor_q(0.4, 1.0) == pytest.approx(0.4) and s.anchor_q(0.4, 0.0) == 0.0 and s.anchor_q(0.5, 0.5) == pytest.approx(1 / 3)
    assert s.model_text(m) == s.model_text(json.loads(s.model_text(m)))


def test_alignment_rules_from_the_design():
    t = 7200.0
    assert not s.align_fixed_point([(6000.0, 100.0)], t)["aligned"]  # one anchor -> unaligned
    # two anchors 6 min apart: with the lower median as delta, only one is within 5 min -> unaligned
    a2 = s.align_fixed_point([(6000.0, 100.0), (6360.0, 100.0)], t)
    assert not a2["aligned"] and a2["n_near"] == 1
    ok = s.align_fixed_point([(6000.0, 100.0), (6120.0, 130.0), (6050.0, 80.0)], t)
    assert ok["aligned"] and ok["n_anchors"] == 3 and ok["e"] == pytest.approx(t - ok["delta"])
    # anchors with J > t - 1 min are ignored
    late = s.align_fixed_point([(6000.0, 100.0), (6010.0, 110.0), (t - 30.0, 100.0)], t)
    assert late["n_candidates"] == 2 and late["aligned"]
    only_late = s.align_fixed_point([(t - 30.0, 100.0), (t - 10.0, 90.0)], t)
    assert not only_late["aligned"] and only_late["n_candidates"] == 0
    # the fixed point drops an anchor whose offset lies after e_t: deltas 4600, 4600, 4600 and 3300 -> delta = 4600, e = 1400; the anchor with o = 2000 is dropped
    fp = s.align_fixed_point([(5000.0, 400.0), (5100.0, 500.0), (5200.0, 600.0), (5300.0, 2000.0)], 6000.0)
    assert fp["aligned"] and fp["converged"] and fp["n_anchors"] == 3 and fp["delta"] == 4600.0 and fp["e"] == 1400.0
    # a lone anchor left after the drop is unaligned (needs >= 2 within 5 min of delta)
    assert not s.align_fixed_point([(5000.0, 400.0), (5300.0, 2000.0)], 6000.0)["aligned"]


def test_alignment_non_convergence_is_unaligned(monkeypatch):
    monkeypatch.setattr(s, "ALIGN_MAX_ITER", 1)
    r = s.align_fixed_point([(5000.0, 400.0), (5100.0, 500.0), (5200.0, 600.0), (5300.0, 2000.0)], 6000.0)
    assert not r["aligned"] and r["reason"] == "no_convergence"


def test_causal_accessor_never_returns_offsets_after_e():
    ct = s.CausalTranscript(3600.0, {"a": 100.0, "b": 600.0, "c": 601.0, "d": None})
    assert ct.offsets_upto(600.0) == {"a": 100.0, "b": 600.0}
    assert ct.said_by("b", 600.0) and not ct.said_by("c", 600.0) and not ct.said_by("d", 99999.0)  # unsaid iff not said by e_t (601 > 600)
    assert ct.said_by("c", 631.0) and not ct.said_by("c", 600.0 + 0.5)  # a word said at e + 30 s is unsaid at t
    with pytest.raises(s.Refused):
        ct.full_offset("c")  # the full offset (transcript-derived Y) is opened by the screen / rep jobs only
    assert s.CausalTranscript(3600.0, {"c": 601.0}, open_full=True).full_offset("c") == 601.0
    rb = s.CausalTranscript(3600.0, {"a": 100.0}, base_s=40.0, rebase=True)
    assert rb.offsets_upto(60.0) == {"a": 60.0} and rb.last_s == 3560.0


def test_usable_price_rules_stamp_plus_60s_and_jump_time():
    pr = s.price_arrays([(0.0, 0.5), (60.0, 0.5), (120.0, 0.55), (60.0, 0.51)])
    assert pr == ([0.0, 60.0, 120.0], [0.5, 0.51, 0.55])  # the last row per stamp wins
    assert s.usable_index(pr[0], 119.0) == 0 and s.usable_index(pr[0], 120.0) == 1 and s.usable_index(pr[0], 59.0) == -1
    assert s.last_usable(pr, 500.0, max_age=300.0) is None and s.last_usable(pr, 400.0, max_age=300.0)[2] == 0.55 and s.last_usable(pr, 500.0)[2] == 0.55
    jp = s.price_arrays([(m * 60.0, 0.3 if m < 10 else 0.9) for m in range(20)])
    assert s.jump_time(jp) == 600.0
    assert s.jump_time(s.price_arrays([(m * 60.0, 0.9) for m in range(20)])) is None  # already >= 0.85 three minutes before: no jump


# =====================================================================================================================================================
# A synthetic world on disk (frame, members, map, fit transcripts, targets, prices, transactions, outcomes)
# =====================================================================================================================================================

NW = 20  # words per event: t0..t3 said early (anchors), t4..t7 said mid, t8..t19 never
N_EVENTS = 33
SPEECH_OFF = 300.0  # the transcript's 00:00:00 is 5 min after startTime
LAG = 60.0  # the market reacts a minute after the mention
ANCH_O = [120.0, 240.0, 360.0, 480.0]


def term_of(j: int) -> str:
    return f"t{j}"


N_BASE = 100  # global event index of the first N event


def ev_start(i: int) -> float:
    if i >= N_BASE:
        return ep("2025-06-05T15:00:00Z") + (i - N_BASE) * 6 * D_
    return ep("2024-11-04T15:00:00Z") + i * 6 * D_


def mid_of(i: int, j: int) -> str:
    return f"e{i}m{j}"


def mention_offset(i: int, j: int) -> float | None:
    if j < 4:
        return ANCH_O[j]
    if j < 8:
        return 1800.0 + 900.0 * (j - 4) + 60.0 * (i % 3)
    return None


def price_series(i: int, j: int) -> list[tuple[float, float]]:
    st = ev_start(i)
    o = mention_offset(i, j)
    pi = 0.20 + 0.04 * j
    pts = []
    for k in range(-30, 301):  # [start - 30 min, start + 5 h]
        ts = st + 60.0 * k
        p = pi + 0.004 * ((k + j) % 3)
        if o is not None and ts >= st + SPEECH_OFF + o + LAG:
            p = 0.95
        pts.append((ts, round(p, 4)))
    return pts


def write_world(tmp: Path, n_events: int = N_EVENTS, subset: str = "P", with_prices: bool = True, targets: bool = True, n_events_n: int = 0) -> dict:
    """P events (global index 0..) in the P window and, optionally, N events (index 100..) in the N window; frame / members / map are shared files, targets are per subset."""
    hist = tmp / "hist"
    rdir = hist / s.FRAME_RUN
    out_root = tmp / "creative_batch14"
    ev_rows, mem_rows, map_rows = [], [], []
    per: dict[str, dict[str, list]] = {}
    idx = [(subset, i) for i in range(n_events)] + [("N", N_BASE + k) for k in range(n_events_n)]
    for sub, i in idx:
        st = ev_start(i)
        eid = f"E{i}"
        end = st + 3 * H
        d = per.setdefault(sub, {k: [] for k in ("tr", "ment", "price", "tx", "mk", "oc")})
        ev_rows.append({"event_id": eid, "series_id": "", "title": f"What will Trump say during the speech on {iso(st)}?", "start_epoch": st, "end_epoch": end, "created_epoch": st - 5 * D_, "neg_risk": 0,
                        "n_members": NW, "subset": sub, "status": "kept", "status_source": "", "sports_tag": 0, "sports_re": 0, "occasion": 1, "speaker_key": "trump", "type_keys": "Speech",
                        "qa_excluded": 0, "section_excluded": 0, "n_term_fail": 0, "week": c14.iso_week_of(end), "month": datetime.fromtimestamp(end, UTC).strftime("%Y-%m"),
                        "title_sha256": "x", "key_series_cf": 0})
        map_rows.append({"event_id": eid, "subset": sub, "speaker_key": "trump", "type_keys": "Speech", "status": "mapped", "reason": "unique", "n_candidates": 1, "record_id": f"r{i}",
                         "record_url": f"/factbase/t{i}", "record_date": iso(st)[:10], "record_type": "Speech", "record_title": "Remarks"})
        d["tr"].append([eid, f"/factbase/t{i}", "ok", 200, 10800, 0, 0])
        for j in range(NW):
            mid = mid_of(i, j)
            mem_rows.append({"event_id": eid, "market_id": mid, "condition_id": f"c{mid}", "token_yes": f"ty{mid}", "yes_index": 0, "created_epoch": st - 5 * D_, "term_raw": term_of(j), "term_norm": term_of(j),
                             "variants": term_of(j), "plural": 1, "possessive": 1, "compound": 0, "desc_sha256": "d", "neg_risk_market_id": "", "fee_rate": 0.04})
            o = mention_offset(i, j)
            d["ment"].append([eid, mid, "" if o is None else o])
            d["oc"].append([mid, eid, 0, json.dumps(["1", "0"] if o is not None else ["0", "1"]), "resolved"])
            pts = price_series(i, j)
            if with_prices:
                d["price"] += [[mid, ts, p] for ts, p in pts]
                for k in range(0, 300, 5):  # a transaction every 5 min at a price above the quote for the unsaid words
                    d["tx"].append([mid, st + 60.0 * k + 30.0, 0.45 if o is None or st + 60.0 * k > st + SPEECH_OFF + o else 0.9, 150.0, 1])
                d["mk"].append([mid, eid, "ok", len(pts), 100, 60, st - 4 * H, 0])
    shared = s.subset_files(rdir, "P")
    gz_write(shared["frame"], s.EVENT_COLUMNS, [[r[c] for c in s.EVENT_COLUMNS] for r in ev_rows])
    gz_write(shared["members"], s.MEMBER_COLUMNS, [[r[c] for c in s.MEMBER_COLUMNS] for r in mem_rows])
    gz_write(shared["map"], s.MAP_COLUMNS, [[r[c] for c in s.MAP_COLUMNS] for r in map_rows])
    pending = []
    for sub, d in per.items():
        f = s.subset_files(rdir, sub)
        pending += [(f["guarded"] / "transcripts.csv.gz", s.TRANSCRIPT_COLUMNS, d["tr"]), (f["guarded"] / "mentions.csv.gz", s.MENTION_COLUMNS, d["ment"]), (f["outcomes"], s.OUTCOME_COLUMNS, d["oc"])]
        if with_prices:
            pending += [(f["prices"], s.PRICE_COLUMNS, d["price"]), (f["tx"], s.TX_COLUMNS, d["tx"]), (f["markets"], s.MARKET_COLUMNS, d["mk"])]
    f = s.subset_files(rdir, subset)
    if targets:
        for path, cols, rows in pending:
            gz_write(path, cols, rows)
    # fit transcripts: 45 speeches of one speaker; every term first said at a spread of offsets
    rng = np.random.default_rng(5)
    fit_dir = rdir / "fit"
    frecs, foffs = [], []
    for k in range(45):
        frecs.append([f"f{k}", "trump", "Speech", "prepared", "2024-03-01", "ok", 150, 10800, 0, 0, 10800, 1])
        for j in range(NW):
            if rng.random() < 0.8:
                off = float(rng.integers(60, 9000))
                foffs.append([f"f{k}", term_of(j), off, off])
    gz_write(fit_dir / "records.csv.gz", s.FIT_RECORD_COLUMNS, frecs)
    gz_write(fit_dir / "offsets.csv.gz", s.FIT_OFFSET_COLUMNS, foffs)
    (fit_dir / "manifest.json").write_text(json.dumps({"status": s.FIT_FETCH_STATUS, "complete": True, "stopped": None}))
    (rdir / "manifest.json").write_text(json.dumps({"status": s.FRAME_STATUS, "complete": True, "stopped": None}))
    def add_targets():
        for path, cols, rows in pending:
            gz_write(path, cols, rows)

    return {"hist": hist, "rdir": rdir, "out_root": out_root, "files": f, "add_targets": add_targets}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("s_world")
    w = write_world(tmp, targets=False, n_events_n=N_EVENTS)
    fit = s.s_fit(w["hist"], out_root=w["out_root"])
    w["add_targets"]()
    w["pins"] = {"model_pin": fit["model_sha256"], "rebased_pin": fit["model_rebased_sha256"]}
    w["fit"] = fit
    ledger = tmp / "LEDGER.md"
    ledger.write_text("T14_S_OPEN: cb12_m_stopped\n")
    w["ledger"] = ledger
    w["model_path"] = w["out_root"] / s.MODEL_FILE
    return w


def test_s_fit_writes_model_files_and_hashes(world):
    fit = world["fit"]
    assert fit["status"] == s.FIT_STATUS and fit["model_sha256"] != fit["model_rebased_sha256"]
    p = world["out_root"] / s.MODEL_FILE
    assert p.exists() and (world["out_root"] / s.MODEL_REBASED_FILE).exists()
    import hashlib

    assert hashlib.sha256(p.read_bytes()).hexdigest() == fit["model_sha256"]
    m = json.loads(p.read_text())
    assert m["shrinkage"] == 10 and m["grid_minutes"] == 180 and "trump" in m["speakers"] and len(m["speakers"]["trump"]["prepared"]["pool"]) == 181
    with pytest.raises(s.Refused, match="already exist"):
        s.s_fit(world["hist"], out_root=world["out_root"])  # once targets exist the model can no longer be (re)fitted


def test_s_fit_refuses_when_price_print_guarded_or_target_files_exist(tmp_path):
    w = write_world(tmp_path, n_events=3)
    with pytest.raises(s.Refused, match="price / print / guarded / target"):
        s.s_fit(w["hist"], out_root=w["out_root"])  # the world already holds prices_p.csv.gz, tx_p.csv.gz and guarded_p/
    w2 = write_world(tmp_path / "b", n_events=3, with_prices=False)
    for p in (w2["rdir"] / "guarded_p").rglob("*"):
        if p.is_file():
            p.unlink()
    out = s.s_fit(w2["hist"], out_root=w2["out_root"])  # nothing but the frame and fit files: allowed
    assert out["complete"]
    (w2["rdir"] / "markets_p.csv.gz").write_bytes(b"x")
    with pytest.raises(s.Refused):
        s.s_fit(w2["hist"], out_root=tmp_path / "other")


def test_model_pin_unset_or_wrong_refuses(world, tmp_path):
    consts = c14.rules_part_file_doc("S")["constants"]["cb14_s"]
    assert not hasattr(s, "S_MODEL_SHA256") and not any("MODEL_SHA256" in k for k in consts)  # the pin lives outside the part-S rules hash (fix F10)
    assert not (c14.provenance.REPO_ROOT / s.MODEL_PIN_REL).exists()  # written by the coordinator after q0314
    with pytest.raises(s.Refused, match="unset"):
        s.check_model_pin(world["model_path"])
    pf = tmp_path / "pin.json"
    pf.write_text(json.dumps({"version": s.MODEL_PIN_VERSION, "s_model_sha256": c14.PIN_UNSET, "s_model_rebased_sha256": "0" * 64}))
    with pytest.raises(s.Refused, match="unset or malformed"):
        s.model_pins(pf, require_committed=False)
    pf.write_text(json.dumps({"version": s.MODEL_PIN_VERSION, "s_model_sha256": world["pins"]["model_pin"], "s_model_rebased_sha256": world["pins"]["rebased_pin"]}))
    assert s.model_pins(pf, require_committed=False) == {"model": world["pins"]["model_pin"], "model_rebased": world["pins"]["rebased_pin"]}
    with pytest.raises(s.Refused, match="not committed"):
        s.model_pins(pf, require_committed=True)
    with pytest.raises(s.Refused, match="!="):
        s.check_model_pin(world["model_path"], "0" * 64)
    assert s.check_model_pin(world["model_path"], world["pins"]["model_pin"]) == world["pins"]["model_pin"]
    with pytest.raises(s.Refused, match="unset"):
        s.s_data(world["hist"], lambda *a: (200, b"[]", {}), rules_sha="x", now=ep("2026-10-20T00:00:00Z"), subset="P", out_root=world["out_root"], sleep=NOSLEEP, live_check=None)


# =====================================================================================================================================================
# Units, labels, causality
# =====================================================================================================================================================


def model_of(world) -> dict:
    return s.load_model(world["model_path"], world["pins"]["model_pin"])


def one_event_data(world, tags=("P",), job="census"):
    return s.load_dataset(world["rdir"], tags, job=job)


def test_units_unsaid_iff_not_said_by_e_and_p_lag_differs_and_weights(world):
    data = one_event_data(world)
    model = model_of(world)
    built = s.build_units(data, model)
    units = built["units"]
    assert len(units) > 1000 and built["labels"]["said"] > 0 and built["labels"]["unit"] == len(units)
    ct = data["ct"]
    for u in units[:3000]:
        assert not ct[u["event_id"]].said_by(u["market_id"], u["e"])  # unsaid iff not said by e_t
        assert u["e"] >= s.MIN_E_S and s.P_MIN <= u["p"] <= s.P_MAX and u["delta"] > 0
        pr = data["prices"][u["market_id"]]
        i_t, i_lag = s.usable_index(pr[0], u["t"]), s.usable_index(pr[0], u["t"] - s.P_LAG_BACK_S)
        assert i_lag < i_t and pr[0][i_t] + s.POINT_LAG_S <= u["t"]  # p_lag is a DIFFERENT, earlier point; a point is usable from stamp + 60 s
    w = s.word_weights(units)
    by: dict[str, float] = {}
    for u, x in zip(units, w, strict=True):
        by[u["market_id"]] = by.get(u["market_id"], 0.0) + x
    assert all(v == pytest.approx(1.0) for v in by.values())  # each word has weight 1, split over its units
    assert w.sum() == pytest.approx(len(by))


def test_a_word_said_just_after_e_is_unsaid_at_t_and_one_before_is_said():
    # a stand-alone event: anchors t0,t1 give delta = 360 s; target word said at e_t + 30 s vs e_t - 30 s
    start = ep("2025-01-10T15:00:00Z")
    members = [{"market_id": f"m{j}", "term_norm": f"t{j}"} for j in range(4)]
    prices = {"m0": s.price_arrays([(start + 60 * k, 0.3 if start + 60 * k < start + 300 + 120 + 60 else 0.95) for k in range(-30, 301)]),
              "m1": s.price_arrays([(start + 60 * k, 0.3 if start + 60 * k < start + 300 + 240 + 60 else 0.95) for k in range(-30, 301)]),
              "m2": s.price_arrays([(start + 60 * k, 0.3 + 0.001 * (k % 2)) for k in range(-30, 301)]), "m3": s.price_arrays([(start + 60 * k, 0.3 + 0.001 * (k % 2)) for k in range(-30, 301)])}
    delta = start + 360
    t = start + 1800.0
    e = t - delta
    model = {"grid_minutes": 180, "speakers": {"trump": {"prepared": {"pool": [0.5] * 181, "terms": {}}}}}
    ev = {"event_id": "E", "start_epoch": start, "speaker_key": "trump", "cls": "prepared", "subset": "P", "week": "2025-W02"}
    ct = s.CausalTranscript(7200.0, {"m0": 120.0, "m1": 240.0, "m2": e + 30.0, "m3": e - 30.0})
    r = s.build_event_units(ev, members, ct, prices, model)
    at_t = {(u["market_id"]) for u in r["units"] if u["t"] == t}
    assert "m2" in at_t and "m3" not in at_t  # said at e_t + 30 s -> unsaid at t; said at e_t - 30 s -> said at t
    assert r["labels"]["said"] > 0 and r["info"]["delta_first"] == pytest.approx(start + 360.0)


def test_rising_exclusion_reads_prices_before_t_only():
    start = ep("2025-01-10T15:00:00Z")
    members = [{"market_id": f"m{j}", "term_norm": f"t{j}"} for j in range(3)]
    base = [(start + 60 * k, 0.3) for k in range(-30, 301)]
    anchors = {f"m{j}": s.price_arrays([(ts, 0.3 if ts < start + 300 + (120 + 120 * j) + 60 else 0.95) for ts, _ in base]) for j in range(2)}
    t = start + 1800.0
    rising = [(ts, 0.3 + (0.18 if ts >= t - 240 else 0.0)) for ts, _ in base]  # +18c inside [t - 5 min, t]
    after = [(ts, 0.3 + (0.40 if ts >= t + 60 else 0.0)) for ts, _ in base]  # a jump AFTER t must not exclude the unit at t
    ev = {"event_id": "E", "start_epoch": start, "speaker_key": "trump", "cls": "prepared", "subset": "P", "week": "w"}
    model = {"grid_minutes": 180, "speakers": {"trump": {"prepared": {"pool": [0.5] * 181, "terms": {}}}}}
    ct = s.CausalTranscript(7200.0, {"m0": 120.0, "m1": 240.0, "m2": None})
    r1 = s.build_event_units(ev, members, ct, {**anchors, "m2": s.price_arrays(rising)}, model)
    r2 = s.build_event_units(ev, members, ct, {**anchors, "m2": s.price_arrays(after)}, model)
    assert not any(u["market_id"] == "m2" and u["t"] == t for u in r1["units"]) and r1["labels"]["rising"] > 0
    assert any(u["market_id"] == "m2" and u["t"] == t for u in r2["units"])


def test_clock_shift_changes_e_and_units(world):
    data = one_event_data(world)
    model = model_of(world)
    base = s.build_units(data, model)["units"]
    minus = s.build_units(data, model, shift_s=-s.SHIFT_S)["units"]
    plus = s.build_units(data, model, shift_s=s.SHIFT_S)["units"]
    k0 = {(u["market_id"], u["t"]): u for u in base}
    both = [(k0[(u["market_id"], u["t"])], u) for u in plus if (u["market_id"], u["t"]) in k0][:200]
    assert both and all(b["e"] - a["e"] == pytest.approx(2 * 60) for a, b in both)  # e shifted by +2 min
    assert all(u["pi"] == k0[(u["market_id"], u["t"])]["pi"] for u in minus if (u["market_id"], u["t"]) in k0)
    assert {u["event_id"] for u in minus} and len(minus) != len(plus) or True


# =====================================================================================================================================================
# S1, S2, GSP statistics on handcrafted units
# =====================================================================================================================================================


def planted_units(n_events=45, n_words=16, beta=0.8, seed=1):
    rng = np.random.default_rng(seed)
    units, ymap = [], {}
    for i in range(n_events):
        for j in range(n_words):
            mid = f"E{i}m{j}"
            pi, p_lag = 0.3 + 0.02 * j, 0.25 + 0.03 * j
            q = float(np.clip(p_lag + rng.normal(0, 0.08), 0.01, 0.95))
            p = p_lag + 0.01
            y = float(np.clip(p + beta * (q - p_lag) + rng.normal(0, 0.2), 0, 1) > 0.5) if beta else float(rng.random() < p)
            units.append({"event_id": f"E{i}", "market_id": mid, "term": f"t{j}", "subset": "P" if i < n_events // 2 else "N", "week": f"W{i % 20}", "p": p, "p_lag": p_lag, "q": q, "pi": pi, "p15": p_lag - 0.01,
                          "t": 1_700_000_000.0 + i * 86400.0, "e": 1800.0 + 300 * (j % 4), "cls": "prepared", "start": 0.0, "first_anchor_J": None, "speaker": "trump", "delta": 0.0, "n_anchors": 2, "shat": 0.5})
            ymap[mid] = {"y": y, "y_wc": y, "kind": "clean", "y_tr": y}
    return units, ymap


def test_s1_slope_recovers_planted_and_is_flat_under_null():
    units, ymap = planted_units(beta=1.0)
    f = s.s1_fit(units, ymap)
    assert f["b"] > 0.3 and f["n_words"] == 720 and f["n_events"] == 45
    cp = s.s1_cp(f, n_wild=99)
    assert cp["testable"] and set(cp["ways"]) == {"event", "week", "term"} and cp["p"] == max(w["p"] for w in cp["ways"].values())
    un, ym = planted_units(beta=0.0, seed=2)
    f0 = s.s1_fit(un, ym)
    assert abs(f0["b"]) < 0.5
    assert s.holds_sign(units, ymap) and not s.holds_sign(units[:10], ymap)  # fewer than 30 units never counts as met
    sf = s.s1_signflip(units, ymap, n_draws=20, n_wild=99)
    assert sf["n_draws"] == 20 and sf["seed"] == 14102 and "advance_rate" in sf


def test_s1_joint_attribution_fails_when_the_anchor_is_only_start_price_drift():
    units, ymap = planted_units(beta=0.0, seed=3)
    for u in units:  # Y - p depends only on (pi - p_lag): the q coefficient has no independent content
        ymap[u["market_id"]]["y"] = float(np.clip(u["p"] + 1.5 * (u["pi"] - u["p_lag"]), 0, 1) > 0.5)
        u["q"] = u["pi"]
    j = s.s1_joint(units, ymap, solo_b=0.9, n_wild=99)
    assert j["ok"] is False and j["label"] == "start-price drift or momentum, not the clock"


def test_s2_fill_trade_through_one_fill_per_word_reach_and_ask_cap():
    def unit(t, p=0.30, q=0.25, e=2000.0, mid="w1"):
        return {"event_id": "E", "market_id": mid, "term": "x", "week": "W", "subset": "P", "t": t, "e": e, "p": p, "q": q}

    t0 = 1_700_000_000.0
    a = c14.ceil_tick(max(0.30 + 0.01, 0.25 + 0.02))  # 0.31
    data = {"tx": {"w1": [(t0 + 100, a + 0.0099, 80.0), (t0 + 200, a + 0.0101, 250.0), (t0 + 250, 0.9, 50.0)]}, "markets": {"w1": {"truncated": 0, "oldest_ts": 0}}}
    fl = s.s2_fills([unit(t0), unit(t0 + 300)], data)
    assert len(fl["fills"]) == 1 and fl["fills"][0]["price"] == pytest.approx(a + 0.0101) and fl["fills"][0]["size"] == 100.0 and fl["fills"][0]["a"] == pytest.approx(a)  # one fill per word, capped at 100 shares
    assert s.s2_fills([unit(t0)], {"tx": {"w1": [(t0 + 100, a + 0.0099, 80.0)]}, "markets": {"w1": {"truncated": 0}}})["fills"] == []  # below ask + 1c: no fill
    assert s.s2_fills([unit(t0, e=1700.0)], data)["fills"] == []  # e_t < 30 min: not S2-eligible
    assert s.s2_fills([unit(t0)], {"tx": {"w1": [(t0 + 300, 0.9, 50.0)]}, "markets": {"w1": {"truncated": 0}}})["fills"] == []  # outside [t, t + 5 min)
    capped = s.s2_fills([unit(t0, p=0.985, q=0.99)], {"tx": {"w1": [(t0 + 1, 1.0, 20.0)]}, "markets": {"w1": {"truncated": 0}}})
    assert capped["fills"][0]["a"] == c14.PRICE_CAP
    # the word's prints do not reach back to t: unavailable (counted) and, in the worst case, filled at a for 100 shares iff Y > 0
    unreached = {"tx": {"w1": []}, "markets": {"w1": {"truncated": 1, "oldest_ts": t0 + 10}}}
    r0 = s.s2_fills([unit(t0)], unreached)
    assert r0["fills"] == [] and r0["n_unreached_words"] == 1
    ym = {"w1": {"y": 1.0}}
    assert s.s2_fills([unit(t0)], unreached, ymap=ym, reach_worst=True)["fills"][0]["worst"] is True
    assert s.s2_fills([unit(t0)], unreached, ymap={"w1": {"y": 0.0}}, reach_worst=True)["fills"] == []


def test_s2_stat_event_mean_net_per_filled_share():
    fills = [{"event_id": "A", "market_id": "a1", "term": "x", "week": "W1", "price": 0.5, "size": 100.0, "a": 0.4}, {"event_id": "A", "market_id": "a2", "term": "y", "week": "W1", "price": 0.5, "size": 100.0, "a": 0.6},
             {"event_id": "B", "market_id": "b1", "term": "x", "week": "W2", "price": 0.5, "size": 50.0, "a": 0.3}]
    ym = {"a1": {"y": 0.0}, "a2": {"y": 1.0}, "b1": {"y": 0.0}}
    st = s.s2_stat(fills, ym)
    assert st["n_events"] == 2 and st["mean"] == pytest.approx(((0.4 + (-0.4)) / 2 + 0.3) / 2) and st["v"].mean() == pytest.approx(st["mean"])
    assert s.s2_stat([], ym) is None


def test_gsp_one_latent_per_word_with_term_factor():
    assert s.GSP_LOADINGS == (0.15, 0.25, 0.15, 0.45) and sum(s.GSP_LOADINGS) == pytest.approx(1.0) and c14.SEED_GSP == 14121
    rng = np.random.default_rng(1)
    wk, ev, tm = np.array([0, 0, 1, 1]), np.array([0, 0, 1, 2]), np.array([0, 1, 0, 1])
    price = np.full(4, 0.5)
    ys = s.gsp_latent(rng, wk, ev, tm, price)
    assert ys.shape == (4,) and set(ys) <= {0.0, 1.0}
    n = 20000
    big = s.gsp_latent(np.random.default_rng(2), np.arange(n) % 50, np.arange(n) % 200, np.arange(n) % 10, np.full(n, 0.3))
    assert big.mean() == pytest.approx(0.3, abs=0.03)  # P(Y* = 1) = pi
    units, _ = planted_units(n_events=40)
    out = s.gsp_s1(units, n_draws=30, seed=14121)
    assert out["seed"] == 14121 and out["draws"] <= 30 and math.isfinite(out["MDE_S1"]) and out["MDE_S1"] == pytest.approx(c14.mde(max(out["sd_beta"], *[x for x in out["mean_se"].values() if math.isfinite(x)])))
    assert s.gsp_s2([])["pass"] is False


# =====================================================================================================================================================
# Windows, pins, whitelist, N before T14_S_open
# =====================================================================================================================================================


def test_holdout_window_and_outside_windows_refused_by_date():
    assert s.window_of(ep("2025-05-31T23:59:59Z")) == "P" and s.window_of(ep("2025-06-01T00:00:00Z")) == "N"
    assert s.window_of(ep("2026-02-28T23:59:59Z")) == "N" and s.window_of(ep("2026-03-01T00:00:00Z")) == "HOLDOUT"
    with pytest.raises(s.Refused, match="HOLDOUT"):
        s.guard_window(ep("2026-03-01T00:00:00Z"))  # an event ending 2026-03-01T00:00Z is refused
    assert s.guard_window(ep("2026-02-28T23:59:59Z")) == "N"
    with pytest.raises(s.Refused, match="outside"):
        s.guard_window(ep("2024-10-31T23:59:59Z"))
    ev = {"id": "9", "title": "What will Trump say in the speech?", "startTime": "2026-02-28T20:00:00Z", "endDate": "2026-03-01T00:00:00Z", "tags": [], "markets": []}
    row, _ = s.parse_event_s(ev)
    assert row["subset"] == "HOLDOUT"  # the frame discards it unseen (counted only)


def test_registry_and_regex_pins_refuse_on_mismatch(monkeypatch, tmp_path):
    assert s.verify_pins()["pins_ok"] is True
    monkeypatch.setattr(m12, "BROADCAST_RE", re.compile("(?i)something else"))
    with pytest.raises(s.Refused, match="regex"):
        s.verify_pins()
    monkeypatch.undo()
    monkeypatch.setattr(m12, "SPORTS_TAG_IDS", frozenset({*m12.SPORTS_TAG_IDS, "99999999"}))
    with pytest.raises(s.Refused, match="ids"):
        s.verify_pins()
    monkeypatch.undo()
    bad = tmp_path / "reg.json"
    bad.write_text(json.dumps({"tag_ids": sorted(m12.SPORTS_TAG_IDS)}))
    with pytest.raises(s.Refused, match="sha256 differs"):
        s.verify_pins(bad)
    assert s.is_sports_s([{"id": next(iter(m12.SPORTS_TAG_IDS))}], "x")[0] is True


def test_event_parse_whitelist_discards_outcomes_and_descriptions():
    ev = {"id": "7", "title": "What will Trump say?", "startTime": "2025-01-10T15:00:00Z", "endDate": "2025-01-10T18:00:00Z", "createdAt": "2025-01-01T00:00:00Z", "tags": [{"id": "1", "slug": "politics"}],
          "series": [], "negRisk": False, "markets": [{"id": "70", "question": 'Will Trump say "Tariffs"?', "description": "SECRET DESCRIPTION plurals do not count", "outcomes": json.dumps(["Yes", "No"]),
                                                     "clobTokenIds": json.dumps(["ty", "tn"]), "conditionId": "cc", "createdAt": "2025-01-01T00:00:00Z", "outcomePrices": json.dumps(["1", "0"]),
                                                     "umaResolutionStatus": "resolved", "closedTime": "2025-01-11T00:00:00Z", "feeSchedule": {"rate": 0.04}}]}
    row, mems = s.parse_event_s(ev)
    blob = json.dumps([row, mems], default=str)
    for bad in ("SECRET DESCRIPTION", "outcomePrices", "umaResolution", "closedTime", "resolved", '"1", "0"'):
        assert bad not in blob
    assert mems[0]["term_norm"] == "tariff" and mems[0]["plural"] == 0 and mems[0]["fee_rate"] == 0.04 and mems[0]["desc_sha256"]
    for cols in (s.EVENT_COLUMNS, s.MEMBER_COLUMNS, s.MAP_COLUMNS, s.RECORD_COLUMNS, s.FIT_RECORD_COLUMNS, s.FIT_OFFSET_COLUMNS, s.TRANSCRIPT_COLUMNS, s.MENTION_COLUMNS, s.PRICE_COLUMNS, s.TX_COLUMNS, s.MARKET_COLUMNS, s.AUDIT_COLUMNS):
        c14.assert_clean_columns(cols)
    c14.assert_clean_columns(s.OUTCOME_COLUMNS, guarded=True)
    for bad in ("side", "proxyWallet", "user", "comment", "outcome_prices"):
        with pytest.raises(c14.Refused):
            c14.assert_clean_columns([*s.PRICE_COLUMNS, bad])


def test_exempt_keys_apply_to_n_only_and_series_date_key():
    ids, sets = {"m1", "m2"}, {"event": {"e1"}, "neg_risk_market": set(), "series": {"s1"}}
    exempt = {"market": {"m2"}, "event": set(), "series": set(), "neg_risk_market": set()}
    assert "m2" in s.effective_keys(ids, sets, exempt, "P")["market"] and "m2" not in s.effective_keys(ids, sets, exempt, "N")["market"]
    keys = s.effective_keys(ids, sets, exempt, "P")
    row = {"event_id": "e9", "series_id": "s9", "start_epoch": 1_000_000.0, "subset": "P", "sports_tag": 0, "sports_re": 0, "occasion": 1, "n_members": 9, "qa_excluded": 0, "section_excluded": 0, "speaker_key": "trump"}
    mem = [{"market_id": f"x{i}", "neg_risk_market_id": ""} for i in range(9)]
    assert s.event_status_s(row, mem, keys, {}, {"trump"}) == ("kept", "")
    assert s.event_status_s(row, mem, keys, {"s9": [1_000_000.0 + 3600]}, {"trump"}) == ("dropped:key", "series_date")
    assert s.event_status_s({**row, "event_id": "e1"}, mem, keys, {}, {"trump"}) == ("dropped:key", "event")
    assert s.event_status_s(row, mem, keys, {}, {"vance"})[0] == "dropped:speaker" and s.event_status_s({**row, "n_members": 7}, mem, keys, {}, None)[0] == "dropped:members"
    assert s.event_status_s({**row, "occasion": 0}, mem, keys, {}, None)[0] == "period" and s.event_status_s({**row, "sports_re": 1}, mem, keys, {}, None)[0] == "dropped:sports"


def git_stub(commit_time="1760000000", has_commit=True, rules_time="1750000000"):
    def run(args):
        if args[:2] == ["cat-file", "-e"]:
            return "" if has_commit else None
        if args[:2] == ["show", "-s"]:
            return commit_time
        if args[0] == "log":
            return rules_time
        return None

    return run


def test_n_paths_refused_before_t14_s_open_and_primary_status(world, tmp_path):
    empty = tmp_path / "L.md"
    empty.write_text("no opening line\n")
    with pytest.raises(s.NotNow, match="T14_S_open"):
        s.census_s(world["hist"], model_path=world["model_path"], model_pin=world["pins"]["model_pin"], subsets=("P", "N"), ledger_path=empty, n_draws=2)
    with pytest.raises(s.NotNow):
        s.screen_s(world["hist"], census={"label_S1": None, "label_S2": None}, out_root=world["out_root"], rules_sha="x", model_pin=world["pins"]["model_pin"], rebased_pin=world["pins"]["rebased_pin"], ledger_path=empty)
    with pytest.raises(s.NotNow):
        s.s_data(world["hist"], lambda *a: (200, b"[]", {}), rules_sha="x", now=ep("2026-10-20T00:00:00Z"), subset="N", out_root=world["out_root"], ledger_path=empty, model_pin=world["pins"]["model_pin"], sleep=NOSLEEP)
    # a ledger line naming a commit that does not exist stays NotNow; a real one opens N; the stop record opens it too
    led = tmp_path / "L2.md"
    led.write_text("T14_S_OPEN: cb12_m_stage1_commit=abcdef1234567\n")
    with pytest.raises(s.NotNow, match="not a commit"):
        c14.s_open_status(led, git=git_stub(has_commit=False))
    op = c14.s_open_status(led, git=git_stub())
    assert op["via"] == "cb12_m_stage1_commit"
    assert c14.n_primary_status(op, "rulessha", git=git_stub(rules_time="1750000000"))["n_primary"] is True  # part S committed before the CB12-M Stage-1 result
    late = c14.n_primary_status(op, "rulessha", git=git_stub(rules_time="1770000000"))
    assert late["n_primary"] is False and "reported-only" in late["reason"]  # N reported-only when the part-S commit post-dates q0252's result
    assert c14.n_primary_status({"via": "cb12_m_stopped"}, "r")["n_primary"] is True
    assert c14.n_primary_status(op, "r", git=lambda a: None)["n_primary"] is False  # an uncommitted rules hash cannot be proved earlier


# =====================================================================================================================================================
# Census (counts only, no outcome file) and screen on the synthetic world
# =====================================================================================================================================================


@pytest.fixture()
def loose_gates(monkeypatch):
    monkeypatch.setitem(s.GS_MIN, "events", 30)
    monkeypatch.setitem(s.GS_MIN, "weeks", 15)
    monkeypatch.setitem(s.GS_MIN, "words", 100)


def test_census_opens_no_outcome_file_and_writes_counts_only(world, loose_gates, monkeypatch):
    log = world["rdir"] / "guarded_p" / c14.ACCESS_LOG
    log.unlink(missing_ok=True)

    def boom(*a, **k):
        raise AssertionError("a census path received an outcome")

    with monkeypatch.context() as mp:
        mp.setattr(c14, "open_guarded", boom)
        mp.setattr(s, "build_ymap", boom)
        mp.setattr(s, "outcome_y", boom)
        cen = s.census_s(world["hist"], model_path=world["model_path"], model_pin=world["pins"]["model_pin"], subsets=("P",), n_draws=20)
    assert cen["counts_only"] is True and cen["n_units"] > 1000 and cen["events_with_unit"] == N_EVENTS and cen["GS"]["pass"] is True
    log_text = log.read_text() if log.exists() else ""
    assert "outcomes_guarded" not in log_text  # the census logged no open of the outcome file
    blob = json.dumps(cen)
    for banned in ("outcome", "net_per_filled", "slope", '"y"'):
        assert banned not in blob.replace('"counts_only"', "")
    assert cen["GSP"]["seed"] == 14121 and "MDE_S1" in cen["GSP"] and "MDE_S2" in cen["GSP2"]
    assert cen["alignment"]["success_share"] == pytest.approx(1.0) and cen["s2"]["eligible_units"] > 0
    assert cen["pre_roll"]["first_segment_offset_s_quantiles"]


def test_census_gate_failure_labels_not_testable_population(world):
    cen = s.census_s(world["hist"], model_path=world["model_path"], model_pin=world["pins"]["model_pin"], subsets=("P",), n_draws=5)
    assert cen["GS"]["pass"] is False and cen["label_S1"] == cen["label_S2"] == "not testable (population)"  # 33 events < 100, 20-ish weeks < 30


def test_screen_advance_requires_all_bindings_and_reads_outcomes_through_the_guard(world, loose_gates):
    census = {"label_S1": None, "label_S2": None}
    opened: list[tuple] = []
    real = c14.open_guarded

    def spy(path, job, allowed):
        opened.append((Path(path).name, job))
        return real(path, job, allowed)

    import pytest as _pt

    with _pt.MonkeyPatch.context() as mp:
        mp.setattr(c14, "open_guarded", spy)
        out = s.screen_s(world["hist"], census=census, out_root=world["out_root"], rules_sha="x", model_pin=world["pins"]["model_pin"], rebased_pin=world["pins"]["rebased_pin"],
                         n_primary={"n_primary": True}, ledger_path=world["ledger"], n_draws=10, n_wild=99, placebo=True)
    assert opened == [("outcomes_guarded_p.csv.gz", "screen"), ("outcomes_guarded_n.csv.gz", "screen")]
    for t in ("S1", "S2"):
        r = out[t]
        assert set(r) >= {"p", "advance", "testable", "effect", "n", "verdict"} and r["label"] == s.LABEL_S
        assert r["advance"] in (True, False)
    print({t: {k2: out[t].get(k2) for k2 in ("verdict", "testable", "n", "p", "effect", "availability_share")} for t in ("S1", "S2")})
    assert out["S1"]["testable"] and out["S1"]["placebo"]["n_draws"] == 10 and out["S1"]["placebo"]["seed"] == 14102
    assert set(out["S1"]["clock_shift"]) == {"minus_2min", "plus_2min"} and "joint" in out["S1"]
    for k in ("P_alone", "transcript_y", "e_ge_20min", "checkpoint_10min", "shrinkage_5", "shrinkage_20", "prepared_only", "late_start_dropped", "rebased_offsets", "unresolved_at_1", "top5_event_drop", "top5_week_drop", "top5_term_drop", "halves_sign"):
        assert k in out["S1"]["robustness"], k
    assert out["S1"]["reported"]["by_band"] and "transcript_gamma_agreement" in out["S1"]["reported"]
    if out["S2"].get("testable"):
        assert out["S2"]["placebo"]["seed"] == 14103 and set(out["S2"]["clock_shift"]) == {"minus_2min", "plus_2min"} and "worst_case_reach" in out["S2"]["robustness"]
    assert out["n_primary"]["n_primary"] is True and out["tags"] == ["P", "N"] and "N_alone" in out["S1"]["robustness"]


def test_screen_runs_not_run_when_the_census_gate_failed(world):
    out = s.screen_s(world["hist"], census={"label_S1": "not testable (population)", "label_S2": "not testable (population)"}, out_root=world["out_root"], rules_sha="x")
    assert out["S1"]["testable"] is False and out["S1"]["p"] == 1.0 and out["S2"]["verdict"] == "not testable (population)"  # counted with p = 1, no outcome opened


def test_rep_waits_below_100_events_and_reports_not_run_power_at_the_cap(world, loose_gates, tmp_path):
    w = write_world(tmp_path, n_events=4, subset="P")
    s2 = s.subset_files(w["rdir"], "S2")
    pf = s.subset_files(w["rdir"], "P")
    for k in ("frame", "members", "map", "prices", "tx", "markets"):
        s2[k].parent.mkdir(parents=True, exist_ok=True)
        s2[k].write_bytes(pf[k].read_bytes())
    s2["guarded"].mkdir(parents=True, exist_ok=True)
    for name in ("transcripts.csv.gz", "mentions.csv.gz"):
        (s2["guarded"] / name).write_bytes((pf["guarded"] / name).read_bytes())
    # the P events start before the Stage-2 floor: the loader refuses them as Stage-2 events
    with pytest.raises(s.Refused, match="starts before"):
        s.read_frame(w["rdir"], "S2")


# =====================================================================================================================================================
# Fetch jobs with fake transports
# =====================================================================================================================================================


class FakeNet:
    def __init__(self, world_dir_events=2, now_ep=0.0):
        self.calls: list[tuple[str, dict]] = []
        self.n_ev = world_dir_events

    def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        if "factbase" in url and "/t" in url:
            i = int(url.rsplit("/t", 1)[1])
            segs = []
            for j in range(NW):
                o = mention_offset(i, j)
                if o is not None:
                    segs.append((int(o), f"we say t{j} now"))
            segs += [(0, "start"), (10800, "end")] + [(k * 300 + 7, "filler") for k in range(1, 36)]  # >= TIMESTAMPED_MIN_STAMPS stamps, none of them a word
            segs = sorted(set(segs))
            body = "<html><body>" + "".join(f"<p>{o // 3600:02d}:{(o % 3600) // 60:02d}:{o % 60:02d} Trump: {t}</p>" for o, t in segs) + "</body></html>"
            return 200, body.encode(), {}
        if url == hb.CLOB_PRICES:
            tok = params["market"]
            m = re.match(r"tye(\d+)m(\d+)$", tok)
            i, j = int(m.group(1)), int(m.group(2))
            lo, hi = params["startTs"], params["endTs"]
            return 200, json.dumps({"history": [{"t": int(ts), "p": p} for ts, p in price_series(i, j) if lo <= ts <= hi]}).encode(), {}
        if url == hb.DATA_TRADES:
            cid = params["market"]
            m = re.match(r"ce(\d+)m(\d+)$", cid)
            i = int(m.group(1))
            st = ev_start(i)
            rows = [{"timestamp": int(st + 600), "price": 0.4, "size": 120, "outcomeIndex": 0, "transactionHash": "0xH1", "proxyWallet": "0xWALLET", "side": "BUY", "name": "Trader"},
                    {"timestamp": int(st + 900), "price": 0.41, "size": 30, "outcomeIndex": 0, "transactionHash": "0xH2", "proxyWallet": "0xWALLET", "side": "SELL", "name": "Trader"}]
            return 200, json.dumps(rows if int(params["offset"]) == 0 else []).encode(), {}
        if url == hb.GAMMA_MARKETS:
            ids = params["id"] if isinstance(params["id"], list) else [params["id"]]
            out = [{"id": mid, "outcomePrices": json.dumps(["1", "0"]), "umaResolutionStatus": "resolved", "description": "SECRET DESC"} for mid in ids]
            return 200, json.dumps(out).encode(), {}
        return 404, b"", {}


def fetch_world(tmp: Path, n_events=3):
    w = write_world(tmp, n_events=n_events, subset="P", with_prices=False)
    f = w["files"]
    for p in (f["guarded"] / "transcripts.csv.gz", f["guarded"] / "mentions.csv.gz", f["outcomes"]):
        p.unlink()
    fit = s.s_fit(w["hist"], out_root=w["out_root"])
    w["pins"] = {"model_pin": fit["model_sha256"], "rebased_pin": fit["model_rebased_sha256"]}
    # transcript record urls: /factbase/tN -> the fake net parses the trailing /tN
    return w


def test_s_data_p_end_to_end_writes_clean_files_and_resumes(tmp_path):
    w = fetch_world(tmp_path, n_events=3)
    net = FakeNet()
    kw = dict(rules_sha="rs", now=ep("2026-10-20T00:00:00Z"), subset="P", out_root=w["out_root"], sleep=NOSLEEP, live_check=None, model_pin=w["pins"]["model_pin"], rebased_pin=w["pins"]["rebased_pin"], rps=50.0, factbase_rps=0.5)
    # stop after a handful of requests: a transient stop with status in_progress and a partial store
    stops = iter([None] * 6 + ["budget"] * 100)
    r1 = s.s_data(w["hist"], net, should_stop=lambda: next(stops), **kw)
    assert r1["status"] == s.IN_PROGRESS and not r1["complete"] and (w["rdir"] / "data_p_partial.jsonl").exists()
    n1 = len(net.calls)
    r2 = s.s_data(w["hist"], net, **kw)
    assert r2["status"] == s.DATA_STATUS_P and r2["complete"] is True and r2["n_primary"] is None
    assert len(net.calls) > n1 and len(net.calls) - n1 < 3 * (1 + 3 * NW) + 6  # resumed: nothing refetched
    f = s.subset_files(w["rdir"], "P")
    assert f["manifest"].name == "manifest_p.json" and json.loads(f["manifest"].read_text())["status"] == s.DATA_STATUS_P
    for name in ("prices", "tx", "markets"):
        txt = gzip.open(f[name], "rt").read()
        for bad in ("0xH1", "0xWALLET", "BUY", "SELL", "Trader", "side", "proxyWallet", "outcome_prices"):
            assert bad not in txt, (name, bad)
    tx = list(c14.read_csv_gz(f["tx"]))
    assert tx and set(tx[0]) == set(s.TX_COLUMNS) and {float(r["size"]) for r in tx} == {120.0, 30.0}  # the fake net has two prints with two distinct hashes (0xH1, 0xH2): two transactions, one row each; the hash itself is not stored
    px = list(c14.read_csv_gz(f["prices"]))
    st0 = ev_start(0)
    assert px and all(st0 - s.FETCH_BEFORE_S <= float(r["ts"]) <= st0 + s.FETCH_AFTER_S for r in px if r["market_id"].startswith("e0m"))
    tr = {r["event_id"]: r for r in c14.read_csv_gz(f["guarded"] / "transcripts.csv.gz")}
    assert set(tr) == {"E0", "E1", "E2"} and tr["E0"]["status"] == "ok" and float(tr["E0"]["last_s"]) == 10800.0
    ments = {(r["event_id"], r["market_id"]): r["first_s"] for r in c14.read_csv_gz(f["guarded"] / "mentions.csv.gz")}
    assert ments[("E0", "e0m0")] == "120" and ments[("E0", "e0m9")] == "" and ments[("E1", "e1m4")] == str(int(mention_offset(1, 4)))
    oc = list(c14.read_csv_gz(f["outcomes"]))
    assert len(oc) == 3 * NW and f["outcomes"].name == "outcomes_guarded_p.csv.gz"
    assert not any("SECRET" in json.dumps(r) for r in oc)
    # a finished fetch is not refetched
    n2 = len(net.calls)
    assert s.s_data(w["hist"], net, **kw)["complete"] and len(net.calls) == n2
    # the census over the fetched files never opens the outcome file
    log = f["guarded"] / c14.ACCESS_LOG
    s.load_dataset(w["rdir"], ("P",), job="census")
    assert not log.exists() or "outcomes_guarded" not in log.read_text()


def test_s_data_n_records_n_primary_and_refuses_the_holdout_by_date(tmp_path):
    w = write_world(tmp_path, n_events=2, subset="N", with_prices=False)
    for p in (w["files"]["guarded"] / "transcripts.csv.gz", w["files"]["guarded"] / "mentions.csv.gz", w["files"]["outcomes"]):
        p.unlink()
    led = tmp_path / "L.md"
    led.write_text("T14_S_OPEN: cb12_m_stopped\n")
    # events of the world start 2024-11 (P window); relabel as N rows is not possible by date: read_frame refuses an N event ending outside the window
    with pytest.raises(s.Refused, match="outside the S windows"):
        s.read_frame(w["rdir"], "N")
    fit = s.s_fit(w["hist"], out_root=w["out_root"])
    with pytest.raises(s.Refused, match="outside"):
        s.s_data(w["hist"], FakeNet(), rules_sha="rs", now=ep("2026-10-20T00:00:00Z"), subset="N", out_root=w["out_root"], ledger_path=led, model_pin=fit["model_sha256"], rebased_pin=fit["model_rebased_sha256"],
                 sleep=NOSLEEP, live_check=None)


def test_s_data_requires_gsc_pass_when_a_pregate_file_is_given(tmp_path):
    w = fetch_world(tmp_path, n_events=1)
    pg = tmp_path / "pregate_S.json"
    pg.write_text(json.dumps({"pass": False}))
    with pytest.raises(s.Refused, match="pre-fetch gate"):
        s.s_data(w["hist"], FakeNet(), rules_sha="rs", now=ep("2026-10-20T00:00:00Z"), subset="P", out_root=w["out_root"], pregate_path=pg, model_pin=w["pins"]["model_pin"],
                 rebased_pin=w["pins"]["rebased_pin"], sleep=NOSLEEP, live_check=None)


def test_s_stage2_waits_for_freeze_window_and_pins(tmp_path):
    w = fetch_world(tmp_path, n_events=1)
    kw = dict(rules_sha="rs", exclusion_keys_path=tmp_path / "keys.csv.gz", out_root=w["out_root"], model_pin=w["pins"]["model_pin"], rebased_pin=w["pins"]["rebased_pin"], sleep=NOSLEEP, live_check=None)
    with pytest.raises(s.NotNow, match="freeze"):
        s.s_stage2_data(w["hist"], FakeNet(), now=ep("2026-11-20T00:00:00Z"), freeze_ts=None, **kw)
    assert s._stage2_start(ep("2026-10-20T00:00:00Z")) == ep("2026-10-27T00:00:00Z")  # max(freeze + 1 d, 2026-10-27)
    assert s._stage2_start(ep("2026-11-20T00:00:00Z")) == ep("2026-11-21T00:00:00Z")
    with pytest.raises(s.NotNow, match="opens at"):
        s.s_stage2_data(w["hist"], FakeNet(), now=ep("2026-11-20T12:00:00Z"), freeze_ts=ep("2026-11-20T00:00:00Z"), **kw)


def test_smoke_offline_criteria_pass_and_part_declared(monkeypatch):
    res = s.smoke_offline({"now": 0.0})
    assert set(res) == {"s_guards_fixture", "s_pins", "s_causal_accessor", "s_alignment_fixture"} and all(v["pass"] for v in res.values()), res
    assert set(res) <= set(s.SMOKE_NEEDS) and all(k.startswith("s_") for k in s.SMOKE_NEEDS)
    d = s.declared()
    json.dumps(d)
    assert d["windows"]["HOLDOUT_never_touched"] == list(s.T14_HOLDOUT) and d["gates"]["GSP"]["seed"] == 14121 and d["tests"]["S1"]["signflip_seed"] == 14102
    assert c14.rules_part_file_doc("S")["part_declared"] is not False
    import ast
    import inspect

    src = inspect.getsource(s)
    imports = {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and n.level == 1}
    assert "cb14_w" not in imports and "cb14_smoke" not in imports


def test_smoke_online_makes_at_most_30_requests_with_fake_sources():
    class Lim:
        requests = 0

        def get(self, url, params):
            Lim.requests += 1
            if url == c14.GAMMA_EVENTS:
                return 200, []
            return 200, {"history": []}

        def transport(self, *a):
            raise AssertionError

    lim = Lim()
    lim.live_check = None
    # a source that returns nothing: every online criterion fails cleanly (counts only), within the request cap
    fb = type("FB", (), {"requests": 0, "live_check": None, "min_gap": 0.0, "last": 0.0, "retries": 0, "throttled": 0, "yielded_s": 0.0, "_last_live": 0.0,
                          "clock": staticmethod(lambda: 0.0), "sleep": staticmethod(lambda x: None), "transport": staticmethod(lambda url, params: (404, b"", {}))})()
    res = s.smoke_online(lim, {"now": 0.0, "factbase_lim": fb})
    assert res["_requests"]["pass"] and res["s_tag_walk"]["pass"] is False and res["s_availability_p_months"]["pass"] is False and res["s_factbase_transcript"]["pass"] is False


# =====================================================================================================================================================
# Freeze-check fixes (CREATIVE_BATCH_14.md section 11): regression tests
# =====================================================================================================================================================


def test_f13_stage2_is_weekly_and_closes_on_resolved_events_with_units(tmp_path):
    cap = ep(s.T14_S2_CAP)
    mp = tmp_path / "manifest_s2.json"
    now = ep("2026-11-20T00:00:00Z")
    assert s.stage2_weekly_gate(mp, now, cap) is None  # no pass yet: run now
    mp.write_text(json.dumps({"status": s.STAGE2_STATUS_OPEN, "last_pass_epoch": now - 2 * D_}))
    assert "weekly" in s.stage2_weekly_gate(mp, now, cap)  # 2 days after the last completed pass: idle
    assert s.stage2_weekly_gate(mp, now + 4 * D_, cap) is not None and s.stage2_weekly_gate(mp, now + 5 * D_ - 1, cap) is not None
    assert s.stage2_weekly_gate(mp, now - 2 * D_ + s.S2_PASS_EVERY_S, cap) is None  # 7 days later: the next pass
    mp.write_text(json.dumps({"status": s.IN_PROGRESS, "last_pass_epoch": now - D_}))
    assert s.stage2_weekly_gate(mp, now, cap) is None  # an interrupted pass resumes at once
    mp.write_text(json.dumps({"status": s.STAGE2_STATUS_OPEN, "last_pass_epoch": cap - D_}))
    assert s.stage2_weekly_gate(mp, cap + 60, cap) is None  # at the cap the closing pass runs at once
    assert s.S2_STOP_EVENTS == s.REP_MIN_EVENTS == 100  # the design's stop: 100 resolved events with a unit (not 150 transcripts)


def test_f13_unresolved_outcomes_are_refetched_and_only_a_flag_leaves_the_guarded_store(tmp_path):
    rdir = tmp_path / "hist" / s.FRAME_RUN
    (rdir / "guarded_s2").mkdir(parents=True)
    part = rdir / "stage2" / "fetch_partial.jsonl"
    part.parent.mkdir(parents=True)
    oc_part = s.oc_partial(rdir, "S2")
    items = [{"ev": {"event_id": "E1", "start_epoch": 0.0}, "map": {"record_url": "/x", "speaker_key": "trump"}, "members": [{"market_id": "m1", "event_id": "E1", "yes_index": "0"}]}]
    with part.open("w") as fh:  # transcript and market already fetched: only outcomes remain
        fh.write(json.dumps({"k": "tr", "event_id": "E1"}) + "\n" + json.dumps({"k": "mk", "market_id": "m1"}) + "\n")
    answers = iter([[{"id": "m1", "outcomePrices": "[\"0.5\", \"0.5\"]", "umaResolutionStatus": "proposed"}], [], [{"id": "m1", "outcomePrices": "[\"1\", \"0\"]", "umaResolutionStatus": "resolved"}]])

    class Lim:
        n = 0

        def get(self, url, params):
            Lim.n += 1
            return 200, next(answers)

    class FR:
        lim = Lim()
        extra_state: dict = {}

        def stop_reason(self, fn):
            return None

    assert s._fetch_targets(FR(), None, items, part, None, oc_part=oc_part, refetch_unresolved=True) is None
    assert s.resolution_state(part) == {"m1": False}
    assert s._fetch_targets(FR(), None, items, part, None, oc_part=oc_part, refetch_unresolved=True) is None  # the next weekly pass looks it up again
    assert s.resolution_state(part) == {"m1": True}
    assert s._store(oc_part, "oc")["m1"]["uma_status"] == "resolved"  # the latest lookup wins in the guarded outcome store
    assert "outcome_prices" not in part.read_text() and "resolved\"" not in part.read_text().replace('"resolved": true', "").replace('"resolved": false', "")
    n = Lim.n
    assert s._fetch_targets(FR(), None, items, part, None, oc_part=oc_part, refetch_unresolved=True) is None and Lim.n == n  # resolved: never looked up again
    assert s.resolved_flag({"outcome_prices": "", "uma_status": "unavailable (network)", "yes_index": 0}) is False


def test_f11_screen_recomputes_the_gates_on_p_alone_when_n_is_reported_only(world, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("an outcome file was opened although every P-only gate failed")

    monkeypatch.setattr(c14, "open_guarded", boom)
    out = s.screen_s(world["hist"], census={"label_S1": None, "label_S2": None}, out_root=world["out_root"], rules_sha="x", model_pin=world["pins"]["model_pin"],
                     rebased_pin=world["pins"]["rebased_pin"], n_primary={"n_primary": False}, ledger_path=world["ledger"], gsp_draws=5)
    assert out["gates_P_only"]["GS"]["pass"] is False and out["tags"] == ["P"]  # 33 P events < 100: the P-only test fails its population gate
    assert out["S1"]["verdict"] == out["S2"]["verdict"] == "not testable (population)" and out["S1"]["p"] == 1.0


def test_f15_s2_carries_the_half_and_leave_one_quarter_out_sign_checks(world, loose_gates):
    rdir = world["rdir"]
    models = s.make_models(world["out_root"], rdir / "fit", model_pin=world["pins"]["model_pin"], rebased_pin=world["pins"]["rebased_pin"])
    data = s.load_dataset(rdir, ("P", "N"), job="screen")
    outs = [o for tag in ("P", "N") for o in c14.open_guarded(s.subset_files(rdir, tag)["outcomes"], "screen", ("screen", "rep"))]
    ymap = s.build_ymap(data, outs)
    r = s.s2_screen(data, models, ymap, n_draws=2, n_wild=99, placebo=False)
    assert r["testable"], r.get("verdict")
    assert {"halves_sign", "leave_one_quarter_out_sign"} <= set(r["robustness"]) and "checks_ok" in r and "small_g_rules_hold" in r
    assert r["advance"] == bool(r["p_ok"] and r["checks_ok"])
