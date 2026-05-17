# Workspace management router
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.security import get_current_user, require_pm_or_admin
from backend.models import TokenData, WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceDashboard
from backend.crud import WorkspaceCRUD, AuditLogCRUD

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# ============================================================================
# Workspace CRUD Endpoints
# ============================================================================

@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    workspace: WorkspaceCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_pm_or_admin)
):
    """
    Create a new workspace
    
    RBAC: pm or admin
    - User becomes owner
    - Ownership determines read/write access
    """
    db_workspace = WorkspaceCRUD.create(db, workspace, current_user.user_id)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="CREATE",
        target_type="Workspace",
        target_id=db_workspace.id,
        details={"name": workspace.name, "quota_gb": workspace.storage_quota_gb},
        ip_address=request.client.host if request else None
    )
    
    return db_workspace

@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    skip: int = 0,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List workspaces owned by current user
    
    RBAC: any authenticated user
    """
    workspaces = WorkspaceCRUD.list_by_owner(db, current_user.user_id, skip, limit)
    return workspaces

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get workspace details
    
    RBAC: owner or admin
    """
    workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check ownership
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
    
    return workspace

@router.get("/{workspace_id}/dashboard", response_model=WorkspaceDashboard)
async def get_workspace_dashboard(
    workspace_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get workspace dashboard with metrics
    
    Returns: project count, job count, storage used, quota
    RBAC: owner or admin
    """
    workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check ownership
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    dashboard = WorkspaceCRUD.get_dashboard(db, workspace_id)
    return dashboard

@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    workspace_update: WorkspaceUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Update workspace (name, quota)
    
    RBAC: owner or admin
    """
    workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check ownership
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Store old values for audit
    old_values = {"name": workspace.name, "quota_gb": workspace.storage_quota_gb}
    
    updated_workspace = WorkspaceCRUD.update(db, workspace_id, workspace_update)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="UPDATE",
        target_type="Workspace",
        target_id=workspace_id,
        details={"old": old_values, "new": workspace_update.dict(exclude_none=True)},
        ip_address=request.client.host if request else None
    )
    
    return updated_workspace

@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_pm_or_admin)
):
    """
    Delete workspace (cascade to projects and jobs)
    
    RBAC: owner or admin
    """
    workspace = WorkspaceCRUD.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check ownership
    if workspace.owner_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    WorkspaceCRUD.delete(db, workspace_id)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="DELETE",
        target_type="Workspace",
        target_id=workspace_id,
        details={"name": workspace.name},
        ip_address=request.client.host if request else None
    )
    
    return None
