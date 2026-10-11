"""D118 launch wrapper (mirrors the D116 wrapper: launch/stdout/stderr/result under data-dumps).

Preconditions checked BEFORE any request (any failure: exit without launching, nothing written to
run roots), D118 protocol section 7:

1. clean tracked tree; launch HEAD descends from 8afbdff;
2. the frozen hashes are read from the artefact table of
   ``docs/implementation/PHASE_03_D118_FREEZE_RECORD.md`` and every file matches; a missing record,
   a missing or extra row, or an unfilled hash fails closed (no hashes live in this file);
3. the freeze record names the freeze commit (``Freeze commit: `<40 hex>```) and
   ``git diff --quiet <freeze commit> HEAD -- backend/astrolabe backend/scripts/d118_launch.py
   backend/scripts/evaluate_d118.py`` succeeds (no code change since the freeze);
4. free disk >= reservation + 1 GiB (the script re-checks the reservation);
5. the current UTC time is not within HH:15-HH:45 of an even hour (research-lab collector window)
   and no AREPO collector process is running (D116 addendum near-miss);
6. no derived root or wrapper file exists.

After the run the collectors are checked again and recorded in result.json.

The isolated database URL is recorded in full in launch.json (D116 recorded a bare path).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path('/Users/DayyanSheikh/Projects/astrolabe')
DD = REPO / 'data-dumps'
PREFIX = 'fs2_d118_control_pairing_1'
RUN = 'd118_control_pairing_1'
PROTOCOL = 'docs/implementation/d118/D118_CONTROL_PAIRING_PROTOCOL.md'
FREEZE_RECORD = 'docs/implementation/PHASE_03_D118_FREEZE_RECORD.md'
SCRATCH = Path('/private/tmp/claude-501/arepo_d118')
REQUIRED_FROZEN = frozenset({
    PROTOCOL,
    'backend/astrolabe/research_panel/d118_evaluator.py',
    'backend/astrolabe/research_panel/d116_evaluator.py',
    'backend/astrolabe/research_panel/panel_declaration.py',
    'backend/astrolabe/research_panel/panel_selection.py',
    'backend/scripts/evaluate_d118.py',
    'backend/scripts/d118_launch.py',
    'backend/tests/unit/test_research_panel_d118_evaluator.py',
    'backend/tests/unit/test_research_panel_liquidity_population.py',
    'backend/tests/unit/test_d118_launch.py',
})
# Code paths that must be byte-identical between the freeze commit and the launch HEAD.
FROZEN_CODE_PATHS = ('backend/astrolabe', 'backend/scripts/d118_launch.py',
                     'backend/scripts/evaluate_d118.py')
RESERVATION = 14449901568  # 7 GiB frame cap + 4x3 panel/window/runtime reservation + 34 MiB
MARGIN = 1024 ** 3
COLLECTORS = ('collect_universe_snapshot', 'sweep_books', 'sample_trades', 'run_forecast')
FREEZE_COMMIT = re.compile(r'^Freeze commit:\s*`([0-9a-f]{40})`\s*$', flags=re.M)
ROW = re.compile(r'^\|\s*`([^`]+)`[^|]*\|\s*`([^`]*)`\s*\|\s*$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')


class PreconditionError(Exception):
    """A launch precondition failed; nothing was launched or written."""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(['git', *args], cwd=REPO, capture_output=True, text=True)


def parse_freeze_record(text):
    """Artefact path -> sha256 from the freeze-record table; fail closed on anything unexpected.

    Rows are ``| `path` (optional note) | `sha256` |``. Only rows whose first code span is a
    repository path (contains ``/``) are artefacts; other rows (for example the classification
    table sha) are ignored here. Exactly the required artefacts must appear, once each, with a
    64-hex lowercase hash.
    """
    table = {}
    for line in text.splitlines():
        match = ROW.match(line.strip())
        if not match or '/' not in match.group(1):
            continue
        path, digest = match.groups()
        if path in table:
            raise PreconditionError(f'duplicate freeze-record row: {path}')
        if not HEX64.match(digest):
            raise PreconditionError(f'unfilled or invalid hash for {path}: {digest!r}')
        table[path] = digest
    if set(table) != REQUIRED_FROZEN:
        missing = sorted(REQUIRED_FROZEN - set(table))
        extra = sorted(set(table) - REQUIRED_FROZEN)
        raise PreconditionError(f'freeze record artefacts differ: missing {missing} extra {extra}')
    return table


def parse_freeze_commit(text):
    """The single ``Freeze commit: `<40 hex>``` line of the freeze record; fail closed otherwise."""
    found = FREEZE_COMMIT.findall(text)
    if len(found) != 1:
        raise PreconditionError(
            f'freeze record must name exactly one freeze commit, found {len(found)}')
    return found[0]


def load_frozen(repo=REPO):
    record = repo / FREEZE_RECORD
    if not record.is_file():
        raise PreconditionError(f'D118 is not frozen: {FREEZE_RECORD} absent')
    text = record.read_text()
    return parse_freeze_record(text), parse_freeze_commit(text)


def check_code_unchanged(freeze_commit, run_git=None):
    """``git diff --quiet <freeze commit> HEAD -- <frozen code paths>``; non-zero refuses."""
    run_git = run_git or git
    rc = run_git('diff', '--quiet', freeze_commit, 'HEAD', '--', *FROZEN_CODE_PATHS).returncode
    if rc != 0:
        raise PreconditionError(f'frozen code differs from freeze commit {freeze_commit} (rc {rc})')


def verify_frozen(table, repo=REPO):
    for rel, expected in table.items():
        path = repo / rel
        if not path.is_file():
            raise PreconditionError(f'frozen artefact missing: {rel}')
        got = sha(path)
        if got != expected:
            raise PreconditionError(f'FROZEN HASH MISMATCH {rel}: {got} != {expected}')


def running_collectors(pgrep=None, own_pids=None):
    """name -> matching process lines for every running research-lab collector."""
    own = {str(p) for p in (own_pids or (os.getpid(), os.getppid()))}
    pgrep = pgrep or (lambda name: subprocess.run(['pgrep', '-fl', name], capture_output=True,
                                                  text=True).stdout)
    found = {}
    for name in COLLECTORS:
        lines = [line for line in pgrep(name).splitlines()
                 if line.strip() and line.split(maxsplit=1)[0] not in own]
        if lines:
            found[name] = lines
    return found


def check_collector_window(now):
    """Refuse inside HH:15-HH:45 (inclusive) of an even UTC hour: the collector window."""
    now = now.astimezone(UTC)
    if now.hour % 2 == 0 and 15 <= now.minute <= 45:
        raise PreconditionError(f'inside the even-hour collector window: {now.isoformat()}')


def check_disk(free):
    if free < RESERVATION + MARGIN:
        raise PreconditionError(f'insufficient free disk {free} < {RESERVATION + MARGIN}')


def check_absent(dd=DD):
    for name in (f'fs2_panel_{RUN}', f'fs2_selection_panel_{RUN}', f'fs2_screening_worker_{RUN}',
                 f'fs2_activation_{RUN}', f'fs2_runtime_{RUN}'):
        if (dd / name).exists():
            raise PreconditionError(f'root exists: {name}')
    for suffix in ('launch.json', 'stdout.log', 'stderr.log', 'result.json', 'evaluation.json'):
        if (dd / f'{PREFIX}_{suffix}').exists():
            raise PreconditionError(f'wrapper file exists: {PREFIX}_{suffix}')


def extract_script(text):
    blocks = re.findall(r'```python\n(.*?)```', text, flags=re.S)
    if len(blocks) != 1:
        raise PreconditionError(f'expected exactly one python block, found {len(blocks)}')
    return blocks[0]


def database_url(scratch=SCRATCH):
    return f'sqlite+aiosqlite:///{scratch / "d118_isolated.sqlite"}'


def preconditions():
    frozen, freeze_commit = load_frozen()
    verify_frozen(frozen)
    if git('merge-base', '--is-ancestor', '8afbdff', 'HEAD').returncode != 0:
        raise PreconditionError('HEAD does not descend from 8afbdff')
    if git('status', '--porcelain', '--untracked-files=no').stdout.strip():
        raise PreconditionError('tracked tree not clean')
    check_code_unchanged(freeze_commit)
    check_collector_window(datetime.now(UTC))
    collectors = running_collectors()
    if collectors:
        raise PreconditionError(f'collector process running: {collectors}')
    free = shutil.disk_usage(REPO).free
    check_disk(free)
    check_absent()
    script = extract_script((REPO / PROTOCOL).read_text())
    return frozen, freeze_commit, free, script


def main():
    try:
        frozen, freeze_commit, free, script_text = preconditions()
    except PreconditionError as exc:
        sys.exit(f'D118 launch refused: {exc}')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    script = SCRATCH / 'arepo_d118_frozen.py'
    script.write_text(script_text)
    head = git('rev-parse', 'HEAD').stdout.strip()
    url = database_url()
    env = dict(os.environ, AUTO_MIGRATE='false', DIGEST_EMAIL_ENABLED='false',
               DATABASE_URL=url, PYTHONPATH=str(REPO / 'backend'))
    cmd = ['caffeinate', '-is', str(REPO / 'backend/.venv/bin/python'), str(script)]
    launch = {'implementation_commit': head, 'started_at': datetime.now(UTC).isoformat(),
              'script_sha256': sha(script), 'protocol_sha256': frozen[PROTOCOL],
              'freeze_record_sha256': sha(REPO / FREEZE_RECORD), 'frozen_hashes': frozen,
              'frozen_hashes_verified': True, 'freeze_commit': freeze_commit,
              'code_unchanged_since_freeze': True, 'ancestor_8afbdff': True,
              'outside_collector_window': True, 'free_bytes': free,
              'required_free_bytes': RESERVATION + MARGIN, 'collectors_running': {},
              'command': cmd, 'env_overrides': {'AUTO_MIGRATE': 'false',
                                                'DIGEST_EMAIL_ENABLED': 'false',
                                                'DATABASE_URL': url}}
    (DD / f'{PREFIX}_launch.json').write_text(json.dumps(launch, indent=2))
    t0 = time.monotonic_ns()
    with (open(DD / f'{PREFIX}_stdout.log', 'w') as out,
          open(DD / f'{PREFIX}_stderr.log', 'w') as err):
        rc = subprocess.run(cmd, cwd=REPO / 'backend', env=env, stdout=out, stderr=err).returncode
    elapsed = str(time.monotonic_ns() - t0)
    result = dict(launch, completed_at=datetime.now(UTC).isoformat(), elapsed_ns=elapsed,
                  returncode=rc, collectors_running_after=running_collectors())
    (DD / f'{PREFIX}_result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'returncode': rc, 'head': head}))


if __name__ == '__main__':
    main()
