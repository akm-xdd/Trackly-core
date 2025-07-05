from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.databases.postgres import get_db
from app.models.auth import (
    LoginRequest, 
    SignupRequest, 
    RefreshTokenRequest,
    LoginResponse, 
    RefreshResponse
)
from app.models.user import UserResponse
from app.services.auth.service import AuthService
from app.middlewares.auth import get_current_user_required

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=LoginResponse)
def signup(
    signup_data: SignupRequest, 
    db: Session = Depends(get_db)
):
    """Register a new user"""
    return AuthService.signup(db, signup_data)


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest, 
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    return AuthService.login(db, login_data)


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    return AuthService.refresh_access_token(db, refresh_data.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Get current user information"""
    return current_user


@router.post("/logout")
def logout():
    """Logout (client should discard tokens)"""
    return {"message": "Successfully logged out. Please discard your tokens."}


# Test endpoints for different roles
@router.get("/test/admin")
def test_admin_access(current_user: UserResponse = Depends(get_current_user_required)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": f"Hello {current_user.role.value} {current_user.full_name}!", "role": current_user.role.value}


@router.get("/test/maintainer")  
def test_maintainer_access(current_user: UserResponse = Depends(get_current_user_required)):
    if current_user.role.value not in ["MAINTAINER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Maintainer or Admin access required")
    return {"message": f"Hello {current_user.role.value} {current_user.full_name}!", "role": current_user.role.value}


@router.get("/test/any")
def test_any_access(
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Test endpoint - Any authenticated user"""
    return {"message": f"Hello {current_user.role} {current_user.full_name}!", "role": current_user.role}