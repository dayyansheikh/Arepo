# LT5 census code freeze check (2026-10-21): summary

Reviewer: `science-reviewer` (independent, read-only), on feat/live-tests-5 at the code pass 1 commit (c881f87a).
Scope: census code (q0561 CF5/CHW/CRW, q0562 CJ/CO), the size check (q0563) and the queue drafts, against
LIVE_TESTS_5.md sections 1.8, 1.8.1, 5, 6, 8, 9 and 15.

**Verdict: CENSUS_READY_WITH_FIXES.** This is a summary saved by the author. The response is in LIVE_TESTS_5.md section 17.

| # | Sev | Location | Finding | Required |
|---|-----|----------|---------|----------|
| 1 | MED | live_tests5.py:719-727, :951; live_tests5_base.py:474-479 | An absent `rows_ext` is dropped silently, and a capture that is sealed but absent locally is not refused | Refuse when any seal-listed file in the needed slot range is absent locally. Count genuinely missing slots (not in the seal, e.g. 10-21 02:31) separately. Skipped flow samples must not count in `n_samples` (:981) |
| 2 | MED | live_tests5.py:877 | R's depth-band median is taken over inside-only units | Take the median over the rewarded band units (section 6, lines 543-544) |
| 3 | MED | live_tests5.py:608-620 | The CHW `d_hi` panel does not apply H's population filters | Apply non-sports and mid band, as declared |
| 4 | LOW | section 5, 527-528 | The H gap rule is not coded | Code it separately (preferred) or declare it subsumed by >= 72/84 |
| 5 | LOW | live_tests5.py:1000-1002 | The J `interval_truncated` share uses the wrong denominator | Use section 8's "traded sampled movers" |
| 6 | LOW | live_tests5_analysis.py:244 | The size check fails open when a scenario is missing from the binding map | Raise. Refuse `--worlds/--draws` overrides outside DRAFT/dev. Record the spec sha256 |
| 7 | LOW | CODE_FILES | Imported dependencies are not hashed | Add maker_rewards, panel, trade_sample, cb17_census and forecast |
| 8 | LOW | :366-367 and doc | Several facts are not stated | Count F's excluded same-neg-risk siblings. State O's NaN `chg_1d` drop and that the block gate counts `n_m` after the first-unit drop |
| 9 | LOW | doc, drafts | Stale text and plan | q0561 look-back starts 10-12. "84-slot" becomes 96 (q0560, q0561, 9.1, 9.2). "First complete capture" becomes the 00:31Z slot. Remove "script does not exist yet". Fix the 9.2 backfill timing for 8-day retention. q0562 (1,200 MB) must not overlap q0560/q0561 |
| 10 | LOW | provenance test | The test skips when a source changed | Fail unless an explicit re-vendor is recorded |
| + | - | tests | No look-ahead test | Add a test that no capture after the last census slot is opened |

Not verified by the reviewer: whether the release tags hold every capture of 10-12..10-21. The catalogue shows all of 10-12 in
data-20261015-dsheikh, only 3 captures of 10-14, and none of 10-20/21. The reviewer asked that q0560 restore only what the host
lacks and that the census read the host originals for the rest, under the seal. The author's read-only host listing is in
section 17.
