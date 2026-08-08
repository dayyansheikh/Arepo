# Final review synthesis

_Lead synthesis of the eight dimension reviews (00–08). Convergent, de-duplicated, ranked by real
value/risk. The eight independent agents were cut off by a session usage limit before writing; the lead
conducted the reviews directly (see `00-review-method.md`)._

## Headline
No **Critical** or launch-blocking defect. Two independent reviewers (quant, security) and the SRE
review find the system **honest and correctly built**; the shared theme is **research maturity + one
spec-required migration check**, not correctness bugs. Overall: **ship-with-fixes**, then deploy.

## Cross-reviewer agreements (the signal)
1. **Cohort cadence 6h → daily is the single most-cited change** (quant High; data-integrity Medium;
   portfolio; SRE storage). It is a *statistical* improvement (less pseudo-replication of the same
   universe) whose storage benefit (~12→~3–4 MB/day; ~3–5 wk → ~4 mo hot) is a byproduct, not the reason.
2. **A long-term, market-deduplicated "selected vs wider" scoreboard** is the top product ask (market-user
   #1, quant, portfolio #1). Live Replay is correctly per-cohort today; the *aggregate* must count each
   market once per period.
3. **Migration must verify per-record immutable values**, not just counts (data-integrity Medium) — this
   is explicitly required by spec §10 for the one irreversible step.
4. **Beginner risk: Strength read as probability** (beginner Medium) — a one-line tooltip fixes it.

## Remediation plan

### Must fix before public launch
- **M1 — Migration value-level verification.** Add an immutable-value check to `import_sqlite`: for every
  source PK, confirm the destination row exists and immutable columns hash-equal; fail closed on mismatch.
  (Data-integrity; spec §10.) **[done this pass + test]**
- **M2 — Cohort cadence → `daily,weekly` (prospective) + refresh target ~10 min.** Config default change;
  existing frozen cohorts untouched. (Quant §9, §8.) **[done this pass]**

### Should fix soon (research/product value)
- **S1 — Long-term aggregate summary** (market-deduplicated, per-scope/per-horizon: total, expected/
  against/no_change/pending/unavailable, hit-rate-among-moved, distinct markets, period). Backend +
  integrity test now; public UI surfaced when evidence accumulates. (Quant/market-user/data-integrity.)
- **S2 — Beginner tooltip:** "Strength is a signal-intensity score (0–100), not a probability of being
  correct" on the strength bar; a short Research-Priority tooltip. (Beginner/UI.)

### Future research improvements (not launch-blocking)
- Selected-vs-shadow win-rate-among-moved with confidence intervals + ablation + calibration, over daily
  cohorts (the analysis that could eventually support/refute an edge — currently far too little data).
- Surface unavailable-reason breakdown so sparse 1h/6h horizons read as honest, not broken.

### Optional polish
- Status "Checking…" chip placement; lighten dense denominator captions; emphasise the top evidence
  chip; CORS `allow_headers` tightening; API security headers.

## Conflicts resolved
- **Depth vs simplicity (portfolio "over-engineering" vs quant "build the aggregate"):** resolved toward
  Arepo's purpose — keep the research harness, but only *expose* the honest, deduplicated subset. Do not
  add product surface that isn't backed by evidence.
- **Cadence frequency vs sample count:** resolved toward **independence over raw row count** (spec §9
  forbids inflating samples with redundant cohorts). Daily wins.

## Explicitly NOT doing (guardrails)
No formula/threshold/frozen-value changes to improve Replay optics. No alteration of historical cohorts.
No edge claim. No redesign — UI language stays.

## Targeted re-review (§26) — closure after remediation
- **M1 migration value-verification (data-integrity lens):** CLOSED. `import_sqlite._verify_values` now
  checks every source PK exists in the destination and is byte-equal on the source's columns (datetimes
  normalised to UTC, JSON canonicalised). Regression test `test_value_verification_catches_corrupted_immutable_row`
  proves a corrupted frozen `strength` is caught (recon `ok=False`) while a clean import checks all 10,412
  rows with 0 mismatches. Data-integrity concern resolved.
- **M2 cadence → daily,weekly (quant lens):** CLOSED. `config.research_freeze_cadences="daily,weekly"`,
  `scan_refresh_interval_minutes=10`. Freeze remains idempotent on `(cadence, cutoff)`; the causal
  freeze-due gate is cadence-agnostic; existing 6h cohorts untouched. Full backend suite (439) green.
- **S2 beginner Strength-not-probability (beginner/UI lens):** CLOSED. `metrics.ts` signal-strength copy
  now explicitly negates the probability misread; `StrengthMeter` carries a native `title` tooltip. No
  test breakage; tsc/lint/vitest/build green; Playwright re-run to confirm no UI regression.
- **S1 long-term aggregate (quant/data-integrity/market-user lens):** DEFERRED with a written spec + the
  market-dedup invariant (D-DEP9). Justified because retention never deletes cohorts/observations, so no
  evidence is lost within the ~4-month hot window; not launch-blocking.

## Remaining open (accepted / future)
Optional polish (status-chip placement, denominator caption weight, top-chip emphasis, CORS
`allow_headers`, API security headers) and the future research analyses (selected-vs-shadow CIs,
ablation, calibration over daily cohorts) are recorded as non-blocking. Reason they're safe to defer:
none affects security, causal integrity, data loss, migration integrity, scheduler reliability, or a
misleading claim (the §24 must-fix classes).
