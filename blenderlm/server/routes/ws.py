from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...client.agents import OpenAIAgent
from ...client.tools import get_blender_tools
import asyncio
import json
import logging

router = APIRouter(prefix="/api/blender", tags=["blender-ws"])
logger = logging.getLogger("blenderlm.api.ws")

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    print(" WebSocket connection established")
    agent_task = None
    cancel_event = asyncio.Event()
    try:
        tools = await get_blender_tools(session_id=None)
        agent = OpenAIAgent(
            tools=tools,
            model_name="gpt-4.1-mini",
        )
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "start":
                query = data.get("query", "")
                cancel_event.clear()
                async def send_updates():
                    async for update in agent.run_stream(query, cancel_event=cancel_event):
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
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.close(code=1011)
