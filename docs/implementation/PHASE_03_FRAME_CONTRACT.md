# Phase 3 frame adapter contract — next implementation milestone

This is a design contract, not collected data. Base implementation: accepted Phase 2 source
journal and Phase 3 pure sampling/target rules. Keep the current production discovery intact.

## Population and discovery authority

The research frame must explicitly name its population. Prefer all returned open Gamma
markets with source-native identity and retained eligibility/status fields; do not silently
inherit v1's 30-day/20k-liquidity product screen. Missing liquidity/category/close metadata
forms an unknown stratum, not an exclusion invented for convenience. Closed/inactive state
and unavailable token mapping have explicit exclusion reasons, with all source rows retained.
One predeclared outcome per market prevents market multiplicity from inflating sampling.

Start with an isolated bounded first-page diagnostic of the documented market keyset endpoint,
then measure bytes per returned row and source shape. Its allowed query is closed=false,
limit in 1..100 and an optional captured-parent after_cursor. Do not pass offset or silently
rely on the undocumented active filter. Any date/liquidity/tag filter requires a new explicit
population definition. The first page is never a complete-frame claim merely because the
returned rows fit the local budget.

Pin a new source registry/parser version and actual raw receipt envelope. The old gamma.markets
diagnostic source is a different endpoint/response contract. A keyset page uses a markets list
and next_cursor; each subsequent request must match the preceding response cursor and all
noncursor scope parameters. Retain page order, duplicates and failed attempts. An empty page
with a continuing cursor is contradictory and incomplete; a repeated cursor, schema error,
byte cap, timeout or stopped page budget is incomplete. End-of-list semantics must be checked
against the source protocol/runtime, not guessed from a convenient short page.

Hash the entire ordered page manifest and preserve every raw and parsed page, including
identical/changed repeated market rows. Conflicting versions of the same market cannot be
resolved by arbitrary first/last-row deduplication: retain both and establish an as-of policy
or mark the frame inconsistent. Successful pagination proves only enumeration under that
source's semantics over its collection interval, not an atomic global snapshot. Record interval
start/end, source freshness limits and any churn/reconciliation evidence.

## Budgets and representativeness

Measure first-page bytes and latency before freezing the complete-frame budget. Keep explicit
ceilings for request count, per-page bytes, total bytes, duration and retained records. Page
collection stops with an incomplete report if any ceiling is reached. Do not shorten the
population or discard raw fields after observing a storage result to claim success. If a
complete frame exceeds safe local capacity, preserve the measured report and refine a future
scoped measurement design or request a consequential infrastructure decision separately.

The CLOB simplified endpoint is only an alternative under investigation: its compact status/
condition/token data may lower cost, but category/liquidity/metadata availability and coverage
equivalence with Gamma must be demonstrated. Its sampling variant is not an automatic random
sample of the intended research universe. Neither source is admitted just by its name.

Only a verified frame adapter may attest runtime completion. The pure sample planner's
caller-supplied frame_status is deliberately insufficient for population inference. Freeze
frame/protocol/seed/strata and sample output durably before origin collection. Reserve source,
control and target budgets together. Failed controls and missed targets remain in the dataset.

## Required tests and integration

Test first-page scope, exact cursor parentage, scope drift, genuine termination, empty-with-
cursor contradiction, duplicates/conflicting identities, omitted identity fields, native
decimal precision, UTC clock regression, partial HTTP bodies, budget stop and crash recovery.
Replayed or reconstructed pages stay so labelled. Actual source verification is a separate
finite run after tests; it must not restart a production scan or application scheduler.

Connect accepted frame facts to the existing pure SamplingProtocol/FrameMember planner only
after source/identity as-of validation. Persist the full frame alongside its hash, rather than
only selected rows. Model-ready origin writing, feature reads/computation and label collection
remain separate following milestones. Unknown economic grouping prevents independence claims.

Documentation basis: [Gamma keyset](https://docs.polymarket.com/api-reference/markets/list-markets-keyset-pagination)
and [CLOB simplified markets](https://docs.polymarket.com/api-reference/markets/get-simplified-markets),
read 2026-09-20. These describe interfaces; empirical coverage and costs are not yet measured.

## Implemented first-page / finite-chain adapter (2026-09-21)

`research_panel/frame.py` freezes the source, build, scope and limits before the first request.
`frame_cli first-page` admits exactly one request, limit 100, at most 1 MiB of raw bytes,
15 seconds for the request and 30 seconds for the request-session budget. Final file sealing
and verification are separate local work. Existing diagnostic maxima remain in force; no
full-universe budget is inferred from a one-page test. All source rows, unknown metadata,
failed requests and duplicate versions are retained. Eligibility counts refer to source rows,
not independent events or deduplicated sample size. No models/origins are written.

Rechecked the official endpoint documentation on 2026-09-21: a continuation cursor occurs
on a full page; the last page omits it. The adapter requires fewer than `limit` rows AND an
omitted cursor for terminal evidence. An explicit null/empty cursor, a short continuing page
or a full page without a cursor is inconsistent with this pinned protocol and fails closed.
Exact page-size multiples therefore require a final empty page. Runtime measurement may
reveal a protocol disagreement; preserve it and investigate a future version instead of
silently loosening the current run. Documentation is not runtime verification.

Every page has the raw receipt, lossless generic parse, frame projection and their durable
acknowledgements. The final ordered manifest references all page hashes. Source and panel
builds are independently pinned; old measurement journals must be read using their original
implementation rather than silently projected under current code. A reader never fills torn
page/report acknowledgements or resumes network collection. Complete file-copy verification
is useful local recovery evidence, not the full archive-equivalence gate.

`exhausted_consistent` means this finite chain ended consistently with the pinned source
protocol. It still sets population inference eligibility false: sampling integration, interval
freshness/churn, source coverage, durable seed/protocol and eventual panel acceptance are
separate obligations. `exhausted_inconsistent` retains contradictory market/condition/token
versions; `incomplete` retains any page/budget/clock/integrity interruption. There is no
first/last-version winner. One source-ordered outcome is selected deterministically per valid
row for future frame mapping, never selected by its price or result.

## Measured enumeration protocol v2 (frozen before larger run)

First-page evidence: `PHASE_03_FIRST_PAGE_EVIDENCE.json`, implementation `bf734a0`.
100 returned rows, 557,140 raw bytes, 1,501,764 retained file bytes and 157,199,875 ns of
request-to-final-receipt monotonic time. It is incomplete with a continuing cursor. One page
cannot estimate total population, tail page sizes or complete-run latency. Local free capacity
at the sizing check was 17,415,118,848 bytes; no hosted infrastructure was inspected/changed.

The next **finite attempt**, not a completeness promise, has these frozen ceilings:

- 1,000 sequential requests, 100 rows/page (at most 100,000 returned row slots), no retries;
- 4 MiB per response and 256 MiB total raw response bytes;
- 15 seconds/request and 900 seconds for admitting requests;
- 1 GiB retained-file stopping budget, plus at least 2 GiB free-space reserve;
- unchanged `closed=false` population with no added date, category, activity or liquidity filter.

These are deliberately bounded cost limits based on the measured first page and local space,
not an estimate of the number of open markets. Any ceiling produces an incomplete report.
The storage stop reserves eight response caps plus 1 MiB before each page for parsed/projection
amplification and final reporting; actual retained bytes are measured, not assumed from raw
bytes. Housekeeping/report verification may extend beyond the request-admission deadline.
No chunk deletion or compaction is performed. Full archive equivalence remains outstanding.

`FrameBudget` is separate from the existing small diagnostic Budget. The larger CLI requires
an intact first-page cost journal and rejects synthetic cost evidence for real collection.
Historical cost bytes/hashes are referenced without promoting or reinterpreting the original
journal under the new build. Source and panel code for the new attempt are frozen independently.

Frame manifest schema v2 keeps per-page hashes and summaries instead of copying every row
into the final report. A streaming verifier reads one full page at a time, retaining only
small identity/conflict indexes and ordered page references. Original raw/generic/frame page
projections remain intact. This bounds memory and final-report size as page count grows.
Run only after tests and the code/protocol commit. Report observed coverage, stop reason,
latency, disk/memory and exclusions before deciding subsequent collection or sampling.

### Attempt 1 result and revised finite attempt

Attempt 1 (`f66dea1`, journal `fs2_capture_95cbb8cdd4334bc1836249e7d7864473`) stopped exactly
at its frozen 256 MiB raw ceiling: 410 attempts, 409 complete pages / 40,900 market rows,
44 unresolved identities, no observed duplicate/conflicting identities. Page 410 is truncated
and retained. No terminal was reached; **incomplete**, never a representative frame. Actual
retained bytes 654,055,783; process peak resident memory 202,407,936 bytes; complete command
elapsed 109,404,831,458 ns. See `PHASE_03_ENUMERATION_ATTEMPT_1.json`.

Before a second fresh attempt, keep the population/parser/eligibility unchanged and revise
only the finite raw/retained stopping ceilings to **1 GiB raw and 3 GiB retained**. Keep
1,000 requests, 100 rows/page, 4 MiB/page, 15s/request, 900s admission, and 2 GiB free reserve.
Require the observed 256 MiB attempt as additional cost evidence in the second run's policy.
Its average retained/raw ratio was about 2.44 and the observed memory footprint is manageable.
The run constructor checks capacity for both the complete new retained budget and free reserve.
These observations support a finite attempt within current local capacity, not a guaranteed
population size or completeness. Retain both previous journals exactly, and restart from the
first cursor to avoid calling an unregistered extension of attempt 1 complete. No outcomes or
model results informed this capacity choice. If the 100,000-row ceiling is insufficient,
preserve the failure and revisit the sampling/reader capacity contract before further runs.
