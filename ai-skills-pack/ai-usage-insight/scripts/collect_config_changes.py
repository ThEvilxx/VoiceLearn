#!/usr/bin/env python3
"""Collect recent AI config changes from one repo or a multi-repo workspace.

Outputs JSON to stdout:
  {
    "rules_changed": [...],
    "skills_changed": [...],
    "hooks_changed": [...],
    "agents_md_changed": bool,
    "ai_config_changed": [...],
    "repositories_scanned": [...]
  }

Usage:
  python3 collect_config_changes.py <project_or_workspace_root>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _helpers import get_report_week_start


AI_CONFIG_PREFIXES = (
    "ai-config/",
    "ailearn/ai-config/",
)


def _git_log_paths(root: Path, path_prefix: str, since: str) -> list[str]:
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--since",
                since,
                "--name-only",
                "--pretty=format:",
                "--diff-filter=ACMR",
                "--",
                path_prefix,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return sorted(set(paths))
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def _discover_git_roots(root: Path) -> list[Path]:
    root = root.resolve()
    if (root / ".git").exists():
        return [root]
    repos: list[Path] = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if child.name.startswith("."):
                continue
            if child.is_dir() and (child / ".git").exists():
                repos.append(child)
    return repos


def _display_path(work_root: Path, repo: Path, rel_path: str) -> str:
    try:
        repo_rel = repo.relative_to(work_root)
        if str(repo_rel) == ".":
            return rel_path
        return (repo_rel / rel_path).as_posix()
    except ValueError:
        return rel_path


def _collect_repo_changes(work_root: Path, repo: Path, since: str) -> list[str]:
    prefixes = [
        ".cursor/rules/",
        ".cursor/skills/",
        ".cursor/hooks",
        "AGENTS.md",
        "ai-config/",
    ]
    paths: set[str] = set()
    for prefix in prefixes:
        for rel_path in _git_log_paths(repo, prefix, since):
            paths.add(_display_path(work_root, repo, rel_path))
    return sorted(paths)


def _is_rule_path(path: str) -> bool:
    return "/rules/" in path or path.startswith(".cursor/rules/")


def _is_skill_path(path: str) -> bool:
    return "/skills/" in path or path.endswith("/SKILL.md") or path.endswith("/SKILL.md.disabled")


def _is_hook_path(path: str) -> bool:
    return "/hooks/" in path or path.endswith("/hooks.json") or "/hooks/" in path


def _is_ai_config_path(path: str) -> bool:
    return any(path.startswith(prefix) or f"/{prefix}" in path for prefix in AI_CONFIG_PREFIXES)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法：collect_config_changes.py <项目或工作区根目录>", file=sys.stderr)
        return 2

    work_root = Path(argv[1]).resolve()
    since = get_report_week_start().strftime("%Y-%m-%d")
    repos = _discover_git_roots(work_root)

    all_paths: set[str] = set()
    for repo in repos:
        all_paths.update(_collect_repo_changes(work_root, repo, since))

    paths = sorted(all_paths)
    data = {
        "rules_changed": [p for p in paths if _is_rule_path(p)],
        "skills_changed": [p for p in paths if _is_skill_path(p)],
        "hooks_changed": [p for p in paths if _is_hook_path(p)],
        "agents_md_changed": any(p.endswith("AGENTS.md") for p in paths),
        "ai_config_changed": [p for p in paths if _is_ai_config_path(p)],
        "repositories_scanned": [str(repo) for repo in repos],
        "since": since,
    }
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
