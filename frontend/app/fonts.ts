import localFont from "next/font/local";

/**
 * Display heading typeface. The Arepo wordmark
 * (`design-assets/brand/AREPO Typeface (word).png`) is a wide-tracked, all-caps,
 * geometric monoline sans (perfect-circle O, triangular A apex, Futura lineage).
 * No exact licensed match ships in the assets, so we vendor Jost (SIL OFL, a
 * Futura revival) locally and use it in uppercase with wide tracking for major
 * titles only. This is a documented approximation, not an exact match — see
 * docs/brand-system.md. Vendored (not next/font/google) so builds need no network.
 */
export const displayFont = localFont({
  src: [
    { path: "./fonts/Jost-Medium.woff2", weight: "500", style: "normal" },
    { path: "./fonts/Jost-SemiBold.woff2", weight: "600", style: "normal" },
    { path: "./fonts/Jost-Bold.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-display",
  display: "swap",
  fallback: ["Futura", "Century Gothic", "system-ui", "sans-serif"],
});
