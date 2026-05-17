# Database configuration and connection
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends

from backend.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Database Engine & Session Setup
# ============================================================================

# Create SQLAlchemy engine
engine = create_engine(
    settings.db_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connection before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================================================
# Dependency: Get Database Session
# ============================================================================

def get_db() -> Session:
    """
    Database session dependency for FastAPI routes
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Connection Event Listeners (Optional, for debugging)
# ============================================================================

@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when connection is established"""
    if settings.debug:
        logger.debug("Database connection established")

@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log when connection is closed"""
    if settings.debug:
        logger.debug("Database connection closed")

# ============================================================================
# Health Check
# ============================================================================

def check_database_health() -> bool:
    """
    Check if database is accessible
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
