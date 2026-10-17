import asyncio

from langchain_core.runnables import RunnableConfig

from ..memory import ResearchState


class PublisherAgent:
    def __init__(
        self,
        queue: asyncio.Queue | None = None,
        stream_output=None,
    ):
        self.queue = queue
        self.stream_output = stream_output

    async def run(
        self,
        state: ResearchState,
        config: RunnableConfig,
    ) -> dict:
        if self.queue is not None and self.stream_output is not None:
            await self.stream_output(
                self.queue,
                {
                    "type": "research_update",
                    "data": {
                        "status": "running",
                        "step": "Finalizing the report",
                    },
                },
            )
        else:
            print("Publisher --- finalizing the report...")

        final_report = self.finalize_report(state)

        return {"report": final_report}

    def finalize_report(self, state: ResearchState) -> str:
        research_data = state.get("research_data") or []
        if not isinstance(research_data, (list, tuple)):
            research_data = [research_data]

        sections = []

        for section in research_data:
            if isinstance(section, dict):
                for value in section.values():
                    if value is not None:
                        sections.append(str(value))
            elif section is not None:
                sections.append(str(section))

        sections_text = "\n\n".join(sections)

        sources = state.get("sources") or []
        if not isinstance(sources, (list, tuple)):
            sources = [sources]

        references = "\n".join(
            str(source) for source in sources if source is not None
        )

        headers = state.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}

        title = headers.get("title") or state.get("title") or "Research Report"
        date_label = headers.get("date") or "Date"
        introduction_label = headers.get("introduction") or "Introduction"
        contents_label = headers.get("table_of_contents") or "Table of Contents"
        conclusion_label = headers.get("conclusion") or "Conclusion"
        references_label = headers.get("references") or "References"

        date = state.get("date") or ""
        introduction = state.get("introduction") or ""
        contents = state.get("table_of_contents") or ""
        conclusion = state.get("conclusion") or ""

        diagrams = state.get("diagrams") or []
        if not isinstance(diagrams, (list, tuple)):
            diagrams = [diagrams]

        diagrams_text = "\n\n".join(
            str(diagram) for diagram in diagrams if diagram
        )

        parts = [
            f"# {title}",
            f"#### {date_label}: {date}" if date else "",
            f"## {introduction_label}\n\n{introduction}",
            f"## {contents_label}\n\n{contents}",
            sections_text,
            f"## {conclusion_label}\n\n{conclusion}",
            f"## Visualizations\n\n{diagrams_text}" if diagrams_text else "",
            f"## {references_label}\n\n{references}",
        ]

        return "\n\n".join(part for part in parts if part) + "\n"
