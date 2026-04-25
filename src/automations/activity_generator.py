"""
Automação A4 — Gerador de Atividades com Auto-Validação.

Gera listas de atividades (exercícios, situações-problema, fixação) para o professor,
com gabarito separado. Usa uma estratégia de dois passos para confiabilidade:

  Passo 1 — Geração: LLM cria as atividades respeitando o escopo curricular.
  Passo 2 — Validação: segundo LLM verifica cada resposta e corrige se necessário.

Saída:
  - Versão do ALUNO: atividades sem gabarito (PDF/DOCX)
  - Versão do PROFESSOR: atividades + gabarito detalhado + habilidade BNCC por questão
"""

import json
import re
import time
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from src.rag.vectorstore import similarity_search
from src.utils.helpers import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Utilitários de texto (espelhados de content_generator para evitar
# importação de símbolos privados que causam ImportError no deploy)
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Remove blocos ```markdown``` ou ``` que LLMs às vezes inserem no output."""
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def _latex_to_text(expr: str) -> str:
    expr = expr.strip()
    expr = expr.replace(r"\times", "×").replace(r"\div", "÷")
    expr = expr.replace(r"\cdot", "×").replace(r"\sqrt", "√")
    expr = expr.replace(r"\neq", "≠").replace(r"\leq", "≤").replace(r"\geq", "≥")
    expr = expr.replace(r"\pm", "±").replace(r"\frac", "/")
    sup_map = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
               "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
               "n": "ⁿ", "m": "ᵐ"}
    def _replace_pow(m: re.Match) -> str:
        sup = "".join(sup_map.get(c, c) for c in m.group(2).strip("{}"))
        return f"{m.group(1)}{sup}"
    expr = re.sub(r"([a-zA-Z0-9])\^\{?([^}^\s]+)\}?", _replace_pow, expr)
    expr = expr.replace("{", "").replace("}", "")
    expr = re.sub(r"\\([a-zA-Z]+)", r"\1", expr)
    return expr


def _fix_latex(text: str) -> str:
    """Converte notação LaTeX residual em texto legível."""
    text = re.sub(r"\\\((.+?)\\\)", lambda m: _latex_to_text(m.group(1)), text)
    text = re.sub(r"\$(.+?)\$", lambda m: _latex_to_text(m.group(1)), text)
    text = re.sub(r"\\\[(.+?)\\\]", lambda m: _latex_to_text(m.group(1)), text, flags=re.DOTALL)
    return text


# ---------------------------------------------------------------------------
# Escopo curricular (importado do módulo público)
# ---------------------------------------------------------------------------

from src.automations.content_generator import CURRICULUM_SCOPE  # noqa: E402

_DEFAULT_SCOPE = (
    "Siga rigorosamente a progressão curricular da BNCC e PCN para o ano escolar informado. "
    "Use apenas conceitos e complexidade adequados à série. "
    "Não antecipe conteúdos de anos superiores."
)

# ---------------------------------------------------------------------------
# Tipos de atividade disponíveis
# ---------------------------------------------------------------------------

ACTIVITY_TYPES = {
    "exercicios": "Exercícios objetivos (cálculo, resposta direta)",
    "fixacao": "Fixação com resolução passo a passo",
    "situacao": "Situações-problema / problemas contextualizados",
    "misto": "Misto: exercícios objetivos + situações-problema",
}

# ---------------------------------------------------------------------------
# Prompt de Geração
# ---------------------------------------------------------------------------

_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um professor especialista em elaboração de atividades pedagógicas
para a Educação Básica brasileira. Você cria atividades precisas, claras e adequadas à faixa etária.

⚠️ ESCOPO CURRICULAR OBRIGATÓRIO para este ano e disciplina:
{escopo_curricular}

Respeite rigorosamente este escopo: não use conceitos de anos superiores.

⚠️ REGRAS DE FORMATAÇÃO:
- Escreva em português claro e acessível
- NÃO use notação LaTeX (\\times, $...$, \\(...\\)). Use × ÷ ² ³ em vez disso.
- Cada questão deve ter: enunciado, alternativas (se aplicável), resposta correta e habilidade BNCC
- Numere as questões: Questão 1, Questão 2, etc.

Tipo de atividade a gerar: {tipo_descricao}

Quantidade: {quantidade} questões

Estruture EXATAMENTE neste formato JSON (sem markdown ao redor):
{{
  "titulo": "Título da lista de atividades",
  "disciplina": "{componente}",
  "ano": "{ano}",
  "topico": "{topico}",
  "habilidades_gerais": ["EF06MA07", ...],
  "questoes": [
    {{
      "numero": 1,
      "tipo": "calculo" | "multipla_escolha" | "situacao_problema" | "verdadeiro_falso",
      "enunciado": "Texto da questão para o aluno",
      "alternativas": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "resposta_correta": "Resposta completa e explicada para o professor",
      "resolucao_passo_a_passo": "Passo 1: ... Passo 2: ... Resultado: ...",
      "habilidade_bncc": "EF06MA07",
      "nivel": "facil" | "medio" | "desafiador"
    }}
  ]
}}

Use alternativas APENAS para questões de múltipla escolha — nos demais tipos, deixe "alternativas": [].
"""),
    ("human", """Disciplina: {componente}
Ano escolar: {ano}
Tópico / Conteúdo: {topico}
Tipo de atividade: {tipo_descricao}
Quantidade de questões: {quantidade}

Contexto dos documentos curriculares (BNCC/PCN):
{context}

Gere as {quantidade} questões em JSON válido, sem markdown ao redor."""),
])

# ---------------------------------------------------------------------------
# Prompt de Validação (segundo passo)
# ---------------------------------------------------------------------------

_VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em matemática e didática da Educação Básica.
Sua tarefa é VERIFICAR e CORRIGIR uma lista de atividades gerada por IA.

Para cada questão, verifique:
1. A resposta está MATEMATICAMENTE ou CONCEITUALMENTE correta?
2. O nível de dificuldade está adequado ao ano escolar?
3. O conteúdo está dentro do escopo curricular do ano?
4. A habilidade BNCC citada existe e é adequada?

Escopo curricular do ano:
{escopo_curricular}

Retorne o JSON corrigido no MESMO formato, com um campo extra por questão:
  "validacao": "ok" | "corrigido"
  "nota_validacao": "O que foi corrigido (se aplicável)"

Retorne APENAS o JSON, sem texto adicional nem markdown.
"""),
    ("human", "Verifique e corrija este JSON de atividades:\n\n{atividades_json}"),
])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_safely(text: str) -> Optional[dict]:
    """Tenta extrair e parsear JSON do output do LLM."""
    text = _strip_code_fences(text).strip()
    # Tenta o texto completo
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Tenta encontrar o primeiro bloco { ... }
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _format_student_version(data: dict) -> str:
    """Formata a versão do aluno (sem gabarito) em Markdown."""
    lines = [
        f"# {data.get('titulo', 'Lista de Atividades')}",
        f"**Disciplina:** {data.get('disciplina', '')}  |  "
        f"**Ano:** {data.get('ano', '')}  |  "
        f"**Tópico:** {data.get('topico', '')}",
        "",
        "---",
        "",
    ]
    for q in data.get("questoes", []):
        lines.append(f"**Questão {q['numero']}** "
                     f"{'🟢' if q.get('nivel') == 'facil' else '🟡' if q.get('nivel') == 'medio' else '🔴'}")
        lines.append("")
        lines.append(q.get("enunciado", ""))
        alts = q.get("alternativas", [])
        if alts:
            lines.append("")
            for alt in alts:
                lines.append(alt)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _format_teacher_version(data: dict) -> str:
    """Formata a versão do professor (com gabarito completo) em Markdown."""
    lines = [
        f"# {data.get('titulo', 'Lista de Atividades')} — GABARITO DO PROFESSOR",
        f"**Disciplina:** {data.get('disciplina', '')}  |  "
        f"**Ano:** {data.get('ano', '')}  |  "
        f"**Tópico:** {data.get('topico', '')}",
        "",
        f"**Habilidades BNCC contempladas:** "
        f"{', '.join(data.get('habilidades_gerais', []))}",
        "",
        "---",
        "",
    ]
    for q in data.get("questoes", []):
        nivel_icon = {"facil": "🟢 Fácil", "medio": "🟡 Médio", "desafiador": "🔴 Desafiador"}.get(
            q.get("nivel", "medio"), "🟡 Médio"
        )
        validacao = q.get("validacao", "ok")
        validacao_icon = "✅" if validacao == "ok" else "🔧 Corrigido"

        lines.append(f"**Questão {q['numero']}** — {nivel_icon} | {validacao_icon}")
        lines.append(f"*Habilidade BNCC: {q.get('habilidade_bncc', '')}*")
        lines.append("")
        lines.append(q.get("enunciado", ""))
        alts = q.get("alternativas", [])
        if alts:
            lines.append("")
            for alt in alts:
                lines.append(alt)
        lines.append("")
        lines.append(f"**✅ Resposta:** {q.get('resposta_correta', '')}")
        resolucao = q.get("resolucao_passo_a_passo", "")
        if resolucao:
            lines.append("")
            lines.append(f"**📋 Resolução:**")
            lines.append(resolucao)
        nota = q.get("nota_validacao", "")
        if nota and validacao == "corrigido":
            lines.append("")
            lines.append(f"*🔧 Nota de correção: {nota}*")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def generate_activities(
    topico: str,
    componente: str,
    ano_escolar: str,
    tipo: str = "misto",
    quantidade: int = 8,
) -> dict:
    """
    Gera lista de atividades com auto-validação em dois passos.

    Returns:
        dict com:
          - 'student_md'   : Markdown versão aluno (sem gabarito)
          - 'teacher_md'   : Markdown versão professor (com gabarito)
          - 'data'         : JSON estruturado das questões
          - 'validated'    : bool — se a validação foi bem-sucedida
          - 'corrections'  : número de questões corrigidas
          - 'elapsed_seconds'
          - 'success'
    """
    start = time.time()

    escopo = (
        CURRICULUM_SCOPE
        .get(componente, {})
        .get(ano_escolar, _DEFAULT_SCOPE)
    )

    tipo_descricao = ACTIVITY_TYPES.get(tipo, ACTIVITY_TYPES["misto"])

    # Busca trechos de documentos curriculares relevantes
    query_hab = f"habilidades BNCC {componente} {topico} {ano_escolar} EF"
    query_ped = f"{topico} {componente} {ano_escolar} atividades exercícios"
    docs_hab = similarity_search(query_hab, k=4)
    docs_ped = similarity_search(query_ped, k=3)

    seen: set[str] = set()
    docs = []
    for d in docs_hab + docs_ped:
        key = d.page_content[:120]
        if key not in seen:
            seen.add(key)
            docs.append(d)

    _SKIP_PHRASES = [
        "está organizado em cinco áreas",
        "competência específica à qual cada habilidade",
        "recentes mudanças na LDB",
        "itinerários formativos",
        "Parecer CNE/CEB",
    ]
    docs = [d for d in docs if not any(p in d.page_content for p in _SKIP_PHRASES)][:6]

    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('source', 'Fonte')}] {d.page_content}"
        for d in docs
    ) or "Use o escopo curricular acima como referência principal."

    llm = get_llm(temperature=0.4)

    # ── Passo 1: Geração ──────────────────────────────────────────────────
    logger.info("activity_generation_start", topico=topico, componente=componente, ano=ano_escolar)
    gen_chain = _GENERATION_PROMPT | llm
    gen_response = gen_chain.invoke({
        "topico": topico,
        "componente": componente,
        "ano": ano_escolar,
        "escopo_curricular": escopo,
        "tipo_descricao": tipo_descricao,
        "quantidade": quantidade,
        "context": context,
    })

    raw_gen = _fix_latex(_strip_code_fences(gen_response.content))
    data = _parse_json_safely(raw_gen)

    if not data or not data.get("questoes"):
        elapsed = round(time.time() - start, 2)
        logger.error("activity_generation_failed", elapsed=elapsed)
        return {
            "student_md": "",
            "teacher_md": "",
            "data": None,
            "validated": False,
            "corrections": 0,
            "elapsed_seconds": elapsed,
            "success": False,
            "error": "Não foi possível gerar as atividades. Tente reformular o tópico.",
            "sources": [],
        }

    # ── Passo 2: Validação ────────────────────────────────────────────────
    logger.info("activity_validation_start", questoes=len(data.get("questoes", [])))
    val_llm = get_llm(temperature=0.1)
    val_chain = _VALIDATION_PROMPT | val_llm
    val_response = val_chain.invoke({
        "escopo_curricular": escopo,
        "atividades_json": json.dumps(data, ensure_ascii=False, indent=2),
    })

    raw_val = _fix_latex(_strip_code_fences(val_response.content))
    validated_data = _parse_json_safely(raw_val)

    # Se a validação falhou no parse, usa os dados originais
    if not validated_data or not validated_data.get("questoes"):
        validated_data = data
        validated = False
        corrections = 0
    else:
        validated = True
        corrections = sum(
            1 for q in validated_data.get("questoes", [])
            if q.get("validacao") == "corrigido"
        )

    elapsed = round(time.time() - start, 2)
    success = bool(validated_data.get("questoes"))

    logger.info(
        "activity_generation_complete",
        validated=validated,
        corrections=corrections,
        elapsed=elapsed,
        success=success,
    )

    return {
        "student_md": _format_student_version(validated_data),
        "teacher_md": _format_teacher_version(validated_data),
        "data": validated_data,
        "validated": validated,
        "corrections": corrections,
        "elapsed_seconds": elapsed,
        "success": success,
        "sources": [
            {"content": d.page_content[:300], "metadata": d.metadata}
            for d in docs
        ],
    }
