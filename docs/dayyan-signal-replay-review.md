# Dayyan functional acceptance review (Agent A)

Acting as Dayyan using the running product (live mode, backend :8012) to decide which markets
deserve further research. Judged against the thirteen questions in spec §3. This reflects the state
after the functional validation fixes.

## The core need: a short ranked list I can act on

- **Signal Lab** returns a concise ranked list (15 signals, one per market, no duplicate Yes/No
  complements). Each names its market and links to it. PASS.
- Each signal states, in words, whether it is a **directional view** or **observational only**, and
  why (the same gate the Board uses, now driven by `n_families`). PASS.
- **Strength** and **Confidence** sit side by side and mean different things. Confidence is now the
  reliability estimate (data quality × corroboration × completeness), the SAME number on every
  surface, and never 100% (capped at 95%). Before this pass Signal Lab showed "Confidence 100%" on
  every card; that is gone. PASS.

## Does the evidence make sense?

- Directional coverage is selective, not everything: ~40% of the screened universe gets a
  directional view; the rest are honestly "observational / insufficient". A high strength on thin,
  single-family evidence reads as strong-but-low-confidence, which is what I want. PASS.
- The hypothesis sentence is cautious and phrased as repricing pressure on a named outcome, never a
  probability of profit. PASS.
- Tags are plain English; the "1133 robust standard deviations" noise a reviewer found is fixed to
  read "much larger than this market's usual trade size, bigger than X% of recent trades". PASS.

## A clear next step and no fake reassurance

- The card tells me to open "why this fired", inspect the market and watch for confirmation. It does
  not tell me to trade. PASS.
- Missing components are explained honestly (warm-up reasons), never shown as zero. PASS.

## Replay: what would Arepo have shown me last week?

- Replay defaults to the reconstructed "last week's opportunities", not a synthetic demo. It shows
  the top opportunities at a real cut-off with strength / confidence / Research Priority AS AT that
  moment, then what happened over 1h / 24h / 7d. PASS.
- Outcomes now separate **correct / incorrect / flat / pending**. A market that did not move is
  shown as "Flat (no move)", not a red miss. The summary and baseline table agree. PASS.
- It is honest about being inconclusive on a tiny sample, and states plainly that "Arepo vs
  momentum" is near-self-referential (agreement % shown). I am not being sold an edge. PASS.

## Residual limitations I was told about (acceptable, disclosed)

- The reconstructed sample is small (survivorship is a hard exclusion, disclosed) and every cut-off
  is labelled inconclusive. The real evidence path (prospective cohorts) has not accumulated yet
  (0 cohorts), and the data-status panel tells me leaving the site open does not change that.

## Verdict

**Accept.** As a research tool for narrowing down what to look at next, Signal Lab and Replay are
usable, honest and internally consistent, and they do not overstate what they know. The confidence
number now means one thing everywhere, and Replay no longer flatters itself by booking flat markets
as misses.
