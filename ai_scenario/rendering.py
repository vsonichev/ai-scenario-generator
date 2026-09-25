"""HTML-обёртка для предпросмотра storage format в браузере.

Storage format — это XHTML: знакомые теги браузер рендерит, а макросы
ac:* показывает как неизвестные элементы (текст внутри их виден).
Стили темы-независимые (Canvas/CanvasText): страница читается и в
светлой, и в тёмной теме. Для точной картинки сценарий нужно смотреть
в Confluence.
"""

import html

HTML_PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {
    margin: 0 auto;
    padding: 2rem 1rem;
    max-width: 50rem;
    font: 16px/1.6 system-ui, sans-serif;
    background: Canvas;
    color: CanvasText;
    color-scheme: light dark;
  }
  pre {
    background: rgb(127 127 127 / 0.15);
    padding: 0.75rem 1rem;
    border-radius: 8px;
    overflow-x: auto;
  }
  code {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 0.9em;
  }
  h1, h2, h3 { line-height: 1.25; }
  hr {
    border: 0;
    border-top: 1px solid rgb(127 127 127 / 0.4);
    margin: 2rem 0;
  }
</style>
</head>
<body>
{body}
</body>
</html>
"""


def preview_page(title: str, storage: str) -> str:
    """Полная HTML-страница с фрагментом storage format внутри."""
    page = HTML_PAGE.replace("{title}", html.escape(title))
    return page.replace("{body}", storage)
