import os
from pravo_app.graph import graph

CATEGORY_CATALOG = {
    "кат1": {
        "кратко": "Коммунальные услуги",
        "полное": "Категория 1: Коммунальные услуги и общедомовое имущество",
    },
    "кат2": {
        "кратко": "Общие зоны",
        "полное": "Категория 2: Места общего пользования и придомовая территория",
    },
    "кат3": {
        "кратко": "Бездействие УК",
        "полное": "Категория 3: Действия/бездействие УК, повлекшие ущерб",
    },
    "кат4": {
        "кратко": "Комплексные случаи",
        "полное": "Категория 4: Специфичные и комплексные ситуации",
    },
    "кат5": {
        "кратко": "Финансы УК",
        "полное": "Категория 5: Долги, начисления и финансовые вопросы УК",
    },
    "кат6": {
        "кратко": "Документы данные",
        "полное": "Категория 6: Данные, документы и информационное взаимодействие",
    },
    "кат7": {
        "кратко": "Соседские конфликты",
        "полное": "Категория 7: Соседские конфликты и действия третьих лиц при попустительстве УК",
    },
    "кат8": {
        "кратко": "Гарантии подрядчики",
        "полное": "Категория 8: Страхование, гарантии и ответственность подрядчиков",
    },
    "кат9": {
        "кратко": "Экология здоровье",
        "полное": "Категория 9: Экология, санитария и здоровье",
    },
}

import json

REQUEST_LIST = []


def save_requests_json(path: str = "legal_requests.json") -> None:
    """Сохранить REQUEST_LIST в JSON."""
    data = []
    for idx, item in enumerate(REQUEST_LIST, start=1):
        data.append({"порядковый_номер": idx, **item})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_requests_json(path: str = "legal_requests.json") -> list:
    """Загрузить REQUEST_LIST из JSON."""
    global REQUEST_LIST
    with open(path, encoding="utf-8") as f:
        REQUEST_LIST = json.load(f)
    return REQUEST_LIST


def load_requests_from_md(path: str = "Генерация запросов к агенту.md") -> list:
    """Импорт запросов из markdown в REQUEST_LIST."""
    import re
    global REQUEST_LIST
    with open(path, encoding="utf-8") as f:
        text = f.read()
    cat = None
    result = []
    for line in text.split("\n"):
        m = re.match(r"### Категория (\d+):", line)
        if m:
            cat = f"кат{m.group(1)}"
            continue
        m = re.match(r"\d+\.\s+\*\*(.+?):\*\*\s*(.+)", line)
        if m and cat:
            result.append({"категория": cat, "тема": m.group(1).strip(), "запрос": m.group(2).strip()})
    REQUEST_LIST = result
    return result


def process_requests_batch(
    input_path: str = "legal_requests.json",
    output_path: str = "legal_process.json",
    limit: int | None = None,
    start_index: int = 1,
) -> list:
    """Пакетная обработка запросов и сохранение результатов в JSON."""

    requests = load_requests_json(input_path)
    if start_index < 1:
        raise ValueError("start_index must be >= 1")
    start_pos = start_index - 1
    if limit is not None:
        requests = requests[start_pos : start_pos + limit]
    else:
        requests = requests[start_pos:]
    results = []

    if requests:
        start_no = requests[0].get("порядковый_номер", start_index)
        end_no = requests[-1].get("порядковый_номер", start_index + len(requests) - 1)
        base, ext = os.path.splitext(output_path)
        if not ext:
            ext = ".json"
        output_path = f"{base}_{start_no}-{end_no}{ext}"

    for idx, item in enumerate(requests, start=1):
        query_preview = item["запрос"][:20]
        request_no = item.get("порядковый_номер", idx)
        print(f"[{request_no}] {item['категория']} | {item['тема']} | {query_preview}")
        state = {
            "query": item["запрос"],
            "batch_mode": True,
            "verbose": False,
        }
        final_state = graph.invoke(state)

        results.append(
            {
                "порядковый_номер": item.get("порядковый_номер", request_no),
                "категория": item["категория"],
                "тема": item["тема"],
                "запрос": item["запрос"],
                "ответ": final_state.get("final_answer"),
                "сгенерированный вопрос": final_state.get("clarification"),
                "сгенерированный ответ": final_state.get("clarification_answer"),
            }
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


if __name__ == "__main__":
    MD_INPUT_PATH = "Генерация запросов к агенту.md"
    JSON_INPUT_PATH = "legal_requests.json"
    JSON_OUTPUT_PATH = "legal_process.json"
    BATCH_LIMIT = 10
    START_INDEX = 14

    # load_requests_from_md(MD_INPUT_PATH)
    # save_requests_json(JSON_INPUT_PATH)

    REQUEST_LIST=load_requests_json(JSON_INPUT_PATH)
    print(f"Загружено {len(REQUEST_LIST)} запросов, сохранено в {JSON_INPUT_PATH}")

    results = process_requests_batch(
        JSON_INPUT_PATH,
        JSON_OUTPUT_PATH,
        limit=BATCH_LIMIT,
        start_index=START_INDEX,
    )
    print(f"Обработано {len(results)} запросов, сохранено в {JSON_OUTPUT_PATH}")
