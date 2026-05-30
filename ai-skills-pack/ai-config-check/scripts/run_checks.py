#!/usr/bin/env python3
"""人工智能规范七层体检脚本。

Usage:
  python3 run_checks.py <project_root> [--config-dir <dir>] [--output results.json]

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


TOOL_CONFIGS = {
    ".cursor": {"rules_subdir": "rules", "rule_ext": ".mdc", "skills_subdir": "skills"},
    ".codex": {"rules_subdir": "rules", "rule_ext": ".md", "skills_subdir": "skills"},
    ".claude": {"rules_subdir": "", "rule_ext": ".md", "skills_subdir": ""},
}

CONSTITUTION_NAMES = [
    "AGENTS.md",
    "CLAUDE.md",
    "CODEX.md",
    "GEMINI.md",
    "COPILOT.md",
    "CURSOR.md",
    ".github/copilot-instructions.md",
]

CONTEXT_ENTRIES = [
    "README.md",
    "README.rst",
    "readme.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs",
    "doc",
]

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "vendor",
    "target",
}


def resolve_config_dir(value: str | None) -> str:
    if value:
        return value
    env = os.environ.get("AI_TOOL_CONFIG_DIR")
    if env:
        return env
    raise SystemExit("缺少配置目录。请先判断目标工具，再显式传入 --config-dir，例如 --config-dir .codex 或 --config-dir .cursor。")


def tool_config(config_dir: str) -> dict[str, str]:
    return TOOL_CONFIGS.get(config_dir, {"rules_subdir": "", "rule_ext": ".md", "skills_subdir": ""})


def read_text(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text if limit is None else text[:limit]


def line_count(path: Path) -> int:
    return len(read_text(path).splitlines()) if path.is_file() else 0


def list_existing(root: Path, candidates: list[str]) -> list[str]:
    found: list[str] = []
    seen: set[tuple[int, int] | Path] = set()
    for name in candidates:
        p = root / name
        if not p.exists():
            continue
        try:
            stat = p.stat()
            key: tuple[int, int] | Path = (stat.st_dev, stat.st_ino)
        except OSError:
            key = p
        if key in seen:
            continue
        seen.add(key)
        found.append(name)
    return found


def status_for_score(score: int, conflict: bool = False) -> str:
    if conflict:
        return "冲突"
    if score >= 80:
        return "已具备"
    if score <= 0:
        return "缺失"
    return "需补齐"


def finding(issue: str, severity: str, detail: str, fix: str) -> dict[str, str]:
    return {"issue": issue, "severity": severity, "detail": detail, "fix": fix}


def layer_result(label: str, score: int, findings: list[dict[str, str]], evidence: dict[str, Any], conflict: bool = False) -> dict[str, Any]:
    score = max(0, min(100, score))
    return {
        "label": label,
        "status": status_for_score(score, conflict=conflict),
        "score": score,
        "evidence": evidence,
        "findings": findings,
    }


def scan_constitutions(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in CONSTITUTION_NAMES:
        p = root / name
        if p.is_file():
            text = read_text(p)
            out[name] = {
                "lines": len(text.splitlines()),
                "chars": len(text),
            }
    return out


def scan_rules(root: Path, config_dir: str) -> tuple[list[Path], Path]:
    cfg = tool_config(config_dir)
    if not cfg["rules_subdir"]:
        return [], root / config_dir
    rules_dir = root / config_dir / cfg["rules_subdir"]
    if not rules_dir.is_dir():
        return [], rules_dir
    return sorted(rules_dir.glob(f"*{cfg['rule_ext']}")), rules_dir


def scan_skills(root: Path, config_dir: str) -> tuple[list[Path], Path | None]:
    cfg = tool_config(config_dir)
    subdir = cfg["skills_subdir"]
    if not subdir:
        return [], None
    skills_dir = root / config_dir / subdir
    if not skills_dir.is_dir():
        return [], skills_dir
    skills = [p for p in sorted(skills_dir.iterdir()) if p.is_dir() and (p / "SKILL.md").is_file()]
    return skills, skills_dir


def scan_make_targets(root: Path) -> list[str]:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return []
    targets: list[str] = []
    for raw in read_text(makefile, limit=40000).splitlines():
        m = re.match(r"^([A-Za-z0-9_\-./]+)\s*:(?!=)", raw)
        if not m:
            continue
        name = m.group(1)
        if name.startswith(".") or name in {"all", "default"}:
            continue
        targets.append(name)
    return targets[:50]


def scan_npm_scripts(root: Path) -> list[str]:
    pkg = root / "package.json"
    if not pkg.is_file():
        return []
    try:
        data = json.loads(read_text(pkg, limit=200000) or "{}")
    except json.JSONDecodeError:
        return []
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return []
    return list(scripts.keys())[:50]


def scan_scripts_dir(root: Path) -> list[str]:
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return []
    return [
        p.name
        for p in sorted(scripts_dir.iterdir())
        if p.is_file() and p.suffix in {".sh", ".py", ".js", ".ts"}
    ][:50]


def scan_ci(root: Path) -> dict[str, Any]:
    workflows = root / ".github" / "workflows"
    github = []
    if workflows.is_dir():
        github = [
            str(p.relative_to(root))
            for p in sorted(workflows.iterdir())
            if p.is_file() and p.suffix in {".yml", ".yaml"}
        ][:50]
    return {
        "github_workflows": github,
        "gitlab_ci": (root / ".gitlab-ci.yml").is_file(),
        "jenkinsfile": (root / "Jenkinsfile").is_file(),
    }


def infer_validation_commands(root: Path, make_targets: list[str], npm_scripts: list[str]) -> list[str]:
    commands: list[str] = []
    for target in ("test", "lint", "vet", "build", "check"):
        if target in make_targets:
            commands.append(f"make {target}")
    for target in ("test", "lint", "typecheck", "build"):
        if target in npm_scripts:
            commands.append(f"npm run {target}")
    if (root / "go.mod").is_file():
        commands.extend(["go test ./...", "go vet ./...", "go build ./..."])
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        commands.append("python -m pytest")

    deduped: list[str] = []
    seen: set[str] = set()
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            deduped.append(cmd)
    return deduped


def check_constitution(root: Path) -> dict[str, Any]:
    constitutions = scan_constitutions(root)
    findings: list[dict[str, str]] = []
    if not constitutions:
        return layer_result("宪法", 0, [
            finding("缺少项目级宪法入口", "high", "没有发现 AGENTS.md 或类似项目级人工智能协作入口。", "运行 ai-bootstrap 生成 AGENTS.md.draft，审阅后再激活。")
        ], {"constitutions": {}})

    primary = next(iter(constitutions))
    text = read_text(root / primary)
    score = 55
    checks = [
        ("事实源", ["事实源", "source of truth", "主源"]),
        ("边界", ["禁止", "不得", "边界", "不要"]),
        ("验证", ["验证", "test", "build", "check"]),
        ("交付", ["交付", "结果", "证据"]),
        ("目录", ["目录", "结构", "路径"]),
    ]
    covered = []
    for label, keywords in checks:
        if any(k.lower() in text.lower() for k in keywords):
            covered.append(label)
            score += 9
        else:
            findings.append(finding(
                f"宪法缺少“{label}”相关约定",
                "medium",
                f"{primary} 中未识别到 {label} 相关关键词。",
                f"在 {primary} 或 supplement 中补充 {label} 规则。",
            ))

    if constitutions[primary]["chars"] < 500:
        score -= 20
        findings.append(finding(
            "宪法内容偏短",
            "medium",
            f"{primary} 只有 {constitutions[primary]['chars']} 字符，可能不足以指导 AI 稳定工作。",
            "生成 AGENTS.md.supplement.draft，补齐项目事实、边界和交付标准。",
        ))

    return layer_result("宪法", score, findings, {"constitutions": constitutions, "covered_topics": covered})


def check_rules(root: Path, config_dir: str) -> dict[str, Any]:
    rules, rules_dir = scan_rules(root, config_dir)
    findings: list[dict[str, str]] = []
    if config_dir == ".claude":
        constitutions = scan_constitutions(root)
        evidence = {"规则承载": "CLAUDE.md / AGENTS.md / 项目事实", "rules_dir": "不固定"}
        if constitutions:
            return layer_result("规范", 70, [
                finding(
                    "Claude Code 规则承载未固定",
                    "low",
                    "本工具包不为 Claude Code 固定 rules/skills 子目录；当前检测到项目级入口，规范层可先由该入口承载。",
                    "由执行者按 Claude Code 和当前项目事实判断是否需要 CLAUDE.md、.claude/ 或其他承载。",
                )
            ], evidence)
        return layer_result("规范", 0, [
            finding(
                "缺少 Claude Code 项目规范入口",
                "high",
                "未发现 AGENTS.md、CLAUDE.md 或类似项目级入口，且 Claude Code 不使用本工具包固定 rules 目录。",
                "运行 ai-bootstrap 生成 AGENTS.md.draft、CLAUDE.md.draft 或待确认问题，审阅后再激活。",
            )
        ], evidence)
    if not rules:
        return layer_result("规范", 0, [
            finding("缺少规则目录或规则文件", "high", f"未发现 {rules_dir} 下的规则文件。", "生成最小规则集：项目指南、编码规则、计划优先、提交/验证规则。")
        ], {"rules_dir": str(rules_dir), "rules": []})

    score = 55 + min(len(rules), 5) * 7
    missing_frontmatter = []
    missing_trigger = []
    long_rules = []
    for rule in rules:
        text = read_text(rule)
        if config_dir != ".codex" and not text.startswith("---"):
            missing_frontmatter.append(rule.name)
        if config_dir == ".codex":
            if "适用范围" not in text and "默认加载" not in text:
                missing_trigger.append(rule.name)
        elif "globs" not in text and "alwaysApply" not in text:
            missing_trigger.append(rule.name)
        if len(text.splitlines()) > 150:
            long_rules.append(rule.name)

    if missing_frontmatter:
        score -= min(len(missing_frontmatter) * 8, 25)
        findings.append(finding(
            "部分规则缺少 frontmatter",
            "medium",
            ", ".join(missing_frontmatter[:5]),
            "为规则补 description 和触发条件。",
        ))
    if missing_trigger:
        score -= min(len(missing_trigger) * 5, 20)
        findings.append(finding(
            "部分规则缺少触发范围",
            "medium",
            ", ".join(missing_trigger[:5]),
            "Cursor 规则补充 globs 或 alwaysApply；Codex 规则补充适用范围或默认加载说明。",
        ))
    if long_rules:
        score -= 10
        findings.append(finding(
            "部分规则过长",
            "low",
            ", ".join(long_rules[:5]),
            "拆分长规则，按主题保留可执行内容。",
        ))

    return layer_result("规范", score, findings, {"rules_dir": str(rules_dir), "rules": [r.name for r in rules]})


def check_context(root: Path, constitutions_layer: dict[str, Any]) -> dict[str, Any]:
    entries = list_existing(root, CONTEXT_ENTRIES)
    findings: list[dict[str, str]] = []
    score = 0
    if entries:
        score = 55 + min(len(entries), 4) * 10
    else:
        findings.append(finding(
            "缺少上下文入口",
            "high",
            "未发现 README、docs、贡献说明或安全说明。",
            "补 README / docs 入口，并在宪法中说明人工智能助手应先读哪些材料。",
        ))

    constitution_evidence = constitutions_layer.get("evidence", {}).get("constitutions", {})
    if constitution_evidence:
        score += 10
    if entries and len(entries) < 2:
        score -= 15
        findings.append(finding(
            "上下文入口偏少",
            "medium",
            f"仅发现：{', '.join(entries)}。",
            "补充 docs / CONTRIBUTING / 架构说明等入口，或在宪法中写清文档路由。",
        ))

    return layer_result("上下文", score, findings, {"context_entries": entries})


def check_tools(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    make_targets = scan_make_targets(root)
    npm_scripts = scan_npm_scripts(root)
    scripts_dir = scan_scripts_dir(root)
    ci = scan_ci(root)
    evidence = {
        "make_targets": make_targets,
        "npm_scripts": npm_scripts,
        "scripts_dir": scripts_dir,
        "ci": ci,
    }
    findings: list[dict[str, str]] = []
    count = len(make_targets) + len(npm_scripts) + len(scripts_dir)
    score = 0
    if count:
        score = 60 + min(count, 6) * 5
    if ci["github_workflows"] or ci["gitlab_ci"] or ci["jenkinsfile"]:
        score += 10
    if not count:
        findings.append(finding(
            "缺少可执行工具入口",
            "medium",
            "未发现 Makefile target、package scripts 或 scripts 目录脚本。",
            "补充常用构建、测试、检查命令，并在规范中说明何时使用。",
        ))
    elif score < 80:
        findings.append(finding(
            "工具入口偏基础",
            "low",
            "已发现部分命令入口，但脚本、CI 或命令说明仍不完整。",
            "补充持续集成工作流、脚本说明或 Makefile 注释，让人工智能助手知道何时使用这些命令。",
        ))
    return layer_result("工具", score, findings, evidence), evidence


def check_guardrails(root: Path, config_dir: str, tools_evidence: dict[str, Any]) -> dict[str, Any]:
    hooks = list_existing(root, [
        ".pre-commit-config.yaml",
        ".husky",
        f"{config_dir}/hooks.json",
        f"{config_dir}/hooks",
    ])
    ignores = list_existing(root, [".gitignore", ".cursorignore", ".dockerignore"])
    ci = tools_evidence["ci"]
    has_ci = bool(ci["github_workflows"] or ci["gitlab_ci"] or ci["jenkinsfile"])
    findings: list[dict[str, str]] = []
    score = 0
    if hooks:
        score += 45
    if has_ci:
        score += 35
    if ignores:
        score += 15
    if not hooks and not has_ci:
        findings.append(finding(
            "缺少人工智能外部强制护栏",
            "high",
            "未发现 hook、pre-commit、CI 或类似自动拦截机制。",
            "把关键禁令升级为 hook、持续集成必要校验、权限或审批策略。",
        ))
    elif has_ci and not hooks:
        findings.append(finding(
            "护栏主要依赖 CI",
            "medium",
            "发现 CI，但缺少本地写入前 / 提交前拦截。",
            "为密钥、生成文件、运行时配置等高风险动作补 hook 或 pre-commit。",
        ))

    return layer_result("护栏", score, findings, {"hooks": hooks, "ignore_files": ignores, "ci": ci})


def check_verification(root: Path, tools_evidence: dict[str, Any]) -> dict[str, Any]:
    commands = infer_validation_commands(root, tools_evidence["make_targets"], tools_evidence["npm_scripts"])
    findings: list[dict[str, str]] = []
    score = 0
    if commands:
        score = 60 + min(len(commands), 5) * 8
    else:
        findings.append(finding(
            "缺少验证命令线索",
            "high",
            "未识别到 test / build / lint / check 等验证入口。",
            "补充验证矩阵，说明不同变更后应执行哪些命令。",
        ))
    if commands and not any("test" in c for c in commands):
        score -= 15
        findings.append(finding(
            "验证入口缺少测试命令",
            "medium",
            "已发现验证命令，但没有 test 类命令。",
            "补充测试命令或说明为什么当前项目无需测试。",
        ))
    return layer_result("验证", score, findings, {"commands": commands})


def check_skills(root: Path, config_dir: str) -> dict[str, Any]:
    skills, skills_dir = scan_skills(root, config_dir)
    findings: list[dict[str, str]] = []
    if config_dir == ".claude":
        return layer_result("技能", 70, [
            finding(
                "Claude Code 技能承载未固定",
                "low",
                "本工具包不为 Claude Code 固定项目 skill 目录。",
                "由执行者按项目事实判断；无法确认时先写待确认问题，不要套用 Cursor 或 Codex 目录。",
            )
        ], {"技能承载": "CLAUDE.md / AGENTS.md / 用户确认的技能目录", "skills_dir": "不固定"})
    if skills_dir is None:
        return layer_result("技能", 100, [], {"skills_dir": None, "skills": [], "note": "当前配置不使用 skill 目录"})
    if not skills:
        if config_dir == ".codex":
            return layer_result("技能", 0, [
                finding(
                    "缺少 Codex 规则检查 skill",
                    "medium",
                    f"未发现 {skills_dir} 下的技能，Codex 无法依赖 Cursor 式自动规则触发。",
                    "运行 ai-bootstrap 为 Codex 生成 .codex/skills/rules-check/SKILL.md.draft，审阅后激活。",
                )
            ], {"skills_dir": str(skills_dir), "skills": []})
        return layer_result("技能", 0, [
            finding("缺少技能或标准流程沉淀", "medium", f"未发现 {skills_dir} 下的技能。", "识别复杂高频流程，先生成候选清单，再按需生成技能草稿。")
        ], {"skills_dir": str(skills_dir), "skills": []})

    score = 55 + min(len(skills), 5) * 8
    missing_desc = []
    for skill in skills:
        text = read_text(skill / "SKILL.md", limit=1000)
        if not text.startswith("---") or "description:" not in text:
            missing_desc.append(skill.name)
    if missing_desc:
        score -= min(len(missing_desc) * 12, 30)
        findings.append(finding(
            "部分 skill 缺少 description",
            "medium",
            ", ".join(missing_desc[:5]),
            "补充能稳定触发的 description。",
        ))
    if config_dir == ".codex" and "rules-check" not in {s.name for s in skills}:
        score -= 20
        findings.append(finding(
            "缺少 Codex rules-check skill",
            "medium",
            "已发现 Codex skill 目录，但没有 rules-check 入口。",
            "补充 .codex/skills/rules-check/SKILL.md，让 Codex 每次任务前显式读取 AGENTS.md 和 .codex/rules。",
        ))
    return layer_result("技能", score, findings, {"skills_dir": str(skills_dir), "skills": [s.name for s in skills]})


def summarize(layers: dict[str, dict[str, Any]]) -> dict[str, int]:
    out = {"已具备": 0, "需补齐": 0, "缺失": 0, "冲突": 0}
    for layer in layers.values():
        out[layer["status"]] += 1
    return out


def priority_actions(layers: dict[str, dict[str, Any]]) -> list[str]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    items: list[tuple[int, int, str]] = []
    for idx, layer in enumerate(layers.values()):
        for f in layer.get("findings", []):
            rank = severity_rank.get(f.get("severity", "low"), 2)
            text = f"{layer['label']}：{f['fix']}"
            items.append((rank, idx, text))
    items.sort(key=lambda x: (x[0], x[1]))
    seen: set[str] = set()
    out: list[str] = []
    for _, _, text in items:
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= 5:
            break
    return out


def grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="人工智能规范七层体检")
    parser.add_argument("project_root")
    parser.add_argument("--config-dir", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv[1:])

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    config_dir = resolve_config_dir(args.config_dir)

    constitution = check_constitution(root)
    rules = check_rules(root, config_dir)
    context = check_context(root, constitution)
    tools, tools_evidence = check_tools(root)
    guardrails = check_guardrails(root, config_dir, tools_evidence)
    verification = check_verification(root, tools_evidence)
    skills = check_skills(root, config_dir)

    layers = {
        "constitution": constitution,
        "rules": rules,
        "context": context,
        "tools": tools,
        "guardrails": guardrails,
        "verification": verification,
        "skills": skills,
    }
    total = round(sum(layer["score"] for layer in layers.values()) / len(layers), 1)
    output = {
        "project": root.name,
        "project_root": str(root),
        "config_dir": config_dir,
        "timestamp": datetime.now().isoformat(),
        "model": "seven-layer ai config check",
        "total_score": total,
        "grade": grade(total),
        "summary": summarize(layers),
        "layers": layers,
        "priority_actions": priority_actions(layers),
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入：{out}")
    else:
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
