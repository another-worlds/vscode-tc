# Module Contract A: Workspace & Project Management + RBAC + Logging
**Contract ID:** MOD-A-RBAC-v1.0  
**Status:** Immutable on green (Phase 2, Task 5)  
**Scope:** FastAPI routers for workspace/project CRUD, dashboard metrics, line config, audit logging, JWT + role-based access control

## Data Model (Pydantic + SQLModel)

```python
# Workspace - top-level organizational unit
Workspace(
    id: UUID,
    name: str,
    owner_id: UUID (FK: User.id),
    storage_quota_gb: float,
    created_at: datetime,
    updated_at: datetime
)

# Project - individual video processing task
Project(
    id: UUID,
    workspace_id: UUID (FK: Workspace.id),
    name: str,
    video_path: str,
    resolution: str,  # e.g., "1920x1080"
    duration_sec: int,
    status: Enum[uploaded | processing | done | failed],
    line_config: JSON,  # React-generated line data
    od_matrix: JSON,  # Aggregated OD matrix result
    created_at: datetime,
    updated_at: datetime
)

# User - authentication & authorization
User(
    id: UUID,
    username: str (unique),
    email: str (unique),
    hashed_password: str,
    roles: List[str],  # ["pm", "analyst", "admin"]
    debug_override: bool,  # DEBUG mode flag
    is_active: bool,
    created_at: datetime
)

# AuditLog - all mutations logged
AuditLog(
    id: UUID,
    user_id: UUID (FK: User.id),
    action: str,  # "CREATE", "UPDATE", "DELETE", "EXPORT"
    target_id: UUID,  # project_id or workspace_id
    target_type: str,  # "Project", "Workspace"
    details: JSON,  # Additional context (e.g., old_value, new_value)
    timestamp: datetime,
    ip_address: str (optional)
)
```

## REST Interfaces (FastAPI Routers)

### Workspace CRUD (RBAC: pm/admin)
- `POST /workspaces` – Create workspace (owner_id from JWT)
- `GET /workspaces` – List user's workspaces
- `GET /workspaces/{id}` – Get workspace details + usage stats
- `PATCH /workspaces/{id}` – Update quota, name (admin only)
- `DELETE /workspaces/{id}` – Delete workspace (cascade: projects & jobs)

### Project CRUD (RBAC: pm/analyst/admin)
- `POST /workspaces/{id}/projects` – Create project (upload video)
- `GET /workspaces/{id}/projects` – List projects in workspace
- `GET /projects/{id}` – Get project details + status
- `GET /projects/{id}/dashboard` – Metrics dashboard
  - Returns: `total_duration_min`, `storage_used_gb`, `processed_gb`, `status`, `current_job_progress`
- `PATCH /projects/{id}` – Update project name, storage quota
- `POST /projects/{id}/lines` – Save line config from React component
  ```json
  {
    "lines": [
      {"id": "line-1", "points": [[x1, y1], [x2, y2]], "name": "Entry Zone"}
    ]
  }
  ```
- `DELETE /projects/{id}` – Delete project (cascade: jobs, Parquet files)

### Export & Analytics (RBAC: analyst/admin)
- `POST /projects/{id}/export` – Trigger Excel OD matrix export
  - Reads Parquet → aggregates OD matrix → openpyxl → download
- `GET /projects/{id}/analytics` – Return aggregated statistics (JSON)

### User & RBAC (RBAC: admin only)
- `POST /users` – Create user (admin only)
- `GET /users` – List users (admin only)
- `PATCH /users/{id}` – Update roles, debug_override (admin only)
- `POST /auth/login` – JWT token generation
  ```json
  {
    "username": "user1",
    "password": "***"
  }
  ```
  Returns: `{"access_token": "...", "token_type": "bearer"}`

### Audit Log (RBAC: admin only)
- `GET /audit-logs` – List audit logs with filters (user_id, action, date range)
- `GET /audit-logs/{id}` – Get single audit entry

## Authentication & Authorization

### JWT Setup (FastAPI)
- Secret key: `$SECRET_KEY` (env var)
- Algorithm: HS256 (configurable)
- Expiration: `$ACCESS_TOKEN_EXPIRE_MINUTES` (env var, default 30)
- Claims: `sub` (username), `roles`, `user_id`, `debug_override`

### RoleChecker Dependency
```python
def role_required(required_roles: List[str]):
    async def check_role(token: str = Depends(oauth2_scheme)):
        # 1. Decode JWT
        # 2. If DEBUG=1 and claims["debug_override"]=true → grant all (roles = ["admin"])
        # 3. Else: verify token claims["roles"] intersect with required_roles
        # 4. If mismatch → raise HTTPException(403, "Insufficient permissions")
    return check_role
```

### DEBUG=1 Bypass
- Environment variable `DEBUG=1` in backend container
- If set: All endpoints grant full access (no role check)
- Logged: Action tagged with `debug_mode=true` in AuditLog

## Invariants

1. **All mutations via Backend only** – No direct SQL writes; only ORM + validated logic
2. **DEBUG=1 sets roles = ["admin"] for all requests** – If `os.environ.get("DEBUG") == "1"`, override JWT roles
3. **Every action → AuditLog** – Middleware or decorator logs all non-GET endpoints
4. **Transactional CRUD** – Use SQLAlchemy sessions + rollback on error
5. **Foreign key constraints** – Postgres enforces referential integrity (ON DELETE CASCADE for projects when workspace deleted)
6. **Immutable audit logs** – AuditLog records never updated, only inserted

## Best Practices

- FastAPI RoleChecker dependency + JWT claims (FastAPI Security)
- Pydantic models for request/response validation
- SQLModel for ORM (hybrid SQL + Pydantic)
- Logging via Python `logging` module + FastAPI middleware
- Password hashing: bcrypt (passlib)
- CORS + HTTPS headers (production-grade)

## Implementation Scope (Task 5, One-Shot)

- Database models (SQLModel)
- All 15+ endpoints listed above
- JWT setup + RoleChecker dependency
- Audit logging middleware
- Error handling (400, 403, 404, 500)
- Unit tests for RBAC (test_workspace.py, test_rbac.py)
- <400 LOC per file

## Success Criteria

- [x] All endpoints respond 200 (valid JWT + sufficient roles)
- [x] All endpoints respond 403 (invalid JWT or insufficient roles)
- [x] AuditLog entries created for all mutations
- [x] DEBUG=1 allows all actions
- [x] Role inheritance: admin > pm > analyst (if needed)
- [x] Database cascade deletes work (delete workspace → delete projects)

---

**References:** [MASTER.md](MASTER.md)  
**Version:** 1.0 (immutable)
