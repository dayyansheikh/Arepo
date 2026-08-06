import { test, expect } from "@playwright/test";

/**
 * Replay real-cohort acceptance (final runtime acceptance §5). The default Replay view must be the
 * REAL prospective research (not reconstructed, not synthetic), showing the real 6h cohort recorded
 * in the local database: 60 frozen markets, the role counts, horizon coverage, and a prominent
 * banner with the actual freeze time, scheduled time and lateness. Synthetic is a separate control.
 */
test("default Replay shows real prospective research, not reconstructed/synthetic", async ({ page }) => {
  await page.goto("/replay", { waitUntil: "networkidle" });
  await page.waitForTimeout(600);

  await expect(page.getByTestId("real-prospective-research")).toBeVisible();
  await expect(page.getByTestId("replay-tab-research")).toHaveAttribute("aria-selected", "true");

  // The real cohort's headline numbers from the reproduced payload.
  const section = page.getByTestId("real-prospective-research");
  await expect(section).toContainText("60"); // total frozen markets
});

test("prominent freeze-timing banner shows actual freeze, scheduled time and lateness", async ({ page }) => {
  await page.goto("/replay", { waitUntil: "networkidle" });
  await page.waitForTimeout(600);

  const banner = page.getByTestId("freeze-timing-banner");
  await expect(banner).toBeVisible();
  const text = (await banner.innerText()).replace(/\s+/g, " ");
  expect(text).toMatch(/Actually frozen at/i);
  expect(text).toMatch(/scheduled for/i);
  expect(text).toMatch(/minutes late/i);
  expect(text).toMatch(/outcomes measured from the actual freeze time/i);
  // ~84 minutes late (lateness_seconds 5053 → 84 min).
  expect(text).toMatch(/8[0-9] minutes late/);
});

test("edge verdict, calibration and horizon coverage are present", async ({ page }) => {
  await page.goto("/replay", { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  await expect(page.getByTestId("edge-verdict")).toBeVisible();
  const body = await page.locator("body").innerText();
  expect(body).toMatch(/Calibration (available|unavailable)/i);
  expect(body).toMatch(/Horizon coverage/i);
  expect(body).toMatch(/Model limitation/i);
});

test("legacy ?replay=prospective lands on the REAL research (not synthetic)", async ({ page }) => {
  await page.goto("/replay?replay=prospective", { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  await expect(page.getByTestId("real-prospective-research")).toBeVisible();
  await expect(page.getByTestId("freeze-timing-banner")).toBeVisible();
});

test("synthetic demonstration is a separate control and not shown by default", async ({ page }) => {
  await page.goto("/replay", { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  // Not shown by default.
  await expect(page.getByText("Everything below is synthetic demonstration data")).toHaveCount(0);

  // Reachable via its own tab, clearly labelled synthetic.
  await page.getByTestId("replay-tab-demo").click();
  await page.waitForTimeout(400);
  await expect(page.getByText("Everything below is synthetic demonstration data")).toBeVisible();
  // The real research section is no longer the active view.
  await expect(page.getByTestId("real-prospective-research")).toHaveCount(0);
});

test("reconstructed analysis is separate and clearly secondary", async ({ page }) => {
  await page.goto("/replay", { waitUntil: "networkidle" });
  await page.getByTestId("replay-tab-reconstructed").click();
  await page.waitForTimeout(500);
  await expect(page.getByText("Reconstructed analysis").first()).toBeVisible();
});
