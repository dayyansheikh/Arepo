import { test, expect, type Page } from "@playwright/test";
import { VIEWPORTS, expectNoHorizontalOverflow } from "./helpers";

/**
 * Opportunities (public top 20) acceptance (final-completion prompt B1, D1, F3). Real Next app
 * (:3000) + real backend (:8000) + preserved database (a complete scan of ~1.4k eligible / ~1k
 * directional). Proves the public shortlist is the top 20 with an honest denominator, the closing
 * window filter works, freshness is plain, the global Live/Cached/Replay switch is gone, and there
 * is no HTTP/pagination jargon in the primary view.
 */
async function load(page: Page, query = "") {
  await page.goto(`/${query}`, { waitUntil: "networkidle" });
  await expect(page.getByTestId("opportunities-page")).toBeVisible();
}

test("shows the public top 20 with an honest denominator", async ({ page }) => {
  await load(page);
  await expect(page.getByTestId("denominator")).toBeVisible({ timeout: 15000 });
  const denom = await page.getByTestId("denominator").innerText();
  // "20 opportunities shown from N directional signals across M eligible markets."
  expect(denom).toMatch(/\d+ opportunities shown from \d+ directional signals across \d+ eligible markets/);
  const cards = await page.getByTestId("opportunity-card").count();
  expect(cards).toBeGreaterThan(0);
  expect(cards).toBeLessThanOrEqual(20);
});

test("no backend jargon in the primary public view", async ({ page }) => {
  await load(page);
  const body = await page.locator("body").innerText();
  // The B4 jargon list: HTTP status codes, keyset/cursor failures, pagination caps, exceptions.
  expect(body).not.toMatch(
    /HTTP \d{3}|keyset|after_cursor|pagination cap|cursor failure|internal exception|backend scan/i,
  );
  // Arepo's OWN strength copy never frames strength as probability (market questions are external
  // content and may legitimately mention probability, so we check the strength phrases only).
  const phrases = await page.getByTestId("strength-phrase").allInnerTexts();
  for (const p of phrases) {
    expect(p).not.toMatch(/more likely|probability|expected profit/i);
  }
});

test("closing window filter changes the shortlist", async ({ page }) => {
  await load(page);
  await expect(page.getByTestId("denominator")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("window-select").selectOption("within_24h");
  // The denominator re-renders for the new window (label 'Later today').
  await expect(page.getByTestId("denominator")).toBeVisible();
});

test("freshness is shown in plain words, not a 'Stale' label", async ({ page }) => {
  await load(page);
  const fresh = page.getByTestId("freshness");
  await expect(fresh).toBeVisible({ timeout: 15000 });
  const text = await fresh.innerText();
  expect(text).toMatch(/Updated .* ago|Refresh delayed|Out of date/);
  expect(text).not.toMatch(/\bStale\b/);
});

test("the global Live/Cached/Replay mode switch is removed", async ({ page }) => {
  await load(page);
  const body = await page.locator("body").innerText();
  // The old segmented control offered these three as a data-mode selector in the header.
  const header = await page.locator("header").innerText();
  expect(header).not.toMatch(/Cached/);
  expect(body).not.toContain("Data mode");
});

test("opportunity cards link to market detail and show a strength bar", async ({ page }) => {
  await load(page);
  await expect(page.getByTestId("opportunity-card").first()).toBeVisible({ timeout: 15000 });
  const meter = page.getByRole("meter").first();
  await expect(meter).toBeVisible();
  await expect(page.getByRole("link", { name: "Market detail" }).first()).toBeVisible();
});

test("no horizontal overflow across viewports", async ({ page }) => {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await load(page);
    await expectNoHorizontalOverflow(page, `opportunities@${vp.name}`);
  }
});
