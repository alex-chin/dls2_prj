import requests


class Tools:
    def __init__(self, garant_token=None):
        self.garant_token = garant_token

    def garant_search_10(self, query_text: str) -> str:
        """
        Выполнить поиск по Garant API и вернуть топ-результаты в виде текста.
        :param query_text: поисковый запрос
        :return: человекочитаемая строка с названием и ссылкой (
        JSON-сериализуемо)
        """
        if not self.garant_token:
            return "Ошибка: переменная окружения GARANT_TOKEN не задана."

        url = "https://api.garant.ru/v1/search"
        headers = {"Accept": "application/json",
                   "Content-Type": "application/json",
                   "Authorization": f"Bearer {self.garant_token}", }
        payload = {"text": query_text, "count": 10, # сколько документов вернуть
                   "kind": [],  # можно уточнить типы документов
                   "sort": 0,  # по релевантности
                   "sortOrder": 0,  # по убыванию
                   }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            documents = data.get("documents") or []
            if not documents:
                return "Ничего не найдено."

            lines = []
            for doc in documents:
                name = doc.get("name", "Без названия")
                rel_url = doc.get("url", "")
                absolute_url = (
                    f"https://d.garant.ru{rel_url}" if rel_url.startswith(
                        "/") else rel_url)
                lines.append(f"{name}\n   {absolute_url}")

            return "\n".join(lines)

        except requests.RequestException as e:
            # Возвращаем строку — это сериализуемо и удобно показывать в чате
            return f"Ошибка API: {e}"


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    load_dotenv(override=True)
    garant_token = os.environ['GARANT_API_KEY']

    lines = (Tools(garant_token=garant_token)).garant_search_10(
        'Как обжаловать штраф ГИПДД')
    print(lines)
