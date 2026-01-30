from typing import Literal

from .state import MyState


def check_need_human(state: MyState) -> Literal["вопрос пользователю", "переформулировка"]:
    clarification_cnt = state["clarification_cnt"]
    need_clarify_question = state["need_clarify_question"]

    if clarification_cnt > 1:
        return "переформулировка"
    if need_clarify_question:
        return "вопрос пользователю"
    return "переформулировка"


def check_search_type(state: MyState) -> Literal["поиск нпа", "поиск судебки"]:
    category = state["category"].lower()
    if "нпа" in category:
        return "поиск нпа"
    if "суд" in category:
        return "поиск судебки"
    return "поиск нпа"


def check_need_re_search(state: MyState) -> Literal["классификация", "финальный ответ"]:
    re_search_cnt = state["re_search_cnt"]
    need_re_search_flag = state["need_re_search"]

    if re_search_cnt > 1:
        return "финальный ответ"
    if need_re_search_flag:
        return "классификация"
    return "финальный ответ"
