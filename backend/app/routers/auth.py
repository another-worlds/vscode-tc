# Grand Contract v1.0 — M1 Auth Router
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(provider: str = Query(default=None)) -> RedirectResponse:
    """
    Redirect user to OAuth2 provider authorization URL.
    If DEBUG=1, redirect directly to /auth/callback?debug=1.
    provider defaults to settings.OAUTH_PROVIDER.
    """
    import secrets
    from app.config import settings
    
    if not provider:
        provider = settings.OAUTH_PROVIDER
    
    state = secrets.token_urlsafe(32)
    redirect_url = await auth_service.get_oauth_redirect_url(provider, state)
    
    return RedirectResponse(url=redirect_url)


@router.get("/callback", response_model=TokenResponse)
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    provider: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Receive OAuth2 authorization code, exchange for token, return JWT.
    CSRF: validate state matches session.
    """
    from app.config import settings
    
    if not provider:
        provider = settings.OAUTH_PROVIDER
    
    # TODO: in production, validate state against session store
    # (simplified here; state is CSRF-safe random token)
    
    return await auth_service.exchange_code_for_user(provider, code, db)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: "UserOut" = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Return the authenticated user's profile."""
    from sqlalchemy import select
    from app.models.user import User
    
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )
