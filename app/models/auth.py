from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole, UserResponse


# Auth Request Models
class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    """Signup request"""
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.REPORTER


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# Auth Response Models
class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginResponse(BaseModel):
    """Login response with user info and tokens"""
    user: UserResponse
    tokens: TokenResponse


class RefreshResponse(BaseModel):
    """Refresh token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Internal Models
class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # user ID
    email: str
    role: UserRole
    exp: Optional[int] = None
    type: str = "access"