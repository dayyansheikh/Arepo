"use client";

import { useMode } from "@/lib/mode-context";
import { useAsync } from "@/lib/use-async";
import { getSignals } from "@/lib/api";
import { SignalItem } from "@/components/SignalItem";
import { ListSkeleton } from "@/components/Skeletons";
import { ErrorState, EmptyState } from "@/components/ErrorState";

export default function SignalLabPage() {
  const { mode } = useMode();
  const { data, loading, error } = useAsync(() => getSignals(mode, 50), [mode]);

  const sorted = data ? [...data.signals].sort((a, b) => b.strength - a.strength) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Signal Lab</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-fg">
          Composite anomaly signals rank markets by how unusual their recent order-book and
          price behavior is relative to their own history. These are screening heuristics for
          further reading — not proof of insider activity, and not a recommendation to trade.
        </p>
      </div>

      {loading && <ListSkeleton rows={8} />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && data && sorted.length === 0 && (
        <EmptyState message="No signals available in this mode right now." />
      )}
      {!loading && sorted.length > 0 && (
        <div className="space-y-3">
          {sorted.map((s, i) => (
            <SignalItem key={`${s.kind}-${s.token_id}-${i}`} signal={s} />
          ))}
        </div>
      )}
    </div>
  );
}
