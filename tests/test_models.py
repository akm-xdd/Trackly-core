import pytest
from datetime import datetime, date
from app.models.user import User, UserResponse, UserRole
from app.models.issue import Issue, IssueResponse, IssueSeverity, IssueStatus
from app.models.daily_stats import DailyStats, DailyStatsResponse


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation_auto_id(self):
        """Test user creation generates ID automatically."""
        user = User(
            email="test@example.com",
            password="hashed_password",
            full_name="Test User",
            role=UserRole.REPORTER
        )
        
        assert user.id is not None
        assert len(user.id) > 10  # UUID should be long
        assert user.created_at is not None
    
    def test_user_to_response(self):
        """Test converting user to response."""
        user = User(
            email="test@example.com",
            password="hashed_password",
            full_name="Test User",
            role=UserRole.ADMIN
        )
        
        response = user.to_response()
        
        assert isinstance(response, UserResponse)
        assert response.email == user.email
        assert response.full_name == user.full_name
        assert response.role == user.role
        assert response.id == user.id


class TestIssueModel:
    """Test Issue model functionality."""
    
    def test_issue_creation_defaults(self):
        """Test issue creation with default values."""
        issue = Issue(
            title="Test Issue",
            description="Test description",
            severity=IssueSeverity.HIGH,
            created_by="user-123"
        )
        
        assert issue.id is not None
        assert issue.status == IssueStatus.OPEN  # Default status
        assert issue.created_at is not None
        assert issue.updated_at is not None
    
    def test_issue_update_method(self):
        """Test issue update method."""
        issue = Issue(
            title="Original Title",
            description="Original description",
            severity=IssueSeverity.LOW,
            created_by="user-123"
        )
        
        original_updated_at = issue.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        issue.update(
            title="Updated Title",
            status=IssueStatus.DONE
        )
        
        assert issue.title == "Updated Title"
        assert issue.status == IssueStatus.DONE
        assert issue.updated_at > original_updated_at
    
    def test_issue_to_response(self):
        """Test converting issue to response."""
        issue = Issue(
            title="Test Issue",
            description="Test description",
            severity=IssueSeverity.CRITICAL,
            created_by="user-123"
        )
        
        response = issue.to_response()
        
        assert isinstance(response, IssueResponse)
        assert response.title == issue.title
        assert response.severity == issue.severity
        assert response.created_by == issue.created_by


class TestDailyStatsModel:
    """Test DailyStats model functionality."""
    
    def test_daily_stats_creation(self):
        """Test daily stats creation."""
        stats = DailyStats(
            date=date.today(),
            status_open=5,
            severity_high=3,
            total_issues=10
        )
        
        assert stats.id is not None
        assert stats.created_at is not None
        assert stats.total_issues == 10
    
    def test_daily_stats_to_response(self):
        """Test converting daily stats to response."""
        stats = DailyStats(
            date=date.today(),
            status_open=2,
            status_done=3,
            total_issues=5
        )
        
        response = stats.to_response()
        
        assert isinstance(response, DailyStatsResponse)
        assert response.date == stats.date
        assert response.total_issues == stats.total_issues
        assert response.id == stats.id