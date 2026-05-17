# SQLModel ORM models for database tables
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr

# ============================================================================
# User Model
# ============================================================================

class User(SQLModel, table=True):
    """User account with roles for RBAC"""
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, min_length=3, max_length=50)
    email: EmailStr = Field(unique=True)
    hashed_password: str
    roles: List[str] = Field(default=["analyst"])  # JSON stored as list
    debug_override: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    workspaces: List["Workspace"] = Relationship(back_populates="owner")
    audit_logs: List["AuditLog"] = Relationship(back_populates="user")

# ============================================================================
# Workspace Model
# ============================================================================

class Workspace(SQLModel, table=True):
    """Workspace: top-level organizational unit"""
    __tablename__ = "workspaces"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=255)
    owner_id: UUID = Field(foreign_key="users.id")
    storage_quota_gb: float = Field(default=100.0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    projects: List["Project"] = Relationship(back_populates="workspace")
    jobs: List["Job"] = Relationship(back_populates="workspace")

# ============================================================================
# Project Model
# ============================================================================

class Project(SQLModel, table=True):
    """Project: individual video processing task"""
    __tablename__ = "projects"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id")
    name: str = Field(max_length=255)
    video_path: str = Field(max_length=1024)
    file_hash: Optional[str] = Field(default=None, unique=True)
    resolution: Optional[str] = Field(default=None, max_length=20)
    duration_sec: Optional[int] = Field(default=None, ge=0)
    status: str = Field(default="uploaded")  # uploaded, processing, done, failed
    line_config: dict = Field(default={})  # JSON
    od_matrix: dict = Field(default={})  # JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    workspace: Workspace = Relationship(back_populates="projects")
    jobs: List["Job"] = Relationship(back_populates="video")

# ============================================================================
# Job Model (Processing Queue State)
# ============================================================================

class Job(SQLModel, table=True):
    """Job: processing queue entry for a project video"""
    __tablename__ = "jobs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    video_id: UUID = Field(foreign_key="projects.id")
    workspace_id: UUID = Field(foreign_key="workspaces.id")
    status: str = Field(default="pending")  # pending, processing, done, failed
    worker_id: Optional[str] = Field(default=None, max_length=255)
    progress_percent: int = Field(default=0, ge=0, le=100)
    error_message: Optional[str] = Field(default=None)
    parquet_path: Optional[str] = Field(default=None, max_length=1024)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    video: Project = Relationship(back_populates="jobs")
    workspace: Workspace = Relationship(back_populates="jobs")

# ============================================================================
# Audit Log Model
# ============================================================================

class AuditLog(SQLModel, table=True):
    """AuditLog: immutable record of all mutations"""
    __tablename__ = "audit_logs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    action: str = Field(max_length=50)  # CREATE, UPDATE, DELETE, EXPORT, etc.
    target_id: Optional[UUID] = Field(default=None)
    target_type: str = Field(max_length=50)  # Project, Workspace, User, Job
    details: dict = Field(default={})  # JSON: old_value, new_value, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    
    # Relationships
    user: User = Relationship(back_populates="audit_logs")
