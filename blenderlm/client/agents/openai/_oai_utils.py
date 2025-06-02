import inspect
import json
import asyncio
from typing import Callable, Optional, Dict, Any, List, Union
from openai.types.chat import ChatCompletionToolParam, ChatCompletionUserMessageParam
from PIL import Image

# --- TOOL SCHEMA GENERATION ---
def generate_tool_schema(func: Callable) -> Optional[ChatCompletionToolParam]:
    """
    Generate OpenAI function schema from a Python function.
    This is a basic implementation - you may want to enhance it with more sophisticated
    type inference or use a library like pydantic for better schema generation.
    """
    try:
        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
        for param_name, param in sig.parameters.items():
            param_info = {"type": "string", "description": f"Parameter {param_name}"}
            # Basic type inference
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == list:
                    param_info["type"] = "array"
                elif param.annotation == dict:
                    param_info["type"] = "object"
            parameters["properties"][param_name] = param_info
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)
        return ChatCompletionToolParam(
            type="function",
            function={
                "name": func.__name__,
                "description": func.__doc__ or f"Function {func.__name__}",
                "parameters": parameters,
                "strict": True
            }
        )
    except Exception as e:
        print(f"Warning: Could not generate schema for function {func.__name__}: {e}")
        return None

# --- TOOL EXECUTION ---
async def execute_tool(tool_map: Dict[str, Callable], tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool function and return the result as a string."""
    if tool_name not in tool_map:
        return f"Error: Tool '{tool_name}' not found"
    tool_func = tool_map[tool_name]
    try:
        # print(f"Executing tool: {tool_name} with args: {tool_args}")
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**tool_args)
        else:
            result = tool_func(**tool_args)
        if isinstance(result, str):
            return result
        elif isinstance(result, (dict, list)):
            return json.dumps(result, indent=2)
        else:
            return str(result)
    except Exception as e:
        error_msg = f"Error executing tool {tool_name}: {str(e)}"
        print(error_msg)
        return error_msg

# --- AGENT TASK TO OAI USER MESSAGE ---
def agent_task_to_oai_user_message(task) -> Union[ChatCompletionUserMessageParam, None]:
    """
    Converts an AgentTask (or str/list) to a single OpenAI user message param.
    Does NOT add system messages or app-specific logic.
    """
    if isinstance(task, str):
        return ChatCompletionUserMessageParam(role="user", content=task)
    elif isinstance(task, list):
        content = []
        for item in task:
            if isinstance(item, str):
                content.append({"type": "text", "text": item})
            elif isinstance(item, Image.Image):
                import io
                import base64
                buffer = io.BytesIO()
                item.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_str}"}
                })
            else:
                print(f"Warning: Unsupported type in task list: {type(item)}. Skipping.")
        if content:
            return ChatCompletionUserMessageParam(role="user", content=content)
        else:
            return None
    elif hasattr(task, 'content'):
        # AgentTask object
        return agent_task_to_oai_user_message(task.content)
    else:
        print(f"Warning: Unsupported task type: {type(task)}")
        return None
