"""Суммарный учёт токенов LLM за один запуск генерации сценария.

Трекер собирает токены по этапам: эмбеддинг запроса пользователя
(Ollama:sandbox) и ответ модели генерации (glm или ollama — см.
LLM_PROVIDER). Сводка печатается в CLI и попадает в ScenarioResult.
Запросы, на которые сервер не прислал usage, считаются нулевыми.
"""

from dataclasses import dataclass, field

from ai_scenario.llm.base import CompletionResult


@dataclass
class UsageRecord:
    """Токены одного этапа работы сервиса."""

    stage: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0


@dataclass
class UsageTracker:
    """Копит токены по этапам и печатает сводку за запуск."""

    records: list[UsageRecord] = field(default_factory=list)

    def add_embedding(self, stage: str, model: str, total_tokens: int) -> None:
        """Записывает токены эмбеддинга (у него только total_tokens)."""
        self.records.append(
            UsageRecord(
                stage=stage,
                model=model,
                total_tokens=total_tokens,
            )
        )

    def add_chat(
        self, stage: str, model: str, result: CompletionResult
    ) -> None:
        """Записывает токены ответа модели генерации."""
        self.records.append(
            UsageRecord(
                stage=stage,
                model=model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                reasoning_tokens=result.reasoning_tokens,
                total_tokens=result.total_tokens,
            )
        )

    def totals(self) -> UsageRecord:
        """Сумма токенов по всем записям за запуск.

        reasoning_tokens входят в completion_tokens, поэтому вторично
        их не прибавляем.
        """
        total = UsageRecord(stage="Итого", model="")
        for record in self.records:
            total.prompt_tokens += record.prompt_tokens
            total.completion_tokens += record.completion_tokens
            total.reasoning_tokens += record.reasoning_tokens
            total.total_tokens += record.total_tokens
        return total

    def report(self) -> str:
        """Многострочная сводка: этапы, модели, токены и итог."""
        lines = ["Расход токенов LLM:"]
        for record in self.records:
            if record.total_tokens:
                tokens = f"всего {record.total_tokens}"
                if record.completion_tokens:
                    tokens = (
                        f"prompt {record.prompt_tokens} + "
                        f"ответ {record.completion_tokens} "
                        f"= {record.total_tokens}"
                    )
                if record.reasoning_tokens:
                    tokens += f" (рассуждения {record.reasoning_tokens})"
            else:
                tokens = "usage не получен"
            lines.append(f"  {record.stage} — {record.model}: {tokens}")
        total = self.totals()
        summary = (
            f"Итого за запуск: {total.total_tokens} токенов "
            f"(prompt {total.prompt_tokens}, "
            f"ответ {total.completion_tokens}"
        )
        if total.reasoning_tokens:
            summary += f", рассуждения {total.reasoning_tokens}"
        lines.append(summary + ")")
        return "\n".join(lines)
