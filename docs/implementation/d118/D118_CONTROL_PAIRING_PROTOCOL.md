# D118 — single live prospective validation of same-stratum control pairing

Status: DRAFT — NOT FROZEN (revision 2: 4 strata × 3 members). The first draft (4 × 4, 16
members) breached its predeclared synthetic dry-run abort criterion (maximum window age at origin
freeze 43.09 s > 40 s) and was not frozen. That was a pre-freeze design iteration, not a failed run:
no live request was made. This revision reduces the members per owned runtime to respect the
unchanged 40 s criterion (section 2a). Freezing still requires a new accepting `science-reviewer`
pass on this revision, then a separate freeze record
`docs/implementation/PHASE_03_D118_FREEZE_RECORD.md` holding the frozen file hashes, before any
request. No source request, pilot run or live network access has been made in drafting this
document. Only the synthetic loopback dry runs of section 5 have been run.

Location note: this file lives under `docs/implementation/d118/` rather than at
`docs/implementation/PHASE_03_D118_CONTROL_PAIRING_PROTOCOL.md` because the project permission rule
`Edit(/docs/implementation/PHASE_03_*_PROTOCOL.md)` denies creating files at that path too. Its
immutability after freeze comes from the sha256 in the freeze record, which the launch wrapper
checks.

Inputs this protocol answers: the specialist diagnosis
(`docs/implementation/d118/D118_SPECIALIST_DIAGNOSIS.md`), the independent Fable review
(`docs/implementation/d118/D118_FABLE_REVIEW.md`, eight points, all accepted by the lead), the
regenerated design estimates (`docs/implementation/d118/D118_DESIGN_ESTIMATES.json` and
`D118_DESIGN_ESTIMATES_V2.json`, produced by `backend/scripts/d118_design_estimates.py`) and the
dry-run records (`docs/implementation/d118/D118_DRY_RUN.json` for 4 × 4, `D118_DRY_RUN_V2.json`
for the 12-member candidates). The acceptance logic is code, not prose:
`backend/astrolabe/research_panel/d118_evaluator.py` (`d118-evaluator-v1`), its CLI
`backend/scripts/evaluate_d118.py` and tests
`backend/tests/unit/test_research_panel_d118_evaluator.py`. The evaluator re-executes the frozen,
unedited D116 evaluator code (`d116_evaluator.py`, `d116-evaluator-v3`) against a namespace in which
only the declared D118 values differ (section 4).

## 1. Purpose and non-claims

D116 (PASS WITH LIMITATION, `no_eligible_untriggered`) left live same-stratum control selection and
pair completion unvalidated: both triggered strata had `control_pool = 0`, and D097 also drew zero
controls. The D116 addendum forbids Phase 4 triggered-versus-control contrasts until a prospectively
frozen design shows a non-zero control pool. D118 is one live run whose only purpose is to exercise
that control path, end to end, on real data with the final Phase 3 code (HEAD descends from
`8afbdff`; launch precondition, section 7).

It validates machinery, not prediction. Non-claims: no prediction, calibration, prevalence, alpha,
profitability, effect-size or independent-sample claim. **One observed pair is an engineering check
that the control path runs, not a statistical result.** Roles overlap markets and are not
independent samples. No Phase 4 modelling is authorised by this protocol or its outcome.

**Claim scope.** A PASS supports exactly: "the live control path was exercised on the population
temporal ∩ frame Gamma liquidity ≥ 1000 only". It says nothing about the D116 temporal population,
about markets below the liquidity floor, or about any other population. **The Phase 4 trade-active
frame is a different population**: a D118 PASS does not transfer to it, and Phase 4 use of
triggered-versus-control contrasts on the trade-active frame needs its own evidence.

D082/D085/D086/D088/D089/D094/D097/D110/D114/D116 keep their original outcomes. Nothing here
redraws, relabels, pools, backfills or reinterprets them, and D118 results are never combined with
them.

## 2. Design: identical to D116 except population, sampling shape and runtime concurrency

Same code path, transport (`accept_gzip=True`, `reuse_connections=True`), frame budget, windows,
screening, trigger rule, freshness, ceilings and audit as D116. Differences, and only these:

- **Population (post hoc, declared as such).** `LIQUIDITY_POPULATION =
  scheduled_end_after_selection_declaration_or_unknown_and_frame_gamma_liquidity_at_least_1000_v1`
  (panel declaration `fs2-panel-declaration-v5`, selection policy `fs2-panel-selection-v4`, plan
  `fs2-panel-selection-plan-v4`). The D116 temporal rule is applied unchanged; additionally a member
  whose original-frame Gamma `liquidity` is missing or invalid
  (`frame_gamma_liquidity_missing_or_invalid`) or below 1000 (`frame_gamma_liquidity_below_1000`) is
  excluded with an explicit zero-inclusion record and counted. 1000 is the first predeclared
  sampling liquidity edge (`sampling.py:25`), not a tuned value.
- **Sampling.** 4 strata × 3 members: `PanelProtocol(scheduled_slots=12, triggered_slots=12,
  scheduled_per_stratum=3, triggered_per_stratum=3)`, `declare_panel(..., strata_limit=4, ...)`;
  `strata_limit × scheduled_per_stratum = 12 = scheduled_slots`. `controls_per_trigger=1`.
  (Revision 1 was 4 × 4, 16/16; see section 2a.)
- **Owned runtime concurrency 8** (D116: 4), see section 5.
- **Naming.** Fixed panel name `fs2_panel_d118_control_pairing_1` and wrapper prefix
  `fs2_d118_control_pairing_1`.

**Why the liquidity filter is post hoc, and why it is legitimate.** D116 stated "no
price/book/outcome-based eligibility". The liquidity restriction is chosen *after* D097 and D116
showed dead strata (diagnosis: about 33% of D116's sampled population had no two-sided Gamma quote;
9 of 87 strata were at least 86% one-sided, concentrated in the liquidity-"unknown" bands, which the
uniform stratum draw picks as often as live strata). It is therefore declared as a post hoc design
change, made to give the control path a fair chance to run, and it narrows the claim (section 1). It
remains causally clean: Gamma `liquidity` is original-frame metadata read before selection and before
any screening book (`metadata.py:73`); it uses no screening book, no trigger state, no target and no
outcome. The alternative `spread ≤ 0.10` filter (also defensible) was rejected because it ties
selection to the same book state the trigger reads.

**Dependence disclosure.** `event_group` is always `None` at selection (`selection.py:180`), so
stratification does not separate siblings. A pair whose members share a Gamma event id or a
`negRiskMarketID` (from the verified 2xx screening `gamma.market` receipts) is disclosed by the
evaluator as `dependent_same_event_or_neg_risk_group`; unverifiable membership is
`unknown_group_membership`. Every pair, dependent or not, counts as mechanism execution only and
never as an independent observation. The disclosure is descriptive and cannot change the outcome.

**Design figures (not acceptance criteria).** From `D118_DESIGN_ESTIMATES_V2.json` (seed
20261011; book sweeps pinned by sha256 to the eight sweeps of the original
`D118_DESIGN_ESTIMATES.json`, whose figures the revised script reproduces exactly; it rebuilds
D116's eligible frame exactly: 208,582 members, 87 strata), for liquidity ∩ temporal (50,598
members, 58 strata), P(≥1 complete observed pair) and E[complete pairs]:

| Scenario (definitions in the JSON) | **4 × 3 (chosen)** | 3 × 4 | 2 × 6 | 4 × 4 (rev. 1, not eligible) |
|---|---|---|---|---|
| S1 pooled sweep trigger rate | **0.966** (2.28) | 0.972 (2.68) | 0.965 (2.86) | 0.992 (3.57) |
| S4 member-specific trigger rate | **0.956** (2.15) | 0.960 (2.50) | 0.950 (2.65) | 0.987 (3.34) |
| S4h untriggered probability halved (stress) | **0.835** (1.45) | 0.836 (1.61) | 0.816 (1.65) | 0.911 (2.15) |
| S4q untriggered probability quartered (harshest defined stress) | **0.600** (0.82) | 0.596 (0.87) | 0.579 (0.86) | 0.702 (1.15) |

On every sweep present when V2 ran (14 sweeps; sensitivity block, not the primary figures) the 4 × 3
values are 0.966 / 0.949 / 0.822 / 0.585. **Reducing 16 to 12 members lowers the pair probability:
the honest range for 4 × 3 is about 0.60–0.97 (4 × 4: 0.70–0.99), with the lower half favoured**:
both pilots had every one of their 10 assessable members triggered, and the likelihood of those
observed states is 134× higher under S4q than under S1 (43× under S4h). Under S4q, D118 is close to
a coin flip between PASS and PASS WITH LIMITATION. S4q is the harshest *defined* scenario, not a
lower bound:
the availability input is a Gamma-snapshot proxy for a two-sided CLOB book, members are modelled as
independent, and chain completion is an assumed 0.95. The Fable review's earlier 0.54 figure came
from the untraceable pre-script table (`design_table2.csv`) and is superseded by the committed
script; only the committed figures are cited here. On the same model the D116 baseline (temporal,
4×2) is 0.39–0.78. A PASS WITH LIMITATION therefore remains a realistic outcome and is not evidence
of a defect.

### 2a. Design iteration before freeze: 4 × 4 → 4 × 3

Revision 1 (4 × 4, 16 members) was reviewed and dry-run under a criterion declared before the run:
maximum window age at origin freeze ≤ 40 s. It measured 43.09 s (`D118_DRY_RUN.json`) and was
therefore not frozen. That is recorded as a pre-freeze design iteration, not as a failed D118 run;
no live request was made and nothing was collected.

**Justification for 12 members.** The breach is structural: the owned runtime runs at most
`concurrency − 1 = 7` origins at once (`concurrent_runtime.py:41-43`), concurrency 8 is the code
maximum, and each additional wave of origins adds roughly 7–11 s to the window age of its members. The
40 s criterion is a safety margin under the 60 s code limit (`OriginWindowPolicy(120000, 60000)`)
and is not loosened; the only remaining lever that changes no frozen threshold, formula, window,
trigger, freshness, ceiling or code is fewer members per owned runtime. The lead decision, taken
before any 12-member run, was to evaluate the two 12-member shapes (4 × 3 and 3 × 4) once each with
the identical dry-run method, and to choose the higher S4q pair probability if both pass. 2 × 6 is
within the declaration bounds and is reported as an estimate only. No other size was or will be
tried.

**Result** (`D118_DRY_RUN_V2.json`, one run each, 0.9 s per response, runtime concurrency 8):
4 × 3 maximum window age at freeze 36.26 s, audit 5.8 s; 3 × 4 36.14 s, audit 5.8 s. Both are
eligible. 4 × 3 is chosen by the predeclared rule (S4q 0.600 vs 0.596). The difference is within
model noise, and 3 × 4 is marginally higher under S1/S4/S4h and in expected pairs; the choice follows
the rule fixed before the runs, not a judgement made after them. 4 × 3 keeps `strata_limit = 4`
unchanged from revision 1 and from D116.

**Disclosed costs.** (1) Lower pair probability (section 2 table). (2) The margin to the 40 s
criterion is only about 3.8 s on loopback, so live latency above the synthetic 0.9 s per response
could push window ages towards the 60 s code limit; a live `window_stale_at_freeze` is ENGINEERING
(FAIL) and is never relabelled. (3) The decision rule of section 4 is unchanged: a PASS WITH
LIMITATION leads to the screen-then-activate re-architecture, not to another size.

## 3. Inherited policies and ceilings (unchanged except where marked)

| Item | Value |
|---|---|
| Trigger rule | `SnapshotTriggerPolicy(1,3,60000)` (\|imbalance\| ≥ 1/3, source age 60000 ms) |
| Controls | 1 per trigger, from untriggered members of the same stratum |
| Screening freshness | `ScreeningPolicy(120,120)` |
| Owned window | `OwnedWindowPolicy(10000, WindowBindingPolicy(60000,180000), WindowReconciliationPolicy(120000,120000,1000), OriginWindowPolicy(120000,60000), binding_mode='observation')` |
| Window duration | 10 s per selected token |
| History age / window age at read and freeze | 120 s / 60 s |
| Binding quote / identity | 60 s / 180 s |
| Origin quote / identity age | 60 s / 180 s |
| Origin dispatch / save | 60 s / 5 s |
| Target horizon / tolerance | 60 s / ±15 s |
| Cadence | 120 s, 1 cycle, 1 target attempt |
| Frame interval / frame age | 600 s / 3600 s from `interval_start` |
| Screening ceiling | `screening.LIMITS['max_seconds']=600` per call |
| Window computation | 180 s |
| Worker / acquisition | 7200 s / 1800 s |
| Activation | 600 s |
| Original-code audit timeout | 300 s literal, unchanged |
| Concurrency | screening/observer 8; **owned runtime 8 (changed from 4)** |
| Sampling | **4 strata × 3 members, 12/12 slots (changed from 4 × 2, 8/8)** |
| Population | **temporal ∩ frame Gamma liquidity ≥ 1000 (changed)** |
| Source bounds | 64 KiB per response, 1 MiB per source run; frame budget 4000 requests, 3 GiB wire, 3 GiB decoded, 7 GiB retained |
| Frame source arguments | `limit=100`, `FrameRetryPolicy()`, same `measurement_root` / `request_capacity_root` / `request_capacity_commit` as D116 |

Nothing else is tuned. Any mismatch between the launch HEAD and this table is a launch refusal, not
an edit.

## 4. Acceptance

Acceptance is D116 section 4, executed by `evaluate_d118`, which runs the identical D116 compiled
code. The D116 classification table is reused byte for byte: the evaluator refuses to load unless
its sha256 equals `6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4`. Sections 4.1
(exhaustive state classification, citation rule, common-mode guard), 4.2 (gates E0–E9), 4.3
(exercise sufficiency), 4.4 (outcome classes and sub-labels) and 4.5 (descriptive diagnostics) of
`PHASE_03_D116_INTEGRATED_VALIDATION_PROTOCOL.md` apply unchanged, except for exactly these declared
overrides (module constant `OVERRIDES`; a test asserts no other name differs):

- `EVALUATOR_VERSION = d118-evaluator-v1`;
- the protocol constant with `scheduled_slots = triggered_slots = 12` and
  `scheduled_per_stratum = triggered_per_stratum = 3`;
- E0 run identity: `fs2_panel_d118_control_pairing_1` and its derived roots (section 7);
- E1 frozen expectations: panel `strata_limit` 4 and `population_policy` `LIQUIDITY_POPULATION`;
  worker `runtime_concurrency` 8.

D118-only additions, which can only add failures:

- **E1:** panel declaration `fs2-panel-declaration-v5`, selection policy `fs2-panel-selection-v4`,
  plan `fs2-panel-selection-plan-v4`, `population_policy` `LIQUIDITY_POPULATION`,
  `liquidity_floor` 1000 and `liquidity_edges[0]` 1000.
- **E2:** every zero-inclusion reason is one of `scheduled_end_at_or_before_selection_declaration`,
  `frame_gamma_liquidity_missing_or_invalid`, `frame_gamma_liquidity_below_1000`;
  `population_exclusion_counts` equals the exclusion list; every eligible selection stratum has
  liquidity band 1, 2 or 3. Missing or unknown values fail closed.
- **Diagnostics:** `observed_origins_of_12`, `eligible_histories_of_12`,
  `max_window_age_at_freeze_s` and the per-pair dependence disclosure (section 2).

The E5 oversubscribed branch (a triggered member without a triggered assignment is accepted only
when its stratum's `triggered_pool` exceeds `triggered_per_stratum`) is unchanged D116 code. It could
not occur at D116's 2 per stratum; at 3 per stratum with `triggered_per_stratum = 3` it still cannot
occur, but it is covered by a test (`test_oversubscribed_trigger_branch_and_all_triggered_label`).

Outcome classes (D116 section 4.4, first match in order): FAIL, INCONCLUSIVE, PASS (≥1 observed
matched pair: both members' origins observed with eligible histories and observed targets), PASS
WITH LIMITATION with exactly one sub-label (`all_triggered_no_control`,
`zero_triggered_control_matching_not_exercised`, `pair_member_unobserved_data_reason`,
`no_eligible_untriggered`; the last requires `control_pool == 0` in every stratum with a trigger,
otherwise a control should have been drawn and the outcome is FAIL).

**Decision rule (predeclared).**

- The live control path counts as validated **only on PASS**, within the claim scope of section 1.
- **Single run, no retry.** No resume, redraw, relaunch, relaxation or second attempt for any
  outcome.
- **PASS WITH LIMITATION** stands as recorded and the control path stays unvalidated. The next step
  is the **screen-then-activate re-architecture** (screen a larger candidate set first, then
  activate matched trigger/control roles from it), **not** another population or sampling tweak (no
  D119 that changes the population again).
- **FAIL** leads to diagnosis, the smallest justified fix and a new written, reviewed, prospectively
  frozen protocol. **INCONCLUSIVE** leads to a new protocol. Neither leads to a rerun to obtain a
  pass.

The class and reasons are recorded in `PHASE_03_D118_EVIDENCE.json` from the evaluator report.

## 5. Clock budget and the window-age dry run

D116 section 5 applies unchanged: the fail-closed bound is frame age 3600 s from `interval_start`;
the 120 s assessment freshness and the 60 s window age at freeze are not budgeted and are
ENGINEERING if breached.

**Why runtime concurrency is 8.** With 12 (revision 1: 16) members, origins rather than screening
are the binding constraint: `concurrent_runtime.py:41-43` permits at most `concurrency − 1`
concurrent origins. At runtime concurrency 4 only three origins run at a time, so the last origins
freeze long after
their 10 s windows ended, risking `window_stale_at_freeze`. Concurrency 8 (seven concurrent
origins) is the maximum the code permits (2..8).

**Synthetic dry run (predeclared abort criteria, unchanged across revisions).** Before freeze,
`backend/scripts/d118_window_dry_run.py` runs the complete owned path with the D118 values
(liquidity population, runtime concurrency 8, D116 windows/trigger/freshness; `--strata` /
`--per-stratum` give the shape) on a
synthetic frame over loopback sockets and a mock HTTP transport that delays every response (0.9 s;
D116 live origins took about 2.9 s for three requests). **Abort: if the maximum
`window_age_at_freeze_s` exceeds 40 s, or the original-code audit exceeds 240 s, D118 is not
frozen.**

Revision 1 (4 × 4), recorded in `docs/implementation/d118/D118_DRY_RUN.json`:
**ABORT.** A single run (16 members, 0.9 s per
response, runtime concurrency 8; 154 s wall-clock) reached the synthetic PASS state with 8 complete
pairs, but the window ages at freeze were 14.8, 15.1, 15.2, 22.8, 23.0, 23.2, 28.1, 28.1, 34.8,
35.0, 35.0, 35.0, 42.6, 42.8, 43.1 and 43.1 s. **The maximum, 43.09 s, exceeds 40 s.** The
original-code audit took 7.5 s, against a limit of 240 s. The ages rise in waves because at most
seven origins run at once (`concurrent_runtime.py:41-43`) and 8 is already the code maximum, so the
breach is structural to 16 members in one owned runtime; it is not noise. The 60 s code limit was
not reached in this run. **Revision 1 was therefore not frozen.**

Revision 2 (12 members), recorded in `docs/implementation/d118/D118_DRY_RUN_V2.json`, one run per
candidate with the same method and settings: **4 × 3 (chosen): maximum window age at freeze
36.26 s** (ages 10.7, 10.7, 17.8, 18.4, 28.9, 28.9, 29.1, 29.1, 29.2, 35.9, 36.2, 36.3 s; audit
5.8 s; 138 s wall-clock); 3 × 4: 36.14 s (audit 5.8 s). Neither breaches 40 s or 240 s. The margin
to 40 s is about 3.8 s; the 40 s criterion itself is unchanged.

The dry run is synthetic engineering evidence only. Live latency may differ, and a live breach is
ENGINEERING (FAIL), never relabelled.

## 6. Storage

Reservation: 14,449,901,568 bytes (7 GiB frame retained cap + the 4 × 3 panel/window/target/
original-recovery reservation incl. 2 GiB reserve + 34 MiB capacity-proof read overhead, no overlap
discount), as the script computes. The script's preflight refuses to start below it, and the launch
wrapper additionally requires a 1 GiB margin. This protocol authorises no data retirement, no
logical evidence deletion and no production storage action; any storage remedy follows
`PHASE_03_BOUNDED_RETENTION.md` with explicit user approval in that session.

## 7. Execution boundary and launch preconditions

Launch preconditions, all required, checked by `backend/scripts/d118_launch.py` before any request
(any miss: exit without launching and without writing to any run root):

1. Clean tracked tree; launch HEAD descends from `8afbdff`
   (`git merge-base --is-ancestor 8afbdff HEAD`).
2. Frozen hashes: the wrapper reads the artefact table of
   `docs/implementation/PHASE_03_D118_FREEZE_RECORD.md` (this protocol, `d118_evaluator.py`, the
   unedited `d116_evaluator.py`, `evaluate_d118.py`, the D118 evaluator tests) and every file's
   sha256 must match. A missing record, a missing or extra row, or an unfilled hash fails closed.
3. Free disk ≥ 14,449,901,568 B + 1 GiB, measured immediately before launch.
4. **No collector process running**: `pgrep -f` finds none of `collect_universe_snapshot`,
   `sweep_books`, `sample_trades`, `run_forecast` (D116 addendum near-miss). Launch only outside the
   research-lab collector window.
5. Panel `fs2_panel_d118_control_pairing_1`; no root with that name, any derived name
   (`fs2_selection_panel_d118_control_pairing_1`, `fs2_screening_worker_d118_control_pairing_1`,
   `fs2_activation_d118_control_pairing_1`, `fs2_runtime_d118_control_pairing_1`) or any wrapper
   file `fs2_d118_control_pairing_1_{launch,stdout,stderr,result,evaluation}` exists.
6. Execution environment: backend interpreter; explicit isolated SQLite URL
   `sqlite+aiosqlite:///<scratch>/d118_isolated.sqlite` (recorded in full in `launch.json`);
   `AUTO_MIGRATE=false`; `DIGEST_EMAIL_ENABLED=false`; process-scoped `caffeinate -is`. No startup,
   migration, scheduler or production action.
7. The wrapper extracts exactly one `python` block from this file and executes it verbatim,
   recording HEAD, command, script hash and actual clocks in `fs2_d118_control_pairing_1_*` files
   under `data-dumps/`, even on failure.

Then: no source edits until the original-code audit ends; single attempt; no assistant turn or
scheduler transition between frame completion, selection, screening and runtime. After the audit,
evaluate once (no network, no writes to run roots; absolute, non-symlinked panel path):

`python backend/scripts/evaluate_d118.py
/Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_panel_d118_control_pairing_1
--launch-commit <the recorded launch HEAD> --out
/Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_d118_control_pairing_1_evaluation.json`

The report is the single source for the outcome class and counts only if `authoritative` is true.
No report, or an evaluator exception, is FAIL. Evidence
`docs/implementation/PHASE_03_D118_EVIDENCE.json` is written afterwards (not by the script) and is
never edited.

## 8. Reporting fields used by the gates

As D116 section 8, with the D118 roots. Script stdout stages: `preflight`, `frame_owned`,
`frame_complete`, `panel_declared`, `selection_complete`, `complete`, `accounting`.

## 9. Stop conditions

Stop and report to the user, without relaunch, if: a launch precondition fails and cannot be met
without a protected action (storage, or collectors owned by another session); a protected boundary
would be crossed; the audit cannot run; or a change to any frozen value is proposed. Every outcome
is final for D118 (section 4 decision rule).

## 10. Script

Derived from D116's section 10 block with only: the fixed panel name
`fs2_panel_d118_control_pairing_1`; `scheduled_slots` / `triggered_slots` 8 → 12;
`scheduled_per_stratum` / `triggered_per_stratum` 2 → 3; `population_policy` `TEMPORAL_POPULATION`
→ `LIQUIDITY_POPULATION` (and its import); `runtime_concurrency` 4 → 8. No other behavioural,
policy or threshold change.

```python
import asyncio,json,resource,shutil,subprocess,time,uuid
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.frame import FrameBudget,FrameRetryPolicy,GammaFrameRun
from astrolabe.research_panel.frame_cli import summary
from astrolabe.research_panel.panel_declaration import PanelProtocol,declare_panel,reservation,LIQUIDITY_POPULATION
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
panel=base/'fs2_panel_d118_control_pairing_1'
p=PanelProtocol(scheduled_slots=12,triggered_slots=12,controls_per_trigger=1,cycles=1,target_attempts=1,
 scheduled_per_stratum=3,triggered_per_stratum=3,cadence_seconds=120,max_origin_delay_seconds=60,
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
 protocol=p,storage_profile='compact-v1',strata_limit=4,population_policy=LIQUIDITY_POPULATION)
print(json.dumps({'stage':'panel_declared','at':_clock()}),flush=True)
selection=create_panel_selection(panel,repository=repo)
print(json.dumps({'stage':'selection_complete','at':_clock(),'provenance_class':selection['provenance_class']}),flush=True)
windows=OwnedWindowPolicy(10000,WindowBindingPolicy(60000,180000),
 WindowReconciliationPolicy(120000,120000,1000),OriginWindowPolicy(120000,60000),binding_mode='observation')
r=asyncio.run(run_public_window_pilot(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),window_policy=windows,concurrency=8,runtime_concurrency=8,repository=repo))
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
