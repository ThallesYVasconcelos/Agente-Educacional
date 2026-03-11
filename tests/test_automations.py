"""
Testes das automações A1 (Plano de Aula) e A2 (Verificador BNCC).
"""

from unittest.mock import patch, MagicMock

import pytest
from langchain_core.documents import Document

from src.automations.lesson_plan import generate_lesson_plan, REQUIRED_SECTIONS
from src.automations.bncc_checker import check_bncc_alignment


def make_doc(content: str) -> Document:
    return Document(page_content=content, metadata={"source": "BNCC", "page": 10})


# ---------------------------------------------------------------------------
# A1 — Gerador de Plano de Aula
# ---------------------------------------------------------------------------

MOCK_LESSON_PLAN = """## Objetivos
Desenvolver habilidades de leitura e interpretação.

## Habilidades BNCC
(EF05LP01) Leitura com fluência e compreensão (BNCC, p. 96).

## Recursos
Livro didático PNLD, cartolina.

## Sequência de Atividades
**Abertura:** Ativação de conhecimentos prévios.
**Desenvolvimento:** Leitura e discussão do texto (PCN LP, p. 34).
**Fechamento:** Produção de resumo.

## Avaliação
Observação da participação e correção do resumo.
"""


@patch("src.automations.lesson_plan.get_llm")
@patch("src.automations.lesson_plan.similarity_search")
def test_lesson_plan_success(mock_search, mock_llm):
    mock_search.return_value = [make_doc("Habilidade BNCC EF05LP01 leitura e interpretação")] * 3
    mock_response = MagicMock()
    mock_response.content = MOCK_LESSON_PLAN
    mock_llm.return_value.__or__ = MagicMock(return_value=MagicMock(invoke=MagicMock(return_value=mock_response)))

    result = generate_lesson_plan("Língua Portuguesa", "EF05LP01", "5º ano", 1)
    assert "lesson_plan" in result
    assert result["citations_count"] >= 2


@patch("src.automations.lesson_plan.get_llm")
@patch("src.automations.lesson_plan.similarity_search")
def test_lesson_plan_all_sections(mock_search, mock_llm):
    mock_search.return_value = [make_doc("conteúdo BNCC")] * 3
    mock_response = MagicMock()
    mock_response.content = MOCK_LESSON_PLAN
    mock_llm.return_value.__or__ = MagicMock(return_value=MagicMock(invoke=MagicMock(return_value=mock_response)))

    result = generate_lesson_plan("Matemática", "EF03MA01", "3º ano", 2)
    for section in REQUIRED_SECTIONS:
        assert section in result["sections_present"] or section in result["lesson_plan"]


@patch("src.automations.lesson_plan.get_llm")
@patch("src.automations.lesson_plan.similarity_search")
def test_lesson_plan_has_elapsed_time(mock_search, mock_llm):
    mock_search.return_value = []
    mock_response = MagicMock()
    mock_response.content = "## Objetivos\n## Habilidades BNCC\n## Recursos\n## Sequência de Atividades\n## Avaliação\nBNCC p.1\nBNCC p.2"
    mock_llm.return_value.__or__ = MagicMock(return_value=MagicMock(invoke=MagicMock(return_value=mock_response)))

    result = generate_lesson_plan("Ciências", "EF04CI01", "4º ano", 1)
    assert "elapsed_seconds" in result
    assert result["elapsed_seconds"] >= 0


# ---------------------------------------------------------------------------
# A2 — Verificador de Habilidades BNCC
# ---------------------------------------------------------------------------

MOCK_BNCC_RESULT = {
    "habilidades": [
        {
            "codigo": "EF05MA07",
            "descricao": "Resolução de problemas com frações",
            "justificativa": "A atividade usa frações em contexto concreto.",
        }
    ],
    "competencias_gerais": ["2 - Pensamento científico, crítico e criativo"],
    "alinhamento": "alto",
    "observacoes": "Atividade bem alinhada com habilidades de Matemática do 5º ano.",
}


@patch("src.automations.bncc_checker.get_llm")
@patch("src.automations.bncc_checker.similarity_search")
def test_bncc_checker_returns_skills(mock_search, mock_llm):
    mock_search.return_value = [make_doc("habilidade matemática frações EF05MA07")] * 3
    mock_response = MagicMock()
    mock_response.content = str(MOCK_BNCC_RESULT).replace("'", '"')

    import json
    mock_llm.return_value.__or__ = MagicMock()
    with patch("src.automations.bncc_checker.JsonOutputParser") as mock_parser:
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value=MOCK_BNCC_RESULT)
        mock_llm.return_value.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        result = check_bncc_alignment(
            "Resolução de problemas com frações usando material concreto",
            "Matemática",
            "5º ano do Ensino Fundamental",
        )
    assert "elapsed_seconds" in result
    assert "success" in result


@patch("src.automations.bncc_checker.get_llm")
@patch("src.automations.bncc_checker.similarity_search")
def test_bncc_checker_handles_parse_error(mock_search, mock_llm):
    mock_search.return_value = []
    with patch("src.automations.bncc_checker.JsonOutputParser") as mock_parser:
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(side_effect=Exception("parse error"))
        mock_llm.return_value.__or__ = MagicMock(return_value=MagicMock(__or__=MagicMock(return_value=mock_chain)))

        result = check_bncc_alignment("atividade qualquer", "Arte", "3º ano")

    assert result["success"] is False
    assert "habilidades" in result
