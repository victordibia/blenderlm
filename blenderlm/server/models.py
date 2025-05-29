from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ObjectType(str, Enum):
    CUBE = "CUBE"
    SPHERE = "SPHERE"
    CYLINDER = "CYLINDER"
    PLANE = "PLANE"
    CONE = "CONE"
    TORUS = "TORUS"
    EMPTY = "EMPTY"
    CAMERA = "CAMERA"
    LIGHT = "LIGHT"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Vector3(BaseModel):
    """3D vector with x, y, z components"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def to_list(self) -> List[float]:
        """Convert to [x, y, z] list format"""
        return [self.x, self.y, self.z]


class Color(BaseModel):
    """RGBA color"""
    r: float = Field(default=0.8, ge=0.0, le=1.0)
    g: float = Field(default=0.8, ge=0.0, le=1.0)
    b: float = Field(default=0.8, ge=0.0, le=1.0)
    a: float = Field(default=1.0, ge=0.0, le=1.0)
    
    def to_list(self) -> List[float]:
        """Convert to [r, g, b, a] list format"""
        return [self.r, self.g, self.b, self.a]


class CreateObjectRequest(BaseModel):
    """Request to create a new object in the scene"""
    type: str
    name: Optional[str] = None
    location: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    color: Optional[List[float]] = None
    
    def to_params(self) -> dict:
        """Convert to parameters for Blender command"""
        params: Dict[str, Any] = {"type": self.type}
        
        if self.name:
            params["name"] = self.name
            
        if self.location:
            params["location"] = tuple(self.location)
            
        if self.rotation:
            params["rotation"] = tuple(self.rotation)
            
        if self.scale:
            params["scale"] = tuple(self.scale)
            
        if self.color:
            params["color"] = self.color
            
        return params


class JobInfo(BaseModel):
    """Information about a job"""
    id: str
    command_type: str
    params: Dict[str, Any]
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float
    completed_at: Optional[float] = None


class ObjectInfo(BaseModel):
    """Information about an object in Blender"""
    name: str
    type: str
    location: List[float]
    rotation: List[float]
    scale: List[float]
    materials: Optional[List[str]] = None


class ModifyObjectRequest(BaseModel):
    """Request to modify an existing object in Blender"""
    name: Optional[str] = None
    location: Optional[Union[Vector3, List[float]]] = None
    rotation: Optional[Union[Vector3, List[float]]] = None
    scale: Optional[Union[Vector3, List[float]]] = None
    visible: Optional[bool] = None
    
    def to_params(self) -> dict:
        """Convert to parameters for Blender command"""
        params: dict[str, Any] = {}
        
        if self.name:
            params["name"] = self.name
        
        if self.location:
            if isinstance(self.location, Vector3):
                params["location"] = self.location.to_list()
            else:
                params["location"] = self.location
                
        if self.rotation:
            if isinstance(self.rotation, Vector3):
                params["rotation"] = self.rotation.to_list()
            else:
                params["rotation"] = self.rotation
                
        if self.scale:
            if isinstance(self.scale, Vector3):
                params["scale"] = self.scale.to_list()
            else:
                params["scale"] = self.scale
                
        if self.visible is not None:
            params["visible"] = self.visible
            
        return params


class DeleteObjectRequest(BaseModel):
    """Request to delete an object from Blender"""
    name: str


class MaterialRequest(BaseModel):
    """Request to set a material for an object"""
    object_name: str
    material_name: Optional[str] = None
    color: Optional[Union[Color, List[float]]] = None
    
    def to_params(self) -> dict:
        """Convert to parameters for Blender command"""
        params: dict[str, Any] = {"object_name": self.object_name}
        
        if self.material_name:
            params["material_name"] = self.material_name
            
        if self.color:
            if isinstance(self.color, Color):
                params["color"] = self.color.to_list()
            else:
                # Ensure list has 4 elements
                if len(self.color) == 3:
                    self.color = list(self.color) + [1.0]
                params["color"] = self.color
                
        return params


class ClearSceneRequest(BaseModel):
    """Request to clear all objects from the current scene"""
    
    def to_params(self) -> Dict[str, Any]:
        return {}


class AddCameraRequest(BaseModel):
    """Request to add a camera to the scene"""
    location: Optional[Union[Vector3, List[float]]] = None
    rotation: Optional[Union[Vector3, List[float]]] = None
    
    def to_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        
        if self.location:
            if isinstance(self.location, Vector3):
                params["location"] = self.location.to_list()
            else:
                params["location"] = self.location
                
        if self.rotation:
            if isinstance(self.rotation, Vector3):
                params["rotation"] = self.rotation.to_list()
            else:
                params["rotation"] = self.rotation
                
        return params


class CodeRequest(BaseModel):
    code: str


class RenderRequest(BaseModel):
    """Request to render the current scene"""
    output_path: Optional[str] = None
    resolution_x: Optional[int] = None
    resolution_y: Optional[int] = None
    
    def to_params(self) -> dict:
        """Convert to parameters for Blender command"""
        params = {}
        
        if self.output_path:
            params["output_path"] = self.output_path
            
        if self.resolution_x:
            params["resolution_x"] = self.resolution_x
            
        if self.resolution_y:
            params["resolution_y"] = self.resolution_y
            
        return params


class SessionInfo(BaseModel):
    """Information about a client session"""
    session_id: str
    created: float
    last_activity: float
    object_count: int = 0


class ToolInfo(BaseModel):
    """Information about an available tool"""
    name: str
    description: str
    parameters: dict
    endpoint: str


class ViewportCaptureRequest(BaseModel):
    filepath: Optional[str] = None
    camera_view: bool = False
    return_base64: bool = True
    
    def to_params(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "camera_view": self.camera_view,
            "return_base64": self.return_base64
        }


# --- New Models for Chat Endpoint ---

class ModelProvider(str, Enum):
    """Supported model providers"""
    GOOGLE = "google"
    OPENAI = "openai"
    # Add other providers here (e.g., ANTHROPIC, MISTRAL)

class ModelInfo(BaseModel):
    """Information about the language model to use"""
    provider: ModelProvider = ModelProvider.GOOGLE
    name: str = "gemini-1.5-flash-latest"

class ChatRequest(BaseModel):
    """Chat request with natural language query"""
    query: str
    model: ModelInfo = Field(default_factory=ModelInfo) # Use ModelInfo with default
    session_id: Optional[str] = None


# --- Project Management Models ---

class ProjectStatus(str, Enum):
    """Project status enumeration"""
    ACTIVE = "active"
    ARCHIVED = "archived"

class ProjectInfo(BaseModel):
    """Project information model"""
    id: str
    name: str
    description: Optional[str] = ""
    file_path: Optional[str] = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: float
    updated_at: float
    last_opened_at: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class CreateProjectRequest(BaseModel):
    """Request to create a new project"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="", max_length=1000)
    file_path: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None

class UpdateProjectRequest(BaseModel):
    """Request to update an existing project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    file_path: Optional[str] = None
    status: Optional[ProjectStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class LoadProjectRequest(BaseModel):
    """Request to load a project (.blend file)"""
    project_id: Optional[str] = None
    file_path: Optional[str] = None

class SaveProjectRequest(BaseModel):
    """Request to save current project"""
    project_id: str
    file_path: Optional[str] = None
    create_backup: bool = True

class NewProjectRequest(BaseModel):
    """Request to create a new Blender project (clear scene)"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="", max_length=1000)
    save_current: bool = False
    current_project_id: Optional[str] = None

class ProjectListResponse(BaseModel):
    """Response for listing projects"""
    projects: List[ProjectInfo]
    total_count: int