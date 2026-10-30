**Verdict: FREEZE_WITH_FIXES.** Three MUSTs; the freeze commit may proceed after them with a diff-only check.

# CB7 code-freeze check, 2026-10-30 (read-only; tree at 301b6679)

## Checks run
- Tests: `pytest -q tests/test_cb7*.py` gave 41 passed. `ruff check` on the 13 `cb7_*.py` files and `run_cb7.py` is clean.
- **Census hash re-check (MUST 5, part 1): PASS.** `/tmp/cb7_census/census.json` has sha256 85824be1…e6920. Its recorded hashes all match the committed files:
  - `rules_sha256` 05bf365c…21e9 equals `seals/cb7_text_geo_rules_v2.json`, which is `cb7_common.RULES_FILE` at line 48.
  - `constants_sha256` 2ce0e637…b0cd and `cb7_xv_definitions_sha256` 73b5f53b…1d9b equal `cc.census_declaration()`.
  - `cb7_census_source_sha256` 351d436d… equals the current file.
  - The seal sha256s equal the sha256 of each committed copy: h8_text 6074eee8…, h8_geo 4ae2be72…, h8_tail 2a88f3e5….
  - The h_geo capture pin 0df1dff6… equals the sha256 of `seals/cb7_hgeo_window_captures.sha256`. The text table is 5333444b…ce15 and `h_geo_binding` is 0.012.
  - `declaration_sha256` recomputes to 8eb396ba…438f, and the 9 file hashes match the code note's table.
- **Spec check (MUSTs 1-3).** G1, X1 and the S1 line match §2.3-2.6 and the CB7-G and CB7-X sections:
  - **G1:** net and fee rule; `p` is the max over event×week and theme; the inverted tail gate uses a one-sided Wilson bound on n/deff (`norm.ppf(0.99)`, cb1_history:682) and needs ≥10 YES event clusters.
  - **G1 placebo:** break-even with seed 7174; it advances only if the p condition and the tail gate both pass.
  - **G1 robustness:** (i), (ii) in each way, (v), (vii), (ix) and (x). Quarter signs are reported only.
  - **X1:** the definitions match `cb7_xv` (there is a test for this); time-shift placebo with seed 7175; wrong-side attribution `X1'−X1 ≥ |X1|/2` affects crediting only; route gate; robustness (i)-(v) and (viii).
  - **Holm and counting:** k1 = 3 at α 0.01, and k2 = 1 if X1 advances, else 0 (`stage2_k`).
  - **KIND_RULES:** `cb7_test` and `cb7_replication` are present (battery2:210-220).
  - **S1:** written as p = 1 and counted, with no wait on q0156.
  - **Count probe:** logging S1, G1 and X1 not-testable lines added exactly +3 to `cumulative_count`.
- **Causality:**
  - `outcomes_guarded` is opened only inside the `OutcomeGate` in `screen_g` (g_analysis:362-368). The units are built from sample, prices and drops first.
  - `require_freeze` refuses if the spec is missing, uncommitted, mismatched or read before `screen_not_before_utc`.
  - Results and Stage-1 copies are opened in `x` mode (write-once).
  - X reads no outcome.
  - Capped days store no prints (cb7_xv:184).

## MUST (blocking)
1. **Queue drafts q0148, q0149 and q0150 cannot run, and they are stale.**
   - All three pass `--n-boot 2000`. The probe `build_parser().parse_args([...,'--n-boot','2000'])` exits 2 with "unrecognized arguments". Remove the flag.
   - `depends_on` points at `q0147_cb7_census`, which failed twice. The census that ran is q0147c.
   - q0148 still depends on q0156, lists `text_edit_audit.json` as an input, and describes the slope analysis. Rewrite it to match MUST 3 and A-S.
   - The listed outputs (`*_screen/results.json`) are wrong. The real outputs are `creative_batch7/results_{S1,G1,X1}.json` plus `seals/cb7_*1_stage1.json`.
   - q0149 relies on exit-75 tempfails, which `TEMPFAIL_CAP` turns into "failed". Give it `depends_on` q0148 and q0150 (Reading A9).
   - Give all three jobs `not_before` = `screen_not_before_utc`.
2. **A1 is an amendment, not a reading. Revert to the literal rule.**
   - §2.3 says "≥ 30 clusters per way", and its stated parent, CB6 §2.3 (CREATIVE_BATCH_6.md:293), says "≥ 30 clusters in each declared way".
   - The code lowers this to 15 for the theme and date ways (`MIN_CLUSTERS` at g_analysis:39 and x_analysis:40). That is less conservative, and it was written after the census was seen.
   - Set both to 30. This changes nothing at census counts (theme 177, dates 295), so it costs no power.
3. **Re-take the hashes after fixes 1-2** (the declaration and source hashes will change). Then update the code note's hash table and its A1 entry before `write-spec`.

## Rulings on A1-A20
- **A1:** amendment; fix it (MUST 2).
- **Acceptable as readings:**
  - A2, A5, A6, A7, A10, A13, A18: each is the stricter or literal choice.
  - A3: §2.2 says unavailable units are "excluded… enter the worst case", and R_ann says "censored excluded".
  - A4: it invents the X worst case for robustness (v), but it touches only 6 prints (23,760 S prints, 23,754 with an available mark) and fills them with a value ≥ 0, which is conservative. Disclose it.
  - A8: see the SHOULD on placebo discordance.
  - A9 and A19: operational; G waits for its siblings.
  - A11: see the proposed value below.
  - A12: literal "in each way".
  - A14 and A15: the design says every C1 window is ≥ 33 h.
  - A17 and A20.
- **A16 deviates from §5.2,** which says every counting command runs the union first. See SHOULD 4.
- **Readings the code note does not list (disclose them, no change needed):**
  - Robustness (i) for G also requires the p threshold (g_analysis:251). The text asks only net > 0, so this is stricter.
  - The event×week clusters use the *scheduled-end* ISO week, not the resolution week. This matches the census and is outcome-blind.
  - The tail gate re-implements `cb1_history.tail_bound` (same algorithm) rather than importing it, so that 50-50 outcomes count as half.

## SHOULD
1. **Placebo discordance (probe).** With comonotone per-unit draws, the same market can resolve differently at its 30-day and 7-day origins: 21 of 400 synthetic markets did (q = 0.03+h vs 0.08+h). The placebo therefore has weaker within-market dependence than the real data, so it is a somewhat weaker check. This is unavoidable if each unit's expected net must be 0. Disclose it.
2. **The theme way is very unbalanced.** It has 177 clusters: the 8 named themes hold about 494 of the 663 events, and the other 169 are singletons. CR1 with a normal reference can be anti-conservative here; the break-even placebo is the declared guard. Before the screen, report the per-named-theme unit counts and the G end-date shares (`|close−end_at| < 1 h` and `close < end_at−7 d`) from `sample.csv.gz` and `origin_prices`, which hold no outcomes. Neither is in census.json, so I could not compute them.
3. **`write-spec` does not check `freeze_utc` against the clock.** The probe accepted `2026-01-01T00:00:00Z`. Require |freeze_utc − now| ≤ 1 h. (`T7_X_list` is safe anyway, because the floor binds for any freeze before 11-02T06:00Z.)
4. **Union step (A16).** The q0150 and q0149 wrapper, or the operator, should run `union_jsonl.py` and record the time in the result. Otherwise label the count "pre-union lower bound". It feeds only the BY triage label.
5. **Seal pins.** At screen time, compare the seal sha256s from `verify_seal_copies` with `spec["seals"]`.
6. **Crash recovery.** If the job crashes after the results file is written but before the trial lines, a re-run refuses and the test stays uncounted. Document the manual recovery.
7. **Spec order.** `spec.queue.promote` should list the run order q0148, q0150, q0149.

## MDEs from the census (one-sided, 80% power, z = 0.842)
- **G1:**
  - Inputs: n = 1,756 units; E = 663 event clusters; mean m = 86.22/1,756 = 0.0491; Var(net) ≈ p(1−p) = 0.0467; m̄ = 2.649 units per event, used as the deff upper bound.
  - Formula: SE = √(Var·m̄/n)·infl.
  - With infl = 1.3 (the design's theme assumption): SE = 1.09c, so the MDE is **3.5c at α 0.01** and **3.9c at the first Holm step** (z = 2.713).
  - With infl = 1.0: 2.7c and 3.0c.
  - So the YES rate must be about 10.5% against a price of about 4.9%, roughly double. This is unchanged from the design.
- **X1:**
  - Formula: SE ≈ σ_between/√G_event, with G = 70 (the design assumed about 95).
  - Scaling the design's 0.15-0.30c by √(95/70) gives SE 0.18-0.35c, so the **MDE is 0.55-1.11c**, at or above the 0.5c floor.
  - S prints are 23,760, about 32% of the 75k assumed, which adds within-event noise the formula ignores.

## Freeze-commit content (`model_specs/cb7_v1.json`, written by `write-spec`)
- `version` cb7-declaration-v1.
- `declaration_sha256` and the 9 `sources` sha256s, re-taken after MUSTs 1-2.
- `rules_sha256` 05bf365c…21e9.
- `census_json_sha256` 85824be1…e6920; `census_constants_sha256` 2ce0e637…b0cd; `census_xv_definitions_sha256` 73b5f53b…1d9b.
- `seals`: h8_text 6074eee8…, h8_geo 4ae2be72…, h8_tail 2a88f3e5….
- `h_geo`: text table 5333444b…ce15, capture pin 0df1dff6…03c0, binding 0.012.
- **Dates:**
  - `freeze_utc` = the commit time.
  - **`screen_not_before_utc`** = the first 06:00Z that is at least 2 h after the freeze commit has been deployed to the host. For a freeze on 10-30 or 10-31 that is `2026-10-31T06:00:00Z` or `2026-11-01T06:00:00Z`; it must be ≤ `T7_X_list` − 48 h so X1 is final and committed before q0153 could list.
  - `T7_X_list` = `2026-11-03T06:00:00Z`.
  - `T7_S_rep_start` "not applicable".
- **Promotion order:** q0148 (not-testable mode), q0150, q0149. Do not promote q0151, q0152 or q0156. q0153-q0155 stay conditional on X1 advancing.
- **Host:** `census.json` must sit at `creative_batch7/census.json` with the same sha256, or `load_census` refuses.

## Not verified
- Per-theme unit counts and the G end-date shares (not in census.json).
- The real host column layouts.
- X and G placebo runtime and memory on real data against the 3,600 s timeout.
- Whether the declaration hash reproduces across Python and numpy versions.

Files: `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/cb7_{astats,g_analysis,x_analysis,s_analysis,declaration}.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_cb7.py`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q014{8,9}_*.json`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0150_cb7_screen_X.json`.
