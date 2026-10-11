import asyncio 
from uuid import uuid4
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.websockets import WebSocketState
from typing import Any
import os
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


# job1/.env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

from ..multi_agents.orchestrator import ChiefAgent




app = FastAPI()
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app.mount(
    "/frontend",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="frontend",
)

@app.get("/", include_in_schema=False)
async def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

tasks: dict[str, Any] = {}
running_tasks: dict[str, asyncio.Task] = {}
feedback_queues: dict[str, asyncio.Queue] = {}

class WebSocketManager:
    def __init__(self):
        self.message_queues: dict[str,asyncio.Queue] = {}

    def create_queue(self, task_id:str):
        self.message_queues[task_id] = asyncio.Queue()

    def get_queue(self, task_id:str):
        return self.message_queues[task_id]

    async def send_messages(self, task_id:str, message: dict):

        await self.get_queue(task_id).put(message)
        

    async def start_sender(self, websocket: WebSocket, task_id: str):
        queue = self.get_queue(task_id)

        while True:
            message = await queue.get()
            await websocket.send_json(message)

            if message.get("type") == "research_update":
                status = message.get("data", {}).get("status")

                if status in {"cancelled", "failed", "completed"}:
                    return


    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    async def disconnet(self, websocket:WebSocket):
        
        if(
            websocket.client_state == WebSocketState.CONNECTED
            and websocket.application_state == WebSocketState.CONNECTED
        ):
           await websocket.close()   
        

manager = WebSocketManager()
class ResearchRequest(BaseModel):
    topic: str

async def receive_messages(websocket: WebSocket, queue:asyncio.Queue, task_id:str):
    while True:
        try:
            message = await websocket.receive_json()
        except ValueError:
            await queue.put({
                "type": "error",
                "data":{"message": "Invalid JSON"}
            })
            continue

        if not isinstance(message, dict):
            await queue.put({
                "type": "error",
                "data": {"message": "Command must be a JSON object"},
            })
            continue

        command = message.get("command")

        if command == "ping":
            await queue.put({
                "type": "pong",
                "data":{}
            })

        elif command == "start":
            await handle_start_command(message, task_id, queue)

        elif command == "feedback":
            feedback = message.get("feedback")
            if tasks[task_id]['status'] != "waiting_for_feedback":
                await queue.put({
                    "type": "error",
                    "data": {"message": "Research is not waiting for feedback"},
                })
                continue
            if not isinstance(feedback, str) or not feedback.strip():
                await queue.put({
                    "type": "error",
                    "data": {"message": "Non-empty feedback is required"},
                })
                continue
            tasks[task_id]['status'] = 'running'
            await feedback_queues[task_id].put(feedback.strip())

                
        elif command == "cancel":
            await cancel_task(task_id)

    
        else:
            await queue.put({
                "type": "error",
                "data": {
                    "message": f"Unknown command: {command}",
                },
            })


async def update_task(task_id:str, **changes):
    tasks[task_id].update(changes)
    await manager.send_messages(task_id,
        {"type": "research_update",
         "data": tasks[task_id].copy()
         }
    )


async def run_research(task_id: str, topic: str):
    async def on_progress(step:str):
        await update_task(task_id, step=step)

    async def get_feedback(outline: str) -> str:
        await update_task(
            task_id, 
            step="Waiting for your feedback",
            status = "waiting_for_feedback"
            )
        await manager.send_messages(
            task_id,
            {
                "type":"feedback_report",
                "data":{"outline": outline}
            }
        )
        feedback = await feedback_queues[task_id].get()

        await update_task(
            task_id,
            status="running",
            step="Feedback received",
        )
        return feedback
        
    try:
        await update_task(
                task_id, 
                status = "running",
                step = "searching for sources"
            )
        report = await run_agent(task_id, topic, on_progress)

        await update_task(
            task_id,
            step= "Completed",
            status = "completed",
            report = report
        ) 

            
    except asyncio.CancelledError:
        await update_task(
            task_id,
            status = "cancelled",
            step = "Research cancelled"
        )
        raise

    except Exception as e:
        await update_task(
                task_id, 
                step = "Failed",
                status = "failed",
                error = str(e)
            )  

async def run_agent(
    task_id: str,
    topic: str,
    on_progress,
) -> str:
    model_id = (os.getenv("RESEARCH_MODEL_ID") or "").strip()

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError(f"请在 {env_path} 中设置 GEMINI_API_KEY")

    if not model_id or model_id == "你已验证可用的Gemini模型ID":
        raise ValueError(f"请在 {env_path} 中设置真实的 RESEARCH_MODEL_ID")

    agent_model = f"google_genai/{model_id}"

    task = {
        "topic": topic,
        "source": "web",
        "verbose": True,
        "include_human_feedback": False,

        "max_sections": 2,
        "max_generated_queries": 1,
        "max_search_loops": 1,

        "query_generate_model": model_id,
        "search_model": model_id,
        "refleciton_model": model_id,
        "answer_model": model_id,

        "planner_model": agent_model,
        "reviewer_model": agent_model,
        "reviser_model": agent_model,
        "writer_model": agent_model,
        "fact_checker_model": agent_model,
        "visualizer_model": agent_model,
    }

    await on_progress("Running multi-agent research")

    chief = ChiefAgent(
        task=task,
        task_id=task_id,
    )

    result = await chief.run_research()

    report = result.get("report")

    if not isinstance(report, str) or not report.strip():
        raise ValueError("ChiefAgent 没有返回有效的文本报告")

    return report


@app.post("/research")
async def start_research(request: ResearchRequest):

    task_id = str(uuid4())

    tasks[task_id] = {
        "status": "pending",
        "step": "Waiting for start",
        "report": None,
        "topic": request.topic
    }

    manager.create_queue(task_id)
    feedback_queues[task_id] = asyncio.Queue()
    running_tasks[task_id] = asyncio.create_task(run_research(task_id, request.topic))

    return{
        "task_id": task_id,
        "status": "pending"
    }


@app.get("/research/{task_id}")
async def get_research(task_id: str):
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail="Task doesn't exist",
        )

    return {
        "task_id": task_id,
        **tasks[task_id],
    }


@app.websocket("/ws/research/{task_id}")
async def research_update(websocket: WebSocket, task_id:str):

    await manager.connect(websocket)

    if task_id not in tasks:
        await websocket.send_json({"error": "wrong"})
        await websocket.close()
        return


    await handle_websocket_communication(websocket,task_id,manager)
    
@app.websocket("/ws")
async def research_socket(websocket:WebSocket):

    await manager.connect(websocket)

    task_id = str(uuid4())

    tasks[task_id] = {
        "step": "Waiting for start command",
        "status": "pending",
        "report": None,
        "topic": None
    }
    manager.create_queue(task_id)
    feedback_queues[task_id] = asyncio.Queue()

    await manager.send_messages(task_id,{
        "type": "connected",
        "data": {"task_id": task_id}
    })

    await handle_websocket_communication(
        websocket, task_id, manager
    )
    
@app.delete("/research/{task_id}")
async def cancel_research(task_id:str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return await cancel_task(task_id)
    


async def cancel_task(task_id:str):
    task = running_tasks.get(task_id)
    if task is None:
        await update_task(
            task_id,
            status = "cancelled",
            step = "Research cancelled before starting"
        )
        return {
            "task_id": task_id,
            "status": tasks[task_id]['status']
        }
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return{
            "task_id": task_id,
            "status": tasks[task_id]['status']
        }

async def handle_websocket_communication(
        websocket:WebSocket,
        task_id: str,
        manager: WebSocketManager
):
    queue = manager.get_queue(task_id)
    sender = asyncio.create_task(manager.start_sender(websocket, task_id))
    receiver = asyncio.create_task(receive_messages(websocket,queue,task_id))

    try:
        done, pending  = await asyncio.wait(
            {sender, receiver},
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            task.result()
    except WebSocketDisconnect:
            print("Client disconnected:", task_id)
            
    finally:
        for task in (sender, receiver):
            task.cancel()

        await asyncio.gather(sender, receiver, return_exceptions=True)

        await manager.disconnet(websocket)


async def handle_start_command(
    message: dict[str, Any],
    task_id: str,
    queue: asyncio.Queue,
):
    
    if tasks[task_id]['status'] != "pending":
        await queue.put({
            "type": "error",
            "data": {"message": "Research has already started"},
        })
        return 

    topic = message.get("topic")

    if not isinstance(topic, str) or not topic.strip():
        await queue.put({
            "type": "error",
            "data": {"message": "A non-empty topic is required"},
        })

        return

    tasks[task_id]['topic'] = topic
    tasks[task_id]["status"] = "running"

    running_tasks[task_id] = asyncio.create_task(run_research(task_id, topic))
    