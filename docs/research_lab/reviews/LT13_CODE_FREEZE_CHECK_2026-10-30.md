# LT13 code-freeze check and A3 ruling (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: ACCEPT_WITH_FIXES.** The code follows the frozen text closely. As written, though, the text makes every fit NaN
by construction (A3, and the same happens through A4). Before q0722 is promoted, the design needs a dated amendment, the
code needs to follow it, and a science-reviewer needs to re-check that diff.

## Verified
- `LIVE_TESTS_13.md` sha256 is `ae594aa1…f738`, equal to the blob at d940c0ab and to `DESIGN_TEXT_SHA256`
  (`live_tests13_base.py:47`). The ledger freeze line is present.
- `pytest tests/test_live_tests13*.py`: **93 passed**. The imported pins match (`imported_hashes()==DECLARED`).
- Refusals in section 6 are in `_load_for_census` (`live_tests13.py:131-181`), in the order the text needs: forbidden
  block, design text plus ledger, seal design hash, batch-join pin, imported pins, scope, bound, spec blocks, feed file,
  non-empty work dir, then per-file sha256. The coverage check runs before any row is read (`:212-213`), and a test proves
  it.
- Causality: series are written only up to the current origin, the loop stops at `ORG[-1]` (`:223`), and
  `SlotStore13._guard` refuses any read past `limit`. The only later-slot read is `lag_twin_state` (`:246`), which returns
  one number per unit.
- Nothing computes a target, k+1 value, CH252, LT11 or LT12 object. An AST test bans those calls and imports.
- Write-once: an O_EXCL marker is created before any output (`:459-475`); the runner exits 2 on a second run.
- Seeds and thresholds match the text (l. 411, 436, 488, 913; `DECLARED:78-87`). Stage A draws no random number.
- The aliasing rule (`:740-778`) uses column-pivoted QR with tolerance `max(n,p)·eps·σ_max`, drops a column only when the
  rank is unchanged, never drops `zs`, and returns NaN when still deficient or `zs` is aliased. Rank, columns and drops are
  printed (`live_tests13.py:392`).

## Part 1: A3 ruling (confirmed: material)
K holds `spread_k` (l. 375). Section 3.3 adds the own innovation `spread_k − spread_{k−1}` (l. 735) and `spread_{i,k−1}`
(l. 741). These three columns satisfy an exact identity, and expanding-past demeaning is linear, so the identity survives
demeaning. None is in drop groups (1)-(3) (l. 748-749), so l. 750-751 forces NaN on every fit; the MDE is infinite and
CH253 is `census_dropped` because of the text, not the data. LT12 never had all three columns together.

**Which column to drop: `spread_{i,k−1}`, from 3.3's list.** Any two of the three span the same space. By
Frisch-Waugh-Lovell, the coefficient on `zs_bt` and its residuals, standard errors, `VIF_w`, design MDE and F-MDE depend
only on that span, so b_bt, every threshold, the window and the population are numerically unchanged and no adjustment
is lost. K is "LT12 1.7 unchanged" (l. 375), and the own innovation is named by the `VIF_w` and same-slot gates (l. 913),
by `rho_census` (l. 921) and by 3.5. `thin_i` still uses `spread_{k−1}`.

**Status.** A recorded deviation from a frozen text, made before the seal and the census, from reading the code only.
It follows the LT7 13.6 / LT8 13.7 precedent: an appended section that "governs where earlier text differs", the old
sha256 kept as a declared predecessor in code, and a ledger line recording old sha → new sha.

**Amendment text (append as a new section 13):**
> ## 13. Amendment after the design-text freeze (2026-10-30; `reviews/LT13_CODE_FREEZE_CHECK_2026-10-30.md`; governs where earlier text differs)
> Predecessor sha256 `ae594aa1a81aa93591d98f3210d907dff4df47ee3ad1dc0bbd44c5dccf59f738`. Made before the LT13 seal and census, from code reading only; no capture, sidecar or census output read. (a) 3.3's control `spread_{i,k−1}` is removed: with K's `spread_k` and the own innovation `spread_k − spread_{k−1}` it is an exact linear identity, so the l. 750-751 rule made every fit NaN by construction. The retained pair spans the same column space, so b_bt, its inference, every gate value, threshold, MDE and window are unchanged and no adjustment is lost; `thin_i` still reads `spread_{i,k−1}`. (b) A control identically zero after demeaning lies in the span of any retained set; it is removed before the rank, printed as `zero_variance_dropped`, and is not a group (1)-(3) drop.

## Part 2: rulings on A1-A17
- **A1** accept (hash pins fail closed; disclose). **A2** accept. **A3** amendment above. **A4** amendment clause (b): as
  written, any all-zero K indicator (`vol_missing`, `hte_unknown`) would also force NaN.
- **A5** accept the causal reading; SHOULD print the batch-rename count.
- **A6-A13** accept. A8 is the literal reading (closed and crypto members count as incomplete); disclose that this pulls
  completeness towards young batches.
- **A14** require a change: unknown fee class must be NaN, not 0 (`live_tests13_base.py:618`). See MUST 3.
- **A15, A16** accept. **A17** accept, with the dry-run memory measurement before promotion.

## Fixes
1. **MUST:** append section 13 above. Update `DESIGN_TEXT_SHA256`, declare `ae594aa1…` as the predecessor, and make
   `design_text_error` accept a ledger line `LT13 DESIGN TEXT AMENDED 13` carrying both hashes. Ledger entry with old →
   new sha.
2. **MUST:** remove `spread_km1_c` from `DECLARED["controls_own"]` (`live_tests13_base.py:73-74`). Turn the A3 test into a
   passing-rank test, and add a test that b_bt is identical whichever of the three columns is dropped. `loose_spec` should
   stop editing the control list.
3. **MUST:** set `fee_on` to NaN when the fee class is `unknown`, and count those units (1.4.3 l. 266 "excluded,
   counted"; 1.5 l. 356 "never 0"). q0717 found 0 such units.
4. **SHOULD:** the census refuses when `code_hashes()` differs from the seal's `code_sha256` (recorded at
   `live_tests13.py:88`, never compared).
5. **SHOULD:** the gate-flip test also flips `g_eff`, `ident_top1`, `ident_batch` and `corr_zs_*`.
6. **SHOULD:** print the batch-rename count (A5) and the closed-member share of completeness (A8).

## Not verified
- That no census-span data was opened (only the code note's statement).
- Whether LT12's `design_ss12`, `slope_mde12` and `f_design_c` demean exactly as l. 906 requires (relied on LT12's check).
- The real memory use of q0722.
