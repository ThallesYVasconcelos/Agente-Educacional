"""Utilitários gerais e carregamento de configurações."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Provedor do LLM: "ollama" | "replicate" | "openai"
    llm_provider: str = "ollama"

    # LLM: Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # LLM: Replicate
    replicate_api_token: str = ""
    # Modelos disponíveis no Replicate:
    #   "meta/meta-llama-3-8b-instruct"   → rápido, barato (~$0.05/1M tokens)
    #   "meta/meta-llama-3-70b-instruct"  → mais preciso
    #   "openai/gpt-4o-mini"              → disponível no Replicate, boa qualidade
    replicate_model: str = "openai/gpt-4o-mini"

    # LLM: OpenAI (fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Embeddings: "huggingface" | "openai"
    embedding_provider: str = "huggingface"
    # bge-small-en-v1.5 é muito mais leve que bge-m3 (~130MB vs ~2GB)
    # Para deploy no Streamlit Cloud, prefira bge-small
    embedding_model: str = "BAAI/bge-m3"

    # VectorStore: "local" | "cloud"
    chroma_mode: str = "local"
    chroma_persist_dir: str = "./data/processed/chroma"

    # ChromaDB Cloud (quando chroma_mode=cloud)
    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = "edurag"

    # MCP
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_log_level: str = "INFO"

    # Self-check
    self_check_threshold: float = 0.7

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Manter compatibilidade com variável legada USE_OLLAMA
    use_ollama: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instância singleton de Settings."""
    return Settings()


def get_llm(temperature: float = 0):
    """
    Retorna o LLM configurado pelo LLM_PROVIDER:
      - "replicate" → Replicate (Llama 3 na nuvem, usa REPLICATE_API_TOKEN)
      - "openai"    → OpenAI ChatGPT (usa OPENAI_API_KEY)
      - "ollama"    → Ollama local (padrão para desenvolvimento)
    A variável legada USE_OLLAMA=false redireciona para "openai" se llm_provider
    não foi explicitamente alterado.
    """
    settings = get_settings()

    provider = settings.llm_provider
    # Compatibilidade retroativa: USE_OLLAMA=false sem LLM_PROVIDER definido
    if provider == "ollama" and not settings.use_ollama:
        provider = "openai"

    if provider == "replicate":
        import os
        from langchain_community.llms import Replicate
        os.environ.setdefault("REPLICATE_API_TOKEN", settings.replicate_api_token)
        return Replicate(
            model=settings.replicate_model,
            model_kwargs={"temperature": max(temperature, 0.01), "max_new_tokens": 1024},
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
        )

    # padrão: ollama
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )
