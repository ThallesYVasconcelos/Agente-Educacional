"""
Avaliação RAG com RAGAS — EduRAG (Educação Básica).

Métricas: Context Precision, Context Recall, Faithfulness, Answer Relevancy + latência.
Documentação: https://docs.ragas.io

Uso:
  python eval/ragas_eval.py
  python eval/ragas_eval.py --max-questions 10
  python eval/ragas_eval.py --output eval/results/
"""

import json
import time
from pathlib import Path

import typer
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.agents.educacao_agent import EducacaoAgent
from src.utils.helpers import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()

QUESTIONS_PATH = Path("eval/questions/educacao.json")
RESULTS_PATH = Path("eval/results")


def load_questions(max_q: int = 20) -> list:
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        questions = json.load(f)
    return questions[:max_q]


def run_rag_eval(max_questions: int = 20) -> dict:
    """Executa avaliação RAGAS para o domínio de Educação Básica."""
    logger.info("ragas_eval_start", max_questions=max_questions)
    questions = load_questions(max_questions)
    agent = EducacaoAgent()

    rows = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    latencies = []

    for q in questions:
        start = time.time()
        result = agent.ask(q["question"])
        elapsed = time.time() - start
        latencies.append(elapsed)

        rows["question"].append(q["question"])
        rows["answer"].append(result["answer"])
        rows["contexts"].append([s["content"] for s in result.get("sources", [])])
        rows["ground_truth"].append(q["ground_truth"])

    dataset = Dataset.from_dict(rows)
    settings = get_settings()

    # RAGAS usa OpenAI para avaliar (independente do LLM da aplicação)
    eval_llm = ChatOpenAI(
        model=settings.ragas_eval_llm,
        openai_api_key=settings.openai_api_key,
    )
    eval_embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )

    score = evaluate(
        dataset,
        metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
        llm=eval_llm,
        embeddings=eval_embeddings,
    )

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    results = {
        "domain": "educacao",
        "n_questions": len(questions),
        "context_precision": round(score["context_precision"], 4),
        "context_recall": round(score["context_recall"], 4),
        "faithfulness": round(score["faithfulness"], 4),
        "answer_relevancy": round(score["answer_relevancy"], 4),
        "avg_latency_s": round(avg_latency, 2),
        "p95_latency_s": round(p95_latency, 2),
    }

    logger.info("ragas_eval_complete", **results)
    return results


@app.command()
def main(
    max_questions: int = typer.Option(20, help="Máximo de perguntas a avaliar"),
    output: str = typer.Option("eval/results", help="Diretório de saída"),
):
    """Executa avaliação RAGAS e salva resultados em JSON."""
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    typer.echo("\nAvaliando EduRAG com RAGAS ...")
    try:
        results = run_rag_eval(max_questions)

        typer.echo(f"\n  Context Precision : {results['context_precision']}")
        typer.echo(f"  Context Recall    : {results['context_recall']}")
        typer.echo(f"  Faithfulness      : {results['faithfulness']}")
        typer.echo(f"  Answer Relevancy  : {results['answer_relevancy']}")
        typer.echo(f"  Latência média    : {results['avg_latency_s']}s")
        typer.echo(f"  P95 latência      : {results['p95_latency_s']}s")

        out_file = output_path / "ragas_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        typer.echo(f"\nResultados salvos em: {out_file}")
    except Exception as e:
        typer.echo(f"Erro: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
