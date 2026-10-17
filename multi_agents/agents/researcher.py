from ..memory import ResearchState
from ..memory import DraftState
from ...configuration import Configuration
from .utils.content import text_content
from langchain_core.runnables import RunnableConfig
import asyncio



class ResearcherAgent:

    def __init__(self, queue: asyncio.Queue = None, stream_output = None, engine_factory=None):

        self.queue = queue
        self.stream_output = stream_output
        self.engine_factory = engine_factory 

    async def generate_result(
        self,
        topic: str,
        configuration: Configuration,
        parent_topic: str = None,
        report_type: str = "research_report",
        verbose: bool = True,
        source: str = "web",
    ):
        if source != "web":
            raise ValueError("当前 Researcher 只支持 web 搜索")

        factory = self.engine_factory

        if factory is None:
            from ...researcher import Researcher
            factory = Researcher

        # 你的 Researcher.__init__() 不接受配置参数
        engine = factory()

        query = (
            f"Overall research topic: {parent_topic}\n"
            f"Research this section only: {topic}"
            if parent_topic
            else topic
        )

        engine_config: RunnableConfig = {
            "configurable": configuration.model_dump(mode="json"),
            "recursion_limit": max(
                25,
                4 * configuration.max_search_loops + 10,
            ),
        }

        # 调用研究引擎已有的 run() 方法
        generated_report = await engine.run(
            search_query=query,
            config=engine_config,
        )

        report = text_content(generated_report).strip()

        if not report:
            raise ValueError("Researcher returned an empty report")

        return report

    async def run_initial_research(self, state: ResearchState, config: RunnableConfig):
        configuration = Configuration.from_runnable_config(config)
        task = state.get("task")
        research_topic = task.get("topic")
        source = task.get("source", "web")
        verbose = task.get("verbose", True)

        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue, 
                {"type": "research_update",
                 "data": {
                     "message": f"Running initial research on the following topic: {research_topic}"
                     }
                 }
            )
        else:
            print(f"Researcher --- Running initial research on the following topic: {research_topic}" )
        result = await self.generate_result(research_topic, configuration, source = source, verbose = verbose)
        return {
            "initial_research": result
        }

    async def run_depth_research(self, state: DraftState, config: RunnableConfig) -> DraftState:
        configuration = Configuration.from_runnable_config(config)
        topic = state.get("topic")
        task = state.get("task")
        parent_topic = task.get("topic")
        source = task.get("source", "web")
        verbose = task.get("verbose", True)
        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue, 
                {"type": "sub-research_update",
                 "data": {
                     "message": f"Running sub-research on the following subtopic: {topic}"
                     }
                 }
            )
        else:
            print(f"Researcher --- Running sub-research on the following subtopic: {topic}" )

        result = await self.generate_result(
            topic = topic, 
            configuration = configuration,
            report_type = "subtopic_report",
            parent_topic = parent_topic,
            source = source,
            verbose = verbose
            )

        return {
            "draft": result
        }
