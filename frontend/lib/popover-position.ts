// Pure, DOM-free popover positioning (final pre-deployment §6). Kept separate from the React
// component so the flip/shift/clamp logic is unit-testable at every required viewport width without
// a browser. Coordinates are viewport-relative CSS pixels (used with position: fixed), so the same
// maths stays correct under browser zoom.

export interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
}

export interface Viewport {
  width: number;
  height: number;
}

export interface PopoverPosition {
  left: number;
  top: number;
  maxWidth: number;
  placement: "below" | "above";
}

export const POPOVER_MARGIN = 8;
export const POPOVER_GAP = 8;
export const POPOVER_MAX_WIDTH = 320;

/**
 * Place a panel of size `panel` relative to a `trigger` within a `viewport`, so the panel is always
 * fully inside the viewport with a safe margin: it aligns to the trigger's left edge then shifts to
 * stay on-screen (flips horizontally near the right edge), and drops below the trigger unless there
 * is no room, in which case it flips above. The returned left+maxWidth guarantee
 * `left + width <= viewport.width - margin`, so the panel can never expand the document width.
 */
export function computePopoverPosition(
  trigger: Rect,
  panel: { width: number; height: number },
  viewport: Viewport,
  { margin = POPOVER_MARGIN, gap = POPOVER_GAP, maxWidth = POPOVER_MAX_WIDTH } = {},
): PopoverPosition {
  const cappedMaxWidth = Math.max(0, Math.min(maxWidth, viewport.width - 2 * margin));
  const panelWidth = Math.min(panel.width || cappedMaxWidth, cappedMaxWidth);
  const panelHeight = panel.height;

  // Horizontal: align to the trigger left, then clamp fully inside [margin, viewport - margin].
  let left = trigger.left;
  left = Math.min(left, viewport.width - margin - panelWidth);
  left = Math.max(margin, left);

  // Vertical: below by default; flip above when there is no room below but there is above.
  let placement: "below" | "above" = "below";
  let top = trigger.bottom + gap;
  const roomBelow = viewport.height - margin - (trigger.bottom + gap);
  const roomAbove = trigger.top - gap - margin;
  if (panelHeight > roomBelow && roomAbove >= panelHeight) {
    placement = "above";
    top = trigger.top - gap - panelHeight;
  }
  top = Math.max(margin, Math.min(top, viewport.height - margin - panelHeight));

  return { left, top, maxWidth: cappedMaxWidth, placement };
}
