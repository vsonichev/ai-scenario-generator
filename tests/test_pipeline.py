"""Пайплайн на подставных клиентах и заглушке векторного поиска."""

from ai_scenario.llm.base import CompletionResult, EmbeddingResult
from ai_scenario.models import SearchHit
from ai_scenario.rag import pipeline


class FakeEmbeddings:
    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.1, 0.2], total_tokens=5)


class FlakyChat:
    """Первый ответ невалиден, второй — валидный storage format."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system: str, user: str) -> CompletionResult:
        self.calls += 1
        if self.calls == 1:
            return CompletionResult(
                text="<p>незакрытый", prompt_tokens=1, total_tokens=2,
            )
        return CompletionResult(
            text=(
                "<p>Сценарий</p><p>Вступление.</p>"
                "<h2>Шаг 1: Подготовка</h2><p>Текст шага.</p>"
            ),
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )


class BadChat:
    """Всегда невалидный ответ — ремонт не помогает."""

    def complete(self, system: str, user: str) -> CompletionResult:
        return CompletionResult(
            text="<p>всё ещё плохо", prompt_tokens=1, total_tokens=2,
        )


def _patch_hits(monkeypatch) -> None:
    hits = [
        SearchHit(
            contentid=1,
            header="Загрузка",
            intro=None,
            step_plan="Шаг 1",
            step_text="<p>т</p>",
            dist=0.1,
        )
    ]
    monkeypatch.setattr(
        pipeline.repository, "search_similar", lambda vector, top_k: hits
    )


def test_repair_loop_fixes_storage(monkeypatch) -> None:
    _patch_hits(monkeypatch)
    chat = FlakyChat()
    result = pipeline.generate_scenario(
        "составь сценарий",
        chat=chat,
        embeddings=FakeEmbeddings(),
        top_k=1,
    )
    assert chat.calls == 2
    assert result.validation_errors == []
    assert result.storage.startswith("<p>")
    assert "<h2>Шаг 1: Подготовка</h2>" in result.html
    # эмбеддинг (5) + генерация (2) + ремонт (15)
    assert result.usage.totals().total_tokens == 22


def test_unrepairable_storage_keeps_best(monkeypatch) -> None:
    _patch_hits(monkeypatch)
    result = pipeline.generate_scenario(
        "составь сценарий",
        chat=BadChat(),
        embeddings=FakeEmbeddings(),
        top_k=1,
    )
    assert result.validation_errors
    assert result.storage == "<p>всё ещё плохо"
