# LT10 R1 challenger review, 2026-10-23

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; report filed by the orchestrator).
Reviewed: `docs/research_lab/LIVE_TESTS_10.md`, sha256 `d7529914…b6829`, commit ba559ced. Nothing counted.

## Verdict: REVISE (a re-check is required; nothing below loosens a threshold)

**Checked and correct:**
- Every MDE, F-MDE and kill line recomputed and matching: CH224 0.299 / 0.232c, F 0.446c, n_eff 11,034 and 24,520;
  CH223 0.473 / 0.263c, n1 ≈ 2,330, so 2,913 withdrawals; CH222 0.625 / 0.442c, n1 ≈ 7,718, so 9,650 traded moves.
- Prior arithmetic: P(no test registers) = 0.66, E[k] = 0.54. ICC 0.0016667 = 0.02 × 252 / 3,024.
- Vendored-source hashes `eac14e68…` and `5264083948…` match. The hand-verdicts file `1d6f942a…` is unchanged since 39857e43.
- `xvenue` runs to 2026-11-04 (`backend/astrolabe/signal_engine/config.py:74`).
- No E009/E010 frozen rule is broken: their no-look rule (ledger, the E009 "Stopping rule", which also covers
  `predictions.jsonl`) applies only before their analyses, and the census runs after both.
- The census's structural rule is sound: within one origin, lag-0 moments only; the tested terms are Kalshi-only.

## Must-fix
1. **Scope can be picked after the census results are seen (§1.4 item 2).** Both scopes' gates are computed in one run,
   and "the owner puts sports in scope before the pin" lets the passing scope be chosen after CF10/CK10 and E009's verdict.
   Fix: the scope is final at the seal commit; without an owner decision by then, the default holds; with-sports values are
   printed only.
2. **D-LT10-1 is a choice made after E009's result is known (§8.2).** Route 3 ("no change, not registered") stays open at
   E010's analysis commit, a registration decision that can depend on the verdict, against §0. Fix: commit to route 1 at the
   freeze; route 3 only on named operational triggers (the disk stop rule, or the owner refusing).
3. **The pair record "in force" uses a time from before the file existed (§1.2).** `refreshed_utc` is the refresh's start
   (`cross_venue_live.py:622,627`); the file is written after paging ends (`:639-640`; about 2,700 pages at ≤ 0.9 req/s,
   about 50 minutes). Retirements, `p_event_id`, `k_close`, `p_end` would apply to origins before the record existed, and
   the live reader and the census would disagree. Fix: a record is in force only from its load or write time; declare how
   that time is recovered for the census (poller log or `runs.jsonl`) or name a declared conservative lag.
4. **The block Freedman-Lane gate breaks within-event dependence (§1.8, §1.8.1).** Each pair × day stratum is shifted
   independently, destroying cross-pair residual covariance at the same origin; event shocks also correlate the regressors
   (W1 jumps, W2 volatility), so the gate can over-reject. The size worlds cap events at 4 pairs, while the E009 ledger's
   Dependence note cites a 20-pair event. Fix: one common offset per event × day (event × two-day block for CH222), and a
   binding large-event world (e.g. one 20-pair event) for all three tests.
5. **Embargo gap against the main branch.** At `26d58fc5`, `CANDIDATES.md:243-250` plans the shadows `kx_last_chg_2h`,
   `kx_pull_2h`, `kx_spread_chg_2h` in `se-aux-xvenue2-v1`, covered only by `xvenue` (ends 11-04). §9 "Not requested:
   xvenue2" leaves CH222-CH224's direct shadows unembargoed in LT10's window. Fix: rebase onto 26d58fc5; make `kxbook` and
   `attrlimit_lt10` name these columns explicitly (Kalshi book, last-price or size changes at any horizon); use the
   `config.EMBARGO` format (a fixed `until` plus `until_before`, not "the later of").
6. **The order of the analysis commits is assumed (§1.1(b), §7).** "After E010's analysis commit (and so after E009's)" —
   the two jobs are independent. Fix: require both analysis commits and record both hashes in the seal.
7. **CH224's count gate is missing from the gate table.** §10.1 declares 31,000 units, but §7's CK10 row for CH224 has no
   count gate. Add it.

## Should-fix
1. CH223 "quiet" checks `dk1 = 0` only at the window's endpoints, so a reverting Kalshi move counts as quiet. Require Kalshi's
   mid unchanged at every step (as the every-step rule for `k_last`).
2. `k_vol24` is a rolling total; a trade can coincide with older volume rolling out, so the total falls and the trade is
   missed. Disclose; print the share of steps where `k_vol24` decreased. Keeping `vol_unknown` as a flag is fine.
3. Sidecar: the last capture *completed* before 00:00Z, not the last *started*.
4. CF10 is described as "pair files and line validity only; seconds", but its eligibility needs features, `rv60`, the ends
   rule and sidecars. Restate it.
5. The CH222 quote-only gate of 9,650 is below the kill line's ratio (about 13,270 at 1.375). State that CK10 count gates are
   necessary but not sufficient, and that CD10 decides.
6. Print the Kish effective event count G_eff = (Σm)² / Σm² and gate it (≥ 15): event-t inference with about 30 unequal
   clusters is anti-conservative.
7. Burn-in acceptance: add field presence ≥ 95%, late-origin share and receipt lags compared with the census. Disclose that
   the successor has shorter cycles without the E009/E010 writers (fewer `late_origin`); align its refresh time of day with
   E009's.
8. Make the engine's second read root a precondition of the handover, otherwise `se4` and `se13` get NaN inputs mid-evaluation.
9. Print `p_book_ts` staleness (the share of unchanged book timestamps across consecutive polls).
10. CH223 F: consider a binding point-estimate condition (β̂_twin < β̂_lead); it costs little power and guards against W7
    being only a convention.

## Rulings on §11
- Q1 independence: sound once must-fix 1, 2 and 6 are made; do not wait for post-11-03 data.
- Q2: the move to `|dk1| >= 0.5c` is a correction (a one-tick Kalshi quote change is 0.5c of mid; the quantiles come from the
  public pilot); keep S4.
- Q3: see should-fix 2. Q4: keep the F labels, plus should-fix 10. Q5: `OF = 1 + ρ_x1` is correct for MA(1) errors.
- Q6, Q7: accept. Q8: endpoints-only accepted; the two-part bot gate is adequate. Q9: route 1, with must-fix 2 and
  should-fix 7 and 8. Q10: accept. Q11: see the checks above.
- CH222 failing its floor at the low planning end: keep it; CD10 removes it cheaply, and Holm counts it only if it survives.

## Answers to §12
1. Keep the full population as primary; *floor-driven* stays a label. 2. Keep `|move|`; M2 reported. 3. Keep +20 minutes
(E009's primary, fixed before its result). 4. Count distinct events, plus G_eff (should-fix 6). 5. Fix the scope at the seal
(must-fix 1); the with-sports print is for later families only. 6. Hand-verified pairs stay a label. 7. Hour dummies are
enough; add diurnal volatility to W2. 8. Keep 3.47.

## Not verified
Host disk, the 11-16 cap projection and the refresh duration on the host; whether the host's verdicts file equals the repo's;
uniqueness of seeds and queue ids; completeness of the census span's quote files beyond the 10-22 resize record (2 cycles
missed, no grid origin lost).
