# Phase 3 — numerical feature and window integration

Status: next implementation contract, not implemented or validated. D056 synthetic runtime
supplies scheduling and replay; it does not supply the feature families below. Phase 3 remains
incomplete. Reload the checkpoint, phase plan, canonical storage/clock contracts and actual
source readers before implementation. No live collection is enabled by this document.

## Research and current implementation

The immutable research register defines F01/F02/F08/F09/F10/F27 and the corresponding H
cards as candidates. The canonical contract requires explicit side/sign/zero conventions
before implementation. `source_parsers.clob_book` retains every source-ordered exact level;
`quote_inputs` currently projects a best quote only. A bounded Data API response preserves
rows and pagination, with unknown fill identity and window coverage. `BookReplay` always
reports continuous sequence as unproven. `stream_probe` is a diagnostic capped at five frames
and ten seconds, not a dense panel collector. Existing successful source requests cannot
waive these limits.

The next milestone should expose preserved snapshot arithmetic and its actual computation
boundary. Then add dense-window evidence and durable trigger assessments. Do not postpone
all numerical work until a large collector exists, or call sparse diagnostic values the
registered continuous-window features.

## Ordered implementation

1. Add a separate versioned pure snapshot primitive projector, preserving existing quote
   schemas. Consume the bounded source observations and `QuoteInputPolicy`; reuse the exact
   identity, receipt freshness and lifecycle checks. Retain every observation, including
   failed/stale/crossed/one-sided/duplicate-level states, without zero substitution.
2. For each valid receipt-time snapshot preserve source-order levels, raw price/size strings,
   exact prices/sizes, level notional, best bid/ask and sizes, midpoint and spread. Compute
   the F08 arithmetic `(bid_size-ask_size)/(bid_size+ask_size)` and the F09 arithmetic
   `(ask*bid_size+bid*ask_size)/(bid_size+ask_size)-midpoint`. Mark these as snapshot
   candidate components; native venue age, tick evidence and continuous history remain
   separately unknown. A receipt age is not a venue-update age.
3. Use exact rational arithmetic for derived ratios. Store exact numerator/denominator and
   an exact decimal only when terminating; otherwise the decimal is null with explicit
   `nonterminating_decimal`. Preserve original decimal strings independently. Bounds must
   reject oversized coefficient/exponent expansion before allocation; raw journals remain
   intact. No binary-float or default Decimal-context rounding. Units are source-local
   price-per-share, shares and their product; do not invent a collateral currency.
4. Add a dedicated durable computation over a verified source/input-read journal, with
   policy/build/quotas frozen before reads, actual read/compute/save clocks, full source
   closure and independent original-cutoff replay. It must not accept caller-computed
   values or clocks as prospective authority. Keep the existing quote writer and origin
   records unchanged; integrate the new computation into a new origin version only after
   its own tests and reservation review. Schema changes are local/additive only.
5. Specify and implement a finite dense-window capture independently of this snapshot
   projector. Record the prewindow snapshot, every received delta/trade/heartbeat/control
   event, actual receipt/durability, sequence evidence, disconnects, invalidation, partial
   bytes and a postwindow reconciliation. Predeclare a fixed source/request/message/byte/
   time budget, source scope and selected identities. Preserve all scheduled/control/outcome
   reservations. Gaps or unproven ordering must produce unavailable features, never repaired
   historical continuity. Runtime source/rights verification precedes live admission.
6. Implement each family against that window's measured prerequisites in the table below.
   Retain exact intermediates and every unavailable state. Freeze the feature version and
   window before gathering its inputs. Do not tune signs, spans or thresholds on outcomes.
7. Build durable measured trigger assessments from verified causal computations; only fresh
   measured negatives may enter D042 control sampling. Unknown markets remain in the
   scheduled frame. Freeze sampling/trigger policy before assessment values, preserve
   control shortages and use exact inclusion probabilities.
8. Only after integration tests, self-review, commits and a refreshed capacity preflight,
   freeze a finite development pilot's timing/control/family/target gates. Old diagnostic
   captures and synthetic runs cannot satisfy that pilot. Report failed gates unchanged.

## Family gates

| Family | Numerical evidence and eligibility | Required abstention |
|---|---|---|
| Price/context and books | Causal identity, actual source reads, exact levels/quote, receipt ages, nullable tick/native age, preceding prices when a return is requested | Invalid/stale/one-sided/crossed/duplicate identity or levels; no invented previous price |
| Raw trades and F01 flow | All original rows, explicit taker side convention, pagination/window boundaries, duplicate/overlap and fill-identity evidence | A bounded page is not complete-window flow; repeated row or transaction hash is not a unique fill |
| F02 depth-normalised flow | Signed notional paired with verified **pre-trade** executable same-side depth within the registered 0.01 price band; resolve side convention in fixtures before capture | Post-trade depth, missing fill/order clocks, gaps, unknown currency or zero denominator; no mechanical-impact proxy presented as independent information |
| F27 persistent imbalance | Registered 60-second window with covered durations, native/update ages and complete ordered evidence; preserve instantaneous and time-weighted numerator/denominator | Unproven sequence, stale unchanged states, receipt batching or zero instantaneous denominator; no persistence from repeated polls alone |
| F10 withdrawal/resiliency | Exact previous/current bid and ask depth, full delta lineage, executions reconciled separately; lock the research sign and denominator before capture | Snapshot differences cannot distinguish cancellation, execution and unobserved replacement; retain ambiguity |
| Related markets | Causal versioned relation/rules mapping, separately clocked prices, full required outcome set, explicit lag/alignment | Gamma event ID is not proof of economic independence or exhaustiveness; no future mapping or carried missing prices |
| Selected external information | Documented public source scope/rights and measured receipt/parse availability, market/rule relevance, revisions and original numeric units | Diagnostic Coinbase/news records are not automatically admitted panel inputs; no publication-time backdating |

## Required tests and acceptance

Snapshot arithmetic: unequal sizes, unsorted/source-ordered levels, zero levels, locked and
crossed books, duplicate prices, one side absent, stale receipt/identity, lifecycle unknown,
changed token/condition, exact small decimals and extreme numeric bounds. Include an F08
ratio of 1/3 and the algebraic identity `F09 = spread * F08 / 2`; this checks related
components without claiming they are independent signals. Preserve failed sources and exact
lineage/units; recomputation cannot alter original clocks/provenance.

Durable computation: policy precedes reads, input/build changes rejected, precise size/time
ceilings, cancellation/crash partial retention, no duplicate ownership/overwrite, immutable
replay and original-build read after code changes. A late calculation cannot enter an earlier
origin. Use synthetic fixtures and isolated local databases; no production startup paths.

Dense windows: disconnect/reconnect, out-of-order and rejected messages, incomplete trade
pages, changed identities, zero denominators, pre/post-trade confusion, boundary updates,
future inputs, elapsed-duration versus update-count weighting, and exact cold round trips.
Bound resource use before adding work to the runtime. Snapshot tests alone do not pass these
window gates.

Each scoped milestone needs proportionate regression, self-review, docs, coherent commit and
draft PR update. The full Phase 3 exit requires measured representative controls and causal
pilot outcomes with honest family coverage; Phase 4 remains gated. No schema migration,
production scheduling, data deletion, model fitting or product redesign is authorized here.

## D057 progress — 2026-09-24

Snapshot tasks 1–4 are implemented and tested under PHASE_03_BOOK_COMPUTATION_CONTRACT.md,
including exact original-build recovery. No old origin format or reservation was expanded.
Next execute task 5 using PHASE_03_DENSE_WINDOW_NEXT.md, then measured family/control integration.
