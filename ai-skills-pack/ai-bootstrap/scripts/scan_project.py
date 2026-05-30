#!/usr/bin/env python3
"""扫描项目根目录并生成 JSON 画像。

Usage:
    python3 scan_project.py <project_root> [--config-dir <dir>]

Output: JSON to stdout.

Stdlib only — no third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from _common import resolve_config_dir, tool_config_for

PRESET_PRIORITY = ["go-backend", "node-frontend", "python", "generic-docs"]

FRONTEND_DEP_KEYS = ("react", "vue", "next", "vite", "svelte", "nuxt", "@angular/core")

INTERESTING_TOP_FILES = (
    "README.md",
    "README.rst",
    "Makefile",
    "Justfile",
    "Taskfile.yml",
    "package.json",
    "go.mod",
    "go.sum",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "Cargo.toml",
    "pubspec.yaml",
    "Dockerfile",
    "docker-compose.yml",
    ".gitignore",
    ".cursorignore",
    ".dockerignore",
    "CONTRIBUTING.md",
    "SECURITY.md",
)

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "target",
    ".gradle",
}


def _read_text(path: Path, limit: int = 2000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _detect_preset(root: Path, entry_files: list[str]) -> str:
    if "go.mod" in entry_files:
        return "go-backend"
    if "package.json" in entry_files:
        pkg_text = _read_text(root / "package.json", limit=8000).lower()
        if any(dep in pkg_text for dep in FRONTEND_DEP_KEYS):
            return "node-frontend"
    if any(f in entry_files for f in ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "Pipfile")):
        return "python"
    return "generic-docs"


def _scan_top_files(root: Path) -> list[str]:
    found = []
    for name in INTERESTING_TOP_FILES:
        if (root / name).is_file():
            found.append(name)
    return found


def _scan_top_dirs(root: Path, limit: int = 30) -> list[str]:
    out = []
    try:
        for entry in sorted(os.scandir(root), key=lambda e: e.name):
            if entry.is_dir() and entry.name not in IGNORED_DIRS and not entry.name.startswith("."):
                out.append(entry.name)
                if len(out) >= limit:
                    break
    except OSError:
        pass
    return out


def _scan_makefile_targets(root: Path) -> list[dict[str, str]]:
    mk = root / "Makefile"
    if not mk.is_file():
        return []
    targets: list[dict[str, str]] = []
    text = _read_text(mk, limit=20000)
    last_comment: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            last_comment.append(line.lstrip("#").strip())
            continue
        m = re.match(r"^([A-Za-z0-9_\-./]+)\s*:(?!=)", line)
        if m and ":=" not in line:
            target = m.group(1)
            if target.startswith(".") or target in {"all", "default"}:
                last_comment = []
                continue
            desc = " ".join(last_comment).strip()
            targets.append({"name": target, "desc": desc})
            last_comment = []
        elif line.strip() == "":
            last_comment = []
    return targets[:30]


def _scan_npm_scripts(root: Path) -> list[dict[str, str]]:
    pkg = root / "package.json"
    if not pkg.is_file():
        return []
    try:
        data = json.loads(_read_text(pkg, limit=200000) or "{}")
    except json.JSONDecodeError:
        return []
    scripts = data.get("scripts", {})
    return [{"name": k, "desc": v} for k, v in scripts.items()][:30]


def _scan_scripts_dir(root: Path) -> list[dict[str, str]]:
    sd = root / "scripts"
    if not sd.is_dir():
        return []
    out = []
    for entry in sorted(os.scandir(sd), key=lambda e: e.name):
        if entry.is_file() and entry.name.endswith((".sh", ".py", ".js", ".ts")):
            head = _read_text(Path(entry.path), limit=600)
            desc = ""
            for line in head.splitlines()[:15]:
                stripped = line.strip()
                if stripped.startswith(("#", "//", '"""', "'''")):
                    cleaned = stripped.lstrip("#/'\" ").strip()
                    if cleaned and not cleaned.startswith("!"):
                        desc = cleaned
                        break
            out.append({"name": entry.name, "desc": desc})
    return out[:30]


def _count_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _list_dir_items(d: Path, suffix: str = "") -> list[str]:
    if not d.is_dir():
        return []
    items = []
    for entry in sorted(os.scandir(d), key=lambda e: e.name):
        if suffix and not entry.name.endswith(suffix):
            continue
        items.append(entry.name)
    return items


def _list_relative_existing(root: Path, candidates: list[str]) -> list[str]:
    found: list[str] = []
    seen_keys: set[tuple[int, int] | Path] = set()
    for name in candidates:
        p = root / name
        if p.exists():
            try:
                stat = p.stat()
                key: tuple[int, int] | Path = (stat.st_dev, stat.st_ino)
            except OSError:
                key = p
            if key in seen_keys:
                continue
            seen_keys.add(key)
            found.append(name)
    return found


def _scan_ci(root: Path) -> dict[str, Any]:
    workflows = root / ".github" / "workflows"
    github_workflows = []
    if workflows.is_dir():
        github_workflows = [
            str(p.relative_to(root))
            for p in sorted(workflows.iterdir())
            if p.is_file() and p.suffix in {".yml", ".yaml"}
        ][:30]
    return {
        "github_workflows": github_workflows,
        "gitlab_ci": (root / ".gitlab-ci.yml").is_file(),
        "jenkinsfile": (root / "Jenkinsfile").is_file(),
    }


def _scan_guardrails(root: Path, config_dir: str) -> dict[str, Any]:
    tool_cfg = tool_config_for(config_dir)
    hooks_candidates = [
        ".pre-commit-config.yaml",
        ".husky",
        f"{config_dir}/hooks.json",
        f"{config_dir}/hooks",
    ]
    ignore_candidates = [
        ".gitignore",
        ".cursorignore",
        ".dockerignore",
    ]
    ci = _scan_ci(root)
    return {
        "hooks": _list_relative_existing(root, hooks_candidates),
        "ignore_files": _list_relative_existing(root, ignore_candidates),
        "ci": ci,
        "has_ci": bool(ci["github_workflows"] or ci["gitlab_ci"] or ci["jenkinsfile"]),
        "rules_subdir": tool_cfg["rules_subdir"],
    }


def _infer_validation_commands(profile_bits: dict[str, Any]) -> list[str]:
    entry_files = set(profile_bits.get("entry_files") or [])
    scripts = profile_bits.get("scripts") or {}
    commands: list[str] = []

    make_targets = {item.get("name") for item in scripts.get("make_targets", [])}
    for target in ("test", "lint", "vet", "build", "check"):
        if target in make_targets:
            commands.append(f"make {target}")

    npm_scripts = {item.get("name") for item in scripts.get("npm_scripts", [])}
    for target in ("test", "lint", "typecheck", "build"):
        if target in npm_scripts:
            commands.append(f"npm run {target}")

    if "go.mod" in entry_files:
        commands.extend(["go test ./...", "go vet ./...", "go build ./..."])
    if "pyproject.toml" in entry_files or "requirements.txt" in entry_files:
        commands.append("python -m pytest")

    deduped: list[str] = []
    seen: set[str] = set()
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            deduped.append(cmd)
    return deduped


def _status(has: bool, partial: bool = False, conflict: bool = False) -> str:
    if conflict:
        return "冲突"
    if has and partial:
        return "需补齐"
    if has:
        return "已具备"
    return "缺失"


def _build_seven_layer_status(
    existing_ai_config: dict[str, Any],
    scripts: dict[str, Any],
    guardrails: dict[str, Any],
    validation_commands: list[str],
    docs_entries: list[str],
) -> dict[str, dict[str, Any]]:
    constitutions = existing_ai_config.get("constitutions") or {}
    rules_count = existing_ai_config.get("rules_count") or 0
    skills_count = existing_ai_config.get("skills_count") or 0
    hook_count = len(guardrails.get("hooks") or [])
    has_tools = bool(
        scripts.get("make_targets")
        or scripts.get("npm_scripts")
        or scripts.get("scripts_dir")
    )
    has_context = bool(docs_entries or constitutions)

    return {
        "constitution": {
            "label": "宪法",
            "status": _status(
                bool(constitutions),
                partial=bool(constitutions) and min(constitutions.values()) < 40,
            ),
            "evidence": constitutions,
        },
        "rules": {
            "label": "规范",
            "status": _status(rules_count > 0, partial=rules_count in (1, 2)),
            "evidence": {
                "rules_count": rules_count,
                "rules_dir": existing_ai_config.get("rules_dir"),
            },
        },
        "context": {
            "label": "上下文",
            "status": _status(has_context, partial=has_context and len(docs_entries) < 2),
            "evidence": {
                "context_entries": docs_entries,
                "constitution_entries": list(constitutions.keys()),
            },
        },
        "tools": {
            "label": "工具",
            "status": _status(has_tools),
            "evidence": scripts,
        },
        "guardrails": {
            "label": "护栏",
            "status": _status(hook_count > 0 or guardrails.get("has_ci"), partial=guardrails.get("has_ci") and hook_count == 0),
            "evidence": {
                "hooks": guardrails.get("hooks"),
                "ci": guardrails.get("ci"),
                "ignore_files": guardrails.get("ignore_files"),
            },
        },
        "verification": {
            "label": "验证",
            "status": _status(bool(validation_commands)),
            "evidence": validation_commands,
        },
        "skills": {
            "label": "技能",
            "status": _status(skills_count > 0, partial=skills_count in (1, 2)),
            "evidence": {
                "skills_count": skills_count,
                "skills_dir": existing_ai_config.get("skills_dir"),
            },
        },
    }


_AI_CONSTITUTION_NAMES = [
    "AGENTS.md",
    "CLAUDE.md",
    "CODEX.md",
    "GEMINI.md",
    "COPILOT.md",
    "CURSOR.md",
    ".github/copilot-instructions.md",
]

_CONTEXT_ENTRY_NAMES = [
    "README.md",
    "README.rst",
    "readme.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs",
    "doc",
]


def _scan_existing_ai_config(root: Path, config_dir: str) -> dict[str, Any]:
    """扫描已有 AI 配置。"""
    constitutions: dict[str, int] = {}
    for name in _AI_CONSTITUTION_NAMES:
        p = root / name
        if p.is_file():
            constitutions[name] = _count_lines(p)

    # 获取当前工具的配置
    tool_cfg = tool_config_for(config_dir)
    rules_subdir = tool_cfg["rules_subdir"]
    rule_ext = tool_cfg["rule_ext"]
    skills_subdir = tool_cfg["skills_subdir"]

    rules_dir = root / config_dir / rules_subdir
    skills_dir = root / config_dir / skills_subdir if skills_subdir else None

    rules_list = _list_dir_items(rules_dir, rule_ext)
    skills_list = []
    if skills_dir and skills_dir.is_dir():
        skills_list = [
            d.name
            for d in sorted(skills_dir.iterdir())
            if d.is_dir() and (d / "SKILL.md").is_file()
        ]

    result: dict[str, Any] = {
        "config_dir": config_dir,
        "constitutions": constitutions,
        "constitution_count": len(constitutions),
        "rules_dir": str(rules_dir.relative_to(root)) if rules_dir.exists() else None,
        "rules_list": rules_list,
        "rules_count": len(rules_list),
        "skills_dir": str(skills_dir.relative_to(root)) if skills_dir and skills_dir.exists() else None,
        "skills_list": skills_list,
        "skills_count": len(skills_list),
    }
    has_any = len(constitutions) > 0 or len(rules_list) > 0 or len(skills_list) > 0
    result["has_existing_config"] = has_any
    return result


def _readme_summary(root: Path) -> str:
    for name in ("README.md", "README.rst", "readme.md"):
        p = root / name
        if p.is_file():
            text = _read_text(p, limit=600)
            for line in text.splitlines():
                line = line.strip().lstrip("#").strip()
                if line and len(line) > 5:
                    return line[:200]
    return ""


def _scan_context_entries(root: Path) -> list[str]:
    return _list_relative_existing(root, _CONTEXT_ENTRY_NAMES)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--config-dir", default=None,
                        help="人工智能配置目录，例如 .codex 或 .cursor；必须由执行者显式填写")
    args = parser.parse_args(argv[1:])

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    config_dir = resolve_config_dir(args.config_dir)

    entry_files = _scan_top_files(root)
    scripts = {
        "make_targets": _scan_makefile_targets(root),
        "npm_scripts": _scan_npm_scripts(root),
        "scripts_dir": _scan_scripts_dir(root),
    }
    existing_ai_config = _scan_existing_ai_config(root, config_dir)
    context_entries = _scan_context_entries(root)
    guardrails = _scan_guardrails(root, config_dir)
    validation_commands = _infer_validation_commands({
        "entry_files": entry_files,
        "scripts": scripts,
    })
    preset = _detect_preset(root, entry_files)
    profile: dict[str, Any] = {
        "project_name": root.name,
        "project_root": str(root),
        "preset": preset,
        "config_dir": config_dir,
        "entry_files": entry_files,
        "top_dirs": _scan_top_dirs(root),
        "readme_summary": _readme_summary(root),
        "context_entries": context_entries,
        "scripts": scripts,
        "guardrails": guardrails,
        "validation_commands": validation_commands,
        "existing_ai_config": existing_ai_config,
        "seven_layers": _build_seven_layer_status(
            existing_ai_config,
            scripts,
            guardrails,
            validation_commands,
            context_entries,
        ),
    }
    json.dump(profile, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
