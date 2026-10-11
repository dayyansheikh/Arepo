# AREPO — Plain-English Progress

**Last updated:** 2026-10-11 09:25 UTC+1
**Current phase:** Phase 3 **closed with a recorded limitation**; fix (D118) being built. **Phase 4 in progress.**
**Overall status:** On track. No decisions needed from you.
**Current objective:** Finish the 24-hour forecasting test (E004/E005/E006), build and run the control-pairing fix
(D118), and grow the order-flow lead into a proper experiment.

## Good morning: what happened overnight
- **Phase 3 closed.**
  - The final live test, D116, passed every engineering check. An independent review confirmed it.
  - One part still needs proving: matched "control" markets never formed in a live run.
- **That gap now has a diagnosis and a fix in progress.**
  - The cause, found by an Opus 5.5 specialist at max effort, is a design limit: too few markets were screened per group, and many sampled markets were dead (one-sided books).
  - **Fable 5.1 reviewed the fix and said "proceed with changes".** It corrected an over-optimistic probability claim. The honest chance of success is about 54–99%, likely in the lower half.
  - Opus is now building the corrected version. After a further review it runs live once.
- **Your data is backed up.**
  - All research data (21 GB, compressed to 2.9 GB) is in your private GitHub repo `arepo-data`.
  - It is verified against GitHub's checksums, and it unpacks to all 206,934 files.
- **E004/E005/E006 collection:** 5 of 12 two-hourly snapshots are done. Results arrive in about 14 hours.
- **New lead (development only):** in markets that actually trade, order-flow features (buy/sell pressure, activity, staleness) consistently add a little predictive power, about +1% R², in both trade-active samples so far. Not proven yet. It becomes a registered experiment (E007) only if it holds over at least 4 samples.

## What AREPO can actually do today
- Run its full research pipeline live in about 24 minutes (proven by D116).
- Snapshot every Polymarket market every 2 hours and log forecasts before outcomes exist.
- Sample order books and trades fairly, with known probabilities.
- Run leakage-safe, fully logged experiments with power calculations, and show them on a Research Lab page (not deployed).

## What the experiments establish
| | Result |
|---|---|
| **E002** | **Confirmed (exploratory):** about 21% of a market's last-hour move reverses within about 5h on unseen data. Tiny, and not shown to be tradable. |
| E003 | Order-book imbalance does not help at about 2 minutes (a useful negative). |
| Data note | About half of "quoted" markets have **never traded**. Only about 22% traded in the last 24h, so research must sample where trading actually happens. |
| Order flow | Promising in trade-active markets (development only). |
| E004/E005/E006 | Collecting. |

## Issues and risks
| Issue | Why it matters | Blocks? | Action |
|---|---|---|---|
| Live control pairing unproven | Weakens future trigger-vs-control studies | No | D118 fix in progress |
| Disk 17 GiB free; D118 needs about 16.6 GB | Tight but fits | No | Rechecked before launch. If needed, the local backup copy (2.9 GB, already safe on GitHub) can be removed, but only with your OK |
| The reversal may be quote noise | It may not be usable | No | E004 tests whether it survives paying the spread |
| The SD-card copy is partial and unverified | Not a backup | No | The GitHub archive is the verified copy; a physical drive is still recommended |

## Decisions I need from you
**None. Autonomous work is continuing.** Parked at your request: website wording, a physical backup drive, compression.

## What's next
1. Finish and review D118, then run it once.
2. Score E004/E005/E006 at 12 snapshots (about 23:00 UTC+1 tonight).
3. More trade-active samples, then possibly register E007 (order flow).

## Scientific reality check
- **Demonstrated:** the full pipeline works live, one forecasting pattern held on unseen data, and data backed up.
- **Unproven:** tradability, stability over days, the order-flow lead, and live control pairing.
- **Validated edge beyond momentum:** **none yet.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D118 notes](implementation/d118/)
