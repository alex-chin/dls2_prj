from typing import Any, Dict


def run_graph(graph, state: Dict[str, Any], mode: str = "debug") -> None:
    if mode not in {"debug", "simple"}:
        raise ValueError("mode must be 'debug' or 'simple'")

    stage_by_node = {
        "поиск нпа": "запрос в web",
        "поиск судебки": "запрос в web",
        "вопрос пользователю": "запрос информации от пользователя",
        "__interrupt__": "запрос информации от пользователя",
        "черновой ответ": "думаю",
        "самопроверка": "оцениваю",
    }

    final_answer = None

    for step_result in graph.stream(state, stream_mode="updates"):
        if mode == "simple":
            for node_name, updated_state in step_result.items():
                stage = stage_by_node.get(node_name)
                if stage:
                    print(stage)
                if node_name == "финальный ответ" and hasattr(updated_state, "get"):
                    final_answer = updated_state.get("final_answer")
            continue

        print("--- ШАГ ---")
        for node_name, updated_state in step_result.items():
            print(f"Выполнен узел: {node_name}")
            if not hasattr(updated_state, "get"):
                print(f"  Interrupt payload: {updated_state}")
                print("-" * 20)
                continue
            if node_name == "финальный ответ":
                final_answer = updated_state.get("final_answer")
            print(f"  Текущий search_query: {updated_state.get('search_query', 'N/A')}")
            print(f"  Текущая category: {updated_state.get('category', 'N/A')}")
            print(f"  Текущий answer: {updated_state.get('answer', 'N/A')[:100]}...")
            print(f"  need_clarify_question: {updated_state.get('need_clarify_question', 'N/A')}")
            print(f"  need_re_search: {updated_state.get('need_re_search', 'N/A')}")
            print(f"  clarification_cnt: {updated_state.get('clarification_cnt', 'N/A')}")
            print(f"  re_search_cnt: {updated_state.get('re_search_cnt', 'N/A')}")
            messages = updated_state.get("messages", [])
            if messages:
                print("  Последние сообщения:")
                for msg in messages[-3:]:
                    print(f"    {msg}")
            print("-" * 20)

    if final_answer:
        print("=== FINAL ANSWER ===")
        print(final_answer)
