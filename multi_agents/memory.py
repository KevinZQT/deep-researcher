"""State contract used by the repaired graph. Merge if memory is a package."""
from typing import Any, TypedDict

class ResearchState(TypedDict, total=False):
    task: dict[str, Any]
    initial_research: str
    title: str
    date: str
    sections: list[str]
    human_feedback: str | None
    plan_review_loop_count: int
    research_data: list[str]
    introduction: str
    conclusion: str
    table_of_contents: str
    sources: list[str]
    headers: dict[str, str]
    fact_check_notes: str | None
    fact_check_revision_count: int
    diagrams: list[str]
    report: str

class DraftState(TypedDict, total=False):
    task: dict[str, Any]
    title: str
    topic: str
    draft: str
    review: str | None
    revision_notes: str | None
    draft_revision_count: int
