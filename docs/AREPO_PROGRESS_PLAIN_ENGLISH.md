# AREPO — Plain-English Progress

**Last updated:** 2026-10-12 08:37 UTC+1
**Current phase:** **Phase 3 closed**, with its last gap fixed this morning. **Phase 4 is in progress.**
**Overall status:** On track. No decisions needed from you.
**Current objective:** Build the combined-signal model (many signals, ML + Bayesian, Shapley breakdown) and collect its data; finish the 24-hour forecasting test tonight; run the pairing redesign (D120) once.

## 1. Where we are
AREPO asks whether information knowable *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum.
- **Research machinery:** complete and proven live.
  - The full pipeline passed its final test (D116).
  - The one missing piece, matched "control" comparison markets, worked live this morning (D118 **PASS**).
- **Forecasting:** one confirmed short-term pattern (price reversal), which is not tradable as it stands. More tests finish tonight.

## 2. What changed overnight (11–12 Oct)
- **24-hour forecasting test, scored and independently checked:**
  - Price reversal (E004) is real but **not tradable**. Buying at the ask and selling at the bid lost about 4.5c per share.
  - Linked-market consistency (E005): no value.
  - When reversal is stronger (E006): the direction was confirmed, but the effect size did not carry over.
- **Resolution forecasting** (about 7,500 resolved markets): no model beat the bias-corrected market price. A 7-day "bias" turned out to be placeholder prices in markets that had never traded, so it was rejected.
- **Historical ML** (3,200 markets, 9 months):
  - Most of the apparent gain was just predicting volatility.
  - Beyond a fair baseline, **trade flow adds a small, demonstrated amount of direction skill at 2h and 6h** (about 2%), but part of it may be a data-timing artefact.
  - New-wallet signals: nothing demonstrated.
  - The sanity checks (placebos) now behave correctly.
- **Unusual pre-news flow** (your Maduro idea):
  - **Maduro:** a 6-day-old wallet bought about $32.5k of "Maduro out" at about 7.5c, roughly 3.4h before the price jumped. But similar bets had happened 7 times before in that market with nothing following.
  - **5 locked alarms on about 357 random past markets:** no better than chance, and far too few alarm episodes to tell.
  - **11 reported cases** (Iran strikes, Nobel, Google Year in Search and others): alarms went off before 4 of 10. The "large trade" alarm fired on about half of the case markets against about 1 in 15 controls. But every alarm fired 36–52h early, while the reported bets came in the **final hours**.
  - **So the next step is a live 5-minute large-trade monitor**, now being built and piloted.
- **Trading costs:** a typical round trip costs about 4.5c. Any edge most likely lives in liquid markets or in large predicted moves.

## 3. What AREPO can actually do today
- Run its full research pipeline live, including matched comparisons, in about 14–24 minutes.
- Snapshot all of Polymarket every 2 hours and log forecasts before outcomes.
- Sample order books and trades fairly.
- Run leakage-safe, fully logged experiments with power calculations.
- Back up all research data to a private, checksum-verified GitHub archive.

## 4. Experiment scoreboard
| | Status |
|---|---|
| E002 reversal | **Confirmed (exploratory)**: about 21% of the last-hour move reverses within about 5h; not shown tradable |
| E003 order-book imbalance | No value at about 2 min (a useful negative) |
| E004 reversal (24h test) | **Supported** but **not tradable**: about 23% of the last-hour move reverses; buying at ask and selling at bid lost about 4.5c/share |
| E005 linked-market consistency | **Not supported** |
| E006 when reversal is stronger | Supported on direction only: stronger in illiquid markets and far from close; the effect sizes did not carry over |
| E007 order flow | Collecting (5 of 12) |
| D120 pairing | **PASS** (mechanism; reliability untested) |
| Combined-signal model | Built and reviewed; collecting development data (needs ~40 snapshots) |

## 5. Issues and risks
| Issue | Why it matters | Blocks? | Action |
|---|---|---|---|
| Disk 16 GB free; each pass adds ~150 MB | Fine; the pairing test needs 15.4 GB at launch | No | Run the pairing test soon |
| Comparison markets are often unavailable | Limits future trigger-vs-control studies | No | Any such study must be designed around it |
| Reversal may be quote noise | It may not be usable | No | E004's spread-crossing test |

Data rights are out of scope during the private research phase (your decision, 2026-10-11).

## 6. Your lunchtime checklist (about 10 minutes, in this order)
Full guide: `docs/infra/DEPLOY_RUNBOOK_2026-10-12.md` on branch `fix/infra-2026-10-11`.

1. **Deploy the infrastructure fixes.**
   - Open https://github.com/dayyansheikh/Arepo/compare/arepo-free-production-v1...fix/infra-2026-10-11
   - Click **Create pull request**, then **Merge**.
   - If Render hasn't started a deploy within about 2 minutes: Render → `arepo-api` → **Manual Deploy**.
   - Then tell me "deployed" and I'll verify the live site.
2. **Security SQL.**
   - Supabase → SQL Editor → paste `docs/infra/supabase_data_api_lockdown.sql` (on the fix branch) → **Run**.
   - Run the check query from the runbook and paste me the result (expected: `0 | 0 | 0`).
3. **Archive token.**
   - GitHub → Settings → Developer settings → fine-grained token, with access ONLY to `dayyansheikh/arepo-data` and permission **Contents: Read and write**.
   - Save it in the Arepo repo as the Actions secret `ARCHIVE_REPO_TOKEN`.
   - Tell me "token added". I then run the archive in two steps: export, verify and test-restore first; delete only after that checks out.
   - The archive can always be restored with one command.
4. **Optional: Etherscan key.** Sign up free at etherscan.io → API Keys → create one. In Terminal, run:
   `read -s k; mkdir -p ~/.arepo; printf %s "$k" > ~/.arepo/etherscan_key; chmod 600 ~/.arepo/etherscan_key; unset k`
   Then tell me "key saved".

5. **Email alerts: create a Gmail app password.**
   - Google Account → Security → 2-Step Verification must be on → **App passwords** → create one named "AREPO".
   - In Terminal, run:
     `read -s k; mkdir -p ~/.arepo; printf %s "$k" > ~/.arepo/gmail_app_password; chmod 600 ~/.arepo/gmail_app_password; unset k`
   - Then tell me "gmail saved". I'll send a test email.

Done already: the **live large-trade monitor** is running permanently (approved). Resend is postponed.

## 7. What's next
1. Collection every 2h; E004/E005/E006 scored tonight.
2. Add sanity-check placebos to the model runner; keep collecting for it.
3. First development model fits at ~40 snapshots (around 14–15 Oct).

## 8. Scientific reality check
- **Demonstrated:** the full, honest data machinery works live, comparisons included; one forecasting pattern held on unseen data.
- **Unproven:** tradability, stability over many days, and any signal beyond the reversal.
- **Validated edge beyond momentum:** **none yet.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D118 addendum](implementation/d118/D118_ADDENDUM.md)
