// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  outputDir: 'test-results',
  // Config uses file output for orchestrator (run_test_suite.py reads the file).
  // Command-line --reporter=json overrides to stdout for Verify: patterns.
  reporter: [['html'], ['json', { outputFile: '.tmp/playwright-results.json' }]],
  timeout: 30000,

  use: {
    baseURL: 'http://localhost:8080',
    viewport: { width: 1280, height: 720 },
    headless: true,
    // Capture on failure only
    screenshot: 'only-on-failure',
    video: 'off',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    // Note: `serve` strips .html extensions via redirect.
    // Use URL path without .html in tests (e.g. /your-app-v1.0.0)
    command: 'npx serve . -p 8080 --no-clipboard',
    url: 'http://localhost:8080',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
