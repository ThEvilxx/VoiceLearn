#!/usr/bin/env python3
"""Analyze local AI conversations and map signals to seven improvement layers.

Input: JSON array from collect_conversations.py.
Output: JSON analysis to stdout.

Usage:
  python3 analyze_patterns.py --conversations conv.json --config-changes cfg.json --project-root /path
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SIMILARITY_THRESHOLD = 0.6

LAYERS = [
    "宪法",
    "规范",
    "上下文",
    "工具",
    "护栏",
    "验证",
    "技能",
]

LAYER_KEYWORDS = {
    "宪法": ["宪法", "AGENTS.md", "事实源", "边界", "最高规则", "禁止", "冲突", "暂停"],
    "规范": ["规范", "规则", "目录", "命名", "流程", "API", "接口", "字段", "文档"],
    "上下文": ["上下文", "背景", "读取", "找", "路径", "哪里", "先看", "分析下"],
    "工具": ["脚本", "命令", "工具", "自动", "生成", "同步", "打包", "zip", "render", "check"],
    "护栏": ["不要", "禁止", "不能", "别", "权限", "审批", "污染", "覆盖", "删除", "安全"],
    "验证": ["测试", "验证", "检查", "跑一下", "结果", "失败", "通过", "smoke", "build"],
    "技能": ["skill", "技能", "沉淀", "复用", "流程", "三件套", "bootstrap", "insight"],
}


def _load_json(path: str | None) -> list[Any] | dict[str, Any]:
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity on character bigrams."""
    if not a or not b:
        return 0.0
    a_low, b_low = a.lower(), b.lower()
    a_bi = {a_low[i:i + 2] for i in range(len(a_low) - 1)}
    b_bi = {b_low[i:i + 2] for i in range(len(b_low) - 1)}
    if not a_bi or not b_bi:
        return 0.0
    return len(a_bi & b_bi) / len(a_bi | b_bi)


def _layer_for_text(text: str) -> str:
    lowered = text.lower()
    scores: dict[str, int] = {}
    for layer, keywords in LAYER_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in lowered:
                score += 1
        if score:
            scores[layer] = score
    if not scores:
        return "上下文"
    return sorted(scores.items(), key=lambda item: (-item[1], LAYERS.index(item[0])))[0][0]


def _status_from_signals(count: int, total: int) -> str:
    if count <= 0:
        return "已具备"
    if total <= 0:
        return "数据不足"
    rate = count / max(total, 1)
    if count >= 3 or rate >= 0.25:
        return "需补齐"
    return "可优化"


def _all_queries(conversations: list[dict[str, Any]]) -> list[str]:
    queries: list[str] = []
    for conv in conversations:
        values = conv.get("queries") or []
        if isinstance(values, list):
            queries.extend(str(v) for v in values if str(v).strip())
    return queries


def _find_repeated(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queries = _all_queries(conversations)
    if not queries:
        return []

    clusters: list[list[str]] = []
    for query in queries:
        placed = False
        for cluster in clusters:
            if _similarity(query, cluster[0]) >= SIMILARITY_THRESHOLD:
                cluster.append(query)
                placed = True
                break
        if not placed:
            clusters.append([query])

    repeated: list[dict[str, Any]] = []
    for cluster in clusters:
        if len(cluster) < 3:
            continue
        representative = cluster[0][:150]
        layer = _layer_for_text(" ".join(cluster[:5]))
        repeated.append({
            "representative": representative,
            "count": len(cluster),
            "layer": layer,
            "suggestion": _suggestion_for_layer(layer, signal="重复模式"),
        })
    return sorted(repeated, key=lambda x: x["count"], reverse=True)[:10]


def _find_failures(conversations: list[dict[str, Any]]) -> dict[str, Any]:
    retry_convs = [c for c in conversations if c.get("has_retry")]
    examples: list[dict[str, Any]] = []
    for conv in retry_convs[:5]:
        sample = (conv.get("queries") or [""])[0]
        layer = _layer_for_text(str(sample))
        examples.append({
            "query_sample": str(sample)[:120],
            "rounds": conv.get("rounds", 0),
            "layer": layer,
            "suggestion": _suggestion_for_layer(layer, signal="重试模式"),
        })
    total = len(conversations)
    return {
        "total_conversations": total,
        "retry_conversations": len(retry_convs),
        "retry_rate": round(len(retry_convs) / max(total, 1) * 100, 1),
        "examples": examples,
    }


def _find_long_tail(conversations: list[dict[str, Any]], threshold: int = 15) -> list[dict[str, Any]]:
    long_tail: list[dict[str, Any]] = []
    for conv in conversations:
        rounds = int(conv.get("rounds", 0) or 0)
        if rounds <= threshold:
            continue
        sample = str((conv.get("queries") or [""])[0])[:120]
        layer = _layer_for_text(sample)
        long_tail.append({
            "rounds": rounds,
            "query_sample": sample,
            "layer": layer,
            "suggestion": _suggestion_for_layer(layer, signal="长尾对话"),
        })
    return sorted(long_tail, key=lambda x: x["rounds"], reverse=True)[:10]


def _inventory_assets(project_root: str) -> dict[str, Any]:
    root = Path(project_root)
    constitution_files = [
        "AGENTS.md",
        "CLAUDE.md",
        "CODEX.md",
        "GEMINI.md",
        "COPILOT.md",
        "CURSOR.md",
        ".github/copilot-instructions.md",
    ]
    rules = []
    for rules_dir in [root / ".cursor" / "rules", root / ".codex" / "rules", root / "rules"]:
        if rules_dir.is_dir():
            rules.extend([p.name for p in rules_dir.glob("*.md*")])
    skills = []
    for skills_dir in [root / ".cursor" / "skills", root / ".codex" / "skills", root / "skills"]:
        if skills_dir.is_dir():
            skills.extend([p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()])
    hooks = (
        (root / ".cursor" / "hooks.json").is_file()
        or (root / ".cursor" / "hooks").is_dir()
        or (root / ".claude" / "hooks").is_dir()
        or (root / "hooks").is_dir()
    )
    validation_candidates = [
        "Makefile",
        "package.json",
        "go.mod",
        "pyproject.toml",
        "requirements.txt",
        "scripts/verify.sh",
        "tests",
        ".github/workflows",
    ]
    validation_files = [name for name in validation_candidates if (root / name).exists()]
    context_entries = [name for name in ["README.md", "CONTRIBUTING.md", "SECURITY.md", "docs", "doc"] if (root / name).exists()]
    return {
        "constitution_count": sum(1 for name in constitution_files if (root / name).is_file()),
        "rules_count": len(rules),
        "skills_count": len(skills),
        "has_hooks": hooks,
        "validation_entries": validation_files,
        "context_entries": context_entries,
    }


def _productivity_snapshot(conversations: list[dict[str, Any]]) -> dict[str, Any]:
    total_rounds = sum(int(c.get("rounds", 0) or 0) for c in conversations)
    total_queries = sum(len(c.get("queries", [])) for c in conversations)
    project_matched = sum(1 for c in conversations if c.get("project_match", True))
    unscoped = len(conversations) - project_matched
    source_counts: dict[str, int] = {}
    for conv in conversations:
        source = str(conv.get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    return {
        "total_conversations": len(conversations),
        "project_matched_conversations": project_matched,
        "unscoped_conversations": unscoped,
        "source_counts": source_counts,
        "total_rounds": total_rounds,
        "total_queries": total_queries,
        "avg_rounds_per_conversation": round(total_rounds / max(len(conversations), 1), 1),
    }


def _suggestion_for_layer(layer: str, signal: str) -> str:
    suggestions = {
        "宪法": "把反复确认的最高规则、事实源或硬边界补进宪法或宪法补充草稿。",
        "规范": "把可复用的领域细则写成正式规范或 canonical rule，减少同类任务重复解释。",
        "上下文": "补充 README、索引、文档路由或任务入口，让 AI 能先找到关键材料。",
        "工具": "把高频命令、检查或生成动作沉淀为脚本，并在说明里给出入口。",
        "护栏": "把高风险动作前置成 hook、检查脚本或明确阻断规则。",
        "验证": "补齐可运行的验证命令、成功标准和失败处理说明。",
        "技能": "把三次以上重复流程沉淀为技能，包含触发条件、步骤和检查清单。",
    }
    return suggestions.get(layer, suggestions["上下文"])


def _changed_count(config_changes: dict[str, Any], key: str) -> int:
    value = config_changes.get(key)
    return len(value) if isinstance(value, list) else 0


def _layer_insights(
    repeated: list[dict[str, Any]],
    failures: dict[str, Any],
    long_tail: list[dict[str, Any]],
    assets: dict[str, Any],
    config_changes: dict[str, Any],
    total_conversations: int,
) -> list[dict[str, Any]]:
    signal_counts = {layer: 0 for layer in LAYERS}
    evidence = {layer: [] for layer in LAYERS}

    for item in repeated:
        layer = item["layer"]
        signal_counts[layer] += item["count"]
        evidence[layer].append(f"重复问题 {item['count']} 次：{item['representative']}")

    for item in failures.get("examples", []):
        layer = item["layer"]
        signal_counts[layer] += 1
        evidence[layer].append(f"出现重试信号：{item['query_sample']}")

    for item in long_tail:
        layer = item["layer"]
        signal_counts[layer] += 1
        evidence[layer].append(f"长尾对话 {item['rounds']} 轮：{item['query_sample']}")

    if assets.get("constitution_count", 0) == 0:
        signal_counts["宪法"] += 2
        evidence["宪法"].append("未发现项目级宪法入口")
    if assets.get("rules_count", 0) == 0:
        signal_counts["规范"] += 2
        evidence["规范"].append("未发现规则文件")
    if not assets.get("context_entries"):
        signal_counts["上下文"] += 2
        evidence["上下文"].append("未发现 README、docs 或贡献说明入口")
    if not assets.get("validation_entries"):
        signal_counts["验证"] += 2
        evidence["验证"].append("未发现明显验证入口")
    if assets.get("skills_count", 0) == 0:
        signal_counts["技能"] += 1
        evidence["技能"].append("未发现技能入口")
    if not assets.get("has_hooks"):
        signal_counts["护栏"] += 1
        evidence["护栏"].append("未发现 hook 入口")

    changed_layers = {
        "规范": _changed_count(config_changes, "rules_changed"),
        "技能": _changed_count(config_changes, "skills_changed"),
        "护栏": _changed_count(config_changes, "hooks_changed"),
    }
    if config_changes.get("agents_md_changed"):
        changed_layers["宪法"] = changed_layers.get("宪法", 0) + 1
    for layer, count in changed_layers.items():
        if count:
            evidence[layer].append(f"近期已有 {count} 项相关配置变更，建议复查效果后再追加规则")

    insights: list[dict[str, Any]] = []
    for layer in LAYERS:
        count = signal_counts[layer]
        insights.append({
            "layer": layer,
            "status": _status_from_signals(count, total_conversations),
            "signal_count": count,
            "evidence": evidence[layer][:4],
            "suggestion": _suggestion_for_layer(layer, signal="综合信号") if count else "暂未发现明显问题，维持现有入口即可。",
        })
    return insights


def _priority_actions(layer_insights: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    ranked = sorted(layer_insights, key=lambda item: (-int(item["signal_count"]), LAYERS.index(item["layer"])))
    for item in ranked:
        if int(item["signal_count"]) <= 0:
            continue
        actions.append(f"{item['layer']}层：{item['suggestion']}")
        if len(actions) >= 3:
            break
    if not actions:
        actions.append("本周数据不足或问题不集中，先运行 ai-config-check 复查七层基础状态。")
    return actions


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversations", default=None)
    parser.add_argument("--config-changes", default=None)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv[1:])

    conversations = _load_json(args.conversations)
    if not isinstance(conversations, list):
        conversations = []
    config_changes = _load_json(args.config_changes)
    if not isinstance(config_changes, dict):
        config_changes = {}

    productivity = _productivity_snapshot(conversations)
    repeated = _find_repeated(conversations)
    failures = _find_failures(conversations)
    long_tail = _find_long_tail(conversations)
    assets = _inventory_assets(args.project_root)
    layer_insights = _layer_insights(
        repeated,
        failures,
        long_tail,
        assets,
        config_changes,
        productivity["total_conversations"],
    )

    top_layer = max(layer_insights, key=lambda item: int(item["signal_count"])) if layer_insights else {}
    analysis = {
        "summary": {
            "project_root": str(Path(args.project_root).resolve()),
            "total_conversations": productivity["total_conversations"],
            "project_matched_conversations": productivity["project_matched_conversations"],
            "unscoped_conversations": productivity["unscoped_conversations"],
            "source_counts": productivity["source_counts"],
            "total_rounds": productivity["total_rounds"],
            "avg_rounds_per_conversation": productivity["avg_rounds_per_conversation"],
            "retry_conversations": failures["retry_conversations"],
            "long_tail_conversations": len(long_tail),
            "top_layer": top_layer.get("layer", "数据不足"),
            "top_layer_status": top_layer.get("status", "数据不足"),
        },
        "signals": {
            "repeated_patterns": repeated,
            "failure_patterns": failures,
            "long_tail": long_tail,
        },
        "layer_insights": layer_insights,
        "priority_actions": _priority_actions(layer_insights),
        "assets": assets,
        "config_changes": config_changes,
        "productivity": productivity,
    }
    json.dump(analysis, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
