# LT7 amendment 13.7 census-code re-check (commit 64acdbc4, branch feat/lt7-reward-carry), 2026-10-22 ~16:19Z

`evidence_role: none`. Reviewer: `science-reviewer` (independent, read-only; text saved by the orchestrator, lightly condensed).

## Verdict: FIXES_REQUIRED (three small must-fixes; causality, hashes and the frozen-gate discipline are sound)

## Verified
- Design text at 64acdbc4 = 575eb1dd…; live_tests7.py = 499225d5…; `DESIGN_TEXT_PREDECESSORS` = {840f4500…, 31baf5e5…};
  `SPEC_HASHED_BLOCKS` unchanged (reward keys outside it), so `spec_blocks_sha` and the committed seal still match. No gate,
  threshold, formula or MDE code changed.
- Causality: `RewardCarry.apply` loops k-1..k-11; `add(k)` precedes `apply(k)` in ascending order; transitions use stored
  slots <= k only; no chaining; missing slots skipped, never filled; malformed/absent never stored as listed.
- CV7 untouched (`census_volsem`, `semantic_rows`, `semantic_gate`); CH191/CH195 read no reward field.
- CS7 slots: the window adds no new captures (K 228-251 plus k-12 look-backs already cover it); 22 of 24 window slots
  sealed; 240/241 (10-21 00:31Z, 02:31Z) unsealed and counted missing. CC7 CH192 windows inside k-84..k.
- Implementer readings 1-8 accepted (13.7's "Unchanged: a listed text at k…" governs reading 1).

## Must-fix
1. **F-feasibility pairs use incomplete carry windows (CS7, feeds a gate).** `patient_units(..., any_slot=True)` drops
   NaN `in_band`; after the carry `in_band` uses the source's `rew_maxspread`; 12 of 22 pair slots lie outside K with 2-12
   stored window slots, so the pair units, `r_gate` (CH197) and F depend on which slots happen to be loaded. Choose and
   state in the ledger: (a) load [j-11, j] for every pair slot j (within CC7's sealed set, slots >= 156; q0604 needs
   CC7's roots); or (b) pair units use the k-only (v1) reward and `in_band`.
2. **"Unit counts do not change" is not guaranteed.** Units are filtered on `isfinite(in_band)` (`patient_units`,
   `ivr_units`); carried units can enter (NaN at k, finite at source) or drop (finite at k, NaN at source), moving
   `covered_share`, the units gate and MDE inputs. Add counts of units whose `in_band` became known only through the
   carry and units lost to it; record an erratum to 13.7's sentence (ledger erratum or re-hash with 575eb1dd… as a
   predecessor) before the census.
3. **Silent fallback in `RewardCarry.add`.** A series file without `rew_raw` (pre-13.7 or reused work dir) silently
   carries nothing. Raise when `rew_raw` is missing and any status is `listed`; add a `write_once_csv` -> `read_series`
   round-trip test with quoted/comma JSON showing the carry still fires.

## Notes (no blocker)
- `_reward_sensitivity` "v1" = v1 `rewarded` on the v2 unit set with v2 `in_band`/standardisation; label it so.
- `reward_switch_markets_1/_ge2` count units (market x origin), not distinct markets; add a market-deduplicated count.
- `s > k` guard in `apply` is dead code; the CS7-window test passes without the change (window adds nothing); 13.7's
  "CS7's capture set gains the carry window" is a no-op in practice.
- `reward_window_slots_missing` mixes "not loaded" and "not sealed" (the same inside CC7/CS7 origin windows).
- q0602 timing: do not update the host checkout before q0602 starts (it would record 575eb1dd… instead of 31baf5e5…).

## Promotion
After fixes 2 and 3 are merged with a short re-check, q0603 may be promoted. q0604 also needs fix 1 and goes after
q0603. Both fit before 2026-10-28T03:30Z.

## Not verified
Tests not run by the reviewer; reward parameters at null captures (no local data); `_merge_counts` summing; q0604 host roots.

## Orchestrator decision on fix 1 (16:20Z, before any census, from code structure only)
(a) full carry windows for pair slots, if every needed slot is inside the LT7 seal and reachable from q0604's roots;
otherwise (b), with the reason recorded. Fix 2 by re-hash (575eb1dd… added as a predecessor; no census has run on it).
