# Phase 3 planning milestone — 2026-09-20

Phase 3 remains **in progress**, stacked from accepted Phase 2 `747485c` / draft #15.
Safe milestone `0ff180f`; draft PR https://github.com/dayyansheikh/Arepo/pull/16.
This milestone implements pure sampling/target rules. It does not attest to an actual
population frame, durable origins, collected panel or predictive improvement.

## Implemented

- Versioned stratified scheduled/triggered/control sampling with a predeclared seed, bounded
  counts, source/trigger/group cutoff checks and explicit category/close/price/liquidity/event
  strata. Missing strata remain unknown; categories or long time-to-close cases are not
  silently excluded. Every exclusion and unfilled control slot is retained.
- Exact reduced rational inclusion probabilities, with a finite decimal only when exactly
  representable. Control arm inclusion differs from conditional matching probability;
  both are recorded. No arm-union probability is claimed. A market with multiple roles
  remains one market; downstream origins/evaluation must deduplicate it.
- Order-invariant keyed hash selection. The eventual trusted protocol writer must freeze
  the random seed before selection; this pure function cannot prove preregistration.
  Frame completeness supplied by a caller is only a claim, so the planner explicitly leaves
  population inference ineligible pending actual source-frame verification. Over-budget plans
  refuse rather than truncate controls or silently narrow the population.
- Receipt-time fixed-horizon target selection: first valid two-sided noncrossed quote at/after
  target within tolerance. Preserve actual delay, missing/late/closed/pending states, invalid
  numbers and identities not known at the origin. Earlier unprocessed receipts block final
  selection; unavailable numerical values and future receipts do not enter current results.
  Ties use the declared observation-ID ordering, not a favourable price. These are receipt
  clocks, not proof of venue-update freshness or millisecond ordering.
- Exact midpoint and delay arithmetic independent of ambient Decimal rounding; equivalent
  aware timezones produce canonical UTC. No carried trade-price fallback, flat label for a
  missing quote, sparse-path extrema or execution-profit claim.

## Validation and review

The planning milestone has 19 targeted tests. Full backend **704 passed**, zero skipped,
38.45s in the final review regression, including actual disposable PostgreSQL; one existing
Starlette/httpx warning. Final review made censoring/blocking receipt IDs explicit and
tightened the exclusion-reason vocabulary before that regression.
Full Ruff, canonical checker and whitespace checks passed. Validation uses the same isolated
temporary SQLite/disabled-email/PostgreSQL fixture setup as Phase 2.

Self-review caught future numerical/identity quality leaking into an as-of inventory hash,
ambient Decimal delay rounding and timezone-dependent output. Fixes now gate all unavailable
values, retain only known receipt metadata, use exact contexts and normalize UTC. Reviewed
conditional control weights, role double-counting, exclusions and iterator/request budgets.
No source/network calls or production paths are invoked by these modules.

## Next milestone and acceptance still outstanding

Implement and verify a bounded prospective population-frame adapter. Preserve enumeration
scope, all pages, cursor progression, exact values and genuine termination. Measure metadata
bytes/rows/time before deciding complete-frame collection budgets; never call the first few
responses a universe. Keep the existing complete 30-day production discovery unchanged.
Then build durable protocol/frame/sample/origin/feature-read records, separate leases and
bounded collectors/targets, followed by an actually preregistered local pilot and its timing,
control coverage, missingness and preservation report. Phase 4 remains gated.

Source-frame preparation findings (documentation checked 2026-09-20):

- Existing `clients/gamma.py` and `discovery/bounded_discovery.py` already reconcile market
  and event keyset paths with completion reports, but normalize through v1 clients/settings
  and do not provide v2 raw receipt evidence. Reuse the completion ideas, not their live entry
  points. Current v1 public eligibility is a separate 30-day/20k-liquidity product rule.
- [Gamma keyset documentation](https://docs.polymarket.com/api-reference/markets/list-markets-keyset-pagination)
  specifies `after_cursor`, response `next_cursor`, maximum page size 100 and rejects offset.
  It exposes date/liquidity filters and `include_tag`; runtime effect and complete termination
  still require v2 evidence. The current parameter list does not show `active`; do not silently
  assume the old client's filter is supported. Use explicit returned-state eligibility and
  preserve the request/coverage contract. Do not inherit the 30-day cutoff as a research claim.
- [CLOB simplified markets](https://docs.polymarket.com/api-reference/markets/get-simplified-markets)
  is a possible smaller frame with condition/tokens/status and a cursor, but this task has not
  verified runtime completeness, endpoint termination or category/liquidity coverage. It is
  not automatically interchangeable with Gamma or its similarly named sampling endpoint.

These are read-only documentation findings, not newly admitted source implementations or a
decision to bulk-collect. Next follow [the frame adapter contract](PHASE_03_FRAME_CONTRACT.md):
pin and test cursor/scope/completeness semantics, then bounded first-page measurement before
setting a complete-frame collection budget. No live panel has been run.

## Gamma frame adapter milestone — 2026-09-21

Implemented `research_panel/frame.py`, `build_identity.py`, `frame_cli.py` and 28 fault/
contract tests, plus isolated keyset source parameters and captured-parent verification.
The original Phase 2 `SourceRun` policy and all production entry points remain untouched.
A durable policy precedes every request; both code packages and source contracts are pinned.
Raw numerical JSON, generic parsed values, every duplicate row and native identity survive.
Schema/HTTP/truncation/cursor/budget/clock failures cannot become successful enumeration.
Torn page/report files remain ineligible and are not repaired on read or retry. A complete
local copy gives identical evidence; that does not waive the full archive-equivalence gate.

Full backend: **732 passed**, zero skipped, 39.85s with disposable PostgreSQL, one existing
Starlette/httpx warning. Targeted frame/capture/source-run tests: **62 passed** in 7.72s.
Full Ruff, canonical contract and whitespace checks passed. No database outside test
fixtures was accessed. Reviewed scope drift, page order/parentage, missing terminal signals,
unknown identities, condition/token conflicts, retained unknown strata, future clocks,
changed loaded code and accidental replay promotion. All population inference flags remain
false pending subsequent integration/acceptance. No new model or edge finding is claimed.

Next: commit this tested implementation, then execute only the frozen one-page CLI. Inspect
actual receipt/size/latency/schema evidence before designing a larger frame budget. The phase
remains incomplete until durable sampling/origins/feature reads, collectors/targets and the
actual prospective pilot satisfy the existing acceptance criteria.

### First-page evidence and bounded enumeration refinement

Live measurement from `bf734a0` succeeded: 100 markets / 557,140 raw bytes / 1,501,764
retained bytes / 157,199,875 ns source request-to-receipt time. The cursor continued, so the
run is correctly **incomplete**. Full evidence references and original journal are recorded
in `PHASE_03_FIRST_PAGE_EVIDENCE.json`. No old diagnostic was relabelled or reused as origins.

The v2 frame format streams page verification and references full page projections from its
final manifest. Separate FrameBudget ceilings and cost-evidence preflight are now implemented;
old diagnostic maxima remain unchanged. Free-space and retained-byte stops preserve prior
files. Synthetic cost evidence cannot authorize a real collection. First-page results estimate
neither total population nor worst-case page volume. Larger-run caps are frozen in the frame
contract before collection. Self-review includes memory growth and conservative file-space
reservation; actual CLI resident-memory and elapsed-time metrics will be reported.

Full backend **740 passed**, zero skipped, 40.32s, including disposable PostgreSQL; 36 frame
tests. Full Ruff and canonical checker passed. One launch initially resolved the virtualenv
interpreter symlink to global Python (pytest unavailable); correcting the launch path produced
the complete successful regression. This was a test-launch error, not a skipped code failure.
