"""
Работа с LLM GigaChat.

Предоставляет единый экземпляр клиента и функцию ask_giga() для синхронных
запросов к модели. Используется узлами графа для классификации, переформулировки
и генерации RAG-ответов.
"""
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from .config import GIGACHAT_API_KEY, GIGACHAT_SCOPE

# Глобальный клиент GigaChat (singleton)
_llm = GigaChat(
    credentials=GIGACHAT_API_KEY,
    verify_ssl_certs=False,
    scope=GIGACHAT_SCOPE,
)


def ask_giga(query: str, model: str) -> str:
    """Отправляет промпт в GigaChat и возвращает текст ответа."""
    payload = Chat(
        messages=[
            Messages(
                role=MessagesRole.USER,
                content=query,
            )
        ],
        temperature=1.0,
        max_tokens=1000,
        top_p=0.0,
        repetition_penalty=1.0,
        model=model,
    )
    response = _llm.chat(payload)
    data = response.model_dump() if hasattr(response, "model_dump") else response.dict()
    return data["choices"][0]["message"]["content"].strip()
