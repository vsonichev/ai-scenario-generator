"""Единственное место с SQL: векторный поиск по content_with_vector.

Эмбеддинги сценариев уже посчитаны внешним ресурсом и лежат в
ai_ods.content_with_vector рядом с контентом, поэтому поиск — это
один SQL: вектор запроса сравнивается оператором <=> (косинусная
дистанция, 1 - cos), таблица читается последовательным сканом.
"""

import psycopg2

from ai_scenario.config import load_settings
from ai_scenario.models import SearchHit

SEARCH_SQL = """
    select contentid, header, intro, step_plan, step_text,
           embedding <=> %(query)s::vector as dist
      from ai_ods.content_with_vector
     order by dist
     limit %(top_k)s
"""

DIM_SQL = (
    "select vector_dims(embedding) "
    "from ai_ods.content_with_vector limit 1"
)


def create_connection() -> psycopg2.extensions.connection:
    """Открывает соединение с PostgreSQL из настроек .env."""
    db = load_settings().db
    try:
        return psycopg2.connect(
            host=db.host,
            port=db.port,
            user=db.user,
            password=db.password,
            dbname=db.dbname,
        )
    except psycopg2.Error as error:
        raise RuntimeError(f"Не удалось подключиться к БД: {error}") from error


def _format_vector(vector: list[float]) -> str:
    """Вектор запроса в текстовый литерал для каста ::vector."""
    return "[" + ",".join(str(value) for value in vector) + "]"


def search_similar(query_vector: list[float], top_k: int) -> list[SearchHit]:
    """Топ-k сценариев с готовым контентом; dist — косинусная (1 - cos).

    Перед поиском проверяется, что размерность вектора запроса
    совпадает с размерностью embedding в таблице: если эмбеддер
    сменили, а таблицу не пересобрали, падаем с понятной ошибкой.
    """
    conn = create_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(DIM_SQL)
            row = cur.fetchone()
            if row and row[0] and len(query_vector) != row[0]:
                raise RuntimeError(
                    f"Размерность вектора запроса ({len(query_vector)}) "
                    f"не совпадает с embedding в БД ({row[0]}); "
                    "проверьте модель эмбеддингов или пересоберите таблицу"
                )
            cur.execute(
                SEARCH_SQL,
                {"query": _format_vector(query_vector), "top_k": top_k},
            )
            return [SearchHit(*row) for row in cur.fetchall()]
    finally:
        conn.close()
