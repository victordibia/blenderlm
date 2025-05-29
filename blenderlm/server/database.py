import sqlite3
import json
import os
import time
import uuid
from contextlib import contextmanager
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"

class BlenderLMDatabase:
    """
    Unified database manager for BlenderLM that handles both jobs and projects.
    Replaces SQLiteJobQueue with extended functionality for project management.
    """
    
    def __init__(self, db_path="blenderlm.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize database with both job and project tables"""
        with self._get_conn() as conn:
            # Create projects table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    file_path TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    last_opened_at REAL,
                    metadata TEXT
                )
            ''')
            
            # Create jobs table (with project_id foreign key)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    command_type TEXT NOT NULL,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    completed_at REAL,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            # Create job queue table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_project_id ON jobs (project_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects (updated_at)')
            
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # =============================================================================
    # PROJECT MANAGEMENT METHODS
    # =============================================================================
    
    def create_project(self, name: str, description: str = "", file_path: str = "", 
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new project and return its ID"""
        project_id = str(uuid.uuid4())
        current_time = time.time()
        
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO projects 
                   (id, name, description, file_path, status, created_at, updated_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, 
                    name, 
                    description, 
                    file_path,
                    ProjectStatus.ACTIVE.value,
                    current_time,
                    current_time,
                    json.dumps(metadata or {})
                )
            )
            conn.commit()
        
        logger.info(f"Created project: {name} ({project_id})")
        return project_id
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            project = dict(row)
            if project["metadata"]:
                project["metadata"] = json.loads(project["metadata"])
            return project
    
    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a project by name"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM projects WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            project = dict(row)
            if project["metadata"]:
                project["metadata"] = json.loads(project["metadata"])
            return project
    
    def list_projects(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List projects, optionally filtered by status"""
        with self._get_conn() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                )
            
            projects = []
            for row in cursor:
                project = dict(row)
                if project["metadata"]:
                    project["metadata"] = json.loads(project["metadata"])
                projects.append(project)
            
            return projects
    
    def update_project(self, project_id: str, name: Optional[str] = None, 
                      description: Optional[str] = None, file_path: Optional[str] = None,
                      status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update project information"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if file_path is not None:
            updates.append("file_path = ?")
            params.append(file_path)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
            
        if not updates:
            return False
            
        updates.append("updated_at = ?")
        params.append(time.time())
        params.append(project_id)
        
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def update_project_last_opened(self, project_id: str) -> bool:
        """Update the last_opened_at timestamp for a project"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE projects SET last_opened_at = ?, updated_at = ? WHERE id = ?",
                (time.time(), time.time(), project_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its associated jobs"""
        with self._get_conn() as conn:
            # First delete all jobs associated with this project
            conn.execute("DELETE FROM queue WHERE job_id IN (SELECT id FROM jobs WHERE project_id = ?)", (project_id,))
            conn.execute("DELETE FROM jobs WHERE project_id = ?", (project_id,))
            
            # Then delete the project
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Deleted project {project_id}")
                return True
            return False

    # =============================================================================
    # JOB MANAGEMENT METHODS (Updated to support projects)
    # =============================================================================
        
    def add_job(self, command_type: str, params: Optional[Dict[str, Any]] = None, 
                project_id: Optional[str] = None) -> str:
        """Add a job to the queue, optionally associated with a project"""
        job_id = str(uuid.uuid4())
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, NULL)",
                    (
                        job_id, 
                        project_id,
                        command_type, 
                        json.dumps(params or {}),
                        JobStatus.PENDING.value,
                        time.time()
                    )
                )
                conn.execute("INSERT INTO queue (job_id) VALUES (?)", (job_id,))
                conn.commit()
            return job_id
        except Exception as e:
            logger.error(f"Error adding job: {str(e)}")
            raise e
        
    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """Get the next job from the queue"""
        with self._get_conn() as conn:
            conn.execute("BEGIN EXCLUSIVE TRANSACTION")
            
            cursor = conn.execute("SELECT job_id FROM queue ORDER BY id LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                conn.commit()
                return None
                
            job_id = row[0]
            
            conn.execute("DELETE FROM queue WHERE job_id = ?", (job_id,))
            
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            job_row = cursor.fetchone()
            
            conn.execute(
                "UPDATE jobs SET status = ? WHERE id = ?",
                (JobStatus.PROCESSING.value, job_id)
            )
            
            conn.commit()
            
            if job_row:
                return {
                    "id": job_row["id"],
                    "project_id": job_row["project_id"],
                    "command_type": job_row["command_type"],
                    "params": json.loads(job_row["params"]),
                    "status": job_row["status"]
                }
            return None
    
    def update_job(self, job_id: str, status: Union[JobStatus, str], result=None, error=None):
        """Update job status and result"""
        if isinstance(status, str):
            status = JobStatus(status)
            
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, result = ?, error = ?, completed_at = ? WHERE id = ?",
                (status.value, json.dumps(result) if result else None, error, time.time(), job_id)
            )
            conn.commit()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            job = dict(row)
            if job["params"]:
                job["params"] = json.loads(job["params"])
            if job["result"]:
                job["result"] = json.loads(job["result"])
            return job
    
    def list_pending_jobs(self) -> List[Dict[str, Any]]:
        """List all pending jobs in queue"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT jobs.* FROM jobs JOIN queue ON jobs.id = queue.job_id ORDER BY jobs.created_at DESC"
            )
            jobs = []
            for row in cursor:
                job = dict(row)
                if job["params"]:
                    job["params"] = json.loads(job["params"])
                if job["result"]:
                    job["result"] = json.loads(job["result"])
                jobs.append(job)
            return jobs
    
    def list_project_jobs(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List jobs for a specific project"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit)
            )
            jobs = []
            for row in cursor:
                job = dict(row)
                if job["params"]:
                    job["params"] = json.loads(job["params"])
                if job["result"]:
                    job["result"] = json.loads(job["result"])
                jobs.append(job)
            return jobs

    def clean_old_jobs(self, max_age_hours=24):
        """Remove completed/failed jobs older than the specified age"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM jobs WHERE status IN (?, ?) AND completed_at < ?",
                (JobStatus.COMPLETED.value, JobStatus.FAILED.value, cutoff_time)
            )
            conn.commit()

    # =============================================================================
    # MIGRATION METHOD (for transitioning from SQLiteJobQueue)
    # =============================================================================
    
    def migrate_from_job_queue_db(self, old_db_path: str) -> bool:
        """Migrate data from the old job queue database format"""
        if not os.path.exists(old_db_path):
            logger.info(f"No old database found at {old_db_path}, starting fresh")
            return True
            
        try:
            # Connect to old database
            old_conn = sqlite3.connect(old_db_path)
            old_conn.row_factory = sqlite3.Row
            
            # Get existing jobs from old database
            cursor = old_conn.execute("SELECT * FROM jobs")
            old_jobs = [dict(row) for row in cursor.fetchall()]
            
            cursor = old_conn.execute("SELECT * FROM queue")
            old_queue = [dict(row) for row in cursor.fetchall()]
            
            old_conn.close()
            
            # Insert into new database
            with self._get_conn() as conn:
                for job in old_jobs:
                    # Insert job with project_id as NULL (no project association)
                    conn.execute(
                        "INSERT OR IGNORE INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            job["id"],
                            None,  # project_id
                            job["command_type"],
                            job["params"],
                            job["status"],
                            job["result"],
                            job["error"],
                            job["created_at"],
                            job["completed_at"]
                        )
                    )
                
                # Insert queue entries
                for queue_item in old_queue:
                    conn.execute(
                        "INSERT OR IGNORE INTO queue (job_id) VALUES (?)",
                        (queue_item["job_id"],)
                    )
                
                conn.commit()
            
            logger.info(f"Successfully migrated {len(old_jobs)} jobs from {old_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate from old database: {str(e)}")
            return False
