# CB18 challenger review, round 2, 2026-10-21 ~00:55 UTC+1 (science-reviewer; saved by the orchestrator, autopilot)

**Verdict: ACCEPT_WITH_CHANGES.** All eleven R1 findings resolved (F1 CB18:31,193,401-407,575-584,695; F2 :202,252-260,
354-367, MDEs 1.58/1.77/2.24c and 0.71/1.00c recomputed and matching; F3 :110-117,452-457,467,484-487; F4 :236-246; F5 :128,
321-329; F6 :155-161; F7 checked against the committed catalogues: q0500 67 captures + 48 sweep dirs, none in two releases;
q0501 23 samples (2 + 12 + 9), the unsealed 10-17T04:40Z sample only in -18-2, not listed; per-file hashes not checked;
F8 :533-554; F9 :460-463; F10 :803, q0506; F11 :804). Five changes must land in part `pre` before any census.

## New findings
1. **MEDIUM:** censuses read inside J4-R [10-16, 10-21) without saying so (S, F read 10-16 captures/sweeps; P, R read
   10-16/17 samples, CB18:314-318); CB18:128 says J4-R is "untouched" (true only for window paths). CB17 refused census
   rows >= 10-16 (CREATIVE_BATCH_17.md:253,281); LT3 refuses J4-R only for maker mark-out objects (LIVE_TESTS_3.md:529).
   Disclose, and state that no census object is a mark-out. HOLDOUT [10-21, 10-26) untouched (census cut-off
   10-17T22:31Z, window floor 10-26T00:00Z).
2. **MEDIUM-LOW:** size scenarios miss the F3 confound (label independent of innovations in §2.3): add a scenario
   (reported at minimum) where the label tracks a latent time-varying volatility that the two |mid| controls capture
   imperfectly.
3. **LOW:** P's power gate ambiguous: §2.4 (:263-264) proxy SE vs GP5 (:390) formula only; pin which binds (suggest max).
4. **LOW:** P look-back: :317 "k-12 from 10-15T12:31Z", but k-12 of the first pass (10-16T00:31Z) is 10-15T00:31Z; fix the
   label or the restore range.
5. **LOW:** q0512 waits for E011 (:135) but not E012 (overlapping population and 24 h target, :146-150; E012 analysed
   on/after 11-13T12:00Z, LIVE_TESTS_2.md:27): add the E012 wait or justify.

## Run the censuses or close now: run them
CB18-S misses on the CB route but RS-2 (LT5 28-day) meets its floor at planning numbers (0.71-1.00c vs 1.0c, :371);
GS1/GS2 (`updated_at` as an indexer clock) is a cheap counts-only kill. CB18-P is expected to drop (GP5 needs ~7.7x the
guessed fade rate), but its census is cheap (q0501 is needed for the R map anyway) and measures the unprobed fade rate;
uncounted; GP5 stays at 0.5c. Commit `pre` and run q0502-q0506; if coding time is short, cut P first and record it
"not run (power, planning)". No floor, alpha or gate changed.
