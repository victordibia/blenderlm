from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...client.agents import OpenAIAgent
from ...client.tools import get_blender_tools
import asyncio
import json
import logging
from PIL import Image
import base64
from io import BytesIO
from ...client.agents import AgentTask

router = APIRouter(prefix="/api/blender", tags=["blender-ws"])
logger = logging.getLogger("blenderlm.api.ws")

def parse_content_list(content_list):
    """Parse a list of content items (str or b64 image dict) into AgentTask content."""
    parsed = []
    for item in content_list:
        if isinstance(item, str):
            parsed.append(item)
        elif isinstance(item, dict) and item.get("type") == "image":
            b64_data = item.get("b64")
            img_format = item.get("format", "PNG")
            if b64_data:
                img_bytes = base64.b64decode(b64_data)
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                parsed.append(img)
    return parsed

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    print(" WebSocket connection established")
    agent_task = None
    cancel_event = asyncio.Event()
    try:
        tools = await get_blender_tools()
        agent = OpenAIAgent(
            tools=tools,
            model_name="gpt-4.1",
        )
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "start":
                content = data.get("content", "")
                cancel_event.clear()
                # Support both string and list for backward compatibility
                if isinstance(content, list):
                    task_content = parse_content_list(content)
                else:
                    task_content = content
                agent_task_obj = AgentTask(content=task_content)
                async def send_updates():
                    async for update in agent.run_stream(agent_task_obj, cancel_event=cancel_event):
                        await websocket.send_json(update.model_dump())
                agent_task = asyncio.create_task(send_updates())
            elif msg_type == "cancel":
                cancel_event.set()
            elif msg_type == "message":
                # For future: handle new user messages in a session
                pass
    except WebSocketDisconnect:
        if agent_task:
            agent_task.cancel()
        logger.info("WebSocket disconnected")
        if cancel_event:
            cancel_event.set()
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.close(code=1011)
