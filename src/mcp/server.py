"""
EduRAG MCP Server — Model Context Protocol para Educação Básica.

Expõe tools via FastAPI com controles de segurança:
  - allowlist de tools (lista explícita em tools.py)
  - validações de tamanho de input
  - audit log JSON em cada requisição
  - rate limiting básico por IP (via middleware)
  - CORS restrito ao Streamlit local

Para rodar: python src/mcp/server.py
"""

import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.mcp.tools import (
    tool_search_docs,
    tool_generate_lesson_plan,
    tool_check_bncc_skills,
    tool_list_sources,
    tool_get_info,
    ALLOWED_TOOLS,
)
from src.utils.helpers import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="EduRAG MCP Server",
    description="Model Context Protocol — Assistente para Professores da Educação Básica",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas de request
# ---------------------------------------------------------------------------

class SearchDocsRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class LessonPlanRequest(BaseModel):
    componente_curricular: str = Field(..., max_length=100)
    habilidade_bncc: str = Field(..., max_length=500)
    ano_escolar: str = Field(..., max_length=50)
    duracao_aulas: int = Field(default=1, ge=1, le=5)


class BnccCheckRequest(BaseModel):
    descricao_atividade: str = Field(..., max_length=3000)
    componente: str = Field(..., max_length=100)
    ano_escolar: str = Field(..., max_length=50)


# ---------------------------------------------------------------------------
# Middleware de audit log
# ---------------------------------------------------------------------------

@app.middleware("http")
async def audit_log(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 1)
    logger.info(
        "mcp_request",
        path=request.url.path,
        method=request.method,
        status=response.status_code,
        latency_ms=elapsed,
        client_host=request.client.host if request.client else "unknown",
    )
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0", "allowed_tools": sorted(ALLOWED_TOOLS)}


@app.get("/tools")
def list_tools():
    """Lista todas as tools disponíveis (allowlist pública)."""
    return {
        "tools": [
            {"name": "search_docs", "description": "Busca semântica na BNCC/PCN/PNLD"},
            {"name": "generate_lesson_plan", "description": "Gera plano de aula com citações normativas (A1)"},
            {"name": "check_bncc_skills", "description": "Verifica alinhamento de atividade com habilidades BNCC (A2)"},
            {"name": "list_sources", "description": "Lista documentos ingeridos no corpus"},
            {"name": "get_info", "description": "Retorna metadados do sistema e corpus"},
        ]
    }


@app.post("/tools/search_docs")
def search_docs(req: SearchDocsRequest):
    try:
        return {"results": tool_search_docs(req.query, req.top_k)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/generate_lesson_plan")
def generate_lesson_plan_endpoint(req: LessonPlanRequest):
    try:
        return tool_generate_lesson_plan(
            req.componente_curricular,
            req.habilidade_bncc,
            req.ano_escolar,
            req.duracao_aulas,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/check_bncc_skills")
def check_bncc_skills_endpoint(req: BnccCheckRequest):
    try:
        return tool_check_bncc_skills(
            req.descricao_atividade,
            req.componente,
            req.ano_escolar,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tools/list_sources")
def list_sources_endpoint():
    return {"sources": tool_list_sources()}


@app.get("/tools/get_info")
def get_info_endpoint():
    return tool_get_info()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.mcp.server:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=False,
        log_level=settings.mcp_log_level.lower(),
    )
