// Playwright config for pulseengine.eu's GDPR / no-third-party-loads watchdog.
//
// Spins up a local static server pointing at public/ (the zola build output),
// then runs the spec which walks every HTML file and checks for external
// network requests. Run `zola build` first; CI does this in the workflow.

const { defineConfig } = require('@playwright/test');

const PORT = 8888;

module.exports = defineConfig({
  testDir: './tests/playwright',

  // Each page gets a few seconds — networkidle settles fast for our static pages.
  timeout: 20 * 1000,

  // Fail loudly in CI; allow .only locally for fast iteration.
  forbidOnly: !!process.env.CI,

  // Don't retry — a flaky external-loads test is meaningful, not noise.
  retries: 0,

  // One reporter is enough; line is concise in CI logs.
  reporter: process.env.CI ? 'github' : 'line',

  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
  },

  webServer: {
    command: `npx http-server public -p ${PORT} --silent`,
    url: `http://127.0.0.1:${PORT}`,
    timeout: 15 * 1000,
    reuseExistingServer: !process.env.CI,
  },
});
