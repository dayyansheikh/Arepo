import { type Page, expect } from "@playwright/test";

/** The viewports the runtime-acceptance suite must pass at (final runtime acceptance §2). 574×900 is
 * the width at which manual testing reproduced the real horizontal overflow. */
export const VIEWPORTS = [
  { name: "574x900-repro", width: 574, height: 900 },
  { name: "320x800", width: 320, height: 800 },
  { name: "375x812", width: 375, height: 812 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1440x900", width: 1440, height: 900 },
] as const;

export interface OverflowElement {
  selector: string;
  classes: string;
  width: number;
  right: number;
  transform: string;
  minWidth: string;
  whiteSpace: string;
  text: string;
}

/**
 * Instrument the real page (final runtime acceptance §3): return the document scroll/client widths
 * and every element whose bounding box exceeds the document client width, with the diagnostics the
 * spec asks for (selector, classes, width, transform, min-width, white-space).
 */
export async function auditOverflow(page: Page): Promise<{
  scrollWidth: number;
  clientWidth: number;
  overflowing: boolean;
  offenders: OverflowElement[];
}> {
  return page.evaluate(() => {
    const docEl = document.documentElement;
    const clientWidth = docEl.clientWidth;
    const offenders: OverflowElement[] = [];
    const all = Array.from(document.querySelectorAll<HTMLElement>("body *"));
    for (const el of all) {
      const r = el.getBoundingClientRect();
      // An element overflows if its right edge extends past the client width (with a 0.5px slop for
      // sub-pixel rounding) OR its left is negative beyond the page. We report right-edge overflow.
      if (r.right > clientWidth + 0.5 && r.width > 0) {
        const cs = getComputedStyle(el);
        // Skip elements that are intentionally offscreen (visibility:hidden popover pre-placement).
        if (cs.visibility === "hidden" || cs.display === "none") continue;
        const id = el.id ? `#${el.id}` : "";
        const cls = el.className && typeof el.className === "string" ? el.className : "";
        offenders.push({
          selector: `${el.tagName.toLowerCase()}${id}`,
          classes: cls,
          width: Math.round(r.width),
          right: Math.round(r.right),
          transform: cs.transform,
          minWidth: cs.minWidth,
          whiteSpace: cs.whiteSpace,
          text: (el.textContent ?? "").trim().slice(0, 60),
        });
      }
    }
    return {
      scrollWidth: docEl.scrollWidth,
      clientWidth,
      overflowing: docEl.scrollWidth > clientWidth,
      offenders,
    };
  });
}

/** Assert the document does not scroll horizontally (final runtime acceptance §2/§3). */
export async function expectNoHorizontalOverflow(page: Page, label: string) {
  const audit = await auditOverflow(page);
  if (audit.overflowing) {
    // Surface the offenders in the failure message so a regression is diagnosable from CI logs.
    // eslint-disable-next-line no-console
    console.log(`[overflow:${label}]`, JSON.stringify(audit, null, 2));
  }
  expect(
    audit.scrollWidth,
    `${label}: document scrollWidth (${audit.scrollWidth}) must be <= clientWidth (${audit.clientWidth}). Offenders: ${JSON.stringify(audit.offenders)}`,
  ).toBeLessThanOrEqual(audit.clientWidth);
}
