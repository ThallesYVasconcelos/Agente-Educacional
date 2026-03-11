FROM python:3.11-slim

LABEL maintainer="agentes-sociais"
LABEL description="Agentes Sociais RAG — Sistema multi-agente para impacto social"

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código-fonte
COPY . .

# Criar diretórios de dados
RUN mkdir -p data/raw data/processed/chroma eval/results logs

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STREAMLIT_PORT=8501
ENV MCP_PORT=8000

# Expor portas
EXPOSE 8501 8000

# Script de entrada
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["streamlit"]
