"""Shared utilities for DOE coordination scripts.

Used by: multi_agent.py, heartbeat.py, context_monitor.py
"""

from pathlib import Path


def resolve_project_root():
    """Detect whether cwd is a git worktree and resolve the main project root.

    In a worktree, .git is a file containing 'gitdir: /path/to/main/.git/worktrees/name'.
    In the main repo, .git is a directory.

    Returns:
        (main_root, worktree_root) tuple of Path objects.
        If not in a worktree, both are the same.
        Falls back to cwd if not in a git repo.
    """
    cwd = Path.cwd()
    git_path = cwd / ".git"

    if git_path.is_file():
        # Worktree: .git is a file like "gitdir: /main/repo/.git/worktrees/task-name"
        try:
            content = git_path.read_text().strip()
            if content.startswith("gitdir:"):
                gitdir = Path(content.split(":", 1)[1].strip())
                if not gitdir.is_absolute():
                    gitdir = (cwd / gitdir).resolve()
                # gitdir is like /main/repo/.git/worktrees/task-name
                # Walk up to find the .git dir, then its parent is the main root
                # Pattern: .git/worktrees/<name> -> go up 2 levels to .git, then up 1 to repo
                if "worktrees" in gitdir.parts:
                    wt_idx = list(gitdir.parts).index("worktrees")
                    # Everything before 'worktrees' is the .git dir
                    git_dir = Path(*gitdir.parts[:wt_idx])
                    main_root = git_dir.parent
                    return main_root, cwd
        except (OSError, ValueError, IndexError):
            pass
        # Fallback: can't parse .git file
        return cwd, cwd

    if git_path.is_dir():
        # Main repo
        return cwd, cwd

    # Not in a git repo — fall back to cwd
    return cwd, cwd
