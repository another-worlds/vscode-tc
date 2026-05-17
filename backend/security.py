# Security: JWT token generation, validation, and RBAC
import os
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.models import TokenData
from backend.config import settings

# ============================================================================
# Password Hashing
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

# ============================================================================
# OAuth2 & JWT Token Handling
# ============================================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Claims to encode (sub=username, user_id, roles, debug_override)
        expires_delta: Token expiration time (default from settings)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """
    Verify JWT token and extract claims
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData with claims
    
    Raises:
        HTTPException if token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        roles: list = payload.get("roles", [])
        debug_override: bool = payload.get("debug_override", False)
        
        if username is None or user_id is None:
            raise credentials_exception
        
        token_data = TokenData(
            sub=username,
            user_id=UUID(user_id),
            roles=roles,
            debug_override=debug_override
        )
        
    except JWTError:
        raise credentials_exception
    
    return token_data

# ============================================================================
# Dependency Injection: Current User
# ============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Get current user from JWT token (dependency)
    
    Args:
        token: JWT token from Authorization header
    
    Returns:
        TokenData with user info and roles
    
    Raises:
        HTTPException (401) if token invalid
    """
    return verify_token(token)

# ============================================================================
# RBAC: Role-Based Access Control
# ============================================================================

def check_debug_mode() -> bool:
    """
    Check if DEBUG mode is enabled (bypasses all RBAC)
    
    Returns:
        True if DEBUG=1 in environment
    """
    return os.environ.get("DEBUG") == "1"

def get_effective_roles(token_data: TokenData) -> List[str]:
    """
    Get effective roles for user, considering DEBUG mode
    
    If DEBUG=1, grants all roles: ["pm", "analyst", "admin"]
    Else: returns token_data.roles
    
    Args:
        token_data: TokenData from JWT
    
    Returns:
        List of effective roles
    """
    if check_debug_mode():
        return ["pm", "analyst", "admin"]
    
    return token_data.roles

def require_role(required_roles: List[str]):
    """
    RBAC dependency factory: requires at least one role
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            current_user: TokenData = Depends(get_current_user),
            _ = Depends(require_role(["admin"]))
        ):
            ...
    
    Args:
        required_roles: List of roles that satisfy the requirement (OR logic)
    
    Returns:
        Async dependency function
    """
    async def check_role(
        current_user: TokenData = Depends(get_current_user)
    ) -> None:
        # If DEBUG mode, allow all
        if check_debug_mode():
            return
        
        # Check if user has at least one required role
        effective_roles = get_effective_roles(current_user)
        
        if not any(role in effective_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
    
    return check_role

def require_all_roles(required_roles: List[str]):
    """
    RBAC dependency factory: requires all roles (AND logic)
    
    Args:
        required_roles: List of roles all required
    
    Returns:
        Async dependency function
    """
    async def check_role(
        current_user: TokenData = Depends(get_current_user)
    ) -> None:
        # If DEBUG mode, allow all
        if check_debug_mode():
            return
        
        effective_roles = get_effective_roles(current_user)
        
        if not all(role in effective_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {required_roles}"
            )
    
    return check_role

# ============================================================================
# Common Role Checks (Pre-defined Dependencies)
# ============================================================================

require_admin = require_role(["admin"])
require_pm_or_admin = require_role(["pm", "admin"])
require_analyst = require_role(["analyst", "pm", "admin"])
