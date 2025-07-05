from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.databases.postgres import get_db
from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services.user.service import UserService
from app.middlewares.auth import (
    require_admin,
    require_any_role,
    get_current_user_required,
    can_access_user_resource
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin)
):
    """Create a new user (ADMIN only)"""
    return UserService.create_user(db, user_data)


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin)
):
    """Get all users with pagination (ADMIN only)"""
    return UserService.get_all_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Get user by ID (Users can see their own data, ADMIN can see all)"""
    # Check if user can access this resource
    if not can_access_user_resource(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied to this user resource")
    
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str, 
    user_data: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Update user (Users can update themselves, ADMIN can update all)"""
    # Check if user can access this resource
    if not can_access_user_resource(current_user, user_id):
        raise HTTPException(status_code=403, detail="Access denied to this user resource")
    
    user = UserService.update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin)
):
    """Delete user (ADMIN only)"""
    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.get("/email/{email}", response_model=UserResponse)
def get_user_by_email(
    email: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin)
):
    """Get user by email (ADMIN only)"""
    user = UserService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/stats/count")
def get_users_count(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin)
):
    """Get total users count (ADMIN only)"""
    count = UserService.get_users_count(db)
    return {"total_users": count}