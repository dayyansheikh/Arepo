"""D116 launch wrapper (mirrors the D114 wrapper: launch/stdout/stderr/result files under data-dumps).

Preconditions checked BEFORE any request (any failure: exit without launching, nothing written to run roots):
frozen hashes match the freeze record, launch HEAD descends from 8afbdff, clean tracked tree, free disk
>= reservation + 1 GiB (the script re-checks the reservation), no derived root exists.
"""
import hashlib, json, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/Users/DayyanSheikh/Projects/astrolabe')
DD = REPO / 'data-dumps'
PREFIX = 'fs2_d116_integrated_1'
SCRATCH = Path('/private/tmp/claude-501/arepo_d116'); SCRATCH.mkdir(parents=True, exist_ok=True)
FROZEN = {
    'docs/implementation/PHASE_03_D116_INTEGRATED_VALIDATION_PROTOCOL.md':
        '1b1b81bb124554191197ca280a0c8a7917dfd684b28f4e26681629b02a6fe7c9',
    'backend/astrolabe/research_panel/d116_evaluator.py':
        '772b984a83f7d984f9d127401d3fe38cd68fcb339bb828f88438176a29893ab9',
    'backend/scripts/evaluate_d116.py':
        '41eadf25bf1445de6e3d2bd53bc37592ec90cecb40b67b2109cca66ff7f1a4ad',
    'backend/tests/unit/test_research_panel_d116_evaluator.py':
        '4a27a4b63bbffe963644f2aea5f9863cb9e78e3903ca7750ae0a7baa05d56248',
}
RESERVATION = 13308526592
MARGIN = 1024 ** 3


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a):
    return subprocess.run(['git', *a], cwd=REPO, capture_output=True, text=True)


def main():
    for rel, h in FROZEN.items():
        got = sha(REPO / rel)
        if got != h:
            sys.exit(f'FROZEN HASH MISMATCH {rel}: {got}')
    if git('merge-base', '--is-ancestor', '8afbdff', 'HEAD').returncode != 0:
        sys.exit('HEAD does not descend from 8afbdff')
    if git('status', '--porcelain', '--untracked-files=no').stdout.strip():
        sys.exit('tracked tree not clean')
    free = shutil.disk_usage(REPO).free
    if free < RESERVATION + MARGIN:
        sys.exit(f'insufficient free disk {free}')
    for name in ('fs2_panel_d116_integrated_1', 'fs2_selection_panel_d116_integrated_1',
                 'fs2_screening_worker_d116_integrated_1', 'fs2_activation_d116_integrated_1',
                 'fs2_runtime_d116_integrated_1'):
        if (DD / name).exists():
            sys.exit(f'root exists: {name}')
    for suffix in ('launch.json', 'stdout.log', 'stderr.log', 'result.json'):
        if (DD / f'{PREFIX}_{suffix}').exists():
            sys.exit(f'wrapper file exists: {suffix}')
    text = (REPO / 'docs/implementation/PHASE_03_D116_INTEGRATED_VALIDATION_PROTOCOL.md').read_text()
    blocks = re.findall(r'```python\n(.*?)```', text, flags=re.S)
    if len(blocks) != 1:
        sys.exit(f'expected exactly one python block, found {len(blocks)}')
    script = SCRATCH / 'arepo_d116_frozen.py'
    script.write_text(blocks[0])
    head = git('rev-parse', 'HEAD').stdout.strip()
    db = SCRATCH / 'd116_isolated.sqlite'
    env = dict(os.environ, AUTO_MIGRATE='false', DIGEST_EMAIL_ENABLED='false',
               DATABASE_URL=f'sqlite+aiosqlite:///{db}', PYTHONPATH=str(REPO / 'backend'))
    cmd = ['caffeinate', '-is', str(REPO / 'backend/.venv/bin/python'), str(script)]
    launch = {'implementation_commit': head, 'started_at': datetime.now(timezone.utc).isoformat(),
              'script_sha256': sha(script), 'protocol_sha256': FROZEN[next(iter(FROZEN))],
              'frozen_hashes_verified': True, 'ancestor_8afbdff': True, 'free_bytes': free,
              'command': cmd, 'env_overrides': {'AUTO_MIGRATE': 'false',
                                                'DIGEST_EMAIL_ENABLED': 'false',
                                                'DATABASE_URL': str(db)}}
    (DD / f'{PREFIX}_launch.json').write_text(json.dumps(launch, indent=2))
    t0 = time.monotonic_ns()
    with open(DD / f'{PREFIX}_stdout.log', 'w') as out, open(DD / f'{PREFIX}_stderr.log', 'w') as err:
        rc = subprocess.run(cmd, cwd=REPO / 'backend', env=env, stdout=out, stderr=err).returncode
    result = dict(launch, completed_at=datetime.now(timezone.utc).isoformat(),
                  elapsed_ns=str(time.monotonic_ns() - t0), returncode=rc)
    (DD / f'{PREFIX}_result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'returncode': rc, 'head': head}))


if __name__ == '__main__':
    main()
