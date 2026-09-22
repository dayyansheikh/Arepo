# Phase 3 planning milestone — 2026-09-20

Phase 3 remains **incomplete**, stacked from accepted Phase 2 `747485c` / draft #15.
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

### First enumeration result and separately gated second attempt

Attempt 1 stopped at its frozen byte limit. 40,900 complete rows and the truncated page were
retained; 44 identity exclusions remain explicit. No completion/population claim. Observed
memory and disk costs support one separately declared larger attempt within local capacity.
The new preflight requires both first-page evidence and verified prior raw-ceiling receipts;
it cannot silently increase a live run's limit or use a synthetic attempt for live admission.
Original runs remain unchanged/incomplete. See D033 and the frame contract. 39 targeted frame
tests pass, including capacity-proof requirements and original-run immutability.

### Final review of this continuation — 2026-09-21

Second attempt retained 100,000 distinct source rows across 1,000 pages, then stopped incomplete
at its request cap. 99,956 eligible row identities, 44 unresolved, no observed duplicates or
mapping conflicts. See `PHASE_03_ENUMERATION_ATTEMPT_2.json`. Actual raw 644,897,535 bytes,
retained 1,577,956,669 bytes, peak resident 343,457,792 bytes; original journal fully verified.
No complete frame, sample, origin, prospective panel or predictive finding is claimed.
Both failed-to-exhaust runs remain evidence, not discarded/relabelled successes.

Final full backend **743 passed**, zero skipped, 41.64s, including disposable PostgreSQL 17.11;
39 frame tests; Ruff/canonical/whitespace checks passed. Existing Starlette/httpx warning only.
Self-review covered all new frame/capacity code, numerical preservation, request/parent scope,
source and panel build pinning, stopping ceilings, no synthetic promotion, original-attempt
immutability, memory growth, future/absent clocks and all protected production boundaries.

Outstanding: complete frame beyond current100,000-member boundary, original-build read boundary,
durable protocol/seed/sample/feature-read/origin records, leases, family coverage, collectors,
due targets and actual pilot. The new panel-journal contract defines that next milestone without
pretending it exists. Phase 3 stays in progress and Phase 4 stays gated. No production code,
configuration, scheduling, migrations, credentials, retention, data deletion or trades changed.

### Original-build read boundary — 2026-09-21

D034 is implemented and self-reviewed. Ten new tests exercise original code extraction,
unchanged source journals and repository state, immutable commit requirements, corrupted
raw bytes, changed source/library builds, output path isolation and repeat-read behavior.
Full backend **753 passed**, zero skipped, 71.62s, including isolated PostgreSQL. Ruff,
canonical contract and whitespace checks pass; existing Starlette/httpx warning only.
The reader produces a new actual read receipt, never a retrospective origin or upgraded
frame completeness. The original decoder still verifies all original dependencies. No
source requests, application startup, databases or dependency installation in this path.
Next verify an actual preserved journal after committing this implementation, then reconcile
finite sampling capacity beyond 100,000 rows before any new source enumeration.

### Original evidence read and finite sampler capacity

The new reader at `2eb7ec4` verified the actual 100,000-row attempt through original commit
`726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0`, preserving its original report hash and incomplete
state. See `PHASE_03_ORIGINAL_READ_EVIDENCE.json`; read journal
`data-dumps/fs2_frame_read_2f0ba791e3974a369a8f5e551fe5f73c`. This was a local read only.

D035 streams the canonical frame digest and uses bounded heap selection. The default output
was compared in full against original `2eb7ec4` code; a frozen golden plan hash and Unicode/
exact-value hash tests preserve that regression. Explicit expanded capacity is versioned and
hashed; over-budget frames still fail instead of truncating. Original default is 100,000.
The deterministic 400,000-row synthetic capacity fixture passed its predeclared 1 GiB /180s
gates at **322,699,264 resident bytes and 29,322,234,667ns**. This single-stratum fixture does
not bound arbitrary string lengths, huge stratum counts, raw Gamma identity verification or
all end-to-end ingestion costs. It supports further finite design, not source completeness.
Full backend **755 passed**, zero skipped, 72.43s, isolated PostgreSQL included; 21 planning
tests passed again after adding the frozen golden assertion. Ruff/canonical/whitespace checks
passed. Existing Starlette/httpx warning only. No collection caps were increased in this
milestone and no new network collection occurred. See the next capacity-refinement contract.

Committed-code capacity confirmation at `84cf4b132bfb9cca4772b0cce0a5a694c7e8ce57`: 400,000 synthetic members,
320,897,024 resident bytes, 27,764,313,417ns; both original gates pass and the plan hash
matches the earlier run. Exact build/script hash and results are preserved in
`PHASE_03_SAMPLING_CAPACITY_EVIDENCE.json`. No tests ran concurrently with this confirmation.
At 87% primary usage, coherent progress is checkpointed for the single 18:13 London heartbeat;
weekly allowance remains available (45% used). No access/data gate has been waived.

### D036 request-ceiling capacity gate

Implemented explicit larger finite bounds only after newly verified original-code evidence
of the prior 1,000-request stop. Original diagnostic/default and byte-cap modes remain intact.
Eleven capacity tests cover actual old-code verification, retained original facts, synthetic/
live separation, complete-versus-incomplete status, corrupted raw bytes, missing code, each
expanded bound and unused proof arguments. Full regression **766 passed**, zero skipped,
91.45s with isolated PostgreSQL; Ruff/canonical/whitespace checks pass. Existing warning only.
Self-review checked source/scope equivalence, fresh receipt clocks, declared budgets, no
hidden retries/extensions, disk reserve before/after verification and unchanged production
boundaries. Safe protocol/code commit precedes the single finite third attempt.

### Third enumeration outcome — data blocker preserved

The committed D036 attempt successfully verified original request-ceiling evidence, then
stopped incomplete on a 15s timeout during response 74. It retained 7,300 complete source
rows plus the failed response; all facts, clocks, partial bytes and acknowledgements remain.
See `PHASE_03_ENUMERATION_ATTEMPT_3.json`. Peak memory 118,849,536 bytes, retained bytes
112,224,334; collection did not reach the larger capacity ceilings. No source terminal,
complete population, model-ready origin or pilot acceptance was observed. A timeout is not
proof of persistent outage. Existing prefixes and synthetic sizing cannot replace missing
complete-frame evidence. Follow the user data-unavailability stop condition; no silent retry.
Final code validation remains **766 passed**, zero skipped, 91.45s with local PostgreSQL;
no further source/module changes since that regression. The final evidence/docs-only update
uses canonical/whitespace checks. D036 engineering milestone is committed; Phase 3 is blocked
on required complete-frame data and remains incomplete. Draft #16 stays open/unmerged.

### D037 bounded retry implementation

After the user requested continued engineering, the preserved failed body was inspected:
first bytes arrived about 0.63s after request start, followed by a mid-JSON stall. Manifest v3
now supports an explicitly frozen opt-in retry with exact failed-attempt/cursor linkage.
Failures remain raw immutable records and historical report errors; only validated recovery
removes an outstanding gap. Source scope, global ceilings and no-retry defaults stay intact.
Self-review covered request/byte/time accounting, first-page versus later-cursor parents,
backoff clocks, denied/rate-limited/schema errors, maximum one retry per cursor and eight total,
retry evidence tampering, unchanged v2 original-code readers and no retrospective relabelling.

Eighteen new retry tests pass. Full backend **784 passed**, zero skipped, 106.17s, including
isolated PostgreSQL; Ruff/canonical/whitespace checks pass, existing Starlette/httpx warning
only. Focused earlier frame/capacity/original-reader/retry suite passed 75 tests before the
three additional global-budget/backoff checks. No claim that retries improve latency or
prove a complete frame. Commit this exact code/protocol before the fourth finite attempt.

### Fourth enumeration outcome — retry exhaustion

The D037 retry-enabled attempt retained 20,000 source rows across 204 verified attempts.
Three transient retries were used; two recovered and the final unrecovered errors were
`ConnectError` and `TimeoutError`. Raw bytes were 132,580,143, retained files 318,668,335,
peak resident memory 141,836,288 bytes. No source terminal, population inference, model-ready
origin or pilot acceptance was observed. Exact report hashes and costs are preserved in
`PHASE_03_ENUMERATION_ATTEMPT_4.json`. This evidence does not justify another automatic run.

### D038 connection reuse — reviewed before fifth attempt

Renewed continuation identified fresh HTTP client creation for every page. The opt-in v4
frame policy binds a single client, finite one-connection pool and stateless cookie handling.
The source query, identity/parser, limits, error allowlist, retry counts and causal clocks are
unchanged. Default callers still open per-request clients; supplied transports stay synthetic.
No production/source admission gate changed. Old frames keep their original decoder/build.

Real loopback HTTP tests establish one connection for two pages and correct reconnection
after a server close. Fault checks cover partial-response retry, cancellation, hard deadline,
storage-fsync failure, cleanup, scope misuse and manifest-policy mismatch. The initial
contextlib-decorated methods failed the loaded-code guard; context-manager factories preserve
direct code verification without weakening that guard. A damaged-session test caught error
ordering, corrected before regression. Private exception text remains excluded from receipts.

Full isolated backend **794 passed**, zero skipped, 69.08s, including disposable PostgreSQL.
After a whitespace wrap and one added storage-failure test, **94 focused tests passed** in
19.76s, including all 11 connection cases. Ruff, canonical and whitespace checks pass. Existing
Starlette/httpx warning only. No current live-source performance claim follows from these
tests. D038 permits one new finite measurement after this reviewed code/protocol is committed;
the four earlier attempts remain incomplete and no phase gate has passed.

### Fifth outcome — complete interval enumeration verified

Under committed D038 `41fcb01`, 1,755 pages reached the terminal page and passed final integrity,
clock, cursor and identity verification: **175,427 distinct markets**, 175,383 eligible mappings
and 44 explicit unresolved identities. No errors, retries, duplicates or conflicting identities.
Raw 1,115,618,904 bytes; retained 2,728,778,097; peak resident 478,052,352. Whole command
514,493,751,417ns; source interval 23:30:55–23:36:47 UTC, sealed 23:37:32 UTC September 21.
No regression tests ran concurrently; lightweight read-only progress checks were made.
Exact facts/hashes: PHASE_03_ENUMERATION_ATTEMPT_5.json and its original local journal.

This clears the complete-frame prerequisite, not Phase 3 acceptance or population inference.
One uncontrolled successful run cannot attribute success causally to connection reuse.
No prior failed run was changed and no raw evidence was removed. Next is durable selection
with actual read/computation clocks and an explicit freshness rule, followed by the pilot.

### D039 pure metadata prerequisite

The reviewed projector reads only the explicit category, aware endDate, liquidity and first
source-ordered outcomePrices value. Exact numerical text/trailing zeros survive; float,
malformed array, wrong mapping length and naive-date cases remain invalid. Missing values
do not fall back to related fields, become zero or exclude eligible markets. Source event IDs
do not become economic groups. No raw row is changed and no availability/origin is asserted.
Full isolated backend **818 passed**, zero skipped, 74.04s, including PostgreSQL and 23 new
projection cases. Ruff/canonical/whitespace pass; existing Starlette/httpx warning only.
Self-review checked bounded inputs, unsupported type handling, source-order selection,
preserved provenance boundaries and no caller payload admission. Durable integration remains.

### D040 durable development selection before capacity measurement

Reviewed seed/policy fsync before original frame reads, original-code verification, exact
raw/page/row linkage on the actual projection read, per-page computation acknowledgements,
full unknown/unmapped inventory and deterministic sampling replay. Identical versions are
deduplicated only for sampling; conflicts stop. Exact rational weights and all failed outputs
are retained. Source categories cannot collide with the missing-category sentinel. No source
request, SQL/startup import, caller seed/clock/provenance, origin or control admission exists.

Review added checks for original policy/page closure after selection and failed child-read
markers. Construction state is released before independent verification to avoid retaining
two full populations in memory. Frozen processing/output/row limits and disk reserve fail
without reseeding, truncating or silently repairing a run. Read-only replay has its own same
processing limit and does not reinterpret low current free space as historical invalidity.

Twenty-three focused cases pass, including real isolated original-code child decoders,
tampering/rehashed false weights, clock order, missing/extra pages, no overwrite, cold copy,
unknown/unmapped rows, budget refusal and immutable source bytes. Full backend **841 passed**,
zero skipped, 94.97s, disposable PostgreSQL included. Ruff/canonical/whitespace pass; existing
Starlette/httpx warning only. Commit this exact protocol/code before the local full-frame
measurement. A synthetic fixture pass does not establish real capacity or Phase 3 acceptance.

Actual local D040 run under `018dbd3` passed independent full inventory and plan replay:
175,427 rows, 175,383 eligible members, 107 scheduled draws/strata, 44 unresolved identities.
It retained 566,741,238 bytes, used 294,977,536 peak resident bytes and took 146,486,870,416ns
including original-code verification and final replay. All bounds passed. No tests ran
concurrently; lightweight status reads occurred. The explicit category field is missing on
every mapped row; other missingness is preserved in PHASE_03_SELECTION_ATTEMPT_1.json.
This validates development plumbing/capacity, not fresh population inference or pilot acceptance.

### D041 original-selection reader before actual evidence read

The shared original-code reader now has two fixed decoder choices, preserving the existing
frame schema/fields and adding a separate selection-read schema. It pins both original report
and plan, checks Git file sets/hashes, and runs the original full-closure reader in an isolated
child. Entire report/plan equality is required, with old clocks/seed/provenance unchanged.
Review added protection against output inside the selection's transitive source frame and
noncanonical source paths, so recording the new read cannot modify either evidence journal.
The 300-second child timeout, 16 MiB output limit and sanitized environment remain in force.

Ten new selection-reader tests cover original status/clocks/weights, corruption, wrong code,
mutable revisions and both evidence-path boundaries. Full isolated backend **851 passed**,
zero skipped, 105.20s, PostgreSQL included; Ruff/canonical/whitespace pass. Existing warning
only. Commit before the actual D040 original-code read; no redraw or source collection needed.

Actual read under committed D041 `d24ed88` passed on 2026-09-22 at 04:56:02 UTC,
with original D040 `018dbd3` decoding the complete saved journal. Original report and
plan equality passed: 175,427 rows, 175,383 members, 107 selected markets; old clocks,
seed, weights and reconstructed status unchanged. The isolated child emitted 107,797
bytes within its limit; CLI exited 0. New read policy/receipt and exact hashes are in
PHASE_03_ORIGINAL_SELECTION_READ_EVIDENCE.json. No source requests or origins occurred.
No process remains active. Phase 3 acceptance remains open; this is development evidence.

### D042 assessment-aware controls

Added an opt-in v3 sampling plan that distinguishes measured negatives, triggered,
unavailable, stale and absent assessments. Only fresh explicit negatives enter controls;
unknowns stay in the scheduled population and full inventory. Review confirmed that
declaration/window/availability bounds are inclusive, future facts refuse the plan, all
assessments match the frozen policy and market/token, and duplicate evidence cannot
represent multiple decisions. Legacy trigger fields must be neutral in this mode.
Exact arm/matching denominators use the actual admitted pools; shortages remain explicit.
The pure helper cannot authenticate caller evidence, and its output requires runtime
verification and explicitly admits no origin. No production or source collection changes.

54 focused tests passed, including the original golden v1 hash. Full isolated backend:
**884 passed**, zero skipped, 118.98s, disposable PostgreSQL included; full Ruff,
canonical contract and whitespace checks pass. One existing Starlette/httpx warning.
No empirical trigger quality, live coverage or pilot acceptance is implied by these fixtures.

### D043 actual input-read journal

Reviewed the source policy/build boundary, full current-build SourceRun validation, exact
retained rows/admission hashes, failed-response preservation, separate exclusive output,
UTC and same-session monotonic ordering, final independent source closure replay, bounded
storage/time and failure retention. Added monotonic source-ack-to-read checks during review;
UTC alone was insufficient. A source append invalidates this completed-run v1 read, and old
diagnostics cannot be admitted. Reads have no clock/payload/provenance/subset injection API.
Synthetic source status stays synthetic, and no origin or feature is admitted.

The first fixture used an already-consumed HTTP body; corrected it to the existing streamed
mock transport without changing production capture logic. 31 focused read/source tests pass.
Full isolated backend **904 passed**, zero skipped, 119.73s; disposable PostgreSQL included.
Full Ruff, canonical and whitespace checks pass; existing Starlette/httpx warning only.
All 20 new cases use synthetic temporary journals; no new live collection occurred.

### D044 exact quote/identity projection

Reviewed strict token/condition matching, identity availability before quote receipt,
conflicting-version refusal, source-order outcome identity, exact positive-size best levels,
duplicate/one-sided/crossed exclusions, receipt/identity freshness boundaries and retained
failed-source inventory. Mixed provenance is refused; no Gamma/trade price fallback or
native-time/flow/economic claim exists. Results explicitly require verified sources and
durable computation; this pure helper creates no clocks, feature-store record or origin.

The streamed SourceRun → D043 integration test exposed canonical `$utc` wrappers, which the
projector now reads explicitly without accepting naive timestamps. Twenty-six new cases
pass; 46 focused quote/input-read tests pass. Full isolated backend **930 passed**, zero
skipped, 116.97s, disposable PostgreSQL included. Full Ruff, canonical and whitespace checks
pass; one existing Starlette/httpx warning. No live collection or production changes.
The next bounded writer's ordered contract is PHASE_03_QUOTE_COMPUTATION_CONTRACT.md.

### D045 durable quote computation

Reviewed policy-before-read and read-before-compute ordering in UTC and comparable
monotonic clocks; exact input hash/ack lineage; original-cutoff replay; separate canonical
paths, concurrent exclusive output, failed/torn writes and recursive child budget accounting.
Every source remains inventoried, source provenance unchanged, no SQL or origin admission.
Whole-parent preflight precedes output creation. The 180-second checks are operation-boundary
checks, not hard process cancellation. Readers preserve evidence and refuse changed source
closure or build. Synthetic tests establish software behavior, not live panel acceptance.

22 new tests; 68 focused tests passed. Full isolated backend **952 passed**, zero skipped,
139.29s, including disposable PostgreSQL. Full Ruff, canonical and whitespace checks pass.
One existing Starlette/httpx warning. No live collection or production changes.

### D046 targeted identity refresh

Reviewed fixed host/path, canonical bounded IDs, request replay, exact response binding,
raw failure retention, nullable lifecycle and unchanged default-policy/source contracts.
Targeted source registry still pins rights and native-clock limitations. No mutable
caller-defined source list, diagnostic SQL importer expansion, broad-frame filtering or
old-build bypass. Quotes use identities known by receipt and abstain for closed, archived,
inactive, not-accepting or unknown lifecycle. Lifecycle does not change economic identity.

34 new cases; 71 focused tests passed. Initial test failures were an incorrect test-only
assumption that read_source_run returned a dictionary rather than its existing list API;
corrected the tests without changing that API. Full isolated backend **986 passed**, zero
skipped, 142.87s, including disposable PostgreSQL. Full Ruff/canonical/whitespace checks
passed; one existing Starlette/httpx warning. Two-request runtime measurement is separately
frozen before collection, with fixed historical target, no retries and no origin claim.

D046 runtime measurement executed once from committed `761d27991fb24073dda3bc819114c8f912a205e9`
under the separately committed fixed-target plan. Both HTTP responses were 200; Gamma
identity became available before book receipt. One receipt-time quote was observed and its
durable computation independently replayed with source/computation bytes unchanged. Raw
6,178 bytes; 81,737 retained before report; 75,972,608 peak resident bytes; whole-process
1,046,331,792 ns. Measurement plan available 13:13:10.462421 UTC; computation available
13:13:11.141974 UTC. Full evidence, report acknowledgement and script/plan/build hashes
are in PHASE_03_TARGETED_QUOTE_EVIDENCE.json. Source provenance is prospective; selection
remains historical, and no research origin, SQL row, predictive finding or pilot is admitted.
No source or measurement process remains active. No production action was taken.

### D047 original quote-computation reader

Reviewed original package extraction/hash binding, transitive source/child verification,
complete facts equality, original summary hash/availability and new read chronology. No
recomputation under current numerical code, source request, dependency installation,
checkout/reset or historical-clock changes. Existing frame/selection APIs stay compatible.
Output nesting inside either source or computation is refused; failed reads are preserved.
Ten new tests cover exact preservation, five closure corruptions, three nested output paths
and mutable/changed original code. Thirty focused original-reader tests pass (37.09s).
Full isolated backend **996 passed**, zero skipped, 155.90s, including disposable PostgreSQL. Full Ruff, canonical
and whitespace checks pass. No new collection or production changes.

Committed D047 then read the saved D046 journal under its original `761d279` code. Exact
full facts/summary equality and unchanged source/computation bytes passed. New read receipt
available 2026-09-22T13:23:45.247836Z; PHASE_03_ORIGINAL_QUOTE_READ_EVIDENCE.json preserves
its hashes and clocks. No new source request or origin admission. The next heartbeat found
this completed evidence file after the preceding usage window ended and records it without
repeating the operation. Documentation-only recovery check: canonical/whitespace pass.

### D048 immutable panel declaration

Reviewed explicit timing bounds, pre-read internal seed, complete scheduled/trigger/control
slot and outcome reservation, exact derived quotas, full disk preflight, fresh exclusive
output, failure preservation and independent replay. The declaration does not read source
numbers, resolve frame completeness, invent feature coverage or admit origins. Per-source
retained quotas remain planned until D049 guards actual writes. Existing computation caps
are reserved in full; no discount for measured-small responses or overlapping roles.
Thirty-nine focused cases passed (1.69s), including tampering, insufficient capacity, failed
acknowledgement and concurrent declarations. Full isolated backend **1,035 passed**, zero skipped, 167.83s, disposable PostgreSQL included.
Full Ruff/canonical/whitespace checks pass; one existing Starlette/httpx warning.
