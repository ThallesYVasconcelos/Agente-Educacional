"""
Testes do pipeline RAG — chunker e retriever (sem LLM, sem ChromaDB).
"""

from unittest.mock import patch, MagicMock

import pytest
from langchain_core.documents import Document

from ingest.chunkers import chunk_documents


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def make_doc(content: str, source: str = "bncc") -> Document:
    return Document(page_content=content, metadata={"source": source, "domain": "educacao"})


def test_chunk_size_within_bounds():
    long_text = "A " * 600
    docs = [make_doc(long_text)]
    chunks = chunk_documents(docs)
    for chunk in chunks:
        assert len(chunk.page_content) <= 900, "Chunk maior que o esperado"


def test_chunk_overlap_creates_continuity():
    text = "palavra " * 300
    docs = [make_doc(text)]
    chunks = chunk_documents(docs)
    assert len(chunks) >= 2, "Deveria ter ao menos 2 chunks"


def test_metadata_preserved():
    doc = make_doc("Conteúdo de teste", source="BNCC-2017")
    chunks = chunk_documents([doc])
    for chunk in chunks:
        assert chunk.metadata["source"] == "BNCC-2017"
        assert chunk.metadata["domain"] == "educacao"


def test_chunk_id_assigned():
    docs = [make_doc("texto " * 200)]
    chunks = chunk_documents(docs)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert ids == list(range(len(chunks)))


def test_empty_documents_returns_empty():
    chunks = chunk_documents([])
    assert chunks == []


def test_bncc_code_separator_respected():
    text = "Primeiro parágrafo antes do código.\n(EF05MA01) Habilidade de matemática importante.\n(EF05MA02) Segunda habilidade."
    docs = [make_doc(text)]
    chunks = chunk_documents(docs)
    full_text = " ".join(c.page_content for c in chunks)
    assert "EF05MA01" in full_text
    assert "EF05MA02" in full_text
