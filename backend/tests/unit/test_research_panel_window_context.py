"""Process-owned window proof, bounded seals and unchanged cold recovery."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

import httpx
import pytest
from websockets.asyncio.server import serve

from astrolabe.feature_store.capture import Budget
from astrolabe.feature_store.source_run import SourceRun
from astrolabe.research_panel import owned_windows as windows
from astrolabe.research_panel import screening_worker as worker
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.build_identity import verified_panel_build
from astrolabe.research_panel.panel_declaration import read_panel_declaration
from astrolabe.research_panel.panel_selection import selection_root
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.screening import ScreeningPolicy, _prepare_owned_screening
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_input_read import rewrite
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_owned_pilot import transport
from tests.unit.test_research_panel_owned_windows import config, setup

original_code = _original_code


async def owned(tmp_path, code, *, missing=True):
    _, panel, rows = await setup(tmp_path, code)
    root = worker.worker_root(panel)
    root.mkdir()
    worker._save(root, 'worker_policy', {
        'schema_version': windows.VERSION, 'build': verified_panel_build(),
        'panel_root': str(panel), 'provenance_class': 'synthetic',
        'window_policy': asdict(config()), 'window_port': 1,
        'reservation': worker.allocation(read_panel_declaration(panel), windows=True),
    })
    frozen, _ = _prepare_owned_screening(selection_root(panel),
        output_root=root / 'fs2_screening_batch', rule=SnapshotTriggerPolicy(1, 3, 120000),
        policy=ScreeningPolicy(120, 120))
    source, _ = transport(rows)

    async def unavailable(request):
        if missing and request.url.path == '/book':
            return httpx.Response(404, stream=Stream([b'{"error":"no book"}']))
        return await source.handle_async_request(request)

    for i, item in enumerate(frozen['selected']):
        run = SourceRun(root / f'fs2_capture_screen_{i:03d}',
            transport=httpx.MockTransport(unavailable),
            budget=Budget(requests=2, bytes_per_response=1048576, total_bytes=2097152,
                          seconds_per_request=15, total_seconds=60),
            policy_version='receipt-time-selected-market-v1', retained_bytes=4 * 1048576)
        await run.fetch('gamma.market', {'market_id': item['member']['market_id']})
        await run.fetch('clob.book', {'token_id': item['member']['token_id']})
        record_book_computation(root / f'fs2_capture_screen_{i:03d}',
                                output_root=Path(item['book_root']),
                                policy=QuoteInputPolicy(120, 120))
    return root, frozen['selected']


async def test_owned_context_cold_equality_slots_and_private_assignments(tmp_path, original_code):
    root, selected = await owned(tmp_path, original_code)
    acquire, finish = windows._prepare(root, selected, 'synthetic')
    with pytest.raises(ValueError, match='incomplete'):
        finish()
    with pytest.raises(ValueError, match='slot'):
        acquire(True)
    await asyncio.to_thread(acquire, 0)
    with pytest.raises(ValueError, match='claimed'):
        acquire(0)
    original = selected[1]['member']['market_id']
    selected[1]['member']['market_id'] = 'substituted'
    await asyncio.to_thread(acquire, 1)
    selected[1]['member']['market_id'] = original
    assert finish() == windows.read(root, selected, 'synthetic')
    with pytest.raises(ValueError, match='consumed'):
        finish()
    with pytest.raises(ValueError, match='slot'):
        acquire(0)
    with pytest.raises(ValueError, match='lineage'):
        windows._prepare(root, selected, 'prospective')
    selected[0]['book_root'] = selected[1]['book_root']
    substituted, _ = windows._prepare(root, selected, 'synthetic')
    with pytest.raises(ValueError, match='source substituted'):
        substituted(0)


@pytest.mark.parametrize('change', ['raw', 'metadata', 'added', 'removed', 'symlink', 'policy',
                                   'unexpected_window'])
async def test_owned_context_refuses_changed_evidence(tmp_path, original_code, change):
    root, selected = await owned(tmp_path, original_code)
    acquire, finish = windows._prepare(root, selected, 'synthetic')
    await asyncio.gather(*(asyncio.to_thread(acquire, i) for i in range(2)))
    source = root / 'fs2_capture_screen_000'
    raw = next(source.rglob('*.bin'))
    if change == 'raw':
        raw.write_bytes(raw.read_bytes() + b'x')
    elif change == 'metadata':
        rewrite(root, 'window_000', lambda p: p.update(missing_reason='invented'))
    elif change == 'added':
        (source / 'extra').write_bytes(b'x')
    elif change == 'removed':
        raw.unlink()
    elif change == 'symlink':
        (source / 'link').symlink_to(raw)
    elif change == 'policy':
        rewrite(root, 'worker_policy', lambda p: p.update(window_port=2))
    else:
        (root / 'fs2_socket_window_000').mkdir()
    with pytest.raises((ValueError, FileNotFoundError)):
        finish()


def test_manifest_bounds_directory_closure_and_symlinks(tmp_path):
    root = tmp_path / 'evidence'
    root.mkdir()
    (root / 'raw').write_bytes(b'1234')
    sealed = windows._manifest((root,), 4)
    assert windows._manifest((root,), 4) == sealed
    with pytest.raises(ValueError, match='byte bound'):
        windows._manifest((root,), 3)
    (root / 'empty').mkdir()
    assert windows._manifest((root,), 4) != sealed
    (root / 'link').symlink_to(root / 'raw')
    with pytest.raises(ValueError):
        windows._manifest((root,), 4)


def test_manifest_count_bound(tmp_path):
    for i in range(3456):
        (tmp_path / str(i)).touch()
    with pytest.raises(ValueError, match='count bound'):
        windows._manifest((tmp_path,), 0)


@pytest.mark.parametrize('change', ['socket_raw', 'analysis_facts'])
async def test_mutation_between_writer_return_and_proof_refused(tmp_path, original_code, change):
    root, selected = await owned(tmp_path, original_code, missing=False)
    item = selected[0]

    async def handle(socket):
        token = json.loads(await socket.recv())['assets_ids'][0]
        await socket.send(json.dumps({'event_type': 'book', 'asset_id': token,
            'market': item['identity']['condition_id'], 'bids': [{'price': '0.4', 'size': '2'}],
            'asks': [{'price': '0.6', 'size': '1'}]}))
        await socket.wait_closed()

    changed = []

    def observe(frame, event, arg):
        if event == 'return' and frame.f_code is windows.collect.__code__ and arg is not None:
            socket, analysis = windows.paths(root, 0)
            if change == 'socket_raw':
                raw = next(socket.glob('*.bin'))
                raw.write_bytes(raw.read_bytes() + b'x')
            else:
                rewrite(analysis, 'socket_analysis_facts',
                        lambda p: p['projection'].update(state='invented'))
            changed.append(change)

    async with serve(handle, '127.0.0.1', 0) as server:
        rewrite(root, 'worker_policy',
                lambda p: p.update(window_port=server.sockets[0].getsockname()[1]))
        acquire, _ = windows._prepare(root, selected, 'synthetic')
        previous = threading.getprofile()
        threading.setprofile(observe)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                with pytest.raises(ValueError, match='socket changed|actual writer results'):
                    await asyncio.get_running_loop().run_in_executor(pool, acquire, 0)
        finally:
            threading.setprofile(previous)
    assert changed == [change]
