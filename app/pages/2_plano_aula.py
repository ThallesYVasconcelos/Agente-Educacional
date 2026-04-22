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

st.title("📝 Criar Plano de Aula e Verificar Habilidades")
st.markdown(
    "Use as ferramentas abaixo para **criar planos de aula** alinhados à BNCC "
    "ou para **descobrir quais habilidades** uma atividade desenvolve."
)
st.divider()

tab1, tab2 = st.tabs(["📋 Criar Plano de Aula", "🔍 Verificar Habilidades da BNCC"])

# ---------------------------------------------------------------------------
# Aba 1 — Gerador de Plano de Aula
# ---------------------------------------------------------------------------

with tab1:
    st.subheader("Criar Plano de Aula")
    st.markdown(
        "Preencha os campos abaixo e receba um plano de aula completo, "
        "pronto para usar em sala — com objetivos, atividades, recursos e avaliação, "
        "alinhado à BNCC e ao PCN."
    )

    col1, col2 = st.columns(2)

    with col1:
        componente = st.selectbox(
            "Disciplina",
            [
                "Língua Portuguesa",
                "Matemática",
                "Ciências",
                "História",
                "Geografia",
                "Arte",
                "Educação Física",
                "Língua Estrangeira",
                "Ensino Religioso",
            ],
        )
        ano = st.selectbox(
            "Ano escolar",
            [
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
            ],
        )

    with col2:
        habilidade = st.text_area(
            "Tema ou habilidade que deseja trabalhar",
            placeholder=(
                "Exemplos:\n"
                "• Produção de texto coletivo sobre animais\n"
                "• Adição e subtração com reagrupamento\n"
                "• EF02MA01 — comparar e ordenar números até 1000\n"
                "• Leitura e interpretação de texto literário"
            ),
            height=120,
        )
        duracao = st.slider("Quantidade de aulas", 1, 5, 1)

    if st.button("Criar plano de aula", type="primary", use_container_width=True):
        if not habilidade.strip():
            st.warning("Informe o tema ou a habilidade que deseja trabalhar.")
        else:
            with st.spinner("Criando seu plano de aula com base nos documentos do MEC..."):
                result = generate_lesson_plan(componente, habilidade, ano, duracao)

            if result["success"]:
                st.success("Plano criado com sucesso! Confira abaixo e faça o download se quiser.")
            else:
                st.info(
                    "Plano gerado! Alguns detalhes podem precisar de ajuste "
                    "— revise antes de usar em sala."
                )

            st.markdown(result["lesson_plan"])

            col_dl, col_src = st.columns([1, 3])
            with col_dl:
                st.download_button(
                    "⬇️ Baixar plano (.md)",
                    data=result["lesson_plan"],
                    file_name=f"plano_{componente.lower().replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            with st.expander("Ver trechos dos documentos utilizados como base"):
                for src in result.get("sources", []):
                    meta = src.get("metadata", {})
                    nome = meta.get("source", meta.get("source_file", "Documento"))
                    st.markdown(f"**{nome}**")
                    st.markdown(f"> {src['content'][:250]}...")
                    st.divider()

# ---------------------------------------------------------------------------
# Aba 2 — Verificador de Habilidades BNCC
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Descobrir quais habilidades da BNCC uma atividade desenvolve")
    st.markdown(
        "Descreva uma atividade que você já faz ou planeja fazer. "
        "O assistente identifica **quais habilidades da BNCC** ela trabalha "
        "e explica o motivo."
    )

    col1, col2 = st.columns(2)
    with col1:
        componente_check = st.selectbox(
            "Disciplina",
            [
                "Língua Portuguesa",
                "Matemática",
                "Ciências",
                "História",
                "Geografia",
                "Arte",
                "Educação Física",
                "Língua Estrangeira",
                "Ensino Religioso",
            ],
            key="check_componente",
        )
        ano_check = st.selectbox(
            "Ano escolar",
            [
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
            ],
            key="check_ano",
        )

    with col2:
        descricao = st.text_area(
            "Descreva a atividade",
            placeholder=(
                "Exemplo: Os alunos vão ouvir a leitura de um conto, "
                "depois desenhar a sequência de eventos e recontar a história "
                "em voz alta para os colegas."
            ),
            height=150,
            key="check_descricao",
        )

    if st.button("Verificar habilidades da BNCC", type="primary", use_container_width=True):
        if not descricao.strip():
            st.warning("Descreva a atividade para verificar o alinhamento.")
        else:
            with st.spinner("Buscando as habilidades da BNCC relacionadas..."):
                result = check_bncc_alignment(descricao, componente_check, ano_check)

            alinhamento = result.get("alinhamento", "baixo")
            if alinhamento == "alto":
                st.success("Esta atividade tem **alto alinhamento** com a BNCC.")
            elif alinhamento == "médio":
                st.warning("Esta atividade tem **alinhamento médio** com a BNCC.")
            else:
                st.info("Esta atividade tem **baixo alinhamento** com a BNCC — considere ajustá-la.")

            habilidades = result.get("habilidades", [])
            if habilidades:
                st.subheader(f"{len(habilidades)} habilidade(s) identificada(s)")
                for h in habilidades:
                    with st.expander(f"**{h.get('codigo', '?')}** — {h.get('descricao', '')}"):
                        st.markdown(f"**Por que esta atividade desenvolve essa habilidade:**")
                        st.markdown(h.get("justificativa", ""))
            else:
                st.info("Não foram identificadas habilidades BNCC específicas para esta atividade.")

            competencias = result.get("competencias_gerais", [])
            if competencias:
                st.subheader("Competências Gerais relacionadas")
                for c in competencias:
                    st.markdown(f"- {c}")

            if obs := result.get("observacoes"):
                st.info(obs)

            with st.expander("Ver trechos dos documentos consultados"):
                for src in result.get("sources", []):
                    meta = src.get("metadata", {})
                    nome = meta.get("source", meta.get("source_file", "Documento"))
                    st.markdown(f"**{nome}**")
                    st.markdown(f"> {src['content'][:250]}...")
                    st.divider()
