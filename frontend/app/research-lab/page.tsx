"use client";

import { useAsync } from "@/lib/use-async";
import { directionLabel, DIRECTION_TONE_CLASS } from "@/lib/directional";
import { ErrorState } from "@/components/ErrorState";
import { ListSkeleton } from "@/components/Skeletons";
import { PageHeader, SectionTitle, Badge } from "@/components/ui";
import {
  getExperiments,
  getForecastScores,
  getLatestForecasts,
  getTrials,
  type Experiments,
  type LabExperiment,
  type LabMetric,
  type LatestForecasts,
  type Scores,
  type Trials,
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
        <span id="scores">Scored against baselines</span>
      </SectionTitle>
      {data.status === "available" ? (
        <div className="panel p-5 space-y-2" data-testid="lab-scores">
          <p className="text-[14px]">
            Scored results for {data.experiment}. They are shown below the experiment table with
            their baselines and intervals; this is exploratory research output, not a claim of skill.
          </p>
        </div>
      ) : (
        <div className="panel p-5 text-sm" role="status" data-testid="lab-scores-pending">
          <p className="font-medium text-arepo-ink">Not scored yet</p>
          <p className="mt-1 text-arepo-muted">
            {data.reason ?? "No forecast has been scored yet."} Skill against the no-change and
            reversal baselines is shown only after the later snapshot exists and the pre-registered
            test has been run.
          </p>
        </div>
      )}
    </section>
  );
}

const num = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(4)}`;

function MetricLine({ m }: { m: LabMetric }) {
  return (
    <li className="break-words">
      <span className="font-mono text-[12px]">{m.name || m.metric}</span>: {m.metric}{" "}
      <span className="tabular-nums">{num(m.value)}</span>
      {m.ci ? (
        <span className="tabular-nums"> [95% CI {num(m.ci[0])}, {num(m.ci[1])}]</span>
      ) : null}
      {m.baseline !== null ? <span> vs {String(m.baseline)}</span> : null}
      {m.n !== null ? <span> (n = {String(m.n)})</span> : null}
      {m.verdict !== null ? <span>, verdict: {String(m.verdict)}</span> : null}
    </li>
  );
}

const STATUS_LABEL: Record<LabExperiment["status"], string> = {
  registered: "Registered, awaiting outcome",
  complete: "Complete",
  unknown: "Status unclear",
};

function ExperimentsSection({ data }: { data: Experiments }) {
  if (data.status !== "available") return <Unavailable what="Experiment list" reason={data.reason} />;
  return (
    <section className="space-y-2" aria-labelledby="experiments">
      <SectionTitle>
        <span id="experiments">Experiments</span>
      </SectionTitle>
      <p className="text-[13px] text-arepo-muted max-w-reading">
        Every experiment is written down before its outcome is known. Verdicts use fixed labels
        such as inconclusive or supported (exploratory); none is a validated result.
      </p>
      <div className="panel overflow-x-auto">
        <table className="w-full text-left text-[13px]" data-testid="lab-experiments">
          <caption className="sr-only">Registered experiments, their status and results so far</caption>
          <thead className="text-arepo-muted">
            <tr>
              <th scope="col" className="p-3 font-medium">Experiment</th>
              <th scope="col" className="p-3 font-medium">Status</th>
              <th scope="col" className="p-3 font-medium">Question</th>
              <th scope="col" className="p-3 font-medium">Result so far</th>
            </tr>
          </thead>
          <tbody>
            {data.experiments.map((e) => {
              const r = e.result;
              return (
                <tr key={e.id} id={e.id.toLowerCase()} className="border-t border-arepo-border align-top">
                  <th scope="row" className="p-3 font-mono font-normal">{e.id}</th>
                  <td className="p-3">
                    <Badge tone={e.status === "complete" ? "moderate" : "neutral"}>
                      {STATUS_LABEL[e.status]}
                    </Badge>
                  </td>
                  <td className="p-3 min-w-[14rem]">{e.question}</td>
                  <td className="p-3 min-w-[16rem] space-y-1">
                    <p>{e.result_summary}</p>
                    {r.status === "available" && r.metrics.length > 0 ? (
                      <ul className="list-disc pl-4 text-arepo-muted">
                        {r.metrics.map((m) => (
                          <MetricLine key={m.name + m.metric} m={m} />
                        ))}
                      </ul>
                    ) : null}
                    {r.status === "unavailable" ? (
                      <p className="text-arepo-muted">Result file unavailable: {r.reason}</p>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TrialsSection({ data }: { data: Trials }) {
  if (data.status !== "available") return <Unavailable what="Trial log" reason={data.reason} />;
  return (
    <section className="panel p-5 space-y-2" aria-labelledby="trials" data-testid="lab-trials">
      <SectionTitle>
        <span id="trials">Trial log</span>
      </SectionTitle>
      <p className="text-[14px]">
        {data.total.toLocaleString("en-GB")} {data.total === 1 ? "analysis" : "analyses"} run, all
        logged. Every comparison run is appended to a committed log, including the ones that did
        not work, so the number of things tried is visible.
        {data.malformed_lines > 0 ? ` ${data.malformed_lines} unreadable log lines were skipped.` : ""}
      </p>
      {data.trials.length > 0 ? (
        <ul className="text-[13px] text-arepo-muted space-y-1">
          {data.trials.map((t, i) => (
            <li key={t.trial_id ?? i} className="break-words">
              {t.utc ?? "unknown time"}: {t.dataset ?? "?"} {t.kind ?? ""}{" "}
              {t.preset ? `(${t.preset})` : ""} {t.label ? `[${t.label}]` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export default function ResearchLabPage() {
  const forecasts = useAsync<LatestForecasts>(() => getLatestForecasts(), []);
  const scores = useAsync<Scores>(() => getForecastScores(), []);
  const experiments = useAsync<Experiments>(() => getExperiments(), []);
  const trials = useAsync<Trials>(() => getTrials(), []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research Lab"
        lead="An open lab notebook and a forecast ledger. Experiments are registered before their outcomes, and every analysis is logged."
      />
      <div className="panel p-5 space-y-2" role="note" data-testid="lab-no-edge">
        <p className="font-medium text-arepo-ink">No validated edge</p>
        <p className="text-[14px] text-arepo-ink2 max-w-reading">
          Arepo is testing whether anything beyond a market&apos;s current price and recent move
          helps predict where its price goes next, on new data collected after each rule is frozen.
          So far no result has passed that test. Nothing here is trading advice, a probability of
          any outcome, or evidence of insider activity.
        </p>
      </div>

      {experiments.loading ? (
        <ListSkeleton />
      ) : experiments.error ? (
        <ErrorState message={experiments.error} title="Couldn't load experiments" />
      ) : experiments.data ? (
        <ExperimentsSection data={experiments.data} />
      ) : null}

      <h2 className="sr-only">Forecast ledger</h2>
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

      {trials.loading ? null : trials.error ? (
        <ErrorState message={trials.error} title="Couldn't load trial log" />
      ) : trials.data ? (
        <TrialsSection data={trials.data} />
      ) : null}
    </div>
  );
}
