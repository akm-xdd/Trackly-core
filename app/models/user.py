"""
User models
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid

# User Roles Enum
class UserRole(str, Enum):
    """User roles"""
    ADMIN = "ADMIN"
    MAINTAINER = "MAINTAINER" 
    REPORTER = "REPORTER"


# Request and Response Models

class UserCreate(BaseModel):
    """Create new user"""
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.REPORTER


class UserUpdate(BaseModel):
    """Update user"""
    full_name: Optional[str] = None
    role: Optional[UserRole] = None



class UserResponse(BaseModel):
    """User response (no password)"""
    id: str
    email: str
    full_name: str
    role: UserRole
    created_at: datetime


# Base User Model

class User(BaseModel):
    """Internal user model"""
    id: str = ""
    email: str
    password: str 
    full_name: str
    role: UserRole
    created_at: datetime = None
    
    def __init__(self, **data):
        if not data.get('id'):
            data['id'] = str(uuid.uuid4())
        if not data.get('created_at'):
            data['created_at'] = datetime.utcnow()
        super().__init__(**data)
    
    def to_response(self) -> UserResponse:
        """Convert to safe response"""
        return UserResponse(
            id=self.id,
            email=self.email,
            full_name=self.full_name,
            role=self.role,
            created_at=self.created_at
        )