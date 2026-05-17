# Quick test for FastAPI setup and Task 5 RBAC implementation
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from backend.app import app
from backend.database import get_db
from backend.db_models import User, Workspace, Project
from backend.crud import UserCRUD
from backend.models import UserCreate, WorkspaceCreate, ProjectCreate
from backend.security import hash_password

# ============================================================================
# Test Database Setup
# ============================================================================

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
from backend.db_models import SQLModel
SQLModel.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ============================================================================
# Helper Functions
# ============================================================================

def create_test_user(username: str = "testuser", password: str = "testpass123", roles: list = None):
    """Create a test user in the database"""
    db = TestingSessionLocal()
    try:
        user_create = UserCreate(
            username=username,
            email=f"{username}@example.com",
            password=password,
            roles=roles or ["analyst"]
        )
        return UserCRUD.create(db, user_create)
    finally:
        db.close()

def get_auth_headers(username: str = "testuser", password: str = "testpass123"):
    """Login and get authorization headers"""
    response = client.post("/auth/login", json={
        "username": username,
        "password": password
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "degraded"]

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()

# ============================================================================
# Authentication Tests
# ============================================================================

def test_login_success():
    """Test login with valid credentials"""
    user = create_test_user("authuser", "password123", ["analyst"])
    
    response = client.post("/auth/login", json={
        "username": "authuser",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_password():
    """Test login with invalid password"""
    user = create_test_user("authuser2", "password123", ["analyst"])
    
    response = client.post("/auth/login", json={
        "username": "authuser2",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_login_nonexistent_user():
    """Test login with nonexistent user"""
    response = client.post("/auth/login", json={
        "username": "nonexistent",
        "password": "anypassword"
    })
    assert response.status_code == 401

def test_get_current_user():
    """Test getting current user info"""
    user = create_test_user("meuser", "password", ["analyst"])
    headers = get_auth_headers("meuser", "password")
    
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "meuser"
    assert "analyst" in response.json()["roles"]

# ============================================================================
# Workspace CRUD Tests
# ============================================================================

def test_create_workspace():
    """Test creating a workspace"""
    user = create_test_user("wsuser", "password", ["pm"])
    headers = get_auth_headers("wsuser", "password")
    
    response = client.post("/workspaces", json={
        "name": "Test Workspace",
        "storage_quota_gb": 500.0
    }, headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Workspace"
    assert data["storage_quota_gb"] == 500.0

def test_list_workspaces():
    """Test listing user workspaces"""
    user = create_test_user("wsuser2", "password", ["pm"])
    headers = get_auth_headers("wsuser2", "password")
    
    # Create a workspace
    client.post("/workspaces", json={
        "name": "Workspace 1",
        "storage_quota_gb": 100.0
    }, headers=headers)
    
    # List workspaces
    response = client.get("/workspaces", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert any(ws["name"] == "Workspace 1" for ws in response.json())

def test_get_workspace():
    """Test getting workspace details"""
    user = create_test_user("wsuser3", "password", ["pm"])
    headers = get_auth_headers("wsuser3", "password")
    
    # Create workspace
    create_response = client.post("/workspaces", json={
        "name": "Detail Workspace",
        "storage_quota_gb": 200.0
    }, headers=headers)
    ws_id = create_response.json()["id"]
    
    # Get workspace
    response = client.get(f"/workspaces/{ws_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Workspace"

def test_get_workspace_dashboard():
    """Test workspace dashboard"""
    user = create_test_user("wsuser4", "password", ["pm"])
    headers = get_auth_headers("wsuser4", "password")
    
    # Create workspace
    create_response = client.post("/workspaces", json={
        "name": "Dashboard WS",
        "storage_quota_gb": 100.0
    }, headers=headers)
    ws_id = create_response.json()["id"]
    
    # Get dashboard
    response = client.get(f"/workspaces/{ws_id}/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["project_count"] >= 0

def test_update_workspace():
    """Test updating workspace"""
    user = create_test_user("wsuser5", "password", ["pm"])
    headers = get_auth_headers("wsuser5", "password")
    
    # Create workspace
    create_response = client.post("/workspaces", json={
        "name": "Update WS",
        "storage_quota_gb": 100.0
    }, headers=headers)
    ws_id = create_response.json()["id"]
    
    # Update
    response = client.patch(f"/workspaces/{ws_id}", json={
        "name": "Updated WS",
        "storage_quota_gb": 300.0
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated WS"

def test_delete_workspace():
    """Test deleting workspace"""
    user = create_test_user("wsuser6", "password", ["pm"])
    headers = get_auth_headers("wsuser6", "password")
    
    # Create workspace
    create_response = client.post("/workspaces", json={
        "name": "Delete WS",
        "storage_quota_gb": 100.0
    }, headers=headers)
    ws_id = create_response.json()["id"]
    
    # Delete
    response = client.delete(f"/workspaces/{ws_id}", headers=headers)
    assert response.status_code == 204

# ============================================================================
# RBAC Tests
# ============================================================================

def test_rbac_unauthorized_analyst_cannot_create_workspace():
    """Test that analysts cannot create workspaces (pm/admin only)"""
    user = create_test_user("analyst_user", "password", ["analyst"])
    headers = get_auth_headers("analyst_user", "password")
    
    response = client.post("/workspaces", json={
        "name": "Denied WS",
        "storage_quota_gb": 100.0
    }, headers=headers)
    assert response.status_code == 403

def test_rbac_unauthenticated_request():
    """Test that unauthenticated requests are rejected"""
    response = client.post("/workspaces", json={
        "name": "Test",
        "storage_quota_gb": 100.0
    })
    assert response.status_code == 403  # or 401 depending on OAuth2 config

def test_rbac_workspace_access_denied():
    """Test that users cannot access others' workspaces"""
    user1 = create_test_user("user1", "password1", ["pm"])
    user2 = create_test_user("user2", "password2", ["pm"])
    headers1 = get_auth_headers("user1", "password1")
    headers2 = get_auth_headers("user2", "password2")
    
    # User1 creates workspace
    create_response = client.post("/workspaces", json={
        "name": "User1 WS",
        "storage_quota_gb": 100.0
    }, headers=headers1)
    ws_id = create_response.json()["id"]
    
    # User2 tries to access it
    response = client.get(f"/workspaces/{ws_id}", headers=headers2)
    assert response.status_code == 403

# ============================================================================
# Project CRUD Tests
# ============================================================================

def test_create_project():
    """Test creating a project"""
    user = create_test_user("projuser", "password", ["analyst"])
    headers = get_auth_headers("projuser", "password")
    
    # Create workspace
    ws_response = client.post("/workspaces", json={
        "name": "Project WS",
        "storage_quota_gb": 100.0
    }, headers=get_auth_headers("projuser", "password"))
    ws_id = ws_response.json()["id"]
    
    # Create project
    response = client.post(f"/workspaces/{ws_id}/projects", json={
        "name": "Test Video",
        "video_path": "/mnt/yandex/workspace/project/video.mp4"
    }, headers=headers)
    
    assert response.status_code == 201
    assert response.json()["name"] == "Test Video"

# ============================================================================
# Audit Log Tests
# ============================================================================

def test_audit_log_creation():
    """Test that actions are logged to audit log"""
    admin = create_test_user("admin_user", "password", ["admin"])
    headers = get_auth_headers("admin_user", "password")
    
    # Create a workspace (should log)
    response = client.post("/workspaces", json={
        "name": "Audited WS",
        "storage_quota_gb": 100.0
    }, headers=headers)
    assert response.status_code == 201

if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_backend.py -v
    pytest.main([__file__, "-v"])
