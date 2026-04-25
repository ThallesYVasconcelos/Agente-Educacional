"""Gerador de Atividades — página do professor."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.automations.activity_generator import ACTIVITY_TYPES, generate_activities
from src.automations.content_generator import CURRICULUM_SCOPE
from src.utils.pdf_export import markdown_to_pdf
from src.utils.docx_export import markdown_to_docx

st.set_page_config(page_title="Gerador de Atividades", page_icon="✏️", layout="wide")

PAGE_CSS = """
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 900px;
    }
    .page-header {
        background: linear-gradient(135deg, #0A7B3E 0%, #15C262 100%);
        color: #ffffff;
        padding: 2rem 2.2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 12px 30px -12px rgba(10, 123, 62, 0.35);
    }
    .page-header h1 {
        margin: 0 0 0.4rem 0;
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .page-header p {
        margin: 0;
        font-size: 1rem;
        opacity: 0.92;
        line-height: 1.55;
        max-width: 680px;
    }
    .form-card {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 16px;
        padding: 1.8rem 2rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .form-card h4 {
        margin: 0 0 1.2rem 0;
        font-size: 1rem;
        font-weight: 700;
        color: #1A1F36;
        letter-spacing: -0.01em;
    }
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        margin-bottom: 1rem;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        border-radius: 20px;
        padding: 0.28rem 0.9rem;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-green  { background:#E6F9EE; color:#0A7B3E; border:1px solid #A8E6C0; }
    .badge-yellow { background:#FFF4DA; color:#8A5A00; border:1px solid #F5D87A; }
    .badge-red    { background:#FFE6E6; color:#B00020; border:1px solid #FFB3B3; }
    .badge-gray   { background:#F4F5F7; color:#5A6378; border:1px solid #D8DCE8; }
    .result-header {
        display: flex;
        align-items: baseline;
        gap: 1rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    .result-header h3 { margin: 0; font-size: 1.1rem; color: #1A1F36; }
    .source-card {
        background: #FAFBFF;
        border-left: 3px solid #0A7B3E;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.7rem;
    }
    .source-card .source-title {
        font-weight: 700;
        color: #1A1F36;
        font-size: 0.88rem;
        margin-bottom: 0.3rem;
    }
    .source-card .source-text {
        color: #5A6378;
        font-size: 0.85rem;
        line-height: 1.5;
        font-style: italic;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 12px 12px 0 0;
        padding: 0.55rem 1.1rem;
        font-weight: 600;
        font-size: 0.92rem;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0A7B3E 0%, #15C262 100%);
        color: #ffffff !important;
        border-color: transparent;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: #ffffff;
        border: 1px solid #E6EAF5;
        border-radius: 0 14px 14px 14px;
        padding: 1.6rem;
        margin-top: -1px;
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #0A7B3E 0%, #15C262 100%);
        border: none;
        border-radius: 10px;
        font-weight: 600;
        box-shadow: 0 4px 14px rgba(10, 123, 62, 0.3);
    }
    div[data-testid="stNumberInput"] { max-width: 160px; }
</style>
"""

st.markdown(PAGE_CSS, unsafe_allow_html=True)

# ── Session state — persiste o último resultado durante a sessão ────────────
if "ativ_result" not in st.session_state:
    st.session_state.ativ_result = None
if "ativ_meta" not in st.session_state:
    st.session_state.ativ_meta = {}

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>✏️ Gerador de Atividades</h1>
        <p>Monte listas de exercícios com gabarito em segundos —
        dentro do escopo curricular da série, com verificação automática de qualidade.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar compacta ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Como funciona")
    st.markdown(
        """
        1. **Geração** — atividades explicitamente sobre o tópico, respeitando o escopo da série
        2. **Verificação de escopo** — detecta termos fora do ano automaticamente
        3. **Validação de respostas** — segundo agente confere cada gabarito

        **Dificuldade:**
        🟢 Fácil · 🟡 Médio · 🔴 Desafiador

        **Gabarito:**
        ✅ Validado · 🔧 Corrigido
        """
    )
    # Histórico da sessão
    if st.session_state.ativ_meta:
        st.divider()
        st.markdown("### Última lista gerada")
        m = st.session_state.ativ_meta
        st.caption(
            f"**{m.get('topico','')}** · {m.get('componente','')} · {m.get('ano','')}\n\n"
            f"{m.get('quantidade','')} questões · {m.get('tipo','')}"
        )
        if st.button("🗑 Limpar resultado", use_container_width=True):
            st.session_state.ativ_result = None
            st.session_state.ativ_meta = {}
            st.rerun()

# ── Listas ─────────────────────────────────────────────────────────────────
ANOS = [
    "1º ano do Ensino Fundamental", "2º ano do Ensino Fundamental",
    "3º ano do Ensino Fundamental", "4º ano do Ensino Fundamental",
    "5º ano do Ensino Fundamental", "6º ano do Ensino Fundamental",
    "7º ano do Ensino Fundamental", "8º ano do Ensino Fundamental",
    "9º ano do Ensino Fundamental",
    "1º ano do Ensino Médio", "2º ano do Ensino Médio", "3º ano do Ensino Médio",
]

DISCIPLINAS = sorted(set(
    list(CURRICULUM_SCOPE.keys()) +
    ["Arte", "Educação Física", "Ensino Religioso", "Língua Estrangeira (Inglês)"]
))

# ── Formulário em card único ───────────────────────────────────────────────
st.markdown('<div class="form-card"><h4>Configure a lista de atividades</h4>', unsafe_allow_html=True)

topico = st.text_input(
    "Tópico / Conteúdo",
    placeholder="Ex: Potenciação, Células, Revolução Industrial, Interpretação de texto…",
    label_visibility="visible",
)

col_disc, col_ano = st.columns(2)
with col_disc:
    componente = st.selectbox("Disciplina", DISCIPLINAS)
with col_ano:
    ano = st.selectbox("Ano escolar", ANOS, index=5)

col_tipo, col_qtd = st.columns([3, 1])
with col_tipo:
    tipo = st.selectbox(
        "Tipo de atividade",
        options=list(ACTIVITY_TYPES.keys()),
        format_func=lambda k: ACTIVITY_TYPES[k],
        index=3,
    )
with col_qtd:
    quantidade = st.number_input("Questões", min_value=3, max_value=10, value=6, step=1)

# Escopo curricular — discreto, dentro do card
escopo_atual = CURRICULUM_SCOPE.get(componente, {}).get(ano, "")
if escopo_atual:
    with st.expander("Ver escopo curricular deste ano"):
        st.caption(escopo_atual)

st.markdown("</div>", unsafe_allow_html=True)

gerar = st.button("✏️ Gerar atividades", type="primary", use_container_width=True)

# ── Geração ────────────────────────────────────────────────────────────────
if gerar:
    if not topico.strip():
        st.warning("Informe o tópico antes de gerar.")
        st.stop()

    with st.spinner("Gerando e validando as atividades… pode levar até 1 minuto."):
        result = generate_activities(
            topico=topico.strip(),
            componente=componente,
            ano_escolar=ano,
            tipo=tipo,
            quantidade=int(quantidade),
        )

    if not result["success"]:
        st.error(result.get("error", "Erro ao gerar. Tente reformular o tópico."))
        st.stop()

    # Salva no session_state para persistir durante a sessão
    st.session_state.ativ_result = result
    st.session_state.ativ_meta = {
        "topico": topico.strip(),
        "componente": componente,
        "ano": ano,
        "tipo": ACTIVITY_TYPES.get(tipo, tipo),
        "quantidade": int(quantidade),
    }

# ── Exibe resultado (do state — persiste após rerun) ───────────────────────
if st.session_state.ativ_result:
    result = st.session_state.ativ_result
    meta = st.session_state.ativ_meta

    # Cabeçalho do resultado
    st.markdown(
        f'<div style="margin:1.2rem 0 0.4rem 0;color:#5A6378;font-size:0.9rem;">'
        f'📋 <strong>{meta.get("topico","")}</strong> · '
        f'{meta.get("componente","")} · {meta.get("ano","")} · '
        f'{meta.get("quantidade","")} questões</div>',
        unsafe_allow_html=True,
    )

    # ── Badges de status ──────────────────────────────────────────────────
    chk = result.get("check_result")
    badges = []

    if chk:
        if chk.scope_ok:
            badges.append('<span class="badge badge-green">✅ Escopo verificado</span>')
        else:
            badges.append('<span class="badge badge-yellow">⚠️ Revisar escopo</span>')

    if result["validated"]:
        badges.append('<span class="badge badge-green">✅ Respostas validadas</span>')
    if result["corrections"] > 0:
        badges.append(
            f'<span class="badge badge-yellow">🔧 {result["corrections"]} corrigida(s)</span>'
        )

    badges.append(f'<span class="badge badge-gray">⏱ {result["elapsed_seconds"]}s</span>')

    st.markdown(
        f'<div class="badge-row">{"".join(badges)}</div>',
        unsafe_allow_html=True,
    )

    if chk and not chk.scope_ok and chk.violations:
        st.caption(f"⚠️ Termos monitorados: {', '.join(chk.violations)}")

    # ── Abas aluno / professor ────────────────────────────────────────────
    _t = meta.get("topico", "atividades")
    _c = meta.get("componente", "")
    _a = meta.get("ano", "")
    _slug = _t[:25].replace(" ", "_")

    tab_aluno, tab_prof = st.tabs(["👧 Versão do Aluno", "👩‍🏫 Gabarito do Professor"])

    with tab_aluno:
        st.caption("🟢 Fácil · 🟡 Médio · 🔴 Desafiador")
        st.markdown(result["student_md"])
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Baixar PDF",
                data=markdown_to_pdf(
                    result["student_md"],
                    title=f"Atividades — {_c} ({_a}) | {_t}",
                ),
                file_name=f"atividades_{_slug}_aluno.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_b:
            st.download_button(
                "⬇️ Baixar Word",
                data=markdown_to_docx(
                    result["student_md"],
                    title=f"Atividades — {_c} ({_a}) | {_t}",
                ),
                file_name=f"atividades_{_slug}_aluno.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    with tab_prof:
        st.caption("🟢 Fácil · 🟡 Médio · 🔴 Desafiador · ✅ Validado · 🔧 Corrigido")
        st.markdown(result["teacher_md"])
        st.divider()
        col_c, col_d = st.columns(2)
        with col_c:
            st.download_button(
                "⬇️ Baixar PDF (com gabarito)",
                data=markdown_to_pdf(
                    result["teacher_md"],
                    title=f"Gabarito — {_c} ({_a}) | USO DO PROFESSOR",
                ),
                file_name=f"gabarito_{_slug}_professor.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_d:
            st.download_button(
                "⬇️ Baixar Word (com gabarito)",
                data=markdown_to_docx(
                    result["teacher_md"],
                    title=f"Gabarito — {_c} ({_a}) | USO DO PROFESSOR",
                ),
                file_name=f"gabarito_{_slug}_professor.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    # ── Fontes consultadas ────────────────────────────────────────────────
    sources = result.get("sources", [])
    if sources:
        with st.expander("📄 Documentos curriculares consultados"):
            for src in sources:
                doc_name = src["metadata"].get("source", "Documento")
                st.markdown(
                    f'<div class="source-card">'
                    f'<div class="source-title">{doc_name}</div>'
                    f'<div class="source-text">{src["content"][:350]}…</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
