import os
from typing import Any, Dict, List, Tuple

from langgraph.types import interrupt

from .config import GIGACHAT_MODEL
from .formatters import format_dialog, format_docs, format_links
from .llm import ask_giga
from .prompts import (
    classification_prompt,
    clarification_prompt,
    clarification_prompt_batch,
    final_answer_prompt,
    query_concat_prompt,
    query_rewrite_prompt,
    rag_prompt, rag_prompt_only_link,
    reflection_prompt,
)
from .search import call_court_api, call_npa_api
from .state import MyState


def ask_human(query: str) -> str:
    return input(query)


def setup_node(state: MyState) -> MyState:
    state_update = dict()
    state_update["search_query"] = state["query"]
    state_update["messages"] = [("user", state["query"])]
    state_update["clarification"] = None
    state_update["clarification_answer"] = None
    state_update["need_clarify_question"] = None
    state_update["category"] = None
    state_update["docs"] = []
    state_update["answers"] = []
    state_update["final_answer"] = None
    state_update["need_re_search"] = None
    state_update["re_search_cnt"] = 0
    state_update["clarification_cnt"] = 0
    state_update["verbose"] = state.get("verbose", False)
    state_update["batch_mode"] = state.get("batch_mode", os.getenv("PRAVO_BATCH_MODE", "0") == "1")
    return state_update


def clarify_node(state: MyState) -> MyState:
    query = state["search_query"]
    prompt = clarification_prompt.format(query=query)
    gen = ask_giga(prompt, GIGACHAT_MODEL)

    state_update = dict()
    state_update["need_clarify_question"] = False if (len(gen) < 10 and "ок" in gen.lower()) else True
    state_update["messages"] = [("tool_clarify", gen)]
    state_update["clarification"] = gen
    state_update["clarification_cnt"] = state["clarification_cnt"] + 1

    if state["verbose"]:
        print("clarify_node:", gen)

    return state_update


def batch_clarify_node(state: MyState) -> MyState:
    query = state["search_query"]
    prompt = clarification_prompt_batch.format(query=query)
    gen = ask_giga(prompt, GIGACHAT_MODEL)

    message = ("tool_batch_clarify", gen)

    state_update = dict()
    state_update["messages"] = [message]
    state_update["clarification_answer"] = gen
    state_update["need_clarify_question"] = False

    if state["verbose"]:
        print("batch_clarify_node:", gen)

    return state_update


def human_clarify_node(state: MyState) -> MyState:
    use_input = os.getenv("PRAVO_USE_INPUT", "0") == "1"
    value = ask_human(state["clarification"]) if use_input else interrupt(state["clarification"])

    message = ("user", value)

    state_update = dict()
    state_update["messages"] = [message]
    state_update["clarification_answer"] = value

    if state["verbose"]:
        print("human_clarify_node:", value)

    return state_update


def query_concat_node(state: MyState) -> MyState:
    dialog = format_dialog(state["messages"])
    prompt = query_concat_prompt.format(dialog=dialog)
    gen = ask_giga(prompt, GIGACHAT_MODEL)

    message = ("tool_concat", gen)

    state_update = dict()
    state_update["search_query"] = gen
    state_update["messages"] = [message]

    if state["verbose"]:
        print("query_concat_node:", gen)

    return state_update


def rewrite_node(state: MyState) -> MyState:
    query = state["search_query"]
    prompt = query_rewrite_prompt.format(query=query)
    rewritten = ask_giga(prompt, GIGACHAT_MODEL)

    message = ("tool_rewrite", rewritten)

    state_update = dict()
    state_update["search_query"] = rewritten
    state_update["messages"] = [message]

    if state["verbose"]:
        print("rewrite_node:", message)

    return state_update


def classify_node(state: MyState) -> MyState:
    query = state["search_query"]
    prompt = classification_prompt.format(query=query)
    category = ask_giga(prompt, GIGACHAT_MODEL)

    message = ("tool_classify", category)

    state_update = dict()
    state_update["category"] = category
    state_update["messages"] = [message]
    state_update["docs"] = []

    if state["verbose"]:
        print("classify_node:", category)

    return state_update


def search_npa_node(state: MyState) -> MyState:
    results = call_npa_api(state["search_query"])

    message_text = format_links(results)
    message = ("result_search_npa", message_text)

    state_update = dict()
    state_update["docs"] = results
    state_update["messages"] = [message]

    if state["verbose"]:
        print("search_npa_node:", message_text)

    return state_update


def search_court_node(state: MyState) -> MyState:
    results = call_court_api(state["search_query"])

    message_text = format_links(results)
    message = ("result_search_court", message_text)

    state_update = dict()
    state_update["docs"] = results
    state_update["messages"] = [message]

    if state["verbose"]:
        print("search_court_node:", message_text)

    return state_update


def answer_node(state: MyState) -> MyState:
    query = state["search_query"]
    docs = state.get("docs", [])
    if not docs:
        answer = "Извините, по вашему запросу не удалось найти подходящие документы."
    else:
        prompt = rag_prompt_only_link.format(query=query, docs=format_docs(docs))
        answer = ask_giga(prompt, GIGACHAT_MODEL)

    answer_data = {
        "title": query,
        "doc_text": answer,
    }

    message = ("tool_rag", answer)

    state_update = dict()
    state_update["answers"] = [answer_data]
    state_update["messages"] = [message]

    if state["verbose"]:
        print("answer_node:", answer)

    return state_update


def reflect_node(state: MyState) -> MyState:
    answer = state["answers"][-1]
    prompt = reflection_prompt.format(query=state["search_query"], response=answer["doc_text"])
    gen = ask_giga(prompt, GIGACHAT_MODEL)

    message = ("tool_reflect", gen)

    state_update = dict()
    state_update["need_re_search"] = False if (len(gen) < 10 and "ок" in gen.lower()) else True
    if state_update["need_re_search"]:
        state_update["search_query"] = gen

    state_update["messages"] = [message]
    state_update["re_search_cnt"] = state["re_search_cnt"] + 1

    if state["verbose"]:
        print("reflect_node:", gen)

    return state_update


def final_answer_node(state: MyState) -> MyState:
    query = state["query"]
    docs = state["answers"]
    if not docs:
        answer = "Извините, по вашему запросу не удалось найти подходящие документы."
    elif len(docs) == 1:
        answer = docs[0]["doc_text"]
    else:
        prompt = final_answer_prompt.format(query=query, docs=format_docs(docs))
        answer = ask_giga(prompt, GIGACHAT_MODEL)

    message = ("tool_final_answer", answer)

    state_update = dict()
    state_update["final_answer"] = answer
    state_update["messages"] = [message]

    if state["verbose"]:
        print("answer_node:", answer)

    return state_update


