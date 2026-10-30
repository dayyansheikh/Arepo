"""Opt-in task-local byte guards for append-only source journals; never prune evidence."""

import shutil
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_ACTIVE = ContextVar('arepo_source_retained_quota', default=None)
MIB = 1048576


class SourceQuotaExceeded(ValueError):
    """A refused write; all earlier bytes remain preserved."""


def quota_policy(retained_bytes):
    if type(retained_bytes) is not int or not MIB <= retained_bytes <= 256 * MIB:
        raise ValueError('source retained quota must be an integer in 1..256 MiB')
    return {'schema_version': 'fs2-source-retained-quota-v1', 'retained_bytes': retained_bytes,
            'failure_reserve_bytes': 65536, 'free_reserve_bytes': 2048 * MIB,
            'max_files': 128, 'max_depth': 3}


def _usage(root, policy):
    root = Path(root)
    if not root.is_absolute() or root.resolve() != root:
        raise ValueError('canonical source quota root required')
    if not root.exists():
        return 0, 0
    stack, files, total, directories = [(root, 0)], 0, 0, 0
    while stack:
        folder, depth = stack.pop()
        for path in folder.iterdir():
            if path.is_symlink():
                raise SourceQuotaExceeded('symlink in guarded source journal')
            if path.is_dir():
                directories += 1
                if depth + 1 >= policy['max_depth'] or directories > 32:
                    raise SourceQuotaExceeded('source quota directory bound exceeded')
                stack.append((path, depth + 1))
            elif path.is_file():
                files += 1
                total += path.stat().st_size
                if files > policy['max_files'] or total > policy['retained_bytes']:
                    raise SourceQuotaExceeded('source retained-byte/file quota exceeded')
            else:
                raise SourceQuotaExceeded('nonregular entry in guarded source journal')
    return total, files


def retention_scope(root, policy, *, failure=False):
    # Keep the actual generator code directly inspectable by the existing build guard.
    return contextmanager(_retention_scope)(root, policy, failure=failure)


def retained_size(root, policy):
    return _usage(root, policy)[0]


def _retention_scope(root, policy, *, failure):
    if policy is None:
        yield
        return
    if _ACTIVE.get() is not None:
        raise ValueError('nested source quota scope is unsupported')
    root = Path(root)
    if policy != quota_policy(policy['retained_bytes']):
        raise ValueError('source quota policy differs')
    retained_size(root, policy)
    token = _ACTIVE.set((root, policy, failure))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def guard_write(path, content):
    active = _ACTIVE.get()
    if active is None:
        return
    root, policy, failure = active
    path = Path(path)
    if path.resolve() != path or root not in path.parents:
        raise SourceQuotaExceeded('write outside canonical guarded source journal')
    if len(path.relative_to(root).parts) > policy['max_depth']:
        raise SourceQuotaExceeded('source write exceeds directory depth')
    total, files = _usage(root, policy)
    if files + 1 > policy['max_files'] - (0 if failure else 2):
        raise SourceQuotaExceeded('source file count would exceed reserved bound')
    limit = policy['retained_bytes'] - (0 if failure else policy['failure_reserve_bytes'])
    if total + len(content) > limit:
        raise SourceQuotaExceeded('source retained-byte quota would be exceeded')
    if failure and len(content) > policy['failure_reserve_bytes'] // 2:
        raise SourceQuotaExceeded('failure evidence exceeds reserved artefact bound')
    if shutil.disk_usage(root).free < policy['free_reserve_bytes'] + len(content):
        raise SourceQuotaExceeded('source free-space reserve reached')


def reserve_response(raw_bytes):
    """Refuse before HTTP unless raw response and receipt/ack have reserved capacity."""
    active = _ACTIVE.get()
    if active is None:
        return
    root, policy, _ = active
    if type(raw_bytes) is not int or not 0 <= raw_bytes <= MIB:
        raise ValueError('bounded raw response reservation required')
    total, files = _usage(root, policy)
    addition = raw_bytes + 65536  # bounded receipt/request metadata and raw acknowledgement
    if (total + addition > policy['retained_bytes'] - policy['failure_reserve_bytes']
            or files + 3 > policy['max_files'] - 2):
        raise SourceQuotaExceeded('insufficient reserved raw response capacity before request')
    if shutil.disk_usage(root).free < policy['free_reserve_bytes'] + addition:
        raise SourceQuotaExceeded('source free-space reserve reached before request')
