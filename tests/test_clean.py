"""Тесты нормализации storage format (storage.clean)."""

from ai_scenario.storage.clean import normalize_storage


def test_removes_color_and_unwraps_span():
    storage = (
        "<p><span style=\"color:var(--ds-text,#333333);\">"
        "В меню выбрать «Staging»</span></p>"
    )
    assert normalize_storage(storage) == "<p>В меню выбрать «Staging»</p>"


def test_preserves_text_and_tails():
    storage = "<p>до <span style=\"color:#333\">серый</span> после</p>"
    assert normalize_storage(storage) == "<p>до серый после</p>"


def test_nested_spans():
    storage = (
        "<p><span style=\"color:#333\"><span> пробел </span></span></p>"
    )
    assert normalize_storage(storage) == "<p> пробел </p>"


def test_keeps_non_color_styles_untouched():
    storage = (
        '<ul style="list-style-type: square;"><li>пункт</li></ul>'
        '<p style="text-align: left;">текст</p>'
    )
    assert normalize_storage(storage) == storage


def test_drops_only_color_in_mixed_style():
    storage = '<p style="color: red; text-align: left;">т</p>'
    assert (
        normalize_storage(storage) == '<p style="text-align: left">т</p>'
    )


def test_removes_data_attributes():
    storage = '<ul><li data-uuid="abc">пункт</li></ul>'
    assert normalize_storage(storage) == "<ul><li>пункт</li></ul>"


def test_broken_xml_passthrough():
    assert normalize_storage("<p>незакрыт") == "<p>незакрыт"
