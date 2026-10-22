# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-22 02:05 UTC+1 (01:05Z), signal-engine autopilot session 9

## In plain English
- **I found a timing flaw in one feature family and contained it.** Direction forecasts are scored from the market's
  price at the capture (~hh:31Z). The `book` (order-book) features are read about 7 minutes later. By then, about a
  third of the markets that move within 2 hours have already moved. A model holding book features can therefore get
  credit for a move that has already happened.
  - What changed: three models that use book features (`se7_lgbm_all`, and the hidden `se3_lr_book` and
    `se14_lgbm_movetype`) can no longer be promoted to champion. They are still scored and shown.
  - The bar for the other challengers stays exactly as strict (K stays 3). The science review accepted the fix after
    two rounds.
- **Two candidate ideas closed.**
  - CH200 (`sweep2`) has the same flaw, but worse, so it was declined.
  - CH199 (resolution-source class) failed its own coverage test: 19.9% of non-sports markets have a source, against
    a 30% minimum.
- **The /lab page now shows the promotion rule's progress** for each challenger: days scored, both lower bounds, and
  checks passed. Ineligible models show "Not eligible". PRs #26 and #27 are merged and live on Vercel.
- **The experiments track's LT7 embargo requests (round 4) are applied.**
- Nothing has been promoted; the earliest possible date is about 11-04. No edge claims. The UI wording stays
  "signal strength".

## Live state (host)
- **Code:** deployed 8ea00bd (~00:55Z). Host check: 18 models load, the rule is `se-promotion-v2`,
  `PROMOTION_INELIGIBLE` lists se7, se3 and se14, and book and movetype are embargoed until 12-31.
- Promotion-eligible non-embargoed challengers: se1 and se17. K stays 3 (se7 still counts).

| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (broad, ineligible), `se17_lgbm_mm_900k` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte` | 11-14 |
| `se15_lgbm_surprise` | 11-19 |
| `se2_lr_flow`, `se11_lgbm_flow`, `se8_lr_event`, `se9_lr_rewards`, `se10_lgbm_event` | 11-22 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible) | 12-31 (round 4) |

  - Tokens with no model yet: `chg1d_x_liq` (11-14), `hollow` (11-18), `wallet_skill` (12-07), `vote`, `clips`,
    `deadline`, `siblings` (12-09), and from round 4 `resist`, `capath`, `mm_fresh`, `deepbook`, `absorbed`, `ivr` (12-31).
- **Queue:** both jobs are healthy and waiting for their due times (rc 75 = not due yet).
  - `q0512` refit: ~10-22 07:34Z. First fits for se14, se15 and se17.
  - `q0513` score: ~10-22 11:40Z. The first `dashboard.json` with the `promotion` block, including `eligible`.

## Changes this session
1. PR #26 (from session 8's unfinished worktree): /lab promotion-rule card. PR #27: "Not eligible" state. Both had full
   validation: vitest 227, tsc, lint and build clean; e2e 120 passed, with 1 known local-DB `replay.spec` failure, as in #23.
2. `config.PROMOTION_INELIGIBLE` (append-only, dated), applied in `promotion.evaluate`. It still counts in K. There is a
   new `eligible` / `ineligible_since` field in the decision and in the dashboard. DESIGN_V1 section 21 and a
   features.py docstring fix. 2 new tests and 1 extended; 44 engine tests pass; ruff clean.
3. Embargo round 4 (LT7) in `config.EMBARGO` and the DESIGN_V1 §8 table, with the builder's reply in CANDIDATES. Ledger lines added.
4. CANDIDATES builder table: row 17 (CH199, killed at census), row 18 (CH200, declined).

## Next actions
1. After the ~07:34Z refit: read `logs/fits-20261022.jsonl`. Expect se14, se15 and se17 `ok` and se16 `no_fit`.
   Check runtime and peak RSS against the 10800 s / 2200 MB limits, then the next tick's se17 predictions.
2. After the ~11:40Z score: `leaderboard/latest.json` day 2 (`gain_twoway` computable) and the `dashboard.json`
   `promotion` block. se7 should show `eligible: false`. Check /lab.
3. After the owner's resize (2 OCPU / 12 GB, 02:40Z): consider LightGBM `num_threads` 2 (now hard-coded 1 in
   `learners.py`; a new fit only, no new spec) and a rows step if se17 gains over se1.
4. Honest replacement for book information: a `book` v2 family from the previous pass's last sweep, strictly before the
   origin, as a new frozen spec. It isolates book, so it stays under the 12-31 embargo. Optional development diagnostic:
   se7 against se1 on a sweep-anchored label (information only; cannot restore eligibility).
5. Around 10-27: se8, se10 and se16 start fitting. Around 10-28: the LightGBM `res_7d` fits.
6. Remaining engine-first ideas: CH198 `theta` (needs LT6 D's classifier; `deadline` and `movetype` tokens) and CH201
   rewards-v2 (sweep-1 depth, so check it against section 21 before building).
7. Housekeeping (needs approval): remove worktrees `/Users/DayyanSheikh/Projects/astrolabe-lab-se` and
   `astrolabe-lab-se-promo` (both merged), plus `/tmp/se_dev` (~410 MB) and `/tmp/se_e2e`.

## Notes for the other track
- Round 4 applied as filed (all 12-31). No interaction attribution exists. The `momentum` family totals stay shown.
- `deploy.sh` printed `rm: cannot remove ~/arepo_trials_from_mac.jsonl` at its last step (00:55Z). The code had
  already synced (the host is at 8ea00bd), and it pulled 5 host trials rows into the main checkout's `trials.jsonl`.
- No queue jobs were touched.
