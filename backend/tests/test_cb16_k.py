# ruff: noqa: E501
"""CB16-K census (offline; synthetic cross_venue files only, no network, no outcome)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import cb13_label as lab
from astrolabe.research_lab import cb16_common as c16
from astrolabe.research_lab import cb16_k as k


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


END0 = ep("2026-03-01T00:00:00Z")
FORBIDDEN_POLY = {"outcome_prices": "[1,0]", "outcomePrices": "x", "closed_time": "2026-03-02T00:00:00Z", "umaResolutionStatus": "resolved", "result": "yes", "settlement_value": 1, "p_end": "x"}


def poly_row(i: int, q_: str, *, end: float = END0, event: str | None = None, vol: float = 50000.0, outcomes=("Yes", "No")) -> dict:
    return {"market_id": str(i), "event_id": event or f"ev{i}", "question": q_, "outcomes": list(outcomes), "end": iso(end), "volume": vol, **FORBIDDEN_POLY}


def kal_row(t: str, title: str, close: float, **kw) -> dict:
    return {"ticker": t, "title": title, "yes_sub": "", "close_time": iso(close), "cat": "Politics", "volume": 9000, "result": "yes", "settlement_value": 1, **kw}


@pytest.fixture()
def cv_dir(tmp_path):
    d = tmp_path / "cross_venue"
    d.mkdir()
    return d


def write_world(d: Path, poly: list[dict], kal: list[dict], matches: list[dict], flags: dict | None = None) -> None:
    (d / "poly_markets.json").write_text(json.dumps(poly))
    (d / "kalshi_markets.jsonl").write_text("".join(json.dumps(x) + "\n" for x in kal))
    (d / "matches_all.json").write_text(json.dumps([{**m, "p_end": "hindsight", "score": 1.0} for m in matches]))
    if flags is not None:
        (d / "audit_flags.json").write_text(json.dumps(flags))


def test_k_part_is_declared_once_the_matches_all_pin_is_set_and_is_a_census_with_no_test():
    assert c16.rules_part_file_doc("K")["part_declared"] is True
    assert k.CROSS_VENUE_PINS["matches_all.json"] != c16.PIN_UNSET and k.part_unready() is None and k.EXPECTED_COUNTS == {"poly_markets": 148384, "kalshi_markets": 326380, "matches": 958}
    d = k.declared()
    assert d["family"].endswith("k = 0") and "result" in d["never_parsed"] or "settlement_value" in d["never_parsed"]
    assert "K" not in c16.FREEZE_PARTS


def test_streaming_readers_keep_only_allow_listed_fields_and_never_parse_an_outcome(cv_dir):
    write_world(cv_dir, [poly_row(1, "Will A win?")], [kal_row("T1", "A wins", END0)], [{"p_market_id": "1", "p_event_id": "ev1", "k_ticker": "T1", "k_cat": "Politics"}],
                {"rule": {"T9": "hand"}, "resolution_disagree": ["T1"], "concordance_after_rule": {"n": 3}})
    rows = list(k.iter_json_array(cv_dir / "poly_markets.json", k.POLY_KEEP)) + list(k.iter_kalshi(cv_dir)) + k.read_matches(cv_dir)
    parsed = {key for r in rows for key in r}
    assert not (set(c16.FORBIDDEN_PARSE_FIELDS) & parsed) and not ({"p_end", "result", "settlement_value", "score", "outcome_prices", "closed_time"} & parsed)
    assert k.read_rule_conflicts(cv_dir) == {"T9"}  # the outcome-based resolution list is never parsed
    big = [poly_row(i, f"Question number {i}?") for i in range(2500)]
    (cv_dir / "poly_markets.json").write_text(json.dumps(big))
    assert sum(1 for _ in k.iter_json_array(cv_dir / "poly_markets.json", ("market_id",), chunk=4096)) == 2500  # chunked streaming
    with pytest.raises(c16.Refused):
        k.read_matches(cv_dir.parent)  # not a cross_venue directory


def test_unknown_cross_venue_files_are_refused(tmp_path):
    for nm in ("results.json", "matches.json", "series.npz"):
        with pytest.raises(c16.Refused):
            c16.guard_cross_venue_file(tmp_path / "cross_venue" / nm)
    for root in ("cross_venue_live", "surprise_live"):
        with pytest.raises(c16.Refused):
            c16.guard_cross_venue_file(tmp_path / root / "matches_all.json")


def test_topic_rule_edges_three_days_two_words_and_jaccard():
    a = frozenset("alpha beta gamma".split())
    assert k.text_twin(a, frozenset("alpha beta delta".split())) is True  # 2 shared, Jaccard 2/4 = 0.5
    assert k.text_twin(frozenset("a1 b1 c1 d1".split()), frozenset("a1 b1 e1 f1 g1 h1".split())) is False  # 2 shared, Jaccard 0.25
    assert k.text_twin(frozenset("a1 b1 c1 d1 e1".split()), frozenset("a1 b1 f1 g1 h1".split())) is False  # 2 shared, Jaccard 2/8 = 0.25
    assert k.text_twin(frozenset("a1 b1 c1".split()), frozenset("a1 d1 e1".split())) is False  # one shared word
    assert k.text_twin(frozenset("a1 b1 c1 d1 e1 f1 g1".split()), frozenset("a1 b1 c1 h1".split())) is True  # 3 shared, Jaccard 3/8 = 0.375
    assert k.text_twin(frozenset("a1 b1 c1 d1 e1 f1 g1 h1".split()), frozenset("a1 b1 c1 x1 y1".split())) is True  # 3 shared, Jaccard 3/10 = 0.30 exactly
    assert k.gap_class(3 * 86400.0) == "topic" and k.gap_class(3 * 86400.0 + 1) is None
    assert k.gap_class(30 * 86400.0) == "far" and k.gap_class(30 * 86400.0 - 1) is None
    assert k.gap_class(180 * 86400.0) == "far" and k.gap_class(180 * 86400.0 + 1) is None
    assert k.gap_class(-4 * 86400.0) is None and k.gap_class(-40 * 86400.0) == "far"


def test_labels_strict_topic_far_absent_unlistable_and_disjointness(cv_dir):
    poly = [
        poly_row(1, "Will Alice Smith win the Ohio senate election?"),                       # strict
        poly_row(2, "Will Bob Jones win the Texas governor election?"),                      # topic twin (same date)
        poly_row(3, "Will Carol White win the Maine senate election?"),                      # far twin only (60 d away)
        poly_row(4, "Will Dave Black visit the moon station?"),                              # absent
        poly_row(5, "Will an assassination attempt occur against the premier?"),             # absent and unlistable
        poly_row(6, "Will Erin Green win the Utah senate election?", outcomes=("A", "B")),   # not Yes/No: outside the frame
        poly_row(7, "Will Fay Gray win the Iowa senate election?", end=ep("2027-05-01T00:00:00Z")),  # outside the date window
    ]
    kal = [kal_row("K1", "Alice Smith win Ohio senate election", END0 + 86400.0),
           kal_row("K2", "Bob Jones win Texas governor election", END0 + 2 * 86400.0),
           kal_row("K3", "Carol White win Maine senate election", END0 + 60 * 86400.0),
           kal_row("K4", "Totally different thing about weather", END0)]
    write_world(cv_dir, poly, kal, [{"p_market_id": "1", "p_event_id": "ev1", "k_ticker": "K1", "k_cat": "Politics"}])
    ix = k.build_kalshi_index(k.iter_kalshi(cv_dir))
    recs, counts = k.label_markets(k.iter_json_array(cv_dir / "poly_markets.json", k.POLY_KEEP), ix, {"1"}, set())
    by = {r["market_id"]: r for r in recs}
    assert set(by) == {"1", "2", "3", "4", "5"} and counts["outside_frame"] == 2
    assert by["1"]["label"] == "PRESENT-STRICT" and by["2"]["label"] == "PRESENT-TOPIC"
    assert by["3"]["label"] == k.LABEL_ABSENT and by["3"]["far_topic"] == 1  # FAR-TOPIC is a counted subset of ABSENT, disjoint from PRESENT-TOPIC
    assert by["4"]["label"] == k.LABEL_ABSENT and by["4"]["far_topic"] == 0 and by["4"]["unlistable"] == 0
    assert by["5"]["label"] == k.LABEL_ABSENT and by["5"]["unlistable"] == 1
    assert not any(r["far_topic"] and r["label"] == "PRESENT-TOPIC" for r in recs)
    # an r1 audit-rule conflict is excluded from PRESENT-STRICT (and counted), then labelled by the text rule
    recs2, c2 = k.label_markets(k.iter_json_array(cv_dir / "poly_markets.json", k.POLY_KEEP), ix, {"1"}, {"1"})
    assert {r["market_id"]: r for r in recs2}["1"]["label"] == "PRESENT-TOPIC" and c2["r1_conflict_excluded"] == 1
    # an UNLISTABLE-regex market labelled PRESENT is a rule conflict, counted
    poly2 = [poly_row(8, "Will the coup in Ohio senate election fail?")]
    kal2 = [kal_row("K8", "coup Ohio senate election fail", END0)]
    write_world(cv_dir, poly2, kal2, [])
    ix2 = k.build_kalshi_index(k.iter_kalshi(cv_dir))
    recs3, c3 = k.label_markets(k.iter_json_array(cv_dir / "poly_markets.json", k.POLY_KEEP), ix2, set(), set())
    assert recs3[0]["label"] == "PRESENT-TOPIC" and c3["unlistable_rule_conflict"] == 1


def test_far_topic_edges_at_30_and_180_days(cv_dir):
    poly = [poly_row(i, "Will Gina Hall win the Alaska senate election?", end=END0) for i in range(1, 5)]
    for i, p in enumerate(poly):
        p["market_id"] = str(i + 1)
    kal = [kal_row("A", "Gina Hall win Alaska senate election", END0 + 30 * 86400.0)]
    write_world(cv_dir, poly[:1], kal, [])
    ix = k.build_kalshi_index(k.iter_kalshi(cv_dir))
    pw = k.words_of(k.poly_text(poly[0]))
    assert ix.best(pw, END0, k.FAR_GAP_S[0], k.FAR_GAP_S[1]) is True
    assert ix.best(pw, END0, 0.0, k.TOPIC_MAX_GAP_S) is False
    ix2 = k.build_kalshi_index([kal_row("B", "Gina Hall win Alaska senate election", END0 + 30 * 86400.0 - 60.0)])
    assert ix2.best(pw, END0, k.FAR_GAP_S[0], k.FAR_GAP_S[1]) is False
    ix3 = k.build_kalshi_index([kal_row("C", "Gina Hall win Alaska senate election", END0 - 180 * 86400.0)])
    assert ix3.best(pw, END0, k.FAR_GAP_S[0], k.FAR_GAP_S[1]) is True
    ix4 = k.build_kalshi_index([kal_row("D", "Gina Hall win Alaska senate election", END0 - 180 * 86400.0 - 60.0)])
    assert ix4.best(pw, END0, k.FAR_GAP_S[0], k.FAR_GAP_S[1]) is False


def test_cells_deciles_eligibility_mde_and_the_reentry_verdict():
    recs = []
    for dec in range(10):
        for lbl, n in (("PRESENT-STRICT", 100), ("PRESENT-TOPIC", 100), (k.LABEL_ABSENT, 120)):
            for i in range(n):
                recs.append({"market_id": f"{dec}-{lbl}-{i}", "event_id": f"e{dec}-{lbl}-{i}", "class": lab.NEWS, "volume": float(dec * 1000 + i), "label": lbl, "far_topic": int(lbl == k.LABEL_ABSENT and i < 40),
                             "unlistable": 0, "rule_conflict": 0})
    k.add_deciles(recs)
    assert {r["decile"] for r in recs} == set(range(10))
    cells = k.cell_counts(recs)
    el_s = k.eligible_cells(cells, ("PRESENT-STRICT",))
    el_u = k.eligible_cells(cells, ("PRESENT-STRICT", "PRESENT-TOPIC"))
    assert len(el_s) == 10 and len(el_u) == 10
    m = k.mde_bounds(cells, ("PRESENT-STRICT", "PRESENT-TOPIC"))
    import math  # noqa: PLC0415

    gp, ga = m["events_present"], m["events_absent"]
    assert m["optimistic_sd_0_10_pp"] == pytest.approx(100 * 3.80 * 0.10 * math.sqrt(1 / gp + 1 / ga)) and m["max_sd_0_24_pp"] == pytest.approx(2.4 * m["optimistic_sd_0_10_pp"])
    strict = k.mde_bounds(cells, ("PRESENT-STRICT",))
    ri = k.re_entry(strict, m, cells)
    assert ri["counts_pass"] is True and ri["far_topic_cells"] == 10 and "audit may proceed" in ri["verdict"]
    thin = [r for r in recs if r["decile"] < 3]
    cells3 = k.cell_counts(thin)
    m3 = k.mde_bounds(cells3, ("PRESENT-STRICT", "PRESENT-TOPIC"))
    r3 = k.re_entry(k.mde_bounds(cells3, ("PRESENT-STRICT",)), m3, cells3)
    assert r3["counts_pass"] is False and "not testable at the floor" in r3["verdict"]
    for r in recs[:5]:
        r["class"] = lab.SPORTS
    k.add_deciles(recs)
    assert all(r["decile"] == -1 for r in recs[:5])
    assert not any(c["decile"] < 0 for c in k.cell_counts(recs).values() if c["class"] != lab.SPORTS)


def test_whole_census_on_a_fixture_counts_only_with_overlaps(cv_dir, monkeypatch):
    names = [chr(96 + i) * 4 for i in range(1, 21)]  # unique alphabetic tokens (the tokenizer drops digits)
    poly = [poly_row(i, f"Will {names[i - 1]}son win the {names[i - 1]}ville?", event=f"ev{i // 2}") for i in range(1, 21)]
    kal = [kal_row(f"K{i}", f"{names[i - 1]}son win {names[i - 1]}ville", END0 + 86400.0) for i in range(1, 11)]
    write_world(cv_dir, poly, kal, [{"p_market_id": "1", "p_event_id": "ev0", "k_ticker": "K1", "k_cat": "Politics"}])
    monkeypatch.setattr(k, "CROSS_VENUE_PINS", {n: c16.sha256_file(cv_dir / n) for n in ("poly_markets.json", "kalshi_markets.jsonl", "matches_all.json")})
    out = k.census(cv_dir, {"1": {"h2_main"}, "2": {"h3_power", "h2_main"}})
    assert out["counts_only"] is True and out["label_counts"]["frame"] == 20 and out["label_counts"]["PRESENT-STRICT"] == 1 and out["label_counts"]["PRESENT-TOPIC"] == 9
    assert out["key_overlaps"]["h2_main"] == {"PRESENT-STRICT": 1, "PRESENT-TOPIC": 1} and out["key_overlaps"]["h3_power"] == {"PRESENT-TOPIC": 1}
    assert out["re_entry"]["counts_pass"] is False and "volume_decile_edges" in out and out["pins"]["ok"] is True


def test_census_refuses_inputs_that_differ_from_their_pins(cv_dir):
    write_world(cv_dir, [poly_row(1, "x y z")], [kal_row("K", "x y z", END0)], [])
    with pytest.raises(c16.Refused, match="pinned sha256"):
        k.census(cv_dir)


def test_smoke_k_requires_the_exact_published_counts_and_no_outcome_field(cv_dir):
    write_world(cv_dir, [poly_row(1, "x y z")], [kal_row("K", "x y z", END0)], [])
    res = k.smoke_offline({"cross_venue_dir": str(cv_dir)})
    assert res["k_counts_exact"]["pass"] is False and res["k_counts_exact"]["counts"] == {"poly_markets": 1, "kalshi_markets": 1, "matches": 0}
    assert res["k_no_outcome_fields"]["pass"] is True and res["k_topic_rule"]["pass"] is True and res["k_inputs_pinned"]["pass"] is False
    assert set(k.SMOKE_NEEDS) <= set(res)
    gone = k.smoke_offline({"cross_venue_dir": str(cv_dir / "nope")})
    assert gone["k_counts_exact"]["pass"] is False and gone["k_inputs_pinned"]["pass"] is False
    assert k.EXPECTED_COUNTS == {"poly_markets": 148384, "kalshi_markets": 326380, "matches": 958}
