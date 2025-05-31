import os
import traceback
from typing import Dict, List, Optional, Any, Callable

from pydantic import BaseModel
from regex import F
from .client import BlenderLMClient

default_api_url = os.environ.get("BLENDERLM_TOOL_URL", "http://localhost:8199")

class CaptureViewPortResult(BaseModel):
    """
    Result of capturing the viewport.
    Contains either a file path or base64 encoded image data.
    """
    filepath: str | None = None
    status: str | None = None
    image_base64: str | None = None 
    message: str | None = None

async def create_blender_object(
    type: str ,
    name: Optional[str],
    location_x: Optional[float],
    location_y: Optional[float],
    location_z: Optional[float],
    session_id: Optional[str],
) -> str:
    """
    Create a new 3D object in Blender.

    Args:
        type: The type of object to create (CUBE, SPHERE, CYLINDER, PLANE, CONE, TORUS, EMPTY, CAMERA, LIGHT)
        name: Optional name for the object
        location_x: Optional x location coordinate
        location_y: Optional y location coordinate
        location_z: Optional z location coordinate
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the created object
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        location = None
        if location_x is not None and location_y is not None and location_z is not None:
            location = [location_x, location_y, location_z]
        result = await client.create_object(
            obj_type=type,
            name=name,
            location=location,
            wait_for_result=True
        ) 
        
        return f"Created {type} named '{result['name']}' at position {str(result['location'])}"
    except Exception as e:
        traceback.print_exc()
        return f"Error creating {type}: {str(e)}"


# async def modify_blender_object(
#     name: str,
#     location: Optional[List[float]],
#     rotation: Optional[List[float]],
#     scale: Optional[List[float]],
#     visible: Optional[bool],
#     session_id: Optional[str],
# ) -> str:
#     """
#     Modify an existing object in Blender.

#     Args:
#         name: Name of the object to modify
#         location: Optional [x, y, z] location coordinates
#         rotation: Optional [x, y, z] rotation in radians
#         scale: Optional [x, y, z] scale factors
#         visible: Optional boolean to set visibility
#         session_id: Optional session ID for the Blender connection

#     Returns:
#         str: Description of the modifications made
#     """
#     client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
#     try:
#         result = await client.modify_object(
#             name=name,
#             location=location,
#             rotation=rotation,
#             scale=scale,
#             visible=visible,
#             wait_for_result=True
#         )
        
#         # Build a description of what was changed
#         changes = []
#         if location:
#             changes.append(f"location to {result['location']}")
#         if rotation:
#             changes.append(f"rotation to {result['rotation']}")
#         if scale:
#             changes.append(f"scale to {result['scale']}")
#         if visible is not None:
#             changes.append(f"visibility to {'visible' if visible else 'hidden'}")
            
#         return f"Modified object '{name}': " + ", ".join(changes)
#     except Exception as e:
#         return f"Error modifying object '{name}': {str(e)}"


async def delete_blender_object(
    name: str,
    session_id: Optional[str],
) -> str:
    """
    Delete an object from the Blender scene.

    Args:
        name: Name of the object to delete
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Confirmation message
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        result = await client.delete_object(name=name, wait_for_result=True)
        return f"Deleted object '{result.get('deleted', name)}'"
    except Exception as e:
        return f"Error deleting object '{name}': {str(e)}"


async def set_blender_material(
    object_name: str,
    color: Optional[List[float]],
    material_name: Optional[str],
    session_id: Optional[str],
) -> str:
    """
    Set or create a material for an object in Blender.

    Args:
        object_name: Name of the object to apply material to
        color: Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0)
        material_name: Optional name for the material
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the material applied
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        result = await client.set_material(
            object_name=object_name,
            color=color,
            material_name=material_name,
            wait_for_result=True
        )
        
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
    except Exception as e:
        return f"Error applying material to '{object_name}': {str(e)}"


async def render_blender_scene(
    output_path: Optional[str],
    resolution_x: Optional[int],
    resolution_y: Optional[int],
    session_id: Optional[str],
) -> str:
    """
    Render the current Blender scene.

    Args:
        output_path: Optional path to save the render
        resolution_x: Optional width in pixels
        resolution_y: Optional height in pixels
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the render operation
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        result = await client.render_scene(
            output_path=output_path,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
            wait_for_result=True
        )
        
        if output_path:
            return f"Rendered scene to '{result.get('output_path', output_path)}'"
        else:
            return "Rendered scene successfully"
    except Exception as e:
        return f"Error rendering scene: {str(e)}"


async def get_blender_scene_info(
    session_id: Optional[str],
) -> str:
    """
    Get information about the current Blender scene, list objects and their properties.

    Args:
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the current scene
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        scene = await client.get_scene_info(wait_for_result=True)
        
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
    except Exception as e:
        return f"Error getting scene info: {str(e)}"


async def capture_viewport(
    filepath: Optional[str] ,
    camera_view: Optional[bool]  ,
    return_base64: Optional[bool] ,
    session_id: Optional[str] ,
) ->  CaptureViewPortResult:
    """
    Capture the current viewport using OpenGL rendering.

    Args:
        filepath: Optional path to save the captured image
        camera_view: Whether to switch to camera view before capture.
        return_base64: Whether to return the image as base64.
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the captured viewport
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        # Use _make_request directly since client.py doesn't have a capture_viewport method
        params = {}
        if filepath:
            params["filepath"] = filepath
        # Pass resolved boolean values
        params["camera_view"] = camera_view
        params["return_base64"] = return_base64 
            
        response = await client._make_request("POST", "/api/viewport", params)
         
        result = await client._wait_for_job_completion(response["job_id"]) 
        result = CaptureViewPortResult(**result)
        
        return result
    except Exception as e:
        return CaptureViewPortResult(
            filepath=None,
            status="error",
            image_base64=None,
            message=f"Error capturing viewport: {str(e)}"
        )


async def execute_code(
    code: str,
    session_id: Optional[str],
) -> str:
    """
    Execute  Python code in Blender to address tasks.

    Args:
        code: The Python code to execute
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the execution result
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        result = await client.execute_code(code=code, wait_for_result=True)
        return "Executed Python code in Blender"
    except Exception as e:
        return f"Error executing code: {str(e)}"


async def clear_blender_scene(
    session_id: Optional[str],
) -> str:
    """
    Clear all objects from the current Blender scene.

    Args:
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Confirmation message
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        # Use _make_request directly since client.py doesn't have a clear_scene method
        response = await client._make_request("POST", "/api/scene/clear", {})
        
        if "job_id" in response:
            result = await client._wait_for_job_completion(response["job_id"])
        else:
            result = response
            
        return "Cleared all objects from the scene"
    except Exception as e:
        return f"Error clearing scene: {str(e)}"


async def add_blender_camera(
    location: Optional[List[float]],
    rotation: Optional[List[float]],
    session_id: Optional[str],
) -> str:
    """
    Add a camera to the Blender scene.

    Args:
        location: Optional [x, y, z] location coordinates
        rotation: Optional [x, y, z] rotation in radians
        session_id: Optional session ID for the Blender connection

    Returns:
        str: Description of the created camera
    """
    client = BlenderLMClient(api_url=default_api_url, session_id=session_id)
    
    try:
        # Use _make_request directly since client.py doesn't have an add_camera method
        params = {}
        if location:
            params["location"] = location
        if rotation:
            params["rotation"] = rotation
            
        response = await client._make_request("POST", "/api/camera", params)
        
        if "job_id" in response:
            result = await client._wait_for_job_completion(response["job_id"])
        else:
            result = response
            
        return "Added camera to scene"
    except Exception as e:
        return f"Error adding camera: {str(e)}"


# Function to get all tools
async def get_blender_tools(session_id: Optional[str] = None) -> List[Callable]:
    """
    Get all available Blender tool functions.
    
    Args:
        session_id: Optional session ID (currently unused in this function but kept for potential future dynamic loading)
        
    Returns:
        List of async functions representing the available tools.
    """
    # TODO: Implement dynamic tool discovery from the API?
    # For now, just return the static list of functions.
    
    tools: List[Callable] = [
        create_blender_object,
        # modify_blender_object,
        delete_blender_object,
        set_blender_material,
        render_blender_scene,
        get_blender_scene_info,
        capture_viewport,
        execute_code,
        clear_blender_scene,
        add_blender_camera,
    ]
    
    return tools