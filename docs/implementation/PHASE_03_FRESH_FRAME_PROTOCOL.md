# D077 — refresh the expired prospective population frame

The September 21 frame remains immutable evidence. Its predeclared seven-day limit expired
September 28; it cannot supply a new prospective selection now. A new complete bounded
Gamma enumeration is required before another public screen or pilot. This is a local public
read, not a production scan, database import or admission of predictive information.

Use the existing tested frame CLI and its existing expanded limits without code changes:
4,000 request attempts, limit100 per page, 3GiB raw total, 8GiB retained plus2GiB free reserve,
15-second requests, 900-second acquisition bound, at most one retry per cursor/eight total,
one HTTP/1 connection. Preserve unknown/missing fields and all failed runs. Stop on existing
caps/failures; do not increase limits or silently relaunch to obtain completeness.

Before running, ensure no source/package changes or tests remain active, code is committed,
PR updated, and actual free bytes exceed the unchanged10GiB preflight. Current observation
October2:23,000,612KiB free. The CLI performs its own before/after-proof preflights. Previous
first-page and incomplete100,000-row journals are historical capacity evidence only. The CLI
performs its required original-code capacity read; do not separately repeat that verification.

Freeze one execution of the following command, with exclusive stdout/stderr files. Generated
frame root is recorded by the CLI; preserve it even on failure. All paths are under the
existing repository; never overwrite an existing attempt log.

```sh
PYTHONPATH=backend DATABASE_URL=sqlite+aiosqlite:////tmp/arepo_d077_frame.sqlite \
AUTO_MIGRATE=false EMAIL_PROVIDER=disabled ALERT_EMAIL_ENABLED=false DIGEST_EMAIL_ENABLED=false \
caffeinate -is backend/.venv/bin/python -m astrolabe.research_panel.frame_cli enumerate \
  --output-parent /Users/DayyanSheikh/Projects/astrolabe/data-dumps \
  --first-page-journal /Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_capture_c63c72a0fe194f47824ccc862b0619cd \
  --request-capacity-journal /Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_capture_3a4f80db7fa94d248fc16e1397af4c71 \
  --request-capacity-commit 726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0 \
  --bounded-retries --reuse-connections
```

Record actual implementation commit, output root, return status, request/row counts, errors,
source interval/availability, raw/retained bytes, peak memory, elapsed time and manifest hashes.
Only an exhausted-consistent source interval may support the new draw. A complete interval
is not an atomic universe snapshot. A failed/incomplete attempt is retained and cannot be
used as a representative frame. Freeze any later sampling/measurement protocol separately;
this command does not start screening, origin collection or models.
