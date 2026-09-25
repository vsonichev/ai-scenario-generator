"""Контракты клиентов LLM и разбор ответов OpenAI-совместимых API."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EmbeddingResult:
    """Вектор текста и число токенов запроса к эмбеддеру."""

    vector: list[float]
    total_tokens: int = 0


@dataclass(frozen=True)
class CompletionResult:
    """Ответ LLM и расход токенов из usage ответа API.

    reasoning_text — «размышления» reasoning-моделей (GLM), если
    сервер их прислал; reasoning_tokens входят в completion_tokens.
    """

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    reasoning_text: str | None = None


class ChatClient(Protocol):
    """Клиент генерации текста (OpenAI-совместимый API)."""

    def complete(self, system: str, user: str) -> CompletionResult: ...


class EmbeddingClient(Protocol):
    """Клиент модели эмбеддингов."""

    def embed(self, text: str) -> EmbeddingResult: ...


def _count(value: Any) -> int:
    """Приводит значение из usage к int, None и мусор считает нулём."""
    return value if isinstance(value, int) else 0


def completion_from_response(response: Any) -> CompletionResult:
    """Собирает CompletionResult из ответа chat.completions."""
    message = response.choices[0].message
    usage = getattr(response, "usage", None)
    details = getattr(usage, "completion_tokens_details", None)
    return CompletionResult(
        text=message.content or "",
        prompt_tokens=_count(getattr(usage, "prompt_tokens", None)),
        completion_tokens=_count(getattr(usage, "completion_tokens", None)),
        reasoning_tokens=_count(getattr(details, "reasoning_tokens", None)),
        total_tokens=_count(getattr(usage, "total_tokens", None)),
        reasoning_text=getattr(message, "reasoning_content", None),
    )
