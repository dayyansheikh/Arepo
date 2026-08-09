import { test, expect } from "@playwright/test";

const cards = [
  {
    id: "high", question: "Alpha market high", slug: "high", category: "Crypto",
    sport: null, competition: null, status: "active", tags: ["Crypto"], volume: 10,
    volume_24hr: 2, liquidity: 5, end_date: "2026-08-20T00:00:00Z",
    top_probability: 0.6, top_outcome: "Yes", spread: null, abs_movement: null,
    signal_strength: 0.9,
  },
  {
    id: "low", question: "Alpha market low", slug: "low", category: "Crypto",
    sport: null, competition: null, status: "active", tags: ["Crypto"], volume: 20,
    volume_24hr: 4, liquidity: 6, end_date: "2026-08-12T00:00:00Z",
    top_probability: 0.4, top_outcome: "No", spread: null, abs_movement: null,
    signal_strength: 0.2,
  },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/markets?**", async (route) => {
    const url = new URL(route.request().url());
    const sorted = url.searchParams.get("sort") === "signal_asc" ? [...cards].reverse() : cards;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        markets: sorted,
        total: sorted.length,
        limit: Number(url.searchParams.get("limit") ?? 48),
        offset: 0,
        status: {
          mode: "cached", rest: { name: "cache", state: "connected" },
          websocket: { name: "clob_ws", state: "unknown" },
          last_update: "2026-08-09T19:00:00Z", data_age_seconds: 60,
          degradation_reason: null,
        },
      }),
    });
  });
});

test("Explore exposes only one search, shared category, time and signal sort controls", async ({
  page,
}) => {
  await page.goto("/markets", { waitUntil: "networkidle" });
  const controls = page.getByTestId("explore-controls");
  await expect(page.getByLabel("Search markets")).toHaveCount(1);
  await expect(controls.getByTestId("category-filter")).toBeVisible();
  await expect(controls.getByTestId("category-other")).toHaveCount(0);
  await expect(controls.getByTestId("closing-select")).toBeVisible();
  await expect(controls.getByTestId("signal-sort-select")).toHaveValue("signal_desc");
  await expect(controls.getByText("Status", { exact: true })).toHaveCount(0);
  await expect(controls.getByText("Probability", { exact: true })).toHaveCount(0);
  await expect(controls.getByText("Volume", { exact: true })).toHaveCount(0);
  await expect(controls.getByText("Newest", { exact: true })).toHaveCount(0);
  await expect(controls.getByText("Sport", { exact: true })).toHaveCount(0);
  await expect(controls.getByText("Competition", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Advanced: search by keyword")).toHaveCount(0);
});

test("Explore filter state survives URL navigation and refresh", async ({ page }) => {
  await page.goto("/markets", { waitUntil: "networkidle" });
  await page.getByLabel("Search markets").fill("Alpha");
  await expect(page).toHaveURL(/q=Alpha/, { timeout: 5000 });
  await page.getByTestId("category-crypto").click();
  await expect(page).toHaveURL(/category=Crypto/);
  await page.getByTestId("closing-select").selectOption("month");
  await expect(page).toHaveURL(/close=month/);
  await page.getByTestId("signal-sort-select").selectOption("signal_asc");
  await expect(page).toHaveURL(/sort=signal_asc/);
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByLabel("Search markets")).toHaveValue("Alpha");
  await expect(page.getByTestId("category-crypto")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("closing-select")).toHaveValue("month");
  await expect(page.getByTestId("signal-sort-select")).toHaveValue("signal_asc");
});
