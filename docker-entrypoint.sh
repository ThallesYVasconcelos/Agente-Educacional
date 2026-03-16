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
    exec python -m ingest.pipeline "$@"
    ;;
  eval)
    echo "Executando avaliação Giskard..."
    exec python eval/giskard_eval.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
