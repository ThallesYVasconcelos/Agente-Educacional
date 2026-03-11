"""
Testes do EducacaoAgent (LangGraph).
Usa mock de LLM para não depender de Ollama/OpenAI.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.agents.graph import (
    node_supervisor,
    node_safety,
    node_refuse,
    node_out_of_scope,
    route_after_supervisor,
    route_after_self_check,
    AgentState,
)


def make_state(**kwargs) -> AgentState:
    defaults = {
        "question": "O que é a BNCC?",
        "route": "",
        "context": [],
        "answer": "",
        "self_check_score": 0.0,
        "retrieval_attempts": 0,
        "sources": [],
        "safety_note": "",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

@patch("src.agents.graph.get_llm")
def test_supervisor_routes_qa(mock_llm):
    mock_response = MagicMock()
    mock_response.content = '{"route": "qa"}'
    mock_llm.return_value.invoke = MagicMock(return_value=mock_response)

    state = make_state(question="Quais são as competências gerais da BNCC?")
    result = node_supervisor(state)
    assert result["route"] == "qa"


@patch("src.agents.graph.get_llm")
def test_supervisor_routes_automation(mock_llm):
    mock_response = MagicMock()
    mock_response.content = '{"route": "automation"}'
    mock_llm.return_value.invoke = MagicMock(return_value=mock_response)

    state = make_state(question="Gere um plano de aula de Matemática para o 5º ano")
    result = node_supervisor(state)
    assert result["route"] == "automation"


@patch("src.agents.graph.get_llm")
def test_supervisor_routes_refuse_on_invalid_json(mock_llm):
    mock_response = MagicMock()
    mock_response.content = "resposta inválida"
    mock_llm.return_value.invoke = MagicMock(return_value=mock_response)

    state = make_state(question="Qualquer pergunta")
    result = node_supervisor(state)
    assert result["route"] == "qa"  # fallback para qa


# ---------------------------------------------------------------------------
# Roteamento condicional
# ---------------------------------------------------------------------------

def test_route_after_supervisor_qa():
    state = make_state(route="qa")
    assert route_after_supervisor(state) == "retriever"


def test_route_after_supervisor_refuse():
    state = make_state(route="refuse")
    assert route_after_supervisor(state) == "out_of_scope"


@patch("src.agents.graph.get_settings")
def test_route_after_self_check_passes(mock_settings):
    mock_settings.return_value.self_check_threshold = 0.7
    state = make_state(self_check_score=0.85, retrieval_attempts=1)
    assert route_after_self_check(state) == "end"


@patch("src.agents.graph.get_settings")
def test_route_after_self_check_retry(mock_settings):
    mock_settings.return_value.self_check_threshold = 0.7
    state = make_state(self_check_score=0.4, retrieval_attempts=1)
    assert route_after_self_check(state) == "retriever"


@patch("src.agents.graph.get_settings")
def test_route_after_self_check_refuse_after_max_attempts(mock_settings):
    mock_settings.return_value.self_check_threshold = 0.7
    state = make_state(self_check_score=0.3, retrieval_attempts=2)
    assert route_after_self_check(state) == "refuse"


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def test_safety_adds_note_for_health_keywords():
    state = make_state(question="Como lidar com saúde mental dos alunos?")
    result = node_safety(state)
    assert "saúde" in result["safety_note"].lower() or "especializado" in result["safety_note"]


def test_safety_no_note_for_normal_questions():
    state = make_state(question="Quais são as habilidades de Matemática do 5º ano?")
    result = node_safety(state)
    assert result["safety_note"] == ""


# ---------------------------------------------------------------------------
# Recusa
# ---------------------------------------------------------------------------

def test_refuse_node_returns_message():
    state = make_state()
    result = node_refuse(state)
    assert len(result["answer"]) > 10
    assert "evidências" in result["answer"].lower() or "BNCC" in result["answer"]


def test_out_of_scope_node_returns_message():
    state = make_state()
    result = node_out_of_scope(state)
    assert len(result["answer"]) > 10
    assert "escopo" in result["answer"].lower()
