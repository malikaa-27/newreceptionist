"""
Pytest configuration: use an in-memory SQLite database for all tests so no
PostgreSQL connection is required.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Patch database before any app module is imported
import app.database as db_module

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Replace the module-level engine/session so imports pick up the test DB
db_module.engine = test_engine
db_module.SessionLocal = TestSessionLocal


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test, drop after."""
    from app.database import Base
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
