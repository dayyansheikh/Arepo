import type { Metadata } from "next";
import Link from "next/link";
import { SectionLabel, Disclose, PageHeader } from "@/components/ui";
import { methodologyAnchor } from "@/lib/metrics";

export const metadata: Metadata = {
  title: "How Arepo Works",
};

/** A calm, bordered block for one numbered explanation section. */
function Section({
  id,
  eyebrow,
  title,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="panel scroll-mt-24 space-y-3.5 p-6 sm:p-7">
      <SectionLabel>{eyebrow}</SectionLabel>
      <h2 className="text-xl font-bold tracking-[-0.01em] text-arepo-ink">{title}</h2>
      <div className="max-w-reading space-y-3 text-[15px] leading-relaxed text-arepo-ink2">
        {children}
      </div>
    </section>
  );
}

function LearnMore({ href }: { href: string }) {
  return (
    <p className="text-[15px]">
      <Link
        href={href}
        className="font-medium text-arepo-accentActive hover:text-arepo-accentHover"
      >
        Learn more &rarr;
      </Link>
    </p>
  );
}

/** Tiny inline order-book diagram: bids left, asks right, spread in the gap. */
function OrderBookDiagram() {
  return (
    <svg
      viewBox="0 0 320 90"
      role="img"
      aria-label="Diagram of an order book: bid prices building up on the left, ask prices building up on the right, with the spread as the gap between the best bid and best ask, and the midpoint marked between them."
      className="h-auto w-full max-w-sm"
    >
      <text x="4" y="14" className="fill-arepo-muted text-[9px]">
        Bids
      </text>
      <text x="316" y="14" textAnchor="end" className="fill-arepo-muted text-[9px]">
        Asks
      </text>
      {[0, 1, 2, 3].map((i) => (
        <rect
          key={`bid-${i}`}
          x={150 - (i + 1) * 24}
          y={70 - i * 10}
          width={22}
          height={i * 10 + 12}
          className="fill-arepo-pos/25"
        />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <rect
          key={`ask-${i}`}
          x={170 + i * 24}
          y={70 - i * 10}
          width={22}
          height={i * 10 + 12}
          className="fill-arepo-neg/25"
        />
      ))}
      <line x1="160" y1="20" x2="160" y2="82" className="stroke-arepo-border" strokeWidth="1" />
      <text x="160" y="88" textAnchor="middle" className="fill-arepo-muted text-[8px]">
        midpoint
      </text>
      <text x="130" y="88" textAnchor="middle" className="fill-arepo-muted text-[8px]">
        best bid
      </text>
      <text x="190" y="88" textAnchor="middle" className="fill-arepo-muted text-[8px]">
        best ask
      </text>
    </svg>
  );
}

export default function HowItWorksPage() {
  return (
    <div className="space-y-12">
      <PageHeader
        title="How Arepo works"
        lead={
          <>
            A plain-English guide to what Arepo watches, what its numbers mean, and what they do
            not tell you. For the exact formulas, see the{" "}
            <Link
              href="/methodology"
              className="text-arepo-accentActive hover:text-arepo-accentHover"
            >
              Methodology
            </Link>{" "}
            page.
          </>
        }
      />

      <Section id="prediction-markets" eyebrow="The basics" title="What a prediction market is">
        <p>
          A prediction market lets people trade on the outcome of a future event, such as
          &quot;Will it rain in London on Friday?&quot; Each outcome (Yes or No) has its own
          price between 0 and 1, and that price moves as people buy and sell based on what they
          think is likely.
        </p>
        <p>
          Polymarket is one such market. Arepo does not run it, does not trade on it, and cannot
          see anything a member of the public could not also see on Polymarket&apos;s own site.
        </p>
      </Section>

      <Section id="prices-as-probability" eyebrow="Reading a price" title="Why prices can be read as probabilities">
        <p>
          If &quot;Yes&quot; is trading at 0.62, that suggests the market collectively prices the
          outcome at roughly a 62% chance. It is a useful shorthand, and Arepo uses it throughout.
        </p>
        <p>
          But it is a price, not a guarantee. It reflects what traders are currently willing to
          pay, which can be moved by thin liquidity, a single large order, or a small number of
          participants, especially in quiet markets. Treat it as a crowd&apos;s current lean, not
          a calibrated forecast.
        </p>
      </Section>

      <Section id="data-sources" eyebrow="Where the numbers come from" title="Arepo's data sources">
        <p>
          Arepo reads two public Polymarket feeds: the <strong>Gamma API</strong> for market
          details (the question, category, tags, close date), and the <strong>CLOB API</strong>{" "}
          for prices and the order book (best bid, best ask, trade history). Both are the same
          public endpoints anyone can query.
        </p>
        <p>
          Arepo is read-only. It holds no positions, places no orders, and has no access to
          anything beyond what these public feeds return.
        </p>
      </Section>

      <Section id="what-arepo-watches" eyebrow="Under the bonnet" title="What Arepo watches">
        <p>
          For each outcome, Arepo keeps a rolling window of recent readings and tracks five
          things: how far the price has moved, how wide the bid/ask spread is, how lopsided the
          order book is between bids and asks, how much size is resting near the midpoint, and
          how trading volume is changing.
        </p>
        <p>None of these are exotic. They are the same figures a trader watching the book would notice, just tracked continuously and compared against each market&apos;s own recent history.</p>
      </Section>

      <Section id="what-a-signal-means" eyebrow="Signals" title="What a signal means">
        <p>
          A signal is a flag that a market&apos;s recent behaviour looks statistically unusual
          compared with its own history, not compared with other markets, and not against any
          external benchmark.
        </p>
        <p>
          A signal is <strong>not</strong> a prediction of which way the price will go next, and
          it is <strong>not</strong> proof that anyone traded on non-public information. Thin
          liquidity, a single large trade, or ordinary news can all produce the same pattern.
        </p>
        <Disclose summary="Why history-relative, not market-relative?">
          <p>
            Markets differ hugely in size and typical noise. A 3-point move is unremarkable in a
            volatile market and striking in a placid one, so Arepo compares each outcome only
            against its own recent behaviour rather than a fixed threshold shared across markets.
          </p>
        </Disclose>
      </Section>

      <Section id="signal-strength" eyebrow="Signals" title="What signal strength means">
        <p>
          Signal strength is a single reading from 0 to 100 that blends price movement, spread
          change, order-book imbalance, depth change and volume acceleration into one number.
          Higher means more of these are lining up at once, unusually, at the same time.
        </p>
        <p>It does not say which direction the price will move next, or that anything is wrong with the market.</p>
        <LearnMore href={methodologyAnchor("signal-strength")} />
      </Section>

      <Section id="confidence" eyebrow="Signals" title="What confidence means">
        <p>
          Confidence is different from strength. Strength measures how unusual the behaviour
          looks; confidence measures how much to trust that reading, based on data quality. A
          short price history, a wide spread, thin depth, stale data or a one-sided book all
          pull confidence down.
        </p>
        <p>
          A strong signal with low confidence is not a contradiction: the pattern looks unusual,
          but the underlying data is thin enough that the reading could be noisy. Low confidence
          on a market says the data is thin, not that the market itself is untrustworthy.
        </p>
        <LearnMore href={methodologyAnchor("confidence")} />
      </Section>

      <Section id="order-books" eyebrow="Order books" title="Why order books matter">
        <p>
          Every price sits between a <strong>best bid</strong> (the highest price a buyer is
          currently offering) and a <strong>best ask</strong> (the lowest a seller will accept).
          The gap between them is the <strong>spread</strong>: narrow usually means the market is
          easy to trade in and out of, wide usually means the opposite.
        </p>
        <p>
          <strong>Order-book imbalance</strong> compares how much size is resting on the bid side
          against the ask side. A heavily bid-skewed book can suggest buying pressure building up,
          though, like every reading here, it describes the visible book at a moment in time and
          says nothing about hidden orders or intent.
        </p>
        <OrderBookDiagram />
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1">
          <LearnMore href={methodologyAnchor("spread")} />
          <LearnMore href={methodologyAnchor("order-book-imbalance")} />
        </div>
      </Section>

      <Section id="data-modes" eyebrow="Data modes" title="Live, Cached and Replay">
        <p>
          The mode selector in the top bar controls where a page&apos;s data comes from, and the
          mode in use always travels with the page, so cached or replay data is never shown as
          live.
        </p>
        <ul className="list-disc space-y-1.5 pl-5">
          <li>
            <strong>Live</strong>: current public Polymarket data, fetched right now. Depends on
            Polymarket&apos;s services being reachable.
          </li>
          <li>
            <strong>Cached</strong>: the latest market data Arepo has successfully stored, served
            when a fresh live read is not available.
          </li>
          <li>
            <strong>Replay</strong>: a fixed, deterministic demonstration dataset, useful for
            exploring Arepo offline and for the backtest below, since it never changes underneath
            you.
          </li>
        </ul>
      </Section>

      <Section id="backtesting" eyebrow="Replay" title="What backtesting is">
        <p>
          Replay takes each historical moment a signal would have fired and checks what actually
          happened to the price afterwards, within a fixed evaluation horizon. It is{" "}
          <strong>look-ahead-safe</strong>: a signal is judged only on frames that come after it
          fired, never on data it could not have seen at the time.
        </p>
        <p>
          A &quot;hit&quot; means the price moved the signalled direction by at least a chosen
          amount within that horizon, that is <strong>follow-through</strong>, not profit. Replay
          runs on a synthetic, fixed dataset with no trading costs or slippage modelled, so its
          hit rate describes this dataset, not a live trading strategy.
        </p>
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <p className="text-[15px]">
            <Link href="/replay" className="font-medium text-arepo-accentActive hover:text-arepo-accentHover">
              Try Replay &rarr;
            </Link>
          </p>
          <LearnMore href={methodologyAnchor("hit-rate")} />
        </div>
      </Section>

      <Section id="limits" eyebrow="Scope" title="What Arepo can and cannot conclude">
        <p>
          Arepo is a screening tool. It can tell you that an outcome&apos;s recent behaviour looks
          statistically unusual compared with its own history, and roughly how confident that
          reading is given the data available.
        </p>
        <p>
          It cannot tell you why the pattern occurred, what will happen next, or whether anyone
          involved holds non-public information. It is not financial advice, not a forecast, and
          not proof of wrongdoing: it is a starting point for a closer look, using only public
          data.
        </p>
      </Section>

      <section className="panel space-y-3 border-arepo-borderStrong bg-arepo-surface2 p-6">
        <SectionLabel>Why Arepo</SectionLabel>
        <p className="max-w-reading text-[15px] leading-relaxed text-arepo-ink2">
          Just as Arepo is believed to have been created to unite the Sator Square, we unite
          information as it is created, conviction as it is expressed, action as it is taken, and
          markets as they move. Arepo represents the hidden signal found between the lines.
        </p>
      </section>
    </div>
  );
}
