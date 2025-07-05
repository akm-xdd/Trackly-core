from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.databases.postgres import get_db
from app.models.issue import IssueCreate, IssueUpdate, IssueResponse, IssueStatus, IssueSeverity
from app.services.issues.service import IssueService
from app.middlewares.auth import (
    require_admin,
    require_maintainer_or_admin,
    require_any_role,
    get_current_user_required,
    can_access_issue_resource,
    can_modify_issue,
    can_delete_issue
)
from app.models.user import UserResponse, UserRole

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post("/", response_model=IssueResponse)
def create_issue(
    issue_data: IssueCreate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Create a new issue (Any authenticated user)"""
    # All users can create issues, but they are automatically the creator
    return IssueService.create_issue(db, issue_data, current_user.id)


@router.get("/", response_model=List[IssueResponse])
def get_issues(
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of issues to return"),
    status: Optional[IssueStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issues with role-based filtering"""
    if status:
        all_issues = IssueService.get_issues_by_status(db, status, skip=skip, limit=limit)
    else:
        all_issues = IssueService.get_all_issues(db, skip=skip, limit=limit)
    
    # REPORTER can only see their own issues
    if current_user.role == UserRole.REPORTER:
        filtered_issues = [
            issue for issue in all_issues 
            if issue.created_by == current_user.id
        ]
        return filtered_issues
    
    # MAINTAINER and ADMIN can see all issues
    return all_issues


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(
    issue_id: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issue by ID with role-based access control"""
    issue = IssueService.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check if user can access this issue
    if not can_access_issue_resource(current_user, issue.created_by):
        raise HTTPException(status_code=403, detail="Access denied to this issue")
    
    return issue


@router.put("/{issue_id}", response_model=IssueResponse)
def update_issue(
    issue_id: str, 
    issue_data: IssueUpdate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Update issue with role-based permissions"""
    # First check if issue exists
    existing_issue = IssueService.get_issue_by_id(db, issue_id)
    if not existing_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check if user can modify this issue
    if not can_modify_issue(current_user, existing_issue.created_by):
        raise HTTPException(status_code=403, detail="Access denied to modify this issue")
    
    # REPORTER can only modify title and description of their own issues
    if current_user.role == UserRole.REPORTER:
        # Prevent REPORTER from changing status or severity
        if issue_data.status is not None or issue_data.severity is not None:
            raise HTTPException(
                status_code=403, 
                detail="Reporters can only update title and description of their own issues"
            )
    
    issue = IssueService.update_issue(db, issue_id, issue_data, current_user.id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.delete("/{issue_id}")
def delete_issue(
    issue_id: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Delete issue with role-based permissions"""
    # First check if issue exists
    existing_issue = IssueService.get_issue_by_id(db, issue_id)
    if not existing_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Check if user can delete this issue
    if not can_delete_issue(current_user, existing_issue.created_by):
        raise HTTPException(
            status_code=403, 
            detail="Only admins or issue creators can delete issues"
        )
    
    success = IssueService.delete_issue(db, issue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"message": "Issue deleted successfully"}


@router.get("/user/{user_id}", response_model=List[IssueResponse])
def get_user_issues(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of issues to return"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issues created by specific user"""
    # REPORTER can only see their own issues
    if current_user.role == UserRole.REPORTER and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Reporters can only view their own issues")
    
    return IssueService.get_issues_by_user(db, user_id, skip=skip, limit=limit)


@router.get("/stats/count")
def get_issues_count(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get total issues count (MAINTAINER+ only)"""
    count = IssueService.get_issues_count(db)
    return {"total_issues": count}


@router.get("/stats/by-status")
def get_issues_by_status_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get issues count grouped by status (MAINTAINER+ only)"""
    stats = IssueService.get_issues_count_by_status(db)
    return {"issues_by_status": stats}


@router.get("/stats/by-severity")
def get_issues_by_severity_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get issues count grouped by severity (MAINTAINER+ only)"""
    stats = IssueService.get_issues_count_by_severity(db)
    return {"issues_by_severity": stats}