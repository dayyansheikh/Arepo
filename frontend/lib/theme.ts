// Arepo palette exposed to chart (Recharts/SVG) code that cannot read Tailwind
// classes. Keep in sync with tailwind.config.ts, app/globals.css and
// docs/brand-system.md.

export const theme = {
  bg: "#F7F6F4",
  surface: "#FFFFFF",
  surface2: "#F4F2EF",
  border: "#E7E4DF",
  borderStrong: "#D6D2CB",
  ink: "#101010",
  ink2: "#3A3A38",
  muted: "#6B6862",
  accent: "#E50C0E",
  accentHover: "#C40B0C",
  accentActive: "#A50A0B",
  accentTint: "#FDECEC",
  accentBorder: "#F5C9C9",
  pos: "#1C7C54",
  neg: "#C0392B",
  series1: "#E50C0E",
  series2: "#546A7B",
  grid: "rgba(16,16,16,0.06)",
} as const;

// Ordered palette for multi-outcome charts: red primary, neutral slate, then
// muted supporting hues that stay clear of the semantic pos/neg colours.
export const seriesColors = [
  theme.series1,
  theme.series2,
  "#B8791F", // amber
  "#4C7A5E", // muted green-slate
  "#7A5C9E", // muted violet
] as const;
