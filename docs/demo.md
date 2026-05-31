# VoiceLearn — 课程项目文档

## 1. 项目名称

**VoiceLearn — 语音交互式学习伴侣**

## 2. 目标用户

大学生及研究生群体。核心场景：
- 上课后录音、拍 PPT，回宿舍让 VoiceLearn 朗读总结并追问细节
- 阅读英文论文时上传 PDF，用语音提问替代逐段翻译
- 期末考试前反复问答知识点，语音播放答案强化记忆

## 3. 语音任务类型

| 任务 | 技术 | 触发方式 |
|------|------|---------|
| 语音识别 (ASR) | faster-whisper (本地 offline) | 点击麦克风按钮录制 → 自动转写 |
| 语音合成 (TTS) | edge-tts (免费, 中英双语) | RAG 答案生成后自动合成 MP3 |
| 语音交互助手 | ASR → RAG 检索 → LLM 生成 → TTS | 完整端到端，全自动链式调用 |

## 4. 痛点与需求来源

1. **英文论文阅读效率低**：手动翻译 + 笔记耗时过长，语音问答可即时获取解释
2. **跨设备不便**：手机录音、电脑打字交替，VoiceLearn 统一入口一句话完成查询
3. **记忆曲线**：纯看容易忘，反复听播反复问能多感官参与学习
4. **DeepSeek 等 LLM 知识截止**：通用模型不知道你刚上传的课件内容，RAG 填补此缺口

## 5. 核心创意与功能

- **语音全链路闭环**：麦克风说话 → ASR 转写 → RAG 检索上传的课件 → DeepSeek 生成回答 → TTS 朗读 → 浏览器播放。全程自动化
- **双模式回答**：🎧 语音简答（≤100 字，口语化，引导式反问）vs 📄 深度长文（Markdown 格式，详细引用来源）
- **多轮对话记忆**：SQLite 持久化历史，LLM Query 改写消解指代词（"它""这个"→具体实体）
- **知识图谱**：上传文档后自动抽取实体关系（NetworkX + vis-network 渲染），可视化学习脉络
- **增删文档**：支持 PDF/Markdown/TXT/Python/JS 等文件上传，RAG 实时索引 + 删除后自动清理
- **Settings 控制台**：前端切换 LLM provider、更换 API Key/Model/Base URL

## 6. 使用的工具

| 角色 | 工具 |
|------|------|
| AI 编程助手 | Claude Code (Opus 4.7) — 全部代码生成、调试、测试 |
| 大语言模型 | DeepSeek V4 Pro (通过 OpenAI 兼容 API) |
| 代码协作 | GitHub Copilot (偶尔辅助) |
| 项目管理 | Git + GitHub (`https://github.com/ThEvilxx/VoiceLearn`) |

## 7. 开发迭代过程

按 `docs/plans/2026-05-25-voicelearn-dev-plan.md` 分阶段推进：

| Phase | 内容 | 提交记录 |
|-------|------|---------|
| P1 | Backend 启动 + Embedding 加载（ModelScope BGE） | `ae8fc91` |
| P2 | 文字问答端到端（RAG + SSE 流式） | `158526f` |
| P3 | 文档上传→检索→删除全链路 | `e67d1a1` |
| P4 | 语音全通路 ASR→RAG→TTS | `e1b04f7` |
| P4.5 | 多轮对话记忆 + LLM Query 改写 | `c596dd3` |
| P4.5 | Markdown 渲染 + 语音/文字双模式回答 | `3e929cf` |
| P5 | 知识图谱提取 + 可视化（vis-network） | `bbf675a` |
| P6 | Settings 前端 + 生产模式单服务部署 | `9eddb63` |
| P7 | CSS 打磨 + 文档 | latest |

每个 Phase 均在 ruff + tsc 零错误、curl/smoke 验证通过后提交。

## 8. 不足与改进方向

- **对话记忆有限**：当前滑动窗口 10 轮，超限自动截断。后续可用 LLM 摘要压缩更早轮次
- **TTS 依赖 edge-tts**：微软 Edge TTS 免费但偶尔网络不稳定、不支持自定义语速/情感
- **ASR 依赖 Whisper base**：英语转写尚可，中文准确率有提升空间（可换 medium/large 模型）
- **知识图谱为静态抽取**：LLM 一次性抽取后存入 JSON，不感知文档更新/删除的增量变化（已通过 orphan 清理缓解）
- **未做流式 TTS**：当前 TTS 需等 LLM 全量回答后才合成，延迟 3-5 秒。理想方案是句子级截断并行合成
- **无用户鉴权**：本地单用户模式，无登录/多租户隔离
