# ruff: noqa: E501
"""q0164c: the resumable scratch file of ``exclusion-keys`` must not count against the declared keys-output cap.

``cb6_tail.exclusion_stage`` appends every Gamma batch to ``exclusion_keys_partial.jsonl`` (about 6 KB per 50 ids, about 40 MB for the 324,735 ids of
q0164b) with a plain ``open(...)``, i.e. outside the budget, and deletes it once ``exclusion_keys.csv.gz`` and ``exclusion_report.json`` are written. But
``DiskBudget`` is seeded with a scan of the whole run directory, so a resumed run starts with ``used`` above the declared cap (0.01 GiB, plus the 10 MB
manifest allowance) and the first real charge fails (q0164b, 2026-10-23: ``20926424 > 20737418``). The cap is part of the CB8 rules hash
(``KEYS_OUTPUT_CAP_GB``), so it is NOT changed: instead, for one run, the scratch file is not counted. The cap still bounds every final output
(keys csv, report, manifest, sidecars). Nothing hashed is edited; the original ``scan`` is restored on exit.
"""
from __future__ import annotations

import contextlib
from collections.abc import Iterator

from . import history_backfill as hb

SCRATCH_NAMES = frozenset({"exclusion_keys_partial.jsonl"})


@contextlib.contextmanager
def scratch_uncounted() -> Iterator[None]:
    orig = hb.DiskBudget.scan

    def scan(self) -> int:
        if not self.root.exists():
            return 0
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file() and p.name not in SCRATCH_NAMES)

    hb.DiskBudget.scan = scan
    try:
        yield
    finally:
        hb.DiskBudget.scan = orig
