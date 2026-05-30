# VoiceLearn — 语音交互式学习伴侣

Upload course notes or papers, then learn by speaking — you ask with your voice, VoiceLearn answers with voice.

《智能语音技术》课程作业 — 基于 Vibe Coding 的 Speech 应用创意开发。

## 核心功能

```
你说话 → ASR 转写 → Query 改写 → RAG 检索 → 外部大模型生成 → TTS 朗读 → 你听到回答
```

| 功能 | 说明 |
|------|------|
| 语音输入 | 前端 VAD 录音 → 本地 faster-whisper 转写 + 幻觉过滤 |
| RAG 问答 | 混合检索 + 知识图谱路由，基于上传资料精准回答 |
| 语音输出 | edge-tts 流式合成自然语音，支持优雅降级 |
| 文档管理 | PDF/Markdown/代码 上传，结构化分块与向量索引 |
| 大模型调度 | 纯外部 API 驱动，全面兼容 OpenAI 格式（Claude/DeepSeek/Kimi 等） |

## 技术栈

- **前端**：React 19 + TypeScript + Vite
- **后端**：FastAPI + SSE 流式
- **大模型 (云端)**：OpenAI Compatible API (如 Claude 3.5, DeepSeek-V3, Kimi K2.6)
- **RAG**：LangChain LCEL + ChromaDB
- **ASR**：faster-whisper (本地推理)
- **TTS**：edge-tts (免费外部服务)
- **Embedding**：BGE-large-zh-v1.5 (本地向量化)

## 快速开始

```bash
# 安装依赖
make install

# 开发模式（前后端热重载）
make dev

# 浏览器打开 http://localhost:5173
```

详见 [CLAUDE.md](CLAUDE.md)

## 项目结构

```
VoiceLearn/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── config.py          # 全局配置
│   │   ├── api/               # REST + SSE 端点
│   │   │   ├── chat.py        # 语音/文字聊天 API
│   │   │   ├── documents.py   # 文档上传/管理
│   │   │   ├── knowledge_graph.py
│   │   │   └── settings.py
│   │   ├── core/              # 核心模块
│   │   │   ├── asr.py         # faster-whisper 语音识别
│   │   │   ├── tts.py         # edge-tts 语音合成
│   │   │   ├── llm.py         # 多 LLM 后端工厂
│   │   │   ├── embeddings.py  # 本地嵌入模型
│   │   │   ├── rag_chain.py   # RAG 管道
│   │   │   ├── vector_store.py # 混合检索
│   │   │   ├── loader.py      # 文档加载
│   │   │   ├── splitter.py    # 文本分块
│   │   │   └── kg_extractor.py # 知识图谱提取
│   │   ├── models/            # Pydantic 数据模型
│   │   ├── services/          # 业务编排
│   │   └── db/                # SQLite 数据库
│   └── data/                  # 持久化数据
├── frontend/
│   ├── src/
│   │   ├── pages/             # Chat, Documents, Graph, Settings
│   │   ├── components/        # ChatPanel, Layout, DocumentManager
│   │   ├── hooks/useSpeech.ts # 浏览器录音 Hook
│   │   ├── api/client.ts     # REST + SSE 客户端
│   │   └── types/            # TypeScript 类型
│   └── ...
├── CLAUDE.md                  # AI 协作宪法
├── Makefile                   # 一键启动
└── README.md
```

## 核心架构设计与工程约束

### 1. 纯 API 驱动与大模型调度 (端云结合)
- **弃用本地 LLM**：为保障跨语言理解和零幻觉的优质体验，业务逻辑和生成任务全部交由外部顶尖大模型。本地算力仅保留 ASR（感知）和 Embedding（切分计算）。
- **统一 API 网关**：封装标准的 `langchain-openai` 客户端，通过切换 `Base URL` 和 `API Key` 无缝对接各大模型。启动时若 `LLM_API_KEY` 或 `LLM_BASE_URL` 缺失，直接报错退出，不在请求时才崩溃。
- **Token 成本与截断**：
    - RAG 上下文硬上限：最多 4000 Token 的英文原文
    - 历史对话超过轮数自动截断早期对话，防止单次请求成本爆炸

### 2. 结构化感知文本切分（Structure-Aware Chunking）
- **痛点**：盲目的字符切分会破坏论文公式、跨页表格或代码块。
- **策略**：引入特定格式的 Splitter（如 `MarkdownHeaderTextSplitter`、特定语言的代码切分器）。保留文档的层级结构，将章节标题存入 Metadata，保障 RAG 召回的上下文完整性。

### 3. 多轮对话上下文与查询改写（Query Rewrite）
- **痛点**：语音交互存在大量指代词（如“它和 RNN 的区别”），直接检索会召回噪音。
- **策略**：在 RAG 管道入口设置**独立查询生成（Standalone Query Generation）**节点。调用极速大模型（或主模型）将“当前输入 + 历史记录”改写为完整、无指代的检索词，再送入 ChromaDB。

### 4. 跨语言混合检索与幻觉控制（Grounded Generation）
- **痛点**：中文 Query 检索英文文档时 BM25 词汇匹配失效；大模型跨语言解答易产生“翻译幻觉”。
- **策略**：
  - **检索降级**：检测到跨语言时，自动降低 BM25 权重，完全依赖双语 Embedding 的 Dense 检索（或预留 Query 翻译节点）。
  - **强制源文引用**：系统提示词严格约束 LLM：“用中文解释后，必须附带原文关键短语或句子作为支撑，并标明来源”。

### 5. 知识图谱与向量检索的融合路由
- **痛点**：知识图谱如果不参与检索，只会沦为前端展示的“孤岛”。
- **策略**：在 `rag_chain.py` 设计**路由节点 (Router)**。事实型查询（“作者是谁”）查图谱；语义型查询（“解释核心机制”）查向量库。或者将图谱三元组文本化，作为补充上下文共同喂给 LLM。

### 6. 语音管线风控：VAD 与 ASR 幻觉过滤
- **痛点**：底噪环境下 Whisper 极易产生幻觉（如“字幕由某某提供”），触发无效检索。
- **策略**：
  - **前端 VAD**：`useSpeech.ts` 必须集成语音活动检测，仅在真实人声时发送音频。
  - **后端黑名单**：`asr.py` 维护停用词黑名单。一旦识别出常见的无意义幻觉词，直接在 ASR 层丢弃。

### 7. 端到端流式与外部服务容灾（Graceful Degradation）
- **痛点**：语音交互对延迟极度敏感；`edge-tts` 作为非官方 API 存在不稳定性。
- **策略**：
  - **句子级流式**：LLM 输出时遇到标点（句号/问号）即刻截断发送给 TTS，实现文本边生成、语音边合成、前端边播放。
  - **网络容灾**：
    - LLM 请求超时：连接 5s，读取 30s
    - SSE 流式中断时捕获 `ConnectionError`，向前端推送标准错误事件 `data: [ERROR] AI 思考中断，请重试`
    - TTS 失败优雅降级，后端捕获异常，前端正常显示文本并给出轻提示（“语音服务拥挤”），绝不阻断文字阅读流
  
## 状态
当前架构蓝图与约束已确立。开发优先级：
1. [ ] 搭建统一大模型 API 调用网关与鉴权（`.env` 强校验）
2. [ ] 跑通纯文本模式下的 RAG 核心（结构化切分、查询改写、跨语言引用测试）
3. [ ] 接入前端 VAD 与后端 ASR 幻觉过滤
4. [ ] 实现 LLM 到 TTS 的句子级流式调度与容灾降级
