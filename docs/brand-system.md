# Arepo brand & design system

_The single source of truth for Arepo's identity and the design tokens every_
_surface is built from. Phase 1 deliverable; implemented in Phase 2._

## The name

**Arepo** is the connective word of the Sator Square (SATOR AREPO TENET OPERA
ROTAS), the one term believed to have been coined to make the square resolve in
every direction. That is the brand's whole idea.

> Just as Arepo is believed to have been created to unite the Sator Square, we
> unite information as it is created, conviction as it is expressed, action as it
> is taken, and markets as they move. Arepo represents the hidden signal found
> between the lines.

Use the full paragraph only where there is room to earn it (About, How Arepo
Works). Elsewhere use a short form, e.g. *"Arepo reads the hidden signal between
the lines, where information, conviction, action and markets meet."* or simply
*"the hidden signal, read from public markets."*

The engine keeps the internal package name `astrolabe` (Python modules, DB
identifiers, API paths), renaming coupled internals is cosmetic risk with no
user benefit, per the brief. Only user-facing surfaces say Arepo.

## Logo

### Brief

Geometric, legible at 16px, modern, analytical; subtly suggests connection or a
hidden central signal; a four-part structure converging on a central point.
Not a literal Sator Square; nothing mystical or ornamental.

### Concepts explored

Three were drawn and compared at 16px (favicon), 28px (nav) and large (report
cover):

1. **Crosshair node**, four orthogonal ink ticks around a central red dot.
   Clean, but reads as a generic map/target marker at 16px and says little about
   "uniting four parts".
2. **Quadrant aperture**, a rounded square split into four quadrants by a cross
   of negative space, red dot at the meeting point. Strong idea (the hidden
   signal is literally *between the lines*), but the thin negative-space cross
   closes up and muddies below ~20px.
3. **Convergence mark (chosen)**, four short, bold chevrons at N/E/S/W pointing
   inward toward a central red node, each stopping just short of it. The four
   marks are the four things Arepo unites; the gap between them and the node is
   "between the lines"; the red node is the hidden signal they reveal.

### Decision

**Concept 3, the convergence mark.** It survives 16px (a red dot framed by four
ink marks stays distinct), is unmistakably geometric and analytical, encodes the
brand meaning without illustration, and pairs cleanly with a Geist wordmark. The
node is the only red in the mark, which models the rule "red marks the signal".

- **Nav lockup:** mark + `Arepo` wordmark in Geist SemiBold, -0.01em tracking.
- **Favicon:** the mark alone on a transparent ground; a 16×16 and 32×32 SVG
  favicon plus an Apple touch variant on an ink tile with the red node.
- **Report cover:** mark scaled up with the full brand paragraph.

The mark is implemented in `frontend/components/Logo.tsx`
(`LogoMark` + `Logo`) and `frontend/app/icon.svg` / `apple-icon.svg`.

### Grid mark reconstruction (Master Final Refinement)

The supplied logo file (`design-assets/brand/AREPO logo (no word).png`) is a
5x5 grid of cells on black, with the second column and the second row filled
in Arepo red, forming an offset cross, and the remaining cells outlined in
white. `frontend/components/Logo.tsx` (`LogoMark`) is a faithful SVG
reconstruction of that exact grid: same 5x5 layout, same red cells (second
column, second row), same arrangement. Because Arepo's product identity is
light-only (see decision R7 in `DECISIONS.md`), the reconstruction is adapted
for a white ground: the black tile is dropped, the white cell outlines become
a fine ink hairline on a transparent background, and the red cells are
preserved unchanged. This supersedes the earlier "convergence mark" concept
described above, which was the Phase 1 design exploration before the supplied
grid logo asset was integrated directly; the convergence-mark rationale is
kept here as a record of that exploration, but the grid mark is what ships.

## Typography

- **Geist Sans** via `next/font` (`geist/font/sans`), with **Inter** as the
  documented fallback. A modernist sans throughout, per brief.
- **Geist Mono** only for raw identifiers (token IDs, market IDs) and code.
- **Tabular numerals** (`font-variant-numeric: tabular-nums`) on every figure so
  columns and meters align and don't jitter as values change.

### Display heading font (Master Final Refinement)

The written wordmark in `design-assets/brand/AREPO Typeface (word).png` is a
wide-tracked, all-caps, geometric **monoline** sans: a perfect-circle `O`, a
sharp triangular `A` apex, uniform stroke weight throughout, and generous
letter-spacing. This is unmistakably in the Futura / geometric-grotesque
lineage. No licensed font file matching it ships with the supplied assets, so
**no exact match is claimed**.

The closest freely-licensable match is **Jost** (SIL Open Font License), a
direct Futura revival with the same perfect circles and triangular apexes.
Jost is vendored locally (not loaded from Google Fonts at request time) as
static `.woff2` files in `frontend/app/fonts/` and wired up via
`next/font/local` in `frontend/app/fonts.ts` (`displayFont`), so the build
needs no network access and the font is self-hosted. It is set in **uppercase
with wide tracking** (`tracking-[0.22em]` on the wordmark, similarly wide on
page titles) to echo the supplied artwork's spacing.

Scope of use is deliberately narrow, per the brief: the display font appears
only on major page titles, hero headings, major section introductions and
report-cover headings (`PageHeader`, `SectionTitle`, the `Logo` wordmark).
Interface text, navigation labels, cards, forms, tooltips, tables and all data
values stay in Geist Sans; nothing in the ordinary product surface is set in
the display face by default.

**This is stated plainly as an approximation, not an exact match.** Jost
shares the wordmark's genre and proportions closely enough to carry the
brand's geometric, wide-tracked character, but it is a different typeface cut
by a different designer, not a reproduction of the exact glyphs in the
supplied PNG. If an exact licensed match for the wordmark becomes available,
it should replace Jost in `frontend/app/fonts.ts` without changing the token
names (`displayFont`, `--font-display`) that the rest of the interface
depends on.

Type scale (implemented as utilities / component styles):

| Role | Size / weight | Notes |
|---|---|---|
| Page title (h1) | 30–34px / 600 | -0.01em tracking |
| Section heading (h2) | 20–22px / 600 | |
| Section label | 12–13px / 600, uppercase, 0.08em | muted; the eyebrow above card grids and tables |
| Body | 14–15px / 400–450 | 1.6–1.7 line height |
| Label / caption | 11–12px / 500 | muted |
| Data value | 13–15px / 600, tabular | |

## Colour

Light identity. One warm neutral ground, white surfaces, one red accent used
sparingly.

### Roles (implemented as CSS variables in `globals.css`)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#F7F6F4` | warm-grey page ground |
| `--surface` | `#FFFFFF` | cards, panels, header |
| `--surface-2` | `#F4F2EF` | table headers, subtle fills, hover |
| `--border` | `#E7E4DF` | hairline borders (the default, kept subtle) |
| `--border-strong` | `#D6D2CB` | dividers that need to read |
| `--text` | `#101010` | primary ink |
| `--text-secondary` | `#3A3A38` | secondary copy |
| `--text-muted` | `#6B6862` | labels, captions, muted copy |
| `--accent` | `#E50C0E` | **Arepo red**, active nav, primary action, selected control, key signal |
| `--accent-hover` | `#C40B0C` | hover |
| `--accent-active` | `#A50A0B` | pressed; also red text on light (≥ body contrast) |
| `--accent-fg` | `#FFFFFF` | text/icon on a red fill |
| `--accent-tint` | `#FDECEC` | red tint fill (selected row, badge bg) |
| `--accent-border` | `#F5C9C9` | border on tinted red surfaces |
| `--focus` | `#E50C0E` | 2px `:focus-visible` ring, 2px offset |

### Data / semantic colours (never carry meaning alone)

| Token | Value | Use |
|---|---|---|
| `--pos` | `#1C7C54` | up / positive, always paired with a ▲ or `+` sign |
| `--neg` | `#C0392B` | down / negative, always paired with a ▼ or `−` sign |
| `--series-1` | `#E50C0E` | primary chart series (Arepo red) |
| `--series-2` | `#546A7B` | comparison chart series (neutral slate) |
| `--grid` | `rgba(16,16,16,0.06)` | chart gridlines, kept faint |

**Rules (from the brief and the modernist DS readme):** red is for active nav,
primary actions, selected controls and important signals only, never a flood.
The red-on-white pair clears ≥3:1 (fine for chrome and large text); for
red *body-size* text use `--accent-active`. Up/down and good/bad always pair the
colour with a sign, arrow or word so colour is never the only cue.

### Signal strength scale

The 0–100 strength meter fills with `--accent` (the signal colour). STRONG /
MODERATE / WEAK badges are tonal, not three different hues: STRONG uses the red
tint, MODERATE a neutral `--surface-2`, WEAK a fainter neutral, distinguished by
the word, not colour alone.

## Shape, elevation, motion

- **Radius (restrained):** `--radius-sm 6px` (badges/inputs inner), `--radius-md
  10px` (inputs, buttons), `--radius-lg 14px` (cards, panels); `999px` for pills
  (tags/badges) only.
- **Borders:** one hairline per surface; prefer subtle contrast over more lines.
- **Elevation:** `--shadow-sm 0 1px 2px rgba(16,16,16,0.04)`; card hover
  `0 6px 20px rgba(16,16,16,0.07)` with a faint accent-tinted border. No
  gradients, glow, glassmorphism or decorative animation.
- **Motion:** ≤150ms colour/shadow transitions; everything respects
  `prefers-reduced-motion: reduce`.

## Reusable components (built once in Phase 2, consumed everywhere)

`Card`/`.panel`, `Button` (primary/secondary/ghost), `Badge`
(quality + strength tiers), `MetricHelp` (info icon + hover/focus/touch tooltip +
plain-English definition + "Learn more" → Methodology anchor), `StatTile`,
`StrengthMeter`, `Select` (guided dropdown), `Slider` (labelled range),
`Disclose` ("Show the maths" / advanced expander), `ModeSelector` (Live / Cached
/ Replay data-mode control), `DisclaimerBanner`, `Equation` (KaTeX block with
plain-English + variable legend), `TopBar`, `Footer`.

## Accessibility baseline

Semantic heading order; every control labelled; `MetricHelp` operable by hover,
keyboard focus and touch; a 2px red `:focus-visible` ring (never the browser
default) on every interactive element; contrast targets met (body ≥ 4.5:1, chrome
≥ 3:1); charts carry text/table alternatives; targets ≥ 24px; reduced-motion
honoured.
