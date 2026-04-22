"""Assistente Pedagógico — página de chat do professor."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.agents.educacao_agent import EducacaoAgent

st.set_page_config(page_title="Tirar Dúvidas", page_icon="💬", layout="wide")

st.title("💬 Tirar Dúvidas com os Documentos Oficiais")
st.markdown(
    "Faça perguntas sobre **habilidades da BNCC**, **objetivos do PCN**, "
    "**metodologias de ensino** ou qualquer orientação curricular. "
    "O assistente busca a resposta diretamente nos documentos do MEC e indica **de onde veio cada informação**."
)
st.divider()

# ---------------------------------------------------------------------------
# Inicialização do agente
# ---------------------------------------------------------------------------

if "agent" not in st.session_state:
    with st.spinner("Carregando os documentos pedagógicos..."):
        st.session_state.agent = EducacaoAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Histórico de conversa
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "meta" in msg:
            score = msg["meta"].get("self_check_score", 0)
            n_fontes = len(msg["meta"].get("sources", []))
            if score >= 0.7:
                st.caption(f"✅ Resposta embasada nos documentos · {n_fontes} trecho(s) consultado(s)")
            elif score >= 0.5:
                st.caption(f"⚠️ Resposta parcialmente embasada · {n_fontes} trecho(s) consultado(s)")
            else:
                st.caption(f"❗ Poucos trechos encontrados para esta pergunta · {n_fontes} trecho(s)")

# ---------------------------------------------------------------------------
# Input do professor
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Digite sua pergunta sobre currículo, habilidades ou metodologias..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando os documentos do MEC..."):
            result = st.session_state.agent.ask(prompt)

        answer = result["answer"]
        score = result["self_check_score"]
        sources = result["sources"]

        st.markdown(answer)

        if score >= 0.7:
            st.caption(f"✅ Resposta embasada nos documentos · {len(sources)} trecho(s) consultado(s)")
        elif score >= 0.5:
            st.caption(f"⚠️ Resposta parcialmente embasada · {len(sources)} trecho(s) consultado(s)")
        else:
            st.caption(f"❗ Poucos trechos encontrados para esta pergunta · {len(sources)} trecho(s)")

        if sources:
            with st.expander("Ver trechos consultados dos documentos"):
                for i, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    doc_nome = meta.get("source", meta.get("source_file", "Documento"))
                    pagina = meta.get("page", "")
                    pagina_str = f" — página {pagina + 1}" if pagina != "" else ""
                    st.markdown(f"**{i}. {doc_nome}{pagina_str}**")
                    st.markdown(f"> {src['content'][:300]}...")
                    st.divider()

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "meta": {"self_check_score": score, "sources": sources},
    })

# ---------------------------------------------------------------------------
# Barra lateral com sugestões
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Sugestões de perguntas")
    exemplos = [
        "Quais habilidades de leitura o 2º ano deve desenvolver?",
        "Como trabalhar alfabetização no 1º ano segundo a BNCC?",
        "Quais são os objetivos de Matemática para o 3º ano?",
        "O que a BNCC orienta para o ensino de Ciências no 4º ano?",
        "Quais habilidades de escrita o 3º ano deve ter?",
        "Como o PCN orienta o ensino de História nos anos iniciais?",
        "O que o PCNEM diz sobre Linguagens no Ensino Médio?",
        "Quais competências gerais a BNCC define para a Educação Básica?",
    ]
    for ex in exemplos:
        st.markdown(f"- *{ex}*")

    st.divider()
    if st.button("Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
