"""
Pipeline de ingestão do corpus de Educação Básica.

Uso:
  python ingest/pipeline.py

Adicione PDFs/TXTs da BNCC, PCN e PNLD em data/raw/educacao/ antes de rodar.

Fontes recomendadas (domínio público):
  BNCC EF: https://basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf
  BNCC EM: https://basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf
  PCNs  : https://portal.mec.gov.br/seb/arquivos/pdf/ (por componente)
"""

import typer
from pathlib import Path

from ingest.loaders import load_corpus
from ingest.chunkers import chunk_documents
from src.rag.vectorstore import add_documents
from src.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


@app.command()
def main(
    reset: bool = typer.Option(False, help="Apaga a coleção existente antes de ingerir"),
):
    """Executa o pipeline completo de ingestão do corpus educacional."""

    raw_path = Path("data/raw/educacao")
    if not raw_path.exists():
        typer.echo("Criando diretório data/raw/educacao/ ...")
        raw_path.mkdir(parents=True, exist_ok=True)

    if not any(raw_path.iterdir()):
        typer.echo(
            "\n[AVISO] Nenhum documento encontrado em data/raw/educacao/\n"
            "Adicione PDFs ou TXTs da BNCC, PCN e PNLD antes de continuar.\n"
            "Consulte o README para os links de download.\n"
        )
        raise typer.Exit(code=1)

    if reset:
        typer.echo("Resetando coleção ChromaDB ...")
        from src.rag.vectorstore import get_vectorstore
        vs = get_vectorstore()
        vs.delete_collection()
        typer.echo("  Coleção removida.")

    typer.echo("\nCarregando documentos ...")
    docs = load_corpus()
    typer.echo(f"  {len(docs)} páginas/documentos carregados")

    typer.echo("Criando chunks ...")
    chunks = chunk_documents(docs)
    typer.echo(f"  {len(chunks)} chunks criados")

    typer.echo("Indexando no ChromaDB ...")
    add_documents(chunks)
    typer.echo(f"  {len(chunks)} chunks indexados com sucesso!\n")
    typer.echo("Ingestão concluída. Execute 'streamlit run app/main.py' para iniciar.")


if __name__ == "__main__":
    app()
