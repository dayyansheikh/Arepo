import { test, expect, type Page } from "@playwright/test";
import { VIEWPORTS } from "./helpers";
import { expectNoHorizontalOverflow } from "./helpers";

/**
 * Prospective Replay acceptance (refinement prompt sections 1-11, 15). Replay is now prospective-
 * only: real predictions genuinely frozen before later prices were known. These run the ACTUAL Next
 * app (:3000) against the real FastAPI backend (:8000) and the preserved local database, which holds
 * the genuine six-hour cohort (60 markets, 19 directional; 6h result 4 expected / 4 against / 11
 * flat; public 2/2/6; shadow 2/2/5).
 */

async function loadReplay(page: Page, query = "") {
  await page.goto(`/replay${query}`, { waitUntil: "networkidle" });
  await expect(page.getByTestId("replay-page")).toBeVisible();
  // Wait for the cohort selectors (the list resolved) and the results to render.
  await expect(page.getByTestId("cohort-cadence")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("headline-sentence")).toBeVisible({ timeout: 15000 });
}

test("default prospective Replay page shows the cohort selectors and real cohort", async ({
  page,
}) => {
  await loadReplay(page);
  // The removed public modes must not appear as tabs or labels.
  await expect(page.getByTestId("replay-tab-reconstructed")).toHaveCount(0);
  await expect(page.getByTestId("replay-tab-demo")).toHaveCount(0);
  await expect(page.getByTestId("replay-tab-research")).toHaveCount(0);
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("Reconstructed analysis");
  expect(body).not.toContain("Synthetic demonstration");
  expect(body).not.toContain("Prospective tracking has not started");

  // Selectors present.
  await expect(page.getByTestId("cohort-cadence")).toBeVisible();
  await expect(page.getByTestId("cohort-freeze")).toBeVisible();
  await expect(page.getByTestId("horizon-select")).toBeVisible();
  await expect(page.getByTestId("closing-filter")).toBeVisible();
  await expect(page.getByTestId("scope-select")).toBeVisible();

  // Dynamic cadence copy (six-hourly, not weekly).
  expect(body).toContain("six-hourly cohort");
  expect(body).not.toMatch(/real signals frozen at the weekly cut-off/i);

  // Freeze-timing banner in plain language.
  const banner = page.getByTestId("freeze-timing-banner");
  await expect(banner).toBeVisible();
  const bt = (await banner.innerText()).replace(/\s+/g, " ");
  expect(bt).toMatch(/Scheduled cut-off/i);
  expect(bt).toMatch(/Actually frozen/i);
  expect(bt).toMatch(/Evaluation starts from/i);
});

test("the real six-hour cohort headline reads 4 expected / 4 against / 11 flat", async ({
  page,
}) => {
  await loadReplay(page);
  // Horizon defaults to 6h.
  const headline = await page.getByTestId("headline-sentence").innerText();
  expect(headline).toContain("Of 19 directional calls");
  expect(headline).toContain("4 moved as expected");
  expect(headline).toContain("4 moved against the call");
  expect(headline).toContain("11 did not change");

  // Hit rate is shown only among markets that moved, explicitly labelled (4 of 8 = 50%).
  await expect(page.getByTestId("hit-rate-among-moved")).toContainText(
    "Hit rate among markets that moved: 50% (4 of 8)",
  );

  // Public 2/2/6 and shadow 2/2/5 splits.
  const section = page.getByTestId("did-move-section");
  const st = (await section.innerText()).replace(/\s+/g, " ");
  expect(st).toMatch(/Public selections\s*2 expected · 2 against · 6 no change/);
  expect(st).toMatch(/Shadow directional\s*2 expected · 2 against · 5 no change/);
});

test("switching between 1h and 6h changes the result", async ({ page }) => {
  await loadReplay(page);
  const six = await page.getByTestId("headline-sentence").innerText();
  expect(six).toContain("Of 19 directional calls");

  await page.getByTestId("horizon-select").selectOption("1h");
  await expect(page.getByTestId("headline-sentence")).not.toHaveText(six, { timeout: 15000 });
  const one = await page.getByTestId("headline-sentence").innerText();
  // 1h has fewer moves (more flat) than 6h in the real cohort.
  expect(one).toContain("Of 19 directional calls");
  expect(one).not.toEqual(six);

  await page.getByTestId("horizon-select").selectOption("6h");
  await expect(page.getByTestId("headline-sentence")).toContainText("11 did not change", {
    timeout: 15000,
  });
});

test("24h horizon shows pending, not fabricated results", async ({ page }) => {
  await loadReplay(page);
  await page.getByTestId("horizon-select").selectOption("24h");
  await expect(page.getByTestId("headline-sentence")).toContainText("19 pending", {
    timeout: 15000,
  });
});

test("changing the closing-window filter changes the qualifying set", async ({ page }) => {
  await loadReplay(page);
  // Default: all closing times -> 10 shown of 19 qualifying.
  await expect(page.getByTestId("qualifying-caption")).toContainText("of 19 qualifying");

  // Closing within 30 days at the freeze -> exactly 3 directional in the real cohort.
  await page.getByTestId("closing-filter").selectOption("30d");
  await expect(page.getByTestId("qualifying-caption")).toContainText(
    "Showing 3 qualifying directional signals",
    { timeout: 15000 },
  );
  await expect(page.getByTestId("market-row")).toHaveCount(3);

  // Closing within 7 days at the freeze -> none qualify (honest empty state, not padded).
  await page.getByTestId("closing-filter").selectOption("7d");
  await expect(page.getByTestId("market-table")).toHaveCount(0, { timeout: 15000 });
});

test("top ten ordering by frozen rank; never padded beyond qualifying", async ({ page }) => {
  await loadReplay(page);
  await expect(page.getByTestId("market-row")).toHaveCount(10);
  const ranks = await page
    .getByTestId("market-row")
    .evaluateAll((rows) =>
      rows.map((r) => Number((r.querySelector("td")?.textContent ?? "0").trim())),
    );
  const sorted = [...ranks].sort((a, b) => a - b);
  expect(ranks).toEqual(sorted);
  expect(ranks[0]).toBe(1);
});

test("per-market result labels are present and colour-independent", async ({ page }) => {
  await loadReplay(page);
  const table = await page.getByTestId("market-table").innerText();
  expect(table).toMatch(/Moved as expected|Moved against the call|No price change/);
  // The tooltip/explanation for "moved as expected" is present on the page.
  const body = await page.locator("body").innerText();
  expect(body).toContain("It does not mean the market finally resolved correctly");
  // Executable result is shown separately from midpoint movement.
  expect(table).toContain("pp");
});

test("scope control switches to public selections only", async ({ page }) => {
  await loadReplay(page);
  await page.getByTestId("scope-select").selectOption("public");
  await expect(page.getByTestId("headline-sentence")).toContainText("Of 10 directional calls", {
    timeout: 15000,
  });
});

test("final resolution is kept separate and shows pending for the unresolved cohort", async ({
  page,
}) => {
  await loadReplay(page);
  await page.getByTestId("horizon-select").selectOption("final");
  await expect(page.getByTestId("did-move-section")).toContainText(
    "What did the market finally resolve to?",
    { timeout: 15000 },
  );
  await expect(page.getByTestId("did-move-section")).toContainText("pending");
});

test("direct navigation with a legacy query param lands on prospective and refreshes", async ({
  page,
}) => {
  // Legacy ?replay=reconstructed must normalise to the prospective page (no removed mode shown).
  await loadReplay(page, "?replay=reconstructed");
  await expect(page.getByTestId("headline-sentence")).toContainText("Of 19 directional calls");
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("Reconstructed analysis");

  // A direct deep link (horizon + closing in the URL) survives a refresh.
  await page.goto("/replay?h=1h&closing=all", { waitUntil: "networkidle" });
  await expect(page.getByTestId("headline-sentence")).toBeVisible({ timeout: 15000 });
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByTestId("horizon-select")).toHaveValue("1h", { timeout: 15000 });
});

test("no horizontal overflow across viewports", async ({ page }) => {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await loadReplay(page);
    await expectNoHorizontalOverflow(page, `replay@${vp.name}`);
  }
});

test("disconnected API shows a clear state and recovers", async ({ page }) => {
  let down = true;
  await page.route("**/api/research/replay/cohorts**", async (route) => {
    if (down) await route.abort("connectionrefused");
    else await route.continue();
  });
  await page.goto("/replay", { waitUntil: "domcontentloaded" });
  // A clear error/empty state appears rather than a blank page or a crash.
  await expect(page.getByTestId("replay-page")).toBeVisible();
  await expect(page.locator("body")).toContainText(/could not be loaded|recover|error/i, {
    timeout: 15000,
  });

  // Recovers on reload once the API is back.
  down = false;
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByTestId("headline-sentence")).toBeVisible({ timeout: 15000 });
});
