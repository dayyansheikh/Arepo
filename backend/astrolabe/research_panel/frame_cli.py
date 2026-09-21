"""Explicit finite local measurement only. No settings, SQL or production scheduling."""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from astrolabe.feature_store.capture import Budget

from .frame import GammaFrameRun, read_frame


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
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--journal', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'first-page':
        parent = args.output_parent
        if not parent.is_absolute() or parent.resolve() != parent or not parent.is_dir():
            parser.error('existing canonical absolute output directory required')
        root = parent / ('fs2_capture_' + uuid.uuid4().hex)
        # Freeze measurement caps before sending the single first-page request.
        run = GammaFrameRun(root, limit=100, budget=Budget(
            requests=1, bytes_per_response=1048576, total_bytes=1048576,
            seconds_per_request=15, total_seconds=30,
        ))
        asyncio.run(run.collect())
    else:
        root = args.journal
    print(json.dumps(summary(root), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
