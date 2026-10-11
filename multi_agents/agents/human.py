from ..memory import ResearchState
from ...configuration import Configuration
from langchain_core.runnables import RunnableConfig
import asyncio
class HumanAgent:
    def __init__(self, 
                 queue: asyncio.Queue = None,
                 feedback_queue: asyncio.Queue = None,
                 stream_output = None):

        self.message_queue = queue
        self.feedback_queue = feedback_queue
        self.stream_output = stream_output 


    async def plan_review(
        self,
        state: ResearchState,
        config: RunnableConfig,
    ) -> dict:
        configuration = Configuration.from_runnable_config(config)

        plan_review_loop_count = state.get("plan_review_loop_count", 0)
        human_feedback = None

        if configuration.include_human_feedback:
            if any(x is not None for x in (self.message_queue, self.feedback_queue, self.stream_output)):
                if self.message_queue is None or self.stream_output is None or self.feedback_queue is None:
                    raise ValueError("Queue mode requires queue, feedback_queue and stream_output")

                await self.stream_output(
                    self.message_queue,
                    {
                        "type": "human_feedback_request",
                        "data": {
                            "message": "Please review the plan. Reply 'no' if approved.",
                            "sections": state["sections"],
                        },
                    },
                )

                feedback = await self.feedback_queue.get()

            else:
                feedback = await asyncio.to_thread(
                    input,
                    f"Any feedback on this plan? {state['sections']} "
                    "If not, please reply with 'no'.\n>> ",
                )

            if not isinstance(feedback, str):
                raise TypeError("Human feedback must be a string")

            human_feedback = feedback.strip()

            if not human_feedback or human_feedback.lower() == "no":
                human_feedback = None

            if human_feedback:
                plan_review_loop_count += 1

        return {
            "human_feedback": human_feedback,
            "plan_review_loop_count": plan_review_loop_count,
        }
