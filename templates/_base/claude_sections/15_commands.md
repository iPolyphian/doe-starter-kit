## Common Commands
```bash
# Verify task contracts
python3 execution/verify.py

# Run DOE methodology health check
python3 execution/test_methodology.py

# Project health check (stubs, TODOs, empty functions)
python3 execution/health_check.py

# Quality gate (mid-feature checkpoint / pre-retro)
python3 execution/quality_gate.py --checkpoint
python3 execution/quality_gate.py --pre-retro

# Run execution script tests
pytest tests/execution/ -q

# Activate git hooks
git config core.hooksPath .githooks

# Create PR from feature branch
gh pr create --title "..." --body "..."
```

## Gotchas
- **Warning:** Never commit `.env` files — credentials must stay local. The pre-commit hook blocks this, but note: the hook only works if `git config core.hooksPath .githooks` has been run.
- **Caveat:** After context compaction, Claude loses all loaded directives. Always re-read the triggers relevant to your current task after a `/clear` or long conversation.
- **Workaround:** If a pre-commit hook fails with "not executable", run `chmod +x .githooks/*` to fix permissions.
- **Note:** `execution/` scripts are deterministic — same input, same output. Never add randomness, API calls, or interactive prompts to them. AI reasoning belongs in orchestration (CLAUDE.md + directives), not execution.
