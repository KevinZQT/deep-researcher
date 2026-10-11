"""Check Writer output against the research supplied in state.

This node does not browse or independently authenticate source URLs.
The graph must invoke it once after each successful Writer run.
"""

import asyncio
import json
from typing import Literal

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from ..memory import ResearchState
from ...configuration import Configuration
from .utils.llms import create_model
from .utils.prompts import fact_check_instructions


class FactCheckIssue(BaseModel):
    section: Literal["introduction", "conclusion", "sources"]
    kind: Literal["contradiction", "unsupported", "citation_mismatch"]
    claim: str = Field(min_length=1, description="Exact problematic text or reference.")
    evidence: str = Field(
        min_length=1,
        description="Relevant supplied passage, or a specific explanation of missing evidence.",
    )
    correction: str = Field(
        min_length=1, description="An actionable correction within the Writer's scope."
    )


class FactCheckOutput(BaseModel):
    issues: list[FactCheckIssue] = Field(
        description="Substantive issues in Writer output; an empty list means none found."
    )


class FactCheckerAgent:
    def __init__(self, queue: asyncio.Queue | None = None, stream_output=None):
        self.queue = queue
        self.stream_output = stream_output

    async def run(self, state: ResearchState, config: RunnableConfig) -> dict:
        configuration = Configuration.from_runnable_config(config)

        # Fail visibly if upstream Writer output has not reached state.
        for field in ("introduction", "conclusion"):
            if not isinstance(state.get(field), str) or not state[field].strip():
                raise ValueError(f"FactChecker requires a non-empty {field} from Writer")
        sources = state.get("sources")
        if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
            raise ValueError("FactChecker requires sources to be a list of strings")
        if not state.get("research_data"):
            raise ValueError("FactChecker requires research_data as supporting evidence")

        await self.emit("Checking Writer output against the supplied research...")
        result = await self.check_facts(state, configuration)

        revision_count = state.get("fact_check_revision_count", 0)

        notes = self.format_notes(result)
        await self.emit(
            f"Found {len(result.issues)} issue(s) for Writer to address."
            if notes
            else "No substantive issues found against the supplied research."
        )

        return {
            "fact_check_notes": notes,
            "fact_check_revision_count": revision_count,
        }

    async def check_facts(
        self, state: ResearchState, configuration: Configuration
    ) -> FactCheckOutput:
        model_name = getattr(configuration, "fact_checker_model", None)
        if not model_name:
            model_name = configuration.writer_model

        report = {
            "title": state.get("title"),
            "introduction": state["introduction"],
            "conclusion": state["conclusion"],
            "sources": state["sources"],
        }
        prompt = fact_check_instructions.format(
            research_data=json.dumps(state["research_data"], ensure_ascii=False),
            report=json.dumps(report, ensure_ascii=False),
            previous_notes=state.get("fact_check_notes") or "No previous issues.",
        )
        model = create_model(model_name).with_structured_output(FactCheckOutput)
        result = await model.ainvoke(prompt)
        # Validate any dictionary result too; malformed output must not become a pass.
        return FactCheckOutput.model_validate(result)

    @staticmethod
    def format_notes(result: FactCheckOutput) -> str | None:
        if not result.issues:
            return None
        return "\n\n".join(
            f"{index}. [{issue.section} / {issue.kind}]\n"
            f"Claim: {issue.claim}\n"
            f"Evidence: {issue.evidence}\n"
            f"Required correction: {issue.correction}"
            for index, issue in enumerate(result.issues, start=1)
        )

    async def emit(self, message: str) -> None:
        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue,
                {"type": "research_update", "data": {"message": message}},
            )
        else:
            print(f"Fact Checker --- {message}")
