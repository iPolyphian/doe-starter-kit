# Directive: Context Management

## Goal
Maximise agent effectiveness by treating context as the scarcest resource. Every irrelevant token degrades performance.

## When to Use
Loaded when working in parallel, managing context limits, recovering from compaction, or scaling from solo to multi-terminal work.

## Core Principle
Every terminal is an independent pipeline: load context -> build -> verify contracts -> commit -> next step. Scale by opening more terminals, not by cramming more into one. The DAG executor automates this; solo mode approximates it through discipline.

## Post-Compaction Recovery

After context compaction, the thin router (CLAUDE.md) is all the agent retains. Without explicit recovery, the agent proceeds with degraded memory of rules it once read.

**Recovery procedure:**
1. Treat ALL directives as unloaded -- do not assume you remember their contents
2. Identify which triggers in CLAUDE.md apply to your current task
3. Re-read those directives before your next action
4. In wave/DAG mode: also re-read your step assignment and ownership list from todo.md
5. Check STATE.md for current position and any blockers

**Why this matters:** A compacted agent that skips recovery may violate guardrails it previously loaded, miss triggers it previously knew about, or duplicate work already completed. The 1% rule (CLAUDE.md) applies with extra force after compaction -- if there's any chance a directive applies, load it.

## Neutral Prompt Discipline

Use Neutral Prompts when evaluating your own work. Never self-congratulate ("this looks great!") or assume success. Instead: state what you did, state what you verified, state what remains. Let the verification results speak.

Bad: "I've successfully implemented a beautiful solution."
Good: "Created the API route. Contract criteria 1-3 pass. Criterion 4 untested -- requires running server."

## Solo

Standard single-terminal work. Context discipline matters most here because you carry the full conversation history.

**Session blocking:** For large features (5+ steps), plan which steps to tackle per session. A fresh `/clear` between groups of steps prevents context degradation. If you notice yourself re-reading the same files or making mistakes on things you previously knew, the context is too polluted -- recommend `/clear`.

**One task, one session:** Don't let conversations drift. If the user pivots to an unrelated topic, recommend `/clear` before continuing. Unrelated context is dead weight.

**Progressive Disclosure:** Only load directives when triggered. Reading all directives "just in case" defeats the purpose of the thin router. Trust the trigger table.

## Informal Parallel

2-3 terminals on independent tasks. Each terminal is its own independent pipeline -- no coordination protocol needed.

**Shared-file awareness:** The only coordination rule: don't edit STATE.md, learnings.md, todo.md, or CLAUDE.md from multiple terminals simultaneously. If you need to update a shared file, check whether another terminal might be mid-edit.

**No step ownership needed:** Informal parallel is for genuinely independent tasks (e.g. one terminal builds a feature, another researches a bug). If tasks touch overlapping files, upgrade to Formal Parallel.

## Formal Parallel

DAG executor (`execution/dispatch_dag.py`) or serial dispatch (`directives/serial-dispatch-protocol.md`). Step ownership via `Owns:` metadata in todo.md. Every step declares which files it will modify.

**Mechanical collision prevention:**
- Pre-commit hooks in each worktree enforce the ownership list -- agents cannot commit files outside their `Owns:` declaration
- Shared files (CLAUDE.md, STATE.md, todo.md, learnings.md) are off-limits to all parallel agents
- The executor's merge phase is the only code that touches shared files

**Contract-gated chaining:** A step's dependents only start after the step passes ALL its contract criteria. Failed steps retry (up to 3x) without blocking independent steps. Blocked steps escalate to the human.

**Integration contracts:** After a wave of parallel steps merges, integration contracts verify cross-step consistency. These are written during planning alongside step contracts.

**The independent pipeline principle:** Each terminal running a step gets a fresh session with minimal context: the step contract, the `Owns:` list, relevant plan sections, and the directives triggered by its task. No cross-terminal state sharing. No shared memory between agents. This is the ideal: maximum context quality, minimum context pollution.

**Recovery after merge:** When parallel steps merge into the feature branch, the coordinator:
1. Runs integration contracts on the merged result
2. Updates todo.md with completion status
3. Identifies the next wave of eligible steps
4. Dispatches or continues serially based on user preference
