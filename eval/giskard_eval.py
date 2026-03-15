"""
Giskard evaluation module for EduRAG (Educação Básica).

Avaliação de qualidade do RAG usando Giskard: scan, test suite e relatório.

Uso:
  python eval/giskard_eval.py
  python eval/giskard_eval.py --max-questions 5
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd
import typer

try:
    from giskard import Dataset, Model, scan
    GISKARD_AVAILABLE = True
except ImportError as e:
    GISKARD_AVAILABLE = False
    _GISKARD_ERROR = str(e)

from src.agents.educacao_agent import EducacaoAgent
from src.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()

QUESTIONS_PATH = Path("eval/questions/educacao.json")
RESULTS_PATH = Path("eval/results")


def load_questions(max_q: int = 20) -> list:
    """Carrega perguntas rotuladas do JSON."""
    if not QUESTIONS_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {QUESTIONS_PATH}")
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # Suporta lista direta ou {"evaluation_dataset": [...]}
    items = data if isinstance(data, list) else data.get("evaluation_dataset", [])
    return items[:max_q]


def run_giskard_eval(max_questions: int = 20) -> dict[str, Any]:
    """Executa avaliação Giskard para o EduRAG."""
    if not GISKARD_AVAILABLE:
        raise RuntimeError(
            f"Giskard não instalado: {_GISKARD_ERROR}\n"
            "Instale com: pip install giskard pandas"
        )

    logger.info("giskard_eval_start", max_questions=max_questions)
    questions = load_questions(max_questions)
    agent = EducacaoAgent()

    # 1. Função de predição para o Giskard
    def predict_answers(df: pd.DataFrame) -> list[str]:
        results = []
        for _, row in df.iterrows():
            question = row["question"]
            try:
                result = agent.ask(question)
                results.append(result["answer"])
            except Exception as e:
                logger.error("giskard_predict_error", question=question[:50], error=str(e))
                results.append("Erro ao processar pergunta")
        return results

    # 2. Dataset no formato esperado pelo Giskard
    df_data = []
    for item in questions:
        df_data.append({
            "question": item["question"],
            "ground_truth": item["ground_truth"],
            "question_id": item.get("id", ""),
            "source": item.get("source", ""),
        })
    df = pd.DataFrame(df_data)

    dataset = Dataset(
        df=df,
        name="EduRAG Evaluation Dataset",
        target="ground_truth",
        cat_columns=[],
    )

    # 3. Modelo Giskard (text_generation)
    model = Model(
        model=predict_answers,
        model_type="text_generation",
        name="EduRAG",
        description="RAG com LangGraph para Educação Básica (BNCC, PCN, PNLD)",
        feature_names=["question"],
    )

    # 4. Scan (Giskard 2.x: scan retorna ScanReport com .issues)
    scan_report = None
    issues_list: list = []
    try:
        scan_report = scan(model, dataset)
        issues_list = getattr(scan_report, "issues", [])
    except Exception as e:
        logger.error("giskard_scan_error", error=str(e))

    # 5. Test suite (Giskard 2.x: generate_test_suite é método do ScanReport)
    test_results: Any = {}
    if scan_report and hasattr(scan_report, "generate_test_suite"):
        try:
            test_suite = scan_report.generate_test_suite("EduRAG Test Suite")
            if test_suite and hasattr(test_suite, "run"):
                raw = test_suite.run(verbose=False)
                test_results = {"passed": getattr(raw, "passed", None), "total": getattr(raw, "total", None)}
        except Exception as e:
            logger.warning("giskard_test_suite_error", error=str(e))
            test_results = {"error": str(e)}

    # 6. Compilar resultados
    results = {
        "evaluation_type": "giskard",
        "dataset_size": len(questions),
        "scan_summary": {
            "total_issues": len(issues_list),
            "critical": len([i for i in issues_list if getattr(i, "level", "") == "error"]),
            "warnings": len([i for i in issues_list if getattr(i, "level", "") == "warning"]),
            "info": len([i for i in issues_list if getattr(i, "level", "") == "info"]),
        },
        "issues": [
            {
                "type": type(issue).__name__,
                "level": getattr(issue, "level", "unknown"),
                "description": str(issue),
            }
            for issue in issues_list
        ],
        "test_results": test_results,
    }

    logger.info("giskard_eval_complete", **results["scan_summary"])
    return results


def generate_report(results: dict[str, Any]) -> str:
    """Gera relatório em Markdown."""
    s = results.get("scan_summary", {})
    issues = results.get("issues", [])
    issues_text = "\n".join(
        f"- **{i.get('type', '?')}** ({i.get('level', '?')}): {str(i.get('description', ''))[:100]}..."
        for i in issues[:15]
    )
    return f"""# Relatório de Avaliação Giskard — EduRAG

## Resumo
- **Tipo**: Giskard AI Quality Scan
- **Dataset**: {results.get('dataset_size', 0)} perguntas
- **Total de problemas**: {s.get('total_issues', 0)}
- **Críticos**: {s.get('critical', 0)}
- **Avisos**: {s.get('warnings', 0)}
- **Info**: {s.get('info', 0)}

## Problemas identificados
{issues_text}

## Recomendações
1. Revisar problemas críticos
2. Executar testes regularmente
3. Monitorar qualidade em produção
"""


@app.command()
def main(
    max_questions: int = typer.Option(20, help="Máximo de perguntas"),
    output: str = typer.Option("eval/results", help="Diretório de saída"),
):
    """Executa avaliação Giskard e salva resultados."""
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    typer.echo("\nAvaliando EduRAG com Giskard ...")
    try:
        results = run_giskard_eval(max_questions)
        s = results["scan_summary"]

        typer.echo(f"\n  Total de problemas : {s['total_issues']}")
        typer.echo(f"  Críticos           : {s['critical']}")
        typer.echo(f"  Avisos             : {s['warnings']}")
        typer.echo(f"  Info               : {s['info']}")

        # Salvar JSON (test_results pode não ser serializável)
        out_json = output_path / "giskard_results.json"
        save_results = {k: v for k, v in results.items() if k != "test_results"}
        save_results["test_results_summary"] = str(results.get("test_results", ""))[:500]
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(save_results, f, ensure_ascii=False, indent=2)
        typer.echo(f"\nResultados salvos em: {out_json}")

        # Salvar relatório
        report = generate_report(results)
        out_md = output_path / f"giskard_report_{int(time.time())}.md"
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(report)
        typer.echo(f"Relatório salvo em: {out_md}")
    except Exception as e:
        typer.echo(f"Erro: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
