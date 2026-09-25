"""Валидация Confluence storage format для файлов.

Использование:
    uv run python scripts/validate_storage.py FILE [...]

Код возврата: 0 — все файлы валидны, 1 — есть ошибки.
Годится и для примеров из БД (выгрузите step_text в файл): атрибуты
вроде data-uuid из выгрузок разрешены, проверяется XML, белый список
элементов и вложенность.
"""

import sys
from pathlib import Path

from ai_scenario.storage.validate import validate_storage


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = argv if argv is not None else sys.argv[1:]
    if not files:
        print(
            "Использование: uv run python scripts/validate_storage.py "
            "FILE [...]",
            file=sys.stderr,
        )
        return 2

    failed = False
    for name in files:
        text = Path(name).read_text(encoding="utf-8")
        errors = validate_storage(text)
        if errors:
            failed = True
            print(f"{name}: НЕ ПРОЙДЕНО ({len(errors)} ошибок)")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"{name}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
