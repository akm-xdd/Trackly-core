from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class EventType(str, Enum):
    ISSUE_CREATED = "issue_created"
    ISSUE_UPDATED = "issue_updated"
    ISSUE_DELETED = "issue_deleted"

class IssueEvent(BaseModel):
    event_type: EventType
    issue_id: str
    user_id: str 
    user_name: Optional[str] = None 
    timestamp: datetime
    data: Optional[Any] = None