import pytest
from datetime import datetime, timedelta
from app.utils.auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_token
)
from app.services.auth.service import AuthService
from app.models.auth import LoginRequest, SignupRequest


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "test123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "test123"
        wrong_password = "wrong123"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWTTokens:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token, token_type="access")
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_wrong_token_type(self):
        """Test verifying token with wrong type."""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        
        # Try to verify as refresh token
        payload = verify_token(access_token, token_type="refresh")
        
        assert payload is None


class TestAuthService:
    """Test authentication service methods."""
    
    def test_signup_success(self, db_session):
        """Test successful user signup."""
        signup_data = SignupRequest(
            email="newuser@test.com",
            password="password123",
            full_name="New User",
            role="REPORTER"
        )
        
        result = AuthService.signup(db_session, signup_data)
        
        assert result.user.email == "newuser@test.com"
        assert result.user.full_name == "New User"
        assert result.tokens.access_token is not None
        assert result.tokens.refresh_token is not None
    
    def test_login_success(self, db_session, reporter_user):
        """Test successful login."""
        login_data = LoginRequest(
            email=reporter_user.email,
            password="reporter123"  # Raw password from fixture
        )
        
        result = AuthService.login(db_session, login_data)
        
        assert result.user.id == reporter_user.id
        assert result.user.email == reporter_user.email
        assert result.tokens.access_token is not None
    
    def test_login_wrong_email(self, db_session):
        """Test login with wrong email."""
        login_data = LoginRequest(
            email="nonexistent@test.com",
            password="password123"
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            AuthService.login(db_session, login_data)
    
    def test_get_current_user_success(self, db_session, admin_user):
        """Test getting current user by ID."""
        user = AuthService.get_current_user(db_session, admin_user.id)
        
        assert user is not None
        assert user.id == admin_user.id
        assert user.email == admin_user.email
    
    def test_get_current_user_not_found(self, db_session):
        """Test getting non-existent user."""
        user = AuthService.get_current_user(db_session, "nonexistent-id")
        
        assert user is None