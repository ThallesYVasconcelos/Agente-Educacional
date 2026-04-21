"""
Configuração de embeddings.

Provedores disponíveis (EMBEDDING_PROVIDER):
  - "huggingface" (padrão local):
      EMBEDDING_MODEL=BAAI/bge-m3          → multilíngue, 1024-dim, ~2 GB RAM
      EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 → leve, 384-dim, ~130 MB RAM
        ⚠ Para deploy no Streamlit Cloud (limite ~1 GB RAM), use bge-small
  - "openai":
      Usa text-embedding-3-small via API (zero RAM local, paga por uso)
      Requer OPENAI_API_KEY configurado
"""

from functools import lru_cache

from src.utils.helpers import get_settings


@lru_cache(maxsize=1)
def get_embeddings():
    """Retorna instância singleton de embeddings conforme EMBEDDING_PROVIDER."""
    settings = get_settings()

    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key,
        )

    # padrão: huggingface
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
