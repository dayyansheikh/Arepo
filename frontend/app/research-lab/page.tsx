"use client";

import { useAsync } from "@/lib/use-async";
import { directionLabel, DIRECTION_TONE_CLASS } from "@/lib/directional";
import { ErrorState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";
import { PageHeader, SectionTitle, Badge } from "@/components/ui";
import {
  getForecastScores,
  getLatestForecasts,
  type LatestForecasts,
  type Scores,
} from "./client";

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : `${d.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

const pct = (v: number | null, digits = 2) => (v === null ? "n/a" : `${(v * 100).toFixed(digits)} pts`);
const signed = (v: number) => `${v > 0 ? "+" : ""}${(v * 100).toFixed(2)} pts`;

function Unavailable({ what, reason }: { what: string; reason?: string }) {
  return (
    <div className="panel p-5 text-sm" role="status" data-testid="lab-unavailable">
      <p className="font-medium text-arepo-ink">{what} unavailable</p>
      <p className="mt-1 text-arepo-muted">
        {reason ?? "Nothing has been recorded here."} Arepo shows nothing in place of missing data.
      </p>
    </div>
  );
}

function ForecastSection({ data }: { data: LatestForecasts }) {
  if (data.status !== "available") return <Unavailable what="Forecasts" reason={data.reason} />;
  const { model, capture, top } = data;
  return (
    <>
      <section className="panel p-5 space-y-2" aria-labelledby="model-card">
        <div className="flex flex-wrap items-center gap-2">
          <SectionTitle>
            <span id="model-card">Model: {model.model_id}</span>
          </SectionTitle>
          <Badge tone="neutral">Experimental</Badge>
        </div>
        <dl className="grid gap-x-8 gap-y-1 text-[14px] sm:grid-cols-2">
          <div>
            <dt className="text-arepo-muted">Predicts</dt>
            <dd>The change in a market&apos;s midpoint price by the next snapshot (not an outcome)</dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Rule (frozen)</dt>
            <dd className="font-mono break-words text-[13px]">{model.spec.form}</dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Validation status</dt>
            <dd>{model.validation_status}</dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Registered at commit</dt>
            <dd className="font-mono text-[13px]">{model.registered_commit}</dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Snapshot</dt>
            <dd className="font-mono break-all text-[13px]">{capture.capture_id}</dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Origin receipt window</dt>
            <dd>
              {when(capture.origin_receipt_min_utc)} to {when(capture.origin_receipt_max_utc)}
            </dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Forecast logged</dt>
            <dd>{when(data.created_utc)}</dd>
          </div>
          <div>
            <dt className="text-arepo-muted">Eligible markets</dt>
            <dd>{data.n_eligible.toLocaleString("en-GB")}</dd>
          </div>
        </dl>
      </section>

      <section className="space-y-2" aria-labelledby="top-moves">
        <SectionTitle>
          <span id="top-moves">Largest predicted moves</span>
        </SectionTitle>
        <p className="text-[13px] text-arepo-muted max-w-reading">
          Each figure is a predicted change in the midpoint price, in percentage points. It is not
          the probability that anything happens, and direction is not good or bad.
          {data.top_note ? ` ${data.top_note}` : ""}
        </p>
        {top.length === 0 ? (
          <Unavailable what="Predicted moves" reason="No eligible market has a non-zero forecast." />
        ) : (
          <div className="panel overflow-x-auto">
            <table className="w-full text-left text-[13px]" data-testid="lab-table">
              <caption className="sr-only">
                Largest predicted midpoint changes from the latest logged forecast
              </caption>
              <thead className="text-arepo-muted">
                <tr>
                  <th scope="col" className="p-3 font-medium">Market ID</th>
                  <th scope="col" className="p-3 font-medium">Direction</th>
                  <th scope="col" className="p-3 text-right font-medium">Predicted change in midpoint</th>
                  <th scope="col" className="p-3 text-right font-medium">Midpoint now</th>
                  <th scope="col" className="p-3 text-right font-medium">Spread</th>
                  <th scope="col" className="p-3 text-right font-medium">1h change</th>
                </tr>
              </thead>
              <tbody>
                {top.map((r) => {
                  const dir = directionLabel(r.direction, null);
                  return (
                    <tr key={r.market_id} className="border-t border-arepo-border">
                      <th scope="row" className="p-3 font-mono font-normal break-all">
                        {r.market_id}
                      </th>
                      <td className={`p-3 ${DIRECTION_TONE_CLASS[dir.tone]}`}>
                        <span aria-hidden="true">{dir.glyph} </span>
                        {dir.text}
                      </td>
                      <td className="p-3 text-right tabular-nums">{signed(r.dmid_hat)}</td>
                      <td className="p-3 text-right tabular-nums">{pct(r.mid, 1)}</td>
                      <td className="p-3 text-right tabular-nums">{pct(r.spread)}</td>
                      <td className="p-3 text-right tabular-nums">{pct(r.chg_1h)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function ScoresSection({ data }: { data: Scores }) {
  return (
    <section className="space-y-2" aria-labelledby="scores">
      <SectionTitle>
        <span id="scores">Scores</span>
      </SectionTitle>
      {data.status === "available" ? (
        <div className="panel p-5 space-y-2" data-testid="lab-scores">
          <p className="text-[14px]">
            Scored results for {data.experiment}. These are exploratory research output, not a
            claim of predictive skill.
          </p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words text-[12px] max-h-96">
            {JSON.stringify(data.results, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="panel p-5 text-sm" role="status" data-testid="lab-scores-pending">
          <p className="font-medium text-arepo-ink">Pending</p>
          <p className="mt-1 text-arepo-muted">
            {data.reason ?? "No forecast has been scored yet."} Scores appear only after the later
            snapshot exists and the pre-registered test has been run.
          </p>
        </div>
      )}
    </section>
  );
}

export default function ResearchLabPage() {
  const forecasts = useAsync<LatestForecasts>(() => getLatestForecasts(), []);
  const scores = useAsync<Scores>(() => getForecastScores(), []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research Lab"
        lead="Experimental forecasts from a frozen research model. They are not validated and are not trading advice."
      />
      {forecasts.loading ? (
        <ListSkeleton />
      ) : forecasts.error ? (
        <ErrorState message={forecasts.error} />
      ) : forecasts.data ? (
        <ForecastSection data={forecasts.data} />
      ) : null}
      {scores.loading ? null : scores.error ? (
        <ErrorState message={scores.error} title="Couldn't load scores" />
      ) : scores.data ? (
        <ScoresSection data={scores.data} />
      ) : null}
    </div>
  );
}
