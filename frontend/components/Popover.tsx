"use client";

import {
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import {
  POPOVER_MARGIN,
  computePopoverPosition,
  popoverMaxWidth,
} from "@/lib/popover-position";

/**
 * Viewport-aware information popover primitive (final pre-deployment §6, final runtime acceptance §1).
 *
 * The panel is rendered through a portal to <body> with `position: fixed`, so it is never clipped by
 * a card's overflow or a sticky container, and it can never expand the document width or create
 * horizontal scrolling.
 *
 * Positioning uses REAL rendered geometry, in two passes:
 *   1. On open, the panel's max-width is capped to `min(22rem, viewport - 24px)` and it is rendered
 *      hidden (visibility:hidden) so it never flashes off-screen.
 *   2. A layout effect then measures the panel with getBoundingClientRect() — at the SAME capped
 *      max-width it will be revealed at — and clamps its left/top to keep it ≥12px from every edge
 *      before making it visible. Because the measured width already reflects the cap, the reveal
 *      width equals the measured width, so the panel can never spill past the clamp (the previous
 *      bug: measured at 320px, revealed wider, overflowing the right edge).
 *
 * The visual viewport (window.visualViewport) is used when available so the clamp stays correct
 * under pinch-zoom and mobile keyboards; otherwise the document client box is used. It flips above
 * the trigger when there is no room below, shifts horizontally near either edge, and repositions on
 * open, scroll, resize and visualViewport resize/scroll.
 *
 * Opens on hover, focus and click/tap; closes on Escape, outside pointer-down, and blur. The trigger
 * is a real button with aria-expanded / aria-controls; the panel carries role="tooltip" and an id.
 */
export function Popover({
  trigger,
  children,
  label,
  panelClassName = "",
  triggerClassName = "",
}: {
  trigger: ReactNode;
  children: ReactNode;
  label?: string; // accessible label used when the trigger has no visible text
  panelClassName?: string;
  triggerClassName?: string;
}) {
  const id = useId();
  const [mounted, setMounted] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  // Capped up-front from the viewport so it is applied BEFORE measurement (see class docstring).
  const [maxWidth, setMaxWidth] = useState<number | undefined>(undefined);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const open = pinned || hovered || focused;

  useEffect(() => setMounted(true), []);

  const readViewport = useCallback(() => {
    const vv = typeof window !== "undefined" ? window.visualViewport : null;
    if (vv) {
      return {
        width: vv.width,
        height: vv.height,
        offsetLeft: vv.offsetLeft,
        offsetTop: vv.offsetTop,
      };
    }
    return {
      width: document.documentElement.clientWidth,
      height: document.documentElement.clientHeight,
      offsetLeft: 0,
      offsetTop: 0,
    };
  }, []);

  const place = useCallback(() => {
    const t = triggerRef.current?.getBoundingClientRect();
    if (!t) return;
    const viewport = readViewport();
    const cap = popoverMaxWidth(viewport.width);
    // Apply the cap first so the measured width equals the revealed width.
    if (maxWidth !== cap) setMaxWidth(cap);
    const panelEl = panelRef.current;
    const rect = panelEl?.getBoundingClientRect();
    const p = computePopoverPosition(
      { left: t.left, top: t.top, right: t.right, bottom: t.bottom, width: t.width, height: t.height },
      { width: rect?.width ?? cap, height: rect?.height ?? 0 },
      viewport,
    );
    setPos({ left: p.left, top: p.top });
  }, [maxWidth, readViewport]);

  // Two-pass placement: first pass (pos null → hidden) sets the cap and measures; the resulting
  // state change re-renders and this effect runs again with the real measured rect, producing the
  // final clamp before the panel is revealed.
  useLayoutEffect(() => {
    if (open) place();
    else {
      setPos(null);
    }
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const reposition = () => place();
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    const vv = window.visualViewport;
    vv?.addEventListener("resize", reposition);
    vv?.addEventListener("scroll", reposition);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPinned(false);
        setHovered(false);
        setFocused(false);
        triggerRef.current?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (!wrapRef.current?.contains(target) && !panelRef.current?.contains(target)) {
        setPinned(false);
        setHovered(false);
        setFocused(false);
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
      vv?.removeEventListener("resize", reposition);
      vv?.removeEventListener("scroll", reposition);
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, place]);

  const handleBlur = useCallback((e: React.FocusEvent<HTMLSpanElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setFocused(false);
      setPinned(false);
    }
  }, []);

  return (
    <span
      ref={wrapRef}
      className="relative inline-flex items-center"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={handleBlur}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-controls={id}
        aria-label={label}
        onClick={() => setPinned((v) => !v)}
        className={`focus-ring inline-flex items-center gap-1 text-left ${triggerClassName}`}
      >
        {trigger}
      </button>

      {open &&
        mounted &&
        createPortal(
          <div
            ref={panelRef}
            id={id}
            role="tooltip"
            style={{
              position: "fixed",
              left: pos?.left ?? -9999,
              top: pos?.top ?? -9999,
              // min(22rem, 100dvw - 24px): capped before measurement so reveal width == measured width.
              maxWidth: maxWidth ?? `min(22rem, calc(100dvw - ${2 * POPOVER_MARGIN}px))`,
              // Hidden until placed, so it never flashes at the wrong spot or expands layout.
              visibility: pos ? "visible" : "hidden",
            }}
            className={`z-[100] w-max whitespace-normal break-words [overflow-wrap:anywhere] rounded-[10px] border border-arepo-border bg-arepo-surface p-3 text-left shadow-[0_6px_20px_rgba(16,16,16,0.12)] ${panelClassName}`}
          >
            {children}
          </div>,
          document.body,
        )}
    </span>
  );
}
