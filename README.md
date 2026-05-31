# VoiceLearn — 语音交互式学习伴侣

Upload course notes or papers, then learn by speaking — you ask with your voice, VoiceLearn answers with voice.

《智能语音技术》课程作业 — 基于 Vibe Coding 的 Speech 应用创意开发。

## 你可以用它做什么

1. **上传课件/论文**（PDF、Markdown、TXT、源代码）
2. **打字或语音提问** — 点击麦克风说话，或直接打字
3. **选择回答模式** — 🎧 语音简答（≤100 字口语 + 引导式反问）或 📄 深度长文（Markdown + 详细引用）
4. **多轮追问** — 系统记住对话历史，支持指代消解（"它和 RNN 有什么区别？"）
5. **听到语音回答** — edge-tts 朗读答案，浏览器内播放
6. **查看知识图谱** — 自动抽取课件中的实体和关系，可视化浏览

```
你说话 → ASR 转写 → Query 改写（消解指代词）→ RAG 混合检索 → 大模型生成 → TTS 朗读 / Markdown 文字
```

## 已实现的完整特性

| 特性 | 说明 |
|------|------|
| 🎤 语音转文字 | 浏览器录音 → faster-whisper 本地转写 + 幻觉过滤黑名单 |
| 🎧 / 📄 双模式回答 | **语音简答**（口语 + 字数红线 + 引导反问）\| **深度长文**（Markdown 排版 + 严格引用来源） |
| 🔍 混合 RAG 检索 | Dense (BGE-large-zh-v1.5) + Sparse (BM25) 加权融合，支持切换 |
| 🧠 多轮对话记忆 | SQLite 持久化 + 10 轮滑动窗口 + LLM Query 改写消解指代词 |
| 🔊 语音朗读 | edge-tts 中英双语自动检测，TTS 失败时文字仍正常输出 |
| 📚 文档管理 | 上传/删除，多格式支持，向量自动索引与清理 |
| 🕸️ 知识图谱 | LLM 自动抽取实体&关系 → vis-network 可视化，文档删后自动清理孤儿节点 |
| ⚙️ Settings 控制台 | 前端切换 LLM provider（OpenAI-compatible / Claude）、更换 API Key 和 Model |
| 🚀 生产部署 | `make prod` 单服务模式 — 一个端口 serve 前端 + 全部 API |

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + TypeScript 6 + Vite 8 + vis-network |
| 后端 | FastAPI + SSE 流式 |
| LLM | OpenAI Compatible API（DeepSeek V4 Pro / Claude 4 Sonnet 等） |
| RAG | LangChain LCEL + ChromaDB + rank-bm25 混合检索 |
| Embedding | BGE-large-zh-v1.5（本地，ModelScope 下载） |
| ASR | faster-whisper base（本地推理，ModelScope 下载） |
| TTS | edge-tts（免费，中英双语） |
| 数据库 | SQLite + SQLAlchemy 异步（对话记忆 + 元数据） |
| 知识图谱 | NetworkX + vis-network |

## 快速开始

### 前置条件

- Python 3.11（推荐 conda 环境）
- Node.js 22+
- DeepSeek 或 Claude API Key

### 配置

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 API Key
```

### 下载本地模型

```bash
# BGE Embedding（~1.2GB）
python -c "from modelscope import snapshot_download; snapshot_download('BAAI/bge-large-zh-v1.5', cache_dir='backend/data/models')"

# faster-whisper（~140MB）
python -c "from modelscope import snapshot_download; snapshot_download('Systran/faster-whisper-base', cache_dir='backend/data/models')"
```

### 启动

```bash
# 开发模式（前后端热重载）
make dev
# 浏览器打开 http://localhost:5173

# 生产模式（单端口 serve 一切）
make prod
# 浏览器打开 http://127.0.0.1:8000
```

## 项目结构

```
VoiceLearn/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI 入口
│   │   ├── config.py             # pydantic-settings 全局配置
│   │   ├── api/                  # REST + SSE 端点
│   │   │   ├── chat.py           # 语音/文字聊天 + 流式
│   │   │   ├── conversations.py  # 会话 CRUD
│   │   │   ├── documents.py      # 文档上传/管理
│   │   │   ├── knowledge_graph.py
│   │   │   └── settings.py       # LLM 配置读/写
│   │   ├── core/                 # 核心模块
│   │   │   ├── asr.py            # faster-whisper 识别 + 幻觉过滤
│   │   │   ├── tts.py            # edge-tts 合成 + 中英检测
│   │   │   ├── llm.py            # 多 provider LLM 工厂
│   │   │   ├── embeddings.py     # 本地 BGE 嵌入
│   │   │   ├── rag_chain.py      # 双模式 System Prompt
│   │   │   ├── query_rewriter.py # LLM 指代消解
│   │   │   ├── vector_store.py   # Dense + BM25 混合检索
│   │   │   ├── loader.py         # PDF/MD/TXT/代码 加载
│   │   │   ├── splitter.py       # 递归分块
│   │   │   └── kg_extractor.py   # LLM 实体关系抽取
│   │   ├── models/               # Pydantic 模型
│   │   ├── services/             # 业务编排层
│   │   └── db/                   # SQLAlchemy async + ORM
│   ├── data/                     # chroma/ uploads/ models/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                # Chat / Documents / Graph / Settings
│   │   ├── components/           # ChatPanel / Layout
│   │   ├── hooks/useSpeech.ts    # 浏览器录音 Hook
│   │   ├── api/client.ts         # REST + SSE 客户端
│   │   └── types/                # TypeScript 类型
│   └── ...
├── docs/
│   ├── demo.md                   # 课程项目文档
│   └── plans/                    # 分阶段实现计划
├── CLAUDE.md                     # AI 协作宪法
├── Makefile                      # 一键启动/安装/检查
└── README.md
```

## 架构设计亮点

### 端云结合

本地算力处理 ASR（感知）和 Embedding（向量化），云端大模型处理理解与生成。通过统一 `langchain-openai` 客户端 + `.env` 注入凭据，切换 provider 无需改代码。启动时缺少 `LLM_API_KEY` 直接 fail-fast 退出。

### 双模式回答系统

同一套 RAG 管道，通过传入 `mode` 参数动态选择 System Prompt：

- **🎧 语音模式**：字数红线 ≤100 字、结论先行、禁止朗读 source 标记、结尾抛引导式反问
- **📄 文字模式**：Markdown 排版、结构化章节、显式引用来源

### 多轮对话与 Query 改写

每轮对话持久化到 SQLite。检索前调用 `query_rewriter.py`（独立 LLM 节点，temperature=0），将"它和 RNN 有什么区别？"改写为独立检索 query。历史超限自动截断早期轮次，控制 token 预算。

### 混合检索 + 幻觉控制

Dense（BGE embedding）与 Sparse（BM25）加权融合，默认 7:3。System Prompt 强制 LLM 在解释后附带原文引用和来源文档名。

### 语音管道风控

`asr.py` 维护停用词黑名单（"谢谢观看" "字幕由…" 等），过滤 Whisper 底噪幻觉。TTS 失败时返回空音频，绝不阻断文字输出流。

## 未来展望

以下特性已在架构设计中规划，但尚未在代码中实现：

| 规划项 | 说明 |
|--------|------|
| 前端 VAD（语音活动检测） | `useSpeech.ts` 集成语音活动检测，仅在真实人声时发送音频，降低 Whisper 幻觉率 |
| 句子级流式 TTS | LLM 输出时遇标点即刻截断发送给 TTS，文本边生成、语音边合成、前端边播放 |
| 结构化文档切分 | 接入 `MarkdownHeaderTextSplitter` 和代码切分器，保留章节标题到 Metadata |
| 知识图谱路由 | 在 RAG 管道中接入路由节点：事实型查询走图谱、语义型查询走向量库 |
| 跨语言检索优化 | 检测到中英跨语言查询时，自动降低 BM25 权重，优先依赖双语 Embedding |

## 不足与改进方向

- **TTS 依赖 edge-tts**：免费但偶有网络波动，不支持自定义语速/情感
- **ASR 模型为 whisper-base**：中文准确率有提升空间，可换 medium/large
- **无用户鉴权**：本地单用户模式，无登录/多租户隔离
- **知识图谱为静态快照**：手动触发 Refresh，不感知文档增量变化
