from fastapi import APIRouter, Request, HTTPException
from typing import List
from ..models import ToolInfo

router = APIRouter(tags=["misc"])

@router.get("/")
async def root():
    return {"status": "BlenderLM API is running"}

@router.get("/health")
async def health_check(request: Request):
    health = {
        "status": "ok",
        "blender_connected": False
    }
    try:
        if await request.app.state.blender_manager.ensure_connected():
            health["blender_connected"] = True
    except Exception as e:
        health["status"] = "degraded"
        health["error"] = str(e)
    return health

@router.get("/api/tools", response_model=List[ToolInfo])
async def list_tools():
    tools = [
        ToolInfo(
            name="create_object",
            description="Create a new 3D object in Blender",
            parameters={
                "type": "The type of object to create (CUBE, SPHERE, CYLINDER, etc.)",
                "name": "Optional name for the object",
                "location": "Optional [x, y, z] location coordinates",
                "rotation": "Optional [x, y, z] rotation in radians",
                "scale": "Optional [x, y, z] scale factors",
                "color": "Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0) to apply directly",
            },
            endpoint="/api/blender/objects"
        ),
        ToolInfo(
            name="capture_viewport",
            description="Capture the current viewport using OpenGL rendering",
            parameters={
                "filepath": "Optional path to save the captured image",
                "camera_view": "Optional boolean to switch to camera view before capture",
                "return_base64": "Optional boolean to return the image as base64 (default: True)"
            },
            endpoint="/api/blender/viewport"
        ),
        ToolInfo(
            name="modify_object",
            description="Modify an existing object in Blender",
            parameters={
                "name": "Name of the object to modify",
                "location": "Optional [x, y, z] location coordinates",
                "rotation": "Optional [x, y, z] rotation in radians",
                "scale": "Optional [x, y, z] scale factors",
                "visible": "Optional boolean to set visibility",
            },
            endpoint="/api/blender/objects/{name}"
        ),
        ToolInfo(
            name="delete_object",
            description="Delete an object from the scene",
            parameters={
                "name": "Name of the object to delete",
            },
            endpoint="/api/blender/objects/{name}"
        ),
        ToolInfo(
            name="set_material",
            description="Set or create a material for an object",
            parameters={
                "object_name": "Name of the object to apply material to",
                "material_name": "Optional name for the material",
                "color": "Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0)",
            },
            endpoint="/api/blender/materials"
        ),
        ToolInfo(
            name="render_scene",
            description="Render the current scene",
            parameters={
                "output_path": "Optional path to save the render",
                "resolution_x": "Optional width in pixels",
                "resolution_y": "Optional height in pixels",
            },
            endpoint="/api/blender/render"
        ),
        ToolInfo(
            name="execute_code",
            description="Execute arbitrary Python code in Blender",
            parameters={
                "code": "The Python code to execute",
            },
            endpoint="/api/blender/code"
        ),
        ToolInfo(
            name="get_scene_info",
            description="Get information about the current scene",
            parameters={},
            endpoint="/api/blender/scene"
        ),
        ToolInfo(
            name="get_object_info",
            description="Get information about a specific object",
            parameters={
                "name": "Name of the object to get information about",
            },
            endpoint="/api/blender/objects/{name}"
        ),
    ]
    return tools

@router.get("/api/tools/{name}", response_model=ToolInfo)
async def get_tool_info(name: str):
    tools = await list_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise HTTPException(status_code=404, detail=f"Tool {name} not found")
