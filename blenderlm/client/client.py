import asyncio
import httpx
from typing import Dict, List, Optional, Any, Union, Callable
import json
import time
import inspect


def blenderlm_tool(func: Callable) -> Callable:
    """Decorator to mark methods intended as tools for LLM agents."""
    setattr(func, '_is_blenderlm_tool', True)
    return func


class BlenderLMClient:
    """
    A client for interacting with the BlenderLM API server.
    This version supports the asynchronous job system.
    """

    def __init__(self, api_url: str = "http://localhost:8199", session_id: Optional[str] = None) -> None:
        """
        Initialize the BlenderLM client.

        Args:
            api_url: The URL of the BlenderLM API server
            session_id: Optional session ID for the Blender connection
        """
        self.api_url = api_url
        self.session_id = session_id

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the BlenderLM API server.

        Args:
            method: The HTTP method to use (GET, POST, PUT, DELETE)
            endpoint: The API endpoint to call
            json_data: Optional JSON data to send with the request

        Returns:
            The JSON response from the server
        """
        headers = {}
        if self.session_id:
            headers["session_id"] = self.session_id

        async with httpx.AsyncClient() as client:
            url = f"{self.api_url}/{endpoint.lstrip('/')}"

            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, json=json_data, headers=headers)
            elif method.upper() == "PUT":
                response = await client.put(url, json=json_data, headers=headers)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

    async def _wait_for_job_completion(
        self,
        job_id: str,
        max_wait_seconds: int = 60,
        poll_interval_seconds: float = 0.5
    ) -> Dict[str, Any]:
        """
        Wait for a job to complete, polling at regular intervals.

        Args:
            job_id: The ID of the job to wait for
            max_wait_seconds: Maximum time to wait before timing out
            poll_interval_seconds: How often to check job status

        Returns:
            The job result
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(f"Job {job_id} did not complete within {max_wait_seconds} seconds")

            job_info = await self._make_request("GET", f"/api/jobs/{job_id}")

            if job_info["status"] == "completed":
                return job_info["result"]
            elif job_info["status"] == "failed":
                raise Exception(f"Job failed: {job_info.get('error', 'Unknown error')}")

            await asyncio.sleep(poll_interval_seconds)

    @blenderlm_tool
    async def get_info(self, wait_for_result: bool = True) -> Dict[str, Any]:
        """
        Get basic information about the Blender instance.

        Args:
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the Blender instance
        """
        response = await self._make_request("GET", "/api/info")

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def get_scene_info(self, wait_for_result: bool = True) -> Dict[str, Any]:
        """
        Get information about the current scene.

        Args:
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the current scene
        """
        response = await self._make_request("GET", "/api/scene")

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def create_object(
        self,
        obj_type: str = "CUBE",
        name: Optional[str] = None,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        color: Optional[List[float]] = None,
        wait_for_result: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new object in Blender.

        Args:
            obj_type: The type of object to create (CUBE, SPHERE, etc.)
            name: Optional name for the object
            location: Optional [x, y, z] location coordinates
            rotation: Optional [x, y, z] rotation in radians
            scale: Optional [x, y, z] scale factors
            color: Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0)
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the created object
        """
        data: Dict[str, Any] = {"type": obj_type}

        if name:
            data["name"] = name
        if location:
            data["location"] = location
        if rotation:
            data["rotation"] = rotation
        if scale:
            data["scale"] = scale
        if color:
            data["color"] = color

        response = await self._make_request("POST", "/api/objects", data)

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def modify_object(
        self,
        name: str,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        visible: Optional[bool] = None,
        wait_for_result: bool = True
    ) -> Dict[str, Any]:
        """
        Modify an existing object in Blender.

        Args:
            name: Name of the object to modify
            location: Optional [x, y, z] location coordinates
            rotation: Optional [x, y, z] rotation in radians
            scale: Optional [x, y, z] scale factors
            visible: Optional boolean to set visibility
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the modified object
        """
        data: Dict[str, Any] = {"name": name}

        if location:
            data["location"] = location
        if rotation:
            data["rotation"] = rotation
        if scale:
            data["scale"] = scale
        if visible is not None:
            data["visible"] = visible

        response = await self._make_request("PUT", f"/api/objects/{name}", data)

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def delete_object(self, name: str, wait_for_result: bool = True) -> Dict[str, Any]:
        """
        Delete an object from Blender.

        Args:
            name: Name of the object to delete
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Confirmation of deletion
        """
        response = await self._make_request("DELETE", f"/api/objects/{name}")

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def set_material(
        self,
        object_name: str,
        color: Optional[List[float]] = None,
        material_name: Optional[str] = None,
        wait_for_result: bool = True
    ) -> Dict[str, Any]:
        """
        Set a material for an object.

        Args:
            object_name: Name of the object to apply material to
            color: Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0)
            material_name: Optional name for the material
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the applied material
        """
        data: Dict[str, Any] = {"object_name": object_name}

        if color:
            data["color"] = color
        if material_name:
            data["material_name"] = material_name

        response = await self._make_request("POST", "/api/materials", data)

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def render_scene(
        self,
        output_path: Optional[str] = None,
        resolution_x: Optional[int] = None,
        resolution_y: Optional[int] = None,
        wait_for_result: bool = True
    ) -> Dict[str, Any]:
        """
        Render the current scene.

        Args:
            output_path: Optional path to save the render
            resolution_x: Optional width in pixels
            resolution_y: Optional height in pixels
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the render
        """
        data: Dict[str, Any] = {}

        if output_path:
            data["output_path"] = output_path
        if resolution_x:
            data["resolution_x"] = resolution_x
        if resolution_y:
            data["resolution_y"] = resolution_y

        response = await self._make_request("POST", "/api/render", data)

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def execute_code(self, code: str, wait_for_result: bool = True) -> Dict[str, Any]:
        """
        Execute arbitrary Python code in Blender.

        Args:
            code: The Python code to execute
            wait_for_result: Whether to wait for the job to complete

        Returns:
            The result of the code execution
        """
        response = await self._make_request("POST", "/api/code", {"code": code})

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    @blenderlm_tool
    async def capture_viewport(
        self,
        filepath: Optional[str] = None,
        camera_view: Optional[bool] = None,
        return_base64: Optional[bool] = True,
        wait_for_result: bool = True
    ) -> Dict[str, Any]:
        """
        Capture the current viewport using OpenGL rendering.

        Args:
            filepath: Optional path to save the captured image
            camera_view: Whether to switch to camera view before capture
            return_base64: Whether to return the image as base64
            wait_for_result: Whether to wait for the job to complete

        Returns:
            Information about the captured viewport
        """
        data: Dict[str, Any] = {}
        if filepath:
            data["filepath"] = filepath
        if camera_view is not None:
            data["camera_view"] = camera_view
        if return_base64 is not None:
            data["return_base64"] = return_base64

        response = await self._make_request("POST", "/api/viewport", data)

        if wait_for_result and "job_id" in response:
            return await self._wait_for_job_completion(response["job_id"])

        return response

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a job.

        Args:
            job_id: The ID of the job to check

        Returns:
            Information about the job
        """
        return await self._make_request("GET", f"/api/jobs/{job_id}")

    async def run_test_scene(self) -> str:
        """
        Create a simple test scene with two colored cubes.

        Returns:
            A string describing the created objects
        """
        try:
            info = await self.get_info()
            print(f"Connected to Blender {info.get('blender_version', 'unknown version')}")

            scene_before = await self.get_scene_info()
            obj_count_before = scene_before.get("object_count", 0)
            print(f"Scene has {obj_count_before} objects initially")

            red_cube = await self.create_object(
                obj_type="CUBE",
                name="TestCube1",
                location=[-1.0, 0.0, 0.0],
                scale=[0.8, 0.8, 0.8]
            )
            print(f"Created {red_cube['name']} at {red_cube['location']}")

            await self.set_material(
                object_name=red_cube["name"],
                color=[1.0, 0.0, 0.0, 1.0],
                material_name="RedMaterial"
            )
            print(f"Applied red material to {red_cube['name']}")

            blue_cube = await self.create_object(
                obj_type="CUBE",
                name="TestCube2",
                location=[1.0, 0.0, 0.0],
                scale=[0.8, 0.8, 0.8]
            )
            print(f"Created {blue_cube['name']} at {blue_cube['location']}")

            await self.set_material(
                object_name=blue_cube["name"],
                color=[0.0, 0.0, 1.0, 1.0],
                material_name="BlueMaterial"
            )
            print(f"Applied blue material to {blue_cube['name']}")

            scene_after = await self.get_scene_info()
            obj_count_after = scene_after.get("object_count", 0)
            print(f"Scene now has {obj_count_after} objects (added {obj_count_after - obj_count_before})")

            return "Test completed successfully: Created red and blue cubes."

        except Exception as e:
            error_msg = f"Test failed: {str(e)}"
            print(error_msg)
            return error_msg


async def main():
    """Run a basic test of the BlenderLM API."""
    client = BlenderLMClient(api_url="http://localhost:8199")

    try:
        result = await client.run_test_scene()
        print(f"\nResult: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())