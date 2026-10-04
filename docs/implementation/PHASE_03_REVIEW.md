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

### D049 source retained-byte guard

Reviewed every managed source write, raw capacity preflight before HTTP, exact recursive
byte/file/depth accounting, free-space checks, task-local async isolation, failed constructor
collisions, reserved failure evidence and terminal retry refusal. Raw responses survive later
generic/source parsing quota stops. No delete/overwrite or old source-clock reconstruction.
The original build verifier rejected a decorated context manager; a directly inspectable
generator plus factory preserves that guard without weakening it. Guarded runs refuse the
unbudgeted index-receipt path before DB access; default indexing remains unchanged.
24 new cases; **69 focused tests passed**, 13.64s, including full synthetic identity/book/trade
to quote computation. A fixture filename was corrected to satisfy the existing local-database
safeguard; the prematurely started full run was cancelled, then restarted after focused checks.
No live collection or production action. Full isolated backend **1,059 passed**, zero skipped, 167.05s, including disposable PostgreSQL.
Full Ruff/canonical/whitespace checks pass; one existing Starlette/httpx warning.

### D050 declaration-bound fresh selection

Reviewed frozen seed and full reservation binding, exclusive deterministic directory, full
original-code frame/projection closure, exact rational weights and lossless uniform
not-assessed inventory. Missing trigger evidence never becomes a measured negative control.
Verified source interval/age at actual cutoff and post-fsync acknowledgement; replay checks
original times without re-aging or current free-space requirements. Old development schema
and reconstructed provenance stay intact. Nested extra files/symlinks and changed evidence
are rejected. No live request, origin, SQL admission or production change.

Initial focused failures were fixture clock-key errors and a fabricated future acknowledgement;
the corrected durability-expiry test uses an actual 10-second save delay. Final new-path focus:
**26 passed**, 38.03s. Earlier combined legacy/new selection focus: 46 passed, 54.02s. Full
isolated backend **1,085 passed**, zero skipped, 214.23s, including disposable PostgreSQL.
Ruff/canonical/whitespace pass; one existing Starlette/httpx warning.

### D051 compact computation profile

Reviewed opt-in schema/profile selection, per-write artefact and recursive total checks,
whole child reservation, original source preservation, exact parent/child policy matching,
read-only recovery and panel cost/selection binding. Defaults retain 32/64 MiB bounds and v1
schemas. New compact 4/8 MiB bounds retain 2 GiB free and 64 KiB failure reserves; insufficient
capacity or oversized input stops without deletion, truncation or in-place profile upgrades.
Collection remains disabled and no live source requests were made.

The original-recovery fixture initially compared the full result wrapper to its summary;
corrected it to verify both the exact summary and full facts. The three-source fixture now
uses the actual trade pagination shape and asserts every source observation is observed.
Final compact focus: **20 passed**, 12.00s; prior combined defaults/declaration focus had
100 passing cases plus that single fixture assertion failure. Full isolated backend **1,105 passed**,
zero skipped, 225.33s, including disposable PostgreSQL. Ruff/canonical/whitespace pass;
one existing Starlette/httpx warning. The next heartbeat records these completed results
without repeating tests or measurements; prior short-window usage reached 100% before commit.

### D052 activation and immutable schedule

Reviewed complete selection/source replay before identity consumption, hash-bound projection
reads, no role duplication, extra origin/target metadata reservation, actual read/save clocks
and freshness at both completion and save. Schedules derive from acknowledgement plus the
frozen two-second lead; independent recovery preserves expired schedules and does not use
current disk capacity. Concurrent ownership has one winner; failures preserve partial output.
No collector, origin, source request, SQL admission or production change. Twenty focused tests
passed in 43.20s, including actual save delay, tampering and resource checks. Full isolated
backend **1,125 passed**, zero skipped, 276.63s, including disposable PostgreSQL.
Ruff/canonical/whitespace checks pass; one existing Starlette/httpx warning.

### D053 synthetic origin integration

Reviewed immutable schedule ownership, fixed request lineage and quotas, actual read-before-
freeze ordering, exact selected identity/rule matching, late-save derivation, partial-source
preservation, replayed source/computation closure and the live-transport refusal. Source parser
records require four path components below the origin root; the bounded inventory reflects
that real layout. Oversized Gamma responses preserve partial raw bytes as `transport_gap` and
produce `identity_unresolved_at_receipt`; they need not raise a worker exception. Cancellation
preserves an incomplete run and cannot resume. Resealed tampered price/intent tests exercise
semantic verification beyond outer checksums. No targets or live observations were collected.

Final focused tests: **19 passed**, 103.43s. Full isolated backend: **1,144 passed**, zero skipped,
386.55s including disposable PostgreSQL. The prior-window recovery report records unchanged
code during both runs; this continuation recovered the results without repeating the suite.
Full Ruff, canonical and whitespace checks pass; one existing Starlette/httpx warning.
Phase 3 remains incomplete. Next: frozen-identity target adaptation and due collection.

### D054 frozen identity target adapter

Reviewed exact projection replay/request binding, original mapping availability, separate fresh
identity consistency, changed-rule closure refusal, failed-book token lineage, explicit quality
states and computation-acknowledgement freshness. Earlier delayed computations still block
later quotes under the existing selector. The pure helper admits no caller-provided outcome;
the due worker must authenticate journals and record actual consumption. Source/runtime
formats were exercised with guarded synthetic journals, and old target outputs are unchanged.

Focused adapter plus existing target rules: **53 passed**, 2.97s, including 32 new cases. Full
isolated backend: **1,176 passed**, zero skipped, 581.27s, including disposable PostgreSQL.
The recovery report records unchanged code during regression. Ruff/canonical/whitespace pass.
One existing Starlette/httpx warning. No live collection, SQL or production changes.

### D055 synthetic due worker

Reviewed exclusive ownership, fixed target schedules/attempt count, source quota/profile
binding, request-start deadline checks, and origin receipt before all target requests.
Origin facts and intent bytes are rebound to the verified hashes when consumed. Every
ineligible/expired/failed attempt remains in the plan/report. Partial computation failure
blocks later outcome selection; known failed-source states stay explicit exclusions.
Independent replay recomputes source/adaptation/target output and exact signed midpoint
change under original clocks. It does not infer executable value or admit SQL labels.

Review corrected availability to include the final target receipt, including the adapter's
actual read/calculation/save, while retaining earlier quote-computation availability. A real
delayed-save test exercises the boundary. A late response can finish within the rounded
request budget but beyond tolerance; the actual late receipt is retained and excluded.
The standalone executor can miss early horizons if launched after a multi-cycle origin run;
interleaved orchestration remains required. MockTransport-only gating remains in place.

Initial focused tests: 15 passed, 269.61s. Final changed-path checks: 3 passed, 14 deselected,
76.15s. Ruff/canonical/whitespace checks pass. Full isolated backend: **1,193 passed**, zero skipped, 1,565.57s, including disposable
PostgreSQL and all 17 new due-worker cases. The following heartbeat recovered this completed
result and verified that code was unchanged during and since the run; it did not repeat
tests or measurements. One existing Starlette/httpx warning. Synthetic due integration is
accepted as a software milestone; interleaved orchestration and full Phase 3 gates remain.

### D056 interleaved runtime — checkpoint, acceptance pending

Reviewed one serialized deterministic queue, exclusive runtime/activation ownership, whole
reservation, per-origin target plans before calls, source/intent/fact hash binding, actual
dispatch/completion clocks and full replay of the evolving queue. Existing origin/due APIs
and schemas are unchanged. Five focused tests passed in 65.88s: two real-clock cycles, target
before the next origin, ties/ineligible dispatch, honest slow-origin expiration, cancellation/
concurrent ownership and live/clock/capacity refusal. Full regression is pending; do not mark
D056 or Phase 3 complete. No live requests, admission, production change or evidence promotion.


D056 follow-up review recovered the 1,198-pass result at `418a130` (zero skipped,
1,260.04s); the saved and current fingerprints matched before further code changes. Review
identified the missing original-runtime recovery path, now added through the existing bounded
Git decoder. Four new cases passed in 130.48s: exact full-report recovery and dependency-path
protection, plus altered raw source, event ordering and outcome refusal. Source snapshots and
Git fixtures remain byte-identical after successful/failed reads. This is read-only recovery,
not redispatch or retrospective admission. Ruff and canonical checks pass. Combined regression
is pending; the sandbox loopback denial is an environment restriction, not a passing test.
The suite was restarted with approved local-service permission. No production service is used.


D056 final acceptance recovered on 2026-09-24: **1,202 passed**, zero skipped, 1,363.95s,
including disposable PostgreSQL. The recorded and freshly recomputed source/test fingerprints
match `0ef54cf49942a41862416a9bff36a3087ba96bc517aeb11e2e364b9ebb6f2df0`; the tested
implementation is committed at `72f89a8`. One existing Starlette/httpx warning. No unchanged
suite was rerun. Final review includes the canonical-directory checks inherited from `_pair`,
exact original-report equality, source dependency output isolation, immutable clocks, queue
ordering and terminal cancellation. D056 is accepted as a synthetic software milestone;
Phase 3 remains incomplete. The next feature-window contract preserves the stricter data gates.

### D057 exact book snapshot components and durable recovery

Reviewed exact F08/F09 algebra, raw level order/precision/zeros, arithmetic exponent/digit
bounds before rational expansion, native clock/tick missingness and source-local units.
Invalid/stale/closed/failed sources remain explicit without zero price/component fallbacks.
Policy/result dictionaries do not alias mutable global policy. Writer/replay bind complete
source/child closure, actual read/compute/fsync chronology, frozen build and exact canonical
results. Partial acknowledgement/cancellation retains evidence; concurrent ownership has one
winner. Capacity checks include child files, failure reserve, per-artefact and whole ceilings.
Original-code recovery verifies all facts under the exact pinned code without rewriting clocks;
shared frame/selection/quote/runtime original-reader paths remain compatible.

Validation: 150 affected tests passed in 326.69s across book primitives/computation/original-book,
all other original readers, quote computation/inputs and input reads. Compact-storage regression:
20 passed in 39.38s. Earlier new-path focus: 44 passed in 25.85s. Full backend Ruff, canonical
contract checker and whitespace checks passed. Tests used explicit isolated SQLite URLs with
email disabled; no production DB, source requests or frontend changes. The prior full 1,202
D056 result is historical baseline coverage, not a full-suite claim for D057. A first invocation
named a nonexistent compact test file and collected no tests; the corrected file passed above.

This accepts the scoped snapshot software milestone only. New capture/coverage contract
PHASE_03_DENSE_WINDOW_NEXT.md preserves the public feed's unproven sequence semantics; no
native event order, feature-window completeness, predictive edge or Phase 3 completion inferred.

### D058 bounded synthetic raw window and original recovery

Reviewed subscription-anchored actual duration, fixed heartbeat schedule, one pending receive,
completed-receive draining before termination, late-frame accounting and cancellation cleanup.
Raw text/binary/control/invalid JSON bytes remain uninterpreted evidence. Journal records actual
receipt and post-fsync clocks, preceding hash and ordinal, exact prefix/full-observed hashes and
explicit truncation. Strict file/byte/event limits include outbound payloads; partial write or
capacity failures cannot seal a valid report. Replay enforces same-session chronology, exact
closure, outbound send order and original policy/build, without sampling new observation clocks.
The only admitted driver input is the exact bounded immutable synthetic fixture class. There is
no socket/live transport, SQL operation, production path or feature eligibility claim.

Initial 23 tests passed in 20.39s. Final affected regression **40 passed in 42.46s**, including
26 new window/original-window cases, original-book recovery, legacy stream probe and book
replay. Added reduced synthetic-budget tests cover frame and raw-total stops; production limits
remain fixed. Ruff, canonical checker and whitespace checks pass. Explicit isolated SQLite URL
and disabled email; no external source requests. D057's 170 affected checks remain the preceding
accepted baseline; no combined full-suite result is claimed for D058.

This accepts raw synthetic capture/recovery only. Next decoded coverage must distinguish
control/invalid/unrelated/late events and gaps from numerical updates. Native sequence, fill
identity, source-rights/identity verification, live transport and pre/post reconciliation remain
unproven. Phase 3 is incomplete; no further phase is started.

### D059 decoded coverage and durable computation

Reviewed source/report/event/raw binding at actual consumption; immutable read/computation/fsync
clocks; exclusive ownership; whole/artifact/storage/time limits and terminal partial failures.
Raw arrays keep element lineage and common receipt time. Unrelated/control events cannot create
elapsed updates; PONG/trade/tick does not refresh book receipt age. Missing initial snapshots,
invalidated/stale intervals, early tails and late frames remain explicit. Repeated equal numeric
books do not become independent changes. Exact rational time weighting differs from update-count
weighting and never fills an uncovered interval with zero. Best-price assertions, including
integer-form token IDs, are checked against replay. Unsupported relevant input or identity/book
conflict requires a new snapshot; earlier gaps remain. Original-code reads preserve complete
facts/summary and source/output bytes, while protecting all source dependency paths.

Initial pure focus: 22 passed in 0.47s. Initial durable/new recovery focus: 41 passed in 29.48s.
After review added source clock-order/terminal guards and an integer-token best-assertion case.
Final affected regression: **90 passed in 112.85s**, including all new pure/durable/original
coverage paths, prior window capture/recovery, original book/quote recovery and BookReplay.
Ruff, canonical and whitespace checks pass. Explicit isolated SQLite and disabled email; no
live source requests, database migration or frontend/production changes. Prior full D056
regression remains historical baseline coverage, not a combined full-suite claim for D059.

Only synthetic receipt diagnostics are accepted here. The declared window identity is not yet
causally admitted; native sequence, native age, complete fills and economic independence remain
unknown. Next execute PHASE_03_WINDOW_IDENTITY_NEXT.md before live transport. Full Phase 3 pilot,
measured controls/external admission and acceptance remain outstanding; Phase 4 stays out of scope.

### D060 pre-subscription binding

Reviewed exact two-source targeted identity/book closure, ordered mapping/rule fingerprint and
explicit known-active lifecycle. Derived token/condition has no caller override. Actual read,
computation receipt, binding fsync and child subscription chronology are checked independently.
Freshness is replayed at original read/save/subscription times, never current time. Delayed
subscription remains identity_expired_before_subscription; it does not rewrite a binding or
admit an origin. Whole 40 MiB reservation includes the unchanged 32 MiB child. Cancellation,
partial acknowledgements and concurrent ownership preserve all evidence. Original-Git recovery
protects parent, pre-computation and raw-source dependencies and rejects corruption.

New binding/recovery suite: **17 passed in 87.37s**. Initial late-subscription fixture used a
2-second pre-age limit, which correctly rejected already-stale evidence before binding. The
fixture was changed to a predeclared 10-second limit and 10.2-second delay so it reaches the
intended later boundary; no production policy or empirical data was changed. Affected existing
book/window/recovery regression is recorded in the final acceptance note below. Ruff, canonical
and whitespace checks pass. Tests use explicit isolated SQLite and disabled email. No real
source requests, live socket, SQL, frontend or production changes.

Scoped software acceptance does not complete Phase 3. Post-window comparison must verify actual
primary request-start clocks after the bound report, not infer chronology from response receipt.
Then the bounded live adapter, measured controls, selected external information and prospective
pilot remain. Phase 4 is reserved for a fresh Codex conversation.

D060 final acceptance (2026-09-24): **17 new tests passed in 87.37s**, plus **52 existing affected tests passed in 96.36s** (69 total across the two disjoint runs). No code changed between these runs. Ruff/canonical/whitespace pass. No test or collector remains running. D060 is accepted only as the pre-subscription synthetic binding/recovery milestone; Phase 3 is incomplete. Resume post-window chronology/reconciliation as specified above.

### D061 post-window request chronology and endpoint reconciliation

Self-review checked primary capture request-start/hash/request binding against verified input
rows, conservative after-bound-report chronology, original ordered mapping/rule availability,
known lifecycle, explicit failed/missing/stale states and expired pre-binding refusal. Exact best
price/size differences preserve raw-primary references and source-local units. First observed
snapshot is not a subscription-time observation; invalid/stale/early tail cannot use the last
good snapshot. Earlier gaps and native continuity remain unaltered. Independent replay verifies
actual read/calculation/durability, exact values, complete closure and all dependency hashes.
Original-Git recovery protects bound, pre/post computation and raw-source roots. Exclusive output,
finite metadata/storage/time bounds, partial failures and cancellation retain evidence.

Initial test fixture inherited disconnect-on-exhaustion from the D060 helper: the unavailable
end state was correct. The endpoint fixture now explicitly keeps its synthetic connection open
for a fixed 500ms window; no implementation guard was relaxed. Subsequent initial run had
20 passes before a cancellation fixture replaced loaded module code and correctly hit the build
identity guard. Cancellation is now injected at a file acknowledgement boundary; no build guard
was weakened. Final affected validation is recorded in the checkpoint/acceptance note.

Only synthetic software is tested. No public requests, production changes, live socket, SQL
admission or Phase 3 empirical acceptance occurred. The separately planned socket transport must
reject redirects as well as proxies, preserve actual failure clocks/bytes and pass loopback tests
before a committed diagnostic protocol can run. Measured controls/external information/pilot
remain required; Phase 4 does not begin in this task.

D061 final affected validation: **63 passed in 300.57s**. Command: explicit isolated SQLite URL
and disabled email, `.venv/bin/pytest -q` over unit/test_research_panel_{window_reconciliation,
original_window_reconciliation,original_bound_window,original_window_computation,original_window,
original_book,window_coverage}.py. Ruff, canonical contract and whitespace checks pass.
No code changed during this final run. Prior full D056 result is historical, not a new full suite.

### D062 fixed socket connector

Self-review checked fixed source URI/options, no caller auth/headers/host overrides, proxy=None,
compression=None, disabled transport pings and single-await connection with no retry iterator.
All redirects return the original refusal, including same-origin changes. The explicit loopback
seam permits only canonical integer ports at 127.0.0.1 and remains synthetic. Tested dependency
version is checked before opening. Returned contract dictionaries do not alias options. Connect
has a five-second outer deadline; close has two seconds and aborts on failure/cancellation without
masking the original error if abort also fails. Importing the module opens nothing.

This is a connection primitive, not the durable driver. It does not authenticate caller identities,
persist receipts, schedule PINGs or enforce a whole capture's message/window/total-byte budget.
No runtime/CLI/production path calls it. The next driver must own those obligations before a
public diagnostic is allowed. Initial local transport tests: 15 passed in 0.29s. Added actual
handshake deadline and close-abort failure tests, plus original recovery regression; final result
is recorded below. No public socket, data acquisition or empirical Phase 3 acceptance occurred.

D062 final validation: **23 passed in 64.86s** using explicit isolated SQLite/email-disabled
`.venv/bin/pytest -q` on unit/test_research_panel_socket_connector.py (17),
unit/test_research_panel_original_window_reconciliation.py (2) and
unit/test_research_panel_original_bound_window.py (4). No code changed during the final run.
Ruff/canonical/whitespace checks passed. No test/collector remains running. This accepts the
connector boundary only; all durable integration and empirical Phase 3 gates remain open.

### D063 durable socket driver and recovery

Reviewed policy-before-read/connect, immutable prior identity/rules and source provenance, actual
read/fsync availability and fresh checks after connection and subscription-intent persistence.
Loopback and public entry points expose no arbitrary identity/clock/factory/provenance override;
a refused public attempt with synthetic inputs remains synthetic. Actual receive, journal record
and durable availability are separate. Single connection/subscription, fixed ten-second PINGs,
one pending receive, finite frame/byte/event/processing budgets and close-on-failure remain.
Raw prefixes with observed full hashes/counts differ from wholly unavailable rejected data.
Network error records retain class/close codes without peer reason text; local I/O errors remain
local failures. Replay checks append/hash/clock/session/order/freshness/terminal/cleanup facts and
transitive source dependencies. Original-code recovery opens no new connection and preserves clocks.

Initial focus caught integer-enum WebSocket close codes being omitted by an exact-type check.
Accepting bounded integer enum values and serialising their integer value fixes evidence retention;
no source or admission gate was weakened. After that fix, 19 new driver/recovery checks passed
in 99.58s. Added explicit send/timeout/close-error and reduced synthetic byte/frame-budget tests.
Final affected result is recorded in the checkpoint/acceptance note. Tests use actual local
loopback only, isolated SQLite URLs and disabled email; no public source requests, production
changes, SQL admission or empirical Phase 3 acceptance.

Next consume these verified journals into versioned receipt coverage/post-window diagnostics,
then commit a separate bounded public diagnostic protocol. All measured control/external/pilot
gates remain open; Phase 4 is reserved for a fresh conversation.

D063 final validation: **47 passed in 183.97s** using explicit isolated SQLite/email-disabled
`.venv/bin/pytest -q` over unit/test_research_panel_{socket_window,original_socket_window,
socket_connector,original_bound_window,original_window_reconciliation}.py. Code unchanged during
the final run. Ruff/canonical/whitespace pass. This is scoped software validation; prior full
D056 result is historical. No collector/test remains active.

### D064 socket coverage and post-window diagnostics

Self-review covered policy-before-read, dependency path protection, actual read/compute/durability
ordering, exact raw chain/manifest replay and original full-facts recovery. The adapter derives
identity/provenance from the socket journal and authenticates every post request using its primary
capture receipt. It shares only pure numerical algebra with D061; old synthetic guards remain.
Missing post, early request, changed rules, closed/failed sources, refused subscription and early
termination remain explicit. Receipt persistence never proves native continuity or feature
admission. Endpoint agreement cannot repair gaps. No public request, production change or SQL
admission occurred. Initial 13 new tests passed in 157.66s. Added resource/concurrency/early-close
cases before the final affected run. Final result is recorded below when complete.

D064 final validation: **70 passed in 471.27s** on explicit isolated SQLite with email disabled:
`.venv/bin/pytest -q tests/unit/test_research_panel_socket_analysis.py
tests/unit/test_research_panel_original_socket_analysis.py
tests/unit/test_research_panel_window_reconciliation.py
tests/unit/test_research_panel_original_window_reconciliation.py
tests/unit/test_research_panel_original_socket_window.py
tests/unit/test_research_panel_window_coverage.py`. Code unchanged during the run. Ruff, canonical
and whitespace checks passed. Initial 13 new tests remain a preliminary subset, not additive
coverage. All 19 final new cases plus 51 affected cases passed. No active collector/test remains.
D064 software contract accepted; public-source and panel acceptance remain open.

### D065 fixed diagnostic orchestration

Reviewed exact fixed target/request count, committed source/panel hash check before requests, full
capacity reservation, retained stage intents, no implicit retries, unknown/closed/failed-prior
abstention, socket-controlled identity freshness and post request chronology. All children retain
their own bounded persistence/error semantics and source provenance. Successful children receive
independent and original-Git recovery; parent memory reporting explicitly excludes child peaks.
The CLI has one fixed attempt directory and refuses restart. Failure records contain class/stage/
time only and never erase partial evidence. Initial full-chain fixture caught an unsupported
floating-point elapsed time; changed report to exact integer nanoseconds. Final affected tests
are recorded below before any public run. See PHASE_03_SOCKET_DIAGNOSTIC_PROTOCOL.md.

D065 final validation: **8 passed in 82.46s** on explicit isolated SQLite/email-disabled pytest:
`backend/tests/unit/test_research_panel_socket_diagnostic.py` (5),
`backend/tests/unit/test_research_panel_original_socket_analysis.py` (1) and
`backend/tests/unit/test_research_panel_original_socket_window.py` (2). No code changed during
the run. Ruff/canonical/whitespace passed. Public diagnostic not yet run at this commit; all
new tests use synthetic HTTP and local sockets. Underlying D064 70/D063 47 remain accepted.

D065 public attempt under committed `c9042eca9f9e2dc6f616b097836f259a32331dc5` completed once,
CLI exit 0. Root `data-dumps/fs2_socket_diagnostic_20260925_1`; source/analysis/recovery evidence
in PHASE_03_SOCKET_DIAGNOSTIC_EVIDENCE.json. Four fixed HTTP requests, all retained; one 60-second
socket from 11:36:38.677297 to 11:37:38.679786 UTC on September 25. One initial book plus five
PONGs; 23 journal events, five PINGs, clean close. The frozen one-second receipt hold yielded
exactly 1,000,000,000 covered and 59,000,000,000 uncovered nanoseconds. Initial best-price/size
comparison agreed; endpoint stayed unavailable (`window_end_unavailable`). Quiet transport and
PONGs do not establish unchanged market state or extend book freshness. Registered F02/F10/F27
remain unavailable. Four independent/original-code recoveries passed without changing old clocks.
HTTP raw 12,378 bytes; socket retained raw 1,470 bytes (includes sent/control evidence); total
retained including final report 372,356 bytes. Elapsed 88,618,854,542ns; parent peak 80,150,528
bytes, excluding recovery-child peaks. Report durable after 11:38:04 UTC. No retries, alternate
targets, production/SQL changes or accepted panel. Preserve the failed coverage formulation;
do not lengthen its hold or reinterpret quiet history retrospectively.

### D066 predeclared snapshot assessment

Reviewed exact reduced threshold, signed/absolute/difference preservation, explicit negative vs
unavailable state, actual declaration before primary request starts, fixed requested and returned
identity, known-active lifecycle and freshness at calculation. Read/computation/durability clocks
remain separate, and later sampling must recheck age. No native-window/registered-feature or
scientific-winner claim. Exclusive child ownership prevents competing writers from damaging the
winner; cancellation/partial writes remain terminal. Full independent/original-Git recovery
protects declaration/book/source roots. No new public request or alteration of D065 evidence.
Initial 15 new tests passed in 63.43s; added the in-flight early-request trap (response arrives
after declaration but request began before it) before final affected regression.

D066 final affected validation: **52 passed in 98.16s** on explicit isolated SQLite/email-disabled
pytest over unit/test_research_panel_trigger_computation.py, test_research_panel_assessments.py,
test_research_panel_original_socket_analysis.py and test_research_panel_original_socket_window.py.
No code changed during the run. Ruff/canonical/whitespace pass. D066 is a software milestone only.
Next run a backend-wide isolated regression because original-reader dispatch/build manifests now
include several new journal types since the D056 full baseline; untouched recovery kinds must
also be checked before composing them into a measured screening/control pipeline.

D066 backend-wide attempt: **728 passed, 19 failed**, one existing warning; interrupted after
196.14s of pytest. All recorded failures arose in existing activation fixtures at the unchanged
full storage-reservation check. No final full-suite pass; remaining tests unrun. Fingerprints
unchanged. See PHASE_03_FULL_REGRESSION_CAPACITY_EVIDENCE.json. Current disk about 4 GiB cannot
satisfy the 4,289 MiB compact or 5,969 MiB default fixture reservations plus temporary headroom.
/tmp shares the volume; no other local data volume found; all pytest temporary roots combined
would not clear the larger requirement. No evidence deleted or safeguard weakened. Local test
capacity requested (at least 8 GiB free); further implementation waits for this validation gate.


## D067 — UTC boundary verification (2026-09-27)

Capacity restored; unchanged D066 full run: 1,438 passed/4 failed, 1,468.63s, unchanged code/test
fingerprint. Evidence: PHASE_03_REGRESSION_RECOVERY_EVIDENCE.json. Three failures were genuine
early timer wakeups; strict replay refused early intents. Fourth was a stale book after a
host pause. D067 rechecks UTC at collection intent, dispatch and final cutoff, returning the
actual clock; bounded backward-clock waiting refuses divergence. No guard loosened.

Affected command: pytest backend/tests/unit/test_research_panel_{scheduling,origin_worker,
due_worker,runtime,original_runtime,original_bound_window}.py -q --tb=short, explicit local
SQLite and disabled email. Initial 53 passed/2 failed/1 teardown error in 483.75s. New clock
test isolation fixed (shared time module mock affected asyncio); six clock tests pass in 0.12s.
Scheduling+due retry: 22 passed/1 pause-induced expiry in 229.48s. Exact remaining rate-limit
case passed in 18.64s under temporary process-scoped sleep prevention. All 55 distinct affected
cases pass across runs; no all-green full-suite claim. Ruff/canonical/whitespace pass. Review
confirmed no clock fabrication, evidence edits, production changes or source requests. Phase 3
is incomplete. Next: authenticated screening/control integration using existing sampler.


## D068 — authenticated screening/control planning

Reuses the first-stage selection, D066 journals and existing sampler; no alternate sampler or
infrastructure. Owns rule/seed/assignments before acquisition, verifies current mapping/rule and
source provenance, preserves all first-stage selections and computes conditional matched roles.
Unknowns never become negative controls; unavailable/stale identities, one-sided pools, partial
screening and unfilled controls remain explicit. Original-code recovery protects transitive
inputs, exact facts and old clocks. No global arm probability or empirical acceptance is claimed.

Final validation: 64 passed in 140.15s using pytest on test_research_panel_screening.py,
test_research_panel_assessments.py and test_research_panel_trigger_computation.py -xq --tb=short.
Explicit local SQLite, disabled email, synthetic HTTP only, process-scoped sleep prevention.
Fifteen new screening cases include positive/negative, both one-sided pools, no assessments,
changed mapping, staleness, source failures, partial screen, tampered raw/plan/clock/assignment,
exclusive completion, full original recovery and retained nonterminating 2/3 first-stage weight.
Initial tagged-UTC decoding defect corrected without relaxing datetime checks. Full backend
baseline remains as recorded under D067; no redundant full-suite rerun. Ruff/canonical/whitespace
pass. Self-review confirmed no future inputs, no redraw, no negative imputation and no production
changes. Next: bounded source worker and verified-role activation under the full reservation.


## D069 — bounded first-stage stratum draw (2026-09-27)

Self-review: full inventory and original matching dimensions survive; only complete entirely
unassessed frames use the new design. Independent domain-tagged stratum ranking precedes the
existing member ranking. Exact min(L,T)/T × min(n,N)/N is preserved even when its denominator
exceeds the single-frame count limit. The cap is frozen before frame reads and checked against
worst-case scheduled slots. Unknown/singleton/unsampled strata remain explicit; controls are not
inferred. Legacy defaults and golden plan hash pass unchanged. New selection versions reach
D068 but remain refused by old activation. No runtime, public source or scientific gate enabled.

Validation: **193 passed in 217.52s**, explicit isolated SQLite, disabled email, process-scoped
caffeinate. Suites: test_research_panel_{bounded_sampling,planning,assessments,declaration,
bound_selection,screening,compact_storage,original_selection}.py. Includes exhaustive small
population design mass, cap/population boundaries, future/measured-input refusal, original-Git
recovery, full inventory and resealed cap/stage-weight/unsampled-inventory corruption.
Development run: 45 passed in 16.88s. Final log /tmp/arepo_d069_acceptance.log. Ruff across
backend, canonical contract and git diff --check pass. No full backend regression repeated.

Remaining: full-reservation acquisition worker, verified-role activation and scalable observation
runtime, selected external information and actual prospective pilot acceptance. Phase 3 incomplete.


## D070 — bounded synthetic screening acquisition (2026-09-27)

29 affected tests passed in 189.01s: test_research_panel_screening_worker.py (14) and
test_research_panel_screening.py (15), explicit local SQLite, disabled email, caffeinate.
Log: /tmp/arepo_d070_final.log. Ruff/backend, canonical contract and whitespace checks passed.
Prior development run: 10 passed/one failed expectation in 91.58s; oversize source responses
correctly yielded retained unavailable evidence rather than exceptions. The test now asserts
that behavior; a separate injected storage failure checks cancellation and preserved raw data.

Self-review: exclusive ownership, frozen request/response/retained quotas, bounded parallelism,
full future current-runtime reservation, provenance, no source replacement/retry, changed/rate-
failed sources, exact matched roles, role overflow refusal, immutable original recovery and
cancellation drainage. Original screening recovery covers every source/book/decision plus
selection/frame/panel; separate original child reads would duplicate that proof.

Only synthetic acquisition is enabled. Worker summaries are not admission authority; future
activation must consume read_screening and prove role/identity/clock closure. No public panel,
new empirical measurement, production change, external-source admission or Phase 3 completion.


## D071 — authenticated screened-role activation (2026-09-27)

57 affected tests passed in 402.86s: test_research_panel_{screened_activation,activation,
original_runtime,screening_worker}.py. Development: 18 passed in 178.02s; final adds exact
age-boundary checks. Explicit isolated SQLite, disabled email and caffeinate; log
/tmp/arepo_d071_final.log. Ruff/backend, canonical-contract and whitespace checks pass.

Self-review covered actual screening availability, role count ceilings without overlap
discounts, market deduplication, exact first-stage/conditional weights, canonical assessment
clocks, freshness at read and save, seed/report pinning, changed source/identity/context
refusal, legacy schema behavior, output outside evidence and original-Git recovery.
Pure role-capacity arithmetic moved from screening_worker to panel_declaration for reuse.
No public collection or phase acceptance. Next: bounded concurrent screened runtime with
reserved target capacity, replayable actual dispatch/completion and cancellation drainage.

## D072 — bounded concurrent screened runtime (2026-09-27)

21 affected tests passed in 246.37s: test_research_panel_{concurrent_runtime,runtime,original_runtime}.py, explicit local SQLite, disabled email, process-scoped caffeinate. Log: /tmp/arepo_d072_final.log. Ruff/backend, canonical and whitespace checks pass. No full regression repeated.

Self-review: 2–8 jobs, at most C−1 origins, ready targets before ready origins, actual parent dispatch/completion events separate from child intent/receipt/freeze clocks. Isolated job event loops prevent synchronous parsing/fsync from stalling other jobs. Cancellation drains durable writers. Replay verifies evolving queue/capacity, all child roots/clocks/outcomes and original-code screening dependencies. Legacy runtime remains compatible.

Development fixture initially retained a late third origin under an 8s synthetic budget; final fixture uses a predeclared 20s budget and deterministic slow second dispatch. No real protocol deadline or causal guard changed. Delayed multi-market validation proves target dispatch during a slow origin, not real-world throughput. Runtime remains MockTransport-only, synthetic, unadmitted. Persistent numerical windows, selected external admission and the empirical panel remain required.

## D073 — restricted official external observation (2026-09-27)

NWS/NOAA research-register XNOAA selected after current Coinbase terms excluded automated/AI-system use absent consent. URLs and exact frozen source measurement are in PHASE_03_EXTERNAL_OBSERVATION.md. No consent/payment requested; old diagnostics retained.

Development 67 passed in 38.45s. Final affected suites (NWS, capture, source_bridge, source_run, source_parsers, input_read, original_runtime): 105 passed in 165.53s, /tmp/arepo_d073_final.log. Final review found OpenAPI advertises GeoJSON; explicit pinned Accept header added before any public request. All 57 affected NWS/capture/source_run cases then passed in 23.38s, /tmp/arepo_d073_headers.log. Explicit isolated SQLite, disabled email and process-scoped caffeinate. Ruff/backend, canonical and whitespace checks pass. No blanket full-regression claim.

Self-review: default policies remain closed; fixed host/path/header and bounded station, exact raw/native value/unit/QC/null retention, source timestamp distinct from unknown publication/first availability, unknown/future native times preserved, changed same-ID revisions retained, new-source parser replay against raw, actual input-read chronology and original-Git recovery, no dependency overwrite, source failures, no retry, full one-request/recovery reservation and pre-request build pin. No source-defined URL is followed. Synthetic tests are not empirical evidence. Commit/update PR before the single predeclared public request; record failed/unavailable responses as such. Phase 3 remains incomplete.

D073 measured once under `77d6652`: HTTP 200 observed prospective NWS response, actual input read and original-Git recovery passed. Evidence: PHASE_03_NWS_SOURCE_EVIDENCE.json. The fixed KNYC reading has no automatic selected-market relevance and does not complete Phase 3. Do not repeat this measurement. Resume the live checkpoint's numerical-family/origin integration step.

## D074 — exact snapshot components at causal origins (2026-09-28)

D074 numerical origin integration accepted as a synthetic software milestone: 44 affected tests passed in 615.56s. Exact snapshot ratios, actual computation/freeze clocks, ineligible-origin preservation, due targets, original-Git recovery and legacy compatibility pass. No public runtime or predictive admission. Next execute PHASE_03_SCREENING_MEASUREMENT_PROTOCOL.md to measure source/control limitations before further window orchestration; all full pilot gates remain.

Validation: isolated SQLite/email-disabled pytest on test_research_panel_origin_features.py,
origin_worker.py, concurrent_runtime.py and original_runtime.py: **44 passed in 615.56s**;
full log /tmp/arepo_d074_final.log. One development test-helper callback error was corrected;
no scientific safeguard was relaxed. No package files changed during the final run.
Self-review: source/input closure reused, full level authority preserved, 16 KiB manifest
inside unchanged metadata reservations, policy bound before requests, computation before
freeze, eligibility refreshed at freeze, original cutoff replay, explicit version dispatch.
Unsupported registered windows remain unavailable. Ruff/canonical/whitespace checks pass.

The next bounded screening measurement is a sequencing refinement toward empirical progress,
not a waiver of window/external relevance or full origin/target pilot acceptance.

D075 public screening entry point accepted as software only: 16 screening-worker tests passed in 156.35s. Public API accepts no transport/provenance override; prospective assignment lineage is checked before source construction, while synthetic API still requires MockTransport. Existing concurrency, budgets, raw failures, cancellation and original recovery pass. No public measurement yet. Execute the single frozen script in PHASE_03_SCREENING_MEASUREMENT_PROTOCOL.md; no redraw/retry.

D075 measured once under e271497: eight Gamma 200, six book 200, two book 404; 41,576 raw bytes. All eight screens remain unavailable because targeted responses omit frame event IDs; all other identity fields match. Three positive/three negative snapshot calculations are not admitted roles. Original-Git recovery passed; no origins or accepted panel. Evidence: PHASE_03_SCREENING_MEASUREMENT_EVIDENCE.json. Next: PHASE_03_IDENTITY_COMPARISON_NEXT.md; do not rerun or reinterpret this attempt.

D076a comparison primitive implemented: 28 focused tests passed in 0.36s. Exact canonical frame-hash validation and current authenticated hash comparison distinguish full equality, only-event-omission equality, absent mapping and other differences. All core changes are rejected; event membership remains unavailable, economic grouping unresolved, and admission false. This pure helper is not wired into screening/origins/targets yet; no new collection or reinterpretation of D075.

D076b opt-in screening identity policy accepted: 39 screening/screened-activation tests passed in 697.66s (/tmp/arepo_d076b_final.log). New schema freezes the comparator before collection, retains raw-backed comparison evidence and preserves v1 replay. Asymmetric endpoint original-Git recovery and tamper refusal pass; changed rules remain unavailable. Legacy activation explicitly refuses the new policy pending its versioned origin contract. Worker API wiring and new empirical validation remain; D075 is unchanged.

D076c worker policy integration accepted: 19 worker tests passed in 205.20s, followed by 3 focused asymmetric-policy/original-recovery tests in 51.65s after import/line-format cleanup. Explicit identity_policy selects worker v3 and frozen screening v2; public/synthetic provenance still derives from actual transport. Defaults retain strict legacy behavior. Whole reservations, source failures, original-code recovery and no-redraw behavior pass. No new public collection; legacy activation remains barred from the new policy.

D076c self-review: policy validated before writes, version recorded before requests, identical
comparator passed into the durable screen declaration, original reader authenticates full
closure, source provenance remains transport-derived, default worker metadata unchanged.
No public collection or implicit activation. Exact logs /tmp/arepo_d076c.log and
/tmp/arepo_d076c_formatted.log. Ruff/canonical/whitespace pass.

Observed follow-on timing concern: D075 screen cutoff02:34:57UTC, recovery ended02:38:39UTC.
Do not place full original-code audit recovery before time-sensitive live activation/targets.
Resolve causal consumption and audit scheduling in the eventual live pilot contract; keep
original freshness limits and immutable evidence. No new service is implied.

D077 completed once under c6f4891661a979ab91755714869288152b8679fb: exhausted-consistent refreshed Gamma frame,236618 distinct/236574 mapped markets,44 unresolved;2367 requests,no retries/errors. Collection interval558.428363s fits the frozen600s screening cap. CLI exit0; complete verification passed. Evidence PHASE_03_FRESH_FRAME_EVIDENCE.json. Old frame remains unchanged; no accepted panel or predictive claim.


D078 measured once under9ea4e38b87ad242ea8d6d37e2536af2c15a69b2e: eight Gamma200 and eight book200 responses,44158 raw bytes. Eight scheduled/six triggered/two control roles across eight distinct markets; four unfilled control slots retained. All current event memberships unavailable; core identities match under the frozen explicit D076 rule. Stratum inclusion2/55 over110 strata; exact first-stage and conditional second-stage fractions retained. Full original-Git recovery passed; wrapper exit0. Screening cutoff04:24:04.526375UTC to recovery04:28:57.489384UTC is292.963009s, exceeding the120s age limit for future activation. No origin or accepted panel. Evidence: PHASE_03_SCREENING_REFRESH_EVIDENCE.json. Do not repeat this accepted measurement or backdate fresh origins; continue PHASE_03_PILOT_EXECUTION_NEXT.md.


D079 — owned pre-source screening context: screening v3/worker v4 retain an immutable bounded context minted by the actual complete selection read. Source completion no longer repeats population replay; cold/original audit still verifies all dependencies before worker return. Default legacy paths remain unchanged. Four new ownership/tamper/cold-recovery tests passed81.15s;39 existing screening/worker regressions passed500.62s. Ruff/backend, canonical and whitespace checks pass. Initial instrumentation replaced a protected function and correctly triggered build-integrity refusal; the test now observes real calls via profiling without replacing code. No public requests or new empirical claims. Activation/runtime wiring remains next; Phase3 incomplete.


D080 — owned activation v3: the private screening finish operation can transition directly to activation using its authenticated bounded state. It retains full original frame identity, the explicit comparison policy, report hashes, exact roles and actual read/save clocks. Cold/original activation recovery still verifies the full frame/selection/screening chain. Legacy activation remains unchanged; existing origin workers explicitly refuse v3 until versioned origin identity handling is implemented.64 affected tests passed839.55s: owned_activation, owned_screening, activation, screened_activation and origin_worker. Initial new test expected the wrong original-reader envelope; corrected to compare report.summary, with no implementation/guard change. Ruff/backend, canonical and whitespace checks pass. No public collection or Phase3 acceptance.


D081 — owned causal pilot execution: origin v3, due v2, concurrent runtime v4 and pilot worker v5 now compose authenticated screening, activation, causal origins and targets before full original-code audit. Public entry points accept no source payload, clock, transport or provenance override. Full frame identity and current event-membership missingness remain distinct; targets compare exactly against actual frozen origin identity. Legacy versions remain strict. No production or SQL change.

Validation: six new owned-pilot cases passed across development logs (a wrong test-result key was corrected without changing safeguards); 87 affected regressions passed in1334.27s (/tmp/arepo_d081_regression.log). Self-review found runtime_concurrency=None could select the internal screening-only path; public/synthetic wrappers now reject it explicitly. Eight focused invalid-input cases passed0.63s after that guard; no redundant broad rerun. Ruff/backend, canonical contract and whitespace checks pass. Review covered authenticated private context, actual provenance/clock ordering, strict target identity, bounded due capacity, cancellation drainage, immutable dependencies and original-code replay. Synthetic success is not empirical panel acceptance.

Next: freeze PHASE_03_OWNED_PILOT_PROTOCOL.md and execute D082 once under the committed implementation. Preserve all failures/missing controls/windows/related/external values. Phase3 remains incomplete; no Phase4.


D082 executed once under c881288d80dbeddfc195c6eacceeb63b78f58e20 and passed its frozen execution gates: eight observed origins/eight valid targets, six triggered roles/two observed matched controls over eight distinct markets; four unfilled controls retained. All56 requests returned200 (24 Gamma/24 book/8 taker-trade),183036 raw bytes. Origin freeze delay8.084763–29.097624s within60s; freeze-to-save1.463–17.300ms within5s; target durable availability5.477850–8.155644s after due within15s. Exact probabilities and raw numerics/clocks preserved. Full original-code audit passed; independent evidence check verified107 artifact hashes/sizes, all eight timing pairs, both matched pairs and exact counts. No code tests repeated for evidence-only changes.

Evidence: PHASE_03_OWNED_PILOT_EVIDENCE.json. Run completed2026-10-03T19:49:41.661088UTC, exit0, elapsed1003342292167ns including selection/audits; no collector remains active. D082 is a successful execution pilot, not predictive evidence or full Phase3 acceptance. PHASE_03_ACCEPTANCE_STATUS.md maps remaining pre-origin windows/history, related/external eligibility and baseline plumbing to the exact D083 next action. Do not rerun D077/D078/D082 or retrofit richer inputs into those origins. No Phase4.


## D083 — authenticated pre-origin window component (2026-10-04)

Owned origin v4/manifestv2 bind a verified pre-origin socket analysis and exact irregular
prior/current price primitives. Strict actual identity/provenance and cutoff/freeze age
checks preserve missingness; late eligibility never erases raw numbers. Sparse receipt
coverage never becomes venue continuity or a registered window feature. Legacy defaults
remain strict. See PHASE_03_PRE_ORIGIN_WINDOW_CONTRACT.md.

Validation:21 new input/origin cases passed255.10s; after final frozen16KiB quota guard,
53 affected window_origin/origin_worker/origin_features/window_reconciliation cases passed
611.89s (/tmp/arepo_d083_regression.log). Explicit isolated SQLite, disabled email; no source
edits during validation. Ruff/backend, canonical contract and whitespace pass. Self-review
covered actual clocks/freshness, identity/provenance, hash/raw tampering, negative/zero/missing
history, silence/disconnection, byte ceilings and legacy replay. Cold per-origin recovery
passes; full original-runtime dependency recovery is not yet wired. No public requests.

This accepts a software component, not Phase3. Next bind selected observers internally in
a bounded owned batch/runtime, reserve all dependencies before reads, retain failed members,
and test cancellation/original-runtime recovery before a separately frozen public measurement.
D082 remains immutable; related/external eligibility and full empirical scope remain open.
