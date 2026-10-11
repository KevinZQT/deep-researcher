from ..memory import ResearchState
from ...configuration import Configuration
from langchain_core.runnables import RunnableConfig
from .utils.prompts import visualizer_instructions
from .utils.llms import create_model
from .utils.content import text_content
import asyncio

class VisualizerAgent:
    def __init__(self, queue: asyncio.Queue = None, stream_output = None):

        self.queue = queue
        self.stream_output = stream_output 

    async def run(self, state:ResearchState, config: RunnableConfig) -> ResearchState:
        configuration = Configuration.from_runnable_config(config)
        if self.queue is not None and self.stream_output is not None:
                    await self.stream_output(
                        self.queue,
                        {
                            "type": "research_update",
                            "data": {
                                "message": f"Visualizing the report"
        
                            },
                        }
                    )
        else:
            print(f"Visualizer --- Visualizing the report...")


        raw_diagrams = await self.generate_visualizations(state, configuration)

        if not isinstance(raw_diagrams, str):
            raise TypeError("Visualizer output must be text")

        text = raw_diagrams.strip()
        diagrams = [text] if text and text.lower() not in {"none", "no"} else []

        return {"diagrams": diagrams}

    async def generate_visualizations(self, state: ResearchState, configuration: Configuration):
        task = state.get("task")
        data = state.get("research_data", [])

        formatted_prompt = visualizer_instructions.format(
             data = data
        )

        model = create_model(configuration.visualizer_model)
        response = await model.ainvoke(formatted_prompt)
        return text_content(response)
