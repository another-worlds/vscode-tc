# Grand Contract v1.0 — M3 Projects Router
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.workspace import ProjectCreate, ProjectOut
from app.services import auth_service
from app.models.workspace import UserRole

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
async def list_projects(workspace_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    # TODO: implement per contract
    pass


@router.post("/", response_model=ProjectOut, status_code=201)
async def create_project(
    workspace_id: UUID,
    payload: ProjectCreate,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Create project. MANAGER+. Fires PROJECT_CREATED audit."""
    # TODO: implement per contract
    pass


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(workspace_id: UUID, project_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    # TODO: implement per contract
    pass


@router.get("/{project_id}/dashboard")
async def project_dashboard(workspace_id: UUID, project_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    """Return ProjectDashboard with video inventory."""
    # TODO: implement per contract
    pass
