import sqlite3
import json
import os
import time
import uuid
from contextlib import contextmanager
from enum import Enum
from typing import Dict, Any, Optional, List, Union

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SQLiteJobQueue:
    def __init__(self, db_path="blenderlm_jobs.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command_type TEXT NOT NULL,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    completed_at REAL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            ''')
            
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)  # 30-second timeout for locks
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def add_job(self, command_type: str, params: Optional[Dict[str, Any]] = None) -> str:
        job_id = str(uuid.uuid4())
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO jobs VALUES (?, ?, ?, ?, NULL, NULL, ?, NULL)",
                    (
                        job_id, 
                        command_type, 
                        json.dumps(params or {}),
                        JobStatus.PENDING,
                        time.time()
                    )
                )
                conn.execute("INSERT INTO queue (job_id) VALUES (?)", (job_id,))
                conn.commit()  # Ensure transaction is committed
            return job_id
        except Exception as e:
            print(f"Error adding job: {str(e)}")
            raise e
        
    def get_next_job(self) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            # Use a transaction to ensure atomicity
            conn.execute("BEGIN EXCLUSIVE TRANSACTION")
            
            # Get next job from queue
            cursor = conn.execute("SELECT job_id FROM queue ORDER BY id LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                conn.commit()
                return None
                
            job_id = row[0]
            
            # Remove from queue
            conn.execute("DELETE FROM queue WHERE job_id = ?", (job_id,))
            
            # Get job details
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            job_row = cursor.fetchone()
            
            # Update status to processing
            conn.execute(
                "UPDATE jobs SET status = ? WHERE id = ?",
                (JobStatus.PROCESSING, job_id)
            )
            
            conn.commit()
            
            if job_row:
                return {
                    "id": job_row["id"],
                    "command_type": job_row["command_type"],
                    "params": json.loads(job_row["params"]),
                    "status": job_row["status"]
                }
            return None
    
    def update_job(self, job_id: str, status: Union[JobStatus, str], result=None, error=None):
        # Convert string status to enum if needed
        if isinstance(status, str):
            status = JobStatus(status)
            
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, result = ?, error = ?, completed_at = ? WHERE id = ?",
                (status.value, json.dumps(result) if result else None, error, time.time(), job_id)
            )
            conn.commit()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
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
    
    def clean_old_jobs(self, max_age_hours=24):
        """Remove completed/failed jobs older than the specified age"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM jobs WHERE status IN (?, ?) AND completed_at < ?",
                (JobStatus.COMPLETED.value, JobStatus.FAILED.value, cutoff_time)
            )