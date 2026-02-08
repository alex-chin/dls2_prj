"""
Состояние графа юридического агента.

Определяет TypedDict для LangGraph: все поля, передаваемые между узлами
графа состояний. Аннотация Annotated[List, add] задаёт редуктор для слияния
списков при обновлении состояния.
"""
from operator import add
from typing import Any, Dict, List, Optional, Tuple, Annotated

from typing_extensions import TypedDict


class MyState(TypedDict):
    """Состояние агента: входные данные, промежуточные и итоговые результаты."""

    # Исходный запрос пользователя (не меняется в ходе выполнения)
    query: str
    # Текущая поисковая фраза после переформулировки/уточнений
    search_query: Optional[str]
    # История диалога: (роль, текст). Используется для конденсации контекста
    messages: Annotated[List[Tuple[str, str]], add]
    # Вопрос уточнения, сформированный LLM (если need_clarify_question)
    clarification: Optional[str]
    # Ответ пользователя на уточняющий вопрос
    clarification_answer: Optional[str]
    # Флаг: требуется ли уточнение у пользователя
    need_clarify_question: Optional[bool]
    # Категория запроса: "НПА" или "Судебное"
    category: Optional[str]
    # Результаты поиска документов (сырые данные провайдера)
    docs: Annotated[List[Dict], add]
    # Черновые ответы RAG по каждому циклу поиска
    answers: Annotated[List[Any], add]
    # Итоговый ответ пользователю
    final_answer: str
    # Флаг: нужен ли повторный поиск после самопроверки
    need_re_search: Optional[bool]
    # Счётчик циклов повторного поиска (ограничение рекурсии)
    re_search_cnt: Optional[int]
    # Счётчик уточняющих вопросов (ограничение диалога)
    clarification_cnt: Optional[int]
    # Режим отладки: вывод промежуточных шагов в консоль
    verbose: Optional[bool]
    # Пакетный режим: автоответ без запроса к пользователю при недостатке данных
    batch_mode: Optional[bool]
