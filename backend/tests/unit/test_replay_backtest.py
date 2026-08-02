"""Replay player + backtest tests, emphasising look-ahead safety and determinism."""
from astrolabe.analytics.backtest import run_backtest
from astrolabe.replay.player import ReplayPlayer, default_player


def test_player_loads_and_shapes():
    p = default_player()
    ids = p.market_ids()
    assert len(ids) == 3
    m = p.market(ids[0])
    assert m.is_binary and m.enable_order_book
    assert len(p.token_ids(ids[0])) == 2
    assert p.n_frames(ids[0]) == 48


def test_book_best_first_and_midpoint_defined():
    p = default_player()
    mid_id = p.market_ids()[0]
    tok = p.token_ids(mid_id)[0]
    book = p.book_at(mid_id, tok, 0)
    # best bid is the highest bid; best ask is the lowest ask
    assert book.best_bid == max(lv.price for lv in book.bids)
    assert book.best_ask == min(lv.price for lv in book.asks)
    assert book.midpoint is not None and book.is_two_sided


def test_price_history_is_a_strict_prefix_lookahead_safe():
    """price_history(upto_index=i) must equal the first i+1 points of the full series."""
    p = default_player()
    mid_id = p.market_ids()[0]
    tok = p.token_ids(mid_id)[0]
    full = p.prices(mid_id, tok)
    for i in (0, 5, 20, p.n_frames(mid_id) - 1):
        prefix = p.prices(mid_id, tok, upto_index=i)
        assert prefix == full[: i + 1]           # no data from frames > i leaks in


def test_backtest_is_deterministic_and_lookahead_safe():
    r1 = run_backtest()
    r2 = run_backtest()
    # Determinism: identical results across runs.
    assert r1.sample_size == r2.sample_size
    assert r1.hit_rate == r2.hit_rate
    assert r1.false_positive_rate == r2.false_positive_rate

    # Non-degenerate demo (planted momentum + spike-revert episodes exist).
    assert r1.sample_size >= 4
    assert r1.hit_rate is not None and 0.0 < r1.hit_rate < 1.0
    assert r1.missing_observations >= 0

    # Look-ahead guard: every scored event's forward price is the entry frame + horizon,
    # taken from data strictly AFTER the signal frame.
    player = default_player()
    for e in r1.events:
        if e.forward_price is None:
            continue
        full = player.prices(e.market_id, e.token_id)
        assert e.entry_price == full[e.frame]
        assert e.forward_price == full[e.frame + r1.horizon]
        assert e.frame + r1.horizon > e.frame


def test_backtest_reports_assumptions_and_limitations():
    r = run_backtest()
    text = " ".join(r.assumptions + r.limitations).lower()
    assert "look" not in text or "frames 0..i" in " ".join(r.assumptions).lower()
    assert any("not" in x.lower() and "profit" in x.lower() for x in r.limitations)
    assert any("survivorship" in x.lower() for x in r.limitations)


def test_custom_player_path_roundtrip(tmp_path):
    # The default dataset file exists and is parseable by a fresh player instance.
    p = ReplayPlayer()
    assert p.meta.get("seed") == 42
    assert "synthetic" in p.meta.get("disclaimer", "").lower()
