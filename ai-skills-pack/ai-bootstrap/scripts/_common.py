"""ai-bootstrap 脚本公共函数。"""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from string import Template

# 默认支持的工具 → 配置目录映射。
# Cursor 和 Codex 使用本工具包约定的项目目录；Claude Code 不固定 rules/skills 子目录，由执行者按项目事实判断。
TOOL_CONFIGS = {
    "cursor": {"config_dir": ".cursor", "rules_subdir": "rules", "rule_ext": ".mdc", "skills_subdir": "skills"},
    "codex": {"config_dir": ".codex", "rules_subdir": "rules", "rule_ext": ".md", "skills_subdir": "skills"},
    "claude-code": {"config_dir": ".claude", "rules_subdir": "", "rule_ext": ".md", "skills_subdir": ""},
}


def resolve_config_dir(config_dir_arg: str | None) -> str:
    """按优先级确定配置目录：命令行参数 > 环境变量。"""
    if config_dir_arg:
        return config_dir_arg
    env = os.environ.get("AI_TOOL_CONFIG_DIR")
    if env:
        return env
    raise SystemExit("缺少配置目录。请先判断目标工具，再显式传入 --config-dir，例如 --config-dir .codex 或 --config-dir .cursor。")


def tool_config_for(config_dir: str) -> dict[str, str]:
    """根据 config_dir 返回对应的工具配置（规则后缀等）。"""
    for _tool, cfg in TOOL_CONFIGS.items():
        if cfg["config_dir"] == config_dir:
            return cfg
    return {"config_dir": config_dir, "rules_subdir": "", "rule_ext": ".md", "skills_subdir": ""}


def tool_name_for_config_dir(config_dir: str) -> str | None:
    """根据配置目录返回工具名称。"""
    for tool_name, cfg in TOOL_CONFIGS.items():
        if cfg["config_dir"] == config_dir:
            return tool_name
    return None


def skill_root() -> Path:
    """解析 skill 安装根目录。"""
    env = os.environ.get("AI_SKILL_ROOT") or os.environ.get("CURSOR_SKILL_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def preset_dir(preset: str, override: str | None = None) -> Path:
    if override:
        p = Path(override).resolve()
        if not p.is_dir():
            raise SystemExit(f"未找到 --preset-dir 指定的目录：{p}")
        return p
    p = skill_root() / "templates" / "presets" / preset
    if not p.is_dir():
        fallback = skill_root() / "templates" / "presets" / "generic-docs"
        if not fallback.is_dir():
            raise SystemExit(f"未找到预设：{preset}，且没有可用默认预设")
        return fallback
    return p


def render_template(text: str, mapping: dict[str, str]) -> str:
    safe = {k: ("" if v is None else str(v)) for k, v in mapping.items()}
    return Template(text).safe_substitute(safe)


def write_draft(target: Path, content: str) -> Path:
    """用 .draft 后缀写入草稿，拒绝覆盖正式文件。"""
    if target.exists() and not str(target).endswith(".draft"):
        raise SystemExit(f"拒绝覆盖已有正式文件：{target}")
    if not str(target).endswith(".draft"):
        target = target.with_name(target.name + ".draft")
    if target.exists():
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = target.with_name(target.name + f".{ts}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def today() -> str:
    return _dt.date.today().isoformat()
