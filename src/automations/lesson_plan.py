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

logger = get_logger(__name__)

REQUIRED_SECTIONS = [
    "Objetivos",
    "Habilidades BNCC",
    "Recursos",
    "Sequência de Atividades",
    "Avaliação",
]

LESSON_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em didática e currículo dos Anos Iniciais do Ensino Fundamental (1º ao 4º ano) brasileiro.
Com base nos trechos da BNCC e PCN fornecidos, gere um plano de aula completo em Markdown.

O plano DEVE conter exatamente estas seções (com esses títulos):
## Objetivos
## Habilidades BNCC
## Recursos
## Sequência de Atividades
## Avaliação

Regras obrigatórias:
1. Cite pelo menos 2 referências normativas no formato: (BNCC, p. XX) ou (PCN [Componente], p. XX)
2. As habilidades BNCC devem usar o código oficial para os anos iniciais (EF01 a EF04), ex.: EF01MA01
3. A sequência de atividades deve ter no mínimo 3 momentos (abertura, desenvolvimento, fechamento)
4. Adapte a linguagem, os recursos e as atividades à faixa etária dos anos iniciais (6–10 anos)
5. Adeque o plano ao ano escolar (1º a 4º) e à duração informados

Trechos normativos disponíveis:
{context}
"""),
    ("human", """Componente curricular: {componente}
Habilidade / Tema: {habilidade}
Ano escolar: {ano}
Duração: {duracao} aula(s)

Gere o plano de aula completo."""),
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

    query = (
        f"{componente_curricular} {habilidade_bncc} {ano_escolar} "
        "habilidades competências objetivos aprendizagem"
    )
    docs = similarity_search(query, k=8)
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
    plan_text: str = _strip_code_fences(response.content)

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
