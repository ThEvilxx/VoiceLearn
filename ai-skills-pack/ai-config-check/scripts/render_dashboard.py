#!/usr/bin/env python3
"""Render a self-contained static HTML dashboard from seven-layer check results.

Usage:
  python3 render_dashboard.py --results results.json [--output dashboard.html]
"""
from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any


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

STATUS_CLASS = {
    "已具备": "ok",
    "需补齐": "warn",
    "缺失": "bad",
    "冲突": "conflict",
}

SEVERITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _score(value: Any) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _status_class(status: Any) -> str:
    return STATUS_CLASS.get(_text(status), "neutral")


def _evidence_items(evidence: Any) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return '<p class="muted">未发现可展示证据。</p>'

    rows: list[str] = []
    for key, value in evidence.items():
        label = EVIDENCE_LABELS.get(key, key)
        body = escape(_json_text(value))
        rows.append(
            "<div class=\"evidence-row\">"
            f"<dt>{escape(label)}</dt>"
            f"<dd><pre>{body}</pre></dd>"
            "</div>"
        )
    return "<dl class=\"evidence-list\">" + "\n".join(rows) + "</dl>"


def _findings_items(findings: Any) -> str:
    items = _as_list(findings)
    if not items:
        return '<p class="muted">当前层未发现明显问题。</p>'

    rows: list[str] = []
    for raw in items:
        if not isinstance(raw, dict):
            rows.append(f"<li>{escape(_text(raw))}</li>")
            continue
        severity = escape(SEVERITY_LABELS.get(_text(raw.get("severity")), _text(raw.get("severity"), "低")))
        issue = escape(_text(raw.get("issue"), "未命名问题"))
        detail = escape(_text(raw.get("detail")))
        fix = escape(_text(raw.get("fix")))
        detail_html = f"<p><strong>诊断：</strong>{detail}</p>" if detail else ""
        fix_html = f"<p><strong>优化：</strong>{fix}</p>" if fix else ""
        rows.append(
            "<li>"
            f"<span class=\"severity\">{severity}</span>"
            f"<strong>{issue}</strong>"
            f"{detail_html}{fix_html}"
            "</li>"
        )
    return "<ul class=\"findings\">" + "\n".join(rows) + "</ul>"


def _layer_card(key: str, layer: Any) -> str:
    if not isinstance(layer, dict):
        layer = {}
    label = escape(_text(layer.get("label"), key))
    status = escape(_text(layer.get("status"), "-"))
    score = _score(layer.get("score"))
    css_class = _status_class(layer.get("status"))
    return f"""
    <section class="layer-card {css_class}">
      <header>
        <div>
          <h3>{label}</h3>
          <p>{status} · {score}/100</p>
        </div>
        <span class="status-pill">{status}</span>
      </header>
      <div class="meter" aria-label="{label} 得分 {score}">
        <span style="width: {score}%"></span>
      </div>
      <div class="section-block">
        <h4>证据</h4>
        {_evidence_items(layer.get("evidence"))}
      </div>
      <div class="section-block">
        <h4>问题与建议</h4>
        {_findings_items(layer.get("findings"))}
      </div>
    </section>
    """


def _layer_row(key: str, layer: Any) -> str:
    if not isinstance(layer, dict):
        layer = {}
    label = escape(_text(layer.get("label"), key))
    status = escape(_text(layer.get("status"), "-"))
    score = _score(layer.get("score"))
    css_class = _status_class(layer.get("status"))
    findings = _as_list(layer.get("findings"))
    focus = "暂无主要问题"
    first = findings[0] if findings else None
    if isinstance(first, dict):
        focus = _text(first.get("issue"), focus)
    elif first is not None:
        focus = _text(first, focus)
    return f"""
    <tr>
      <td>{label}</td>
      <td><span class="status-pill {css_class}">{status}</span></td>
      <td>
        <div class="score-cell">
          <span>{score}</span>
          <div class="mini-meter"><span style="width: {score}%"></span></div>
        </div>
      </td>
      <td>{escape(focus)}</td>
    </tr>
    """


def _actions_html(actions: Any) -> str:
    items = [escape(_text(item)) for item in _as_list(actions) if _text(item)]
    if not items:
        return '<p class="muted">暂无高优先级优化动作。</p>'
    return "<ol>" + "\n".join(f"<li>{item}</li>" for item in items) + "</ol>"


def render(data: dict[str, Any]) -> str:
    layers = data.get("layers")
    if not isinstance(layers, dict):
        layers = {}

    total = _score(data.get("total_score"))
    grade = escape(_text(data.get("grade"), "?"))
    project = escape(_text(data.get("project"), "?"))
    timestamp = escape(_text(data.get("timestamp")))
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    summary_text = (
        f"已具备 {escape(_text(summary.get('已具备'), '0'))} 层，"
        f"需补齐 {escape(_text(summary.get('需补齐'), '0'))} 层，"
        f"缺失 {escape(_text(summary.get('缺失'), '0'))} 层，"
        f"冲突 {escape(_text(summary.get('冲突'), '0'))} 层。"
    )

    rows = "\n".join(_layer_row(key, layers.get(key, {})) for key in LAYER_ORDER)
    cards = "\n".join(_layer_card(key, layers.get(key, {})) for key in LAYER_ORDER)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>人工智能规范体检报告 - {project}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #202124;
      --muted: #666b73;
      --line: #dfe3e6;
      --ok: #16794c;
      --warn: #a45d00;
      --bad: #b3261e;
      --conflict: #6f3cc3;
      --neutral: #5f6368;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.55;
    }}
    main {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 190px;
      gap: 24px;
      align-items: stretch;
      border-bottom: 1px solid var(--line);
      padding-bottom: 26px;
      margin-bottom: 24px;
    }}
    h1, h2, h3, h4, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 10px; font-size: 30px; line-height: 1.2; }}
    h2 {{ margin: 28px 0 14px; font-size: 22px; }}
    h3 {{ margin-bottom: 4px; font-size: 18px; }}
    h4 {{ margin-bottom: 8px; font-size: 14px; color: var(--muted); }}
    .meta {{ color: var(--muted); margin-bottom: 4px; }}
    .score-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 150px;
    }}
    .score-number {{ font-size: 42px; font-weight: 700; line-height: 1; }}
    .grade {{ color: var(--muted); margin-top: 6px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{ background: #f0f3f5; color: #3c4043; font-weight: 600; }}
    tr:last-child td {{ border-bottom: 0; }}
    .score-cell {{ display: grid; grid-template-columns: 36px minmax(80px, 1fr); gap: 10px; align-items: center; }}
    .mini-meter, .meter {{
      height: 9px;
      overflow: hidden;
      border-radius: 999px;
      background: #e7eaee;
    }}
    .meter {{ height: 11px; margin: 12px 0 18px; }}
    .mini-meter span, .meter span {{
      display: block;
      height: 100%;
      background: var(--accent);
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid currentColor;
      color: var(--neutral);
      font-size: 13px;
      white-space: nowrap;
    }}
    .status-pill.ok, .layer-card.ok .status-pill {{ color: var(--ok); }}
    .status-pill.warn, .layer-card.warn .status-pill {{ color: var(--warn); }}
    .status-pill.bad, .layer-card.bad .status-pill {{ color: var(--bad); }}
    .status-pill.conflict, .layer-card.conflict .status-pill {{ color: var(--conflict); }}
    .layer-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .layer-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-left: 5px solid var(--neutral);
      border-radius: 8px;
      padding: 18px;
      min-width: 0;
    }}
    .layer-card.ok {{ border-left-color: var(--ok); }}
    .layer-card.warn {{ border-left-color: var(--warn); }}
    .layer-card.bad {{ border-left-color: var(--bad); }}
    .layer-card.conflict {{ border-left-color: var(--conflict); }}
    .layer-card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }}
    .section-block {{ margin-top: 14px; }}
    .evidence-list {{ margin: 0; }}
    .evidence-row {{
      display: grid;
      grid-template-columns: 110px minmax(0, 1fr);
      gap: 10px;
      padding: 8px 0;
      border-top: 1px solid #edf0f2;
    }}
    .evidence-row:first-child {{ border-top: 0; }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; min-width: 0; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      color: #30353b;
    }}
    .findings {{ margin: 0; padding-left: 20px; }}
    .findings li {{ margin: 8px 0; }}
    .findings p {{ margin: 5px 0 0; color: #3c4043; }}
    .severity {{
      display: inline-block;
      margin-right: 8px;
      color: var(--bad);
      font-weight: 700;
    }}
    .actions {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px 22px;
    }}
    .actions ol {{ margin: 0; padding-left: 22px; }}
    .actions li {{ margin: 8px 0; }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 760px) {{
      main {{ padding: 22px 14px 40px; }}
      .hero {{ grid-template-columns: 1fr; }}
      .layer-grid {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }}
      .evidence-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>人工智能规范体检报告</h1>
        <p class="meta">项目：{project}</p>
        <p class="meta">生成时间：{timestamp}</p>
        <p>{summary_text}</p>
        <p class="muted">分数只用于项目自评，不用于排名。HTML 为离线静态页面，不依赖外部脚本或网络资源。</p>
      </div>
      <aside class="score-panel" aria-label="总分">
        <div class="score-number">{total}</div>
        <div class="grade">/ 100 · {grade}</div>
        <div class="meter"><span style="width: {total}%"></span></div>
      </aside>
    </section>

    <section>
      <h2>七层状态</h2>
      <table>
        <thead>
          <tr>
            <th>层级</th>
            <th>状态</th>
            <th>得分</th>
            <th>重点</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </section>

    <section>
      <h2>优先优化动作</h2>
      <div class="actions">
        {_actions_html(data.get("priority_actions"))}
      </div>
    </section>

    <section>
      <h2>详细诊断</h2>
      <div class="layer-grid">
        {cards}
      </div>
    </section>
  </main>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv[1:])

    data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    html = render(data)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"已写入：{out}")
    else:
        print(html)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
