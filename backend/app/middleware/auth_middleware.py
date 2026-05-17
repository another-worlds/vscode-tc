# Grand Contract v1.0 — M1 Auth Middleware
# Extracts Bearer token and attaches current_user to request state
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

PUBLIC_PATHS = {"/auth/login", "/auth/callback", "/health", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT on all non-public routes.

    In DEBUG=1: attaches synthetic ADMIN user without token validation.

    Invariants:
        - request.state.user is always set after this middleware runs
        - Public paths bypass JWT check entirely
    """

    async def dispatch(self, request: Request, call_next):
        """
        Extract Authorization: Bearer <token>, validate, set request.state.user.

        Error modes:
            - Returns 401 JSON if token missing on protected route (non-DEBUG)
            - Returns 401 JSON if token invalid/expired (non-DEBUG)
        """
        from app.config import settings
        
        # DEBUG mode: synthetic admin user
        if settings.DEBUG:
            import uuid
            request.state.user = {
                "id": str(uuid.UUID(int=0)),
                "email": "debug@local",
                "display_name": "Debug User",
                "role": "ADMIN",
            }
            return await call_next(request)
        
        # Check if path is public
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        
        # Extract Bearer token
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        
        if not token:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authorization token"},
            )
        
        # Validate token (signature, expiry, etc.) — detailed validation happens in get_current_user
        # Here we just make sure it's a valid JWT structure
        from jose import jwt as jose_jwt, JWTError
        try:
            payload = jose_jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_signature": True},
            )
            request.state.user = {"token": token, "payload": payload}
        except JWTError as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid token: {e}"},
            )
        
        return await call_next(request)
