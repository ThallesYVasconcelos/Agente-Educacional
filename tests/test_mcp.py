"""
Testes do servidor MCP (FastAPI) — sem LLM, sem ChromaDB real.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.mcp.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health e discovery
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "allowed_tools" in data


def test_list_tools_returns_all():
    resp = client.get("/tools")
    assert resp.status_code == 200
    tools = resp.json()["tools"]
    names = {t["name"] for t in tools}
    assert "search_docs" in names
    assert "generate_lesson_plan" in names
    assert "check_bncc_skills" in names
    assert "list_sources" in names
    assert "get_info" in names


def test_get_info():
    resp = client.get("/tools/get_info")
    assert resp.status_code == 200
    data = resp.json()
    assert "corpus" in data
    assert "tools_disponiveis" in data


# ---------------------------------------------------------------------------
# Validações de input
# ---------------------------------------------------------------------------

def test_search_docs_query_too_long():
    resp = client.post("/tools/search_docs", json={"query": "a" * 2001, "top_k": 5})
    assert resp.status_code == 400
    assert "2000" in resp.json()["detail"]


def test_search_docs_top_k_clamped():
    with patch("src.mcp.tools.similarity_search", return_value=[]):
        resp = client.post("/tools/search_docs", json={"query": "BNCC competências", "top_k": 100})
    assert resp.status_code == 200


def test_lesson_plan_componente_too_long():
    resp = client.post("/tools/generate_lesson_plan", json={
        "componente_curricular": "x" * 101,
        "habilidade_bncc": "EF05MA01",
        "ano_escolar": "5º ano",
    })
    assert resp.status_code == 422


def test_bncc_check_descricao_too_long():
    resp = client.post("/tools/check_bncc_skills", json={
        "descricao_atividade": "x" * 3001,
        "componente": "Matemática",
        "ano_escolar": "5º ano",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------

def test_list_sources_returns_list():
    with patch("src.mcp.tools.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        resp = client.get("/tools/list_sources")
    assert resp.status_code == 200
    assert "sources" in resp.json()
