# VoiceLearn — 语音交互式学习伴侣

Upload course papers or notes, then learn by speaking — you ask with your voice, VoiceLearn answers with voice.

《智能语音技术》课程作业 — 基于 Vibe Coding 的 Speech 应用创意开发。

## 使用场景

专为**论文阅读与学术文献学习**设计：

1. 下载一篇英文论文 PDF → 上传到 VoiceLearn
2. 阅读过程中遇到不懂的概念 → 用语音或打字提问
3. 系统从论文原文中检索答案 → 用你的母语朗读解释，同时保留英文原文引用
4. 积累多篇论文后 → 跨论文对比、追问细节、构建知识图谱

## 你可以用它做什么

1. **上传论文/笔记**（PDF、Word、Markdown、TXT、源代码）
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
| 🎤 语音转文字 | 浏览器录音 → faster-whisper 本地转写 → opencc 繁→简 → 幻觉过滤黑名单 |
| 🎧 / 📄 双模式回答 | **语音简答**（口语 + 字数红线 + **加粗关键词** + 引导反问）\| **深度长文**（Markdown 排版 + 术语首次出现加粗 + 严格引用来源）。语音模式 TTS 自动剥离 Markdown 标记 |
| 🔍 混合 RAG 检索 | Dense (BGE-large-zh-v1.5) + Sparse (BM25) 加权融合；检索前注入知识库文档概览使 LLM 感知完整文档清单；低相关度片段自动过滤 |
| 🧠 多轮对话记忆 | SQLite 持久化 + sources 跟随存/读 + 10 轮滑动窗口 + LLM Query 改写消解指代词 |
| 🔊 语音朗读 | edge-tts 中英双语自动检测，TTS 失败时文字仍正常输出 |
| 📚 文档管理 | PDF / Word / Markdown / TXT / 源代码上传删除，向量自动索引与清理；上传时 spinner + 进度提示 + Toast 通知 |
| 🕸️ 知识图谱 | LLM 自动抽取实体&关系 → vis-network 现代化渲染（圆角节点/平滑边/箭头），文档删后自动清理孤儿节点 |
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

| 依赖 | 版本/说明 |
|------|----------|
| Python | **3.11**（推荐 [conda](https://docs.conda.io/en/latest/miniconda.html) / [venv](https://docs.python.org/3/library/venv.html) 虚拟环境） |
| Node.js | **22+** (含 npm) |
| LLM API Key | [DeepSeek](https://platform.deepseek.com/api_keys)（推荐）或 [Anthropic Claude](https://console.anthropic.com/) |
| ModelScope | `pip install modelscope`（用于下载本地 Embedding + ASR 模型） |

### 1. 克隆项目

```bash
git clone https://github.com/ThEvilxx/VoiceLearn.git
cd VoiceLearn
```

### 2. 安装依赖

```bash
make install
# 等同于:
# cd backend && pip install -r requirements.txt && pip install modelscope
# cd frontend && npm install
```

> Windows 用户若无可用的 `make`，请手动执行上述注释中的两条命令。

### 3. 配置

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，修改以下行：

```ini
# 方式 A：DeepSeek（推荐，国内无障碍）
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-deepseek-api-key
OPENAI_MODEL=deepseek-v4-pro
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 方式 B：Anthropic Claude
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key
CLAUDE_MODEL=claude-sonnet-4-6
```

其余配置保持默认即可。

### 4. 下载本地模型

```bash
# BGE Embedding 模型（~1.2GB，用于文本向量化）
python -c "from modelscope import snapshot_download; snapshot_download('BAAI/bge-large-zh-v1.5', cache_dir='backend/data/models')"

# faster-whisper 模型（~140MB，用于语音识别）
python -c "from modelscope import snapshot_download; snapshot_download('Systran/faster-whisper-base', cache_dir='backend/data/models')"
```

> ModelScope 镜像下载速度快（国内可达 20MB/s）。首次下载后模型缓存在 `backend/data/models/`，无需重复下载。

### 5. 启动

```bash
# 开发模式：前后端热重载（需要两个终端窗口）
make dev
# 前端: http://localhost:5173
# 后端: http://127.0.0.1:8000

# 生产模式：单端口 serve 一切
make prod
# 打开 http://127.0.0.1:8000
```

> **Windows 快速启动**（不用 make）：
> 打开两个终端——
> 终端 1: `cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
> 终端 2: `cd frontend && npm run dev`
> 然后浏览器访问 `http://localhost:5173`

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

- **🎧 语音模式**：字数红线 ≤120 字、结论先行、允许少量加粗关键词（TTS 自动剥离）、结尾抛引导式反问
- **📄 文字模式**：Markdown 排版、术语首次出现加粗、结构化章节、显式引用来源

### 多轮对话与 Query 改写

每轮对话持久化到 SQLite。检索前调用 `query_rewriter.py`（独立 LLM 节点，temperature=0），将"它和 RNN 有什么区别？"改写为独立检索 query。历史超限自动截断早期轮次，控制 token 预算。

### 混合检索 + 幻觉控制

Dense（BGE embedding）与 Sparse（BM25）加权融合，默认 7:3。System Prompt 强制 LLM 在解释后附带原文引用和来源文档名。

### 语音管道风控

`asr.py` 维护停用词黑名单 + opencc 自动繁→简转换，过滤 Whisper 底噪幻觉。语音模式下 `_strip_markdown()` 在 TTS 合成前剥离所有 Markdown 标记，确保不朗读"星号星号"。TTS 失败时返回空音频，绝不阻断文字输出流。静音录音 5 秒超时自动结束。

## 已知局限与后续规划

### ASR

- whisper-base 中文存在音近字偏差（"论文"→"乐文"）和中英混杂退化（BERT→Bird），**不影响 LLM 最终理解**。可通过换 medium/large 模型提升，仅改一行 `.env` 配置

### PDF 提取

- 当前使用 `pypdf` ——对双栏排版、跨栏图表、页眉页脚、脚注等多区域混合的论文存在文字流交叉。已安装但未启用的 `pdfplumber` 可显著改善
- 数学公式被渲染为矢量图形，无法从 PDF 文本层提取。直接使用 LaTeX 源码是精准保留公式和代码的唯一路径
- 部分会议论文的自定义字体可能导致字符映射错误（连字陷阱、乱码）
- 嵌入在论文中的伪代码/pseudocode 缩进无法保留
- 详细分析见 [docs/pdf-extraction-analysis.md](docs/pdf-extraction-analysis.md)

### TTS

- edge-tts 免费但偶有网络波动，不支持自定义语速/情感。TTS 失败时已实现优雅降级——文字正常输出、音频为空

### 系统架构

- 无用户鉴权 — 本地单用户模式，无登录/多租户/配额管理
- 知识图谱为手动触发快照，不感知文档增量变化。已通过 orphan 清理保证删除后对应节点移除
- 对话记忆为 10 轮滑动窗口，超限直接截断。Sources 已跟随消息持久化到 SQLite
- 未做句子级流式 TTS — 当前等待 LLM 完成全量回答后才一次性合成语音

### 后续规划项

| 规划项 | 说明 |
|--------|------|
| pypdf→pdfplumber 替换 | ~20 行 loader 改动，解决双栏/页眉/脚注交叉 |
| LaTeX 源码上传（`.tex`） | ~15 行 loader，数学公式和代码缩进完美保留 |
| 前端 VAD（语音活动检测） | 仅在真实人声时发送音频，降低 Whisper 底噪幻觉 |
| 句子级流式 TTS | 边生成文本边合成语音边播放 |
| 结构化文档切分 | 接入 `MarkdownHeaderTextSplitter`，保留章节标题到 Metadata |
| 知识图谱路由 | 事实型查询走图谱、语义型查询走向量库 |
| 跨语言检索优化 | 中英跨语言查询时自动调整 BM25/Dense 权重
