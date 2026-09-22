# Phase 3 next milestone — durable quote computation

Status: D045 implemented and locally tested (952 backend tests); no live computation
measurement or prospective panel validation claimed. Prerequisites: D043 verified
actual source reads and D044 pure quote/identity projection. This is an internal Phase 3
milestone, not a completed research panel or a Phase 4 baseline.

## Objective and boundary

Record the actual computation and durable availability of exact quote inputs. D043 proves
an actual input read, while D044 validates a supplied projection at a supplied cutoff. A
new writer must connect them without accepting caller rows, timestamps, results, provenance
or origin flags. No SQL, application startup, production scheduler or network collection.
No research origin or feature-store admission until the full sampling/identity/feature
closure and the actual origin writer are implemented and tested.

## Ordered implementation

1. Reload checkpoint, master, current phase, panel contract, source admission contract and
   actual code/tests. Confirm a clean relevant working tree and no active measurement.
2. Add a dedicated `quote_computation.py` journal under a fresh canonical
   `fs2_quote_computation_*` output. It must be disjoint from the source root and ancestors.
   Preserve unrelated files and every failed/torn run. Never resume or overwrite.
3. Freeze policy/build/source-root and explicit finite quote/identity receipt-age bounds
   before any numerical source read. No automatically chosen scientific thresholds.
   Bind the D044 policy hash and the primary-journal authority, not an index visibility claim.
4. Invoke D043 `record_input_read` into a fresh child journal under this output. Include
   its entire storage/time cost in the parent budget. The source must be a completed bounded
   current-build SourceRun; no diagnostic promotion, old-code fallback or hidden capture subset.
5. After D043 verification, record a new actual computation start. Read the exact sealed
   `read_facts` projection, checking its hash and acknowledgement as actually consumed.
   D043 read availability must precede this computation start in UTC and, where comparable,
   monotonic time. Apply D044 at that actual start as the cutoff; do not backdate to source
   receipt or an intended scheduled boundary. All rows/failures remain in its inventory.
6. Record completion; persist the complete projection and bind source/input-read hashes,
   policy/build, actual start/end and a fresh post-fsync acknowledgement. Freshness at
   computation start is distinct from future origin admission; a slow computation may
   require an origin abstention even when its input projection was initially fresh.
7. Re-verify the source and input-read closure and replay D044 at the original recorded
   cutoff. Compare canonical bytes, not rounded values. Append/changed raw/parse/source
   facts or any failed child/parent marker make this v1 computation ineligible. Keep all
   evidence and a bounded failure receipt; no retry that changes old timestamps.
8. Return a compact summary containing immutable hashes, clocks, quote-state counts and
   unchanged source provenance. Never print raw payloads, wallet fields or credentials.
9. Self-review, local tests, full isolated regression, docs, coherent commit and draft PR
   before any actual bounded public-read measurement is proposed or performed.

## Resource design to freeze before implementation

D043 already limits one source run to 10 responses /4 MiB raw, each read artefact to 16 MiB,
and retained read output to 32 MiB, with 2 GiB free reserve. The parent must account for the
child's upper bound plus its own policy/projection/ack/failure artefacts **before starting**.
Choose and test a finite total parent budget; do not count only top-level files or double
spend the reserve. Time checks must cover child verification and final replay. A deadline
checked at operation boundaries is not a hard process cancellation guarantee; state that
limit accurately. No disk-history deletion or reduced market discovery is authorized.

D045 implementation refinement: freeze 64 MiB total recursive retained output (including
the child's 32 MiB allowance), 16 MiB per artefact, 180 seconds checked at operation
boundaries including initial child read and final replay, and 2 GiB free reserve. Reserve
64 KiB for failure evidence. Preflight the whole parent bound plus reserve; recheck the
child's full allowance before calling it. Only the named immediate child input-read
journal is allowed, with no symlinks or deeper directories. The successful parent closure
is policy/facts with both acknowledgements and exactly that child. Old source/child
timestamps are never reused as computation clocks.

## Tests and acceptance

- Streamed synthetic Gamma then book SourceRun through D043 and the new writer: exact
  numbers, source-local identity, input availability <= actual computation <= durability.
- Failed Gamma/book responses retained; unknown, conflicting, late-known or stale mappings
  abstain; synthetic stays synthetic and mixed provenance cannot be promoted.
- Pre-policy reads, injected old/future clocks, same-session monotonic regression, changed
  code, source append, hash corruption, partial writes/acks and child failure all refuse.
- Parent/child/transitive source path protection, concurrent exclusive output collision,
  total recursive byte accounting, free-space/time refusal and preserved partial evidence.
- Deterministic replay uses the original cutoff, does not reevaluate old freshness at
  today's time, and leaves source and computation bytes unchanged.
- No caller payload/provenance/subset/clock override, SQL connection, settings import or
  network request. No accepted origin or feature-store row from this milestone.

## Following integration, still unimplemented

Fresh broad-frame protocol and identity refresh, durable trigger computation (D042's
evidence hashes must resolve to verified records), conditional/two-stage weights, matched
controls, actual origin freeze, due outcome collection, leases, coverage and accepted pilot.
Existing D040 assignments stay historical development evidence. Gamma's explicit category
field is absent across the measured mapped frame; no invented taxonomy. D046 adds an explicit selected-market SourceRun policy under
PHASE_03_IDENTITY_REFRESH_CONTRACT.md. Default active/open list semantics stay unchanged.
Targeted runtime verification and full panel identity integration remain separate gates.
