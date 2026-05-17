# User and admin management router
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.security import get_current_user, require_admin
from backend.models import TokenData, UserCreate, UserResponse
from backend.crud import UserCRUD, AuditLogCRUD

router = APIRouter(prefix="/users", tags=["users"])

# ============================================================================
# User Management Endpoints (Admin Only)
# ============================================================================

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_admin)
):
    """
    Create a new user
    
    RBAC: admin only
    """
    # Check if user already exists
    existing_user = UserCRUD.get_by_username(db, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check email
    from backend.db_models import User as UserModel
    existing_email = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    db_user = UserCRUD.create(db, user)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="CREATE",
        target_type="User",
        target_id=db_user.id,
        details={"username": user.username, "email": user.email, "roles": user.roles},
        ip_address=request.client.host if request else None
    )
    
    return db_user

@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    List all users
    
    RBAC: admin only
    """
    users = UserCRUD.get_all(db, skip, limit)
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user details
    
    RBAC: self or admin
    """
    user = UserCRUD.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # User can only see their own info unless they're admin
    if user_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return user

@router.patch("/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: UUID,
    roles: List[str],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_admin)
):
    """
    Update user roles
    
    RBAC: admin only
    """
    user = UserCRUD.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_roles = user.roles.copy()
    updated_user = UserCRUD.update_roles(db, user_id, roles)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="UPDATE",
        target_type="User",
        target_id=user_id,
        details={"old_roles": old_roles, "new_roles": roles},
        ip_address=request.client.host if request else None
    )
    
    return updated_user

@router.patch("/{user_id}/debug-override", response_model=UserResponse)
async def update_debug_override(
    user_id: UUID,
    debug_override: bool,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
    _: None = Depends(require_admin)
):
    """
    Update user debug_override flag
    
    RBAC: admin only
    """
    user = UserCRUD.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_value = user.debug_override
    updated_user = UserCRUD.update_debug_override(db, user_id, debug_override)
    
    # Audit log
    AuditLogCRUD.create(
        db,
        user_id=current_user.user_id,
        action="UPDATE",
        target_type="User",
        target_id=user_id,
        details={"field": "debug_override", "old_value": old_value, "new_value": debug_override},
        ip_address=request.client.host if request else None
    )
    
    return updated_user
