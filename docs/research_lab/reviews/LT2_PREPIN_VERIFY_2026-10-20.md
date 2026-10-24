# LT2 (E012-E014) pre-pin verification, 2026-10-20 ~17:50Z (science-reviewer; read-only; saved by the orchestrator)

**Verdict: PIN_OK_WITH_DISCLOSURE.** No code change required; correct the design text, then pin `SPEC_SHA256`.

## Input checked
Host dry run of the R1 collector, 2026-10-20 17:41-17:47Z (root `/tmp/lt2dry`, not `~/arepo`), code a532ee33,
`run --max-items 4 --dry-run-start 2026-10-19T00:00:00Z --dry-run-end 2026-10-20T00:00:00Z`, repeated 20 times under
`ulimit -v` 960 MB until exit 75: peak RSS 584 MB; exits 0 or 75, at most 32 s; 34 series, 34 status, 7 E012 and 24 flow
files, 55 MB; `x_skip6`, `trunc1h`, `vol24_i`, `spec_sha` 010a7ba131936e8f, `code_sha` 88ee00b20fbe8241 in the lines;
`pinned=false`; no statistic on any target computed. Every one of 3,918,532 status rows was `one_sided`.

## Findings (most severe first)
1. **(Medium; disclosure only) The design overstated what R1 finding 3 delivered.** Complete captures query Gamma with
   `closed=false` (`backend/astrolabe/research_lab/collector.py:38`), so `status_frame` (`live_tests2.py:333-342`) can never
   write `closed`. A market that closes or resolves before its target is labelled `unavailable_absent`, which also covers
   markets delisted or archived. `inactive` remains possible in principle (not seen in the dry run). "Resolution and closure
   are therefore measurable" (`LIVE_TESTS_2.md` §1.3) was false as written.
   - Effect on results: none. `attrition_summary` and `_unavail` count every status starting with `unavailable` regardless of
     reason (`live_tests2_analysis.py:546`, `:147`); the 5 pp label, bounds and Holm are unchanged; the finding's intent
     (differential attrition detected) is met. Only the by-reason breakdown is mislabelled.
   - Required text (applied in §1.2, §1.3 and the finding-3 row of §9): captures list open markets only; `unavailable_closed`
     cannot occur; closure/resolution appears as `unavailable_absent`, reported as "closed, resolved or removed"; the
     attrition rule uses the unavailable share regardless of reason.
   - Leave the code alone (docstrings at `live_tests2.py:17-19`, `:333-336` are misleading but behaviour-neutral; editing them
     would change `code_sha256`). Optional descriptive split of `absent` by `hte_h` not required (not adopted).
2. **(Low) The pre-pin record in §6.2 was out of date**: items (b) dry run and (c) `dev_fit.json` were still listed as owed;
   (c) was verified in `reviews/LT2_RECHECK_R1_2026-10-20.md:40`. Add the dry run to §6.2 (applied).

## Verified
- Normalised code hashes recomputed: `88ee00b2…8053` (`live_tests2.py`) and `a7b5c781…1ab0` (`live_tests2_analysis.py`) equal
  the spec map; the first matches the dry-run lines' `code_sha`.
- `sha256(model_specs/live_tests2_v1.json)` = `010a7ba131936e8ffda243a1858f5be8864562f2b036d5863af7b785f5d6584c`, matching
  the dry-run `spec_sha`; the spec does not hash the design doc, so the doc edits leave it unchanged.
- `dev_fit` `source_sha256` in the spec equals §4 and the E007 ledger line (`EXPERIMENT_LEDGER.md:587`).
- Census: `vol24_cap` = +inf recorded.

Nothing else owed. Pin `SPEC_SHA256` = `010a7ba1…584c` with `REGISTERED_UTC` 2026-10-22T00:00:00Z; if the pin commit lands
after 2026-10-21T22:00Z, §1.1 moves the start.

## Could not verify (no host access)
Host dry-run figures, the 3,918,532 / 260,392 row counts, the host `dev_fit` hash (taken from the orchestrator and the R1
re-check); that no capture contains `active=false` rows.
