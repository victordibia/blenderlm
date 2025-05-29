import asyncio
import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .database import BlenderLMDatabase, JobStatus
from .connection import BlenderConnectionManager
from .models import (
    CodeRequest,
    CreateObjectRequest, 
    MaterialRequest, 
    ModifyObjectRequest,
    RenderRequest,
    ToolInfo,
    JobInfo,
    ViewportCaptureRequest,
    ClearSceneRequest,
    AddCameraRequest,
    ModelProvider,
    ChatRequest,
    # Project management models
    ProjectInfo,
    CreateProjectRequest,
    UpdateProjectRequest,
    LoadProjectRequest,
    SaveProjectRequest,
    NewProjectRequest,
    ProjectListResponse
)

from ..client.client import BlenderLMClient
from ..client.agents import GeminiAgent
from ..client.tools import get_blender_tools

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("blenderlm_api.log")
    ]
)
logger = logging.getLogger("blenderlm.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app"""
    logger.info("Starting BlenderLM API server")
    
    db_path = os.environ.get("BLENDERLM_DB_PATH", "blenderlm.db")
    app.state.database = BlenderLMDatabase(db_path)
    logger.info(f"Initialized database: {db_path}")
    
    # Migrate from old job queue database if it exists
    old_db_path = os.environ.get("BLENDERLM_OLD_DB_PATH", "blenderlm_jobs.db")
    if app.state.database.migrate_from_job_queue_db(old_db_path):
        logger.info("Successfully migrated from old job queue database")
    
    blender_host = os.environ.get("BLENDERLM_BLENDER_HOST", "localhost")
    blender_port = int(os.environ.get("BLENDERLM_BLENDER_PORT", "9876"))
    app.state.blender_manager = BlenderConnectionManager(host=blender_host, port=blender_port)
    logger.info(f"Initialized connection manager for Blender at {blender_host}:{blender_port}")
    
    async def cleanup_task():
        while True:
            try:
                result = app.state.database.clean_old_jobs(max_age_hours=24)
                logger.debug(f"Cleaned up old jobs: {result}")
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(3600)
            
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    logger.info("Started background cleanup task")
    
    try:
        yield
    finally:
        cleanup_task_handle.cancel()
        logger.info("Shutting down BlenderLM API server")

app = FastAPI(
    title="BlenderLM API",
    description="API for controlling Blender with LLM agents",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_job(job_id: str, database: BlenderLMDatabase, blender_manager: BlenderConnectionManager):
    """Process a job in the background"""
    job = database.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    logger.info(f"Processing job {job_id}: {job['command_type']}")
    
    database.update_job(job_id, JobStatus.PROCESSING)
    
    try:
        if not await blender_manager.ensure_connected():
            raise ConnectionError("Could not connect to Blender")
        
        result = await blender_manager.send_command(job["command_type"], job["params"])
 
        database.update_job(job_id, JobStatus.COMPLETED, result=result)
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        error_message = f"Error processing job: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_message}")
        database.update_job(job_id, JobStatus.FAILED, error=error_message)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "BlenderLM API is running"}

@app.get("/api/jobs", response_model=List[JobInfo])
async def list_jobs():
    """List pending jobs"""
    return app.state.database.list_pending_jobs()

@app.get("/api/jobs/{job_id}", response_model=JobInfo)
async def get_job(job_id: str):
    """Get job status and result""" 
    job = app.state.database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/info")
async def get_blender_info(background_tasks: BackgroundTasks):
    """Get information about the Blender instance"""
    job_id = app.state.database.add_job("get_simple_info")
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.get("/api/scene")
async def get_scene_info(background_tasks: BackgroundTasks):
    """Get information about the current scene"""
    job_id = app.state.database.add_job("get_scene_info")
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.get("/api/objects/{name}")
async def get_object_info(name: str, background_tasks: BackgroundTasks):
    """Get information about a specific object"""
    job_id = app.state.database.add_job("get_object_info", {"name": name})
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}


@app.post("/api/viewport")
async def capture_viewport(request: ViewportCaptureRequest, background_tasks: BackgroundTasks):
    """Capture the current viewport using OpenGL rendering"""
    job_id = app.state.database.add_job("capture_viewport", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/objects")
async def create_object(request: CreateObjectRequest, background_tasks: BackgroundTasks):
    """Create a new object in the scene"""
    job_id = app.state.database.add_job("create_object", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.put("/api/objects/{name}")
async def modify_object(
    name: str, 
    request: ModifyObjectRequest, 
    background_tasks: BackgroundTasks
):
    """Modify an existing object"""
    if request.name is None:
        request.name = name
    elif request.name != name:
        request.name = name
    
    job_id = app.state.database.add_job("modify_object", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.delete("/api/objects/{name}")
async def delete_object(name: str, background_tasks: BackgroundTasks):
    """Delete an object from the scene"""
    job_id = app.state.database.add_job("delete_object", {"name": name})
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/materials")
async def set_material(request: MaterialRequest, background_tasks: BackgroundTasks):
    """Set a material for an object"""
    job_id = app.state.database.add_job("set_material", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/render")
async def render_scene(request: RenderRequest, background_tasks: BackgroundTasks):
    """Render the current scene"""
    job_id = app.state.database.add_job("render_scene", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/code")
async def execute_code(request: CodeRequest, background_tasks: BackgroundTasks):
    """Execute arbitrary Python code in Blender"""
    job_id = app.state.database.add_job("execute_code", {"code": request.code})
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/scene/clear")
async def clear_scene(request: ClearSceneRequest, background_tasks: BackgroundTasks):
    """Clear all objects from the current scene"""
    job_id = app.state.database.add_job("clear_scene", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/camera")
async def add_camera(request: AddCameraRequest, background_tasks: BackgroundTasks):
    """Add a camera to the scene"""
    job_id = app.state.database.add_job("add_camera", request.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        app.state.database, 
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.post("/api/chat")
async def chat_with_blender(request: ChatRequest):
    """Process a natural language query using an agent to interact with Blender"""
    try:
        logger.info(f"Processing chat request with model {request.model.provider.value}/{request.model.name}: {request.query}")

        server_host = os.environ.get("BLENDERLM_API_HOST", "localhost")
        server_port = os.environ.get("BLENDERLM_API_PORT", "8199")
        base_api_url = f"http://{server_host}:{server_port}"

        blender_client = BlenderLMClient(
            api_url=base_api_url,
            session_id=request.session_id
        )

        agent = None
        if request.model.provider == ModelProvider.GOOGLE:
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if not gemini_api_key:
                raise HTTPException(status_code=500, detail="Gemini API key not configured on server.")
            tools = await get_blender_tools(api_url=base_api_url, session_id=request.session_id)
            agent = GeminiAgent(
                tools=tools,
                model_name=request.model.name,
                api_key=gemini_api_key
            )
        elif request.model.provider == ModelProvider.OPENAI:
            raise HTTPException(status_code=501, detail="OpenAI agent not yet implemented.")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model provider: {request.model.provider}")

        agent_response = await agent.run(request.query)

        return {
            "status": "success",
            "response": agent_response.dict(),
            "query": request.query,
            "model_used": request.model.dict()
        }

    except HTTPException as http_exc:
        logger.error(f"HTTP error processing chat request: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/api/tools", response_model=List[ToolInfo])
async def list_tools():
    """List all available tools"""
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
            endpoint="/api/objects"
        ),
        ToolInfo(
            name="capture_viewport",
            description="Capture the current viewport using OpenGL rendering",
            parameters={
                "filepath": "Optional path to save the captured image",
                "camera_view": "Optional boolean to switch to camera view before capture",
                "return_base64": "Optional boolean to return the image as base64 (default: True)"
            },
            endpoint="/api/viewport"
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
            endpoint="/api/objects/{name}"
        ),
        ToolInfo(
            name="delete_object",
            description="Delete an object from the scene",
            parameters={
                "name": "Name of the object to delete",
            },
            endpoint="/api/objects/{name}"
        ),
        ToolInfo(
            name="set_material",
            description="Set or create a material for an object",
            parameters={
                "object_name": "Name of the object to apply material to",
                "material_name": "Optional name for the material",
                "color": "Optional [R, G, B] or [R, G, B, A] color values (0.0-1.0)",
            },
            endpoint="/api/materials"
        ),
        ToolInfo(
            name="render_scene",
            description="Render the current scene",
            parameters={
                "output_path": "Optional path to save the render",
                "resolution_x": "Optional width in pixels",
                "resolution_y": "Optional height in pixels",
            },
            endpoint="/api/render"
        ),
        ToolInfo(
            name="execute_code",
            description="Execute arbitrary Python code in Blender",
            parameters={
                "code": "The Python code to execute",
            },
            endpoint="/api/code"
        ),
        ToolInfo(
            name="get_scene_info",
            description="Get information about the current scene",
            parameters={},
            endpoint="/api/scene"
        ),
        ToolInfo(
            name="get_object_info",
            description="Get information about a specific object",
            parameters={
                "name": "Name of the object to get information about",
            },
            endpoint="/api/objects/{name}"
        ),
    ]
    return tools

@app.get("/api/tools/{name}", response_model=ToolInfo)
async def get_tool_info(name: str):
    """Get information about a specific tool"""
    tools = await list_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise HTTPException(status_code=404, detail=f"Tool {name} not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health = {
        "status": "ok",
        "blender_connected": False
    }
    
    try:
        if await app.state.blender_manager.ensure_connected():
            health["blender_connected"] = True
    except Exception as e:
        health["status"] = "degraded"
        health["error"] = str(e)
    
    return health

# =============================================================================
# PROJECT MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/projects", response_model=ProjectListResponse)
async def list_projects(status: Optional[str] = None, limit: int = 50):
    """List projects, optionally filtered by status"""
    try:
        projects = app.state.database.list_projects(status=status, limit=limit)
        return ProjectListResponse(
            projects=[ProjectInfo(**project) for project in projects],
            total_count=len(projects)
        )
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects", response_model=ProjectInfo)
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        project_id = app.state.database.create_project(
            name=request.name,
            description=request.description,
            file_path=request.file_path,
            metadata=request.metadata
        )
        
        project = app.state.database.get_project(project_id)
        if not project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        return ProjectInfo(**project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str):
    """Get a specific project by ID"""
    project = app.state.database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectInfo(**project)

@app.put("/api/projects/{project_id}", response_model=ProjectInfo)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update a project"""
    try:
        success = app.state.database.update_project(
            project_id=project_id,
            name=request.name,
            description=request.description,
            file_path=request.file_path,
            status=request.status.value if request.status else None,
            metadata=request.metadata
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = app.state.database.get_project(project_id)
        return ProjectInfo(**project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its associated jobs"""
    try:
        success = app.state.database.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Project deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/new")
async def new_project(request: NewProjectRequest, background_tasks: BackgroundTasks):
    """Create a new Blender project (clear scene)"""
    try:
        # Create project entry in database
        project_id = app.state.database.create_project(
            name=request.name,
            description=request.description
        )
        
        # Add job to clear scene and create new project in Blender
        job_id = app.state.database.add_job(
            command_type="new_project",
            params={"clear_scene": True},
            project_id=project_id
        )
        
        background_tasks.add_task(
            process_job,
            job_id,
            app.state.database,
            app.state.blender_manager
        )
        
        return {
            "project_id": project_id,
            "job_id": job_id,
            "message": "New project creation started"
        }
    except Exception as e:
        logger.error(f"Error creating new project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/load")
async def load_project(request: LoadProjectRequest, background_tasks: BackgroundTasks):
    """Load a project (.blend file)"""
    try:
        project_id = None
        file_path = request.file_path
        
        # If project_id is provided, get file path from database
        if request.project_id:
            project = app.state.database.get_project(request.project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            project_id = request.project_id
            if project["file_path"]:
                file_path = project["file_path"]
            elif not file_path:
                raise HTTPException(status_code=400, detail="No file path available for this project")
            
            # Update last opened timestamp
            app.state.database.update_project_last_opened(project_id)
        
        if not file_path:
            raise HTTPException(status_code=400, detail="File path is required")
        
        # Add job to load project in Blender
        job_id = app.state.database.add_job(
            command_type="load_project",
            params={"file_path": file_path},
            project_id=project_id
        )
        
        background_tasks.add_task(
            process_job,
            job_id,
            app.state.database,
            app.state.blender_manager
        )
        
        return {
            "project_id": project_id,
            "job_id": job_id,
            "file_path": file_path,
            "message": "Project loading started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/save")
async def save_project(request: SaveProjectRequest, background_tasks: BackgroundTasks):
    """Save current project"""
    try:
        # Get project from database
        project = app.state.database.get_project(request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        file_path = request.file_path or project["file_path"]
        
        # Add job to save project in Blender
        job_id = app.state.database.add_job(
            command_type="save_project",
            params={
                "file_path": file_path,
                "create_backup": request.create_backup
            },
            project_id=request.project_id
        )
        
        background_tasks.add_task(
            process_job,
            job_id,
            app.state.database,
            app.state.blender_manager
        )
        
        # Update project file path if provided
        if request.file_path and request.file_path != project["file_path"]:
            app.state.database.update_project(
                project_id=request.project_id,
                file_path=request.file_path
            )
        
        return {
            "project_id": request.project_id,
            "job_id": job_id,
            "file_path": file_path,
            "message": "Project saving started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/current")
async def get_current_project_info(background_tasks: BackgroundTasks):
    """Get information about the current Blender project"""
    job_id = app.state.database.add_job("get_project_info")
    background_tasks.add_task(
        process_job,
        job_id,
        app.state.database,
        app.state.blender_manager
    )
    return {"job_id": job_id}

@app.get("/api/projects/{project_id}/jobs", response_model=List[JobInfo])
async def list_project_jobs(project_id: str, limit: int = 50):
    """List jobs for a specific project"""
    try:
        # Verify project exists
        project = app.state.database.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        jobs = app.state.database.list_project_jobs(project_id, limit=limit)
        return jobs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing project jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))