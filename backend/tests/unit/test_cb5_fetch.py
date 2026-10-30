# ruff: noqa: E501
"""CB5 fetch side (astrolabe.research_lab.cb5_fetch, scripts/run_cb5.py cohort-fetch / census): census parse guard, cohort
selection, cohort fetch (wallet blanking, price clipping, failed status, manifest and selection pin) and the CLI refusals.
Fixtures and a fake limiter only: no network (CB5 freeze check 2026-10-29, items 1-5)."""

from __future__ import annotations

import gzip
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from astrolabe.research_lab import cb5_fetch as F
from astrolabe.research_lab import cb5_run as R
from astrolabe.research_lab import history_backfill as hb

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND / "scripts"))

H = 3600.0
L0 = 1_791_936_000.0  # 2026-10-14T00:00Z, inside the census window


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _trade(ts: float, price: float, *, side: str = "BUY", outcome: int = 0, wallet: str = "0xabc", tx: str = "") -> dict:
    return {"timestamp": int(ts), "side": side, "size": 10.0, "price": price, "outcomeIndex": outcome, "proxyWallet": wallet,
            "transactionHash": tx or f"tx{int(ts)}{price}", "asset": "tok0"}


class FakeLimiter:
    """``get`` answers from per-market tables: ``trades[condition_id]`` -> (status, list) and ``prices[token]`` -> (status, points)
    or an exception to raise (the limiter giving up)."""

    def __init__(self, trades: dict, prices: dict) -> None:
        self.trades, self.prices, self.calls = trades, prices, []

    def get(self, url, params, max_retries=None):
        self.calls.append((url, dict(params)))
        if url == hb.DATA_TRADES:
            ans = self.trades[params["market"]]
            if isinstance(ans, Exception):
                raise ans
            status, rows = ans
            return (status, rows[params["offset"]:params["offset"] + params["limit"]]) if status == 200 else (status, None)
        if url == hb.CLOB_PRICES:
            ans = self.prices[params["market"]]
            if isinstance(ans, Exception):
                raise ans
            status, pts = ans
            if status != 200:
                return status, None
            return 200, {"history": [{"t": t, "p": p} for t, p in pts if params["startTs"] <= t <= params["endTs"]]}
        raise AssertionError(url)


def _listings(n: int = 3, *, created: float = L0) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({"market_id": f"m{i}", "condition_id": f"c{i}", "clob_token_id_0": f"t{i}", "clob_token_id_1": f"u{i}",
                     "created_at": _iso(created + i * H), "fee_category": "politics", "received_utc": _iso(created + i * H + 60),
                     "best_bid": "0.40", "best_ask": "0.44"})
    return pd.DataFrame(rows)


def _select(lst: pd.DataFrame, **kw) -> pd.DataFrame:
    return F.select_cohort(lst, window="census", seed=kw.pop("seed", "s"), max_markets=kw.pop("max_markets", 100),
                           dev_start="2026-10-11T12:00:00Z", census_end="2026-10-26T00:00:00Z", **kw)


def _read_gz(path: Path) -> pd.DataFrame:
    with gzip.open(path, "rt") as fh:
        return pd.read_csv(fh, dtype=str, keep_default_na=False)


# ---- census_trim ---------------------------------------------------------------------------------------------------------


def test_census_trim_keeps_only_created_to_first_trade_plus_1h():
    L = L0
    rows = [[L - 60, "BUY"], [L + 600, "BUY"], [L + 600 + 3599, "SELL"], [L + 600 + 3600, "BUY"], [L + 600 + 3601, "BUY"], [L + 30 * H, "BUY"]]
    kept, info = F.census_trim(rows, L)
    assert info["first_trade"] == L + 600 and info["bound"] == L + 600 + H
    assert [r[0] for r in kept] == [L + 600, L + 600 + 3599, L + 600 + 3600]


def test_census_trim_caps_at_24h_and_handles_no_trade():
    L = L0
    kept, info = F.census_trim([[L + 23.5 * H, "BUY"], [L + 24 * H + 1, "BUY"]], L)
    assert info["bound"] == L + 24 * H and [r[0] for r in kept] == [L + 23.5 * H]
    kept, info = F.census_trim([[L - 10, "BUY"]], L)
    assert kept == [] and info == {"bound": L + 24 * H, "first_trade": None}


# ---- select_cohort -------------------------------------------------------------------------------------------------------


def test_select_cohort_population_rules_and_window():
    lst = _listings(6)
    lst.loc[1, "fee_category"] = "sports:nba"
    lst.loc[2, "fee_category"] = "weather"
    lst.loc[3, "clob_token_id_1"] = ""  # not binary
    lst.loc[4, "created_at"] = "2026-10-25T23:59:59Z"  # last second inside census_end
    lst.loc[5, "created_at"] = "2026-10-26T00:00:00Z"  # census_end is exclusive
    dup = lst.iloc[[0]].assign(received_utc=_iso(L0 + 99 * H))
    sel = _select(pd.concat([lst, dup], ignore_index=True))
    assert sorted(sel["market_id"]) == ["m0", "m4"]
    assert sel.loc[sel["market_id"] == "m0", "received_utc"].item() == _iso(L0 + 60)  # first sighting kept


def test_select_cohort_seeded_rank_is_deterministic_and_capped():
    lst = _listings(40)
    a = _select(lst, seed="arepo-cb5-census", max_markets=10)
    b = _select(lst.sample(frac=1.0, random_state=3), seed="arepo-cb5-census", max_markets=10)
    assert list(a["market_id"]) == list(b["market_id"]) and len(a) == 10
    assert list(_select(lst, seed="other", max_markets=10)["market_id"]) != list(a["market_id"])
    assert set(_select(lst, max_markets=100, exclude_ids={"m0", "m1"})["market_id"]).isdisjoint({"m0", "m1"})


# ---- cohort_fetch --------------------------------------------------------------------------------------------------------


def _world(sel: pd.DataFrame, *, ft_offset: float = 600.0):
    trades, prices = {}, {}
    for _, r in sel.iterrows():
        L = float(r["created"])
        trades[r["condition_id"]] = (200, [_trade(L + ft_offset, 0.42), _trade(L + ft_offset + 1800, 0.45), _trade(L + ft_offset + 2 * H, 0.50)])
        prices[r["clob_token_id_0"]] = (200, [(int(L - 600), 0.5), (int(L + 300), 0.42), (int(L + ft_offset + 1800), 0.45), (int(L + 5 * H), 0.6)])
    return trades, prices


def test_cohort_fetch_blanks_wallets_clips_prices_and_records_manifest(tmp_path):
    sel = _select(_listings(2))
    trades, prices = _world(sel)
    out = tmp_path / "census_cohort"
    res = F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s",
                         listings_input={"manifest_sha256": "ab" * 32, "captures_in_window": 5})
    assert res["complete"] and res["total_done"] == 2 and res["n_failed"] == 0
    for _, r in sel.iterrows():
        L = float(r["created"])
        tr = _read_gz(out / "trades" / f"{r['market_id']}.csv.gz")
        assert (tr["wallet_hash"] == "").all() and "0xabc" not in (out / "trades" / f"{r['market_id']}.csv.gz").read_bytes().decode("latin1")
        assert tr["ts"].astype(float).max() <= L + 600 + H  # trade 2h after the first is dropped
        assert len(tr) == 2
        pr = _read_gz(out / "prices" / f"{r['market_id']}.csv.gz")
        assert pr["t"].astype(float).max() <= L + 600 + H and len(pr) == 3  # the L + 5h point is never written
    man = json.loads((out / "manifest.json").read_text())
    assert man["complete"] is True and man["seed"] == "s" and man["selection_sha256"] == F.selection_sha256(sel)
    assert man["listings_manifest_sha256"] == "ab" * 32 and man["n_failed"] == 0 and man["done"] == 2
    prog = [json.loads(x) for x in (out / "progress.jsonl").read_text().splitlines()]
    assert {p["status"] for p in prog} == {"done"} and all(p["trades_truncated"] is False for p in prog)


@pytest.mark.parametrize("kind", ["trades_404", "prices_500", "gave_up"])
def test_failed_fetch_is_failed_not_done_and_retried_on_resume(tmp_path, kind):
    sel = _select(_listings(2))
    trades, prices = _world(sel)
    bad = sel.iloc[0]
    good_trades, good_prices = dict(trades), dict(prices)
    if kind == "trades_404":
        trades[bad["condition_id"]] = (404, None)
    elif kind == "prices_500":
        prices[bad["clob_token_id_0"]] = (500, None)
    else:
        trades[bad["condition_id"]] = RuntimeError("giving up after 6 retries")
    out = tmp_path / "census_cohort"
    res = F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s")
    assert res["n_failed"] == 1 and res["total_done"] == 1 and res["complete"] is True  # every market attempted; failure counted
    assert not (out / "trades" / f"{bad['market_id']}.csv.gz").exists() and not (out / "prices" / f"{bad['market_id']}.csv.gz").exists()
    last = hb._read_progress(out / "progress.jsonl")[bad["market_id"]]
    assert last["status"] == "failed" and last["failures"]
    assert json.loads((out / "manifest.json").read_text())["n_failed"] == 1
    # resume: only the failed market is retried, and it becomes done
    lim = FakeLimiter(good_trades, good_prices)
    res2 = F.cohort_fetch(sel, lim, out, window="census", now_epoch=L0 + 30 * 86400, seed="s")
    assert res2["done"] == 1 and res2["n_failed"] == 0 and res2["total_done"] == 2
    assert {c[1].get("market") for c in lim.calls} == {bad["condition_id"], bad["clob_token_id_0"]}
    assert hb._read_progress(out / "progress.jsonl")[bad["market_id"]]["status"] == "done"


def test_truncated_trade_list_is_recorded(tmp_path):
    sel = _select(_listings(1))
    L = float(sel.iloc[0]["created"])
    many = [_trade(L + 600 + i, 0.42, tx=f"x{i}") for i in range(F.MAX_TRADES + 5)]
    trades = {sel.iloc[0]["condition_id"]: (200, sorted(many, key=lambda t: -t["timestamp"]))}  # newest first, over the cap
    prices = {sel.iloc[0]["clob_token_id_0"]: (200, [])}
    out = tmp_path / "c"
    F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s")
    assert hb._read_progress(out / "progress.jsonl")[sel.iloc[0]["market_id"]]["trades_truncated"] is True


def test_census_resume_refused_when_selection_changes(tmp_path):
    lst = _listings(5)
    sel = _select(lst, max_markets=3)
    trades, prices = _world(_select(lst))
    out = tmp_path / "c"
    F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s", max_items=1)
    man = json.loads((out / "manifest.json").read_text())
    assert man["complete"] is False and man["selection_sha256"] == F.selection_sha256(sel)
    with pytest.raises(F.SelectionChanged):
        F.cohort_fetch(_select(lst, max_markets=4), FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s")
    res = F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s")  # same selection resumes
    assert res["complete"] and res["total_done"] == 3
    (out / "manifest.json").unlink()  # progress without a manifest cannot be verified
    with pytest.raises(F.SelectionChanged):
        F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s")


# ---- census_g_cohort: truncated and failed markets ---------------------------------------------------------------------


def test_census_g_cohort_excludes_truncated_and_counts_failed(tmp_path):
    sel = _select(_listings(3))
    trades, prices = _world(sel)
    out = tmp_path / "c"
    F.cohort_fetch(sel, FakeLimiter(trades, prices), out, window="census", now_epoch=L0 + 30 * 86400, seed="s")
    prog = hb._read_progress(out / "progress.jsonl")
    ids = list(sel["market_id"])
    F._append(out / "progress.jsonl", {**prog[ids[0]], "trades_truncated": True})
    F._append(out / "progress.jsonl", {"market_id": ids[1], "status": "failed", "failures": [{"status": 500}]})
    (out / "trades" / f"{ids[0]}.csv.gz").write_bytes(b"not read")  # a truncated market's files are never read
    c = R.census_g_cohort(sel.drop(columns="created"), out)
    assert c["n_cohort"] == 1 and c["unavailable_truncated"] == 1 and c["n_failed"] == 1
    assert c["seed_echo"]["n_valid"] <= 1


# ---- CLI refusals --------------------------------------------------------------------------------------------------------


def _cli_args(tmp_path, *extra):
    dd = tmp_path / "dd"
    dd.mkdir(exist_ok=True)
    return ["cohort-fetch", "--window", "census", "--out-root", str(tmp_path / "out"), "--extract-root", str(tmp_path / "ext"),
            "--data-dumps", str(dd), *extra]


def test_cohort_fetch_cli_exit_75_on_headroom(tmp_path):
    import run_cb5 as cli

    (tmp_path / "dd").mkdir()
    (tmp_path / "dd" / "blob").write_bytes(b"x" * 1000)
    assert cli.main(_cli_args(tmp_path, "--data-dumps-max-gb", "0.00000001", "--disk-cap-gb", "0.03")) == 75
    assert not (tmp_path / "out").exists()


def test_cohort_fetch_cli_exit_2_before_t5_dev_end(tmp_path, monkeypatch):
    import run_cb5 as cli

    class Early(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 26, 23, 0, tzinfo=UTC)

    monkeypatch.setattr(cli, "datetime", Early)
    assert cli.main(_cli_args(tmp_path, "--data-dumps-max-gb", "100")) == 2
    assert not (tmp_path / "out").exists()


def test_cohort_fetch_cli_exit_2_on_changed_selection(tmp_path, monkeypatch):
    import run_cb5 as cli

    lst = _listings(5)
    trades, prices = _world(_select(lst))
    monkeypatch.setattr(R, "read_listings", lambda *a, **k: lst)
    monkeypatch.setattr(R, "listings_input", lambda *a, **k: {"manifest_sha256": "cd" * 32})
    monkeypatch.setattr(cli, "_limiter", lambda rps: FakeLimiter(trades, prices))
    assert cli.main(_cli_args(tmp_path, "--data-dumps-max-gb", "100", "--max-markets", "3")) == 0
    man = json.loads((tmp_path / "out" / "census_cohort" / "manifest.json").read_text())
    assert man["complete"] is True and man["seed"] == "arepo-cb5-census" and man["listings_manifest_sha256"] == "cd" * 32
    assert cli.main(_cli_args(tmp_path, "--data-dumps-max-gb", "100", "--max-markets", "4")) == 2


def test_census_cli_refused_unless_cohort_manifest_complete(tmp_path):
    import run_cb5 as cli

    out = tmp_path / "out"
    args = ["census", "--family", "K", "--out-root", str(out), "--history-root", str(tmp_path / "hist")]
    assert cli.main(args) == 2  # no cohort manifest
    (out / "census_cohort").mkdir(parents=True)
    (out / "census_cohort" / "manifest.json").write_text(json.dumps({"complete": False}))
    assert cli.main(args) == 2  # partial cohort
    assert not (out / "census.json").exists()


def test_listings_input_counts_capture_status(tmp_path):
    man = {"captures": {"a": {"capture_start_utc": "2026-10-12T00:00:00Z", "tables": {"listings": {"status": "extracted"}}},
                        "b": {"capture_start_utc": "2026-10-13T00:00:00Z", "tables": {"listings": {"status": "missing"}}},
                        "c": {"capture_start_utc": "2026-10-28T00:00:00Z", "tables": {"listings": {"status": "extracted"}}}}}
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    info = R.listings_input(tmp_path, before="2026-10-27T00:00:00Z", since="2026-10-11T12:00:00Z")
    assert info["captures_in_window"] == 2 and info["listings_status_counts"] == {"extracted": 1, "missing": 1}
    assert len(info["manifest_sha256"]) == 64


@pytest.fixture(autouse=True)
def _no_real_trials_log(monkeypatch):
    monkeypatch.setattr(R, "log_descriptive", lambda *a, **k: [])  # census CLI tests must not append to the real trials.jsonl


def _census_l_setup(tmp_path, manifest):
    out = tmp_path / "out"
    (out / "census_cohort").mkdir(parents=True)
    (out / "census_cohort" / "manifest.json").write_text(json.dumps({"complete": True}))
    if manifest is not None:
        (out / "cdf_frame").mkdir(parents=True)
        (out / "cdf_frame" / "manifest_v1.json").write_text(json.dumps(manifest))
    return out, ["census", "--family", "L", "--out-root", str(out), "--history-root", str(tmp_path / "hist"), "--extract-root", str(tmp_path / "ext")]


def test_census_l_zero_family_manifest_emits_g59_not_testable(tmp_path):
    import hashlib

    import run_cb5 as cli

    out, args = _census_l_setup(tmp_path, {"version": 1, "counts": {"n_families": 0}, "family_list_sha256": "ab" * 32})
    assert cli.main(args) == 0
    doc = json.loads((out / "census.json").read_text())
    L = doc["L"]
    assert L["status"] == "g59_not_testable" and L["g59"] == {"ok": False, "n_families": 0, "status": "not testable: 0 families"}
    assert L["l1_counted_p"] == 1.0 and "0 families" in L["ch59"]
    assert L["family_list_sha256"] == "ab" * 32
    assert L["frame_manifest_sha256"] == hashlib.sha256((out / "cdf_frame" / "manifest_v1.json").read_bytes()).hexdigest()
    assert not (out / "cdf_frame" / "audit_state.json").exists()  # no audit failure recorded
    assert cli.main(args) == 2  # census stays write-once (FileExistsError refused)


def test_census_l_nonempty_manifest_without_frozen_list_stays_inputs_missing(tmp_path):
    import run_cb5 as cli

    out, args = _census_l_setup(tmp_path, {"version": 1, "counts": {"n_families": 3}, "family_list_sha256": "cd" * 32})
    assert cli.main(args) == 0
    assert json.loads((out / "census.json").read_text())["L"]["status"] == "inputs_missing"


@pytest.mark.parametrize("manifest", [None, "garbage"])
def test_census_l_missing_or_unreadable_manifest_is_inputs_missing(tmp_path, manifest):
    import run_cb5 as cli

    out, args = _census_l_setup(tmp_path, None)
    if manifest:
        (out / "cdf_frame").mkdir(parents=True)
        (out / "cdf_frame" / "manifest_v1.json").write_text("{not json")
    assert cli.main(args) == 0
    assert json.loads((out / "census.json").read_text())["L"]["status"] == "inputs_missing"
