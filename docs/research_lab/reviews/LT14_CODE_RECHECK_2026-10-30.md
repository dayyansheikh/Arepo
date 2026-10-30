# LT14 census code fixes: diff re-check (science-reviewer, 2026-10-30; read-only)

**Verdict: ACCEPT_WITH_FIXES.** I accept the code fixes for MUST 1-4 and SHOULD 1-3 and 5-7. One part of the MUST 5 fix, the restore draft q0743, can silently do nothing, so it needs fixes before q0741 is promoted. MUST 4 also needs a narrower comparison.

## Verified
- `LIVE_TESTS_14.md` still hashes to `f047c000…f815`. The file at b6bb71a7 is the same.
- `git diff --stat fbc22f24 b3b6e3ed` is empty for the E026 frozen files, `model_specs/` and `backend/astrolabe/signal_engine/`. `test_pinned_files_hash_to_the_pins` passes.
- The declaration sha changed from `71ec21e5…` to `d2b89b1a…`. I loaded DECLARED from both commits and diffed them key by key: the only difference is `/mde/rule`.
- The code sha256s match the code note: `db6c7a81…`, `12c6c934…` and `aaa12b51…`.
- `pytest tests/test_live_tests14.py tests/test_live_tests14_census.py`: **56 passed**.
- I re-ran my earlier probes against the new code, on synthetic data in `/tmp/lt14rc/probes/p_all.py`:

| Probe | Result |
|---|---|
| Baseline | `census_pass`, 134 units |
| Sidecar altered, single root | refused |
| Sidecar altered in the second root only | refused |
| Sidecar deleted, single root | refused |
| Quotes sealed as absent at k+1 (and one inside the span) | `census_pass`, no refusal |
| Absent file reappears after the seal | output identical; it is still read as missing |
| Sidecar absent at seal, then reappears | no refusal; the origin stays uncovered |
| Second seal | "seal is written once; refused" |

## MUST / SHOULD status
| Item | Fixed? | Evidence; does the new test fail on the old code? |
|---|---|---|
| MUST 1 | Yes | `lt:288-300` checks every copy and needs at least one. Old code: probe 134→127, `census_pass`, so `tc:341` would fail. |
| MUST 2 | Yes | `absent_files` in the seal; `_chk` returns False (`base:315-322`). Old code raises `Refused`, so `tc:359` fails. |
| MUST 3 | Yes | `de_cluster(…, 1.0, …)` at `lt:472-473`; scaled values are print-only. The hand fixture (DE 1.025/1.065/1.08) would not match f=10.5. |
| MUST 4 | Partly | Compares `registry_entry` and the spec's canonical sha (`lt:280-285`). Old code refuses an unrelated registry change, so `tc:431` fails. But see F3. |
| MUST 5 | Code yes, draft no | q0741 `depends_on` q0743; the second root path is correct in q0741 and q0742. See F1 and F2. |
| SHOULD 1 | Yes | `spec_error`; `spec_used_sha256`; the runner is in `CODE_FILES`. |
| SHOULD 2 | Yes | `_durable` withdrawal; the fail-safe is checked from sidecars before any features row; the runner writes both (exit 0). |
| SHOULD 3 | Yes | `lt:226-227`; old code returned `ok`, so `tc:506` fails. |
| SHOULD 4 | Not yet | The A1/A2/A8/A11 rulings and the `log_file_mismatch` ruling are not in `EXPERIMENT_LEDGER.md` (grep). Required before the seal. |
| SHOULD 5 | Yes | `SEAL_GLOB`; probe confirms. |
| SHOULD 6 | Yes | `rn:121-126`; q0742 lists the copy as an output. |
| SHOULD 7 | Yes | `base:453-455`. The new `tb:183` test fails on fbc22f24 (I ran the new tests against the old tree). |
| Weak tests | Yes | `or True`, the tautology and the `deepcopy` check are replaced; per-file read counts; `mid_check_share` added to the gate-flip test. |

Running the new census tests against the old code mostly stopped at fixture setup, because the new tests use new APIs (`ALLOW_NONDECLARED_SPEC`, `seals_dir`). So "fails on old behaviour" for those rows is shown by the probes and by reasoning, not by a direct run.

## Rulings
- **`log_file_mismatch`:** consistent with the frozen text, not a deviation. Design 1.4 (l.228-229) says a unit exists only if P's file was logged before k+1, otherwise the capture is `late`. A log line with another sha256 does not log the sealed file. So this status is a named sub-case of `late`/not logged. Counting it against the 90% line is what the text requires. Record in the ledger: "log_file_mismatch ⊂ late (1.4); reported separately".
- **MUST 4 and `status`:** not acceptable as written. The audit already checks the model id, the spec sha and the canonical sha. The audit does not check `status` (`base:206-250`), so including the entry in the comparison adds only `status` and `added_utc`. The design treats P stopping as `unavailable_spec`, not as a refusal (l.217-219), and refusals are limited to l.534-535. A demotion between the seal and the census would block the one-time census without a durable record.
- **Can old sidecars still be restored on 11-17?** Yes, in principle. Under `--delete`, a host file is deleted only if it is in a verified, published release with the same sha256 (`COLLECTION_HOST.md:101-104`). The source is the arepo-data releases, via `restore_from_archive.py`.
  - Snapshot retention is currently **12 days**, not 8 (`archive_retention.json`, 99984534; to go back to 8 after q0147c). At 12 days, no span sidecar is deleted before about 11-19, and q0743 is only a safety net.

## Required fixes
- **F1 (HIGH, q0743): a stale catalogue makes the restore a silent no-op.**
  - Selection uses the repo catalogue. With no `--tag`, the tags default to the catalogue files (`restore_from_archive.py:248`).
  - The catalogue stops at `data-20261020-dsheikh.jsonl`, and no cron regenerates it (only manual `archive_catalogue.py`).
  - A selection that matches nothing returns passed with exit 0 (`:177-179`). q0741 would then seal about 27 origins as uncovered, which cannot be undone.
  - Fix:
    1. Add a prerequisite (a job or a promotion step) that regenerates the catalogue through the 11-17 release.
    2. Pass an explicit `--tag` list.
    3. Add a post-restore check in `lt14_restore_guard.py` (not hashed; LT14-only): every span slot with a host `meta/` must have a sidecar in one of the two roots, otherwise exit 3 "STOP AND ASK THE OWNER".
- **F2 (MEDIUM, q0743 resources).**
  - `disk_mb: 400` is too low. Catalogue rows show `rows_ext` at about 37.8 MB each, so about 110 archived span sidecars would be about 4 GB (estimate).
  - The guard checks free disk only. Data-dumps was 38.9 GiB on 10-28, against the pass cap `AREPO_DATA_CAP_GB=55` (`arepo_pass.sh:11-18`). Adding the LT12/LT13 restores the same morning could make collection skip passes.
  - Fix: set `disk_mb` from `--measure-only`, and have the guard also refuse when used + bytes + reserve exceeds the cap. Alternatively, limit the globs to 11-07..11-10. This still covers a census delayed about 1 day.
- **F3 (MEDIUM, MUST 4).** Compare only `model_id`, `spec_sha256` and `added_utc` plus the canonical sha. Print the sealed and current `status`. Add a test where a changed status does not refuse. This changes the `live_tests14.py` hash, so re-announce it before the seal.
- **F4 (LOW).** Write the SHOULD 4 rulings and the `log_file_mismatch` ruling into the ledger before q0741.

## q0740
**May be promoted now.** It reads only schemas and the registry, does not depend on q0743, and none of F1-F4 changes its inputs. q0741 waits for F1-F4. q0742 waits for the seal.

## Not verified
- Host state: the catalogue on the Oracle checkout, current data-dumps usage, the actual November `rows_ext` sizes, and which retention rule (8 or 12 days) will apply on 11-17. I made no network or ssh access.
- Real engine data (not read).

Files:
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/live_tests14.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/live_tests14_base.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/lt14_restore_guard.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/restore_from_archive.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0743_lt14_sidecar_restore.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/data_catalogue/
- /Users/DayyanSheikh/Projects/astrolabe/scripts/oracle/archive_retention.json
- /Users/DayyanSheikh/Projects/astrolabe/scripts/oracle/arepo_pass.sh
- Probe: /tmp/lt14rc/probes/p_all.py
