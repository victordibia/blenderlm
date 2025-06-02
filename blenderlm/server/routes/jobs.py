from fastapi import APIRouter, HTTPException, Request
from typing import List
from ..models import JobInfo

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/", response_model=List[JobInfo])
async def list_jobs(request: Request):
    """List pending jobs"""
    return request.app.state.database.list_pending_jobs()

@router.get("/{job_id}", response_model=JobInfo)
async def get_job(job_id: str, request: Request):
    """Get job status and result"""
    job = request.app.state.database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
