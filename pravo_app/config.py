"""
Конфигурация юридического агента.

Загружает переменные окружения из .env и экспортирует параметры для подключения
к GigaChat API — LLM, используемой агентом для генерации и классификации.
"""
import os

from dotenv import load_dotenv

load_dotenv(override=True)

# Обязательный ключ авторизации GigaChat API
GIGACHAT_API_KEY = os.environ["GIGACHAT_API_KEY"]
# Область доступа: по умолчанию персональный скоуп (GIGACHAT_API_PERS)
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
# Имя модели: GigaChat-2 или иная, поддерживаемая API
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-2")
