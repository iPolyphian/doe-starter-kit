// @ts-check
// Generic page load tests for any DOE project.
// Route-specific tests are driven by tests/config.json — no hardcoded pages.

const { test, expect } = require('@playwright/test');
const { getConfig, getAppPath, runInitScript } = require('./helpers');

const config = getConfig();
const APP_PATH = getAppPath();

test.beforeEach(async ({ page }) => {
  await runInitScript(page);
});

test.describe('App load', () => {
  test('page loads without JS errors', async ({ page }) => {
    const errors = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', err => errors.push(err.message));

    const firstRoute = (config.routes || [])[0];
    const url = firstRoute ? `${APP_PATH}#${firstRoute.hash}` : APP_PATH;
    await page.goto(url);
    await page.waitForTimeout(1500);

    // Filter benign network errors (favicon, 404s, etc.)
    const serious = errors.filter(e =>
      !e.includes('favicon') && !e.includes('Failed to load resource') &&
      !e.includes('net::ERR') && !e.includes('404')
    );
    expect(serious, `JS errors: ${serious.join('; ')}`).toHaveLength(0);
  });

  test('page has a title', async ({ page }) => {
    const firstRoute = (config.routes || [])[0];
    const url = firstRoute ? `${APP_PATH}#${firstRoute.hash}` : APP_PATH;
    await page.goto(url);
    await page.waitForTimeout(500);
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });
});

// Route tests: only run if config.json defines routes
if (config.routes && config.routes.length > 0) {
  test.describe('Route rendering', () => {
    for (const route of config.routes) {
      test(`${route.label || route.hash} page renders`, async ({ page }) => {
        await runInitScript(page);
        await page.goto(`${APP_PATH}#${route.hash}`);
        await page.waitForTimeout(1200);

        const pageEl = page.locator(`#${route.pageId}`);
        await expect(pageEl).toBeAttached();
      });
    }
  });
}
