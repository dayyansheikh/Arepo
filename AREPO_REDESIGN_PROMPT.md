# Arepo UX, Brand and Educational Redesign

## Role

Act as the Opus lead product, design and engineering manager.

Use Sonnet subagents for independent workstreams including reference HTML analysis, design-system implementation, brand and logo exploration, page redesign, educational copy, mathematical typesetting, accessibility review, frontend testing, visual review and defect repair.

Opus must coordinate the work, inspect every substantial change, review diffs, run tests and personally decide whether the redesign is complete.

## Starting point

The current Astrolabe version is a stable, working baseline.

Before changing anything:

1. Confirm the Git working tree is clean.
2. Create a branch called `arepo-redesign`.
3. Create a tag called `astrolabe-baseline`.
4. Record the current test, lint, type-check and build status.
5. Preserve all existing functionality and data modes.
6. Do not alter quantitative calculations or backend behaviour unless a genuine defect is found.
7. Do not rewrite Git history or delete the previous working version.

## Reference HTML files

A folder called `design-references/` contains HTML files exported from Claude Design.

Treat them as visual and interaction references, not production code.

Before implementation:

1. Open every HTML file.
2. Render each locally in a browser.
3. Inspect layout, spacing, typography, navigation, cards, density, responsive behaviour and interaction patterns.
4. Create `docs/design-reference-audit.md`.
5. Record what should be adopted, adapted or rejected.
6. Translate the strongest ideas into the existing Next.js architecture.

Do not paste the reference HTML directly into the application. Do not replace React components with static HTML.

## Product rename

Rename the user-facing product from Astrolabe to **Arepo**.

Update navigation, page titles, metadata, README title, report, screenshots, deployment name, descriptions, logo and favicon.

Do not rename deeply coupled internal Python packages or database identifiers purely for cosmetic consistency if doing so adds risk.

Remove old Astrolabe branding from final user-facing surfaces.

## Brand meaning

Use this exact core meaning as the basis of the brand story:

> Just as Arepo is believed to have been created to unite the Sator Square, we unite information as it is created, conviction as it is expressed, action as it is taken, and markets as they move. Arepo represents the hidden signal found between the lines.

Use the full paragraph only on suitable pages such as About or How Arepo Works. Use shorter versions elsewhere.

## Brand direction

Create a restrained, modern quantitative-research identity.

### Palette

Primary accent: `#E50C0E`

Core neutrals:

- `#FFFFFF`
- `#101010`
- `#191919`
- warm grey backgrounds
- light neutral borders

Use red sparingly for active navigation, key actions, selected controls and important signals. Do not flood the interface with red. Do not rely on red alone for meaning.

### Typography

Use a modernist sans-serif throughout.

Preferred:

- Geist Sans through `next/font`
- otherwise Inter through `next/font`

Use tabular numerals for data. Use monospace only for raw identifiers, code examples and highly technical values.

Create a clear type hierarchy with strong page titles, readable headings, comfortable body text and compact but legible labels.

### Logo

Create an original Arepo logo and favicon.

The logo should be geometric, simple at 16 px, modern, analytical and subtly suggest connection or a hidden central signal.

Do not reproduce the Sator Square literally. Avoid mystical or ornamental styling.

A suitable direction is a minimal four-part structure converging on or revealing a central point.

Generate several SVG concepts, compare them at favicon, navigation and report-cover sizes, then select one after review.

Document the rationale in `docs/brand-system.md`.

## General visual objective

Redesign the interface to feel calm, precise, modern, spacious, approachable and credible.

Use clear spacing, fewer visible borders, restrained rounded corners, subtle surface contrast, consistent cards, progressive disclosure, concise headings and clean charts.

Do not use excessive gradients, glow, glassmorphism or decorative animation.

## Writing rules

Rewrite user-facing copy in natural British English.

Never use em dashes.

Avoid marketing filler, buzzwords, generic AI phrasing, repeated sentence structures, unnecessary disclaimers, walls of text and unexplained jargon.

Keep default explanations short. Put deeper detail behind links, tooltips and expandable sections.

## Information architecture

Create two explanation layers.

### How Arepo Works

This simple page must explain:

1. What a prediction market is
2. Why prices can be interpreted as approximate probabilities
3. Where Arepo gets data
4. What Arepo watches
5. What a signal means
6. What signal strength means
7. What confidence means
8. Why order books matter
9. What Live, Cached and Replay mean
10. What backtesting is
11. What Arepo can and cannot conclude

Use diagrams, short sections and concrete examples. Link to detailed Methodology sections.

### Methodology

This is the technical reference.

Include equations, variables, assumptions, implementation details, limitations, interpretation guidance and links back to product pages.

Use anchored sections. Every technical term used elsewhere must have a matching anchor.

## Mathematical presentation

Never display equations as programming text or malformed inline fractions.

Use KaTeX or an appropriate lightweight renderer.

Render fractions vertically, superscripts and subscripts correctly, Greek letters correctly and aligned equations where useful.

For each equation include:

1. Equation
2. Plain-English explanation
3. Variable legend
4. Worked example where helpful
5. Interpretation
6. Limitations

Default product pages should show plain-English meaning first. Detailed equations should appear after “Show the maths” or in Methodology.

## Contextual help

Create a reusable metric-help component.

Each technical metric should support:

- information icon
- hover and keyboard-focus tooltip
- plain-English definition
- short interpretation
- “Learn more” link to the exact Methodology anchor

Apply it to implied probability, signal strength, confidence, z-score, rolling volatility, spread, midpoint, order-book imbalance, near-mid depth, composite anomaly, movement, volume, liquidity, hit rate, false-positive rate, average forward move, threshold, evaluation horizon and sample size.

Support click or focus on touch devices.

## Navigation

Use:

- Overview
- Markets
- Signal Lab
- Replay
- How It Works
- Methodology

Use the Arepo logo and wordmark. Make the active page obvious. Support laptop and mobile widths.

## Mode selector

Redesign Live, Cached and Replay as a clearly labelled data-mode control.

Explain:

- Live: current public Polymarket data
- Cached: latest successfully stored market data
- Replay: deterministic demonstration dataset

Show current mode, data age, REST state, WebSocket state, concise explanation and a Learn more link.

Do not expose unexplained technical abbreviations.

## Overview

Reduce information density.

Begin with a short orientation block explaining what is shown, when data updated and which mode is active.

Each market card should show only:

- question
- leading outcome and probability
- recent movement
- signal strength
- confidence
- status
- View details

Move secondary statistics to the detail page.

## Markets

Make guided dropdowns the main discovery method.

Include:

- category
- sport
- competition or event group where available
- status
- time to close
- probability range
- signal-strength range
- sort order

Retain free-text search as an advanced secondary option.

Use clear empty states and do not imply all markets have sports metadata.

## Market detail

Use progressive disclosure.

### Summary

Show question, leading probability, recent movement, signal strength, confidence and status.

### Price history

Use a clean chart with clear outcome labels, readable axes, sensible time formatting, explanation and accessible legend.

### Outcomes

Use rounded panels or a clean comparison table.

Default values:

- probability
- best bid
- best ask
- spread

Place z-score, rolling volatility, imbalance, near-mid depth, normalised probability and other specialist metrics behind “Advanced market data”.

Avoid excessive decimal places. Use tabular numerals.

### Signals

Show plain-English meaning first:

- Why this fired
- What changed
- Why it may matter
- Confidence and data quality
- Show the maths
- Methodology link

## Signal Lab

Keep “Why this fired”.

Make each signal read like a short analyst explanation.

Explain what a score such as 93 means, why confidence differs from strength, which components contributed and why the result is not proof of informed or insider activity.

Put maths in an expandable section.

## Replay

Add an introduction titled “What this page shows”.

Explain:

- replay uses a fixed sample dataset
- a signal is generated at one point
- the system checks what happened afterwards
- thresholds change selectivity
- a hit does not mean a profitable trade
- this demonstrates evaluation, not predictive advantage

Rename controls using plain language where possible:

- Minimum signal strength
- Required later movement
- How far ahead to check

Add a dynamic summary sentence, for example:

> With these settings, 4 signals were tested. 2 were followed by a move in the expected direction.

Show conclusions before the data table. Put detailed events and maths in expandable sections.

## Charts and tables

Improve charts with restrained Arepo red, neutral comparison colours, readable date and probability labels, hover values, clear legends and reduced gridline noise.

Improve tables with rounded containers, subtle row separation, shaded headers, consistent alignment, tabular numerals, fewer default columns and responsive behaviour.

## Accessibility

Improve keyboard navigation, focus states, tooltip accessibility, ARIA labels, contrast, form labels, chart alternatives, target sizes, reduced-motion support, mobile interactions and semantic heading order.

## Implementation phases

### Phase 1

Save baseline, audit reference HTML, audit current UI, define design system, select logo and typography, and create the plan. Do not pause for approval.

### Phase 2

Implement design tokens, font, logo, favicon, layout, navigation, cards, controls, tooltips and expandable panels.

### Phase 3

Create How Arepo Works, rebuild Methodology, add maths rendering, anchors and reusable metric explanations.

### Phase 4

Redesign Overview and Markets.

### Phase 5

Redesign Market Detail and Signal Lab.

### Phase 6

Redesign Replay and data-mode controls.

### Phase 7

Run responsive and accessibility reviews, visual review against the HTML references, cross-browser smoke tests, lint, type-check, build, independent Sonnet review, repairs and Opus verification.

## Testing

Preserve backend behaviour.

Run all backend tests plus frontend lint, type checks, tests, production build, browser smoke tests, responsive checks and accessibility checks where available.

Add tests for navigation, tooltips, mode explanations, expandable maths, filters, Methodology anchors, renamed metadata and key page rendering.

Manually inspect every page in Live, Cached and Replay.

Check for broken links, missing labels, overflowing content, unreadable maths, unexplained metrics, stale Astrolabe naming, em dashes, direct HTML copying, excessive text, inconsistent spacing and mobile issues.

## Git and deliverables

Commit in logical milestones.

Do not squash the stable baseline.

At completion create:

- `docs/brand-system.md`
- `docs/design-reference-audit.md`
- updated screenshots
- updated README
- updated portfolio report
- updated submission ZIP
- updated `FINAL_STATUS.md`

Provide a concise changelog grouped into:

- Brand
- Interface
- Education
- Mathematics
- Accessibility
- Technical quality

The final product must be easier to understand, calmer to use and visually stronger while retaining the quantitative capability.
