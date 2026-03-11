"""
Tools expostas via MCP — EduRAG (Educação Básica).

Tools disponíveis:
  - search_docs         : busca semântica na BNCC/PCN/PNLD
  - generate_lesson_plan: gera plano de aula com citações (A1)
  - check_bncc_skills   : verifica alinhamento com habilidades BNCC (A2)
  - list_sources        : lista documentos ingeridos
  - get_info            : retorna metadados do corpus disponível

Controles de segurança:
  - allowlist de tools (nenhuma ferramenta fora da lista é executada)
  - validação de tamanho de input
  - audit log via structlog (ver server.py)
  - sem acesso a filesystem fora de data/raw/educacao/
"""

import hashlib
from typing import List, Optional

from src.rag.vectorstore import similarity_search
from src.automations.lesson_plan import generate_lesson_plan
from src.automations.bncc_checker import check_bncc_alignment
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_QUERY_LEN = 2000
MAX_DESC_LEN = 3000
MAX_TOP_K = 20

ALLOWED_TOOLS = {
    "search_docs",
    "generate_lesson_plan",
    "check_bncc_skills",
    "list_sources",
    "get_info",
}


def tool_search_docs(query: str, top_k: int = 5) -> List[dict]:
    """Busca semântica nos documentos pedagógicos ingeridos."""
    if len(query) > MAX_QUERY_LEN:
        raise ValueError(f"Query excede {MAX_QUERY_LEN} caracteres.")
    top_k = min(top_k, MAX_TOP_K)
    logger.info("mcp_search_docs", query_hash=hashlib.md5(query.encode()).hexdigest()[:8])
    docs = similarity_search(query, k=top_k)
    return [{"content": d.page_content, "metadata": d.metadata} for d in docs]


def tool_generate_lesson_plan(
    componente_curricular: str,
    habilidade_bncc: str,
    ano_escolar: str,
    duracao_aulas: int = 1,
) -> dict:
    """Gera plano de aula estruturado com citações da BNCC e PCN."""
    if len(componente_curricular) > 100 or len(habilidade_bncc) > 500:
        raise ValueError("Parâmetros excedem tamanho máximo permitido.")
    duracao_aulas = max(1, min(duracao_aulas, 5))
    logger.info(
        "mcp_lesson_plan",
        componente=componente_curricular,
        habilidade_preview=habilidade_bncc[:40],
    )
    return generate_lesson_plan(componente_curricular, habilidade_bncc, ano_escolar, duracao_aulas)


def tool_check_bncc_skills(
    descricao_atividade: str,
    componente: str,
    ano_escolar: str,
) -> dict:
    """Verifica quais habilidades da BNCC uma atividade desenvolve."""
    if len(descricao_atividade) > MAX_DESC_LEN:
        raise ValueError(f"Descrição excede {MAX_DESC_LEN} caracteres.")
    logger.info(
        "mcp_bncc_check",
        desc_hash=hashlib.md5(descricao_atividade.encode()).hexdigest()[:8],
    )
    return check_bncc_alignment(descricao_atividade, componente, ano_escolar)


def tool_list_sources() -> List[str]:
    """Lista os documentos ingeridos no corpus de educação."""
    from pathlib import Path
    raw_path = Path("data/raw/educacao")
    if not raw_path.exists():
        return []
    return [f.name for f in sorted(raw_path.iterdir()) if f.is_file()]


def tool_get_info() -> dict:
    """Retorna metadados sobre o corpus e as capacidades do agente."""
    return {
        "sistema": "EduRAG — Assistente para Professores da Educação Básica",
        "corpus": [
            "BNCC — Base Nacional Comum Curricular (2017/2018)",
            "PCN — Parâmetros Curriculares Nacionais (1997–2000)",
            "Guias PNLD (Programa Nacional do Livro Didático)",
            "Diretrizes Curriculares Nacionais para a Educação Básica",
        ],
        "tools_disponiveis": sorted(ALLOWED_TOOLS),
        "llm": "Ollama (local OSS) ou OpenAI (fallback)",
        "embeddings": "BAAI/bge-m3 (HuggingFace, local)",
        "aviso": (
            "As respostas têm caráter pedagógico e informativo. "
            "Para decisões curriculares definitivas, consulte as equipes pedagógicas "
            "e a versão oficial da BNCC em https://basenacionalcomum.mec.gov.br/."
        ),
    }
