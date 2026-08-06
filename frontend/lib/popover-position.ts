// Pure, DOM-free popover positioning (final pre-deployment §6, final runtime acceptance §1). Kept
// separate from the React component so the flip/shift/clamp logic is unit-testable at every required
// viewport width without a browser. Coordinates are viewport-relative CSS pixels (used with
// position: fixed), so the same maths stays correct under browser zoom. The viewport may carry an
// `offsetLeft`/`offsetTop` (from window.visualViewport) so clamping stays correct under pinch-zoom
// and mobile keyboards, where the visual viewport is inset within the layout viewport.

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
  /** Visual-viewport inset within the layout viewport (visualViewport.offsetLeft/offsetTop). */
  offsetLeft?: number;
  offsetTop?: number;
}

export interface PopoverPosition {
  left: number;
  top: number;
  maxWidth: number;
  placement: "below" | "above";
}

// At least 12px from every viewport edge (final runtime acceptance §1); 22rem ≈ 352px cap so the
// panel never grows wider than min(22rem, 100dvw - 24px).
export const POPOVER_MARGIN = 12;
export const POPOVER_GAP = 8;
export const POPOVER_MAX_WIDTH = 352;

/** The width cap for a given viewport: min(22rem, viewport - 2·margin). Exported so the React layer
 * can apply the SAME cap to the panel BEFORE measuring it — otherwise the panel would be measured at
 * one width and revealed at another, and the wider revealed panel would spill past the clamp. */
export function popoverMaxWidth(
  viewportWidth: number,
  { margin = POPOVER_MARGIN, maxWidth = POPOVER_MAX_WIDTH } = {},
): number {
  return Math.max(0, Math.min(maxWidth, viewportWidth - 2 * margin));
}

/**
 * Place a panel of size `panel` relative to a `trigger` within a `viewport`, so the panel is always
 * fully inside the viewport with a safe margin: it aligns to the trigger's left edge then shifts to
 * stay on-screen (flips horizontally near the right edge), and drops below the trigger unless there
 * is no room, in which case it flips above. The returned left+maxWidth guarantee
 * `left + width <= viewport.right - margin`, so the panel can never expand the document width.
 *
 * `panel.width`/`panel.height` MUST be the panel's real measured size (getBoundingClientRect) after
 * the same maxWidth cap has been applied, so the clamp reserves exactly the space the panel occupies.
 */
export function computePopoverPosition(
  trigger: Rect,
  panel: { width: number; height: number },
  viewport: Viewport,
  { margin = POPOVER_MARGIN, gap = POPOVER_GAP, maxWidth = POPOVER_MAX_WIDTH } = {},
): PopoverPosition {
  const vpLeft = viewport.offsetLeft ?? 0;
  const vpTop = viewport.offsetTop ?? 0;
  const vpRight = vpLeft + viewport.width;
  const vpBottom = vpTop + viewport.height;

  const cappedMaxWidth = popoverMaxWidth(viewport.width, { margin, maxWidth });
  const panelWidth = Math.min(panel.width || cappedMaxWidth, cappedMaxWidth);
  const panelHeight = panel.height;

  // Horizontal: align to the trigger left, then clamp fully inside [vpLeft+margin, vpRight-margin].
  let left = trigger.left;
  left = Math.min(left, vpRight - margin - panelWidth);
  left = Math.max(vpLeft + margin, left);

  // Vertical: below by default; flip above when there is no room below but there is above.
  let placement: "below" | "above" = "below";
  let top = trigger.bottom + gap;
  const roomBelow = vpBottom - margin - (trigger.bottom + gap);
  const roomAbove = trigger.top - gap - (vpTop + margin);
  if (panelHeight > roomBelow && roomAbove >= panelHeight) {
    placement = "above";
    top = trigger.top - gap - panelHeight;
  }
  top = Math.max(vpTop + margin, Math.min(top, vpBottom - margin - panelHeight));

  return { left, top, maxWidth: cappedMaxWidth, placement };
}
