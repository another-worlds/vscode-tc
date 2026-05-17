# Grand Contract v1.0 — M3 Projects Router
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.workspace import ProjectCreate, ProjectOut
from app.services import auth_service
from app.services.dashboard_service import get_project_dashboard
from app.models.workspace import UserRole
from app.models.project import Project
from app.schemas.dashboard import ProjectDashboard

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
async def list_projects(
    workspace_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Project).where(Project.workspace_id == workspace_id)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [ProjectOut.model_validate(p) for p in projects]


@router.post("/", response_model=ProjectOut, status_code=201)
async def create_project(
    workspace_id: UUID,
    payload: ProjectCreate,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Create project. MANAGER+."""
    project = Project(
        workspace_id=workspace_id,
        name=payload.name,
        location_label=payload.location_label,
        created_by=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    workspace_id: UUID,
    project_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectOut.model_validate(project)


@router.get("/{project_id}/dashboard", response_model=ProjectDashboard)
async def project_dashboard(
    workspace_id: UUID,
    project_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return ProjectDashboard with video inventory."""
    return await get_project_dashboard(project_id, db)
