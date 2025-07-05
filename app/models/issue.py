"""
Issue model
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Optional
import uuid

# Issue Types and Severity Levels
class IssueSeverity(str, Enum):
    """Severity levels for issues"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IssueStatus(str, Enum):
    """Status of an issue"""
    OPEN = "OPEN"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


# Request and Response Models

class IssueCreate(BaseModel):
    """Create new issue"""
    title: str
    description: str
    severity: IssueSeverity = IssueSeverity.MEDIUM
    file_url: Optional[str] = None


class IssueUpdate(BaseModel):
    """Update issue"""
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[IssueSeverity] = None
    status: Optional[IssueStatus] = None
    file_url: Optional[str] = None


class IssueResponse(BaseModel):
    """Issue response"""
    id: str
    title: str
    description: str
    severity: IssueSeverity
    status: IssueStatus
    created_by: str  # User ID
    file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None  


# Base Issue Model

class Issue(BaseModel):
    """Internal issue model"""
    id: str = ""
    title: str
    description: str
    severity: IssueSeverity
    status: IssueStatus = IssueStatus.OPEN
    created_by: str 
    file_url: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    updated_by: Optional[str] = None  
    
    def __init__(self, **data):
        if not data.get('id'):
            data['id'] = str(uuid.uuid4())
        if not data.get('created_at'):
            data['created_at'] = datetime.utcnow()
        if not data.get('updated_at'):
            data['updated_at'] = datetime.utcnow()
        super().__init__(**data)
    
    def update(self, **data):
        """Update issue and timestamp"""
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
    
    def to_response(self) -> IssueResponse:
        """Convert to response"""
        return IssueResponse(
            id=self.id,
            title=self.title,
            description=self.description,
            severity=self.severity,
            status=self.status,
            created_by=self.created_by,
            file_url=self.file_url,
            created_at=self.created_at,
            updated_at=self.updated_at
        )