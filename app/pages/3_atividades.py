"""Gerador de Atividades — página do professor."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.automations.activity_generator import (
    ACTIVITY_TYPES,
    generate_activities,
)
from src.automations.content_generator import CURRICULUM_SCOPE
from src.utils.pdf_export import markdown_to_pdf
from src.utils.docx_export import markdown_to_docx

st.set_page_config(page_title="Gerador de Atividades", page_icon="✏️", layout="wide")

PAGE_CSS = """
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }
    .page-header {
        background: linear-gradient(135deg, #0A7B3E 0%, #15C262 100%);
        color: #ffffff;
        padding: 1.8rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.8rem;
        box-shadow: 0 12px 30px -12px rgba(10, 123, 62, 0.4);
    }
    .page-header h1 { margin: 0 0 0.3rem 0; font-size: 1.9rem; font-weight: 700; color: #ffffff; }
    .page-header p  { margin: 0; font-size: 1rem; opacity: 0.95; line-height: 1.5; max-width: 750px; }

    .info-box {
        background: #F0FBF4;
        border: 1px solid #A8E6C0;
        border-left: 4px solid #0A7B3E;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
        font-size: 0.95rem;
        color: #1A3E2A;
    }
    .validated-badge {
        display: inline-block;
        background: #E6F9EE;
        color: #0A7B3E;
        border: 1px solid #A8E6C0;
        border-radius: 20px;
        padding: 0.25rem 0.85rem;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
    .correction-badge {
        display: inline-block;
        background: #FFF4DA;
        color: #8A5A00;
        border: 1px solid #F5D87A;
        border-radius: 20px;
        padding: 0.25rem 0.85rem;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
        margin-left: 0.5rem;
    }
    .result-panel {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 14px;
        padding: 1.6rem;
        margin-top: 1rem;
    }
    .level-legend {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
        font-size: 0.88rem;
        color: #5A6378;
    }
    .source-card {
        background: #FAFBFF;
        border-left: 3px solid #0A7B3E;
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
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #0A7B3E 0%, #15C262 100%);
        border: none;
        border-radius: 10px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 14px rgba(10, 123, 62, 0.35);
        transition: all 0.2s ease;
    }
    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(10, 123, 62, 0.45);
    }
</style>
"""

st.markdown(PAGE_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-header">
        <h1>✏️ Gerador de Atividades</h1>
        <p>
            Crie listas de exercícios, situações-problema e atividades de fixação
            alinhadas à BNCC — com gabarito completo para o professor e versão
            limpa para imprimir e distribuir aos alunos.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ✏️ Gerador de Atividades")
    st.markdown(
        """
        **Como funciona a confiabilidade?**

        O sistema usa dois passos:

        1. **Geração** — cria as atividades respeitando o escopo curricular do ano
        2. **Validação automática** — um segundo agente verifica cada resposta e corrige se necessário

        Questões corrigidas ficam marcadas com 🔧 no gabarito do professor.

        ---
        **Legenda de dificuldade:**
        - 🟢 Fácil
        - 🟡 Médio
        - 🔴 Desafiador
        """
    )

# ── Formulário ────────────────────────────────────────────────────────────
ANOS = [
    "1º ano do Ensino Fundamental",
    "2º ano do Ensino Fundamental",
    "3º ano do Ensino Fundamental",
    "4º ano do Ensino Fundamental",
    "5º ano do Ensino Fundamental",
    "6º ano do Ensino Fundamental",
    "7º ano do Ensino Fundamental",
    "8º ano do Ensino Fundamental",
    "9º ano do Ensino Fundamental",
    "1º ano do Ensino Médio",
    "2º ano do Ensino Médio",
    "3º ano do Ensino Médio",
]

DISCIPLINAS = sorted(CURRICULUM_SCOPE.keys()) + [
    "Arte",
    "Educação Física",
    "Ensino Religioso",
    "Língua Estrangeira (Inglês)",
]
DISCIPLINAS = sorted(set(DISCIPLINAS))

col1, col2 = st.columns([2, 1])

with col1:
    topico = st.text_input(
        "🎯 Tópico / Conteúdo",
        placeholder="Ex: Potenciação, Células, Revolução Industrial, Interpretação de texto…",
        help="Informe o tema que deseja trabalhar com os alunos.",
    )

with col2:
    componente = st.selectbox("📚 Disciplina", DISCIPLINAS)

col3, col4, col5 = st.columns([2, 2, 1])

with col3:
    ano = st.selectbox("🎓 Ano escolar", ANOS, index=5)

with col4:
    tipo = st.selectbox(
        "📋 Tipo de atividade",
        options=list(ACTIVITY_TYPES.keys()),
        format_func=lambda k: ACTIVITY_TYPES[k],
        index=3,
    )

with col5:
    quantidade = st.number_input(
        "Nº de questões",
        min_value=3,
        max_value=10,
        value=6,
        step=1,
        help="Entre 3 e 10 questões por lista.",
    )

# Escopo curricular do ano selecionado
escopo_atual = CURRICULUM_SCOPE.get(componente, {}).get(ano, "")
if escopo_atual:
    with st.expander("👁 Ver o que está previsto para este ano (escopo curricular)"):
        st.info(escopo_atual)

st.markdown(
    """
    <div class="info-box">
        <strong>Como garantimos a qualidade das atividades?</strong><br>
        As atividades são geradas respeitando o escopo curricular oficial (BNCC/PCN) para o ano e
        disciplina selecionados. Em seguida, um segundo agente verifica cada resposta e corrige
        eventuais erros antes de exibir o resultado. As questões corrigidas ficam marcadas no
        gabarito do professor.
    </div>
    """,
    unsafe_allow_html=True,
)

gerar = st.button("✏️ Gerar atividades", type="primary", use_container_width=True)

# ── Resultado ─────────────────────────────────────────────────────────────
if gerar:
    if not topico.strip():
        st.warning("Informe o tópico / conteúdo antes de gerar.")
        st.stop()

    with st.spinner("Gerando e validando as atividades… Isso pode levar até 1 minuto."):
        result = generate_activities(
            topico=topico.strip(),
            componente=componente,
            ano_escolar=ano,
            tipo=tipo,
            quantidade=int(quantidade),
        )

    if not result["success"]:
        st.error(result.get("error", "Erro ao gerar atividades. Tente novamente."))
        st.stop()

    # Badges de status
    status_html = '<span class="validated-badge">✅ Gabarito validado automaticamente</span>'
    if result["corrections"] > 0:
        status_html += (
            f'<span class="correction-badge">'
            f'🔧 {result["corrections"]} questão(ões) corrigida(s)</span>'
        )
    st.markdown(status_html, unsafe_allow_html=True)
    st.caption(f"Gerado em {result['elapsed_seconds']}s")

    # Abas: aluno / professor
    tab_aluno, tab_professor = st.tabs(["👧 Versão do Aluno", "👩‍🏫 Versão do Professor (com gabarito)"])

    with tab_aluno:
        st.markdown(
            """
            <div class="result-panel">
            <div class="level-legend">🟢 Fácil &nbsp;&nbsp; 🟡 Médio &nbsp;&nbsp; 🔴 Desafiador</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(result["student_md"])
        st.markdown("</div>", unsafe_allow_html=True)

        col_pdf, col_docx = st.columns(2)
        with col_pdf:
            pdf_aluno = markdown_to_pdf(
                result["student_md"],
                title=f"Atividades — {componente} ({ano}) | Tópico: {topico}",
            )
            st.download_button(
                "⬇️ Baixar PDF (versão aluno)",
                data=pdf_aluno,
                file_name=f"atividades_{topico[:30].replace(' ', '_')}_aluno.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_docx:
            docx_aluno = markdown_to_docx(
                result["student_md"],
                title=f"Atividades — {componente} ({ano}) | Tópico: {topico}",
            )
            st.download_button(
                "⬇️ Baixar DOCX (versão aluno)",
                data=docx_aluno,
                file_name=f"atividades_{topico[:30].replace(' ', '_')}_aluno.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    with tab_professor:
        st.markdown(
            """
            <div class="result-panel">
            <div class="level-legend">🟢 Fácil &nbsp;&nbsp; 🟡 Médio &nbsp;&nbsp; 🔴 Desafiador
            &nbsp;&nbsp; | &nbsp;&nbsp; ✅ Validado &nbsp;&nbsp; 🔧 Corrigido pelo validador</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(result["teacher_md"])
        st.markdown("</div>", unsafe_allow_html=True)

        col_pdf2, col_docx2 = st.columns(2)
        with col_pdf2:
            pdf_prof = markdown_to_pdf(
                result["teacher_md"],
                title=f"Gabarito — {componente} ({ano}) | USO DO PROFESSOR",
            )
            st.download_button(
                "⬇️ Baixar PDF (gabarito professor)",
                data=pdf_prof,
                file_name=f"gabarito_{topico[:30].replace(' ', '_')}_professor.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_docx2:
            docx_prof = markdown_to_docx(
                result["teacher_md"],
                title=f"Gabarito — {componente} ({ano}) | USO DO PROFESSOR",
            )
            st.download_button(
                "⬇️ Baixar DOCX (gabarito professor)",
                data=docx_prof,
                file_name=f"gabarito_{topico[:30].replace(' ', '_')}_professor.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    # Trechos consultados
    sources = result.get("sources", [])
    if sources:
        with st.expander("📄 Ver trechos dos documentos curriculares consultados"):
            for src in sources:
                doc_name = src["metadata"].get("source", "Documento")
                st.markdown(
                    f"""
                    <div class="source-card">
                        <div class="source-title">{doc_name}</div>
                        <div class="source-text">{src['content'][:400]}…</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
