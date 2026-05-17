# Grand Contract v1.0 — M1 Auth Pydantic schemas
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class TokenResponse(BaseModel):
    """JWT access token returned after successful OAuth2 callback."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserOut(BaseModel):
    """Public user profile returned in API responses."""
    id: UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CurrentUser(BaseModel):
    """
    Dependency-injected current user.
    In DEBUG=1 mode, a synthetic ADMIN user is always returned.
    """
    id: UUID
    email: str
    display_name: str
    role: str = "ADMIN"  # resolved per workspace context
