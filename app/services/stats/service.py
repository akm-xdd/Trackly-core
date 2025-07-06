from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import date, datetime
from fastapi import HTTPException
import uuid
import logging

from app.schemas.daily_stats_schema import DailyStatsSchema
from app.schemas.issue_schema import IssueSchema
from app.models.daily_stats import DailyStatsCreate, DailyStatsResponse, DailyStatsUpdate
from app.models.issue import IssueStatus, IssueSeverity
from app.databases.postgres import SessionLocal

# Set up logging
logger = logging.getLogger(__name__)


class StatsService:
    """Statistics aggregation service"""
    
    @staticmethod
    def aggregate_daily_stats(target_date: date = None) -> dict:
        """
        Aggregate issue statistics for a specific date (default: today)
        This is the main background job function
        """
        if target_date is None:
            target_date = date.today()
        
        db = SessionLocal()
        try:
            logger.info(f"Starting daily stats aggregation for {target_date}")
            
            # Get all issues created up to the target date
            issues_query = db.query(IssueSchema).filter(
                func.date(IssueSchema.created_at) <= target_date
            )
            
            # Count by status
            status_counts = {
                'status_open': 0,
                'status_triaged': 0,
                'status_in_progress': 0,
                'status_done': 0
            }
            
            # Count by severity
            severity_counts = {
                'severity_low': 0,
                'severity_medium': 0,
                'severity_high': 0,
                'severity_critical': 0
            }
            
            # Get aggregated counts using SQL queries for efficiency
            status_results = (db.query(IssueSchema.status, func.count(IssueSchema.id))
                            .filter(func.date(IssueSchema.created_at) <= target_date)
                            .group_by(IssueSchema.status)
                            .all())
            
            severity_results = (db.query(IssueSchema.severity, func.count(IssueSchema.id))
                              .filter(func.date(IssueSchema.created_at) <= target_date)
                              .group_by(IssueSchema.severity)
                              .all())
            
            # Process status counts
            for status, count in status_results:
                if status == IssueStatus.OPEN:
                    status_counts['status_open'] = count
                elif status == IssueStatus.TRIAGED:
                    status_counts['status_triaged'] = count
                elif status == IssueStatus.IN_PROGRESS:
                    status_counts['status_in_progress'] = count
                elif status == IssueStatus.DONE:
                    status_counts['status_done'] = count
            
            # Process severity counts
            for severity, count in severity_results:
                if severity == IssueSeverity.LOW:
                    severity_counts['severity_low'] = count
                elif severity == IssueSeverity.MEDIUM:
                    severity_counts['severity_medium'] = count
                elif severity == IssueSeverity.HIGH:
                    severity_counts['severity_high'] = count
                elif severity == IssueSeverity.CRITICAL:
                    severity_counts['severity_critical'] = count
            
            # Calculate total
            total_issues = sum(status_counts.values())
            
            # Create stats object
            stats_data = DailyStatsCreate(
                date=target_date,
                total_issues=total_issues,
                **status_counts,
                **severity_counts
            )
            
            # Save or update in database
            saved_stats = StatsService.save_daily_stats(db, stats_data)
            
            logger.info(f"Successfully aggregated daily stats for {target_date}: {total_issues} total issues")
            
            return {
                "date": target_date,
                "total_issues": total_issues,
                "status_counts": status_counts,
                "severity_counts": severity_counts,
                "stats_id": saved_stats.id if saved_stats else None
            }
            
        except Exception as e:
            logger.error(f"Error aggregating daily stats for {target_date}: {str(e)}")
            raise e
        finally:
            db.close()
    
    @staticmethod
    def save_daily_stats(db: Session, stats_data: DailyStatsCreate) -> Optional[DailyStatsResponse]:
        """Save or update daily stats in database"""
        try:
            # Check if stats for this date already exist
            existing_stats = db.query(DailyStatsSchema).filter(
                DailyStatsSchema.date == stats_data.date
            ).first()
            
            if existing_stats:
                # Update existing record
                existing_stats.status_open = stats_data.status_open
                existing_stats.status_triaged = stats_data.status_triaged
                existing_stats.status_in_progress = stats_data.status_in_progress
                existing_stats.status_done = stats_data.status_done
                existing_stats.severity_low = stats_data.severity_low
                existing_stats.severity_medium = stats_data.severity_medium
                existing_stats.severity_high = stats_data.severity_high
                existing_stats.severity_critical = stats_data.severity_critical
                existing_stats.total_issues = stats_data.total_issues
                
                db.commit()
                db.refresh(existing_stats)
                
                return DailyStatsResponse(
                    id=existing_stats.id,
                    date=existing_stats.date,
                    status_open=existing_stats.status_open,
                    status_triaged=existing_stats.status_triaged,
                    status_in_progress=existing_stats.status_in_progress,
                    status_done=existing_stats.status_done,
                    severity_low=existing_stats.severity_low,
                    severity_medium=existing_stats.severity_medium,
                    severity_high=existing_stats.severity_high,
                    severity_critical=existing_stats.severity_critical,
                    total_issues=existing_stats.total_issues,
                    created_at=existing_stats.created_at
                )
            else:
                # Create new record
                db_stats = DailyStatsSchema(
                    id=str(uuid.uuid4()),
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
                
                db.add(db_stats)
                db.commit()
                db.refresh(db_stats)
                
                return DailyStatsResponse(
                    id=db_stats.id,
                    date=db_stats.date,
                    status_open=db_stats.status_open,
                    status_triaged=db_stats.status_triaged,
                    status_in_progress=db_stats.status_in_progress,
                    status_done=db_stats.status_done,
                    severity_low=db_stats.severity_low,
                    severity_medium=db_stats.severity_medium,
                    severity_high=db_stats.severity_high,
                    severity_critical=db_stats.severity_critical,
                    total_issues=db_stats.total_issues,
                    created_at=db_stats.created_at
                )
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving daily stats: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save daily stats: {str(e)}")
    
    @staticmethod
    def get_daily_stats(db: Session, target_date: date) -> Optional[DailyStatsResponse]:
        """Get daily stats for specific date"""
        db_stats = db.query(DailyStatsSchema).filter(
            DailyStatsSchema.date == target_date
        ).first()
        
        if not db_stats:
            return None
            
        return DailyStatsResponse(
            id=db_stats.id,
            date=db_stats.date,
            status_open=db_stats.status_open,
            status_triaged=db_stats.status_triaged,
            status_in_progress=db_stats.status_in_progress,
            status_done=db_stats.status_done,
            severity_low=db_stats.severity_low,
            severity_medium=db_stats.severity_medium,
            severity_high=db_stats.severity_high,
            severity_critical=db_stats.severity_critical,
            total_issues=db_stats.total_issues,
            created_at=db_stats.created_at
        )
    
    @staticmethod
    def get_all_daily_stats(db: Session, limit: int = 30) -> List[DailyStatsResponse]:
        """Get recent daily stats with limit"""
        db_stats = (db.query(DailyStatsSchema)
                   .order_by(DailyStatsSchema.date.desc())
                   .limit(limit)
                   .all())
        
        return [
            DailyStatsResponse(
                id=stats.id,
                date=stats.date,
                status_open=stats.status_open,
                status_triaged=stats.status_triaged,
                status_in_progress=stats.status_in_progress,
                status_done=stats.status_done,
                severity_low=stats.severity_low,
                severity_medium=stats.severity_medium,
                severity_high=stats.severity_high,
                severity_critical=stats.severity_critical,
                total_issues=stats.total_issues,
                created_at=stats.created_at
            )
            for stats in db_stats
        ]


# Background job wrapper function (for scheduler)
def run_daily_aggregation():
    """Wrapper function for the background scheduler"""
    try:
        result = StatsService.aggregate_daily_stats()
        logger.info(f"Background aggregation completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Background aggregation failed: {str(e)}")
        raise e