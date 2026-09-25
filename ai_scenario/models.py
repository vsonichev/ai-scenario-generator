"""Модели домена: найденный сценарий-пример и результат генерации."""

from dataclasses import dataclass

from ai_scenario.usage import UsageTracker


@dataclass(frozen=True)
class SearchHit:
    """Строка ai_ods.content_with_vector и дистанция до запроса."""

    contentid: int
    header: str
    intro: str | None
    step_plan: str | None
    step_text: str | None
    dist: float


@dataclass
class ScenarioResult:
    """Итог генерации: примеры, storage format, валидация и токены."""

    query: str
    hits: list[SearchHit]
    storage: str
    validation_errors: list[str]
    html: str
    usage: UsageTracker
    elapsed_seconds: float = 0.0
