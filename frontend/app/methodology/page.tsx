import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { Katex } from "@/components/Katex";
import { Disclose } from "@/components/ui";

export const metadata: Metadata = {
  title: "Methodology",
  description:
    "The technical reference for every reading Arepo computes: definitions, formulas, worked examples, interpretation and limitations.",
};

const NAV: { group: string; items: { id: string; label: string }[] }[] = [
  {
    group: "Foundations",
    items: [
      { id: "overview", label: "Overview" },
      { id: "data-sources", label: "Data sources" },
    ],
  },
  {
    group: "Prices & the book",
    items: [
      { id: "implied-probability", label: "Implied probability" },
      { id: "midpoint", label: "Midpoint" },
      { id: "spread", label: "Spread" },
      { id: "order-book-imbalance", label: "Order-book imbalance" },
      { id: "near-mid-depth", label: "Near-mid depth" },
      { id: "liquidity", label: "Liquidity" },
      { id: "volume", label: "Volume" },
    ],
  },
  {
    group: "Movement",
    items: [
      { id: "movement", label: "Movement" },
      { id: "z-score", label: "Z-score" },
      { id: "rolling-volatility", label: "Rolling volatility" },
    ],
  },
  {
    group: "Signals",
    items: [
      { id: "signal-strength", label: "Signal strength" },
      { id: "confidence", label: "Confidence" },
    ],
  },
  {
    group: "Evaluation (Replay)",
    items: [
      { id: "threshold", label: "Threshold" },
      { id: "evaluation-horizon", label: "Evaluation horizon" },
      { id: "hit-rate", label: "Hit rate" },
      { id: "false-positive-rate", label: "False-positive rate" },
      { id: "average-forward-move", label: "Average forward move" },
      { id: "sample-size", label: "Sample size" },
    ],
  },
  { group: "", items: [{ id: "disclaimer", label: "Disclaimer" }] },
];

function Section({
  id,
  title,
  lead,
  children,
}: {
  id: string;
  title: string;
  lead: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="text-[22px] font-semibold text-arepo-ink">{title}</h2>
      <p className="mt-2 max-w-reading leading-relaxed text-arepo-ink2">{lead}</p>
      {children}
    </section>
  );
}

/** A boxed equation with a plain-English gloss, variable legend, optional worked
 * example, interpretation and limitations — the structure the brief requires. */
function Maths({
  tex,
  gloss,
  legend,
  example,
  interpretation,
  limitations,
}: {
  tex: string;
  gloss?: ReactNode;
  legend?: [string, ReactNode][];
  example?: ReactNode;
  interpretation?: ReactNode;
  limitations?: ReactNode;
}) {
  return (
    <Disclose summary="Show the maths" className="mt-3">
      <div className="space-y-3 text-[13px] leading-relaxed text-arepo-ink2">
        {gloss && <p className="max-w-reading">{gloss}</p>}
        <div className="rounded-card border border-arepo-border bg-arepo-surface px-5 py-4 text-[17px]">
          <Katex tex={tex} display />
        </div>
        {legend && (
          <dl className="grid grid-cols-[auto,1fr] gap-x-4 gap-y-1 max-w-reading">
            {legend.map(([sym, meaning], i) => (
              <div key={i} className="contents">
                <dt className="text-arepo-ink">
                  <Katex tex={sym} />
                </dt>
                <dd className="text-arepo-muted">{meaning}</dd>
              </div>
            ))}
          </dl>
        )}
        {example && (
          <p className="max-w-reading">
            <span className="font-semibold text-arepo-ink">Worked example. </span>
            {example}
          </p>
        )}
        {interpretation && (
          <p className="max-w-reading">
            <span className="font-semibold text-arepo-ink">Interpretation. </span>
            {interpretation}
          </p>
        )}
        {limitations && (
          <p className="max-w-reading">
            <span className="font-semibold text-arepo-ink">Limitations. </span>
            {limitations}
          </p>
        )}
      </div>
    </Disclose>
  );
}

export default function MethodologyPage() {
  return (
    <div className="flex gap-12">
      <nav
        aria-label="Methodology sections"
        className="sticky top-24 hidden h-fit w-52 shrink-0 flex-col gap-4 self-start lg:flex"
      >
        {NAV.map((g) => (
          <div key={g.group || "misc"} className="flex flex-col gap-1">
            {g.group && (
              <span className="section-label mb-1 text-[11px]">{g.group}</span>
            )}
            {g.items.map((it) => (
              <a
                key={it.id}
                href={`#${it.id}`}
                className="focus-ring rounded text-[13px] text-arepo-muted hover:text-arepo-ink"
              >
                {it.label}
              </a>
            ))}
          </div>
        ))}
      </nav>

      <div className="flex min-w-0 flex-1 flex-col gap-14">
        <Section
          id="overview"
          title="Methodology"
          lead={
            <>
              Arepo is a read-only research instrument over public market data. Every reading is a
              descriptive statistic or a screening heuristic, not a prediction, a trading signal, or
              evidence of insider activity. This page states, in plain terms first and precisely
              underneath, exactly what each number means, how it is computed, and where it stops.
            </>
          }
        />

        <Section
          id="data-sources"
          title="Data sources"
          lead={
            <>
              Market questions, categories, tags and end dates come from Polymarket&apos;s public
              Gamma API. Order-book and price data (best bid and ask, midpoint, price history) come
              from Polymarket&apos;s public CLOB REST and WebSocket feeds. Arepo only reads these
              public endpoints. It holds no positions, has no private information, and executes no
              orders.
            </>
          }
        />

        <Section
          id="implied-probability"
          title="Implied probability"
          lead={
            <>
              An outcome&apos;s price is read as an approximate probability. A &quot;Yes&quot;
              trading at 0.62 suggests the market collectively prices the outcome at roughly a 62%
              chance. It reflects what traders are willing to pay, not a calibrated forecast, and it
              can be moved by thin liquidity or a single large order.
            </>
          }
        >
          <Maths
            tex={"\\hat p_i = \\dfrac{p_i}{\\sum_j p_j}"}
            gloss="Raw prices carry a small overround, so the normalised figure rescales an outcome's price by the sum across the market's outcomes so they total 100%."
            legend={[
              ["p_i", "the traded price of outcome i, in [0, 1]"],
              ["\\hat p_i", "the normalised implied probability of outcome i"],
            ]}
            example="If Yes trades at 0.523 and No at 0.477 (sum 1.000), the normalised probabilities are 52.3% and 47.7%."
            interpretation="Treat it as the market's current price of the outcome, not a guarantee."
            limitations="In low-volume markets a handful of participants can set the price, so the implied probability may be a poor estimate of the true chance."
          />
        </Section>

        <Section
          id="midpoint"
          title="Midpoint"
          lead={
            <>
              The midpoint is the halfway price between the best bid and the best ask. It is a
              neutral reference price used for spread and movement when bid and ask disagree.
            </>
          }
        >
          <Maths
            tex={"m = \\dfrac{b + a}{2}"}
            legend={[
              ["b", "best bid (highest buy price)"],
              ["a", "best ask (lowest sell price)"],
              ["m", "midpoint"],
            ]}
            example="With a best bid of 0.523 and best ask of 0.527, the midpoint is 0.525."
            interpretation="A single fair-value reference between the two sides of the book."
            limitations="Undefined when the book is one-sided (no bid or no ask)."
          />
        </Section>

        <Section
          id="spread"
          title="Spread"
          lead={
            <>
              The spread is the gap between the best bid and best ask. The relative spread expresses
              that gap as a share of the midpoint, which makes spreads comparable across markets
              trading at different price levels. A narrow spread usually means a market is easy to
              trade in and out of.
            </>
          }
        >
          <Maths
            tex={"s = a - b, \\qquad s_{\\text{rel}} = \\dfrac{a - b}{m}"}
            legend={[
              ["s", "absolute spread, in probability points"],
              ["s_{\\text{rel}}", "relative spread, as a share of the midpoint"],
              ["a, b, m", "best ask, best bid, midpoint"],
            ]}
            example="A bid of 0.523 and ask of 0.527 give a spread of 0.004 (0.4 points); relative to a 0.525 midpoint that is about 0.76%."
            interpretation="Wider spreads mean a noisier midpoint and a costlier round trip."
            limitations="A momentary quote can widen the spread without reflecting sustained illiquidity."
          />
        </Section>

        <Section
          id="order-book-imbalance"
          title="Order-book imbalance"
          lead={
            <>
              Imbalance compares the resting size on the bid side to the ask side over the first few
              levels of the book, on a scale from −1 (ask-heavy) to +1 (bid-heavy). It describes the
              shape of the visible book at a moment in time.
            </>
          }
        >
          <Maths
            tex={"I = \\dfrac{D_{\\text{bid}} - D_{\\text{ask}}}{D_{\\text{bid}} + D_{\\text{ask}}}"}
            gloss="Depth is the summed order size over the first five levels on each side."
            legend={[
              ["D_{\\text{bid}}", "total resting size on the bid side (first 5 levels)"],
              ["D_{\\text{ask}}", "total resting size on the ask side (first 5 levels)"],
              ["I", "imbalance, in [−1, +1]"],
            ]}
            example="Bid depth 130 and ask depth 70 give I = (130 − 70)/200 = +0.30, a bid-heavy book."
            interpretation="Values near zero are balanced; a large magnitude means one side is much heavier right now."
            limitations="It sees only the visible book. It says nothing about hidden orders, off-book activity, or intent."
          />
        </Section>

        <Section
          id="near-mid-depth"
          title="Near-mid depth"
          lead={
            <>
              Near-mid depth is the total resting order size within a small band of the midpoint. It
              is a transparent, explicitly defined measure of near-touch liquidity, not a universal
              claim about how much a market can absorb.
            </>
          }
        >
          <Maths
            tex={"D_{\\text{near}} = \\!\\!\\sum_{|p - m| \\le \\delta}\\!\\! q_p"}
            legend={[
              ["m", "midpoint"],
              ["\\delta", "band half-width (0.02 probability points by default)"],
              ["q_p", "resting size at price p"],
            ]}
            example="With a 0.525 midpoint and a ±0.02 band, all size resting between 0.505 and 0.545 is summed."
            interpretation="More near-mid depth means the market can absorb larger orders with less price impact."
            limitations="Only resting, visible size within the band is counted; the band choice is an assumption."
          />
        </Section>

        <Section
          id="liquidity"
          title="Liquidity"
          lead={
            <>
              Liquidity is an estimate of how much can be traded near the current price without
              moving it much, drawn from order-book depth close to the midpoint. Higher liquidity
              means a market can absorb larger orders with less price impact. Arepo reports the
              venue&apos;s liquidity figure alongside its own near-mid depth measure.
            </>
          }
        />

        <Section
          id="volume"
          title="Volume"
          lead={
            <>
              Volume is the total value traded in a market. Higher-volume markets tend to have
              tighter, more informative prices, because more participants have acted on them.
            </>
          }
        />

        <Section
          id="movement"
          title="Movement"
          lead={
            <>
              Movement is the change in an outcome&apos;s price over a recent window, in probability
              points. Read it alongside volatility: a 3-point move is large in a calm market and
              small in a jumpy one.
            </>
          }
        />

        <Section
          id="z-score"
          title="Z-score"
          lead={
            <>
              The z-score answers a single question: how unusual is the most recent move, relative
              to this outcome&apos;s own recent behaviour? A z-score near zero is unremarkable; one
              beyond about ±2 is worth a second look.
            </>
          }
        >
          <Maths
            tex={"z = \\dfrac{r_{\\text{last}} - \\mu}{\\sigma}"}
            gloss="The reference distribution is the successive price changes (returns) over a trailing window; μ and σ are their mean and sample standard deviation."
            legend={[
              ["r_{\\text{last}}", "the most recent price change"],
              ["\\mu", "mean of returns over the window (20 observations by default)"],
              ["\\sigma", "sample standard deviation of those returns (ddof = 1)"],
            ]}
            example="If recent moves average 0 with a standard deviation of 0.01, a latest move of +0.025 gives z = 2.5."
            interpretation="A reading of +2.5 means about 2.5 standard deviations above this outcome's typical recent move, not a probability or a guarantee."
            limitations="Needs at least 8 observations; it is undefined when the window is flat (zero variance), and is clipped to ±10 to avoid absurd magnitudes from a near-zero standard deviation."
          />
        </Section>

        <Section
          id="rolling-volatility"
          title="Rolling volatility"
          lead={
            <>
              Rolling volatility is the size of a market&apos;s recent price wobble: the standard
              deviation of its returns over a trailing window, independent of direction. Higher
              volatility means larger recent swings, so a given move is less surprising.
            </>
          }
        >
          <Maths
            tex={"\\sigma = \\sqrt{\\dfrac{1}{n-1} \\sum_{i=1}^{n} (r_i - \\bar r)^2}"}
            legend={[
              ["r_i", "the i-th return in the window"],
              ["\\bar r", "the mean return over the window"],
              ["n", "number of returns in the window"],
            ]}
            interpretation="It sets the scale against which the z-score judges the latest move."
            limitations="A sample standard deviation over a short window is itself noisy."
          />
        </Section>

        <Section
          id="signal-strength"
          title="Signal strength (composite anomaly)"
          lead={
            <>
              Signal strength is a single 0 to 100 reading of how unusual a market&apos;s recent
              behaviour looks, blending several ordinary things worth watching: the size of the
              latest move, a change in spread, a shift in near-mid depth, order-book imbalance and a
              rise in volume. A higher number means more of these are lining up at once. It does not
              say which way the price will move, and it is not proof of informed or insider activity.
            </>
          }
        >
          <Maths
            tex={
              "S = \\dfrac{\\sum_i w_i\\, n_i}{\\sum_i w_i}, \\qquad n_i = \\min\\!\\left(1,\\ \\dfrac{|x_i|}{c_i}\\right)"
            }
            gloss="Each raw component is squashed to a 0–1 magnitude that saturates at a documented cap, then combined as a weighted mean over the components actually available (weights renormalise, so a missing input neither inflates nor deflates the score). The result is shown as 0–100."
            legend={[
              ["x_i", "the i-th raw component"],
              ["c_i", "its saturation cap"],
              ["n_i", "its normalised magnitude, in [0, 1]"],
              ["w_i", "its weight"],
            ]}
            example="Components and (weight, cap): |return z-score| (0.35, 4), volume acceleration (0.20, 3), |order-book imbalance| (0.15, 1), spread change (0.15, 1), depth change (0.15, 1). A z-score of 4 alone squashes to 1.0 and, with only that component present, gives S = 100."
            interpretation="It is a screening tool for finding markets worth a closer look, weighted so the score is auditable rather than a black box."
            limitations="Sensitive to the chosen weights, caps and windows, which are assumptions, not empirically optimal values. It is not a normal-distribution probability and not a profit signal."
          />
        </Section>

        <Section
          id="confidence"
          title="Confidence"
          lead={
            <>
              Confidence says how much to trust a reading, based on how clean the inputs were. It is
              separate from strength: a strong reading on a thin, stale market can still have low
              confidence. A low-confidence reading means the underlying numbers are more likely to be
              noisy, not that the market itself is untrustworthy.
            </>
          }
        >
          <Maths
            tex={"c = \\prod_k f_k, \\qquad f_k \\in (0, 1]"}
            gloss="Confidence starts at 1.0 and is multiplied by a penalty factor below 1 for each weakness in the data, and every applied penalty is recorded so a low confidence is always explainable. A signal's reported confidence is its strength multiplied by this data-quality confidence."
            legend={[
              ["f_k", "the penalty for the k-th weakness"],
              ["c", "overall data-quality confidence, in [0, 1]"],
            ]}
            example="Penalties apply for short history (about n/20 of the ideal), a wide relative spread (over 0.10), thin near-mid depth, stale data, a one-sided book (×0.3) and partial API coverage (×0.7). Bands: GOOD ≥ 0.75, LIMITED ≥ 0.45, POOR below."
            interpretation="Use it as a discount on how seriously to take a reading, not as a verdict on the market."
            limitations="The thresholds are transparent assumptions; they are not calibrated against outcomes."
          />
        </Section>

        <Section
          id="threshold"
          title="Threshold"
          lead={
            <>
              In Replay, the threshold is the minimum signal strength at which a reading counts as a
              fired signal. Raising it gives fewer, higher-confidence signals; lowering it surfaces
              more candidates with more false positives.
            </>
          }
        />

        <Section
          id="evaluation-horizon"
          title="Evaluation horizon"
          lead={
            <>
              The horizon is how far ahead, in frames, Replay looks to check whether a signal was
              followed by a move. A longer horizon gives a move more time to appear but blurs cause
              and effect.
            </>
          }
        />

        <Section
          id="hit-rate"
          title="Hit rate"
          lead={
            <>
              In Replay, the hit rate is the share of fired signals that were followed by a real
              price move of the chosen size, in the signalled direction, within the horizon. It
              measures directional follow-through only. A hit is not a profitable trade.
            </>
          }
        >
          <Maths
            tex={
              "\\text{hit rate} = \\dfrac{\\#\\{\\, \\text{sign}(d)\\,(p_{t+H} - p_t) \\ge \\theta \\,\\}}{\\#\\ \\text{evaluated}}"
            }
            gloss="Signal generation uses frames 0 to t; evaluation uses frames after t only, so the backtest cannot see the future when scoring a signal (look-ahead-safe)."
            legend={[
              ["p_t", "entry price at the signal frame"],
              ["p_{t+H}", "price H frames later"],
              ["d", "signalled direction (up or down)"],
              ["\\theta", "the required later movement (move threshold)"],
            ]}
            example="With 4 signals evaluated and 2 followed by a move of at least θ in the signalled direction, the hit rate is 50%."
            interpretation="Higher means signals were more often followed by a move of the required size. It says nothing about the size of the move beyond the threshold."
            limitations="It is not a profitability measure: no transaction costs, slippage or fees are modelled, and the dataset is a small synthetic sample that does not generalise to live markets."
          />
        </Section>

        <Section
          id="false-positive-rate"
          title="False-positive rate"
          lead={
            <>
              The false-positive rate is the share of fired signals that were not followed by the
              required move within the horizon. Lower is better, but a lower rate usually comes with
              fewer signals overall.
            </>
          }
        >
          <Maths
            tex={
              "\\text{FP rate} = \\dfrac{\\#\\{\\, |p_{t+H} - p_t| < \\theta \\,\\}}{\\#\\ \\text{evaluated}}"
            }
            legend={[
              ["p_{t+H} - p_t", "the forward move over the horizon"],
              ["\\theta", "the required later movement"],
            ]}
            interpretation="Read it against the hit rate and the sample size together, not on its own."
            limitations="On a small sample this rate is noisy; treat it as rough."
          />
        </Section>

        <Section
          id="average-forward-move"
          title="Average forward move"
          lead={
            <>
              The average forward move is the mean price change after a signal fires, over the
              horizon, in the signalled direction. A small or negative average means signals were
              not, on average, followed by a meaningful move.
            </>
          }
        >
          <Maths
            tex={"\\bar{\\Delta} = \\dfrac{1}{N} \\sum_{k=1}^{N} \\text{sign}(d_k)\\,(p_{t_k+H} - p_{t_k})"}
            legend={[
              ["N", "number of evaluated signals"],
              ["d_k", "the k-th signal's direction"],
            ]}
            interpretation="A positive average means moves tended to go the signalled way; near zero or negative means they did not."
            limitations="An average hides the spread of outcomes; a few large moves can dominate a small sample."
          />
        </Section>

        <Section
          id="sample-size"
          title="Sample size"
          lead={
            <>
              The sample size is the number of signals evaluated in a Replay run. Small samples make
              hit and false-positive rates noisy, so read them as rough, not precise.
            </>
          }
        />

        <Section
          id="disclaimer"
          title="Disclaimer"
          lead={
            <>
              Arepo does not place trades, offer financial advice, or prove insider activity. It
              surfaces statistical anomalies in public market data for further reading. An anomalous
              reading can have many mundane explanations, including thin liquidity, a single
              participant, or ordinary news-driven repricing. Nothing here should be treated as
              investment advice or as evidence of wrongdoing.
            </>
          }
        >
          <div className="mt-3 rounded-card border border-arepo-accentBorder bg-arepo-accentTint px-5 py-4 text-[13px] leading-relaxed text-arepo-accentActive">
            New to prediction markets? Start with{" "}
            <Link href="/how-it-works" className="underline">
              How Arepo Works
            </Link>{" "}
            for the plain-English version, then return here for the detail.
          </div>
        </Section>
      </div>
    </div>
  );
}
