# Glossary

A reference for every term you'll encounter working with DOE and Claude Code. If you're new to software development, start here whenever you hit a word you don't recognise.

---

## Git & Version Control

### Repository (repo)

A project folder that git is tracking. It contains your files plus a hidden `.git` folder that stores the complete history of every change ever made. When someone says "clone the repo," they mean "download the project and its full history."

### Commit

A saved snapshot of your project at a specific point in time. Each commit has a message describing what changed ("Fix date parsing for Scottish data"). You can go back to any commit, which makes it possible to undo changes cleanly. Think of commits as save points in a video game.

### Branch

A parallel version of your project. The main branch (usually called `main`, or `master` in older repos) is the primary version. You can create other branches to work on features without affecting the main version, then merge them back when the work is done. DOE typically works on a single branch for simplicity.

### Push / Pull

**Push** sends your local commits to a remote server (like GitHub) so they're backed up and others can see them. **Pull** downloads new commits from the remote server to your local machine. Push is uploading; pull is downloading.

### Clone

Copying an entire repository from a remote server to your local machine. Unlike downloading a ZIP file, cloning preserves the full git history and the connection to the remote, so you can push and pull changes afterwards.

### Merge

Combining changes from one branch into another. If you built a feature on a separate branch, merging brings those changes into the main branch. Most merges happen automatically. Occasionally two branches change the same lines — that's a "merge conflict" and requires a human decision about which version to keep.

### Diff

The difference between two versions of a file. A diff shows exactly which lines were added, removed, or changed. Git diffs use `+` for added lines and `-` for removed lines. When Claude shows you what it changed, it's usually showing a diff.

### Tag / Version tag

A permanent label attached to a specific commit, typically used to mark releases. If commit `a1b2c3d` is the point where you released version 1.0, you'd tag it `v1.0`. Tags don't move — they're bookmarks in your project's history.

### Git hook

A script that runs automatically when a specific git event happens. For example, a pre-commit hook runs before every commit and can check for problems (like accidentally committing an API key). If the hook fails, the commit is blocked. DOE uses hooks to enforce code hygiene.

---

## DOE Framework

### DOE (Directive, Orchestration, Execution)

The three-layer architecture that structures how Claude Code works on your project. Directives are the instructions, orchestration is Claude making decisions, and execution is deterministic scripts doing the work. The separation ensures AI handles reasoning while reliable code handles mechanics.

### Directive

A plain-English instruction document stored in the `directives/` folder. Directives are like Standard Operating Procedures — they tell Claude how to handle specific types of tasks, what to watch out for, and what "done" looks like. They contain no code, only intent.

### Orchestration

The decision-making layer — Claude itself. When you give Claude a task, it reads the relevant directives, checks what scripts exist, decides what order to do things in, and calls the right tools. This is where AI reasoning belongs: making judgment calls and understanding context.

### Execution script

A Python script in the `execution/` folder that performs a specific mechanical task: fetching data from an API, transforming a file, running a calculation. Execution scripts are deterministic — same inputs, same outputs, every time. No AI interpretation, no variation.

### Session

One continuous conversation with Claude Code, from when you start it to when you close it or run `/wrap`. Each session has access to the project's memory files and can read/write code. DOE is designed so that sessions can pick up where the last one left off.

### Contract

A set of testable criteria attached to a task step that define what "done" means. Contracts remove ambiguity — instead of "build the import script," a contract says "the script exists, it runs without errors, and it produces a file with 650 records." Each criterion is tagged as either auto-verifiable or manual.

### Auto criteria ([auto])

Contract criteria that can be checked by running a command or inspecting a file. Claude verifies these automatically after completing a step. Example: `Verify: run: python3 execution/test_import.py` or `Verify: file: src/data/results.json exists`.

### Manual criteria ([manual])

Contract criteria that require a human to check — typically visual or experiential things like "the chart looks correct" or "the page loads without layout glitches." Claude can't verify these, so it collects them and presents them for you to test at the end of a feature.

### Verify pattern

The specific format used in contract criteria to define how something gets checked. Four forms exist: `run:` (execute a command), `file: ... exists` (check a file is present), `file: ... contains` (check a file has specific content), and `html: ... has` (check HTML output). These patterns are executable — Claude runs them, not just reads them.

### Awaiting Sign-off

The state a feature enters when all code is complete and automated checks pass, but manual checks (visual layout, interaction quality) still need human verification. Features stay here until you test and confirm all manual items.

### Self-annealing

DOE's system for learning from failure. When something goes wrong, Claude records the root cause and prevention in the project's learnings files. Over time, the project accumulates immunity to its own failure patterns. Named after the metallurgical process of strengthening metal through heating and cooling cycles.

### Progressive disclosure

The principle of only loading information when it's needed. Claude doesn't read every directive at the start of every session — that would waste context. Instead, CLAUDE.md contains triggers: "if you're importing data, read the data import directive." Claude loads the right information at the right time.

### Governed document

A file with special rules about when and how it must be updated. In DOE, files like `learnings.md`, `data-governance.md`, and `legal-framework.md` are governed — they have front-matter defining their purpose and update triggers. Claude checks whether governed docs need updating before every commit.

---

## Project Files

### CLAUDE.md

The project's instruction manual, loaded automatically at every session start. Contains operating rules, guardrails, directory structure, and triggers for loading directives. Think of it as the constitution — it defines how Claude should behave in this project. It rarely changes.

### STATE.md

Short-term memory. A snapshot of what's happening right now: current feature, recent progress, blockers, next steps. Claude updates this when you run `/wrap` at the end of a session. Next session, it reads STATE.md to pick up where things left off.

### learnings.md

Long-term memory. Patterns discovered over the life of the project — API quirks, bug fixes, decisions and their rationale. Kept concise (around 50 lines). When Claude encounters a situation similar to a past failure, it checks here first to avoid repeating mistakes.

### tasks/todo.md

The active work tracker. Contains four sections: Current (what's being built now), Queue (approved tasks waiting), Awaiting Sign-off (code-complete features waiting for manual verification), and Done (completed work). Each task has numbered steps with contracts that define "done" in testable terms. This is where day-to-day progress is tracked.

### ROADMAP.md

Product-level planning. Ideas flow through stages: Ideas, Must Plan, Up Next, Current, Complete. While todo.md tracks *how* a feature is being built (steps and contracts), ROADMAP.md tracks *what* should be built and in what order.

### directives/

The folder containing all directive files — plain-English SOPs that tell Claude how to handle specific types of tasks. Each directive covers a domain (data import, UI building, documentation, testing) and is loaded automatically when Claude detects a matching task.

### execution/

The folder containing deterministic Python scripts. These are the mechanical tools Claude calls to do actual work — API calls, data transforms, file operations, builds. They run the same way every time and don't depend on AI reasoning.

### .claude/

A folder for Claude Code configuration: hooks, settings, plans, and custom slash commands. Plans for complex features live in `.claude/plans/`. Custom commands (like `/wrap` or `/audit`) live in `.claude/commands/`. This is the project's control infrastructure.

---

## Claude Code

### Claude Code (the CLI tool)

Anthropic's official command-line interface for working with Claude on code projects. You run it in a terminal, give it tasks in natural language, and it reads, writes, and runs code in your project. DOE is a framework built on top of Claude Code that adds structure, memory, and verification.

### Slash command

A command you type in Claude Code that starts with `/`. Examples: `/wrap` ends a session and updates memory files. `/clear` resets the conversation. Some slash commands are built into Claude Code; others are custom commands defined in your project's `.claude/commands/` folder.

### Hook (PreToolUse / PostToolUse)

Code that runs automatically before or after Claude uses a tool. A PreToolUse hook runs before Claude writes a file, executes a command, or takes any action — it can block the action if something is wrong. A PostToolUse hook runs after the action completes and can trigger follow-up tasks. Hooks are defined in `.claude/settings.json`.

### Subagent

A separate Claude instance spawned by the main conversation to handle a specific task. The main Claude sends the subagent a focused brief ("read these 3 files and write a summary"), the subagent does the work, and the result comes back. This keeps the main conversation's context clean. Subagents don't see the full project — only what they're given.

### Wave (multi-agent)

A way to run multiple Claude Code sessions in parallel, each working on a different task in its own isolated copy of the codebase. Useful for building several independent features at once. A coordinator merges the results when all tasks are done. Advanced usage — not needed for most projects.

### Context window

The amount of text Claude can "see" at once in a single conversation. Think of it as Claude's working memory — everything in the conversation (your messages, code it's read, tool outputs) takes up space in the context window. When it fills up, older content gets pushed out. DOE's progressive disclosure system helps manage this by only loading information when it's needed.

### API key

A secret string that acts as a password for accessing a service. Your Claude Code API key authenticates you with Anthropic's servers. Other API keys might connect to data sources, cloud services, or third-party tools. API keys are stored in `.env` and must never appear in code or git history.

### MCP (Model Context Protocol)

A standard for connecting Claude Code to external tools and data sources. MCP servers give Claude new capabilities — reading from a database, browsing the web, interacting with an IDE. Each MCP connection is configured in your project or global settings. Think of MCP as USB ports for Claude: plug in a tool, and Claude can use it.

---

## General Development

### Terminal / Command line

A text-based interface for controlling your computer. Instead of clicking icons, you type commands. The terminal is where you run Claude Code, git commands, and Python scripts. On macOS it's called Terminal (or iTerm2). On Windows it's Command Prompt, PowerShell, or Windows Terminal.

### CLI (Command Line Interface)

Any program you interact with by typing commands in a terminal rather than clicking buttons in a window. Git is a CLI. Claude Code is a CLI. `npm` is a CLI. The alternative is a GUI (Graphical User Interface) — the point-and-click version.

### API (Application Programming Interface)

A way for one program to talk to another. When Claude Code sends your message to Anthropic's servers and gets a response back, it's using an API. When an execution script fetches election data from a government website, it's using that website's API. APIs are how software systems exchange information.

### npm (Node Package Manager)

A tool for installing JavaScript packages (pre-built code libraries). Claude Code is installed using npm (`npm install -g @anthropic-ai/claude-code`). You don't need to know JavaScript to use npm — it's just the delivery mechanism for getting Claude Code onto your machine.

### Script

A file containing code that performs a task when you run it. In DOE, scripts live in `execution/` and are written in Python. You run them with `python3 execution/script_name.py`. Unlike applications that stay open, scripts run, do their job, and finish.

### Build

The process of assembling source files into the final output. In a web project, this might mean combining multiple JavaScript files into one, compiling stylesheets, or generating HTML from templates. DOE projects typically have a `build.py` script that produces the final deliverable.

### Deploy

Making your project available to users. For a website, deploying means uploading it to a server where people can visit it. For a data tool, deploying might mean publishing results to a shared location. Deployment is the step between "it works on my machine" and "other people can use it."

### Monolith

A single self-contained file that bundles everything together. In DOE web projects, the build process often produces a monolith HTML file — one file containing all the HTML, CSS, JavaScript, and data needed for the entire application. No server required — just open the file in a browser.

### CRUD

An acronym for Create, Read, Update, Delete — the four basic operations for managing data. Most applications are fundamentally CRUD operations with a user interface on top. If you can create records, view them, edit them, and remove them, you've covered the basics.
