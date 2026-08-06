"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import { useMode } from "@/lib/mode-context";
import type { DataMode } from "@/lib/types";

const MODES: { value: DataMode; label: string; blurb: string }[] = [
  {
    value: "live",
    label: "Live",
    blurb: "Current public Polymarket data, fetched now.",
  },
  {
    value: "cached",
    label: "Cached",
    blurb: "The latest market data Arepo has successfully stored.",
  },
  {
    value: "replay",
    label: "Replay",
    blurb: "A fixed, deterministic demonstration dataset.",
  },
];

/**
 * Data-mode control. A labelled segmented control (Live / Cached / Replay) plus
 * an info popover that explains each mode in plain English and links to the
 * fuller explanation. Source health and data age sit alongside in StatusChip.
 */
export function ModeSwitcher() {
  const { mode, setMode } = useMode();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleBlur = useCallback((e: React.FocusEvent<HTMLDivElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setOpen(false);
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative flex items-center gap-1.5"
      onBlur={handleBlur}
      onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
    >
      <div
        role="radiogroup"
        aria-label="Data mode"
        className="inline-flex items-center rounded-control border border-arepo-border bg-arepo-surface p-0.5"
      >
        {MODES.map((m) => {
          const active = m.value === mode;
          return (
            <button
              key={m.value}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setMode(m.value)}
              className={`focus-ring rounded-[7px] px-3 py-1 text-xs font-semibold transition-colors ${
                active
                  ? "bg-arepo-accent text-arepo-accentFg"
                  : "text-arepo-muted hover:text-arepo-ink"
              }`}
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        aria-expanded={open}
        aria-label="About data modes"
        onClick={() => setOpen((v) => !v)}
        className="focus-ring inline-flex h-5 w-5 items-center justify-center rounded-full border border-arepo-muted/60 text-[10px] font-semibold text-arepo-muted hover:text-arepo-ink"
      >
        i
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Data modes explained"
          className="absolute right-0 top-full z-50 mt-2 w-80 max-w-[calc(100vw-1.5rem)] rounded-card border border-arepo-border bg-arepo-surface p-4 shadow-[0_6px_20px_rgba(16,16,16,0.10)]"
        >
          <p className="text-sm font-semibold text-arepo-ink">Data modes</p>
          <ul className="mt-2 space-y-2">
            {MODES.map((m) => (
              <li key={m.value} className="text-[13px] leading-relaxed">
                <span className="font-semibold text-arepo-ink">{m.label}.</span>{" "}
                <span className="text-arepo-muted">{m.blurb}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[13px] leading-relaxed text-arepo-muted">
            The mode you are viewing is always shown here and travels with every
            reading, so cached or replay data is never presented as live.
          </p>
          <Link
            href="/how-it-works#data-modes"
            className="focus-ring mt-2 inline-block text-[13px] font-medium text-arepo-accentActive hover:text-arepo-accentHover"
            onClick={() => setOpen(false)}
          >
            Learn more &rarr;
          </Link>
        </div>
      )}
    </div>
  );
}
