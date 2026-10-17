from typing import TypedDict, Annotated, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
import operator


class ResearchState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    search_query: list[str]

    web_search_result: Annotated[list[str], operator.add]
    sources_gathered: Annotated[list[dict[str, Any]], operator.add]

    max_generated_queries: int
    max_search_loops: int
    search_loop_count: int
    reasoning_model: str

    is_sufficient: bool
    knowledge_gap: str
    follow_up_queries: list[str]
    number_of_ran_queries: int




class QueryGenerationState(TypedDict):
    search_query: list[str]


class WebSearchState(TypedDict):
    search_query: str
    id: int
