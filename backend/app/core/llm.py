"""
Multi-provider LLM factory.
Returns a LangChain BaseChatModel based on settings.llm_provider.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm() -> BaseChatModel:
    """Return the default LLM for RAG Q&A."""
    provider = settings.llm_provider
    if provider == "claude":
        return ChatAnthropic(
            model=settings.claude_model,
            api_key=settings.anthropic_api_key,
            temperature=0.3,
            max_tokens=2048,
        )
    if provider == "openai":
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0.3,
            max_tokens=2048,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_for_extraction() -> BaseChatModel:
    """Return a cheaper/faster LLM for entity extraction tasks."""
    provider = settings.llm_provider
    if provider == "claude":
        return ChatAnthropic(
            model="claude-haiku-4-5",
            api_key=settings.anthropic_api_key,
            temperature=0.0,
            max_tokens=1024,
        )
    # OpenAI-compatible: use same model with lower temperature
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=0.0,
        max_tokens=1024,
    )
