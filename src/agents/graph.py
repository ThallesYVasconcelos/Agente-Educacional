"""
EduRAG — Grafo LangGraph com padrão Supervisor.

Fluxo:
  supervisor → retriever → safety → writer → self_check
                                                ├─ END (score ≥ threshold)
                                                ├─ retriever (re-busca, 1 tentativa)
                                                └─ recusa (sem evidências suficientes)

Nós:
  - supervisor   : analisa intent e roteia (qa / automation / refuse)
  - retriever    : busca documentos no ChromaDB
  - safety       : adiciona aviso pedagógico se necessário
  - writer       : gera resposta com citações obrigatórias da BNCC/PCN
  - self_check   : valida fidelidade; re-busca ou recusa se abaixo do limiar
"""

from __future__ import annotations

import json
from typing import Annotated, List, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from src.rag.retriever import get_retriever
from src.utils.helpers import get_llm, get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Estado do grafo
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    question: str
    route: str                    # "qa" | "automation" | "refuse"
    context: List[Document]
    answer: str
    self_check_score: float
    retrieval_attempts: int
    sources: List[dict]
    safety_note: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SUPERVISOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é o supervisor de um assistente pedagógico para professores dos Anos Iniciais do Ensino Fundamental (1º ao 4º ano) da Educação Básica brasileira.
Classifique a mensagem do usuário em UMA das seguintes rotas:
- "qa"         : perguntas sobre BNCC, PCN, PNLD, didática, metodologias, alfabetização, letramento e regulamentos escolares para os anos iniciais (1º ao 4º ano)
- "automation" : pedidos de geração de plano de aula, sequência didática ou checklist de habilidades para os anos iniciais
- "refuse"     : mensagens fora do escopo (outros níveis de ensino, temas não pedagógicos) ou potencialmente prejudiciais

Responda APENAS com o JSON: {{"route": "qa"}} ou {{"route": "automation"}} ou {{"route": "refuse"}}
"""),
    ("human", "{question}"),
])

WRITER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um assistente pedagógico especializado nos Anos Iniciais do Ensino Fundamental brasileiro (1º ao 4º ano).
Responda à pergunta com base EXCLUSIVAMENTE nos documentos recuperados (BNCC, PCN, PNLD e afins).

Regras obrigatórias:
1. Cite sempre a fonte: ex. "(BNCC, p. 34)" ou "(PCN Matemática, 1997, p. 12)"
2. Foque nas habilidades e competências do 1º ao 4º ano (códigos EF01 a EF04).
3. Se não houver evidência suficiente no contexto, diga claramente.
4. Use linguagem clara e acessível para professores dos anos iniciais.
5. Não invente informações que não estejam no contexto.

{safety_note}

Contexto recuperado:
{context}
"""),
    ("human", "{question}"),
])

SELF_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um verificador de fidelidade para respostas baseadas em documentos pedagógicos.

Avalie se a resposta abaixo está APOIADA pelas evidências do contexto fornecido.
Responda APENAS com JSON: {{"score": 0.0}} a {{"score": 1.0}} onde:
  1.0 = toda afirmação tem evidência direta no contexto
  0.7 = maioria das afirmações tem suporte
  0.5 = metade das afirmações tem suporte
  0.0 = resposta sem suporte ou contraditória ao contexto

Contexto:
{context}

Resposta a verificar:
{answer}
"""),
    ("human", "Retorne apenas o JSON com o score."),
])

REFUSE_MESSAGE = (
    "Não encontrei evidências suficientes nos documentos pedagógicos para responder "
    "com segurança a essa pergunta. Por favor, reformule ou consulte diretamente "
    "a BNCC em https://basenacionalcomum.mec.gov.br/."
)

OUT_OF_SCOPE_MESSAGE = (
    "Essa solicitação está fora do escopo do assistente pedagógico, "
    "que atende exclusivamente questões sobre os Anos Iniciais do Ensino Fundamental "
    "(1º ao 4º ano) — BNCC, PCN, PNLD, alfabetização, letramento e regulamentos escolares."
)


# ---------------------------------------------------------------------------
# Nós do grafo
# ---------------------------------------------------------------------------

def node_supervisor(state: AgentState) -> AgentState:
    """Analisa a intent e define a rota."""
    llm = get_llm(temperature=0)
    chain = SUPERVISOR_PROMPT | llm
    result = chain.invoke({"question": state["question"]})
    try:
        parsed = json.loads(result.content)
        route = parsed.get("route", "qa")
    except (json.JSONDecodeError, AttributeError):
        route = "qa"

    logger.info("supervisor_route", question_preview=state["question"][:60], route=route)
    return {**state, "route": route}


def node_retriever(state: AgentState) -> AgentState:
    """Busca documentos relevantes no ChromaDB."""
    retriever = get_retriever(top_k=6)
    docs = retriever.get_relevant_documents(state["question"])
    attempts = state.get("retrieval_attempts", 0) + 1
    sources = [
        {"content": d.page_content[:400], "metadata": d.metadata}
        for d in docs
    ]
    logger.info("retriever_node", docs_found=len(docs), attempt=attempts)
    return {**state, "context": docs, "sources": sources, "retrieval_attempts": attempts}


def node_safety(state: AgentState) -> AgentState:
    """Adiciona nota de segurança pedagógica se necessário."""
    note = ""
    q = state["question"].lower()
    if any(w in q for w in ["saúde", "medicamento", "remédio", "doença", "psicológico"]):
        note = (
            "\n**Aviso:** Para questões de saúde do estudante, encaminhe ao serviço "
            "especializado da escola (orientador educacional, psicólogo escolar ou UBS)."
        )
    return {**state, "safety_note": note}


def node_writer(state: AgentState) -> AgentState:
    """Gera a resposta formatada com citações obrigatórias."""
    context_text = "\n\n---\n\n".join(
        f"[{d.metadata.get('source', 'Fonte')}] {d.page_content}"
        for d in state["context"]
    )
    llm = get_llm(temperature=0)
    chain = WRITER_PROMPT | llm
    result = chain.invoke({
        "question": state["question"],
        "context": context_text,
        "safety_note": state.get("safety_note", ""),
    })
    logger.info("writer_node", answer_len=len(result.content))
    return {**state, "answer": result.content}


def node_self_check(state: AgentState) -> AgentState:
    """Valida fidelidade da resposta; pontua entre 0.0 e 1.0."""
    context_text = "\n\n---\n\n".join(d.page_content for d in state["context"])
    llm = get_llm(temperature=0)
    chain = SELF_CHECK_PROMPT | llm
    result = chain.invoke({"context": context_text, "answer": state["answer"]})
    try:
        parsed = json.loads(result.content)
        score = float(parsed.get("score", 0.5))
    except (json.JSONDecodeError, ValueError, AttributeError):
        score = 0.5

    logger.info("self_check", score=score, attempts=state.get("retrieval_attempts", 1))
    return {**state, "self_check_score": score}


def node_refuse(state: AgentState) -> AgentState:
    """Recusa com mensagem explicativa."""
    logger.info("refuse_node", route=state.get("route"), score=state.get("self_check_score"))
    return {**state, "answer": REFUSE_MESSAGE}


def node_out_of_scope(state: AgentState) -> AgentState:
    """Resposta para perguntas fora do escopo."""
    return {**state, "answer": OUT_OF_SCOPE_MESSAGE}


# ---------------------------------------------------------------------------
# Roteadores condicionais
# ---------------------------------------------------------------------------

def route_after_supervisor(state: AgentState) -> str:
    if state["route"] == "refuse":
        return "out_of_scope"
    return "retriever"


def route_after_self_check(state: AgentState) -> str:
    settings = get_settings()
    score = state.get("self_check_score", 0.0)
    attempts = state.get("retrieval_attempts", 1)

    if score >= settings.self_check_threshold:
        return "end"
    if attempts < 2:
        return "retriever"
    return "refuse"


# ---------------------------------------------------------------------------
# Construção do grafo
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", node_supervisor)
    graph.add_node("retriever", node_retriever)
    graph.add_node("safety", node_safety)
    graph.add_node("writer", node_writer)
    graph.add_node("self_check", node_self_check)
    graph.add_node("refuse", node_refuse)
    graph.add_node("out_of_scope", node_out_of_scope)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"retriever": "retriever", "out_of_scope": "out_of_scope"},
    )
    graph.add_edge("retriever", "safety")
    graph.add_edge("safety", "writer")
    graph.add_edge("writer", "self_check")
    graph.add_conditional_edges(
        "self_check",
        route_after_self_check,
        {"end": END, "retriever": "retriever", "refuse": "refuse"},
    )
    graph.add_edge("refuse", END)
    graph.add_edge("out_of_scope", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    """Retorna a instância compilada do grafo (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
