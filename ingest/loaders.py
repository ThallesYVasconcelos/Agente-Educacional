"""
Carregadores de documentos — corpus de Educação Básica.

Fontes suportadas:
  - PDF  : BNCC, PCN, guias PNLD, diretrizes MEC (data/raw/educacao/*.pdf)
  - TXT  : transcrições, ementas, documentos digitalizados (data/raw/educacao/*.txt)

Todos os documentos são de domínio público (MEC/gov.br).
Links para download estão no README.
"""

from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from src.utils.logger import get_logger

logger = get_logger(__name__)

RAW_PATH = Path("data/raw/educacao")


def load_corpus() -> List[Document]:
    """
    Carrega todos os documentos PDF e TXT do corpus de Educação Básica.
    Adiciona metadados: source, source_file, domain.
    """
    if not RAW_PATH.exists():
        logger.warning("corpus_path_missing", path=str(RAW_PATH))
        return []

    docs: List[Document] = []

    for pdf_file in sorted(RAW_PATH.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf_file))
        loaded = loader.load()
        for doc in loaded:
            doc.metadata["source"] = pdf_file.stem
            doc.metadata["source_file"] = pdf_file.name
            doc.metadata["domain"] = "educacao"
        docs.extend(loaded)
        logger.info("pdf_loaded", file=pdf_file.name, pages=len(loaded))

    for txt_file in sorted(RAW_PATH.glob("*.txt")):
        loader = TextLoader(str(txt_file), encoding="utf-8")
        loaded = loader.load()
        for doc in loaded:
            doc.metadata["source"] = txt_file.stem
            doc.metadata["source_file"] = txt_file.name
            doc.metadata["domain"] = "educacao"
        docs.extend(loaded)
        logger.info("txt_loaded", file=txt_file.name, docs=len(loaded))

    logger.info("corpus_loaded", total_docs=len(docs))
    return docs
