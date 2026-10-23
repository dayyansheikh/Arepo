# CB8-B amendment fixes: verification (science-reviewer, 2026-10-23, read-only)
`evidence_role: review` | Verified tip: `93787c2f` on `feat/cb8b-variant` (diff `8cd09e72..93787c2f`: 8 files, +86/-24). Filed verbatim by the orchestrator. `pytest -q tests -k cb8`: 223 passed.

**Verdict: VERIFIED**

- Fix 1 (disclosure): done; §1.3 adds the required sentence word for word, plus the counts 35/791/840.
- Fix 2 (B1 sensitivity): done; the frozen B1 statistic re-run once, after Stage 1, on the day set without `day_exclusion_sensitivity_days`, by a new file outside `cb8_b_analysis.py`, descriptive only, binding nothing.
- Fix 3 (masked test): done both ways; `run_cb8.py` calls `u.smoke_ok` before `attribution_pins`; `test_cb8_updown.py:673-676` asserts "smoke result" / "not found"; new CLI attribution-path test.
- Fix 4 (attribution provenance): done; `id_drop_report.attribution_pins` with name and sha256 for all 5 `c7.EXCLUSION_PINS`.
- Recommendation 1: `SMOKE_ACCEPT_FILE_SHAS = (8189303f…6954)` enforced; equals the committed `seals/cb8_smoke_FAIL_20261022.json` and the host's `smoke.json` (orchestrator check ~17:45Z).
- Recommendation 2: `archives_vs_prior_run.prior_meta_file_sha256` recorded.
- Nothing scientific changed: v3 diff limited to `exclusion.smoke_accepted_file_sha256` and necessarily changed hashes; `cb8_b_analysis_rules.json` only `data_rules_sha256` and derived `rules_sha256` (`funcs_sha256 437871…` unchanged); no gate, threshold, regex, MDE, placebo or margin touched; W/H pins `9dc74a91…`, `e7e72f4c…` pass.
- Reproducibility: both rules files regenerate JSON-identical (`rules_sha256 9c5d432d6f52…e498`, b-analysis `904208df…`). Drafts quote the new hash; no stale `e10fb289` / `5076e3f8`.
- Not verified (host): every attribution pin file present with matching hashes (checked by the job at run time); that nobody read q0165's guarded or Binance files.

**Promotion:** q0165b may be promoted now. q0166b only after q0165b reaches `updown_frame_complete`, and only after confirming again, at that moment, that no `seals/cb8_updown_holdout_SEAL.json` exists on the host (none at 17:45Z).
