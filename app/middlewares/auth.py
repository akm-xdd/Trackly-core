from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
from functools import wraps

from app.databases.postgres import get_db
from app.utils.auth import verify_token
from app.services.auth.service import AuthService
from app.models.user import UserResponse, UserRole


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[UserResponse]:
    """Get current user from JWT token"""
    if not credentials:
        return None
    
    # Verify token
    payload = verify_token(credentials.credentials)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Get user from database
    user = AuthService.get_current_user(db, user_id)
    return user


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get current user (required - raises exception if not authenticated)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify token
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Get user from database
    user = AuthService.get_current_user(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


def require_roles(allowed_roles: List[UserRole]):
    """Decorator to require specific roles for an endpoint"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (must be injected by dependency)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Role-based dependencies
async def require_admin(current_user: UserResponse = Depends(get_current_user_required)) -> UserResponse:
    """Require ADMIN role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_maintainer_or_admin(current_user: UserResponse = Depends(get_current_user_required)) -> UserResponse:
    """Require MAINTAINER or ADMIN role"""
    if current_user.role not in [UserRole.MAINTAINER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Maintainer or Admin access required")
    return current_user


async def require_any_role(current_user: UserResponse = Depends(get_current_user_required)) -> UserResponse:
    """Require any authenticated user"""
    return current_user


# Resource ownership checks
def can_access_user_resource(current_user: UserResponse, target_user_id: str) -> bool:
    """Check if current user can access another user's resource"""
    # ADMIN can access everything
    if current_user.role == UserRole.ADMIN:
        return True
    
    # Users can access their own resources
    if current_user.id == target_user_id:
        return True
    
    return False


def can_access_issue_resource(current_user: UserResponse, issue_creator_id: str) -> bool:
    """Check if current user can access an issue"""
    # ADMIN and MAINTAINER can access all issues
    if current_user.role in [UserRole.ADMIN, UserRole.MAINTAINER]:
        return True
    
    # REPORTER can only access their own issues
    if current_user.role == UserRole.REPORTER and current_user.id == issue_creator_id:
        return True
    
    return False


def can_modify_issue(current_user: UserResponse, issue_creator_id: str) -> bool:
    """Check if current user can modify an issue"""
    # ADMIN can modify everything
    if current_user.role == UserRole.ADMIN:
        return True
    
    # MAINTAINER can modify any issue (triage, status updates)
    if current_user.role == UserRole.MAINTAINER:
        return True
    
    # REPORTER can only modify their own issues
    if current_user.role == UserRole.REPORTER and current_user.id == issue_creator_id:
        return True
    
    return False


def can_delete_issue(current_user: UserResponse, issue_creator_id: str) -> bool:
    """Check if current user can delete an issue"""
    # Only ADMIN can delete issues, or REPORTER can delete their own
    if current_user.role == UserRole.ADMIN:
        return True
    
    if current_user.role == UserRole.REPORTER and current_user.id == issue_creator_id:
        return True
    
    return False