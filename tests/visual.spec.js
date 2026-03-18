// @ts-check
// Generic visual regression test for any DOE project.
// Takes a full-page screenshot and compares against Playwright's built-in baseline.

const { test, expect } = require('@playwright/test');
const { getConfig, getAppPath, runInitScript } = require('./helpers');

const config = getConfig();
const APP_PATH = getAppPath();

test.describe('Visual regression', () => {
  test('main page matches baseline screenshot', async ({ page }) => {
    await runInitScript(page);

    const firstRoute = (config.routes || [])[0];
    const url = firstRoute ? `${APP_PATH}#${firstRoute.hash}` : APP_PATH;
    await page.goto(url);
    await page.waitForTimeout(1500);

    // Disable animations for deterministic screenshots
    await page.addStyleTag({
      content: '*, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }',
    });
    await page.waitForTimeout(200);

    await expect(page).toHaveScreenshot('main-page.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });
});
