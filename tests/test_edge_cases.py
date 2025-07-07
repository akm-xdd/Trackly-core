import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.services.user.service import UserService
from app.services.issues.service import IssueService
from app.models.user import UserCreate, UserUpdate
from app.models.issue import IssueCreate, IssueUpdate, IssueSeverity


class TestServiceErrorHandling:
    """Test service layer error handling."""
    
    def test_user_service_create_database_error(self, db_session):
        """Test user creation with database error."""
        user_data = UserCreate(
            email="error@test.com",
            password="password123",
            full_name="Error User",
            role="REPORTER"
        )
        
        # Mock db.commit to raise an exception
        with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
            with pytest.raises(HTTPException) as exc_info:
                UserService.create_user(db_session, user_data)
            
            assert exc_info.value.status_code == 500
    
    def test_user_service_update_database_error(self, db_session, reporter_user):
        """Test user update with database error."""
        update_data = UserUpdate(full_name="New Name")
        
        with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
            with pytest.raises(HTTPException) as exc_info:
                UserService.update_user(db_session, reporter_user.id, update_data)
            
            assert exc_info.value.status_code == 500
    
    def test_user_service_delete_database_error(self, db_session, reporter_user):
        """Test user deletion with database error."""
        with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
            with pytest.raises(HTTPException) as exc_info:
                UserService.delete_user(db_session, reporter_user.id)
            
            assert exc_info.value.status_code == 500


class TestPasswordEdgeCases:
    """Test password handling edge cases."""
    
    def test_hash_empty_password(self):
        """Test hashing empty password."""
        from app.utils.auth import hash_password
        
        hashed = hash_password("")
        assert hashed != ""
        assert len(hashed) > 20
    
    def test_hash_unicode_password(self):
        """Test hashing unicode password."""
        from app.utils.auth import hash_password, verify_password
        
        unicode_password = "密码123!@#"
        hashed = hash_password(unicode_password)
        
        assert verify_password(unicode_password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_verify_password_empty_hash(self):
        """Test verifying password against empty hash."""
        from app.utils.auth import verify_password
        from passlib.exc import UnknownHashError

        with pytest.raises(UnknownHashError):
            verify_password("password", "")


class TestTokenEdgeCases:
    """Test JWT token edge cases."""
    
    def test_verify_token_malformed_payload(self):
        """Test verifying token with malformed payload."""
        from app.utils.auth import verify_token
        
        # Create a token-like string that will fail JSON parsing
        malformed_token = "eyJ.malformed.token"
        
        result = verify_token(malformed_token)
        assert result is None
    
    def test_create_token_empty_data(self):
        """Test creating token with empty data."""
        from app.utils.auth import create_access_token
        
        token = create_access_token({})
        assert isinstance(token, str)
        assert len(token) > 20
    
    def test_verify_token_missing_required_fields(self):
        """Test token missing required type field."""
        from app.utils.auth import create_access_token, verify_token
        from jose import jwt
        import os
        
        # Create token without 'type' field
        data = {"sub": "user123"}
        token_without_type = jwt.encode(data, os.getenv("JWT_SECRET_KEY", "test-key"), algorithm="HS256")
        
        result = verify_token(token_without_type)
        assert result is None


class TestModelValidation:
    """Test model validation edge cases."""
    
    def test_user_create_minimal_data(self):
        """Test creating user with minimal required data."""
        from app.models.user import UserCreate, UserRole
        
        user_data = UserCreate(
            email="minimal@test.com",
            password="pass",
            full_name="Min",
            role=UserRole.REPORTER
        )
        
        assert user_data.email == "minimal@test.com"
        assert user_data.role == UserRole.REPORTER
    
    def test_issue_create_with_all_fields(self):
        """Test creating issue with all possible fields."""
        issue_data = IssueCreate(
            title="Complete Issue",
            description="Full description here",
            severity=IssueSeverity.CRITICAL,
            file_url="https://example.com/file.jpg"
        )
        
        assert issue_data.title == "Complete Issue"
        assert issue_data.severity == IssueSeverity.CRITICAL
        assert issue_data.file_url == "https://example.com/file.jpg"
    
    def test_issue_update_empty_fields(self):
        """Test issue update with no fields specified."""
        update_data = IssueUpdate()
        
        # All fields should be None (optional)
        assert update_data.title is None
        assert update_data.description is None
        assert update_data.severity is None
        assert update_data.status is None


class TestAPIResponseFormats:
    """Test API response format edge cases."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "features" in data
    
    def test_invalid_endpoint(self, client):
        """Test accessing non-existent endpoint."""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test using wrong HTTP method."""
        # Try PATCH on endpoint that only accepts GET/POST
        response = client.patch("/api/auth/login")
        
        assert response.status_code == 405


class TestDatabaseQueries:
    """Test database query edge cases."""
    
    def test_get_users_with_zero_limit(self, db_session):
        """Test getting users with limit 0."""
        result = UserService.get_all_users(db_session, skip=0, limit=0)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_users_with_high_skip(self, db_session):
        """Test getting users with skip higher than total count."""
        result = UserService.get_all_users(db_session, skip=1000, limit=10)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_issues_count_edge_cases(self, db_session):
        """Test issue count with different parameters."""
        # Test with None user_role
        count1 = IssueService.get_issues_count(db_session, user_role=None)
        assert isinstance(count1, int)
        
        # Test with empty user_id
        count2 = IssueService.get_issues_count(db_session, user_id="", user_role="ADMIN")
        assert isinstance(count2, int)


class TestValidationErrors:
    """Test validation error responses."""
    
    def test_login_with_invalid_email_format(self, client):
        """Test login with malformed email."""
        response = client.post("/api/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        
        assert response.status_code == 422
    
    def test_create_issue_with_empty_title(self, client, reporter_token):
        """Test creating issue with empty title."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.post("/api/issues/", json={
            "title": "",  # Empty title
            "description": "Valid description",
            "severity": "MEDIUM"
        }, headers=headers)
        
        assert response.status_code == 422
    
    def test_create_user_with_invalid_role(self, client, admin_token):
        """Test creating user with invalid role."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.post("/api/users/", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "role": "INVALID_ROLE"
        }, headers=headers)
        
        assert response.status_code == 422