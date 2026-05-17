# Grand Contract v1.0 — M2/M3 Workspace & Project Pydantic schemas
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.workspace import UserRole


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    user_id: UUID
    role: UserRole


class MemberOut(BaseModel):
    user_id: UUID
    role: UserRole
    assigned_at: datetime
    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str
    location_label: str | None = None


class ProjectOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    location_label: str | None
    created_at: datetime
    created_by: UUID
    model_config = {"from_attributes": True}
