"""Тесты учёта токенов UsageTracker."""

from ai_scenario.llm.base import CompletionResult
from ai_scenario.usage import UsageTracker


def test_report_and_totals():
    tracker = UsageTracker()
    tracker.add_embedding(
        "векторный поиск: запрос", "qwen3-embedding:4b", 12
    )
    tracker.add_chat(
        "генерация сценария",
        "glm-5.3",
        CompletionResult(
            text="ok",
            prompt_tokens=100,
            completion_tokens=30,
            reasoning_tokens=10,
            total_tokens=130,
        ),
    )
    total = tracker.totals()
    assert total.total_tokens == 142
    report = tracker.report()
    assert "векторный поиск: запрос" in report
    assert "рассуждения 10" in report
    assert "Итого за запуск: 142 токенов" in report


def test_missing_usage_counts_zero():
    tracker = UsageTracker()
    tracker.add_chat("генерация", "glm-5.3", CompletionResult(text=""))
    assert tracker.totals().total_tokens == 0
    assert "usage не получен" in tracker.report()
