# LT9 census-code final verification (2026-10-23)

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; filed by the orchestrator). Diff
`a3841fc1..60df6c47` on `feat/live-tests-9`. 76 tests pass (live_tests9 + provenance). Design text sha256 098aa3fb…
equals `DESIGN_TEXT_SHA256` (`live_tests9.py:54`). Nothing counted.

**Verdict: OK_WITH_NOTES.** **Ruling on the CH203 overlap: option (i), keep NaN; option (ii) is not allowed under the frozen text.**

1. Reading capture k's mid in CS9 would break two frozen clauses: CH214's decision is the receipt of sweep k - 1 with
   eligibility from capture k - 1 and earlier (`LIVE_TESTS_9.md:227-229`), so capture k is after the unit's decision; and
   section 7's lag-slot rule admits only the named fields of a later slot, "no mid … of a later slot" (`:967-970`). A
   descriptive is no reason to amend a frozen loader rule.
2. Wording: "manifest start only" is not frozen text; the NaN reason (`live_tests9.py:376`) and the declaration
   (`live_tests9_v1.json:117`) should cite 1.3 `:227-229` and the section 7 lag-slot loader `:967-970`.
3. Optional (not taken by the orchestrator): CH203 units at capture j = k - 1 use only origin-side inputs for origin k
   (first-origin boundary counted), keyed on (market, UTC day), if every `quiet_units` input is in CS9's seal (not verified).
4. OK: `test_vendored_provenance` checks every `VENDORED` entry by normalised sha256 and exact source match (new entries
   from 86e32dd3 / 8dd013b9); `test_prior_population_specs_equal_the_prior_spec_files` ties the restated parameters.
5. OK, no gate can be helped: `overlaps` is only in CS9's output and never reaches `census_ch214`; `prior_spec_view` goes
   only to `patient_units` (copy); `prior_population_specs` is hashed and read by no gate.
6. OK: CH197's inputs at pass s (captures s, s - 1, sweep s) are origin-side for origin s + 1; `day_keys` aligns with UTC
   days; `osz` NaN filters nothing.
7. Low: a 12:31Z pass whose capture s - 1 is missing is skipped uncounted (`live_tests9.py:2041`): add a
   `pass_prev_capture_missing` count.
8. OK: the CR9 receipt-less count and the malformed control-pool exclusion are correct, with denominators, and can only
   lower counts.

Not verified: seal membership of the `lv_*` / store inputs (item 3); behaviour on real data.
