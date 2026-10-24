"""D120 synthetic screen-then-activate dry run (loopback sockets, mock HTTP; never live data).

Runs the complete owned D120 path (frame -> pairing declaration/selection -> screening of the
group-disjoint list with no windows -> role draw -> fresh binding reads, recomputed triggers and
10 s socket windows for activated members only -> activation -> origins/targets -> original-code
audit) with the D120 values (liquidity population, all categories, D116 windows/trigger/freshness,
runtime concurrency 8) against a synthetic frame with seven category strata of 18 dependence
groups. Every HTTP response is delayed by ``--latency`` seconds (D116 live origins took about
2.9 s for three requests).

Predeclared abort criteria (D120 protocol section 5), for the shapes tried in order 6x16 then
6x12, stopping at the first passing shape:

* maximum window age at origin freeze > 40 s;
* maximum binding age (binding ``clob.book`` receipt to socket subscription) > 40 s;
* maximum assessment age at activation > 80 s;
* screening (screening declaration to sealed screening) > 60 s;
* original-code audit > 240 s.

    cd backend && python scripts/d120_window_dry_run.py --work-dir <empty scratch dir>
        [--per-stratum 16] [--latency 0.9] [--out PATH]

Writes only under ``--work-dir`` (and ``--out`` when given) and prints one JSON summary. Makes no
network request other than loopback.
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
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.frame import GammaFrameRun
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.owned_windows import OwnedWindowPolicy
from astrolabe.research_panel.pairing import PairingDesign
from astrolabe.research_panel.pairing_declaration import (
    PairingPanelProtocol,
    declare_pairing_panel,
)
from astrolabe.research_panel.pairing_selection import create_pairing_selection
from astrolabe.research_panel.pairing_worker import run_synthetic_pairing_pilot
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy

SOURCE = Path(__file__).resolve().parents[1] / "astrolabe"
ABORT = {"max_window_age_at_freeze_s": 40, "max_binding_age_s": 40,
         "max_assessment_age_at_activation_s": 80, "max_screening_s": 60, "max_audit_s": 240}
CATEGORIES = ("sports_fees_v3", "politics_fees", "crypto_fees", "weather_fees",
              "culture_fees", "finance_fees", "tech_fees")
GROUPS_PER_STRATUM = 18


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
            "endDate": "2099-01-01T00:00:00Z", "liquidity": "5000",
            "outcomePrices": '["0.3","0.7"]', **extra}


def rows():
    """Seven category strata x 18 groups; every third group has a sibling (shared event)."""
    result, index = [], 1
    for c, fee in enumerate(CATEGORIES):
        for g in range(GROUPS_PER_STRATUM):
            event = {"id": f"{c}{g:03d}", "slug": f"event-{c}-{g}",
                     "series": [{"id": f"s{c}{g}", "slug": f"series-{c}-{g}"}]}
            result.append(market(index, feeType=fee, events=[event]))
            index += 1
            if g % 3 == 0:  # sibling in the same event: same dependence group
                result.append(market(index, feeType=fee, events=[event]))
                index += 1
    result.append(market(index, feeType="sports_fees_v3", liquidity="10",
                         events=[{"id": "low"}]))  # below the liquidity floor
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
        "-c", "commit.gpgsign=false", "commit", "-qm", "D120 dry-run code fixture")
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
    """Keyset pages of 100 rows; the last page omits next_cursor and is shorter than 100."""
    pages = [markets[i:i + 100] for i in range(0, len(markets), 100)]
    if len(pages[-1]) == 100:
        pages.append([])

    def handle(request):
        index = int(request.url.params.get("after_cursor", "c0")[1:])
        body = {"markets": pages[index]}
        if index + 1 < len(pages):
            body["next_cursor"] = f"c{index + 1}"
        return httpx.Response(200, stream=Stream([json.dumps(body).encode()]))

    run = GammaFrameRun(root, limit=100, budget=Budget(requests=len(pages)),
                        transport=httpx.MockTransport(handle))
    await run.collect()


def protocol(per_stratum, strata=6):
    return PairingPanelProtocol(
        screened_slots=strata * per_stratum, origin_slots=2 * strata, cycles=1,
        target_attempts=1, cadence_seconds=120, max_origin_delay_seconds=60,
        max_origin_save_seconds=5, horizon_seconds=60, tolerance_seconds=15,
        max_frame_age_seconds=3600, max_frame_interval_seconds=600, max_quote_age_seconds=60,
        max_identity_age_seconds=180, source_response_bytes=65536,
        source_run_retained_bytes=1048576)


def _at(value):
    if isinstance(value, dict):
        value = value.get("utc") or value.get("$utc")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _seconds(later, earlier):
    return (_at(later) - _at(earlier)).total_seconds()


def measurements(panel, worker, result):
    """The five abort quantities, read from the retained artefacts (descriptive)."""
    runtime = panel.with_name("fs2_runtime_" + panel.name.removeprefix("fs2_panel_"))
    activation = panel.with_name("fs2_activation_" + panel.name.removeprefix("fs2_panel_"))
    facts, facts_ack = _pair(activation, "activation_facts")
    freeze = []
    for folder in sorted((runtime / "origins").iterdir()):
        if not (folder / "origin_facts.json").exists():
            continue
        origin, _ = _pair(folder, "origin_facts")
        window = origin["projection"].get("pre_origin_window") or {}
        if window.get("frozen_at") and window.get("window_ended_at"):
            freeze.append(_seconds(window["frozen_at"], window["window_ended_at"]))
    binding = []
    bindings, _ = _pair(worker, "bindings")
    for k, item in enumerate(bindings["items"]):
        socket = worker / f"fs2_socket_window_{k:03d}"
        if not socket.exists():
            continue
        report, _ = _pair(socket, "socket_window_report")
        book, _ = _pair(Path(item["book_root"]), "book_facts")
        (snapshot,) = book["projection"]["snapshots"]
        received = snapshot["quote"].get("received_at")
        if received is not None and report.get("subscription_sent_at"):
            binding.append(_seconds(report["subscription_sent_at"], received))
    assessment = []
    inventory = result["screening"]["plan"]["assessment_inventory"]
    roles = {a["market_id"] for a in result["screening"]["plan"]["assignments"]}
    for entry in inventory:
        if entry["market_id"] in roles and entry["assessment"]:
            assessment.append(_seconds(facts["read_completed_at"],
                                       entry["assessment"]["available_at"]))
    screen_policy, _ = _pair(worker / "fs2_screening_batch", "screening_policy")
    screening_s = _seconds(result["screening"]["screening_available_at"],
                           screen_policy["declared_at"])
    receipt = result["recovery"][0]
    audit = _seconds(receipt["completed_at"], receipt["verification_started_at"])
    return {"window_ages_at_freeze_s": sorted(round(a, 3) for a in freeze),
            "max_window_age_at_freeze_s": max(freeze) if freeze else None,
            "binding_ages_s": sorted(round(a, 3) for a in binding),
            "max_binding_age_s": max(binding) if binding else None,
            "max_assessment_age_at_activation_s": max(assessment) if assessment else None,
            "screening_s": screening_s, "audit_verification_s": audit,
            "activation_acknowledged_at": facts_ack["durable_ack"]}


async def one_shape(work, per_stratum, latency, runtime_concurrency):
    work.mkdir(parents=True, exist_ok=False)
    code = code_fixture(work)
    markets = rows()
    source_frame = work / "fs2_capture_dry_run_frame"
    await frame(source_frame, markets)
    panel = work / "fs2_panel_dry_run"
    design = PairingDesign(strata=6, screen_per_stratum=per_stratum, min_groups_per_stratum=8)
    declare_pairing_panel(source_frame, implementation_commit=code[1], output_root=panel,
                          protocol=protocol(per_stratum), design=design,
                          storage_profile="compact-v1")
    create_pairing_selection(panel, repository=code[0])
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
        except ConnectionClosed:
            return

    windows = OwnedWindowPolicy(10000, WindowBindingPolicy(60000, 180000),
                                WindowReconciliationPolicy(120000, 120000, 1000),
                                OriginWindowPolicy(120000, 60000), binding_mode="observation")
    started = time.monotonic()
    async with serve(handle, "127.0.0.1", 0) as server:
        result = await run_synthetic_pairing_pilot(
            panel, implementation_commit=code[1], repository=code[0],
            transport=http(markets, latency), port=server.sockets[0].getsockname()[1],
            rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(120, 120),
            window_policy=windows, concurrency=8, runtime_concurrency=runtime_concurrency)
    elapsed = time.monotonic() - started
    worker = panel.with_name("fs2_screening_worker_" + panel.name.removeprefix("fs2_panel_"))
    measured = measurements(panel, worker, result)
    plan = result["screening"]["plan"]
    origin_states = {}
    for row in result["runtime"]["origins"]:
        origin_states[row["state"]] = origin_states.get(row["state"], 0) + 1
    summary = {
        "shape": f"6x{per_stratum}", "screened": len(result["screening"]["states"]),
        "activated": len(result["bindings"]), "pairs_drawn": plan["pairs_drawn"],
        "triggers_in_scope": plan["triggers_in_scope"], "origin_states": origin_states,
        "target_states": sorted({o["state"] for o in result["runtime"]["outcomes"]}),
        "worker_state": result["state"], "elapsed_s": round(elapsed, 3),
        "retained_bytes_before_report": result["retained_bytes_before_report"],
        **measured,
    }
    checks = {
        "max_window_age_at_freeze_s": summary["max_window_age_at_freeze_s"],
        "max_binding_age_s": summary["max_binding_age_s"],
        "max_assessment_age_at_activation_s": summary["max_assessment_age_at_activation_s"],
        "max_screening_s": summary["screening_s"], "max_audit_s": summary["audit_verification_s"],
    }
    summary["breaches"] = sorted(k for k, v in checks.items() if v is None or v > ABORT[k])
    summary["abort"] = bool(summary["breaches"])
    return summary


async def main_async(args):
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    record = {
        "provenance": "synthetic loopback dry run; never evidence about live data",
        "latency_s_per_request": args.latency, "runtime_concurrency": args.runtime_concurrency,
        "abort_criteria": ABORT, "rule": "try 6x16 first, then 6x12; stop at the first passing "
                                         "shape", "runs": [],
    }
    for per in args.shapes:
        summary = await one_shape(work / f"shape_6x{per}", per, args.latency,
                                  args.runtime_concurrency)
        record["runs"].append(summary)
        if not summary["abort"]:
            record["chosen_shape"] = summary["shape"]
            break
    else:
        record["chosen_shape"] = None
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--shapes", type=int, nargs="+", default=[16, 12])
    parser.add_argument("--latency", type=float, default=0.9)
    parser.add_argument("--runtime-concurrency", type=int, default=8)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    record = asyncio.run(main_async(args))
    text = json.dumps(record, indent=1, default=str)
    if args.out is not None:
        args.out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
