"""Правила структуры сценария поверх storage format.

Структура BI.QUBE:
- название сценария и вступление — обычные абзацы <p>: сценарий не
  начинается с заголовка, h1 не используется;
- плоский сценарий: каждый шаг — заголовок <h2>Шаг №: Название</h2>;
- двухуровневый: этап — <h2>Название этапа</h2>, шаги в этапе —
  <h3>Шаг №: Название</h3>, нумерация шагов в каждом этапе с 1;
- раздел «План шагов» запрещён. Заключительный абзац-вывод
  («На этом задача … выполнена») необязателен и не проверяется.

Ошибки этой проверки попадают в тот же цикл ремонта, что и ошибки
storage format.
"""

import re

from lxml import etree

from ai_scenario.storage.validate import parse_fragment

PLAN_MARKER_RE = re.compile(r"план\s+шагов", re.IGNORECASE)
STEP_HEADING_RE = re.compile(r"^Шаг\s+(\d+)\s*:\s*(\S.*)$")
HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
STEP_LEVELS = frozenset({"h2", "h3"})


def scenario_structure_errors(storage: str) -> list[str]:
    """[] — структура сценария соблюдена, иначе список ошибок."""
    try:
        root = parse_fragment(storage)
    except etree.XMLSyntaxError:
        return []  # XML-ошибки уже отдаёт validate_storage

    errors: list[str] = []
    headings: list[tuple[str, str, int | None]] = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        line = getattr(element, "sourceline", None)
        where = f"строка {line}: " if line else ""
        text = (element.text or "").strip()
        tail = (element.tail or "").strip()
        if PLAN_MARKER_RE.search(text) or PLAN_MARKER_RE.search(tail):
            errors.append(
                f"{where}раздел «План шагов» не должен попадать "
                "в сценарий"
            )
        local = etree.QName(element).localname
        if local in HEADINGS and text:
            if local == "h1":
                errors.append(
                    f"{where}заголовок <h1> не используется: название "
                    "сценария — обычный абзац <p>"
                )
            headings.append((local, text, line))

    first = next((el for el in root if isinstance(el.tag, str)), None)
    if first is not None and etree.QName(first).localname in HEADINGS:
        errors.append(
            "сценарий начинается с заголовка: название сценария и "
            "вступление должны быть обычными абзацами <p>"
        )

    steps = [
        (tag, text, line)
        for tag, text, line in headings
        if STEP_HEADING_RE.match(text)
    ]
    if not steps:
        errors.append(
            "не найдено ни одного заголовка шага в формате "
            "«Шаг №: Название шага»"
        )
        return errors

    levels = {tag for tag, _, _ in steps}
    if not levels <= STEP_LEVELS:
        errors.append("заголовки шагов — только <h2> или <h3>")
    if len(levels) > 1:
        errors.append(
            "заголовки шагов должны быть одного уровня: в плоском "
            "сценарии <h2>, в двухуровневом <h3>"
        )
    staged = "h3" in levels
    if staged and not any(tag == "h2" for tag, _, _ in headings):
        errors.append(
            "в двухуровневом сценарии нет ни одного названия этапа <h2>"
        )

    # Нумерация: в плоском сценарии сквозная, в двухуровневом —
    # заново с 1 в каждом этапе (новый сегмент — каждая нешаговая h2).
    sequences: list[list[tuple[int, int | None]]] = [[]]
    for tag, text, line in headings:
        match = STEP_HEADING_RE.match(text)
        if match:
            sequences[-1].append((int(match.group(1)), line))
        elif staged and tag == "h2":
            sequences.append([])
    for segment in sequences:
        for position, (number, line) in enumerate(segment, start=1):
            if number != position:
                where = f"строка {line}: " if line else ""
                errors.append(
                    f"{where}нумерация шагов: ожидался «Шаг {position}», "
                    f"найден «Шаг {number}»"
                )
                break  # по одной ошибке на этап
    return errors
