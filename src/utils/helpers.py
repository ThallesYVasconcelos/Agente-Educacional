"""Utilitários gerais e carregamento de configurações."""

import os as _os
from functools import lru_cache
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Provedor do LLM: "ollama" | "replicate" | "openai"
    llm_provider: str = "ollama"

    # LLM: Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # LLM: Replicate
    replicate_api_token: str = ""
    # Modelos disponíveis no Replicate:
    #   "meta/meta-llama-3-8b-instruct"   → rápido, barato (~$0.05/1M tokens)
    #   "meta/meta-llama-3-70b-instruct"  → mais preciso
    #   "openai/gpt-4o-mini"              → disponível no Replicate, boa qualidade
    replicate_model: str = "openai/gpt-4o-mini"

    # LLM: OpenAI (fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Embeddings: "huggingface" | "openai"
    embedding_provider: str = "huggingface"
    # bge-small-en-v1.5 é muito mais leve que bge-m3 (~130MB vs ~2GB)
    # Para deploy no Streamlit Cloud, prefira bge-small
    embedding_model: str = "BAAI/bge-m3"

    # VectorStore: "local" | "cloud"
    chroma_mode: str = "local"
    chroma_persist_dir: str = "./data/processed/chroma"

    # ChromaDB Cloud (quando chroma_mode=cloud)
    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = "edurag"

    # MCP
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_log_level: str = "INFO"

    # Self-check
    self_check_threshold: float = 0.7

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Manter compatibilidade com variável legada USE_OLLAMA
    use_ollama: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instância singleton de Settings."""
    return Settings()


# ---------------------------------------------------------------------------
# ChatReplicate — wrapper ChatModel sobre o cliente nativo do Replicate.
# Definido no nível de módulo para evitar NameError ao usar variáveis de
# closure como defaults de atributos de classe (proibido no Python 3.14+).
# ---------------------------------------------------------------------------

class _ChatReplicate(BaseChatModel):
    """ChatModel mínimo que delega ao cliente nativo do Replicate."""

    model_name: str = Field(default="openai/gpt-4o-mini")
    temperature: float = Field(default=0.0)
    api_token: str = Field(default="")

    @property
    def _llm_type(self) -> str:
        return "replicate-chat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        O modelo openai/gpt-4o-mini no Replicate expõe `prompt` + `system_prompt`
        (schema Cog), não o campo `messages` da API Chat da OpenAI.
        Enviar `messages` como JSON string faz a API retornar ReplicateError (422).
        """
        import replicate as _replicate
        from replicate.exceptions import ReplicateError

        token = (self.api_token or "").strip()
        if not token:
            raise RuntimeError(
                "REPLICATE_API_TOKEN não configurado. "
                "No Streamlit Cloud: Settings → Secrets → defina REPLICATE_API_TOKEN."
            )
        _os.environ["REPLICATE_API_TOKEN"] = token

        system_parts: List[str] = []
        prompt_parts: List[str] = []
        for m in messages:
            if isinstance(m, SystemMessage):
                system_parts.append(str(m.content))
            elif isinstance(m, HumanMessage):
                prompt_parts.append(str(m.content))
            elif isinstance(m, AIMessage):
                prompt_parts.append(
                    f"[Resposta do assistente]\n{m.content}"
                )
            else:
                prompt_parts.append(str(m.content))

        system_prompt = "\n\n".join(system_parts).strip()
        prompt = "\n\n".join(prompt_parts).strip() or "Responda conforme as instruções do sistema."

        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "temperature": max(float(self.temperature), 0.01),
            "max_completion_tokens": 2048,
        }
        if system_prompt:
            input_payload["system_prompt"] = system_prompt

        try:
            output = _replicate.run(self.model_name, input=input_payload)
        except ReplicateError as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            raise RuntimeError(
                f"Erro na API do Replicate ({self.model_name}): {detail}"
            ) from exc

        if hasattr(output, "__iter__") and not isinstance(output, str):
            text = "".join(str(chunk) for chunk in output)
        else:
            text = str(output)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


def get_llm(temperature: float = 0):
    """
    Retorna o LLM configurado pelo LLM_PROVIDER:
      - "replicate" → ChatReplicate wrapper (usa REPLICATE_API_TOKEN)
      - "openai"    → ChatOpenAI (usa OPENAI_API_KEY)
      - "ollama"    → ChatOllama local (padrão para desenvolvimento)
    """
    settings = get_settings()

    provider = settings.llm_provider
    if provider == "ollama" and not settings.use_ollama:
        provider = "openai"

    if provider == "replicate":
        return _ChatReplicate(
            model_name=settings.replicate_model,
            api_token=settings.replicate_api_token,
            temperature=temperature,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
        )

    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )
