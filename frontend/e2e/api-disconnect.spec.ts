import { test, expect } from "@playwright/test";

/**
 * API disconnection acceptance (final runtime acceptance §7). When /api/status fails, the UI must
 * show ONE clear "API disconnected" state, must NOT flood the console/network with retries (bounded
 * backoff), must not raise unhandled rejections, and must recover automatically when the API returns.
 *
 * The status chip is only rendered at md+ widths, so this runs at 1024×768.
 */
test("disconnected → bounded retries → automatic recovery, no unhandled rejections", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1024, height: 768 });

  const rejections: string[] = [];
  await page.addInitScript(() => {
    window.addEventListener("unhandledrejection", (e) => {
      // Record on window so the test can read it.
      (window as unknown as { __rejections: string[] }).__rejections ??= [];
      (window as unknown as { __rejections: string[] }).__rejections.push(String(e.reason));
    });
  });
  page.on("pageerror", (e) => rejections.push(String(e)));

  // Count status requests to prove there is no flood.
  let statusRequests = 0;
  page.on("request", (req) => {
    if (req.url().includes("/api/status")) statusRequests += 1;
  });

  // Simulate the backend being down for /api/status only.
  let down = true;
  await page.route("**/api/status**", async (route) => {
    if (down) await route.abort("connectionrefused");
    else await route.continue();
  });

  await page.goto("/signals", { waitUntil: "domcontentloaded" });

  // One clear disconnected state appears.
  await expect(page.getByTestId("api-disconnected")).toBeVisible({ timeout: 15000 });

  // Bounded retries: over a multi-second window while down, the shared backoff poller must issue only
  // a handful of requests (base cadence is 30s), never a tight loop. Allow generous headroom for
  // React StrictMode double-mounting in dev; a flood would be dozens.
  const before = statusRequests;
  await page.waitForTimeout(4000);
  const during = statusRequests - before;
  expect(during, `status requests in 4s while down (${during}) must be bounded`).toBeLessThanOrEqual(4);

  // Bring the API back and trigger the poller's immediate resume (its visibilitychange handler polls
  // at once when the tab is visible) rather than waiting for the 30s backoff timer.
  down = false;
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));

  // Recovers automatically to the connected chip.
  await expect(page.getByTestId("api-connected")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("api-disconnected")).toHaveCount(0);

  // No unhandled rejections throughout.
  const winRejections = await page.evaluate(
    () => (window as unknown as { __rejections?: string[] }).__rejections ?? [],
  );
  expect([...rejections, ...winRejections], "no unhandled rejections / page errors").toEqual([]);
});
