"""Самопроверка БД: версия сервера и сводка по content_with_vector."""

import sys

from ai_scenario.db.repository import create_connection


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = create_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("select version();")
            print(cur.fetchone()[0])
            cur.execute(
                "select count(*),"
                " (select vector_dims(embedding)"
                "   from ai_ods.content_with_vector limit 1)"
                " from ai_ods.content_with_vector"
            )
            rows, dim = cur.fetchone()
            print(
                f"ai_ods.content_with_vector: {rows} строк, "
                f"размерность embedding {dim}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
