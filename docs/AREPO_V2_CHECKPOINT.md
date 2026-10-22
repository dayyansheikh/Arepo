# AREPO v2 live checkpoint

**PHASE 3 CLOSED.**
- D116 was PASS_WITH_LIMITATION, giving D117.
- D118 then PASSED live on 2026-10-11, validating the control-pairing *mechanism* on liquid markets (D119).
  - Scope and disclosures: `implementation/d118/D118_ADDENDUM.md`. Pair 1 was very probably sibling markets; 5 of 7 triggers had no control.

**PHASE 4 IN PROGRESS.** See `implementation/phases/PHASE_04_EDGE_EXPERIMENTS.md` and the ledger `research_lab/EXPERIMENT_LEDGER.md`.
User dashboard: `AREPO_PROGRESS_PLAIN_ENGLISH.md`; its `Last updated` uses `TZ=Etc/GMT-1 date`.

## Interactive session state (2026-10-21 ~09:50Z)
- **Web (all merged by Claude under the owner exception in CLAUDE.md):**
  - #21 and #24: Claude board (costs, messages, controls).
  - #22 and #25: security keys / passkeys, unlock-method chooser, per-device trust.
  - #23 (signal autopilot): signal engine section.
  - Production schema is v18.
- **Owner key:** an iCloud Keychain passkey (synced to the iPhone). Recovery codes are with the owner. DB reset steps are in docs/lab/SECURITY_KEYS.md.
- **Autopilots:** two run on the Mac:
  - experiments: `~/.arepo/autopilot`, label experiments;
  - signal engine: `~/.arepo/autopilot-signal`, worktree ../astrolabe-signal-auto, branch auto/signal-engine.
  - Owner messages arrive in each instance's INBOX.md via /lab/claude.
- **Host resize:** owner-approved, free, to 2 OCPU / 12 GB, scheduled 2026-10-22 02:40Z (resize_host.py, post_resize_check.py,
  COLLECTION_HOST.md). No deploys 02:40–03:45Z. After DONE: append the ledger deviation draft, remove the cron, re-promote MC1 (q0116*) on 12 GB.
- **E026 copy-skilled wallets:** owned by the experiments autopilot. The owner wants a phone notification at each milestone. Freeze is due before 2026-10-25.
- **New streams live:** PredictIt, Smarkets, ESPN odds, gamma rules, reward params.
- **Merged development work:** cost model, maker-rewards study, wallet-skill study (WS1).

## Interactive usage push (owner: use all usage before Wed 21 Oct morning), started 2026-10-19 ~21:20Z
Parallel worktrees: one branch per stream, each merged by the interactive orchestrator after review. The autopilot keeps the CB8–CB17 pipeline.
- `feat/live-tests-2` (`../astrolabe-live-tests`): new prospective live tests E0xx. Designs, light collectors and drafts; challenger review, then freeze.
- `feat/creative-r6` (`../astrolabe-creative-r6`): Fable xhigh creative round 6, CH118+.
- `feat/prior-art` (`../astrolabe-prior-art`): literature map of PM anomalies against AREPO status, and gaps.
- `feat/new-streams` (`../astrolabe-new-streams`): new keyless prospective collectors (drafts, dry runs).
- `feat/live-audit` (`../astrolabe-live-audit`): readiness audit of registered live tests' analyses (counts only, no peeking).
- `feat/cost-model` (`../astrolabe-cost-model`): a realistic taker/maker execution cost model (development).
- Web: PR #20 (members admin) is waiting for the owner's merge. /lab is live (PR #19).

## Owner Lab dashboard (/lab), 2026-10-18 (interactive session, user-approved incl. production deploy)
- **Spec:** `docs/lab/LAB_DASHBOARD_SPEC.md`. Web code: branch `feat/lab-dashboard`, NOT yet on production.
  - aa166b7: frontend /lab; 1053cd1: API + 2 additive tables, schema v14.
  - Tests: backend 24 new, frontend 129, build OK.
  - Local end-to-end check: signed mac push 204; forged push 401; unauthenticated 401. The host key matches the committed public key.
- **Clients and registry:** merged into this branch (5e0f0b2). `scripts/lab/lab_host.py` (host, 10 min) and `lab_mac.py` (Mac); science-reviewed
  `docs/research_lab/lab_dashboard/registry.json`. The host cron line in crontab.txt is commented out until the API is live.
- **Blocked on the user:**
  - The repo hook forbids pushes to `arepo-free-production-v1` from Claude.
  - The Mac's git credential helper `/usr/local/bin/gh` is x86_64 and fails after the 10-18 macOS update ("Bad CPU type"), so no push works.
  - The user fixes gh (e.g. installs Rosetta or an arm64 gh), pushes `feat/lab-dashboard`, and merges the PR into `arepo-free-production-v1`.
- **After the merge:**
  1. Verify the Render build/migration and the Vercel deploy.
  2. Set `is_superuser=true` for the owner account (approved).
  3. Deploy to the host, uncomment the lab cron, and install `scripts/lab/com.arepo.lab-mac.plist`.
  4. Smoke-test with `--no-commands`, then a pause/resume round trip.

## Second Always Free server: auto-retry running (2026-10-17 15:12Z, interactive session)
- **Approval:** the user approved a second free A1 instance (1 OCPU / 6 GB / 100 GB boot; totals 2/12/200 = the tenancy's
  free limits) to move some experiments onto. London AD-1/AD-2 were out of host capacity, so the user chose the auto-retry.
- **How:** `scripts/oracle/oci_retry_create.py` runs on the host every 10 min (cron, flock, `~/oci_venv`, API key in
  `~/.oci`, never leaves the host). It refuses if the result would exceed the free limits, never creates a duplicate, and
  stops itself and sends a phone alert once `arepo-research` exists.
  - Log: `~/arepo_collector/logs/oci-retry.log`. Stop: `touch ~/.arepo/oci_retry/DONE`.
- **First runs (15:12Z):** "Out of host capacity" in both ADs. One AD-2 call returned a transient 401, and the next run was fine.
- **q0116b (MC1 dev run): PARKED on 2026-10-17 by the user's instruction, as a backup, not dropped.** Both attempts died in
  about 16 s at the 2 x 3200 MB address-space cap (`_ArrayMemoryError`). The new queue status `parked` never starts until
  `queue_worker.py retry <id>`. Revive it on the second instance, or with a measured cap. Do not create a q0116c on this host meanwhile.
- **Next, once created:** set up the instance (OL9, Python 3.11 venv, repo, ssh alias), then move queue `cpu`-lane jobs there.

## Host disk: RESOLVED (2026-10-17 ~15:05Z, interactive session)
- **Resize:** boot volume 46.6 -> 100 GB in the OCI console, user-approved. It stays Always Free: home region, no other
  volumes or backups, 100 of 200 GB used. The host was grown online with the rescan plus `oci-growfs`.
- **Result:** root is 89 GB with 61 GB free. Collection and the monitors were uninterrupted.
- **Collector cap:** 16 -> 45 GiB (`arepo_pass.sh`, deployed 0122e3e). The 4 GB free-disk guard is kept.
- **Per-job guards:** raised to **40 GiB** in every pending job and draft by the autopilot (36d908f, deployed 15:35Z;
  q0120b was running and stays at 14). New convention: `--data-dumps-cap-gb 40`.
- **Relocation:** the /var/oled relocation is not needed and was not done. Symlinked dirs could hide files from recursive
  globs.

## (superseded by the entry above) Host disk (2026-10-17 ~14:35Z, autopilot): eased, not solved
- **Was (14:30Z):** data-dumps 13.1 GiB against the 14 GiB collector cap, about +1.1 GB/day; root free 6.0 GB against the
  4 GB guard. The 8-day snapshot rule frees nothing until about 21 Oct (host captures start 10-13/14).
- **Done (a8bbe68):** `dnf clean all` (1.5 GB), `dnf-makecache.timer` disabled (it rebuilt the cache within a day; undo
  with `sudo systemctl enable --now dnf-makecache.timer`), journal vacuumed to 60 MB (0.2 GB). Root free 6.0 -> 7.5 GB.
  Collector cap 14 -> 16 GiB, so the 4 GB free-disk guard binds first (about 20 Oct). q0120b data-dumps guard 13 -> 14
  (ops only; its output cap stays 0.25 GB).
- **Blocked by the evidence hook (correctly, not bypassed):** relocating idle data (`ml_cache` 1.4 GB and
  `history/h1_first,h3_power,h5_cb1*,h6_weather` 1.7 GB, unwritten for 6 h+) to the separate 10 GB `/var/oled` volume
  (9.1 GB free; holds only pcp logs and the empty kdump dir) as a verified copy plus symlink. `protect_evidence.py`
  blocks move/delete under data-dumps unless a user-approved retirement session is running. **Dashboard approval item.**
  Alternative: the user grows the boot volume in the OCI console (Always Free includes 200 GB of block storage; the boot
  volume is 46.6 GB).
- h7_cb4_series `walk_partial*.jsonl` is already 1.3 GB uncompressed (q0082f).

## Standing user decisions
- Work autonomously. Use parallel agents where there is real cause.
- Specialists: Opus max, or Fable 5.1 used sparingly. Extra credits are off.
- Never hold two multi-GB jobs at once.
- Data rights are out of scope (private phase).
- **Category scope is undecided**: sports inclusion is the user's later call, so designs stay category-agnostic with category as a parameter.
- **Trading engine:** a possible far-future feature only. Do not touch the trading or execution plans committed by another session.
- Website wording, physical backup and compression are parked.
- Bypass permissions mode is persisted in `.claude/settings.local.json`. The `git push` ask rule has been removed. Branch-delete and worktree-remove asks remain; do not use them.

## State (2026-10-11 ~13:45Z; historical, see the autonomous programme section for live state)
- **Branch:** `chore/arepo-claude-setup`, pushed. Production is untouched. Another session also commits here, so commit only your own files.
- **Backup:** private repo `dayyansheikh/arepo-data`, release `data-20261011`, verified. The local archive parts were deleted 13:4xZ with user approval after a hash re-check; the local manifest and index files remain.
- **Disk:** about 16.3 GB free. D120 launch needs 15,382,085,632 B.

## Multi-signal ML pipeline (user direction, 2026-10-11)
Edge search now goes through combined models plus SHAP, not a chain of single E-tests (memory `multi-signal-ml-direction`).
- **Design:** `research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`. Reviewed twice and accepted; amendment A1 (M3 Laplace-EM, fixed-effect categories) has been re-simulated.
- **Target:** 3-class Gamma-mid move over the next snapshot, δ = 0.005.
- **Confirmation:** one model, fixed-sequence H1 (log loss vs M0), then H2a/H2b (economic). Needs ≥40 development snapshots plus 24 test periods.
- **Code:**
  - `ml_panel.py` (latest 6c5a074): pairs, features, sweep A features, siblings, dependence groups, fold plan, sweep-gap diagnostic.
  - `ml_models.py` (a1de02e): M0, elastic net, LightGBM (20-config search), M3_eb, clustered bootstrap, OOF SHAP, trials logging.
  - `requirements-research.txt` and `scripts/research_ml_setup.sh` (libomp workaround).
- **Sidecar:** `ext_sidecar.py` writes `rows_ext.csv.gz` per snapshot (v2, from pass 7 on). Main files are byte-identical.
- **Clustering:** `research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md` (393249a) concludes ML co-primary = fixture-day groups (event ∪ parentEventId ∪ negRisk ∪ series×UTC day ∪ underlying), with season-level as a sensitivity.
  - Done: ml_panel uses fixture-day `dep_group` plus `dep_group_season`; sidecar v3 adds parentEventId (pass 9 onwards).
- **Runner:** `scripts/run_ml_dev.py` (87fb74c). Gate: 40 consecutive complete snapshots with sidecar, which means about 14–15 Oct. `--dry-run` is available. Placebos are being added.

## Experiments
- E002: Confirmed (exploratory). E003: inconclusive.
- E004/E005/E006: 9 of 12 qualifying. Passes run at 18:31Z, 20:31Z and 22:31Z. Score at 12.
- E007: 2 of 12. Deadline 2026-10-18.
- **Collection runs on the Oracle host (`ssh oracle`) since 2026-10-14 11:29Z** (user-approved; runbook `research_lab/COLLECTION_HOST.md`).
  - Mac launchd `com.arepo.*` is unloaded; the plists are kept as `*.plist.disabled` for rollback.
  - Host cron (UTC): `scripts/oracle/arepo_pass.sh` at `31 */2` (flock, 4 GB free-disk guard, 12 GB data cap); `supervise.sh` watchdog at `@reboot` and `*/5` for the live trade monitor and E009/E010 poller; outcomes at `10 2,14`; notify every 15 min.
  - Code reaches the host only via `scripts/oracle/deploy.sh` (committed tip; unions trials.jsonl both ways). Pull data read-only with rsync.
  - Health: `ssh oracle '~/arepo/scripts/oracle/supervise.sh status; tail -n 12 ~/arepo_collector/logs/collector.log'`.
  - Disk: about 1 GB/day against the 12 GB cap (3.7 GB at cutover), so it fills around 2026-10-22 unless archive rotation is installed (needs user decisions; see COLLECTION_HOST.md).
  - Mac outage: 00:31Z–10:31Z passes on 10-14 were missed and monitors were down ~00:00–10:47Z (ledger: operational deviation). A host validation copy covering it sits unmerged in `/home/opc/arepo_val` pending a design decision.

## D120 (pairing redesign): PASS
- Frozen at 04e71ea (record ea29ae6). Launched once at 14:47Z (HEAD 47375bc).
- Evaluator: PASS, 6/6 group-disjoint complete pairs, 0 engineering findings.
- Challenger: PASS_WITH_CAVEATS. Economics pair shares a driver; reliability is untested.
- Evidence `PHASE_03_D120_EVIDENCE.json`, addendum `d120/D120_ADDENDUM.md`, decision D120/D121 (86004ed).

## Hourly update job
Cancelled by the user at about 18:30 UTC+1 on 2026-10-11 (cron `dbea28e0` deleted).

## Feature-discovery programme (user objective, 2026-10-11 evening)
- **Mapping and governance:** `research_lab/FEATURE_DISCOVERY_PROGRAMME.md` (09afff6), plus Phase 4 amendment A-ML1. M1 is the default F*. Complex arms must beat M1 (CI under both clusterings, ≥2/3 blocks stable, ≥16 dev days). Budgets are cumulative.
- **Done:**
  - `flow_features.py` and `wallet_sidecar.py` (b3923b5): HMAC wallet hashes; E007 files unchanged.
  - `ml_explain.py`: ranks by incremental out-of-sample ΔLL; `demonstrated_incremental_value` vs `descriptive_only`.
  - Horizons h1/h3/h12 plus magnitude and binary targets (389a677).
- **Running agents (usage budget high until Wed 14 Oct; user asked for max progress):**
  - `history_backfill` (CLOB prices-history plus Data API trades; exploratory_historical);
  - non-sports dependence analysis (Opus max);
  - integration (flow/wallet into the panel, evidence_role enforcement, cumulative counter);
  - `history_sources` (historical books, on-chain wallet history);
  - `resolution_dev` (T5 resolution forecasting, Opus);
  - `external_news` (GDELT);
  - `economics` (fees, slippage, paper P&L, break-even).
- **Disk caps:** history 1.5 GB, sources 1 GB, resolution 2 GB, news 0.5 GB.

## Unusual pre-news flow programme (the user's founding goal: Maduro-style signals)
**Design and tooling**
- Programme (Fable): `research_lab/UNUSUAL_FLOW_PROGRAMME.md` and `detector_eval.py`.
- 5 variants FINAL FREEZE at 692ab61 (`UNUSUAL_FLOW_DETECTOR.md`). IF-H1 frozen as f92952cb.
- Theory (Opus max): `INFORMED_FLOW_SIGNAL_THEORY.md`.

**Results**
- Maduro (`CASE_STUDY_MADURO.md`): striking but not unusual against the market's own history.
- Broad backtest and census revision (7dbc7bf): nothing significant; underpowered (26–80 alert episodes against 200–800 needed). Lead only: `uf_new_wallet_concentration` lift 6.9, nominal p 0.045.
- Held-out cases (`CASE_CATALOGUE.md`, 11 cases): alerts before 4/10, but always 36–52h early. The reported flows came in the final hours.
- Cumulative detector trials: 18.

**Conclusion:** rare events can only be tested prospectively, at fine time resolution.

**Live large-trade monitor**
- `live_trade_monitor.py` (c8a291c and later): 5-minute poll of trades ≥ $1k, hashed wallets, wallet age, frozen-rule scores, matched controls, and a separate outcome writer.
- Being fixed: a causal trailing-99th-percentile alert budget with a 7-day warm-up, and a wider control pool.
- NOT installed as launchd: **this needs the user's approval.**

## Other results (overnight 11–12 Oct)
- E004 Supported but not tradable; E005 Not supported; E006 sign-only (ad55b0f).
- T5 resolution: no model beats recalibrated price. The 7d candidate was an artefact (untraded placeholder prices).
- Historical ML (`HISTORICAL_ML_DEV.md`, revisions r1–r3): against M0v, flow adds about 2% direction skill at 2h and 1% at 6h (demonstrated; possibly a series-lag artefact); wallet age shows nothing. r4_book is pending the h2 book table (background job, about 15h).
- GDELT is unusable; the Wikipedia pageviews fallback is built (574b703).
- **E007: Supported** (β 0.0036, CI [0.0017, 0.0053], 11/12 periods). The challenger confirmed it with caveats. The staleness check (dev, 7cffda0) survives excluding the last 5–15 min. Not tradable as a taker.

## Wave 3 workstreams (launched 2026-10-12 ~17:30 UTC+1; heavy-lock convention in `~/arepo_collector/heavy_lock.md`)
1. **Learned surprise-move detector** (Fable): `SURPRISE_MOVE_DETECTOR.md`. If it beats the hand rules on the test months, freeze it and add it to the live monitor.
2. **Hypothesis battery 1: DONE (development).** 72 declared (7a4d80c), one run: 18 pass cumulative BY (m=468). Survivors are flow continuation (aggressive flow strongest), reversal moderators by trade confirmation (quote noise), flow weaker at longshots/quiet markets, price-level drift and one |move| feature. Wallet, cross-market, time, category and book hypotheses are null; ladders untestable. No survivor covers taker costs. Candidates C1-C4 (not registered) are in `HYPOTHESIS_BATTERY_1.md` section 11.6. **Replication on h3_power (HB1-R, e5a3ef3): 16 of 18 replicate under Holm, no shrinkage (median ratio 1.20); still no cost viability; wallet-age nulls stay null except a weak WA2 lead** (`HYPOTHESIS_BATTERY_1_REPLICATION.md`). Cumulative tests now 494.
3. **`h3_power` backfill:** about 10k more markets, oversampling decision-asymmetric categories.
4. **Cross-venue Kalshi lead-lag:** `CROSS_VENUE_STUDY.md` (historical, L1). **Live test E009 registered** (`CROSS_VENUE_LIVE.md`, `cross_venue_live.py`): `REGISTERED_UTC` 2026-10-13T00:00Z, fixed end 2026-11-03T00:00Z, analyse once after 02:00Z that day; no interim outcome looks.
5. **Economic conditions** (liquid markets, large signals, maker-style paper analysis): `ECONOMIC_CONDITIONS_STUDY.md`.
6. **IF-H2 deadline ladder:** development, then possible E008 registration (`IF_H2_DEADLINE_LADDER.md`).

**Live jobs (Oracle host since 2026-10-14 11:29Z):** collector pass, live trade monitor + outcomes, E009/E010 cross-venue poller (+ daily pair refresh) and notify (ntfy topic in `~/.arepo/ntfy_topic` on the host). See `research_lab/COLLECTION_HOST.md`.

## Latest results (12–13 Oct)
- **Economics:** 95 conditions, none after-cost positive (`ECONOMIC_CONDITIONS_STUDY.md`).
- **Battery 1:** 72 hypotheses, 18 survive BY, none cost-viable. Flow continuation is the main real effect; wallet effects are null (`HYPOTHESIS_BATTERY_1.md`).
- **Learned surprise detector** `sm_learned_v1`: test-month lift about 4x, excess +1.8 pts, Holm p 0.008, placebo rank 1/100. It is volatility-driven. Deployed live in the monitor (`SURPRISE_MOVE_DETECTOR.md`).
- **Cross-venue:** Kalshi leads Polymarket by 10–20 min (`CROSS_VENUE_STUDY.md`).
  - **E009 registered:** live test, runs 2026-10-13 to 2026-11-03, analysed once (`CROSS_VENUE_LIVE.md`). launchd job `com.arepo.cross-venue-live`.
  - The historical pairs are being re-audited for matcher errors: 56 of 167 live pairs were wrongly matched.
- **Running:** IF-H2 (E008 is reserved for it) and `h3_power`.

## Registered live experiments (as of 2026-10-13)
- **E009 / E010:** Kalshi→Polymarket lead and gap. Poller on the Oracle host (`supervise.sh`). Analyse once after 2026-11-03.
- **E011:** ungated learned surprise score `sm_learned_v2` on complete-universe snapshots.
  - Registered at 3e628ec; window starts 2026-10-13 14:00Z; analyse once after 2026-11-11 13:00Z.
  - Wired into the host pass `scripts/oracle/arepo_pass.sh` (`run_surprise_snapshot.py score`).
- **Replications on `h3_power`:**
  - HB1: 16/18 replicate.
  - ML flow: 2/4 cells replicate.
  - Frozen gated `sm_learned_v1`: null, because of the deployment gate. The ungated form replicates (excess +5.8 pts).
  - Wallet effects stay null.
- **Ops:** the live monitor crashed at 22:23Z on 10-12 (KeyError). Fixed in 1 commit; launchd now restarts it on any failure; the 11h gap stays missing.
- **Disk:** about 6.3 GB free. A restart would reclaim swap.

## Autonomous programme: live state (2026-10-15 ~19:18Z)
Mission: `research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md`.

### Persistence
- **Server research queue: live and verified.**
  - Worker: `scripts/oracle/queue_worker.py` (cron `*/2`).
  - Specs: `research_lab/queue/jobs/`. Runtime state on the host: `~/arepo/run/queue/`.
  - Tests:
    - Local: deps, error, timeout, invalid argv, kill -9 recovery, stop/pause/resume.
    - Host: `q0001_selftest` was killed with -9 mid-run, recorded as interrupted, and attempt 2 finished `done` under cron at 18:23Z.
- **Claude autopilot: installed and verified (the user approved full power, 2026-10-15 ~20:00 UTC+1).**
  - launchd `com.arepo.autopilot` runs `scripts/autopilot/autopilot.py tick` every 30 min. Each session runs
    `claude -p` with a 5 h cap, `bypassPermissions` and `caffeinate -i`, and sleeps until any usage-limit reset.
  - Verified: a real headless run; kill -9 recovery; the reset parser. Details: `research_lab/autopilot/PERSISTENCE.md`.
  - Session prompt: `research_lab/autopilot/AUTOPILOT_PROMPT.md`. Read-only host view: `scripts/oracle/queue_status.sh`.
- **Cloud routines:** rejected. The minimum interval is 1h and they cannot reach the host without an SSH key in the cloud.
- **One-time reset:** no documented redemption mechanism. The user was alerted by ntfy at about 18:22Z.

### Jobs
- **Queued** (book family; pending step 1 of `research_lab/HISTORICAL_ML_DEV.md`):
  - `q0002_books_h2main`: pmxt book features. Resumable, with repeat-until-complete.
  - `q0003_books_finalize`.
  - `q0004_ml_r4_book`: `run_ml_history.py --revision r4_book --book-table`.
- **Data:** `history/`, `history_sources/` and `ml_cache/` are being restored from release `data-20261013-research-lab` to the host's `~/arepo/data-dumps/research_lab/`, hash-verified per file, using a scratchpad script on the Mac.
- **Code change:** `history_sources.memory_free_pct` now falls back to `/proc/meminfo` on Linux.

## Pending user decisions (2026-10-15)
1. Autopilot: approve as built, ask for a restricted variant, or stay server-only (`research_lab/autopilot/PERSISTENCE.md`).
2. Server GitHub token for archive rotation (needed by ~20-22 Oct; disk cap).
3. E009/E010 overnight gap: include the server validation copy (recommended) or leave the gap.
4. Resend audit (deferred).
5. One-time usage reset (deadline Wed 21 Oct): the user must check claude.ai/settings/usage. Already alerted.

## Exact next actions (for the next session, autopilot or interactive) — updated 2026-10-22 16:30Z
Deploy only from `chore/arepo-claude-setup`; check `ssh oracle 'cd ~/arepo && git log --oneline -1'` = local tip.
Host 2 OCPU / 11.4 GiB since the resize. data-dumps 33 / 40 GB cap: owner approval 8 (restore-tree clearing) is time-relevant.

**Autopilot session 10-22 ~15:59Z (in progress; state at 16:30Z):**
- **Worktree caveat:** agent worktrees (isolation) start from the PRODUCTION tip (e1dfa8a5), not chore. Never merge such
  branches into chore; cherry-pick the agent's own commits.
- **LT7 (deadline: CC7/CS7 finish before 10-28T03:30Z):** probe rule (c) fired -> ruling (C) `listed_carry24h_v2`;
  code on `feat/lt7-reward-carry` 64acdbc4 + 8dd013b9 (design 8fc83a73…, live_tests7.py e1c5c0c6…; fix 1 option (b));
  re-check **OK_WITH_NOTES** (reviews/LT7_REWARD_CARRY_FIX_RECHECK_2026-10-22.md; 143 tests). **NOT yet on chore on
  purpose:** q0602 CV7 (priority 97) must write `live_tests7_census/CV7.json` first (it records the design sha from disk
  at write time). **Next:** when q0602 is `done`: cherry-pick 64acdbc4 and 8dd013b9 onto chore, run LT7 tests, deploy,
  confirm host hashes (e1c5c0c6…, 8fc83a73…), promote q0603 (drafts, work_cc7_rn_v2), then q0604 after q0603.
  Then ledger + registry. Notes for later (after the censuses): `_status_array` in `_reward_cols` no-carry branch.
- **LT8:** fixes on `feat/live-tests-8-code` (2c932e07); implementer re-vendoring from LT7 8dd013b9 (fix 6) and
  reporting LT8's reward handling. Then ask the reviewer (re-check of fixes 1-10 + whether LT8 adopts listed_carry24h_v2).
- **MC1:** q0116f parked; q0116g one-fold profile promoted (priority 45, exclusive, 2 h).
- **CB16-K:** q0393 audit sample promoted (priority 9). When done: science-reviewer blind audit on `audit_K_sample.json`
  only (never the keys file), >= 90/100 genuine twins -> K may be designed in a later batch.
- **CB7:** code on chore (75708661, 4cc77b64, 35a6fd33); q0146 PROMOTED + deployed. q0147: short re-check of fixes 3-8,
  then promote at/after **10-24T01:00Z** after checking the 10-22..10-25 captures exist on the host.
- **CB8-B:** q0165/q0166 queued. **CB9:** q0181 running; q0182 per reviews/CB9_H9_DEPENDENCY_RULING_2026-10-22.md after q0166.
- **Creative round 14** (Fable xhigh) running on `feat/creative-r14` (chore-based: merge is fine).

**Earlier this day (06:00Z):** q0561 LT5 census done (F/H/R dropped, c0700f8f); q0484 size check PASS -> **E022
REGISTERED** (bf730c6f; reader cron `10-59/20` installed on the host 06:0xZ; q0486 analysis queued, not before 11-17T12Z);
LT7 merged + seal committed (cd4f3702) + q0601b promoted; h8 tail/geo seals done. **Queue now:** q0582 LT6 captures
census (exclusive, running) -> q0583 -> q0116f MC1 (6 h) ; q0562 LT5 flow census; q0144; q0601b; CB8/CB16-K.

1. **E026: REGISTERED** (7777ca66, 2026-10-21 15:20Z). q0541 (net, not_before 10-25T00Z), q0542 (10-25T06Z), q0543
   (12-06T12Z). On/after 10-25: confirm q0541/q0542 start and stay healthy (counts only; `run_copy_skilled.py status`),
   send the owner "collection started" note, then weekly counts notes. Re-promote a `failed` collector within 48 h.
   FROZEN until 12-07: copy_skilled*.py, wallet_skill*.py, costs.py, copy_skilled_v1.json, cost_model_calibration_v1.json.
2. **LT5: CLOSED, no test** (524b35ce): F/H/R dropped at q0561, J/O at q0562 (7.3; seals CF5_CHW_CRW.json, CJ_CO.json);
   uncounted; q0563 moot; vendored drift recorded (LT5 tests green). **Retention:** keep the temporary 10-day snapshot rule
   until LT7's q0604 is done, then revert to 8 days (ledger line, deploy). Watch data-dumps (33 / 40 GB).
3. **h8 seals:** q0121 done; `seals/h8_tail_SEAL.json` committed (sha256 2a88f3e5…). q0144/q0145 promoted; when done,
   commit `seals/h8_text_SEAL.json` and `seals/h8_geo_SEAL.json` before q0147 (never retry q0141). **CB8:** W1 not
   testable (counted 1); B continues (q0164 pins write-once, do NOT re-derive; then q0165, q0166). CB9 q0181+ and CB10
   q0201 after their pins.
4. **LT6: CLOSED, no test** (2ac48655): V, D, B dropped at q0582, K at q0583 (6.3; seals CD_CB_CV.json, CK.json);
   uncounted. q0584-q0586 moot (never promote). q0602's dependency on q0584 removed (LT7 text 7 "or its recorded drop").
5. **MC1 q0116f:** when done, write up as development (MULTI_SIGNAL_PIPELINE_DESIGN.md / ledger), record the panel hash.
   If it OOMs: record, park, write the memory profile; no new id without a measured fix.
6. **LT7:** merged (dde3c3c4); seal fix (74c7f5ac); seal committed (cd4f3702, sha256 117e9b45…); q0601b promoted
   (priority 97, ahead of MC1). When q0601b is done: read `common` (counts only); if false, promote q0602 by hand (it now
   depends only on q0601/q0601b), then q0603 and q0604 (drafts; promote each after the previous is done or together,
   their depends_on chain them); if true, challenger ruling first. Censuses must FINISH before 10-28T03:30Z (10-day rule
   kept until q0604). After q0604: revert retention to 8 days. Then phase 2 (reader, analysis, size check q0605, RSS probe).
7. **Creative round 13 merged** (553bd125). **LT8** (CH203, CH202, CH204) on `feat/live-tests-8` (worktree
   `.claude/worktrees/agent-ac703b52d84655da0`): draft 4552cec5 -> R1 REVISE (9f99504d) -> response 164078c8 -> re-check
   ACCEPT_WITH_FIXES (3ec28bad/78f0bae4; 4 fixes: worlds 3/5 restored, vendoring wording, LT5 closed). Fixes being applied
   ~07:30Z by the drafter. Next: verify the 4 fixes, then **design-text freeze** (record sha256 in the ledger), merge into
   chore, registry; file embargo requests (`quietbook`, `swclock`, `sched`; `book0`/`book` to the later of 2027-01-23 and
   LT8's analysis commit) in CANDIDATES before 12-01; then code phase (censuses q0620-q0627 per LT8 8.x).

**E022 (LT4) REGISTERED 2026-10-22** (bf730c6f; REGISTER_OK). Window 10-26..11-16; reader = host cron `10-59/20`
(never also q0485); q0486 after 11-17T12Z. Check the reader log `~/arepo/run/live_tests4.log` after 10-26T00Z (counts only).
q0116f depends_on q0484, so it cannot start first.

**CB17:** window jobs use `--root ../data-dumps/research_lab/cb17_window/creative_batch17` (1c9f604e; the frozen 0.3 GB
cap had counted q0413's input restore). **q0404 smoke PASS 20:12Z (P1-P3 exact; freeze accepted).** q0405 promoted
(f7e98170, base pin 56dc953e… from q0380's manifest). Next: q0406+ after S_8 (10-26T00Z) per the drafts' dates; ruling 6
attestation again with q0406's commit. **Owner approval 8 (not urgent):** a clearing session for finished restore trees
(~9 GB; data-dumps 33 / 40 GB on 10-22).

**LT6 history:** code re-check/fixes/verification FIXES_OK_WITH_NOTES, merged (7ebfcb8b); q0580 restore and q0581 seal done 10-22.
Open should-fix: `e022.pin_commit_utc` check (before the pin). D's P1 is implemented (deadline 11-11T08:00Z met).

**LT7:** R1 REVISE -> response efdcdb6e (CH194 withdrawn, uncounted) -> re-check ACCEPT_WITH_FIXES -> fixes cedfd6be ->
**design-text freeze** (sha256 840f4500...; ledger bda3691b; merged e4b1973d). Embargo applied by the builder (18d4adc5;
`mm_fresh` withdrawal filed). **Code phase 1** (vendored base, seal, censuses CC7/CS7/CV7, runner, drafts q0600-q0604)
being implemented on `feat/live-tests-7` (started ~01:20Z). Then: code freeze check (science-reviewer), censuses before
the sealed capture rows leave the host (10-23..10-29 03:30Z) or from restores, phase 2 (reader, analysis, size check).

**LT5 test guard (pre-existing since 44a7e938):** `test_vendored_provenance` fails because `live_tests4.py` changed after LT5
vendored it. Record `vendored_source_drift_accepted["live_tests4.py"]` (sha256 d80bde72..., reason, date) in
`live_tests5_v1.json` together with the post-census fills (after q0562), confirming every vendored function still
equals its source (the test checks). Do not edit the LT5 spec while q0561/q0562 run.

**Registered and running (no interim looks):**
- E009/E010 (to 11-03), E011 (to 11-10), LT2 E012-E014 (q0460; analysis q0461 after 11-13T12Z).
- **E026** registered 2026-10-21; collection 10-25..11-15, analysis q0543 after 12-06T12Z.
- **LT3 E015** registered 2026-10-21 (2580c58a). Host cron `*/20`; remove it after 2026-11-15T06:00Z. q0475 after 11-15T12Z.

**Queued and in progress:**
- **CB18 closed** (routing record `seals/cb18_routing.json`, fa856ec4): S and P dropped uncounted at census; R/F/M maps;
  k = 0; drafts q0590-q0599 moot. **CB13 closed** (q0282: R1 "not testable (basis)", counted 1).
- CB14 and CB15 closed (W GWC FAIL, P GPB FAIL, counted 2 each; S/E earlier); drafts q0306-q0309, q0349-q0354 moot.
- **Creative round 12 merged** (042e883d; CH191-CH201). **LT7 design draft** from its top 6 (CH195, CH191, CH194, CH197,
  CH193, CH192) being written ~20:50Z on `feat/live-tests-7` (`LIVE_TESTS_7.md`; window not before 12-08). Next: challenger
  R1 (science-reviewer), response, re-check; registry entry; embargo requests in CANDIDATES.md.
- CB16-K q0383 (exclusive, not before 10-22T06Z). CB17 q0404 blocked (above), then q0405.

**Waiting:**
- MC1: after the resize (item 4).
- CB4 q0085 not before ~10-24T12Z. CB5 q0103b on or after 10-27, then q0106. CB3 freeze after q0064 (after 10-25).
- Signal engine: live state in `signal_engine/STATUS.md` (10-22 ~16:40Z: refit q0512 and score q0513 had died at their virtual-memory caps; select_rows now copies the 900k-row frame once, caps re-measured (refit 3400/6000 MB, score as_cap 3000); refit OK 2,887 s / 2.9 GB incl. first fits of se14/15/17/18/19; day-2 leaderboard K 7, no promotion; /lab last-refit time now live; embargo table unchanged since the 12:00Z withdrawals).

## Learned surprise-move detector (2026-10-12 evening)
`docs/research_lab/SURPRISE_MOVE_DETECTOR.md`. Labels fixed and logged before features (`surprise-labels-v1`,
sha `d9cf42f7…`), 1,186 surprise moves in `history/h2_main`, matched negatives, 83 pre-event features, three
learned arms + 5 frozen hand rules, time split train ≤ 2026-05 / valid Jun-Jul / test Aug-Oct. Test months at
the 1 % budget: `en_logit_full` precision 2.25 % vs 0.56 % base and 0.43 % matched controls (excess +1.8 pts,
Holm p 0.008, first of 100 shuffled-label placebos); hand rules 0 %. Value sits in price-path context
(`rv_1d` −, `rv_7d` +), flow/wallet families carry no demonstrated incremental value; paper P&L ≤ 0; no case
clears the budget under the frozen arm. Frozen `sm_learned_v1` (sha `ee7ea5f1…`, `FROZEN_SURPRISE.json`) and
deployed in `live_trade_monitor` v2 (prospective, unregistered). Next: let the live alert stream accumulate;
register (programme §7) only if ≥ 30 episodes with controls; do not revise features on this data window.
- **h3 replication (2026-10-13):** frozen `sm_learned_v1` as specified (direction gate on) is **null** on the
  disjoint h3 primary months (0/63 alerts, placebo rank 0.78); the gate admits only rows with 1 h flow (8 %), where
  the signal is absent. The validated ungated score replicates strongly (1 %: precision 6.5 % vs 0.87 % base,
  matched excess +5.8 pts, CI +2.6/+9.6, weighted +7.2), concentrated in sports/crypto/politics; asymmetric topics
  weak or absent. Combined h2+h3 refit: price path only; flow/wallet families still ≈ 0. Decision for the
  coordinator: freeze an ungated v2 and test it on the complete-universe passes, not the print monitor.
- **E011 registered (2026-10-13):** frozen ungated `sm_learned_v2` (sha `ee227e7e…`, identical terms to v1,
  `FROZEN_SURPRISE_SNAPSHOT.json`) scored on every complete-universe capture by
  `scripts/run_surprise_snapshot.py score` (stage-1 proxies from the rolling capture series, Spearman 0.71 on h3;
  stage-2 exact features for 400 candidates; top 60 alerts + 3 matched controls per capture written before
  outcomes; one price-history fetch per line at t + 24 h 15 min for the surprise label and moves). Window
  2026-10-13T14:00Z to 2026-11-10T00:00Z, single analysis after 2026-11-11T13:00Z (`analyze`). Primary: matched
  excess of the 6 h surprise label, event-clustered, one-sided. Reviewer ACCEPT_WITH_CHANGES applied. **User action:**
  add `caffeinate -i $PY scripts/run_surprise_snapshot.py score --rps 4 2>&1 | tail -2` after `run_flow_screen.py`
  in `~/arepo_collector/arepo_pass.sh`.
