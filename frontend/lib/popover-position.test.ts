import { describe, expect, it } from "vitest";
import {
  POPOVER_MARGIN,
  type Rect,
  computePopoverPosition,
} from "./popover-position";

// The six supported widths from the prompt. Height fixed; zoom is represented by the fact that the
// maths is in CSS pixels (a zoomed viewport reports a smaller CSS width, already covered by 320).
const WIDTHS = [320, 375, 768, 1024, 1280, 1440];

function rect(left: number, top: number, w = 20, h = 16): Rect {
  return { left, top, right: left + w, bottom: top + h, width: w, height: h };
}

describe("computePopoverPosition", () => {
  it.each(WIDTHS)("never overflows the viewport at width %i (trigger near right edge)", (width) => {
    const viewport = { width, height: 800 };
    // Trigger hard against the right edge — the classic overflow case.
    const trigger = rect(width - 24, 100);
    const panel = { width: 320, height: 140 };
    const p = computePopoverPosition(trigger, panel, viewport);
    // Left edge stays within the margin.
    expect(p.left).toBeGreaterThanOrEqual(POPOVER_MARGIN);
    // Right edge (left + actual width) stays fully inside the viewport minus the margin.
    const actualWidth = Math.min(panel.width, p.maxWidth);
    expect(p.left + actualWidth).toBeLessThanOrEqual(width - POPOVER_MARGIN);
  });

  it.each(WIDTHS)("caps max width to the viewport at width %i", (width) => {
    const p = computePopoverPosition(rect(10, 10), { width: 320, height: 100 }, {
      width,
      height: 800,
    });
    expect(p.maxWidth).toBeLessThanOrEqual(width - 2 * POPOVER_MARGIN);
    expect(p.maxWidth).toBeGreaterThan(0);
  });

  it("flips above when there is no room below", () => {
    const viewport = { width: 1024, height: 600 };
    const trigger = rect(200, 560); // near the bottom
    const panel = { width: 300, height: 200 };
    const p = computePopoverPosition(trigger, panel, viewport);
    expect(p.placement).toBe("above");
    expect(p.top).toBeGreaterThanOrEqual(POPOVER_MARGIN);
    expect(p.top + panel.height).toBeLessThanOrEqual(trigger.top); // sits above the trigger
  });

  it("stays below when there is room", () => {
    const p = computePopoverPosition(rect(200, 100), { width: 300, height: 120 }, {
      width: 1024,
      height: 800,
    });
    expect(p.placement).toBe("below");
    expect(p.top).toBeGreaterThan(100);
  });

  it("aligns to the trigger left when there is room (no needless shift)", () => {
    const p = computePopoverPosition(rect(200, 100), { width: 300, height: 120 }, {
      width: 1024,
      height: 800,
    });
    expect(p.left).toBe(200);
  });

  it("never produces a negative or off-screen coordinate for a tiny viewport", () => {
    const p = computePopoverPosition(rect(300, 10), { width: 320, height: 500 }, {
      width: 320,
      height: 480,
    });
    expect(p.left).toBeGreaterThanOrEqual(POPOVER_MARGIN);
    expect(p.top).toBeGreaterThanOrEqual(POPOVER_MARGIN);
    expect(p.left + Math.min(320, p.maxWidth)).toBeLessThanOrEqual(320 - POPOVER_MARGIN);
  });
});
