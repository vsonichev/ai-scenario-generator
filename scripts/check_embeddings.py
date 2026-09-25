"""Самопроверка эмбеддера: размерность вектора тестовой строки."""

import sys

from ai_scenario.config import load_settings
from ai_scenario.llm.embeddings import QwenEmbeddingClient


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = QwenEmbeddingClient()
    result = client.embed("Проверка подключения к Ollama:sandbox")
    print(f"Модель: {load_settings().embedding.model}")
    print(f"Размерность эмбеддинга: {len(result.vector)}")
    print(f"Первые 5 значений: {result.vector[:5]}")
    print(f"Токенов: {result.total_tokens}")


if __name__ == "__main__":
    main()
