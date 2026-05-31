# CLAUDE.md — VoiceLearn

语音交互式学习伴侣。核心架构为 **端云结合**：本地负责 ASR/Embedding 感知，云端外部大模型负责认知归纳。
**作为 AI 编程助手，你必须在所有开发任务中严格遵守本文件的架构约束。**

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + SSE 流式 |
| LLM 后端 | 外部 API (OpenAI 兼容格式) |
| RAG | LangChain LCEL + ChromaDB |
| Embedding | BGE-large-zh-v1.5 (本地) |
| 语音识别 | faster-whisper (本地) |
| 语音合成 | edge-tts (免费) |
| 前端 | React 19 + TypeScript 6 + Vite 8 |
| 知识图谱 | NetworkX + vis-network |
| 数据库 | SQLite + SQLAlchemy (异步) |
| Python | 3.11 |

## 技术栈与架构边界

- **后端**：FastAPI + SSE 流式 (Python 3.11)
- **大模型 (云端)**：统一使用 `langchain-openai` 兼容外部 API（严格禁止集成/调用本地 LLM）
- **RAG**：LangChain LCEL + ChromaDB (本地)
- **语音**：faster-whisper (本地 ASR) + edge-tts (外部 TTS)
- **前端**：React 19 + TypeScript + Vite

```text
前端 VAD 录音 ─→ 幻觉过滤 ─→ Query 改写 ─→ ChromaDB 检索 ─→ 外部大模型 API ─→ 句子级 TTS ─→ 音频流播放
```


## 核心架构红线 (绝对约束)

### 1. API 与安全性 (Security)
- **禁止硬编码**：任何 API Key、Base URL 绝对禁止写在代码中。
- **环境强校验**：必须使用 Pydantic `BaseSettings` 从 `.env` 读取配置。应用启动时若缺少 `LLM_API_KEY`，必须 Fail-fast 报错退出。
- **统一 API 网关**：LLM 调用统一通过 `core/llm.py` 工厂函数，封装单一 `langchain-openai` 客户端。通过切换 `base_url` + `api_key` 对接不同服务商，禁止引入多个 SDK。
- **网络容灾**：所有外部调用必须设置严格超时（连接 5s，读取 30s）。SSE 流式中断时捕获 `ConnectionError`，向前端推送 `data: [ERROR] AI 思考中断，请重试`。

### 2. RAG 管道规范 (RAG Pipeline)
- **结构化切分**：禁止无脑 `RecursiveCharacterTextSplitter`。针对 Markdown/代码必须使用对应的结构化切分器。
- **强制 Query 改写**：在检索前，必须包含“独立查询生成”节点，结合历史对话改写用户的指代词（如把“它”改写为具体实体）。
- **防幻觉引用**：System Prompt 必须要求模型在中文解释后，引用对应的英文原句来源。
- **Token 控制**：RAG 上下文硬上限 4000 Token（英文原文）。历史对话超过轮数自动截断早期对话，防止单次请求成本爆炸。

### 3. 语音管道规范 (Voice Pipeline)
- **ASR 防幻觉**：`asr.py` 必须维护停用词黑名单（过滤"谢谢观看", "字幕由..."等底噪幻觉）。前端必须配合 VAD。
- **TTS 优雅降级**：TTS 失败时直接捕获异常并返回空音频/错误码，**绝不允许**阻断 LLM 的文字输出。保证“语音可挂，文字必须出”。
- **流式并发**：实现大模型 SSE 输出与 TTS 合成的并行调度（句子级截断合成）。

## 目录与数据权限
- **数据目录**：`backend/data/` 存放持久化数据（chroma/, uploads/）。
- **禁止直接操作 DB**：禁止绕过应用层代码去手动篡改 ChromaDB 的底层 SQLite。

## 开发与验证常规
- Python 规范：`pathlib.Path`，类型注解 (mypy strict)，Ruff 格式化。
- TypeScript：React 19 Hooks，ESLint flat config。
- 启动：`make dev`
- 验证流程：开发 RAG 时，**先在纯文本 API 下测试（禁用语音）**，确认切分与检索质量后，再接入语音管道。

**核心目录结构**：
```text
VoiceLearn/
├── backend/
│   ├── app/
│   │   ├── api/       # 路由层 (chat.py, documents.py)
│   │   ├── core/      # 核心业务层 (rag_chain.py, asr.py, tts.py 等)
│   │   └── data/      # 数据持久化目录 (chroma/, uploads/)
│   └── .env           # 环境变量 (Agent 启动前必须检查此文件)
├── frontend/
│   ├── src/
│   │   ├── hooks/     # 前端逻辑 (如 useSpeech.ts, 包含 VAD 控制)
│   │   └── api/       # 请求层 (client.ts, 包含 SSE 接收与容灾)
