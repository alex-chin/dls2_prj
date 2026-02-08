"""
Модуль работы с юридическими запросами: импорт, пакетная обработка через агента, экспорт в markdown.

Типичный сценарий:
  1. import_md — импорт запросов из markdown в legal_requests.json
  2. batch — обработка через pravo_app.graph, сохранение в legal_process_*.json
  3. print — сборка legal_process_*.json в единый legal_process.md
"""
import os
import json
import glob
import re

from pravo_app.graph import graph

# Справочник категорий: ключ (кат1..кат9) → краткое и полное наименование
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

# Глобальный список запросов (заполняется load_requests_from_md / load_requests_json)
REQUEST_LIST = []


def _parse_legal_process_filename(path: str) -> tuple[int, int]:
    """Извлечь диапазон номеров из имени файла legal_process_N-M.json для сортировки."""
    base = os.path.basename(path)
    m = re.search(r"legal_process_(\d+)-(\d+)\.json", base)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (0, 0)


def legal_process_print(
    mask: str = "legal_process_*.json",
    output_path: str = "legal_process.md",
) -> str:
    """
    Преобразует файлы по маске legal_process_*.json в единый markdown-файл legal_process.md.

    Формат каждой записи:
    # {порядковый номер}. {категория}. {тема}
    > {Запрос}
    **Сгенерированный запрос** {сгенерированный вопрос}
    **Сгенерированный ответ** {сгенерированный ответ}
    {ответ}
    """
    files = sorted(glob.glob(mask), key=_parse_legal_process_filename)
    if not files:
        return output_path

    # Объединяем записи из всех файлов, сортируем по порядковому номеру
    all_entries = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_entries.extend(data)
            else:
                all_entries.append(data)

    all_entries.sort(key=lambda e: e.get("порядковый_номер", 0))

    lines = []
    for e in all_entries:
        no = e.get("порядковый_номер", "?")
        cat_key = e.get("категория", "")
        cat = CATEGORY_CATALOG.get(cat_key, {}).get("кратко", cat_key)  # «кат1» → «Коммунальные услуги»
        tema = e.get("тема", "")
        zapros = e.get("запрос", "")
        gen_q = e.get("сгенерированный вопрос")
        gen_a = e.get("сгенерированный ответ")
        otvet = e.get("ответ", "")

        lines.append(f"# {no}. {cat}. {tema}")
        lines.append("")
        lines.append(f"> {zapros}")
        lines.append("")
        if gen_q:
            lines.append(f"**Сгенерированный запрос** {gen_q}")
            lines.append("")
        if gen_a is not None:
            lines.append(f"**Сгенерированный ответ** {gen_a}")
            lines.append("")
        if otvet:
            lines.append(otvet)
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip())

    return output_path


def save_requests_json(path: str = "legal_requests.json") -> None:
    """Сохранить REQUEST_LIST в JSON. Добавляет порядковый_номер при записи."""
    data = []
    for idx, item in enumerate(REQUEST_LIST, start=1):
        data.append({"порядковый_номер": idx, **item})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_requests_json(path: str = "legal_requests.json") -> list:
    """Загрузить данные из JSON в глобальный REQUEST_LIST."""
    global REQUEST_LIST
    with open(path, encoding="utf-8") as f:
        REQUEST_LIST = json.load(f)
    return REQUEST_LIST


def load_requests_from_md(path: str = "Генерация запросов к агенту.md") -> list:
    """
    Импорт запросов из markdown в REQUEST_LIST.

    Ожидаемый формат: заголовки ### Категория N:, строки вида «N. **Тема:** запрос».
    """
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
    """
    Пакетная обработка запросов через pravo_app.graph и сохранение в legal_process_N-M.json.

    Через limit и start_index задаётся срез запросов. Имя выходного файла формируется
    автоматически по диапазону номеров (например, legal_process_1-10.json).
    """
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
        # Формируем имя вида legal_process_1-10.json
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
        final_state = graph.invoke(state)  # вызов LangGraph-агента

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
    # Выбор действия: print — md из json; import_md — md → json; batch — обработка через агента
    ACTION = "print"  # "print" | "import_md" | "batch"

    MD_INPUT_PATH = "legal requests/Генерация запросов к агенту.md"
    JSON_INPUT_PATH = "legal requests/legal_requests.json"
    JSON_OUTPUT_PATH = "legal_process.json"
    BATCH_LIMIT = 1
    START_INDEX = 135

    if ACTION == "print":
        legal_process_print()

    elif ACTION == "import_md":
        load_requests_from_md(MD_INPUT_PATH)
        save_requests_json(JSON_INPUT_PATH)
        print("Импорт из md выполнен")

    elif ACTION == "batch":
        REQUEST_LIST = load_requests_json(JSON_INPUT_PATH)
        print(f"Загружено {len(REQUEST_LIST)} запросов")
        results = process_requests_batch(
            JSON_INPUT_PATH,
            JSON_OUTPUT_PATH,
            limit=BATCH_LIMIT,
            start_index=START_INDEX,
        )
        print(f"Обработано {len(results)} запросов")
