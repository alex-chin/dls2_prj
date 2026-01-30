from typing import Dict, List, Tuple


def format_docs(search_results: List[Dict]) -> str:
    tpl = ""
    for i, r in enumerate(search_results):
        title = r.get("title", "")
        doc_text = r.get("doc_text", "")[:15000]
        tpl += f"[Source {i}]: {title}\n{doc_text}\n\n"
    return tpl


def format_links(search_results: List[Dict]) -> str:
    links = []
    for r in search_results:
        links.append(f"{r['title']} [{r['href']}\n\n")
    return "\n".join(links)


def format_dialog(messages: List[Tuple[str, str]]) -> str:
    tpl = ""
    for m in messages:
        tpl += f"[{m[0]}]: {m[1]}\n\n"
    return tpl
