import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SignalEngine } from "@/components/lab/SignalEngine";
import { buildLabFixture, buildSignalEngineFixture } from "./fixture";
import {
  activeUntil,
  attributionViews,
  developmentRows,
  embargoLabel,
  engineStatus,
  familySeries,
  fmtGain,
  fmtSigned,
  isEmbargoed,
  parseSignalEngine,
  promotionView,
  promotions,
  prospectiveRows,
  rowCells,
} from "./signal-engine";
import type { SignalEngineBlock } from "./types";

const NOW = Date.parse("2026-10-21T12:00:00Z");
const UNTIL = "2026-10-30T00:00:00Z";

function render(block: unknown): string {
  return renderToStaticMarkup(createElement(SignalEngine, { block, nowMs: NOW }));
}

describe("parseSignalEngine", () => {
  it("returns null for absent, malformed or other-schema blocks", () => {
    expect(parseSignalEngine(undefined)).toBeNull();
    expect(parseSignalEngine(null)).toBeNull();
    expect(parseSignalEngine("se-dash-v1")).toBeNull();
    expect(parseSignalEngine([])).toBeNull();
    expect(parseSignalEngine({ schema: "se-dash-v2" })).toBeNull();
    expect(parseSignalEngine({ schema: "se-dash-v1" })).not.toBeNull();
  });
});

describe("embargoed rows never show numbers", () => {
  it("rowCells keeps only id and date, even if the row smuggles numbers", () => {
    const cells = rowCells({ model_id: "se8", embargoed_until: UNTIL, log_loss: 0.61, gain: 0.02, n: 999 }, NOW);
    expect(cells).toEqual({ kind: "embargoed", modelId: "se8", until: UNTIL });
    expect(isEmbargoed({ model_id: "x", embargoed_until: null }, NOW)).toBe(false);
  });

  it("a future or unparseable date is active; a past date is not", () => {
    expect(activeUntil(UNTIL, NOW)).toBe(UNTIL);
    expect(activeUntil("not a date", NOW)).toBe("not a date");
    expect(activeUntil("2026-10-01T00:00:00Z", NOW)).toBeNull();
    expect(activeUntil(null, NOW)).toBeNull();
    const past = rowCells({ model_id: "se8", embargoed_until: "2026-10-01T00:00:00Z", log_loss: 0.61 }, NOW);
    expect(past.kind === "scored" && past.logLoss).toBe(0.61);
  });

  it("the model list embargoes a row that carries numbers but no date of its own", () => {
    const models = new Map([["se8", UNTIL]]);
    expect(rowCells({ model_id: "se8", target: "dir_2h", log_loss: 0.61, gain: 0.02 }, NOW, models)).toEqual({
      kind: "embargoed",
      modelId: "se8",
      until: UNTIL,
    });
    const se: SignalEngineBlock = {
      schema: "se-dash-v1",
      models: [{ model_id: "leaky", embargoed_until: UNTIL }],
      prospective: { status: "scoring", rows: [
        { model_id: "champ", role: "champion", target: "dir_2h", window_days: 14, n: 5, log_loss: 0.65 },
        { model_id: "leaky", target: "dir_2h", window_days: 14, n: 5, log_loss: 0.4321, gain: 0.0888 },
      ] },
      development: { rows: [{ model_id: "leaky", target: "dir_2h", log_loss: 0.4322, gain: 0.0889 }] },
    };
    expect(developmentRows(se, NOW)[0].kind).toBe("embargoed");
    const html = render(se);
    for (const leak of ["0.4321", "0.0888", "0.4322", "0.0889"]) expect(html).not.toContain(leak);
    expect(html).toContain("embargoed until 30 Oct 2026 (live test)");
  });

  it("the embargo label carries only a date", () => {
    expect(embargoLabel(UNTIL)).toBe("embargoed until 30 Oct 2026 (live test)");
  });

  it("the rendered row contains the label and no digits beyond the date", () => {
    const se: SignalEngineBlock = {
      schema: "se-dash-v1",
      prospective: {
        status: "scoring",
        days_scored: 15,
        rows: [
          { model_id: "champ", role: "champion", target: "dir_2h", window_days: 14, n: 10, log_loss: 0.65 },
          { model_id: "secret", embargoed_until: UNTIL, log_loss: 0.12345, gain: 0.0777 } as never,
        ],
      },
      family_gains: [
        { date: "2026-10-19", model_id: "secret", family: "event", gain: 0.0555 },
        { date: "2026-10-20", model_id: "secret", family: "event", gain: 0.0555 },
      ],
      models: [{ model_id: "secret", family: "event", embargoed_until: UNTIL }],
    };
    const html = render(se);
    expect(html).toContain("embargoed until 30 Oct 2026 (live test)");
    expect(html).not.toContain("0.1235");
    expect(html).not.toContain("0.0777");
    expect(html).not.toContain("0.0555");
    const row = html.match(/<tr[^>]*data-testid="se-embargoed-row"[^>]*>(.*?)<\/tr>/)?.[1] ?? "";
    expect(row).toContain("secret");
    expect(row.replace(/<[^>]+>/g, "").replace("30 Oct 2026", "")).not.toMatch(/\d/);
  });

  it("family gains drop models that the model list says are embargoed", () => {
    const se = buildSignalEngineFixture(NOW);
    se.family_gains = [...(se.family_gains ?? []), { date: "2026-10-20", model_id: "se8_lr_event", family: "event", gain: 0.9 }];
    expect(familySeries(se, NOW).map((s) => s.key)).not.toContain("se8_lr_event");
  });
});

describe("bootstrapping state", () => {
  it("is bootstrapping when the engine says so; early rows show with a too-few-days notice", () => {
    const se = buildSignalEngineFixture(NOW);
    se.prospective = { ...se.prospective, status: "bootstrapping", days_scored: 3 };
    expect(engineStatus(se, NOW)).toBe("bootstrapping");
    const html = render(se);
    expect(html).toContain("at least 14 days of prospective scores");
    expect(html).toContain("Days scored so far: 3.");
    expect(html).toContain("too few days to judge");
    expect(html).toContain("0.6512");
  });

  it("explains the empty state in plain English for the real host payload", () => {
    const se: SignalEngineBlock = {
      schema: "se-dash-v1",
      champion: { model_id: "se0_champion_lr_mm", family: "baseline" },
      models: [
        { model_id: "se0_champion_lr_mm", family: "baseline", embargoed_until: null },
        { model_id: "se2_lr_flow", family: "flow", embargoed_until: "2026-11-16T00:00:00Z" },
      ],
      prospective: { status: "bootstrapping", days_scored: 0, rows: [{ model_id: "se2_lr_flow", embargoed_until: "2026-11-16T00:00:00Z" }] },
      family_gains: [],
      attribution: [],
      promotions: [],
      note: "Signal strength / forecast quality only; not probability of profit, not an edge claim.",
    };
    const html = render(se);
    expect(html).toContain("writing a prediction for each new market capture");
    expect(html).toContain("Days scored so far: 0.");
    expect(html).toContain("embargoed until 16 Nov 2026 (live test)");
    expect(html).toContain("Signal strength / forecast quality only");
    expect(html).not.toContain("too few days to judge");
    expect(html).not.toContain("Family attribution");
  });

  it("is bootstrapping when rows are empty or only embargoed", () => {
    expect(engineStatus({ schema: "se-dash-v1", prospective: { status: "scoring", rows: [] } }, NOW)).toBe("bootstrapping");
    expect(
      engineStatus(
        { schema: "se-dash-v1", prospective: { status: "scoring", rows: [{ model_id: "a", embargoed_until: UNTIL }] } },
        NOW,
      ),
    ).toBe("bootstrapping");
    expect(engineStatus({ schema: "se-dash-v1" }, NOW)).toBe("bootstrapping");
  });

  it("renders the calm absent state, and a minimal block without crashing", () => {
    expect(render(undefined)).toContain("no signal-engine block");
    expect(render({ schema: "se-dash-v1", prospective: "junk", models: "junk", promotions: [null, 3] })).toContain(
      "Bootstrapping",
    );
  });
});

describe("scoring view", () => {
  it("sorts champion first, then by gain, embargoed last", () => {
    const rows = prospectiveRows(buildSignalEngineFixture(NOW), NOW);
    expect(rows.map((r) => r.modelId)).toEqual(["se1_lr_base", "se3_lr_flow", "se5_lgbm_all", "se8_lr_event"]);
    expect(rows[3].kind).toBe("embargoed");
  });

  it("keeps only the 14-day window in the prospective table", () => {
    const se: SignalEngineBlock = {
      schema: "se-dash-v1",
      prospective: { status: "scoring", rows: [
        { model_id: "a", target: "dir_2h", window_days: 7, n: 1 },
        { model_id: "a", target: "dir_2h", window_days: 14, n: 2 },
      ] },
    };
    const rows = prospectiveRows(se, NOW);
    expect(rows).toHaveLength(1);
    expect(rows[0].kind === "scored" && rows[0].n).toBe(2);
  });

  it("labels the development table as historical, not prospective", () => {
    const html = render(buildSignalEngineFixture(NOW));
    expect(html).toContain("Development (historical, not prospective)");
    expect(developmentRows(buildSignalEngineFixture(NOW), NOW).at(-1)?.kind).toBe("embargoed");
  });

  it("formats gains with a true minus and the interval", () => {
    expect(fmtGain(0.0011, -0.0004, 0.0026)).toBe("+0.0011 [−0.0004, +0.0026]");
    expect(fmtGain(null, 1, 2)).toBe("–");
    expect(fmtSigned(0)).toBe("0.0000");
  });

  it("lists promotions newest first and ignores malformed entries", () => {
    const se: SignalEngineBlock = {
      schema: "se-dash-v1",
      promotions: [
        { at: "2026-10-01T00:00:00Z", champion: "a" },
        { at: "2026-10-10T00:00:00Z", champion: "b", previous: "a" },
        { at: "2026-10-11T00:00:00Z" },
        { event: "init", at: "2026-10-12T00:00:00Z", champion: "c" },
      ],
    };
    expect(promotions(se).map((p) => p.champion)).toEqual(["b", "a"]);
  });

  it("the lab fixture carries a signal_engine block", () => {
    const host = buildLabFixture(NOW).host?.payload;
    expect(typeof host === "object" && host?.signal_engine?.schema).toBe("se-dash-v1");
  });
});

describe("family attribution", () => {
  const base = (over: Partial<SignalEngineBlock> = {}): SignalEngineBlock => ({
    schema: "se-dash-v1",
    attribution: [{ model_id: "lg", target: "dir_2h", rows: 100, families: { market_state: 3, momentum: 1, flow: 0.777 }, hidden: ["book"] }],
    embargo_tokens: [{ token: "flow", until: UNTIL }],
    ...over,
  });

  it("drops families under an active embargo token to names only; shares use the visible total", () => {
    const [v] = attributionViews(base(), NOW);
    expect(v.families.map((f) => [f.family, f.share])).toEqual([["market_state", 0.75], ["momentum", 0.25]]);
    expect(v.hidden).toEqual(["book", "flow"]);
    const html = render(base());
    expect(html).toContain("Hidden while under a live test: book, flow");
    expect(html).not.toContain("0.777");
    expect(html).toContain("Development diagnostic, not a score");
  });

  it("an expired token no longer hides its family; an unparseable one still does", () => {
    expect(attributionViews(base({ embargo_tokens: [{ token: "flow", until: "2026-10-01T00:00:00Z" }] }), NOW)[0].hidden).toEqual(["book"]);
    expect(attributionViews(base({ embargo_tokens: [{ token: "flow", until: "soon" }] }), NOW)[0].hidden).toContain("flow");
  });

  it("drops the whole entry when its model is embargoed", () => {
    expect(attributionViews(base({ models: [{ model_id: "lg", embargoed_until: UNTIL }] }), NOW)).toEqual([]);
  });
});

describe("promotion rule status", () => {
  const cand = (model_id: string, over: Record<string, unknown> = {}) => ({
    model_id, pass: false, days: 15, days_to_min: 0,
    checks: { c1_days: true, c2_ci: true, c3_days_positive: true, c4_calibration: false, c5_secondary: true, c6_coverage: true, c7_cooldown: true },
    gain: 0.02, lo_event: 0.01, lo_twoway: 0.004, se_event: 0.003, se_day: 0.006, n_days: 15, ...over,
  });
  const block = (over: Record<string, unknown> = {}, models: SignalEngineBlock["models"] = []): SignalEngineBlock => ({
    schema: "se-dash-v1",
    models,
    promotion: { rule: "se-promotion-v2", at: "2026-10-21T11:40:00Z", K: 3, level: 0.9833, min_days: 14, promote: null, reason: null, candidates: [cand("se1_lgbm_mm")], ...over },
  });

  it("computes day share, checks passed and failed-check labels", () => {
    const v = promotionView(block(), NOW)!;
    expect(v.candidates).toHaveLength(1);
    expect(v.candidates[0].dayShare).toBeCloseTo(36 / 45, 10);
    expect(v.candidates[0].passed).toBe(6);
    expect(v.candidates[0].failed).toEqual(["calibration"]);
    const html = render(block());
    expect(html).toContain("Promotion rule");
    expect(html).toContain("98.3% one-sided");
    expect(html).toContain("6/7");
    expect(html).toContain("Not met: calibration");
    expect(html).toContain("80%");
    expect(html).toContain("Not yet");
    expect(html).toContain("now");
  });

  it("drops an embargoed candidate (model-list date or own date) and withholds an embargoed promote", () => {
    const b = block({ promote: "se8", candidates: [cand("se1_lgbm_mm"), cand("se8"), cand("se9", { embargoed_until: UNTIL })] }, [{ model_id: "se8", embargoed_until: UNTIL }]);
    expect(promotionView(b, NOW)!.candidates.map((c) => c.modelId)).toEqual(["se1_lgbm_mm"]);
    expect(promotionView(b, NOW)!.promote).toBeNull();
    const html = render(b);
    expect(html).not.toContain("se8");
    expect(html).not.toContain("se9");
    expect(html).toContain("se1_lgbm_mm");
    // an expired embargo no longer hides the candidate
    expect(promotionView(block({ candidates: [cand("x")] }, [{ model_id: "x", embargoed_until: "2026-10-01T00:00:00Z" }]), NOW)!.candidates).toHaveLength(1);
  });

  it("handles null numbers, eligibility text and a promote pill", () => {
    const b = block({ promote: "se1_lgbm_mm", reason: "waiting", candidates: [cand("a", { lo_twoway: null, se_day: null, gain: null, days_to_min: 3.25 })] });
    const v = promotionView(b, NOW)!;
    expect(v.candidates[0].dayShare).toBeNull();
    const html = render(b);
    expect(html).toContain("3.3 days");
    expect(html).toContain("Promotes se1_lgbm_mm");
    expect(html).toContain("waiting");
  });

  it("renders nothing for an absent, null or malformed promotion", () => {
    for (const p of [undefined, null, "x", [], 5]) {
      expect(promotionView({ schema: "se-dash-v1", promotion: p as never }, NOW)).toBeNull();
      expect(render({ schema: "se-dash-v1", promotion: p })).not.toContain("Promotion rule");
    }
    expect(promotionView(block({ candidates: "nope" }), NOW)!.candidates).toEqual([]);
  });
});
