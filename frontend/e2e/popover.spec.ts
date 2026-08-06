import { test, expect, type Page } from "@playwright/test";
import { VIEWPORTS } from "./helpers";

/**
 * Popover geometry acceptance (final runtime acceptance §1, §2). Opens the real information popovers
 * on Signal Lab at every required viewport and asserts, from the REAL rendered bounding rectangle,
 * that the panel stays ≥12px inside every viewport edge and never expands the document. This is the
 * check the pure positioning unit tests could not make: it exercises the two-pass measure/clamp on a
 * genuinely-rendered panel, including the previously-broken case where the panel was measured at one
 * width and revealed wider.
 */
const MARGIN = 12;

async function openTriggers(page: Page): Promise<number> {
  // The info popovers are buttons with aria-controls (MetricHelp / Popover triggers).
  return page.locator("button[aria-controls]").count();
}

/** Click candidate triggers until one actually opens a [role=tooltip] popover; leaves it open and
 * returns its locator, or null if none opened. The aria-controls selector also matches the detail
 * toggle (not a tooltip), so we must probe rather than assume. */
async function openFirstTooltipTrigger(page: Page) {
  const triggers = page.locator("button[aria-controls]");
  const count = await triggers.count();
  for (let i = count - 1; i >= 0; i--) {
    const t = triggers.nth(i);
    await t.scrollIntoViewIfNeeded();
    await t.click();
    await page.waitForTimeout(80);
    const tip = page.locator('[role="tooltip"]');
    if ((await tip.count()) > 0 && (await tip.last().isVisible())) return t;
    await page.keyboard.press("Escape");
    await page.waitForTimeout(30);
  }
  return null;
}

async function assertPanelInside(page: Page, vp: { width: number; height: number }, label: string) {
  // A visible tooltip panel is portaled to <body> with role="tooltip".
  const panel = page.locator('[role="tooltip"]').last();
  await expect(panel).toBeVisible();
  const box = await panel.boundingBox();
  expect(box, `${label}: panel should have a box`).not.toBeNull();
  if (!box) return;
  expect(box.x, `${label}: left ≥ ${MARGIN}`).toBeGreaterThanOrEqual(MARGIN - 0.5);
  expect(
    box.x + box.width,
    `${label}: right (${(box.x + box.width).toFixed(1)}) ≤ viewport (${vp.width}) - ${MARGIN}`,
  ).toBeLessThanOrEqual(vp.width - MARGIN + 0.5);
  expect(box.y, `${label}: top ≥ ${MARGIN}`).toBeGreaterThanOrEqual(MARGIN - 0.5);
  // Bottom may exceed the viewport only if the panel is physically taller than the space; assert it
  // stays inside when it can (panel shorter than viewport height).
  if (box.height <= vp.height - 2 * MARGIN) {
    expect(
      box.y + box.height,
      `${label}: bottom ≤ viewport (${vp.height}) - ${MARGIN}`,
    ).toBeLessThanOrEqual(vp.height - MARGIN + 0.5);
  }
  // Opening the popover must never expand the document.
  const doc = await page.evaluate(() => ({
    s: document.documentElement.scrollWidth,
    c: document.documentElement.clientWidth,
  }));
  expect(doc.s, `${label}: document must not widen when popover open`).toBeLessThanOrEqual(doc.c);
}

for (const vp of VIEWPORTS) {
  test(`popover stays inside the viewport @ ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/signals", { waitUntil: "networkidle" });
    await page.waitForTimeout(300);

    const count = await openTriggers(page);
    expect(count, "expected info popover triggers on Signal Lab").toBeGreaterThan(0);

    // Only a sample is needed and iterating all 20+ triggers per viewport is too slow. Prioritise the
    // rightmost triggers (nearest the right edge — the original off-screen repro case), plus a couple
    // near the start. Only assert geometry for candidates that actually open a tooltip popover (the
    // aria-controls selector also matches the non-tooltip detail toggle). Stop after 3 assertions.
    const triggers = page.locator("button[aria-controls]");
    const order = [
      count - 1,
      count - 2,
      count - 3,
      0,
      1,
      Math.floor(count / 2),
    ].filter((v, i, a) => v >= 0 && v < count && a.indexOf(v) === i);

    let asserted = 0;
    for (const i of order) {
      if (asserted >= 3) break;
      const trigger = triggers.nth(i);
      await trigger.scrollIntoViewIfNeeded();
      await trigger.click();
      await page.waitForTimeout(90);
      const tooltip = page.locator('[role="tooltip"]');
      if ((await tooltip.count()) > 0 && (await tooltip.last().isVisible())) {
        await assertPanelInside(page, vp, `${vp.name} trigger#${i}`);
        asserted += 1;
      }
      await page.keyboard.press("Escape");
      await page.waitForTimeout(40);
    }
    expect(asserted, `expected at least one tooltip popover to open @ ${vp.name}`).toBeGreaterThan(0);
  });
}

test("popover stays inside after scroll and after resize @ 574x900", async ({ page }) => {
  await page.setViewportSize({ width: 574, height: 900 });
  await page.goto("/signals", { waitUntil: "networkidle" });
  await page.waitForTimeout(300);

  const trigger = await openFirstTooltipTrigger(page);
  expect(trigger, "a tooltip popover trigger on Signal Lab").not.toBeNull();

  // Open, then scroll the page — the popover must reposition and stay inside.
  await assertPanelInside(page, { width: 574, height: 900 }, "before-scroll");
  await page.mouse.wheel(0, 200);
  await page.waitForTimeout(150);
  await assertPanelInside(page, { width: 574, height: 900 }, "after-scroll");

  // Resize while open — must reposition and stay inside.
  await page.setViewportSize({ width: 375, height: 812 });
  await page.waitForTimeout(200);
  await assertPanelInside(page, { width: 375, height: 812 }, "after-resize");
});

test("popover supports keyboard + ARIA and closes on Escape", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/signals", { waitUntil: "networkidle" });
  await page.waitForTimeout(300);

  // Find the first trigger that actually opens a tooltip popover.
  const trigger = await openFirstTooltipTrigger(page);
  expect(trigger, "a tooltip popover trigger").not.toBeNull();
  if (!trigger) return;
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator('[role="tooltip"]')).toHaveCount(0);
});
