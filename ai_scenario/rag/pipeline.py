"""Генерация сценария: поиск примеров → промпт → LLM → валидация.

Единственная точка входа сервиса — generate_scenario(): по запросу
пользователя находится топ-k похожих сценариев (pgvector по готовым
эмбеддингам ai_ods.content_with_vector, векторизуется только запрос),
примеры передаются LLM как образцы стиля. Ответ генерируется сразу в
Confluence storage format и проверяется валидатором; при ошибках
модель чинит их по списку (до max_repairs попыток, принимается
кандидат только если он лучше текущего).
"""

import re
from time import perf_counter

from ai_scenario import rendering
from ai_scenario.config import load_settings
from ai_scenario.db import repository
from ai_scenario.llm.base import (
    ChatClient,
    CompletionResult,
    EmbeddingClient,
)
from ai_scenario.llm.factory import (
    create_chat_client,
    create_embedding_client,
)
from ai_scenario.models import ScenarioResult
from ai_scenario.rag.prompts import (
    build_prompt,
    build_repair_prompt,
    load_system_prompt,
)
from ai_scenario.rag.scenario_rules import scenario_structure_errors
from ai_scenario.storage.clean import normalize_storage
from ai_scenario.storage.validate import validate_storage
from ai_scenario.usage import UsageTracker

FENCED_RE = re.compile(r"^```[\w-]*\s*\n(.*)\n```\s*$", re.DOTALL)


def _validation_errors(storage: str) -> list[str]:
    """Ошибки storage format и структуры сценария одним списком."""
    return validate_storage(storage) + scenario_structure_errors(storage)


def _to_storage(text: str) -> str:
    """Ответ модели → чистый storage format: без fence и артефактов."""
    return normalize_storage(_strip_wrapping_fence(text))


def _strip_wrapping_fence(text: str) -> str:
    """Снимает обёртку всего ответа в ```-блок.

    Снимаем только если внешние ``` не парные с внутренними
    (нечётное число) — иначе в ответе есть свои блоки кода.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    fences = [
        line for line in stripped.splitlines()
        if line.lstrip().startswith("```")
    ]
    if len(fences) % 2:
        fenced = FENCED_RE.match(stripped)
        if fenced:
            return fenced.group(1)
    return text


def generate_scenario(
    query: str,
    *,
    chat: ChatClient | None = None,
    embeddings: EmbeddingClient | None = None,
    top_k: int | None = None,
    max_repairs: int = 1,
) -> ScenarioResult:
    """Полный цикл генерации по запросу пользователя.

    Клиенты можно подставить снаружи (тесты, будущий UI); по
    умолчанию берутся из фабрики по LLM_PROVIDER. max_repairs —
    сколько раз отправлять модели ошибки валидатора на исправление.
    """
    settings = load_settings()
    chat = chat if chat is not None else create_chat_client()
    embeddings = (
        embeddings if embeddings is not None else create_embedding_client()
    )
    top_k = settings.top_k if top_k is None else top_k
    tracker = UsageTracker()

    started = perf_counter()
    embedded = embeddings.embed(query)
    tracker.add_embedding(
        "векторный поиск: запрос",
        settings.embedding.model,
        embedded.total_tokens,
    )
    hits = repository.search_similar(embedded.vector, top_k)

    system_prompt = load_system_prompt()
    completion: CompletionResult = chat.complete(
        system_prompt, build_prompt(query, hits),
    )
    tracker.add_chat("генерация сценария", settings.chat.model, completion)

    storage = _to_storage(completion.text)
    errors = _validation_errors(storage)
    for attempt in range(1, max_repairs + 1):
        if not errors:
            break
        completion = chat.complete(
            system_prompt,
            build_repair_prompt(query, storage, errors),
        )
        tracker.add_chat(
            f"ремонт storage format ({attempt})",
            settings.chat.model,
            completion,
        )
        candidate = _to_storage(completion.text)
        candidate_errors = _validation_errors(candidate)
        if not candidate_errors or len(candidate_errors) < len(errors):
            storage, errors = candidate, candidate_errors

    return ScenarioResult(
        query=query,
        hits=hits,
        storage=storage,
        validation_errors=errors,
        html=rendering.preview_page(query, storage),
        usage=tracker,
        elapsed_seconds=perf_counter() - started,
    )
