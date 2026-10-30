# R19 Rule 26 ruling: registered measurements (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: ACCEPT_WITH_CONDITIONS.** CH263 is coherent once revised. CH264 must be revised: as written, it picks its
units using information from after k.

**Summary.** A prospective measurement (k = 0) is allowed as a separate evidence role, `prospective_measurement`. It
reads the payoff the same way rule 19 already lets counts-only maps read a resolution
(`CREATIVE_HYPOTHESES_2026-10-31.md:120-122`). The difference is that its estimands, weights, splits and cost lines are
all frozen before the window. A measurement is never confirmation and never an edge claim (CLAUDE.md; ledger header
lines 5-6). The draft currently states its estimands as claims. Two errors must be fixed for CH263: the payoff formula,
and a double-counted entry cost. CH264 must stop using information from k+1 or later to exclude units.

## Conditions on the role
1. **Wording.** The draft's claim sentences are directional hypotheses (lines 440-444, 520-522), and so is its
   P(replicates) definition, "net above its cost line" (200-201). All of these must become plain estimand definitions.
   - The ledger may say only: "measured (prospective, k = 0): <estimand> = X [95% CI], cost-model-v1, conservative fee,
     touch, size-unlimited, capacity Y."
   - Banned words: Supported, confirmed, significant, edge, profitable, route exists. No p-values.
2. **Freeze.** Before the window starts, freeze and pin the code hash for: one headline estimand with its weighting
   (unit-weighted, event-bootstrap CI); the complete list of splits; the cost lines; the read-out date; and the
   precision threshold below which the result is reported as "coarse".
   - Every declared split is reported. None may be dropped or added.
3. **Later verdict tests.** A later test on the same object is labelled `informed (M1/M2)` and must use a disjoint, later
   window. Measurement data never counts as its evidence.
   - If the test targets a split that was chosen after seeing the measurement, it must report the measurement's split
     count as its selection width.
   - The measurement may set planning SDs. It must never set a threshold after the fact.
4. **Multiplicity and counting.** Measurements are not part of any Holm family, so k = 0 is correct. They are counted
   separately from registered tests.
   - Section 3's "about 1.8 registrations" (lines 820-822) must not count M1/M2 toward the programme's record of
     registered tests.
5. **What voids a measurement:**
   - any change to an estimand, split, weight or cost line after the window starts;
   - any read of a resolution, or of any data from after k, before the read-out date;
   - unit selection that uses information from after k;
   - a resolution source whose coverage of the population falls below the declared floor.
6. **Outcome states.** `pending`, `not_found`, `split_50_50`, `unavailable` and `contested` stay as separate counted
   classes. They are never filled in, and never valued at a midpoint.

## CH263 (M1): coherent, after these MUST items
- **Payoff formula.** Buying at a = 1 − c has expected payoff c − r_eff, where r_eff = P(loss) + 0.5·P(split). The
  draft's `net = c − r(1+c) − cost` (line 476) is wrong.
- **Double-counted cost.** c is measured from the ask, so the half-spread is already inside it. The cost line should be
  the fee (both rates) plus capital (lines 472-475). Alternatively, define c from the mid and keep the half-spread. Do
  one, not both (`COST_MODEL.md:84`).
- **Tail bound and clustering.** The 0.06% Clopper-Pearson bound (486-487) assumes independent units. A ladder proposed
  at once reverses together. Report reversals by event and bound the event-level rate.
- **Event cap.** For an estimand, a cap of 10 per event changes what is being estimated. Declare the weights instead.
- **Decision time.** Decision time = the latest receipt of the row, the sidecar and sweep 1's `ask_size_1`.
- **Resolution source.** Pin it, and check how much of the population it covers. The engine's logs may leave out
  proposed rows that the engine already dropped at eligibility.
- **Read-out date.** The read-out must be at least 30 days after the window ends. Line 838 says ≥14 days, which conflicts
  with the 30-day `not_found` rule at line 471. Units still unresolved at read-out stay `pending`.

## CH264 (M2): REVISE
- **Selection uses the future.**
  - A unit is made `unavailable` if its "`end_date` moved inside the window" (536). The moved `end_date` is only known
    after k.
  - S50 drops units that are "closed at k + 1" (552).
  - A buyer at k sees neither fact. These units must stay in the population as counted classes. Only state visible at
    ≤ k may exclude a unit.
- **The draft claims an identification it cannot have.** Ambiguity versus inattention by open-interest tercile is a
  contrast hypothesis (520-531). Under k = 0 it can only be a descriptive difference with a CI.
- **`not_found`.** Its payoff is unknown. Report net twice: with not_found as a loss of the stake, and with not_found
  excluded. Never value it at the mid.
- **Payoff and cost.** net = q_eff − ask − fee. The favoured side at mid = 0.5 is its own class.
- **Hazard estimand.** Read it under declared right-censoring at read-out.
- **Precision.** Event-clustered SEs. The ±2.2 points (546) assumes independent units.
- **Zone floors.** Rule 25 applies inside [0.05, 0.95] only where the tick is 0.001.

## Not verified
- Whether `uma_resolution_statuses` names the proposed side, or carries a time.
- How much of the population the resolution logs cover.
- All population counts (both are marked "unprobed").
- Whether the venue actually charges the "rate 0" fee it serves.
- The reviewer did not read DESIGN_V1, CH01, CH189 or the code.
