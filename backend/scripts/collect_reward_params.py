# ruff: noqa: E501
"""One write-once capture of Polymarket liquidity-reward parameters (keyless; see reward_params_collector).

  python scripts/collect_reward_params.py --out-root ../data-dumps/research_lab/reward_params
Exit 0 on a complete capture, 1 on a failed one (the failed capture is kept as such), 2 on refusal.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import reward_params_collector as rpc  # noqa: E402


def _commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10,
                              cwd=Path(__file__).parent).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--min-interval-s", type=float, default=0.5)
    ap.add_argument("--min-free-gb", type=float, default=2.0, help="refuse when the disk has less free space")
    a = ap.parse_args(argv)
    root = Path(a.out_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < a.min_free_gb * 1e9:
        print("refused: low disk", file=sys.stderr)
        return 2
    man = rpc.capture(root, rpc.httpx_fetch(), max_pages=a.max_pages, min_interval_s=a.min_interval_s,
                      code_commit=_commit())
    print(json.dumps({k: man[k] for k in ("capture_id", "state", "markets_native", "markets_sponsored", "rows_bytes")}))
    return 0 if man["state"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
