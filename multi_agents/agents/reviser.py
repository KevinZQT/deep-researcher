from ..memory import DraftState
from ...configuration import Configuration
from .utils.prompts import reviser_instructions
from .utils.llms import create_model
from .utils.tool_and_schema import ReviserOutput
from langchain_core.runnables import RunnableConfig
import asyncio



class ReviserAgent:
    def __init__(self, queue: asyncio.Queue = None, stream_output = None):
        self.queue = queue
        self.stream_output = stream_output 

    
    async def run(self, state: DraftState, config: RunnableConfig) -> DraftState:
        configuration = Configuration.from_runnable_config(config)
        revision = await self.revise_draft(state, configuration)
        return {
            "draft": revision.draft,
            "draft_revision_count": state.get("draft_revision_count", 0) + 1,
            "revision_notes": revision.revision_notes,
        }


    async def revise_draft(self, state: DraftState, configuration:Configuration):

        review = state.get("review")
        task = state.get("task")
        draft_report = state.get("draft")

        formatted_prompt = reviser_instructions.format(
            draft_report = draft_report,
            review = review
        )

        model = create_model(configuration.reviser_model)

        response = await model.with_structured_output(
            ReviserOutput).ainvoke(formatted_prompt)

        return ReviserOutput.model_validate(response)
