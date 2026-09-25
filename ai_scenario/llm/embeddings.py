"""Эмбеддер запросов: qwen3-embedding на Ollama:sandbox.

Векторизует только запрос пользователя: эмбеддинги сценариев уже
посчитаны внешним ресурсом и лежат в ai_ods.content_with_vector,
пересчитывать их на стороне сервиса не нужно.
"""

from openai import OpenAI

from ai_scenario.config import EmbeddingSettings, load_settings
from ai_scenario.llm.base import EmbeddingResult


class QwenEmbeddingClient:
    """Клиент embeddings.create у OpenAI-совместимого эндпоинта."""

    def __init__(self, settings: EmbeddingSettings | None = None) -> None:
        self._settings = settings or load_settings().embedding
        self._client = OpenAI(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
        )

    def embed(self, text: str) -> EmbeddingResult:
        """Вектор одного текста и число токенов запроса."""
        response = self._client.embeddings.create(
            model=self._settings.model, input=text,
        )
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", None)
        return EmbeddingResult(
            vector=response.data[0].embedding,
            total_tokens=tokens if isinstance(tokens, int) else 0,
        )
