import { test, expect, type Page } from "@playwright/test";
import { expectNoHorizontalOverflow } from "./helpers";

const NOW = new Date().toISOString();
const row = (id: number, title: string, s: number, c: string) => ({
  market_id: id,
  title,
  signal_strength: s,
  confidence: c,
});
const PAYLOAD = {
  schema: "arepo-public-signals-v1",
  status: "ok",
  server_time: NOW,
  snapshot_received_at: NOW,
  champion: { model_id: "champ_a", family: "lr" },
  feed: {
    origin_utc: NOW,
    stale: false,
    top_up: [
      row(101, "A very long market title that should wrap rather than push the page wider than the screen", 0.312, "strong"),
      row(102, "Second up market", 0.12, "moderate"),
    ],
    top_down: [row(201, "First down market", -0.104, "moderate")],
    track_record: { days: 20, n: 900, brier: 0.241, log_loss: 0.671, cal_slope: 0.93, cal_intercept: 0.01 },
    days_scored: 20,
    bands: [
      { band: "strong", n: 80, events: 40, status: "ok", log_loss: 0.6, brier: 0.22, cal_slope: 1.1 },
      { band: "weak", n: 5, events: 2, status: "unavailable" },
    ],
  },
  leaderboard: [
    { model_id: "champ_a", family: "lr", role: "champion", days: 20, n: 900, log_loss: 0.671, brier: 0.241, provisional: false },
    { model_id: "secret_b", family: "gbm", role: "challenger", hidden_until: "2099-01-01" },
  ],
};

async function mock(page: Page, status: number, body: unknown) {
  await page.route("**/api/public/signals**", (route) =>
    route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) }),
  );
}

test("live render: notice, badge, tables, records, embargo", async ({ page }) => {
  await mock(page, 200, PAYLOAD);
  await page.goto("/signals/live", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Live signal strength");
  await expect(page.getByTestId("live-notice")).toContainText("Signal strength, not a probability.");
  await expect(page.getByTestId("live-badge")).toContainText("Live");
  await expect(page.getByTestId("live-badge")).toContainText("UTC");
  await expect(page.getByTestId("live-top-up")).toContainText("+0.312");
  await expect(page.getByTestId("live-top-down")).toContainText("-0.104");
  await expect(page.getByTestId("live-top-up").getByRole("link", { name: "Second up market" })).toHaveAttribute(
    "href",
    "/markets/102",
  );
  await expect(page.getByTestId("live-record")).toContainText("0.671");
  await expect(page.getByTestId("live-bands")).toContainText("unavailable");
  const emb = page.getByTestId("live-embargoed-row");
  await expect(emb).toContainText("hidden until 2099-01-01");
  expect((await emb.innerText()).replace("secret_b", "").replace("2099-01-01", "")).not.toMatch(/\d/);
  await expect(page.locator("main")).not.toContainText("%");
});

test("stale snapshot is labelled in text", async ({ page }) => {
  await mock(page, 200, { ...PAYLOAD, status: "stale", feed: { ...PAYLOAD.feed, stale: true } });
  await page.goto("/signals/live", { waitUntil: "networkidle" });
  await expect(page.getByTestId("live-badge")).toContainText("Stale");
});

test("disabled endpoint shows a calm not-public message", async ({ page }) => {
  await mock(page, 404, { detail: "Not Found" });
  await page.goto("/signals/live", { waitUntil: "networkidle" });
  await expect(page.getByTestId("live-unavailable")).toContainText("Live signals are not public yet");
  await expect(page.getByTestId("live-top-up")).toHaveCount(0);
});

test("API error shows temporarily unavailable", async ({ page }) => {
  await mock(page, 500, { detail: "boom" });
  await page.goto("/signals/live", { waitUntil: "networkidle" });
  await expect(page.getByTestId("live-unavailable")).toContainText("temporarily unavailable");
});

for (const width of [320, 375, 574]) {
  test(`no horizontal overflow @ ${width}`, async ({ page }) => {
    await mock(page, 200, PAYLOAD);
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/signals/live", { waitUntil: "networkidle" });
    await expect(page.getByTestId("live-top-up")).toBeVisible();
    await expectNoHorizontalOverflow(page, `signals-live@${width}`);
    expect(await page.evaluate(() => { window.scrollTo(9999, 0); return window.scrollX; })).toBe(0);
  });
}
