# Knowledge Graph Bilingual Extraction Plan

**Goal:** LLM 抽取实体/关系时同时输出 `label_en`（原文）和 `label_zh`（中文翻译），前端加 🌐 中/英 切换开关。用户无需重新上传文档即可在两种语言间即时切换图谱显示。

**Decision log (2026-05-31):**
- 前端切换方式：toggle 按钮，从已有数据中读取 `label_en`/`label_zh` 即时切换，不重新调 LLM
- 旧数据迁移：不写迁移脚本。旧图读取时 `label_en`=`label_zh`=原 `label` 作为 fallback。用户点 Refresh Graph 后 LLM 按新 Prompt 重新生成双语数据
- 不在本次计划中引入"自动翻译 fallback"——如果 LLM 漏了 `label_zh`，前端降级为显示 `label_en`

---

## 受影响的文件（共 5 个）

| 文件 | 改动类型 | 改动量 |
|------|---------|--------|
| `backend/app/models/graph.py` | Schema 扩展 | +2 字段 / 模型 |
| `backend/app/core/kg_extractor.py` | Prompt 重写 | ~20 行 |
| `backend/app/services/kg_service.py` | 存储 + 读取适配 | ~10 行 |
| `frontend/src/types/index.ts` | TS 类型扩增 | +2 字段 |
| `frontend/src/pages/GraphPage.tsx` | Toggle UI + 数据映射 | ~40 行 |

无新增文件，无依赖变更。

---

## Task 1: Schema 扩展（5 min）

**File:** `backend/app/models/graph.py`

```python
class GraphNode(BaseModel):
    id: str
    label: str            # kept for backward compat
    label_en: str = ""    # NEW: English/original-language label
    label_zh: str = ""    # NEW: Chinese translation
    type: str
    properties: dict
    document_ids: list[str]

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str            # kept for backward compat
    label_en: str = ""    # NEW
    label_zh: str = ""    # NEW
    weight: float

class EntityDetail(BaseModel):
    id: str
    label: str
    label_en: str = ""
    label_zh: str = ""
    type: str
    properties: dict
    related_documents: list[dict]
    related_entities: list[dict]
```

策略：`label` 保留不删（旧数据兼容），新增 `label_en`/`label_zh` 默认空字符串，使得旧 `knowledge_graph.json` 反序列化时不会报错。

---

## Task 2: Prompt 重写（10 min）

**File:** `backend/app/core/kg_extractor.py`

新 Prompt 模板：

```python
EXTRACTION_PROMPT = """Extract entities and their relationships from the text below.
Output valid JSON only.

Format:
{{
  "entities": [
    {{
      "id": "unique_id",
      "label": "Entity Name",
      "label_en": "Entity Name (original language, always required)",
      "label_zh": "实体中文翻译 (always required)",
      "type": "person|organization|concept|technology|event|location|other"
    }}
  ],
  "relations": [
    {{
      "source": "entity_id",
      "target": "entity_id",
      "label": "relation description",
      "label_en": "relation in original language (always required)",
      "label_zh": "关系中文翻译 (always required)"
    }}
  ]
}}

Rules:
- You MUST output label_en and label_zh for EVERY entity and relation.
  These fields are NEVER optional.
- label_en: the entity/relation name in its ORIGINAL language (English).
- label_zh: an accurate, concise Chinese translation.
- Use short, readable IDs derived from the English entity name.
- Deduplicate entities that refer to the same thing.
- Output ONLY the JSON, no explanation.

Text:
{text}"""
```

关键变化：
- `label` 仍然要求输出（向后兼容）
- **新增 `label_en` / `label_zh` 作为必填字段**（大写 MUST / NEVER 强调）
- 保留原有的 ID 去重、JSON-only 约束

---

## Task 3: 存储 + 读取适配（10 min）

**File:** `backend/app/services/kg_service.py`

### 3a. 写入（`build_graph()`）

```python
# 创建节点时存储双语 label
graph.add_node(
    eid,
    label=entity.get("label", eid),
    label_en=entity.get("label_en", entity.get("label", eid)),
    label_zh=entity.get("label_zh", entity.get("label", eid)),
    type=entity.get("type", "other"),
    properties=entity.get("properties", {}),
    document_ids=[doc_id],
)

# 添加边时存储双语 label
graph.add_edge(
    src, tgt,
    label=rel.get("label", ""),
    label_en=rel.get("label_en", rel.get("label", "")),
    label_zh=rel.get("label_zh", rel.get("label", "")),
    weight=1.0,
)
```

### 3b. 读取（`get_graph_data()` + `get_entity_detail()`）

```python
GraphNode(
    ...
    label_en=graph.nodes[nid].get("label_en", graph.nodes[nid].get("label", nid)),
    label_zh=graph.nodes[nid].get("label_zh", graph.nodes[nid].get("label", nid)),
)

GraphEdge(
    ...
    label_en=attrs.get("label_en", attrs.get("label", "")),
    label_zh=attrs.get("label_zh", attrs.get("label", "")),
)
```

逻辑：取 `label_en`/`label_zh`，若 graph JSON 中不存在（旧数据）则 fallback 到 `label`。

---

## Task 4: 前端类型 + Toggle 按钮（20 min）

### 4a. `frontend/src/types/index.ts`

```typescript
export interface GraphNode {
  id: string;
  label: string;
  label_en?: string;
  label_zh?: string;
  type: string;
  properties: Record<string, unknown>;
  document_ids: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  label_en?: string;
  label_zh?: string;
  weight: number;
}
```

### 4b. `frontend/src/pages/GraphPage.tsx`

**状态：** `const [lang, setLang] = useState<"zh" | "en">("zh")`

**数据清洗时按语言选择 label：**

```typescript
const activeLang = lang; // captures current value for use inside filter/map
const safeNodes = data.nodes.map((n) => ({
  id: String(n.id),
  label: String(
    (activeLang === "zh" ? n.label_zh : n.label_en) || n.label_zh || n.label_en || n.label || n.id
  ),
}));
```

**Toggle UI（放在 Refresh Graph 按钮旁边）：**

```tsx
<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
  <button
    onClick={() => setLang(lang === "zh" ? "en" : "zh")}
    style={{
      padding: "4px 12px",
      borderRadius: 14,
      border: "1px solid #ccc",
      background: "transparent",
      color: "#666",
      cursor: "pointer",
      fontSize: "0.85rem",
    }}
  >
    {lang === "zh" ? "🌐 English" : "🌐 中文"}
  </button>
  <button onClick={handleReload} ...>Refresh Graph</button>
</div>
```

`useEffect` 依赖数组加上 `[data, lang]`，语言切换时重新构建 `finalData` 并重建 vis-network。

---

## Verification

| 步骤 | 预期 |
|------|------|
| 上传一篇英文论文 → Refresh Graph | 节点显示中文标签，边标签为中文翻译 |
| 点击 🌐 English 按钮 | 画布即时切换为英文标签，连线标签同步切换 |
| 再次点击 🌐 中文 | 切回中文 |
| 旧图（单语 label）直接加载 | 中英显示相同文本（fallback to label），不报错、不白屏 |
| Refresh Graph 后 | LLM 重新生成数据，中英标签分别正确显示 |

## Summary

```
Task 1: Schema (graph.py)         ~5 min
Task 2: Prompt (kg_extractor.py)  ~10 min
Task 3: Storage (kg_service.py)   ~10 min
Task 4: Frontend (types + toggle) ~20 min
                                  ────────
                                  ~45 min total
```

**风险点：** 唯一不可控的是 LLM 是否严格遵守 `label_zh` 必填要求。如果 DeepSeek 偶尔漏字段，前端 fallback 链确保不白屏。
