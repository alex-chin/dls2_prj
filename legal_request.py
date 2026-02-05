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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(REQUEST_LIST, f, ensure_ascii=False, indent=2)


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


if __name__ == "__main__":
    load_requests_from_md()
    save_requests_json()
    print(f"Загружено {len(REQUEST_LIST)} запросов, сохранено в legal_requests.json")
