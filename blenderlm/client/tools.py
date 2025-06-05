import os
import httpx
from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel

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
    type: str,
    name: Optional[str],
    location_x: Optional[float],
    location_y: Optional[float],
    location_z: Optional[float],
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Create a new object in Blender.
    Args:
        type: Type of object to create, e.g. 'CUBE', 'SPHERE', etc.
        name: Optional name for the object.
        location_x: Optional X coordinate.
        location_y: Optional Y coordinate.
        location_z: Optional Z coordinate.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        The created object info or job info.
    """
    api_url = default_api_url
    data: Dict[str, Any] = {"type": type}
    if name:
        data["name"] = name
    if None not in (location_x, location_y, location_z):
        data["location"] = [location_x, location_y, location_z]
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/objects", json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def delete_blender_object(
    name: str,
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Delete an object from Blender.
    Args:
        name: Name of the object to delete.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Deletion result or job info.
    """
    api_url = default_api_url
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{api_url}/api/blender/objects/{name}", headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def set_blender_material(
    object_name: str,
    color: Optional[List[float]],
    material_name: Optional[str],
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Set a material for an object in Blender.
    Args:
        object_name: Name of the object to apply material to.
        color: Optional color as [R, G, B] or [R, G, B, A].
        material_name: Optional name for the material.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Material application result or job info.
    """
    api_url = default_api_url
    data: Dict[str, Any] = {"object_name": object_name}
    if color:
        data["color"] = color
    if material_name:
        data["material_name"] = material_name
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/materials", json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def render_blender_scene(
    output_path: Optional[str],
    resolution_x: Optional[int],
    resolution_y: Optional[int],
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Render the current Blender scene.
    Args:
        output_path: Optional path to save the render.
        resolution_x: Optional width in pixels.
        resolution_y: Optional height in pixels.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Render result or job info.
    """
    api_url = default_api_url
    data = {}
    if output_path:
        data["output_path"] = output_path
    if resolution_x:
        data["resolution_x"] = resolution_x
    if resolution_y:
        data["resolution_y"] = resolution_y
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/render", json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def get_blender_scene_info(
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Get information about the current Blender scene.
    Args:
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Scene info as a dict or job info.
    """
    api_url = default_api_url
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/blender/scene", headers=headers)
        response.raise_for_status()
        scene = response.json()
    if wait_for_result and "job_id" in scene:
        scene = await _wait_for_job_completion(scene["job_id"], api_url, session_id)
    return scene if wait_for_result else scene

async def capture_viewport( 
    camera_view: Optional[bool],
    return_base64: Optional[bool],
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Capture the current Blender viewport as an image.
    Args:
        filepath: Optional path to save the captured image.
        camera_view: Whether to switch to camera view before capture.
        return_base64: Whether to return the image as base64.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Viewport capture result or job info.
    """
    api_url = default_api_url
    data = {}
    
    if camera_view is not None:
        data["camera_view"] = camera_view
    if return_base64 is not None:
        data["return_base64"] = return_base64
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/viewport", json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def execute_code(
    code: str,
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Execute arbitrary Python code in Blender to address tasks.
    Args:
        code: The Python code to execute.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Code execution result or job info.
    """
    api_url = default_api_url
    data = {"code": code}
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/code", json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def clear_blender_scene(
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Clear all objects from the Blender scene.
    Args:
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Scene clear result or job info.
    """
    api_url = default_api_url
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/scene/clear", json={},headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def add_blender_camera(
    location: Optional[List[float]],
    rotation: Optional[List[float]],
    session_id: Optional[str],
    wait_for_result: bool,
) -> Any:
    """
    Add a camera to the Blender scene.
    Args:
        location: Optional [x, y, z] location coordinates.
        rotation: Optional [x, y, z] rotation in radians.
        session_id: Optional session ID for Blender connection.
        wait_for_result: Whether to wait for job completion.
    Returns:
        Camera addition result or job info.
    """
    api_url = default_api_url
    data = {}
    if location:
        data["location"] = location
    if rotation:
        data["rotation"] = rotation
    headers = {"session_id": session_id} if session_id else {}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{api_url}/api/blender/camera", json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
    if wait_for_result and "job_id" in result:
        result = await _wait_for_job_completion(result["job_id"], api_url, session_id)
    return result if wait_for_result else result

async def _wait_for_job_completion(job_id: str, api_url: str, session_id: Optional[str], max_wait_seconds: int = 60, poll_interval_seconds: float = 0.5) -> Dict[str, Any]:
    import asyncio, time
    headers = {"session_id": session_id} if session_id else {}
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(f"Job {job_id} did not complete within {max_wait_seconds} seconds")
            response = await client.get(f"{api_url}/api/jobs/{job_id}", headers=headers)
            response.raise_for_status()
            job_info = response.json()
            if job_info["status"] == "completed":
                return job_info["result"]
            elif job_info["status"] == "failed":
                raise Exception(f"Job failed: {job_info.get('error', 'Unknown error')}")
            await asyncio.sleep(poll_interval_seconds)

# List of all tool callables for agent registration
blender_tools = [
    # create_blender_object,
    # delete_blender_object,
    # set_blender_material,
    # render_blender_scene,
    get_blender_scene_info,
    capture_viewport,
    execute_code,
    clear_blender_scene,
    add_blender_camera,
]

async def get_blender_tools() -> List[Callable]:
    return blender_tools