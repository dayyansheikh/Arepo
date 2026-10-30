"""One finite NWS source measurement; no market binding, feature or origin admission."""

import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

import httpx

from astrolabe.feature_store.admission import content_hash
from astrolabe.feature_store.capture import Budget, _clock, _sync_directory
from astrolabe.feature_store.source_run import (
    NWS_POLICY,
    SourceRun,
    _pair,
    _persist,
    read_source_run,
)

from .build_identity import verified_panel_build
from .input_read import _canonical, record_input_read
from .original_reader import _extract, read_original_input_read

POLICY = {
    "version": "fs2-nws-source-measurement-v1",
    "station_id": "KNYC",
    "source_id": "nws.station.observation",
    "source_retained_bytes": 1048576,
    "input_read_bytes": 4 * 1048576,
    "original_read_bytes": 16 * 1048576,
    "metadata_bytes": 1048576,
    "free_reserve_bytes": 2 * 1024**3,
    "retries": 0,
    "market_relevance_admitted": False,
    "accepted_panel": False,
}
BUDGET = Budget(
    requests=1,
    bytes_per_response=65536,
    total_bytes=65536,
    seconds_per_request=15,
    total_seconds=30,
)


async def measure_nws(output_root, *, implementation_commit, repository, transport=None):
    """Policy and full reservation precede the single request; no replacement/retry/SQL."""
    if transport is not None and type(transport) is not httpx.MockTransport:
        raise ValueError("only explicit MockTransport or fixed public source allowed")
    root, repo = _canonical(output_root), _canonical(repository)
    if not root.name.startswith("fs2_nws_measurement_"):
        raise ValueError("separate NWS measurement root required")
    if root.exists():
        raise FileExistsError("NWS measurement retained; never overwrite or rerun")
    required = sum(
        POLICY[k]
        for k in (
            "source_retained_bytes",
            "input_read_bytes",
            "original_read_bytes",
            "metadata_bytes",
            "free_reserve_bytes",
        )
    )
    if shutil.disk_usage(root.parent).free < required:
        raise ValueError("insufficient complete NWS measurement/recovery reservation")
    build = verified_panel_build()
    with tempfile.TemporaryDirectory(prefix="arepo_nws_code_") as tmp:
        _extract(repo, implementation_commit, build, Path(tmp))
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    _persist(
        root,
        "measurement_policy",
        {
            "policy": POLICY,
            "budget": asdict(BUDGET),
            "build": build,
            "implementation_commit": implementation_commit,
            "required_free_bytes": required,
            "declared_at": _clock(),
        },
    )
    try:
        source = root / "fs2_capture_nws"
        run = SourceRun(
            source,
            budget=BUDGET,
            transport=transport,
            policy_version=NWS_POLICY["version"],
            retained_bytes=POLICY["source_retained_bytes"],
        )
        rows = await run.fetch(POLICY["source_id"], {"station_id": POLICY["station_id"]})
        read_root = root / "fs2_input_read_nws"
        read = record_input_read(source, output_root=read_root, storage_profile="compact-v1")
        original = read_original_input_read(
            read_root,
            implementation_commit=implementation_commit,
            repository=repo,
            output_root=root / "fs2_input_read_read_nws",
        )
        if rows != read_source_run(source) or original["report"]["summary"] != read:
            raise ValueError("NWS source/read/original verification differs")
        observation = next(row for kind, row in rows if kind == "source_observation")
        report = {
            "schema_version": POLICY["version"],
            "source_records_hash": content_hash(rows),
            "observation_id": observation["id"],
            "state": observation["missing_reason"],
            "provenance_class": observation["provenance_class"],
            "payload_hash": observation["payload_hash"],
            "received_at": observation["first_received_at"],
            "source_available_at": observation["available_to_model_at"],
            "actual_input_read": read,
            "original_read_available_at": original["read_available_at"],
            "retained_bytes_before_report": sum(
                p.stat().st_size for p in root.rglob("*") if p.is_file()
            ),
            "finished_at": _clock(),
            "market_relevance_admitted": False,
            "origin_admitted": False,
            "accepted_panel": False,
        }
        if verified_panel_build() != build:
            raise ValueError("NWS measurement build changed")
        _persist(root, "measurement_report", report)
        return _pair(root, "measurement_report")[0]
    except BaseException as exc:
        try:
            _persist(
                root, "measurement_failure", {"exception_type": type(exc).__name__, "at": _clock()}
            )
        except (OSError, ValueError):
            pass
        raise
