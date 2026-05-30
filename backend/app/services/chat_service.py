"""Chat service: RAG Q&A with streaming support."""

from __future__ import annotations

from app.core.rag_chain import format_docs, qa_chain
from app.core.vector_store import search_hybrid, search_similar
from app.models.chat import SourceDocument


async def generate_answer(
    question: str,
    top_k: int = 5,
    use_hybrid: bool = True,
) -> tuple[str, list[SourceDocument]]:
    """Generate an answer using RAG.

    Returns (answer_text, list_of_sources).
    """
    if use_hybrid:
        results = search_hybrid(question, top_k=top_k)
    else:
        results = search_similar(question, top_k=top_k)

    if not results:
        return (
            "I couldn't find any relevant information in your learning materials "
            "to answer this question. Try uploading some course notes or papers first.",
            [],
        )

    docs = [doc for doc, _ in results]
    scores = [score for _, score in results]
    context = format_docs(docs)

    answer = await qa_chain.ainvoke({"context": context, "question": question})

    sources = [
        SourceDocument(
            document_id=doc.metadata.get("document_id", ""),
            document_name=doc.metadata.get("source", "unknown"),
            content=doc.page_content[:300],
            relevance_score=round(score, 4),
        )
        for doc, score in zip(docs, scores, strict=True)
    ]

    return answer, sources


async def answer_stream(
    question: str,
    top_k: int = 5,
    use_hybrid: bool = True,
):
    """Stream-based RAG answer generation (SSE compatible).

    Yields chunks of the answer text as they're generated.
    """
    if use_hybrid:
        results = search_hybrid(question, top_k=top_k)
    else:
        results = search_similar(question, top_k=top_k)

    if not results:
        yield "[VoiceLearn] I couldn't find relevant information in your materials."
        return

    docs = [doc for doc, _ in results]
    context = format_docs(docs)

    llm = qa_chain.steps[1] if hasattr(qa_chain, "steps") else qa_chain.middle[0]
    prompt = qa_chain.steps[0] if hasattr(qa_chain, "steps") else qa_chain.first

    prompt_value = await prompt.ainvoke({"context": context, "question": question})
    async for chunk in llm.astream(prompt_value.to_messages()):
        if hasattr(chunk, "content"):
            yield chunk.content
        else:
            yield str(chunk)
