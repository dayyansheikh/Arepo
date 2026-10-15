"""One fixed-target development diagnostic; never a panel, scheduler or admission path."""

import argparse
import asyncio
import json
import resource
import shutil
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import httpx

from astrolabe.feature_store.capture import Budget, _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_run import SourceRun, _pair, _persist

from .book_computation import read_book_computation, record_book_computation
from .bound_window import WindowBindingPolicy
from .build_identity import verified_panel_build
from .input_read import _canonical
from .original_reader import (
    _extract,
    read_original_book_computation,
    read_original_socket_analysis,
    read_original_socket_window,
)
from .quote_inputs import QuoteInputPolicy
from .socket_analysis import read_socket_analysis, record_socket_analysis
from .socket_window import capture_loopback_socket, capture_market_socket
from .socket_window_journal import read_socket_window
from .window_reconciliation import WindowReconciliationPolicy

MARKET = "1068745"
TOKEN = "71990823545476172057397539228999083435242402644332688321711165550800328090716"
VERSION = "fs2-fixed-socket-diagnostic-v1"
LIMITS = {
    "retained_bytes": 512 * 1048576,
    "free_reserve_bytes": 2 * 1024**3,
    "metadata_bytes": 262144,
    "max_files": 4096,
    "max_seconds": 1500,
    "acquisition_seconds": 180,
    "source_retained_bytes": 16 * 1048576,
}
BUDGET = Budget(
    requests=2,
    bytes_per_response=262144,
    total_bytes=524288,
    seconds_per_request=15,
    total_seconds=60,
)


def _size(root):
    total = files = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("diagnostic symlink refused")
        if path.is_file():
            files += 1
            total += path.stat().st_size
        elif not path.is_dir():
            raise ValueError("diagnostic nonregular file refused")
        if files > LIMITS["max_files"] or total > LIMITS["retained_bytes"]:
            raise ValueError("diagnostic retained budget exceeded")
    return total


def _check(root, started, *, acquisition=False):
    if time.monotonic() - started > LIMITS["acquisition_seconds" if acquisition else "max_seconds"]:
        raise ValueError("diagnostic stage deadline exceeded")
    retained = _size(root)
    if shutil.disk_usage(root).free < LIMITS["free_reserve_bytes"] + (
        LIMITS["retained_bytes"] - retained
    ):
        raise ValueError("remaining diagnostic reservation unavailable")
    return retained


def _save(root, name, value):
    if len(_json_bytes(value)) > LIMITS["metadata_bytes"]:
        raise ValueError("diagnostic metadata budget exceeded")
    _persist(root, name, value)


async def run_socket_diagnostic(output_root, *, implementation_commit):
    """Public fixed target only; no caller source, duration or identity substitutions."""
    return await _run(output_root, implementation_commit, None, None, 60000, None)


async def run_loopback_diagnostic(
    output_root, *, implementation_commit, transport, port, duration_ms=500, repository=None
):
    """Explicit synthetic HTTP fixtures plus an actual local socket, never public transport."""
    if (
        type(transport) is not httpx.MockTransport
        or type(port) is not int
        or not 1 <= port <= 65535
    ):
        raise ValueError("explicit mock HTTP and numeric loopback socket required")
    if type(duration_ms) is not int or not 1 <= duration_ms <= 60000:
        raise ValueError("bounded synthetic duration required")
    return await _run(output_root, implementation_commit, transport, port, duration_ms, repository)


async def _run(output_root, commit, transport, port, duration, repository):
    root = _canonical(output_root)
    repository = _canonical(repository or Path(__file__).parents[3])
    if not root.name.startswith("fs2_socket_diagnostic_"):
        raise ValueError("fresh diagnostic output required")
    if root.exists():
        raise FileExistsError("diagnostic terminal; never overwrite or resume")
    if (
        shutil.disk_usage(root.parent).free
        < LIMITS["retained_bytes"] + LIMITS["free_reserve_bytes"]
    ):
        raise ValueError("full diagnostic storage reservation unavailable")
    build = verified_panel_build()
    # Verify the complete loaded source/panel package against Git before any public request.
    with tempfile.TemporaryDirectory(prefix="arepo_diagnostic_code_check_") as tmp:
        _extract(repository, commit, build, Path(tmp))
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    started, started_ns, stage = time.monotonic(), time.monotonic_ns(), "declaration"
    summaries, recovery = {}, {}
    try:
        _save(
            root,
            "diagnostic_policy",
            {
                "schema_version": VERSION,
                "declared_at": _clock(),
                "build": build,
                "implementation_commit": commit,
                "limits": dict(LIMITS),
                "market_id": MARKET,
                "token_id": TOKEN,
                "duration_ms": duration,
                "provenance_class": "synthetic" if transport is not None else "prospective",
                "http_budget_per_pair": asdict(BUDGET),
                "quote_policy": asdict(QuoteInputPolicy(60, 60)),
                "binding_policy": asdict(WindowBindingPolicy(60000, 60000)),
                "analysis_policy": asdict(WindowReconciliationPolicy(60000, 60000, 1000)),
                "no_retry_or_alternate_target": True,
                "source_policy_version": "receipt-time-selected-market-v1",
                "purpose": "fixed development diagnostic; no representative panel or edge claim",
            },
        )
        _, pa = _pair(root, "diagnostic_policy")

        def step(name, *, acquisition=False):
            nonlocal stage
            _check(root, started, acquisition=acquisition)
            if verified_panel_build() != build:
                raise ValueError("diagnostic build changed")
            stage = name
            _save(root, "intent_" + name, {"at": _clock(), "policy_hash": pa["payload_hash"]})

        async def pair(label):
            source = root / ("fs2_capture_" + label)
            computation = root / ("fs2_book_computation_" + label)
            step(label + "_sources", acquisition=True)
            run = SourceRun(
                source,
                transport=transport,
                budget=BUDGET,
                policy_version="receipt-time-selected-market-v1",
                retained_bytes=LIMITS["source_retained_bytes"],
            )
            await run.fetch("gamma.market", {"market_id": MARKET})
            _check(root, started, acquisition=True)
            await run.fetch("clob.book", {"token_id": TOKEN})
            step(label + "_computation")
            summaries[label] = record_book_computation(
                source, output_root=computation, policy=QuoteInputPolicy(60, 60)
            )
            return computation

        pre = await pair("pre")
        socket = root / "fs2_socket_window_fixed"
        analysis = root / "fs2_socket_analysis_fixed"
        post = None
        # No socket or post requests for a closed, failed or otherwise unusable prior snapshot.
        if summaries["pre"]["snapshot_states"] == {"observed": 1}:
            step("socket", acquisition=True)
            args = {
                "output_root": socket,
                "policy": WindowBindingPolicy(60000, 60000),
                "duration_ms": duration,
            }
            summaries["socket"] = (
                await capture_market_socket(pre, **args)
                if port is None
                else await capture_loopback_socket(pre, port=port, **args)
            )
            if (
                summaries["socket"]["subscription_sent_at"] is not None
                and summaries["socket"]["identity_fresh_at_subscription_completion"]
            ):
                post = await pair("post")
            step("analysis")
            summaries["analysis"] = record_socket_analysis(
                socket,
                post_root=post,
                output_root=analysis,
                policy=WindowReconciliationPolicy(60000, 60000, 1000),
            )
        else:
            summaries["socket_not_attempted"] = "prior_snapshot_unavailable"

        children = [("pre", pre, read_book_computation, read_original_book_computation)]
        if "socket" in summaries:
            children += [
                ("socket", socket, read_socket_window, read_original_socket_window),
                ("analysis", analysis, read_socket_analysis, read_original_socket_analysis),
            ]
        if post is not None:
            children.append(("post", post, read_book_computation, read_original_book_computation))
        for label, child, reader, original in children:
            step("recovery_" + label)
            if reader(child) != summaries[label]:
                raise ValueError("independent diagnostic replay differs")
            kind = {
                "pre": "book_computation",
                "post": "book_computation",
                "socket": "socket_window",
                "analysis": "socket_analysis",
            }[label]
            result = original(
                child,
                implementation_commit=commit,
                repository=repository,
                output_root=root / ("fs2_" + kind + "_read_" + label),
            )
            recovery[label] = result["read_receipt"]
        retained = _check(root, started)
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result = {
            "schema_version": VERSION,
            "policy_hash": pa["payload_hash"],
            "reported_at": _clock(),
            "summaries": summaries,
            "recovery": recovery,
            "elapsed_ns": str(time.monotonic_ns() - started_ns),
            "parent_peak_resident_bytes": peak if sys.platform == "darwin" else peak * 1024,
            "retained_bytes_before_report": retained,
            "state": "completed_with_retained_source_states",
            "origin_admitted": False,
            "feature_store_admitted": False,
            "accepted_panel": False,
        }
        _save(root, "diagnostic_report", result)
        _check(root, started)
        return result
    except BaseException as exc:
        try:
            _save(
                root,
                "diagnostic_failure",
                {"failed_at": _clock(), "stage": stage, "exception_type": type(exc).__name__},
            )
        except (OSError, ValueError):
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-commit", required=True)
    args = parser.parse_args()
    # Exactly one public attempt for this frozen protocol; reruns refuse its retained directory.
    root = Path(__file__).parents[3] / "data-dumps/fs2_socket_diagnostic_20260925_1"
    result = asyncio.run(
        run_socket_diagnostic(root, implementation_commit=args.implementation_commit)
    )
    print(
        json.dumps(
            {"root": str(root), "state": result["state"], "accepted_panel": False}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
