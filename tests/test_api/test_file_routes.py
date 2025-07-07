import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestFileRoutes:
    """Test file upload/download API endpoints."""
    
    @patch('app.services.uploads.service.azure_client')
    def test_upload_file_success(self, mock_azure, client, db_session, reporter_token):
        """Test successful file upload."""
        mock_azure.upload_file.return_value = "https://fake-storage.blob.core.windows.net/test-file.jpg"
        
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        # Create a fake file
        file_content = b"fake file content"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
        
        response = client.post("/api/files/upload", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert "file_url" in data
        assert data["original_filename"] == "test.jpg"
    
    def test_upload_file_no_auth(self, client, db_session):
        """Test file upload without authentication."""
        file_content = b"fake file content"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
        
        response = client.post("/api/files/upload", files=files)
        
        assert response.status_code == 401
    
    def test_upload_file_no_file(self, client, db_session, admin_token):
        """Test file upload without file."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.post("/api/files/upload", headers=headers)
        
        assert response.status_code == 422
    
    @patch('app.services.uploads.service.azure_client')
    def test_upload_file_too_large(self, mock_azure, client, db_session, maintainer_token):
        """Test uploading file that's too large."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        # Create a large file (mock 60MB)
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB
        files = {"file": ("large.jpg", BytesIO(large_content), "image/jpeg")}
        
        response = client.post("/api/files/upload", files=files, headers=headers)
        
        assert response.status_code == 413  # Payload too large
    
    def test_get_files_admin(self, client, db_session, admin_token):
        """Test admin can get all files."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/files/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
    
    def test_get_files_non_admin_forbidden(self, client, db_session, reporter_token):
        """Test non-admin cannot get all files."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get("/api/files/", headers=headers)
        
        assert response.status_code == 403
    
    def test_get_files_pagination(self, client, db_session, admin_token):
        """Test file listing pagination."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/files/?skip=0&limit=5", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) <= 5
    
    @patch('app.services.uploads.service.UploadService.get_file_by_id')
    def test_get_file_by_id_success(self, mock_get_file, client, db_session, reporter_token):
        """Test getting file by ID."""
        from app.models.uploads import FileResponse
        from datetime import datetime
        
        mock_get_file.return_value = FileResponse(
            file_id="TEST123",
            original_filename="test.jpg",
            file_size=1024,
            content_type="image/jpeg",
            file_url="https://example.com/test.jpg",
            uploaded_by="user-123",
            uploaded_by_name="Test User",
            status="ACTIVE",
            upload_timestamp=datetime.utcnow()
        )
        
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get("/api/files/TEST123", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "TEST123"
        assert data["original_filename"] == "test.jpg"
    
    def test_get_file_by_id_not_found(self, client, db_session, admin_token):
        """Test getting non-existent file."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/files/NONEXISTENT", headers=headers)
        
        assert response.status_code == 404
    
    @patch('app.services.uploads.service.UploadService.get_file_by_id')
    @patch('app.services.uploads.service.UploadService.delete_file')
    def test_delete_file_success(self, mock_delete, mock_get_file, client, db_session, reporter_token):
        """Test successful file deletion."""
        from app.models.uploads import FileResponse
        from datetime import datetime
        
        # Mock file owned by current user
        mock_get_file.return_value = FileResponse(
            file_id="DELETE123",
            original_filename="delete.jpg",
            file_size=1024,
            content_type="image/jpeg",
            file_url="https://example.com/delete.jpg",
            uploaded_by="reporter-id",  # Same as reporter_token user
            uploaded_by_name="Reporter User",
            status="ACTIVE",
            upload_timestamp=datetime.utcnow()
        )
        mock_delete.return_value = True
        
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.delete("/api/files/DELETE123", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    @patch('app.services.uploads.service.UploadService.get_file_by_id')
    def test_delete_file_forbidden(self, mock_get_file, client, db_session, reporter_token):
        """Test deleting file owned by another user."""
        from app.models.uploads import FileResponse
        from datetime import datetime
        
        # Mock file owned by different user
        mock_get_file.return_value = FileResponse(
            file_id="OTHER123",
            original_filename="other.jpg",
            file_size=1024,
            content_type="image/jpeg",
            file_url="https://example.com/other.jpg",
            uploaded_by="other-user-id",  # Different user
            uploaded_by_name="Other User",
            status="ACTIVE",
            upload_timestamp=datetime.utcnow()
        )
        
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.delete("/api/files/OTHER123", headers=headers)
        
        assert response.status_code == 403
    
    def test_get_files_count_admin(self, client, db_session, admin_token):
        """Test getting files count."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/files/stats/count", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
    
    def test_get_files_count_forbidden(self, client, db_session, reporter_token):
        """Test non-admin cannot get files count."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get("/api/files/stats/count", headers=headers)
        
        assert response.status_code == 403
    
    @patch('app.services.uploads.service.UploadService.get_file_url_by_id')
    def test_get_file_url_success(self, mock_get_url, client, db_session, maintainer_token):
        """Test getting file URL by ID."""
        mock_get_url.return_value = "https://example.com/file.jpg"
        
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        response = client.get("/api/files/url/FILE123", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "FILE123"
        assert data["file_url"] == "https://example.com/file.jpg"
    
    def test_get_file_url_not_found(self, client, db_session, admin_token):
        """Test getting URL for non-existent file."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/files/url/NOTFOUND", headers=headers)
        
        assert response.status_code == 404


class TestFileRouteAuth:
    """Test file route authentication."""
    
    def test_all_file_endpoints_require_auth(self, client, db_session):
        """Test all file endpoints require authentication."""
        endpoints = [
            ("GET", "/api/files/"),
            ("GET", "/api/files/TEST123"),
            ("DELETE", "/api/files/TEST123"),
            ("GET", "/api/files/stats/count"),
            ("GET", "/api/files/url/TEST123"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401