# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 13:41 UTC+1 (2026-10-30 12:41Z), signal-engine autopilot session 36

## In plain English
- **Two new signal ideas were tested and both failed their entry check, so nothing new was added to the model line-up.**
  Each was a counts-only check fixed in writing before it ran; no prices, outcomes or scores were looked at.
  - **Rule edits (CH228, `ruleedit`):** "how long since this market's rules or end date were last changed". Edits are
    too rare. Only 0.36% of the markets we cover had a rule edit in the past week, and 0.37% an end-date move. The bar
    was 0.5%. Most recorded end-date moves are on markets that have already dropped out.
  - **Parent-event siblings (CH237, `parentsib`):** "what the other contests under the same parent event (say, the
    other states in a national race) just did". Outside sports almost no market has a parent event (0.14%, against a
    5% bar). In sports two-thirds do. A sports-only version would be a new idea, and it waits on your open decision
    about sports scope.
- **Engine speed-up (no change to any number):** the engine re-read the whole rules stream on every run (22 s, growing
  daily). It now keeps a ready-parsed copy of each finished day. On the server a run now takes 1.8 s instead of 22 s,
  with values checked identical. The copy is 19 MB.
- **New alarm:** if the rules stream stops updating, the engine's input monitor now raises a `stale_stream` alert. Before
  this, a stopped stream would have gone unnoticed, because the old rows stay in place.
- **Leaderboard today (development, 10 days scored, not a claim):** every tree-based (LightGBM) challenger beats the
  simple logistic champion on the main 2-hour target every day, by about 0.045 in log loss. No promotion is possible
  before 14 scored days (~11-04).
- **Still needing the owner:** disk retention by ~11-15 (session 33; Next actions 3); a public website version of the
  feed; the sports-scope decision (it now also gates a sports-only parent-sibling family).

## Live state (host)
- **Code:** main `fad48d35` deployed 12:1xZ (`stream_cache.py`; `rules_text.py` sha `2c82c8a4...`, `uma_params.py`
  `0b915145...`). Commit `4b1b5e48` (input-monitor stream check) **merges and deploys after the 12:31Z pass ends**
  (see the deploy line below).
- **Engine `status`** (12:0xZ): 212 captures, 198 fits, 11 leaderboards; input monitor ok, 0 alerts; disk 5.51 GB of 16 GB
  (0.344).
- **Score job q0513** ran 11:50-12:03Z: leaderboard `20261030T115004Z.json`, 10 days scored, K 15, no promotion (every
  candidate fails `c1_days`).
- **Queue:** q0518 (se17 + refit_full dev probe) queued at priority 30 behind the other track's cpu jobs; q0512 refit in
  retry_wait (next window ~13:40Z). Nothing of the other track's was touched.
- **Parse cache:** `signal_engine/cache/stream_parse/{rules,umaparams}/`, one pickle per closed day file (19 MB). Cold
  22.7 s, warm 1.8 s on the host, identical values for both readers.

## Embargo list (unchanged; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full`, `se27_lgbm_stress`, `se28_lr_rules`, `se29_lr_uma`, `se30_lr_framein` | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **DESIGN_V1 §43 `ruleedit`:** definitions, `rule_edits.py` and the census script were committed `c1eb4c77` before
   the run (12:04:39Z). **Killed** (0.36% / 0.37% < 0.5%). The reader and its test are kept as the census record, not wired.
2. **DESIGN_V1 §44 parse cache** (`stream_cache.py`; optional `cache_dir` on `rules_at` / `uma_at`; the builders pass
   `<engine>/cache/stream_parse`). Tests cover cold, warm, append, torn entry, today's file and None. 430 engine tests
   passed. Deployed `fad48d35`.
3. **DESIGN_V1 §45 `parentsib`:** definitions, `parent_sib.py` and the census script were committed `ec352da0` before
   the run (12:17:21Z). **Killed** (non-sports parent share 0.14% < 5%). The code is kept as the census record, not wired.
4. **Input monitor `stale_stream` rule** (§44 companion): 7 input-health tests and 439 engine tests passed; commit `4b1b5e48`.
5. CANDIDATES rows 33-34; builder notes on `attn` (deprioritised: the 10-22 probe shows 0.04% comment changes in 2 h,
   against a 2% line) and `disp` (blocked by §37 rule (a) as written). Ledger entries for both kills and §44.

## Next actions
1. **Deploy `4b1b5e48`** (merge into main, then `deploy.sh chore/arepo-claude-setup`) once the 12:31Z pass has ended,
   if this session did not already. Then confirm `state/input_health.json` carries `streams.gamma_rules.status` ok
   with a lag of ~1.5 h, and that the 12:31Z capture's `rules` / `umaparams` / `framein` tables were built
   (`aux-20261030.jsonl`) without errors.
2. **After the 10-30 refit (~13:40-15:20Z):**
   - confirm the fits of se27 (3 directions), se28, se29 and se30, or `insufficient_coverage`;
   - check that the fits carry `.json.gz` artifacts, and peak RSS against 3,400 MB.
3. **Reading rule for se28 / se29 (§42 item 3):** from ~11-18, compute the per-day `dir_2h` gain difference against
   se30, pooled and by category group. Credit needs the pooled 95% interval above 0 and 2 of 3 groups positive.
4. **Disk:** read `status` -> `disk` each session. If the owner approves, move the engine `deferred_rules` into
   `rules` and add `signal_engine/aux/` at 45 days. Do **not** activate the proposed 14-day rule for
   `stream_gamma_rules/`: three families need every day file (the parse cache does not replace the files).
5. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
6. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written and record the decision.
7. **~11-13:** se27's 14 days. If it beats se1 on `dir_2h`, register the slotfac-only reference arm (§36) before any
   credit to stress.
8. **Candidate pool** (scout inventory 2026-10-30):
   - Designable now: `shock` (CH254, favourite collapse spreading to category favourites), `headline` (CH255;
     two-member events held to 2027-01-03), `rowq` (CH217).
   - `disp` only as a lagged (k - 1) redefinition with its own section and review.
   - `xent` needs an entity matcher and confirmation that the PredictIt / Smarkets feeds are collected.
   - `batch` is held for the LT13 freeze.
9. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq` and `dispgap` later,
   and `flow` before 11-16; check `rewards` against E022 before 11-18.
10. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
11. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
12. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*` and the `/tmp/se_*` scratch (Mac and
    host, including `/tmp/se_uma/`, `/tmp/se_ruleedit/`, `/tmp/se_parentsib/`) and old backfill logs.

## Notes for the other track
- Merged your tip twice and deployed main `fad48d35`. The ledger conflict was resolved by keeping both entries (yours
  first). Nothing of yours was changed.
- The two censuses ran read-only at nice 19 (5 s each, < 400 MB). The cache warm-up ran under the collector lock
  between passes.
- `stream_gamma_rules/` still needs every day file since 20261020. Please do not activate its proposed 14-day
  retention without telling this track.
- No job of yours was paused, cancelled or re-prioritised.
