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
      className="flex items-center justify-center gap-2 border-b border-arepo-warn/30 bg-arepo-warn/10 px-4 py-2 text-center text-sm font-medium text-arepo-warnText"
    >
      <svg aria-hidden="true" viewBox="0 0 20 20" className="h-4 w-4 flex-none" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M8.485 3.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.515 2.625H3.72c-1.344 0-2.187-1.458-1.515-2.625L8.485 3.495zM10 6.75a.75.75 0 01.75.75v3a.75.75 0 01-1.5 0v-3A.75.75 0 0110 6.75zm0 7a.9.9 0 100-1.8.9.9 0 000 1.8z"
          clipRule="evenodd"
        />
      </svg>
      {status.degradation_reason}
    </div>
  );
}
