# D088 — lifecycle-fresh complete frame before a new bounded pilot

D085 retained four closed/non-accepting markets selected from the October3 frame. Their
failed observations and denominators remain unchanged. Refresh the complete frame before
any new draw; do not filter or redraw D085. The eligibility definition remains the existing
active=true, closed=false, resolvable mapping rule over the complete Gamma keyset inventory.
Unknown/excluded states and raw rows remain preserved. No date/category/liquidity/top-N cut.

Prerequisite: D087 committed verifier optimization passes76 scoped tests and its fresh
8-member synthetic runtime/history/target/original-recovery measurement succeeds under the
unchanged clocks. Record that result before committing/executing this protocol. Public reads
are local/nonproduction; this is not a production scheduler or scan restart.

Execute the existing finite CLI once:4000 attempts,100 rows/page,3GiB raw,8GiB retained,
2GiB free reserve,15s request/900s acquisition limits, one retry per cursor/eight total,
one reused HTTP/1 connection. Original-code capacity checks remain mandatory. Stop on any
quota/error/incomplete interval. Never silently retry the whole attempt or delete evidence.
Before launch require no active test/collector, committed clean source, current draft PR,
and at least10GiB free. Wrapper launch/stdout/stderr/result paths must all be new.

```sh
PYTHONPATH=backend DATABASE_URL=sqlite+aiosqlite:////tmp/arepo_d088_frame.sqlite \
AUTO_MIGRATE=false EMAIL_PROVIDER=disabled ALERT_EMAIL_ENABLED=false DIGEST_EMAIL_ENABLED=false \
caffeinate -is backend/.venv/bin/python -m astrolabe.research_panel.frame_cli enumerate \
  --output-parent /Users/DayyanSheikh/Projects/astrolabe/data-dumps \
  --first-page-journal /Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_capture_c63c72a0fe194f47824ccc862b0619cd \
  --request-capacity-journal /Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_capture_3a4f80db7fa94d248fc16e1397af4c71 \
  --request-capacity-commit 726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0 \
  --bounded-retries --reuse-connections
```

Use exclusive wrapper prefix `data-dumps/fs2_frame_refresh_20261005_1`. Record actual
implementation HEAD, wall/monotonic start/end, command, exit status, raw/retained bytes,
source interval, request/row/error totals and manifest hashes. Retain partial evidence on
failure. Only exhausted_consistent can feed a new draw; even that is an interval, not an
atomic market universe. A separate committed pilot protocol must precede selection/requests.
For that future attempt use a maximum1-hour frame age, justified by measured lifecycle drift;
this prospective restriction does not reinterpret the prior seven-day protocol or old draws.
Phase3 remains incomplete; no model training, Phase4, production change or predictive claim.

Prerequisite fulfilled: D087 implementation5678b10 passed76 tests and the new8-member
synthetic measurement;8 observed/fresh origins and8 observed targets, full original audit.
Evidence: PHASE_03_VERIFIER_CACHE_TIMING_EVIDENCE.json. Preflight free17,706,476KiB; recheck
at launch. Raw source files must remain unchanged throughout acquisition/recovery.
