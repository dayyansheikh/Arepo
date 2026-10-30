import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

// Lightweight unit-test runner for pure frontend logic (no DOM needed). The `@`
// alias mirrors tsconfig so tests import modules the same way the app does.
export default defineConfig({
  // Automatic JSX runtime so a test may server-render a component (tsconfig keeps "preserve" for Next).
  esbuild: { jsx: "automatic" },
  resolve: {
    alias: { "@": resolve(__dirname, ".") },
  },
  test: {
    include: ["lib/**/*.test.ts"],
    environment: "node",
  },
});
