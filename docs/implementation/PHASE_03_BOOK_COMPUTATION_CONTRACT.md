# Phase 3 — snapshot primitive computation (D057)

Status: implemented and tested; 150 affected checks plus 20 compact-storage checks passed. This is the first scoped numerical milestone of
PHASE_03_FEATURE_WINDOWS_NEXT.md. It supplies F08/F09 snapshot components, not dense-window
features, model-ready origins, a live panel or predictive evidence.

## Frozen numerical scope

Use existing receipt/identity/lifecycle validation over at most ten source observations and
4 MiB of raw input. Preserve every source inventory entry. Retain all source-ordered book
levels up to 10,000 per book, including zero levels and original strings, native timestamp
and hash without interpreting their clock semantics. Never truncate an oversized book: report
numerical_budget_exceeded and retain its raw source reference. Quote quality remains separate.
Arithmetic operands permit at most 256 coefficient digits and absolute exponent 256 before
Fraction expansion. Larger exact source values remain preserved, with components unavailable.
These are engineering bounds, not market-universe eligibility or empirical thresholds.

Keep exact reduced integer numerator/denominator for each result and its formula intermediates.
A terminating decimal is encoded exactly; a repeating decimal is null with an explicit reason.
Preserve raw precision/trailing zeroes separately. F08 = size difference / total best size;
F09 = size-weighted microprice minus midpoint. Retain their algebraic dependence. Source-local
price/share/notional units do not establish collateral identity. Unknown native age and tick
remain null, not receipt-age substitutes. Invalid/stale/closed books supply no zero fallback.

## Actual computation and preservation

`record_book_computation` accepts only a sealed source-run directory, new output directory
and explicit QuoteInputPolicy. Freeze build, policy and storage limits before a new compact
input-read journal. Reuse the verified source reader and its consumption hash checks. Record
actual computation start/end and post-fsync availability. A pure projector output or supplied
clock cannot bypass this boundary. Preserve synthetic versus source prospective provenance;
neither grants feature-store/origin admission.

Output prefix `fs2_book_computation_`, schema `fs2-book-computation-v1`; child
`fs2_input_read_source` uses unchanged compact-v1 (4 MiB total /2 MiB artefact). Reserve a
16 MiB whole computation, 4 MiB per artefact, 64 KiB failure allowance and 2 GiB free disk.
Reuse the existing finite-depth/file-count/time accounting with explicit new limits. Processing
limit is 180 seconds at checked boundaries; it is not a hard process kill. Keep old quote and
origin schemas/APIs unchanged. Concurrent ownership has one winner; failed attempts remain
terminal and retain partial bytes. Independent reads verify complete source/child closure,
all policy/build hashes and chronology, and recompute at the original cutoff without restamping.

Extend the allowlisted original-Git decoder for this new journal kind. Pin exact facts and
summary, execute its original full reader, issue a new read receipt and leave all original
values/clocks intact. Output cannot be nested inside the computation or source evidence.
No dependency installation, current-parser fallback or production access.

## Acceptance and handoff

Test exact rational/decimal values and extreme bounds; raw ordering/zero preservation;
causal identity/lifecycle/freshness; source errors; input mutation; actual chronology;
source rebinding/tampering; false admission; missing acknowledgements; cancellation/concurrent
ownership; storage/time/path bounds; old-build recovery; and semantic corruption with resealed
hashes. Run affected quote/input/original-reader regressions, Ruff/canonical/whitespace checks,
review and commit. Do not repeat the unchanged 1,202-test base solely for documentation.

Next: integrate this computation only through a new bounded origin protocol/reservation, and
build separately versioned dense windows and measured control assessments. All Phase 3 live
pilot/family requirements remain; no migrations, production changes, deletion or trading.
