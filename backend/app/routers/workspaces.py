# Grand Contract v1.0 — M2 Workspace Router
import uuid as uuid_lib
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut, MemberAdd, MemberOut
from app.services import auth_service
from app.services.dashboard_service import get_workspace_dashboard
from app.models.workspace import Workspace, WorkspaceMember, UserRole
from app.schemas.dashboard import WorkspaceDashboard

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/", response_model=list[WorkspaceOut])
async def list_workspaces(
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceOut]:
    """List all workspaces the current user is a member of."""
    stmt = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    workspaces = result.scalars().all()
    return [WorkspaceOut.model_validate(w) for w in workspaces]


@router.post("/", response_model=WorkspaceOut, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    """Create workspace. ADMIN only."""
    workspace = Workspace(
        name=payload.name,
        owner_id=current_user.id,
        created_by=current_user.id,
    )
    db.add(workspace)
    await db.flush()
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=UserRole.ADMIN,
        assigned_by=current_user.id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceOut.model_validate(workspace)


@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=201)
async def add_member(
    workspace_id: UUID,
    payload: MemberAdd,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    """Add or update a user's role in the workspace."""
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == payload.user_id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if member:
        member.role = payload.role
        member.assigned_by = current_user.id
    else:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=payload.role,
            assigned_by=current_user.id,
        )
        db.add(member)
    await db.commit()
    await db.refresh(member)
    return MemberOut.model_validate(member)


@router.get("/{workspace_id}/dashboard", response_model=WorkspaceDashboard)
async def workspace_dashboard(
    workspace_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return WorkspaceDashboard aggregate stats."""
    return await get_workspace_dashboard(workspace_id, db)
