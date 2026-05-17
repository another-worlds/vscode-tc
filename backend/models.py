# Pydantic models for request/response validation
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID

# ============================================================================
# Authentication & User Models
# ============================================================================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    roles: List[str] = Field(default=["analyst"])

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    debug_override: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class TokenData(BaseModel):
    sub: str  # username
    user_id: UUID
    roles: List[str]
    debug_override: bool

# ============================================================================
# Workspace Models
# ============================================================================

class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    storage_quota_gb: float = Field(default=100.0, ge=0)

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    storage_quota_gb: Optional[float] = None

class WorkspaceResponse(WorkspaceBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WorkspaceDashboard(WorkspaceResponse):
    project_count: int = 0
    job_count: int = 0
    storage_used_gb: float = 0.0

# ============================================================================
# Project Models
# ============================================================================

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    video_path: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    line_config: Optional[dict] = None

class ProjectResponse(ProjectBase):
    id: UUID
    workspace_id: UUID
    status: str  # uploaded, processing, done, failed
    resolution: Optional[str] = None
    duration_sec: Optional[int] = None
    file_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProjectDashboard(ProjectResponse):
    line_config: dict = {}
    od_matrix: dict = {}
    total_tracks: int = 0
    current_job_id: Optional[UUID] = None
    job_progress_percent: int = 0

# ============================================================================
# Line Configuration Models
# ============================================================================

class Point(BaseModel):
    x: float
    y: float

class LineConfig(BaseModel):
    id: str
    name: str
    points: List[tuple]  # [(x1, y1), (x2, y2)]
    color: Optional[str] = "#FF0000"
    visible: bool = True

class LineConfigUpdate(BaseModel):
    lines: List[LineConfig]

# ============================================================================
# Analytics & Export Models
# ============================================================================

class ODMatrixResponse(BaseModel):
    origin_zones: List[str]
    destination_zones: List[str]
    matrix: List[List[int]]  # 2D array of counts
    total: int
    timestamp: datetime

class ExportRequest(BaseModel):
    export_format: str = "od_matrix"  # od_matrix, tracking_data, statistics
    include_trajectories: bool = False

class ExportResponse(BaseModel):
    status: str
    file_path: str
    file_size_bytes: int
    download_url: str
    expires_in_seconds: int

# ============================================================================
# Job & Processing Models
# ============================================================================

class JobBase(BaseModel):
    video_id: UUID
    status: str = "pending"  # pending, processing, done, failed

class JobResponse(JobBase):
    id: UUID
    workspace_id: UUID
    worker_id: Optional[str] = None
    progress_percent: int = 0
    error_message: Optional[str] = None
    parquet_path: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ============================================================================
# Audit Log Models
# ============================================================================

class AuditLogEntry(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    target_id: Optional[UUID] = None
    target_type: str
    details: dict = {}
    timestamp: datetime
    ip_address: Optional[str] = None
    
    class Config:
        from_attributes = True

class AuditLogFilter(BaseModel):
    user_id: Optional[UUID] = None
    action: Optional[str] = None
    target_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)

# ============================================================================
# Error & Health Check Models
# ============================================================================

class HealthStatus(BaseModel):
    status: str = "ok"
    database: str = "ok"
    redis: str = "ok"
    version: str = "1.0"

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
