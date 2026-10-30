# M3 (CH274) J1 / J0 code check, 2026-10-30 (science-reviewer, read-only; 33cd591c)

**Verdict: ACCEPT_WITH_FIXES.** Two MUSTs block J0. The rest are text changes or fixes needed before the freeze or before q0781.

Checked on branch `chore/arepo-claude-setup` at 33cd591c. The hashes match the code note: `code_sha` is 105587be…98ef, and `m3_spec.py`, `m3_j1.py` and `run_m3.py` match their listed hashes. The tests pass (49 of 49) and ruff is clean. I ran three probes from `/tmp/m3probe/`, all on synthetic data only.

## MUST (blocking before J0)

**MUST 1. The event member count reads an earlier unit's row after its k (S6 and S8).**
- **Where:** `m3_j1.py:802-803` counts open members (`evc`) from every row, including rows of markets that are already units, and `:1059`/`:1064` turn that count into the new unit's S6 and S8 cells.
- **Probe p1:** two markets in one event. Market 1 becomes a hypothetical unit at k=7; market 40 crosses at k=10. If market 1 is set to closed at k=9, after its k, J0's output changes:
  - S6: `member_yes 3 → 2`
  - S8: `2-5: 3 → 2`
- **Why it matters:** it breaks 10.1 ("J0 reads no … exit … or any other capture content for a hypothetical unit after its k", l.645-646). This is the sibling-reads-post-k defect that R1 MUST 7 named. In J1 it is literally the void condition 12.2 ("any read … of any data from after a unit's k", l.838-839). R8 discloses it but does not resolve it. The existing test misses it because `alter_after_k` moves the unit to its own event "eZ".
- **Fix (recommended, option a, code):** count open members only among non-unit rows. Then add the earlier M3 units of the same event, taken from state (store `event_id` in `unit_meta`), without reading their rows. Text for 3.4 and S8:
  > "The event's open binary member count at k counts every market of the event that is not an earlier M3 unit and whose row at k has `binary` true, `closed` false and `active` true, plus every earlier M3 unit of the same event (by its `event_id` at its own k), counted without reading its row after its k; an earlier unit that has since left the listing still counts (disclosed)."
- **Alternative (option b):** amend 10.1, 3.4 and 12.2 to carve out this one read. That reverses the reasoning of MUST 7, so I do not recommend it.

**MUST 2. Define "full day" and the empty case of rule (a) before J0 runs.**
- **Where:** "Full day = 12 classified captures" exists only in code (`:1232-1239`, R16).
- **Why it matters:** one missing slot removes two classified captures, so a day with any missing slot drops out. If no day survives, `rule_a` comes back null. Choosing what to do about that after seeing the output would be a retrospective rule.
- **Text to add to 10.1:**
  > "A full day is a UTC day with 12 classified captures. If J0 yields fewer than 3 full days, rule (a) is not evaluable and the window is extended to 42 days (the branch that keeps coarse rule 1 attainable); J0 is not re-run to obtain a different answer."
- Changing the threshold or the branch is the orchestrator's call, but it must be declared before the output is seen.

## MUST (text, before the design-text freeze; no effect on J0)

**MUST 3. R1 (separate side files).** This is an acceptable reading, but it amends the text. The reason given (catch-up and live passes must give identical status files) is sound. Replace the sentence at 10.2 l.700-701 with:
> "Late, duplicate and off-grid capture ids are each written to their own write-once status file (`late_<id>`, `dup_<id>`, `offgrid_<id>`, with the reason) when their slot is decided, so J2's manifest carries them."

**MUST 4. R2 (J1 refuses without a registration commit).** Acceptable; it is stricter than the text. Add to 10.2:
> "J1 refuses unless the pins file carries a parseable `registration_commit_utc` at least 24 h before `REGISTERED_UTC` (12.6)."

**MUST 5. Rule records after `t_d` (10.2 l.687-688 and 12.2(a)).** Read literally, these void M3: the state's rule ledger does hold records committed after `t_d`, because the merge runs at pass time (k + 6 h or later); the reader filters them out (`lookup_records`, test (v)). Reword to:
> "…the state used at k holds only captures before k; the rule ledger may hold records committed later, and the reader uses only records with commit time ≤ `t_d` (3.5)…"

In 12.2(a), change "used state holding … a rule record committed after t_d" to "used a rule record committed after t_d".

## Rulings on the readings

- **R1, R2:** amend the text (MUST 3, MUST 4).
- **R3:** acceptable. But 2.1 says `spec_sha` is the sha256 of the file *at the registration commit*, while R3 says "after the freeze". Set `design_sha256` at the registration commit.
- **R4:** acceptable. Name the set (`false`, `0`, `0.0`, `f`, case-insensitive) in 6.1. S10 (`c251.fee_class`) treats any served non-truthy value as fee-free; disclose that mismatch.
- **R7:** acceptable. The in-scope part is counted once, at entry, from that capture's sidecar.
- **R8:** not acceptable as written (MUST 1).
- **R13:** the note says the proposal set is "empty", but the code writes no file and `proposals: null`. Keep the code, since unavailable is not the same as empty, and correct the note and 10.2 ("at every processed window capture").
- **R17:** see Memory below.
- **R5, R6, R9-R12, R14-R16:** follow the text and its precedents.

## SHOULD

1. **Memory: q0781 will likely breach 600 MB.**
   - Probe p2 (laptop): importing the code costs 166 MB; adding the pad brings it to 366 MB; staging the state peaks at 411 MB and writes a 114 MB file in 2.6 s.
   - Adding an 800k-record copy of the rules index in memory (shaped like `RulesIndex`) brings it to **586 MB**, before any capture is read.
   - Every pass reloads the whole retained `gamma_rules` directory and holds it alongside the ledger.
   - The pad goes on top of the real records, so the end-of-window *ledger* is covered (about 31 real days plus 30 padded days, against 56 days from 10-20 to 12-15). The in-memory rules index is not padded. It grows with every retained day file, and `RulesIndex.load` still runs on every pass after `END_UTC` until 01-29, even though `merge_rule_ledger:740` skips the merge then.
   - Fix before q0781: skip the load once the window is closed; read only new or unmerged day files (keep the file size or offset in state); stream records straight into `Ledger`.
2. **Wall time.** `j1_runs.jsonl` has no elapsed time, and q0781 is one catch-up run of about 120 captures. A second run on the same store is impossible: the dry window comes from the newest capture, so `spec_sha` changes and the stored state is refused. Add timing per capture and per phase, and add a fixed `--dry-run-end-utc` option so a steady-state pass can be measured.
3. **Serial M1+M2+M3 pass.** No queue draft exists for it, yet 10 and 20 step 8 require it before registration.
4. **Follow-up sidecar fields.** The sidecar rows kept (`wanted`, `:821`) should include every id in `unit_meta`. Otherwise a unit with a sidecar row but no main row loses its status and accepting fields.
5. **`rules_gap` differs between live and catch-up.** Probe p3: if k's day file appears after the live pass, market 37 is `rules_gap` live but `no_rules` on catch-up. The risk is low because a slot is processed only 6 h or more after its grid time. Disclose it or narrow the rule.
6. **`_write_once:1089-1090` re-reads follow-up bytes on a crash re-run.** 10.2 says "the extractor never opens a follow-up file". Either compare the sha recorded in the status instead, or amend the wording.
7. **Two small risks.** An uncaught exception exits with code 1, the same code as "output exists". With `--last-days 8` against roughly 8-day retention, J0 could lose a capture mid-run.

## Memory budget for J0

`mem_mb` only gates the job's start; the hard limit is the 6000 MB address-space cap (`queue/README.md:23-36`). `m2_j1` already pulls in numpy and pyarrow (165 MB on import), so M2-J0's 457.7 MB peak is the right comparison. J0 is safe to run.

## q0780 and q0781

- **q0780:** the arguments are correct, the output (`m3_ch274_j0`) is separate from the real store, it makes no network use, and the seal records `code_sha`, the per-file hashes, the pins and `spec_sha_kind`. Its next action already says to copy rule (a) into the text by hand. **It may be promoted after MUSTs 1-2 with a diff-only check**, with `code_sha` recomputed after the fix.
- **q0781:** its store is separate and correct. Promote it after SHOULDs 1-2, or treat its run as a first measurement that is expected to breach 600 MB.

## Not verified

Host data: records per day, retention of `gamma_rules` files, number of markets per capture, real peak memory on Linux and run time. Whether the M1 and M2 code avoid the same sibling-count read.

Relevant files:
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m3_j1.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m3_spec.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_m3.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_m3_code.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M3_CH274.md`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0780_m3_j0.json`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0781_m3_dryrun.json`
