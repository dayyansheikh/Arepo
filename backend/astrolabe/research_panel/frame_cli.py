"""Explicit finite local measurement only. No settings, SQL or production scheduling."""

import argparse
import asyncio
import json
import resource
import sys
import time
import uuid
from pathlib import Path

from astrolabe.feature_store.capture import Budget

from .frame import FrameBudget, FrameRetryPolicy, GammaFrameRun, read_frame


def summary(root):
    result = read_frame(root)
    return {**{k: v for k, v in result.items() if k != 'pages'}, 'journal_root': str(root),
            'retained_file_bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            'retained_files': sum(p.is_file() for p in root.rglob('*'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    first = commands.add_parser('first-page')
    first.add_argument('--output-parent', required=True, type=Path)
    bounded = commands.add_parser('enumerate')
    bounded.add_argument('--output-parent', required=True, type=Path)
    bounded.add_argument('--first-page-journal', required=True, type=Path)
    sizes = bounded.add_mutually_exclusive_group()
    sizes.add_argument('--capacity-journal', type=Path)
    sizes.add_argument('--request-capacity-journal', type=Path)
    bounded.add_argument('--request-capacity-commit')
    bounded.add_argument('--bounded-retries', action='store_true')
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--journal', required=True, type=Path)
    original = commands.add_parser('inspect-original')
    original.add_argument('--journal', required=True, type=Path)
    original.add_argument('--implementation-commit', required=True)
    original.add_argument('--output-parent', required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic_ns()
    if args.command == 'inspect-original':
        from .original_reader import read_original_frame

        root = args.output_parent / ('fs2_frame_read_' + uuid.uuid4().hex)
        read = read_original_frame(args.journal, implementation_commit=args.implementation_commit,
                                   output_root=root)
        read['report'] = {k: v for k, v in read['report'].items() if k != 'pages'}
        print(json.dumps(read, sort_keys=True, indent=2))
        return
    if args.command in {'first-page', 'enumerate'}:
        parent = args.output_parent
        if not parent.is_absolute() or parent.resolve() != parent or not parent.is_dir():
            parser.error('existing canonical absolute output directory required')
        root = parent / ('fs2_capture_' + uuid.uuid4().hex)
        # Freeze measurement caps before sending the single first-page request.
        budget = Budget(
            requests=1, bytes_per_response=1048576, total_bytes=1048576,
            seconds_per_request=15, total_seconds=30,
        ) if args.command == 'first-page' else FrameBudget()
        basis = args.first_page_journal if args.command == 'enumerate' else None
        capacity = args.capacity_journal if args.command == 'enumerate' else None
        if capacity is not None:
            budget = FrameBudget(total_bytes=1073741824, retained_bytes=3221225472)
        request_capacity = args.request_capacity_journal if args.command == 'enumerate' else None
        commit = args.request_capacity_commit if args.command == 'enumerate' else None
        if (request_capacity is None) != (commit is None):
            parser.error('request-capacity journal and original full commit must be paired')
        if request_capacity is not None:
            budget = FrameBudget(requests=4000, total_bytes=3221225472,
                                 retained_bytes=8589934592)
        run = GammaFrameRun(root, limit=100, budget=budget, measurement_root=basis,
                            capacity_root=capacity, request_capacity_root=request_capacity,
                            request_capacity_commit=commit,
                            retry_policy=FrameRetryPolicy() if args.command == 'enumerate'
                            and args.bounded_retries else None)
        asyncio.run(run.collect())
    else:
        root = args.journal
    result = summary(root)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result.update(process_peak_resident_bytes=peak if sys.platform == 'darwin' else peak * 1024,
                  process_elapsed_ns=str(time.monotonic_ns() - started))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
