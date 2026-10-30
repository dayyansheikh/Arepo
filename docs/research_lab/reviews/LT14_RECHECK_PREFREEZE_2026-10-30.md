# LT14 re-check and pre-freeze verification (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: FREEZE_AFTER_FIXES.** Two fixes are blocking: each would kill the test by how the text is written, not by the
data (the LT13 A3 failure mode).

## Verified
- sha256 `d14981fd…5489` (last change 4e295556; ledger line present). R1 MUST 1-7, SHOULD 1-10, open questions 1-11 mapped (§12)
  and present. Nothing loosened (`H` 1.30c; F and placebo binding; k = 1; size limit 0.058; alpha 0.05). Arithmetic
  reproduces (0.0806c, 0.218c, 2.48c, 1.30c). Pre-freeze hold filed (`signal_engine/CANDIDATES.md`).
- Input-clock claims match the specs: se0 / se1 / se17 use `market_state` and `momentum` only; se18 adds `flow`, `xvenue`,
  `wallet`, `book0`; xvenue before the capture start (`features.py:406`); book0 strictly before the origin (`DESIGN_V1.md:575-583`);
  flow and wallet come from the pass's trade sample, promised only received before the prediction is written
  (`DESIGN_V1.md:64-65`, `features.py:12-13`), so se18 fails only on flow and wallet, under a receipt-clock reading.
- Base eligibility requires an open two-sided quote (`features.py:160-161`), so `mid_k` always exists.
- Collinearity: no exact identity among M6's controls (`log1p` hours-to-end is non-linear in the slot index; `hte_unknown`
  and `rv_missing` near market constants, removed by drop group 2). No degenerate estimator in the primary, M1 or F.
- Every census threshold stated before data. Designer's twin reading adequate (expected value exactly 0 by construction).

## Fixes (ranked)
1. **BLOCKING: `mid_k == ms_mid` fails by data type.** `quotes/` stores bid and ask as float32 (`features.py:110-111`); `ms_mid`
   is the float64 mid cast to float32 (`:182, :490`); exact equality held on 33.8% of one-tick pairs on a 0.001 grid, so the
   100% census line would give `census_dropped`. In §1.5 and §3: "`|mid_k - ms_mid| <= 1e-6` (float32 storage; exact
   equality is not expected)".
2. **BLOCKING: world 9 is not a null for the estimand.** `theta` is conditional on `labelled` (§1.8); attrition of units with
   `g < H - 2c` raises `E[g | labelled]` above `H`; with F and the placebo able to pass, the analytic p decides. Planning: at a
   2% top-decile unavailable share (SD 1.3c, n_eff about 20k, DE 5) the shift is about 0.032c (about 1.5 SE), Supported in about
   45% of worlds (about 0.13 at 0.5%), so the size check fails and p = 1. World 9's mean cell: "`H` on labelled units (the unit
   term is shifted after attrition)"; diagnostics: "world 9 unshifted: share Supported, printed, never a verdict change"; a
   one-line justification in the text.
3. §1.9 and §12: "the twin's sign-weighted expected mean is 0 by construction (shocks mean 0, independent of `sign(s)`); its
   realised mean varies around 0".
4. §1.3 audit bullet: "'received' is the receipt clock of the record read (fetch time), not its venue event timestamp".
5. §1.5: "`spread_k = ask_k - bid_k` from `quotes/<k>`" (`ms_spread` is Gamma's `spread` field, `features.py:183-184`).
6. §3: "the F-MDE uses planning `r` = 0.2; the census reads no twin value".
7. §1.9: "verdict size and the analytic-p share are computed per world type".

## Low-severity note
The first `se-promotion-v2` read is due about 11-04, before the 11-07 deadline; whoever chooses the freeze moment also chooses
`P`. No cents data have been seen, so the risk is small; freezing promptly after these fixes removes it.

**Could not verify:** trade-sample fetch timestamps vs `t_row`; expanding-past demeaning of a stratum's first observation;
the real unavailable share and `|s|` distribution (census-only); the q > 0.85 placebo regime.
