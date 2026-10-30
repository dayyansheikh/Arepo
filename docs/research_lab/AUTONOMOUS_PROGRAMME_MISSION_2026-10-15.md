# AREPO — Autonomous Edge Discovery Programme (user mission, issued 2026-10-15)

This is the user's standing mission, issued 2026-10-15 at about 19:00 UTC+1. It is recorded here verbatim in substance so it survives session changes.
- The user's current request defines operational authority.
- Every protected boundary in CLAUDE.md and AGENTS.md still applies.

## Primary mission
Run an aggressive, autonomous, sustained scientific programme to discover reproducible predictive advantages on Polymarket.
- There is no ceiling of 100 experiments. Run as many meaningful experiments, model fits, feature comparisons, interaction searches and robustness checks as the data, server capacity and research standards support.
- Run for at least the coming week and continue beyond it, unless the user stops it or a real approval requirement blocks the work.
- Do actual experimentation and implementation, not proposals.
- **Brute-force hypothesis discovery, not the evidence.** Never manufacture significance.

## 1. Usage reset schedule (as stated by the user; verify where possible)
- **Rolling windows:** about 5 hours.
- **Normal weekly allowance:** resets **Thursday 22 Oct 2026**.
- **Separate one-time reset:** this opportunity **EXPIRES Wednesday 21 Oct 2026**. Do not confuse it with Thursday's reset.

Plan:
- Use up the current weekly allowance by about **Sunday evening, 18 Oct**.
- Then use the one-time reset before it expires, and use that allowance intensively until 22 Oct.
- After 22 Oct, continue on the normal allowance.

Rules:
- Verify the entitlement mechanics and reset times. Don't assume the one-time reset is redeemed automatically.
- If redemption needs the user, **alert them with exact steps and the deadline**. Do not miss Wednesday.
- Order of work:
  - **Phase A (now to Sunday):** research development, experiments, reviews, implementation, hard methodological work.
  - **Phase B (after the one-time reset):** the strongest unfinished experiments, wider screening, tuning, robustness.
  - **Phase C (22 Oct onward):** continue.
- Don't waste usage on repetitive reports, unnecessary agents or circular discussion.
- Never bypass platform limits. Never start paid overage or API billing without approval.

## 2. Real autonomous operation
Find and implement the best authorised persistence mechanism. Options include:
- a supervised server worker (systemd);
- durable queues and checkpoints;
- scheduled non-interactive Claude Code runs where supported;
- native Claude scheduling;
- a combination of these.

A chat loop does not survive session end or usage exhaustion.

Required behaviour:
- **Usage available:** read state, choose the highest-value work, implement or analyse, launch server jobs, review results, generate justified follow-ups, save, continue.
- **5-hour limit reached:** save state, persist tasks and job ids, let authorised server jobs keep running, stop Claude requests, find the next permitted time, resume automatically.
- **Weekly allowance exhausted:** preserve work, keep independent server compute running, wait for a legitimate reset, alert the user if the one-time reset needs manual redemption, resume.
- **Crash:** recover from checkpoints, prevent duplicate runs, verify partial experiments, never overwrite evidence.
- **Job safeguards:** locking, idempotent jobs, bounded retries, timeouts, clear failure states.
- **Testing:** test the mechanism with a harmless real run and a controlled interruption. Don't claim autonomy until it is verified.

If fully autonomous Claude re-invocation can't be supported on the user's subscription, say so explicitly and build the strongest independent supervised experiment runner instead. Never silently switch to billable API access.

## 3. Maximise scientific experimentation
Feature families, not limited to these:
- **Price:** momentum and reversal; acceleration and volatility.
- **Order book and liquidity:** depth, shape and imbalance; liquidity and spreads.
- **Trades:** signed flow; bursts; large trades relative to liquidity.
- **Wallets:** fresh-wallet participation; wallet concentration and agreement.
- **Market context:** time to resolution; extreme probabilities; category and regime.
- **Cross-market:** related-market relationships; event-level inconsistencies; diffusion and lead-lag.
- **Public information:** public information available before the prediction.
- **Modelling:** interactions; nonlinearities; learned thresholds; Bayesian, regularised linear and gradient boosting; justified ensembles; regime dependence; alternative horizons and targets.

Generate hypotheses from:
- literature and mechanisms;
- existing AREPO research;
- completed results;
- residuals and failures;
- well-supported interactions;
- independent review.

Avoid re-running failed hypotheses without new justification.

## 4. Discovery funnel
- **A. Exploratory screening** on permitted historical development data, on the server. Track every attempt:
  - hypothesis, dataset version and provenance, train and validation periods;
  - configuration and hyperparameters, metrics with uncertainty;
  - compute cost and limitations.

  Record nulls and failures.
- **B. Candidate selection.** Rank candidates by:
  - incremental value beyond the baseline and beyond AREPO's stronger existing models;
  - chronological stability and event and calendar robustness;
  - uncertainty, data quality, and resistance to leakage and overfitting;
  - economic plausibility and reproducibility.

  Never select on one strong backtest.
- **C. Intensive modelling.** Careful hyperparameter search, interactions, Bayesian alternatives, nonlinearity, conditional weighting, ensembles, calibration, ablations, SHAP, regime performance. Use nested or otherwise defensible selection.
- **D. Independent confirmation.**
  - Keep untouched final data and never re-optimise against it.
  - Use fresh prospective data where the programme requires it, and respect the limited confirmation slots.
  - Freeze model, features, target, population, scoring and acceptance criteria before collection.
  - Disclose the selection history.
  - Control for multiple testing, correlated markets, overlapping horizons, common events and calendar dependence.
- **E. Economic validation** after spread, fees, depth, slippage, latency, eligibility and realistic fills. Keep forecasting improvement separate from profitability. No real trades.

## 5. Compute and usage
- Inspect real server capacity before setting concurrency.
- Use the server rather than the 8 GB Mac for heavy jobs.
- Prioritise parallel CPU-efficient screening, bounded tuning, incremental features, cached immutable intermediates, reproducibility and checkpointed long jobs.
- Avoid huge redundant datasets. Measure the compute cost per candidate family and stop low-value work.
- **Storage:** verify the GitHub storage arrangement (visibility, security, capacity, licences). Preserve raw evidence and hashes. Nothing restricted, no credentials and no sensitive wallet data in public repos.
- **Models:** Fable for hard scientific challenges, consequential architecture and validation reviews. Respect the stated 50% weekly Fable cap where it applies. Cheaper models for routine work. The aim is maximum useful research, not maximum expensive-model use.

## 6. Independent challenge
A bounded challenger reviews major findings: big improvements, suspicious backtests, novel interactions, wallet claims, diffusion, model promotion, significance and economics.
- The challenger tries to falsify.
- One substantive challenge and one response, then reject, revise or proceed.
- No endless review loops.

## 7. Protect existing work
- Read the governing docs first.
- Preserve the scientific contracts, D116 and its evidence, frozen experiments, the E-series, feature definitions and provenance, history, retention boundaries and production safety.
- Don't duplicate completed experiments. Don't interrupt collectors to launch tests.
- Coordinate workers and file ownership.
- No production redeploy, no destructive live DB changes, no spending and no bypassing security without approval.

## 8. Durable research queue
Each job records:
- priority and expected value;
- data and resources;
- dependencies and status;
- outputs, failures and retries;
- next action.

Prioritise by information gain, importance, cost and readiness.
- When one job is blocked, run another. Stop spending on consistently negative candidates; invest in promising ones.
- When data is insufficient, collect new data rather than reusing the same sample.
- This is a disciplined programme, not a parameter lottery.

## 9. Phone-friendly dashboard
Show:
- whether the programme is running or waiting for a usage reset, and the next scheduled invocation;
- worker health;
- active, completed, and failed or blocked experiments;
- usage and reset milestones;
- leading candidates, models awaiting confirmation, and confirmed findings;
- infrastructure problems and approvals needed.

Rules:
- Exact update times. Separate measured values from estimates.
- Detailed machine-readable results go in a separate place.
- Interrupt the user only for consequential problems, manual reset redemption, security, cost, unrecoverable failures or approval-gated production actions.
- Provide a documented manual pause and stop.

## 10. Success
Success is reliable knowledge of which observable factors improve future price forecasts, or ruling out large sets of them. It is not the number of tests run.

Questions to answer:
1. Does fresh-wallet buying add anything beyond ordinary volume?
2. When does order flow become predictive?
3. Does liquidity change which signals matter?
4. Do related markets predict delayed moves?
5. Is reversal just bid-ask bounce?
6. Do model interactions find conditions that simple indicators miss?
7. Does any Bayesian, linear, boosted or ensemble model reliably beat the baseline?
8. Do the gains persist on new data?
9. Do any survive realistic costs?

## 11. Start sequence
1. Inspect the checkpoint, research state and workers.
2. Verify server, dataset and storage readiness.
3. Establish and demonstrate persistence and recovery.
4. Verify usage-window handling.
5. Identify the highest-value feasible experiments.
6. Launch real jobs.
7. Iterate on generating, implementing, testing and evaluating.
8. Update the dashboard.
9. Persist state before each usage boundary.
10. Resume autonomously.

Don't stop at a plan. No artificial limits. No edge claims without evidence.
