from langgraph.graph import StateGraph, END, add_messages
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Send
from .configuration import Configuration
from .state import (
    ResearchState,
    QueryGenerationState,
    WebSearchState,
)
from .prompts import (
    web_search_instructions, 
    query_generate_instructions,
    reflection_instructions,
    answer_instructions
)
from .utils import (
    get_search_topic, 
    get_current_date,
    get_url_map,
    get_citations,
    insert_citation_markers,
)
from .schema import SearchQuery, ReflectionOutput
from google.genai import Client
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()





class Researcher:

    def __init__(self):
        pass

    async def generate_query(self, state: ResearchState, config: RunnableConfig) -> QueryGenerationState:

        configurable = Configuration.from_runnable_config(config)
        max_generated_queries = state.get("max_generated_queries")
        if max_generated_queries is None:
            max_generated_queries = configurable.max_generated_queries

        messages = state["messages"]
        search_topic = get_search_topic(messages)
        current_date = get_current_date()

        prompt = query_generate_instructions.format(
            number_queries = max_generated_queries,
            current_date = current_date,
            search_topic = search_topic
        )


        model = ChatGoogleGenerativeAI(
            model = configurable.query_generate_model,
            temperature = 1.0,
            max_retries = 2,
            api_key = os.getenv("GEMINI_API_KEY")
        )

        structured_model = model.with_structured_output(SearchQuery)

        result = await structured_model.ainvoke(prompt)

        if not result.query:
            raise ValueError("No search queries were generated")

        return {"search_query": result.query}



    def continue_to_web_search(self, state: QueryGenerationState) -> list[Send]:

        return [
            Send("web_search", {"search_query": query, "id": int(idx)}) 
                 for idx, query in enumerate(state["search_query"])]


    async def web_search(self, state: WebSearchState, config: RunnableConfig) -> ResearchState:

        query = state['search_query']

        formatted_query = web_search_instructions.format(
            current_date=get_current_date(),
            research_topic=state["search_query"],
        )

        configurable = Configuration.from_runnable_config(config)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        
        async with Client(api_key = api_key).aio as client:         
            response = await client.models.generate_content(
                model = configurable.search_model,
                contents = formatted_query,
                config = {
                    "tools": [{"google_search":{}}],
                    "temperature": 0
                    }
            )

            text = response.text or ""
            if not text.strip():
                raise ValueError(f"搜索没有返回正文：{query}")

            candidates = response.candidates or []
            metadata = candidates[0].grounding_metadata if candidates else None
            chunks = (metadata.grounding_chunks or []) if metadata else []

            if chunks:
                url_map = get_url_map(chunks, state["id"])
                citations = get_citations(response, url_map)
                modified_text = insert_citation_markers(text, citations)

                sources_gathered = [
                    item
                    for citation in citations
                    for item in citation["segments"]
                ]
            else:
                modified_text = (
                    "[本次回答未提供搜索来源，内容尚未经来源核验]\n"
                    + text
                )
                sources_gathered = []
                print(f"本次响应没有搜索引用元数据：{query}")
        return {
            "sources_gathered": sources_gathered,
            "web_search_result": [modified_text],
        }

     
    async def reflection(self, state: ResearchState, config: RunnableConfig) -> ResearchState:
        configurable = Configuration.from_runnable_config(config)
        search_loop_count = state.get("search_loop_count", 0) + 1
        refleciton_model = configurable.refleciton_model

        prompt = reflection_instructions.format(
            current_date = get_current_date(),
            search_topic=get_search_topic(state["messages"]),
            summaries="\n\n---\n\n".join(state["web_search_result"]),
        )


        model = ChatGoogleGenerativeAI(
        model=refleciton_model,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("GEMINI_API_KEY"),
        )

        if not state.get("sources_gathered"):
            return {
                "is_sufficient": False,
                "knowledge_gap": "No sources are currently available.",
                "follow_up_queries": [
                    get_search_topic(state["messages"])
                    + " official sources latest information"
                ],
                "search_loop_count": search_loop_count,
                "number_of_ran_queries": len(state["web_search_result"]),
            }
        structured_model = model.with_structured_output(ReflectionOutput)


        print("Reflection: checking research results...")

        result = await structured_model.ainvoke(prompt)

        print(
            f"Reflection: sufficient={result.is_sufficient}, "
            f"follow_up_queries={result.follow_up_queries}"
        )
        return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "search_loop_count": search_loop_count,
        "number_of_ran_queries": len(state["web_search_result"]),
        }
    
    def evaluate_research(self, state: ResearchState, config: RunnableConfig) -> str | list[Send]:
        configurable = Configuration.from_runnable_config(config)
        max_search_loops = (
            state.get("max_search_loops")
            if state.get("max_search_loops") is not None
            else configurable.max_search_loops
        )
        if (
            state["is_sufficient"]
            or state["search_loop_count"] >= max_search_loops
            or not state["follow_up_queries"]
        ):
            return "finalize_answer"
        else:
            return [
                Send(
                    "web_search",
                    {
                        "search_query": follow_up_query,
                        "id": state["number_of_ran_queries"] + int(idx),
                    },
                )
                for idx, follow_up_query in enumerate(state["follow_up_queries"])
            ]

    
    async def finalize_answer(self, state: ResearchState, config: RunnableConfig):

        configurable = Configuration.from_runnable_config(config)
        reasoning_model = state.get("reasoning_model") or configurable.answer_model

        current_date = get_current_date()
        formatted_prompt = answer_instructions.format(
            current_date=current_date,
            research_topic=get_search_topic(state["messages"]),
            summaries="\n---\n\n".join(state["web_search_result"]),
        )

        model = ChatGoogleGenerativeAI(
            model=reasoning_model,
            temperature=0,
            max_retries=2,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        result = await model.ainvoke(formatted_prompt)

        content = result.content

        if isinstance(content, str):
            answer_text = content
        else:
            answer_text = "\n".join(
                block if isinstance(block, str) else block.get("text", "")
                for block in content
                if isinstance(block, str)
                or (
                    isinstance(block, dict)
                    and block.get("type") == "text"
                )
            )

        for source in state.get("sources_gathered", []):
            short_url = source.get("short_url")
            original_url = source.get("value")

            if short_url and original_url:
                answer_text = answer_text.replace(short_url, original_url)

        return {
            "messages": [AIMessage(content=answer_text)],
        }


    def create_workflow_nodes(self, workflow: StateGraph):

        workflow.add_node("generate_query",self.generate_query)
        workflow.add_node("web_search", self.web_search)
        workflow.add_node("reflection", self.reflection)
        workflow.add_node("finalize_answer", self.finalize_answer)    



    def create_workflow_edges(self, workflow: StateGraph):
        workflow.set_entry_point("generate_query")
        workflow.add_conditional_edges("generate_query", self.continue_to_web_search, ["web_search"])
        workflow.add_edge("web_search", "reflection")
        workflow.add_conditional_edges("reflection", self.evaluate_research, ["web_search", "finalize_answer"])
        workflow.add_edge("finalize_answer", END)

    def create_workflow(self) -> StateGraph:

        workflow = StateGraph(ResearchState, config_schema = Configuration)
        self.create_workflow_nodes(workflow)
        self.create_workflow_edges(workflow)
        return workflow

    async def run(self, search_query: str, config: RunnableConfig):
        graph = self.create_workflow().compile()

        response = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=search_query)],
                "search_query": [],
                "web_search_result": [],
                "sources_gathered": [],
                "search_loop_count": 0,
            },
            config=config,
        )

        return response["messages"][-1].content

async def main():
    researcher = Researcher()

    config: RunnableConfig = {
        "configurable": {}
    }  

    answer = await researcher.run(
        search_query="who is Leo Messi?",
        config=config,
    )

    print(answer)


if __name__ == "__main__":
    asyncio.run(main())