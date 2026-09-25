"""Нормализация storage format: снятие экспортных артефактов Confluence.

Тексты в БД выгружены из Confluence и несут декоративные inline-стили
— color: var(--ds-text, #333333) и подобные — и служебные атрибуты
(data-uuid). Модель копирует их из примеров, а вне Confluence
undefined-переменные --ds-* откатываются к тёмному фолбэку: на тёмной
теме такой текст становится «бесцветным».

normalize_storage() снимает цветовые декларации (color,
background-color), data-* атрибуты и освобождает от обёрток
опустевшие <span>; текст и остальные стили (list-style-type,
text-align) не трогает. Применяется и к примерам промпта, и к ответу
модели — до валидации.
"""

from lxml import etree

from ai_scenario.storage.validate import parse_fragment

COLOR_PROPERTIES = frozenset({"color", "background-color"})
DATA_PREFIX = "data-"


def _clean_style(style: str) -> str:
    """Убирает цветовые декларации; если их нет — возвращает как есть."""
    declarations = style.split(";")
    kept = [
        declaration.strip()
        for declaration in declarations
        if declaration.partition(":")[0].strip().lower()
        not in COLOR_PROPERTIES
    ]
    if len(kept) == len(declarations):
        return style
    return "; ".join(kept for kept in kept if kept)


def _unwrap(element) -> None:
    """Заменяет элемент на его содержимое (текст, дети и хвост)."""
    parent = element.getparent()
    if parent is None:
        return
    index = parent.index(element)
    if element.text:
        if index == 0:
            parent.text = (parent.text or "") + element.text
        else:
            previous = parent[index - 1]
            previous.tail = (previous.tail or "") + element.text
    for child in list(element):
        parent.insert(index, child)
        index += 1
    if element.tail:
        if index > 0:
            parent[index - 1].tail = (
                (parent[index - 1].tail or "") + element.tail
            )
        else:
            parent.text = (parent.text or "") + element.tail
    parent.remove(element)


def normalize_storage(storage: str) -> str:
    """Чистый storage format; при ошибке XML возвращает вход как есть."""
    try:
        root = parse_fragment(storage)
    except etree.XMLSyntaxError:
        return storage  # сломанный XML чинит цикл ремонта

    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for name in [
            name
            for name in element.attrib
            if name.lower().startswith(DATA_PREFIX)
        ]:
            del element.attrib[name]
        style = element.get("style")
        if style:
            cleaned = _clean_style(style)
            if cleaned:
                element.set("style", cleaned)
            else:
                del element.attrib["style"]

    # Опустевшие <span> раскрываем, пока таких не останется.
    while True:
        bare = next(
            (
                el
                for el in root.iter()
                if isinstance(el.tag, str)
                and etree.QName(el).localname == "span"
                and not el.attrib
            ),
            None,
        )
        if bare is None:
            break
        _unwrap(bare)

    # Служебные обёртки-пространства имён в сериализацию не тащим:
    # используемые (макросы ac:/ri:) останутся сами.
    etree.cleanup_namespaces(root)

    return (
        (root.text or "")
        + "".join(
            etree.tostring(child, encoding="unicode") for child in root
        )
    ).strip()
