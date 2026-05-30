#!/usr/bin/env python3
"""生成规则草稿。

Usage:
    python3 generate_rules.py <project_root> --preset <name> [--config-dir <dir>] \
        [--preset-dir <dir>] [--profile <profile.json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import preset_dir, render_template, resolve_config_dir, skill_root, today, tool_config_for, tool_name_for_config_dir, write_draft


def _load_profile(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"未找到 --profile 指定的文件：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _write_codex_rules_check_skill(root: Path, config_dir: str, mapping: dict[str, str]) -> list[str]:
    """Codex 项目约定：额外生成规则检查 skill 草稿。"""
    tmpl = skill_root() / "templates" / "tool-targets" / "codex" / "skills" / "rules-check" / "SKILL.md.tmpl"
    if not tmpl.is_file():
        raise SystemExit(f"缺少 Codex rules-check skill 模板：{tmpl}")

    target = root / config_dir / "skills" / "rules-check" / "SKILL.md"
    if target.exists():
        return []
    rendered = render_template(tmpl.read_text(encoding="utf-8"), mapping)
    return [str(write_draft(target, rendered))]


def _render_rule_for_tool(template_text: str, mapping: dict[str, str], tool_name: str) -> str:
    rendered = render_template(template_text, mapping)
    if tool_name != "codex" or not rendered.startswith("---"):
        return rendered

    parts = rendered.split("---", 2)
    if len(parts) < 3:
        return rendered
    meta_text = parts[1]
    body = parts[2].lstrip()
    meta: dict[str, str] = {}
    for raw in meta_text.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')

    lines = ["<!-- Codex 项目规则：由 ai-bootstrap 生成的草稿。 -->"]
    if meta.get("description"):
        lines.append(f"> 说明：{meta['description']}")
    if meta.get("globs"):
        lines.append(f"> 适用范围：`{meta['globs']}`")
    if meta.get("alwaysApply", "").lower() == "true":
        lines.append("> 默认加载：是")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--preset", default="generic-docs")
    parser.add_argument("--preset-dir", default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--config-dir", default=None,
                        help="人工智能配置目录，例如 .codex 或 .cursor；必须由执行者显式填写")
    args = parser.parse_args(argv[1:])

    root = Path(args.project_root).resolve()
    config_dir = resolve_config_dir(args.config_dir)
    tool_cfg = tool_config_for(config_dir)
    tool_name = tool_name_for_config_dir(config_dir) or config_dir
    rules_subdir = tool_cfg.get("rules_subdir", "")
    if not rules_subdir:
        raise SystemExit(
            f"{tool_name} 没有本工具包固定的项目规则目录。"
            "请由执行者按该工具和当前项目事实判断承载方式；"
            "无法确认时只生成 AGENTS.md.supplement.draft、AGENTS.md.draft、CLAUDE.md.draft 或待确认问题。"
        )

    pdir = preset_dir(args.preset, args.preset_dir)
    rules_dir = pdir / "rules"
    if not rules_dir.is_dir():
        raise SystemExit(f"预设缺少 rules/ 子目录：{rules_dir}")

    profile = _load_profile(args.profile)
    mapping = {
        "PROJECT_NAME": profile.get("project_name") or root.name,
        "PROJECT_TYPE": args.preset,
        "ENTRY_FILES": "、".join(f"`{item}`" for item in profile.get("entry_files", [])) or "待补充：关键入口文件",
        "TODAY": today(),
    }

    # 输出到对应工具的规则目录
    target_dir = root / config_dir / rules_subdir
    rule_ext = tool_cfg["rule_ext"]

    written: list[str] = []
    skipped: list[str] = []
    for tmpl in sorted(rules_dir.glob("*.mdc.tmpl")):
        # 模板文件名格式: xxx.mdc.tmpl → 提取基础名
        base_name = tmpl.stem.replace(".mdc", "")  # e.g. "code-style"
        rule_name = base_name + rule_ext  # e.g. "code-style.mdc" or "code-style.md"

        live = target_dir / rule_name
        if live.exists():
            skipped.append(str(live))
            continue
        rendered = _render_rule_for_tool(tmpl.read_text(encoding="utf-8"), mapping, tool_name)
        out = write_draft(live, rendered)
        written.append(str(out))

    written_skills: list[str] = []
    if tool_name == "codex":
        written_skills = _write_codex_rules_check_skill(root, config_dir, mapping)

    print(json.dumps({
        "配置目录": config_dir,
        "规则目录": str(target_dir),
        "规则后缀": rule_ext,
        "已写入草稿": written,
        "已写入技能草稿": written_skills,
        "已跳过正式文件": skipped,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
