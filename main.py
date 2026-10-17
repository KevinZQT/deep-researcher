import asyncio
import argparse
import importlib
import sys
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv


def import_project_module(name):
    root = Path(__file__).resolve().parent
    parent = str(root.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return importlib.import_module(f"{root.name}.{name}")


async def run_research_example():
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("请在项目根目录的 .env 中设置 GEMINI_API_KEY")

    model_id = os.getenv("RESEARCH_MODEL_ID")

    if not model_id:
        raise ValueError(
            "请设置 RESEARCH_MODEL_ID，填写你已验证可用的 Gemini 模型 ID"
        )

    ChiefAgent = import_project_module("multi_agents.orchestrator").ChiefAgent
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deep Researcher")
    parser.add_argument("--cli", action="store_true", help="Run the example research topic")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default: 8000)")
    args = parser.parse_args(argv)
    if args.cli:
        asyncio.run(run_research_example())
    else:
        import uvicorn
        app = import_project_module("backend.app").app
        uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
