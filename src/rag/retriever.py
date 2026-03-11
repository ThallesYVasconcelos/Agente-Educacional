"""Retriever para o pipeline RAG de Educação Básica."""

from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from src.rag.vectorstore import get_vectorstore
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EducacaoRetriever(BaseRetriever):
    """Retriever com over-fetch para melhor cobertura semântica."""

    top_k: int = 5
    fetch_k: int = 20

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        vs = get_vectorstore()
        docs = vs.similarity_search(query, k=self.fetch_k)
        logger.info(
            "retriever_search",
            fetched=len(docs),
            returning=min(self.top_k, len(docs)),
        )
        return docs[: self.top_k]


def get_retriever(top_k: int = 5) -> EducacaoRetriever:
    """Factory para criar o retriever de educação."""
    return EducacaoRetriever(top_k=top_k)
