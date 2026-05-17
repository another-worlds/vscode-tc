# Backend main FastAPI application
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import check_database_health, get_db
from backend.models import HealthStatus, TokenResponse, LoginRequest
from backend.security import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user,
)
from backend.crud import UserCRUD
from backend.routers import workspace, project, user, audit

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI App Initialization
# ============================================================================

app = FastAPI(
    title="Traffic Count MVP Backend",
    description="GPU-accelerated video traffic counting service",
    version="1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ============================================================================
# Register Routers
# ============================================================================

app.include_router(workspace.router)
app.include_router(project.router)
app.include_router(user.router)
app.include_router(audit.router)

# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Audit Logging Middleware
# ============================================================================

@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    """
    Log all non-GET requests for audit trail
    
    Will be extended in Task 5 to write to AuditLog table
    """
    response = await call_next(request)
    
    if request.method != "GET" and settings.debug:
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}"
        )
    
    return response

# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup event: initialize connections and resources"""
    logger.info("Backend service starting up...")
    
    # Check database connection
    if check_database_health():
        logger.info("Database connection established")
    else:
        logger.warning("Database health check failed - proceeding anyway")
    
    # TODO: Connect to Redis queue
    # TODO: Load YOLO model cache
    
    logger.info("Backend service ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event: cleanup resources"""
    logger.info("Backend service shutting down...")
    # TODO: Close database connections
    # TODO: Close Redis connections
    logger.info("Backend service shut down complete")

# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Health check endpoint for load balancers and monitoring
    
    Returns:
        HealthStatus with service and dependency status
    """
    db_ok = check_database_health()
    redis_ok = True  # TODO: Check Redis connection
    
    return HealthStatus(
        status="ok" if db_ok and redis_ok else "degraded",
        database="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
        version="1.0"
    )

# ============================================================================
# Authentication Endpoints (Placeholder - Full Impl in Task 5)
# ============================================================================

@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Login endpoint: authenticate user and return JWT token
    
    Args:
        credentials: username + password
        db: database session
    
    Returns:
        TokenResponse with access_token
    
    Raises:
        HTTPException(401) if invalid credentials
    """
    # Query database for user
    user = UserCRUD.verify_password(db, credentials.username, credentials.password)
    
    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid credentials"},
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": str(user.id),
            "roles": user.roles,
            "debug_override": user.debug_override,
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )

@app.get("/auth/me")
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    Get current user information from JWT token
    
    Returns:
        User information extracted from token
    """
    return {
        "username": current_user.sub,
        "user_id": str(current_user.user_id),
        "roles": current_user.roles,
        "debug_override": current_user.debug_override,
    }

# ============================================================================
# Placeholder Routes (To be Implemented in Tasks 6-8)
# ============================================================================

@app.post("/projects/ingest")
async def ingest_video(current_user = Depends(get_current_user)):
    """Ingest video from Yandex Disk (Task 6)"""
    return {"message": "Video ingest endpoint - Task 6"}

@app.post("/projects/{project_id}/process")
async def enqueue_processing(project_id: str, current_user = Depends(get_current_user)):
    """Enqueue video for processing (Task 7)"""
    return {"message": "Processing enqueue endpoint - Task 7"}

@app.post("/projects/{project_id}/export")
async def export_od_matrix(project_id: str, current_user = Depends(get_current_user)):
    """Export OD matrix to Excel (Task 8)"""
    return {"message": "Export endpoint - Task 8"}

# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Traffic Count MVP Backend",
        "version": "1.0",
        "status": "ok" if check_database_health() else "degraded",
        "docs_url": "/docs" if settings.debug else None,
    }

# ============================================================================
# Error Handlers (Optional, can be extended)
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for logging"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# ============================================================================
# Main Entry Point (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
