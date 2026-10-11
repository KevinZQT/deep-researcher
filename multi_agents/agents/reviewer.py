import asyncio

from langchain_core.runnables import RunnableConfig

from ...configuration import Configuration
from ..memory import DraftState
from .utils.llms import create_model
from .utils.prompts import review_instructions


class ReviewerAgent:
    def __init__(self, queue: asyncio.Queue = None, stream_output=None):
        self.queue = queue
        self.stream_output = stream_output

    async def run(self, state: DraftState, config: RunnableConfig) -> dict:
        configuration = Configuration.from_runnable_config(config)
        review = await self.review_draft(state, configuration)

        revision_count = state.get("draft_revision_count", 0)


        return {
            "review": review,
            "draft_revision_count": revision_count,
        }

    async def review_draft(
        self, state: DraftState, configuration: Configuration
    ) -> str | None:
        task = state.get("task") or {}
        raw_guidelines = (
            task.get("guideline") if task.get("follow_guideline") else None
        )
        if not isinstance(raw_guidelines, (list, tuple)):
            raw_guidelines = [raw_guidelines] if raw_guidelines else []
        guidelines = "\n".join(
            f"- {str(item).strip()}"
            for item in raw_guidelines
            if item is not None and str(item).strip()
        )
        revision_notes = state.get("revision_notes")

        formatted_prompt = review_instructions.format(
            review_stage="re-review" if state.get("review") or revision_notes else "initial review",
            guidelines=guidelines or "No additional guidelines. Apply general quality criteria.",
            revision_notes=revision_notes or "No previous revisions.",
            draft=state["draft"],
        )

        model = create_model(configuration.reviewer_model)
        response = await model.ainvoke(formatted_prompt)
        content = response.content

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(
                block if isinstance(block, str) else block["text"]
                for block in content
                if isinstance(block, str)
                or (
                    isinstance(block, dict)
                    and block.get("type") == "text"
                    and isinstance(block.get("text"), str)
                )
            )
        else:
            raise TypeError("Reviewer response content must be text or content blocks")

        review = text.strip()
        if not review:
            raise ValueError("Reviewer returned an empty review; approval requires 'no'")

        return None if review.lower() == "no" else review
