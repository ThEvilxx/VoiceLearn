# AI 协作飞轮工具包

你拿到了三个 AI Skill，它们构成一个自循环改进闭环：

```text
① ai-bootstrap        ──→  ② ai-config-check
   (诊断并补齐规范)           (配置体检)
        │                         │
        │                         ↓
        └──── 改进 rules / skills ← ③ ai-usage-insight
                                      (使用洞察)
```

---

## 快速开始

把这个文件夹（`ai-skills-pack/`）放到任意位置，在你的项目根目录打开 AI 编程工具，对话框输入：

```text
读 <ai-skills-pack 的绝对路径>/README.md 并按执行计划操作
```

例如放在桌面上：

```text
读 ~/Desktop/ai-skills-pack/README.md 并按执行计划操作
```

AI 会自动完成安装、bootstrap、体检、洞察流程。你只需要在关键节点确认。

---

## 执行计划

> 下面是 AI 的执行指南。如果你是 AI Agent 正在读这个文件，请按下面的计划执行。

### Phase 1：安装 Skills（自动执行，无需确认）

1. 确定本 README.md 所在目录的绝对路径，也就是 `ai-skills-pack/` 的位置。
2. 确定当前 AI 编程工具的全局 skill 安装目录；无法确定时，询问用户或参考工具自身文档。
3. 逐个检查三个 skill：
   - `ai-bootstrap`
   - `ai-config-check`
   - `ai-usage-insight`
4. 如果目标目录不存在对应 skill，直接复制安装。
5. 如果目标目录已存在对应 skill，用分发包中的版本覆盖，因为分发包就是本次要使用的版本。
6. 验证安装成功：检查 3 个 `SKILL.md` 是否存在。

完成后进入 Phase 2。

### 默认工具目标

本包默认支持三类 AI 编程工具。执行者必须先判断当前工具，再填写实际配置目录；不要让脚本猜目录。

| 工具 | 配置目录 | 规则 / 技能口径 |
|------|----------|----------------|
| Cursor | `.cursor` | 使用 `.cursor/rules`、`.cursor/skills`、`.cursor/hooks.json` |
| Codex | `.codex` | 使用 `.codex/rules`，并生成 `.codex/skills/rules-check` 草稿，要求任务前读取规则 |
| Claude Code | `.claude` 或项目已有入口 | 不固定 rules / skills 子目录，由 AI 按项目事实判断；无法确认时只生成草稿和待确认问题 |

### Phase 2：项目 AI 规范 Bootstrap（需要用户确认）

读取并执行 `ai-bootstrap/SKILL.md`。

默认项目已经有宪法或基础规范，所以先按七层做全面诊断：

| 层级 | 输出 |
|------|------|
| 宪法 | 状态 + 详细诊断 + 优化建议 |
| 规范 | 状态 + 详细诊断 + 优化建议 |
| 上下文 | 状态 + 详细诊断 + 优化建议 |
| 工具 | 状态 + 详细诊断 + 优化建议 |
| 护栏 | 状态 + 详细诊断 + 优化建议 |
| 验证 | 状态 + 详细诊断 + 优化建议 |
| 技能 | 状态 + 详细诊断 + 优化建议 |

过程记录默认只写临时目录，不写入项目。

项目内只允许写用户确认过的 `*.draft` 文件：

- 已有宪法项目：优先生成 `AGENTS.md.supplement.draft`
- 新项目：才生成 `AGENTS.md.draft`
- 缺失规则：生成 rules 草稿
- Codex 项目：生成 `.codex/rules/*.md.draft`，并生成 `.codex/skills/rules-check/SKILL.md.draft`
- 复杂高频流程：先给候选清单，用户确认后再生成 skill 草稿

完成标志：用户看到七层诊断报告、生成物清单和下一步建议，并确认草稿。

确认后一键激活所有 draft 文件：

```bash
bash <skill_install_dir>/ai-bootstrap/scripts/activate_drafts.sh "$(pwd)"
```

脚本会把所有 `*.draft` 重命名，已有同名文件会跳过不覆盖。

完成 Phase 2 后，必须暂停并向用户确认：

> Bootstrap 已完成并激活草稿。是否继续执行 ai-config-check 做配置体检？

用户确认后，再进入 Phase 3。

### Phase 3：配置体检（用户确认后执行）

用户确认后，先判断当前项目的实际配置目录，再运行 `ai-config-check` 做七层体检：

```bash
python3 <skill_install_dir>/ai-config-check/scripts/run_checks.py "$(pwd)" --config-dir <实际配置目录>
```

常见取值：Cursor 使用 `.cursor`，Codex 使用 `.codex`。Claude Code 不固定 rules / skills 结构，执行者需要按项目事实判断；无法确认时先说明不确定点。

然后生成报告和仪表盘，按 `ai-config-check/SKILL.md` 流程执行。

展示七层状态、主要缺口和优先修复建议。分数只作为辅助参考，不作为评价目标。

完成 Phase 3 后，必须暂停并向用户确认：

> ai-config-check 已完成。是否继续执行 ai-usage-insight，分析近期 AI 使用情况？

用户确认后，再进入 Phase 4。

### Phase 4：使用洞察（用户确认后执行）

读取并执行 `ai-usage-insight/SKILL.md`。

这个 skill 会采集本地 AI 对话记录，分析重复提问、重试模式和长尾对话，并按七层输出使用洞察报告。

如果本机没有可读取的对话记录，或当前工具不开放会话存储目录，优雅说明数据不足，不要伪造洞察。

### Phase 5：使用反馈（可选）

基于 Phase 2、Phase 3 和 Phase 4 的结果，可以生成一份反馈报告。

```markdown
# ai-skills-pack 使用反馈

## 基本信息
- 项目语言/框架：<从 Phase 2 扫描结果填入>
- 项目之前是否已有 AI 配置：有 / 无
- bootstrap 诊断结果：宪法 <状态> | 规范 <状态> | 上下文 <状态> | 工具 <状态> | 护栏 <状态> | 验证 <状态> | 技能 <状态>

## 七层体检
- 宪法：<状态>
- 规范：<状态>
- 上下文：<状态>
- 工具：<状态>
- 护栏：<状态>
- 验证：<状态>
- 技能：<状态>

## 生成物
- AGENTS.md：已补充 / 仍为 draft / 未生成
- Rules：生成 N 个，采纳 N 个，跳过 N 个
- Skills：候选 N 个，生成 N 个，采纳 N 个

## 好用的地方
- <根据用户反馈总结>

## 不好用 / 不准的地方
- <如实记录报错、误判或用户不满>

## 使用洞察
- <根据 Phase 4 总结重复提问、重试模式、长尾对话、优先优化层或数据不足原因>

## 没覆盖到的需求
- <记录用户提到但工具未覆盖的需求>
```

生成后向用户确认内容是否准确。用户确认或修改后结束。

---

## 各 Skill 独立使用

安装完成后，随时可以单独使用：

| 对话指令 | 触发的 Skill |
|---|---|
| "帮我 bootstrap 这个项目的 AI 配置" | ai-bootstrap |
| "帮我检查这个项目的 AI 配置" | ai-config-check |
| "帮我分析本周的 AI 使用情况" | ai-usage-insight |

---

## 依赖

- Python 3.8+
- 任意支持 Skill 的 AI 编程工具
- HTML Dashboard 需要网络；离线时退化为 Markdown 报告

## FAQ

**Q: 会不会破坏我现有的代码或配置？**
A: 不会。bootstrap 只写 `.draft` 文件，不覆盖已有文件；insight 和 check 只读不写。

**Q: 我已经有 AGENTS.md 了怎么办？**
A: bootstrap 会切换到诊断 + 补充模式，只生成 supplement 和缺口草稿。

**Q: 我的项目不是 Go 的能用吗？**
A: 支持 Go / Node / Python / 通用文档 4 种预设，无法识别时按通用项目处理。

**Q: 体检结果是 KPI 吗？**
A: 不是。体检结果只用于定位下一步怎么补规则、上下文、工具、护栏、验证或 skill。
