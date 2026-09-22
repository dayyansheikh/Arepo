"""Explicit local development selection only; never collect sources or create origins."""

import argparse
import json
import resource
import sys
import time
import uuid
from pathlib import Path

from .selection import create_selection, read_selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    select = commands.add_parser('select')
    select.add_argument('--frame', required=True, type=Path)
    select.add_argument('--implementation-commit', required=True)
    select.add_argument('--output-parent', required=True, type=Path)
    select.add_argument('--scheduled-per-stratum', type=int, default=1)
    select.add_argument('--max-unique-markets', type=int, default=256)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--journal', required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic_ns()
    if args.command == 'select':
        parent = args.output_parent
        if not parent.is_absolute() or parent.resolve() != parent or not parent.is_dir():
            parser.error('existing canonical output parent required')
        root = parent / ('fs2_selection_' + uuid.uuid4().hex)
        result = create_selection(
            args.frame, implementation_commit=args.implementation_commit, output_root=root,
            scheduled_per_stratum=args.scheduled_per_stratum,
            max_unique_markets=args.max_unique_markets,
        )
    else:
        root = args.journal
        result = read_selection(root)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({
        **{k: v for k, v in result.items() if k != 'plan'},
        'journal_root': str(root), 'strata_count': len(result['plan']['strata']),
        'sampling_plan_hash': result['plan']['plan_hash'],
        'retained_file_bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
        'process_peak_resident_bytes': peak if sys.platform == 'darwin' else peak * 1024,
        'process_elapsed_ns': str(time.monotonic_ns() - started),
    }, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
