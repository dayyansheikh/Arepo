# CB18 challenger review, round 1, 2026-10-20 ~19:40Z (science-reviewer; saved by the orchestrator)

**Overall: REVISE.** Part `pre` must not be committed and no census may run until findings 1-7 are fixed (routing rules
bind when `pre` lands; findings 1-2 are known-defective gates carried over from LT4). Per family: CB18-S REVISE (2-6);
CB18-P ACCEPT_WITH_CHANGES (2, 8; likely to drop at census); CB18-R DROP the counted LT5 member (1), race map ACCEPTED;
CB18-F ACCEPT_WITH_CHANGES (11); CB18-M ACCEPT_WITH_CHANGES (10). CH178 exclusion (§0.2) accepted.

1. **HIGH** CB18-R reuses the residualised donor gate that LT4 R2 recorded as failed (corr 0.5: 0.085 vs 0.075; "drop rather
   than redesign"); same cap = a redraw. Drop CB18-R as counted; keep the map; revival only with a new null passing a size
   check at the census-measured correlation, declared before the census. §0.1, §4.3 still call E023/E024 live: correct.
2. **HIGH** DE formula `1 + (m_W - 1) 0.02` treats 0.02 as an estimate (LT4 R2 finding 4): `DE_gate = max(3.0, computed)`;
   inflate the RS-1 proxy SE by `sqrt(max(3, DE_W/DE_census))`; no UTC-day way (G = 2) in the census SE; apply §2.4's 1.5
   factor and the 1/n0 term in RS-1 (§4.1 :417-421): pessimistic MDE ~1.58c at SD 6c, DE 3 (not 1.06c).
3. **HIGH** "silent" may be uncaptured numeric fields changing (`chg_*`, rolling volumes, outcome prices) -> proxy for recent
   volatility: add byte-equality flags for `chg_1h/1d/1w` (flags only, never parsed; `chg_only` class reported); controls
   |mid_k - mid_{k-3}| and |mid_k - mid_{k-12}|; census count of silent units by flag status.
4. **HIGH** no size check with overlapping targets (Y spans 12 slots): binding scenario with MA(11) target in slot steps,
   persistent clustered silent label, level-2 (7-day) stratum.
5. **MEDIUM** lookback to k-13 breaches the 10-26T00Z floor (first origin 10-27T00:31Z needs 10-25T22:31Z, inside the CB13-T
   HOLDOUT [10-21, 10-26)): cap at 11 or move S_18 one slot; census needs k-12 into the missing 10-14 00:31-10:31Z
   captures: pin and declare unavailable (unknown, never 0).
6. **MEDIUM** undisclosed prior use of `updated_at`-derived ages (`ml_quote_staleness_h`, `quote_age_s`;
   CREATIVE_HYPOTHESES_2026-10-22.md:106,331; `ml_panel.py:282`): disclose in §1.1/§1.3.
7. **MEDIUM** q0501 cannot satisfy the pins: 36 of 92 files (9 of 23 samples) are in `data-20261019-dsheikh` (not listed);
   `plan.json` pinned but no glob restores it.
8. **MEDIUM** CB18-P collider: active frame sampled by volume quartile at k+1 includes the state window's trades:
   restrict to markets in the frame at both k and k+1; add k+1 sampling-stratum dummies (or 1/pi weights).
9. **LOW** `uma_resolution_statuses` needs an explicit whitelist exception (`cb13_common.py:137`); exclude units whose status
   at k is not the empty literal.
10. **LOW** CB18-M: fold [0, 0.01) and (0.99, 1] into symmetric |mid - 0.5| bands; disclose the 10-14 gap stretches exit lags.
11. **LOW** CB18-F: B only from the dated venue observation, never q0505's churn shares; if not in the candidate set, rerun
    the census as counts only.

Answers: Q1 accept sweep as decision time + strict stamp rule (disclose dormant-books-only population); Q2 admit `chg_*`
flags; Q3 keep flag with finding 9; Q4 keep binding Lee bound; Q5 RS-1 first, both MDEs in the routing record; Q6 accept
hash thinning; Q7 fade vs none primary; Q8 a 42-day LT5b branch only if declared in part `pre` now; Q9 7-day level subject
to 4; Q10 map: label same-second races "same block" if `ts` is quantised; Q11 if R revived, Holm across E016, E018, R;
Q12 accept with 11; Q13 3.6 days enough; Q14 accept CB17's convention.
Sound: rules 10-25T18:00Z -> S_18 10-27T00:00Z (24 h rule met); arm hash fixed before data; unavailability a status in
the denominator; 0-2 counted tests with Holm; no outcome fields read; CB18-P MDE arithmetic correct.
Could not verify: release tags holding 10-16/17 captures and sweeps; whether 3-day sweep deletion is enabled; releases for
10-26..11-24; LT4's REGISTERED_UTC; Gamma `updated_at` semantics; overlap with LT2 E012/E014.
