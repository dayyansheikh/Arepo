"""Encoded frame scope, decoded budgets and original-code selection recovery."""

import gzip
import json

import httpx
import pytest

from astrolabe.feature_store.capture import Budget, _digest, _json_bytes
from astrolabe.research_panel.frame import FrameRetryPolicy, GammaFrameRun, read_frame
from astrolabe.research_panel.original_reader import read_original_frame, read_original_selection
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_frame import body, market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, select, snapshot


def compress(raw):
    return gzip.compress(raw, mtime=0)


original_code = _original_code


def run(tmp_path, pages, *, limit=2, budget=None):
    requests = []

    def handler(request):
        assert request.headers["accept-encoding"] == "gzip"
        requests.append(dict(request.url.params))
        return httpx.Response(
            200,
            headers={"content-encoding": "gzip"},
            stream=Stream([compress(pages[len(requests) - 1])]),
        )

    item = GammaFrameRun(
        tmp_path.resolve() / "fs2_capture_encoded",
        limit=limit,
        transport=httpx.MockTransport(handler),
        reuse_connections=True,
        accept_gzip=True,
        budget=budget or Budget(requests=len(pages)),
    )
    return item, requests


async def test_encoded_cursor_frame_and_original_selection_recovery(tmp_path, original_code):
    pages = [body([market(1), market(2)], "opaque"), body([market(3)])]
    item, requests = run(tmp_path, pages)
    report = await item.collect()
    root = item.journal.root
    assert report["schema_version"] == "fs2-gamma-frame-v5"
    assert report["state"] == "exhausted_consistent"
    assert report["source_rows"] == 3
    assert requests[1]["after_cursor"] == "opaque"
    assert report["decoded_bytes"] == report["decoded_budget_charge"] == sum(map(len, pages))
    assert report["decoded_unavailable_attempts"] == 0
    assert report["raw_bytes"] == sum(len(compress(p)) for p in pages)
    before = snapshot(root)
    repo, commit = original_code
    proof = read_original_frame(
        root,
        implementation_commit=commit,
        repository=repo,
        output_root=tmp_path / "fs2_frame_read_gzip",
    )
    assert proof["report"] == report
    assert not proof["read_receipt"]["observation_clocks_changed"]
    selected = select(tmp_path, root, original_code)
    assert selected["counts"]["sampling_members"] == 3
    assert selected["plan"]["assignments"][0]["inclusion_probability"]["denominator"] == "3"
    selection = tmp_path / "fs2_selection_test"
    selection_before = snapshot(selection)
    recovered = read_original_selection(
        selection,
        implementation_commit=commit,
        repository=repo,
        output_root=tmp_path / "fs2_selection_read_gzip",
    )
    assert recovered["report"] == selected
    assert snapshot(root) == before and snapshot(selection) == selection_before


async def test_decoded_budget_stops_before_more_requests_even_when_wire_budget_remains(tmp_path):
    first = body([market(1)], "next")
    item, requests = run(
        tmp_path,
        [first, body([])],
        limit=1,
        budget=Budget(requests=2, bytes_per_response=len(first), total_bytes=len(first)),
    )
    report = await item.collect()
    assert len(requests) == 1 and report["raw_bytes"] < len(first)
    assert report["decoded_budget_charge"] == len(first)
    assert report["state"] == "incomplete" and report["stop_reason"] == "decoded_byte_budget"
    assert read_frame(item.journal.root) == report


async def test_frame_refuses_rehashed_decoded_budget_lineage(tmp_path):
    item, _ = run(tmp_path, [body([market(1), market(2)], "a"), body([])])
    report = await item.collect()
    folder = item.journal.root / report["pages"][1]["capture_id"]
    receipt = json.loads((folder / "receipt.json").read_bytes())
    receipt["decoded_budget_before"] += 1
    # Limit remains per-response; this is internally valid but fails global reconciliation.
    data = _json_bytes(receipt)
    (folder / "receipt.json").write_bytes(data)
    ack = json.loads((folder / "raw_ack.json").read_bytes())
    ack["receipt_hash"] = _digest(data)
    raw_ack_bytes = _json_bytes(ack)
    (folder / "raw_ack.json").write_bytes(raw_ack_bytes)
    parsed_ack = json.loads((folder / "parsed_ack.json").read_bytes())
    parsed_ack["raw_ack_hash"] = _digest(raw_ack_bytes)
    parsed_bytes = _json_bytes(parsed_ack)
    (folder / "parsed_ack.json").write_bytes(parsed_bytes)
    amend(folder, "frame_page", lambda p: p.update(receipt_hash=ack["receipt_hash"]))
    with pytest.raises(ValueError, match="decoded budget lineage"):
        read_frame(item.journal.root)


async def test_legacy_frame_cannot_hide_encoded_transport(tmp_path):
    item, _ = run(tmp_path, [body([])])
    await item.collect()
    amend(
        item.journal.root, "frame_policy", lambda p: p.update(schema_version="fs2-gamma-frame-v4")
    )
    with pytest.raises(ValueError, match="payload policy"):
        read_frame(item.journal.root)


async def test_malformed_gzip_is_a_retained_failed_frame_not_a_retryable_empty_page(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, stream=Stream([b"invalid gzip"])
        )

    item = GammaFrameRun(
        tmp_path.resolve() / "fs2_capture_bad_gzip",
        limit=2,
        budget=Budget(requests=2),
        retry_policy=FrameRetryPolicy(),
        reuse_connections=True,
        accept_gzip=True,
        transport=httpx.MockTransport(handler),
    )
    report = await item.collect()
    assert len(requests) == 1
    assert report["state"] == "incomplete" and report["stop_reason"] == "page_error"
    assert report["errors"] == ["invalid_content_encoding"]
    assert report["decoded_bytes"] == 0 and report["decoded_unavailable_attempts"] == 1
    assert report["decoded_budget_charge"] == item.journal.budget.bytes_per_response
    assert read_frame(item.journal.root) == report
