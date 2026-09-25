"""Выбор провайдеров LLM по настройкам .env."""

from ai_scenario.config import load_settings
from ai_scenario.llm.base import ChatClient, EmbeddingClient
from ai_scenario.llm.embeddings import QwenEmbeddingClient
from ai_scenario.llm.glm import GlmChatClient
from ai_scenario.llm.ollama import OllamaChatClient


def create_chat_client() -> ChatClient:
    """GLM в тестах (LLM_PROVIDER=glm), Ollama:gpt-oss в проде."""
    provider = load_settings().chat.provider
    if provider == "glm":
        return GlmChatClient()
    return OllamaChatClient()


def create_embedding_client() -> EmbeddingClient:
    """Эмбеддер один для всех сред: qwen3-embedding на Ollama:sandbox."""
    return QwenEmbeddingClient()
