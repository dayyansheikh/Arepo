# CB9 h9_flow dependency ruling (science-reviewer, 2026-10-22 ~16:09Z, read-only; saved verbatim by the orchestrator)

`evidence_role: none`. Written BEFORE q0166's result is known (q0166 promoted ~16:03Z, not started at the time of writing).

**Verdict: REVISE.** Item (f) does not apply to q0168. q0182 keeps its id and its key-set definition. Its `depends_on` drops q0168. It may be promoted once conditions C1 to C5 are met.

## Justification
1. **The code does not need an h9_flow seal.** `cb9_common.exclusion_keys` (`backend/astrolabe/research_lab/cb9_common.py:492-560`) calls `cb8_books.seal_copy_ids_audited` with `own=("cb9_kd_holdout_SEAL.json",)` (line 81). That function (`cb8_books.py:585-613`) reads every committed `seals/*_SEAL.json` it finds and skips nothing silently. A missing `h9_flow_SEAL.json` is simply not found, so the job does not refuse. `h9` appears nowhere in `cb9_sign.py`, `cb9_kd.py` or `cb9_pyth.py`. The h10 source list (`run_cb9.py:585-589`) has no h9 entry.
2. **The design already covers absent seals.** CB9 §1.3 (`CREATIVE_BATCH_9.md:178`) says: "A seal copy not yet committed is 'absent at q0182'". Seal-time drops at q0187 then re-read every seal copy committed by then.
3. **(f) was written for a failed CB8 job.** q0167 and q0168 were never committed, under CB8's own pre-declared rule (`EXPERIMENT_LEDGER.md:3454-3459`). No h9_flow data exists, so there is nothing to overlap and no information to leak. h9_flow is permanently absent, not failed. The key file is built by the same code from the same definition, so it is not a "substitute key file".
4. **Dropping q0168 is an operational gating fix, not a design change.** Leaving it in would stall q0182 forever (`:1102`). It needs a dated note in CB9 and a ledger line. It does not need a scientific amendment.

## Conditions
- **C1. Gating.** q0182 depends on `[q0164_cb8_exclusion_keys, q0166_cb8_updown_books]` and nothing else. The note and ledger must say: "h9_flow never fetched (CB8 q0161 FAIL (a)); absent at q0182 per CB9 §1.3; (f) not engaged."
- **C2. Missing extra pins (most serious defect).** The draft argv (`:791`) has no `--extra-pin`. Extra pins are the only way the code reads the CB8 updown frame and the CB8-H holders frame (`cb9_common.py:522-527`, `run_cb9.py:941`). Only `cb8_updown_holdout_SEAL.json` arrives automatically. As drafted, q0182 would silently leave out the q0165 SCREEN frame and the holders frame. That contradicts the job's own title and §1.3 (`:172-176`). Fix: add `--extra-pin cb8_updown_frame:<abs path>:<sha256>` and `--extra-pin cb8_holders_frame:<abs path>:<sha256>`, both hashed on the host. The holders frame keeps growing, so pin a dated snapshot and record its timestamp.
- **C3. q0166 first.** q0166 must be `done`. If it sealed, `cb8_updown_holdout_SEAL.json` must be committed and present on the host checkout before q0182 starts. Otherwise it is skipped as `not_committed` (`cb8_books.py:599-601`).
- **C4. MUST 1.** Replace the placeholder with q0164's `keys_sha256` from `creative_batch8/exclusion_report.json`, after checking it equals the host's sha256 of `creative_batch8/exclusion_keys.csv.gz`. Record the value in the ledger.
- **C5. Extra seal copies.** The CB11, CB12 and CB13 `*_SEAL.json` copies now in `seals/` will be included automatically. That fits "every seal copy committed since" and is conservative. Disclose the list from the `seal_copies_used` field of the q0182 output report.

## Question 3: if q0166 fails (rule fixed now, before q0166's result is known)
- **Coverage audit FAIL.** q0166 ends `complete` with status `source_unavailable` (`cb8_books.py:471-476`) and extracts no checkpoint. That means no CB8 HOLDOUT books exist, so the holdout seal is "absent at q0182". q0182 runs with the q0165 frame extra-pinned (C2). This is not an (f) failure.
- **Crash or unrecoverable failure.** (f) applies as written: retry, or P, K, D and S1 are not testable, counted. The exception: if the q0165 frame exists and is hash-pinnable, a new job id over the same definition with a written justification and a reviewer pass may follow (f) step 3.
- **Before promotion:** confirm how the queue records a `source_unavailable` exit (done or failed).

## Question 4: q0181
q0181 is unaffected. Its job file depends only on `q0180b_cb9_smoke_v2`. For S0c it drops markets by the CB7 keys plus the seal copies committed when it starts (`cb9_sign.py:729-732`). There is no h9 or q0182 dependency.

## Not verified
- q0164's key-file sha256 (q0164 is `done` in the queue at 2026-10-22T00:20Z; the value is read at promotion).
- The exact file paths and column names of the CB8 updown frame and the holders frame. The extra-pin reader needs a `market_id` column (`cb9_common.py:526`).
- Whether reading an extra pin under `creative_batch8/` passes the refused-roots check. `exclusion_keys` does not call `refuse_read` on extra-pin paths. Test with a dry run on the host.
- Whether the queue treats `source_unavailable` as `done`.
