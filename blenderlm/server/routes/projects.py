from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import Optional, List
from ..models import (
    ProjectInfo,
    CreateProjectRequest,
    UpdateProjectRequest,
    LoadProjectRequest,
    SaveProjectRequest,
    NewProjectRequest,
    ProjectListResponse,
    JobInfo
)
import logging

router = APIRouter(prefix="/api/projects", tags=["projects"])
logger = logging.getLogger("blenderlm.api")

@router.get("/", response_model=ProjectListResponse)
async def list_projects(request: Request, status: Optional[str] = None, limit: int = 50):
    try:
        projects = request.app.state.database.list_projects(status=status, limit=limit)
        return ProjectListResponse(
            projects=[ProjectInfo(**project) for project in projects],
            total_count=len(projects)
        )
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_project(request_body: CreateProjectRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        project_id = request.app.state.database.create_project(
            name=request_body.name,
            description=request_body.description,
            file_path=None,
            metadata=request_body.metadata
        )
        job_id = request.app.state.database.add_job(
            command_type="new_project",
            params={"clear_scene": True},
            project_id=project_id
        )
        async def process_and_update_project(job_id, database, blender_manager, project_id):
            # This function should be imported from a shared location
            pass
        background_tasks.add_task(
            process_and_update_project,
            job_id,
            request.app.state.database,
            request.app.state.blender_manager,
            project_id
        )
        project = request.app.state.database.get_project(project_id)
        if not project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        return {"project": ProjectInfo(**project), "job_id": job_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str, request: Request):
    project = request.app.state.database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectInfo(**project)

@router.put("/{project_id}", response_model=ProjectInfo)
async def update_project(project_id: str, request_body: UpdateProjectRequest, request: Request):
    try:
        success = request.app.state.database.update_project(
            project_id=project_id,
            name=request_body.name,
            description=request_body.description,
            file_path=request_body.file_path,
            status=request_body.status.value if request_body.status else None,
            metadata=request_body.metadata
        )
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        project = request.app.state.database.get_project(project_id)
        return ProjectInfo(**project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{project_id}")
async def delete_project(project_id: str, request: Request):
    try:
        success = request.app.state.database.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Project deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load")
async def load_project(request_body: LoadProjectRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        project_id = None
        file_path = request_body.file_path
        if request_body.project_id:
            project = request.app.state.database.get_project(request_body.project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            project_id = request_body.project_id
            if project["file_path"]:
                file_path = project["file_path"]
            elif not file_path:
                raise HTTPException(status_code=400, detail="No file path available for this project")
            request.app.state.database.update_project_last_opened(project_id)
        if not file_path:
            raise HTTPException(status_code=400, detail="File path is required")
        job_id = request.app.state.database.add_job(
            command_type="load_project",
            params={"file_path": file_path},
            project_id=project_id
        )
        # This function should be imported from a shared location
        background_tasks.add_task(
            lambda: None,
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

@router.post("/save")
async def save_project(request_body: SaveProjectRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        project = request.app.state.database.get_project(request_body.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        file_path = request_body.file_path or project["file_path"]
        job_id = request.app.state.database.add_job(
            command_type="save_project",
            params={
                "file_path": file_path,
                "create_backup": request_body.create_backup
            },
            project_id=request_body.project_id
        )
        # This function should be imported from a shared location
        background_tasks.add_task(
            lambda: None,
        )
        if request_body.file_path and request_body.file_path != project["file_path"]:
            request.app.state.database.update_project(
                project_id=request_body.project_id,
                file_path=request_body.file_path
            )
        return {
            "project_id": request_body.project_id,
            "job_id": job_id,
            "file_path": file_path,
            "message": "Project saving started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current")
async def get_current_project_info(request: Request, background_tasks: BackgroundTasks):
    job_id = request.app.state.database.add_job("get_project_info")
    # This function should be imported from a shared location
    background_tasks.add_task(
        lambda: None,
    )
    return {"job_id": job_id}

@router.get("/{project_id}/jobs", response_model=List[JobInfo])
async def list_project_jobs(project_id: str, request: Request, limit: int = 50):
    try:
        project = request.app.state.database.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        jobs = request.app.state.database.list_project_jobs(project_id, limit=limit)
        return jobs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing project jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
