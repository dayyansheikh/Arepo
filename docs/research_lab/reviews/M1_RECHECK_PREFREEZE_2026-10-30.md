# M1 R1 re-check and pre-freeze verification (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: NOT_READY to freeze now.** All of R1 is addressed, but three things block a freeze: the text's own order puts the
J0 counts before the design-text freeze (status block l. 9; 9.1 heading l. 292; rules (a)/(b) "dates rewritten before the
freeze", l. 303-305); S2's cell list is "written at the freeze" from J0's counts (l. 376-377); and fixes 1-5 below. Apply
fixes 1-5, run J0, then a final verification and freeze. (Alternative: the LT13 order, freeze first, then the census; then
say so in the status block and 9.1 and make (a)/(b) the only effects J0 can have.)

**Verified:** sha256 `6362f3a7…9dca` (482 lines); no date or threshold changed (the diff only removes the old "(c) below 50%"
rule, as R1 asked); coarse thresholds (0.30c, 2,000, 2%, 75%), the 0.95 floor, read-out +31 days, B and the seed unchanged;
no banned word; MUST 6 ledger correction present; MUST 7 matches `costs.py:91-92`; MUST 2, 4, 5 and SHOULD 1-6 discharged.

## Blocking defects
1. **MUST 3 planning figure wrong (l. 351-352).** With zero reversals `p_U,s ≈ 4.38/E_s`, so `T_U = (4.38/N_F)·Σ_s (N_s/E_s)`,
   and each non-empty stratum adds at least its lower edge (1, 2, 4, 10 units per event): with all four strata `T_U >=
   74.5/N_F`, so `T_U <= 0.30c` needs about **24,800 final-state units** (about 17x the stated 1,460). Replacement text:
   > "with zero reversals `p_U,s` is about 4.38 / E_s, so `T_U` is at least 4.38 / N_F times the sum over non-empty strata of
   > their units per event (at least 1, 2, 4, 10): about 1,460 units if every event is a single unit, about 24,800 if all four
   > strata are non-empty. With about 4,200 units, coarse rule 3 is expected to fire and `theta_low` is expected to be
   > dominated by the sparsest stratum; disclosed in advance, it changes no rule."
   Add to 7.2: "A stratum with no final-state events contributes 0."
2. **S2 constant split; fee category unspecified.** `boundary_map_ch240.category_of` returns only `unknown`, `sports`,
   `crypto`, `nonsports_excrypto`; E5 keeps only the last, so S2 has one cell. Passed `nonsports_excrypto`, the docs rate is NaN
   (`costs.py:48-53, 93`). Fix: "S2 and both fee lines use `costs.category_key(capture k's sidecar fee_category)`; S2's cells
   are the `CATEGORY_TAKER_RATE` keys inside scope plus `unknown`; J0 prints its distribution." Fee exponent: "`fee_schedule`'s
   exponent where served, else 1.0".
3. **Chronological rule not deterministic; void case not auditable (9.2, 11.2(a)).** Fix: "A slot is recorded
   `missing_capture` once it has no complete capture 6 h after its grid time; a capture appearing later stays unprocessed
   (counted `late_capture_ignored`). The run refuses unless the state file's last folded capture is the last
   processed-or-missing capture before k. Each `status/<capture_id>.json` records that capture id and the state file's
   sha256 before and after."
4. **Undisclosed exact identity:** S8 cell "1" equals S3 "standalone" by definition; note it beside the S3 = S5 note.
5. **Degenerate CI:** with zero reversals the `r_eff` and `P(loss)` bootstrap intervals are [0, 0]: "printed as degenerate;
   `T_U` is the bound."

## Non-blocking
S6 x S9 structural zeros at tick 0.01 (cells (0.001, 0.005] empty): disclose. `theta_low` mixes an estimate (mean `c`) with
bounds: name the averaging set (final-state units).

**Could not verify:** the 735 / 1,735 count's scope; `fee_category` values vs docs keys; UMA status history; host retention
(84 captures); the 821-a-day figure.
