"""Companion schemas for this repair; merge with unrelated existing schemas."""
from pydantic import BaseModel, Field, ConfigDict

class Output(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

class ResearchPlan(Output):
    title: str = Field(min_length=1)
    date: str
    sections: list[str] = Field(min_length=1)

class ReviserOutput(Output):
    draft: str = Field(min_length=1, description="Complete revised section, not just its title")
    revision_notes: str

class WriterModelOutput(Output):
    introduction: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)
    table_of_contents: str
    sources: list[str] = Field(description="References copied from supplied research; never invented")

class HeaderOutput(Output):
    title: str = Field(min_length=1)
    date: str = Field(min_length=1)
    introduction: str = Field(min_length=1)
    table_of_contents: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)
    references: str = Field(min_length=1)
