# Audit log router
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.security import get_current_user, require_admin
from backend.models import TokenData, AuditLogEntry, AuditLogFilter
from backend.crud import AuditLogCRUD
from backend.db_models import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"])

# ============================================================================
# Audit Log Endpoints (Admin Only)
# ============================================================================

@router.get("", response_model=List[AuditLogEntry])
async def list_audit_logs(
    user_id: str = None,
    action: str = None,
    target_type: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    List audit logs with optional filters
    
    Query Parameters:
    - user_id: Filter by user UUID
    - action: Filter by action (CREATE, UPDATE, DELETE, EXPORT)
    - target_type: Filter by target type (Project, Workspace, User, Job)
    - skip: Pagination offset
    - limit: Max results (default 100, max 1000)
    
    RBAC: admin only
    """
    filter_params = AuditLogFilter(
        user_id=user_id,
        action=action,
        target_type=target_type,
        skip=skip,
        limit=min(limit, 1000)
    )
    
    logs = AuditLogCRUD.list_filtered(db, filter_params)
    return logs

@router.get("/{log_id}", response_model=AuditLogEntry)
async def get_audit_log(
    log_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    Get a single audit log entry
    
    RBAC: admin only
    """
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    
    return log
