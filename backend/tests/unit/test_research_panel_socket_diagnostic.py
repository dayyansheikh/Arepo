"""Fixed diagnostic orchestration never chases a target or promotes loopback evidence."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from websockets.asyncio.server import serve

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel import socket_diagnostic as module
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_window_coverage import CONDITION, book

original_code = _original_code


def output(tmp_path):
    return tmp_path / "fs2_socket_diagnostic_test"


def transport(requests, *, closed=False, fail=False, cancel=False):
    async def handler(request):
        requests.append(str(request.url))
        if cancel:
            raise asyncio.CancelledError()
        gamma = request.url.path.startswith("/markets/")
        payload = {
            "id": module.MARKET,
            "conditionId": CONDITION,
            "outcomes": ["Yes", "No"],
            "clobTokenIds": [module.TOKEN, "2"],
            "description": "Rules",
            "active": True,
            "closed": closed,
            "archived": False,
            "acceptingOrders": not closed,
        }
        return httpx.Response(
            503 if fail else 200,
            stream=Stream([json.dumps(payload if gamma else book(asset_id=module.TOKEN)).encode()]),
        )

    return httpx.MockTransport(handler)


async def run(tmp_path, original_code, source, port):
    return await module.run_loopback_diagnostic(
        output(tmp_path),
        implementation_commit=original_code[1],
        repository=original_code[0],
        transport=source,
        port=port,
        duration_ms=200,
    )


async def test_fixed_chain_and_original_recovery_precede_final_report(tmp_path, original_code):
    requests = []

    async def handler(socket):
        subscription = json.loads(await socket.recv())
        assert subscription == {"assets_ids": [module.TOKEN], "type": "market"}
        await socket.send(json.dumps(book(asset_id=module.TOKEN)))
        await socket.wait_closed()

    async with serve(handler, "127.0.0.1", 0) as server:
        result = await run(
            tmp_path, original_code, transport(requests), server.sockets[0].getsockname()[1]
        )
    assert len(requests) == 4 and requests[:2] == requests[2:]
    assert all(module.MARKET in u or module.TOKEN in u for u in requests)
    assert set(result["recovery"]) == {"pre", "socket", "post", "analysis"}
    assert not result["accepted_panel"]
    for receipt in result["recovery"].values():
        assert receipt["original_provenance_class"] == "synthetic"
        assert not receipt["observation_clocks_changed"]
        assert _ordered_clocks(receipt["completed_at"], result["reported_at"])
    before = snapshot(output(tmp_path))
    with pytest.raises(FileExistsError):
        await run(tmp_path, original_code, transport(requests), 1)
    assert snapshot(output(tmp_path)) == before and len(requests) == 4


@pytest.mark.parametrize("kwargs", [{"closed": True}, {"fail": True}])
async def test_unavailable_prior_stops_without_socket_post_or_alternate(
    tmp_path, original_code, kwargs
):
    requests = []
    result = await run(tmp_path, original_code, transport(requests, **kwargs), 1)
    assert len(requests) == 2 and set(result["recovery"]) == {"pre"}
    assert result["summaries"]["socket_not_attempted"] == "prior_snapshot_unavailable"
    assert not (output(tmp_path) / "fs2_socket_window_fixed").exists()
    assert not (output(tmp_path) / "fs2_capture_post").exists()


async def test_cancelled_source_retains_failure_and_never_restarts(tmp_path, original_code):
    requests = []
    with pytest.raises(asyncio.CancelledError):
        await run(tmp_path, original_code, transport(requests, cancel=True), 1)
    assert len(requests) == 1
    failure, _ = _pair(output(tmp_path), "diagnostic_failure")
    assert failure["stage"] == "pre_sources" and failure["exception_type"] == "CancelledError"
    assert not (output(tmp_path) / "diagnostic_report.json").exists()
    with pytest.raises(FileExistsError):
        await run(tmp_path, original_code, transport(requests), 1)


async def test_capacity_and_uncommitted_code_refuse_before_requests(
    tmp_path, original_code, monkeypatch
):
    requests = []
    source = transport(requests)
    with monkeypatch.context() as patch:
        patch.setattr(module.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
        with pytest.raises(ValueError, match="reservation"):
            await run(tmp_path, original_code, source, 1)
    assert not output(tmp_path).exists()
    with pytest.raises(ValueError, match="Git"):
        await run(tmp_path, (original_code[0], "0" * 40), source, 1)
    assert not output(tmp_path).exists() and requests == []
