# Directive: Delivery Rules

## Goal
Ensure quality, compliance, and completeness when shipping features -- verification, retros, guardrails, and governance.

## When to Use
Loaded when delivering: retros, PR creation, sign-off, wrap, version bumps, merging, or any pre-ship activity.

## Verify Before Delivering

Verify before delivering: run the script, test the output, confirm it matches the spec. After file edits, `ls`/`cat` to confirm. Neutral prompts only -- no sycophantic self-evaluation.

## Pre-Commit Checks

Check STATE.md, learnings.md, and governed docs before every commit. Update if position/decisions/domain changed. Skip if none apply.

## Pitch Spontaneously

Pitch spontaneously: if you notice a genuine improvement, pitch it briefly. One sentence what, one sentence why. User says "add it" (-> Ideas in ROADMAP.md) or "this is important" (-> Must Plan).

## Pre-Retro Quality Gate

Before starting the retro step on any feature (regardless of size):

1. Run `python3 execution/test_methodology.py --scenario cross_reference_consistency --scenario directive_schema --scenario agent_definition_integrity`
2. If the feature modified shared infrastructure (directives, CLAUDE.md routing, agents, execution scripts): spawn Finder agent to review all files modified during the feature (`git diff --name-only main...HEAD`). The Finder should focus on cross-file consistency and documentation-implementation drift, not individual code correctness.
3. Fix findings before proceeding to retro. Log significant findings to learnings.md.

This gate is the universal safety net. Even if the mid-feature checkpoint in `building-rules.md` was skipped or the feature had fewer than 5 steps, the pre-retro gate catches accumulated drift before it ships.

## Retro Discipline

Retro discipline: every feature gets a mandatory retro as its final step. Includes PR creation via `gh pr create`.

- **Quick** (default): `[x] Retro [quick: nothing to log]` or `[quick: logged to learnings.md]`
- **Full** (escalate when: failure, approach change, workaround, repeatable pattern, time exceeded, prevented past failure): `[x] Retro [full: logged to learnings.md + prevention added]`
- Wave agents defer: `[quick: deferred to merge]` or `[full: deferred to merge]`

### Retro Procedure
1. Rename HTML to final patch version, update nav badge
2. Update changelog -- add final entry to grouped card
3. Update ROADMAP.md: move feature from Up Next to Complete
4. If [APP] feature, add to showcase entries array
5. Update feature heading from (vX.Y.x) to (vX.Y.N)
6. Run brief retro: what worked, what was slow, what to do differently
7. Promote lasting contracts to `tests/invariants.txt`. Auto-promote: any `[auto]` contract whose `Verify:` pattern references files in `CLAUDE.md`, `directives/`, `.claude/agents/`, `execution/`, `.github/workflows/`, `.githooks/`, `SYSTEM-MAP.md`, `CUSTOMIZATION.md`, or `tests/`. Skip version-specific patterns (containing `vX.Y.Z` or HTML filenames). If the feature intentionally changed something an existing invariant tests, update that invariant to reflect the new state.
8. PR creation: `gh pr create` from feature branch to main
9. Move the whole block to ## Done

## IMPORTANT: Guardrails

- **YOU MUST NOT overwrite or delete existing directives without explicit permission.** Propose changes, don't make them. New directives: also add a trigger to CLAUDE.md Progressive Disclosure.
- **YOU MUST NOT store secrets outside `.env`.** No API keys in code, comments, or logs.
- Deliverables go to cloud services (Google Sheets, Slides, etc.) where the user can access them directly.
- Clean up `.tmp/` after tasks complete. Intermediate files are disposable.
- **YOU MUST NOT edit `~/doe-starter-kit` directly.** All changes go through `/sync-doe` (versioning, tagging, releases).
- **YOU MUST NOT force-push, revert commits, or delete branches without explicit permission.** If something needs rolling back, show what you want to revert and why first.
- **When a hook blocks an action, fix it immediately.** Show what was flagged, what you fixed, and proof. Don't just say "I updated the file."
- **Wave agents MUST NOT edit shared files on main** (`todo.md`, `CLAUDE.md`, `learnings.md`, `STATE.md`). Coordinator fixes after `--merge`.

## Performance Budget

The performance budget when shipping to production:
- LCP (Largest Contentful Paint): < 2.5s
- JavaScript bundle: < 300KB (compressed)
- Lighthouse Performance: >= 80
- No render-blocking resources on critical path

Run `npx lighthouse <url> --output=json` or Playwright Lighthouse integration to verify.

## Feature Flag Guidance

Use a feature flag for gradual rollout or toggling without deploying:
- Use Vercel Flags + Edge Config when on the Vercel platform
- Feature flags are especially critical for a political tool where broken features have real consequences
- Add as a step in the deployment plan, not a separate feature
- Default: flag off in production, on in preview

## Staging & Environments

Vercel's model is preview-per-PR, not persistent staging. Each PR gets a unique preview URL for testing. For stakeholders who need a bookmarkable URL to check weekly, use a `staging` Git branch with auto-deploy or a promoted preview. Clarify needs before scoping.

## Delivery-Phase Triggers

These triggers apply during delivery (absorbed from the original CLAUDE.md trigger table):
- Version bump or release -> check `tasks/todo.md` ## Done for the version bump pattern
- Reviewing changes before commit -> suggest `/diff-review`
- Running `/wrap` -> run `python3 execution/health_check.py`, include in wrap summary
- Feature's final code step with unchecked [manual] items -> read `directives/manual-testing.md`, run `python3 execution/generate_test_checklist.py`
- Syncing DOE or updating framework version -> run `python3 execution/scan_docs.py` after sync
- Returning after absence -> suggest `/project-recap`

## Common Delivery Commands
```bash
python3 execution/build.py              # Rebuild monolith HTML from src/
python3 execution/verify.py             # Run contract verification
python3 execution/health_check.py       # Health check (--quick --json)
python3 execution/audit_claims.py       # Audit governed docs (--hook --json)
gh pr create                            # Create PR from feature branch
gh pr list --state open                 # List open PRs
```
