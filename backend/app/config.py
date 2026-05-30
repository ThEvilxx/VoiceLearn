"""
VoiceLearn backend configuration.
All settings are loaded from .env file via pydantic-settings.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    data_dir: Path = Path(__file__).parent.parent / "data"
    chroma_dir: Path = data_dir / "chroma"
    upload_dir: Path = data_dir / "uploads"
    db_url: str = f"sqlite+aiosqlite:///{data_dir / 'metadata.db'}"

    # Embedding — local ModelScope download or HF model ID
    # ModelScope 下载路径: BAAI/bge-large-zh-v1___5
    # HuggingFace 直接下载: data/models/bge-large-zh-v1.5
    embedding_model: str = str(data_dir / "models" / "BAAI" / "bge-large-zh-v1___5")
    embedding_device: str = "cpu"

    # LLM Providers
    llm_provider: str = "openai"

    # Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_base_url: str = ""

    # Ollama
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI-compatible
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = ""

    # ASR
    whisper_model: str = "base"

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5

    # Server
    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
