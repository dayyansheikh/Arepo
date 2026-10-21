// DEV-ONLY visual fixture for /lab?fixture=1. Never imported in a production build: the hook loads
// it through a dynamic import wrapped in a literal NODE_ENV check (see use-lab-dashboard.ts), and
// fixtureAllowed() refuses production. The screen labels it "FIXTURE". Values are illustrative
// stand-ins shaped like the real programme, not evidence.

import type { ClaudeActivity, ClaudeSession, CostsBlock, Experiment, LabDashboardResponse, LabMessage, SignalEngineBlock } from "./types";

/** Grepped for in the production build output to prove the fixture is not shipped. */
export const FIXTURE_SENTINEL = "arepo-lab-fixture-sentinel-7f3c";

const EXPERIMENTS: Experiment[] = [
  { id: "E009", title: "Kalshi lead", batch: "E", reached: ["idea", "designed", "screened", "replicated", "live_test"], stage_results: { idea: "pass", designed: "pass", screened: "pass", replicated: "pass", live_test: "pending" }, family: "cross_venue", stage: "live_test", status: "collecting", verdict: "pending", effect: null, next: "Analysis after 3 Nov", next_date: "2026-11-03", candidate: true,
    plain: "When the same question trades on Kalshi, does Kalshi move first? Collecting fresh paired prices; nothing is analysed until the registered date." },
  { id: "E010", title: "Surprise detector", reached: ["idea", "designed", "screened", "live_test"], stage_results: { idea: "pass", designed: "pass", screened: "pass", live_test: "pending" }, batch: "E", family: "anomaly", stage: "live_test", status: "collecting", verdict: "pending", effect: null, next: "Analysis after 11 Nov", next_date: "2026-11-11", candidate: true,
    plain: "Flags markets whose move is unusually large for their history and records what happens next. Counts only until 11 Nov." },
  { id: "E011", title: "Pre-close drift", batch: "E", family: "time", stage: "live_test", status: "collecting", verdict: "pending", effect: null, next: "Analysis after 24 Nov", next_date: "2026-11-24", candidate: false,
    plain: "Do prices keep drifting the same way in the last day before a market closes? Prospective collection only." },
  { id: "CB7-O", title: "Order flow", reached: ["idea", "designed", "screened", "replicated", "cost_check"], stage_results: { idea: "pass", designed: "pass", screened: "pass", replicated: "pass", cost_check: "fail" }, batch: "CB7", family: "flow", stage: "cost_check", status: "analysed", verdict: "failed_costs", effect: { label: "+0.36c", note: "before costs" }, next: "Closed: smaller than the spread", next_date: null, candidate: true,
    plain: "Net buying pressure does predict the next small move, but by about a third of a cent: less than it costs to trade." },
  { id: "C-TTE", title: "Near-close model gain", reached: ["idea", "designed", "screened", "replicated"], stage_results: { idea: "pass", designed: "pass", screened: "pass", replicated: "pass" }, batch: "CB9", family: "time", stage: "replicated", status: "analysed", verdict: "replicated", effect: { label: "+0.019 nats", note: "development (historical)" }, next: "Design a live test", next_date: "2026-10-28", candidate: true,
    plain: "The model is measurably better in the last 24 hours before close than a month out. Replicated on held-out history; not yet tested live." },
  { id: "CB8-H", title: "Flow × volatility", reached: ["idea", "designed", "screened", "replicated"], stage_results: { idea: "pass", designed: "pass", screened: "pass", replicated: "pass" }, batch: "CB8", family: "flow", stage: "replicated", status: "analysed", verdict: "replicated", effect: { label: "+0.011 nats", note: "development (historical)" }, next: "Collectors running", next_date: "2026-11-06", candidate: true,
    plain: "Order flow matters more when the market is already volatile. Held up on a second, unseen period." },
  { id: "CB11-W", title: "Whale prints", stage_results: { idea: "pass", designed: "pass", screened: "fail" }, batch: "CB11", family: "flow", stage: "screened", status: "analysed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Large single trades did not predict follow-through at a size the test could detect." },
  { id: "CB11-P", title: "Price clustering", batch: "CB11", family: "book", stage: "designed", status: "queued", verdict: null, effect: null, next: "Queued", candidate: false,
    plain: "Do prices stick to round numbers, and does breaking one mean anything?" },
  { id: "CB10-S", title: "Sports line moves", batch: "CB10", family: "cross_venue", stage: "screened", status: "closed", verdict: "not_testable", effect: null, next: null, candidate: false,
    plain: "Too few overlapping sports markets with clean timestamps to test fairly." },
  { id: "CB10-R", title: "Resolution-source lag", batch: "CB10", family: "time", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Markets did not lag their official resolution source by enough to matter." },
  { id: "CB9-V", title: "Volatility regime", batch: "CB9", family: "volatility", stage: "screened", status: "analysed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Calm-to-volatile switches did not predict direction." },
  { id: "CB9-D", title: "Depth imbalance", batch: "CB9", family: "book", stage: "screened", status: "analysed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "More resting bids than asks did not predict the next move beyond price itself." },
  { id: "CB8-M", title: "Momentum after news", batch: "CB8", family: "momentum", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Moves after big news did not continue more than ordinary moves." },
  { id: "CB8-T", title: "Thin-book spikes", batch: "CB8", family: "book", stage: "screened", status: "closed", verdict: "failed_costs", effect: { label: "+0.21c", note: "before costs" }, next: null, candidate: false,
    plain: "Spikes in thin books partly revert, but the reversion is smaller than the cost of trading it." },
  { id: "CB7-A", title: "Wallet age", batch: "CB7", family: "wallets", stage: "screened", status: "closed", verdict: "not_testable", effect: null, next: null, candidate: false,
    plain: "Public data does not identify enough first-time wallets reliably." },
  { id: "CB6-C", title: "Correlated markets", batch: "CB6", family: "cross_market", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Linked questions did not lead each other by a usable margin." },
  { id: "CB6-Q", title: "Quiet hours", batch: "CB6", family: "time", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Overnight moves were not more likely to reverse." },
  { id: "CB5-F", title: "Fee changes", batch: "CB5", family: "venue", stage: "designed", status: "waiting", verdict: null, effect: null, next: "Waiting for data", candidate: false,
    plain: "Did fee changes alter how quickly prices settle?" },
  { id: "CB4-K", title: "Kalshi spread", batch: "CB4", family: "cross_venue", stage: "screened", status: "closed", verdict: "advanced", effect: null, next: null, candidate: false,
    plain: "The cross-venue gap was large enough to justify the Kalshi lead live test (E009)." },
  { id: "CB3-L", title: "Liquidity drought", batch: "CB3", family: "book", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Markets losing liquidity did not drift in a predictable direction." },
  { id: "SB2-1", title: "Signal strength audit", batch: "SB2", family: "signals", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Arepo's own signal-strength score did not predict direction on its own." },
  { id: "SB1-3", title: "Tail prices", batch: "SB1", family: "momentum", stage: "screened", status: "closed", verdict: "not_detected", effect: null, next: null, candidate: false,
    plain: "Very cheap or very expensive outcomes were not systematically mispriced after costs." },
  { id: "CB12-N", title: "Novelty of question", batch: "CB12", family: "text", stage: "idea", status: "queued", verdict: null, effect: null, next: "Design in progress", candidate: false,
    plain: "Are brand-new kinds of question priced less efficiently than familiar ones?" },
  { id: "CB12-B", title: "Bot cadence", batch: "CB12", family: "flow", stage: "idea", status: "queued", verdict: null, effect: null, next: "Design in progress", candidate: false,
    plain: "Do regular, machine-like trade rhythms reveal anything about the next move?" },
];


/** Illustrative autopilot sessions: [hours ago it ended, runtime hours, outcome, done line, summary]. */
const SESSION_SPECS: Array<[number, number, string, string | null, string | null]> = [
  [3, 4.9, "ok", "CB17 censuses done; E012–E014 reviewed (revise); checkpoint rewritten",
    "This session got **CB17** through its counting jobs and recorded four overnight server checks.\n\n**Results**\n- Server checks: batches 13 and 15 passed; batch 14 was not testable (source returned nothing), counted 2.\n- CB17: two independent reviews caught real defects; both fixed before any job ran.\n\n**Queue:** the network lane has many hours of work lined up; the compute lane is idle until `q0305` at 14:05Z."],
  [9, 2.1, "usage_limit", null, "You've hit your session limit · resets 11:30pm (Europe/London)"],
  [12.1, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [12.6, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [13.1, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [13.6, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [14.1, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [14.6, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [15.1, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [15.6, 0.05, "error", null, "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)"],
  [21, 5, "timeout", null, null],
  [24, 2.8, "ok", null,
    "## Summary\nI finished the LT3 order-flow counting check and found no problems with the counts. The registry now lists LT3 as ready for its frozen analysis date.\n\n- q0472 counted 18,204 events."],
  [29, 3.6, "ok", "Round 9 creative hypotheses written (CH156–CH168); LT3 draft started",
    "Round 9 produced 13 new hypotheses, each with a plain-English mechanism and a falsification test.\n\n1. Three are cheap to screen on data we already hold.\n2. Two need the second server.\n\nNothing here is a result yet."],
  [36, 1.2, "interrupted", null, null],
  [44, 4.2, "ok", "LT2 challenger fixes applied; queue promoted q0480/q0471", "Applied the challenger's round-1 fixes and promoted two census jobs. No outcome statistics were computed."],
];

export function buildActivityFixture(nowMs: number): ClaudeActivity {
  const HOUR = 3_600_000;
  const at = (hAgo: number) => new Date(nowMs - hAgo * HOUR).toISOString().replace(/\.\d{3}Z$/, "Z");
  const mk = ([endH, runH, outcome, done, summary]: (typeof SESSION_SPECS)[number], i: number): ClaudeSession => ({
    started_at: at(endH + runH),
    ended_at: at(endH),
    runtime_s: Math.round(runH * 3600),
    outcome,
    ...(outcome === "ok" || outcome === "usage_limit" || outcome === "timeout" ? { cost_usd: 18 + ((i * 17) % 60), turns: 40 + i * 23 } : {}),
    ...(done ? { done } : {}),
    ...(summary ? { summary, summary_truncated: i === 0 } : {}),
    log_state: outcome === "interrupted" ? "missing" : outcome === "timeout" ? "empty" : "ok",
    ...(outcome === "interrupted" ? { note: "ended without a record (sleep, crash or kill); end time is when this was noticed" } : {}),
  });
  const signal: ClaudeSession[] = [
    [6, 1.5, "usage_limit", null, "You've hit your session limit · resets 2:20am (Europe/London)"],
    [19, 3.2, "ok", "Signal desk: order-flow feature audit complete; 3 features dropped as leaky", "Audited 41 order-flow features for look-ahead. Three used post-decision fields and were dropped; the remaining 38 are point-in-time safe."],
    [40, 2.4, "ok", "Signal desk: SHAP stability check across 5 seeds", null],
  ].map((x, i) => mk(x as (typeof SESSION_SPECS)[number], i + 3));
  const subjects = [
    "CB14-W GW0 blind audit (38/56, precision 0.679, FAIL); registry CB12-M/E closed",
    "ledger: CB12 M/E freeze + screens (3 tests p = 1), LT4 censuses promoted",
    "Merge feat/live-audit: live-test readiness (E009/E010 gapfill-v2 + merge step)",
    "review: LT3 donor-gate ruling 2 (donor gate non-binding)",
    "queue: promote LT4 censuses q0482 (CQ/CH) and q0483 (CF clock), counts only",
    "test: q0082 depends on q0082g, stale expectation",
    "creative round 9: CH156–CH168 written up with falsification tests",
    "checkpoint: rewrite live section after CB17 censuses",
    "registry: E012–E014 marked revise after challenger review",
    "docs: plain-English dashboard refreshed",
  ];
  const shas = ["14377914", "48d64d11", "0dcdaa0e", "6d78f940", "d397f98b", "ad73f51e", "8a840291", "4a3824ec", "9b1e22c4", "3c7f0a51"];
  return {
    generated_at: at(0.2),
    branch: "chore/arepo-claude-setup",
    instances: [
      {
        name: "experiments",
        key: "autopilot",
        startable: true,
        home: "~/.arepo/autopilot",
        paused: false,
        pause_reason: null,
        session_alive: true,
        current: {
          text: "The second CB18 review accepted the design with five changes, and an agent is now applying them and writing CB18's counts-only census code. Creative round 11 and LT3's order-flow counting check are still running.",
          at: at(0.15),
        },
        started_at: at(1.4),
        last_outcome: "ok",
        last_finished_at: at(3),
        next_allowed: null,
        sessions_total: 59,
        sessions: SESSION_SPECS.map(mk),
      },
      {
        name: "signal",
        key: "autopilot-signal",
        startable: true,
        home: "~/.arepo/autopilot-signal",
        paused: true,
        pause_reason: `${at(5)} paused until signal engine v1 is merged (orchestrator)`,
        session_alive: false,
        started_at: null,
        last_outcome: "usage_limit",
        last_finished_at: at(6),
        next_allowed: null,
        sessions_total: 3,
        sessions: signal,
      },
    ],
    commits: subjects.map((subject, i) => ({ at: at(0.3 + i * i * 0.45), sha: shas[i], subject })),
  };
}

export function buildCostsFixture(nowMs: number): CostsBlock {
  const DAY = 86_400_000;
  const spend = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2.1, 338.6, 307.9, 117.9, 43.7, 137.3, 144.7, 299.7, 146.7, 340.7, 297.1];
  const by_day = spend
    .map((usd, i) => ({ date: new Date(nowMs - (spend.length - 1 - i) * DAY).toISOString().slice(0, 10), usd }))
    .filter((d) => d.usd > 0);
  return {
    generated_at: new Date(nowMs - 14 * 60_000).toISOString(),
    basis: "API-equivalent: tokens x published API prices. You pay a flat subscription, not this.",
    pricing_source: "https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-10-21)",
    total_usd: 2240.73,
    last_7d_usd: 1410.65,
    today_usd: 297.12,
    messages: 23727,
    tokens: { input: 59020, output: 28125003, cache_write: 204050877, cache_read: 4006650789 },
    first_at: new Date(nowMs - 10.3 * DAY).toISOString(),
    by_day,
    by_model: [
      { model: "claude-opus-5-5", label: "Opus 5.5", usd: 1601.47, messages: 16065 },
      { model: "claude-sonnet-5-5", label: "Sonnet 5.5", usd: 365.43, messages: 7073 },
      { model: "claude-fable-5-1", label: "Fable 5.1", usd: 272.06, messages: 395 },
      { model: "claude-sonnet-5", label: "Sonnet 5", usd: 0.53, messages: 4 },
      { model: "claude-haiku-5-5", label: "Haiku 5.5", usd: 0.33, messages: 189 },
    ],
    by_source: [
      { key: "experiments", label: "experiments autopilot", kind: "autopilot", usd: 1176.01, main_usd: 191.39, subagent_usd: 984.62, sessions: 60 },
      { key: "interactive", label: "Interactive sessions (you + Claude)", kind: "interactive", usd: 1063.83, main_usd: 321.14, subagent_usd: 742.69, sessions: 16 },
    ],
    unknown_models: [],
    infra: [
      { name: "Oracle Cloud research host", gbp_month: 0, note: "Always Free tier" },
      { name: "Render API", gbp_month: 0, note: "Free web service" },
      { name: "Supabase database", gbp_month: 0, note: "Free tier (500 MB)" },
      { name: "Vercel website", gbp_month: 0, note: "Hobby (free)" },
      { name: "GitHub Actions + releases", gbp_month: 0, note: "Free for this repository" },
    ],
    infra_note: "All hosting runs on free tiers: £0 a month.",
  };
}

export function buildMessagesFixture(nowMs: number): LabMessage[] {
  const iso = (hAgo: number) => new Date(nowMs - hAgo * 3_600_000).toISOString();
  return [
    { id: 7, target: "autopilot", body: "When CB18 is frozen, prioritise the LT3 analysis over new creative rounds.", status: "delivered", created_at: iso(0.6), fetched_at: iso(0.5), delivered_at: iso(0.5) },
    { id: 6, target: "autopilot-signal", body: "Stay paused until v1 is merged; then start with the leakage audit.", status: "pending", created_at: iso(0.1) },
    { id: 5, target: "autopilot", body: "Please write the session summary in plain English, one sentence.", status: "read", created_at: iso(20), fetched_at: iso(19.9), delivered_at: iso(19.9), read_at: iso(18) },
  ];
}

/** Illustrative `se-dash-v1` block: one embargoed challenger (no numbers), placeholder scores. */
export function buildSignalEngineFixture(nowMs: number): SignalEngineBlock {
  const day = (d: number) => new Date(nowMs - d * 86_400_000).toISOString().slice(0, 10);
  const until = new Date(nowMs + 9 * 86_400_000).toISOString().slice(0, 19) + "Z";
  const gains = Array.from({ length: 10 }, (_, i) => i);
  return {
    schema: "se-dash-v1",
    generated_at: new Date(nowMs - 3 * 3_600_000).toISOString().slice(0, 19) + "Z",
    engine_version: "se-v1",
    primary_target: "dir_2h",
    champion: { model_id: "se1_lr_base", spec_sha256: "0".repeat(64), family: "baseline" },
    models: [
      { model_id: "se1_lr_base", family: "baseline", learner: "logreg", status: "active", embargoed_until: null },
      { model_id: "se3_lr_flow", family: "flow", learner: "logreg", status: "active", embargoed_until: null },
      { model_id: "se5_lgbm_all", family: "combination (lgbm)", learner: "lgbm", status: "active", embargoed_until: null },
      { model_id: "se8_lr_event", family: "event", learner: "logreg", status: "active", embargoed_until: until, embargo_tests: ["E012"] },
    ],
    note: "Signal strength / forecast quality only; not probability of profit, not an edge claim.",
    last_refit: { at: new Date(nowMs - 5 * 3_600_000).toISOString().slice(0, 19) + "Z", models: 4, targets_ok: 15 },
    last_prediction: { capture_id: "c20261021T1200Z", at: new Date(nowMs - 40 * 60_000).toISOString().slice(0, 19) + "Z", models: 4 },
    prospective: {
      generated_at: new Date(nowMs - 3 * 3_600_000).toISOString().slice(0, 19) + "Z",
      days_scored: 16,
      status: "scoring",
      rows: [
        { model_id: "se1_lr_base", role: "champion", target: "dir_2h", window_days: 14, n: 48210, log_loss: 0.6512, brier: 0.2297, cal_slope: 0.97, cal_intercept: -0.01, auc: 0.584, coverage: 0.93, days: 14 },
        { model_id: "se3_lr_flow", role: "challenger", target: "dir_2h", window_days: 14, n: 47980, log_loss: 0.6501, brier: 0.2293, cal_slope: 0.95, cal_intercept: 0.02, auc: 0.589, coverage: 0.92, days: 14, gain: 0.0011, gain_lo: -0.0004, gain_hi: 0.0026, days_positive: 9, n_days: 14, n_clusters: 3120 },
        { model_id: "se5_lgbm_all", role: "challenger", target: "dir_2h", window_days: 14, n: 47110, log_loss: 0.6530, brier: 0.2304, cal_slope: 0.88, cal_intercept: 0.04, auc: 0.581, coverage: 0.9, days: 14, gain: -0.0018, gain_lo: -0.0041, gain_hi: 0.0005, days_positive: 5, n_days: 14, n_clusters: 3080 },
        { model_id: "se8_lr_event", embargoed_until: until },
      ],
    },
    family_gains: gains.flatMap((i) => [
      { date: day(9 - i), model_id: "se3_lr_flow", family: "flow", gain: 0.0004 + i * 0.00008, lo: -0.0012 + i * 0.0001, hi: 0.002 + i * 0.00006 },
      { date: day(9 - i), model_id: "se5_lgbm_all", family: "combination (lgbm)", gain: -0.001 - (i % 3) * 0.0003, lo: -0.0035, hi: 0.0012 },
    ]),
    development: {
      label: "development/historical",
      generated_at: new Date(nowMs - 2 * 86_400_000).toISOString().slice(0, 19) + "Z",
      test_days: 6,
      rows: [
        { model_id: "se1_lr_base", role: "champion", target: "dir_2h", n: 120400, log_loss: 0.6488, brier: 0.2286, cal_slope: 1.01, cal_intercept: 0.0, auc: 0.591, coverage: 0.94 },
        { model_id: "se3_lr_flow", role: "challenger", target: "dir_2h", n: 119800, log_loss: 0.6479, brier: 0.2283, cal_slope: 0.98, cal_intercept: 0.01, auc: 0.594, coverage: 0.93, gain: 0.0009, gain_lo: 0.0001, gain_hi: 0.0017, days_positive: 5, n_days: 6, n_clusters: 2900 },
        { model_id: "se8_lr_event", embargoed_until: until },
      ],
    },
    attribution: [
      {
        model_id: "se5_lgbm_all",
        fit_time: new Date(nowMs - 5 * 3_600_000).toISOString().slice(0, 19) + "Z",
        target: "dir_2h",
        method: "mean_abs_shap",
        rows: 20000,
        families: { market_state: 0.42, momentum: 0.31, flow: 0.12, tte: 0.08, category: 0.03 },
        hidden: ["event"],
        label: "development diagnostic (mean |SHAP| on the fit's validation block), not a score",
      },
    ],
    embargo_tokens: [{ token: "event", until }],
    promotions: [],
    stale: false,
  };
}

export function buildLabFixture(nowMs: number): LabDashboardResponse {
  const iso = (msAgo: number) => new Date(nowMs - msAgo).toISOString();
  const MIN = 60_000;
  const HOUR = 60 * MIN;

  const testsOverTime = Array.from({ length: 21 }, (_, i) => {
    const d = new Date(nowMs - (20 - i) * 24 * HOUR);
    const cumulative = Math.round(520 + 586 * Math.pow(i / 20, 1.3) + (i % 3) * 4);
    return { date: d.toISOString().slice(0, 10), cumulative: i === 20 ? 1106 : cumulative };
  });

  const outcomes = ["done", "done", "done", "tempfail", "done", "done", "error", "done", "done", "done", "done", "tempfail", "done", "done", "done", "done", "done", "done", "done", "error", "done", "done", "done", "done"];
  const recent = outcomes.map((outcome, i) => ({
    ...(i === 4 ? { repeats: 3 } : i === 15 ? { repeats: 5 } : {}),
    at: iso((i + 1) * 47 * MIN),
    id: `q01${70 - i}`,
    title: ["CB11 W census", "CB8-H collector", "C-TTE refit", "Kalshi pairs", "E010 surprise sweep", "CB11 screen"][i % 6],
    outcome,
    runtime_s: 300 + ((i * 397) % 4200),
  }));

  const history = Array.from({ length: 48 }, (_, i) => ({
    t: iso((47 - i) * 30 * MIN),
    disk_free_gb: Math.round((61.5 - i * 0.05 + Math.sin(i / 5) * 0.4) * 10) / 10,
    mem_available_mb: Math.round(4300 + Math.sin(i / 3) * 420 + ((i * 37) % 200)),
  }));

  return {
    server_time: new Date(nowMs).toISOString(),
    host: {
      received_at: iso(4 * MIN),
      payload: {
        schema: "arepo-lab-v1",
        source: "host",
        generated_at: iso(5 * MIN),
        headline: { confirmed_edges: 0, tests_run: 1106, hypotheses: 117, batches: 12, live_tests: 3, jobs_done: 73 },
        funnel: [
          { stage: "idea", label: "Ideas", count: 117, unit: "hypotheses", help: "Every hypothesis written down so far." },
          { stage: "designed", label: "Designed", count: 64, unit: "hypotheses", help: "Pre-registered with a minimum effect it must beat." },
          { stage: "screened", label: "Screened", count: 26, unit: "registry entries", help: "Run once on historical data." },
          { stage: "replicated", label: "Replicated", count: 6, unit: "registry entries", help: "Held up again on unseen data." },
          { stage: "live_test", label: "Live test", count: 6, unit: "registry entries", help: "Collecting fresh predictions forward in time." },
          { stage: "cost_check", label: "Cost check", count: 6, unit: "registry entries", help: "Is it still there after trading costs?" },
          { stage: "confirmed", label: "Confirmed", count: 0, unit: "registry entries", help: "Passed every gate prospectively, after costs." },
        ],
        experiments: EXPERIMENTS,
        live_tests: [
          { id: "E009", title: "Kalshi lead", collected: 1234, target: null, unit: "paired predictions", started_at: "2026-10-06", analysis_after: "2026-11-03" },
          { id: "E010", title: "Surprise detector", collected: 412, target: null, unit: "flagged moves", started_at: "2026-10-11", analysis_after: "2026-11-11" },
          { id: "E011", title: "Pre-close drift", collected: 287, target: 600, unit: "closing markets", analysis_after: "2026-11-24" },
        ],
        ml: {
          status: "parked",
          status_note: "Parked until more markets resolve; the next fit needs about 400 more.",
          learned: [
            "Price and recent momentum explain almost everything the model can see.",
            "What is left is concentrated in the last day before a market closes.",
            "Order flow helps most when the market is already volatile.",
            "Text features and wallet features add nothing measurable so far.",
          ],
          feature_weights: [
            { feature: "Order flow", family: "flow", weight: 0.0121 },
            { feature: "Time to close", family: "time", weight: 0.0094 },
            { feature: "Volatility", family: "volatility", weight: 0.0058 },
            { feature: "Cross-venue gap", family: "cross_venue", weight: 0.0044 },
            { feature: "Order book", family: "book", weight: 0.0019 },
            { feature: "Question text", family: "text", weight: -0.0006 },
            { feature: "Wallets", family: "wallets", weight: -0.0013 },
            { feature: "Sports context", family: "sports", weight: 0.0031, comparable: false },
          ],
          feature_weights_note:
            "Family-level drop-one changes on the development fit. Negative means the model did slightly better without that family. Sports context comes from a separate run.",
          contrasts: [
            { label: "Last 24h vs >30 days before close", value: 0.0188, lo: 0.0094, hi: 0.0292, unit: "nats", replicated: true },
            { label: "Volatile vs calm markets", value: 0.0112, lo: 0.0031, hi: 0.0198, unit: "nats", replicated: true },
            { label: "Sports vs politics", value: -0.0024, lo: -0.0121, hi: 0.0069, unit: "nats", replicated: false },
          ],
        },
        tests_over_time: testsOverTime,
        queue: {
          updated_at: iso(6 * MIN),
          paused: false,
          counts: { done: 73, queued: 5, running: 2, retry_wait: 1, parked: 2, error: 3 },
          running: [
            { id: "q0171", title: "CB8-H collector", started_at: iso(38 * MIN), lane: "cpu" },
            { id: "q0172", title: "CB11 W census", started_at: iso(12 * MIN), lane: "io" },
          ],
          recent,
          upcoming: [
            { id: "q0173", title: "CB11 P screen", status: "queued", not_before: null },
            { id: "q0174", title: "C-TTE live design check", status: "queued", not_before: null },
            { id: "q0168", title: "Kalshi pairs backfill", status: "retry_wait", not_before: new Date(nowMs + 25 * MIN).toISOString() },
            { id: "q0160", title: "Wallet age re-test", status: "parked", not_before: null },
          ],
        },
        infra: {
          disk_free_gb: 59,
          disk_total_gb: 89,
          mem_available_mb: 4345,
          mem_total_mb: 5648,
          collector_last_ok: iso(3 * MIN),
          collector_ok: true,
          data_gb: 15.1,
          data_cap_gb: 45,
          second_server: { status: "retrying", attempts: 275, last_try: iso(9 * MIN) },
          history,
        },
        activity: {
          queue: {
            window_h: 48,
            since: iso(48 * HOUR),
            attempts: 61,
            outcomes: { done: 38, tempfail: 19, error: 3, interrupted: 1 },
            distinct_jobs: 27,
            runtime_h: 71.4,
            first_at: iso(47 * HOUR),
            last_at: iso(4 * MIN),
          },
        },
        signal_engine: buildSignalEngineFixture(nowMs),
      },
    },
    mac: {
      received_at: iso(14 * MIN),
      payload: {
        schema: "arepo-lab-v1",
        source: "mac",
        generated_at: iso(14 * MIN),
        autopilot: {
          paused: false,
          pause_reason: null,
          session_alive: true,
          started_at: iso(2 * HOUR + 10 * MIN),
          last_outcome: "timeout",
          next_allowed: null,
          recent: [
            { at: iso(3 * HOUR), outcome: "timeout", runtime_s: 18000 },
            { at: iso(9 * HOUR), outcome: "done", runtime_s: 14200 },
            { at: iso(16 * HOUR), outcome: "usage_limit", runtime_s: 9100 },
            { at: iso(26 * HOUR), outcome: "done", runtime_s: 17600 },
          ],
        },
        activity: buildActivityFixture(nowMs),
        costs: buildCostsFixture(nowMs),
      },
    },
    messages: buildMessagesFixture(nowMs),
    limits: { message_max_chars: 4000, messages_per_day: 20, messages_last_24h: 2 },
    commands: [
      { id: 5, target: "autopilot-signal", action: "pause", status: "done", created_at: iso(5 * HOUR), delivered_at: iso(4.9 * HOUR), finished_at: iso(4.9 * HOUR), result: "signal paused" },
      { id: 4, target: "queue", action: "resume", status: "done", created_at: iso(20 * HOUR), delivered_at: iso(19.9 * HOUR), finished_at: iso(19.9 * HOUR), result: "queue resumed" },
      { id: 3, target: "queue", action: "pause", status: "done", created_at: iso(22 * HOUR), delivered_at: iso(21.9 * HOUR), finished_at: iso(21.9 * HOUR), result: "queue paused" },
      { id: 2, target: "autopilot", action: "pause", status: "expired", created_at: iso(30 * HOUR), delivered_at: null, finished_at: null, result: null },
    ],
  };
}
