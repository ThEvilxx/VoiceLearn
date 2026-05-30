#!/usr/bin/env python3
"""Generate a seven-layer AI usage insight markdown report.

Usage:
  python3 generate_insight.py --analysis analysis.json [--output path.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _week_label() -> str:
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def _cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", "<br>")


def _join_evidence(values: list[Any]) -> str:
    if not values:
        return "暂无明显信号"
    return "<br>".join(_cell(v) for v in values[:3])


def _format_source_counts(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "无"
    return "，".join(f"{key}: {count}" for key, count in sorted(value.items()))


def _render(analysis: dict[str, Any]) -> str:
    summary = analysis.get("summary", {})
    signals = analysis.get("signals", {})
    repeated = signals.get("repeated_patterns", [])
    failures = signals.get("failure_patterns", {})
    long_tail = signals.get("long_tail", [])
    layers = analysis.get("layer_insights", [])
    actions = analysis.get("priority_actions", [])
    assets = analysis.get("assets", {})
    config = analysis.get("config_changes", {})

    lines: list[str] = []
    w = lines.append

    w(f"# 人工智能使用洞察 - {_week_label()}\n")

    w("## 简单状态\n")
    w("| 项目 | 结果 |")
    w("|---|---|")
    w(f"| 分析范围 | {_cell(summary.get('project_root', '当前项目'))} |")
    w(f"| 对话记录 | {_cell(summary.get('total_conversations', 0))} |")
    w(f"| 项目匹配对话 | {_cell(summary.get('project_matched_conversations', summary.get('total_conversations', 0)))} |")
    w(f"| 未归属对话 | {_cell(summary.get('unscoped_conversations', 0))} |")
    w(f"| 数据来源 | {_cell(_format_source_counts(summary.get('source_counts')))} |")
    w(f"| 总轮次 | {_cell(summary.get('total_rounds', 0))} |")
    w(f"| 平均轮次/对话 | {_cell(summary.get('avg_rounds_per_conversation', 0))} |")
    w(f"| 重试信号 | {_cell(summary.get('retry_conversations', 0))} |")
    w(f"| 长尾对话 | {_cell(summary.get('long_tail_conversations', 0))} |")
    w(f"| 优先优化层 | {_cell(summary.get('top_layer', '数据不足'))}（{_cell(summary.get('top_layer_status', '数据不足'))}） |")
    w("")

    w("## 七层洞察\n")
    w("| 层级 | 状态 | 证据 | 优化建议 |")
    w("|---|---|---|---|")
    for item in layers:
        w(
            "| "
            f"{_cell(item.get('layer'))} | "
            f"{_cell(item.get('status'))} | "
            f"{_join_evidence(item.get('evidence') or [])} | "
            f"{_cell(item.get('suggestion'))} |"
        )
    if not layers:
        w("| 数据不足 | 数据不足 | 未读取到有效对话记录 | 先运行 ai-bootstrap 或 ai-config-check 建立基础状态 |")
    w("")

    w("## 重点信号\n")
    w("### 重复模式\n")
    if repeated:
        for item in repeated[:5]:
            w(f"- {item.get('layer', '上下文')}层：出现 {item.get('count', 0)} 次，`{item.get('representative', '')}`。{item.get('suggestion', '')}")
    else:
        w("- 暂无三次以上的明显重复模式。")
    w("")

    w("### 重试模式\n")
    retry_total = failures.get("total_conversations", 0)
    retry_count = failures.get("retry_conversations", 0)
    retry_rate = failures.get("retry_rate", 0)
    w(f"- 重试率：{retry_rate}%（{retry_count}/{retry_total}）。")
    examples = failures.get("examples") or []
    if examples:
        for item in examples[:3]:
            w(f"- {item.get('layer', '上下文')}层：`{item.get('query_sample', '')}`。{item.get('suggestion', '')}")
    else:
        w("- 暂无明显重试样例。")
    w("")

    w("### 长尾对话\n")
    if long_tail:
        for item in long_tail[:5]:
            w(f"- {item.get('layer', '上下文')}层：{item.get('rounds', 0)} 轮，`{item.get('query_sample', '')}`。{item.get('suggestion', '')}")
    else:
        w("- 暂无超过 15 轮的长尾对话。")
    w("")

    w("## 当前基础状态\n")
    w("| 项目 | 数量/状态 |")
    w("|---|---|")
    w(f"| 宪法入口 | {assets.get('constitution_count', 0)} |")
    w(f"| 规则文件 | {assets.get('rules_count', 0)} |")
    w(f"| 上下文入口 | {len(assets.get('context_entries') or [])} |")
    w(f"| 验证入口 | {len(assets.get('validation_entries') or [])} |")
    w(f"| 护栏入口 | {'有' if assets.get('has_hooks') else '无'} |")
    w(f"| 技能入口 | {assets.get('skills_count', 0)} |")
    w("")

    changed_total = sum(
        len(config.get(key) or [])
        for key in ["rules_changed", "skills_changed", "hooks_changed", "ai_config_changed"]
    )
    if config.get("agents_md_changed"):
        changed_total += 1
    w("## 近期配置变更\n")
    if changed_total:
        w(f"- 本期检测到 {changed_total} 项人工智能配置相关变更。建议优先复查这些变更是否已经降低重复、重试或长尾信号。")
    else:
        w("- 本期未检测到明显人工智能配置变更。")
    w("")

    w("## 本周建议动作\n")
    for index, action in enumerate(actions[:3], start=1):
        w(f"{index}. {action}")
    if not actions:
        w("1. 本周数据不足，先运行 ai-config-check 获取七层基础体检。")
    w("")

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv[1:])

    analysis = _load(args.analysis)
    report = _render(analysis)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"已写入：{out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
