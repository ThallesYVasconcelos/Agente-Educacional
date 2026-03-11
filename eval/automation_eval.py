"""
Avaliação das Automações — EduRAG.

Avalia A1 (Gerador de Plano de Aula) e A2 (Verificador BNCC).
Métricas: taxa de sucesso, tempo médio, número de citações/habilidades.

Uso:
  python eval/automation_eval.py
  python eval/automation_eval.py --output eval/results/
"""

import json
import time
from pathlib import Path

import typer

from src.automations.lesson_plan import generate_lesson_plan
from src.automations.bncc_checker import check_bncc_alignment
from src.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()

# ---------------------------------------------------------------------------
# Casos de teste — A1: Plano de Aula
# ---------------------------------------------------------------------------

LESSON_PLAN_CASES = [
    {
        "id": "LP01",
        "componente": "Matemática",
        "habilidade": "EF02MA01 — Comparar e ordenar números naturais até 1000",
        "ano": "2º ano do Ensino Fundamental",
        "duracao": 2,
        "expected_sections": 5,
        "expected_min_citations": 2,
    },
    {
        "id": "LP02",
        "componente": "Língua Portuguesa",
        "habilidade": "EF03LP01 — Leitura de textos com fluência e compreensão",
        "ano": "3º ano do Ensino Fundamental",
        "duracao": 1,
        "expected_sections": 5,
        "expected_min_citations": 2,
    },
    {
        "id": "LP03",
        "componente": "Ciências",
        "habilidade": "EF04CI01 — Propriedades físicas dos materiais do cotidiano",
        "ano": "4º ano do Ensino Fundamental",
        "duracao": 3,
        "expected_sections": 5,
        "expected_min_citations": 2,
    },
    {
        "id": "LP04",
        "componente": "Língua Portuguesa",
        "habilidade": "EF01LP02 — Segmentação oral de palavras em sílabas (consciência fonológica)",
        "ano": "1º ano do Ensino Fundamental",
        "duracao": 1,
        "expected_sections": 5,
        "expected_min_citations": 2,
    },
    {
        "id": "LP05",
        "componente": "Arte",
        "habilidade": "EF15AR01 — Identificação e exploração de linguagens artísticas",
        "ano": "2º ano do Ensino Fundamental",
        "duracao": 1,
        "expected_sections": 5,
        "expected_min_citations": 2,
    },
]

# ---------------------------------------------------------------------------
# Casos de teste — A2: Verificador BNCC
# ---------------------------------------------------------------------------

BNCC_CHECK_CASES = [
    {
        "id": "BC01",
        "descricao": "A professora lê em voz alta um conto de fadas. Em seguida, os alunos recontem oralmente a história e identifiquem personagens principais e secundários.",
        "componente": "Língua Portuguesa",
        "ano": "2º ano do Ensino Fundamental",
        "expected_min_skills": 1,
    },
    {
        "id": "BC02",
        "descricao": "Os alunos usam palitos de sorvete para montar grupos e contar de 5 em 5 até 100, registrando no caderno.",
        "componente": "Matemática",
        "ano": "1º ano do Ensino Fundamental",
        "expected_min_skills": 1,
    },
    {
        "id": "BC03",
        "descricao": "Experimento: os alunos observam o que acontece com água, areia e sal quando misturados, registrando as observações em desenho.",
        "componente": "Ciências",
        "ano": "3º ano do Ensino Fundamental",
        "expected_min_skills": 1,
    },
    {
        "id": "BC04",
        "descricao": "Os alunos trazem fotos antigas da família e comparam com fotos atuais, identificando mudanças e permanências na vida cotidiana.",
        "componente": "História",
        "ano": "2º ano do Ensino Fundamental",
        "expected_min_skills": 1,
    },
    {
        "id": "BC05",
        "descricao": "Os alunos exploram instrumentos musicais de percussão simples (pandeiro, chocalho) e criam padrões rítmicos coletivos.",
        "componente": "Arte",
        "ano": "4º ano do Ensino Fundamental",
        "expected_min_skills": 1,
    },
]


def eval_lesson_plan() -> dict:
    results = []
    for case in LESSON_PLAN_CASES:
        start = time.time()
        try:
            result = generate_lesson_plan(
                case["componente"],
                case["habilidade"],
                case["ano"],
                case["duracao"],
            )
            elapsed = time.time() - start
            ok = (
                result["citations_count"] >= case["expected_min_citations"]
                and len(result["sections_present"]) >= case["expected_sections"]
            )
            results.append({
                "id": case["id"],
                "success": ok,
                "citations": result["citations_count"],
                "sections": len(result["sections_present"]),
                "elapsed_s": round(elapsed, 2),
            })
        except Exception as e:
            results.append({"id": case["id"], "success": False, "error": str(e)})

    success_rate = sum(1 for r in results if r.get("success")) / len(results)
    avg_time = sum(r.get("elapsed_s", 0) for r in results) / len(results)
    return {"cases": results, "success_rate": round(success_rate, 3), "avg_time_s": round(avg_time, 2)}


def eval_bncc_checker() -> dict:
    results = []
    for case in BNCC_CHECK_CASES:
        start = time.time()
        try:
            result = check_bncc_alignment(
                case["descricao"],
                case["componente"],
                case["ano"],
            )
            elapsed = time.time() - start
            ok = len(result.get("habilidades", [])) >= case["expected_min_skills"]
            results.append({
                "id": case["id"],
                "success": ok,
                "skills_found": len(result.get("habilidades", [])),
                "alinhamento": result.get("alinhamento"),
                "elapsed_s": round(elapsed, 2),
            })
        except Exception as e:
            results.append({"id": case["id"], "success": False, "error": str(e)})

    success_rate = sum(1 for r in results if r.get("success")) / len(results)
    avg_time = sum(r.get("elapsed_s", 0) for r in results) / len(results)
    return {"cases": results, "success_rate": round(success_rate, 3), "avg_time_s": round(avg_time, 2)}


@app.command()
def main(
    output: str = typer.Option("eval/results", help="Diretório de saída"),
):
    """Avalia A1 (Plano de Aula) e A2 (Verificador BNCC)."""
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    typer.echo("\nAvaliando A1 — Gerador de Plano de Aula ...")
    lp_results = eval_lesson_plan()
    typer.echo(f"  Taxa de sucesso : {lp_results['success_rate']:.0%}")
    typer.echo(f"  Tempo médio     : {lp_results['avg_time_s']}s")

    typer.echo("\nAvaliando A2 — Verificador de Habilidades BNCC ...")
    bc_results = eval_bncc_checker()
    typer.echo(f"  Taxa de sucesso : {bc_results['success_rate']:.0%}")
    typer.echo(f"  Tempo médio     : {bc_results['avg_time_s']}s")

    out = {
        "lesson_plan_eval": lp_results,
        "bncc_checker_eval": bc_results,
    }
    out_file = output_path / "automation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    typer.echo(f"\nResultados salvos em: {out_file}")


if __name__ == "__main__":
    app()
