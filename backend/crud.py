# CRUD operations for all models
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from backend.db_models import User, Workspace, Project, Job, AuditLog
from backend.security import hash_password, verify_password
from backend.models import (
    UserCreate, UserResponse,
    WorkspaceCreate, WorkspaceUpdate, WorkspaceDashboard,
    ProjectCreate, ProjectUpdate, ProjectDashboard,
    AuditLogFilter
)

# ============================================================================
# User CRUD
# ============================================================================

class UserCRUD:
    """CRUD operations for User"""
    
    @staticmethod
    def create(db: Session, user_create: UserCreate) -> User:
        """Create a new user"""
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hash_password(user_create.password),
            roles=user_create.roles
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users (admin only)"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_roles(db: Session, user_id: UUID, roles: List[str]) -> Optional[User]:
        """Update user roles (admin only)"""
        db_user = UserCRUD.get_by_id(db, user_id)
        if not db_user:
            return None
        db_user.roles = roles
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def update_debug_override(db: Session, user_id: UUID, debug_override: bool) -> Optional[User]:
        """Update debug_override flag (admin only)"""
        db_user = UserCRUD.get_by_id(db, user_id)
        if not db_user:
            return None
        db_user.debug_override = debug_override
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def verify_password(db: Session, username: str, password: str) -> Optional[User]:
        """Verify user password (for login)"""
        db_user = UserCRUD.get_by_username(db, username)
        if not db_user or not verify_password(password, db_user.hashed_password):
            return None
        return db_user

# ============================================================================
# Workspace CRUD
# ============================================================================

class WorkspaceCRUD:
    """CRUD operations for Workspace"""
    
    @staticmethod
    def create(db: Session, workspace_create: WorkspaceCreate, owner_id: UUID) -> Workspace:
        """Create a new workspace"""
        db_workspace = Workspace(
            name=workspace_create.name,
            owner_id=owner_id,
            storage_quota_gb=workspace_create.storage_quota_gb
        )
        db.add(db_workspace)
        db.commit()
        db.refresh(db_workspace)
        return db_workspace
    
    @staticmethod
    def get_by_id(db: Session, workspace_id: UUID) -> Optional[Workspace]:
        """Get workspace by ID"""
        return db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    @staticmethod
    def list_by_owner(db: Session, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[Workspace]:
        """List workspaces owned by user"""
        return db.query(Workspace)\
            .filter(Workspace.owner_id == owner_id)\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    @staticmethod
    def update(db: Session, workspace_id: UUID, workspace_update: WorkspaceUpdate) -> Optional[Workspace]:
        """Update workspace"""
        db_workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
        if not db_workspace:
            return None
        
        if workspace_update.name:
            db_workspace.name = workspace_update.name
        if workspace_update.storage_quota_gb is not None:
            db_workspace.storage_quota_gb = workspace_update.storage_quota_gb
        
        db_workspace.updated_at = datetime.utcnow()
        db.add(db_workspace)
        db.commit()
        db.refresh(db_workspace)
        return db_workspace
    
    @staticmethod
    def delete(db: Session, workspace_id: UUID) -> bool:
        """Delete workspace (cascade to projects and jobs)"""
        db_workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
        if not db_workspace:
            return False
        
        db.delete(db_workspace)
        db.commit()
        return True
    
    @staticmethod
    def get_dashboard(db: Session, workspace_id: UUID) -> Optional[WorkspaceDashboard]:
        """Get workspace dashboard metrics"""
        db_workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
        if not db_workspace:
            return None
        
        # Count projects and jobs
        project_count = db.query(Project).filter(Project.workspace_id == workspace_id).count()
        job_count = db.query(Job).filter(Job.workspace_id == workspace_id).count()
        
        # TODO: Calculate actual storage used from Parquet files
        storage_used_gb = 0.0
        
        return WorkspaceDashboard(
            id=db_workspace.id,
            name=db_workspace.name,
            owner_id=db_workspace.owner_id,
            storage_quota_gb=db_workspace.storage_quota_gb,
            created_at=db_workspace.created_at,
            updated_at=db_workspace.updated_at,
            project_count=project_count,
            job_count=job_count,
            storage_used_gb=storage_used_gb
        )

# ============================================================================
# Project CRUD
# ============================================================================

class ProjectCRUD:
    """CRUD operations for Project"""
    
    @staticmethod
    def create(db: Session, workspace_id: UUID, project_create: ProjectCreate) -> Project:
        """Create a new project"""
        db_project = Project(
            workspace_id=workspace_id,
            name=project_create.name,
            video_path=project_create.video_path
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def get_by_id(db: Session, project_id: UUID) -> Optional[Project]:
        """Get project by ID"""
        return db.query(Project).filter(Project.id == project_id).first()
    
    @staticmethod
    def get_by_file_hash(db: Session, file_hash: str) -> Optional[Project]:
        """Get project by file hash (for deduplication)"""
        return db.query(Project).filter(Project.file_hash == file_hash).first()
    
    @staticmethod
    def list_by_workspace(db: Session, workspace_id: UUID, skip: int = 0, limit: int = 100) -> List[Project]:
        """List projects in a workspace"""
        return db.query(Project)\
            .filter(Project.workspace_id == workspace_id)\
            .order_by(desc(Project.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    @staticmethod
    def update(db: Session, project_id: UUID, project_update: ProjectUpdate) -> Optional[Project]:
        """Update project"""
        db_project = ProjectCRUD.get_by_id(db, project_id)
        if not db_project:
            return None
        
        if project_update.name:
            db_project.name = project_update.name
        if project_update.line_config is not None:
            db_project.line_config = project_update.line_config
        
        db_project.updated_at = datetime.utcnow()
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def update_line_config(db: Session, project_id: UUID, line_config: dict) -> Optional[Project]:
        """Update project line configuration"""
        db_project = ProjectCRUD.get_by_id(db, project_id)
        if not db_project:
            return None
        
        db_project.line_config = line_config
        db_project.updated_at = datetime.utcnow()
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def update_od_matrix(db: Session, project_id: UUID, od_matrix: dict) -> Optional[Project]:
        """Update project OD matrix result"""
        db_project = ProjectCRUD.get_by_id(db, project_id)
        if not db_project:
            return None
        
        db_project.od_matrix = od_matrix
        db_project.updated_at = datetime.utcnow()
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def update_status(db: Session, project_id: UUID, status: str) -> Optional[Project]:
        """Update project processing status"""
        db_project = ProjectCRUD.get_by_id(db, project_id)
        if not db_project:
            return None
        
        db_project.status = status
        db_project.updated_at = datetime.utcnow()
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def delete(db: Session, project_id: UUID) -> bool:
        """Delete project (cascade to jobs)"""
        db_project = ProjectCRUD.get_by_id(db, project_id)
        if not db_project:
            return False
        
        db.delete(db_project)
        db.commit()
        return True
    
    @staticmethod
    def get_dashboard(db: Session, project_id: UUID) -> Optional[ProjectDashboard]:
        """Get project dashboard with current job info"""
        db_project = ProjectCRUD.get_by_id(db, project_id)
        if not db_project:
            return None
        
        # Get most recent job
        current_job = db.query(Job)\
            .filter(Job.video_id == project_id)\
            .order_by(desc(Job.created_at))\
            .first()
        
        return ProjectDashboard(
            id=db_project.id,
            workspace_id=db_project.workspace_id,
            name=db_project.name,
            video_path=db_project.video_path,
            status=db_project.status,
            resolution=db_project.resolution,
            duration_sec=db_project.duration_sec,
            created_at=db_project.created_at,
            updated_at=db_project.updated_at,
            line_config=db_project.line_config,
            od_matrix=db_project.od_matrix,
            current_job_id=current_job.id if current_job else None,
            job_progress_percent=current_job.progress_percent if current_job else 0,
            total_tracks=0  # TODO: Count from Parquet
        )

# ============================================================================
# Job CRUD
# ============================================================================

class JobCRUD:
    """CRUD operations for Job"""
    
    @staticmethod
    def create(db: Session, video_id: UUID, workspace_id: UUID) -> Job:
        """Create a new job"""
        db_job = Job(
            video_id=video_id,
            workspace_id=workspace_id
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job
    
    @staticmethod
    def get_by_id(db: Session, job_id: UUID) -> Optional[Job]:
        """Get job by ID"""
        return db.query(Job).filter(Job.id == job_id).first()
    
    @staticmethod
    def list_by_status(db: Session, status: str, limit: int = 100) -> List[Job]:
        """List jobs by status"""
        return db.query(Job)\
            .filter(Job.status == status)\
            .order_by(Job.created_at)\
            .limit(limit)\
            .all()
    
    @staticmethod
    def update_status(db: Session, job_id: UUID, status: str) -> Optional[Job]:
        """Update job status"""
        db_job = JobCRUD.get_by_id(db, job_id)
        if not db_job:
            return None
        
        db_job.status = status
        if status == "processing" and db_job.started_at is None:
            db_job.started_at = datetime.utcnow()
        elif status == "done" or status == "failed":
            db_job.completed_at = datetime.utcnow()
        
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job
    
    @staticmethod
    def update_progress(db: Session, job_id: UUID, progress_percent: int) -> Optional[Job]:
        """Update job progress"""
        db_job = JobCRUD.get_by_id(db, job_id)
        if not db_job:
            return None
        
        db_job.progress_percent = max(0, min(100, progress_percent))
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job
    
    @staticmethod
    def set_error(db: Session, job_id: UUID, error_message: str) -> Optional[Job]:
        """Set job error and mark as failed"""
        db_job = JobCRUD.get_by_id(db, job_id)
        if not db_job:
            return None
        
        db_job.error_message = error_message
        db_job.status = "failed"
        db_job.completed_at = datetime.utcnow()
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job

# ============================================================================
# Audit Log CRUD
# ============================================================================

class AuditLogCRUD:
    """CRUD operations for AuditLog (immutable)"""
    
    @staticmethod
    def create(
        db: Session,
        user_id: UUID,
        action: str,
        target_type: str,
        target_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Create audit log entry (immutable insert only)"""
        db_log = AuditLog(
            user_id=user_id,
            action=action,
            target_id=target_id,
            target_type=target_type,
            details=details or {},
            ip_address=ip_address
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log
    
    @staticmethod
    def list_filtered(db: Session, filter_params: AuditLogFilter) -> List[AuditLog]:
        """List audit logs with optional filters"""
        query = db.query(AuditLog)
        
        if filter_params.user_id:
            query = query.filter(AuditLog.user_id == filter_params.user_id)
        
        if filter_params.action:
            query = query.filter(AuditLog.action == filter_params.action)
        
        if filter_params.target_type:
            query = query.filter(AuditLog.target_type == filter_params.target_type)
        
        if filter_params.date_from:
            query = query.filter(AuditLog.timestamp >= filter_params.date_from)
        
        if filter_params.date_to:
            query = query.filter(AuditLog.timestamp <= filter_params.date_to)
        
        return query\
            .order_by(desc(AuditLog.timestamp))\
            .offset(filter_params.offset)\
            .limit(filter_params.limit)\
            .all()
