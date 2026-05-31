# VoiceLearn 测试问题分析报告

> 来源：`docs/test.md` — 语音+RAG+多轮对话实测记录
> 日期：2026-05-31

---

## 问题清单

### 1. TTS 朗读 Markdown 标记（P0）

**现象：** 语音模式下，LLM 输出中的 `**加粗语法**` 被 TTS 逐字朗读为"星号星号"。

**根因：** `chat.py` 中 voice 端点调用 `synthesize(answer)` 前未剥离 Markdown 标记。LLM 即使收到 voice prompt 约束，偶尔仍输出 `**Transformer**` 这类强调语法。

**修复方向：** `synthesize()` 调用前加正则剥离 `**` `*` `###` `>` 等 Markdown 标记。

**修复难度：** 低

---

### 2. 繁体字未转换（P0）

**现象：** 全文输出繁体："查詢""標題""詳細內容""區別""極致"。之前已确认加入 opencc，未执行。

**根因：** `asr.py` 的 `transcribe()` 返回前未调用繁转简。

**修复方向：** `pip install opencc-python-reimplemented` → `asr.py` 中 `return text` 前加 `opencc.convert(text)`。

**修复难度：** 低

---

### 3. ASR 音近字误识（P1）

**现象：** "论文"反复被识别为"樂文"（全文出现 4 次）。

**根因：** whisper-base 中文语料不足，对轻声韵母（-un/-en）区分能力弱。

**修复方向：** 可换 whisper-medium 模型（精度↑，加载时间↑）。短期可接受、不阻塞。

**修复难度：** 中（模型替换涉及下载+配置）

---

### 4. ASR 中英混杂误识（P1）

**现象：** "BERT"→"Bird"，"attention mechanism"→"attention by channeling"。Whisper 对中英混杂场景倾向把英文词强行映射到中文字库。

**根因：** whisper-base 强制将音频映射到同语种 token 空间。

**修复方向：** 同 #3，换 medium/large 可改善。不换模型则短期无有效修复。

**修复难度：** 中

---

### 5. 检索覆盖不全（P1）

**现象：** 问"四个论文分别讲什么"，回答只提到 2 篇（InstructGPT + LLaMA），漏了 CoT 和 Transformer。用户追问后才修正。

**根因：** `top_k=5` 从多篇论文的 chunks 中可能只召回了 2 篇的内容。BM25 的分词/加权方式可能导致某篇论文完全边缘化。

**修复方向：**
- 调大 `top_k`（如 8→10）
- 检查 `search_hybrid` 中 dense/BM25 的 7:3 权重是否合适
- 考虑按文档来源去重后补全（retrieve top-N per document, not top-N global）

**修复难度：** 中

---

### 6. 静音/噪音无回调（P2）

**现象：** "一直卡了，没有反应"——静音时点停止录音，界面无任何反馈。

**根因：** `useSpeech.ts` 的 `stopRecording` 没有超时保护。静音时 MediaRecorder 的 `ondataavailable` 不触发，`stopRecording` 返回的 Promise 永远不 resolve。

**修复方向：** `stopRecording` 内加 `Promise.race` + 5 秒超时，超时返回空 blob 并在 UI 提示"未检测到语音"。

**修复难度：** 低

---

### 7. voice 模式回答超长（P2）

**现象：** voice 模式下回答 3 段文字 + 反问，远超 100 字红线。

**根因：** `VOICE_SYSTEM_PROMPT` 中"≤100 Chinese characters"的约束对 DeepSeek 约束力不够强。

**修复方向：** prompt 调优——大写强调、增加惩罚性措辞（"IF YOUR ANSWER EXCEEDS 100 CHARACTERS THE STUDENT WILL FALL ASLEEP"）、或在代码层做硬截断。

**修复难度：** 低

---

### 8. 知识库外问题回答策略不一致（P3）

**现象：** "深圳天气"没有提示"你上传的材料里没有相关信息"，而是做了通用知识回答。与空知识库时的行为（"I couldn't find any relevant information…"）不一致。

**根因：** 空知识库走的是 `if not results: return "no relevant info"` 分支（chat_service.py）。有文档但 RAG 未命中时，LLM 仍能用自身知识回答。两条路径的行为未统一。

**修复方向：** 当 RAG source 的 relevance_score 普遍低于阈值时（如 <0.3），system prompt 中追加"如果没有找到相关材料，直接告知学生，不要用你自己的知识编造答案"。

**修复难度：** 低

---

## 根因分类汇总

| 类别 | 问题数 | 问题编号 |
|------|--------|---------|
| whisper-base 模型能力上限 | 3 | #1, #3, #4 |
| 代码管道缺失环节 | 2 | #2 (繁体), #5 (TTS Markdown) |
| Prompt/RAG 参数调优 | 2 | #6 (覆盖不全), #8 (voice 约束) |
| 前端交互缺陷 | 1 | #7 (静音无回调) |
| 策略不一致 | 1 | #9 (知识库外回答) |

## 优先级

| 优先级 | 数量 | 严重程度 |
|--------|------|---------|
| P0 (立即修) | 2 | TTS Markdown 剥离、繁转简 |
| P1 (近期修) | 3 | ASR 识别精度、检索覆盖 |
| P2 (择机修) | 2 | 静音回调、voice 约束 |
| P3 (关注) | 1 | 知识库外回答策略 |

## 修复顺序建议

1. **P0-1: TTS Markdown 剥离** — `chat.py` voice 端点 `synthesize()` 前加 `re.sub(r'[*#>`~_]+', '', text)`
2. **P0-2: opencc 繁转简** — `pip install opencc-python-reimplemented` + `asr.py` 一行转换
3. **P1-1: 调大 top_k** — `.env` 中 `TOP_K=5` → `TOP_K=8`
4. **P1-2: 增强 voice prompt** — `VOICE_SYSTEM_PROMPT` 中数字和惩罚措辞
5. **P2-1: 静音超时** — `useSpeech.ts` `Promise.race` 5 秒超时
6. **P2-2: 知识库外策略** — system prompt 追加防幻觉指令
