from ..memory import ResearchState
from ...configuration import Configuration
from langchain_core.runnables import RunnableConfig
from .utils.tool_and_schema import WriterModelOutput, HeaderOutput

from .utils.prompts import (
    get_current_date,
    writer_instructions,
    header_revision_instructions,
    writer_sample
)
from .utils.llms import create_model
import asyncio

class WriterAgent:
    def __init__(self, queue: asyncio.Queue = None, stream_output = None):

        self.queue = queue
        self.stream_output = stream_output 


    async def run(self, state: ResearchState, config: RunnableConfig):
        configuration = Configuration.from_runnable_config(config)

        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue,
                {
                    "type": "research_update",
                    "data": {
                        "message": f"Writing the report"

                    },
                }
            )
        else:
            print(f"Writer --- Writing the report...")

        content = await self.write_sections(state, configuration)
        raw_headers = self.get_headers(state)
        headers = await self.revise_headers(state, raw_headers, configuration)
        return {
            **content, "headers": headers,
            "fact_check_revision_count": state.get("fact_check_revision_count", 0) + int(bool(state.get("fact_check_notes")))
        }

        
    async def write_sections(self, state: ResearchState, configuration:Configuration):
        topic = state.get("title")
        data = state.get("research_data")
        task = state.get("task")
        follow_guideline = task.get("follow_guideline")
        guideline = task.get("guideline") if follow_guideline else ""

        fact_check_notes = state.get("fact_check_notes")

        if fact_check_notes:
            fact_note_str = (
                f"Fact Checker Notes: {fact_check_notes}."
                "You MUST revise the introduction and conclusion"
                " and sources to address these issues.\n"
            )
        else:
            fact_note_str = ""

        formatted_prompt = writer_instructions.format(
            date = get_current_date(),
            topic = topic,
            data = str(data),
            fact_note = fact_note_str,
            guideline = guideline,
            sample = writer_sample
        )


        model = create_model(configuration.writer_model)

        response = await model.with_structured_output(
            WriterModelOutput).ainvoke(formatted_prompt)

        return WriterModelOutput.model_validate(response).model_dump()



    def get_headers(self, state: dict):
        return {
            "title": state.get("title"),
            "date": "Date",
            "introduction": "Introduction",
            "table_of_contents": "Table of Contents",
            "conclusion": "Conclusion",
            "references": "References",
        }
    async def revise_headers(self, state: ResearchState, headers: dict, configuration: Configuration):
        task = state.get("task") or {}
        if not task.get("follow_guideline") or not task.get("guideline"):
            return headers
        guideline = task["guideline"]
        formatted_prompt = header_revision_instructions.format(
            guideline = guideline,
            headers = headers
        )

        model = create_model(configuration.writer_model)

        response = await model.with_structured_output(
            HeaderOutput).ainvoke(formatted_prompt)

        return HeaderOutput.model_validate(response).model_dump()
