import asyncio
from typing import Dict, List, Optional, Any
from . import tools


class BlenderLMClient:
    """
    A client for interacting with the BlenderLM API server.
    This version delegates all logic to async functions in tools.py.
    """

    def __init__(self, api_url: str = "http://localhost:8199", session_id: Optional[str] = None) -> None:
        self.api_url = api_url  # Kept for compatibility, but not used in tools
        self.session_id = session_id

    async def get_info(self, wait_for_result: bool = True) -> Any:
        """
        Get basic information about the Blender instance.
        """
        return await tools.get_blender_scene_info(session_id=self.session_id, wait_for_result=wait_for_result)

    async def get_scene_info(self, wait_for_result: bool = True) -> Any:
        """
        Get information about the current scene.
        """
        return await tools.get_blender_scene_info(session_id=self.session_id, wait_for_result=wait_for_result)

    async def create_object(
        self,
        obj_type: str = "CUBE",
        name: Optional[str] = None,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        color: Optional[List[float]] = None,
        wait_for_result: bool = True,
    ) -> Any:
        """
        Create a new object in Blender.
        """
        location_x, location_y, location_z = (location or [None, None, None])
        return await tools.create_blender_object(
            type=obj_type,
            name=name,
            location_x=location_x,
            location_y=location_y,
            location_z=location_z,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def modify_object(
        self,
        name: str,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        visible: Optional[bool] = None,
        wait_for_result: bool = True,
    ) -> Any:
        # Not implemented in tools.py; placeholder for future extension
        raise NotImplementedError("modify_object is not implemented in tools.py")

    async def delete_object(self, name: str, wait_for_result: bool = True) -> Any:
        """
        Delete an object from Blender.
        """
        return await tools.delete_blender_object(
            name=name,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def set_material(
        self,
        object_name: str,
        color: Optional[List[float]] = None,
        material_name: Optional[str] = None,
        wait_for_result: bool = True,
    ) -> Any:
        """
        Set a material for an object.
        """
        return await tools.set_blender_material(
            object_name=object_name,
            color=color,
            material_name=material_name,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def render_scene(
        self,
        output_path: Optional[str] = None,
        resolution_x: Optional[int] = None,
        resolution_y: Optional[int] = None,
        wait_for_result: bool = True,
    ) -> Any:
        """
        Render the current scene.
        """
        return await tools.render_blender_scene(
            output_path=output_path,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def execute_code(self, code: str, wait_for_result: bool = True) -> Any:
        """
        Execute arbitrary Python code in Blender.
        """
        return await tools.execute_code(
            code=code,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def capture_viewport(
        self,
        filepath: Optional[str] = None,
        camera_view: Optional[bool] = None,
        return_base64: Optional[bool] = True,
        wait_for_result: bool = True,
    ) -> Any:
        """
        Capture the current viewport using OpenGL rendering.
        """
        return await tools.capture_viewport(
            filepath=filepath,
            camera_view=camera_view,
            return_base64=return_base64,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def clear_scene(self, wait_for_result: bool = True) -> Any:
        """
        Clear all objects from the scene.
        """
        return await tools.clear_blender_scene(
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    async def add_camera(
        self,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        wait_for_result: bool = True,
    ) -> Any:
        """
        Add a camera to the scene.
        """
        return await tools.add_blender_camera(
            location=location,
            rotation=rotation,
            session_id=self.session_id,
            wait_for_result=wait_for_result,
        )

    @staticmethod
    def get_blender_tools():
        """
        For agent tool registration, use blender_tools or get_blender_tools() from tools.py.
        """
        import warnings

        warnings.warn("Use blender_tools or get_blender_tools() from tools.py for agent registration.")
        return tools.get_blender_tools()

    # Remove run_test_scene and other demo logic for clarity

# If you need to run a test, use the async functions in tools.py directly or via this client.