// One-off instrumentation (final runtime acceptance §3): open the real page at 574x900 and log the
// document scroll/client widths plus every element whose bounding box exceeds the viewport. Run with
//   node e2e/instrument.mjs [path]
import { chromium } from "@playwright/test";

const path = process.argv[2] ?? "/signals";
const width = Number(process.argv[3] ?? 574);
const height = Number(process.argv[4] ?? 900);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height } });
await page.goto(`http://localhost:3000${path}`, { waitUntil: "networkidle" });
await page.waitForTimeout(800);

const result = await page.evaluate(() => {
  const docEl = document.documentElement;
  const clientWidth = docEl.clientWidth;
  const offenders = [];
  for (const el of Array.from(document.querySelectorAll("body *"))) {
    const r = el.getBoundingClientRect();
    if (r.right > clientWidth + 0.5 && r.width > 0) {
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      offenders.push({
        tag: el.tagName.toLowerCase(),
        id: el.id || null,
        classes: typeof el.className === "string" ? el.className : "",
        width: Math.round(r.width),
        right: Math.round(r.right),
        transform: cs.transform,
        minWidth: cs.minWidth,
        whiteSpace: cs.whiteSpace,
        text: (el.textContent ?? "").trim().slice(0, 50),
      });
    }
  }
  return { scrollWidth: docEl.scrollWidth, clientWidth, overflowing: docEl.scrollWidth > clientWidth, offenders };
});

console.log(`PATH=${path}  ${width}x${height}`);
console.log(`scrollWidth: ${result.scrollWidth}  clientWidth: ${result.clientWidth}  overflowing: ${result.overflowing}`);
console.log(`offenders (${result.offenders.length}):`);
// Show the narrowest set of true sources: elements whose OWN box overflows and are not merely
// inheriting width from an overflowing child (sort by right edge, show deepest first).
for (const o of result.offenders.slice(0, 40)) {
  console.log(JSON.stringify(o));
}
await browser.close();
