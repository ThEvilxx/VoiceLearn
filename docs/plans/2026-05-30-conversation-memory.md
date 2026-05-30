# Conversation Memory Implementation Plan

**Goal:** 实现多轮对话上下文记忆，支持历史追问和指代消解。每条消息关联 `conversation_id`，历史持久化到 SQLite，超出窗口自动截断。

**Architecture:** 检索前 LLM 改写 query（消解指代词）→ 改写后的 query 检索 ChromaDB → 历史 + RAG 上下文拼入 prompt → LLM 生成答案。

**Decision log (2026-05-30):**
- 存储: SQLite (SQLAlchemy async, 新建 `conversations` + `messages` 表)
- 上下文: 滑动窗口 (可配 N, 默认 10 轮), token 超限自动截断早期
- RAG 整合: LLM 改写 query 后再检索 (对齐 CLAUDE.md 强制 Query 改写约束)
- 前端: Sidebar "New Chat" + 会话列表, `conversation_id` 切换

---

## Task 1: Database — 新建 conversations / messages 表

**Files:**
- New: `backend/app/db/models.py` — SQLAlchemy ORM 模型
- Modify: `backend/app/db/database.py` — 添加 create_all / session factory

- [ ] **Step 1: 定义模型**

```python
class Conversation(Base):
    __tablename__ = "conversations"
    id: str (UUID, PK)
    title: str (首条消息截断)
    created_at: datetime
    updated_at: datetime

class Message(Base):
    __tablename__ = "messages"
    id: int (PK, autoincrement)
    conversation_id: str (FK → conversations.id)
    role: str ("user" | "assistant")
    content: str
    created_at: datetime
```

`database.py` 需改为异步 engine + session factory (`create_async_engine` + `async_sessionmaker`)。

- [ ] **Step 2: 初始化表**

在 `main.py` lifespan 中调用 `create_all()`。

验证: 启动后端, 检查 SQLite 文件含 `conversations` + `messages` 两张表。

---

## Task 2: Service — 会话 CRUD + 历史管理

**Files:**
- New: `backend/app/services/conversation_service.py`

- [ ] **Step 1: 实现 CRUD**

```
create_conversation() → conversation_id
list_conversations() → list[ConversationMeta]
get_messages(conversation_id) → list[Message]
add_message(conversation_id, role, content) → None
delete_conversation(conversation_id) → None
```

- [ ] **Step 2: 实现滑动窗口**

`build_history_context(conversation_id, max_turns=10) → str`
取最近 max_turns 轮 (user + assistant 各算一轮), 格式化为 prompt 可用的字符串。

- [ ] **Step 3: 实现自动截断**

在 `add_message` 后检查消息总数, 超过 `max_turns * 2` 条时删除最早的。

验证: 写入 15 轮对话, 确认只保留最近 10 轮。

---

## Task 3: RAG — LLM Query 改写 + 历史注入

**Files:**
- Modify: `backend/app/services/chat_service.py` — 接收 `conversation_id`, 调用改写
- New: `backend/app/core/query_rewriter.py` — 独立查询生成节点

- [ ] **Step 1: 实现 query_rewriter**

`rewrite_query(history: str, current_question: str) → str`

用 `get_llm_for_extraction()` (temperature=0, max_tokens=256) 生成独立检索 query。

Prompt 模板:
```
Given the conversation history and the user's latest question,
generate a standalone search query that resolves any pronouns
or references to previous answers.

History:
{history}

Latest question: {question}

Standalone query:
```

- [ ] **Step 2: 改造 chat_service.generate_answer()**

签名改为 `generate_answer(question, conversation_id=None, top_k=5, use_hybrid=True)`。

流程:
1. 如果有 conversation_id → 获取历史 → 调用 `rewrite_query()` 生成独立 query
2. 用改写后的 query 检索 ChromaDB (dense/hybrid)
3. 构建 prompt: system + history + RAG context + question
4. LLM 生成答案
5. `add_message()` 双向保存 (user question + assistant answer)

- [ ] **Step 3: 构建完整 prompt 模板**

```
System: You are VoiceLearn... (现有)
History: {history_context}  
RAG Context: {context}
Human: {rewritten_query}
```

验证: 先问"A和B的区别"，再追问"它的优缺点是什么" → 确认 query 改写为"A 和 B 的优缺点"。

---

## Task 4: API — 路由更新

**Files:**
- Modify: `backend/app/api/chat.py` — text + voice 端点接收 `conversation_id`
- New: `backend/app/api/conversations.py` — 会话 CRUD API

- [ ] **Step 1: ChatRequest 增加字段**

```python
class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    use_hybrid: bool = True
    top_k: int = 5
```

- [ ] **Step 2: chat_text 端点改造**

接收 `conversation_id`, 透传给 `chat_service.generate_answer()`。没有 `conversation_id` 时自动创建新会话。

返回增加 `conversation_id` 字段。

- [ ] **Step 3: 新增 conversations API**

```
GET    /api/conversations          → list_conversations()
POST   /api/conversations          → create_conversation()  
GET    /api/conversations/{id}     → get_messages()
DELETE /api/conversations/{id}     → delete_conversation()
```

- [ ] **Step 4: Voice 端点同样改造**

`/api/chat/voice` 和 `/api/chat/voice/stream` 同样接收 `conversation_id` (从 request body/form 传入)。SSE 流式端点返回 `conversation_id` 作为首个 event。

验证: curl 发两轮对话, 确认第二轮答案引用第一轮内容。

---

## Task 5: Frontend — 会话列表 + 记忆化聊天

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx` — 管理 `conversation_id` 状态
- Modify: `frontend/src/components/Layout/Sidebar.tsx` — 会话列表 + New Chat
- Modify: `frontend/src/api/client.ts` — 新增 conversations API
- Modify: `frontend/src/types/index.ts` — 新增 ConversationMeta 类型

- [ ] **Step 1: Sidebar 增加会话列表**

```
┌─────────────┐
│ Logo        │
│─────────────│
│ + New Chat  │
│─────────────│
│ Chat 1      │  ← 点击切换
│ Chat 2      │
│ Chat 3  ✕   │  ← 点击删除
│─────────────│
│ Documents   │
│ Graph       │
│ Settings    │
└─────────────┘
```

- [ ] **Step 2: ChatPage 集成 conversation_id**

- 发送消息: 携带 `conversation_id` (无则 null, 后端自动创建)
- 收到响应: 设置 `conversation_id`
- 切换会话: 调用 `GET /api/conversations/{id}` 加载历史消息
- 新建会话: 将 `conversation_id` 置 null, 清空消息列表

- [ ] **Step 3: textChat / voiceChat client 更新**

`textChat(question, conversation_id?)` → 返回 `{answer, sources, conversation_id}`

- [ ] **Step 4: Error case 处理**

- 加载会话失败 → "Failed to load conversation"
- 删除会话失败 → "Failed to delete conversation"

验证: 浏览器内新建会话 → 发送"什么是机器学习" → 追问"那深度学习呢" → 答案引用第一轮上下文。

---

## Task 6: Token 控制 — 硬上限 + 截断日志

**Files:**
- Modify: `backend/app/services/chat_service.py`

- [ ] **Step 1: 实现 token 估算**

用 1 token ≈ 4 字符估算。总预算 4000 token (对齐 CLAUDE.md 约束)。分配:
- System prompt: ~200
- RAG context: ~2500
- History: ~1000
- Current question: ~300

- [ ] **Step 2: 截断逻辑**

在构建 prompt 前:
1. 先估算 history 的 token 数
2. 超限时从最早的消息开始删除, 直到符合预算
3. 记录截断日志 (`logging.info`)

验证: 手动构造 30 轮历史, 确认日志输出截断信息且总 prompt 在预算内。

---

## Verification Gates

| Task | Gate |
|------|------|
| Task 1 | 启动 → SQLite 含两张表 |
| Task 2 | 写入 15 轮 → 保留 10 轮 |
| Task 3 | 追问"它" → query 改写为具体实体 |
| Task 4 | curl 两轮问答 → 答案引用历史 |
| Task 5 | 浏览器前端跨会话切换 → 历史恢复 |
| Task 6 | 30 轮历史 → 截断日志 → prompt 不超限 |

## Summary

```
Task 1: DB 建表               (~30 min)
Task 2: Service CRUD + 窗口   (~45 min)
Task 3: RAG Query 改写整合    (~45 min)
Task 4: API 路由更新          (~30 min)
Task 5: Frontend 会话 UI      (~1 hr)
Task 6: Token 控制            (~30 min)
                              ─────────
                              ~4 hrs total
```

**Dependency chain:** T1 → T2 → (T3 ‖ T4) → T5. T6 在 T3 之后即可做。
