#!/bin/bash
# Arepo overnight three-stage runner
# 1) Wait for the latest cohort's 1h horizon, then collect and record it.
# 2) Run the full runtime-acceptance Claude prompt.
# 3) After the expected Claude usage reset, continue the same task.

set -u
set -o pipefail

REPO="$HOME/Projects/astrolabe"
BACKEND="$REPO/backend"
PROMPT_FILE="$REPO/AREPO_FINAL_RUNTIME_ACCEPTANCE_FIX_PROMPT.md"
PYTHON="$BACKEND/.venv/bin/python"
CLAUDE_BIN="$(command -v claude || true)"

# User estimated 3h25m until reset. Add a 5-minute safety buffer.
RESET_WAIT_MINUTES=210
ONE_HOUR_BUFFER_SECONDS=120

RUN_ID="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$REPO/overnight-runs/$RUN_ID"
MASTER_LOG="$RUN_DIR/master.log"
FORWARD_LOG="$RUN_DIR/research-forward.log"
STATUS_LOG="$RUN_DIR/research-status.json"
CLAUDE_FIRST_LOG="$RUN_DIR/claude-first-pass.log"
CLAUDE_RESUME_LOG="$RUN_DIR/claude-resume-pass.log"
INITIAL_INPUT="$RUN_DIR/claude-first-input.txt"
RESUME_INPUT="$RUN_DIR/claude-resume-input.txt"
PID_FILE="$REPO/overnight-three-stage.pid"

mkdir -p "$RUN_DIR"
exec >>"$MASTER_LOG" 2>&1

START_EPOCH="$(date +%s)"
RESUME_EPOCH=$((START_EPOCH + RESET_WAIT_MINUTES * 60))

echo "=== Arepo overnight three-stage runner ==="
echo "Started: $(date)"
echo "Run directory: $RUN_DIR"
echo "Expected resume attempt: $(date -r "$RESUME_EPOCH")"
echo

fail() {
  echo "ERROR: $1"
  exit 1
}

[ -d "$REPO/.git" ] || fail "Repository not found at $REPO"
[ -f "$BACKEND/astrolabe.db" ] || fail "Database not found at $BACKEND/astrolabe.db"
[ -x "$PYTHON" ] || fail "Virtual-environment Python not found at $PYTHON"
[ -f "$PROMPT_FILE" ] || fail "Prompt not found at $PROMPT_FILE"
[ -n "$CLAUDE_BIN" ] || fail "Claude Code is not available on PATH"

cd "$REPO" || exit 1

# Refuse to proceed over tracked, uncommitted changes. Untracked DB backups are allowed.
git diff --quiet || fail "Tracked working-tree changes exist. Commit or revert them first."
git diff --cached --quiet || fail "Staged changes exist. Commit them first."

echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo

# Back up the valid database before any automated work.
DB_BACKUP="$BACKEND/astrolabe.db.backup-overnight-$RUN_ID"
cp "$BACKEND/astrolabe.db" "$DB_BACKUP" || fail "Database backup failed"
echo "Database backup: $DB_BACKUP"

# Derive the collection time from the latest cohort's real causal origin.
DUE_EPOCH="$("$PYTHON" - <<'PY'
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

db = Path.home() / "Projects" / "astrolabe" / "backend" / "astrolabe.db"
conn = sqlite3.connect(db)
row = conn.execute(
    """
    SELECT evaluation_origin_at
    FROM research_cohorts
    WHERE frozen = 1
    ORDER BY evaluation_origin_at DESC
    LIMIT 1
    """
).fetchone()
conn.close()

if not row or not row[0]:
    raise SystemExit("No frozen cohort with evaluation_origin_at was found.")

value = str(row[0]).replace("Z", "+00:00")
dt = datetime.fromisoformat(value)
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)

# First horizon plus a two-minute buffer.
print(int(dt.timestamp()) + 3600 + 120)
PY
)" || fail "Could not calculate the 1h collection time"

NOW_EPOCH="$(date +%s)"
if [ "$DUE_EPOCH" -gt "$NOW_EPOCH" ]; then
  DELAY=$((DUE_EPOCH - NOW_EPOCH))
  echo "Latest cohort 1h collection will run at: $(date -r "$DUE_EPOCH")"
  echo "Waiting $DELAY seconds."
  sleep "$DELAY"
else
  echo "The latest cohort's 1h horizon is already due. Continuing immediately."
fi

echo
echo "=== Stage 1: collect the one-hour result ==="
echo "Started: $(date)"

cd "$BACKEND" || exit 1

"$PYTHON" -m astrolabe.evaluation.research_cli research-forward \
  >"$FORWARD_LOG" 2>&1
FORWARD_EXIT=$?

"$PYTHON" -m astrolabe.evaluation.research_cli research-status \
  >"$STATUS_LOG" 2>&1
STATUS_EXIT=$?

echo "research-forward exit: $FORWARD_EXIT"
echo "research-status exit: $STATUS_EXIT"
echo "--- research-forward ---"
cat "$FORWARD_LOG"
echo "--- research-status ---"
cat "$STATUS_LOG"

# Build a context-rich first Claude input.
cd "$REPO" || exit 1

{
  cat "$PROMPT_FILE"

  cat <<'CONTEXT'

# Additional authoritative overnight context

A valid local six-hour prospective cohort exists in `backend/astrolabe.db`.
Its causal timing was verified before this run:

- `evaluation_origin_at` equals the actual `frozen_at`
- the scheduled bucket is not used as the forward-evaluation origin
- the duplicate freeze guard worked
- the immediate early `research-forward` run wrote zero outcomes, as required

Preserve `backend/astrolabe.db` and every valid research row.

Do not delete, reset, recreate, replace, clean, or destructively migrate the database.
A timestamped backup was created immediately before this automated sequence.

The two supplied market routes worked after stopping Next.js, deleting `.next`,
running `npm ci`, and restarting `npm run dev`. Therefore the earlier
`vendor-chunks/geist.js` error was stale or corrupted generated Next.js output,
not a current routing-logic failure. Document and guard against this with a safe
clean-development workflow, but do not redesign working market routes unnecessarily.

Manual runtime testing still reproduced these failures:

- the information popover leaves the right side of the real viewport
- Signal Lab measured `scrollWidth: 632`, `clientWidth: 574`
- `Why this fired` remains too close to the qualification badge
- Replay does not show the real prospective six-hour research cohort
- Replay does not show scheduled time, actual freeze time, evaluation origin, or lateness
- the synthetic demonstration occupies the prospective view
- API polling floods the console when the backend is unavailable

The one-hour collection was run immediately before this Claude pass.
Its exact output follows.

Do not deploy external services during this pass.
CONTEXT

  echo
  echo "## research-forward result"
  cat "$FORWARD_LOG"
  echo
  echo "## research-status result"
  cat "$STATUS_LOG"
  echo
  echo "## Git state before Claude"
  git branch --show-current
  git log -3 --oneline
  git status --short
} >"$INITIAL_INPUT"

echo
echo "=== Stage 2: run the main Claude runtime-fix prompt ==="
echo "Started: $(date)"
echo "Claude log: $CLAUDE_FIRST_LOG"

export CLAUDE_CODE_SUBAGENT_MODEL=sonnet

set +e
cat "$INITIAL_INPUT" | "$CLAUDE_BIN" -p \
  "Read the complete specification and authoritative runtime context from standard input. Work autonomously from the repository root. Implement every requirement, preserve the valid database, run real browser acceptance tests, commit completed work, and push the resulting branch. If usage limits stop you, leave a precise checkpoint in CHECKPOINT.md and commit and push the smallest safe completed unit before exiting." \
  --model opus \
  --dangerously-skip-permissions \
  --verbose \
  >"$CLAUDE_FIRST_LOG" 2>&1
CLAUDE_FIRST_EXIT=$?
set -e

echo "First Claude pass exit: $CLAUDE_FIRST_EXIT"
echo "First Claude pass finished: $(date)"

# Wait until the estimated account reset. If the first pass ran beyond it, continue now.
NOW_EPOCH="$(date +%s)"
if [ "$RESUME_EPOCH" -gt "$NOW_EPOCH" ]; then
  DELAY=$((RESUME_EPOCH - NOW_EPOCH))
  echo
  echo "Waiting $DELAY seconds for the estimated Claude usage reset."
  echo "Resume scheduled for: $(date -r "$RESUME_EPOCH")"
  sleep "$DELAY"
else
  echo
  echo "Estimated reset time has passed. Continuing immediately."
fi

cd "$REPO" || exit 1

{
  cat "$PROMPT_FILE"

  cat <<'CONTEXT'

# Resume instruction

Continue the exact runtime-acceptance task from the most recent Claude Code
conversation in this repository.

The previous pass may have stopped because the usage limit was reached.
Do not restart from scratch and do not discard completed work.

First inspect:

- the current branch
- `git status`
- recent commits
- `CHECKPOINT.md`
- `TASKS.md`
- `DECISIONS.md`
- `docs/FINAL_RUNTIME_ACCEPTANCE.md`
- current test results
- the valid `backend/astrolabe.db`

Preserve the database and all valid research rows.

Continue from the first incomplete or failed requirement. Re-run the real browser
acceptance checks, not only unit tests. Fix all remaining confirmed failures.
Commit and push the final work.

If the previous pass already met every completion gate, independently verify it,
run the required test suites, and provide the exact local verification report
instead of making unnecessary changes.
CONTEXT

  echo
  echo "## Original one-hour collection result"
  cat "$FORWARD_LOG"
  echo
  echo "## Original research status"
  cat "$STATUS_LOG"
  echo
  echo "## Current Git state before resume"
  git branch --show-current
  git log -8 --oneline
  git status --short
  echo
  echo "## Tail of first Claude pass"
  tail -n 250 "$CLAUDE_FIRST_LOG"
} >"$RESUME_INPUT"

echo
echo "=== Stage 3: continue Claude after the expected reset ==="
echo "Started: $(date)"
echo "Claude resume log: $CLAUDE_RESUME_LOG"

set +e
cat "$RESUME_INPUT" | "$CLAUDE_BIN" --continue -p \
  "Resume the most recent Claude Code task in this repository. Use the supplied specification, collection results, checkpoint, Git state, and previous-pass tail. Continue from the first incomplete requirement, preserve the database, finish the real runtime acceptance work, run all tests, commit, and push." \
  --model opus \
  --dangerously-skip-permissions \
  --verbose \
  >"$CLAUDE_RESUME_LOG" 2>&1
CLAUDE_RESUME_EXIT=$?
set -e

echo "Resume Claude pass exit: $CLAUDE_RESUME_EXIT"
echo
echo "=== Overnight sequence finished ==="
echo "Finished: $(date)"
echo "Run directory: $RUN_DIR"
echo "Master log: $MASTER_LOG"
echo "Forward log: $FORWARD_LOG"
echo "Status log: $STATUS_LOG"
echo "First Claude log: $CLAUDE_FIRST_LOG"
echo "Resume Claude log: $CLAUDE_RESUME_LOG"
echo
echo "Final Git state:"
git branch --show-current
git log -5 --oneline
git status --short
