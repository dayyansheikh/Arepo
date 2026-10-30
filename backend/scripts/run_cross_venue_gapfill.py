"""E009/E010 gap fill (rule gapfill-v2, docs/research_lab/E009_E010_GAPFILL_RULE_V2.md). Run ONCE
at analysis time (after 2026-11-03T08:00Z), on sha-recorded copies of the two source folders:

  python scripts/run_cross_venue_gapfill.py --canonical <copy of cross_venue_live> \
      --copy <copy of arepo_val/.../cross_venue_live> --out <new folder>

Records HEAD and refuses a dirty working tree (``--allow-dirty`` only flags it as
``tree_dirty: true`` in the manifest; disclose it with the result). Then:
run_cross_venue_live.py --root <new folder> --analyze ... / --analyze-e010 ... (primary) and the
same on the canonical folder (sensitivity). Prints MERGE_MANIFEST.json (counts, sha256s only).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import cross_venue_gapfill as gf  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]


def git_state(cwd: Path = BACKEND) -> tuple[str, bool]:
    """(HEAD commit, tracked files modified?) of the repository holding this script."""

    def run(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=cwd).stdout

    head = run("rev-parse", "HEAD").strip()
    dirty = bool(run("status", "--porcelain", "--untracked-files=no").strip())
    return head, dirty


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canonical", type=Path, required=True)
    ap.add_argument("--copy", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--allow-dirty", action="store_true")
    a = ap.parse_args(argv)
    head, dirty = git_state()
    if not head:
        print("refused: cannot read git HEAD (run from the repository)", file=sys.stderr)
        return 2
    if dirty and not a.allow_dirty:
        print("refused: the working tree has uncommitted changes to tracked files "
              "(commit them, or pass --allow-dirty and disclose it)", file=sys.stderr)
        return 2
    m = gf.merge(a.canonical, a.copy, a.out, code_commit=head, tree_dirty=dirty)
    print(json.dumps(m, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
