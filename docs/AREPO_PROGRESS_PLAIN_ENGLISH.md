# AREPO — Plain-English Progress

**Last updated:** 2026-10-10 (evening UTC)
**Current phase:** Phase 3 finishing (provisional); Phase 4 development tools under way (Track A)
**Overall status:** On track. One storage decision is needed from you before the final Phase 3 live test.
**Current objective:** Finish the one live end-to-end test of the data machinery (D116). Meanwhile, build the forecasting
tools and run the first honest experiments on data we already have.

## 1. Where we are
AREPO asks whether information available *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum. There are two halves:
- **The research machinery** is almost finished. One live end-to-end test (D116) is still missing.
- **The forecasting experiments** have now started on existing data. Everything there is still exploratory.

## 2. What AREPO can actually do today
- Capture the complete Polymarket market list (about 270,000 markets) with exact timestamps and provenance.
- Sample markets fairly, record pre-prediction order-book history, record prediction moments and measure later outcomes. Each step has worked live, but only in separate runs.
- **New:** turn saved market-wide snapshots into a point-in-time dataset. Features come from one snapshot and the outcome from the next, and the code checks that no future information leaks into the features.
- **New:** fit and fairly compare simple forecasting models with walk-forward testing. Models are always tested on later data than they were trained on.
- **In progress:** a lightweight collector for new market-wide snapshots, at about 15 MB per snapshot instead of 2.7 GB.

## 3. What changed recently
- **The earlier "Phase 3 complete" claim was withdrawn** (D115). The final code still needs one live run.
- **The plan for that run (D116) was written and reviewed.** An independent reviewer found real loopholes: some software timing failures could have been counted as "the market had no data". So we are building an automatic gate checker that classifies every outcome by fixed rules. It must exist before the test is frozen.
- **First experiment (E001), on about 162,000 market snapshot pairs, 2026-10-03 to 2026-10-10:**
  - Recent momentum over one day did not help.
  - About **30% of a market's last-hour price move tends to reverse** by the next snapshot, hours to days later.
  - This held in every test period. Our best simple model explains about 3.7% of price-change variation beyond "no change".
- **That result is exploratory, not an edge.** It was found on old data, it may be quote noise rather than something tradable, and it ignores trading costs. Its coefficient is now frozen. The next experiment (E002) tests it on brand-new snapshots that did not exist when we froze it.

## 4. What we're working on now
- A tool that checks the D116 test mechanically, so its pass/fail cannot depend on judgement.
- The snapshot collector, and the first new snapshots for E002.

## 5. Issues and risks
| Issue | Why it matters | Blocks progress? | What is being done |
|---|---|---|---|
| Disk: about 11.8 GB free, 13.3 GB needed for D116 | The live test needs reserved space | Yes, the D116 run only | We can free about 4 GB by lossless compression with nothing deleted (needs your OK, below) |
| No external backup of raw research evidence | A disk failure would lose it | No, but it raises risk | Recommend backing up `data-dumps/` when convenient |
| The reversal could be quote noise | It might not be usable in practice | No | E002 and its spread/liquidity breakdown will tell |
| D116 may end "pass with limitation" (no matched control pair) | With 2 markets per group, a pair often can't form | No | Disclosed in advance; that outcome still closes Phase 3 |

## 6. Decisions I need from you
| Decision needed | Why it matters | My recommendation | Urgency |
|---|---|---|---|
| Allow lossless compression of 6 old data folders (same bytes, same files, verified before swapping; about 4 GB freed) | Needed before D116 can run; your protective hook blocks it until you start a storage session | Yes. Restart Claude with `AREPO_RETIREMENT_SESSION=1` set, or run `backend/scripts/storage_compress_exact.py` yourself on the 6 folders listed in the checkpoint | Before D116 (after the gate checker is done) |

## 7. What's next
1. Finish the D116 gate checker, have it re-reviewed, freeze D116, free the disk space, then run D116. A pass closes Phase 3.
2. Collect new snapshots and run E002, the first truly prospective test of a forecasting signal.
3. Expand the features (order book, trade flow, related markets) and the models (regularised linear, then boosting) on the same honest walk-forward framework.

## 8. Scientific reality check
- **Demonstrated:** the data machinery works stage by stage. The new forecasting framework runs end to end without leaking future data.
- **Unproven:** the whole final pipeline in one live run, and any signal on unseen future data.
- **Validated edge beyond momentum:** **none yet.** There is one promising exploratory pattern (short-term reversal) awaiting a prospective test.
- **Next phase?** Phase 4 findings stay exploratory until D116 passes. Tool building continues meanwhile.

Detailed records: [AREPO_V2_CHECKPOINT.md](AREPO_V2_CHECKPOINT.md), [implementation/AREPO_V2_DECISIONS.md](implementation/AREPO_V2_DECISIONS.md),
[research_lab/EXPERIMENT_LEDGER.md](research_lab/EXPERIMENT_LEDGER.md).
