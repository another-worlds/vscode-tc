# ════════════════════════════════════════════════════════════════════════════════
# IMMUTABLE MODULE v1.0 — Do not modify unless new explicit contract supersedes.
# Pluggable via deterministic interface.
# 
# Module: M1 Auth Service
# Description: OAuth2 (Google + Yandex), JWT, role resolution, DEBUG bypass
# ════════════════════════════════════════════════════════════════════════════════

# Grand Contract v1.0 — M1 Auth Service
# Handles OAuth2 code exchange, JWT issue/validate, debug bypass, role resolution
from __future__ import annotations
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import WorkspaceMember, UserRole
from app.schemas.auth import TokenResponse, CurrentUser
from app.config import settings

# OAuth2 provider configurations
OAUTH_PROVIDERS: dict[str, dict] = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
    "yandex": {
        "auth_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "userinfo_url": "https://login.yandex.ru/info",
        "scopes": ["login:email", "login:info", "login:avatar"],
    },
}


async def get_oauth_redirect_url(provider: str, state: str) -> str:
    """
    Build the OAuth2 authorization redirect URL for the given provider.

    Args:
        provider: 'google' | 'yandex'
        state:    CSRF-safe random state string

    Returns:
        Full authorization URL the user should be redirected to.

    Error modes:
        - ValueError if provider not in OAUTH_PROVIDERS
    """
    if provider not in OAUTH_PROVIDERS:
        raise ValueError(f"Unknown OAuth provider: {provider}")
    
    cfg = OAUTH_PROVIDERS[provider]
    client_id_env = f"{provider.upper()}_CLIENT_ID"
    client_id = getattr(settings, client_id_env, "")
    
    if not client_id:
        raise ValueError(f"{client_id_env} not configured")
    
    scopes_str = "%20".join(cfg["scopes"])
    return (
        f"{cfg['auth_url']}?"
        f"client_id={client_id}&"
        f"redirect_uri={settings.OAUTH_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scopes_str}&"
        f"state={state}"
    )


async def exchange_code_for_user(
    provider: str, code: str, db: AsyncSession
) -> TokenResponse:
    """
    Exchange OAuth2 authorization code for tokens, fetch userinfo,
    upsert User record, issue JWT.

    Args:
        provider: 'google' | 'yandex'
        code:     authorization code from OAuth callback
        db:       async DB session

    Returns:
        TokenResponse with signed JWT access token.

    Side-effects:
        - Upserts User in DB (creates on first login)
        - Sets oauth_provider, oauth_id, email, display_name, avatar_url

    Error modes:
        - HTTPException 400 if code exchange fails
        - HTTPException 502 if userinfo fetch fails
    """
    from fastapi import HTTPException
    import httpx
    
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    cfg = OAUTH_PROVIDERS[provider]
    client_id_env = f"{provider.upper()}_CLIENT_ID"
    client_secret_env = f"{provider.upper()}_CLIENT_SECRET"
    client_id = getattr(settings, client_id_env, "")
    client_secret = getattr(settings, client_secret_env, "")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail=f"{provider} not configured")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        try:
            token_resp = await client.post(
                cfg["token_url"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": settings.OAUTH_REDIRECT_URI,
                },
                timeout=10.0,
            )
            token_resp.raise_for_status()
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="No access_token in response")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")
        
        # Fetch user info
        try:
            userinfo_resp = await client.get(
                cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Userinfo fetch failed: {e}")
    
    # Extract user data (provider-specific keys)
    oauth_id = userinfo.get("sub") or userinfo.get("id") or userinfo.get("uid")
    email = userinfo.get("email") or ""
    display_name = userinfo.get("name") or email.split("@")[0] or "User"
    avatar_url = userinfo.get("picture") or userinfo.get("default_avatar_id")
    
    if not oauth_id or not email:
        raise HTTPException(status_code=502, detail="Missing oauth_id or email in userinfo")
    
    # Upsert user
    user = await upsert_user(provider, str(oauth_id), email, display_name, avatar_url, db)
    
    # Issue JWT
    jwt_token = issue_jwt(user)
    
    return TokenResponse(access_token=jwt_token, expires_in=86400)  # 24h


async def upsert_user(
    provider: str, oauth_id: str, email: str, display_name: str,
    avatar_url: str | None, db: AsyncSession
) -> User:
    """
    Find existing user by (oauth_provider, oauth_id) or create new.

    Invariant: User.email is unique; email change updates the record.
    Side-effects: DB INSERT or UPDATE.
    """
    from sqlalchemy import select, update
    
    # Try to find by oauth_provider + oauth_id (primary match)
    stmt = select(User).where(
        (User.oauth_provider == provider) & (User.oauth_id == oauth_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Update fields if changed (especially email)
        if user.email != email or user.display_name != display_name or user.avatar_url != avatar_url:
            stmt = update(User).where(User.id == user.id).values(
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
            )
            await db.execute(stmt)
            await db.commit()
            # Refresh from DB
            await db.refresh(user)
        return user
    
    # Create new user
    user = User(
        oauth_provider=provider,
        oauth_id=oauth_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def issue_jwt(user: User) -> str:
    """
    Sign a JWT with user.id, email, exp=24h using SECRET_KEY (HS256).

    Returns:
        Signed JWT string.

    Security note (OWASP A02): uses python-jose with HS256;
    production should rotate SECRET_KEY and consider RS256.
    """
    from datetime import datetime, timedelta, timezone
    from jose import jwt as jose_jwt
    
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=24)
    
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    
    token = jose_jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return token


async def get_current_user(token: str, db: AsyncSession) -> CurrentUser:
    """
    FastAPI dependency: validate JWT, load user, attach workspace role if context known.

    In DEBUG=1 mode: returns a synthetic CurrentUser(role=ADMIN) without validating token.

    Args:
        token: Bearer token from Authorization header
        db:    async DB session

    Returns:
        CurrentUser with resolved role.

    Error modes:
        - HTTPException 401 if token invalid/expired (non-DEBUG mode)
    """
    from fastapi import HTTPException
    from jose import jwt as jose_jwt, JWTError
    from sqlalchemy import select
    import uuid as uuid_lib
    
    # DEBUG bypass: synthetic ADMIN user
    if settings.DEBUG:
        return CurrentUser(
            id=uuid_lib.UUID(int=0),
            email="debug@local",
            display_name="Debug User",
            role="ADMIN",
        )
    
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    try:
        payload = jose_jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    
    user_id_str = payload.get("sub")
    email = payload.get("email")
    
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Token missing sub claim")
    
    try:
        user_id = uuid_lib.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")
    
    # Load user from DB
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return CurrentUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role="VIEWER",  # default; can be overridden per workspace
    )


async def resolve_role(user_id: UUID, workspace_id: UUID, db: AsyncSession) -> UserRole:
    """
    Look up the user's role in the given workspace.

    Returns:
        UserRole enum value.

    Error modes:
        - HTTPException 403 if user is not a member of the workspace
    """
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.workspace import WorkspaceMember
    
    stmt = select(WorkspaceMember.role).where(
        (WorkspaceMember.workspace_id == workspace_id)
        & (WorkspaceMember.user_id == user_id)
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=403,
            detail=f"User is not a member of workspace {workspace_id}",
        )
    
    return role


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory: raises 403 if current_user.role not in allowed_roles.

    Usage:
        @router.post("/", dependencies=[Depends(require_role(UserRole.MANAGER))])
    """
    from fastapi import Depends, HTTPException
    
    async def check_role(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role {current_user.role} not authorized. Required: {', '.join(allowed_roles)}",
            )
        return current_user
    
    return Depends(check_role)
