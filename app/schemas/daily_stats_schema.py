from sqlalchemy import Column, String, DateTime, Integer, Date
from sqlalchemy.sql import func
from app.databases.postgres import Base


class DailyStatsSchema(Base):
    """Daily statistics table schema"""
    __tablename__ = "daily_stats"

    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    status_open = Column(Integer, nullable=False, default=0)
    status_triaged = Column(Integer, nullable=False, default=0)
    status_in_progress = Column(Integer, nullable=False, default=0)
    status_done = Column(Integer, nullable=False, default=0)
    severity_low = Column(Integer, nullable=False, default=0)
    severity_medium = Column(Integer, nullable=False, default=0)
    severity_high = Column(Integer, nullable=False, default=0)
    severity_critical = Column(Integer, nullable=False, default=0)
    total_issues = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<DailyStats(date={self.date}, total={self.total_issues})>"
