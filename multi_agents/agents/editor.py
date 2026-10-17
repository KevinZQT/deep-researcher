from typing import Dict, Any, Literal
from ..memory import ResearchState
from ..memory import DraftState

from ...configuration import Configuration
from .utils.prompts import get_current_date, plan_research_instructions
from .utils.llms import create_model
from .utils.tool_and_schema import ResearchPlan
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph,END
from .researcher import ResearcherAgent
from .reviewer import ReviewerAgent
from .reviser import ReviserAgent
import asyncio




    
class EditorAgent:

    def __init__(self, queue: asyncio.Queue = None, stream_output = None, engine_factory=None):
        self.queue = queue
        self.stream_output = stream_output
        self.engine_factory = engine_factory 


    async def plan_research(self, state: ResearchState, config: RunnableConfig) -> ResearchState:
        configuration = Configuration.from_runnable_config(config)
        prompt = self.format_prompt(state, configuration)
        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue,
                {
                    "type": "research_update",
                    "data": {
                        "message": "Planning research layout..."
                    },
                },
            )
        else:
            print("Editor --- Planning research layout based on initial resaerch...")
        model = create_model(configuration.planner_model).with_structured_output(ResearchPlan)
        result = ResearchPlan.model_validate(await model.ainvoke(prompt))
        if len(result.sections) > configuration.max_sections:
            raise ValueError("Planner exceeded max_sections")
        return {
            "title": result.title,
            "date": get_current_date(),
            "sections": result.sections
        }
        
    def format_prompt(
        self, 
        state: ResearchState, 
        configuration: Configuration
    ) -> str:
        task = state.get("task")
        formatted_prompt = plan_research_instructions.format(
            date = get_current_date(),
            topic = (task or {}).get("topic", ""),
            initial_research = state.get("initial_research"),
            human_feedback = state.get("human_feedback"),
            include_human_feedback = configuration.include_human_feedback,
            max_sections = configuration.max_sections
        )
        return formatted_prompt


    async def run_parallel_research(self, state: ResearchState, config: RunnableConfig):
        workflow = self.create_workflow()
        graph = workflow.compile()
        topics = state.get("sections")
        if not isinstance(topics, list) or not topics or any(not isinstance(t, str) or not t.strip() for t in topics):
            raise ValueError("sections must be a non-empty list of non-empty strings")
        
        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue,
                {
                    "type": "research_update",
                    "data": {
                        "message": f"Running parallel deep research"

                    },
                },
            )
        else:
            print(f"Editor --- Running parallel deep research..." )
            
        drafts = [
            asyncio.create_task(graph.ainvoke(self.create_draft_schema(state, topic), config=config))
            for topic in topics
        ]
        try:
            outputs = await asyncio.gather(*drafts)
        except BaseException:
            # Stop sibling searches on failure or parent cancellation.
            for draft in drafts:
                draft.cancel()
            await asyncio.gather(*drafts, return_exceptions=True)
            raise
        return {"research_data": [result["draft"] for result in outputs]}

    def initial_agents(self):
        return {
            "researcher": ResearcherAgent(self.queue, self.stream_output, engine_factory=self.engine_factory),
            "reviewer": ReviewerAgent(self.queue, self.stream_output),
            "reviser": ReviserAgent(self.queue, self.stream_output)
        }

    def create_workflow(self):
        agents = self.initial_agents()
        workflow = StateGraph(DraftState)
        self.create_nodes(workflow,agents)
        self.create_edges(workflow)
        return workflow
    
    def create_nodes(self, workflow: StateGraph, agents: Dict[str, Any]):

        workflow.add_node("researcher", agents['researcher'].run_depth_research)
        workflow.add_node("reviewer", agents['reviewer'].run)
        workflow.add_node("reviser", agents['reviser'].run)

    def create_edges(self, workflow: StateGraph):

        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "reviewer")
        workflow.add_conditional_edges(
            "reviewer", 
            self.route_draft_review, 
            {"accept": END,  "revise":"reviser"}
            )
        workflow.add_edge("reviser", "reviewer")

    def create_draft_schema(self, state:ResearchState, topic:str):

        return{
            "task": state.get("task"),
            "title": state.get("title"),
            "topic": topic,
            "draft_revision_count": 0,
            "review": None,
            "revision_notes": None,
        }

    def route_draft_review(self, state:DraftState, config: RunnableConfig) -> Literal["accept", "revise"]:
        if not state.get("review"):
            return "accept"
        configuration = Configuration.from_runnable_config(config)
        if state.get("draft_revision_count", 0) >= configuration.max_draft_revisions:
            raise RuntimeError(
                f"Draft review failed for {state.get('topic')!r} after the revision limit: "
                f"{state['review']}"
            )
        return "revise"
