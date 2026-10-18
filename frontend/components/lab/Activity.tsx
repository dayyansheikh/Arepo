"use client";

import { useId } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { agoLabel, outcomeTone, shortDate } from "@/lib/lab/model";
import { LiveProgress } from "./Candidates";
import type { HostPayload, LiveTest, QueueJob } from "@/lib/lab/types";
import { theme } from "@/lib/theme";
import { Card, Dot, fmtCount, Quiet, TONE_COLOR } from "./primitives";

function TestsChart({ data }: { data: Array<{ date: string; cumulative: number }> }) {
  const gid = useId().replace(/[:]/g, "");
  const rows = data
    .filter((d) => d && typeof d.cumulative === "number" && !Number.isNaN(Date.parse(d.date)))
    .map((d) => ({ t: Date.parse(d.date.length === 10 ? `${d.date}T00:00:00Z` : d.date), v: d.cumulative }))
    .sort((a, b) => a.t - b.t);
  if (rows.length < 2) return <Quiet>Not enough history to draw yet.</Quiet>;
  const first = rows[0];
  const last = rows[rows.length - 1];
  const fmtDay = (t: number) => new Date(t).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  return (
    <figure className="m-0">
      <div
        className="h-56 w-full"
        role="img"
        aria-label={`Tests run over time: from ${fmtCount(first.v)} on ${fmtDay(first.t)} to ${fmtCount(last.v)} on ${fmtDay(last.t)}.`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={theme.accent} stopOpacity={0.18} />
                <stop offset="100%" stopColor={theme.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={fmtDay}
              tick={{ fontSize: 11, fill: theme.muted }}
              tickLine={false}
              axisLine={{ stroke: theme.border }}
              minTickGap={48}
            />
            <YAxis
              tick={{ fontSize: 11, fill: theme.muted }}
              tickLine={false}
              axisLine={false}
              width={44}
              tickFormatter={(v: number) => fmtCount(v)}
              domain={["auto", "auto"]}
            />
            <Tooltip
              formatter={(v: number) => [fmtCount(v), "Tests run"]}
              labelFormatter={(t: number) => fmtDay(t)}
              cursor={{ stroke: theme.borderStrong, strokeDasharray: "3 3" }}
              contentStyle={{
                background: theme.surface,
                border: `1px solid ${theme.border}`,
                borderRadius: 10,
                fontSize: 12,
                boxShadow: "0 6px 20px rgba(16,16,16,0.10)",
                color: theme.ink,
              }}
              itemStyle={{ fontVariantNumeric: "tabular-nums", color: theme.ink }}
            />
            <Area
              type="monotone"
              dataKey="v"
              name="Tests run"
              stroke={theme.accent}
              strokeWidth={2}
              fill={`url(#${gid})`}
              dot={false}
              activeDot={{ r: 4.5, fill: theme.accent, stroke: theme.surface, strokeWidth: 2 }}
              animationDuration={900}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

const OUTCOME_WORD: Record<string, string> = { pos: "done", warn: "retried", neg: "errors", muted: "other" };

function JobStrip({ recent }: { recent: QueueJob[] }) {
  const jobs = [...recent]
    .filter((j) => j && j.at)
    .sort((a, b) => Date.parse(a.at ?? "") - Date.parse(b.at ?? ""))
    .slice(-40);
  if (!jobs.length) return <Quiet>No finished jobs reported yet.</Quiet>;
  const tally = new Map<string, number>();
  for (const j of jobs) {
    const t = outcomeTone(j.outcome);
    const k = t === "pos" || t === "warn" || t === "neg" ? t : "muted";
    tally.set(k, (tally.get(k) ?? 0) + Math.max(1, j.repeats ?? 1));
  }
  return (
    <div>
      <ol className="flex h-9 items-stretch gap-[3px]" aria-label="Recent jobs, oldest to newest">
        {jobs.map((j, i) => {
          const tone = outcomeTone(j.outcome);
          const mins = typeof j.runtime_s === "number" ? Math.round(j.runtime_s / 60) : null;
          const reps = Math.max(1, Math.floor(j.repeats ?? 1));
          const label = `${j.title ?? j.id ?? "Job"}: ${j.outcome ?? "unknown"}${reps > 1 ? ` ×${reps}` : ""}${mins != null ? `, ${mins} min` : ""}, ${shortDate(j.at)}`;
          return (
            <li
              key={`${j.id}-${i}`}
              className="flex min-w-[3px] items-center justify-center overflow-hidden rounded-[3px] transition-transform hover:scale-y-110"
              style={{ background: TONE_COLOR[tone], opacity: tone === "pos" ? 0.75 : 1, flex: `${Math.min(reps, 4)} 1 0` }}
              title={label}
              aria-label={label}
            >
              {reps > 1 ? (
                <span aria-hidden="true" className="font-tabular text-[10px] font-semibold text-white">
                  ×{reps}
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[12px] text-arepo-muted">
        <span>Older</span>
        <span className="flex flex-wrap gap-x-3">
          {(["pos", "warn", "neg", "muted"] as const)
            .filter((k) => tally.get(k))
            .map((k) => (
              <span key={k} className="inline-flex items-center gap-1.5">
                <span aria-hidden="true" className="h-2 w-2 rounded-[2px]" style={{ background: TONE_COLOR[k] }} />
                {tally.get(k)} {OUTCOME_WORD[k]}
              </span>
            ))}
        </span>
        <span>Newest</span>
      </div>
    </div>
  );
}

function LiveTests({ tests, nowMs }: { tests: LiveTest[]; nowMs: number }) {
  if (!tests.length) return <Quiet>No live tests running.</Quiet>;
  return (
    <ul className="space-y-5">
      {tests.map((t) => (
        <li key={t.id}>
          <p className="mb-1 text-[13px] font-medium text-arepo-ink">
            {t.title ?? t.id} <span className="font-mono text-[11px] font-normal text-arepo-muted">{t.id}</span>
          </p>
          <LiveProgress live={t} nowMs={nowMs} />
        </li>
      ))}
    </ul>
  );
}

export function Activity({ host, nowMs }: { host: HostPayload; nowMs: number }) {
  const running = host.queue?.running ?? [];
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
      <Card className="lg:col-span-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-[15px] font-semibold text-arepo-ink">Tests run</h3>
          <span className="font-display font-tabular text-[22px] font-semibold text-arepo-ink">
            {fmtCount(host.headline?.tests_run ?? host.tests_over_time?.slice(-1)[0]?.cumulative)}
          </span>
        </div>
        <p className="mb-3 text-[12.5px] text-arepo-muted">Cumulative statistical tests, every one counted.</p>
        <TestsChart data={host.tests_over_time ?? []} />
      </Card>
      <Card className="lg:col-span-2">
        <h3 className="text-[15px] font-semibold text-arepo-ink">Live tests</h3>
        <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">
          Collection counts only. Results stay sealed until each registered analysis date.
        </p>
        <LiveTests tests={host.live_tests ?? []} nowMs={nowMs} />
      </Card>
      <Card className="lg:col-span-5">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_18rem]">
          <div>
            <h3 className="text-[15px] font-semibold text-arepo-ink">Recent jobs</h3>
            <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">Each bar is one finished job on the research host.</p>
            <JobStrip recent={host.queue?.recent ?? []} />
          </div>
          <div className="md:border-l md:border-arepo-border md:pl-6">
            <h3 className="text-[13px] font-semibold uppercase tracking-wider text-arepo-muted">Running now</h3>
            {running.length ? (
              <ul className="mt-3 space-y-2.5">
                {running.map((j, i) => {
                  const started = j.started_at ? Date.parse(j.started_at) : NaN;
                  return (
                    <li key={`${j.id}-${i}`} className="flex items-start gap-2.5 text-[13px]">
                      <span className="mt-[6px]">
                        <Dot tone="pos" pulse />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-arepo-ink">{j.title ?? j.id}</span>
                        <span className="text-[12px] text-arepo-muted">
                          {Number.isNaN(started) ? "running" : `for ${agoLabel((nowMs - started) / 1000).replace(" ago", "")}`}
                          {j.lane ? ` · ${j.lane}` : ""}
                        </span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mt-3 text-[13px] text-arepo-muted">Nothing running.</p>
            )}
            {host.queue?.upcoming?.length ? (
              <>
                <h3 className="mt-5 text-[13px] font-semibold uppercase tracking-wider text-arepo-muted">Up next</h3>
                <ul className="mt-2 space-y-1.5">
                  {host.queue.upcoming.slice(0, 4).map((j, i) => (
                    <li key={`${j.id}-${i}`} className="flex items-baseline justify-between gap-2 text-[12.5px]">
                      <span className="min-w-0 truncate text-arepo-ink2">{j.title ?? j.id}</span>
                      <span className="flex-none text-[11.5px] text-arepo-muted">{(j.status ?? "").replace(/_/g, " ")}</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        </div>
      </Card>
    </div>
  );
}
