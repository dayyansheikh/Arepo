# CB7 freeze check, 2026-10-30 (read-only)
**Verdict: NOT_READY**

**1. Census write-up.** It is faithful, with one error.
- The gate thresholds in `cb7_census.py:52-54` match §2.7. They were added in 75708661 (10-22) and have not changed since. No CB7 backend file changed between the census commit 7e9958c1 and HEAD, and the only change to the CB7 document is 62 added lines.
- The 2.7a numbers add up:
  - 4,108 − 430 = 3,678 and 3,067 − 218 = 2,849.
  - 787/319 = 2.467 clusters per unit, and 1 + 1.467 × 0.941 = 2.381.
  - Standard error 0.39/(0.971·√787)·√2.381 = 0.0221, so the minimum detectable effect is 7.0c.
- "Theme clusters 177" is correct: the 8 named themes plus one cluster per unmatched event (`cb7_census.py:379`, §CB7-G).
- **Error:** 2.7a (lines 425-427) and ledger line 5554 say "k ≤ 2 if S1-rep and S2 do not run". With both gone, only X1-rep is left, so k ≤ 1.

**2. Consequence of the S failure.**
- S1 is "not testable", p = 1, and counted. This is correct (§2.5, §2.7).
- The design does settle S2: Stage 2, which includes S2, is "registered only if S1 advanced" (line 594). q0152 holds both S1-rep and S2 (line 52) and is committed only if S1 advanced (§8.5). So S2 does not run and is not counted. The ledger's "not settled by the text" (line 5553) is wrong.
- `textorig` / q0151: line 594 says to collect data "regardless", but the stop rule (line 618) says it is never analysed under CB7. The reason for collecting early (before S1's result was known) no longer applies. The conservative reading is:
  - do not deploy the step;
  - do not pin `T7_S_rep_start` (record it as "not applicable");
  - do not promote q0156 or q0152;
  - record this as a written decision.
- Not deploying loses no CB7 replay capability, and it avoids changing `creative_batch1.py` and `arepo_pass.sh`.

**3. Holm families.**
- Stage 1: k1 = 3 (S1 at p = 1, G1, X1), α = 0.01.
- Stage 2: k2 = 1 if X1 advances, otherwise 0.
- The cumulative count gets +3 (S1, G1, X1), plus 1 more only if X1-rep runs.

**4. Reading 13a: ACCEPT, with notes added.**
- Its text was committed (836dc3f9, 0f6f031c, 10-28) before the census ran (10-30), and both variants equal 0.012, so the choice between them makes no difference.
- Note that acceptance comes after the run.
- h_geo = 1.2c is below `HALF_SPREAD` (1.5c and 2.05c in that price band). So the measured-spread check (robustness (ix)) gives the same result as the main calculation and tests nothing. Disclose this; change nothing.

**5. MUST fixes (blocking):**
1. Write G1 and X1 analysis code to the §5.1 spec: placebos, robustness (i)-(x), the inverted tail gate, the route gate and wrong-side attribution. Also write `cb7_declaration.py` and `run_cb7.py screen`. None of these exist: `run_cb7.py:3` says "Fetch side only: no analysis or screen code", and none of `screen`, `g1_net`, `x1_test` or `cb7_declaration` is found. Tests must use values the real code can produce.
2. Add `cb7_test` and `cb7_replication` to `battery2.KIND_RULES`; only `cb7_descriptive` is there (`battery2.py:210`).
3. Make `screen --family S` write the counted S1 "not testable" line (p = 1) without waiting on q0156, and record that removed dependency.
4. Correct k2 and the S2 statement in 2.7a and the ledger.
5. Freeze-time checks: re-check the census declaration hashes (an item still listed as not done in `CB7_CENSUS_FIX_RECHECK` "Not verified"), and run a `science-reviewer` code freeze check.

**SHOULD:**
- Report the minimum detectable effects for G1 and X1 from the census counts (§2.7 requires it). X has 23,760 S prints against the design's assumed ~75k.
- Report the per-named-theme unit counts.
- For G, report `|closed_time − end_at| < 1 h` and `closed_time < end_at − 7 d`. The census computes these only for S; G1 is where the end-date risk sits.

**What the freeze commit must pin:**
- `model_specs/cb7_v1.json`, containing:
  - the declaration sha256;
  - the source sha256 of `cb7_declaration.py`, the G/X analysis modules, `run_cb7.py`, `cb7_census.py`, `cb7_xv.py` and `cb7_common.py`;
  - `rules_sha256` 05bf365c…;
  - the census `constants_sha256` 2ce0e637… and the `census.json` sha256;
  - the h8_text, h8_geo and h8_tail seal listings;
  - the h_geo text table 5333444b… and the capture pin file.
- Dates: `T7_X_list` = max(2026-11-03T06:00Z, freeze + 24 h). `T7_S_rep_start` is not applicable.
- Jobs to promote: q0148 (in not-testable mode), q0149, q0150. Do not promote q0151, q0152 or q0156. q0153-q0155 stay conditional on X1 advancing.

**6. Leakage and point-in-time.**
- G: only 1 unit, and S: only 4 eligible units have `closed_time` before the origin, so this is minor.
- The 778 of 3,656 S markets that closed more than 7 days before `end_at` suggest Gamma keeps the scheduled end date rather than rewriting it.
- **Undeclared risk:** the geopolitics tag is read as of the fetch, not as of the origin. Markets tagged after they became newsworthy would bias G1 towards the hypothesis. The tag-and-topic subset still requires the tag. 40.0% of the frame is tag-only. Disclose this and label G1 L1.
- X: the Kalshi `end_ts + 120 s` rule and the mark at ≤ u − 600 are point-in-time correct. 72% of minute ends have no candle stamped exactly there (Reading 1, conservative).

**Not verified:** the `census.json` values (no host access), and the q0147t first-row and text-availability reports.
