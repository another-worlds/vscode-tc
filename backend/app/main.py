# Grand Contract v1.0 — M1/M2/.../M11 Backend entry point
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import auth, workspaces, projects, videos, counting_lines, dashboard, export, audit, internal_videos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: create DB tables (dev mode); shutdown: close engine.
    Production uses Alembic migrations instead of create_all.
    """
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """
    Factory for the FastAPI application.

    Returns:
        Configured FastAPI instance with all routers mounted.

    Invariants:
        - All routes prefixed /v1/
        - CORS restricted to frontend origin in production; open in DEBUG
        - Audit middleware attached to all state-mutating routes
    """
    app = FastAPI(
        title="TrafficCount API",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS configuration (using 2026 best practices: explicit origins)
    cors_origins = ["*"] if settings.DEBUG else ["http://localhost", "https://localhost"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Auth middleware (JWT validation, DEBUG bypass)
    from app.middleware.auth_middleware import AuthMiddleware
    app.add_middleware(AuthMiddleware)
    
    # Mount routers under /v1 prefix
    app.include_router(auth.router, prefix="/v1")
    app.include_router(workspaces.router, prefix="/v1")
    app.include_router(projects.router, prefix="/v1")
    app.include_router(videos.router, prefix="/v1")
    app.include_router(counting_lines.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/v1")
    app.include_router(export.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(internal_videos.router)
    
    # Health check endpoint
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app


app = create_app()
