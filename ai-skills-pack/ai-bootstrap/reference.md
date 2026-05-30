# ai-bootstrap 参考文档

## 定位

`ai-bootstrap` 面向已有项目的 AI 规范诊断和补齐。

默认假设项目已经有宪法、README、贡献说明、规则目录或团队约定中的一部分。它的主任务是把这些材料按七层梳理清楚，找出缺口、冲突和不可执行规则，再生成补充草稿。

只有没有任何规范入口的新项目，才生成完整 `AGENTS.md.draft`。

## 七层诊断

诊断报告固定按七层输出：

| 层级 | 检查重点 | 常见补齐动作 |
|------|----------|--------------|
| 宪法 | 项目级总入口、事实源、边界、禁令、交付标准 | 生成 `AGENTS.md.supplement.draft` 或新项目 `AGENTS.md.draft` |
| 规范 | 编码、Git、API、安全、文档等细分规则 | 拆分规则、删除重复、补缺失领域 |
| 上下文 | README、设计文档、目录说明、示例、文档路由 | 补上下文入口和读取顺序 |
| 工具 | Makefile、脚本、CI、构建、测试、发布命令 | 补命令说明，校准不存在的命令 |
| 护栏 | hook、CI、权限、审批、服务端保护 | 把纯文本禁令升级为自动机制 |
| 验证 | 不同变更类型对应的测试、构建、检查 | 补验证矩阵 |
| 技能 | 复杂高频流程是否沉淀为 SOP / skill | 生成候选 skill 清单或草稿 |

每层状态只能使用：

- `已具备`
- `缺失`
- `需补齐`
- `冲突`

先给状态，再给详细诊断和优化建议。

## 过程记录

过程记录默认不写入项目。临时目录建议：

```text
/tmp/ai-bootstrap-<project>-<timestamp>/
├── profile.json
├── decisions.md
└── generated-files.md
```

用户明确要求保存时，才把过程记录写入项目。否则用完即可丢弃。

## 预设类型识别

| 信号 | 预设 |
|---|---|
| 存在 `go.mod` | `go-backend` |
| `package.json` 含 react/vue/next/vite/svelte | `node-frontend` |
| 存在 `pyproject.toml` 或 `requirements*.txt` | `python` |
| 以上均无 | `generic-docs` |

优先级：go-backend > node-frontend > python > generic-docs。

## 工具结构口径

默认只支持 `cursor`、`codex`、`claude-code` 三类目标。Cursor 和 Codex 有本工具包约定的项目结构；Claude Code 不硬套目录，由执行者按项目事实判断。

| 工具 / 场景 | 默认承载 | 生成策略 |
|------------|----------|----------|
| Cursor | `.cursor/rules`、`.cursor/skills`、`.cursor/hooks.json` | 可生成对应 `.draft`，用户确认后再激活 |
| Codex | `AGENTS.md`、`.codex/rules`、`.codex/skills/rules-check` | 生成 `.codex/rules/*.md.draft`，并生成 `rules-check` skill 草稿，要求 Codex 任务前读取规则 |
| Claude Code | `CLAUDE.md`、`AGENTS.md` 或项目已有 Claude Code 配置 | 不固定 rules / skills 子目录；无法确认时只生成 `CLAUDE.md.draft`、`AGENTS.md.draft` 或待确认问题 |

## 保留脚本

| 脚本 | 用途 | 是否必须 |
|------|------|---------|
| `scan_project.py` | 扫描项目结构、规范入口、工具线索和七层状态 | 可选，AI 仍需人工诊断 |
| `generate_rules.py` | 从预设模板渲染规则草稿 | 可选，生成后必须人工删改 |
| `_common.py` | 共享工具函数 | 被脚本依赖 |
| `activate_drafts.sh` | 激活用户确认过的 `*.draft` | 用户确认后执行 |

已移除旧脚本：

| 原脚本 | 替代方式 | 原因 |
|--------|----------|------|
| `generate_constitution.py` | AI 基于证据生成 `AGENTS.md.draft` 或 supplement | 完整宪法不能靠模板填空 |
| `identify_sops.py` | AI 阅读 Makefile / scripts / CI 后输出候选清单 | 正则解析容易把普通命令误判为 skill |

## 脚本命令

```bash
# 扫描项目结构和 AI 规范线索
python3 scripts/scan_project.py <project_root> --config-dir <实际配置目录>

# 从模板渲染规则草稿
python3 scripts/generate_rules.py <project_root> --preset <name> --config-dir <实际配置目录>
```

`<实际配置目录>` 必须由执行者先判断后填入，例如 `.codex`、`.cursor` 或项目约定的其他目录。脚本不会猜默认目录，避免把 Codex 执行结果写到 Cursor 目录，或反过来写错。
`--config-dir .cursor` 生成 `.cursor/rules/*.mdc.draft`。`--config-dir .codex` 生成 `.codex/rules/*.md.draft`，并额外生成 `.codex/skills/rules-check/SKILL.md.draft`。Claude Code 目标不固定 rules / skills 子目录，无法确认时 `generate_rules.py` 会拒绝生成。

## 护栏口径

`AGENTS.md`、规则文件、skill 和 checklist 不是护栏；它们是规则或流程。护栏必须由 AI 外部自动执行，并能拦截、审批或补救具体动作。

推荐示例：

| 类型 | 示例 | 强制结果 |
|------|------|----------|
| 写入前 hook | 写 `.env`、`credentials`、`*.pem` 前触发 secret guard | warn / deny / require approval |
| 生成文件 hook | 写 `handler/`、`types/`、`server/` 前检查是否生成文件 | deny |
| 运行时配置 hook | 写 AI 工具运行时目录前检查 | deny |
| 命令审批 | `rm -rf`、`git reset --hard`、远程写接口调用 | require approval / deny |
| Git 服务端保护 | protected branch、required checks、pre-receive hook | reject push / block merge |
| 写后补救 | 编辑 Go 文件后自动格式化，或 CI 中跑 drift check | auto-fix / fail check |

不推荐示例：

- “AI 必须先读文档”。
- “提交前自查 checklist”。
- “连续失败后换方向”。
- “不要直接改生成文件”的纯文本规则。

这些可以作为护栏设计来源，但不是护栏本体。

## 生成物要求

1. 已有宪法项目默认生成 `AGENTS.md.supplement.draft`，不生成替代性完整宪法。
2. 新项目才生成 `AGENTS.md.draft`。
3. 所有项目内产物必须带 `.draft`。
4. 草稿必须说明证据来源。
5. 证据不足时写“待确认问题”，不要伪造命令或流程。
6. 候选 skill 只给复杂高频流程，不包装简单命令。
7. 面向用户阅读的宪法、规则、技能和待确认问题默认使用中文；命令、路径、文件名、代码标识符可以保留英文。
