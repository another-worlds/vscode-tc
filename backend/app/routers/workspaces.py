# Grand Contract v1.0 — M2 Workspace Router
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut, MemberAdd, MemberOut
from app.services import auth_service
from app.models.workspace import UserRole

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/", response_model=list[WorkspaceOut])
async def list_workspaces(
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceOut]:
    """List all workspaces the current user is a member of."""
    # TODO: implement per contract
    pass


@router.post("/", response_model=WorkspaceOut, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    """Create workspace. ADMIN only. Fires WORKSPACE_CREATED audit."""
    # TODO: implement per contract
    pass


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    # TODO: implement per contract
    pass


@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=201)
async def add_member(
    workspace_id: UUID,
    payload: MemberAdd,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    """Add or update a user's role in the workspace."""
    # TODO: implement per contract
    pass


@router.get("/{workspace_id}/dashboard")
async def workspace_dashboard(
    workspace_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return WorkspaceDashboard aggregate stats."""
    # TODO: implement per contract
    pass
