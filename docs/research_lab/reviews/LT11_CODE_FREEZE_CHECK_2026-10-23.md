# LT11 code-freeze check (8.4 step 3), 2026-10-23 ~23:00Z

Reviewer: `science-reviewer` (independent, read-only). Branch `feat/live-tests-11-code` at 3452419b. Frozen text
`LIVE_TESTS_11.md` sha256 `991100db…3583` (matches `DESIGN_TEXT_SHA256`).
**Verdict: REJECT** (fixable entirely in code / queue drafts; no fix needs frozen text changed). Re-check required.

## Verified
- Scoped tests 143 passed (vendored-copy provenance and `test_e026_frozen_files_untouched_by_this_branch` included); no E026
  frozen file in the diff; `live_tests7.py` hash `e1c5c0c6…`.
- Coverage check returns before any gate block or row read and writes `census_unavailable (coverage)` (`live_tests11.py:2071-2073`);
  census gate values match the section 7 table; lag loaders return only twin terms (`:1172-1240`); `volume_num` read from
  slot k - 1's own row, no carry-forward (`:675`, `:779`); causality tests assert `max(reads) <= k`; event-phase gate keeps one
  offset per event and omits (never fills) missing positions (`analysis.py:372-380`).

## MUST-FIX
1. World `w` not the declared state (1.8.1 worlds 1-4, 12; 2.4): `worlds.py:106-107` draws `w` ~ U[0.2, 1.0]; the design
   defines `w = 0.5 + sign(d)(p_{k-1} - 0.5)`, |d| winsorised at 0.20. Build `xw` from the declared `w`.
2. Worlds 3 / 3b `q` hard-coded 0.20 (`worlds.py:97`, A11) though the census writes `census_fixed.CH234.q_unknown`
   (`live_tests11.py:1743`); section 7 lists world 3's q as census-fixed. Read it from the spec.
3. Census-value refusal disabled (`if False`, `worlds.py:462`); `cf.get(t)` is a dict of Nones. Refuse on any None.
4. World 3b not "world 3 with capture-level missingness" (1.8.1 3b): row-level `a` zero (`worlds.py:94`, `99`, `134`), so
   `0.3c x a` continuation and `logistic(-0.6 + 0.8a)` trading are missing; control `A_t + noise` instead of `a + A_t + noise`;
   slot-of-day dummies missing from `CTRL` / `EXTRA_CTRL` (`:319`, `:323`).
5. M-Q worlds 12-14 do not apply "loading 0.3 per SD [on] the lead state and the twin": world 12 multiplies `w` by
   `exp(0.3 mu)` (E[xw | mu] ~ 0) and adds an undeclared `0.3a` term (`:94`, `:127-128`); world 13 loads `mu` on bid levels
   (`:187`); world 14 puts `mu` into the spread level (`:259`). All three weaker than declared.
6. `q0691_lt11_seal.json` `not_before 2026-11-07T03:00Z` is before the last sealed capture (11-07T04:31 twin; spec bound
   `refuse_at_or_after 2026-11-07T06:00Z`). Set >= 06:00Z plus capture completion.
7. `battery2.py` edit changes LT10's hashed code set (`live_tests10.py:74-75`; `55b1e349…` -> `931ffeb5…`).

## SHOULD-FIX
1. Event-gate minimum counts units (`analysis.py:355`) vs census counting captures (`live_tests11.py:1802-1803`): use 16 captures.
2. Labels vs 1.9: "material" vs 0.5c not beta x tercile gap (`analysis.py:609`); precedence at `:611`; "series-concentrated" on
   `event_id` not series family (`:625-627`); underpowered / within-bin / re-centring / ladder-dominated / volume-missing / CLOB
   labels missing (A20 / A22): implement or disclose as deviations.
3. A23: CH233 "difference p" fits `zcl` with `zca` as a control (`analysis.py:455-456`); use the `zcl + zca` form as F does.
4. A12: re-crossings counted only among zone / mover units (`live_tests11.py:1872`), non-conservative for the <= 60% gate:
   count every outward crossing between defined mids (or print both).
5. Undisclosed: `category_split` (`:765`) drops sidecar-missing movers before `vnum_classes` (`:779`), so `sidecar_missing`
   never occurs (lowers the unknown share and q). Count it.
6. A6 (`:901`): undefined mid at slot ds - 1 leaves first-crossing status unknown; at least count these.
7. World 6 longshot spreads AR 0.7 not "reflected AR(0.8)" (`worlds.py:188-191`); world 8 scales SD not variance by
   `exp(0.5 L_e)` (`:182`).
8. `limit_for` gives 0.058017; use the frozen 0.058.
9. Power runs add the effect per SD of `xw`, not per tercile gap (`:157`) (non-binding).
10. No timing-only mode: `--dev` writes rejection rates, 8.4 step 3 allows only the clock to be read.
11. q0690 restore lacks the byte-measure / stop step (only in `next_action`); `restore_from_archive.py` has no free-disk check.

## A1-A24
A1-A5, A7-A10, A13-A19, A21, A24 consistent and conservative or neutral; none changes a threshold, formula or gate. A10
acceptable only once MUST-FIX 1, 4, 5 are done. A6, A11, A12, A20, A22, A23: see above.

## Not verified
LT10's freeze record on the host; peak memory under the 2 x `mem_mb` caps; size-check run time (no worlds run); LT9's M-Q
loading implementation; host copies of the census span.
