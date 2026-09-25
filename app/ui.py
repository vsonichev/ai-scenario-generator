"""Streamlit-интерфейс генератора сценариев BI.QUBE.

Запуск: uv run streamlit run app/ui.py
Одна страница: запрос → найденные эталоны → сценарий в Confluence
storage format. Логика целиком в ai_scenario.rag.pipeline; здесь
только ввод, запуск и отображение.
"""

from datetime import datetime
from pathlib import Path

import streamlit as st

from ai_scenario.config import ConfigError, load_settings
from ai_scenario.models import ScenarioResult
from ai_scenario.rag.pipeline import generate_scenario

st.set_page_config(
    page_title="BI.QUBE Scenario Generator",
    page_icon="⚡",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"

for key in ("result", "query"):
    st.session_state.setdefault(key, None)


# ── Вспомогательное ─────────────────────────────────────────────────


def default_top_k() -> int:
    """TOP_K из настроек, если конфигурация уже доступна."""
    try:
        return load_settings().top_k
    except ConfigError:
        return 3


def generate(user_query: str, top_k: int) -> ScenarioResult | None:
    """Запуск пайплайна; ошибки конфигурации и сервисов — в UI."""
    try:
        return generate_scenario(user_query, top_k=top_k)
    except ConfigError as error:
        st.error(str(error))
    except Exception as error:  # noqa: BLE001 — граница UI: показываем любую
        st.error(f"Ошибка генерации: {error}")
    return None


def save_scenario(result: ScenarioResult, user_query: str) -> Path:
    """Сохраняет .xml (storage) и .html (предпросмотр) в outputs/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005 — локальное время
    slug = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in user_query
    )[:50]
    base = OUTPUT_DIR / f"{stamp}_{slug.strip()}"
    base.with_suffix(".xml").write_text(result.storage, encoding="utf-8")
    base.with_suffix(".html").write_text(result.html, encoding="utf-8")
    return base


# ── Интерфейс ───────────────────────────────────────────────────────

st.title("⚡ BI.QUBE Scenario Generator")
st.caption(
    "Опишите задачу — сервис найдёт похожие сценарии в базе и "
    "сгенерирует новый в формате Confluence storage."
)

with st.form("generation_form"):
    user_query = st.text_area(
        "Описание задачи",
        placeholder=(
            "Например: Полная загрузка справочника из 1С в Greenplum\n"
            "Или: Инкрементальная загрузка документа в PostgreSQL"
        ),
        height=120,
        help=(
            "Тип загрузки (полная / инкрементальная / "
            "секционированная), источник и приёмник."
        ),
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        top_k = st.slider(
            "Сколько эталонов задействовать для контекста?",
            min_value=1,
            max_value=7,
            value=default_top_k(),
            help="Сколько похожих сценариев подтянуть как образцы",
        )
    with col2:
        auto_save = st.checkbox("💾 Автосохранение", value=False)
    with col3:
        show_usage = st.checkbox("💸 Расход токенов", value=True)

    submitted = st.form_submit_button(
        "🚀 Сгенерировать", type="primary", use_container_width=True
    )

if submitted:
    if not user_query.strip():
        st.error("Введите описание задачи.")
    else:
        with st.status(
            "🔄 Генерация сценария...", expanded=False
        ) as status:
            result = generate(user_query, top_k)
            if result is not None:
                st.session_state.result = result
                st.session_state.query = user_query
                status.update(label="✅ Готово", state="complete")
            else:
                status.update(label="Ошибка генерации", state="error")

        if auto_save and st.session_state.result is not None:
            base = save_scenario(
                st.session_state.result, user_query
            )
            st.info(f"💾 Сохранено: `{base.name}.xml` + `.html`")


# ── Результат ───────────────────────────────────────────────────────

if st.session_state.result:
    result: ScenarioResult = st.session_state.result
    saved_query: str = st.session_state.query or result.query
    now = datetime.now()  # noqa: DTZ005 — локальное время в имени файла

    st.markdown("---")

    left, right = st.columns([3, 1])
    with left:
        st.subheader("📄 Результат")
    with right:
        st.metric("Время", f"{result.elapsed_seconds:.1f} с")

    if result.validation_errors:
        st.error(
            "⚠ Валидация storage format не пройдена "
            f"({len(result.validation_errors)} ошибок после ремонта):\n\n"
            + "\n".join(f"- {e}" for e in result.validation_errors)
        )
    else:
        st.success("✅ Валидация storage format пройдена")

    # Найденные эталоны — видно, на чём строилась генерация;
    # пригодится при настройке качества поиска и примеров.
    with st.expander("🔍 Найденные сценарии-примеры", expanded=False):
        for hit in result.hits:
            st.markdown(
                f"`{hit.dist:.6f}` **{hit.header}**"
                f" · contentid {hit.contentid}"
            )

    if show_usage:
        with st.expander("💸 Расход токенов", expanded=False):
            st.code(result.usage.report(), language="text")

    tab_view, tab_src = st.tabs(["👁️ Просмотр", "📝 Storage format"])
    with tab_view:
        st.html(result.html)
    with tab_src:
        st.code(result.storage, language="xml")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 Сохранить", use_container_width=True):
            base = save_scenario(result, saved_query)
            st.success(f"`{base.name}.xml` + `.html`")
    with col2:
        st.download_button(
            "📥 Скачать .xml",
            data=result.storage,
            file_name=f"scenario_{now:%Y%m%d_%H%M%S}.xml",
            mime="application/xml",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "📥 Скачать .html",
            data=result.html,
            file_name=f"preview_{now:%Y%m%d_%H%M%S}.html",
            mime="text/html",
            use_container_width=True,
        )
    with col4:
        if st.button("🔄 Новый запрос", use_container_width=True):
            for key in ("result", "query"):
                st.session_state[key] = None
            st.rerun()
