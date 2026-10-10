# AREPO — Plain-English Progress

**Last updated:** 2026-10-10 21:09 UTC
**Current phase:** Phase 3 finishing (provisional; D116 frozen and waiting for disk). Phase 4 forecasting work is under way (Track A).
**Overall status:** Needs my decision (storage) for D116. All other work continues autonomously.
**Current objective:** Turn tonight's prospective experiments into honest evidence, keep a 24-hour snapshot-and-forecast
loop running, and launch D116 once disk allows.

## 1. Where we are
AREPO asks whether information available *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum.
- **Research machinery:** built. Its final live test (D116) is frozen and only waiting for disk space.
- **Forecasting:** a real working loop now exists: snapshot the market, log forecasts *before* outcomes, score them later, and show them in the app. No proven edge yet.

## 2. What AREPO can actually do today
- Snapshot every live Polymarket market (about 276,000) in about 7 minutes, and read ~43,000 order books in about 80 seconds.
- Build leakage-safe point-in-time datasets, and compare models fairly with one shared, tested pipeline. The pipeline reproduces earlier results exactly and supports "remove one feature family" tests.
- Log forecasts from a frozen model before outcomes exist, then score them prospectively.
- **New in the app:** a "Research Lab" page and API show the latest experimental forecasts and their scoring status. They are clearly labelled experimental and are not deployed.
- Judge the D116 live test automatically by fixed rules.

## 3. What the newest experiments establish
- **E001 (past data):** about 30% of a market's last-hour price move tends to reverse by the next snapshot. This is exploratory.
- **Method lesson:** related markets in the same event move together. Measuring uncertainty by *event* instead of by market makes the error bars about four times wider. Earlier confidence was overstated, and all future experiments now use the stricter method.
- **E003 (order books, independently confirmed on a second data round):**
  - Book imbalance and microprice show **no measurable predictive value** over ~2 minutes. That is a useful negative result.
  - A combined model did better, but only in wide-spread, illiquid markets, through spread effects that are probably not tradable.
- **E002 (reversal on brand-new data):** forecasts are logged. The outcome snapshot arrives about 22:36 UTC.

## 4. Work progressing in parallel
- **E004:** a stronger 24-hour test of the reversal over 12 new snapshots, with the first realistic-trading check (does it survive paying the bid-ask spread?). Pre-registered; data collection starts about 22:55 UTC.
- The E004 scorer is being built while the data accumulates.

## 5. Issues and risks
| Issue | Why it matters | Blocks progress? | What is being done |
|---|---|---|---|
| Disk: about 11 GiB free; D116 needs about 13.3 GB plus a 1 GB margin | D116 cannot launch | **Yes, D116 only** | Lossless compression could free about 4 GB (needs your OK) |
| No external backup of raw research evidence | Risk of irreplaceable loss | No | Backup of `data-dumps/` recommended |
| The 24h collection loop runs inside this session | If the session ends, collection stops | No | It will be reported honestly; partial data stays valid |
| Reversal may be untradable noise | It might not be useful | No | E004's spread-crossing check addresses this directly |

## 6. Decisions I need from you
| Decision needed | Why it matters | My recommendation | Urgency |
|---|---|---|---|
| Free about 4 GB by lossless compression of 6 old data folders (nothing deleted, verified before swap) | D116 cannot launch without it | Back up `data-dumps/` externally, then restart Claude with `AREPO_RETIREMENT_SESSION=1`, or run `backend/scripts/storage_compress_exact.py` yourself on the folders in the checkpoint | Now |

## 7. What's next
1. Score E002 after about 22:36 UTC. Score E004 when its 12 snapshots exist (about 24h).
2. Run D116 once storage is resolved. A pass closes Phase 3.
3. Next registered experiments, using the shared pipeline:
   - whether context features help *conditionally*, for example the reversal by liquidity and spread;
   - trade-flow features;
   - related-market signals.

## 8. Scientific reality check
- **Demonstrated:** working data machinery and an honest, leakage-safe forecasting loop.
- **Unproven:** any signal on unseen future data (E002 and E004 pending), and the full Phase 3 pipeline in one live run.
- **Validated edge beyond momentum:** **none.** One promising pattern (short-term reversal) and one clear negative (book imbalance at ~2 min).
- **Next phase?** Phase 4 findings stay exploratory until D116 passes.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md), [experiment ledger](research_lab/EXPERIMENT_LEDGER.md),
[D116 freeze record](implementation/PHASE_03_D116_FREEZE_RECORD.md).
