"""Тесты промптов: RULES.md, правила формата и сборка примеров."""

from pathlib import Path

from ai_scenario.models import SearchHit
from ai_scenario.rag.prompts import (
    build_prompt,
    build_repair_prompt,
    load_system_prompt,
)


def test_fallback_without_rules(tmp_path: Path):
    prompt = load_system_prompt(tmp_path / "нет_файла.md")
    assert "BI.QUBE" in prompt


def test_rules_md_used_when_present(tmp_path: Path):
    rules = tmp_path / "RULES.md"
    rules.write_text("Пиши кратко, без воды.", encoding="utf-8")
    assert load_system_prompt(rules) == "Пиши кратко, без воды."


def test_build_prompt_contains_storage_rules_and_examples():
    hit = SearchHit(
        contentid=1,
        header="Загрузка из 1С",
        intro="<p>Вступление</p>",
        step_plan="Шаг 1: Подготовка | Шаг 2: Загрузка",
        step_text="<p>т1</p> | <p>т2</p>",
        dist=0.1,
    )
    prompt = build_prompt("Составь сценарий загрузки", [hit])
    assert "Confluence storage format" in prompt
    assert "Шаг №: Название шага" in prompt
    assert "Первый этап" in prompt
    assert "На этом задача" in prompt
    assert "<example>" in prompt
    # название сценария — обычный абзац, шаги плоского сценария — <h2>
    assert "<p>Загрузка из 1С</p>" in prompt
    assert "<h2>Шаг 1: Подготовка</h2>" in prompt
    assert "<h2>Шаг 2: Загрузка</h2>" in prompt
    assert "<p>т2</p>" in prompt
    # в примере нет старого блока «План шагов», только заголовки шагов
    assert "<p><strong>План шагов:</strong>" not in prompt
    assert "Составь сценарий загрузки" in prompt


def test_staged_example_renders_stage_headings():
    hit = SearchHit(
        contentid=2,
        header="Инкрементальная загрузка",
        intro=None,
        step_plan=(
            "Первый этап: подготовка / Шаг 1: Создание"
            " | Второй этап: загрузка / Шаг 1: Запуск"
        ),
        step_text="<p>т1</p> | <p>т2</p>",
        dist=0.2,
    )
    prompt = build_prompt("Запрос", [hit])
    assert "<h2>Первый этап: подготовка</h2>" in prompt
    assert "<h3>Шаг 1: Создание</h3>" in prompt
    assert "<h2>Второй этап: загрузка</h2>" in prompt
    assert "<h3>Шаг 1: Запуск</h3>" in prompt


def test_repair_prompt_lists_errors():
    prompt = build_repair_prompt(
        "запрос", "<p>текст", ["строка 1: ошибка"]
    )
    assert "строка 1: ошибка" in prompt
    assert "<p>текст" in prompt
    assert "запрос" in prompt
