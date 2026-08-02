"use client";

import { useMode } from "@/lib/mode-context";
import type { DataMode } from "@/lib/types";

const MODES: { value: DataMode; label: string }[] = [
  { value: "live", label: "Live" },
  { value: "cached", label: "Cached" },
  { value: "replay", label: "Replay" },
];

export function ModeSwitcher() {
  const { mode, setMode } = useMode();

  return (
    <div
      role="radiogroup"
      aria-label="Data mode"
      className="inline-flex items-center rounded-instrument border border-astro-light-border dark:border-astro-border overflow-hidden"
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
            className={`focus-ring px-3 py-1.5 text-xs font-medium transition-colors ${
              active
                ? "bg-astro-brass text-[#141A24]"
                : "text-muted-fg hover:text-astro-light-text dark:hover:text-astro-text"
            }`}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
