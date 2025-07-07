import pytest
from unittest.mock import patch, MagicMock
from app.services.issues.service import IssueService
from app.models.issue import IssueCreate, IssueUpdate, IssueSeverity, IssueStatus
from app.schemas.issue_schema import IssueSchema


class TestIssueServiceCreate:
    """Test issue creation functionality."""
    
    @patch('app.services.issues.service.asyncio.create_task')
    def test_create_issue_success(self, mock_create_task, db_session, reporter_user):
        """Test successful issue creation."""
        mock_create_task.return_value = MagicMock()
        
        issue_data = IssueCreate(
            title="Test Bug Report",
            description="This is a test bug description",
            severity=IssueSeverity.HIGH,
            file_url=None
        )
        
        result = IssueService.create_issue(db_session, issue_data, reporter_user.id)
        
        assert result.title == "Test Bug Report"
        assert result.description == "This is a test bug description"
        assert result.severity == IssueSeverity.HIGH
        assert result.status == IssueStatus.OPEN  # Default status
        assert result.created_by == reporter_user.id
        assert result.created_by_name == reporter_user.full_name
        assert result.id is not None
        
        # Verify broadcast was called
        mock_create_task.assert_called_once()
    
    @patch('app.services.issues.service.asyncio.create_task')
    def test_create_issue_with_file(self, mock_create_task, db_session, admin_user):
        """Test issue creation with file URL."""
        mock_create_task.return_value = MagicMock()
        
        issue_data = IssueCreate(
            title="Bug with Screenshot",
            description="Bug report with attached screenshot",
            severity=IssueSeverity.MEDIUM,
            file_url="https://example.com/screenshot.png"
        )
        
        result = IssueService.create_issue(db_session, issue_data, admin_user.id)
        
        assert result.file_url == "https://example.com/screenshot.png"
        assert result.created_by == admin_user.id


class TestIssueServiceRead:
    """Test issue retrieval functionality."""
    
    def test_get_issue_by_id_success(self, db_session, sample_issue):
        """Test successful issue retrieval by ID."""
        result = IssueService.get_issue_by_id(db_session, sample_issue.id)
        
        assert result is not None
        assert result.id == sample_issue.id
        assert result.title == sample_issue.title
        assert result.description == sample_issue.description
        assert result.created_by_name is not None  # Should include creator name
    
    def test_get_issue_by_id_not_found(self, db_session):
        """Test issue retrieval with non-existent ID."""
        result = IssueService.get_issue_by_id(db_session, "nonexistent-id")
        
        assert result is None
    
    def test_get_all_issues(self, db_session, sample_issue):
        """Test retrieving all issues."""
        result = IssueService.get_all_issues(db_session, skip=0, limit=10)
        
        assert len(result) >= 1
        assert any(issue.id == sample_issue.id for issue in result)
    
    def test_get_issues_pagination(self, db_session, reporter_user):
        """Test issue pagination."""
        # Create multiple issues
        for i in range(3):
            issue = IssueSchema(
                title=f"Test Issue {i}",
                description=f"Description {i}",
                severity=IssueSeverity.LOW,
                created_by=reporter_user.id
            )
            db_session.add(issue)
        db_session.commit()
        
        # Test pagination
        result = IssueService.get_all_issues(db_session, skip=0, limit=2)
        assert len(result) == 2
        
        result = IssueService.get_all_issues(db_session, skip=2, limit=2)
        assert len(result) >= 1
    
    def test_get_issues_by_user(self, db_session, reporter_user, admin_user):
        """Test retrieving issues by specific user."""
        # Create issue for reporter
        reporter_issue = IssueSchema(
            title="Reporter Issue",
            description="Issue by reporter",
            severity=IssueSeverity.MEDIUM,
            created_by=reporter_user.id
        )
        db_session.add(reporter_issue)
        
        # Create issue for admin
        admin_issue = IssueSchema(
            title="Admin Issue",
            description="Issue by admin",
            severity=IssueSeverity.HIGH,
            created_by=admin_user.id
        )
        db_session.add(admin_issue)
        db_session.commit()
        
        # Get issues by reporter
        result = IssueService.get_issues_by_user(db_session, reporter_user.id)
        
        assert len(result) >= 1
        assert all(issue.created_by == reporter_user.id for issue in result)
    
    def test_get_issues_by_status(self, db_session, reporter_user):
        """Test retrieving issues by status."""
        # Create issues with different statuses
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
        
        # Get only OPEN issues
        result = IssueService.get_issues_by_status(db_session, IssueStatus.OPEN)
        
        assert len(result) >= 1
        assert all(issue.status == IssueStatus.OPEN for issue in result)


class TestIssueServiceUpdate:
    """Test issue update functionality."""
    
    @patch('app.services.issues.service.asyncio.create_task')
    def test_update_issue_success(self, mock_create_task, db_session, sample_issue, maintainer_user):
        """Test successful issue update."""
        mock_create_task.return_value = MagicMock()
        
        update_data = IssueUpdate(
            title="Updated Title",
            description="Updated description",
            severity=IssueSeverity.CRITICAL,
            status=IssueStatus.IN_PROGRESS
        )
        
        result = IssueService.update_issue(db_session, sample_issue.id, update_data, maintainer_user.id)
        
        assert result is not None
        assert result.title == "Updated Title"
        assert result.description == "Updated description"
        assert result.severity == IssueSeverity.CRITICAL
        assert result.status == IssueStatus.IN_PROGRESS
        assert result.updated_by == maintainer_user.id
        assert result.updated_by_name == maintainer_user.full_name
    
    @patch('app.services.issues.service.asyncio.create_task')
    def test_update_issue_partial(self, mock_create_task, db_session, sample_issue, admin_user):
        """Test partial issue update."""
        mock_create_task.return_value = MagicMock()
        
        original_title = sample_issue.title
        update_data = IssueUpdate(status=IssueStatus.TRIAGED)
        
        result = IssueService.update_issue(db_session, sample_issue.id, update_data, admin_user.id)
        
        assert result is not None
        assert result.title == original_title  # Unchanged
        assert result.status == IssueStatus.TRIAGED  # Changed
    
    def test_update_issue_not_found(self, db_session, admin_user):
        """Test updating non-existent issue."""
        update_data = IssueUpdate(title="New Title")
        
        result = IssueService.update_issue(db_session, "nonexistent-id", update_data, admin_user.id)
        
        assert result is None


class TestIssueServiceDelete:
    """Test issue deletion functionality."""
    
    @patch('app.services.issues.service.asyncio.create_task')
    def test_delete_issue_success(self, mock_create_task, db_session, reporter_user):
        """Test successful issue deletion."""
        mock_create_task.return_value = MagicMock()
        
        # Create issue to delete
        issue = IssueSchema(
            title="To Delete",
            description="Issue to be deleted",
            severity=IssueSeverity.LOW,
            created_by=reporter_user.id
        )
        db_session.add(issue)
        db_session.commit()
        db_session.refresh(issue)
        
        # Delete the issue
        result = IssueService.delete_issue(db_session, issue.id, reporter_user.id)
        
        assert result is True
        
        # Verify issue is deleted
        deleted_issue = IssueService.get_issue_by_id(db_session, issue.id)
        assert deleted_issue is None
    
    def test_delete_issue_not_found(self, db_session, admin_user):
        """Test deleting non-existent issue."""
        result = IssueService.delete_issue(db_session, "nonexistent-id", admin_user.id)
        
        assert result is False


class TestIssueServiceStats:
    """Test issue statistics functionality."""
    
    def test_get_issues_count_all_roles(self, db_session, sample_issue):
        """Test getting issues count for admin/maintainer (see all)."""
        count = IssueService.get_issues_count(db_session, user_role="ADMIN")
        
        assert count >= 1
    
    def test_get_issues_count_reporter_only(self, db_session, reporter_user, admin_user):
        """Test getting issues count for reporter (own only)."""
        # Create issue for reporter
        reporter_issue = IssueSchema(
            title="Reporter Issue",
            description="Issue by reporter",
            severity=IssueSeverity.LOW,
            created_by=reporter_user.id
        )
        db_session.add(reporter_issue)
        db_session.commit()
        
        count = IssueService.get_issues_count(db_session, user_id=reporter_user.id, user_role="REPORTER")
        
        assert count >= 1
    
    def test_get_issues_count_by_status(self, db_session, reporter_user):
        """Test getting issues count grouped by status."""
        # Create issues with different statuses
        statuses = [IssueStatus.OPEN, IssueStatus.TRIAGED, IssueStatus.DONE]
        for status in statuses:
            issue = IssueSchema(
                title=f"Issue {status.value}",
                description="Test issue",
                severity=IssueSeverity.LOW,
                status=status,
                created_by=reporter_user.id
            )
            db_session.add(issue)
        db_session.commit()
        
        result = IssueService.get_issues_count_by_status(db_session, user_role="ADMIN")
        
        assert isinstance(result, dict)
        assert "OPEN" in result
        assert "TRIAGED" in result
        assert "DONE" in result
    
    def test_get_issues_count_by_severity(self, db_session, admin_user):
        """Test getting issues count grouped by severity."""
        # Create issues with different severities
        severities = [IssueSeverity.LOW, IssueSeverity.MEDIUM, IssueSeverity.HIGH]
        for severity in severities:
            issue = IssueSchema(
                title=f"Issue {severity.value}",
                description="Test issue",
                severity=severity,
                created_by=admin_user.id
            )
            db_session.add(issue)
        db_session.commit()
        
        result = IssueService.get_issues_count_by_severity(db_session, user_role="ADMIN")
        
        assert isinstance(result, dict)
        assert "LOW" in result
        assert "MEDIUM" in result
        assert "HIGH" in result