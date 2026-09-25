"""Тесты валидатора Confluence storage format."""

from ai_scenario.storage.validate import validate_storage


def test_valid_fragment():
    storage = (
        "<h2>Сценарий</h2>"
        "<p>Вступление: A &amp; B &lt;C&gt;.</p>"
        '<ul style="list-style-type: square;">'
        "<li>Шаг один</li><li>Шаг два</li></ul>"
    )
    assert validate_storage(storage) == []


def test_valid_macro_and_table():
    storage = (
        '<ac:structured-macro ac:name="info" ac:schema-version="1">'
        "<ac:rich-text-body><p>Важно.</p></ac:rich-text-body>"
        "</ac:structured-macro>"
        "<table><tbody><tr><td>ячейка</td></tr></tbody></table>"
    )
    assert validate_storage(storage) == []


def test_unclosed_tag():
    errors = validate_storage("<p>абзац")
    assert any("XML" in error for error in errors)


def test_named_entity_rejected():
    errors = validate_storage("<p>пробел&nbsp;тут</p>")
    assert errors


def test_element_not_in_whitelist():
    errors = validate_storage("<p>текст <script>alert(1)</script></p>")
    assert any("script" in error for error in errors)


def test_event_attribute_rejected():
    errors = validate_storage('<p onclick="x()">текст</p>')
    assert any("onclick" in error for error in errors)


def test_javascript_href_rejected():
    errors = validate_storage('<a href="javascript:x()">ссылка</a>')
    assert any("href" in error for error in errors)


def test_li_outside_list():
    errors = validate_storage("<p><li>пункт</li></p>")
    assert any("<li>" in error for error in errors)


def test_text_inside_list_forbidden():
    errors = validate_storage("<ul>текст<li>пункт</li></ul>")
    assert any("<ul>" in error for error in errors)


def test_ri_outside_macro():
    errors = validate_storage('<p><ri:page ri:content-title="X"/></p>')
    assert any("ri:" in error for error in errors)


def test_macro_without_name():
    errors = validate_storage(
        "<ac:structured-macro><ac:rich-text-body>"
        "<p>т</p></ac:rich-text-body></ac:structured-macro>"
    )
    assert any("ac:name" in error for error in errors)


def test_data_attributes_allowed():
    storage = '<ul><li data-uuid="abc">пункт</li></ul>'
    assert validate_storage(storage) == []


def test_empty():
    assert validate_storage("   ") != []
