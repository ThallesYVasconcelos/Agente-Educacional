"""
Automação A2 — Verificador de Alinhamento com Habilidades BNCC.

Input:
  - descricao_atividade : descrição de uma atividade ou conteúdo de aula
  - componente          : componente curricular (ex. "Matemática")
  - ano_escolar         : ex. "3º ano do Ensino Fundamental"

Output:
  - habilidades identificadas (códigos BNCC + justificativa)
  - competências gerais relacionadas
  - nível de alinhamento (alto / médio / baixo)

Critério de sucesso:
  - ≥1 habilidade BNCC identificada com código válido
  - Justificativa presente para cada habilidade
"""

import json
import time
from typing import Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.rag.vectorstore import similarity_search
from src.utils.helpers import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)

BNCC_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em BNCC (Base Nacional Comum Curricular) para os Anos Iniciais do Ensino Fundamental (1º ao 4º ano).
Analise a descrição da atividade fornecida e identifique as habilidades da BNCC que ela desenvolve.

Baseie-se nos trechos normativos fornecidos para embasar sua análise.
Considere apenas habilidades dos anos iniciais: códigos EF01, EF02, EF03 e EF04.

Responda EXCLUSIVAMENTE com JSON no formato:
{{
  "habilidades": [
    {{
      "codigo": "EF0XYYЗЗ",
      "descricao": "Descrição resumida da habilidade",
      "justificativa": "Por que esta atividade desenvolve essa habilidade"
    }}
  ],
  "competencias_gerais": ["número e título"],
  "alinhamento": "alto" | "médio" | "baixo",
  "observacoes": "Observações adicionais sobre o alinhamento com os anos iniciais"
}}

Trechos normativos da BNCC/PCN:
{context}
"""),
    ("human", """Descrição da atividade: {descricao}
Componente curricular: {componente}
Ano escolar: {ano}

Identifique as habilidades BNCC dos anos iniciais (1º ao 4º ano) alinhadas."""),
])


def check_bncc_alignment(
    descricao_atividade: str,
    componente: str,
    ano_escolar: str,
) -> dict:
    """
    Verifica o alinhamento de uma atividade com as habilidades da BNCC.

    Returns:
        dict com 'habilidades', 'competencias_gerais', 'alinhamento',
        'observacoes', 'elapsed_seconds', 'success'
    """
    start = time.time()

    query = f"habilidades {componente} {ano_escolar} {descricao_atividade[:200]}"
    docs = similarity_search(query, k=6)
    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('source', 'Fonte')}] {d.page_content}"
        for d in docs
    )

    llm = get_llm(temperature=0)
    parser = JsonOutputParser()
    chain = BNCC_CHECK_PROMPT | llm | parser

    try:
        result = chain.invoke({
            "descricao": descricao_atividade,
            "componente": componente,
            "ano": ano_escolar,
            "context": context,
        })
        habilidades = result.get("habilidades", [])
        success = len(habilidades) >= 1 and all(
            h.get("codigo") and h.get("justificativa") for h in habilidades
        )
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("bncc_checker_parse_error", error=str(e))
        result = {
            "habilidades": [],
            "competencias_gerais": [],
            "alinhamento": "baixo",
            "observacoes": "Não foi possível identificar habilidades BNCC com os documentos disponíveis.",
        }
        success = False

    elapsed = round(time.time() - start, 2)
    logger.info(
        "bncc_check_done",
        componente=componente,
        habilidades_found=len(result.get("habilidades", [])),
        alinhamento=result.get("alinhamento"),
        success=success,
        elapsed=elapsed,
    )

    return {
        **result,
        "elapsed_seconds": elapsed,
        "success": success,
        "sources": [{"content": d.page_content[:300], "metadata": d.metadata} for d in docs],
    }
