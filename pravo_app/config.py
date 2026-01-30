import os

from dotenv import load_dotenv

load_dotenv(override=True)

GIGACHAT_API_KEY = os.environ["GIGACHAT_API_KEY"]
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-2")
