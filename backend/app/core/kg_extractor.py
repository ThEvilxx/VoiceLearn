"""
Knowledge graph entity-relation extraction using LLM.
Extracts triples (entity-relation-entity) from documents.
"""

from __future__ import annotations

import json
import logging

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm_for_extraction

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract entities and their relationships from the text below. \
Output valid JSON only.

Format:
{{
  "entities": [
    {{"id": "unique_id", "label": "Entity Name", \
"type": "person|organization|concept|technology|event|location|other"}}
  ],
  "relations": [
    {{"source": "entity_id", "target": "entity_id", "label": "relation description"}}
  ]
}}

Rules:
- Use short, readable IDs derived from the entity name (e.g. "self_attention")
- Deduplicate entities that refer to the same thing
- Only extract meaningful entities and non-trivial relationships
- For each relation, label it with a concise verb phrase
- Output ONLY the JSON, no explanation

Text:
{text}"""


async def extract_triples(text: str) -> dict:
    llm = get_llm_for_extraction()
    prompt = ChatPromptTemplate.from_messages([("human", EXTRACTION_PROMPT)])
    chain = prompt | llm | StrOutputParser()

    result = await chain.ainvoke({"text": text[:8000]})
    result = result.strip()

    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:])
        if result.endswith("```"):
            result = result[:-3]

    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        logger.warning("KG extraction JSON parse failed: %s, result[:200]=%s", e, result[:200])
        return {"entities": [], "relations": []}


async def extract_from_documents(documents: list[Document]) -> dict:
    combined_text = "\n\n".join(doc.page_content for doc in documents)
    if not combined_text.strip():
        return {"entities": [], "relations": []}
    return await extract_triples(combined_text)
