from langgraph.graph import END, START, StateGraph

from .decisions import check_need_human, check_need_re_search, check_search_type
from .nodes import (
    answer_node,
    clarify_node,
    classify_node,
    final_answer_node,
    human_clarify_node,
    query_concat_node,
    reflect_node,
    rewrite_node,
    search_court_node,
    search_npa_node,
    setup_node,
)
from .state import MyState


def build_graph() -> StateGraph:
    workflow = StateGraph(MyState)
    workflow.add_node("старт", setup_node)
    workflow.add_node("уточнение", clarify_node)
    workflow.add_node("вопрос пользователю", human_clarify_node)
    workflow.add_node("сбор запроса", query_concat_node)
    workflow.add_node("переформулировка", rewrite_node)
    workflow.add_node("классификация", classify_node)
    workflow.add_node("поиск нпа", search_npa_node)
    workflow.add_node("поиск судебки", search_court_node)
    workflow.add_node("черновой ответ", answer_node)
    workflow.add_node("самопроверка", reflect_node)
    workflow.add_node("финальный ответ", final_answer_node)

    workflow.add_edge(START, "старт")
    workflow.add_edge("старт", "уточнение")
    workflow.add_conditional_edges("уточнение", check_need_human)
    workflow.add_edge("вопрос пользователю", "сбор запроса")
    workflow.add_edge("сбор запроса", "переформулировка")
    workflow.add_edge("переформулировка", "классификация")
    workflow.add_conditional_edges("классификация", check_search_type)
    workflow.add_edge("поиск нпа", "черновой ответ")
    workflow.add_edge("поиск судебки", "черновой ответ")
    workflow.add_edge("черновой ответ", "самопроверка")
    workflow.add_conditional_edges("самопроверка", check_need_re_search)
    workflow.add_edge("финальный ответ", END)

    return workflow


graph = build_graph().compile()
