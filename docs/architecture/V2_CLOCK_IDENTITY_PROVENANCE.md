# v2 clocks, identities, missingness and provenance

Normative companion to [Feature Store contract](FEATURE_STORE_V2_CONTRACT.md), version `arepo-fs-v2.0`.

Phase 2's bounded source-journal implementation is refined by
[prospective source admission](V2_PROSPECTIVE_SOURCE_ADMISSION.md). Primary fact durability,
later SQL index visibility and actual model read/computation are separate clocks. The
source-only path does not admit arbitrary historical diagnostics or derived model outputs.

## Clock envelope

| Clock | Meaning | Unknown/precision rule |
|---|---|---|
| source_event_at | Event time asserted by venue/publisher | Null if absent; raw timestamp, unit, timezone and native precision retained. No collector fallback. |
| source_published_at | Publication time asserted by publisher | Can precede actual availability or be revised. Never establishes AREPO receipt. |
| first_available_at | Independently evidenced first public availability | Nullable; evidence IDs and uncertainty required. Printed article dates alone insufficient. |
| first_received_at | First receipt by this AREPO collector | Prospective ingest stamps once before parsing; retry preserves it. Monotonic counter/ns tied to process/connection session. |
| ingested_at / recorded_at | Durable ingestion/version time | Actual persistence, never backdated to venue time. Multi-transaction raw capture then parsed record is allowed; each stage immutable. |
| parsed_at | Parsing completion | Failure/null records cannot be eligible model inputs. |
| available_to_model_at | When all needed source records and computation were usable | Max of receipt, parse completion, durable availability required by the pipeline and every dependency's availability. |
| feature_cutoff_at | Latest permissible dependency time | Frozen at origin, not recalculated from future records. |
| prediction_origin_at | Actual decision origin | Scheduled cadence is a separate label. |
| generated_at / prediction_persisted_at | Model completion / durable output | Record actual latency; both precede future outcome admission and fixed-horizon target. |
| target_at | Intended horizon or registered event target | Fixed horizon = origin + horizon, not scheduled boundary. |
| label_observed_at | Actual quote/event time using locked clock basis | Keep actual delay; do not conflate with receipt. |
| label_available_at | Completion of all required facts and label calculation | Training uses only labels available by the training cutoff, including revisions. |

As-of invariant: every dependency's `available_to_model_at <= feature_cutoff_at <= prediction_origin_at`. Clock uncertainty is nullable decimal milliseconds, not default zero. Overlapping uncertainty intervals mean ordering is uncertain; exclude from tests requiring strict ordering or use explicitly labelled receipt-time analysis. Monotonic clocks only order observations within a clock session. Clock regression, timezone ambiguity, future source times and reconnect gaps are quality flags. Interpolate neither receipt time nor venue time across a gap.

Historical source data retrieved now is `reconstructed`, even if it carries a convincing old event time. Parsing old observations now does not make the derived feature prospectively available then. A test harness may inject a clock solely with `synthetic` provenance. No wall-clock overrides for live backdating.

Legacy specifics: `research_tracking.quote_from_book` writes `source_timestamp=utcnow()`; store its original value with `collector_time` semantics. `normalize_book` can replace missing/invalid native times with now; without original payload, distinguishability is lost. `collect_due_forward` captures `now` before batch network fetches, so even `observed_at` is not a verified per-response receipt. `freeze_cohort_from_scan` defaults the origin to scan start although enrichment finishes later. Existing frozen data must stay intact; v2 admission must validate each dependency's actual availability rather than inherit a v1 prospective label. Record these as legacy limitations, not silent repairs.

## Identity and two grouping views

- Market: `(venue, native market_id)`; title/slug never a key.
- Condition: `(chain_id, condition_id)`; oracle question ID separately sourced. Unknown chain/collateral cannot be filled from today's defaults for old records.
- Asset: `(chain_id, token_contract, token_id)`; retain uint256 token text losslessly. A source-local token can be recorded unresolved until chain/contract evidence exists.
- Outcome: native array index and label in the market version; preserve ordering. Do not manufacture complementary probabilities or exhaustive baskets.
- Gamma event ID: source grouping only. Economic group: a versioned graph of common causes, nested thresholds, exclusions and recurring events.
- Mapping versions retain effective-world intervals and when AREPO knew the evidence. An as-of query first selects records known by cutoff, then evaluates effective interval. Later supersession cannot disappear an earlier as-known mapping.
- Conservative evaluation groups may use reconstructed later evidence solely to avoid leakage/dependence in evaluation. They cannot become historical model features. Changed graphs require new split manifests and reruns, preserving prior reports.
- Unknown grouping stays explicitly unresolved. Sensitivity analyses cluster more conservatively by category/time where justified; assigning each unknown market its own UUID is not evidence of independence.

## Missingness and provenance

Required vocabulary: `observed`, `not_supported`, `not_requested`, `permission_denied`, `rate_limited`, `source_error`, `transport_gap`, `not_yet_available`, `history_truncated`, `stale`, `invalid`, `identity_unresolved`, `not_applicable`, `censored_by_close`, `censored_by_window_end`, `deleted_by_source`, `unknown_legacy`.

`observed` requires a valid typed value or explicitly evidenced empty collection, with coverage. Measured zero is a value. A zero denominator is retained; undefined derived ratio is null/invalid with `zero_denominator` quality flag. A stale value can remain in the raw observation, but eligible feature value is null/stale unless that definition explicitly models staleness. Missing features are never silently imputed at collection; later model imputation is training-only, versioned and keeps original missingness.

Quality flags are separate: one_sided_book, crossed_book, incomplete_pages, duplicate, revision, transport_gap, source_clock_unknown, timestamp_precision, units_conflict, metadata_stale, chain_reorg, aggressor_uncertain, zero_denominator, clock_regression, quality_not_checked. Empty flags mean 'checked and no detected issues' only with checked assessment state. Reconstruction status: complete/gap/stale/invalid. Label state: pending/unavailable/unchanged/closed/evaluated/invalid. An unobserved outcome is not flat; a closed market is not automatically a resolved market.

Provenance classes: prospective (actual captured chronology passes), reconstructed (later reconstruction with its limitations), synthetic (fixtures/simulation only), legacy_unverified (preserved historic values without v2 proof). Retain original provenance in `legacy_reference`; never overwrite the v1 source label. Provenance cannot improve merely through copying or recomputation. A derived record inherits the weakest relevant dependency status, plus its actual computation availability. Permanent registered dependency closure includes unsuccessful/abstained candidates and controls.

All substantive corrections append, including mapping, source revisions, label updates, settlement reversions and protocol changes. Content hashes pin the old state. Physical mutable caches must be reproducible from append-only records and never serve as research authority.
