# AREPO research queue (Oracle host)

Durable job queue for the autonomous programme (mission §2, §8). Specs live here in the repo; the worker
`scripts/oracle/queue_worker.py` runs them on `ssh oracle`. Server compute keeps running through Claude usage limits
and session ends; nothing here calls Claude or any paid API.

## How it works
- **Specs:** `jobs/<id>.json`, one per job. Fields are `id`, `title`, `family`, `priority` (higher runs first),
  `expected_value`, `data`, `resources.mem_mb`, `depends_on`, `argv`, `timeout_s`, `max_retries`, `outputs`,
  `next_action` and `notes`.
  - `argv[0]` must be a script under `backend/scripts/`. It runs with the host venv, `cwd=backend`.
  - Optional `repeat {max_runs, until_log_regex}` re-queues a resumable, budgeted job until its log shows completion.
  - Add a job by committing a spec and running `scripts/oracle/deploy.sh`.
- **Runtime state** lives on the host at `~/arepo/run/queue/` (deploy never touches it):
  - `state/<id>.json`;
  - `logs/<id>.<attempt>.log`;
  - `attempts.jsonl` (every attempt, including failures, timeouts and interruptions);
  - `status.json` (dashboard snapshot).
- **Cron** runs `queue_worker.py tick` every 2 minutes; the line is in `scripts/oracle/crontab.txt`. A tick:
  - takes the worker lock;
  - marks a job whose runner vanished (reboot, kill, OOM) as `interrupted`, counting it as an attempt;
  - starts at most one job, only if the queue is not paused, the collector pass is not running and
    `MemAvailable ≥ mem_mb + 1200 MB`.
- **Each job:**
  - runs detached at nice 19;
  - has an address-space cap of 2 × `mem_mb`;
  - is killed (process group) at `timeout_s`;
  - is retried with backoff (5 min, 30 min, 2 h) up to `max_retries`, then becomes `failed`.
- **Idempotency:** a job id is terminal once `done`. A spec changed after completion is ignored; use a new id.
- **Concurrency:** one job at a time. The host has 1 OCPU and about 5.6 GiB RAM, shared with the collector and monitors.

## Statuses
- `queued`
- `running`
- `retry_wait` (backoff)
- `interrupted` (will retry)
- `done`
- `failed` (retries exhausted)
- `invalid` (bad spec)
- `cancelled`

## Manual control (on the host)
```bash
ssh oracle
cd ~/arepo && Q=".venv/bin/python scripts/oracle/queue_worker.py"
$Q status            # print status.json
$Q pause             # no new job starts; a running job finishes
$Q resume
$Q stop              # pause + SIGTERM the running job (re-queued, not counted as a failure)
$Q retry <id>        # re-queue a failed/interrupted job with a fresh retry budget
$Q cancel <id>
```
To remove the worker completely, delete its two lines from `crontab -e`.

## Verified (2026-10-15)
- **Local (macOS):**
  - dependency ordering;
  - error leading to `failed`;
  - timeout kill;
  - invalid `argv` rejected (`../../etc/passwd`);
  - kill -9 of runner and job, giving `interrupted` then retry then `done`;
  - `stop` giving re-queue (attempt not counted), then pause, resume and `done`.
- **Host:**
  - `q0001_selftest` started;
  - runner and job were killed with -9 mid-run;
  - the next tick recorded `interrupted` and started attempt 2, which then ran under cron.
