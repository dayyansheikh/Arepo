# CB5 code re-check (science-reviewer, 2026-10-30): ACCEPT_WITH_FIXES

(Read-only reviewer; text saved by the experiments autopilot.)

**Commit checked:** 5b534a26 on fix/cb5-freeze-check.
- `pytest -k cb5`: 116 passed. ruff is clean on the 4 changed code and test files.
- `declaration_sha256()` recomputed from the worktree gives `7c62c037…5cd0`. The parent commit 8dd7011b gives `42bde44f…8ede`.
- Comparing the two declaration blobs, only these entries differ:
  - **Added:** `cb5_fetch.SelectionChanged`, `_StatusTap`, `selection_sha256` and `cb5_run.listings_input`.
  - **Changed:** `cb5_fetch.cohort_fetch` and `cb5_run.census_g_cohort`.
- No constant, window, threshold, seed or grouper changed. The grouper hash (`aaac0948…`) and the r_inc hash (`8f51ef36…`) are unchanged.
- §10 of the design explains the change accurately. The commit touches no E026 file and there is no `cb5_v1.json`.

**Item by item:**
1. **Truncated trade lists:** done. `census_g_cohort` leaves truncated markets out of G-ii and G-v, counts them as `unavailable_truncated` and never reads their files. The test that overwrites the trade file with junk would fail without the fix.
2. **Failed fetches:** done. `_StatusTap` records any non-200 answer or a request given up after retries. The market gets status `failed`, no file is written, it is retried on resume and it is counted as `n_failed`. Three parametrised tests cover a trades 404, a prices 500 and a give-up.
3. **Census on a partial cohort:** done. `cmd_census` refuses with exit 2 unless the cohort manifest shows `complete: true`. A test covers this.
4. **Manifest contents:** done. The manifest now records the seed, the selected-id hash and the listings-manifest sha256, and a census resume with a changed selection is refused (tested in code and through the CLI). `listings_input` counts captures that were skipped instead of hiding them.
5. **Fetch-side tests:** done (`tests/unit/test_cb5_fetch.py`).
6. **Disclosure that the census cohort reaches past `T_seal`:** done (CREATIVE_BATCH_5.md:123,148-152).

**MUST**
1. **Settle q0105/q0106 by a recorded decision, before q0106 runs.**
   - The 0-family result came from the frame q0104b, not from q0105 (EXPERIMENT_LEDGER.md:1355-1365).
   - The declared rule, CREATIVE_BATCH_5.md:375-376: *"L-iv: gate G59: at least 20 audited live families with eligible pair-captures in the dev window. Fewer → CB5-L is 'not testable: n families' (L1 counted with p = 1) and stops; CH59 is closed at 'too rare in the live universe'."*
   - The verdict map, :696: *"G59 fails → CH59 closed: 'too rare in the live universe (n families)'."*
   - The counting rule, :248-250: tests behind a failed G59 are "not testable" (p = 1) and still counted.
   - Zero audited families can never reach 20, so G59 fails whatever the audit says. That is the declared outcome, not a rescue.
   - **The code gap:** `cmd_census` reads only `families_v{2,1}.json` (run_cb5.py:334-335). Those files are written only after an audit passes (run_cb5.py:285-289), and `apply_audit` treats an empty sample as a failure (`pass = n and …`, cb5_cdf.py:488-489). So the census would permanently record `L: inputs_missing` instead of the G59 result, and `census.json` is write-once.
   - **Do not** run `cdf-audit-apply` on an empty sample. It would record a false audit failure 1.
   - **What to record instead:**
     - q0105 and q0107 as "not run: empty frame family list", which is distinct from failed.
     - Take q0105 out of q0106's `depends_on`.
     - Bind the G59 result to `manifest_v1.json` (counts and `family_list_sha256`) in the ledger, or add a reviewed code path that emits `g59_gate(0)` from the candidate list. The code path changes the hash and needs review.

**SHOULD**
2. **Two meanings of "complete."** `complete: true` in the manifest allows `n_failed > 0`, but the `cohort_fetch_complete` log marker needs zero failures, and q0103b stops after `max_runs` 3. Declare now that q0106 may run on `complete: true`, with the failed markets reported as unavailable (never filled in) and their count written in the release commit.
3. **Replication selection can shift.** Selection is `head(max_markets)` on a set that keeps growing (cb5_fetch.py:211-212). Markets that were already fetched can drop out of the selection, and the hash is only recorded, not pinned. This is outside the fix scope. Review it before q0111 runs.
4. **Labelling.** The 0-family finding belongs to q0104b; don't attribute it to q0105 in the ledger.

**Not verified:** anything on the host (extract manifest coverage, whether `families_v1*.json` exist there, the deployed `arepo_pass.sh`). Promotion conditions 2-6 for q0103b are still open.
