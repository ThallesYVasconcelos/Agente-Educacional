# EduRAG — Assistente para Professores dos Anos Iniciais (1º ao 4º ano)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

Sistema RAG agêntico open source para apoiar professores dos **Anos Iniciais do Ensino Fundamental** (1º ao 4º ano) brasileira.
Baseado em documentos públicos do MEC: **BNCC**, **PCN** e guias do **PNLD**.

> Documentação completa será adicionada ao final do desenvolvimento.

## Stack (planejado)

- **Orquestração:** LangGraph (StateGraph + Self-RAG)
- **LLM:** Ollama local (llama3.2 / qwen2.5)
- **Embeddings:** BAAI/bge-m3 via HuggingFace
- **VectorStore:** ChromaDB
- **Interface:** Streamlit
- **MCP:** FastAPI
- **Avaliação:** RAGAS

## Licença

MIT — veja [LICENSE](LICENSE).
