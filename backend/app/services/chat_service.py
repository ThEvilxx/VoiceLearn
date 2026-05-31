"""Chat service: RAG Q&A with conversation memory and token control."""

from __future__ import annotations

import logging

from app.core.query_rewriter import rewrite_query
from app.core.rag_chain import format_docs, get_qa_chain
from app.core.vector_store import search_hybrid, search_similar
from app.models.chat import SourceDocument
from app.services.conversation_service import (
    add_message,
    build_history_context,
    create_conversation,
)

logger = logging.getLogger(__name__)

# Token budget (1 token ≈ 4 chars for CJK-friendly estimation)
CHARS_PER_TOKEN = 4
RAG_CONTEXT_BUDGET = 2500  # tokens
HISTORY_BUDGET = 1000  # tokens


async def generate_answer(
    question: str,
    conversation_id: str | None = None,
    top_k: int = 5,
    use_hybrid: bool = True,
    mode: str = "text",
) -> tuple[str, list[SourceDocument], str]:
    """Generate an answer using RAG with conversation memory.

    mode: "voice" for concise spoken answers, "text" for detailed markdown.
    Returns (answer_text, list_of_sources, conversation_id).
    """

    # Ensure we have a conversation
    if not conversation_id:
        conversation_id = await create_conversation(title=question[:100])

    # Get history and rewrite query
    history = await build_history_context(conversation_id)
    search_query = await rewrite_query(history, question)

    # Retrieve with rewritten query
    if use_hybrid:
        results = search_hybrid(search_query, top_k=top_k)
    else:
        results = search_similar(search_query, top_k=top_k)

    if not results:
        answer = (
            "I couldn't find any relevant information in your learning materials "
            "to answer this question. Try uploading some course notes or papers first."
        )
        await add_message(conversation_id, "user", question)
        await add_message(conversation_id, "assistant", answer)
        return answer, [], conversation_id

    # Filter low-relevance results: if the best score is below threshold,
    # the retrieved content is probably noise — don't feed it to the LLM
    low_relevance_threshold = 0.25
    if all(score < low_relevance_threshold for _, score in results):
        answer = (
            "I couldn't find relevant information about that in your uploaded "
            "materials. Try asking about a topic covered in your notes or papers."
        )
        await add_message(conversation_id, "user", question)
        await add_message(conversation_id, "assistant", answer)
        return answer, [], conversation_id

    docs = [doc for doc, _ in results]
    scores = [score for _, score in results]

    # Build RAG context with token budget
    rag_context = _build_rag_context(docs, RAG_CONTEXT_BUDGET * CHARS_PER_TOKEN)
    history_context = _truncate_history(history, HISTORY_BUDGET * CHARS_PER_TOKEN)

    # Generate answer with mode-aware prompt
    chain = get_qa_chain(mode)
    answer = await chain.ainvoke(
        {
            "history": history_context or "(no previous conversation)",
            "context": rag_context,
            "question": question,
        }
    )

    sources = [
        SourceDocument(
            document_id=doc.metadata.get("document_id", ""),
            document_name=doc.metadata.get("source", "unknown"),
            content=doc.page_content[:300],
            relevance_score=round(score, 4),
        )
        for doc, score in zip(docs, scores, strict=True)
    ]

    # Persist messages
    await add_message(conversation_id, "user", question)
    await add_message(conversation_id, "assistant", answer)

    return answer, sources, conversation_id


def _build_rag_context(docs: list, max_chars: int) -> str:
    """Build RAG context, trimming doc contents to fit max_chars."""
    parts: list[str] = []
    budget = max_chars
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "unknown")
        prefix = f"[Source {i + 1}: {source}]\n"
        remaining = budget - len(prefix) - 4  # 4 for "\n\n---\n\n"
        if remaining <= 0:
            break
        content = doc.page_content[:remaining]
        parts.append(prefix + content)
        budget -= len(prefix) + len(content) + 4
    return "\n\n---\n\n".join(parts) if parts else format_docs(docs)


def _truncate_history(history: str, max_chars: int) -> str:
    """Truncate history from the beginning to fit max_chars."""
    if len(history) <= max_chars:
        return history
    truncated = history[-max_chars:]
    first_newline = truncated.find("\n")
    if first_newline > 0:
        truncated = truncated[first_newline + 1 :]
    logger.info("History truncated from %d to %d chars", len(history), len(truncated))
    return truncated
