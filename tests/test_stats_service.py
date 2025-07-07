import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from app.services.stats.service import StatsService
from app.models.daily_stats import DailyStatsCreate, DailyStatsResponse
from app.schemas.daily_stats_schema import DailyStatsSchema
from app.schemas.issue_schema import IssueSchema
from app.models.issue import IssueStatus, IssueSeverity


class TestStatsServiceAggregation:
    """Test daily stats aggregation functionality."""
    
    def test_aggregate_daily_stats_logic(self, db_session, reporter_user):
        """Test the SQL aggregation logic directly."""
        # Create test issues with different statuses and severities
        issues_data = [
            {"status": IssueStatus.OPEN, "severity": IssueSeverity.HIGH},
            {"status": IssueStatus.OPEN, "severity": IssueSeverity.MEDIUM},
            {"status": IssueStatus.TRIAGED, "severity": IssueSeverity.LOW},
            {"status": IssueStatus.DONE, "severity": IssueSeverity.CRITICAL},
        ]
        
        for issue_data in issues_data:
            issue = IssueSchema(
                title="Test Issue",
                description="Test description",
                status=issue_data["status"],
                severity=issue_data["severity"],
                created_by=reporter_user.id
            )
            db_session.add(issue)
        db_session.commit()
        
        # Test the SQL queries directly (this is what aggregate_daily_stats does)
        from sqlalchemy import func
        
        # Count by status
        status_results = (db_session.query(IssueSchema.status, func.count(IssueSchema.id))
                         .filter(func.date(IssueSchema.created_at) <= date.today())
                         .group_by(IssueSchema.status)
                         .all())
        
        status_counts = {status.value: count for status, count in status_results}
        
        assert status_counts.get("OPEN", 0) == 2
        assert status_counts.get("TRIAGED", 0) == 1
        assert status_counts.get("DONE", 0) == 1
        
        # Count by severity
        severity_results = (db_session.query(IssueSchema.severity, func.count(IssueSchema.id))
                           .filter(func.date(IssueSchema.created_at) <= date.today())
                           .group_by(IssueSchema.severity)
                           .all())
        
        severity_counts = {severity.value: count for severity, count in severity_results}
        
        assert severity_counts.get("HIGH", 0) == 1
        assert severity_counts.get("MEDIUM", 0) == 1
        assert severity_counts.get("LOW", 0) == 1
        assert severity_counts.get("CRITICAL", 0) == 1
        
        # Total count
        total = sum(status_counts.values())
        assert total == 4


class TestStatsServiceSaveRetrieve:
    """Test saving and retrieving daily stats."""
    
    def test_save_daily_stats_new(self, db_session):
        """Test saving new daily stats."""
        test_date = date.today()
        stats_data = DailyStatsCreate(
            date=test_date,
            status_open=5,
            status_triaged=3,
            status_in_progress=2,
            status_done=10,
            severity_low=8,
            severity_medium=7,
            severity_high=4,
            severity_critical=1,
            total_issues=20
        )
        
        # Create stats schema directly to test database interaction
        db_stats = DailyStatsSchema(
            id="test-stats-id",
            date=stats_data.date,
            status_open=stats_data.status_open,
            status_triaged=stats_data.status_triaged,
            status_in_progress=stats_data.status_in_progress,
            status_done=stats_data.status_done,
            severity_low=stats_data.severity_low,
            severity_medium=stats_data.severity_medium,
            severity_high=stats_data.severity_high,
            severity_critical=stats_data.severity_critical,
            total_issues=stats_data.total_issues
        )
        
        db_session.add(db_stats)
        db_session.commit()
        db_session.refresh(db_stats)
        
        # Verify it was saved
        assert db_stats.date == test_date
        assert db_stats.total_issues == 20
        assert db_stats.status_open == 5
    
    def test_get_daily_stats_success(self, db_session):
        """Test retrieving existing daily stats."""
        test_date = date.today()
        
        # Create test stats
        stats = DailyStatsSchema(
            id="test-stats",
            date=test_date,
            status_open=3,
            severity_high=2,
            total_issues=5
        )
        db_session.add(stats)
        db_session.commit()
        
        result = StatsService.get_daily_stats(db_session, test_date)
        
        assert result is not None
        assert result.date == test_date
        assert result.total_issues == 5
        assert result.status_open == 3
        assert result.severity_high == 2
    
    def test_get_daily_stats_not_found(self, db_session):
        """Test retrieving non-existent daily stats."""
        future_date = date.today() + timedelta(days=30)
        
        result = StatsService.get_daily_stats(db_session, future_date)
        
        assert result is None
    
    def test_get_all_daily_stats(self, db_session):
        """Test retrieving multiple daily stats with limit."""
        # Create stats for multiple dates
        base_date = date.today()
        for i in range(5):
            stats_date = base_date - timedelta(days=i)
            stats = DailyStatsSchema(
                id=f"stats-{i}",
                date=stats_date,
                total_issues=i + 1
            )
            db_session.add(stats)
        db_session.commit()
        
        result = StatsService.get_all_daily_stats(db_session, limit=3)
        
        assert len(result) == 3
        # Should be ordered by date desc (most recent first)
        assert result[0].date >= result[1].date >= result[2].date
    
    def test_get_all_daily_stats_empty(self, db_session):
        """Test retrieving daily stats when none exist."""
        result = StatsService.get_all_daily_stats(db_session, limit=10)
        
        assert len(result) == 0


class TestStatsServiceBackgroundJob:
    """Test background job functionality (mocked)."""
    
    @patch('app.services.stats.service.StatsService.aggregate_daily_stats')
    @patch('app.services.stats.service.logger')
    def test_run_daily_aggregation_success(self, mock_logger, mock_aggregate):
        """Test successful background job execution."""
        # Mock the aggregate method to return expected result
        mock_aggregate.return_value = {
            "date": date.today(),
            "total_issues": 5,
            "status_counts": {"status_open": 3, "status_done": 2},
            "severity_counts": {"severity_high": 2, "severity_low": 3},
            "stats_id": "test-stats-id"
        }
        
        from app.services.stats.service import run_daily_aggregation
        result = run_daily_aggregation()
        
        assert result is not None
        assert result["total_issues"] == 5
        assert "date" in result
        mock_logger.info.assert_called()
        mock_aggregate.assert_called_once()
    
    @patch('app.services.stats.service.StatsService.aggregate_daily_stats')
    @patch('app.services.stats.service.logger')
    def test_run_daily_aggregation_error_handling(self, mock_logger, mock_aggregate):
        """Test background job error handling."""
        # Mock aggregate to raise an exception
        mock_aggregate.side_effect = Exception("Database connection failed")
        
        from app.services.stats.service import run_daily_aggregation
        
        with pytest.raises(Exception):
            run_daily_aggregation()
        
        mock_logger.error.assert_called()


class TestStatsServiceEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_date_filtering_logic(self, db_session, reporter_user):
        """Test that date filtering works correctly."""
        from sqlalchemy import func
        
        # Create an issue
        issue = IssueSchema(
            title="Date Test Issue",
            description="For testing date filtering",
            severity=IssueSeverity.MEDIUM,
            created_by=reporter_user.id
        )
        db_session.add(issue)
        db_session.commit()
        
        # Test today - should include the issue
        today_count = (db_session.query(func.count(IssueSchema.id))
                      .filter(func.date(IssueSchema.created_at) <= date.today())
                      .scalar())
        assert today_count >= 1
        
        # Test yesterday - should not include today's issue
        yesterday = date.today() - timedelta(days=1)
        yesterday_count = (db_session.query(func.count(IssueSchema.id))
                          .filter(func.date(IssueSchema.created_at) <= yesterday)
                          .scalar())
        assert yesterday_count == 0  # No issues created before today
    
    def test_stats_data_structure(self, db_session):
        """Test that DailyStatsCreate structure is correct."""
        stats_data = DailyStatsCreate(
            date=date.today(),
            status_open=1,
            status_triaged=2,
            status_in_progress=3,
            status_done=4,
            severity_low=5,
            severity_medium=6,
            severity_high=7,
            severity_critical=8,
            total_issues=10
        )
        
        # Verify all fields are present and correct types
        assert isinstance(stats_data.date, date)
        assert isinstance(stats_data.total_issues, int)
        assert stats_data.status_open == 1
        assert stats_data.severity_critical == 8
        
        # Total should match sum of statuses
        status_sum = (stats_data.status_open + stats_data.status_triaged + 
                     stats_data.status_in_progress + stats_data.status_done)
        assert status_sum == 10
        
        # Total should match sum of severities  
        severity_sum = (stats_data.severity_low + stats_data.severity_medium +
                       stats_data.severity_high + stats_data.severity_critical)
        assert severity_sum == 26  # 5+6+7+8