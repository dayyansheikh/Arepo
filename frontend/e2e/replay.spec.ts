import { test, expect, type Page } from "@playwright/test";
import { VIEWPORTS, expectNoHorizontalOverflow } from "./helpers";

/**
 * Redesigned, results-first Replay acceptance (FINAL REPLAY UX OVERRIDE). Real Next app (:3000) +
 * real backend (:8000) + preserved database. The default cohort is the newest one that has
 * evaluable 6h results (the complete-scan cohort, universe 1,382). A new user must understand
 * "how did Arepo's past signals perform?" at a glance: the result comes before the controls, the
 * horizon is one click, cohort mechanics are collapsed, and a due horizon is never a wall of zero
 * cards.
 */
async function loadReplay(page: Page, query = "") {
  await page.goto(`/replay${query}`, { waitUntil: "networkidle" });
  await expect(page.getByTestId("replay-page")).toBeVisible();
  await expect(page.getByTestId("horizon-tabs")).toBeVisible({ timeout: 15000 });
}

test("results come first: 6h performance and a plain hit sentence are the main focus", async ({
  page,
}) => {
  await loadReplay(page, "?h=6h");
  await expect(page.getByTestId("result-block")).toContainText("6-hour performance", {
    timeout: 15000,
  });
  // Real evaluated numbers (not a wall of zeros), and the plain hit-rate sentence.
  await expect(page.getByTestId("repricing-result")).toBeVisible();
  await expect(page.getByTestId("hit-sentence")).toContainText(
    /% of markets that moved went in Arepo's recorded direction\./,
  );
});

test("cohort mechanics are collapsed, not dominating the page", async ({ page }) => {
  await loadReplay(page);
  // One subtle cohort line, not a big coloured timing box.
  await expect(page.getByTestId("cohort-line")).toContainText(/Frozen .* · [\d,]+ markets/);
  // Scheduled cut-off / lateness / evaluation origin live inside the collapsed disclosure.
  const details = page.locator("details", { hasText: "Cohort details" });
  await expect(details).toHaveCount(1);
  await expect(details).not.toHaveJSProperty("open", true);
  const body = await page.locator("body").innerText();
  // These labels must NOT be visible before the disclosure is opened.
  expect(body).not.toContain("Scheduled cut-off");
  expect(body).not.toContain("Evaluation starts from");
});

test("horizon is one click and a due-but-uncollected horizon shows a clean pending state", async ({
  page,
}) => {
  await loadReplay(page, "?h=6h");
  await expect(page.getByTestId("repricing-result")).toBeVisible({ timeout: 15000 });
  // 24h is not yet due for this cohort -> a single clear pending state, never six zero cards.
  await page.getByTestId("horizon-24h").click();
  const pending = page.getByTestId("pending-state");
  await expect(pending).toBeVisible({ timeout: 15000 });
  await expect(pending).toContainText("still being collected");
  await expect(pending).toContainText(/signals pending/);
  await expect(pending).toContainText(/Expected from/);
});

test("horizon tabs label pending horizons concisely", async ({ page }) => {
  await loadReplay(page);
  await expect(page.getByTestId("horizon-24h")).toContainText("pending");
  // 6h is evaluable for the default cohort, so it carries no pending label.
  await expect(page.getByTestId("horizon-6h")).not.toContainText("pending");
});

test("scope is Opportunities by default; Research comparison reveals the public/shadow panels", async ({
  page,
}) => {
  await loadReplay(page, "?h=6h");
  await expect(page.getByTestId("repricing-result")).toBeVisible({ timeout: 15000 });
  // The public/shadow/combined comparison is NOT shown on the normal view.
  await expect(page.getByTestId("research-comparison")).toHaveCount(0);
  await page.getByTestId("scope-pills-research").click();
  await expect(page.getByTestId("research-comparison")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("research-comparison")).toContainText("Opportunities (public)");
  await expect(page.getByTestId("research-comparison")).toContainText("Shadow directional");
});

test("closing window is one click", async ({ page }) => {
  await loadReplay(page, "?h=6h");
  await expect(page.getByTestId("result-block")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("closing-pills-6h").click();
  // The result re-renders for the new window (still the 6-hour performance heading).
  await expect(page.getByTestId("result-block")).toContainText("6-hour performance");
});

test("To close and Resolved tabs show their own separate panels", async ({ page }) => {
  await loadReplay(page, "?h=6h");
  await page.getByTestId("horizon-close").click();
  await expect(page.getByTestId("freeze-to-close-result")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("horizon-resolved").click();
  await expect(page.getByTestId("resolution-result")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("resolution-result")).toContainText(/resolve|await/i);
});

test("individual rows are concise with progressive disclosure", async ({ page }) => {
  await loadReplay(page, "?h=6h");
  const row = page.getByTestId("market-row").first();
  await expect(row).toBeVisible({ timeout: 15000 });
  // Concise by default: a details disclosure is present but closed.
  const details = row.locator("details", { hasText: "View details" });
  await expect(details).toHaveCount(1);
  await expect(details).not.toHaveJSProperty("open", true);
  // Opening it reveals the advanced fields.
  await row.getByText("View details").click();
  await expect(row).toContainText("Research Priority");
  await expect(row).toContainText("Final resolution");
});

test("no horizontal overflow across viewports", async ({ page }) => {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await loadReplay(page, "?h=6h");
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
  await expect(page.getByTestId("replay-page")).toBeVisible();
  await expect(page.getByTestId("horizon-tabs")).toHaveCount(0, { timeout: 15000 });
  down = false;
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByTestId("horizon-tabs")).toBeVisible({ timeout: 15000 });
});
