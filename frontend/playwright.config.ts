import { defineConfig, devices } from "@playwright/test";

/**
 * Real-browser acceptance tests (final runtime acceptance §2, §3, §8). These run the ACTUAL Next app
 * (already-running dev server on :3000, backed by the FastAPI backend on :8000) and assert against
 * real rendered geometry — bounding rectangles, document scrollWidth vs clientWidth — because the
 * pure positioning unit tests passed while the running page still overflowed.
 *
 * Start the servers before running (see docs/FINAL_RUNTIME_ACCEPTANCE.md):
 *   backend:  uvicorn astrolabe.api.app:app --port 8000
 *   frontend: NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
 * or set PW_WEB_SERVER=1 to let Playwright boot the frontend itself.
 */
const BASE_URL = process.env.PW_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  outputDir: "test-results",
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.PW_WEB_SERVER
    ? {
        command: "NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev",
        url: BASE_URL,
        reuseExistingServer: true,
        timeout: 120_000,
      }
    : undefined,
});
