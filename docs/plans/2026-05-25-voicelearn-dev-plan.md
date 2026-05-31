# VoiceLearn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a voice-interactive learning companion — upload course notes/papers, then ask questions by voice and hear spoken answers.

**Architecture:** FastAPI backend serves REST + SSE APIs; React frontend captures mic audio via MediaRecorder → HTTP POST → backend runs ASR (faster-whisper) → RAG retrieval (ChromaDB hybrid) → LLM generation (DeepSeek/Claude) → TTS (edge-tts) → returns text + MP3 audio to browser. One-command startup via Makefile.

**Tech Stack:** Python 3.11 (FastAPI, LangChain, ChromaDB, faster-whisper, edge-tts) + TypeScript 6 (React 19, Vite 8, vis-network)

**Current state (2026-05-25):** 57 source files created, skeleton complete, all dependencies installed, ruff checks pass, tsc --noEmit passes, zero runtime testing done.

---

## Development Standards (referenced throughout)

Every task must satisfy these before being marked complete:

| Check | Command | Scope |
|-------|---------|-------|
| Python lint | `cd backend && ruff check app/` | All Python changes |
| Python types | `cd backend && mypy app/ --ignore-missing-imports` | All Python changes |
| TS lint | `cd frontend && npm run lint` | All TS changes |
| TS types | `cd frontend && npx tsc --noEmit` | All TS changes |
| Python style | `pathlib.Path` only, config via `config.settings` singleton, LLM via `core/llm.py` factory | All Python changes |
| TS style | React 19 function components + Hooks, pages/components/api/types separation | All TS changes |

---

## Phase 1: Backend Smoke Test (健康检查)

**Goal:** Verify FastAPI starts, `/api/health` responds, embedding model loads, no import errors.

### Task 1.1: First startup

**Files:**
- Verify: `backend/app/main.py`
- Verify: `backend/app/config.py`
- Verify: `backend/.env`

- [ ] **Step 1: Start backend**

```bash
cd VoiceLearn\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: Server starts. If BGE model not downloaded, it will download ~1.3GB on first run.

- [ ] **Step 2: Verify health endpoint**

```bash
curl http://127.0.0.1:8000/api/health
```

Expected: `{"status":"ok","app":"VoiceLearn"}`

- [ ] **Step 3: Verify embedding model loaded**

Check console output for: `Loading embedding model...` → `Embedding model loaded.`
No `ImportError` or `FileNotFoundError` for model path.

- [ ] **Step 4: Fix any startup errors**

Common issues:
- **BGE model download blocked (HuggingFace GFW)**: Switch to ModelScope download:
  ```bash
  python -c "
  from modelscope import snapshot_download
  snapshot_download('BAAI/bge-large-zh-v1.5', cache_dir='backend/data/models')
  "
  ```
  Then set `.env`: `EMBEDDING_MODEL=./data/models/bge-large-zh-v1.5`
- **Port 8000 in use**: Change port in `.env`: `PORT=8001`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: verify backend startup, fix embedding model path if needed"
```

**Verification gate:** `/api/health` returns 200 + embedding model loads without error.

---

## Phase 2: Text Chat End-to-End (文字问答通路)

**Goal:** User types a question → backend retrieves from ChromaDB → LLM generates answer → frontend displays it. No voice yet. No documents yet (will fail gracefully with "no relevant information").

### Task 2.1: Test backend /api/chat endpoint

**Files:**
- Test: `backend/app/api/chat.py`
- Test: `backend/app/services/chat_service.py`

- [ ] **Step 1: Test with empty knowledge base**

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is machine learning?"}'
```

Expected: Returns `{"answer": "I couldn't find any relevant information...", "sources": []}`

- [ ] **Step 2: Verify LLM connectivity**

If the `rag_chain.py` line `prompt | llm | StrOutputParser()` throws a connection error (DeepSeek API key, network), fix in `.env`:
```
OPENAI_API_KEY=sk-<your-key>
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=DeepSeek-V4-pro[1m]
LLM_PROVIDER=openai
```

Alternative: switch to Claude by setting `LLM_PROVIDER=claude` + valid `ANTHROPIC_API_KEY`.

- [ ] **Step 3: Test streaming endpoint**

```bash
curl -X POST http://127.0.0.1:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Explain deep learning in one sentence."}' \
  --no-buffer
```

Expected: SSE events with `event: sources` then `event: message`.

- [ ] **Step 4: Fix backend issues if any**

Common issues in `chat_service.py`:
- `qa_chain.steps` / `qa_chain.middle` / `qa_chain.first` — these accessor patterns on LCEL `RunnableSequence` may differ by LangChain version. If `answer_stream()` errors, replace with:
```python
async def answer_stream(question, top_k=5, use_hybrid=True):
    answer, _ = await generate_answer(question, top_k, use_hybrid)
    yield answer
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: text chat API working with LLM connectivity"
```

### Task 2.2: Wire frontend text chat

**Files:**
- Verify: `frontend/src/pages/ChatPage.tsx`
- Verify: `frontend/src/api/client.ts`
- Verify: `frontend/src/components/ChatPanel/ChatWindow.tsx`
- Verify: `frontend/src/components/ChatPanel/ChatInput.tsx`

- [ ] **Step 1: Start frontend dev server**

```bash
cd VoiceLearn\frontend
npm run dev
```

Expected: Vite starts on `http://localhost:5173`

- [ ] **Step 2: Test text chat in browser**

Open `http://localhost:5173`, type a question in the chat input, press Send.

Expected:
- User message bubble appears (blue, right-aligned)
- Loading indicator shows "VoiceLearn is thinking..."
- Assistant response bubble appears (gray, left-aligned)
- Sources are expandable via "Sources (N)" dropdown

- [ ] **Step 3: Fix frontend issues**

Common issues:
- **API proxy not working**: Vite proxy in `vite.config.ts` should forward `/api` to `http://127.0.0.1:8000`. Verify the proxy config.
- **CORS error**: Backend CORS middleware must allow `http://localhost:5173`. Check `main.py` has `allow_origins=["http://localhost:5173", ...]`.
- **Empty state**: If `messages` array is empty, the welcome message should show: "Upload a document, then ask a question — by voice or text."

- [ ] **Step 4: Test error state**

Stop the backend, send a message. Expected: "Sorry, something went wrong. Please try again." (not a blank screen or infinite spinner).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: frontend text chat wired end-to-end"
```

**Verification gate:** Type question → get answer with sources displayed in browser. Error state handled gracefully.

---

## Phase 3: Document Ingestion + RAG (文档摄入与检索问答)

**Goal:** Upload a PDF → system indexes it → ask questions about its content → get cited answers.

### Task 3.1: Test backend document upload

**Files:**
- Verify: `backend/app/api/documents.py`
- Verify: `backend/app/services/document_service.py`
- Verify: `backend/app/core/loader.py`
- Verify: `backend/app/core/splitter.py`

- [ ] **Step 1: Upload a test PDF**

```bash
# Create a simple test file
echo "Machine learning is a subset of artificial intelligence. It enables systems to learn from data without explicit programming. Deep learning uses neural networks with many layers." > /tmp/test-ml.txt

curl -X POST http://127.0.0.1:8000/api/documents \
  -F "file=@/tmp/test-ml.txt"
```

Expected: `{"status":"ready","document_id":"<uuid>","name":"test-ml.txt","file_type":"txt","chunk_count":1}`

- [ ] **Step 2: List documents**

```bash
curl http://127.0.0.1:8000/api/documents
```

Expected: Array with the uploaded document.

- [ ] **Step 3: Test RAG Q&A with ingested document**

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is machine learning?"}'
```

Expected: Answer references the uploaded content. Sources array is non-empty. Source content shows relevant text.

- [ ] **Step 4: Test hybrid search vs dense-only**

```bash
# Hybrid (default)
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"neural networks and deep learning","use_hybrid":true}'

# Dense only
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"neural networks and deep learning","use_hybrid":false}'
```

Both should return relevant results.

- [ ] **Step 5: Test delete**

```bash
curl -X DELETE http://127.0.0.1:8000/api/documents/<doc_id>
curl http://127.0.0.1:8000/api/documents  # Should be empty
```

- [ ] **Step 6: Test error cases**

```bash
# No file
curl -X POST http://127.0.0.1:8000/api/documents -F "file=@/nonexistent"
# Delete non-existent doc
curl -X DELETE http://127.0.0.1:8000/api/documents/fake-id
```

Expected: Appropriate error responses, not 500 crashes.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: document ingestion pipeline working, RAG returns cited answers"
```

### Task 3.2: Wire frontend document management

**Files:**
- Verify: `frontend/src/pages/DocumentsPage.tsx`
- Verify: `frontend/src/api/client.ts`

- [ ] **Step 1: Test upload UI**

Navigate to http://localhost:5173/documents, click "Upload Document", select a PDF/TXT file.

Expected: Document appears in list with name, file type, chunk count.

- [ ] **Step 2: Test delete UI**

Click "Delete" on a document.

Expected: Document disappears from list. Refreshing confirms deletion.

- [ ] **Step 3: Test cross-page flow**

Upload a document → switch to Chat page → ask a question about it.

Expected: Answer references the uploaded document.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: frontend document upload and management complete"
```

**Verification gate:** Upload PDF → ask question → get cited answer showing source document name. Delete document → answers become "no relevant information."

---

## Phase 4: Voice Pipeline (语音全通路)

**Goal:** Click mic button → speak → ASR transcribes → RAG answers → TTS speaks back → user hears audio.

### Task 4.1: Test ASR in isolation

**Files:**
- Verify: `backend/app/core/asr.py`

- [ ] **Step 1: Test faster-whisper model loads**

```bash
python -c "
from app.core.asr import transcribe
# Test with silence/empty — should return empty string
result = transcribe(b'')
print(f'Empty audio result: [{result}]')
print('ASR model loaded OK')
"
```

Expected: Whisper `base` model downloads on first run (~140MB), then prints "ASR model loaded OK".

- [ ] **Step 2: Record test audio and transcribe**

Use PowerShell or browser to record a short WAV saying "what is machine learning". Then:

```bash
python -c "
from app.core.asr import transcribe_file
from pathlib import Path
text = transcribe_file(Path('/tmp/test-question.wav'))
print(f'Transcribed: [{text}]')
"
```

Expected: Prints the spoken text accurately.

### Task 4.2: Test TTS in isolation

**Files:**
- Verify: `backend/app/core/tts.py`

- [ ] **Step 1: Test TTS synthesis**

```bash
python -c "
import asyncio
from app.core.tts import synthesize

async def test():
    audio = await synthesize('你好，我是你的学习助手。')
    print(f'Audio bytes: {len(audio)}')
    # Save for manual playback check
    with open('/tmp/tts-test.mp3', 'wb') as f:
        f.write(audio)
    print('Saved to /tmp/tts-test.mp3 — play it to verify voice quality')

asyncio.run(test())
"
```

Expected: Generates MP3 bytes. Play the file to verify Chinese voice quality.

- [ ] **Step 2: Test language auto-detection**

```bash
python -c "
import asyncio
from app.core.tts import synthesize, _detect_voice

print('Chinese text voice:', _detect_voice('你好世界'))
print('English text voice:', _detect_voice('Hello world, this is a test'))
# Should pick zh-CN-XiaoxiaoNeural for Chinese, en-US-JennyNeural for English

async def test():
    en_audio = await synthesize('Machine learning is a subset of AI.')
    zh_audio = await synthesize('机器学习是人工智能的一个分支。')
    print(f'EN audio: {len(en_audio)} bytes, ZH audio: {len(zh_audio)} bytes')

asyncio.run(test())
"
```

### Task 4.3: Test /api/chat/voice endpoint

**Files:**
- Verify: `backend/app/api/chat.py` (the `/voice` and `/voice/stream` routes)

- [ ] **Step 1: Send recorded audio to voice endpoint**

After recording a WAV file of a question:

```bash
curl -X POST http://127.0.0.1:8000/api/chat/voice \
  --data-binary @/tmp/test-question.wav \
  -H "Content-Type: audio/webm"
```

Expected: Response contains `{"question": "...", "answer": "...", "audio_base64": "...", "sources": [...]}`

- [ ] **Step 2: Decode and play returned audio**

```bash
python -c "
import json, base64
# Paste the JSON response or read from file
data = json.loads(open('/tmp/voice-response.json').read())
audio = base64.b64decode(data['audio_base64'])
with open('/tmp/voice-answer.mp3', 'wb') as f:
    f.write(audio)
print('Saved answer audio to /tmp/voice-answer.mp3')
"
```

Play the file. Expected: Natural-sounding voice speaking the answer.

- [ ] **Step 3: Test voice streaming endpoint**

```bash
curl -X POST http://127.0.0.1:8000/api/chat/voice/stream \
  --data-binary @/tmp/test-question.wav \
  -H "Content-Type: audio/webm" \
  --no-buffer
```

Expected: SSE events: `question` → `sources` → `message` → `audio`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: voice pipeline working — ASR→RAG→TTS end-to-end"
```

### Task 4.4: Wire frontend voice button

**Files:**
- Verify: `frontend/src/components/ChatPanel/VoiceButton.tsx`
- Verify: `frontend/src/hooks/useSpeech.ts`
- Verify: `frontend/src/api/client.ts` (the `voiceChat` function)
- Verify: `frontend/src/pages/ChatPage.tsx` (the `handleVoice` callback)

- [ ] **Step 1: Test browser mic permission**

Open `http://localhost:5173`, click the mic button. Expected: Browser shows "Allow microphone" prompt. After allowing, button turns red with pulse animation and shows "Listening..."

- [ ] **Step 2: Test recording and voice chat**

Click mic → speak a question → click stop. Expected:
- User message bubble with transcribed text
- Loading indicator
- Assistant response with answer text
- Audio player below the answer (playable in-browser)
- Sources expandable

- [ ] **Step 3: Test error states**

- Deny mic permission → expected: error message "Cannot access microphone"
- Send empty/silent recording → expected: "Could not transcribe audio" or graceful fallback
- Backend down during voice request → expected: "Sorry, voice processing failed"

- [ ] **Step 4: Fix issues found during testing**

Common issues in `useSpeech.ts`:
- MIME type `audio/webm` may not be supported in all browsers. Add fallback:
  ```typescript
  const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : 'audio/webm';
  ```

Common issues in `VoiceButton.tsx`:
- The `@keyframes pulse` animation is defined in `App.css` — verify it's loading.
- Button disabled state when `loading` — verify it doesn't allow concurrent recordings.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: frontend voice recording and playback integrated"
```

**Verification gate:** Click mic → speak → see transcribed text → read answer → hear spoken answer via audio player. Error states handled gracefully.

---

## Phase 5: Knowledge Graph (知识图谱)

**Goal:** After uploading documents, click "Refresh Graph" → see entity-relationship visualization.

### Task 5.1: Test backend graph building

**Files:**
- Verify: `backend/app/api/knowledge_graph.py`
- Verify: `backend/app/services/kg_service.py`
- Verify: `backend/app/core/kg_extractor.py`

- [ ] **Step 1: Trigger graph build**

```bash
curl -X POST http://127.0.0.1:8000/api/graph/reload
```

Expected: `{"nodes": N, "edges": M}` with N > 0 if documents exist.

- [ ] **Step 2: Retrieve graph data**

```bash
curl http://127.0.0.1:8000/api/graph | python -m json.tool | head -30
```

Expected: JSON with `nodes` and `edges` arrays, each node has `id`, `label`, `type`.

- [ ] **Step 3: Test entity detail**

```bash
curl http://127.0.0.1:8000/api/graph/entity/machine_learning
```

Expected: Entity detail with `related_documents` and `related_entities`.

- [ ] **Step 4: Fix common issues**

If `build_graph` returns 0 nodes:
- Check `kg_extractor.py` `extract_triples()` — the `text[:4000]` truncation may cut off entities. Try increasing to 8000 for longer documents.
- Check LLM output parsing — `json.loads()` may fail silently. Add logging:

```python
try:
    return json.loads(result)
except json.JSONDecodeError as e:
    logging.warning(f"KG extraction JSON parse failed: {e}, result[:200]={result[:200]}")
    return {"entities": [], "relations": []}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: knowledge graph extraction and API working"
```

### Task 5.2: Wire frontend graph visualization

**Files:**
- Verify: `frontend/src/pages/GraphPage.tsx`
- Verify: `frontend/src/api/client.ts` (the `getGraph` and `reloadGraph` functions)

- [ ] **Step 1: Test graph page**

Navigate to `http://localhost:5173/graph`. Click "Refresh Graph".

Expected: Wait ~10s, then vis-network renders nodes and edges. Nodes show entity labels, edges show relationship labels.

- [ ] **Step 2: Test interaction**

- Drag nodes → reposition works
- Scroll to zoom → zoom in/out works
- Click a node → should show detail (if implemented, otherwise just highlighting)

- [ ] **Step 3: Test empty state**

Delete all documents → refresh graph. Expected: "No knowledge graph yet. Upload documents and click Refresh Graph."

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: knowledge graph visualization integrated"
```

**Verification gate:** Upload doc → Refresh Graph → see entity-relationship network in browser. Empty state handled.

---

## Phase 6: Settings & Production Mode (设置与生产部署)

**Goal:** LLM/embedding/chunking settings are configurable; one-command production startup works.

### Task 6.1: Test settings API

**Files:**
- Verify: `backend/app/api/settings.py`

- [ ] **Step 1: Test read settings**

```bash
curl http://127.0.0.1:8000/api/settings/llm
curl http://127.0.0.1:8000/api/settings/chunking
```

Expected: Current settings values.

- [ ] **Step 2: Test update settings**

```bash
curl -X PUT http://127.0.0.1:8000/api/settings/llm \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","openai_model":"gpt-4o"}'
```

Expected: `{"status":"ok","provider":"openai"}`

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: settings API read/write verified"
```

### Task 6.2: Production mode

**Files:**
- Verify: `Makefile`
- Verify: `backend/app/main.py` (static file serving)

- [ ] **Step 1: Build frontend**

```bash
cd VoiceLearn\frontend
npm run build
```

Expected: `frontend/dist/` created with compiled assets.

- [ ] **Step 2: Test single-service startup**

```bash
cd VoiceLearn
make prod
```

Expected: Server starts. `http://127.0.0.1:8000` serves the frontend. `/api/health` still works.

- [ ] **Step 3: Verify full flow in production mode**

Browse `http://127.0.0.1:8000` → upload doc → voice chat. Everything works without port 5173.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: production single-service mode working"
```

**Verification gate:** `make prod` → one URL serves everything.

---

## Phase 7: Polish & Demo (打磨与录屏)

**Goal:** UI polish, demo-ready state, recording preparation.

### Task 7.1: UI polish

**Files:**
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/components/ChatPanel/ChatWindow.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Fix Settings page placeholder**

Replace the text "Settings UI coming soon" with actual LLM provider selector form. Read current config from `/api/settings/llm`, render dropdown + text fields, PUT on save.

- [ ] **Step 2: Polish CSS**

- Chat bubble max-width responsive on mobile
- Mic button sizing consistent
- Dark mode support? (optional, low priority for demo)

- [ ] **Step 3: Add loading spinners to document upload and graph refresh**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "style: UI polish, settings page, loading states"
```

### Task 7.2: Prepare demo

- [ ] **Step 1: Prepare demo materials**

1. Upload 2-3 relevant documents (a course PPT as PDF, a paper as PDF, a Markdown note)
2. Prepare 3-4 demo questions for the recording
3. Test the full flow twice end-to-end

- [ ] **Step 2: Record demo video**

Script:
```
1. Show homepage → explain "this is VoiceLearn"
2. Upload a paper PDF → show it in document list
3. Switch to Chat → type a question → show text answer with sources
4. Click mic → ask a question by voice → show transcribed text
5. Wait for answer → play audio response → show sources
6. Switch to Knowledge Graph → click Refresh → show the graph
7. Click a node → show entity detail
8. Show Settings page
```

- [ ] **Step 3: Write documentation**

Per course requirements:
1. **项目名称**: VoiceLearn — 语音交互式学习伴侣
2. **目标用户**: 大学生/研究生
3. **语音任务类型**: ASR + TTS + 语音交互助手
4. **痛点/需求来源**: (fill from your earlier brainstorming)
5. **核心创意与功能**: (summarize from README.md)
6. **使用的工具**: Claude Code + DeepSeek API
7. **开发迭代过程**: (summarize from git log + your experience)
8. **不足与改进方向**: conversation memory not implemented, voice quality depends on edge-tts, etc.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "docs: demo preparation, course documentation"
```

**Verification gate:** Demo video recorded, all course materials ready for submission.

---

## Summary: Phase Completion Order

```
Phase 1: Backend smoke test         (~30 min, includes BGE model download)
Phase 2: Text chat E2E              (~1 hr)
Phase 3: Document ingestion + RAG   (~1 hr)
Phase 4: Voice pipeline             (~2 hrs, includes Whisper model download)
Phase 5: Knowledge graph            (~1 hr)
Phase 6: Settings + production mode (~30 min)
Phase 7: Polish + demo              (~2 hrs)
                                    ─────────
                                    ~8 hrs total
```

**Dependency chain:** P1 → P2 → (P3 ‖ P4) → P5 → P6 → P7.
- P3 and P4 are independent, can be done in parallel.
- P1 is the critical path — if embedding model download is blocked, everything else stalls.

**After every task:** run the verification gates listed in the task. Don't move to the next task until the current one passes.
