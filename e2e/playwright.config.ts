import { defineConfig, devices } from "@playwright/test";

/**
 * Pruebas E2E de M3.
 *
 * Todo corre contra el stack real de Docker Compose (PostgreSQL, Keycloak,
 * migraciones, seed y API). El frontend se levanta aparte con `PW_WEBSERVER=1`
 * o se reutiliza uno ya iniciado.
 *
 * Variables relevantes:
 *   API_URL   base de la API (por defecto http://localhost:8080/api/v1)
 *   UI_URL    base del frontend (por defecto http://localhost:3000)
 *   PW_WEBSERVER=1  Playwright arranca `npm run dev` del frontend
 */
const API_URL = process.env.API_URL ?? "http://localhost:8080/api/v1";
const UI_URL = process.env.UI_URL ?? "http://localhost:3000";
const levantarFrontend = process.env.PW_WEBSERVER === "1";

export default defineConfig({
  testDir: "./tests",
  outputDir: "./test-results",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  // Un solo worker: los tests comparten PostgreSQL, Keycloak y el seed.
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    trace: "on-first-retry",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "es-AR",
    timezoneId: "America/Argentina/Buenos_Aires",
  },
  projects: [
    {
      name: "api",
      testDir: "./tests/api",
      use: { baseURL: API_URL },
    },
    {
      name: "ui",
      testDir: "./tests/ui",
      use: { ...devices["Desktop Chrome"], baseURL: UI_URL },
    },
  ],
  webServer: levantarFrontend
    ? {
        command: "npm run dev --prefix frontend",
        cwd: "..",
        url: UI_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
      }
    : undefined,
});
