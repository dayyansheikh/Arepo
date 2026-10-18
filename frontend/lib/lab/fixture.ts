// DEV-ONLY visual fixture for /lab?fixture=1. Never imported in a production build: the hook loads
// it through a dynamic import wrapped in a literal NODE_ENV check (see use-lab-dashboard.ts), and
// fixtureAllowed() refuses production. The screen labels it "FIXTURE". Values are illustrative
// stand-ins shaped like the real programme, not evidence.

import type { Experiment, LabDashboardResponse } from "./types";

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
      },
    },
    commands: [
      { id: 4, target: "queue", action: "resume", status: "done", created_at: iso(20 * HOUR), delivered_at: iso(19.9 * HOUR), finished_at: iso(19.9 * HOUR), result: "queue resumed" },
      { id: 3, target: "queue", action: "pause", status: "done", created_at: iso(22 * HOUR), delivered_at: iso(21.9 * HOUR), finished_at: iso(21.9 * HOUR), result: "queue paused" },
      { id: 2, target: "autopilot", action: "pause", status: "expired", created_at: iso(30 * HOUR), delivered_at: null, finished_at: null, result: null },
    ],
  };
}
