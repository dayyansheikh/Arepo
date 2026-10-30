# ruff: noqa: E501
"""Engine-side disk cache of a stream reader's per-day parse (DESIGN_V1 section 44; operational, no value changes).

The ``gamma_rules`` readers (``rules_text``, ``uma_params``) parse every day file in each tick process. A day file's
parse is a pure function of its bytes and of the reader's code, so it is cached under the engine root, keyed by the
file's size and mtime and the reader's code sha256. Any append, restore or code change is a miss and a fresh parse.
Only days before the current UTC day are written (today's file grows every hour). A failed load is a miss, never an
error. ``cache_dir`` None (tests, censuses) disables the cache. The cache is derived data: deleting it changes nothing.
"""

from __future__ import annotations

import os
import pickle
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


def _name(p: Path, st: os.stat_result, code_sha: str) -> str:
    return f"{p.stem}_{st.st_size}_{st.st_mtime_ns}_{code_sha[:16]}.pkl"


def cached_parse(cache_dir: Path | None, tag: str, p: Path, st: os.stat_result, code_sha: str,
                 parse: Callable[[Path], dict]) -> dict:
    """``parse(p)``, read from or written to ``cache_dir/tag`` for a closed day file."""
    if cache_dir is None:
        return parse(p)
    d = Path(cache_dir) / tag
    f = d / _name(p, st, code_sha)
    if f.exists():
        try:
            with open(f, "rb") as fh:
                out = pickle.load(fh)
            if isinstance(out, dict) and "rows" in out and "polls" in out:
                return out
        except Exception:  # noqa: BLE001 - a torn or stale cache file is a miss
            pass
    out = parse(p)
    if p.stem < datetime.now(UTC).strftime("%Y%m%d"):
        try:
            d.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(f".tmp{os.getpid()}")
            with open(tmp, "wb") as fh:
                pickle.dump(out, fh, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, f)
            for old in d.glob(f"{p.stem}_*.pkl"):  # one entry per day file
                if old.name != f.name:
                    old.unlink(missing_ok=True)
        except OSError:
            pass  # the cache is optional; a full disk or read-only root only costs the parse
    return out
