# M3 (CH274) challenger review R1

Text reviewed: `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M3_CH274.md` at 69c32cff (sha256 `61bd55da…086d1a`, 925 lines). Also read: R19, the round-20 file §2 C, §2 E and §3, the CH269 map, the later M1/M2 checks, `costs.py`, and the CH276 code at `feat/ch276-map` d3795a38. I edited nothing.

## Verdict: GO_WITH_CHANGES

The causal design holds up. Units are chosen only on state visible at k, the follow-up is blind, and units are disjoint from M1 and M2 at the (market, capture) level by construction (E6 vs M1 E2, E7 vs M2's overdue rule; §2.3). The problems are elsewhere:
- three estimands quietly use a denominator that depends on post-k outcomes;
- §17 claims to carry every defect class caught on M1/M2, but six later-caught ones are missing;
- a sibling job (CH276) will read this design's own outcome before the freeze.

All of these can be fixed in the text before J0 runs.

## MUST

**1. Void 12.2 is unscoped and will fire by design (repeats M2 final-verify MUST 2).** At l.717, M1's 2027-01-15 analysis and the engine both read resolutions before 01-29. Replace the opening with: "any read, **by an M3 job or for M3's purposes**, of a resolution, label, Gamma outcome field, follow-up file, proposal-set file or any data from after a unit's k before `READOUT_UTC` …".

**2. Six later-caught defects are absent from §10.2/10.3 and §17.** None of the following appears in the text (grep finds nothing):
- **J2 at `END_UTC + 6 h` (l.657)** repeats M1 R-diff MUST 2. Use: "J2 not before 2026-12-15T07:00Z, and it refuses unless all 252 slots are decided."
- k − 1 must be taken from the chain status, not the capture list (M1 R-diff MUST 1).
- Every on-time capture for a slot already recorded missing must be recorded as `delivered_after_missing_recorded` (M1 fix-diff MUST 1).
- Ties use the `(start, id)` key (M1 fix-diff SHOULD 1).
- The rule-ledger lookup takes the latest commit `ts`, not the list position (M2 final SHOULD 2).
- The host dry run uses an end-of-window-sized state: near-seen set, ever-seen set and rule ledger after about 66 days (M2 final SHOULD 3). Also add: "`spec_sha` = sha256 of this file at the registration commit" (M2 final SHOULD 4).

Add one §17 row for each, and add the M1/M2 diff-check reviews to §15.

**3. Three denominators depend on the follow-up (a post-k selection).**
- **Early share (l.357):** "determinate if S observed or `t_last >= E_k - 2 h`" drops the long-dated units with no S, and those are mostly not early. Replace with: "The early share and the three-way partition are computed over units with `H_k < 43 d` (k-visible). For these, `E_k + 24 h` falls before `t_last` by design. A residual `indeterminate` (missing final captures) is counted and bounded." S4's bins become `[1 d, 3 d), [3 d, 14 d), [14 d, 43 d), >= 43 d`. The reason is follow-up length, decided before any data.
- **A99 (l.368):** "A99 share = units with A99 observed before S and within 30 d of `t_d`, over all units." Every unit is then determinate, because every unit has at least 45 d of follow-up. The slots-to-A99 figure is labelled "conditional on A99".
- **`g` (l.425-429):** quantiles over S-observed units only overstate `g`. Define `V_i = ask_f,i · W+_i / (1 - ask_f,i - fee_i)`, censored at `ask_f,i · (t_last - t_d) / (1 - ask_f,i - fee_i)`. Take KM quantiles of V and report `g_q = 100·8760 / V_(1-q)`. The numerator is always positive because ask ≤ 0.999. A quantile that is not reached prints "< bound".

**4. The bracket claim "true time in (W−, W+]" is false (l.322-333).** `t_j` is the capture start, but the state is observed at row receipt, later in the capture. Replace with:
- "`W+ = t⁺ − t_d`, where `t⁺` is the sidecar row's `received_utc` at `j_S` for P, the row's for C-by-`closed`, and capture `j_S`'s manifest `finished_utc` for C-by-absence."
- "`W− = max(0, t⁻ − t_d)`, where `t⁻` is the market's row `received_utc` at `j_S'` (`t_d` if `j_S'` = k)."
- "If a receipt is missing, fall back to `finished_utc` for `t⁺` and the manifest start for `t⁻` (counted)."

**5. CH276 collision (not addressed anywhere).** CH276's line 7 (`ch276_map.py:471-535, :1158`) applies a near-identical crossing rule to pre-window data. It reads the proposal flag after k and prints a `proposed_before_end_date` share by class, tier and hours-to-end. That is a pre-window version of estimand 2. Its gate is ≥ 30 crossings a day (`:69`; round l.803), while M3-J0 rule (a) uses 25. The status-block claim (l.20-23) that only J0 can change this text is therefore not yet true. Add: "M3's only population gate is M3-J0 rule (a). CH276's `ch274` line is superseded for M3, and this is recorded in the ledger before q0760 runs. The designer's response and every §18 ruling are committed before q0760's output is opened. After that, CH276 changes nothing in M3, and the freeze commit lists any CH276 line the designer has read."

**6. J0 rule (a) and coarse rule 1 contradict each other (l.590, 679).** At 25 to 47 crossings a day there is no extension, yet N < 1,000 is near-certain. Set "(a) median full-day units < 48 (= ⌈1,000/21⌉) → 42 days", declared now, before any count. Disclose that J0's one-day fold overstates the count (l.586-589).

**7. Status semantics: be robust, do not switch definitions.**
- Drop J0's status-semantics line (l.583-585). Siblings of hypothetical units can be hypothetical units after their own k, so the line reads their post-k status. CH276 line (1) already covers the question.
- Add to the headline line: "the same figure on S8 = 1 (single-open-member events), where market and event semantics coincide". P stays as defined, whatever CH276 shows.
- Disclose that under per-event semantics, "by-date" ladders would shorten W (an earlier rung's proposal would also fire P for later rungs).

**8. `rules_gap` is ambiguous and could wipe out S2 (l.276-278).** As written, one missing day file could reclass every unit. Use: "`rules_gap` applies only to a unit with no visible record when at least one day file in [`RULES_FIRST_DAY`, k's day] was never merged. A unit with a visible record keeps its class (disclosed)." Add an ops guard to the registration commit: no `gamma_rules` day-file retention may activate before every M-recorder's first pass.

**9. Headline (see Q3).** Adopt `F_S(7 d)` and recast coarse rule 2 as "the event-bootstrap 95% CI of `F_S(7 d)` wider than 10 points".

## SHOULD
1. The day-block bootstrap splits ladders (l.460). Either assign each event to the UTC day of its first unit's k, or drop it and disclose that common follow-up shocks (Christmas) are not captured.
2. Planning: cite CH269's 821 non-sports ex-crypto proposals a day as the inflow ceiling, and M1-J0's units per event (586/94/48/12) for the design effect. Fix the 1,050-3,150 vs 1,000-3,000 mismatch (l.59 vs 693).
3. Scheduled units were 7 of 1,024 in M2-J0, so D1's `log(W50)` ratio will mostly print thin or "not reached". Define D1 as the `F_S(7 d)` difference within S4 bins.
4. L2 returns 0 for `geopolitics` (docs rate 0.0, `costs.py:52, 93-104`), so "rate 0 not trusted" fails there. Disclose this (kept for consistency with M1/M2).
5. "LT15" means CH267 at l.128 but CH275 in round 20 l.864. Name these objects by CH id.
6. Widen J3's retries (3 passes over 7 days) so that a Gamma outage cannot void the W headline through the coverage floor.
7. Sweep coverage is likely tiny (the CH276 code cites M1-J0's 0.73%). Consider dropping estimand 6 and printing "capacity: not measured (no book read)". This cuts J1's inputs and memory use.
8. Add a `created_at_after_k` class to E8.
9. §18 lists 12 questions, but the ledger says eleven.

## Rulings on §18
- **Q1 (prices in the blind store): ACCEPT.** Status strings are already outcome content, so bid/ask add no new risk class. Same procedure and hashes, and use MUST 3's fixed-horizon A99.
- **Q2 (`t_d` without the sweep): ACCEPT.** R19's sweep item was specific to CH263's route. Record the gap and keep capacity labelled "read minutes after `t_d`" (moot if SHOULD 7 is taken).
- **Q3 (headline): use `F_S(7 d)`, over all units, event-bootstrap CI with CR1 beside.** Every horizon up to 30 d is uncensored because minimum follow-up is 45 d, so it is a plain proportion. The pooled KM median mixes long-dated, clock-bound NO-deadline units and is likely to be "not reached" or more than 2× wide. W50 and W50− go in the same line.
- **Q4 (C at first absence): require confirmed absence.** C-by-absence is dated at the first absent capture j only if the next processed capture also shows the market absent or closed (or j is the last capture). Otherwise count `absent_flicker` and the wait continues. `closed` true needs no confirmation. No 2 h is added.
- **Q5 (near-certainty state):** keep the mid clause (a programme constant) and the one-sided fold. The survivorship line counts what the fold removes.
- **Q6 (LT15's reserved object):** no conflict. Any later test on class × hours-to-end, for any target, is `informed (M3)` and reports 13 splits, 84 cells and 5 contrast numbers.
- **Q7 (class reader):** keep the five-way S2 with S3 beside it. Do not change the lexicon.
- **Q8 (coverage floor scope):** keep the whole-measurement void, because R19 condition 5 binds. Mitigate with SHOULD 6.
- **Q9 (long-dated units):** keep them in the population. The Q3 headline removes the censoring problem, and the early share follows MUST 3.
- **Q10 (`g` per dollar): ACCEPT.** Use MUST 3's censoring treatment.
- **Q11 (age clock):** ACCEPT, with SHOULD 8.
- **Q12 (host load):** feasible only with the three J1s run serially within the 2 h cadence. The dry run must report peak memory at end-of-window state size and wall time per pass. Precedent: CH269 peaked at 558.8 MB against a 450 MB spec.

## Feasibility
Freezing by 11-16 is realistic. M2 went from J1 code through J0 to freeze in about a day, and M3's J1 can be built from `m2_j1.py`'s chain and rule reader (the pattern lines match those in `census_map_ch269.py:65-66` and `rules_text.py:24-25`). The risk is 11-17 to 11-22: M1, M2 and M3 all need J2/J3/analysis code, code-freeze checks and host dry runs from the same reviewer and host. To fit:
- Share J3 with M2 (same read-out date, same fetch).
- Drop J0's semantics line, the day-block bootstrap, the Aalen-Johansen machinery (uncensored proportions up to 30 d are enough) and, optionally, capacity.
- Keep the ask path (it costs two fields). Use its declared fallback only if J1 slips past 11-12.

## Not verified
- Whether an open market can be absent from a `complete` capture (the capture universe's filters, pagination flicker).
- Market vs event status semantics.
- Whether host `gamma_rules` retention is off.
- Whether q0760 has run.
- The CH276 code beyond lines 50-78 and 471-560.
- Every population count. No M3 code exists yet.
