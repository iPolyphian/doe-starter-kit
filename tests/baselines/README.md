# Test Baselines

Baseline files record known states so tests can detect **regressions** without failing on pre-existing issues.

## Files

- **a11y-known.json** -- Known accessibility violations. The a11y spec fails only if critical violations *exceed* this count. As you fix issues, lower `total_known_critical` toward 0.
- **lighthouse.json** -- Lighthouse performance score baseline. Update after significant performance work.

## Updating Baselines

1. Fix the underlying issue (don't just bump the number).
2. Run the tests to confirm the fix: `npx playwright test`.
3. Update the baseline file to reflect the new (lower) count.
4. Commit the baseline change alongside the fix.

For visual regression baselines (screenshot PNGs), Playwright stores those separately in the test-results directory. Update them with `npx playwright test --update-snapshots`.
