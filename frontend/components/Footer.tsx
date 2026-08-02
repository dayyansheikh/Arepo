"use client";

import { useAsync } from "@/lib/use-async";
import { getMeta } from "@/lib/api";

export function Footer() {
  const { data, error } = useAsync(() => getMeta(), []);

  return (
    <footer className="border-t border-astro-light-border dark:border-astro-border mt-16">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 text-xs text-muted-fg space-y-2">
        <p>
          Astrolabe is a read-only research instrument over public Polymarket
          data. It does not place trades, offer financial advice, or prove
          insider activity — it surfaces statistical anomalies for further
          reading.
        </p>
        <p>
          {data?.disclaimer ??
            (error
              ? "Disclaimer unavailable — could not reach the Astrolabe API."
              : "Loading disclaimer…")}
        </p>
      </div>
    </footer>
  );
}
