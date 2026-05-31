# VoiceLearn Bug Fix Plan — Round 2

> 来源：`docs/test2.md` 第二轮测试记录
> 涉及文件：5 个（3 后端 + 2 前端）
> 预计总工作量：~1 小时

---

## 问题分析

### 问题 1：低相关性阈值误杀（最严重）

**TEST2 证据（第 10-11 行）：**
```
这几篇论文分别研究了什么问题?
I couldn't find relevant information about that in your uploaded materials.
```

**根因：** Round 1 引入的 `low_relevance_threshold = 0.25` 过于激进。对概括性问题（"这几篇论文分别研究什么"），单个 chunk 的相关度分数天然偏低——一个 chunk 只包含一篇论文的一小段，不可能高匹配 "summarize all papers" 的 query。全部 chunk 的分数都在 0.25 附近，被一刀切过滤。

**证据二（第 18-24 行）：** 换了一种问法后（"数据库里面上传的级别论文"），retrieval 返回了分数 0.250-0.273 的 5 个 chunk，刚好在阈值边缘，侥幸通过。

**修复方案：** 将阈值从 0.25 降到 0.10。如果某 chunk 的 relevance_score 连 0.10 都不到，那确实是噪声。0.10~0.25 之间的 chunk 虽然分低但可能有相关内容，放行让 LLM 自己判断。

---

### 问题 2：文数统计严重不准

**TEST2 证据（第 35 行标题）：**
```
明明库里有四篇论文，但说只有两篇
```

**根因：** LLM 无法统计库里有几篇文档，因为：
1. 它只能看到 `top_k=8` 个检索到的 chunk 的 source 信息
2. 如果 8 个 chunk 来自 2 篇论文，LLM 就以为只有 2 篇
3. 用户说"四篇论文"可能是因为上传了 CoT、InstructGPT、Transformer、LLaMA 四篇，但某些论文的 chunk 在检索中完全被边缘化

**修复方案：** 双管齐下——(a) 增大 retrieval 结果中按 source 去重的能力 (b) 在 prompt context 中注入"数据库概览"信息，让 LLM 知道当前知识库的真实全貌。

在 `_build_rag_context` 之前调用 `list_documents()`，获取完整文档列表。在 system prompt 的 `{context}` 段开头追加一行概览：

```
当前知识库包含以下 N 篇文档：
1. AttentionIsAllYouNeed.pdf (52 chunks)
2. Chain-of-Thought Prompting...pdf (178 chunks)
3. Training_language_models_to...pdf (246 chunks)
4. LLaMA...pdf (XX chunks)

以下是检索到的最相关片段：
...
```

这样 LLM 在回答"库里有几篇论文"时不再只能靠猜。

---

### 问题 3：引用来来源展开时间太短

**根因：** ChatWindow.tsx 用 `<details>` + `<summary>` 将 source 列表折叠隐藏。默认折叠状态。

**修复方案：** 去掉 `<details>` 折叠，改为始终展开的浅色卡片。每个 source 显示文档名 + 相关度 + 内容截断，不依赖用户手动点击。

---

### 问题 4：Voice Prompt 禁止 Markdown 但代码层已剥离

**用户明确要求：** "既然代码层已经把 _strip_markdown 兜底了，就不需要在 Prompt 里禁止 Markdown。相反，要'引导'大模型克制精准地使用加粗。"

**修复方案：** 

Voice prompt 中：
- 删除 "NEVER use Markdown. No **bold**..."
- 改为 "You may use **bold** for key terms only — the TTS will read them normally. Never use other Markdown (headings, lists, code blocks)."

Text prompt 中：
- 强化加粗引导："When introducing a key term for the first time, always **bold** it. Use bold judiciously — one or two terms per paragraph, not entire sentences."

---

### 问题 5（附带）：ASR 持续误识别

**TEST2 证据：**
- "论文"→"乐文"（第 36 行）
- "核心贡献"→"核心弓箭"（第 41 行）
- "数据库里面的几篇论文"→"数据库里面上传的级别论文"（第 15 行）

**根因：** whisper-base 固有噪声，不属于代码级 bug。不纳入本轮修复。

---

## 受影响文件

| # | 文件 | 改动量 | 涉及问题 |
|---|------|--------|---------|
| 1 | `backend/app/services/chat_service.py` | ~15 行 | Q1: 阈值降低, Q2: 注入文档概览 |
| 2 | `backend/app/core/rag_chain.py` | ~10 行 | Q4: voice prompt 允许加粗, text prompt 强化加粗引导 |
| 3 | `frontend/src/components/ChatPanel/ChatWindow.tsx` | ~15 行 | Q3: 来源始终展开 |
| 4 | `frontend/src/App.css` | ~10 行 | Q3: 来源卡片样式 |
| 5 | `backend/app/services/document_service.py` | 不变 | 只是 import, chat_service 调用已有函数 |

---

## 详细修改步骤

### B7: 降低低相关性阈值 + 注入文档概览 (P0)

**文件：** `backend/app/services/chat_service.py`

**(a) 第 5 行新增 import：**

```python
from app.services.document_service import list_documents
```

**(b) 第 63 行降低阈值：**

```python
low_relevance_threshold = 0.10  # was 0.25, too aggressive for broad queries
```

**(c) 第 73 行之后（`docs = [doc for doc, _ in results]` 之后），构建 rag_context 前插入文档概览：**

```python
    # Inject a knowledge-base overview so the LLM knows the full document inventory
    all_docs = list_documents()
    kb_overview = "\n".join(
        f"- {d['name']} ({d['chunk_count']} chunks)"
        for d in sorted(all_docs, key=lambda d: d.get("name", ""))
    )
    kb_overview_block = (
        f"The knowledge base currently contains {len(all_docs)} document(s):\n"
        f"{kb_overview}\n\n"
        f"Below are the most relevant retrieved excerpts:\n"
    )

    # Build RAG context with token budget
    rag_context = _build_rag_context(docs, RAG_CONTEXT_BUDGET * CHARS_PER_TOKEN)
    rag_context = kb_overview_block + rag_context
```

> 注意：`rag_context = _build_rag_context(...)` 行原来在第 77 行，需要在前面插入 `kb_overview_block` 后拼接。

---

### B8: Voice Prompt 允许加粗 + Text Prompt 强化加粗引导 (P0)

**文件：** `backend/app/core/rag_chain.py`

**(a) Voice prompt 第 17-20 行：**

替换为：
```python
1. HARD LIMIT: Your ENTIRE answer must be under **120 Chinese characters** \
(~80 English words). Count them. If you exceed this, the TTS will cut you off.
2. You may use **bold** sparingly for key technical terms — the TTS engine \
automatically strips formatting and reads them normally. Never use any other \
Markdown (headings, lists, code blocks, blockquotes).
3. NEVER read source markers like "Source 1" aloud. \
Instead say "According to the paper..." or "The material mentions..."
```

**(b) Text prompt 第 49 行：**

替换为：
```python
7. Use Markdown formatting judiciously:
   - **Bold** every key technical term on its FIRST appearance in the answer \
(e.g. **self-attention**, **gradient descent**). One or two terms per paragraph maximum.
   - Use bullet lists for enumeration, > blockquotes for cited passages, \
and ### headings to organize sections.
```

---

### B9: 来源引用始终展开 (P0)

**文件：** `frontend/src/components/ChatPanel/ChatWindow.tsx`

**位置：** 第 144 行开始的 `<details>` 块

**替换前（约 15 行，144-163）：**

```tsx
          {msg.sources && msg.sources.length > 0 && (
            <details style={{ marginTop: 8, fontSize: "0.8rem" }}>
              <summary style={{ cursor: "pointer", opacity: 0.7 }}>
                Sources ({msg.sources.length})
              </summary>
              {msg.sources.map((s, j) => (
                <div key={j} style={{ marginTop: 4 }}>
                  [{s.document_name}] score: {s.relevance_score.toFixed(3)} — "
                  {s.content.slice(0, 120)}..."
                </div>
              ))}
            </details>
          )}
```

**替换后（始终展开的浅色来源卡片）：**

```tsx
          {msg.sources && msg.sources.length > 0 && (
            <div
              style={{
                marginTop: 10,
                padding: "0.5rem 0.7rem",
                background: "rgba(0,0,0,0.04)",
                borderRadius: 8,
                fontSize: "0.78rem",
                color: "#666",
                border: "1px solid rgba(0,0,0,0.08)",
              }}
            >
              <span style={{ fontWeight: 600, color: "#888", fontSize: "0.72rem" }}>
                Sources ({msg.sources.length})
              </span>
              {msg.sources.map((s, j) => (
                <div key={j} style={{ marginTop: 3, lineHeight: 1.45 }}>
                  <span style={{ fontWeight: 600, color: "#777" }}>
                    {s.document_name}
                  </span>
                  {" · "}
                  <span style={{ opacity: 0.6 }}>score: {s.relevance_score.toFixed(3)}</span>
                  <div style={{ color: "#999", marginTop: 1 }}>
                    "{s.content.slice(0, 180)}..."
                  </div>
                </div>
              ))}
            </div>
          )}
```

---

## 验证清单

| # | 验证动作 | 预期结果 |
|---|---------|---------|
| B7a | 📄 问 "这几篇论文分别研究了什么问题" | 不再被阈值误杀，正常返回回答 + sources |
| B7b | 📄 问 "知识库里现在有几篇文档" | 回答能准确说出文档数量（≥3） |
| B7c | 📄 问 "Transformer 那篇论文的核心贡献是什么" | 回答引用 AttentionIsAllYouNeed.pdf 的内容 |
| B8a | 🎧 语音问 "什么是自注意力机制" → 看前端文字答案 | 关键术语用 **加粗** 显示，TTS 朗读无星号 |
| B8b | 📄 文字问 "解释 Transformer" → 看前端文字答案 | 首次出现的术语是加粗的，不超过每段 2 个 |
| B9 | 📄 任意问答 → 看聊天气泡下方 | 来源卡片始终可见，不需要点 ▶ 展开 |

---

## 执行顺序

```
B7 (chat_service.py)        ← 阈值 + 文档概览，最核心
  ↓
B8 (rag_chain.py)           ← 双 Prompt 加粗策略
  ↓
B9 (ChatWindow.tsx)         ← 来源始终展开，纯前端
```

B8 的 voice prompt 改动最好和 B1（`_strip_markdown`）配合验证——确认加粗语法的文字在前端正常显示为 **粗体**、在 TTS 中被剥离为纯文本。

## 不纳入本轮修复的问题

| 问题 | TEST2 证据 | 原因 |
|------|-----------|------|
| "论文"→"乐文" | 第 36 行 | whisper-base 音近字，非代码 bug |
| "核心贡献"→"核心弓箭" | 第 41 行 | whisper-base 音近字 |
| "几篇论文"→"级别论文" | 第 15 行 | whisper-base 音近字 |
| 某次查询"搜不到 Attention 论文" | 第 36-37 行 | 同一文档在不同 query 下能/不能命中是 RAG 随机性（第 42-49 行换个窗口就找到了） |
| source 中出现 `[unknown]` | 第 48 行 | graph extraction 的副产品，非 chat 问题 |
