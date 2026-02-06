from operator import add
from typing import Any, Dict, List, Optional, Tuple, Annotated

from typing_extensions import TypedDict


class MyState(TypedDict):
    query: str
    search_query: Optional[str]
    messages: Annotated[List[Tuple[str, str]], add]
    clarification: Optional[str]
    clarification_answer: Optional[str]
    need_clarify_question: Optional[bool]
    category: Optional[str]
    docs: Annotated[List[Dict], add]
    answers: Annotated[List[Any], add]
    final_answer: str
    need_re_search: Optional[bool]
    re_search_cnt: Optional[int]
    clarification_cnt: Optional[int]
    verbose: Optional[bool]
    batch_mode: Optional[bool]
