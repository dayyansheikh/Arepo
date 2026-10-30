# E011 code version ruling (science-reviewer, read-only, HEAD 909a883d, 2026-10-30)

**Verdict: PIN_HEAD_WITH_DEVIATION_NOTE.** Pin the `surprise_snapshot.py` that exists at both ed7dea22 and HEAD (909a883d). Their bytes are identical.

**(a) Effect of afd67c3a: it can make a run fail, but it cannot change any value.**
- The premise is wrong. `forecast.require_local` (forecast.py:70-79) does not restore anything. If the file is missing it raises `ArchivedDataError`, otherwise it does nothing. The ledger entry at EXPERIMENT_LEDGER.md:5820-5821 ("restores a missing extension file from the archive") is factually wrong.
- `analyze()` (surprise_snapshot.py:630-725) never calls `load_capture`. It reads only `alerts.jsonl` and `outcomes.jsonl`. `run_surprise_snapshot.py analyze` returns at :53-55, before any capture is loaded.
- `load_capture` is only reached during live scoring: `Scorer.run_pass` (:431) and `bootstrap_series` (run script :26-38, last 7.5 days only).
- With the registered code, a missing `rows_ext.csv.gz` gave `fee_category="unknown"` and `created_at=None`, so `created_ts` became NaN in `eligible()` (:194). With afd67c3a, it does the same unless `ext_manifest.json` exists, in which case the pass raises. That means either identical output or no output for that pass. It never produces different values.
- This is outcome-neutral for `analyze()`. The only way it could matter: a scoring pass crashing after deployment, which would show up as a missing or non-ok pass in `passes.jsonl`.
- Deploy timing: host checkouts a4c2585c and 8defe614 (both 2026-10-20) contain afd67c3a (checked with merge-base). When the host switched between 10-15 and 10-20 is not recorded.
- Readiness doc LIVE_TESTS_READINESS_2026-10-19.md:228-236 reports 70 window captures, 73 passes all `ok` and 0 shortfalls as of 10-19.

**(b) Why HEAD, not a reconstruction**
- afd67c3a is an ancestor of ed7dea22. Every commit that has the ledger-required fix (:2682) also has afd67c3a.
- A "registered plus ed7dea22 only" file would be a version that was never run, tested or deployed. Rebuilding it would also be a deviation, and a worse one: it brings back silent `"unknown"` filling instead of a loud failure.
- Picking HEAD is not informed by outcomes. The only E011 outcome info in the ledger or readiness doc is counts (14,639 outcome lines, 0 duplicates; readiness :233), and the ledger at :5817 records "no E011 outcome read". I read no alert or outcome contents.

**(c) Draft ledger text**
```
## Deviation (retroactive): archive-aware load_capture in frozen E011 code, afd67c3a (logged 2026-10-30 18:29Z; pre-analysis, not counted)
- What: commit afd67c3a (2026-10-15) added to surprise_snapshot.load_capture: if rows_ext.csv.gz is absent but
  ext_manifest.json exists, call forecast.require_local, which raises ArchivedDataError (fail loudly). Before, the pass
  silently set fee_category="unknown", created_at=None. Nothing is restored; correction to the 18:27Z entry ("restores").
- Found: during E011 analysis prep on 2026-10-30, before the analysis (not before 2026-11-11T13:00Z); not logged at the time.
- Effect: analyze() does not call load_capture; it reads alerts.jsonl/outcomes.jsonl only. In live scoring the change can
  only turn a silently degraded pass into a failed pass; it cannot change any written value. Host ran post-afd67c3a code by
  2026-10-20 (a4c2585c); 73/73 passes ok as of 2026-10-19. Primary statistic, episode rule, window, thresholds unchanged.
- Pin: analysis runs from surprise_snapshot.py sha256 413107af… (= ed7dea22 = HEAD), which contains both changes.
```

**(d) Pin list.** The sha256 values are the same at ed7dea22 and at HEAD 909a883d:
- `backend/astrolabe/research_lab/surprise_snapshot.py`: 413107af882152029da4db8c68bf011ca160382dc3298f55d5f44f3922dda4b1 (registered version was 7c17571c…)
- `backend/scripts/run_surprise_snapshot.py`: 6df4fb39af804a1f414ac5298d6d79458c005766b473bade635f7055115bcf9e (unchanged)
- `backend/astrolabe/research_lab/detector_eval.py`: 7cc2032706fed6a05d4f3edf00beabfeb5bc72eced9d8097d378aaa5e3880f24 (unchanged)
- `backend/astrolabe/research_lab/surprise_moves.py`: 93183416a6bb3ab49ce1d653ac58a7f850deedf9dd2a7c4c459088c3da4d76ca (unchanged)
- `backend/astrolabe/research_lab/detector_specs/FROZEN_SURPRISE_SNAPSHOT.json`: 5c095deba482c3155e361484e7d13454644ad949556ff922d43ccd3376e0b6f2 (unchanged)
- Add `backend/astrolabe/research_lab/detector_specs/sm_learned_v2.json`: af9b9da2ad7e3644bf625a1b51edd4390cdddd34721ce169db99844ca718825d (unchanged)
- Add `backend/astrolabe/research_lab/ml_explain.py`: ac00eac8739433036dab8e317199d5f6cc93cdedb53423fbf27617e24ae25399 (registered version was ba9f0c82…; see (e))

**(e) Other dependencies**
- `analyze()` imports `ml_explain.cluster_boot`. That changed in 47b74e36 (10-15), which added an optional `weights` argument. With `weights=None`, which is what `analyze` uses, the sums, the bootstrap loop, `mean` and `p_pos` are the same code (diff checked). It is outcome-neutral, but it is not in the registered list, so pin it and mention it in the deviation note.
- `forecast.py` changed only in afd67c3a (`require_local`), and `analyze` does not use it.
- `history_backfill.Limiter.get` gained `max_retries=None`, with the default behaviour unchanged. `analyze` only creates a Limiter and makes no requests.
- `detector_eval`, `surprise_moves`, `wallet_sidecar`, `compare` and `provenance` are unchanged since 3e628ec3.

**Defects, most serious first**
1. Ledger :5820-5821 says the code restores the file when it actually raises. Correct it with an appended entry, not an edit.
2. The pin list is missing `ml_explain.py` and `sm_learned_v2.json`, both of which the analysis depends on.
3. The deviation for afd67c3a was never logged at the time. Text (c) fixes this, with outcomes still unseen.
4. Still open from readiness S1 (:146-150): secondaries (c), (e), (f) and (g) are not produced. The wrapper must report them as "not produced", never fill them in.

**Not verified**
- When the host switched to post-afd67c3a code (only that it was in place by 10-20).
- Whether either branch ever fired on the host.
- Before running the analysis, do a counts-only check that ignores outcomes: non-ok passes in `passes.jsonl`, and window alert lines with `fee_category=="unknown"`.
