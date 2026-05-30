#!/usr/bin/env python3
"""Render Markdown report from seven-layer check results JSON.

Usage:
  python3 render_report.py --results results.json [--output report.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


LAYER_ORDER = ["constitution", "rules", "context", "tools", "guardrails", "verification", "skills"]

EVIDENCE_LABELS = {
    "constitutions": "宪法入口",
    "rules_dir": "规则目录",
    "rules": "规则文件",
    "context_entries": "上下文入口",
    "make_targets": "Makefile 目标",
    "npm_scripts": "package.json 脚本",
    "scripts_dir": "脚本目录",
    "ci": "持续集成",
    "hooks": "自动护栏",
    "ignore_files": "忽略文件",
    "commands": "验证命令",
    "skills_dir": "技能目录",
    "skills": "技能",
}


def _severity_label(value: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(value, value or "低")


def render(data: dict) -> str:
    lines: list[str] = []
    w = lines.append

    total = data.get("total_score", 0)
    w(f"# 人工智能规范体检报告 — {data.get('project', '?')}\n")
    w(f"- 总分：{total} / 100（{data.get('grade', '?')}）")
    w(f"- 生成时间：{data.get('timestamp', '')}")
    w("- 说明：分数只用于项目自评，不用于排名。\n")

    summary = data.get("summary", {})
    w("## 七层状态\n")
    w(f"已具备 {summary.get('已具备', 0)} 层，需补齐 {summary.get('需补齐', 0)} 层，缺失 {summary.get('缺失', 0)} 层，冲突 {summary.get('冲突', 0)} 层。\n")
    w("| 层级 | 状态 | 得分 | 重点 |")
    w("|------|------|------|------|")
    layers = data.get("layers", {})
    for key in LAYER_ORDER:
        layer = layers.get(key, {})
        findings = layer.get("findings") or []
        focus = findings[0]["issue"] if findings else "暂无主要问题"
        w(f"| {layer.get('label', key)} | {layer.get('status', '-')} | {layer.get('score', 0)} | {focus} |")
    w("")

    w("## 详细诊断\n")
    for key in LAYER_ORDER:
        layer = layers.get(key, {})
        label = layer.get("label", key)
        w(f"### {label}：{layer.get('status', '-')}（{layer.get('score', 0)}/100）\n")

        evidence = layer.get("evidence", {})
        if evidence:
            w("证据：")
            for ev_key, ev_value in evidence.items():
                w(f"- {EVIDENCE_LABELS.get(ev_key, ev_key)}：{ev_value}")
            w("")

        findings = layer.get("findings") or []
        if findings:
            w("问题与建议：")
            for item in findings:
                w(f"- [{_severity_label(item.get('severity', 'low'))}] {item.get('issue', '')}")
                if item.get("detail"):
                    w(f"  - 诊断：{item['detail']}")
                if item.get("fix"):
                    w(f"  - 优化：{item['fix']}")
            w("")
        else:
            w("问题与建议：当前层未发现明显问题。\n")

    actions = data.get("priority_actions") or []
    w("## 优先优化动作\n")
    if actions:
        for idx, action in enumerate(actions, start=1):
            w(f"{idx}. {action}")
    else:
        w("暂无高优先级优化动作。")
    w("")

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv[1:])

    data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    report = render(data)

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
