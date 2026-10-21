import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SignalEngine } from "@/components/lab/SignalEngine";
import { buildLabFixture, buildSignalEngineFixture } from "./fixture";
import {
  developmentRows,
  embargoLabel,
  engineStatus,
  familySeries,
  fmtGain,
  fmtSigned,
  isEmbargoed,
  parseSignalEngine,
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
    const cells = rowCells({ model_id: "se8", embargoed_until: UNTIL, log_loss: 0.61, gain: 0.02, n: 999 });
    expect(cells).toEqual({ kind: "embargoed", modelId: "se8", until: UNTIL });
    expect(isEmbargoed({ model_id: "x", embargoed_until: null })).toBe(false);
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
  it("is bootstrapping when the engine says so, even with rows", () => {
    const se = buildSignalEngineFixture(NOW);
    se.prospective = { ...se.prospective, status: "bootstrapping", days_scored: 3 };
    expect(engineStatus(se)).toBe("bootstrapping");
    const html = render(se);
    expect(html).toContain("Bootstrapping: no prospective scores yet (3 of 14 days scored).");
    expect(html).not.toContain("0.6512");
  });

  it("is bootstrapping when rows are empty or only embargoed", () => {
    expect(engineStatus({ schema: "se-dash-v1", prospective: { status: "scoring", rows: [] } })).toBe("bootstrapping");
    expect(
      engineStatus({ schema: "se-dash-v1", prospective: { status: "scoring", rows: [{ model_id: "a", embargoed_until: UNTIL }] } }),
    ).toBe("bootstrapping");
    expect(engineStatus({ schema: "se-dash-v1" })).toBe("bootstrapping");
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
    const rows = prospectiveRows(buildSignalEngineFixture(NOW));
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
    const rows = prospectiveRows(se);
    expect(rows).toHaveLength(1);
    expect(rows[0].kind === "scored" && rows[0].n).toBe(2);
  });

  it("labels the development table as historical, not prospective", () => {
    const html = render(buildSignalEngineFixture(NOW));
    expect(html).toContain("Development (historical, not prospective)");
    expect(developmentRows(buildSignalEngineFixture(NOW)).at(-1)?.kind).toBe("embargoed");
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
      ],
    };
    expect(promotions(se).map((p) => p.champion)).toEqual(["b", "a"]);
  });

  it("the lab fixture carries a signal_engine block", () => {
    const host = buildLabFixture(NOW).host?.payload;
    expect(typeof host === "object" && host?.signal_engine?.schema).toBe("se-dash-v1");
  });
});
