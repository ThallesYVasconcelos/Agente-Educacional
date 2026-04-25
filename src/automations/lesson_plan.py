"""
Automação A1 — Gerador de Plano de Aula.

Focado nos Anos Iniciais do Ensino Fundamental (1º ao 4º ano).

Input:
  - componente_curricular : ex. "Matemática", "Língua Portuguesa"
  - habilidade_bncc       : ex. "EF01MA01" ou descrição livre
  - ano_escolar           : "1º ano", "2º ano", "3º ano" ou "4º ano" do EF
  - duracao_aulas         : número de aulas (1–5)

Output:
  Markdown com plano de aula estruturado e ≥2 citações da BNCC/PCN.

Critério de sucesso:
  - Todas as seções obrigatórias presentes
  - ≥2 citações normativas (BNCC ou PCN)
  - Gerado em < 60 segundos
"""

import re
import time
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from src.rag.vectorstore import similarity_search
from src.utils.helpers import get_llm
from src.utils.logger import get_logger


def _strip_code_fences(text: str) -> str:
    """Remove blocos ```markdown``` ou ``` que LLMs às vezes inserem no output."""
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def _fix_latex(text: str) -> str:
    """Converte notação LaTeX residual em texto legível."""
    sup_map = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
               "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
               "n": "ⁿ", "m": "ᵐ"}

    def latex_to_text(expr: str) -> str:
        expr = expr.strip()
        expr = expr.replace(r"\times", "×").replace(r"\div", "÷")
        expr = expr.replace(r"\cdot", "×").replace(r"\sqrt", "√")
        expr = expr.replace(r"\neq", "≠").replace(r"\leq", "≤").replace(r"\geq", "≥")
        def replace_pow(m: re.Match) -> str:
            sup = "".join(sup_map.get(c, c) for c in m.group(2).strip("{}"))
            return f"{m.group(1)}{sup}"
        expr = re.sub(r"([a-zA-Z0-9])\^\{?([^}^\s]+)\}?", replace_pow, expr)
        expr = expr.replace("{", "").replace("}", "")
        expr = re.sub(r"\\([a-zA-Z]+)", r"\1", expr)
        return expr

    text = re.sub(r"\\\((.+?)\\\)", lambda m: latex_to_text(m.group(1)), text)
    text = re.sub(r"\$(.+?)\$", lambda m: latex_to_text(m.group(1)), text)
    text = re.sub(r"\\\[(.+?)\\\]", lambda m: latex_to_text(m.group(1)), text, flags=re.DOTALL)
    return text

logger = get_logger(__name__)

REQUIRED_SECTIONS = [
    "Objetivos",
    "Habilidades BNCC",
    "Recursos",
    "Sequência de Atividades",
    "Avaliação",
]

LESSON_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em didática e currículo da Educação Básica brasileira.
Com base nos trechos da BNCC e PCN fornecidos, gere um plano de aula completo em Markdown.

O plano DEVE conter exatamente estas seções (com esses títulos):
## Objetivos
## Habilidades BNCC
## Recursos
## Sequência de Atividades
## Avaliação

Regras obrigatórias:
1. Cite pelo menos 2 referências normativas no formato: (BNCC, p. XX) ou (PCN [Componente], p. XX)
2. As habilidades BNCC devem usar o código oficial (ex.: EF01MA01, EF06CI05)
3. A sequência de atividades deve ter no mínimo 3 momentos: abertura, desenvolvimento e fechamento
4. Adapte a linguagem, os recursos e as atividades à faixa etária e ao ano escolar informados
5. Escreva em português claro e acessível — como um professor experiente escreveria para outro professor
6. NÃO use notação LaTeX (\\times, \\frac, $...$, \\(...\\)). Para operações matemáticas, escreva em texto:
   - Use × (ou "vezes"), ÷ (ou "dividido por"), use ² ³ ⁴ para potências
   - Ex.: "3² = 3 × 3 = 9" em vez de "3^{{2}} = 9"

Trechos normativos disponíveis:
{context}
"""),
    ("human", """Componente curricular: {componente}
Habilidade / Tema: {habilidade}
Ano escolar: {ano}
Duração: {duracao} aula(s)

Gere o plano de aula completo em linguagem clara, sem notação LaTeX."""),
])


def generate_lesson_plan(
    componente_curricular: str,
    habilidade_bncc: str,
    ano_escolar: str,
    duracao_aulas: int = 1,
) -> dict:
    """
    Gera um plano de aula com base na BNCC e PCN.

    Returns:
        dict com 'lesson_plan' (markdown), 'citations_count',
        'sections_present', 'elapsed_seconds', 'success'
    """
    start = time.time()

    # Duas buscas complementares para trazer trechos mais relevantes
    query_hab = (
        f"habilidades BNCC {componente_curricular} {habilidade_bncc} {ano_escolar} EF"
    )
    query_ped = (
        f"{habilidade_bncc} {componente_curricular} {ano_escolar} "
        "ensino aprendizagem objetivos atividades"
    )
    docs_hab = similarity_search(query_hab, k=5)
    docs_ped = similarity_search(query_ped, k=4)

    # Junta, deduplica e filtra trechos estruturais genéricos
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
        "Currículos: BNCC e itinerários",
        "itinerários formativos",
        "Parecer CNE/CEB",
    ]
    docs = [d for d in docs if not any(p in d.page_content for p in _SKIP_PHRASES)][:8]

    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('source', 'Fonte')}] {d.page_content}"
        for d in docs
    )

    llm = get_llm(temperature=0.2)
    chain = LESSON_PLAN_PROMPT | llm

    response = chain.invoke({
        "componente": componente_curricular,
        "habilidade": habilidade_bncc,
        "ano": ano_escolar,
        "duracao": duracao_aulas,
        "context": context,
    })
    plan_text: str = _fix_latex(_strip_code_fences(response.content))

    citations = sum(1 for ref in ["BNCC", "PCN", "PNLD", "Diretrizes"] if ref in plan_text)
    sections_present = [s for s in REQUIRED_SECTIONS if s in plan_text]
    elapsed = round(time.time() - start, 2)
    success = citations >= 2 and len(sections_present) == len(REQUIRED_SECTIONS) and elapsed < 60

    logger.info(
        "lesson_plan_generated",
        componente=componente_curricular,
        citations=citations,
        sections=len(sections_present),
        elapsed=elapsed,
        success=success,
    )

    return {
        "lesson_plan": plan_text,
        "citations_count": citations,
        "sections_present": sections_present,
        "elapsed_seconds": elapsed,
        "success": success,
        "sources": [{"content": d.page_content[:300], "metadata": d.metadata} for d in docs],
    }
