"""Measured negative decisions require fresh authenticated evidence under a prior rule."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from astrolabe.feature_store.source_run import _ordered_clocks, _pair
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.original_reader import read_original_trigger_computation
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.trigger_computation import (
    CHILD,
    SnapshotTriggerPolicy,
    declare_snapshot_trigger,
    read_snapshot_trigger,
    record_snapshot_trigger,
)
from tests.unit.test_research_panel_bound_window import pre
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_window_reconciliation import post

original_code = _original_code


def parent(tmp_path):
    return tmp_path / "fs2_trigger_declaration_test"


def declare(tmp_path, numerator=1, denominator=2, age=60000):
    return declare_snapshot_trigger(
        parent(tmp_path),
        book_root=tmp_path / "fs2_book_computation_post",
        market_id="10",
        token_id="1",
        policy=SnapshotTriggerPolicy(numerator, denominator, age),
    )


def facts(tmp_path):
    return _pair(parent(tmp_path) / CHILD, "trigger_computation_facts")[0]


@pytest.mark.parametrize(
    "n,d,bid,state,signed",
    [
        (1, 3, "2", "triggered", "1"),
        (1, 4, "2", "triggered", "1"),
        (1, 2, "2", "untriggered", "1"),
        (1, 3, "0.5", "triggered", "-1"),
    ],
)
async def test_exact_boundary_sign_and_measured_negative(tmp_path, n, d, bid, state, signed):
    declaration_ack = declare(tmp_path, n, d)
    source, book = await post(tmp_path, bid=bid)
    before = snapshot(source), snapshot(book)
    result = record_snapshot_trigger(parent(tmp_path))
    saved = facts(tmp_path)
    assert result["state"] == state and result["source_provenance_class"] == "synthetic"
    assert saved["projection"]["signed_imbalance"]["numerator"] == signed
    assert saved["projection"]["signed_imbalance"]["denominator"] == "3"
    assert _ordered_clocks(
        declaration_ack["durable_ack"],
        saved["projection"]["input_window_start"],
        saved["projection"]["input_window_end"],
        result["computation_started_at"],
        result["computed_at"],
        result["computation_available_at"],
    )
    assert read_snapshot_trigger(parent(tmp_path) / CHILD) == result
    assert before == (snapshot(source), snapshot(book))
    with pytest.raises(FileExistsError):
        record_snapshot_trigger(parent(tmp_path))


@pytest.mark.parametrize(
    "kwargs,age",
    [
        ({"closed": True}, 60000),
        ({"gamma_status": 503}, 60000),
        ({"omit_book": True}, 60000),
        ({"market": "11"}, 60000),
        ({}, 0),
    ],
)
async def test_unavailable_is_never_a_measured_control(tmp_path, kwargs, age):
    declare(tmp_path, age=age)
    await post(tmp_path, **kwargs)
    result = record_snapshot_trigger(parent(tmp_path))
    assert result["state"] == "unavailable"
    projection = facts(tmp_path)["projection"]
    assert projection["reasons"] and projection["signed_imbalance"] is None
    assert projection["absolute_minus_threshold"] is None


async def test_old_source_cannot_become_a_predeclared_assessment(tmp_path):
    source, _ = await pre(tmp_path)
    declare(tmp_path)
    record_book_computation(
        source, output_root=tmp_path / "fs2_book_computation_post", policy=QuoteInputPolicy(60, 60)
    )
    with pytest.raises(ValueError, match="preceded"):
        record_snapshot_trigger(parent(tmp_path))
    assert (parent(tmp_path) / CHILD / "trigger_failure_ack.json").exists()


@pytest.mark.parametrize("change", ["raw", "result", "clock"])
async def test_resealed_decision_and_source_corruption_refused(tmp_path, change):
    declare(tmp_path)
    source, _ = await post(tmp_path)
    record_snapshot_trigger(parent(tmp_path))
    root = parent(tmp_path) / CHILD
    if change == "raw":
        next(source.glob("*/raw.bin")).write_bytes(b"bad")
    elif change == "result":
        rewrite(
            root, "trigger_computation_facts", lambda p: p["projection"].update(state="triggered")
        )
    else:
        declaration, _ = _pair(parent(tmp_path), "trigger_declaration")
        rewrite(
            root,
            "trigger_computation_facts",
            lambda p: p.update(computed_at=declaration["declared_at"]),
        )
    before = snapshot(parent(tmp_path)), snapshot(source)
    with pytest.raises(ValueError):
        read_snapshot_trigger(root)
    assert before == (snapshot(parent(tmp_path)), snapshot(source))


async def test_exclusive_writer_and_terminal_cancelled_input(tmp_path, monkeypatch):
    declare(tmp_path)
    await post(tmp_path)

    def attempt():
        try:
            return record_snapshot_trigger(parent(tmp_path))
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert len([r for r in results if r]) == 1
    other = tmp_path / "other"
    other.mkdir()
    declare(other)
    await post(other)
    original = Path.open

    def cancel(path, *args, **kwargs):
        if path.name == "trigger_input_ack.json":
            raise asyncio.CancelledError()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", cancel)
    with pytest.raises(asyncio.CancelledError):
        record_snapshot_trigger(parent(other))
    assert (parent(other) / CHILD / "trigger_input.json").exists()
    with pytest.raises(ValueError, match="closure"):
        read_snapshot_trigger(parent(other) / CHILD)


async def test_original_full_facts_clocks_and_transitive_root_protection(tmp_path, original_code):
    declare(tmp_path)
    source, book = await post(tmp_path)
    summary = record_snapshot_trigger(parent(tmp_path))
    root = parent(tmp_path) / CHILD
    before = tuple(snapshot(p) for p in (parent(tmp_path), source, book))
    result = read_original_trigger_computation(
        root,
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_trigger_computation_read_test",
    )
    assert result["report"] == {"summary": summary, "facts": facts(tmp_path)}
    assert not result["read_receipt"]["observation_clocks_changed"]
    for dependency in (parent(tmp_path), root, source, book):
        with pytest.raises(ValueError, match="separate"):
            read_original_trigger_computation(
                root,
                implementation_commit=original_code[1],
                repository=original_code[0],
                output_root=dependency / "fs2_trigger_computation_read_bad",
            )
    assert before == tuple(snapshot(p) for p in (parent(tmp_path), source, book))


async def test_inflight_request_before_declaration_cannot_be_saved_as_later_evidence(tmp_path):
    started, release = asyncio.Event(), asyncio.Event()
    pending = asyncio.create_task(post(tmp_path, gamma_gate=(started, release)))
    await started.wait()
    declare(tmp_path)
    release.set()
    await pending
    with pytest.raises(ValueError, match="preceded"):
        record_snapshot_trigger(parent(tmp_path))
    assert (parent(tmp_path) / CHILD / "trigger_failure_ack.json").exists()
