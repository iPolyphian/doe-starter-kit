// @ts-check
// Shared test helpers for DOE projects.
// All project-specific config comes from tests/config.json.

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, 'config.json');
const STATE_PATH = path.join(__dirname, '..', 'STATE.md');

/**
 * Load and return the test config from tests/config.json.
 * Returns an empty object if the file is missing.
 */
function getConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
  } catch {
    return {};
  }
}

/**
 * Build the app URL path from config.appPrefix + STATE.md version.
 * Example: appPrefix "my-app" + version "1.2.3" => "/my-app-v1.2.3"
 * Falls back to "/" if neither is available.
 */
function getAppPath() {
  const config = getConfig();
  const prefix = config.appPrefix || '';

  // Try to extract version from STATE.md (looks for "v1.2.3" pattern)
  let version = '';
  try {
    const state = fs.readFileSync(STATE_PATH, 'utf-8');
    const match = state.match(/v(\d+\.\d+\.\d+)/);
    if (match) version = match[1];
  } catch {
    // No STATE.md — that's fine
  }

  if (prefix && version) return `/${prefix}-v${version}`;
  if (prefix) return `/${prefix}`;
  return '/';
}

/**
 * If config.initScript is set, inject it into the page before navigation.
 * The initScript string is evaluated as raw JS in the browser context.
 */
async function runInitScript(page) {
  const config = getConfig();
  if (config.initScript) {
    await page.addInitScript(config.initScript);
  }
}

module.exports = { getConfig, getAppPath, runInitScript };
