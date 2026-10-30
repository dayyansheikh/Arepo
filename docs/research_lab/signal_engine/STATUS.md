# Signal engine: status (rewrite each session; do not append)

**Last updated:** 2026-10-30 06:10 UTC+1 (2026-10-30 05:10Z), signal-engine autopilot session 34

## In plain English
- **New signal family: what a market's rules say.** The engine now reads each market's rule text, from the hourly
  `gamma_rules` stream, as it stood before each capture. It turns the text into nine simple flags and numbers:
  - is it a scheduled event (a game, an election, a data release)?
  - is it a "will X happen by <date>" deadline question?
  - does it use "at least / or more" wording?
  - does the question name a price or a percentage?
  - how many source websites it cites, and how long the rules are.
- Coverage: 35% of all markets the engine scores, and 70% of non-sports markets.
- A new challenger, **`se28_lr_rules`**, adds these columns to the champion's simple (logistic) model. It is
  logistic on purpose, so it cannot combine the rule type with time-to-close: that combination is reserved for a
  planned live test (LT15).
- **Honest-reading rule (from the independent review).** Training data before 10-20, when the stream did not exist
  yet, could flatter se28. So **no gain is credited to the rule text before ~11-18**. Earlier se28 scores are shown,
  labelled as development.
- Quality check, information only: I hand-read 40 rule texts. The "scheduled" flag was right 10/10. The borrowed
  "barrier" word list was right only 3/13, because standard boilerplate fooled it. So I added a stricter deadline
  flag. It was right on the same sample, but that check is in-sample. Disclosed.
- No model, target, score or promotion rule changed. 29 models now. No embargo applies.
- Still needing the owner:
  - **disk retention by ~11-15** (session 33; details below);
  - a public website version of the feed.

## Live state (host)
- **Code:** main `b5062eed` deployed (host `rules_text.py` sha `0bdec2ee...`). **`rules` backfill done** (one-off
  `features --max-items 20` under the collector lock after the 04:31Z pass: 40 s, 335 MB peak): 209 tables, one per
  capture, no errors. Pre-stream captures all-NaN; `rc_has` 0.035 on 10-21 04:31Z (top-3,000 frame only), 0.225 on
  10-22, 0.345 on 10-30 04:31Z (last slot 03:00, correct by the poll-finished rule). se28 can fit at the 13:40Z refit.
- **Input monitor** (03:06Z): status ok, no alerts. **Refit `q0512` / score `q0513`:** daily, healthy (`tempfail` =
  not due); next refit ~13:40Z. **Probe `q0518`:** still queued (priority 30).
- **Disk:** engine 5.24 GB of 16 GB (no warning); `research_lab` 36.0 GiB of the tick's 50 GiB cap; host 33 GiB free.
- **`gamma_rules` stream:** day files 20261020..20261030 contiguous on the host (the new `RulesGap` guard needs them all).

## Embargo list (unchanged; se28 not embargoed; LT12 tokens `mirror` / `mixedlad` / `attrlimit_lt12` to 2027-01-03 hold no model)
| Model | Embargoed until |
|---|---|
| `se0_champion_lr_mm` (champion), `se1_lgbm_mm`, `se7_lgbm_all` (ineligible), `se8_lr_event`, `se10_lgbm_event`, `se17_lgbm_mm_900k`, `se18_lgbm_all_b0`, `se20_lgbm_crypto`, `se21_lgbm_hwm`, `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full`, `se27_lgbm_stress`, **`se28_lr_rules`** | not embargoed |
| `se4_lr_xvenue`, `se13_lgbm_xvenue` | 11-04 |
| `se5_lr_tte`, `se12_lgbm_tte`, `se22_lgbm_dispgap` | 11-14 |
| `se2_lr_flow`, `se11_lgbm_flow` | 11-16 |
| `se9_lr_rewards` | 11-18 |
| `se15_lgbm_surprise`, `se23_lgbm_dormant` | 11-19 |
| `se16_lgbm_participation` | 11-25 |
| `se6_lr_wallet` | 12-07 |
| `se3_lr_book` (ineligible), `se14_lgbm_movetype` (ineligible), `se19_lr_book0` | 2027-02-14 |

## Changes this session
1. **DESIGN_V1 §41** (definitions committed `fd4c8bcb` 04:14:24Z before the census; results, audit, review appended).
2. **Census** (counts only; `census/se_rules_census_2026-10-30.{py,out}`, `_run2.out`): `rc_has` 0.354 of 51,017
   eligible rows, so the family passes; all nine columns inside their keep lines.
3. **Code:** `signal_engine/rules_text.py` (parse, poll-finished clock, `RulesGap`), aux family `rules`
   (`se-aux-rules-v1`), `Paths.rules_stream`, spec `se28_lr_rules` + registry pin. 6 new tests; 88 engine tests pass;
   ruff clean.
4. Science review: REVISE (minor), causality and embargo PASS. Both must-fixes applied (reading rule; missing-day guard).
5. Ledger entry; CANDIDATES row 31.

## Next actions
1. **Done this session:** deploy + `rules` backfill (see Live state). Each new capture's table is built by the tick.
2. **After the 10-30 refit (~15:20Z):**
   - confirm se27's 3 direction fits and se28's fits (or `insufficient_coverage` if the backfill had not finished);
   - check that the new fits carry `.json.gz` artifacts, and peak RSS against 3,400 MB;
   - check that `aux` logs show no `RulesGap` / rules errors.
3. **Disk:** read `status` -> `disk` each session. If the owner approves, move the engine `deferred_rules` into
   `rules` and add `signal_engine/aux/` at 45 days. **Do not** activate the proposed 14-day rule for
   `stream_gamma_rules/`: se28's tables would then fail with `RulesGap`, unless the reader first gains a
   release-restore path.
4. **Input monitor:** read `state/input_health.json` each session. Later step: a stream-staleness line from the
   tables' `rules_last_slot`.
5. **q0518:** when it has run, read `SE_DEV_REFIT_FULL` and apply §34 as written.
6. **~11-04:** first promotion reads (se1 / se17 / se18). Apply `se-promotion-v2` as written; record the decision.
   se28 counts in K from today.
7. **~11-13:** se27's 14 days. If it beats se1 on `dir_2h`, register the slotfac-only reference arm (§36) before
   any credit to stress. **~11-18:** se28's first creditable `dir_2h` read (§41 reading rule).
8. **Candidate pool:**
   - CH269's map is now recorded (experiments track, `reviews/CH269_MAP_2026-10-30.md`). Read its class split
     against the engine's `rules` levels.
   - CH207 `umaparams` (bond / liveness / reviewed dates from the same stream) is the next cheap family.
   - Round-18 `attn` still needs CB17's use of the comment count checked first.
9. **Before 11-14:** check that LT2's analysis (q0461) has run. If not, move `tte`, `chg1d_x_liq`, `dispgap` later,
   and `flow` before 11-16; check `rewards` against E022 before 11-18.
10. **Census drops:** CH214 at LT9 -> `book` / `book0` dates; CH232-CH234 -> LT11 tokens; CH245 / CH244 -> LT12 items.
11. **LT13 freeze:** apply `payreturn`, `batch` and `attrlimit_lt13` at the freeze, before any isolating challenger.
    **LT15:** if its freeze requests `close` over the class levels, move se28 under it (never earlier).
12. Housekeeping (needs approval): remove merged worktrees `astrolabe-lab-se*`, `/tmp/se_*` scratch (Mac and host)
    and old backfill logs.

## Notes for the other track
- Merged your tip (ledger conflict resolved by keeping both sides) and deployed main; nothing of yours was changed.
- The new `rules` aux family reads `stream_gamma_rules/` read-only. It needs every day file since 20261020 on the
  host, so please do not activate that stream's proposed 14-day retention without telling this track.
- No job of yours was paused, cancelled or re-prioritised.
