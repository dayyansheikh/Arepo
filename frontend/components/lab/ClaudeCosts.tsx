"use client";

import { useState } from "react";
import { costDays, sourceLabel, usdLabel } from "@/lib/lab/claude";
import type { CostsBlock } from "@/lib/lab/types";
import { theme } from "@/lib/theme";
import { Card, fmtCount, Quiet } from "./primitives";

const DAYS = 30;

function dayLabel(date: string): string {
  const t = Date.parse(`${date}T12:00:00Z`);
  return Number.isNaN(t) ? date : new Date(t).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

/** Daily API-equivalent spend, last 30 days: one series, thin bars anchored to the baseline. */
function DailyBars({ costs, nowMs }: { costs: CostsBlock; nowMs: number }) {
  const days = costDays(costs, nowMs, DAYS);
  const max = Math.max(1, ...days.map((d) => d.usd));
  const [hover, setHover] = useState<number | null>(null);
  const shown = hover != null ? days[hover] : null;
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3 text-[12px] text-arepo-muted">
        <span>Per day, last {DAYS} days (UTC)</span>
        <span className="font-tabular text-arepo-ink2" aria-live="polite">
          {shown ? `${dayLabel(shown.date)}: ${usdLabel(shown.usd)}` : `Peak ${usdLabel(max)}`}
        </span>
      </div>
      <ol className="flex h-28 items-end gap-[2px]" aria-label={`API-equivalent spend per day over the last ${DAYS} days`} onMouseLeave={() => setHover(null)}>
        {days.map((d, i) => {
          const h = d.usd > 0 ? Math.max(3, (d.usd / max) * 100) : 0;
          const today = i === days.length - 1;
          const label = `${dayLabel(d.date)}: ${usdLabel(d.usd)}`;
          return (
            <li key={d.date} className="flex h-full min-w-0 flex-1 items-end" onMouseEnter={() => setHover(i)} title={label}>
              <span className="sr-only">{label}</span>
              <span
                aria-hidden="true"
                className="block w-full rounded-t-[4px] transition-opacity"
                style={{
                  height: `${h}%`,
                  background: today ? theme.ink2 : theme.series2,
                  opacity: hover == null || hover === i ? 1 : 0.45,
                }}
              />
            </li>
          );
        })}
      </ol>
      <div className="mt-1 flex justify-between border-t border-arepo-border pt-1 text-[11px] text-arepo-muted" aria-hidden="true">
        <span>{dayLabel(days[0].date)}</span>
        <span>today</span>
      </div>
    </div>
  );
}

function Breakdown({ title, rows, total }: { title: string; rows: Array<{ key: string; label: string; usd: number; note?: string }>; total: number }) {
  return (
    <div>
      <h4 className="text-[12px] font-semibold uppercase tracking-wider text-arepo-muted">{title}</h4>
      <ul className="mt-2 space-y-2.5">
        {rows.map((r) => {
          const pct = total > 0 ? Math.max(0.5, (r.usd / total) * 100) : 0;
          return (
            <li key={r.key}>
              <div className="flex items-baseline justify-between gap-3 text-[13px]">
                <span className="min-w-0 truncate text-arepo-ink">{r.label}</span>
                <span className="font-tabular text-arepo-ink2">{usdLabel(r.usd)}</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-arepo-surface2" aria-hidden="true">
                <div className="h-full rounded-full" style={{ width: `${pct}%`, background: theme.series2 }} />
              </div>
              {r.note ? <p className="mt-0.5 text-[11.5px] text-arepo-muted">{r.note}</p> : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ClaudeCosts({ costs, nowMs }: { costs: CostsBlock | null | undefined; nowMs: number }) {
  if (!costs || costs.error || typeof costs.total_usd !== "number") {
    return (
      <Quiet>
        {costs?.error
          ? `The Mac could not compute the project cost this time (${costs.error}).`
          : "No cost figures yet: the Mac adds them once its client is updated."}
      </Quiet>
    );
  }
  const total = costs.total_usd;
  const since = costs.first_at ? new Date(costs.first_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : null;
  const models = (costs.by_model ?? []).map((m) => ({ key: m.model, label: m.label ?? m.model, usd: m.usd }));
  const sources = (costs.by_source ?? []).map((s) => ({
    key: s.key,
    label: sourceLabel(s),
    usd: s.usd,
    note:
      typeof s.subagent_usd === "number" && s.subagent_usd > 0
        ? `${usdLabel(s.main_usd)} main sessions · ${usdLabel(s.subagent_usd)} subagents${typeof s.sessions === "number" ? ` · ${fmtCount(s.sessions)} sessions` : ""}`
        : undefined,
  }));
  const unknown = costs.unknown_models ?? [];
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="col-span-2 sm:col-span-1">
            <dt className="text-[12px] text-arepo-muted">Whole project</dt>
            <dd className="whitespace-nowrap font-display font-tabular text-[30px] font-semibold leading-tight text-arepo-ink sm:text-[36px]">{usdLabel(total)}</dd>
            {since ? <dd className="text-[11.5px] text-arepo-muted">since {since}</dd> : null}
          </div>
          <div>
            <dt className="text-[12px] text-arepo-muted">Last 7 days</dt>
            <dd className="font-display font-tabular text-[22px] font-semibold leading-tight text-arepo-ink sm:text-[26px]">{usdLabel(costs.last_7d_usd)}</dd>
          </div>
          <div>
            <dt className="text-[12px] text-arepo-muted">Today (UTC)</dt>
            <dd className="font-display font-tabular text-[22px] font-semibold leading-tight text-arepo-ink sm:text-[26px]">{usdLabel(costs.today_usd)}</dd>
          </div>
        </dl>
        <p className="mt-3 rounded-control bg-arepo-surface2 px-3 py-2 text-[12.5px] leading-relaxed text-arepo-ink2">
          <strong className="font-semibold text-arepo-ink">API-equivalent; you pay a flat subscription.</strong> What these Claude Code tokens
          would cost at Anthropic&apos;s published API prices, from every session transcript on the Mac (interactive, autopilot and subagents), each
          message counted once.
        </p>
        <div className="mt-5">
          <DailyBars costs={costs} nowMs={nowMs} />
        </div>
      </Card>
      <Card>
        <div className="space-y-6">
          {sources.length ? <Breakdown title="Who spent it" rows={sources} total={total} /> : null}
          {models.length ? <Breakdown title="By model" rows={models} total={total} /> : null}
          {unknown.length ? (
            <p className="text-[12px] text-arepo-warnText">
              Not priced (model missing from the price table): {unknown.map((u) => `${u.model} (${fmtCount(u.messages)} messages)`).join(", ")}.
            </p>
          ) : null}
          <div>
            <h4 className="text-[12px] font-semibold uppercase tracking-wider text-arepo-muted">Infrastructure</h4>
            <p className="mt-1 font-display font-tabular text-[20px] font-semibold text-arepo-ink">£0 a month</p>
            <ul className="mt-1 space-y-0.5 text-[12px] text-arepo-ink2">
              {(costs.infra ?? []).map((i) => (
                <li key={i.name} className="flex justify-between gap-3">
                  <span className="min-w-0 truncate">{i.name}</span>
                  <span className="whitespace-nowrap text-arepo-muted">£{i.gbp_month ?? 0} · {i.note}</span>
                </li>
              ))}
            </ul>
          </div>
          {costs.pricing_source ? (
            <p className="text-[11.5px] leading-relaxed text-arepo-muted">
              Prices: {costs.pricing_source.replace(/^https?:\/\//, "")}.{costs.assumptions?.length ? ` ${costs.assumptions.join(" ")}` : ""}
            </p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
