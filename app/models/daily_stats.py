from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional
import uuid


class DailyStatsCreate(BaseModel):
    """Create daily stats"""
    date: date
    status_open: int = 0
    status_triaged: int = 0
    status_in_progress: int = 0
    status_done: int = 0
    severity_low: int = 0
    severity_medium: int = 0
    severity_high: int = 0
    severity_critical: int = 0
    total_issues: int = 0


class DailyStatsResponse(BaseModel):
    """Daily stats response"""
    id: str
    date: date
    status_open: int
    status_triaged: int
    status_in_progress: int
    status_done: int
    severity_low: int
    severity_medium: int
    severity_high: int
    severity_critical: int
    total_issues: int
    created_at: datetime


class DailyStatsUpdate(BaseModel):
    """Update daily stats"""
    status_open: Optional[int] = None
    status_triaged: Optional[int] = None
    status_in_progress: Optional[int] = None
    status_done: Optional[int] = None
    severity_low: Optional[int] = None
    severity_medium: Optional[int] = None
    severity_high: Optional[int] = None
    severity_critical: Optional[int] = None
    total_issues: Optional[int] = None


# Internal Model
class DailyStats(BaseModel):
    """Internal daily stats model"""
    id: str = ""
    date: date
    status_open: int = 0
    status_triaged: int = 0
    status_in_progress: int = 0
    status_done: int = 0
    severity_low: int = 0
    severity_medium: int = 0
    severity_high: int = 0
    severity_critical: int = 0
    total_issues: int = 0
    created_at: datetime = None
    
    def __init__(self, **data):
        if not data.get('id'):
            data['id'] = str(uuid.uuid4())
        if not data.get('created_at'):
            data['created_at'] = datetime.utcnow()
        super().__init__(**data)
    
    def to_response(self) -> DailyStatsResponse:
        """Convert to response"""
        return DailyStatsResponse(
            id=self.id,
            date=self.date,
            status_open=self.status_open,
            status_triaged=self.status_triaged,
            status_in_progress=self.status_in_progress,
            status_done=self.status_done,
            severity_low=self.severity_low,
            severity_medium=self.severity_medium,
            severity_high=self.severity_high,
            severity_critical=self.severity_critical,
            total_issues=self.total_issues,
            created_at=self.created_at
        )