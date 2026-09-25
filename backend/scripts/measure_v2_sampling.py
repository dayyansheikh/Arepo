"""Synthetic finite local capacity measurement, never prospective panel/edge evidence."""

import json
import resource
import sys
import time
from datetime import UTC, datetime, timedelta

from astrolabe.research_panel.build_identity import verified_panel_build
from astrolabe.research_panel.sampling import FrameMember, SamplingProtocol, plan_sample

# Frozen before measurement. No database, production settings, network or file deletion.
ROWS = 400000
MAX_RESIDENT_BYTES = 1073741824
MAX_SECONDS = 180


def members():
    at = datetime(2026, 9, 21, tzinfo=UTC)
    for index in range(ROWS):
        yield FrameMember(
            market_id=f"synthetic-{index:08d}", token_id=str(10**76 + index),
            source_observation_id=f"{index:064x}",
            available_at=at + timedelta(microseconds=index),
            time_stratum="synthetic-scheduled", category="synthetic-unknown",
            close_stratum="unknown", probability="0.400000000000000000000000000001",
            liquidity="2000.000000000000000000000000000001", event_group=None,
            group_available_at=None, eligible=True, exclusion_reason=None,
            triggered=index < 10, trigger_id=f"fixture-trigger-{index}" if index < 10 else None,
            trigger_available_at=at if index < 10 else None,
        )


def main():
    build = verified_panel_build()
    started = time.monotonic_ns()
    plan = plan_sample(
        SamplingProtocol("a" * 64, 5, 5, 2, 20), members(),
        cutoff=datetime(2026, 9, 21, 1, tzinfo=UTC), frame_scope="synthetic capacity fixture",
        frame_status="explicit_list", frame_evidence_ids=["f" * 64], max_frame_members=ROWS,
    )
    elapsed = time.monotonic_ns() - started
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak = peak if sys.platform == "darwin" else peak * 1024
    passed = peak <= MAX_RESIDENT_BYTES and elapsed <= MAX_SECONDS * 10**9
    print(json.dumps({
        "measurement": "synthetic capacity only; no live source or panel acceptance",
        "build": build, "rows": ROWS, "max_resident_bytes": MAX_RESIDENT_BYTES,
        "max_seconds": MAX_SECONDS, "elapsed_ns": str(elapsed), "peak_resident_bytes": peak,
        "capacity_gate_passed": passed, "frame_hash": plan["frame_hash"],
        "plan_hash": plan["plan_hash"], "assignments": plan["assignments"],
        "strata": plan["strata"], "population_inference_eligible": False,
    }, sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
