"""Evaluate one retained D116 run from its artifacts and write the report JSON.

Reads only the retained panel / selection / screening-worker / activation / runtime roots. Makes
no network request, writes only the report path given, and never touches the roots.

    python scripts/evaluate_d116.py <panel_root> --out <report.json>
"""

import argparse
import json
import sys
from pathlib import Path

from astrolabe.research_panel.d116_evaluator import evaluate_d116


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("panel_root", type=Path, help="fs2_panel_* root of the D116 run")
    parser.add_argument("--out", type=Path, required=True, help="report JSON path (must not exist)")
    for name in ("selection", "worker", "runtime", "activation"):
        parser.add_argument(f"--{name}-root", type=Path, default=None,
                            help=f"override the derived {name} root")
    parser.add_argument("--no-protocol-check", action="store_true",
                        help="skip the frozen D116 protocol-value comparison (test fixtures only)")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"refusing to overwrite {args.out}")
    kwargs = {"activation_root": args.activation_root}
    if args.no_protocol_check:
        kwargs["protocol_expectation"] = None
    report = evaluate_d116(args.panel_root, args.selection_root, args.worker_root,
                           args.runtime_root, **kwargs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"outcome": report["outcome"], "reasons": report["outcome_reasons"],
                      "report": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
