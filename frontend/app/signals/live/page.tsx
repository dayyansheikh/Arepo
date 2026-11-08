"use client";

import Link from "next/link";
import { useAsync } from "@/lib/use-async";
import {
  PUBLIC_NOTICE,
  bandIsAvailable,
  embargoText,
  formatScore,
  formatStrength,
  getPublicSignals,
  pageState,
  snapshotTime,
  type PublicBand,
  type PublicFeed,
  type PublicLeaderboardRow,
  type PublicMarketRow,
  type PublicSignals,
} from "@/lib/public-signals";
import { DIRECTION_TONE_CLASS } from "@/lib/directional";
import { PageHeader, SectionTitle } from "@/components/ui";

const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-arepo-muted";
const TD = "px-3 py-2 align-top";
const WRAP = "overflow-x-auto max-w-full";
const FOCUS = "focus:outline-none focus-visible:ring-2 focus-visible:ring-arepo-accent";

function Notice({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel p-6 space-y-1" role="status" data-testid="live-unavailable">
      <p className="font-medium">{title}</p>
      <p className="text-sm text-arepo-ink2">{children}</p>
    </div>
  );
}

function Badge({ data }: { data: PublicSignals }) {
  const state = pageState(data);
  const time = snapshotTime(data);
  const label = state === "live" ? "Live" : state === "stale" ? "Stale" : "No current feed";
  const tone =
    state === "live" ? "text-arepo-pos border-arepo-pos" : "text-arepo-ink2 border-arepo-border";
  return (
    <p
      className={`inline-flex flex-wrap items-center gap-x-2 rounded-full border px-3 py-1 text-sm ${tone}`}
      data-testid="live-badge"
    >
      <strong>{label}</strong>
      <span>{time ? `Snapshot ${time}` : "Snapshot time unavailable"}</span>
    </p>
  );
}

function MarketTable({
  rows,
  caption,
  tone,
  glyph,
  testId,
}: {
  rows: PublicMarketRow[];
  caption: string;
  tone: "up" | "down";
  glyph: string;
  testId: string;
}) {
  return (
    <div className={WRAP} data-testid={testId}>
      <table className="w-full min-w-0 text-sm">
        <caption className="mb-2 text-left text-base font-bold text-arepo-ink">
          <span className={DIRECTION_TONE_CLASS[tone]} aria-hidden="true">
            {glyph}{" "}
          </span>
          {caption}
        </caption>
        <thead>
          <tr>
            <th scope="col" className={TH}>Market</th>
            <th scope="col" className={`${TH} text-right`}>Signal strength</th>
            <th scope="col" className={TH}>Confidence band</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={3} className={`${TD} text-arepo-muted`}>No markets in this list.</td>
            </tr>
          ) : (
            rows.map((r, i) => (
              <tr key={`${r.market_id ?? "x"}-${i}`} className="border-t border-arepo-border">
                <th scope="row" className={`${TD} font-normal break-words`}>
                  {r.market_id !== null ? (
                    <Link
                      href={`/markets/${encodeURIComponent(String(r.market_id))}`}
                      className={`underline underline-offset-2 ${FOCUS}`}
                    >
                      {r.title ?? `Market ${r.market_id}`}
                    </Link>
                  ) : (
                    (r.title ?? "Untitled market")
                  )}
                </th>
                <td className={`${TD} text-right font-mono tabular-nums ${DIRECTION_TONE_CLASS[tone]}`}>
                  {formatStrength(r.signal_strength)}
                </td>
                <td className={TD}>{r.confidence}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function RecordTable({ feed }: { feed: PublicFeed }) {
  const r = feed.track_record;
  return (
    <div className={WRAP} data-testid="live-record">
      <table className="w-full text-sm">
        <caption className="mb-2 text-left text-base font-bold text-arepo-ink">
          Champion prospective record (2-hour direction)
        </caption>
        <thead>
          <tr>
            <th scope="col" className={TH}>Days scored</th>
            <th scope="col" className={`${TH} text-right`}>Log loss</th>
            <th scope="col" className={`${TH} text-right`}>Brier</th>
            <th scope="col" className={`${TH} text-right`}>Calibration slope</th>
            <th scope="col" className={`${TH} text-right`}>Calibration intercept</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-arepo-border font-mono tabular-nums">
            <td className={TD}>{r?.days ?? feed.days_scored ?? "–"}</td>
            <td className={`${TD} text-right`}>{formatScore(r?.log_loss)}</td>
            <td className={`${TD} text-right`}>{formatScore(r?.brier)}</td>
            <td className={`${TD} text-right`}>{formatScore(r?.cal_slope)}</td>
            <td className={`${TD} text-right`}>{formatScore(r?.cal_intercept)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function BandTable({ bands }: { bands: PublicBand[] }) {
  return (
    <div className={WRAP} data-testid="live-bands">
      <table className="w-full text-sm">
        <caption className="mb-2 text-left text-base font-bold text-arepo-ink">
          Record by confidence band
        </caption>
        <thead>
          <tr>
            <th scope="col" className={TH}>Band</th>
            <th scope="col" className={`${TH} text-right`}>Log loss</th>
            <th scope="col" className={`${TH} text-right`}>Brier</th>
            <th scope="col" className={`${TH} text-right`}>Calibration slope</th>
          </tr>
        </thead>
        <tbody>
          {bands.map((b) => (
            <tr key={b.band} className="border-t border-arepo-border">
              <th scope="row" className={`${TD} font-normal`}>{b.band}</th>
              {bandIsAvailable(b) ? (
                <>
                  <td className={`${TD} text-right font-mono tabular-nums`}>{formatScore(b.log_loss)}</td>
                  <td className={`${TD} text-right font-mono tabular-nums`}>{formatScore(b.brier)}</td>
                  <td className={`${TD} text-right font-mono tabular-nums`}>{formatScore(b.cal_slope)}</td>
                </>
              ) : (
                <td colSpan={3} className={`${TD} text-right text-arepo-muted`}>unavailable</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Leaderboard({ rows }: { rows: PublicLeaderboardRow[] }) {
  return (
    <div className={WRAP} data-testid="live-leaderboard">
      <table className="w-full text-sm">
        <caption className="mb-2 text-left text-base font-bold text-arepo-ink">
          Model leaderboard (2-hour direction, lower log loss is better)
        </caption>
        <thead>
          <tr>
            <th scope="col" className={TH}>Model</th>
            <th scope="col" className={TH}>Role</th>
            <th scope="col" className={`${TH} text-right`}>Days</th>
            <th scope="col" className={`${TH} text-right`}>Log loss</th>
            <th scope="col" className={`${TH} text-right`}>Brier</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => {
            const hidden = embargoText(m);
            return (
              <tr
                key={m.model_id}
                className="border-t border-arepo-border"
                data-testid={hidden ? "live-embargoed-row" : "live-model-row"}
              >
                <th scope="row" className={`${TD} font-normal break-words`}>{m.model_id}</th>
                <td className={TD}>
                  {m.role}
                  {m.provisional ? " (provisional)" : ""}
                </td>
                {hidden ? (
                  <td colSpan={3} className={`${TD} text-right text-arepo-muted`}>{hidden}</td>
                ) : (
                  <>
                    <td className={`${TD} text-right font-mono tabular-nums`}>{m.days ?? "–"}</td>
                    <td className={`${TD} text-right font-mono tabular-nums`}>{formatScore(m.log_loss)}</td>
                    <td className={`${TD} text-right font-mono tabular-nums`}>{formatScore(m.brier)}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Body({ data }: { data: PublicSignals }) {
  const state = pageState(data);
  if (state === "unavailable") {
    return (
      <Notice title="Live signals are temporarily unavailable">
        No signal snapshot is available right now. Please check back later.
      </Notice>
    );
  }
  const feed = data.feed;
  return (
    <div className="space-y-8">
      <Badge data={data} />
      {state === "partial" || !feed ? (
        <Notice title="No current signal feed">
          The champion model has no public feed at the moment; only the leaderboard is shown.
        </Notice>
      ) : (
        <>
          <div className="grid gap-8 lg:grid-cols-2">
            <MarketTable
              rows={feed.top_up}
              caption="Top upward markets"
              tone="up"
              glyph="↑"
              testId="live-top-up"
            />
            <MarketTable
              rows={feed.top_down}
              caption="Top downward markets"
              tone="down"
              glyph="↓"
              testId="live-top-down"
            />
          </div>
          <RecordTable feed={feed} />
          {feed.bands.length > 0 ? <BandTable bands={feed.bands} /> : null}
        </>
      )}
      {data.leaderboard.length > 0 ? <Leaderboard rows={data.leaderboard} /> : null}
    </div>
  );
}

export default function LiveSignalsPage() {
  const { data, loading, error } = useAsync(() => getPublicSignals(), []);
  return (
    <div className="space-y-6" data-testid="live-signals">
      <PageHeader title="Live signal strength" />
      <p className="max-w-reading text-[15px] text-arepo-ink2" data-testid="live-notice">
        {PUBLIC_NOTICE}
      </p>
      <SectionTitle className="sr-only">Signals</SectionTitle>
      {loading && !data ? (
        <p role="status" className="text-sm text-arepo-muted">Loading…</p>
      ) : data === "disabled" ? (
        <Notice title="Live signals are not public yet">
          This page will show signal strength once it is switched on.
        </Notice>
      ) : data ? (
        <Body data={data} />
      ) : error ? (
        <Notice title="Live signals are temporarily unavailable">
          The data could not be loaded. Please try again shortly.
        </Notice>
      ) : null}
    </div>
  );
}
