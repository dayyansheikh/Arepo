"use client";

import type { ReactNode } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  attributionViews,
  developmentRows,
  embargoLabel,
  engineStatus,
  familyOf,
  familySeries,
  fmtDaysPositive,
  fmtFixed,
  fmtGain,
  fmtPct,
  fmtSigned,
  fmtUtc,
  parseSignalEngine,
  promotions,
  prospectiveRows,
  SE_WINDOW_DAYS,
  type AttributionView,
  type GainSeries,
  type SeCells,
} from "@/lib/lab/signal-engine";
import { seriesColors, theme } from "@/lib/theme";
import { Card, fmtCount, Pill, Quiet } from "./primitives";

const COLS = [
  "Model",
  "Target",
  "Rows",
  "Log loss",
  "Brier",
  "Cal. slope",
  "Cal. intercept",
  "AUC",
  "Coverage",
  "Gain vs champion (nats, 95% CI)",
  "Days positive",
];

function ScoreTable({ rows, families, caption }: { rows: SeCells[]; families: Map<string, string>; caption: string }) {
  if (!rows.length) return <Quiet>No rows yet.</Quiet>;
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full min-w-[56rem] border-collapse text-[12.5px]">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-arepo-border text-left text-[11.5px] font-semibold text-arepo-muted">
            {COLS.map((c, i) => (
              <th key={c} scope="col" className={`whitespace-nowrap px-2 py-2 font-semibold ${i >= 2 ? "text-right" : ""}`}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-tabular">
          {rows.map((r, i) => {
            const fam = families.get(r.modelId);
            const model = (
              <th scope="row" className="px-2 py-2 text-left font-normal">
                <span className="block font-medium text-arepo-ink">{r.modelId}</span>
                {fam ? <span className="block text-[11.5px] text-arepo-muted">{fam}</span> : null}
              </th>
            );
            if (r.kind === "embargoed") {
              return (
                <tr key={`${r.modelId}-e-${i}`} className="border-b border-arepo-border/70" data-testid="se-embargoed-row">
                  {model}
                  <td colSpan={COLS.length - 1} className="px-2 py-2 text-arepo-muted">
                    <Pill tone="muted">{embargoLabel(r.until)}</Pill>
                  </td>
                </tr>
              );
            }
            const champ = r.role === "champion";
            return (
              <tr key={`${r.modelId}-${r.target}-${i}`} className="border-b border-arepo-border/70 text-arepo-ink2">
                {model}
                <td className="whitespace-nowrap px-2 py-2">
                  {r.target || "–"}
                  {champ ? <span className="ml-1.5 text-[11px] font-semibold text-arepo-accentActive">champion</span> : null}
                </td>
                <td className="px-2 py-2 text-right">{fmtCount(r.n)}</td>
                <td className="px-2 py-2 text-right">{fmtFixed(r.logLoss, 4)}</td>
                <td className="px-2 py-2 text-right">{fmtFixed(r.brier, 4)}</td>
                <td className="px-2 py-2 text-right">{fmtFixed(r.calSlope, 2)}</td>
                <td className="px-2 py-2 text-right">{fmtSigned(r.calIntercept, 2)}</td>
                <td className="px-2 py-2 text-right">{fmtFixed(r.auc, 3)}</td>
                <td className="px-2 py-2 text-right">{fmtPct(r.coverage)}</td>
                <td className="whitespace-nowrap px-2 py-2 text-right">{fmtGain(r.gain, r.gainLo, r.gainHi)}</td>
                <td className="px-2 py-2 text-right">{fmtDaysPositive(r.daysPositive, r.nDays)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function GainsChart({ series }: { series: GainSeries[] }) {
  const dates = Array.from(new Set(series.flatMap((s) => s.points.map((p) => p.date)))).sort();
  if (dates.length < 2) return <Quiet>Not enough daily scores to draw gains over time yet.</Quiet>;
  const data = dates.map((date) => {
    const row: Record<string, unknown> = { date };
    series.forEach((s, i) => {
      const p = s.points.find((x) => x.date === date);
      if (!p) return;
      row[`g${i}`] = p.gain;
      if (p.lo !== null && p.hi !== null) row[`r${i}`] = [p.lo, p.hi];
    });
    return row;
  });
  const colour = (i: number) => seriesColors[(i + 1) % seriesColors.length] ?? theme.series2;
  const fmtDay = (d: string) => new Date(`${d}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  return (
    <figure className="m-0">
      <figcaption className="sr-only">
        {SE_WINDOW_DAYS}-day gain over the champion by challenger family, latest:{" "}
        {series.map((s) => `${s.label} ${fmtSigned(s.points[s.points.length - 1]?.gain)}`).join(", ")}.
      </figcaption>
      <div className="h-56 w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis dataKey="date" tickFormatter={fmtDay} tick={{ fontSize: 11, fill: theme.muted }} tickLine={false} axisLine={{ stroke: theme.border }} minTickGap={32} />
            <YAxis tick={{ fontSize: 11, fill: theme.muted }} tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => fmtSigned(v, 3)} />
            <Tooltip
              labelFormatter={(d: string) => fmtDay(d)}
              formatter={(v: unknown, name: string) => [Array.isArray(v) ? `[${fmtSigned(v[0])}, ${fmtSigned(v[1])}]` : fmtSigned(v as number), name]}
              contentStyle={{ background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 10, fontSize: 12, color: theme.ink }}
            />
            {series.map((s, i) => (
              <Area key={`r${i}`} dataKey={`r${i}`} name={`${s.label} CI`} stroke="none" fill={colour(i)} fillOpacity={0.12} isAnimationActive={false} connectNulls />
            ))}
            {series.map((s, i) => (
              <Line key={`g${i}`} dataKey={`g${i}`} name={s.label} stroke={colour(i)} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {series.map((s, i) => (
          <span key={s.key} className="inline-flex items-center gap-1.5 text-[12px] text-arepo-ink2">
            <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ background: colour(i) }} />
            {s.label}
          </span>
        ))}
      </div>
      <p className="mt-2 text-[12px] text-arepo-muted">
        Primary target, {SE_WINDOW_DAYS}-day window. Line: mean log-loss gain over the champion; band: 95% interval. Above
        zero means better forecast quality than the champion, not profit.
      </p>
    </figure>
  );
}

function Attribution({ views }: { views: AttributionView[] }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2" data-testid="se-attribution">
      {views.map((v) => (
        <div key={v.modelId} className="min-w-0">
          <p className="text-[13.5px] font-medium text-arepo-ink">{v.modelId}</p>
          <p className="mb-3 text-[12px] text-arepo-muted">
            {v.target || "–"}
            {v.fitTime ? <> · fit {fmtUtc(v.fitTime)}</> : null}
            {v.rows !== null ? <> · {fmtCount(v.rows)} rows</> : null}
          </p>
          {v.families.length ? (
            <ul className="space-y-1.5">
              {v.families.map((f) => (
                <li key={f.family} className="grid grid-cols-[minmax(0,8rem)_1fr_3rem] items-center gap-2 text-[12.5px]">
                  <span className="truncate text-arepo-ink2">{f.family}</span>
                  <span aria-hidden="true" className="h-2 rounded-full bg-arepo-border/60">
                    <span className="block h-2 rounded-full bg-arepo-ink2/70" style={{ width: `${Math.max(1, Math.round(f.share * 100))}%` }} />
                  </span>
                  <span className="font-tabular text-right text-arepo-ink2">{fmtPct(f.share)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Quiet>No visible families.</Quiet>
          )}
          {v.hidden.length ? (
            <p className="mt-2 text-[12px] text-arepo-muted" data-testid="se-attribution-hidden">
              Hidden while under a live test: {v.hidden.join(", ")}
            </p>
          ) : null}
          <p className="mt-2 text-[11.5px] text-arepo-muted">{v.label}</p>
        </div>
      ))}
    </div>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[12px] text-arepo-muted">{label}</dt>
      <dd className="mt-0.5 break-words text-[13.5px] text-arepo-ink">{children}</dd>
    </div>
  );
}

export function SignalEngine({ block, nowMs }: { block: unknown; nowMs: number }) {
  const se = parseSignalEngine(block);
  if (!se) return <Quiet>The latest snapshot has no signal-engine block.</Quiet>;
  const status = engineStatus(se, nowMs);
  const families = familyOf(se);
  const prospective = prospectiveRows(se, nowMs);
  const scored = prospective.some((r) => r.kind === "scored");
  const dev = developmentRows(se, nowMs);
  const series = familySeries(se, nowMs);
  const attribution = attributionViews(se, nowMs);
  const promos = promotions(se);
  const days = typeof se.prospective?.days_scored === "number" ? se.prospective.days_scored : 0;
  const champ = se.champion?.model_id;
  return (
    <div className="grid grid-cols-1 gap-4" data-testid="signal-engine">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={status === "scoring" ? "pos" : "neutral"}>{status === "scoring" ? "Scoring" : "Bootstrapping"}</Pill>
          {se.stale ? <Pill tone="warn">Stale: engine report over 2 days old</Pill> : null}
        </div>
        <dl className="mt-4 grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          <Fact label="Champion">
            {champ ?? "–"}
            {se.champion?.family ? <span className="block text-[12px] text-arepo-muted">{se.champion.family}</span> : null}
          </Fact>
          <Fact label="Days scored">
            {fmtCount(days)}
            <span className="block text-[12px] text-arepo-muted">promotion needs at least {SE_WINDOW_DAYS}</span>
          </Fact>
          <Fact label="Engine report">
            {fmtUtc(se.generated_at)}
            {se.engine_version ? <span className="block text-[12px] text-arepo-muted">{se.engine_version}</span> : null}
          </Fact>
          <Fact label="Last refit">
            {fmtUtc(se.last_refit?.at)}
            {typeof se.last_refit?.models === "number" ? (
              <span className="block text-[12px] text-arepo-muted">{fmtCount(se.last_refit.models)} models</span>
            ) : null}
          </Fact>
          <Fact label="Last prediction">
            {fmtUtc(se.last_prediction?.at)}
            {se.last_prediction?.capture_id ? (
              <span className="block break-all text-[12px] text-arepo-muted">capture {se.last_prediction.capture_id}</span>
            ) : null}
          </Fact>
        </dl>
        <p className="mt-4 text-[12px] leading-relaxed text-arepo-muted">
          {se.note ?? "Signal strength / forecast quality only; not probability of profit, not an edge claim."}
        </p>
      </Card>

      <Card>
        <h3 className="text-[15px] font-semibold text-arepo-ink">Prospective leaderboard</h3>
        <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">
          Last {SE_WINDOW_DAYS} days of predictions made before outcomes were known. Sorted by target, then gain.
        </p>
        {status === "bootstrapping" ? (
          <div data-testid="se-bootstrapping" className="mb-4 rounded-control border border-arepo-border bg-arepo-surface2/60 px-4 py-3">
            <p className="text-[13px] leading-relaxed text-arepo-ink2">
              <span className="font-semibold text-arepo-ink">Bootstrapping.</span> Every model is writing a prediction for
              each new market capture now, before the outcome is known. A prediction can only be scored once its outcome
              arrives, so scores build up over the coming days. A challenger can replace the champion only after at least{" "}
              {SE_WINDOW_DAYS} days of prospective scores. Days scored so far: {fmtCount(days)}.
            </p>
            {scored ? (
              <p className="mt-1.5 text-[12px] text-arepo-muted">Early scores below are too few days to judge.</p>
            ) : null}
          </div>
        ) : null}
        {scored ? (
          <ScoreTable rows={prospective} families={families} caption="Prospective leaderboard, 14-day window" />
        ) : prospective.length ? (
          <ul className="flex flex-wrap gap-x-4 gap-y-2" data-testid="se-embargo-list">
            {prospective.map((r) => (
              <li key={r.modelId} className="text-[12px] text-arepo-ink2">
                <span className="font-medium">{r.modelId}</span>
                {families.get(r.modelId) ? <span className="text-arepo-muted"> · {families.get(r.modelId)}</span> : null}{" "}
                {r.kind === "embargoed" ? <Pill tone="muted">{embargoLabel(r.until)}</Pill> : null}
              </li>
            ))}
          </ul>
        ) : (
          <Quiet>No prospective rows yet.</Quiet>
        )}
      </Card>

      <Card>
        <h3 className="text-[15px] font-semibold text-arepo-ink">Family gains over time</h3>
        <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">How each challenger family compares with the champion, day by day.</p>
        {series.length ? <GainsChart series={series} /> : <Quiet>No daily gains yet.</Quiet>}
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[15px] font-semibold text-arepo-ink">Development</h3>
          <Pill tone="warn">Development (historical, not prospective)</Pill>
        </div>
        <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">
          Held-out historical days{typeof se.development?.test_days === "number" ? ` (${se.development.test_days} test days)` : ""}.
          Useful for building models, not evidence of forward performance.
        </p>
        {se.development ? (
          <ScoreTable rows={dev} families={families} caption="Development (historical, not prospective) scores" />
        ) : (
          <Quiet>No development scores in this snapshot.</Quiet>
        )}
      </Card>

      {attribution.length ? (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-[15px] font-semibold text-arepo-ink">Family attribution</h3>
            <Pill tone="warn">Development diagnostic, not a score</Pill>
          </div>
          <p className="mb-4 mt-0.5 text-[12.5px] text-arepo-muted">
            Share of each feature family in the newest primary-target fit (mean |SHAP| on the fit&apos;s validation block).
            It describes what a model leans on, not how well it forecasts, and plays no part in promotion.
          </p>
          <Attribution views={attribution} />
        </Card>
      ) : null}

      <Card>
        <h3 className="text-[15px] font-semibold text-arepo-ink">Promotions</h3>
        {promos.length ? (
          <ol className="mt-3 space-y-3">
            {promos.map((p, i) => {
              const g = p.evidence?.gain;
              return (
                <li key={`${p.at}-${i}`} className="text-[13px] leading-relaxed text-arepo-ink2">
                  <span className="block text-[12px] text-arepo-muted">{fmtUtc(p.at)}</span>
                  <span className="font-medium text-arepo-ink">{p.champion}</span>
                  {p.previous ? <> replaced {p.previous}</> : null}
                  {g ? (
                    <span className="font-tabular block text-[12px] text-arepo-muted">
                      gain {fmtGain(typeof g.mean === "number" ? g.mean : null, g.lo ?? null, g.hi ?? null)} nats
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="mt-2 text-[13px] text-arepo-muted">No promotions yet; the initial champion holds.</p>
        )}
      </Card>
    </div>
  );
}
