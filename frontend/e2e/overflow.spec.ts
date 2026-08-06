import { test, expect } from "@playwright/test";
import { VIEWPORTS, auditOverflow, expectNoHorizontalOverflow } from "./helpers";

/**
 * Horizontal-overflow acceptance (final runtime acceptance §2, §3). For every required route and
 * every required viewport, the real running page must satisfy
 * document.documentElement.scrollWidth <= clientWidth AND must not actually scroll horizontally.
 * On failure, auditOverflow's offender list (selector, classes, width, transform, min-width,
 * white-space) is attached to the assertion message so the source is diagnosable from the log, and
 * Playwright captures a screenshot (configured in playwright.config.ts).
 */
const ROUTES = [
  "/",
  "/signals",
  "/markets",
  "/markets/2694364",
  "/markets/2822017",
  "/replay",
  "/replay?replay=prospective",
];

for (const route of ROUTES) {
  for (const vp of VIEWPORTS) {
    test(`no horizontal overflow: ${route} @ ${vp.name}`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(route, { waitUntil: "networkidle" });
      await page.waitForTimeout(300);

      await expectNoHorizontalOverflow(page, `${route}@${vp.name}`);

      // Also assert the page cannot actually be scrolled horizontally (belt-and-suspenders: a clip
      // guard could hide scrollWidth, but the user must never get a horizontal scrollbar either).
      const scrollX = await page.evaluate(() => {
        window.scrollTo(9999, 0);
        return window.scrollX;
      });
      expect(scrollX, `${route}@${vp.name} should not scroll horizontally`).toBe(0);
    });
  }
}

test("instrumentation reports offenders when overflow exists (self-check of the audit)", async ({
  page,
}) => {
  // Inject a deliberately-too-wide element and confirm the audit catches it — proving the audit is
  // capable of failing, so a green run on the real routes is meaningful rather than vacuous. The
  // audit works from getBoundingClientRect, which reflects real layout geometry regardless of any
  // overflow:clip guard, so this stays a genuine capability check.
  await page.setViewportSize({ width: 574, height: 900 });
  await page.goto("/signals", { waitUntil: "networkidle" });
  await page.evaluate(() => {
    const d = document.createElement("div");
    d.style.cssText = "position:relative;width:2000px;height:10px";
    d.setAttribute("data-overflow-probe", "1");
    document.body.appendChild(d);
  });
  const audit = await auditOverflow(page);
  expect(
    audit.offenders.some((o) => o.width >= 2000),
    "audit must report the injected 2000px offender",
  ).toBe(true);
});
