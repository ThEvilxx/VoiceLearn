---
name: ai-usage-insight
description: >-
  分析近期 AI 协作记录并生成七层改进洞察。当用户说 "AI 使用洞察", "AI insight",
  "本周 AI 协作总结", "ai-usage-insight", "AI 用得怎么样", "分析 AI 使用情况"
  时使用此 skill。读取本地 AI 对话记录，识别重复、重试、长尾和配置变更信号，
  归因到宪法、规范、上下文、工具、护栏、验证、技能七层，并给出可执行优化建议。
---

# AI 使用洞察

基于当前项目的真实使用痕迹反推 AI 规范怎么优化。它不是 KPI，不做排名，也不评价人；目标是发现哪些规则、上下文、工具或技能还没有帮当前项目省事。

它承接前两个工具：

1. `ai-bootstrap`：首次诊断并生成补齐草稿。
2. `ai-config-check`：检查当前七层是否具备。
3. `ai-usage-insight`：根据实际使用记录，判断七层哪里仍然需要优化。

过程记录默认写到临时目录，例如 `/tmp/ai-usage-insight-YYYYMMDD/`。除非用户明确要求归档，否则不要把中间 JSON、HTML 或草稿写进项目。

---

## 七层口径

| 层级 | 关注问题 | 典型信号 |
|------|----------|----------|
| 宪法 | 项目最高规则是否清楚 | 反复确认边界、事实源、禁止事项 |
| 规范 | 领域细则是否可执行 | 同类实现反复询问流程、命名、目录、接口约定 |
| 上下文 | AI 是否能快速找到关键材料 | 长尾对话、反复补充背景、路径来回确认 |
| 工具 | 常用动作是否有脚本入口 | 重复执行固定检查、生成、统计、发布动作 |
| 护栏 | 高风险错误是否被提前拦住 | 重试来自越权修改、错误目录、遗漏审批、污染项目 |
| 验证 | 成功标准是否可运行 | 用户反复追问有没有测、怎么验、结果在哪里 |
| 技能 | 高频任务是否沉淀为流程 | 相似任务重复出现三次以上 |

---

## 工作流程

```
阶段 1：采集本地证据 → 阶段 2：七层归因 → 阶段 3：输出改进报告
```

脚本只负责采集和初步整理。最终判断必须由 AI 结合语义完成，不要只照抄关键词结果。

---

## 阶段 1：采集本地证据

创建临时工作目录：

```bash
mkdir -p /tmp/ai-usage-insight-$(date +%Y%m%d)
```

采集近期对话记录。默认读取 Cursor、Codex、Hermes、Claude Code 四类本地记录，并只采集与当前项目路径匹配的会话，不扫描个人所有项目：

```bash
python3 "${AI_SKILL_ROOT}/scripts/collect_conversations.py" --source all \
  --project-root /path/to/project \
  > /tmp/ai-usage-insight-$(date +%Y%m%d)/conversations.json
```

规则：

- `--project-root` 必须填写当前项目根目录；如果正在项目根目录执行，也可以用 `"$(pwd)"`。
- Codex 会按会话 `cwd` 是否落在项目根目录下过滤。
- Cursor 会按 `~/.cursor/projects` 中的项目路径标识和会话内容中的项目路径过滤。
- Hermes 会读取 `~/.hermes/sessions/` 和 `~/.hermes/profiles/*/sessions/`，再按项目路径过滤。
- Claude Code 会读取 `~/.claude/projects/**/*.jsonl`，再按项目路径过滤。
- 默认排除无法识别项目归属的会话；只有用户明确要求分析跨项目个人使用习惯时，才加 `--include-unscoped`。

可选环境变量：

- `CODEX_SESSIONS_DIR`：覆盖 Codex 会话目录。
- `HERMES_HOME`：覆盖 Hermes 主目录。
- `CLAUDE_HOME` 或 `CLAUDE_PROJECTS_DIR`：覆盖 Claude Code 会话目录。

采集近期 AI 配置变更：

```bash
python3 "${AI_SKILL_ROOT}/scripts/collect_config_changes.py" /path/to/workspace \
  > /tmp/ai-usage-insight-$(date +%Y%m%d)/config_changes.json
```

采集脚本输出本地 JSON，只包含用于分析的摘要字段：

- `queries`：用户问题摘要。
- `rounds`：对话轮次。
- `has_retry`：是否出现重试或纠错信号。
- `mtime`：记录时间。
- `project_match`：是否匹配当前项目。

脚本会过滤审批器注入文本、系统提示和“可以 / 继续 / ok”等低信号确认语，避免把流程噪声误判为重复问题。

如果脚本不可用，可以手动读取本地对话记录目录，统计本周文件数、问题摘要、长尾对话和重试信号；不要输出完整文件路径。

---

## 阶段 2：七层归因

运行初步分析：

```bash
python3 "${AI_SKILL_ROOT}/scripts/analyze_patterns.py" \
  --conversations /tmp/ai-usage-insight-$(date +%Y%m%d)/conversations.json \
  --config-changes /tmp/ai-usage-insight-$(date +%Y%m%d)/config_changes.json \
  --project-root /path/to/project \
  > /tmp/ai-usage-insight-$(date +%Y%m%d)/analysis.json
```

分析时按以下顺序判断：

1. 先看重复模式：是否应该沉淀为规范、脚本或 skill。
2. 再看重试模式：是否来自规则冲突、上下文不足、护栏缺失或验证缺口。
3. 再看长尾对话：是否因为任务太大、背景缺失、流程不清或成功标准不明确。
4. 最后看配置变更：近期是否已经在补某一层，避免重复建议。

要求：

- 重复出现三次以上的相似问题，必须给出沉淀建议。
- 长尾对话不能只说“拆分任务”，要指出应该补哪一层。
- 重试不能只说“上下文不足”，要判断是事实源、规范、护栏还是验证问题。
- 分数只作为排序辅助，不作为 KPI。

---

## 阶段 3：输出七层改进报告

生成 Markdown 报告：

```bash
python3 "${AI_SKILL_ROOT}/scripts/generate_insight.py" \
  --analysis /tmp/ai-usage-insight-$(date +%Y%m%d)/analysis.json \
  --output /tmp/ai-usage-insight-$(date +%Y%m%d)/ai-usage-insight.md
```

报告格式：

```markdown
# 人工智能使用洞察 - YYYY-WXX

## 简单状态
| 项目 | 结果 |
|---|---|
| 对话记录 | N |
| 重试信号 | N |
| 长尾对话 | N |
| 优先优化层 | <层级> |

## 七层洞察
| 层级 | 状态 | 证据 | 优化建议 |
|---|---|---|---|
| 宪法 | 已具备/需补齐/缺失 | ... | ... |

## 重点信号
### 重复模式
...

### 重试模式
...

### 长尾对话
...

## 本周建议动作
1. <最优先的一条>
2. <第二条>
3. <第三条>
```

---

## 注意事项

- 数据全部在本地处理，不发送到外部。
- 默认分析范围是当前项目，不是用户所有 AI 对话。
- 不展示完整文件路径，只展示概要和文件名级别线索。
- 没有对话记录时，报告应说明“数据不足”，并建议先运行 `ai-bootstrap` 或 `ai-config-check`。
- 默认不把报告写入项目；用户明确要求归档时，再放入用户指定目录。
- 不要把这个报告写成周报表扬稿。它的价值是指出下一步怎么改 AI 规范。
