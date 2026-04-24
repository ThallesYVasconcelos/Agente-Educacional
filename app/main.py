"""
EduRAG — Assistente para Professores da Educação Básica.
Interface principal Streamlit.

Execução: python -m streamlit run app/main.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st


CUSTOM_CSS = """
<style>
    /* ----------- Reset suave e tipografia ----------- */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    h1, h2, h3 {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        letter-spacing: -0.02em;
    }

    /* ----------- Hero ----------- */
    .edurag-hero {
        background: linear-gradient(135deg, #2E5BFF 0%, #6B4EFF 50%, #B23CFF 100%);
        color: #ffffff;
        padding: 3rem 2.5rem;
        border-radius: 24px;
        margin-bottom: 2.5rem;
        box-shadow: 0 20px 50px -15px rgba(46, 91, 255, 0.35);
        position: relative;
        overflow: hidden;
    }
    .edurag-hero::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -10%;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .edurag-hero h1 {
        font-size: 2.6rem;
        font-weight: 700;
        margin: 0 0 0.6rem 0;
        color: #ffffff;
        position: relative;
    }
    .edurag-hero p {
        font-size: 1.15rem;
        margin: 0;
        opacity: 0.95;
        max-width: 700px;
        position: relative;
        line-height: 1.55;
    }
    .edurag-hero .badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        backdrop-filter: blur(10px);
        position: relative;
    }

    /* ----------- Cards de feature ----------- */
    .feature-card {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 18px;
        padding: 1.8rem;
        height: 100%;
        transition: all 0.25s ease;
        box-shadow: 0 2px 8px rgba(46, 91, 255, 0.04);
    }
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px -10px rgba(46, 91, 255, 0.18);
        border-color: #2E5BFF;
    }
    .feature-card .feature-icon {
        font-size: 2.2rem;
        display: block;
        margin-bottom: 0.7rem;
    }
    .feature-card h3 {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1A1F36;
        margin: 0 0 0.6rem 0;
    }
    .feature-card p {
        color: #5A6378;
        font-size: 0.96rem;
        line-height: 1.55;
        margin: 0;
    }

    /* ----------- Sessão "O que sei" ----------- */
    .docs-section {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 18px;
        padding: 2rem;
        margin-top: 2rem;
    }
    .doc-item {
        display: flex;
        gap: 1rem;
        padding: 1rem 0;
        border-bottom: 1px solid #F0F3FF;
    }
    .doc-item:last-child { border-bottom: none; }
    .doc-item .doc-tag {
        background: linear-gradient(135deg, #EEF1FF 0%, #F5EFFF 100%);
        color: #2E5BFF;
        padding: 0.4rem 0.85rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.85rem;
        height: fit-content;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .doc-item .doc-info strong {
        color: #1A1F36;
        font-size: 1.0rem;
        display: block;
        margin-bottom: 0.2rem;
    }
    .doc-item .doc-info span {
        color: #5A6378;
        font-size: 0.9rem;
        line-height: 1.4;
    }

    /* ----------- Estatísticas ----------- */
    .stat-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin: 1.5rem 0 0.5rem 0;
    }
    .stat-card {
        background: linear-gradient(135deg, #F0F3FF 0%, #FAFBFF 100%);
        padding: 1.4rem;
        border-radius: 14px;
        text-align: center;
        border: 1px solid #E6EAF5;
    }
    .stat-card .stat-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2E5BFF 0%, #B23CFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1;
        margin-bottom: 0.3rem;
    }
    .stat-card .stat-label {
        color: #5A6378;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* ----------- Botões e inputs ----------- */
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #2E5BFF 0%, #6B4EFF 100%);
        border: none;
        box-shadow: 0 4px 14px rgba(46, 91, 255, 0.35);
    }
    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(46, 91, 255, 0.45);
    }

    /* ----------- Chat ----------- */
    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }

    /* ----------- Sidebar ----------- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FAFBFF 0%, #F0F3FF 100%);
        border-right: 1px solid #E6EAF5;
    }

    /* ----------- Footer minimalista ----------- */
    .edurag-footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #E6EAF5;
        text-align: center;
        color: #8892A6;
        font-size: 0.85rem;
        line-height: 1.6;
    }
    .edurag-footer a { color: #2E5BFF; text-decoration: none; }
    .edurag-footer a:hover { text-decoration: underline; }
</style>
"""


def home():
    st.set_page_config(
        page_title="Assistente do Professor",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Hero
    st.markdown(
        """
        <div class="edurag-hero">
            <span class="badge">📚 Educação Básica · Gratuito</span>
            <h1>Assistente do Professor</h1>
            <p>
                Tire dúvidas curriculares e crie planos de aula em segundos —
                tudo embasado nos documentos oficiais do MEC, da Educação Infantil ao Ensino Médio.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Estatísticas
    st.markdown(
        """
        <div class="stat-row">
            <div class="stat-card">
                <div class="stat-value">5</div>
                <div class="stat-label">Documentos oficiais do MEC</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">12</div>
                <div class="stat-label">Anos da Educação Básica</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">9</div>
                <div class="stat-label">Componentes curriculares</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Como posso te ajudar hoje?")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <span class="feature-icon">💬</span>
                <h3>Tirar dúvidas curriculares</h3>
                <p>
                    Pergunte sobre habilidades da BNCC, objetivos do PCN,
                    metodologias de alfabetização ou orientações curriculares para qualquer ano.
                    O assistente sempre indica de qual documento veio a informação.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <span class="feature-icon">📝</span>
                <h3>Criar plano de aula</h3>
                <p>
                    Informe a disciplina, o ano e o tema — e receba um plano completo
                    com objetivos, atividades, recursos e avaliação,
                    já alinhado à BNCC e pronto para usar em sala.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Seção de documentos
    st.markdown(
        """
        <div class="docs-section">
            <h3 style="margin-top:0; margin-bottom:0.3rem;">📖 Base de conhecimento</h3>
            <p style="color:#5A6378; margin-bottom:1.2rem;">
                Documentos oficiais do <strong>Ministério da Educação</strong> usados como fonte das respostas:
            </p>
            <div class="doc-item">
                <span class="doc-tag">BNCC</span>
                <div class="doc-info">
                    <strong>Educação Infantil e Ensino Fundamental</strong>
                    <span>Habilidades e competências do 1º ao 9º ano</span>
                </div>
            </div>
            <div class="doc-item">
                <span class="doc-tag">PCN AI</span>
                <div class="doc-info">
                    <strong>Anos Iniciais (1ª a 4ª série)</strong>
                    <span>Língua Portuguesa, Matemática, Ciências, História, Geografia, Arte e Educação Física</span>
                </div>
            </div>
            <div class="doc-item">
                <span class="doc-tag">PCN AF</span>
                <div class="doc-info">
                    <strong>Anos Finais (5ª a 8ª série)</strong>
                    <span>Língua Portuguesa, Matemática, Ciências, História, Geografia, Arte, Ed. Física e Língua Estrangeira</span>
                </div>
            </div>
            <div class="doc-item">
                <span class="doc-tag">PCNEM</span>
                <div class="doc-info">
                    <strong>Ensino Médio</strong>
                    <span>Linguagens, Ciências da Natureza, Ciências Humanas e Bases Legais</span>
                </div>
            </div>
            <div class="doc-item">
                <span class="doc-tag">PCN+</span>
                <div class="doc-info">
                    <strong>Ensino Médio — Orientações Complementares</strong>
                    <span>Aprofundamento por área de conhecimento</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Footer
    st.markdown(
        """
        <div class="edurag-footer">
            Todos os documentos são de domínio público (MEC/gov.br).
            As respostas têm caráter pedagógico e informativo —
            consulte sempre o documento original para decisões formais.<br>
            <a href="https://github.com/ThallesYVasconcelos/Agente-Educacional" target="_blank">Ver código-fonte</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


pg = st.navigation([
    st.Page(home, title="Início", icon="📚", default=True),
    st.Page("pages/1_assistente.py", title="Tirar Dúvidas", icon="💬"),
    st.Page("pages/2_plano_aula.py", title="Plano de Aula", icon="📝"),
])

pg.run()
