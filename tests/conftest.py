import pytest
import asyncio
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import your app and dependencies
from app.main import app
from app.databases.postgres import get_db, Base
from app.schemas.user_schema import UserSchema
from app.schemas.issue_schema import IssueSchema
from app.models.user import UserRole
from app.models.issue import IssueSeverity, IssueStatus
from app.utils.auth import create_access_token, hash_password

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_azure_client():
    """Mock Azure blob client to avoid external dependencies."""
    with patch('app.databases.azure_blob.azure_client') as mock:
        mock.upload_file.return_value = "https://fake-storage.blob.core.windows.net/test-file.jpg"
        mock.delete_file.return_value = True
        mock.file_exists.return_value = True
        yield mock

# Test user fixtures
@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    user = UserSchema(
        id="admin-id",
        email="admin@test.com",
        password=hash_password("admin123"),
        full_name="Admin User",
        role=UserRole.ADMIN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def maintainer_user(db_session):
    """Create a maintainer user for testing."""
    user = UserSchema(
        id="maintainer-id",
        email="maintainer@test.com",
        password=hash_password("maintainer123"),
        full_name="Maintainer User",
        role=UserRole.MAINTAINER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def reporter_user(db_session):
    """Create a reporter user for testing."""
    user = UserSchema(
        id="reporter-id",
        email="reporter@test.com",
        password=hash_password("reporter123"),
        full_name="Reporter User",
        role=UserRole.REPORTER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

# Token fixtures
@pytest.fixture
def admin_token(admin_user):
    """Create admin JWT token."""
    return create_access_token({
        "sub": admin_user.id,
        "email": admin_user.email,
        "role": admin_user.role.value
    })

@pytest.fixture
def maintainer_token(maintainer_user):
    """Create maintainer JWT token."""
    return create_access_token({
        "sub": maintainer_user.id,
        "email": maintainer_user.email,
        "role": maintainer_user.role.value
    })

@pytest.fixture
def reporter_token(reporter_user):
    """Create reporter JWT token."""
    return create_access_token({
        "sub": reporter_user.id,
        "email": reporter_user.email,
        "role": reporter_user.role.value
    })

# Sample issue fixture
@pytest.fixture
def sample_issue(db_session, reporter_user):
    """Create a sample issue for testing."""
    issue = IssueSchema(
        id="issue-1",
        title="Test Issue",
        description="This is a test issue",
        severity=IssueSeverity.MEDIUM,
        status=IssueStatus.OPEN,
        created_by=reporter_user.id
    )
    db_session.add(issue)
    db_session.commit()
    db_session.refresh(issue)
    return issue

# Auth header helpers
def auth_headers(token):
    """Helper to create auth headers."""
    return {"Authorization": f"Bearer {token}"}