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
import { POPOVER_MAX_WIDTH, computePopoverPosition } from "@/lib/popover-position";

/**
 * Viewport-aware information popover primitive (final pre-deployment §6).
 *
 * The panel is rendered through a portal to <body> with `position: fixed`, so it is never clipped
 * by a card's overflow or a sticky container, and it can never expand the document width or create
 * horizontal scrolling: its left/top are clamped to the viewport with a safe margin, and its width
 * is capped to the viewport. It flips above the trigger when there is no room below, shifts
 * horizontally near either edge, and repositions on open, scroll and resize. Because it uses layout
 * coordinates (getBoundingClientRect, CSS pixels), it stays correct under browser zoom.
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
  const [pos, setPos] = useState<{ left: number; top: number; maxWidth: number } | null>(null);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const open = pinned || hovered || focused;

  useEffect(() => setMounted(true), []);

  const place = useCallback(() => {
    const t = triggerRef.current?.getBoundingClientRect();
    if (!t) return;
    const p = computePopoverPosition(
      t,
      {
        width: panelRef.current?.offsetWidth ?? POPOVER_MAX_WIDTH,
        height: panelRef.current?.offsetHeight ?? 0,
      },
      { width: document.documentElement.clientWidth, height: window.innerHeight },
    );
    setPos({ left: p.left, top: p.top, maxWidth: p.maxWidth });
  }, []);

  // Position after the panel has mounted (so we can measure it), and on every open.
  useLayoutEffect(() => {
    if (open) place();
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const reposition = () => place();
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
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
              maxWidth: pos?.maxWidth ?? POPOVER_MAX_WIDTH,
              // Hidden until placed, so it never flashes at the wrong spot or expands layout.
              visibility: pos ? "visible" : "hidden",
            }}
            className={`z-[100] w-max rounded-[10px] border border-arepo-border bg-arepo-surface p-3 text-left shadow-[0_6px_20px_rgba(16,16,16,0.12)] ${panelClassName}`}
          >
            {children}
          </div>,
          document.body,
        )}
    </span>
  );
}
