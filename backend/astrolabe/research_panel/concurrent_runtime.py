"""Bounded origin/target jobs with replayable dispatch events and explicit source provenance."""

import asyncio
import heapq
import shutil
from datetime import timedelta

import httpx

from astrolabe.feature_store.capture import _clock, _json_bytes, _sync_directory
from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _ordered_clocks, _pair

from . import due_worker, origin_worker, owned_windows
from . import runtime as base
from .activation import activate_screened_panel, read_activation
from .build_identity import verified_panel_build
from .input_read import _canonical
from .panel_declaration import PanelProtocol, read_panel_declaration
from .scheduling import wait_until
from .screening_worker import _durable_call

VERSION = "fs2-concurrent-synthetic-runtime-v2"
FEATURE_VERSION = "fs2-concurrent-feature-runtime-v3"
OWNED_VERSION = "fs2-owned-concurrent-runtime-v4"
WINDOW_VERSION = "fs2-owned-window-runtime-v5"
POLICY = {
    **base.POLICY,
    "queue_order": "ready targets before ready origins; then scheduled UTC/id",
    "request_concurrency": "frozen 2..8 total jobs; at most concurrency-1 origins",
    "clock_semantics": "parent dispatch/completion; actual child intent/receipt/freeze clocks",
    "job_execution": "bounded isolated event loops; cancellation drains durable jobs",
}


def _capacity(concurrency):
    if type(concurrency) is not int or not 2 <= concurrency <= 8:
        raise ValueError("bounded concurrency from 2 to 8 required")


def _permitted(kind, active, concurrency):
    return len(active) < concurrency and (
        kind == "target" or sum(v[3] == "origin" for v in active.values()) < concurrency - 1
    )


def _ready(queue, active, concurrency, at):
    available = [
        entry for entry in queue if entry[0] <= at and _permitted(entry[3], active, concurrency)
    ]
    return min(available, key=lambda e: (e[1], e[0], e[2])) if available else None


def _remove(queue, entry):
    queue.remove(entry)
    heapq.heapify(queue)


async def _execute(root, entry, members, panel_policy, activation, origins, transport, features,
                   window_inputs=None):
    _, _, identity, kind, job = entry
    protocol = PanelProtocol(**panel_policy["protocol"])
    if kind == "origin":
        dependency = (window_inputs["members"][job["market_id"]]["analysis_root"]
                      if window_inputs else None)
        result = await origin_worker._collect_one(
            root / "origins" / identity,
            job,
            members[job["market_id"]],
            panel_policy,
            activation,
            transport, features=features, window_root=dependency,
            window_policy=owned_windows.policy_from_dict(window_inputs["policy"]).origin
            if dependency else None,
        )
        return base._plan(root, result, protocol)
    return await due_worker._collect_one(
        root / "targets" / identity, job, origins[job["origin_id"]], panel_policy, transport
    )


async def exercise_screened_panel(panel_root, screening_root, *, transport, concurrency=4,
                                  features=False):
    if type(transport) is not httpx.MockTransport:
        raise ValueError("concurrent runtime requires explicit synthetic MockTransport")
    return await _exercise(panel_root, screening_root, transport=transport,
                           concurrency=concurrency, features=features)


async def _exercise_owned_panel(panel_root, screening_root, *, finish_owned, transport,
                                 concurrency, window_inputs=None):
    return await _exercise(panel_root, screening_root, transport=transport,
                           concurrency=concurrency, features=True, finish_owned=finish_owned,
                           window_inputs=window_inputs)


async def _exercise(panel_root, screening_root, *, transport, concurrency, features,
                    finish_owned=None, window_inputs=None):
    if type(features) is not bool:
        raise ValueError("explicit feature mode required")
    owned = finish_owned is not None
    if transport is not None and type(transport) is not httpx.MockTransport:
        raise ValueError("unsupported owned runtime transport")
    if not owned and transport is None:
        raise ValueError("legacy runtime requires synthetic transport")
    provenance = 'prospective' if transport is None else 'synthetic'
    if window_inputs is not None and not owned:
        raise ValueError("owned runtime required for window inputs")
    version = WINDOW_VERSION if window_inputs is not None else (
        OWNED_VERSION if owned else FEATURE_VERSION if features else VERSION)
    runtime_policy = ({**POLICY, 'live_collection_enabled': transport is None,
                       'identity_policy': origin_worker.IDENTITY_POLICY}
                      if owned else POLICY)
    _capacity(concurrency)
    panel, root = _canonical(panel_root), base.run_root(panel_root)
    screening = _canonical(screening_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, "panel_policy")
    protocol = PanelProtocol(**panel_policy["protocol"])
    if root.exists():
        raise FileExistsError("runtime retained; never resume or reschedule")
    if shutil.disk_usage(root.parent).free < base._reserved(declaration):
        raise ValueError("insufficient complete concurrent runtime reservation")
    build = verified_panel_build()
    root.mkdir(mode=0o700)
    _sync_directory(root.parent)
    try:
        for child in sorted(base.CHILDREN):
            (root / child).mkdir(mode=0o700)
        _sync_directory(root)
        base._save(
            root,
            "runtime_policy",
            {
                "schema_version": version,
                "policy": runtime_policy,
                **({'provenance_class': provenance} if owned else {}),
                "build": build,
                "panel_root": str(panel),
                "screening_root": str(screening),
                "concurrency": concurrency,
                **({"window_inputs": window_inputs} if window_inputs is not None else {}),
                "declaration_hash": declaration["declaration_hash"],
                "required_free_bytes": base._reserved(declaration),
                "declared_at": _clock(),
            },
        )
        if owned:
            screened, activation = finish_owned(activate=True)
            if activation['provenance_class'] != provenance:
                raise ValueError('owned activation transport provenance differs')
        else:
            activation = activate_screened_panel(panel, screening)
        members = {m["market_id"]: m for m in activation["selected"]}
        queue = base._queue(activation)
        heapq.heapify(queue)
        origins, attempts, events, active, tasks = {}, [], [], {}, {}
        # No task uses another job's event loop or source quota. This also prevents synchronous
        # parsing/fsync/replay in one job from delaying another job's network receipt handling.
        async with asyncio.TaskGroup() as group:
            while queue or tasks:
                for identity in sorted(i for i, task in tasks.items() if task.done()):
                    result = tasks.pop(identity).result()
                    entry = active.pop(identity)
                    kind = entry[3]
                    if kind == "origin":
                        origin, jobs, ack = result
                        origins[identity] = origin
                        base._enqueue(queue, jobs, ack, origin["result"]["state"] == "observed")
                    else:
                        attempts.append(result)
                    events.append(
                        {"event": "completed", "kind": kind, "id": identity, "at": _clock()}
                    )
                at = _clock()
                entry = _ready(queue, active, concurrency, _time(at))
                if entry is not None:
                    _remove(queue, entry)
                    identity = entry[2]
                    active[identity] = entry
                    events.append(
                        {"event": "dispatched", "kind": entry[3], "id": identity, "at": at}
                    )

                    # Construct the coroutine inside its thread. No detached durable writers on
                    # cancellation: _durable_call drains it before the task group can finish.
                    def execute(entry=entry):
                        return asyncio.run(
                            _execute(
                                root, entry, members, panel_policy, activation, origins,
                                transport, features, window_inputs
                            )
                        )

                    tasks[identity] = group.create_task(_durable_call(execute))
                    continue
                future = [e[0] for e in queue if _permitted(e[3], active, concurrency)]
                if not tasks:
                    if future:
                        await wait_until(min(future))
                    continue
                timeout = max(0.001, (min(future) - _time(at)).total_seconds()) if future else None
                await asyncio.wait(
                    tasks.values(), timeout=timeout, return_when=asyncio.FIRST_COMPLETED
                )
        deadlines = [
            _time(o["facts"]["origin_at"])
            + timedelta(seconds=protocol.horizon_seconds + protocol.tolerance_seconds)
            for o in origins.values()
            if o["result"]["state"] == "observed"
        ]
        if deadlines:
            await wait_until(max(deadlines))
        cutoff = _clock()
        outcomes = due_worker._outcomes(list(origins.values()), attempts, protocol, cutoff)
        if verified_panel_build() != build:
            raise ValueError("concurrent runtime build changed")
        base._save(
            root,
            "runtime_report",
            {
                "schema_version": version,
                "activation_hash": activation["activation_hash"],
                "events": events,
                "origins": [o["result"] for o in origins.values()],
                "attempts": [{k: v for k, v in a.items() if k != "projection"} for a in attempts],
                "outcomes": outcomes,
                "as_of": cutoff,
                "finished_at": _clock(),
                "provenance_class": provenance,
                "accepted_panel": False,
                "feature_store_admitted": False,
            },
        )
        result = read_runtime(panel)
        return (screened, result) if owned else result
    except BaseException as exc:
        try:
            base._save(
                root,
                "runtime_failure",
                {"exception_type": type(exc).__name__, "at": _clock()},
                failure=True,
            )
        except (ValueError, OSError):
            pass
        raise


def read_runtime(panel_root):
    panel, root = _canonical(panel_root), base.run_root(panel_root)
    declaration = read_panel_declaration(panel)
    panel_policy, _ = _pair(panel, "panel_policy")
    protocol = PanelProtocol(**panel_policy["protocol"])
    policy, policy_ack = _pair(root, "runtime_policy")
    report, report_ack = _pair(root, "runtime_report")
    activation = read_activation(panel)
    version = policy["schema_version"]
    windows = version == WINDOW_VERSION
    owned = version in {OWNED_VERSION, WINDOW_VERSION}
    features = version in {FEATURE_VERSION, OWNED_VERSION, WINDOW_VERSION}
    provenance = activation['provenance_class'] if owned else 'synthetic'
    runtime_policy = ({**POLICY, 'live_collection_enabled': provenance == 'prospective',
                       'identity_policy': origin_worker.IDENTITY_POLICY}
                      if owned else POLICY)
    if (version not in {VERSION, FEATURE_VERSION, OWNED_VERSION, WINDOW_VERSION}
            or windows != ("window_inputs" in policy)
            or owned and (policy.get('provenance_class') != provenance
                          or activation['schema_version'] != origin_worker.OWNED_ACTIVATION
                          or provenance not in {'synthetic', 'prospective'})
            or not owned and 'provenance_class' in policy):
        raise ValueError("unknown concurrent runtime version")
    concurrency = policy["concurrency"]
    _capacity(concurrency)
    if (
        set(p.name for p in root.iterdir())
        != base.CHILDREN
        | {
            "runtime_policy.json",
            "runtime_policy_ack.json",
            "runtime_report.json",
            "runtime_report_ack.json",
        }
        or base._size(root) > POLICY["top_bytes"]
        or policy["schema_version"] != version
        or policy["policy"] != runtime_policy
        or policy["build"] != verified_panel_build()
        or policy["panel_root"] != str(panel)
        or policy["screening_root"] != activation.get("screening_root")
        or policy["declaration_hash"] != declaration["declaration_hash"]
        or policy["required_free_bytes"] != base._reserved(declaration)
        or report["schema_version"] != version
        or report["activation_hash"] != activation["activation_hash"]
        or not _ordered_clocks(
            policy["declared_at"],
            policy_ack["durable_ack"],
            activation["activation_available_at"],
            report["as_of"],
            report["finished_at"],
            report_ack["durable_ack"],
        )
    ):
        raise ValueError("concurrent runtime policy/activation/chronology differs")
    window_inputs = None
    if windows:
        sp, _ = _pair(_canonical(policy['screening_root']), 'screening_policy')
        window_inputs = owned_windows.read(_canonical(policy['screening_root']).parent,
                                          sp['selected'], provenance)
        if window_inputs != policy['window_inputs'] or any(
            not _ordered_clocks(v['available_at'], policy['declared_at'])
            for v in window_inputs['members'].values()
        ):
            raise ValueError('runtime window ownership/availability differs')
    members = {m["market_id"]: m for m in activation["selected"]}
    queue = base._queue(activation)
    heapq.heapify(queue)
    origins, attempts, active, starts = {}, [], {}, {}
    previous = activation["activation_available_at"]
    for event in report["events"]:
        if not _ordered_clocks(previous, event["at"]):
            raise ValueError("concurrent event clocks regressed")
        identity, kind = event["id"], event["kind"]
        if event["event"] == "dispatched":
            entry = _ready(queue, active, concurrency, _time(event["at"]))
            if entry is None or entry[2:4] != (identity, kind):
                raise ValueError("concurrent ready order/capacity differs")
            _remove(queue, entry)
            active[identity], starts[identity] = entry, event["at"]
        elif event["event"] == "completed":
            entry = active.pop(identity, None)
            if entry is None or entry[3] != kind:
                raise ValueError("completion without matching dispatch")
            job = entry[4]
            if kind == "origin":
                child = root / "origins" / identity
                result = origin_worker._read_one(
                    child, job, members[job["market_id"]], panel_policy, activation
                )
                intent, _ = _pair(child, "origin_intent")
                dependency = (window_inputs["members"][job["market_id"]]["analysis_root"]
                              if windows else None)
                if dependency and intent.get("window_dependency") != {
                    "analysis_root": dependency, "policy": window_inputs["policy"]["origin"]
                }:
                    raise ValueError("origin window differs from owned selected dependency")
                if intent["schema_version"] != (
                    origin_worker.WINDOW_VERSION if dependency else
                    origin_worker.OWNED_VERSION if owned
                    else origin_worker.FEATURE_VERSION if features else origin_worker.VERSION
                ):
                    raise ValueError("runtime and origin feature modes differ")
                origin, jobs, ack = base._read_plan(root, result, protocol)
                origins[identity] = origin
                base._enqueue(queue, jobs, ack, origin["result"]["state"] == "observed")
                last = ack["durable_ack"]
            else:
                child = root / "targets" / identity
                attempt = due_worker._read_one(child, job, origins[job["origin_id"]], panel_policy)
                intent, _ = _pair(child, "target_intent")
                _, ack = _pair(root / "plans" / job["origin_id"], "plan")
                if not _ordered_clocks(ack["durable_ack"], intent["created_at"]):
                    raise ValueError("concurrent target preceded durable plan")
                attempts.append(attempt)
                last = attempt["available_at"]
            if not _ordered_clocks(starts.pop(identity), intent["created_at"], last, event["at"]):
                raise ValueError("concurrent dispatch/child/completion chronology differs")
        else:
            raise ValueError("unknown concurrent event")
        previous = event["at"]
    if (
        queue
        or active
        or starts
        or set(p.name for p in (root / "origins").iterdir()) != set(origins)
        or set(p.name for p in (root / "plans").iterdir()) != set(origins)
        or set(p.name for p in (root / "targets").iterdir()) != {a["attempt_id"] for a in attempts}
        or not _ordered_clocks(previous, report["as_of"])
        or report["origins"] != [o["result"] for o in origins.values()]
        or report["attempts"]
        != [{k: v for k, v in a.items() if k != "projection"} for a in attempts]
        or _json_bytes(report["outcomes"])
        != _json_bytes(
            due_worker._outcomes(list(origins.values()), attempts, protocol, report["as_of"])
        )
        or report["provenance_class"] != provenance
        or report["accepted_panel"] is not False
        or report["feature_store_admitted"] is not False
    ):
        raise ValueError("concurrent runtime closure/outcome replay differs")
    return {
        **report,
        "runtime_report_hash": report_ack["payload_hash"],
        "runtime_available_at": report_ack["durable_ack"],
    }
