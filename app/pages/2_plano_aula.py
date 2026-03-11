"""
EduRAG — Gerador de Plano de Aula + Verificador de Habilidades BNCC.

Focado nos Anos Iniciais do Ensino Fundamental (1º ao 4º ano).
Automação A1: gera plano de aula estruturado com citações normativas.
Automação A2: verifica alinhamento de atividade com habilidades BNCC (EF01–EF04).
"""

import streamlit as st

from src.automations.lesson_plan import generate_lesson_plan
from src.automations.bncc_checker import check_bncc_alignment

st.set_page_config(page_title="Plano de Aula & BNCC", page_icon="📝", layout="wide")

st.title("📝 Automações Pedagógicas — Anos Iniciais (1º ao 4º ano)")
st.markdown("Ferramentas de automação baseadas na BNCC e PCN para os **Anos Iniciais do Ensino Fundamental**.")
st.divider()

tab1, tab2 = st.tabs(["📋 Gerador de Plano de Aula", "🔍 Verificador de Habilidades BNCC"])

# ---------------------------------------------------------------------------
# Aba 1 — Gerador de Plano de Aula
# ---------------------------------------------------------------------------

with tab1:
    st.subheader("Gerador de Plano de Aula")
    st.markdown(
        "Gera um plano de aula completo e estruturado com base nas habilidades da BNCC e PCN. "
        "O plano inclui objetivos, sequência de atividades, recursos e avaliação."
    )

    col1, col2 = st.columns(2)

    with col1:
        componente = st.selectbox(
            "Componente Curricular",
            [
                "Língua Portuguesa",
                "Matemática",
                "Ciências",
                "História",
                "Geografia",
                "Arte",
                "Educação Física",
                "Ensino Religioso",
            ],
        )
        ano = st.selectbox(
            "Ano",
            [
                "1º ano do Ensino Fundamental",
                "2º ano do Ensino Fundamental",
                "3º ano do Ensino Fundamental",
                "4º ano do Ensino Fundamental",
            ],
        )

    with col2:
        habilidade = st.text_area(
            "Habilidade BNCC ou Tema",
            placeholder="Ex.: EF02MA01 — Comparar e ordenar números naturais até 1000...\nOu descreva o tema livremente: 'produção de texto coletivo sobre animais'.",
            height=100,
        )
        duracao = st.slider("Duração (número de aulas)", 1, 5, 1)

    if st.button("Gerar Plano de Aula", type="primary", use_container_width=True):
        if not habilidade.strip():
            st.warning("Informe a habilidade BNCC ou o tema da aula.")
        else:
            with st.spinner("Gerando plano de aula com base na BNCC e PCN..."):
                result = generate_lesson_plan(componente, habilidade, ano, duracao)

            if result["success"]:
                st.success(
                    f"Plano gerado com sucesso! "
                    f"{result['citations_count']} citações normativas · "
                    f"{len(result['sections_present'])}/5 seções · "
                    f"{result['elapsed_seconds']}s"
                )
            else:
                st.warning(
                    f"Plano gerado com ressalvas: "
                    f"{result['citations_count']} citação(ões) · "
                    f"{len(result['sections_present'])}/5 seções presentes. "
                    "Considere adicionar mais documentos ao corpus."
                )

            st.markdown(result["lesson_plan"])

            with st.expander("Ver documentos utilizados como base"):
                for src in result.get("sources", []):
                    meta = src.get("metadata", {})
                    nome = meta.get("source", meta.get("source_file", "Fonte"))
                    st.markdown(f"**{nome}**")
                    st.markdown(f"> {src['content'][:250]}...")
                    st.divider()

            st.download_button(
                "Baixar plano (.md)",
                data=result["lesson_plan"],
                file_name=f"plano_{componente.lower().replace(' ', '_')}_{ano[:2]}ano.md",
                mime="text/markdown",
            )

# ---------------------------------------------------------------------------
# Aba 2 — Verificador de Habilidades BNCC
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Verificador de Alinhamento com a BNCC")
    st.markdown(
        "Descreva uma atividade ou conteúdo de aula e descubra quais "
        "habilidades da BNCC ela desenvolve, com justificativas baseadas no documento oficial."
    )

    col1, col2 = st.columns(2)
    with col1:
        componente_check = st.selectbox(
            "Componente Curricular",
            [
                "Língua Portuguesa",
                "Matemática",
                "Ciências",
                "História",
                "Geografia",
                "Arte",
                "Educação Física",
                "Ensino Religioso",
            ],
            key="check_componente",
        )
        ano_check = st.selectbox(
            "Ano",
            [
                "1º ano do Ensino Fundamental",
                "2º ano do Ensino Fundamental",
                "3º ano do Ensino Fundamental",
                "4º ano do Ensino Fundamental",
            ],
            key="check_ano",
        )

    with col2:
        descricao = st.text_area(
            "Descrição da atividade",
            placeholder="Ex.: Os alunos vão escutar a leitura em voz alta de um conto, "
            "depois desenhar a sequência de eventos e recontar oralmente para o grupo.",
            height=150,
            key="check_descricao",
        )

    if st.button("Verificar Habilidades BNCC", type="primary", use_container_width=True):
        if not descricao.strip():
            st.warning("Descreva a atividade para verificar o alinhamento.")
        else:
            with st.spinner("Analisando alinhamento com a BNCC..."):
                result = check_bncc_alignment(descricao, componente_check, ano_check)

            alinhamento = result.get("alinhamento", "baixo")
            color_map = {"alto": "success", "médio": "warning", "baixo": "error"}
            level_fn = getattr(st, color_map.get(alinhamento, "info"))
            level_fn(f"Nível de alinhamento BNCC: **{alinhamento.upper()}**")

            habilidades = result.get("habilidades", [])
            if habilidades:
                st.subheader(f"{len(habilidades)} habilidade(s) identificada(s)")
                for h in habilidades:
                    with st.expander(f"**{h.get('codigo', '?')}** — {h.get('descricao', '')}"):
                        st.markdown(f"**Justificativa:** {h.get('justificativa', '')}")

            competencias = result.get("competencias_gerais", [])
            if competencias:
                st.subheader("Competências Gerais relacionadas")
                for c in competencias:
                    st.markdown(f"- {c}")

            if obs := result.get("observacoes"):
                st.info(f"**Observações:** {obs}")

            with st.expander("Ver documentos consultados"):
                for src in result.get("sources", []):
                    meta = src.get("metadata", {})
                    nome = meta.get("source", meta.get("source_file", "Fonte"))
                    st.markdown(f"**{nome}**")
                    st.markdown(f"> {src['content'][:250]}...")
                    st.divider()
