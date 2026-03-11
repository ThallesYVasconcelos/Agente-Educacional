"""Gerenciamento do VectorStore ChromaDB — domínio Educação Básica."""

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


def get_vectorstore() -> Chroma:
    """Retorna o vectorstore ChromaDB para Educação Básica."""
    settings = get_settings()
    persist_dir = str(Path(settings.chroma_persist_dir) / DOMAIN)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )


def add_documents(documents: List[Document]) -> None:
    """Adiciona documentos ao vectorstore."""
    vs = get_vectorstore()
    vs.add_documents(documents)
    logger.info("documents_added", domain=DOMAIN, count=len(documents))


def similarity_search(query: str, k: int = 5) -> List[Document]:
    """Busca semântica no vectorstore."""
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=k)
    logger.info("similarity_search", query_len=len(query), results=len(results))
    return results
