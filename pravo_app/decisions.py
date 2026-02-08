"""
Условные переходы (conditional edges) графа LangGraph.

Функции возвращают имя следующего узла в зависимости от состояния.
Используются в workflow.add_conditional_edges() для маршрутизации потока.
"""
from typing import Literal

from .state import MyState


def check_need_human(state: MyState) -> Literal["вопрос пользователю", "уточнение в batch", "переформулировка"]:
    """Определяет, нужен ли уточняющий вопрос: пользователю, в batch или переформулировка."""
    clarification_cnt = state["clarification_cnt"]
    need_clarify_question = state["need_clarify_question"]
    batch_mode = state.get("batch_mode")

    if clarification_cnt > 1:
        return "переформулировка"
    if need_clarify_question:
        return "уточнение в batch" if batch_mode else "вопрос пользователю"
    return "переформулировка"


def check_search_type(state: MyState) -> Literal["поиск нпа", "поиск судебки"]:
    """Выбирает тип поиска: НПА или судебная практика по категории запроса."""
    category = state["category"].lower()
    if "нпа" in category:
        return "поиск нпа"
    if "суд" in category:
        return "поиск судебки"
    return "поиск нпа"


def check_need_re_search(state: MyState) -> Literal["классификация", "финальный ответ"]:
    """Решает: требуется ли повторный поиск или формировать финальный ответ."""
    re_search_cnt = state["re_search_cnt"]
    need_re_search_flag = state["need_re_search"]

    if re_search_cnt > 1:
        return "финальный ответ"
    if need_re_search_flag:
        return "классификация"
    return "финальный ответ"
