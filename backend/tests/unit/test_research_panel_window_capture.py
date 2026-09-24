"""Bounded synthetic raw windows: actual clocks, unavailable continuity and preservation."""

import asyncio
from pathlib import Path

import pytest

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel import window_journal as journal
from astrolabe.research_panel.window_capture import SyntheticWindowFeed, capture_window
from astrolabe.research_panel.window_journal import LIMITS, read_window
from tests.unit.test_research_panel_input_read import rewrite, snapshot


def output(tmp_path):
    return tmp_path.resolve() / 'fs2_window_test'


async def capture(tmp_path, frames=(), *, disconnect=True, duration=500):
    return await capture_window(output(tmp_path), token_id='1', condition_id='condition',
                                feed=SyntheticWindowFeed(frames, disconnect), duration_ms=duration)


async def test_raw_binary_text_controls_arrays_and_invalid_frames_are_not_lost(tmp_path):
    wire = ('PONG', '[{"event_type":"book"}]', b'\xff\x00', '{bad json')
    report = await capture(tmp_path, tuple((0, raw) for raw in wire))
    assert report['frame_count'] == 4 and report['state'] == 'incomplete'
    assert report['terminal'] == 'disconnected'
    assert report['provenance_class'] == 'synthetic'
    assert report['complete_continuous_history'] is report['origin_admitted'] is False
    root = output(tmp_path)
    declaration, pa = _pair(root, 'window_policy')
    clocks = [declaration['declared_at'], pa['durable_ack']]
    found = []
    for index in range(1, report['event_count'] + 1):
        name = f'event_{index:06d}'
        event, ack = _pair(root, name)
        clocks += [event['observed_at'], ack['durable_ack']]
        if event['kind'] == 'received':
            found.append((root / (name + '.bin')).read_bytes())
    assert found == [raw.encode() if isinstance(raw, str) else raw for raw in wire]
    assert _ordered_clocks(*clocks, report['window_available_at'])
    before = snapshot(root)
    assert read_window(root) == report
    assert snapshot(root) == before
    with pytest.raises(FileExistsError):
        await capture(tmp_path)


async def test_no_messages_completes_only_actual_duration_not_continuity(tmp_path):
    report = await capture(tmp_path, disconnect=False, duration=30)
    assert report['state'] == 'duration_completed' and report['frame_count'] == 0
    assert int(report['elapsed_ns']) >= 30000000
    assert not report['complete_continuous_history']


async def test_heartbeat_fixed_schedule_is_saved_without_cancelling_receive(tmp_path):
    report = await capture(tmp_path, ((10200, 'PONG'),), disconnect=False, duration=10500)
    kinds = [_pair(output(tmp_path), f'event_{i:06d}')[0]['kind']
             for i in range(1, report['event_count'] + 1)]
    assert kinds.count('ping_intent') == kinds.count('ping_sent') == 1
    assert kinds.index('ping_sent') < kinds.index('received')
    assert report['frame_count'] == 1 and int(report['elapsed_ns']) >= 10500000000


async def test_truncated_raw_has_full_observed_size_hash_and_stops(tmp_path):
    raw = b'x' * (LIMITS['max_frame_bytes'] + 1)
    report = await capture(tmp_path, ((0, raw),))
    event, _ = _pair(output(tmp_path), 'event_000004')
    assert event['truncated'] and event['received_bytes'] == len(raw)
    assert event['raw_bytes'] == len(raw) - 1
    assert event['received_hash'] != event['raw_hash']
    assert report['terminal'] == 'budget_stop' and report['frame_count'] == 1


@pytest.mark.parametrize('change', ['raw', 'clock', 'ordinal', 'admission', 'duration',
                                   'heartbeat', 'extra', 'symlink'])
async def test_resealed_semantic_or_raw_corruption_fails_without_repair(tmp_path, change):
    await capture(tmp_path, ((0, 'PONG'),))
    root = output(tmp_path)
    if change == 'raw':
        (root / 'event_000004.bin').write_bytes(b'bad')
    elif change == 'clock':
        policy, _ = _pair(root, 'window_policy')
        rewrite(root, 'event_000004', lambda p: p.update(observed_at=policy['declared_at']))
    elif change == 'ordinal':
        rewrite(root, 'event_000004', lambda p: p.update(ordinal=9))
    elif change == 'admission':
        rewrite(root, 'window_report', lambda p: p.update(origin_admitted=True))
    elif change == 'duration':
        rewrite(root, 'window_report', lambda p: p.update(elapsed_ns='0'))
    elif change == 'heartbeat':
        rewrite(root, 'event_000004', lambda p: p.update(kind='ping_sent'))
    elif change == 'extra':
        (root / 'unexpected.json').write_text('{}')
    else:
        (root / 'link').symlink_to(root / 'window_report.json')
    before = snapshot(root)
    with pytest.raises(ValueError):
        read_window(root)
    assert snapshot(root) == before


async def test_cancellation_retains_raw_and_is_terminal(tmp_path):
    task = asyncio.create_task(capture(tmp_path, ((0, 'raw before cancellation'),),
                                      disconnect=False, duration=60000))
    root = output(tmp_path)
    for _ in range(200):
        if (root / 'event_000004_ack.json').exists():
            break
        await asyncio.sleep(.005)
    assert (root / 'event_000004.bin').exists()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (root / 'window_failure_ack.json').exists()
    assert not (root / 'window_report.json').exists()
    with pytest.raises(FileExistsError):
        await capture(tmp_path)


async def test_torn_ack_retains_raw_without_sealed_report(tmp_path, monkeypatch):
    original = Path.open
    def fail(path, *args, **kwargs):
        if path.name == 'event_000004_ack.json':
            raise OSError('synthetic disk failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError):
        await capture(tmp_path, ((0, 'raw'),))
    root = output(tmp_path)
    assert (root / 'event_000004.bin').read_bytes() == b'raw'
    assert (root / 'window_failure_ack.json').exists()
    assert not (root / 'window_report.json').exists()


async def test_single_concurrent_owner_and_no_caller_clock_or_live_transport(tmp_path):
    results = await asyncio.gather(capture(tmp_path), capture(tmp_path), return_exceptions=True)
    assert sum(isinstance(r, FileExistsError) for r in results) == 1
    assert sum(isinstance(r, dict) for r in results) == 1
    with pytest.raises(ValueError, match='live window transport closed'):
        await capture_window(output(tmp_path), token_id='1', condition_id='x', feed=None)
    with pytest.raises(TypeError):
        await capture_window(output(tmp_path), token_id='1', condition_id='x',
                             feed=SyntheticWindowFeed(()), clock=None)


async def test_capacity_refusal_precedes_directory_creation(tmp_path, monkeypatch):
    disk = journal.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(journal.shutil, 'disk_usage', lambda p:
                        disk._replace(free=LIMITS['free_reserve_bytes']))
    with pytest.raises(ValueError, match='storage reserve'):
        await capture(tmp_path)
    assert not output(tmp_path).exists()


@pytest.mark.parametrize('frames', [[(0, 'x')], ((True, 'x'),), ((-1, 'x'),),
                                     ((0, {}),), ((60001, 'x'),)])
def test_invalid_synthetic_allocations_refused(frames):
    with pytest.raises(ValueError):
        SyntheticWindowFeed(frames)


async def test_frame_cap_is_explicit_and_retains_every_consumed_frame(tmp_path, monkeypatch):
    # Instrument a smaller declared synthetic budget; production defaults stay unchanged.
    monkeypatch.setitem(LIMITS, 'max_frames', 3)
    report = await capture(tmp_path, tuple((0, str(i)) for i in range(4)))
    assert report['terminal'] == 'budget_stop' and report['frame_count'] == 3
    assert read_window(output(tmp_path)) == report


async def test_raw_total_cap_preserves_partial_final_frame(tmp_path, monkeypatch):
    # Subscription bytes also count; preserve an explicit prefix and incomplete terminal.
    monkeypatch.setitem(LIMITS, 'max_raw_bytes', 60)
    report = await capture(tmp_path, ((0, b'x' * 100),))
    assert report['retained_raw_bytes'] == 60 and report['terminal'] == 'budget_stop'
    event, _ = _pair(output(tmp_path), 'event_000004')
    assert event['truncated'] and 0 < event['raw_bytes'] < 100


async def test_replay_never_samples_new_observation_clocks(tmp_path, monkeypatch):
    report = await capture(tmp_path, ((0, 'PONG'),))
    monkeypatch.setattr(journal, '_clock', lambda: (_ for _ in ()).throw(
        AssertionError('new observation clock')))
    assert read_window(output(tmp_path)) == report
