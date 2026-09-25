"""Промпты: системный промпт, правила storage format и сборка примеров.

Системный промпт (роль и стиль) берётся из docs/RULES.md — файл
подхватывается автоматически при появлении; пока его нет, используется
встроенный fallback. Правила формата вывода (Confluence storage
format) кодифицированы здесь, в STORAGE_RULES, чтобы промпт и
валидатор (storage/validate.py) не расходились.
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from ai_scenario.config import PROJECT_ROOT
from ai_scenario.models import SearchHit
from ai_scenario.storage.clean import normalize_storage

RULES_PATH = PROJECT_ROOT / "docs" / "RULES.md"

FALLBACK_SYSTEM_PROMPT = (
    "Ты — технический писатель фреймворка BI.QUBE. Твоя задача "
    "писать тексты сценариев использования фреймворка."
    "Отвечай на русском языке в том же стиле, что и в примерах: "
    "заголовок сценария, вступление, план шагов и подробный текст "
    "каждого шага."
)

STORAGE_RULES = (
    "Формат ответа — Confluence storage format (XHTML). Правила:\n"
    "- Выводи только XHTML-фрагмент, готовый для вставки в тело "
    "страницы Confluence: без <html>, <body>, без markdown, без "
    "пояснений и ```-блоков.\n"
    "- Фрагмент обязан быть корректным XML: закрывай все теги, "
    "пустые элементы делай самозакрытыми (<br />, <hr />), значения "
    "атрибутов — в двойных кавычках.\n"
    "- Используй только элементы: p, h1-h6, ul, ol, li, table, "
    "thead, tbody, tr, td, th, strong, em, u, s, code, pre, "
    "blockquote, a, span, div, br, hr.\n"
    "- Спецсимволы в тексте экранируй: & как &amp;, < как &lt;, "
    "> как &gt;. Именованные HTML-сущности (&nbsp; и подобные) "
    "запрещены — используй числовые (&#160;) или обычный пробел.\n"
    "- Не используй inline-цвета (color, background-color) и "
    "служебные атрибуты (data-*): оформление задаёт тема Confluence.\n"
    "- Не переноси служебные атрибуты из примеров (data-uuid и т.п.).\n"
    "- Макросы, если нужны, оформляй так:\n"
    '<ac:structured-macro ac:name="info" ac:schema-version="1">'
    "<ac:rich-text-body>…</ac:rich-text-body>"
    "</ac:structured-macro> — для info, note, warning, panel;\n"
    '<ac:structured-macro ac:name="code" ac:schema-version="1">'
    '<ac:parameter ac:name="language">sql</ac:parameter>'
    "<ac:plain-text-body><![CDATA[SELECT 1;]]></ac:plain-text-body>"
    "</ac:structured-macro> — для кода;\n"
    '<ac:structured-macro ac:name="status" ac:schema-version="1">'
    '<ac:parameter ac:name="title">Готово</ac:parameter>'
    '<ac:parameter ac:name="colour">Green</ac:parameter>'
    "</ac:structured-macro> — для статусов.\n"
    "- Структура сценария:\n"
    "  1) название сценария — обычный абзац <p> (не заголовок);\n"
    "  2) вступление — обычный текст в <p>;\n"
    "  3) плоский сценарий: каждый шаг — заголовок "
    "<h2>Шаг №: Название шага</h2>, за ним текст шага;\n"
    "  4) двухуровневый сценарий (с этапами): этап — заголовок "
    "<h2>Первый этап: Название этапа</h2>, шаги внутри этапа — "
    "<h3>Шаг №: Название шага</h3>, нумерация шагов в каждом этапе "
    "с 1;\n"
    "  5) заголовок h1 не используется; раздел «План шагов» "
    "(перечисление шагов) не включается;\n"
    "  6) в конце — абзац-вывод: «На этом задача <название сценария> "
    "выполнена.»\n"
)


def load_system_prompt(path: Path | None = None) -> str:
    """docs/RULES.md, если файл есть и не пустой, иначе fallback."""
    rules_path = path if path is not None else RULES_PATH
    if rules_path.exists():
        text = rules_path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return FALLBACK_SYSTEM_PROMPT


STEP_SEP = " | "
STAGE_SEP = " / "


def _normalize_title(title: str, index: int) -> str:
    """«Шаг 5: Х» → «Шаг {index + 1}: Х»; без префикса — как есть."""
    match = re.match(r"^Шаг\s+\d+\s*:\s*(.*)$", title)
    name = match.group(1).strip() if match else title.strip()
    if not name:
        name = f"Шаг {index + 1}"
    return f"Шаг {index + 1}: {name}"


def _split_stage(item: str) -> tuple[str | None, str]:
    """«Этап / Шаг №: Название» → (этап, шаг); без « / » → (None, item)."""
    if STAGE_SEP in item:
        stage, step = item.split(STAGE_SEP, 1)
        return stage.strip(), step.strip()
    return None, item


def _structure_blocks(
    step_plan: str | None, step_text: str | None
) -> list[str]:
    """Блоки шагов и этапов из агрегированных строк БД.

    step_plan — пункты через « | ». Пункт вида «Этап / Шаг №: Название»
    задаёт двухуровневый сценарий: этап → <h2>, шаги внутри → <h3>
    с нумерацией заново; обычный пункт — плоский сценарий, шаг → <h2>.
    step_text — тексты через « | », число частей совпадает с пунктами
    (проверено на всех 29 строках). Склейка позиционная, нумерация
    шагов нормализуется.
    """
    items = [
        i.strip() for i in (step_plan or "").split(STEP_SEP) if i.strip()
    ]
    texts = [
        t.strip() for t in (step_text or "").split(STEP_SEP) if t.strip()
    ]
    blocks: list[str] = []
    stage: str | None = None
    step_index = 0
    for index, item in enumerate(items[: len(texts)]):
        item_stage, title = _split_stage(item)
        if item_stage is not None and item_stage != stage:
            blocks.append(f"<h2>{xml_escape(item_stage)}</h2>")
            step_index = 0
        stage = item_stage
        step_index += 1
        level = 3 if stage else 2
        heading = xml_escape(_normalize_title(title, step_index - 1))
        blocks.append(f"<h{level}>{heading}</h{level}>")
        blocks.append(normalize_storage(texts[index]))
    return blocks


def _example_block(hit: SearchHit) -> str:
    """Собирает пример сценария в storage format из строки таблицы."""
    parts = [f"<p>{xml_escape(hit.header)}</p>"]
    if hit.intro:
        parts.append(normalize_storage(hit.intro.strip()))
    parts.extend(_structure_blocks(hit.step_plan, hit.step_text))
    return "<example>\n" + "\n".join(parts) + "\n</example>"


def build_prompt(query: str, examples: list[SearchHit]) -> str:
    """Промпт: правила формата + примеры в storage format + запрос."""
    return (
        STORAGE_RULES
        + "\nНиже примеры существующих сценариев в storage format.\n\n"
        + "\n\n".join(_example_block(hit) for hit in examples)
        + "\n\nНапиши новый сценарий для запроса в том же стиле и в "
        "том же формате. Ответ — только storage format:\n"
        + query
    )


def build_repair_prompt(query: str, storage: str, errors: list[str]) -> str:
    """Промпт ремонта: ошибки валидатора + текущий текст."""
    listed = "\n".join(f"- {error}" for error in errors)
    return (
        f"Сценарий для запроса «{query}» написан в Confluence storage "
        "format, но валидатор нашёл ошибки:\n"
        f"{listed}\n\n"
        "Текущий текст:\n<storage>\n"
        + storage
        + "\n</storage>\n\n"
        "Верни исправленную версию целиком, тем же storage format: "
        "только XHTML-фрагмент, без пояснений и ```-блоков."
    )
