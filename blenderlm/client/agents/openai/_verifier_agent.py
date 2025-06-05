from typing import Optional

class VerifierAgent:
    """
    An agent that verifies whether a Blender task (or step) is complete, given the user task, recent tool log, and current Blender scene state.
    Usage: await VerifierAgent(model_name, api_key).run(task, tool_log)
    """
    def __init__(self, model_name: str = "gpt-4.1", api_key: Optional[str] = None):
        from openai import AsyncOpenAI
        import os
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name

    async def run(self, task, tool_log=None):
        """
        Verifies if the given task is complete using the current Blender scene and tool log.
        Args:
            task: AgentTask or str
            tool_log: list of str (recent tool actions)
        Returns:
            VerificationStatus
        """
        from ._oai_utils import get_blender_scene_state
        from .._base_agent import VerificationStatus
        user_task = task.to_text() if hasattr(task, 'to_text') else str(task)
        tool_log = tool_log or []
        tool_call_log_str = '\n'.join(tool_log[-5:]) if tool_log else 'No tool calls yet.'
        verification_prompt = f"""
You are a highly qualified 3D verification expert that can verify or evaluate the work of another agent who has attempted to complete a user's task in Blender.
You will be given information on the task, the current status of the task (the objects in the scene, a capture of the blender viewport), and a log of recent tool actions taken by the agent.

The user's task is: {user_task}
The recent set of tool actions taken so far are:\n{tool_call_log_str}

If these actions address the user's task and the current scene matches the expected result, consider the task complete. Your judgement should take into consideration the work done so far, should lean towards approval if uncertain given that you might not see the entire scene or might not be able to see things like colors, sides of objects, etc.

Please provide a verification status. This will include a boolean status indicating if the task is complete, a reason for the status, and a description of the next steps if the task is not complete. The next steps can consider building on the progress so far (e.g., what needs to be added or removed to address the task).
"""
        scene_state = await get_blender_scene_state()
        messages = [
            {"role": "system", "content": verification_prompt},
            scene_state,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_task}
                ]
            }
        ]
        response = await self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            response_format=VerificationStatus,
        )
        result = response.choices[0].message.parsed if response and response.choices and response.choices[0].message and hasattr(
            response.choices[0].message, 'parsed') else None
        if not result:
            return VerificationStatus(status=False, reason="Verification failed: No result returned.", next_step="Check the task and try again.")
        return result
