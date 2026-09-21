"""Read preserved frames with their original Git-pinned implementation in a child process.

Never checkout/reset the working repository, weaken a build guard, install dependencies,
recapture a source, or substitute current parsing for original numerical facts. Temporary
code extraction is disposable; original evidence and newly clocked read receipts are not.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from astrolabe.feature_store.capture import _clock, _digest, _sync_directory
from astrolabe.feature_store.source_run import _ordered_clocks, _pair, _persist, _read

from .build_identity import verified_panel_build

VERSION = 'fs2-original-frame-read-v1'
PACKAGES = ('feature_store', 'research_panel')
_FILENAME = re.compile(r'[a-z_][a-z_0-9]*\.py\Z')
_COMMIT = re.compile(r'[0-9a-f]{40}\Z')
_ENV = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.frame import read_frame
report = read_frame(Path(sys.argv[2]))
json.dump(report, sys.stdout, sort_keys=True, separators=(",", ":"))
'''


def _git(repository, *args):
    result = subprocess.run(['git', '-C', str(repository), *args], env=_ENV,
                            capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('original implementation is unavailable in local Git')
    return result.stdout


def _blob(repository, commit, name):
    ref = commit + ':' + name
    size = int(_git(repository, 'cat-file', '-s', ref).strip())
    if not 0 <= size <= 1048576:
        raise ValueError('original source blob exceeds bounded extraction limit')
    data = _git(repository, 'show', ref)
    if len(data) != size:
        raise ValueError('original Git source size differs')
    return data


def _extract(repository, commit, build, destination):
    """Only declared direct Python files from two packages; no arbitrary archive paths."""
    if not _COMMIT.fullmatch(commit):
        raise ValueError('full lowercase immutable Git commit SHA required')
    actual = _git(repository, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if actual != commit:
        raise ValueError('original implementation must resolve to the exact commit')
    manifests = {'research_panel': build['files'],
                 'feature_store': build['source_build']['files']}
    for package in PACKAGES:
        files = manifests[package]
        if not isinstance(files, dict) or not 1 <= len(files) <= 64:
            raise ValueError('bounded original package manifest required')
        prefix = f'backend/astrolabe/{package}/'
        tracked = _git(repository, 'ls-tree', '-r', '--name-only', commit, '--', prefix)
        actual_files = {p[len(prefix):] for p in tracked.decode().splitlines() if p.endswith('.py')}
        if actual_files != set(files):
            raise ValueError('Git implementation file set differs from original build')
        for name, expected in files.items():
            if not _FILENAME.fullmatch(name):
                raise ValueError('invalid original implementation filename')
            data = _blob(repository, commit, prefix + name)
            if _digest(data) != expected:
                raise ValueError('Git implementation hash differs from original build')
            target = destination / prefix / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    name = 'backend/astrolabe/__init__.py'
    data = _blob(repository, commit, name)
    (destination / name).write_bytes(data)
    return {'packages': manifests, 'package_root_hash': _digest(data)}


def read_original_frame(frame_root, *, implementation_commit, output_root, repository=None):
    """Seal a new actual read receipt; original observation/availability clocks stay intact.

    A successful read does not make an incomplete frame complete or itself establish an
    origin, sample, model execution or SQL visibility. No old run is modified. A failed
    attempt retains its declaration/partial output and requires a fresh output directory.
    """
    build = verified_panel_build()
    frame_root, output_root = Path(frame_root), Path(output_root)
    repository = Path(repository) if repository else Path(__file__).parents[3]
    for path in (frame_root, output_root, repository):
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError('canonical absolute original-read paths required')
    if (not output_root.name.startswith('fs2_frame_read_')
            or output_root == frame_root or frame_root in output_root.parents):
        raise ValueError('separate fresh fs2_frame_read_ output directory required')
    metadata_started = _clock()
    policy, policy_ack = _pair(frame_root, 'frame_policy')
    # Only sealed original reports are consumed. No crash-repair or semantic reconstruction.
    original_report, report_ack = _pair(frame_root, 'frame_report')
    if original_report['policy_hash'] != policy_ack['payload_hash']:
        raise ValueError('original report/policy lineage differs')
    with tempfile.TemporaryDirectory(prefix='arepo_original_decoder_') as tmp:
        code = Path(tmp)
        code_manifest = _extract(repository, implementation_commit, policy['build'], code)
        output_root.mkdir(mode=0o700, exist_ok=False)
        _sync_directory(output_root.parent)
        _persist(output_root, 'read_policy', {
            'schema_version': VERSION, 'frame_root': str(frame_root),
            'frame_policy_hash': policy_ack['payload_hash'],
            'metadata_read_started_at': metadata_started,
            'frame_report_hash': report_ack['payload_hash'],
            'original_build': policy['build'], 'implementation_commit': implementation_commit,
            'extracted_code': code_manifest, 'reader_build': build,
            'reader_script_hash': _digest(_SCRIPT.encode()),
            'timeout_seconds': 300, 'max_output_bytes': 16 * 1048576,
            'purpose': 'actual verified read only; no new observation or origin admission',
        })
        _, read_policy_ack = _pair(output_root, 'read_policy')
        started = _clock()
        output = output_root / 'original_report.json'
        try:
            # -I ignores Python path/user-site environment; -B avoids source-tree bytecode writes.
            with output.open('xb') as handle:
                child = subprocess.run(
                    [sys.executable, '-I', '-B', '-c', _SCRIPT,
                     str(code / 'backend'), str(frame_root)],
                    env=_ENV, cwd=code, stdout=handle, stderr=subprocess.PIPE, timeout=300,
                )
                handle.flush()
                os.fsync(handle.fileno())
            _sync_directory(output_root)
            if child.returncode:
                raise ValueError('original-build verification refused the frame or environment')
            result_bytes = _read(output)
            result = json.loads(result_bytes)
            facts = {k: v for k, v in result.items()
                     if k not in {'frame_report_hash', 'frame_available_at'}}
            if (result['frame_report_hash'] != report_ack['payload_hash']
                    or result['frame_available_at'] != report_ack['durable_ack']
                    or facts != original_report):
                raise ValueError('original-build read output differs from sealed facts')
            verified_panel_build()
            completed = _clock()
            if not _ordered_clocks(report_ack['durable_ack'], metadata_started,
                                   read_policy_ack['durable_ack'],
                                   started, completed):
                raise ValueError('original read chronology differs')
            _persist(output_root, 'read_receipt', {
                'schema_version': VERSION, 'read_policy_hash': read_policy_ack['payload_hash'],
                'original_report_hash': report_ack['payload_hash'],
                'output_hash': _digest(result_bytes), 'output_bytes': len(result_bytes),
                'metadata_read_started_at': metadata_started,
                'verification_started_at': started, 'completed_at': completed,
                'original_provenance_class': result['provenance_class'],
                'original_state': result['state'],
                'observation_clocks_changed': False, 'origin_admitted': False,
            })
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            # Never expose upstream content/environment in an error receipt.
            _persist(output_root, 'read_failure', {
                'schema_version': VERSION, 'read_policy_hash': read_policy_ack['payload_hash'],
                'started_at': started, 'failed_at': _clock(), 'error_class': type(exc).__name__,
            })
            raise
    receipt, ack = _pair(output_root, 'read_receipt')
    return {'report': result, 'read_receipt': receipt, 'read_available_at': ack['durable_ack'],
            'read_receipt_hash': ack['payload_hash'], 'read_root': str(output_root)}
