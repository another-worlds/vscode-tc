# Project management router
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.security import get_current_user, require_analyst
from backend.models import TokenData, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDashboard, LineConfigUpdate
from backend.crud import ProjectCRUD, WorkspaceCRUD, JobCRUD, AuditLogCRUD

router = APIRouter(prefix="/workspaces", tags=["projects"])

# ============================================================================
# Project CRUD Endpoints
# ============================================================================

@router.post("/{workspace_id}/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    workspace_id: UUID,
    project: ProjectCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_analyst)
):
    """
    Create a new project in a workspace
    
    RBAC: analyst or above
    - Creates project in workspace
    - Enqueues for processing if needed
    """
    # Verify workspace ownership/access
    workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create project
    db_project = ProjectCRUD.create(db, workspace_id, project)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="CREATE",
        target_type="Project",
        target_id=db_project.id,
        details={"name": project.name, "video_path": project.video_path},
        ip_address=request.client.host if request else None
    )
    
    return db_project

@router.get("/{workspace_id}/projects", response_model=List[ProjectResponse])
async def list_projects(
    workspace_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List projects in a workspace
    
    RBAC: workspace owner or admin
    """
    workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    projects = ProjectCRUD.list_by_workspace(db, workspace_id, skip, limit)
    return projects

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get project details
    
    RBAC: workspace owner or admin
    """
    project = ProjectCRUD.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check workspace access
    workspace = WorkspaceCRUD.get_by_id(db, project.workspace_id)
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return project

@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboard)
async def get_project_dashboard(
    project_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get project dashboard with processing status and metrics
    
    Returns: line_config, od_matrix, current job progress, total tracks
    RBAC: workspace owner or admin
    """
    project = ProjectCRUD.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check workspace access
    workspace = WorkspaceCRUD.get_by_id(db, project.workspace_id)
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    dashboard = ProjectCRUD.get_dashboard(db, project_id)
    return dashboard

@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_analyst)
):
    """
    Update project (name, line_config)
    
    RBAC: workspace owner or admin
    """
    project = ProjectCRUD.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check workspace access
    workspace = WorkspaceCRUD.get_by_id(db, project.workspace_id)
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Store old values
    old_values = {"name": project.name}
    
    updated_project = ProjectCRUD.update(db, project_id, project_update)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="UPDATE",
        target_type="Project",
        target_id=project_id,
        details={"old": old_values, "new": project_update.dict(exclude_none=True)},
        ip_address=request.client.host if request else None
    )
    
    return updated_project

@router.post("/projects/{project_id}/lines")
async def save_line_config(
    project_id: UUID,
    line_update: LineConfigUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_analyst)
):
    """
    Save line configuration for a project
    
    Receives: lines (from React component)
    RBAC: workspace owner or admin
    """
    project = ProjectCRUD.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check workspace access
    workspace = WorkspaceCRUD.get_by_id(db, project.workspace_id)
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Save line config
    line_config = {"lines": [line.dict() for line in line_update.lines]}
    updated_project = ProjectCRUD.update_line_config(db, project_id, line_config)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="UPDATE",
        target_type="Project",
        target_id=project_id,
        details={"action": "line_config_updated", "line_count": len(line_update.lines)},
        ip_address=request.client.host if request else None
    )
    
    return {"status": "ok", "project_id": project_id}

@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_analyst)
):
    """
    Delete project (cascade to jobs)
    
    RBAC: workspace owner or admin
    """
    project = ProjectCRUD.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check workspace access
    workspace = WorkspaceCRUD.get_by_id(db, project.workspace_id)
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    ProjectCRUD.delete(db, project_id)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="DELETE",
        target_type="Project",
        target_id=project_id,
        details={"name": project.name},
        ip_address=request.client.host if request else None
    )
    
    return None
