"""Самопроверка LLM: короткий ответ активного провайдера."""

import sys

from ai_scenario.config import load_settings
from ai_scenario.llm.factory import create_chat_client


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    settings = load_settings()
    client = create_chat_client()
    result = client.complete(
        "Отвечай кратко, по-русски.",
        "Ответь одним словом: связь есть?",
    )
    print(f"Провайдер: {settings.chat.provider}, модель: {settings.chat.model}")
    print(f"Ответ: {result.text}")
    print(
        f"Токены: prompt {result.prompt_tokens}, "
        f"ответ {result.completion_tokens}, всего {result.total_tokens}"
    )


if __name__ == "__main__":
    main()
