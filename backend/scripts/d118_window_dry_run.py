"""D118 synthetic 16-member window-pilot dry run (loopback sockets, mock HTTP; never live data).

Runs the complete owned path (frame -> liquidity-scoped declaration/selection -> screening with
10 s socket windows -> activation -> origins/targets -> original-code audit) with the frozen D118
values (4 strata x 4 members, 16/16 slots, runtime concurrency 8, D116 windows/trigger/freshness)
against a synthetic frame. HTTP responses are delayed by ``--latency`` seconds each to emulate
live request latency (D116 live origins took about 2.9 s for three requests).

Predeclared abort criteria (protocol section 5): if the maximum window age at origin freeze
exceeds 40 s, or the original-code audit takes longer than 240 s, D118 must not be frozen.

    cd backend && python scripts/d118_window_dry_run.py --work-dir <empty scratch dir>
        [--per-stratum 4] [--latency 0.9] [--runtime-concurrency 8]

Writes only under ``--work-dir`` and prints one JSON summary. Makes no network request other
than loopback.
"""

import argparse
import asyncio
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import httpx
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from astrolabe.feature_store.capture import Budget
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.d118_evaluator import evaluate_d118_logic_only_test_aid
from astrolabe.research_panel.frame import GammaFrameRun
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.owned_windows import OwnedWindowPolicy
from astrolabe.research_panel.panel_declaration import (
    LIQUIDITY_POPULATION,
    PanelProtocol,
    declare_panel,
)
from astrolabe.research_panel.panel_selection import create_panel_selection
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.screening_worker import run_synthetic_window_pilot
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy

SOURCE = Path(__file__).resolve().parents[1] / "astrolabe"
MAX_WINDOW_AGE_AT_FREEZE_S = 40
MAX_AUDIT_S = 240
STRATA = [("5000", '["0.3","0.7"]'), ("5000", '["0.6","0.4"]'),
          ("50000", '["0.3","0.7"]'), ("500000", '["0.6","0.4"]')]


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


def market(index, **extra):
    return {"id": str(index), "conditionId": "0x" + f"{index:064x}",
            "clobTokenIds": json.dumps([str(index * 2), str(index * 2 + 1)]),
            "outcomes": '["Yes","No"]', "active": True, "closed": False,
            "description": "Rules", "archived": False, "acceptingOrders": True,
            "events": [{"id": "42"}], "endDate": "2099-01-01T00:00:00Z", **extra}


def rows(per_stratum):
    result, index = [], 1
    for liquidity, prices in STRATA:
        for _ in range(per_stratum + 1):  # one spare member per stratum: real within draw
            result.append(market(index, liquidity=liquidity, outcomePrices=prices))
            index += 1
    result.append(market(index, liquidity="10", outcomePrices='["0.3","0.7"]'))
    result.append(market(index + 1, outcomePrices='["0.3","0.7"]'))  # liquidity missing
    return result


def code_fixture(work):
    """A disposable git copy of the current code, as the original-code audit requires."""
    repo = work / "original_code"
    package = repo / "backend" / "astrolabe"
    package.mkdir(parents=True)
    shutil.copyfile(SOURCE / "__init__.py", package / "__init__.py")
    for name in ("feature_store", "research_panel"):
        (package / name).mkdir()
        for file in (SOURCE / name).glob("*.py"):
            shutil.copyfile(file, package / name / file.name)

    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                              text=True).stdout.strip()

    git("init", "--quiet")
    git("add", "backend")
    git("-c", "user.name=DryRun", "-c", "user.email=dry-run@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "D118 dry-run code fixture")
    return repo, git("rev-parse", "HEAD")


def http(markets, latency):
    by_id = {r["id"]: r for r in markets}
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in markets}

    async def handle(request):
        await asyncio.sleep(latency)
        if request.url.path.startswith("/markets/"):
            body = dict(by_id[request.url.path.split("/")[-1]])
            body.pop("events", None)
        elif request.url.path == "/book":
            token = request.url.params["token_id"]
            row = by_token[token]
            # Alternate members: bid size 2 vs ask 1 triggers (|imbalance| = 1/3), 1 vs 1 not.
            size = "2" if int(row["id"]) % 2 else "1"
            body = {"asset_id": token, "market": row["conditionId"],
                    "bids": [{"price": "0.4", "size": size}],
                    "asks": [{"price": "0.6", "size": "1"}]}
        else:
            body = {"data": [], "pagination": {"has_more": False, "next_cursor": None}}
        return httpx.Response(200, stream=Stream([json.dumps(body).encode()]))

    return httpx.MockTransport(handle)


async def frame(root, markets):
    body = json.dumps({"markets": markets}).encode()
    run = GammaFrameRun(root, limit=100, budget=Budget(requests=1), transport=httpx.MockTransport(
        lambda r: httpx.Response(200, stream=Stream([body]))))
    await run.collect()


def protocol(per_stratum):
    slots = 4 * per_stratum
    return PanelProtocol(
        scheduled_slots=slots, triggered_slots=slots, controls_per_trigger=1, cycles=1,
        target_attempts=1, scheduled_per_stratum=per_stratum, triggered_per_stratum=per_stratum,
        cadence_seconds=120, max_origin_delay_seconds=60, max_origin_save_seconds=5,
        horizon_seconds=60, tolerance_seconds=15, max_frame_age_seconds=3600,
        max_frame_interval_seconds=600, max_quote_age_seconds=60, max_identity_age_seconds=180,
        source_response_bytes=65536, source_run_retained_bytes=1048576)


def _seconds(later, earlier):
    def at(value):
        return datetime.fromisoformat(value["utc"].replace("Z", "+00:00"))

    return (at(later) - at(earlier)).total_seconds()


async def main_async(args):
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    code = code_fixture(work)
    markets = rows(args.per_stratum)
    source_frame = work / "fs2_capture_dry_run_frame"
    await frame(source_frame, markets)
    panel = work / "fs2_panel_dry_run"
    declare_panel(source_frame, implementation_commit=code[1], output_root=panel,
                  protocol=protocol(args.per_stratum), storage_profile="compact-v1",
                  strata_limit=4, population_policy=LIQUIDITY_POPULATION)
    create_panel_selection(panel, repository=code[0])
    by_token = {json.loads(r["clobTokenIds"])[0]: r for r in markets}

    async def handle(socket):
        token = json.loads(await socket.recv())["assets_ids"][0]
        row = by_token[token]
        try:
            while True:  # a book event every 0.5 s, like a quoted liquid market
                await socket.send(json.dumps({
                    "event_type": "book", "asset_id": token, "market": row["conditionId"],
                    "bids": [{"price": "0.4", "size": "2"}],
                    "asks": [{"price": "0.6", "size": "1"}]}))
                await asyncio.sleep(0.5)
        except ConnectionClosed:  # the observer closes the socket at window end
            return

    windows = OwnedWindowPolicy(10000, WindowBindingPolicy(60000, 180000),
                                WindowReconciliationPolicy(120000, 120000, 1000),
                                OriginWindowPolicy(120000, 60000), binding_mode="observation")
    started = time.monotonic()
    async with serve(handle, "127.0.0.1", 0) as server:
        result = await run_synthetic_window_pilot(
            panel, implementation_commit=code[1], repository=code[0],
            transport=http(markets, args.latency), port=server.sockets[0].getsockname()[1],
            rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(120, 120),
            window_policy=windows, concurrency=8, runtime_concurrency=args.runtime_concurrency)
    elapsed = time.monotonic() - started
    report = evaluate_d118_logic_only_test_aid(panel)
    receipt = result["recovery"][0]
    audit = _seconds(receipt["completed_at"], receipt["verification_started_at"])
    recovery = _seconds(result["reported_at"], result["runtime"]["finished_at"])
    ages = [a["window_age_at_freeze_s"]
            for a in report["timeline"]["margins"]["window_age_at_freeze"]]
    assessment = report["timeline"]["margins"]["assessment_ages_at_activation"]
    summary = {
        "provenance": "synthetic loopback dry run; never evidence about live data",
        "per_stratum": args.per_stratum, "members": len(result["screening"]["states"]),
        "latency_s_per_request": args.latency, "runtime_concurrency": args.runtime_concurrency,
        "worker_state": result["state"], "elapsed_s": round(elapsed, 3),
        "max_window_age_at_freeze_s": max(ages) if ages else None,
        "window_ages_at_freeze_s": sorted(round(a, 3) for a in ages),
        "max_assessment_window_age_at_activation_s": max(
            (a["window_age_s"] for a in assessment), default=None),
        "audit_verification_s": audit, "recovery_after_runtime_s": recovery,
        "evaluator_outcome": report["outcome"], "evaluator_reasons": report["outcome_reasons"],
        "pairs_both_complete": report["summary"].get("pairs_both_complete"),
        "role_capacity": result["role_capacity"]["counts_per_cycle"],
        "abort_criteria": {"max_window_age_at_freeze_s": MAX_WINDOW_AGE_AT_FREEZE_S,
                           "max_audit_s": MAX_AUDIT_S},
    }
    summary["abort"] = bool(
        summary["max_window_age_at_freeze_s"] is None
        or summary["max_window_age_at_freeze_s"] > MAX_WINDOW_AGE_AT_FREEZE_S
        or audit > MAX_AUDIT_S)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--per-stratum", type=int, default=4, choices=(2, 4))
    parser.add_argument("--latency", type=float, default=0.9)
    parser.add_argument("--runtime-concurrency", type=int, default=8)
    args = parser.parse_args(argv)
    print(json.dumps(asyncio.run(main_async(args)), indent=1, default=str))


if __name__ == "__main__":
    main()
