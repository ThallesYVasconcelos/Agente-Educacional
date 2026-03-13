"""
EduRAG — Assistente para Professores da Educação Básica.
Interface principal Streamlit.

Execução: python -m streamlit run app/main.py
"""

import streamlit as st


def home():
    st.set_page_config(
        page_title="EduRAG — Assistente para Professores",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📚 EduRAG — Assistente para Professores dos Anos Iniciais")
    st.markdown(
        """
        Sistema RAG com agentes LangGraph para apoiar professores dos **Anos Iniciais do Ensino Fundamental** (1º ao 4º ano).
        Baseado na **BNCC**, **PCN** e guias do **PNLD** — documentos públicos do MEC.
        """
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.info(
            "### 💬 Assistente Pedagógico\n"
            "Tire dúvidas sobre BNCC, PCN, alfabetização, letramento e metodologias "
            "para o 1º ao 4º ano.\n\n"
            "Respostas com **citações** e verificação de fidelidade (Self-RAG).\n\n"
            "**Corpus:** BNCC 2017 · PCN 1997–2000 · PNLD"
        )

    with col2:
        st.info(
            "### 📝 Plano de Aula & BNCC\n"
            "Gere planos de aula para o 1º ao 4º ano com habilidades BNCC (EF01–EF04), "
            "sequência de atividades e avaliação.\n\n"
            "**Automação:** verificador de alinhamento BNCC integrado."
        )

    st.divider()

    st.subheader("Arquitetura do sistema")
    st.markdown(
        """
        ```
        Usuário
          │
          ▼
        Streamlit UI
          │
          ▼
        LangGraph (Supervisor)
          ├─ Q&A route   → Retriever → Safety → Writer → Self-check
          └─ Auto route  → Automação A1/A2 (Plano de Aula / BNCC Checker)
          │
          ▼
        ChromaDB (BAAI/bge-m3)        MCP Server (FastAPI)
        BNCC · PCN · PNLD              search_docs · lesson_plan · bncc_skills
          │
          ▼
        Ollama (LLM local OSS)
        llama3.2 / qwen2.5 / mistral
        ```
        """
    )

    st.caption(
        "Corpus: documentos públicos do MEC (CC BY / domínio público). "
        "As respostas têm caráter pedagógico e informativo. "
        "MIT License | [GitHub](https://github.com/ThallesYVasconcelos/Agente-Educacional)"
    )


pg = st.navigation([
    st.Page(home, title="Home", icon="📚", default=True),
    st.Page("pages/1_assistente.py", title="Assistente", icon="💬"),
    st.Page("pages/2_plano_aula.py", title="Plano de Aula", icon="📝"),
])

pg.run()
