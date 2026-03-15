"""Utilitários gerais e carregamento de configurações."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM principal: Ollama (preferência OSS local)
    use_ollama: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # LLM fallback: OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Embeddings HuggingFace OSS
    embedding_model: str = "BAAI/bge-m3"

    # VectorStore
    chroma_persist_dir: str = "./data/processed/chroma"

    # MCP
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_log_level: str = "INFO"

    # Self-check
    self_check_threshold: float = 0.7

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instância singleton de Settings."""
    return Settings()


def get_llm(temperature: float = 0):
    """
    Retorna o LLM configurado: Ollama (preferência) ou OpenAI (fallback).
    Usa USE_OLLAMA=true/.env para escolher.
    """
    settings = get_settings()
    if settings.use_ollama:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
        )
