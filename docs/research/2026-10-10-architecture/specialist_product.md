# AREPO: product research and UX specialist report

Date: 2026-10-10. Read-only review. Sources are cited inline. Repository observations come from `frontend/app/*`, `AGENTS.md`, `PHASE_08_ECONOMIC_PRODUCT.md` and `PHASE_10_PROMOTION.md`.

## 1. What exists today (context only)

- **Routes:** `/` (Opportunities; `/opportunities` redirects here), `/signals`, `/replay`, `/markets/[id]`, `/research-lab`, `/methodology`, `/how-it-works`, plus the auth and account routes.
- **What works:** The copy is disciplined. It repeats "Not a probability, not good or bad" and "Research record, not trading advice", and it shows explicit "unavailable" states ("Arepo shows nothing in place of missing data"). The Research Lab model card is the most honest surface in the product. It shows the frozen rule, the registration commit, the snapshot ID, the receipt window and the validation status.
- **Structural problems:**
  1. The home page is called **"Opportunities"**. That word means expected profit, which contradicts the AGENTS.md rule to "distinguish research priority from expected profit". Phase 08 also says economic value is unproven.
  2. The headline **"directional call"** is defined as "which way this outcome has been repricing". That is momentum, the very baseline AREPO is trying to beat. Putting it first frames the baseline as the product.
  3. Research Lab lists **raw market IDs, not question titles**, and dumps scores as a raw `<pre>` JSON block. It is honest but unreadable to anyone outside the team.
  4. Replay asks "How did Arepo Opportunities perform?". That invites a P&L reading of results that are midpoint moves, not fills. Phase 08 says: "midpoint changes are not fills".
- **Constraints from the phase docs:**
  - Phase 08 requires three separate verdicts (predictive, screening and economic) and four separate claim levels (gross move, indicative opportunity, simulated execution, real fill).
  - Phase 10 requires a source-rights review before any promotion.
  - Any public redesign needs a scoped review.

## 2. Landscape (brief)

- **Polymarket analytics tools cluster around wallets and whales.** They offer live trade feeds, wallet PnL and win rate, insider scanners and Telegram alerts ([QuickNode, Top 10 Polymarket whale trackers](https://www.quicknode.com/builders-guide/best/top-10-polymarket-whale-trackers)).
  - HashDive markets a "Potential Insider Scanner" based on Z-scores ([QuickNode listing](https://www.quicknode.com/nl/builders-guide/tools/hashdive-by-hashdive); [comparison](https://simplefunctions.dev/alternatives/simplefunctions-vs-hashdive)).
  - Polymarket Analytics sells a wallet and leaderboard API ([QuickNode listing](https://www.quicknode.com/de/builders-guide/tools/polymarket-analytics-api-by-polymarket-analytics)).
  - The Graph sells on-chain Polymarket endpoints ([The Graph docs](https://thegraph.com/docs/en/token-api/guides/polymarket/)).
  - Even vendor guides warn that a large trade may be a hedge and that copying whales goes badly. The crowded part of this market sells excitement, not verified skill.
- **Forecasting platforms publish track records as the product.**
  - Metaculus publishes a track record page with Brier scores against a 0.25 "always 50%" baseline, plus calibration views. Third parties have found that the reported figures move with the date filter ([EA Forum analysis](https://forum.effectivealtruism.org/posts/e9htD7txe8RDdcehm/exploring-metaculus-s-ai-track-record); [community predictions](https://forum.effectivealtruism.org/posts/zeL52MFB2Pkq9Kdme/exploring-metaculus-community-predictions)). Lesson: fix the scoring window in advance and show every window.
  - FiveThirtyEight's "Checking our work" shows reliability by probability bin with sample counts, and it admits which models were miscalibrated ([project](https://projects.fivethirtyeight.com/checking-our-work); [70% means 70%](https://fivethirtyeight.com/features/when-we-say-70-percent-it-really-means-70-percent)).
- **Best practice for showing calibration:**
  - Use proper scoring rules.
  - Use skill scores against a named baseline.
  - Use CORP reliability diagrams (isotonic/PAV recalibration with resampling consistency bands). They replace unstable ad hoc binning ([Dimitriadis, Gneiting and Jordan, PNAS 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7923594); [`reliabilitydiag`](https://www.stats.bris.ac.uk/R/web/packages/reliabilitydiag/index.html)).
- **Polymarket terms and data rights (flag):**
  - I could not retrieve the body of Polymarket's Terms of Use. `polymarket.com/tos` renders client-side and returned only a US banner ("Trading is blocked in the United States").
  - Polymarket's own open-source agents repo says the ToS restricts US and other persons from *trading*, while "data and information is viewable globally" ([Polymarket/agents](https://github.com/Polymarket/agents/)).
  - The public API docs publish rate limits and Builder tiers but no API licence ([rate limits](https://docs.polymarket.com/api-reference/rate-limits); [builder tiers](https://docs.polymarket.com/builders/tiers)).
  - Analogous data vendors require a separate written agreement before data is redistributed or used in a customer-facing product ([Telonex ToS](https://telonex.io/terms); [marketdata.app redistribution](https://www.marketdata.app/docs/account/data-policies/data-redistribution/)).
  - **Recommendation:** treat commercial use or redistribution of raw Polymarket data as *unverified*.
    - Before any paid tier, bulk data export or raw-tape redistribution, a human must read the full ToS and ideally get counsel or written confirmation from Polymarket.
    - Derived statistics and Arepo's own forecasts are lower-risk than re-serving raw books or trades, but are still unconfirmed.
    - Do not add "trade this" deep links. They would steer users toward trading that is geoblocked in the US and elsewhere.

## 3. User segments and jobs-to-be-done

| Segment | Real job | What they value | Fit with honest AREPO today |
|---|---|---|---|
| Internal researcher (you, agents) | "Did hypothesis X beat price+momentum prospectively, on what sample, and can I reproduce it?" | Frozen protocols, provenance, raw scores, failure visibility | High: this is the core need |
| Quant-curious forecaster / researcher (external) | "Show me a verifiable record of a model I can't fool myself about" | Timestamps, hash commitments, proper scores, negative results | High, if the record is credible |
| Journalist / analyst | "What changed in this market, when, and is it unusual relative to its own history?" | Plain-language context, charts, sourcing, no hype | Medium-high: descriptive, needs no edge |
| Active Polymarket trader | "Where can I make money, and is someone informed trading?" | Speed, alerts, wallet intel, edge after costs | Low: Arepo cannot honestly serve this without validated economic value |

**Should Labs and the public product share an app?**

- They should share the *backend and evidence store*, not the *information architecture*.
- Labs is a workbench. It is dense, shows IDs and raw scores, and is full of failure states, and it should stay explicitly internal-grade (an `/lab` subtree or a separate deploy behind a flag).
- The public surface should be a curated read of the same ledger.
- Mixing them causes the current problem: the public home leads with trader vocabulary while the honest content sits in an obscure tab.
- One codebase and one design system are fine. Keep separate navigation, separate copy registers and a separate promotion gate (Phase 10).

## 4. Product concepts

### A. Verifiable Forecast Ledger (track-record-first)

- **Target user:** external forecasters and researchers, and the internal team.
- **Core loop:** register a model (frozen rule, commit, hash) → log forecasts at fixed boundaries with a public SHA-256 commitment, published before the outcome window → auto-score when the target time passes → leaderboard of models vs baselines, including dead ones.
- **What it shows:**
  - A per-model page: protocol, status (pre-registered / running / passed / failed / retired), skill vs baseline with intervals, and event-clustered N.
  - A ledger table of every forecast, with commitment hash and outcome.
  - A "graveyard" of failed hypotheses (E003, D082...).
- **Must NOT claim:** that a positive skill score means profit or a calibrated outcome probability, or that results transfer to other horizons.
- **Prerequisites:** none for the ledger itself, which is honest today with zero edge, because it records the absence of edge. Needs scoring infrastructure (exists in part: the E004 scorer) and an append-only, hash-chained forecast log.
- **Technical cost:** low to moderate. Hash chain and log, score pages and a CORP reliability plot. A commitment can be published as a daily digest (e.g. a git commit or GitHub release) for third-party verifiability.
- **Risks:**
  - It is boring until something passes.
  - An audience exists but is small.
  - A long run of nulls must be framed as rigour, not failure.

### B. Market Context Explainer / Anomaly Screener (descriptive-first)

- **Target user:** journalists, analysts and casual market followers.
- **Core loop:** pick or search a market → see what moved, when, how unusual that is relative to the market's own history and its event siblings, and what was observable at the time (spread, depth, volume burst, neg-risk group inconsistency, wallet concentration) → optional email digest of the most unusual moves.
- **What it shows:**
  - A timeline with annotated moves.
  - "Unusualness" percentiles.
  - Liquidity quality (how much of the move happened at a 10-point spread).
  - Cross-market consistency within neg-risk groups (enabled by commit 19d7bd3).
- **Must NOT claim:** that unusual means informed, insider or predictive; that a move will continue or reverse; that a flagged wallet knows anything.
- **Prerequisites:** none predictive. It is descriptive statistics and honest today. It needs good percentile baselines and a careful insider-language ban.
- **Technical cost:** moderate. Market search UX, per-market history and explanation templates. Most data already exists.
- **Risks:**
  - It drifts toward the whale-tracker genre and invites insider readings.
  - It competes with free Polymarket UI charts, so the value lies in context and comparison, not raw charts.
  - Data-rights exposure is higher if it re-serves raw tapes.

### C. Open Lab Notebook (research-process-first)

- **Target user:** methodologically minded readers, potential collaborators or employers, and the internal team.
- **Core loop:** each experiment (E001–E00n) is a page: question → pre-registration (frozen hash and date) → data window → result → verdict → what it changes. A new entry appears when a protocol freezes or a result lands.
- **What it shows:**
  - Hypotheses and their status.
  - Plain-English summaries next to the technical ones, as in the existing `AREPO_PROGRESS_PLAIN_ENGLISH.md`.
  - Effect sizes with intervals.
  - Explicit "exploratory" vs "confirmatory" badges.
- **Must NOT claim:** that exploratory findings (E001 reversal) are established, or anything about generalisation.
- **Prerequisites:** none. It is honest today and mostly a rendering of existing docs.
- **Technical cost:** low (an MDX/static pages pipeline from the repo).
- **Risks:**
  - Narrow audience.
  - Writing burden.
  - It can become a vanity blog if not tied to the ledger.
  - It works best fused with A as its narrative layer.

### D. Alerts-first ("tell me when something unusual or forecast-relevant happens")

- **Target user:** traders and power followers.
- **Core loop:** subscribe to markets or categories → receive an alert on an anomaly or a model signal → click through to context.
- **Must NOT claim:** actionability, urgency or edge.
- **Prerequisites:** to be useful rather than noise, it needs *validated* signals with *economic value after spread and delay* (Phase 08 verdict). Anomaly-only alerts are honest but low-value and invite trading behaviour.
- **Technical cost:** moderate. Resend exists, but the latency expectations of traders, which run to seconds, exceed the current snapshot cadence and GitHub-cron reliability.
- **Risks:**
  - The highest risk of implied advice.
  - Users judge alerts by P&L.
  - Flaky scheduling erodes trust.
  - **Do not build until a signal passes Phase 08.**

**Challenge to attractive-but-empty features:**

- Leaderboards of "top opportunities", signal-strength gauges, red/green directional arrows, and "confidence" meters without calibration evidence all look like a trading product and carry no validated information.
- A big headline number such as "~30% reversal" from an exploratory study (E001) is attractive and premature.
- Wallet "smart money" tags are the most clickable and least defensible feature.

## 5. Communicating predictive value honestly

**Target and metric:**

- Arepo forecasts *midpoint change*, so the primary score is out-of-sample MSE/MAE of Δmid.
- Report it as a **skill score vs baselines**: SS = 1 − MSE_model / MSE_baseline. Report both:
  - B0, the zero-change (martingale/price) baseline;
  - B1, the price+momentum baseline. This is the one that matters for AREPO's question.
- **Incremental value** = SS of model vs B1, with a block or event-clustered bootstrap interval.
- Add a Diebold–Mariano-style loss-difference test clustered by event.
- For probabilistic outcome forecasts, if ever produced:
  - use log or Brier score with the market price itself as the baseline;
  - show CORP reliability diagrams with consistency bands.

**Sample size:**

- Always show three counts: forecasts, unique markets and **unique events (clusters)**. Intervals use the event count.
- Show the share of the score contributed by the top 5 events (concentration).

**Abstention:**

- Show coverage (the share of eligible markets on which the model made a non-zero call).
- Score abstained cases as B1, so selective forecasting cannot inflate skill. Display a skill-vs-coverage curve.

**Economic usefulness:** four separate rows, never merged:

1. Gross midpoint move.
2. Move net of half-spread at entry and exit (touch-to-touch, as in E004).
3. Net of fees and realistic delay at size N.
4. "Real fills: not measured."

Most signals that survive row 1 will die at row 2, as E003 found for wide spreads. Show that openly.

**Status vocabulary:** Exploratory → Pre-registered (running) → Confirmed prospectively / Failed / Inconclusive → Economic: untested / negative / positive-after-costs.

**Example forecast card (public):**

> **Will X happen by Dec 31?** Midpoint now 0.42 (spread 3 pts).
> Model E004-reversal (pre-registered 2026-10-08, commit `3d7335e`, status: *running; not yet confirmed*) expects the midpoint to give back about 1 pt of its last-hour 3-pt rise by the next snapshot.
> This is a forecast of short-term price change, not the chance the event happens. It is smaller than the 3-pt spread, so it would not be tradable at the touch even if correct.
> Forecast committed at 12:00 UTC, hash `9f2c…` (verify). Scored at 12:30 UTC.

**Example track-record page header:**

> **E004 short-term reversal: running.** 1,240 forecasts on 410 markets in 96 events, 2026-10-08 → today.
> Skill vs zero-change: +2.1% (95% event-clustered interval −0.4% to +4.6%). Skill vs price+momentum: +0.3% (−1.9% to +2.5%): **no detectable incremental value yet.**
> After half-spread: negative in 3 of 4 spread bands.
> Confirmation is evaluated only at the pre-registered end date. Interim numbers are shown for transparency and must not be read as a result.
> Coverage 38%. Top 5 events supply 22% of the score.

## 6. Recommendation and staging

**Direction:** **A + C fused as the public product: "Arepo, an open, verifiable prediction-market research ledger".** Add **B as a secondary descriptive layer**, and **defer D**.

- This is the only positioning that is honest at zero validated edge.
- It turns AREPO's discipline (pre-registration, failures kept, provenance) into the differentiator in a field that sells unverified "smart money" signals.

**Stage 0, now (zero edge):**

1. Rename "Opportunities" to a neutral name ("Market movers" or "Screener") and demote it from home.
2. Stop leading with the momentum "directional call". Label it explicitly as "recent direction (baseline)".
3. Make the home page the ledger and lab overview: experiments, statuses and the latest committed forecasts.
4. Research Lab: show question titles and event grouping, and render scores as tables or charts instead of JSON.
5. Begin a public forecast-commitment hash chain now, so that any future pass carries a credible timestamped history.
6. Get a human or counsel read of the Polymarket ToS before any monetisation or data export.

**Stage 1, descriptive layer:** market context pages (concept B) built only from descriptive statistics, with a banned-words list in copy review (insider, smart money, edge, opportunity, confidence).

**Stage 2, after a prospective confirmation (E002/E004 pass vs B1 on event-clustered intervals):** forecast cards on market pages carrying the confirmed status, reliability and skill plots, and still the four-row economic table.

**Stage 3, only after a positive Phase 08 economic verdict at realistic size and delay:** consider opt-in alerts, still framed as research, with no trade links. Re-check data rights and jurisdictional exposure first.

**Three least-certain assumptions and cheap ways to resolve them:**

1. **"An external audience values a verifiable record of mostly null results."**
   - Test: publish a static Notebook/Ledger page and post it to forecasting communities (r/Metaculus, the EA Forum, the Manifold Discord, quant Twitter).
   - Measure return visits and sign-ups for a monthly digest against a "Market movers" page.
   - Do 5–8 short interviews with forecasters on what would make them trust it.
2. **"Journalists or analysts need market-context explanations that Polymarket's own UI does not give."**
   - Test: send 10 journalists who cite prediction markets a one-page mock-up of the context view for a market currently in the news.
   - Ask what they would cite and what they distrust. Run a 5-second test on whether "unusual" reads as "insider".
3. **"Users will read 'predicted midpoint change' and skill-vs-baseline correctly, not as a probability or profit."**
   - Test: an unmoderated comprehension test (Maze, or a Google Form with screenshots, n≈20).
   - Show the forecast card and ask: "What is the chance the event happens?", "Would you make money?" and "Is this model proven?".
   - Iterate copy until misreading falls below roughly 20%.
