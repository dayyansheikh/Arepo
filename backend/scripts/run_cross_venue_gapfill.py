"""E009/E010 gap fill (rule gapfill-v1, docs/research_lab/E009_E010_GAPFILL_RULE.md). Run ONCE at
analysis time (after 2026-11-03T08:00Z), on sha-recorded copies of the two source folders:

  python scripts/run_cross_venue_gapfill.py --canonical <copy of cross_venue_live> \
      --copy <copy of arepo_val/.../cross_venue_live> --out <new folder>

Then: run_cross_venue_live.py --root <new folder> --analyze ... / --analyze-e010 ... (primary) and
the same on the canonical folder (sensitivity). Prints MERGE_MANIFEST.json (counts, sha256s only).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import cross_venue_gapfill as gf  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canonical", type=Path, required=True)
    ap.add_argument("--copy", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[1]).stdout.strip()
    print(json.dumps(gf.merge(a.canonical, a.copy, a.out, code_commit=commit), indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
