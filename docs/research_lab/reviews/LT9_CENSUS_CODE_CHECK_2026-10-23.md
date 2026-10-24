# LT9 census code-freeze check (2026-10-23)

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; the text below is its report, filed by the
orchestrator because the reviewer cannot write). Branch `feat/live-tests-9`, tip `2925961a`. Design text
`docs/research_lab/LIVE_TESTS_9.md`, sha256 098aa3fb… (verified). Nothing counted.

**Verdict: FIXES_REQUIRED**

## Checked and OK
- Design-text sha256 098aa3fb… as stated. 55 LT9 tests pass; ruff clean.
- Vendored sources match their recorded hashes (LT7 e1c5c0c6 / 2e8baa90; LT8 d1b252cf, equal to the hash in the LT8 seal).
- Every threshold in the section 7 table matches the spec.
- The seal checks the design hash; the runner refuses a seal that is untracked or differs from HEAD
  (`run_live_tests9.py:58-71`).
- CC9 and CS9 census inputs come from before each origin.

## Must-fix
1. **A missing sealed sidecar does not stop the census** (`live_tests9.py:1645-1649`; the vendored `capture_files` at
   line 442 skips a missing `rows_ext`). In a scratch world with one sealed sidecar deleted, `census_captures` ran without
   error and counted `sidecar_missing` 92. Section 7 says the census must refuse. LT8 has a completeness check
   (`seal_completeness`) that LT9 never calls.
2. **CR9's decision capture can still be in progress at the decision time** (`:1355`, "starting at or before" the feed
   finish). Row receipts after `t_dec` can then decide eligibility, tier and control choice, against 1.3's "strictly
   earlier". Use the last capture whose last row receipt is before `t_dec`.
3. **CH213's twin for control units uses the band of capture k** (`v_ctrl(k)`, `:1824`). Section 2 says `v_ctrl` of
   capture k + 5's cell; this feeds the binding F-MDE gate. Compute that band inside the lag-slot loader and still return
   only the flag.
4. **CH215 control ties are broken by `market_id`** (`:1401`, and the spec's `control_rule`). Section 5 says by
   `condition_id`.
5. **CR9 feed completeness covers only the last 96 slots** (`:1324`). Section 7 says the span's slots (all 120).

## Rulings on the implementer's three ambiguous points
1. **Malformed plus dated positive config:** not settled by the text, and the code is inconsistent (open + malformed ->
   open, dated + malformed -> malformed; `:259`). Minimal conservative choice: declare that any malformed positive config
   makes the market NaN (order malformed > open > dated), and count the mixed cases.
2. **Sentinel year read before UTC conversion:** "a value with year >= 2100" supports the year as written. It matters
   only within about 14 h of 2100-01-01, so no census count can change. Declare as is.
3. **Different end-kind denominators in CR9 and CC9:** not fixed by the text; both are descriptives. Declare each
   denominator in the output. CR9 must also print its positive-config count, without which the shares the text asks for
   cannot be computed.

## Notes (fix before the seal, since each census runs once)
- CH212's `feed_end_shares` labels unlisted ("ghost") markets as `feed_no_positive_config` (`:827-839`).
- Missing descriptives the text asks for: CR9's sponsored shares, the share listed >= 48 h ahead, the share moved between
  captures; the overlaps with LT8 CH203 and LT7 CH197.
- The switching gate uses the mean per day over all sidecar rows: declare it.
- `scan_feed` reads manifests of feed captures the seal does not name.
- Queue drafts look consistent. Before promoting, check by hand that no LT8 size-check or analysis job (q0624-q0627) runs.

## Not verified
The vendored helpers' internals (DE, `design_se`, `pair_correlations`). LT8's census outputs do not exist yet, so the LT8
hash re-check stays open.

## Response (implementer, 2026-10-23; design text untouched, vendored files untouched)

All edits are in `backend/astrolabe/research_lab/live_tests9.py` and `model_specs/live_tests9_v1.json` (new key `declared_before_seal`, printed in every
census output); tests are in `backend/tests/unit/test_research_lab_live_tests9.py`.

| Item | Fix (file:function) | Test |
|---|---|---|
| Must-fix 1, missing sealed sidecar | `_load_for_census` now calls the vendored `b.seal_completeness` (every sealed file of a sealed capture or sweep must exist locally) | `test_missing_sealed_sidecar_refuses_the_census` |
| Must-fix 2, CR9 decision capture | `capture_last_receipt`, `decision_slot` (last capture whose last row receipt is strictly before `t_dec`), used in `census_feed` | `test_decision_capture_is_the_last_with_last_receipt_strictly_before` (includes a capture in progress at `t_dec`) |
| Must-fix 3, CH213 control twin | `lag_twin_flags` (v_ctrl of capture k + 5's cell via `assign_control_band` on `control_cells` of k + 5, then `lag_break_flag`; flag only), wired in `census_captures` | `test_ch213_control_twin_uses_v_ctrl_of_capture_k_plus_5_cell` |
| Must-fix 4, CH215 ties | `rank_control_candidates` (ties by `condition_id`); spec `control_rule` updated | `test_ch215_control_ties_break_by_condition_id` |
| Must-fix 5, CR9 feed completeness | `census_feed` passes all span slots (120) to `feed_completeness` | `test_cr9_feed_completeness_covers_all_span_slots` |
| Ruling 1, malformed > open > dated | `feed_frame` (`end_kind`, `mixed_malformed`); CR9 excludes dated ends of malformed markets and counts them; mixed cases counted | `test_malformed_beats_open_beats_dated_and_mixed_cases_are_counted` |
| Ruling 2, sentinel year as written | declared in `declared_before_seal.sentinel_year` (no code change) | `test_sentinel_year_is_read_as_written` |
| Ruling 3, denominators | each end-kind denominator printed (CC9, CR9, CH212 shares) and declared; CR9 prints `positive_configs`, `date_only_share`, `sentinel_share` | `test_cr9_and_cc9_print_declared_denominators_and_descriptives` |
| Note: ghost label | `feed_end_ok` labels unlisted markets `feed_unlisted`; excluded from `feed_end_shares` | `test_ghost_market_is_its_own_feed_end_category` |
| Note: missing descriptives | CR9: `sponsored_shares_of_decisions`, `share_listed_ge_48h_ahead`, `moved_between_consecutive_feed_captures`; overlaps with LT8 CH203 and LT7 CH197 printed NaN with a reason (`PRIOR_POPULATION_OVERLAPS`: those population definitions are not vendored into LT9 and no earlier module may be imported) | same test as ruling 3 |
| Note: switching-gate mean per day | `SWITCHING_GATE_DEFINITION` printed in CH212 output and declared in the spec | same test as ruling 3 |
| Note: `scan_feed` | `scan_feed(only=...)`; `_sealed_feeds` passes the sealed feed names | `test_scan_feed_reads_only_the_named_manifests` |

Open: the overlaps with CH203 and CH197 are NaN, not computed (no vendored population definition). The queue check (no LT8 job q0624-q0627 running
before promotion) is for the orchestrator.
