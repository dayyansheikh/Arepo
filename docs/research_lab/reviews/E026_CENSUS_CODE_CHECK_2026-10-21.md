# E026 census code check (2026-10-21) — summary

Independent check of the E026 planning census code (`backend/scripts/run_copy_skilled.py census`, queue draft
`q0544_copy_census`, recorder `copy_skilled.py`) at `c4f3549b`. Verdict: **CENSUS_READY_WITH_FIXES**. This file is a
summary written by the implementing session from the coordinator's relay of the review; the fixes are listed with
their resolution.

| # | severity | finding | resolution |
|---|---|---|---|
| 1 | MED | A skipped sample (sidecar incomplete or files retired) does not advance the per-market last-seen time, so the next usable sample picks up the gap's trades (up to 500 per market). The rate denominator counted only usable samples x 2 h, so rates were inflated after a gap (`run_copy_skilled.py` rate code; `copy_skilled.py` `load_sample_batch` and the last-sent update). | Each usable batch is credited with the time back to the previous usable sample read (the census start for the first one). This matches the design's first-observation rule, under which a gap's trades are first observed, and counted, in the next usable sample; the recorder is unchanged. Skipped-sample counts are reported next to the gate result. q0544 note and LIVE_TESTS_COPY.md 7.5 / 8.2 corrected. |
| 2 | LOW | When nothing can be projected (no signals, empty primary set, no usable days) no gate result was written. | Gates are always written; in those cases the decision is `do_not_register_redesign` with a reason. |
| 3 | LOW | Gate checks compared rounded values. | Gate checks use unrounded values; rounding is for display only. |
| 4 | LOW | A SIGKILL leaves a non-empty work dir holding wallet hashes, and the retry refuses. | The runner writes a marker file into the work dir it creates; at start it removes a non-empty work dir only if it carries that marker (a previous attempt of the census), and still refuses any other non-empty dir. Nothing else is deleted. |
| 5 | LOW | Timing: the job must finish before the 2026-10-22T03:30Z retention run. | q0544 note: promote by about 01:30Z. |

Also noted: the labeller end-date skip added in `c4f3549b` (by another session) is a proposed change to design
section 6 that needs review before the pin; it does not affect the census.
