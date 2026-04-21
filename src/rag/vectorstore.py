"""
Gerenciamento do VectorStore ChromaDB — domínio Educação Básica.

Modos disponíveis (CHROMA_MODE):
  - "local"  (padrão): persiste em disco em CHROMA_PERSIST_DIR
  - "cloud"           : conecta ao ChromaDB Cloud (requer CHROMA_API_KEY,
                        CHROMA_TENANT e CHROMA_DATABASE)
    Crie sua conta gratuita em https://trychroma.com
    Free tier: até 1 milhão de vetores, sem cartão de crédito
"""

from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.rag.embeddings import get_embeddings
from src.utils.helpers import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "edurag_educacao"
DOMAIN = "educacao"


def _get_chroma_client():
    """Retorna o cliente ChromaDB conforme CHROMA_MODE."""
    settings = get_settings()

    if settings.chroma_mode == "cloud":
        import chromadb
        return chromadb.CloudClient(
            tenant=settings.chroma_tenant,
            database=settings.chroma_database,
            api_key=settings.chroma_api_key,
        )
    return None


def get_vectorstore() -> Chroma:
    """Retorna o vectorstore ChromaDB para Educação Básica."""
    settings = get_settings()

    if settings.chroma_mode == "cloud":
        client = _get_chroma_client()
        return Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
        )

    persist_dir = str(Path(settings.chroma_persist_dir) / DOMAIN)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )


def add_documents(documents: List[Document], batch_size: int = 500) -> None:
    """Adiciona documentos ao vectorstore em lotes para respeitar o limite do ChromaDB Cloud."""
    vs = get_vectorstore()
    total = len(documents)
    for start in range(0, total, batch_size):
        batch = documents[start: start + batch_size]
        vs.add_documents(batch)
        end = min(start + batch_size, total)
        print(f"  Indexados {end}/{total} chunks...")
    logger.info("documents_added", domain=DOMAIN, count=total)


def similarity_search(query: str, k: int = 5) -> List[Document]:
    """Busca semântica no vectorstore."""
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=k)
    logger.info("similarity_search", query_len=len(query), results=len(results))
    return results
