// @ts-check
// Generic accessibility scan for any DOE project.
// Compares critical violations against a baseline in tests/baselines/a11y-known.json.
// Fails only if NEW critical violations exceed the known count.

const { test, expect } = require('@playwright/test');
const { AxeBuilder } = require('@axe-core/playwright');
const fs = require('fs');
const path = require('path');
const { getConfig, getAppPath, runInitScript } = require('./helpers');

const config = getConfig();
const APP_PATH = getAppPath();
const BASELINE_PATH = path.join(__dirname, 'baselines', 'a11y-known.json');

// Load known violations baseline (or default to 0 if no file)
function loadBaseline() {
  try {
    return JSON.parse(fs.readFileSync(BASELINE_PATH, 'utf-8'));
  } catch {
    return { known_violations: [], total_known_critical: 0 };
  }
}

test.describe('Accessibility', () => {
  test('critical violations do not exceed baseline', async ({ page }) => {
    await runInitScript(page);

    const firstRoute = (config.routes || [])[0];
    const url = firstRoute ? `${APP_PATH}#${firstRoute.hash}` : APP_PATH;
    await page.goto(url);
    await page.waitForTimeout(1500);

    const results = await new AxeBuilder({ page }).include('body').analyze();
    const critical = results.violations.filter(v => v.impact === 'critical');
    const baseline = loadBaseline();

    if (critical.length > 0) {
      console.log(
        `[a11y] ${critical.length} critical violation(s) (baseline: ${baseline.total_known_critical}):\n` +
        critical.map(v => `  [critical] ${v.id}: ${v.description} (${v.nodes.length} node(s))`).join('\n')
      );
    }

    expect(
      critical.length,
      `Critical violations increased beyond baseline ${baseline.total_known_critical}. ` +
      `Found: ${critical.map(v => v.id).join(', ')}`
    ).toBeLessThanOrEqual(baseline.total_known_critical);

    // Confirm axe ran successfully
    expect(results.passes.length).toBeGreaterThan(0);
  });
});
