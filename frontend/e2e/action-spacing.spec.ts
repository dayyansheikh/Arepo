import { test, expect } from "@playwright/test";
import { VIEWPORTS } from "./helpers";

/**
 * Action-row spacing acceptance (final runtime acceptance §4). On Signal Lab, the qualification badge
 * and the "Why this fired" / "Hide detail" toggle must be a deliberate action row: the badge in its
 * own item, ≥12px horizontal gap before the toggle when they share a row, ≥8px vertical gap when the
 * toggle wraps to a second row, a padded (usable) toggle target, and no overlap. All assertions read
 * the REAL bounding rectangles.
 */
for (const vp of VIEWPORTS) {
  test(`action row spacing @ ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/signals", { waitUntil: "networkidle" });
    await page.waitForTimeout(300);

    const rows = page.locator(':has(> [data-testid="signal-qualification"]) >> visible=true');
    const toggles = page.locator('[data-testid="signal-detail-toggle"]');
    const n = await toggles.count();
    expect(n, "expected signal action rows").toBeGreaterThan(0);

    for (let i = 0; i < Math.min(n, 4); i++) {
      const badge = page.locator('[data-testid="signal-qualification"]').nth(i);
      const toggle = toggles.nth(i);
      const b = await badge.boundingBox();
      const t = await toggle.boundingBox();
      expect(b && t, `row#${i} boxes`).toBeTruthy();
      if (!b || !t) continue;

      // Padded, usable click target.
      expect(t.height, `row#${i}: toggle height (tap target)`).toBeGreaterThanOrEqual(24);

      // Same row iff the two boxes' vertical ranges overlap (robust when the badge wraps tall and
      // the toggle is vertically centred — a y-distance heuristic misclassifies that case).
      const yOverlap = !(t.y >= b.y + b.height || t.y + t.height <= b.y);
      if (yOverlap) {
        // Sharing a row → ≥12px horizontal gap (badge is left, toggle right).
        const gap = t.x - (b.x + b.width);
        expect(gap, `row#${i}: horizontal gap ≥ 12 (got ${gap.toFixed(1)})`).toBeGreaterThanOrEqual(
          12 - 0.5,
        );
      } else {
        // Wrapped to a second row → ≥8px vertical gap.
        const vgap = t.y - (b.y + b.height);
        expect(vgap, `row#${i}: vertical gap ≥ 8 (got ${vgap.toFixed(1)})`).toBeGreaterThanOrEqual(
          8 - 1,
        );
      }

      // Never overlapping rectangles.
      const overlap = !(
        t.x >= b.x + b.width ||
        t.x + t.width <= b.x ||
        t.y >= b.y + b.height ||
        t.y + t.height <= b.y
      );
      expect(overlap, `row#${i}: badge and toggle must not overlap`).toBe(false);
    }
  });
}
