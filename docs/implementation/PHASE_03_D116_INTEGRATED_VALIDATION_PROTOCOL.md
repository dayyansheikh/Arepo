# D116 — single integrated live prospective validation of the final Phase 3 code

Status: DRAFT — NOT FROZEN. Requires an accepting `science-reviewer` pass, then commit of this
protocol, its script and its evaluator (hashes recorded) before any request. No source request,
pilot run or network access has been made in drafting this document.

Revision 2 (this text) answers an independent review that returned REVISE with seven findings:
(1) engineering timing/defect states could masquerade as data availability; (2) outcome classes
were not exhaustive; (3) several field names and states were not the real ones; (4) the clock
budget was presented as a bound; (5) the 4x2 fill probability was over-read; (6) the sufficiency
floor was too weak; (7) the panel name carried a placeholder. Each is resolved below (sections
2, 4, 5, 7, 10). The acceptance logic is implemented as code, not prose:
`backend/astrolabe/research_panel/d116_evaluator.py` (version `d116-evaluator-v1`), with the
command-line entry `backend/scripts/evaluate_d116.py` and tests
`backend/tests/unit/test_research_panel_d116_evaluator.py`. **At freeze the evaluator's commit
hash and the sha256 of each of those three files are recorded next to the script hash; the
evaluator and the classification table are never edited after the first D116 request.** The
evaluator also reports the sha256 of its classification table (`classification_table_sha256`).

## 1. Purpose and non-claims

D115 withdrew the 2026-10-10 Phase 3 closeout; Phase 3 stays PROVISIONAL. D116 is the one
integrated live prospective validation of the FINAL Phase 3 code: HEAD must contain `8afbdff`
(600 s screening ceiling, owned screening schema `fs2-screening-owned-selection-v4`). It runs the
whole path once on real data: complete Gamma discovery, exact sampling, screening, selected-market
observation, pre-origin histories, trigger/control assessment, origins (feature freeze), future
targets and the terminal original-code audit.

It validates machinery, not predictive performance. Non-claims: no prediction, calibration,
prevalence, alpha, profitability or independent-sample claim. Roles overlap markets and are not
independent samples. No Phase 4 modelling is authorised by this protocol or its outcome.

D082/D085/D086/D088/D089/D094/D097/D110/D114 keep their original outcomes. Nothing here redraws,
relabels, pools, backfills or reinterprets them; their frames, samples and failed gates are
untouched, and D116 results are never combined with them.

## 2. Design: identical to D114 except sampling shape

Same code path, transport (`accept_gzip=True`, `reuse_connections=True`), frame budget, windows,
screening, runtime and audit as D114. Differences, and only these:

- Sampling: 4 strata x 2 members. In code: `PanelProtocol(scheduled_per_stratum=2,
  triggered_per_stratum=2)` and `declare_panel(..., strata_limit=4, ...)` (D097's exact arguments;
  D114 used 4 per stratum and `strata_limit=2`). Slot ceilings are unchanged
  (`scheduled_slots=8`, `triggered_slots=8`, `controls_per_trigger=1`); `strata_limit x
  scheduled_per_stratum = 8` equals `scheduled_slots`.
- Population: `TEMPORAL_POPULATION = scheduled_end_after_selection_declaration_or_unknown_v1`
  (as in D097/D114): members whose stated endDate is at or before the actual selection-policy
  declaration clock are excluded with explicit zero-inclusion records; unknown/invalid dates stay
  eligible. All probabilities are conditional on this declared population. It is not a claim of
  active trading. No price/book/outcome-based eligibility.
- A fresh complete Gamma frame is collected in the same process, with a fresh pre-source seed
  generated internally after frame completion and before selection numerical reads. The D114 frame,
  seed and sample are never reused.
- Script differences are naming (fixed panel name `fs2_panel_d116_integrated_1`, no placeholder),
  the two sampling arguments, and stdout-only additions (a `panel_declared` clock print and a
  final `accounting` print). See section 10.

Justification of 4x2, and what it does not show. D114's 2x4 draw could not fill: its drawn strata
held 3 and 1 members. On D114's actual stratum-size structure (90 eligible strata: 3 of size 1, 7
of size 2, 3 of size 3, 1 of 5, 1 of 6, 2 of 7, 73 of >=10; 87 strata have >=2 members; uniform
stratum draw without replacement), P(8 distinct members selected) = 0.871 for 4x2 versus 0.731
for 2x4. This is a structural fill-probability argument made from D114's frame structure before
any D116 data exist; it uses no outcome. A future frame may differ, and underfill is possible
(reported under E2, not redrawn).

Disclosures that bound how the outcome may be read:

- 0.871 is a **fill probability only**: the chance that eight distinct members are drawn. It says
  nothing about the chance of a matched pair.
- A matched pair needs, inside one stratum of at most two sampled members, a *fresh triggered*
  member and a *fresh untriggered* member (second-stage plan: `triggered_per_stratum=2`,
  `controls_per_trigger=1`, controls drawn only from untriggered members of the same stratum), and
  then both members must complete the whole chain (section 4.3). With strata of two members this
  can fail for purely data reasons: both members triggered, both untriggered, one unavailable.
- D097 used this same 4x2 shape and obtained **zero** matched pairs. A zero-pair result for D116
  is therefore expected to be common and is not evidence of a defect.
- Consequently the split between PASS and PASS WITH LIMITATION is largely determined by the
  design and by market state on the day, not by the quality of the code. Both are legitimate
  results; neither is a claim about prediction, calibration or alpha.

## 3. Inherited policies and ceilings (unchanged, with values)

| Item | Value |
|---|---|
| Trigger rule | `SnapshotTriggerPolicy(1,3,60000)` (|imbalance| >= 1/3, source age 60000 ms) |
| Controls | 1 per trigger, from untriggered members of the same stratum |
| Screening freshness | `ScreeningPolicy(120,120)` (window age 120 s, assessment age 120 s) |
| Owned window | `OwnedWindowPolicy(10000, WindowBindingPolicy(60000,180000), WindowReconciliationPolicy(120000,120000,1000), OriginWindowPolicy(120000,60000), binding_mode='observation')` |
| Window duration | 10 s per selected token (one observer per eligible token) |
| History age / window age at read and freeze | 120 s / 60 s |
| Binding quote / identity | 60 s / 180 s |
| Origin quote age / identity age | `max_quote_age_seconds=60` / `max_identity_age_seconds=180` |
| Origin dispatch / save | `max_origin_delay_seconds=60` / `max_origin_save_seconds=5` |
| Target horizon / tolerance | 60 s / +-15 s |
| Cadence | `cadence_seconds=120`, 1 cycle, 1 target attempt |
| Frame interval | `max_frame_interval_seconds=600` |
| Frame age | `max_frame_age_seconds=3600`, measured from frame `interval_start` |
| Screening ceiling | `screening.LIMITS['max_seconds']=600` per call (declare / inputs / finish / read), including the input evidence-read deadline in `_inputs` (D115 item 2); not cumulative |
| Window computation | 180 s |
| Worker / acquisition | 7200 s / 1800 s |
| Activation | 600 s |
| Concurrency | screening/observer 8, owned runtime 4 |
| Source bounds | 64 KiB per response, 1 MiB per source run; frame budget 4000 requests, 3 GiB wire, 3 GiB decoded, 7 GiB retained |
| Frame source arguments | `limit=100`, `FrameRetryPolicy()`, same `measurement_root` / `request_capacity_root` / `request_capacity_commit` as D114 |

Nothing is tuned for D116. Values are those in the committed code at the launch HEAD; the
launch wrapper records the HEAD and the script hash, and any mismatch with this table is a
launch refusal, not an edit.

## 4. Acceptance

Per D115 item 5 (user decision, 2026-10-10), acceptance reflects the actual design and its
denominator. Genuine data-availability outcomes (unavailable or closed markets, one-sided books,
all candidates triggered, no eligible control, unavailable histories) are results, not
engineering failures. Engineering timing and defect states are failures and must never be
relabelled as data availability. Gates, the classification table and the decision rule are frozen
before any D116 data exist and are never changed afterwards. They are executed by the evaluator
(`d116_evaluator.py`, `evaluate_d116(panel_root, selection_root, worker_root, runtime_root, ...)`),
which reads only the retained artifacts, checks every pair file against its acknowledged sha256,
makes no request, and returns the per-member per-stage states and classes, E1-E9, the chain and
pair counts, the sufficiency checks and the outcome class as JSON.

### 4.1 Exhaustive state classification (predeclared)

Every state or reason the code can emit at every stage maps to exactly one class:

- `OK` the expected, non-limiting state;
- `DATA_SOURCE` the provider's data legitimately says so;
- `DATA_TRANSPORT` the provider or network did not deliver;
- `ENGINEERING` our timing, budgets or defects.

**Any state or reason that is not listed is ENGINEERING. Any ENGINEERING finding makes the outcome
FAIL**, whatever the other gates say. The authoritative table is the module constant
`CLASSIFICATION_TABLE` (currently 224 expanded rows; its sha256 is printed in each report and
recorded at freeze); the condensed form below lists every distinct state. The
`gamma.market_<r>` / `clob.book_<r>` rows (r in permission_denied, rate_limited, transport_gap,
source_error, invalid), the `snapshot_<q>` rows (q any quote state except observed, same class as
q) and the `origin_<s>` freeze reasons (same class as origin state s) are expanded in the constant.

**Discriminating citation rule.** A DATA class is honoured only if the retained raw receipts
support it; otherwise the finding is reclassified ENGINEERING (`citation_failed:<check>`). Every
DATA finding carries, per cited receipt, `status`, `transport_error`, `raw_hash` and whether the
raw bytes re-hash to `raw_hash` (receipt fields at `feature_store/capture.py:395-405`; the
provider-state mapping at `feature_store/source_run.py:285-288`). Checks, by id:

| check | requirement (all need `sha256(raw.bin) == raw_hash`) |
|---|---|
| `http_auth_denied` / `http_rate_limited` | no transport_error and status in {401,403} / == 429 |
| `transport_error` | transport_error is not null |
| `http_5xx_or_none` | no transport_error and status null or >= 500 |
| `http_invalid` | no transport_error and status < 500 and not 401/403/429 |
| `book_empty_side` | 2xx `clob.book`, parsed body has an empty bid or ask side (size > 0 levels) |
| `book_non_decimal` / `book_crossed` / `book_duplicate_price` | 2xx `clob.book` whose parsed body shows a non-decimal level / best bid > best ask or price outside [0,1] / a repeated price on one side |
| `lifecycle_closed` / `_archived` / `_not_accepting` / `_unknown` | 2xx `gamma.market`, parsed `closed` is true / `archived` is true / `active` or `acceptingOrders` is false / any lifecycle field null or absent |
| `identity_unresolved` | `gamma.market` failed, or its `clobTokenIds` lack the member token, or the book failed (mapping is null whenever the book failed) |
| `identity_conflict` | 2xx gamma `conditionId` differs from 2xx book `market` |
| `frame_mapping_citation` | cites the `compare_mapping` result (`screening.py:324-325`): `mapping_differs` needs current != frame `mapping_version` with a 2xx gamma receipt (differing field `mapping_version`); `mapping_unavailable` needs current null and a failing gamma/book receipt or unresolved token |
| `pre_identity_citation` | `owned_windows.py:92-96` compares token, condition and market IDs (it does not call `compare_mapping`): cites the differing field among `token_id`, `condition_id`, `market_id`, or a null mapping with a failing receipt |
| `pre_snapshot_citation`, `pre_lifecycle_citation` | the pre-window quote state classifies DATA through the quote-state rows against the screening receipts; the pre-window lifecycle differs from active and the gamma receipt agrees or failed |
| `origin_mapping_differs`, `target_mapping_differs` | cites the differing field(s) among token, condition, market, outcome index/label, mapping_version, or `core_identity_equal` false |
| `history_snapshot_citation`, `history_identity_citation` | the prior or current quote state classifies DATA with receipts; or prior and current `mapping_version` differ (both non-null) |
| `socket_error_event` | the terminal socket journal event carries a non-null `error` |
| `target_lifecycle_closed` | gamma lifecycle `closed` true in a target-attempt receipt |

**Common-mode guard** (applied before any INCONCLUSIVE or PASS WITH LIMITATION): if every selected
member ends without a complete chain and (a) two or more members share one limiting `(stage,
state)`, or (b) every member's limiting cause is DATA_TRANSPORT, or (c) every member has a
transport error or 4xx/5xx receipt on a market listed in the frame minutes earlier, the outcome is
FAIL pending diagnosis, never INCONCLUSIVE.

Condensed table (class; check):

| namespace | state or reason | class |
|---|---|---|
| screening state (`screening_report.states[].state`) | triggered, untriggered | OK |
| | unavailable | OK container; every reason is classified separately |
| | **not_assessed** (journal missing, `screening.py:300-303`) | ENGINEERING |
| trigger reason (`states[].reasons`, `trigger_computation.py:127-168`) | `gamma.market_*`/`clob.book_*`: transport_gap, rate_limited, permission_denied, source_error | DATA_TRANSPORT |
| | `gamma.market_invalid`, `clob.book_invalid` | DATA_SOURCE |
| | snapshot_one_sided_or_missing, snapshot_invalid_numerical, snapshot_invalid_or_crossed, snapshot_duplicate_price_level, snapshot_market_closed/archived/not_accepting_orders/lifecycle_unknown, snapshot_identity_unresolved_at_receipt, snapshot_identity_ambiguous_or_conflicting, snapshot_invalid | DATA_SOURCE |
| | snapshot_permission_denied/rate_limited/transport_gap/source_error | DATA_TRANSPORT |
| | snapshot_identity_unavailable_or_changed, known_active_lifecycle_unavailable, frame_mapping_changed_or_unavailable | DATA_SOURCE (cited) |
| | source_pair_unavailable, source_stale_at_assessment, requested_identity_differs, snapshot_unavailable, snapshot_identity_stale, snapshot_receipt_stale, snapshot_numerical_budget_exceeded | ENGINEERING |
| assessment reason (`plan.assessment_inventory[].reasons`, visible there and not in `screening.states`; `assessments.py:97-104`) | **input_window_stale, assessment_stale** | ENGINEERING |
| window pre-state (`window_NNN.json missing_reason`) | none | OK |
| | pre_snapshot_unavailable, pre_identity_differs, pre_lifecycle_unavailable | DATA_SOURCE (cited) |
| socket terminal (`socket_window_report.terminal`) | interval_ended | OK |
| | connect_error, subscription_error, receive_error, ping_error | DATA_TRANSPORT (cited event error) |
| | budget_stop, refused (provenance_mismatch, pre_binding_stale, identity_expired_before_subscription) | ENGINEERING |
| socket close state | closed (or not_connected after connect_error) | OK |
| | close_error, any other | ENGINEERING |
| origin state (runtime `origins[].state`) | observed | OK |
| | transport_gap, rate_limited, permission_denied, source_error | DATA_TRANSPORT |
| | invalid, one_sided_or_missing, invalid_numerical, invalid_or_crossed, duplicate_price_level, identity_unresolved_at_receipt, identity_ambiguous_or_conflicting, market_closed, market_archived, market_not_accepting_orders, market_lifecycle_unknown, identity_changed_since_selection | DATA_SOURCE (cited) |
| | **failed** (`origin_worker.py:317-321`), expired_before_request, expired_during_requests, **late_origin** (`:229-230`), **late_persistence** (`:238-240`, `:396-399`), **receipt_stale_at_origin, identity_stale_at_origin** (`:221-228`), identity_stale, receipt_stale, numerical_budget_exceeded | ENGINEERING |
| history reason (`pre_origin_window.history_reasons`, `origin_window.py:85-101`) | snapshot_unavailable, identity_changed_or_unavailable | DATA_SOURCE (cited) |
| | prior_quote_stale, current_quote_not_after_window, **window_stale** | ENGINEERING |
| freeze reason (`freeze_reasons`, `origin_features.py:97-108`) | the history rows; `origin_<state>` follows the origin-state row | as above |
| | **prior_quote_stale_at_freeze, window_stale_at_freeze** | ENGINEERING |
| target attempt state (`attempts[].state`) | recorded | OK |
| | origin_ineligible | OK; class follows the origin state, and is ENGINEERING if the origin was observed |
| | **incomplete_evidence** (`due_worker.py:410`), **expired** (`:319`, `:413`) | ENGINEERING |
| target outcome (`outcomes[].state`) | observed | OK |
| | closed | DATA_SOURCE (lifecycle cited) |
| | unavailable | OK container; requires a non-empty classified exclusion list (empty = ENGINEERING) |
| | origin_ineligible | follows the origin state |
| | **pending**, **incomplete_evidence** (`targets.py:121`, `due_worker.py:464-467`) | ENGINEERING |
| target exclusion reasons (`outcomes[].target.exclusions[].reason`) | quote-state rows above plus identity_changed_since_origin (DATA_SOURCE, cited) | as quote state |
| | **late**, identity_not_frozen_at_origin (`targets.py:115`, `:126`), not_yet_available, identity_unresolved, identity_not_known_at_receipt | ENGINEERING |
| failure artifacts | selection_failure, activation_failure, worker_failure, runtime_failure, origin_failure, target_failure | ENGINEERING |
| evaluator | missing or unreadable artifact, artifact hash mismatch | ENGINEERING |
| worker state | pilot_collected_unaccepted | OK |
| | blocked_role_capacity, screening_complete (not an owned pilot) | ENGINEERING |

Note that `origin_ineligible` is an outcome/attempt state, not an origin state. An origin state
other than `observed` abstains the origin only for a DATA reason; a timing or defect abstention
(`late_persistence`, `failed`, ...) is an engineering failure, not an acceptable abstention.

### 4.2 Engineering gates E1-E9 (all must pass; the evaluator's checks, with real fields)

- **E1 Discovery.** `selection/fs2_frame_read_original/original_report.json`: `state ==
  exhausted_consistent`; `interval_end - interval_start <= 600 s`; `frame_report_hash` and
  `page_manifest_hash` present and raw pages retained under `selection/pages/`; frame age
  (measured from `interval_start`) <= 3600 s at screening declaration (`screening_policy.declared_at`,
  re-check `screening.py:175-182`), at the screening cutoff (`screening.py:494-501`) and at
  activation read completion and acknowledgement (`activation.py:332`, `:352`, replay `:415-416`);
  the panel protocol equals the frozen section 3 values.
- **E2 Sampling.** `panel_policy.declared_at >= selection_report.original_frame_available_at`
  (the evaluator enforces this; the code does not); selection policy declared after the panel and
  before the selection numerical reads (`selection_report.computation_started_at`); sealed `seed`
  in `selection_plan.protocol`; for each sampled stratum the exact `stratum_inclusion_probability`,
  `conditional_market_inclusion_probability`, `market_inclusion_probability`; temporal and other
  zero-inclusion exclusions are `selection_plan.exclusions` (reason
  `scheduled_end_at_or_before_selection_declaration`, `panel_selection.py:164-166`, count
  `selection_eligible_member_count`, `:196-199`), and `selection_report.counts` (`selection.py:329`:
  `source_rows`, `eligible_row_count`, `duplicate_market_rows`, `sampling_members`) reconcile:
  `counts.sampling_members == plan.frame_size == len(exclusions) + selection_eligible_member_count`;
  `unique_selected_markets` (n) reported and equal to the screened member count; underfill below 8
  explained from the per-stratum `eligible_count`/`scheduled_count`; no `selection_failure`; no
  redraw. (The script's stdout `accounting` key that earlier drafts called `exclusions` is the
  *second-stage screening plan's* exclusion list, not the selection exclusions; it is relabelled
  `second_stage_plan_exclusions` and is not used for E2.)
- **E3 Screening.** The worker report exists with state `pilot_collected_unaccepted`; each selected
  member has a `screening_report.states[]` row (triggered, untriggered or unavailable) whose every
  reason is classified (section 4.1); `plan.assessment_inventory` shows no `input_window_stale` /
  `assessment_stale`; the finish call lasted <= 600 s.
- **E4 Observation and histories.** For every selected member `window_NNN.json` exists with
  `missing_reason` in {null, pre_snapshot_unavailable, pre_identity_differs,
  pre_lifecycle_unavailable} (also `runtime_policy.json window_inputs.members[...].missing_reason`);
  a non-null refusal is classified (it is a pre-state refusal, before any socket). Otherwise the
  socket report `terminal`/`close_state` and the terminal event are classified. The origin fact
  `runtime/origins/<intent_id>/origin_facts.json projection.pre_origin_window` carries
  `eligible_at_freeze`, `history_reasons`, `freeze_reasons`, `socket_terminal`, `socket_close_state`;
  each history is eligible or has only classified DATA reasons. No continuity is inferred from
  silence, PONGs or matching endpoints.
- **E5 Trigger and control.** Every member's screening state is triggered/untriggered/unavailable;
  each control assignment's `matched_trigger_ids` (`sampling.py:236`) equals the `trigger_id` of a
  triggered assignment (`trigger_id` is that member's assessment `evidence_id`,
  `sampling.py:215-217`) in the **same stratum**, and the control's `assessment_state` is
  `untriggered`; each stratum reports integer `triggered_pool`, `control_pool`, `controls_wanted`,
  `controls_selected` and `unfilled_control_slots == controls_wanted - controls_selected`;
  `role_capacity.fits` is true.
- **E6 Origins.** Runtime origins carry only `intent_id` (`origin_worker.py:400-403`); the member is
  resolved through `origin_intent.json slot.market_id` (the activation slot, `activation.py:267-274`,
  whose `intent_id` the evaluator recomputes from the slot identity, checked under E9). Exactly one origin result and a
  durable `origin_receipt` per selected member; an observed origin records `origin_at`; every origin
  state is classified (no ENGINEERING state); and every target intent was created after that origin's
  `plans/<intent_id>/plan_ack.json` `durable_ack`.
- **E7 Targets.** Each member's origin has the declared `target_attempts` attempt(s); attempt states
  are drawn from recorded, incomplete_evidence, origin_ineligible, expired and outcome states from
  observed, unavailable, closed, pending, incomplete_evidence, origin_ineligible
  (`targets.py:121,132,148`; `due_worker.py:464-467`). Terminal acceptable: observed, closed,
  unavailable (non-empty classified exclusions), origin_ineligible (non-observed origin with a DATA
  class). `late` and `identity_not_frozen_at_origin` are exclusion reasons (`targets.py:115`,
  `:126`) and are ENGINEERING; none may be `pending`.
- **E8 Original-code audit.** Worker `state == pilot_collected_unaccepted`; exactly one recovery
  receipt whose `original_report_hash` equals the runtime report hash and whose `original_state`
  starts `verified_`; the `fs2_runtime_read_batch/read_receipt.json` file exists. No retry.
- **E9 Accounting.** Every selected member appears exactly once at each stage (screening state,
  assessment inventory, window entry, origin result, outcome, activation selection) and has
  exactly 2 screening receipts, 3 origin receipts (observed origins) and 2 receipts per target
  attempt (observed/unavailable/closed); every cited receipt re-hashes; retained bytes <= the
  screening reservation; stage clocks are ordered across artifacts; nothing is fabricated,
  backfilled or reconstructed.

### 4.3 Exercise sufficiency

The machinery must actually be exercised on real data. Required, all of:

1. At least ONE complete chain = an observed origin with `eligible_at_freeze` true and a valid
   target (`outcomes[].state == 'observed'`).
2. At least ONE member with an authenticated `effective_state` of `triggered` or `untriggered`
   (assessment `evidence_id` present and `states[]` = `plan.assessment_inventory`).
3. The strata report shows `control_pool` and `controls_wanted` computed (integers) for every
   second-stage stratum.

A PASS pair requires **both** pair members' origins observed with eligible histories **and** valid
(observed) targets. A pair in which either member lacks any of the three is not an observed pair.

### 4.4 Outcome classes (exhaustive; first match in order FAIL, INCONCLUSIVE, PASS, PASS WITH LIMITATION)

- **FAIL** — any ENGINEERING finding (section 4.1), any failed E-gate, or a common-mode pattern.
  Engineering defect or timing: preserve all evidence, diagnose, fix the smallest justified issue,
  and freeze any changed rule prospectively with written justification and review. D116 is never
  reinterpreted.
- **INCONCLUSIVE** — E1-E9 pass, no ENGINEERING finding, no common-mode pattern, but a sufficiency
  condition (section 4.3) is unmet, every cause being a classified DATA reason. Phase 3 stays
  provisional; a new protocol is designed. No automatic relaunch.
- **PASS** — E1-E9 pass, sufficiency met, and >= 1 observed matched pair (section 4.3).
- **PASS WITH LIMITATION** — E1-E9 pass, sufficiency met, no observed matched pair, and every cause
  is a classified DATA reason. Exactly one sub-label:
  - `all_triggered_no_control`: every selected member is triggered, so no untriggered control
    exists;
  - `zero_triggered_control_matching_not_exercised`: no member has an authenticated triggered state;
  - `pair_member_unobserved_data_reason`: a control/trigger pair was drawn but a member lacks a
    complete chain for a classified DATA reason;
  - `no_eligible_untriggered`: triggered members exist but no eligible untriggered member in their
    strata (the rest unavailable or in other strata).
  The limitation is stated in the evidence; Phase 3 may close with it recorded.

The class and its reasons are recorded in `PHASE_03_D116_EVIDENCE.json` from the evaluator report.

### 4.5 Descriptive diagnostics (not acceptance)

Reported for comparability with earlier pilots only (evaluator `diagnostics`): D089-era
availability counts: observed origins / n (and / 8), eligible completed histories / n (and / 8),
observed matched pairs, and the target ratio `5 * valid >= 4 * observed` (true/false with counts).
These do not determine the outcome class. Also reported: per-window actual interval, terminal/
close state, raw messages, covered/uncovered receipt durations, history ages, origin/target timing,
bytes and role coverage. Per D115 item 5 these are diagnostics for D116 onward only; the earlier
pilots' failed gates stand exactly as recorded.

## 5. Clock budget (estimate, not a bound)

The timeline below is an **estimate** from one prior run (D114), not a budget. The code ceilings
do not add up to a bound inside the frame age: screening declaration <= 600 s (`screening.LIMITS
max_seconds`), acquisition <= 1800 s (`screening_worker.py:52`, `:372`), then the owned inputs read
and the finish call each <= 600 s, and the activation/window steps follow. 600 + 1800 + 600 + 600
already reaches 3600 s before activation, so a slow but permitted run can exceed the frame age. The
real, fail-closed bound is **frame age 3600 s measured from `interval_start`**, re-checked at the
screening declaration (`screening.py:175-182`), the screening cutoff (`screening.py:494-501`) and
activation (`activation.py:332`, `:352`, replay `:415-416`). Exceeding it aborts the run; that is
an ENGINEERING timing failure and the outcome is FAIL. The 3600 s limit, the 600 s ceiling and all
other values are never relaxed, extended or worked around for D116.

D114 reference, in seconds after `interval_start`: interval end 409.27, frame available 572.78,
selection declaration 901.60, selection read completed 1070.85, cutoff 1285.62, saved 1320.02,
screening declaration ~1518.97; screening then ran 203.85 s before the old 180 s guard stopped it
(failure at 1722.82). Expected D116 timeline, assuming comparable source conditions and the same
code up to screening: interval end ~410, frame available ~575, selection declaration ~900, read
completed ~1070, cutoff ~1285, saved ~1320, screening declaration ~1520, screening phase end
~2400 or earlier, activation ~3000 or earlier. The ~329 s declaration gap in D114 was attributed
from code, not measured per step (the `panel_declared` stdout clock gives a first measurement).
The evaluator reports the measured seconds after `interval_start` and the remaining frame-age
margin.

Two further risks are **not budgeted** and each is ENGINEERING if it occurs:

- **120 s assessment freshness.** A triggered/control role must still have an assessment input
  window and availability no older than `ScreeningPolicy(120,120)` at activation
  (`assessments.py:98-101`; `activation.py:235-258`, evaluated at `:333`, `:353`, replay `:413-414`).
  Slow screening-to-activation hand-off breaks the role; the evaluator reports each assessment's
  age at activation.
- **60 s window age at freeze.** The pre-origin window must have ended no more than 60000 ms
  (`OriginWindowPolicy(120000,60000)`) before the origin freeze (`origin_window.py:98-101`,
  `origin_features.py:105-108`, reasons `window_stale`, `window_stale_at_freeze`). The origin is
  scheduled after activation, so windows that end early in a long screening phase will age out;
  this can make most or all histories ineligible and is recorded as ENGINEERING, not as
  unavailable history.

## 6. Storage

Reservation unchanged: 13,308,526,592 bytes (7 GiB frame retained cap + declared panel/window/
target/original-recovery reservation incl. 2 GiB reserve + 34 MiB capacity-proof read overhead,
no overlap discount). The script's preflight refuses to start below it. The run starts only after
storage is resolved under the capsule-first policy (`PHASE_03_BOUNDED_RETENTION.md`) through a
separate retirement record with explicit user approval for that session. This protocol authorises
no data retirement, no logical evidence deletion and no production storage action.

## 7. Execution boundary

- Clean tracked tree; this protocol, the script and the evaluator committed and their hashes
  recorded before any request: the protocol sha256, the script sha256, and for the evaluator
  (`backend/astrolabe/research_panel/d116_evaluator.py`), its CLI
  (`backend/scripts/evaluate_d116.py`) and its tests the commit hash and each file's sha256, plus
  the evaluator `classification_table_sha256`. Nothing is edited after the first request.
- The panel name is fixed: `data-dumps/fs2_panel_d116_integrated_1` (the `fs2_panel_` prefix is
  required by `panel_declaration.py:139`; no date placeholder, so the hashed script is the
  executed script). Derived roots follow from it: `fs2_selection_panel_d116_integrated_1`,
  `fs2_screening_worker_d116_integrated_1`, `fs2_activation_d116_integrated_1`,
  `fs2_runtime_d116_integrated_1`.
- Exclusive wrapper prefix, also fixed: `fs2_d116_integrated_1_*` for launch, stdout, stderr and
  result logs under `data-dumps/`, recording HEAD, command, script hash and actual clocks, even
  on failure.
- Backend interpreter, explicit isolated SQLite URL, `AUTO_MIGRATE=false`, email disabled,
  process-scoped `caffeinate`. No startup, migration, scheduler or production action.
- Verify absence of every derived panel / selection / worker / activation / runtime root before
  writes (script does this).
- No source edits until the original-code audit ends. Single attempt: no resume, redraw, retry or
  relaxation. A failed/incomplete frame cannot feed selection. A failure stops acquisition and is
  retained for diagnosis.
- No assistant turn or scheduler transition between frame completion, selection, screening and
  runtime.
- After the audit, evaluate the retained artifacts (no network, no writes to the run roots):
  `python backend/scripts/evaluate_d116.py data-dumps/fs2_panel_d116_integrated_1 --out
  data-dumps/fs2_d116_integrated_1_evaluation.json`. The report is the single source for the
  outcome class.
- Evidence output `docs/implementation/PHASE_03_D116_EVIDENCE.json` is written afterwards (not by
  the script) and includes the evaluator report (outcome class and reasons, gate-by-gate results
  with the cited fields, per-member per-stage states and classes, the section 4.5 diagnostics),
  the evaluator version, `classification_table_sha256` and the recorded file hashes. Evidence
  JSONs are never edited afterwards.

## 8. Reporting fields used by the gates

Script stdout stages: `preflight`, `frame_owned`, `frame_complete` (frame summary incl.
`interval_start`, `interval_end`, `frame_available_at`), `panel_declared`, `selection_complete`,
`complete` (worker `state`, `role_capacity`, screening `states`, `recovery`, full `runtime`
report with `events`, `origins`, `attempts`, `outcomes`), `accounting` (see section 10).
Per-window histories, observer attempts and refusals, origin facts and the selection
inventory/exclusions live in retained artifacts. The evaluator reads these roots only, all derived
from the panel root and overridable on its command line: panel (`panel_policy`), selection
(`selection_policy`, `selection_plan`, `selection_report`, `fs2_frame_read_original/
original_report.json`, `pages/`), screening worker (`worker_policy`, `worker_report`,
`fs2_screening_batch/screening_report`, `window_NNN`, `intent_NNN`, `fs2_capture_screen_NNN`,
`fs2_book_computation_screen_batch_NNN`, `fs2_socket_window_NNN`), activation (`activation_policy`,
`activation_facts`) and runtime (`runtime_policy`, `runtime_report`, `origins/<intent_id>/`,
`plans/<intent_id>/`, `targets/<attempt_id>/` with their captures). It makes no source request.

## 9. Stop conditions

Stop and report to the user, without relaunch, if: storage cannot be resolved; a protected boundary
would be crossed; the audit cannot run; or a change to any frozen value is proposed. A FAIL or
INCONCLUSIVE outcome leads to diagnosis and a new written protocol, never a rerun to obtain a pass.

## 10. Script

Derived from D114 (`PHASE_03_GZIP_PILOT_PROTOCOL.md`) with only: the fixed panel name
`fs2_panel_d116_integrated_1`, `scheduled_per_stratum` / `triggered_per_stratum` 4 -> 2,
`strata_limit` 2 -> 4, an added `panel_declared` stdout print, and a final `accounting` print
(derived from the returned report only; wrapped so that a print failure cannot affect results; its
former `exclusions` key is relabelled `second_stage_plan_exclusions`). No behavioural, policy or
threshold change.

```python
import asyncio,json,resource,shutil,subprocess,time,uuid
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.frame import FrameBudget,FrameRetryPolicy,GammaFrameRun
from astrolabe.research_panel.frame_cli import summary
from astrolabe.research_panel.panel_declaration import PanelProtocol,declare_panel,reservation,TEMPORAL_POPULATION
from astrolabe.research_panel.panel_selection import create_panel_selection,selection_root
from astrolabe.research_panel.screening_worker import allocation,run_public_window_pilot,worker_root
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.activation import activation_root
from astrolabe.research_panel.runtime import run_root
from astrolabe.research_panel.owned_windows import OwnedWindowPolicy
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
repo=Path('/Users/DayyanSheikh/Projects/astrolabe');base=repo/'data-dumps'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo).strip():raise ValueError('clean tracked tree required')
panel=base/'fs2_panel_d116_integrated_1'
p=PanelProtocol(scheduled_slots=8,triggered_slots=8,controls_per_trigger=1,cycles=1,target_attempts=1,
 scheduled_per_stratum=2,triggered_per_stratum=2,cadence_seconds=120,max_origin_delay_seconds=60,
 max_origin_save_seconds=5,horizon_seconds=60,tolerance_seconds=15,max_frame_age_seconds=3600,
 max_frame_interval_seconds=600,max_quote_age_seconds=60,max_identity_age_seconds=180,
 source_response_bytes=65536,source_run_retained_bytes=1048576)
reserved=allocation({'reservation':reservation(p,storage_profile='compact-v1')},windows=True)
budget=FrameBudget(requests=4000,total_bytes=3221225472,retained_bytes=7*1024**3)
# No overlap discount between old and new frame, selection, windows, roles or targets.
# Existing data is already reflected in free space. Add capacity-proof read journal space.
required=budget.retained_bytes+reserved['required_free_bytes']+34*1048576
free=shutil.disk_usage(repo).free
if free<required:raise ValueError('complete frame plus panel reservation unavailable')
for root in (panel,selection_root(panel),worker_root(panel),activation_root(panel),run_root(panel)):
 if root.exists():raise FileExistsError(str(root))
print(json.dumps({'stage':'preflight','implementation_commit':commit,'at':_clock(),'free_bytes':free,'required_free_bytes':required,'panel_reservation':reserved,'frame_retained_limit':budget.retained_bytes}),flush=True)
started=time.monotonic_ns();frame_root=base/('fs2_capture_'+uuid.uuid4().hex)
print(json.dumps({'stage':'frame_owned','root':str(frame_root),'at':_clock()}),flush=True)
run=GammaFrameRun(frame_root,limit=100,budget=budget,
 measurement_root=base/'fs2_capture_c63c72a0fe194f47824ccc862b0619cd',
 request_capacity_root=base/'fs2_capture_3a4f80db7fa94d248fc16e1397af4c71',
 request_capacity_commit='726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0',
 retry_policy=FrameRetryPolicy(),reuse_connections=True,accept_gzip=True)
asyncio.run(run.collect());frame=summary(frame_root)
print(json.dumps({'stage':'frame_complete','at':_clock(),'report':frame}),flush=True)
if frame['state']!='exhausted_consistent':raise ValueError('complete frame required; no selection')
# No assistant turn, schedule or wall-clock fabrication between verified frame and selection.
declare_panel(frame_root,implementation_commit=commit,output_root=panel,
 protocol=p,storage_profile='compact-v1',strata_limit=4,population_policy=TEMPORAL_POPULATION)
print(json.dumps({'stage':'panel_declared','at':_clock()}),flush=True)
selection=create_panel_selection(panel,repository=repo)
print(json.dumps({'stage':'selection_complete','at':_clock(),'provenance_class':selection['provenance_class']}),flush=True)
windows=OwnedWindowPolicy(10000,WindowBindingPolicy(60000,180000),
 WindowReconciliationPolicy(120000,120000,1000),OriginWindowPolicy(120000,60000),binding_mode='observation')
r=asyncio.run(run_public_window_pilot(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),window_policy=windows,concurrency=8,runtime_concurrency=4,repository=repo))
print(json.dumps({'stage':'complete','at':_clock(),'elapsed_ns':str(time.monotonic_ns()-started),
 'peak_resident_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'state':r['state'],
 'role_capacity':r['role_capacity'],'states':r['screening']['states'],'recovery':r['recovery'],
 'runtime':r['runtime'],'retained_bytes_before_report':r['retained_bytes_before_report']}),flush=True)
try:
 sc=r['screening'];plan=sc['plan'];rt=r['runtime'];from collections import Counter as C
 print(json.dumps({'stage':'accounting','at':_clock(),'unique_selected_markets':plan['unique_selected_markets'],
  'arm_counts':dict(C(a['arm'] for a in plan['assignments'])),'strata':plan['strata'],'second_stage_plan_exclusions':plan['exclusions'],
  'screening_states':dict(C(x['state'] for x in sc['states'])),'origin_states':dict(C(o['state'] for o in rt['origins'])),
  'target_states':dict(C(o['state'] for o in rt['outcomes'])),'attempt_states':dict(C(a['state'] for a in rt['attempts'])),
  'frame_interval_start':frame.get('interval_start'),'frame_interval_end':frame.get('interval_end'),
  'frame_available_at':frame.get('frame_available_at')},default=str),flush=True)
except Exception as exc:
 print(json.dumps({'stage':'accounting_error','type':type(exc).__name__,'at':_clock()}),flush=True)
```
