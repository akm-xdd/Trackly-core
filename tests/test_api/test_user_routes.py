import pytest
from app.models.user import UserRole


class TestUserRoutesCRUD:
    """Test user CRUD operations via API."""
    
    def test_create_user_admin_success(self, client, db_session, admin_token):
        """Test admin can create users."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        user_data = {
            "email": "newadmin@test.com",
            "password": "password123",
            "full_name": "New Admin User",
            "role": "ADMIN"
        }
        
        response = client.post("/api/users/", json=user_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newadmin@test.com"
        assert data["full_name"] == "New Admin User"
        assert data["role"] == "ADMIN"
        assert "id" in data
    
    def test_create_user_non_admin_forbidden(self, client, db_session, reporter_token):
        """Test non-admin cannot create users."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        user_data = {
            "email": "unauthorized@test.com",
            "password": "password123",
            "full_name": "Unauthorized User",
            "role": "REPORTER"
        }
        
        response = client.post("/api/users/", json=user_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_create_user_duplicate_email(self, client, db_session, admin_token, reporter_user):
        """Test creating user with duplicate email."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        user_data = {
            "email": reporter_user.email,  # Duplicate
            "password": "password123",
            "full_name": "Duplicate User",
            "role": "REPORTER"
        }
        
        response = client.post("/api/users/", json=user_data, headers=headers)
        
        assert response.status_code == 400
    
    def test_get_all_users_admin(self, client, db_session, admin_token, reporter_user, maintainer_user):
        """Test admin can get all users."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/users/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least admin, reporter, maintainer
    
    def test_get_all_users_pagination(self, client, db_session, admin_token):
        """Test user pagination."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/users/?skip=0&limit=2", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
    
    def test_get_all_users_non_admin_forbidden(self, client, db_session, maintainer_token):
        """Test non-admin cannot get all users."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        response = client.get("/api/users/", headers=headers)
        
        assert response.status_code == 403
    
    def test_get_user_by_id_self(self, client, db_session, reporter_user, reporter_token):
        """Test user can get their own info."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get(f"/api/users/{reporter_user.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == reporter_user.id
        assert data["email"] == reporter_user.email
    
    def test_get_user_by_id_admin(self, client, db_session, reporter_user, admin_token):
        """Test admin can get any user info."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get(f"/api/users/{reporter_user.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == reporter_user.id
    
    def test_get_user_by_id_forbidden(self, client, db_session, admin_user, reporter_token):
        """Test user cannot get other user's info."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get(f"/api/users/{admin_user.id}", headers=headers)
        
        assert response.status_code == 403
    
    def test_get_user_by_id_not_found(self, client, db_session, admin_token):
        """Test getting non-existent user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/users/nonexistent-id", headers=headers)
        
        assert response.status_code == 404
    
    def test_update_user_self(self, client, db_session, reporter_user, reporter_token):
        """Test user can update their own info."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        update_data = {
            "full_name": "Updated Reporter Name"
        }
        
        response = client.put(f"/api/users/{reporter_user.id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Reporter Name"
    
    def test_update_user_admin(self, client, db_session, reporter_user, admin_token):
        """Test admin can update any user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        update_data = {
            "full_name": "Admin Updated Name",
            "role": "MAINTAINER"
        }
        
        response = client.put(f"/api/users/{reporter_user.id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Admin Updated Name"
        assert data["role"] == "MAINTAINER"
    
    def test_update_user_forbidden(self, client, db_session, admin_user, reporter_token):
        """Test user cannot update other users."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        update_data = {
            "full_name": "Unauthorized Update"
        }
        
        response = client.put(f"/api/users/{admin_user.id}", json=update_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_update_user_not_found(self, client, db_session, admin_token):
        """Test updating non-existent user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        update_data = {
            "full_name": "Does Not Exist"
        }
        
        response = client.put("/api/users/nonexistent-id", json=update_data, headers=headers)
        
        assert response.status_code == 404
    
    def test_delete_user_admin(self, client, db_session, admin_token):
        """Test admin can delete users."""
        # Create user to delete
        headers = {"Authorization": f"Bearer {admin_token}"}
        user_data = {
            "email": "todelete@test.com",
            "password": "password123",
            "full_name": "To Delete",
            "role": "REPORTER"
        }
        
        create_response = client.post("/api/users/", json=user_data, headers=headers)
        created_user = create_response.json()
        
        # Delete the user
        response = client.delete(f"/api/users/{created_user['id']}", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_delete_user_non_admin_forbidden(self, client, db_session, admin_user, maintainer_token):
        """Test non-admin cannot delete users."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        response = client.delete(f"/api/users/{admin_user.id}", headers=headers)
        
        assert response.status_code == 403
    
    def test_get_user_by_email_admin(self, client, db_session, reporter_user, admin_token):
        """Test admin can get user by email."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get(f"/api/users/email/{reporter_user.email}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == reporter_user.email
    
    def test_get_user_by_email_not_found(self, client, db_session, admin_token):
        """Test getting user by non-existent email."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/users/email/nonexistent@test.com", headers=headers)
        
        assert response.status_code == 404
    
    def test_get_users_count_admin(self, client, db_session, admin_token):
        """Test admin can get users count."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/users/stats/count", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert data["total_users"] >= 1


class TestUserRoutesAuth:
    """Test authentication requirements for user routes."""
    
    def test_create_user_no_auth(self, client, db_session):
        """Test creating user without authentication."""
        user_data = {
            "email": "noauth@test.com",
            "password": "password123",
            "full_name": "No Auth User",
            "role": "REPORTER"
        }
        
        response = client.post("/api/users/", json=user_data)
        
        assert response.status_code == 401
    
    def test_get_users_no_auth(self, client, db_session):
        """Test getting users without authentication."""
        response = client.get("/api/users/")
        
        assert response.status_code == 401
    
    def test_update_user_no_auth(self, client, db_session, reporter_user):
        """Test updating user without authentication."""
        update_data = {"full_name": "Unauthorized Update"}
        
        response = client.put(f"/api/users/{reporter_user.id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_delete_user_no_auth(self, client, db_session, reporter_user):
        """Test deleting user without authentication."""
        response = client.delete(f"/api/users/{reporter_user.id}")
        
        assert response.status_code == 401