"""Historical reconstructed retrospective: no look-ahead, ranking, forward scoring."""
from datetime import UTC, datetime, timedelta

from astrolabe.domain.models import PricePoint
from astrolabe.evaluation.historical import Candidate, run_historical_screen

AS_OF = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def _series(returns, start_price, start_time, step_minutes):
    pts = [PricePoint(t=start_time, p=start_price)]
    p, t = start_price, start_time
    for r in returns:
        t = t + timedelta(minutes=step_minutes)
        p = min(0.99, max(0.01, p + r))
        pts.append(PricePoint(t=t, p=p))
    return pts


def _mover_up():
    # 40 pre-cutoff points: calm baseline then a 6-step upward burst ending at the cut-off.
    base = [0.002 if i % 2 == 0 else -0.002 for i in range(33)]
    burst = [0.02] * 6
    t0 = AS_OF - timedelta(minutes=39 * 30)
    prefix = _series(base + burst, 0.30, t0, 30)
    # After the cut-off it keeps rising (so the up signal is later confirmed at 24h).
    suffix = _series([0.01] * 200, prefix[-1].p, AS_OF + timedelta(hours=1), 60)
    return prefix + suffix


def _flat():
    prefix = _series([0.0] * 39, 0.50, AS_OF - timedelta(minutes=39 * 30), 30)
    suffix = _series([0.0] * 50, 0.50, AS_OF + timedelta(hours=1), 60)
    return prefix + suffix


def _too_short():
    prefix = _series([0.01] * 9, 0.40, AS_OF - timedelta(minutes=9 * 30), 30)
    suffix = _series([0.01] * 20, prefix[-1].p, AS_OF + timedelta(hours=1), 60)
    return prefix + suffix


def _ended_before_cutoff():
    # All history is before the cut-off: no forward data, so it cannot be evaluated.
    return _series([0.01] * 40, 0.30, AS_OF - timedelta(days=10), 30)


CANDS = [
    Candidate("mUp", "mUp-y", "Will the mover rise?", "Yes", 0.42),
    Candidate("mFlat", "mFlat-y", "Will the flat market move?", "Yes", 0.50),
    Candidate("mShort", "mShort-y", "Too short?", "Yes", 0.40),
    Candidate("mEnded", "mEnded-y", "Ended before cutoff?", "Yes", 0.60),
]
_HIST = {
    "mUp-y": _mover_up(),
    "mFlat-y": _flat(),
    "mShort-y": _too_short(),
    "mEnded-y": _ended_before_cutoff(),
}


async def _history_of(token_id):
    return _HIST.get(token_id, [])


async def test_screen_selects_mover_ranks_and_scores_forward():
    screen = await run_historical_screen(
        candidates=CANDS, history_of=_history_of, as_of=AS_OF, min_strength=0.1, top_n=15
    )
    # The flat market and the ended-before-cutoff market are not eligible; the too-short one
    # is skipped; only the genuine mover qualifies.
    markets = [e.market_id for e in screen.entries]
    assert markets == ["mUp"]
    top = screen.entries[0]
    assert top.rank == 1
    assert top.direction == "up"
    assert top.entry_price < 0.9  # entered at the real cut-off price, not a later one
    # It kept rising after the cut-off, so the 24h move confirms the up signal.
    assert top.direction_correct_24h is True
    fwd24 = next(f for f in top.forward if f.horizon == "24h")
    assert fwd24.price is not None and fwd24.price > top.entry_price
    assert screen.moved_expected_24h == 1
    assert screen.provenance_class == "reconstructed"
    assert "survivorship" in " ".join(screen.limitations).lower()


async def test_no_lookahead_entry_uses_only_pre_cutoff_price():
    # The entry price must equal the last pre-cutoff price, never a later one.
    screen = await run_historical_screen(
        candidates=CANDS, history_of=_history_of, as_of=AS_OF, min_strength=0.1
    )
    entry = screen.entries[0].entry_price
    # The entry must equal the last pre-cutoff point's price, never a later one.
    last_prefix = [p for p in _HIST["mUp-y"] if p.t <= AS_OF][-1].p
    assert entry == last_prefix
    # And it is strictly less than the final (later) price, proving no forward leakage.
    assert entry < screen.entries[0].final_price


async def test_flat_market_below_threshold_excluded():
    screen = await run_historical_screen(
        candidates=[CANDS[1]], history_of=_history_of, as_of=AS_OF, min_strength=0.1
    )
    assert screen.selected == 0
    assert screen.universe_considered == 1  # it was looked at, just not eligible


def _low_mover():
    # Same relative burst as the near-mid mover, but pinned near 0.02 at the cut-off so its
    # cut-off price is below the near-mid band, even though it drifts up afterwards.
    base = [0.0005 if i % 2 == 0 else -0.0005 for i in range(33)]
    burst = [0.004] * 6
    t0 = AS_OF - timedelta(minutes=39 * 30)
    prefix = _series(base + burst, 0.02, t0, 30)
    suffix = _series([0.01] * 100, prefix[-1].p, AS_OF + timedelta(hours=1), 60)
    return prefix + suffix


async def test_current_price_does_not_change_historical_selection():
    # The same near-mid-at-cut-off history, but pretend today's price is pinned at 0.001.
    # Selection must be unchanged: the near-mid gate reads the price at the cut-off, not now.
    cand = Candidate("mUp", "mUp-y", "Will the mover rise?", "Yes", gamma_price=0.001)

    async def hof(tok):
        return _mover_up() if tok == "mUp-y" else []

    screen = await run_historical_screen(
        candidates=[cand], history_of=hof, as_of=AS_OF, min_strength=0.1
    )
    assert [e.market_id for e in screen.entries] == ["mUp"]


async def test_pinned_at_cutoff_excluded_even_if_near_mid_or_moving_later():
    # Pinned near 0 at the cut-off (below the near-mid band) but with a real signal and a later
    # up-drift, and a current price of 0.5. It must be EXCLUDED: neither today's price nor the
    # later move can make a market that was pinned at the cut-off a candidate.
    cand = Candidate("mPin", "mPin-y", "Pinned at the cut-off?", "Yes", gamma_price=0.5)

    async def hof(tok):
        return _low_mover() if tok == "mPin-y" else []

    screen = await run_historical_screen(
        candidates=[cand], history_of=hof, as_of=AS_OF, min_strength=0.05
    )
    assert screen.selected == 0


async def test_top_n_caps_selection():
    # Five movers, top_n=3 keeps only the three strongest.
    cands = [Candidate(f"m{i}", f"m{i}-y", f"q{i}", "Yes", 0.4) for i in range(5)]
    hist = {f"m{i}-y": _mover_up() for i in range(5)}

    async def hof(tok):
        return hist.get(tok, [])

    screen = await run_historical_screen(
        candidates=cands, history_of=hof, as_of=AS_OF, min_strength=0.1, top_n=3
    )
    assert screen.selected == 3
    assert [e.rank for e in screen.entries] == [1, 2, 3]
