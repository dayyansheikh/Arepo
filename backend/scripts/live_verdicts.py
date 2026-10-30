"""Mechanical verdict from a saved registered-analysis JSON (no new statistics).

  python scripts/live_verdicts.py e009 e009_primary.json
  python scripts/live_verdicts.py e010 e010_primary.json
  python scripts/live_verdicts.py e011 e011.json

The input is the exact stdout of run_cross_venue_live.py --analyze / --analyze-e010 or
run_surprise_snapshot.py analyze. Prints the verdict with the fields used and the input sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_verdicts as lv  # noqa: E402

FN = {"e009": lv.verdict_e009, "e010": lv.verdict_e010, "e011": lv.verdict_e011}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("experiment", choices=sorted(FN))
    ap.add_argument("analysis_json", type=Path)
    a = ap.parse_args(argv)
    raw = a.analysis_json.read_bytes()
    out = FN[a.experiment](json.loads(raw))
    out["input"] = {"path": str(a.analysis_json), "sha256": hashlib.sha256(raw).hexdigest()}
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
