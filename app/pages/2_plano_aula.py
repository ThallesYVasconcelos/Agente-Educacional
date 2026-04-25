"""Plano de Aula e Verificador BNCC — página do professor."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.automations.lesson_plan import generate_lesson_plan
from src.automations.content_generator import generate_class_content, CURRICULUM_SCOPE
from src.utils.pdf_export import markdown_to_pdf

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


tab1, tab2 = st.tabs(["📋  Criar Plano de Aula", "📖  Conteúdo da Aula"])

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

            nome_base = f"plano_{componente.lower().replace(' ', '_')}"
            col_pdf, col_md, _ = st.columns([1, 1, 1])
            with col_pdf:
                titulo_pdf = f"Plano de Aula — {componente} ({ano})"
                pdf_bytes = markdown_to_pdf(result["lesson_plan"], titulo_pdf)
                st.download_button(
                    "⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"{nome_base}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            with col_md:
                st.download_button(
                    "⬇️ Baixar Markdown",
                    data=result["lesson_plan"].encode("utf-8"),
                    file_name=f"{nome_base}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            render_sources(
                result.get("sources", []),
                "📄 Ver trechos dos documentos utilizados como base",
            )

# ---------------------------------------------------------------------------
# Aba 2 — Gerador de Conteúdo de Aula com Escopo Curricular
# ---------------------------------------------------------------------------

with tab2:
    st.markdown(
        "Informe o **tópico** que deseja ensinar e o **ano escolar** — "
        "o assistente gera o conteúdo completo da aula respeitando "
        "**exatamente o que é previsto para aquela série** conforme BNCC e PCN. "
        "Nada além, nada aquém."
    )

    # Aviso explicativo
    st.markdown(
        """
        <div style="background:#EEF1FF;border-left:4px solid #2E5BFF;border-radius:8px;
                    padding:0.9rem 1.1rem;margin:0.5rem 0 1.2rem 0;font-size:0.93rem;color:#1A1F36;">
            <strong>Como funciona o controle de escopo?</strong><br>
            O sistema conhece a progressão curricular de cada série. Por exemplo:<br>
            • <em>Potenciação no 6º ano</em> → apenas números naturais e propriedades básicas.<br>
            • <em>Potenciação no 7º ano</em> → inclui expoentes inteiros negativos (introdução).<br>
            • <em>Potenciação no 8º ano</em> → expoentes fracionários e relação com radiciação.<br>
            O conteúdo gerado sempre indica o que <strong>não trabalhar</strong> naquele ano.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        componente_content = st.selectbox(
            "📚 Disciplina", COMPONENTES, key="content_componente"
        )
        ano_content = st.selectbox(
            "🎓 Ano escolar", ANOS_ESCOLARES, key="content_ano"
        )

        # Mostra o escopo curricular mapeado para o ano selecionado
        escopo_preview = (
            CURRICULUM_SCOPE
            .get(componente_content, {})
            .get(ano_content, "")
        )
        if escopo_preview:
            with st.expander("👁 Ver o que está previsto para este ano (escopo curricular)"):
                st.markdown(
                    f"<div style='font-size:0.88rem;color:#3A4055;line-height:1.6'>{escopo_preview}</div>",
                    unsafe_allow_html=True,
                )

    with col2:
        topico = st.text_area(
            "🎯 Tópico / Conteúdo da aula",
            placeholder=(
                "Exemplos:\n"
                "• Potenciação (Matemática — 6º ano)\n"
                "• Estrutura da célula (Ciências — 6º ano)\n"
                "• Gênero textual: crônica (Língua Portuguesa — 7º ano)\n"
                "• Roma Antiga (História — 6º ano)\n"
                "• Cartografia e coordenadas geográficas (Geografia — 6º ano)"
            ),
            height=200,
            key="content_topico",
        )

    st.markdown("")
    if st.button("✨ Gerar conteúdo da aula", type="primary", use_container_width=True):
        if not topico.strip():
            st.warning("Informe o tópico que deseja trabalhar.")
        else:
            with st.spinner(
                f"Gerando conteúdo de '{topico}' para o {ano_content} "
                "respeitando o escopo curricular..."
            ):
                result = generate_class_content(topico, componente_content, ano_content)

            if result["success"]:
                st.success("Conteúdo gerado com sucesso! Dentro do escopo curricular do ano.")
            else:
                st.info(
                    "Conteúdo gerado. Revise se está adequado ao nível da turma "
                    "antes de usar em sala."
                )

            st.markdown("---")
            st.markdown(result["content"])
            st.markdown("---")

            slug = (
                f"conteudo_{topico[:30].lower().replace(' ', '_')}"
                f"_{ano_content[:6].replace('º', '').replace(' ', '')}"
            )
            col_pdf2, col_md2, _ = st.columns([1, 1, 1])
            with col_pdf2:
                titulo_pdf2 = f"Conteúdo da Aula — {topico} ({ano_content})"
                pdf_bytes2 = markdown_to_pdf(result["content"], titulo_pdf2)
                st.download_button(
                    "⬇️ Baixar PDF",
                    data=pdf_bytes2,
                    file_name=f"{slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            with col_md2:
                st.download_button(
                    "⬇️ Baixar Markdown",
                    data=result["content"].encode("utf-8"),
                    file_name=f"{slug}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            render_sources(
                result.get("sources", []),
                "📄 Ver trechos dos documentos curriculares consultados",
            )
