"""Evaluate one retained D116 run from its artifacts and write the report JSON.

Reads only the retained panel / selection / screening-worker / activation / runtime roots. Makes
no network request, writes only the report path given, and never touches the roots.

    python scripts/evaluate_d116.py <panel_root> --launch-commit <40-hex> --out <report.json>

The report is authoritative only when every run-identity check (gate E0) passes. The root
overrides and --no-protocol-check are test aids: using one forces FAIL (test_override_used).
A missing report is a FAIL (protocol section 4.4).
"""

import argparse
import json
import os
import sys
from pathlib import Path

from astrolabe.research_panel.d116_evaluator import evaluate_d116


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("panel_root", type=Path, help="fs2_panel_d116_integrated_1 root")
    parser.add_argument("--out", type=Path, required=True, help="report JSON path (must not exist)")
    parser.add_argument(
        "--launch-commit",
        required=True,
        help="40-hex commit the run was launched from; must equal every artifact's commit",
    )
    for name in ("selection", "worker", "runtime", "activation"):
        parser.add_argument(
            f"--{name}-root",
            type=Path,
            default=None,
            help=f"TEST AID: override the derived {name} root (forces FAIL)",
        )
    parser.add_argument(
        "--no-protocol-check",
        action="store_true",
        help="TEST AID: skip the frozen-value comparison (forces FAIL)",
    )
    args = parser.parse_args(argv)
    raw_root = args.panel_root.absolute()
    try:
        resolved = raw_root.resolve(strict=True)
    except OSError as exc:
        parser.error(f"panel root unreadable: {exc}")
    # Refuse symlinked roots: the evaluator needs canonical absolute paths (selection.py:88-92).
    if Path(os.path.normpath(raw_root)) != resolved:
        parser.error(f"panel root {raw_root} is or traverses a symlink (resolves to {resolved})")
    args.panel_root = resolved
    if args.out.exists():
        parser.error(f"refusing to overwrite {args.out}")
    report = evaluate_d116(
        args.panel_root,
        args.selection_root,
        args.worker_root,
        args.runtime_root,
        activation_root=args.activation_root,
        launch_commit=args.launch_commit,
        protocol_check=not args.no_protocol_check,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n")
    print(
        json.dumps(
            {
                "outcome": report["outcome"],
                "authoritative": report["authoritative"],
                "reasons": report["outcome_reasons"],
                "report": str(args.out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
