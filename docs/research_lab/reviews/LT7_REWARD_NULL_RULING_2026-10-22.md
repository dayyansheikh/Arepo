# LT7 challenger ruling on q0601b (reward-field nulls), 2026-10-22 ~11:05Z

`evidence_role: none`. Counts only; no price, target or outcome was read. Challenger: `science-reviewer` (independent,
read-only). Trigger: q0601b's pre-declared `common` rule fired (`seals/lt7_rewards_null_share.json`, sha256 2278ce60…):
`clob_rewards` is null on 0.60-0.65 of sealed non-sports ex-crypto market-captures every day 10-12..10-21 (1,047,747 of
2,774,846 rows non-null); `[]` never occurs; `rewards_max_spread` and `rewards_min_size` are never null.

## Verdict: (B) with changes. Revise before CC7 / CS7. q0602 (CV7) may be promoted (conditions below).

## Justification (reviewer's)
1. `rewarded` is a control in CH192's **primary** (`live_tests7.py` CONTROLS_192), not only in its wall-class secondary;
   the NaN filter drops those units. Left as frozen, (A) silently shrinks both CH197 and CH192's primary to ~38% of units.
2. (A) breaks the frozen design: the planning MDEs (`LIVE_TESTS_7.md` sections 5 and 6) assume the whole non-sports
   ex-crypto population; keeping 38% inflates the MDE ~1.6x and changes the estimand.
3. Reading null as "no programme listed" is a statement about the field's meaning, not imputation: Gamma never sent `[]`
   (0 of 2.77M rows); the sidecar object is complete (`rewards_min_size` / `rewards_max_spread` null in 0 rows), so a null
   is not a capture failure; the null share is stable; the non-null share fits the maker study's 13,683 rewarded markets.
4. Outcome-blind: decided from sidecar counts only, before any census, through the gate route q0601b declared.
5. Still a design change after the text freeze (units and control coding; the section 1.5 exceptions do not cover it):
   dated amendment, new sha256 and ledger line, before any adjacent `T_X`. Gates, thresholds and formulas unchanged.
6. The brief's "collinear" claim is not verified: the seal counted zero-rate programmes over all days (`day=None`), but
   the census parses by the capture's UTC day and programme start dates roll forward, so a listed programme can be
   inactive on the day. Pool those with nulls as `rewarded = 0`; no indicator column; count the two groups separately.
7. Existing defect, whatever the ruling: `maker_rewards.parse_daily_rate` returns 0.0 for malformed JSON, so section 5's
   "unparseable excluded" is not implemented; `cnt["reward_unparseable"]` actually counts nulls and missing sidecars.
8. `in_band` needs no availability ruling (`rewards_max_spread` never null): keep the frozen mechanical definition for
   every market; report the `rewarded x in_band` counts.

## Required code changes (applied on a separate branch, then a census-code re-check)
- `live_tests7.py:series7_frame`: `rew_status` in {`listed`, `null`, `malformed`, `absent`} (absent from row presence, not
  from `ext.reindex`); strict local parse (a JSON list, else `malformed`); `rew_rate` = `parse_daily_rate(v, day)` if listed,
  0.0 if null, NaN if malformed or absent. `maker_rewards.py` is not edited.
- CH197 and CH192 unit builders: counts `rewards_null_as_zero`, `rewards_listed_inactive`, `reward_unparseable`,
  `reward_sidecar_absent`; carry `rew_status`, `rew_min`, `osz` in unit output (bookkeeping, not controls).
- Analysis (phase 2): wall rule `rewarded == 1` uses `rew_min`, `== 0` uses `osz`, NaN field = unassigned; listed-only
  sensitivity reported.
- Spec key `reward_null_rule: "null_as_unrewarded_v1"`; re-pin the spec and `code_sha256` map; census-code re-check; unit
  tests for all four statuses. CC7 and CS7 use **fresh** work dirs (series files are write-once).

## Before CC7 (counts only, no prices)
The share of listed programmes with zero rate on the capture day; the null share of `order_min_size`; the share of markets
switching between null and non-null `clob_rewards` within a UTC day.

## q0602 (CV7)
May be promoted now (it reads no reward field, but writes series into `work_volsem` with the old `rew_rate`), provided
`work_volsem` is never reused by CC7 / CS7, CV7 records its code hash, and the fix does not touch `census_volsem`.
Landing the fix first gives one code pin. **Orchestrator decision:** land the fix first (the retention deadline,
2026-10-28T03:30Z, leaves room), then run CV7, CC7, CS7 on one code hash.

## Not verified
Gamma's documented meaning of null; whether CV7 refuses on a design-sha change mid-run; whether CC7 / CS7 work dirs exist
on the host; whether an adjacent `T_X` has passed (none before 11-17 on the current table).
