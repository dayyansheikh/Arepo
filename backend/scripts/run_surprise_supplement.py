"""E011 descriptive supplement (registered secondaries not printed by the frozen analyze). Run
once, right after `run_surprise_snapshot.py analyze`, after 2026-11-11T13:00:00Z. No verdict role.

  python scripts/run_surprise_supplement.py [--root DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import surprise_snapshot as ss  # noqa: E402
from astrolabe.research_lab import surprise_supplement as sup  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ss.ROOT)
    a = ap.parse_args(argv)
    print(json.dumps(sup.supplement(a.root), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
