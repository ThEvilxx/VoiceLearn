"""
RAG Q&A pipeline built with LCEL.
Chain: prompt | llm | StrOutputParser
"""

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm

SYSTEM_PROMPT = """You are VoiceLearn, a patient and knowledgeable learning companion. \
Your role is to help students understand course materials and research papers through \
natural conversation.

When answering:
1. Use the provided context to give accurate, well-structured explanations.
2. If the context is insufficient, be honest and offer what you do know.
3. Break down complex concepts step by step. Use analogies when helpful.
4. Keep your tone encouraging and conversational — like a tutor sitting next to the student.
5. Answer in the same language as the student's question.
6. When citing from the context, mention which source document the information comes from.

Context from the student's learning materials:
{context}"""


def build_qa_chain():
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "{question}")]
    )
    return prompt | llm | StrOutputParser()


def format_docs(docs: list[Document]) -> str:
    parts: list[str] = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[Source {i + 1}: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


qa_chain = build_qa_chain()
