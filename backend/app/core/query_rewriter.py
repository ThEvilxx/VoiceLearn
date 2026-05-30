"""Query rewriter — resolves pronouns and references using conversation history."""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm_for_extraction

REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given the conversation history and the student's latest question, "
            "generate a standalone search query that resolves any pronouns "
            "(like 'it', 'this', 'they') and references to previous answers.\n\n"
            "Rules:\n"
            "1. Output ONLY the rewritten query, no explanation.\n"
            "2. Keep the original language of the question.\n"
            "3. If the question is already standalone, return it unchanged.",
        ),
        ("human", "History:\n{history}\n\nLatest question: {question}\n\nStandalone query:"),
    ]
)

_rewrite_chain = REWRITE_PROMPT | get_llm_for_extraction() | StrOutputParser()


async def rewrite_query(history: str, question: str) -> str:
    if not history.strip():
        return question
    try:
        result = await _rewrite_chain.ainvoke(
            {"history": history, "question": question}
        )
        return result.strip() or question
    except Exception:
        return question
