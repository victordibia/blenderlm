from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import ValidationError
from ..models import (
    CodeRequest,
    CreateObjectRequest, 
    MaterialRequest, 
    ModifyObjectRequest,
    RenderRequest,
    ViewportCaptureRequest,
    ClearSceneRequest,
    AddCameraRequest
)
from ..database import BlenderLMDatabase, JobStatus
from ..connection import BlenderConnectionManager
import logging

router = APIRouter(prefix="/api/blender", tags=["blender"])
logger = logging.getLogger("blenderlm.api")

# Helper function (should be imported or moved to a utils file)
async def process_job(job_id: str, database: BlenderLMDatabase, blender_manager: BlenderConnectionManager):
    job = database.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
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

@router.get("/scene")
async def get_scene_info(request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("get_scene_info")
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.get("/objects/{name}")
async def get_object_info(name: str, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("get_object_info", {"name": name})
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.post("/viewport")
async def capture_viewport(request_body: ViewportCaptureRequest, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("capture_viewport", request_body.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.post("/objects")
async def create_object(request_body: CreateObjectRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        job_id = request.app.state.database.add_job("create_object", request_body.to_params())
        background_tasks.add_task(
            process_job, 
            job_id, 
            request.app.state.database, 
            request.app.state.blender_manager
        )
        return {"job_id": job_id}
    except Exception as e:
        logger.error(f"Error creating object: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.put("/objects/{name}")
async def modify_object(name: str, request_body: ModifyObjectRequest, request: Request, background_tasks: BackgroundTasks):
    if request_body.name is None or request_body.name != name:
        request_body.name = name
    job_id = request.app.state.database.add_job("modify_object", request_body.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.delete("/objects/{name}")
async def delete_object(name: str, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("delete_object", {"name": name})
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.post("/materials")
async def set_material(request_body: MaterialRequest, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("set_material", request_body.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.post("/render")
async def render_scene(request_body: RenderRequest, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("render_scene", request_body.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.post("/code")
async def execute_code(request_body: CodeRequest, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("execute_code", {"code": request_body.code})
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}

@router.post("/scene/clear")
async def clear_scene(request_body: ClearSceneRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        job_id = request.app.state.database.add_job("clear_scene", request_body.to_params())
        background_tasks.add_task(
            process_job, 
            job_id, 
            request.app.state.database, 
            request.app.state.blender_manager
        )
        return {"job_id": job_id}
    except ValidationError as ve:
        logger.error(f"Validation error clearing scene: {ve}")
        print(f"Error JSON: {ve.json()}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Error clearing scene: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/camera")
async def add_camera(request_body: AddCameraRequest, request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("add_camera", request_body.to_params())
    background_tasks.add_task(
        process_job, 
        job_id, 
        request.app.state.database, 
        request.app.state.blender_manager
    )
    return {"job_id": job_id}
