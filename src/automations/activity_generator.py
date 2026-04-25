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
# Classificação de disciplinas por natureza pedagógica
# ---------------------------------------------------------------------------

# Disciplinas onde cálculo numérico é o objeto central das questões
_DISCIPLINAS_EXATAS = {"Matemática", "Física", "Química"}

# Disciplinas onde questões devem ser conceituais/analíticas (sem cálculo numérico)
_DISCIPLINAS_CONCEITUAIS = {
    "Ciências", "Biologia", "Língua Portuguesa", "Literatura",
    "História", "Geografia", "Arte", "Educação Física",
    "Ensino Religioso", "Filosofia", "Sociologia",
    "Língua Estrangeira (Inglês)", "Língua Estrangeira (Espanhol)",
    "Língua Estrangeira", "Inglês", "Espanhol",
    "Ciências da Natureza", "Ciências Humanas",
}

# Escopos-padrão para disciplinas sem entrada no CURRICULUM_SCOPE
_SCOPE_DEFAULTS: dict[str, str] = {
    "Arte": (
        "Explore elementos da linguagem artística (linha, forma, cor, textura, volume, espaço) "
        "e manifestações culturais e artísticas regionais e universais. "
        "Questões devem envolver análise, identificação e contextualização de obras e movimentos artísticos, "
        "adequados ao ano escolar informado. Habilidades BNCC: EF01-09AR / EM13LGG."
    ),
    "Educação Física": (
        "Aborde práticas corporais, esportes, jogos, danças, lutas e ginásticas "
        "conforme o ano escolar informado. "
        "Questões devem envolver conceitos, regras, valores e reflexão crítica sobre as práticas corporais. "
        "Habilidades BNCC: EF01-09EF / EM13LGG."
    ),
    "Ensino Religioso": (
        "Aborde diversidade religiosa, tradições, práticas de espiritualidade e respeito "
        "à pluralidade de crenças no contexto brasileiro, conforme o ano escolar informado. "
        "Questões devem ser reflexivas e respeitosas. Habilidades BNCC: EF01-09ER."
    ),
    "Filosofia": (
        "Aborde conceitos filosóficos, pensadores, correntes do pensamento e ética, "
        "adequados ao Ensino Médio. Questões devem estimular argumentação e reflexão crítica. "
        "Habilidades BNCC: EM13CNT / EM13CHS."
    ),
    "Sociologia": (
        "Aborde conceitos sociológicos, fenômenos sociais, cultura, desigualdades, "
        "cidadania e democracia, adequados ao Ensino Médio. "
        "Questões devem estimular análise crítica da realidade social. "
        "Habilidades BNCC: EM13CHS."
    ),
    "Língua Estrangeira (Inglês)": (
        "Aborde vocabulário, gramática, compreensão de texto e produção escrita em inglês, "
        "adequados ao ano escolar informado. Questões podem ser em português com trechos em inglês. "
        "Habilidades BNCC: EF06-09LI / EM13LGG."
    ),
    "Língua Estrangeira (Espanhol)": (
        "Aborde vocabulário, gramática, compreensão de texto e produção escrita em espanhol, "
        "adequados ao ano escolar informado. Habilidades BNCC: EF06-09LE / EM13LGG."
    ),
    "Física": (
        "Trabalhe conceitos, leis e fenômenos físicos com cálculos adequados ao Ensino Médio. "
        "Habilidades BNCC: EM13CNT."
    ),
    "Química": (
        "Trabalhe conceitos, reações e cálculos químicos adequados ao Ensino Médio. "
        "Habilidades BNCC: EM13CNT."
    ),
    "Biologia": (
        "Trabalhe conceitos e processos biológicos adequados ao Ensino Médio: célula, genética, "
        "evolução, ecologia, fisiologia. Questões devem ser conceituais e analíticas. "
        "Habilidades BNCC: EM13CNT."
    ),
}


def _classify_discipline(componente: str) -> str:
    """Retorna 'exata' ou 'conceitual' para a disciplina informada."""
    if componente in _DISCIPLINAS_EXATAS:
        return "exata"
    return "conceitual"


def _get_scope(componente: str, ano: str) -> str:
    """Retorna o escopo curricular para a disciplina e ano, com fallback."""
    scope = CURRICULUM_SCOPE.get(componente, {}).get(ano, "")
    if not scope:
        scope = _SCOPE_DEFAULTS.get(componente, _DEFAULT_SCOPE)
    return scope


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
    ("system", """Você é professor especialista em Educação Básica brasileira.
Gere atividades pedagógicas DIRETAMENTE sobre o tópico informado.

⚠️ REGRA ABSOLUTA: TODAS as questões devem exigir conhecimento de "{topico}" em "{componente}".
Classificação desta disciplina: {natureza_disciplina}

{instrucoes_por_natureza}

ESCOPO CURRICULAR ({ano} — {componente}):
{escopo_curricular}

REGRAS ADICIONAIS:
- Respeite o escopo: não antecipe conteúdos de séries superiores.
- Use português claro. Proibido LaTeX: use × ÷ ² ³ ⁴ ⁵ no lugar de notação matemática.
- Tipo de atividade: {tipo_descricao}
- Quantidade: {quantidade} questões
- Gradação obrigatória: distribua entre fácil, médio e desafiador.

Retorne APENAS este JSON (sem markdown, sem texto extra):
{{"titulo":"...","disciplina":"{componente}","ano":"{ano}","topico":"{topico}","habilidades_gerais":["EM13.." ou "EF.."],"questoes":[{{"numero":1,"tipo":"dissertativa|multipla_escolha|situacao_problema|calculo","enunciado":"...","alternativas":[],"resposta_correta":"...","resolucao_passo_a_passo":"...","habilidade_bncc":"EM13.. ou EF..","nivel":"facil|medio|desafiador"}}]}}

alternativas: lista vazia [] exceto em múltipla escolha.
"""),
    ("human", """Disciplina: {componente} | Ano: {ano} | Tópico: {topico}
Tipo: {tipo_descricao} | Questões: {quantidade}

Referência curricular (BNCC/PCN):
{context}

{lembrete_por_natureza}

Gere o JSON com exatamente {quantidade} questões."""),
])

# ---------------------------------------------------------------------------
# Prompt de Validação (segundo passo)
# ---------------------------------------------------------------------------

_VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é especialista em Educação Básica. Verifique cada questão:

1. A resposta está correta (conceitual ou matematicamente)?
2. Está dentro do escopo do ano?
3. ⚠️ A questão exige realmente conhecimento de "{topico}" em "{componente}"?

Classificação desta disciplina: {natureza_disciplina}

{instrucoes_validacao_por_natureza}

Tópico: {topico} | Disciplina: {componente} | Ano: {ano}
Escopo: {escopo_curricular}

Retorne o MESMO JSON, adicionando em cada questão:
  "validacao": "ok" ou "corrigido"
  "nota_validacao": "o que corrigiu" (só se corrigido)

Retorne APENAS o JSON, sem markdown."""),
    ("human", "Verifique:\n{atividades_json}"),
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

    # ── Escopo e classificação de disciplina ──────────────────────────────
    escopo = _get_scope(componente, ano_escolar)
    tipo_descricao = ACTIVITY_TYPES.get(tipo, ACTIVITY_TYPES["misto"])
    natureza = _classify_discipline(componente)

    if natureza == "exata":
        natureza_label = "EXATA (Matemática / Física / Química) — cálculos e resolução numérica são esperados"
        instrucoes_por_natureza = (
            f"REGRAS para disciplinas EXATAS:\n"
            f"- As questões devem envolver cálculos, fórmulas e resolução numérica de '{topico}'.\n"
            f"- Cada questão deve testar diretamente '{topico}', não outro conteúdo matemático.\n"
            f"- Exemplo ERRADO (tópico: Potenciação): 'Maria tem 3 caixas com 4 docinhos. Quantos docinhos?' → isso é multiplicação.\n"
            f"- Exemplo CERTO (tópico: Potenciação): 'Calcule 3⁴.' ou 'Uma bactéria duplica por hora. Partindo de 1, quantas após 5h? Escreva como potência.'"
        )
        instrucoes_validacao = (
            "Para disciplinas EXATAS: verifique se os cálculos e resultados estão corretos.\n"
            "Verifique se a questão realmente testa o TÓPICO informado, não outro conteúdo matemático."
        )
        lembrete = f"Gere questões com cálculo e resolução numérica explícita de '{topico}'."
    else:
        natureza_label = "CONCEITUAL (Ciências / Humanas / Linguagens / Arte / Outras) — questões conceituais, analíticas e reflexivas"
        instrucoes_por_natureza = (
            f"REGRAS para disciplinas CONCEITUAIS:\n"
            f"- As questões DEVEM exigir conhecimento específico de '{topico}' em '{componente}'.\n"
            f"- PROIBIDO: questões que sejam apenas cálculos numéricos (porcentagem, razão, multiplicação)\n"
            f"  disfarçados com o tema da disciplina. Isso é Matemática, não {componente}.\n"
            f"- PERMITIDO: questões de identificação, definição, análise, comparação, exemplificação,\n"
            f"  interpretação, produção de texto, múltipla escolha conceitual, situação-problema que\n"
            f"  exija raciocínio próprio da disciplina.\n\n"
            f"Exemplos por disciplina:\n"
            f"  Ciências/Biologia — 'O que é uma cadeia alimentar? Cite produtores e consumidores.'\n"
            f"  História — 'Quais foram as principais causas da Revolução Francesa?'\n"
            f"  Geografia — 'Explique o que é urbanização e cite dois impactos sociais.'\n"
            f"  Língua Portuguesa — 'Identifique o tema e a tese no texto abaixo.'\n"
            f"  Arte — 'Cite três características do movimento impressionista.'\n"
            f"  Filosofia — 'O que Platão entendia por justiça? Relacione com a República.'\n"
            f"  Inglês — 'Complete com o tempo verbal correto: She ___ (go) to school every day.'"
        )
        instrucoes_validacao = (
            f"Para disciplinas CONCEITUAIS: REJEITE qualquer questão que seja apenas um cálculo numérico\n"
            f"(porcentagem, razão, multiplicação, etc.) sem exigir conhecimento real de '{topico}' em '{componente}'.\n"
            f"Substitua tais questões por perguntas conceituais, analíticas ou de múltipla escolha sobre o tema.\n"
            f"Exemplo de questão INVÁLIDA para Ecologia: 'Uma floresta tem 120 árvores. Se 30% são frutíferas, quantas são?'\n"
            f"→ Substitua por: 'O que é um ecossistema? Cite dois exemplos de relações ecológicas.'"
        )
        lembrete = (
            f"ATENÇÃO: Não gere cálculos numéricos de Matemática com '{topico}' como contexto.\n"
            f"Gere questões que testem conhecimento real de '{topico}' em '{componente}'."
        )

    # ── Busca trechos de documentos curriculares relevantes ───────────────
    query_hab = f"habilidades BNCC {componente} {topico} {ano_escolar}"
    query_ped = f"{topico} {componente} {ano_escolar} atividades"
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

    context_parts = []
    for d in docs:
        snippet = d.page_content[:400]
        source = d.metadata.get("source", "Fonte")
        context_parts.append(f"[{source}] {snippet}")
    context = "\n---\n".join(context_parts) or "Use o escopo curricular como referência."

    escopo_curto = escopo[:600] if len(escopo) > 600 else escopo

    from src.utils.curriculum_checker import check_content

    # ── Passo 1: Geração com retry por violação de escopo ─────────────────
    logger.info("activity_generation_start", topico=topico, componente=componente, ano=ano_escolar)

    data = None
    check_result = None
    MAX_GEN_RETRIES = 2

    for gen_attempt in range(MAX_GEN_RETRIES + 1):
        gen_llm = get_llm(temperature=0.4 - gen_attempt * 0.1)
        gen_chain = _GENERATION_PROMPT | gen_llm
        gen_response = gen_chain.invoke({
            "topico": topico,
            "componente": componente,
            "ano": ano_escolar,
            "escopo_curricular": escopo_curto,
            "tipo_descricao": tipo_descricao,
            "quantidade": quantidade,
            "context": context,
            "natureza_disciplina": natureza_label,
            "instrucoes_por_natureza": instrucoes_por_natureza,
            "lembrete_por_natureza": lembrete,
        })

        raw_gen = _fix_latex(_strip_code_fences(gen_response.content))
        data = _parse_json_safely(raw_gen)

        if not data or not data.get("questoes"):
            continue  # tenta de novo

        # Verifica escopo (nível 1, rápido) nas questões geradas
        questoes_text = " ".join(
            q.get("enunciado", "") + " " + q.get("resposta_correta", "")
            for q in data.get("questoes", [])
        )
        check_result = check_content(
            content=questoes_text,
            componente=componente,
            ano=ano_escolar,
            escopo=escopo_curto,
            run_traceability=False,  # rápido — sem LLM aqui
        )

        logger.info(
            "activity_scope_check",
            attempt=gen_attempt + 1,
            scope_ok=check_result.scope_ok,
            violations=check_result.violations,
        )

        if check_result.scope_ok:
            break

        logger.warning("activity_scope_violation_retry", violations=check_result.violations)

    if not data or not data.get("questoes"):
        elapsed = round(time.time() - start, 2)
        logger.error("activity_generation_failed", elapsed=elapsed)
        return {
            "student_md": "",
            "teacher_md": "",
            "data": None,
            "validated": False,
            "corrections": 0,
            "check_result": None,
            "elapsed_seconds": elapsed,
            "success": False,
            "error": "Não foi possível gerar as atividades. Tente reformular o tópico ou reduzir a quantidade de questões.",
            "sources": [],
        }

    # ── Passo 2: Validação de respostas ───────────────────────────────────
    logger.info("activity_validation_start", questoes=len(data.get("questoes", [])))
    val_llm = get_llm(temperature=0.1)
    val_chain = _VALIDATION_PROMPT | val_llm
    val_response = val_chain.invoke({
        "topico": topico,
        "componente": componente,
        "ano": ano_escolar,
        "escopo_curricular": escopo_curto,
        "natureza_disciplina": natureza_label,
        "instrucoes_validacao_por_natureza": instrucoes_validacao,
        "atividades_json": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    })

    raw_val = _fix_latex(_strip_code_fences(val_response.content))
    validated_data = _parse_json_safely(raw_val)

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
        scope_ok=check_result.scope_ok if check_result else None,
        elapsed=elapsed,
        success=success,
    )

    return {
        "student_md": _format_student_version(validated_data),
        "teacher_md": _format_teacher_version(validated_data),
        "data": validated_data,
        "validated": validated,
        "corrections": corrections,
        "check_result": check_result,
        "elapsed_seconds": elapsed,
        "success": success,
        "sources": [
            {"content": d.page_content[:300], "metadata": d.metadata}
            for d in docs
        ],
    }
