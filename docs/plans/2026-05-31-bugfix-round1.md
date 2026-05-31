# VoiceLearn Bug Fix Plan — Round 1

> 来源：`docs/test-analysis.md` 测试记录
> 涉及文件：6 个（4 后端 + 1 前端 + 1 配置）
> 预计总工作量：~1.5 小时

---

## 受影响文件总览

| # | 文件 | 改动量 | 涉及问题 |
|---|------|--------|---------|
| 1 | `backend/app/core/asr.py` | +4 行 | B2: 繁转简 |
| 2 | `backend/app/api/chat.py` | +8 行 | B1: TTS Markdown 剥离, 附带修复 voice/stream 缺失 mode 参数 |
| 3 | `backend/app/core/rag_chain.py` | ~15 行 | B4: voice 约束增强, B5: 防幻觉指令 |
| 4 | `backend/app/hooks/useSpeech.ts` (frontend) | ~10 行 | B6: 静音超时 |
| 5 | `backend/app/services/chat_service.py` | ~10 行 | B3: 相关性阈值过滤 + 低置信度分支 |
| 6 | `backend/.env` | 1 行 | B3: TOP_K=5 → 8 |

---

## B1: TTS 朗读 Markdown 标记 (P0, low)

**文件：** `backend/app/api/chat.py`
**位置：** 第 69 行（`/voice` 端点）、第 138 行（`/voice/stream` 端点）

**问题：** `synthesize(answer)` 传入的 answer 仍含 `**` `###` 等 Markdown 标记，被 TTS 逐字朗读为"星号星号"。

**修改方案：**

(1) 文件顶部新增 import：
```python
import re
```

(2) 在 `synthesize(answer)` 调用前插入 Markdown 剥离函数，作用于 voice 端点和 voice/stream 端点两处：

```python
# 在 _to_base64 函数上方新增辅助函数
def _strip_markdown(text: str) -> str:
    """Remove Markdown formatting tokens for clean TTS reading."""
    # bold/italic markers
    text = re.sub(r"\*{1,3}[^*]+\*{1,3}", lambda m: m.group().strip("*"), text)
    # headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # blockquotes, list markers, horizontal rules
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    # inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # links: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # table pipes
    text = re.sub(r"\|", " ", text)
    return text
```

(3) 在 `/voice` 端点（第 69 行）：
```python
# Step 3: TTS
tts_text = _strip_markdown(answer)
audio = await synthesize(tts_text)
```

(4) 在 `/voice/stream` 端点（第 138 行）：
```python
# TTS
tts_text = _strip_markdown(answer)
audio = await synthesize(tts_text)
```

**附带修复：** `/voice/stream` 端点第 127-128 行遗漏了 `mode="voice"` 和 `conversation_id`：

当前代码：
```python
answer, sources, conv_id = await generate_answer(
    question, conversation_id=conversation_id
)
```

修复为：
```python
answer, sources, conv_id = await generate_answer(
    question, conversation_id=conversation_id, mode="voice"
)
```

**验证：** 语音提问后听答案 → 不应出现"星号星号"、"井号"等朗读。

---

## B2: ASR 繁体字转简体 (P0, low)

**文件：** `backend/app/core/asr.py`
**位置：** 第 61 行 `return text` 前

**问题：** whisper-base 训练语料偏向台湾/香港中文，所有转写输出为繁体。

**修改方案：**

(1) 安装依赖：
```bash
pip install opencc-python-reimplemented
```

(2) 更新 `backend/requirements.txt`：
```
opencc-python-reimplemented
```

(3) 修改 `asr.py` 第 31-36 行，在函数顶部增加懒加载：
```python
_converter: object | None = None

def _get_converter() -> object:
    global _converter
    if _converter is None:
        from opencc import OpenCC
        _converter = OpenCC("t2s")  # Traditional to Simplified
    return _converter
```

(4) 修改 `transcribe()` 第 61 行 `return text` 前：
```python
        # 繁体→简体
        text = _get_converter().convert(text)  # type: ignore[union-attr]
        return text
```

> 放在黑名单检查**之后**、`return` **之前**，第 60 行 `return text` 改为上两行。

**验证：** 语音说任意中文 → 前端显示简体字。

---

## B3: RAG 检索覆盖不全 + 低置信度策略 (P1, medium)

### B3a: 调大 top_k

**文件：** `backend/.env`
**位置：** 第 24 行

```diff
- TOP_K=5
+ TOP_K=8
```

同步更新 `.env.example` 第 24 行。

### B3b: 低相关性分数的回答策略

**文件：** `backend/app/services/chat_service.py`
**位置：** 第 52-59 行分支之后、第 61 行 `docs = [doc for doc, _ in results]` 之前

**问题：** 当 results 非空但所有 relevance_score 均 < 0.3 时，LLM 会用自己的知识"编造"答案（如"深圳天气"问题是通用知识回答而非"材料中未找到"）。

**修改方案：** 在第 59 行后（`return answer, [], conversation_id` 之后）、第 61 行前插入：

```python
    # Filter low-relevance results: if the best score is below threshold,
    # the retrieved content is probably noise — don't feed it to the LLM
    LOW_RELEVANCE_THRESHOLD = 0.25
    if all(score < LOW_RELEVANCE_THRESHOLD for _, score in results):
        answer = (
            "I couldn't find relevant information about that in your uploaded "
            "materials. Try asking about a topic covered in your notes or papers."
        )
        await add_message(conversation_id, "user", question)
        await add_message(conversation_id, "assistant", answer)
        return answer, [], conversation_id

    docs = [doc for doc, _ in results]
```

**验证：** 问"今天深圳的天气怎么样" → 应返回"未在材料中找到相关信息"而非通用气象回答。

---

## B4: Voice Prompt 约束增强 + 禁止 Markdown (P2, low)

**文件：** `backend/app/core/rag_chain.py`
**位置：** 第 13-32 行 `VOICE_SYSTEM_PROMPT`

**问题：** (1) 100 字红线约束不够强，DeepSeek 经常超标。 (2) 未明确禁止 Markdown 语法，导致 TTS 朗读 `**` 标记。

**修改方案：** 替换整个 `VOICE_SYSTEM_PROMPT`：

```python
VOICE_SYSTEM_PROMPT = """You are VoiceLearn, a voice-interactive learning companion. \
All of your answers will be read aloud via TTS, so you MUST follow these rules exactly:

CRITICAL — IF YOU VIOLATE ANY RULE THE STUDENT CANNOT UNDERSTAND YOU:
1. HARD LIMIT: Your ENTIRE answer must be under **120 Chinese characters** \
(~80 English words). Count them. If you exceed this, the TTS will cut you off.
2. NEVER use Markdown. No **bold**, no *italic*, no ### headings, \
no `code blocks`, no > blockquotes. Plain text only.
3. NEVER read source markers like "Source 1" or "(Source: xxx)" aloud. \
Instead say "According to the paper..." or "The material mentions..."
4. Lead with the one-sentence conclusion, then add 1-2 sentences of context.
5. End with ONE short follow-up question to invite deeper discussion.
6. Speak warmly and naturally, like a tutor sitting next to the student.

Conversation history between you and the student:
{history}

Context from the student's learning materials:
{context}"""
```

**验证：** 🎧 语音模式问一个问题 → 回答字数应 ≤120 字，不含 `**` 等标记。

---

## B5: 防幻觉指令注入 System Prompts (P3, low)

**文件：** `backend/app/core/rag_chain.py`
**位置：** `VOICE_SYSTEM_PROMPT` 和 `TEXT_SYSTEM_PROMPT` 末尾各加一条

**问题：** 有文档但检索未命中时，LLM 会用自身训练知识回答，而非声明"上传材料中没有相关信息"。

**修改方案：** 两个 prompt 的 context 部分之后各追加一行：

VOICE prompt 末尾追加：
```
CRITICAL: If the provided context does NOT contain information relevant \
to the student's question, say so honestly. Do NOT make up answers from \
your own knowledge — the student is only interested in what their \
uploaded materials say.
```

TEXT prompt 末尾追加（第 52 行 `{context}` 之后）：
```
IMPORTANT: When the provided context lacks information relevant to the student's \
question, state this clearly. Prioritize honesty over completeness — do not \
fabricate answers using your own training knowledge.
```

**验证：** 上传一篇关于 ML 的论文后问"今天天气怎么样" → 应声明材料中没有此信息。

---

## B6: 静音/噪音录音无超时回调 (P2, low)

**文件：** `frontend/src/hooks/useSpeech.ts`
**位置：** 第 56-62 行 `stopRecording` 函数

**问题：** 静音时 `MediaRecorder.ondataavailable` 不触发，`stopRecording` 返回的 Promise 永久挂起，UI 卡死无反馈。

**修改方案：**

```typescript
const stopRecording = useCallback((): Promise<Blob | null> => {
    const SILENCE_TIMEOUT_MS = 5000;

    const stopPromise = new Promise<Blob | null>((resolve) => {
      resolveRef.current = resolve;
      recorderRef.current?.stop();
      setIsRecording(false);
    });

    const timeoutPromise = new Promise<Blob | null>((resolve) => {
      setTimeout(() => {
        if (resolveRef.current) {
          resolveRef.current = null;
          setIsRecording(false);
          // Force-stop the recorder if it's still running
          if (recorderRef.current?.state === "recording") {
            recorderRef.current.stop();
          }
          resolve(null);
        }
      }, SILENCE_TIMEOUT_MS);
    });

    return Promise.race([stopPromise, timeoutPromise]);
  }, []);
```

**验证：** 点击录音 → 不说话 → 5 秒后点停止 → 应正常结束，麦克风按钮恢复，不卡死。

---

## 执行顺序（推荐）

```
B2 (opencc)         ← 安装依赖，最独立
  ↓
B1 (TTS Markdown)   ← 改 chat.py，附带修复 voice/stream
  ↓
B4 (voice prompt)   ← 改 rag_chain.py，与 B1 互补
  ↓
B5 (防幻觉)         ← 改 rag_chain.py，同上文件
  ↓
B3a (TOP_K)         ← 改 .env + .env.example
  ↓
B3b (低置信过滤)    ← 改 chat_service.py
  ↓
B6 (静音超时)       ← 改 useSpeech.ts，最后修前端
```

`B3a` 和 `B3b` 可合并为一个 commit。`B4` 和 `B5` 可合并为一个 commit（同文件）。

## 验证清单

| # | 验证动作 | 预期结果 |
|---|---------|---------|
| B1 | 🎧 模式提问 "解释 Transformer" | 不听到"星号星号"等 Markdown 朗读 |
| B2 | 🎤 说任意中文 | 前端显示简体字 |
| B3a | 📄 模式问"四篇论文分别讲什么" | 回答覆盖 ≥3 篇论文 |
| B3b | 📄 模式问"今天天气" | "I couldn't find relevant information..." |
| B4 | 🎧 模式提问 | 回答 ≤120 字，纯文本无 Markdown |
| B5 | 上传文档后问无关问题 | 诚实回复"未找到" |
| B6 | 点击录音后保持静音 5 秒 → 点停止 | 正常结束，不卡死 |
