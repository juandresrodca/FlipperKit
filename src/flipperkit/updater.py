"""Self-update: pull newer commits when FlipperKit was installed from a git clone.

The git-inspection logic depends only on a small ``run(*args) -> (code, output)``
callable, so it can be driven by real git or by a fake in tests — the same
dependency-injection approach used in :mod:`flipperkit.backup`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

GitRunner = Callable[..., Tuple[int, str]]


def repo_root() -> Path:
    """The clone's root (…/FlipperKit), two levels above this package."""
    return Path(__file__).resolve().parents[2]


def git_runner(root: Path) -> GitRunner:
    """A runner that shells out to ``git -C <root> ...``."""

    def run(*args: str) -> Tuple[int, str]:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()

    return run


def is_git_repo(run: GitRunner) -> bool:
    code, out = run("rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def current_branch(run: GitRunner) -> Optional[str]:
    code, out = run("rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if code == 0 and out.strip() != "HEAD" else None


def remote_url(run: GitRunner) -> Optional[str]:
    code, out = run("remote", "get-url", "origin")
    return out.strip() if code == 0 and out.strip() else None


def working_tree_dirty(run: GitRunner) -> bool:
    code, out = run("status", "--porcelain")
    return bool(out.strip())


def short_sha(run: GitRunner, ref: str = "HEAD") -> str:
    code, out = run("rev-parse", "--short", ref)
    return out.strip() if code == 0 else "?"


def ahead_behind(run: GitRunner, branch: str) -> Optional[Tuple[int, int]]:
    """Return ``(ahead, behind)`` relative to ``origin/<branch>``, or None."""
    code, out = run("rev-list", "--left-right", "--count", f"HEAD...origin/{branch}")
    if code != 0 or not out.strip():
        return None
    parts = out.split()
    if len(parts) != 2:
        return None
    return int(parts[0]), int(parts[1])


@dataclass
class UpdateStatus:
    is_repo: bool
    branch: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    dirty: bool = False
    local: str = "?"
    remote: Optional[str] = None
    fetched: bool = True
    fetch_error: Optional[str] = None


def check(run: GitRunner) -> UpdateStatus:
    """Fetch from origin (GitHub) and compare HEAD against its upstream.

    Does not modify the working tree. ``fetched`` is False when the network
    fetch failed, so the caller can avoid falsely reporting "up to date" from
    stale local refs.
    """
    if not is_git_repo(run):
        return UpdateStatus(is_repo=False)
    branch = current_branch(run) or "main"
    url = remote_url(run)
    code, out = run("fetch", "origin", "--quiet")
    fetched = code == 0
    counts = ahead_behind(run, branch)
    ahead, behind = counts if counts else (0, 0)
    return UpdateStatus(
        is_repo=True,
        branch=branch,
        ahead=ahead,
        behind=behind,
        dirty=working_tree_dirty(run),
        local=short_sha(run),
        remote=url,
        fetched=fetched,
        fetch_error=None if fetched else out,
    )


def pull(run: GitRunner) -> Tuple[bool, str]:
    """Fast-forward to the upstream. Returns ``(ok, message)``."""
    code, out = run("pull", "--ff-only")
    return code == 0, out
