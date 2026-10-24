# ruff: noqa: E501
"""CB16-K topic-audit sample (offline; synthetic cross_venue files only, no network, no outcome)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from astrolabe.research_lab import cb16_common as c16
from astrolabe.research_lab import cb16_k as k
from astrolabe.research_lab import cb16_k_audit as ka
from tests.test_cb16_k import END0, kal_row, poly_row, write_world


def word(i: int) -> str:
    return "qq" + "".join(chr(97 + (i // 26**j) % 26) for j in range(3))


def world(n: int):
    """n frame markets, each with one same-date topic twin; market 1 also has a second, weaker twin; one absent market."""
    poly, kal = [], []
    for i in range(1, n + 1):
        poly.append(poly_row(i, f"Will {word(i)} {word(i + 500)} {word(i + 900)} happen?"))
        kal.append(kal_row(f"T{i}", f"{word(i)} {word(i + 500)} {word(i + 900)}", END0 + 3600.0))
    kal.append(kal_row("WEAK", f"{word(1)} {word(1 + 500)} {word(1 + 900)} zzextraone zzextratwo", END0 + 7200.0))
    poly.append(poly_row(9001, "Will zzzunmatched thing happen on the moon?"))
    return poly, kal


@pytest.fixture()
def built(tmp_path, monkeypatch):
    d = tmp_path / "cross_venue"
    d.mkdir()
    poly, kal = world(130)
    write_world(d, poly, kal, [])
    monkeypatch.setattr(k, "CROSS_VENUE_PINS", {n: c16.sha256_file(d / n) for n in ("poly_markets.json", "kalshi_markets.jsonl", "matches_all.json")})
    block = k.census(d)
    block["re_entry"]["counts_pass"] = True  # the fixture is too small to pass the real counts
    census = {"version": "cb16-census-K-v1", "counts_only": True, "K": block}
    return d, census


def run(d: Path, census: dict, out: Path, n: int = 100):
    return ka.sample_run(d, census, "c" * 64, out, n=n)


def test_exactly_100_and_deterministic_under_the_seed(built, tmp_path):
    d, census = built
    r1 = run(d, census, tmp_path / "o1")
    r2 = run(d, census, tmp_path / "o2")
    assert r1["n_drawn"] == 100 and r1["n_present_topic_pairs"] == 130
    assert r1["sample_sha256"] == r2["sample_sha256"] and r1["keys_sha256"] == r2["keys_sha256"]
    keys = json.loads((tmp_path / "o1" / ka.KEYS_NAME).read_text())["pairs"]
    assert len({p["market_id"] for p in keys}) == 100 and [p["pair"] for p in keys] == list(range(100))
    pairs = ka.derive_topic_pairs(d)
    assert [p["market_id"] for p in ka.draw(pairs, 16141, 100)] == [p["market_id"] for p in ka.draw(pairs, 16141, 100)]
    assert [p["market_id"] for p in ka.draw(pairs, 16142, 100)] != [p["market_id"] for p in ka.draw(pairs, 16141, 100)]


def test_all_pairs_when_fewer_than_100(built, tmp_path):
    d, census = built
    r = run(d, census, tmp_path / "o", n=500)
    assert r["n_drawn"] == 130  # fewer than requested: all
    assert ka.draw([], 16141, 100) == []


def test_only_allowed_fields_and_no_outcomes_or_ids_in_the_auditor_file(built, tmp_path):
    d, census = built
    run(d, census, tmp_path / "o")
    sample = json.loads((tmp_path / "o" / ka.SAMPLE_NAME).read_text())
    assert set(sample) == {"version", "for_auditor", "pairs"}
    for p in sample["pairs"]:
        assert set(p) == set(ka.SAMPLE_FIELDS)
    txt = (tmp_path / "o" / ka.SAMPLE_NAME).read_text()
    for forbidden in ("outcome_prices", "closed_time", "settlement_value", "volume", "result", "market_id", "ticker", "event_id", '"T1"', "p_end"):
        assert forbidden not in txt
    keys = json.loads((tmp_path / "o" / ka.KEYS_NAME).read_text())
    assert all(set(p) == set(ka.KEY_FIELDS) for p in keys["pairs"]) and keys["NOT_FOR_AUDITOR"] is True


def test_the_weakest_twin_is_shown_and_manifest_pins_both_files(built, tmp_path):
    d, census = built
    pairs = {p["market_id"]: p for p in ka.derive_topic_pairs(d)}
    assert pairs["1"]["n_twins"] == 2 and pairs["1"]["ticker"] == "WEAK" and pairs["2"]["n_twins"] == 1
    run(d, census, tmp_path / "o")
    man = json.loads((tmp_path / "o" / ka.MANIFEST_NAME).read_text())
    for nm, key in ((ka.SAMPLE_NAME, "sample_sha256"), (ka.KEYS_NAME, "keys_sha256")):
        assert man[key] == hashlib.sha256((tmp_path / "o" / nm).read_bytes()).hexdigest()
    assert man["seed"] == 16141 and man["census_K_sha256"] == "c" * 64 and man["cross_venue_pins_sha256"] == k.CROSS_VENUE_PINS and man["outcome_free"] is True


def test_refusals_missing_or_mismatched_census_pins_and_counts(built, tmp_path):
    d, census = built
    with pytest.raises(c16.Refused):
        ka.sample_run(d, {}, "x", tmp_path / "a")
    bad = copy.deepcopy(census)
    bad["K"]["pins"]["sha256"]["poly_markets.json"] = "0" * 64
    with pytest.raises(c16.Refused, match="pins"):
        run(d, bad, tmp_path / "b")
    bad = copy.deepcopy(census)
    bad["K"]["re_entry"]["counts_pass"] = False
    with pytest.raises(c16.Refused, match="counts"):
        run(d, bad, tmp_path / "c")
    bad = copy.deepcopy(census)
    bad["K"]["re_entry"]["topic_audit_seed"] = 1
    with pytest.raises(c16.Refused, match="seed"):
        run(d, bad, tmp_path / "d")
    bad = copy.deepcopy(census)
    bad["K"]["label_counts"]["PRESENT-TOPIC"] += 1
    with pytest.raises(c16.Refused, match="census"):
        run(d, bad, tmp_path / "e")
    assert not (tmp_path / "e" / ka.SAMPLE_NAME).exists()
    (d / "matches_all.json").write_text("[]\n")  # the input on disk no longer hashes to the pin
    with pytest.raises(c16.Refused, match="pinned"):
        run(d, census, tmp_path / "f")


def test_outputs_are_write_once(built, tmp_path):
    d, census = built
    run(d, census, tmp_path / "o")
    with pytest.raises(c16.Refused, match="written once"):
        run(d, census, tmp_path / "o")
