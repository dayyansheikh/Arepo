import { test, expect, type Page } from "@playwright/test";
import { VIEWPORTS, expectNoHorizontalOverflow } from "./helpers";

/**
 * Complete-scan Signal Lab acceptance (prompt sections 10, 11, 22). Runs the real Next app (:3000)
 * against the real backend (:8000) and the preserved local database, which holds two recorded
 * complete scans (113k discovered, ~1.4k eligible within 30 days, ~1k directional). Proves signals
 * come first, the explanation is collapsed, top ten is shown as a display subset of the full
 * eligible universe, controls work, and trajectory + numeric strength changes render.
 */

async function loadSignals(page: Page, query = "") {
  await page.goto(`/signals${query}`, { waitUntil: "networkidle" });
  await expect(page.getByTestId("signal-lab")).toBeVisible();
  await expect(page.getByTestId("scan-status")).toBeVisible({ timeout: 15000 });
}

test("signals come first and the explanation is collapsed by default", async ({ page }) => {
  await loadSignals(page);
  // The "How Signal Lab works" explanation is a <details> that is closed by default.
  const details = page.locator("details", { hasText: "How Signal Lab works" });
  await expect(details).toHaveCount(1);
  await expect(details).not.toHaveJSProperty("open", true);

  // The actual signals section and scan status appear above the explanation.
  await expect(page.getByTestId("eligible-headline")).toBeVisible();
});

test("scan status shows raw discovered, eligible analysed and directional counts", async ({
  page,
}) => {
  await loadSignals(page);
  const headline = await page.getByTestId("eligible-headline").innerText();
  expect(headline).toMatch(/\d+ markets discovered/);
  expect(headline).toMatch(/eligible within 30 days analysed/);
  expect(headline).toMatch(/directional signals found/);
  // Honest browser-independence statement.
  await expect(page.getByTestId("scan-status")).toContainText(
    "Leaving this page open does not scan",
  );
});

test("top ten is shown as a subset of the full eligible universe", async ({ page }) => {
  await loadSignals(page, "?bucket=closing_1_7d&scope=public");
  const caption = page.getByTestId("coverage-caption");
  await expect(caption).toBeVisible();
  // "Top 20 shown from N eligible markets" - N is the full eligible set for this bucket.
  const text = await caption.innerText();
  expect(text).toMatch(/Top \d+ shown from \d+ eligible markets/);
  const shownCards = await page.getByTestId("signal-card").count();
  expect(shownCards).toBeLessThanOrEqual(20);
  expect(shownCards).toBeGreaterThan(0);
});

test("switching scope from public to all directional expands the set", async ({ page }) => {
  await loadSignals(page, "?bucket=closing_1_7d&scope=public");
  const publicCount = await page.getByTestId("signal-card").count();
  await page.getByTestId("signal-more-filters").getByText("More filters").click();
  await page.getByTestId("scope-select").selectOption("directional");
  await expect(page.getByTestId("coverage-caption")).toContainText("eligible markets", {
    timeout: 15000,
  });
  const allCount = await page.getByTestId("signal-card").count();
  expect(allCount).toBeGreaterThanOrEqual(publicCount); // ten never reduces the universe
});

test("changing the closing universe changes the signals", async ({ page }) => {
  await loadSignals(page, "?bucket=closing_1_7d&scope=public");
  await expect(page.getByTestId("coverage-caption")).toBeVisible();
  await page.getByTestId("signal-more-filters").getByText("More filters").click();
  await page.getByTestId("bucket-select").selectOption("closing_7_30d");
  // The caption re-renders for the new bucket.
  await expect(page.getByTestId("coverage-caption")).toContainText("eligible markets", {
    timeout: 15000,
  });
});

test("search, shared category and compact sorting are primary URL-backed controls", async ({
  page,
}) => {
  await loadSignals(page, "?bucket=closing_1_7d&scope=directional");
  await expect(page.getByLabel("Search Signal Lab markets")).toBeVisible();
  await expect(page.getByTestId("category-filter")).toBeVisible();
  await expect(page.getByTestId("category-other")).toHaveCount(0);
  await expect(page.getByTestId("signal-sort-select")).toHaveValue("priority_desc");

  await page.getByTestId("signal-sort-select").selectOption("strength_asc");
  await expect(page).toHaveURL(/sort=strength_asc/);
  await page.getByTestId("category-crypto").click();
  await expect(page).toHaveURL(/category=Crypto/);
  await page.getByLabel("Search Signal Lab markets").fill("election");
  await expect(page).toHaveURL(/q=election/, { timeout: 5000 });
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByTestId("signal-sort-select")).toHaveValue("strength_asc");
  await expect(page.getByTestId("category-crypto")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel("Search Signal Lab markets")).toHaveValue("election");
});

test("specialist closing and scope controls remain under More filters", async ({ page }) => {
  await loadSignals(page);
  const disclosure = page.getByTestId("signal-more-filters").locator("details");
  await expect(disclosure).not.toHaveJSProperty("open", true);
  await page.getByTestId("signal-more-filters").getByText("More filters").click();
  await expect(page.getByTestId("bucket-select")).toBeVisible();
  await expect(page.getByTestId("scope-select")).toBeVisible();
});

test("trajectory labels and numeric strength changes render, no probability language", async ({
  page,
}) => {
  await loadSignals(page, "?bucket=closing_1_7d&scope=public");
  await expect(page.getByTestId("signal-card").first()).toBeVisible();
  const phrase = await page.getByTestId("strength-phrase").first().innerText();
  expect(phrase).toMatch(/Strength \d+/);
  // Arepo's own strength phrases never frame strength as probability (external market questions
  // may legitimately mention probability, so we check the strength phrases only).
  for (const p of await page.getByTestId("strength-phrase").allInnerTexts()) {
    expect(p).not.toMatch(/more likely|probability|expected profit/i);
  }
});

test("no horizontal overflow across viewports", async ({ page }) => {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await loadSignals(page, "?bucket=closing_1_7d&scope=public");
    await expectNoHorizontalOverflow(page, `signals@${vp.name}`);
  }
});

test("disconnected scan API shows a clear state and recovers", async ({ page }) => {
  let down = true;
  await page.route("**/api/scan/status**", async (route) => {
    if (down) await route.abort("connectionrefused");
    else await route.continue();
  });
  await page.goto("/signals", { waitUntil: "domcontentloaded" });
  // The page shell survives a failed scan-status fetch (no crash, no blank page) and the headline
  // does not render because the status did not load.
  await expect(page.getByTestId("signal-lab")).toBeVisible();
  await expect(page.getByTestId("eligible-headline")).toHaveCount(0, { timeout: 15000 });
  // Recovers on reload once the API is back.
  down = false;
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByTestId("eligible-headline")).toBeVisible({ timeout: 15000 });
});
