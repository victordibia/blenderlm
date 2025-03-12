from typing import Dict, List, Optional, Union, Any
import httpx
from autogen_core.tools import FunctionTool
from autogen_core.code_executor import ImportFromModule


async def create_blender_object(
    type: str = "CUBE",
    name: Optional[str] = None,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None,
) -> str:
    """
    Create a new 3D object in Blender.

    Args:
        type: The type of object to create (CUBE, SPHERE, CYLINDER, PLANE, CONE, TORUS, EMPTY, CAMERA, LIGHT)
        name: Optional name for the object
        location: Optional [x, y, z] location coordinates
        rotation: Optional [x, y, z] rotation in radians
        scale: Optional [x, y, z] scale factors
        api_url: The URL of the BlenderLM API
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the created object
    """
    headers = {}
    if session_id:
        headers["session_id"] = session_id
        
    params: Dict[str, Any] = {
        "type": type
    }
    
    if name:
        params["name"] = name
    if location:
        params["location"] = location
    if rotation:
        params["rotation"] = rotation
    if scale:
        params["scale"] = scale
        
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/objects",
            json=params,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract session ID if provided in response
        if "session_id" in result and not session_id:
            session_id = result["session_id"]
            
        return f"Created {type} named '{result['name']}' at position {result['location']}"


async def modify_blender_object(
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
    visible: Optional[bool] = None,
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None,
) -> str:
    """
    Modify an existing object in Blender.

    Args:
        name: Name of the object to modify
        location: Optional [x, y, z] location coordinates
        rotation: Optional [x, y, z] rotation in radians
        scale: Optional [x, y, z] scale factors
        visible: Optional boolean to set visibility
        api_url: The URL of the BlenderLM API
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the modifications made
    """
    headers = {}
    if session_id:
        headers["session_id"] = session_id
        
    params: Dict[str, Any] = {
        "name": name
    }
    
    if location:
        params["location"] = location
    if rotation:
        params["rotation"] = rotation
    if scale:
        params["scale"] = scale
    if visible is not None:
        params["visible"] = visible
        
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{api_url}/api/objects/{name}",
            json=params,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        
        # Build a description of what was changed
        changes = []
        if location:
            changes.append(f"location to {result['location']}")
        if rotation:
            changes.append(f"rotation to {result['rotation']}")
        if scale:
            changes.append(f"scale to {result['scale']}")
        if visible is not None:
            changes.append(f"visibility to {'visible' if visible else 'hidden'}")
            
        return f"Modified object '{name}': " + ", ".join(changes)


async def delete_blender_object(
    name: str,
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None,
) -> str:
    """
    Delete an object from the Blender scene.

    Args:
        name: Name of the object to delete
        api_url: The URL of the BlenderLM API
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Confirmation message
    """
    headers = {}
    if session_id:
        headers["session_id"] = session_id
        
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{api_url}/api/objects/{name}",
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        
        return f"Deleted object '{result['deleted']}'"


async def set_blender_material(
    object_name: str,
    color: Optional[List[float]] = None,
    material_name: Optional[str] = None,
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None,
) -> str:
    """
    Set or create a material for an object in Blender.

    Args:
        object_name: Name of the object to apply material to
        color: Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0)
        material_name: Optional name for the material
        api_url: The URL of the BlenderLM API
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the material applied
    """
    headers = {}
    if session_id:
        headers["session_id"] = session_id
        
    params: Dict[str, Any] = {
        "object_name": object_name
    }
    
    if color:
        params["color"] = color
    if material_name:
        params["material_name"] = material_name
        
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/materials",
            json=params,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        
        color_str = ""
        if color:
            color_desc = "transparent " if len(color) > 3 and color[3] < 0.5 else ""
            if len(color) >= 3:
                # Create a human-readable color description
                r, g, b = color[0], color[1], color[2]
                if r > 0.8 and g < 0.3 and b < 0.3:
                    color_str = "red"
                elif r < 0.3 and g > 0.8 and b < 0.3:
                    color_str = "green"
                elif r < 0.3 and g < 0.3 and b > 0.8:
                    color_str = "blue"
                elif r > 0.8 and g > 0.8 and b < 0.3:
                    color_str = "yellow"
                elif r < 0.3 and g > 0.8 and b > 0.8:
                    color_str = "cyan"
                elif r > 0.8 and g < 0.3 and b > 0.8:
                    color_str = "magenta"
                elif r > 0.8 and g > 0.8 and b > 0.8:
                    color_str = "white"
                elif r < 0.3 and g < 0.3 and b < 0.3:
                    color_str = "black"
                elif abs(r - g) < 0.1 and abs(g - b) < 0.1:
                    brightness = (r + g + b) / 3
                    if brightness < 0.4:
                        color_str = "dark gray"
                    elif brightness > 0.7:
                        color_str = "light gray"
                    else:
                        color_str = "gray"
                else:
                    color_str = f"custom ({r:.1f}, {g:.1f}, {b:.1f})"
            
            color_str = f"{color_desc}{color_str}"
                
        material_desc = f"'{result.get('material')}'" if "material" in result else "material"
        if color_str:
            return f"Applied {color_str} {material_desc} to object '{object_name}'"
        else:
            return f"Applied {material_desc} to object '{object_name}'"


async def render_blender_scene(
    output_path: Optional[str] = None,
    resolution_x: Optional[int] = None,
    resolution_y: Optional[int] = None,
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None,
) -> str:
    """
    Render the current Blender scene.

    Args:
        output_path: Optional path to save the render
        resolution_x: Optional width in pixels
        resolution_y: Optional height in pixels
        api_url: The URL of the BlenderLM API
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the render operation
    """
    headers = {}
    if session_id:
        headers["session_id"] = session_id
        
    params = {}
    
    if output_path:
        params["output_path"] = output_path
    if resolution_x:
        params["resolution_x"] = resolution_x
    if resolution_y:
        params["resolution_y"] = resolution_y
        
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/render",
            json=params,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        
        if output_path:
            return f"Started rendering scene to '{output_path}'"
        else:
            return "Rendered scene preview"


async def get_blender_scene_info(
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None,
) -> str:
    """
    Get information about the current Blender scene.

    Args:
        api_url: The URL of the BlenderLM API
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the current scene
    """
    headers = {}
    if session_id:
        headers["session_id"] = session_id
        
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_url}/api/scene",
            headers=headers
        )
        response.raise_for_status()
        scene = response.json()
        
        # Create a human-readable description of the scene
        objects_desc = []
        if "objects" in scene and scene["objects"]:
            for obj in scene["objects"]:
                obj_type = obj["type"].lower()
                obj_loc = obj.get("location", [0, 0, 0])
                objects_desc.append(f"'{obj['name']}' ({obj_type}) at position {obj_loc}")
        
        scene_text = f"Scene '{scene.get('name', 'Untitled')}' contains {scene.get('object_count', 0)} objects"
        if objects_desc:
            scene_text += ":\n- " + "\n- ".join(objects_desc)
        else:
            scene_text += "."
            
        return scene_text


# Create function tools
create_object_tool = FunctionTool(
    func=create_blender_object,
    description="Create a new 3D object in Blender",
    global_imports=[
        ImportFromModule("typing", ("List", "Optional")),
        "httpx",
    ],
)

modify_object_tool = FunctionTool(
    func=modify_blender_object,
    description="Modify an existing object in Blender",
    global_imports=[
        ImportFromModule("typing", ("List", "Optional")),
        "httpx",
    ],
)

delete_object_tool = FunctionTool(
    func=delete_blender_object,
    description="Delete an object from Blender",
    global_imports=[
        ImportFromModule("typing", ("Optional",)),
        "httpx",
    ],
)

set_material_tool = FunctionTool(
    func=set_blender_material,
    description="Set a material for an object in Blender",
    global_imports=[
        ImportFromModule("typing", ("List", "Optional")),
        "httpx",
    ],
)

render_scene_tool = FunctionTool(
    func=render_blender_scene,
    description="Render the current scene in Blender",
    global_imports=[
        ImportFromModule("typing", ("Optional",)),
        "httpx",
    ],
)

get_scene_info_tool = FunctionTool(
    func=get_blender_scene_info,
    description="Get information about the current Blender scene",
    global_imports=[
        ImportFromModule("typing", ("Optional",)),
        "httpx",
    ],
)


# Function to get all tools
async def get_blender_tools(
    api_url: str = "http://localhost:8000",
    session_id: Optional[str] = None
) -> List[FunctionTool]:
    """
    Get all available Blender tools.
    
    This will connect to the BlenderLM API and retrieve the tool set.
    You can optionally specify a session ID to use an existing Blender session.
    
    Args:
        api_url: URL of the BlenderLM API
        session_id: Optional session ID for persistent connection
        
    Returns:
        List of FunctionTool objects ready to use with Autogen
    """
    # TODO: Implement dynamic tool discovery from the API
    # For now, just return the static tools with the provided api_url
    
    tools: List[FunctionTool] = [
        create_object_tool,
        modify_object_tool,
        delete_object_tool,
        set_material_tool,
        render_scene_tool,
        get_scene_info_tool,
    ]
    
    # # Pass along the api_url and session_id as defaults
    # for tool in tools:
    #     tool.default_kwargs = {
    #         "api_url": api_url,
    #         "session_id": session_id
    #     }
    
    return tools