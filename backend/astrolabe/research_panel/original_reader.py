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
_SELECTION_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.selection import read_selection
report = read_selection(Path(sys.argv[2]))
json.dump(report, sys.stdout, sort_keys=True, separators=(",", ":"))
'''
_QUOTE_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.quote_computation import read_quote_computation
from astrolabe.feature_store.source_run import _pair
root = Path(sys.argv[2])
summary = read_quote_computation(root)
facts, ack = _pair(root, 'quote_facts')
json.dump({'facts': facts, 'summary': summary}, sys.stdout, sort_keys=True, separators=(",", ":"))
'''

_BOOK_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.book_computation import read_book_computation
from astrolabe.feature_store.source_run import _pair
root = Path(sys.argv[2])
summary = read_book_computation(root)
facts, ack = _pair(root, 'book_facts')
json.dump({'facts': facts, 'summary': summary}, sys.stdout, sort_keys=True, separators=(",", ":"))
'''

_WINDOW_COMPUTATION_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.window_computation import read_window_computation
from astrolabe.feature_store.source_run import _pair
root = Path(sys.argv[2])
summary = read_window_computation(root)
facts, ack = _pair(root, 'window_facts')
json.dump({'facts': facts, 'summary': summary}, sys.stdout, sort_keys=True, separators=(",", ":"))
'''

_WINDOW_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.window_journal import read_window
json.dump(read_window(Path(sys.argv[2])), sys.stdout, sort_keys=True, separators=(",", ":"))
'''

_RUNTIME_SCRIPT = '''import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from astrolabe.research_panel.runtime import read_runtime, run_root
from astrolabe.feature_store.source_run import _pair
root = Path(sys.argv[2])
policy, ack = _pair(root, 'runtime_policy')
panel = Path(policy['panel_root'])
if run_root(panel) != root:
    raise ValueError('original runtime root differs')
report = read_runtime(panel)
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
    return _read_original(frame_root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='frame')


def read_original_selection(selection_root, *, implementation_commit, output_root, repository=None):
    """Verify the original selection and exact plan; never redraw or change its clocks."""
    return _read_original(selection_root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='selection')


def read_original_quote_computation(root, *, implementation_commit, output_root, repository=None):
    """Verify original exact quote facts/summary without restamping its computation cutoff."""
    return _read_original(root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='quote_computation')


def read_original_runtime(root, *, implementation_commit, output_root, repository=None):
    """Read a sealed runtime under its original code; never redispatch or refresh clocks."""
    return _read_original(root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='runtime')


def read_original_book_computation(root, *, implementation_commit, output_root, repository=None):
    """Verify exact original snapshot components without changing their computation clocks."""
    return _read_original(root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='book_computation')


def read_original_window(root, *, implementation_commit, output_root, repository=None):
    """Read a sealed original synthetic window without changing source clocks."""
    return _read_original(root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='window')


def read_original_window_computation(root, *, implementation_commit, output_root, repository=None):
    """Preserve original receipt diagnostics without moving source or computation clocks."""
    return _read_original(root, implementation_commit=implementation_commit,
                          output_root=output_root, repository=repository, kind='window_computation')


def _read_original(frame_root, *, implementation_commit, output_root, repository, kind):
    if kind not in {'frame', 'selection', 'quote_computation', 'book_computation',
                    'runtime', 'window', 'window_computation'}:
        raise ValueError('unsupported original journal kind')
    schema = VERSION if kind == 'frame' else 'fs2-original-' + kind.replace('_', '-') + '-read-v1'
    script = {'frame': _SCRIPT, 'selection': _SELECTION_SCRIPT,
              'quote_computation': _QUOTE_SCRIPT, 'book_computation': _BOOK_SCRIPT,
              'runtime': _RUNTIME_SCRIPT, 'window': _WINDOW_SCRIPT,
              'window_computation': _WINDOW_COMPUTATION_SCRIPT}[kind]
    computation = kind in {'quote_computation', 'book_computation', 'window_computation'}
    fact_prefix = {'quote_computation': 'quote', 'book_computation': 'book',
                   'window_computation': 'window'}.get(kind, kind)
    prefix = 'fs2_' + kind + '_read_'
    hash_key = kind + '_report_hash'
    available_key = kind + '_available_at'
    build = verified_panel_build()
    frame_root, output_root = Path(frame_root), Path(output_root)
    repository = Path(repository) if repository else Path(__file__).parents[3]
    for path in (frame_root, output_root, repository):
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError('canonical absolute original-read paths required')
    if (not output_root.name.startswith(prefix)
            or output_root == frame_root or frame_root in output_root.parents):
        raise ValueError('separate fresh ' + prefix + ' output directory required')
    metadata_started = _clock()
    policy, policy_ack = _pair(frame_root, fact_prefix + '_policy')
    # Only sealed original reports are consumed. No crash-repair or semantic reconstruction.
    original_report, report_ack = _pair(frame_root, fact_prefix + '_facts' if computation
                                        else kind + '_report')
    if kind != 'runtime' and original_report['policy_hash'] != policy_ack['payload_hash']:
        raise ValueError('original report/policy lineage differs')
    extra, extra_hashes = {}, {}
    if kind in {'selection', 'quote_computation', 'book_computation', 'window_computation'}:
        source_root = Path(policy['frame_root' if kind == 'selection' else 'source_root'])
        if not source_root.is_absolute() or source_root.resolve() != source_root:
            raise ValueError('canonical original source evidence path required')
        if output_root == source_root or source_root in output_root.parents:
            raise ValueError('separate output outside original source evidence required')
    if kind == 'runtime':
        if policy['schema_version'] != 'fs2-interleaved-synthetic-runtime-v1':
            raise ValueError('unsupported original runtime layout')
        panel = Path(policy['panel_root'])
        declaration, _ = _pair(panel, 'panel_policy')
        suffix = panel.name.removeprefix('fs2_panel_')
        dependencies = [panel, Path(declaration['frame_root']),
                        panel.with_name('fs2_activation_' + suffix),
                        panel.with_name('fs2_selection_panel_' + suffix)]
        for dependency in dependencies:
            if not dependency.is_absolute() or dependency.resolve() != dependency:
                raise ValueError('canonical original runtime dependency required')
            if output_root == dependency or dependency in output_root.parents:
                raise ValueError('separate output outside original runtime dependencies required')
    if kind == 'selection':
        plan, plan_ack = _pair(frame_root, 'selection_plan')
        if original_report['plan_hash'] != plan_ack['payload_hash']:
            raise ValueError('original selection report/plan lineage differs')
        extra, extra_hashes = {'plan': plan}, {'selection_plan_hash': plan_ack['payload_hash']}
    with tempfile.TemporaryDirectory(prefix='arepo_original_decoder_') as tmp:
        code = Path(tmp)
        code_manifest = _extract(repository, implementation_commit, policy['build'], code)
        output_root.mkdir(mode=0o700, exist_ok=False)
        _sync_directory(output_root.parent)
        _persist(output_root, 'read_policy', {
            'schema_version': schema, kind + '_root': str(frame_root),
            kind + '_policy_hash': policy_ack['payload_hash'],
            'metadata_read_started_at': metadata_started,
            hash_key: report_ack['payload_hash'], **extra_hashes,
            'original_build': policy['build'], 'implementation_commit': implementation_commit,
            'extracted_code': code_manifest, 'reader_build': build,
            'reader_script_hash': _digest(script.encode()),
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
                    [sys.executable, '-I', '-B', '-c', script,
                     str(code / 'backend'), str(frame_root)],
                    env=_ENV, cwd=code, stdout=handle, stderr=subprocess.PIPE, timeout=300,
                )
                handle.flush()
                os.fsync(handle.fileno())
            _sync_directory(output_root)
            if child.returncode:
                raise ValueError(
                    'original-build verification refused the ' + kind + ' or environment')
            result_bytes = _read(output)
            result = json.loads(result_bytes)
            if computation:
                facts, summary = result['facts'], result['summary']
                actual_hash, actual_available = summary['computation_hash'], summary[
                    'computation_available_at']
                provenance, state = summary['source_provenance_class'], 'verified_' + kind
            else:
                facts = {k: v for k, v in result.items()
                         if k not in {hash_key, available_key, *extra}}
                actual_hash, actual_available = result[hash_key], result[available_key]
                provenance = result['provenance_class']
                state = 'verified_synthetic_runtime' if kind == 'runtime' else result['state']
            if (actual_hash != report_ack['payload_hash']
                    or actual_available != report_ack['durable_ack']
                    or facts != original_report
                    or any(result.get(k) != v for k, v in extra.items())):
                raise ValueError('original-build read output differs from sealed facts')
            verified_panel_build()
            completed = _clock()
            if not _ordered_clocks(report_ack['durable_ack'], metadata_started,
                                   read_policy_ack['durable_ack'],
                                   started, completed):
                raise ValueError('original read chronology differs')
            _persist(output_root, 'read_receipt', {
                'schema_version': schema, 'read_policy_hash': read_policy_ack['payload_hash'],
                'original_report_hash': report_ack['payload_hash'],
                'output_hash': _digest(result_bytes), 'output_bytes': len(result_bytes),
                'metadata_read_started_at': metadata_started,
                'verification_started_at': started, 'completed_at': completed,
                'original_provenance_class': provenance,
                'original_state': state,
                'observation_clocks_changed': False, 'origin_admitted': False,
            })
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            # Never expose upstream content/environment in an error receipt.
            _persist(output_root, 'read_failure', {
                'schema_version': schema, 'read_policy_hash': read_policy_ack['payload_hash'],
                'started_at': started, 'failed_at': _clock(), 'error_class': type(exc).__name__,
            })
            raise
    receipt, ack = _pair(output_root, 'read_receipt')
    return {'report': result, 'read_receipt': receipt, 'read_available_at': ack['durable_ack'],
            'read_receipt_hash': ack['payload_hash'], 'read_root': str(output_root)}
