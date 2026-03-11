"""
EduRAG — Assistente Pedagógico (Q&A com Self-RAG).

Chat com o agente LangGraph: supervisor → retriever → safety → writer → self_check.
Exibe fontes recuperadas e pontuação de fidelidade para cada resposta.
"""

import streamlit as st

from src.agents.educacao_agent import EducacaoAgent

st.set_page_config(page_title="Assistente Pedagógico", page_icon="💬", layout="wide")

st.title("💬 Assistente Pedagógico — Anos Iniciais (1º ao 4º ano)")
st.markdown(
    "Tire dúvidas sobre **BNCC**, **PCN** e metodologias para os **Anos Iniciais do Ensino Fundamental** (1º ao 4º ano). "
    "Todas as respostas incluem **citações** dos documentos e pontuação de fidelidade (Self-RAG)."
)
st.divider()

# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

if "agent" not in st.session_state:
    with st.spinner("Carregando agente..."):
        st.session_state.agent = EducacaoAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Histórico de chat
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "meta" in msg:
            meta = msg["meta"]
            score = meta.get("self_check_score", 0)
            color = "green" if score >= 0.7 else "orange" if score >= 0.5 else "red"
            st.caption(
                f"Fidelidade: :{color}[{score:.2f}] · "
                f"Rota: `{meta.get('route', 'qa')}` · "
                f"{len(meta.get('sources', []))} trechos recuperados"
            )

# ---------------------------------------------------------------------------
# Input do usuário
# ---------------------------------------------------------------------------

    if prompt := st.chat_input("Pergunte sobre BNCC, PCN, alfabetização ou habilidades do 1º ao 4º ano..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando documentos pedagógicos..."):
            result = st.session_state.agent.ask(prompt)

        answer = result["answer"]
        score = result["self_check_score"]
        route = result["route"]
        sources = result["sources"]

        st.markdown(answer)

        color = "green" if score >= 0.7 else "orange" if score >= 0.5 else "red"
        st.caption(
            f"Fidelidade: :{color}[{score:.2f}] · "
            f"Rota: `{route}` · "
            f"{len(sources)} trechos recuperados"
        )

        if sources:
            with st.expander("Ver fontes recuperadas"):
                for i, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    source_name = meta.get("source", meta.get("source_file", "Fonte desconhecida"))
                    page = meta.get("page", "")
                    page_str = f" · p. {page + 1}" if page != "" else ""
                    st.markdown(f"**{i}. {source_name}{page_str}**")
                    st.markdown(f"> {src['content'][:300]}...")
                    st.divider()

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "meta": {"self_check_score": score, "route": route, "sources": sources},
    })

# ---------------------------------------------------------------------------
# Sidebar com exemplos
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Exemplos de perguntas")
    examples = [
        "Quais habilidades de leitura o 2º ano deve desenvolver?",
        "Como trabalhar alfabetização no 1º ano segundo a BNCC?",
        "Quais são os objetivos de Matemática para o 3º ano?",
        "O que a BNCC diz sobre letramento para os anos iniciais?",
        "Como a BNCC orienta o ensino de Ciências no 4º ano?",
        "Qual a diferença entre PCN e BNCC para o ensino de LP?",
        "Quais habilidades de escrita o 3º ano deve ter?",
        "Como trabalhar contagem e números com o 1º ano?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

    st.divider()
    if st.button("Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
