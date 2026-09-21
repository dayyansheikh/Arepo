# Phase 3 next finite frame capacity — implementation contract

Status: D036 bounds and original-decoder capacity gate implemented; validated (**766 tests passed**),
third attempt completed **incomplete on a response timeout**. All prior attempts remain incomplete. Read checkpoint,
phase/frame/panel contracts and D034–D035 before implementation. No scientific threshold or
population definition changes are proposed. This is the exact next engineering milestone.

## Evidence and scope

Actual Gamma scope exceeds 100,000 returned rows. Attempt 2 used 645 MB raw, 1.58 GB retained,
343 MB peak resident and about 196 seconds for enumeration. D034 verified the complete original
journal under its original build without recollection. D035 permits an explicitly declared
400,000-member pure plan; the single-stratum synthetic measurement used 323 MB /29.3 seconds.
These are bounded observations, not guarantees about remaining Gamma pages or metadata tails.

Keep all `closed=false` source rows; do not narrow dates/categories/liquidity, merge incomplete
prefixes, change source identity semantics or turn source groups into independent events.
Continue to retain unknown/excluded identities and all raw numerical/source facts. No models,
origins, production database, scheduler or retention changes belong in this milestone.

## Ordered tasks

1. Reload actual tests/code and verify current local memory/free disk. The prior machine had
   8 GiB RAM and about 16 GB free disk. Check capacity again; do not assume it is unchanged.
2. Implement an explicit larger `FrameBudget`/CLI mode for at most 4,000 sequential requests,
   100 rows/page, 4 MiB/page, 3 GiB raw total, 15s/request, 900s request-admission window,
   8 GiB retained stop and 2 GiB free reserve. These are proposed future ceilings, not active
   collection authority from this document alone. They fit the previous disk measurement but
   need fresh preflight; fail without creating a run if the full reserve is unavailable.
3. Require verified first-page evidence AND the preserved request-ceiling attempt as cost
   lineage before exceeding existing 1,000-request /1 GiB raw /3 GiB retained maxima. Distinguish
   prior byte-ceiling proof from prior request-ceiling proof. Verify all referenced raw bytes,
   receipts/page/report hashes, original policy/scope and actual stop condition; synthetic
   evidence must never authorize live collection. Do not weaken original build admission.
4. Preserve existing small diagnostic/default limits. Freeze larger ceilings explicitly in a
   fresh policy. No hidden retries, old-run extension, budget changes during a run or current
   parser substitution for old facts. Streaming page verification continues; report-size and
   identity-index costs must remain bounded within the actual machine. Housekeeping time is
   separate from admission time. Avoid overlapping capacity measurement with regression tests.
5. Add fault tests for missing/wrong/truncated capacity proof, synthetic/live mismatch,
   raw/request stop distinction, over-max ceilings, free-space refusal and original-journal
   immutability. Run targeted/full isolated checks, self-review, update D036 and commit before
   collection. Existing 755-test result is historical, not validation of those future changes.
6. If preflight and tests pass, run exactly one fresh finite attempt. Preserve its own root,
   implementation hash, source interval, original report/ack and bytes/memory/latency metrics.
   A continuing cursor at any ceiling is still incomplete. Never relabel or delete any prior
   attempt. If safe capacity cannot reach a complete frame, document required data/capacity
   and stop; no paid infrastructure or deletion as an automatic workaround.
7. Inspect complete exhaustion, conflicts and unresolved mapping counts. A complete interval
   enumeration is not an atomic population snapshot. Refine/pin freshness and coverage
   interpretation before seed/sample use. Then implement durable protocol/seed/sample/actual
   read/computation/origin journals per `PHASE_03_PANEL_JOURNAL_CONTRACT.md`, followed by bounded
   collectors/targets and the predeclared prospective pilot. No Phase 4 transition yet.

## Acceptance and output

New bounds are explicit, tested and frozen before requests. Original attempts remain byte-for-
byte intact and retain original status. The new result truthfully reports exhaustion or the
exact incomplete stop; no caller-supplied completeness or synthetic evidence admits a panel.
Update checkpoint/review/master and draft #16. Commit the measurement evidence separately from
its predeclared code/protocol. Phase 3 acceptance still requires the full prospective pilot.

## Implementation review before new collection

`FrameBudget` supports the explicit finite maxima while keeping existing defaults. CLI
`enumerate --request-capacity-journal <root> --request-capacity-commit <full-sha>` selects
only the separately planned larger mode. These flags are paired and mutually exclusive with
the earlier byte-ceiling mode. The constructor verifies prior evidence with the D034 original
reader, preserving an actual new read journal. Source/scope, nonterminal request stop, full
page count, raw bytes, original policy/report lineage and live provenance are checked before
new requests. Insufficient disk or missing/invalid proof refuses without creating a new
capture run. Original evidence is never extended or overwritten.

Self-review covers old defaults, every expanded ceiling, unsupported argument combinations,
synthetic/live separation, corruption, original-code availability, byte-versus-request stop,
source scope, free-space checks and complete-frame misclassification. New capacity tests use
real isolated original-code child decoders with synthetic HTTP; no production or network
requests. Full regression results and safe code commit must be recorded before collection.

Local preflight at this revision: 14711009280 free bytes; 8,589,934,592 bytes RAM.
Required disk capacity for the proposed run: 10,737,418,240 bytes. Runtime rechecks it.

Final precollection regression: **766 passed**, zero skipped, 91.45s, isolated PostgreSQL included.
Full Ruff, canonical checker and whitespace checks pass. Existing Starlette/httpx warning only.

## Actual attempt and data gate

Third attempt under `5cdb2d2`, journal `fs2_capture_ff7f05b057b647109b4239ca781e10fb`,
retained 73 complete pages /7,300 rows, then a partial HTTP 200 response timed out at 15s.
The failed 74th attempt retained 604,209 raw bytes; no retry was part of this frozen protocol.
Whole run: 46,929,025 raw bytes, 112,224,334 retained bytes and 118,849,536 peak resident bytes.
The original-code capacity proof succeeded; the new failure is response availability, not a
mislabelled success or evidence that the memory/storage ceiling was reached. Source terminal
was not observed. 7,256 row identities eligible, 44 unresolved; no observed identity conflicts
in the prefix. See `PHASE_03_ENUMERATION_ATTEMPT_3.json` for exact hashes/clocks/costs.

**BLOCKED — REQUIRED DATA UNAVAILABLE:** no complete sampling frame has been obtained under
any frozen attempt. This single timeout does not prove a persistent venue outage. Current
productive collection/implementation stops at this checkpoint under the user's data gate.
No protected approval is requested. All code/test/review gates for D036 passed; Phase 3 did not.

Safe alternatives inspected: old prefixes remain incomplete; original-code rereading verifies
what exists but cannot supply missing pages; synthetic capacity does not replace real evidence;
CLOB compact/sampling endpoints have no established equivalent population; dropping categories,
dates, raw fields or controls would not solve the stated requirement. The current HTTP capture
creates a client per request; connection reuse and bounded, separately declared retry lineage
are possible future engineering work, not demonstrated fixes. No new transport or deadline was
substituted during this run. No unbounded retries, partial-frame sampling or production changes.

A later continuation must inspect this completed result, confirm source/access conditions and
refine/test/freeze any resilience protocol before another enumeration. Do not automatically
repeat the same failed full run, extend an old journal or loosen its clocks/timeout retrospectively.
If the required data remains unavailable and no evidenced safe path exists, leave the blocker
unchanged and stay quiet. Only an actually verified complete frame can open the panel milestone.

## User-directed continuation: bounded retry protocol D037

The user explicitly requested continued engineering after the data checkpoint. The failure
began receiving bytes after about 0.63s but stalled mid-body; the preserved JSON is incomplete.
This is evidence for a bounded transport retry, not parser loosening. Implement manifest v3
with `FrameRetryPolicy` and explicit CLI `--bounded-retries`. The default stays no-retry.

Freeze one retry per cursor, eight total and one-second backoff. Qualifying errors are
TimeoutError/ReadTimeout/ReadError/RemoteProtocolError/ConnectTimeout/ConnectError (only with
no status or a 2xx status), or HTTP502/503/504. All other errors stop, including HTTP429,
permission denials, invalid schemas, cursor cycles, partial byte caps and cancellation.
Retry requests repeat exactly the failed scope/cursor and link to its capture ID; the source
cursor parent remains the last successful page. Every attempt consumes the original global
limits. A successful retry advances pagination once; a second failure at that cursor stops.

The v3 final report retains all errors, failed bytes and attempt clocks and separately records
retry count, recovered failures and unrecovered errors. Source exhaustion can be reported only
if the complete successful cursor chain terminates and every transient failure has its
verified same-cursor recovery. Such a frame is still an interval enumeration, not an atomic
snapshot or model-ready sample. Old attempts remain incomplete, read under their old builds.

Test partial first/later-page failures, exact cursor/parent linkage, retry exhaustion, global
retry and request caps, denied/rate-limited/schema responses, default no-retry behavior, retry
lineage tampering and fixed backoff. Run regression and self-review; commit this protocol
before any new attempt. A fourth finite run, if made, keeps D036's capacity/deadline bounds
and adds only this predeclared retry policy; do not promise completion at today's latency.
Connection pooling is a separate possible transport change and is not implemented here.
