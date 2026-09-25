"""Тесты предпросмотра storage format (rendering.preview_page)."""

from ai_scenario.rendering import preview_page


def test_preview_page_contains_storage():
    page = preview_page("Заголовок & детали", "<h2>Сценарий</h2>")
    assert page.startswith("<!doctype html>")
    assert "<title>Заголовок &amp; детали</title>" in page
    assert "<h2>Сценарий</h2>" in page
