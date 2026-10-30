# M2 (CH264) challenger R1 (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: GO_WITH_CHANGES.** sha256 `c075355b…0ca4` checked. All R19 CH264 REVISE items, conditions 1-6 and the single cost
convention are met; no banned word; payoff `n = Q − ask_f − fee` at `p = ask_f`, no half-spread counted twice (l. 198-202,
221-222). Three items would break the measurement by how the text is written (the LT13 / LT14 failure mode), and one brings
back the forbidden post-k exclusion as a secondary result.

## MUST
1. **S11 spread cells misclassify by floating-point maths (l. 286).** `ask − bid <= 0.01` on floats parsed from decimal strings
   fails on 80 of 99 one-tick spreads at tick 0.01 and 803 of 990 at tick 0.001; the 0.03 and 0.10 edges fail too (53/97,
   19/90 at 0.01; 533/970, 203/900 at 0.001). Fix: `spread_k = round(ask − bid, 6)`, `mid_f = round(1 − mid_k, 6)`, every cell
   edge tested on the rounded values; synthetic test (vii).
2. **E6 is a token blacklist, not CH269's reading (l. 143-144).** CH269 counted "no proposal" only for empty-like strings
   (`"", "[]", "nan", "none"`; `census_map_ch269.py:238`). Fix: E6 passes only on that empty-form whitelist; any other non-empty
   form is its own class `uma_other_at_k`; the follow-up's P event matches whole tokens.
3. **Coverage floor contradicts the backlog label (l. 362-363 vs 376-379).** Counting `not_found` as uncovered voids M2 once
   `not_found` > 5% (designer Q4: yes, by construction if the venue deletes markets). Fix: coverage = "the source gave a
   definite answer" (a record, or absence confirmed in both passes plus one single-id re-query with HTTP 200); the 0.95 floor
   on `unavailable (fetch)` only; `not_found` stays a counted outcome class (`theta_NF`, the band, coarse rule 3). Define
   event coverage.
4. **Remove `theta_open` (l. 213, 358-359):** it drops units by a post-k state (`closedTime < t_d`), what the ruling removed, and
   is the number most likely to be read as "the tradeable payoff". §8.2 already prints the class count and mean `n_i`.
5. **Look-back depends on retention (l. 79-80, 125-126):** use a fixed span `[REGISTERED_UTC − 7 d, REGISTERED_UTC)` (84 slots),
   missing slots counted.

## SHOULD
1. Define S4 (`fee_free / fee_on / unknown`; neither M2 l. 279 nor M1 l. 225 defines it; CH269 uses `c251.fee_class`) and S3's
   `unknown` (a key outside the table, since E5 requires a non-empty `fee_category`).
2. Disclose likely empty cells (CH269: scheduled 14 of 1,347; high-liquidity x `no_rules` 0; S1 confounded with rule coverage,
   154 of 180 `no_rules` in the low tercile).
3. `theta = pi − mean h − mean fee` holds only to floating-point error: check within 1e-9, never `==`.
4. §7.4: `not_found` and `unavailable` units excluded and counted.
5. §7.2: unit basis of the strata (final-state units plus `not_found`); M1's corrected lower-edge wording.
6. Disclose: the Gamma touch at a past-end market may be stale (unmeasured).
7. Rename "gross premium" to "gross difference at the mid".
8. Rule-class reader: a `hash` record whose full row is gone gets `rules_unresolved`, not `no_rules`.
9. Void list: add "J2 unit manifest missing".

## Designer questions
1. Blind write-only follow-up store: acceptable under condition 5 (pinned code, no price or outcome field, hashed, read only at
   read-out); call it procedural blinding (void 11.2(b) cannot be audited); J1 status files and monitoring print no P/C counts,
   only hash and line count. 2. Keep E2. 3. Keep `theta` headline (`theta_NF` and band mandatory in the same line). 4. MUST 3.
5. S1 liquidity proxy acceptable with fixed cuts and label. 6. Placeholder lexicon acceptable if pinned. 7. 45 days fine.
8. Coarse thresholds fine. 9. Fee line, unknown category with served rate 0: confirmed at `costs.py:93-104` (key outside the
   table -> docs NaN -> `max(cands)` returns the served rate, possibly 0; 0.07 only when no schedule is served). M2's L1 must
   say "unknown key: served rate, possibly 0". **M1 has the same defect** (`MEASUREMENT_M1_CH263.md:185-186`, `:191` say
   "unknown giving 0.07"): fix at M1's final verification.

## Arithmetic recomputed
120-159 units a day x 21 days = 2,520-3,339; `N_F` about 2,140-3,170; independent-unit SE 0.71-0.99c; DE 2.2-6.4 gives a
half-width 2.1-4.9c; "as likely as not" coarse at 3.0c stands; `−ln(0.0125) = 4.38`; J0 rule (b) redundant (75 x 21 = 1,575 >
1,500, so (a) always fires first).

## Feasibility
The 2026-11-16 text freeze is reachable, but J0 must apply 3.2, 3.3 and 3.5 exactly: build J0 as J1 in dry mode (same pinned
code). J1 runs on the host until 2027-01-29 (about 790 captures) beside M1. With MUST 4 applied, nothing allows an edge reading.

**Could not verify:** `uma_resolution_statuses` forms; receipt time on `poll` lines; host retention and cron; Gamma `/markets?id=`
batching of closed or archived markets; the real `not_found` rate; `fee_category` for past-end markets; whether past-end closed
markets stay in the captures; whether the venue charges the 0 rate it serves.
