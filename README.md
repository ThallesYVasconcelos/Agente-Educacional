# EduRAG — Assistente para Professores dos Anos Iniciais (1º ao 4º ano)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11--3.13-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)

Sistema RAG agêntico open source para apoiar professores da Educação Básica brasileira.
Baseado em documentos públicos do MEC: **BNCC**, **PCN** e guias do **PNLD**.

---

## Problema

Professores dos Anos Iniciais (1º ao 4º ano) do Ensino Fundamental brasileiro frequentemente têm dificuldade de:

- Localizar rapidamente quais **habilidades da BNCC** (EF01–EF04) um conteúdo desenvolve
- Criar **planos de aula** alinhados à Base com citações normativas
- Navegar nas +600 páginas da BNCC para responder dúvidas sobre alfabetização e letramento

## Solução

Agente LangGraph com RAG focado nos **Anos Iniciais (1º ao 4º ano)** que:

1. **Responde perguntas** sobre BNCC, PCN e PNLD dos anos iniciais com citações de página
2. **Gera planos de aula** para o 1º ao 4º ano com habilidades BNCC (EF01–EF04) (Automação A1)
3. **Verifica habilidades** — dado uma atividade, identifica os códigos BNCC dos anos iniciais (Automação A2)
4. **Valida fidelidade** das respostas com Self-RAG (anti-alucinação)

---

## Arquitetura

```
Usuário
  │
  ▼
Streamlit UI (app/)
  │
  ▼
LangGraph — Supervisor Pattern
  │
  ├─ supervisor   → analisa intent → roteia (Q&A / automação / recusa)
  ├─ retriever    → ChromaDB (BAAI/bge-m3 embeddings, sem custo de API)
  ├─ safety       → adiciona aviso pedagógico se necessário
  ├─ writer       → resposta formatada com citações obrigatórias
  └─ self_check   → valida fidelidade (0.0–1.0); re-busca ou recusa se < 0.7
  │
  ├─ ChromaDB (local)          MCP Server (FastAPI :8000)
  │  BAAI/bge-m3 embeddings    search_docs · lesson_plan · bncc_skills
  │
  └─ Ollama (LLM local OSS)
     llama3.2 / qwen2.5 / mistral / gemma2
```

---

## Stack

| Componente | Tecnologia |
|---|---|
| Orquestração | LangGraph 0.2+ (StateGraph) |
| LLM (preferência) | Ollama + llama3.2 / qwen2.5 (100% local, sem custo) |
| LLM (fallback) | OpenAI gpt-4o-mini |
| Embeddings | BAAI/bge-m3 via HuggingFace (local, sem custo de API) |
| VectorStore | ChromaDB (local) |
| Interface | Streamlit |
| MCP Server | FastAPI |
| Avaliação | Giskard 2.0+ |
| Testes | pytest |

---

## Instalação

### Pré-requisitos

- Python **3.11 a 3.13** (recomendado 3.11 ou 3.12)
- [Ollama](https://ollama.com) instalado e rodando
- Git

> **Atenção:** Python 3.14 não é recomendado. O LangChain utiliza internamente o Pydantic v1, que não é compatível com Python 3.14+.

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/ThallesYVasconcelos/Agente-Educacional.git
cd Agente-Educacional
pip install -r requirements.txt
```


### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env conforme necessário
# USE_OLLAMA=true (padrão)
# OLLAMA_MODEL=llama3.2
```

### 3. Baixar o modelo Ollama

```bash
ollama pull llama3.2
# Alternativas: ollama pull qwen2.5 | ollama pull mistral
```

### 4. Baixar o corpus (documentos públicos do MEC)

Coloque os PDFs em **`data/raw/educacao/`** (crie a pasta se não existir).

#### Documentos obrigatórios

| Arquivo sugerido | Documento | URL de download |
|---|---|---|
| `bncc_ef.pdf` | BNCC — Ensino Fundamental (Anos Iniciais e Finais) | https://basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf |
| `pcn_lp_1_4.pdf` | PCN — Língua Portuguesa (1ª a 4ª série) | https://portal.mec.gov.br/seb/arquivos/pdf/livro02.pdf |
| `pcn_mat_1_4.pdf` | PCN — Matemática (1ª a 4ª série) | https://portal.mec.gov.br/seb/arquivos/pdf/matematica.pdf |
| `pcn_ciencias_1_4.pdf` | PCN — Ciências Naturais (1ª a 4ª série) | https://portal.mec.gov.br/seb/arquivos/pdf/ciencias.pdf |
| `pcn_historia_1_4.pdf` | PCN — História e Geografia (1ª a 4ª série) | https://portal.mec.gov.br/seb/arquivos/pdf/livro051a4.pdf |
| `pcn_arte_1_4.pdf` | PCN — Arte (1ª a 4ª série) | https://portal.mec.gov.br/seb/arquivos/pdf/livro06.pdf |
| `pcn_ef_1_4.pdf` | PCN — Educação Física (1ª a 4ª série) | https://portal.mec.gov.br/seb/arquivos/pdf/livro07.pdf |

> Todos são de **domínio público** (Ministério da Educação / gov.br). Acesso gratuito, sem login.

#### Como baixar rapidamente (PowerShell)

```powershell
# Crie a pasta
New-Item -ItemType Directory -Force -Path "data\raw\educacao"

# Baixe a BNCC (arquivo principal, ~474 páginas)
Invoke-WebRequest -Uri "https://basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf" -OutFile "data\raw\educacao\bncc_ef.pdf"

# Baixe os PCNs dos anos iniciais
Invoke-WebRequest -Uri "https://portal.mec.gov.br/seb/arquivos/pdf/livro02.pdf" -OutFile "data\raw\educacao\pcn_lp_1_4.pdf"
Invoke-WebRequest -Uri "https://portal.mec.gov.br/seb/arquivos/pdf/matematica.pdf" -OutFile "data\raw\educacao\pcn_mat_1_4.pdf"
Invoke-WebRequest -Uri "https://portal.mec.gov.br/seb/arquivos/pdf/ciencias.pdf" -OutFile "data\raw\educacao\pcn_ciencias_1_4.pdf"
```

### 5. Ingerir o corpus

```bash
python ingest/pipeline.py
```

### 6. Iniciar a aplicação

```bash
# Terminal 1 — Interface Streamlit
python -m streamlit run app/main.py

# Terminal 2 — MCP Server (opcional)
python src/mcp/server.py
```

### Usando Docker

```bash
docker-compose up
# Streamlit: http://localhost:8501
# MCP:       http://localhost:8000
```

---

## Uso com OpenAI (fallback)

Caso não tenha Ollama instalado:

```bash
# No .env:
USE_OLLAMA=false
OPENAI_API_KEY=sk-...
```

---

## MCP (Model Context Protocol)

### Tools disponíveis

| Tool | Endpoint | Descrição |
|---|---|---|
| `search_docs` | `POST /tools/search_docs` | Busca semântica na BNCC/PCN/PNLD |
| `generate_lesson_plan` | `POST /tools/generate_lesson_plan` | Gera plano de aula (A1) |
| `check_bncc_skills` | `POST /tools/check_bncc_skills` | Verifica alinhamento BNCC (A2) |
| `list_sources` | `GET /tools/list_sources` | Lista documentos ingeridos |
| `get_info` | `GET /tools/get_info` | Metadados do corpus e sistema |

### Segurança MCP

**Allowlist explícita:** apenas as 5 tools acima podem ser chamadas. Qualquer requisição a endpoint não listado retorna 404.

**Limites de input:**
- Query máxima: 2.000 caracteres
- Descrição máxima: 3.000 caracteres
- `top_k` máximo: 20
- `duracao_aulas` máximo: 5

**Audit log:** cada requisição é registrada em JSON com: timestamp, path, status, latência, IP do cliente (hash anonimizado).

**CORS restrito:** apenas `http://localhost:8501` (Streamlit local) é permitido.

**O que o agente NÃO pode fazer:**
- Executar código arbitrário
- Acessar internet diretamente (corpus local apenas)
- Ler arquivos fora de `data/raw/educacao/` e `data/processed/chroma/educacao/`
- Armazenar inputs do usuário além do log anonimizado
- Fornecer aconselhamento médico, jurídico ou psicológico
- Aceitar uploads de arquivos via API

**Justificativa da escolha MCP próprio (Opção 1):**
Criamos um servidor MCP próprio (`mcp-docstore`) em vez de usar um de terceiros para ter controle total sobre o que é exposto. Servidores MCP de terceiros apresentam riscos de supply-chain (injeção de prompt, exfiltração de dados). Com o servidor próprio, a allowlist é explícita e o filesystem é controlado.

---

## Avaliação

### RAG (Giskard)

```bash
python eval/giskard_eval.py --max-questions 15
```

Giskard AI Quality Scan: detecta vulnerabilidades (ex.: Prompt Injection), gera suíte de testes e relatório.
Perguntas rotuladas em `eval/questions/educacao.json`.

### Automações

```bash
python eval/automation_eval.py
```

- **A1 (Plano de Aula):** 5 casos → taxa de sucesso, citações, tempo médio
- **A2 (Verificador BNCC):** 5 casos → taxa de sucesso, habilidades identificadas, tempo médio

---

## Testes

```bash
pytest tests/ -v --cov=src
```

---

## Estrutura do projeto

```
edurag/
├── src/
│   ├── agents/
│   │   ├── graph.py            # LangGraph: supervisor→retriever→safety→writer→self_check
│   │   └── educacao_agent.py   # Fachada sobre o grafo
│   ├── rag/
│   │   ├── embeddings.py       # HuggingFace bge-m3 (local, sem custo)
│   │   ├── vectorstore.py      # ChromaDB
│   │   └── retriever.py        # EducacaoRetriever
│   ├── automations/
│   │   ├── lesson_plan.py      # A1: Gerador de Plano de Aula
│   │   └── bncc_checker.py     # A2: Verificador de Habilidades BNCC
│   ├── mcp/
│   │   ├── server.py           # FastAPI MCP Server
│   │   ├── tools.py            # 5 tools com allowlist
│   │   └── config.yaml         # Configuração de segurança
│   └── utils/
│       ├── helpers.py          # Settings + get_llm() (Ollama/OpenAI)
│       └── logger.py           # structlog JSON
├── app/
│   ├── main.py                 # Homepage Streamlit
│   └── pages/
│       ├── 1_assistente.py     # Chat Q&A com Self-RAG
│       └── 2_plano_aula.py     # Gerador de plano + verificador BNCC
├── ingest/
│   ├── loaders.py              # PDF e TXT loaders
│   ├── chunkers.py             # Chunking otimizado para BNCC
│   └── pipeline.py             # CLI de ingestão
├── eval/
│   ├── giskard_eval.py         # Avaliação RAG (Giskard)
│   ├── automation_eval.py      # Avaliação das automações
│   └── questions/
│       └── educacao.json       # 15 perguntas rotuladas
├── tests/                      # pytest
├── docs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── CITATION.cff
└── LICENSE
```

---

## Licença

MIT — veja [LICENSE](LICENSE).

## Citação

```bibtex
@software{edurag2026,
  title  = {EduRAG: Assistente RAG para Professores da Educação Básica},
  year   = {2026},
  url    = {https://github.com/seu-usuario/edurag},
  license = {MIT}
}
```
