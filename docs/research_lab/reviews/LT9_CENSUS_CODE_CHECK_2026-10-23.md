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
