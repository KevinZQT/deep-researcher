from typing import TypedDict, Dict, Any, Literal
from langgraph.graph import StateGraph,END
from langchain_core.runnables import RunnableConfig
from .memory import ResearchState
from datetime import datetime,timezone
from ..configuration import Configuration
from .agents import (
    ResearcherAgent,
    EditorAgent,
    HumanAgent,
    ReviserAgent,
    ReviewerAgent,
    WriterAgent,
    VisualizerAgent,
    PublisherAgent,
    FactCheckerAgent
)

class ChiefAgent:

    def __init__(self, task: dict, task_id: str, queue=None, feedback_queue=None, stream_output=None, engine_factory=None):

        if not isinstance(task, dict) or not isinstance(task.get("topic"), str) or not task["topic"].strip():
            raise ValueError("task must contain a non-empty topic string")
        self.queue = queue
        self.feedback_queue = feedback_queue
        self.stream_output = stream_output
        self.engine_factory = engine_factory
        self.task = task
        self.task_id = task_id
 
    async def run_research(self):

        agents = self.initial_agents()
        workflow = self.create_workflow(agents)
        graph = workflow.compile()

        config = {
            "configurable": {
                **self.task,
                "thread_id": self.task_id,
            }
        }
        settings = Configuration.from_runnable_config(config)
        config["recursion_limit"] = max(
            25, 12 + 2 * settings.max_plan_revisions + 2 * settings.max_fact_check_revisions,
            5 + 2 * settings.max_draft_revisions,
        )
        result = await graph.ainvoke({
            "task": self.task,
            "plan_review_loop_count": 0,
            "human_feedback": None,
            "fact_check_notes": None,
            "fact_check_revision_count": 0,
        }, config)
        return result

    def initial_agents(self):
        return {
            "researcher": ResearcherAgent(self.queue, self.stream_output, engine_factory=self.engine_factory),
            "editor": EditorAgent(self.queue, self.stream_output, engine_factory=self.engine_factory),
            "human": HumanAgent(self.queue, self.feedback_queue, self.stream_output),
            "reviewer": ReviewerAgent(self.queue, self.stream_output),
            "reviser": ReviserAgent(self.queue, self.stream_output),
            "writer": WriterAgent(self.queue, self.stream_output),
            "visualizer": VisualizerAgent(self.queue, self.stream_output),
            "publisher": PublisherAgent(self.queue, self.stream_output),
            "fact_checker": FactCheckerAgent(self.queue, self.stream_output)          
        }

    def create_workflow(self, agents: Dict[str, Any]):
        workflow = StateGraph(ResearchState)
        self.create_nodes(workflow, agents)
        self.create_routes(workflow)
        return workflow 
    
    def create_nodes(self, workflow: StateGraph, agents: Dict[str, Any]):
        workflow.add_node("browser", agents["researcher"].run_initial_research)
        workflow.add_node("planner", agents["editor"].plan_research)
        workflow.add_node("human", agents["human"].plan_review)
        workflow.add_node("researcher", agents["editor"].run_parallel_research)
        workflow.add_node("writer", agents["writer"].run)
        workflow.add_node("fact_checker", agents["fact_checker"].run)
        workflow.add_node("visualizer", agents["visualizer"].run)
        workflow.add_node("publisher", agents["publisher"].run)

    def create_routes(self, workflow: StateGraph):

        workflow.set_entry_point("browser")

        workflow.add_edge("browser", "planner")
        workflow.add_edge("planner", "human")
        workflow.add_conditional_edges(
            "human", 
            self.route_human_feedback, 
            {"accept":"researcher", "revise": "planner"}
        )
        workflow.add_edge("researcher", "writer") 
        workflow.add_edge("writer", "fact_checker")
        workflow.add_conditional_edges(
            "fact_checker",
            self.route_fact_check,
            {"accept":"visualizer", "revise": "writer"}
        )
        workflow.add_edge("visualizer", "publisher")
        workflow.add_edge("publisher", END)

    def route_human_feedback(
        self, 
        state: ResearchState, 
        config: RunnableConfig
    ) -> Literal["accept", "revise"]:

        configuration = Configuration.from_runnable_config(config)
        if not state.get("human_feedback"):
            return "accept"
        # Human counts rejection events; <= permits exactly N replans.
        if state.get("plan_review_loop_count", 0) > configuration.max_plan_revisions:
            raise RuntimeError("Plan still rejected after the maximum number of revisions")
        return "revise"

    def route_fact_check(
        self,
        state: ResearchState,
        config: RunnableConfig,
    ) -> Literal["accept", "revise"]:

        configuration = Configuration.from_runnable_config(config)

        if not state.get("fact_check_notes"):
            return "accept"

        revision_count = state.get("fact_check_revision_count", 0)

        if revision_count >= configuration.max_fact_check_revisions:
            raise RuntimeError(
                "Fact checking still found issues after the maximum "
                f"number of revisions:\n{state['fact_check_notes']}"
            )

        return "revise"
