from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime

from app.databases.postgres import get_db
from app.models.daily_stats import DailyStatsResponse
from app.services.stats.service import StatsService
from app.middlewares.auth import (
    require_admin,
    require_maintainer_or_admin,
    get_current_user_required
)
from app.models.user import UserResponse
from app.utils.scheduler import get_scheduler_status, manual_trigger_aggregation

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/daily", response_model=List[DailyStatsResponse])
def get_daily_stats(
    limit: int = Query(30, ge=1, le=365, description="Number of days to return"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get daily statistics (MAINTAINER+ only)"""
    return StatsService.get_all_daily_stats(db, limit=limit)


@router.get("/daily/{target_date}", response_model=DailyStatsResponse)
def get_daily_stats_by_date(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get daily statistics for specific date (MAINTAINER+ only)"""
    stats = StatsService.get_daily_stats(db, target_date)
    if not stats:
        raise HTTPException(status_code=404, detail=f"No statistics found for {target_date}")
    return stats


@router.post("/aggregate")
def trigger_manual_aggregation(
    current_user: UserResponse = Depends(require_admin)
):
    """Manually trigger daily stats aggregation (ADMIN only)"""
    try:
        result = manual_trigger_aggregation()
        return {
            "message": "Daily aggregation triggered successfully",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger aggregation: {str(e)}")


@router.get("/scheduler/status")
def get_background_job_status(
    current_user: UserResponse = Depends(require_admin)
):
    """Get background scheduler status (ADMIN only)"""
    return get_scheduler_status()


@router.get("/summary")
def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get latest statistics summary (MAINTAINER+ only)"""
    # Get today's stats
    today_stats = StatsService.get_daily_stats(db, date.today())
    
    # Get yesterday's stats for comparison
    from datetime import timedelta
    yesterday = date.today() - timedelta(days=1)
    yesterday_stats = StatsService.get_daily_stats(db, yesterday)
    
    # Calculate changes
    changes = {}
    if today_stats and yesterday_stats:
        changes = {
            "total_change": today_stats.total_issues - yesterday_stats.total_issues,
            "open_change": today_stats.status_open - yesterday_stats.status_open,
            "critical_change": today_stats.severity_critical - yesterday_stats.severity_critical
        }
    
    return {
        "today": today_stats,
        "yesterday": yesterday_stats,
        "changes": changes,
        "last_updated": datetime.utcnow().isoformat()
    }