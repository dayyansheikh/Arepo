"""E003 runner: ``fit-s1`` (freeze models on S1) and ``score-s2`` (apply frozen fit to S2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import e003  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["fit-s1", "score-s2"])
    ap.add_argument("--out-dir", type=Path, default=e003.E003_DIR)
    a = ap.parse_args(argv)
    fn = e003.fit_s1 if a.command == "fit-s1" else e003.score_s2
    res = fn(out_dir=a.out_dir)
    if a.command == "fit-s1":
        res = {**res, "in_sample": {"DEVELOPMENT_IN_SAMPLE": res["in_sample"]}}
    print(json.dumps(e003._clean(res), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
