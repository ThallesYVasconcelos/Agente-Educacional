"""Plano de Aula e Verificador BNCC — página do professor."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.automations.lesson_plan import generate_lesson_plan
from src.automations.bncc_checker import check_bncc_alignment

st.set_page_config(page_title="Plano de Aula", page_icon="📝", layout="wide")

PAGE_CSS = """
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }
    .page-header {
        background: linear-gradient(135deg, #6B4EFF 0%, #B23CFF 100%);
        color: #ffffff;
        padding: 1.8rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.8rem;
        box-shadow: 0 12px 30px -12px rgba(107, 78, 255, 0.35);
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

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 12px 12px 0 0;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2E5BFF 0%, #6B4EFF 100%);
        color: #ffffff !important;
        border-color: transparent;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 0 14px 14px 14px;
        padding: 1.8rem;
        margin-top: -1px;
    }

    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #2E5BFF 0%, #6B4EFF 100%);
        border: none;
        border-radius: 10px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 14px rgba(46, 91, 255, 0.35);
        transition: all 0.2s ease;
    }
    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(46, 91, 255, 0.45);
    }

    .alignment-card {
        padding: 1.2rem 1.4rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-size: 1rem;
        border-left: 4px solid;
    }
    .alignment-high {
        background: #E6F9EE;
        border-color: #0A7B3E;
        color: #0A7B3E;
    }
    .alignment-mid {
        background: #FFF4DA;
        border-color: #C08A00;
        color: #8A5A00;
    }
    .alignment-low {
        background: #FFE6E6;
        border-color: #B00020;
        color: #B00020;
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
        <h1>📝 Plano de Aula & Habilidades BNCC</h1>
        <p>
            Crie planos de aula completos alinhados à BNCC ou descubra
            quais habilidades uma atividade desenvolve — tudo embasado nos
            documentos oficiais do MEC.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

ANOS_ESCOLARES = [
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

COMPONENTES = [
    "Língua Portuguesa",
    "Matemática",
    "Ciências",
    "História",
    "Geografia",
    "Arte",
    "Educação Física",
    "Língua Estrangeira",
    "Ensino Religioso",
]


def render_sources(sources, expander_label):
    if not sources:
        return
    with st.expander(expander_label):
        for src in sources:
            meta = src.get("metadata", {})
            nome = meta.get("source", meta.get("source_file", "Documento"))
            excerpt = src["content"][:250].replace("\n", " ").strip()
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">{nome}</div>
                    <div class="source-text">"{excerpt}..."</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


tab1, tab2 = st.tabs(["📋  Criar Plano de Aula", "🔍  Verificar Habilidades da BNCC"])

# ---------------------------------------------------------------------------
# Aba 1 — Gerador de Plano de Aula
# ---------------------------------------------------------------------------

with tab1:
    st.markdown(
        "Preencha os campos abaixo e receba um **plano de aula completo**, pronto "
        "para usar em sala — com objetivos, atividades, recursos e avaliação."
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        componente = st.selectbox("📚 Disciplina", COMPONENTES)
        ano = st.selectbox("🎓 Ano escolar", ANOS_ESCOLARES)
        duracao = st.slider("⏱ Quantidade de aulas", 1, 5, 1)

    with col2:
        habilidade = st.text_area(
            "🎯 Tema ou habilidade que deseja trabalhar",
            placeholder=(
                "Exemplos:\n"
                "• Produção de texto coletivo sobre animais\n"
                "• Adição e subtração com reagrupamento\n"
                "• EF02MA01 — comparar e ordenar números até 1000\n"
                "• Leitura e interpretação de texto literário"
            ),
            height=180,
        )

    st.markdown("")
    if st.button("✨ Criar plano de aula", type="primary", use_container_width=True):
        if not habilidade.strip():
            st.warning("Informe o tema ou a habilidade que deseja trabalhar.")
        else:
            with st.spinner("Criando seu plano de aula com base nos documentos do MEC..."):
                result = generate_lesson_plan(componente, habilidade, ano, duracao)

            if result["success"]:
                st.success("Plano criado com sucesso! Confira abaixo e baixe se quiser.")
            else:
                st.info(
                    "Plano gerado! Alguns detalhes podem precisar de ajuste — "
                    "revise antes de usar em sala."
                )

            st.markdown("---")
            st.markdown(result["lesson_plan"])
            st.markdown("---")

            col_dl, _ = st.columns([1, 2])
            with col_dl:
                st.download_button(
                    "⬇️ Baixar plano (.md)",
                    data=result["lesson_plan"],
                    file_name=f"plano_{componente.lower().replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            render_sources(
                result.get("sources", []),
                "📄 Ver trechos dos documentos utilizados como base",
            )

# ---------------------------------------------------------------------------
# Aba 2 — Verificador de Habilidades BNCC
# ---------------------------------------------------------------------------

with tab2:
    st.markdown(
        "Descreva uma atividade e descubra **quais habilidades da BNCC** "
        "ela desenvolve, com explicação para cada uma."
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        componente_check = st.selectbox(
            "📚 Disciplina", COMPONENTES, key="check_componente"
        )
        ano_check = st.selectbox(
            "🎓 Ano escolar", ANOS_ESCOLARES, key="check_ano"
        )

    with col2:
        descricao = st.text_area(
            "📝 Descreva a atividade",
            placeholder=(
                "Exemplo: Os alunos vão ouvir a leitura de um conto, "
                "depois desenhar a sequência de eventos e recontar a história "
                "em voz alta para os colegas."
            ),
            height=180,
            key="check_descricao",
        )

    st.markdown("")
    if st.button("🔎 Verificar habilidades", type="primary", use_container_width=True):
        if not descricao.strip():
            st.warning("Descreva a atividade para verificar o alinhamento.")
        else:
            with st.spinner("Buscando as habilidades da BNCC relacionadas..."):
                result = check_bncc_alignment(descricao, componente_check, ano_check)

            alinhamento = result.get("alinhamento", "baixo")
            if alinhamento == "alto":
                st.markdown(
                    '<div class="alignment-card alignment-high">'
                    '<strong>✓ Alto alinhamento</strong> com a BNCC. '
                    'A atividade desenvolve habilidades importantes do currículo.'
                    '</div>',
                    unsafe_allow_html=True,
                )
            elif alinhamento == "médio":
                st.markdown(
                    '<div class="alignment-card alignment-mid">'
                    '<strong>⚠ Alinhamento médio</strong>. '
                    'A atividade contempla parte das habilidades — vale enriquecê-la.'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="alignment-card alignment-low">'
                    '<strong>! Alinhamento baixo</strong>. '
                    'Considere ajustar a atividade para contemplar habilidades da BNCC.'
                    '</div>',
                    unsafe_allow_html=True,
                )

            habilidades = result.get("habilidades", [])
            if habilidades:
                st.markdown(f"### 🎯 {len(habilidades)} habilidade(s) identificada(s)")
                for h in habilidades:
                    with st.expander(
                        f"**{h.get('codigo', '?')}** — {h.get('descricao', '')}"
                    ):
                        st.markdown("**Por que esta atividade desenvolve essa habilidade:**")
                        st.markdown(h.get("justificativa", ""))
            else:
                st.info("Não foram identificadas habilidades BNCC específicas para esta atividade.")

            competencias = result.get("competencias_gerais", [])
            if competencias:
                st.markdown("### 🌟 Competências Gerais relacionadas")
                for c in competencias:
                    st.markdown(f"- {c}")

            if obs := result.get("observacoes"):
                st.info(obs)

            render_sources(
                result.get("sources", []),
                "📄 Ver trechos dos documentos consultados",
            )
