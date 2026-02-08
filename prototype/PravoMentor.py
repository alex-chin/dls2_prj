from __future__ import annotations

import os
from operator import add
from typing import Any, Dict, List, Literal, Optional, Tuple, Annotated

from dotenv import load_dotenv
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from ddgs import DDGS
import trafilatura

from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from typing_extensions import TypedDict


load_dotenv(override=True)

gigachat_token = os.environ["GIGACHAT_API_KEY"]
llm = GigaChat(credentials=gigachat_token, verify_ssl_certs=False, scope="GIGACHAT_API_PERS")


def ask_giga(query: str, model: str):
    payload = Chat(
        messages=[
            Messages(
                role=MessagesRole.USER,
                content=query
            )
        ],
        temperature=1.0,
        max_tokens=1000,
        top_p=0.0,
        repetition_penalty=1.0,
        model=model
    )
    response = llm.chat(payload)
    return response.dict()["choices"][0]["message"]["content"].strip()


def ddgs_search(query: str, max_results: int = 3):
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


def call_npa_api(query: str):
    query = query + " site:consultant.ru/"
    results = ddgs_search(query)
    return results


def call_court_api(query: str):
    # query = query + ' site:судебныерешения.рф'
    # query = query + ' site:sudrf.ru'
    query = query + " site:reputation.su"
    results = ddgs_search(query)
    return results


def format_docs(search_results: List[Dict]):
    tpl = ""
    for i, r in enumerate(search_results):
        # Используем get с дефолтными значениями на случай, если ключи отсутствуют
        title = r.get("title", "")
        doc_text = r.get("doc_text", "")[:15000]  # Ограничиваем длину
        tpl += f"[Source {i}]: {title}\n{doc_text}\n\n"  # Добавим пустую строку для разделения
    return tpl


def format_links(search_results):
    links = []
    for r in search_results:
        links.append(f"{r['title']} [{r['href']}\n\n")
    return "\n".join(links)


def ask_human(query: str):
    return input(query)


def format_dialog(messages: List[Tuple[str, str]]):  # Уточнение типа
    tpl = ""
    for m in messages:
        tpl += f"[{m[0]}]: {m[1]}\n\n"  # Добавим перевод строки
    return tpl


# Промпты

# Кратко: промт проверяет, хватает ли данных в вопросе для поиска. Если данных мало, он формулирует уточняющий вопрос, иначе отвечает "ок".
# Тип: диагностический (выявление недостатка контекста).
# Техника: бинарная классификация с примерами (few-shot) и строгим ограничением на формат ответа.
# Шаблон: подставляет {query} в конец и запрещает продолжать диалог, оставляя только "ок" или вопрос.
clarification_prompt = PromptTemplate.from_template("""Ты юридический ассистент в Российской Федерации. Тебе дан вопрос пользователя.
Твоя задача определить, надо ли что-то уточнить у пользователя, чтобы выполнить юридический поиск или вопрос пользователя содержит всю необходимую информацию?
Если вопрос содержит всю необходимую информацию ответь: "ок" и больше ничего не пиши.  
Пример: 
Вопрос пользователя: "мне не заплатили по договору, в какой суд подать иск?"
Ответ: Уточите пожалуйста, вы являетесь физическим лицом, индивидуальным предпринимателем или описываете ситуацию компании (юридического лица)?
Вопрос пользователя: "Какой вычет НДФЛ на первого ребенка"
Ответ: ок
[Вопрос пользователя]: "{query}"
Не отвечай на вопрос пользователя, не продолжай диалог, выполни свою задачу.""")

# Кратко: промт сводит диалог в единый поисковый вопрос. Он учитывает все реплики пользователя и выдаёт итоговую формулировку.
# Тип: конденсация контекста (суммаризация/переформулирование).
# Техника: инструктивное перефразирование с запретом на лишний текст.
# Шаблон: подставляет {dialog} в блок <dialog> и требует вывести только один итоговый вопрос.
query_concat_prompt = PromptTemplate.from_template("""Ты юридический ассистент. Тебе дан диалог с пользователем, твоя задача собрать этот диалог в один вопрос к справочной правовой системе, который учтет всю информацию, полученную от пользователя.
<dialog>
{dialog}
</dialog>
Не продолжай диалог, только сформулируй один вопрос.
Вопрос к поисковой системе:""")

# Кратко: промт превращает пользовательский запрос в короткую юридическую поисковую фразу. Он убирает разговорные слова и сохраняет смысл.
# Тип: переписывание запроса (query rewriting).
# Техника: rule-based инструкции + few-shot примеры с форматным ограничением "одна строка".
# Шаблон: вставляет {query} и ожидает только итоговую поисковую фразу без пояснений.
query_rewrite_prompt = PromptTemplate.from_template("""Ты юридический ассистент. Преобразуй запрос пользователя в краткую, точную поисковую фразу, подходящую для ввода в правовую систему (например, «КонсультантПлюс», «Гарант»).
Требования к результату:
- Сохраняй юридический смысл исходного запроса.
- Используй официальную юридическую терминологию.
- Убирай разговорные формулировки, местоимения и лишние слова.
- Формулируй максимально ёмко — как если бы ты искал в базе законов или судебных решений.
- Не добавляй пояснений, комментариев или примеров.
- Отвечай только одной строкой — самой поисковой фразой.

Примеры преобразований:
Исходный запрос: "Что будет, если не платить алименты?"
Поисковая фраза: Уклонение от уплаты алиментов ответственность
Исходный запрос: "Могу ли я вернуть товар, если он не подошёл по цвету?"
Поисковая фраза: Возврат товара ненадлежащего качества цвет
Исходный запрос: "Какие льготы у ветеранов труда в Москве?"
Поисковая фраза: Льготы ветеранам труда Москва
Исходный запрос: "Судебная практика по увольнению за прогул без объяснений"
Поисковая фраза: Судебная практика увольнение за прогул отсутствие объяснений
Исходный запрос: "Что говорит 217-ФЗ о добровольной ликвидации ООО?"
Поисковая фраза: ФЗ-217 добровольная ликвидация ООО

Теперь обработай следующий запрос (не отвечая на сам вопрос, только сделай перефразировку):
[Исходный запрос]: "{query}"
Поисковая фраза:""")

# Кратко: промт относит запрос к НПА или судебной практике. Он выдаёт ровно одно слово-категорию.
# Тип: классификация (labeling).
# Техника: явное определение классов и строгий формат вывода.
# Шаблон: подставляет {query} и требует ответить только "НПА" или "Судебное".
classification_prompt = PromptTemplate.from_template("""Ты юридический ассистент. Проанализируй следующий запрос пользователя и определи, к какой категории он относится:
- "НПА" — если запрос касается нормативно-правовых актов: законов, кодексов, статей, постановлений, правил, положений, требований законодательства, юридических норм, обязанностей по закону и т.п.
- "Судебное" — если запрос касается судебных решений, прецедентов, примеров из практики судов, разборов дел, аргументов в суде, толкования норм судами, позиции ВС/Арбитражных судов и т.п.
Важно: отвечай **только одним словом** — либо "НПА", либо "Судебное".
Запрос: "{query}"
Ответ (одно слово):""")

# Кратко: промт формирует структурированный ответ по документам. Он включает разделы про законодательство, практику и итоговый вывод.
# Тип: RAG-ответ (ответ с опорой на источники).
# Техника: структурный шаблон + запрет внешних знаний.
# Шаблон: вставляет {query} и {docs}, затем требует ответ в фиксированной структуре.
rag_prompt = PromptTemplate.from_template("""Ты — опытный юрист. На основе представленных документов ответь на вопрос пользователя, строго придерживаясь следующей структуры:
1. **Законодательство**
   Перечисли применимые нормативно-правовые акты, статьи, положения. Укажи, что именно они устанавливают по вопросу. Ссылайся только на документы, приведённые ниже. Не добавляй внешние знания.
2. **Судебная практика**
   Приведи примеры из судебных решений, если они есть в документах. Укажи: какой суд, по какому делу, какую позицию занял. Если практики нет — напиши: "В представленных документах отсутствует судебная практика по данному вопросу."
3. **Вывод**  
   Дай краткий, однозначный ответ на вопрос, основанный на совокупности НПА и судебной практики. Формулируй как юридическую позицию: что допускается, запрещено, рекомендовано, возможно в суде и т.п.
Требования:
- Отвечай только на основе документов.
- Не вымышляй нормы или дела.
- Используй официальную юридическую терминологию.
- Будь точен, лаконичен, структурирован.
[Вопрос]: "{query}"
[Документы]:
{docs}
Ответ:""")

# Кратко: промт проверяет полноту чернового ответа и решает, нужен ли доп. поиск. Если есть пробелы — формирует новый поисковый запрос.
# Тип: рефлексия/самопроверка.
# Техника: контроль качества с бинарным исходом ("ок" или новая поисковая фраза) и примерами.
# Шаблон: подставляет {query} и {response}, затем требует вернуть только "ок" или запрос.
reflection_prompt = PromptTemplate.from_template("""Ты — эксперт-юрист. Проанализируй вопрос пользователя и черновик ответа. 
Оцени, насколько черновик ответа полностью раскрывает вопрос с точки зрения:
- нормативно-правового регулирования (НПА),
- судебной практики (если уместно),
- возможных нюансов, условий, исключений.
Если ответ:
- полностью раскрывает вопрос по всем значимым аспектам → верни одну фразу: "ок" и больше ничего не пиши.
- недостаточен, содержит пробелы или требует уточнения → сформулируй один точный поисковой запрос для справочно-правовой системы (например, «КонсультантПлюс», «Гарант»), который поможет дополнить ответ. Запрос должен быть кратким, ёмким, с использованием юридической терминологии.
Не добавляй пояснений. Отвечай только "ок" или поисковой фразой.
---
Пример 1:
Вопрос: Можно ли уволить сотрудника за однократный прогул без предупреждений?
Черновик ответа: Да, можно. Согласно ст. 81 ТК РФ, прогул является основанием для увольнения.
Твой ответ: Судебная практика увольнение за прогул отсутствие уведомления
Пример 2:
Вопрос: Облагается ли НДС продажа доли в уставном капитале ООО?
Черновик ответа: Нет, передача доли в уставном капитале ООО не облагается НДС на основании п. 2 ст. 149 НК РФ.
Твой ответ: ок
---
[Вопрос]: "{query}"
[Черновик ответа]: {response}
[Твой ответ]:""")

# Кратко: промт собирает финальный развернутый ответ по документам. Он использует ту же структуру, но допускает более подробный вывод.
# Тип: финальный RAG-ответ (синтез).
# Техника: фиксированная структура + запрет на внешние знания.
# Шаблон: подставляет {query} и {docs} и просит выдать полный ответ по шаблону.
final_answer_prompt = PromptTemplate.from_template("""Ты — опытный юрист. На основе представленных документов ответь на вопрос пользователя, строго придерживаясь следующей структуры:
1. **Законодательство**
   Перечисли применимые нормативно-правовые акты, статьи, положения. Укажи, что именно они устанавливают по вопросу. Ссылайся только на документы, приведённые ниже. Не добавляй внешние знания.
2. **Судебная практика**
   Приведи примеры из судебных решений, если они есть в документах. Укажи: какой суд, по какому делу, какую позицию занял. Если практики нет — напиши: "В представленных документах отсутствует судебная практика по данному вопросу."
3. **Вывод**  
    Дай развернутый ответ на основе всех предложенных документов. Формулируй как юридическую позицию: что допускается, запрещено, рекомендовано, возможно в суде и т.п.

Требования:
- Отвечай только на основе документов.
- Не вымышляй нормы или дела.
- Используй официальную юридическую терминологию.
- Будь точен, лаконичен, структурирован.
[Вопрос]: "{query}"
[Документы]:
{docs}
Ответ:""")


class MyState(TypedDict):
    # Используем Optional для полей, которые могут отсутствовать в начале
    query: str  # Исходный запрос пользователя
    search_query: Optional[str]  # Текущий поисковый запрос агента
    messages: Annotated[List[Tuple[str, str]], add]  # Сообщения
    clarification: Optional[str]
    need_clarify_question: Optional[bool]
    category: Optional[str]
    docs: Annotated[List[Dict], add]  # Документы, полученные в результате поиска
    answers: Annotated[List[Any], add]  # Промежуточные ответы ассистента
    final_answer: str
    need_re_search: Optional[bool]
    re_search_cnt: Optional[int]
    clarification_cnt: Optional[int]
    verbose: Optional[bool]


# Nodes
def setup_node(state: MyState) -> MyState:
    state_update = dict()
    state_update["search_query"] = state["query"]
    state_update["messages"] = [("user", state["query"])]
    state_update["clarification"] = None
    state_update["need_clarify_question"] = None
    state_update["category"] = None
    state_update["docs"] = []
    state_update["answers"] = []
    state_update["final_answer"] = None
    state_update["need_re_search"] = None
    state_update["re_search_cnt"] = 0
    state_update["clarification_cnt"] = 0
    state_update["verbose"] = state.get("verbose", False)

    return state_update


def clarify_node(state: MyState) -> MyState:
    """
    Проверяем нуждается ли вопрос в уточнении от пользователя.
    Если нуждается, то формулируем уточняющий вопрос
    """
    query = state["search_query"]
    prompt = clarification_prompt.format(query=query)
    gen = ask_giga(prompt, "GigaChat-2")

    state_update = dict()
    state_update["need_clarify_question"] = False if (len(gen) < 10 and "ок" in gen.lower()) else True
    state_update["messages"] = [("tool_clarify", gen)]
    state_update["clarification"] = gen
    state_update["clarification_cnt"] = state["clarification_cnt"] + 1

    if state["verbose"]:
        print("clarify_node:", gen)

    return state_update


def human_clarify_node(state: MyState) -> MyState:
    """Просим пользователя ответить на уточняющий вопрос"""
    if __name__ == "__main__":
        value = ask_human(state["clarification"])
    else:
        value = interrupt(state["clarification"])

    message = ("user", value)

    state_update = dict()
    state_update["messages"] = [message]

    if state["verbose"]:
        print("human_clarify_node:", value)

    return state_update


def query_concat_node(state: MyState) -> MyState:
    """Объединяем диалог с пользователем в один вопрос для поиска"""
    dialog = format_dialog(state["messages"])
    prompt = query_concat_prompt.format(dialog=dialog)
    gen = ask_giga(prompt, "GigaChat-2")

    message = ("tool_concat", gen)

    state_update = dict()
    state_update["search_query"] = gen
    state_update["messages"] = [message]

    if state["verbose"]:
        print("query_concat_node:", gen)

    return state_update


def rewrite_node(state: MyState) -> MyState:
    query = state["search_query"]
    prompt = query_rewrite_prompt.format(query=query)
    rewritten = ask_giga(prompt, "GigaChat-2")

    message = ("tool_rewrite", rewritten)

    state_update = dict()
    state_update["search_query"] = rewritten
    state_update["messages"] = [message]

    if state["verbose"]:
        print("rewrite_node:", message)

    return state_update


def classify_node(state: MyState) -> MyState:
    """Классифицируем запрос по типу поиск - в правовой системе или в судебной практике"""
    query = state["search_query"]
    prompt = classification_prompt.format(query=query)
    category = ask_giga(prompt, "GigaChat-2")

    message = ("tool_classify", category)

    state_update = dict()
    state_update["category"] = category
    state_update["messages"] = [message]
    state_update["docs"] = []

    if state["verbose"]:
        print("classify_node:", category)

    return state_update


def search_npa_node(state: MyState) -> MyState:
    results = call_npa_api(state["search_query"])

    message_text = format_links(results)
    message = ("result_search_npa", message_text)

    state_update = dict()
    state_update["docs"] = results
    state_update["messages"] = [message]

    if state["verbose"]:
        print("search_npa_node:", message_text)

    return state_update


def search_court_node(state: MyState) -> MyState:
    results = call_court_api(state["search_query"])

    message_text = format_links(results)
    message = ("result_search_court", message_text)

    state_update = dict()
    state_update["docs"] = results
    state_update["messages"] = [message]

    if state["verbose"]:
        print("search_court_node:", message_text)

    return state_update


def answer_node(state: MyState) -> MyState:
    query = state["search_query"]
    # Проверка на существование docs
    docs = state.get("../docs", [])
    if not docs:
        # Обработка случая, если документы не найдены
        answer = "Извините, по вашему запросу не удалось найти подходящие документы."
    else:
        prompt = rag_prompt.format(query=query, docs=format_docs(docs))
        answer = ask_giga(prompt, "GigaChat-2")

    answer_data = {
        "title": query,
        "doc_text": answer
    }

    message = ("tool_rag", answer)

    state_update = dict()
    state_update["answers"] = [answer_data]
    state_update["messages"] = [message]

    if state["verbose"]:
        print("answer_node:", answer)

    return state_update


def reflect_node(state: MyState) -> MyState:
    answer = state["answers"][-1]
    prompt = reflection_prompt.format(query=state["search_query"], response=answer["doc_text"])
    gen = ask_giga(prompt, "GigaChat-2")

    message = ("tool_reflect", gen)

    state_update = dict()
    state_update["need_re_search"] = False if (len(gen) < 10 and "ок" in gen.lower()) else True
    if state_update["need_re_search"]:
        state_update["search_query"] = gen

    state_update["messages"] = [message]
    state_update["re_search_cnt"] = state["re_search_cnt"] + 1

    if state["verbose"]:
        print("reflect_node:", gen)

    return state_update


def final_answer_node(state: MyState) -> MyState:
    query = state["query"]
    # Проверка на существование docs
    docs = state["answers"]
    if not docs:
        # Обработка случая, если документы не найдены
        answer = "Извините, по вашему запросу не удалось найти подходящие документы."
    elif len(docs) == 1:
        answer = docs[0]["doc_text"]
    else:
        prompt = final_answer_prompt.format(query=query, docs=format_docs(docs))
        answer = ask_giga(prompt, "GigaChat-2")

    message = ("tool_final_answer", answer)

    state_update = dict()
    state_update["final_answer"] = answer
    state_update["messages"] = [message]

    if state["verbose"]:
        print("answer_node:", answer)

    return state_update


# Decisions
def check_need_human(state: MyState) -> Literal["human_clarify_node", "rewrite_node"]:
    clarification_cnt = state["clarification_cnt"]
    need_clarify_question = state["need_clarify_question"]

    if clarification_cnt > 1:
        return "rewrite_node"
    if need_clarify_question:
        return "human_clarify_node"
    return "rewrite_node"


def check_search_type(state: MyState) -> Literal["search_npa_node", "search_court_node"]:
    # Проверка существования ключа
    category = state["category"].lower()
    if "нпа" in category:
        return "search_npa_node"
    if "суд" in category:
        return "search_court_node"
    return "search_npa_node"  # По умолчанию ищем в НПА


def check_need_re_search(state: MyState) -> Literal["classify_node", "final_answer_node"]:
    # Проверка существования ключей
    re_search_cnt = state["re_search_cnt"]
    need_re_search_flag = state["need_re_search"]

    if re_search_cnt > 1:
        return "final_answer_node"
    if need_re_search_flag:
        return "classify_node"  # После рефлексии снова классифицируем вопрос и идем в поиск
    return "final_answer_node"


# Workflow definition
workflow = StateGraph(MyState)
workflow.add_node("setup_node", setup_node)
workflow.add_node("clarify_node", clarify_node)
workflow.add_node("human_clarify_node", human_clarify_node)
workflow.add_node("query_concat_node", query_concat_node)
workflow.add_node("rewrite_node", rewrite_node)
workflow.add_node("classify_node", classify_node)
workflow.add_node("search_npa_node", search_npa_node)
workflow.add_node("search_court_node", search_court_node)
workflow.add_node("answer_node", answer_node)
workflow.add_node("reflect_node", reflect_node)
workflow.add_node("final_answer_node", final_answer_node)

workflow.add_edge(START, "setup_node")
workflow.add_edge("setup_node", "clarify_node")
workflow.add_conditional_edges("clarify_node", check_need_human)
workflow.add_edge("human_clarify_node", "query_concat_node")
workflow.add_edge("query_concat_node", "rewrite_node")
workflow.add_edge("rewrite_node", "classify_node")
workflow.add_conditional_edges("classify_node", check_search_type)
workflow.add_edge("search_npa_node", "answer_node")
workflow.add_edge("search_court_node", "answer_node")
workflow.add_edge("answer_node", "reflect_node")
workflow.add_conditional_edges("reflect_node", check_need_re_search)
workflow.add_edge("final_answer_node", END)

# Компиляция графа
graph = workflow.compile()

def run_graph(state: Dict[str, Any], mode: str = "debug") -> None:
    """Запуск графа с выбранным режимом вывода: debug или simple."""
    if mode not in {"debug", "simple"}:
        raise ValueError("mode must be 'debug' or 'simple'")

    stage_by_node = {
        "search_npa_node": "запрос в web",
        "search_court_node": "запрос в web",
        "human_clarify_node": "запрос информации от пользователя",
        "__interrupt__": "запрос информации от пользователя",
        "answer_node": "думаю",
        "reflect_node": "оцениваю",
    }

    final_answer = None

    # stream(from_checkpoint=None) означает запуск с самого начала
    # stream_mode="values" тоже может быть полезен
    for step_result in graph.stream(state, stream_mode="updates"):
        if mode == "simple":
            for node_name, updated_state in step_result.items():
                stage = stage_by_node.get(node_name)
                if stage:
                    print(stage)
                if node_name == "final_answer_node" and hasattr(updated_state, "get"):
                    final_answer = updated_state.get("final_answer")
            continue

        print("--- ШАГ ---")
        # step_result - это словарь, где ключ - это имя узла или "__end__", а значение - обновленное состояние (state)
        for node_name, updated_state in step_result.items():
            print(f"Выполнен узел: {node_name}")
            if not hasattr(updated_state, "get"):
                print(f"  Interrupt payload: {updated_state}")
                print("-" * 20)
                continue
            if node_name == "final_answer_node":
                final_answer = updated_state.get("final_answer")
            # Здесь вы можете инспектировать updated_state
            print(f"  Текущий search_query: {updated_state.get('search_query', 'N/A')}")
            print(f"  Текущая category: {updated_state.get('category', 'N/A')}")
            print(f"  Текущий answer: {updated_state.get('answer', 'N/A')[:100]}...")  # Первые 100 символов
            print(f"  need_clarify_question: {updated_state.get('need_clarify_question', 'N/A')}")
            print(f"  need_re_search: {updated_state.get('need_re_search', 'N/A')}")
            print(f"  clarification_cnt: {updated_state.get('clarification_cnt', 'N/A')}")
            print(f"  re_search_cnt: {updated_state.get('re_search_cnt', 'N/A')}")
            # Печать последних нескольких сообщений для понимания диалога
            messages = updated_state.get("messages", [])
            if messages:
                print("  Последние сообщения:")
                for msg in messages[-3:]:  # Печатаем последние 3 сообщения
                    print(f"    {msg}")
            print("-" * 20)

    if final_answer:
        print("=== FINAL ANSWER ===")
        print(final_answer)

if __name__ == "__main__":
    state = dict()
    state["query"] = "Как обжаловать расторжение договора аренды помещения?"

    mode = os.getenv("PRAVO_RUN_MODE", "simple")
    run_graph(state, mode=mode)
