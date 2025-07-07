import pytest
from fastapi import HTTPException
from app.services.user.service import UserService
from app.models.user import UserCreate, UserUpdate, UserRole
from app.schemas.user_schema import UserSchema


class TestUserServiceCreate:
    """Test user creation functionality."""
    
    def test_create_user_success(self, db_session):
        """Test successful user creation."""
        user_data = UserCreate(
            email="newuser@test.com",
            password="password123",
            full_name="New Test User",
            role=UserRole.REPORTER
        )
        
        result = UserService.create_user(db_session, user_data)
        
        assert result.email == "newuser@test.com"
        assert result.full_name == "New Test User"
        assert result.role == UserRole.REPORTER
        assert result.id is not None
        assert result.created_at is not None
    
    def test_create_user_duplicate_email(self, db_session, reporter_user):
        """Test creating user with duplicate email fails."""
        user_data = UserCreate(
            email=reporter_user.email,  # Same email as existing user
            password="password123",
            full_name="Duplicate User",
            role=UserRole.REPORTER
        )
        
        with pytest.raises(HTTPException) as exc_info:
            UserService.create_user(db_session, user_data)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)


class TestUserServiceRead:
    """Test user retrieval functionality."""
    
    def test_get_user_by_id_success(self, db_session, admin_user):
        """Test successful user retrieval by ID."""
        result = UserService.get_user_by_id(db_session, admin_user.id)
        
        assert result is not None
        assert result.id == admin_user.id
        assert result.email == admin_user.email
        assert result.full_name == admin_user.full_name
        assert result.role == admin_user.role
    
    def test_get_user_by_id_not_found(self, db_session):
        """Test user retrieval with non-existent ID."""
        result = UserService.get_user_by_id(db_session, "nonexistent-id")
        
        assert result is None
    
    def test_get_user_by_email_success(self, db_session, maintainer_user):
        """Test successful user retrieval by email."""
        result = UserService.get_user_by_email(db_session, maintainer_user.email)
        
        assert result is not None
        assert result.id == maintainer_user.id
        assert result.email == maintainer_user.email
    
    def test_get_user_by_email_not_found(self, db_session):
        """Test user retrieval with non-existent email."""
        result = UserService.get_user_by_email(db_session, "nonexistent@test.com")
        
        assert result is None
    
    def test_get_all_users(self, db_session, admin_user, maintainer_user, reporter_user):
        """Test retrieving all users with pagination."""
        result = UserService.get_all_users(db_session, skip=0, limit=10)
        
        assert len(result) == 3
        user_emails = [user.email for user in result]
        assert admin_user.email in user_emails
        assert maintainer_user.email in user_emails
        assert reporter_user.email in user_emails
    
    def test_get_all_users_pagination(self, db_session, admin_user, maintainer_user, reporter_user):
        """Test user pagination."""
        # Get first user only
        result = UserService.get_all_users(db_session, skip=0, limit=1)
        
        assert len(result) == 1
        
        # Get second user
        result = UserService.get_all_users(db_session, skip=1, limit=1)
        
        assert len(result) == 1


class TestUserServiceUpdate:
    """Test user update functionality."""
    
    def test_update_user_success(self, db_session, reporter_user):
        """Test successful user update."""
        update_data = UserUpdate(
            full_name="Updated Name",
            role=UserRole.MAINTAINER
        )
        
        result = UserService.update_user(db_session, reporter_user.id, update_data)
        
        assert result is not None
        assert result.full_name == "Updated Name"
        assert result.role == UserRole.MAINTAINER
        assert result.email == reporter_user.email  # Unchanged
    
    def test_update_user_partial(self, db_session, admin_user):
        """Test partial user update (only one field)."""
        original_role = admin_user.role
        update_data = UserUpdate(full_name="New Admin Name")
        
        result = UserService.update_user(db_session, admin_user.id, update_data)
        
        assert result is not None
        assert result.full_name == "New Admin Name"
        assert result.role == original_role  # Unchanged
    
    def test_update_user_not_found(self, db_session):
        """Test updating non-existent user."""
        update_data = UserUpdate(full_name="New Name")
        
        result = UserService.update_user(db_session, "nonexistent-id", update_data)
        
        assert result is None


class TestUserServiceDelete:
    """Test user deletion functionality."""
    
    def test_delete_user_success(self, db_session):
        """Test successful user deletion."""
        # Create a user to delete
        user_data = UserCreate(
            email="todelete@test.com",
            password="password123",
            full_name="To Delete",
            role=UserRole.REPORTER
        )
        created_user = UserService.create_user(db_session, user_data)
        
        # Delete the user
        result = UserService.delete_user(db_session, created_user.id)
        
        assert result is True
        
        # Verify user is deleted
        deleted_user = UserService.get_user_by_id(db_session, created_user.id)
        assert deleted_user is None
    
    def test_delete_user_not_found(self, db_session):
        """Test deleting non-existent user."""
        result = UserService.delete_user(db_session, "nonexistent-id")
        
        assert result is False


class TestUserServiceCount:
    """Test user count functionality."""
    
    def test_get_users_count(self, db_session, admin_user, maintainer_user, reporter_user):
        """Test getting total users count."""
        count = UserService.get_users_count(db_session)
        
        assert count == 3
    
    def test_get_users_count_empty(self, db_session):
        """Test getting count with no users."""
        count = UserService.get_users_count(db_session)
        
        assert count == 0