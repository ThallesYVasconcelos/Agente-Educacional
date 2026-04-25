"""
Verificador curricular de dois níveis.

Nível 1 — Escopo (local, rápido, sem LLM):
  Detecta palavras-chave proibidas para o ano/disciplina
  baseado nas restrições explícitas do CURRICULUM_SCOPE.

Nível 2 — Rastreabilidade (LLM + corpus):
  Pede ao LLM que avalie se cada seção do conteúdo tem
  respaldo nos documentos curriculares ou é "invenção".
  Retorna um score de confiança (0–1) e lista de alegações
  sem fonte.

Uso típico:
    result = check_content(
        content=markdown_text,
        componente="Matemática",
        ano="6º ano do Ensino Fundamental",
        escopo=CURRICULUM_SCOPE["Matemática"]["6º ano..."],
    )
    if not result["approved"]:
        # regenerar ou avisar
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Restrições explícitas por ano — complementam o CURRICULUM_SCOPE.
# Cada entrada: (ano, disciplina) -> lista de termos proibidos.
# Baseado nas anotações "NÃO trabalhar" do CURRICULUM_SCOPE.
# ---------------------------------------------------------------------------

_FORBIDDEN: dict[tuple[str, str], list[str]] = {
    # Matemática — anos iniciais
    ("1º ano do Ensino Fundamental", "Matemática"): [
        "reagrupamento", "multiplicação", "multiplicar", "divisão", "dividir",
        "fração", "decimal", "porcentagem", "potência", "raiz",
    ],
    ("2º ano do Ensino Fundamental", "Matemática"): [
        "tabuada completa", "divisão formal", "fração escrita", "decimal",
        "porcentagem", "potência", "raiz quadrada",
    ],
    ("3º ano do Ensino Fundamental", "Matemática"): [
        "decimal", "porcentagem", "potenciação", "potência", "raiz quadrada",
        "frações equivalentes formais", "equação",
    ],
    ("4º ano do Ensino Fundamental", "Matemática"): [
        "porcentagem", "potenciação", "potência", "equação", "raiz quadrada",
        "operações com decimais",
    ],
    ("5º ano do Ensino Fundamental", "Matemática"): [
        "potenciação", "potência", "radiciação", "raiz quadrada",
        "equação", "número negativo", "inteiro negativo",
    ],
    # Matemática — anos finais
    ("6º ano do Ensino Fundamental", "Matemática"): [
        "expoente negativo", "expoente fracionário", "raiz quadrada",
        "radiciação", "raiz cúbica", "√", "número irracional",
    ],
    ("7º ano do Ensino Fundamental", "Matemática"): [
        "expoente fracionário", "raiz de não-perfeito", "número irracional",
        "equação do 2º grau", "bhaskara", "função do 1º grau",
    ],
    ("8º ano do Ensino Fundamental", "Matemática"): [
        "progressão aritmética", "progressão geométrica",
        "seno", "cosseno", "tangente", "trigonometria",
        "análise combinatória", "permutação",
    ],
    ("9º ano do Ensino Fundamental", "Matemática"): [
        "logaritmo", "matriz", "determinante", "geometria analítica",
    ],
    # Ciências — anos iniciais
    ("1º ano do Ensino Fundamental", "Ciências"): [
        "célula", "fotossíntese", "mitose", "genética", "átomo",
    ],
    ("2º ano do Ensino Fundamental", "Ciências"): [
        "célula", "fotossíntese", "átomo", "tabela periódica",
    ],
    ("3º ano do Ensino Fundamental", "Ciências"): [
        "célula", "átomo", "tabela periódica", "química formal",
    ],
    ("4º ano do Ensino Fundamental", "Ciências"): [
        "átomo", "tabela periódica", "ligação química", "célula eucariótica",
    ],
    ("5º ano do Ensino Fundamental", "Ciências"): [
        "célula", "mitose", "meiose", "genética", "átomo", "tabela periódica",
        "ligação química", "física formal",
    ],
    # Ciências — anos finais
    ("6º ano do Ensino Fundamental", "Ciências"): [
        "genética", "hereditariedade", "evolução", "átomo", "tabela periódica",
        "ligação química", "newton", "cinemática",
    ],
    ("7º ano do Ensino Fundamental", "Ciências"): [
        "genética", "DNA", "cromossomo", "átomo", "tabela periódica",
        "ligação química", "leis de newton",
    ],
    ("8º ano do Ensino Fundamental", "Ciências"): [
        "tabela periódica", "ligação química", "funções inorgânicas",
        "cinemática", "leis de newton",
    ],
}

# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    approved: bool
    scope_ok: bool
    violations: list[str] = field(default_factory=list)
    trust_score: float = 1.0          # 0.0 a 1.0
    unsupported_claims: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def trust_label(self) -> str:
        if self.trust_score >= 0.80:
            return "alta"
        if self.trust_score >= 0.50:
            return "média"
        return "baixa"

    @property
    def trust_color(self) -> str:
        return {"alta": "#0A7B3E", "média": "#C08A00", "baixa": "#B00020"}[self.trust_label]


# ---------------------------------------------------------------------------
# Nível 1 — verificação de escopo (local, sem LLM)
# ---------------------------------------------------------------------------

def _check_scope(
    content: str,
    ano: str,
    componente: str,
) -> tuple[bool, list[str]]:
    """
    Verifica se o conteúdo menciona termos proibidos para o ano/disciplina.
    Retorna (ok, lista_de_violações).
    """
    key = (ano, componente)
    forbidden = _FORBIDDEN.get(key, [])
    content_lower = content.lower()

    violations = []
    for term in forbidden:
        # Busca o termo como palavra completa (evita falsos positivos)
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, content_lower):
            violations.append(term)

    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# Nível 2 — rastreabilidade via LLM (mais lento, mais preciso)
# ---------------------------------------------------------------------------

def _check_traceability(
    content: str,
    escopo: str,
    componente: str,
    ano: str,
) -> tuple[float, list[str]]:
    """
    Pede ao LLM que avalie o conteúdo gerado:
    - O conteúdo está dentro do escopo curricular do ano?
    - Existe alguma afirmação sem respaldo nos documentos BNCC/PCN?

    Retorna (trust_score 0.0–1.0, lista de alegações problemáticas).
    """
    try:
        from src.utils.helpers import get_llm
        from langchain_core.prompts import ChatPromptTemplate

        _TRACE_PROMPT = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em currículo da Educação Básica brasileira.
Sua tarefa é avaliar se um conteúdo pedagógico gerado por IA está correto e dentro do escopo.

Escopo curricular oficial para {ano} — {componente}:
{escopo}

Avalie o conteúdo recebido e retorne APENAS este JSON:
{{"score": 0.0_a_1.0, "problemas": ["lista de problemas encontrados ou vazia"]}}

Critérios para diminuir o score:
- Conteúdo que ultrapassa o escopo do ano (-0.3 por ocorrência)
- Afirmações factuais incorretas (-0.4)
- Habilidades BNCC inventadas ou erradas (-0.2)
- Conceitos misturados entre séries diferentes (-0.2)

Score 1.0 = tudo correto e dentro do escopo.
Score 0.0 = conteúdo totalmente inadequado para o ano."""),
            ("human", "Avalie este conteúdo:\n\n{content}"),
        ])

        llm = get_llm(temperature=0.0)
        chain = _TRACE_PROMPT | llm
        response = chain.invoke({
            "ano": ano,
            "componente": componente,
            "escopo": escopo[:500],  # limita tokens
            "content": content[:2000],  # limita tokens
        })

        import json, re as _re
        raw = response.content.strip()
        # Remove code fences
        raw = _re.sub(r"```[a-zA-Z]*\n?", "", raw)
        raw = _re.sub(r"```", "", raw).strip()

        # Tenta extrair JSON
        match = _re.search(r"\{[\s\S]+\}", raw)
        if match:
            data = json.loads(match.group())
            score = float(data.get("score", 0.8))
            score = max(0.0, min(1.0, score))
            problems = data.get("problemas", [])
            return score, problems

    except Exception as exc:
        logger.warning("traceability_check_failed", error=str(exc))

    # Se falhar, retorna score neutro
    return 0.75, []


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def check_content(
    content: str,
    componente: str,
    ano: str,
    escopo: str,
    run_traceability: bool = True,
) -> CheckResult:
    """
    Executa verificação de dois níveis no conteúdo gerado.

    Args:
        content: texto Markdown gerado pelo sistema
        componente: disciplina (ex. "Matemática")
        ano: ano escolar (ex. "6º ano do Ensino Fundamental")
        escopo: texto do CURRICULUM_SCOPE para este ano/componente
        run_traceability: se True, executa verificação LLM (mais lento)

    Returns:
        CheckResult com approved, violations, trust_score e detalhes.
    """
    # Nível 1
    scope_ok, violations = _check_scope(content, ano, componente)

    # Nível 2 (opcional, mais lento)
    trust_score = 1.0
    unsupported: list[str] = []
    if run_traceability:
        trust_score, unsupported = _check_traceability(content, escopo, componente, ano)

    # Aprovado se: sem violações de escopo E confiança >= 0.50
    approved = scope_ok and trust_score >= 0.50

    detail_parts = []
    if violations:
        detail_parts.append(
            f"Termos fora do escopo detectados: {', '.join(violations)}."
        )
    if unsupported:
        detail_parts.append(
            f"Possíveis problemas: {'; '.join(unsupported[:3])}."
        )
    if approved:
        detail_parts.append("Conteúdo dentro do escopo curricular.")

    logger.info(
        "curriculum_check",
        componente=componente,
        ano=ano,
        scope_ok=scope_ok,
        violations=violations,
        trust_score=trust_score,
        approved=approved,
    )

    return CheckResult(
        approved=approved,
        scope_ok=scope_ok,
        violations=violations,
        trust_score=trust_score,
        unsupported_claims=unsupported,
        detail=" ".join(detail_parts),
    )
