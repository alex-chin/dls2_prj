"""
Форматирование данных для передачи в LLM и отображения пользователю.

Функции преобразуют структурированные результаты поиска и диалог
в текстовые строки, подходящие для промптов RAG.
"""
from typing import Dict, List, Tuple


def format_docs(search_results: List[Dict]) -> str:
    """Собирает документы в текст для RAG-промпта: [Source N]: title + doc_text (до 15К символов)."""
    tpl = ""
    for i, r in enumerate(search_results):
        title = r.get("title", "")
        doc_text = r.get("doc_text", "")[:15000]
        tpl += f"[Source {i}]: {title}\n{doc_text}\n\n"
    return tpl


def format_links(search_results: List[Dict]) -> str:
    """Формирует список ссылок: title [href] для записи в messages."""
    links = []
    for r in search_results:
        links.append(f"{r['title']} [{r['href']}\n\n")
    return "\n".join(links)


def format_dialog(messages: List[Tuple[str, str]]) -> str:
    """Преобразует диалог (роль, текст) в текст для query_concat_prompt."""
    tpl = ""
    for m in messages:
        tpl += f"[{m[0]}]: {m[1]}\n\n"
    return tpl
