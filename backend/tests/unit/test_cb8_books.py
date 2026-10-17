# ruff: noqa: E501
"""CB8-B data side, part 2 (q0166): pmxt book states at the checkpoints (both clocks, freshness, crossed, halted, depth), the count-only coverage audit, the
terminal prints, the ingress cap, the HOLDOUT seal and the leakage rules. Mocked HTTP and in-memory parquet only."""

from __future__ import annotations

import csv
import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import cb8_books as bk
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_updown as u
from astrolabe.research_lab import h5_seal
from tests.unit._cb8_fakes import print_row
from tests.unit._cb8_updown_fakes import PmxtFake, ev, parquet_bytes
from tests.unit.test_cb8_updown import FRAME_DAYS, FrameEnv, gz_rows, nosleep

DAY = "2026-04-14"
TE = int(u.t_end(DAY) * 1000)


def book_ev(tok, v, *, r=None, bids=(("0.90", "100"),), asks=(("0.95", "50"),), fee=700, mk="0xc"):
    return ev(mk, tok, "book", v, r, bids=[list(b) for b in bids], asks=[list(a) for a in asks], fee=fee)


def elist(*evs):
    """Convert fake parquet-style event dicts into the loader's event dicts (as read_hour_events produces)."""
    out = []
    for e in evs:
        out.append({"et": e["event_type"], "v": e["timestamp"], "r": e["timestamp_received"], "bids": e["bids"], "asks": e["asks"], "price": e["price"], "size": e["size"], "side": e["side"],
                    "tick": e["new_tick_size"], "fee": e["fee_rate_bps"]})
    return sorted(out, key=lambda e: (e["v"], e["r"]))


# ---- state_at -----------------------------------------------------------------------------------------------------------------------------------------------------


def test_state_best_ask_depth_tick_fee_and_price_changes():
    t = TE - 300000
    events = elist(book_ev("T", t - 90000, asks=(("0.95", "50"), ("0.96", "30"), ("0.99", "100"))),
                   ev("0xc", "T", "price_change", t - 60000, price=0.95, size=0.0, side="SELL"),  # the 0.95 level is removed
                   ev("0xc", "T", "price_change", t - 50000, price=0.97, size=7.0, side="SELL"),
                   ev("0xc", "T", "tick_size_change", t - 40000, tick="0.001"))
    s = bk.state_at(events, t, TE)
    assert s["has_book"] and s["best_ask"] == 0.96 and s["ask_size"] == 30.0 and s["ask_size_1c"] == 37.0  # 0.96 and 0.97 within 1c
    assert s["best_bid"] == 0.90 and s["tick"] == "0.001" and s["fee_bps"] == 700.0 and s["fresh"] and not s["crossed"]
    assert [p for p, _ in s["asks_top"]] == [0.96, 0.97, 0.99]


def test_state_uses_events_with_both_clocks_at_or_before_t():
    t = TE - 300000
    early = book_ev("T", t - 10000, asks=(("0.90", "50"),))
    late_receipt = book_ev("T", t - 5000, r=t + 1, asks=(("0.50", "50"),))  # venue time before t, received after t: not usable
    late_venue = book_ev("T", t + 1, r=t + 2, asks=(("0.40", "50"),))
    s = bk.state_at(elist(early, late_receipt, late_venue), t, TE)
    assert s["best_ask"] == 0.90 and s["n_events"] == 1
    exact = bk.state_at(elist(book_ev("T", t, r=t, asks=(("0.93", "50"),))), t, TE)
    assert exact["best_ask"] == 0.93  # both clocks equal to t are usable


def test_state_freshness_120s_halted_crossed_and_no_book():
    t = TE - 120000
    old = book_ev("T", t - 120000)  # exactly 120 s old: fresh
    assert bk.state_at(elist(old), t, TE)["fresh"] is True
    older = book_ev("T", t - 120001)
    s = bk.state_at(elist(older), t, TE)
    assert s["fresh"] is False and s["best_ask"] == 0.95  # stale but reconstructed
    # a price_change keeps the token fresh although the book is old
    pc = ev("0xc", "T", "price_change", t - 1000, price=0.96, size=10.0, side="SELL")
    assert bk.state_at(elist(older, pc), t, TE)["fresh"] is True
    crossed = bk.state_at(elist(book_ev("T", t - 5000, bids=(("0.97", "10"),), asks=(("0.95", "50"),))), t, TE)
    assert crossed["crossed"] is True and crossed["best_bid"] == 0.97  # reported, never repaired
    none = bk.state_at([], t, TE)
    assert not none["has_book"] and none["best_ask"] is None and none["halted"] is True and none["fresh"] is False
    pre_book = bk.state_at(elist(ev("0xc", "T", "price_change", t - 1000, price=0.96, size=10.0, side="SELL")), t, TE)
    assert not pre_book["has_book"]  # a price_change without a prior book event has no basis
    no_ask = bk.state_at(elist(book_ev("T", TE - 700000, asks=())), t, TE)
    assert no_ask["has_book"] and no_ask["best_ask"] is None and no_ask["halted"] is True  # no event after t_end - 600 s and no ask
    live_no_ask = bk.state_at(elist(book_ev("T", TE - 500000, asks=())), t, TE)
    assert live_no_ask["halted"] is False


def test_token_rows_checkpoints_and_plus_ten_seconds():
    m = {"market_id": "1", "condition_id": "0xc", "day": DAY}
    rows = bk.token_rows(m, "up", "T", elist(book_ev("T", TE - 900000)), TE)
    assert len(rows) == 8 and {(r[5], r[6]) for r in rows} == {(o, p) for o in bk.OFFSETS_S for p in (0, 10)}
    assert {r[7] for r in rows} == {TE - o * 1000 + p * 1000 for o in bk.OFFSETS_S for p in (0, 10)}
    assert max(r[7] for r in rows) == TE - 50000  # no state is later than t_end - 50 s


# ---- pmxt read / day states ----------------------------------------------------------------------------------------------------------------------------


def frame_markets(day=DAY, n=2):
    return [{"market_id": str(i), "condition_id": f"0xcond{i}", "token_up": f"tU{i}", "token_down": f"tD{i}", "day": day} for i in range(1, n + 1)]


def test_day_states_reads_15z_with_lookback_only_when_needed():
    px = PmxtFake()
    ms = frame_markets(n=3)
    h15 = int(datetime(2026, 4, 14, 15, tzinfo=UTC).timestamp() * 1000)
    h14 = h15 - 3600000
    evs15 = []
    for m in ms[:2]:
        for tok in (m["token_up"], m["token_down"]):
            evs15.append(book_ev(tok, h15 + 60000, mk=m["condition_id"], asks=(("0.95", "50"),)))
    # market 3: only a price_change in 15Z; its book sits in 14Z
    evs15.append(ev(ms[2]["condition_id"], ms[2]["token_up"], "price_change", h15 + 100000, price=0.96, size=9.0, side="SELL"))
    px.files["2026-04-14T15"] = parquet_bytes(evs15)
    px.files["2026-04-14T14"] = parquet_bytes([book_ev(ms[2]["token_up"], h14 + 60000, mk=ms[2]["condition_id"], asks=(("0.91", "20"),)),
                                               book_ev(ms[2]["token_down"], h14 + 60000, mk=ms[2]["condition_id"], asks=(("0.09", "20"),))])
    rows, minfo, info = bk.day_states(DAY, ms, fetch=px.fetch, size_fn=px.size_fn)
    assert info["lookback_tokens"] == 2 and info["lookback_status"] == "read" and info["bytes"] > 0
    by = {(r[0], r[3], r[5], r[6]): r for r in rows}
    assert by[("3", "up", 60, 0)][10] == 0.91 and by[("3", "up", 300, 0)][10] == 0.91  # the 14Z book, then the 15Z price_change (0.96 level at 100 s after the hour: later than t - 300 s?)
    assert [x["status"] for x in minfo] == ["ok", "ok", "ok"] and [x["lookback"] for x in minfo] == ["not_needed", "not_needed", "read"]
    assert {r[0] for r in rows} == {"1", "2", "3"} and len(rows) == 3 * 2 * 8


def test_day_states_marks_market_without_events_source_unavailable_and_missing_hour():
    px = PmxtFake()
    ms = frame_markets(n=2)
    px.add_day(DAY, ms, skip={"2"})
    rows, minfo, _ = bk.day_states(DAY, ms, fetch=px.fetch, size_fn=px.size_fn)
    assert [x["status"] for x in minfo] == ["ok", "source_unavailable"] and {r[0] for r in rows} == {"1"}  # its own label, never "no trade"
    px2 = PmxtFake()
    with pytest.raises(bk.HourMissing):
        bk.day_states(DAY, ms, fetch=px2.fetch, size_fn=px2.size_fn)
    px.corrupt.add("2026-04-14T15")
    with pytest.raises(bk.HourCorrupt):
        bk.day_states(DAY, ms, fetch=px.fetch, size_fn=px.size_fn)


def test_read_hour_events_prunes_row_groups_and_uses_both_clocks():
    px = PmxtFake()
    ms = frame_markets(n=6)
    px.add_day(DAY, ms)
    tokens = {ms[0]["token_up"]: ms[0]["condition_id"]}
    full = len(px.files["2026-04-14T15"])
    evs, info = bk.read_hour_events(datetime(2026, 4, 14, 15, tzinfo=UTC), tokens, fetch=px.fetch, size_fn=px.size_fn, cut_ms=TE)
    assert info["row_groups_read"] < info["row_groups_total"] and len(evs[ms[0]["token_up"]]) == 2
    # a cut before the price_change drops it; a cut before the receipt of the book event drops that too
    h15 = int(datetime(2026, 4, 14, 15, tzinfo=UTC).timestamp() * 1000)
    evs, _ = bk.read_hour_events(datetime(2026, 4, 14, 15, tzinfo=UTC), tokens, fetch=px.fetch, size_fn=px.size_fn, cut_ms=h15 + 1002)
    assert len(evs[ms[0]["token_up"]]) == 0  # book at h15 + 1000 received at +1005
    evs, _ = bk.read_hour_events(datetime(2026, 4, 14, 15, tzinfo=UTC), tokens, fetch=px.fetch, size_fn=px.size_fn, cut_ms=h15 + 1005)
    assert len(evs[ms[0]["token_up"]]) == 1
    assert full > 0


# ---- audit, order -------------------------------------------------------------------------------------------------------------------------------------------


def test_audit_day_list_and_order_alternate_and_are_seeded():
    days = {"screen": [f"s{i}" for i in range(30)], "holdout": [f"h{i}" for i in range(30)]}
    a = bk.audit_day_list(days)
    assert len(a) == 20 and sum(d.startswith("s") for d in a) == 10 and a == bk.audit_day_list(days)
    o = bk.day_order(days)
    assert len(o) == 60 and [d[0] for d in o[:6]] == ["s", "h", "s", "h", "s", "h"] and o == bk.day_order(days)
    assert bk.day_order({"screen": ["a"], "holdout": ["b", "c"]})[-1] in ("b", "c")


def audit_inputs(px, present: dict[str, bool], tmp_path):
    days = list(present)
    markets_by_day, split_of = {}, {}
    for d in days:
        markets_by_day[d] = frame_markets(d, 3)
        split_of[d] = "screen"
        if present[d]:
            px.add_day(d, markets_by_day[d], hour=13)
    return days, markets_by_day, split_of


def test_coverage_audit_pass_fail_threshold_and_counts_only(tmp_path):
    px = PmxtFake()
    days, mk, sp = audit_inputs(px, {"2026-04-14": True, "2026-04-15": True}, tmp_path)
    a = bk.coverage_audit(days, mk, sp, fetch=px.fetch, size_fn=px.size_fn, rdir=tmp_path)
    assert a["pass"] and a["share"] == 1.0 and a["n_pairs"] == 6 and set(a) >= {"per_day", "share_readable_only"}
    assert bk.ingress_used(tmp_path) > 0
    px = PmxtFake()
    days, mk, sp = audit_inputs(px, {"2026-04-14": True, "2026-04-15": False}, tmp_path)  # one hour file missing -> 50%
    a = bk.coverage_audit(days, mk, sp, fetch=px.fetch, size_fn=px.size_fn, rdir=tmp_path)
    assert not a["pass"] and a["share"] == 0.5 and a["n_days_hour_unreadable"] == 1 and a["share_readable_only"] == 1.0
    px = PmxtFake()
    days, mk, sp = audit_inputs(px, {"2026-04-14": True}, tmp_path)
    px.files.pop("2026-04-14T13")
    px.add_day("2026-04-14", mk["2026-04-14"], hour=13, skip={"1", "2"})  # 1 of 3 present: 33%
    a = bk.coverage_audit(days, mk, sp, fetch=px.fetch, size_fn=px.size_fn, rdir=tmp_path)
    assert not a["pass"] and a["n_present"] == 1
    # exactly 90% passes (9 of 10 pairs), a shade below does not
    px = PmxtFake()
    mk = {"2026-04-14": frame_markets(n=10)}
    px.add_day("2026-04-14", mk["2026-04-14"], hour=13, skip={"10"})
    a = bk.coverage_audit(["2026-04-14"], mk, {"2026-04-14": "screen"}, fetch=px.fetch, size_fn=px.size_fn, rdir=tmp_path)
    assert a["share"] == 0.9 and a["pass"]


# ---- terminal prints --------------------------------------------------------------------------------------------------------------------------------------


def test_terminal_prints_split_at_t_end_and_keep_no_wallet():
    from astrolabe.research_lab import history_backfill as hb
    from tests.unit._cb8_fakes import Api

    api = Api()
    te = int(u.t_end(DAY))
    api.trades["0xc"] = [print_row("0xc", te - 600, wallet="0xRAW1"), print_row("0xc", te - 1, wallet="0xRAW2"), print_row("0xc", te + 5, wallet="0xRAW3"), print_row("0xc", te - 1000, wallet="0xRAW4"),
                         print_row("0xc", te - 901, wallet="0xRAW5"), print_row("0xc", te + 121, wallet="0xRAW6")]
    lim = hb.Limiter(api, rps=1000.0, sleep=nosleep)
    pre, post, info = bk.terminal_prints(lim, "0xc", te)
    assert [r[0] for r in pre] == [te - 600, te - 1] and [r[0] for r in post] == [te + 5] and not info["capped"]
    assert all(len(r) == 5 for r in pre + post) and "RAW" not in json.dumps([pre, post])
    assert api.calls[0][1]["start"] == te - 900 and api.calls[0][1]["end"] == te + 120


# ---- books_fetch: end to end ----------------------------------------------------------------------------------------------------------------------------


class BooksEnv(FrameEnv):
    def __init__(self, tmp: Path):
        super().__init__(tmp)
        self.frame_run = self.frame()
        assert self.frame_run["status"] == u.FRAME_COMPLETE
        self.rows = gz_rows(self.root / u.RUN_FRAME / "frame.csv.gz")
        self.px = PmxtFake()
        self.seals = tmp / "seals"
        self.seals.mkdir()
        by_day: dict[str, list[dict]] = {}
        for r in self.rows:
            by_day.setdefault(r["day"], []).append(r)
        self.by_day = by_day
        for d, ms in by_day.items():
            self.px.add_day(d, ms, hour=15)
            self.px.add_day(d, ms, hour=13)
            te = int(u.t_end(d))
            for m in ms:
                self.api.trades[m["condition_id"]] = [print_row(m["condition_id"], te - 100, wallet=f"0xRAW{m['market_id']}"), print_row(m["condition_id"], te + 10, wallet="0xRAWZ")]

    def books(self, **kw):
        args = dict(rules_sha=self.sha, fetch=self.px.fetch, size_fn=self.px.size_fn, smoke_path=self.smoke, audit_days=4, rps=1000.0, sleep=nosleep, now=1.8e9, seals_dir=self.seals)
        args.update(kw)
        return bk.books_fetch(self.root, self.api, **args)


@pytest.fixture
def benv(tmp_path):
    return BooksEnv(tmp_path)


def test_books_fetch_end_to_end_holdout_sealed_and_post_prints_guarded(benv):
    m = benv.books()
    assert m["status"] == bk.COMPLETE and m["complete"], m
    rdir = benv.root / bk.RUN_ID
    screen_days = {d for d in benv.by_day if u.day_split(d) == "screen"}
    holdout_days = set(benv.by_day) - screen_days
    assert screen_days and holdout_days
    for d in benv.by_day:
        sp = u.day_split(d)
        assert (rdir / sp / f"{d}.states.csv.gz").exists() and (rdir / sp / f"{d}.prints.csv.gz").exists() and (rdir / sp / f"{d}.prints_post_guarded.csv.gz").exists()
        other = "holdout" if sp == "screen" else "screen"
        assert not (rdir / other / f"{d}.states.csv.gz").exists()
    states = gz_rows(rdir / "screen" / f"{sorted(screen_days)[0]}.states.csv.gz")
    assert states and set(states[0]) == set(bk.STATE_COLUMNS) and max(int(r["t_ms"]) for r in states) <= int(u.t_end(sorted(screen_days)[0]) * 1000) - 50000
    # post-t_end prints exist only in the *_guarded file; the pre file has only ts < t_end
    d0 = sorted(benv.by_day)[0]
    sp0 = u.day_split(d0)
    pre = gz_rows(rdir / sp0 / f"{d0}.prints.csv.gz")
    post = gz_rows(rdir / sp0 / f"{d0}.prints_post_guarded.csv.gz")
    assert pre and post and all(int(r["ts"]) < u.t_end(d0) for r in pre) and all(int(r["ts"]) >= u.t_end(d0) for r in post)
    assert b"0xRAW" not in b"".join(gzip.decompress(p.read_bytes()) for p in rdir.rglob("*.csv.gz"))
    # the coverage audit ran first and counted
    audit = json.loads((rdir / "audit.json").read_text())
    assert audit["pass"] and audit["n_days"] == 4 and audit["hour"] == 13
    days = gz_rows(rdir / "days.csv.gz")
    assert {d["states_status"] for d in days} == {"ok"} and len(days) == len(benv.by_day)
    mk = gz_rows(rdir / "markets.csv.gz")
    assert {x["states_status"] for x in mk} == {"ok"} and {x["split"] for x in mk} == {"screen", "holdout"}
    # no checkpoint extraction happened before the audit: the first pmxt request is hour 13Z
    assert benv.px.sizes[0].endswith("T13")
    man = json.loads((rdir / "manifest.json").read_text())
    assert cm.verify_manifest_files(rdir, {"file_sha256": man["file_sha256"]}) == len(man["file_sha256"])


def test_holdout_seal_listing_copy_and_leakage_rules(benv):
    benv.books()
    rdir = benv.root / bk.RUN_ID
    seal = json.loads((rdir / bk.SEAL_NAME).read_text())
    copy = benv.seals / bk.SEAL_COPY_NAME
    assert copy.read_bytes() == (rdir / bk.SEAL_NAME).read_bytes()
    files = h5_seal.list_files(rdir)
    holdout = {k: v for k, v in files.items() if k.startswith("holdout/")}
    assert seal["listing_sha256"] == h5_seal.listing_sha256(holdout) and seal["n_holdout_files"] == len(holdout) and holdout
    assert set(seal["files"]) == set(holdout) and not any(k.startswith("screen/") for k in seal["files"])
    assert (rdir / "ACCESS_LOG.jsonl").exists() and (rdir / "ACCESS_LOG.jsonl").read_text() == ""
    assert "never read" in seal["read_rules"] or "not opened before" in seal["read_rules"]
    # the sealed copy names no market, outcome, price or ask: only file hashes and counts
    text = copy.read_text()
    assert "outcome_prices" not in text and "best_ask" not in text
    # re-running is idempotent and the seal is never rewritten
    assert benv.books()["complete"]
    assert copy.read_bytes() == (rdir / bk.SEAL_NAME).read_bytes()
    # a changed sealed file is detected by the listing hash
    victim = next((rdir / "holdout").glob("*.states.csv.gz"))
    victim.write_bytes(victim.read_bytes() + b"x")
    assert h5_seal.listing_sha256({k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith("holdout/")}) != seal["listing_sha256"]


def test_no_holdout_value_reaches_screen_files_or_the_census_inputs(benv):
    benv.books()
    rdir = benv.root / bk.RUN_ID
    hold_ids = {r["market_id"] for r in benv.rows if r["split"] == "holdout"}
    screen_ids = {r["market_id"] for r in benv.rows if r["split"] == "screen"}
    assert hold_ids and screen_ids and not hold_ids & screen_ids
    for p in (rdir / "screen").glob("*.states.csv.gz"):
        assert not {r["market_id"] for r in gz_rows(p)} & hold_ids
    for p in (rdir / "holdout").glob("*.states.csv.gz"):
        assert not {r["market_id"] for r in gz_rows(p)} & screen_ids
    # the day-level files are counts only: no price, ask or print column
    for name in ("days.csv.gz", "markets.csv.gz"):
        header = next(csv.reader(gzip.open(rdir / name, "rt")))
        assert not [c for c in header if "ask" in c or "bid" in c or "price" in c or "outcome" in c]


def test_seal_time_drops_by_id_and_key_are_recorded_not_applied(benv):
    victim = benv.rows[0]
    twin_event = benv.rows[1]["event_id"]
    benv.api.gamma["7777"] = benv.api.gamma[benv.rows[1]["market_id"]] | {"id": "7777", "conditionId": "0xother"}
    (benv.seals / "h6_weather_SEAL.json").write_text(json.dumps({"files": {f"prices/{victim['market_id']}.csv.gz": "x", "trades/7777.csv.gz": "y", "manifest.json": "z"}}))
    m = benv.books()
    assert m["status"] == bk.COMPLETE
    rdir = benv.root / bk.RUN_ID
    drops = {d["market_id"]: d for d in gz_rows(rdir / "drops.csv.gz")}
    assert drops[victim["market_id"]]["block"] == "DROPPED_SEAL_COPIES" and drops[victim["market_id"]]["reason"].startswith("id")
    assert any("event" in d["reason"] for d in drops.values()) and benv.rows[1]["market_id"] in drops and twin_event
    seal = json.loads((rdir / bk.SEAL_NAME).read_text())
    assert seal["drops"]["seal_copies_read"] == ["h6_weather_SEAL.json"] and seal["drops"]["disjointness"] == "verified"
    # sealed states are not edited: the dropped market's rows are still in its split file
    sp = victim["split"]
    assert victim["market_id"] in {r["market_id"] for p in (rdir / sp).glob("*.states.csv.gz") for r in gz_rows(p)}


def test_seal_time_drops_unverified_when_metadata_is_missing(benv):
    (benv.seals / "h5_cb1_SEAL.json").write_text(json.dumps({"files": {"prices/nometa1.csv.gz": "x", "prices/nometa2.csv.gz": "y"}}))
    benv.books()
    seal = json.loads((benv.root / bk.RUN_ID / bk.SEAL_NAME).read_text())
    assert seal["drops"]["disjointness"] == u.UNVERIFIED


def test_audit_fail_ends_source_unavailable_and_extracts_no_checkpoint(benv):
    for d in benv.by_day:
        benv.px.files.pop(f"{d}T13", None)  # no hour 13Z anywhere: 0% coverage
    m = benv.books()
    assert m["status"] == bk.SOURCE_UNAVAILABLE and m["complete"]
    rdir = benv.root / bk.RUN_ID
    assert (rdir / "AUDIT_FAIL.json").exists() and not list(rdir.rglob("*.states.csv.gz")) and not (rdir / bk.SEAL_NAME).exists()
    assert not any(k.endswith("T15") for k in benv.px.sizes)  # the checkpoint hour was never even asked for
    assert benv.books()["status"] == bk.SOURCE_UNAVAILABLE


def test_market_without_events_is_source_unavailable_not_no_trade(benv):
    d = sorted(benv.by_day)[0]
    ms = benv.by_day[d]
    benv.px.files.pop(f"{d}T15")
    benv.px.add_day(d, ms, hour=15, skip={ms[0]["market_id"]})
    benv.books()
    rdir = benv.root / bk.RUN_ID
    mk = {x["market_id"]: x for x in gz_rows(rdir / "markets.csv.gz")}
    assert mk[ms[0]["market_id"]]["states_status"] == "source_unavailable" and mk[ms[1]["market_id"]]["states_status"] == "ok"
    days = {x["day"]: x for x in gz_rows(rdir / "days.csv.gz")}
    assert days[d]["n_source_unavailable"] == "1"


def test_missing_and_corrupt_hours_lose_the_day_and_are_counted(benv):
    ds = sorted(benv.by_day)
    benv.px.files.pop(f"{ds[0]}T15")
    benv.px.corrupt.add(f"{ds[1]}T15")
    benv.books()
    rdir = benv.root / bk.RUN_ID
    days = {x["day"]: x for x in gz_rows(rdir / "days.csv.gz")}
    assert days[ds[0]]["states_status"] == "hour_missing" and days[ds[1]]["states_status"] == "hour_corrupt" and days[ds[2]]["states_status"] == "ok"
    mk = [x for x in gz_rows(rdir / "markets.csv.gz") if x["day"] == ds[0]]
    assert {x["states_status"] for x in mk} == {"day_hour_missing"}  # never replaced, never "no trade"


def test_ingress_cap_truncates_both_splits_evenly_and_counts_unprocessed_days(benv):
    by_split = {s: sorted(d for d in benv.by_day if u.day_split(d) == s) for s in ("screen", "holdout")}
    order = bk.day_order(by_split)
    assert {u.day_split(order[0]), u.day_split(order[1])} == {"screen", "holdout"}  # the cap truncates both splits evenly
    # a cap far below the audit's own ingress: the audit still runs first (it is counts only), then every day is "ingress_cap" (counted, never "no trade")
    benv.books(ingress_cap_gb=1e-9)
    rdir = benv.root / bk.RUN_ID
    days = gz_rows(rdir / "days.csv.gz")
    assert {d["states_status"] for d in days} == {"ingress_cap"} and {d["prints_status"] for d in days} == {"ingress_cap"}
    assert json.loads((rdir / "manifest.json").read_text())["counts"]["days_ingress_cap"] == len(days)
    assert not list(rdir.glob("*/*.states.csv.gz"))


def test_ingress_cap_midway_processes_the_first_day_of_the_seeded_order(tmp_path):
    env = BooksEnv(tmp_path)
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    by_split = {s: sorted(d for d in env.by_day if u.day_split(d) == s) for s in ("screen", "holdout")}
    order = bk.day_order(by_split)
    audit = bk.coverage_audit(bk.audit_day_list(by_split, 4), env.by_day, {d: u.day_split(d) for d in env.by_day}, fetch=env.px.fetch, size_fn=env.px.size_fn, rdir=probe_dir)
    cap = (bk.ingress_used(probe_dir) + 1) / 1e9
    assert audit["pass"]
    env.px.served = 0
    env.books(ingress_cap_gb=cap)
    rdir = env.root / bk.RUN_ID
    days = {d["day"]: d for d in gz_rows(rdir / "days.csv.gz")}
    assert days[order[0]]["states_status"] == "ok" and {days[d]["states_status"] for d in order[1:]} == {"ingress_cap"}


def test_books_resume_after_stop_and_guards(benv):
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 3

    m = benv.books(should_stop=stop)
    assert m["status"] == "in_progress" and m["stopped"] == "should_stop"
    asked_before = list(benv.px.sizes)
    m = benv.books()
    assert m["status"] == bk.COMPLETE
    days_states = [s for s in benv.px.sizes if s.endswith("T15")]
    assert len(days_states) == len(set(days_states))  # no day's checkpoint hour is read twice across chunks
    assert asked_before
    benv.smoke.write_text(json.dumps({"smoke_version": u.SMOKE_VERSION, "rules_sha256": benv.sha, "criterion_b_binance_checksum": True, "criterion_c_pmxt_heads": False}))
    with pytest.raises(cm.Refused, match="not met"):
        bk.books_fetch(benv.root, benv.api, rules_sha=benv.sha, fetch=benv.px.fetch, size_fn=benv.px.size_fn, smoke_path=benv.smoke, rps=1000.0, sleep=nosleep, now=1.8e9)
    with pytest.raises(cm.Refused, match="run id"):
        bk.books_fetch(benv.root, benv.api, rules_sha=benv.sha, fetch=benv.px.fetch, size_fn=benv.px.size_fn, smoke_path=benv.smoke, run_id="h6_weather", rps=1000.0, sleep=nosleep)


def test_books_refuse_an_unfinished_or_tampered_frame(tmp_path):
    env = FrameEnv(tmp_path)
    px = PmxtFake()
    with pytest.raises(cm.Refused, match="no manifest"):
        bk.books_fetch(env.root, env.api, rules_sha=env.sha, fetch=px.fetch, size_fn=px.size_fn, smoke_path=env.smoke, rps=1000.0, sleep=nosleep)
    env.frame()
    victim = env.root / u.RUN_FRAME / "frame.csv.gz"
    victim.write_bytes(victim.read_bytes() + b"x")
    with pytest.raises(cm.Refused, match="differs"):
        bk.books_fetch(env.root, env.api, rules_sha=env.sha, fetch=px.fetch, size_fn=px.size_fn, smoke_path=env.smoke, rps=1000.0, sleep=nosleep)


def test_frame_days_have_both_splits():
    assert {u.day_split(d) for d in FRAME_DAYS if d in u.b_days()} == {"screen", "holdout"}
