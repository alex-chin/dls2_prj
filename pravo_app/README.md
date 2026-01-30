# Pravo App

Модульная версия юридического ассистента на LangGraph.

## Структура
- `config.py` — загрузка env и конфигурация модели.
- `llm.py` — вызов GigaChat.
- `search.py` — web-поиск и извлечение текста.
- `formatters.py` — форматирование документов, ссылок и диалога.
- `prompts.py` — промпты для всех этапов.
- `state.py` — тип состояния графа.
- `nodes.py` — узлы графа.
- `decisions.py` — логика переходов.
- `graph.py` — сборка и экспорт `graph`.
- `run.py` — режимы запуска (debug/simple).
- `main.py` — CLI entrypoint.

## Запуск
CLI:
- `python -m pravo_app.main`

Переменные окружения:
- `PRAVO_QUERY` — стартовый запрос.
- `PRAVO_RUN_MODE` — `debug` или `simple`.
- `PRAVO_USE_INPUT=1` — использовать `input()` вместо `interrupt()`.
- `PRAVO_SEARCH_PROVIDER` — `ddgs` (по умолчанию) или `garant`.
- `GARANT_API_KEY` — токен для Garant API.
