"""Настройки сервиса: единая загрузка .env и проверка переменных."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Настройки не заполнены или некорректны."""


@dataclass(frozen=True)
class DbSettings:
    """Параметры подключения к PostgreSQL с pgvector."""

    host: str
    port: int
    user: str
    password: str
    dbname: str


@dataclass(frozen=True)
class ChatSettings:
    """Параметры LLM генерации: glm в тестах, ollama в проде."""

    provider: str
    base_url: str
    api_key: str
    model: str
    temperature: float
    reasoning_effort: str


@dataclass(frozen=True)
class EmbeddingSettings:
    """Параметры эмбеддера запросов (Ollama:sandbox, qwen3-embedding)."""

    base_url: str
    api_key: str
    model: str


@dataclass(frozen=True)
class Settings:
    """Полная конфигурация сервиса на один запуск."""

    db: DbSettings
    chat: ChatSettings
    embedding: EmbeddingSettings
    top_k: int


def _require(*names: str) -> dict[str, str]:
    """Значения переменных; ConfigError со списком пропущенных."""
    values = {name: os.getenv(name, "") for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigError(
            "Не заданы переменные окружения: "
            + ", ".join(missing)
            + ". Заполните .env по образцу .env.example"
        )
    return values


def _db_settings() -> DbSettings:
    env = _require("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
    try:
        port = int(env["DB_PORT"])
    except ValueError:
        raise ConfigError("DB_PORT должен быть целым числом") from None
    return DbSettings(
        host=env["DB_HOST"],
        port=port,
        user=env["DB_USER"],
        password=env["DB_PASSWORD"],
        dbname=env["DB_NAME"],
    )


def _chat_settings(provider: str) -> ChatSettings:
    """Параметры выбранного провайдера генерации из .env."""
    if provider == "glm":
        env = _require("GLM_URL", "GLM_KEY")
        return ChatSettings(
            provider=provider,
            base_url=env["GLM_URL"],
            api_key=env["GLM_KEY"],
            model=os.getenv("GLM_MODEL", "glm-5.3"),
            temperature=float(os.getenv("GLM_TEMPERATURE", "0.1")),
            reasoning_effort=os.getenv("GLM_REASONING_EFFORT", "low"),
        )
    if provider == "ollama":
        env = _require("OLLAMA_LOCAL_URL", "OLLAMA_LOCAL_KEY")
        return ChatSettings(
            provider=provider,
            base_url=env["OLLAMA_LOCAL_URL"],
            api_key=env["OLLAMA_LOCAL_KEY"],
            model=os.getenv("OLLAMA_LOCAL_MODEL", "gpt-oss:20b"),
            temperature=float(os.getenv("OLLAMA_LOCAL_TEMPERATURE", "0.1")),
            reasoning_effort=os.getenv(
                "OLLAMA_LOCAL_REASONING_EFFORT", "low"
            ),
        )
    raise ConfigError(
        f"LLM_PROVIDER={provider!r} не поддерживается: "
        "ожидается glm или ollama"
    )


def _embedding_settings() -> EmbeddingSettings:
    env = _require("OLLAMA_SANDBOX_URL", "OLLAMA_SANDBOX_KEY")
    return EmbeddingSettings(
        base_url=env["OLLAMA_SANDBOX_URL"],
        api_key=env["OLLAMA_SANDBOX_KEY"],
        model=os.getenv("OLLAMA_SANDBOX_EMBEDDING", "qwen3-embedding:4b"),
    )


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Читает .env один раз и валидирует настройки (fail-fast)."""
    load_dotenv(PROJECT_ROOT / ".env")
    provider = os.getenv("LLM_PROVIDER", "glm").strip().lower()
    try:
        top_k = int(os.getenv("TOP_K", "3"))
    except ValueError:
        raise ConfigError("TOP_K должен быть целым числом") from None
    return Settings(
        db=_db_settings(),
        chat=_chat_settings(provider),
        embedding=_embedding_settings(),
        top_k=top_k,
    )
