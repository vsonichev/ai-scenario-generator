"""Генерация текста через Ollama (gpt-oss:20b) — продовый провайдер."""

from openai import OpenAI

from ai_scenario.config import ChatSettings, load_settings
from ai_scenario.llm.base import CompletionResult, completion_from_response


class OllamaChatClient:
    """gpt-oss:20b на Ollama:local.

    OpenAI-совместимый эндпоинт Ollama не принимает reasoning_effort,
    поэтому уровень рассуждения для gpt-oss передаётся директивой
    "Reasoning: ..." в начале системного сообщения.
    """

    def __init__(self, settings: ChatSettings | None = None) -> None:
        self._settings = settings or load_settings().chat
        self._client = OpenAI(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
        )

    def complete(self, system: str, user: str) -> CompletionResult:
        system = f"Reasoning: {self._settings.reasoning_effort}\n\n{system}"
        response = self._client.chat.completions.create(
            model=self._settings.model,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return completion_from_response(response)
