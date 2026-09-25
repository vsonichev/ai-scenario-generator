"""Генерация текста через GLM (Z.ai) — тестовый провайдер LLM_PROVIDER=glm."""

from openai import OpenAI

from ai_scenario.config import ChatSettings, load_settings
from ai_scenario.llm.base import CompletionResult, completion_from_response


class GlmChatClient:
    """GLM: reasoning_effort параметром, thinking отключён через extra_body."""

    def __init__(self, settings: ChatSettings | None = None) -> None:
        self._settings = settings or load_settings().chat
        self._client = OpenAI(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
        )

    def complete(self, system: str, user: str) -> CompletionResult:
        response = self._client.chat.completions.create(
            model=self._settings.model,
            temperature=self._settings.temperature,
            reasoning_effort=self._settings.reasoning_effort,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            extra_body={"thinking": {"type": "disabled"}},
        )
        return completion_from_response(response)
