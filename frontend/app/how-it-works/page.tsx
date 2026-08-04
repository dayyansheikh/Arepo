import type { Metadata } from "next";
import Link from "next/link";
import { SectionLabel, Disclose, PageHeader } from "@/components/ui";
import { SectionMenu } from "@/components/SectionMenu";
import { methodologyAnchor } from "@/lib/metrics";

export const metadata: Metadata = {
  // Tab title stays exactly "Arepo" on every route (spec §9); no per-route title.
  title: { absolute: "Arepo" },
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
    <section id={id} className="panel scroll-mt-24 space-y-2.5 p-5">
      <SectionLabel>{eyebrow}</SectionLabel>
      <h2 className="text-lg font-bold tracking-[-0.01em] text-arepo-ink">{title}</h2>
      <div className="max-w-reading space-y-2.5 text-[14.5px] leading-relaxed text-arepo-ink2">
        {children}
      </div>
    </section>
  );
}

function LearnMore({ href, children }: { href: string; children?: React.ReactNode }) {
  return (
    <p className="text-[15px]">
      <Link
        href={href}
        className="font-medium text-arepo-accentActive hover:text-arepo-accentHover"
      >
        {children ?? "Learn more"} &rarr;
      </Link>
    </p>
  );
}

/**
 * Order-book diagram: bid levels build up on the left, ask levels build up
 * on the right, the dashed line marks the midpoint, the bracket at the top
 * marks the spread, and the best (nearest-to-spread) level on each side is
 * outlined and joined to its label by a leader line. Each bar also carries a
 * native tooltip and brightens slightly on hover, so a reader can pick out
 * an individual level without needing a script to drive it.
 */
function OrderBookDiagram() {
  const bidHeights = [22, 38, 54, 70];
  const askHeights = [18, 31, 44, 57];
  const pitch = 26;
  const barWidth = 24;
  const centerX = 180;
  const spreadHalf = 10;
  const baseline = 116;
  const bidX = (i: number) => centerX - spreadHalf - (i + 1) * pitch;
  const askX = (i: number) => centerX + spreadHalf + i * pitch;

  return (
    <svg
      viewBox="0 0 360 154"
      role="img"
      aria-label="Diagram of an order book. Bid levels build up on the left in green and ask levels build up on the right in red. The best bid and best ask, the two levels closest to the middle, are outlined. The gap between them is the spread, marked by a bracket at the top. The dashed vertical line marks the midpoint, exactly halfway between the best bid and best ask."
      className="h-auto w-full max-w-md"
    >
      {/* Spread bracket */}
      <line x1="156" y1="18" x2="156" y2="28" className="stroke-arepo-ink" strokeWidth="1.25" />
      <line x1="202" y1="18" x2="202" y2="28" className="stroke-arepo-ink" strokeWidth="1.25" />
      <line x1="156" y1="23" x2="202" y2="23" className="stroke-arepo-ink" strokeWidth="1.25" />
      <text x="179" y="12" textAnchor="middle" className="fill-arepo-ink text-[10px] font-semibold">
        Spread
      </text>

      {/* Side labels */}
      <text
        x={(bidX(3) + bidX(0) + barWidth) / 2}
        y="40"
        textAnchor="middle"
        className="fill-arepo-pos text-[11px] font-semibold"
      >
        Bids
      </text>
      <text
        x={(askX(0) + askX(3) + barWidth) / 2}
        y="40"
        textAnchor="middle"
        className="fill-arepo-neg text-[11px] font-semibold"
      >
        Asks
      </text>

      {/* Baseline */}
      <line
        x1={bidX(3)}
        y1={baseline}
        x2={askX(3) + barWidth}
        y2={baseline}
        className="stroke-arepo-border"
        strokeWidth="1"
      />

      {/* Bid levels: level 0 (the best bid) sits closest to the spread and is outlined */}
      {bidHeights.map((h, i) => (
        <rect
          key={`bid-${i}`}
          x={bidX(i)}
          y={baseline - h}
          width={barWidth}
          height={h}
          className={
            i === 0
              ? "fill-arepo-pos stroke-arepo-ink transition-opacity hover:opacity-90"
              : "fill-arepo-pos stroke-transparent transition-opacity hover:opacity-90"
          }
          strokeWidth={i === 0 ? 1.25 : 0}
        >
          <title>{i === 0 ? "Best bid: the highest price a buyer is currently offering" : `Bid level ${i + 1}`}</title>
        </rect>
      ))}

      {/* Ask levels: level 0 (the best ask) sits closest to the spread and is outlined */}
      {askHeights.map((h, i) => (
        <rect
          key={`ask-${i}`}
          x={askX(i)}
          y={baseline - h}
          width={barWidth}
          height={h}
          className={
            i === 0
              ? "fill-arepo-neg stroke-arepo-ink transition-opacity hover:opacity-90"
              : "fill-arepo-neg stroke-transparent transition-opacity hover:opacity-90"
          }
          strokeWidth={i === 0 ? 1.25 : 0}
        >
          <title>{i === 0 ? "Best ask: the lowest price a seller will currently accept" : `Ask level ${i + 1}`}</title>
        </rect>
      ))}

      {/* Midpoint */}
      <line
        x1={centerX}
        y1="32"
        x2={centerX}
        y2="128"
        strokeDasharray="3 3"
        className="stroke-arepo-ink"
        strokeWidth="1.25"
      >
        <title>Midpoint: exactly halfway between the best bid and best ask</title>
      </line>
      <text x={centerX} y="140" textAnchor="middle" className="fill-arepo-ink text-[10px] font-semibold">
        Midpoint
      </text>

      {/* Best bid / best ask labels, each joined to its level by a leader line */}
      <line
        x1="100"
        y1="132"
        x2={bidX(0) + barWidth / 2}
        y2={baseline - bidHeights[0]}
        className="stroke-arepo-muted"
        strokeWidth="1"
      />
      <text x="100" y="140" textAnchor="middle" className="fill-arepo-muted text-[9px] font-medium">
        Best bid
      </text>
      <line
        x1="260"
        y1="132"
        x2={askX(0) + barWidth / 2}
        y2={baseline - askHeights[0]}
        className="stroke-arepo-muted"
        strokeWidth="1"
      />
      <text x="260" y="140" textAnchor="middle" className="fill-arepo-muted text-[9px] font-medium">
        Best ask
      </text>
    </svg>
  );
}

/** Legend tying each order-book term to the diagram element that shows it. */
function OrderBookLegend() {
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-2 text-[12.5px] text-arepo-ink2">
      <div className="inline-flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-sm bg-arepo-pos" aria-hidden="true" />
        <dt className="font-semibold text-arepo-ink">Bids</dt>
        <dd>buyers waiting to purchase</dd>
      </div>
      <div className="inline-flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-sm bg-arepo-neg" aria-hidden="true" />
        <dt className="font-semibold text-arepo-ink">Asks</dt>
        <dd>sellers waiting to sell</dd>
      </div>
      <div className="inline-flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 border border-arepo-ink" aria-hidden="true" />
        <dt className="font-semibold text-arepo-ink">Spread</dt>
        <dd>the gap between best bid and best ask</dd>
      </div>
      <div className="inline-flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-px bg-arepo-ink" aria-hidden="true" />
        <dt className="font-semibold text-arepo-ink">Midpoint</dt>
        <dd>exactly halfway between the two</dd>
      </div>
      <div className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="text-arepo-ink">
          &#8646;
        </span>
        <dt className="font-semibold text-arepo-ink">Imbalance</dt>
        <dd>how bid size compares with ask size</dd>
      </div>
    </dl>
  );
}

const HIW_NAV = [
  {
    items: [
      { id: "prediction-markets", label: "Prediction markets" },
      { id: "prices-as-probability", label: "Prices as probability" },
      { id: "data-sources", label: "Data sources" },
      { id: "what-arepo-watches", label: "What Arepo watches" },
      { id: "what-a-signal-means", label: "What a signal means" },
      { id: "signal-strength", label: "Signal strength" },
      { id: "confidence", label: "Confidence" },
      { id: "order-books", label: "Order books" },
      { id: "data-modes", label: "Data modes" },
      { id: "backtesting", label: "Replay & backtesting" },
      { id: "limits", label: "What it can't conclude" },
    ],
  },
];

export default function HowItWorksPage() {
  return (
    <div className="space-y-8">
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

      <div className="flex gap-12">
        <SectionMenu label="How Arepo works sections" groups={HIW_NAV} />
        <div className="flex min-w-0 flex-1 flex-col gap-5">
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
          easy to trade in and out of, wide usually means the opposite. Exactly halfway between
          the two sits the <strong>midpoint</strong>, often used as the market&apos;s single best
          estimate of the price.
        </p>
        <p>
          <strong>Order-book imbalance</strong> compares how much size is resting on the bid side
          against the ask side. A heavily bid-skewed book can suggest buying pressure building up,
          though, like every reading here, it describes the visible book at a moment in time and
          says nothing about hidden orders or intent.
        </p>
        <div className="space-y-3 pt-1">
          <OrderBookDiagram />
          <OrderBookLegend />
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1">
          <LearnMore href={methodologyAnchor("spread")}>Learn more about spread</LearnMore>
          <LearnMore href={methodologyAnchor("order-book-imbalance")}>
            Learn more about imbalance
          </LearnMore>
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
        </div>
      </div>
    </div>
  );
}
