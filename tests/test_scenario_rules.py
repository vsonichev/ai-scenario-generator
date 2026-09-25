"""Тесты правил структуры сценария (rag.scenario_rules)."""

from ai_scenario.rag.scenario_rules import scenario_structure_errors

FLAT = (
    "<p>Полная загрузка справочника</p>"
    "<p>Вступление.</p>"
    "<h2>Шаг 1: Создание команды</h2><p>Текст.</p>"
    "<h2>Шаг 2: Проверка</h2><p>Текст.</p>"
    "<p>На этом задача выполнена.</p>"
)

STAGED = (
    "<p>Инкрементальная загрузка</p>"
    "<p>Вступление.</p>"
    "<h2>Первый этап: подготовка</h2>"
    "<h3>Шаг 1: Создание</h3><p>Текст.</p>"
    "<h3>Шаг 2: Запуск</h3><p>Текст.</p>"
    "<h2>Второй этап: загрузка</h2>"
    "<h3>Шаг 1: Загрузка</h3><p>Текст.</p>"
)


def test_valid_flat():
    assert scenario_structure_errors(FLAT) == []


def test_valid_staged_numbering_restarts():
    assert scenario_structure_errors(STAGED) == []


def test_title_must_be_paragraph():
    storage = (
        "<h2>Полная загрузка справочника</h2>"
        "<p>Вступление.</p>"
        "<h2>Шаг 1: Создание команды</h2><p>Текст.</p>"
    )
    errors = scenario_structure_errors(storage)
    assert any("начинается с заголовка" in error for error in errors)


def test_h1_forbidden():
    storage = (
        "<h1>Название</h1><p>Вступление.</p>"
        "<h2>Шаг 1: А</h2><p>т</p>"
    )
    errors = scenario_structure_errors(storage)
    assert any("<h1>" in error for error in errors)


def test_plan_section_forbidden():
    storage = (
        "<p>Сценарий</p>"
        "<p><strong>План шагов:</strong> Шаг 1: А | Шаг 2: Б</p>"
        "<h2>Шаг 1: А</h2><p>т</p>"
    )
    errors = scenario_structure_errors(storage)
    assert any("План шагов" in error for error in errors)


def test_missing_step_headings():
    errors = scenario_structure_errors("<p>Сценарий</p><p>Текст.</p>")
    assert any("заголовка шага" in error for error in errors)


def test_mixed_step_levels():
    storage = (
        "<p>Сценарий</p>"
        "<h2>Шаг 1: А</h2><p>т</p>"
        "<h3>Шаг 2: Б</h3><p>т</p>"
    )
    errors = scenario_structure_errors(storage)
    assert any("одного уровня" in error for error in errors)


def test_staged_requires_stage_heading():
    storage = "<p>Сценарий</p><h3>Шаг 1: А</h3><p>т</p>"
    errors = scenario_structure_errors(storage)
    assert any("этапа" in error for error in errors)


def test_step_heading_level_h4_forbidden():
    storage = "<p>Сценарий</p><h4>Шаг 1: А</h4><p>т</p>"
    errors = scenario_structure_errors(storage)
    assert any("только <h2> или <h3>" in error for error in errors)


def test_non_sequential_steps():
    storage = (
        "<p>Сценарий</p>"
        "<h2>Шаг 1: А</h2><p>т</p>"
        "<h2>Шаг 3: Б</h2><p>т</p>"
    )
    errors = scenario_structure_errors(storage)
    assert any("Шаг 2" in error for error in errors)


def test_non_sequential_inside_stage():
    storage = (
        "<p>Сценарий</p>"
        "<h2>Первый этап: подготовка</h2>"
        "<h3>Шаг 1: А</h3><p>т</p>"
        "<h3>Шаг 3: Б</h3><p>т</p>"
    )
    errors = scenario_structure_errors(storage)
    assert any("Шаг 2" in error for error in errors)


def test_broken_xml_ignored_here():
    assert scenario_structure_errors("<p>незакрыт") == []
