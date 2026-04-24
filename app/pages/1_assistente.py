"""Assistente Pedagógico — página de chat do professor."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.agents.educacao_agent import EducacaoAgent

st.set_page_config(page_title="Tirar Dúvidas", page_icon="💬", layout="wide")

PAGE_CSS = """
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }
    .page-header {
        background: linear-gradient(135deg, #2E5BFF 0%, #6B4EFF 100%);
        color: #ffffff;
        padding: 1.8rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.8rem;
        box-shadow: 0 12px 30px -12px rgba(46, 91, 255, 0.35);
    }
    .page-header h1 {
        margin: 0 0 0.3rem 0;
        font-size: 1.9rem;
        font-weight: 700;
        color: #ffffff;
    }
    .page-header p {
        margin: 0;
        font-size: 1rem;
        opacity: 0.95;
        line-height: 1.5;
        max-width: 750px;
    }
    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    [data-testid="stChatInput"] {
        background: #ffffff;
        border-radius: 14px;
        border: 2px solid #E6EAF5;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #2E5BFF;
    }
    .quality-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    .quality-high { background: #E6F9EE; color: #0A7B3E; }
    .quality-mid  { background: #FFF4DA; color: #8A5A00; }
    .quality-low  { background: #FFE6E6; color: #B00020; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FAFBFF 0%, #F0F3FF 100%);
    }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #1A1F36;
    }
    .sidebar-suggestion {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 10px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 0.5rem;
        font-size: 0.88rem;
        color: #1A1F36;
        line-height: 1.4;
    }
    .source-card {
        background: #FAFBFF;
        border-left: 3px solid #2E5BFF;
        border-radius: 8px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.8rem;
    }
    .source-card .source-title {
        font-weight: 700;
        color: #1A1F36;
        font-size: 0.92rem;
        margin-bottom: 0.4rem;
    }
    .source-card .source-text {
        color: #5A6378;
        font-size: 0.88rem;
        line-height: 1.5;
        font-style: italic;
    }
</style>
"""

st.markdown(PAGE_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-header">
        <h1>💬 Tirar Dúvidas</h1>
        <p>
            Pergunte sobre habilidades da BNCC, objetivos do PCN, metodologias de ensino
            ou qualquer orientação curricular. As respostas vêm direto dos documentos do MEC,
            com indicação clara da fonte.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def quality_badge(score: float, n_sources: int) -> str:
    if score >= 0.7:
        cls, icon, label = "quality-high", "✓", "Resposta bem embasada"
    elif score >= 0.5:
        cls, icon, label = "quality-mid", "⚠", "Resposta parcialmente embasada"
    else:
        cls, icon, label = "quality-low", "!", "Poucos trechos encontrados"
    return (
        f'<span class="quality-badge {cls}">{icon} {label} · '
        f'{n_sources} trecho(s) consultado(s)</span>'
    )


if "agent" not in st.session_state:
    with st.spinner("Carregando os documentos pedagógicos..."):
        st.session_state.agent = EducacaoAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "meta" in msg:
            score = msg["meta"].get("self_check_score", 0)
            n_fontes = len(msg["meta"].get("sources", []))
            st.markdown(quality_badge(score, n_fontes), unsafe_allow_html=True)

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
        st.markdown(quality_badge(score, len(sources)), unsafe_allow_html=True)

        if sources:
            with st.expander(f"📄 Ver os {len(sources)} trechos consultados nos documentos"):
                for i, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    doc_nome = meta.get("source", meta.get("source_file", "Documento"))
                    pagina = meta.get("page", "")
                    pagina_str = f" — página {pagina + 1}" if pagina != "" else ""
                    excerpt = src["content"][:300].replace("\n", " ").strip()
                    st.markdown(
                        f"""
                        <div class="source-card">
                            <div class="source-title">{i}. {doc_nome}{pagina_str}</div>
                            <div class="source-text">"{excerpt}..."</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "meta": {"self_check_score": score, "sources": sources},
    })

with st.sidebar:
    st.markdown("### 💡 Sugestões de perguntas")
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
        st.markdown(
            f'<div class="sidebar-suggestion">{ex}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("🗑 Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
