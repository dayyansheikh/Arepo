"use client";

import { useMode } from "@/lib/mode-context";
import { useStatus } from "@/lib/use-status";

export function DegradationBanner() {
  const { mode } = useMode();
  const { status } = useStatus(mode);

  if (!status?.degradation_reason) return null;

  return (
    <div
      role="status"
      className="border-b border-astro-brass/30 bg-astro-brass/10 px-4 py-2 text-center text-sm text-astro-brass"
    >
      {status.degradation_reason}
    </div>
  );
}
