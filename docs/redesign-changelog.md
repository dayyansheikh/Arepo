# Arepo redesign changelog

The Astrolabe baseline (tag `astrolabe-baseline`) was rebranded and redesigned into
**Arepo** on branch `arepo-redesign`, without altering the quantitative engine or
backend behaviour. Grouped by theme.

## Brand

- Renamed the product to **Arepo** on every user-facing surface: navigation, page
  titles, metadata, README, portfolio report, footer, and the backend-provided
  display strings (`config.app_name`, the `/api/meta` disclaimer, the `/docs`
  title). Internal Python package, database identifiers and API paths keep the
  original `astrolabe` name to avoid coupled-rename risk.
- New identity: a single red accent (`#E50C0E`) on a warm-neutral light ground,
  used sparingly for active navigation, primary actions, selected controls and key
  signals; committed to a single light theme.
- Original **convergence-mark logo** (four chevrons revealing a central red node)
  and matching SVG favicon and Apple touch icon, legible at 16px.
- The Sator-Square brand story, in full on How Arepo Works and in short form
  elsewhere. Rationale in `docs/brand-system.md`; reference verdicts in
  `docs/design-reference-audit.md`.

## Interface

- Rebuilt shell: sticky top bar with the Arepo logo and wordmark, a clear active
  state, a **data-mode control** (Live / Cached / Replay) with a plain-English
  explanation popover, and a source-health chip.
- **Overview**: reduced density, an orientation line stating mode and data age, a
  research-disclaimer callout, top-movers cards trimmed to the essentials, and
  compact ranked lists.
- **Markets**: guided dropdown discovery (category, status, signal strength,
  probability, time to close, sort) as the primary method, with free-text search
  demoted to a secondary control and honest empty states.
- **Market detail**: breadcrumb, a stat strip, a clean red/slate price-history
  chart, and outcome panels that show the headline numbers by default with a
  "Show advanced market data" panel for specialist metrics.
- **Signal Lab**: a plain-English explainer and explainable signal cards ("Why
  this fired"), with a functional strength filter and strength tiers.
- **Replay**: a "What this page shows" introduction, plain-language renamed
  controls, a dynamic summary sentence stated before the data, emphasised hit-rate
  tile, and the events table and assumptions behind expanders.
- Consistent cards, restrained radii, fewer and subtler borders, and no gradients,
  glow or glassmorphism.

## Education

- New **How Arepo Works** page: eleven short, plain-English sections (what a
  prediction market is, why prices read as probabilities, data sources, what Arepo
  watches, signals, strength, confidence, order books, data modes, backtesting, and
  what Arepo can and cannot conclude) with an inline order-book diagram.
- Rebuilt **Methodology** as the technical reference: a sticky anchor sidebar and a
  section for every metric, plain-English first, then the maths.
- A single metric registry (`lib/metrics.ts`) backs both the tooltips and the
  Methodology anchors, so every term used in the product resolves to a real anchor.

## Mathematics

- Equations render with **KaTeX** (correct fractions, subscripts, Greek letters),
  not programming text or malformed inline fractions.
- Each equation carries a plain-English gloss, a variable legend, a worked example
  where helpful, an interpretation and its limitations.
- Formulas were verified against the actual analytics code (the composite anomaly
  is a weighted mean of saturating components, not a normal CDF; confidence is a
  multiplicative data-quality penalty), correcting the reference mockup.

## Accessibility

- A reusable **metric-help** component: an info icon with a plain-English
  definition, a short interpretation and a "Learn more" link to the exact
  Methodology anchor, operable by hover, keyboard focus and touch (click to pin),
  and dismissable with Escape.
- A single themed `:focus-visible` ring on every interactive element, never the
  browser default.
- Colour is never the only cue: up/down and good/bad pair colour with a sign,
  arrow or word; source-health dots carry a text state via `aria-label`.
- Chart data is exposed as a visually-hidden table; semantic heading order (one
  `h1` per page); reduced-motion honoured.

## Technical quality

- Frontend type-checks, lints and builds cleanly; backend **128 tests pass** and is
  ruff-clean (two tests updated for the rebranded app name).
- New dependencies: `geist` (font) and `katex` (maths). The data layer
  (`lib/api|types|format|use-async|use-status|mode-context`) is unchanged.
- An independent Sonnet review was run and its findings fixed: a stale-branding
  error string, a missing Methodology `h1`, colour-only source-health, a hardcoded
  amber hex (now a token), a run-on sentence, and a documentation-accuracy
  correction.
- The `astrolabe-baseline` tag and the original commit history are preserved; the
  redesign is additive commits on a branch.
