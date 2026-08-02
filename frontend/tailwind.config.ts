import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "media",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        astro: {
          bg: "#0C0F16",
          panel: "#151A24",
          border: "#232C3B",
          text: "#E7ECF5",
          muted: "#93A0B4",
          brass: "#E7B24C",
          positive: "#46C7A8",
          negative: "#F27289",
        },
        "astro-light": {
          bg: "#F7F9FC",
          panel: "#FFFFFF",
          border: "#DDE3ED",
          text: "#141A24",
          muted: "#5B6779",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "var(--font-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      borderRadius: {
        instrument: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
