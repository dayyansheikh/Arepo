import { test, expect, type Page } from "@playwright/test";

/**
 * Auth-page footer acceptance (final-completion prompt D2). The sticky-footer shell (body is a
 * full-viewport flex column, main is flex-1, the footer follows main) must place the footer at the
 * very bottom of the viewport on the short auth pages, with no large gap below it.
 */
async function footerReachesBottom(page: Page, path: string) {
  await page.goto(path, { waitUntil: "networkidle" });
  const info = await page.evaluate(() => {
    const footer = document.querySelector("footer");
    if (!footer) return null;
    const r = footer.getBoundingClientRect();
    return {
      footerTop: r.top,
      footerBottom: r.bottom,
      viewportH: window.innerHeight,
      docH: document.documentElement.scrollHeight,
      scrollY: window.scrollY,
    };
  });
  expect(info, `footer present on ${path}`).not.toBeNull();
  // The footer must follow content with no gap below it AND, when the page fits the viewport, reach
  // the bottom (the exact D2 bug: on a short auth page the footer floated in the middle).
  if (info!.docH <= info!.viewportH + 2) {
    // Short page: footer bottom is at the viewport bottom.
    expect(
      Math.abs(info!.footerBottom - info!.viewportH),
      `${path} short-page footer reaches the viewport bottom`,
    ).toBeLessThanOrEqual(2);
  } else {
    // Taller-than-viewport page: footer sits at the very end of the document, no gap below it.
    expect(
      Math.abs(info!.footerBottom + info!.scrollY - info!.docH),
      `${path} footer follows the content to the document end`,
    ).toBeLessThanOrEqual(2);
  }
}

for (const path of ["/signin", "/signup", "/reset"]) {
  test(`auth footer reaches the bottom on ${path} (desktop)`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await footerReachesBottom(page, path);
  });

  test(`auth footer reaches the bottom on ${path} (mobile)`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await footerReachesBottom(page, path);
  });
}
