# CB5 code freeze check (science-reviewer, 2026-10-29): REVISE

Saved by the experiments autopilot (reviewer read-only). 99 CB5 tests pass; `declaration_sha256()` = `42bde44f…8ede` (matches CB5
§10). No `model_specs/cb5_v1.json`: CB5 is not frozen.

**Matches the design:** census window created_at in [2026-10-11T12Z, 2026-10-26T00Z), non-sports, non-weather, binary; first
3,000 by `sha256(seed|id)`; refuses before 10-27 (`TooEarly`, exit 2) and on headroom (exit 75); wallet hashes blanked before
storage (`cb5_fetch.py:217`); stored prices/trades clipped to <= bound (`:219-226`); G1/G2 read only `rep_cohort`
(`run_cb5.py:450`); replication cohort starts >= `T5_rep_start` (disjoint); `assert_census_frame` blocks outcome columns.

**Defects (most severe first):**
1. Truncated trade lists can give the wrong first trade (`hb.fetch_trades` newest-first, 10,000 cap); breaks the seed set, G-ii,
   G-v; stored rows can pass true first trade + 1h (never L + 24h). `census_g_cohort` (`cb5_run.py:397-407`) ignores
   `trades_truncated`. Fix: exclude truncated markets from G-ii and G-v; report "unavailable (truncated)" separately.
2. A failed fetch is recorded "done" (non-200 trades -> `truncated`; non-200 prices -> `[]`, `cb5_fetch.py:91`). Fix: distinct
   `failed` status, not done; census counts it separately.
3. Census can run on a partial cohort; output is permanent. Fix: refuse (exit 2) unless the cohort manifest shows `complete: true`.
4. Listings input not checked or recorded (`read_listings`, `cb5_run.py:433-435`, skips non-extracted silently); manifest lacks
   seed, selected-id hash, listings-manifest sha256. Fix: record all three; refuse to resume if the selection hash changes.
5. No fetch-side tests (`census_trim`, `select_cohort`, `cohort_fetch` wallet blanking/price clipping/failure status,
   `cohort-fetch` refusals exit 2/75).
6. Disclosure gap: design says no historical fetch reaches `T_seal` (`CREATIVE_BATCH_5.md:123`), but census cohort rows reach
   ~10-27 > `T_seal` 10-22. Add a disclosure line for the census cohort.
7. q0106 `depends_on` q0105, a held draft (ledger:1364), not in jobs.

**Lapsed dates:** `T5_rep_start` = max(2026-10-29T00:00Z, first complete capture >= CB5 freeze commit + 2h); floor passed, the
freeze-time term governs; nothing lapses. q0106's "run before 2026-10-20T03:00Z for the J4 count" lapsed; J4 "has no
release-copy fallback: a deleted capture appears as `n_missing_raw`" (§10). §2.8 headroom "<= 12 GB" is operational, outside the
declaration hash: use precondition (a) or record the current guard.

**Promotion conditions for q0103b:** (1) fixes 1-5 committed and tested; new declaration hash recorded in §10 (`cb5_fetch`,
`cb5_run` are in the hash). (2) Host `cb5_extract/manifest.json` shows every complete capture starting in [2026-10-11T12Z,
2026-10-27T00Z) as `listings.status=="extracted"` or `"missing"` with reason after `--retry-missing`; counts vs host snapshot list,
`prev_chain=="broken"` count, counts + manifest sha256 in the release commit. (3) Deployed `arepo_pass.sh` uses
`--data-dumps-max-gb 50`. (4) §2.8 headroom precondition recorded. (5) Lane `net`. (6) q0106 only after the cohort manifest is
`complete:true` and q0105 is resolved and recorded.
