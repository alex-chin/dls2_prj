"""
Поиск правовой информации во внешних источниках.

Провайдеры: DuckDuckGo (DDGS) + trafilatura для извлечения текста,
Garant API для НПА. call_npa_api / call_court_api — точки входа для узлов графа.
"""
import os
from typing import Any, Dict, List, Protocol

import requests
from ddgs import DDGS
import trafilatura


class SearchProvider(Protocol):
    """Протокол провайдера поиска: метод search возвращает список документов {title, href, doc_text}."""

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        ...


class DdgsSearchProvider:
    """Поиск через DuckDuckGo + извлечение текста страниц через trafilatura."""

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        results = DDGS().text(query, max_results=max_results)
        for r in results:
            try:
                doc_html = trafilatura.fetch_url(r["href"])
                doc_text = trafilatura.extract(doc_html)
                r["doc_html"] = doc_html
                r["doc_text"] = doc_text
            except Exception as e:
                print(f"Ошибка при извлечении текста с {r['href']}: {e}")
                r["doc_html"] = ""
                r["doc_text"] = ""
        return results


class GarantSearchProvider:
    """Поиск по НПА через API Garant.ru. Судебная практика не поддерживается — fallback на DDGS."""

    def __init__(self, token: str | None) -> None:
        self.token = token  # GARANT_API_KEY из окружения

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.token:
            return [{"title": "Ошибка", "href": "", "doc_text": "GARANT_API_KEY не задан."}]

        url = "https://api.garant.ru/v1/search"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        payload = {
            "text": query,
            "count": max_results,
            "kind": ["003"],
            "sort": 0,
            "sortOrder": 0,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            documents = data.get("documents") or []
            results: List[Dict[str, Any]] = []
            for doc in documents:
                name = doc.get("name", "Без названия")
                rel_url = doc.get("url", "")
                absolute_url = f"https://d.garant.ru{rel_url}" if rel_url.startswith("/") else rel_url
                results.append({"title": name, "href": absolute_url, "doc_text": ""})
            return results if results else [{"title": "Ничего не найдено", "href": "", "doc_text": ""}]
        except requests.RequestException as e:
            return [{"title": "Ошибка API", "href": "", "doc_text": str(e)}]


def get_search_provider(name: str | None) -> SearchProvider:
    """Возвращает провайдер по имени: 'garant' или по умолчанию DdgsSearchProvider."""
    if name == "garant":
        token = os.getenv("GARANT_API_KEY")
        return GarantSearchProvider(token)
    return DdgsSearchProvider()


def call_npa_api(query: str) -> List[Dict[str, Any]]:
    """Поиск НПА: при DDGS добавляет site:consultant.ru/."""
    provider = get_search_provider(os.getenv("PRAVO_SEARCH_PROVIDER"))
    if isinstance(provider, DdgsSearchProvider):
        query = query + " site:consultant.ru/"
    return provider.search(query)


def call_court_api(query: str) -> List[Dict[str, Any]]:
    """Поиск судебной практики: site:reputation.su. Garant → fallback на DDGS."""
    provider = get_search_provider(os.getenv("PRAVO_SEARCH_PROVIDER"))
    if isinstance(provider, DdgsSearchProvider):
        query = query + " site:reputation.su"
        return provider.search(query)
    # Garant не предоставляет судебную практику — используем web-поиск
    return DdgsSearchProvider().search(query + " site:reputation.su")
