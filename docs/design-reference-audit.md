# Design reference audit

_Phase 1 deliverable for the Arepo redesign. Records what each reference in_
_`design-references/` contributes, and what is adopted, adapted or rejected._

## What was inspected

All files in `design-references/` were opened and read in full, and the four
`uploads/` screenshots were rendered:

- **Seven page mockups** (`*.dc.html`), Overview, Markets, MarketDetail,
  SignalLab, Replay, Methodology, plus `Overview-print.html`. These are static
  exports from Claude Design using an `x-dc` / `sc-for` templating runtime
  (`support.js`, `doc-page.js`). They are visual references, not production code.
- **Three design-system bundles** (`_ds/`), `modernist` (red-on-white, Archivo,
  flat 2px rules, zero radius), `industry` (steel-blue blueprint wireframe,
  Barlow Condensed), `broadsheet` (newsprint serif, CMYK spot colour). Each ships
  a token sheet (`styles.css`), a `readme.md` and a `theme.json`.
- **Four `uploads/` PNGs**, screenshots of the *current* (baseline) Astrolabe app
  at `localhost:3000` (Overview, Markets, Replay, Market detail). These are the
  "before" state, useful only for before/after comparison.

## Rendering note

The `.dc.html` files depend on a bundled runtime and Google Fonts, so rather than
serve them, their markup and inline styles were read directly (every colour,
size, radius and interaction is inline). This gives an exact reading of the
intended typography, spacing, component structure and interaction patterns
without executing untrusted bundled JavaScript.

---

## The core tension: mockup palette vs. brand brief

The `.dc.html` mockups are branded **Astrolabe** with a **warm gold** accent
(`#b8791f`), a cream ground (`#f6f4ef`) and **Barlow / Barlow Condensed** type.
The redesign brief (`AREPO_REDESIGN_PROMPT.md`) supersedes all three of those:
the product becomes **Arepo**, the accent becomes **red `#E50C0E`**, and the type
becomes **Geist Sans (Inter fallback)**.

**Resolution:** the mockups are treated as authorities on *layout, density,
component anatomy and interaction*, and are overridden on *brand* (name, colour,
type). Where this audit says "adopt" a mockup pattern, it means adopt the
structure and translate the colour/type through the Arepo tokens.

---

## Per-reference verdicts

### Overview (`Overview.dc.html`), ADOPT (structure)

- **Adopt:** 76px header with logo + wordmark + primary nav + a right-aligned
  status pill; page title + one-line orientation sentence; a dismissable research
  disclaimer banner directly under the title; "Top movers" as a responsive card
  grid (`minmax(300px, 1fr)`); "Most active" as a compact list inside one rounded
  container; uppercase 13px section labels with a right-aligned secondary note.
- **Adapt:** the card only shows question, category, status, top outcome, volume,
  spread, movement, and a signal-strength meter, this matches the brief's
  "reduce density" list closely, but the brief drops volume/spread from the card
  and keeps movement, signal strength, confidence and status. Trim the card to the
  brief's field list and push spread to the detail page.
- **Reject:** the gold gradient logo tile; the warm-cream palette; Barlow.

### Markets (`Markets.dc.html`), ADOPT (structure)

- **Adopt:** guided filter bar as the primary discovery method, Category,
  Status, Signal strength, Sort by as styled native `<select>`s in one rounded
  panel; identical card grid to Overview; whole card is a link.
- **Adapt:** the brief asks for more guided dropdowns (sport, competition/event
  group, time-to-close, probability range) and free-text search demoted to an
  "advanced" secondary control. Extend the filter set and add a clear empty state
  that does not imply every market has sports metadata.
- **Reject:** gold focus ring on selects (use the red accent ring).

### Market detail (`MarketDetail.dc.html`), ADOPT (structure)

- **Adopt:** breadcrumb (Markets / category); large question title; a horizontal
  stat strip (volume, 24h, liquidity, ends, source) under a hairline; **price
  history** as a clean area+line chart with 5 horizontal gridlines, right-edge
  value labels and formatted date ticks; **Outcomes** as two rounded panels with a
  3-column stat grid and a `<details>` "Show advanced metrics" holding z-score,
  rolling volatility, imbalance, near-mid depth, normalised probability, relative
  spread; **Signals** panel with plain-English meaning first, a strength meter,
  confidence, and a "How this signal is calculated" `<details>` + "Learn more →"
  anchor.
- **Adapt:** this is the strongest reference. Keep the progressive-disclosure
  split (default vs. advanced) exactly. Translate the chart's gold/green series to
  Arepo red (primary) + a neutral slate (comparison) per the charts brief. Add the
  metric-help tooltip component (icon + hover/focus + definition + Learn more)
  to every specialist metric rather than a bare `title` attribute.
- **Reject:** `title`-only tooltips (not keyboard accessible); gold chart fills.

### Signal Lab (`SignalLab.dc.html`), ADOPT (structure)

- **Adopt:** a "What is the composite anomaly signal?" explainer card with a
  "Show the maths" `<details>`; a "Currently firing" list with STRONG / MODERATE /
  WEAK badges + strength meters; a "Signal configuration" panel of labelled
  sliders; a "How thresholds affect the signal" `<details>`.
- **Adapt:** the brief wants each signal to read like a short analyst explanation
  ("Why this fired", what changed, why it may matter, confidence/data quality,
  and why it is not proof of insider activity). Expand each row into that
  narrative rather than a bare title + meter.
- **Reject:** the WEAK badge's warm-green palette (retune to neutral tokens).

### Replay (`Replay.dc.html`), ADOPT (structure)

- **Adopt:** intro sentence; three plain-language controls (strength, move,
  horizon); a grid of stat tiles with the hit-rate tile emphasised; a "Signal
  outcomes" table with a shaded header, tabular numerals and Yes/No follow-through
  badges; an "Assumptions and limitations" two-column `<details>`; a closing
  disclaimer banner.
- **Adapt:** the brief wants a **titled "What this page shows" intro**, controls
  **renamed** to "Minimum signal strength", "Required later movement", "How far
  ahead to check", a **dynamic summary sentence** ("With these settings, 4 signals
  were tested. 2 were followed by a move…"), and conclusions shown *before* the
  data table with detailed events behind an expander.
- **Reject:** emphasising hit rate in accent without a caveat that a hit is not a
  profitable trade (make that explicit in the summary).

### Methodology (`Methodology.dc.html`), ADOPT (structure)

- **Adopt:** two-column layout with a **sticky anchor sidebar**; each concept as
  an `id`-anchored `<section>` with plain-English first, then a "Show the maths"
  `<details>` containing a boxed equation and a variable legend; `scroll-margin-top`
  on sections so anchor jumps clear the sticky header.
- **Adapt:** the mockup hand-rolls fractions with a `.frac` class and STIX Two
  Text. The brief mandates **KaTeX or an equivalent**, replace hand-rolled
  fractions with real KaTeX so superscripts, subscripts, Greek letters and aligned
  equations render correctly. Every technical term used elsewhere must have a
  matching anchor here (the mockup only covers a subset, expand to the full metric
  list in the brief). Each equation gets: equation, plain-English explanation,
  variable legend, worked example where helpful, interpretation, limitations.
- **Reject:** the `.frac` / STIX approach; `title`-only tooltips.

### `Overview-print.html`, ADAPT (report only)

- A print/report-oriented variant of Overview. **Adapt** its ideas only for the
  portfolio report / report-cover work in Phase 7 (not a live app surface).

---

## Design-system bundle verdicts

| System | Verdict | Why |
|---|---|---|
| **modernist** (red on white, Archivo, flat) | **ADAPT, primary influence** | Closest to the brief: a single red accent on a light ground, disciplined flush-left type, tabular data, restraint. Adopt its *philosophy* (red used sparingly, ink-on-ground, themed focus rings, accent tonal ramp) but **soften** its zero radius and heavy 2px rules into the brief's restrained radius, fewer/subtler borders and calmer spacing. Its accent `#ec3013` is replaced by the brief's `#E50C0E`. |
| **industry** (steel-blue blueprint) | **REJECT** | Wireframe crosshairs, condensed type and a blue accent conflict with the calm, red-accented brief. |
| **broadsheet** (newsprint serif, CMYK) | **REJECT** | Serif body and CMYK spot colour contradict the modernist sans-serif and single-red direction. |

**Borrowed conventions (all three systems share these, and they are adopted):**
themed interaction states (every interactive element gets a hover tint + pressed
step from the accent ramp), a `:focus-visible { outline: 2px solid accent; offset:
2px }` keyboard ring (never the default blue), an accent tint for `::selection`,
disabled at reduced opacity, and a 100–900 perceptual tonal ramp per role so tints
and pressed states are consistent. The brief's own rule that red never carries
meaning alone, and that accent-on-ground is only ≥3:1 (fine for chrome/large text,
not body copy, use a deep red step for red body text) is taken directly from the
modernist/industry readmes.

---

## Consolidated design decisions carried into Phase 2

1. **Layout:** centered max-width shell (~1440px content, ~1280px reading), 48px
   desktop gutters collapsing on mobile; 72–76px sticky header; generous vertical
   rhythm.
2. **Palette:** warm-neutral page ground, white surfaces, one red accent used only
   for active nav, primary actions, selected controls and key signals; neutral
   slate as the chart comparison colour; green/red used for up/down only alongside
   a sign or arrow, never colour alone.
3. **Type:** Geist Sans (Inter fallback) via `next/font`; tabular numerals for all
   data; monospace only for raw identifiers.
4. **Radius:** restrained, cards ~12–14px, inputs ~10px, pills 999px for
   tags/badges only.
5. **Cards:** white, one hairline border (subtler than the mockup's), `shadow-sm`,
   a gentle hover lift; no gradients, glow or glass.
6. **Components to build once and reuse:** metric-help tooltip, stat tile, signal
   strength meter, STRONG/MODERATE/WEAK badge, guided select, labelled slider,
   "Show the maths" expander, data-mode selector, disclaimer banner, KaTeX
   equation block with legend.
7. **Interaction & a11y:** keyboard-operable tooltips (hover + focus + touch), red
   `:focus-visible` ring everywhere, semantic headings, ARIA on controls,
   reduced-motion support.
8. **Maths:** KaTeX rendering; plain-English first, equations behind "Show the
   maths" or in Methodology; every cross-referenced term anchored in Methodology.
</invoke>
