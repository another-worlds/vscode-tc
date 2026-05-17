# Grand Contract v1.0 — M9 Dashboard Router
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.dashboard import WorkspaceDashboard, ProjectDashboard
from app.services import auth_service, dashboard_service
from app.models.workspace import UserRole

router = APIRouter(prefix="/workspaces", tags=["dashboard"])


@router.get("/{workspace_id}/dashboard", response_model=WorkspaceDashboard)
async def workspace_dashboard(
    workspace_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_workspace_dashboard(workspace_id, db)


@router.get("/{workspace_id}/projects/{project_id}/dashboard", response_model=ProjectDashboard)
async def project_dashboard(
    workspace_id: UUID,
    project_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_project_dashboard(project_id, db)
