# ruff: noqa: E501
"""Host resize scripts (scripts/oracle/resize_host.py, post_resize_check.py) with a fake OCI client and fake clock."""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "oracle"


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rh = _load("resize_host_under_test", "resize_host.py")
prc = _load("post_resize_check_under_test", "post_resize_check.py")

ME = {"id": "ocid1.instance.me", "name": "dsheikh", "shape": rh.SHAPE, "state": "RUNNING", "ad": "AD-1", "ocpus": 1.0, "memory_gb": 6.0}


# ---------------------------------------------------------------- guard
def test_guard_ok_for_single_1_6_instance():
    g = rh.evaluate_guard(ME, [ME, {**ME, "id": "x", "state": "TERMINATED"}], {"standard-a1-core-count": 2.0, "standard-a1-memory-count": 12.0, "standard-a1-core-count:available": 1.0, "standard-a1-memory-count:available": 6.0})
    assert g["ok"] and g["would_be"] == {"a1_ocpus": 2.0, "a1_memory_gb": 12.0} and g["a1_used_now"] == {"ocpus": 1.0, "memory_gb": 6.0}


@pytest.mark.parametrize("me,others,limits,needle", [
    (ME, [{**ME, "id": "o", "name": "arepo-research", "state": "PROVISIONING"}], {}, "another A1 instance"),
    (ME, [{**ME, "id": "o", "name": "stopped", "state": "STOPPED"}], {}, "another A1 instance"),
    ({**ME, "state": "STOPPED"}, [], {}, "not RUNNING"),
    ({**ME, "shape": "VM.Standard.E2.1.Micro"}, [], {}, "not VM.Standard.A1.Flex"),
    ({**ME, "ocpus": 2.0, "memory_gb": 12.0}, [], {}, "already at or above"),
    (ME, [], {"standard-a1-core-count": 1.0}, "tenancy limit"),
    (ME, [], {"standard-a1-core-count": 2.0, "standard-a1-core-count:available": 0.0}, "available in this AD"),
    (ME, [], {"standard-a1-memory-count": 12.0, "standard-a1-memory-count:available": 4.0}, "available in this AD"),
])
def test_guard_refusals(me, others, limits, needle):
    g = rh.evaluate_guard(me, [me, *others], limits)
    assert not g["ok"] and any(needle in r for r in g["reasons"])


def test_guard_refuses_when_result_exceeds_free_allowance(monkeypatch):
    monkeypatch.setattr(rh, "TARGET_OCPUS", 3.0)
    g = rh.evaluate_guard(ME, [ME], {})
    assert not g["ok"] and any("exceeds the free" in r for r in g["reasons"])


def test_unknown_limits_are_reported_not_refused():
    assert rh.evaluate_guard(ME, [ME], {"standard-a1-core-count": "unknown (ServiceError)"})["ok"]


def test_rejection_retryability():
    assert rh.ResizeRejected(500, "InternalError", "Out of host capacity.").retryable
    assert rh.ResizeRejected(429, "TooManyRequests", "slow down").retryable
    assert not rh.ResizeRejected(400, "LimitExceeded", "limit").retryable
    assert not rh.ResizeRejected(404, "NotAuthorizedOrNotFound", "no").retryable


# ---------------------------------------------------------------- schedule / date guard
def T(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)


@pytest.mark.parametrize("now,markers,ok,why", [
    ("2026-10-21T02:41:00", [], False, "before the scheduled night"),
    ("2026-10-22T02:39:59", [], False, "outside"),
    ("2026-10-22T02:40:00", [], True, "due"),
    ("2026-10-22T03:04:59", [], True, "due"),
    ("2026-10-22T03:05:00", [], False, "outside"),
    ("2026-10-23T02:45:00", [], True, "due"),
    ("2026-10-22T02:45:00", ["STARTED"], False, "marker"),
    ("2026-10-22T02:45:00", ["DONE"], False, "marker"),
    ("2026-10-22T02:45:00", ["GAVE_UP"], False, "marker"),
])
def test_due(now, markers, ok, why):
    res = rh.due(T(now), {"not_before_date": "2026-10-22"}, markers)
    assert res[0] is ok and why in res[1]


def test_reschedule_next_night_then_give_up():
    s = {"not_before_date": "2026-10-22", "nights_tried": 0, "history": []}
    s, gave = rh.reschedule(s, T("2026-10-22T03:05:00"), "pass running")
    assert not gave and s["not_before_date"] == "2026-10-23" and s["nights_tried"] == 1
    s["nights_tried"] = rh.MAX_NIGHTS - 1
    s, gave = rh.reschedule(s, T("2026-10-28T03:05:00"), "pass running")
    assert gave and s["not_before_date"] == "2026-10-23"


def test_cron_block_append_and_remove_are_exact():
    cur = "# keep\n*/5 * * * * /x/supervise.sh\n"
    added = rh.cron_with_block(cur)
    assert added.startswith(cur) and rh.cron_with_block(added) == added
    assert all(ln in added for ln in rh.CRON_BLOCK)
    assert rh.cron_without_block(added) == cur
    assert "% " not in "\n".join(rh.CRON_BLOCK)  # cron would treat % as a newline


# ---------------------------------------------------------------- run() with fakes
class Clock:
    def __init__(self, t: datetime):
        self.t = t

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += timedelta(seconds=s)


class FakeApi:
    def __init__(self, reject=None, others=()):
        self.reject, self.others, self.calls = reject, list(others), []

    def get_instance(self, ocid):
        return dict(ME)

    def list_instances(self):
        return [dict(ME), *self.others]

    def a1_limits(self, ad):
        return {"standard-a1-core-count": 2.0, "standard-a1-memory-count": 12.0,
                "standard-a1-core-count:available": 1.0, "standard-a1-memory-count:available": 6.0}

    def update_shape(self, ocid, ocpus, mem):
        self.calls.append((ocid, ocpus, mem))
        if self.reject:
            raise self.reject
        return {"opc_request_id": "req", "opc_work_request_id": "wr", "state": "RUNNING"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "arepo"
    (home / "run/queue/state").mkdir(parents=True)
    (home / "docs/research_lab/queue/jobs").mkdir(parents=True)
    st = tmp_path / "resize"
    for k, v in {"HOME": home, "STATE": st, "OCI_RETRY": tmp_path / "oci_retry", "QUEUE_RUN": home / "run/queue",
                 "QUEUE_JOBS": home / "docs/research_lab/queue/jobs", "COLLECTOR_LOCK": tmp_path / "collector.lock",
                 "SUPERVISE_LOCK": home / "run/supervise.lock", "LIGHT_LOCKS": [tmp_path / "s1.lock", tmp_path / "s2.lock"]}.items():
        monkeypatch.setattr(rh, k, v)
    clock = Clock(T("2026-10-22T02:40:05"))
    monkeypatch.setattr(rh, "_now", clock.now)
    monkeypatch.setattr(rh, "_sleep", clock.sleep)
    calls = {"notify": [], "queue": [], "supervise": 0, "stopped": 0}

    def queue_cmd(cmd):
        calls["queue"].append(cmd)
        if cmd in ("pause", "stop"):
            (home / "run/queue/PAUSE").write_text("x")
        elif cmd == "resume":
            (home / "run/queue/PAUSE").unlink(missing_ok=True)
        return 0

    def stop_monitors(timeout_s=120):
        calls["stopped"] += 1
        return {"cross-venue-live": "exited", "live-trade-monitor": "exited"}

    monkeypatch.setattr(rh, "queue_cmd", queue_cmd)
    monkeypatch.setattr(rh, "notify", lambda h, lines, key, severity="high": calls["notify"].append((h, lines, key)))
    monkeypatch.setattr(rh, "run_supervise", lambda: calls.__setitem__("supervise", calls["supervise"] + 1))
    monkeypatch.setattr(rh, "stop_monitors", stop_monitors)
    monkeypatch.setattr(rh, "monitor_pid", lambda name: 4242)
    monkeypatch.setattr(rh, "wait_grid_cycle", lambda until: {"grid_cycle_utc": "2026-10-22T03:00:00Z", "confirmed": True})
    monkeypatch.setattr(rh, "poller_cycles", lambda *a, **k: [T("2026-10-22T03:00:00")])
    monkeypatch.setattr(rh, "busy_unlocked_jobs", lambda: [])
    monkeypatch.setattr(rh, "instance_metadata", lambda: {"id": ME["id"], "shapeConfig": {"ocpus": 1.0, "memoryInGBs": 6.0}})
    monkeypatch.setattr(rh, "boot_id", lambda: "boot-1")
    monkeypatch.setattr(rh, "host_shape", lambda: {"nproc": 1, "mem_total_gib": 5.52})
    monkeypatch.setattr(rh, "HOLD_S", 30)
    return {"home": home, "state": st, "clock": clock, "calls": calls, "tmp": tmp_path}


def test_not_due_before_the_night_touches_nothing(env):
    env["clock"].t = T("2026-10-21T02:40:05")
    api = FakeApi()
    assert rh.run(lambda: api) == 0
    assert not api.calls and not env["calls"]["queue"] and not (env["tmp"] / "oci_retry/DONE").exists()


def test_success_path_writes_markers_and_gap_and_never_runs_twice(env):
    api = FakeApi()
    assert rh.run(lambda: api) == 0
    assert api.calls == [(ME["id"], 2.0, 12.0)]
    st = env["state"]
    assert (st / "STARTED").exists() and (env["tmp"] / "oci_retry/DONE").exists()
    gap = json.loads((st / "gap.json").read_text())
    assert gap["boot_id_before"] == "boot-1" and gap["api_called_utc"] and gap["monitors_stopped_utc"] and not gap["queue_was_paused"]
    assert env["calls"]["queue"][0] == "pause" and env["calls"]["stopped"] == 1
    assert any(h == "Server resize started" for h, *_ in env["calls"]["notify"])
    # no restart within HOLD_S: everything is restored (post-check finalises later)
    assert "resume" in env["calls"]["queue"] and env["calls"]["supervise"] == 1
    api2 = FakeApi()
    assert rh.run(lambda: api2) == 0 and not api2.calls  # STARTED marker: never twice


def test_capacity_error_restores_and_reschedules(env):
    api = FakeApi(reject=rh.ResizeRejected(500, "InternalError", "Out of host capacity."))
    assert rh.run(lambda: api) == 0
    st = env["state"]
    assert not (st / "STARTED").exists() and not (st / "gap.json").exists() and not (st / "GAVE_UP").exists()
    assert (st / "gap_aborted_20261022.json").exists() and (st / "ledger_deviation_draft_aborted_20261022.md").exists()
    assert json.loads((st / "schedule.json").read_text())["not_before_date"] == "2026-10-23"
    assert env["calls"]["queue"][-1] == "resume" and env["calls"]["supervise"] == 1
    assert not (env["home"] / "run/queue/PAUSE").exists()
    head, lines, _ = env["calls"]["notify"][-1]
    assert "server unchanged" in head and any("2026-10-23" in ln for ln in lines)


def test_non_retryable_rejection_gives_up(env):
    api = FakeApi(reject=rh.ResizeRejected(400, "LimitExceeded", "limit"))
    assert rh.run(lambda: api) == 0
    assert (env["state"] / "GAVE_UP").exists()


def test_guard_refusal_touches_nothing(env):
    api = FakeApi(others=[{**ME, "id": "o", "name": "arepo-research"}])
    assert rh.run(lambda: api) == 0
    assert not api.calls and not env["calls"]["queue"] and env["calls"]["stopped"] == 0
    assert (env["state"] / "GAVE_UP").exists() and not (env["tmp"] / "oci_retry/DONE").exists()


def test_pass_still_running_at_deadline_skips_and_keeps_existing_pause(env):
    (env["home"] / "run/queue/PAUSE").write_text("owner pause")
    fd = os.open(env["tmp"] / "collector.lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)  # the 02:31 pass holds the lock past 03:05
    try:
        api = FakeApi()
        assert rh.run(lambda: api) == 0
    finally:
        os.close(fd)
    assert not api.calls and env["clock"].t >= T("2026-10-22T03:05:00")
    assert "pause" not in env["calls"]["queue"] and "resume" not in env["calls"]["queue"]
    assert (env["home"] / "run/queue/PAUSE").read_text() == "owner pause"
    assert json.loads((env["state"] / "schedule.json").read_text())["not_before_date"] == "2026-10-23"
    assert not (env["state"] / "ledger_deviation_draft_aborted_20261022.md").exists()  # nothing was interrupted
    assert "skipped" in env["calls"]["notify"][-1][0]


def test_heavy_queue_job_is_stopped_light_job_waited_for(env, monkeypatch):
    jobs = [{"id": "q_heavy", "runner_pid": 11, "mem_mb": 3000}, {"id": "q0460_lt2", "runner_pid": 12, "mem_mb": 480}]
    alive = {11: True, 12: True}

    def running():
        return [j for j in jobs if alive[j["runner_pid"]]]

    def sleep(s):
        env["clock"].t += timedelta(seconds=s)
        alive[12] = False  # the light job finishes on its own
        if "stop" in env["calls"]["queue"]:
            alive[11] = False
    monkeypatch.setattr(rh, "running_queue_jobs", running)
    monkeypatch.setattr(rh, "pid_alive", lambda pid: alive.get(pid, False))
    monkeypatch.setattr(rh, "_sleep", sleep)
    assert rh.run(lambda: FakeApi()) == 0
    gap = json.loads((env["state"] / "gap.json").read_text())
    assert gap["queue_jobs_stopped"] == ["q_heavy"]


def test_error_mid_run_restores_collection(env, monkeypatch):
    monkeypatch.setattr(rh, "stop_monitors", lambda timeout_s=120: (_ for _ in ()).throw(RuntimeError("kill failed")))
    assert rh.run(lambda: FakeApi()) == 1
    assert env["calls"]["queue"][-1] == "resume" and env["calls"]["supervise"] == 1
    assert not (env["state"] / "STARTED").exists() and not (env["state"] / "GAVE_UP").exists()
    assert json.loads((env["state"] / "schedule.json").read_text())["not_before_date"] == "2026-10-23"
    assert "kill failed" in env["calls"]["notify"][-1][1][0]


# ---------------------------------------------------------------- post_resize_check
def test_grid_points_and_passes():
    lb, fa = T("2026-10-22T03:00:00"), T("2026-10-22T03:14:00")
    assert prc.grid_points_missed(lb, fa) == ["2026-10-22T03:10:00Z"]
    assert prc.grid_points_missed(T("2026-10-22T03:00:00"), T("2026-10-22T03:08:00")) == []
    assert prc.passes_in(T("2026-10-22T03:01:00"), T("2026-10-22T03:20:00")) == []
    assert prc.passes_in(T("2026-10-22T04:00:00"), T("2026-10-22T06:40:00")) == ["2026-10-22T04:31:00Z", "2026-10-22T06:31:00Z"]


@pytest.fixture
def penv(tmp_path, monkeypatch):
    home, st, logs = tmp_path / "arepo", tmp_path / "resize", tmp_path / "logs"
    (home / "run/queue").mkdir(parents=True)
    st.mkdir()
    logs.mkdir()
    for k, v in {"HOME": home, "STATE": st, "LOGS": logs, "QUEUE_RUN": home / "run/queue",
                 "POLLER_LOG": logs / "cross-venue-live.err", "TRADE_LOG": logs / "live-trade-monitor.err"}.items():
        monkeypatch.setattr(prc, k, v)
    calls = {"notify": [], "resume": 0, "supervise": 0}
    mons = {"v": {"live-trade-monitor": "running pid 1", "cross-venue-live": "running pid 2"}}

    def resume():
        calls["resume"] += 1
        (home / "run/queue/PAUSE").unlink(missing_ok=True)
        return 0

    def supervise():
        calls["supervise"] += 1
        return mons["v"]
    monkeypatch.setattr(prc, "notify", lambda h, lines, key, severity="high": calls["notify"].append((h, lines)))
    monkeypatch.setattr(prc, "queue_resume", resume)
    monkeypatch.setattr(prc, "run_supervise", supervise)
    monkeypatch.setattr(prc, "metadata_shape", lambda: {"ocpus": 2.0, "memory_gb": 12.0})
    monkeypatch.setattr(prc, "boot_id", lambda: "boot-2")
    monkeypatch.setattr(prc, "boot_time", lambda: T("2026-10-22T03:06:00"))
    monkeypatch.setattr(prc, "host_shape", lambda: {"nproc": 2, "mem_total_gib": 11.4})
    (home / "run/queue/PAUSE").write_text("x")
    gap = {"attempt_night": "2026-10-22", "boot_id_before": "boot-1", "queue_was_paused": False,
           "queue_paused_utc": "2026-10-22T02:40:05Z", "collector_lock_utc": "2026-10-22T03:00:10Z",
           "light_jobs_held_utc": "2026-10-22T03:00:20Z", "monitors_stopped_utc": "2026-10-22T03:00:30Z",
           "api_called_utc": "2026-10-22T03:00:40Z", "accepted_utc": "2026-10-22T03:00:41Z",
           "shape_before": {"nproc": 1, "mem_total_gib": 5.52}}
    (st / "gap.json").write_text(json.dumps(gap))
    (st / "STARTED").write_text("x")
    return {"home": home, "st": st, "logs": logs, "calls": calls, "mons": mons}


def _poller_log(path: Path, times: list[str]) -> None:
    path.write_text("".join(f'2026-10-22 00:00:00,000 INFO cycle {i}: {{"t": "{t}", "pairs": 1}}\n' for i, t in enumerate(times)))


def test_post_check_noop_without_started(penv):
    (penv["st"] / "STARTED").unlink()
    assert prc.check(T("2026-10-22T03:10:00")) == 0
    assert not penv["calls"]["notify"] and not penv["calls"]["supervise"]


def test_post_check_waits_for_restart(penv, monkeypatch):
    monkeypatch.setattr(prc, "boot_id", lambda: "boot-1")
    monkeypatch.setattr(prc, "host_shape", lambda: {"nproc": 1, "mem_total_gib": 5.52})
    assert prc.check(T("2026-10-22T03:20:00")) == 0
    assert not (penv["st"] / "DONE").exists() and not penv["calls"]["supervise"]


def test_post_check_no_restart_after_40_min_restores(penv, monkeypatch):
    monkeypatch.setattr(prc, "boot_id", lambda: "boot-1")
    monkeypatch.setattr(prc, "host_shape", lambda: {"nproc": 1, "mem_total_gib": 5.52})
    _poller_log(penv["logs"] / "cross-venue-live.err", ["2026-10-22T03:00:00Z", "2026-10-22T03:22:00Z"])
    assert prc.check(T("2026-10-22T03:45:00")) == 0
    assert (penv["st"] / "DONE").read_text().split()[1] == "no_restart"
    assert penv["calls"]["resume"] == 1 and "did not happen" in penv["calls"]["notify"][-1][0]


def test_post_check_restored_but_waits_for_first_poll(penv):
    _poller_log(penv["logs"] / "cross-venue-live.err", ["2026-10-22T03:00:00Z"])
    assert prc.check(T("2026-10-22T03:08:40")) == 0
    assert not (penv["st"] / "DONE").exists()
    assert penv["calls"]["resume"] == 1 and penv["calls"]["supervise"] == 1  # restored at once
    assert not penv["calls"]["notify"]


def test_post_check_success_records_gap_and_notifies(penv):
    _poller_log(penv["logs"] / "cross-venue-live.err", ["2026-10-22T02:58:00Z", "2026-10-22T03:00:00Z", "2026-10-22T03:12:00Z"])
    assert prc.check(T("2026-10-22T03:13:00")) == 0
    st = penv["st"]
    assert (st / "DONE").read_text().split()[1] == "resized"
    gap = json.loads((st / "gap.json").read_text())
    assert gap["gap_end_utc"] == "2026-10-22T03:12:00Z" and gap["result"]["problems"] == []
    assert gap["result"]["measured"]["poller"]["grid_600s_origins_without_poll"] == ["2026-10-22T03:10:00Z"]
    assert gap["result"]["measured"]["poller"]["missed_120s_cycles"] == 5
    head, lines = penv["calls"]["notify"][-1]
    assert head == "Server resized: 2 CPUs, 12 GB"
    assert lines == ["Server resized: 2 CPUs, 12 GB. Downtime 12 min. Collection back to normal."]
    draft = (st / "ledger_deviation_draft.md").read_text()
    assert "2026-10-22T03:10:00Z" in draft and "Not backfilled" in draft
    assert prc.check(T("2026-10-22T03:23:00")) == 0 and len(penv["calls"]["notify"]) == 1  # idempotent


def test_post_check_existing_owner_pause_is_kept(penv):
    gap = json.loads((penv["st"] / "gap.json").read_text())
    gap["queue_was_paused"] = True
    (penv["st"] / "gap.json").write_text(json.dumps(gap))
    _poller_log(penv["logs"] / "cross-venue-live.err", ["2026-10-22T03:00:00Z", "2026-10-22T03:12:00Z"])
    assert prc.check(T("2026-10-22T03:13:00")) == 0
    assert penv["calls"]["resume"] == 0 and (penv["home"] / "run/queue/PAUSE").exists()


def test_post_check_reports_problems_after_30_min(penv):
    penv["mons"]["v"] = {"live-trade-monitor": "running pid 1", "cross-venue-live": "NOT running (last exit 1)"}
    _poller_log(penv["logs"] / "cross-venue-live.err", ["2026-10-22T03:00:00Z"])
    assert prc.check(T("2026-10-22T03:37:00")) == 0
    gap = json.loads((penv["st"] / "gap.json").read_text())
    assert any("cross-venue-live" in p for p in gap["result"]["problems"])
    assert penv["calls"]["notify"][-1][0] == "Server resize: needs a look"
