import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import BlenderLMDatabase
from .connection import BlenderConnectionManager
from .models import *


from .routes import blender, jobs, projects, misc
from .routes import ws  # Import the new WebSocket router

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

# Register routers
app.include_router(blender.router)
app.include_router(jobs.router)
app.include_router(projects.router)
app.include_router(misc.router)
app.include_router(ws.router)  # Add the WebSocket router

# All endpoint definitions have been moved to the routes/ folder.