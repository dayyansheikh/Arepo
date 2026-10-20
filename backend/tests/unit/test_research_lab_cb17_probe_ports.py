# ruff: noqa: E501
"""The smoke's ports of probes P1-P3 against the VERBATIM scripts of design section 9, on one SYNTHETIC worn-window fixture (no real file is opened). The smoke can only be run on the host's
worn files, so this is the offline evidence that its counting equals the scripts' counting (a different count on the host is then a data difference, never a port difference)."""

from __future__ import annotations

import ast
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb17_smoke as sm
from tests.cb17_synth import (
    FILL_COLS,
    ep,
    fill_row,
    print_,
    stamp,
    write_capture,
    write_csv_gz,
    write_day,
    write_sweep,
)

DESIGN = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "CREATIVE_BATCH_17.md"
D12, D15 = ep("2026-10-12T00:00:00Z"), ep("2026-10-15T00:00:00Z")
LABELS = ["UNSCHEDULED-NEWS", "SCHEDULED-EVENT", "PATH-SETTLED", "SPORTS-FEED", "PUBLIC-STATISTIC"]


def scripts() -> dict[str, str]:
    txt = DESIGN.read_text()
    sec = txt[txt.index("## 9. Probe scripts"):txt.index("## 10. Challenger round 1")]
    blocks = re.findall(r"```python\n(.*?)```", sec, flags=re.S)
    assert len(blocks) == 3
    return {"p1": blocks[0], "p2": blocks[1], "p3": blocks[2]}


def run_script(src: str, root: Path) -> list[str]:
    head = 'R = "/home/opc/arepo/data-" + "dumps/research_lab"'
    assert head in src
    code = src.replace(head, f"R = {str(root)!r}")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip().splitlines()


def dict_in(line: str) -> dict:
    return ast.literal_eval(line[line.index("{"):line.rindex("}") + 1])


def ints(line: str) -> list[int]:
    return [int(x) for x in re.findall(r"(?<![\w.])\d+(?![\w.])", line)]


@pytest.fixture(scope="module")
def worn(tmp_path_factory):
    R = tmp_path_factory.mktemp("worn") / "research_lab"
    rnd = random.Random(11)
    snap, tr, sw = R / "snapshots", R / "live_trades", R / "book_sweeps"
    mkts = [(f"m{i}", f"c{i}", f"E{i // 2}") for i in range(10)]
    created = {f"m{i}": ("2026-10-11T23:00:00Z" if i == 0 else "2026-10-12T02:00:00Z" if i == 1 else "2026-10-05T00:00:00Z" if i < 6 else "2026-09-01T00:00:00Z" if i < 8 else "") for i in range(10)}
    quotes = [{"mid": m, "cid": c, "eid": e, "bid": "0.48", "ask": "0.50", "created": created[m], "fee_type": "sports_fees" if i in (8, 9) else "crypto_fees_v2", "fee_category": "sports" if i in (8, 9) else "crypto",
               "oi": str(1000 + 10 * i), "vol": str(5000 + 5 * i)} for i, (m, c, e) in enumerate(mkts)]
    write_capture(snap, "2026-10-12T00:31:03Z", quotes, name="20261012T003103Z_2df48d64")
    write_capture(snap, "2026-10-15T22:31:02Z", quotes, name="20261015T223102Z_2eae9aa6")
    # P3 captures (2026-10-15): six, the sports one named as the probe expects
    names = ["20261015T063101Z_9c518015", "20261015T083101Z_aa000001", "20261015T103101Z_aa000002", "20261015T123101Z_aa000003", "20261015T143101Z_aa000004", "20261015T163101Z_aa000005"]
    for k, nm in enumerate(names):
        qs = []
        for i, (m, c, e) in enumerate(mkts):
            mid = 0.4 + 0.003 * ((k * (i + 1)) % 5)
            qs.append({"mid": m, "cid": c, "eid": e, "bid": f"{mid - 0.01:.3f}", "ask": f"{mid + 0.01:.3f}", "fee_type": "sports_fees" if i in (8, 9) else "crypto_fees_v2", "fee_category": "sports" if i in (8, 9) else "crypto",
                       "oi": str(1000 + 7 * k * (i % 3) + (k % 2)), "vol": str(5000 + 100 * k * (1 + i % 4) if (k + i) % 5 else 5000 + 100 * (k - 1) * (1 + i % 4)), "nrm": "NR1" if i in (2, 3) else "",
                       "created": created[m]})
        write_capture(snap, f"2026-10-15T{6 + 2 * k:02d}:31:01Z", qs, name=nm)
    # P2 sweeps on 2026-10-15: 4 passes, two sweeps each; stamps differ by token and pass; tokens of the sports markets are excluded by the probe
    for p in range(4):
        for j, off in enumerate((0.0, 120.0)):
            recv = D15 + 7200.0 * p + off + 5.0
            books = []
            for i, (m, _c, _e) in enumerate(mkts):
                age = [20.0, 300.0, 1500.0, 5000.0][(i + p) % 4]
                shift = (i + p) % 3 == 0
                books.append({"tok": f"T{i}", "mid": m, "bid": "0.48", "ask": "0.50" if (i + p) % 5 else "0.51", "ts": int((D15 + 7200.0 * p + 5.0 - age + (30 if (j and shift) else 0)) * 1000), "hash": f"h{i}-{p}-{j if shift else 0}",
                              "d5b": 2000 + (300 * j if shift else 0), "d5a": 2000 - (200 * j if shift else 0), "d1b": 500, "d1a": 500, "recv": recv,
                              "state": "two_sided" if (i + p) % 7 else "one_sided_bid"})
            if p == 3 and j == 1:
                books = books[:-3]  # a token missing from the second sweep
            write_sweep(sw, D15 + 7200.0 * p + off, books, name=stamp(D15 + 7200.0 * p + off, f"{p:02x}{j:02x}0000"))
    # P1 fills and prints
    fills, days = [], {d: [] for d in ("12", "13", "14", "15")}
    for i in range(60):
        m, c, e = mkts[i % 10]
        tau = D12 + 3 * 86400.0 * rnd.random() + 600.0 * i
        d = rnd.choice((-1, 1))
        f = fill_row(i, c, tau, d, mkt=m, ev=e, label=LABELS[i % 5] if i % 10 not in (8, 9) else "SPORTS-FEED")
        f["tau"], f["tau_last"] = int(tau), int(tau) + 1
        fills.append(f)
        day = f"{int(tau // 86400) - int(D12 // 86400) + 12:02d}"
        kind = i % 9
        if kind == 8:
            continue  # no print
        oi = 0 if kind in (0, 1, 2, 3) else 1 if kind in (4, 5) else 2 if kind == 6 else 0
        days[day].append(print_(int(tau), c, 0.5, oi=oi, tx=f"tx{i}", mkt=m, ev=e))
        if kind == 7:
            days[day].append(print_(int(tau), c, 0.5, oi=0, tx=f"tx{i}b", mkt=m, ev=e))  # a second transaction in the same second: ambiguous
        if kind == 3:
            days[day].append(print_(int(tau) + 1, c, 0.5, oi=1, tx=f"tx{i}", mkt=m, ev=e))  # the same transaction on both tokens: mixed
    for dd, lines in days.items():
        write_day(tr, f"202610{dd}", lines)
    t_screen = R / "creative_batch13" / "t_screen"
    write_csv_gz(t_screen / "fills.csv.gz", FILL_COLS, fills)
    write_csv_gz(t_screen / "labels.csv.gz", ["condition_id", "label"], [{"condition_id": f["condition_id"], "label": f["label"]} for f in fills])
    return R


def test_p1_port_equals_the_verbatim_script(worn):
    out = run_script(scripts()["p1"], worn)
    got = sm.probe_p1(worn / "creative_batch13" / "t_screen", worn / "live_trades", worn / "snapshots")
    res = dict_in(out[0])
    assert ints(out[0])[0] == got["fills"] and {k: res.get(k, 0) for k in ("resolved", "ambiguous_tx", "no_print", "mixed_or_unknown_token")} == {k: got[k] for k in ("resolved", "ambiguous_tx", "no_print", "mixed_or_unknown_token")}
    assert got["resolved"] > 5 and got["ambiguous_tx"] >= 1 and got["no_print"] >= 1 and got["mixed_or_unknown_token"] >= 1
    assert ints(out[1])[0:2] == [got["non_sports"], got["non_sports_resolved"]]
    lab = dict_in(out[2])
    assert (lab.get("open", 0), lab.get("close", 0)) == (got["open"], got["close"]) and got["open"] > 0 and got["close"] > 0
    cl = dict_in(out[3])
    assert cl and {f"class|{a}|{b}": v for (a, b), v in cl.items()} == {k: v for k, v in got.items() if k.startswith("class|")}
    sp = dict_in(out[4])
    assert (sp.get("open", 0), sp.get("close", 0)) == (got["sports_open"], got["sports_close"])
    n = ints(out[5])
    assert n[-5:] == [got["cells"], got["cells_both"], got["fills_in_both"], got["markets_both"], got["events_both"]] or n == [got["cells"], got["cells_both"], got["fills_in_both"], got["markets_both"], got["events_both"]]
    assert ints(out[6])[-2:] == [got["markets_both_any_d"], got["fills_in_markets_both_any_d"]]
    age = dict_in(out[7])
    assert age and {f"age|{k}": v for k, v in age.items()} == {k: v for k, v in got.items() if k.startswith("age|")}
    assert ints(out[8])[-2:] == [got["markets_first_and_later"], got["markets_any_first_day"]]


def test_p2_port_equals_the_verbatim_script(worn):
    out = run_script(scripts()["p2"], worn)
    got = sm.probe_p2(worn / "book_sweeps", worn / "snapshots")
    assert ints(out[0]) == [got["sweeps"], got["pairs"]] and got["pairs"] >= 3
    counts = dict_in(out[1])
    assert counts and {k: got.get(k, 0) for k in counts} == counts and all(got.get(k, 0) == 0 for k in got if k in ("touch_same_shift_unparseable",) and k not in counts)
    age = dict_in(out[2])
    assert {f"age|{k}": v for k, v in age.items()} == {k: v for k, v in got.items() if k.startswith("age|")}
    assert ints(out[3])[-2:] == [got["tokens_both"], got["tokens_seen"]]
    av = dict_in(out[4])
    assert (av["ns_tok_pass"], av["next_pass_present"]) == (got["ns_tok_pass"], got["next_pass_present"])
    assert counts["hash_same"] > 0 and counts["hash_diff"] > 0 and got["touch_same_shift_nonzero"] > 0


def test_p3_port_equals_the_verbatim_script(worn):
    out = run_script(scripts()["p3"], worn)
    got = sm.probe_p3(worn / "snapshots")
    assert ints(out[0])[:2] == [got["captures"], got["intervals"]] and got["intervals"] >= 4
    c = dict_in(out[1])
    assert c and {k: got.get(k, 0) for k in c} == c and c["ns_traded"] > 0 and c["oi_changed"] > 0
    n = ints(out[2])  # "... >= 6 intervals X >= 3 Y any Z"
    assert [n[1], n[3], n[4]] == [got["events_ge6"], got["events_ge3"], got["events_any"]] and got["events_ge3"] > 0


def test_a_different_count_is_a_fail_never_adjusted(worn):
    got = sm.probe_p3(worn / "snapshots")
    cmp = sm.compare(got, sm.P3_EXPECTED)  # the synthetic fixture is not the host's data
    assert cmp["pass"] is False and "captures" in cmp["differences"] and cmp["observed"] == got
