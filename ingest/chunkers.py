"""
Estratégia de chunking para o corpus de Educação Básica.

Configuração otimizada para documentos pedagógicos:
  - chunk_size 800: preserva contexto de habilidades BNCC (cada habilidade ~200-400 chars)
  - chunk_overlap 120: garante continuidade entre habilidades adjacentes
  - separadores especiais: "EF", "EM", "CO" (prefixos de códigos BNCC) e "Art." (normas)
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.utils.logger import get_logger

logger = get_logger(__name__)

CHUNK_CONFIG = {
    "chunk_size": 800,
    "chunk_overlap": 120,
    "separators": ["\n\n", "\n", "(EF", "(EM", "(CO", "Art.", ". ", " "],
}


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Divide documentos em chunks para indexação no ChromaDB.
    Preserva metadados originais e adiciona chunk_id.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_CONFIG["chunk_size"],
        chunk_overlap=CHUNK_CONFIG["chunk_overlap"],
        separators=CHUNK_CONFIG["separators"],
        add_start_index=True,
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    logger.info(
        "chunks_created",
        input_docs=len(documents),
        output_chunks=len(chunks),
        avg_chunk_size=sum(len(c.page_content) for c in chunks) // max(len(chunks), 1),
    )
    return chunks
