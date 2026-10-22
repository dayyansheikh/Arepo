# LT9 R1 challenger review, 2026-10-22

**Reviewer:** science-reviewer (read-only; text saved by the experiments autopilot).
**Reviewed:** `docs/research_lab/LIVE_TESTS_9.md`, sha256 `01c49890…5bef0a`, at commit b2882734.

## Verdict: REVISE (a re-check is required; nothing below loosens a threshold)

**Checked and correct:** every planning MDE, F-MDE and pass count recomputed and matching. CH213: 1.385c / 0.622c, about
67 breaks. CH214: 0.280c / 0.193c. CH212: 0.576c / 0.347c, n1 ≈ 48,240. CH215: 2.230c / 0.919c, n_eff ≈ 845. Vendored-file
hashes match (`e1c5c0c6…`, `2e8baa90…`). Seeds 2026119x / 2026129x and queue ids q0640–q0647 unused.

## Required changes
1. **Remove `f_binding`.** It is the census-conditional verdict switch that LT8 6.1 item 8(d) rejected (LIVE_TESTS_8.md:803).
   LT7 and LT8 fix F per test by design. CH213's state is built from origin k−1's target (§1.7), so its F binds
   unconditionally: add a CC9 gate `F-MDE <= 1.0c` and make world 14 binding unconditionally. CH212's F becomes a reported label, fixed now.
2. **CH213's panel is not fixed per market.** Under 13.7 (LIVE_TESTS_7.md:1296ff) a rewarded market becomes `rewarded = 0`
   after 12 null slots in a row, and programmes start and end, so §1.8's "panel label never shifted" is undefined and `rew`
   varies within a market through omission runs (CH212's state). Fix: a market's panel is its status at its first unit;
   later units with the opposite status are excluded and counted as `panel_switched`.
3. **CH213's stale-display world tests the wrong direction.** World 4r makes reward-panel rows staler (biases against the
   hypothesis). The risky case: a stale control row at k+1 sets `ds = 0`, weakening control reversion and favouring the
   hypothesis. Add a binding world 4c: control 0.25, listed reward rows 0.15, omitted rows 0.30.
4. **CH213 relative-position confounder.** Reward-panel `v` is per market; the control's `v_ctrl` is a cell median, so a
   break's jump relative to the market's normal spread differs by panel. Add the control
   `break x (log s_k − expanding-past mean of log s)` and a binding world 3b in which the panels differ in mean(s)/2v.
5. **CH212 route B model is singular.** In its population `om_k = om_k x clob_dropped_k` exactly. The tested term must be
   `om_k` on that two-class population.
6. **CH212 route A leak.** A CLOB drop between the k−1 :35 feed capture and capture k's :31 start enters route A and pushes
   the same way as the hypothesis. Require (causally) that the feed-listed programme end is after capture k+1. Report,
   never use for the verdict, the subset still listed at the next feed capture.
7. **F arms outrun eligibility.** Twins need k+5 (CH213) and k+4 (CH212), but eligibility needs only end > t+7 h. Require
   end > t+11 h and end > t+9 h respectively for F-arm membership (CH214's existing rule).
8. **A CC9 print acts as a reversion proxy.** "Share broken at k−1 given broken at k−2" measures persistence of broken
   spreads. Print it pooled only, never split by panel.
9. **CH214 fill confounder.** World 8 treats the fill control as exact where present; `volume_num` is market-wide and lags
   the sweeps by ~6 min. Add non-fill volume noise of equal variance to the observed control. Make `max(0, zdD)` the tested
   term, with `min(0, zdD)` as a control (fills only cause departures). Recompute the MDEs (rough estimate ~0.54c low; F
   ~0.77–0.92c). World 8 stays binding.

## Should-fix
- State whether census counts include planning's 0.8 effective factor; reconcile count gates with the MDE kill lines (70 vs 68 a capture; 240).
- One feed-flag clock (§1.2 "before decision" vs §1.3/§4 "before capture k's start"). CH213's decision time = capture k's
  last row receipt (cell medians and `n_members` use other markets' rows).
- CH214: require half-spread < v at both state sweeps.
- CH215: state which ends T_e fall in the window; disclose the placebo reaches pre-window data; "day" = UTC day of T_e;
  ban controls reused across ends or cluster them; add a gate on the `end_moved` share.
- Run CS9 after `T_E022` (its unfiltered lag sweeps fall inside E022's window), otherwise label it.
- Bar LT9 staff from looking at census-span data before the seal.
- Disclose that a late LT8 registration kills LT9 at `T_LT7`, or allow the pin earlier with a rule-based `REGISTERED_UTC`.
- Write the attribution limits into `config.EMBARGO` and `CANDIDATES.md`.
- State that no LT9 result can satisfy the programme's economic check.
- Fix the scoring-rule wording in §1.4.

## Answers to section 11
1. Any carry lag ≥ 1 is causal. The route-A filter is not caused by the omission, but it leaks (fix 6). Thresholds and "both → A" acceptable.
2. CH212 does not re-test LT7's verdicts. Note in the ledger that the agreement table was seen before `T_LT7`.
3. See fixes 2 and 4. Hidden programmes in the control panel bias towards zero. Keep world 3 binding.
4. See fix 3.
5. Moving the decision removes the catch-up threat. State that skipping (k−1, k] is because sweep k−1 is also a state input, and that the quiet filter removes units that responded immediately.
6. See fix 9.
7. Holding `z dimb5` fixed makes CH214 cleaner. A correlation gate of 0.5 is acceptable together with `VIF_w` ≤ 2.0.
8. No. See fix 1.
9. Adequate once the should-fix item is done.
10. The ordered lane and the freeze date are sound.
11. CH215's entry is counts-only and can only raise k, so it is not a forking path; see the should-fix list.
12. Verified.

## Answers to section 12
1. Keep any lag; S3 reports by run length. 2. Keep |move| as the primary. 3. Use the strict break. 4. No; the interaction
stays primary. 5. Keep the one-pass target. 6. Yes. 7. Yes, but re-reading the venue's page at the pin must not change any
value. 8. DE 31 is conservative. 9. Yes. 10. Acceptable once fix 9 is in. 11. Acceptable. 12. Keep 3.47.

## Not verified
When LT8's censuses will run; the venue's scoring rule (no network); how often `volume_num` is present.
