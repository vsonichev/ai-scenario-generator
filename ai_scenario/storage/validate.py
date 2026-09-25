"""Валидатор Confluence storage format.

Storage format — XHTML-фрагмент с макросами Confluence (пространства
имён ac: urn:ac:xhtml и ri: urn:ri:xhtml). Фрагмент разбирается lxml
с обёрткой <root> с объявлением пространств — так же, как это делает
сам Confluence, — и проверяется по правилам:

1. корректный XML: теги закрыты, сущности только XML (&amp; и числовые);
2. белый список элементов: XHTML-подмножество + макросы ac:* / ri:*;
3. запрещены событийные атрибуты on* и схемы javascript:/data: в href/src;
4. правила вложенности: li — в ul/ol, td — в tr, ac:parameter — в макрос;
5. текст не может быть напрямую внутри ul/ol/table/tr/макроса.

validate_storage() возвращает список человекочитаемых ошибок; пустой
список — фрагмент валиден. Для файлов с диска есть CLI:
uv run python scripts/validate_storage.py FILE [...]
"""

from lxml import etree

AC_NS = "urn:ac:xhtml"
RI_NS = "urn:ri:xhtml"
XHTML_NS = "http://www.w3.org/1999/xhtml"

WRAPPER_OPEN = f'<root xmlns:ac="{AC_NS}" xmlns:ri="{RI_NS}">'
WRAPPER_CLOSE = "</root>"

XHTML_ELEMENTS = frozenset({
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "br", "hr",
    "strong", "em", "u", "s", "sub", "sup",
    "code", "pre", "blockquote", "a", "span", "div",
    "table", "caption", "colgroup", "col",
    "thead", "tbody", "tfoot", "tr", "td", "th",
})

AC_ELEMENTS = frozenset({
    "ac:structured-macro", "ac:parameter",
    "ac:rich-text-body", "ac:plain-text-body",
    "ac:link", "ac:link-body", "ac:image", "ac:emoticon",
    "ac:task-list", "ac:task", "ac:task-id", "ac:task-status",
    "ac:task-body", "ac:placeholder",
})

RI_ELEMENTS = frozenset({
    "ri:page", "ri:space", "ri:attachment", "ri:url",
    "ri:user", "ri:shortcut",
})

ALLOWED_ELEMENTS = XHTML_ELEMENTS | AC_ELEMENTS | RI_ELEMENTS

PARENT_RULES = {
    "li": frozenset({"ul", "ol"}),
    "tr": frozenset({"table", "thead", "tbody", "tfoot"}),
    "td": frozenset({"tr"}),
    "th": frozenset({"tr"}),
    "caption": frozenset({"table"}),
    "colgroup": frozenset({"table"}),
    "col": frozenset({"colgroup"}),
    "ac:parameter": frozenset({"ac:structured-macro"}),
    "ac:rich-text-body": frozenset({"ac:structured-macro"}),
    "ac:plain-text-body": frozenset({"ac:structured-macro"}),
    "ac:link-body": frozenset({"ac:link"}),
    "ac:task": frozenset({"ac:task-list"}),
    "ac:task-id": frozenset({"ac:task"}),
    "ac:task-status": frozenset({"ac:task"}),
    "ac:task-body": frozenset({"ac:task"}),
}

# Элементы, внутрь которых текст напрямую попадать не может.
TEXT_FORBIDDEN = frozenset({
    "ul", "ol", "table", "thead", "tbody", "tfoot", "tr", "colgroup",
    "ac:structured-macro", "ac:task-list", "ac:task",
})


def _tag_name(element) -> str | None:
    """Имя тега с префиксом ac:/ri: или None при чужом пространстве."""
    qname = etree.QName(element)
    if qname.namespace is None or qname.namespace == XHTML_NS:
        return qname.localname
    if qname.namespace == AC_NS:
        return f"ac:{qname.localname}"
    if qname.namespace == RI_NS:
        return f"ri:{qname.localname}"
    return None


def _attribute_errors(element, tag: str, line: int | None) -> list[str]:
    where = f"строка {line}: " if line else ""
    errors = []
    for name, value in element.attrib.items():
        low = name.lower()
        if low.startswith("on"):
            errors.append(
                f"{where}<{tag}>: запрещён событийный атрибут {name}"
            )
        elif low in ("href", "src") and value.strip().lower().startswith(
            ("javascript:", "data:")
        ):
            errors.append(
                f"{where}<{tag}>: запрещённая схема в {name}=\"{value}\""
            )
    return errors


def _has_direct_text(element) -> bool:
    if element.text and element.text.strip():
        return True
    return any(child.tail and child.tail.strip() for child in element)


def parse_fragment(storage: str) -> etree._Element:
    """Разбирает фрагмент storage format с обёрткой <root>.

    Обёртка объявляет пространства имён ac/ri, как это делает
    Confluence; корень — служебный, его содержимое и есть фрагмент.
    """
    return etree.fromstring(
        (WRAPPER_OPEN + storage.strip() + WRAPPER_CLOSE).encode("utf-8")
    )


def validate_storage(storage: str) -> list[str]:
    """[] — валидный storage format, иначе список ошибок."""
    text = (storage or "").strip()
    if not text:
        return ["Пустой фрагмент storage format."]
    try:
        root = parse_fragment(text)
    except etree.XMLSyntaxError as error:
        return [f"Некорректный XML: {error}"]

    errors: list[str] = []
    if len(root) == 0:
        return ["Фрагмент не содержит XHTML-элементов."]

    for element in root.iter():
        if element is root or not isinstance(element.tag, str):
            continue  # сама обёртка, комментарии и инструкции разбора
        tag = _tag_name(element)
        line = getattr(element, "sourceline", None)
        where = f"строка {line}: " if line else ""
        if tag is None:
            errors.append(
                f"{where}элемент <{element.tag}> в чужом пространстве имён"
            )
            continue
        if tag not in ALLOWED_ELEMENTS:
            errors.append(
                f"{where}элемент <{tag}> не входит в белый список "
                "storage format"
            )
            continue
        errors.extend(_attribute_errors(element, tag, line))

        parent = element.getparent()
        if parent is not None:
            parent_tag = None if parent is root else _tag_name(parent)
            allowed = PARENT_RULES.get(tag)
            if allowed and parent_tag not in allowed:
                expected = ", ".join(sorted(allowed))
                errors.append(
                    f"{where}<{tag}> должен быть внутри <{expected}>, "
                    f"а найден внутри <{parent_tag or 'root'}>"
                )
            if tag.startswith("ri:") and not (
                parent_tag or ""
            ).startswith("ac:"):
                errors.append(
                    f"{where}<{tag}> допустим только внутри макроса ac:*"
                )

        if tag in TEXT_FORBIDDEN and _has_direct_text(element):
            errors.append(
                f"{where}текст не может быть напрямую внутри <{tag}>"
            )

        if (
            tag == "ac:structured-macro"
            and f"{{{AC_NS}}}name" not in element.attrib
        ):
            errors.append(f"{where}ac:structured-macro без ac:name")

    return errors
