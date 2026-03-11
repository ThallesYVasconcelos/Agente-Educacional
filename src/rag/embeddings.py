"""
Configuração de embeddings OSS via HuggingFace.

Modelo padrão: BAAI/bge-m3
  - Suporte multilíngue (português nativo)
  - 1024 dimensões
  - Alternativa leve: BAAI/bge-small-en-v1.5

Sem custo de API — roda 100% local.
"""

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from src.utils.helpers import get_settings


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Retorna instância singleton de HuggingFaceEmbeddings (bge-m3)."""
    settings = get_settings()
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
