# Active Task List
<!--
FORMAT RULES (Claude: follow these when updating this file)
- This file tracks immediate work only. Long-term roadmap lives in ROADMAP.md.
- Sections: ## Current (one active feature), ## Awaiting Sign-off (all [auto] pass, [manual] pending), ## Pending PRs (open PRs waiting to merge), ## Queue (approved, not started), ## Done (completed, keep for audit)
- **## Awaiting Sign-off**: When a feature's final code step completes (all [auto] criteria pass) but unchecked `[manual]` items remain, move the feature block here. The user tests manually, reports pass/fail, and failures get fixed before moving to ## Done. Features stay in this section until all [manual] criteria are checked off. Multiple features can await sign-off simultaneously.
- **## Pending PRs**: Tracks open PRs that are code-complete but not yet merged to main. **Oldest first** (lowest PR number at top). This section stores ONLY static data -- things that don't change unless the PR itself changes. Live data (merge status, commits behind main, CI status, current conflicts) is computed and displayed by session commands (stand-up, crack-on, wrap) when they run, never written to this file.
  **Entry format**: heading with PR number + feature name, bold summary line (merge order, step count, manual items, readiness), "Contains" one-liner (what changes when this merges), detail table (URL, branch, created, manual items, known conflicts), and post-merge checklist with `[ ]` items that get ticked during the merge procedure.
  **"Next to merge" pointer**: first line of the section names the PR that should merge next. Updated when merge order changes.
  When a PR merges, execute its post-merge checklist, then remove the entry. When a new PR is created during retro, add an entry here. If 2+ PRs conflict on shared files, note known conflicts and merge order.
- Each feature gets a heading, short description, and numbered steps
- Each feature heading includes a type tag: [APP] for changes users see, [INFRA] for tooling/workflow/dev improvements
- Complex features (3+ steps): link to the full design in .claude/plans/ -- e.g. "Plan: .claude/plans/feature-name.md". Wrap steps in `<details><summary>Steps (0-N)</summary>...</details>` so they collapse in GitHub/editors.
- Steps are numbered. Each step scoped to one shippable patch -- one commit, one push
- **Task contracts** are mandatory for every step. Every task added to todo.md gets a `Contract:` block with at least one `[auto]` criterion. No exceptions.
  Format:
  N. [ ] Step name -> vX.Y.Z
    Contract:
    - [ ] [auto] Description. Verify: [executable pattern]
    - [ ] [manual] Description of what the human should check
    Agent cannot mark the step done until all contract items pass /agent-verify.
  **`[auto]` criteria** must use one of these executable Verify: patterns:
    - `Verify: run: <shell command>` -- execute, check exit code 0
    - `Verify: file: <path> exists` -- check file existence
    - `Verify: file: <path> contains <string>` -- check file content for substring
    - `Verify: html: <path> has <selector>` -- parse HTML, check CSS selector (requires BeautifulSoup)
    Anything not matching a pattern is flagged invalid during /agent-launch pre-flight.
  **`[manual]` criteria** describe what the human should check visually/behaviourally. No Verify: method. Before marking a criterion `[manual]`, ask: could a machine determine pass/fail? If the answer involves checking a count, verifying a file exists, or comparing a value -- write it as `[auto]` with a `Verify:` pattern instead. Only keep `[manual]` for things that genuinely need human eyes: visual quality, content clarity, interaction feel, subjective judgment.
  **Rules:** Every task must have at least one `[auto]` criterion. `[APP]` tasks must also have at least one `[manual]` criterion. `[INFRA]` tasks can be fully `[auto]`.
  System-generated side effects (stats.json, learnings, wave infrastructure) are NOT tasks and don't get contracts.
- **Retro step** is mandatory as the final step of every feature. Format: `N. [ ] Retro`. Quick retros mark as `[x] Retro [quick: nothing to log]` or `[quick: logged to learnings.md]`. Full retros mark as `[x] Retro [full: logged to learnings.md + prevention added]`. Default is quick -- escalate to full when: something failed unexpectedly, approach changed mid-task, a workaround was used, the task touched a repeatable pattern, time significantly exceeded expectation, or you discovered something that would have prevented a past failure. Wave agents mark `[quick: deferred to merge]` or `[full: deferred to merge]`.
- Keep ## Done trimmed to last 3 completed features. Move older ones to tasks/archive.md with all steps and timestamps preserved.
- Progress tracking happens HERE, not in .claude/plans/. Plans are reference docs.
- This format can be changed -- just update these rules and Claude will follow the new convention.
-->

## Current

<!-- No active feature. Run /stand-up to start a session. -->

## Awaiting Sign-off

<!-- Features where all [auto] criteria pass but [manual] items need human testing. Move to ## Done when all checked. -->

## Pending PRs

<!-- Open PRs waiting to merge. Oldest first. Static data only -- live status (mergeable, behind main, CI) computed by session commands, not stored here. -->

## Queue

<!-- Approved features waiting to start. -->

## Done

<!-- Completed features. Keep last 3, archive older ones. -->
