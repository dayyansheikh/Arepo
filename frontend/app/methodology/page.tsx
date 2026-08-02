import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Methodology — Astrolabe",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel space-y-2 p-5">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="space-y-2 text-sm text-muted-fg">{children}</div>
    </section>
  );
}

export default function MethodologyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Methodology</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-fg">
          Astrolabe is a read-only instrument: it takes public order-book and price data from
          Polymarket and computes a fixed set of descriptive statistics and screening heuristics.
          It does not place trades, does not have private information, and does not prove that
          any market participant has an information edge.
        </p>
      </div>

      <Section title="Data sources">
        <p>
          Market metadata (questions, categories, tags, end dates) comes from Polymarket&apos;s
          public Gamma API. Order-book and price data — best bid/ask, midpoint, trade prints —
          comes from Polymarket&apos;s public CLOB REST and WebSocket feeds. Astrolabe only reads
          these public endpoints; it holds no positions and executes no orders.
        </p>
      </Section>

      <Section title="Data modes">
        <p>
          <strong>Live</strong> queries the CLOB/Gamma APIs directly over the network. It depends
          on those services being reachable and can be slower or briefly stale during upstream
          hiccups. <strong>Cached</strong> serves the most recent successfully fetched snapshot
          when live data is unavailable or rate-limited. <strong>Replay</strong> serves a fixed,
          deterministic dataset captured ahead of time — useful for demos, offline use, and for
          the backtest, since it never changes underneath you. The mode in use is always shown in
          the status chip in the top bar; Astrolabe never presents replay or cached data as live.
        </p>
      </Section>

      <Section title="Implied probability">
        <p>
          A market&apos;s implied probability is read directly from its traded price (a price of
          $0.63 implies roughly 63%). This is a reflection of what traders are willing to pay, not
          a calibrated forecast — it can be moved by thin liquidity, a single large order, or a
          handful of participants, especially in low-volume markets. The normalized figure rescales
          outcome probabilities so they sum to 100% across a market&apos;s outcomes, correcting for
          the small overround typically present in raw order-book prices.
        </p>
      </Section>

      <Section title="Movement and rolling volatility">
        <p>
          Movement is the change in an outcome&apos;s midpoint price over a trailing window (for
          example, the last hour). Rolling volatility is the standard deviation of returns over a
          trailing window of observations, giving a sense of how noisy a market&apos;s pricing has
          been recently, independent of direction.
        </p>
      </Section>

      <Section title="Midpoint, spread, and z-score">
        <p>
          Midpoint is the average of the best bid and best ask. Spread is the gap between them in
          price terms; relative spread expresses that gap as a share of the midpoint, which makes
          spreads comparable across markets trading at different price levels. The z-score
          expresses a current reading (such as a price move) in standard deviations relative to
          that outcome&apos;s own recent history, so a reading of +2.5 means &quot;about 2.5
          standard deviations above this outcome&apos;s typical recent behavior,&quot; not a
          probability or a guarantee of anything.
        </p>
      </Section>

      <Section title="Book imbalance and near-mid depth">
        <p>
          Book imbalance compares resting bid size to resting ask size near the top of the book,
          on a scale from -1 (ask-heavy) to +1 (bid-heavy). Near-mid depth is the total order size
          resting within a small band around the midpoint. Both describe the shape of the visible
          order book at a moment in time — they say nothing about hidden orders, off-book
          activity, or intent.
        </p>
      </Section>

      <Section title="Composite anomaly signals">
        <p>
          A signal combines several normalized components — for example, price movement, z-score,
          volatility, and book imbalance — into a single weighted strength score between 0 and 1,
          plus a direction. Each component carries an explanation and a weight so the score is
          auditable rather than a black box. Signals are a screening tool for finding markets
          worth a closer look; they are not evidence of insider trading, market manipulation, or
          any other specific cause, and they are not trading signals to act on directly.
        </p>
      </Section>

      <Section title="Confidence and data quality">
        <p>
          Every outcome and signal carries a data-quality label (good, limited, or poor) and a
          confidence score. These reflect how much and how recent the underlying order-book and
          trade data is — thin order books, stale quotes, or short history all lower confidence.
          Low-confidence readings should be treated with proportionally more skepticism.
        </p>
      </Section>

      <Section title="Look-ahead-safe backtesting">
        <p>
          The Replay &amp; Backtest page evaluates historical signals against a fixed, synthetic
          dataset. Every signal is evaluated only against price data that occurred strictly after
          it was detected, so the backtest cannot &quot;see the future&quot; when scoring a signal
          — this is what look-ahead-safe means. The resulting hit rate and false-positive rate
          describe how often a signal of a given strength was followed by a move of the chosen
          size in this dataset. They are backward-looking descriptive statistics about a synthetic
          scenario, not a forecast, not a backtest of a tradeable strategy, and not adjusted for
          fees, slippage, or execution.
        </p>
      </Section>

      <Section title="Ethical boundaries">
        <ul className="list-disc space-y-1 pl-5">
          <li>Astrolabe is read-only: it never places, suggests, or automates trades.</li>
          <li>
            It never claims to detect insider trading or any other specific wrongdoing — an
            anomalous reading can have many mundane explanations, including thin liquidity, a
            single participant, or normal news-driven repricing.
          </li>
          <li>
            Every page keeps the active data mode visible, and cached or replay data is never
            relabeled as live.
          </li>
          <li>
            Numbers here are descriptive statistics over public data, not financial advice or a
            recommendation to act.
          </li>
        </ul>
      </Section>
    </div>
  );
}
