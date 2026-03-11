#!/bin/bash
set -e

case "$1" in
  streamlit)
    echo "Iniciando interface Streamlit..."
    exec streamlit run app/main.py \
      --server.port=${STREAMLIT_PORT:-8501} \
      --server.address=0.0.0.0 \
      --server.headless=true
    ;;
  mcp)
    echo "Iniciando servidor MCP..."
    exec python src/mcp/server.py
    ;;
  ingest)
    echo "Executando pipeline de ingestão..."
    exec python ingest/pipeline.py "$@"
    ;;
  eval)
    echo "Executando avaliação RAGAS..."
    exec python eval/ragas_eval.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
