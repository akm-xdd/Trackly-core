import pytest
from unittest.mock import patch, MagicMock
from app.models.user import UserRole


class TestAuthRoutes:
    """Test authentication API endpoints."""
    
    def test_signup_success(self, client, db_session):
        """Test successful user signup."""
        signup_data = {
            "email": "newuser@test.com",
            "password": "password123",
            "full_name": "New Test User",
            "role": "REPORTER"
        }
        
        response = client.post("/api/auth/signup", json=signup_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["full_name"] == "New Test User"
        assert data["user"]["role"] == "REPORTER"
        assert data["tokens"]["access_token"] is not None
        assert data["tokens"]["refresh_token"] is not None
    
    def test_signup_duplicate_email(self, client, db_session, reporter_user):
        """Test signup with duplicate email."""
        signup_data = {
            "email": reporter_user.email,  # Same as existing user
            "password": "password123",
            "full_name": "Duplicate User",
            "role": "REPORTER"
        }
        
        response = client.post("/api/auth/signup", json=signup_data)
        
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()
    
    def test_signup_invalid_data(self, client, db_session):
        """Test signup with invalid data."""
        signup_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "123",  # Too short
            "full_name": "",  # Empty name
            "role": "INVALID_ROLE"
        }
        
        response = client.post("/api/auth/signup", json=signup_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, client, db_session, reporter_user):
        """Test successful login."""
        login_data = {
            "email": reporter_user.email,
            "password": "reporter123"  # Raw password from fixture
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == reporter_user.email
        assert data["user"]["id"] == reporter_user.id
        assert data["tokens"]["access_token"] is not None
    
    def test_login_wrong_email(self, client, db_session):
        """Test login with non-existent email."""
        login_data = {
            "email": "nonexistent@test.com",
            "password": "password123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_wrong_password(self, client, db_session, admin_user):
        """Test login with wrong password."""
        login_data = {
            "email": admin_user.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_missing_fields(self, client, db_session):
        """Test login with missing required fields."""
        # Missing password
        response = client.post("/api/auth/login", json={
            "email": "test@example.com"
        })
        
        assert response.status_code == 422  # Validation error
        
        # Missing email
        response = client.post("/api/auth/login", json={
            "password": "password123"
        })
        
        assert response.status_code == 422


class TestAuthMiddleware:
    """Test authentication middleware and protected endpoints."""
    
    def test_get_current_user_success(self, client, db_session, admin_token):
        """Test getting current user info with valid token."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "role" in data
        assert data["role"] == "ADMIN"
    
    def test_get_current_user_no_token(self, client, db_session):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client, db_session):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_get_current_user_malformed_header(self, client, db_session):
        """Test accessing protected endpoint with malformed auth header."""
        headers = {"Authorization": "InvalidFormat token"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401


class TestRefreshToken:
    """Test refresh token functionality."""
    
    def test_refresh_token_success(self, client, db_session, reporter_user):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = client.post("/api/auth/login", json={
            "email": reporter_user.email,
            "password": "reporter123"
        })
        
        refresh_token = login_response.json()["tokens"]["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client, db_session):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid.refresh.token"}
        
        response = client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401


class TestGoogleOAuth:
    """Test Google OAuth endpoints (mocked)."""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_google_exchange_success(self, mock_get, mock_post, client, db_session):
        """Test successful Google OAuth code exchange."""
        # Mock Google's token response
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "access_token": "google_access_token"
        }
        
        # Mock Google's user info response
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            "email": "googleuser@gmail.com",
            "name": "Google User"
        }
        
        response = client.post("/api/auth/google/exchange", json={
            "code": "google_auth_code"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "googleuser@gmail.com"
        assert data["name"] == "Google User"
    
    @patch('requests.post')
    def test_google_exchange_invalid_code(self, mock_post, client, db_session):
        """Test Google OAuth with invalid code."""
        # Mock Google's error response
        mock_post.return_value.ok = False
        mock_post.return_value.text = "Invalid authorization code"
        
        response = client.post("/api/auth/google/exchange", json={
            "code": "invalid_code"
        })
        
        assert response.status_code == 400
    
    def test_google_login_success(self, client, db_session, admin_user):
        """Test Google OAuth login with existing user."""
        google_data = {
            "email": admin_user.email,  # User exists in DB
            "name": "Updated Google Name"
        }
        
        response = client.post("/api/auth/google", json=google_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == admin_user.email
        assert data["tokens"]["access_token"] is not None
    
    def test_google_login_user_not_found(self, client, db_session):
        """Test Google OAuth login with non-existent user."""
        google_data = {
            "email": "nonexistent@gmail.com",
            "name": "New User"
        }
        
        response = client.post("/api/auth/google", json=google_data)
        
        assert response.status_code == 401
        assert "not found" in response.json()["detail"].lower()


class TestAuthTestEndpoints:
    """Test role-based test endpoints."""
    
    def test_admin_access_success(self, client, db_session, admin_token):
        """Test admin test endpoint with admin token."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/auth/test/admin", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "ADMIN" in data["message"]
        assert data["role"] == "ADMIN"
    
    def test_admin_access_denied(self, client, db_session, reporter_token):
        """Test admin test endpoint with reporter token."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get("/api/auth/test/admin", headers=headers)
        
        assert response.status_code == 403
    
    def test_maintainer_access_success(self, client, db_session, maintainer_token):
        """Test maintainer test endpoint with maintainer token."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        response = client.get("/api/auth/test/maintainer", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "MAINTAINER" in data["message"]
    
    def test_maintainer_access_with_admin(self, client, db_session, admin_token):
        """Test maintainer test endpoint with admin token (should work)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/auth/test/maintainer", headers=headers)
        
        assert response.status_code == 200
    
    def test_any_access_success(self, client, db_session, reporter_token):
        """Test any user test endpoint with any valid token."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get("/api/auth/test/any", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "role" in data


class TestLogout:
    """Test logout endpoint."""
    
    def test_logout_success(self, client, db_session):
        """Test logout endpoint (stateless - always succeeds)."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data["message"].lower()