"""
EduRAG — Assistente para Professores da Educação Básica.
Interface principal Streamlit.

Execução: python -m streamlit run app/main.py
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path tanto localmente
# quanto no Streamlit Cloud (onde o cwd pode ser app/ ou a raiz do repo)
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st


def home():
    st.set_page_config(
        page_title="Assistente do Professor",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📚 Assistente do Professor")
    st.markdown(
        "Bem-vindo! Este assistente foi criado para **apoiar professores da Educação Básica** "
        "na consulta a documentos oficiais do MEC — da Educação Infantil ao Ensino Médio."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.info(
            "### 💬 Tirar dúvidas\n"
            "Pergunte sobre habilidades e competências da BNCC, "
            "objetivos de aprendizagem do PCN, metodologias de alfabetização "
            "e letramento, e orientações curriculares para qualquer ano escolar.\n\n"
            "As respostas sempre indicam **de qual documento veio a informação**."
        )

    with col2:
        st.info(
            "### 📝 Plano de Aula\n"
            "Crie um plano de aula completo em segundos: basta informar "
            "o componente curricular, o ano escolar e o tema ou habilidade desejada.\n\n"
            "O plano vem pronto com objetivos, atividades, recursos e avaliação, "
            "já alinhado à BNCC."
        )

    st.divider()

    st.subheader("O que este assistente sabe?")
    st.markdown(
        """
        O assistente foi alimentado com os seguintes documentos oficiais do **Ministério da Educação (MEC)**,
        todos de acesso público e gratuito:

        | Documento | O que contém |
        |---|---|
        | **BNCC — Educação Infantil e Ensino Fundamental** | Habilidades e competências do 1º ao 9º ano |
        | **PCN — Anos Iniciais (1ª a 4ª série)** | Língua Portuguesa, Matemática, Ciências, História, Geografia, Arte e Educação Física |
        | **PCN — Anos Finais (5ª a 8ª série)** | Língua Portuguesa, Matemática, Ciências, História, Geografia, Arte, Ed. Física e Língua Estrangeira |
        | **PCNEM — Ensino Médio** | Linguagens, Ciências da Natureza, Ciências Humanas e Bases Legais |
        | **PCN+ — Ensino Médio** | Orientações complementares por área de conhecimento |
        """
    )

    st.caption(
        "Todos os documentos são de domínio público (MEC/gov.br). "
        "As respostas têm caráter pedagógico e informativo — consulte sempre o documento original para decisões formais. "
        "[Ver código-fonte](https://github.com/ThallesYVasconcelos/Agente-Educacional)"
    )


pg = st.navigation([
    st.Page(home, title="Home", icon="📚", default=True),
    st.Page("pages/1_assistente.py", title="Assistente", icon="💬"),
    st.Page("pages/2_plano_aula.py", title="Plano de Aula", icon="📝"),
])

pg.run()
