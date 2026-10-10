# AREPO — Plain-English Progress

**Last updated:** 2026-10-10 22:56 UTC+1
**Current phase:** Phase 3 finishing (provisional; D116 frozen and waiting for disk). Phase 4 forecasting work is under way (Track A).
**Overall status:** Needs my decision (backup and storage). All other work continues autonomously.
**Current objective:** Get tonight's prospective results (E002 now, E004/E005 over the next ~24h), keep building the
forecasting loop, and launch D116 once disk allows.

## 1. Where we are
AREPO asks whether information knowable *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum.
- **Research machinery:** built. Its final live test (D116) is frozen; only disk space stands in the way.
- **Forecasting:** a real loop now works end to end. It snapshots every market, logs forecasts *before* outcomes, scores them later, and shows them in the app. **No proven edge yet.**

## 2. What AREPO can actually do today
- Snapshot all ~273,000 live markets in 7–12 minutes (about 27 MB each). Read the order books of the ~43,000 actively quoted markets in about 2 minutes.
- Build leakage-safe datasets and compare models with one shared, tested pipeline. It reproduces earlier results exactly, and every run is now fingerprinted and permanently logged.
- Log frozen-model forecasts before outcomes exist, score them later, and show them on a "Research Lab" page in the app. The page is labelled experimental and is not deployed.
- Sample markets fairly (with known inclusion probabilities) for trade-flow research. The tool is built but not yet run.
- Judge the D116 live test automatically by fixed rules.

## 3. What the experiments establish so far
| Experiment | Question | Status / result |
|---|---|---|
| E001 | Do price/momentum/context fields predict the next snapshot? (past data) | About 30% of the last-hour move tends to reverse. **Exploratory only**; possibly partly quote noise |
| E002 | Does that reversal hold on brand-new data? | Forecasts logged at 19:22 UTC. **Outcome snapshot arrives about 23:36 UTC+1, then scored once** |
| E003 | Does order-book imbalance predict the next ~2 minutes? | **No measurable value** (a useful negative). A combined model helped only in wide-spread, likely untradable markets |
| E004 | Does the reversal hold over 11 new 2-hour periods, and survive paying the spread? | Pre-registered; 24h collection starts about 23:53 UTC+1 |
| E005 | Do related outcomes (in multi-outcome events) correct inconsistent prices? | Pre-registered. On development data the effect points the wrong way, so a negative result is expected but will be tested fairly |

**Method lessons:**
- Related markets in one event move together. Measuring uncertainty by event makes error bars about 4× wider, and that is now the default.
- An independent challenger reviews every important design. This week it caught a flawed E005 feature, and a trading check that was too generous.

## 4. Work progressing in parallel
- An independent **architecture study** (data, costs, ML, product) is now in `docs/research/2026-10-10-architecture/`. Its main conclusion is that AREPO's real risk is **no backup and a full disk**, not computing power.
- Adopted from it now: full fingerprinting and a permanent log of every experiment run, and stated detectable-effect sizes for future experiments.
- Deferred until E004/E005 finish: a new compact file format (about 10× smaller snapshots) and collector metadata. The running series must not change.

## 5. Issues and risks
| Issue | Why it matters | Blocks progress? | What is being done |
|---|---|---|---|
| **No backup of ~21 GB of research evidence** | One disk failure loses irreplaceable data | No, but it is the top risk | Needs your choice of destination (below) |
| Disk: 9.6 GiB free; D116 needs about 13.3 GB + 1 GB margin | D116 cannot launch | **Yes, D116 only** | Lossless compression could free about 15 GB (needs a storage session) |
| The 24h collection runs inside this session | If the session ends, collection stops | No | Reported honestly; collection resumes at the same cadence if interrupted |
| The reversal may be untradable quote noise | Might not be usable | No | E004's spread-crossing check addresses it |
| The live site's "Opportunities" page headlines a momentum call | It overstates what is proven; momentum is our *baseline* | No | Wording fix proposed; needs your sign-off (production) |

## 6. Decisions I need from you
| Decision needed | Why it matters | My recommendation | Urgency |
|---|---|---|---|
| Backup destination | Protects irreplaceable evidence | A 4 TB external disk (~£130), or any 8 GB+ USB stick for a ~2 GB compressed archive now; optionally a free cloud tier as a second copy | **High** |
| Storage session to compress old data losslessly (~15 GB freed, nothing deleted) | Unblocks D116 | Yes, after the backup: restart Claude with `AREPO_RETIREMENT_SESSION=1` | High |
| Production wording changes (rename "Opportunities", label momentum as the baseline) | Honest product framing | Approve; I'll prepare them on a branch for review | Medium |

## 7. What's next
1. Score E002 at about 23:45 UTC+1 and report the result whatever it is.
2. Score E004 and E005 once their 12 snapshots exist (about 24h).
3. After a backup and a storage session: run D116. A pass closes Phase 3.
4. Then: the new compact data format, a trade-flow experiment, and only the experiments that earn one of the 2–4 confirmation slots.

## 8. Scientific reality check
- **Demonstrated:** working, leakage-safe data and forecasting machinery, and one clean negative result (book imbalance at ~2 minutes).
- **Unproven:** any signal on unseen future data (E002, E004 and E005 are pending), and the full Phase 3 pipeline in one live run.
- **Validated edge beyond momentum:** **none.**
- **Next phase?** Phase 4 findings stay exploratory until D116 passes.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [experiment ledger](research_lab/EXPERIMENT_LEDGER.md) ·
[D116 freeze record](implementation/PHASE_03_D116_FREEZE_RECORD.md) · [architecture study](research/2026-10-10-architecture/AREPO_FUTURE_ARCHITECTURE_2026-10-10.md)
