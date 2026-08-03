import type { Config } from "tailwindcss";

// Arepo design tokens. The canonical palette is `arepo.*`; the `astro.*` /
// `astro-light.*` keys are thin aliases kept only so components still compiling
// against the old names inherit the new palette during migration. See
// docs/brand-system.md for the authoritative token table, and lib/theme.ts for
// the same values exposed to chart (Recharts/SVG) code.
const arepo = {
  bg: "#F7F6F4", // warm-grey page ground
  surface: "#FFFFFF", // cards, panels, header
  surface2: "#F4F2EF", // table headers, subtle fills, hover
  border: "#E7E4DF", // hairline borders (default, subtle)
  borderStrong: "#D6D2CB", // dividers that need to read
  ink: "#101010", // primary text
  ink2: "#3A3A38", // secondary copy
  muted: "#6B6862", // labels, captions, muted copy
  accent: "#E50C0E", // Arepo red
  accentHover: "#C40B0C",
  accentActive: "#A50A0B", // pressed; red text on light
  accentFg: "#FFFFFF",
  accentTint: "#FDECEC",
  accentBorder: "#F5C9C9",
  pos: "#1C7C54", // up / positive (always paired with a sign/arrow)
  neg: "#C0392B", // down / negative
  series2: "#546A7B", // neutral comparison chart series
};

const config: Config = {
  // Light-only identity (see DECISIONS R7); no dark variant.
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        arepo,
        // Legacy aliases → Arepo values (migration scaffolding).
        astro: {
          bg: arepo.bg,
          panel: arepo.surface,
          border: arepo.border,
          text: arepo.ink,
          muted: arepo.muted,
          brass: arepo.accent,
          positive: arepo.pos,
          negative: arepo.neg,
        },
        "astro-light": {
          bg: arepo.bg,
          panel: arepo.surface,
          border: arepo.border,
          text: arepo.ink,
          muted: arepo.muted,
        },
      },
      fontFamily: {
        sans: [
          "var(--font-geist-sans)",
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "var(--font-geist-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      borderRadius: {
        instrument: "10px", // legacy alias, retuned to the new md radius
        card: "14px",
        control: "10px",
      },
      boxShadow: {
        "arepo-sm": "0 1px 2px rgba(16,16,16,0.04)",
        "arepo-card": "0 1px 2px rgba(16,16,16,0.04)",
        "arepo-hover": "0 6px 20px rgba(16,16,16,0.07)",
      },
      maxWidth: {
        shell: "1440px",
        reading: "760px",
      },
    },
  },
  plugins: [],
};

export default config;
