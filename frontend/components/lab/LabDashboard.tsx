"use client";

import { useEffect, useMemo, useState } from "react";
import { useLabDashboard } from "@/lib/lab/use-lab-dashboard";
import { agoLabel, buildPipeline, parsePayload, snapshotFreshness, type Freshness } from "@/lib/lab/model";
import type { HostPayload, LabCommand, MacPayload } from "@/lib/lab/types";
import { SkeletonBlock } from "@/components/Skeletons";
import { ErrorState } from "@/components/ErrorState";
import { Activity } from "./Activity";
import { Candidates } from "./Candidates";
import { EdgePipeline } from "./EdgePipeline";
import { ExperimentExplorer } from "./ExperimentExplorer";
import { MachineLearning } from "./MachineLearning";
import { SignalEngine } from "./SignalEngine";
import { AutopilotCard, Controls, HostCard } from "./Machines";
import { useAuth } from "@/lib/auth-context";
import { Revealed, UnlockScreen } from "@/components/security/UnlockScreen";
import { LabTabs } from "./LabTabs";
import { Dot, fmtCount, LabNotFound, LabSection, Pill, Quiet } from "./primitives";

const HOST_STALE_S = 30 * 60; // host pushes every 10 min; spec: stale warning after 30 min
const MAC_STALE_S = 75 * 60; // mac pushes every 30 min; allow two missed pushes plus slack

function MachineDot({ name, fresh }: { name: string; fresh: Freshness }) {
  const tone = fresh.state === "fresh" ? "pos" : fresh.state === "stale" ? "warn" : "muted";
  const word = fresh.state === "missing" ? "no report" : fresh.state === "stale" ? `stale, ${agoLabel(fresh.ageSeconds)}` : agoLabel(fresh.ageSeconds);
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-arepo-border bg-arepo-surface px-2.5 py-1 text-[12px] text-arepo-ink2" title={`${name}: ${word}`}>
      <Dot tone={tone} pulse={fresh.state === "fresh"} />
      <span className="font-medium">{name}</span>
      <span className="text-arepo-muted">{word}</span>
    </span>
  );
}

function Headline({ host }: { host: HostPayload }) {
  const h = host.headline ?? {};
  const items: Array<[string, number | undefined]> = [
    ["Ideas", h.hypotheses],
    ["Tests run", h.tests_run],
    ["Live tests", h.live_tests],
    ["Batches", h.batches],
    ["Jobs done", h.jobs_done],
  ];
  const shown = items.filter(([, v]) => typeof v === "number");
  if (!shown.length) return null;
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:flex sm:flex-wrap sm:gap-x-10">
      {shown.map(([label, v]) => (
        <div key={label}>
          <dt className="text-[12px] text-arepo-muted">{label}</dt>
          <dd className="font-display font-tabular text-[26px] font-semibold leading-tight text-arepo-ink">{fmtCount(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function LoadingView() {
  return (
    <div className="space-y-10" aria-busy="true" aria-label="Loading the lab">
      <SkeletonBlock className="h-10 w-48" />
      <SkeletonBlock className="h-64 w-full" />
      <div className="grid gap-4 sm:grid-cols-3">
        <SkeletonBlock className="h-48" />
        <SkeletonBlock className="h-48" />
        <SkeletonBlock className="h-48" />
      </div>
    </div>
  );
}

export function LabDashboard() {
  const { data, fetchedAt, loading, error, notFound: missing, isFixture, locked, refresh } = useLabDashboard();
  const auth = useAuth();
  const [revealed, setRevealed] = useState(false);
  const lockedState = locked ?? auth.locked;
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [sent, setSent] = useState<LabCommand[]>([]);

  // Re-render relative times every 30 s without refetching.
  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 30_000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => setNowMs(Date.now()), [fetchedAt]);

  const host = useMemo(() => parsePayload<HostPayload>(data?.host), [data]);
  const mac = useMemo(() => parsePayload<MacPayload>(data?.mac), [data]);
  const pipeline = useMemo(() => buildPipeline(host), [host]);

  // Commands just sent are shown immediately, until the next poll returns them.
  const commands = useMemo(() => {
    const server = Array.isArray(data?.commands) ? data!.commands! : [];
    const ids = new Set(server.map((c) => c.id));
    return [...sent.filter((c) => !ids.has(c.id)), ...server];
  }, [data, sent]);

  if (lockedState) {
    return (
      <UnlockScreen
        keys={lockedState.keys}
        onUnlocked={() => {
          setRevealed(true);
          void auth.refresh();
          void refresh();
        }}
      />
    );
  }
  if (missing) return <LabNotFound />;
  if (loading && !data) return <LoadingView />;
  if (!data) return <ErrorState title="Couldn't load the lab" message={error ?? "Something went wrong."} />;

  const hostFresh = snapshotFreshness(data.host?.received_at, data.server_time, fetchedAt, nowMs, HOST_STALE_S);
  const macFresh = snapshotFreshness(data.mac?.received_at, data.server_time, fetchedAt, nowMs, MAC_STALE_S);
  const experiments = host?.experiments ?? [];
  const confirmed = pipeline[pipeline.length - 1]?.count;

  return (
    <Revealed active={revealed}>
    <div className="mx-auto max-w-6xl space-y-16 pb-10 sm:space-y-20">
      {isFixture ? (
        <div
          role="note"
          className="z-30 rounded-control border border-arepo-warn/50 md:sticky md:top-[72px] bg-[repeating-linear-gradient(135deg,#FBF3E4_0_10px,#F7EAD2_10px_20px)] px-4 py-2 text-center text-[12.5px] font-semibold uppercase tracking-wider text-arepo-warnText"
        >
          Fixture · local development data, not real results
        </div>
      ) : null}

      {/* 1. Header */}
      <header className="lab-rise space-y-6">
        <LabTabs current="research" />
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
          <div className="min-w-0">
            <p className="section-label flex items-center gap-2">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-arepo-accent" /> Private · owner only
            </p>
            <h1 className="display-hero mt-2 text-[40px] sm:text-[52px]">Lab</h1>
            <p className="mt-2 max-w-reading text-[15.5px] leading-relaxed text-arepo-ink2">
              The search for an edge in prediction markets, live. Every idea, every test, and how far each one has
              got. Nothing here is a trading signal.
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <p
              className={`flex items-center gap-1.5 text-[13px] ${hostFresh.state === "stale" ? "text-arepo-warnText" : "text-arepo-muted"}`}
              aria-live="polite"
            >
              {hostFresh.state === "missing"
                ? "Waiting for the first report"
                : hostFresh.state === "stale"
                  ? `▲ Out of date · updated ${agoLabel(hostFresh.ageSeconds)}`
                  : `Updated ${agoLabel(hostFresh.ageSeconds)}`}
              <button type="button" onClick={refresh} className="focus-ring ml-1 rounded px-1 text-arepo-muted underline-offset-2 hover:text-arepo-ink hover:underline">
                Refresh
              </button>
            </p>
            <div className="flex flex-wrap gap-2">
              <MachineDot name="Host" fresh={hostFresh} />
              <MachineDot name="Autopilot" fresh={macFresh} />
            </div>
          </div>
        </div>
        {error ? (
          <p className="rounded-control border border-arepo-warn/40 bg-arepo-warn/10 px-4 py-2 text-[13px] text-arepo-warnText" role="status">
            {error} Showing the last data received.
          </p>
        ) : null}
        {hostFresh.state === "stale" ? (
          <p className="rounded-control border border-arepo-warn/40 bg-arepo-warn/10 px-4 py-2 text-[13px] text-arepo-warnText" role="status">
            The research host last reported {agoLabel(hostFresh.ageSeconds)} (it normally reports every 10 minutes). Everything
            below is as of then.
          </p>
        ) : null}
        {host ? <Headline host={host} /> : null}
      </header>

      {!host ? (
        <Quiet>
          No snapshot from the research host yet. It reports every 10 minutes; until it does, there is nothing honest to show
          here.
        </Quiet>
      ) : (
        <>
          {/* 2. Edge pipeline (hero) */}
          <LabSection
            id="pipeline"
            eyebrow="How close to an edge"
            title="The edge pipeline"
            lead="An idea moves along only by passing a gate. Closeness is the stage reached, never a probability or an expected profit."
            aside={
              <div className="rounded-card border border-dashed border-arepo-accentBorder bg-arepo-surface px-5 py-3 text-right">
                <p className="text-[12px] font-medium text-arepo-muted">Confirmed edges</p>
                <p className="font-display font-tabular text-[34px] font-semibold leading-none text-arepo-accentActive">
                  {fmtCount(confirmed)}
                </p>
              </div>
            }
          >
            <div className="panel px-4 py-6 sm:px-6 sm:py-8">
              <EdgePipeline stages={pipeline} />
            </div>
          </LabSection>

          {/* 3. Leading candidates */}
          <LabSection
            id="candidates"
            eyebrow="Leading candidates"
            title="Closest so far"
            lead="The ideas that have got furthest, and what happens next."
          >
            <Candidates experiments={experiments} liveTests={host.live_tests ?? []} nowMs={nowMs} />
          </LabSection>

          {/* 4. Experiment explorer */}
          <LabSection
            id="experiments"
            eyebrow="Every experiment"
            title="Explorer"
            lead="Filter by stage, verdict or batch. Open a row for the plain-English version."
          >
            <ExperimentExplorer experiments={experiments} />
          </LabSection>

          {/* 5. Machine learning */}
          <LabSection
            id="ml"
            eyebrow="Machine learning"
            title="What the model has learnt"
            aside={<Pill tone="neutral">Development (historical)</Pill>}
          >
            <MachineLearning ml={host.ml} />
          </LabSection>

          {/* 5b. Signal engine (champion/challenger) */}
          <LabSection
            id="signal-engine"
            eyebrow="Signal engine"
            title="Champion and challengers"
            lead="Models compete on forecast quality for fresh markets. Signal strength and forecast quality only: never a probability of profit or an edge claim."
          >
            <SignalEngine block={host.signal_engine} nowMs={nowMs} />
          </LabSection>

          {/* 6. Activity */}
          <LabSection id="activity" eyebrow="Activity" title="The work, over time">
            <Activity host={host} nowMs={nowMs} />
          </LabSection>
        </>
      )}

      {/* 7. Machines & controls */}
      <LabSection id="machines" eyebrow="Machines" title="Machines and controls">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <HostCard infra={host?.infra} fresh={hostFresh} nowMs={nowMs} />
          <AutopilotCard autopilot={mac?.autopilot} fresh={macFresh} nowMs={nowMs} />
          <Controls
            commands={commands}
            queuePaused={host?.queue?.paused}
            autopilotPaused={mac?.autopilot?.paused}
            nowMs={nowMs}
            simulate={isFixture}
            onSent={(cmd) => {
              if (cmd) setSent((s) => [cmd, ...s.filter((c) => c.id !== cmd.id)]);
              refresh();
            }}
          />
        </div>
      </LabSection>
    </div>
    </Revealed>
  );
}
