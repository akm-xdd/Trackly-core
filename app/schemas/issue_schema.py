from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.databases.postgres import Base
from app.models.issue import IssueSeverity, IssueStatus
import uuid


class IssueSchema(Base):
    """Issue table schema"""
    __tablename__ = "issues"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(IssueSeverity), nullable=False, default=IssueSeverity.MEDIUM)
    status = Column(SQLEnum(IssueStatus), nullable=False, default=IssueStatus.OPEN)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String, nullable=True)
    
    # Relationship to user
    creator = relationship("UserSchema", backref="issues")
    
    def __repr__(self):
        return f"<Issue(id={self.id}, title={self.title}, status={self.status})>"