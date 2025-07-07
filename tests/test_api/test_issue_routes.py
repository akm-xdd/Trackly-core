import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.issue import IssueSeverity, IssueStatus


class TestIssueRoutesCRUD:
    """Test issue CRUD operations via API."""
    
    def test_create_issue_success(self, client, db_session, reporter_token):
        """Test successful issue creation."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        issue_data = {
            "title": "API Test Bug",
            "description": "Bug found during API testing",
            "severity": "HIGH",
            "file_url": None
        }
        
        response = client.post("/api/issues/", json=issue_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API Test Bug"
        assert data["description"] == "Bug found during API testing"
        assert data["severity"] == "HIGH"
        assert data["status"] == "OPEN"  # Default status
        assert data["created_by_name"] is not None
    
    def test_create_issue_unauthorized(self, client, db_session):
        """Test issue creation without authentication."""
        issue_data = {
            "title": "Unauthorized Issue",
            "description": "This should fail",
            "severity": "LOW"
        }
        
        response = client.post("/api/issues/", json=issue_data)
        
        assert response.status_code == 401
    
    def test_create_issue_invalid_data(self, client, db_session, admin_token):
        """Test issue creation with invalid data."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Missing required title
        response = client.post("/api/issues/", json={
            "description": "Missing title",
            "severity": "MEDIUM"
        }, headers=headers)
        
        assert response.status_code == 422
    
    def test_get_all_issues_admin(self, client, db_session, sample_issue, admin_token):
        """Test admin can see all issues."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/issues/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(issue["id"] == sample_issue.id for issue in data)
    
    def test_get_all_issues_reporter_filtered(self, client, db_session, sample_issue, reporter_token, admin_user):
        """Test reporter only sees their own issues."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        # Create issue by admin (should not be visible to reporter)
        from app.schemas.issue_schema import IssueSchema
        admin_issue = IssueSchema(
            title="Admin Issue",
            description="Admin-only issue",
            severity=IssueSeverity.LOW,
            created_by=admin_user.id
        )
        db_session.add(admin_issue)
        db_session.commit()
        
        response = client.get("/api/issues/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # Reporter should only see their own issues
        assert all(issue["created_by"] == "reporter-id" for issue in data)
    
    def test_get_issue_by_id_success(self, client, db_session, sample_issue, maintainer_token):
        """Test getting specific issue by ID."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        response = client.get(f"/api/issues/{sample_issue.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_issue.id
        assert data["title"] == sample_issue.title
    
    def test_get_issue_by_id_not_found(self, client, db_session, admin_token):
        """Test getting non-existent issue."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/issues/nonexistent-id", headers=headers)
        
        assert response.status_code == 404
    
    def test_get_issue_access_denied(self, client, db_session, sample_issue, reporter_token, admin_user):
        """Test reporter cannot access other user's issues."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        # Create issue by admin
        from app.schemas.issue_schema import IssueSchema
        admin_issue = IssueSchema(
            title="Admin Issue",
            description="Private issue",
            severity=IssueSeverity.MEDIUM,
            created_by=admin_user.id
        )
        db_session.add(admin_issue)
        db_session.commit()
        
        response = client.get(f"/api/issues/{admin_issue.id}", headers=headers)
        
        assert response.status_code == 403


class TestIssueRoutesUpdate:
    """Test issue update operations."""
    
    def test_update_issue_admin(self, client, db_session, sample_issue, admin_token):
        """Test admin can update any issue."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        update_data = {
            "title": "Updated by Admin",
            "status": "TRIAGED",
            "severity": "CRITICAL"
        }
        
        response = client.put(f"/api/issues/{sample_issue.id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated by Admin"
        assert data["status"] == "TRIAGED"
        assert data["severity"] == "CRITICAL"
        assert data["updated_by_name"] is not None
    
    def test_update_issue_maintainer(self, client, db_session, sample_issue, maintainer_token):
        """Test maintainer can update issues."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        update_data = {
            "status": "IN_PROGRESS",
            "severity": "HIGH"
        }
        
        response = client.put(f"/api/issues/{sample_issue.id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["severity"] == "HIGH"
    
    def test_update_issue_reporter_own(self, client, db_session, sample_issue, reporter_token):
        """Test reporter can update their own issue (title/description only)."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        update_data = {
            "title": "Updated by Reporter",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/issues/{sample_issue.id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated by Reporter"
        assert data["description"] == "Updated description"
    
    def test_update_issue_reporter_forbidden_fields(self, client, db_session, sample_issue, reporter_token):
        """Test reporter cannot update status/severity."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        update_data = {
            "status": "DONE",  # Reporter shouldn't be able to change this
            "severity": "CRITICAL"
        }
        
        response = client.put(f"/api/issues/{sample_issue.id}", json=update_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_update_issue_not_found(self, client, db_session, admin_token):
        """Test updating non-existent issue."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        update_data = {"title": "Should Fail"}
        
        response = client.put("/api/issues/nonexistent-id", json=update_data, headers=headers)
        
        assert response.status_code == 404


class TestIssueRoutesDelete:
    """Test issue deletion operations."""
    
    def test_delete_issue_admin(self, client, db_session, reporter_user, admin_token):
        """Test admin can delete any issue."""
        # Create issue to delete
        from app.schemas.issue_schema import IssueSchema
        issue = IssueSchema(
            title="To Delete",
            description="Will be deleted",
            severity=IssueSeverity.LOW,
            created_by=reporter_user.id
        )
        db_session.add(issue)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete(f"/api/issues/{issue.id}", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_delete_issue_reporter_own(self, client, db_session, sample_issue, reporter_token):
        """Test reporter can delete their own issue."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.delete(f"/api/issues/{sample_issue.id}", headers=headers)
        
        assert response.status_code == 200
    
    def test_delete_issue_reporter_forbidden(self, client, db_session, admin_user, reporter_token):
        """Test reporter cannot delete other user's issues."""
        # Create issue by admin
        from app.schemas.issue_schema import IssueSchema
        admin_issue = IssueSchema(
            title="Admin Issue",
            description="Cannot be deleted by reporter",
            severity=IssueSeverity.MEDIUM,
            created_by=admin_user.id
        )
        db_session.add(admin_issue)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {reporter_token}"}
        response = client.delete(f"/api/issues/{admin_issue.id}", headers=headers)
        
        assert response.status_code == 403


class TestIssueRoutesStats:
    """Test issue statistics endpoints."""
    
    def test_get_issues_count(self, client, db_session, sample_issue, admin_token):
        """Test getting total issues count."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/issues/stats/count", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_issues" in data
        assert data["total_issues"] >= 1
    
    def test_get_issues_by_status_stats(self, client, db_session, sample_issue, maintainer_token):
        """Test getting issues grouped by status."""
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        response = client.get("/api/issues/stats/by-status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "issues_by_status" in data
        assert isinstance(data["issues_by_status"], dict)
    
    def test_get_issues_by_severity_stats(self, client, db_session, sample_issue, admin_token):
        """Test getting issues grouped by severity."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/issues/stats/by-severity", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "issues_by_severity" in data
        assert isinstance(data["issues_by_severity"], dict)


class TestIssueRoutesPagination:
    """Test pagination and filtering."""
    
    def test_issues_pagination(self, client, db_session, reporter_user, admin_token):
        """Test issue pagination parameters."""
        # Create multiple issues
        from app.schemas.issue_schema import IssueSchema
        for i in range(5):
            issue = IssueSchema(
                title=f"Pagination Test {i}",
                description=f"Issue {i}",
                severity=IssueSeverity.LOW,
                created_by=reporter_user.id
            )
            db_session.add(issue)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test with limit
        response = client.get("/api/issues/?skip=0&limit=3", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
    
    def test_issues_filter_by_status(self, client, db_session, reporter_user, maintainer_token):
        """Test filtering issues by status."""
        # Create issues with different statuses
        from app.schemas.issue_schema import IssueSchema
        open_issue = IssueSchema(
            title="Open Issue",
            description="Open issue",
            severity=IssueSeverity.LOW,
            status=IssueStatus.OPEN,
            created_by=reporter_user.id
        )
        done_issue = IssueSchema(
            title="Done Issue",
            description="Done issue",
            severity=IssueSeverity.LOW,
            status=IssueStatus.DONE,
            created_by=reporter_user.id
        )
        db_session.add(open_issue)
        db_session.add(done_issue)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {maintainer_token}"}
        
        # Filter by OPEN status
        response = client.get("/api/issues/?status=OPEN", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert all(issue["status"] == "OPEN" for issue in data)


class TestIssueRoutesSSE:
    """Test Server-Sent Events endpoint."""
    
    def test_sse_endpoint_invalid_token(self, client, db_session):
        """Test SSE endpoint with invalid token."""
        response = client.get("/api/issues/events?token=invalid.token.here")
        
        assert response.status_code == 401
    
    def test_sse_endpoint_missing_token(self, client, db_session):
        """Test SSE endpoint without token."""
        response = client.get("/api/issues/events")
        
        assert response.status_code == 422
    
    @pytest.mark.skip(reason="SSE endpoint requires complex async mocking")
    def test_sse_endpoint_admin_access(self, client, db_session, admin_token):
        """Test SSE endpoint access (admin only) - SKIPPED due to complexity."""

        pass
    
    def test_sse_stats_endpoint(self, client, db_session, admin_token):
        """Test SSE statistics endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/api/issues/events/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "timestamp" in data


class TestIssueRoutesUserIssues:
    """Test user-specific issue endpoints."""
    
    def test_get_user_issues_admin(self, client, db_session, sample_issue, reporter_user, admin_token):
        """Test admin can get any user's issues."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get(f"/api/issues/user/{reporter_user.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(issue["created_by"] == reporter_user.id for issue in data)
    
    def test_get_user_issues_reporter_own(self, client, db_session, sample_issue, reporter_user, reporter_token):
        """Test reporter can get their own issues."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get(f"/api/issues/user/{reporter_user.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_issues_reporter_forbidden(self, client, db_session, admin_user, reporter_token):
        """Test reporter cannot get other user's issues."""
        headers = {"Authorization": f"Bearer {reporter_token}"}
        
        response = client.get(f"/api/issues/user/{admin_user.id}", headers=headers)
        
        assert response.status_code == 403