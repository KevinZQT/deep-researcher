from pydantic import BaseModel, Field
from datetime import datetime, timezone
from langchain_core.runnables import RunnableConfig, ensure_config
from typing import Dict, Any, Literal
import os

class Configuration(BaseModel):

    # researcher fields
    thread_id: str | None = None
    thread_ts: datetime = Field(
        default_factory = lambda: datetime.now(timezone.utc)
    )
    
    search_model: str = Field(default = "gemini-3.8-flash")
    query_generate_model: str = Field(default = "gemini-3.8-flash")
    refleciton_model: str = Field(default = "gemini-3.8-flash")
    answer_model: str = Field(default = "gemini-3.8-flash")

    max_search_loops: int = Field(default=3)
    max_generated_queries : int = Field(default=3)

    # multi_agent fields
    planner_model: str
    reviewer_model: str
    reviser_model: str
    writer_model: str
    fact_checker_model: str
    visualizer_model: str

    include_human_feedback: bool = False

    max_sections: int = Field(default=3, ge=1)

    max_plan_revisions: int = Field(default=2, ge=0)
    max_draft_revisions: int = Field(default=2, ge=0)
    max_fact_check_revisions: int = Field(default=2, ge=0)




    @classmethod 
    def from_runnable_config(cls, config: RunnableConfig):

        config = ensure_config(config)
        configurable = config.get("configurable", {})

        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)
        