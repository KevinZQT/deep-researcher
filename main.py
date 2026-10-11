import asyncio
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv


async def main():
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("请在 researcher/.env 中设置 GEMINI_API_KEY")

    model_id = os.getenv("RESEARCH_MODEL_ID")

    if not model_id:
        raise ValueError(
            "请设置 RESEARCH_MODEL_ID，填写你已验证可用的 Gemini 模型 ID"
        )

    from .multi_agents.orchestrator import ChiefAgent

    agent_model = f"google_genai/{model_id}"

    task = {
        "topic": "Explainable AI methods for spectroscopy",

        "source": "web",
        "verbose": True,

        # initial search
        "include_human_feedback": False,
        "max_sections": 2,
        "max_generated_queries": 1,
        "max_search_loops": 1,

        # Researcher 
        "query_generate_model": model_id,
        "search_model": model_id,
        "refleciton_model": model_id,
        "answer_model": model_id,

        # multi-agent 
        "planner_model": agent_model,
        "reviewer_model": agent_model,
        "reviser_model": agent_model,
        "writer_model": agent_model,
        "fact_checker_model": agent_model,
        "visualizer_model": agent_model,
    }

    chief = ChiefAgent(
        task=task,
        task_id=str(uuid4()),
    )

    result = await chief.run_research()

    print("\n===== Final Report =====\n")
    print(result["report"])


if __name__ == "__main__":
    asyncio.run(main())