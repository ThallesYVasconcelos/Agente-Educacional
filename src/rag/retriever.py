"""Retriever para o pipeline RAG de Educação Básica."""

from typing import List

from langchain_core.documents import Document

from src.rag.vectorstore import get_vectorstore
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Frases de índice/sumário que não acrescentam conteúdo real
_SKIP_PHRASES = [
    "está organizado em cinco áreas",
    "competência específica à qual cada habilidade",
    "recentes mudanças na LDB",
    "Currículos: BNCC e itinerários",
    "itinerários formativos",
    "Parecer CNE/CEB",
]


class EducacaoRetriever:
    """
    Retriever com over-fetch, deduplicação por fonte+conteúdo e filtro
    de trechos estruturais irrelevantes.
    """

    def __init__(self, top_k: int = 5, fetch_k: int = 30):
        self.top_k = top_k
        self.fetch_k = fetch_k

    def invoke(self, query: str) -> List[Document]:
        vs = get_vectorstore()
        docs = vs.similarity_search(query, k=self.fetch_k)

        # Deduplicação: mesmo conteúdo indexado em arquivos diferentes
        # (ex: ciencian e pcnem_ciencias_natureza com páginas idênticas)
        seen_content: set[str] = set()
        unique_docs: List[Document] = []
        for d in docs:
            # Usa os primeiros 200 chars do conteúdo como chave de dedup
            key = d.page_content[:200].strip()
            if key not in seen_content:
                seen_content.add(key)
                unique_docs.append(d)

        # Remove trechos estruturais/de apresentação sem valor informativo
        filtered = [
            d for d in unique_docs
            if not any(phrase in d.page_content for phrase in _SKIP_PHRASES)
        ]

        result = filtered[: self.top_k]
        logger.info(
            "retriever_search",
            fetched=len(docs),
            after_dedup=len(unique_docs),
            after_filter=len(filtered),
            returning=len(result),
        )
        return result


def get_retriever(top_k: int = 5) -> EducacaoRetriever:
    """Factory para criar o retriever de educação."""
    return EducacaoRetriever(top_k=top_k)
