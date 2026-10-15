# D120 — single live prospective validation of screen-then-activate pairing

Status: **DRAFT — NOT FROZEN.** Freezing requires an accepting `science-reviewer` pass on this
draft, then a separate freeze record `docs/implementation/d120/D120_FREEZE_RECORD.md` holding
the frozen file hashes and the freeze commit, before any request. No source request, pilot run or
live network access has been made in drafting this document. Only the synthetic loopback dry runs
of section 5 have been run.

Location note: as for D118, the file lives under `docs/implementation/d120/` because the deny rule
on `PHASE_03_*_PROTOCOL.md` blocks creating files at that path. After freeze, the sha256 recorded in
the freeze record governs, and the launch wrapper refuses to launch if this file differs from it.

Inputs this protocol answers: the specialist design (`d120/D120_SPECIALIST_DESIGN.md`), the Fable
5.1 review (`d120/D120_FABLE_REVIEW.md`; every item adopted by the lead and binding here), the
committed, pinned design estimates (`d120/D120_DESIGN_ESTIMATES.json`, produced by
`backend/scripts/d120_design_estimates.py`) and the dry-run record (`d120/D120_DRY_RUN.json`,
produced by `backend/scripts/d120_window_dry_run.py`). The acceptance logic is code, not prose:
`backend/astrolabe/research_panel/d120_evaluator.py` (`d120-evaluator-v1`), its CLI
`backend/scripts/evaluate_d120.py` and tests `backend/tests/unit/test_research_panel_d120_pairing.py`.

## 1. Purpose, non-claims and what a PASS licenses

D118 drew two of seven triggers with a control. The cause is structural (three screened members per
stratum, a trigger state on about 56% of quoted books, one-to-one matching inside the stratum),
and D118's decision rule routes a limitation to a screen-then-activate re-architecture. D120 is one
live run whose purpose is to show that this re-architecture fills trigger/control pairs reliably on a
declared population while keeping every pair group-disjoint.

It validates machinery and a population definition, not prediction. Non-claims: no prediction,
calibration, prevalence, alpha, profitability, effect-size or independent-sample claim.

**Terminology.** A *group-disjoint* pair is a trigger/control pair whose two members belong to
different dependence groups, with no group shared with any other activated member. Group-disjoint is
**not** independent: all origins of one run occur within about a minute and share run-level shocks.

**What a PASS licenses (and only this).** (1) The screen-then-activate mechanism (screening, role
draw, binding, activation, origins, targets, audit) works end to end on live data; (2) the
population definition below (temporal ∩ frame Gamma liquidity ≥ 1000, fee-category strata, the
declared category policy, dependence groups as attributes, strata with ≥ 8 groups) is the frame for
registered Phase 4 trigger-versus-control studies. It says **nothing about fill reliability**: one
run is six Bernoulli stratum trials. **Phase 4 effect studies need repeated runs**: N runs give at
most 6N pairs and at most N run clusters; estimands are within-stratum paired contrasts clustered by
run (and by dependence group). Changing the category policy (for example excluding sports) is a
declared parameter change: it needs regenerated design figures, not a new validation. Not licensed:
any effect claim from D120 itself, any other population, the Phase 4 trade-active frame, or any
Phase 4 modelling. Phase 3 stays provisional.

D082/D085/D086/D088/D089/D094/D097/D110/D114/D116/D118 keep their original outcomes. Nothing here
redraws, relabels, pools, backfills or reinterprets them, and D120 results are never combined with
them.

## 2. Design

Unchanged from D118: frame source and budget, transport (`accept_gzip=True`,
`reuse_connections=True`), trigger rule, screening freshness, window/binding/origin policies,
horizon, tolerance, quote and identity ages, source bounds, original-code audit. Changes:

- **Population (declared parameter).** `LIQUIDITY_POPULATION` exactly as D118 (scheduled end
  after the selection declaration or unknown, and original-frame Gamma `liquidity` ≥ 1000; explicit
  zero-inclusion records). Then the **category policy**: a declared population parameter, default
  `all` (no exclusion). An optional, sorted exclusion list (`PairingDesign.exclude_categories`)
  gives each excluded member the zero-inclusion reason `category_excluded_by_population_policy`.
  D120 is frozen with `all`.
- **Category.** `fee_category` from the original-frame `feeType` through the frozen prefix map
  `fs2-fee-category-map-v1` (`pairing.py`): sports, politics, crypto, weather, finance, economics,
  culture, tech, mentions; unmatched values `other:<raw>`; missing or invalid `unknown` (its own
  stratum). The stratum field is `fee:<category>` (selection v5 path), so no literal source value can
  collide with the missing-category stratum (the guard of `selection.py:178-180` is kept). Category is
  never inferred from question text; Gamma `category` is on 0 rows.
- **Dependence group (attribute, never a stratum field).** Union-find over every event id (including
  each event's `parentEventId`, which is itself an event id) and every series slug of the row (not
  only `[0]`), `negRiskMarketID`, and the frozen slug-token table
  `fs2-underlying-slug-tokens-v1` (btc/bitcoin, eth/ethereum, sol/solana, xrp/ripple, doge/dogecoin;
  exact `-`-separated tokens of event and series slugs only, never question text), computed over
  every sampling member of the complete frame (`fs2-dependence-groups-v2`). `parentEventId` was
  added at the pre-freeze review: 22,344 of 52,084 eligible rows carry it and it merges groups
  (3,684 → 3,677 on the D118 frame), so it is unioned; this can only make grouping stricter.
- **Strata.** time × fee category × time-to-close × probability band × liquidity band. A stratum is
  **drawable** only with ≥ 8 dependence groups.
- **Screen draw (selection, before any book read).** 6 drawable strata uniformly without
  replacement (seeded ranking); in drawn order, each screens 12 groups in seeded order (6 × 12
  chosen by the predeclared dry-run rule, section 2a; 6 × 16 breached a criterion), **skipping
  groups claimed by an earlier stratum (shared claim set)**, one seeded member per group. Exact
  conditional inclusion probabilities are recorded per screened member: the stratum probability,
  the group probability given the available (unclaimed) groups, the member probability within the
  group, and their product; the unconditional probability is recorded as `None` with its reason.
  The scheduled arm is a parameter kept at 0 (`PairingDesign.scheduled_per_stratum = 0`).
- **Screening.** Every screened member: `gamma.market` + `clob.book`, book computation and the
  frozen snapshot trigger, **no window**. All screening assessments are retained with their
  inclusion probabilities (a conditional, design-dependent prevalence estimate: conditional on the
  drawn strata and the shared claim set, not an unconditional population prevalence), and every screened member's book
  covariates (best bid/ask, best sizes, spread, signed imbalance, level counts and total size per
  side) are retained for Phase 4 matched or post-stratified variants. D120 itself does no
  covariate matching.
- **Role draw (at screening completion; fixed thereafter).** Per drawn stratum: trigger = the first
  available triggered member by seeded hash; control = the first available untriggered member by
  seeded hash; at most one pair per stratum (≤ 12 origins). A stratum with a trigger and no
  untriggered member records `control_scarcity` and activates nothing. Exact conditional role
  probabilities (1/|pool|) are recorded. `activate_screened = False`: screened-only members never
  get a window, origin or target.
- **Binding and activation.** For activated members only: a fresh binding read (`gamma.market` +
  `clob.book`), its book computation and a recomputed snapshot trigger (declared before the read),
  then the owned 10 s socket window bound to that fresh book; then activation, origins and targets.
- **Predeclared state disagreement.** The trigger state persists (D120 estimates over pinned sweep
  series: 95.25% unchanged after about 80 s; P(untriggered next | triggered) = 4.26%,
  P(triggered next | untriggered) = 5.36%), so about 0.57 disagreeing members are expected per run
  under S4 (roughly 1 pair in 10). **Roles are fixed at screening.** The binding trigger
  recomputation is the recorded origin-adjacent state; the evaluator counts disagreements
  descriptively (`state_disagreements`) and never relabels a role. **Phase 4 must use the
  `origin_window` imbalance fields** (`pre_origin_window.coverage`: `end_imbalance`,
  `covered_mean_imbalance`, `covered_persistence_ratio`) for any origin-time state.
- **Reservation.** A new protocol version (`PairingPanelProtocol`, `fs2-pairing-panel-protocol-v1`)
  separates `screened_slots = 72` (two 64 KiB receipts plus 2 MiB bounded screening metadata each,
  enforced at runtime by the worker's retained-byte check) from `origin_slots = 12`. Screened members
  are no longer counted as origins (`panel_declaration.py:114-118` is frozen and untouched).
- **Frame (no frame-contract change).** A blocked keyset cursor (an HTTP 403 page) leaves the frame
  incomplete; the script then records `frame_abort` **before any selection** and makes **one**
  bounded frame-only re-run into a fresh frame root (`frame_rerun`). If the re-run is not
  `exhausted_consistent`, D120 stops before selection. Any other incomplete frame stops before
  selection without a re-run. No panel, seed or draw exists before a complete frame.
- **Naming.** Panel `fs2_panel_d120_pairing_1`; wrapper prefix `fs2_d120_pairing_1`.

**Dependence disclosure.** Screened members are group-disjoint by construction (shared claim set),
so activated members are too; the evaluator re-checks this as a hard gate. Residual dependence
remains through common underlyings not in the token table, and through run-level shocks.

**Design figures (not acceptance criteria).** `D120_DESIGN_ESTIMATES.json` (seed 20261011, 4,000
replications; inputs pinned by sha256: the D118 frame report, the D118 selection inventory, eight
2026-10-11 book sweeps in four 2-sweep series before the D118 frame, the 08:18 snapshot). The
rebuild reproduces D118 exactly (240,487 sampling members, 52,084 eligible, 57 strata without
category). With category strata: 298 strata, 127 drawable (≥ 8 groups) holding 96.1% of eligible
members, 3,677 dependence groups with `parentEventId` and the underlying table (3,752 without the
underlying table, 134 drawable strata; the specialist's 3,759 is reproduced exactly without both). Single-run P(PASS) = P(fill ≥ 0.8 with ≥ 4 triggers in scope and ≥ 3
group-disjoint complete pairs), `P_fill_ok_and_ind_ge_3`:

| Scenario | 6 × 16 (aborted, section 5) | **6 × 12 (chosen)** | E[pairs] 6 × 12 | E[complete group-disjoint pairs] 6 × 12 |
|---|---|---|---|---|
| S1 pooled trigger rate | 0.999 | **0.998** | 5.93 | 5.35 |
| S4 member-specific | 0.998 | **0.996** | 5.90 | 5.32 |
| S4h untriggered halved | 0.951 | **0.906** | 5.47 | 4.93 |
| S4q untriggered quartered | 0.578 | **0.434** | 4.24 | 3.82 |

**Honest range for the chosen 6 × 12: about 0.43 to 1.00, lower half favoured** by both pilots
(every assessable pilot member was triggered); under S4q D120 is close to a coin flip, slightly
against, between PASS and `PASS WITH LIMITATION:control_scarcity`. Fable's lower-bound estimate
(about 0.45 under S4q) is consistent. Reducing 16 to 12 costs about 0.14 under S4q (0.578 → 0.434).
S4q is the harshest *defined* scenario,
not a true lower bound: availability is a sweep/snapshot proxy, members are modelled as independent
and chain completion is an assumed 0.95. P(< 4 strata with a trigger) is about 0 in every scenario;
the dominant non-PASS outcome is `control_scarcity` (any scarcity stratum, 6 × 12: 0.07 S4, 0.41
S4h, 0.87 S4q). The expected run is not frame-weighted: strata are drawn uniformly, so sports are about 29%
of screened members and pairs (S4) against 65% of eligible members; drawable strata by category:
sports 36, politics 21, unknown 13, finance 13, culture 10, weather 10, crypto 8, economics 8,
tech 8. Excluding sports leaves 91 drawable strata and S4q 0.438 (6 × 12).

### 2a. Shape iteration before freeze (predeclared)

6 × 16 is tried first and 6 × 12 second, with the identical dry-run method; the first shape that
passes every abort criterion of section 5 is chosen, and no other shape is tried. **Result: 6 × 16
breached the assessment-age criterion (85.3 s > 80 s) and is not frozen; 6 × 12 passed every
criterion and is chosen.** This is a pre-freeze design iteration, not a failed run: no live request
was made.

**Disclosure (pre-freeze review).** Only the 40 s window-age and 240 s audit criteria were
inherited from D118. The three additional criteria (binding age 40 s, assessment age at activation
80 s, screening 60 s) and the "6 × 16, then 6 × 12" order were first committed together with the dry-run
script and its results (`3edba22`), not in an earlier commit; they were written into the
uncommitted draft before the 6 × 16 run, but the repository cannot prove that ordering. The cut is
conservative, not threshold-shopping: moving from 6 × 16 to 6 × 12 lowers the design probability of
PASS (S4q 0.578 → 0.434; S4h 0.951 → 0.906) and makes `control_scarcity` more likely, and no
criterion was loosened to admit a shape. The 40 s, 80 s, 60 s and 240 s criteria are safety margins under the unchanged code limits (60 s window age, 60 s
binding quote age, 120 s assessment age, 600 s screening ceiling, 300 s audit timeout) and are not
loosened.

## 3. Inherited policies and ceilings

| Item | Value |
|---|---|
| Trigger rule | `SnapshotTriggerPolicy(1,3,60000)` (\|imbalance\| ≥ 1/3, source age 60000 ms), screening and binding |
| Screening freshness | `ScreeningPolicy(120,120)` |
| Owned window | `OwnedWindowPolicy(10000, WindowBindingPolicy(60000,180000), WindowReconciliationPolicy(120000,120000,1000), OriginWindowPolicy(120000,60000), binding_mode='observation')`, activated members only |
| Origin dispatch / save; horizon / tolerance | 60 s / 5 s; 60 s / ±15 s |
| Cadence, cycles, target attempts | 120 s, 1, 1 |
| Frame interval / age | 600 s / 3600 s from `interval_start` |
| Concurrency | screening and binding 8; owned runtime 8 (at most 7 concurrent origins) |
| Sampling | **6 strata × 12 screened groups, ≥ 8 groups per drawable stratum, 1 pair per stratum, ≤ 12 origins; scheduled arm 0** |
| Population | temporal ∩ frame Gamma liquidity ≥ 1000; category policy `all` |
| Source bounds | 64 KiB per response, 1 MiB per source run; frame budget 4000 requests, 3 GiB wire, 7 GiB retained |
| Requests per run (ceiling) | 228 = 144 screening + 24 binding + 36 origin + 24 target (6 × 16 would be 276; Fable's ~252 counted 6 × 16 without targets) |

## 4. Acceptance

Executed by `evaluate_d120` (`d120-evaluator-v1`). It re-runs the frozen D116 per-stage
classification code (classification table sha256
`6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4`, citation rule, common-mode
rule) with only the names in `OVERRIDES` changed (version, protocol, run identity, frozen
expectations, screening schema, decision). The stage driver, gates and decision are D120-specific:

- **E0** run identity: names, launch commit in every artifact, screening schema
  `fs2-screening-pairing-v5`, live provenance of every screening, binding, origin, target and socket
  artifact.
- **E1** frame complete and fresh; frozen D120 protocol values, design (6, 12, 8), schemas
  (declaration `fs2-pairing-panel-declaration-v1`, selection `fs2-pairing-selection-v1`, plan
  `fs2-pairing-selection-plan-v1`, worker `fs2-pairing-worker-v8`, runtime
  `fs2-pairing-window-runtime-v6`), grouping policy, liquidity floor, D116 worker values.
- **E2** selection: chronology; exact stratum probabilities; exclusion allow-list (temporal,
  liquidity missing/below; category exclusion only when declared); every eligible stratum liquid
  and `fee:`-categorised; sampled = min(6, drawable); drawable ⇔ ≥ 8 groups; ≤ 12 screened per
  stratum; screened members group-disjoint.
- **E3** screening of every screened member (state row, covariates, classification, finish ≤ 600 s).
- **E4** binding (two receipts, recomputed trigger), window and history of activated members.
- **E5** roles: **exact replay of the role draw** from the sealed screening seed, list and states;
  **no two activated members share a dependence group**; triggers/controls authenticated;
  activated = bound = activation members = drawn roles; role capacity fits; scheduled arm 0.
- **E6/E7** origins and targets of activated members only (none for screened-only members).
- **E8** one original-code audit. **E9** accounting (receipt counts, hashes, retained bytes, ordered
  clocks including the binding declaration, slot identities).

**Outcome (first match):**

1. **FAIL**: any engineering finding, failed gate or common-mode pattern (applied separately to the
   screened members and to the activated members).
2. **INCONCLUSIVE**: fewer than 4 drawn strata with a trigger, or authenticated screening coverage
   below 80% (unassessable screened members for classified data reasons).
3. **PASS**: fill ≥ 0.8 with ≥ 4 triggers in scope and ≥ 3 group-disjoint complete pairs (both
   members: observed origin, eligible history, observed target).
4. **PASS WITH LIMITATION:`control_scarcity`**: fill < 0.8. Routes to the predeclared
   **screen-the-whole-stratum** fallback (specialist design estimate: fill 0.86 under S4q), not
   another tweak.
5. **PASS WITH LIMITATION:`pair_member_unobserved_data_reason`**: fill ≥ 0.8 but fewer than 3
   complete pairs, every incomplete pair member limited by a classified DATA cause.
6. Otherwise **FAIL**.

`state_disagreements` and the binding states are descriptive and cannot change the outcome.

**Decision rule.** Single run, no retry, no resume, redraw or relaxation. FAIL → diagnosis, smallest
justified fix, new reviewed frozen protocol. INCONCLUSIVE → new protocol. The evaluator's report is
the single source when `authoritative` is true; no report or an exception is FAIL. Evidence
`docs/implementation/PHASE_03_D120_EVIDENCE.json` is written afterwards and never edited.

## 5. Clock budget and the dry run

Fail-closed bound: frame age 3600 s from `interval_start`. Unbudgeted code limits: assessment age
120 s at activation, binding quote 60 s at subscription, window age 60 s at freeze; a live breach is
ENGINEERING (FAIL), never relabelled.

**Synthetic dry run (predeclared abort criteria).** `backend/scripts/d120_window_dry_run.py` runs
the complete owned D120 path (pairing declaration and selection, screening without windows, role
draw, binding reads and windows for activated members, activation, origins, targets, audit) on a
synthetic seven-category frame over loopback sockets and a mock HTTP transport delaying every
response by 0.9 s, runtime concurrency 8. **Abort (shape not frozen) if: maximum window age at
freeze > 40 s; maximum binding age (binding `clob.book` receipt to socket subscription) > 40 s;
maximum assessment age at activation > 80 s; screening (declaration to sealed screening) > 60 s; or
audit > 240 s.** Order 6 × 16 then 6 × 12; stop at the first passing shape.

**Result** (`d120/D120_DRY_RUN.json`, one run per shape, 0.9 s per response, 2026-10-11 12:46–12:52
UTC, outside the collector window):

| Measure (criterion) | 6 × 16 | **6 × 12 (chosen)** |
|---|---|---|
| Max window age at freeze (≤ 40 s) | 37.02 | **36.91** |
| Max binding age at subscription (≤ 40 s) | 3.39 | **2.74** |
| Max assessment age at activation (≤ 80 s) | **85.33 (breach)** | **69.03** |
| Screening, declaration to sealed (≤ 60 s) | 48.89 | **33.52** |
| Original-code audit (≤ 240 s) | 9.96 | **9.11** |
| Screened / activated / pairs | 96 / 12 / 6 | 72 / 12 / 6 |
| Wall clock | 201 s | 183 s |

Window ages at freeze, 6 × 12: 10.8, 10.9, 17.8, 18.0, 29.6, 29.6, 29.8, 29.8, 29.9, 36.6, 36.9,
36.9 s (waves of at most seven concurrent origins). **Disclosed costs:** the 6 × 12 margin to the
40 s window criterion is 3.09 s and to the 80 s assessment criterion 10.97 s on loopback; live
latency above 0.9 s per response could push the assessment age towards the 120 s code limit and the
window age towards the 60 s code limit. A live breach is ENGINEERING (FAIL), never relabelled. The
assessment age is driven by screening plus the binding/window phase before activation; it was not
calibrated against a live run (D120 has none). The synthetic frame has seven category strata of 18
groups, every screened book is quoted and every window event arrives every 0.5 s, so the dry run
says nothing about live availability or fill.

**Offline full-size measurements (pre-freeze review; no network).** The D120 pairing selection was
rebuilt with the production code on the pinned D118 frame (`fs2_capture_52eead5d...`, 240,487
sampling members) at code `da81c9d`, with one measurement-only deviation (frame age limit 604800 s,
because the frame is from 09:22 UTC; the temporal rule therefore used the 13:09 UTC declaration and
kept 46,402 eligible members, 296 strata, 125 drawable, 3,637 groups, against 52,084 at the D118
declaration):

- **Plan size:** `selection_plan.json` = 14,111,195 B against the 16 MiB (16,777,216 B) artefact
  limit (`selection.py:80`): margin 2,666,021 B (2.54 MiB). D118's plan was 13,368,020 B. The plan
  is dominated by the zero-inclusion exclusion list; an exclusion that removes about 30,000 more
  members (for example excluding sports) could exceed the limit and would need a compact encoding
  first. With the frozen policy `all` it fits.
- **Audit time:** the original-code selection replay (`read_original_selection`, child process,
  extracted code at `da81c9d`) took 59.7 s against the 300 s timeout (`original_reader.py`). This
  replay is the dominant term of the runtime audit, which additionally replays 72 screened members,
  12 bindings/windows, origins and targets (D118's live runtime audit took 62 s). Peak resident
  memory of the measuring process was 0.96 GB; selection creation took 211 s.

## 6. Storage

Reservation: 14,308,343,808 B (7 GiB frame retained cap + the pairing worker reservation of
6,756,499,456 B: 72 screened receipts and metadata, 12 bindings and windows, 12 origins and targets,
recovery, 2 GiB reserve + 34 MiB capacity-proof read overhead), as the script computes; the launch
wrapper adds a 1 GiB margin (15,382,085,632 B). Measured retained bytes of the synthetic worker:
10.1 MB for 6 × 12 (12.6 MB for 6 × 16), far below the reservation. A blocked-cursor re-run requires the same free space
again before it starts. No data retirement, logical deletion or production storage action is
authorised; any storage remedy follows `PHASE_03_BOUNDED_RETENTION.md` with explicit user approval.

## 7. Execution boundary and launch preconditions

Checked by `backend/scripts/d120_launch.py` before any request (any miss: exit without launching or
writing to any run root):

1. Clean tracked tree; launch HEAD descends from `8afbdff`.
2. Frozen hashes read from the artefact table of `d120/D120_FREEZE_RECORD.md` (this protocol, the
   design-estimate and dry-run records, `d120_evaluator.py`, the unedited `d116_evaluator.py`, every
   `pairing*.py` module, the shared research-panel modules on the launch path, `evaluate_d120.py`,
   `d120_launch.py`, the estimate and dry-run scripts, and the D120 tests; the exact list is
   `REQUIRED_FROZEN` in the wrapper and the record's table);
   a missing record, a missing or extra row, or an unfilled hash fails closed. The record names one
   ``Freeze commit: `<40 hex>` ``; `git diff --quiet <freeze commit> HEAD -- backend/astrolabe
   backend/scripts/d120_launch.py backend/scripts/evaluate_d120.py` must succeed, and there are no
   untracked or modified files under `backend/astrolabe`.
3. Free disk ≥ 15,382,085,632 B immediately before launch. For orientation only: after the local
   backup copy was removed with the user's approval (verified against GitHub first), free space was
   about 16.3 GB on 2026-10-11, about 0.9 GB above the requirement; the measurement immediately
   before launch is what counts, and a shortfall is a stop condition (section 9).
4. Launch only between HH:46 of an even UTC hour and HH:49 of the next odd hour (research-lab
   collectors start about HH:18 of even hours); no `collect_universe_snapshot`, `sweep_books`,
   `sample_trades` or `run_forecast` process; collectors are re-checked and recorded after the run.
5. No root `fs2_panel_d120_pairing_1` or derived root, and no wrapper file
   `fs2_d120_pairing_1_{launch,stdout,stderr,result,evaluation}` exists.
6. Backend interpreter; isolated SQLite URL `sqlite+aiosqlite:///<scratch>/d120_isolated.sqlite`;
   `AUTO_MIGRATE=false`; `DIGEST_EMAIL_ENABLED=false`; `caffeinate -is`.
7. The wrapper extracts exactly one `python` block from this file and executes it verbatim.

Then evaluate once:

`python backend/scripts/evaluate_d120.py
/Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_panel_d120_pairing_1 --launch-commit
<the recorded launch HEAD> --out
/Users/DayyanSheikh/Projects/astrolabe/data-dumps/fs2_d120_pairing_1_evaluation.json`

## 8. Reporting stages

`preflight`, `frame_owned`, `frame_complete`, optionally `frame_abort` and `frame_rerun`,
`panel_declared`, `selection_complete`, `complete`, `accounting`.

## 9. Stop conditions

Stop and report to the user, without relaunch, if a launch precondition cannot be met without a
protected action (storage, collectors owned by another session), a protected boundary would be
crossed, the audit cannot run, or a change to any frozen value is proposed.

## 10. Script

```python
import asyncio,json,resource,shutil,subprocess,time,uuid
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.frame import FrameBudget,FrameRetryPolicy,GammaFrameRun,read_frame
from astrolabe.research_panel.pairing import PairingDesign
from astrolabe.research_panel.pairing_declaration import PairingPanelProtocol,declare_pairing_panel,reservation
from astrolabe.research_panel.pairing_selection import create_pairing_selection
from astrolabe.research_panel.pairing_worker import allocation,run_pairing_window_pilot
from astrolabe.research_panel.panel_selection import selection_root
from astrolabe.research_panel.screening_worker import worker_root
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
panel=base/'fs2_panel_d120_pairing_1'
p=PairingPanelProtocol(screened_slots=72,origin_slots=12,cycles=1,target_attempts=1,cadence_seconds=120,
 max_origin_delay_seconds=60,max_origin_save_seconds=5,horizon_seconds=60,tolerance_seconds=15,
 max_frame_age_seconds=3600,max_frame_interval_seconds=600,max_quote_age_seconds=60,
 max_identity_age_seconds=180,source_response_bytes=65536,source_run_retained_bytes=1048576)
d=PairingDesign(strata=6,screen_per_stratum=12,min_groups_per_stratum=8)
reserved=allocation({'reservation':reservation(p,d,storage_profile='compact-v1')})
budget=FrameBudget(requests=4000,total_bytes=3221225472,retained_bytes=7*1024**3)
# No overlap discount between frame, selection, screening, bindings, windows, roles or targets.
required=budget.retained_bytes+reserved['required_free_bytes']+34*1048576
free=shutil.disk_usage(repo).free
if free<required:raise ValueError('complete frame plus pairing reservation unavailable')
for root in (panel,selection_root(panel),worker_root(panel),activation_root(panel),run_root(panel)):
 if root.exists():raise FileExistsError(str(root))
print(json.dumps({'stage':'preflight','implementation_commit':commit,'at':_clock(),'free_bytes':free,'required_free_bytes':required,'pairing_reservation':reserved,'frame_retained_limit':budget.retained_bytes}),flush=True)
started=time.monotonic_ns()
def collect_frame():
 frame_root=base/('fs2_capture_'+uuid.uuid4().hex)
 print(json.dumps({'stage':'frame_owned','root':str(frame_root),'at':_clock()}),flush=True)
 run=GammaFrameRun(frame_root,limit=100,budget=budget,
  measurement_root=base/'fs2_capture_c63c72a0fe194f47824ccc862b0619cd',
  request_capacity_root=base/'fs2_capture_3a4f80db7fa94d248fc16e1397af4c71',
  request_capacity_commit='726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0',
  retry_policy=FrameRetryPolicy(),reuse_connections=True,accept_gzip=True)
 asyncio.run(run.collect());report=read_frame(frame_root)
 pages=report.pop('pages')
 return frame_root,report,[{k:x.get(k) for k in ('ordinal','http_status','error','state')} for x in pages]
frame_root,frame,pages=collect_frame()
print(json.dumps({'stage':'frame_complete','at':_clock(),'root':str(frame_root),'report':frame},default=str),flush=True)
if frame['state']!='exhausted_consistent':
 # Predeclared: a blocked keyset cursor (HTTP 403 page) aborts before any selection and gets ONE
 # bounded frame-only re-run; any other incomplete frame stops here. No panel or seed exists yet.
 blocked=any(x['http_status']==403 for x in pages)
 print(json.dumps({'stage':'frame_abort','at':_clock(),'root':str(frame_root),'state':frame['state'],'blocked_cursor':blocked,'unrecovered_errors':frame.get('unrecovered_errors'),'failed_pages':[x for x in pages if x['error']]},default=str),flush=True)
 if not blocked:raise ValueError('complete frame required; no selection')
 free=shutil.disk_usage(repo).free
 if free<required:raise ValueError('frame re-run capacity unavailable; no selection')
 frame_root,frame,pages=collect_frame()
 print(json.dumps({'stage':'frame_rerun','at':_clock(),'root':str(frame_root),'report':frame},default=str),flush=True)
 if frame['state']!='exhausted_consistent':raise ValueError('frame re-run incomplete; no selection')
# No assistant turn, schedule or wall-clock fabrication between verified frame and selection.
declare_pairing_panel(frame_root,implementation_commit=commit,output_root=panel,protocol=p,design=d,storage_profile='compact-v1')
print(json.dumps({'stage':'panel_declared','at':_clock()}),flush=True)
selection=create_pairing_selection(panel,repository=repo)
print(json.dumps({'stage':'selection_complete','at':_clock(),'provenance_class':selection['provenance_class']}),flush=True)
windows=OwnedWindowPolicy(10000,WindowBindingPolicy(60000,180000),
 WindowReconciliationPolicy(120000,120000,1000),OriginWindowPolicy(120000,60000),binding_mode='observation')
r=asyncio.run(run_pairing_window_pilot(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),window_policy=windows,concurrency=8,runtime_concurrency=8,repository=repo))
print(json.dumps({'stage':'complete','at':_clock(),'elapsed_ns':str(time.monotonic_ns()-started),
 'peak_resident_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'state':r['state'],
 'role_capacity':r['role_capacity'],'bindings':r['bindings'],'recovery':r['recovery'],
 'retained_bytes_before_report':r['retained_bytes_before_report']},default=str),flush=True)
try:
 sc=r['screening'];plan=sc['plan'];rt=r['runtime'];from collections import Counter as C
 print(json.dumps({'stage':'accounting','at':_clock(),'screened':len(sc['states']),
  'screening_states':dict(C(x['state'] for x in sc['states'])),'arm_counts':dict(C(a['arm'] for a in plan['assignments'])),
  'triggers_in_scope':plan['triggers_in_scope'],'pairs_drawn':plan['pairs_drawn'],'fill':plan['fill'],'strata':plan['strata'],
  'origin_states':dict(C(o['state'] for o in rt['origins'])),'target_states':dict(C(o['state'] for o in rt['outcomes'])),
  'frame_interval_start':frame.get('interval_start'),'frame_interval_end':frame.get('interval_end'),
  'frame_available_at':frame.get('frame_available_at')},default=str),flush=True)
except Exception as exc:
 print(json.dumps({'stage':'accounting_error','type':type(exc).__name__,'at':_clock()}),flush=True)
```
