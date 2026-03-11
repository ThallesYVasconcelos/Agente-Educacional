"""
EduRAG — Agente principal de Educação Básica.

Fachada sobre o grafo LangGraph.
Corpus de referência:
  - BNCC (Base Nacional Comum Curricular, 2017/2018)
  - PCN (Parâmetros Curriculares Nacionais, 1997–2000)
  - Guias PNLD (Programa Nacional do Livro Didático)
  - Diretrizes Curriculares Nacionais para a Educação Básica
"""

from src.agents.graph import get_graph
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EducacaoAgent:
    """Agente RAG para professores da Educação Básica brasileira."""

    def __init__(self):
        self._graph = get_graph()

    def ask(self, question: str) -> dict:
        """
        Processa uma pergunta sobre Educação Básica.

        Returns:
            dict com:
              - answer        : resposta com citações
              - sources       : lista de trechos e metadados recuperados
              - self_check_score : fidelidade validada (0.0–1.0)
              - route         : rota usada pelo supervisor
        """
        logger.info("educacao_agent_ask", question_preview=question[:60])

        initial_state = {
            "question": question,
            "route": "",
            "context": [],
            "answer": "",
            "self_check_score": 0.0,
            "retrieval_attempts": 0,
            "sources": [],
            "safety_note": "",
        }

        final_state = self._graph.invoke(initial_state)

        return {
            "answer": final_state["answer"],
            "sources": final_state.get("sources", []),
            "self_check_score": final_state.get("self_check_score", 0.0),
            "route": final_state.get("route", "qa"),
        }
